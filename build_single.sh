#!/bin/bash
# build_single.sh [args…] — one .apkg for the whole deck.
#
# Wrapper around scripts/build_single.py that uses the project venv if it
# exists (that is where genanki lives on macOS), otherwise the system python3.
#
#   ./build_single.sh                    # decks/lietuviu_A2.apkg, a subdeck per theme
#   ./build_single.sh --subdecks none    # one flat deck
#   ./build_single.sh --subdecks batch   # a subdeck per batch
#   ./build_single.sh --no-fetch         # never call the synthesiser
#
# Audio must already be cached — run `python3 scripts/fetch_audio.py` first.
set -u
cd "$(dirname "$0")"
PY=$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
exec "$PY" scripts/build_single.py "$@"
