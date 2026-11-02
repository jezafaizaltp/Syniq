from tests.test_api import client, login  # first: it points the app at a test database

from app import interests


def test_activities_are_complete_and_cover_every_area():
    assert len({a["id"] for a in interests.ACTIVITIES}) == len(interests.ACTIVITIES)
    for a in interests.ACTIVITIES:
        assert a["area"] in interests.AREAS and a["id"].startswith(a["area"] + ".")
        assert a["title"] and a["intro"] and a["reflect"] and 3 <= len(a["steps"]) <= 6
        assert 5 <= a["minutes"] <= 20
    for area in interests.AREAS:
        assert sum(a["area"] == area for a in interests.ACTIVITIES) >= 4


def test_suggestions_keep_exploring_broad():
    first = interests.suggest({})
    assert len(first) == 3 and len({interests.BY_ID[i]["area"] for i in first}) == 3
    # Loved a creative one: more creative, but also somewhere new, never the one already done.
    after = interests.suggest({"creative.comic": "loved"})
    areas = [interests.BY_ID[i]["area"] for i in after]
    assert "creative.comic" not in after and "creative" in areas and any(a != "creative" for a in areas)
    # Everything done: nothing left to suggest.
    assert interests.suggest({a["id"]: "okay" for a in interests.ACTIVITIES}) == []


def test_explore_flow_is_private_and_has_no_labels():
    anu = login("anu@demo.syniq")
    over = client.get("/explore", headers=anu).json()
    assert [a["area"] for a in over["areas"]] == list(interests.AREAS)
    assert len(over["suggested"]) == 3

    act = client.get("/explore/scientific.float", headers=anu).json()
    assert act["steps"] and act["feeling"] is None
    assert client.post("/explore/scientific.float/reflect", json={"feeling": "loved", "note": "The foil ball sank!"}, headers=anu).json()["ok"]
    assert client.post("/explore/scientific.float/reflect", json={"feeling": "great"}, headers=anu).status_code == 422
    assert client.post("/explore/nope/reflect", json={"feeling": "okay"}, headers=anu).status_code == 404

    over = client.get("/explore", headers=anu).json()
    assert [e["id"] for e in over["enjoyed"]] == ["scientific.float"]
    assert "scientific.float" not in [s["id"] for s in over["suggested"]]
    assert not {"type", "label", "profile", "score"} & set(over)

    # Another student, a parent or a teacher never sees it.
    assert client.get("/explore", headers=login("rahul@demo.syniq")).json()["enjoyed"] == []
    for email in ("parent@demo.syniq", "teacher@demo.syniq"):
        assert client.get("/explore", headers=login(email)).status_code == 403


def test_audit_log_for_admin_only_in_plain_words():
    parent = login("parent@demo.syniq")
    child = client.get("/guardian/children", headers=parent).json()[0]
    client.post(f"/guardian/children/{child['id']}/consent", json={"scope": "mood_checkins", "granted": True}, headers=parent)

    admin = login("admin@demo.syniq")
    log = client.get("/admin/audit?limit=5", headers=admin).json()
    first = log["entries"][0]
    assert first["what"] == "Changed consent (mood_checkins, yes)" and first["role"] == "guardian" and first["student"]
    older = client.get(f"/admin/audit?before_id={first['id']}&limit=5", headers=admin).json()["entries"]
    assert all(e["id"] < first["id"] for e in older)
    assert client.get("/admin/audit", headers=login("teacher@demo.syniq")).status_code == 403
