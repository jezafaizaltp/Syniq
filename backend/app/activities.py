"""Hands-on activities: something a child can play with to explore a topic.

Like pictures (app/pictures.py), an activity is a small description in a content pack,
not code or an image: the app builds it (frontend/app/learn/Activity.tsx), so it costs
nothing, works offline and can be checked here. Each activity has a short prompt and one
or more goals; the child changes things with buttons (never by dragging, so it works with
a switch, a keyboard or a screen reader) and presses Check. A wrong try shows what the
child is coached, never just told "wrong": the app marks on the picture where the try went
wrong, says what that mistake causes and nudges towards the fix without giving it away; the
goal is drawn next to the child's try only from the third wrong try. Content can make the
coaching sharper for its topic:
  goal  mistakes: [{when: {name: value or [low, high]}, say: what that slip causes}]
  sort  item clue: a question that makes the child look again (first wrong try); why: the reason
  order reasons: {step: why it can't come earlier}
  scale zone says: what a reading in that zone means
Nothing is scored or stored except that an activity was finished (a help event, like read-aloud).

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
  formula        change numbers and watch what a formula gives (motion, Ohm's law, identities)
  graph          move a point, or tilt and shift a line, on a grid

The format, with an example of each type, is in content/README.md.
"""

from fractions import Fraction
from numbers import Real

