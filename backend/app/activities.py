"""Hands-on activities: something a child can play with to explore a topic.

Like pictures (app/pictures.py), an activity is a small description in a content pack,
not code or an image: the app builds it (frontend/app/learn/Activity.tsx), so it costs
nothing, works offline and can be checked here. Each activity has a short prompt and one
or more goals; the child changes things with buttons (never by dragging, so it works with
a switch, a keyboard or a screen reader) and presses Check. A wrong try shows what the
child made next to what the goal wanted, never just "wrong". Nothing is scored or stored
except that an activity was finished (a help event, like read-aloud).

Types:
  number_line    move a marker along a line (integers, fractions, estimation)
  fraction_bar   cut a bar into equal parts and shade some
  rectangle      change width and height; area and perimeter shown live
  mirror         complete the other half of a shape across a mirror line
  angle          turn an arm to make an angle
  sort           put each thing in the group it belongs to
  order          put steps in the right order (cycles, methods, sequences)
  bars           build a bar graph from data
  array          arrange counters in rows to find factors (primes make one row)
  scale          set a reading on a scale (ruler, thermometer), with named zones
  pattern        grow a dot pattern step by step

The format, with an example of each type, is in content/README.md.
"""

from fractions import Fraction
from numbers import Real

TYPES = (
    "number_line", "fraction_bar", "rectangle", "mirror", "angle", "sort", "order", "bars", "array", "scale", "pattern",
)
PATTERN_RULES = {
    "square": lambda n: n * n,
    "triangle": lambda n: n * (n + 1) // 2,
    "odd": lambda n: 2 * n - 1,
    "even": lambda n: 2 * n,
    "double": lambda n: 2 ** (n - 1),
}
ANGLE_KINDS = {"acute", "right", "obtuse", "straight", "reflex"}
TEXT_MAX = 160
LABEL_MAX = 60


def _num(v) -> bool:
    return isinstance(v, Real) and not isinstance(v, bool)


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _text(v, where: str, errors: list[str], limit: int = TEXT_MAX) -> None:
    if not isinstance(v, str) or not v.strip():
        errors.append(f"{where} needs some text")
    elif len(v) > limit:
        errors.append(f"{where} is too long ({len(v)} characters, at most {limit})")


def _on_step(value: float, start: float, step: float) -> bool:
    k = (value - start) / step
    return abs(k - round(k)) < 1e-9


def check_activity(a) -> list[str]:
    """Everything wrong with an activity, as plain sentences. Empty when it can be built."""
    if not isinstance(a, dict):
        return ["activity must be a mapping"]
    errors: list[str] = []
    kind = a.get("type")
    if kind not in TYPES:
        return [f"activity type must be one of {', '.join(TYPES)}"]
    _text(a.get("prompt"), "activity prompt", errors)
    goals = a.get("goals")
    needs_goals = kind not in ("sort", "order", "bars", "mirror")
    if needs_goals:
        if not isinstance(goals, list) or not 1 <= len(goals) <= 4:
            errors.append("activity needs 1 to 4 goals")
            goals = []
        for i, g in enumerate(goals, start=1):
            if not isinstance(g, dict):
                errors.append(f"goal {i} must be a mapping")
                continue
            _text(g.get("prompt"), f"goal {i} prompt", errors)
            if "hint" in g:
                _text(g["hint"], f"goal {i} hint", errors)
    elif goals is not None:
        errors.append(f"a {kind} activity has one task, set by its own fields, not goals")
    check = globals()[f"_check_{kind}"]
    errors += check(a, goals or [])
    return errors


def _check_number_line(a, goals):
    e = []
    lo, hi, step = a.get("min"), a.get("max"), a.get("step")
    if not (_num(lo) and _num(hi) and _num(step)) or step <= 0 or lo >= hi:
        return ["number_line needs numbers min < max and step > 0"]
    if (hi - lo) / step > 40:
        e.append("number_line has too many steps (at most 40)")
    start = a.get("start", lo)
    if not _num(start) or not lo <= start <= hi or not _on_step(start, lo, step):
        e.append("number_line start must be on the line, on a step")
    if "denominator" in a and not (_int(a["denominator"]) and 2 <= a["denominator"] <= 12):
        e.append("number_line denominator must be 2 to 12")
    for i, g in enumerate(goals, start=1):
        t = g.get("target")
        if not _num(t) or not lo <= t <= hi or not _on_step(t, lo, step):
            e.append(f"goal {i} target must be on the line, on a step")
        elif t == start and i == 1:
            e.append("goal 1 target is where the marker starts")
    return e


