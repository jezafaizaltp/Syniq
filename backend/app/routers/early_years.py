"""Healthy screen time for ages 2 to 4: activities, limits set by the parent, and time used.

Adults in the family start each sitting; the child never signs in. Only minutes are stored.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import early
from .. import family as fam
from ..auth import audit, require_role
from ..db import get_db
from ..models import Child, ScreenTimeSession, User, utcnow
from .families import _membership

router = APIRouter(prefix="/early", tags=["early years"])
IST = timezone(timedelta(hours=5, minutes=30))
GRACE_SECONDS = 60  # time to say goodbye after the sitting ends


def india_today() -> date:
    return datetime.now(IST).date()


def _child(db: DbSession, user: User, child_id: int, holder: bool = False) -> Child:
    family, _ = _membership(db, user)
    child = db.get(Child, child_id)
    if not child or child.family_id != family.id:
        raise HTTPException(404, "Child not found")
    if holder and family.holder_id != user.id:
        raise HTTPException(403, "Only the account holder can change the limits")
    if fam.section_for(child.birth_date, child.due_date, child.grade) != "early":
        raise HTTPException(400, "Healthy screen time is for children aged 2 to 4")
    return child


def _used(db: DbSession, child_id: int, day: str) -> int:
    rows = db.scalars(select(ScreenTimeSession).where(ScreenTimeSession.child_id == child_id, ScreenTimeSession.day == day)).all()
    # A sitting still running counts in full, so a second device can't start another alongside it.
    return sum(r.seconds if r.ended_at else r.allowed_minutes * 60 for r in rows)


def _left_minutes(db: DbSession, child: Child) -> int:
    return max(0, child.daily_limit - (_used(db, child.id, india_today().isoformat()) + 59) // 60)


@router.get("/{child_id}")
def overview(child_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id)
    family, _ = _membership(db, user)
    today = india_today()
    week = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        week.append({"day": d, "minutes": round(_used(db, child.id, d) / 60)})
    return {
        "child": {"id": child.id, "name": child.name, "age": fam.age_words(child.birth_date, child.due_date)},
        "limits": {"daily": child.daily_limit, "session": child.session_limit, "daily_max": early.DAILY_MAX, "session_max": early.SESSION_MAX},
        "holder": family.holder_id == user.id,
        "today": today.isoformat(),
        "left_today": _left_minutes(db, child),
        "week": week,
        "areas": early.AREAS,
        "activities": early.ACTIVITIES,
    }


class StartIn(BaseModel):
    activity_id: str


@router.post("/{child_id}/sessions")
def start(child_id: int, body: StartIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id)
    if body.activity_id not in early.BY_ID:
        raise HTTPException(404, "Activity not found")
    left = _left_minutes(db, child)
    if left <= 0:
        raise HTTPException(409, f"{child.name}'s screen time for today is used up. More tomorrow.")
    row = ScreenTimeSession(
        child_id=child.id, started_by=user.id, activity_id=body.activity_id, day=india_today().isoformat(),
        allowed_minutes=min(child.session_limit, left),
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "minutes": row.allowed_minutes}


class EndIn(BaseModel):
    seconds: int = Field(ge=0, le=24 * 3600)


@router.post("/sessions/{session_id}/end")
def end(session_id: int, body: EndIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    row = db.get(ScreenTimeSession, session_id)
    if not row:
        raise HTTPException(404, "Not found")
    _child(db, user, row.child_id)
    if row.ended_at is None:
        row.seconds = min(body.seconds, row.allowed_minutes * 60 + GRACE_SECONDS)
        row.ended_at = utcnow()
        db.commit()
    return {"seconds": row.seconds}


class PlayedIn(BaseModel):
    activity_id: str
    day: str
    seconds: int = Field(ge=0, le=24 * 3600)


@router.post("/{child_id}/played")
def played_offline(child_id: int, body: PlayedIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Time played without internet, sent when the phone is back online, so it still counts."""
    child = _child(db, user, child_id)
    try:
        day = date.fromisoformat(body.day)
    except ValueError:
        raise HTTPException(422, "Bad date")
    if not india_today() - timedelta(days=7) <= day <= india_today():
        raise HTTPException(422, "Too old to record")
    seconds = min(body.seconds, child.session_limit * 60 + GRACE_SECONDS)
    db.add(ScreenTimeSession(
        child_id=child.id, started_by=user.id, activity_id=body.activity_id[:40], day=day.isoformat(),
        allowed_minutes=child.session_limit, seconds=seconds, ended_at=utcnow(),
    ))
    db.commit()
    return {"seconds": seconds}


class LimitsIn(BaseModel):
    daily: int = Field(ge=5, le=early.DAILY_MAX)
    session: int = Field(ge=3, le=early.SESSION_MAX)


@router.put("/{child_id}/limits")
def set_limits(child_id: int, body: LimitsIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, holder=True)
    child.daily_limit = body.daily
    child.session_limit = min(body.session, body.daily)
    db.commit()
    audit(db, user, f"screen_time_limits:{child.daily_limit}:{child.session_limit}")
    return {"daily": child.daily_limit, "session": child.session_limit}
