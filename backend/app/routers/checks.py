"""Subject checks: a short quiz per subject at the start, at the end of term, and four weeks later.

The starting check tells the adaptive teacher where each student begins, so nobody
spends a week on topics they already know. The end-of-term and retention checks
measure what was learnt and what stayed, for the pilot report.

Students never see a score: after a check they see, in words, which topics they
already seem to know and where SYNiq will start. Answers are kept apart from the
practice history, so a check never switches on support modes or counts as practice.
The school admin sees group results only, and only for groups of 5 or more.
"""

import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import i18n, learning
from ..auth import audit, require_learning_consent, require_role
from ..db import get_db
from ..engine import mastery as m
from ..models import CheckRound, Concept, Item, Subject, SubjectCheck, User, utcnow
from .student import visible_chapters

router = APIRouter(tags=["checks"])
admin_only = require_role("admin")

MAX_QUESTIONS = 12
MIN_GROUP = 5  # smaller groups are hidden, so no one student's result can be worked out
KINDS = ("start", "end", "retention")


def _pick_items(db: DbSession, student: User, subject_id: int) -> list[int]:
    """One question per topic, spread across the subject's chapters, avoiding ones from earlier checks."""
    chapters = visible_chapters(db, student, subject_id)
    chapter_order = {c.id: c.number for c in chapters}
    items = db.scalars(
        select(Item).join(Concept, Concept.id == Item.concept_id).where(
            Concept.chapter_id.in_(chapter_order), Item.status == "approved"
        )
    ).all()
    if not items:
        return []
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.id.in_({i.concept_id for i in items}))).all()}
    used = set()
    for earlier in db.scalars(
        select(SubjectCheck.item_ids).where(SubjectCheck.student_id == student.id, SubjectCheck.subject_id == subject_id)
    ).all():
        used.update(earlier or [])

    by_concept: dict[int, list[Item]] = {}
    for item in items:
        by_concept.setdefault(item.concept_id, []).append(item)
    ordered = sorted(by_concept, key=lambda cid: (chapter_order[concepts[cid].chapter_id], concepts[cid].order, cid))
    if len(ordered) > MAX_QUESTIONS:
        step = len(ordered) / MAX_QUESTIONS
        ordered = [ordered[int(i * step)] for i in range(MAX_QUESTIONS)]

    rng = random.Random(f"{student.id}-{subject_id}-{len(used)}")
    picked = []
    for cid in ordered:
        pool = [i for i in by_concept[cid] if i.id not in used] or by_concept[cid]
        best = min(abs(i.difficulty - 2) for i in pool)  # middle difficulty tells the most
        picked.append(rng.choice(sorted((i for i in pool if abs(i.difficulty - 2) == best), key=lambda i: i.id)).id)
    return picked


def _open_rounds(db: DbSession) -> list[CheckRound]:
    return db.scalars(select(CheckRound).where(CheckRound.closed_at.is_(None)).order_by(CheckRound.id)).all()


def _find(db: DbSession, student_id: int, subject_id: int, kind: str, round_id: int | None) -> SubjectCheck | None:
    q = select(SubjectCheck).where(
        SubjectCheck.student_id == student_id, SubjectCheck.subject_id == subject_id, SubjectCheck.kind == kind
    )
    q = q.where(SubjectCheck.round_id.is_(None)) if round_id is None else q.where(SubjectCheck.round_id == round_id)
    return db.scalars(q.order_by(SubjectCheck.id.desc())).first()


def _check_out(db: DbSession, check: SubjectCheck, student: User) -> dict:
    items = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_(check.item_ids))).all()}
    remaining = [items[i] for i in check.item_ids if str(i) not in check.answers and i in items]
    out = {
        "id": check.id,
        "kind": check.kind,
        "subject_id": check.subject_id,
        "status": check.status,
        "total": len(check.item_ids),
        "answered": len(check.answers),
        "item": learning.public_item(remaining[0], student.settings) if remaining and check.status == "open" else None,
    }
    if check.status == "done":
        out["summary"] = _summary(db, check)
    return out


