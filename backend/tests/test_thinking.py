"""Thinking puzzles and own-pace timing: consent first, no scores, used only to teach better."""

from datetime import timedelta

from sqlalchemy import select

from tests.test_api import client, login  # first: points the app at a fresh test database

from app import learning, thinking
from app.db import SessionLocal
from app.models import Attempt, Consent, Item, PuzzleAnswer, User, utcnow
from tests.test_mistake_patterns import new_student


def test_every_puzzle_has_its_answer_among_four_options_and_is_repeatable():
    for domain in thinking.DOMAINS:
        for level in (1, 2, 3):
            for seed in range(60):
                p = thinking.make(domain, level, seed)
                assert p.answer in p.options and len(set(p.options)) == len(p.options) >= 3, p
                assert thinking.make(domain, level, seed) == p
                assert thinking.parse_id(p.id) == (domain, level, seed)


def test_odd_one_out_really_is_the_only_odd_one():
    for seed in range(100):
        p = thinking.make("odd_one_out", 3, seed)
        k = int(p.explain.split("the ")[1].split(" ")[0])
        assert [o for o in p.options if int(o) % k] == [p.answer]


def test_levels_follow_the_child_and_kinds_take_turns():
    A = thinking.Answer
    assert thinking.level_for("number", [A("number", 2, True), A("number", 2, True)], 9) == 3
    assert thinking.level_for("number", [A("number", 2, False)], 9) == 1
    assert thinking.next_domain([A("pattern", 1, True)], 9) == "number"
    assert "words" not in thinking.domains_for(1)  # young children aren't given reading puzzles


def test_a_clear_strength_only_nudges_the_first_explanation():
    A = thinking.Answer
    strong_patterns = [A("pattern", 3, True)] * 4 + [A("number", 1, False)] * 4 + [A("words", 1, True)] * 4
    assert thinking.lean(strong_patterns, 9) == "visual"
    even = [A("pattern", 2, True)] * 4 + [A("number", 2, True)] * 4
    assert thinking.lean(even, 9) is None
    assert thinking.lean([A("pattern", 3, True)] * 4, 9) is None  # one kind alone says nothing


def test_growth_is_words_never_numbers():
    A = thinking.Answer
    g = thinking.growth([A("pattern", 1, False), A("pattern", 1, True), A("pattern", 2, True), A("pattern", 3, True)], 9)
    assert {"domain": "pattern", "trend": "growing"} in g
    assert all(set(k) == {"domain", "trend"} for k in g)


def test_pace_compares_only_with_the_child_and_needs_misses():
    usual = [10_000] * 20
    assert thinking.pace_break(usual, [(30_000, False), (25_000, False), (28_000, True), (40_000, True)])
    assert not thinking.pace_break(usual, [(30_000, True)] * 4)  # slow but right: thinking hard is fine
    assert not thinking.pace_break([60_000] * 20, [(30_000, False)] * 4)  # a slow-and-steady child isn't flagged
    assert not thinking.pace_break(usual[:5], [(30_000, False)] * 4)  # usual pace not known yet


def _consent(sid, granted):
    with SessionLocal() as db:
        guardian = db.scalars(select(User).where(User.email == "parent@demo.syniq")).first()
        db.add(Consent(student_id=sid, guardian_id=guardian.id, scope="thinking_puzzles", granted=granted, method="parent_page"))
        db.commit()


def test_no_puzzles_or_timing_without_the_parents_switch():
    sid = new_student("nopuzzle.tp@demo.syniq")
    _consent(sid, False)
    me = login("nopuzzle.tp@demo.syniq")
    assert client.get("/thinking/puzzle", headers=me).status_code == 204
    assert client.post("/thinking/puzzle", json={"id": "number:1:5", "choice": "1"}, headers=me).status_code == 404
    with SessionLocal() as db:
        assert not learning.pace_break_due(db, db.get(User, sid))


