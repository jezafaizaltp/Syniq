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
"""

from __future__ import annotations

import random

from .pictures import check_picture

MIN_STEPS, MAX_STEPS = 2, 8


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
        unknown = set(step) - {"teach", "picture", "check"}
        if unknown:
            errors.append(f"{where}: unknown field {sorted(unknown)[0]}")
        if not str(step.get("teach") or "").strip():
            errors.append(f"{where}: missing 'teach'")
        if "picture" in step:
            errors += [f"{where}: {e}" for e in check_picture(step["picture"])]
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


def public_lesson(lesson: list[dict] | None, concept_id: int) -> list[dict] | None:
    """The lesson as the learner gets it: options shuffled (the same way each time), no answers or reasons."""
    if not lesson:
        return None
    steps = []
    for n, step in enumerate(lesson):
        options = [str(o) for o in step["check"]["options"]]
        random.Random(concept_id * 100 + n).shuffle(options)
        steps.append({"teach": step["teach"].strip(), "picture": step.get("picture"), "check": {"prompt": step["check"]["prompt"], "options": options}})
    return steps


def mark(lesson: list[dict], step: int, choice: str) -> dict:
    """Whether the tapped option is right, with the right answer and why. Raises IndexError for a step not there."""
    if not 0 <= step < len(lesson):
        raise IndexError(step)
    check = lesson[step]["check"]
    return {"right": str(choice).strip() == str(check["answer"]).strip(), "answer": str(check["answer"]), "why": check["why"].strip()}
