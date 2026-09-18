#!/usr/bin/env python3
"""
ltcard.py (v4) — Lithuanian flashcards for AnkiMobile: one note -> two cards.

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

Sources: en.wiktionary.org tables + kaikki.org (verifiable). Definitions,
examples and translations are supplied via --defs FILE (tab-separated):
  word <TAB> lt_def <TAB> en_word <TAB> en_def <TAB> lt_example <TAB> en_example
The script WARNS if a definition contains any form of the headword
(definitions must be word-free) or if no form of the word is found in the
example. Words not found on Wiktionary are skipped, never invented.

Usage:
  python3 ltcard.py namas kalbėti gražus --defs defs.tsv -o deck.apkg
  Options: --deck NAME  --voice lt-LT-OnaNeural|lt-LT-LeonasNeural
"""

import argparse
import functools
import asyncio
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import genanki

WIKT_HTML = "https://en.wiktionary.org/api/rest_v1/page/html/{}"
KAIKKI = "https://kaikki.org/dictionary/Lithuanian/meaning/{a}/{ab}/{w}.jsonl"
HEADERS = {"User-Agent": "ltcard/4.0 (personal flashcard tool)"}
POSES = {"noun", "verb", "adj"}
FUNCTION_WORDS = {
    "yra", "būti", "buvo", "bus", "esu", "esi", "kad", "kai", "kur", "kas",
    "kuris", "kuri", "kurie", "kurios", "kuriame", "kurioje", "kuriuos",
    "arba", "bet", "labai", "apie", "prie", "ant", "per", "nuo", "iki",
    "su", "be", "į", "iš", "po", "už", "tarp", "prieš", "dėl", "pagal",
    "tai", "tas", "ta", "šis", "ši", "jis", "ji", "jie", "jos", "mes",
    "savo", "kitas", "kita", "visi", "visos", "daug", "mažai", "dar",
    "jau", "tik", "taip", "kaip", "pro", "aplink", "viduryje", "vidury", "keli", "kelios", "kažkas", "kažką", "nors", "gali",
    # Pusiaukelė ch.4 (abstrakčiosios sąvokos) adverbs & connectors
    "šiandien", "rytoj", "vakar", "užvakar", "poryt", "dabar", "tada",
    "dažnai", "retai", "kartais", "visada", "niekada", "kasdien",
    "anksti", "vėlai", "greitai", "lėtai", "gerai", "blogai", "kartu",
    "čia", "ten", "todėl", "nes", "kadangi", "vieną", "vienas", "kiek",
    "tiek", "šiek", "truputį", "gana", "kokia", "koks", "kurią", "kurio",
    # added after the A2 gate flagged them repeatedly in otherwise good
    # definitions — all ordinary grammar words the word list simply lacked
    "atgal", "kol", "nieko", "nėra", "pas", "savęs", "save", "viskas", "visą", "visa", "visos", "visų", "kitiems", "kitoms", "kitais", "kitomis", "kituose", "virš", "žemiau", "aukščiau",
}


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
    cdir = Path("kaikki_cache"); cdir.mkdir(exist_ok=True)
    cfile = cdir / f"{word}.jsonl"
    if cfile.exists():
        return [json.loads(l) for l in
                cfile.read_text(encoding="utf-8").splitlines() if l.strip()]
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
    cfile.write_text("\n".join(json.dumps(e, ensure_ascii=False)
                                for e in out), encoding="utf-8")
    return out


def wikt_lt_tables(word):
    cdir = Path("wikt_cache"); cdir.mkdir(exist_ok=True)
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
    scope = soup
    h2 = soup.find(lambda t: t.name == "h2"
                   and t.get("id", "").startswith("Lithuanian"))
    if h2 and h2.parent and h2.parent.name == "section":
        scope = h2.parent
    tables = scope.find_all("table", class_="inflection-table")
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


async def _tts_edge(text, path, voice):
    import edge_tts
    await edge_tts.Communicate(text, voice).save(str(path))


def make_audio(text, path, voice, engine="liepa", attempts=8, quota_wait=120):
    """Synthesise `text` to `path`, unless it is already there.

    attempts / quota_wait let the caller own the retry policy. resume_audio.py
    passes attempts=1, quota_wait=0 so that IT does the waiting and logging,
    one clip at a time; the defaults keep batch.py's old behaviour.
    """
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        return
    if engine == "liepa":
        import base64, time
        last = None
        for i in range(attempts):
            t0 = time.monotonic()
            try:
                r = requests.post(LIEPA_URL,
                                  json={"text": text, "voice": voice,
                                        "speed": LIEPA_SPEED},
                                  headers=HEADERS, timeout=LIEPA_TIMEOUT)
                dt = time.monotonic() - t0
                if r.status_code == 200:
                    data = base64.b64decode(r.json()["audioAsString"])
                    Path(path).write_bytes(data)
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
def load_manual_forms(path="manual_forms.tsv"):
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


