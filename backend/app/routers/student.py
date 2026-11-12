import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import ai, i18n, learning, lessons, rewards
from ..auth import current_user, has_consent, require_learning_consent
from ..db import get_db
from ..engine.mastery import is_secure, progress_label
from ..engine import detect, responses
from ..engine.rules import STYLES
from .lab import _day_start as lab_day_start
from ..models import Attempt, Chapter, CheckIn, Concept, Decision, Explanation, Family, FamilyMember, Item, LearningEvent, Mastery, Misconception, Subject, User

router = APIRouter(tags=["student"])

READING_TINTS = ("none", "cream", "blue", "green", "rose")

ALLOWED_SETTINGS = {
    "font_scale": (float, int),
    "high_contrast": bool,
    "dyslexia_font": bool,
    "reduced_motion": bool,
    "read_aloud": bool,
    "extra_time": bool,
    "preferred_style": (str, type(None)),
    "ui_language": str,
    "reading_tint": str,  # none, cream, blue, green, rose: a soft page colour that some readers find easier
    "wide_spacing": bool,  # more space between letters, words and lines
    "support_modes": list,  # chosen: see engine/detect.CHOSEN
    "auto_off": list,  # noticed modes the student has switched off
    "hindi_course": str,  # "a" or "b": which CBSE Hindi course the student's school follows
    "welcome_seen": bool,  # the first-day welcome card has been read
    "more_challenges": bool,  # the learner's own choice: harder questions sooner
}


# --- Curriculum browsing ------------------------------------------------------

def visible_chapters(db: DbSession, user: User, subject_id: int) -> list[Chapter]:
    """Students see only chapters with approved content; staff see every chapter, ready or not."""
    query = select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.number)
    if user.role in ("student", "guardian"):
        ready = (
            select(Concept.chapter_id)
            .join(Item, Item.concept_id == Concept.id)
            .where(Item.status == "approved")
            .union(select(Concept.chapter_id).join(Explanation, Explanation.concept_id == Concept.id).where(Explanation.status == "approved"))
        )
        query = query.where(Chapter.id.in_(ready))
    return db.scalars(query).all()


def next_chapter(db: DbSession, user: User, chapter_id: int) -> dict | None:
    """The next chapter of the same subject that still has topics to learn, for when this one is done."""
    done = db.get(Chapter, chapter_id)
    if not done:
        return None
    for ch in visible_chapters(db, user, done.subject_id):
        if ch.number <= done.number:
            continue
        topics = db.scalars(select(Concept.id).where(Concept.chapter_id == ch.id)).all()
        rows = {r.concept_id: r for r in db.scalars(select(Mastery).where(Mastery.student_id == user.id, Mastery.concept_id.in_(topics)))}
        if any(cid not in rows or not is_secure(rows[cid].p_known, rows[cid].attempts) for cid in topics):
            return {"id": ch.id, "number": ch.number, "title": ch.title}
    return None


