from tests.test_api import client, login  # first: it points the app at a test database

from datetime import date, timedelta

from app import baby, pregnancy


def mother():
    mum = login("mother@demo.syniq")
    kids = {c["name"]: c for c in client.get("/family", headers=mum).json()["children"]}
    return mum, kids


def test_content_is_sourced_and_complete():
    assert len(baby.MILESTONE_IDS) == sum(len(g["items"]) for g in baby.MILESTONES)  # ids are unique
    assert all(q["source"] in baby.SOURCES for q in baby.QUESTIONS)
    assert [p["from"] for p in baby.PLAY] == [0, 3, 6, 9, 12, 18]
    assert baby.play_for(10)["title"] == "9 to 12 months" and baby.food_for(3)["from"] == 0
    assert [pregnancy.month_of(w) for w in (1, 13, 20, 40)] == [1, 3, 5, 9]
    assert pregnancy.week_of(0) == 40 and pregnancy.week_of(280) == 1
    # Calm activities are for the mother's peace; no promise about the baby's brain.
    text = str(pregnancy.CALM).lower() + str(pregnancy.MONTHS).lower()
    assert "brain" not in text and "iq" not in text.split()


def test_baby_page_milestones_vaccines_and_log():
    mum, kids = mother()
    meera = kids["Meera"]  # about 10 months old
    view = client.get(f"/baby/{meera['id']}", headers=mum).json()
    assert 9 <= view["child"]["months"] <= 10
    assert view["play"]["title"] == "9 to 12 months" and view["food"]["from"] == 6
    assert not view["together_time"]
    groups = {g["months"]: g for g in view["milestones"]}
    assert groups[2]["status"] == "past" and groups[2]["mention_to_doctor"]
    assert 12 in groups and 15 not in groups  # shows up to the next checkpoint only

    # Ticking every 2-month milestone clears the gentle note.
    for item in groups[2]["items"]:
        assert client.put(f"/baby/{meera['id']}/milestones/{item['id']}", json={"seen": True}, headers=mum).status_code == 200
    groups = {g["months"]: g for g in client.get(f"/baby/{meera['id']}", headers=mum).json()["milestones"]}
    assert not groups[2]["mention_to_doctor"] and all(i["seen"] for i in groups[2]["items"])
    client.put(f"/baby/{meera['id']}/milestones/m2-face", json={"seen": False}, headers=mum)
    assert client.put(f"/baby/{meera['id']}/milestones/made-up", json={"seen": True}, headers=mum).status_code == 404

    # Vaccines: due dates from birth, marked given with a date.
    vac = {v["id"]: v for v in view["vaccines"]}
    assert vac["bcg"]["status"] == "overdue" and vac["m16"]["status"] == "upcoming"
    birth = date.fromisoformat(meera["birth_date"])
    assert vac["w6"]["due_on"] == (birth + timedelta(days=42)).isoformat()
    assert client.put(f"/baby/{meera['id']}/vaccines/bcg", json={"given_on": meera["birth_date"]}, headers=mum).status_code == 200
    assert client.put(f"/baby/{meera['id']}/vaccines/w6", json={"given_on": "2099-01-01"}, headers=mum).status_code == 422
    vac = {v["id"]: v for v in client.get(f"/baby/{meera['id']}", headers=mum).json()["vaccines"]}
    assert vac["bcg"]["status"] == "given" and vac["bcg"]["given_on"] == meera["birth_date"]

    # Care log.
    feed = client.post(f"/baby/{meera['id']}/log", json={"kind": "breastfeed", "minutes": 15}, headers=mum).json()
    client.post(f"/baby/{meera['id']}/log", json={"kind": "sleep", "minutes": 90, "note": "afternoon nap"}, headers=mum)
    assert client.post(f"/baby/{meera['id']}/log", json={"kind": "screen"}, headers=mum).status_code == 400
    assert client.post(f"/baby/{meera['id']}/log", json={"kind": "food", "at": "2020-01-01T10:00"}, headers=mum).status_code == 422
    view = client.get(f"/baby/{meera['id']}", headers=mum).json()
    assert {e["kind"] for e in view["log_today"]} == {"breastfeed", "sleep"}
    assert view["log_week"][-1]["sleep_minutes"] == 90 and view["log_week"][-1]["counts"]["breastfeed"] == 1
    assert client.delete(f"/baby/{meera['id']}/log/{feed['id']}", headers=mum).status_code == 204

    # Only the family; and only for a baby.
    other = login("parent@demo.syniq")
    assert client.get(f"/baby/{meera['id']}", headers=other).status_code == 404
    assert client.get(f"/baby/{kids['Kabir']['id']}", headers=mum).status_code == 400


def test_pregnancy_page():
    mum, kids = mother()
    view = client.get(f"/pregnancy/{kids['Baby']['id']}", headers=mum).json()
    assert 20 <= view["week"] <= 25 and view["month"]["month"] in (5, 6)
    assert view["go_to_hospital_now"] and view["calm"] and view["disclaimer"]
    assert client.get(f"/pregnancy/{kids['Meera']['id']}", headers=mum).status_code == 400


def test_together_time_from_18_months_is_short_and_words_only():
    mum, _ = mother()
    toddler = client.post("/family/children", json={"name": "Anvi", "birth_date": (date.today() - timedelta(days=600)).isoformat()}, headers=mum).json()
    assert toddler["section"] == "baby"
    assert client.get(f"/baby/{toddler['id']}", headers=mum).json()["together_time"]
    view = client.get(f"/early/{toddler['id']}", headers=mum).json()
    assert view["together_only"] and view["limits"]["daily"] == 10 and view["left_today"] == 10
    assert {a["kind"] for a in view["activities"]} == {"name"}
    assert client.post(f"/early/{toddler['id']}/sessions", json={"activity_id": "find-colours"}, headers=mum).status_code == 404
    # Even if the holder sets a longer limit, under 2 stays at 10 minutes.
    client.put(f"/early/{toddler['id']}/limits", json={"daily": 30, "session": 15}, headers=mum)
    s = client.post(f"/early/{toddler['id']}/sessions", json={"activity_id": "farm-animals"}, headers=mum).json()
    assert s["minutes"] == 10
    client.post(f"/early/sessions/{s['id']}/end", json={"seconds": 300}, headers=mum)
    assert client.delete(f"/family/children/{toddler['id']}", headers=mum).status_code == 204