# The word list sits next to this script. It used to be referenced by an
# absolute path that existed only on the machine the deck was first built on;
# everywhere else load_themes() silently returned {} and every note was tagged
# tema::be-temos.
THEME_FILE = Path(__file__).resolve().parent / "a2_zodziai_v2.txt"


@functools.lru_cache(maxsize=8)
def load_themes(path=None):
    themes, cur = {}, "be-temos"
    p = Path(path) if path else THEME_FILE
    if not p.exists():
        return themes
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#"):
            cur = line.lstrip("# ").split()[0]
        elif line:
            themes[line.split("\t")[0]] = cur
    return themes


def load_defs(path):
    """Load a defs TSV.

    Columns: key, lt_def, en_word, en_def, lt_example, en_example, pos,
             [qualifier]

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
        p = (line.split("\t") + [""] * 8)[:8]
        key = p[0].strip().lower()
        defs[key] = dict(
            headword=key.split("#")[0], qualifier=p[7].strip(),
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
                 engine="liepa", known=None, extra_tags=None):
    # `key` may be `headword#sense`; everything linguistic keys off headword,
    # while the card identity and display key off the full key.
    word = key.split("#")[0]
    _d = defs.get(key) or {}
    qualifier = _d.get("qualifier", "")
    shown = display_word(word, qualifier)
    spoken = f"{qualifier} {word}".strip()
    manual_all = load_manual_forms()
    manual = manual_all.get(word)
    pron_table = pronoun_table(word, manual_all)   # "" unless a pronoun
    entries = kaikki_entries(word)
    # a manual-forms word takes none of its data from the Wiktionary table,
    # so skip the lookup entirely
    tables = [] if manual else wikt_lt_tables(word)
    poses = {e.get("pos") for e in entries} & POSES
    if manual:
        d = defs.get(key)
        if not d:
            errors.append(f"{word}: no defs entry — skipped."); return
        kind = manual["pos"]
        forms_line = manual["forms_line"]
        match_forms = manual["forms"]
        example_html, found = bold_word(html.escape(d["lt_example"]),
                                        match_forms)
        if not found:
            errors.append(f"{word}: WARNING — headword form not found "
                          f"in example."); 
        h = hashlib.md5(f"{key}:{kind}:{AUDIO_TAG}".encode()).hexdigest()[:8]
        paths = {k: media_dir / f"lt_{h}_{k}.mp3" for k in ("w","f","d","e")}
        make_audio(spoken, paths["w"], voice, engine)
        make_audio(forms_clip_text(word, forms_line, manual_all),
                   paths["f"], voice, engine)
        make_audio(d["lt_def"], paths["d"], voice, engine)
        make_audio(d["lt_example"], paths["e"], voice, engine)
        media += [str(p) for p in paths.values()]
        # bold the English equivalent, mirroring the bolded Lithuanian
        en_def_html, _ = bold_en(html.escape(d["en_def"]), d["en_word"])
        en_ex_html, _ = bold_en(html.escape(d["en_example"]), d["en_word"])
        vertimai = " · ".join(x for x in (en_def_html, en_ex_html) if x)
        notes.append(genanki.Note(model=MODEL,
            guid=genanki.guid_for(key, kind),
            tags=[f"pos::{kind}", f"tema::{load_themes().get(word, 'be-temos')}"]
                 + (extra_tags or []), fields=[
            # field 3 was the part of speech, which no template ever read;
            # it now carries the pronoun table (empty for every other word),
            # so no field had to be added — adding one changes the notetype
            # schema and Anki then refuses to update an existing collection.
            # The part of speech is still on the note as a pos:: tag.
            shown, qualifier,
            (pron_table + f'[sound:{paths["f"].name}]') if pron_table
            else "",
            html.escape(forms_line), html.escape(d["en_word"]),
            html.escape(d["lt_def"]), example_html,
            en_def_html, en_ex_html,
            vertimai,
            f'[sound:{paths["w"].name}]', f'[sound:{paths["f"].name}]',
            f'[sound:{paths["d"].name}]', f'[sound:{paths["e"].name}]']))
        errors.append(f"{word}: NOTE — built from manual forms "
                      f"(absent from Wiktionary, hunspell-verified).")
        return
    if not entries or not tables or not poses:
        errors.append(f"{word}: not found as a Lithuanian noun/verb/adjective "
                      f"on Wiktionary — skipped.")
        return
    d = defs.get(key)
    if not d:
        errors.append(f"{key}: no defs.tsv entry — skipped (definitions and "
                      f"examples are required in this format).")
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

        match_forms = all_word_forms(entries, kind)
        example_html, found = bold_word(html.escape(d["lt_example"]),
                                        match_forms)
        if not found:
            errors.append(f"{word}: WARNING — no inflected form of the word "
                          f"found in example '{d['lt_example']}'; not bolded. "
                          f"Check the sentence.")
        leak = [t for t in tokenize(d["lt_def"].lower())
                if t in match_forms]
        if leak:
            errors.append(f"{word}: WARNING — definition contains the "
                          f"headword form(s) {leak}; definitions must be "
                          f"word-free.")

        en_word = d["en_word"] or wikt_gloss(entries, kind)

        h = hashlib.md5(f"{key}:{kind}:{AUDIO_TAG}".encode()).hexdigest()[:8]
        paths = {k: media_dir / f"lt_{h}_{k}.mp3"
                 for k in ("w", "f", "d", "e")}
        make_audio(f"{qualifier} {strip_stress(canon)}".strip(),
                   paths["w"], voice, engine)
        make_audio(forms_clip_text(word, forms_line, manual_all),
                   paths["f"], voice, engine)
        make_audio(d["lt_def"], paths["d"], voice, engine)
        make_audio(d["lt_example"], paths["e"], voice, engine)
        media += [str(p) for p in paths.values()]

        en_def_html, _ = bold_en(html.escape(d["en_def"]), en_word)
        en_ex_html, _ = bold_en(html.escape(d["en_example"]), en_word)
        vertimai = " · ".join(x for x in (en_def_html, en_ex_html) if x)
        notes.append(genanki.Note(model=MODEL,
            guid=genanki.guid_for(key, kind),
            tags=[f"pos::{kind}", f"tema::{load_themes().get(word, 'be-temos')}"]
                 + (extra_tags or []), fields=[
            shown,
            qualifier,
            (pron_table + f'[sound:{paths["f"].name}]') if pron_table
            else "",
            html.escape(forms_line),
            html.escape(en_word), html.escape(d["lt_def"]), example_html,
            en_def_html, en_ex_html,
            vertimai,
            f'[sound:{paths["w"].name}]', f'[sound:{paths["f"].name}]',
            f'[sound:{paths["d"].name}]', f'[sound:{paths["e"].name}]']))
        poses.discard(kind)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="+")
    ap.add_argument("-o", "--out", default="lietuviu_kalba.apkg")
    ap.add_argument("--deck", default="Lietuvių kalba")
    ap.add_argument("--engine", choices=["liepa", "edge"], default="liepa",
                    help="liepa = Lithuanian LIEPA synthesizer (default); "
                         "edge = Microsoft neural voices")
    ap.add_argument("--voice", default=None,
                    help="liepa: astra, lina, laimis, vytautas; "
                         "edge: lt-LT-OnaNeural, lt-LT-LeonasNeural")
    ap.add_argument("--tag", action="append", default=[],
                    help="extra tag(s) for all notes, e.g. batch::batch1")
    ap.add_argument("--cache", default="forms_cache.json",
                    help="known-forms cache for A2 vocabulary checking")
    ap.add_argument("--defs", required=True,
                    help="TSV: word, lt_def, en_word, en_def, "
                         "lt_example, en_example")
    args = ap.parse_args()

    if args.voice is None:
        args.voice = "astra" if args.engine == "liepa" else "lt-LT-OnaNeural"
    known = None
    if Path(args.cache).exists():
        cache = json.load(open(args.cache, encoding="utf-8"))
        known = set()
        for w, forms in cache.items():
            known.add(w); known.update(forms)
        known |= FUNCTION_WORDS
    defs = load_defs(args.defs)
    media_dir = Path("media_tmp"); media_dir.mkdir(exist_ok=True)
    deck = genanki.Deck(
        int(hashlib.md5(args.deck.encode()).hexdigest()[:8], 16), args.deck)
    notes, media, errors = [], [], []

    for w in args.words:
        print(f"• {w} ...", flush=True)
        try:
            process_word(w.strip().lower(), args.voice, media_dir,
                         defs, notes, media, errors,
                         engine=args.engine, known=known,
                         extra_tags=args.tag)
        except Exception as exc:
            errors.append(f"{w}: error — {exc}")

    for n in notes:
        deck.add_note(n)
    if notes:
        pkg = genanki.Package(deck)
        pkg.media_files = media
        pkg.write_to_file(args.out)
        print(f"\nWrote {args.out}: {len(notes)} note(s), "
              f"{2 * len(notes)} cards.")
    else:
        print("\nNo cards generated.")
    for e in errors:
        print("!", e, file=sys.stderr)


if __name__ == "__main__":
    main()
