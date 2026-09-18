#!/usr/bin/env python3
"""build_cache.py START END — warm forms_cache.json for a slice of the
word list, so a later build or gate run needs no network for those words.

    python3 build_cache.py 0 200
"""
import json, sys, concurrent.futures as cf
from pathlib import Path
import ltcard

words = [w.split("\t")[0] for w in
         open("a2_zodziai_v2.txt", encoding="utf-8").read().splitlines()
         if w and not w.startswith("#")]
cache = json.load(open("forms_cache.json")) if Path("forms_cache.json").exists() else {}
todo = [w for w in words if w not in cache]
start, end = int(sys.argv[1]), int(sys.argv[2])
chunk = todo[start:end]

def fetch(w):
    try:
        e = ltcard.kaikki_entries(w)
        forms = set()
        for pos in ("noun", "verb", "adj"):
            forms |= ltcard.all_word_forms(e, pos)
        return w, sorted(forms)
    except Exception:
        return w, None

ok = 0
with cf.ThreadPoolExecutor(10) as ex:
    for w, forms in ex.map(fetch, chunk):
        if forms is not None:
            cache[w] = forms; ok += 1
json.dump(cache, open("forms_cache.json", "w"), ensure_ascii=False)
print(f"chunk {start}-{end}: cached {ok}, total {len(cache)}/{len(words)}")
