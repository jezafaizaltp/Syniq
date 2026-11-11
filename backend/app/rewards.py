"""Rewards: stickers for spotting mistakes, and achievements for moments of learning.

The rules (owner's design, 10 Nov 2026; see docs/rewards.md):
- Rewards come from learning: spotting SYNiq's deliberate mistakes, securing topics, fixing a mistake pattern,
  getting a harder question right, coming back after a break. Never from minutes on screen, never from logging in.
- Nothing is compared with anyone. A sticker or achievement is the learner's own; teachers don't see them.
- Missing a deliberate mistake costs nothing: the learner is told gently to look carefully next time.
- A parent can switch rewards off for their child; the school sets the default.

Everything here is worked out from the learner's own answers and spot-the-mistake stars, so deleting a learner's
data (withdrawal) deletes their rewards too, and the data download carries them.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .engine import mastery as m
from .models import Attempt, Concept, Item, LearningEvent, Mastery, SchoolSetting, User

STARS_PER_STICKER = 5
# One sticker every few stars, in this order. Calm pictures from nature and everyday life.
STICKERS = [
    "🌱", "🐢", "🌻", "🦋", "🐘", "🌈", "🪁", "🐬", "🌙", "🦚",
    "🍀", "🐝", "⛵", "🌳", "🦜", "🐳", "🌼", "🦉", "🏔️", "🌟",
    "🐠", "🍉", "🛶", "🌊",
]
SPOTS_FOR_ACHIEVEMENT = 10
BREAK_DAYS = 7  # back after at least this many days away

# Achievement ids, in the order shown. Words for each are in the app (frontend/lib/i18n.ts "ach.<id>").
ACHIEVEMENTS = ["first_secure", "chapter_done", "first_hard_right", "pattern_fixed", "spotted_10", "back_after_break"]

# Every kind of reward and what earns it. test_rewards checks that none of these is time on screen.
EARNED_BY = {
    "sticker": "spot_star",
    "first_secure": "mastery",
    "chapter_done": "mastery",
    "first_hard_right": "attempt",
    "pattern_fixed": "attempt",
    "spotted_10": "spot_star",
    "back_after_break": "attempt_days",
}


def _local_day(at: datetime):
    return (at + timedelta(hours=5, minutes=30)).date()


def school_default_on(db: DbSession) -> bool:
    row = db.get(SchoolSetting, "rewards")
    return not (row and row.value == "off")


def rewards_on(db: DbSession, student: User) -> bool:
    """The parent's choice for this child if they made one, else the school's default (on unless switched off)."""
    choice = (student.settings or {}).get("rewards")
    if choice in ("on", "off"):
        return choice == "on"
    return school_default_on(db)


def star_times(db: DbSession, student_id: int) -> list[datetime]:
    return list(
        db.scalars(
            select(LearningEvent.created_at)
            .where(LearningEvent.student_id == student_id, LearningEvent.kind == "spot_star")
            .order_by(LearningEvent.created_at)
        ).all()
    )


def stickers(stars: int) -> dict:
    """The stickers unlocked by this many stars, and how many stars until the next one."""
    got = min(stars // STARS_PER_STICKER, len(STICKERS))
    nxt = None if got >= len(STICKERS) else STARS_PER_STICKER - stars % STARS_PER_STICKER
    return {"unlocked": STICKERS[:got], "locked": len(STICKERS) - got, "stars_to_next": nxt}


def achievements(db: DbSession, student_id: int) -> list[dict]:
    """Each achievement earned, with the day it was earned. Worked out from the learner's own record."""
    earned: dict[str, datetime] = {}

    secured = db.execute(
        select(Mastery.concept_id, Mastery.secured_at).where(Mastery.student_id == student_id, Mastery.secured_at.is_not(None))
    ).all()
    if secured:
        earned["first_secure"] = min(at for _, at in secured)
        by_concept = dict(secured)
        chapters = {c.chapter_id for c in db.scalars(select(Concept).where(Concept.id.in_(by_concept))).all()}
        done = []
        for ch in chapters:
            topics = db.scalars(select(Concept.id).where(Concept.chapter_id == ch)).all()
            if topics and all(t in by_concept for t in topics):
                done.append(max(by_concept[t] for t in topics))
        if done:
            earned["chapter_done"] = min(done)

    hard = db.scalars(
        select(func.min(Attempt.created_at))
        .join(Item, Item.id == Attempt.item_id)
        .where(Attempt.student_id == student_id, Attempt.correct.is_(True), Item.difficulty >= m.HARD)
    ).first()
    if hard:
        earned["first_hard_right"] = hard

    from . import learning  # here: learning imports this module

    fixed = [p.fixed_at for p in learning.mistake_patterns(db, student_id) if p.status == "fixed" and p.fixed_at]
    if fixed:
        earned["pattern_fixed"] = min(fixed)

    stars = star_times(db, student_id)
    if len(stars) >= SPOTS_FOR_ACHIEVEMENT:
        earned["spotted_10"] = stars[SPOTS_FOR_ACHIEVEMENT - 1]

    days = sorted({_local_day(at) for (at,) in db.execute(select(Attempt.created_at).where(Attempt.student_id == student_id)).all()})
    for before, after in zip(days, days[1:]):
        if (after - before).days >= BREAK_DAYS:
            earned["back_after_break"] = datetime(after.year, after.month, after.day)
            break

    return [{"id": a, "earned_on": earned[a].date().isoformat()} for a in ACHIEVEMENTS if a in earned]


def practice_days_this_week(db: DbSession, student_id: int, now: datetime) -> int:
    """Days with at least one answer in the last 7 days. Days, never minutes; missed days are not counted against anyone."""
    since = now - timedelta(days=7)
    rows = db.execute(select(Attempt.created_at).where(Attempt.student_id == student_id, Attempt.created_at >= since)).all()
    return len({_local_day(at) for (at,) in rows})


def summary(db: DbSession, student: User, now: datetime) -> dict:
    """What My space shows. When rewards are off, only that they are off."""
    if not rewards_on(db, student):
        return {"on": False}
    stars = len(star_times(db, student.id))
    return {
        "on": True,
        "stars": stars,
        "stickers": stickers(stars),
        "achievements": achievements(db, student.id),
        "practice_days": practice_days_this_week(db, student.id, now),
    }


def new_this_week(db: DbSession, student: User, now: datetime) -> list[str]:
    """Achievement ids earned in the last 7 days, for the parent's This week (in words, no numbers to compare)."""
    if not rewards_on(db, student):
        return []
    since = (now - timedelta(days=7)).date().isoformat()
    return [a["id"] for a in achievements(db, student.id) if a["earned_on"] >= since]
