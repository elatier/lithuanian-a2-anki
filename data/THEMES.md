# Theme taxonomy

Every card names exactly one of these in column 8 of its row, by the part
after `::` (`02-pastatai-ir-namai`); the group prefix is added when the
`tema::` tag is built. The QA gate rejects a row whose slug is not below.

The **twelve `egzaminas::` themes are the exam's own syllabus** — they are the
twelve topics of the ministry's *A2 kalbos mokėjimo turinio aprašas*
(smsm.lrv.lt), in its order: Asmens tapatybė · Būstas · Gamta, regionas ·
Kasdienis gyvenimas · Laisvalaikis · Kelionės · Santykiai su žmonėmis ·
Sveikata ir higiena · Švietimas ir mokslas · Prekyba · Maistas ir gėrimai ·
Paslaugos. They hold 1,278 of the 1,596 words.

The six **`papildoma::` themes** were added by this deck because the catch-all
bucket needed splitting; they have no counterpart in that description. They
hold the remaining 318.

Numbers are zero-padded so a theme list sorts 01, 02 … 10, not 1, 10, 11, 2.
In Anki the tags nest, and `Egzamino temos` sorts above `Papildomos temos`.

| tag | covers |
|---|---|
| `egzaminas::01-asmens-tapatybe` | name, surname, age, nationality, personal details, appearance |
| `egzaminas::02-pastatai-ir-namai` | home, rooms, furniture, buildings, household objects |
| `egzaminas::03-gamta-regionas` | nature, animals, birds, insects, plants, trees, landscape, geography |
| `egzaminas::04-kasdienis-gyvenimas` | daily routine, getting up, washing, sleeping, housework |
| `egzaminas::05-laisvalaikis` | free time, sport, hobbies, music, art, theatre, reading, media |
| `egzaminas::06-keliones` | travel, transport, vehicles, tickets, borders, tourism |
| `egzaminas::07-santykiai-su-zmonemis` | family, friends, feelings, emotions, social behaviour, celebrations |
| `egzaminas::08-sveikata-ir-higiena` | body parts, illness, doctors, medicine, hygiene |
| `egzaminas::09-svietimas-ir-mokslas` | school, university, study, subjects, science |
| `egzaminas::10-prekyba` | shopping, shops, money, prices, clothes, footwear |
| `egzaminas::11-maistas-ir-gerimai` | food, drink, ingredients, cooking, meals, restaurants |
| `egzaminas::12-paslaugos` | services — post, bank, hairdresser, repairs, cleaning |
| `papildoma::13-darbas-ir-profesijos` | work, jobs, professions, workplace, salary |
| `papildoma::14-laikas-ir-orai` | time, days, months, seasons, dates, weather |
| `papildoma::15-skaiciai-ir-ivardziai` | numerals, ordinals, pronouns |
| `papildoma::16-spalvos-ir-savybes` | colours, and general adjectives describing qualities |
| `papildoma::17-valstybe-ir-visuomene` | state, government, law, police, politics, society |
| `papildoma::18-kalba-ir-gramatika` | language, grammar terms, letters, writing |

Rules:

- Every word gets exactly one theme. When two fit, choose the one a learner
  would look for it under — `padavėjas` (waiter) is a profession, but a
  learner meets it in a restaurant, so `11-maistas-ir-gerimai` is better than
  `13-darbas-ir-profesijos`. Use judgement, prefer the concrete situation.
- Common verbs and adjectives with no situational home go to
  `4-kasdienis-gyvenimas` (verbs of everyday action) or
  `16-spalvos-ir-savybes` (descriptive adjectives).
- Do not invent slugs. Do not leave a row's theme empty.
