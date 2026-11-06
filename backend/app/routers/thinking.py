"""Thinking puzzles inside lessons, with the parent's consent. See app/thinking.py."""

import random

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import learning, thinking
from ..auth import audit, guardian_of, has_consent, require_learning_consent, require_role
from ..db import get_db
from ..models import PuzzleAnswer, User, utcnow

router = APIRouter(tags=["thinking puzzles"])

SCOPE = "thinking_puzzles"


def history(db: DbSession, student_id: int) -> list[PuzzleAnswer]:
    return db.scalars(select(PuzzleAnswer).where(PuzzleAnswer.student_id == student_id).order_by(PuzzleAnswer.id)).all()


def answers(rows: list[PuzzleAnswer]) -> list[thinking.Answer]:
    return [thinking.Answer(r.domain, r.level, r.correct) for r in rows]


def _today(rows: list[PuzzleAnswer]) -> int:
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return sum(r.created_at >= start for r in rows)


@router.get("/thinking/puzzle")
def puzzle(db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """A brain teaser if one is due; 204 when not (or when the parent hasn't switched puzzles on)."""
    if not has_consent(db, user.id, SCOPE):
        return Response(status_code=204)
    rows = history(db, user.id)
    _, grade = learning.class_of(user)
    if not thinking.due(len(rows), _today(rows), grade):
        return Response(status_code=204)
    past = answers(rows)
    domain = thinking.next_domain(past, grade)
    p = thinking.make(domain, thinking.level_for(domain, past, grade), random.randint(1, 10**6))
    # No domain, level or "test" wording reaches the app: to the child it's a brain teaser.
    return {"id": p.id, "prompt": p.prompt, "sequence": p.sequence, "options": p.options}


class PuzzleIn(BaseModel):
    id: str = Field(max_length=40)
    choice: str = Field(max_length=60)
    time_ms: int | None = Field(default=None, ge=0, le=3_600_000)


@router.post("/thinking/puzzle")
def answer(body: PuzzleIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    if not has_consent(db, user.id, SCOPE):
        raise HTTPException(404, "Not found")
    parsed = thinking.parse_id(body.id)
    if not parsed:
        raise HTTPException(400, "Unknown puzzle")
    p = thinking.make(*parsed)
    correct = body.choice == p.answer
    db.add(PuzzleAnswer(student_id=user.id, domain=p.domain, level=p.level, correct=correct, time_ms=body.time_ms))
    db.commit()
    return {"correct": correct, "answer": p.answer, "explain": p.explain}


def summary(db: DbSession, student: User) -> dict:
    rows = history(db, student.id)
    _, grade = learning.class_of(student)
    return {"puzzles": len(rows), "kinds": thinking.growth(answers(rows), grade)}


@router.get("/guardian/children/{student_id}/thinking", tags=["guardian"])
def child_thinking(student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Which kinds of thinking puzzle are growing, in words. Never a number or a comparison with others."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    if not has_consent(db, student_id, SCOPE):
        return {"on": False, "puzzles": 0, "kinds": []}
    audit(db, user, "view_child_thinking", student_id)
    return {"on": True, **summary(db, db.get(User, student_id))}
