import csv
import io

from tests.test_api import client, login  # first: it points the app at a test database

from app import evaluation
from app.evaluation import Pair


def pairs(group, changes, before=50.0):
    return [Pair(group, before + i, before + i + c) for i, c in enumerate(changes)]


def test_difference_in_differences():
    pilot = pairs("pilot", [10, 12, 8, 11, 9])
    comparison = pairs("comparison", [2, 3, 1, 2, 2])
    r = evaluation.report(pilot + comparison)
    assert r["pilot"]["change"] == 10.0 and r["comparison"]["change"] == 2.0
    assert r["difference"]["points"] == 8.0 and r["difference"]["clear"] is True
    assert r["difference"]["low"] < 8 < r["difference"]["high"]

    same = evaluation.report(pairs("pilot", [5, -5, 10, -10, 0]) + pairs("comparison", [4, -6, 9, -9, 1]))
    assert same["difference"]["clear"] is False


def test_small_groups_are_hidden():
    r = evaluation.report(pairs("pilot", [10, 12, 8, 11]) + pairs("comparison", [1, 2, 3, 4, 5]))
    assert r["pilot"] == {"n": 4, "too_few": True}
    assert r["difference"] is None
    for third in r["by_starting_marks"]:
        assert third["pilot"]["too_few"] is True  # never a figure from fewer than 5 students


def test_thirds_and_practice_split():
    pilot = [Pair("pilot", b, b + 5, practised=b) for b in range(10, 100, 6)]  # 15 students
    r = evaluation.report(pilot)
    assert [t["third"] for t in r["by_starting_marks"]] == ["lower", "middle", "upper"]
    assert sum(t["pilot"]["n"] for t in r["by_starting_marks"]) == 15
    assert [p["practice"] for p in r["by_practice"]] == ["more", "less"]
    # No split when it can't make two groups big enough, e.g. nobody has practised yet.
    assert evaluation.report([Pair("pilot", b, b + 5, practised=0) for b in range(10, 100, 6)])["by_practice"] == []


SHEET = "student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school\n" + "".join(
    f"Pilot{i} Kumar,9 R,Parent{i},results{i}@example.com,,yes,no,no\n" for i in range(6)
) + "Noconsent Kumar,9 R,Parent9,results9@example.com,,no,no,no\n"


def test_results_flow_admin_only_and_private():
    a = login("admin@demo.syniq")
    accounts = client.post("/admin/import", json={"csv": SHEET, "dry_run": False}, headers=a).json()["accounts"]
    logins = [x["student_login"] for x in accounts]
    pilot, no_consent = logins[:6], logins[6]
    subjects = client.get("/subjects", headers=a).json()
    bio = next(s for s in subjects if s["code"] == "bio")["id"]

    before = client.post("/admin/results/assessments", headers=a,
                         json={"name": "First term", "subject_id": bio, "max_marks": 40, "phase": "before", "taken_on": "2027-08-20"}).json()["id"]
    after = client.post("/admin/results/assessments", headers=a,
                        json={"name": "Second term", "subject_id": bio, "max_marks": 40, "phase": "after", "taken_on": "2027-12-15"}).json()["id"]

    # Names, unknown logins, students without consent and bad marks are all refused before anything is saved.
    bad = "student,marks\nAnu Krishna,20\n" + f"{no_consent},20\n{pilot[0]},45\n{pilot[1]},abc\n"
    r = client.post(f"/admin/results/assessments/{before}/scores", json={"csv": bad, "dry_run": False}, headers=a).json()
    assert r["ok"] is False and [e["row"] for e in r["errors"]] == [2, 3, 4, 5]

    rows_before = "student,marks\n" + "".join(f"{p},{20 + i}\n" for i, p in enumerate(pilot)) + "".join(f"C{i},{20 + i}\n" for i in range(6)) + "c99,AB\n"
    rows_after = "student,marks\n" + "".join(f"{p},{26 + i}\n" for i, p in enumerate(pilot)) + "".join(f"c{i},{21 + i}\n" for i in range(6))
    r = client.post(f"/admin/results/assessments/{before}/scores", json={"csv": rows_before}, headers=a).json()
    assert (r["ok"], r["pilot"], r["comparison"], r["absent"]) == (True, 6, 6, 1)
    client.post(f"/admin/results/assessments/{before}/scores", json={"csv": rows_before, "dry_run": False}, headers=a)
    client.post(f"/admin/results/assessments/{after}/scores", json={"csv": rows_after, "dry_run": False}, headers=a)

    report = client.get("/admin/results/report", headers=a).json()
    biology = next(s for s in report["subjects"] if s["subject"] == "Biology")
    assert biology["pilot"]["change"] == 15.0  # 6 of 40 marks
    assert biology["comparison"]["change"] == 2.5  # 1 of 40
    assert biology["difference"]["points"] == 12.5
    assert "Pilot0" not in str(report) and pilot[0] not in str(report)

    exported = list(csv.DictReader(io.StringIO(client.get("/admin/results/export.csv", headers=a).text)))
    assert len([r for r in exported if r["subject"] == "Biology"]) == 12
    assert all(set(r) == {"group", "subject", "before_percent", "after_percent", "questions_practised"} for r in exported)

    for who in ("teacher@demo.syniq", "parent@demo.syniq", "anu@demo.syniq"):
        h = login(who)
        assert client.get("/admin/results/report", headers=h).status_code == 403
        assert client.get("/admin/results/export.csv", headers=h).status_code == 403

    assert client.delete("/admin/results", headers=a).json() == {"ok": True}
    assert client.get("/admin/results/assessments", headers=a).json() == []