def _summary(db: DbSession, check: SubjectCheck) -> dict:
    """In words: topics the student seems to know already, and where SYNiq will start."""
    items = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_(check.item_ids))).all()}
    titles = {c.id: c.title for c in db.scalars(select(Concept).where(Concept.id.in_({i.concept_id for i in items.values()}))).all()}
    known, start_with = [], []
    for item_id in check.item_ids:
        item = items.get(item_id)
        if not item:
            continue
        answer = check.answers.get(str(item_id), {})
        (known if answer.get("correct") else start_with).append(titles[item.concept_id])
    return {"known": known, "start_with": start_with}


# --- Student --------------------------------------------------------------------

@router.get("/checks")
def my_checks(db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """Checks waiting for this student, per subject that has content."""
    rounds = _open_rounds(db)
    out = []
    for s in learning.subjects_for(db, user):
        if not visible_chapters(db, user, s.id):
            continue
        start = _find(db, user.id, s.id, "start", None)
        row = {"subject_id": s.id, "subject": s.name, "start": start.status if start else "not_started", "rounds": []}
        for r in rounds:
            c = _find(db, user.id, s.id, r.kind, r.id)
            row["rounds"].append({"round_id": r.id, "kind": r.kind, "status": c.status if c else "not_started"})
        out.append(row)
    return out


class StartIn(BaseModel):
    subject_id: int
    kind: str = Field(default="start", pattern="^(start|end|retention)$")


@router.post("/checks")
def start_check(
    body: StartIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent), lang: str = Depends(i18n.language)
):
    """Start (or carry on with) a check. End and retention checks need a round the school has opened."""
    if not db.get(Subject, body.subject_id):
        raise HTTPException(404, "Subject not found")
    round_id = None
    if body.kind != "start":
        r = next((r for r in _open_rounds(db) if r.kind == body.kind), None)
        if not r:
            raise HTTPException(400, i18n.t(lang, "err.check_not_open"))
        round_id = r.id
    existing = _find(db, user.id, body.subject_id, body.kind, round_id)
    if existing:
        return _check_out(db, existing, user)
    item_ids = _pick_items(db, user, body.subject_id)
    if not item_ids:
        raise HTTPException(400, i18n.t(lang, "err.check_no_questions"))
    check = SubjectCheck(
        student_id=user.id, subject_id=body.subject_id, kind=body.kind, round_id=round_id, item_ids=item_ids, answers={}, status="open"
    )
    db.add(check)
    db.commit()
    return _check_out(db, check, user)


class CheckAnswerIn(BaseModel):
    item_id: int
    # Empty means "I haven't learnt this yet": always allowed, never a wrong answer to feel bad about.
    response: str = Field(default="", max_length=200)


def _seed_mastery(db: DbSession, check: SubjectCheck) -> None:
    """A starting check moves where the engine begins, but only for topics not yet practised.

    One answer is one piece of evidence: it nudges the estimate, it never marks a topic secure.
    """
    items = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_(check.item_ids))).all()}
    for key, answer in check.answers.items():
        item = items.get(int(key))
        if not item:
            continue
        row = learning.get_mastery(db, check.student_id, item.concept_id)
        if row.attempts == 0:
            row.p_known = m.update_p_known(row.p_known, m.Evidence(bool(answer.get("correct")), item.kind, 0))
            row.updated_at = utcnow()


@router.post("/checks/{check_id}/answer")
def answer_check(
    check_id: int, body: CheckAnswerIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)
):
    check = db.get(SubjectCheck, check_id)
    if not check or check.student_id != user.id:
        raise HTTPException(404, "Check not found")
    if check.status != "open":
        return _check_out(db, check, user)
    if body.item_id not in check.item_ids:
        raise HTTPException(400, "That question is not part of this check")
    if check.round_id:
        r = db.get(CheckRound, check.round_id)
        if r and r.closed_at:
            raise HTTPException(400, "This check has closed")
    item = db.get(Item, body.item_id)
    response = body.response.strip()
    answers = dict(check.answers or {})
    answers[str(body.item_id)] = {"response": response, "correct": bool(response) and learning.same_answer(response, item.answer)}
    check.answers = answers
    if len(answers) >= len(check.item_ids):
        check.status = "done"
        check.finished_at = utcnow()
        if check.kind == "start":
            _seed_mastery(db, check)
    db.commit()
    return _check_out(db, check, user)