TYPES = (
    "number_line", "fraction_bar", "rectangle", "mirror", "angle", "sort", "order", "bars", "array", "scale", "pattern",
    "formula", "graph",
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
            errors += _check_mistakes(a, g, i)
    elif goals is not None:
        errors.append(f"a {kind} activity has one task, set by its own fields, not goals")
    check = globals()[f"_check_{kind}"]
    errors += check(a, goals or [])
    if not errors:
        errors += _mistake_says_right(a, goals or [])
    return errors


# The numbers each type reports for a try, which a goal's `mistakes` can match on.
TRY_NAMES = {
    "number_line": {"v"},
    "scale": {"v"},
    "angle": {"degrees"},
    "rectangle": {"width", "height", "area", "perimeter"},
    "pattern": {"step", "count"},
    "array": {"rows"},
    "fraction_bar": {"shaded", "parts"},
}


def _want_ok(v) -> bool:
    return _num(v) or (isinstance(v, list) and len(v) == 2 and all(_num(x) for x in v) and v[0] < v[1])


def _check_mistakes(a, g, i):
    """A goal's `mistakes`: what a common wrong try causes, said when a try matches `when`."""
    if "mistakes" not in g:
        return []
    ms = g["mistakes"]
    if not isinstance(ms, list) or not 1 <= len(ms) <= 6:
        return [f"goal {i} mistakes must be a list of 1 to 6"]
    kind = a.get("type")
    if kind == "formula":
        names = {x.get("name") for x in (a.get("inputs") or []) + (a.get("outputs") or []) if isinstance(x, dict)}
    elif kind == "graph":
        names = {"x", "y"} if a.get("mode") == "point" else {"m", "c"}
    else:
        names = TRY_NAMES.get(kind, set())
    if not names:
        return [f"goal {i}: a {kind} activity can't have mistakes"]
    e = []
    for n, m in enumerate(ms, start=1):
        if not isinstance(m, dict) or not isinstance(m.get("when"), dict) or not m["when"]:
            e.append(f"goal {i} mistake {n} needs 'when' and 'say'")
            continue
        _text(m.get("say"), f"goal {i} mistake {n} say", e, 220)
        bad = set(m["when"]) - names
        if bad:
            e.append(f"goal {i} mistake {n} uses {', '.join(sorted(map(str, bad)))}; it can use {', '.join(sorted(names))}")
        elif not all(_want_ok(v) for v in m["when"].values()):
            e.append(f"goal {i} mistake {n} values must be numbers or [low, high]")
    return e


def _mistake_says_right(a, goals) -> list[str]:
    """A mistake rule must never match a right answer: that would tell a child they were wrong.
    Checked here for one-number types; formula goals are checked while their inputs are tried."""
    e = []
    key = {"number_line": "target", "scale": "value", "angle": "degrees"}.get(a.get("type"))
    if not key:
        return e
    kind = a.get("type")
    if kind == "angle":
        reach = list(range(5, 361, 5))
    else:
        reach = _values(a["min"], a["max"], a["step"])
    for i, g in enumerate(goals, start=1):
        right = g.get(key)
        if not _num(right):
            continue
        for n, m in enumerate(g.get("mistakes") or [], start=1):
            w = next(iter(m["when"].values()))
            if wanted(right, w):
                e.append(f"goal {i} mistake {n} matches the right answer")
            elif not any(wanted(x, w) for x in reach):
                e.append(f"goal {i} mistake {n} can never happen: no try can reach that value")
    return e


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
        elif i > 1 and t == goals[i - 2].get("target"):
            e.append(f"goal {i} target is where goal {i - 1} leaves the marker")
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
    if not isinstance(bins, list) or not 2 <= len(bins) <= 5 or len(set(bins)) != len(bins):
        return ["sort needs 2 to 5 different bins"]
    for b in bins:
        _text(b, "a bin", e, LABEL_MAX)
    items = a.get("items")
    if not isinstance(items, list) or not 4 <= len(items) <= 12:
        return e + ["sort needs 4 to 12 items"]
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
        if "clue" in it:
            _text(it["clue"], f"item {n} clue", e)
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
    reasons = a.get("reasons", {})
    if not isinstance(reasons, dict):
        return e + ["order reasons must map a step to why it can't come earlier"]
    for k, why in reasons.items():
        if k not in steps:
            e.append(f"order reason for '{k}', which is not a step")
        elif k == steps[0]:
            e.append("the first step can never come too early, so it needs no reason")
        else:
            _text(why, f"reason for '{k}'", e, 220)
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
        if "says" in z:
            _text(z["says"], f"zone {n} says", e)
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


# --- Formulas -----------------------------------------------------------------------------
# A tiny arithmetic language, the same one the app evaluates (frontend/app/learn/formula.ts):
# numbers, names, + - * / ^ (power), brackets, pi, and sqrt, min, max, abs. Nothing else, so a
# pack can never run code.

FUNCS = {"sqrt": lambda x: x ** 0.5, "min": min, "max": max, "abs": abs}
_NAME = __import__("re").compile(r"^[a-z][a-z0-9_]*$")


def _tokens(text: str) -> list[str]:
    import re

    out = re.findall(r"\d+\.?\d*|\.\d+|[a-z][a-z0-9_]*|[-+*/^(),]", text)
    if "".join(out) != text.replace(" ", ""):
        raise ValueError(f"can't read '{text}'")
    return out


class _Parser:
    def __init__(self, text: str):
        self.t = _tokens(text)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, want=None):
        tok = self.peek()
        if tok is None or (want and tok != want):
            raise ValueError(f"expected {want or 'more'}")
        self.i += 1
        return tok

    def parse(self):
        node = self.sum()
        if self.peek() is not None:
            raise ValueError(f"unexpected '{self.peek()}'")
        return node

    def sum(self):
        node = self.product()
        while self.peek() in ("+", "-"):
            node = (self.take(), node, self.product())
        return node

    def product(self):
        node = self.unary()
        while self.peek() in ("*", "/"):
            node = (self.take(), node, self.unary())
        return node

    def unary(self):
        if self.peek() == "-":
            self.take()
            return ("neg", self.unary())
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek() == "^":
            self.take()
            return ("^", base, self.unary())
        return base

    def atom(self):
        tok = self.take()
        if tok == "(":
            node = self.sum()
            self.take(")")
            return node
        if tok[0].isdigit() or tok[0] == ".":
            return ("num", float(tok))
        if tok in FUNCS:
            self.take("(")
            args = [self.sum()]
            while self.peek() == ",":
                self.take()
                args.append(self.sum())
            self.take(")")
            return ("call", tok, args)
        if _NAME.match(tok):
            return ("name", tok)
        raise ValueError(f"unexpected '{tok}'")


