# Market rulebook

Prediction markets do not die of bad code. They die of an edge case nobody wrote down, argued
about after the fact. This is that list, written before the argument.

## Market templates

| Template | Question | Window | Resolves YES when |
|---|---|---|---|
| `reach` | will the cap reach a level above it | 1 hour | the cap touches the target at any point in the window |
| `hold` | will the cap stay above a level below it | 1 hour | the cap never touches the floor before the deadline |
| `double` | will the cap double from the open | 1 day | the cap touches twice the opening cap in the window |

## Timing

- **Open.** The target is computed from candles that closed before the window opened, then frozen.
- **Early resolution.** A touch market resolves the moment the condition is met. A floor market
  resolves NO the moment the floor is breached. Neither waits for the deadline.
- **Deadline.** Anything still open settles on the cap printed by the last candle that closed at
  or before the deadline.
- **Phase.** Each token's window is offset by `hash32("hour:" + address) % 3600` so twenty
  markets do not all expire on the same minute.

## Edge cases

**A candle is missing.** Five-minute candles can be absent when nothing trades. A gap is not a
price of zero: the last known close carries forward, and a gap covering more than half the window
voids the market rather than resolving it on two prints.

**The cap touches the target exactly.** A touch is `>=` for a target above and `<=` for a floor
below. Exactly on the number resolves the market, it does not push it.

**The pool migrates.** A token that graduates from the launchpad curve to a pool keeps its
market: the cap series follows the venue with the deepest liquidity at each timestamp. If the
migration leaves a gap longer than half the window, the previous rule applies and the market is
voided.

**Liquidity disappears.** If the pool's liquidity falls under the listing threshold mid-window,
the market runs to its deadline on the data that exists. Prices on a dead pool are noise, so
resolution uses the last close before liquidity fell away.

**The quote leg misreads.** A fill whose quote token decodes in the wrong units puts the cap off
by a factor of `1e12`. Every reader in this repository trims price paths around their own median
and drops a token whose implied cap leaves a sane range entirely. A market built on a misread cap
is void, not merely wrong.

**A reorg crosses the deadline.** Robinhood Chain runs a single sequencer at roughly 101 ms per
block, so a reorg deep enough to move a five-minute close is not expected. If one happens, the
market resolves on the canonical chain after the reorg settles, and the correction goes into the
incident log.

**The token is not a memecoin.** Stablecoins, wrapped majors, tokenized equities and launchpad
infrastructure are filtered out before the board is built. A token that slips through and gets a
market keeps it: the filter applies at selection, not retroactively.

**Two tokens share a symbol.** Symbols on a launchpad are not unique. Markets are keyed by
contract address, and the board prints the address under the ticker for exactly this reason.

## Voiding

A voided market settles both sides at the price they were bought at. Voiding is the last resort,
reserved for the cases named above: missing data over half the window, a cap proven to be a
decoding artifact, or a resolution that contradicts the canonical chain.

Every void is logged with the market, the reason and the block, because a project that voids
quietly is a project that voids often.
