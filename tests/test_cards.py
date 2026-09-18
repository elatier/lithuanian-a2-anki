"""What a card says: the text helpers, the table parsers and the note the
builder assembles. Everything here is offline and deterministic."""
import re

import pytest
from bs4 import BeautifulSoup

import genanki
import ltcard
import paths


# ------------------------------------------------------------ text helpers --

def test_strip_stress_removes_only_the_stress_marks():
    assert ltcard.strip_stress("žibiñtas") == "žibintas"
    assert ltcard.strip_stress("mán, tavè, mẽs") == "man, tave, mes"
    assert ltcard.strip_stress("ąžuolų ėjimas ūkis įėjo") == "ąžuolų ėjimas ūkis įėjo"


def test_bold_word_matches_any_inflected_form_case_insensitively():
    html, found = ltcard.bold_word("Vaikai sėdi ant žolės.", {"žolė", "žolės"})
    assert found and html == "Vaikai sėdi ant <b>žolės</b>."
    assert ltcard.bold_word("Žolė yra žalia.", {"žolė"}) == ("<b>Žolė</b> yra žalia.", True)
    assert ltcard.bold_word("Vaikai sėdi.", {"žolė"}) == ("Vaikai sėdi.", False)


@pytest.mark.parametrize("gloss, sentence, bolded", [
    ("bush", "By the house grows a green bush.", "bush"),
    ("country", "Two countries share a border.", "countries"),
    ("to go (on foot)", "He went home.", "went"),
    ("wine glass", "She raised her wine glass.", "wine glass"),   # phrase before head
    ("Mr; sir", "Good morning, sir.", "sir"),
    ("to wage war", "They waged war for years.", "waged war"),
    ("piece of jewellery", "Two pieces of jewellery.", "pieces of jewellery"),
    ("child", "The children play.", "children"),
])
def test_bold_en_finds_the_gloss_in_its_inflected_form(gloss, sentence, bolded):
    html, found = ltcard.bold_en(sentence, gloss)
    assert found and f"<b>{bolded}</b>" in html


def test_bold_en_never_matches_a_prefix():
    html, found = ltcard.bold_en("I talked with the pharmacist.", "pharm")
    assert not found and "<b>" not in html


def test_en_candidates_prefers_the_longest_form():
    cands = ltcard.en_candidates("wine glass")
    assert cands[0] == "wine glass" and "glass" in cands
    assert cands.index("wine glass") < cands.index("glass")


def test_forms_speech_drops_notes_and_reads_alternatives_as_a_list():
    assert ltcard.forms_speech("sidãbras (tik vns.)") == "sidabras"
    assert ltcard.forms_speech("nãmas / namaĩ") == "namas , namai"


def test_canonical_strips_kaikki_annotation():
    entries = [{"pos": "noun", "forms": [
        {"form": "sakinỹs m stress pattern 3ᵇ", "tags": ["canonical"]}]}]
    assert ltcard.canonical(entries, "noun", "sakinys") == "sakinỹs"
    assert ltcard.canonical([], "noun", "sakinys") == "sakinys"


# ----------------------------------------------------------- table parsers --

def table(html):
    return BeautifulSoup(html, "html.parser").find("table")


NOUN = table("""<table class="inflection-table">
<tr><th></th><th>singular</th><th>plural</th></tr>
<tr><th>nominative</th><td>nãmas</td><td>namaĩ</td></tr>
<tr><th>genitive</th><td>nãmo</td><td>namų̃</td></tr></table>""")
PLURALE = table("""<table class="inflection-table">
<tr><th></th><th>plural</th></tr>
<tr><th>nominative</th><td>dùrys</td></tr></table>""")
VERB = table("""<table class="inflection-table">
<tr><th>indicative</th><th>aš</th><th>tu</th><th>jis/ji</th>
    <th>mes</th><th>jūs</th><th>jie/jos</th></tr>
<tr><th>present</th><td>eĩnu</td><td>einì</td><td>eĩna</td>
    <td>eĩname</td><td>eĩnate</td><td>eĩna</td></tr>
<tr><th>past</th><td>ėjaũ</td><td>ėjaĩ</td><td>ė̃jo</td>
    <td>ė̃jome</td><td>ė̃jote</td><td>ė̃jo</td></tr>
<tr><th>past frequentative</th><td>eĩdavau</td><td>eĩdavai</td><td>eĩdavo</td>
    <td>eĩdavome</td><td>eĩdavote</td><td>eĩdavo</td></tr>
</table>""")
ADJ = table("""<table class="inflection-table">
<tr><th>masculine</th><th>feminine</th></tr><tr><td>grãžus</td><td>gražì</td></tr></table>""")


def test_classify_table():
    assert ltcard.classify_table(NOUN) == "noun"
    assert ltcard.classify_table(VERB) == "verb"
    assert ltcard.classify_table(ADJ) == "adj"


def test_noun_compact_reads_singular_and_plural_nominative():
    assert ltcard.noun_compact(NOUN) == "nãmas / namaĩ"


def test_noun_compact_labels_a_one_number_noun_from_its_header():
    assert ltcard.noun_compact(PLURALE) == "dùrys (tik dgs.)"


def test_verb_compact_takes_third_person_present_and_simple_past():
    assert ltcard.verb_compact(VERB, "eĩti") == "eĩti, eĩna, ė̃jo"


# --------------------------------------------------------- pronoun tables --

def test_pronoun_table_pairs_the_confusable_column(no_network):
    manual = ltcard.load_manual_forms()
    html = ltcard.pronoun_table("aš", manual)
    assert '<th class="hd">aš</th>' in html and '<th class="hd">mes</th>' in html
    assert html.count("<tr>") == 7                       # header + six cases
    assert ltcard.pronoun_table("namas", manual) == ""
    spoken = ltcard.pronoun_speech("aš", manual).split(", ")
    assert len(spoken) == 12 and spoken[0] == "aš" and "mes" in spoken


