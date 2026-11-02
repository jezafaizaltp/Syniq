"""Interest exploration: short activities across five areas, for every student.

See app/interests.py for the activities and why SYNiq never labels a student from them.
Reflections are private: no teacher, parent or engine endpoint reads them.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import interests
from ..auth import require_learning_consent
from ..db import get_db
from ..models import InterestReflection, User

router = APIRouter(prefix="/explore", tags=["explore"])


def _latest(db: DbSession, user: User) -> dict[str, InterestReflection]:
    rows = db.scalars(
        select(InterestReflection).where(InterestReflection.student_id == user.id).order_by(InterestReflection.id)
    ).all()
    return {r.activity_id: r for r in rows}  # the latest reflection per activity wins


def _card(a: dict, done: dict[str, InterestReflection]) -> dict:
    r = done.get(a["id"])
    return {"id": a["id"], "area": a["area"], "title": a["title"], "minutes": a["minutes"], "feeling": r.feeling if r else None}


@router.get("")
def overview(db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    done = _latest(db, user)
    return {
        "areas": [
            {"area": area, "activities": [_card(a, done) for a in interests.ACTIVITIES if a["area"] == area]}
            for area in interests.AREAS
        ],
        "suggested": [_card(interests.BY_ID[i], done) for i in interests.suggest({k: v.feeling for k, v in done.items()})],
        "enjoyed": [_card(interests.BY_ID[k], done) for k, v in done.items() if v.feeling == "loved" and k in interests.BY_ID],
    }


@router.get("/{activity_id}")
def activity(activity_id: str, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    a = interests.BY_ID.get(activity_id)
    if not a:
        raise HTTPException(404, "Activity not found")
    r = _latest(db, user).get(activity_id)
    return {**a, "feeling": r.feeling if r else None, "note": r.note if r else ""}


class ReflectionIn(BaseModel):
    feeling: str = Field(pattern="^(loved|okay|not_for_me)$")
    note: str = Field(default="", max_length=1000)


@router.post("/{activity_id}/reflect")
def reflect(activity_id: str, body: ReflectionIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    if activity_id not in interests.BY_ID:
        raise HTTPException(404, "Activity not found")
    db.add(InterestReflection(student_id=user.id, activity_id=activity_id, feeling=body.feeling, note=body.note.strip()))
    db.commit()
    return {"ok": True}
