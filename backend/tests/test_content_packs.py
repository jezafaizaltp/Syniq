import copy

from tests.test_api import client, login  # first: it points the app at a test database

from app import content_packs, learning
from app.db import SessionLocal
from app.models import Chapter, Concept, Explanation, Item


def test_every_pack_is_correct():
    """Structure, tips and every answer with a check, worked out again by computer."""
    packs = content_packs.read_packs()
    assert len(packs) >= 4
    assert content_packs.check_all(packs) == []
    numeric = [i for _, p in packs for c in p["concepts"] for i in c["items"] if not i.get("options")]
    assert numeric and all("check" in i for i in numeric)


GOOD_ITEM = {"prompt": "What is 6 × 7?", "answer": "42", "check": "6*7", "difficulty": 1, "hints": ["h"], "solution": "s"}


def problems(**changes):
    item = {**copy.deepcopy(GOOD_ITEM), **changes}
    return content_packs.check_item(item, {"known_tag"})


def test_checker_catches_wrong_content():
    assert problems() == []
    assert "doesn't match the check" in problems(answer="43")[0]
    no_check = {k: v for k, v in GOOD_ITEM.items() if k != "check"}
    assert "needs a 'check'" in content_packs.check_item(no_check, set())[0]
    # A choice question with two right answers, or with the answer missing from its options.
    assert "also correct" in problems(options=["42", "6 × 7", "40", "48"], answer="42")[0]
    assert "not one of the options" in problems(options=["40", "41", "43"], answer="42")[0]
    assert "has no tip" in problems(mistakes={"40": "unknown_tag"})[0]
    assert "different number" in problems(mistakes={"42": "known_tag"})[0]
    # Algebra is compared by value, not by spelling.
    alg = {"prompt": "Expand (x + 1)².", "check": "expand((x + 1)^2)"}
    assert problems(**alg, options=["x² + 2x + 1", "x² + 1", "x² + x + 1"], answer="x² + 2x + 1") == []
    assert "doesn't match" in problems(**alg, options=["x² + 2x + 1", "x² + 1", "x² + x + 1"], answer="x² + 1")[0]
    surd = {"prompt": "Diagonal of a unit square?", "check": "sqrt(1^2 + 1^2)", "options": ["√2", "2", "1"]}
    assert problems(**surd, answer="√2") == []


def test_numbers_written_differently_count_as_right():
    assert learning.same_answer("2.50", "2.5")
    assert learning.same_answer(" 1/2", "0.5")
    assert learning.same_answer("x^2 + 1", "x² + 1")
    assert not learning.same_answer("0.33", "1/3")


def test_packs_are_loaded_and_reloading_changes_nothing():
    with SessionLocal() as db:
        chapter = db.query(Chapter).filter(Chapter.number == 1, Chapter.title == "Pairs of Equations").one()
        concepts = db.query(Concept).filter(Concept.chapter_id == chapter.id).all()
        assert {c.code for c in concepts} >= {"math9.pairs.sum_difference", "math9.pairs.word_problems"}
        items = db.query(Item).filter(Item.source == "pack").all()
        assert items and all(i.status == "approved" and "Claude" in i.review_note for i in items)
        before = len(items)

        counts = content_packs.load(db, content_packs.read_packs())
        assert counts == {"chapters": 0, "concepts": 0, "explanations": 0, "items": 0, "withdrawn": 0}
        assert db.query(Item).filter(Item.source == "pack").count() == before


def test_question_taken_out_of_a_pack_is_withdrawn_and_teacher_content_kept():
    packs = content_packs.read_packs()
    path, pack = next((p, x) for p, x in packs if x["chapter"] == 1)
    pack = copy.deepcopy(pack)
    removed = pack["concepts"][0]["items"].pop()
    with SessionLocal() as db:
        concept = db.query(Concept).filter(Concept.code == pack["concepts"][0]["code"]).one()
        db.add(Explanation(concept_id=concept.id, style="text", body="A teacher's own words.", status="approved", source="teacher"))
        db.commit()
        content_packs.load(db, [(path, pack)])
        gone = db.query(Item).filter(Item.prompt == removed["prompt"]).one()
        assert gone.status == "rejected"
        assert db.query(Explanation).filter(Explanation.body == "A teacher's own words.").one().status == "approved"
        content_packs.load(db, packs)  # put it back
        assert db.query(Item).filter(Item.prompt == removed["prompt"]).one().status == "approved"


