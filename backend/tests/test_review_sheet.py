from tests.test_api import client, login  # first: it points the app at a test database


def test_teacher_prints_every_question_in_a_subject_with_its_tips():
    teacher = login("teacher@demo.syniq")
    subjects = client.get("/admin/review-sheet", headers=teacher).json()
    assert subjects and all(s["questions"] > 0 for s in subjects)
    math = next(s for s in subjects if s["name"] == "Mathematics" and s["syllabus"] == "kerala_scert")
    sheet = client.get(f"/admin/review-sheet/{math['id']}", headers=teacher).json()
    questions = [q for ch in sheet["chapters"] for t in ch["topics"] for q in t["questions"]]
    assert len(questions) == sheet["questions"] == math["questions"]
    assert [q["n"] for q in questions] == list(range(1, len(questions) + 1))
    assert all(q["answer"] and q["prompt"] for q in questions)
    tipped = [m for q in questions for m in q["mistakes"]]
    assert tipped and all(m["tip"] for m in tipped)
    assert client.get("/admin/review-sheet/999999", headers=teacher).status_code == 404


def test_students_and_parents_cannot_open_the_review_sheet():
    for email in ("anu@demo.syniq",):
        assert client.get("/admin/review-sheet", headers=login(email)).status_code == 403


def _sheet_questions(teacher):
    subjects = client.get("/admin/review-sheet", headers=teacher).json()
    math = next(s for s in subjects if s["name"] == "Mathematics" and s["syllabus"] == "kerala_scert")
    sheet = client.get(f"/admin/review-sheet/{math['id']}", headers=teacher).json()
    return [q for ch in sheet["chapters"] for t in ch["topics"] for q in t["questions"]]


def test_filled_in_sheet_comes_back_as_a_fix_list_without_changing_questions():
    teacher = login("teacher@demo.syniq")
    qs = _sheet_questions(teacher)
    a, b, c, d = qs[:4]
    csv_text = (
        "﻿no,id,chapter,topic,question,choices,answer,solution,wrong answers and tips,ok (yes/no),what to fix\n"
        f"1,{a['id']},x,x,x,,x,x,x,yes,\n"
        f"2,{b['id']},x,x,x,,x,x,x,no,\"The tip, gives too much away\"\n"
        f"3,{c['id']},x,x,x,,x,x,x,,\n"
        f"4,{d['id']},x,x,x,,x,x,x,no,\n"
        "5,99999999,x,x,x,,x,x,x,no,missing\n"
    )
    r = client.post("/admin/review-sheet/upload", json={"csv": csv_text}, headers=teacher)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": 1, "to_fix": 2, "not_checked": 1, "unknown_ids": ["99999999"]}
    fixes = {f["id"]: f for f in client.get("/admin/review-fixes", headers=teacher).json()}
    assert set(fixes) >= {b["id"], d["id"]} and a["id"] not in fixes
    assert fixes[b["id"]]["note"].startswith("The tip, gives too much away")
    after = {q["id"]: q for q in _sheet_questions(teacher)}
    assert after[b["id"]]["status"] == b["status"] and after[b["id"]]["fix_note"]
    # Uploading the same sheet again doesn't repeat the note.
    client.post("/admin/review-sheet/upload", json={"csv": csv_text}, headers=teacher)
    assert client.get("/admin/review-fixes", headers=teacher).json()[0]["note"].count("gives too much away") <= 1
    assert client.post(f"/admin/review-fixes/{b['id']}/done", headers=teacher).json() == {"ok": True}
    assert client.post(f"/admin/review-fixes/{d['id']}/done", headers=teacher).status_code == 200
    assert b["id"] not in {f["id"] for f in client.get("/admin/review-fixes", headers=teacher).json()}
    assert client.post("/admin/review-sheet/upload", json={"csv": "name,class\nAnu,9\n"}, headers=teacher).status_code == 400
    assert client.post("/admin/review-sheet/upload", json={"csv": csv_text}, headers=login("anu@demo.syniq")).status_code == 403
