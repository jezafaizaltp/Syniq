"""Lessons that explain each idea in more than one way, ordered for each learner, and the mentor's plan."""

from sqlalchemy import select

from tests.test_api import client, login  # first: points the app at a fresh test database

from app import lessons, mentor
from app.db import SessionLocal
from app.engine import methods
from app.models import Concept, LearningEvent, Mastery, User
from tests.test_mistake_patterns import new_student

CHECK = {"prompt": "A question?", "options": ["a", "b", "c"], "answer": "a", "why": "Because."}
PIC = {"kind": "bars", "alt": "Two bars, one twice as tall as the other", "bars": [{"label": "x", "value": 1}, {"label": "y", "value": 2}]}
STEP = {
    "teach": "An idea, said in words.",
    "check": CHECK,
    "ways": [
        {"style": "real_world", "teach": "The same idea with a shop in Calicut, where it shows up every day."},
        {"style": "step_by_step", "teach": "First do this. Then do that. Last, check it the other way round."},
    ],
}


def test_ways_are_checked():
    two = [STEP, {**STEP, "check": {**CHECK, "prompt": "Another?"}}]
    assert lessons.check_lesson(two) == []
    bad = {**STEP, "ways": [{"style": "text", "teach": "x" * 50}, {"style": "colour", "teach": "short"}, {"style": "visual", "teach": "y" * 50}]}
    errors = lessons.check_lesson([bad, two[1]])
    assert any("style text is used twice" in e for e in errors)
    assert any("style must be one of" in e for e in errors) and any("40 characters" in e for e in errors)
    assert any("a visual way needs a picture" in e for e in errors)
    assert lessons.check_lesson([{**STEP, "ways": []}, two[1]]) == ["lesson step 1: ways must be a list of 1 to 3"]


def test_the_way_most_likely_to_work_comes_first():
    shown = lessons.public_lesson([STEP, STEP], 7, ["step_by_step", "real_world", "text", "visual"])
    assert [w["style"] for w in shown[0]["ways"]] == ["step_by_step", "real_world", "text"]
    assert shown[0]["teach"] == shown[0]["ways"][0]["teach"]  # older apps get the first way
    assert [w["style"] for w in lessons.public_lesson([STEP, STEP], 7)[0]["ways"]] == ["text", "real_world", "step_by_step"]
    # A learner whose answers went well after real-life examples gets those first.
    stats = {"real_world": {"after_correct": 6, "after_wrong": 0, "expected": 3}, "text": {"after_correct": 1, "after_wrong": 4, "expected": 2.5}}
    assert methods.ranked(stats, None)[0] == "real_world" and methods.ranked(stats, None)[-1] == "text"
    assert methods.ranked(stats, None, preferred="visual")[0] == "visual"


def _with_ways(cid):
    with SessionLocal() as db:
        c = db.get(Concept, cid)
        before = c.lesson
        c.lesson = [{**s, "ways": STEP["ways"]} if n < 2 else s for n, s in enumerate(c.lesson)]
        db.commit()
        return before


def test_wrong_check_gets_another_way_and_one_more_try_and_credits_what_worked():
    sid = new_student("ravi.ways@demo.syniq")
    h = login("ravi.ways@demo.syniq")
    with SessionLocal() as db:
        concept = db.scalars(select(Concept).where(Concept.code == "math9.pairs.sum_difference")).first()
        cid, chapter_id = concept.id, concept.chapter_id
    before = _with_ways(cid)
    try:
        first = client.post("/learn/next", json={"chapter_id": chapter_id}, headers=h).json()
        step = first["lesson"][0]
        assert len(step["ways"]) == len(STEP["ways"]) + 1
        answer = before[0]["check"]["answer"]
        wrong = next(o for o in step["check"]["options"] if o != answer)
        shown = step["ways"][0]["style"]
        r = client.post("/learn/lesson-check", json={"concept_id": cid, "step": 0, "choice": wrong, "style": shown, "can_retry": True}, headers=h).json()
        assert r == {"right": False, "retry": True}  # no answer yet: another way first
        other = step["ways"][1]["style"]
        r = client.post("/learn/lesson-check", json={"concept_id": cid, "step": 0, "choice": answer, "style": other, "attempt": 2}, headers=h).json()
        assert r["right"] is True and r["why"]
        # Right first time after asking for another way counts for that way too.
        answer1 = before[1]["check"]["answer"]
        r = client.post("/learn/lesson-check", json={"concept_id": cid, "step": 1, "choice": answer1, "style": other, "switched": True}, headers=h).json()
        assert r["right"] is True
        # A style the step doesn't have is not credited.
        client.post("/learn/lesson-check", json={"concept_id": cid, "step": 2, "choice": "x", "style": "visual"}, headers=h)
        with SessionLocal() as db:
            stats = db.scalars(select(Mastery.format_stats).where(Mastery.student_id == sid, Mastery.concept_id == cid)).first()
        assert stats[shown]["felt_no"] == 1 and stats[other]["felt_yes"] == 2 and "visual" not in stats
        # The next time this learner opens the lesson, the way that worked comes first.
        again = client.get(f"/learn/lesson/{cid}", headers=h).json()
        assert again["steps"][0]["ways"][0]["style"] == other

        assert client.post("/learn/lesson-done", json={"concept_id": cid, "steps": 4, "first_time": 3}, headers=h).json() == {"ok": True}
        with SessionLocal() as db:
            done = db.scalars(select(LearningEvent.detail).where(LearningEvent.student_id == sid, LearningEvent.kind == "lesson_done")).all()
        assert done == [f"{cid}:3/4:taught"]
        week = client.get("/me/mentor", headers=h).json()["week"]
        assert week["lessons"] == 1
    finally:
        with SessionLocal() as db:
            db.get(Concept, cid).lesson = before
            db.commit()


