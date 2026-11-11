"""Lessons: a new topic is taught one idea at a time, each with a quick check, before any practice."""

from sqlalchemy import select

from tests.test_api import client, login  # first: points the app at a fresh test database

from app import lessons
from app.db import SessionLocal
from app.models import Concept, LearningEvent
from tests.test_mistake_patterns import new_student

STEP = {"teach": "An idea.", "check": {"prompt": "A question?", "options": ["a", "b"], "answer": "a", "why": "Because."}}


def test_lesson_rules():
    assert lessons.check_lesson([STEP, {**STEP, "check": {**STEP["check"], "prompt": "Another?"}}]) == []
    assert lessons.check_lesson([STEP]) == ["lesson must be a list of 2 to 8 steps"]
    assert "lesson asks the same check question twice" in lessons.check_lesson([STEP, STEP])
    bad = {"teach": "", "check": {"prompt": "Q?", "options": ["a", "a"], "answer": "c", "why": ""}}
    errors = lessons.check_lesson([bad, {**STEP, "colour": "red"}])
    assert any("missing 'teach'" in e for e in errors) and any("same option twice" in e for e in errors)
    assert any("missing 'why'" in e for e in errors) and any("unknown field" in e for e in errors)


def test_the_learner_never_gets_the_answers_ahead():
    shown = lessons.public_lesson([STEP, STEP], 7)
    assert all(set(s["check"]) == {"prompt", "options"} for s in shown)
    assert lessons.public_lesson([STEP, STEP], 7) == shown  # the same order every time
    assert lessons.mark([STEP], 0, " a ") == {"right": True, "answer": "a", "why": "Because."}


def test_a_new_topic_opens_with_its_lesson_then_practice():
    sid = new_student("lena.ls@demo.syniq")
    h = login("lena.ls@demo.syniq")
    with SessionLocal() as db:
        concept = db.scalars(select(Concept).where(Concept.code == "math9.pairs.sum_difference")).first()
        cid, chapter_id, lesson = concept.id, concept.chapter_id, concept.lesson
    assert lesson and len(lesson) >= 3
    first = client.post("/learn/next", json={"chapter_id": chapter_id}, headers=h).json()
    assert first["kind"] == "explain" and first["concept"]["id"] == cid
    assert len(first["lesson"]) == len(lesson) and "answer" not in first["lesson"][0]["check"]
    assert first["explanation"]  # the sum-up after the lesson

    wrong = next(o for o in first["lesson"][0]["check"]["options"] if o != lesson[0]["check"]["answer"])
    r = client.post("/learn/lesson-check", json={"concept_id": cid, "step": 0, "choice": wrong}, headers=h).json()
    assert r["right"] is False and r["answer"] == lesson[0]["check"]["answer"] and r["why"]
    r = client.post("/learn/lesson-check", json={"concept_id": cid, "step": 1, "choice": lesson[1]["check"]["answer"]}, headers=h).json()
    assert r["right"] is True
    assert client.post("/learn/lesson-check", json={"concept_id": cid, "step": 99, "choice": "x"}, headers=h).status_code == 404
    with SessionLocal() as db:
        kinds = db.scalars(select(LearningEvent.kind).where(LearningEvent.student_id == sid)).all()
    assert sorted(kinds) == ["lesson_right", "lesson_wrong"]

    after = client.post("/learn/next", json={"chapter_id": chapter_id, "current_concept_id": cid}, headers=h).json()
    assert after["kind"] == "practice" and after["has_lesson"] is True and "lesson" not in after
    again = client.get(f"/learn/lesson/{cid}", headers=h).json()
    assert again["steps"] == first["lesson"]
