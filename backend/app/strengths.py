"""Strengths: what comes easily to a learner and what they love doing, so it can be grown.

Every child has things they are good at, and a disabled child's strengths are easy to miss when
everyone looks at what is hard. SYNiq looks at four signals, each against the child's own
record, never against other children:

- a subject where their first-try answers are clearly better than in their other subjects;
- kinds of thinking puzzle that are growing (only with the parent's thinking-puzzles consent);
- Explore areas they loved (making, fixing, finding out, people, ideas, movement, nature, technology);
- what they keep choosing to do (hands-on activities).

What comes back is words and ways to grow it, never a score, a rank or a label such as
"gifted". It changes as the child does, and every area stays open: suggestions include
somewhere new as well as more of what they love.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from . import interests, learning, thinking
from .models import Attempt, Chapter, Concept, InterestReflection, LearningEvent, PuzzleAnswer, Subject, User

MIN_ANSWERS = 15  # answers in a subject before it can count as a strength
LEAD = 0.10  # first-try rate above the child's own overall rate
FLOOR = 0.60  # and at least this many right first time
MAX_SUBJECTS = 2
HANDS_ON_MIN = 5  # activities opened before "learning with your hands" shows


def family(subject_name: str) -> str:
    """A subject's family, for choosing ways to grow a strength in it."""
    n = subject_name.lower()
    if any(w in n for w in ("math", "ganit")):
        return "maths"
    if any(w in n for w in ("physics", "chemistry", "biology", "science", "evs", "world")):
        return "science"
    if any(w in n for w in ("english", "hindi", "malayalam", "sanskrit")):
        return "language"
    if any(w in n for w in ("social", "history", "geography", "civics", "economics", "society")):
        return "social"
    if any(w in n for w in ("it", "computer", "information")):
        return "technology"
    return "general"


@dataclass
class SubjectRecord:
    name: str
    answers: int
    first_try: int


def subject_strengths(records: list[SubjectRecord]) -> list[SubjectRecord]:
    """Subjects clearly ahead of the child's own overall first-try rate."""
    total = sum(r.answers for r in records)
    if total < MIN_ANSWERS * 2 or len([r for r in records if r.answers >= MIN_ANSWERS]) < 2:
        return []  # one subject alone can't stand out from the child's other subjects
    overall = sum(r.first_try for r in records) / total
    ahead = [r for r in records if r.answers >= MIN_ANSWERS and r.first_try / r.answers >= max(FLOOR, overall + LEAD)]
    return sorted(ahead, key=lambda r: -r.first_try / r.answers)[:MAX_SUBJECTS]


def _subject_records(db: DbSession, student_id: int) -> list[SubjectRecord]:
    rows = db.execute(
        select(Subject.name, Attempt.correct, Attempt.hints_used)
        .join(Concept, Concept.id == Attempt.concept_id)
        .join(Chapter, Chapter.id == Concept.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .where(Attempt.student_id == student_id)
    ).all()
    by: dict[str, SubjectRecord] = {}
    for name, correct, hints in rows:
        r = by.setdefault(name, SubjectRecord(name, 0, 0))
        r.answers += 1
        r.first_try += int(bool(correct) and not hints)
    return list(by.values())


def strengths(db: DbSession, student: User, puzzles_allowed: bool) -> dict:
    """The child's strengths in words, each with ways to grow it."""
    out: list[dict] = []
    for r in subject_strengths(_subject_records(db, student.id)):
        out.append({"kind": "subject", "subject": r.name, "family": family(r.name)})

    if puzzles_allowed:
        rows = db.scalars(select(PuzzleAnswer).where(PuzzleAnswer.student_id == student.id).order_by(PuzzleAnswer.id)).all()
        _, grade = learning.class_of(student)
        history = [thinking.Answer(p.domain, p.level, p.correct) for p in rows]
        for g in thinking.growth(history, grade):
            if g["trend"] == "growing":
                out.append({"kind": "thinking", "domain": g["domain"]})

    latest: dict[str, str] = {}
    for r in db.scalars(select(InterestReflection).where(InterestReflection.student_id == student.id).order_by(InterestReflection.id)):
        latest[r.activity_id] = r.feeling
    loved = [interests.BY_ID[a]["area"] for a, f in latest.items() if f == "loved" and a in interests.BY_ID]
    for area in dict.fromkeys(loved):
        tried = {a for a in latest}
        next_ = [a for a in interests.ACTIVITIES if a["area"] == area and a["id"] not in tried][:1]
        out.append({"kind": "explore", "area": area, "next": [{"id": a["id"], "title": a["title"]} for a in next_]})

    hands_on = db.scalars(
        select(LearningEvent).where(LearningEvent.student_id == student.id, LearningEvent.kind == "activity")
    ).all()
    if len(hands_on) >= HANDS_ON_MIN:
        out.append({"kind": "hands_on"})

    # Somewhere new to try, so nobody is boxed in by what they found first.
    untried = [a for a in interests.ACTIVITIES if a["id"] not in latest and a["area"] not in loved]
    return {"strengths": out, "try_new": {"id": untried[0]["id"], "title": untried[0]["title"], "area": untried[0]["area"]} if untried else None}
