"""forms.py: drafting a regular paradigm, checking it, and resume_audio's
--redo, which deletes a word's clips so they are recorded afresh."""
import json

import forms
import ltcard
import paths
import resume_audio
import spell


def test_draft_regular_noun_and_verb():
    assert forms.draft("lentyna", "noun") == (
        "lentyna\tnoun\tlentyna / lentynos\t"
        "lentyna lentynos lentynai lentyną lentyna lentynoje "
        "lentynos lentynų lentynoms lentynas lentynomis lentynose")
    assert forms.draft("skaityti", "verb").startswith(
        "skaityti\tverb\tskaityti, skaito, skaitė\t")
    assert forms.draft("xyz", "noun") is None


def test_check_reports_unknown_forms_and_excuses_lexicon_gaps(tmp_path,
                                                              monkeypatch):
    f = tmp_path / "manual.tsv"
    f.write_text("# c\nponia\tnoun\tponia / ponios\tponia ponios ponioms\n"
                 "skalbyklė\tnoun\tskalbyklė / skalbyklės\tskalbyklė skalbyklės\n",
                 encoding="utf-8")
    monkeypatch.setattr(spell, "unknown_words",
                        lambda text: ["ponioms", "skalbyklės"])
    checked, bad = forms.check(f)
    assert len(checked) == 5 and bad == ["ponioms"]


def test_cli_draft_and_check(capsys, tmp_path, monkeypatch):
    assert forms.main(["draft", "lentyna", "noun"]) == 0
    assert capsys.readouterr().out.startswith("lentyna\tnoun\t")
    assert forms.main(["draft", "xyz", "verb"]) == 1
    f = tmp_path / "m.tsv"
    f.write_text("a\tnoun\ta / b\ta b\n", encoding="utf-8")
    monkeypatch.setattr(spell, "unknown_words", lambda text: [])
    assert forms.main(["check", str(f)]) == 0
    assert "2 forms checked; 0 unknown" in capsys.readouterr().out


def test_redo_deletes_a_words_clips_and_manifest_entries(tmp_path, monkeypatch,
                                                         no_network):
    media = tmp_path / "media"
    media.mkdir()
    monkeypatch.setattr(paths, "MEDIA", media)
    monkeypatch.setattr(resume_audio, "MEDIA", media)
    monkeypatch.setattr(resume_audio, "MANIFEST", media / ".text_manifest.json")
    # the clip names the planner would use for one real batch
    f = paths.batch_files()[-1]
    planned = {p.name: t for t, p in resume_audio.clips_for(str(f))}
    for name, text in planned.items():
        (media / name).write_bytes(b"ID3" + b"\0" * 300)
    resume_audio.save_manifest({n: resume_audio.text_key(t)
                                for n, t in planned.items()})
    word = next(iter(ltcard.load_defs(str(f)))).split("#")[0]
    gone = resume_audio.invalidate([word])
    assert len(gone) == 4 and all(not (media / n).exists() for n in gone)
    left = json.loads((media / ".text_manifest.json").read_text())
    assert set(left) == set(planned) - set(gone)
    assert len(list(media.glob("*.mp3"))) == len(planned) - 4
