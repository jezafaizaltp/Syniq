"""Prepare a fresh live server: the nine Class 9 subjects and the first admin.

No demo students, content or passwords. Safe to run more than once.

Run:  SYNIQ_ADMIN_EMAIL=... SYNIQ_ADMIN_PASSWORD=... python -m app.bootstrap
"""

import os
import sys

from sqlalchemy import select

from .auth import MIN_PASSWORD, hash_password
from .db import SessionLocal
from . import content_packs
from .models import Subject, User
from .seed import SUBJECTS


def bootstrap(db, admin_email: str, admin_password: str, admin_name: str = "School admin") -> list[str]:
    done = []
    have = {s.code for s in db.scalars(select(Subject)).all()}
    for code, name, lang in SUBJECTS:
        if code not in have:
            db.add(Subject(code=code, name=name, language=lang))
            done.append(f"added subject {name}")
    email = admin_email.lower().strip()
    if not db.scalars(select(User).where(User.email == email)).first():
        if len(admin_password) < MIN_PASSWORD:
            raise ValueError(f"The admin password needs at least {MIN_PASSWORD} characters")
        db.add(User(name=admin_name, email=email, password_hash=hash_password(admin_password), role="admin", settings={}))
        done.append(f"added admin {email}")
    db.commit()
    packs = content_packs.read_packs()
    if packs and not content_packs.check_all(packs):
        counts = content_packs.load(db, packs)
        if any(counts.values()):
            done.append(f"loaded content: {counts['chapters']} new chapters, {counts['items']} new questions")
    return done


def main() -> None:
    email, password = os.environ.get("SYNIQ_ADMIN_EMAIL"), os.environ.get("SYNIQ_ADMIN_PASSWORD")
    if not email or not password:
        sys.exit("Set SYNIQ_ADMIN_EMAIL and SYNIQ_ADMIN_PASSWORD")
    with SessionLocal() as db:
        for line in bootstrap(db, email, password) or ["nothing to do"]:
            print(line)


if __name__ == "__main__":
    main()
