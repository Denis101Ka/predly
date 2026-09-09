# Reading Robinhood Chain

Everything in `data/` comes out of one public RPC and two event topics. This is the map, so the
numbers can be re-derived without this repository.

```
RPC       https://rpc.mainnet.chain.robinhood.com
chain id  4663
blocks    about 101 ms apart, single sequencer
```

## The launchpad curve

Every launchpad token trades against a bonding curve contract before it graduates. The curve
emits one event per fill:

```
BUY   0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455
SELL  0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df
```

The data layout is two words that swap by side: on a buy, word 0 is the quote amount and word 1
is the token amount; on a sell it is the other way around. The executed price of that fill is the
ratio of the two. No pricing oracle is involved anywhere.

```python
quote_raw, tok_raw = (w0, w1) if is_buy else (w1, w0)
price = (quote_raw / 1e18) / (tok_raw / 1e18)     # ETH-quoted curves
```

## Two quote tokens, one trap

Some curves quote in ETH and some in USDG, and the raw integers look similar enough that a naive
reader mixes them up. USDG carries six decimals, ETH carries eighteen, so a quote below `1e12` is
USDG and anything above is ETH. Get this wrong on one fill in a thousand and that token's cap
lands three orders of magnitude away from reality.

Two defences, both in `chain/fetch_chain.py`: implausible quotes are dropped per fill, and every
price path is trimmed around its own median before it is used. A token whose cap still leaves a
sane range after that is dropped entirely rather than printed.

## Market cap

Launchpad supply is fixed at `1e9` tokens, which is `1e27` in wei and confirmable with
`totalSupply()`, so:

```
cap_in_quote = price * 1e9
cap_in_usd   = cap_in_quote * eth_usd     # for ETH-quoted curves
```

The ETH price comes from `slot0()` on the ETH/USDG pool
`0x52e65b17fb6e5ba00ed806f37afcd2daa50271ca`, squared and scaled, the standard Uniswap v3
conversion.

## Token identity

The curve exposes its token through `token()` (`0xfc0c546a`). The token answers `symbol()` and
`name()` like any ERC-20. Symbols are **not** unique on a launchpad, so everything is keyed by
address.

## Where the launch metadata lives

There is no metadata getter on these tokens. The name, the description, the socials and the logo
live in the calldata of the transaction that created the token, which is found through the mint:
a `Transfer` out of the zero address, one per token.

```
Transfer  0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
topic1    0x0000000000000000000000000000000000000000000000000000000000000000
```

Pull that transaction, scan its input for printable strings, and the launch record falls out:
the name, an `ipfs://` image, an `x.com` link. Images are almost always IPFS, and gateway choice
matters: `ipfs.io` and `dweb.link` answer a plain client with 403, while `gateway.pinata.cloud`
and `4everland.io` serve the file, which is why the reader tries them in that order.

## Rate limits

The public RPC limits hard and answers a burst with `429`. The readers pace themselves at roughly
sixteen calls a second, back off six seconds on a `429`, and cache every image on disk. A full
scan of 60,000 blocks is about 25 `eth_getLogs` calls; resolving metadata for fourteen tokens is
another thirty or so.
