from tests.test_api import client, login  # first: it points the app at a test database

from app.db import SessionLocal
from app.models import Attempt, AuditLog, Consent, Mastery, Session, User

SHEET = """student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school
Lab Kiran,9 L,Lab Parent,labparent@example.com,,yes,no,yes
Lab Nila,9 L,Lab Other,,,yes,no,no
Lab Zara,9 M,Lab Third,,,yes,no,yes
"""


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def sign_in(login_id, password):
    r = client.post("/auth/login", json={"email": login_id, "password": password})
    assert r.status_code == 200, r.text
    return bearer(r.json()["token"])


def setup_class():
    a = login("admin@demo.syniq")
    rows = client.post("/admin/import", json={"csv": SHEET, "dry_run": False}, headers=a).json()["accounts"]
    t = client.post("/admin/teachers", json={"name": "Lab Teacher", "email": "labteacher@example.com", "classes": ["9 L"]}, headers=a).json()
    teacher = sign_in("labteacher@example.com", t["temporary_password"])
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    return a, teacher, class_id, {r["student"]: r for r in rows}


def practise(h):
    subject = next(x for x in client.get("/subjects", headers=h).json() if x["code"] == "math")
    chapter = client.get(f"/subjects/{subject['id']}/chapters", headers=h).json()[0]["id"]
    first = client.post("/learn/next", json={"chapter_id": chapter}, headers=h).json()
    nxt = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": first["concept"]["id"]}, headers=h).json()
    r = client.post("/learn/attempts", json={"item_id": nxt["item"]["id"], "response": "zzz"}, headers=h)
    assert r.status_code == 200, r.text


def test_lab_period_tools():
    a, teacher, class_id, rows = setup_class()
    kiran = sign_in(rows["Lab Kiran"]["student_login"], rows["Lab Kiran"]["student_password"])
    kiran = bearer(client.post("/me/password", json={"current": rows["Lab Kiran"]["student_password"], "new": "kiran-pass-1"}, headers=kiran).json()["token"])
    practise(kiran)

    today = client.get(f"/teacher/classes/{class_id}/today", headers=teacher).json()
    assert today["class"] == "9 L"
    names = [s["name"] for s in today["students"]]
    assert names == ["Lab Kiran", "Lab Nila"]  # own class only, alphabetical
    k, n = today["students"]
    assert k["first_sign_in_pending"] is False and n["first_sign_in_pending"] is True
    assert "answered_today" in k and "answered_today" not in n  # Nila's family doesn't share progress
    assert k["answered_today"] == 1 and today["today"] == {"active": 1, "answers": 1, "topics": 1}

    # The student hears their own day back.
    mine = client.get("/me/today", headers=kiran).json()
    assert mine["answered"] == k["answered_today"]
    # And where to start next time: the mentor's most useful step.
    assert mine["lessons"] == 0 and mine["next"]["kind"] in ("fix_mistake", "relearn", "review", "carry_on", "start_topic")
    assert client.get("/me/today", headers=teacher).status_code == 403

    # A teacher can give a new password to a student in their class, not to anyone else.
    zara_id = client.get("/admin/people", headers=a).json()
    zara_id = next(s["id"] for c in zara_id["classes"] for s in c["students"] if s["name"] == "Lab Zara")
    assert client.post(f"/teacher/classes/{class_id}/students/{zara_id}/reset-password", headers=teacher).status_code == 404
    r = client.post(f"/teacher/classes/{class_id}/students/{k['id']}/reset-password", headers=teacher).json()
    assert client.get("/me", headers=kiran).status_code == 401  # old session ended
    kiran = sign_in(k["login"], r["temporary_password"])

    # End of the period signs the whole class out.
    zara = sign_in(rows["Lab Zara"]["student_login"], rows["Lab Zara"]["student_password"])
    assert client.post(f"/teacher/classes/{class_id}/end-period", headers=teacher).json()["signed_out"] >= 1
    assert client.get("/me", headers=kiran).status_code == 401
    assert client.get("/me", headers=zara).status_code == 200  # another class is untouched
    assert client.post(f"/teacher/classes/{class_id}/end-period", headers=login("teacher@demo.syniq")).status_code == 404


def test_withdraw_deletes_what_was_learned_and_keeps_the_record():
    a = login("admin@demo.syniq")
    people = client.get("/admin/people", headers=a).json()
    kiran = next(s for c in people["classes"] for s in c["students"] if s["name"] == "Lab Kiran")
    assert client.post(f"/admin/students/{kiran['id']}/withdraw", headers=login("teacher@demo.syniq")).status_code == 403
    assert client.post(f"/admin/students/{kiran['id']}/withdraw", headers=a).json() == {"ok": True, "parent_logins_closed": 1}
    with SessionLocal() as db:
        u = db.get(User, kiran["id"])
        assert u.role == "withdrawn" and u.name == "Withdrawn student" and u.class_group_id is None
        for model in (Attempt, Mastery):
            assert db.query(model).filter_by(student_id=u.id).count() == 0
        assert db.query(Session).filter_by(user_id=u.id).count() == 0
        latest = db.query(Consent).filter_by(student_id=u.id, scope="core_learning").order_by(Consent.id.desc()).first()
        assert latest.granted is False and latest.method == "withdrawn"
        assert db.query(AuditLog).filter_by(action="withdraw_student", subject_student_id=u.id).count() == 1
    assert client.post("/auth/login", json={"email": kiran["login"], "password": "kiran-pass-1"}).status_code == 401
    people = client.get("/admin/people", headers=a).json()
    assert "Lab Kiran" not in str(people)


def test_welcome_card_is_remembered():
    h = login("anu@demo.syniq")
    assert client.put("/me/settings", json={"welcome_seen": True}, headers=h).status_code == 200
    assert client.get("/me", headers=h).json()["settings"]["welcome_seen"] is True


def test_weekly_usage_hides_small_weeks():
    a = login("admin@demo.syniq")
    practise(login("anu@demo.syniq"))
    r = client.get("/admin/usage", headers=a).json()
    assert r["min_group"] == 5 and r["weeks"]
    week = r["weeks"][-1]
    assert week["hidden"] is True and week["active_students"] is None  # only a couple of test students practised
    assert "name" not in str(r).lower()
    assert client.get("/admin/usage", headers=login("teacher@demo.syniq")).status_code == 403


def test_new_student_is_not_called_quiet():
    a = login("admin@demo.syniq")
    sheet = "student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school\nQuiet Q,9 Q,Q Parent,,,yes,no,yes\n"
    row = client.post("/admin/import", json={"csv": sheet, "dry_run": False}, headers=a).json()["accounts"][0]
    h = sign_in(row["student_login"], row["student_password"])
    client.post("/me/password", json={"current": row["student_password"], "new": "quiet-pass-1"}, headers=h)
    class_id = next(c["id"] for c in client.get("/teacher/classes", headers=a).json() if c["name"] == "9 Q")
    student = client.get(f"/teacher/classes/{class_id}/today", headers=a).json()["students"][0]
    assert student["first_sign_in_pending"] is False and student["quiet"] is False
