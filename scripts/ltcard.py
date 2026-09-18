"""ltcard.py — the card builder: note type, templates, CSS, the Wiktionary
and kaikki.org lookups, and the LIEPA synthesiser call.

One note -> two cards.

CARD 1  Word card
  FRONT: word (bold) + audio; LT example + audio, word bolded
  BACK:  the word again above the rule, then EN word (bold italic);
         forms + audio; LT definition + audio; LT example + audio;
         pronoun table; hint "Vertimai" -> EN definition · EN example
  English is italic everywhere, hints included, so it never reads as Lithuanian.

CARD 2  Definition card
  FRONT: LT definition (word-free) + audio; hint "English" -> EN definition
  BACK:  EN word (bold italic, as on card 1); forms + audio; LT example +
         audio; pronoun table; the word itself last, muted and silent;
         hint "Vertimas" -> EN example

Forms line: nouns nom sg/pl · verbs principal parts (inf, pres3, past3)
· adjectives masc/fem. The inflected word inside the example is bolded
automatically by matching against all Wiktionary forms.

Sources: en.wiktionary.org tables + kaikki.org, both cached under data/cache/
so a build needs no network. Definitions, examples and translations come from
the batch files (see load_defs). Words not found on Wiktionary and not in
manual_forms.tsv are skipped, never invented.

This module has no command line of its own: build_single.py builds the deck,
resume_audio.py records the clips, verify_defs.py is the QA gate.
"""

import asyncio
import functools
import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import genanki

import paths

WIKT_HTML = "https://en.wiktionary.org/api/rest_v1/page/html/{}"
KAIKKI = "https://kaikki.org/dictionary/Lithuanian/meaning/{a}/{ab}/{w}.jsonl"
HEADERS = {"User-Agent": "ltcard/4.0 (personal flashcard tool)"}
POSES = {"noun", "verb", "adj"}


def _get(url, tries=4):
    import time
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code == 404 and i >= 2:
                return r          # persistent 404 = genuinely absent
            last = r
        except requests.RequestException as exc:
            last = exc
        time.sleep(1.5 * (i + 1))
    if isinstance(last, Exception):
        raise last
    return last


# ---------- text helpers ----------

def strip_stress(s: str) -> str:
    """Remove stress marks; keep real Lithuanian diacritics (ą č ę ė į š ų ū ž)."""
    out, prev = [], ""
    for ch in unicodedata.normalize("NFD", s):
        cp = ord(ch)
        if cp in (0x0300, 0x0301, 0x0303):
            continue
        if cp == 0x0307 and prev in ("i", "I"):
            continue
        if unicodedata.combining(ch) == 0:
            prev = ch
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def first_variant(cell_text: str) -> str:
    parts = [p for p in cell_text.split() if p not in ("", "-", "—")]
    return parts[0] if parts else ""


def tokenize(text: str):
    return re.findall(r"\w+", text, flags=re.UNICODE)


def bold_word(sentence: str, forms: set) -> tuple[str, bool]:
    """Bold every token that matches an inflected form. -> (html, found)"""
    found = False
    def repl(m):
        nonlocal found
        if m.group(0).lower() in forms:
            found = True
            return f"<b>{m.group(0)}</b>"
        return m.group(0)
    return re.sub(r"\w+", repl, sentence, flags=re.UNICODE), found


# English inflections a gloss may legitimately appear under. Deliberately
# short: a miss just leaves the sentence unbolded, whereas a bad rule bolds
# the wrong word. Prefix matching is exactly what NOT to do here — "pharm"
# would bold "pharmacy" in "At the chemist's I talked with the pharmacist".
_EN_SUFFIXES = ("", "s", "es", "ed", "d", "ing", "'s")

# The irregular forms the suffix rules cannot reach. A closed, checkable list —
# every entry is a standard English irregular, so this adds coverage without
# adding guesswork.
_EN_IRREGULAR = {
    "be": "am is are was were been being", "do": "does did done",
    "have": "has had having", "go": "goes went gone",
    "become": "became become", "begin": "began begun", "break": "broke broken",
    "bring": "brought", "build": "built", "buy": "bought", "catch": "caught",
    "choose": "chose chosen", "come": "came", "cut": "cut", "draw": "drew drawn",
    "drink": "drank drunk", "drive": "drove driven", "eat": "ate eaten",
    "fall": "fell fallen", "feel": "felt", "find": "found", "fly": "flew flown",
    "forget": "forgot forgotten", "forgive": "forgave forgiven",
    "freeze": "froze frozen", "get": "got gotten", "give": "gave given",
    "grow": "grew grown", "hang": "hung", "hear": "heard", "hide": "hid hidden",
    "hold": "held", "hurt": "hurt", "keep": "kept", "know": "knew known",
    "lead": "led", "learn": "learnt learned", "leave": "left", "lend": "lent",
    "lie": "lay lain", "light": "lit", "lose": "lost", "make": "made",
    "mean": "meant", "meet": "met", "pay": "paid", "put": "put", "read": "read",
    "ride": "rode ridden", "ring": "rang rung", "rise": "rose risen",
    "run": "ran", "say": "said", "see": "saw seen", "sell": "sold",
    "send": "sent", "shine": "shone", "show": "showed shown", "shoot": "shot", "shut": "shut",
    "sing": "sang sung", "sit": "sat", "sleep": "slept", "speak": "spoke spoken",
    "spend": "spent", "stand": "stood", "steal": "stole stolen",
    "swim": "swam swum", "take": "took taken", "teach": "taught", "tell": "told",
    "think": "thought", "throw": "threw thrown", "understand": "understood",
    "wake": "woke woken", "wear": "wore worn", "win": "won", "write": "wrote written",
    # irregular plurals
    "child": "children", "foot": "feet", "leaf": "leaves", "life": "lives",
    "man": "men", "mouse": "mice", "person": "people", "tooth": "teeth",
    "wife": "wives", "woman": "women", "knife": "knives", "shelf": "shelves",
    "loaf": "loaves", "goose": "geese", "half": "halves",
    "wolf": "wolves", "sheep": "sheep", "fish": "fish",
}


