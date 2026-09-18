# Can the synthesised audio be redistributed?

Short answer: **the operator's own terms say yes, for personal and commercial
use, with no attribution required.** What follows is what I actually read, and
what I could not.

## What the deck uses

The clips were generated at `sinteze.intelektika.lt`, voice "astra". That host
now **302-redirects to `snekos-sinteze.lt`**, which is operated by
**UAB Intelektika** — the same company. So Intelektika's terms of use are the
ones that govern it.

## What the terms say

From <https://intelektika.lt/naudojimosi-salygos/>, section
*Intelektinės nuosavybės teisės*:

> **Mūsų suteiktų Paslaugų rezultatus galite naudoti tiek asmeniniais, tiek
> komerciniais tikslais.**
>
> *The results of the Services we provide may be used for both personal and
> commercial purposes.*

The distribution prohibition in the same section is aimed at something else —
the company's **website content**, not the output:

> Mūsų interneto svetainių turinio negalima kopijuoti, modifikuoti, kurti jo
> pagrindu išvestinių produktų/paslaugų, viešai rodyti, viešai atlikti,
> perspausdinti, atsisiųsti, laikyti ar perduoti

*("Paslaugų rezultatai" — the synthesised speech — is treated as distinct from
the protected website content.)*

Responsibility runs the other way on input: **you** must hold the rights to the
text you submit for synthesis.

> Pateikdami tekstinę, garso ar vaizdo medžiagą mūsų Paslaugoms… jūs esate
> atsakingi už tai, kad nebūtų pažeistos autorių ar kitos teisės.

Other obligations in the terms: no vulgar language in synthesis requests, no
sharing of purchased service keys, no breaking Lithuanian law.

**No attribution requirement appears anywhere in the terms.**

## What this means for the deck

| Question | Answer |
|---|---|
| Redistribute ~6,372 generated clips inside a shared deck? | Permitted — commercial use is explicitly allowed, so free sharing is a lesser case |
| Must the deck credit Intelektika or LIEPA? | No. The credit on the page and in the README is courtesy |
| Whose rights cover the Lithuanian text that was synthesised? | Yours — the definitions and examples in this deck are original, not copied |
| Can the AnkiWeb copyright box be ticked in good conscience? | On the audio question, yes |

## Two things I could not verify

1. **LIEPA's own project pages.** `raštija.lt` is an internationalised domain and
   its `robots.txt` fails to parse for the fetcher, so every page under it was
   unreachable. If the LIEPA project publishes terms of its own that differ from
   Intelektika's commercial terms, I have not seen them.
2. **Whether the free endpoint is covered by the same terms.** The terms are
   written around a **purchased-key** model ("keys are personal and
   non-transferable", refunds within three months). This deck's clips were
   generated through the free endpoint, at volume — roughly 6,372 requests, with
   the service rate-limiting along the way. The terms do not address bulk use of
   the free tier one way or the other.

Neither of these contradicts the permission quoted above; they are simply gaps.
If you want the question closed rather than merely well-evidenced, the terms list
**info@intelektika.lt** — one email describing the deck, the volume and the
intended free distribution would settle it.
