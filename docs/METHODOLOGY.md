# Methodology

How a market gets born, priced and settled, and why each choice is the way it is.

## The problem with a fixed percentage

The obvious way to write a market on a memecoin is "will it go up 50%". It is also useless. A
token worth half a billion dollars moves a few percent an hour; a token nine minutes old moves
fifty. The same question is a coin flip for one and a lottery ticket for the other, and a board
made of those questions is a board where every row is priced at 3c or 97c. Nobody trades a row
that is already decided.

## Volatility-scaled goalposts

A market's target sits a fixed number of standard deviations away from the cap, not a fixed
percentage:

```
target = cap · exp( k · σ · √T )
```

`σ` is the token's own realized hourly volatility, `T` the length of the window, `k` the
difficulty knob. The quiet half-billion token and the nine-minute-old meme both get a target that
is roughly as hard to reach as each other, which is exactly what makes the board readable: the
cents spread across the range instead of piling up at the ends.

The target is measured at the window's open, from candles that closed **before** it, and then
frozen. Goalposts that move while a market is live are not goalposts.

## Realized volatility

`σ` is the sample standard deviation of close-to-close log returns over the trailing six hours of
five-minute candles, scaled to an hour by `√12`, then clamped to `[0.05, 3]`.

Six hours is a compromise. Shorter and a single wick sets the target for the whole window;
longer and a token that woke up twenty minutes ago still looks asleep. The clamp exists because a
token with three trades in six hours produces either a zero or a number in the hundreds, and both
break the pricing.

## The price

The cap is modelled as a driftless log-normal walk. Drift is deliberately left out: over an hour
the drift term is swamped by the volatility term, and estimating it from six hours of memecoin
candles produces a number that says more about the last pump than about the next one.

For a **touch** market the question is whether the running maximum reaches the target before the
deadline. The reflection principle turns that into a closed form:

```
P(max over [0,τ] ≥ target) = 2 · (1 − Φ(d)),    d = ln(target / cap) / (σ√τ)
```

A **floor** market asks the opposite, that the walk never touches the level below, which is the
complement of the same expression.

The result is clamped to `[0.03, 0.97]`. A market never quotes certainty, because the model is
never certain: the clamp is where the model admits it stops knowing.

## Why cents

Shares are priced in whole cents, YES and NO always summing to a dollar. A price of 62c is a
probability of 62%, readable without a conversion, and settlement is trivial: the winning side
pays a dollar, the losing side pays zero.

## Resolution

The cap path is read off the same five-minute candles the price used. A touch market resolves YES
the moment the candles show the cap reaching the target, early rather than at the deadline,
because the question was whether it *reaches*, not where it ends. A floor market resolves NO the
moment the cap goes through the floor. Anything still open at the deadline settles on the cap at
the deadline.

Nobody votes. There is no committee, no dispute window and no oracle to bribe: the input is
public data and the rule is arithmetic. The tradeoff is that the market is only as good as the
data source, which is why [the rulebook](RULEBOOK.md) spends most of its length on what happens
when that source misbehaves.

## What is modelled and what is measured

Caps, volumes, candles, launches and block heights are measured. Odds are modelled from those
measurements. Order book depth, payouts and positions on the demo board are a product preview.
The distinction is marked on every panel, and it is the reason this repository exists: a measured
number you cannot reproduce is just a claim.
