# Security policy

## What the site can and cannot do

Predly is a read-only front end at this stage. It is worth stating the boundary plainly, because
"connect wallet" is the moment every crypto site earns or loses trust:

- It **never** requests `personal_sign`, `eth_sign` or `eth_signTypedData`.
- It **never** builds, requests or broadcasts a transaction.
- It **never** asks for a seed phrase, a private key or an approval.
- A connected wallet is used for one thing: reading the address and its balances.
- Every position on the site is paper. It lives in the browser's own storage and never leaves it.

You do not have to take that on faith. Open the developer tools, filter the network tab for the
RPC host, and watch: the only methods that go out are `eth_blockNumber`, `eth_getLogs`,
`eth_call` and `eth_getBalance`. If you ever see a signing request from a Predly page, that page
is not ours — close it and report it.

## Reporting a vulnerability

Open a [security advisory](https://github.com/Denis101Ka/predly-tools/security/advisories/new),
or write to security@predly.tech if the issue affects the live site.

Please include what you did, what happened, and what you expected. If the report concerns the
odds engine, a failing test vector is the fastest possible bug report.

**In scope:** this repository, the odds engine, the chain readers, the published data, and
anything on predly.tech that could put a visitor's wallet or funds at risk.

**Out of scope:** the fact that odds are model-derived rather than bet-derived, and the fact
that trading is paper. Both are documented, deliberate, and stated on the site.

## Data corrections

A wrong cap, a mislabelled token, a market that resolved against the chain: open an issue with
the block number and the token address. Numbers in this repo are reproducible, so a correction is
a matter of rerunning the reader, not of opinion.
