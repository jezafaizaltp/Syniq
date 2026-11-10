"""Lab-period tools: what the class did today, new passwords, ending the period, and a student's own day.

Teachers see sign-in status for every student in their own class (that is running the lab, not
learning data). What a student practised is shown only when the family shares progress with the
school. Nothing here ranks students: lists are alphabetical and counts are for the class.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from ..auth import audit, current_user, has_consent, hash_password, require_role, temporary_password
from ..db import get_db
from ..models import (
    AssessmentScore,
    Attempt,
    CheckIn,
    ClassGroup,
    Concept,
    Consent,
    Decision,
    Goal,
    GuardianLink,
    InterestReflection,
    LearningEvent,
    Mastery,
    Note,
    PuzzleAnswer,
    Session,
    SpecialistLink,
    SubjectCheck,
    User,
    utcnow,
)
from ..engine.mastery import progress_label
from ..evaluation import MIN_GROUP

router = APIRouter()

QUIET_DAYS = 7


def _day_start(now: datetime) -> datetime:
    """Start of today in India (UTC+05:30), as naive UTC like the rest of the database."""
    ist = now + timedelta(hours=5, minutes=30)
    return datetime(ist.year, ist.month, ist.day) - timedelta(hours=5, minutes=30)


def _own_class(db: DbSession, user: User, class_id: int) -> ClassGroup:
    group = db.get(ClassGroup, class_id)
    if not group or (user.role == "teacher" and group.teacher_id != user.id):
        raise HTTPException(404, "Class not found")
    return group


def _students(db: DbSession, class_id: int) -> list[User]:
    return sorted(
        db.scalars(select(User).where(User.class_group_id == class_id, User.role == "student")).all(), key=lambda s: s.name
    )


@router.get("/teacher/classes/{class_id}/today", tags=["teacher"])
def class_today(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """The lab period at a glance: who has signed in, who practised today, who has been quiet."""
    group = _own_class(db, user, class_id)
    now = utcnow()
    start = _day_start(now)
    quiet_since = now - timedelta(days=QUIET_DAYS)
    students, active, answers, topics = [], 0, 0, set()
    for s in _students(db, class_id):
        shared = has_consent(db, s.id, "school_sharing")
        row = {"id": s.id, "name": s.name, "login": s.email, "first_sign_in_pending": s.must_change_password, "shared": shared}
        if shared:
            today = db.scalars(select(Attempt).where(Attempt.student_id == s.id, Attempt.created_at >= start)).all()
            last = db.scalars(select(Attempt.created_at).where(Attempt.student_id == s.id).order_by(Attempt.created_at.desc())).first()
            row["answered_today"] = len(today)
            row["quiet"] = not s.must_change_password and (last is None or last < quiet_since)
            if today:
                active += 1
                answers += len(today)
                topics |= {a.concept_id for a in today}
        students.append(row)
    audit(db, user, "view_class_today")
    return {
        "class": group.name,
        "students": students,
        "today": {"active": active, "answers": answers, "topics": len(topics)},
        "quiet_days": QUIET_DAYS,
    }


@router.post("/teacher/classes/{class_id}/students/{student_id}/reset-password", tags=["teacher"])
def teacher_reset_password(
    class_id: int, student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))
):
    """A forgotten password in the middle of a lab period: the class teacher gives a new temporary one."""
    _own_class(db, user, class_id)
    student = db.get(User, student_id)
    if not student or student.role != "student" or student.class_group_id != class_id:
        raise HTTPException(404, "Student not found")
    pw = temporary_password()
    student.password_hash = hash_password(pw)
    student.must_change_password = True
    db.execute(delete(Session).where(Session.user_id == student.id))
    db.commit()
    audit(db, user, "reset_password", student.id)
    return {"name": student.name, "login": student.email, "temporary_password": pw}


@router.post("/teacher/classes/{class_id}/end-period", tags=["teacher"])
def end_period(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Sign every student in the class out, so the next class can't open their accounts on shared computers."""
    _own_class(db, user, class_id)
    ids = [s.id for s in _students(db, class_id)]
    n = db.execute(delete(Session).where(Session.user_id.in_(ids))).rowcount if ids else 0
    db.commit()
    audit(db, user, "end_lab_period")
    return {"signed_out": n}


