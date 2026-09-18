#!/usr/bin/env python3
"""forms.py — the paradigms Wiktionary does not have: draft, check, accent.

A word with no Wiktionary inflection table gets a hand-written row in
data/manual_forms.tsv (word, pos, forms line, all forms). Three steps:

    python3 scripts/forms.py draft WORD POS     # a row for a regular word
    python3 scripts/forms.py check [FILE]       # hunspell-verify every form
    python3 scripts/forms.py accent [--dry-run] # stress marks on every shown form

draft  detects the declension or conjugation from the ending and expands
       it; paste the printed row into manual_forms.tsv. Every generated
       form is then checked, so a wrong pattern is caught rather than
       shipped; irregular words fail the check and are filled by hand.
check  exits 1 and lists any form the lt_LT lexicon does not recognise.
accent puts stress marks on every form printed on the card, from two
       sources that actually have the data — data/accented.txt, produced
       by a person with VDU's Kirčiuoklis, and kaikki.org — and refuses to
       invent the rest: forms neither source has are listed in
       out/needs_accents.txt for the next Kirčiuoklis round.
"""
import argparse
import json
import re
import sys
import unicodedata as u

import ltcard
import paths
import spell

# ------------------------------------------------------------------ draft --

NOUN = {
    "as":  ("as o ui ą u e", "ai ų ams us ais uose"),          # namas
    "is":  ("is io iui į iu yje", "iai ių iams ius iais iuose"), # brolis
    "ys":  ("ys io iui į iu yje", "iai ių iams ius iais iuose"), # arklys
    "us":  ("us aus ui ų umi uje", "ūs ų ums us umis uose"),     # sūnus
    "a":   ("a os ai ą a oje", "os ų oms as omis ose"),          # knyga
    "ė":   ("ė ės ei ę e ėje", "ės ių ėms es ėmis ėse"),         # gėlė
}
VERB = {  # infinitive ending -> (pres3, past3) added to the stem
    "yti": ("o", "ė"), "ėti": ("i", "ėjo"), "oti": ("oja", "ojo"),
    "uoti": ("uoja", "avo"), "auti": ("auja", "avo"), "inti": ("ina", "ino"),
}


def draft_noun(word):
    for end, (sg, pl) in NOUN.items():
        if word.endswith(end):
            stem = word[: -len(end)]
            sgf = [stem + e for e in sg.split()]
            plf = [stem + e for e in pl.split()]
            return f"{sgf[0]} / {plf[0]}", sgf + plf
    return None, None


def draft_verb(word):
    for end, (p3, t3) in VERB.items():
        if word.endswith(end):
            stem = word[: -len(end)]
            pres = stem + p3            # rašyti -> rašo, mylėti -> myli
            past = stem + t3
            return f"{word}, {pres}, {past}", [word, pres, past]
    return None, None


def draft(word, pos):
    """A manual_forms.tsv row for a regular word, or None."""
    line, forms = draft_noun(word) if pos == "noun" else draft_verb(word)
    if not line:
        return None
    return f"{word}\t{pos}\t{line}\t{' '.join(forms)}"


# ------------------------------------------------------------------ check --

# Real words missing from the hunspell lt_LT lexicon (verified against the
# Pusiaukelė A2 word list, which lists them as required vocabulary). Both
# decline fully regularly, so the paradigms are derived, not guessed.
LEXICON_GAPS = {"skalbykl", "džiovykl", "keitykl", "atidarytuv"}


def check(path=None):
    """Forms in a manual_forms file that hunspell does not know."""
    path = path or paths.MANUAL_FORMS
    forms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = line.split("\t")
        if line.strip() and not line.startswith("#") and len(cells) > 3:
            forms += cells[3].split()
    bad = sorted({w for w in spell.unknown_words("\n".join(forms))
                  if not any(w.startswith(g) for g in LEXICON_GAPS)})
    return forms, bad


