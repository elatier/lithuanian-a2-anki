"""Deciding what to record, recording it patiently, and restoring the
published clips — including when the service keeps failing."""
import hashlib
import json
import zipfile

import pytest

import fetch_audio
import ltcard
import paths
import resume_audio
from conftest import MP3


def a_card(word="žibintas"):
    """A real row from the deck, so its forms resolve from data/cache/."""
    for f in paths.batch_files():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.split("\t", 1)[0] == word:
                return line
    raise LookupError(word)


@pytest.fixture
def media(tmp_path, monkeypatch):
    m = tmp_path / "media"
    m.mkdir()
    monkeypatch.setattr(paths, "MEDIA", m)
    monkeypatch.setattr(resume_audio, "MEDIA", m)
    monkeypatch.setattr(resume_audio, "MANIFEST", m / ".text_manifest.json")
    monkeypatch.setattr(resume_audio, "log", lambda msg: None)
    return m


def tsv(tmp_path, *rows):
    p = tmp_path / "batch.tsv"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return str(p)


def record_all(tmp_path, f):
    """Plan and mark every clip as recorded with its current text."""
    todo, man, _ = resume_audio.plan([f], quiet=True)
    for text, path in todo:
        path.write_bytes(MP3)
        man[path.name] = resume_audio.text_key(text)
    resume_audio.save_manifest(man)
    return todo


# -------------------------------------------------------------- planning ----

def test_new_card_needs_its_four_clips(tmp_path, media, no_network):
    todo, _, stale = resume_audio.plan([tsv(tmp_path, a_card())], quiet=True)
    assert len(todo) == 4 and stale == 0


def test_nothing_to_do_once_recorded(tmp_path, media, no_network):
    f = tsv(tmp_path, a_card())
    record_all(tmp_path, f)
    todo, _, _ = resume_audio.plan([f], quiet=True)
    assert todo == []


def test_edited_definition_rerecords_only_that_clip(tmp_path, media,
                                                    no_network):
    row = a_card().split("\t")
    f = tsv(tmp_path, "\t".join(row))
    record_all(tmp_path, f)
    row[1] = "Visiškai naujas apibrėžimas."
    f = tsv(tmp_path, "\t".join(row))
    todo, _, stale = resume_audio.plan([f], quiet=True)
    assert stale == 1
    assert [t for t, _ in todo] == ["Visiškai naujas apibrėžimas."]
    assert not todo[0][1].exists()          # the outdated clip is gone


def test_clip_without_manifest_entry_is_trusted(tmp_path, media, no_network):
    """Clips recorded before the manifest existed have no entry; they are
    adopted, not re-recorded."""
    f = tsv(tmp_path, a_card())
    record_all(tmp_path, f)
    resume_audio.save_manifest({})
    todo, man, _ = resume_audio.plan([f], quiet=True)
    assert todo == [] and len(man) == 4


def test_empty_clip_counts_as_missing(tmp_path, media, no_network):
    f = tsv(tmp_path, a_card())
    todo = record_all(tmp_path, f)
    todo[0][1].write_bytes(b"")
    again, _, _ = resume_audio.plan([f], quiet=True)
    assert [p for _, p in again] == [todo[0][1]]


# ------------------------------------------------------------- recording ----

def test_record_stops_after_repeated_failures(tmp_path, media, sleeps,
                                              monkeypatch):
    monkeypatch.setattr(resume_audio, "MAX_STALLS", 3)
    calls = []

    def always_down(text, path, *a, **k):
        calls.append(text)
        raise TimeoutError("LIEPA not answering")
    monkeypatch.setattr(ltcard, "make_audio", always_down)
    todo = [("a", media / "a.mp3"), ("b", media / "b.mp3")]
    assert resume_audio.record(todo, {}) == 1
    assert len(calls) == 3                          # gave up, did not loop
    assert sleeps.count(resume_audio.BACKOFF) == 2  # backed off between


def test_record_keeps_what_succeeded(tmp_path, media, sleeps, monkeypatch):
    monkeypatch.setattr(resume_audio, "MAX_STALLS", 2)

    def first_only(text, path, *a, **k):
        if text != "a":
            raise ConnectionError("reset")
        path.write_bytes(MP3)
    monkeypatch.setattr(ltcard, "make_audio", first_only)
    man = {}
    todo = [("a", media / "a.mp3"), ("b", media / "b.mp3")]
    assert resume_audio.record(todo, man) == 1
    saved = json.loads(resume_audio.MANIFEST.read_text())
    assert saved == {"a.mp3": resume_audio.text_key("a")}


