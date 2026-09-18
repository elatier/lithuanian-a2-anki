---
name: add-word
description: Add one or more Lithuanian words to the deck end to end — draft the card from the drafting packet, pass the QA gate, record the audio, build, update the numbers, commit. Use when asked to add, draft or create a card for a word.
---

# Add a word: $ARGUMENTS

Work one word at a time, in this order. The scripts do everything
mechanical; you write four columns of Lithuanian and English and fix what
the gate rejects. Do not skip the checkpoint in step 6: recording costs
calls to a public service, and no native speaker has proofread the deck.

## 1. Read the packet

```bash
python3 scripts/draft_packet.py WORD
```

Read all of it. It tells you whether the word already has a card, what
Wiktionary says it means and how it inflects, which theme it is in or which
to choose, how that theme's cards read, and which cards already answer
with the same English word.

- **Already in the deck**: stop and tell the user, unless they asked for a
  second sense (then key it `WORD#sense`, give both rows a qualifier, and
  keep the primary sense on the bare key — README, "The card format").
- **No inflection table**: the paradigm goes in `data/manual_forms.tsv`.
  Draft it with `python3 scripts/gen_forms.py WORD POS`, run
  `python3 scripts/check_forms.py`, then `python3 scripts/apply_accents.py`.
  Stress marks that neither source has must come from the VDU Kirčiuoklis
  (the script writes `out/needs_accents.txt` for the user to paste there).
  Say so and never invent an accent.

## 2. Choose the theme and the part of speech

One theme per word, from the packet's list, following `data/THEMES.md`:
prefer the concrete situation a learner meets the word in. The part of
speech is the Wiktionary one the card teaches.

## 3. Scaffold the row

```bash
python3 scripts/add_word.py WORD --new --pos POS --theme SLUG
```

This appends `WORD <tab> <tab> gloss <tab> <tab> <tab> <tab> POS` to the
newest batch file and lists the word under the theme.

## 4. Write the four columns

Edit the row in the batch file: `lt_def`, `en_def`, `lt_example`,
`en_example`. Follow `data/DRAFTING_GUIDE.md` and match the register of
the neighbouring cards in the packet. In short:

- Definition for an A2 learner: concrete, 5–9 words, one clause plus an
  optional clarifying clause after `;` or `–`. No form of the headword, no
  word of the same root, no compound part. Only the packet's vocabulary.
- If another card answers with the same English word, the two definitions
  must be distinguishable.
- Example uses an **inflected** form from the packet, not the dictionary
  form. English keeps Lithuanian word order where English allows.
- `en_word` is one of the Wiktionary glosses; verbs as `to run`. If
  Wiktionary's wording is deficient, add a row to
  `data/gloss_overrides.tsv` with the reason.
- `en_def` is a plain rendering of `lt_def`.

## 5. Run the gate until it passes

```bash
python3 scripts/add_word.py WORD --no-audio
```

Fix every `[FAIL]` (SPELL, GLOSS, LEAK, FORM, QUAL, HEAD) and every
`[WARN]` that is easy (LEN, A2, ORDER). Root-leak hits are for judgement:
a shared prefix is not a shared root. Rerun after each edit.

## 6. Checkpoint

Show the user the finished row and the gate's output, and ask whether to
record. Wait for a yes.

## 7. Record, build, update the numbers

```bash
python3 scripts/add_word.py WORD
./build_single.sh
python3 scripts/update_numbers.py
python3 -m pytest -q tests/test_docs.py
```

## 8. Commit

Stage the batch file, `data/a2_zodziai_v2.txt`, the new clips and
`data/audio/.text_manifest.json`, any new files under `data/cache/`, any
`manual_forms.tsv` or `gloss_overrides.tsv` rows, and the docs the numbers
script touched. Message: `Add WORD (theme)`.
