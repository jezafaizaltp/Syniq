"""School setup for the pilot: accounts, classes and paper consent.

The school's admin uploads one spreadsheet (CSV) with a row per student. SYNiq
creates the student, their parent or guardian, the class, and records the
consent from the paper form. Every new account gets a temporary password,
shown once on a printable sheet, that must be changed at first sign-in.

Marks or ability groups used to choose pilot students are never uploaded.
"""

import csv
import io
import re
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..auth import audit, has_consent, hash_password, require_role, temporary_password
from ..db import get_db
from ..models import AuditLog, Chapter, ClassGroup, Concept, Consent, GuardianLink, Session, Subject, TutorQuestion, User

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role("admin")

SCOPES = ("core_learning", "mood_checkins", "school_sharing", "thinking_puzzles")
COLUMNS = {
    "student_name": "Student's full name",
    "class": "Class, e.g. 9 A",
    "guardian_name": "Parent or guardian's name",
    "guardian_email": "Parent's email (optional; used as their login)",
    "guardian_phone": "Parent's phone (optional; only used to keep siblings under one parent, not saved)",
    "consent_learning": "yes if the paper form allows SYNiq for learning",
    "consent_mood": "yes if the form allows saving mood check-ins",
    "consent_school": "yes if the form allows sharing progress with the school",
    "consent_puzzles": "optional: yes if the form allows thinking puzzles and own-pace timing",
}
TEMPLATE = ",".join(COLUMNS) + "\nAnu Krishna,9 A,Lakshmi Krishna,lakshmi@example.com,,yes,yes,yes,yes\n"
YES = {"yes", "y", "true", "1", "ok", "agreed"}
NO = {"no", "n", "false", "0", ""}


@router.get("/csv-template", response_class=PlainTextResponse)
def csv_template(user: User = Depends(admin_only)):
    return TEMPLATE


def _slug(name: str) -> str:
    first = (name.strip().split() or ["user"])[0].lower()
    return re.sub(r"[^a-z]", "", first)[:12] or "user"


def _unique_login(db: DbSession, base: str, taken: set[str]) -> str:
    while True:
        login = f"{base}{secrets.randbelow(900) + 100}"
        if login not in taken and not db.scalars(select(User.id).where(User.email == login)).first():
            taken.add(login)
            return login


class ImportIn(BaseModel):
    csv: str = Field(max_length=500_000)
    dry_run: bool = True


