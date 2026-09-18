#!/bin/bash
# release.sh vX.Y.Z — build, check the numbers, tag, push.
#
# The Release workflow (.github/workflows/release.yml) then builds the deck
# from the tag and attaches the .apkg to a GitHub release, which is what the
# download links point at. Without GitHub Actions, upload the local build:
#   gh release create vX.Y.Z decks/lietuviu_A2.apkg
set -eu
cd "$(dirname "$0")"
v=${1:?usage: ./release.sh vX.Y.Z}
PY=$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

[ -z "$(git status --porcelain)" ] || { echo "commit or stash your changes first"; git status --short; exit 1; }
./build_single.sh
"$PY" scripts/update_numbers.py --check || {
  echo "the docs quote stale numbers: run  $PY scripts/update_numbers.py  and commit"; exit 1; }
"$PY" -m pytest -q tests/test_docs.py
git tag "$v"
git push origin main "$v"
echo "tagged $v — the Release workflow will attach decks/lietuviu_A2.apkg"
