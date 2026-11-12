"""The demo learner's week: the mentor, parent and teacher views all have something true to show."""

from tests.test_api import client, login  # first: points the app at a fresh test database

from tools import demo_week


def test_demo_week_gives_every_view_something_to_show_and_can_run_again():
    demo_week.main()
    demo_week.main()  # resets Meera rather than piling up a second week
    h = login("meera@demo.syniq")
    plan = client.get("/me/mentor", headers=h).json()
    assert [s["kind"] for s in plan["steps"]] == ["fix_mistake", "relearn", "review"]
    assert plan["week"]["lessons"] == 3 and plan["week"]["days"] == 3 and plan["week"]["came_back"] >= 1
    parent = login("parent@demo.syniq")
    kids = client.get("/guardian/children", headers=parent).json()
    meera = next(k for k in kids if k["name"] == "Meera")
    assert client.get(f"/guardian/children/{meera['id']}/week", headers=parent).json()["grew"]["lessons"] == 3
    teacher = login("teacher@demo.syniq")
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    rows = client.get(f"/teacher/classes/{class_id}/lesson-trouble", headers=teacher).json()
    assert any(r["topic"] == "Two numbers from their sum and difference" and r["idea"] == 1 for r in rows)
