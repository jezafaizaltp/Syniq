"""Calm and movement help, reading colours, and the gentle check-up note for parents."""

from datetime import datetime, timedelta

from tests.test_api import client, login  # noqa: F401  (must load first: sets up the test database)

from sqlalchemy import select

from app import learning
from app.db import SessionLocal
from app.engine import checkup, detect
from app.models import Item

NOW = datetime(2026, 11, 7, 12, 0)


def _answers(days: int, per_day: int, right_every: int) -> list[tuple[datetime, bool]]:
    """per_day answers a day for `days` days; every right_every-th one right."""
    out = []
    n = 0
    for d in range(days):
        for _ in range(per_day):
            n += 1
            out.append((NOW - timedelta(days=d, hours=1), n % right_every == 0))
    return out


def test_calm_and_motor_are_chosen_not_noticed():
    assert {"calm", "motor"} <= set(detect.CHOSEN)
    assert not {"calm", "motor"} & set(detect.NOTICED)


def test_student_can_switch_on_calm_motor_tint_and_spacing():
    me = login("rahul@demo.syniq")
    r = client.put(
        "/me/settings",
        json={"support_modes": ["calm", "motor"], "reading_tint": "blue", "wide_spacing": True},
        headers=me,
    )
    assert r.status_code == 200
    s = r.json()
    assert s["support_modes"] == ["calm", "motor"] and s["reading_tint"] == "blue" and s["wide_spacing"] is True
    assert client.put("/me/settings", json={"reading_tint": "purple"}, headers=me).status_code == 400
    assert client.put("/me/settings", json={"support_modes": ["autism"]}, headers=me).status_code == 400
    client.put("/me/settings", json={"support_modes": [], "reading_tint": "none", "wide_spacing": False}, headers=me)


def test_parent_can_switch_on_calm_and_motor():
    g = login("parent@demo.syniq")
    kid = client.get("/guardian/children", headers=g).json()[0]
    r = client.put(f"/guardian/children/{kid['id']}/support", json={"modes": ["calm", "motor"]}, headers=g)
    assert r.status_code == 200
    kid = next(k for k in client.get("/guardian/children", headers=g).json() if k["id"] == kid["id"])
    assert kid["support_modes"] == ["calm", "motor"]
    client.put(f"/guardian/children/{kid['id']}/support", json={"modes": []}, headers=g)


def test_motor_gives_number_questions_answers_to_tap():
    with SessionLocal() as db:
        items = db.scalars(select(Item).where(Item.kind == "numeric")).all()
        item = next(i for i in items if learning.public_item(i, {"support_modes": ["tap_to_answer"]}).get("choices"))
        assert "choices" not in learning.public_item(item, {})
        assert learning.public_item(item, {"support_modes": ["motor"]})["choices"]


# --- The check-up note: a rule, never a label -----------------------------------------------


def test_no_note_for_a_child_who_is_doing_fine():
    assert not checkup.show_note(_answers(35, 4, 2), noticed_on=0, stuck_topics=0, now=NOW)  # half right
    assert not checkup.show_note(_answers(35, 4, 1), noticed_on=3, stuck_topics=0, now=NOW)  # help on, but not stuck


def test_no_note_from_a_short_hard_patch():
    # Mostly wrong, but only for two weeks: a hard chapter, not a pattern.
    assert not checkup.show_note(_answers(14, 10, 5), noticed_on=2, stuck_topics=5, now=NOW)
    # Or too few answers to say anything.
    assert not checkup.show_note(_answers(40, 1, 5), noticed_on=2, stuck_topics=5, now=NOW)


def test_note_after_weeks_of_finding_things_hard():
    assert checkup.show_note(_answers(35, 4, 4), noticed_on=0, stuck_topics=0, now=NOW)  # a quarter right
    assert checkup.show_note(_answers(35, 4, 2) + _answers(1, 0, 1), noticed_on=2, stuck_topics=3, now=NOW)


def test_parent_can_hide_the_note_for_six_months():
    hard = _answers(35, 4, 4)
    assert not checkup.show_note(hard, 0, 0, NOW, hidden_at=NOW - timedelta(days=30))
    assert checkup.show_note(hard, 0, 0, NOW, hidden_at=NOW - timedelta(days=checkup.HIDE_DAYS + 1))


def test_parent_sees_note_flag_and_can_hide_it_child_cannot_see_it():
    g = login("parent@demo.syniq")
    kid = client.get("/guardian/children", headers=g).json()[0]
    assert kid["checkup_note"] is False  # demo children have too little practice for any note
    r = client.post(f"/guardian/children/{kid['id']}/checkup-note/hide", headers=g)
    assert r.status_code == 200
    assert client.post("/guardian/children/99999/checkup-note/hide", headers=g).status_code == 404
    # Kept on the parent's account, so nothing about it reaches the child's settings.
    me = login("rahul@demo.syniq")
    assert "checkup" not in str(client.get("/me", headers=me).json())


def test_note_words_never_name_a_condition():
    import re
    from pathlib import Path

    words = Path(__file__).resolve().parents[2].joinpath("frontend/lib/i18n.ts").read_text()
    notes = " ".join(re.findall(r'"checkup\.[a-z_]+": "([^"]*)"', words)).lower()
    assert notes
    for label in ("dyslexia", "adhd", "autism", "autistic", "disab", "disorder", "delay", "deficit"):
        assert label not in notes
