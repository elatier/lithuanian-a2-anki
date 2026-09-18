#!/usr/bin/env python3
"""invalidate_audio.py [word ...] — drop clips whose Lithuanian text changed.

Clip filenames hash the card key, not the spoken text, so editing a definition
leaves the old recording in place. resume_audio.py now keeps a manifest that
catches this going forward, but clips generated before the manifest existed
have no record. Run this ONCE against the words whose text is known to have
changed; after that the manifest handles it automatically.

    python3 scripts/invalidate_audio.py           # the known list below
    python3 scripts/invalidate_audio.py kasa oda  # specific words
"""
import hashlib
import json
import sys

import ltcard
import paths

# Headwords whose definition, example or spoken form changed after their audio
# may already have been generated.
CHANGED = """
žibintas žiedas oda žalias balandis aštrus kasa narys šokti besmegenis lipti
skalbyklė džiovyklė skalbykla šviesti pati
pavardė gimtadienis miegamasis prieškambaris senamiestis ligoninė augalas
šaltis vakarienė kepti prašymas tautybė vairuoti parašas pagalvė svetainė
# 28 words whose canonical form carried kaikki annotation ("sakinỹs m stress
# pattern 3ᵇ") — that text was spoken as the headword audio
alkanas atskiras avinas brangus didelis dovana dujos gabalas gegužė kailiniai
kamuolys katinas marškiniai metai pabaiga paprastas patogus pavyzdys pažymys
sakinys saldus smegenys traukinys uodega užduotis vakarai ąžuolas žmogus
# cards whose Lithuanian was rewritten in the review pass
apžiūrėti lipdyti antra pirma kartas ateiti galima meistras spręsti tirti
kiaušinienė omletas
# definition rewritten
arbata
# example sentence reordered to fix the ORDER warnings
balkonas blogas prieškambaris svetainė lova rožė tulpė
# pronoun pass: jie/jūs/mes had their definitions rewritten, and jie/tie/šie
# now show a masculine|feminine table instead of the masculine paradigm alone,
# so their FORMS clip says twelve forms rather than six
jie jūs mes tie šie
# NOTE: the "(tik vns.)" / "(tik dgs.)" number marker was corrected on 20
# nouns, but forms_speech() strips anything in parentheses, so the spoken
# forms clip is unchanged and those words do NOT need new audio.
""".split()
CHANGED = [w for w in CHANGED if not w.startswith("#")]

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
    print("rerun resume_audio.py to regenerate them")


if __name__ == "__main__":
    main(sys.argv[1:] or CHANGED)
