"""School-wide settings and records for the admin, today's chapter and raised hands for the lab.

Raised hands are a student's own request for help, so the class teacher sees the student's
name and topic even when the family doesn't share progress. Nothing else about practice is shown.
"""

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from .. import ai, learning, rewards
from ..auth import audit, current_user, require_role
from ..db import get_db
from ..models import (
    Attempt,
    Chapter,
    CheckIn,
    ClassGroup,
    Concept,
    Consent,
    FamilyMember,
    Goal,
    GuardianLink,
    HelpRequest,
    InterestReflection,
    LearningEvent,
    Mastery,
    Note,
    PuzzleAnswer,
    SchoolSetting,
    Session,
    Subject,
    SubjectCheck,
    TutorQuestion,
    User,
    utcnow,
)
from .lab import _day_start, _own_class

router = APIRouter()
admin_only = require_role("admin")

SETTING_KEYS = {"name": 120, "contact": 200, "rewards": 3}


def school_settings(db: DbSession) -> dict[str, str]:
    return {s.key: s.value for s in db.scalars(select(SchoolSetting)).all()}


@router.get("/school", tags=["school"])
def public_school(db: DbSession = Depends(get_db)):
    """Only the school's name, for the sign-in page. Nothing private."""
    return {"name": school_settings(db).get("name", "")}


