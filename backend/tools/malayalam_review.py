"""Make a language review workbook (Malayalam or Hindi) and read the reviewed one back.

    cd backend
    python -m tools.malayalam_review --out /tmp/malayalam-review.xlsx [--new-since <git ref>]
    python -m tools.malayalam_review --lang hi --out /tmp/hindi-review.xlsx
    python -m tools.malayalam_review --apply reviewed.xlsx [--report changes.md] [--dry-run]

The reviewer either corrects the wording in place (question, choices, answer, hints,
solution, or the Malayalam/Hindi column of App words) or writes a note in the last
column. --apply puts in-place corrections into the content packs and the app's word
lists, and writes every note, and anything it could not place, into a report.

Sheets:
  1. Questions - every question in content/malayalam (or content/hindi), newest first when --new-since is
     given, with choices, answer, hints, solution and the tip shown after each wrong answer.
  2. App words - every Malayalam string the app shows (frontend/lib/i18n.ts and
     backend/app/i18n.py), next to the English.
Each row has an empty "OK? / better wording" column for the reviewer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
PACK_DIRS = {"ml": BACKEND / "content" / "malayalam", "hi": BACKEND / "content" / "hindi"}
REVIEW_HEAD = "OK? / better wording"
OK_WORDS = {"", "ok", "okay", "yes", "y", "✓", "✔", "ശരി", "ശരിയാണ്", "ठीक", "ठीक है", "सही", "हाँ"}
Q_HEAD = ["New?", "Unit", "Topic", "Question", "Choices", "Right answer", "Hints", "Solution",
          "Tip after each wrong answer", REVIEW_HEAD, "code", "id"]


def _old_prompts(ref: str, packs_dir: Path) -> set[str]:
    seen: set[str] = set()
    for path in sorted(packs_dir.glob("*.yaml")):
        rel = path.relative_to(REPO).as_posix()
        out = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=REPO, capture_output=True, text=True)
        if out.returncode:
            continue
        for c in yaml.safe_load(out.stdout)["concepts"]:
            seen.update(i["prompt"] for i in c["items"])
    return seen


def _prompt_id(code: str, n: int, prompt: str) -> str:
    return f"{code}#{n}#{hashlib.sha1(prompt.encode()).hexdigest()[:8]}"


def _load_packs(packs_dir: Path) -> list[tuple[Path, dict]]:
    return [(p, yaml.safe_load(p.read_text(encoding="utf-8"))) for p in sorted(packs_dir.glob("*.yaml"))]


def _all_tips() -> dict[str, tuple[Path, str]]:
    """Every tip tag in every pack, with the pack that defines it first (that text wins)."""
    from app import content_packs

    out: dict[str, tuple[Path, str]] = {}
    for path, pack in content_packs.read_packs():
        for tag, text in (pack.get("tips") or {}).items():
            out.setdefault(tag, (path, text))
    return out


def question_rows(new_since: str | None, lang: str = "ml") -> list[list[str]]:
    packs_dir = PACK_DIRS[lang]
    old = _old_prompts(new_since, packs_dir) if new_since else None
    tips = {tag: text for tag, (_, text) in _all_tips().items()}
    rows = []
    for path, pack in _load_packs(packs_dir):
        for c in pack["concepts"]:
            for n, item in enumerate(c["items"]):
                mistakes = item.get("mistakes") or {}
                tip_lines = [f"{wrong} → {tips.get(tag, tag)}" for wrong, tag in mistakes.items()]
                is_new = old is not None and item["prompt"] not in old
                rows.append([
                    "new" if is_new else "",
                    pack.get("title", path.stem),
                    c.get("title", c["code"]),
                    item["prompt"],
                    "\n".join(map(str, item.get("options") or [])),
                    str(item["answer"]),
                    "\n".join(item.get("hints") or []),
                    item.get("solution", ""),
                    "\n\n".join(tip_lines),
                    "",
                    c["code"],
                    _prompt_id(c["code"], n, item["prompt"]),
                ])
    rows.sort(key=lambda r: r[0] != "new")
    return rows


def app_word_rows(lang: str = "ml") -> list[list[str]]:
    rows: list[list[str]] = []
    ts = REPO / "frontend" / "lib" / "i18n.ts"
    out = subprocess.run(
        ["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", _TS_DUMP, ts.as_uri()],
        capture_output=True, text=True,
    )
    if out.returncode == 0:
        data = json.loads(out.stdout)
        for key, en in data["en"].items():
            rows.append(["app screen", key, en, data[lang].get(key, ""), ""])
    else:  # node missing: still give the server words
        rows.append(["app screen", "(could not read frontend/lib/i18n.ts)", out.stderr[:200], "", ""])
    from app.i18n import MESSAGES
    from app.i18n_hi import HINDI

    for key, langs in MESSAGES.items():
        local = langs.get("ml", "") if lang == "ml" else HINDI.get(key, "")
        rows.append(["server message", key, langs.get("en", ""), local, ""])
    return rows


# i18n.ts keeps its tables private; read the module text, strip the exports we don't
# need, and evaluate it as a module that hands back the en and ml tables.
_TS_DUMP = r"""
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
const src = readFileSync(fileURLToPath(process.argv[1]), "utf8");
const dir = mkdtempSync(join(tmpdir(), "i18n-"));
const file = join(dir, "i18n.ts");
writeFileSync(file, src + "\nexport const __REVIEW = { en, ml, hi };\n");
const m = await import("file://" + file);
console.log(JSON.stringify(m.__REVIEW));
"""


def write(path: Path, questions: list[list[str]], words: list[list[str]], lang: str = "ml") -> None:
    wb = Workbook()
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="8B3A2B")
    new_fill = PatternFill("solid", fgColor="FFF4C2")
    wrap = Alignment(wrap_text=True, vertical="top")

    ws = wb.active
    ws.title = "Questions"
    ws.append(Q_HEAD)
    for r in questions:
        ws.append(r)
    widths = [7, 24, 22, 45, 35, 30, 35, 45, 55, 30, 18, 4]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap
        if row[0].value == "new":
            for cell in row:
                cell.fill = new_fill

    ws2 = wb.create_sheet("App words")
    ws2.append(["Where", "Key", "English", "Malayalam" if lang == "ml" else "Hindi", REVIEW_HEAD])
    for r in words:
        ws2.append(r)
    for i, w in enumerate([14, 30, 50, 50, 30]):
        ws2.column_dimensions[chr(65 + i)].width = w
    for row in ws2.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap

    for sheet in (ws, ws2):
        for cell in sheet[1]:
            cell.font, cell.fill = head_font, head_fill
        sheet.freeze_panes = "A2"
    ws.column_dimensions["L"].hidden = True  # row id for --apply; keep it
    wb.save(path)


# --- Reading a reviewed workbook back --------------------------------------------------------


@dataclass
class Result:
    applied: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return f"{len(self.applied)} changes applied, {len(self.notes)} notes, {len(self.problems)} to do by hand"

    def markdown(self) -> str:
        out = ["# Review read back", "", self.summary(), ""]
        for title, lines in (("Applied", self.applied), ("Notes from the reviewer", self.notes),
                             ("Could not apply automatically", self.problems)):
            out += [f"## {title}", ""] + ([f"- {x}" for x in lines] or ["- none"]) + [""]
        return "\n".join(out)


def _cell(v) -> str:
    return "" if v is None else str(v).strip()


def _lines(v: str) -> list[str]:
    return [x.strip() for x in v.split("\n") if x.strip()]


def _literals(s: str) -> list[str]:
    """The ways a string can be written in our YAML, TypeScript and Python files."""
    single = "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return [json.dumps(s, ensure_ascii=False), single]


def _replace_after(text: str, start: int, end: int, old: str, new: str) -> tuple[str, bool]:
    for lit in _literals(old):
        i = text.find(lit, start, end)
        if i >= 0:
            return text[:i] + json.dumps(new, ensure_ascii=False) + text[i + len(lit):], True
    return text, False


def _item_block(text: str, prompt: str) -> tuple[int, int] | None:
    i = text.find(f"- prompt: {json.dumps(prompt, ensure_ascii=False)}")
    if i < 0:
        return None
    nxt = [j for j in (text.find("- prompt:", i + 1), text.find("\n  - code:", i + 1)) if j >= 0]
    return i, min(nxt) if nxt else len(text)


def _apply_questions(ws, result: Result, dry_run: bool) -> None:
    head = [_cell(c.value) for c in ws[1]]
    if "id" not in head:
        result.problems.append("Questions sheet has no id column (made by an old version); notes only")
    col = {name: head.index(name) for name in head if name}
    index: dict[str, tuple[Path, dict, int]] = {}
    for packs_dir in PACK_DIRS.values():
        for path, pack in _load_packs(packs_dir):
            for c in pack["concepts"]:
                for n, item in enumerate(c["items"]):
                    index[_prompt_id(c["code"], n, item["prompt"])] = (path, item, n)
    tips = _all_tips()
    tip_edits: dict[str, tuple[str, str]] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        get = lambda name: _cell(row[col[name]]) if name in col and col[name] < len(row) else ""
        where = f"{get('code')} '{get('Question')[:50]}'"
        note = get(REVIEW_HEAD)
        if note.lower() not in OK_WORDS:
            result.notes.append(f"{where}: {note}")
        rid = get("id")
        if not rid:
            continue
        if rid not in index:
            result.problems.append(f"{where}: this question changed since the workbook was made; check by hand")
            continue
        path, item, _ = index[rid]
        changes: dict[str, str] = {}
        if get("Question") != item["prompt"]:
            changes[item["prompt"]] = get("Question")
        old_opts = [str(o) for o in item.get("options") or []]
        new_opts = _lines(get("Choices"))
        if old_opts and new_opts != old_opts:
            if len(new_opts) != len(old_opts):
                result.problems.append(f"{where}: number of choices changed ({len(old_opts)} -> {len(new_opts)})")
            else:
                changes.update({o: n for o, n in zip(old_opts, new_opts) if o != n})
        old_ans, new_ans = str(item["answer"]), get("Right answer")
        if new_ans != old_ans:
            if old_opts and new_ans not in new_opts:
                result.problems.append(f"{where}: new answer '{new_ans}' is not one of the choices")
                continue
            if not old_opts:
                result.problems.append(f"{where}: typed answer changed to '{new_ans}'; its check needs a person")
                continue
        old_hints, new_hints = list(item.get("hints") or []), _lines(get("Hints"))
        if new_hints != old_hints:
            if len(new_hints) != len(old_hints):
                result.problems.append(f"{where}: number of hints changed; edit by hand")
            else:
                changes.update({o: n for o, n in zip(old_hints, new_hints) if o != n})
        if get("Solution") and get("Solution") != item.get("solution", ""):
            changes[item.get("solution", "")] = get("Solution")
        for block in get("Tip after each wrong answer").split("\n\n"):
            if " → " not in block:
                continue
            wrong, text = (x.strip() for x in block.split(" → ", 1))
            tag = (item.get("mistakes") or {}).get(wrong)
            if tag and tag in tips and text != tips[tag][1]:
                if tag in tip_edits and tip_edits[tag][1] != text:
                    result.problems.append(f"tip {tag}: two different new wordings; pick one by hand")
                tip_edits[tag] = (tips[tag][1], text)
        if not changes:
            continue
        text = path.read_text(encoding="utf-8")
        span = _item_block(text, item["prompt"])
        if not span:
            result.problems.append(f"{where}: could not find it in {path.name}")
            continue
        new_text, ok = text, True
        for old, new in changes.items():
            start, end = _item_block(new_text, changes.get(item["prompt"], item["prompt"])
                                     if old != item["prompt"] else item["prompt"]) or (0, 0)
            seg = new_text[start:end]
            count = sum(seg.count(lit) for lit in _literals(old))
            if not count:
                ok = False
                break
            for lit in _literals(old):
                seg = seg.replace(lit, json.dumps(new, ensure_ascii=False))
            new_text = new_text[:start] + seg + new_text[end:]
        if not ok:
            result.problems.append(f"{where}: could not place the change in {path.name}")
            continue
        try:
            yaml.safe_load(new_text)
        except yaml.YAMLError as e:
            result.problems.append(f"{where}: change would break {path.name} ({e.__class__.__name__})")
            continue
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        for old, new in changes.items():
            result.applied.append(f"{path.name} {where}: '{old}' -> '{new}'")
    for tag, (old, new) in tip_edits.items():
        path = tips[tag][0]
        text = path.read_text(encoding="utf-8")
        i = text.find(f"\n  {tag}: ")
        end = text.find("\n", i + 1)
        new_text, ok = _replace_after(text, i, end, old, new) if i >= 0 else (text, False)
        if not ok:
            result.problems.append(f"tip {tag}: could not place the new wording in {path.name}")
            continue
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        result.applied.append(f"tip {tag} ({path.name}): '{old}' -> '{new}'")


def _apply_words(ws, result: Result, dry_run: bool) -> None:
    lang = "hi" if _cell(ws.cell(1, 4).value) == "Hindi" else "ml"
    current = {(r[0], r[1]): r[3] for r in app_word_rows(lang)}
    ts_path = REPO / "frontend" / "lib" / "i18n.ts"
    py_path = BACKEND / "app" / ("i18n_hi.py" if lang == "hi" else "i18n.py")
    files = {ts_path: ts_path.read_text(encoding="utf-8"), py_path: py_path.read_text(encoding="utf-8")}
    for row in ws.iter_rows(min_row=2, values_only=True):
        where_kind, key, _en, new, note = (_cell(v) for v in (list(row) + [None] * 5)[:5])
        if note.lower() not in OK_WORDS:
            result.notes.append(f"app word {key}: {note}")
        old = current.get((where_kind, key))
        if old is None or not new or new == old.strip():
            continue
        if where_kind == "app screen":
            path, text = ts_path, files[ts_path]
            block_start = text.find(f"const {lang}: Record<Key, string> = {{")
            block_end = text.find("\n};", block_start)
            k = text.find(f'"{key}":', block_start, block_end)
        else:
            path, text = py_path, files[py_path]
            k = text.find(f'"{key}":')
            if lang == "ml" and k >= 0:
                k = text.find('"ml":', k)
            block_end = len(text)
        if k < 0:
            result.problems.append(f"app word {key}: not found in {path.name}")
            continue
        end = min(block_end, k + len(old) * 4 + 400)
        text, ok = _replace_after(text, k, end, old, new)
        if not ok:
            result.problems.append(f"app word {key}: could not place the new wording in {path.name}")
            continue
        files[path] = text
        result.applied.append(f"app word {key}: '{old}' -> '{new}'")
    if not dry_run:
        for path, text in files.items():
            path.write_text(text, encoding="utf-8")


def apply_workbook(path: Path, dry_run: bool = False) -> Result:
    wb = load_workbook(path)
    result = Result()
    if "Questions" in wb.sheetnames:
        _apply_questions(wb["Questions"], result, dry_run)
    if "App words" in wb.sheetnames:
        _apply_words(wb["App words"], result, dry_run)
    return result



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="write a fresh review workbook here")
    ap.add_argument("--lang", choices=["ml", "hi"], default="ml")
    ap.add_argument("--new-since", help="git ref; questions not in it are marked new and listed first")
    ap.add_argument("--apply", help="a reviewed workbook to read back")
    ap.add_argument("--report", help="where to write the list of changes and notes (Markdown)")
    ap.add_argument("--dry-run", action="store_true", help="with --apply: report only, change nothing")
    args = ap.parse_args()
    if args.apply:
        result = apply_workbook(Path(args.apply), dry_run=args.dry_run)
        text = result.markdown()
        if args.report:
            Path(args.report).write_text(text, encoding="utf-8")
        print(text if not args.report else f"{result.summary()} -> {args.report}")
        return
    if not args.out:
        ap.error("give --out to make a workbook, or --apply to read one back")
    q = question_rows(args.new_since, args.lang)
    w = app_word_rows(args.lang)
    write(Path(args.out), q, w, args.lang)
    print(f"{len(q)} questions ({sum(r[0] == 'new' for r in q)} new), {len(w)} app words -> {args.out}")


if __name__ == "__main__":
    main()
