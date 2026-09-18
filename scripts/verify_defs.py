#!/usr/bin/env python3
"""
verify_defs.py — automated QA for the batch files before any deck is built.

Checks per word (no human input needed):
  1. SPELL   every Lithuanian word in the definition and example exists
             (hunspell lt_LT; capitalized words treated as proper nouns)
  2. GLOSS   the one-word English translation is anchored in the word's
             Wiktionary glosses (independent, verifiable source)
  3. LEAK    definition contains no inflected form of the headword
  4. FORM    example contains at least one inflected form of the headword
  5. A2      definition+example vocabulary stays inside the deck's own
             words (every inflected form, from the cached Wiktionary
             entries, manual_forms.tsv and forms_cache.json) + function
             words + the documented extras in extra_def_vocab.tsv
  6. LEN     definition is short enough for A2 (warn > 12 tokens)
  7. THEME   column 8 names a theme from data/THEMES.md
  8. ROOT    definition shares no root with the headword (warn: a
             derivation like augalas ~ auga gives card 2 away, but a
             shared prefix is not a shared root, so this is for review;
             a hit judged harmless is listed in root_reviewed.tsv)

Also writes out/review.txt: word | draft def | Wiktionary glosses | EN —
side by side, so human spot-checking a sample takes seconds per word.

Usage: python3 scripts/verify_defs.py                            # every batch
       python3 scripts/verify_defs.py data/batches/batch32.tsv   # just one
Exit code 1 if any hard check (SPELL/GLOSS/LEAK/FORM/QUAL/HEAD/THEME) fails.
"""
import functools
import json
import re
import sys
import unicodedata
from pathlib import Path

import ltcard
import paths
import spell

# The gate used to check only what a human wrote (definition, example,
# translation) and never the GENERATED parts of a card — the headword as it is
# displayed and spoken, and the inflection line. kaikki.org glues annotation
# onto canonical forms ("sakinỹs m stress pattern 3ᵇ"), and a mis-parsed table
# yields a forms line full of header text. Both reach the card and the
# synthesiser, so they are checked here too.
JUNK_IN_HEAD = re.compile(
    r"stress pattern|declension|conjugation|inflection|singular|plural|"
    r"masculine|feminine|neuter|\bm\b|\bf\b|\bn\b|[0-9]|[ᵃᵇᶜᵈ]", re.I)
# legitimate annotations the project adds itself
HEAD_OK = re.compile(r"\(tik dgs\.\)|\(nekait\.\)")


def _flatten(text):
    """Drop combining marks before the junk test.

    A combining accent is not a word character, so `mán,` looks to `\\b` like a
    standalone `n` and tripped the `\\bn\\b` rule meant to catch Wiktionary's
    gender annotation. Removing the marks — `mán` -> `man` — restores real word
    boundaries while leaving the junk itself ("stress pattern", "m", digits)
    exactly as detectable.
    """
    import unicodedata
    return unicodedata.normalize(
        "NFC", "".join(c for c in unicodedata.normalize("NFD", text or "")
                       if not unicodedata.combining(c)))


def head_problems(key, d, manual):
    """Check the generated headword and forms line, as ltcard.py builds them."""
    word = d.get("headword") or key.split("#")[0]
    out = []
    if word in manual:
        forms_line, canon = manual[word]["forms_line"], word
    else:
        entries = ltcard.kaikki_entries(word)
        poses = {e.get("pos") for e in entries} & ltcard.POSES
        if d.get("pos"):
            poses &= {d["pos"]}
        forms_line = canon = None
        for table in ltcard.wikt_lt_tables(word):
            kind = ltcard.classify_table(table)
            if kind not in poses:
                continue
            canon = ltcard.canonical(entries, kind, word)
            if kind == "noun":
                forms_line = ltcard.noun_compact(table)
            elif kind == "verb":
                forms_line = ltcard.verb_compact(table, canon)
            else:
                fem = ltcard.feminine(entries)
                forms_line = f"{canon} / {fem}" if fem else canon
            break
        if forms_line is None:
            return ["HEAD: no usable inflection table or manual forms — "
                    "ltcard.py would skip this word"]
    for label, value in (("forms line", forms_line), ("headword", canon)):
        if value and JUNK_IN_HEAD.search(_flatten(HEAD_OK.sub("", value))):
            out.append(f"HEAD: {label} looks mis-parsed: {value!r}")
    if not forms_line:
        out.append("HEAD: empty forms line")
    return out

