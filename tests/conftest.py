"""Shared fixtures. The tests never touch the network: every request goes
through a fake, and time.sleep is recorded instead of slept."""
import base64
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ltcard  # noqa: E402
import paths  # noqa: E402

MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 400


class FakeResponse:
    def __init__(self, status=200, text="", payload=None):
        self.status_code = status
        self.text = text if payload is None else json.dumps(payload)

    def json(self):
        return json.loads(self.text)


def liepa_ok(data=MP3):
    return FakeResponse(payload={"audioAsString":
                                 base64.b64encode(data).decode()})


class Script:
    """Plays back a list of responses (or exceptions to raise), one per call,
    and remembers what each call was sent."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = []

    def __call__(self, url, **kw):
        self.calls.append((url, kw))
        if not self.steps:
            raise AssertionError(f"unexpected extra request to {url}")
        step = self.steps.pop(0)
        if isinstance(step, BaseException) or (
                isinstance(step, type) and issubclass(step, BaseException)):
            raise step
        return step


@pytest.fixture
def sleeps(monkeypatch):
    """Record time.sleep instead of sleeping."""
    log = []
    monkeypatch.setattr(time, "sleep", log.append)
    return log


@pytest.fixture
def caches(tmp_path, monkeypatch):
    """Point the lookup caches and the media folder at empty temp dirs."""
    monkeypatch.setattr(paths, "KAIKKI_CACHE", tmp_path / "kaikki")
    monkeypatch.setattr(paths, "WIKT_CACHE", tmp_path / "wikt")
    monkeypatch.setattr(paths, "MEDIA", tmp_path / "media")
    (tmp_path / "media").mkdir()
    return tmp_path


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly on any real HTTP request."""
    def refuse(*a, **k):
        raise AssertionError(f"network access attempted: {a[:1]}")
    monkeypatch.setattr(ltcard.requests, "get", refuse)
    monkeypatch.setattr(ltcard.requests, "post", refuse)


def pytest_configure(config):
    # genanki's dependency, not ours
    config.addinivalue_line(
        "filterwarnings", "ignore::DeprecationWarning:cached_property")
