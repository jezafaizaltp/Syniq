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
P_TRANSIT = 0.15
SLIP = 0.1
GUESS = {"mcq": 0.25, "numeric": 0.05}
SECURE_THRESHOLD = 0.95
MIN_ATTEMPTS_TO_SECURE = 3

# Spaced review after a concept is secured: 2 days, then 7, then 21, then 60.
REVIEW_INTERVALS_DAYS = [2, 7, 21, 60]


@dataclass
class Evidence:
    correct: bool
    kind: str = "mcq"
    hints_used: int = 0


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
