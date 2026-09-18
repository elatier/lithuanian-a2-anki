#!/usr/bin/env python3
"""build_single.py — build ONE .apkg containing every batch.

Every note carries `batch::batchN`, `pos::*` and `tema::*` tags, so any batch
or theme can be pulled out in Anki with a tag search or a filtered deck.

It reuses ltcard.py's own card builder — same fields, same audio, same note
GUIDs — so re-importing over an existing collection updates the notes in place
rather than duplicating them.

    python3 scripts/build_single.py                  # decks/lietuviu_A2.apkg
    python3 scripts/build_single.py --subdecks none  # one flat deck
    python3 scripts/build_single.py --subdecks batch # subdeck per batch
    python3 scripts/build_single.py -o ~/Desktop/lt.apkg

The default is a subdeck per theme, which is what the released deck uses.

Before building, any clip that is missing or whose text changed is recorded
(see resume_audio.py). The recorded clips are in data/audio/, so that is
only ever the clips for words you added or edited. --no-fetch never contacts
the synthesiser.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

import genanki

import ltcard
import paths
import resume_audio

# ---------------------------------------------------------------- audio ----
# Recording happens BEFORE the build, in resume_audio: it records only clips
# that are missing or whose text changed, paces itself for the public
# service, and stops cleanly if the service is down. The build itself never
# calls the synthesiser, so a card is never dropped for want of audio; a clip
# that is still missing is just left off its card, and rebuilding later fills
# it in (the note GUID is stable, so Anki updates in place).


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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(paths.DECKS / "lietuviu_A2.apkg"))
    ap.add_argument("--deck", default="Lietuvių A2")
    ap.add_argument("--subdecks", choices=["none", "batch", "tema"],
                    default="tema",
                    help="tema = a subdeck per theme (default, as released); "
                         "batch = a subdeck per batch; none = one flat deck")
    ap.add_argument("--voice", default="astra")
    ap.add_argument("--engine", choices=["liepa", "edge"], default="liepa")
    ap.add_argument("--no-fetch", action="store_true",
                    help="do not contact the synthesiser at all; cards whose "
                         "clips are missing are still built, just without "
                         "that recording")
    args = ap.parse_args(argv)

    files = [str(f) for f in paths.batch_files()]
    audio_incomplete = False
    if args.no_fetch:
        man = resume_audio.load_manifest()
        missing = stale = 0
        for f in files:
            for text, p in resume_audio.clips_for(f):
                if not (p.exists() and p.stat().st_size > 0):
                    missing += 1
                elif man.get(p.name) not in (None, resume_audio.text_key(text)):
                    stale += 1
        if missing or stale:
            print(f"--no-fetch: {missing} clip(s) missing (left off their "
                  f"cards), {stale} outdated (text changed; the old recording "
                  f"is used).", flush=True)
            audio_incomplete = True
    else:
        # records only what is missing or out of date; usually nothing
        audio_incomplete = resume_audio.main(
            files, engine=args.engine, voice=args.voice, quiet=True) != 0

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
                # every clip is already recorded (or deliberately skipped),
                # so the builder is handed a synthesiser that does nothing
                ltcard.process_word(key, args.voice, media_dir, defs, notes,
                                    media, errors, engine=args.engine,
                                    extra_tags=[tag],
                                    tts=lambda *a, **k: None)
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
    if audio_incomplete:
        print("Some clips are missing; those cards are in the deck without "
              "that one recording. Run ./build_single.sh again later to record "
              "them — the note GUIDs are stable, so Anki updates in place.",
              file=sys.stderr)
    # ltcard.py uses one list for both real failures and informational notes
    # ("NOTE — built from manual forms"); only the former should fail a build
    fatal = [e for e in errors if "NOTE —" not in e and "WARNING —" not in e]
    for e in errors:
        print("!" if e in fatal else "·", e, file=sys.stderr)
    if fatal:
        sys.exit(f"{len(fatal)} card(s) failed — see above")


if __name__ == "__main__":
    main()
