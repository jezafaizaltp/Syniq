"""Glue between the database and the pure adaptive engine."""

import random
from datetime import timedelta
from fractions import Fraction

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from .engine import detect
from .engine import methods
from .engine import patterns
from . import thinking
from .engine import mastery as m
from .engine import responses
from .engine.rules import Action, ConceptState, decide
from .models import Attempt, Chapter, Concept, Subject, ConceptPrereq, Decision, Explanation, Item, LearningEvent, Mastery, User, utcnow


# Pilot students made before family accounts have no class set: they're Kerala State Class 9.
DEFAULT_BOARD, DEFAULT_GRADE = "kerala_scert", 9


def class_of(user: User) -> tuple[str, int]:
    settings = user.settings or {}
    grade = settings.get("grade")
    return settings.get("board") or DEFAULT_BOARD, DEFAULT_GRADE if grade is None else grade


def hindi_course(user: User) -> str:
    """CBSE Hindi Course A (Kshitij, Kritika) or B (Sparsh, Sanchayan). Schools choose one; A unless the student picks B."""
    return "b" if (user.settings or {}).get("hindi_course") == "b" else "a"


def _course_of(code: str) -> str | None:
    if code.endswith("-hinb"):
        return "b"
    return "a" if code.endswith("-hin") else None


def subjects_for(db: DbSession, user: User) -> list[Subject]:
    """Students see their own class and board, and only the Hindi course they take; staff see every subject."""
    query = select(Subject).order_by(Subject.id)
    if user.role != "student":
        return db.scalars(query).all()
    board, grade = class_of(user)
    subjects = db.scalars(query.where(Subject.syllabus == board, Subject.grade == grade)).all()
    if not any(_course_of(s.code) == "b" for s in subjects):
        return subjects
    mine = hindi_course(user)
    return [s for s in subjects if _course_of(s.code) in (None, mine)]


def has_hindi_choice(db: DbSession, user: User) -> bool:
    board, grade = class_of(user)
    return db.scalars(
        select(Subject).where(Subject.syllabus == board, Subject.grade == grade, Subject.code.like("%-hinb"))
    ).first() is not None


def get_mastery(db: DbSession, student_id: int, concept_id: int) -> Mastery:
    query = select(Mastery).where(Mastery.student_id == student_id, Mastery.concept_id == concept_id)
    row = db.scalars(query).first()
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
        try:
            with db.begin_nested():
                db.add(row)
        except IntegrityError:
            # Two requests at once (a double tap) both started this topic; use the row the other made.
            row = db.scalars(query).one()
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
    # Only topics with approved questions can be practised; a topic from the syllabus sheet may have none yet.
    practisable = select(Item.concept_id).where(Item.status == "approved")
    concepts = db.scalars(select(Concept).where(Concept.chapter_id == chapter_id, Concept.id.in_(practisable))).all()
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
    for cid, prior in method_priors(db, student.id, list(states)).items():
        states[cid].method_prior = prior
    return [states[c.id] for c in concepts], states


# --- Which ways of explaining work for this student (engine/methods.py) ----------------

# An explanation gets the credit (or not) for the next few answers on its topic.
CREDIT_WINDOW = 3


def style_to_credit(db: DbSession, student_id: int, concept_id: int) -> str | None:
    """The method last used to explain this topic, if this answer is one of the few right after it."""
    last = db.scalars(
        select(Decision)
        .where(Decision.student_id == student_id, Decision.concept_id == concept_id, Decision.action == "explain")
        .order_by(Decision.created_at.desc(), Decision.id.desc())
    ).first()
    style = (last.evidence or {}).get("style") if last else None
    if not style:
        return None
    since = db.scalars(
        select(Attempt.id).where(Attempt.student_id == student_id, Attempt.concept_id == concept_id, Attempt.created_at >= last.created_at)
    ).all()
    return style if len(since) < CREDIT_WINDOW else None


def subject_of(db: DbSession, concept_ids) -> dict[int, int]:
    rows = db.execute(
        select(Concept.id, Chapter.subject_id).join(Chapter, Chapter.id == Concept.chapter_id).where(Concept.id.in_(list(concept_ids)))
    ).all()
    return {cid: sid for cid, sid in rows}


def method_stats(db: DbSession, student_id: int) -> tuple[dict[int, dict], dict[int, dict], dict]:
    """The student's answers after each method: per topic, per subject, and in total."""
    rows = db.execute(select(Mastery.concept_id, Mastery.format_stats).where(Mastery.student_id == student_id)).all()
    per_topic = {cid: st for cid, st in rows if st}
    subjects = subject_of(db, per_topic)
    per_subject: dict[int, dict] = {}
    overall: dict = {}
    for cid, st in per_topic.items():
        methods.add(per_subject.setdefault(subjects.get(cid), {}), st)
        methods.add(overall, st)
    return per_topic, per_subject, overall


