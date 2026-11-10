from tests.test_api import client, login  # first: it points the app at a test database

from sqlalchemy import select

from app.db import SessionLocal
from app.engine import methods
from app.engine.methods import Prior
from app.engine.rules import ConceptState, decide
from app.models import Chapter, Concept, Consent, GuardianLink, Item, Mastery, Subject, User
from app.seed import DEMO_PASSWORD
from datetime import datetime


def st(**kw):
    """format_stats from style=(right, wrong) pairs."""
    return {k: {"after_correct": v[0], "after_wrong": v[1]} for k, v in kw.items()}


# --- The pure matcher -------------------------------------------------------------

def test_no_evidence_starts_with_text_as_before():
    assert methods.choose([], {}, None) == ("text", "default")
    assert methods.choose([], {}, Prior()) == ("text", "default")


def test_what_helped_in_other_topics_picks_the_first_explanation():
    prior = Prior(subject=st(visual=(8, 1), text=(2, 6)))
    assert methods.choose([], {}, prior) == ("visual", "history")


def test_the_childs_own_choice_still_wins():
    prior = Prior(subject=st(visual=(8, 1)))
    assert methods.choose([], {}, prior, preferred="real_world") == ("real_world", "preferred")


def test_struggling_always_gets_a_method_not_tried_on_this_topic():
    prior = Prior(subject=st(visual=(9, 0), real_world=(4, 1)))
    style, _ = methods.choose(["visual"], st(visual=(0, 2)), prior)
    assert style == "real_world"


def test_this_topic_outweighs_lots_of_evidence_elsewhere():
    # Visual worked 50 times in other subjects, but not here; text worked here.
    prior = Prior(subject=st(visual=(50, 0)))
    style, why = methods.choose(methods.STYLES, st(text=(2, 0), visual=(0, 2)), prior)
    assert (style, why) == ("text", "this_topic")


def test_similar_learners_count_when_the_child_has_no_history():
    prior = Prior(peers=st(step_by_step=(12, 2)), peers_are_similar=True)
    assert methods.choose([], {}, prior) == ("step_by_step", "similar")
    prior.peers_are_similar = False
    assert methods.choose([], {}, prior) == ("step_by_step", "everyone")


def test_clearest_method_needs_enough_answers_and_a_real_gap():
    assert methods.best_method(st(visual=(2, 0))) is None  # too few answers
    assert methods.best_method(st(visual=(5, 1), text=(5, 1))) is None  # about the same
    assert methods.best_method(st(visual=(6, 0), text=(1, 4))) == "visual"


def test_describe_shows_counts_not_scores():
    out = methods.describe(st(visual=(6, 1), text=(1, 1), real_world=(2, 2)))
    assert out == [
        {"style": "visual", "right_after": 6, "answers_after": 7},
        {"style": "real_world", "right_after": 2, "answers_after": 4},
    ]


def test_rules_introduce_a_new_topic_in_the_method_that_helps():
    s = ConceptState(concept_id=1, order=0, method_prior=Prior(overall=st(real_world=(5, 0))))
    action = decide([s], {1: s}, datetime(2026, 11, 2))
    assert action.rule_id == "R4_introduce" and action.style == "real_world"
    assert action.evidence["method_why"] == "history"


# --- Through the app ------------------------------------------------------------------

def _new_student(db, name, email):
    group_id = db.scalars(select(User.class_group_id).where(User.email == "anu@demo.syniq")).one()
    guardian = db.scalars(select(User).where(User.email == "parent@demo.syniq")).one()
    from app.auth import hash_password

    s = User(name=name, email=email, password_hash=hash_password(DEMO_PASSWORD), role="student", class_group_id=group_id, settings={})
    db.add(s)
    db.flush()
    db.add(GuardianLink(guardian_id=guardian.id, student_id=s.id))
    for scope in ("core_learning", "school_sharing"):
        db.add(Consent(student_id=s.id, guardian_id=guardian.id, scope=scope, granted=True, method="school_form"))
    return s


