"""Noticing, from a student's answers, which kind of support helps them.

Two kinds of support mode:

- Chosen: screen_reader, visual_first, tap_to_answer. These depend on sight,
  hearing or speech, which answers can't reveal, so a parent (or the student)
  switches them on.
- Noticed: focus, easy_read, small_steps. SYNiq turns these on by itself when
  the pattern in the student's answers is clear, tells the student why, and
  lets them switch it off. Once switched off, SYNiq never turns it back on.

What this module never does:
- name or suggest a condition (ADHD, dyslexia, dyscalculia). It only says
  what seems to help;
- decide from one answer, or from too few answers;
- use how fast the student answered.

Pure functions, so the rules can be tested and audited without a database.
"""

from dataclasses import dataclass, field

from ..i18n import t, translate_english

DETECT_VERSION = "2026.10-1"

CHOSEN = ["screen_reader", "visual_first", "tap_to_answer"]
NOTICED = ["focus", "easy_read", "small_steps"]

MIN_ATTEMPTS = 10  # nothing is noticed before this many answers
LONG_PROMPT_WORDS = 15
BASIC_MISTAKES = {
    "counting_slip", "tens_slip", "one_group_only", "one_group_off",
    "added_instead", "subtracted_instead", "multiplied_instead", "digits_swapped",
}
CONCRETE = {"count_it_out", "try_similar"}
ABSTRACT = {"step_by_step", "real_life"}


def announce(mode: str, reason: str, lang: str = "en") -> str:
    """What the student is told when a mode switches on. reason is the finding's English reason."""
    return t(lang, f"announce.{mode}", reason=translate_english(lang, reason)) + " " + t(lang, "announce.switch_off")


@dataclass
class AttemptRecord:
    correct: bool
    prompt_words: int
    session: int  # attempts more than 30 minutes apart are different sessions
    mistake: str | None = None  # from responses.diagnose, for sums
    after_mode: str | None = None  # the response mode shown just before this answer, if any


@dataclass
class Signals:
    read_aloud_presses: int = 0  # recent, from the student pressing read aloud
    break_presses: int = 0  # recent, from the student pressing "take a break"


@dataclass
class Finding:
    mode: str
    reason: str
    evidence: dict = field(default_factory=dict)


def _rate(xs: list[bool]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def notice_small_steps(attempts: list[AttemptRecord]) -> Finding | None:
    recent = attempts[-20:]
    basic = [a.mistake for a in recent if a.mistake in BASIC_MISTAKES]
    if len(basic) >= 3:
        return Finding("small_steps", t("en", "noticed.small_steps.basic"),
                       {"basic_mistakes": len(basic), "of": len(recent)})
    after_concrete = [a.correct for a in attempts if a.after_mode in CONCRETE]
    after_abstract = [a.correct for a in attempts if a.after_mode in ABSTRACT]
    if len(after_concrete) >= 2 and len(after_abstract) >= 2 and _rate(after_concrete) - _rate(after_abstract) >= 0.4:
        return Finding("small_steps", t("en", "noticed.small_steps.pictures"),
                       {"after_pictures": _rate(after_concrete), "after_words": _rate(after_abstract)})
    return None


def notice_easy_read(attempts: list[AttemptRecord], signals: Signals) -> Finding | None:
    long_ = [a.correct for a in attempts if a.prompt_words >= LONG_PROMPT_WORDS]
    short = [a.correct for a in attempts if a.prompt_words < LONG_PROMPT_WORDS]
    if len(long_) >= 4 and len(short) >= 4 and _rate(short) - _rate(long_) >= 0.3:
        return Finding("easy_read", t("en", "noticed.easy_read.long"),
                       {"short": _rate(short), "long": _rate(long_), "n_long": len(long_)})
    if signals.read_aloud_presses >= 3:
        return Finding("easy_read", t("en", "noticed.easy_read.read_aloud"),
                       {"read_aloud_presses": signals.read_aloud_presses})
    return None


def notice_focus(attempts: list[AttemptRecord], signals: Signals) -> Finding | None:
    sessions: dict[int, list[bool]] = {}
    for a in attempts:
        sessions.setdefault(a.session, []).append(a.correct)
    slipping = 0
    for answers in sessions.values():
        if len(answers) >= 6:
            half = len(answers) // 2
            if _rate(answers[:half]) - _rate(answers[half:]) >= 0.35:
                slipping += 1
    if slipping >= 2:
        return Finding("focus", t("en", "noticed.focus.slipping"),
                       {"sessions_slipping": slipping})
    if signals.break_presses >= 3:
        return Finding("focus", t("en", "noticed.focus.breaks"),
                       {"break_presses": signals.break_presses})
    return None


def notice(attempts: list[AttemptRecord], signals: Signals, already: set[str], switched_off: set[str]) -> list[Finding]:
    """New findings only: never one the student already has or has switched off."""
    if len(attempts) < MIN_ATTEMPTS:
        return []
    found = [notice_focus(attempts, signals), notice_easy_read(attempts, signals), notice_small_steps(attempts)]
    return [f for f in found if f and f.mode not in already and f.mode not in switched_off]


def effective_support(settings: dict | None) -> list[str]:
    """Chosen modes plus noticed ones the student hasn't switched off."""
    s = settings or {}
    chosen = [m for m in s.get("support_modes", []) if m in CHOSEN]
    off = set(s.get("auto_off", []))
    noticed = [m for m in s.get("auto_support", {}) if m in NOTICED and m not in off]
    return chosen + noticed
