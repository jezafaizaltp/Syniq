"""Data model.

The learner model (Mastery, CheckIn) is kept apart from raw interaction events
(Attempt) and from the adaptation log (Decision), so each can be governed,
retained and audited separately.
"""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- People and access -------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20))  # student | guardian | teacher | admin | specialist
    class_group_id: Mapped[int | None] = mapped_column(ForeignKey("class_groups.id"), nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    # Set for accounts made with a temporary password; cleared when they choose their own.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Session(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship()


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", use_alter=True, name="fk_class_groups_teacher_id_users"), nullable=True)
    # The chapter the teacher chose for today's lab period, shown first to the class. Only counts on that day.
    today_chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id", use_alter=True, name="fk_class_groups_today_chapter"), nullable=True)
    today_set_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class GuardianLink(Base):
    __tablename__ = "guardian_links"
    __table_args__ = (UniqueConstraint("guardian_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Consent(Base):
    """Append-only consent record. The latest row per (student, scope) wins."""

    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    scope: Mapped[str] = mapped_column(String(40))  # core_learning | mood_checkins | school_sharing | thinking_puzzles
    granted: Mapped[bool] = mapped_column(Boolean)
    method: Mapped[str] = mapped_column(String(60), default="school_form")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SpecialistLink(Base):
    """A parent shares one child with one specialist (counsellor, special educator).

    Ending a share sets ended_at; rows are never deleted, so who could see what, and when, stays on record.
    """

    __tablename__ = "specialist_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    specialist_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Family(Base):
    """A family account. The holder (usually the mother) controls the children's data and who else joins."""

    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    holder_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan: Mapped[str] = mapped_column(String(20), default="free")  # free | premium
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FamilyMember(Base):
    """An adult in a family with their own login: mother, father, grandparent or another carer."""

    __tablename__ = "family_members"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    relation: Mapped[str] = mapped_column(String(20))  # mother | father | grandparent | carer
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Child(Base):
    """A child in a family, from pregnancy onwards. Only school-age children get a login of their own.

    The section SYNiq opens (pregnancy, baby, early years, school) comes from these dates and the class,
    never from a test or a label.
    """

    __tablename__ = "children"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # while expecting
    board: Mapped[str] = mapped_column(String(30), default="cbse")  # cbse | kerala_scert
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)  # -1 LKG, 0 UKG, 1..12
    student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # their own login
    # Healthy screen time (2 to 4): minutes a day and per sitting, set by the account holder.
    daily_limit: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    session_limit: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChildMark(Base):
    """Something a parent has ticked for a child: a milestone seen, or a vaccine given (with its date)."""

    __tablename__ = "child_marks"
    __table_args__ = (UniqueConstraint("child_id", "kind", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # milestone | vaccine
    key: Mapped[str] = mapped_column(String(40))
    on_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CareLog(Base):
    """A feed, meal, sleep or nappy the family logs for a baby. Visible only to the family."""

    __tablename__ = "care_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # breastfeed | bottle | food | sleep | nappy
    at: Mapped[datetime] = mapped_column(DateTime, index=True)  # India time, as the parent sees it
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ScreenTimeSession(Base):
    """One sitting of healthy screen time. Only the time used is kept, never taps or answers."""

    __tablename__ = "screen_time_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True)
    started_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    activity_id: Mapped[str] = mapped_column(String(40))
    day: Mapped[str] = mapped_column(String(10), index=True)  # India date, YYYY-MM-DD
    allowed_minutes: Mapped[int] = mapped_column(Integer)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    subject_student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Curriculum ---------------------------------------------------------------

class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(10), default="en")  # content language
    grade: Mapped[int] = mapped_column(Integer, default=9)
    syllabus: Mapped[str] = mapped_column(String(30), default="kerala_scert")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer, default=0)
    # Teacher-written summary of what the textbook says. Grounds AI drafts and the tutor.
    notes: Mapped[str] = mapped_column(Text, default="")
    # A hands-on activity to explore the topic (app/activities.py), or None.
    activity: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)


class ConceptPrereq(Base):
    __tablename__ = "concept_prereqs"
    __table_args__ = (UniqueConstraint("concept_id", "prereq_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"))
    prereq_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"))


class Explanation(Base):
    __tablename__ = "explanations"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    style: Mapped[str] = mapped_column(String(30))  # text | visual | step_by_step | real_world
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved | rejected
    source: Mapped[str] = mapped_column(String(20), default="teacher")  # teacher | ai | pack
    review_note: Mapped[str] = mapped_column(Text, default="")
    # For the visual style: a drawing the app renders (see app/pictures.py). None for text only.
    picture: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # mcq | numeric
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[str] = mapped_column(String(200))
    hints: Mapped[list] = mapped_column(JSON, default=list)
    solution: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1..3
    # Maps a wrong response to a misconception tag, e.g. {"x² + 9": "square_each_term"}
    misconceptions: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved | rejected
    source: Mapped[str] = mapped_column(String(20), default="teacher")  # teacher | ai | pack
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # What a teacher wrote on the paper review sheet. Kept apart from review_note, which the
    # content loader rewrites, so it survives a reload until someone marks it fixed.
    fix_note: Mapped[str] = mapped_column(Text, default="")


class TutorQuestion(Base):
    """Something a student asked Ask SYNiq that the topic's content didn't cover.

    Kept so the content can grow. Never linked to the student: no id, name or
    class, and contact details are removed from the text before it is saved.
    """

    __tablename__ = "tutor_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    text: Mapped[str] = mapped_column(String(600))
    answered_by: Mapped[str] = mapped_column(String(10))  # ai | none
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # Set when an adult has dealt with it (added content, or nothing to add). Hidden by default.
    handled: Mapped[bool] = mapped_column(Boolean, default=False)


class Misconception(Base):
    """What to tell a student who made a common mistake, by the tag items use in misconceptions."""

    __tablename__ = "misconceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(60), unique=True)
    tip: Mapped[str] = mapped_column(Text)


# --- Raw events ---------------------------------------------------------------

class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    response: Mapped[str] = mapped_column(String(200))
    correct: Mapped[bool] = mapped_column(Boolean)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # The response SYNiq gave to this answer (count_it_out, step_by_step, ...), if it was wrong.
    feedback_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PuzzleAnswer(Base):
    """A thinking puzzle answered inside a lesson (app/thinking.py). Kept only with the parent's consent."""

    __tablename__ = "puzzle_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    domain: Mapped[str] = mapped_column(String(20))
    level: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool] = mapped_column(Boolean)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningEvent(Base):
    """A help button the student pressed (read aloud, take a break). Never timings."""

    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # read_aloud | break
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Learner model -------------------------------------------------------------

