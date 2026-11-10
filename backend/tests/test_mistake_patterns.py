"""Mistake patterns, mistakes explained the learner's way, the next step, gentle starts and spot the mistake."""

from datetime import datetime, timedelta

from sqlalchemy import select

from tests.test_api import client, login, math_chapter_id  # first: points the app at a fresh test database

from app import learning
from app.auth import hash_password
from app.db import SessionLocal
from app.engine import patterns, responses
from app.models import Concept, Consent, GuardianLink, Item, Mastery, User
from app.seed import DEMO_PASSWORD

T0 = datetime(2026, 11, 1)


def sight(made=None, correct=False, traps=("square_each_term",), concept=1, minutes=0):
    return patterns.Sighting(concept, list(traps), made, correct, T0 + timedelta(minutes=minutes))


# --- Pure rules -------------------------------------------------------------------------

def test_one_mistake_is_not_a_pattern():
    assert patterns.find([sight("square_each_term")]) == []


def test_repeat_mistake_across_topics_is_a_pattern_until_fixed():
    found = patterns.find([sight("square_each_term", concept=1), sight("square_each_term", concept=2, minutes=1)])
    assert [(p.tag, p.status, p.topics) for p in found] == [("square_each_term", "working_on", [1, 2])]
    later = [sight(correct=True, minutes=i) for i in range(2, 4)]
    assert patterns.find([sight("square_each_term"), sight("square_each_term", minutes=1), *later])[0].status == "working_on"
    fixed = [sight(correct=True, minutes=i) for i in range(2, 5)]
    assert patterns.find([sight("square_each_term"), sight("square_each_term", minutes=1), *fixed])[0].status == "fixed"


def test_falling_in_again_reopens_a_fixed_pattern():
    seq = [sight("square_each_term"), sight("square_each_term", minutes=1)]
    seq += [sight(correct=True, minutes=i) for i in range(2, 5)]
    seq.append(sight("square_each_term", minutes=6))
    p = patterns.find(seq)[0]
    assert p.status == "working_on" and p.times == 3


def test_mistake_explanation_follows_what_helps_this_learner():
    base = ["step_by_step", "count_it_out", "real_life", "try_similar"]
    # No evidence: the usual order.
    assert patterns.mode_order(base, {}, None) == (base, None)
    # The learner learns best from pictures: pictures first.
    order, lead = patterns.mode_order(base, {}, "visual")
    assert order[0] == "count_it_out" and lead == "count_it_out"
    # Their own record after mistakes outweighs that nudge.
    stats = {"real_life": {"helped": 4, "after": 4}, "count_it_out": {"helped": 0, "after": 3}}
    assert patterns.mode_order(base, stats, "visual")[0][0] == "real_life"


def test_wrong_answer_response_starts_with_their_way_and_says_why():
    ctx = responses.Context(
        prompt="Expand (x + 3)².", answer="x² + 6x + 9", response="x² + 9", correct=False,
        solution="x² + 2(x)(3) + 9", explanations={"text": "t", "visual": "v", "real_world": "r", "step_by_step": "a. b."},
        wrong_in_a_row=1, best_method="real_world", known_pattern=True,
    )
    out = responses.build(ctx)
    assert out["mode"] == "real_life" and out["for_you"]
    assert "helped you most" in out["why"]
    assert any("met this trap before" in b.get("text", "") for b in out["blocks"])
    # The next wrong answer in a row tries another way.
    ctx.wrong_in_a_row = 2
    assert responses.build(ctx)["mode"] != "real_life"


def test_answers_to_secure_counts_down():
    assert learning.answers_to_secure(0.2, 0) > learning.answers_to_secure(0.8, 3) >= 1
    assert learning.answers_to_secure(0.99, 5) == 0


# --- Through the app --------------------------------------------------------------------

def new_student(email):
    with SessionLocal() as db:
        anu = db.scalars(select(User).where(User.email == "anu@demo.syniq")).first()
        guardian = db.scalars(select(User).where(User.email == "parent@demo.syniq")).first()
        s = User(name=email.split("@")[0].split(".")[0].title(), email=email, password_hash=hash_password(DEMO_PASSWORD), role="student",
                 class_group_id=anu.class_group_id, settings={})
        db.add(s)
        db.flush()
        db.add(GuardianLink(guardian_id=guardian.id, student_id=s.id))
        for scope in ("core_learning", "mood_checkins", "school_sharing"):
            db.add(Consent(student_id=s.id, guardian_id=guardian.id, scope=scope, granted=True, method="school_form"))
        db.commit()
        return s.id


