#!/usr/bin/env python3
"""resume_audio.py [batchN.tsv ...] — generate the remaining LIEPA clips
politely, one at a time, and resume where it stopped.

The public synthesiser at sinteze.intelektika.lt rate-limits hard: a short
burst is fine, sustained parallel load gets 403 "Quota reached" and then
connection resets. This walks the clips serially with a gap between calls and
a long, patient backoff, so a full run just takes a while instead of failing.

Every clip is written to media_tmp/ as soon as it arrives, and existing files
are skipped, so interrupting this at any point loses nothing — rerun it.

    python3 scripts/resume_audio.py                               # every batch
    python3 scripts/resume_audio.py data/batches/batch12.tsv      # just one

When it reports 0 missing, build the deck with:
    ./build_single.sh --subdecks tema
"""
import hashlib
import json
import sys
import time
from datetime import datetime

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
    """(text, path) for every clip a batch needs."""
    defs = ltcard.load_defs(defs_path)
    manual = ltcard.load_manual_forms()
    jobs = []
    for key, d in defs.items():
        # a key may be `headword#sense`; the clip hash uses the full key (so
        # two senses get separate audio) but every lookup uses the headword,
        # and the word clip speaks the qualified phrase, matching ltcard.py
        word = d.get("headword") or key.split("#")[0]
        qual = d.get("qualifier", "")
        if word in manual:
            kind = manual[word]["pos"]
            forms = manual[word]["forms_line"]
            canon = word
        else:
            entries = ltcard.kaikki_entries(word)
            poses = {e.get("pos") for e in entries} & ltcard.POSES
            kind = forms = canon = None
            for t in ltcard.wikt_lt_tables(word):
                k = ltcard.classify_table(t)
                if k not in poses:
                    continue
                canon = ltcard.canonical(entries, k, word)
                forms = (ltcard.noun_compact(t) if k == "noun"
                         else ltcard.verb_compact(t, canon) if k == "verb"
                         else f"{canon} / {ltcard.feminine(entries)}")
                kind = k
                break
        if not forms:
            continue
        h = hashlib.md5(f"{key}:{kind}:{ltcard.AUDIO_TAG}".encode()).hexdigest()[:8]
        jobs += [(f"{qual} {ltcard.strip_stress(canon)}".strip(),
                  MEDIA / f"lt_{h}_w.mp3"),
                 (ltcard.forms_clip_text(word, forms, manual),
                  MEDIA / f"lt_{h}_f.mp3"),
                 (d["lt_def"], MEDIA / f"lt_{h}_d.mp3"),
                 (d["lt_example"], MEDIA / f"lt_{h}_e.mp3")]
    return jobs


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def main(paths):
    ltcard.AUDIO_LOG = log          # trace every HTTP attempt into this log
    log(f"scanning {len(paths)} batch file(s)…")
    log(f"endpoint {ltcard.LIEPA_URL}  timeout {ltcard.LIEPA_TIMEOUT}s  "
        f"voice astra  speed {ltcard.LIEPA_SPEED}")
    man = load_manifest()
    todo, stale = [], 0
    for n, p in enumerate(paths, 1):
        # The scan resolves every word's paradigm before a single clip is
        # fetched, and a word missing from the local caches costs a network
        # round trip. Without this line the script looks hung for minutes.
        log(f"  scanning {p} ({n}/{len(paths)})…")
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
    log(f"{len(todo)} clip(s) to generate"
        + (f" ({stale} stale, text had changed)" if stale else "")
        + f"; {len(man)} already done")
    stalls = done = 0
    for i, (text, path) in enumerate(todo, 1):
        while True:
            try:
                # attempts=1/quota_wait=0: this loop owns retries and pacing
                ltcard.make_audio(text, path, "astra", "liepa",
                                  attempts=1, quota_wait=0)
                man[path.name] = text_key(text)
                done += 1
                stalls = 0
                break
            except Exception as exc:
                stalls += 1
                if stalls >= MAX_STALLS:
                    log(f"throttled {stalls}x in a row — stopping at "
                        f"{done}/{len(todo)}. Rerun later; nothing is lost.")
                    log(f"last error: {exc}")
                    save_manifest(man)
                    return 1
                log(f"  throttled ({stalls}/{MAX_STALLS}) at "
                    f"{done}/{len(todo)}, waiting {BACKOFF}s…")
                time.sleep(BACKOFF)
        if i % 10 == 0:
            log(f"--- {i}/{len(todo)} done")
        time.sleep(GAP)
    save_manifest(man)
    log(f"DONE — {done} new clip(s), nothing left to generate")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:] or [str(p) for p in paths.batch_files()]
    sys.exit(main(args))