# Proper nouns are data/proper_nouns.txt; the words that always count as
# known A2 vocabulary are data/function_words.txt; the accepted translations
# the GLOSS check cannot verify are data/gloss_overrides.tsv.
PROPER_NOUNS = ltcard.load_word_set(paths.PROPER_NOUNS)

SENT = re.compile(r"(?<=[.!?])\s+")


def meaningful_caps(text):
    """Capitalised tokens whose capital is not just sentence position."""
    out = set()
    for sent in SENT.split(text):
        for i, tok in enumerate(ltcard.tokenize(sent)):
            if tok[:1].isupper() and (i > 0 or tok.lower() in PROPER_NOUNS):
                out.add(tok.lower())
    return out


def spell_unknown(text, headword_forms=frozenset()):
    """Unknown words, excusing genuine proper nouns and the headword itself.

    A few A2 words (skalbyklė, džiovyklė, keitykla) are simply absent from the
    lt_LT lexicon — check_forms.py already tracks these as LEXICON_GAPS. Their
    inflections are verified when the paradigm is written, so an example
    sentence must not fail merely for containing the word it is illustrating.
    """
    proper = meaningful_caps(text)
    return sorted({w for w in spell.unknown_words(text)
                   if w and w.lower() not in headword_forms
                   and (not w[0].isupper() or w.lower() not in proper)})


# ---- ROOT: a definition that shares a root with its headword ------------
# Exact inflected forms are LEAK; this is the weaker, still card-breaking
# case of a derivationally related word (mokytojas -> mokykla, gėlė ->
# gėlių, valgyti -> valgis) in the definition. Heuristic: longest common
# prefix after folding the consonant/vowel alternations that break a naive
# prefix match, plus a compound's embedded stem (senamiestis ~ miesto).

_FOLD = str.maketrans({"č": "t", "ę": "e", "ė": "e", "į": "i",
                       "ų": "u", "ū": "u", "y": "i", "š": "s", "ž": "z",
                       "ą": "a", "o": "a"})


def _norm(w):
    w = unicodedata.normalize("NFC", ltcard.strip_stress(w).lower())
    return w.replace("dž", "d").translate(_FOLD)


def shared_root(head, tok):
    """Shared root length if `tok` looks derivationally related to `head`,
    else 0."""
    h, t = _norm(head), _norm(tok)
    if len(t) < 3:
        return 0
    n = 0
    for x, y in zip(h, t):
        if x != y:
            break
        n += 1
    if n >= 4 and (n >= 0.6 * len(h) or n >= 0.6 * len(t)):
        return n
    if n >= 5:
        return n
    for k in range(len(t), 3, -1):          # embedded stem of a compound
        if t[:k] in h:
            return k
    return 0


