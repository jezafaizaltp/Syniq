"""Harder questions count: secure needs one right, practice steps up and down by answers, challenge setting."""


from tests.test_api import client, login  # first: points the app at a fresh test database

from app import learning
from app.db import SessionLocal
from app.engine import mastery as m
from app.engine import rules
from app.models import User
from tests.test_mistake_patterns import items_of, new_student


def state(p, right=0, wrong=0):
    return rules.ConceptState(concept_id=1, order=1, p_known=p, right_streak=right, wrong_in_row=wrong)


def test_practice_steps_up_after_a_run_of_right_answers():
    assert rules.practice_difficulty(state(0.5)) == (2, None)
    assert rules.practice_difficulty(state(0.5, right=3)) == (3, "step_up")
    assert rules.practice_difficulty(state(0.5, right=2)) == (2, None)
    assert rules.practice_difficulty(state(0.5, right=2), challenge=True) == (3, "step_up")
    assert rules.practice_difficulty(state(0.9, right=9)) == (3, None)  # already the top level


def test_practice_steps_down_after_two_wrong_in_a_row():
    assert rules.practice_difficulty(state(0.9, wrong=2)) == (2, "step_down")
    assert rules.practice_difficulty(state(0.9, wrong=1)) == (3, None)
    assert rules.practice_difficulty(state(0.2, wrong=5)) == (1, None)  # never below the first level


def test_cap_until_a_hard_question_is_right():
    assert m.cap_until_hard_right(0.99, True, False, False) == m.CAP_UNTIL_HARD_RIGHT
    assert m.cap_until_hard_right(0.99, True, True, False) == 0.99
    assert m.cap_until_hard_right(0.99, False, False, False) == 0.99  # topic has no hard questions
    assert m.cap_until_hard_right(0.99, True, False, True) == 0.99  # secure before: never taken away
    assert m.cap_until_hard_right(0.5, True, False, False) == 0.5
    assert m.CAP_UNTIL_HARD_RIGHT < m.SECURE_THRESHOLD


def test_easy_answers_alone_do_not_secure_a_topic():
    sid = new_student("hari.hq@demo.syniq")
    cid, items = items_of("math9.square_of_sum")
    easy = [i for i in items if i.difficulty < m.HARD and i.status == "approved"]
    hard = [i for i in items if i.difficulty >= m.HARD and i.status == "approved"]
    assert easy and hard
    with SessionLocal() as db:
        student = db.get(User, sid)
        for n in range(30):
            item = easy[n % len(easy)]
            *_, row = learning.record_attempt(db, student, item, item.answer, 0, 5000, None)
            db.commit()
        assert not m.is_secure(row.p_known, row.attempts)
        assert row.p_known == m.CAP_UNTIL_HARD_RIGHT
        *_, row = learning.record_attempt(db, student, hard[0], hard[0].answer, 0, 5000, None)
        db.commit()
        assert m.is_secure(row.p_known, row.attempts)


def test_challenge_setting_is_saved():
    h = login("anu@demo.syniq")
    r = client.put("/me/settings", json={"more_challenges": True}, headers=h)
    assert r.status_code == 200, r.text
    assert client.get("/me", headers=h).json()["settings"]["more_challenges"] is True
    assert client.put("/me/settings", json={"more_challenges": "yes"}, headers=h).status_code == 400
    client.put("/me/settings", json={"more_challenges": False}, headers=h)
