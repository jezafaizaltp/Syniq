"""CBSE Class 10 students take Hindi A or Hindi B; each sees only the course they chose."""

from sqlalchemy import select

from tests.test_api import client, login  # first: points the app at a fresh test database

from app.auth import hash_password
from app.db import SessionLocal
from app.models import Consent, GuardianLink, User
from app.seed import DEMO_PASSWORD


def student(email, grade):
    with SessionLocal() as db:
        guardian = db.scalars(select(User).where(User.email == "parent@demo.syniq")).first()
        s = User(name="Hc", email=email, password_hash=hash_password(DEMO_PASSWORD), role="student",
                 settings={"board": "cbse", "grade": grade})
        db.add(s)
        db.flush()
        db.add(GuardianLink(guardian_id=guardian.id, student_id=s.id))
        db.add(Consent(student_id=s.id, guardian_id=guardian.id, scope="core_learning", granted=True, method="school_form"))
        db.commit()


def codes(headers):
    return {s["code"]: s["chapters"] for s in client.get("/subjects", headers=headers).json()}


def test_class_10_sees_one_hindi_course_and_can_switch():
    student("hindi.hc@demo.syniq", 10)
    me = login("hindi.hc@demo.syniq")
    assert client.get("/me", headers=me).json()["hindi_course"] == "a"
    seen = codes(me)
    assert "cbse10-hin" in seen and "cbse10-hinb" not in seen

    assert client.put("/me/settings", json={"hindi_course": "b"}, headers=me).status_code == 200
    seen = codes(me)
    assert "cbse10-hinb" in seen and "cbse10-hin" not in seen
    assert seen["cbse10-hinb"] == 17  # Sparsh 2 (14) and Sanchayan 2 (3)
    assert client.get("/me", headers=me).json()["hindi_course"] == "b"
    assert client.put("/me/settings", json={"hindi_course": "c"}, headers=me).status_code == 400


def test_other_classes_have_no_hindi_choice():
    student("hindi9.hc@demo.syniq", 9)
    me = login("hindi9.hc@demo.syniq")
    assert "hindi_course" not in client.get("/me", headers=me).json()
    assert "cbse9-hin" in codes(me)
