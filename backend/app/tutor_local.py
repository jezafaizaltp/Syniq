"""Ask SYNiq without AI: answers from the topic's own approved content.

The tutor works this out first, every time, with no outside call:

- "explain another way", "show me a picture", "an example", "step by step":
  the next of the topic's four explanations the student hasn't seen in this
  chat, starting with the method that works best for them.
- "test me": a question from the topic, checked here. A wrong answer gets a
  hint and another try, then the working, the way the Learn page does.
- "help with this question" / "hint": the question's hints one at a time. For
  the question the student is answering on the Learn page, never the answer.
- "what is ...", "why ...": the sentences in this topic (or another topic of
  the same subject) that cover the words they asked about.

Only when none of that fits is the message handed to the outside AI, if one is
switched on (see app.ai). Otherwise the question is saved, without any student
details, so the content can be added to.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from . import ai, i18n, learning
from .engine import methods
from .models import Chapter, Concept, Decision, Explanation, Item, Misconception, User

STYLES = methods.STYLES
RULE_VERSION = "tutor-1"
ACTIONS = ("explain", "picture", "example", "steps", "test", "hint")
ACTION_STYLE = {"picture": "visual", "example": "real_world", "steps": "step_by_step"}

# --- Reading what the student wrote --------------------------------------------------

_WORD = re.compile(r"[\wऀ-ॿഀ-ൿ]+")
STOP = set(
    """a an the is are was were be been am do does did of to in on at by for from with and or but not no yes it its this that these
    those there here what whats which who whom whose why how when where i me my mine you your we us our they them their he she his her
    can could would should will shall may might must please tell explain explanation mean meaning means define definition describe
    about give show say said know understand dont don't didnt get got just so very really more again some any much many also
    sir miss teacher maam ma'am ok okay hi hello hey thanks thank one two use used using like as if then than into out up down
    syniq answer question help made make makes happen happens work works use uses function role job purpose importance
    important long difference between""".split()
)

INTENTS = [
    ("distress", None),  # handled before anything else, see app.ai
    ("picture", re.compile(r"\b(picture|diagram|draw|drawing|image|figure|visual|see it|show me)\b|ചിത്രം|വരച്ച|chithram", re.I)),
    ("example", re.compile(r"\b(example|real[- ]?life|daily life|everyday|where (is|are) .* used|in life)\b|ഉദാഹരണ|udaharan", re.I)),
    ("steps", re.compile(r"\b(step|steps|step[- ]by[- ]step|how (do|to|can) (i |we )?(solve|do|work|find|calculate|expand|simplify|factori[sz]e|prove|draw|write|get)|method|procedure)\b|ഘട്ട|പടിപടി", re.I)),
    ("test", re.compile(r"\b(test me|quiz|practice|practise|ask me|give me a (question|problem|sum)|another question)\b|ചോദ്യം തരൂ|ടെസ്റ്റ്", re.I)),
    ("hint", re.compile(r"\b(hint|clue|stuck|help me (with|solve)|i can'?t (do|solve)|how (do|should) i (start|begin))\b|സൂചന|sahayikk", re.I)),
    ("answer", re.compile(r"\b(the answer|what('s| is) the answer|solve (it|this)|solution|tell me the answer)\b|ഉത്തരം", re.I)),
    (
        "explain",
        re.compile(
            r"\b(don'?t (get|understand)|didn'?t (get|understand)|not clear|confus|another way|other way|again|simpler|"
            r"easier|explain (it|this|that)|what does (it|this|that) mean|i don'?t know)\b|മനസ്സിലായില്ല|മനസിലായില്ല|വീണ്ടും|manasilayilla|manassilayilla",
            re.I,
        ),
    ),
    ("thanks", re.compile(r"^\s*(thanks|thank you|thank u|thx|ok thanks|got it|i understand( now)?)\W*$|നന്ദി|മനസ്സിലായി\W*$", re.I)),
    ("hello", re.compile(r"^\s*(hi|hello|hey|good (morning|afternoon|evening)|namaskaram)\W*$|^\s*നമസ്കാരം", re.I)),
]


# Malayalam question words and fillers, compared by their start (see stem).
STOP_ML = {w[:6] for w in "എന്താണ് എന്ത് എന്തുകൊണ്ട് എങ്ങനെ ആണ് ആര് ആരാണ് ഏത് ഏതാണ് എന്നാൽ ഒരു ഈ ആ വിശദീകരിക്കൂ പറയൂ പറഞ്ഞുതരൂ എനിക്ക് ഇത് അത് ഉണ്ട് ഇല്ല".split()}


def stem(word: str) -> str:
    w = word.lower()
    if not w.isascii():
        # Malayalam and Hindi add endings to the word itself (കവിതയിൽ, കവിതയുടെ): compare the start.
        return w[:6]
    for suffix in ("ations", "ation", "ings", "ing", "ies", "ed", "es", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return w


def terms(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower()):
        if w in STOP or (w.isascii() and len(w) <= 2):
            continue
        st = stem(w)
        if st not in STOP_ML:
            out.append(st)
    return out


def intent_of(text: str) -> str | None:
    for name, pattern in INTENTS:
        if pattern is not None and pattern.search(text):
            return name
    return None


_SENTENCE = re.compile(r"(?<=[.!?।])\s+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(" ".join((text or "").split())) if len(s.strip()) > 3]


# --- What the topic knows --------------------------------------------------------------

@dataclass
class TopicDoc:
    concept_id: int
    chapter_id: int
    title: str
    chapter_title: str
    chapter_number: int
    sentences: list[tuple[str, set[str]]]  # (sentence, its terms)
    all_terms: set[str]
    title_terms: set[str]


@dataclass
class SubjectIndex:
    stamp: tuple
    topics: dict[int, TopicDoc]
    idf: dict[str, float]


_cache: dict[int, SubjectIndex] = {}


def _stamp(db: DbSession, subject_id: int) -> tuple:
    concept_ids = select(Concept.id).join(Chapter, Chapter.id == Concept.chapter_id).where(Chapter.subject_id == subject_id)
    return (
        db.scalar(select(func.count(Concept.id)).where(Concept.id.in_(concept_ids))),
        db.scalar(select(func.max(Explanation.id)).where(Explanation.concept_id.in_(concept_ids))),
        db.scalar(select(func.count(Explanation.id)).where(Explanation.concept_id.in_(concept_ids), Explanation.status == "approved")),
    )


def subject_index(db: DbSession, subject_id: int) -> SubjectIndex:
    stamp = _stamp(db, subject_id)
    cached = _cache.get(subject_id)
    if cached and cached.stamp == stamp:
        return cached
    topics: dict[int, TopicDoc] = {}
    rows = db.execute(
        select(Concept, Chapter).join(Chapter, Chapter.id == Concept.chapter_id).where(Chapter.subject_id == subject_id)
    ).all()
    ids = [c.id for c, _ in rows]
    exps: dict[int, list[Explanation]] = {}
    for e in db.scalars(select(Explanation).where(Explanation.concept_id.in_(ids), Explanation.status == "approved")).all():
        exps.setdefault(e.concept_id, []).append(e)
    worked: dict[int, list[str]] = {}
    for it in db.scalars(select(Item).where(Item.concept_id.in_(ids), Item.status == "approved")).all():
        if it.solution:
            worked.setdefault(it.concept_id, []).append(it.solution)
    for concept, chapter in rows:
        # Notes and the plain-words explanation first: they read best as an answer.
        order = sorted(exps.get(concept.id, []), key=lambda e: ["text", "step_by_step", "real_world", "visual"].index(e.style) if e.style in STYLES else 9)
        texts = [concept.notes] + [e.body for e in order] + worked.get(concept.id, [])[:4]
        sents, seen = [], set()
        for text in texts:
            for s in sentences(text):
                if s not in seen:
                    seen.add(s)
                    sents.append((s, set(terms(s))))
        title_terms = set(terms(concept.title))
        all_terms = set().union(title_terms, *(t for _, t in sents)) if sents else title_terms
        topics[concept.id] = TopicDoc(concept.id, chapter.id, concept.title, chapter.title, chapter.number, sents, all_terms, title_terms)
    n = max(1, len(topics))
    df: dict[str, int] = {}
    for doc in topics.values():
        for term in doc.all_terms:
            df[term] = df.get(term, 0) + 1
    idf = {term: math.log(1 + n / c) for term, c in df.items()}
    index = SubjectIndex(stamp, topics, idf)
    _cache[subject_id] = index
    return index


_WHAT = re.compile(
    r"^\s*(?:what|who)\s+(?:is|are|was|were|does|do)\s+(?:an?\s+|the\s+)?(.+?)\s*(?:mean|do|does|work|stand for)?\s*\??\s*$", re.I
)


# Chat with the tutor itself, not a question about the lesson.
CHAT = re.compile(r"\b(your|yourself|are you|who made you|joke|play (a )?game|bored|love you|my name)\b", re.I)


_WHAT_ML = re.compile(r"^\s*(.+?)\s*(?:എന്നാൽ എന്ത്|എന്താണ്|എന്ത്|എന്നാലെന്ത്)\s*\??\s*$")


def what_about(question: str) -> str | None:
    """The thing a "what is ..." question asks about: "what is the normal?" -> "normal"."""
    m = _WHAT.match(question) or _WHAT_ML.match(question)
    return m.group(1).strip() if m and len(m.group(1)) < 60 else None


@dataclass
class Found:
    doc: TopicDoc
    coverage: float
    text: str


def _weight(index: SubjectIndex, term: str) -> float:
    # A word that appears nowhere in the subject still counts, as the most specific kind.
    return index.idf.get(term, math.log(1 + len(index.topics)) + 1)


def coverage(index: SubjectIndex, doc: TopicDoc, q: list[str]) -> float:
    total = sum(_weight(index, t) for t in q)
    hit = sum(_weight(index, t) for t in q if t in doc.all_terms)
    return hit / total if total else 0.0


def find(index: SubjectIndex, concept_id: int, chapter_id: int, question: str) -> Found | None:
    q = list(dict.fromkeys(terms(question)))
    if not q:
        return None
    here = index.topics.get(concept_id)

    def rank(doc: TopicDoc) -> tuple:
        c = coverage(index, doc, q)
        title = sum(_weight(index, t) for t in q if t in doc.title_terms)
        return (round(c, 3), doc.concept_id == concept_id, doc.chapter_id == chapter_id, title)

    best = max(index.topics.values(), key=rank, default=None)
    # Stay on this topic when it covers the question about as well as anywhere else.
    if here and best and coverage(index, here, q) >= coverage(index, best, q) - 0.1:
        best = here
    if not best:
        return None
    cov = coverage(index, best, q)
    if cov < 0.6:
        return None
    subject_words = what_about(question)
    defines = (
        re.compile(
            rf"\b{re.escape(subject_words)}\b\s*(\(|,\s*the\b|is\b|are\b|means\b|refers\b|:)|\b(called|known as|is named)\s+(the\s+)?{re.escape(subject_words)}\b",
            re.I,
        )
        if subject_words
        else None
    )
    maths_here = best.concept_id == concept_id and bool(re.search(r"\d", q[0]))
    if not subject_words and len(q) == 1 and q[0] not in best.title_terms and not maths_here:
        # One word to go on ("where is bile made?") is too little to be sure which sentence answers it.
        return None
    if subject_words:
        # "What is X?" is only answered when the content says what X is, or X is what the topic is about.
        named = set(terms(subject_words))
        says_it = any(defines.search(s) for s, _ in best.sentences)
        about_topic = bool(named) and named <= best.title_terms
        # Or this topic or chapter mentions it in one sentence, so it's part of what the student is learning now.
        nearby = best.chapter_id == chapter_id and bool(named) and any(named <= ts for _, ts in best.sentences)
        if not (says_it or about_topic or nearby):
            return None
    scored = []
    for i, (s, ts) in enumerate(best.sentences):
        score = sum(_weight(index, t) for t in q if t in ts)
        if score:
            # A sentence that says what the thing asked about is answers "what is" questions best.
            if defines and defines.search(s):
                score *= 2
            elif re.search(r"\b(is|are|means|called)\b", s):
                score *= 1.15
            scored.append((score, -i, s))
    if not scored:
        if not set(q) <= best.title_terms or not best.sentences:
            return None
        # The question names the topic itself: start from the top of its notes.
        scored = [(1.0, -i, s) for i, (s, _) in enumerate(best.sentences[:2])]
    scored.sort(reverse=True)
    picked = sorted(scored[:2], key=lambda x: -x[1])
    # Keep the answer short: two sentences, or one if it already covers every word asked about.
    first_terms = {t for t in q if t in set(terms(picked[0][2]))}
    if len(picked) > 1 and first_terms >= set(q):
        picked = [max(picked, key=lambda x: x[0])]
    out = []
    for _, neg_i, s in picked:
        i = -neg_i
        # "This is called ..." needs the sentence before it to make sense on its own.
        if i > 0 and re.match(r"(this|that|it|these|such|so|then)\b", s, re.I):
            prev = best.sentences[i - 1][0]
            if prev not in out:
                out.append(prev)
        if s not in out:
            out.append(s)
    return Found(best, cov, " ".join(out))


# --- Replying ------------------------------------------------------------------------

@dataclass
class Reply:
    text: str
    source: str = "notes"  # notes | ai | none
    picture: dict | None = None
    style: str | None = None
    quiz: dict | None = None
    chips: list[str] = field(default_factory=lambda: ["explain", "picture", "example", "steps", "test"])
    state: dict = field(default_factory=dict)
    unanswered: bool = False


def _explanations(db: DbSession, concept_id: int) -> dict[str, Explanation]:
    rows = db.scalars(select(Explanation).where(Explanation.concept_id == concept_id, Explanation.status == "approved")).all()
    return {e.style: e for e in rows}


def _next_style(db: DbSession, user: User, concept_id: int, shown: list[str], available: list[str]) -> str | None:
    pool = [s for s in available if s not in shown]
    if not pool:
        return None
    mastery = learning.get_mastery(db, user.id, concept_id)
    prior = learning.method_priors(db, user.id, [concept_id]).get(concept_id)
    best, _ = methods.choose([s for s in STYLES if s not in pool], mastery.format_stats, prior)
    return best if best in pool else pool[0]


def explain(db: DbSession, user: User, concept: Concept, lang: str, state: dict, style: str | None) -> Reply:
    exps = _explanations(db, concept.id)
    shown = list(state.get("shown", []))
    if style is None:
        style = _next_style(db, user, concept.id, shown, list(exps))
        if style is None:
            return Reply(i18n.t(lang, "tutor.local.all_seen", topic=concept.title), state={**state, "shown": []})
    exp = exps.get(style)
    if exp is None:
        return Reply(i18n.t(lang, "tutor.local.clarify"), state=state)
    picture = exp.picture if style == "visual" else None
    # Logged like the Learn page's explanations, so the next few answers count towards this method
    # and SYNiq learns which way of explaining works for this student.
    db.add(
        Decision(
            student_id=user.id, concept_id=concept.id, rule_id="T_tutor_explain", rule_version=RULE_VERSION, action="explain",
            reason=f"The student asked Ask SYNiq for the {style} explanation.", evidence={"style": style, "from": "tutor"},
        )
    )
    db.commit()
    text = f"{i18n.t(lang, f'tutor.local.lead.{style}')} {exp.body}\n\n{i18n.t(lang, 'tutor.local.check')}"
    rest = [a for a, s in (("picture", "visual"), ("example", "real_world"), ("steps", "step_by_step")) if s != style and s in exps]
    return Reply(text, picture=picture, style=style, chips=["test", *rest, "explain"], state={**state, "shown": [*shown, style]})


def _public(item: Item) -> dict:
    return {"prompt": item.prompt, "options": learning.shuffled_options(item)}


def quiz(db: DbSession, user: User, concept: Concept, lang: str, state: dict) -> Reply:
    mastery = learning.get_mastery(db, user.id, concept.id)
    target = 1 if mastery.p_known < 0.4 else 2 if mastery.p_known < 0.75 else 3
    item = learning.pick_item(db, user.id, concept.id, target)
    if not item:
        return Reply(i18n.t(lang, "tutor.local.no_questions"), state=state)
    return Reply(
        f"{i18n.t(lang, 'tutor.local.try_this')} {item.prompt}",
        quiz=_public(item), chips=["hint"], state={**state, "quiz": item.id, "tries": 0, "hints": 0},
    )


def _tip(db: DbSession, lang: str, item: Item, response: str) -> str | None:
    for wrong, tag in (item.misconceptions or {}).items():
        if learning.same_answer(wrong, response):
            key = f"tip.{tag}"
            if i18n.has(key):
                return i18n.t(lang, key)
            row = db.scalars(select(Misconception).where(Misconception.tag == tag)).first()
            return row.tip if row else None
    return None


def check_quiz(db: DbSession, item: Item, lang: str, state: dict, response: str) -> Reply:
    tries = int(state.get("tries", 0)) + 1
    if learning.same_answer(response, item.answer):
        text = i18n.t(lang, "tutor.local.right") + (f" {item.solution}" if item.solution else "")
        return Reply(text, chips=["test", "explain"], state={k: v for k, v in state.items() if k not in ("quiz", "tries", "hints")})
    tip = _tip(db, lang, item, response)
    hints = item.hints or []
    if tries == 1 and (tip or hints):
        # First miss: the student's answer next to a nudge, then another go. Never the answer yet.
        nudge = tip or hints[0]
        text = i18n.t(lang, "tutor.local.not_yet", yours=response, nudge=nudge)
        used = int(state.get("hints", 0)) if tip else max(1, int(state.get("hints", 0)))
        return Reply(text, quiz=_public(item), chips=["hint"], state={**state, "tries": tries, "hints": used})
    # Second miss: the mistake becomes the way in. Their answer, the right one, and the working.
    text = i18n.t(lang, "tutor.local.reveal", yours=response, right=item.answer) + (f" {item.solution}" if item.solution else "")
    if tip:
        text += f"\n\n{tip}"
    return Reply(text, chips=["test", "explain", "steps"], state={k: v for k, v in state.items() if k not in ("quiz", "tries", "hints")})


def hint(db: DbSession, item: Item, lang: str, state: dict, protect: bool, asked_answer: bool = False) -> Reply:
    """The next hint. Once they've all been given, the working, except for a question being marked on the Learn page."""
    n = int(state.get("hints", 0))
    hints = item.hints or []
    if n < len(hints):
        text = i18n.t(lang, "tutor.local.hint", n=n + 1, hint=hints[n])
        if asked_answer:
            text = i18n.t(lang, "tutor.local.hint_first") + " " + text
        return Reply(text, chips=["hint", "steps"] if n + 1 < len(hints) else ["steps"], state={**state, "hints": n + 1})
    if protect:
        return Reply(i18n.t(lang, "tutor.local.try_it"), chips=["steps", "picture"], state=state)
    text = i18n.t(lang, "tutor.local.working", solution=item.solution or item.answer)
    return Reply(text, chips=["test", "explain"], state={k: v for k, v in state.items() if k != "item"})


