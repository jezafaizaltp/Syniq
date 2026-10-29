"""Claude API calls: the student tutor and AI-drafted content for teacher review.

Privacy rules for everything in this module:
- No student's name, email, id, mastery, mood or history is ever sent. The tutor
  sees only curriculum content and the words the student typed, with obvious
  contact details removed.
- Tutor conversations are not stored on the server.
- AI-drafted content is saved as a draft. Nothing reaches students until a
  teacher approves it.

AI is off unless ANTHROPIC_API_KEY is set; every caller handles AIUnavailable.
"""

import json
import os
import re

import anthropic

from .i18n import t

MODEL = os.environ.get("SYNIQ_AI_MODEL", "claude-opus-5-5")
# If Claude declines a request, the API retries it on Anthropic's recommended
# fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

STYLE_GUIDE = {
    "text": "a short explanation in plain words",
    "visual": "a description of a picture or diagram the student can imagine or draw",
    "step_by_step": "a worked example broken into numbered steps",
    "real_world": "an everyday example from life in Kerala",
}


class AIUnavailable(Exception):
    """No API key is configured, or the API could not be reached."""


class AIDeclined(Exception):
    """Claude declined the request, even after the fallback."""


_client = None


def set_client(client) -> None:
    """Swap in a client (tests use a fake)."""
    global _client
    _client = client


def get_client():
    global _client
    if _client is None and os.environ.get("ANTHROPIC_API_KEY"):
        _client = anthropic.Anthropic()
    return _client


def enabled() -> bool:
    return get_client() is not None


def _call(system: str, messages: list[dict], *, max_tokens: int, effort: str, schema: dict | None = None) -> str:
    client = get_client()
    if client is None:
        raise AIUnavailable("AI is not switched on for this server")
    output_config: dict = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config=output_config,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.APIError as e:  # network, auth, rate limit: the app keeps working without AI
        raise AIUnavailable(str(e)) from e
    if response.stop_reason == "refusal":
        raise AIDeclined("Claude declined this request")
    return "".join(b.text for b in response.content if b.type == "text").strip()


# --- Student tutor ----------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(?:\+?\d[\s-]?){8,}")


def scrub(text: str) -> str:
    """Remove contact details a student might type by mistake."""
    return _PHONE.sub("[number removed]", _EMAIL.sub("[email removed]", text))


# Messages that need a trusted adult, not a maths explanation. Checked before any
# API call so the reply is immediate and the same every time.
_DISTRESS = re.compile(
    r"\b(kill myself|suicide|want to die|hurt myself|self[- ]harm|cut myself|end my life|"
    r"someone (is )?(hurting|hitting|touching) me|being abused|abusing me|"
    r"a+thmahathya|marikkanam|marikkan thonnunnu)\b",
    re.IGNORECASE,
)
# Malayalam script: no \b, which doesn't work reliably with Malayalam vowel signs.
# Words for suicide, wanting to die, not wanting to live, and someone hitting or harming me.
_DISTRESS_ML = re.compile(r"ആത്മഹത്യ|മരിക്കണം|മരിക്കാൻ തോന്നു|ജീവിക്കണ്ട|ജീവിതം അവസാനിപ്പിക്ക|എന്നെ ഉപദ്രവിക്കു|എന്നെ തല്ലു|എന്നെ പീഡിപ്പിക്കു")

DISTRESS_REPLY = t("en", "tutor.distress")

TUTOR_SYSTEM = """You are SYNiq, a patient tutor for a Class 9 student in Kerala who follows the Kerala State (SCERT) syllabus.

The student is working on this topic:
Subject: {subject}
Chapter: {chapter}
Topic: {concept}

Teacher's notes on what the textbook covers:
{notes}

Explanations the teacher has approved for this topic:
{explanations}

How to help:
- Stay with this topic and the notes above. If the question is about something else in the syllabus, help briefly and suggest they open that chapter. If it is unrelated to school, gently bring them back.
- Guide rather than tell. Ask one small question or give one hint at a time so the student does the thinking. Give a full worked answer only if they have tried and are still stuck.
- If you are not sure something matches the Kerala textbook, say so and suggest checking with their teacher.
- Keep replies short: a few sentences, plain words. Use ² and × rather than LaTeX.
- {language}
- Be warm and never judge. Mistakes are normal. Never describe the student as weak, slow or behind.
- Do not ask for or repeat personal details such as names, phone numbers, addresses or school.
- If the student says they are upset, unsafe or being hurt, respond kindly, encourage them to talk to a trusted adult, and mention the free Tele-MANAS helpline on 14416."""


