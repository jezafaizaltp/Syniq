"""A demo learner with a week of real learning behind her, for showing SYNiq to people.

    python -m tools.demo_week          # from backend/, on a DEMO database only

It makes (or resets) "Meera" (meera@demo.syniq, password syniq-demo) in the demo class, then plays a week
through the app's own endpoints, so every screen shows something true to talk about:

- Day 1: the lesson on "Two numbers from their sum and difference". She misses idea 1, a second way of
  explaining it helps, and she finishes. Then practice, mostly right. The topic is later made secure and due
  for revision, so the mentor suggests revising it.
- Day 3: the lesson on elimination, then practice where she twice forgets to divide at the end: a repeat
  mistake, so the mentor's first step is to fix it. She gets the topic right later too ("came back").
- Day 5: the lesson on making coefficients match, then three wrong in a row: the mentor suggests learning it
  again another way.
- Anu and Rahul (demo classmates) also miss idea 1 of the first lesson, so the teacher's re-teach sheet lists it.

Then sign in as meera@demo.syniq (mentor, This week, Before you go), parent@demo.syniq (This week for Meera)
or teacher@demo.syniq (re-teach sheet). It refuses to run where there is no demo class, so it can't touch a
school's real data.
"""

from __future__ import annotations

import sys
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal
from app.main import app
from app.models import (
    Attempt,
    ClassGroup,
    Concept,
    Consent,
    Decision,
    GuardianLink,
    Item,
    LearningEvent,
    Mastery,
    User,
    utcnow,
)
from app.routers.lab import _STUDENT_ROWS
from app.seed import DEMO_PASSWORD

EMAIL = "meera@demo.syniq"
DEMO_CLASS = "Class 9 A (demo)"
client = TestClient(app)


def login(email: str) -> dict:
    r = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


def make_meera() -> int:
    with SessionLocal() as db:
        group = db.scalars(select(ClassGroup).where(ClassGroup.name == DEMO_CLASS)).first()
        parent = db.scalars(select(User).where(User.email == "parent@demo.syniq")).first()
        if not group or not parent:
            sys.exit("No demo class here: this only runs on a demo database (python -m app.seed).")
        meera = db.scalars(select(User).where(User.email == EMAIL)).first()
        if meera:
            for model, column in _STUDENT_ROWS:
                if model not in (Consent,):
                    db.query(model).filter(column == meera.id).delete()
            db.commit()
        else:
            meera = User(name="Meera", email=EMAIL, password_hash=hash_password(DEMO_PASSWORD), role="student", class_group_id=group.id)
            db.add(meera)
            db.flush()
            db.add(GuardianLink(guardian_id=parent.id, student_id=meera.id))
            for scope in ("core_learning", "mood_checkins", "school_sharing", "thinking_puzzles"):
                db.add(Consent(student_id=meera.id, guardian_id=parent.id, scope=scope, granted=True, method="school_form"))
        meera.settings = {"welcome_seen": True}
        db.commit()
        return meera.id


def concept(code: str) -> Concept:
    with SessionLocal() as db:
        c = db.scalars(select(Concept).where(Concept.code == code)).first()
        if not c:
            sys.exit(f"Topic {code} is not loaded: load the Kerala Class 9 packs first.")
        return c


def lesson(h: dict, cid: int, miss: set[int] = frozenset()) -> None:
    """Go through a topic's lesson: missed ideas get a wrong first answer, then right after the second way."""
    steps = client.get(f"/learn/lesson/{cid}", headers=h).json()["steps"]
    with SessionLocal() as db:
        checks = [s["check"] for s in db.get(Concept, cid).lesson]
    first_time = 0
    for n, (step, check) in enumerate(zip(steps, checks)):
        ways = [w["style"] for w in step.get("ways") or [{"style": "text"}]]
        body = {"concept_id": cid, "step": n, "style": ways[0], "attempt": 1, "can_retry": True}
        if n in miss:
            wrong = next(o for o in check["options"] if o != check["answer"])
            client.post("/learn/lesson-check", json={**body, "choice": wrong}, headers=h)
            second = ways[1] if len(ways) > 1 else ways[0]
            client.post("/learn/lesson-check", json={**body, "choice": check["answer"], "style": second, "attempt": 2}, headers=h)
        else:
            client.post("/learn/lesson-check", json={**body, "choice": check["answer"]}, headers=h)
            first_time += 1
    client.post("/learn/lesson-done", json={"concept_id": cid, "steps": len(steps), "first_time": first_time}, headers=h)


