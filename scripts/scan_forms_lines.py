#!/usr/bin/env python3
"""scan_forms_lines.py — find cards whose inflection line parsed badly.

The forms line is printed on the card AND read aloud, so junk pulled out of a
Wiktionary table header ("sakinys m stress pattern 3ᵇ") is both visible and
audible. Cached table fragments differ between machines, so this has to be run
where the cache lives.
"""
import re
import sys
import ltcard
import paths

# things that never belong in "namas / namai" or "kalbėti, kalba, kalbėjo"
BAD = re.compile(r"stress pattern|declension|conjugation|inflection|"
                 r"singular|plural|masculine|feminine|\bm\b|\bf\b|"
                 r"[0-9]|[ᵃᵇᶜᵈ]", re.I)
OK_SUFFIX = re.compile(r"\(tik dgs\.\)|\(nekait\.\)")


def forms_line_for(key, d, manual):
    word = d.get("headword") or key.split("#")[0]
    if word in manual:
        return manual[word]["forms_line"], "manual"
    entries = ltcard.kaikki_entries(word)
    poses = {e.get("pos") for e in entries} & ltcard.POSES
    if d.get("pos"):
        poses &= {d["pos"]}
    for table in ltcard.wikt_lt_tables(word):
        kind = ltcard.classify_table(table)
        if kind not in poses:
            continue
        canon = ltcard.canonical(entries, kind, word)
        if kind == "noun":
            return ltcard.noun_compact(table), "wikt"
        if kind == "verb":
            return ltcard.verb_compact(table, canon), "wikt"
        fem = ltcard.feminine(entries)
        return (f"{canon} / {fem}" if fem else canon), "wikt"
    return None, "none"


def main(files):
    manual = ltcard.load_manual_forms()
    bad, missing, total = [], [], 0
    for f in files:
        for key, d in ltcard.load_defs(f).items():
            total += 1
            fl, src = forms_line_for(key, d, manual)
            if not fl:
                missing.append((f, key))
                continue
            probe = OK_SUFFIX.sub("", fl)
            if BAD.search(probe):
                bad.append((f, key, src, fl))
            # a "(tik vns.)" whose nominative looks plural means Wiktionary
            # mislabelled the table's only column — how sultys slipped through
            elif "tik vns." in fl and re.match(
                    r"\S*(ai|iai|ys|ūs|ės|os)\b", fl.split()[0]):
                bad.append((f, key, src, fl + "   <-- singular-only but the "
                                              "form looks plural"))
    for f, k, src, fl in bad:
        print(f"BAD  {f:16} {k:20} [{src}] {fl!r}")
    for f, k in missing:
        print(f"NONE {f:16} {k}")
    print(f"\n{len(bad)} suspicious, {len(missing)} unresolved, of {total} cards")
    return 1 if bad or missing else 0


if __name__ == "__main__":
    args = sys.argv[1:] or [str(p) for p in paths.batch_files()]
    sys.exit(main(args))
