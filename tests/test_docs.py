"""The numbers in the README, the deck page, the AnkiWeb listing and the
theme taxonomy are derived from the data here, so adding or moving a card
without updating them fails this file rather than shipping a stale claim."""
import re

import ltcard
import paths
import update_numbers

ROOT = paths.ROOT


facts = update_numbers.facts


def n(x):
    return f"{x:,}"


def test_every_row_names_a_theme_from_the_taxonomy():
    tags = ltcard.theme_tags()
    bad = [(f.name, key) for f in paths.batch_files()
           for key, d in ltcard.load_defs(str(f)).items()
           if d["theme"] not in tags]
    assert bad == []


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
    text = (paths.DATA / "THEMES.md").read_text(encoding="utf-8")
    assert f"They hold {n(f['exam'])} of the {n(f['notes'])} words" in text
    assert f"hold the remaining {n(f['extra'])}" in text


def test_update_numbers_agrees_with_these_tests(capsys):
    """The fixer and the checks read the same spots: nothing to update."""
    assert update_numbers.main(check=True) == 0
