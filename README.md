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

Everything needed to rebuild the deck is in this repo, recordings included.
A rebuild needs no network and synthesises no audio.

### Setting up

Once per clone:

```bash
./setup.sh
```

That creates `.venv`, installs the Python packages, and installs the
hunspell binary with Homebrew or apt. The Lithuanian dictionary is in the
repo. By hand, the same is:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # the build needs only requirements.txt
```

No local setup at all: open the repo in a GitHub Codespace. The
`.devcontainer/` gives you Python, hunspell, the dictionary and the Claude
Code CLI in the browser.

The 6,372 recordings (~115 MB) come with the clone, in `data/audio/`. Only
the clips for words you add or edit are ever recorded, and you commit them
with the card. If you only want to build, `git clone --depth 1` skips the
history and keeps the download small.

`build_single.sh` uses `.venv` automatically, even when it is not activated.
The other scripts run with whichever `python3` is active.

Checking cards also needs the **hunspell** binary (`brew install hunspell`
or `apt install hunspell`). Building does not. The Lithuanian dictionary it
uses is `data/hunspell/`, so nothing else has to be found or downloaded. If
hunspell is missing, the scripts stop with an error rather than passing
everything.

### Rebuilding the released deck

```bash
./build_single.sh                 # -> decks/lietuviu_A2.apkg
```

This builds the same notes, cards, subdecks and audio as the release,
offline, in about ten seconds. The note IDs are stable, so
importing it over an existing copy updates the cards in place.

Before building, `build_single.sh` records any clip that is missing or whose
text has changed, and only those. `--no-fetch` never contacts the synthesiser:
missing clips are left off their cards.

### Adding words

**[ADDING_WORDS.md](ADDING_WORDS.md)** is the guide. In short, a card is one
row in a batch file, and only four of its columns are written by a person
or a model: the Lithuanian definition, its English rendering, an example
sentence and its translation. Everything else — forms, stress marks,
audio, tags — comes from scripts, and a QA gate checks every row before
anything is recorded.

- **With Claude Code:** `/add-word slėnis`, or `/add-word words.tsv` for a
  batch. The model drafts the cards, passes the gate, records, builds and
  commits, and ends with every card written out for you to read.
- **Without:** three commands and the writing in between.
  `python3 scripts/add_word.py slėnis --new --theme 03` prints a drafting
  packet and scaffolds the row; you fill the four columns;
  `python3 scripts/add_word.py slėnis` checks, records, builds and
  refreshes the numbers. `--new --list words.tsv` and `--batch batch33`
  do the same for a batch.
- **Nothing installed:** add the row on GitHub and open a pull request;
  CI runs the gate.

Words Wiktionary has no table for, second senses, fixing a card, and what
each gate code means are all in the guide.

### Releasing

```bash
./release.sh v1.1.0
```

That builds, checks that the docs quote the current numbers, tags, and
pushes. The release workflow then builds the deck offline from the tag and
attaches the `.apkg` to a GitHub release, which is what the download links
point at. Without GitHub Actions, upload the local build instead:
`gh release create v1.1.0 decks/lietuviu_A2.apkg`.

The AnkiWeb listing is updated by importing the new build into Anki
desktop and sharing it again from there; that step has no script.

### The card format

One row per card, tab-separated, no header:

```
key    lt_def    en_word    en_def    lt_example    en_example    pos    theme    [qualifier]
```

- `key` is normally the headword. A word taught in two senses gets one row per
  sense, keyed `headword#sense` (e.g. `žibintas#auto`, `žibintas`).
- `theme` is one of the eighteen slugs in `data/THEMES.md`, without the
  group prefix: `02-pastatai-ir-namai`. It becomes the `tema::` tag and the
  subdeck.
- `qualifier` is optional. It is shown in lighter type beside the headword to
  tell the senses apart (`gatvės žibintas`, `automobilio žibintas`), and the
  definition must not contain it.
- `lt_def` must not contain any form of the headword, and `lt_example` must
  contain at least one. `verify_defs.py` enforces both.

### Layout

```
ADDING_WORDS.md   how to add or fix a card, with Claude Code or without
setup.sh          one-time setup: venv, packages, the hunspell binary
build_single.sh   build the deck
release.sh        build, check the numbers, tag and push
scripts/          the pipeline (Python); paths.py says where everything lives
tests/            pytest suite; no network needed
data/             deck source: word list, paradigms, accents, caches
data/batches/     batch*.tsv, the cards themselves
data/audio/       the recordings, ~115 MB
docs/             the deck page (GitHub Pages)
ankiweb/          the AnkiWeb listing: description and Share-form fields
.github/          CI, the release workflow, the correction issue template
.devcontainer/    a ready environment for GitHub Codespaces
.claude/skills/   the /add-word skill for Claude Code
pyproject.toml    pytest and ruff configuration
```

