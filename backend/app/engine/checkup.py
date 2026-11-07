"""When to show a parent a gentle, label-free note that a free check-up might help.

Owner's choice (2026-11-07): SYNiq never names or guesses a condition. When a
child has kept finding things hard for weeks, even after SYNiq changed how it
teaches, the parent sees one calm note: some children find reading, attention,
numbers, seeing or hearing harder, a free check is available, and SYNiq can't
diagnose anything. The note says nothing about which condition, and the child
never sees it.

The rule, all of it needed:
- at least MIN_ANSWERS answers spread over at least MIN_DAYS days, so it is
  never a bad week or a hard chapter;
- over the last MIN_DAYS days, either fewer than LOW_RATE of answers right
  (SYNiq aims for most answers right, so this means its changes haven't been
  enough), or SYNiq has turned on two or more kinds of help AND the child is
  stuck on STUCK_TOPICS or more topics;
- the parent hasn't hidden the note in the last HIDE_DAYS days.

It never uses answer speed, mood check-ins or puzzles. Pure function, so the
rule can be tested and audited.
"""

from datetime import datetime, timedelta

CHECKUP_VERSION = "2026.11-1"

MIN_ANSWERS = 80
MIN_DAYS = 28
LOW_RATE = 0.5
STUCK_TOPICS = 3
HIDE_DAYS = 180


def show_note(
    answers: list[tuple[datetime, bool]],
    noticed_on: int,
    stuck_topics: int,
    now: datetime,
    hidden_at: datetime | None = None,
) -> bool:
    """answers: (when, right?) for every answer; noticed_on: help SYNiq turned on and still on."""
    if hidden_at and now - hidden_at < timedelta(days=HIDE_DAYS):
        return False
    if len(answers) < MIN_ANSWERS:
        return False
    first = min(when for when, _ in answers)
    if now - first < timedelta(days=MIN_DAYS):
        return False
    recent = [right for when, right in answers if now - when <= timedelta(days=MIN_DAYS)]
    if len(recent) < MIN_ANSWERS // 2:
        return False  # not enough recent practice to say anything
    low = sum(recent) / len(recent) < LOW_RATE
    much_help = noticed_on >= 2 and stuck_topics >= STUCK_TOPICS
    return low or much_help
