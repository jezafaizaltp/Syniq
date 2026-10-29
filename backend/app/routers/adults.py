"""Teacher, guardian and auth endpoints.

No endpoint here returns a ranked or ordered list of students by ability, and
self-reported check-ins are never exposed to teachers.
"""

from collections import Counter

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..auth import (
    MIN_PASSWORD,
    audit,
    clear_login_failures,
    current_user,
    guardian_of,
    has_consent,
    hash_password,
    login_blocked,
    new_token,
    record_login_failure,
    require_role,
    verify_password,
)
from .. import i18n
from ..db import get_db
from ..engine import detect
from ..engine.mastery import progress_label
from ..models import (
    Attempt,
    ClassGroup,
    Concept,
    Consent,
    Explanation,
    GuardianLink,
    Item,
    Mastery,
    Session,
    User,
)

router = APIRouter()


# --- Auth ------------------------------------------------------------------------

class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/login", tags=["auth"])
def login(body: LoginIn, request: Request, db: DbSession = Depends(get_db), lang: str = Depends(i18n.language)):
    login_id = body.email.lower().strip()
    key = f"{login_id}|{request.client.host if request.client else ''}"
    if login_blocked(key):
        raise HTTPException(429, i18n.t(lang, "err.too_many_tries"))
    user = db.scalars(select(User).where(User.email == login_id)).first()
    if not user or not verify_password(body.password, user.password_hash):
        record_login_failure(key)
        raise HTTPException(401, i18n.t(lang, "err.wrong_login"))
    clear_login_failures(key)
    return {"token": new_token(db, user), "role": user.role, "name": user.name}


@router.post("/auth/logout", tags=["auth"])
def logout(authorization: str = Header(default=""), db: DbSession = Depends(get_db)):
    sess = db.get(Session, authorization.removeprefix("Bearer ").strip())
    if sess:
        db.delete(sess)
        db.commit()
    return {"ok": True}


class PasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=MIN_PASSWORD, max_length=200)


@router.post("/me/password", tags=["auth"])
def change_password(
    body: PasswordIn, db: DbSession = Depends(get_db), user: User = Depends(current_user), lang: str = Depends(i18n.language)
):
    if not verify_password(body.current, user.password_hash):
        raise HTTPException(400, i18n.t(lang, "err.current_password"))
    if body.new == body.current:
        raise HTTPException(400, i18n.t(lang, "err.same_password"))
    user.password_hash = hash_password(body.new)
    user.must_change_password = False
    # Sign out everywhere else.
    for other in db.scalars(select(Session).where(Session.user_id == user.id)).all():
        db.delete(other)
    db.commit()
    return {"token": new_token(db, user)}


# --- Teacher -----------------------------------------------------------------------

def _teacher_class(db: DbSession, teacher: User, class_id: int) -> ClassGroup:
    group = db.get(ClassGroup, class_id)
    if not group or (teacher.role == "teacher" and group.teacher_id != teacher.id):
        raise HTTPException(404, "Class not found")
    return group


def _shared_students(db: DbSession, class_id: int) -> list[User]:
    """Students in the class whose guardians allow sharing with the school."""
    students = db.scalars(select(User).where(User.class_group_id == class_id, User.role == "student")).all()
    return [s for s in students if has_consent(db, s.id, "school_sharing")]


