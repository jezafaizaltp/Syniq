"""A replaced textbook: the old subject is kept under another code and board, and the new book loads in its place."""

from sqlalchemy import select

from tests.test_api import client  # noqa: F401  first: points the app at a fresh test database

from app import content_packs
from app.db import SessionLocal
from app.models import Chapter, Subject


def test_old_book_is_retired_once_and_new_book_is_left_alone():
    with SessionLocal() as db:
        # The test database already has the new book: nothing is retired.
        assert content_packs.sync_subjects(db) == []
        new = db.scalars(select(Subject).where(Subject.code == "cbse9-math")).first()
        assert db.scalars(select(Chapter).where(Chapter.subject_id == new.id, Chapter.number == 1)).first().title.startswith("Orienting")

        # An older database: cbse9-math still holds the old book.
        new.code = "cbse9-math-new-test"
        old = Subject(code="cbse9-math", name="Mathematics", language="en", syllabus="cbse", grade=9)
        db.add(old)
        db.flush()
        db.add(Chapter(subject_id=old.id, number=1, title="Number Systems"))
        db.flush()
        done = content_packs.sync_subjects(db)
        assert "retired subject cbse9-math as cbse9old-math" in done and "added subject cbse9-math" in done
        assert (old.code, old.syllabus) == ("cbse9old-math", "cbse-old")
        assert content_packs.sync_subjects(db) == []  # only once
        db.rollback()
