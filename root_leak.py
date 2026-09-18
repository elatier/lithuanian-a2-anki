#!/usr/bin/env python3
"""root_leak.py FILE.tsv ... — find definitions sharing a ROOT with the headword.

verify_defs.py only blocks exact inflected forms of the headword. This catches
the weaker but still card-breaking case: a derivationally related word
(mokytojas -> mokykla, gėlė -> gėlių, valgyti -> valgis) sitting in the
definition, which gives the answer away on card 2.

Heuristic: longest common prefix between the (stress-stripped, lowercased)
headword and each definition token, after folding the handful of Lithuanian
consonant/vowel alternations that break a naive prefix match.
"""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ltcard

# fold alternations so tokens of one root still share a prefix
FOLD = str.maketrans({"č": "t", "ę": "e", "ė": "e", "į": "i",
                      "ų": "u", "ū": "u", "y": "i", "š": "s", "ž": "z",
                      "ą": "a", "o": "a"})


def norm(w):
    w = ltcard.strip_stress(w).lower()
    w = unicodedata.normalize("NFC", w)
    return w.replace("dž", "d").translate(FOLD)


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def flag(head, tok):
    """Return the shared root length if tok looks derivationally related.

    Two ways a root can be shared:
      (a) common prefix        gėlė ~ gėlių, augalas ~ auga
      (b) embedded stem        senamiestis ~ miesto, prieškambaris ~ kambarys
          (the compound's second element is the definition's word)
    """
    h, t = norm(head), norm(tok)
    if len(t) < 3:
        return 0
    n = lcp(h, t)
    if n >= 4 and (n >= 0.6 * len(h) or n >= 0.6 * len(t)):
        return n
    if n >= 5:
        return n
    # (b) embedded: does a >=4-char stem of the token sit inside the headword?
    for k in range(len(t), 3, -1):
        if t[:k] in h:
            return k
    return 0


def main(paths):
    hits = []
    for path in paths:
        defs = ltcard.load_defs(path)
        for word, d in defs.items():
            head = d.get("headword") or word.split("#")[0]
            shared = []
            for tok in ltcard.tokenize(d["lt_def"]):
                n = flag(head, tok)
                if n:
                    shared.append((tok, n))
            if shared:
                hits.append((Path(path).name, word, d, shared))
    for f, word, d, shared in hits:
        toks = ", ".join(f"{t} (+{n})" for t, n in shared)
        print(f"{f}\t{word}\t{toks}\n    LT : {d['lt_def']}\n"
              f"    EN : {d['en_word']} — {d['en_def']}\n"
              f"    Pvz: {d['lt_example']}\n")
    print(f"{len(hits)} definition(s) share a root with their headword.")


if __name__ == "__main__":
    main(sys.argv[1:])
