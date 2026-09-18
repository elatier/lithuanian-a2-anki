#!/usr/bin/env python3
"""gen_forms.py WORD POS — generate regular Lithuanian inflections.

Detects the declension/conjugation pattern from the ending and expands it.
Output is a manual_forms.tsv line; EVERY generated form is then checked by
check_forms.py against the hunspell lexicon, so wrong patterns are caught
rather than shipped. Irregular words will fail that check — fill by hand.
"""
import sys

NOUN = {
    "as":  ("as o ui ą u e", "ai ų ams us ais uose"),          # namas
    "is":  ("is io iui į iu yje", "iai ių iams ius iais iuose"), # brolis
    "ys":  ("ys io iui į iu yje", "iai ių iams ius iais iuose"), # arklys
    "us":  ("us aus ui ų umi uje", "ūs ų ums us umis uose"),     # sūnus
    "a":   ("a os ai ą a oje", "os ų oms as omis ose"),          # knyga
    "ė":   ("ė ės ei ę e ėje", "ės ių ėms es ėmis ėse"),         # gėlė
}
VERB = {  # infinitive ending -> (pres3, past3) stem rules
    "yti": ("o", "ė"), "ėti": ("i", "ėjo"), "oti": ("oja", "ojo"),
    "uoti": ("uoja", "avo"), "auti": ("auja", "avo"), "inti": ("ina", "ino"),
}

def noun(word):
    for end, (sg, pl) in NOUN.items():
        if word.endswith(end):
            stem = word[: -len(end)]
            sgf = [stem + e for e in sg.split()]
            plf = [stem + e for e in pl.split()]
            return f"{sgf[0]} / {plf[0]}", sgf + plf
    return None, None

def verb(word):
    for end, (p3, t3) in VERB.items():
        if word.endswith(end):
            stem = word[: -len(end)]
            pres = stem + (end[:-2] + p3 if len(p3) == 1 else p3)
            past = stem + t3
            return f"{word}, {pres}, {past}", [word, pres, past]
    return None, None

w, pos = sys.argv[1], sys.argv[2]
line, forms = (noun(w) if pos == "noun" else verb(w))
if not line:
    print(f"# no pattern matched for {w} ({pos}) — fill by hand", file=sys.stderr)
    sys.exit(1)
print(f"{w}\t{pos}\t{line}\t{' '.join(forms)}")