def test_record_recovers_after_a_failure(tmp_path, media, sleeps,
                                         monkeypatch):
    fails = iter([True, False, False])

    def flaky(text, path, *a, **k):
        if next(fails):
            raise TimeoutError
        path.write_bytes(MP3)
    monkeypatch.setattr(ltcard, "make_audio", flaky)
    todo = [("a", media / "a.mp3"), ("b", media / "b.mp3")]
    assert resume_audio.record(todo, {}) == 0
    assert (media / "a.mp3").exists() and (media / "b.mp3").exists()


def test_bad_audio_from_service_counts_as_failure(tmp_path, media, sleeps,
                                                  monkeypatch):
    """End to end: a 200 carrying garbage leaves no clip and no manifest
    entry, so the next run records it again."""
    from conftest import FakeResponse, Script
    monkeypatch.setattr(resume_audio, "MAX_STALLS", 2)
    garbage = FakeResponse(payload={"audioAsString": ""})
    monkeypatch.setattr(ltcard.requests, "post", Script(garbage, garbage))
    man = {}
    assert resume_audio.record([("a", media / "a.mp3")], man) == 1
    assert not (media / "a.mp3").exists() and man == {}


# ----------------------------------------------------------- fetch_audio ----

def archive(tmp_path, entries, manifest=None):
    z = tmp_path / "audio.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        zf.writestr(".text_manifest.json", json.dumps(manifest or {}))
    return z


def test_fetch_unpacks_and_keeps_existing(tmp_path, media):
    (media / "lt_keep_w.mp3").write_bytes(b"local")
    z = archive(tmp_path, {"lt_new_w.mp3": MP3, "lt_keep_w.mp3": MP3},
                {"lt_new_w.mp3": "x", "lt_keep_w.mp3": "theirs"})
    resume_audio.save_manifest({"lt_keep_w.mp3": "ours"})
    fetch_audio.unpack(z)
    assert (media / "lt_new_w.mp3").read_bytes() == MP3
    assert (media / "lt_keep_w.mp3").read_bytes() == b"local"
    man = json.loads(resume_audio.MANIFEST.read_text())
    assert man == {"lt_new_w.mp3": "x", "lt_keep_w.mp3": "ours"}


@pytest.mark.parametrize("name", ["../escape.mp3", "sub/dir.mp3",
                                  "script.sh"])
def test_fetch_rejects_unexpected_entries(tmp_path, media, name):
    with pytest.raises(SystemExit):
        fetch_audio.unpack(archive(tmp_path, {name: MP3}))
    assert not (tmp_path / "escape.mp3").exists()


def test_fetch_rejects_a_corrupt_download(tmp_path, media, monkeypatch):
    z = archive(tmp_path, {"lt_x_w.mp3": MP3})
    assert hashlib.sha256(z.read_bytes()).hexdigest() != fetch_audio.SHA256
    monkeypatch.setattr("sys.argv", ["fetch_audio.py", "--zip", str(z)])
    with pytest.raises(SystemExit, match="checksum"):
        fetch_audio.main()
    assert list(media.iterdir()) == []


def test_fetch_download_has_a_timeout(tmp_path, monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout=None):
        seen["timeout"] = timeout
        raise TimeoutError("stalled")
    monkeypatch.setattr(fetch_audio.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TimeoutError):
        fetch_audio.download("https://example.invalid/a.zip",
                             tmp_path / "a.zip")
    assert seen["timeout"]


# ------------------------------------------- planner agrees with the deck ----

def test_planner_names_every_clip_the_deck_uses(no_network):
    """The planner once derived clip names on its own and disagreed with the
    card builder for four words: it recorded clips no card used, and missed
    the ones the cards did. Now every [sound:] the builder writes must be
    exactly a clip the planner would record, with the same text."""
    import re
    planned, referenced = {}, set()
    for f in paths.batch_files():
        planned.update({p.name: t for t, p in resume_audio.clips_for(str(f))})
        defs, notes = ltcard.load_defs(str(f)), []
        real = ltcard.make_audio
        ltcard.make_audio = lambda *a, **k: None
        try:
            for key in defs:
                ltcard.process_word(key, "astra", paths.MEDIA, defs, notes,
                                    [], [])
        finally:
            ltcard.make_audio = real
        for n in notes:
            referenced |= set(re.findall(r"\[sound:([^\]]+)\]",
                                         " ".join(n.fields)))
    assert set(planned) == referenced
    assert ltcard.make_audio is real                # nothing left patched