def _check_fraction_bar(a, goals):
    e = []
    most = a.get("max_parts", 12)
    if not _int(most) or not 2 <= most <= 12:
        e.append("fraction_bar max_parts must be 2 to 12")
        most = 12
    for i, g in enumerate(goals, start=1):
        num, den = g.get("num"), g.get("den")
        if not (_int(num) and _int(den)) or not 0 < num <= den or den > most:
            e.append(f"goal {i} needs whole numbers 0 < num <= den <= {most}")
        if "equivalent" in g and not isinstance(g["equivalent"], bool):
            e.append(f"goal {i} equivalent must be true or false")
    return e


def _rect_options(most: int):
    return [(w, h) for w in range(1, most + 1) for h in range(1, most + 1)]


def _check_rectangle(a, goals):
    e = []
    most = a.get("max_side", 10)
    if not _int(most) or not 2 <= most <= 12:
        return ["rectangle max_side must be 2 to 12"]
    for i, g in enumerate(goals, start=1):
        keys = [k for k in ("area", "perimeter", "width", "height") if k in g]
        if not keys or not all(_int(g[k]) and g[k] > 0 for k in keys):
            e.append(f"goal {i} needs whole-number area, perimeter, width or height")
            continue
        if not any(
            all({"area": w * h, "perimeter": 2 * (w + h), "width": w, "height": h}[k] == g[k] for k in keys)
            for w, h in _rect_options(most)
        ):
            e.append(f"goal {i} can't be made with sides up to {most}")
    return e


def _check_mirror(a, goals):
    left = a.get("left")
    if not isinstance(left, list) or not 2 <= len(left) <= 8:
        return ["mirror needs 'left': 2 to 8 rows like '#..'"]
    widths = {len(r) if isinstance(r, str) else -1 for r in left}
    if len(widths) != 1 or not 2 <= widths.pop() <= 5:
        return ["mirror rows must all be 2 to 5 characters wide"]
    if any(set(r) - {"#", "."} for r in left):
        return ["mirror rows use only # (filled) and . (empty)"]
    if not any("#" in r for r in left):
        return ["mirror needs at least one filled square"]
    return []


def _check_angle(a, goals):
    e = []
    for i, g in enumerate(goals, start=1):
        if "degrees" in g:
            d = g["degrees"]
            if not _int(d) or not 0 < d <= 360 or d % 5:
                e.append(f"goal {i} degrees must be 5 to 360, in fives")
        elif g.get("kind") not in ANGLE_KINDS:
            e.append(f"goal {i} needs degrees or a kind ({', '.join(sorted(ANGLE_KINDS))})")
    return e


def _check_sort(a, goals):
    e = []
    bins = a.get("bins")
    if not isinstance(bins, list) or not 2 <= len(bins) <= 4 or len(set(bins)) != len(bins):
        return ["sort needs 2 to 4 different bins"]
    for b in bins:
        _text(b, "a bin", e, LABEL_MAX)
    items = a.get("items")
    if not isinstance(items, list) or not 4 <= len(items) <= 10:
        return e + ["sort needs 4 to 10 items"]
    labels = [i.get("label") if isinstance(i, dict) else None for i in items]
    if len(set(labels)) != len(labels):
        e.append("sort has the same item twice")
    used = set()
    for n, it in enumerate(items, start=1):
        if not isinstance(it, dict):
            e.append(f"item {n} must be a mapping")
            continue
        _text(it.get("label"), f"item {n} label", e, LABEL_MAX)
        if it.get("bin") not in bins:
            e.append(f"item {n} bin must be one of the bins")
        used.add(it.get("bin"))
        if "why" in it:
            _text(it["why"], f"item {n} why", e)
    if set(bins) - used:
        e.append("every bin needs at least one item")
    return e


