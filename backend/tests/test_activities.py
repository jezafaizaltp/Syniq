"""Hands-on activities: every CBSE Class 6, 9 and 10 Maths and Science topic and every Kerala Class 9 topic has one,
each can be built and solved, and each says what a wrong try causes, not just "wrong"."""

from tests.test_api import client  # noqa: F401  (must load first: sets up the test database)

import re

from sqlalchemy import select

from app import content_packs
from app.activities import PATTERN_RULES, check_activity, evaluate, fraction_matches, parse_formula
from app.auth import hash_password
from app.db import SessionLocal
from app.models import Chapter, Concept, Consent, Subject, User


def _class6_packs():
    return [p for path, p in content_packs.read_packs() if p["subject"] in ("cbse6-math", "cbse6-sci")]


def test_every_class6_maths_and_science_topic_has_a_working_activity():
    packs = _class6_packs()
    concepts = [c for p in packs for c in p["concepts"]]
    assert len(concepts) == 44
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def test_activities_use_many_kinds_not_one():
    kinds = {c["activity"]["type"] for p in _class6_packs() for c in p["concepts"]}
    assert len(kinds) >= 10


def test_bad_activities_are_caught_in_plain_words():
    assert check_activity({"type": "spin", "prompt": "x"})
    # A target between the steps can never be reached with the buttons.
    assert any("on a step" in e for e in check_activity(
        {"type": "number_line", "prompt": "p", "min": 0, "max": 10, "step": 2, "goals": [{"prompt": "g", "target": 3}]}))
    # No rectangle with sides up to 10 has area 7 and perimeter 10.
    assert any("can't be made" in e for e in check_activity(
        {"type": "rectangle", "prompt": "p", "goals": [{"prompt": "g", "area": 7, "perimeter": 10}]}))
    assert any("bin" in e for e in check_activity(
        {"type": "sort", "prompt": "p", "bins": ["A", "B"], "items": [{"label": str(i), "bin": "C"} for i in range(4)]}))
    assert any("count" in e for e in check_activity(
        {"type": "pattern", "prompt": "p", "rule": "square", "goals": [{"prompt": "g", "count": 20}]}))
    assert any("goals" in e for e in check_activity({"type": "order", "prompt": "p", "steps": ["a", "b", "c"], "goals": []}))


def test_every_goal_can_be_reached():
    for p in _class6_packs():
        for c in p["concepts"]:
            a = c["activity"]
            for g in a.get("goals", []):
                if a["type"] == "pattern":
                    assert g["count"] in [PATTERN_RULES[a["rule"]](n) for n in range(1, a.get("max_step", 8) + 1)]
                if a["type"] == "fraction_bar":
                    assert fraction_matches(g["num"], g["den"], g)
                if a["type"] == "scale" and "zone" in g:
                    assert g["zone"] in {z["label"] for z in a["zones"]}


def _kerala9_concepts():
    return [
        c for _path, p in content_packs.read_packs()
        if p["subject"] in ("math", "phy", "chem", "bio")
        for c in p["concepts"]
    ]


def test_every_kerala_class9_topic_has_a_working_activity():
    concepts = _kerala9_concepts()
    assert len(concepts) == 129
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def _cbse9_concepts():
    return [
        c for _path, p in content_packs.read_packs()
        if p["subject"] in ("cbse9-math", "cbse9-sci")
        for c in p["concepts"]
    ]


def test_every_cbse_class9_maths_and_science_topic_has_a_working_activity():
    concepts = _cbse9_concepts()
    assert len(concepts) == 71  # Ganita Manjari 39, Exploration 32
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def _cbse10_concepts():
    return [
        c for _path, p in content_packs.read_packs()
        if p["subject"] in ("cbse10-math", "cbse10-sci")
        for c in p["concepts"]
    ]


def test_every_cbse_class10_maths_and_science_topic_has_a_working_activity():
    concepts = _cbse10_concepts()
    assert len(concepts) == 52  # Maths 26, Science 26
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def _cbse11_concepts():
    return [
        c for _path, p in content_packs.read_packs()
        if p["subject"] in ("cbse11-math", "cbse11-phy", "cbse11-chem", "cbse11-bio")
        for c in p["concepts"]
    ]


def test_every_cbse_class11_science_topic_has_a_working_activity():
    concepts = _cbse11_concepts()
    assert len(concepts) == 112  # Maths 28, Physics 28, Chemistry 18, Biology 38
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def _cbse12_concepts():
    return [
        c for _path, p in content_packs.read_packs()
        if p["subject"] in ("cbse12-math", "cbse12-phy", "cbse12-chem", "cbse12-bio")
        for c in p["concepts"]
    ]