LANGUAGE_LINE = {
    "en": "Reply in Indian English, or in Malayalam if the student writes in Malayalam.",
    "ml": "Reply in simple Malayalam, in Malayalam script, even if the student writes in English or Manglish. "
    "Keep numbers, maths symbols and textbook terms the student would recognise.",
}


def tutor_reply(
    *, subject: str, chapter: str, concept: str, notes: str, explanations: list[str], history: list[dict], lang: str = "en"
) -> str:
    """history: [{"role": "student"|"tutor", "text": ...}], ending with the student's message."""
    latest = history[-1]["text"] if history else ""
    if _DISTRESS.search(latest) or _DISTRESS_ML.search(latest):
        return t(lang, "tutor.distress")
    messages = [
        {"role": "user" if turn["role"] == "student" else "assistant", "content": scrub(turn["text"])}
        for turn in history
    ]
    system = TUTOR_SYSTEM.format(
        subject=subject,
        chapter=chapter,
        concept=concept,
        notes=notes.strip() or "(none yet)",
        explanations="\n".join(f"- {e}" for e in explanations) or "(none yet)",
        language=LANGUAGE_LINE.get(lang, LANGUAGE_LINE["en"]),
    )
    return _call(system, messages, max_tokens=2000, effort="low")


# --- Content drafting for teacher review --------------------------------------------

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "style": {"type": "string", "enum": list(STYLE_GUIDE)},
                    "body": {"type": "string"},
                },
                "required": ["style", "body"],
                "additionalProperties": False,
            },
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["mcq", "numeric"]},
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": "string"},
                    "hints": {"type": "array", "items": {"type": "string"}},
                    "solution": {"type": "string"},
                    "difficulty": {"type": "integer", "enum": [1, 2, 3]},
                    "misconceptions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "wrong_answer": {"type": "string"},
                                "mistake": {"type": "string"},
                            },
                            "required": ["wrong_answer", "mistake"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["kind", "prompt", "options", "answer", "hints", "solution", "difficulty", "misconceptions"],
                "additionalProperties": False,
            },
        },
        "reviewer_notes": {"type": "string"},
    },
    "required": ["explanations", "items", "reviewer_notes"],
    "additionalProperties": False,
}

DRAFT_SYSTEM = """You write learning content for SYNiq, an adaptive learning app used by Class 9 students in Kerala who follow the Kerala State (SCERT) syllabus. A subject teacher reviews and edits everything you write before any student sees it, so flag anything they should check.

Write for 14-year-olds in clear Indian English. Follow the teacher's notes: they describe what the textbook covers and how it presents the topic, so match its methods, notation and level, and do not go beyond it."""

DRAFT_TASK = """Subject: {subject}
Chapter {chapter_number}: {chapter}
Topic: {concept}

Teacher's notes from the textbook:
{notes}

Explanations already approved for this topic (do not repeat them):
{existing}

Please draft:
1. One explanation in each of these styles: {styles}.
{style_guide}
2. {count} practice questions, from easy (difficulty 1) to harder (difficulty 3).
   - "mcq" questions have 3 or 4 options, and the answer must be exactly one of the options.
   - "numeric" questions have no options, and the answer is a single number.
   - Give 2 or 3 hints per question, each revealing a little more.
   - Give a worked solution.
   - For each wrong option or common wrong answer, give the wrong answer and a short snake_case name for the mistake behind it (for example "sign_error").
3. reviewer_notes: anything the teacher should check, such as places where you were unsure the content matches the textbook."""


def draft_content(
    *, subject: str, chapter_number: int, chapter: str, concept: str, notes: str,
    existing: list[str], styles: list[str], count: int,
) -> dict:
    task = DRAFT_TASK.format(
        subject=subject,
        chapter_number=chapter_number,
        chapter=chapter,
        concept=concept,
        notes=notes.strip() or "(none given: keep to the standard Class 9 treatment and say so in reviewer_notes)",
        existing="\n".join(f"- {e}" for e in existing) or "(none)",
        styles=", ".join(styles) or "(none needed)",
        style_guide="\n".join(f'   - "{s}": {STYLE_GUIDE[s]}' for s in styles),
        count=count,
    )
    text = _call(DRAFT_SYSTEM, [{"role": "user", "content": task}], max_tokens=16000, effort="high", schema=DRAFT_SCHEMA)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AIUnavailable("The draft came back incomplete. Please try again.") from e
