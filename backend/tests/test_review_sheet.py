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
