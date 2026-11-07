"""Hands-on activities: every Class 6 Maths and Science topic has one, each can be built and solved."""

from tests.test_api import client  # noqa: F401  (must load first: sets up the test database)

from sqlalchemy import select

from app import content_packs
from app.activities import PATTERN_RULES, check_activity, fraction_matches
from app.auth import hash_password
from app.db import SessionLocal
from app.models import Chapter, Concept, Consent, Subject, User


def _class6_packs():
    return [p for path, p in content_packs.read_packs() if p["subject"] in ("cbse6-math", "cbse6-sci")]


def test_every_class6_maths_and_science_topic_has_a_working_activity():
    packs = _class6_packs()
    concepts = [c for p in packs for c in p["concepts"]]
    assert len(concepts) == 44
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def test_activities_use_many_kinds_not_one():
    kinds = {c["activity"]["type"] for p in _class6_packs() for c in p["concepts"]}
    assert len(kinds) >= 10


def test_bad_activities_are_caught_in_plain_words():
    assert check_activity({"type": "spin", "prompt": "x"})
    # A target between the steps can never be reached with the buttons.
    assert any("on a step" in e for e in check_activity(
        {"type": "number_line", "prompt": "p", "min": 0, "max": 10, "step": 2, "goals": [{"prompt": "g", "target": 3}]}))
    # No rectangle with sides up to 10 has area 7 and perimeter 10.
    assert any("can't be made" in e for e in check_activity(
        {"type": "rectangle", "prompt": "p", "goals": [{"prompt": "g", "area": 7, "perimeter": 10}]}))
    assert any("bin" in e for e in check_activity(
        {"type": "sort", "prompt": "p", "bins": ["A", "B"], "items": [{"label": str(i), "bin": "C"} for i in range(4)]}))
    assert any("count" in e for e in check_activity(
        {"type": "pattern", "prompt": "p", "rule": "square", "goals": [{"prompt": "g", "count": 20}]}))
    assert any("goals" in e for e in check_activity({"type": "order", "prompt": "p", "steps": ["a", "b", "c"], "goals": []}))


def test_every_goal_can_be_reached():
    for p in _class6_packs():
        for c in p["concepts"]:
            a = c["activity"]
            for g in a.get("goals", []):
                if a["type"] == "pattern":
                    assert g["count"] in [PATTERN_RULES[a["rule"]](n) for n in range(1, a.get("max_step", 8) + 1)]
                if a["type"] == "fraction_bar":
                    assert fraction_matches(g["num"], g["den"], g)
                if a["type"] == "scale" and "zone" in g:
                    assert g["zone"] in {z["label"] for z in a["zones"]}


def test_lesson_offers_the_activity_with_the_topic():
    with SessionLocal() as db:
        kid = User(name="Isha", email="isha@test.syniq", password_hash=hash_password("a-long-password"),
                   role="student", settings={"board": "cbse", "grade": 6, "support_modes": ["calm"]})
        db.add(kid)
        db.flush()
        parent = db.scalars(select(User).where(User.role == "guardian")).first()
        db.add(Consent(student_id=kid.id, guardian_id=parent.id, scope="core_learning", granted=True, method="school_form"))
        subject = db.scalars(select(Subject).where(Subject.code == "cbse6-math")).first()
        chapter = db.scalars(select(Chapter).where(Chapter.subject_id == subject.id, Chapter.number == 7)).first()
        db.commit()
        chapter_id = chapter.id
    token = client.post("/auth/login", json={"email": "isha@test.syniq", "password": "a-long-password"}).json()["token"]
    me = {"Authorization": f"Bearer {token}"}
    step = client.post("/learn/next", json={"chapter_id": chapter_id}, headers=me).json()
    assert step["concept"] and step["activity"]["type"] == "fraction_bar"
    assert client.post("/learn/events", json={"kind": "activity"}, headers=me).status_code == 200
    assert client.post("/learn/events", json={"kind": "score"}, headers=me).status_code == 422


def test_topics_without_an_activity_send_none():
    with SessionLocal() as db:
        c = db.scalars(select(Concept).where(Concept.code.like("cbse12m.%"))).first()
        assert c.activity is None
