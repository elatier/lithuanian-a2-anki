#!/usr/bin/env python3
"""add_word.py — add or fix words in the deck: start, check, record, build.

Start a word:

    python3 scripts/add_word.py lentyna --new --theme 02

prints the drafting packet — what Wiktionary says the word means and how it
inflects, how the theme's cards read, which cards already share the English
answer, the allowed vocabulary — and appends a row to the newest batch file
with the key, part of speech, theme and Wiktionary's first gloss filled in.
Without --theme it prints the packet, with the list of themes, and writes
nothing. Then fill lt_def, en_def, lt_example, en_example in the row
(data/DRAFTING_GUIDE.md).

Finish it:

    python3 scripts/add_word.py lentyna

runs the QA gate and the root-leak check on the word's rows, records the
clips that are missing or whose text changed (four per card, a few seconds
each), rebuilds the deck and refreshes the numbers in the docs. Nothing is
recorded while a hard check fails, so a typo never costs a recording. Then
commit: the row, the clips in data/audio/, new files under data/cache/,
and the docs.

A batch:

    python3 scripts/add_word.py --new --list words.tsv    # word<TAB>theme[<TAB>pos]
    python3 scripts/add_word.py --batch batch33           # finish every word in it

--list scaffolds every word into a NEW batch file (the next number), so the
batch can be checked, recorded and built as one unit.

    --no-audio   check only
    --no-build   check and record, but do not rebuild the deck
    --pos        noun/verb/adj; needed when Wiktionary has more than one
    --theme      a theme from data/THEMES.md: "02-pastatai-ir-namai", "02", "pastatai"
    --batch      with --new: the batch file to append to (default: the newest);
                 alone: finish every word in that batch file
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

import build_single
import draft_packet
import ltcard
import paths
import resume_audio
import root_leak
import update_numbers
import verify_defs

TEMPLATE = ("key\tlt_def\ten_word\ten_def\tlt_example\ten_example\tpos"
            "\ttheme\t[qualifier]")
POS_CHOICES = ["noun", "verb", "adj", "num", "pron", "adv"]


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


def batch_path(name):
    return paths.BATCHES / (name if name.endswith(".tsv") else name + ".tsv")


def headwords_in(batch):
    p = batch_path(batch)
    if not p.exists():
        raise SystemExit(f"no such batch file: {p}")
    return sorted({k.split("#")[0] for k in ltcard.load_defs(str(p))})


def resolve_theme(slug):
    try:
        return ltcard.resolve_theme(slug)
    except LookupError as exc:
        raise SystemExit(f"--{exc}") from None


# -------------------------------------------------------------- start ----

def next_batch_name():
    last = paths.batch_files()
    return f"batch{paths.batch_num(last[-1]) + 1 if last else 1}"


def read_list(path):
    """[(word, theme, pos)] from a `word <TAB> theme [<TAB> pos]` file."""
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8")
                             .splitlines(), 1):
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        cols = [c.strip() for c in line.split("\t")] + ["", ""]
        if not cols[1]:
            raise SystemExit(f"{path}:{n}: expected `word<TAB>theme[<TAB>pos]`, "
                             f"got {line!r}")
        out.append((cols[0].lower(), cols[1], cols[2] or None))
    return out


def scaffold(word, pos, theme, batch, quiet=False):
    """Print the packet and append a row with everything a script can fill."""
    if rows_for(word):
        print(f"{word}: already has a card — edit that row, or add a second "
              f"sense keyed {word}#sense (README, 'The card format').")
        return 1
    theme = resolve_theme(theme) if theme else None
    if not quiet:
        draft_packet.packet(word, theme, next_steps=False)
        print()
    if not theme:
        print(f"{word}: choose a theme from the list above and rerun with "
              f"--theme; nothing written.")
        return 1
    entries = ltcard.kaikki_entries(word)
    poses = sorted({e.get("pos") for e in entries} & ltcard.POSES)
    if not pos:
        if len(poses) != 1:
            print(f"{word}: pass --pos; Wiktionary has "
                  + (f"{', '.join(poses)}" if poses else "no entry")
                  + f". Choices: {', '.join(POS_CHOICES)}")
            return 1
        pos = poses[0]
    gloss = ltcard.wikt_gloss(entries, pos, n=1) if pos in poses else ""
    gloss = re.sub(r"\s+", " ", re.split(r"[;,]", gloss)[0]).strip()
    if pos == "verb" and gloss and not gloss.startswith("to "):
        gloss = "to " + gloss
    target = batch_path(batch) if batch else paths.batch_files()[-1]
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    row = "\t".join([word, "", gloss, "", "", "", pos, theme])
    target.write_text(existing + row + "\n", encoding="utf-8")
    ltcard.load_themes.cache_clear()
    print(f"{word}: row appended to {target.name}\n    {row}")
    if not gloss:
        print("    (no Wiktionary gloss: the GLOSS check will need a row in "
              "data/gloss_overrides.tsv)")
    if not quiet:
        print(f"\nFill lt_def, en_def, lt_example, en_example in {target.name} "
              f"(data/DRAFTING_GUIDE.md), then:\n"
              f"    python3 scripts/add_word.py {word}")
    return 0


def scaffold_list(path, pos, batch):
    todo = read_list(path)
    batch = batch or next_batch_name()
    for _, theme, _ in todo:
        resolve_theme(theme)            # every theme must resolve before any write
    rc = 0
    for word, theme, p in todo:
        rc |= scaffold(word, p or pos, theme, batch, quiet=True)
    print(f"\n{len(todo)} word(s) scaffolded into {batch}.tsv. Fill the "
          f"columns, then:\n    python3 scripts/add_word.py --batch {batch}")
    return rc


# ------------------------------------------------------------- finish ----

def finish(words, no_audio=False, no_build=False):
    """Check the words' rows; if clean, record, build and refresh the docs."""
    rows, problems = [], []
    for w in words:
        found = rows_for(w)
        if not found:
            problems.append(
                f"{w}: no card. Start one with `add_word.py {w} --new "
                f"--theme ...`, or add a row to a data/batches/batch*.tsv "
                f"file:\n    {TEMPLATE}")
            continue
        for f, _ in found:
            print(f"{w}: {f.name}")
        rows += [line for _, line in found]
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
        if no_audio:
            return 0

        print("\n--- audio")
        rc = resume_audio.main([str(tsv)], quiet=True)
    if rc:
        print("\nSome clips could not be recorded; rerun later.")
        return rc
    if no_build:
        print("\nRecorded. Build with ./build_single.sh when ready.")
        return 0

    print("\n--- build")
    build_single.main(["--no-fetch"])
    print("\n--- numbers")
    update_numbers.main()
    print("\nDone. Commit the row(s), the new clips in data/audio/ (with "
          ".text_manifest.json), new files under data/cache/, and the docs.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("words", nargs="*")
    ap.add_argument("--new", action="store_true",
                    help="start a word that has no card yet")
    ap.add_argument("--list", metavar="FILE",
                    help="with --new: every `word<TAB>theme[<TAB>pos]` line "
                         "of FILE into a new batch file")
    ap.add_argument("--pos", choices=POS_CHOICES)
    ap.add_argument("--theme", help="theme from data/THEMES.md, full or partial")
    ap.add_argument("--batch", help="batch file: append to it (--new) or "
                                    "finish every word in it")
    ap.add_argument("--no-audio", action="store_true", help="check only")
    ap.add_argument("--no-build", action="store_true",
                    help="check and record, but do not rebuild the deck")
    args = ap.parse_args()
    words = [w.strip().lower() for w in args.words]

    if args.new:
        if args.list:
            return scaffold_list(args.list, args.pos, args.batch)
        if not words:
            ap.error("--new needs a word, or --list FILE")
        rc = 0
        for w in words:
            rc |= scaffold(w, args.pos, args.theme, args.batch)
        return rc
    if args.batch and not words:
        words = headwords_in(args.batch)
    if not words:
        ap.error("give a word, --batch NAME, or --new")
    return finish(words, args.no_audio, args.no_build)


if __name__ == "__main__":
    sys.exit(main())
