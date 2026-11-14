"""Content rules beyond 'is it correct' (test_content_packs): enough harder questions, hints that don't hand over the
answer, worked solutions, numbers written the Indian way, and language packs written in their own language.

These read the YAML packs only, so they run in seconds.
"""

import re

from app import content_packs as cp
from app.learning import same_answer

PACKS = cp.read_packs()
KERALA9 = {"bio", "chem", "eng", "hin", "it", "mal", "math", "phy", "ss"}


def code_of(pack) -> str:
    return pack["subject"] if isinstance(pack["subject"], str) else pack["subject"]["code"]


def rel(path) -> str:
    return str(path).split("content/", 1)[-1]


def all_items():
    for path, pack in PACKS:
        for concept in pack["concepts"]:
            for item in concept["items"]:
                yield path, pack, concept, item


def test_every_kerala9_topic_has_at_least_two_harder_questions():
    """The Class 9 pilot: a topic is only secure after a harder question (engine/mastery.py), so each needs a few."""
    thin = [
        f"{rel(path)} {c['code']}: {sum(i['difficulty'] == 3 for i in c['items'])}"
        for path, pack in PACKS
        if code_of(pack) in KERALA9 and "demo" not in str(path)
        for c in pack["concepts"]
        if sum(i["difficulty"] == 3 for i in c["items"]) < 2
    ]
    assert not thin, thin


