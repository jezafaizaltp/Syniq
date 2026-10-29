"""How SYNiq responds to an answer, without calling any AI.

There are ten response modes, in two groups.

Support modes are switched on in settings by the student, a parent or a
teacher. They change how every response is presented. They describe what
helps, not a diagnosis: SYNiq never infers them and never labels a student.

    focus          Short bursts, one step at a time, a quick challenge to finish.
    easy_read      One short sentence per line, read aloud, clearer font.
    screen_reader  Everything in words; no meaning carried only by pictures.
    visual_first   Never relies on sound; pictures and text for everything.
    tap_to_answer  Tap choices instead of typing or speaking.
    small_steps    Objects and smaller numbers first, then the real question.

Answer-driven modes are picked from how the student answers, getting more
concrete each time the same topic goes wrong in a row.

    count_it_out   Show the sum with objects (stars, tens blocks) and where it went wrong.
    step_by_step   The worked solution, one step per line.
    real_life      The same idea as an everyday story.
    try_similar    A smaller question with the same idea, to rebuild confidence.

If none of these has helped after several tries, the response suggests the AI
tutor, when the school has switched it on.

Everything here is a pure function so it can be tested without a database.
"""

import re
from dataclasses import dataclass, field

RESPONSES_VERSION = "2026.10-1"

SUPPORT_MODES = ["focus", "easy_read", "screen_reader", "visual_first", "tap_to_answer", "small_steps"]
ANSWER_MODES = ["count_it_out", "step_by_step", "real_life", "try_similar"]

# After this many wrong answers in a row, offer the AI tutor.
SUGGEST_TUTOR_AFTER = 4

STAR, TEN = "⭐", "🟦"
MAX_STARS = 20  # bigger numbers are drawn as tens blocks
MAX_BLOCKS = 100  # beyond this a picture stops helping

OPS = {"+": "+", "-": "−", "−": "−", "x": "×", "×": "×", "*": "×", "÷": "÷", "/": "÷"}
_SUM = re.compile(r"(\d+)\s*([+\-−x×*÷/])\s*(\d+)")


