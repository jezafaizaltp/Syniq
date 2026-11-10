"""Ask SYNiq answering from the topic's own content, with no AI."""

import pytest
from sqlalchemy import select

from app import ai
from app.db import SessionLocal
from app.models import Decision, Item, TutorQuestion
from tests.test_api import client, login
from tests.test_tutor_and_content import UNCOVERED, first_concept


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    ai.set_client(None)


class Chat:
    def __init__(self, headers, concept_id=None, item_id=None):
        self.h, self.state, self.history, self.item_id = headers, {}, [], item_id
        self.concept_id = concept_id or first_concept(headers)

    def say(self, text, action=None):
        self.history.append({"role": "student", "text": text})
        r = client.post(
            "/tutor",
            json={"concept_id": self.concept_id, "history": self.history[-12:], "action": action, "state": self.state, "item_id": self.item_id},
            headers=self.h,
        )
        assert r.status_code == 200, r.text
        out = r.json()
        self.state = out["state"]
        self.history.append({"role": "tutor", "text": out["reply"]})
        return out


def test_explains_every_way_then_asks_what_is_unclear():
    anu = login("anu@demo.syniq")
    chat = Chat(anu)
    styles = [chat.say("I don't understand", "explain")["style"] for _ in range(4)]
    assert sorted(styles) == ["real_world", "step_by_step", "text", "visual"]
    assert "every way" in chat.say("still confused", "explain")["reply"]
    # Each explanation is logged, so the next answers count towards that method for this student.
    with SessionLocal() as db:
        logged = db.scalars(select(Decision).where(Decision.rule_id == "T_tutor_explain", Decision.concept_id == chat.concept_id)).all()
        assert {d.evidence["style"] for d in logged} >= set(styles)


def test_picture_example_and_steps_on_request():
    anu = login("anu@demo.syniq")
    chat = Chat(anu)
    assert chat.say("can you show me a picture")["style"] == "visual"
    assert chat.say("give me a real life example")["style"] == "real_world"
    assert chat.say("step by step please")["style"] == "step_by_step"
    assert chat.say("hi")["source"] == "notes"


def test_what_is_answered_from_the_notes():
    anu = login("anu@demo.syniq")
    r = Chat(anu).say("why is there a 2ab?")
    assert r["source"] == "notes" and "2ab" in r["reply"]


def test_test_me_checks_the_answer_and_turns_a_mistake_into_the_way_in():
    anu = login("anu@demo.syniq")
    chat = Chat(anu)
    q = chat.say("Test me", "test")
    assert q["quiz"] and q["state"]["quiz"]
    with SessionLocal() as db:
        item = db.get(Item, q["state"]["quiz"])
        right, hints = item.answer, list(item.hints)
    wrong = chat.say("12345")
    assert "You said 12345" in wrong["reply"] and wrong["state"].get("quiz")
    assert right not in wrong["reply"]  # not the answer on the first miss
    again = chat.say("12345")
    assert f"The answer is {right}" in again["reply"] and "quiz" not in again["state"]
    q2 = chat.say("Test me", "test")
    with SessionLocal() as db:
        right2 = db.get(Item, q2["state"]["quiz"]).answer
    assert "right" in chat.say(right2)["reply"]


def test_hints_for_the_question_on_the_learn_page_never_give_the_answer():
    anu = login("anu@demo.syniq")
    concept = first_concept(anu)
    with SessionLocal() as db:
        item = db.scalars(select(Item).where(Item.concept_id == concept, Item.status == "approved")).first()
        answer, n = item.answer, len(item.hints)
    chat = Chat(anu, concept, item_id=item.id)
    replies = [chat.say("just tell me the answer")["reply"]] + [chat.say("hint", "hint")["reply"] for _ in range(n + 2)]
    assert all(f"answer is {answer}" not in r and "Here's the working" not in r for r in replies)
    assert "after you answer" in replies[-1]


def test_uncovered_question_saved_without_student_details_for_admin():
    anu = login("anu@demo.syniq")
    r = Chat(anu).say(UNCOVERED + " call me on 98470 12345")
    assert r["source"] == "none" and "saved your question" in r["reply"]
    with SessionLocal() as db:
        saved = db.scalars(select(TutorQuestion).order_by(TutorQuestion.id.desc())).first()
        assert "Babylonian" in saved.text and "98470" not in saved.text and saved.answered_by == "none"
        assert not hasattr(saved, "student_id")
    admin = login("admin@demo.syniq")
    topics = client.get("/admin/tutor-questions", headers=admin).json()
    assert any("Babylonian" in q["text"] for t in topics for q in t["questions"])
    assert client.get("/admin/tutor-questions", headers=anu).status_code == 403
    # Marking it handled moves it off the open list and onto the handled one.
    qid = next(q["id"] for t in topics for q in t["questions"] if "Babylonian" in q["text"])
    assert client.post("/admin/tutor-questions/handled", json={"ids": [qid]}, headers=admin).json() == {"changed": 1}
    open_ids = {q["id"] for t in client.get("/admin/tutor-questions", headers=admin).json() for q in t["questions"]}
    done = client.get("/admin/tutor-questions?show=handled", headers=admin).json()
    assert qid not in open_ids and any(q["id"] == qid and q["handled"] for t in done for q in t["questions"])
    client.post("/admin/tutor-questions/handled", json={"ids": [qid], "handled": False}, headers=admin)
    assert qid in {q["id"] for t in client.get("/admin/tutor-questions", headers=admin).json() for q in t["questions"]}
    assert client.post("/admin/tutor-questions/handled", json={"ids": [qid]}, headers=anu).status_code == 403


def test_chat_with_the_tutor_is_not_answered_from_notes():
    anu = login("anu@demo.syniq")
    assert Chat(anu).say("what is your name")["source"] == "none"


def test_distress_still_gets_the_helpline():
    anu = login("anu@demo.syniq")
    assert "14416" in Chat(anu).say("I want to hurt myself")["reply"]


def test_openai_used_only_when_notes_dont_cover_it(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Let's think about it together."}, "finish_reason": "stop"}]}

    def fake_post(url, **kw):
        calls.append(kw["json"])
        return FakeResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "post", fake_post)
    anu = login("anu@demo.syniq")
    chat = Chat(anu)
    assert chat.say("why is there a 2ab?")["source"] == "notes" and calls == []
    r = chat.say(UNCOVERED)
    assert r["source"] == "ai" and r["reply"] == "Let's think about it together."
    assert len(calls) == 1 and calls[0]["model"] == ai.OPENAI_MODEL


def test_free_cloudflare_fallback(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Good question. What do you already know?"}, "finish_reason": "stop"}]}

    def fake_post(url, **kw):
        calls.append((url, kw["headers"], kw["json"]))
        return FakeResponse()

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc123")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cf-token")
    monkeypatch.setattr(ai.httpx, "post", fake_post)
    anu = login("anu@demo.syniq")
    r = Chat(anu).say(UNCOVERED)
    assert r["source"] == "ai"
    url, headers, body = calls[0]
    assert url == "https://api.cloudflare.com/client/v4/accounts/acc123/ai/v1/chat/completions"
    assert headers["Authorization"] == "Bearer cf-token" and body["model"] == ai.CLOUDFLARE_MODEL
    assert "anu" not in str(body).lower()
