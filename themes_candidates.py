#!/usr/bin/env python3
"""themes_candidates.py — candidate card themes for the deck.

Each entry is a complete replacement for ltcard.CSS. They all keep the same
class names and the same layout you approved — only typography, colour and
spacing change — so switching theme cannot move anything around.

Anki puts `card cardN` on <body>, and adds `nightMode night_mode` there in dark
mode, so `.card {…}` styles the page and `.nightMode .word {…}` overrides a
child. Every theme here carries a full dark set; the current deck CSS has none,
which is why the cards are black-on-cream even in Anki's dark mode.
"""

# --------------------------------------------------------------- shared ----
# The paradigm table and the play button behave the same everywhere.
_COMMON = """
b { font-weight: 700; }
.replay { font-size: .62em; opacity: .45; vertical-align: .12em; }
"""

# ============================================================ 1. Švarus ====
# Clean and neutral: the current design, tidied. One accent colour, used only
# for the English answer line and the hint link. Nothing decorative.
SVARUS = """
.card { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        sans-serif; font-size: 22px; text-align: center;
        color: #23252b; background: #fbfbfa; line-height: 1.45; }

.word    { font-size: 34px; font-weight: 700; letter-spacing: -.01em; }
.qual    { font-weight: 400; color: #8a8f98; }
.forms   { font-size: 19px; color: #5b6068; margin: 6px 0; }
.forms-q { font-size: 23px; font-weight: 600; color: #3c414a; margin: 10px 0; }
.formsbig{ font-size: 27px; font-weight: 700; margin: 8px 0; }
.lt      { font-size: 21px; margin: 12px 0; }
.en      { font-size: 20px; color: #4a4f57; margin: 8px 0; font-style: italic; }
.small   { font-size: 19px; margin-top: 12px; font-style: italic;
           color: #6b7078; }
.en-main { font-size: 28px; font-weight: 700; font-style: italic;
           color: #1a5f7a; margin: 14px 0; }
.word-a  { font-size: 24px; font-weight: 400; color: #8a8f98; margin: 12px 0; }
a.hint   { color: #1a5f7a; font-size: 19px; text-decoration: none;
           font-style: normal; }
hr#answer { border: none; border-top: 1px solid #e2e2df; margin: 16px 0; }

.par    { margin: 14px auto; border-collapse: collapse; font-size: 19px; }
.par th { color: #9aa0a8; font-weight: 400; text-align: right; font-size: 17px;
          padding: 3px 12px 3px 0; }
.par td { text-align: left; padding: 3px 18px 3px 0; }
.par th.hd { color: #9aa0a8; text-align: left; font-size: 15px;
             letter-spacing: .06em; text-transform: uppercase;
             padding-top: 10px; }

.nightMode.card, .nightMode .card { color: #e4e5e7; background: #26272b; }
.nightMode .qual,
.nightMode .word-a   { color: #85898f; }
.nightMode .forms    { color: #a8acb3; }
.nightMode .forms-q  { color: #c8ccd2; }
.nightMode .en       { color: #b8bcc2; }
.nightMode .small    { color: #9ea2a9; }
.nightMode .en-main,
.nightMode a.hint    { color: #6fb6d4; }
.nightMode hr#answer { border-top-color: #3a3c42; }
.nightMode .par th,
.nightMode .par th.hd { color: #8b9097; }
""" + _COMMON

