import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Item  # noqa: E402
from app.seed import DEMO_PASSWORD, seed  # noqa: E402

with SessionLocal() as _db:
    seed(_db)

client = TestClient(app)


def login(email):
    r = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def anu():
    return login("anu@demo.syniq")


def math_chapter_id(headers):
    subjects = client.get("/subjects", headers=headers).json()
    math = next(s for s in subjects if s["code"] == "math")
    return client.get(f"/subjects/{math['id']}/chapters", headers=headers).json()[0]["id"]


def test_wrong_password_rejected():
    r = client.post("/auth/login", json={"email": "anu@demo.syniq", "password": "nope"})
    assert r.status_code == 401


def test_all_nine_subjects_present(anu):
    assert len(client.get("/subjects", headers=anu).json()) == 9


def test_no_learning_without_guardian_consent():
    fathima = login("fathima@demo.syniq")
    r = client.post("/learn/next", json={"chapter_id": math_chapter_id(fathima)}, headers=fathima)
    assert r.status_code == 403


def test_learning_loop_and_no_answer_leak(anu):
    chapter = math_chapter_id(anu)
    first = client.post("/learn/next", json={"chapter_id": chapter}, headers=anu).json()
    assert first["kind"] == "explain" and first["explanation"]["body"]

    nxt = client.post(
        "/learn/next", json={"chapter_id": chapter, "current_concept_id": first["concept"]["id"]}, headers=anu
    ).json()
    assert nxt["kind"] == "practice"
    item = nxt["item"]
    assert "answer" not in item and "hints" not in item

    hint = client.get(f"/items/{item['id']}/hints/1", headers=anu).json()
    assert hint["hint"]

    wrong = client.post("/learn/attempts", json={"item_id": item["id"], "response": "zzz", "hints_used": 1}, headers=anu).json()
    assert wrong["correct"] is False and wrong["solution"]

    why = client.get(f"/me/why/{nxt['decision_id']}", headers=anu).json()
    assert why["rule"] == "R6_practice"


def test_draft_items_never_served(anu):
    with SessionLocal() as db:
        draft = db.query(Item).filter(Item.status == "draft").first()
    r = client.get(f"/items/{draft.id}/hints/1", headers=anu)
    assert r.status_code == 404
    r = client.post("/learn/attempts", json={"item_id": draft.id, "response": "1"}, headers=anu)
    assert r.status_code == 404


def test_settings_validated(anu):
    ok = client.put("/me/settings", json={"font_scale": 1.4, "dyslexia_font": True}, headers=anu)
    assert ok.status_code == 200 and ok.json()["font_scale"] == 1.4
    bad = client.put("/me/settings", json={"is_admin": True}, headers=anu)
    assert bad.status_code == 400


def test_teacher_sees_counts_not_rankings():
    t = login("teacher@demo.syniq")
    classes = client.get("/teacher/classes", headers=t).json()
    overview = client.get(f"/teacher/classes/{classes[0]['id']}/overview", headers=t).json()
    # Fathima has not consented to school sharing, so only two students are counted.
    assert overview["students"] == 2
    first = overview["concepts"][0]
    assert set(first["counts"]) == {"not_started", "learning", "getting_there", "secure"}
    assert "students" not in first


def test_student_cannot_use_teacher_endpoints(anu):
    assert client.get("/teacher/review-queue", headers=anu).status_code == 403


def test_teacher_approves_draft():
    t = login("teacher@demo.syniq")
    queue = client.get("/teacher/review-queue", headers=t).json()
    item_id = queue["items"][0]["id"]
    r = client.post(f"/teacher/items/{item_id}/review", json={"decision": "approve"}, headers=t)
    assert r.json()["status"] == "approved"


def test_guardian_consent_unlocks_learning():
    g = login("parent@demo.syniq")
    kids = client.get("/guardian/children", headers=g).json()
    fathima = next(k for k in kids if k["name"] == "Fathima")
    assert fathima["consent"]["core_learning"] is False
    client.post(f"/guardian/children/{fathima['id']}/consent", json={"scope": "core_learning", "granted": True}, headers=g)
    f = login("fathima@demo.syniq")
    r = client.post("/learn/next", json={"chapter_id": math_chapter_id(f)}, headers=f)
    assert r.status_code == 200


def test_checkin_not_stored_without_mood_consent():
    f = login("fathima@demo.syniq")
    r = client.post("/checkins", json={"mood": "low"}, headers=f).json()
    assert r["stored"] is False


def test_guardian_cannot_see_unlinked_child():
    g = login("parent@demo.syniq")
    assert client.get("/guardian/children/99999/progress", headers=g).status_code == 404


def test_new_explanation_is_followed_by_practice_not_another_explanation():
    r = login("rahul@demo.syniq")
    chapter = math_chapter_id(r)
    a = client.post("/learn/next", json={"chapter_id": chapter}, headers=r).json()
    cur = a["concept"]["id"]
    for _ in range(2):
        a = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": cur}, headers=r).json()
        assert a["kind"] == "practice"
        client.post("/learn/attempts", json={"item_id": a["item"]["id"], "response": "wrong"}, headers=r)
    a = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": cur}, headers=r).json()
    assert a["kind"] == "explain" and a["offer_support"] and a["explanation"]["style"] != "text"
    a = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": cur}, headers=r).json()
    assert a["kind"] == "practice"
