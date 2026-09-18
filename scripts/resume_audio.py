#!/usr/bin/env python3
"""resume_audio.py [batchN.tsv ...] — record the missing or outdated LIEPA
clips politely, one at a time, and resume where it stopped.

The public synthesiser at sinteze.intelektika.lt rate-limits hard: a short
burst is fine, sustained parallel load gets 403 "Quota reached" and then
connection resets. This walks the clips serially with a gap between calls and
a long, patient backoff, so a full run just takes a while instead of failing.

Every clip is written to data/audio/ as soon as it arrives, and existing files
are skipped, so interrupting this at any point loses nothing — rerun it. A
clip whose text has changed since it was recorded (a definition was edited)
is re-recorded: data/audio/.text_manifest.json records what each clip says.

build_single.sh runs this before building, so you rarely need it directly.

    python3 scripts/resume_audio.py                               # every batch
    python3 scripts/resume_audio.py data/batches/batch12.tsv      # just one

"""
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import ltcard
import paths

GAP = 1.5          # seconds between successful calls
BACKOFF = 60       # seconds to wait after a throttle
MAX_STALLS = 20    # give up after this many consecutive throttles

MEDIA = paths.MEDIA
MEDIA.mkdir(exist_ok=True)

# Clip filenames hash the card key, not the spoken text, so editing a
# definition would otherwise leave the old recording in place forever. This
# manifest records what each clip actually says; a mismatch means the clip is
# stale and gets regenerated.
MANIFEST = MEDIA / ".text_manifest.json"


def load_manifest():
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def save_manifest(m):
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=0),
                        encoding="utf-8")


def text_key(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def clips_for(defs_path):
    """(text, path) for every clip a batch needs.

    Runs ltcard's own card builder with the synthesiser swapped for a
    recorder, so the clip names and texts are exactly the ones the deck will
    reference. This used to re-derive them separately, and for four words it
    picked a different part of speech than the builder (which honours the
    row's pos column), so it recorded 16 clips no card ever used.
    """
    defs = ltcard.load_defs(defs_path)
    jobs = []
    for key in defs:
        ltcard.process_word(key, "astra", MEDIA, defs, [], [], [],
                            tts=lambda text, path, *a, **k: jobs.append(
                                (text, Path(path))))
    return jobs


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def plan(files, quiet=False):
    """Work out which clips need recording.

    Returns (todo, manifest, stale): todo is a list of (text, path) that are
    missing or whose text has changed since they were recorded; stale clips
    are deleted here so nothing can build them into a deck by mistake.
    """
    man = load_manifest()
    todo, stale = [], 0
    for n, p in enumerate(files, 1):
        # The scan resolves every word's paradigm before a single clip is
        # fetched, and a word missing from the local caches costs a network
        # round trip. Without this line the script looks hung for minutes.
        if not quiet:
            log(f"  scanning {Path(p).name} ({n}/{len(files)})…")
        for text, path in clips_for(p):
            fresh = path.exists() and path.stat().st_size > 0
            if fresh and man.get(path.name) not in (None, text_key(text)):
                path.unlink()               # text changed since it was spoken
                fresh = False
                stale += 1
            if fresh:
                man.setdefault(path.name, text_key(text))
            else:
                todo.append((text, path))
    save_manifest(man)
    return todo, man, stale


def record(todo, man, engine="liepa", voice="astra"):
    """Synthesise every (text, path) in todo, politely. 0 = all done."""
    stalls = done = 0
    for i, (text, path) in enumerate(todo, 1):
        while True:
            try:
                # attempts=1/quota_wait=0: this loop owns retries and pacing
                ltcard.make_audio(text, path, voice, engine,
                                  attempts=1, quota_wait=0)
                man[path.name] = text_key(text)
                done += 1
                stalls = 0
                break
            except Exception as exc:
                stalls += 1
                if stalls >= MAX_STALLS:
                    log(f"failed {stalls}x in a row — stopping at "
                        f"{done}/{len(todo)}. Rerun later; nothing is lost.")
                    log(f"last error: {exc}")
                    save_manifest(man)
                    return 1
                log(f"  failed ({stalls}/{MAX_STALLS}) at "
                    f"{done}/{len(todo)}: {exc}; waiting {BACKOFF}s…")
                time.sleep(BACKOFF)
        if i % 10 == 0:
            log(f"--- {i}/{len(todo)} done")
            save_manifest(man)
        time.sleep(GAP)
    save_manifest(man)
    return 0


def main(files, engine="liepa", voice="astra", quiet=False):
    ltcard.AUDIO_LOG = log          # trace every HTTP attempt into this log
    if not quiet:
        log(f"scanning {len(files)} batch file(s)…")
    todo, man, stale = plan(files, quiet)
    log(f"{len(todo)} clip(s) to record"
        + (f" ({stale} stale, text had changed)" if stale else "")
        + f"; {len(man)} already done")
    if not todo:
        return 0
    log(f"endpoint {ltcard.LIEPA_URL}  timeout {ltcard.LIEPA_TIMEOUT}s  "
        f"voice {voice}  speed {ltcard.LIEPA_SPEED}")
    rc = record(todo, man, engine, voice)
    if rc == 0:
        log(f"DONE — {len(todo)} new clip(s), nothing left to record")
    return rc


if __name__ == "__main__":
    args = sys.argv[1:] or [str(p) for p in paths.batch_files()]
    sys.exit(main(args))
