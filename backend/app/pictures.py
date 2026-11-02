"""Pictures for the "Show me a picture" explanation.

A picture is a small description in a content pack, not an image file: the app draws it
(frontend/components/Picture.tsx), so it costs nothing, works offline, stays sharp on any
screen, and can be checked here like an answer. Every picture has an `alt` sentence that
screen readers say instead.

Kinds:
  number_line  points and jumps on a number line
  area_grid    a rectangle split into labelled boxes (areas, identities, multiplication)
  bars         a bar chart, or a histogram when `touching` is true
  flow         steps joined by arrows (processes, timelines, cycles)
  compare      two or three columns side by side
  geometry     points, segments, circles and angles, optionally on coordinate axes.
               A point whose name starts with _ is a helper: used for drawing, not shown.

The format, with an example of each kind, is in content/README.md.
"""

from numbers import Real

KINDS = ("number_line", "area_grid", "bars", "flow", "compare", "geometry")
LABEL_MAX = 40
TEXT_MAX = 160


def _num(v) -> bool:
    return isinstance(v, Real) and not isinstance(v, bool)


def _label(v, where: str, errors: list[str], limit: int = LABEL_MAX) -> None:
    if not isinstance(v, str) or not v.strip():
        errors.append(f"{where} needs some text")
    elif len(v) > limit:
        errors.append(f"{where} is too long ({len(v)} characters, at most {limit})")


def check_picture(p) -> list[str]:
    """Everything wrong with a picture, as plain sentences. Empty when it can be drawn."""
    if not isinstance(p, dict):
        return ["picture must be a set of fields"]
    errors: list[str] = []
    kind = p.get("kind")
    if kind not in KINDS:
        return [f"picture kind '{kind}' is not one of {', '.join(KINDS)}"]
    alt = p.get("alt")
    if not isinstance(alt, str) or len(alt.strip()) < 15:
        errors.append("picture needs an 'alt' sentence describing it for screen readers")
    if "caption" in p:
        _label(p["caption"], "caption", errors, TEXT_MAX)
    errors += CHECKS[kind](p)
    return [f"picture: {e}" for e in errors]


def _number_line(p) -> list[str]:
    errors: list[str] = []
    lo, hi, step = p.get("from"), p.get("to"), p.get("step", 1)
    if not (_num(lo) and _num(hi) and lo < hi):
        return ["number_line needs numbers 'from' and 'to', with from < to"]
    if not _num(step) or step <= 0 or (hi - lo) / step > 40:
        errors.append("number_line 'step' must be positive, with at most 40 ticks")
    for n, pt in enumerate(p.get("points") or [], 1):
        if not isinstance(pt, dict) or not _num(pt.get("at")) or not lo <= pt["at"] <= hi:
            errors.append(f"point {n} needs 'at' between {lo} and {hi}")
        else:
            _label(pt.get("label"), f"point {n}", errors)
    for n, j in enumerate(p.get("jumps") or [], 1):
        if not isinstance(j, dict) or not all(_num(j.get(k)) and lo <= j[k] <= hi for k in ("from", "to")):
            errors.append(f"jump {n} needs 'from' and 'to' on the line")
        elif "label" in j:
            _label(j["label"], f"jump {n}", errors)
    if not (p.get("points") or p.get("jumps")):
        errors.append("number_line needs some points or jumps")
    return errors


def _parts(parts, name: str, errors: list[str]) -> int:
    if not isinstance(parts, list) or not 1 <= len(parts) <= 4:
        errors.append(f"area_grid needs 1 to 4 {name}")
        return 0
    for n, part in enumerate(parts, 1):
        if not isinstance(part, dict) or not _num(part.get("size")) or part["size"] <= 0:
            errors.append(f"{name} {n} needs a positive 'size'")
        else:
            _label(part.get("label"), f"{name} {n}", errors)
    return len(parts)


def _area_grid(p) -> list[str]:
    errors: list[str] = []
    ncols = _parts(p.get("cols"), "cols", errors)
    nrows = _parts(p.get("rows"), "rows", errors)
    cells = p.get("cells")
    if not isinstance(cells, list) or len(cells) != nrows or any(not isinstance(r, list) or len(r) != ncols for r in cells):
        errors.append(f"area_grid 'cells' must have {nrows} rows of {ncols} labels")
    else:
        for r, row in enumerate(cells, 1):
            for c, cell in enumerate(row, 1):
                _label(cell, f"cell {r},{c}", errors)
    return errors