def _maths_chapters(db):
    sid = db.scalars(select(Subject.id).where(Subject.code == "math")).one()
    practisable = select(Concept.chapter_id).join(Item, Item.concept_id == Concept.id).where(Item.status == "approved")
    return db.scalars(select(Chapter).where(Chapter.subject_id == sid, Chapter.id.in_(practisable)).order_by(Chapter.number)).all()


def test_a_new_chapter_starts_with_what_helped_and_adults_see_it():
    with SessionLocal() as db:
        kiran = _new_student(db, "Kiran", "kiran@demo.syniq")
        first, second = _maths_chapters(db)[:2]
        # Pictures have clearly helped Kiran in an earlier Maths chapter.
        concept = db.scalars(select(Concept).where(Concept.chapter_id == first.id)).first()
        db.add(Mastery(student_id=kiran.id, concept_id=concept.id, p_known=0.9, attempts=8, correct_streak=3, wrong_streak=0,
                       review_count=0, misconceptions={}, format_stats=st(visual=(7, 1), text=(1, 3))))
        db.commit()
        kid, second_id = kiran.id, second.id

    kiran = login("kiran@demo.syniq")
    step = client.post("/learn/next", json={"chapter_id": second_id}, headers=kiran).json()
    assert step["kind"] == "explain"
    assert step["explanation"]["style"] == "visual"

    # The next answers on this topic are credited to that picture by the server, whatever the app says.
    item = client.post("/learn/next", json={"chapter_id": second_id, "current_concept_id": step["concept"]["id"]}, headers=kiran).json()["item"]
    with SessionLocal() as db:
        answer = db.get(Item, item["id"]).answer
    client.post("/learn/attempts", json={"item_id": item["id"], "response": answer, "explanation_style": "text"}, headers=kiran)
    with SessionLocal() as db:
        row = db.scalars(select(Mastery).where(Mastery.student_id == kid, Mastery.concept_id == item["concept_id"])).one()
        assert {k: v for k, v in row.format_stats["visual"].items() if k != "expected"} == st(visual=(1, 0))["visual"]
        # Also how likely a right answer was from what Kiran knew just before, to judge the method fairly.
        assert 0 < row.format_stats["visual"]["expected"] < 1

    mine = client.get("/me/methods", headers=kiran).json()["subjects"]
    assert mine[0]["clearest"] == "visual" and mine[0]["methods"][0]["style"] == "visual"

    parent = login("parent@demo.syniq")
    assert client.get(f"/guardian/children/{kid}/methods", headers=parent).json()["subjects"][0]["clearest"] == "visual"

    teacher = login("teacher@demo.syniq")
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    maths = next(s for s in client.get(f"/teacher/classes/{class_id}/methods", headers=teacher).json() if s["subject"] == mine[0]["subject"])
    visual = next(g for g in maths["groups"] if g["style"] == "visual")
    assert "Kiran" in [s["name"] for s in visual["students"]]
    # Grouped by how they learn, with no marks or scores.
    assert "score" not in str(maths) and "p_known" not in str(maths)


