# Adding words to the deck

A card is one line in a `data/batches/batch*.tsv` file. Everything about it
except four columns of text is produced by scripts: the inflected forms and
stress marks come from Wiktionary, the four recordings from the LIEPA
synthesiser, the tags from the row itself. What a person or a model has to
write is:

| column | what it is | example |
|---|---|---|
| `lt_def` | a definition in Lithuanian that never contains the word | *Mažas augalas su šakomis; ne medis.* |
| `en_def` | the same in plain English | *A small plant with branches; not a tree.* |
| `lt_example` | a sentence using an inflected form of the word | *Prie namo auga žalias krūmas.* |
| `en_example` | its translation, keeping the Lithuanian word order | *By the house grows a green bush.* |

A QA gate checks every row before anything is recorded, so a mistake never
costs a recording. The rules it enforces are in [the drafting
guide](data/DRAFTING_GUIDE.md), and the codes it prints are explained [at the
end of this page](#what-the-gate-checks).

There are three ways to do the work, by how much you want installed.

## Before you start

- **Nothing.** Open the repo in a GitHub Codespace: `.devcontainer/` gives
  you Python, hunspell, the dictionary and the Claude Code CLI in the
  browser. Or skip the tools entirely and use the [pull request
  path](#without-anything-installed).
- **Locally.** Once per clone:

  ```bash
  ./setup.sh
  ```

  That creates `.venv`, installs the Python packages and the hunspell
  binary. The Lithuanian dictionary is in the repo. The scripts run with
  `python3` from the active venv; `./build_single.sh` finds `.venv` itself.

Recording needs the network: each new card asks the public LIEPA service
for four clips, a few seconds each. Looking up a word Wiktionary has not
been asked about before also needs the network, once; the answer is cached
in `data/cache/` and committed.

## With Claude Code

Open the repo in Claude Code (the desktop app, the `claude` CLI, or the
terminal of a Codespace) and say:

```
/add-word slėnis
```

The skill in `.claude/skills/add-word/` runs the whole path without
stopping:

1. Prints the drafting packet for the word: what Wiktionary says it means
   and how it inflects, the themes to choose from, how that theme's cards
   read, which cards already answer with the same English word.
2. Chooses the theme, scaffolds the row, and writes the four columns
   following the drafting guide and the register of the neighbouring cards.
3. Runs the gate and rewrites until it passes.
4. Records the clips, rebuilds the deck, refreshes the numbers in the docs,
   and commits.
5. Ends with every card as written, so you can read them without opening
   the files.

Several words at once:

```
/add-word words.tsv
```

where each line of the file is `word<TAB>theme`, with `<TAB>noun`,
`verb` or `adj` added when Wiktionary has more than one part of speech.
The words go into one new batch file and are checked, recorded and built
as one unit. Thirty words take about ten minutes, most of it recording.

You can also give it words with no file: `/add-word slėnis žvakidė lentyna`.

**What to read afterwards.** No native speaker has proofread this deck, and
the model's Lithuanian is not one either. The gate catches leaks, spelling,
off-list vocabulary and word order; it does not catch a definition that is
correct but odd. Read the cards in the final report, and fix any you dislike
the same way you would fix any card: edit the row, run
`python3 scripts/add_word.py WORD`, commit.

**What Claude will not do.** A word with no Wiktionary inflection table
needs a hand-written paradigm, and stress marks that no source has must
come from the VDU Kirčiuoklis, a web form. The skill drafts the paradigm,
checks it with hunspell, and tells you what to paste into the tool; it
never invents an accent. And the AnkiWeb listing is updated by importing
the built deck into Anki desktop and sharing it again from there, which
has no script.

## Without Claude

Yes, entirely. You write the four columns yourself; the scripts do
everything else. Three steps: start the row, write it, finish it.

### 1. Start

```bash
python3 scripts/add_word.py slėnis --new
```

prints the drafting packet and, because no theme was given, the list of
themes, and writes nothing. It looks like this:

```
=== žvakidė

--- Wiktionary (via kaikki.org)
  noun (daiktavardis) — headword žvaki̇̀dė
    glosses: candlestick, candelabrum
    forms line on the card: žvaki̇̀dė / žvaki̇̀dės
    inflected forms for the example (use one of these, not the dictionary form):
      žvakidės (plural) · žvakidžių (genitive plural) · žvakidei (dative singular)
      …

--- theme
  none yet. Pick exactly one for column 8 (THEMES.md: prefer the concrete
  situation a learner meets the word in):
    01-asmens-tapatybe         name, surname, age, nationality, …
    02-pastatai-ir-namai       home, rooms, furniture, buildings, …
    …

--- 99 cards already in egzaminas::02-pastatai-ir-namai; the register to match:
  antklodė   Lovoje ji yra ant mūsų, kad būtų šilta.   blanket   Žiemą reikia šiltos antklodės. …

--- cards that already answer with one of these glosses …
--- vocabulary: 1799 lemmas may appear in the definition and example …
```

Pick the theme and run it again with it. Any unambiguous part of the slug
will do:

```bash
python3 scripts/add_word.py slėnis --new --theme 03
```

That appends a row to the newest batch file with the key, part of speech,
theme and Wiktionary's first gloss filled in:

```
slėnis		valley				noun	03-gamta-regionas
```

If Wiktionary lists the word under more than one part of speech, add
`--pos noun` (or `verb`, `adj`). If the word already has a card, the
script says so and writes nothing; edit that row instead.

### 2. Write

Open the batch file and fill the four empty columns of the row. The
[drafting guide](data/DRAFTING_GUIDE.md) has the register and the rules;
the packet has the inflected forms, the neighbouring cards to match, and
the words a definition may use. Change `en_word` if the first gloss is not
the sense you are teaching; it must still be one of the Wiktionary glosses.

### 3. Finish

```bash
python3 scripts/add_word.py slėnis
```

That runs the gate on the row. If it passes, it records the four clips,
rebuilds the deck into `decks/`, and refreshes the counts in the README,
the deck page and the AnkiWeb listing. If it fails, it prints what is
wrong, records nothing, and you go back to step 2. To check without
recording:

```bash
python3 scripts/add_word.py slėnis --no-audio
```

Then commit: the batch file, the new clips in `data/audio/` together with
`data/audio/.text_manifest.json`, any new files under `data/cache/`, and
the docs.

### A batch of words

The same three steps on a file. Put the words in `words.tsv`:

```
lentyna	02
žvakidė	02-pastatai-ir-namai
kirsti	04	verb
```

Then:

```bash
python3 scripts/add_word.py --new --list words.tsv
```

creates the next `data/batches/batchNN.tsv` with a prefilled row per word
(every theme must resolve, or nothing is written). Write the columns, then:

```bash
python3 scripts/add_word.py --batch batch33
```

checks, records, builds and refreshes the numbers for the whole batch.
`out/review.txt`, written by the gate, shows every card side by side for a
read-through before you commit.

### A word Wiktionary has no table for

The gate reports `HEAD: no usable inflection table`. Write the paradigm
into `data/manual_forms.tsv`:

```bash
python3 scripts/forms.py draft WORD noun      # prints a row for a regular word
python3 scripts/forms.py check                # hunspell-verifies every form
python3 scripts/forms.py accent               # stress marks from the sources that have them
```

Paste the drafted row into the file, fix any form `check` rejects, and run
`accent`. Forms that neither `data/accented.txt` nor kaikki.org can accent
are listed in `out/needs_accents.txt`; run them through the [VDU
Kirčiuoklis](https://kalbu.vdu.lt/mokymosi-priemones/kirciuoklis/), save
its output as `data/accented.txt`, and run `accent` again.

### A second sense of a word

Give it its own row keyed `word#sense`, with the theme in column 8 and a
one-word qualifier in column 9 that tells the senses apart on the card.
Give the original row a qualifier too, and keep it on the bare key so its
note identity survives. See "One word, two senses" in the drafting guide.

### Fixing an existing card

Edit its row. `python3 scripts/add_word.py WORD` re-records only the clips
whose text changed and leaves the rest alone, then rebuilds. To force a
clip that merely sounds wrong to be re-recorded:

```bash
python3 scripts/resume_audio.py --redo WORD
```

## Without anything installed

Add the row on GitHub, in a `data/batches/batch*.tsv` file, in the format
above (tab-separated, no header; the theme slug in column 8), and open a
pull request. The CI workflow runs the gate on every row and the report is
in the checks. The maintainer records the audio, builds and releases.

## What the gate checks

`[FAIL]` blocks recording; `[WARN]` is worth fixing if it is easy.

| code | | means | fix |
|---|---|---|---|
| SPELL | FAIL | a Lithuanian word hunspell does not know | fix the typo; a real word it lacks goes in `extra_def_vocab.tsv` |
| GLOSS | FAIL | `en_word` is not among Wiktionary's glosses | pick one that is, or add a row to `gloss_overrides.tsv` with the reason |
| LEAK | FAIL | the definition contains a form of the headword | rewrite the definition |
| FORM | FAIL | the example contains no form of the headword | use an inflected form from the packet |
| QUAL | FAIL | the definition contains the qualifier | rewrite the definition |
| HEAD | FAIL | no inflection table, or a mis-parsed one | `manual_forms.tsv`, see above |
| THEME | FAIL | column 8 is empty or not a slug from `THEMES.md` | fix the slug |
| LEN | WARN | definition over 12 words | shorten |
| A2 | WARN | a word outside the deck's vocabulary | use a deck word, or document the exception in `extra_def_vocab.tsv` |
| ORDER | WARN | the English translation moved the headword far from its Lithuanian position | keep the word order where English allows |
| ROOT | WARN | a word of the same root as the headword in the definition | rewrite, or if the relation is transparent add the pair to `root_reviewed.tsv` |

## Releasing

```bash
./release.sh v1.1.0
```

builds, checks that the docs quote the current numbers, tags and pushes;
the release workflow attaches the `.apkg` to a GitHub release. Then import
the new build into Anki desktop and share it again to update AnkiWeb.
