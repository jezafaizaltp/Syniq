"""Print what content the database holds: one line, for deploy/lab/check.sh. Changes nothing.

    python -m tools.content_counts          # e.g. "15 subjects, 410 topics, 3,912 questions (1,020 harder)"
Exits 1 when there are no questions at all (the content packs did not load).
"""

import sys

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Concept, Item, Subject


def counts() -> dict:
    with SessionLocal() as db:
        approved = Item.status == "approved"
        return {
            "subjects": db.scalar(select(func.count(Subject.id))) or 0,
            "topics": db.scalar(select(func.count(Concept.id))) or 0,
            "questions": db.scalar(select(func.count(Item.id)).where(approved)) or 0,
            "harder": db.scalar(select(func.count(Item.id)).where(approved, Item.difficulty >= 3)) or 0,
        }


def main() -> int:
    c = counts()
    print(f"{c['subjects']:,} subjects, {c['topics']:,} topics, {c['questions']:,} questions ({c['harder']:,} harder)")
    return 0 if c["questions"] else 1


if __name__ == "__main__":
    sys.exit(main())
