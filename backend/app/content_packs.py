"""Content packs: chapters of explanations and questions written as YAML files.

A pack is one chapter of one subject (see content/README.md for the format). Loading
a pack creates the chapter if it is missing and adds or updates its topics,
explanations, questions and mistake tips. Packs are the source of truth for what
they loaded: running the loader again updates those rows, and a question taken out
of a pack is withdrawn. Explanations and questions written by teachers in the app
are never touched.

Every question is checked before anything is saved: the structure, and, where the
question has a `check`, the answer itself, worked out again by computer.

Run:  python -m app.content_packs            # load everything in content/
      python -m app.content_packs --check    # check only, save nothing
"""

import re
import sys
from fractions import Fraction
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from . import i18n
from .models import Chapter, Concept, ConceptPrereq, Explanation, Item, Misconception, Subject

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
STYLES = ("text", "visual", "step_by_step", "real_world")
SOURCE = "pack"
REVIEW_NOTE = "Written and checked by Claude for SYNiq. Not yet reviewed by a school teacher."


def read_packs(paths: list[Path] | None = None) -> list[tuple[Path, dict]]:
    files = []
    for p in paths or [CONTENT_DIR]:
        files += sorted(p.rglob("*.yaml")) if p.is_dir() else [p]
    return [(f, yaml.safe_load(f.read_text(encoding="utf-8"))) for f in files]


# --- Checking -------------------------------------------------------------------------

def _number(text: str) -> Fraction | None:
    try:
        return Fraction(str(text).strip().replace("−", "-"))
    except (ValueError, ZeroDivisionError):
        return None


def to_sympy(text: str):
    """Read maths as students see it (x² + 5x + 6, 3√2, 2/5) into a sympy expression."""
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    s = str(text).strip()
    for a, b in (("−", "-"), ("×", "*"), ("·", "*"), ("÷", "/"), ("²", "^2"), ("³", "^3"), ("π", " pi ")):
        s = s.replace(a, b)
    s = re.sub(r"√\(", "sqrt(", s)
    s = re.sub(r"√(\d+(?:\.\d+)?|[a-z])", r"sqrt(\1)", s)
    return parse_expr(s, transformations=standard_transformations + (implicit_multiplication_application, convert_xor))


def _exact(e):
    """Decimals as exact fractions (1.414 is 1414/1000), so comparisons don't depend on rounding."""
    from sympy import Float, Rational

    return e.xreplace({f: Rational(str(f)) for f in e.atoms(Float)})


def _equal(a, b) -> bool:
    from sympy import simplify

    return simplify(_exact(a) - _exact(b)) == 0


def check_pack(pack: dict, known_tags: set[str] | None = None) -> list[str]:
    """Everything wrong with a pack, as plain sentences. Empty when it is fine to load."""
    errors: list[str] = []
    for field in ("subject", "chapter", "title", "concepts"):
        if not pack.get(field):
            errors.append(f"missing '{field}'")
    if errors:
        return errors
    tips = pack.get("tips") or {}
    tags = set(tips) | (known_tags or set())
    codes = [c.get("code") for c in pack["concepts"]]
    if len(codes) != len(set(codes)):
        errors.append("a topic code is used twice")

    for c in pack["concepts"]:
        where = c.get("code", "?")
        for field in ("code", "title", "notes", "explanations", "items"):
            if not c.get(field):
                errors.append(f"{where}: missing '{field}'")
        for style in STYLES:
            if not (c.get("explanations") or {}).get(style):
                errors.append(f"{where}: needs a '{style}' explanation")
        for style in c.get("explanations") or {}:
            if style not in STYLES:
                errors.append(f"{where}: unknown explanation style '{style}'")
        levels = {i.get("difficulty") for i in c.get("items") or []}
        if not {1, 2} <= levels:
            errors.append(f"{where}: needs questions at difficulty 1 and 2")
        prompts = [i.get("prompt") for i in c.get("items") or []]
        if len(prompts) != len(set(prompts)):
            errors.append(f"{where}: the same question is in twice")
        for n, item in enumerate(c.get("items") or [], start=1):
            errors += [f"{where} question {n}: {e}" for e in check_item(item, tags)]
    return errors


