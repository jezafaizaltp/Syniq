"""Re-fit the mastery (BKT) settings to real answers. Reads the database, changes nothing.

The settings in app/engine/mastery.py (P_INIT, P_TRANSIT, SLIP, GUESS) were tuned on simulated learners
(docs/learner-simulation.md). After the first few weeks of the pilot, run this on the lab computer's copy of the
database to see which settings predict the students' real next answers best:

    cd backend
    python -m tools.fit_mastery                      # all answers
    python -m tools.fit_mastery --subject math       # one subject code
    python -m tools.fit_mastery --min-answers 3000   # refuse to suggest anything on less data

It replays every student's answers on every topic in order and scores each setting by how well it predicted the
next answer (average log-likelihood; higher is better), then prints the current settings, the best ones found and
how much better they predict. Only answers are used: no names, no times, no marks.

It is a suggestion for a person to look at, not an automatic change: copy the numbers into engine/mastery.py only if
the gain is clear and the values make sense (for example, SLIP above 0.3 would mean the questions are confusing).
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from dataclasses import dataclass

from sqlalchemy import select

from app.db import SessionLocal
from app.engine import mastery as m
from app.models import Attempt, Chapter, Concept, Item, Subject


@dataclass(frozen=True)
class Params:
    p_init: float
    p_transit: float
    slip: float
    guess_mcq: float
    guess_numeric: float


CURRENT = Params(m.P_INIT, m.P_TRANSIT, m.SLIP, m.GUESS["mcq"], m.GUESS["numeric"])
GRID = {
    "p_init": [0.1, 0.2, 0.3, 0.4],
    "p_transit": [0.04, 0.06, 0.08, 0.12, 0.16],
    "slip": [0.05, 0.1, 0.15, 0.2],
    "guess_mcq": [0.2, 0.25, 0.3, 0.35],
    "guess_numeric": [0.02, 0.05, 0.1],
}


@dataclass
class Answer:
    correct: bool
    kind: str
    hints: int


def guess_for(p: Params, kind: str, hints: int) -> float:
    g = p.guess_numeric if kind == "numeric" else p.guess_mcq
    return min(0.6, g + 0.15 * hints) if hints else g


def score(seqs: list[list[Answer]], p: Params) -> float:
    """Average log-likelihood of each answer, predicted from the answers before it on that topic."""
    total, n = 0.0, 0
    for seq in seqs:
        known = p.p_init
        for a in seq:
            g = guess_for(p, a.kind, a.hints)
            right = known * (1 - p.slip) + (1 - known) * g
            right = min(max(right, 1e-6), 1 - 1e-6)
            total += math.log(right if a.correct else 1 - right)
            n += 1
            if a.correct:
                num, den = known * (1 - p.slip), known * (1 - p.slip) + (1 - known) * g
            else:
                num, den = known * p.slip, known * p.slip + (1 - known) * (1 - g)
            post = num / den if den else known
            known = post + (1 - post) * p.p_transit
    return total / n if n else float("-inf")


def load(subject: str | None) -> list[list[Answer]]:
    with SessionLocal() as db:
        q = (
            select(Attempt.student_id, Attempt.concept_id, Attempt.correct, Attempt.hints_used, Item.kind)
            .join(Item, Item.id == Attempt.item_id)
            .order_by(Attempt.student_id, Attempt.concept_id, Attempt.created_at, Attempt.id)
        )
        if subject:
            q = (
                q.join(Concept, Concept.id == Attempt.concept_id)
                .join(Chapter, Chapter.id == Concept.chapter_id)
                .join(Subject, Subject.id == Chapter.subject_id)
                .where(Subject.code == subject)
            )
        seqs: dict[tuple[int, int], list[Answer]] = {}
        for sid, cid, correct, hints, kind in db.execute(q).all():
            seqs.setdefault((sid, cid), []).append(Answer(bool(correct), kind, hints or 0))
        return list(seqs.values())


def fit(seqs: list[list[Answer]]) -> tuple[Params, float]:
    best, best_score = CURRENT, score(seqs, CURRENT)
    for values in itertools.product(*GRID.values()):
        p = Params(*values)
        s = score(seqs, p)
        if s > best_score:
            best, best_score = p, s
    return best, best_score


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--subject", help="only this subject code, e.g. math")
    ap.add_argument("--min-answers", type=int, default=2000, help="below this many answers, don't suggest a change")
    args = ap.parse_args(argv)

    seqs = load(args.subject)
    answers = sum(len(s) for s in seqs)
    print(f"{answers:,} answers on {len(seqs):,} student-topic pairs")
    if not answers:
        print("No answers yet.")
        return 1
    now = score(seqs, CURRENT)
    best, best_score = fit(seqs)
    print(f"current  {CURRENT}  score {now:.4f}")
    print(f"best     {best}  score {best_score:.4f}")
    gain = best_score - now
    print(f"gain     {gain:+.4f} per answer")
    if answers < args.min_answers:
        print(f"Only {answers:,} answers: too few to change anything yet (want {args.min_answers:,}).")
    elif gain < 0.005:
        print("The current settings already fit about as well. Keep them.")
    else:
        print("Worth a look: the best settings predict real answers clearly better. See the note at the top of this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
