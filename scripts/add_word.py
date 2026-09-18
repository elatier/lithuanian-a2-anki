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

Starting a word from nothing:

    python3 scripts/draft_packet.py lentyna          # what to write, and how
    python3 scripts/add_word.py lentyna --new --pos noun --theme 02-pastatai-ir-namai

--new appends a row with the key, the part of speech and Wiktionary's first
gloss filled in, and lists the word under the theme. Fill the definition,
the example and their translations, then run the checks as above.
    --pos        noun/verb/adj; needed when Wiktionary has more than one
    --theme      a theme slug from data/THEMES.md, full or partial
    --batch      the batch file to append to (default: the newest)

A batch of words at once:

    python3 scripts/add_word.py --new --list words.tsv

where each line of words.tsv is `word <TAB> theme [<TAB> pos]`; `#` starts a
comment. The rows go into a NEW batch file (the next number) unless --batch
says otherwise, so the batch can be checked and recorded as one unit:

    python3 scripts/verify_defs.py data/batches/batch33.tsv
    python3 scripts/root_leak.py data/batches/batch33.tsv
    python3 scripts/resume_audio.py data/batches/batch33.tsv
"""
import argparse
import re
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


def theme_headings():
    """[(line index, tag)] for every theme heading in a2_zodziai_v2.txt."""
    out = []
    for i, line in enumerate(paths.THEME_FILE.read_text(encoding="utf-8")
                             .splitlines()):
        if line.startswith("#") and "::" in line and " " not in line.strip("# "):
            out.append((i, line.lstrip("# ").strip()))
    return out


def resolve_theme(slug):
    """A theme tag from a full or partial slug: "egzaminas::02-pastatai-ir-namai",
    "02-pastatai-ir-namai", "02" or "pastatai" all name the same theme."""
    heads = theme_headings()
    hits = [tag for _, tag in heads
            if tag == slug or tag.split("::")[-1] == slug
            or tag.split("::")[-1].startswith(slug) or slug in tag]
    if len(hits) != 1:
        raise SystemExit(f"--theme {slug!r} matches {len(hits)} themes; use one "
                         f"of:\n  " + "\n  ".join(t for _, t in heads))
    return hits[0]


def add_to_theme(word, slug):
    """List `word` at the end of the theme whose tag matches `slug`."""
    tag = resolve_theme(slug)
    heads = theme_headings()
    lines = paths.THEME_FILE.read_text(encoding="utf-8").splitlines()
    i = next(j for j, t in heads if t == tag)
    end = next((j for j, _ in heads if j > i), len(lines))
    while end > i + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, word)
    paths.THEME_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tag


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
    """Append a row for a new word with everything a script can fill in."""
    if rows_for(word):
        print(f"{word}: already has a card — edit that row, or add a second "
              f"sense keyed {word}#sense (README, 'The card format').")
        return 1
    if theme:
        resolve_theme(theme)            # fail before anything is written
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
    if batch:
        target = paths.BATCHES / (batch if batch.endswith(".tsv") else batch + ".tsv")
    else:
        target = paths.batch_files()[-1]
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    row = "\t".join([word, "", gloss, "", "", "", pos])
    target.write_text(existing + row + "\n", encoding="utf-8")
    print(f"{word}: row appended to {target.name}\n    {row}")
    if not gloss:
        print("    (no Wiktionary gloss: the GLOSS check will need a row in "
              "data/gloss_overrides.tsv)")
    if theme:
        if word in ltcard.load_themes():
            print(f"{word}: already listed under {ltcard.load_themes()[word]}")
        else:
            print(f"{word}: listed under {add_to_theme(word, theme)}")
    else:
        print(f"{word}: no --theme given; list it in data/a2_zodziai_v2.txt "
              f"before the build, or it lands in tema::be-temos.")
    if not quiet:
        print(f"\nFill lt_def, en_def, lt_example, en_example in {target.name} "
              f"(data/DRAFTING_GUIDE.md), then:\n"
              f"    python3 scripts/add_word.py {word} --no-audio")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("words", nargs="*")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--new", action="store_true",
                    help="scaffold a row for a word that has no card yet")
    ap.add_argument("--pos", choices=POS_CHOICES)
    ap.add_argument("--theme", help="theme slug (with --new)")
    ap.add_argument("--batch", help="batch file to append to (with --new)")
    ap.add_argument("--list", metavar="FILE",
                    help="with --new: scaffold every `word<TAB>theme[<TAB>pos]` "
                         "line of FILE into a new batch file")
    args = ap.parse_args()

    if args.list:
        if not args.new:
            ap.error("--list needs --new")
        todo = read_list(args.list)
        batch = args.batch or next_batch_name()
        for _, theme, _ in todo:
            resolve_theme(theme)        # every theme must resolve before any write
        rc = 0
        for word, theme, pos in todo:
            rc |= scaffold(word, pos or args.pos, theme, batch, quiet=True)
        print(f"\n{len(todo)} word(s) scaffolded into {batch}.tsv. Fill the "
              f"columns, then check the whole batch:\n"
              f"    python3 scripts/verify_defs.py data/batches/{batch}.tsv\n"
              f"    python3 scripts/root_leak.py data/batches/{batch}.tsv")
        return rc
    if not args.words:
        ap.error("give at least one word, or --new --list FILE")
    if args.new:
        rc = 0
        for w in args.words:
            rc |= scaffold(w.strip().lower(), args.pos, args.theme, args.batch)
        return rc

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
