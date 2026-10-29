from pathlib import Path

from tests.test_api import client, login  # first: it points the app at a test database

from app import content_packs

from app.db import SessionLocal
from app.models import Chapter, Concept, Subject

SHEET = """subject,chapter_number,chapter_title,topic
ss,39,Kerala History,Early Kerala
ss,39,Kerala History,The spice trade
Information Technology,2,Spreadsheets,
"""


def chapters(code):
    with SessionLocal() as db:
        subject = db.query(Subject).filter_by(code=code).one()
        return {c.number: (c.title, [t.title for t in db.query(Concept).filter_by(chapter_id=c.id).order_by(Concept.order)])
                for c in db.query(Chapter).filter_by(subject_id=subject.id)}


def test_syllabus_checked_then_added_and_safe_to_repeat():
    a = login("admin@demo.syniq")
    bad = SHEET + "geo,1,Mountains,\nss,x,,\nss,39,History of Kerala,Temple architecture\n"
    r = client.post("/admin/syllabus", json={"csv": bad, "dry_run": False}, headers=a).json()
    assert r["ok"] is False and [e["row"] for e in r["errors"]] == [5, 6, 7]
    assert chapters("ss") == {}

    r = client.post("/admin/syllabus", json={"csv": SHEET}, headers=a).json()
    assert r == {"ok": True, "errors": [], "dry_run": True, "chapters": 2, "new_chapters": 2, "topics": 3}

    r = client.post("/admin/syllabus", json={"csv": SHEET, "dry_run": False}, headers=a).json()
    assert (r["added_chapters"], r["added_topics"]) == (2, 3)
    assert chapters("ss") == {39: ("Kerala History", ["Early Kerala", "The spice trade"])}
    assert chapters("it") == {2: ("Spreadsheets", ["Spreadsheets"])}

    # Uploading again with one more topic adds only that topic, at the end.
    more = SHEET + "ss,39,Kerala History,Temple architecture\n"
    r = client.post("/admin/syllabus", json={"csv": more, "dry_run": False}, headers=a).json()
    assert (r["added_chapters"], r["added_topics"]) == (0, 1)
    assert chapters("ss")[39][1][-1] == "Temple architecture"

    # A different title for an existing chapter is refused rather than renaming it.
    r = client.post("/admin/syllabus", json={"csv": "subject,chapter_number,chapter_title\nss,39,Kerala\n"}, headers=a).json()
    assert r["ok"] is False and "already exists" in r["errors"][0]["problems"][0]


def test_only_admins_load_the_syllabus():
    for who in ("teacher@demo.syniq", "anu@demo.syniq"):
        assert client.post("/admin/syllabus", json={"csv": SHEET}, headers=login(who)).status_code == 403


def test_students_only_see_chapters_with_approved_content():
    a = login("admin@demo.syniq")
    client.post("/admin/syllabus", json={"csv": SHEET, "dry_run": False}, headers=a)
    anu, teacher = login("anu@demo.syniq"), login("teacher@demo.syniq")
    social = next(s for s in client.get("/subjects", headers=anu).json() if s["code"] == "ss")
    assert social["chapters"] == 0
    assert client.get(f"/subjects/{social['id']}/chapters", headers=anu).json() == []
    assert len(client.get(f"/subjects/{social['id']}/chapters", headers=teacher).json()) == 1
    math = next(s for s in client.get("/subjects", headers=anu).json() if s["code"] == "math")
    packs = [p for _, p in content_packs.read_packs() if p["subject"] == "math"]
    assert math["chapters"] == 2 + len(packs)  # the two demo chapters and the content packs have approved content
    for code in {p["subject"] for _, p in content_packs.read_packs()} - {"math"}:
        subject = next(s for s in client.get("/subjects", headers=anu).json() if s["code"] == code)
        assert subject["chapters"] == len([p for _, p in content_packs.read_packs() if p["subject"] == code])


def test_draft_sheet_in_the_repo_is_valid():
    sheet = (Path(__file__).parents[2] / "content" / "class9-syllabus-draft.csv").read_text()
    r = client.post("/admin/syllabus", json={"csv": sheet}, headers=login("admin@demo.syniq")).json()
    assert r["ok"] is True and r["chapters"] == 63
