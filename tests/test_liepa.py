"""The LIEPA synthesiser: slow, throttled, and sometimes answering 200 with
something that is not audio. A bad answer must never become a clip."""
import base64

import pytest
import requests

import ltcard
from conftest import MP3, FakeResponse, Script, liepa_ok


def synth(monkeypatch, tmp_path, *steps, attempts=3, quota_wait=0):
    post = Script(*steps)
    monkeypatch.setattr(ltcard.requests, "post", post)
    out = tmp_path / "clip.mp3"
    try:
        ltcard.make_audio("labas", out, "astra", attempts=attempts,
                          quota_wait=quota_wait)
    finally:
        # never a half-written file, whatever happened
        assert not (tmp_path / "clip.mp3.part").exists()
    return out, post


def test_success_writes_the_clip(monkeypatch, tmp_path, sleeps):
    out, post = synth(monkeypatch, tmp_path, liepa_ok())
    assert out.read_bytes() == MP3
    assert len(post.calls) == 1


def test_every_request_has_a_timeout(monkeypatch, tmp_path, sleeps):
    _, post = synth(monkeypatch, tmp_path, liepa_ok())
    assert post.calls[0][1]["timeout"] == ltcard.LIEPA_TIMEOUT


def test_existing_clip_is_not_requested_again(monkeypatch, tmp_path, sleeps):
    (tmp_path / "clip.mp3").write_bytes(MP3)
    _, post = synth(monkeypatch, tmp_path)          # no responses scripted
    assert post.calls == []


def test_timeout_then_success_retries(monkeypatch, tmp_path, sleeps):
    out, post = synth(monkeypatch, tmp_path,
                      requests.Timeout(), requests.Timeout(), liepa_ok())
    assert out.read_bytes() == MP3
    assert len(post.calls) == 3


def test_timeouts_every_time_raise_and_write_nothing(monkeypatch, tmp_path,
                                                     sleeps):
    with pytest.raises(requests.Timeout):
        synth(monkeypatch, tmp_path, *[requests.Timeout()] * 3)
    assert not (tmp_path / "clip.mp3").exists()


def test_connection_reset_is_retried(monkeypatch, tmp_path, sleeps):
    out, _ = synth(monkeypatch, tmp_path,
                   requests.ConnectionError("reset by peer"), liepa_ok())
    assert out.exists()


def test_server_error_then_success(monkeypatch, tmp_path, sleeps):
    out, _ = synth(monkeypatch, tmp_path,
                   FakeResponse(503, "Service Unavailable"), liepa_ok())
    assert out.read_bytes() == MP3


def test_quota_without_wait_gives_up_at_once(monkeypatch, tmp_path, sleeps):
    with pytest.raises(RuntimeError, match="403"):
        synth(monkeypatch, tmp_path, FakeResponse(403, "Quota reached"))
    assert not (tmp_path / "clip.mp3").exists()


def test_quota_with_wait_sleeps_then_retries(monkeypatch, tmp_path, sleeps):
    out, _ = synth(monkeypatch, tmp_path, FakeResponse(403, "Quota reached"),
                   liepa_ok(), quota_wait=120)
    assert out.exists()
    assert 120 in sleeps


BAD_200S = {
    "html error page": FakeResponse(200, "<html><body>Bad gateway</body></html>"),
    "json without audio": FakeResponse(payload={"error": "voice not found"}),
    "audio is null": FakeResponse(payload={"audioAsString": None}),
    "invalid base64": FakeResponse(payload={"audioAsString": "%%%not base64"}),
    "empty audio": FakeResponse(payload={"audioAsString": ""}),
    "text, not mp3": FakeResponse(payload={"audioAsString": base64.b64encode(
        b"Internal error: synthesis failed" * 20).decode()}),
    "truncated mp3": FakeResponse(payload={"audioAsString": base64.b64encode(
        MP3[:40]).decode()}),
}


@pytest.mark.parametrize("bad", BAD_200S.values(), ids=BAD_200S.keys())
def test_bad_200_is_never_saved(monkeypatch, tmp_path, sleeps, bad):
    with pytest.raises(ltcard.BadAudio):
        synth(monkeypatch, tmp_path, bad, bad, bad)
    assert not (tmp_path / "clip.mp3").exists()


@pytest.mark.parametrize("bad", BAD_200S.values(), ids=BAD_200S.keys())
def test_bad_200_is_retried(monkeypatch, tmp_path, sleeps, bad):
    out, _ = synth(monkeypatch, tmp_path, bad, liepa_ok())
    assert out.read_bytes() == MP3


def test_interrupted_write_leaves_no_clip(monkeypatch, tmp_path, sleeps):
    """A crash between writing and renaming must not leave a clip that a
    later run would take for a finished one."""
    def boom(self, target):
        raise KeyboardInterrupt
    monkeypatch.setattr(ltcard.Path, "replace", boom)
    monkeypatch.setattr(ltcard.requests, "post", Script(liepa_ok()))
    with pytest.raises(KeyboardInterrupt):
        ltcard.make_audio("labas", tmp_path / "clip.mp3", "astra",
                          attempts=1, quota_wait=0)
    assert not (tmp_path / "clip.mp3").exists()
