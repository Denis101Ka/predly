"""Reference implementation of the Predly odds engine.

Predly prices a market on a token's market cap as a first passage problem: the cap is
treated as a driftless log-normal walk, and the YES price is the probability that the
walk touches the target (or stays above the floor) before the deadline.

Nothing here talks to Predly. Feed it public candles and it reproduces, to the cent,
the number the board is showing. That is the whole point of this file.

    python -m verify --cap 493e6 --target 986e6 --sigma 0.35 --hours 5.5
    -> touch  d=0.8444  p_yes=0.3986  YES 40c / NO 60c

The same maths lives in verify/odds.ts, and both are checked against verify/vectors.json.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

# clamps, kept identical in both implementations
P_MIN, P_MAX = 0.03, 0.97          # a market never quotes certainty
SIGMA_MIN, SIGMA_MAX = 0.05, 3.0   # hourly realized volatility bounds
TAU_MIN_HOURS = 1.0 / 60.0         # a deadline never gets closer than a minute
BARS_PER_HOUR = 12                 # five minute candles
VOL_WINDOW_HOURS = 6               # how far back realized volatility is measured

Kind = Literal["touch", "floor"]


def phi(x: float) -> float:
    """Standard normal CDF, Abramowitz and Stegun 26.2.17.

    Chosen over math.erf so that the Python and the TypeScript implementation
    agree bit for bit at the cent level on every platform.
    """
    p = 0.2316419
    b = (0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429)
    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    poly = sum(c * t ** (i + 1) for i, c in enumerate(b))
    cdf = 1.0 - (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-x * x / 2.0) * poly
    return cdf if sign > 0 else 1.0 - cdf


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def realized_sigma(closes: Sequence[float], bars_per_hour: int = BARS_PER_HOUR) -> float:
    """Hourly realized volatility from close to close log returns.

    `closes` are five minute closes, oldest first. The sample standard deviation of
    the log returns is a per bar figure, so it is scaled by sqrt(bars per hour).
    """
    if len(closes) < 3:
        return SIGMA_MIN
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    if len(rets) < 2:
        return SIGMA_MIN
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return clamp(math.sqrt(var) * math.sqrt(bars_per_hour), SIGMA_MIN, SIGMA_MAX)


def sigma_from_candles(closes: Sequence[float], window_hours: int = VOL_WINDOW_HOURS) -> float:
    """Realized volatility over the trailing window only, the way a market open measures it."""
    need = window_hours * BARS_PER_HOUR + 1
    return realized_sigma(list(closes)[-need:])


@dataclass(frozen=True)
class Quote:
    kind: Kind
    d: float
    p_yes: float
    yes_cents: int
    no_cents: int

    def __str__(self) -> str:
        return (f"{self.kind}  d={self.d:.4f}  p_yes={self.p_yes:.4f}  "
                f"YES {self.yes_cents}c / NO {self.no_cents}c")


def quote(cap: float, level: float, sigma: float, hours: float, kind: Kind = "touch") -> Quote:
    """Price one market.

    touch: will the cap reach `level` before the deadline (reach, double templates).
    floor: will the cap stay above `level` until the deadline (hold template).
    """
    if cap <= 0 or level <= 0:
        raise ValueError("cap and level must be positive")
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    tau = max(hours, TAU_MIN_HOURS)
    denom = clamp(sigma, SIGMA_MIN, SIGMA_MAX) * math.sqrt(tau)

    if kind == "touch":
        d = math.log(level / cap) / denom
        p = 2.0 * (1.0 - phi(d))          # reflection principle on the running maximum
    elif kind == "floor":
        d = math.log(cap / level) / denom
        p = 2.0 * phi(d) - 1.0            # complement: never touching the floor
    else:
        raise ValueError(f"unknown market kind: {kind}")

    p = clamp(p, P_MIN, P_MAX)
    yes = int(clamp(round(p * 100), 1, 99))
    return Quote(kind=kind, d=d, p_yes=p, yes_cents=yes, no_cents=100 - yes)


def quote_from_candles(cap: float, level: float, closes: Sequence[float], hours: float,
                       kind: Kind = "touch") -> Quote:
    """Convenience: measure volatility off the candles, then price."""
    return quote(cap, level, sigma_from_candles(closes), hours, kind)


def target_for(cap: float, sigma: float, hours: float, k: float = 1.0) -> float:
    """Where a volatility scaled goalpost sits: k sigma root T away from the cap.

    This is why a half billion dollar token and a five minute old meme both get a
    question worth asking instead of a fixed percentage that is trivial for one and
    impossible for the other.
    """
    return cap * math.exp(k * clamp(sigma, SIGMA_MIN, SIGMA_MAX) * math.sqrt(max(hours, TAU_MIN_HOURS)))


def iter_ladder(cap: float, sigma: float, hours: float,
                ks: Iterable[float] = (0.5, 1.0, 1.5, 2.0)) -> list[tuple[float, Quote]]:
    """The whole goalpost ladder for one token, useful when eyeballing a board row."""
    out = []
    for k in ks:
        level = target_for(cap, sigma, hours, k)
        out.append((level, quote(cap, level, sigma, hours, "touch")))
    return out