@router.post("/import")
def import_students(body: ImportIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Check (dry_run) or create every account in the sheet. All rows or none."""
    reader = csv.DictReader(io.StringIO(body.csv.lstrip("﻿")))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in ("student_name", "class", "guardian_name") if c not in headers]
    if missing:
        raise HTTPException(400, f"The sheet needs these columns: {', '.join(missing)}")

    errors, rows = [], []
    for n, raw in enumerate(reader, start=2):  # row 1 is the header
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(r.values()):
            continue
        problems = [f"{c.replace('_', ' ')} is empty" for c in ("student_name", "class", "guardian_name") if not r.get(c)]
        consents = {}
        for scope, col in zip(SCOPES, ("consent_learning", "consent_mood", "consent_school", "consent_puzzles")):
            value = r.get(col, "").lower()
            if col == "consent_puzzles" and not value:
                value = "no"  # added later: older sheets without this column still import
            if value not in YES | NO:
                problems.append(f"{col} should be yes or no, not '{r.get(col)}'")
            consents[scope] = value in YES
        email = r.get("guardian_email", "").lower()
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            problems.append(f"'{email}' doesn't look like an email address")
        if problems:
            errors.append({"row": n, "problems": problems})
        rows.append({**r, "guardian_email": email, "consents": consents, "row": n})

    if errors or body.dry_run:
        classes = sorted({r["class"] for r in rows})
        return {
            "ok": not errors,
            "errors": errors,
            "students": len(rows),
            "classes": classes,
            "without_learning_consent": sum(not r["consents"]["core_learning"] for r in rows),
            "dry_run": True,
        }

    taken: set[str] = set()
    groups = {g.name: g for g in db.scalars(select(ClassGroup)).all()}
    guardians: dict[str, tuple[User, str | None]] = {}  # key -> (user, temp password if new)
    accounts = []
    for r in rows:
        group = groups.get(r["class"])
        if group is None:
            group = groups[r["class"]] = ClassGroup(name=r["class"])
            db.add(group)
            db.flush()

        student_pw = temporary_password()
        student = User(
            name=r["student_name"], email=_unique_login(db, _slug(r["student_name"]), taken),
            password_hash=hash_password(student_pw), role="student", class_group_id=group.id,
            settings={}, must_change_password=True,
        )
        db.add(student)

        # Siblings share one parent account: same email, or same name and phone in this sheet.
        phone = re.sub(r"\D", "", r.get("guardian_phone", ""))
        key = r["guardian_email"] or f"{r['guardian_name'].lower()}|{phone}"
        if key not in guardians:
            existing = db.scalars(select(User).where(User.email == r["guardian_email"])).first() if r["guardian_email"] else None
            if existing:
                guardians[key] = (existing, None)
            else:
                pw = temporary_password()
                g = User(
                    name=r["guardian_name"],
                    email=r["guardian_email"] or _unique_login(db, "parent-" + _slug(r["guardian_name"]), taken),
                    password_hash=hash_password(pw), role="guardian", settings={}, must_change_password=True,
                )
                db.add(g)
                guardians[key] = (g, pw)
        guardian, guardian_pw = guardians[key]
        db.flush()
        db.add(GuardianLink(guardian_id=guardian.id, student_id=student.id))
        for scope, granted in r["consents"].items():
            db.add(Consent(student_id=student.id, guardian_id=guardian.id, scope=scope, granted=granted, method="paper_form"))
        accounts.append({
            "class": group.name, "student": student.name, "student_login": student.email, "student_password": student_pw,
            "guardian": guardian.name, "guardian_login": guardian.email,
            "guardian_password": guardian_pw if guardian_pw else "(already has an account, or see above)",
            "learning_consent": r["consents"]["core_learning"],
        })
        if guardian_pw:
            # Show a new parent's password once, on their first child's row.
            guardians[key] = (guardian, None)
    db.commit()
    audit(db, user, f"import_students:{len(accounts)}")
    return {"ok": True, "errors": [], "dry_run": False, "accounts": accounts}


@router.get("/people")
def people(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Everyone in the school, by class. No progress or ability data here."""
    groups = db.scalars(select(ClassGroup).order_by(ClassGroup.name)).all()
    teachers = db.scalars(select(User).where(User.role == "teacher").order_by(User.name)).all()
    out = []
    for g in groups:
        students = db.scalars(select(User).where(User.class_group_id == g.id, User.role == "student").order_by(User.name)).all()
        out.append({
            "id": g.id, "name": g.name,
            "teacher": next((t.name for t in teachers if t.id == g.teacher_id), None),
            "students": [
                {
                    "id": s.id, "name": s.name, "login": s.email, "first_sign_in_pending": s.must_change_password,
                    "consent": {scope: has_consent(db, s.id, scope) for scope in SCOPES},
                    "guardians": [
                        {"id": gu.id, "name": gu.name, "login": gu.email, "first_sign_in_pending": gu.must_change_password}
                        for gu in db.scalars(
                            select(User).join(GuardianLink, GuardianLink.guardian_id == User.id).where(GuardianLink.student_id == s.id)
                        ).all()
                    ],
                }
                for s in students
            ],
        })
    return {
        "classes": out,
        "teachers": [{"id": t.id, "name": t.name, "login": t.email, "first_sign_in_pending": t.must_change_password} for t in teachers],
    }


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """A new temporary password, for a student, parent or teacher who has forgotten theirs."""
    target = db.get(User, user_id)
    if not target or target.role == "admin":
        raise HTTPException(404, "Not found")
    pw = temporary_password()
    target.password_hash = hash_password(pw)
    target.must_change_password = True
    for s in db.scalars(select(Session).where(Session.user_id == target.id)).all():
        db.delete(s)
    db.commit()
    audit(db, user, "reset_password", target.id if target.role == "student" else None)
    return {"name": target.name, "login": target.email, "temporary_password": pw}


class TeacherIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    classes: list[str] = Field(default_factory=list, max_length=20)


@router.post("/teachers")
def add_teacher(body: TeacherIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    email = body.email.lower()
    if db.scalars(select(User.id).where(User.email == email)).first():
        raise HTTPException(409, "Someone already uses that email")
    pw = temporary_password()
    teacher = User(name=body.name.strip(), email=email, password_hash=hash_password(pw), role="teacher", settings={}, must_change_password=True)
    db.add(teacher)
    db.flush()
    for name in body.classes:
        group = db.scalars(select(ClassGroup).where(ClassGroup.name == name.strip())).first()
        if group is None:
            group = ClassGroup(name=name.strip())
            db.add(group)
        group.teacher_id = teacher.id
    db.commit()
    audit(db, user, "add_teacher")
    return {"name": teacher.name, "login": teacher.email, "temporary_password": pw}


class PaperConsentIn(BaseModel):
    scope: str = Field(pattern="^(core_learning|mood_checkins|school_sharing|thinking_puzzles)$")
    granted: bool


@router.post("/students/{student_id}/consent")
def record_paper_consent(student_id: int, body: PaperConsentIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Record a change a parent made on paper. Parents can also change consent themselves."""
    link = db.scalars(select(GuardianLink).where(GuardianLink.student_id == student_id)).first()
    if not link:
        raise HTTPException(404, "No parent linked to this student")
    db.add(Consent(student_id=student_id, guardian_id=link.guardian_id, scope=body.scope, granted=body.granted, method="paper_form"))
    db.commit()
    audit(db, user, f"paper_consent:{body.scope}:{'yes' if body.granted else 'no'}", student_id)
    return {"scope": body.scope, "granted": body.granted}


# --- Syllabus ---------------------------------------------------------------------------

SYLLABUS_COLUMNS = ("subject", "chapter_number", "chapter_title", "topic")
SYLLABUS_TEMPLATE = ",".join(SYLLABUS_COLUMNS) + "\nmath,1,Pairs of Equations,Equations with two unknowns\nmath,1,Pairs of Equations,Solving a pair of equations\n"


@router.get("/syllabus-template", response_class=PlainTextResponse)
def syllabus_template(user: User = Depends(admin_only)):
    return SYLLABUS_TEMPLATE


class SyllabusIn(BaseModel):
    csv: str = Field(max_length=500_000)
    dry_run: bool = True


@router.post("/syllabus")
def import_syllabus(body: SyllabusIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Add chapters and topics from a sheet, one row per topic. Safe to run again.

    A chapter is matched by subject and chapter number. Topics already in a chapter are
    skipped, so the same sheet, with new rows added, can be uploaded as teachers fill it in.
    An empty topic gives the chapter one topic with the chapter's name, to split up later.
    Checked first; all rows or none.
    """
    reader = csv.DictReader(io.StringIO(body.csv.lstrip("﻿")))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in SYLLABUS_COLUMNS[:3] if c not in headers]
    if missing:
        raise HTTPException(400, f"The sheet needs these columns: {', '.join(missing)}")

    subjects = {s.code: s for s in db.scalars(select(Subject)).all()}
    by_name = {s.name.lower(): s for s in subjects.values()}
    errors, rows = [], []
    titles: dict[tuple[str, int], str] = {}
    for n, raw in enumerate(reader, start=2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(r.values()):
            continue
        problems = []
        subject = subjects.get(r.get("subject", "").lower()) or by_name.get(r.get("subject", "").lower())
        if not subject:
            problems.append(f"unknown subject '{r.get('subject')}' (use one of: {', '.join(sorted(subjects))})")
        number = r.get("chapter_number", "")
        if not number.isdigit() or not 1 <= int(number) <= 40:
            problems.append(f"chapter_number should be a number from 1 to 40, not '{number}'")
        if not r.get("chapter_title"):
            problems.append("chapter title is empty")
        if len(r.get("chapter_title", "")) > 200 or len(r.get("topic", "")) > 200:
            problems.append("titles can be at most 200 characters")
        if subject and number.isdigit() and r.get("chapter_title"):
            key = (subject.code, int(number))
            if titles.setdefault(key, r["chapter_title"]) != r["chapter_title"]:
                problems.append(f"chapter {number} has two different titles: '{titles[key]}' and '{r['chapter_title']}'")
        if problems:
            errors.append({"row": n, "problems": problems})
        else:
            rows.append({"subject": subject, "number": int(number), "title": r["chapter_title"], "topic": r.get("topic", ""), "row": n})

    existing = {(c.subject_id, c.number): c for c in db.scalars(select(Chapter)).all()}
    for r in rows:
        have = existing.get((r["subject"].id, r["number"]))
        if have and have.title != r["title"]:
            problem = f"{r['subject'].name} chapter {r['number']} already exists as '{have.title}'"
            if not any(problem in e["problems"] for e in errors):
                errors.append({"row": r["row"], "problems": [problem]})
    new_chapters = {(r["subject"].id, r["number"]) for r in rows} - set(existing)
    if errors or body.dry_run:
        return {
            "ok": not errors,
            "errors": errors,
            "dry_run": True,
            "chapters": len({(r["subject"].id, r["number"]) for r in rows}),
            "new_chapters": len(new_chapters),
            "topics": len(rows),
        }

    added_chapters = added_topics = 0
    for r in rows:
        key = (r["subject"].id, r["number"])
        chapter = existing.get(key)
        if chapter is None:
            chapter = existing[key] = Chapter(subject_id=r["subject"].id, number=r["number"], title=r["title"])
            db.add(chapter)
            db.flush()
            added_chapters += 1
        topic = r["topic"] or r["title"]
        have = db.scalars(select(Concept).where(Concept.chapter_id == chapter.id)).all()
        if any(c.title.lower() == topic.lower() for c in have):
            continue
        order = max((c.order for c in have), default=-1) + 1
        db.add(Concept(chapter_id=chapter.id, code=f"{r['subject'].code}9.c{chapter.id}.{order}", title=topic, order=order, notes=""))
        db.flush()
        added_topics += 1
    db.commit()
    audit(db, user, f"import_syllabus:{added_chapters}:{added_topics}")
    return {"ok": True, "errors": [], "dry_run": False, "added_chapters": added_chapters, "added_topics": added_topics}


# --- Audit log --------------------------------------------------------------------
# Who looked at or changed what. Read-only: nobody can edit or delete entries here.

AUDIT_WORDS = {
    "view_class_overview": "Viewed a class overview",
    "view_support_list": "Viewed the list of students who may need a hand",
    "view_child_progress": "Viewed a child's progress",
    "view_child_methods": "Viewed what helps a child learn",
    "view_class_methods": "Viewed how a class learns best",
    "view_child_mistakes": "Viewed a child's repeated mistakes",
    "view_class_mistakes": "Viewed a class's repeated mistakes",
    "view_child_thinking": "Viewed how a child's thinking puzzles are growing",
    "set_child_support": "Changed a child's support settings",
    "consent": "Changed consent",
    "paper_consent": "Recorded paper consent",
    "import_students": "Imported students",
    "review_sheet_upload": "Uploaded a filled-in review sheet",
    "review_fix_done": "Marked a question fixed",
    "reset_password": "Gave someone a new password",
    "add_teacher": "Added a teacher",
    "import_syllabus": "Uploaded the syllabus",
    "create_chapter": "Created a chapter",
    "ai_draft_content": "Asked AI to draft content",
    "add_assessment": "Added a school test for pilot results",
    "delete_assessment": "Deleted a school test",
    "upload_scores": "Uploaded marks",
    "view_pilot_results": "Viewed pilot results",
    "export_pilot_results": "Downloaded pilot results",
    "delete_pilot_results": "Deleted all pilot marks",
    "open_check_round": "Opened a subject check",
    "close_check_round": "Closed a subject check",
    "add_specialist": "Added a specialist",
    "share_with_specialist": "Shared a child with a specialist",
    "stop_sharing_with_specialist": "Stopped sharing a child with a specialist",
    "view_student_as_specialist": "Specialist viewed a child",
    "family_signup": "Started a family account",
    "family_add_child": "Added a child to a family",
    "family_update_child": "Changed a child's details",
    "family_remove_child": "Removed a child from a family",
    "family_child_login": "Made a login for a child",
    "family_add_adult": "Added an adult to a family",
    "family_remove_adult": "Removed an adult from a family",
    "screen_time_limits": "Changed screen time limits (minutes a day, per sitting)",
    "view_class_today": "Viewed today in the lab",
    "end_lab_period": "Ended a lab period (signed the class out)",
    "withdraw_student": "Withdrew a student and deleted their learning data",
    "view_weekly_usage": "Viewed weekly use",
    "set_school_details": "Changed the school's name or contact",
    "edit_student": "Changed a student's name or class",
    "export_consent_register": "Downloaded the consent register",
    "export_student_data": "Downloaded everything held about a student",
}


def describe(action: str) -> str:
    """Plain words for an audit action such as "paper_consent:mood_checkins:yes"."""
    head, *rest = action.split(":")
    words = AUDIT_WORDS.get(head, head.replace("_", " ").capitalize())
    return f"{words} ({', '.join(rest)})" if rest else words


@router.get("/audit")
def audit_log(
    before_id: int | None = None,
    student_id: int | None = None,
    action: str | None = None,
    since: date | None = None,
    limit: int = 50,
    db: DbSession = Depends(get_db),
    user: User = Depends(admin_only),
):
    """Newest first, 50 at a time. Pass before_id from the last row to see older entries.

    action keeps rows whose action starts with it (e.g. "reset_password"); since keeps rows from that day on.
    """
    limit = max(1, min(limit, 200))
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit + 1)
    if action:
        q = q.where(AuditLog.action.startswith(action))
    if since:
        q = q.where(AuditLog.created_at >= datetime(since.year, since.month, since.day) - timedelta(hours=5, minutes=30))
    if before_id:
        q = q.where(AuditLog.id < before_id)
    if student_id:
        q = q.where(AuditLog.subject_student_id == student_id)
    rows = db.scalars(q).all()
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.actor_id for r in rows} | {r.subject_student_id for r in rows if r.subject_student_id}))).all()}
    out = []
    for r in rows[:limit]:
        actor = people.get(r.actor_id)
        student = people.get(r.subject_student_id) if r.subject_student_id else None
        out.append(
            {
                "id": r.id,
                "when": r.created_at.isoformat(timespec="minutes"),
                "who": actor.name if actor else "?",
                "role": actor.role if actor else "?",
                "what": describe(r.action),
                "action": r.action,
                "student": student.name if student else None,
            }
        )
    return {"entries": out, "more": len(rows) > limit}


