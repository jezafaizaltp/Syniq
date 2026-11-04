"""Matching each student to the ways of explaining that work for them.

After every explanation, the next few answers on that topic show whether it
helped. Those counts are kept per topic (Mastery.format_stats). This module
pools them so that a new topic can start with the method most likely to work:

1. this topic, for this student (strongest);
2. the same subject, for this student;
3. the student's other subjects;
4. this topic, for learners who learn in a similar way (their best method
   matches this student's best method), or every learner on this topic while
   the student's own pattern isn't clear yet.

Wider evidence is capped so it only nudges: two answers on this very topic
outweigh fifty in other subjects. Nothing here is a label. It is a description
of what helped lately, recomputed after every answer, and it never limits what
the student sees: they can switch to any method at any time.
"""

from dataclasses import dataclass, field

STYLES = ["text", "visual", "step_by_step", "real_world"]

# Most pseudo-answers each wider level may add to a style's score.
CAPS = {"subject": 6.0, "overall": 3.0, "peers": 4.0}
# Answers after a method before it counts towards someone's pattern.
CLEAR_PATTERN_MIN = 6
# A method needs this many answers after it before we describe it to people.
DESCRIBE_MIN = 3


def counts(stats: dict | None, style: str) -> tuple[int, int]:
    st = (stats or {}).get(style) or {}
    return int(st.get("after_correct", 0)), int(st.get("after_wrong", 0))


def add(total: dict, stats: dict | None) -> dict:
    """Add one format_stats dict into a running total (same shape)."""
    for style, st in (stats or {}).items():
        t = total.setdefault(style, {"after_correct": 0, "after_wrong": 0})
        t["after_correct"] += int(st.get("after_correct", 0))
        t["after_wrong"] += int(st.get("after_wrong", 0))
    return total


def subtract(total: dict | None, stats: dict | None) -> dict:
    out = {k: dict(v) for k, v in (total or {}).items()}
    for style, st in (stats or {}).items():
        if style in out:
            out[style]["after_correct"] = max(0, out[style].get("after_correct", 0) - int(st.get("after_correct", 0)))
            out[style]["after_wrong"] = max(0, out[style].get("after_wrong", 0) - int(st.get("after_wrong", 0)))
    return out


def _capped(good: int, bad: int, cap: float) -> tuple[float, float]:
    n = good + bad
    if n <= cap or n == 0:
        return float(good), float(bad)
    scale = cap / n
    return good * scale, bad * scale


@dataclass
class Prior:
    """What the student's other topics, and similar learners, say about each method."""

    subject: dict = field(default_factory=dict)
    overall: dict = field(default_factory=dict)  # the student's other subjects
    peers: dict = field(default_factory=dict)
    peers_are_similar: bool = False

    def pseudo(self, style: str) -> tuple[float, float, str | None]:
        """(good, bad) pseudo-counts for a style, and the level that contributed most."""
        good = bad = 0.0
        best_level, best_n = None, 0.0
        for level in ("subject", "overall", "peers"):
            g, b = _capped(*counts(getattr(self, level), style), CAPS[level])
            good, bad = good + g, bad + b
            if g + b > best_n:
                best_level, best_n = level, g + b
        return good, bad, best_level


def score(style: str, topic_stats: dict | None, prior: Prior | None) -> float:
    """Chance the next answer is right after this method: a smoothed rate, 0.5 with no evidence."""
    good, bad = counts(topic_stats, style)
    if prior:
        g, b, _ = prior.pseudo(style)
        good, bad = good + g, bad + b
    return (good + 1) / (good + bad + 2)


def choose(
    seen: list[str], topic_stats: dict | None, prior: Prior | None, preferred: str | None = None, ties: list[str] | None = None
) -> tuple[str, str]:
    """The method to explain with next, and why: preferred | this_topic | history | similar | everyone | default.

    Methods not yet tried on this topic go first, so a struggling student always
    gets something new; among those, the one most likely to work for them. With no
    evidence either way, `ties` sets the order (young children start with the picture).
    """
    order = ties or STYLES
    if preferred and preferred in STYLES and preferred not in seen:
        return preferred, "preferred"
    pool = [s for s in STYLES if s not in seen] or STYLES
    scores = {s: score(s, topic_stats, prior) for s in pool}
    best = max(pool, key=lambda s: (scores[s], -order.index(s) if s in order else -len(order)))
    if all(abs(scores[s] - scores[best]) < 1e-9 for s in pool):
        return best, "default"
    topic_n = sum(counts(topic_stats, best))
    g, b, level = prior.pseudo(best) if prior else (0.0, 0.0, None)
    if level is None or topic_n >= g + b:
        return best, "this_topic"
    if level == "peers":
        return best, "similar" if prior.peers_are_similar else "everyone"
    return best, "history"


def best_method(stats: dict | None, minimum: int = CLEAR_PATTERN_MIN) -> str | None:
    """The method that has clearly helped most, once there's enough evidence, else None."""
    rated = [(s, *counts(stats, s)) for s in STYLES]
    if sum(g + b for _, g, b in rated) < minimum:
        return None
    tried = [(s, (g + 1) / (g + b + 2)) for s, g, b in rated if g + b >= DESCRIBE_MIN]
    if not tried:
        return None
    tried.sort(key=lambda x: (-x[1], STYLES.index(x[0])))
    if len(tried) > 1 and tried[0][1] - tried[1][1] < 0.1:
        return None  # two methods are about as good: no clear pattern
    return tried[0][0]


def describe(stats: dict | None) -> list[dict]:
    """Per method with enough answers after it: how many helped. Best first. No scores, no labels."""
    out = []
    for s in STYLES:
        g, b = counts(stats, s)
        if g + b >= DESCRIBE_MIN:
            out.append({"style": s, "right_after": g, "answers_after": g + b})
    out.sort(key=lambda d: (-(d["right_after"] + 1) / (d["answers_after"] + 2), STYLES.index(d["style"])))
    return out