def items(cid: int) -> list[Item]:
    with SessionLocal() as db:
        return db.scalars(select(Item).where(Item.concept_id == cid, Item.status == "approved").order_by(Item.difficulty, Item.id)).all()


def answer(h: dict, item: Item, right: bool, trap: str | None = None) -> None:
    if right:
        response = item.answer
    else:
        wrongs = [w for w, t in (item.misconceptions or {}).items() if trap is None or t == trap]
        response = wrongs[0] if wrongs else "0"
    client.post("/learn/attempts", json={"item_id": item.id, "response": str(response), "hints_used": 0}, headers=h).raise_for_status()


def with_trap(cid: int, trap: str) -> list[Item]:
    return [i for i in items(cid) if trap in (i.misconceptions or {}).values()]


def days_ago(sid: int, since: dict[str, int], days: int) -> dict[str, int]:
    """Move everything Meera did since the last mark back by `days`, so the week reads as a week."""
    shift = timedelta(days=days)
    with SessionLocal() as db:
        marks = {}
        for model in (Attempt, LearningEvent, Decision):
            rows = db.scalars(select(model).where(model.student_id == sid, model.id > since.get(model.__name__, 0))).all()
            for r in rows:
                r.created_at = r.created_at - shift
            marks[model.__name__] = max([r.id for r in rows], default=since.get(model.__name__, 0))
        db.commit()
        return marks


def main() -> None:
    sid = make_meera()
    h = login(EMAIL)
    a, b, c = (concept(x) for x in ("math9.pairs.sum_difference", "math9.pairs.elimination", "math9.pairs.make_match"))
    marks: dict[str, int] = {}

    # Day 1: a lesson where a second way helps, then practice.
    lesson(h, a.id, miss={0})
    for n, it in enumerate(items(a.id)[:8]):
        answer(h, it, right=n != 2)
    marks = days_ago(sid, marks, 6)

    # Day 3: elimination, with the same slip twice (forgetting to divide at the end), then right later.
    lesson(h, b.id)
    trap = with_trap(b.id, "forgot_divide")
    plain = [i for i in items(b.id) if i not in trap]
    answer(h, plain[0], right=True)
    answer(h, trap[0], right=False, trap="forgot_divide")
    answer(h, plain[1], right=True)
    answer(h, trap[1], right=False, trap="forgot_divide")
    answer(h, plain[2], right=True)
    marks = days_ago(sid, marks, 4)

    # Day 5: making coefficients match, and three wrong in a row.
    lesson(h, c.id, miss={1})
    for it in items(c.id)[:3]:
        answer(h, it, right=False)
    marks = days_ago(sid, marks, 1)

    # The first topic, practised well, is secure and now due for revision.
    with SessionLocal() as db:
        row = db.scalars(select(Mastery).where(Mastery.student_id == sid, Mastery.concept_id == a.id)).first()
        now = utcnow()
        row.p_known, row.attempts, row.wrong_streak = 0.985, max(row.attempts, 8), 0
        row.secured_at, row.next_review_at, row.review_count = now - timedelta(days=5), now - timedelta(hours=3), 1
        row.updated_at = now - timedelta(days=6)
        db.commit()

    # Two classmates miss the same lesson idea, so the teacher's re-teach sheet has something to show.
    for email in ("anu@demo.syniq", "rahul@demo.syniq"):
        try:
            lesson(login(email), a.id, miss={0})
        except Exception:  # noqa: BLE001 - a demo nicety, never a reason to stop
            pass

    plan = client.get("/me/mentor", headers=h).json()
    print("Meera is ready: meera@demo.syniq /", DEMO_PASSWORD)
    for s in plan["steps"]:
        print(" -", s["kind"], s.get("topic") or s.get("chapter"))
    print(" this week:", {k: v for k, v in plan["week"].items() if v})


if __name__ == "__main__":
    main()
