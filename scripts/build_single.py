#!/usr/bin/env python3
"""build_single.py — build ONE .apkg containing every batch.

build_decks.sh writes one deck per batch, which means 30 imports and 30 decks
in Anki. This puts all 1,389 notes in a single package instead, keeping the
per-batch tag so nothing is lost: every note still carries `batch::batchN`,
`pos::*` and `tema::*`, so any batch or theme can be pulled out in Anki with a
tag search or a filtered deck.

It reuses ltcard.py's own card builder — same fields, same audio, same note
GUIDs — so re-importing over an existing collection updates the notes in place
rather than duplicating them.

    python3 scripts/build_single.py                  # decks/lietuviu_A2.apkg, flat
    python3 scripts/build_single.py --subdecks tema  # subdeck per theme
    python3 scripts/build_single.py --subdecks batch # subdeck per batch
    python3 scripts/build_single.py -o ~/Desktop/lt.apkg

Audio must already be cached — run `python3 scripts/resume_audio.py` until it reports
nothing left to generate, or this will hit the LIEPA rate limit mid-build.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import genanki

import ltcard
import paths

# ---------------------------------------------------------------- audio ----
# ltcard.py synthesises a missing clip inline, which is fine, and raises when
# the service refuses — which is not: the raise happens BEFORE the note is
# appended, so a rate-limited clip silently costs a whole card. Fetching is
# wrapped here so that a card is never dropped for want of audio. Anything
# still missing at the end is simply built without that one recording, and
# rebuilding later fills it in (the note GUID is stable, so Anki updates in
# place rather than duplicating).
GAP = 1.5           # seconds between successful calls, as resume_audio.py
BACKOFFS = (15, 30, 60)     # patient but not the stock 120s x 8
MAX_STALLS = 6      # consecutive failures before giving up on audio entirely

_failed = []        # clip paths that could not be fetched
_stalls = 0
_gave_up = False


def tolerant_make_audio(text, path, voice, engine="liepa", **kw):
    """ltcard.make_audio, but a fetch failure is reported, never raised."""
    global _stalls, _gave_up
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        return
    if _gave_up:
        _failed.append(p)
        return
    for backoff in BACKOFFS:
        try:
            # attempts=1/quota_wait=0: this loop owns the retry policy
            _real_make_audio(text, path, voice, engine,
                             attempts=1, quota_wait=0)
            _stalls = 0
            time.sleep(GAP)
            return
        except Exception as exc:
            last = exc
            print(f"  audio: {p.name} failed ({exc}); waiting {backoff}s",
                  file=sys.stderr, flush=True)
            time.sleep(backoff)
    _failed.append(p)
    _stalls += 1
    if _stalls >= MAX_STALLS:
        _gave_up = True
        print(f"  audio: {MAX_STALLS} clips failed in a row — building the "
              f"rest without fetching. Run resume_audio.py later and rebuild.",
              file=sys.stderr, flush=True)


_real_make_audio = ltcard.make_audio


def strip_missing_sounds(note):
    """Blank [sound:…] references whose file was never fetched.

    Leaving the tag in place would show a missing-media error on the card;
    an empty field just means that element has no audio yet.
    """
    for i, field in enumerate(note.fields):
        m = re.fullmatch(r"\[sound:(.+?)\]", field.strip())
        if m and not (paths.MEDIA / m.group(1)).exists():
            note.fields[i] = ""



def deck_for(name, decks):
    if name not in decks:
        decks[name] = genanki.Deck(
            int(hashlib.md5(name.encode()).hexdigest()[:8], 16), name)
    return decks[name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(paths.DECKS / "lietuviu_A2.apkg"))
    ap.add_argument("--deck", default="Lietuvių A2")
    ap.add_argument("--subdecks", choices=["none", "batch", "tema"],
                    default="none",
                    help="none = one flat deck (default); batch/tema = a "
                         "subdeck per batch or per theme tag")
    ap.add_argument("--voice", default="astra")
    ap.add_argument("--engine", choices=["liepa", "edge"], default="liepa")
    ap.add_argument("--cache", default=str(paths.FORMS_CACHE))
    ap.add_argument("--no-fetch", action="store_true",
                    help="do not contact the synthesiser at all; cards whose "
                         "clips are missing are still built, just without "
                         "that recording")
    args = ap.parse_args()

    # Missing clips are fetched during the build, never a reason to skip a
    # card. Say up front how many there are, so a long fetch is not a surprise.
    import resume_audio
    missing = []
    files = paths.batch_files()
    for n, f in enumerate(files, 1):
        # The scan resolves every word's paradigm before anything is built,
        # and a word missing from the local caches costs a network round trip.
        # Without this line the build looks hung for minutes.
        print(f"  checking audio for {f.name} ({n}/{len(files)})…", flush=True)
        missing += [p for _t, p in resume_audio.clips_for(str(f))
                    if not (p.exists() and p.stat().st_size > 0)]
    if missing:
        mins = round(len(missing) * (GAP + 0.8) / 60)
        print(f"{len(missing)} audio clip(s) missing"
              + (" — building without them (--no-fetch)." if args.no_fetch else
                 f" — fetching them as we go, roughly {mins} min. "
                 f"Ctrl-C and run `python3 scripts/resume_audio.py` instead if you "
                 f"would rather do it separately; nothing is lost either way."),
              flush=True)
    ltcard.make_audio = (
        (lambda *a, **k: None) if args.no_fetch else tolerant_make_audio)

    known = None
    if Path(args.cache).exists():
        cache = json.load(open(args.cache, encoding="utf-8"))
        known = set()
        for w, forms in cache.items():
            known.add(w)
            known.update(forms)
        known |= ltcard.FUNCTION_WORDS

    media_dir = paths.MEDIA
    media_dir.mkdir(exist_ok=True)
    decks, media, errors = {}, [], []
    total = 0

    for path in paths.batch_files():
        tag = f"batch::{path.stem.replace('_full', '')}"
        defs = ltcard.load_defs(str(path))
        notes = []
        print(f"=== {path.name} ({len(defs)} card(s))", flush=True)
        for key in defs:
            try:
                ltcard.process_word(key, args.voice, media_dir, defs, notes,
                                    media, errors, engine=args.engine,
                                    known=known, extra_tags=[tag])
            except Exception as exc:
                errors.append(f"{key}: error — {exc}")
        for note in notes:
            strip_missing_sounds(note)
            if args.subdecks == "batch":
                name = f"{args.deck}::{tag.split('::')[1]}"
            elif args.subdecks == "tema":
                # tags are tema::egzaminas::01-… / tema::papildoma::13-… ;
                # "Egzamino" sorts before "Papildomos", so the twelve topics
                # of the ministry's A2 description come first in the deck list
                tema = next((t[len("tema::"):] for t in note.tags
                             if t.startswith("tema::")), "be-temos")
                group, _, leaf = tema.rpartition("::")
                pretty = {"egzaminas": "Egzamino temos",
                          "papildoma": "Papildomos temos"}.get(group, group)
                name = f"{args.deck}::{pretty}::{leaf}" if pretty \
                    else f"{args.deck}::{leaf}"
            else:
                name = args.deck
            deck_for(name, decks).add_note(note)
        total += len(notes)

    if not total:
        sys.exit("no cards generated")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pkg = genanki.Package(list(decks.values()))
    # the same clip is shared by both cards of a note; genanki would happily
    # pack it twice, and it raises on a path that is not there
    pkg.media_files = sorted({str(m) for m in media if Path(m).exists()})
    pkg.write_to_file(str(out))
    print(f"\nWrote {out}: {total} note(s), {2 * total} cards, "
          f"{len(pkg.media_files)} media file(s), {len(decks)} deck(s).")
    if _failed:
        print(f"{len(_failed)} clip(s) could not be fetched; those cards are "
              f"in the deck without that one recording. Run "
              f"`python3 scripts/resume_audio.py` and rebuild to fill them in — the "
              f"note GUIDs are stable, so Anki will update in place.",
              file=sys.stderr)
    # ltcard.py uses one list for both real failures and informational notes
    # ("NOTE — built from manual forms"); only the former should fail a build,
    # exactly as build_decks.sh treats them
    fatal = [e for e in errors if "NOTE —" not in e and "WARNING —" not in e]
    for e in errors:
        print("!" if e in fatal else "·", e, file=sys.stderr)
    if fatal:
        sys.exit(f"{len(fatal)} card(s) failed — see above")


if __name__ == "__main__":
    main()
