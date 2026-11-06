"""Thinking puzzles and own-pace timing, used only to teach each child better.

Short puzzles (patterns, number sequences, odd one out, word links) appear inside
lessons as brain teasers: at the start, then now and then. They are not a test and
give no score. What they are for:

- how SYNiq first explains a new topic, before the child's own answers show what
  works (a strong pattern-and-shape thinker gets the picture first);
- telling parents, in words, which kinds of thinking are growing.

Timing: each answer's time is compared only with the child's own usual pace. A clear
slow-down together with missed answers offers a break. Speed never changes the
level of questions and is never used to judge ability.

What this never does: produce an IQ or any number about the child, rank children,
or run without the parent switching it on (consent scope "thinking_puzzles").

Pure functions, so they can be tested without a database.
"""

import random
import statistics
from dataclasses import dataclass

THINKING_VERSION = "2026.11-1"

DOMAINS = ["pattern", "number", "odd_one_out", "words"]
YOUNG_DOMAINS = ["pattern", "number", "odd_one_out"]  # LKG to Class 2 can't be expected to read word puzzles
START_SET_PER_DOMAIN = 2
PER_DAY = 2  # after the start set: now and then, never a stream
START_PER_DAY = 4
GROWTH_MIN = 4  # answers in a kind of puzzle before parents see anything about it

# Which way of explaining a clear strength points to (engine/methods.py styles).
LEAN = {"pattern": "visual", "odd_one_out": "visual", "number": "step_by_step", "words": "text"}

PATTERN_SETS = [
    ["🔴", "🔵", "🟢", "🟡"],
    ["⭐", "🌙", "☀️", "☁️"],
    ["🍎", "🍌", "🍇", "🍊"],
    ["🐶", "🐱", "🐰", "🐸"],
    ["▲", "■", "●", "◆"],
]
CATEGORIES = {
    "fruit": ["🍎", "🍌", "🍇", "🍓", "🍊", "🍍", "🥭"],
    "animal": ["🐶", "🐱", "🐮", "🐷", "🐸", "🐘", "🐯"],
    "vehicle": ["🚗", "🚌", "🚲", "🚂", "✈️", "🚜", "🛺"],
    "weather": ["☀️", "🌧️", "❄️", "⛅", "🌈", "🌪️"],
    "clothes": ["👕", "👖", "🧦", "👗", "🧢", "🧤"],
}
# (a, b, c, right, distractors): a is to b as c is to right.
WORD_LINKS = {
    1: [
        ("hot", "cold", "up", "down", ["high", "top", "sky"]),
        ("day", "night", "big", "small", ["large", "tall", "huge"]),
        ("cat", "kitten", "dog", "puppy", ["bone", "bark", "calf"]),
        ("bird", "fly", "fish", "swim", ["water", "fin", "walk"]),
        ("hand", "glove", "foot", "sock", ["toe", "leg", "hat"]),
        ("happy", "sad", "fast", "slow", ["quick", "run", "speed"]),
    ],
    2: [
        ("pen", "write", "knife", "cut", ["fork", "sharp", "eat"]),
        ("doctor", "hospital", "teacher", "school", ["book", "student", "class"]),
        ("bee", "hive", "bird", "nest", ["tree", "egg", "fly"]),
        ("cow", "milk", "hen", "egg", ["farm", "chick", "feather"]),
        ("ear", "hear", "eye", "see", ["look", "face", "glasses"]),
        ("summer", "hot", "winter", "cold", ["snow", "season", "warm"]),
    ],
    3: [
        ("author", "book", "composer", "music", ["piano", "song", "orchestra"]),
        ("thermometer", "temperature", "clock", "time", ["hour", "wall", "alarm"]),
        ("seed", "tree", "egg", "bird", ["nest", "shell", "yolk"]),
        ("water", "thirst", "food", "hunger", ["meal", "eat", "kitchen"]),
        ("brick", "wall", "page", "book", ["paper", "write", "letter"]),
        ("caterpillar", "butterfly", "tadpole", "frog", ["pond", "fish", "egg"]),
    ],
}


