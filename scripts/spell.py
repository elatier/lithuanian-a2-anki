"""spell.py — the one place that calls hunspell with the lt_LT dictionary.

hunspell exits non-zero and prints nothing on stdout when it cannot load a
dictionary, which used to read as "every word is spelled correctly". Every
caller now goes through unknown_words(), which stops instead.
"""
import subprocess
import sys

HELP = """\
The SPELL checks need hunspell and its Lithuanian dictionary (lt_LT.aff +
lt_LT.dic). See "Setting up" in README.md. In short:
  macOS:  brew install hunspell, then put lt_LT.aff/.dic in ~/Library/Spelling
  Debian: apt install hunspell hunspell-lt
or point DICPATH at the folder that holds them."""


def unknown_words(text):
    """Words in `text` that the lt_LT lexicon does not recognise."""
    try:
        p = subprocess.run(["hunspell", "-d", "lt_LT", "-i", "UTF-8", "-l"],
                           input=text, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(f"hunspell is not installed.\n\n{HELP}")
    if p.returncode != 0:
        sys.exit(f"hunspell failed: {p.stderr.strip()}\n\n{HELP}")
    return p.stdout.split()
