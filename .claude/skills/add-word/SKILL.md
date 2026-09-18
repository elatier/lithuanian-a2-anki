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

## 1. Start each word

```bash
.venv/bin/python scripts/add_word.py WORD
```

For a word with no row this prints the drafting packet and the list of
themes and writes nothing. Read all of it: whether the word already has a card,
what Wiktionary says it means and how it inflects, and which cards already
answer with the same English word. Then choose one theme, following
`data/THEMES.md` (prefer the concrete situation a learner meets the word
in; if the user's list gives themes, use them), and scaffold:

```bash
.venv/bin/python scripts/add_word.py WORD --theme SLUG [--pos POS]
```

That appends a row to the newest batch file with the key, part of speech,
theme and gloss filled in. `--pos` is needed only when Wiktionary has more
than one part of speech.

A batch: write `out/words.tsv` with one `word<TAB>theme[<TAB>pos]` line per
word (or use the user's file; run `add_word.py WORD` for any word whose
theme you need to look at first), then

```bash
.venv/bin/python scripts/add_word.py --list out/words.tsv
```

which creates the next `data/batches/batchNN.tsv` with a prefilled row per
word.

- **Already in the deck**: leave it out and tell the user, unless they
  asked for a second sense (key it `WORD#sense`, give both rows a
  qualifier in column 9, keep the primary sense on the bare key — README,
  "The card format").
- **No inflection table**: the paradigm goes in `data/manual_forms.tsv`.
  Draft it with `forms.py draft WORD POS`, run `forms.py check`, then
  `forms.py accent`. Stress marks that neither source has must come from
  the VDU Kirčiuoklis; the script writes `out/needs_accents.txt` for the
  user to paste there. Say so, and never invent an accent.

## 2. Write the four columns

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

## 3. Check until clean, then finish

```bash
.venv/bin/python scripts/add_word.py WORD --no-audio        # one word
.venv/bin/python scripts/add_word.py --batch batchNN --no-audio   # a batch
```

Fix every `[FAIL]` (SPELL, GLOSS, LEAK, FORM, QUAL, HEAD, THEME) and every
`[WARN]` that is easy (LEN, A2, ORDER, ROOT). ROOT is for judgement: a
shared prefix is not a shared root; a hit you judge harmless goes into
`data/root_reviewed.tsv` with a note. Rerun after each edit. When it is
clean, drop `--no-audio`:

```bash
.venv/bin/python scripts/add_word.py WORD
.venv/bin/python scripts/add_word.py --batch batchNN
```

That records the clips, rebuilds the deck and refreshes the numbers in the
docs. Recording is paced for the public synthesiser: about four clips a
word, a few seconds each; a batch of thirty words takes around ten
minutes, and the script resumes if interrupted.

## 4. Commit

Stage the batch file, the new clips and `data/audio/.text_manifest.json`,
any new files under `data/cache/`, any `manual_forms.tsv` or
`gloss_overrides.tsv` rows, and the docs the numbers step touched.
Message: `Add WORD (theme)` or `Add batchNN: N words`. If the user wants a
release, `./release.sh vX.Y.Z`.

## 5. Report

End with every card as written — key, definition, English word, example,
translation — and any gate warnings you left in place, so the user can
read them without opening the files.
