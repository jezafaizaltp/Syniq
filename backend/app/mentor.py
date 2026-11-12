"""The learner's mentor: what to do next, and how they have grown.

A good tutor starts each sitting by saying where to go, not by asking. This module looks at everything SYNiq
already knows about the learner and picks at most three next steps, most useful first:

1. a mistake made more than once and not fixed yet: a few questions that catch it, so it gets fixed;
2. a topic stuck right now (three wrong in a row): the lesson again, explained the way that works for them;
3. a topic due for revision, so what was learnt doesn't fade;
4. carry on: the next topic not yet secure in the chapter they were working on, or the next chapter.

Then what went well this week, in the learner's own terms: topics made secure, mistakes fixed, lessons
finished, days practised, and the way of explaining that has helped most lately. Never a mark, a rank or a
comparison with anyone else, and never a label: "pictures have helped you most lately" describes what worked,
recomputed after every answer.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from . import learning
from .engine import mastery as m
from .engine import methods
from .models import Attempt, Chapter, Concept, Decision, Item, LearningEvent, Mastery, Subject, User, utcnow

IST = timedelta(hours=5, minutes=30)
WEEK = timedelta(days=7)
MAX_STEPS = 3
STUCK_IN_A_ROW = 3


def part_of_day(now) -> str:
    hour = (now + IST).hour
    return "morning" if 4 <= hour < 12 else "afternoon" if hour < 17 else "evening"


def _where(db: DbSession, concept_id: int) -> dict | None:
    concept = db.get(Concept, concept_id)
    if not concept:
        return None
    chapter = db.get(Chapter, concept.chapter_id)
    subject = db.get(Subject, chapter.subject_id) if chapter else None
    if not chapter or not subject:
        return None
    return {"concept_id": concept.id, "topic": concept.title, "chapter_id": chapter.id, "chapter": chapter.title, "subject": subject.name}


def _last_topic(db: DbSession, user: User, rows: list[Mastery]) -> int | None:
    """The topic worked on last: the latest answer, or else the latest lesson or explanation (no answers yet)."""
    if rows:
        return max(rows, key=lambda r: r.updated_at or utcnow()).concept_id
    return db.scalars(
        select(Decision.concept_id)
        .where(Decision.student_id == user.id, Decision.concept_id.is_not(None))
        .order_by(Decision.created_at.desc(), Decision.id.desc())
    ).first()


def _carry_on(db: DbSession, user: User, rows: list[Mastery]) -> dict | None:
    """The next topic to learn in the chapter worked on last, or the next chapter once that one is secure."""
    from .routers.student import next_chapter  # the same rule the end of a chapter uses

    last = _last_topic(db, user, rows)
    concept = db.get(Concept, last) if last else None
    if not concept:
        return None
    practisable = select(Item.concept_id).where(Item.status == "approved")
    topics = db.scalars(select(Concept).where(Concept.chapter_id == concept.chapter_id, Concept.id.in_(practisable)).order_by(Concept.order)).all()
    mine = {r.concept_id: r for r in rows}
    for t in topics:
        r = mine.get(t.id)
        if not r or not m.is_secure(r.p_known, r.attempts):
            where = _where(db, t.id)
            if where:
                # Taught already (a lesson or an explanation), even with nothing answered yet: carry on.
                where["started"] = bool(r) or t.id == last
            return where
    nxt = next_chapter(db, user, concept.chapter_id)
    if not nxt:
        return None
    subject = db.get(Subject, db.get(Chapter, nxt["id"]).subject_id)
    return {"concept_id": None, "topic": None, "chapter_id": nxt["id"], "chapter": nxt["title"], "subject": subject.name, "started": False}


def plan(db: DbSession, user: User, lang: str = "en") -> dict:
    now = utcnow()
    rows = db.scalars(select(Mastery).where(Mastery.student_id == user.id, Mastery.attempts > 0)).all()
    steps: list[dict] = []
    used: set[int] = set()

    def add(kind: str, concept_id: int | None, **extra):
        if len(steps) >= MAX_STEPS or (concept_id and concept_id in used):
            return
        where = _where(db, concept_id) if concept_id else None
        if concept_id and not where:
            return
        used.add(concept_id) if concept_id else None
        steps.append({"kind": kind, **(where or {}), **extra})

    patterns = learning.mistake_patterns(db, user.id)
    for p in patterns:
        if p.status == "working_on" and p.topics:
            add("fix_mistake", p.topics[-1], mistake=learning.pattern_text(db, lang, p.tag), times=p.times)
            break

    for r in sorted(rows, key=lambda r: r.updated_at or now, reverse=True):
        if (r.wrong_streak or 0) >= STUCK_IN_A_ROW and not m.is_secure(r.p_known, r.attempts):
            concept = db.get(Concept, r.concept_id)
            add("relearn", r.concept_id, has_lesson=bool(concept and concept.lesson))
            break

    due = sorted((r for r in rows if r.next_review_at and r.next_review_at <= now), key=lambda r: r.next_review_at)
    if due:
        add("review", due[0].concept_id, due=len(due))

    carry = _carry_on(db, user, rows)
    if carry and (carry["concept_id"] is None or carry["concept_id"] not in used) and len(steps) < MAX_STEPS:
        steps.append({"kind": "carry_on" if carry.pop("started") else "start_topic", **carry})
    if not steps:
        steps.append({"kind": "first_lesson"})

    return {"part_of_day": part_of_day(now), "steps": steps, "week": week(db, user, rows, patterns, now)}


def growth(db: DbSession, user: User) -> dict:
    """This week's good news on its own, for the parent's view of the same week the learner sees."""
    rows = db.scalars(select(Mastery).where(Mastery.student_id == user.id, Mastery.attempts > 0)).all()
    return week(db, user, rows, learning.mistake_patterns(db, user.id), utcnow())


def week(db: DbSession, user: User, rows: list[Mastery], patterns, now) -> dict:
    since = now - WEEK
    attempts = db.scalars(select(Attempt).where(Attempt.student_id == user.id, Attempt.created_at >= since)).all()
    days = {(a.created_at + IST).date() for a in attempts}
    lessons = db.scalars(
        select(LearningEvent.detail).where(
            LearningEvent.student_id == user.id, LearningEvent.kind == "lesson_done", LearningEvent.created_at >= since
        )
    ).all()
    _, _, overall = learning.method_stats(db, user.id)
    # Wrong, then right on the same topic later this week: getting past a hard moment, the habit worth naming.
    bounced = set()
    wrong_on: set[int] = set()
    for a in sorted(attempts, key=lambda a: a.created_at):
        if not a.correct:
            wrong_on.add(a.concept_id)
        elif a.concept_id in wrong_on:
            bounced.add(a.concept_id)
    return {
        "answered": len(attempts),
        "days": len(days),
        "secured": sum(1 for r in rows if r.secured_at and r.secured_at >= since and m.is_secure(r.p_known, r.attempts)),
        "fixed": sum(1 for p in patterns if p.status == "fixed" and p.fixed_at and p.fixed_at >= since),
        "lessons": len(set(d.split(":")[0] for d in lessons if d)),
        "came_back": len(bounced),
        "helped_most": methods.best_method(overall),
    }
