from tests.test_api import client, login  # first: it points the app at a test database




def test_parent_shares_a_child_with_a_specialist_and_can_stop():
    admin = login("admin@demo.syniq")
    r = client.post("/admin/specialists", json={"name": "Meera Nair", "email": "meera@school.example", "title": "Special educator"}, headers=admin)
    assert r.status_code == 200
    temp = r.json()["temporary_password"]
    assert client.post("/admin/specialists", json={"name": "X", "email": "meera@school.example"}, headers=admin).status_code == 409

    tok = client.post("/auth/login", json={"email": "meera@school.example", "password": temp}).json()["token"]
    meera = {"Authorization": f"Bearer {tok}"}
    client.post("/me/password", json={"current": temp, "new": "meera-long-password"}, headers=meera)
    meera = {"Authorization": f"Bearer {client.post('/auth/login', json={'email': 'meera@school.example', 'password': 'meera-long-password'}).json()['token']}"}

    # Nothing to see until a parent shares.
    assert client.get("/specialist/students", headers=meera).json() == []

    parent = login("parent@demo.syniq")
    child = client.get("/guardian/children", headers=parent).json()[0]
    spec = next(s for s in client.get("/guardian/specialists", headers=parent).json() if s["name"] == "Meera Nair")
    assert spec["shared_with"] == []
    client.put(f"/guardian/children/{child['id']}/specialists/{spec['id']}", json={"share": True}, headers=parent)

    students = client.get("/specialist/students", headers=meera).json()
    assert [s["id"] for s in students] == [child["id"]]
    seen = students[0]
    assert {"chosen_support", "noticed_support", "subjects", "repeated_mistakes", "last_14_days"} <= set(seen)
    # Support, not ranking or private things.
    assert not {"mood", "checkins", "marks", "goals", "notes", "score", "p_known"} & set(seen)

    # Teachers and other roles can't use the specialist view.
    assert client.get("/specialist/students", headers=login("teacher@demo.syniq")).status_code == 403
    # A parent can't share a child who isn't theirs.
    assert client.put(f"/guardian/children/99999/specialists/{spec['id']}", json={"share": True}, headers=parent).status_code == 404

    client.put(f"/guardian/children/{child['id']}/specialists/{spec['id']}", json={"share": False}, headers=parent)
    assert client.get("/specialist/students", headers=meera).json() == []

    whats = [e["what"] for e in client.get("/admin/audit?limit=20", headers=admin).json()["entries"]]
    assert any(w.startswith("Shared a child with a specialist") for w in whats)
    assert any(w.startswith("Stopped sharing") for w in whats)
    assert "Specialist viewed a child" in whats
