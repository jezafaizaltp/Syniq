"""Mastery estimation with Bayesian Knowledge Tracing (BKT).

Each concept holds a probability that the student knows it. Every answer moves
that probability by an amount that depends on how informative the answer is:
a lucky guess on a multiple-choice item, or a correct answer reached with hints,
counts for less than an unaided correct answer.

Response time is stored with each attempt but deliberately not used here:
speed is not the same as understanding.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

P_INIT = 0.2
# Tuned 2026-11 with simulated learners (tools/learner_sim.py, docs/learner-simulation.md): the old
# values (0.15, 0.95, 3 answers, first review after 2 days) called many topics secure after three lucky
# right answers in a row, so the learner moved on while they still knew too little.
P_TRANSIT = 0.08
SLIP = 0.1
GUESS = {"mcq": 0.25, "numeric": 0.05}
SECURE_THRESHOLD = 0.98
MIN_ATTEMPTS_TO_SECURE = 5
# A topic that has harder questions (difficulty 3) is not called secure until one of them has been
# answered right: easy questions answered well are not the whole topic. Until then the estimate stops
# just short of secure, which also makes practice step up to the harder questions (rules.target_difficulty).
HARD = 3
CAP_UNTIL_HARD_RIGHT = 0.97

# Spaced review after a concept is secured: the next day, then 3, 7, 21 and 60 days.
REVIEW_INTERVALS_DAYS = [1, 3, 7, 21, 60]


@dataclass
class Evidence:
    correct: bool
    kind: str = "mcq"
    hints_used: int = 0


def expected_correct(p: float, ev: Evidence) -> float:
    """Chance of a right answer from what was known just before it (BKT's own prediction)."""
    guess = GUESS.get(ev.kind, 0.2)
    if ev.hints_used:
        guess = min(0.6, guess + 0.15 * ev.hints_used)
    return p * (1 - SLIP) + (1 - p) * guess


def update_p_known(p: float, ev: Evidence) -> float:
    guess = GUESS.get(ev.kind, 0.2)
    # Each hint makes a correct answer less telling about unaided knowledge.
    slip = SLIP
    if ev.correct and ev.hints_used:
        guess = min(0.6, guess + 0.15 * ev.hints_used)

    if ev.correct:
        num = p * (1 - slip)
        den = num + (1 - p) * guess
    else:
        num = p * slip
        den = num + (1 - p) * (1 - guess)
    posterior = num / den if den else p
    return posterior + (1 - posterior) * P_TRANSIT


def cap_until_hard_right(p: float, has_hard: bool, hard_right: bool, was_secure: bool) -> float:
    """Keep a topic just short of secure until one harder question is answered right.

    A topic that was already secure stays secure (this rule is not used to take it away)."""
    if has_hard and not hard_right and not was_secure and p >= SECURE_THRESHOLD:
        return CAP_UNTIL_HARD_RIGHT
    return p


def is_secure(p: float, attempts: int) -> bool:
    return p >= SECURE_THRESHOLD and attempts >= MIN_ATTEMPTS_TO_SECURE


def next_review(now: datetime, review_count: int) -> datetime:
    idx = min(review_count, len(REVIEW_INTERVALS_DAYS) - 1)
    return now + timedelta(days=REVIEW_INTERVALS_DAYS[idx])


def progress_label(p: float, attempts: int) -> str:
    """Words a student or guardian sees instead of a number."""
    if attempts == 0:
        return "not_started"
    if is_secure(p, attempts):
        return "secure"
    if p >= 0.6:
        return "getting_there"
    return "learning"
