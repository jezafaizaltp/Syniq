"""Content rules beyond 'is it correct' (test_content_packs): enough harder questions, hints that don't hand over the
answer, worked solutions, numbers written the Indian way, and language packs written in their own language.

These read the YAML packs only, so they run in seconds.
"""

import re
import pytest

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

def test_every_cbse7_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 7 English (Poorvi): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse7/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse7/english/") for _ in pack["concepts"]) >= 15

def test_every_cbse7_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 7 Hindi (Malhar): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse7/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse7/hindi/") for _ in pack["concepts"]) >= 10

def test_every_cbse6_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 6 Maths (Ganita Prakash): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse6/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse6/maths/") for _ in pack["concepts"]) >= 20


def test_every_cbse6_science_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 6 Science (Curiosity): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse6/science/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse6/science/") for _ in pack["concepts"]) >= 24


def test_every_cbse6_social_science_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 6 Social Science (Exploring Society: India and Beyond): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse6/social-science/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse6/social-science/") for _ in pack["concepts"]) >= 28


def test_every_cbse6_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 6 English (Poorvi): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse6/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse6/english/") for _ in pack["concepts"]) >= 16


def test_every_cbse6_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 6 Hindi (Malhar): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse6/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse6/hindi/") for _ in pack["concepts"]) >= 13


def test_every_cbse5_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 5 Maths (Maths Mela): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse5/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse5/maths/") for _ in pack["concepts"]) >= 30


def test_every_cbse5_evs_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 5 EVS (Our Wondrous World): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse5/evs/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse5/evs/") for _ in pack["concepts"]) >= 20


def test_every_cbse5_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 5 English (Santoor): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse5/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse5/english/") for _ in pack["concepts"]) >= 10


def test_every_cbse5_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 5 Hindi (Veena): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse5/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse5/hindi/") for _ in pack["concepts"]) >= 12


def test_every_cbse4_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 4 Maths (Maths Mela): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse4/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse4/maths/") for _ in pack["concepts"]) >= 28


def test_every_cbse4_evs_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 4 EVS (Our Wondrous World): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse4/evs/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse4/evs/") for _ in pack["concepts"]) >= 20


def test_every_cbse4_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 4 English (Santoor): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse4/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse4/english/") for _ in pack["concepts"]) >= 12


def test_every_cbse4_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 4 Hindi (Veena): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse4/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse4/hindi/") for _ in pack["concepts"]) >= 13


def test_every_cbse3_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 3 Maths (Maths Mela): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse3/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse3/maths/") for _ in pack["concepts"]) >= 28


def test_every_cbse3_evs_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 3 EVS (Our Wondrous World): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse3/evs/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse3/evs/") for _ in pack["concepts"]) >= 12


def test_every_cbse3_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 3 English (Santoor): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse3/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse3/english/") for _ in pack["concepts"]) >= 12


def test_every_cbse3_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 3 Hindi (Veena): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse3/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse3/hindi/") for _ in pack["concepts"]) >= 18


def test_every_cbse2_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 2 Maths (Joyful Mathematics): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse2/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse2/maths/") for _ in pack["concepts"]) >= 22


def test_every_cbse2_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 2 English (Mridang): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse2/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse2/english/") for _ in pack["concepts"]) >= 13


def test_every_cbse2_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 2 Hindi (Sarangi): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse2/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse2/hindi/") for _ in pack["concepts"]) >= 26


def test_every_cbse1_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 1 Maths (Joyful Mathematics): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse1/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse1/maths/") for _ in pack["concepts"]) >= 26


def test_every_cbse1_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 1 English (Mridang): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse1/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse1/english/") for _ in pack["concepts"]) >= 9


def test_every_cbse1_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE Class 1 Hindi (Sarangi): a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse1/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse1/hindi/") for _ in pack["concepts"]) >= 19


def test_every_cbseukg_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE UKG Maths: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbseukg/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbseukg/maths/") for _ in pack["concepts"]) >= 10


def test_every_cbseukg_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE UKG English: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbseukg/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbseukg/english/") for _ in pack["concepts"]) >= 8


def test_every_cbseukg_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE UKG Hindi: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbseukg/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbseukg/hindi/") for _ in pack["concepts"]) >= 8


def test_every_cbseukg_world_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE UKG My World: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbseukg/world/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbseukg/world/") for _ in pack["concepts"]) >= 6