def _check_order(a, goals):
    e = []
    steps = a.get("steps")
    if not isinstance(steps, list) or not 3 <= len(steps) <= 8 or len(set(steps)) != len(steps):
        return ["order needs 3 to 8 different steps"]
    for n, s in enumerate(steps, start=1):
        _text(s, f"step {n}", e, LABEL_MAX)
    return e


def _check_bars(a, goals):
    e = []
    cats = a.get("categories")
    most = a.get("max", 10)
    if not _int(most) or not 4 <= most <= 20:
        e.append("bars max must be 4 to 20")
        most = 20
    if not isinstance(cats, list) or not 2 <= len(cats) <= 6:
        return e + ["bars needs 2 to 6 categories"]
    for n, c in enumerate(cats, start=1):
        if not isinstance(c, dict):
            e.append(f"category {n} must be a mapping")
            continue
        _text(c.get("label"), f"category {n} label", e, 30)
        if not _int(c.get("value")) or not 0 <= c["value"] <= most:
            e.append(f"category {n} value must be 0 to {most}")
    if a.get("show", "tally") not in ("tally", "table"):
        e.append("bars show must be tally or table")
    return e


def _check_array(a, goals):
    e = []
    for i, g in enumerate(goals, start=1):
        n = g.get("n")
        if not _int(n) or not 2 <= n <= 36:
            e.append(f"goal {i} n must be 2 to 36")
        if g.get("find", "all") != "all" and not (_int(g.get("find")) and _int(n) and n % g["find"] == 0):
            e.append(f"goal {i} find must be 'all' or a number of rows that divides n")
    return e


def _check_scale(a, goals):
    e = []
    lo, hi, step = a.get("min"), a.get("max"), a.get("step")
    if not (_num(lo) and _num(hi) and _num(step)) or step <= 0 or lo >= hi:
        return ["scale needs numbers min < max and step > 0"]
    if (hi - lo) / step > 1000:
        e.append("scale has too many steps (at most 1000)")
    _text(a.get("unit"), "scale unit", e, 12)
    if a.get("orientation", "horizontal") not in ("horizontal", "vertical"):
        e.append("scale orientation must be horizontal or vertical")
    start = a.get("start", lo)
    if not _num(start) or not lo <= start <= hi or not _on_step(start, lo, step):
        e.append("scale start must be on the scale, on a step")
    zones = a.get("zones", [])
    names = set()
    for n, z in enumerate(zones, start=1):
        if not isinstance(z, dict) or not (_num(z.get("from")) and _num(z.get("to"))) or z["from"] >= z["to"]:
            e.append(f"zone {n} needs numbers from < to")
            continue
        _text(z.get("label"), f"zone {n} label", e, 30)
        names.add(z.get("label"))
    for i, g in enumerate(goals, start=1):
        if "value" in g:
            v = g["value"]
            if not _num(v) or not lo <= v <= hi or not _on_step(v, lo, step):
                e.append(f"goal {i} value must be on the scale, on a step")
        elif g.get("zone") not in names:
            e.append(f"goal {i} needs a value or the label of a zone")
    return e


def _check_pattern(a, goals):
    e = []
    rule = a.get("rule")
    if rule not in PATTERN_RULES:
        return [f"pattern rule must be one of {', '.join(PATTERN_RULES)}"]
    most = a.get("max_step", 8)
    if not _int(most) or not 3 <= most <= 10:
        return ["pattern max_step must be 3 to 10"]
    counts = [PATTERN_RULES[rule](n) for n in range(1, most + 1)]
    if counts[-1] > 100:
        e.append("pattern grows past 100 dots: lower max_step")
    for i, g in enumerate(goals, start=1):
        if g.get("count") not in counts[1:]:
            e.append(f"goal {i} count must be one the pattern reaches after step 1 ({counts[1:]})")
    return e


def fraction_matches(num: int, den: int, goal: dict) -> bool:
    """Used by tests to mirror the app's rule: equivalent fractions count unless the goal says exact."""
    if goal.get("equivalent", True):
        return Fraction(num, den) == Fraction(goal["num"], goal["den"])
    return (num, den) == (goal["num"], goal["den"])