def _matching_item(db: DbSession, concept: Concept, text: str) -> Item | None:
    """A practice question the student has typed or pasted, from this chapter."""
    q = set(terms(text))
    if len(q) < 5:
        return None
    items = db.scalars(
        select(Item).join(Concept, Concept.id == Item.concept_id).where(Concept.chapter_id == concept.chapter_id, Item.status == "approved")
    ).all()
    best, score = None, 0.0
    for it in items:
        p = set(terms(it.prompt))
        if not p:
            continue
        s = len(q & p) / len(q | p)
        if s > score:
            best, score = it, s
    return best if score >= 0.6 else None


def reply(
    db: DbSession, user: User, concept: Concept, text: str, lang: str, *, action: str | None = None,
    state: dict | None = None, current_item_id: int | None = None,
) -> Reply | None:
    """SYNiq's own answer, or None when the content doesn't cover it (then the outside AI may help)."""
    state = dict(state or {})
    if state.get("concept") != concept.id:
        state = {"concept": concept.id}
    # Without contact details first, so "anu@example.com" doesn't read as asking for an example.
    text = ai.scrub(text).strip()

    # 1. An answer to the question the tutor just asked.
    pending = db.get(Item, state["quiz"]) if state.get("quiz") else None
    if pending and action is None and len(text) <= 60 and (intent_of(text) is None or text in (pending.options or [])):
        return check_quiz(db, pending, lang, state, text)
    if pending and action == "hint":
        return hint(db, pending, lang, state, protect=True)

    kind = action or intent_of(text)
    if kind in ("picture", "example", "steps"):
        return explain(db, user, concept, lang, state, ACTION_STYLE[kind])
    if kind == "explain":
        return explain(db, user, concept, lang, state, None)
    if kind == "test":
        return quiz(db, user, concept, lang, state)
    if kind == "hello":
        return Reply(i18n.t(lang, "tutor.local.hello", topic=concept.title), state=state)
    if kind == "thanks":
        return Reply(i18n.t(lang, "tutor.local.thanks", topic=concept.title), chips=["test", "explain"], state=state)

    # 2. Help with a question: the one on the Learn page, one they pasted, or the last one discussed.
    current = db.get(Item, current_item_id) if current_item_id else None
    pasted = _matching_item(db, concept, text)
    if pasted:
        state = {**state, "item": pasted.id, "hints": 0} if state.get("item") != pasted.id else state
    item = pasted or (db.get(Item, state["item"]) if state.get("item") else None) or current
    if kind in ("hint", "answer") or pasted:
        if item is None:
            return Reply(i18n.t(lang, "tutor.local.which_question"), chips=["test", "steps"], state=state)
        protect = current is not None and item.id == current.id
        if item.id != state.get("item"):
            state = {**state, "item": item.id, "hints": 0}
        return hint(db, item, lang, state, protect=protect, asked_answer=kind == "answer")

    # 3. "What is ...", "why ...": the topic's own sentences.
    if CHAT.search(text):
        return None
    found = find(subject_index(db, concept_chapter_subject(db, concept)), concept.id, concept.chapter_id, text)
    if found:
        out = found.text
        if found.doc.concept_id != concept.id:
            out += "\n\n" + i18n.t(lang, "tutor.local.elsewhere", topic=found.doc.title, chapter=found.doc.chapter_number)
        out += "\n\n" + i18n.t(lang, "tutor.local.follow_up")
        return Reply(out, chips=["explain", "picture", "example", "test"], state=state)
    if not terms(text):
        # Nothing to look up (symbols, "this?", "hmm"): explain the topic another way.
        return explain(db, user, concept, lang, state, None)
    return None


def concept_chapter_subject(db: DbSession, concept: Concept) -> int:
    return db.get(Chapter, concept.chapter_id).subject_id


def unsure(concept: Concept, lang: str, state: dict) -> Reply:
    return Reply(
        i18n.t(lang, "tutor.local.unsure", topic=concept.title), source="none",
        chips=["explain", "picture", "example", "steps", "test"], state=state, unanswered=True,
    )
