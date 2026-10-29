"""Did SYNiq help? Before-and-after marks for pilot students compared with students not using it.

The school already sets term exams. Their marks before SYNiq started and after some
weeks of use, for pilot students and for a comparison group of Class 9 students who
don't use SYNiq, give a fair measure: if both groups' marks move by the same amount,
the exam just got easier or harder; the difference between the two changes is what
SYNiq may have added (a "difference in differences").

Privacy:
- Results are only ever shown in aggregate, never as a list or ranking of students.
- Any group smaller than MIN_GROUP is hidden, so no one student's marks can be read off.
- Starting-mark thirds are worked out for this report only and never stored on a student.
- Comparison students are anonymous codes (C1, C2, ...), never names.

Pure functions, so the maths can be tested without a database.
"""

import math
from dataclasses import dataclass
from statistics import mean, median, stdev

MIN_GROUP = 5  # hide any figure based on fewer students than this


@dataclass
class Pair:
    group: str  # pilot | comparison
    before: float  # percent
    after: float  # percent
    practised: int | None = None  # questions answered in SYNiq, pilot students only

    @property
    def change(self) -> float:
        return self.after - self.before


def summary(pairs: list[Pair]) -> dict:
    n = len(pairs)
    if n < MIN_GROUP:
        return {"n": n, "too_few": True}
    changes = [p.change for p in pairs]
    return {
        "n": n,
        "too_few": False,
        "before": round(mean(p.before for p in pairs), 1),
        "after": round(mean(p.after for p in pairs), 1),
        "change": round(mean(changes), 1),
        "sd_change": round(stdev(changes), 1),
    }


def difference(pilot: list[Pair], comparison: list[Pair]) -> dict | None:
    """Pilot change minus comparison change, with a rough 95% range. None if a group is too small."""
    if len(pilot) < MIN_GROUP or len(comparison) < MIN_GROUP:
        return None
    a, b = [p.change for p in pilot], [p.change for p in comparison]
    diff = mean(a) - mean(b)
    se = math.sqrt(stdev(a) ** 2 / len(a) + stdev(b) ** 2 / len(b))
    low, high = diff - 1.96 * se, diff + 1.96 * se
    return {
        "points": round(diff, 1),
        "low": round(low, 1),
        "high": round(high, 1),
        # Plain words, not p-values: does the whole range sit on one side of zero?
        "clear": low > 0 or high < 0,
    }


def thirds(pairs: list[Pair]) -> list[tuple[str, list[Pair]]]:
    """Split everyone by starting marks into lower, middle and upper thirds (both groups together)."""
    ordered = sorted(p.before for p in pairs)
    if len(ordered) < 3:
        return []
    cut1, cut2 = ordered[len(ordered) // 3], ordered[2 * len(ordered) // 3]
    lower = [p for p in pairs if p.before < cut1]
    middle = [p for p in pairs if cut1 <= p.before < cut2]
    upper = [p for p in pairs if p.before >= cut2]
    return [("lower", lower), ("middle", middle), ("upper", upper)]


def report(pairs: list[Pair]) -> dict:
    pilot = [p for p in pairs if p.group == "pilot"]
    comparison = [p for p in pairs if p.group == "comparison"]
    out = {
        "pilot": summary(pilot),
        "comparison": summary(comparison),
        "difference": difference(pilot, comparison),
        "by_starting_marks": [
            {
                "third": name,
                "pilot": summary([p for p in group if p.group == "pilot"]),
                "comparison": summary([p for p in group if p.group == "comparison"]),
            }
            for name, group in thirds(pairs)
        ],
        "by_practice": [],
    }
    practised = [p for p in pilot if p.practised is not None]
    mid = median(p.practised for p in practised) if practised else 0
    more = [p for p in practised if p.practised > mid]
    less = [p for p in practised if p.practised <= mid]
    if len(more) >= MIN_GROUP and len(less) >= MIN_GROUP:
        out["by_practice"] = [
            {"practice": "more", "questions_from": int(mid) + 1, "pilot": summary(more)},
            {"practice": "less", "questions_up_to": int(mid), "pilot": summary(less)},
        ]
    return out
