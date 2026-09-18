#!/usr/bin/env python3
"""update_numbers.py — rewrite the deck's numbers in the docs from the data.

The README, the deck page (docs/index.html), the AnkiWeb listing (ankiweb/)
and data/THEMES.md all quote the note, card, recording and paradigm counts
and the size of every theme. tests/test_docs.py fails while any of them
disagrees with the batch files; this is the fix.

    python3 scripts/update_numbers.py            # rewrite, report what changed
    python3 scripts/update_numbers.py --check    # exit 1 if anything is stale
"""
import re
import sys
from collections import Counter

import ltcard
import paths

ROOT = paths.ROOT
FILES = [ROOT / "README.md", ROOT / "docs" / "index.html",
         ROOT / "ankiweb" / "DESCRIPTION.md", ROOT / "ankiweb" / "SHARE_FORM.md",
         paths.DATA / "THEMES.md"]


def facts():
    """The counts every document quotes, straight from the data."""
    themes = ltcard.load_themes()
    notes, per_theme = 0, Counter()
    for f in paths.batch_files():
        for key in ltcard.load_defs(str(f)):
            notes += 1
            leaf = themes.get(key.split("#")[0], "be-temos").rsplit("::", 1)[-1]
            # a card with no theme counts under 0: the docs will not add up,
            # and test_docs names the word
            per_theme[int(leaf[:2]) if leaf[:2].isdigit() else 0] += 1
    exam = sum(per_theme[i] for i in range(1, 13))
    return dict(notes=notes, cards=2 * notes,
                recordings=len(list(paths.MEDIA.glob("*.mp3"))),
                paradigms=len(ltcard.load_manual_forms()),
                exam=exam, extra=notes - exam, per_theme=per_theme)


def n(x):
    return f"{x:,}"


def quoted(readme, themes_md):
    """The numbers the docs currently quote, read from their canonical spots."""
    def grab(pattern, text):
        m = re.search(pattern, text)
        return int(m.group(1).replace(",", "")) if m else None
    return dict(
        notes=grab(r"\| Words \| ([\d,]+)", readme),
        cards=grab(r"\| Cards \| ([\d,]+)", readme),
        recordings=grab(r"\| Recordings \| ([\d,]+)", readme),
        paradigms=grab(r"\| Hand-checked paradigms \| ([\d,]+)", readme),
        exam=grab(r"They hold ([\d,]+) of the", themes_md),
        extra=grab(r"hold the remaining ([\d,]+)", themes_md))


def rewrite(text, mapping, per_theme):
    """Swap every quoted total for the current one, and the theme sizes."""
    if mapping:
        alt = "|".join(re.escape(n(old)) for old in mapping)
        text = re.sub(rf"(?<![\d,]){alt}(?![\d,])",
                      lambda m: n(mapping[int(m.group(0).replace(',', ''))]), text)
    # README theme table: "| 01 | Asmens tapatybė | 128 |"
    text = re.sub(r"(\| (\d\d) \| [^|]+ \| )\d+( \|)",
                  lambda m: f"{m.group(1)}{per_theme[int(m.group(2))]}{m.group(3)}",
                  text)
    # deck page theme list: "<li>Asmens tapatybė <span class="n">128</span></li>"
    i = iter(range(1, 19))
    text = re.sub(r'(<li>[^<]+<span class="n">)\d+(</span></li>)',
                  lambda m: f"{m.group(1)}{per_theme[next(i)]}{m.group(2)}", text)
    return text


def main(check=False):
    f = facts()
    texts = {p: p.read_text(encoding="utf-8") for p in FILES}
    old = quoted(texts[FILES[0]], texts[FILES[-1]])
    missing = [k for k, v in old.items() if v is None]
    if missing:
        sys.exit(f"could not find the current {', '.join(missing)} in the docs")
    mapping = {old[k]: f[k] for k in old if old[k] != f[k]}
    changed = []
    for p, text in texts.items():
        new = rewrite(text, mapping, f["per_theme"])
        if new != text:
            changed.append(p)
            if not check:
                p.write_text(new, encoding="utf-8")
    if not changed:
        print(f"up to date: {n(f['notes'])} notes, {n(f['cards'])} cards, "
              f"{n(f['recordings'])} recordings, {f['paradigms']} paradigms.")
        return 0
    for k, v in mapping.items():
        print(f"  {n(k)} -> {n(v)}")
    verb = "stale" if check else "updated"
    print(f"{verb}: " + ", ".join(p.relative_to(ROOT).as_posix() for p in changed))
    return 1 if check else 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv[1:]))