@router.post("/checks/{check_id}/skip")
def skip_check(check_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """A starting check is optional. End and retention checks can be left and picked up later."""
    check = db.get(SubjectCheck, check_id)
    if not check or check.student_id != user.id:
        raise HTTPException(404, "Check not found")
    if check.kind == "start" and check.status == "open":
        check.status = "skipped"
        check.finished_at = utcnow()
        db.commit()
    return _check_out(db, check, user)


@router.post("/checks/skip-start")
def skip_start(body: StartIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """Skip a starting check without opening it."""
    if not db.get(Subject, body.subject_id):
        raise HTTPException(404, "Subject not found")
    check = _find(db, user.id, body.subject_id, "start", None)
    if not check:
        check = SubjectCheck(student_id=user.id, subject_id=body.subject_id, kind="start", item_ids=[], answers={}, status="open")
        db.add(check)
    if check.status == "open":
        check.status = "skipped"
        check.finished_at = utcnow()
    db.commit()
    return {"status": check.status}


# --- School admin -----------------------------------------------------------------

class RoundIn(BaseModel):
    kind: str = Field(pattern="^(end|retention)$")


@router.get("/admin/checks")
def check_report(db: DbSession = Depends(get_db), admin: User = Depends(admin_only)):
    """Group results per subject: how many took each check, and the share of questions right.

    Change from start to end counts only students who took both, so it isn't skewed by who joined.
    """
    rounds = db.scalars(select(CheckRound).order_by(CheckRound.id)).all()
    done = db.scalars(select(SubjectCheck).where(SubjectCheck.status == "done")).all()
    subjects = db.scalars(select(Subject).order_by(Subject.id)).all()

    def share(c: SubjectCheck) -> float:
        return sum(1 for a in c.answers.values() if a.get("correct")) / max(1, len(c.item_ids))

    report = []
    for s in subjects:
        mine = [c for c in done if c.subject_id == s.id]
        if not mine:
            continue
        cols = [("start", None)] + [(r.kind, r.id) for r in rounds]
        row = {"subject": s.name, "checks": []}
        start_by_student = {c.student_id: share(c) for c in mine if c.kind == "start"}
        for kind, rid in cols:
            group = [c for c in mine if c.kind == kind and c.round_id == rid]
            entry = {"kind": kind, "round_id": rid, "students": len(group), "average_right": None, "change_from_start": None}
            if len(group) >= MIN_GROUP:
                entry["average_right"] = round(100 * sum(share(c) for c in group) / len(group))
            both = [share(c) - start_by_student[c.student_id] for c in group if kind != "start" and c.student_id in start_by_student]
            if len(both) >= MIN_GROUP:
                entry["change_from_start"] = round(100 * sum(both) / len(both))
            row["checks"].append(entry)
        report.append(row)
    return {
        "rounds": [
            {"id": r.id, "kind": r.kind, "opened_at": r.opened_at.isoformat(timespec="minutes"), "open": r.closed_at is None}
            for r in rounds
        ],
        "subjects": report,
        "min_group": MIN_GROUP,
    }


@router.post("/admin/check-rounds")
def open_round(body: RoundIn, db: DbSession = Depends(get_db), admin: User = Depends(admin_only)):
    if any(r.kind == body.kind for r in _open_rounds(db)):
        raise HTTPException(400, f"An {body.kind} check is already open. Close it first.")
    r = CheckRound(kind=body.kind)
    db.add(r)
    db.commit()
    audit(db, admin, f"open_check_round:{body.kind}")
    return {"id": r.id, "kind": r.kind}


@router.post("/admin/check-rounds/{round_id}/close")
def close_round(round_id: int, db: DbSession = Depends(get_db), admin: User = Depends(admin_only)):
    r = db.get(CheckRound, round_id)
    if not r:
        raise HTTPException(404, "Not found")
    if r.closed_at is None:
        r.closed_at = utcnow()
        db.commit()
        audit(db, admin, f"close_check_round:{r.kind}")
    return {"id": r.id, "open": False}
