"""Listening, fewer choices, the talk board, sign-language links and strengths."""

from tests.test_api import client, login, math_chapter_id  # first: it points the app at a test database

from sqlalchemy import select

from app import strengths
from app.db import SessionLocal
from app.learning import fewer, public_item
from app.models import Chapter, Concept, HelpRequest, Item, User


def _set_modes(email: str, modes: list[str]):
    who = login(email)
    r = client.put("/me/settings", json={"support_modes": modes}, headers=who)
    assert r.status_code == 200, r.text
    return who


def test_new_modes_are_accepted_and_unknown_refused():
    anu = _set_modes("anu@demo.syniq", ["listen", "fewer_choices", "talk_board", "maths_helper"])
    assert client.put("/me/settings", json={"support_modes": ["mind_reading"]}, headers=anu).status_code == 400
    _set_modes("anu@demo.syniq", [])


def test_fewer_choices_keeps_the_right_answer_and_the_expected_mistake():
    with SessionLocal() as db:
        item = db.scalars(select(Item).where(Item.kind == "mcq")).first()
        pair = fewer(list(item.options), item)
        assert len(pair) == 2 and item.answer in pair
        expected = [o for o in item.options if o in (item.misconceptions or {})]
        if expected:
            assert expected[0] in pair
        assert public_item(item, {"support_modes": ["fewer_choices"]})["options"] == fewer(public_item(item)["options"], item)


def test_listening_turns_typed_sums_into_choices():
    with SessionLocal() as db:
        item = db.scalars(select(Item).where(Item.kind == "numeric")).first()
        assert "choices" not in public_item(item)
        out = public_item(item, {"support_modes": ["listen"]})
        assert item.answer in out["choices"]


def test_talk_board_tells_the_teacher_what_is_needed():
    anu = login("anu@demo.syniq")
    assert client.post("/me/help", json={"need": "shout"}, headers=anu).status_code == 400
    assert client.post("/me/help", json={"need": "break"}, headers=anu).status_code == 200
    assert client.post("/me/help", json={"need": "too_loud"}, headers=anu).status_code == 200
    with SessionLocal() as db:
        anu_id = db.scalars(select(User.id).where(User.email == "anu@demo.syniq")).one()
        open_ = db.scalars(select(HelpRequest).where(HelpRequest.student_id == anu_id, HelpRequest.resolved_at.is_(None))).all()
        assert len(open_) == 1 and open_[0].need == "too_loud"
        class_id = open_[0].class_group_id
    teacher = login("teacher@demo.syniq")
    hands = client.get(f"/teacher/classes/{class_id}/today", headers=teacher).json()["hands"]
    assert any(h["need"] == "too_loud" for h in hands)
    client.delete("/me/help", headers=anu)


def test_sign_videos_are_set_by_staff_and_reach_the_lesson():
    admin = login("admin@demo.syniq")
    anu = login("anu@demo.syniq")
    chapter = math_chapter_id(anu)
    with SessionLocal() as db:
        subject_id = db.get(Chapter, chapter).subject_id
        concepts = db.scalars(select(Concept).where(Concept.chapter_id == chapter)).all()
    step = client.post("/learn/next", json={"chapter_id": chapter}, headers=anu).json()
    concept = next(c for c in concepts if c.id == step["concept"]["id"])
    bad = client.put(f"/admin/signs/{concept.id}", json={"videos": [{"word": "x", "url": "javascript:alert(1)"}]}, headers=admin)
    assert bad.status_code in (400, 422)
    ok = client.put(f"/admin/signs/{concept.id}", json={"videos": [{"word": "square", "url": "https://example.org/isl/square"}]}, headers=admin)
    assert ok.status_code == 200 and ok.json()["videos"][0]["word"] == "square"
    assert client.put(f"/admin/signs/{concept.id}", json={"videos": []}, headers=anu).status_code == 403
    again = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": concept.id}, headers=anu).json()
    if again["concept"]["id"] == concept.id:
        assert again["concept"]["signs"] == [{"word": "square", "url": "https://example.org/isl/square"}]
    listed = client.get(f"/admin/signs/{subject_id}", headers=admin).json()
    assert any(t["videos"] for c in listed for t in c["topics"])
    client.put(f"/admin/signs/{concept.id}", json={"videos": []}, headers=admin)


def test_a_subject_strength_needs_a_clear_lead_over_the_childs_own_record():
    S = strengths.SubjectRecord
    assert strengths.subject_strengths([S("Maths", 40, 34), S("English", 40, 18)])[0].name == "Maths"
    assert strengths.subject_strengths([S("Maths", 40, 30), S("English", 40, 29)]) == []  # no clear lead
    assert strengths.subject_strengths([S("Maths", 40, 34)]) == []  # nothing to compare with
    assert strengths.subject_strengths([S("Maths", 10, 10), S("English", 40, 18)]) == []  # too few answers
    assert strengths.family("Ganita Manjari") == "maths" and strengths.family("Science") == "science"


def test_strengths_from_loved_explore_areas_for_child_and_parent():
    anu = login("anu@demo.syniq")
    assert client.post("/explore/nature.watch/reflect", json={"feeling": "loved", "note": ""}, headers=anu).status_code == 200
    mine = client.get("/me/strengths", headers=anu).json()
    nature = [s for s in mine["strengths"] if s["kind"] == "explore" and s["area"] == "nature"]
    assert nature and nature[0]["next"] and nature[0]["next"][0]["id"].startswith("nature.")
    assert mine["try_new"] and mine["try_new"]["area"] != "nature"
    with SessionLocal() as db:
        anu_id = db.scalars(select(User.id).where(User.email == "anu@demo.syniq")).one()
    parent = login("parent@demo.syniq")
    theirs = client.get(f"/guardian/children/{anu_id}/strengths", headers=parent).json()
    assert any(s["kind"] == "explore" for s in theirs["strengths"])
    assert client.get(f"/guardian/children/{anu_id}/strengths", headers=login("mother@demo.syniq")).status_code == 404
