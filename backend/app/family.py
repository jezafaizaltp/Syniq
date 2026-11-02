"""Which part of SYNiq fits each child, from pregnancy to Class 12.

The section comes only from dates and the class a parent enters, never from a test or a label.
"""

from datetime import date

BOARDS = {"cbse": "CBSE", "kerala_scert": "Kerala State (SCERT)"}
GRADES = list(range(-1, 13))  # -1 LKG, 0 UKG, 1..12
RELATIONS = ("mother", "father", "grandparent", "carer")

# What each section is for, in a parent's words. "ready" says whether it can be opened yet.
SECTIONS = {
    "pregnancy": {"title": "Pregnancy", "about": "Calm activities for you, and what to expect month by month.", "ready": False},
    "baby": {"title": "Baby, 0 to 2 years", "about": "Play ideas you do together, milestones, food, sleep and vaccines.", "ready": False},
    "early": {"title": "Healthy screen time, 2 to 4 years", "about": "Slow, calm games with a daily limit you set, and ideas to play away from the screen.", "ready": False},
    "school": {"title": "School, LKG to Class 12", "about": "One-to-one learning that adapts to how your child learns best.", "ready": True},
}


def grade_name(grade: int | None) -> str | None:
    if grade is None:
        return None
    return {-1: "LKG", 0: "UKG"}.get(grade, f"Class {grade}")


def parse_day(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (1 if end.day < start.day else 0)


def section_for(birth_date: str | None, due_date: str | None, grade: int | None, today: date | None = None) -> str:
    today = today or date.today()
    if grade is not None:
        return "school"
    born = parse_day(birth_date)
    if born is None or born > today:
        return "pregnancy" if due_date or born else "school"
    months = months_between(born, today)
    if months < 24:
        return "baby"
    if months < 48:
        return "early"
    return "school"


def age_words(birth_date: str | None, due_date: str | None, today: date | None = None) -> str:
    today = today or date.today()
    born = parse_day(birth_date)
    if born is None or born > today:
        due = parse_day(due_date) or born
        if due is None:
            return ""
        weeks = max(0, (due - today).days // 7)
        return f"Due in about {weeks} weeks" if weeks else "Due any day"
    months = months_between(born, today)
    if months < 1:
        return f"{(today - born).days} days old"
    if months < 24:
        return f"{months} month{'s' if months != 1 else ''} old"
    return f"{months // 12} years old"
