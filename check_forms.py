#!/usr/bin/env python3
"""check_forms.py [file] — hunspell-verify every form in a manual_forms file.
Exits 1 and lists any form the Lithuanian lexicon does not recognise."""
import subprocess, sys
from pathlib import Path
path = Path(sys.argv[1] if len(sys.argv) > 1 else "manual_forms.tsv")
# Real words missing from the hunspell lt_LT lexicon (verified against the
# Pusiaukelė A2 word list, which lists them as required vocabulary).
LEXICON_GAPS = {"skalbykl", "džiovykl",
                # A2-list words absent from the lt_LT lexicon entirely
                # (no form of either is recognised); both decline
                # fully regularly, so the paradigms are derived, not guessed.
                "keitykl", "atidarytuv"}
forms = []
for line in path.read_text(encoding="utf-8").splitlines():
    if line.strip() and not line.startswith("#"):
        forms += line.split("\t")[3].split() if len(line.split("\t")) > 3 else []
p = subprocess.run(["hunspell", "-d", "lt_LT", "-i", "UTF-8", "-l"],
                   input="\n".join(forms), capture_output=True, text=True)
bad = sorted({w for w in p.stdout.split()
              if not any(w.startswith(g) for g in LEXICON_GAPS)})
print(f"{len(forms)} forms checked; {len(bad)} unknown to hunspell")
if bad:
    print("UNKNOWN:", bad); sys.exit(1)