def method_priors(db: DbSession, student_id: int, concept_ids: list[int]) -> dict[int, methods.Prior]:
    """For each topic: what the student's other topics and similar learners say about each method."""
    if not concept_ids:
        return {}
    per_topic, per_subject, overall = method_stats(db, student_id)
    subjects = subject_of(db, concept_ids)
    peer_rows = [
        r
        for r in db.execute(
            select(Mastery.student_id, Mastery.concept_id, Mastery.format_stats).where(
                Mastery.concept_id.in_(concept_ids), Mastery.student_id != student_id
            )
        ).all()
        if r.format_stats
    ]
    # Learners who learn in a similar way: their clearest method is the same as this student's.
    similar: set[int] = set()
    mine = methods.best_method(overall)
    if mine and peer_rows:
        totals: dict[int, dict] = {}
        for sid, st in db.execute(
            select(Mastery.student_id, Mastery.format_stats).where(Mastery.student_id.in_({r.student_id for r in peer_rows}))
        ).all():
            methods.add(totals.setdefault(sid, {}), st)
        similar = {sid for sid, st in totals.items() if methods.best_method(st) == mine}

    out = {}
    for cid in concept_ids:
        own = per_topic.get(cid)
        subject_total = per_subject.get(subjects.get(cid), {})
        on_topic = [r for r in peer_rows if r.concept_id == cid]
        alike = [r for r in on_topic if r.student_id in similar]
        peers: dict = {}
        for r in alike or on_topic:
            methods.add(peers, r.format_stats)
        out[cid] = methods.Prior(
            subject=methods.subtract(subject_total, own),
            overall=methods.subtract(overall, subject_total),
            peers=peers,
            peers_are_similar=bool(alike),
        )
    return out


def next_action(
    db: DbSession, student: User, chapter_id: int, current_concept_id: int | None, gentle: bool = False
) -> tuple[Action, Decision]:
    chapter, states = build_states(db, student, chapter_id)
    settings = student.settings or {}
    preferred = settings.get("preferred_style")
    if not preferred and "visual_first" in detect.effective_support(settings):
        preferred = "visual"
    # LKG to Class 5 see the picture first until their answers show another way works better.
    _, grade = class_of(student)
    ties = ["visual", "text", "step_by_step", "real_world"] if grade <= 5 else None
    # A clear strength in the thinking puzzles (parent's consent) sets which way goes first
    # while the child's own answers don't yet show one. Only a starting nudge.
    puzzle_lean = thinking_lean(db, student, grade)
    if puzzle_lean:
        ties = [puzzle_lean] + [s for s in (ties or methods.STYLES) if s != puzzle_lean]
    action = decide(chapter, states, utcnow(), current_concept_id, preferred, ties)
    evidence = dict(action.evidence)
    if puzzle_lean and action.style:
        evidence["puzzle_lean"] = puzzle_lean
    # The student said they're tired or having a hard time: start this sitting with easier questions.
    if gentle and action.kind in ("practice", "review", "prereq_review") and (action.difficulty or 1) > 1:
        evidence["gentle_start"] = {"from": action.difficulty}
        action.difficulty = 1
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


def pick_item(
    db: DbSession, student_id: int, concept_id: int, difficulty: int | None, working_on: set[str] | None = None
) -> Item | None:
    """An approved item near the target difficulty, avoiding the most recent ones.

    When the student has a mistake pattern this topic can catch, a question with
    that trap comes first (within one level of the target), so the pattern gets
    practised until it is fixed rather than avoided.
    """
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
    if working_on:
        repair = [i for i in fresh if set(traps_of(i)) & working_on and abs(i.difficulty - target) <= 1]
        if repair:
            fresh = repair
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


def same_answer(a: str, b: str) -> bool:
    """Same text, or the same number written another way (2.50 and 2.5, 1/2 and 0.5)."""
    a, b = normalise(a), normalise(b)
    if a == b:
        return True
    try:
        return Fraction(a) == Fraction(b)
    except (ValueError, ZeroDivisionError):
        return False


def record_attempt(
    db: DbSession,
    student: User,
    item: Item,
    response: str,
    hints_used: int,
    time_ms: int | None,
    explanation_style: str | None,
) -> tuple[bool, str | None, Mastery]:
    correct = same_answer(response, item.answer)
    # The server decides which explanation this answer reflects on (the app's value is not trusted for this).
    explanation_style = style_to_credit(db, student.id, item.concept_id)
    misconception = None
    if not correct:
        misconception = next((tag for wrong, tag in item.misconceptions.items() if same_answer(response, wrong)), None)

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


