#!/bin/bash
# setup.sh — everything the scripts need, in one command.
#
#   ./setup.sh          # venv + Python packages + hunspell with lt_LT
#
# Building the deck needs only Python. Checking cards (the QA gate) also
# needs hunspell and its Lithuanian dictionary; this installs both where it
# can and tells you what it could not do. Safe to rerun.
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
  elif command -v apt-get >/dev/null; then sudo apt-get install -y hunspell hunspell-lt
  else echo "install hunspell with your package manager, then rerun"; exit 1
  fi
fi
echo "ok: $(hunspell --version 2>/dev/null | head -1)"

say "Lithuanian dictionary (lt_LT)"
if echo namas | hunspell -d lt_LT -l >/dev/null 2>&1; then
  echo "ok: lt_LT found"
else
  case "$(uname)" in
    Darwin)
      # Homebrew ships no Lithuanian dictionary; LibreOffice's is BSD-licensed.
      dir="$HOME/Library/Spelling"; mkdir -p "$dir"
      base="https://raw.githubusercontent.com/LibreOffice/dictionaries/master/lt_LT"
      curl -fsSL "$base/lt.aff" -o "$dir/lt_LT.aff"
      curl -fsSL "$base/lt.dic" -o "$dir/lt_LT.dic"
      echo "installed lt_LT.aff and lt_LT.dic into $dir" ;;
    *)
      if command -v apt-get >/dev/null; then sudo apt-get install -y hunspell-lt
      else echo "install the hunspell lt_LT dictionary for your system, or set DICPATH"; exit 1
      fi ;;
  esac
  echo namas | hunspell -d lt_LT -l >/dev/null && echo "ok: lt_LT works"
fi

say "check"
.venv/bin/python -m pytest -q tests/test_tools.py 2>&1 | tail -1
echo
echo "Ready. Build with ./build_single.sh; add words as described in README.md."
