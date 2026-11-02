from tests.test_api import client, login  # first: it points the app at a test database

from app.auth import hash_password
from app.db import SessionLocal
from app.seed import DEMO_PASSWORD
from app.models import Attempt, Item, Mastery, SubjectCheck, User


def subject_id(headers, code="math"):
    return next(s["id"] for s in client.get("/subjects", headers=headers).json() if s["code"] == code)


def answer_all(headers, check, right: bool):
    with SessionLocal() as db:
        while check["item"]:
            item = db.get(Item, check["item"]["id"])
            r = client.post(
                f"/checks/{check['id']}/answer",
                json={"item_id": item.id, "response": item.answer if right else ""},
                headers=headers,
            )
            assert r.status_code == 200, r.text
            check = r.json()
    return check


def test_starting_check_seeds_where_the_engine_begins_without_a_score():
    rahul = login("rahul@demo.syniq")
    sid = subject_id(rahul, "phy")
    listed = next(c for c in client.get("/checks", headers=rahul).json() if c["subject_id"] == sid)
    assert listed["start"] == "not_started"

    check = client.post("/checks", json={"subject_id": sid}, headers=rahul).json()
    assert 1 <= check["total"] <= 12
    assert "answer" not in check["item"] and "hints" not in check["item"]
    # Asking again carries on the same check.
    assert client.post("/checks", json={"subject_id": sid}, headers=rahul).json()["id"] == check["id"]

    with SessionLocal() as db:
        user = db.query(User).filter_by(email="rahul@demo.syniq").one()
        attempts_before = db.query(Attempt).filter_by(student_id=user.id).count()

    done = answer_all(rahul, check, right=True)
    assert done["status"] == "done"
    assert len(done["summary"]["known"]) == done["total"] and done["summary"]["start_with"] == []
    assert "score" not in done and "average_right" not in done

    with SessionLocal() as db:
        # Never counted as practice, so it can't switch support modes on.
        assert db.query(Attempt).filter_by(student_id=user.id).count() == attempts_before
        check_row = db.get(SubjectCheck, done["id"])
        items = db.query(Item).filter(Item.id.in_(check_row.item_ids)).all()
        rows = db.query(Mastery).filter(Mastery.student_id == user.id, Mastery.concept_id.in_({i.concept_id for i in items})).all()
        assert rows and all(r.p_known > 0.2 and r.p_known < 0.95 and r.attempts == 0 for r in rows)


def test_starting_check_is_optional_and_end_check_needs_an_open_round():
    anu = login("anu@demo.syniq")
    sid = subject_id(anu, "chem")
    assert client.post("/checks/skip-start", json={"subject_id": sid}, headers=anu).json()["status"] == "skipped"
    listed = next(c for c in client.get("/checks", headers=anu).json() if c["subject_id"] == sid)
    assert listed["start"] == "skipped"

    r = client.post("/checks", json={"subject_id": sid, "kind": "end"}, headers=anu)
    assert r.status_code == 400

    admin = login("admin@demo.syniq")
    assert client.post("/admin/check-rounds", json={"kind": "end"}, headers=anu).status_code == 403
    rnd = client.post("/admin/check-rounds", json={"kind": "end"}, headers=admin).json()
    assert client.post("/admin/check-rounds", json={"kind": "end"}, headers=admin).status_code == 400

    end = client.post("/checks", json={"subject_id": sid, "kind": "end"}, headers=anu).json()
    assert end["kind"] == "end"
    answer_all(anu, end, right=False)

    report = client.get("/admin/checks", headers=admin).json()
    chem = next(s for s in report["subjects"] if s["subject"] == "Chemistry")
    entry = next(c for c in chem["checks"] if c["round_id"] == rnd["id"])
    # One student: too few to show a result.
    assert entry["students"] == 1 and entry["average_right"] is None

    client.post(f"/admin/check-rounds/{rnd['id']}/close", headers=admin)
    assert all(not r["rounds"] for r in client.get("/checks", headers=anu).json())


def test_no_checks_or_space_without_consent():
    # Other tests give the demo students consent, so make a student who has none.
    with SessionLocal() as db:
        db.add(User(name="New", email="new-no-consent@demo.syniq", password_hash=hash_password(DEMO_PASSWORD), role="student", settings={}))
        db.commit()
    new = login("new-no-consent@demo.syniq")
    assert client.get("/checks", headers=new).status_code == 403
    assert client.get("/me/overview", headers=new).status_code == 403


def test_overview_goals_and_notes_are_private():
    anu = login("anu@demo.syniq")
    overview = client.get("/me/overview", headers=anu).json()
    assert {"subjects", "review_due"} <= set(overview)

    g = client.post("/me/goals", json={"text": "  Finish chapter 2 of Maths ", "due_on": "2026-12-01"}, headers=anu).json()
    assert g["text"] == "Finish chapter 2 of Maths" and not g["done"]
    assert client.post("/me/goals", json={"text": "x", "due_on": "next week"}, headers=anu).status_code == 422
    assert client.put(f"/me/goals/{g['id']}", json={"done": True}, headers=anu).json()["done"] is True

    with SessionLocal() as db:
        concept_id = db.query(Item).filter_by(status="approved").first().concept_id
    n = client.post("/me/notes", json={"body": "(a+b)² has a middle term 2ab", "concept_id": concept_id}, headers=anu).json()
    assert n["topic"]
    assert [x["id"] for x in client.get(f"/me/notes?concept_id={concept_id}", headers=anu).json()] == [n["id"]]
    assert client.put(f"/me/notes/{n['id']}", json={"body": "edited"}, headers=anu).json()["body"] == "edited"

    # Nobody else can read or change them: not another student, not a parent or teacher.
    rahul = login("rahul@demo.syniq")
    assert client.get("/me/notes", headers=rahul).json() == []
    assert client.delete(f"/me/notes/{n['id']}", headers=rahul).status_code == 404
    assert client.put(f"/me/goals/{g['id']}", json={"done": False}, headers=rahul).status_code == 404
    for email in ("parent@demo.syniq", "teacher@demo.syniq"):
        assert client.get("/me/notes", headers=login(email)).status_code == 403

    assert client.delete(f"/me/notes/{n['id']}", headers=anu).status_code == 204
    assert client.delete(f"/me/goals/{g['id']}", headers=anu).status_code == 204
    assert client.get("/me/goals", headers=anu).json() == []