def shuffled_options(item: Item) -> list[str] | None:
    """Choices in a fixed order per question, but not the order they were written in.

    Packs list the right answer first, so showing them as written would teach
    "always tap the first one". Seeding by the item id keeps the order the same
    every time the question comes back."""
    if not item.options:
        return item.options
    options = list(item.options)
    random.Random(f"options-{item.id}").shuffle(options)
    return options


def public_item(item: Item, settings: dict | None = None) -> dict:
    """An item as the student sees it: no answer, no hints until asked."""
    out = {
        "id": item.id,
        "concept_id": item.concept_id,
        "kind": item.kind,
        "prompt": item.prompt,
        "options": shuffled_options(item),
        "difficulty": item.difficulty,
        "hint_count": len(item.hints),
    }
    if item.kind == "numeric":
        # Phone number pads have no "/", so fraction answers get the full keyboard.
        out["keyboard"] = "text" if "/" in item.answer else "decimal"
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


def method_summary(db: DbSession, student_id: int) -> list[dict]:
    """Per subject: how often answers were right after each method, and the clearest one right now (or None)."""
    _, per_subject, _ = method_stats(db, student_id)
    names = {s.id: s.name for s in db.scalars(select(Subject).where(Subject.id.in_([k for k in per_subject if k]))).all()}
    out = []
    for sid, stats in per_subject.items():
        described = methods.describe(stats)
        if sid in names and described:
            out.append({"subject_id": sid, "subject": names[sid], "methods": described, "clearest": methods.best_method(stats)})
    return sorted(out, key=lambda d: d["subject_id"])


# --- Mistake patterns (engine/patterns.py) ------------------------------------------

PATTERN_WINDOW = 500  # the student's most recent answers that patterns are read from

_SUM_TRAPS = {
    "+": ["subtracted_instead", "multiplied_instead", "one_group_only", "counting_slip", "digits_swapped", "tens_slip"],
    "−": ["added_instead", "counting_slip", "digits_swapped", "tens_slip"],
    "×": ["added_instead", "one_group_off", "one_group_only", "counting_slip", "digits_swapped"],
    "÷": ["counting_slip", "digits_swapped"],
}


def traps_of(item: Item) -> list[str]:
    """The mistakes this question can catch: its written misconceptions, or the slips a sum allows."""
    tags = list(dict.fromkeys((item.misconceptions or {}).values()))
    sum_ = responses.parse_arithmetic(item.prompt, item.answer)
    if sum_ is not None:
        tags += [t for t in _SUM_TRAPS.get(sum_.op, []) if t not in tags]
    return tags


def mistake_made(item: Item, response: str) -> str | None:
    """Which known mistake a wrong answer is, if any."""
    tag = next((tag for wrong, tag in (item.misconceptions or {}).items() if same_answer(response, wrong)), None)
    if tag:
        return tag
    sum_ = responses.parse_arithmetic(item.prompt, item.answer)
    if sum_ is not None and response.strip().isdigit():
        found = responses.diagnose(sum_, int(response.strip()))[0]
        return None if found == "other" else found
    return None


def _recent_attempts(db: DbSession, student_id: int) -> tuple[list[Attempt], dict[int, Item]]:
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.student_id == student_id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .limit(PATTERN_WINDOW)
    ).all()[::-1]
    items = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_({a.item_id for a in attempts}))).all()}
    return attempts, items


def mistake_patterns(db: DbSession, student_id: int) -> list[patterns.Pattern]:
    attempts, items = _recent_attempts(db, student_id)
    sightings = []
    for a in attempts:
        item = items.get(a.item_id)
        if not item:
            continue
        traps = traps_of(item)
        made = None if a.correct else mistake_made(item, a.response)
        if traps or made:
            sightings.append(patterns.Sighting(a.concept_id, traps, made, a.correct, a.created_at))
    return patterns.find(sightings)


def mistake_mode_stats(db: DbSession, student_id: int) -> dict:
    """After each response to a wrong answer, was the next answer on that topic right?"""
    attempts, _ = _recent_attempts(db, student_id)
    answers, waiting = [], {}
    for a in attempts:
        if a.concept_id in waiting:
            answers.append(patterns.ModeAnswer(waiting.pop(a.concept_id), a.correct))
        if a.feedback_mode:
            waiting[a.concept_id] = a.feedback_mode
    return patterns.mode_stats(answers)


def best_method_overall(db: DbSession, student: User) -> str | None:
    """The way of explaining that helps this student most, or the one they chose."""
    _, _, overall = method_stats(db, student.id)
    return methods.best_method(overall) or (student.settings or {}).get("preferred_style")