def _en_variants(phrase):
    """The phrase itself plus the plausible inflections of its last word."""
    words = phrase.split()
    if not words:
        return []
    head, rest = words[-1], words[:-1]
    stems = [head]
    if head.endswith("y") and len(head) > 2 and head[-2] not in "aeiou":
        stems.append(head[:-1] + "ie")          # country -> countries
    if head.endswith("e"):
        stems.append(head[:-1])                 # ride -> riding
    out = []
    for stem in stems:
        for suf in _EN_SUFFIXES:
            out.append(" ".join(rest + [stem + suf]))
    for irr in _EN_IRREGULAR.get(head.lower(), "").split():
        out.append(" ".join(rest + [irr]))
    if rest:
        # the inflection may sit on the first word instead: "wage war" ->
        # "waged war", "piece of jewellery" -> "pieces of jewellery"
        first, tail = rest[0], rest[1:] + [head]
        for suf in _EN_SUFFIXES[1:]:
            out.append(" ".join([first + suf] + tail))
        for irr in _EN_IRREGULAR.get(first.lower(), "").split():
            out.append(" ".join([irr] + tail))
    return out


def en_candidates(en_word):
    """Every form of the gloss worth looking for, longest first.

    A gloss may be a list ("Mr; sir", "flight, trip"), carry a disambiguating
    parenthesis ("to wear (footwear)"), or be a phrase ("wine glass"). The
    parenthesis is guidance for the learner, not part of the translation.
    """
    en_word = re.sub(r"\([^)]*\)", " ", en_word or "")
    parts = [p.strip() for p in re.split(r"[;,/]", en_word) if p.strip()]
    cands = []
    for part in parts:
        part = re.sub(r"^(to|a|an|the)\s+", "", part, flags=re.I).strip()
        if not part:
            continue
        cands.append(part)
        if " " in part:                 # "wine glass" also appears as "glass"
            cands.append(part.split()[-1])
    seen, out = set(), []
    for c in sorted(cands, key=len, reverse=True):
        for v in _en_variants(c):
            if v.lower() not in seen:
                seen.add(v.lower())
                out.append(v)
    return out


def bold_en(sentence: str, en_word: str) -> tuple[str, bool]:
    """Bold the headword's English equivalent in an English sentence.

    Tries the whole gloss phrase before its head word and the longest
    candidate before shorter ones, so "wine glass" wins over "glass". Matching
    is whole-word only; the first candidate that matches wins, and every
    occurrence of that one is bolded.
    """
    if not sentence or not en_word:
        return sentence, False
    for cand in en_candidates(en_word):
        pattern = re.compile(
            r"(?<!\w)" + r"\s+".join(re.escape(w) for w in cand.split())
            + r"(?!\w)", re.I | re.UNICODE)
        if pattern.search(sentence):
            return pattern.sub(lambda m: f"<b>{m.group(0)}</b>", sentence), True
    return sentence, False


# ---------- pronoun paradigm table ----------

CASE_ABBR = ["V.", "K.", "N.", "G.", "Įn.", "Vt."]

# A pronoun and the counterpart a learner keeps confusing it with. Each column
# is (label, lemma, tags): `label` heads the column and is looked up in
# manual_forms.tsv first; when there is no manual row the forms come from the
# Wiktionary table of `lemma`, filtered to every tag in `tags`.
#
# For the 1st and 2nd person the confusable pair is singular vs plural. For the
# 3rd-person plurals it is masculine vs feminine: `jie/tie/šie` are used for
# men or for mixed groups, `jos/tos/šios` only for women, and a deck that
# teaches one and not the other teaches a mistake. jis→jie stays on the `jis`
# card, so nothing is lost by re-pointing `jie` here.
_M, _F, _SG, _PL = "masculine", "feminine", "singular", "plural"
PRONOUN_PAIR = {
    "aš":  (("aš", "aš", {_SG}), ("mes", "mes", {_PL})),
    "mes": (("aš", "aš", {_SG}), ("mes", "mes", {_PL})),
    "tu":  (("tu", "tu", {_SG}), ("jūs", "jūs", {_PL})),
    "jūs": (("tu", "tu", {_SG}), ("jūs", "jūs", {_PL})),
    "jis": (("jis", "jis", {_SG}), ("jie", "jie", {_PL})),
    "ji":  (("ji", "ji", {_SG}), ("jos", "ji", {_PL})),
    "jie": (("jie", "jie", {_PL}), ("jos", "ji", {_PL})),
    "tie": (("tie", "tie", {_PL}), ("tos", "tas", {_F, _PL})),
    "šie": (("šie", "šie", {_PL}), ("šios", "šis", {_F, _PL})),
    # the singular demonstratives and the relative pronoun inflect for gender
    # in the singular too, and English gives no clue that they do
    "tas": (("tas", "tas", {_M, _SG}), ("ta", "tas", {_F, _SG})),
    "šis": (("šis", "šis", {_M, _SG}), ("ši", "šis", {_F, _SG})),
    "kuris": (("kuris", "kuris", {_M, _SG}), ("kuri", "kuris", {_F, _SG})),
}
CASE_TAG = {"V.": "nominative", "K.": "genitive", "N.": "dative",
            "G.": "accusative", "Įn.": "instrumental", "Vt.": "locative"}


