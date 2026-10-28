"""Ask SYNiq: the AI tutor for the topic the student is working on.

The conversation lives only in the student's browser. The server forwards it to
Claude with the topic's approved content and keeps nothing but a daily count.
"""

from collections import defaultdict
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import ai
from ..auth import current_user, require_learning_consent
from ..db import get_db
from ..models import Chapter, Concept, Explanation, Subject, User

router = APIRouter(tags=["tutor"])

DAILY_LIMIT = 60
_usage: dict[tuple[int, date], int] = defaultdict(int)


@router.get("/ai/status")
def status(user: User = Depends(current_user)):
    return {"enabled": ai.enabled()}


class Turn(BaseModel):
    role: Literal["student", "tutor"]
    text: str = Field(min_length=1, max_length=2000)


class TutorIn(BaseModel):
    concept_id: int
    history: list[Turn] = Field(min_length=1, max_length=12)


@router.post("/tutor")
def ask(body: TutorIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    latest = body.history[-1]
    if latest.role != "student" or len(latest.text) > 600:
        raise HTTPException(400, "Please ask a question of up to 600 characters")
    concept = db.get(Concept, body.concept_id)
    if not concept:
        raise HTTPException(404, "Topic not found")
    key = (user.id, date.today())
    if _usage[key] >= DAILY_LIMIT:
        raise HTTPException(429, "That's a lot of questions for one day. Try the explanations, or ask your teacher.")
    chapter = db.get(Chapter, concept.chapter_id)
    subject = db.get(Subject, chapter.subject_id)
    explanations = db.scalars(
        select(Explanation).where(Explanation.concept_id == concept.id, Explanation.status == "approved")
    ).all()
    try:
        reply = ai.tutor_reply(
            subject=subject.name,
            chapter=chapter.title,
            concept=concept.title,
            notes=concept.notes,
            explanations=[e.body for e in explanations],
            history=[t.model_dump() for t in body.history],
        )
    except ai.AIUnavailable:
        raise HTTPException(503, "The tutor isn't available right now. The explanations and hints still work.")
    except ai.AIDeclined:
        reply = "I can't help with that one. Let's get back to the topic. What part would you like me to explain?"
    _usage[key] += 1
    return {"reply": reply}
