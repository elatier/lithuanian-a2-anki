"""Render the pronoun cards under the live theme, backs only (that is where
the table and the definition live)."""
import html, sys
from pathlib import Path
import ltcard, paths, theme_preview as TP

WORDS = ["jie", "tie", "šie", "tas", "šis", "kuris", "kas", "savo", "jos"]
TP.WORDS = WORDS
notes = {}
ltcard.make_audio = lambda *a, **k: None
for p in paths.batch_files():
    d = ltcard.load_defs(str(p))
    for w in WORDS:
        if w in d and w not in notes:
            n = []
            ltcard.process_word(w, "astra", paths.MEDIA, d, n, [], [])
            if n:
                notes[w] = n[0]
missing = [w for w in WORDS if w not in notes]
if missing:
    sys.exit(f"no note built for {missing}")

body = []
for w in WORDS:
    body.append(f"<h1>{html.escape(w)}</h1><div class='row'>")
    for label, ti, side in TP.STATES:
        inner = TP.render(ltcard.MODEL.templates[ti][side], notes[w])
        body.append(f"<div class='pane'><div class='cap'>{label}</div>"
                    f"<div class='stage'><div class='card'>{inner}</div>"
                    f"</div></div>")
    body.append("</div>")
Path("preview_pron").mkdir(exist_ok=True)
Path("preview_pron/pronouns.html").write_text(
    TP.PAGE.format(name="pronouns", css=ltcard.CSS, body="\n".join(body)),
    encoding="utf-8")
print("wrote preview_pron/pronouns.html")
