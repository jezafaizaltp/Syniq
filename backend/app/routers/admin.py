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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..auth import audit, has_consent, hash_password, require_role, temporary_password
from ..db import get_db
from ..models import Chapter, ClassGroup, Concept, Consent, GuardianLink, Session, Subject, User

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role("admin")

SCOPES = ("core_learning", "mood_checkins", "school_sharing")
COLUMNS = {
    "student_name": "Student's full name",
    "class": "Class, e.g. 9 A",
    "guardian_name": "Parent or guardian's name",
    "guardian_email": "Parent's email (optional; used as their login)",
    "guardian_phone": "Parent's phone (optional; only used to keep siblings under one parent, not saved)",
    "consent_learning": "yes if the paper form allows SYNiq for learning",
    "consent_mood": "yes if the form allows saving mood check-ins",
    "consent_school": "yes if the form allows sharing progress with the school",
}
TEMPLATE = ",".join(COLUMNS) + "\nAnu Krishna,9 A,Lakshmi Krishna,lakshmi@example.com,,yes,yes,yes\n"
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
        for scope, col in zip(SCOPES, ("consent_learning", "consent_mood", "consent_school")):
            value = r.get(col, "").lower()
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
    scope: str = Field(pattern="^(core_learning|mood_checkins|school_sharing)$")
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
