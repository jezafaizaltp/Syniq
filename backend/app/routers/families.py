"""Family accounts for SYNiq outside school.

The holder (usually the mother) signs up, adds children from pregnancy onwards, and invites
other adults (father, grandparents) with their own logins. Only the holder adds or removes
people or makes a child's login. Every change is in the audit log.
"""

import re
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import family as fam
from ..auth import (
    MIN_PASSWORD,
    audit,
    hash_password,
    login_blocked,
    new_token,
    record_login_failure,
    require_role,
    temporary_password,
)
from ..db import get_db
from ..models import CareLog, Child, ChildMark, Consent, Family, FamilyMember, GuardianLink, ScreenTimeSession, Session, User

router = APIRouter(tags=["family"])

MAX_CHILDREN = 12
MAX_ADULTS = 8
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")


def _email_taken(db: DbSession, email: str) -> bool:
    return db.scalars(select(User.id).where(User.email == email)).first() is not None


def _check_day(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("Use a date like 2025-06-30")
    return value


# --- Sign up ------------------------------------------------------------------------

class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=EMAIL, max_length=200)
    password: str = Field(min_length=MIN_PASSWORD, max_length=200)
    relation: str = "mother"
    family_name: str = Field(default="", max_length=120)


@router.post("/auth/signup")
def signup(body: SignupIn, request: Request, db: DbSession = Depends(get_db)):
    """Anyone can start a family account. The person who signs up holds it."""
    key = f"signup|{request.client.host if request.client else ''}"
    if login_blocked(key):
        raise HTTPException(429, "Too many tries. Please wait a few minutes.")
    record_login_failure(key)  # counts every sign-up, so one address can't make hundreds of accounts
    if body.relation not in fam.RELATIONS:
        raise HTTPException(400, "Unknown relation")
    email = body.email.lower().strip()
    if _email_taken(db, email):
        raise HTTPException(409, "That email already has a SYNiq account. Sign in instead.")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password), role="guardian", settings={})
    db.add(user)
    db.flush()
    family = Family(name=body.family_name.strip() or f"{user.name}'s family", holder_id=user.id)
    db.add(family)
    db.flush()
    db.add(FamilyMember(family_id=family.id, user_id=user.id, relation=body.relation))
    db.commit()
    audit(db, user, "family_signup")
    return {"token": new_token(db, user), "role": user.role, "name": user.name}


# --- Who's in the family ------------------------------------------------------------

def _membership(db: DbSession, user: User) -> tuple[Family, FamilyMember]:
    member = db.scalars(select(FamilyMember).where(FamilyMember.user_id == user.id)).first()
    if not member:
        raise HTTPException(404, "No family account")
    return db.get(Family, member.family_id), member


def _holder(db: DbSession, user: User) -> Family:
    family, _ = _membership(db, user)
    if family.holder_id != user.id:
        raise HTTPException(403, "Only the account holder can do this")
    return family


def _child(db: DbSession, family: Family, child_id: int) -> Child:
    child = db.get(Child, child_id)
    if not child or child.family_id != family.id:
        raise HTTPException(404, "Child not found")
    return child


def _child_out(db: DbSession, c: Child) -> dict:
    section = fam.section_for(c.birth_date, c.due_date, c.grade)
    login = db.get(User, c.student_id).email if c.student_id else None
    return {
        "id": c.id,
        "name": c.name,
        "birth_date": c.birth_date,
        "due_date": c.due_date,
        "board": c.board,
        "grade": c.grade,
        "grade_name": fam.grade_name(c.grade),
        "age": fam.age_words(c.birth_date, c.due_date),
        "section": section,
        "login": login,
        "student_id": c.student_id,
    }


