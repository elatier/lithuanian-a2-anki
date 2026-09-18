#!/usr/bin/env python3
"""add_word.py WORD ... — check new or edited words end to end, then record
only their audio.

Write the card first: a row in a data/batches/batch*.tsv file (see "The card
format" in README.md) and the headword under a theme in
data/a2_zodziai_v2.txt. Then:

    python3 scripts/add_word.py žibintas
    ./build_single.sh

For each word this finds its rows, checks the theme, runs the QA gate and the
root-leak check on just those rows, and records the clips that are missing or
whose text changed — four per card, a few seconds each. Nothing is recorded
while a hard QA check fails, so a typo never costs a recording.

    --no-audio   stop after the checks
"""
import argparse
import sys
import tempfile
from pathlib import Path

import ltcard
import paths
import resume_audio
import root_leak
import verify_defs

TEMPLATE = ("key\tlt_def\ten_word\ten_def\tlt_example\ten_example\tpos"
            "\t[qualifier]")


def rows_for(word):
    """(batch file, raw line) for every card whose headword is `word`."""
    out = []
    for f in paths.batch_files():
        for line in f.read_text(encoding="utf-8").splitlines():
            key = line.split("\t", 1)[0].strip()
            if line.strip() and not line.startswith("#") \
                    and key.split("#")[0] == word:
                out.append((f, line))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("words", nargs="+")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    themes = ltcard.load_themes()
    rows, problems = [], []
    for w in args.words:
        found = rows_for(w)
        if not found:
            problems.append(
                f"{w}: no card. Add a row to a data/batches/batch*.tsv file:\n"
                f"    {TEMPLATE}")
            continue
        for f, _ in found:
            print(f"{w}: {f.name}")
        rows += [line for _, line in found]
        if w not in themes:
            problems.append(
                f"{w}: no theme. List it under a theme heading in "
                f"data/a2_zodziai_v2.txt (themes: data/THEMES.md), or it "
                f"lands in tema::be-temos.")
    for p in problems:
        print(f"\n✗ {p}")
    if not rows:
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tsv = Path(tmp) / "words.tsv"
        tsv.write_text("\n".join(rows) + "\n", encoding="utf-8")

        print("\n--- QA gate")
        hard_fail, _review = verify_defs.check(str(tsv))
        print("\n--- root leak")
        root_leak.main([str(tsv)])
        if hard_fail or problems:
            print("\nFix the problems above and rerun; no audio recorded.")
            print("No inflection table? Draft one with "
                  "`python3 scripts/gen_forms.py WORD POS` into "
                  "data/manual_forms.tsv.")
            return 1
        if args.no_audio:
            return 0

        print("\n--- audio")
        rc = resume_audio.main([str(tsv)], quiet=True)
    if rc:
        print("\nSome clips could not be recorded; rerun later.")
        return rc
    print("\nDone. Now build: ./build_single.sh")
    print("New dictionary lookups land in data/cache/ — commit them with "
          "the card, so the next build needs no network.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