class Mastery(Base):
    __tablename__ = "mastery"
    __table_args__ = (UniqueConstraint("student_id", "concept_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"))
    p_known: Mapped[float] = mapped_column(Float, default=0.2)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_streak: Mapped[int] = mapped_column(Integer, default=0)
    wrong_streak: Mapped[int] = mapped_column(Integer, default=0)
    secured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    misconceptions: Mapped[dict] = mapped_column(JSON, default=dict)
    # Per explanation style: {"visual": {"after_correct": 3, "after_wrong": 1}}
    format_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    energy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Adaptation log --------------------------------------------------------------

class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id"), nullable=True)
    rule_id: Mapped[str] = mapped_column(String(40))
    rule_version: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Subject checks ---------------------------------------------------------------
# A short check per subject: at the start (tells the engine where to begin), at the end of
# term and four weeks later (measure what was learnt and kept). Never shown as a score.

class CheckRound(Base):
    """An end-of-term or retention check the admin opens for every student at once."""

    __tablename__ = "check_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # end | retention
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SubjectCheck(Base):
    """One student's check in one subject. Answers stay here, never in the practice history."""

    __tablename__ = "subject_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    kind: Mapped[str] = mapped_column(String(10))  # start | end | retention
    round_id: Mapped[int | None] = mapped_column(ForeignKey("check_rounds.id"), nullable=True)
    item_ids: Mapped[list] = mapped_column(JSON, default=list)
    # {"<item id>": {"response": "...", "correct": true}}
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | done | skipped
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# --- The student's own space ------------------------------------------------------
# Goals and notes belong to the student. No teacher, parent or engine reads them.

class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(String(200))
    due_on: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class InterestReflection(Base):
    """How an exploration activity felt to the student. Theirs alone; never turned into a label."""

    __tablename__ = "interest_reflections"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    activity_id: Mapped[str] = mapped_column(String(60))
    feeling: Mapped[str] = mapped_column(String(20))  # loved | okay | not_for_me
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Pilot evaluation -------------------------------------------------------------
# School marks used only to measure whether SYNiq helped, in aggregate. Kept apart from
# the learner model: nothing in the engine, teacher, parent or student views reads them.

class Assessment(Base):
    """A school test or term exam whose marks measure the pilot, e.g. "First term 2027, Maths"."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    max_marks: Mapped[float] = mapped_column(Float)
    phase: Mapped[str] = mapped_column(String(10))  # before | after (SYNiq started)
    taken_on: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssessmentScore(Base):
    """One student's marks: a pilot student by account, or a comparison student by an anonymous code."""

    __tablename__ = "assessment_scores"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id"),
        UniqueConstraint("assessment_id", "comparison_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    comparison_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    marks: Mapped[float] = mapped_column(Float)


class SchoolSetting(Base):
    """A few words about the school, set by the admin: its name, shown on sign-in, letters and slips."""

    __tablename__ = "school_settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))


class HelpRequest(Base):
    """A student's raised hand in the lab: seen only by their class teacher, cleared when helped."""

    __tablename__ = "help_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_group_id: Mapped[int] = mapped_column(ForeignKey("class_groups.id"), index=True)
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
