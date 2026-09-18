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
everything else. Two steps: write the row, run the command. The command
is the same one throughout, `add_word.py WORD`, and it does whatever the
word needs next: for a word with no row it shows you what to write and can
start the row for you; for a word with a row it checks, records and builds.

### 1. Write the row

Either write the whole line into a `data/batches/batch*.tsv` file yourself
(tab-separated: `key lt_def en_word en_def lt_example en_example pos theme`),
or let the script start it. Before the row exists,

```bash
python3 scripts/add_word.py slėnis
```

prints the drafting packet and, because no theme was given, the list of
themes, and writes nothing:

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

--- cards that already answer with one of these glosses …
--- vocabulary: 1799 lemmas may appear in the definition and example …
```

Pick the theme and run it again with it; any unambiguous part of the slug
will do:

```bash
python3 scripts/add_word.py slėnis --theme 03
```

That appends a row to the newest batch file with the key, part of speech,
theme and Wiktionary's first gloss filled in, and shows the theme's
neighbouring cards so you can match their register:

```
slėnis		valley				noun	03-gamta-regionas
```

If Wiktionary lists the word under more than one part of speech, add
`--pos noun` (or `verb`, `adj`). A theme on a word that already has a row
never adds a second one.

Now fill the four empty columns. The [drafting
guide](data/DRAFTING_GUIDE.md) has the register and the rules; the packet
has the inflected forms and the words a definition may use. Change
`en_word` if the first gloss is not the sense you are teaching; it must
still be one of the Wiktionary glosses.

### 2. Run the command

```bash
python3 scripts/add_word.py slėnis
```

Now that the row exists, this runs the gate on it. If it passes, it
records the four clips, rebuilds the deck into `decks/`, and refreshes the
counts in the README, the deck page and the AnkiWeb listing. If it fails,
it prints what is wrong, records nothing, and you go back to the row. To
check without recording:

```bash
python3 scripts/add_word.py slėnis --no-audio
```

Then commit: the batch file, the new clips in `data/audio/` together with
`data/audio/.text_manifest.json`, any new files under `data/cache/`, and
the docs.

### A batch of words

The same two steps on a file. Put the words in `words.tsv`:

```
lentyna	02
žvakidė	02-pastatai-ir-namai
kirsti	04	verb
```

Then:

```bash
python3 scripts/add_word.py --list words.tsv
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

## A worked example

Three words added by hand on 2026-09-19, exactly as above; this is the
batch33 commit in the history. The list:

```
kvitas	10
kopėčios	02
jungiklis	02
```

Scaffolding it prints a compact packet per word and writes the rows:

```
$ python3 scripts/add_word.py --list out/words.tsv
=== kvitas
--- Wiktionary (via kaikki.org)
  noun (daiktavardis) — headword kvi̇̀tas
    glosses: receipt (an official certificate showing the delivery and receipt of money …)
    forms line on the card: kvi̇̀tas / kvi̇̀tai
    inflected forms for the example (use one of these, not the dictionary form):
      kvitai (plural) · kvito (genitive singular) · kvitų (genitive plural)
      kvitui (dative singular) · kvitams (dative plural) · kvitą (accusative singular)
      …
--- cards that already answer with one of these glosses (their definitions must stay distinguishable from yours):
  čekis	receipt	Mažas popierius iš parduotuvės; rodo, kiek mokėjome.
kvitas: row appended to batch33.tsv
    kvitas		receipt				noun	10-prekyba
…
3 of 3 word(s) scaffolded into batch33.tsv. Write the columns, then:
    python3 scripts/add_word.py --batch batch33
```

Two things in that packet shaped the writing: *kopėčios* is plural-only,
so the forms line reads `kópėčios (tik dgs.)` and the example has to use a
plural case; and *čekis* already answers "receipt", so the definition of
*kvitas* had to be about a different receipt (a bank's or the post
office's, not a shop's) or card 2 would have two right answers.

The first draft of the four columns, and the gate's answer:

```
$ python3 scripts/add_word.py --batch batch33 --no-audio
--- QA gate
[WARN] jungiklis
       A2: off-list vocabulary ['spaudžiame']
[WARN] kopėčios
       A2: off-list vocabulary ['aukštyn']
[OK ] kvitas
```

Both warnings are the A2 rule: *spausti* is taught, but only its
dictionary forms are known, so the first person *spaudžiame* is off-list;
*aukštyn* is not taught at all. The two definitions were rewritten with
words the deck has (*jį reikia spausti, kad lempa degtų*; *lipame į
viršų*), and the gate passed. The final rows:

```
kvitas	Popierius; jis rodo, kad sumokėjai pinigus, pavyzdžiui, banke ar pašte.	receipt	A paper; it shows that you paid money, for example at the bank or the post office.	Banke man davė kvitą.	At the bank they gave me a receipt.	noun	10-prekyba
kopėčios	Daiktas, kuriuo lipame į viršų, pavyzdžiui, prie stogo ar aukštos lentynos.	ladder	A thing we climb up on, for example to the roof or a high shelf.	Tėtis lipa kopėčiomis ant stogo.	Dad climbs the ladder onto the roof.	noun	02-pastatai-ir-namai
jungiklis	Mažas daiktas ant sienos; jį reikia spausti, kad lempa degtų.	switch	A small thing on the wall; you press it to make the lamp light up.	Kur yra šviesos jungiklis?	Where is the light switch?	noun	02-pastatai-ir-namai
```

Then the finish, about half a minute:

```
$ python3 scripts/add_word.py --batch batch33
--- QA gate
[OK ] jungiklis
[OK ] kopėčios
[OK ] kvitas

--- audio
[00:32:01] 12 clip(s) to record; 6372 already done
[00:32:03] POST   9 ch -> 200 in  1.43s, 9.7 KB  'jungiklis'
[00:32:06] POST  22 ch -> 200 in  1.64s, 15.8 KB  'jungiklis , jungikliai'
[00:32:08] POST  61 ch -> 200 in  0.31s, 36.6 KB  'Mažas daiktas ant sienos; jį reikia spausti, kad lempa degtų.'
…
[00:32:28] DONE — 12 new clip(s), nothing left to record

--- build
Wrote decks/lietuviu_A2.apkg: 1596 note(s), 3192 cards, 6384 media file(s), 18 deck(s).

--- numbers
  1,593 -> 1,596
  3,186 -> 3,192
  6,372 -> 6,384
  1,275 -> 1,278
updated: README.md, docs/index.html, ankiweb/DESCRIPTION.md, ankiweb/SHARE_FORM.md, data/THEMES.md

Done. Commit the row(s), the new clips in data/audio/ (with .text_manifest.json), new files under data/cache/, and the docs.
```

What got committed: `data/batches/batch33.tsv`, twelve clips and the
manifest in `data/audio/`, six lookup files under `data/cache/`, and the
five documents with the new numbers.

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
the release workflow attaches the `.apkg` to a GitHub release titled with
the word count and summarised from the data. Then import
the new build into Anki desktop and share it again to update AnkiWeb.
