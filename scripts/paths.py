"""paths.py — where everything lives, so the scripts run from any directory.

    data/            deck source, tracked
    data/batches/    batch*.tsv, one row per card
    media_tmp/       cached audio clips        (local, gitignored)
    kaikki_cache/    cached kaikki.org lookups (local, gitignored)
    wikt_cache/      cached Wiktionary pages   (local, gitignored)
    decks/           built .apkg files         (local, gitignored)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BATCHES = DATA / "batches"

MANUAL_FORMS = DATA / "manual_forms.tsv"
FORMS_CACHE = DATA / "forms_cache.json"
THEME_FILE = DATA / "a2_zodziai_v2.txt"
EXTRA_DEF_VOCAB = DATA / "extra_def_vocab.tsv"
ACCENTED = DATA / "accented.txt"

MEDIA = ROOT / "media_tmp"
KAIKKI_CACHE = ROOT / "kaikki_cache"
WIKT_CACHE = ROOT / "wikt_cache"
DECKS = ROOT / "decks"


def batch_num(path):
    return int("".join(c for c in Path(path).stem if c.isdigit()) or 0)


def batch_files():
    """Every batch*.tsv, in numeric order (batch2 before batch10)."""
    return sorted(BATCHES.glob("batch*.tsv"), key=batch_num)