def test_puzzles_inside_lessons_with_consent():
    sid = new_student("puzzle.tp@demo.syniq")
    _consent(sid, True)
    me = login("puzzle.tp@demo.syniq")
    first = client.get("/thinking/puzzle", headers=me).json()
    assert set(first) == {"id", "prompt", "sequence", "options"}  # no domain, level, score or "test"
    right = thinking.make(*thinking.parse_id(first["id"])).answer
    r = client.post("/thinking/puzzle", json={"id": first["id"], "choice": right, "time_ms": 4000}, headers=me).json()
    assert r["correct"] and r["explain"]
    # The start set allows a few a day, then stops: never a stream.
    shown = 1
    while shown < 10:
        nxt = client.get("/thinking/puzzle", headers=me)
        if nxt.status_code == 204:
            break
        client.post("/thinking/puzzle", json={"id": nxt.json()["id"], "choice": "?"}, headers=me)
        shown += 1
    assert shown == thinking.START_PER_DAY
    parent = login("parent@demo.syniq")
    view = client.get(f"/guardian/children/{sid}/thinking", headers=parent).json()
    assert view["on"] and view["puzzles"] == thinking.START_PER_DAY and all(set(k) == {"domain", "trend"} for k in view["kinds"])
    assert client.post("/thinking/puzzle", json={"id": "bogus:9:1", "choice": "x"}, headers=me).status_code == 400


def test_slowing_down_and_missing_offers_a_break_not_easier_questions():
    sid = new_student("pace.tp@demo.syniq")
    _consent(sid, True)
    me = login("pace.tp@demo.syniq")
    with SessionLocal() as db:
        item = db.scalars(select(Item).where(Item.kind == "mcq", Item.status == "approved")).first()
        item_id, concept_id, answer = item.id, item.concept_id, item.answer
        wrong = next(o for o in item.options if o != answer)
        t = utcnow() - timedelta(days=1)
        for i in range(20):  # yesterday: usual pace about 10 seconds
            db.add(Attempt(student_id=sid, item_id=item_id, concept_id=concept_id, response=answer, correct=True, time_ms=10_000,
                           created_at=t + timedelta(minutes=i)))
        now = utcnow() - timedelta(minutes=5)
        for i, ok in enumerate([False, True, False]):  # today: much slower, missing some
            db.add(Attempt(student_id=sid, item_id=item_id, concept_id=concept_id, response=answer if ok else wrong, correct=ok,
                           time_ms=35_000, created_at=now + timedelta(minutes=i)))
        db.commit()
    r = client.post("/learn/attempts", json={"item_id": item_id, "response": wrong, "time_ms": 40_000}, headers=me).json()
    assert r.get("offer_break") is True
    # Offered once, not again straight away.
    r2 = client.post("/learn/attempts", json={"item_id": item_id, "response": wrong, "time_ms": 40_000}, headers=me).json()
    assert "offer_break" not in r2


def test_a_strong_pattern_thinker_gets_the_picture_first():
    from tests.test_api import math_chapter_id

    sid = new_student("visual.tp@demo.syniq")
    _consent(sid, True)
    me = login("visual.tp@demo.syniq")
    with SessionLocal() as db:
        for domain, level, ok in [("pattern", 3, True)] * 4 + [("number", 1, False)] * 4 + [("words", 1, False)] * 4:
            db.add(PuzzleAnswer(student_id=sid, domain=domain, level=level, correct=ok))
        db.commit()
    step = client.post("/learn/next", json={"chapter_id": math_chapter_id(me)}, headers=me).json()
    assert step["kind"] == "explain"
    with SessionLocal() as db:
        from app.models import Decision

        d = db.get(Decision, step["decision_id"])
        # The puzzles put pictures first among ways with no evidence yet; other learners' evidence on the topic still counts.
        assert d.evidence["puzzle_lean"] == "visual"
        if d.evidence.get("method_why") == "default":
            assert step["explanation"]["style"] == "visual"
