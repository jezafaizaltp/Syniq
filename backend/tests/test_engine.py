from datetime import datetime, timedelta

from app.engine import mastery as m
from app.engine.rules import ConceptState, decide, pick_style, target_difficulty

NOW = datetime(2026, 11, 1, 10, 0)


def test_correct_raises_and_wrong_lowers():
    p = 0.5
    assert m.update_p_known(p, m.Evidence(True, "mcq")) > p
    assert m.update_p_known(p, m.Evidence(False, "mcq")) < p


def test_hints_make_a_correct_answer_count_for_less():
    unaided = m.update_p_known(0.4, m.Evidence(True, "mcq", 0))
    with_hints = m.update_p_known(0.4, m.Evidence(True, "mcq", 2))
    assert with_hints < unaided


def test_numeric_correct_is_stronger_evidence_than_mcq():
    assert m.update_p_known(0.4, m.Evidence(True, "numeric")) > m.update_p_known(0.4, m.Evidence(True, "mcq"))


def test_cannot_be_secure_from_too_few_attempts():
    assert not m.is_secure(0.99, 2)
    assert m.is_secure(0.99, 3)


def test_progress_labels_have_no_numbers():
    assert m.progress_label(0.2, 0) == "not_started"
    assert m.progress_label(0.3, 2) == "learning"
    assert m.progress_label(0.7, 2) == "getting_there"
    assert m.progress_label(0.97, 4) == "secure"


def _chapter(**overrides):
    a = ConceptState(concept_id=1, order=0)
    b = ConceptState(concept_id=2, order=1, prereq_ids=[1])
    for cid, fields in overrides.items():
        target = a if cid == "a" else b
        for k, v in fields.items():
            setattr(target, k, v)
    return [a, b], {1: a, 2: b}


def test_new_concept_starts_with_explanation_in_preferred_style():
    chapter, states = _chapter()
    action = decide(chapter, states, NOW, preferred_style="visual")
    assert action.kind == "explain" and action.style == "visual" and action.concept_id == 1


def test_single_wrong_answer_does_not_trigger_format_change():
    chapter, states = _chapter(a={"attempts": 1, "wrong_streak": 1, "styles_seen": ["text"]})
    assert decide(chapter, states, NOW).kind == "practice"


def test_two_wrong_in_a_row_offers_new_format_and_support():
    chapter, states = _chapter(a={"attempts": 2, "wrong_streak": 2, "styles_seen": ["text"]})
    action = decide(chapter, states, NOW)
    assert action.kind == "explain"
    assert action.style != "text"
    assert action.offer_support


def test_prereq_gap_routes_to_weak_prerequisite():
    chapter, states = _chapter(
        a={"p_known": 0.97, "attempts": 5, "styles_seen": ["text"]},
        b={"p_known": 0.3, "attempts": 4, "styles_seen": ["text"]},
    )
    states[1].p_known = 0.5  # prerequisite became weak again
    action = decide(chapter, states, NOW, current_concept_id=2)
    assert action.kind == "prereq_review" and action.concept_id == 1


def test_secure_concept_moves_on_to_next():
    chapter, states = _chapter(a={"p_known": 0.97, "attempts": 4, "styles_seen": ["text"]})
    action = decide(chapter, states, NOW, current_concept_id=1)
    assert action.concept_id == 2


def test_spaced_review_when_due():
    chapter, states = _chapter(
        a={"p_known": 0.97, "attempts": 4, "styles_seen": ["text"], "next_review_at": NOW - timedelta(hours=1)},
        b={"attempts": 1, "styles_seen": ["text"]},
    )
    action = decide(chapter, states, NOW, current_concept_id=2)
    assert action.kind == "review" and action.concept_id == 1


def test_chapter_complete():
    chapter, states = _chapter(
        a={"p_known": 0.97, "attempts": 4}, b={"p_known": 0.97, "attempts": 4}
    )
    assert decide(chapter, states, NOW).kind == "chapter_complete"


def test_difficulty_never_depends_on_speed():
    # target_difficulty only takes mastery; there is no time input to misuse.
    assert [target_difficulty(p) for p in (0.1, 0.5, 0.9)] == [1, 2, 3]


def test_style_choice_prefers_what_has_worked():
    s = ConceptState(
        concept_id=1, order=0,
        styles_seen=["text", "visual", "step_by_step", "real_world"],
        format_stats={"visual": {"after_correct": 5, "after_wrong": 0}, "text": {"after_correct": 0, "after_wrong": 4}},
    )
    assert pick_style(s, None) == "visual"
