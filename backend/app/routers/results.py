"""Pilot results: school marks before and after SYNiq, for the school admin only.

See evaluation.py for the method. Marks live in their own tables and are read only
here: the adaptive engine, teachers, parents and students never see them.
"""

import csv
import io
import random
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from .. import evaluation
from ..auth import audit, has_consent, require_role
from ..db import get_db
from ..models import Assessment, AssessmentScore, Attempt, Chapter, Concept, Subject, User

router = APIRouter(prefix="/admin/results", tags=["results"])
admin_only = require_role("admin")

COMPARISON_CODE = re.compile(r"^C\d{1,4}$", re.IGNORECASE)
ABSENT = {"", "ab", "absent", "-"}


class AssessmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subject_id: int
    max_marks: float = Field(gt=0, le=1000)
    phase: str = Field(pattern="^(before|after)$")
    taken_on: date


@router.get("/assessments")
def list_assessments(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    subjects = {s.id: s.name for s in db.scalars(select(Subject)).all()}
    out = []
    for a in db.scalars(select(Assessment).order_by(Assessment.taken_on, Assessment.id)).all():
        scores = db.scalars(select(AssessmentScore).where(AssessmentScore.assessment_id == a.id)).all()
        out.append({
            "id": a.id, "name": a.name, "subject_id": a.subject_id, "subject": subjects.get(a.subject_id),
            "max_marks": a.max_marks, "phase": a.phase, "taken_on": a.taken_on,
            "pilot_scores": sum(s.student_id is not None for s in scores),
            "comparison_scores": sum(s.comparison_code is not None for s in scores),
        })
    return out


@router.post("/assessments")
def add_assessment(body: AssessmentIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    if not db.get(Subject, body.subject_id):
        raise HTTPException(404, "Subject not found")
    a = Assessment(name=body.name.strip(), subject_id=body.subject_id, max_marks=body.max_marks, phase=body.phase,
                   taken_on=body.taken_on.isoformat())
    db.add(a)
    db.commit()
    audit(db, user, "add_assessment")
    return {"id": a.id}


@router.delete("/assessments/{assessment_id}")
def delete_assessment(assessment_id: int, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(404, "Not found")
    db.execute(delete(AssessmentScore).where(AssessmentScore.assessment_id == a.id))
    db.delete(a)
    db.commit()
    audit(db, user, "delete_assessment")
    return {"ok": True}


class ScoresIn(BaseModel):
    csv: str = Field(max_length=200_000)
    dry_run: bool = True


@router.post("/assessments/{assessment_id}/scores")
def upload_scores(assessment_id: int, body: ScoresIn, db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Columns: student (a pilot student's login, or a comparison code like C12) and marks.

    Checked first; all rows or none. Uploading again replaces a student's marks.
    Marks of AB or blank mean absent and are skipped.
    """
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(404, "Not found")
    reader = csv.DictReader(io.StringIO(body.csv.lstrip("﻿")))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    if "student" not in headers or "marks" not in headers:
        raise HTTPException(400, "The sheet needs two columns: student and marks")

    students = {u.email: u for u in db.scalars(select(User).where(User.role == "student")).all()}
    errors, rows, seen, absent = [], [], set(), 0
    for n, raw in enumerate(reader, start=2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(r.values()):
            continue
        who, marks = r.get("student", ""), r.get("marks", "")
        problems = []
        student = students.get(who.lower())
        if student:
            key = ("pilot", student.id)
            if not has_consent(db, student.id, "core_learning"):
                problems.append(f"{who} has no parent consent for SYNiq, so leave them out")
        elif COMPARISON_CODE.match(who):
            key = ("comparison", who.upper())
        else:
            problems.append(f"'{who}' is not a pilot student's login or a comparison code like C12 (never a name)")
            key = None
        if key and key in seen:
            problems.append(f"{who} is in the sheet twice")
        seen.add(key)
        value = None
        if marks.lower() in ABSENT:
            absent += 1
        else:
            try:
                value = float(marks)
                if not 0 <= value <= a.max_marks:
                    problems.append(f"marks should be between 0 and {a.max_marks:g}, not {marks}")
            except ValueError:
                problems.append(f"marks should be a number or AB, not '{marks}'")
        if problems:
            errors.append({"row": n, "problems": problems})
        elif value is not None:
            rows.append((key, value))

    pilot = sum(k[0] == "pilot" for k, _ in rows)
    if errors or body.dry_run:
        return {"ok": not errors, "errors": errors, "dry_run": True, "pilot": pilot, "comparison": len(rows) - pilot, "absent": absent}

    for (group, ident), value in rows:
        column = AssessmentScore.student_id if group == "pilot" else AssessmentScore.comparison_code
        score = db.scalars(select(AssessmentScore).where(AssessmentScore.assessment_id == a.id, column == ident)).first()
        if score:
            score.marks = value
        elif group == "pilot":
            db.add(AssessmentScore(assessment_id=a.id, student_id=ident, marks=value))
        else:
            db.add(AssessmentScore(assessment_id=a.id, comparison_code=ident, marks=value))
    db.commit()
    audit(db, user, f"upload_scores:{a.id}:{len(rows)}")
    return {"ok": True, "errors": [], "dry_run": False, "pilot": pilot, "comparison": len(rows) - pilot, "absent": absent}


def _pairs(db: DbSession, subject_id: int) -> tuple[list[evaluation.Pair], Assessment | None, Assessment | None]:
    """Each student with marks on both the subject's latest 'before' and latest 'after' assessments."""
    assessments = db.scalars(select(Assessment).where(Assessment.subject_id == subject_id).order_by(Assessment.taken_on)).all()
    before = next((a for a in reversed(assessments) if a.phase == "before"), None)
    after = next((a for a in reversed(assessments) if a.phase == "after"), None)
    if not before or not after:
        return [], before, after

    def percents(a: Assessment) -> dict:
        scores = db.scalars(select(AssessmentScore).where(AssessmentScore.assessment_id == a.id)).all()
        return {(s.student_id or s.comparison_code): 100 * s.marks / a.max_marks for s in scores}

    b, f = percents(before), percents(after)
    pairs = []
    for key in b.keys() & f.keys():
        if isinstance(key, int):
            # Leave out anyone whose parent has since withdrawn consent.
            if not has_consent(db, key, "core_learning"):
                continue
            practised = db.scalar(
                select(func.count(Attempt.id))
                .join(Concept, Concept.id == Attempt.concept_id)
                .join(Chapter, Chapter.id == Concept.chapter_id)
                .where(Attempt.student_id == key, Chapter.subject_id == subject_id)
            )
            pairs.append(evaluation.Pair("pilot", b[key], f[key], practised))
        else:
            pairs.append(evaluation.Pair("comparison", b[key], f[key]))
    return pairs, before, after


@router.get("/report")
def report(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    out = []
    subject_ids = sorted({a.subject_id for a in db.scalars(select(Assessment)).all()})
    for sid in subject_ids:
        pairs, before, after = _pairs(db, sid)
        entry = {
            "subject": db.get(Subject, sid).name,
            "before": before.name if before else None,
            "after": after.name if after else None,
        }
        if before and after:
            entry.update(evaluation.report(pairs))
        out.append(entry)
    audit(db, user, "view_pilot_results")
    return {"min_group": evaluation.MIN_GROUP, "subjects": out}


@router.get("/export.csv", response_class=PlainTextResponse)
def export(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """One row per student and subject, without names, logins or codes, in random order."""
    rows = []
    for sid in sorted({a.subject_id for a in db.scalars(select(Assessment)).all()}):
        name = db.get(Subject, sid).name
        pairs, _, _ = _pairs(db, sid)
        rows += [[p.group, name, f"{p.before:.1f}", f"{p.after:.1f}", "" if p.practised is None else p.practised] for p in pairs]
    random.shuffle(rows)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["group", "subject", "before_percent", "after_percent", "questions_practised"])
    w.writerows(rows)
    audit(db, user, "export_pilot_results")
    return buf.getvalue()


@router.delete("")
def delete_all(db: DbSession = Depends(get_db), user: User = Depends(admin_only)):
    """Remove every assessment and mark, e.g. once the pilot report is written."""
    db.execute(delete(AssessmentScore))
    db.execute(delete(Assessment))
    db.commit()
    audit(db, user, "delete_pilot_results")
    return {"ok": True}
