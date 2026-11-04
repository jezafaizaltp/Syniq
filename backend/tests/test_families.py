from tests.test_api import client, login  # first: it points the app at a test database

from datetime import date, timedelta

from app.family import age_words, section_for

TODAY = date(2026, 11, 2)


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_section_comes_from_dates_and_class_only():
    assert section_for(None, "2027-03-01", None, TODAY) == "pregnancy"
    assert section_for("2026-01-15", None, None, TODAY) == "baby"
    assert section_for("2024-11-03", None, None, TODAY) == "baby"  # one day short of 2 years
    assert section_for("2024-11-02", None, None, TODAY) == "early"
    assert section_for("2022-11-02", None, None, TODAY) == "school"
    assert section_for("2023-06-01", None, -1, TODAY) == "school"  # in LKG already
    assert age_words("2026-01-15", None, TODAY) == "9 months old"
    assert age_words(None, "2026-12-14", TODAY) == "Due in about 6 weeks"


def test_family_account_from_sign_up_to_a_childs_login():
    r = client.post("/auth/signup", json={"name": "Asha", "email": "Asha.Mother@Example.com", "password": "short"})
    assert r.status_code == 422
    r = client.post("/auth/signup", json={"name": "Asha", "email": "Asha.Mother@Example.com", "password": "a-long-password"})
    assert r.status_code == 200, r.text
    asha = bearer(r.json()["token"])
    assert client.post("/auth/signup", json={"name": "X", "email": "asha.mother@example.com", "password": "a-long-password"}).status_code == 409
    assert client.get("/me", headers=asha).json()["family"] == {"holder": True}

    fam = client.get("/family", headers=asha).json()
    assert fam["you"] == {"relation": "mother", "holder": True} and fam["children"] == []

    # Dates decide where each child starts.
    bad = client.post("/family/children", json={"name": "Nobody"}, headers=asha)
    assert bad.status_code == 422
    assert client.post("/family/children", json={"name": "Later", "birth_date": "2099-01-01"}, headers=asha).status_code == 422
    baby = client.post("/family/children", json={"name": "Meera", "birth_date": days_ago(200)}, headers=asha).json()
    toddler = client.post("/family/children", json={"name": "Kabir", "birth_date": days_ago(365 * 3)}, headers=asha).json()
    coming = client.post("/family/children", json={"name": "Baby", "due_date": (date.today() + timedelta(days=90)).isoformat()}, headers=asha).json()
    big = client.post("/family/children", json={"name": "Riya", "birth_date": days_ago(365 * 14 + 100), "board": "kerala_scert", "grade": 9}, headers=asha).json()
    assert [baby["section"], toddler["section"], coming["section"], big["section"]] == ["baby", "early", "pregnancy", "school"]
    assert big["grade_name"] == "Class 9"

    # Only school children get a login, and making one is the holder's consent.
    assert client.post(f"/family/children/{toddler['id']}/login", json={"username": "kabir"}, headers=asha).status_code == 400
    assert client.post(f"/family/children/{big['id']}/login", json={"username": "anu@demo.syniq"}, headers=asha).status_code == 409
    made = client.post(f"/family/children/{big['id']}/login", json={"username": "Riya.K"}, headers=asha).json()
    assert made["login"] == "riya.k"
    r = client.post("/auth/login", json={"email": "riya.k", "password": made["temporary_password"]})
    riya = bearer(r.json()["token"])
    me = client.get("/me", headers=riya).json()
    assert me["must_change_password"] and me["consent"]["core_learning"] and me["class"] == {"board": "kerala_scert", "grade": 9}
    assert client.get("/subjects", headers=riya).json()  # Kerala Class 9 has content

    # Move her to CBSE Class 9: she sees the CBSE subjects only, never the Kerala ones.
    client.put(f"/family/children/{big['id']}", json={"name": "Riya", "birth_date": big["birth_date"], "board": "cbse", "grade": 9}, headers=asha)
    codes = [s["code"] for s in client.get("/subjects", headers=riya).json()]
    assert codes and all(c.startswith("cbse9-") for c in codes)
    # A class with no subjects yet shows none rather than another class's.
    client.put(f"/family/children/{big['id']}", json={"name": "Riya", "birth_date": big["birth_date"], "board": "kerala_scert", "grade": 5}, headers=asha)
    assert client.get("/subjects", headers=riya).json() == []
    client.put(f"/family/children/{big['id']}", json={"name": "Riya", "birth_date": big["birth_date"], "board": "cbse", "grade": 9}, headers=asha)
    assert client.put(f"/family/children/{big['id']}", json={"name": "Riya", "birth_date": big["birth_date"]}, headers=asha).status_code == 400
    assert client.delete(f"/family/children/{big['id']}", headers=asha).status_code == 400
    assert client.delete(f"/family/children/{coming['id']}", headers=asha).status_code == 204

    # A father joins with his own login and sees the children, but can't change who's in the family.
    dad = client.post("/family/adults", json={"name": "Ravi", "email": "ravi@example.com", "relation": "father"}, headers=asha).json()
    r = client.post("/auth/login", json={"email": "ravi@example.com", "password": dad["temporary_password"]})
    ravi = bearer(r.json()["token"])
    fam = client.get("/family", headers=ravi).json()
    assert fam["you"] == {"relation": "father", "holder": False} and len(fam["children"]) == 3
    assert [c["name"] for c in client.get("/guardian/children", headers=ravi).json()] == ["Riya"]
    assert client.post("/family/children", json={"name": "X", "birth_date": days_ago(10)}, headers=ravi).status_code == 403
    assert client.post("/family/adults", json={"name": "Y", "email": "y@example.com", "relation": "carer"}, headers=ravi).status_code == 403

    # Nobody outside the family sees it.
    other = login("parent@demo.syniq")
    assert client.get("/family", headers=other).status_code == 404
    assert client.put(f"/family/children/{baby['id']}", json={"name": "X", "birth_date": days_ago(10)}, headers=other).status_code == 404
    assert client.get("/family", headers=riya).status_code == 403

    # Removing him ends his access straight away.
    holder_row = next(a for a in fam["adults"] if a["holder"])
    assert client.delete(f"/family/adults/{holder_row['id']}", headers=asha).status_code == 400
    dad_row = next(a for a in fam["adults"] if a["relation"] == "father")
    assert client.delete(f"/family/adults/{dad_row['id']}", headers=asha).status_code == 204
    assert client.get("/family", headers=ravi).status_code == 401
    assert client.post("/auth/login", json={"email": "ravi@example.com", "password": dad["temporary_password"]}).status_code == 401

    actions = [e["what"] for e in client.get("/admin/audit", headers=login("admin@demo.syniq")).json()["entries"]]
    assert "Made a login for a child" in actions and "Removed an adult from a family" in actions


def test_pilot_students_keep_kerala_class_9():
    anu = login("anu@demo.syniq")
    assert client.get("/me", headers=anu).json()["class"] == {"board": "kerala_scert", "grade": 9}
    assert len(client.get("/subjects", headers=anu).json()) >= 9
