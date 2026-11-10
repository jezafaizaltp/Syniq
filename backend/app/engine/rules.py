"""Adaptation rules: choose the student's next learning action.

Rules are plain, ordered, versioned and unit-tested. The first rule that
applies wins, and every decision carries the rule id, version and a reason a
teacher (or the student) can read. Bump RULES_VERSION whenever behaviour
changes so logged decisions can be traced to the rules that made them.

Guardrails from the product spec:
- never adapt on a single answer (streak and attempt minimums below);
- never lower difficulty or infer anything from speed alone;
- offers of help or a break are questions the student can decline.
"""

from dataclasses import dataclass, field
from datetime import datetime

from . import methods
from .mastery import is_secure

RULES_VERSION = "2026.11-2"

STYLES = methods.STYLES
STRUGGLE_STREAK = 2
PREREQ_GAP_MIN_ATTEMPTS = 3
PREREQ_GAP_P = 0.4
PREREQ_WEAK_P = 0.6


@dataclass
class ConceptState:
    concept_id: int
    order: int
    p_known: float = 0.2
    attempts: int = 0
    wrong_streak: int = 0  # wrong answers in a row since the last explanation
    next_review_at: datetime | None = None
    prereq_ids: list[int] = field(default_factory=list)
    styles_seen: list[str] = field(default_factory=list)
    format_stats: dict = field(default_factory=dict)
    # What other topics and similar learners say about each method (engine/methods.py).
    method_prior: methods.Prior | None = None


@dataclass
class Action:
    kind: str  # practice | explain | review | prereq_review | chapter_complete
    concept_id: int | None
    rule_id: str
    reason: str
    difficulty: int | None = None
    style: str | None = None
    offer_support: bool = False
    evidence: dict = field(default_factory=dict)
    version: str = RULES_VERSION


def target_difficulty(p: float) -> int:
    if p < 0.4:
        return 1
    if p < 0.7:
        return 2
    return 3


def pick_style(state: ConceptState, preferred: str | None, ties: list[str] | None = None) -> str:
    """Choose a way to explain. The student's own preference wins; see engine/methods.py."""
    return choose_style(state, preferred, ties)[0]


def choose_style(state: ConceptState, preferred: str | None, ties: list[str] | None = None) -> tuple[str, str]:
    return methods.choose(state.styles_seen, state.format_stats, state.method_prior, preferred, ties)


def decide(
    chapter: list[ConceptState],
    states_by_id: dict[int, ConceptState],
    now: datetime,
    current_concept_id: int | None = None,
    preferred_style: str | None = None,
    style_ties: list[str] | None = None,
    set_aside: set[int] | None = None,
) -> Action:
    """Pick the next action for one chapter.

    `chapter` is the chapter's concepts in teaching order; `states_by_id` also
    holds prerequisite concepts that may live in earlier chapters.
    """
    ordered = sorted(chapter, key=lambda s: s.order)
    current = states_by_id.get(current_concept_id) if current_concept_id else None
    set_aside = set_aside or set()
    if current is None or is_secure(current.p_known, current.attempts) or current.concept_id in set_aside:
        # Topics whose questions are all used up for today wait, unless nothing else is left.
        open_ = [s for s in ordered if not is_secure(s.p_known, s.attempts)]
        current = next((s for s in open_ if s.concept_id not in set_aside), None) or (
            current if current in open_ else next(iter(open_), None)
        )

    # R1: persistent difficulty plus a weak prerequisite -> revisit the prerequisite.
    if current and current.attempts >= PREREQ_GAP_MIN_ATTEMPTS and current.p_known < PREREQ_GAP_P:
        weak = [
            states_by_id[pid]
            for pid in current.prereq_ids
            if pid in states_by_id and states_by_id[pid].p_known < PREREQ_WEAK_P
        ]
        if weak:
            pre = min(weak, key=lambda s: s.p_known)
            return Action(
                kind="prereq_review",
                concept_id=pre.concept_id,
                rule_id="R1_prereq_gap",
                reason="This topic builds on an earlier one that may need a quick refresh first.",
                difficulty=target_difficulty(pre.p_known),
                evidence={
                    "concept_id": current.concept_id,
                    "attempts": current.attempts,
                    "p_known": round(current.p_known, 3),
                    "prereq_id": pre.concept_id,
                    "prereq_p_known": round(pre.p_known, 3),
                },
            )

    # R2: two or more wrong in a row -> explain it a different way and offer support.
    if current and current.wrong_streak >= STRUGGLE_STREAK:
        style, why = choose_style(current, preferred_style, style_ties)
        return Action(
            kind="explain",
            concept_id=current.concept_id,
            rule_id="R2_struggle_new_format",
            reason="The last few answers suggest a different explanation might help.",
            style=style,
            offer_support=True,
            evidence={"wrong_streak": current.wrong_streak, "styles_seen": current.styles_seen, "method_why": why},
        )

    # R3: a secured concept is due for spaced review.
    due = [
        s
        for s in states_by_id.values()
        if s.next_review_at and s.next_review_at <= now and is_secure(s.p_known, s.attempts)
    ]
    if due:
        s = min(due, key=lambda x: x.next_review_at)
        return Action(
            kind="review",
            concept_id=s.concept_id,
            rule_id="R3_spaced_review",
            reason="A quick review now helps you remember this for longer.",
            difficulty=2,
            evidence={"next_review_at": s.next_review_at.isoformat()},
        )

    if current is None:
        return Action(
            kind="chapter_complete",
            concept_id=None,
            rule_id="R5_chapter_complete",
            reason="Every topic in this chapter looks secure.",
        )

    # R4: a new concept starts with an explanation, in the student's preferred style.
    if current.attempts == 0 and not current.styles_seen:
        style, why = choose_style(current, preferred_style, style_ties)
        return Action(
            kind="explain",
            concept_id=current.concept_id,
            rule_id="R4_introduce",
            reason="Starting a new topic with an explanation.",
            style=style,
            evidence={"method_why": why},
        )

    # R6: default -> practise at a difficulty matched to current understanding.
    return Action(
        kind="practice",
        concept_id=current.concept_id,
        rule_id="R6_practice",
        reason="Practice at a level that matches where you are now.",
        difficulty=target_difficulty(current.p_known),
        evidence={"p_known": round(current.p_known, 3), "attempts": current.attempts},
    )