def kaikki_case_forms(word, tags):
    """Accented case forms from kaikki, for a pronoun with no manual row.

    `tags` are the Wiktionary tags a form must carry — {"plural"} for a
    genderless paradigm, {"feminine", "plural"} to pick the feminine column
    out of a table that holds both.
    """
    want = set(tags)
    out = {}
    for entry in kaikki_entries(word):
        for f in entry.get("forms", []) or []:
            ftags = set(f.get("tags") or [])
            if "dual" in ftags or "alternative" in ftags:
                continue
            if not want <= ftags:
                continue
            for ab, case in CASE_TAG.items():
                if case in ftags:
                    out.setdefault(ab, f["form"])
    return out


def _column_forms(spec, manual):
    """The six case forms of one table column."""
    label, lemma, tags = spec
    # The manual row holds one paradigm keyed by the headword, so it may only
    # be used when the column IS that headword. `jos` is looked up under the
    # lemma `ji`, whose manual row is the SINGULAR — taking it would print the
    # singular twice, which is exactly what the first version of this did.
    if label == lemma and lemma in manual:
        got = manual[lemma]["forms_line"].split(", ")
        if len(got) == len(CASE_ABBR):
            return got
    got = kaikki_case_forms(lemma, tags)
    return [got.get(c, "") for c in CASE_ABBR]


def pronoun_speech(word, manual):
    """Both columns of the pronoun table as TTS text, singular then plural.

    The table replaces the forms line on pronoun cards, so the forms clip has
    to say what the table shows — all twelve forms, not the six of one column.
    """
    if word not in PRONOUN_PAIR:
        return ""
    out = []
    for spec in PRONOUN_PAIR[word]:
        out += _column_forms(spec, manual)
    out = [strip_stress(f) for f in out if f]
    return ", ".join(out)


def forms_clip_text(word, forms_line, manual):
    """What the forms clip says — the single source of truth.

    Everything that generates or checks that clip must call this. A pronoun
    card shows a two-column table instead of the forms line, so its clip
    speaks the whole table; every other word speaks its forms line. This used
    to be decided in two places, and resume_audio.py kept quietly rebuilding
    pronoun clips with only the singular half.
    """
    return pronoun_speech(word, manual) or forms_speech(forms_line)


def pronoun_table(word, manual):
    """Two-column case table for a personal pronoun, or "" for anything else.

    The two columns are whatever PRONOUN_PAIR says a learner confuses with
    this word: singular vs plural for the 1st and 2nd person, masculine vs
    feminine for the 3rd-person plurals. `jos`, `tos` and `šios` have no cards
    of their own and are taken from kaikki, the same source the rest of the
    deck's paradigms come from.
    """
    if word not in PRONOUN_PAIR:
        return ""
    left_spec, right_spec = PRONOUN_PAIR[word]
    left = _column_forms(left_spec, manual)
    right = _column_forms(right_spec, manual)
    if not any(left) or not any(right):
        return ""
    rows = "".join(
        f"<tr><th>{c}</th><td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>"
        for c, a, b in zip(CASE_ABBR, left, right))
    return (f'<table class="par"><tr><th></th>'
            f'<th class="hd">{html.escape(left_spec[0])}</th>'
            f'<th class="hd">{html.escape(right_spec[0])}</th></tr>{rows}</table>')


# ---------- lookups (verifiable sources) ----------

def kaikki_entries(word):
    cdir = paths.KAIKKI_CACHE
    cdir.mkdir(exist_ok=True)
    cfile = cdir / f"{word}.jsonl"
    if cfile.exists():
        return [json.loads(line) for line in
                cfile.read_text(encoding="utf-8").splitlines() if line.strip()]
    r = _get(KAIKKI.format(a=word[0], ab=word[:2], w=word))
    if r.status_code == 404:
        # Negative cache. Without this, every word that simply has no
        # kaikki.org entry (all the manual_forms words) costs a ~2s network
        # round trip on EVERY verify_defs run, which is most of the gate's
        # runtime. A transient error is deliberately not cached.
        cfile.write_text("", encoding="utf-8")
        return []
    if r.status_code != 200:
        return []
    out = []
    for line in r.text.splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if not out:
        # A 200 with nothing parseable is an error page (proxy, captive
        # portal, outage), not an answer. Caching it would record the word
        # as absent for good.
        return []
    cfile.write_text("\n".join(json.dumps(e, ensure_ascii=False)
                                for e in out), encoding="utf-8")
    return out