def check_item(item: dict, tags: set[str]) -> list[str]:
    errors = []
    for field in ("prompt", "answer", "hints", "solution", "difficulty"):
        if item.get(field) in (None, "", []):
            errors.append(f"missing '{field}'")
    if errors:
        return errors
    answer = str(item["answer"])
    options = [str(o) for o in item.get("options") or []]
    mistakes = {str(k): v for k, v in (item.get("mistakes") or {}).items()}
    if item["difficulty"] not in (1, 2, 3):
        errors.append("difficulty must be 1, 2 or 3")

    if options:
        if not 3 <= len(options) <= 4:
            errors.append("a choice question needs 3 or 4 options")
        if len(set(options)) != len(options):
            errors.append("two options are the same")
        if answer not in options:
            errors.append(f"the answer '{answer}' is not one of the options")
        for wrong in mistakes:
            if wrong not in options or wrong == answer:
                errors.append(f"mistake '{wrong}' should be one of the wrong options")
    else:
        if _number(answer) is None:
            errors.append(f"a typed answer must be a number, not '{answer}' (use options instead)")
        if "check" not in item:
            errors.append("a typed-answer question needs a 'check'")
        for wrong in mistakes:
            if _number(wrong) is None or _number(wrong) == _number(answer):
                errors.append(f"mistake '{wrong}' should be a different number")
    for tag in mistakes.values():
        if tag not in tags:
            errors.append(f"mistake tag '{tag}' has no tip")

    if item.get("check") is not None and not errors:
        errors += check_answer(item["check"], answer, options)
    return errors


def check_answer(check: str, answer: str, options: list[str]) -> list[str]:
    """Work the answer out again from `check` and compare it with the stored answer and options."""
    try:
        expected = to_sympy(check)
    except Exception as e:  # noqa: BLE001 - any parse failure is a content error
        return [f"can't read check '{check}': {e}"]
    try:
        if not _equal(to_sympy(answer), expected):
            return [f"the answer '{answer}' doesn't match the check '{check}' (= {expected})"]
    except Exception:  # noqa: BLE001
        return [f"can't read the answer '{answer}' as maths"]
    for o in options:
        if o == answer:
            continue
        try:
            if _equal(to_sympy(o), expected):
                return [f"option '{o}' is also correct"]
        except Exception:  # noqa: BLE001 - options in words can't also be right by value
            continue
    return []


def known_tags() -> set[str]:
    return {k.removeprefix("tip.") for k in i18n.MESSAGES if k.startswith("tip.")}


def check_all(packs: list[tuple[Path, dict]]) -> list[str]:
    errors = []
    seen: dict[str, Path] = {}
    # A tip given in one pack can be used in any other, since all packs load together.
    tags = known_tags() | {tag for _, pack in packs for tag in (pack.get("tips") or {})}
    for path, pack in packs:
        errors += [f"{path.name}: {e}" for e in check_pack(pack, tags)]
        for c in pack.get("concepts") or []:
            if c.get("code") in seen:
                errors.append(f"{path.name}: topic code {c['code']} is also in {seen[c['code']].name}")
            seen[c.get("code")] = path
    for path, pack in packs:
        for c in pack.get("concepts") or []:
            for p in c.get("after") or []:
                if p not in seen:
                    errors.append(f"{path.name}: {c['code']} comes after unknown topic {p}")
    return errors


# --- Loading --------------------------------------------------------------------------

