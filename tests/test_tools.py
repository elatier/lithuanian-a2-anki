"""hunspell, the one-word workflow, and the offline build."""
import subprocess
import sys

import pytest

import ltcard
import paths
import spell


def hunspell_ready():
    try:
        p = subprocess.run(["hunspell", "-d", str(spell.DICT), "-l"],
                           input="namas", capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return p.returncode == 0


needs_hunspell = pytest.mark.skipif(not hunspell_ready(),
                                    reason="hunspell not installed")


# ---------------------------------------------------------------- hunspell --

def test_missing_dictionary_stops_instead_of_passing(monkeypatch):
    """hunspell without lt_LT prints nothing and exits 1 — which used to
    read as 'no misspellings'."""
    monkeypatch.setattr(spell.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(
                            a, 1, "", "Can't open affix or dictionary files"))
    with pytest.raises(SystemExit, match="Can't open affix"):
        spell.unknown_words("namas")


def test_missing_hunspell_stops(monkeypatch):
    def not_installed(*a, **k):
        raise FileNotFoundError("hunspell")
    monkeypatch.setattr(spell.subprocess, "run", not_installed)
    with pytest.raises(SystemExit, match="not installed"):
        spell.unknown_words("namas")


@needs_hunspell
def test_real_hunspell_flags_only_the_misspelling():
    assert spell.unknown_words("namas kalbėjo xyzzyq") == ["xyzzyq"]


# ---------------------------------------------------------------- add_word --

@pytest.fixture
def one_batch(tmp_path, monkeypatch):
    """A batches folder holding a single real card, and a stubbed
    synthesiser that records what it was asked to say."""
    b = tmp_path / "batches"
    b.mkdir()
    media = tmp_path / "media"
    media.mkdir()
    import resume_audio
    monkeypatch.setattr(paths, "BATCHES", b)
    monkeypatch.setattr(paths, "MEDIA", media)
    monkeypatch.setattr(resume_audio, "MEDIA", media)
    monkeypatch.setattr(resume_audio, "MANIFEST", media / ".text_manifest.json")
    monkeypatch.setattr(resume_audio, "log", lambda m: None)
    monkeypatch.setattr(resume_audio, "GAP", 0)
    spoken = []

    def fake_make_audio(text, path, *a, **k):
        spoken.append(text)
        path.write_bytes(b"ID3" + b"\0" * 400)
    monkeypatch.setattr(ltcard, "make_audio", fake_make_audio)
    real = next(line for f in sorted((paths.DATA / "batches").glob("*.tsv"))
                for line in f.read_text(encoding="utf-8").splitlines()
                if line.startswith("slėnis\t"))
    return b / "batch1.tsv", real.split("\t"), spoken


def run_add_word(monkeypatch, *words):
    import add_word
    monkeypatch.setattr(sys, "argv", ["add_word.py", *words])
    return add_word.main()


@needs_hunspell
def test_add_word_records_new_card_then_only_edits(monkeypatch, one_batch,
                                                   no_network):
    f, row, spoken = one_batch
    f.write_text("\t".join(row) + "\n", encoding="utf-8")
    assert run_add_word(monkeypatch, "slėnis") == 0
    assert len(spoken) == 4

    spoken.clear()
    assert run_add_word(monkeypatch, "slėnis") == 0
    assert spoken == []                             # nothing changed

    row[4] = "Mūsų kaimas yra slėnyje."             # edit the example
    f.write_text("\t".join(row) + "\n", encoding="utf-8")
    assert run_add_word(monkeypatch, "slėnis") == 0
    assert spoken == ["Mūsų kaimas yra slėnyje."]


@needs_hunspell
def test_add_word_records_nothing_when_qa_fails(monkeypatch, one_batch,
                                                no_network):
    f, row, spoken = one_batch
    row[1] = "Slėnis yra žemė tarp kalnų."          # defines itself: LEAK
    f.write_text("\t".join(row) + "\n", encoding="utf-8")
    assert run_add_word(monkeypatch, "slėnis") == 1
    assert spoken == []


def test_add_word_unknown_word(monkeypatch, one_batch, capsys):
    assert run_add_word(monkeypatch, "nėratokio") == 1
    assert "no card" in capsys.readouterr().out


# ------------------------------------------------------------------- build --

def test_build_is_offline_and_complete(tmp_path, monkeypatch, no_network):
    """Everything a build looks up must be in data/cache/: with the network
    refused, --no-fetch still builds every card. (No audio folder, so the
    test deck is small; missing clips are simply left off the cards.)"""
    import build_single
    monkeypatch.setattr(ltcard, "make_audio", ltcard.make_audio)  # restore after
    monkeypatch.setattr(paths, "MEDIA", tmp_path / "media")
    out = tmp_path / "deck.apkg"
    monkeypatch.setattr(sys, "argv", ["build_single.py", "--no-fetch",
                                      "-o", str(out)])
    build_single.main()
    import sqlite3
    import zipfile
    with zipfile.ZipFile(out) as z:
        z.extract("collection.anki2", tmp_path)
    db = sqlite3.connect(tmp_path / "collection.anki2")
    notes = db.execute("select count(*) from notes").fetchone()[0]
    rows = sum(1 for f in paths.batch_files()
               for line in f.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.startswith("#"))
    assert notes == rows
