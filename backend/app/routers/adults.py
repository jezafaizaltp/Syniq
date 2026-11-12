"""Teacher, guardian and auth endpoints.

No endpoint here returns a ranked or ordered list of students by ability, and
self-reported check-ins are never exposed to teachers.
"""

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..auth import (
    MIN_PASSWORD,
    audit,
    clear_login_failures,
    current_user,
    guardian_of,
    has_consent,
    hash_password,
    login_blocked,
    new_token,
    record_login_failure,
    require_role,
    verify_password,
)
from .. import i18n, learning, rewards
from ..db import get_db
from ..engine import checkup, detect, methods
from ..engine.mastery import progress_label
from ..models import (
    Attempt,
    Chapter,
    ClassGroup,
    Concept,
    Consent,
    Explanation,
    GuardianLink,
    Item,
    LearningEvent,
    Mastery,
    Session,
    User,
)

router = APIRouter()


# --- Auth ------------------------------------------------------------------------

class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/login", tags=["auth"])
def login(body: LoginIn, request: Request, db: DbSession = Depends(get_db), lang: str = Depends(i18n.language)):
    login_id = body.email.lower().strip()
    key = f"{login_id}|{request.client.host if request.client else ''}"
    if login_blocked(key):
        raise HTTPException(429, i18n.t(lang, "err.too_many_tries"))
    user = db.scalars(select(User).where(User.email == login_id)).first()
    if not user or not verify_password(body.password, user.password_hash):
        record_login_failure(key)
        raise HTTPException(401, i18n.t(lang, "err.wrong_login"))
    clear_login_failures(key)
    return {"token": new_token(db, user), "role": user.role, "name": user.name}


@router.post("/auth/logout", tags=["auth"])
def logout(authorization: str = Header(default=""), db: DbSession = Depends(get_db)):
    sess = db.get(Session, authorization.removeprefix("Bearer ").strip())
    if sess:
        db.delete(sess)
        db.commit()
    return {"ok": True}


class PasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=MIN_PASSWORD, max_length=200)


@router.post("/me/password", tags=["auth"])
def change_password(
    body: PasswordIn, db: DbSession = Depends(get_db), user: User = Depends(current_user), lang: str = Depends(i18n.language)
):
    if not verify_password(body.current, user.password_hash):
        raise HTTPException(400, i18n.t(lang, "err.current_password"))
    if body.new == body.current:
        raise HTTPException(400, i18n.t(lang, "err.same_password"))
    user.password_hash = hash_password(body.new)
    user.must_change_password = False
    # Sign out everywhere else.
    for other in db.scalars(select(Session).where(Session.user_id == user.id)).all():
        db.delete(other)
    db.commit()
    return {"token": new_token(db, user)}


# --- Teacher -----------------------------------------------------------------------

def _teacher_class(db: DbSession, teacher: User, class_id: int) -> ClassGroup:
    group = db.get(ClassGroup, class_id)
    if not group or (teacher.role == "teacher" and group.teacher_id != teacher.id):
        raise HTTPException(404, "Class not found")
    return group


def _shared_students(db: DbSession, class_id: int) -> list[User]:
    """Students in the class whose guardians allow sharing with the school."""
    students = db.scalars(select(User).where(User.class_group_id == class_id, User.role == "student")).all()
    return [s for s in students if has_consent(db, s.id, "school_sharing")]