@dataclass
class Puzzle:
    id: str
    domain: str
    level: int
    prompt: str
    sequence: list[str]  # shown as big tiles; empty for word puzzles
    options: list[str]
    answer: str
    explain: str


def _shuffle(rng: random.Random, right: str, wrong: list[str]) -> list[str]:
    opts = list(dict.fromkeys([right, *[w for w in wrong if w != right]]))[:4]
    rng.shuffle(opts)
    return opts


def make(domain: str, level: int, seed: int) -> Puzzle:
    """The same domain, level and seed always give the same puzzle, so answers are checked without storing puzzles."""
    rng = random.Random(f"{domain}:{level}:{seed}")
    pid = f"{domain}:{level}:{seed}"
    if domain == "pattern":
        symbols = rng.choice(PATTERN_SETS)
        size = {1: 2, 2: 3, 3: 4}[level]
        unit = rng.sample(symbols, size) if level < 3 else [*rng.sample(symbols, 3)]
        if level == 3:
            unit = [unit[0], unit[0], unit[1], unit[2]]  # AABC
        length = len(unit) * 2 + rng.randint(1, len(unit) - 1)
        seq = [unit[i % len(unit)] for i in range(length)]
        right = unit[length % len(unit)]
        return Puzzle(pid, domain, level, "What comes next?", seq, _shuffle(rng, right, symbols), right,
                      f"The pattern repeats {' '.join(unit)}, so {right} comes next.")
    if domain == "number":
        start = rng.randint(1, 9 if level == 1 else 20)
        if level == 1:
            step = rng.choice([1, 2, 5, 10])
            seq = [start + step * i for i in range(4)]
            right, rule = start + step * 4, f"add {step} each time"
        elif level == 2:
            step = rng.choice([3, 4, 6, 7, 9, -3, -2])
            start += 40 if step < 0 else 0
            seq = [start + step * i for i in range(4)]
            right = start + step * 4
            rule = f"add {step} each time" if step > 0 else f"take away {-step} each time"
        else:
            kind = rng.choice(["double", "square", "grow"])
            if kind == "double":
                start = rng.randint(1, 5)
                seq = [start * 2 ** i for i in range(4)]
                right, rule = start * 16, "double each time"
            elif kind == "square":
                k = rng.randint(1, 4)
                seq = [(k + i) ** 2 for i in range(4)]
                right, rule = (k + 4) ** 2, "they are square numbers"
            else:
                a, b = rng.randint(1, 3), rng.randint(1, 3)
                seq, add = [start], a
                for _ in range(3):
                    seq.append(seq[-1] + add)
                    add += b
                right, rule = seq[-1] + add, f"the gap grows by {b} each time"
        wrong = [str(right + d) for d in rng.sample([-2, -1, 1, 2, 3, 10], 3)]
        return Puzzle(pid, domain, level, "What number comes next?", [str(n) for n in seq], _shuffle(rng, str(right), wrong),
                      str(right), f"The rule: {rule}. So the next number is {right}.")
    if domain == "odd_one_out":
        if level < 3:
            a, b = rng.sample(sorted(CATEGORIES), 2)
            same = rng.sample(CATEGORIES[a], 3 if level == 1 else 4)
            odd = rng.choice(CATEGORIES[b])
            tiles = same + [odd]
            rng.shuffle(tiles)
            return Puzzle(pid, domain, level, "Which one doesn't belong?", [], tiles, odd,
                          f"{' '.join(same)} are all {a}; {odd} is not.")
        k = rng.choice([3, 4, 5])
        same = [str(k * n) for n in rng.sample(range(2, 12), 3)]
        odd = str(rng.choice([n for n in range(10, 60) if n % k]))
        tiles = same + [odd]
        rng.shuffle(tiles)
        return Puzzle(pid, domain, level, "Which number doesn't belong?", [], tiles, odd,
                      f"{', '.join(same)} are all in the {k} times table; {odd} is not.")
    if domain == "words":
        a, b, c, right, wrong = rng.choice(WORD_LINKS[level])
        return Puzzle(pid, domain, level, f"{a.capitalize()} goes with {b}. {c.capitalize()} goes with …?", [],
                      _shuffle(rng, right, wrong), right, f"{a.capitalize()} and {b} go together the same way as {c} and {right}.")
    raise ValueError(domain)


