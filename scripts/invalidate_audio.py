#!/usr/bin/env python3
"""invalidate_audio.py WORD ... — delete a word's clips so they are re-recorded.

You normally do not need this. Clip filenames hash the card key, not the
spoken text, but resume_audio.py keeps a manifest of what each clip says
(media_tmp/.text_manifest.json) and re-records any clip whose text changed.
Use this only to force a fresh recording, e.g. when a clip sounds wrong.

    python3 scripts/invalidate_audio.py kasa oda
"""
import hashlib
import json
import sys

import ltcard
import paths

MEDIA = paths.MEDIA
MANIFEST = MEDIA / ".text_manifest.json"


def main(words):
    words = set(words)
    manual = ltcard.load_manual_forms()
    man = {}
    if MANIFEST.exists():
        try:
            man = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except ValueError:
            man = {}
    gone = []
    for f in paths.batch_files():
        for key, d in ltcard.load_defs(str(f)).items():
            head = d.get("headword") or key.split("#")[0]
            if head not in words:
                continue
            kind = (manual[head]["pos"] if head in manual
                    else (d.get("pos") or "noun"))
            h = hashlib.md5(
                f"{key}:{kind}:{ltcard.AUDIO_TAG}".encode()).hexdigest()[:8]
            for suf in ("w", "f", "d", "e"):   # f only matters
                # when the SPOKEN forms change, but dropping it
                # is cheap and avoids a stale-clip class of bug
                p = MEDIA / f"lt_{h}_{suf}.mp3"
                if p.exists():
                    p.unlink()
                    man.pop(p.name, None)
                    gone.append(p.name)
    if man:
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=0),
                            encoding="utf-8")
    print(f"deleted {len(gone)} stale clip(s) for {len(words)} word(s)")
    print("rerun scripts/resume_audio.py to regenerate them")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    main(sys.argv[1:])
