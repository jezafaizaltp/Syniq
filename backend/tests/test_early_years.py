from tests.test_api import client, login  # first: it points the app at a test database

from app import early
from app.db import SessionLocal
from app.models import Child, User


def mother_family():
    mum = login("mother@demo.syniq")
    fam = client.get("/family", headers=mum).json()
    by_name = {c["name"]: c for c in fam["children"]}
    return mum, by_name


def test_activities_are_well_formed():
    assert len(early.ACTIVITIES) >= 18 and len(early.BY_ID) == len(early.ACTIVITIES)
    for a in early.ACTIVITIES:
        assert a["area"] in early.AREAS and a["together"] and a["after"]
        if a["kind"] == "name":
            assert all(i["pic"] and i["word"] and i["say"] for i in a["items"])
        elif a["kind"] == "find":
            assert all(0 <= r["answer"] < len(r["options"]) for r in a["rounds"])
        else:
            assert a["kind"] == "count" and all(1 <= r["n"] <= 5 for r in a["rounds"])


def test_screen_time_follows_the_parents_limits():
    mum, kids = mother_family()
    kabir = kids["Kabir"]
    assert kabir["section"] == "early"
    # Only for 2 to 4 year olds.
    assert client.get(f"/early/{kids['Meera']['id']}", headers=mum).status_code == 400

    view = client.get(f"/early/{kabir['id']}", headers=mum).json()
    assert view["limits"]["daily"] == 20 and view["left_today"] == 20 and len(view["week"]) == 7

    # Limits are capped at the paediatric guidance.
    assert client.put(f"/early/{kabir['id']}/limits", json={"daily": 90, "session": 10}, headers=mum).status_code == 422
    assert client.put(f"/early/{kabir['id']}/limits", json={"daily": 12, "session": 15}, headers=mum).json() == {"daily": 12, "session": 12}
    client.put(f"/early/{kabir['id']}/limits", json={"daily": 12, "session": 8}, headers=mum)

    s1 = client.post(f"/early/{kabir['id']}/sessions", json={"activity_id": "farm-animals"}, headers=mum).json()
    assert s1["minutes"] == 8
    # A running sitting counts in full: only 4 minutes are left to start.
    s2 = client.post(f"/early/{kabir['id']}/sessions", json={"activity_id": "fruits"}, headers=mum).json()
    assert s2["minutes"] == 4
    assert client.post(f"/early/{kabir['id']}/sessions", json={"activity_id": "fruits"}, headers=mum).status_code == 409

    # Ending early gives the time back; claims beyond the sitting are capped.
    assert client.post(f"/early/sessions/{s1['id']}/end", json={"seconds": 120}, headers=mum).json()["seconds"] == 120
    assert client.post(f"/early/sessions/{s2['id']}/end", json={"seconds": 9999}, headers=mum).json()["seconds"] == 4 * 60 + 60
    assert client.post(f"/early/sessions/{s1['id']}/end", json={"seconds": 1}, headers=mum).json()["seconds"] == 120  # only once
    left = client.get(f"/early/{kabir['id']}", headers=mum).json()["left_today"]
    assert left == 12 - 2 - 5

    # Time played offline still counts when the phone is back online.
    today = client.get(f"/early/{kabir['id']}", headers=mum).json()["today"]
    client.post(f"/early/{kabir['id']}/played", json={"activity_id": "fruits", "day": today, "seconds": 120}, headers=mum)
    assert client.get(f"/early/{kabir['id']}", headers=mum).json()["left_today"] == left - 2
    assert client.post(f"/early/{kabir['id']}/played", json={"activity_id": "fruits", "day": "2020-01-01", "seconds": 1}, headers=mum).status_code == 422

    # Nobody outside the family can see or start it.
    other = login("parent@demo.syniq")
    assert client.get(f"/early/{kabir['id']}", headers=other).status_code == 404
    assert client.post(f"/early/sessions/{s1['id']}/end", json={"seconds": 1}, headers=other).status_code == 404


def test_only_the_holder_changes_limits():
    mum, kids = mother_family()
    dad = client.post("/family/adults", json={"name": "Demo Dad", "email": "dad.early@example.com", "relation": "father"}, headers=mum).json()
    r = client.post("/auth/login", json={"email": "dad.early@example.com", "password": dad["temporary_password"]})
    dad_h = {"Authorization": f"Bearer {r.json()['token']}"}
    kabir = kids["Kabir"]["id"]
    assert client.get(f"/early/{kabir}", headers=dad_h).status_code == 200
    assert client.put(f"/early/{kabir}/limits", json={"daily": 30, "session": 10}, headers=dad_h).status_code == 403
    with SessionLocal() as db:
        assert db.get(Child, kabir).daily_limit != 30
        assert db.query(User).filter_by(email="dad.early@example.com").one().role == "guardian"
