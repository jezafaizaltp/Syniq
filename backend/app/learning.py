"""Glue between the database and the pure adaptive engine."""

import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .engine import detect
from .engine import mastery as m
from .engine import responses
from .engine.rules import Action, ConceptState, decide
from .models import Attempt, Concept, ConceptPrereq, Decision, Explanation, Item, LearningEvent, Mastery, User, utcnow


def get_mastery(db: DbSession, student_id: int, concept_id: int) -> Mastery:
    row = db.scalars(
        select(Mastery).where(Mastery.student_id == student_id, Mastery.concept_id == concept_id)
    ).first()
    if row is None:
        row = Mastery(
            student_id=student_id,
            concept_id=concept_id,
            p_known=m.P_INIT,
            attempts=0,
            correct_streak=0,
            wrong_streak=0,
            review_count=0,
            misconceptions={},
            format_stats={},
        )
        db.add(row)
        db.flush()
    return row


def _styles_seen(db: DbSession, student_id: int, concept_id: int) -> list[str]:
    rows = db.scalars(
        select(Decision.evidence).where(
            Decision.student_id == student_id,
            Decision.concept_id == concept_id,
            Decision.action == "explain",
        )
    ).all()
    return sorted({e.get("style") for e in rows if e.get("style")})


def _wrong_since_explanation(db: DbSession, student_id: int, concept_id: int) -> int:
    """Consecutive wrong answers since the last explanation of this concept.

    Counting from the last explanation means a fresh explanation gets a fair
    chance before the engine decides to try yet another approach.
    """
    last_explain = db.scalars(
        select(Decision.created_at)
        .where(Decision.student_id == student_id, Decision.concept_id == concept_id, Decision.action == "explain")
        .order_by(Decision.created_at.desc())
    ).first()
    q = select(Attempt.correct).where(Attempt.student_id == student_id, Attempt.concept_id == concept_id)
    if last_explain:
        q = q.where(Attempt.created_at > last_explain)
    streak = 0
    for correct in db.scalars(q.order_by(Attempt.created_at.desc(), Attempt.id.desc())).all():
        if correct:
            break
        streak += 1
    return streak


def build_states(db: DbSession, student: User, chapter_id: int) -> tuple[list[ConceptState], dict[int, ConceptState]]:
    concepts = db.scalars(select(Concept).where(Concept.chapter_id == chapter_id)).all()
    ids = {c.id for c in concepts}
    prereqs: dict[int, list[int]] = {}
    for link in db.scalars(select(ConceptPrereq).where(ConceptPrereq.concept_id.in_(ids))).all():
        prereqs.setdefault(link.concept_id, []).append(link.prereq_id)
    all_ids = ids | {p for ps in prereqs.values() for p in ps}
    all_concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.id.in_(all_ids))).all()}

    states: dict[int, ConceptState] = {}
    for cid, concept in all_concepts.items():
        row = get_mastery(db, student.id, cid)
        states[cid] = ConceptState(
            concept_id=cid,
            order=concept.order,
            p_known=row.p_known,
            attempts=row.attempts,
            wrong_streak=_wrong_since_explanation(db, student.id, cid),
            next_review_at=row.next_review_at,
            prereq_ids=prereqs.get(cid, []),
            styles_seen=_styles_seen(db, student.id, cid),
            format_stats=row.format_stats or {},
        )
    return [states[c.id] for c in concepts], states


def next_action(db: DbSession, student: User, chapter_id: int, current_concept_id: int | None) -> tuple[Action, Decision]:
    chapter, states = build_states(db, student, chapter_id)
    settings = student.settings or {}
    preferred = settings.get("preferred_style")
    if not preferred and "visual_first" in detect.effective_support(settings):
        preferred = "visual"
    action = decide(chapter, states, utcnow(), current_concept_id, preferred)
    evidence = dict(action.evidence)
    if action.style:
        evidence["style"] = action.style
    decision = Decision(
        student_id=student.id,
        concept_id=action.concept_id,
        rule_id=action.rule_id,
        rule_version=action.version,
        action=action.kind,
        reason=action.reason,
        evidence=evidence,
    )
    db.add(decision)
    db.commit()
    return action, decision