@router.get("/teacher/classes", tags=["teacher"])
def my_classes(db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    q = select(ClassGroup)
    if user.role == "teacher":
        q = q.where(ClassGroup.teacher_id == user.id)
    return [{"id": g.id, "name": g.name} for g in db.scalars(q).all()]


@router.get("/teacher/classes/{class_id}/overview", tags=["teacher"])
def class_overview(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Per concept: how many students are at each stage. Counts, not rankings."""
    _teacher_class(db, user, class_id)
    students = _shared_students(db, class_id)
    ids = [s.id for s in students]
    concepts = db.scalars(select(Concept).order_by(Concept.chapter_id, Concept.order)).all()
    rows = db.scalars(select(Mastery).where(Mastery.student_id.in_(ids))).all() if ids else []
    by_concept: dict[int, list[Mastery]] = {}
    for r in rows:
        by_concept.setdefault(r.concept_id, []).append(r)

    concept_out = []
    for c in concepts:
        labels = Counter(progress_label(r.p_known, r.attempts) for r in by_concept.get(c.id, []))
        labels["not_started"] += len(ids) - sum(labels.values())
        miscon = Counter()
        for r in by_concept.get(c.id, []):
            miscon.update(r.misconceptions or {})
        concept_out.append(
            {
                "concept_id": c.id,
                "title": c.title,
                "counts": {k: labels.get(k, 0) for k in ("not_started", "learning", "getting_there", "secure")},
                "common_misconceptions": [m for m, _ in miscon.most_common(3)],
            }
        )
    audit(db, user, "view_class_overview")
    return {"students": len(ids), "concepts": concept_out}


@router.get("/teacher/classes/{class_id}/support", tags=["teacher"])
def may_need_support(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Students who have been stuck on a concept, listed alphabetically, with the concept."""
    _teacher_class(db, user, class_id)
    out = []
    for s in sorted(_shared_students(db, class_id), key=lambda x: x.name):
        stuck = db.scalars(
            select(Mastery).where(Mastery.student_id == s.id, Mastery.attempts >= 4, Mastery.p_known < 0.4)
        ).all()
        if stuck:
            titles = [db.get(Concept, r.concept_id).title for r in stuck]
            out.append({"student_id": s.id, "name": s.name, "concepts": titles})
    audit(db, user, "view_support_list")
    return out


@router.get("/teacher/review-queue", tags=["teacher"])
def review_queue(db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    items = db.scalars(select(Item).where(Item.status == "draft")).all()
    exps = db.scalars(select(Explanation).where(Explanation.status == "draft")).all()
    return {
        "items": [
            {
                "id": i.id,
                "concept": db.get(Concept, i.concept_id).title,
                "kind": i.kind,
                "prompt": i.prompt,
                "options": i.options,
                "answer": i.answer,
                "hints": i.hints,
                "solution": i.solution,
                "difficulty": i.difficulty,
                "source": i.source,
                "review_note": i.review_note,
            }
            for i in items
        ],
        "explanations": [
            {
                "id": e.id,
                "concept": db.get(Concept, e.concept_id).title,
                "style": e.style,
                "body": e.body,
                "source": e.source,
                "review_note": e.review_note,
            }
            for e in exps
        ],
    }


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


@router.post("/teacher/items/{item_id}/review", tags=["teacher"])
def review_item(item_id: int, body: ReviewIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.status = "approved" if body.decision == "approve" else "rejected"
    item.reviewed_by = user.id
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/teacher/explanations/{exp_id}/review", tags=["teacher"])
def review_explanation(exp_id: int, body: ReviewIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    exp = db.get(Explanation, exp_id)
    if not exp:
        raise HTTPException(404, "Explanation not found")
    exp.status = "approved" if body.decision == "approve" else "rejected"
    db.commit()
    return {"id": exp.id, "status": exp.status}


# --- Guardian ----------------------------------------------------------------------

@router.get("/guardian/children", tags=["guardian"])
def children(db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian")), lang: str = Depends(i18n.language)):
    links = db.scalars(select(GuardianLink).where(GuardianLink.guardian_id == user.id)).all()
    out = []
    for link in links:
        child = db.get(User, link.student_id)
        out.append(
            {
                "id": child.id,
                "name": child.name,
                "consent": {
                    scope: has_consent(db, child.id, scope)
                    for scope in ("core_learning", "mood_checkins", "school_sharing")
                },
                "support_modes": (child.settings or {}).get("support_modes", []),
                "noticed": [
                    {"mode": mode, "reason": i18n.translate_english(lang, v["reason"]), "on": mode not in (child.settings or {}).get("auto_off", [])}
                    for mode, v in (child.settings or {}).get("auto_support", {}).items()
                ],
            }
        )
    return out


@router.get("/guardian/children/{student_id}/progress", tags=["guardian"])
def child_progress(
    student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian")), lang: str = Depends(i18n.language)
):
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    rows = db.scalars(select(Mastery).where(Mastery.student_id == student_id, Mastery.attempts > 0)).all()
    practised = len(db.scalars(select(Attempt.id).where(Attempt.student_id == student_id)).all())
    audit(db, user, "view_child_progress", student_id)
    return {
        "questions_practised": practised,
        "note": i18n.t(lang, "parent.progress_note"),
        "concepts": [
            {"title": db.get(Concept, r.concept_id).title, "progress": progress_label(r.p_known, r.attempts)}
            for r in rows
        ],
    }


class SupportIn(BaseModel):
    modes: list[str] = Field(max_length=3)


@router.put("/guardian/children/{student_id}/support", tags=["guardian"])
def set_support(student_id: int, body: SupportIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Support for sight, hearing or speech, which SYNiq can't tell from answers."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    if not set(body.modes) <= set(detect.CHOSEN):
        raise HTTPException(400, "Unknown support mode")
    child = db.get(User, student_id)
    child.settings = {**(child.settings or {}), "support_modes": body.modes}
    db.commit()
    audit(db, user, "set_child_support", student_id)
    return {"support_modes": body.modes}


class ConsentIn(BaseModel):
    scope: str = Field(pattern="^(core_learning|mood_checkins|school_sharing)$")
    granted: bool
    method: str = "in_app"


@router.post("/guardian/children/{student_id}/consent", tags=["guardian"])
def set_consent(student_id: int, body: ConsentIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    db.add(Consent(student_id=student_id, guardian_id=user.id, scope=body.scope, granted=body.granted, method=body.method))
    db.commit()
    return {"scope": body.scope, "granted": body.granted}