def test_every_cbselkg_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE LKG Maths: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbselkg/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbselkg/maths/") for _ in pack["concepts"]) >= 8


def test_every_cbselkg_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE LKG English: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbselkg/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbselkg/english/") for _ in pack["concepts"]) >= 8


def test_every_cbselkg_hindi_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE LKG Hindi: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbselkg/hindi/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbselkg/hindi/") for _ in pack["concepts"]) >= 6


def test_every_cbselkg_world_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE LKG My World: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbselkg/world/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbselkg/world/") for _ in pack["concepts"]) >= 6


def test_lesson_checks_do_not_repeat_a_practice_question():
    """A lesson check that is word-for-word a practice question gives the practice answer away."""
    repeats = [
        f"{rel(path)} {c['code']}: {step['check']['prompt']}"
        for path, pack in PACKS
        for c in pack["concepts"]
        for step in c.get("lesson") or []
        if step["check"]["prompt"].strip().lower() in {i["prompt"].strip().lower() for i in c["items"]}
    ]
    assert not repeats, repeats


def test_every_cbse11_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 11 Maths: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse11/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse11/maths/") for _ in pack["concepts"]) >= 28


def test_every_cbse11_physics_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 11 Physics: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse11/physics/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse11/physics/") for _ in pack["concepts"]) >= 28


def test_every_cbse11_chemistry_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 11 Chemistry: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse11/chemistry/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse11/chemistry/") for _ in pack["concepts"]) >= 18


def test_every_cbse11_biology_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 11 Biology: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse11/biology/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse11/biology/") for _ in pack["concepts"]) >= 38


def test_every_cbse11_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 11 English: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse11/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse11/english/") for _ in pack["concepts"]) >= 15


def test_every_cbse12_maths_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 12 Maths: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse12/maths/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse12/maths/") for _ in pack["concepts"]) >= 26


def test_every_cbse12_physics_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 12 Physics: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse12/physics/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse12/physics/") for _ in pack["concepts"]) >= 28


def test_every_cbse12_chemistry_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 12 Chemistry: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse12/chemistry/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse12/chemistry/") for _ in pack["concepts"]) >= 20


def test_every_cbse12_biology_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 12 Biology: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse12/biology/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse12/biology/") for _ in pack["concepts"]) >= 26


def test_every_cbse12_english_topic_teaches_first_then_gives_fifteen_questions():
    """CBSE 12 English: a lesson before practice, and at least 15 questions."""
    short = [
        f"{rel(path)} {c['code']}: lesson={'lesson' in c}, questions={len(c['items'])}"
        for path, pack in PACKS
        if rel(path).startswith("cbse12/english/")
        for c in pack["concepts"]
        if "lesson" not in c or len(c["items"]) < 15
    ]
    assert not short, short
    assert sum(1 for path, pack in PACKS if rel(path).startswith("cbse12/english/") for _ in pack["concepts"]) >= 19


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


def test_every_cbse10_maths_step_has_more_ways_and_every_topic_board_style_questions():
    """Class 10 Maths: every lesson step can be taught at least three ways (one with a picture), and every topic
    has questions in the board-exam formats, including at least one assertion-reason question."""
    thin, no_exam = [], []
    for path, pack in PACKS:
        if not rel(path).startswith("cbse10/maths/"):
            continue
        for c in pack["concepts"]:
            for n, step in enumerate(c.get("lesson") or [], start=1):
                ways = step.get("ways") or []
                pictured = bool(step.get("picture")) or any(w.get("picture") for w in ways)
                if len(ways) < 2 or not pictured:
                    thin.append(f"{c['code']} step {n}")
            styles = {i.get("exam") for i in c["items"]}
            if "assertion_reason" not in styles or len(styles - {None}) < 2:
                no_exam.append(c["code"])
    assert not thin, thin
    assert not no_exam, no_exam