def parse_formula(text: str):
    return _Parser(text).parse()


def evaluate(node, env: dict) -> float:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "name":
        if node[1] == "pi":
            return 3.141592653589793
        return env[node[1]]
    if kind == "neg":
        return -evaluate(node[1], env)
    if kind == "call":
        return FUNCS[node[1]](*[evaluate(a, env) for a in node[2]])
    a, b = evaluate(node[1], env), evaluate(node[2], env)
    if kind == "+":
        return a + b
    if kind == "-":
        return a - b
    if kind == "*":
        return a * b
    if kind == "/":
        return a / b
    return a ** b


def _names(node) -> set[str]:
    if node[0] == "name":
        return {node[1]} - {"pi"}
    if node[0] == "num":
        return set()
    if node[0] == "call":
        return set().union(*[_names(a) for a in node[2]])
    return set().union(*[_names(n) for n in node[1:]])


def _values(lo, hi, step):
    n = round((hi - lo) / step)
    return [round(lo + k * step, 10) for k in range(n + 1)]


def wanted(value: float, want) -> bool:
    if isinstance(want, list):
        return want[0] - 1e-9 <= value <= want[1] + 1e-9
    return abs(value - want) < 1e-6


def _check_formula(a, goals):
    e = []
    inputs, outputs = a.get("inputs"), a.get("outputs")
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= 4:
        return ["formula needs 1 to 4 inputs"]
    if not isinstance(outputs, list) or not 1 <= len(outputs) <= 4:
        return ["formula needs 1 to 4 outputs"]
    names = []
    grids = []
    for n, i in enumerate(inputs, start=1):
        if not isinstance(i, dict) or not _NAME.match(str(i.get("name", ""))):
            e.append(f"input {n} needs a lower-case name")
            continue
        _text(i.get("label"), f"input {n} label", e, 40)
        lo, hi, step = i.get("min"), i.get("max"), i.get("step")
        if not (_num(lo) and _num(hi) and _num(step)) or step <= 0 or lo >= hi or (hi - lo) / step > 1000:
            e.append(f"input {n} needs min < max and a step (at most 1000 steps)")
            continue
        start = i.get("start", lo)
        if not _num(start) or not lo <= start <= hi or not _on_step(start, lo, step):
            e.append(f"input {n} start must be on a step")
        names.append(i["name"])
        grids.append(_values(lo, hi, step))
    parsed = {}
    for n, o in enumerate(outputs, start=1):
        if not isinstance(o, dict) or not _NAME.match(str(o.get("name", ""))):
            e.append(f"output {n} needs a lower-case name")
            continue
        _text(o.get("label"), f"output {n} label", e, 40)
        try:
            tree = parse_formula(str(o.get("expr", "")))
        except (ValueError, IndexError) as err:
            e.append(f"output {n} formula: {err}")
            continue
        unknown = _names(tree) - set(names)
        if unknown:
            e.append(f"output {n} uses {', '.join(sorted(unknown))}, which is not an input")
            continue
        parsed[o["name"]] = tree
    if len(set(names) | set(parsed)) != len(names) + len(parsed):
        e.append("inputs and outputs need different names")
    if e:
        return e
    import itertools

    combos = 1
    for g in grids:
        combos *= len(g)
    for gi, g in enumerate(goals, start=1):
        want = g.get("want")
        if not isinstance(want, dict) or not want:
            e.append(f"goal {gi} needs 'want': values for outputs or inputs")
            continue
        if set(want) - set(names) - set(parsed):
            e.append(f"goal {gi} wants something that is not an input or output")
            continue
        if any(not (_num(v) or (isinstance(v, list) and len(v) == 2 and all(_num(x) for x in v) and v[0] < v[1])) for v in want.values()):
            e.append(f"goal {gi} values must be numbers or [low, high]")
            continue
        if combos > 300_000:
            continue  # too many to try them all; the app still checks each try
        # A rule that pins down every wanted value but still matches a right answer would tell a
        # child who got it right that they slipped. (Partial rules, like "only the sum is right",
        # are fine: they are only read on a wrong try.)
        rules = [
            m["when"] for m in g.get("mistakes") or []
            if isinstance(m, dict) and isinstance(m.get("when"), dict) and set(want) <= set(m["when"])
        ]
        every = [m["when"] for m in g.get("mistakes") or [] if isinstance(m, dict) and isinstance(m.get("when"), dict)]
        seen = set()
        reachable = False
        clash = set()
        for combo in itertools.product(*grids):
            env = dict(zip(names, combo))
            try:
                env.update({k: evaluate(t, env) for k, t in parsed.items()})
            except (ZeroDivisionError, ValueError, OverflowError, TypeError):
                continue
            if any(isinstance(v, complex) for v in env.values()):
                continue
            for n, w in enumerate(every, start=1):
                if n not in seen and all(k in env and _want_ok(v) and wanted(env[k], v) for k, v in w.items()):
                    seen.add(n)
            if all(wanted(env[k], v) for k, v in want.items()):
                reachable = True
                for n, w in enumerate(rules, start=1):
                    if all(k in env and _want_ok(v) and wanted(env[k], v) for k, v in w.items()):
                        clash.add(n)
                if not rules and len(seen) == len(every):
                    break
        if not reachable:
            e.append(f"goal {gi} can't be reached with these inputs")
        for n in range(1, len(every) + 1):
            if n not in seen:
                e.append(f"goal {gi} mistake {n} can never happen: no inputs give those values")
        for n in sorted(clash):
            e.append(f"goal {gi} mistake {n} also matches a right answer")
    return e


