from pathlib import Path

from tests.test_api import client, login  # first: it points the app at a test database

from app.db import SessionLocal
from app.models import Chapter, Concept, Subject

SHEET = """subject,chapter_number,chapter_title,topic
chem,1,Structure of Atom,Atoms and their parts
chem,1,Structure of Atom,Electron arrangement
Biology,2,Digestion and Transport of Nutrients,
"""


def chapters(code):
    with SessionLocal() as db:
        subject = db.query(Subject).filter_by(code=code).one()
        return {c.number: (c.title, [t.title for t in db.query(Concept).filter_by(chapter_id=c.id).order_by(Concept.order)])
                for c in db.query(Chapter).filter_by(subject_id=subject.id)}


def test_syllabus_checked_then_added_and_safe_to_repeat():
    a = login("admin@demo.syniq")
    bad = SHEET + "geo,1,Mountains,\nchem,x,,\nchem,1,Atomic Structure,Isotopes\n"
    r = client.post("/admin/syllabus", json={"csv": bad, "dry_run": False}, headers=a).json()
    assert r["ok"] is False and [e["row"] for e in r["errors"]] == [5, 6, 7]
    assert chapters("chem") == {}

    r = client.post("/admin/syllabus", json={"csv": SHEET}, headers=a).json()
    assert r == {"ok": True, "errors": [], "dry_run": True, "chapters": 2, "new_chapters": 2, "topics": 3}

    r = client.post("/admin/syllabus", json={"csv": SHEET, "dry_run": False}, headers=a).json()
    assert (r["added_chapters"], r["added_topics"]) == (2, 3)
    assert chapters("chem") == {1: ("Structure of Atom", ["Atoms and their parts", "Electron arrangement"])}
    assert chapters("bio") == {2: ("Digestion and Transport of Nutrients", ["Digestion and Transport of Nutrients"])}

    # Uploading again with one more topic adds only that topic, at the end.
    more = SHEET + "chem,1,Structure of Atom,Isotopes\n"
    r = client.post("/admin/syllabus", json={"csv": more, "dry_run": False}, headers=a).json()
    assert (r["added_chapters"], r["added_topics"]) == (0, 1)
    assert chapters("chem")[1][1][-1] == "Isotopes"

    # A different title for an existing chapter is refused rather than renaming it.
    r = client.post("/admin/syllabus", json={"csv": "subject,chapter_number,chapter_title\nchem,1,Atoms\n"}, headers=a).json()
    assert r["ok"] is False and "already exists" in r["errors"][0]["problems"][0]


def test_only_admins_load_the_syllabus():
    for who in ("teacher@demo.syniq", "anu@demo.syniq"):
        assert client.post("/admin/syllabus", json={"csv": SHEET}, headers=login(who)).status_code == 403


def test_students_only_see_chapters_with_approved_content():
    a = login("admin@demo.syniq")
    client.post("/admin/syllabus", json={"csv": SHEET, "dry_run": False}, headers=a)
    anu, teacher = login("anu@demo.syniq"), login("teacher@demo.syniq")
    chem = next(s for s in client.get("/subjects", headers=anu).json() if s["code"] == "chem")
    assert chem["chapters"] == 0
    assert client.get(f"/subjects/{chem['id']}/chapters", headers=anu).json() == []
    assert len(client.get(f"/subjects/{chem['id']}/chapters", headers=teacher).json()) == 1
    math = next(s for s in client.get("/subjects", headers=anu).json() if s["code"] == "math")
    assert math["chapters"] == 6  # the two demo chapters and the four from content packs have approved content


def test_draft_sheet_in_the_repo_is_valid():
    sheet = (Path(__file__).parents[2] / "content" / "class9-syllabus-draft.csv").read_text()
    r = client.post("/admin/syllabus", json={"csv": sheet}, headers=login("admin@demo.syniq")).json()
    assert r["ok"] is True and r["chapters"] == 30
