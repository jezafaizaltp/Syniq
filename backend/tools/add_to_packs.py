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


def _block(lines: list[str], code: str) -> tuple[int, int]:
    start = next(n for n, line in enumerate(lines) if line.rstrip() == f"  - code: {code}")
    end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith("  - code: ")), len(lines))
    return start, end


def merge(text: str, extra: dict) -> str:
    lines = text.split("\n")
    if extra.get("tips"):
        at = next(n for n, line in enumerate(lines) if line.rstrip() == "tips:")
        while at + 1 < len(lines) and lines[at + 1].startswith("  "):
            at += 1
        lines[at + 1 : at + 1] = _dump(extra["tips"], 2)
    for code, add in (extra.get("topics") or {}).items():
        start, end = _block(lines, code)
        if add.get("items"):
            items_at = next(n for n in range(start, end) if lines[n].rstrip() == "    items:")
            stop = next((n for n in range(items_at + 1, end) if lines[n].strip() and not lines[n].startswith("      ")), end)
            while stop > items_at + 1 and not lines[stop - 1].strip():
                stop -= 1
            lines[stop:stop] = _dump(add["items"], 6)
            start, end = _block(lines, code)
        if add.get("lesson"):
            old = next((n for n in range(start, end) if lines[n].rstrip() == "    lesson:"), None)
            if old is not None:
                stop = next(n for n in range(old + 1, end) if lines[n].strip() and not lines[n].startswith("      "))
                del lines[old:stop]
                start, end = _block(lines, code)
            items_at = next(n for n in range(start, end) if lines[n].rstrip() == "    items:")
            lines[items_at:items_at] = ["    lesson:", *_dump(add["lesson"], 6)]
    return "\n".join(lines)


def main(paths: list[str]) -> int:
    known = cp.known_tags() | {t for _, p in cp.read_packs() for t in (p.get("tips") or {})}
    failed = 0
    for p in paths:
        extra = yaml.safe_load(Path(p).read_text())
        target = CONTENT / extra["pack"]
        new = merge(target.read_text(), extra)
        errors = cp.check_pack(yaml.safe_load(new), known)
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