def test_students_practise_a_pack_chapter_and_get_its_tips():
    anu = login("anu@demo.syniq")
    subjects = client.get("/subjects", headers=anu).json()
    math = next(s for s in subjects if s["code"] == "math")
    chapters = client.get(f"/subjects/{math['id']}/chapters", headers=anu).json()
    chapter = next(c for c in chapters if c["title"] == "Pairs of Equations")

    step = client.post("/learn/next", json={"chapter_id": chapter["id"]}, headers=anu).json()
    for _ in range(5):
        if step.get("item"):
            break
        step = client.post("/learn/next", json={"chapter_id": chapter["id"], "current_concept_id": step["concept"]["id"]}, headers=anu).json()
    assert step["item"] and "answer" not in step["item"]

    with SessionLocal() as db:
        item = db.query(Item).filter(Item.prompt.like("The sum of two numbers is 34 and their difference is 10. What is the bigger%")).one()
        item_id = item.id
    wrong = client.post("/learn/attempts", json={"item_id": item_id, "response": "44"}, headers=anu).json()
    assert wrong["correct"] is False
    assert wrong["tip"].startswith("That is the total for more than one")
    right = client.post("/learn/attempts", json={"item_id": item_id, "response": "22.0"}, headers=anu).json()
    assert right["correct"] is True


def test_tap_choices_for_negative_and_fraction_answers():
    from app.engine.responses import tap_choices

    negative = tap_choices(None, "-12", 0, ["12"])
    assert "-12" in negative and "12" in negative and sum(c.startswith("-") for c in negative) > 1
    assert sorted(tap_choices(None, "1/2", 0, ["1", "1/4"])) == ["1", "1/2", "1/4"]
    assert tap_choices(None, "3.5", 0, []) == []  # no likely mistakes known: typed instead


def test_every_question_has_planned_mistakes():
    """Every question in every pack names the wrong answers we expect and gives each one a tip."""
    missing = []
    for path, pack in content_packs.read_packs():
        rel = path.relative_to(content_packs.CONTENT_DIR)
        missing += [f"{rel}: {i['prompt'][:50]}" for c in pack["concepts"] for i in c["items"] if not i.get("mistakes")]
    assert missing == []


def test_no_tip_tag_defined_twice_with_different_text():
    """Tags are shared across packs and the first definition wins, so a second, different text would be silently lost."""
    seen: dict[str, tuple[str, str]] = {}
    clashes = []
    for path, pack in content_packs.read_packs():
        rel = str(path.relative_to(content_packs.CONTENT_DIR))
        for tag, tip in (pack.get("tips") or {}).items():
            if tag in seen and seen[tag][1] != tip:
                clashes.append(f"{tag}: {seen[tag][0]} and {rel}")
            seen.setdefault(tag, (rel, tip))
    assert clashes == []


# Tips that name the answer on purpose: a memory trick, a method that works the answer
# out in front of the learner, or a word root they still have to spot. Keep this list short.
TIPS_ALLOWED_TO_NAME_THE_ANSWER = {
    "axis_point_zero", "b11_relative_growth", "c10ss_rabi_kharif", "c11_third_law", "c5_directions",
    "h2_baingani", "m4_minutes_count", "solubility_per_100g", "t7_sun_east",
}


def test_tips_point_the_way_without_stating_the_answer():
    """Mistake principle: a tip shown after a wrong answer must not just hand over the right one."""
    import re

    packs = content_packs.read_packs()
    tips: dict[str, str] = {}
    for _, pack in packs:
        for tag, tip in (pack.get("tips") or {}).items():
            tips.setdefault(tag, tip)
    giveaways = set()
    for path, pack in packs:
        rel = path.relative_to(content_packs.CONTENT_DIR)
        for c in pack["concepts"]:
            for item in c["items"]:
                answer = re.sub(r"\(.*?\)", "", str(item["answer"])).strip().lower()
                for tag in (item.get("mistakes") or {}).values():
                    if tag in TIPS_ALLOWED_TO_NAME_THE_ANSWER:
                        continue
                    tip = tips.get(tag, "").lower()
                    if re.fullmatch(r"\d{2,}", answer):
                        named = re.search(rf"(?<![\d.,]){answer}(?!\d)", tip)
                    elif len(answer) >= 4 and not re.fullmatch(r"[\d.,/ −-]+", answer):
                        named = re.search(rf"(?<!\w){re.escape(answer)}(?!\w)", tip)
                    else:
                        named = None
                    if named:
                        giveaways.add(f"{rel}: {tag} names '{item['answer']}'")
    assert sorted(giveaways) == []