def wikt_lt_tables(word):
    cdir = paths.WIKT_CACHE
    cdir.mkdir(exist_ok=True)
    cfile = cdir / f"{word}.html"
    if cfile.exists():
        soup = BeautifulSoup(cfile.read_text(encoding="utf-8"), "html.parser")
        return soup.find_all("table", class_="inflection-table")
    r = _get(WIKT_HTML.format(requests.utils.quote(word, safe="")))
    if r.status_code == 404:
        # Negative cache. Words with no Wiktionary page — every manual_forms
        # word — were otherwise refetched WITH RETRIES on every single build,
        # which was ~95% of build time and made offline builds impossible.
        cfile.write_text("", encoding="utf-8")
        return []
    if r.status_code != 200:
        return []          # transient: do not cache
    soup = BeautifulSoup(r.text, "html.parser")
    if not soup.find("h2"):
        return []          # not a Wiktionary entry page: do not cache
    h2 = soup.find(lambda t: t.name == "h2"
                   and t.get("id", "").startswith("Lithuanian"))
    if h2 is None:
        # The page exists but has no Lithuanian entry. Falling back to the
        # whole page would take another language's tables as Lithuanian.
        tables = []
    elif h2.parent and h2.parent.name == "section":
        tables = h2.parent.find_all("table", class_="inflection-table")
    else:
        # unsectioned HTML: everything between this h2 and the next one
        tables = []
        for el in h2.find_all_next():
            if el.name == "h2":
                break
            if el.name == "table" and "inflection-table" in (el.get("class") or []):
                tables.append(el)
    # cache even when empty: "page exists but has no Lithuanian inflection
    # table" is a permanent answer too
    cfile.write_text("\n".join(str(t) for t in tables), encoding="utf-8")
    return tables


def classify_table(table):
    ths = " ".join(th.get_text(" ", strip=True).lower()
                   for th in table.find_all("th"))
    tds = " ".join(td.get_text(" ", strip=True).lower()
                   for td in table.find_all("td"))
    if "aš" in ths or "indicative" in ths:
        return "verb"
    if "masculine" in ths and "feminine" in ths:
        return "adj"
    if "nominative" in ths or "nominative" in tds:
        return "noun"
    return None


def all_word_forms(entries, pos) -> set:
    """Every inflected form (stress-stripped, lowercase) for bold-matching."""
    forms = set()
    for e in entries:
        if e.get("pos") != pos:
            continue
        for f in e.get("forms", []):
            v = f.get("form", "")
            if v and "-" not in v and " " not in v and v.isascii() is False or v.isalpha():
                forms.add(strip_stress(v).lower())
    return {f for f in forms if f.isalpha()}


# kaikki sometimes glues grammatical annotation onto the canonical form —
# "sakinỹs m stress pattern 3ᵇ", "brangùs m stress pattern 4 or 3". That text
# was reaching the card AND being read aloud by the synthesiser.
CANON_ANNOT = re.compile(r"\s+(?:[mfn]\b|\S*\s*stress pattern).*$", re.I)


def canonical(entries, pos, fallback):
    for e in entries:
        if e.get("pos") == pos:
            for f in e.get("forms", []):
                if "canonical" in f.get("tags", []):
                    return CANON_ANNOT.sub("", f["form"]).strip() or fallback
    return fallback


def feminine(entries):
    for e in entries:
        if e.get("pos") == "adj":
            for f in e.get("forms", []):
                if f.get("tags") == ["feminine"]:
                    return f["form"]
    return ""


def noun_compact(table):
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells or not cells[0].get_text(
                " ", strip=True).lower().startswith("nominative"):
            continue
        if len(cells) >= 3:
            sg = first_variant(cells[-2].get_text(" ", strip=True))
            pl = first_variant(cells[-1].get_text(" ", strip=True))
            if sg and pl:
                return f"{sg} / {pl}"
        elif len(cells) == 2:
            # One column only. That means the noun has just one number — but
            # WHICH one has to come from the header, not be assumed. Mass nouns
            # like sidabras are singular-only and were being labelled "(tik
            # dgs.)", i.e. exactly backwards.
            only = first_variant(cells[-1].get_text(" ", strip=True))
            if only:
                hdr = ""
                first = table.find("tr")
                if first:
                    hdr = " ".join(c.get_text(" ", strip=True).lower()
                                   for c in first.find_all(["th", "td"]))
                num = "dgs." if "plural" in hdr else "vns."
                return f"{only} (tik {num})"
    return ""


def forms_speech(forms_line):
    """Forms line as TTS text: drop notes in parentheses."""
    return re.sub(r"\s*\(.*?\)", "", strip_stress(forms_line)).replace("/", ",")