def parse_id(pid: str) -> tuple[str, int, int] | None:
    try:
        domain, level, seed = pid.split(":")
        level_i, seed_i = int(level), int(seed)
    except ValueError:
        return None
    if domain not in DOMAINS or level_i not in (1, 2, 3):
        return None
    return domain, level_i, seed_i


@dataclass
class Answer:
    domain: str
    level: int
    correct: bool


def domains_for(grade: int) -> list[str]:
    return YOUNG_DOMAINS if grade <= 2 else DOMAINS


def start_level(grade: int) -> int:
    return 1 if grade <= 5 else 2


def level_for(domain: str, history: list[Answer], grade: int) -> int:
    """Up a level after two right in a row in this kind of puzzle, down one after a miss."""
    mine = [a for a in history if a.domain == domain]
    if not mine:
        return start_level(grade)
    last = mine[-1]
    if not last.correct:
        return max(1, last.level - 1)
    if len(mine) >= 2 and mine[-2].correct and mine[-2].level == last.level:
        return min(3, last.level + 1)
    return last.level


def next_domain(history: list[Answer], grade: int) -> str:
    """The kind of puzzle seen least, so every kind gets a fair look."""
    allowed = domains_for(grade)
    counts = {d: sum(a.domain == d for a in history) for d in allowed}
    return min(allowed, key=lambda d: (counts[d], allowed.index(d)))


def due(history_count: int, today_count: int, grade: int) -> bool:
    start_set = START_SET_PER_DOMAIN * len(domains_for(grade))
    if history_count < start_set:
        return today_count < START_PER_DAY
    return today_count < PER_DAY


def growth(history: list[Answer], grade: int) -> list[dict]:
    """Per kind of puzzle, in words: just_started | steady | growing. The level is relative to the child only."""
    out = []
    for d in domains_for(grade):
        mine = [a for a in history if a.domain == d]
        if len(mine) < GROWTH_MIN:
            out.append({"domain": d, "trend": "just_started"})
            continue
        half = len(mine) // 2
        early = sum(a.level * a.correct for a in mine[:half]) / half
        late = sum(a.level * a.correct for a in mine[half:]) / (len(mine) - half)
        out.append({"domain": d, "trend": "growing" if late - early >= 0.3 else "steady"})
    return out


def lean(history: list[Answer], grade: int) -> str | None:
    """The explanation style a clear puzzle strength points to, or None. Only a starting nudge."""
    scores = {}
    for d in domains_for(grade):
        mine = [a for a in history if a.domain == d][-8:]
        if len(mine) >= GROWTH_MIN:
            scores[d] = sum(a.level * a.correct for a in mine) / len(mine)
    if len(scores) < 2:
        return None
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    if ranked[0][1] - ranked[1][1] < 0.5:
        return None
    return LEAN[ranked[0][0]]


# --- Own pace -------------------------------------------------------------------------

PACE_BASELINE_MIN = 15  # answers before the child's usual pace is known
PACE_RECENT = 4
PACE_SLOWER = 2.0  # times slower than their own usual pace
PACE_MISSES = 2


def pace_break(baseline_ms: list[int], recent: list[tuple[int, bool]]) -> bool:
    """Offer a break when the last few answers were all much slower than this child's own usual
    pace and several were missed. Compared only with the child themselves; never used for levels."""
    if len(baseline_ms) < PACE_BASELINE_MIN or len(recent) < PACE_RECENT:
        return False
    usual = statistics.median(baseline_ms)
    last = recent[-PACE_RECENT:]
    slow = all(ms > PACE_SLOWER * usual for ms, _ in last)
    misses = sum(not ok for _, ok in last)
    return slow and misses >= PACE_MISSES
