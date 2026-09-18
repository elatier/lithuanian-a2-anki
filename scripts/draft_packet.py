#!/usr/bin/env python3
"""draft_packet.py WORD [--theme SLUG] [--vocab] — everything a drafter needs
to write the card for WORD, on one screen. `add_word.py WORD --new` prints
the same before it scaffolds the row; this is the packet on its own.

Whoever writes the row — a person, or Claude via the add-word skill — starts
from the same facts: what Wiktionary says the word means and how it inflects,
which theme it belongs to and how that theme's cards read, which existing
cards share its English answer (their definitions must stay distinct), and
what vocabulary a definition may use. The gate then checks the result; this
just makes a good first draft likely.

    python3 scripts/draft_packet.py lentyna
    python3 scripts/draft_packet.py lentyna --theme 02
    python3 scripts/draft_packet.py lentyna --vocab      # also list the A2 lemmas

A word not yet in the caches costs one kaikki.org and one Wiktionary lookup;
the answers are cached under data/cache/ for the build.
"""
import argparse
import re
import sys

import ltcard
import paths

POS_NAMES = {"noun": "daiktavardis", "verb": "veiksmažodis", "adj": "būdvardis"}


def known_lemmas():
    """The lemmas a definition may use: the deck's headwords, the grammar
    words and the documented extras (their inflected forms count too)."""
    lemmas = {k.split("#")[0] for f in paths.batch_files()
              for k in ltcard.load_defs(str(f))}
    lemmas |= set(ltcard.load_manual_forms())
    if paths.EXTRA_DEF_VOCAB.exists():
        for line in paths.EXTRA_DEF_VOCAB.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                lemmas.add(line.split("\t")[0].strip().lower())
    lemmas |= ltcard.load_word_set(paths.FUNCTION_WORDS)
    return lemmas


def all_cards():
    for f in paths.batch_files():
        for key, d in ltcard.load_defs(str(f)).items():
            yield f.name, key, d


def forms_line_for(word, entries, pos, manual):
    """The inflection line ltcard.py would print, or None if it has nothing."""
    if word in manual:
        return manual[word]["forms_line"]
    for table in ltcard.wikt_lt_tables(word):
        if ltcard.classify_table(table) != pos:
            continue
        canon = ltcard.canonical(entries, pos, word)
        if pos == "noun":
            return ltcard.noun_compact(table) or None
        if pos == "verb":
            return ltcard.verb_compact(table, canon) or None
        fem = ltcard.feminine(entries)
        return f"{canon} / {fem}" if fem else canon
    return None


def gloss_heads(en_word):
    """Bare English heads of a gloss list, for collision matching."""
    out = set()
    for part in re.split(r"[;,/]", re.sub(r"\([^)]*\)", " ", en_word or "")):
        part = re.sub(r"^(to|a|an|the)\s+", "", part.strip(), flags=re.I).strip().lower()
        if part:
            out.add(part)
    return out