def test_every_cbse_class12_science_topic_has_a_working_activity():
    concepts = _cbse12_concepts()
    assert len(concepts) == 100  # Maths 26, Physics 28, Chemistry 20, Biology 26
    for c in concepts:
        assert "activity" in c, c["code"]
        assert check_activity(c["activity"]) == [], c["code"]


def _concepts_of(*subjects):
    return [c for _path, p in content_packs.read_packs() if p["subject"] in subjects for c in p["concepts"]]


def test_every_cbse_kg_to_8_maths_and_science_topic_has_a_working_activity():
    for subjects, count in ((("cbse8-math", "cbse8-sci"), 54), (("cbse7-math", "cbse7-sci"), 54), (("cbse5-math", "cbse5-evs"), 50),
                            (("cbse4-math", "cbse4-evs"), 48), (("cbse3-math", "cbse3-evs"), 40),
                            (("cbse2-math",), 22), (("cbse1-math",), 26), (("cbselkg-math", "cbselkg-world"), 14),
                            (("cbseukg-math", "cbseukg-world"), 16)):
        concepts = _concepts_of(*subjects)
        assert len(concepts) == count, subjects  # Class 8: 28 + 26; 7: 30 + 24; 5: 30 + 20; 4: 28 + 20; 3: 28 + 12; LKG: 8 + 6; UKG: 10 + 6
        for c in concepts:
            assert "activity" in c, c["code"]
            assert check_activity(c["activity"]) == [], c["code"]


SS_IT_ENGLISH = (
    (("ss",), 60), (("it",), 30), (("eng",), 25),
    (("cbse10-ss",), 38), (("cbse9-ss",), 32), (("cbse8-ss",), 30), (("cbse7-ss",), 40), (("cbse6-ss",), 28),
    (("cbse9-eng",), 16), (("cbse10-eng",), 26), (("cbse11-eng",), 15), (("cbse12-eng",), 19),
    (("cbse8-eng",), 15), (("cbse7-eng",), 15), (("cbse6-eng",), 16), (("cbse5-eng",), 10), (("cbse4-eng",), 12),
    (("cbse3-eng",), 12), (("cbse2-eng",), 13), (("cbse1-eng",), 9), (("cbselkg-eng",), 8), (("cbseukg-eng",), 8),
)


def test_every_social_science_it_and_english_topic_has_a_working_activity():
    for subjects, count in SS_IT_ENGLISH:
        concepts = _concepts_of(*subjects)
        assert len(concepts) == count, subjects
        for c in concepts:
            assert "activity" in c, c["code"]
            assert check_activity(c["activity"]) == [], c["code"]


def test_every_activity_coaches_a_wrong_try():
    """The mistake principle: every sort item has a clue and a reason, every order says why a step
    can't come earlier, and number activities name the slips children really make."""
    concepts = (
        _kerala9_concepts() + _cbse9_concepts() + _cbse10_concepts() + _cbse11_concepts() + _cbse12_concepts()
        + _concepts_of("cbse8-math", "cbse8-sci", "cbse7-math", "cbse7-sci", "cbse5-math", "cbse5-evs",
                       "cbse4-math", "cbse4-evs", "cbse3-math", "cbse3-evs", "cbse2-math", "cbse1-math",
                       "cbselkg-math", "cbselkg-world", "cbseukg-math", "cbseukg-world")
        + _concepts_of(*(s for subjects, _count in SS_IT_ENGLISH for s in subjects))
        + [c for p in _class6_packs() for c in p["concepts"]]
    )
    numeric = 0
    with_mistakes = 0
    for c in concepts:
        a = c["activity"]
        if a["type"] == "sort":
            for it in a["items"]:
                assert it.get("clue") and it.get("why"), (c["code"], it["label"])
                # A clue may offer a choice ("faster or slower?") but must not just name the answer.
                named = [b for b in a["bins"] if not b.isdigit() and re.search(rf"(?<!\w){re.escape(b)}(?!\w)", it["clue"], re.I)]
                assert named != [it["bin"]], (c["code"], "the clue gives the answer away", it["label"])
        elif a["type"] == "order":
            assert set(a.get("reasons", {})) == set(a["steps"][1:]), c["code"]
        elif a["type"] in ("formula", "number_line", "angle", "graph", "scale", "pattern"):
            numeric += 1
            if any(g.get("mistakes") for g in a.get("goals", [])) or any(z.get("says") for z in a.get("zones", [])):
                with_mistakes += 1
    assert with_mistakes / numeric > 0.8