def test_mentor_starts_a_new_learner_and_then_points_the_way():
    new_student("mira.mentor@demo.syniq")
    h = login("mira.mentor@demo.syniq")
    plan = client.get("/me/mentor", headers=h).json()
    assert plan["steps"] == [{"kind": "first_lesson"}] and plan["part_of_day"] in ("morning", "afternoon", "evening")
    assert plan["week"]["answered"] == 0 and plan["week"]["helped_most"] is None

    with SessionLocal() as db:
        concept = db.scalars(select(Concept).where(Concept.code == "math9.pairs.sum_difference")).first()
        chapter_id = concept.chapter_id
    step = client.post("/learn/next", json={"chapter_id": chapter_id}, headers=h).json()
    # Taught the lesson, nothing answered yet: carry on with that topic.
    first = client.get("/me/mentor", headers=h).json()["steps"]
    assert first[0]["kind"] == "carry_on" and first[0]["chapter_id"] == chapter_id
    step = client.post("/learn/next", json={"chapter_id": chapter_id, "current_concept_id": step["concept"]["id"]}, headers=h).json()
    item = step["item"]
    for _ in range(3):
        assert client.post("/learn/attempts", json={"item_id": item["id"], "response": "definitely not it"}, headers=h).status_code == 200
    plan = client.get("/me/mentor", headers=h).json()
    kinds = [s["kind"] for s in plan["steps"]]
    assert kinds[0] == "relearn" and "first_lesson" not in kinds
    relearn = next(s for s in plan["steps"] if s["kind"] == "relearn")
    assert relearn["chapter_id"] == chapter_id and relearn["topic"] and relearn["has_lesson"] is True
    assert plan["week"]["answered"] == 3 and plan["week"]["days"] == 1
    assert len(plan["steps"]) <= mentor.MAX_STEPS
    with SessionLocal() as db:
        assert db.scalars(select(User).where(User.email == "mira.mentor@demo.syniq")).first()


def test_part_of_day_is_india_time():
    from datetime import datetime

    assert mentor.part_of_day(datetime(2026, 11, 12, 3, 0)) == "morning"  # 8:30 in India
    assert mentor.part_of_day(datetime(2026, 11, 12, 9, 0)) == "afternoon"  # 14:30
    assert mentor.part_of_day(datetime(2026, 11, 12, 14, 0)) == "evening"  # 19:30


def test_lesson_starts_with_questions_only_when_the_learner_already_knows_some():
    from app import learning

    sid = new_student("meera.checkfirst@demo.syniq")
    with SessionLocal() as db:
        student = db.get(User, sid)
        cid = db.scalars(select(Concept.id).where(Concept.code == "math9.pairs.sum_difference")).first()
        assert learning.lesson_check_first(db, student, cid) is None  # new topic: teach first
        row = learning.get_mastery(db, sid, cid)
        row.p_known = 0.52  # one right answer in the start check
        db.commit()
        assert learning.lesson_check_first(db, student, cid) == "knows_some"
        row.wrong_streak = 2  # stuck right now: the teaching, not a quiz
        db.commit()
        assert learning.lesson_check_first(db, student, cid) is None
        row.wrong_streak = 0
        db.add(LearningEvent(student_id=sid, kind="lesson_done", detail=f"{cid}:3/4:taught"))
        db.commit()
        assert learning.lesson_check_first(db, student, cid) == "seen_before"


def test_teacher_sees_lesson_ideas_the_class_found_hard_and_what_helped():
    with SessionLocal() as db:
        concept = db.scalars(select(Concept).where(Concept.code.like("phy9.%"), Concept.lesson.is_not(None)).order_by(Concept.id)).first()
        cid, check = concept.id, concept.lesson[1]["check"]
        first_way, second_way = [w["style"] for w in lessons.public_lesson(concept.lesson, cid)[1]["ways"]][:2]
    wrong = next(o for o in check["options"] if o != check["answer"])
    for n, first_right in enumerate([False, False, True]):
        email = f"class{n}.idea@demo.syniq"
        new_student(email)
        h = login(email)
        body = {"concept_id": cid, "step": 1, "style": first_way, "attempt": 1, "can_retry": True}
        if first_right:
            client.post("/learn/lesson-check", json={**body, "choice": check["answer"]}, headers=h)
            continue
        assert client.post("/learn/lesson-check", json={**body, "choice": wrong}, headers=h).json()["retry"] is True
        client.post("/learn/lesson-check", json={**body, "choice": check["answer"], "style": second_way, "attempt": 2}, headers=h)
    teacher = login("teacher@demo.syniq")
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    rows = client.get(f"/teacher/classes/{class_id}/lesson-trouble", headers=teacher).json()
    row = next(r for r in rows if r["concept_id"] == cid and r["idea"] == 2)
    assert row["tried"] == 3 and row["missed_first"] == 2 and row["helped"] == second_way
    assert row["check"] == check["prompt"] and "Class" not in str(row)  # counts only, no names


def test_mentor_reminds_the_learner_of_their_own_goal():
    new_student("gita.goal@demo.syniq")
    h = login("gita.goal@demo.syniq")
    assert client.get("/me/mentor", headers=h).json()["goal"] is None
    client.post("/me/goals", json={"text": "Finish Pairs of Equations", "due_on": None}, headers=h)
    client.post("/me/goals", json={"text": "Revise motion", "due_on": "2026-12-01"}, headers=h)
    assert client.get("/me/mentor", headers=h).json()["goal"] == {"text": "Revise motion", "due_on": "2026-12-01"}  # due first