The scripts find their files through `scripts/paths.py`, so they can be run
from any directory. Only the built decks in `decks/` and the reports and
previews in `out/` are local and gitignored.

### What the scripts do

All in `scripts/`.

| | |
|---|---|
| `build_single.py` (via `../build_single.sh`) | builds the `.apkg`; `--subdecks tema\|batch\|none`, default `tema` |
| `add_word.py` | the word workflow: `--new` prints the packet and scaffolds a row (`--list` a batch); a bare run checks, records, builds and refreshes the numbers |
| `draft_packet.py` | the drafting packet on its own; `add_word.py --new` prints it |
| `update_numbers.py` | rewrites the counts quoted in the README, deck page and AnkiWeb listing |
| `resume_audio.py` | records missing or outdated clips (LIEPA, rate-limited, resumable); the build runs it; `--redo WORD` re-records a word whose clip sounds wrong |
| `verify_defs.py` | the QA gate: SPELL, GLOSS, LEAK, FORM, A2, ORDER, LEN, QUAL, HEAD, THEME, ROOT |
| `forms.py` | the paradigms Wiktionary lacks: `draft WORD POS` a row, `check` every form with hunspell, `accent` the stress marks |
| `ltcard.py` | the card builder library: note type, templates, CSS, Wiktionary lookups, TTS |
| `paths.py`, `spell.py` | file locations; the hunspell wrapper |
| `design/` | design history: render real cards under candidate stylings; how the current theme was chosen |

### Tests

```bash
python3 -m pytest
```

The tests never touch the network. The services are faked, including slow,
throttled and broken responses: LIEPA timing out, answering 403 "Quota
reached", or answering 200 with an error page, empty audio or bytes that
are not MP3. kaikki.org and Wiktionary are faked too, returning outages,
error pages, and pages with no Lithuanian entry.

The tests check that:

- a bad answer is never saved as a clip or cached as a fact;
- retries back off and give up instead of looping;
- an interrupted recording never leaves a partial clip behind;
- the whole deck builds with the network refused;
- the text on a card is what the parsers and the bolding rules should
  produce, and each QA rule fires on exactly the fault it is for;
- the numbers in this README, the deck page and the AnkiWeb listing match
  the data.

### The data

All in `data/`.

| | |
|---|---|
| `batches/batch*.tsv` | the 1,593 cards |
| `manual_forms.tsv` | 469 hand-written, hunspell-verified paradigms for words Wiktionary has no table for |
| `THEMES.md` | the theme taxonomy; column 8 of every row names one of its slugs |
| `DRAFTING_GUIDE.md` | how to write a card: register, rules, two-sense words |
| `forms_cache.json` | Wiktionary paradigms fetched for the original A2 word list; the gate counts them as known vocabulary |
| `extra_def_vocab.tsv` | words allowed inside definitions but not taught as cards |
| `root_reviewed.tsv` | ROOT hits a person has judged harmless, so the gate stops reporting them |
| `function_words.txt` | grammar words that always count as known A2 vocabulary |
| `proper_nouns.txt` | names that may open a sentence without failing SPELL or A2 |
| `gloss_overrides.tsv` | translations the GLOSS check accepts on trust, each with its reason |
| `accented.txt`, `accents_from_engine.tsv` | stress marks by source; engine-derived ones are flagged for review, never trusted |
| `cache/kaikki/`, `cache/wikt/` | every kaikki.org and Wiktionary lookup the build makes, so a build needs no network and does not drift as Wiktionary is edited. An empty file records that a word has no entry. |
| `audio/` | the recordings, four per card, and `.text_manifest.json`, which records what each clip says so that edited text is re-recorded |
| `STYLING.css` | the card styling, identical to the CSS inside the note type |
| `hunspell/` | the `lt_LT` spelling dictionary the QA gate runs, with its licence |

## Licence and reuse

The definitions, examples and translations in this deck are the author's own
work and may be reused freely with attribution.

The **scripts** in this repo are MIT-licensed — see `LICENSE`.

**Inflected forms and glosses** are derived from **English Wiktionary**, which
is CC BY-SA. That covers `forms_cache.json`, `data/cache/` and the paradigm
columns.

**The spelling dictionary** in `data/hunspell/` is the
[ispell-lt](https://github.com/ispell-lt/ispell-lt) lexicon by Albertas
Agejevas and contributors, redistributed under its BSD licence
(`data/hunspell/COPYING`). It is used to check the cards and is not part of
the deck.

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

[Open an issue](https://github.com/elatier/lithuanian-a2-anki/issues/new?template=correction.yml)
with the word and what is wrong. Corrections go into the next build.