def test_learners_like_you_shape_the_first_explanation():
    with SessionLocal() as db:
        chapters = _maths_chapters(db)
        first, third = chapters[0], chapters[2]
        early = db.scalars(select(Concept).where(Concept.chapter_id == first.id)).first()
        later = db.scalars(select(Concept).where(Concept.chapter_id == third.id).order_by(Concept.order)).first()
        # Two learners whose clearest method is real-life examples; on the new topic, step by step worked for them.
        for i in range(2):
            peer = _new_student(db, f"Peer {i}", f"peer{i}@demo.syniq")
            db.add(Mastery(student_id=peer.id, concept_id=early.id, p_known=0.9, attempts=8, correct_streak=3, wrong_streak=0,
                           review_count=0, misconceptions={}, format_stats=st(real_world=(8, 0), text=(1, 4))))
            db.add(Mastery(student_id=peer.id, concept_id=later.id, p_known=0.9, attempts=6, correct_streak=3, wrong_streak=0,
                           review_count=0, misconceptions={}, format_stats=st(step_by_step=(3, 1), text=(0, 3))))
        # Someone who learns differently: pictures, and pictures on the new topic too.
        other = _new_student(db, "Other", "other@demo.syniq")
        db.add(Mastery(student_id=other.id, concept_id=early.id, p_known=0.9, attempts=8, correct_streak=3, wrong_streak=0,
                       review_count=0, misconceptions={}, format_stats=st(visual=(8, 0), text=(1, 4))))
        db.add(Mastery(student_id=other.id, concept_id=later.id, p_known=0.9, attempts=6, correct_streak=3, wrong_streak=0,
                       review_count=0, misconceptions={}, format_stats=st(visual=(5, 0))))
        me = _new_student(db, "Devi", "devi@demo.syniq")
        db.add(Mastery(student_id=me.id, concept_id=early.id, p_known=0.9, attempts=8, correct_streak=3, wrong_streak=0,
                       review_count=0, misconceptions={}, format_stats=st(real_world=(6, 0), text=(1, 3))))
        db.commit()
        third_id, later_id = third.id, later.id

    from app import learning

    with SessionLocal() as db:
        devi = db.scalars(select(User).where(User.email == "devi@demo.syniq")).one()
        prior = learning.method_priors(db, devi.id, [later_id])[later_id]
        # Only learners who learn like Devi count, and on this topic step by step worked for them.
        assert prior.peers_are_similar and "visual" not in prior.peers
        assert prior.peers["step_by_step"] == {"after_correct": 6, "after_wrong": 2}
        # Devi's own history still comes first; among the rest, what helped similar learners leads.
        assert methods.choose(["real_world"], {}, prior) == ("step_by_step", "similar")


def test_young_children_start_with_the_picture_when_nothing_is_known():
    from app.engine.methods import choose

    assert choose([], None, None)[0] == "text"
    assert choose([], None, None, ties=["visual", "text", "step_by_step", "real_world"])[0] == "visual"
    # Once evidence exists it wins over the starting order.
    stats = {"text": {"after_correct": 5, "after_wrong": 0}}
    assert choose([], stats, None, ties=["visual", "text", "step_by_step", "real_world"])[0] == "text"


def test_methods_are_judged_against_what_was_expected():
    # Same right answers after both, but after text they were expected anyway (the topic was nearly known).
    stats = {
        "visual": {"after_correct": 3, "after_wrong": 1, "expected": 1.2},
        "text": {"after_correct": 3, "after_wrong": 1, "expected": 3.4},
    }
    assert methods.score("visual", stats, None) > 0.5 > methods.score("text", stats, None)
    # Old rows without an expected count keep the old smoothed rate.
    assert methods.score("visual", {"visual": {"after_correct": 3, "after_wrong": 1}}, None) == (3 + 1) / (4 + 2)


def test_learner_saying_it_helped_counts():
    with SessionLocal() as db:
        _new_student(db, "Leena", "leena@demo.syniq")
        db.commit()
        concept_id = db.scalars(select(Concept)).first().id
    leena = login("leena@demo.syniq")
    for _ in range(3):
        r = client.post("/learn/explanation-feedback", json={"concept_id": concept_id, "style": "real_world", "helped": True}, headers=leena)
        assert r.status_code == 200
    client.post("/learn/explanation-feedback", json={"concept_id": concept_id, "style": "text", "helped": False}, headers=leena)
    assert client.post("/learn/explanation-feedback", json={"concept_id": concept_id, "style": "dance", "helped": True}, headers=leena).status_code == 400
    with SessionLocal() as db:
        stats = db.scalars(select(Mastery).where(Mastery.concept_id == concept_id, Mastery.student_id == db.scalars(select(User.id).where(User.email == "leena@demo.syniq")).one())).one().format_stats
    assert stats["real_world"]["felt_yes"] == 3 and stats["text"]["felt_no"] == 1
    assert methods.score("real_world", stats, None) > methods.score("text", stats, None)
