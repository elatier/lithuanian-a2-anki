#!/usr/bin/env python3
"""
verify_defs.py — automated QA for defs.tsv before any deck is built.

Checks per word (no human input needed):
  1. SPELL   every Lithuanian word in the definition and example exists
             (hunspell lt_LT; capitalized words treated as proper nouns)
  2. GLOSS   the one-word English translation is anchored in the word's
             Wiktionary glosses (independent, verifiable source)
  3. LEAK    definition contains no inflected form of the headword
  4. FORM    example contains at least one inflected form of the headword
  5. A2      definition+example vocabulary stays inside the approved
             A2 list (forms_cache.json) + function words
  6. LEN     definition is short enough for A2 (warn > 12 tokens)

Also writes review.txt: word | draft def | Wiktionary glosses | EN —
side by side, so human spot-checking a sample takes seconds per word.

Usage: python3 scripts/verify_defs.py data/batches/batchN.tsv
Exit code 1 if any hard check (SPELL/GLOSS/LEAK/FORM) fails.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import ltcard
import paths

CACHE = paths.FORMS_CACHE

# The gate used to check only what a human wrote (definition, example,
# translation) and never the GENERATED parts of a card — the headword as it is
# displayed and spoken, and the inflection line. kaikki.org glues annotation
# onto canonical forms ("sakinỹs m stress pattern 3ᵇ"), and a mis-parsed table
# yields a forms line full of header text. Both reach the card and the
# synthesiser, so they are checked here too.
JUNK_IN_HEAD = re.compile(
    r"stress pattern|declension|conjugation|inflection|singular|plural|"
    r"masculine|feminine|neuter|\bm\b|\bf\b|\bn\b|[0-9]|[ᵃᵇᶜᵈ]", re.I)
# legitimate annotations the project adds itself
HEAD_OK = re.compile(r"\(tik dgs\.\)|\(nekait\.\)")


def _flatten(text):
    """Drop combining marks before the junk test.

    A combining accent is not a word character, so `mán,` looks to `\\b` like a
    standalone `n` and tripped the `\\bn\\b` rule meant to catch Wiktionary's
    gender annotation. Removing the marks — `mán` -> `man` — restores real word
    boundaries while leaving the junk itself ("stress pattern", "m", digits)
    exactly as detectable.
    """
    import unicodedata
    return unicodedata.normalize(
        "NFC", "".join(c for c in unicodedata.normalize("NFD", text or "")
                       if not unicodedata.combining(c)))


def head_problems(key, d, manual):
    """Check the generated headword and forms line, as ltcard.py builds them."""
    word = d.get("headword") or key.split("#")[0]
    out = []
    if word in manual:
        forms_line, canon = manual[word]["forms_line"], word
    else:
        entries = ltcard.kaikki_entries(word)
        poses = {e.get("pos") for e in entries} & ltcard.POSES
        if d.get("pos"):
            poses &= {d["pos"]}
        forms_line = canon = None
        for table in ltcard.wikt_lt_tables(word):
            kind = ltcard.classify_table(table)
            if kind not in poses:
                continue
            canon = ltcard.canonical(entries, kind, word)
            if kind == "noun":
                forms_line = ltcard.noun_compact(table)
            elif kind == "verb":
                forms_line = ltcard.verb_compact(table, canon)
            else:
                fem = ltcard.feminine(entries)
                forms_line = f"{canon} / {fem}" if fem else canon
            break
        if forms_line is None:
            return ["HEAD: no usable inflection table or manual forms — "
                    "ltcard.py would skip this word"]
    for label, value in (("forms line", forms_line), ("headword", canon)):
        if value and JUNK_IN_HEAD.search(_flatten(HEAD_OK.sub("", value))):
            out.append(f"HEAD: {label} looks mis-parsed: {value!r}")
    if not forms_line:
        out.append("HEAD: empty forms line")
    return out

# Documented exceptions where the Wiktionary gloss is deficient
GLOSS_OVERRIDES = {"berniukas": "boy",        # Wikt: only 'lad; dim. of bernas'
                   "svetainė": "living room", # Wikt: 'parlor, guest room' — dated
                   "praustis": "to wash", "šukuotis": "to comb one's hair",
                   "rengtis": "to get dressed", "pabusti": "to wake up",
                   "darželis": "kindergarten", "pertrauka": "break",
                   "kabinetas": "office", "termometras": "thermometer",
                   # Senses that ARE on Wiktionary but sit outside the first
                   # four glosses that wikt_gloss() reads, so the gate cannot
                   # see them. Each verified in the kaikki entry:
                   "šokti": "dance",      # verb sense 5 'dance (move in rhythm to music)'
                   "kasa": "cash desk",   # 2nd noun etymology, 'cash register'
                   "narys": "member",     # noun sense 7 'member (person who belongs...)'
                   "pažymys": "grade",    # Wiktionary entry has a full declension
                                          # table but its sense is tagged no-gloss,
                                          # so NO translation can ever anchor
                   "auklė": "nanny",      # Wiktionary glosses 'nannie, nurse' —
                                          # 'nannie' is the archaic spelling of the
                                          # same sense; 'nurse' is slaugytoja
                   "kilimas": "carpet",   # 2nd noun etymology; wikt_gloss reads
                                          # only the first, which is 'rising up'
                   "valdymas": "governance",  # senses[*].glosses[1] is
                                          # 'governance, rule'; wikt_gloss reads
                                          # only glosses[0], a form-of pointer
                   "žvakutė": "candle",   # sense 2 is 'diminutive of žvakė',
                                          # and žvakė glosses exactly 'candle'
                   "režisierius": "film director",  # sole gloss is the ambiguous
                                          # 'director', already used by another
                                          # card; same sense, disambiguated
                   # Deficient glosses: the sense is right but Wiktionary's
                   # wording cannot be matched by a substring test. Each
                   # checked against the kaikki entry.
                   "danė": "Danish woman",     # Wikt: 'Dane (female from Denmark)'
                   "ispanė": "Spanish woman",  # Wikt: 'Spaniard (female from Spain)'
                   "vokietė": "German woman",  # Wikt: 'a woman from Germany'
                   "čekė": "Czech woman",      # Wikt: 'Czech (female from Czechia)'
                   "teisininkas": "lawyer",    # Wikt: 'jurist, legal scholar'
                   "manyti": "to think",       # Wikt: only 'to deem'
                   "aikštelė": "playground",   # Wikt: 'field, pad, site'
                   "žiedas#ring": "ring",      # Wikt noun lists only blossom/flower
                   "žibintas#auto": "headlight",   # Wikt: only 'lantern'
                   "besmegenis#snow": "snowman",   # Wikt has only the adjective
                   "lipti#climb": "to climb",  # 2nd verb etymology;
                                          # wikt_gloss reads only the first
                   # Senses genuinely ABSENT from Wiktionary, approved for
                   # the deck because the attested alternative made a poor card
                   "apžiūrėti": "to examine",  # Wikt: only 'to survey, to view'
                   "atskiras": "separate",     # Wikt: only 'isolated, dedicated'
                   "lipdyti": "to mould",      # Wikt: only 'to create by sticking'
                   # ---- review pass: translations deliberately narrowed ----
                   # Each of these replaces a gloss the review found wrong,
                   # ambiguous, or colliding with another card's answer. The
                   # Wiktionary gloss is quoted; the change is the point.
                   "ponas": "Mr; sir",         # 'sir' misused before a surname
                   "žmogus": "person; human",  # 'a good human' is not English
                   "mama": "mom",              # 'mother' collided with motina
                   "vaikinas": "young man; guy",   # 'guy' alone is slangier
                   "krosnelė": "stove",        # re-cut to the wood-burning sense
                   "keltis": "to get up",      # Wikt 'to rise'; daily-routine sense
                   "praustis": "to wash (oneself)",  # was 'to wash' — see skalbti
                   "šaltis": "cold (weather)",  # 'frost' is šalna/šerkšnas
                   "prašymas": "application",   # the written-paper sense
                   "išmokti": "to learn (master)",  # aspect pair with mokytis
                   "vagonas": "carriage (railway car)",   # 'wagon' is a cart
                   "reisas": "flight, trip",    # def also covers bus journeys
                   "eiti": "to go (on foot)",   # 'to walk' undersells it
                   "pasienis": "border area",   # 'borderland' is literary
                   "pildyti": "to fill in (a form)",   # not filling a container
                   "kariauti": "to wage war",   # 'to battle' too narrow
                   "pavargti": "to get tired",  # 'to tire' reads transitive
                   "skalbti": "to wash (clothes)",     # collided with plauti
                   "ligonis": "sick person",    # 'patient' belongs to pacientas
                   "kursas": "year (of study)",  # 'course' contradicted the def
                   "kirpti": "to cut (with scissors)",  # 'to clip' wrong for hair
                   "sesija": "exam session",    # bare 'session' collided
                   "pardavėjas": "shop assistant",     # 'salesman' is gendered
                   "laikrodis": "clock/watch",  # one LT word covers both
                   "papuošalas": "piece of jewellery",  # ornaments aren't worn
                   "švarkas": "suit jacket",    # 'jacket' collided with striukė
                   "taurė": "wine glass",       # 'cup' collided with puodukas
                   "kiaušinienė": "fried eggs",  # def says 'be pieno'
                   "atrodyti": "to look (like)",  # this sense is look, not seem
                   "avėti": "to wear (footwear)",      # vs dėvėti for clothes
                   "barščiai": "beetroot soup",  # deck's other cards say this
                   "giminė": "relatives",       # 'family' belongs to šeima
                   "estė": "Estonian woman",    # matches danė / vokietė pattern
                   "graikė": "Greek woman",     # same pattern
                   "forma": "shape",            # def is about round/long/square
                   "japonas": "Japanese man",   # bare 'Japanese' is the adjective
                   "jautis": "ox, bull",        # jautis is the ox; bulius is bull
                   "keletas": "a few, several",  # 'a couple' implies two
                   "kūrinys": "work, piece",    # 'creation' is not idiomatic
                   "linksniuotė": "declension (class)",  # vs linksniavimas
                   "ožys": "billy goat",        # 'goat' collided with ožka
                   "posėdis": "meeting (formal)",      # 'session' is not English
                   "prašyti": "to ask for",     # vs klausti, 'to ask'
                   "skara": "headscarf",        # 'scarf' collided with šalikas
                   "skyrius": "chapter",        # a titled part of a book
                   "tarnautojas": "clerk",      # 'employee' is darbuotojas
                   "vainikas": "wreath",        # worn on the head, not a garland
                   "valdymas": "rule",          # 'governance' is above the level
                   "šiukšlės": "rubbish, trash",       # 'litter' is scattered
                   "žibintas": "street lamp",   # the bare card is the street one
                   "remontas": "renovation",    # walls painted, windows changed
                   "centras": "centre",        # British spelling, as the
                                               # example sentence already used
                   # ---- batch31. Each gloss is deliberate; the
                   # Wiktionary wording is quoted where it differs.
                   "nulis": "zero",            # Wiktionary has no gloss at all
                   "atsiprašyti": "to apologise",   # Wikt: US spelling only
                   "pora": "couple",           # Wikt: 'pair'
                   "žaidėjas": "player (in sport)",  # 'player' alone collides
                   "tirpti": "to melt",        # sense sits past wikt_gloss n=4
                   "gaminti": "to cook",       # Wikt: 'to produce; to prepare'
                   "raidė": "letter (of the alphabet)",  # vs laiškas
                   "kantrus": "patient (able to wait)",  # vs the noun pacientas
                   "nemokamas": "free (of charge)",      # Wikt: 'free of charge'
                   }   # words absent from Wiktionary -> gloss unverifiable

PRONOUNS = {"mano", "tavo", "jo", "jos", "man", "tau", "jam", "jai",
            "mums", "jums", "jiems", "joms", "mus", "jus", "juos", "jas",
            "jūsų", "mūsų", "jį", "ją", "kurį", "kurią", "kuriuo", "kuria",
            "kuriam", "kuriai", "kituose", "kitam", "kitą", "kitos", "kito",
            # personal pronouns: previously only passed when capitalised at the
            # start of a sentence, which pushed drafts into awkward word order
            "aš", "tu", "mes", "jūs", "mane", "tave", "manęs", "tavęs",
            "sau", "save", "jų", "juose", "jose", "jomis", "jais",
            "manimi", "tavimi",
            "juo", "ja", "jame", "joje", "šiuo", "šia", "šiame", "šioje",
            "šią", "tuo", "tame", "toje", "tą"}

# Capitalisation alone no longer excuses a word from the SPELL and A2 checks.
# A capital is treated as meaningful only mid-sentence, where it cannot be an
# artefact of sentence position — or for a name on this explicit list, which
# is the only way a proper noun can open a sentence. Add to it deliberately.
PROPER_NOUNS = {
    "vilnius", "vilniaus", "vilniuje", "vilnių",
    "kaunas", "kauno", "kaune", "kauną",
    "klaipėda", "klaipėdos", "klaipėdoje",
    "lietuva", "lietuvos", "lietuvoje", "lietuvą",
    "latvija", "latvijos", "latvijoje", "latviją",
    "lenkija", "lenkijos", "lenkijoje", "lenkiją",
    "europa", "europos", "europoje", "europą",
    "amerika", "amerikos", "amerikoje", "ameriką",
    "londonas", "londono", "londone", "londoną",
    "olandija", "olandijos", "olandijoje",
    "nemunas", "nemuno", "nemune", "nemuną",
    "gedimino", "katedros", "katedra", "seimas", "seime", "seimo",
    "kalėdos", "kalėdas", "kalėdų", "dievas", "dievu", "dievo",
    "jonas", "jono", "jonui", "joną", "tomas", "tomo", "tomą",
    "ona", "onos", "oną", "rūta", "rūtos", "rūtą",
    "petraitis", "kazlauskienė", "kazlauskas",
}

SENT = re.compile(r"(?<=[.!?])\s+")


def meaningful_caps(text):
    """Capitalised tokens whose capital is not just sentence position."""
    out = set()
    for sent in SENT.split(text):
        for i, tok in enumerate(ltcard.tokenize(sent)):
            if tok[:1].isupper() and (i > 0 or tok.lower() in PROPER_NOUNS):
                out.add(tok.lower())
    return out


def spell_unknown(text, headword_forms=frozenset()):
    """Unknown words, excusing genuine proper nouns and the headword itself.

    A few A2 words (skalbyklė, džiovyklė, keitykla) are simply absent from the
    lt_LT lexicon — check_forms.py already tracks these as LEXICON_GAPS. Their
    inflections are verified when the paradigm is written, so an example
    sentence must not fail merely for containing the word it is illustrating.
    """
    p = subprocess.run(["hunspell", "-d", "lt_LT", "-i", "UTF-8", "-l"],
                       input=text, capture_output=True, text=True)
    proper = meaningful_caps(text)
    return sorted({w for w in p.stdout.split()
                   if w and w.lower() not in headword_forms
                   and (not w[0].isupper() or w.lower() not in proper)})


def main(path):
    defs = ltcard.load_defs(path)
    known = None
    if CACHE.exists():
        cache = json.load(open(CACHE, encoding="utf-8"))
        known = set(cache) | {f for v in cache.values() for f in v}
        known |= ltcard.FUNCTION_WORDS
        # 219 A2 lemmas have no Wiktionary table, so forms_cache holds only
        # their bare nominative and every inflected use looked "off-list".
        # manual_forms.tsv now carries hunspell-verified paradigms for all of
        # them — fold those in so the gate stops rejecting approved vocabulary.
        for _m in ltcard.load_manual_forms().values():
            known |= _m["forms"]
        # Vocabulary allowed inside definitions but not taught as cards. The
        # A2-only restriction made ~20 synonym pairs mutually ambiguous on the
        # definition->word card; extra_def_vocab.tsv holds the deliberate,
        # documented exceptions that buy distinctness. See that file's header.
        extra = paths.EXTRA_DEF_VOCAB
        if extra.exists():
            for _line in extra.read_text(encoding="utf-8").splitlines():
                if _line.strip() and not _line.startswith("#"):
                    _lemma, _, _forms = _line.partition("\t")
                    known.add(_lemma.strip().lower())
                    known |= {f.lower() for f in _forms.split()}
    hard_fail = False
    review = []
    manual = ltcard.load_manual_forms()
    for word, d in defs.items():
        # `word` may be a keyed sense variant (`žibintas#auto`); every
        # linguistic lookup uses the bare headword.
        head = d.get("headword") or word.split("#")[0]
        qualifier = d.get("qualifier", "")
        entries = ltcard.kaikki_entries(head)
        poses = {e.get("pos") for e in entries} & ltcard.POSES
        if d.get("pos"):
            poses &= {d["pos"]}
        problems = []
        is_manual = head in manual

        forms = set()
        for p in poses:
            forms |= ltcard.all_word_forms(entries, p)
        if is_manual:
            forms = manual[head]["forms"]

        # 1 SPELL
        bad = spell_unknown(f'{d["lt_def"]} {d["lt_example"]}', forms)
        if bad:
            problems.append(f"SPELL: unknown word(s) {bad}")

        # 2 GLOSS anchor
        glosses = " ; ".join(ltcard.wikt_gloss(entries, p, n=4)
                             for p in poses).lower()
        if is_manual:
            glosses = "(manual forms — no Wiktionary entry; "\
                      "translation relies on spot-check)"
        enw = d["en_word"].lower().replace("to ", "")
        ov = GLOSS_OVERRIDES.get(word, GLOSS_OVERRIDES.get(head))
        if ov is not None:
            # normalise the override the same way enw was, or a capitalised
            # or "to "-prefixed override can never match and silently falls
            # through to the substring test it was meant to bypass
            ov = ov.lower().replace("to ", "")
        if is_manual or (ov is not None and enw == ov):
            enw = ""          # manual word or accepted documented override
        if enw and enw not in glosses:
            problems.append(f"GLOSS: '{d['en_word']}' not found in "
                            f"Wiktionary glosses [{glosses[:90]}]")

        # 3 LEAK + 4 FORM + 5 A2
        leak = [t for t in ltcard.tokenize(d["lt_def"].lower())
                if t in forms]
        if leak:
            problems.append(f"LEAK: definition contains {leak}")
        _, found = ltcard.bold_word(d["lt_example"], forms)
        if not found:
            problems.append("FORM: no inflected form of headword in example")

        # ORDER heuristic: headword's relative position should be similar
        # in the LT example and its EN translation
        if found and d["en_example"] and d["en_word"]:
            lt_toks = [t.lower() for t in ltcard.tokenize(d["lt_example"])]
            en_toks = [t.lower() for t in ltcard.tokenize(d["en_example"])]
            lt_pos = next((i for i, t in enumerate(lt_toks) if t in forms), None)
            enw_last = d["en_word"].lower().split()[-1]
            en_pos = next((i for i, t in enumerate(en_toks)
                           if t.startswith(enw_last[:5])), None)
            if lt_pos is not None and en_pos is not None and \
               len(lt_toks) > 2 and len(en_toks) > 2:
                drift = abs(lt_pos / (len(lt_toks) - 1)
                            - en_pos / (len(en_toks) - 1))
                if drift > 0.34:
                    problems.append(
                        f"ORDER: headword moved (LT pos {lt_pos+1}/"
                        f"{len(lt_toks)}, EN pos {en_pos+1}/{len(en_toks)}) "
                        f"— keep Lithuanian word order where possible")
        if known:
            raw = d["lt_def"] + " " + d["lt_example"]
            capitalized = meaningful_caps(raw)
            def is_known(t):
                if t in known or t in forms or t in PRONOUNS:
                    return True
                if t in capitalized:          # proper nouns / sentence names
                    return True
                for pref in ("nebe", "ne"):   # negated verb forms
                    if t.startswith(pref) and t[len(pref):] in known:
                        return True
                return False
            off = sorted({t for t in ltcard.tokenize(raw.lower())
                          if len(t) > 2 and not is_known(t)})
            if off:
                problems.append(f"A2: off-list vocabulary {off}")

        # HEAD: the generated headword / inflection line
        problems += head_problems(word, d, manual)

        # QUAL: the disambiguating word must not appear in the definition
        if qualifier:
            qt = {t_.lower() for t_ in ltcard.tokenize(qualifier)}
            hit = [t_ for t_ in ltcard.tokenize(d["lt_def"].lower())
                   if t_ in qt]
            if hit:
                problems.append(f"QUAL: definition contains the "
                                f"disambiguating word {hit}")

        # 6 LEN
        if len(d["lt_def"].split()) > 12:
            problems.append(f"LEN: definition {len(d['lt_def'].split())} "
                            f"words (>12)")

        status = "OK " if not problems else "FAIL" if any(
            p.split(":")[0] in ("SPELL", "GLOSS", "LEAK", "FORM", "QUAL",
                                "HEAD")
            for p in problems) else "WARN"
        if status == "FAIL":
            hard_fail = True
        print(f"[{status}] {word}")
        for p in problems:
            print(f"       {p}")
        review.append(f"{word}\n  LT def : {d['lt_def']}\n"
                      f"  Wikt   : {glosses}\n"
                      f"  EN     : {d['en_word']} — {d['en_def']}\n"
                      f"  Pvz    : {d['lt_example']}\n"
                      f"  Pvz EN : {d['en_example']}\n")
    Path("review.txt").write_text("\n".join(review), encoding="utf-8")
    print(f"\nreview.txt written ({len(review)} words).")
    sys.exit(1 if hard_fail else 0)


if __name__ == "__main__":
    main(sys.argv[1])
