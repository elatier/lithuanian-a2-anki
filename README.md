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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # the build needs only requirements.txt
```

The 6,372 recordings (~115 MB) come with the clone, in `data/audio/`. Only
the clips for words you add or edit are ever recorded, and you commit them
with the card. If you only want to build, `git clone --depth 1` skips the
history and keeps the download small.

`build_single.sh` uses `.venv` automatically, even when it is not activated.
The other scripts run with whichever `python3` is active.

Checking cards also needs **hunspell** with the Lithuanian dictionary.
Building does not.

- **Debian/Ubuntu:** `apt install hunspell hunspell-lt`
- **macOS:** `brew install hunspell`. Homebrew has no Lithuanian dictionary, so
  take `lt.aff` and `lt.dic` from
  [LibreOffice/dictionaries](https://github.com/LibreOffice/dictionaries/tree/master/lt_LT)
  and save them as `~/Library/Spelling/lt_LT.aff` and `lt_LT.dic`.

If the dictionary is missing, the scripts stop with an error rather than
passing everything.

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

### Adding or changing a word

1. **Write the card**: a row in a `data/batches/batch*.tsv` file, or a new
   batch file. See [the card format](#the-card-format) below, and
   [`data/DRAFTING_GUIDE.md`](data/DRAFTING_GUIDE.md) for the style and the
   rules the QA gate enforces.
2. **Give it a theme**: list the headword under a theme heading in
   `data/a2_zodziai_v2.txt` (the themes are in `data/THEMES.md`).
3. **Check it and record it**:

   ```bash
   python3 scripts/add_word.py slėnis
   ```

   This finds the word's rows and checks its theme. It runs the QA gate and
   the root-leak check on those rows only. If they pass, it records the clips
   that are new or whose text changed: four per card, a few seconds each.
   Nothing is recorded while a check fails. Pass several words at once, or
   `--no-audio` to only check.
4. **Build**: `./build_single.sh`.
5. **Commit** the card, its new clips in `data/audio/` (including
   `.text_manifest.json`), and any new files under `data/cache/`: the
   dictionary lookups for the new word.

If the QA gate reports no inflection table, Wiktionary has none for the word.
Write its paradigm into `data/manual_forms.tsv` instead:

1. `python3 scripts/gen_forms.py WORD POS` drafts the line for a regular word.
2. `python3 scripts/check_forms.py` spell-checks every form.
3. `python3 scripts/apply_accents.py` adds the stress marks.

Before a release, `python3 scripts/verify_defs.py` with no arguments checks
every batch. Every push runs the same checks on GitHub Actions: lint, the
tests, the gate, and an offline build (`.github/workflows/ci.yml`).

### Releasing

Tag the commit and push the tag:

```bash
git tag v1.1.0 && git push origin v1.1.0
```

The release workflow builds the deck offline from that tag and attaches the
`.apkg` to a GitHub release, which is what the download links point at.
Update the numbers in this README, `docs/index.html` and `ankiweb/` first;
`tests/test_docs.py` fails while they disagree with the data.

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
tests/            pytest suite; no network needed
data/             deck source: word list, paradigms, accents, caches
data/batches/     batch*.tsv, the cards themselves
data/audio/       the recordings, ~115 MB
docs/             the deck page (GitHub Pages)
ankiweb/          the AnkiWeb listing: description and Share-form fields
.github/          CI, the release workflow, the correction issue template
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
| `add_word.py` | checks new or edited words and records only their audio |
| `resume_audio.py` | records missing or outdated clips (LIEPA, rate-limited, resumable); the build runs it |
| `verify_defs.py` | the QA gate: SPELL, GLOSS, LEAK, FORM, A2, ORDER, LEN, QUAL, HEAD |
| `root_leak.py` | catches definitions that share a root with their headword |
| `check_forms.py` | hunspell-verifies every form in `manual_forms.tsv` |
| `gen_forms.py` | drafts a `manual_forms.tsv` line for a regular word |
| `apply_accents.py` | places stress marks on headwords and every displayed form |
| `scan_forms_lines.py` | audits the inflection line on every card |
| `invalidate_audio.py` | forces specific words to be re-recorded, e.g. when a clip sounds wrong |
| `build_cache.py` | pre-fetches Wiktionary paradigms into `forms_cache.json` |
| `ltcard.py` | the card builder library: note type, templates, CSS, Wiktionary lookups, TTS |
| `paths.py`, `spell.py` | file locations; the hunspell wrapper |
| `theme_preview.py`, `themes*_candidates.py`, `pron_preview.py` | design history: render real cards under candidate stylings; how the current theme was chosen |

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
| `a2_zodziai_v2.txt` | the word list, grouped by theme; the source of the `tema::` tags |
| `THEMES.md` | the theme taxonomy |
| `DRAFTING_GUIDE.md` | how to write a card: register, rules, two-sense words |
| `extra_def_vocab.tsv` | words allowed inside definitions but not taught as cards |
| `function_words.txt` | grammar words that always count as known A2 vocabulary |
| `proper_nouns.txt` | names that may open a sentence without failing SPELL or A2 |
| `gloss_overrides.tsv` | translations the GLOSS check accepts on trust, each with its reason |
| `accented.txt`, `accents_from_engine.tsv` | stress marks by source; engine-derived ones are flagged for review, never trusted |
| `cache/kaikki/`, `cache/wikt/` | every kaikki.org and Wiktionary lookup the build makes, so a build needs no network and does not drift as Wiktionary is edited. An empty file records that a word has no entry. |
| `audio/` | the recordings, four per card, and `.text_manifest.json`, which records what each clip says so that edited text is re-recorded |
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

[Open an issue](https://github.com/elatier/lithuanian-a2-anki/issues/new?template=correction.yml)
with the word and what is wrong. Corrections go into the next build.