@functools.lru_cache(maxsize=1)
def known_vocabulary():
    """Every word form a definition or example may use.

    The deck's own vocabulary: each headword and all its inflected forms,
    from the cached Wiktionary entries (data/cache/kaikki) or from
    manual_forms.tsv for the words Wiktionary has no table for, so a new
    word's forms count as soon as its card exists; the paradigms in
    forms_cache.json, fetched for the original A2 word list, which hold
    fuller tables for some words than the caches do now and a few words
    the definitions use but the deck no longer teaches; the grammar words
    in function_words.txt; and the documented extras in
    extra_def_vocab.tsv — words allowed inside definitions but not taught
    as cards, because the A2-only restriction made ~20 synonym pairs
    mutually ambiguous on the definition->word card.
    """
    known = ltcard.load_word_set(paths.FUNCTION_WORDS)
    if paths.FORMS_CACHE.exists():
        cache = json.load(open(paths.FORMS_CACHE, encoding="utf-8"))
        known |= set(cache) | {f for v in cache.values() for f in v}
    manual = ltcard.load_manual_forms()
    for f in paths.batch_files():
        for key in ltcard.load_defs(str(f)):
            head = key.split("#")[0]
            known.add(head)
            if head in manual:
                known |= manual[head]["forms"]
            else:
                entries = ltcard.kaikki_entries(head)
                for pos in ltcard.POSES:
                    known |= ltcard.all_word_forms(entries, pos)
    for m in manual.values():
        known |= m["forms"]
    extra = paths.EXTRA_DEF_VOCAB
    if extra.exists():
        for line in extra.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                lemma, _, forms = line.partition("\t")
                known.add(lemma.strip().lower())
                known |= {f.lower() for f in forms.split()}
    return known


@functools.lru_cache(maxsize=1)
def root_reviewed():
    """{(key, token)} ROOT hits a person has judged harmless."""
    out = set()
    if paths.ROOT_REVIEWED.exists():
        for line in paths.ROOT_REVIEWED.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                key, _, rest = line.partition("\t")
                out.add((key.strip(), rest.split("\t")[0].strip().lower()))
    return out


