---
name: add-word
description: Add words to the deck end to end — one word, or a batch from a list. Draft the cards from the drafting packets, pass the QA gate, record the audio, build, update the numbers, commit. Use when asked to add, draft or create cards for Lithuanian words.
---

# Add words: $ARGUMENTS

The scripts do everything mechanical; you write four columns of Lithuanian
and English per word and fix what the gate rejects. Run straight through:
no checkpoint. The user reads the finished cards in your final report and
in the commit, and corrects them afterwards if needed.

The argument is either words (`slėnis`, `slėnis žvakidė`) or a file of
`word <TAB> theme [<TAB> pos]` lines. Several words are a batch: scaffold
them together into one new batch file, draft them all, check the file as a
whole, and stop once.

## 0. Environment

If `.venv/bin/python` is missing or `hunspell` is not on the path, run
`./setup.sh` (it may need the user's approval to install hunspell; the
dictionary is in the repo). Use `.venv/bin/python` for every script below.

## 1. Read the packet for each word

```bash
.venv/bin/python scripts/draft_packet.py WORD
```

Read all of it. It tells you whether the word already has a card, what
Wiktionary says it means and how it inflects, which theme it is in or which
to choose, how that theme's cards read, and which cards already answer
with the same English word.

- **Already in the deck**: leave it out and tell the user, unless they
  asked for a second sense (key it `WORD#sense`, give both rows a
  qualifier, keep the primary sense on the bare key — README, "The card
  format").
- **No inflection table**: the paradigm goes in `data/manual_forms.tsv`.
  Draft it with `gen_forms.py WORD POS`, run `check_forms.py`, then
  `apply_accents.py`. Stress marks that neither source has must come from
  the VDU Kirčiuoklis; the script writes `out/needs_accents.txt` for the
  user to paste there. Say so, and never invent an accent.

## 2. Choose the theme and the part of speech

One theme per word, from the packet's list, following `data/THEMES.md`:
prefer the concrete situation a learner meets the word in. If the user's
list gives themes, use them. The part of speech is the Wiktionary one the
card teaches.

## 3. Scaffold

One word:

```bash
.venv/bin/python scripts/add_word.py WORD --new --pos POS --theme SLUG
```

A batch: write `out/words.tsv` with one `word<TAB>theme[<TAB>pos]` line per
word (or use the user's file), then

```bash
.venv/bin/python scripts/add_word.py --new --list out/words.tsv
```

which creates the next `data/batches/batchNN.tsv` with a prefilled row per
word and lists every word under its theme.

## 4. Write the four columns

Edit each row: `lt_def`, `en_def`, `lt_example`, `en_example`. Follow
`data/DRAFTING_GUIDE.md` and the register of the neighbouring cards in
the packet. In short:

- Definition for an A2 learner: concrete, 5–9 words, one clause plus an
  optional clarifying clause after `;` or `–`. No form of the headword, no
  word of the same root, no compound part. Only the packet's vocabulary.
- If another card answers with the same English word, the two definitions
  must be distinguishable. Within a batch, the same applies between the
  new cards.
- Example uses an **inflected** form from the packet, not the dictionary
  form. English keeps Lithuanian word order where English allows.
- `en_word` is one of the Wiktionary glosses; verbs as `to run`. If
  Wiktionary's wording is deficient, add a row to
  `data/gloss_overrides.tsv` with the reason.
- `en_def` is a plain rendering of `lt_def`.

## 5. Run the gate until it passes

One word:

```bash
.venv/bin/python scripts/add_word.py WORD --no-audio
```

A batch, as one unit:

```bash
.venv/bin/python scripts/verify_defs.py data/batches/batchNN.tsv
.venv/bin/python scripts/root_leak.py data/batches/batchNN.tsv
```

Fix every `[FAIL]` (SPELL, GLOSS, LEAK, FORM, QUAL, HEAD) and every
`[WARN]` that is easy (LEN, A2, ORDER). Root-leak hits are for judgement:
a shared prefix is not a shared root. Rerun after each edit.

## 6. Record, build, update the numbers

```bash
.venv/bin/python scripts/add_word.py WORD            # one word
.venv/bin/python scripts/resume_audio.py data/batches/batchNN.tsv   # a batch
./build_single.sh
.venv/bin/python scripts/update_numbers.py
.venv/bin/python -m pytest -q tests/test_docs.py
```

Recording is paced for the public synthesiser: about four clips a word,
a few seconds each. A batch of thirty words takes around ten minutes; the
script resumes if interrupted.

## 7. Commit

Stage the batch file, `data/a2_zodziai_v2.txt`, the new clips and
`data/audio/.text_manifest.json`, any new files under `data/cache/`, any
`manual_forms.tsv` or `gloss_overrides.tsv` rows, and the docs the numbers
script touched. Message: `Add WORD (theme)` or `Add batchNN: N words`.
If the user wants a release, `./release.sh vX.Y.Z`.

## 8. Report

End with every card as written — key, definition, English word, example,
translation — and any gate warnings you left in place, so the user can
read them without opening the files.
