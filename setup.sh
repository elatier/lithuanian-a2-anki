#!/bin/bash
# setup.sh — everything the scripts need, in one command.
#
#   ./setup.sh          # venv + Python packages + the hunspell binary
#
# Building the deck needs only Python. Checking cards (the QA gate) also
# needs hunspell; its Lithuanian dictionary is in the repo (data/hunspell/),
# so only the binary is installed here. Safe to rerun.
set -eu
cd "$(dirname "$0")"

say() { printf '\n== %s\n' "$*"; }

say "Python environment (.venv)"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements-dev.txt
echo "ok: $(.venv/bin/python --version)"

say "hunspell"
if ! command -v hunspell >/dev/null; then
  if command -v brew >/dev/null; then brew install hunspell
  elif command -v apt-get >/dev/null; then sudo apt-get install -y hunspell
  else echo "install hunspell with your package manager, then rerun"; exit 1
  fi
fi
echo "ok: $(hunspell --version 2>/dev/null | head -1)"
echo namas | hunspell -d "$PWD/data/hunspell/lt_LT" -l >/dev/null && echo "ok: lt_LT dictionary (data/hunspell/) works"

say "check"
.venv/bin/python -m pytest -q tests/test_tools.py 2>&1 | tail -1
echo
echo "Ready. Build with ./build_single.sh; add words as described in README.md."