def test_every_kerala9_topic_teaches_first_then_gives_fifteen_questions():
    """The Class 9 pilot: SYNiq teaches a topic (its lesson) before practice, and practice needs enough questions to
    adapt, revisit and spot repeated mistakes without the learner meeting the same few again and again."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if code_of(pack) in KERALA9 and "demo" not in str(path)
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short


def test_every_cbse9_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 9 (2026-27 books) follows the pilot's rule: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse9/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse9/") for _ in pack["concepts"]) >= 131


def test_every_cbse10_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 10 (all six subjects, Hindi A and B) follows the same rule: a lesson before practice, and 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse10/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse10/") for _ in pack["concepts"]) >= 148


def test_every_cbse8_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 8 Maths (Ganita Prakash): a lesson before practice, and at least 15 questions, like Classes 9 and 10."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse8/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse8/maths/") for _ in pack["concepts"]) >= 28


def test_every_cbse8_science_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 8 Science (Curiosity): a lesson before practice, and at least 15 questions, like Maths."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse8/science/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse8/science/") for _ in pack["concepts"]) >= 26


def test_every_cbse8_social_science_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 8 Social Science (Exploring Society): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse8/social-science/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse8/social-science/") for _ in pack["concepts"]) >= 30


def test_every_cbse8_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 8 English (Poorvi): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse8/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse8/english/") for _ in pack["concepts"]) >= 15


def test_every_cbse8_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 8 Hindi (Malhar): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse8/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse8/hindi/") for _ in pack["concepts"]) >= 10



def test_every_cbse7_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 7 Maths (Ganita Prakash, Parts 1 and 2): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse7/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse7/maths/") for _ in pack["concepts"]) >= 30


def test_every_cbse7_science_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 7 Science (Curiosity): a lesson before practice, and at least 15 questions, like Maths."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse7/science/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse7/science/") for _ in pack["concepts"]) >= 24

def test_every_cbse7_social_science_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 7 Social Science (Exploring Society): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse7/social-science/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse7/social-science/") for _ in pack["concepts"]) >= 40

# The answer's words or number appear in these first hints, but they don't give it away: the number is part of the
# question itself, or the hint lists every level or both choices.
FIRST_HINT_MAY_NAME = {
    ("biology/06-classification.yaml", "Class"),
    ("biology/06-classification.yaml", "Family"),
    ("cbse11/biology/13-plant-growth-and-development.yaml", "100"),
    ("cbse11/maths/12-limits-and-derivatives.yaml", "10"),
    ("cbse12/maths/02-inverse-trigonometric-functions.yaml", "30"),
    ("cbse9/maths/11-world-of-algorithms.yaml", "12"),
    ("maths/04-multiplication-identities.yaml", "(y − x)²"),
}


def names_answer(answer: str, text: str) -> bool:
    if re.fullmatch(r"-?\d{2,}", answer):
        return re.search(rf"(?<![\d.,]){answer}(?!\d)", text) is not None
    if len(answer) >= 4 and not re.fullmatch(r"[\d.,/ −-]+", answer):
        return re.search(rf"(?<!\w){re.escape(answer.lower())}(?!\w)", text.lower()) is not None
    return False


def test_first_hint_never_states_the_answer():
    """The first hint points the way. Later hints may come closer, but the first never hands the answer over."""
    found = []
    for path, _, _, item in all_items():
        answer = str(item["answer"]).strip()
        first = str((item.get("hints") or [""])[0])
        if (rel(path), answer) in FIRST_HINT_MAY_NAME or names_answer(answer, str(item["prompt"])):
            continue
        if names_answer(answer, first):
            found.append(f"{rel(path)}: '{answer}' in '{first}'")
    assert not found, found


def test_worked_solutions_say_more_than_the_answer():
    """Maths and science from Class 6 up: the solution shows a reason or step, not just the answer again.
    CBSE Classes 11 and 12 are not yet held to this (see backend/content/README.md, "Who checked it")."""
    short = []
    for path, pack, _, item in all_items():
        code = code_of(pack)
        if not re.search(r"math|sci|phy|chem|bio", code) or re.match(r"cbse(lkg|ukg|[1-5]|11|12)-", code):
            continue
        if len(str(item.get("solution", "")).split()) < 3:
            short.append(f"{rel(path)}: {item['prompt'][:60]}")
    assert not short, short


def test_choices_are_unique_and_the_answer_is_one_of_them():
    for path, _, _, item in all_items():
        options = [str(o) for o in item.get("options") or []]
        if options:
            assert len(set(options)) == len(options), (rel(path), item["prompt"])
            assert str(item["answer"]) in options, (rel(path), item["prompt"])


def test_typed_numbers_accept_indian_and_international_grouping():
    for typed in ("1,00,000", "100,000", "1 00 000", "100000"):
        assert same_answer(typed, "100000"), typed
    assert same_answer("12,345.5", "12345.5")
    assert same_answer("-1,000", "-1000")
    assert not same_answer("2,3", "23")  # a list, not a grouped number
    assert not same_answer("1,00,000", "10000")


def test_language_packs_are_written_in_their_language():
    """Malayalam and Hindi packs: prompts, tips, hints and solutions use their own script (English words in a
    'what is this in English?' question are fine as options)."""
    scripts = {"ml": "[ഀ-ൿ]", "hi": "[ऀ-ॿ]"}
    found = []
    for path, pack in PACKS:
        code = code_of(pack)
        lang = "ml" if code == "mal" or code.endswith("-mal") else "hi" if code == "hin" or re.search(r"-hinb?$", code) else None
        if not lang:
            continue
        script = scripts[lang]
        for tag, tip in (pack.get("tips") or {}).items():
            if not re.search(script, tip):
                found.append(f"{rel(path)} tip {tag}")
        for concept in pack["concepts"]:
            for item in concept["items"]:
                texts = [item["prompt"], *(item.get("hints") or []), item.get("solution", "")]
                for text in texts:
                    if text and re.search(r"[A-Za-z]{4,}", str(text)) and not re.search(script, str(text)):
                        found.append(f"{rel(path)}: {str(text)[:50]}")
    assert not found, found


def test_every_tip_tag_is_defined():
    tags = cp.known_tags() | {t for _, p in PACKS for t in (p.get("tips") or {})}
    missing = {(rel(path), tag) for path, _, _, item in all_items() for tag in (item.get("mistakes") or {}).values() if tag not in tags}
    assert not missing, sorted(missing)


def test_every_kerala9_lesson_step_can_be_explained_another_way():
    """The pilot: every idea in every Kerala Class 9 subject has at least two ways to explain it."""
    one_way = [
        f"{c['code']} step {n}"
        for path, pack in PACKS
        if rel(path).split("/")[0] in ("maths", "physics", "chemistry", "biology", "social-science", "english", "it", "hindi", "malayalam")
        for c in pack["concepts"]
        for n, step in enumerate(c.get("lesson") or [], start=1)
        if not step.get("ways")
    ]
    assert not one_way, one_way