@router.get("/subjects")
def list_subjects(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    subjects = learning.subjects_for(db, user)
    out = []
    for s in subjects:
        n = len(visible_chapters(db, user, s.id))
        out.append(
            {"id": s.id, "code": s.code, "name": s.name, "language": s.language, "chapters": n, "grade": s.grade, "syllabus": s.syllabus}
        )
    return out


@router.get("/subjects/{subject_id}/chapters")
def list_chapters(subject_id: int, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    chapters = visible_chapters(db, user, subject_id)
    return [{"id": c.id, "number": c.number, "title": c.title} for c in chapters]


@router.get("/chapters/{chapter_id}")
def chapter_detail(chapter_id: int, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    concepts = db.scalars(select(Concept).where(Concept.chapter_id == chapter_id).order_by(Concept.order)).all()
    result = []
    for c in concepts:
        label = None
        if user.role == "student":
            row = db.scalars(
                select(Mastery).where(Mastery.student_id == user.id, Mastery.concept_id == c.id)
            ).first()
            label = progress_label(row.p_known, row.attempts) if row else "not_started"
        result.append({"id": c.id, "title": c.title, "progress": label})
    return {"id": chapter.id, "title": chapter.title, "concepts": result}


# --- Learning loop -------------------------------------------------------------

class NextRequest(BaseModel):
    chapter_id: int
    current_concept_id: int | None = None
    # The first few steps after the student said they feel low or tired: easier questions first.
    gentle: bool = False


@router.post("/learn/next")
def learn_next(
    body: NextRequest, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent), lang: str = Depends(i18n.language)
):
    if not db.get(Chapter, body.chapter_id):
        raise HTTPException(404, "Chapter not found")
    action, decision = learning.next_action(db, user, body.chapter_id, body.current_concept_id, body.gentle)
    concept = db.get(Concept, action.concept_id) if action.concept_id else None
    payload = {
        "decision_id": decision.id,
        "kind": action.kind,
        "reason": i18n.translate_english(lang, action.reason),
        "concept": {"id": concept.id, "title": concept.title, "signs": concept.sign_videos or []} if concept else None,
        "offer_support": action.offer_support,
        # Something to explore with their hands. Offered with the explanation and any time during practice.
        "activity": concept.activity if concept else None,
        "has_lesson": bool(concept and concept.lesson),
    }
    if action.kind == "chapter_complete":
        payload["next_chapter"] = next_chapter(db, user, body.chapter_id)
    if action.kind == "explain" and concept:
        exp = learning.get_explanation(db, concept.id, action.style or "text")
        payload["explanation"] = {"style": exp.style, "body": exp.body, "picture": exp.picture} if exp else None
        payload["styles"] = STYLES
        why = (decision.evidence or {}).get("method_why")
        if exp and exp.style == action.style and why in ("history", "similar", "everyone"):
            payload["method_why"] = why  # the app says, in the student's words, why this way first
        if action.rule_id == "R4_introduce":
            # A new topic is taught first: the lesson's steps, then this explanation as the sum-up.
            payload["lesson"] = lessons.public_lesson(concept.lesson, concept.id, learning.style_order(db, user, concept.id))
            # Knows some of it already: questions first, teaching only for what they miss.
            payload["lesson_check_first"] = learning.lesson_check_first(db, user, concept.id) if concept.lesson else None
    elif action.kind in ("practice", "review", "prereq_review") and concept:
        working_on = learning.patterns.active(learning.mistake_patterns(db, user.id))
        item = None
        if action.rule_id == "R7_stretch":
            item = learning.pick_stretch_item(db, user.id, concept.id)
        item = item or learning.pick_item(db, user.id, concept.id, action.difficulty, working_on)
        payload["item"] = learning.public_item(item, user.settings) if item else None
        if item and set(learning.traps_of(item)) & working_on and not learning.watch_out_shown_recently(db, user.id):
            # A trap they've fallen into before: a nudge to slow down, never the answer. Not on every
            # question, or it stops being noticed.
            payload["item"]["watch_out"] = True
            decision.evidence = {**(decision.evidence or {}), "watch_out": True}
            db.commit()
    return payload


@router.get("/learn/lesson/{concept_id}")
def lesson(concept_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """The topic's lesson, to go over again at any time."""
    concept = db.get(Concept, concept_id)
    if not concept or not concept.lesson:
        raise HTTPException(404, "No lesson for this topic yet")
    order = learning.style_order(db, user, concept.id)
    return {"concept_id": concept.id, "title": concept.title, "steps": lessons.public_lesson(concept.lesson, concept.id, order)}


class LessonCheck(BaseModel):
    concept_id: int
    step: int = Field(ge=0)
    choice: str = Field(max_length=500)
    # The way of explaining on screen when the learner answered (none: checked before any teaching).
    style: str | None = None
    attempt: int = Field(default=1, ge=1, le=2)
    # The learner asked for another way before answering.
    switched: bool = False
    # A wrong first answer gets another way and one more try before the answer is shown.
    can_retry: bool = False


@router.post("/learn/lesson-check")
def lesson_check(body: LessonCheck, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """A check question inside a lesson: right or not, and why. Not marked: mastery comes from practice.

    It does teach the engine which ways of explaining work for this learner: a wrong answer just after a way
    counts against it, a right answer after another way (offered or asked for) counts for that one."""
    concept = db.get(Concept, body.concept_id)
    if not concept or not concept.lesson:
        raise HTTPException(404, "No lesson for this topic yet")
    try:
        result = lessons.mark(concept.lesson, body.step, body.choice)
    except IndexError:
        raise HTTPException(404, "No such step") from None
    style = body.style if body.style in lessons.way_styles(concept.lesson, body.step) else None
    if style and user.role == "student":
        if body.attempt == 1 and not result["right"]:
            learning.record_felt(db, user, concept.id, style, helped=False)
        elif result["right"] and (body.attempt == 2 or body.switched):
            learning.record_felt(db, user, concept.id, style, helped=True)
    kind = "lesson_right" if result["right"] else "lesson_wrong"
    db.add(LearningEvent(student_id=user.id, kind=kind, detail=f"{concept.id}:{body.step}:{style or '-'}:{body.attempt}"))
    db.commit()
    if not result["right"] and body.can_retry and body.attempt == 1:
        return {"right": False, "retry": True}
    return result


class LessonDone(BaseModel):
    concept_id: int
    steps: int = Field(ge=0, le=20)
    first_time: int = Field(ge=0, le=20)
    check_first: bool = False


@router.post("/learn/lesson-done")
def lesson_done(body: LessonDone, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """A lesson finished: kept so the learner's mentor can say what they've done this week."""
    concept = db.get(Concept, body.concept_id)
    if not concept or not concept.lesson:
        raise HTTPException(404, "No lesson for this topic yet")
    mode = "check_first" if body.check_first else "taught"
    db.add(LearningEvent(student_id=user.id, kind="lesson_done", detail=f"{concept.id}:{min(body.first_time, body.steps)}/{body.steps}:{mode}"))
    db.commit()
    return {"ok": True}


@router.get("/concepts/{concept_id}/explanations/{style}")
def explanation(concept_id: int, style: str, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    """The student can ask for any explanation style at any time."""
    if style not in STYLES:
        raise HTTPException(400, "Unknown style")
    exp = learning.get_explanation(db, concept_id, style)
    if not exp:
        raise HTTPException(404, "No approved explanation yet")
    if user.role == "student":
        db.add(
            Decision(
                student_id=user.id,
                concept_id=concept_id,
                rule_id="student_choice",
                rule_version="-",
                action="explain",
                reason="The student asked for this explanation style.",
                evidence={"style": exp.style},
            )
        )
        db.commit()
    return {"style": exp.style, "body": exp.body, "picture": exp.picture}


@router.get("/items/{item_id}/hints/{n}")
def hint(item_id: int, n: int, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    item = db.get(Item, item_id)
    if not item or item.status != "approved":
        raise HTTPException(404, "Item not found")
    if n < 1 or n > len(item.hints):
        raise HTTPException(404, "No more hints")
    return {"n": n, "hint": item.hints[n - 1], "remaining": len(item.hints) - n}


class AttemptIn(BaseModel):
    item_id: int
    response: str = Field(max_length=200)
    hints_used: int = Field(default=0, ge=0, le=10)
    time_ms: int | None = Field(default=None, ge=0)
    explanation_style: str | None = None


# Tips for common mistakes: in i18n.py (tip.<misconception>) when translated, else from content packs.
def misconception_tip(db: DbSession, lang: str, misconception: str | None) -> str | None:
    if not misconception:
        return None
    key = f"tip.{misconception}"
    if i18n.has(key):
        return i18n.t(lang, key)
    row = db.scalars(select(Misconception).where(Misconception.tag == misconception)).first()
    return row.tip if row else None


def localized_settings(settings: dict | None, lang: str) -> dict:
    """Settings as shown to the reader: noticed-support reasons in their language."""
    out = dict(settings or {})
    if lang != "en" and out.get("auto_support"):
        out["auto_support"] = {
            mode: {**v, "reason": i18n.translate_english(lang, v.get("reason", ""))} for mode, v in out["auto_support"].items()
        }
    return out


@router.post("/learn/attempts")
def submit_attempt(
    body: AttemptIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent), lang: str = Depends(i18n.language)
):
    item = db.get(Item, body.item_id)
    if not item or item.status != "approved":
        raise HTTPException(404, "Item not found")
    correct, misconception, row = learning.record_attempt(
        db, user, item, body.response, body.hints_used, body.time_ms, body.explanation_style
    )
    findings = learning.update_noticed_support(db, user)
    tip = None if correct else misconception_tip(db, lang, misconception)
    made = None if correct else learning.mistake_made(item, body.response)
    known = next((p for p in learning.mistake_patterns(db, user.id) if made and p.tag == made and p.status == "working_on"), None)
    explanations = db.scalars(
        select(Explanation).where(Explanation.concept_id == item.concept_id, Explanation.status == "approved")
    ).all()
    response = responses.build(
        responses.Context(
            prompt=item.prompt,
            answer=item.answer,
            response=body.response,
            correct=correct,
            solution=item.solution,
            misconception_tip=tip,
            wrong_in_a_row=row.wrong_streak,
            explanations={e.style: e.body for e in explanations},
            support=detect.effective_support(user.settings),
            tutor_available=ai.enabled(),
            lang=lang,
            mode_stats=None if correct else learning.mistake_mode_stats(db, user.id),
            best_method=None if correct else learning.best_method_overall(db, user),
            known_pattern=known is not None,
        ),
        seed=row.attempts,
    )
    response["adapted"] = [{"mode": f.mode, "message": detect.announce(f.mode, f.reason, lang)} for f in findings]
    if response["mode"]:
        attempt = db.scalars(
            select(Attempt).where(Attempt.student_id == user.id).order_by(Attempt.id.desc())
        ).first()
        attempt.feedback_mode = response["mode"]
        # Logged like every other adaptation, so "Why am I seeing this?" and audits can explain it.
        db.add(
            Decision(
                student_id=user.id,
                concept_id=item.concept_id,
                rule_id=f"F_{response['mode']}",
                rule_version=responses.RESPONSES_VERSION,
                action="feedback",
                reason=i18n.t("en", f"why.{response['mode']}"),
                evidence={
                    "wrong_in_a_row": row.wrong_streak,
                    "mistake": response.get("mistake") or misconception,
                    "for_you": response.get("for_you", False),
                    "pattern_times": known.times if known else 0,
                },
            )
        )
        db.commit()
    out = {
        "correct": correct,
        "progress": progress_label(row.p_known, row.attempts),
        "feedback": i18n.t(lang, "feedback.correct" if correct else "feedback.not_yet"),
        "response": response,
        "next_step": learning.next_step(db, user, item.concept_id, item.kind),
    }
    if tip:
        out["tip_tag"] = misconception  # so the app can ask "Was this tip helpful?"
    if known:
        out["pattern"] = {"text": learning.pattern_text(db, lang, known.tag), "times": known.times}
    if learning.pace_break_due(db, user):
        # Own pace only: offers a break, never changes the level of questions.
        out["offer_break"] = True
        db.add(
            Decision(
                student_id=user.id,
                concept_id=item.concept_id,
                rule_id="P_pace_break",
                rule_version=learning.thinking.THINKING_VERSION,
                action="offer_break",
                reason="The last few answers took much longer than usual and some were missed, so a short break was offered.",
                evidence={"compared_with": "own usual pace"},
            )
        )
        db.commit()
    if not correct:
        out["tip"] = tip
        out["solution"] = item.solution
        # The mistake is the way in: show the learner's answer next to the right one, with the topic's picture.
        out["your_answer"] = body.response
        out["right_answer"] = item.answer
        out["picture"] = next((e.picture for e in explanations if e.picture), None)
    return out


class FeltIn(BaseModel):
    concept_id: int
    style: str
    helped: bool


@router.post("/learn/explanation-feedback")
def explanation_feedback(body: FeltIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """The learner says whether a way of explaining helped. Used only to choose the next explanation."""
    if body.style not in STYLES:
        raise HTTPException(400, "Unknown style")
    if not db.get(Concept, body.concept_id):
        raise HTTPException(404, "Topic not found")
    learning.record_felt(db, user, body.concept_id, body.style, body.helped)
    return {"ok": True}


class EventIn(BaseModel):
    kind: str = Field(pattern="^(read_aloud|break|activity)$")


@router.post("/learn/events")
def learning_event(body: EventIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    """A help button was pressed. Counts only; used to notice what helps."""
    db.add(LearningEvent(student_id=user.id, kind=body.kind))
    db.commit()
    return {"ok": True}


# --- Spot the mistake ---------------------------------------------------------------
# A friend's answer with a common mistake in it. Finding the right answer earns a star.
# Stars are a small thank-you, never a score: they unlock nothing and are never compared.

SPOT_STARS_PER_DAY = 20  # stars are a thank-you, not something to grind
SPOT_PUZZLES_PER_DAY = 60  # puzzles given out per day: a guard against a stuck loop, far above real use
TIP_FEEDBACK_PER_DAY = 100
SPOT_FRIENDS = ["Asha", "Ravi", "Meera", "Arjun", "Zara", "Kabir", "Nila", "Dev"]


def spot_material(item: Item) -> list[str]:
    """The wrong answers this question has a written mistake for."""
    return [w for w in (item.misconceptions or {}) if not learning.same_answer(w, item.answer)]


def _spot_events_today(db: DbSession, user: User, kind: str) -> list[LearningEvent]:
    today = lab_day_start(learning.utcnow())
    return db.scalars(
        select(LearningEvent).where(LearningEvent.student_id == user.id, LearningEvent.kind == kind, LearningEvent.created_at >= today)
    ).all()


@router.get("/learn/spot")
def spot(concept_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    items = [
        i
        for i in db.scalars(select(Item).where(Item.concept_id == concept_id, Item.status == "approved")).all()
        if spot_material(i)
    ]
    # A puzzle never comes back on the same day.
    seen_today = _spot_events_today(db, user, "spot_seen")
    if len(seen_today) >= SPOT_PUZZLES_PER_DAY:
        raise HTTPException(429, "That's plenty of puzzles for today")
    seen = {e.item_id for e in seen_today}
    items = [i for i in items if i.id not in seen]
    if not items:
        raise HTTPException(404, "Nothing to spot here yet")
    item = random.choice(items)
    theirs = random.choice(spot_material(item))
    options = learning.shuffled_options(item) or []
    if not options:
        options = sorted({item.answer, theirs, *spot_material(item)[:2]}, key=lambda o: hash((item.id, o)))
    db.add(LearningEvent(student_id=user.id, kind="spot_seen", item_id=item.id))
    db.commit()
    return {
        "item_id": item.id,
        "friend": SPOT_FRIENDS[(item.id + user.id) % len(SPOT_FRIENDS)],
        "prompt": item.prompt,
        "their_answer": theirs,
        "options": options,
    }


class SpotIn(BaseModel):
    item_id: int
    their_answer: str = Field(max_length=200)
    choice: str = Field(max_length=200)


@router.post("/learn/spot")
def spot_answer(
    body: SpotIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent), lang: str = Depends(i18n.language)
):
    item = db.get(Item, body.item_id)
    if not item or item.status != "approved" or body.their_answer not in spot_material(item):
        raise HTTPException(404, "Item not found")
    # Only a puzzle SYNiq gave today can be answered, and only its first answer can earn a star.
    if body.item_id not in {e.item_id for e in _spot_events_today(db, user, "spot_seen")}:
        raise HTTPException(404, "Item not found")
    correct = learning.same_answer(body.choice, item.answer)
    on = rewards.rewards_on(db, user)
    stars_today = _spot_events_today(db, user, "spot_star")
    already = body.item_id in {e.item_id for e in stars_today}
    new_sticker = None
    star = on and correct and not already and len(stars_today) < SPOT_STARS_PER_DAY
    if star:
        db.add(LearningEvent(student_id=user.id, kind="spot_star", item_id=item.id))
        db.commit()
        n = learning.stars(db, user.id)
        if n % rewards.STARS_PER_STICKER == 0 and n // rewards.STARS_PER_STICKER <= len(rewards.STICKERS):
            new_sticker = rewards.STICKERS[n // rewards.STARS_PER_STICKER - 1]
    tag = item.misconceptions[body.their_answer]
    return {
        "correct": correct,
        "right_answer": item.answer,
        "why": misconception_tip(db, lang, tag),
        # Missing it costs nothing: a gentle "look carefully next time" in the app.
        "careful": not correct,
        "star_earned": star,
        "stars": learning.stars(db, user.id) if on else None,
        "new_sticker": new_sticker,
    }


# --- Was this tip helpful? ----------------------------------------------------------
# After a mistake tip, the learner can say whether it helped. Counts only, per tip, for the admin's list of tips to
# improve. Never shown to teachers per student, never used by the engine.

class TipFeedbackIn(BaseModel):
    item_id: int
    tag: str = Field(max_length=60)
    helpful: bool


@router.post("/learn/tip-feedback")
def tip_feedback(body: TipFeedbackIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent)):
    item = db.get(Item, body.item_id)
    if not item or body.tag not in (item.misconceptions or {}).values():
        raise HTTPException(404, "Tip not found")
    answered = db.scalars(select(Attempt.id).where(Attempt.student_id == user.id, Attempt.item_id == item.id).limit(1)).first()
    if not answered:
        raise HTTPException(404, "Tip not found")
    today = [*_spot_events_today(db, user, "tip_yes"), *_spot_events_today(db, user, "tip_no")]
    if len(today) >= TIP_FEEDBACK_PER_DAY:
        raise HTTPException(429, "Thank you, that's enough for today")
    if any(e.item_id == item.id and e.detail == body.tag for e in today):
        return {"ok": True}  # one vote per tip per question per day
    db.add(LearningEvent(student_id=user.id, kind="tip_yes" if body.helpful else "tip_no", item_id=item.id, detail=body.tag))
    db.commit()
    return {"ok": True}


# --- Check-ins, settings, progress -------------------------------------------------

class CheckInIn(BaseModel):
    mood: str | None = Field(default=None, pattern="^(great|okay|low|frustrated)$")
    energy: str | None = Field(default=None, pattern="^(high|medium|low)$")


@router.post("/checkins")
def checkin(
    body: CheckInIn, db: DbSession = Depends(get_db), user: User = Depends(require_learning_consent), lang: str = Depends(i18n.language)
):
    """Optional and self-reported. Skipping it changes nothing."""
    low = body.mood in ("low", "frustrated") or body.energy == "low"
    # The child hears the same thanks either way; whether it is kept is the parent's choice, explained on their page.
    message = i18n.t(lang, "checkin.thanks_low" if low else "checkin.thanks")
    if not has_consent(db, user.id, "mood_checkins"):
        return {"stored": False, "message": message}
    db.add(CheckIn(student_id=user.id, mood=body.mood, energy=body.energy))
    db.commit()
    return {"stored": True, "message": message}


@router.get("/me")
def me(user: User = Depends(current_user), db: DbSession = Depends(get_db), lang: str = Depends(i18n.language)):
    out = {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "settings": localized_settings(user.settings, lang),
        "must_change_password": user.must_change_password,
    }
    if user.role == "student":
        out["consent"] = {
            "core_learning": has_consent(db, user.id, "core_learning"),
            "mood_checkins": has_consent(db, user.id, "mood_checkins"),
        }
        board, grade = learning.class_of(user)
        out["class"] = {"board": board, "grade": grade}
        if learning.has_hindi_choice(db, user):
            out["hindi_course"] = learning.hindi_course(user)
    if user.role == "guardian":
        member = db.scalars(select(FamilyMember).where(FamilyMember.user_id == user.id)).first()
        holder = member and db.get(Family, member.family_id).holder_id == user.id
        out["family"] = {"holder": bool(holder)} if member else None
    return out


@router.put("/me/settings")
def update_settings(
    body: dict, user: User = Depends(current_user), db: DbSession = Depends(get_db), lang: str = Depends(i18n.language)
):
    """Accessibility settings need no diagnosis and no approval."""
    settings = dict(user.settings or {})
    for key, value in body.items():
        expected = ALLOWED_SETTINGS.get(key)
        if expected is None or not isinstance(value, expected):
            raise HTTPException(400, f"Invalid setting: {key}")
        if key == "preferred_style" and value is not None and value not in STYLES:
            raise HTTPException(400, "Unknown style")
        if key == "support_modes" and not (all(isinstance(v, str) for v in value) and set(value) <= set(detect.CHOSEN)):
            raise HTTPException(400, "Unknown support mode")
        if key == "auto_off" and not (all(isinstance(v, str) for v in value) and set(value) <= set(detect.NOTICED)):
            raise HTTPException(400, "Unknown support mode")
        if key == "reading_tint" and value not in READING_TINTS:
            raise HTTPException(400, "Unknown reading colour")
        if key == "hindi_course" and value not in ("a", "b"):
            raise HTTPException(400, "Unknown Hindi course")
        if key == "ui_language" and value not in i18n.LANGS:
            raise HTTPException(400, "Unknown language")
        if key == "font_scale" and not 0.8 <= float(value) <= 2.0:
            raise HTTPException(400, "font_scale must be between 0.8 and 2.0")
        settings[key] = value
    user.settings = settings
    db.add(user)
    db.commit()
    return localized_settings(settings, lang)


@router.get("/me/progress")
def my_progress(user: User = Depends(require_learning_consent), db: DbSession = Depends(get_db)):
    rows = db.scalars(select(Mastery).where(Mastery.student_id == user.id)).all()
    concepts = {c.id: c for c in db.scalars(select(Concept)).all()}
    now = learning.utcnow()
    return [
        {
            "concept_id": r.concept_id,
            "title": concepts[r.concept_id].title,
            "progress": progress_label(r.p_known, r.attempts),
            "review_due": bool(r.next_review_at and r.next_review_at <= now),
        }
        for r in rows
        if r.attempts > 0
    ]


@router.get("/me/why/{decision_id}")
def why(decision_id: int, user: User = Depends(current_user), db: DbSession = Depends(get_db), lang: str = Depends(i18n.language)):
    """'Why am I seeing this?' in plain words."""
    d = db.get(Decision, decision_id)
    if not d or d.student_id != user.id:
        raise HTTPException(404, "Not found")
    return {"reason": i18n.translate_english(lang, d.reason), "rule": d.rule_id, "version": d.rule_version}
