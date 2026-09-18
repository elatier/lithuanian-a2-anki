#!/usr/bin/env python3
"""theme_preview.py — render real cards under candidate CSS themes.

Builds notes with ltcard's own templates and field values (audio stubbed out),
then writes one HTML page per theme showing every card state side by side, in
Anki's light and dark modes. Screenshot the pages to compare themes.

    python3 scripts/theme_preview.py  # writes preview/<theme>.html
"""
import html
import re
import sys
from pathlib import Path

import ltcard
import paths

# which module supplies THEMES, and where the pages go
_mod = sys.argv[1] if len(sys.argv) > 1 else "themes_candidates"
_out = sys.argv[2] if len(sys.argv) > 2 else str(paths.OUT / "preview")
TC = __import__(_mod)

WORDS = ["vaistinė", "traukinys", "aš"]


def build_notes():
    media, errors = [], []
    media_dir = paths.MEDIA
    media_dir.mkdir(exist_ok=True)
    out = {}
    for path in paths.batch_files():
        defs = ltcard.load_defs(str(path))
        for w in WORDS:
            if w in defs and w not in out:
                n = []
                ltcard.process_word(w, "astra", media_dir, defs, n, media,
                                    errors)
                if n:
                    out[w] = n[0]
    return [out[w] for w in WORDS if w in out]


FIELDS = ["Word", "Accented", "POS", "FormsLine", "EN_Word", "LT_Def",
          "Pavyzdys", "English", "Vertimas", "Vertimai",
          "WordAudio", "FormsAudio", "DefAudio", "ExAudio"]


def render(tmpl, note):
    """Expand an Anki template against a note's fields.

    Supports the three constructs these templates use: {{Field}},
    {{hint:Field}} and the {{#F}}…{{/F}} / {{^F}}…{{/F}} conditionals.
    [sound:…] is replaced by Anki's play button glyph so the layout matches
    what the learner actually sees.
    """
    f = dict(zip(FIELDS, note.fields))

    def cond(m):
        neg, name, body = m.group(1) == "^", m.group(2), m.group(3)
        filled = bool(f.get(name, "").strip())
        return body if (filled != neg) else ""

    tmpl = re.sub(r"\{\{([#^])(\w+)\}\}(.*?)\{\{/\2\}\}", cond, tmpl,
                  flags=re.S)
    tmpl = re.sub(r"\{\{hint:(\w+)\}\}",
                  lambda m: f'<a class="hint" href="#">{m.group(1)}</a>'
                            f'<div class="hint-shown">{f.get(m.group(1), "")}'
                            f'</div>', tmpl)
    tmpl = re.sub(r"\{\{(\w+)\}\}", lambda m: f.get(m.group(1), ""), tmpl)
    tmpl = tmpl.replace('<hr id="answer">', '<hr id="answer">')
    return re.sub(r"\[sound:[^\]]+\]", '<span class="replay">▶</span>', tmpl)


STATES = [("Card 1 — front", 0, "qfmt"), ("Card 1 — back", 0, "afmt"),
          ("Card 2 — front", 1, "qfmt"), ("Card 2 — back", 1, "afmt")]

PAGE = """<!doctype html><meta charset="utf-8">
<title>{name}</title>
<style>
body {{ margin:0; font-family:-apple-system,Segoe UI,sans-serif;
        background:#e9e9ee; }}
h1 {{ font-size:17px; margin:18px 20px 4px; color:#333;
      font-weight:600; letter-spacing:.01em; }}
h2 {{ font-size:12px; margin:14px 20px 2px; color:#888; font-weight:600;
      text-transform:uppercase; letter-spacing:.08em; }}
.row {{ display:flex; gap:14px; padding:0 20px 14px; flex-wrap:nowrap; }}
.pane {{ flex:1 1 0; min-width:0; border-radius:14px; overflow:hidden;
         box-shadow:0 1px 4px rgba(0,0,0,.14); background:#fff; }}
.cap {{ font-size:11px; color:#8a8a92; padding:7px 12px 0; background:inherit;
        letter-spacing:.05em; text-transform:uppercase; }}
.night .pane {{ background:#2f2f31; }}
.night .cap {{ color:#8a8a92; }}
.stage {{ padding:16px 14px 20px; }}
{css}
/* preview-only: Anki hides hint contents until tapped; show them so the
   full card is visible in one shot */
.hint-shown {{ display:block; }}
a.hint {{ display:none; }}
.replay {{ font-size:.62em; opacity:.42; vertical-align:.12em; }}
/* no hr rule here: each theme styles hr#answer itself, and a rule at the same
   specificity later in the sheet would silently win */
</style>
{body}
"""


def main():
    notes = build_notes()
    if len(notes) < len(WORDS):
        sys.exit(f"only built {len(notes)} of {len(WORDS)} sample notes")
    outdir = Path(_out)
    outdir.mkdir(parents=True, exist_ok=True)
    for name, css in TC.THEMES.items():
        body = []
        for note, word in zip(notes, WORDS):
            body.append(f"<h1>{html.escape(word)}</h1>")
            for mode, cls in (("light", "card"), ("dark", "card nightMode")):
                body.append(f'<h2>{mode}</h2><div class="row'
                            + (' night' if mode == "dark" else "") + '">')
                for label, ti, side in STATES:
                    tmpl = ltcard.MODEL.templates[ti][side]
                    inner = render(tmpl, note)
                    body.append(
                        f'<div class="pane"><div class="cap">{label}</div>'
                        f'<div class="stage"><div class="{cls}">{inner}</div>'
                        f'</div></div>')
                body.append("</div>")
        p = outdir / f"{name}.html"
        p.write_text(PAGE.format(name=name, css=css, body="\n".join(body)),
                     encoding="utf-8")
        print("wrote", p)


if __name__ == "__main__":
    main()
