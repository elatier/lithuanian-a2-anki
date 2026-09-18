#!/usr/bin/env python3
"""apply_accents.py — put stress marks on the hand-written paradigms.

The paradigms in manual_forms.tsv were typed for words Wiktionary has no
declension table for, and typed without stress marks — while the cards
built from Wiktionary carry them on every form of the line (žibiñtas / žibiñtai).
This closes the gap from sources that actually have the data, and refuses to
invent the rest.

It accents EVERY form shown on the card, not just the headword: a line reading
`ponià / ponios` is still half done. Column 4 of manual_forms.tsv — the form
list used to match and bold the word inside example sentences — is deliberately
left bare, because example text is written without marks and an accented entry
there would simply never match.

Two sources, in order:

  1. accented.txt — produced by a human with VDU's Kirčiuoklis
     (https://kalbu.vdu.lt/mokymosi-priemones/kirciuoklis/), the standard
     Lithuanian accentuation tool. Paste in the contents of out/needs_accents.txt
     (which lists whole paradigm lines, so the tool sees `megzti, mezga, mezgė`
     as a verb rather than three loose words) and save the output here. Format
     is free: the file is read as a bag of accented word forms, in any order,
     newlines or not.

  2. kaikki.org — the same source the rest of the deck uses. A word may have an
     accented headword there even with no inflection table, which is exactly
     the case for these words.

Every candidate is checked before use: stripping the stress marks off it must
give back exactly the form it replaces. Where a source offers two different
accentuations for one spelling — `mes` is both mès and mẽs — the form is
skipped and reported, because choosing would be guessing.

    python3 scripts/apply_accents.py
    python3 scripts/apply_accents.py --dry-run
"""
import json
import re
import sys
import unicodedata as u

import ltcard
import paths

MANUAL = paths.MANUAL_FORMS
SUPPLIED = paths.ACCENTED
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
    pattern = re.compile(r"(?<!\w)" + re.escape(form) + r"(?![\w\u0300-\u036f])",
                         re.UNICODE)
    new, n = pattern.subn(accented, forms_line)
    return new, bool(n)


def main():
    dry = "--dry-run" in sys.argv
    supplied = from_file(SUPPLIED)
    lines = MANUAL.read_text(encoding="utf-8").splitlines()
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
        MANUAL.write_text("\n".join(lines) + "\n", encoding="utf-8")
        TODO.parent.mkdir(exist_ok=True)
        TODO.write_text(
            "# Paradigms that still have unaccented forms — EVERY form printed\n"
            "# on a card should carry its stress mark, not just the headword.\n"
            "#\n"
            "# Paste everything below the comments into VDU's Kirciuoklis\n"
            "#   https://kalbu.vdu.lt/mokymosi-priemones/kirciuoklis/\n"
            "# save its output as data/accented.txt, then rerun\n"
            "#   python3 scripts/apply_accents.py\n"
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


if __name__ == "__main__":
    main()
