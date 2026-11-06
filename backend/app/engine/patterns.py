"""Mistake patterns: the same kind of mistake made more than once, across topics.

Each wrong answer that matches a known mistake (a misconception tag written with
the question, or a slip spotted in a sum) is one sighting. A mistake made twice or
more is a pattern. A pattern counts as fixed once the student has met the same
trap again, after the last sighting, and got it right enough times in a row.

What SYNiq does with a pattern:
- picks practice questions that carry the same trap, so it gets fixed rather than
  avoided (learning.pick_item);
- tells the student, without giving anything away, that this question has a trap
  they've met before;
- shows the student, their parents and teachers what is being worked on and
  what is fixed. Never as a score, never as a label about the child.

It also learns which way of explaining a mistake helps this student: after each
response to a wrong answer (count_it_out, step_by_step, real_life, try_similar),
the next answer on that topic shows whether it helped.

Pure functions, so they can be tested without a database.
"""

from dataclasses import dataclass, field
from datetime import datetime

PATTERNS_VERSION = "2026.11-1"

PATTERN_MIN = 2  # sightings before a mistake counts as a pattern
FIXED_AFTER = 3  # right answers in a row on the same trap, after the last sighting

# Which response to a wrong answer fits each way of explaining.
METHOD_TO_MODE = {
    "visual": "count_it_out",
    "step_by_step": "step_by_step",
    "real_world": "real_life",
    "text": "step_by_step",
}
MODE_MIN = 2  # answers after a response mode before its record counts
PREFERRED_BONUS = 0.15


@dataclass
class Sighting:
    """One answer to a question that carries one or more known traps."""

    concept_id: int
    traps: list[str]  # the mistakes this question can catch
    made: str | None  # the mistake made, if the answer was one of them
    correct: bool
    at: datetime


@dataclass
class Pattern:
    tag: str
    times: int
    topics: list[int] = field(default_factory=list)
    status: str = "working_on"  # working_on | fixed
    right_since: int = 0
    last_seen: datetime | None = None


def find(sightings: list[Sighting]) -> list[Pattern]:
    """Mistakes made at least PATTERN_MIN times, newest first, with whether they're fixed."""
    out: dict[str, Pattern] = {}
    for s in sorted(sightings, key=lambda s: s.at):
        if s.made:
            p = out.setdefault(s.made, Pattern(tag=s.made, times=0))
            p.times += 1
            p.right_since = 0
            p.last_seen = s.at
            if s.concept_id not in p.topics:
                p.topics.append(s.concept_id)
        if s.correct:
            for tag in s.traps:
                if tag in out:
                    out[tag].right_since += 1
        elif not s.made:
            # Wrong in another way on a question that carries the trap: not a clean avoid.
            for tag in s.traps:
                if tag in out:
                    out[tag].right_since = 0
    found = [p for p in out.values() if p.times >= PATTERN_MIN]
    for p in found:
        p.status = "fixed" if p.right_since >= FIXED_AFTER else "working_on"
    return sorted(found, key=lambda p: (p.status != "working_on", -(p.last_seen.timestamp() if p.last_seen else 0)))


def active(patterns: list[Pattern]) -> set[str]:
    return {p.tag for p in patterns if p.status == "working_on"}


@dataclass
class ModeAnswer:
    """A response SYNiq gave to a wrong answer, and whether the next answer on that topic was right."""

    mode: str
    next_correct: bool | None  # None: no answer on that topic since


def mode_stats(answers: list[ModeAnswer]) -> dict:
    stats: dict[str, dict] = {}
    for a in answers:
        if a.next_correct is None:
            continue
        st = stats.setdefault(a.mode, {"helped": 0, "after": 0})
        st["after"] += 1
        st["helped"] += int(a.next_correct)
    return stats


def mode_order(base: list[str], stats: dict | None, best_method: str | None) -> tuple[list[str], str | None]:
    """The base ladder reordered by what has helped this student after a mistake.

    Returns the order and which mode leads because of the student (or None if the
    base order stands). A mode needs MODE_MIN answers after it before its own record
    counts; until then the way of explaining that helps them most gets a nudge.
    """
    preferred = METHOD_TO_MODE.get(best_method or "")

    def score(mode: str) -> float:
        st = (stats or {}).get(mode) or {}
        n, good = st.get("after", 0), st.get("helped", 0)
        s = (good + 1) / (n + 2) if n >= MODE_MIN else 0.5
        return s + (PREFERRED_BONUS if mode == preferred else 0.0)

    order = sorted(base, key=lambda m: (-score(m), base.index(m)))
    lead = order[0] if order[0] != base[0] or score(order[0]) != 0.5 else None
    return order, lead