@router.get("/me/today", tags=["student"])
def my_today(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    """A student's own day, said back to them before they sign out. No marks."""
    if user.role != "student":
        raise HTTPException(403, "Only for students")
    start = _day_start(utcnow())
    today = db.scalars(select(Attempt).where(Attempt.student_id == user.id, Attempt.created_at >= start)).all()
    topics = []
    for cid in dict.fromkeys(a.concept_id for a in today):
        concept = db.get(Concept, cid)
        m = db.scalars(select(Mastery).where(Mastery.student_id == user.id, Mastery.concept_id == cid)).first()
        topics.append({"title": concept.title, "progress": progress_label(m.p_known, m.attempts) if m else "learning"})
    return {"answered": len(today), "right": sum(a.correct for a in today), "topics": topics}


# Rows that belong to one student, in an order that respects foreign keys.
_STUDENT_ROWS = [
    (Attempt, Attempt.student_id),
    (Decision, Decision.student_id),
    (LearningEvent, LearningEvent.student_id),
    (Mastery, Mastery.student_id),
    (CheckIn, CheckIn.student_id),
    (Goal, Goal.student_id),
    (Note, Note.student_id),
    (InterestReflection, InterestReflection.student_id),
    (PuzzleAnswer, PuzzleAnswer.student_id),
    (SubjectCheck, SubjectCheck.student_id),
    (AssessmentScore, AssessmentScore.student_id),
    (SpecialistLink, SpecialistLink.student_id),
]


@router.post("/admin/students/{student_id}/withdraw", tags=["admin"])
def withdraw_student(student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("admin"))):
    """A family withdraws: the login stops working and everything SYNiq learned about the child is deleted.

    The consent history stays (with a final 'withdrawn' row for every scope) and so does the audit log,
    because both show what was allowed and who did what. The name is replaced, so neither names the child.
    """
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(404, "Student not found")
    for model, col in _STUDENT_ROWS:
        db.execute(delete(model).where(col == student.id))
    db.execute(delete(Session).where(Session.user_id == student.id))
    scopes = {c.scope for c in db.scalars(select(Consent).where(Consent.student_id == student.id)).all()}
    for scope in sorted(scopes):
        db.add(Consent(student_id=student.id, guardian_id=user.id, scope=scope, granted=False, method="withdrawn"))
    db.execute(delete(GuardianLink).where(GuardianLink.student_id == student.id))
    student.name = "Withdrawn student"
    student.email = f"withdrawn-{student.id}@removed.invalid"
    student.password_hash = "!"
    student.settings = {}
    student.class_group_id = None
    student.role = "withdrawn"
    db.commit()
    audit(db, user, "withdraw_student", student.id)
    return {"ok": True}


@router.get("/admin/usage", tags=["admin"])
def weekly_usage(db: DbSession = Depends(get_db), user: User = Depends(require_role("admin"))):
    """How much SYNiq was used each week of the pilot, for the report. Counts only, never names.

    A week (Monday to Sunday, India time) with fewer than five active students shows no numbers,
    so a small week can't point to one child.
    """
    rows = db.execute(
        select(Attempt.student_id, Attempt.concept_id, Attempt.created_at)
        .join(User, User.id == Attempt.student_id)
        .where(User.role == "student", User.class_group_id.is_not(None))
    ).all()
    weeks: dict[str, dict] = {}
    for sid, cid, at in rows:
        local = at + timedelta(hours=5, minutes=30)
        monday = (local - timedelta(days=local.weekday())).date().isoformat()
        w = weeks.setdefault(monday, {"students": set(), "answers": 0, "topics": set(), "days": set()})
        w["students"].add(sid)
        w["answers"] += 1
        w["topics"].add(cid)
        w["days"].add(local.date())
    out = []
    for monday in sorted(weeks):
        w = weeks[monday]
        small = len(w["students"]) < MIN_GROUP
        out.append(
            {
                "week_of": monday,
                "active_students": None if small else len(w["students"]),
                "answers": None if small else w["answers"],
                "topics": None if small else len(w["topics"]),
                "days_used": len(w["days"]),
                "hidden": small,
            }
        )
    audit(db, user, "view_weekly_usage")
    return {"min_group": MIN_GROUP, "weeks": out}
