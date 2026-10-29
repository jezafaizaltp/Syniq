import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .db import get_db
from .models import AuditLog, Consent, GuardianLink, Session, User, utcnow

PBKDF2_ROUNDS = 200_000
SESSION_IDLE = timedelta(days=14)  # signed out after two weeks without use
MIN_PASSWORD = 8

# Letters and digits that are hard to confuse when read off a printed sheet.
_TEMP_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def temporary_password() -> str:
    """Easy to type from a printed sheet, e.g. 'kq7m-xp3t'."""
    pick = lambda n: "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(n))  # noqa: E731
    return f"{pick(4)}-{pick(4)}"


# --- Sign-in attempt limits ----------------------------------------------------------
# Per process: enough to stop password guessing against children's accounts.
LOGIN_WINDOW = 15 * 60
LOGIN_MAX_FAILURES = 10
_failures: dict[str, deque] = defaultdict(deque)


def login_blocked(key: str) -> bool:
    q = _failures[key]
    while q and q[0] < time.monotonic() - LOGIN_WINDOW:
        q.popleft()
    return len(q) >= LOGIN_MAX_FAILURES


def record_login_failure(key: str) -> None:
    _failures[key].append(time.monotonic())


def clear_login_failures(key: str) -> None:
    _failures.pop(key, None)


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
    now = utcnow()
    if not sess or now - (sess.last_seen_at or sess.created_at) > SESSION_IDLE:
        raise HTTPException(401, "Session expired")
    if now - (sess.last_seen_at or sess.created_at) > timedelta(hours=1):
        sess.last_seen_at = now
        db.commit()
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
