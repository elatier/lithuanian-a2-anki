"""spell.py — the one place that calls hunspell with the Lithuanian dictionary.

The dictionary ships with the repo (data/hunspell/lt_LT.aff and .dic, the
ispell-lt lexicon by Albertas Agejevas, BSD-licensed — see the COPYING file
beside them), so only the hunspell binary has to be installed.

hunspell exits non-zero and prints nothing on stdout when it cannot load a
dictionary, which used to read as "every word is spelled correctly". Every
caller now goes through unknown_words(), which stops instead.
"""
import subprocess
import sys

import paths

DICT = paths.HUNSPELL / "lt_LT"          # hunspell -d takes a path prefix

HELP = """\
The SPELL checks need the hunspell binary. See "Setting up" in README.md:
  macOS:  brew install hunspell
  Debian: apt install hunspell
The Lithuanian dictionary is in the repo (data/hunspell/)."""


def unknown_words(text):
    """Words in `text` that the lt_LT lexicon does not recognise."""
    try:
        p = subprocess.run(["hunspell", "-d", str(DICT), "-i", "UTF-8", "-l"],
                           input=text, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(f"hunspell is not installed.\n\n{HELP}")
    if p.returncode != 0:
        sys.exit(f"hunspell failed: {p.stderr.strip()}\n\n{HELP}")
    return p.stdout.split()