def verb_compact(table, inf):
    pres3 = past3 = ""
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        tds = [c for c in cells if c.name == "td"]
        if len(tds) != 6:
            continue
        label = " ".join(c.get_text(" ", strip=True).lower()
                         for c in cells if c.name == "th")
        if "present" in label and not pres3:
            pres3 = first_variant(tds[2].get_text(" ", strip=True))
        elif "past" in label and "frequentative" not in label and not past3:
            past3 = first_variant(tds[2].get_text(" ", strip=True))
    return f"{inf}, {pres3}, {past3}" if pres3 and past3 else ""


def wikt_gloss(entries, pos, n=1):
    for e in entries:
        if e.get("pos") == pos:
            gl = [s["glosses"][0] for s in e.get("senses", [])
                  if s.get("glosses")]
            return "; ".join(gl[:n])
    return ""


# ---------- audio ----------

LIEPA_URL = "https://sinteze.intelektika.lt/synthesis.service/prod/synthesize"
LIEPA_SPEED = 1.2      # >1 = slower; user-chosen tempo
AUDIO_TAG = "v2"       # bump when audio settings change -> new media filenames
LIEPA_TIMEOUT = 60     # seconds to wait for one synthesis request

# Optional callable(str) for per-request tracing. resume_audio.py sets this so
# every HTTP attempt — status, elapsed time, bytes, timeouts — reaches the log
# instead of disappearing inside the retry loop.
AUDIO_LOG = None


def _alog(msg):
    if AUDIO_LOG:
        AUDIO_LOG(msg)


class BadAudio(ValueError):
    """The synthesiser answered 200, but not with a usable MP3."""


def _is_mp3(data):
    # an ID3 tag, or an MPEG audio frame sync (11 set bits)
    return data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF
                                  and data[1] & 0xE0 == 0xE0)


def _liepa_audio(r):
    """The MP3 bytes in a LIEPA response, or BadAudio."""
    import base64
    import binascii
    try:
        data = base64.b64decode(r.json()["audioAsString"])
    except (ValueError, KeyError, TypeError, binascii.Error) as exc:
        raise BadAudio(f"unreadable response: {r.text[:60]!r}") from exc
    if len(data) < 256 or not _is_mp3(data):
        raise BadAudio(f"not an MP3 ({len(data)} bytes)")
    return data


def _write_atomic(path, data):
    """Write via a temp file, so an interrupted run never leaves a partial
    clip that later passes for a finished one."""
    path = Path(path)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


async def _tts_edge(text, path, voice):
    import edge_tts
    await edge_tts.Communicate(text, voice).save(str(path))


def make_audio(text, path, voice, engine="liepa", attempts=8, quota_wait=120):
    """Synthesise `text` to `path`, unless it is already there.

    attempts / quota_wait let the caller own the retry policy. resume_audio.py
    passes attempts=1, quota_wait=0 so that IT does the waiting and logging,
    one clip at a time.
    """
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        return
    if engine == "liepa":
        import time
        last = RuntimeError("LIEPA: no attempts made")
        for i in range(attempts):
            t0 = time.monotonic()
            try:
                r = requests.post(LIEPA_URL,
                                  json={"text": text, "voice": voice,
                                        "speed": LIEPA_SPEED},
                                  headers=HEADERS, timeout=LIEPA_TIMEOUT)
                dt = time.monotonic() - t0
                if r.status_code == 200:
                    data = _liepa_audio(r)
                    _write_atomic(p, data)
                    _alog(f"POST {len(text):3d} ch -> 200 in {dt:5.2f}s, "
                          f"{len(data)/1024:.1f} KB  {text!r}")
                    time.sleep(0.3)      # be polite to the public service
                    return
                body = r.text[:60].replace("\n", " ")
                _alog(f"POST {len(text):3d} ch -> {r.status_code} in {dt:5.2f}s"
                      f"  {body!r}")
                last = RuntimeError(f"LIEPA {r.status_code}: {r.text[:100]}")
                if r.status_code == 403 and "uota" in r.text:
                    # Public service throttle, not a permanent failure.
                    if quota_wait:
                        _alog(f"  quota hit, sleeping {quota_wait}s")
                        time.sleep(quota_wait)
                        continue
                    break
            except requests.Timeout as exc:
                _alog(f"POST {len(text):3d} ch -> TIMEOUT after "
                      f"{LIEPA_TIMEOUT}s")
                last = exc
            except BadAudio as exc:
                _alog(f"POST {len(text):3d} ch -> 200 but {exc}")
                last = exc
            except requests.RequestException as exc:
                _alog(f"POST {len(text):3d} ch -> {type(exc).__name__} in "
                      f"{time.monotonic()-t0:5.2f}s: {str(exc)[:70]}")
                last = exc
            if i + 1 < attempts:
                time.sleep(1 + i)
        raise last
    asyncio.run(_tts_edge(text, path, voice))


# ---------- Anki model: one note, two cards ----------