@dataclass
class Arithmetic:
    a: int
    op: str  # + − × ÷
    b: int

    @property
    def result(self) -> int:
        return {"+": self.a + self.b, "−": self.a - self.b, "×": self.a * self.b, "÷": self.a // self.b}[self.op]

    def text(self) -> str:
        return f"{self.a} {self.op} {self.b}"


def parse_arithmetic(prompt: str, answer: str) -> Arithmetic | None:
    """Spot a simple whole-number sum in a question, so teachers don't have to tag it.

    Only trusted when the sum's result matches the item's answer.
    """
    m = _SUM.search(prompt)
    if not m:
        return None
    a, op, b = int(m.group(1)), OPS[m.group(2)], int(m.group(3))
    if op == "÷" and (b == 0 or a % b):
        return None
    sum_ = Arithmetic(a, op, b)
    try:
        return sum_ if int(answer.strip()) == sum_.result else None
    except ValueError:
        return None


# --- Spotting the mistake -------------------------------------------------------------

def diagnose(s: Arithmetic, response: int) -> tuple[str, str]:
    """Return (mistake tag, plain-words description) for a wrong whole-number answer."""
    right = s.result
    diff = response - right
    if s.op == "+" and response == abs(s.a - s.b):
        return "subtracted_instead", "It looks like you took away instead of adding."
    if s.op == "−" and response == s.a + s.b:
        return "added_instead", "It looks like you added instead of taking away."
    if s.op == "+" and response == s.a * s.b:
        return "multiplied_instead", "It looks like you multiplied instead of adding."
    if s.op == "×" and response == s.a + s.b:
        return "added_instead", "It looks like you added instead of multiplying."
    if s.op == "×" and abs(diff) in (s.a, s.b):
        return "one_group_off", "You have one group too many or too few."
    if response in (s.a, s.b) and s.op in "+×":
        return "one_group_only", "It looks like you counted only one of the groups."
    if abs(diff) == 1:
        return "counting_slip", "So close! You are just 1 away. Count once more, slowly."
    if str(response) == str(right)[::-1] and response != right:
        return "digits_swapped", "You have the right digits, but in the wrong order."
    if abs(diff) % 10 == 0 and s.op in "+−":
        return "tens_slip", "The ones are right. Check the tens again."
    return "other", f"Your answer is {abs(diff)} {'more' if diff > 0 else 'less'} than it should be."


# --- Pictures ----------------------------------------------------------------------------

def _draw(n: int, tens: bool = False) -> str:
    """n as objects: stars, or tens blocks and stars when the numbers are big."""
    if not tens:
        return STAR * n
    return TEN * (n // 10) + STAR * (n % 10)


def _say(n: int, tens: bool = False) -> str:
    """n in words for a screen reader, grouped the same way as the picture."""
    if not tens:
        return f"{n} star{'s' if n != 1 else ''}"
    t, ones = divmod(n, 10)
    parts = ([f"{t} ten{'s' if t != 1 else ''}"] if t else []) + ([f"{ones} one{'s' if ones != 1 else ''}"] if ones else [])
    return " and ".join(parts) or "nothing"


def can_draw(s: Arithmetic) -> bool:
    biggest = max(s.a, s.b, s.result) if s.op != "×" else s.a * s.b
    return 0 < biggest <= MAX_BLOCKS and s.result >= 0


def picture(s: Arithmetic, response: int | None) -> dict:
    """A visual block: rows of objects, each with a spoken alternative."""
    rows = []
    # Use tens blocks when one row would hold more than 20 objects.
    widest = {"+": max(s.a, s.b, s.result), "−": s.a, "×": s.a, "÷": s.result}[s.op]
    big = widest > MAX_STARS

    def draw(n: int) -> str:
        return _draw(n, big)

    def say(n: int) -> str:
        return _say(n, big)

    if s.op == "+":
        # Show their answer as a picture only when it reads clearly as "the second group was wrong".
        if not big and response is not None and s.a <= response <= MAX_STARS and response - s.a != s.b:
            rows.append({"label": "What you wrote", "symbols": f"{draw(s.a)} + {draw(response - s.a)} = {response}",
                         "alt": f"{say(s.a)} plus {say(response - s.a)} makes {response}"})
        rows.append({"label": "The right way", "symbols": f"{draw(s.a)} + {draw(s.b)} = {s.result}",
                     "alt": f"{say(s.a)} plus {say(s.b)} makes {s.result}"})
        tip = f"Count every object in both groups: {s.a} and then {s.b} more makes {s.result}."
    elif s.op == "−":
        rows.append({"label": f"Start with {s.a}", "symbols": draw(s.a), "alt": say(s.a)})
        rows.append({"label": f"Take away {s.b}", "symbols": draw(s.result) + " " + ("❌" * s.b if not big else f"(❌ {s.b})"),
                     "alt": f"cross out {s.b}, and {say(s.result)} are left"})
        tip = f"Cross out {s.b} and count what is left: {s.result}."
    elif s.op == "×":
        for i in range(s.b):
            rows.append({"label": f"Group {i + 1}", "symbols": draw(s.a), "alt": say(s.a)})
        tip = f"{s.b} groups of {s.a} make {s.result}. Count the groups, then count every object."
    else:
        for i in range(s.b):
            rows.append({"label": f"Share {i + 1}", "symbols": draw(s.result), "alt": say(s.result)})
        tip = f"Share {s.a} equally into {s.b} groups. Each group gets {s.result}."
    return {"type": "visual", "rows": rows, "caption": tip}


# --- Stories ----------------------------------------------------------------------------

def story(s: Arithmetic) -> str:
    if s.op == "+":
        return f"You have {s.a} mangoes. Your friend gives you {s.b} more. Now you have {s.a} + {s.b} = {s.result} mangoes."
    if s.op == "−":
        return f"There are {s.a} bananas in a bunch. You share {s.b} with your family. {s.a} − {s.b} = {s.result} bananas are left."
    if s.op == "×":
        return f"There are {s.b} plates with {s.a} appams on each. Altogether that is {s.b} × {s.a} = {s.result} appams."
    return f"{s.a} sweets are shared equally among {s.b} friends. Each friend gets {s.a} ÷ {s.b} = {s.result} sweets."


def smaller(s: Arithmetic) -> Arithmetic:
    """The same idea with friendlier numbers."""
    if s.op == "+":
        return Arithmetic(max(1, s.a // 2), "+", max(1, s.b // 2))
    if s.op == "−":
        b = max(1, s.b // 2)
        return Arithmetic(b + max(1, s.result // 2), "−", b)
    if s.op == "×":
        return Arithmetic(max(2, min(s.a, 5)), "×", 2)
    b = max(2, min(s.b, 3))
    return Arithmetic(b * 2, "÷", b)


def steps_from(solution: str) -> list[str]:
    """Split a written solution into steps: on 'Step n:', '=' chains or sentences."""
    parts = [p.strip(" .") for p in re.split(r"Step \d+:", solution) if p.strip(" .")]
    if len(parts) > 1:
        return parts
    if "=" in solution:
        first, *rest = [p.strip() for p in solution.split("=")]
        return [f"{first}"] + [f"= {p}" for p in rest]
    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", solution) if p.strip()]
    return sentences or ([solution] if solution else [])


def tap_choices(s: Arithmetic | None, answer: str, seed: int, likely_wrong: list[str] | None = None) -> list[str]:
    """Four answers to tap, built from likely mistakes, in an order that is stable per item."""
    try:
        right = int(answer.strip())
    except ValueError:
        return []
    wrongs: list[int] = []
    if s is not None:
        wrongs += [s.a + s.b, abs(s.a - s.b), s.a * s.b]
    wrongs += [int(w) for w in (likely_wrong or []) if w.strip().lstrip("-").isdigit()]
    wrongs += [right + 1, right - 1, right + 10, right - 10, right + 2]
    options = [right]
    for w in wrongs:
        if len(options) == 4:
            break
        if w >= 0 and w not in options:
            options.append(w)
    options.sort()
    shift = seed % len(options)
    return [str(o) for o in options[shift:] + options[:shift]]


# --- Putting a response together ------------------------------------------------------------

@dataclass
class Context:
    """Everything the response needs. Built by the caller from the database."""

    prompt: str
    answer: str
    response: str
    correct: bool
    solution: str = ""
    misconception_tip: str | None = None
    wrong_in_a_row: int = 0  # including this answer
    explanations: dict[str, str] = field(default_factory=dict)  # approved, by style
    support: list[str] = field(default_factory=list)
    tutor_available: bool = False


def choose_answer_mode(ctx: Context, s: Arithmetic | None) -> str:
    """More concrete each time the topic goes wrong in a row."""
    drawable = s is not None and can_draw(s)
    if "small_steps" in ctx.support and drawable:
        ladder = ["count_it_out", "try_similar", "real_life", "step_by_step"]
    elif drawable:
        ladder = ["count_it_out", "step_by_step", "real_life", "try_similar"]
    else:
        ladder = ["step_by_step", "count_it_out", "real_life", "try_similar"]
    mode = ladder[min(max(ctx.wrong_in_a_row, 1), len(ladder)) - 1]
    if mode == "count_it_out" and not drawable and "visual" not in ctx.explanations:
        mode = "real_life"
    return mode


WHY = {
    "count_it_out": "Seeing it with objects often makes a mistake easy to spot.",
    "step_by_step": "Going through it one step at a time shows exactly where it changed.",
    "real_life": "This has been tricky a few times, so here it is as an everyday story.",
    "try_similar": "Several tries have not worked yet, so here is a smaller one with the same idea.",
}

CHEERS = ["Nice work!", "Correct, well done.", "Yes! That's it.", "Great thinking."]


def build(ctx: Context, seed: int = 0) -> dict:
    """The full response to one answer, as blocks the app can show, speak or both."""
    s = parse_arithmetic(ctx.prompt, ctx.answer)
    support = set(ctx.support)

    if ctx.correct:
        headline = "⭐ Correct!" if "focus" in support else CHEERS[seed % len(CHEERS)]
        out = {"correct": True, "mode": None, "headline": headline, "blocks": [], "why": ""}
        return _present(out, support)

    mode = choose_answer_mode(ctx, s)
    blocks: list[dict] = []
    resp = _as_int(ctx.response)

    mistake = None
    if s is not None and resp is not None:
        mistake, words = diagnose(s, resp)
        blocks.append({"type": "text", "text": words})
    elif ctx.misconception_tip:
        blocks.append({"type": "text", "text": ctx.misconception_tip})

    if mode == "count_it_out":
        if s is not None and can_draw(s):
            blocks.append(picture(s, resp))
        else:
            blocks.append({"type": "text", "text": ctx.explanations["visual"]})
    elif mode == "step_by_step":
        steps = steps_from(ctx.solution) if ctx.solution else []
        if not steps and s is not None:
            steps = [f"Read the question: {s.text()}.", f"Work it out: {s.text()} = {s.result}."]
        if not steps and "step_by_step" in ctx.explanations:
            steps = steps_from(ctx.explanations["step_by_step"])
        blocks.append({"type": "steps", "steps": steps})
    elif mode == "real_life":
        text = story(s) if s is not None else ctx.explanations.get("real_world") or ctx.explanations.get("text", "")
        if text:
            blocks.append({"type": "text", "text": text})
        if ctx.solution:
            blocks.append({"type": "text", "text": f"The worked answer: {ctx.solution}"})
    elif mode == "try_similar":
        if s is not None:
            easy = smaller(s)
            if can_draw(easy):
                blocks.append(picture(easy, None))
            # Practice only: not marked or stored, so the answer can travel with it.
            blocks.append({"type": "challenge", "prompt": f"What is {easy.text()}?", "answer": str(easy.result)})
        else:
            blocks.append({"type": "text", "text": "Let's look at the worked answer, then try an easier one next."})
            if ctx.solution:
                blocks.append({"type": "steps", "steps": steps_from(ctx.solution)})

    out = {
        "correct": False,
        "mode": mode,
        "mistake": mistake,
        "headline": "Not quite yet. Let's look at it together.",
        "blocks": [b for b in blocks if b.get("text") or b.get("steps") or b.get("rows") or b.get("prompt")],
        "why": WHY[mode],
        "suggest_tutor": ctx.tutor_available and ctx.wrong_in_a_row >= SUGGEST_TUTOR_AFTER,
    }
    if "focus" in support and s is not None and mode != "try_similar":
        quick = smaller(s)
        out["blocks"].append({"type": "challenge", "prompt": f"Quick challenge: {quick.text()} = ?", "answer": str(quick.result)})
    return _present(out, support)


def _as_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


def _sentences(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]


def _present(out: dict, support: set[str]) -> dict:
    """Apply support modes to the finished response."""
    out["support"] = sorted(support)
    out["one_at_a_time"] = "focus" in support
    out["speak"] = bool(support & {"screen_reader", "easy_read"}) and "visual_first" not in support
    out["show_pictures"] = "screen_reader" not in support

    blocks = []
    for b in out["blocks"]:
        b = dict(b)
        if "easy_read" in support and b["type"] == "text":
            b = {"type": "steps", "steps": _sentences(b["text"]), "plain": True}
        if "screen_reader" in support and b["type"] == "visual":
            # Same meaning, carried in words.
            b = {"type": "steps", "steps": [f"{r['label']}: {r['alt']}." for r in b["rows"]] + [b["caption"]], "plain": True}
        if "focus" in support and b["type"] == "steps":
            b["steps"] = b["steps"][:4]
        blocks.append(b)
    out["blocks"] = blocks

    # A single spoken script, for read-aloud and screen readers.
    spoken = [out["headline"]]
    for b in blocks:
        if b["type"] == "text":
            spoken.append(b["text"])
        elif b["type"] == "steps":
            spoken.extend(b["steps"])
        elif b["type"] == "visual":
            spoken.extend(r["alt"] for r in b["rows"])
            spoken.append(b["caption"])
        elif b["type"] == "challenge":
            spoken.append(b["prompt"])
    out["script"] = " ".join(spoken)
    return out
