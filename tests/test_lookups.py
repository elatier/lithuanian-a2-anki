"""kaikki.org and Wiktionary lookups. Answers are cached for good, so the
important property is that only a real answer is ever cached: an outage, an
error page or another language's table must not be written down as fact."""
import json

import pytest
import requests

import ltcard
import paths
from conftest import FakeResponse, Script

LT_TABLE = ('<table class="inflection-table"><tr><th>nominative</th>'
            '<td>namas</td></tr></table>')
FR_TABLE = ('<table class="inflection-table"><tr><th>nominative</th>'
            '<td>maison</td></tr></table>')


def page(*sections):
    return "<html><body>" + "".join(
        f'<section><h2 id="{lang}">{lang}</h2>{body}</section>'
        for lang, body in sections) + "</body></html>"


def kaikki(monkeypatch, *steps, word="namas"):
    get = Script(*steps)
    monkeypatch.setattr(ltcard.requests, "get", get)
    return ltcard.kaikki_entries(word), get


def wikt(monkeypatch, *steps, word="namas"):
    get = Script(*steps)
    monkeypatch.setattr(ltcard.requests, "get", get)
    return ltcard.wikt_lt_tables(word), get


# ------------------------------------------------------------------ kaikki --

def test_kaikki_answer_is_parsed_and_cached(monkeypatch, caches, sleeps):
    entry = {"word": "namas", "pos": "noun"}
    got, _ = kaikki(monkeypatch, FakeResponse(200, json.dumps(entry)))
    assert got == [entry]
    assert (paths.KAIKKI_CACHE / "namas.jsonl").exists()


def test_kaikki_cache_hit_makes_no_request(monkeypatch, caches, sleeps):
    paths.KAIKKI_CACHE.mkdir()
    (paths.KAIKKI_CACHE / "namas.jsonl").write_text('{"pos": "noun"}')
    got, get = kaikki(monkeypatch)
    assert got == [{"pos": "noun"}] and get.calls == []


def test_kaikki_requests_have_a_timeout(monkeypatch, caches, sleeps):
    _, get = kaikki(monkeypatch, FakeResponse(200, '{"pos": "noun"}'))
    assert get.calls[0][1]["timeout"]


def test_kaikki_404_is_cached_as_absent(monkeypatch, caches, sleeps):
    got, get = kaikki(monkeypatch, *[FakeResponse(404)] * 3)
    assert got == []
    assert (paths.KAIKKI_CACHE / "namas.jsonl").read_text() == ""
    assert len(get.calls) == 3      # a 404 is double-checked before believed


def test_kaikki_html_error_page_is_not_cached(monkeypatch, caches, sleeps):
    got, _ = kaikki(monkeypatch,
                    FakeResponse(200, "<html>Please log in to the Wi-Fi</html>"))
    assert got == []
    assert not (paths.KAIKKI_CACHE / "namas.jsonl").exists()


def test_kaikki_server_error_is_not_cached(monkeypatch, caches, sleeps):
    got, _ = kaikki(monkeypatch, *[FakeResponse(502, "Bad Gateway")] * 4)
    assert got == []
    assert not (paths.KAIKKI_CACHE / "namas.jsonl").exists()


def test_kaikki_timeouts_raise_and_cache_nothing(monkeypatch, caches, sleeps):
    with pytest.raises(requests.Timeout):
        kaikki(monkeypatch, *[requests.Timeout()] * 4)
    assert not (paths.KAIKKI_CACHE / "namas.jsonl").exists()


def test_kaikki_recovers_from_a_timeout(monkeypatch, caches, sleeps):
    got, _ = kaikki(monkeypatch, requests.Timeout(),
                    FakeResponse(200, '{"pos": "noun"}'))
    assert got == [{"pos": "noun"}]


def test_kaikki_retries_back_off(monkeypatch, caches, sleeps):
    kaikki(monkeypatch, *[FakeResponse(503)] * 4)
    assert sleeps == sorted(sleeps) and sleeps[0] > 0


# --------------------------------------------------------------- wiktionary --

def test_wikt_takes_only_the_lithuanian_section(monkeypatch, caches, sleeps):
    tables, _ = wikt(monkeypatch, FakeResponse(200, page(
        ("French", FR_TABLE), ("Lithuanian", LT_TABLE))))
    assert [t.td.text for t in tables] == ["namas"]


def test_wikt_page_without_lithuanian_has_no_tables(monkeypatch, caches,
                                                    sleeps):
    """Used to fall back to the whole page: French tables read as Lithuanian."""
    tables, _ = wikt(monkeypatch, FakeResponse(200, page(("French", FR_TABLE))))
    assert tables == []
    # a real page with no Lithuanian entry is a permanent answer: cached
    assert (paths.WIKT_CACHE / "namas.html").read_text() == ""


def test_wikt_unsectioned_html_stops_at_next_language(monkeypatch, caches,
                                                      sleeps):
    html = (f'<h2 id="Lithuanian">Lithuanian</h2>{LT_TABLE}'
            f'<h2 id="Latvian">Latvian</h2>{FR_TABLE}')
    tables, _ = wikt(monkeypatch, FakeResponse(200, html))
    assert [t.td.text for t in tables] == ["namas"]


def test_wikt_non_wiki_200_is_not_cached(monkeypatch, caches, sleeps):
    tables, _ = wikt(monkeypatch, FakeResponse(200, "<html>Sign in</html>"))
    assert tables == []
    assert not (paths.WIKT_CACHE / "namas.html").exists()


def test_wikt_404_is_cached_as_absent(monkeypatch, caches, sleeps):
    tables, _ = wikt(monkeypatch, *[FakeResponse(404)] * 3)
    assert tables == []
    assert (paths.WIKT_CACHE / "namas.html").read_text() == ""


def test_wikt_server_error_is_not_cached(monkeypatch, caches, sleeps):
    tables, _ = wikt(monkeypatch, *[FakeResponse(500)] * 4)
    assert tables == []
    assert not (paths.WIKT_CACHE / "namas.html").exists()


def test_wikt_timeouts_raise_and_cache_nothing(monkeypatch, caches, sleeps):
    with pytest.raises(requests.Timeout):
        wikt(monkeypatch, *[requests.Timeout()] * 4)
    assert not (paths.WIKT_CACHE / "namas.html").exists()


def test_wikt_cached_answer_survives_a_reload(monkeypatch, caches, sleeps):
    wikt(monkeypatch, FakeResponse(200, page(("Lithuanian", LT_TABLE))))
    tables, get = wikt(monkeypatch)                 # second call: cache only
    assert get.calls == [] and [t.td.text for t in tables] == ["namas"]
