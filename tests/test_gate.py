"""The QA gate's rules, one at a time, without hunspell: the spell checker
is stubbed so each test exercises exactly one rule on a real card."""
import pytest

import ltcard
import paths
import spell
import verify_defs


def real_line(head):
    for f in paths.batch_files():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.split("\t", 1)[0] == head:
                return line.split("\t")
    raise LookupError(head)


@pytest.fixture
def gate(tmp_path, monkeypatch, no_network, capsys):
    """gate(**column overrides) -> (hard_fail, printed report)."""
    monkeypatch.setattr(spell, "unknown_words", lambda text: [])

    def run(head="kelionė", key=None, **over):
        cols = real_line(head)
        names = ["key", "lt_def", "en_word", "en_def", "lt_example",
                 "en_example", "pos", "qualifier"]
        cols += [""] * (len(names) - len(cols))
        row = dict(zip(names, cols))
        row.update(over)
        if key:
            row["key"] = key
        f = tmp_path / "one.tsv"
        f.write_text("\t".join(row[n] for n in names).rstrip("\t") + "\n",
                     encoding="utf-8")
        hard, _ = verify_defs.check(str(f))
        return hard, capsys.readouterr().out
    return run


def test_a_real_card_passes(gate):
    hard, out = gate()
    assert not hard and "[OK ]" in out


def test_leak_the_headword_in_its_own_definition(gate):
    hard, out = gate(lt_def="Ilga kelionė į kitą šalį.")
    assert hard and "LEAK:" in out


def test_form_the_example_must_inflect_the_headword(gate):
    hard, out = gate(lt_example="Mes važiuojame į Vilnių.")
    assert hard and "FORM:" in out


def test_len_is_only_a_warning(gate):
    hard, out = gate(lt_def="Tai yra labai ilga ir nelabai gera vieta, "
                            "kur žmonės eina ir eina ir eina.")
    assert not hard and "LEN:" in out and "[WARN]" in out


def test_gloss_must_be_a_wiktionary_gloss(gate):
    hard, out = gate(en_word="banana")
    assert hard and "GLOSS:" in out


def test_gloss_override_is_taken_on_trust(gate, monkeypatch):
    monkeypatch.setattr(ltcard, "load_gloss_overrides",
                        lambda *a: {"kelionė": "Banana"})
    hard, out = gate(en_word="banana")
    assert not hard and "GLOSS:" not in out


def test_gloss_override_may_target_one_sense(gate, monkeypatch):
    monkeypatch.setattr(ltcard, "load_gloss_overrides",
                        lambda *a: {"kelionė#x": "banana"})
    assert not gate(key="kelionė#x", en_word="banana", qualifier="ilga")[0]
    assert gate(en_word="banana")[0]                  # the bare key is not covered


def test_qual_the_qualifier_must_not_appear_in_the_definition(gate):
    hard, out = gate(key="kelionė#x", qualifier="ilga",
                     lt_def="Ilga išvyka į kitą vietą.")
    assert hard and "QUAL:" in out


def test_spell_reports_what_hunspell_rejects(gate, monkeypatch):
    monkeypatch.setattr(spell, "unknown_words", lambda text: ["išvyka"])
    hard, out = gate()
    assert hard and "SPELL: unknown word(s) ['išvyka']" in out


def test_spell_excuses_the_headword_and_listed_proper_nouns(gate, monkeypatch):
    monkeypatch.setattr(spell, "unknown_words",
                        lambda text: ["kelionės", "Vilnius"])
    hard, out = gate(lt_example="Vilnius yra kelionės tikslas.")
    assert not hard and "SPELL:" not in out


def test_a2_flags_vocabulary_outside_the_list(gate):
    hard, out = gate(lt_example="Mūsų kelionė buvo ekstravagantiška.")
    assert not hard and "A2: off-list vocabulary ['ekstravagantiška']" in out


def test_head_catches_a_mis_parsed_forms_line(gate, monkeypatch):
    monkeypatch.setattr(ltcard, "load_manual_forms", lambda *a: {
        "kelionė": dict(pos="noun", forms_line="kelionė m stress pattern 3",
                        forms={"kelionė", "kelionės", "kelionę"})})
    hard, out = gate()
    assert hard and "HEAD: forms line looks mis-parsed" in out