def pick_item(db: DbSession, student_id: int, concept_id: int, difficulty: int | None) -> Item | None:
    """An approved item near the target difficulty, avoiding the most recent ones."""
    items = db.scalars(select(Item).where(Item.concept_id == concept_id, Item.status == "approved")).all()
    if not items:
        return None
    recent = db.scalars(
        select(Attempt.item_id)
        .where(Attempt.student_id == student_id, Attempt.concept_id == concept_id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .limit(max(1, len(items) // 2))
    ).all()
    fresh = [i for i in items if i.id not in recent] or items
    target = difficulty or 1
    best = min(abs(i.difficulty - target) for i in fresh)
    return random.choice([i for i in fresh if abs(i.difficulty - target) == best])


def get_explanation(db: DbSession, concept_id: int, style: str) -> Explanation | None:
    rows = db.scalars(
        select(Explanation).where(Explanation.concept_id == concept_id, Explanation.status == "approved")
    ).all()
    for e in rows:
        if e.style == style:
            return e
    return rows[0] if rows else None


def normalise(answer: str) -> str:
    return "".join(answer.lower().split()).replace("^2", "²").replace("−", "-")


def record_attempt(
    db: DbSession,
    student: User,
    item: Item,
    response: str,
    hints_used: int,
    time_ms: int | None,
    explanation_style: str | None,
) -> tuple[bool, str | None, Mastery]:
    correct = normalise(response) == normalise(item.answer)
    misconception = None if correct else item.misconceptions.get(response)

    db.add(
        Attempt(
            student_id=student.id,
            item_id=item.id,
            concept_id=item.concept_id,
            response=response,
            correct=correct,
            hints_used=hints_used,
            time_ms=time_ms,
            explanation_style=explanation_style,
        )
    )

    row = get_mastery(db, student.id, item.concept_id)
    was_secure = m.is_secure(row.p_known, row.attempts)
    row.p_known = m.update_p_known(row.p_known, m.Evidence(correct, item.kind, hints_used))
    row.attempts += 1
    row.correct_streak = row.correct_streak + 1 if correct else 0
    row.wrong_streak = 0 if correct else row.wrong_streak + 1
    if misconception:
        counts = dict(row.misconceptions or {})
        counts[misconception] = counts.get(misconception, 0) + 1
        row.misconceptions = counts
    if explanation_style:
        stats = {k: dict(v) for k, v in (row.format_stats or {}).items()}
        st = stats.setdefault(explanation_style, {"after_correct": 0, "after_wrong": 0})
        st["after_correct" if correct else "after_wrong"] += 1
        row.format_stats = stats

    now = utcnow()
    if m.is_secure(row.p_known, row.attempts):
        if not was_secure:
            row.secured_at = now
            row.next_review_at = m.next_review(now, 0)
        elif row.next_review_at and row.next_review_at <= now:
            # A review answered: correct pushes the next one further out.
            row.review_count += 1 if correct else 0
            row.next_review_at = m.next_review(now, row.review_count)
    row.updated_at = now
    db.commit()
    return correct, misconception, row


def public_item(item: Item, settings: dict | None = None) -> dict:
    """An item as the student sees it: no answer, no hints until asked."""
    out = {
        "id": item.id,
        "concept_id": item.concept_id,
        "kind": item.kind,
        "prompt": item.prompt,
        "options": item.options,
        "difficulty": item.difficulty,
        "hint_count": len(item.hints),
    }
    if item.kind == "numeric" and "tap_to_answer" in detect.effective_support(settings):
        # Answers to tap instead of type. The right one is among them, so it is not a hint.
        sum_ = responses.parse_arithmetic(item.prompt, item.answer)
        out["choices"] = responses.tap_choices(sum_, item.answer, item.id, list(item.misconceptions))
    return out


# --- Noticing what helps ---------------------------------------------------------------

SESSION_GAP = timedelta(minutes=30)
RECENT = timedelta(days=14)


def attempt_records(db: DbSession, student_id: int, limit: int = 60) -> list[detect.AttemptRecord]:
    """The student's recent answers, oldest first, in the shape the detector reads."""
    attempts = db.scalars(
        select(Attempt).where(Attempt.student_id == student_id).order_by(Attempt.created_at.desc(), Attempt.id.desc()).limit(limit)
    ).all()[::-1]
    items = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_({a.item_id for a in attempts}))).all()}
    records, session, last_time = [], 0, None
    last_mode_by_concept: dict[int, str | None] = {}
    for a in attempts:
        if last_time and a.created_at - last_time > SESSION_GAP:
            session += 1
        last_time = a.created_at
        item = items[a.item_id]
        mistake = None
        sum_ = responses.parse_arithmetic(item.prompt, item.answer)
        if not a.correct and sum_ is not None and a.response.strip().isdigit():
            mistake = responses.diagnose(sum_, int(a.response))[0]
        records.append(
            detect.AttemptRecord(
                correct=a.correct,
                prompt_words=len(item.prompt.split()),
                session=session,
                mistake=mistake,
                after_mode=last_mode_by_concept.get(a.concept_id),
            )
        )
        last_mode_by_concept[a.concept_id] = a.feedback_mode
    return records


def signals(db: DbSession, student_id: int) -> detect.Signals:
    since = utcnow() - RECENT
    kinds = db.scalars(
        select(LearningEvent.kind).where(LearningEvent.student_id == student_id, LearningEvent.created_at >= since)
    ).all()
    return detect.Signals(read_aloud_presses=kinds.count("read_aloud"), break_presses=kinds.count("break"))


def update_noticed_support(db: DbSession, student: User) -> list[detect.Finding]:
    """Switch on any support the student's answers now clearly point to, and log why."""
    settings = dict(student.settings or {})
    noticed = dict(settings.get("auto_support", {}))
    findings = detect.notice(
        attempt_records(db, student.id), signals(db, student.id), set(noticed), set(settings.get("auto_off", []))
    )
    for f in findings:
        noticed[f.mode] = {"reason": f.reason, "since": utcnow().isoformat(timespec="seconds")}
        db.add(
            Decision(
                student_id=student.id,
                concept_id=None,
                rule_id=f"A_{f.mode}",
                rule_version=detect.DETECT_VERSION,
                action="support_on",
                reason=f.reason,
                evidence=f.evidence,
            )
        )
    if findings:
        settings["auto_support"] = noticed
        student.settings = settings
        db.add(student)
        db.commit()
    return findings
