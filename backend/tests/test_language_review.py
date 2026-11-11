"""The Malayalam/Hindi review workbook builds and reads back cleanly (tools/malayalam_review.py)."""
import tests.test_api  # noqa: F401  (sets up the test database before app modules load)

from openpyxl import load_workbook

from tools import malayalam_review as review


def _build(tmp_path, lang="ml"):
    out = tmp_path / f"{lang}.xlsx"
    review.write(out, review.question_rows(None, lang), review.app_word_rows(lang), lang)
    return out


def test_workbook_builds_for_both_languages(tmp_path):
    for lang in ("ml", "hi"):
        wb = load_workbook(_build(tmp_path, lang))
        assert wb.sheetnames == ["Questions", "App words"]
        assert wb["Questions"].max_row > 100
        assert wb["Questions"]["L1"].value == "id"


def test_untouched_workbook_changes_nothing(tmp_path):
    result = review.apply_workbook(_build(tmp_path), dry_run=True)
    assert result.applied == [] and result.problems == [] and result.notes == []


def test_edits_and_notes_are_read_back(tmp_path):
    path = _build(tmp_path)
    wb = load_workbook(path)
    row = wb["Questions"][2]
    row[3].value = row[3].value + " (തിരുത്ത്)"
    row[9].value = "ഒരു ചിത്രം വേണം"
    wb.save(path)
    result = review.apply_workbook(path, dry_run=True)
    assert len(result.applied) == 1 and "(തിരുത്ത്)" in result.applied[0]
    assert result.notes == [result.notes[0]] and "ചിത്രം" in result.notes[0]
    assert result.problems == []