@router.get("/tutor-questions")
def tutor_questions(
    show: str = "open",
    db: DbSession = Depends(get_db),
    user: User = Depends(require_role("admin", "teacher")),
):
    """What students asked Ask SYNiq that the content didn't cover, by topic, most asked first. No student details.

    show: "open" (default, not yet handled), "handled", or "all".
    """
    q = (
        select(TutorQuestion, Concept, Chapter, Subject)
        .join(Concept, Concept.id == TutorQuestion.concept_id)
        .join(Chapter, Chapter.id == Concept.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .order_by(TutorQuestion.id.desc())
        .limit(1000)
    )
    if show in ("open", "handled"):
        q = q.where(TutorQuestion.handled == (show == "handled"))
    topics: dict[int, dict] = {}
    for tq, concept, chapter, subject in db.execute(q).all():
        t = topics.setdefault(
            concept.id,
            {"subject": subject.name, "chapter": f"{chapter.number}. {chapter.title}", "topic": concept.title, "questions": []},
        )
        t["questions"].append(
            {"id": tq.id, "text": tq.text, "answered_by": tq.answered_by, "asked": tq.created_at.date().isoformat(), "handled": tq.handled}
        )
    return sorted(topics.values(), key=lambda t: -len(t["questions"]))


class HandledIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)
    handled: bool = True


