"""Teacher content pipeline.

1. Set up a chapter and its topics, following the SCERT textbook.
2. Write notes for each topic: what the textbook covers and how.
3. Ask Claude to draft explanations and questions from those notes, or write them by hand.
4. Edit and approve in the review queue. Only approved content reaches students.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .. import ai
from ..auth import audit, require_role
from ..db import get_db
from ..engine.rules import STYLES
from ..models import Chapter, Concept, Explanation, Item, Subject, User

router = APIRouter(tags=["content"])
staff = require_role("teacher", "admin")


class ConceptIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=8000)


class ChapterIn(BaseModel):
    subject_id: int
    number: int = Field(ge=1, le=40)
    title: str = Field(min_length=1, max_length=200)
    concepts: list[ConceptIn] = Field(min_length=1, max_length=30)


@router.post("/teacher/chapters")
def create_chapter(body: ChapterIn, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    subject = db.get(Subject, body.subject_id)
    if not subject:
        raise HTTPException(404, "Subject not found")
    chapter = Chapter(subject_id=subject.id, number=body.number, title=body.title.strip())
    db.add(chapter)
    db.flush()
    for order, c in enumerate(body.concepts):
        # Codes only need to be unique; chapter id keeps them so across re-imports.
        db.add(Concept(chapter_id=chapter.id, code=f"{subject.code}9.c{chapter.id}.{order}", title=c.title.strip(), order=order, notes=c.notes))
    db.commit()
    audit(db, user, "create_chapter")
    return {"id": chapter.id}


def _counts(db: DbSession, model, concept_id: int) -> dict[str, int]:
    rows = db.execute(select(model.status, func.count()).where(model.concept_id == concept_id).group_by(model.status)).all()
    return {status: n for status, n in rows}


@router.get("/teacher/concepts/{concept_id}")
def concept_detail(concept_id: int, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    concept = db.get(Concept, concept_id)
    if not concept:
        raise HTTPException(404, "Topic not found")
    return {
        "id": concept.id,
        "title": concept.title,
        "notes": concept.notes,
        "items": _counts(db, Item, concept.id),
        "explanations": _counts(db, Explanation, concept.id),
    }


class NotesIn(BaseModel):
    notes: str = Field(max_length=8000)


@router.put("/teacher/concepts/{concept_id}/notes")
def save_notes(concept_id: int, body: NotesIn, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    concept = db.get(Concept, concept_id)
    if not concept:
        raise HTTPException(404, "Topic not found")
    concept.notes = body.notes
    db.commit()
    return {"id": concept.id, "notes": concept.notes}


class DraftIn(BaseModel):
    count: int = Field(default=6, ge=1, le=10)


def _clean_item(raw: dict) -> dict | None:
    """Keep only drafts the app can actually mark. Returns None to drop one."""
    kind, answer = raw["kind"], raw["answer"].strip()
    options = [o.strip() for o in raw["options"] if o.strip()]
    if not raw["prompt"].strip() or not answer:
        return None
    if kind == "mcq":
        if not 2 <= len(options) <= 5 or len(set(options)) != len(options) or answer not in options:
            return None
    else:
        try:
            float(answer)
        except ValueError:
            return None
        options = []
    return {
        "kind": kind,
        "prompt": raw["prompt"].strip(),
        "options": options,
        "answer": answer,
        "hints": [h.strip() for h in raw["hints"] if h.strip()][:3],
        "solution": raw["solution"].strip(),
        "difficulty": min(max(int(raw["difficulty"]), 1), 3),
        "misconceptions": {
            m["wrong_answer"].strip(): m["mistake"].strip()
            for m in raw["misconceptions"]
            if m["wrong_answer"].strip() and m["wrong_answer"].strip() != answer
        },
    }


@router.post("/teacher/concepts/{concept_id}/draft")
def draft(concept_id: int, body: DraftIn, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    """Ask Claude for draft explanations (for styles not yet approved) and questions."""
    concept = db.get(Concept, concept_id)
    if not concept:
        raise HTTPException(404, "Topic not found")
    chapter = db.get(Chapter, concept.chapter_id)
    subject = db.get(Subject, chapter.subject_id)
    approved = db.scalars(
        select(Explanation).where(Explanation.concept_id == concept.id, Explanation.status == "approved")
    ).all()
    have = {e.style for e in approved}
    try:
        result = ai.draft_content(
            subject=subject.name,
            chapter_number=chapter.number,
            chapter=chapter.title,
            concept=concept.title,
            notes=concept.notes,
            existing=[e.body for e in approved],
            styles=[s for s in STYLES if s not in have],
            count=body.count,
        )
    except ai.AIUnavailable as e:
        raise HTTPException(503, f"AI drafting isn't available: {e}")
    except ai.AIDeclined:
        raise HTTPException(422, "Claude declined to draft this topic. Please write it by hand or adjust the notes.")

    note = result.get("reviewer_notes", "").strip()
    added_exp = 0
    for e in result["explanations"]:
        if e["style"] in STYLES and e["style"] not in have and e["body"].strip():
            db.add(Explanation(concept_id=concept.id, style=e["style"], body=e["body"].strip(), status="draft", source="ai", review_note=note))
            have.add(e["style"])
            added_exp += 1
    added_items = dropped = 0
    for raw in result["items"]:
        clean = _clean_item(raw)
        if clean is None:
            dropped += 1
            continue
        db.add(Item(concept_id=concept.id, status="draft", source="ai", review_note=note, **clean))
        added_items += 1
    db.commit()
    audit(db, user, "ai_draft_content")
    return {"explanations": added_exp, "items": added_items, "dropped": dropped, "reviewer_notes": note}


# --- Editing drafts before approval -------------------------------------------------

class ItemEdit(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(default_factory=list, max_length=5)
    answer: str = Field(min_length=1, max_length=200)
    hints: list[str] = Field(default_factory=list, max_length=5)
    solution: str = Field(default="", max_length=4000)
    difficulty: int = Field(ge=1, le=3)


@router.put("/teacher/items/{item_id}")
def edit_item(item_id: int, body: ItemEdit, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if item.status != "draft":
        raise HTTPException(409, "Only drafts can be edited")
    options = [o.strip() for o in body.options if o.strip()]
    if item.kind == "mcq" and body.answer.strip() not in options:
        raise HTTPException(400, "The answer must be one of the options")
    item.prompt, item.options, item.answer = body.prompt.strip(), options, body.answer.strip()
    item.hints = [h.strip() for h in body.hints if h.strip()]
    item.solution, item.difficulty = body.solution.strip(), body.difficulty
    db.commit()
    return {"id": item.id}


class ExplanationEdit(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.put("/teacher/explanations/{exp_id}")
def edit_explanation(exp_id: int, body: ExplanationEdit, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    exp = db.get(Explanation, exp_id)
    if not exp:
        raise HTTPException(404, "Explanation not found")
    if exp.status != "draft":
        raise HTTPException(409, "Only drafts can be edited")
    exp.body = body.body.strip()
    db.commit()
    return {"id": exp.id}
