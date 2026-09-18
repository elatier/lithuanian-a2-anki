#!/usr/bin/env python3
"""themes2_candidates.py — four ways to do the Trispalvė theme.

They share the same skeleton: serif Lithuanian, sans-serif English, warm paper
ground, full dark set. They differ only in how much of the flag is used and
how the answer is separated from the question.

    ramus     amber only; the English answer is set apart by weight, not colour
    zalias    amber rule + deep green English, no red
    antraste  headword in a banner with an amber hairline; green English
    pilna     all three colours, the red as a mark beside the answer rule

The serif stack is Charter first (iOS and macOS ship it, and it was drawn for
low-resolution screens, so accents stay legible at 19px), then Iowan, Georgia,
then whatever the system calls `serif`. I have not verified which of those is
present on your phone — the fonts.html page renders the same card in each one
so you can see what the fallbacks look like.
"""

SERIF = ('"Charter", "Bitstream Charter", "Iowan Old Style", Georgia, '
         '"Times New Roman", serif')
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

# flag colours, adjusted for text contrast on a warm ground
AMBER = "#fdb913"       # rules and marks only — too light for text
AMBER_TX = "#a97c10"    # the same hue, dark enough to read as text
GREEN = "#00694a"
GREEN_N = "#4fbe8f"     # dark mode
RED = "#c1272d"


def build(*, accent, accent_night, rule, forms_rule, banner=False):
    """One theme. `accent` colours the English answer and the hint link;
    `rule` is the CSS for the answer separator; `forms_rule` decorates the
    inflected-forms line; `banner` boxes the headword."""
    return f"""
.card {{ font-family: {SERIF}; font-size: 22px; text-align: center;
        color: #2b2620; background: #fdfaf2; line-height: 1.5; }}

.word    {{ font-size: 35px; font-weight: 700; color: #1f1b16;
           letter-spacing: -.005em; {'padding: 10px 0 12px; margin: 0 0 4px; border-bottom: 1px solid #eadfc4;' if banner else ''} }}
.qual    {{ font-weight: 400; color: #9a9284; }}
.forms   {{ font-size: 19px; color: #6a6255; margin: 6px 0; }}
.forms-q {{ font-size: 23px; font-weight: 600; color: #4a4335; margin: 12px 0;
           {forms_rule} }}
.formsbig{{ font-size: 27px; font-weight: 700; margin: 10px 0; color: #2b2620;
           {forms_rule} }}
.lt      {{ font-size: 21px; margin: 12px 0; }}
.en      {{ font-size: 20px; color: #55503f; margin: 8px 0; font-style: italic;
           font-family: {SANS}; }}
.small   {{ font-size: 18px; margin-top: 12px; font-style: italic;
           color: #6f6858; font-family: {SANS}; }}
.en-main {{ font-size: 27px; font-weight: 700; font-style: italic;
           color: {accent}; margin: 14px 0; font-family: {SANS}; }}
.word-a  {{ font-size: 24px; font-weight: 400; color: #9a9284; margin: 12px 0; }}
a.hint   {{ color: {accent}; font-size: 19px; text-decoration: none;
           font-style: normal; font-family: {SANS}; }}
hr#answer {{ {rule} }}

.par    {{ margin: 14px auto; border-collapse: collapse; font-size: 19px; }}
.par th {{ color: #a89f8d; font-weight: 400; text-align: right; font-size: 17px;
          padding: 3px 12px 3px 0; }}
.par td {{ text-align: left; padding: 3px 18px 3px 0; }}
.par th.hd {{ color: {AMBER_TX}; text-align: left; font-size: 14px;
             letter-spacing: .08em; text-transform: uppercase;
             padding-top: 10px; }}

.nightMode.card, .nightMode .card {{ color: #e8e2d6; background: #211f1c; }}
/* .word and .formsbig carry explicit dark colours for the paper ground and
   would otherwise stay near-black on the dark one */
.nightMode .word,
.nightMode .formsbig {{ color: #f2ece0; }}
{'.nightMode .word { border-bottom-color: #3d382d; }' if banner else ''}
.nightMode .qual,
.nightMode .word-a   {{ color: #8b8477; }}
.nightMode .forms    {{ color: #b0a897; }}
.nightMode .forms-q  {{ color: #d6cfc0; }}
.nightMode .en       {{ color: #bdb6a6; }}
.nightMode .small    {{ color: #a49c8b; }}
.nightMode .en-main,
.nightMode a.hint    {{ color: {accent_night}; }}
.nightMode .par th   {{ color: #8b8477; }}
.nightMode .par th.hd {{ color: #d6a233; }}

b {{ font-weight: 700; }}
.replay {{ font-size: .62em; opacity: .45; vertical-align: .12em; }}
"""


# ------------------------------------------------------------------------
# a) amber only. The English answer is told apart by font, italic and weight
#    — no colour at all — which is the quietest the card can be while still
#    reading as an answer.
RAMUS = build(
    accent="#3a3128", accent_night="#e8e2d6",
    rule=f"border: none; border-top: 2px solid {AMBER}; width: 52px; "
         f"margin: 18px auto; opacity: .85;",
    forms_rule="")

# b) the baseline, with the red dropped and the green darkened so it holds up
#    against the cream.
ZALIAS = build(
    accent=GREEN, accent_night=GREEN_N,
    rule="border: none; border-top: 1px solid #e6dcc6; margin: 16px 0;",
    forms_rule=f"border-top: 2px solid {AMBER}; display: inline-block; "
               f"padding-top: 6px;")

# c) the headword sits in its own band, so every card has the same visible
#    header line whether it opens with a word or with a definition.
ANTRASTE = build(
    accent=GREEN, accent_night=GREEN_N, banner=True,
    rule=f"border: none; border-top: 2px solid {AMBER}; width: 52px; "
         f"margin: 18px auto;",
    forms_rule="")

# d) all three colours, as the flag itself: the answer separator is a 54x6
#    block of yellow over green over red. Small enough to read as a rule,
#    unmistakable close up.
PILNA = build(
    accent=GREEN, accent_night=GREEN_N,
    rule=f"border: none; width: 54px; height: 6px; margin: 20px auto; "
         f"border-radius: 1px; background: linear-gradient({AMBER} 0 33.34%, "
         f"{GREEN} 33.34% 66.67%, {RED} 66.67% 100%);",
    forms_rule=f"border-top: 2px solid {AMBER}; display: inline-block; "
               f"padding-top: 6px;")

THEMES = {"2a-ramus": RAMUS, "2b-zalias": ZALIAS,
          "2c-antraste": ANTRASTE, "2d-pilna": PILNA}