def _check_graph(a, goals):
    e = []
    mode = a.get("mode")
    if mode not in ("point", "line"):
        return ["graph mode must be point or line"]
    rng = a.get("range", [-6, 6])
    if not (isinstance(rng, list) and len(rng) == 2 and all(_int(x) for x in rng) and rng[0] < 0 < rng[1] and rng[1] - rng[0] <= 20):
        return ["graph range must be [low, high] whole numbers around 0, at most 20 apart"]
    for k in ("x_label", "y_label"):
        if k in a:
            _text(a[k], k, e, 30)
    m_step = a.get("m_step", 0.5)
    if mode == "line" and not (_num(m_step) and m_step > 0):
        e.append("graph m_step must be a number above 0")
    lo, hi = rng
    for i, g in enumerate(goals, start=1):
        if mode == "point":
            if not all(_int(g.get(k)) and lo <= g[k] <= hi for k in ("x", "y")):
                e.append(f"goal {i} needs whole-number x and y inside the range")
            continue
        keys = [k for k in ("m", "c", "through") if k in g]
        if not keys:
            e.append(f"goal {i} needs m, c or through")
            continue
        ms = [round(k * m_step, 10) for k in range(round(-10 / m_step), round(10 / m_step) + 1)]
        cs = list(range(lo, hi + 1))
        ok = any(
            (g.get("m") is None or abs(m - g["m"]) < 1e-9)
            and (g.get("c") is None or c == g["c"])
            and all(abs(m * p[0] + c - p[1]) < 1e-9 for p in g.get("through", []))
            for m in ms
            for c in cs
        )
        if not ok:
            e.append(f"goal {i} can't be reached with slope steps of {m_step} and whole-number c")
    return e


def fraction_matches(num: int, den: int, goal: dict) -> bool:
    """Used by tests to mirror the app's rule: equivalent fractions count unless the goal says exact."""
    if goal.get("equivalent", True):
        return Fraction(num, den) == Fraction(goal["num"], goal["den"])
    return (num, den) == (goal["num"], goal["den"])
