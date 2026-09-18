# Lietuvių kalba A2 — Anki deck

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

## Licence and reuse

The definitions, examples and translations in this deck are the author's own
work and may be reused freely with attribution.

**Inflected forms and glosses** are derived from **English Wiktionary**, which
is CC BY-SA.

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