def packet(word, theme=None, vocab=False, next_steps=True):
    """Print the packet. `theme` is a column-8 slug (resolved), or None."""
    word = word.strip().lower()
    manual = ltcard.load_manual_forms()
    themes = ltcard.load_themes()
    theme_map = ltcard.theme_tags()
    p = print

    p(f"=== {word}")
    existing = [(f, k, d) for f, k, d in all_cards() if k.split("#")[0] == word]
    if existing:
        p(f"ALREADY IN THE DECK — {len(existing)} card(s):")
        for f, k, d in existing:
            p(f"  {f}: {k}\t{d['lt_def']}\t{d['en_word']}")
        p("  A second sense needs a `headword#sense` key and a qualifier "
          "(README, 'The card format').")

    # --- what Wiktionary knows
    entries = ltcard.kaikki_entries(word)
    poses = sorted({e.get("pos") for e in entries} & ltcard.POSES)
    p("\n--- Wiktionary (via kaikki.org)")
    if not entries:
        p("  no entry. The GLOSS check cannot verify a translation; if there "
          "is no inflection table either, the word needs a manual_forms.tsv "
          "row (forms.py draft).")
    other = sorted({e.get("pos") for e in entries} - ltcard.POSES - {None})
    if other:
        p(f"  entries for other parts of speech: {', '.join(other)} "
          f"(a card for these needs manual_forms.tsv and pos in the row)")
    glosses_all = set()
    for pos in poses:
        canon = ltcard.canonical(entries, pos, word)
        gl = ltcard.wikt_gloss(entries, pos, n=6)
        glosses_all |= gloss_heads(gl)
        p(f"  {pos} ({POS_NAMES[pos]}) — headword {canon}")
        p(f"    glosses: {gl}")
        line = forms_line_for(word, entries, pos, manual)
        if line:
            p(f"    forms line on the card: {line}"
              + ("   [manual_forms.tsv]" if word in manual else ""))
        else:
            p("    NO INFLECTION TABLE on Wiktionary: write the paradigm "
              "into manual_forms.tsv (forms.py draft / check / accent) "
              "before the gate will pass.")
        forms = []
        for e in entries:
            if e.get("pos") != pos:
                continue
            for f in e.get("forms", []):
                tags = [t for t in (f.get("tags") or [])
                        if t not in ("canonical", "table-tags", "inflection-template")]
                if not f.get("form") or "dual" in tags or "alternative" in tags:
                    continue
                if f.get("source") == "inflection" or tags:
                    forms.append((ltcard.strip_stress(f["form"]), " ".join(tags)))
        seen, shown = set(), []
        for form, tags in forms:
            if form not in seen and form != word:
                seen.add(form)
                shown.append(f"{form} ({tags})" if tags else form)
        if shown:
            p("    inflected forms for the example (use one of these, not "
              "the dictionary form):")
            for i in range(0, min(len(shown), 24), 3):
                p("      " + " · ".join(shown[i:i + 3]))
            if len(shown) > 24:
                p(f"      … {len(shown) - 24} more")
    if word in manual and not poses:
        m = manual[word]
        p(f"  manual_forms.tsv: {m['pos']} — {m['forms_line']}")
        p(f"    forms: {' '.join(sorted(m['forms']))}")

    # --- theme
    p("\n--- theme")
    theme = themes.get(word) or (theme_map.get(theme) if theme else None)
    if word in themes:
        p(f"  the card's row says {theme}")
    elif theme:
        p(f"  chosen: {theme}")
    else:
        p("  none yet. Pick exactly one for column 8 (THEMES.md: prefer the "
          "concrete situation a learner meets the word in):")
        for tag, covers in ltcard.theme_table():
            p(f"    {tag.split('::', 1)[1]:26} {covers}")

    # --- neighbours: how cards in this theme read
    if theme:
        want = poses[0] if poses else (manual.get(word) or {}).get("pos")
        rows = [(k, d) for _, k, d in all_cards()
                if themes.get(k.split("#")[0]) == theme]
        rows.sort(key=lambda kd: (kd[1]["pos"] != want, kd[0]))
        p(f"\n--- {len(rows)} cards already in {theme}; the register to match:")
        for k, d in rows[:4]:
            p(f"  {k}\t{d['lt_def']}\t{d['en_word']}\t{d['lt_example']}\t"
              f"{d['en_example']}")

    # --- collisions on the English answer
    coll = [(k, d) for _, k, d in all_cards()
            if k.split("#")[0] != word and gloss_heads(d["en_word"]) & glosses_all]
    if coll:
        p("\n--- cards that already answer with one of these glosses "
          "(their definitions must stay distinguishable from yours):")
        for k, d in coll[:8]:
            p(f"  {k}\t{d['en_word']}\t{d['lt_def']}")

    # --- vocabulary
    lemmas = known_lemmas()
    p(f"\n--- vocabulary: {len(lemmas)} lemmas may appear in the definition "
      f"and example (their inflected forms too); anything else is an A2 "
      f"warning. --vocab lists them." if not vocab else
      f"\n--- {len(lemmas)} lemmas a definition may use:")
    if vocab:
        words = sorted(lemmas)
        for i in range(0, len(words), 10):
            p("  " + " ".join(words[i:i + 10]))

    if not next_steps:
        return 0
    p("\n--- next")
    if existing:
        p(f"  edit the row in {existing[0][0]}, then")
        p(f"  python3 scripts/add_word.py {word}          # check, record, build")
        return 0
    p(f"  python3 scripts/add_word.py {word} --new"
      + (f" --pos {poses[0]}" if len(poses) == 1 else " --pos POS")
      + (f" --theme {theme.split('::')[1]}" if theme else " --theme SLUG")
      + "    # scaffolds the row")
    p("  fill lt_def, en_def, lt_example, en_example (data/DRAFTING_GUIDE.md), then")
    p(f"  python3 scripts/add_word.py {word}          # check, record, build")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("word")
    ap.add_argument("--theme", help="theme slug, full or partial")
    ap.add_argument("--vocab", action="store_true",
                    help="also list every lemma a definition may use")
    args = ap.parse_args()
    theme = None
    if args.theme:
        try:
            theme = ltcard.resolve_theme(args.theme)
        except LookupError as exc:
            print(exc)
    return packet(args.word, theme, args.vocab)


if __name__ == "__main__":
    sys.exit(main())