# ------------------------------------------------------------- the builder --

def test_load_defs_splits_sense_keys_and_reads_the_qualifier(tmp_path):
    f = tmp_path / "b.tsv"
    f.write_text("žibintas#auto\tdef\theadlight\ten def\tpvz\tex\tnoun"
                 "\t02-pastatai-ir-namai\tautomobilio\n"
                 "# comment\n\nnamas\tdef\thouse\ten def\tpvz\tex\tnoun"
                 "\t02-pastatai-ir-namai\n", encoding="utf-8")
    defs = ltcard.load_defs(str(f))
    assert set(defs) == {"žibintas#auto", "namas"}
    assert defs["žibintas#auto"]["headword"] == "žibintas"
    assert defs["žibintas#auto"]["qualifier"] == "automobilio"
    assert defs["žibintas#auto"]["theme"] == "02-pastatai-ir-namai"
    assert defs["namas"]["qualifier"] == "" and defs["namas"]["pos"] == "noun"


def test_themes_come_from_the_rows_and_the_taxonomy(no_network):
    tags = ltcard.theme_tags()
    assert tags["02-pastatai-ir-namai"] == "egzaminas::02-pastatai-ir-namai"
    assert len(tags) == 18
    assert ltcard.resolve_theme("02") == "02-pastatai-ir-namai"
    assert ltcard.resolve_theme("pastatai") == "02-pastatai-ir-namai"
    assert ltcard.resolve_theme("egzaminas::06-keliones") == "06-keliones"
    with pytest.raises(LookupError, match="matches 0"):
        ltcard.resolve_theme("99")
    assert ltcard.load_themes()["kelionė"] == "egzaminas::06-keliones"


def test_display_word_shows_the_qualifier_in_lighter_type():
    assert ltcard.display_word("namas", "") == "namas"
    assert ltcard.display_word("žibintas", "automobilio") == \
        '<span class="qual">automobilio</span> žibintas'


def real_row(head):
    """A card straight from the deck, as (defs, key)."""
    for f in paths.batch_files():
        defs = ltcard.load_defs(str(f))
        for key in defs:
            if key.split("#")[0] == head:
                return defs, key
    raise LookupError(head)


def build(head, tmp_path, **kw):
    defs, key = real_row(head)
    notes, media, errors, spoken = [], [], [], []

    def tts(text, path, *a, **k):
        spoken.append((text, path.name))
    ltcard.process_word(key, "astra", tmp_path, defs, notes, media, errors,
                        tts=tts, **kw)
    return notes, media, errors, spoken, defs[key]


@pytest.mark.parametrize("head", ["kelionė",     # from the Wiktionary table
                                  "ponia"])      # from manual_forms.tsv
def test_builder_requests_four_clips_and_fills_every_field(head, tmp_path,
                                                            no_network):
    notes, media, errors, spoken, d = build(head, tmp_path)
    assert len(notes) == 1 and len(spoken) == 4 and len(media) == 4
    note = notes[0]
    texts = [t for t, _ in spoken]
    assert texts[0] == head                          # the headword, unaccented
    assert texts[2] == d["lt_def"] and texts[3] == d["lt_example"]
    assert "stress pattern" not in texts[1] and texts[1]
    fields = dict(zip([f["name"] for f in ltcard.MODEL.fields], note.fields))
    assert fields["Word"] == head
    assert fields["EN_Word"] == d["en_word"]
    assert "<b>" in fields["Pavyzdys"]              # an inflected form bolded
    assert fields["FormsLine"] and fields["POS"] == ""
    sounds = [re.fullmatch(r"\[sound:(lt_[0-9a-f]{8}_[wfde]\.mp3)\]",
                           fields[k]).group(1)
              for k in ("WordAudio", "FormsAudio", "DefAudio", "ExAudio")]
    assert sounds == [name for _, name in spoken]
    assert any(t.startswith("pos::") for t in note.tags)
    assert any(t.startswith("tema::") and not t.endswith("be-temos")
               for t in note.tags)
    assert not [e for e in errors if "WARNING" in e], errors


def test_note_identity_is_stable(tmp_path, no_network):
    a = build("kelionė", tmp_path)[0][0]
    b = build("kelionė", tmp_path)[0][0]
    assert a.guid == b.guid == genanki.guid_for("kelionė", "noun")
    assert a.fields == b.fields


def test_two_senses_are_two_notes_with_distinct_fronts(tmp_path, no_network):
    defs, _ = real_row("žibintas")
    keys = [k for k in defs if k.split("#")[0] == "žibintas"]
    assert len(keys) == 2
    notes = []
    for k in keys:
        ltcard.process_word(k, "astra", tmp_path, defs, notes, [], [],
                            tts=lambda *a, **k: None)
    assert len({n.guid for n in notes}) == 2
    assert len({n.fields[0] for n in notes}) == 2           # qualifier differs
    assert all('class="qual"' in n.fields[0] for n in notes)


def test_default_synthesiser_is_the_module_function(tmp_path, monkeypatch,
                                                    no_network):
    """Callers that patch ltcard.make_audio (the tests, older scripts) still
    reach the builder when no tts is passed."""
    calls = []
    monkeypatch.setattr(ltcard, "make_audio", lambda *a, **k: calls.append(a))
    defs, key = real_row("kelionė")
    ltcard.process_word(key, "astra", tmp_path, defs, [], [], [])
    assert len(calls) == 4
