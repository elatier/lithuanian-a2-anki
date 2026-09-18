"""Render the pronoun cards under the live theme, backs only (that is where
the table and the definition live). Writes out/preview_pron/pronouns.html."""
import html
import sys

import ltcard
import paths
import theme_preview as TP

WORDS = ["jie", "tie", "šie", "tas", "šis", "kuris", "kas", "savo", "jos"]


def main():
    TP.WORDS = WORDS
    notes = {}
    for p in paths.batch_files():
        d = ltcard.load_defs(str(p))
        for w in WORDS:
            if w in d and w not in notes:
                n = []
                ltcard.process_word(w, "astra", paths.MEDIA, d, n, [], [],
                                    tts=lambda *a, **k: None)
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
    out = paths.OUT / "preview_pron" / "pronouns.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        TP.PAGE.format(name="pronouns", css=ltcard.CSS, body="\n".join(body)),
        encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