@router.get("/admin/school", tags=["admin"])
def get_school(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    s = school_settings(db)
    return {k: s.get(k, "") for k in SETTING_KEYS}


class SchoolIn(BaseModel):
    name: str = Field(default="", max_length=120)
    contact: str = Field(default="", max_length=200)
    # Stickers and achievements for every student unless a parent chooses otherwise: "on" (default) or "off".
    rewards: str = Field(default="", pattern="^(|on|off)$")


@router.put("/admin/school", tags=["admin"])
def set_school(body: SchoolIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    for key in SETTING_KEYS:
        value = getattr(body, key).strip()
        row = db.get(SchoolSetting, key)
        if value and row:
            row.value = value
        elif value:
            db.add(SchoolSetting(key=key, value=value))
        elif row:
            db.delete(row)
    db.commit()
    audit(db, user, "set_school_details")
    return get_school(db, user)


# --- Students: fix a name or class -------------------------------------------------------

class StudentEdit(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    class_name: str | None = Field(default=None, min_length=1, max_length=80)


@router.put("/admin/students/{student_id}", tags=["admin"])
def edit_student(student_id: int, body: StudentEdit, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """A spelling fix, or a move to another class (made if it doesn't exist yet). The login stays the same."""
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(404, "Student not found")
    if body.name:
        student.name = body.name.strip()
    if body.class_name:
        name = body.class_name.strip()
        group = db.scalars(select(ClassGroup).where(ClassGroup.name == name)).first()
        if group is None:
            group = ClassGroup(name=name)
            db.add(group)
            db.flush()
        student.class_group_id = group.id
        db.execute(
            delete(HelpRequest).where(HelpRequest.student_id == student.id, HelpRequest.resolved_at.is_(None))
        )
    db.commit()
    audit(db, user, "edit_student", student.id)
    return {"id": student.id, "name": student.name, "class": db.get(ClassGroup, student.class_group_id).name}


# --- Records ---------------------------------------------------------------------------------

@router.get("/admin/consents.csv", response_class=PlainTextResponse, tags=["admin"])
def consent_register(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Every consent ever recorded, oldest first: the school's register, to keep with the paper forms."""
    people = {u.id: u for u in db.scalars(select(User)).all()}
    classes = {g.id: g.name for g in db.scalars(select(ClassGroup)).all()}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "student", "student_login", "class", "permission", "given", "how", "recorded_by"])
    for c in db.scalars(select(Consent).order_by(Consent.created_at, Consent.id)).all():
        s, by = people.get(c.student_id), people.get(c.guardian_id)
        w.writerow([
            c.created_at.isoformat(timespec="minutes"),
            s.name if s else "",
            s.email if s else "",
            classes.get(s.class_group_id, "") if s else "",
            c.scope,
            "yes" if c.granted else "no",
            c.method or "",
            f"{by.name} ({by.role})" if by else "",
        ])
    audit(db, user, "export_consent_register")
    return buf.getvalue()


def _rows(db: DbSession, model, col, sid: int) -> list[dict]:
    out = []
    for r in db.scalars(select(model).where(col == sid)).all():
        row = {}
        for c in model.__table__.columns:
            v = getattr(r, c.key)
            row[c.key] = v.isoformat() if hasattr(v, "isoformat") else v
        out.append(row)
    return out


@router.get("/admin/students/{student_id}/data", tags=["admin"])
def student_data(student_id: int, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Everything SYNiq holds about one student, for a family's request to see it (DPDP Act, section 11)."""
    s = db.get(User, student_id)
    if not s or s.role != "student":
        raise HTTPException(404, "Student not found")
    group = db.get(ClassGroup, s.class_group_id) if s.class_group_id else None
    concepts = {c.id: c.title for c in db.scalars(select(Concept)).all()}
    attempts = _rows(db, Attempt, Attempt.student_id, s.id)
    for a in attempts:
        a["topic"] = concepts.get(a["concept_id"], "")
    mastery = _rows(db, Mastery, Mastery.student_id, s.id)
    for m in mastery:
        m["topic"] = concepts.get(m["concept_id"], "")
    out = {
        "about": "Everything SYNiq holds about this student, exported by the school admin.",
        "exported_at": utcnow().isoformat(timespec="minutes"),
        "student": {"name": s.name, "login": s.email, "class": group.name if group else None, "settings": s.settings, "joined": s.created_at.isoformat(timespec="minutes")},
        "parents": [
            {"name": g.name, "login": g.email}
            for g in db.scalars(select(User).join(GuardianLink, GuardianLink.guardian_id == User.id).where(GuardianLink.student_id == s.id)).all()
        ],
        "consents": _rows(db, Consent, Consent.student_id, s.id),
        "answers": attempts,
        "topic_progress": mastery,
        "mood_check_ins": _rows(db, CheckIn, CheckIn.student_id, s.id),
        "goals": _rows(db, Goal, Goal.student_id, s.id),
        "notes": _rows(db, Note, Note.student_id, s.id),
        "interest_reflections": _rows(db, InterestReflection, InterestReflection.student_id, s.id),
        "thinking_puzzles": _rows(db, PuzzleAnswer, PuzzleAnswer.student_id, s.id),
        "subject_checks": _rows(db, SubjectCheck, SubjectCheck.student_id, s.id),
        "events": _rows(db, LearningEvent, LearningEvent.student_id, s.id),
        "help_requests": _rows(db, HelpRequest, HelpRequest.student_id, s.id),
        "rewards": {"on": rewards.rewards_on(db, s), "achievements": rewards.achievements(db, s.id), "stars": learning.stars(db, s.id)},
    }
    audit(db, user, "export_student_data", s.id)
    return out


@router.get("/admin/ai-usage", tags=["admin"])
def ai_usage(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Ask SYNiq today: how many questions went to the outside AI, and how many were saved unanswered."""
    start = _day_start(utcnow())
    counts = dict(
        db.execute(
            select(TutorQuestion.answered_by, func.count()).where(TutorQuestion.created_at >= start).group_by(TutorQuestion.answered_by)
        ).all()
    )
    return {
        "outside_ai_on": ai.enabled(),
        "provider": ai.provider_name(),
        "answered_by_outside_ai_today": counts.get("ai", 0),
        "saved_unanswered_today": counts.get("none", 0),
        "per_student_daily_limit": 20,
    }


# --- Today's chapter -------------------------------------------------------------------

class TodayChapterIn(BaseModel):
    chapter_id: int | None = None


def _today_chapter(db: DbSession, group: ClassGroup) -> dict | None:
    today = (utcnow() + timedelta(hours=5, minutes=30)).date()
    if not group.today_chapter_id or group.today_set_on != today:
        return None
    ch = db.get(Chapter, group.today_chapter_id)
    if not ch:
        return None
    return {"chapter_id": ch.id, "title": ch.title, "number": ch.number, "subject": db.get(Subject, ch.subject_id).name}


@router.put("/teacher/classes/{class_id}/today-chapter", tags=["teacher"])
def set_today_chapter(class_id: int, body: TodayChapterIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """The chapter for today's lab period. Students see it first; it clears itself tomorrow."""
    group = _own_class(db, user, class_id)
    if body.chapter_id is not None and not db.get(Chapter, body.chapter_id):
        raise HTTPException(404, "Chapter not found")
    group.today_chapter_id = body.chapter_id
    group.today_set_on = (utcnow() + timedelta(hours=5, minutes=30)).date() if body.chapter_id else None
    db.commit()
    return {"today_chapter": _today_chapter(db, group)}


@router.get("/teacher/classes/{class_id}/chapters", tags=["teacher"])
def class_chapters(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Chapters the class can choose from, by subject: those of its students' board and class."""
    from .. import learning

    _own_class(db, user, class_id)
    students = db.scalars(select(User).where(User.class_group_id == class_id, User.role == "student")).all()
    subjects = {sub.id: sub for st in students for sub in learning.subjects_for(db, st)}
    out = []
    for sid, sub in sorted(subjects.items()):
        for ch in db.scalars(select(Chapter).where(Chapter.subject_id == sid).order_by(Chapter.number)).all():
            out.append({"chapter_id": ch.id, "subject": sub.name, "number": ch.number, "title": ch.title})
    return out


@router.get("/me/lesson-today", tags=["student"])
def my_lesson_today(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    """Today's chapter from the class teacher, and whether this student's hand is up. Only for students in a school class."""
    if user.role != "student" or not user.class_group_id:
        return {"in_class": False, "today_chapter": None, "hand_up": False}
    group = db.get(ClassGroup, user.class_group_id)
    hand = db.scalars(select(HelpRequest).where(HelpRequest.student_id == user.id, HelpRequest.resolved_at.is_(None))).first()
    return {"in_class": True, "today_chapter": _today_chapter(db, group), "hand_up": hand is not None}


# --- Raised hands ----------------------------------------------------------------------

# The talk board: picture buttons for students who find it hard to speak up or ask out loud.
NEEDS = ("help", "dont_understand", "break", "too_loud", "finished", "toilet", "upset")


class HelpIn(BaseModel):
    concept_id: int | None = None
    need: str | None = None


@router.post("/me/help", tags=["student"])
def raise_hand(body: HelpIn, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    """'I need help': tells the class teacher, quietly. One open hand at a time."""
    if user.role != "student" or not user.class_group_id:
        raise HTTPException(400, "Only for students in a class")
    if body.need is not None and body.need not in NEEDS:
        raise HTTPException(400, "Unknown need")
    open_ = db.scalars(select(HelpRequest).where(HelpRequest.student_id == user.id, HelpRequest.resolved_at.is_(None))).first()
    if open_:
        open_.concept_id = body.concept_id or open_.concept_id
        # The newest press says what they need now.
        open_.need = body.need
    else:
        db.add(HelpRequest(student_id=user.id, class_group_id=user.class_group_id, concept_id=body.concept_id, need=body.need))
    db.commit()
    return {"hand_up": True}


@router.delete("/me/help", tags=["student"])
def lower_hand(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    for h in db.scalars(select(HelpRequest).where(HelpRequest.student_id == user.id, HelpRequest.resolved_at.is_(None))).all():
        h.resolved_at = utcnow()
    db.commit()
    return {"hand_up": False}


def open_hands(db: DbSession, class_id: int) -> list[dict]:
    """Raised hands in the last three hours, oldest first (first come, first helped)."""
    since = utcnow() - timedelta(hours=3)
    rows = db.scalars(
        select(HelpRequest)
        .where(HelpRequest.class_group_id == class_id, HelpRequest.resolved_at.is_(None), HelpRequest.created_at >= since)
        .order_by(HelpRequest.created_at)
    ).all()
    now = utcnow()
    out = []
    for h in rows:
        s = db.get(User, h.student_id)
        if not s or s.class_group_id != class_id:
            continue
        concept = db.get(Concept, h.concept_id) if h.concept_id else None
        out.append({"id": h.id, "name": s.name, "topic": concept.title if concept else None, "need": h.need, "minutes": int((now - h.created_at).total_seconds() // 60)})
    return out


@router.post("/teacher/help/{help_id}/done", tags=["teacher"])
def hand_done(help_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    h = db.get(HelpRequest, help_id)
    if not h:
        raise HTTPException(404, "Not found")
    _own_class(db, user, h.class_group_id)
    h.resolved_at = utcnow()
    db.commit()
    return {"ok": True}


# --- Withdrawal: parents left with no children -----------------------------------------------

def close_orphan_guardians(db: DbSession, guardian_ids: list[int]) -> int:
    """After a withdrawal, a school parent login with no children left is closed too.

    A family account holder (who may have other children at home, or a baby log) is left alone.
    """
    closed = 0
    for gid in guardian_ids:
        g = db.get(User, gid)
        if not g or g.role != "guardian":
            continue
        if db.scalars(select(GuardianLink.id).where(GuardianLink.guardian_id == gid)).first():
            continue
        if db.scalars(select(FamilyMember.id).where(FamilyMember.user_id == gid)).first():
            continue
        db.execute(delete(Session).where(Session.user_id == gid))
        g.name = "Former parent"
        g.email = f"withdrawn-{g.id}@removed.invalid"
        g.password_hash = "!"
        g.settings = {}
        g.role = "withdrawn"
        closed += 1
    return closed
