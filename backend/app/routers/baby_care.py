"""The baby (birth to 2) and pregnancy sections, for the adults in a family.

Milestones, vaccines and the care log are visible only to the family. SYNiq never turns them into
a score, a label or a diagnosis: a milestone not yet seen only ever leads to "mention it to your doctor".
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import baby, pregnancy
from .. import family as fam
from ..auth import require_role
from ..db import get_db
from ..models import CareLog, Child, ChildMark, User
from .early_years import IST, india_today
from .families import _membership

router = APIRouter(tags=["baby and pregnancy"])
OVERDUE_AFTER = timedelta(days=28)


def _child(db: DbSession, user: User, child_id: int, section: str) -> Child:
    family, _ = _membership(db, user)
    child = db.get(Child, child_id)
    if not child or child.family_id != family.id:
        raise HTTPException(404, "Child not found")
    if fam.section_for(child.birth_date, child.due_date, child.grade) != section:
        raise HTTPException(400, f"This child isn't in the {section} section")
    return child


def _marks(db: DbSession, child_id: int, kind: str) -> dict[str, ChildMark]:
    rows = db.scalars(select(ChildMark).where(ChildMark.child_id == child_id, ChildMark.kind == kind)).all()
    return {r.key: r for r in rows}


def _log_out(r: CareLog) -> dict:
    return {"id": r.id, "kind": r.kind, "at": r.at.isoformat(timespec="minutes"), "minutes": r.minutes, "note": r.note}


@router.get("/baby/{child_id}")
def baby_overview(child_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, "baby")
    today = india_today()
    born = date.fromisoformat(child.birth_date)
    months = fam.months_between(born, today)

    seen = _marks(db, child.id, "milestone")
    milestones = []
    for group in baby.MILESTONES:
        if group["months"] > months + 3 and milestones:
            break  # show what's past, now, and the next checkpoint only
        items = [{"id": mid, "text": text, "seen": mid in seen} for mid, text in group["items"]]
        past = months >= group["months"] + 1
        milestones.append({
            "months": group["months"],
            "items": items,
            "status": "past" if past else ("now" if months >= group["months"] - 1 else "next"),
            # Gentle, never a verdict: most children (3 in 4) do these by this age.
            "mention_to_doctor": past and any(not i["seen"] for i in items),
        })

    given = _marks(db, child.id, "vaccine")
    vaccines = []
    for v in baby.VACCINES:
        due = born + timedelta(days=v["due_days"])
        mark = given.get(v["id"])
        status = "given" if mark else "overdue" if today > due + OVERDUE_AFTER else "due" if today >= due else "upcoming"
        vaccines.append({**v, "due_on": due.isoformat(), "status": status, "given_on": mark.on_date if mark else None})

    start = datetime.combine(today - timedelta(days=6), datetime.min.time())
    logs = db.scalars(select(CareLog).where(CareLog.child_id == child.id, CareLog.at >= start).order_by(CareLog.at.desc())).all()
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_logs = [r for r in logs if r.at.date() == d]
        week.append({
            "day": d.isoformat(),
            "counts": {k: sum(1 for r in day_logs if r.kind == k) for k in baby.LOG_KINDS},
            "sleep_minutes": sum(r.minutes or 0 for r in day_logs if r.kind == "sleep"),
        })

    return {
        "child": {"id": child.id, "name": child.name, "age": fam.age_words(child.birth_date, None), "months": months},
        "today": today.isoformat(),
        "play": baby.play_for(months),
        "every_child": baby.EVERY_CHILD,
        "milestones": milestones,
        "vaccines": vaccines,
        "vaccine_note": baby.VACCINE_NOTE,
        "food": baby.food_for(months),
        "sleep": baby.SLEEP,
        "log_kinds": baby.LOG_KINDS,
        "log_today": [_log_out(r) for r in logs if r.at.date() == today],
        "log_week": week,
        "questions": baby.QUESTIONS,
        "see_doctor_now": baby.SEE_DOCTOR_NOW,
        "together_time": months >= 18,
        "sources": baby.SOURCES,
        "disclaimer": baby.DISCLAIMER,
    }


class SeenIn(BaseModel):
    seen: bool


@router.put("/baby/{child_id}/milestones/{milestone_id}")
def mark_milestone(child_id: int, milestone_id: str, body: SeenIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, "baby")
    if milestone_id not in baby.MILESTONE_IDS:
        raise HTTPException(404, "Unknown milestone")
    row = _marks(db, child.id, "milestone").get(milestone_id)
    if body.seen and not row:
        db.add(ChildMark(child_id=child.id, kind="milestone", key=milestone_id, on_date=india_today().isoformat(), by_id=user.id))
    elif not body.seen and row:
        db.delete(row)
    db.commit()
    return {"id": milestone_id, "seen": body.seen}


class GivenIn(BaseModel):
    given_on: str | None = None


@router.put("/baby/{child_id}/vaccines/{vaccine_id}")
def mark_vaccine(child_id: int, vaccine_id: str, body: GivenIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, "baby")
    if vaccine_id not in baby.VACCINE_IDS:
        raise HTTPException(404, "Unknown vaccine")
    if body.given_on is not None:
        try:
            day = date.fromisoformat(body.given_on)
        except ValueError:
            raise HTTPException(422, "Use a date like 2026-05-30")
        if not date.fromisoformat(child.birth_date) <= day <= india_today():
            raise HTTPException(422, "The date should be between birth and today")
    row = _marks(db, child.id, "vaccine").get(vaccine_id)
    if body.given_on and row:
        row.on_date = body.given_on
    elif body.given_on:
        db.add(ChildMark(child_id=child.id, kind="vaccine", key=vaccine_id, on_date=body.given_on, by_id=user.id))
    elif row:
        db.delete(row)
    db.commit()
    return {"id": vaccine_id, "given_on": body.given_on}


class LogIn(BaseModel):
    kind: str
    at: str | None = None  # "YYYY-MM-DDTHH:MM", India time; now if left out
    minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    note: str = Field(default="", max_length=300)


@router.post("/baby/{child_id}/log")
def add_log(child_id: int, body: LogIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, "baby")
    if body.kind not in baby.LOG_KINDS:
        raise HTTPException(400, "Unknown kind")
    now = datetime.now(IST).replace(tzinfo=None, second=0, microsecond=0)
    if body.at:
        try:
            at = datetime.fromisoformat(body.at).replace(tzinfo=None, second=0, microsecond=0)
        except ValueError:
            raise HTTPException(422, "Bad time")
        if not now - timedelta(days=7) <= at <= now + timedelta(minutes=5):
            raise HTTPException(422, "Log times within the last week")
    else:
        at = now
    row = CareLog(child_id=child.id, kind=body.kind, at=at, minutes=body.minutes, note=body.note.strip(), by_id=user.id)
    db.add(row)
    db.commit()
    return _log_out(row)


@router.delete("/baby/{child_id}/log/{log_id}", status_code=204)
def delete_log(child_id: int, log_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, "baby")
    row = db.get(CareLog, log_id)
    if not row or row.child_id != child.id:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()


@router.get("/pregnancy/{child_id}")
def pregnancy_overview(child_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    child = _child(db, user, child_id, "pregnancy")
    due = date.fromisoformat(child.due_date or child.birth_date)
    week = pregnancy.week_of((due - india_today()).days)
    month = pregnancy.month_of(week)
    return {
        "child": {"id": child.id, "name": child.name, "due_date": due.isoformat(), "due_words": fam.age_words(None, due.isoformat())},
        "week": week,
        "month": pregnancy.MONTHS[month - 1],
        "next_month": pregnancy.MONTHS[month] if month < 9 else None,
        "care": pregnancy.CARE,
        "calm": pregnancy.CALM,
        "go_to_hospital_now": pregnancy.GO_TO_HOSPITAL_NOW,
        "sources": pregnancy.SOURCES,
        "disclaimer": pregnancy.DISCLAIMER,
    }
