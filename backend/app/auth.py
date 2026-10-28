import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .db import get_db
from .models import AuditLog, Consent, GuardianLink, Session, User

PBKDF2_ROUNDS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
    return hmac.compare_digest(check.hex(), digest)


def new_token(db: DbSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(Session(token=token, user_id=user.id))
    db.commit()
    return token


def current_user(authorization: str = Header(default=""), db: DbSession = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in")
    sess = db.get(Session, authorization.removeprefix("Bearer ").strip())
    if not sess:
        raise HTTPException(401, "Session expired")
    return sess.user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Not allowed for this role")
        return user

    return dep


def has_consent(db: DbSession, student_id: int, scope: str) -> bool:
    latest = db.scalars(
        select(Consent)
        .where(Consent.student_id == student_id, Consent.scope == scope)
        .order_by(Consent.created_at.desc(), Consent.id.desc())
    ).first()
    return bool(latest and latest.granted)


def require_learning_consent(user: User = Depends(require_role("student")), db: DbSession = Depends(get_db)) -> User:
    """No learning data is processed until a guardian has consented."""
    if not has_consent(db, user.id, "core_learning"):
        raise HTTPException(403, "Waiting for a parent or guardian to give consent")
    return user


def guardian_of(db: DbSession, guardian: User, student_id: int) -> bool:
    return (
        db.scalars(
            select(GuardianLink).where(
                GuardianLink.guardian_id == guardian.id, GuardianLink.student_id == student_id
            )
        ).first()
        is not None
    )


def audit(db: DbSession, actor: User, action: str, student_id: int | None = None) -> None:
    db.add(AuditLog(actor_id=actor.id, action=action, subject_student_id=student_id))
    db.commit()