def test_every_kerala9_step_has_more_ways_and_every_topic_exam_style_questions():
    """The Class 9 pilot: every lesson step can be taught at least three ways (the step plus two more, one of them
    with a picture), and every topic has at least one question in a Kerala exam format (one mark, short, case or
    competency; Kerala papers don't use assertion-reason)."""
    thin, no_exam, wrong_style = [], [], []
    for path, pack in PACKS:
        if code_of(pack) not in KERALA9 or "demo" in str(path):
            continue
        for c in pack["concepts"]:
            for n, step in enumerate(c.get("lesson") or [], start=1):
                ways = step.get("ways") or []
                pictured = bool(step.get("picture")) or any(w.get("picture") for w in ways)
                if len(ways) < 2 or not pictured:
                    thin.append(f"{rel(path)} {c['code']} step {n}")
            styles = {i.get("exam") for i in c["items"]} - {None}
            if not styles:
                no_exam.append(f"{rel(path)} {c['code']}")
            if "assertion_reason" in styles:
                wrong_style.append(f"{rel(path)} {c['code']}")
    assert not thin, thin
    assert not no_exam, no_exam
    assert not wrong_style, wrong_style


CBSE9 = {"cbse9-eng", "cbse9-hin", "cbse9-math", "cbse9-sci", "cbse9-ss"}
CBSE10 = {"cbse10-eng", "cbse10-hin", "cbse10-hinb", "cbse10-math", "cbse10-sci", "cbse10-ss"}
CBSE12 = {"cbse12-bio", "cbse12-chem", "cbse12-eng", "cbse12-math", "cbse12-phy"}
CBSE11 = {"cbse11-bio", "cbse11-chem", "cbse11-eng", "cbse11-math", "cbse11-phy"}
CBSE8 = {"cbse8-eng", "cbse8-hin", "cbse8-math", "cbse8-sci", "cbse8-ss"}
CBSE7 = {"cbse7-eng", "cbse7-hin", "cbse7-math", "cbse7-sci", "cbse7-ss"}
CBSE6 = {"cbse6-eng", "cbse6-hin", "cbse6-math", "cbse6-sci", "cbse6-ss"}
CBSE5 = {"cbse5-eng", "cbse5-evs", "cbse5-hin", "cbse5-math"}
CBSE4 = {"cbse4-eng", "cbse4-evs", "cbse4-hin", "cbse4-math"}
CBSE3 = {"cbse3-eng", "cbse3-evs", "cbse3-hin", "cbse3-math"}
CBSE2 = {"cbse2-eng", "cbse2-hin", "cbse2-math"}
CBSE1 = {"cbse1-eng", "cbse1-hin", "cbse1-math"}
CBSEKG = {"cbselkg-eng", "cbselkg-hin", "cbselkg-math", "cbselkg-world", "cbseukg-eng", "cbseukg-hin", "cbseukg-math", "cbseukg-world"}


@pytest.mark.parametrize("subjects", [CBSE9, CBSE10, CBSE11, CBSE12, CBSE8, CBSE7, CBSE6], ids=["cbse9", "cbse10", "cbse11", "cbse12", "cbse8", "cbse7", "cbse6"])
def test_every_step_has_more_ways_and_every_topic_board_style_questions(subjects):
    """CBSE Class 9 (the 2026-27 books), Classes 10, 11, 12, 8, 7 and 6: every lesson step can be taught at least three ways,
    one of them drawn, and every topic has at least one question in a CBSE board format (assertion-reason allowed)."""
    thin, no_exam = [], []
    for path, pack in PACKS:
        if code_of(pack) not in subjects:
            continue
        for c in pack["concepts"]:
            for n, step in enumerate(c.get("lesson") or [], start=1):
                ways = step.get("ways") or []
                pictured = bool(step.get("picture")) or any(w.get("picture") for w in ways)
                if len(ways) < 2 or not pictured:
                    thin.append(f"{rel(path)} {c['code']} step {n}")
            if not {i.get("exam") for i in c["items"]} - {None}:
                no_exam.append(f"{rel(path)} {c['code']}")
    assert not thin, thin
    assert not no_exam, no_exam


@pytest.mark.parametrize("subjects", [CBSE5, CBSE4, CBSE3, CBSE2, CBSE1, CBSEKG], ids=["cbse5", "cbse4", "cbse3", "cbse2", "cbse1", "cbsekg"])
def test_every_primary_step_has_more_ways_and_every_topic_case_and_competency_questions(subjects):
    """CBSE Classes 5 to 1, LKG and UKG: every lesson step can be taught at least three ways, one of them drawn, and every topic has a
    case question and a competency question. Primary classes have no board exam, so no assertion-reason here."""
    thin, missing, wrong_style = [], [], []
    for path, pack in PACKS:
        if code_of(pack) not in subjects:
            continue
        for c in pack["concepts"]:
            for n, step in enumerate(c.get("lesson") or [], start=1):
                ways = step.get("ways") or []
                pictured = bool(step.get("picture")) or any(w.get("picture") for w in ways)
                if len(ways) < 2 or not pictured:
                    thin.append(f"{rel(path)} {c['code']} step {n}")
            styles = {i.get("exam") for i in c["items"]}
            if not {"case", "competency"} <= styles:
                missing.append(f"{rel(path)} {c['code']}")
            if "assertion_reason" in styles:
                wrong_style.append(f"{rel(path)} {c['code']}")
    assert not thin, thin
    assert not missing, missing
    assert not wrong_style, wrong_style


