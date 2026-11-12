"""Lessons: how SYNiq teaches a topic before any practice.

A topic's lesson is a short run of steps, one idea per step, in the textbook's order. Each step teaches the idea
(in a few sentences, with a picture when one helps) and then asks one quick question about just that idea. The
learner taps an answer and is told, right or wrong, why the right answer is right, before the next idea. Nothing
here is marked: check answers don't change mastery (that comes from practice), they show the learner and the
engine whether the idea landed.

Pack format (backend/content/README.md, "Lessons"):

    lesson:
      - teach: One idea, in two to five short sentences.
        picture: {...}            # optional, same kinds as a topic's picture (app/pictures.py)
        check:
          prompt: A question about this idea only.
          options: [right one, wrong one, wrong one]
          answer: right one
          why: Why the right answer is right, in a sentence or two.
        ways:                     # optional: the same idea explained another way, so each learner
          - style: visual         # meets it first the way that works for them (engine/methods.py)
            teach: ...            # and can ask for another way at any time. Each way is complete on
            picture: {...}        # its own: the check question can be answered from any of them.
          - style: real_world
            teach: ...

The step's own `teach` is its `style` (default text). A wrong check answer brings the next way and one more try
before the answer is shown; the way that then works is credited to the learner's method counts.
"""

from __future__ import annotations

import random

from .engine.methods import STYLES
from .pictures import check_picture

MIN_STEPS, MAX_STEPS = 2, 8
MAX_WAYS = 3


def ways_of(step: dict) -> list[dict]:
    """Every way this step is taught: its own teaching first, then the others in the order written."""
    main = {"style": step.get("style") or "text", "teach": str(step["teach"]).strip(), "picture": step.get("picture")}
    extra = [{"style": w["style"], "teach": str(w["teach"]).strip(), "picture": w.get("picture")} for w in step.get("ways") or []]
    return [main] + extra


def _check_ways(step: dict, where: str) -> list[str]:
    errors = []
    style = step.get("style", "text")
    if style not in STYLES:
        errors.append(f"{where}: unknown style {style}")
    if "ways" not in step:
        return errors
    ways = step["ways"]
    if not isinstance(ways, list) or not 1 <= len(ways) <= MAX_WAYS:
        return errors + [f"{where}: ways must be a list of 1 to {MAX_WAYS}"]
    seen = {style}
    for k, way in enumerate(ways, start=1):
        w = f"{where} way {k}"
        if not isinstance(way, dict):
            errors.append(f"{w} must be a mapping")
            continue
        unknown = set(way) - {"style", "teach", "picture"}
        if unknown:
            errors.append(f"{w}: unknown field {sorted(unknown)[0]}")
        if way.get("style") not in STYLES:
            errors.append(f"{w}: style must be one of {', '.join(STYLES)}")
        elif way["style"] in seen:
            errors.append(f"{w}: style {way['style']} is used twice in this step")
        seen.add(way.get("style"))
        if len(str(way.get("teach") or "").strip()) < 40:
            errors.append(f"{w}: 'teach' must explain the idea (40 characters or more)")
        if "picture" in way:
            errors += [f"{w}: {e}" for e in check_picture(way["picture"])]
        if way.get("style") == "visual" and "picture" not in way and "picture" not in step:
            errors.append(f"{w}: a visual way needs a picture")
    return errors


def check_lesson(lesson) -> list[str]:
    """Everything wrong with a lesson, as plain sentences. Empty when it can be taught."""
    if not isinstance(lesson, list) or not MIN_STEPS <= len(lesson) <= MAX_STEPS:
        return [f"lesson must be a list of {MIN_STEPS} to {MAX_STEPS} steps"]
    errors: list[str] = []
    prompts = []
    for n, step in enumerate(lesson, start=1):
        where = f"lesson step {n}"
        if not isinstance(step, dict):
            errors.append(f"{where} must be a mapping")
            continue
        unknown = set(step) - {"teach", "picture", "check", "style", "ways"}
        if unknown:
            errors.append(f"{where}: unknown field {sorted(unknown)[0]}")
        if not str(step.get("teach") or "").strip():
            errors.append(f"{where}: missing 'teach'")
        if "picture" in step:
            errors += [f"{where}: {e}" for e in check_picture(step["picture"])]
        errors += _check_ways(step, where)
        check = step.get("check")
        if not isinstance(check, dict):
            errors.append(f"{where}: missing 'check'")
            continue
        for field in ("prompt", "answer", "why"):
            if not str(check.get(field) or "").strip():
                errors.append(f"{where}: check is missing '{field}'")
        options = [str(o) for o in check.get("options") or []]
        if not 2 <= len(options) <= 4:
            errors.append(f"{where}: check needs 2 to 4 options")
        elif len(set(options)) != len(options):
            errors.append(f"{where}: check has the same option twice")
        elif str(check.get("answer")) not in options:
            errors.append(f"{where}: check answer is not one of its options")
        prompts.append(check.get("prompt"))
    if len(prompts) != len(set(prompts)):
        errors.append("lesson asks the same check question twice")
    return errors


def order_ways(ways: list[dict], order: list[str] | None) -> list[dict]:
    """The step's ways, the one most likely to work for this learner first (order = their styles, best first)."""
    if not order:
        return ways
    rank = {s: i for i, s in enumerate(order)}
    return sorted(ways, key=lambda w: rank.get(w["style"], len(rank)))


def public_lesson(lesson: list[dict] | None, concept_id: int, order: list[str] | None = None) -> list[dict] | None:
    """The lesson as the learner gets it: each step's ways in this learner's order, options shuffled (the same way
    each time), no answers or reasons. `teach` and `picture` are the first way's, for older apps."""
    if not lesson:
        return None
    steps = []
    for n, step in enumerate(lesson):
        options = [str(o) for o in step["check"]["options"]]
        random.Random(concept_id * 100 + n).shuffle(options)
        ways = order_ways(ways_of(step), order)
        steps.append(
            {
                "teach": ways[0]["teach"],
                "picture": ways[0]["picture"],
                "ways": ways,
                "check": {"prompt": step["check"]["prompt"], "options": options},
            }
        )
    return steps


def way_styles(lesson: list[dict], step: int) -> set[str]:
    return {w["style"] for w in ways_of(lesson[step])} if 0 <= step < len(lesson) else set()


def mark(lesson: list[dict], step: int, choice: str) -> dict:
    """Whether the tapped option is right, with the right answer and why. Raises IndexError for a step not there."""
    if not 0 <= step < len(lesson):
        raise IndexError(step)
    check = lesson[step]["check"]
    return {"right": str(choice).strip() == str(check["answer"]).strip(), "answer": str(check["answer"]), "why": check["why"].strip()}
