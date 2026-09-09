"""CLI for the reference odds engine.

    python -m verify --cap 493e6 --target 986e6 --sigma 0.35 --hours 5.5
    python -m verify --cap 39000 --floor 34000 --sigma 0.9 --hours 1 --kind floor
    python -m verify --vectors           # replay every published test vector
    python -m verify --ladder --cap 188e6 --sigma 0.42 --hours 1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .odds import Quote, iter_ladder, quote

VECTORS = pathlib.Path(__file__).resolve().parent / "vectors.json"


def human(n: float) -> str:
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= size:
            return f"${n / size:.2f}{unit}"
    return f"${n:.0f}"


def run_vectors() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    bad = 0
    for v in data["vectors"]:
        q = quote(v["cap"], v["level"], v["sigma"], v["hours"], v["kind"])
        ok = q.yes_cents == v["yes_cents"]
        bad += 0 if ok else 1
        mark = "ok  " if ok else "FAIL"
        print(f"  {mark} {v['name']:<34} expected {v['yes_cents']:>2}c  got {q.yes_cents:>2}c")
    print(f"\n{len(data['vectors']) - bad}/{len(data['vectors'])} vectors reproduced")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="verify", description="recompute a Predly market price")
    p.add_argument("--cap", type=float, help="current market cap in dollars")
    p.add_argument("--target", type=float, help="touch level for reach and double markets")
    p.add_argument("--floor", type=float, help="floor level for hold markets")
    p.add_argument("--sigma", type=float, help="hourly realized volatility, for example 0.35")
    p.add_argument("--hours", type=float, help="hours left until the deadline")
    p.add_argument("--kind", choices=["touch", "floor"], help="market kind, inferred if omitted")
    p.add_argument("--ladder", action="store_true", help="print the whole goalpost ladder")
    p.add_argument("--vectors", action="store_true", help="replay the published test vectors")
    a = p.parse_args(argv)

    if a.vectors:
        return run_vectors()

    if a.cap is None or a.sigma is None or a.hours is None:
        p.error("--cap, --sigma and --hours are required")

    if a.ladder:
        print(f"cap {human(a.cap)}  sigma {a.sigma}/h  {a.hours}h left\n")
        for level, q in iter_ladder(a.cap, a.sigma, a.hours):
            print(f"  target {human(level):>10}   {q}")
        return 0

    kind = a.kind or ("floor" if a.floor is not None else "touch")
    level = a.floor if kind == "floor" else a.target
    if level is None:
        p.error("pass --target for a touch market or --floor for a hold market")

    q: Quote = quote(a.cap, level, a.sigma, a.hours, kind)
    print(q)
    return 0


if __name__ == "__main__":
    sys.exit(main())
