"""The numbers in the README, the deck page, the AnkiWeb listing and the
theme taxonomy are derived from the data here, so adding or moving a card
without updating them fails this file rather than shipping a stale claim."""
import re
from collections import Counter

import ltcard
import paths

ROOT = paths.ROOT


def facts():
    themes = ltcard.load_themes()
    notes, per_theme = 0, Counter()
    for f in paths.batch_files():
        for key in ltcard.load_defs(str(f)):
            notes += 1
            slug = themes.get(key.split("#")[0], "be-temos")
            per_theme[int(slug.rsplit("::", 1)[-1][:2])] += 1
    return dict(notes=notes, cards=2 * notes,
                recordings=len(list(paths.MEDIA.glob("*.mp3"))),
                paradigms=len(ltcard.load_manual_forms()),
                per_theme=per_theme)


def n(x):
    return f"{x:,}"


def test_every_theme_entry_has_a_card_and_every_card_a_theme():
    themes = set(ltcard.load_themes())
    heads = {key.split("#")[0] for f in paths.batch_files()
             for key in ltcard.load_defs(str(f))}
    assert heads - themes == set(), "cards with no theme (tagged be-temos)"
    assert themes - heads == set(), "theme-list entries with no card"


def test_readme_numbers():
    f = facts()
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for label, value in (("Cards", f["cards"]), ("Recordings", f["recordings"]),
                         ("Hand-checked paradigms", f["paradigms"])):
        assert f"| {label} | {n(value)}" in text, label
    table = {int(a): int(b) for a, b in
             re.findall(r"\| (\d\d) \| [^|]+ \| (\d+) \|", text)}
    assert table == dict(f["per_theme"])
    assert f"{n(f['notes'])} Lithuanian words" in text     # headline


def test_deck_page_numbers():
    f = facts()
    text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    for value in (f["notes"], f["cards"], f["recordings"], f["paradigms"]):
        assert f"<b>{n(value)}</b>" in text, value
    shown = [int(x) for x in
             re.findall(r'<li>[^<]+<span class="n">(\d+)</span></li>', text)]
    assert shown == [f["per_theme"][i] for i in range(1, 19)]


def test_ankiweb_listing_numbers():
    f = facts()
    text = (ROOT / "ankiweb" / "DESCRIPTION.md").read_text(encoding="utf-8")
    assert (f"{n(f['notes'])} words · {n(f['cards'])} cards · "
            f"{n(f['recordings'])} recordings") in text


def test_theme_taxonomy_split():
    f = facts()
    exam = sum(f["per_theme"][i] for i in range(1, 13))
    text = (paths.DATA / "THEMES.md").read_text(encoding="utf-8")
    assert f"They hold {n(exam)} of the {n(f['notes'])} words" in text
    assert f"hold the remaining {n(f['notes'] - exam)}" in text