def test_formulas_are_read_safely_and_correctly():
    assert evaluate(parse_formula("2*x^2-3*x"), {"x": -2}) == 14
    assert round(evaluate(parse_formula("sqrt(a)*sqrt(b)"), {"a": 2, "b": 18}), 9) == 6
    assert evaluate(parse_formula("min(s,36)"), {"s": 40}) == 36
    for bad in ("__import__('os')", "x;y", "open(x)"):
        try:
            parse_formula(bad)
        except (ValueError, IndexError):
            continue
        raise AssertionError(bad)


def _formula(want, mistakes=None, expr="2*x"):
    g = {"prompt": "g", "want": want}
    if mistakes:
        g["mistakes"] = mistakes
    return {"type": "formula", "prompt": "p", "inputs": [{"name": "x", "label": "x", "min": 0, "max": 10, "step": 1}],
            "outputs": [{"name": "y", "label": "y", "expr": expr}], "goals": [g]}


def test_formula_and_graph_goals_are_proved_reachable():
    assert check_activity(_formula({"y": 8})) == []
    assert any("can't be reached" in e for e in check_activity(_formula({"y": 7})))
    assert any("not an input" in e for e in check_activity(_formula({"y": 8}, expr="2*z")))
    line = {"type": "graph", "prompt": "p", "mode": "line", "range": [-6, 6]}
    assert check_activity({**line, "goals": [{"prompt": "g", "through": [[0, 1], [2, 5]]}]}) == []
    assert any("can't be reached" in e for e in check_activity({**line, "goals": [{"prompt": "g", "through": [[0, 0], [3, 1]]}]}))


def test_a_mistake_rule_can_never_call_a_right_answer_wrong():
    # x = 4 is right (2 × 4 = 8); a rule pinning y = 8 would tell a child who got it that they slipped.
    assert any("matches a right answer" in e for e in check_activity(_formula({"y": 8}, [{"when": {"y": 8}, "say": "s"}])))
    assert check_activity(_formula({"y": 8}, [{"when": {"y": [0, 6]}, "say": "too small"}])) == []
    nl = {"type": "number_line", "prompt": "p", "min": 0, "max": 10, "step": 1,
          "goals": [{"prompt": "g", "target": 4, "mistakes": [{"when": {"v": 4}, "say": "s"}]}]}
    assert any("matches the right answer" in e for e in check_activity(nl))
    # Names must be ones the type reports.
    nl["goals"][0]["mistakes"] = [{"when": {"q": 4}, "say": "s"}]
    assert any("it can use v" in e for e in check_activity(nl))


def test_order_reasons_must_belong_to_steps():
    a = {"type": "order", "prompt": "p", "steps": ["a", "b", "c"], "reasons": {"a": "x", "z": "y"}}
    errors = check_activity(a)
    assert any("first step" in e for e in errors) and any("'z'" in e for e in errors)


def test_lesson_offers_the_activity_with_the_topic():
    with SessionLocal() as db:
        kid = User(name="Isha", email="isha@test.syniq", password_hash=hash_password("a-long-password"),
                   role="student", settings={"board": "cbse", "grade": 6, "support_modes": ["calm"]})
        db.add(kid)
        db.flush()
        parent = db.scalars(select(User).where(User.role == "guardian")).first()
        db.add(Consent(student_id=kid.id, guardian_id=parent.id, scope="core_learning", granted=True, method="school_form"))
        subject = db.scalars(select(Subject).where(Subject.code == "cbse6-math")).first()
        chapter = db.scalars(select(Chapter).where(Chapter.subject_id == subject.id, Chapter.number == 7)).first()
        db.commit()
        chapter_id = chapter.id
    token = client.post("/auth/login", json={"email": "isha@test.syniq", "password": "a-long-password"}).json()["token"]
    me = {"Authorization": f"Bearer {token}"}
    step = client.post("/learn/next", json={"chapter_id": chapter_id}, headers=me).json()
    assert step["concept"] and step["activity"]["type"] == "fraction_bar"
    assert client.post("/learn/events", json={"kind": "activity"}, headers=me).status_code == 200
    assert client.post("/learn/events", json={"kind": "score"}, headers=me).status_code == 422


def test_topics_without_an_activity_send_none():
    with SessionLocal() as db:
        c = db.scalars(select(Concept).where(Concept.code.like("mal9.%"))).first()
        assert c.activity is None
