"""Specialist view: a school counsellor or special educator sees a child only when a parent shares them.

What a specialist sees is about support, not ranking: the support switched on and why,
progress per subject in words, the mistakes that keep coming back, and which help buttons
the child uses. Never mood check-ins, marks, goals, notes or Explore reflections, and never
a diagnosis. Every share, stop and view is in the audit log.
"""

from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import i18n
from ..auth import audit, guardian_of, hash_password, require_role, temporary_password
from ..db import get_db
from ..engine.mastery import progress_label
from ..models import Attempt, Chapter, Concept, LearningEvent, Mastery, Misconception, SpecialistLink, Subject, User, utcnow

router = APIRouter(tags=["specialists"])
RECENT = timedelta(days=14)


def _active(db: DbSession, **where) -> list[SpecialistLink]:
    q = select(SpecialistLink).where(SpecialistLink.ended_at.is_(None))
    for k, v in where.items():
        q = q.where(getattr(SpecialistLink, k) == v)
    return db.scalars(q).all()


# --- School admin adds specialists ---------------------------------------------------

class SpecialistIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    title: str = Field(default="School counsellor", min_length=1, max_length=80)


@router.post("/admin/specialists")
def add_specialist(body: SpecialistIn, db: DbSession = Depends(get_db), admin: User = Depends(require_role("admin"))):
    email = body.email.lower()
    if db.scalars(select(User.id).where(User.email == email)).first():
        raise HTTPException(409, "Someone already uses that email")
    pw = temporary_password()
    user = User(
        name=body.name.strip(), email=email, password_hash=hash_password(pw), role="specialist",
        settings={"title": body.title.strip()}, must_change_password=True,
    )
    db.add(user)
    db.commit()
    audit(db, admin, "add_specialist")
    return {"name": user.name, "login": user.email, "temporary_password": pw}


def _specialists(db: DbSession) -> list[User]:
    return db.scalars(select(User).where(User.role == "specialist").order_by(User.name)).all()


@router.get("/admin/specialists")
def list_specialists(db: DbSession = Depends(get_db), admin: User = Depends(require_role("admin"))):
    return [
        {"id": s.id, "name": s.name, "title": (s.settings or {}).get("title", ""), "login": s.email, "children": len(_active(db, specialist_id=s.id))}
        for s in _specialists(db)
    ]


# --- Parents share and stop sharing ---------------------------------------------------

@router.get("/guardian/specialists")
def guardian_specialists(db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """The school's specialists, and which of the parent's children each can see."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "title": (s.settings or {}).get("title", ""),
            "shared_with": [link.student_id for link in _active(db, specialist_id=s.id) if guardian_of(db, user, link.student_id)],
        }
        for s in _specialists(db)
    ]


class ShareIn(BaseModel):
    share: bool


@router.put("/guardian/children/{student_id}/specialists/{specialist_id}")
def share_with_specialist(
    student_id: int, specialist_id: int, body: ShareIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))
):
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    spec = db.get(User, specialist_id)
    if not spec or spec.role != "specialist":
        raise HTTPException(404, "Specialist not found")
    current = _active(db, specialist_id=specialist_id, student_id=student_id)
    if body.share and not current:
        db.add(SpecialistLink(specialist_id=specialist_id, student_id=student_id, guardian_id=user.id))
        db.commit()
        audit(db, user, f"share_with_specialist:{spec.name}", student_id)
    elif not body.share and current:
        for link in current:
            link.ended_at = utcnow()
        db.commit()
        audit(db, user, f"stop_sharing_with_specialist:{spec.name}", student_id)
    return {"shared": body.share}


# --- What the specialist sees -------------------------------------------------------

def _tip(tag: str, tips: dict[str, str]) -> str | None:
    if i18n.has(f"tip.{tag}"):
        return i18n.t("en", f"tip.{tag}")
    return tips.get(tag)


def _summary(db: DbSession, student: User) -> dict:
    settings = student.settings or {}
    rows = db.scalars(select(Mastery).where(Mastery.student_id == student.id, Mastery.attempts > 0)).all()
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.id.in_({r.concept_id for r in rows}))).all()}
    chapters = {c.id: c for c in db.scalars(select(Chapter).where(Chapter.id.in_({c.chapter_id for c in concepts.values()}))).all()}
    subjects = {s.id: s.name for s in db.scalars(select(Subject)).all()}

    per_subject: dict[str, Counter] = {}
    mistakes: Counter = Counter()
    for r in rows:
        name = subjects[chapters[concepts[r.concept_id].chapter_id].subject_id]
        per_subject.setdefault(name, Counter())[progress_label(r.p_known, r.attempts)] += 1
        mistakes.update(r.misconceptions or {})
    tips = {m.tag: m.tip for m in db.scalars(select(Misconception).where(Misconception.tag.in_(list(mistakes)))).all()}

    since = utcnow() - RECENT
    helps = Counter(db.scalars(select(LearningEvent.kind).where(LearningEvent.student_id == student.id, LearningEvent.created_at >= since)).all())
    modes = Counter(
        m for m in db.scalars(select(Attempt.feedback_mode).where(Attempt.student_id == student.id, Attempt.created_at >= since)).all() if m
    )
    return {
        "id": student.id,
        "name": student.name,
        "chosen_support": settings.get("support_modes", []),
        "noticed_support": [
            {"mode": mode, "reason": v.get("reason", ""), "since": v.get("since", "")[:10], "on": mode not in settings.get("auto_off", [])}
            for mode, v in settings.get("auto_support", {}).items()
        ],
        "settings": {k: settings[k] for k in ("font_scale", "high_contrast", "dyslexia_font", "reduced_motion", "read_aloud", "extra_time", "preferred_style") if settings.get(k)},
        "subjects": [{"subject": k, **dict(v)} for k, v in sorted(per_subject.items())],
        "repeated_mistakes": [{"tag": tag, "times": n, "tip": _tip(tag, tips)} for tag, n in mistakes.most_common(5)],
        "last_14_days": {"read_aloud": helps.get("read_aloud", 0), "breaks": helps.get("break", 0), "responses": dict(modes)},
    }


@router.get("/specialist/students")
def my_students(db: DbSession = Depends(get_db), user: User = Depends(require_role("specialist"))):
    out = []
    for link in _active(db, specialist_id=user.id):
        student = db.get(User, link.student_id)
        out.append(_summary(db, student))
        audit(db, user, "view_student_as_specialist", student.id)
    return sorted(out, key=lambda s: s["name"])