# ----------------------------------------------------------------- accent --
# The paradigms in manual_forms.tsv were typed without stress marks, while
# the cards built from Wiktionary carry them on every form of the line
# (žibiñtas / žibiñtai). This closes the gap from sources that have the data.
# It accents EVERY form shown on the card, not just the headword. Column 4
# — the form list used to match and bold the word inside example sentences
# — is deliberately left bare, because example text is written without
# marks and an accented entry there would simply never match.
#
# Every candidate is checked before use: stripping the stress marks off it
# must give back exactly the form it replaces. Where a source offers two
# different accentuations for one spelling — `mes` is both mès and mẽs —
# the form is skipped and reported, because choosing would be guessing.

TODO = paths.OUT / "needs_accents.txt"

# Grave, acute, tilde — the three Lithuanian stress marks, and nothing else.
# The macron U+0304 is part of the LETTER ū, not an accent; counting it as one
# made every word containing ū look already-accented and skipped it silently.
# ltcard.strip_stress() strips exactly these three, so the two agree.
STRESS = {"̀", "́", "̃"}


def stressed(s):
    return any(c in STRESS for c in u.normalize("NFD", s or ""))


def signature(s):
    """'plaukai̇̃' and 'plaukaĩ' are one accentuation spelled two ways."""
    return u.normalize("NFC", "".join(c for c in u.normalize("NFD", s)
                                      if ord(c) != 0x0307))


def display_tokens(forms_line):
    """The forms actually printed on the card.

    Parenthesised notes — `(tik dgs.)`, `(nekait.)` — are the project's own
    annotations, not Lithuanian to be accented.
    """
    return [t for t in re.split(r"[,/ ]+", re.sub(r"\(.*?\)", "", forms_line))
            if t]


def from_kaikki(word):
    entries = ltcard.kaikki_entries(word)
    if not entries:
        return set()
    blob = json.dumps(entries, ensure_ascii=False).replace('","', " ")
    return {t.strip('",:[]{} ') for t in blob.split()
            if stressed(t) and
            ltcard.strip_stress(t.strip('",:[]{} ')).lower() == word}


def from_file(path):
    """Every accented form the file offers, keyed by its bare spelling."""
    out = {}
    if not path.exists():
        return out
    for tok in re.split(r"[\s,;/]+", path.read_text(encoding="utf-8")):
        tok = tok.strip(".:()[]«»„“\"'")
        if tok and stressed(tok):
            out.setdefault(ltcard.strip_stress(tok).lower(), set()).add(tok)
    return out


def place(forms_line, form, accented):
    """Replace `form` wherever it stands, marks and all.

    The form is not always first and not always followed by a space: rows read
    `dujos (tik dgs.)`, `plaukas / plaukai`, `megzti, mezga, mezgė`. Splitting
    on whitespace leaves the comma glued to the token, so this matches on
    Unicode word boundaries instead.
    """
    # The trailing guard must also reject a combining mark: `\w` does not
    # match U+0300, so a bare `taksi` would still match inside an already
    # accented `taksì` and stack a second mark onto it.
    pattern = re.compile(r"(?<!\w)" + re.escape(form) + r"(?![\ẁ-ͯ])",
                         re.UNICODE)
    new, n = pattern.subn(accented, forms_line)
    return new, bool(n)


