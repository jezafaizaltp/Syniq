from datetime import timedelta

from app import auth
from app.bootstrap import bootstrap
from app.db import SessionLocal
from app.models import Consent, Session, Subject, User
from tests.test_api import client, login

SHEET = """student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school
Meera Nair,9 B,Divya Nair,divya@example.com,,yes,no,yes
Arjun Nair,9 B,Divya Nair,divya@example.com,,yes,no,yes
Sam Thomas,9 C,Joseph Thomas,,98470 11111,no,no,no
"""


def admin():
    return login("admin@demo.syniq")


def test_dry_run_checks_without_writing():
    a = admin()
    bad = SHEET + "Nobody,,Someone,not-an-email,,maybe,no,no\n"
    r = client.post("/admin/import", json={"csv": bad, "dry_run": False}, headers=a).json()
    assert r["ok"] is False and r["errors"][0]["row"] == 5
    assert any("class is empty" in p for p in r["errors"][0]["problems"])
    with SessionLocal() as db:
        assert db.query(User).filter_by(name="Meera Nair").count() == 0

    r = client.post("/admin/import", json={"csv": SHEET}, headers=a).json()
    assert r == {"ok": True, "errors": [], "students": 3, "classes": ["9 B", "9 C"], "without_learning_consent": 1, "dry_run": True}


def test_import_creates_accounts_consent_and_sibling_links():
    a = admin()
    r = client.post("/admin/import", json={"csv": SHEET, "dry_run": False}, headers=a).json()
    rows = r["accounts"]
    assert len(rows) == 3
    meera, arjun, sam = rows
    assert meera["guardian_login"] == arjun["guardian_login"] == "divya@example.com"
    assert meera["guardian_password"] != arjun["guardian_password"]  # shown once only
    assert sam["guardian_login"].startswith("parent-joseph")

    # A student signs in with the temporary password and must change it first.
    h = {"Authorization": "Bearer " + client.post("/auth/login", json={"email": meera["student_login"], "password": meera["student_password"]}).json()["token"]}
    assert client.get("/me", headers=h).json()["must_change_password"] is True
    r = client.post("/me/password", json={"current": meera["student_password"], "new": "my-new-pass"}, headers=h)
    assert r.status_code == 200
    assert client.get("/me", headers=h).status_code == 401  # old session ended
    h = {"Authorization": "Bearer " + r.json()["token"]}
    assert client.get("/me", headers=h).json()["must_change_password"] is False

    # Paper consent recorded for both siblings under one parent.
    with SessionLocal() as db:
        parent = db.query(User).filter_by(email="divya@example.com").one()
        consents = db.query(Consent).filter_by(guardian_id=parent.id, scope="core_learning").all()
        assert len(consents) == 2 and all(c.granted and c.method == "paper_form" for c in consents)

    people = client.get("/admin/people", headers=a).json()
    nine_c = next(c for c in people["classes"] if c["name"] == "9 C")
    assert nine_c["students"][0]["consent"]["core_learning"] is False
    assert "98470" not in str(people)  # phone numbers are never saved


def test_reset_password_and_add_teacher():
    a = admin()
    people = client.get("/admin/people", headers=a).json()
    student = next(s for c in people["classes"] for s in c["students"] if s["name"] == "Sam Thomas")
    r = client.post(f"/admin/users/{student['id']}/reset-password", headers=a).json()
    ok = client.post("/auth/login", json={"email": student["login"], "password": r["temporary_password"]})
    assert ok.status_code == 200

    r = client.post("/admin/teachers", json={"name": "Asha Varma", "email": "asha@example.com", "classes": ["9 B"]}, headers=a)
    assert r.status_code == 200
    t = client.post("/auth/login", json={"email": "asha@example.com", "password": r.json()["temporary_password"]}).json()
    classes = client.get("/teacher/classes", headers={"Authorization": f"Bearer {t['token']}"}).json()
    assert [c["name"] for c in classes] == ["9 B"]
    assert client.post("/admin/teachers", json={"name": "X", "email": "asha@example.com"}, headers=a).status_code == 409


def test_paper_consent_change():
    a = admin()
    people = client.get("/admin/people", headers=a).json()
    sam = next(s for c in people["classes"] for s in c["students"] if s["name"] == "Sam Thomas")
    client.post(f"/admin/students/{sam['id']}/consent", json={"scope": "core_learning", "granted": True}, headers=a)
    people = client.get("/admin/people", headers=a).json()
    sam = next(s for c in people["classes"] for s in c["students"] if s["name"] == "Sam Thomas")
    assert sam["consent"]["core_learning"] is True


def test_only_admins_set_up_the_school():
    for who in ("teacher@demo.syniq", "parent@demo.syniq", "anu@demo.syniq"):
        h = login(who)
        assert client.post("/admin/import", json={"csv": SHEET}, headers=h).status_code == 403
        assert client.get("/admin/people", headers=h).status_code == 403


def test_login_attempts_are_limited():
    for _ in range(auth.LOGIN_MAX_FAILURES):
        assert client.post("/auth/login", json={"email": "rahul@demo.syniq", "password": "guess"}).status_code == 401
    assert client.post("/auth/login", json={"email": "rahul@demo.syniq", "password": "syniq-demo"}).status_code == 429
    auth._failures.clear()


def test_idle_sessions_expire_and_logout_ends_session():
    h = login("rahul@demo.syniq")
    token = h["Authorization"].split()[1]
    with SessionLocal() as db:
        s = db.get(Session, token)
        s.last_seen_at = s.last_seen_at - auth.SESSION_IDLE - timedelta(minutes=1)
        db.commit()
    assert client.get("/me", headers=h).status_code == 401

    h = login("rahul@demo.syniq")
    client.post("/auth/logout", headers=h)
    assert client.get("/me", headers=h).status_code == 401


def test_password_rules():
    h = login("rahul@demo.syniq")
    assert client.post("/me/password", json={"current": "wrong", "new": "long-enough"}, headers=h).status_code == 400
    assert client.post("/me/password", json={"current": "syniq-demo", "new": "short"}, headers=h).status_code == 422


def test_bootstrap_is_repeatable():
    with SessionLocal() as db:
        first = bootstrap(db, "Head@School.example", "a-long-password")
        assert first == ["added admin head@school.example"]  # subjects already exist
        assert bootstrap(db, "head@school.example", "a-long-password") == []
        assert db.query(Subject).count() == 9