@router.post("/tutor-questions/handled")
def mark_tutor_questions(body: HandledIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("admin", "teacher"))):
    """Mark asked questions as dealt with (or open again). Handled ones drop off the default list."""
    rows = db.scalars(select(TutorQuestion).where(TutorQuestion.id.in_(body.ids))).all()
    for row in rows:
        row.handled = body.handled
    db.commit()
    return {"changed": len(rows)}


# --- Teacher review sheet -------------------------------------------------------

staff = require_role("admin", "teacher")


@router.get("/review-sheet")
def review_subjects(db: DbSession = Depends(get_db), user: User = Depends(staff)):
    """Subjects that have questions, with how many, for choosing a sheet to print."""
    from sqlalchemy import func

    from ..models import Item

    rows = db.execute(
        select(Subject, func.count(Item.id))
        .join(Chapter, Chapter.subject_id == Subject.id)
        .join(Concept, Concept.chapter_id == Chapter.id)
        .join(Item, Item.concept_id == Concept.id)
        .where(Item.status != "rejected")
        .group_by(Subject.id)
        .order_by(Subject.syllabus, Subject.grade, Subject.name)
    ).all()
    return [
        {"id": s.id, "name": s.name, "grade": s.grade, "syllabus": s.syllabus, "questions": n}
        for s, n in rows
        if not s.syllabus.endswith("-old")
    ]


