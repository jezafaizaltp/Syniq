"""Every app word has a Malayalam version that keeps the same {placeholders}.

TypeScript already refuses a missing key; this catches a Malayalam line that drops or renames
a {name} (the child would see a raw "{name}") or was left in English by mistake.
"""

import re
from pathlib import Path

I18N = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "i18n.ts"


def _block(src: str, name: str) -> str:
    start = src.index("{", src.index(f"const {name}"))
    depth, i = 0, start
    while True:
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
        if depth == 0:
            return src[start + 1 : i - 1]


def _words(block: str) -> dict[str, str]:
    pattern = r'^\s*"([\w.]+)":\s*\n?\s*("(?:[^"\\]|\\.)*"|`[^`]*`)'
    return {m.group(1): m.group(2)[1:-1] for m in re.finditer(pattern, block, re.M)}


def test_every_app_word_has_malayalam_with_the_same_placeholders():
    src = I18N.read_text(encoding="utf-8")
    en, ml = _words(_block(src, "en")), _words(_block(src, "ml"))
    assert len(en) > 500 and set(en) == set(ml)
    holes = lambda t: sorted(set(re.findall(r"\{(\w+)\}", t)))  # noqa: E731
    wrong = [k for k in en if holes(en[k]) != holes(ml[k])]
    untranslated = [k for k in en if en[k] == ml[k] and re.search(r"[a-z]{3} [a-z]{3}", en[k])]
    assert wrong == [] and untranslated == []