def accent(dry=False):
    supplied = from_file(paths.ACCENTED)
    lines = paths.MANUAL_FORMS.read_text(encoding="utf-8").splitlines()
    filled, ambiguous, rejected, disagree = [], {}, [], []
    rows_done = rows_partial = 0
    todo_lines, todo_forms = [], set()

    for i, line in enumerate(lines):
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) < 4:
            continue
        word, forms_line = cells[0], cells[2]
        new_line = forms_line
        missing = []

        # dict.fromkeys keeps order while dropping duplicates: an indeclinable
        # noun reads `taksi / taksi`, and processing the form twice used to
        # substitute into its own output
        for form in dict.fromkeys(display_tokens(forms_line)):
            if stressed(form):
                continue
            key = form.lower()
            src_file = supplied.get(key, set())
            src_kaikki = from_kaikki(key) if key == word else set()
            if src_file and src_kaikki and \
                    {signature(h) for h in src_file} != \
                    {signature(h) for h in src_kaikki}:
                disagree.append((form, sorted(src_file), sorted(src_kaikki)))
            hits = src_file or src_kaikki
            if not hits:
                missing.append(form)
                continue
            if len({signature(h) for h in hits}) > 1:
                ambiguous[form] = sorted(hits)
                missing.append(form)
                continue
            accented = sorted(hits, key=len)[0]
            if ltcard.strip_stress(accented).lower() != key:
                rejected.append((form, accented))
                missing.append(form)
                continue
            new_line, hit = place(new_line, form, accented)
            if not hit:
                rejected.append((form, f"not placeable in {forms_line!r}"))
                missing.append(form)
            else:
                filled.append((form, accented))

        if new_line != forms_line:
            cells[2] = new_line
            lines[i] = "\t".join(cells)
        if missing:
            rows_partial += 1
            todo_forms.update(missing)
            # Give the tool the whole paradigm, so it reads `mezga` as a verb
            # rather than a noun — and give it bare, since it expects unmarked
            # input and its answer for a form we already have is checked
            # against ours rather than silently overwriting it.
            todo_lines.append(", ".join(ltcard.strip_stress(t)
                                        for t in display_tokens(forms_line)))
        else:
            rows_done += 1

    if not dry:
        paths.MANUAL_FORMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
        TODO.parent.mkdir(exist_ok=True)
        TODO.write_text(
            "# Paradigms that still have unaccented forms — EVERY form printed\n"
            "# on a card should carry its stress mark, not just the headword.\n"
            "#\n"
            "# Paste everything below the comments into VDU's Kirciuoklis\n"
            "#   https://kalbu.vdu.lt/mokymosi-priemones/kirciuoklis/\n"
            "# save its output as data/accented.txt, then rerun\n"
            "#   python3 scripts/forms.py accent\n"
            "#\n"
            "# Whole paradigm lines are given rather than loose words so the\n"
            "# tool can tell a verb form from a same-spelled noun. The output\n"
            "# is read as a bag of forms, so its layout does not matter.\n"
            + "\n".join(todo_lines) + "\n", encoding="utf-8")

    print(f"{len(filled)} form(s) accented across the paradigms")
    print(f"complete lines: {rows_done}; still missing something: {rows_partial}"
          f" ({len(todo_forms)} distinct form(s))")
    for f, a in filled[:10]:
        print(f"  {f:16s} -> {a}")
    if ambiguous:
        print(f"\n{len(ambiguous)} form(s) skipped — the source gives more than "
              f"one accentuation, so choosing would be guessing:")
        for f, hits in list(ambiguous.items())[:15]:
            print(f"  {f:16s} {' / '.join(hits)}")
    if rejected:
        print(f"\n{len(rejected)} candidate(s) rejected by the safety check:")
        for f, why in rejected[:15]:
            print(f"  {f:16s} {why}")
    if disagree:
        print(f"\n{len(disagree)} form(s) where accented.txt and kaikki "
              f"disagree — accented.txt was used, worth a look:")
        for f, s, k in disagree:
            print(f"  {f:16s} accented.txt {'/'.join(s)}  vs  kaikki {'/'.join(k)}")
    if not dry:
        print(f"\n{len(todo_lines)} paradigm line(s) to run through Kirciuoklis "
              f"-> {TODO}")
    return 0


# ------------------------------------------------------------------- main --

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="a manual_forms.tsv row for a regular word")
    d.add_argument("word")
    d.add_argument("pos", choices=["noun", "verb"])
    c = sub.add_parser("check", help="hunspell-verify every form")
    c.add_argument("file", nargs="?")
    a = sub.add_parser("accent", help="stress marks on every form shown")
    a.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "draft":
        row = draft(args.word, args.pos)
        if not row:
            print(f"# no pattern matched for {args.word} ({args.pos}) — "
                  f"fill by hand", file=sys.stderr)
            return 1
        print(row)
        return 0
    if args.cmd == "check":
        from pathlib import Path
        forms, bad = check(Path(args.file) if args.file else None)
        print(f"{len(forms)} forms checked; {len(bad)} unknown to hunspell")
        if bad:
            print("UNKNOWN:", bad)
            return 1
        return 0
    return accent(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