def test_assertion_reason_questions_use_the_standard_choices():
    bad = [
        f"{rel(path)}: {item['prompt'][:50]}"
        for path, _, _, item in all_items()
        if item.get("exam") == "assertion_reason" and item.get("options") != cp.AR_OPTIONS
    ]
    assert not bad, bad


SOLUTIONS_EXPLAINED = (
    "cbse6/", "cbse7/", "cbse8/", "cbse9/", "cbse10/", "cbse11/", "cbse12/",
    "biology/", "chemistry/", "physics/", "maths/", "english/", "hindi/", "it/", "social-science/",
)


def test_class_6_to_12_and_kerala_solutions_show_the_working_or_the_reason():
    """Answers explain themselves: a solution is more than the bare answer (owner asked for a teaching product, not an answer key).
    Covers CBSE 6-12 and the Kerala Class 9 packs except Malayalam; KG-5 keep short answers on purpose."""
    bare = [
        f"{rel(path)}: {str(item['prompt'])[:60]} -> {item.get('solution')!r}"
        for path, pack, concept, item in all_items()
        if rel(path).startswith(SOLUTIONS_EXPLAINED)
        and len(str(item.get("solution", "")).split()) <= 4
    ]
    assert not bare, bare


KERALA_TWO_HINTS = ("biology/", "chemistry/", "physics/", "maths/", "english/", "hindi/", "it/", "social-science/")


def test_every_kerala_question_has_a_second_closer_hint():
    """Kerala Class 9 pilot packs (except Malayalam, which the owner reviews): every question has at least two hints,
    so a stuck learner gets a nudge and then a closer step before any answer is shown. CBSE packs already do."""
    single = [
        f"{rel(path)}: {str(item['prompt'])[:60]}"
        for path, pack, concept, item in all_items()
        if rel(path).startswith(KERALA_TWO_HINTS) and len(item.get("hints") or []) < 2
    ]
    assert not single, single


def answer_stands_out_by_length(options, answer) -> bool:
    """True when the right choice is clearly the longest (30% longer than the next), so a learner could pick it
    without knowing anything. Short choices (all under 25 characters) are left alone."""
    lengths = [len(str(o)) for o in options]
    longest = max(lengths)
    return (longest >= 25 and len(str(answer)) == longest and lengths.count(longest) == 1
            and len(str(answer)) > 1.3 * sorted(lengths)[-2])


# Where the longest choice is right by the nature of the question (the sentence with the most detail) or is a
# proper name that can't be padded.
LONGEST_IS_THE_POINT = (
    "किस वाक्य में सबसे अधिक जानकारी है", "'छिपकली दीवार पर बैठी।'", "Who wrote the poem 'Success'",
    "What does OCR stand for", "Which law protects women from violence at home",
)
NO_LENGTH_GIVEAWAY = KERALA_TWO_HINTS + ("cbselkg/", "cbseukg/", "cbse1/", "cbse2/", "cbse3/", "cbse4/", "cbse5/", "cbse6/", "cbse7/", "cbse8/", "cbse9/", "cbse10/", "cbse11/", "cbse12/")


def test_the_right_choice_does_not_stand_out_by_length():
    """Wrong choices should be as full as the right one, or length alone gives the answer away."""
    stand_out = [f"{rel(path)}: {str(item['prompt'])[:60]}"
                 for path, pack, concept, item in all_items()
                 if rel(path).startswith(NO_LENGTH_GIVEAWAY) and item.get("options") and len(item["options"]) >= 3
                 and not str(item["prompt"]).startswith(LONGEST_IS_THE_POINT)
                 and answer_stands_out_by_length(item["options"], item["answer"])]
    assert not stand_out, stand_out
