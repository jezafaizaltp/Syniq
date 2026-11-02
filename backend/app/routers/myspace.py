"""The student's own space: progress in words, revision due, their goals and their notes.

Goals and notes are the student's alone. Teachers, parents and the engine never read
them, and the student can delete them at any time.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .. import learning
from ..auth import require_learning_consent, require_role
from ..db import get_db
from ..engine.mastery import progress_label
from ..models import Chapter, Concept, Goal, Mastery, Note, Subject, User, utcnow

router = APIRouter(prefix="/me", tags=["my space"])
student_only = require_role("student")

MAX_OPEN_GOALS = 20
MAX_NOTES = 500
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/overview")
def overview(user: User = Depends(require_learning_consent), db: DbSession = Depends(get_db)):
    """Per subject: topics secure, getting there and learning; where to carry on; what is due for revision."""
    rows = db.scalars(select(Mastery).where(Mastery.student_id == user.id, Mastery.attempts > 0)).all()
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.id.in_({r.concept_id for r in rows}))).all()}
    chapters = {c.id: c for c in db.scalars(select(Chapter).where(Chapter.id.in_({c.chapter_id for c in concepts.values()}))).all()}
    subjects = {s.id: s for s in db.scalars(select(Subject)).all()}
    now = learning.utcnow()

    per_subject: dict[int, dict] = {}
    due = []
    for r in sorted(rows, key=lambda r: r.updated_at or now, reverse=True):
        concept = concepts[r.concept_id]
        chapter = chapters[concept.chapter_id]
        subject = subjects[chapter.subject_id]
        label = progress_label(r.p_known, r.attempts)
        entry = per_subject.setdefault(
            subject.id,
            {
                "id": subject.id,
                "name": subject.name,
                "secure": 0,
                "getting_there": 0,
                "learning": 0,
                # The most recently practised chapter: where to carry on.
                "carry_on": {"chapter_id": chapter.id, "title": chapter.title},
            },
        )
        entry[label] += 1
        if r.next_review_at and r.next_review_at <= now:
            due.append(
                {
                    "concept_id": concept.id,
                    "title": concept.title,
                    "chapter_id": chapter.id,
                    "chapter": chapter.title,
                    "subject": subject.name,
                }
            )
    return {"subjects": sorted(per_subject.values(), key=lambda s: s["id"]), "review_due": due}


# --- Goals --------------------------------------------------------------------

class GoalIn(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    due_on: str | None = None

    @field_validator("text")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Write a goal")
        return v

    @field_validator("due_on")
    @classmethod
    def date(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if not DATE.match(v):
            raise ValueError("Use a date like 2026-12-01")
        return v


class GoalUpdate(BaseModel):
    done: bool | None = None
    text: str | None = Field(default=None, min_length=1, max_length=200)


def _goal_out(g: Goal) -> dict:
    return {"id": g.id, "text": g.text, "due_on": g.due_on, "done": g.done}


@router.get("/goals")
def list_goals(user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    goals = db.scalars(select(Goal).where(Goal.student_id == user.id).order_by(Goal.done, Goal.id.desc())).all()
    return [_goal_out(g) for g in goals]


@router.post("/goals")
def add_goal(body: GoalIn, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    open_goals = db.scalar(select(func.count()).select_from(Goal).where(Goal.student_id == user.id, Goal.done.is_(False)))
    if open_goals >= MAX_OPEN_GOALS:
        raise HTTPException(400, f"You have {MAX_OPEN_GOALS} goals on the go. Finish or remove one first.")
    g = Goal(student_id=user.id, text=body.text, due_on=body.due_on)
    db.add(g)
    db.commit()
    return _goal_out(g)


def _own_goal(db: DbSession, user: User, goal_id: int) -> Goal:
    g = db.get(Goal, goal_id)
    if not g or g.student_id != user.id:
        raise HTTPException(404, "Goal not found")
    return g


@router.put("/goals/{goal_id}")
def update_goal(goal_id: int, body: GoalUpdate, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    g = _own_goal(db, user, goal_id)
    if body.done is not None:
        g.done = body.done
    if body.text is not None and body.text.strip():
        g.text = body.text.strip()
    db.commit()
    return _goal_out(g)


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: int, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    db.delete(_own_goal(db, user, goal_id))
    db.commit()
    return Response(status_code=204)


# --- Notes --------------------------------------------------------------------

class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    concept_id: int | None = None


def _note_out(db: DbSession, n: Note) -> dict:
    concept = db.get(Concept, n.concept_id) if n.concept_id else None
    return {
        "id": n.id,
        "body": n.body,
        "concept_id": n.concept_id,
        "topic": concept.title if concept else None,
        "updated_at": n.updated_at.isoformat(timespec="minutes"),
    }


@router.get("/notes")
def list_notes(concept_id: int | None = None, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    q = select(Note).where(Note.student_id == user.id)
    if concept_id is not None:
        q = q.where(Note.concept_id == concept_id)
    return [_note_out(db, n) for n in db.scalars(q.order_by(Note.updated_at.desc(), Note.id.desc())).all()]


@router.post("/notes")
def add_note(body: NoteIn, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    if not body.body.strip():
        raise HTTPException(400, "Write something first")
    if body.concept_id is not None and not db.get(Concept, body.concept_id):
        raise HTTPException(404, "Topic not found")
    if db.scalar(select(func.count()).select_from(Note).where(Note.student_id == user.id)) >= MAX_NOTES:
        raise HTTPException(400, f"You have {MAX_NOTES} notes. Remove some old ones first.")
    n = Note(student_id=user.id, concept_id=body.concept_id, body=body.body.strip())
    db.add(n)
    db.commit()
    return _note_out(db, n)


def _own_note(db: DbSession, user: User, note_id: int) -> Note:
    n = db.get(Note, note_id)
    if not n or n.student_id != user.id:
        raise HTTPException(404, "Note not found")
    return n


@router.put("/notes/{note_id}")
def edit_note(note_id: int, body: NoteIn, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    n = _own_note(db, user, note_id)
    if not body.body.strip():
        raise HTTPException(400, "Write something first")
    n.body = body.body.strip()
    n.updated_at = utcnow()
    db.commit()
    return _note_out(db, n)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, user: User = Depends(student_only), db: DbSession = Depends(get_db)):
    db.delete(_own_note(db, user, note_id))
    db.commit()
    return Response(status_code=204)