def tip_text(db: DbSession, tag: str, cache: dict[str, str]) -> str:
    """The tip a student sees for this mistake, in English, as the Learn page finds it."""
    if tag not in cache:
        from .. import i18n
        from ..models import Misconception

        if i18n.has(f"tip.{tag}"):
            cache[tag] = i18n.t("en", f"tip.{tag}")
        else:
            row = db.scalars(select(Misconception).where(Misconception.tag == tag)).first()
            cache[tag] = row.tip if row else ""
    return cache[tag]


@router.get("/review-sheet/{subject_id}")
def review_sheet(subject_id: int, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    """Every question in one subject, chapter by chapter, for a teacher to read on paper.

    Shows what a student sees (question, choices), the right answer and worked solution, and
    each planned wrong answer with the tip it gets, so the teacher can mark anything to fix.
    """
    from ..models import Item

    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "No such subject")
    rows = db.execute(
        select(Item, Concept, Chapter)
        .join(Concept, Concept.id == Item.concept_id)
        .join(Chapter, Chapter.id == Concept.chapter_id)
        .where(Chapter.subject_id == subject.id, Item.status != "rejected")
        .order_by(Chapter.number, Concept.order, Concept.id, Item.difficulty, Item.id)
    ).all()
    tips: dict[str, str] = {}
    chapters: dict[int, dict] = {}
    n = 0
    for item, concept, chapter in rows:
        ch = chapters.setdefault(chapter.id, {"number": chapter.number, "title": chapter.title, "topics": {}})
        topic = ch["topics"].setdefault(concept.id, {"title": concept.title, "questions": []})
        n += 1
        topic["questions"].append(
            {
                "n": n,
                "id": item.id,
                "prompt": item.prompt,
                "options": item.options or [],
                "answer": item.answer,
                "solution": item.solution,
                "difficulty": item.difficulty,
                "status": item.status,
                "fix_note": item.fix_note,
                "mistakes": [
                    {"wrong": wrong, "tip": tip_text(db, tag, tips)} for wrong, tag in (item.misconceptions or {}).items()
                ],
            }
        )
    return {
        "subject": {"id": subject.id, "name": subject.name, "grade": subject.grade, "syllabus": subject.syllabus},
        "questions": n,
        "chapters": [{**c, "topics": list(c["topics"].values())} for c in chapters.values()],
    }


