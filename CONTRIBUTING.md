# Contributing

The most valuable contribution to this repository is a number that does not reproduce.

## Found a price that disagrees with the site?

1. Recompute it: `python -m verify --cap <cap> --target <level> --sigma <sigma> --hours <hours>`
2. If your cents differ from the board's, open an issue with the token address, the block, and
   both numbers.
3. If they differ between `verify/odds.py` and `verify/odds.ts`, that is a bug in this repo and
   it will be treated as one. Add the case to `verify/vectors.json` in the pull request.

## Running the suites

```bash
python -m unittest discover -s verify -p "test_*.py" -t .
npm install && npm test
```

Both replay `verify/vectors.json`. A change to the engine that does not change the vectors is
suspicious; a change that does needs a sentence in the pull request explaining which market
behaviour moved and why.

## House style

- Standard library only on the Python side. The point of this repo is that anyone can run it
  without trusting a dependency tree.
- The two engines stay line-for-line comparable. If you touch one, touch the other.
- Comments explain *why*, not *what*. The formula is in the README; the code should say what the
  formula does not.

## Chain readers

`chain/` talks to a public RPC that rate limits hard. Keep the pacing and the backoff in place,
and cache anything that can be cached. A pull request that removes a `time.sleep` is a pull
request that gets somebody rate limited.
