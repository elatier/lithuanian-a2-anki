"""The authoring helpers: the drafting packet, --new scaffolding and the
numbers updater. Offline; the dictionary lookups are faked where a word
has no cache."""
import shutil
import sys
from collections import Counter

import pytest

import add_word
import draft_packet
import ltcard
import paths
import update_numbers

SHELF = [{"pos": "noun", "senses": [{"glosses": ["shelf"]}], "forms": []}]
TWO = [{"pos": "noun", "senses": [{"glosses": ["a cut"]}], "forms": []},
       {"pos": "verb", "senses": [{"glosses": ["cut, chop"]}], "forms": []}]


@pytest.fixture
def workspace(tmp_path, monkeypatch, no_network):
    """A batches folder with one card and a copy of the real theme list."""
    b = tmp_path / "batches"
    b.mkdir()
    (b / "batch1.tsv").write_text("namas\tdef\thouse\tdef\tpvz\tex\tnoun\n",
                                  encoding="utf-8")
    theme = tmp_path / "themes.txt"
    shutil.copy(paths.THEME_FILE, theme)
    monkeypatch.setattr(paths, "BATCHES", b)
    monkeypatch.setattr(paths, "THEME_FILE", theme)
    monkeypatch.setattr(ltcard, "THEME_FILE", theme)
    ltcard.load_themes.cache_clear()
    yield b, theme
    ltcard.load_themes.cache_clear()


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["add_word.py", *argv])
    return add_word.main()


def test_new_appends_a_prefilled_row_and_lists_the_theme(workspace, monkeypatch):
    b, theme = workspace
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: SHELF)
    assert run(monkeypatch, "žvakidė", "--new", "--theme", "02") == 0
    assert (b / "batch1.tsv").read_text(encoding="utf-8").endswith(
        "žvakidė\t\tshelf\t\t\t\tnoun\n")
    lines = theme.read_text(encoding="utf-8").splitlines()
    i = lines.index("žvakidė")
    assert lines[i + 1] == "# egzaminas::03-gamta-regionas"     # end of theme 02
    ltcard.load_themes.cache_clear()
    assert ltcard.load_themes()["žvakidė"] == "egzaminas::02-pastatai-ir-namai"


def test_new_prefixes_verbs_with_to_and_needs_pos_when_ambiguous(workspace,
                                                                  monkeypatch,
                                                                  capsys):
    b, _ = workspace
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: TWO)
    assert run(monkeypatch, "kirsti", "--new") == 1
    assert "pass --pos" in capsys.readouterr().out
    assert run(monkeypatch, "kirsti", "--new", "--pos", "verb") == 0
    assert "kirsti\t\tto cut\t\t\t\tverb\n" in (b / "batch1.tsv").read_text()


def test_new_refuses_an_existing_word_and_an_unknown_theme(workspace,
                                                            monkeypatch,
                                                            capsys):
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: SHELF)
    assert run(monkeypatch, "namas", "--new") == 1
    assert "already has a card" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="matches 0 themes"):
        run(monkeypatch, "lentyna", "--new", "--theme", "99-nonsense")


def test_packet_for_a_deck_word(monkeypatch, capsys, no_network):
    monkeypatch.setattr(sys, "argv", ["draft_packet.py", "kelionė"])
    draft_packet.main()
    out = capsys.readouterr().out
    assert "ALREADY IN THE DECK" in out
    assert "glosses: journey" in out and "kelionėje (locative singular)" in out
    assert "egzaminas::06-keliones" in out
    assert "reisas" in out                              # answers 'trip' too
    assert "edit the row in batch6.tsv" in out and "--new" not in out


def test_packet_for_an_unknown_word_lists_the_themes(monkeypatch, capsys,
                                                      no_network):
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: [])
    monkeypatch.setattr(ltcard, "wikt_lt_tables", lambda w: [])
    monkeypatch.setattr(sys, "argv", ["draft_packet.py", "zzz"])
    draft_packet.main()
    out = capsys.readouterr().out
    assert "no entry" in out and "papildoma::18-kalba-ir-gramatika" in out
    assert "ALREADY" not in out


def test_rewrite_restores_stale_numbers():
    readme = (paths.ROOT / "README.md").read_text(encoding="utf-8")
    f = update_numbers.facts()
    stale = readme.replace("1,593", "1,500").replace("| 01 | Asmens tapatybė | 128 |",
                                                     "| 01 | Asmens tapatybė | 1 |")
    assert stale != readme
    assert update_numbers.rewrite(stale, {1500: 1593}, f["per_theme"]) == readme


def test_rewrite_leaves_other_numbers_alone():
    text = "116 MB (115,970,047 bytes), 469 paradigms, 1,469 other"
    assert update_numbers.rewrite(text, {469: 470}, Counter()) == \
        "116 MB (115,970,047 bytes), 470 paradigms, 1,469 other"