CSS = """
/* Theme: Švarus, set in Charter.
   Lithuanian is serif, English is sans and always italic, so the two are
   never mistaken for each other at a glance — including inside hints.
   Charter is on iOS and macOS and was drawn for low-resolution screens, so
   the stacked kirtis marks (i + dot + tilde) stay legible at 19px. The rest
   of the stack is what a device without it will reach for. */
.card { font-family: "Charter", "Bitstream Charter", "Iowan Old Style",
        Georgia, "Times New Roman", serif; font-size: 22px;
        text-align: center; color: #23252b; background: #fbfbfa;
        line-height: 1.45; }

.word    { font-size: 34px; font-weight: 700; letter-spacing: -.01em; }
.qual    { font-weight: 400; color: #8a8f98; }
.forms   { font-size: 19px; color: #5b6068; margin: 6px 0; }
.lt      { font-size: 21px; margin: 12px 0; }
.formsbig{ font-size: 27px; font-weight: 700; margin: 8px 0; }

/* Word card. The headword carries the front and reappears unchanged above
   the rule, so the question still reads the same after answering; the
   English answer below is the one thing set in italic bold. */
.forms-q { font-size: 23px; font-weight: 600; color: #3c414a; margin: 10px 0; }
/* the word answered on card 2 — the forms line above already spells it out,
   so it closes the card quietly rather than shouting the answer twice */
.word-a  { font-size: 24px; font-weight: 400; color: #8a8f98; margin: 12px 0; }
b { font-weight: 700; }
hr#answer { border: none; border-top: 1px solid #e2e2df; margin: 16px 0; }

/* Everything English, in the sans face */
.en      { font-size: 20px; color: #4a4f57; margin: 8px 0; font-style: italic;
           font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
           sans-serif; }
.small   { font-size: 19px; margin-top: 12px; font-style: italic;
           color: #6b7078; font-family: -apple-system, BlinkMacSystemFont,
           "Segoe UI", Roboto, sans-serif; }
.en-main { font-size: 27px; font-weight: 700; font-style: italic;
           color: #1a5f7a; margin: 14px 0;
           font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
           sans-serif; }
a.hint   { color: #1a5f7a; font-size: 19px; text-decoration: none;
           font-style: normal; font-family: -apple-system, BlinkMacSystemFont,
           "Segoe UI", Roboto, sans-serif; }

/* Pronoun paradigm, shown on the backs of the seven personal-pronoun cards */
.par    { margin: 14px auto; border-collapse: collapse; font-size: 19px; }
.par th { color: #9aa0a8; font-weight: 400; text-align: right; font-size: 17px;
          padding: 3px 12px 3px 0; }
.par td { text-align: left; padding: 3px 18px 3px 0; }
.par th.hd { color: #9aa0a8; text-align: left; font-size: 15px;
             letter-spacing: .06em; text-transform: uppercase;
             padding-top: 10px; }

/* Anki puts `nightMode` on the same element as `card`, so a descendant
   selector reaches the card's own children. Without this block the deck
   stays dark-on-light in Anki's dark mode. */
.nightMode.card, .nightMode .card { color: #e4e5e7; background: #26272b; }
.nightMode .qual,
.nightMode .word-a   { color: #85898f; }
.nightMode .forms    { color: #a8acb3; }
.nightMode .forms-q  { color: #c8ccd2; }
.nightMode .en       { color: #b8bcc2; }
.nightMode .small    { color: #9ea2a9; }
.nightMode .en-main,
.nightMode a.hint    { color: #6fb6d4; }
.nightMode hr#answer { border-top-color: #3a3c42; }
.nightMode .par th,
.nightMode .par th.hd { color: #8b9097; }
"""

MODEL = genanki.Model(
    1607392322,
    "LT žodis (v4: word + definition cards)",
    fields=[{"name": f} for f in
            # Field 2 carries the qualifier of a two-word headword
            # ("gatvės"), empty otherwise, and the card-1 templates branch on
            # it. It keeps its original name `Accented`, unused since v4:
            # renaming a field changes the notetype schema, and Anki then
            # refuses to update an existing collection — it forks a second
            # notetype called "…+" and leaves your cards untouched. A stale
            # name is a smaller price than an unimportable deck.
            ["Word", "Accented", "POS", "FormsLine", "EN_Word",
             "LT_Def", "Pavyzdys", "English", "Vertimas", "Vertimai",
             "WordAudio", "FormsAudio", "DefAudio", "ExAudio"]],
    templates=[
        {
            "name": "1 Word card",
            # Front: the headword and the example, both spoken.
            "qfmt": '<div class="word">{{Word}}</div>{{WordAudio}}'
                    '<div class="lt">{{Pavyzdys}} {{ExAudio}}</div>',
            # Back: the headword again above the rule, silent, as it was
            # asked. Below it the English answer leads, then the definition
            # and example speak, and the paradigm closes before the hint.
            "afmt": '<div class="word">{{Word}}</div><hr id="answer">'
                    '<div class="en-main">{{EN_Word}}</div>'
                    # a pronoun shows its table instead, which carries the
                    # same clip, so the one-line paradigm would only repeat it
                    '{{^POS}}<div class="forms-q">{{FormsLine}} '
                    '{{FormsAudio}}</div>{{/POS}}'
                    '<div class="lt">{{LT_Def}} {{DefAudio}}</div>'
                    '<div class="lt">{{Pavyzdys}} {{ExAudio}}</div>'
                    '{{POS}}'
                    '<div class="small">{{hint:Vertimai}}</div>',
        },
        {
            "name": "2 Definition card",
            "qfmt": '<div class="lt">{{LT_Def}}</div>{{DefAudio}}'
                    '<div class="small">{{hint:English}}</div>',
            # The reverse card carries everything: the word answered, its
            # whole paradigm, the translation, the example and — for the
            # pronouns — the case table.
            "afmt": '<div class="lt">{{LT_Def}}</div>'
                    '<div class="small">{{hint:English}}</div><hr id="answer">'
                    '<div class="en-main">{{EN_Word}}</div>'
                    '{{^POS}}<div class="formsbig">{{FormsLine}} {{FormsAudio}}</div>{{/POS}}'
                    '<div class="lt">{{Pavyzdys}} {{ExAudio}}</div>'
                    '{{POS}}'
                    '<div class="word-a">{{Word}}</div>'
                    '<div class="small">{{hint:Vertimas}}</div>',
        },
    ],
    css=CSS,
)


