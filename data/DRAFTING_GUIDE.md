# Writing a card

How to write a row that fits the deck and passes the QA gate. The format
itself — columns, `headword#sense` keys, the qualifier — is in the README
under "The card format"; this is about what goes in the columns.

Check as you go:

```bash
python3 scripts/add_word.py WORD --no-audio
```

Start a row with `python3 scripts/add_word.py WORD --new --theme SLUG`: it
prints the drafting packet and fills in everything but the four text
columns.

`[FAIL]` (SPELL, GLOSS, LEAK, FORM, QUAL, HEAD, THEME) must be fixed.
`[WARN]` (LEN, A2, ORDER) should be fixed if it is easy, and is acceptable if
it is not.

## The register

Real cards from the deck:

| word | lt_def | en_word | lt_example | en_example |
|---|---|---|---|---|
| krūmas | Mažas augalas su šakomis; ne medis. | bush | Prie namo auga žalias krūmas. | By the house grows a green bush. |
| numeris | Skaičius ant namo, buto ar telefono. | number | Koks tavo telefono numeris? | What is your telephone number? |
| valgyti | Dėti maistą į burną. | to eat | Pietums valgome sriubą. | For lunch we eat soup. |
| gražus | Malonus akiai; toks, į kurį gera žiūrėti. | beautiful | Šiandien labai graži diena. | Today is a very beautiful day. |

- **Definitions are for an A2 learner**, not a dictionary: concrete and
  everyday, one clause plus an optional clarifying clause after `;` or `–`.
  Aim for 5–9 words; over 12 is a LEN warning.
- `en_def` is a plain English rendering of `lt_def`.
- Verbs are translated as `to run`, `to speak`.

## The rules

1. **No leak.** `lt_def` must not contain the headword or any inflected form
   of it. Card 2 shows the definition alone and asks for the word, so a leak
   gives the answer away. (LEAK)

2. **No same-root giveaway.** A derivation of the same root gives the answer
   away just as badly: `augalas` defined as "tai, kas **auga**", `skalbyklė`
   as "mašina, kuri **skalbia**". For compounds this includes their parts:
   do not define `prieškambaris` with **kambarys**, or `senamiestis` with
   **miesto**. `add_word.py` runs the root-leak check. Its hits are for
   review, not automatic failures: a shared prefix (`pavardė` /
   `pavadinimas`) is not a shared root.

3. **A2 vocabulary only.** Every Lithuanian word in `lt_def` and
   `lt_example` should be A2 vocabulary. That means a form in
   `forms_cache.json` or `manual_forms.tsv`, a grammar word in
   `function_words.txt`, a documented exception in `extra_def_vocab.tsv`,
   or a proper noun in `proper_nouns.txt`. Anything else is an A2 warning.
   Capitalising a word at the start of a sentence does not excuse it.

4. **The example contains an inflected form of the headword**, and
   preferably not the dictionary form: `Vaikai sėdi ant žolės.`, not
   `Žolė yra žalia.` (FORM)

5. **English keeps Lithuanian word order** wherever English grammar allows:
   `Prie namo auga žalias krūmas.` → `By the house grows a green bush.` The
   gate warns when the headword drifts more than a third of the way through
   the sentence. (ORDER)

6. **`en_word` must be one of the word's Wiktionary glosses.** If your
   preferred translation is not among them, pick one that is — or, when
   Wiktionary's wording is genuinely deficient, add a row to
   `gloss_overrides.tsv` saying what you chose and why. (GLOSS)

7. **Spell everything correctly.** Every Lithuanian word is checked with
   hunspell `lt_LT`. (SPELL)

## Two cards, one English word

Two cards may share an English answer — `motina` and `mama` are both
"mother", and that is correct. Pick the most natural English for each word
rather than distorting it to avoid a collision. What must differ is the
**definition**, since that is what card 2 asks.

## One word, two senses

Give each sense its own row, keyed `headword#sense`, with a qualifier in the
8th column (see "The card format" in the README). Also:

- **Keep the primary sense on the bare key.** That preserves its note
  identity, so a re-import updates the existing card instead of duplicating
  it. Only the added sense takes a `#tag`.
- **Give both cards a qualifier**, or their card-1 fronts are identical and
  unanswerable.
- The qualifier must itself be A2 vocabulary, and must not appear in the
  definition. (QUAL)