# ======================================================== 2. Trispalvė ====
# The flag's three colours, used as signal rather than decoration: yellow
# marks the Lithuanian answer, green the English one, red only the rule under
# the question. Warm paper ground. Slightly more character, same restraint.
TRISPALVE = """
.card { font-family: "Charter", "Iowan Old Style", Georgia,
        -apple-system, serif; font-size: 22px; text-align: center;
        color: #2b2620; background: #fdfaf2; line-height: 1.5; }

.word    { font-size: 35px; font-weight: 700; color: #1f1b16;
           letter-spacing: -.005em; }
.qual    { font-weight: 400; color: #9a9284; }
.forms   { font-size: 19px; color: #6a6255; margin: 6px 0; }
.forms-q { font-size: 23px; font-weight: 600; color: #4a4335; margin: 10px 0;
           border-top: 2px solid #fdb913; display: inline-block;
           padding-top: 6px; }
.formsbig{ font-size: 27px; font-weight: 700; margin: 8px 0; color: #2b2620;
           border-top: 2px solid #fdb913; display: inline-block;
           padding-top: 6px; }
.lt      { font-size: 21px; margin: 12px 0; }
.en      { font-size: 20px; color: #55503f; margin: 8px 0; font-style: italic;
           font-family: -apple-system, "Segoe UI", sans-serif; }
.small   { font-size: 18px; margin-top: 12px; font-style: italic;
           color: #6f6858; font-family: -apple-system, "Segoe UI", sans-serif; }
.en-main { font-size: 27px; font-weight: 700; font-style: italic;
           color: #00694a; margin: 14px 0;
           font-family: -apple-system, "Segoe UI", sans-serif; }
.word-a  { font-size: 24px; font-weight: 400; color: #9a9284; margin: 12px 0; }
a.hint   { color: #00694a; font-size: 19px; text-decoration: none;
           font-style: normal;
           font-family: -apple-system, "Segoe UI", sans-serif; }
hr#answer { border: none; border-top: 2px solid #c1272d; width: 44px;
            margin: 18px auto; opacity: .5; }

.par    { margin: 14px auto; border-collapse: collapse; font-size: 19px; }
.par th { color: #a89f8d; font-weight: 400; text-align: right; font-size: 17px;
          padding: 3px 12px 3px 0; }
.par td { text-align: left; padding: 3px 18px 3px 0; }
.par th.hd { color: #b8891a; text-align: left; font-size: 14px;
             letter-spacing: .08em; text-transform: uppercase;
             padding-top: 10px; }

.nightMode.card, .nightMode .card { color: #e8e2d6; background: #211f1c; }
.nightMode .word,
/* .formsbig sets an explicit dark colour for the light ground; without this
   it stays near-black on the dark ground and the card-2 answer vanishes */
.nightMode .formsbig { color: #f2ece0; }
.nightMode .qual,
.nightMode .word-a   { color: #8b8477; }
.nightMode .forms    { color: #b0a897; }
.nightMode .forms-q  { color: #d6cfc0; }
.nightMode .en       { color: #bdb6a6; }
.nightMode .small    { color: #a49c8b; }
.nightMode .en-main,
.nightMode a.hint    { color: #4fbe8f; }
.nightMode .par th   { color: #8b8477; }
.nightMode .par th.hd { color: #d6a233; }
""" + _COMMON

# ======================================================= 3. Kontrastas ====
# Built for a phone at arm's length: bigger type, heavier weights, more air,
# near-maximum contrast. Nothing grey enough to disappear in sunlight.
KONTRASTAS = """
.card { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        sans-serif; font-size: 24px; text-align: center;
        color: #101114; background: #ffffff; line-height: 1.5;
        padding: 4px 2px; }

.word    { font-size: 40px; font-weight: 800; letter-spacing: -.02em;
           margin: 6px 0; }
.qual    { font-weight: 500; color: #565b63; }
.forms   { font-size: 21px; color: #33373d; margin: 10px 0; font-weight: 500; }
.forms-q { font-size: 26px; font-weight: 700; color: #1c1e22; margin: 14px 0; }
.formsbig{ font-size: 30px; font-weight: 800; margin: 12px 0; }
.lt      { font-size: 23px; margin: 16px 0; }
.en      { font-size: 22px; color: #2a2d33; margin: 12px 0;
           font-style: italic; }
.small   { font-size: 20px; margin-top: 16px; font-style: italic;
           color: #3d4148; }
.en-main { font-size: 31px; font-weight: 800; font-style: italic;
           color: #0b4fa8; margin: 18px 0; }
.word-a  { font-size: 26px; font-weight: 500; color: #565b63; margin: 14px 0; }
a.hint   { color: #0b4fa8; font-size: 20px; text-decoration: none;
           font-style: normal; font-weight: 600; }
hr#answer { border: none; border-top: 2px solid #c9ccd1; margin: 20px 0; }

.par    { margin: 18px auto; border-collapse: collapse; font-size: 21px; }
.par th { color: #5c616a; font-weight: 500; text-align: right; font-size: 18px;
          padding: 5px 14px 5px 0; }
.par td { text-align: left; padding: 5px 20px 5px 0; font-weight: 500; }
.par th.hd { color: #0b4fa8; text-align: left; font-size: 15px;
             letter-spacing: .08em; text-transform: uppercase;
             padding-top: 14px; font-weight: 700; }

.nightMode.card, .nightMode .card { color: #f7f8fa; background: #000000; }
.nightMode .qual,
.nightMode .word-a   { color: #a7adb6; }
.nightMode .forms    { color: #d2d6dc; }
.nightMode .forms-q  { color: #f0f2f5; }
.nightMode .en       { color: #dfe2e7; }
.nightMode .small    { color: #c3c8cf; }
.nightMode .en-main,
.nightMode a.hint    { color: #74b4ff; }
.nightMode hr#answer { border-top-color: #3c4149; }
.nightMode .par th   { color: #a7adb6; }
.nightMode .par th.hd { color: #74b4ff; }
""" + _COMMON

THEMES = {"1-svarus": SVARUS,
          "2-trispalve": TRISPALVE,
          "3-kontrastas": KONTRASTAS}
