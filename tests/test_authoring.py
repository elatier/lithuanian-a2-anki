"""The authoring helpers: the drafting packet, the scaffolding and the
numbers updater. Offline; the dictionary lookups are faked where a word
has no cache."""
import sys
from collections import Counter

import pytest

import add_word
import draft_packet
import ltcard
import paths
import update_numbers

SHELF = [{"pos": "noun", "senses": [{"glosses": ["shelf"]}],
          "forms": [{"form": "lentynos", "tags": ["genitive", "singular"]}]}]
TWO = [{"pos": "noun", "senses": [{"glosses": ["a cut"]}], "forms": []},
       {"pos": "verb", "senses": [{"glosses": ["cut, chop"]}], "forms": []}]


@pytest.fixture
def workspace(tmp_path, monkeypatch, no_network):
    """A batches folder with one card; words outside the caches are faked."""
    b = tmp_path / "batches"
    b.mkdir()
    (b / "batch1.tsv").write_text(
        "namas\tdef\thouse\tdef\tpvz\tex\tnoun\t02-pastatai-ir-namai\n",
        encoding="utf-8")
    monkeypatch.setattr(paths, "BATCHES", b)
    monkeypatch.setattr(ltcard, "wikt_lt_tables", lambda w: [])
    ltcard.load_themes.cache_clear()
    yield b
    ltcard.load_themes.cache_clear()


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["add_word.py", *argv])
    return add_word.main()


def test_theme_on_a_new_word_prints_the_packet_and_scaffolds(workspace,
                                                            monkeypatch, capsys):
    b = workspace
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: SHELF)
    assert run(monkeypatch, "žvakidė", "--theme", "02") == 0
    out = capsys.readouterr().out
    assert "glosses: shelf" in out and "chosen: egzaminas::02-pastatai-ir-namai" in out
    assert "lentynos (genitive singular)" in out
    assert (b / "batch1.tsv").read_text(encoding="utf-8").endswith(
        "žvakidė\t\tshelf\t\t\t\tnoun\t02-pastatai-ir-namai\n")
    assert ltcard.load_themes()["žvakidė"] == "egzaminas::02-pastatai-ir-namai"


def test_a_new_word_without_a_theme_shows_the_choices_and_writes_nothing(workspace,
                                                                  monkeypatch,
                                                                  capsys):
    b = workspace
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: SHELF)
    before = (b / "batch1.tsv").read_text(encoding="utf-8")
    assert run(monkeypatch, "žvakidė") == 1
    out = capsys.readouterr().out
    assert "18-kalba-ir-gramatika" in out and "rerun with --theme" in out
    assert (b / "batch1.tsv").read_text(encoding="utf-8") == before


def test_scaffold_prefixes_verbs_with_to_and_needs_pos_when_ambiguous(workspace,
                                                                  monkeypatch,
                                                                  capsys):
    b = workspace
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: TWO)
    assert run(monkeypatch, "kirsti", "--theme", "04") == 1
    assert "pass --pos" in capsys.readouterr().out
    assert run(monkeypatch, "kirsti", "--theme", "04", "--pos", "verb") == 0
    assert "kirsti\t\tto cut\t\t\t\tverb\t04-kasdienis-gyvenimas\n" \
        in (b / "batch1.tsv").read_text()


def test_a_word_with_a_row_is_checked_not_scaffolded(workspace, monkeypatch,
                                                      capsys):
    """--theme on an existing word never adds a second row: the state of
    the word decides, and a row means the gate runs."""
    import spell
    monkeypatch.setattr(spell, "unknown_words", lambda text: [])
    b = workspace
    before = (b / "batch1.tsv").read_text(encoding="utf-8")
    assert run(monkeypatch, "namas", "--theme", "02", "--no-audio") == 1
    out = capsys.readouterr().out
    assert "--- QA gate" in out and "[FAIL] namas" in out
    assert (b / "batch1.tsv").read_text(encoding="utf-8") == before


def test_unknown_theme_writes_nothing(workspace, monkeypatch):
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: SHELF)
    with pytest.raises(SystemExit, match="matches 0 of"):
        run(monkeypatch, "lentyna", "--theme", "99-nonsense")


def test_packet_for_a_deck_word(monkeypatch, capsys, no_network):
    monkeypatch.setattr(sys, "argv", ["draft_packet.py", "kelionė"])
    draft_packet.main()
    out = capsys.readouterr().out
    assert "ALREADY IN THE DECK" in out
    assert "glosses: journey" in out and "kelionėje (locative singular)" in out
    assert "the card's row says egzaminas::06-keliones" in out
    assert "reisas" in out                              # answers 'trip' too
    assert "edit the row in batch6.tsv" in out and "--new" not in out


def test_packet_for_an_unknown_word_lists_the_themes(monkeypatch, capsys,
                                                      no_network):
    monkeypatch.setattr(ltcard, "kaikki_entries", lambda w: [])
    monkeypatch.setattr(ltcard, "wikt_lt_tables", lambda w: [])
    monkeypatch.setattr(sys, "argv", ["draft_packet.py", "zzz"])
    draft_packet.main()
    out = capsys.readouterr().out
    assert "no entry" in out and "18-kalba-ir-gramatika" in out
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


def test_list_scaffolds_a_whole_batch_into_the_next_file(workspace,
                                                              monkeypatch,
                                                              tmp_path, capsys):
    b = workspace
    monkeypatch.setattr(ltcard, "kaikki_entries",
                        lambda w: TWO if w == "kirsti" else SHELF)
    lst = tmp_path / "words.tsv"
    lst.write_text("# a batch\nžvakidė\t02\nkirsti\t04-kasdienis\tverb\n",
                   encoding="utf-8")
    assert run(monkeypatch, "--list", str(lst)) == 0
    new = (b / "batch2.tsv").read_text(encoding="utf-8")
    assert new == ("žvakidė\t\tshelf\t\t\t\tnoun\t02-pastatai-ir-namai\n"
                   "kirsti\t\tto cut\t\t\t\tverb\t04-kasdienis-gyvenimas\n")
    assert "add_word.py --batch batch2" in capsys.readouterr().out
    t = ltcard.load_themes()
    assert t["žvakidė"].endswith("02-pastatai-ir-namai")
    assert t["kirsti"].endswith("04-kasdienis-gyvenimas")


def test_list_writes_nothing_when_a_theme_is_wrong(workspace, monkeypatch,
                                                        tmp_path):
    b = workspace
    lst = tmp_path / "words.tsv"
    lst.write_text("žvakidė\t02\nkirsti\t99\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="matches 0 of"):
        run(monkeypatch, "--list", str(lst))
    assert not (b / "batch2.tsv").exists()
