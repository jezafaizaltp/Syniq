"""Rewards: stickers from spotting mistakes, achievements from learning, the parent's switch, tip feedback."""

import inspect
from datetime import timedelta

from sqlalchemy import select

from tests.test_api import client, login  # first: points the app at a fresh test database

from app import learning, rewards
from app.db import SessionLocal
from app.engine import mastery as m
from app.models import Attempt, Item, LearningEvent, User
from tests.test_mistake_patterns import items_of, new_student


def spot_concept_with(n):
    """A topic with at least n questions that carry written mistakes (spot-the-mistake material)."""
    with SessionLocal() as db:
        counts: dict[int, int] = {}
        for i in db.scalars(select(Item).where(Item.status == "approved")).all():
            if any(not learning.same_answer(w, i.answer) for w in (i.misconceptions or {})):
                counts[i.concept_id] = counts.get(i.concept_id, 0) + 1
        return next(c for c, k in sorted(counts.items()) if k >= n)


def spot_once(h, concept_id, right=True):
    r = client.get(f"/learn/spot?concept_id={concept_id}", headers=h)
    if r.status_code != 200:
        return r, None
    p = r.json()
    with SessionLocal() as db:
        item = db.get(Item, p["item_id"])
        choice = item.answer if right else p["their_answer"]
    return r, client.post("/learn/spot", json={"item_id": p["item_id"], "their_answer": p["their_answer"], "choice": choice}, headers=h)


# --- Pure rules -------------------------------------------------------------------------

def test_a_sticker_every_few_stars():
    assert rewards.stickers(0) == {"unlocked": [], "locked": len(rewards.STICKERS), "stars_to_next": 5}
    s = rewards.stickers(12)
    assert s["unlocked"] == rewards.STICKERS[:2] and s["stars_to_next"] == 3
    assert rewards.stickers(10_000)["stars_to_next"] is None


def test_no_reward_is_ever_based_on_time_on_screen():
    assert all(source in {"spot_star", "mastery", "attempt", "attempt_days"} for source in rewards.EARNED_BY.values())
    assert set(rewards.ACHIEVEMENTS) | {"sticker"} == set(rewards.EARNED_BY)
    code = inspect.getsource(rewards)
    for word in ("time_ms", "duration", "seconds", "Session.", "last_seen_at", "login"):
        assert word not in code.split('"""', 2)[2], word  # the module docstring may name what it doesn't do


# --- Spot the mistake ------------------------------------------------------------------------

def test_spot_puzzles_never_repeat_the_same_day_and_star_once():
    new_student("kavya.rw@demo.syniq")
    h = login("kavya.rw@demo.syniq")
    cid = spot_concept_with(2)
    seen = []
    for _ in range(40):
        r, answer = spot_once(h, cid)
        if r.status_code == 404:
            break
        assert r.json()["item_id"] not in seen
        seen.append(r.json()["item_id"])
        assert answer.json()["star_earned"] is True
    assert len(seen) >= 2
    # Answering the same puzzle again earns nothing more.
    with SessionLocal() as db:
        item = db.get(Item, seen[0])
        theirs = next(w for w in item.misconceptions if not learning.same_answer(w, item.answer))
    again = client.post("/learn/spot", json={"item_id": seen[0], "their_answer": theirs, "choice": item.answer}, headers=h).json()
    assert again["star_earned"] is False and again["stars"] == len(seen)


def test_a_spot_answer_needs_a_puzzle_given_today():
    new_student("joel.rw@demo.syniq")
    h = login("joel.rw@demo.syniq")
    cid = spot_concept_with(1)
    with SessionLocal() as db:
        item = next(
            i for i in db.scalars(select(Item).where(Item.concept_id == cid)).all() if any(not learning.same_answer(w, i.answer) for w in i.misconceptions)
        )
        theirs = next(w for w in item.misconceptions if not learning.same_answer(w, item.answer))
    r = client.post("/learn/spot", json={"item_id": item.id, "their_answer": theirs, "choice": item.answer}, headers=h)
    assert r.status_code == 404


def test_missing_a_mistake_is_gentle():
    new_student("nila.rw@demo.syniq")
    h = login("nila.rw@demo.syniq")
    _, answer = spot_once(h, spot_concept_with(1), right=False)
    body = answer.json()
    assert body["correct"] is False and body["careful"] is True and body["star_earned"] is False


def test_fifth_star_brings_a_sticker():
    sid = new_student("dev.rw@demo.syniq")
    with SessionLocal() as db:
        for _ in range(4):
            db.add(LearningEvent(student_id=sid, kind="spot_star", created_at=learning.utcnow() - timedelta(days=2)))
        db.commit()
    h = login("dev.rw@demo.syniq")
    _, answer = spot_once(h, spot_concept_with(1))
    assert answer.json()["new_sticker"] == rewards.STICKERS[0]
    view = client.get("/me/rewards", headers=h).json()
    assert view["on"] and view["stickers"]["unlocked"] == [rewards.STICKERS[0]]


# --- Achievements -----------------------------------------------------------------------------