def load(db: DbSession, packs: list[tuple[Path, dict]]) -> dict:
    """Save packs that passed check_all. Returns counts of what changed."""
    counts = {"chapters": 0, "concepts": 0, "explanations": 0, "items": 0, "withdrawn": 0}
    concepts: dict[str, Concept] = {}
    for path, pack in packs:
        subject = db.scalars(select(Subject).where(Subject.code == pack["subject"])).first()
        if not subject:
            raise ValueError(f"{path.name}: no subject with code {pack['subject']}")
        chapter = db.scalars(
            select(Chapter).where(Chapter.subject_id == subject.id, Chapter.number == pack["chapter"])
        ).first()
        if not chapter:
            chapter = Chapter(subject_id=subject.id, number=pack["chapter"], title=pack["title"])
            db.add(chapter)
            db.flush()
            counts["chapters"] += 1
        elif chapter.title != pack["title"]:
            raise ValueError(f"{path.name}: chapter {pack['chapter']} is called '{chapter.title}' here, not '{pack['title']}'")

        for tag, tip in (pack.get("tips") or {}).items():
            row = db.scalars(select(Misconception).where(Misconception.tag == tag)).first()
            if row:
                row.tip = tip.strip()
            else:
                db.add(Misconception(tag=tag, tip=tip.strip()))

        for order, c in enumerate(pack["concepts"]):
            concept = db.scalars(select(Concept).where(Concept.code == c["code"])).first()
            if not concept:
                concept = Concept(code=c["code"], chapter_id=chapter.id, title=c["title"])
                db.add(concept)
                counts["concepts"] += 1
            concept.chapter_id, concept.title, concept.order, concept.notes = chapter.id, c["title"], order, c["notes"].strip()
            db.flush()
            concepts[c["code"]] = concept
            counts["explanations"] += _load_explanations(db, concept, c["explanations"])
            added, withdrawn = _load_items(db, concept, c["items"])
            counts["items"] += added
            counts["withdrawn"] += withdrawn

    for _, pack in packs:
        for c in pack["concepts"]:
            concept = concepts[c["code"]]
            db.query(ConceptPrereq).filter(ConceptPrereq.concept_id == concept.id).delete()
            for p in c.get("after") or []:
                prereq = concepts.get(p) or db.scalars(select(Concept).where(Concept.code == p)).first()
                db.add(ConceptPrereq(concept_id=concept.id, prereq_id=prereq.id))
    db.commit()
    return counts


def _load_explanations(db: DbSession, concept: Concept, explanations: dict) -> int:
    added = 0
    for style, body in explanations.items():
        row = db.scalars(
            select(Explanation).where(Explanation.concept_id == concept.id, Explanation.style == style, Explanation.source == SOURCE)
        ).first()
        if not row:
            row = Explanation(concept_id=concept.id, style=style, source=SOURCE)
            db.add(row)
            added += 1
        row.body, row.status, row.review_note = body.strip(), "approved", REVIEW_NOTE
    return added


def _load_items(db: DbSession, concept: Concept, items: list[dict]) -> tuple[int, int]:
    existing = {i.prompt: i for i in db.scalars(select(Item).where(Item.concept_id == concept.id, Item.source == SOURCE)).all()}
    added = 0
    for spec in items:
        prompt = spec["prompt"].strip()
        row = existing.pop(prompt, None)
        if not row:
            row = Item(concept_id=concept.id, prompt=prompt, source=SOURCE)
            db.add(row)
            added += 1
        options = [str(o) for o in spec.get("options") or []]
        row.kind = "mcq" if options else "numeric"
        row.options = options
        row.answer = str(spec["answer"])
        row.hints = [str(h) for h in spec["hints"]]
        row.solution = spec["solution"].strip()
        row.difficulty = spec["difficulty"]
        row.misconceptions = {str(k): v for k, v in (spec.get("mistakes") or {}).items()}
        row.status, row.review_note = "approved", REVIEW_NOTE
    for row in existing.values():
        if row.status != "rejected":
            row.status, row.review_note = "rejected", "Taken out of the content pack."
    return added, sum(1 for _ in existing)


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    paths = [Path(a) for a in argv if not a.startswith("--")]
    packs = read_packs(paths or None)
    errors = check_all(packs)
    questions = sum(len(c["items"]) for _, p in packs for c in p.get("concepts") or [])
    checked = sum(1 for _, p in packs for c in p.get("concepts") or [] for i in c["items"] if i.get("check") is not None)
    for e in errors:
        print(e)
    print(f"{len(packs)} chapters, {questions} questions, {checked} answers worked out again by computer, {len(errors)} problems")
    if errors or check_only:
        return 1 if errors else 0

    from .db import SessionLocal

    with SessionLocal() as db:
        if not db.scalars(select(Subject)).first():
            print("No subjects yet: run python -m app.bootstrap first, which also loads the content.")
            return 0
        print(load(db, packs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
