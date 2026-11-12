"""Add lessons, questions and tips to existing content packs without rewriting what is already there.

    cd backend
    python -m tools.add_to_packs extra/maths/01-pairs-of-equations.yaml [more files...]

Each extra file names its pack and what to add to each topic:

    pack: maths/01-pairs-of-equations.yaml     # under backend/content/
    tips:                                      # optional: new mistake tips for the pack
      some_tag: "A hint that points the way."
    topics:
      math9.pairs.sum_difference:
        lesson: [...]                          # app/lessons.py; replaces any lesson the topic has
        items: [...]                           # new questions, added after the topic's own
        ways:                                  # more ways to teach each lesson step, in step order
          - [{style: real_world, teach: ...}]  # step 1's other ways (app/lessons.py); [] leaves a step as it is

The pack's text is changed in place (comments and layout kept), then the whole pack is checked with the same
rules as the loader. Nothing is written if the check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from app import content_packs as cp

CONTENT = Path(__file__).resolve().parent.parent / "content"


def _dump(value, indent: int) -> list[str]:
    text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000, default_flow_style=False)
    return [(" " * indent + line) if line else line for line in text.rstrip("\n").split("\n")]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block(lines: list[str], code: str) -> tuple[int, int, int]:
    """Where the topic starts and ends, and the indent of its keys (packs nest lists either way)."""
    start = next(n for n, line in enumerate(lines) if line.lstrip(" ").rstrip() == f"- code: {code}")
    ind = _indent(lines[start])
    end = next((n for n in range(start + 1, len(lines)) if lines[n].strip() and _indent(lines[n]) <= ind), len(lines))
    return start, end, ind + 2


def _value_end(lines: list[str], at: int, end: int, key: int) -> int:
    """The line after the value of the key on line `at` (a list may sit at the key's own indent)."""
    stop = next(
        (n for n in range(at + 1, end) if lines[n].strip() and _indent(lines[n]) <= key and not lines[n].startswith(" " * key + "- ")),
        end,
    )
    while stop > at + 1 and not lines[stop - 1].strip():
        stop -= 1
    return stop


def with_ways(pack: dict, code: str, ways: list, lesson: list | None = None) -> list:
    """The topic's lesson (or the new one given) with each step's other ways added."""
    if lesson is None:
        lesson = next(c for c in pack["concepts"] if c["code"] == code)["lesson"]
    if len(ways) != len(lesson):
        raise SystemExit(f"{code}: {len(ways)} lists of ways for a lesson of {len(lesson)} steps")
    out = []
    for step, more in zip(lesson, ways):
        step = dict(step)
        if more:
            step["ways"] = list(step.get("ways") or []) + list(more)
        out.append(step)
    return out


def merge(text: str, extra: dict) -> str:
    lines = text.split("\n")
    if extra.get("tips"):
        at = next(n for n, line in enumerate(lines) if line.rstrip() == "tips:")
        while at + 1 < len(lines) and lines[at + 1].startswith("  "):
            at += 1
        lines[at + 1 : at + 1] = _dump(extra["tips"], 2)
    for code, add in (extra.get("topics") or {}).items():
        if add.get("ways"):
            add = {**add, "lesson": with_ways(yaml.safe_load("\n".join(lines)), code, add["ways"], add.get("lesson"))}
        start, end, key = _block(lines, code)
        if add.get("items"):
            items_at = next(n for n in range(start, end) if lines[n].rstrip() == " " * key + "items:")
            stop = _value_end(lines, items_at, end, key)
            lines[stop:stop] = _dump(add["items"], _indent(lines[items_at + 1]))
            start, end, key = _block(lines, code)
        if add.get("lesson"):
            old = next((n for n in range(start, end) if lines[n].rstrip() == " " * key + "lesson:"), None)
            if old is not None:
                del lines[old : _value_end(lines, old, end, key)]
                start, end, key = _block(lines, code)
            items_at = next(n for n in range(start, end) if lines[n].rstrip() == " " * key + "items:")
            lines[items_at:items_at] = [" " * key + "lesson:", *_dump(add["lesson"], key + 2)]
    return "\n".join(lines)


def main(paths: list[str]) -> int:
    known = cp.known_tags() | {t for _, p in cp.read_packs() for t in (p.get("tips") or {})}
    failed = 0
    for p in paths:
        extra = yaml.safe_load(Path(p).read_text())
        target = CONTENT / extra["pack"]
        new = merge(target.read_text(), extra)
        # Tip tags are shared by every pack, so a new tip must not reuse a tag that already has a text.
        errors = [f"tip tag '{t}' already exists; pick a new name" for t in (extra.get("tips") or {}) if t in known]
        errors += cp.check_pack(yaml.safe_load(new), known)
        if errors:
            failed += 1
            print(f"{extra['pack']}: NOT changed")
            for e in errors[:20]:
                print("   ", e)
            continue
        target.write_text(new)
        print(f"{extra['pack']}: {len(extra.get('topics') or {})} topics updated")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
