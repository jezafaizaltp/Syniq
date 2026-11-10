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
# What format_stats keeps per method: answers right and wrong after it, how many were expected right
# from what the learner knew just before, and the learner's own "this helped" / "not really" taps.
FIELDS = ("after_correct", "after_wrong", "expected", "felt_yes", "felt_no")

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
        for key in FIELDS:
            if key in st:
                t[key] = t.get(key, 0) + st[key]
    return total


def subtract(total: dict | None, stats: dict | None) -> dict:
    out = {k: dict(v) for k, v in (total or {}).items()}
    for style, st in (stats or {}).items():
        if style in out:
            for key in FIELDS:
                if key in st and key in out[style]:
                    out[style][key] = max(0, out[style][key] - st[key])
    return out


def evidence(stats: dict | None, style: str) -> tuple[float, float, float]:
    """(right answers, answers, right answers expected) after this method, plus the learner's own
    "did this help?" taps as answers expected right half the time.

    Comparing with what was expected matters: a first explanation comes when the topic is new and a
    second one after mistakes, so raw right-after counts mostly say how hard the moment was. Rows
    from before the expected count was kept are taken at half, which gives the old smoothed rate."""
    st = (stats or {}).get(style) or {}
    good, bad = int(st.get("after_correct", 0)), int(st.get("after_wrong", 0))
    expected = float(st["expected"]) if "expected" in st else 0.5 * (good + bad)
    yes, no = int(st.get("felt_yes", 0)), int(st.get("felt_no", 0))
    return good + yes, good + bad + yes + no, expected + 0.5 * (yes + no)


@dataclass
class Prior:
    """What the student's other topics, and similar learners, say about each method."""

    subject: dict = field(default_factory=dict)
    overall: dict = field(default_factory=dict)  # the student's other subjects
    peers: dict = field(default_factory=dict)
    peers_are_similar: bool = False

    def pseudo(self, style: str) -> tuple[float, float, float, str | None]:
        """(right, answers, expected right) pseudo-counts for a style, and the level that contributed most."""
        hits = n = expected = 0.0
        best_level, best_n = None, 0.0
        for level in ("subject", "overall", "peers"):
            h, k, e = evidence(getattr(self, level), style)
            scale = CAPS[level] / k if k > CAPS[level] else 1.0
            hits, n, expected = hits + h * scale, n + k * scale, expected + e * scale
            if k * scale > best_n:
                best_level, best_n = level, k * scale
        return hits, n, expected, best_level


def score(style: str, topic_stats: dict | None, prior: Prior | None) -> float:
    """How much better than expected the answers after this method went: 0.5 with no evidence."""
    hits, n, expected = evidence(topic_stats, style)
    if prior:
        h, k, e, _ = prior.pseudo(style)
        hits, n, expected = hits + h, n + k, expected + e
    return 0.5 + (hits - expected) / (n + 2)


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
    topic_n = evidence(topic_stats, best)[1]
    _, k, _, level = prior.pseudo(best) if prior else (0.0, 0.0, 0.0, None)
    if level is None or topic_n >= k:
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
