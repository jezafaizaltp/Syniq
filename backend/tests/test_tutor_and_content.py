import json
from types import SimpleNamespace

import pytest

from app import ai
from app.db import SessionLocal
from app.models import Explanation, Item
from tests.test_api import client, login, math_chapter_id


class FakeClaude:
    """Stands in for anthropic.Anthropic(); records every request."""

    def __init__(self, text="", stop_reason="end_turn"):
        self.text, self.stop_reason, self.calls = text, stop_reason, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=self.text)])


@pytest.fixture
def fake():
    def install(**kw):
        f = FakeClaude(**kw)
        ai.set_client(f)
        return f

    yield install
    ai.set_client(None)


def first_concept(headers):
    chapter = client.get(f"/chapters/{math_chapter_id(headers)}", headers=headers).json()
    return chapter["concepts"][1]["id"]


def ask(headers, text, concept_id=None):
    concept_id = concept_id or first_concept(headers)
    return client.post("/tutor", json={"concept_id": concept_id, "history": [{"role": "student", "text": text}]}, headers=headers)


# --- Tutor --------------------------------------------------------------------------

def test_tutor_off_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    anu = login("anu@demo.syniq")
    assert client.get("/ai/status", headers=anu).json() == {"enabled": False}
    assert ask(anu, "why is there a 2ab?").status_code == 503


def test_tutor_grounded_and_sends_no_personal_data(fake):
    f = fake(text="Good question. What do you get when you multiply (a + b) by itself?")
    anu = login("anu@demo.syniq")
    r = ask(anu, "why is there a 2ab? my number is 98470 12345 and email anu@example.com")
    assert r.status_code == 200
    assert r.json()["reply"].startswith("Good question")

    sent = f.calls[0]
    wire = json.dumps(sent, ensure_ascii=False)
    assert "Anu" not in wire and "anu@" not in wire and "98470" not in wire
    assert "[number removed]" in wire and "[email removed]" in wire
    assert "Square of a sum" in sent["system"]  # grounded in the current topic
    assert "a² + 2ab + b²" in sent["system"]  # and its approved explanation
    assert sent["model"] == "claude-opus-5-5"
    assert sent["fallbacks"] == "default" and sent["betas"] == [ai.FALLBACK_BETA]


def test_tutor_distress_answered_without_calling_claude(fake):
    f = fake(text="should not be used")
    anu = login("anu@demo.syniq")
    r = ask(anu, "I want to hurt myself")
    assert "14416" in r.json()["reply"]
    assert f.calls == []


def test_tutor_refusal_gets_gentle_redirect(fake):
    fake(stop_reason="refusal")
    anu = login("anu@demo.syniq")
    assert "back to the topic" in ask(anu, "something off topic").json()["reply"]


def test_tutor_rejects_long_or_non_student_last_turn(fake):
    fake(text="ok")
    anu = login("anu@demo.syniq")
    assert ask(anu, "x" * 601).status_code == 400
    r = client.post(
        "/tutor",
        json={"concept_id": first_concept(anu), "history": [{"role": "tutor", "text": "hi"}]},
        headers=anu,
    )
    assert r.status_code == 400


def test_tutor_is_for_students_only(fake):
    fake(text="ok")
    t = login("teacher@demo.syniq")
    assert ask(t, "hello", concept_id=1).status_code == 403


# --- Content pipeline -------------------------------------------------------------------

DRAFT = {
    "explanations": [
        {"style": "text", "body": "Speed is distance divided by time."},
        {"style": "visual", "body": "Picture a bus moving along a road with marks every kilometre."},
        {"style": "not_a_style", "body": "ignored"},
    ],
    "items": [
        {
            "kind": "mcq", "prompt": "A bus goes 120 km in 2 hours. Its speed?", "options": ["60 km/h", "240 km/h", "122 km/h"],
            "answer": "60 km/h", "hints": ["Speed = distance ÷ time"], "solution": "120 ÷ 2 = 60 km/h", "difficulty": 1,
            "misconceptions": [{"wrong_answer": "240 km/h", "mistake": "multiplied_instead"}],
        },
        {
            "kind": "numeric", "prompt": "Distance in 3 hours at 40 km/h?", "options": [], "answer": "120",
            "hints": ["Distance = speed × time"], "solution": "40 × 3 = 120", "difficulty": 2, "misconceptions": [],
        },
        {  # answer is not an option: dropped
            "kind": "mcq", "prompt": "Broken", "options": ["a", "b"], "answer": "c",
            "hints": [], "solution": "", "difficulty": 1, "misconceptions": [],
        },
        {  # numeric answer that is not a number: dropped
            "kind": "numeric", "prompt": "Broken", "options": [], "answer": "sixty",
            "hints": [], "solution": "", "difficulty": 1, "misconceptions": [],
        },
    ],
    "reviewer_notes": "Check the textbook uses km/h rather than kmph.",
}


