# Lithuanian A2 — Anki deck

**1,593 Lithuanian words for the A2 state language exam**, with audio, stress
marks (kirtis) and Lithuanian-language definitions.

📄 **[Deck page](https://elatier.github.io/lithuanian-a2-anki/)** ·
⬇️ **[Download the .apkg](https://github.com/elatier/lithuanian-a2-anki/releases/latest)**

| | |
|---|---|
| Words | 1,593 |
| Cards | 3,186 (two per word) |
| Recordings | 6,372 |
| Themes | 18 — the ministry's twelve A2 topics, plus six more |
| Hand-checked paradigms | 469 |

## Two cards per word

1. **Lithuanian → English.** The headword and an example sentence, answered with
   the English word, a Lithuanian definition, the inflected forms and the
   translations.
2. **Definition → word.** A definition written *entirely in Lithuanian* asks you
   to produce the word. This is the card that builds active recall, and it is why
   no definition ever contains the word it defines.

## What's on a card

- **Audio on everything** — headword, inflected forms, Lithuanian definition,
  example sentence. Four recordings per word.
- **Stress marks** on headwords *and* on the inflected forms shown.
- **Inflected forms** on every card: nouns with the genitive, verbs with 3rd
  person present and past, adjectives with the feminine.
- **Voiced case tables** for personal pronouns and demonstratives, including the
  feminine column (`jie | jos`, `tie | tos`, `šie | šios`).
- **The target word bolded** in the English translation.
- **Tags**: `tema::`, `pos::`, `batch::` — filter to just the verbs, or just one
  theme.

## Installing

Download the `.apkg` from the
[latest release](https://github.com/elatier/lithuanian-a2-anki/releases/latest)
and open it, or in Anki use **File → Import**. It arrives as `Lietuvių A2` with
one subdeck per theme.

To study recognition only, suspend the second card type — it roughly halves the
workload, and it is the harder half.

## Themes

The first twelve are the twelve topics of the Ministry of Education's A2 content
description (*A2 kalbos mokėjimo lygio turinio aprašas*); six more cover ground
that description does not name.

| # | Theme | Words | | # | Theme | Words |
|---|---|---|---|---|---|---|
| 01 | Asmens tapatybė | 128 | | 10 | Prekyba | 113 |
| 02 | Pastatai ir namai | 99 | | 11 | Maistas ir gėrimai | 121 |
| 03 | Gamta, regionas | 108 | | 12 | Paslaugos | 43 |
| 04 | Kasdienis gyvenimas | 118 | | 13 | Darbas ir profesijos | 27 |
| 05 | Laisvalaikis | 124 | | 14 | Laikas ir orai | 59 |
| 06 | Kelionės | 103 | | 15 | Skaičiai ir įvardžiai | 89 |
| 07 | Santykiai su žmonėmis | 134 | | 16 | Spalvos ir savybės | 83 |
| 08 | Sveikata ir higiena | 128 | | 17 | Valstybė ir visuomenė | 31 |
| 09 | Švietimas ir mokslas | 56 | | 18 | Kalba ir gramatika | 29 |

## How it was made

With the seams showing:

- The word list follows the A2 syllabus and the vocabulary of *Pusiaukelė*
  (Ramonienė et al.) and *Nė dienos be lietuvių kalbos*.
- Inflected forms and stress marks come from English Wiktionary, the VDU
  *Kirčiuoklis* stress tool and the `phonology_engine` library, cross-checked
  against each other. Every form is verified against the hunspell `lt_LT`
  dictionary.
- Definitions, examples and translations were **written with AI assistance and
  checked by automated rules** — no headword inside its own definition, an
  inflected form in every example, restricted vocabulary, spell-checked
  throughout. They have **not** been proofread by a native speaker.
- The audio is **synthesised, not recorded**: LIEPA / *Sintezatorius*
  (UAB Intelektika, developed with Vilnius University), voice "astra".

## Building it yourself

Everything needed to rebuild the released deck is in this repo and its
release: the cards are in `data/`, and the recordings are a release asset, so
a rebuild does not have to synthesise any audio.

### Setting up

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`build_single.sh` uses `.venv` automatically, even when it is not activated.
The other scripts run with whichever `python3` is active.

The QA scripts, `verify_defs.py` and `check_forms.py`, also need **hunspell**
with the Lithuanian dictionary. Building the deck does not.

- **Debian/Ubuntu:** `apt install hunspell hunspell-lt`
- **macOS:** `brew install hunspell`. Homebrew has no Lithuanian dictionary, so
  take `lt.aff` and `lt.dic` from
  [LibreOffice/dictionaries](https://github.com/LibreOffice/dictionaries/tree/master/lt_LT)
  and save them as `~/Library/Spelling/lt_LT.aff` and `lt_LT.dic`.

If the dictionary is missing, the scripts stop with an error rather than
passing everything.

### Rebuilding the released deck

```bash
python3 scripts/fetch_audio.py    # the 6,372 clips, ~115 MB, into media_tmp/
./build_single.sh                 # -> decks/lietuviu_A2.apkg
```

The result has the same notes, cards, subdecks and audio as the release.
Because the note IDs are stable, importing it over an existing copy updates
the cards in place. `./build_single.sh --no-fetch` builds without calling the
synthesiser at all; any clip that is missing is left out of the deck.

### Adding or changing a word

1. **Edit the card** in a `data/batches/batch*.tsv` file, or start a new
   batch. See [the card format](#the-card-format) below.
2. **Give it a theme**: the headword must be listed in `data/a2_zodziai_v2.txt`
   under one of the themes in `data/THEMES.md`. Otherwise it is tagged
   `tema::be-temos` and lands outside the theme subdecks.
3. **Inflected forms** come from Wiktionary. If Wiktionary has no table for
   the word, write the paradigm into `data/manual_forms.tsv`.
   `python3 scripts/gen_forms.py WORD POS` drafts a line for regular words.
   Then run `python3 scripts/check_forms.py` to spell-check every form, and
   `python3 scripts/apply_accents.py` to add the stress marks.
4. **Check it**: `python3 scripts/verify_defs.py` runs the QA gate over every
   batch. Pass it one file to check just that batch. Run
   `python3 scripts/root_leak.py data/batches/batchN.tsv` to catch definitions
   that give the answer away through a related word.
5. **Record the audio**: `python3 scripts/resume_audio.py` synthesises only
   what is missing. That includes clips whose text changed: it keeps a
   manifest of what each clip says. It is slow, about 1,250 clips an hour.
6. **Build**: `./build_single.sh`.

### The card format

One row per card, tab-separated, no header:

```
key    lt_def    en_word    en_def    lt_example    en_example    pos    [qualifier]
```

- `key` is normally the headword. A word taught in two senses gets one row per
  sense, keyed `headword#sense` (e.g. `žibintas#auto`, `žibintas`).
- `qualifier` is optional. It is shown in lighter type beside the headword to
  tell the senses apart (`gatvės žibintas`, `automobilio žibintas`), and the
  definition must not contain it.
- `lt_def` must not contain any form of the headword, and `lt_example` must
  contain at least one. `verify_defs.py` enforces both.

### Layout

```
build_single.sh   build the deck
scripts/          the pipeline (Python); paths.py says where everything lives
data/             deck source: word list, paradigms, accents, caches
data/batches/     batch*.tsv, the cards themselves
docs/             the deck page (GitHub Pages)
```

The scripts find their files through `scripts/paths.py`, so they can be run
from any directory. Two things are local and gitignored: the audio in
`media_tmp/`, and the built decks in `decks/`.

### What the scripts do

All in `scripts/`.

| | |
|---|---|
| `build_single.py` (via `../build_single.sh`) | builds the `.apkg`; `--subdecks tema\|batch\|none`, default `tema` |
| `fetch_audio.py` | downloads the published recordings into `media_tmp/` |
| `resume_audio.py` | synthesises missing or outdated clips (LIEPA, rate-limited, resumable) |
| `verify_defs.py` | the QA gate: SPELL, GLOSS, LEAK, FORM, A2, ORDER, LEN, QUAL, HEAD |
| `root_leak.py` | catches definitions that share a root with their headword |
| `check_forms.py` | hunspell-verifies every form in `manual_forms.tsv` |
| `gen_forms.py` | drafts a `manual_forms.tsv` line for a regular word |
| `apply_accents.py` | places stress marks on headwords and every displayed form |
| `scan_forms_lines.py` | audits the inflection line on every card |
| `invalidate_audio.py` | forces specific words to be re-recorded |
| `build_cache.py` | pre-fetches Wiktionary paradigms into `forms_cache.json` |
| `ltcard.py` | the card builder library: note type, templates, CSS, Wiktionary lookups, TTS |
| `paths.py`, `spell.py` | file locations; the hunspell wrapper |
| `theme_preview.py`, `themes*_candidates.py`, `pron_preview.py` | design history: render real cards under candidate stylings; how the current theme was chosen |

### The data

All in `data/`.

| | |
|---|---|
| `batches/batch*.tsv` | the 1,593 cards |
| `manual_forms.tsv` | 469 hand-written, hunspell-verified paradigms for words Wiktionary has no table for |
| `a2_zodziai_v2.txt` | the word list, grouped by theme; the source of the `tema::` tags |
| `THEMES.md` | the theme taxonomy |
| `extra_def_vocab.tsv` | words allowed inside definitions but not taught as cards |
| `accented.txt`, `accents_from_engine.tsv` | stress marks by source; engine-derived ones are flagged for review, never trusted |
| `cache/kaikki/`, `cache/wikt/` | every kaikki.org and Wiktionary lookup the build makes, so a build needs no network and does not drift as Wiktionary is edited. An empty file records that a word has no entry. |
| `forms_cache.json` | cached Wiktionary paradigms used by the QA gate |
| `STYLING.css` | the card styling, identical to the CSS inside the note type |

## Licence and reuse

The definitions, examples and translations in this deck are the author's own
work and may be reused freely with attribution.

The **scripts** in this repo are MIT-licensed — see `LICENSE`.

**Inflected forms and glosses** are derived from **English Wiktionary**, which
is CC BY-SA. That covers `forms_cache.json`, `data/cache/` and the paradigm
columns.

**The audio** was generated with the Lithuanian speech synthesiser operated by
**UAB Intelektika** (`sinteze.intelektika.lt`, now `snekos-sinteze.lt`), voice
"astra". Intelektika's terms of use say, under *Intelektinės nuosavybės teisės*:

> Mūsų suteiktų Paslaugų rezultatus galite naudoti tiek asmeniniais, tiek
> komerciniais tikslais.

— *the results of our Services may be used for both personal and commercial
purposes.* The restriction on copying and redistribution in those terms covers
the operator's own website content, not the synthesis output, and no attribution
is required. The credit below is courtesy, not obligation.

## Corrections

Open an issue with the word and what is wrong. Corrections go into the next
build.