# --- Teacher's filled-in sheet back in -------------------------------------------

class ReviewUploadIn(BaseModel):
    csv: str = Field(max_length=5_000_000)


def _cell(row: dict, *names: str) -> str:
    """A column by any of its names, ignoring case, spaces and a spreadsheet's byte-order mark."""
    keys = {re.sub(r"[^a-z]", "", (k or "").lower()): v for k, v in row.items()}
    for name in names:
        v = keys.get(re.sub(r"[^a-z]", "", name.lower()))
        if v is not None:
            return str(v).strip()
    return ""


@router.post("/review-sheet/upload")
def upload_review_sheet(body: ReviewUploadIn, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    """Read back the spreadsheet a teacher filled in (the CSV from the review sheet page).

    A row marked "no" in the ok column, or with anything in "what to fix", becomes a note on
    that question's fix list. Nothing is changed in what students see: someone fixes the
    question in its content pack, then marks the note done. Rows marked ok are only counted.
    """
    from datetime import date

    from ..models import Item

    reader = csv.DictReader(io.StringIO(body.csv.lstrip("\ufeff")))
    if not reader.fieldnames or not any(re.sub(r"[^a-z]", "", (f or "").lower()) == "id" for f in reader.fieldnames):
        raise HTTPException(400, "This doesn't look like a review sheet: there is no 'id' column.")
    ok = fixes = blank = 0
    unknown: list[str] = []
    stamp = f"{user.name}, {date.today().isoformat()}"
    for row in reader:
        raw_id = _cell(row, "id")
        verdict = _cell(row, "ok (yes/no)", "ok").lower()
        note = _cell(row, "what to fix", "fix")
        if not raw_id:
            continue
        if not verdict and not note:
            blank += 1
            continue
        item = db.get(Item, int(raw_id)) if raw_id.isdigit() else None
        if not item:
            unknown.append(raw_id)
            continue
        if note or verdict in NO - {""}:
            text = f"{note or 'Marked not ok, no details given.'} ({stamp})"
            item.fix_note = f"{item.fix_note}\n{text}" if item.fix_note and text not in item.fix_note else text
            fixes += 1
        else:
            ok += 1
    audit(db, user, f"review_sheet_upload:{fixes} to fix:{ok} ok")
    return {"ok": ok, "to_fix": fixes, "not_checked": blank, "unknown_ids": unknown[:50]}


@router.get("/review-fixes")
def review_fixes(db: DbSession = Depends(get_db), user: User = Depends(staff)):
    """Questions a teacher marked to fix, by subject and chapter, until someone marks them done."""
    from ..models import Item

    rows = db.execute(
        select(Item, Concept, Chapter, Subject)
        .join(Concept, Concept.id == Item.concept_id)
        .join(Chapter, Chapter.id == Concept.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .where(Item.fix_note != "", Item.status != "rejected")
        .order_by(Subject.syllabus, Subject.grade, Subject.name, Chapter.number, Item.id)
    ).all()
    return [
        {
            "id": item.id,
            "subject": f"{subject.name} (class {subject.grade})",
            "chapter": f"{chapter.number}. {chapter.title}",
            "topic": concept.title,
            "prompt": item.prompt,
            "answer": item.answer,
            "note": item.fix_note,
        }
        for item, concept, chapter, subject in rows
    ]


@router.post("/review-fixes/{item_id}/done")
def review_fix_done(item_id: int, db: DbSession = Depends(get_db), user: User = Depends(staff)):
    """The question has been fixed (or the note was wrong): take it off the list."""
    from ..models import Item

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "No such question")
    item.fix_note = ""
    audit(db, user, f"review_fix_done:{item_id}")
    return {"ok": True}