# ---------- assembly ----------

@functools.lru_cache(maxsize=8)
def load_manual_forms(path=paths.MANUAL_FORMS):
    mf = {}
    p = Path(path)
    if not p.exists():
        return mf
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        w, pos, forms_line, allf = (line.split("\t") + [""] * 4)[:4]
        mf[w.strip()] = dict(pos=pos.strip(), forms_line=forms_line.strip(),
                             forms={f.lower() for f in allf.split()})
    return mf


def load_word_set(path):
    """The words in a plain text file, lowercased: any number per line,
    `#` starts a comment. data/function_words.txt and data/proper_nouns.txt."""
    words, p = set(), Path(path)
    if not p.exists():
        return words
    for line in p.read_text(encoding="utf-8").splitlines():
        words.update(w.lower() for w in line.split("#", 1)[0].split())
    return words


def load_gloss_overrides(path=None):
    """Card key -> the accepted English gloss, from data/gloss_overrides.tsv
    (key, gloss, note). The GLOSS check takes these on trust; the note says
    why each one was allowed."""
    out, p = {}, Path(path or paths.GLOSS_OVERRIDES)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            key, _, rest = line.partition("\t")
            out[key.strip()] = rest.split("\t")[0].strip()
    return out


@functools.lru_cache(maxsize=1)
def theme_table():
    """[(full tag, what it covers)] from data/THEMES.md, in its order:
    ("egzaminas::02-pastatai-ir-namai", "home, rooms, furniture, ...")."""
    text = paths.THEMES_MD.read_text(encoding="utf-8")
    return re.findall(r"^\| `([a-z]+::\d\d-[a-z-]+)` \| (.+?) \|$", text, re.M)


def theme_tags():
    """{slug as written in column 8: full tag}, e.g.
    {"02-pastatai-ir-namai": "egzaminas::02-pastatai-ir-namai"}."""
    return {tag.split("::", 1)[1]: tag for tag, _ in theme_table()}


def resolve_theme(slug):
    """The column-8 slug for a full or partial name: "02-pastatai-ir-namai",
    "egzaminas::02-pastatai-ir-namai", "02" and "pastatai" all resolve to
    "02-pastatai-ir-namai". Raises LookupError listing the choices."""
    tags = theme_tags()
    hits = [leaf for leaf, tag in tags.items()
            if slug in (leaf, tag) or leaf.startswith(slug) or slug in leaf]
    if len(hits) != 1:
        raise LookupError(f"theme {slug!r} matches {len(hits)} of:\n  "
                          + "\n  ".join(tags))
    return hits[0]


@functools.lru_cache(maxsize=1)
def load_themes():
    """{headword: full theme tag} from column 8 of every batch row. A word
    whose slug is not in THEMES.md keeps the slug as written, so the gate
    can name it; a word with no theme is absent, and the note is tagged
    tema::be-temos."""
    tags, themes = theme_tags(), {}
    for f in paths.batch_files():
        for key, d in load_defs(str(f)).items():
            if d["theme"]:
                themes.setdefault(key.split("#")[0], tags.get(d["theme"], d["theme"]))
    return themes


def load_defs(path):
    """Load a batch TSV.

    Columns: key, lt_def, en_word, en_def, lt_example, en_example, pos,
             theme, [qualifier]

    `theme` is a slug from data/THEMES.md without its group prefix
    (`02-pastatai-ir-namai`); it becomes the note's tema:: tag.

    `key` is normally just the headword. A word with two teachable senses gets
    one row per sense, keyed `headword#tag` (e.g. `žibintas#auto`), with the
    optional 8th column giving a qualifier word that disambiguates it on the
    card: "automobilio žibintas", the qualifier shown in lighter type and the
    headword itself in bold. Inflections, audio and the leak/form checks all
    still key off the headword.
    """
    defs = {}
    if not path:
        return defs
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = (line.split("\t") + [""] * 9)[:9]
        key = p[0].strip().lower()
        defs[key] = dict(
            headword=key.split("#")[0], theme=p[7].strip(),
            qualifier=p[8].strip(),
            lt_def=p[1].strip(), en_word=p[2].strip(), en_def=p[3].strip(),
            lt_example=p[4].strip(), en_example=p[5].strip(),
            pos=p[6].strip())
    return defs


