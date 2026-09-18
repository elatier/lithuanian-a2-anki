"""paths.py — where everything lives, so the scripts run from any directory.

    data/            deck source, tracked
    data/batches/    batch*.tsv, one row per card
    data/cache/      kaikki.org and Wiktionary lookups, tracked so a build
                     is reproducible and needs no network
    data/audio/      the recorded clips and .text_manifest.json, tracked so
                     nobody re-records what is already recorded
    decks/           built .apkg files   (local, gitignored)
    out/             review.txt, needs_accents.txt, previews (local, gitignored)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BATCHES = DATA / "batches"

MANUAL_FORMS = DATA / "manual_forms.tsv"
FORMS_CACHE = DATA / "forms_cache.json"
THEME_FILE = DATA / "a2_zodziai_v2.txt"
EXTRA_DEF_VOCAB = DATA / "extra_def_vocab.tsv"
HUNSPELL = DATA / "hunspell"        # lt_LT.aff + lt_LT.dic, BSD (see COPYING)
ACCENTED = DATA / "accented.txt"
FUNCTION_WORDS = DATA / "function_words.txt"
PROPER_NOUNS = DATA / "proper_nouns.txt"
GLOSS_OVERRIDES = DATA / "gloss_overrides.tsv"

MEDIA = DATA / "audio"
KAIKKI_CACHE = DATA / "cache" / "kaikki"
WIKT_CACHE = DATA / "cache" / "wikt"
DECKS = ROOT / "decks"
OUT = ROOT / "out"


def batch_num(path):
    return int("".join(c for c in Path(path).stem if c.isdigit()) or 0)


def batch_files():
    """Every batch*.tsv, in numeric order (batch2 before batch10)."""
    return sorted(BATCHES.glob("batch*.tsv"), key=batch_num)