@router.get("/family")
def my_family(db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    family, member = _membership(db, user)
    adults = db.scalars(select(FamilyMember).where(FamilyMember.family_id == family.id).order_by(FamilyMember.id)).all()
    children = db.scalars(select(Child).where(Child.family_id == family.id).order_by(Child.id)).all()
    return {
        "id": family.id,
        "name": family.name,
        "plan": family.plan,
        "you": {"relation": member.relation, "holder": family.holder_id == user.id},
        "adults": [
            {"id": m.id, "name": db.get(User, m.user_id).name, "relation": m.relation, "holder": m.user_id == family.holder_id, "you": m.user_id == user.id}
            for m in adults
        ],
        "children": [_child_out(db, c) for c in children],
        "sections": fam.SECTIONS,
        "boards": fam.BOARDS,
        "grades": [{"value": g, "name": fam.grade_name(g)} for g in fam.GRADES],
    }


# --- Children -----------------------------------------------------------------------

class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birth_date: str | None = None
    due_date: str | None = None
    board: str = "cbse"
    grade: int | None = None

    @field_validator("birth_date", "due_date")
    @classmethod
    def days(cls, v: str | None) -> str | None:
        return _check_day(v)

    @model_validator(mode="after")
    def sensible(self):
        today = date.today()
        if not self.birth_date and not self.due_date:
            raise ValueError("Add a date of birth, or the due date if you're expecting")
        if self.birth_date and date.fromisoformat(self.birth_date) > today:
            raise ValueError("The date of birth can't be in the future")
        if self.birth_date and date.fromisoformat(self.birth_date) < today - timedelta(days=365 * 20):
            raise ValueError("SYNiq is for children up to Class 12")
        if self.due_date and not self.birth_date and not today - timedelta(days=30) <= date.fromisoformat(self.due_date) <= today + timedelta(days=300):
            raise ValueError("The due date should be within the next 10 months")
        if self.board not in fam.BOARDS:
            raise ValueError("Unknown board")
        if self.grade is not None and self.grade not in fam.GRADES:
            raise ValueError("Unknown class")
        if self.grade is not None and not self.birth_date:
            raise ValueError("Add the date of birth for a child in school")
        return self


@router.post("/family/children")
def add_child(body: ChildIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    family = _holder(db, user)
    if db.query(Child).filter_by(family_id=family.id).count() >= MAX_CHILDREN:
        raise HTTPException(400, "That's the most children one account can hold")
    child = Child(family_id=family.id, name=body.name.strip(), birth_date=body.birth_date, due_date=None if body.birth_date else body.due_date, board=body.board, grade=body.grade)
    db.add(child)
    db.commit()
    audit(db, user, "family_add_child", child.student_id)
    return _child_out(db, child)


@router.put("/family/children/{child_id}")
def update_child(child_id: int, body: ChildIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    family = _holder(db, user)
    child = _child(db, family, child_id)
    if child.student_id and body.grade is None:
        raise HTTPException(400, "This child has a login, so they need a class")
    child.name = body.name.strip()
    child.birth_date = body.birth_date
    child.due_date = None if body.birth_date else body.due_date
    child.board = body.board
    child.grade = body.grade
    if child.student_id:
        _sync_student(db, child)
    db.commit()
    audit(db, user, "family_update_child", child.student_id)
    return _child_out(db, child)


@router.delete("/family/children/{child_id}", status_code=204)
def remove_child(child_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Removes the child from the family. A child with their own login keeps it until it is closed with the school or support."""
    family = _holder(db, user)
    child = _child(db, family, child_id)
    if child.student_id:
        raise HTTPException(400, "This child has their own login. Close the login first.")
    for model in (ScreenTimeSession, ChildMark, CareLog):
        for row in db.scalars(select(model).where(model.child_id == child.id)).all():
            db.delete(row)
    db.delete(child)
    db.commit()
    audit(db, user, "family_remove_child")


def _sync_student(db: DbSession, child: Child) -> None:
    """The class and board a child learns in follow what the parent set."""
    student = db.get(User, child.student_id)
    student.name = child.name
    student.settings = {**(student.settings or {}), "board": child.board, "grade": child.grade}


class ChildLoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=200)


@router.post("/family/children/{child_id}/login")
def make_child_login(child_id: int, body: ChildLoginIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """A school-age child gets their own login. Making it is the holder's consent for SYNiq to adapt to them."""
    family = _holder(db, user)
    child = _child(db, family, child_id)
    if child.student_id:
        raise HTTPException(400, "This child already has a login")
    if fam.section_for(child.birth_date, child.due_date, child.grade) != "school" or child.grade is None:
        raise HTTPException(400, "Set the child's class first. Logins are for children in LKG to Class 12.")
    login = body.username.lower().strip()
    if not (USERNAME.match(login) or re.match(EMAIL, login)):
        raise HTTPException(400, "Use 3 to 40 letters, numbers, dots or dashes, or an email address")
    if _email_taken(db, login):
        raise HTTPException(409, "That login is taken. Try another.")
    pw = temporary_password()
    student = User(name=child.name, email=login, password_hash=hash_password(pw), role="student", settings={}, must_change_password=True)
    db.add(student)
    db.flush()
    child.student_id = student.id
    _sync_student(db, child)
    for m in db.scalars(select(FamilyMember).where(FamilyMember.family_id == family.id)).all():
        db.add(GuardianLink(guardian_id=m.user_id, student_id=student.id))
    db.add(Consent(student_id=student.id, guardian_id=user.id, scope="core_learning", granted=True, method="family_app"))
    db.commit()
    audit(db, user, "family_child_login", student.id)
    audit(db, user, "consent:core_learning:yes", student.id)
    return {"name": child.name, "login": login, "temporary_password": pw}


# --- Other adults -------------------------------------------------------------------

class AdultIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=EMAIL, max_length=200)
    relation: str


@router.post("/family/adults")
def invite_adult(body: AdultIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    family = _holder(db, user)
    if body.relation not in fam.RELATIONS:
        raise HTTPException(400, "Unknown relation")
    if db.query(FamilyMember).filter_by(family_id=family.id).count() >= MAX_ADULTS:
        raise HTTPException(400, "That's the most adults one account can hold")
    email = body.email.lower().strip()
    if _email_taken(db, email):
        raise HTTPException(409, "That email already has a SYNiq account")
    pw = temporary_password()
    adult = User(name=body.name.strip(), email=email, password_hash=hash_password(pw), role="guardian", settings={}, must_change_password=True)
    db.add(adult)
    db.flush()
    db.add(FamilyMember(family_id=family.id, user_id=adult.id, relation=body.relation))
    for c in db.scalars(select(Child).where(Child.family_id == family.id, Child.student_id.is_not(None))).all():
        db.add(GuardianLink(guardian_id=adult.id, student_id=c.student_id))
    db.commit()
    audit(db, user, f"family_add_adult:{body.relation}")
    return {"name": adult.name, "login": email, "temporary_password": pw}


@router.delete("/family/adults/{member_id}", status_code=204)
def remove_adult(member_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Takes an adult out of the family: they lose sight of the children and can no longer sign in."""
    family = _holder(db, user)
    member = db.get(FamilyMember, member_id)
    if not member or member.family_id != family.id:
        raise HTTPException(404, "Not found")
    if member.user_id == family.holder_id:
        raise HTTPException(400, "The account holder can't be removed")
    student_ids = [c.student_id for c in db.scalars(select(Child).where(Child.family_id == family.id)).all() if c.student_id]
    for link in db.scalars(select(GuardianLink).where(GuardianLink.guardian_id == member.user_id, GuardianLink.student_id.in_(student_ids))).all():
        db.delete(link)
    for s in db.scalars(select(Session).where(Session.user_id == member.user_id)).all():
        db.delete(s)
    adult = db.get(User, member.user_id)
    adult.password_hash = "closed"  # never matches, so the login stops working; the row stays for the audit log
    db.delete(member)
    db.commit()
    audit(db, user, "family_remove_adult")