def test_achievements_come_from_learning_moments():
    sid = new_student("ravi.rw@demo.syniq")
    cid, items = items_of("math9.square_of_sum")
    hard = next(i for i in items if i.difficulty >= m.HARD and i.status == "approved")
    with SessionLocal() as db:
        student = db.get(User, sid)
        assert rewards.achievements(db, sid) == []
        learning.record_attempt(db, student, hard, hard.answer, 0, 5000, None)
        got = {a["id"] for a in rewards.achievements(db, sid)}
        assert "first_hard_right" in got
        # Back after a break: answers 10 days apart.
        old = db.scalars(select(Attempt).where(Attempt.student_id == sid)).first()
        db.add(Attempt(student_id=sid, item_id=old.item_id, concept_id=old.concept_id, response="x", correct=False,
                       created_at=learning.utcnow() - timedelta(days=10)))
        db.commit()
        assert "back_after_break" in {a["id"] for a in rewards.achievements(db, sid)}
    # The parent sees what is new this week, in words.
    parent = login("parent@demo.syniq")
    week = client.get(f"/guardian/children/{sid}/week", headers=parent).json()
    assert "first_hard_right" in week["achievements"]


def test_parent_switch_and_school_default():
    sid = new_student("asha.rw@demo.syniq")
    h = login("asha.rw@demo.syniq")
    parent = login("parent@demo.syniq")
    admin = login("admin@demo.syniq")
    assert next(c for c in client.get("/guardian/children", headers=parent).json() if c["id"] == sid)["rewards_on"] is True

    assert client.put(f"/guardian/children/{sid}/rewards", json={"on": False}, headers=parent).status_code == 200
    assert client.get("/me/rewards", headers=h).json() == {"on": False}
    _, answer = spot_once(h, spot_concept_with(1))
    assert answer.json()["star_earned"] is False and answer.json()["stars"] is None

    # The school's default applies until a parent chooses; the parent's choice wins.
    school = client.get("/admin/school", headers=admin).json()
    assert client.put("/admin/school", json={**school, "rewards": "off"}, headers=admin).status_code == 200
    client.put(f"/guardian/children/{sid}/rewards", json={"on": True}, headers=parent)
    assert client.get("/me/rewards", headers=h).json()["on"] is True
    other = new_student("binu.rw@demo.syniq")
    assert client.get("/me/rewards", headers=login("binu.rw@demo.syniq")).json() == {"on": False}
    client.put("/admin/school", json={**school, "rewards": "on"}, headers=admin)
    assert other


def test_rewards_are_in_the_data_download_and_hidden_from_teachers():
    sid = new_student("tara.rw@demo.syniq")
    admin = login("admin@demo.syniq")
    data = client.get(f"/admin/students/{sid}/data", headers=admin).json()
    assert data["rewards"]["on"] is True and data["rewards"]["stars"] == 0
    teacher = login("teacher@demo.syniq")
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    for path in ("overview", "today", "mistakes", "hard-trouble"):
        text = client.get(f"/teacher/classes/{class_id}/{path}", headers=teacher).text
        assert "sticker" not in text and "achievement" not in text and '"stars"' not in text, path


# --- Tip feedback, teacher and admin pages ------------------------------------------------------

def test_tip_feedback_is_counted_per_tip():
    sid = new_student("sara.rw@demo.syniq")
    h = login("sara.rw@demo.syniq")
    with SessionLocal() as db:
        item = next(i for i in db.scalars(select(Item).where(Item.status == "approved")).all() if i.misconceptions)
        wrong, tag = next(iter(item.misconceptions.items()))
    body = {"item_id": item.id, "tag": tag, "helpful": False}
    assert client.post("/learn/tip-feedback", json=body, headers=h).status_code == 404  # not answered yet
    r = client.post("/learn/attempts", json={"item_id": item.id, "response": wrong, "hints_used": 0}, headers=h)
    assert r.status_code == 200
    assert client.post("/learn/tip-feedback", json=body, headers=h).status_code == 200
    assert client.post("/learn/tip-feedback", json=body, headers=h).status_code == 200  # counted once
    rows = client.get("/admin/tip-feedback", headers=login("admin@demo.syniq")).json()
    row = next(r for r in rows if r["tag"] == tag)
    assert row["no"] == 1 and "sara" not in str(rows).lower()
    assert sid


def test_teacher_sheets_and_admin_pages():
    teacher = login("teacher@demo.syniq")
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    chapters = client.get(f"/teacher/classes/{class_id}/chapters", headers=teacher).json()
    sheet = client.get(f"/teacher/classes/{class_id}/chapter-progress?chapter_id={chapters[0]['chapter_id']}", headers=teacher).json()
    assert sheet["topics"] and set(sheet["topics"][0]) == {"topic", "secure", "getting_there", "learning", "not_started"}
    assert client.get(f"/teacher/classes/{class_id}/hard-trouble", headers=teacher).status_code == 200
    admin = login("admin@demo.syniq")
    health = client.get("/admin/health", headers=admin).json()
    assert {"backup_ok", "disk_ok", "disk_free_gb"} <= set(health)
    coverage = client.get("/admin/coverage", headers=admin).json()
    assert coverage and all(r["questions"] >= 0 for r in coverage)
    assert client.get("/admin/coverage", headers=teacher).status_code == 403
