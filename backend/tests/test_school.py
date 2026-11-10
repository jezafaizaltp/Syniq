from datetime import timedelta

from tests.test_api import client, login  # first: it points the app at a test database

from app.db import SessionLocal
from app.models import AuditLog, Session, User, utcnow

SHEET = """student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school
Sch Asha,9 S,Sch Parent,schparent@example.com,,yes,no,no
Sch Binu,9 S,Sch Parent,schparent@example.com,,yes,no,yes
"""


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def sign_in(login_id, password):
    r = client.post("/auth/login", json={"email": login_id, "password": password})
    assert r.status_code == 200, r.text
    return bearer(r.json()["token"])


def ready(row):
    h = sign_in(row["student_login"], row["student_password"])
    return bearer(client.post("/me/password", json={"current": row["student_password"], "new": "school-pass-1"}, headers=h).json()["token"])


def test_school_name_is_public_and_only_the_name():
    a = login("admin@demo.syniq")
    assert client.put("/admin/school", json={"name": "Test School", "contact": "Office, 0495 000"}, headers=a).json() == {"name": "Test School", "contact": "Office, 0495 000"}
    assert client.get("/school").json() == {"name": "Test School"}
    assert client.put("/admin/school", json={"name": "x"}, headers=login("teacher@demo.syniq")).status_code == 403
    client.put("/admin/school", json={"name": "", "contact": ""}, headers=a)
    assert client.get("/school").json() == {"name": ""}


def test_raised_hands_today_chapter_and_records():
    a = login("admin@demo.syniq")
    rows = {r["student"]: r for r in client.post("/admin/import", json={"csv": SHEET, "dry_run": False}, headers=a).json()["accounts"]}
    t = client.post("/admin/teachers", json={"name": "Sch Teacher", "email": "schteacher@example.com", "classes": ["9 S"]}, headers=a).json()
    teacher = sign_in("schteacher@example.com", t["temporary_password"])
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    asha = ready(rows["Sch Asha"])

    # Today's chapter: the teacher picks from the class's own chapters, the student sees it.
    chapters = client.get(f"/teacher/classes/{class_id}/chapters", headers=teacher).json()
    chosen = next(c for c in chapters if c["subject"] == "Mathematics")
    r = client.put(f"/teacher/classes/{class_id}/today-chapter", json={"chapter_id": chosen["chapter_id"]}, headers=teacher).json()
    assert r["today_chapter"]["title"] == chosen["title"]
    assert client.get("/me/lesson-today", headers=asha).json()["today_chapter"]["chapter_id"] == chosen["chapter_id"]

    # A raised hand reaches the class teacher with the student's name, even without progress sharing.
    assert client.post("/me/help", json={}, headers=asha).json() == {"hand_up": True}
    client.post("/me/help", json={}, headers=asha)  # one open hand, not two
    today = client.get(f"/teacher/classes/{class_id}/today", headers=teacher).json()
    assert [h["name"] for h in today["hands"]] == ["Sch Asha"]
    assert "answered_today" not in today["students"][0]  # Asha's family doesn't share progress
    assert today["today_chapter"]["chapter_id"] == chosen["chapter_id"]
    other = login("teacher@demo.syniq")
    assert client.post(f"/teacher/help/{today['hands'][0]['id']}/done", headers=other).status_code == 404
    client.post(f"/teacher/help/{today['hands'][0]['id']}/done", headers=teacher)
    assert client.get(f"/teacher/classes/{class_id}/today", headers=teacher).json()["hands"] == []
    assert client.get("/me/lesson-today", headers=asha).json()["hand_up"] is False

    # Fix a name and move class.
    people = client.get("/admin/people", headers=a).json()
    asha_id = next(s["id"] for c in people["classes"] for s in c["students"] if s["name"] == "Sch Asha")
    r = client.put(f"/admin/students/{asha_id}", json={"name": "Sch Asha K", "class_name": "9 T"}, headers=a).json()
    assert r == {"id": asha_id, "name": "Sch Asha K", "class": "9 T"}

    # The family's request to see everything held about the child.
    data = client.get(f"/admin/students/{asha_id}/data", headers=a).json()
    assert data["student"]["name"] == "Sch Asha K" and len(data["help_requests"]) == 1 and data["consents"]
    assert client.get(f"/admin/students/{asha_id}/data", headers=teacher).status_code == 403

    # The consent register lists every recorded consent.
    register = client.get("/admin/consents.csv", headers=a).text
    assert register.startswith("date,student,student_login,class,permission,given,how,recorded_by")
    assert "Sch Asha K" in register and "paper_form" in register

    # Withdrawing one sibling keeps the parent; withdrawing the other closes the parent login too.
    binu_id = next(s["id"] for c in people["classes"] for s in c["students"] if s["name"] == "Sch Binu")
    assert client.post(f"/admin/students/{asha_id}/withdraw", headers=a).json()["parent_logins_closed"] == 0
    assert client.post(f"/admin/students/{binu_id}/withdraw", headers=a).json()["parent_logins_closed"] == 1
    with SessionLocal() as db:
        assert db.query(User).filter_by(email="schparent@example.com").count() == 0
        assert db.query(AuditLog).filter_by(action="export_student_data").count() >= 1


def test_ai_usage_and_expired_sign_ins_are_tidied():
    a = login("admin@demo.syniq")
    r = client.get("/admin/ai-usage", headers=a).json()
    assert set(r) == {"outside_ai_on", "provider", "answered_by_outside_ai_today", "saved_unanswered_today", "per_student_daily_limit"}
    with SessionLocal() as db:
        anu = db.query(User).filter_by(email="anu@demo.syniq").one()
        db.add(Session(token="old-token-for-test", user_id=anu.id, created_at=utcnow() - timedelta(days=40), last_seen_at=utcnow() - timedelta(days=40)))
        db.commit()
    login("anu@demo.syniq")
    with SessionLocal() as db:
        assert db.get(Session, "old-token-for-test") is None


def test_audit_log_filters():
    a = login("admin@demo.syniq")
    client.get("/admin/consents.csv", headers=a)
    r = client.get("/admin/audit", params={"action": "export_consent", "since": "2020-01-01"}, headers=a).json()
    assert r["entries"] and all(e["action"].startswith("export_consent") for e in r["entries"])
    assert r["entries"][0]["what"] == "Downloaded the consent register"
    assert client.get("/admin/audit", params={"since": "2999-01-01"}, headers=a).json()["entries"] == []


def test_week_summary_for_parent_and_days_for_student():
    anu = login("anu@demo.syniq")
    r = client.get("/me/days", headers=anu).json()
    assert len(r["days"]) == 28 and set(r["week"]) == {"days", "answered", "topics"}
    parent = login("parent@demo.syniq")
    kids = client.get("/guardian/children", headers=parent).json()
    week = client.get(f"/guardian/children/{kids[0]['id']}/week", headers=parent).json()
    assert set(week) == {"days", "answered", "topics"}
    assert client.get(f"/guardian/children/{kids[0]['id']}/week", headers=login("mother@demo.syniq")).status_code in (403, 404)
