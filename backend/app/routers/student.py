from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import ai, learning
from ..auth import current_user, has_consent, require_learning_consent
from ..db import get_db
from ..engine.mastery import progress_label
from ..engine import detect, responses
from ..engine.rules import STYLES
from ..models import Attempt, Chapter, CheckIn, Concept, Decision, Explanation, Item, LearningEvent, Mastery, Subject, User

router = APIRouter(tags=["student"])

ALLOWED_SETTINGS = {
    "font_scale": (float, int),
    "high_contrast": bool,
    "dyslexia_font": bool,
    "reduced_motion": bool,
    "read_aloud": bool,
    "extra_time": bool,
    "preferred_style": (str, type(None)),
    "ui_language": str,
    "support_modes": list,  # chosen: screen_reader, visual_first, tap_to_answer
    "auto_off": list,  # noticed modes the student has switched off
}


# --- Curriculum browsing ------------------------------------------------------

@router.get("/subjects")
def list_subjects(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    subjects = db.scalars(select(Subject).order_by(Subject.id)).all()
    out = []
    for s in subjects:
        n = len(db.scalars(select(Chapter.id).where(Chapter.subject_id == s.id)).all())
        out.append({"id": s.id, "code": s.code, "name": s.name, "language": s.language, "chapters": n})
    return out


@router.get("/subjects/{subject_id}/chapters")
def list_chapters(subject_id: int, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    chapters = db.scalars(select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.number)).all()
    return [{"id": c.id, "number": c.number, "title": c.title} for c in chapters]


@router.get("/chapters/{chapter_id}")
def chapter_detail(chapter_id: int, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    concepts = db.scalars(select(Concept).where(Concept.chapter_id == chapter_id).order_by(Concept.order)).all()
    result = []
    for c in concepts:
        label = None
        if user.role == "student":
            row = db.scalars(
                select(Mastery).where(Mastery.student_id == user.id, Mastery.concept_id == c.id)
            ).first()
            label = progress_label(row.p_known, row.attempts) if row else "not_started"
        result.append({"id": c.id, "title": c.title, "progress": label})
    return {"id": chapter.id, "title": chapter.title, "concepts": result}


# --- Learning loop -------------------------------------------------------------

class NextRequest(BaseModel):
    chapter_id: int
    current_concept_id: int | None = None


@router.post("/learn/next")
def learn_next(body: NextRequest, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    if not db.get(Chapter, body.chapter_id):
        raise HTTPException(404, "Chapter not found")
    action, decision = learning.next_action(db, user, body.chapter_id, body.current_concept_id)
    concept = db.get(Concept, action.concept_id) if action.concept_id else None
    payload = {
        "decision_id": decision.id,
        "kind": action.kind,
        "reason": action.reason,
        "concept": {"id": concept.id, "title": concept.title} if concept else None,
        "offer_support": action.offer_support,
    }
    if action.kind == "explain" and concept:
        exp = learning.get_explanation(db, concept.id, action.style or "text")
        payload["explanation"] = {"style": exp.style, "body": exp.body} if exp else None
        payload["styles"] = STYLES
    elif action.kind in ("practice", "review", "prereq_review") and concept:
        item = learning.pick_item(db, user.id, concept.id, action.difficulty)
        payload["item"] = learning.public_item(item, user.settings) if item else None
    return payload


@router.get("/concepts/{concept_id}/explanations/{style}")
def explanation(concept_id: int, style: str, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    """The student can ask for any explanation style at any time."""
    if style not in STYLES:
        raise HTTPException(400, "Unknown style")
    exp = learning.get_explanation(db, concept_id, style)
    if not exp:
        raise HTTPException(404, "No approved explanation yet")
    if user.role == "student":
        db.add(
            Decision(
                student_id=user.id,
                concept_id=concept_id,
                rule_id="student_choice",
                rule_version="-",
                action="explain",
                reason="The student asked for this explanation style.",
                evidence={"style": exp.style},
            )
        )
        db.commit()
    return {"style": exp.style, "body": exp.body}


@router.get("/items/{item_id}/hints/{n}")
def hint(item_id: int, n: int, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    item = db.get(Item, item_id)
    if not item or item.status != "approved":
        raise HTTPException(404, "Item not found")
    if n < 1 or n > len(item.hints):
        raise HTTPException(404, "No more hints")
    return {"n": n, "hint": item.hints[n - 1], "remaining": len(item.hints) - n}


class AttemptIn(BaseModel):
    item_id: int
    response: str = Field(max_length=200)
    hints_used: int = Field(default=0, ge=0, le=10)
    time_ms: int | None = Field(default=None, ge=0)
    explanation_style: str | None = None


MISCONCEPTION_TIPS = {
    "square_each_term": "Squaring a sum is not the same as squaring each part: (a + b)² also has a middle term, 2ab.",
    "missing_double": "Check the middle term: it is 2ab, twice the product of the two terms.",
    "sign_middle": "In (a − b)² the middle term is negative: −2ab.",
    "sign_last": "The last term is b², and a square is never negative.",
    "sum_not_difference": "(a + b)(a − b) gives a difference of squares, a² − b², so the result has a minus sign.",
    "extra_middle_term": "In (a + b)(a − b) the middle terms cancel out, so there is no middle term.",
    "product_terms": "Multiply every term in the first bracket by every term in the second.",
    "arithmetic": "The method looks right; check the arithmetic in the last step.",
}


@router.post("/learn/attempts")
def submit_attempt(body: AttemptIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    item = db.get(Item, body.item_id)
    if not item or item.status != "approved":
        raise HTTPException(404, "Item not found")
    correct, misconception, row = learning.record_attempt(
        db, user, item, body.response, body.hints_used, body.time_ms, body.explanation_style
    )
    findings = learning.update_noticed_support(db, user)
    tip = None if correct else MISCONCEPTION_TIPS.get(misconception or "")
    explanations = db.scalars(
        select(Explanation).where(Explanation.concept_id == item.concept_id, Explanation.status == "approved")
    ).all()
    response = responses.build(
        responses.Context(
            prompt=item.prompt,
            answer=item.answer,
            response=body.response,
            correct=correct,
            solution=item.solution,
            misconception_tip=tip,
            wrong_in_a_row=row.wrong_streak,
            explanations={e.style: e.body for e in explanations},
            support=detect.effective_support(user.settings),
            tutor_available=ai.enabled(),
        ),
        seed=row.attempts,
    )
    response["adapted"] = [
        {"mode": f.mode, "message": detect.ANNOUNCE[f.mode].format(reason=f.reason) + " You can switch this off in Settings."}
        for f in findings
    ]
    if response["mode"]:
        attempt = db.scalars(
            select(Attempt).where(Attempt.student_id == user.id).order_by(Attempt.id.desc())
        ).first()
        attempt.feedback_mode = response["mode"]
        # Logged like every other adaptation, so "Why am I seeing this?" and audits can explain it.
        db.add(
            Decision(
                student_id=user.id,
                concept_id=item.concept_id,
                rule_id=f"F_{response['mode']}",
                rule_version=responses.RESPONSES_VERSION,
                action="feedback",
                reason=response["why"],
                evidence={"wrong_in_a_row": row.wrong_streak, "mistake": response.get("mistake") or misconception},
            )
        )
        db.commit()
    out = {
        "correct": correct,
        "progress": progress_label(row.p_known, row.attempts),
        "feedback": "Correct, well done." if correct else "Not quite yet.",
        "response": response,
    }
    if not correct:
        out["tip"] = tip
        out["solution"] = item.solution
    return out


class EventIn(BaseModel):
    kind: str = Field(pattern="^(read_aloud|break)$")


@router.post("/learn/events")
def learning_event(body: EventIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """A help button was pressed. Counts only; used to notice what helps."""
    db.add(LearningEvent(student_id=user.id, kind=body.kind))
    db.commit()
    return {"ok": True}


# --- Check-ins, settings, progress -------------------------------------------------

class CheckInIn(BaseModel):
    mood: str | None = Field(default=None, pattern="^(great|okay|low|frustrated)$")
    energy: str | None = Field(default=None, pattern="^(high|medium|low)$")


@router.post("/checkins")
def checkin(body: CheckInIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """Optional and self-reported. Skipping it changes nothing."""
    if not has_consent(db, user.id, "mood_checkins"):
        return {"stored": False, "message": "Thanks. Check-ins are not saved for your account."}
    db.add(CheckIn(student_id=user.id, mood=body.mood, energy=body.energy))
    db.commit()
    message = "Thanks for telling me."
    if body.mood in ("low", "frustrated") or body.energy == "low":
        message = "Thanks for telling me. We can start with something short, and you can take a break any time."
    return {"stored": True, "message": message}


@router.get("/me")
def me(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    out = {"id": user.id, "name": user.name, "role": user.role, "settings": user.settings or {}}
    if user.role == "student":
        out["consent"] = {
            "core_learning": has_consent(db, user.id, "core_learning"),
            "mood_checkins": has_consent(db, user.id, "mood_checkins"),
        }
    return out


@router.put("/me/settings")
def update_settings(body: dict, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Accessibility settings need no diagnosis and no approval."""
    settings = dict(user.settings or {})
    for key, value in body.items():
        expected = ALLOWED_SETTINGS.get(key)
        if expected is None or not isinstance(value, expected):
            raise HTTPException(400, f"Invalid setting: {key}")
        if key == "preferred_style" and value is not None and value not in STYLES:
            raise HTTPException(400, "Unknown style")
        if key == "support_modes" and not (all(isinstance(v, str) for v in value) and set(value) <= set(detect.CHOSEN)):
            raise HTTPException(400, "Unknown support mode")
        if key == "auto_off" and not (all(isinstance(v, str) for v in value) and set(value) <= set(detect.NOTICED)):
            raise HTTPException(400, "Unknown support mode")
        if key == "font_scale" and not 0.8 <= float(value) <= 2.0:
            raise HTTPException(400, "font_scale must be between 0.8 and 2.0")
        settings[key] = value
    user.settings = settings
    db.add(user)
    db.commit()
    return settings


@router.get("/me/progress")
def my_progress(user: User = Depends(require_learning_consent), db: DbSession = Depends(get_db)):
    rows = db.scalars(select(Mastery).where(Mastery.student_id == user.id)).all()
    concepts = {c.id: c for c in db.scalars(select(Concept)).all()}
    now = learning.utcnow()
    return [
        {
            "concept_id": r.concept_id,
            "title": concepts[r.concept_id].title,
            "progress": progress_label(r.p_known, r.attempts),
            "review_due": bool(r.next_review_at and r.next_review_at <= now),
        }
        for r in rows
        if r.attempts > 0
    ]


@router.get("/me/why/{decision_id}")
def why(decision_id: int, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """'Why am I seeing this?' in plain words."""
    d = db.get(Decision, decision_id)
    if not d or d.student_id != user.id:
        raise HTTPException(404, "Not found")
    return {"reason": d.reason, "rule": d.rule_id, "version": d.rule_version}