def display_word(headword, qualifier):
    """Card headword, with any qualifier in lighter type beside it."""
    if not qualifier:
        return html.escape(headword)
    return (f'<span class="qual">{html.escape(qualifier)}</span> '
            f'{html.escape(headword)}')


def process_word(key, voice, media_dir, defs, notes, media, errors,
                 engine="liepa", extra_tags=None, tts=None):
    """Build the note for one card and append it to `notes`.

    `key` may be `headword#sense`: everything linguistic keys off the
    headword, the card identity and display key off the full key. The four
    clips are requested through `tts(text, path, voice, engine)`, which
    defaults to make_audio; the build passes a no-op because every clip is
    already recorded, and the audio planner passes a recorder that only
    notes what each clip would say.
    """
    tts = tts or make_audio
    word = key.split("#")[0]
    d = defs.get(key)
    if not d:
        errors.append(f"{key}: no defs entry — skipped.")
        return
    qualifier = d.get("qualifier", "")
    manual_all = load_manual_forms()
    manual = manual_all.get(word)
    pron_table = pronoun_table(word, manual_all)   # "" unless a pronoun
    entries = kaikki_entries(word)
    # a manual-forms word takes none of its data from the Wiktionary table,
    # so skip the lookup entirely
    tables = [] if manual else wikt_lt_tables(word)
    poses = {e.get("pos") for e in entries} & POSES

    def emit(kind, forms_line, match_forms, spoken_head, en_word):
        """Request the four clips and append the note."""
        example_html, found = bold_word(html.escape(d["lt_example"]),
                                        match_forms)
        if not found:
            errors.append(f"{word}: WARNING — no inflected form of the word "
                          f"found in example '{d['lt_example']}'; not bolded. "
                          f"Check the sentence.")
        leak = [t for t in tokenize(d["lt_def"].lower()) if t in match_forms]
        if leak:
            errors.append(f"{word}: WARNING — definition contains the "
                          f"headword form(s) {leak}; definitions must be "
                          f"word-free.")
        h = hashlib.md5(f"{key}:{kind}:{AUDIO_TAG}".encode()).hexdigest()[:8]
        clip = {k: media_dir / f"lt_{h}_{k}.mp3" for k in ("w", "f", "d", "e")}
        tts(f"{qualifier} {spoken_head}".strip(), clip["w"], voice, engine)
        tts(forms_clip_text(word, forms_line, manual_all), clip["f"], voice,
            engine)
        tts(d["lt_def"], clip["d"], voice, engine)
        tts(d["lt_example"], clip["e"], voice, engine)
        media.extend(str(p) for p in clip.values())
        # bold the English equivalent, mirroring the bolded Lithuanian
        en_def_html, _ = bold_en(html.escape(d["en_def"]), en_word)
        en_ex_html, _ = bold_en(html.escape(d["en_example"]), en_word)
        vertimai = " · ".join(x for x in (en_def_html, en_ex_html) if x)
        sound = {k: f"[sound:{p.name}]" for k, p in clip.items()}
        notes.append(genanki.Note(
            model=MODEL, guid=genanki.guid_for(key, kind),
            tags=[f"pos::{kind}",
                  f"tema::{load_themes().get(word, 'be-temos')}"]
                 + (extra_tags or []),
            fields=[
                display_word(word, qualifier),
                # Field 2 is the qualifier (see MODEL for why it is still
                # called Accented); field 3 was the part of speech, which no
                # template read, and now carries the pronoun table — adding
                # a field would change the notetype schema, and Anki then
                # refuses to update an existing collection.
                qualifier,
                (pron_table + sound["f"]) if pron_table else "",
                html.escape(forms_line), html.escape(en_word),
                html.escape(d["lt_def"]), example_html,
                en_def_html, en_ex_html, vertimai,
                sound["w"], sound["f"], sound["d"], sound["e"]]))

    if manual:
        emit(manual["pos"], manual["forms_line"], manual["forms"], word,
             d["en_word"])
        errors.append(f"{word}: NOTE — built from manual forms "
                      f"(absent from Wiktionary, hunspell-verified).")
        return
    if not entries or not tables or not poses:
        errors.append(f"{word}: not found as a Lithuanian noun/verb/adjective "
                      f"on Wiktionary — skipped.")
        return
    if d.get("pos"):
        poses &= {d["pos"]}
    for table in tables:
        kind = classify_table(table)
        if kind not in poses:
            continue
        canon = canonical(entries, kind, word)
        if kind == "noun":
            forms_line = noun_compact(table)
        elif kind == "verb":
            forms_line = verb_compact(table, canon)
        else:
            fem = feminine(entries)
            forms_line = f"{canon} / {fem}" if fem else canon
        if not forms_line:
            errors.append(f"{word}: could not parse {kind} forms — skipped.")
            continue
        emit(kind, forms_line, all_word_forms(entries, kind),
             strip_stress(canon), d["en_word"] or wikt_gloss(entries, kind))
        poses.discard(kind)