def items_of(concept_key):
    with SessionLocal() as db:
        concept = db.scalars(select(Concept).where(Concept.code == concept_key)).first()
        return concept.id, db.scalars(select(Item).where(Item.concept_id == concept.id)).all()


def test_practice_picks_the_trap_they_keep_falling_into():
    sid = new_student("meenu.mp@demo.syniq")
    cid, items = items_of("math9.square_of_sum")
    with SessionLocal() as db:
        # "arithmetic" is only in the hardest question, one level above the target: it still comes first.
        picked = learning.pick_item(db, sid, cid, 2, {"arithmetic"})
        assert "arithmetic" in learning.traps_of(picked)
        assert learning.pick_item(db, sid, cid, 1, {"arithmetic"}).difficulty == 1  # two levels away: not forced


def test_repeat_mistake_is_tracked_explained_and_shown_to_everyone():
    sid = new_student("kiran.mp@demo.syniq")
    me = login("kiran.mp@demo.syniq")
    cid, items = items_of("math9.square_of_sum")
    trap = [i for i in items if "x² + 9" in (i.misconceptions or {}) or "a² + 25" in (i.misconceptions or {})]
    first = client.post("/learn/attempts", json={"item_id": trap[0].id, "response": next(w for w, t in trap[0].misconceptions.items() if t == "square_each_term")}, headers=me).json()
    assert "pattern" not in first
    assert first["next_step"]["kind"] == "secure_in" and first["next_step"]["n"] >= 1

    second = client.post("/learn/attempts", json={"item_id": trap[1].id, "response": next(w for w, t in trap[1].misconceptions.items() if t == "square_each_term")}, headers=me).json()
    assert second["pattern"]["times"] == 2
    assert any("met this trap before" in b.get("text", "") for b in second["response"]["blocks"])

    mine = client.get("/me/mistakes", headers=me).json()["patterns"]
    assert mine[0]["tag"] == "square_each_term" and mine[0]["status"] == "working_on" and mine[0]["topics"]

    parent = login("parent@demo.syniq")
    seen = client.get(f"/guardian/children/{sid}/mistakes", headers=parent).json()["patterns"]
    assert seen[0]["tag"] == "square_each_term"

    teacher = login("teacher@demo.syniq")
    class_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    rows = client.get(f"/teacher/classes/{class_id}/mistakes", headers=teacher).json()
    row = next(r for r in rows if r["tag"] == "square_each_term")
    assert "Kiran" in [s["name"] for s in row["working_on"]]

    # After the two misses SYNiq explains again; the practice question after that carries
    # the same trap, says "watch out", and never the answer.
    chapter = math_chapter_id(me)
    step = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": cid}, headers=me).json()
    assert step["kind"] == "explain"
    step = client.post("/learn/next", json={"chapter_id": chapter, "current_concept_id": cid}, headers=me).json()
    assert step["kind"] == "practice" and step["item"]["watch_out"] is True
    with SessionLocal() as db:
        assert "square_each_term" in learning.traps_of(db.get(Item, step["item"]["id"]))
    assert "answer" not in step["item"]


def test_gentle_start_lowers_the_first_questions():
    sid = new_student("devi.mp@demo.syniq")
    cid, _ = items_of("math9.binomial_product")
    with SessionLocal() as db:
        db.add(Mastery(student_id=sid, concept_id=cid, p_known=0.85, attempts=3))
        db.commit()
        student = db.get(User, sid)
        chapter = db.get(Concept, cid).chapter_id
        normal, _ = learning.next_action(db, student, chapter, cid)
        gentle, decision = learning.next_action(db, student, chapter, cid, gentle=True)
    assert normal.kind == "practice" and normal.difficulty == 3
    assert gentle.difficulty == 1 and decision.evidence["gentle_start"] == {"from": 3}


def test_spot_the_mistake_earns_a_star_and_explains():
    new_student("sana.mp@demo.syniq")
    me = login("sana.mp@demo.syniq")
    cid, _ = items_of("math9.square_of_sum")
    spot = client.get(f"/learn/spot?concept_id={cid}", headers=me).json()
    assert spot["their_answer"] in spot["options"] and spot["friend"]
    with SessionLocal() as db:
        right = db.get(Item, spot["item_id"]).answer
    wrong = client.post("/learn/spot", json={"item_id": spot["item_id"], "their_answer": spot["their_answer"], "choice": spot["their_answer"]}, headers=me).json()
    assert wrong["correct"] is False and wrong["stars"] == 0 and wrong["why"]
    good = client.post("/learn/spot", json={"item_id": spot["item_id"], "their_answer": spot["their_answer"], "choice": right}, headers=me).json()
    assert good["correct"] and good["stars"] == 1
    assert client.get("/me/overview", headers=me).json()["stars"] == 1
    # A made-up "friend's answer" is refused.
    bad = client.post("/learn/spot", json={"item_id": spot["item_id"], "their_answer": "nonsense", "choice": right}, headers=me)
    assert bad.status_code == 404


