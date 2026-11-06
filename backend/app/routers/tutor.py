"""Ask SYNiq: the tutor for the topic the student is working on.

It answers from the topic's own approved content first (app.tutor_local), with
no outside call and no cost. Only a question that content doesn't cover goes
to the outside AI, if one is switched on, and that is limited per student per day.

The conversation lives only in the student's browser. The server keeps a daily
count of outside-AI questions and, with no student details, the questions the
content didn't cover, so it can be added to.
"""

from collections import defaultdict
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import ai, i18n, tutor_local
from ..auth import current_user, require_learning_consent
from ..db import get_db
from ..models import Chapter, Concept, Explanation, Subject, TutorQuestion, User

router = APIRouter(tags=["tutor"])

# Questions per student per day that go to the outside AI. Answers from SYNiq's own content are unlimited.
DAILY_LIMIT = 20
_usage: dict[tuple[int, date], int] = defaultdict(int)


@router.get("/ai/status")
def status(user: User = Depends(current_user)):
    # The tutor always works from SYNiq's own content; "ai" says whether harder questions can go further.
    return {"enabled": True, "ai": ai.enabled()}


class Turn(BaseModel):
    role: Literal["student", "tutor"]
    text: str = Field(min_length=1, max_length=2000)


class TutorIn(BaseModel):
    concept_id: int
    history: list[Turn] = Field(min_length=1, max_length=12)
    # A quick button the student pressed instead of typing.
    action: Literal["explain", "picture", "example", "steps", "test", "hint"] | None = None
    # What the tutor needs to remember between messages (styles shown, the question it asked). Sent back each time.
    state: dict[str, Any] = Field(default_factory=dict)
    # The question being marked on the Learn page: the tutor gives hints for it, never the answer.
    item_id: int | None = None


def _out(r: tutor_local.Reply) -> dict:
    return {"reply": r.text, "source": r.source, "picture": r.picture, "style": r.style, "quiz": r.quiz, "chips": r.chips, "state": r.state}


def _save_question(db: DbSession, concept_id: int, text: str, answered_by: str) -> None:
    db.add(TutorQuestion(concept_id=concept_id, text=ai.scrub(text)[:600], answered_by=answered_by))
    db.commit()


@router.post("/tutor")
def ask(
    body: TutorIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent), lang: str = Depends(i18n.language)
):
    latest = body.history[-1]
    if latest.role != "student" or len(latest.text) > 600:
        raise HTTPException(400, i18n.t(lang, "err.tutor_too_long"))
    concept = db.get(Concept, body.concept_id)
    if not concept:
        raise HTTPException(404, "Topic not found")
    if ai.distressed(latest.text):
        return _out(tutor_local.Reply(i18n.t(lang, "tutor.distress"), chips=[], state=body.state))
    own = tutor_local.reply(
        db, user, concept, latest.text, lang, action=body.action, state=body.state, current_item_id=body.item_id
    )
    if own is not None:
        return _out(own)
    unsure = tutor_local.unsure(concept, lang, body.state)
    key = (user.id, date.today())
    if not ai.enabled() or _usage[key] >= DAILY_LIMIT:
        _save_question(db, concept.id, latest.text, "none")
        return _out(unsure)
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
            lang=lang,
        )
    except ai.AIUnavailable:
        _save_question(db, concept.id, latest.text, "none")
        return _out(unsure)
    except ai.AIDeclined:
        reply = i18n.t(lang, "tutor.declined")
    _usage[key] += 1
    _save_question(db, concept.id, latest.text, "ai")
    return _out(tutor_local.Reply(reply, source="ai", state=body.state))