def physics_subject(headers):
    return next(s for s in client.get("/subjects", headers=headers).json() if s["code"] == "phy")


def test_teacher_builds_chapter_drafts_with_ai_and_approves(fake):
    t = login("teacher@demo.syniq")
    phy = physics_subject(t)
    r = client.post(
        "/teacher/chapters",
        json={"subject_id": phy["id"], "number": 1, "title": "Motion", "concepts": [{"title": "Speed", "notes": "Speed = distance / time, in km/h and m/s."}]},
        headers=t,
    )
    assert r.status_code == 200
    concept_id = client.get(f"/chapters/{r.json()['id']}", headers=t).json()["concepts"][0]["id"]

    f = fake(text=json.dumps(DRAFT))
    r = client.post(f"/teacher/concepts/{concept_id}/draft", json={"count": 4}, headers=t)
    assert r.status_code == 200, r.text
    assert r.json() == {"explanations": 2, "items": 2, "dropped": 2, "reviewer_notes": DRAFT["reviewer_notes"]}

    sent = f.calls[0]
    assert "Speed = distance / time" in sent["messages"][0]["content"]  # grounded in the teacher's notes
    assert sent["output_config"]["format"]["type"] == "json_schema"

    # Drafts wait for review and are marked as AI drafts.
    queue = client.get("/teacher/review-queue", headers=t).json()
    mine = [i for i in queue["items"] if i["concept"] == "Speed"]
    assert len(mine) == 2 and all(i["source"] == "ai" and "km/h" in i["review_note"] for i in mine)
    with SessionLocal() as db:
        assert db.query(Item).filter_by(concept_id=concept_id, status="approved").count() == 0
        mcq = db.query(Item).filter_by(concept_id=concept_id, kind="mcq").one()
        assert mcq.misconceptions == {"240 km/h": "multiplied_instead"}

    # A teacher can fix a draft before approving it.
    item = next(i for i in mine if i["kind"] == "mcq")
    bad = {**item, "answer": "70 km/h"}
    assert client.put(f"/teacher/items/{item['id']}", json=bad, headers=t).status_code == 400
    fixed = {**item, "prompt": "A bus travels 120 km in 2 hours. What is its speed?"}
    assert client.put(f"/teacher/items/{item['id']}", json=fixed, headers=t).status_code == 200
    client.post(f"/teacher/items/{item['id']}/review", json={"decision": "approve"}, headers=t)
    assert client.put(f"/teacher/items/{item['id']}", json=fixed, headers=t).status_code == 409

    exp = next(e for e in queue["explanations"] if e["concept"] == "Speed")
    assert client.put(f"/teacher/explanations/{exp['id']}", json={"body": "Edited."}, headers=t).status_code == 200
    with SessionLocal() as db:
        assert db.get(Explanation, exp["id"]).body == "Edited."


def test_draft_skips_styles_already_approved(fake):
    f = fake(text=json.dumps({"explanations": [], "items": [], "reviewer_notes": ""}))
    t = login("teacher@demo.syniq")
    anu = login("anu@demo.syniq")
    concept_id = first_concept(anu)  # every style is approved for this demo topic
    client.post(f"/teacher/concepts/{concept_id}/draft", json={"count": 2}, headers=t)
    assert "(none needed)" in f.calls[0]["messages"][0]["content"]


def test_draft_unavailable_and_declined(fake, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    t = login("teacher@demo.syniq")
    assert client.post("/teacher/concepts/1/draft", json={}, headers=t).status_code == 503
    fake(stop_reason="refusal")
    assert client.post("/teacher/concepts/1/draft", json={}, headers=t).status_code == 422


def test_students_and_guardians_cannot_author(fake):
    fake(text="{}")
    anu = login("anu@demo.syniq")
    g = login("parent@demo.syniq")
    for h in (anu, g):
        assert client.post("/teacher/concepts/1/draft", json={}, headers=h).status_code == 403
        assert client.put("/teacher/concepts/1/notes", json={"notes": "x"}, headers=h).status_code == 403