def test_learner_who_learns_from_stories_gets_a_story_after_a_mistake():
    """Simulated learner: right after everyday-story responses, still wrong after step-by-step ones."""
    from app.models import Attempt

    sid = new_student("story.mp@demo.syniq")
    me = login("story.mp@demo.syniq")
    cid, items = items_of("math9.difference_of_squares")
    other_cid, other_items = items_of("math9.binomial_product")
    with SessionLocal() as db:
        t = T0
        for mode, then_right in [("real_life", True), ("step_by_step", False), ("real_life", True), ("step_by_step", False)]:
            for item, right in ((other_items[0], False), (other_items[1], then_right)):
                t += timedelta(minutes=1)
                db.add(Attempt(student_id=sid, item_id=item.id, concept_id=other_cid, response="x", correct=right,
                               feedback_mode=None if right else mode, created_at=t))
        db.commit()
    wrong = next(w for w in items[0].misconceptions)
    r = client.post("/learn/attempts", json={"item_id": items[0].id, "response": wrong}, headers=me).json()
    assert r["response"]["mode"] == "real_life" and r["response"]["for_you"] is True
    assert "helped you most" in r["response"]["why"]


def test_no_question_twice_in_a_sitting_while_others_are_left():
    sid = new_student("ravi.mp@demo.syniq")
    cid, items = items_of("math9.pairs.sum_difference")
    seen = []
    with SessionLocal() as db:
        student = db.get(User, sid)
        for _ in range(len(items)):
            item = learning.pick_item(db, sid, cid, 2)
            seen.append(item.id)
            learning.record_attempt(db, student, item, "zzz", 0, None, None)
    assert len(set(seen)) == len(items)


def test_used_up_topic_waits_while_others_are_open():
    from app.engine.rules import ConceptState, decide

    a, b = ConceptState(concept_id=1, order=0, attempts=4, styles_seen=["text"]), ConceptState(concept_id=2, order=1, attempts=2, styles_seen=["text"])
    states = {1: a, 2: b}
    assert decide([a, b], states, T0, current_concept_id=1, set_aside={1}).concept_id == 2
    # Nothing else left: carry on with it rather than stop.
    assert decide([a, b], states, T0, current_concept_id=1, set_aside={1, 2}).concept_id == 1


def test_due_review_from_another_chapter_comes_into_the_sitting():
    sid = new_student("asha.mp@demo.syniq")
    with SessionLocal() as db:
        chapters = db.scalars(select(Concept.chapter_id).join(Item, Item.concept_id == Concept.id).distinct()).all()
        subject_chapters = {}
        from app.models import Chapter

        for ch in db.scalars(select(Chapter).where(Chapter.id.in_(chapters))).all():
            subject_chapters.setdefault(ch.subject_id, []).append(ch.id)
        subject = next(s for s, chs in subject_chapters.items() if len(chs) >= 2 and db.get(__import__("app.models", fromlist=["Subject"]).Subject, s).syllabus == "kerala_scert")
        first, second = sorted(subject_chapters[subject])[:2]
        old = db.scalars(select(Concept).join(Item, Item.concept_id == Concept.id).where(Concept.chapter_id == first)).first()
        db.add(Mastery(student_id=sid, concept_id=old.id, p_known=0.99, attempts=6, correct_streak=6, wrong_streak=0, review_count=0,
                       misconceptions={}, format_stats={}, secured_at=T0, next_review_at=T0))
        db.commit()
        old_id = old.id
    h = login("asha.mp@demo.syniq")
    step = client.post("/learn/next", json={"chapter_id": second}, headers=h).json()
    if step["kind"] == "explain":  # a new topic starts with its explanation; the review comes with practice
        step = client.post("/learn/next", json={"chapter_id": second, "current_concept_id": step["concept"]["id"]}, headers=h).json()
    assert step["kind"] == "review" and step["concept"]["id"] == old_id
    with SessionLocal() as db:
        answer = db.get(Item, step["item"]["id"]).answer
    client.post("/learn/attempts", json={"item_id": step["item"]["id"], "response": answer}, headers=h)
    # Reviewed once this sitting: back to today's chapter.
    after = client.post("/learn/next", json={"chapter_id": second, "current_concept_id": old_id}, headers=h).json()
    assert after["concept"]["id"] != old_id
