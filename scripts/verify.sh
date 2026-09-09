#!/usr/bin/env bash
# Recompute everything this repository claims, in one go.
#
#   ./scripts/verify.sh            replay the published vectors through both engines
#   ./scripts/verify.sh --full     also scan the chain and rebuild the board
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== python engine =="
python -m unittest discover -s verify -p "test_*.py" -t . 2>&1 | tail -3
python -m verify --vectors

if command -v node >/dev/null 2>&1; then
  echo
  echo "== typescript engine =="
  npm install --no-audit --no-fund --silent
  npm test 2>&1 | tail -6
else
  echo
  echo "node not found, skipping the typescript engine"
fi

if [ "${1:-}" = "--full" ]; then
  echo
  echo "== chain scan =="
  python chain/fetch_chain.py 60000
  python chain/fetch_logos.py 0.5 || echo "metadata pass failed, keeping the previous images"
  python board/build_board.py PREDLY
  echo "open board/board.html"
fi