@router.get("/teacher/classes", tags=["teacher"])
def my_classes(db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    q = select(ClassGroup)
    if user.role == "teacher":
        q = q.where(ClassGroup.teacher_id == user.id)
    return [{"id": g.id, "name": g.name} for g in db.scalars(q).all()]


@router.get("/teacher/classes/{class_id}/overview", tags=["teacher"])
def class_overview(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Per concept: how many students are at each stage. Counts, not rankings."""
    _teacher_class(db, user, class_id)
    students = _shared_students(db, class_id)
    ids = [s.id for s in students]
    # Only the subjects this class learns (its students' board and class), not every class in SYNiq.
    subjects = {sub.id: sub for st in students for sub in learning.subjects_for(db, st)}
    chapters = {
        ch.id: ch for ch in db.scalars(select(Chapter).where(Chapter.subject_id.in_(list(subjects)))).all()
    } if subjects else {}
    concepts = db.scalars(
        select(Concept).where(Concept.chapter_id.in_(list(chapters))).order_by(Concept.chapter_id, Concept.order)
    ).all() if chapters else []
    rows = db.scalars(select(Mastery).where(Mastery.student_id.in_(ids))).all() if ids else []
    by_concept: dict[int, list[Mastery]] = {}
    for r in rows:
        by_concept.setdefault(r.concept_id, []).append(r)

    concept_out = []
    for c in concepts:
        labels = Counter(progress_label(r.p_known, r.attempts) for r in by_concept.get(c.id, []))
        labels["not_started"] += len(ids) - sum(labels.values())
        miscon = Counter()
        for r in by_concept.get(c.id, []):
            miscon.update(r.misconceptions or {})
        concept_out.append(
            {
                "concept_id": c.id,
                "title": c.title,
                "subject": subjects[chapters[c.chapter_id].subject_id].name,
                "chapter": chapters[c.chapter_id].title,
                "counts": {k: labels.get(k, 0) for k in ("not_started", "learning", "getting_there", "secure")},
                "common_misconceptions": [m for m, _ in miscon.most_common(3)],
            }
        )
    audit(db, user, "view_class_overview")
    return {"students": len(ids), "concepts": concept_out}


@router.get("/teacher/classes/{class_id}/support", tags=["teacher"])
def may_need_support(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Students who have been stuck on a concept, listed alphabetically, with the concept."""
    _teacher_class(db, user, class_id)
    out = []
    for s in sorted(_shared_students(db, class_id), key=lambda x: x.name):
        stuck = db.scalars(
            select(Mastery).where(Mastery.student_id == s.id, Mastery.attempts >= 4, Mastery.p_known < 0.4)
        ).all()
        if stuck:
            titles = [db.get(Concept, r.concept_id).title for r in stuck]
            out.append({"student_id": s.id, "name": s.name, "concepts": titles})
    audit(db, user, "view_support_list")
    return out


@router.get("/teacher/classes/{class_id}/methods", tags=["teacher"])
def class_methods(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Per subject, students grouped by the way of explaining that helps them most right now.

    Groups are by how students learn, never by marks or ability, and they change as
    students answer. Students without a clear pattern yet are only counted.
    """
    _teacher_class(db, user, class_id)
    subjects: dict[int, dict] = {}
    for s in sorted(_shared_students(db, class_id), key=lambda x: x.name):
        for row in learning.method_summary(db, s.id):
            entry = subjects.setdefault(row["subject_id"], {"subject_id": row["subject_id"], "subject": row["subject"], "groups": {}, "still_finding_out": 0})
            if row["clearest"]:
                entry["groups"].setdefault(row["clearest"], []).append({"student_id": s.id, "name": s.name})
            else:
                entry["still_finding_out"] += 1
    audit(db, user, "view_class_methods")
    return [
        {**e, "groups": [{"style": k, "students": v} for k, v in sorted(e["groups"].items())]}
        for _, e in sorted(subjects.items())
    ]


@router.get("/teacher/classes/{class_id}/mistakes", tags=["teacher"])
def class_mistakes(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Mistakes several students keep making: who is still working on each, and how many have fixed it.

    Lets a teacher re-teach one idea to the few who need it. Most common first.
    """
    _teacher_class(db, user, class_id)
    by_tag: dict[str, dict] = {}
    for s in sorted(_shared_students(db, class_id), key=lambda x: x.name):
        for p in learning.pattern_summary(db, s.id):
            e = by_tag.setdefault(p["tag"], {"tag": p["tag"], "text": p["text"], "working_on": [], "fixed": 0, "topics": []})
            if p["status"] == "working_on":
                e["working_on"].append({"student_id": s.id, "name": s.name})
            else:
                e["fixed"] += 1
            e["topics"] += [t for t in p["topics"] if t not in e["topics"]]
    audit(db, user, "view_class_mistakes")
    return sorted(by_tag.values(), key=lambda e: (-len(e["working_on"]), -e["fixed"], e["text"]))


HARD_TROUBLE_MIN_STUDENTS = 2  # a topic is listed when this many students are stuck on its harder questions


@router.get("/teacher/classes/{class_id}/hard-trouble", tags=["teacher"])
def class_hard_trouble(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Topics whose harder questions several students have missed twice or more without one right yet.

    A harder question is best gone through together on the board. Students in alphabetical order, never ranked.
    """
    _teacher_class(db, user, class_id)
    hard_items = {i.id: i.concept_id for i in db.scalars(select(Item).where(Item.difficulty >= 3, Item.status == "approved")).all()}
    by_topic: dict[int, list[dict]] = {}
    for s in sorted(_shared_students(db, class_id), key=lambda x: x.name):
        wrong: Counter = Counter()
        right: set[int] = set()
        for item_id, correct in db.execute(
            select(Attempt.item_id, Attempt.correct).where(Attempt.student_id == s.id, Attempt.item_id.in_(list(hard_items)))
        ).all():
            if correct:
                right.add(hard_items[item_id])
            else:
                wrong[hard_items[item_id]] += 1
        for cid, n in wrong.items():
            if n >= 2 and cid not in right:
                by_topic.setdefault(cid, []).append({"student_id": s.id, "name": s.name})
    out = []
    for cid, students in by_topic.items():
        if len(students) < HARD_TROUBLE_MIN_STUDENTS:
            continue
        c = db.get(Concept, cid)
        ch = db.get(Chapter, c.chapter_id)
        out.append({"concept_id": cid, "topic": c.title, "chapter": ch.title, "students": students})
    audit(db, user, "view_class_hard_trouble")
    return sorted(out, key=lambda e: (-len(e["students"]), e["topic"]))


LESSON_TROUBLE_MIN_TRIED = 3  # an idea is listed once this many students have answered its check


@router.get("/teacher/classes/{class_id}/lesson-trouble", tags=["teacher"])
def class_lesson_trouble(class_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Lesson ideas that half or more of the class missed the first time, and the way that helped them after.

    Counts only, never names: it is about the idea, not who missed it. "Helped" is the way of explaining on screen
    when a student who had missed it then got it right, so the teacher knows how to go over it on the board.
    """
    _teacher_class(db, user, class_id)
    ids = [s.id for s in _shared_students(db, class_id)]
    events = db.execute(
        select(LearningEvent.student_id, LearningEvent.kind, LearningEvent.detail)
        .where(LearningEvent.student_id.in_(ids), LearningEvent.kind.in_(("lesson_right", "lesson_wrong")))
        .order_by(LearningEvent.created_at, LearningEvent.id)
    ).all() if ids else []
    first: dict[tuple[int, int], dict[int, bool]] = {}  # (topic, idea) -> student -> right the first time
    helped: dict[tuple[int, int], Counter] = {}
    for sid, kind, detail in events:
        parts = (detail or "").split(":")
        if len(parts) != 4 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        key, style, attempt = (int(parts[0]), int(parts[1])), parts[2], parts[3]
        seen = first.setdefault(key, {})
        if attempt == "1" and sid not in seen:
            seen[sid] = kind == "lesson_right"
        elif attempt == "2" and kind == "lesson_right" and seen.get(sid) is False and style in methods.STYLES:
            helped.setdefault(key, Counter())[style] += 1
    out = []
    for (cid, step), answers in first.items():
        missed = sum(1 for ok in answers.values() if not ok)
        if len(answers) < LESSON_TROUBLE_MIN_TRIED or missed * 2 < len(answers):
            continue
        c = db.get(Concept, cid)
        if not c or not c.lesson or step >= len(c.lesson):
            continue
        best = helped.get((cid, step))
        out.append(
            {
                "concept_id": cid,
                "topic": c.title,
                "chapter": db.get(Chapter, c.chapter_id).title,
                "idea": step + 1,
                "check": c.lesson[step]["check"]["prompt"],
                "tried": len(answers),
                "missed_first": missed,
                "helped": best.most_common(1)[0][0] if best else None,
            }
        )
    audit(db, user, "view_class_lesson_trouble")
    return sorted(out, key=lambda e: (-e["missed_first"] / e["tried"], -e["tried"], e["topic"], e["idea"]))[:10]


@router.get("/teacher/classes/{class_id}/chapter-progress", tags=["teacher"])
def class_chapter_progress(
    class_id: int, chapter_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))
):
    """For one chapter: how many students are secure, getting there, learning or not started on each topic.

    Counts only: no names, no marks, nothing to rank anyone by. For the teacher's printed planning sheet.
    """
    _teacher_class(db, user, class_id)
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    students = _shared_students(db, class_id)
    ids = [s.id for s in students]
    topics = db.scalars(select(Concept).where(Concept.chapter_id == chapter_id).order_by(Concept.order, Concept.id)).all()
    rows = []
    for c in topics:
        counts = {"secure": 0, "getting_there": 0, "learning": 0, "not_started": 0}
        seen = 0
        for r in db.scalars(select(Mastery).where(Mastery.concept_id == c.id, Mastery.student_id.in_(ids), Mastery.attempts > 0)).all():
            counts[progress_label(r.p_known, r.attempts)] += 1
            seen += 1
        counts["not_started"] = len(ids) - seen
        rows.append({"topic": c.title, **counts})
    audit(db, user, "view_class_chapter_progress")
    return {"chapter": chapter.title, "number": chapter.number, "students": len(ids), "topics": rows}


@router.get("/teacher/review-queue", tags=["teacher"])
def review_queue(db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    items = db.scalars(select(Item).where(Item.status == "draft")).all()
    exps = db.scalars(select(Explanation).where(Explanation.status == "draft")).all()
    return {
        "items": [
            {
                "id": i.id,
                "concept": db.get(Concept, i.concept_id).title,
                "kind": i.kind,
                "prompt": i.prompt,
                "options": i.options,
                "answer": i.answer,
                "hints": i.hints,
                "solution": i.solution,
                "difficulty": i.difficulty,
                "source": i.source,
                "review_note": i.review_note,
            }
            for i in items
        ],
        "explanations": [
            {
                "id": e.id,
                "concept": db.get(Concept, e.concept_id).title,
                "style": e.style,
                "body": e.body,
                "source": e.source,
                "review_note": e.review_note,
            }
            for e in exps
        ],
    }


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


@router.post("/teacher/items/{item_id}/review", tags=["teacher"])
def review_item(item_id: int, body: ReviewIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.status = "approved" if body.decision == "approve" else "rejected"
    item.reviewed_by = user.id
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/teacher/explanations/{exp_id}/review", tags=["teacher"])
def review_explanation(exp_id: int, body: ReviewIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    exp = db.get(Explanation, exp_id)
    if not exp:
        raise HTTPException(404, "Explanation not found")
    exp.status = "approved" if body.decision == "approve" else "rejected"
    db.commit()
    return {"id": exp.id, "status": exp.status}


# --- Guardian ----------------------------------------------------------------------

@router.get("/guardian/children", tags=["guardian"])
def children(db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian")), lang: str = Depends(i18n.language)):
    links = db.scalars(select(GuardianLink).where(GuardianLink.guardian_id == user.id)).all()
    out = []
    for link in links:
        child = db.get(User, link.student_id)
        out.append(
            {
                "id": child.id,
                "name": child.name,
                "consent": {
                    scope: has_consent(db, child.id, scope)
                    for scope in ("core_learning", "mood_checkins", "school_sharing", "thinking_puzzles")
                },
                "support_modes": (child.settings or {}).get("support_modes", []),
                "noticed": [
                    {"mode": mode, "reason": i18n.translate_english(lang, v["reason"]), "on": mode not in (child.settings or {}).get("auto_off", [])}
                    for mode, v in (child.settings or {}).get("auto_support", {}).items()
                ],
                "checkup_note": _checkup_note(db, user, child),
                "rewards_on": rewards.rewards_on(db, child),
            }
        )
    return out


def _checkup_note(db: DbSession, guardian: User, child: User) -> bool:
    """A gentle note that a free check might help. Never names a condition (engine/checkup.py)."""
    answers = db.execute(select(Attempt.created_at, Attempt.correct).where(Attempt.student_id == child.id)).all()
    if len(answers) < checkup.MIN_ANSWERS:
        return False
    s = child.settings or {}
    off = set(s.get("auto_off", []))
    noticed_on = sum(1 for m in s.get("auto_support", {}) if m in detect.NOTICED and m not in off)
    stuck = len(
        db.scalars(select(Mastery).where(Mastery.student_id == child.id, Mastery.attempts >= 4, Mastery.p_known < 0.4)).all()
    )
    hidden = (guardian.settings or {}).get("checkup_hidden", {}).get(str(child.id))
    return checkup.show_note(
        [(a.created_at, a.correct) for a in answers],
        noticed_on,
        stuck,
        learning.utcnow(),
        datetime.fromisoformat(hidden) if hidden else None,
    )


@router.post("/guardian/children/{student_id}/checkup-note/hide", tags=["guardian"])
def hide_checkup_note(student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """The parent has read the note. It stays hidden for checkup.HIDE_DAYS days. Kept on the parent's own account."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    settings = dict(user.settings or {})
    hidden = dict(settings.get("checkup_hidden", {}))
    hidden[str(student_id)] = learning.utcnow().isoformat()
    settings["checkup_hidden"] = hidden
    user.settings = settings
    db.commit()
    audit(db, user, "hide_checkup_note", student_id)
    return {"ok": True}


@router.get("/guardian/children/{student_id}/progress", tags=["guardian"])
def child_progress(
    student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian")), lang: str = Depends(i18n.language)
):
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    rows = db.scalars(select(Mastery).where(Mastery.student_id == student_id, Mastery.attempts > 0)).all()
    practised = len(db.scalars(select(Attempt.id).where(Attempt.student_id == student_id)).all())
    audit(db, user, "view_child_progress", student_id)
    return {
        "questions_practised": practised,
        "note": i18n.t(lang, "parent.progress_note"),
        "concepts": [
            {"title": db.get(Concept, r.concept_id).title, "progress": progress_label(r.p_known, r.attempts)}
            for r in rows
        ],
    }


@router.get("/guardian/children/{student_id}/methods", tags=["guardian"])
def child_methods(student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Which ways of explaining have helped the child lately, per subject."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    audit(db, user, "view_child_methods", student_id)
    return {"subjects": learning.method_summary(db, student_id)}


@router.get("/guardian/children/{student_id}/strengths", tags=["guardian"])
def child_strengths(student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Where the child shines lately and ways to grow it at home. In words, never a score or a label."""
    from .. import strengths

    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    audit(db, user, "view_child_strengths", student_id)
    child = db.get(User, student_id)
    return strengths.strengths(db, child, puzzles_allowed=has_consent(db, student_id, "thinking_puzzles"))


@router.get("/guardian/children/{student_id}/mistakes", tags=["guardian"])
def child_mistakes(
    student_id: int, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian")), lang: str = Depends(i18n.language)
):
    """Mistakes the child has made more than once, and which are fixed now."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    audit(db, user, "view_child_mistakes", student_id)
    return {"patterns": learning.pattern_summary(db, student_id, lang)}


class SupportIn(BaseModel):
    modes: list[str] = Field(max_length=3)


@router.put("/guardian/children/{student_id}/support", tags=["guardian"])
def set_support(student_id: int, body: SupportIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Support for sight, hearing or speech, which SYNiq can't tell from answers."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    if not set(body.modes) <= set(detect.CHOSEN):
        raise HTTPException(400, "Unknown support mode")
    child = db.get(User, student_id)
    child.settings = {**(child.settings or {}), "support_modes": body.modes}
    db.commit()
    audit(db, user, "set_child_support", student_id)
    return {"support_modes": body.modes}


class RewardsIn(BaseModel):
    on: bool


@router.put("/guardian/children/{student_id}/rewards", tags=["guardian"])
def set_rewards(student_id: int, body: RewardsIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    """Stickers and achievements on or off for this child. The parent's choice wins over the school's default."""
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    child = db.get(User, student_id)
    child.settings = {**(child.settings or {}), "rewards": "on" if body.on else "off"}
    db.commit()
    audit(db, user, "set_child_rewards", student_id)
    return {"rewards_on": body.on}


class ConsentIn(BaseModel):
    scope: str = Field(pattern="^(core_learning|mood_checkins|school_sharing|thinking_puzzles)$")
    granted: bool
    method: str = "in_app"


@router.post("/guardian/children/{student_id}/consent", tags=["guardian"])
def set_consent(student_id: int, body: ConsentIn, db: DbSession = Depends(get_db), user: User = Depends(require_role("guardian"))):
    if not guardian_of(db, user, student_id):
        raise HTTPException(404, "Not found")
    db.add(Consent(student_id=student_id, guardian_id=user.id, scope=body.scope, granted=body.granted, method=body.method))
    db.commit()
    audit(db, user, f"consent:{body.scope}:{'yes' if body.granted else 'no'}", student_id)
    return {"scope": body.scope, "granted": body.granted}