def _bars(p) -> list[str]:
    errors: list[str] = []
    bars = p.get("bars")
    if not isinstance(bars, list) or not 2 <= len(bars) <= 10:
        return ["bars needs 2 to 10 bars"]
    for n, b in enumerate(bars, 1):
        if not isinstance(b, dict) or not _num(b.get("value")) or b["value"] < 0:
            errors.append(f"bar {n} needs a 'value' of 0 or more")
        else:
            _label(b.get("label"), f"bar {n}", errors)
    if bars and all(isinstance(b, dict) and b.get("value") == 0 for b in bars):
        errors.append("bars can't all be 0")
    if "unit" in p:
        _label(p["unit"], "unit", errors)
    return errors


def _flow(p) -> list[str]:
    errors: list[str] = []
    steps = p.get("steps")
    if not isinstance(steps, list) or not 2 <= len(steps) <= 8:
        return ["flow needs 2 to 8 steps"]
    for n, s in enumerate(steps, 1):
        _label(s, f"step {n}", errors, 80)
    return errors


def _compare(p) -> list[str]:
    errors: list[str] = []
    cols = p.get("columns")
    if not isinstance(cols, list) or not 2 <= len(cols) <= 3:
        return ["compare needs 2 or 3 columns"]
    for n, col in enumerate(cols, 1):
        if not isinstance(col, dict):
            errors.append(f"column {n} needs a 'title' and 'points'")
            continue
        _label(col.get("title"), f"column {n} title", errors)
        points = col.get("points")
        if not isinstance(points, list) or not 1 <= len(points) <= 6:
            errors.append(f"column {n} needs 1 to 6 points")
        else:
            for m, pt in enumerate(points, 1):
                _label(pt, f"column {n} point {m}", errors, 80)
    return errors


def _geometry(p) -> list[str]:
    errors: list[str] = []
    points = p.get("points")
    axes = p.get("axes", False)
    lo, hi = (p.get("range") or [-6, 6]) if axes else (0, 10)
    if axes and not (_num(lo) and _num(hi) and lo < 0 < hi and hi - lo <= 24):
        return ["geometry 'range' must be [low, high] around 0, at most 24 wide"]
    if not isinstance(points, dict) or not points:
        return ["geometry needs some named points"]
    for key in ("x_label", "y_label"):
        if key in p:
            if not axes:
                errors.append(f"geometry '{key}' only works with axes")
            _label(p[key], key, errors, 24)
    for name, xy in points.items():
        if not (isinstance(xy, list) and len(xy) == 2 and all(_num(v) and lo <= v <= hi for v in xy)):
            errors.append(f"point {name} needs [x, y] between {lo} and {hi}")

    def known(name, where):
        if name not in points:
            errors.append(f"{where} uses point '{name}', which isn't in 'points'")
            return False
        return True

    for n, seg in enumerate(p.get("segments") or [], 1):
        if not isinstance(seg, list) or not 2 <= len(seg) <= 3:
            errors.append(f"segment {n} must be [A, B] or [A, B, label]")
            continue
        known(seg[0], f"segment {n}") and known(seg[1], f"segment {n}")
        if len(seg) == 3:
            _label(seg[2], f"segment {n} label", errors)
    for n, c in enumerate(p.get("circles") or [], 1):
        if not isinstance(c, dict) or not _num(c.get("radius")) or c["radius"] <= 0:
            errors.append(f"circle {n} needs a 'centre' and a positive 'radius'")
        else:
            known(c.get("centre"), f"circle {n}")
    for n, a in enumerate(p.get("angles") or [], 1):
        if not isinstance(a, dict):
            errors.append(f"angle {n} needs 'at', 'from' and 'to'")
            continue
        if all(known(a.get(k), f"angle {n}") for k in ("at", "from", "to")) and "label" in a:
            _label(a["label"], f"angle {n} label", errors)
    if not (p.get("segments") or p.get("circles") or axes):
        errors.append("geometry needs segments, circles or axes")
    return errors


CHECKS = {
    "number_line": _number_line,
    "area_grid": _area_grid,
    "bars": _bars,
    "flow": _flow,
    "compare": _compare,
    "geometry": _geometry,
}