def check(path):
    """Print the report for one batch; return (hard_fail, review entries)."""
    defs = ltcard.load_defs(path)
    known = known_vocabulary()
    reviewed = root_reviewed()
    hard_fail = False
    review = []
    manual = ltcard.load_manual_forms()
    overrides = ltcard.load_gloss_overrides()
    for word, d in defs.items():
        # `word` may be a keyed sense variant (`žibintas#auto`); every
        # linguistic lookup uses the bare headword.
        head = d.get("headword") or word.split("#")[0]
        qualifier = d.get("qualifier", "")
        entries = ltcard.kaikki_entries(head)
        poses = {e.get("pos") for e in entries} & ltcard.POSES
        if d.get("pos"):
            poses &= {d["pos"]}
        problems = []
        is_manual = head in manual

        forms = set()
        for p in poses:
            forms |= ltcard.all_word_forms(entries, p)
        if is_manual:
            forms = manual[head]["forms"]

        # 1 SPELL
        bad = spell_unknown(f'{d["lt_def"]} {d["lt_example"]}', forms)
        if bad:
            problems.append(f"SPELL: unknown word(s) {bad}")

        # 2 GLOSS anchor
        glosses = " ; ".join(ltcard.wikt_gloss(entries, p, n=4)
                             for p in poses).lower()
        if is_manual:
            glosses = "(manual forms — no Wiktionary entry; "\
                      "translation relies on spot-check)"
        enw = d["en_word"].lower().replace("to ", "")
        ov = overrides.get(word, overrides.get(head))
        if ov is not None:
            # normalise the override the same way enw was, or a capitalised
            # or "to "-prefixed override can never match and silently falls
            # through to the substring test it was meant to bypass
            ov = ov.lower().replace("to ", "")
        if is_manual or (ov is not None and enw == ov):
            enw = ""          # manual word or accepted documented override
        if enw and enw not in glosses:
            problems.append(f"GLOSS: '{d['en_word']}' not found in "
                            f"Wiktionary glosses [{glosses[:90]}]")

        # 3 LEAK + 4 FORM + 5 A2
        leak = [t for t in ltcard.tokenize(d["lt_def"].lower())
                if t in forms]
        if leak:
            problems.append(f"LEAK: definition contains {leak}")
        _, found = ltcard.bold_word(d["lt_example"], forms)
        if not found:
            problems.append("FORM: no inflected form of headword in example")

        # ORDER heuristic: headword's relative position should be similar
        # in the LT example and its EN translation
        if found and d["en_example"] and d["en_word"]:
            lt_toks = [t.lower() for t in ltcard.tokenize(d["lt_example"])]
            en_toks = [t.lower() for t in ltcard.tokenize(d["en_example"])]
            lt_pos = next((i for i, t in enumerate(lt_toks) if t in forms), None)
            enw_last = d["en_word"].lower().split()[-1]
            en_pos = next((i for i, t in enumerate(en_toks)
                           if t.startswith(enw_last[:5])), None)
            if lt_pos is not None and en_pos is not None and \
               len(lt_toks) > 2 and len(en_toks) > 2:
                drift = abs(lt_pos / (len(lt_toks) - 1)
                            - en_pos / (len(en_toks) - 1))
                if drift > 0.34:
                    problems.append(
                        f"ORDER: headword moved (LT pos {lt_pos+1}/"
                        f"{len(lt_toks)}, EN pos {en_pos+1}/{len(en_toks)}) "
                        f"— keep Lithuanian word order where possible")
        if known:
            raw = d["lt_def"] + " " + d["lt_example"]
            capitalized = meaningful_caps(raw)
            def is_known(t):
                if t in known or t in forms:
                    return True
                if t in capitalized:          # proper nouns / sentence names
                    return True
                for pref in ("nebe", "ne"):   # negated verb forms
                    if t.startswith(pref) and t[len(pref):] in known:
                        return True
                return False
            off = sorted({t for t in ltcard.tokenize(raw.lower())
                          if len(t) > 2 and not is_known(t)})
            if off:
                problems.append(f"A2: off-list vocabulary {off}")

        # HEAD: the generated headword / inflection line
        problems += head_problems(word, d, manual)

        # QUAL: the disambiguating word must not appear in the definition
        if qualifier:
            qt = {t_.lower() for t_ in ltcard.tokenize(qualifier)}
            hit = [t_ for t_ in ltcard.tokenize(d["lt_def"].lower())
                   if t_ in qt]
            if hit:
                problems.append(f"QUAL: definition contains the "
                                f"disambiguating word {hit}")

        # ROOT: a same-root word in the definition (review, not a failure)
        shared = [f"{t} (+{n})" for t in ltcard.tokenize(d["lt_def"])
                  for n in [shared_root(head, t)]
                  if n and (word, t.lower()) not in reviewed]
        if shared:
            problems.append(f"ROOT: definition shares a root with the "
                            f"headword: {', '.join(shared)}")

        # THEME: the row's theme must be one of the taxonomy's slugs
        if not d.get("theme"):
            problems.append("THEME: no theme in column 8 (slugs in data/THEMES.md)")
        elif d["theme"] not in ltcard.theme_tags():
            problems.append(f"THEME: unknown theme {d['theme']!r} "
                            f"(slugs in data/THEMES.md)")

        # 6 LEN
        if len(d["lt_def"].split()) > 12:
            problems.append(f"LEN: definition {len(d['lt_def'].split())} "
                            f"words (>12)")

        status = "OK " if not problems else "FAIL" if any(
            p.split(":")[0] in ("SPELL", "GLOSS", "LEAK", "FORM", "QUAL",
                                "HEAD", "THEME")
            for p in problems) else "WARN"
        if status == "FAIL":
            hard_fail = True
        print(f"[{status}] {word}")
        for p in problems:
            print(f"       {p}")
        review.append(f"{word}\n  LT def : {d['lt_def']}\n"
                      f"  Wikt   : {glosses}\n"
                      f"  EN     : {d['en_word']} — {d['en_def']}\n"
                      f"  Pvz    : {d['lt_example']}\n"
                      f"  Pvz EN : {d['en_example']}\n")
    return hard_fail, review


def main(files):
    failed, review = [], []
    for f in files:
        print(f"=== {Path(f).name}")
        bad, rev = check(f)
        review += rev
        if bad:
            failed.append(Path(f).name)
    out = paths.OUT / "review.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(review), encoding="utf-8")
    print(f"\n{out.name} written ({len(review)} words).")
    if failed:
        print(f"FAIL in {len(failed)} file(s): {', '.join(failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:] or [str(p) for p in paths.batch_files()])
