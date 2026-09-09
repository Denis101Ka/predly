#!/usr/bin/env bash
# Pull a fresh snapshot off the chain and rebuild everything that depends on it.
#
#   ./scripts/snapshot.sh           scan 60k blocks, about 1.7 hours of chain
#   ./scripts/snapshot.sh 150000    scan wider, slower, more tokens to choose from
set -euo pipefail
cd "$(dirname "$0")/.."

BLOCKS="${1:-60000}"
STAMP="$(date -u +%Y-%m-%dT%HZ)"

echo "scanning $BLOCKS blocks"
python chain/fetch_chain.py "$BLOCKS"

echo "resolving launch metadata and images"
python chain/fetch_logos.py 0.5 || echo "metadata pass failed, keeping what was cached"

echo "rebuilding the board"
python board/build_board.py PREDLY

mkdir -p data/history
cp data/snapshot-latest.json "data/history/$STAMP.json"
echo "kept data/history/$STAMP.json"

python - <<'PY'
import json, pathlib
s = json.loads(pathlib.Path("data/snapshot-latest.json").read_text(encoding="utf-8"))
print()
print("head block   ", f"{s['chain']['head_block']:,}")
print("curves seen  ", f"{s['curves_seen']:,}")
print("tokens kept  ", len(s["tokens"]))
print("with a logo  ", sum(1 for t in s["tokens"] if t.get("logo")))
print("eth/usd      ", s.get("eth_usd"))
PY