def pattern_text(db: DbSession, lang: str, tag: str) -> str:
    from . import i18n

    for key in (f"pattern.{tag}", f"tip.{tag}"):
        if i18n.has(key):
            return i18n.t(lang, key)
    from .models import Misconception

    row = db.scalars(select(Misconception).where(Misconception.tag == tag)).first()
    return row.tip if row else tag.replace("_", " ")


def pattern_summary(db: DbSession, student_id: int, lang: str = "en") -> list[dict]:
    """Mistakes made more than once: what they are, where, and whether they're fixed. No scores."""
    found = mistake_patterns(db, student_id)
    titles = {c.id: c.title for c in db.scalars(select(Concept).where(Concept.id.in_({t for p in found for t in p.topics}))).all()}
    return [
        {
            "tag": p.tag,
            "text": pattern_text(db, lang, p.tag),
            "status": p.status,
            "times": p.times,
            "topics": [titles[t] for t in p.topics if t in titles],
        }
        for p in found
    ]


# --- The next step ------------------------------------------------------------------

def answers_to_secure(p: float, attempts: int, kind: str = "mcq", cap: int = 9) -> int:
    """Right answers in a row (without hints) that would make this topic secure."""
    n = 0
    while not m.is_secure(p, attempts) and n < cap:
        p = m.update_p_known(p, m.Evidence(True, kind, 0))
        attempts += 1
        n += 1
    return n


def next_step(db: DbSession, student: User, concept_id: int, kind: str = "mcq") -> dict:
    """What the student is working towards now, in a form the app puts into words."""
    concept = db.get(Concept, concept_id)
    row = get_mastery(db, student.id, concept_id)
    if not m.is_secure(row.p_known, row.attempts):
        return {"kind": "secure_in", "n": answers_to_secure(row.p_known, row.attempts, kind), "topic": concept.title}
    practisable = select(Item.concept_id).where(Item.status == "approved")
    later = db.scalars(
        select(Concept).where(Concept.chapter_id == concept.chapter_id, Concept.id.in_(practisable)).order_by(Concept.order)
    ).all()
    for c in later:
        r = db.scalars(select(Mastery).where(Mastery.student_id == student.id, Mastery.concept_id == c.id)).first()
        if not r or not m.is_secure(r.p_known, r.attempts):
            return {"kind": "secured", "topic": concept.title, "next_topic": c.title}
    return {"kind": "secured", "topic": concept.title, "next_topic": None}


def stars(db: DbSession, student_id: int) -> int:
    """Stars from spotting mistakes. A count the student sees; never compared with anyone."""
    return len(db.scalars(select(LearningEvent.id).where(LearningEvent.student_id == student_id, LearningEvent.kind == "spot_star")).all())


# --- Thinking puzzles and own pace (app/thinking.py), only with the parent's consent ------

def thinking_lean(db: DbSession, student: User, grade: int) -> str | None:
    from .auth import has_consent
    from .models import PuzzleAnswer

    if not has_consent(db, student.id, "thinking_puzzles"):
        return None
    rows = db.scalars(select(PuzzleAnswer).where(PuzzleAnswer.student_id == student.id).order_by(PuzzleAnswer.id)).all()
    return thinking.lean([thinking.Answer(r.domain, r.level, r.correct) for r in rows], grade)


PACE_WINDOW = 80


def pace_break_due(db: DbSession, student: User) -> bool:
    """Much slower than the child's own usual pace and missing several: offer a break.
    Not offered again within 20 minutes of a break or an earlier offer."""
    from .auth import has_consent

    if not has_consent(db, student.id, "thinking_puzzles"):
        return False
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.student_id == student.id, Attempt.time_ms.is_not(None))
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .limit(PACE_WINDOW)
    ).all()[::-1]
    if not attempts:
        return False
    # This sitting: answers since the last gap of more than SESSION_GAP.
    start = len(attempts) - 1
    while start > 0 and attempts[start].created_at - attempts[start - 1].created_at <= SESSION_GAP:
        start -= 1
    sitting = attempts[start:]
    baseline = [a.time_ms for a in attempts[: max(0, len(attempts) - thinking.PACE_RECENT)]]
    if not thinking.pace_break(baseline, [(a.time_ms, a.correct) for a in sitting]):
        return False
    since = utcnow() - timedelta(minutes=20)
    recent_break = db.scalars(
        select(LearningEvent.id).where(LearningEvent.student_id == student.id, LearningEvent.kind == "break", LearningEvent.created_at >= since)
    ).first()
    recent_offer = db.scalars(
        select(Decision.id).where(Decision.student_id == student.id, Decision.rule_id == "P_pace_break", Decision.created_at >= since)
    ).first()
    return not recent_break and not recent_offer
