"""Simulated learners on the Kerala Class 9 lab install.

Each simulated learner has hidden knowledge of every topic and a way of learning
(which explanations and which kinds of help after a mistake teach them most).
They use the real app through its API, exactly as the browser does, over a few
weeks of lab periods with days off in between. The same learner also goes
through a fixed version (text explanation, six questions per topic, move on)
with the same number of steps, so the two can be compared.

This checks the ENGINE, not real children: the learners behave the way this file
says learners behave. It answers questions like "does SYNiq find the way a child
learns", "does it ever call a topic secure when the child doesn't know it",
"does anyone get stuck". Whether real children learn more is for the pilot.

Run one seed (a fresh database each time):
    python -m tools.learner_sim --seed 1 --out /tmp/sim-1.json
Then summarise several runs:
    python -m tools.learner_sim --summarise /tmp/sim-*.json
"""

import argparse
import glob
import json
import math
import os
import random
import statistics
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import timedelta

if "--summarise" not in sys.argv:
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/sim.db"

STYLES = ["text", "visual", "step_by_step", "real_world"]
# What each kind of help after a mistake mostly is, for the learner model.
MODE_STYLE = {"count_it_out": "visual", "step_by_step": "step_by_step", "real_life": "real_world", "try_similar": "text"}

# Kerala Class 9: (subject code, chapter number). Two Maths chapters, Physics, Biology, Social Science.
CHAPTERS = [("math", 1), ("phy", 1), ("math", 2), ("bio", 1), ("ss", 1)]
SITTINGS = 15  # lab periods
STEPS = 30  # explanations read + questions answered per period
DAYS_BETWEEN = [1, 2, 1, 3]  # school week rhythm, repeating
DELAYED_DAYS = 14  # retention test this long after the last period
# SIM_TAPS=0 turns off the learners' "did this help?" answers.
TAPS = os.environ.get("SIM_TAPS", "1") != "0"

# SIM_TERM=1: a whole term. Ten chapters taught in order, 40 lab periods; each subject's chapter moves on
# every third time that subject comes round, as a teacher's plan would.
TERM = os.environ.get("SIM_TERM") == "1"
if TERM:
    CHAPTERS = [("math", 1), ("math", 2), ("math", 3), ("math", 4), ("phy", 1), ("phy", 2), ("chem", 1), ("chem", 2),
                ("bio", 1), ("ss", 1)]
    SITTINGS = 40
SUBJECT_ROUND = ["math", "phy", "chem", "math", "bio", "ss"]


def todays_chapter(period: int) -> int:
    """Index into CHAPTERS of the chapter the class works on in this period."""
    if not TERM:
        return period % len(CHAPTERS)
    subject = SUBJECT_ROUND[period % len(SUBJECT_ROUND)]
    visit = sum(1 for p in range(period) if SUBJECT_ROUND[p % len(SUBJECT_ROUND)] == subject)
    mine = [i for i, (code, _) in enumerate(CHAPTERS) if code == subject]
    return mine[min(visit // 3, len(mine) - 1)]


@dataclass
class Kind:
    """How one kind of learner learns. Nothing here is a label shown to anyone."""

    key: str
    name: str
    about: str
    start: float  # what they already know of a new topic (0..1)
    gain: dict  # how much one explanation in each style teaches (share of the gap closed)
    slip: float  # chance of a slip when they do know it
    trap: float  # extra chance of falling into a question's trap
    focus: int  # questions in a period before attention starts to drop
    hints_below: float  # asks for a hint when they feel less sure than this
    takes_breaks: bool = True
    absent: float = 0.0  # chance of missing a lab period


KINDS = [
    Kind("pictures", "Meera", "learns best from pictures and diagrams; long text explanations don't stick",
         0.25, {"text": 0.06, "visual": 0.40, "step_by_step": 0.15, "real_world": 0.15}, 0.08, 0.10, 25, 0.3),
    Kind("steps", "Arjun", "slow and careful; needs it one step at a time, learns slowly overall",
         0.15, {"text": 0.08, "visual": 0.12, "step_by_step": 0.32, "real_world": 0.10}, 0.06, 0.10, 30, 0.4),
    Kind("careless", "Zara", "quick, already knows a lot, but rushes and falls into traps",
         0.45, {"text": 0.30, "visual": 0.22, "step_by_step": 0.18, "real_world": 0.22}, 0.15, 0.35, 30, 0.0),
    Kind("real_life", "Vishnu", "finds reading hard and starts with gaps; learns from everyday examples; attention fades",
         0.08, {"text": 0.03, "visual": 0.18, "step_by_step": 0.12, "real_world": 0.34}, 0.10, 0.15, 12, 0.5),
    # A control: every way of explaining works equally. Adapting can't help here; it must not hurt.
    Kind("any_way", "Control", "control learner: every way of explaining works the same",
         0.25, {s: 0.20 for s in STYLES}, 0.08, 0.10, 25, 0.3),
    Kind("strong", "Ammu", "already strong: knows much of it and learns fast from any explanation",
         0.60, {"text": 0.40, "visual": 0.35, "step_by_step": 0.30, "real_world": 0.35}, 0.04, 0.05, 40, 0.0),
    Kind("absent", "Rahul", "learns like the control, but misses about 4 periods in 10",
         0.25, {s: 0.20 for s in STYLES}, 0.08, 0.10, 25, 0.3, absent=0.4),
]


@dataclass
class Topic:
    k: float  # hidden knowledge, 0..1
    floor: float
    strength: float = 0.0  # how well it is held in memory
    last_day: float | None = None


@dataclass
class Learner:
    kind: Kind
    rng: random.Random
    topics: dict = field(default_factory=dict)  # concept id -> Topic
    traps: dict = field(default_factory=dict)  # misconception tag -> tendency (1 = full)
    day: float = 0.0
    in_period: int = 0  # questions answered this period, for attention

    def topic(self, cid: int) -> Topic:
        if cid not in self.topics:
            s = max(0.0, min(1.0, self.rng.gauss(self.kind.start, 0.08)))
            self.topics[cid] = Topic(k=s, floor=s)
        return self.topics[cid]

    def learn(self, cid: int, amount: float) -> None:
        t = self.topic(cid)
        t.k += amount * (1 - t.k)

    def read(self, cid: int, style: str) -> None:
        self.learn(cid, self.kind.gain[style])

    def rest_days(self, days: float) -> None:
        """Forgetting: knowledge slides back towards what they started with, slower once it's held."""
        self.day += days
        for t in self.topics.values():
            hold = 4.0 * (1 + 0.6 * t.strength)
            t.k = t.floor + (t.k - t.floor) * math.exp(-days / hold)
        self.in_period = 0

    def p_correct(self, item, cid: int, watch_out: bool = False, hints: int = 0, attention: bool = True) -> float:
        t = self.topic(cid)
        k = max(0.0, min(1.0, t.k - 0.12 * (item.difficulty - 2) + 0.15 * hints))
        slip = self.kind.slip
        if item.misconceptions:
            tendency = max(self.traps.get(tag, 1.0) for tag in item.misconceptions.values())
            slip += self.kind.trap * tendency * (0.4 if watch_out else 1.0)
        know = k * (1 - min(slip, 0.9))
        guess = 1 / max(2, len(item.options)) if item.kind == "mcq" else 0.02
        p = know + (1 - know) * guess
        if attention:
            lapse = min(0.5, max(0, self.in_period - self.kind.focus) * 0.03)
            p = p * (1 - lapse) + lapse * guess
        return p

    def answer(self, item, cid: int, options: list | None, watch_out: bool) -> tuple[str, int]:
        hints = 1 if item.hints and self.topic(cid).k < self.kind.hints_below else 0
        right = self.rng.random() < self.p_correct(item, cid, watch_out, hints)
        self.in_period += 1
        if right:
            return item.answer, hints
        traps = list((item.misconceptions or {}).keys())
        if traps and self.rng.random() < 0.7:
            return self.rng.choice(traps), hints
        wrong = [o for o in (options or item.options or []) if o.strip().lower() != item.answer.strip().lower()]
        if wrong:
            return self.rng.choice(wrong), hints
        return "0" if item.answer != "0" else "1", hints

    def after(self, item, cid: int, correct: bool, help_style: str | None, tip_shown: bool, watch_out: bool) -> None:
        t = self.topic(cid)
        if correct:
            self.learn(cid, 0.04)
            spaced = t.last_day is None or self.day - t.last_day >= 1
            t.strength += 1.0 if spaced else 0.15
            if watch_out:
                for tag in (item.misconceptions or {}).values():
                    self.traps[tag] = self.traps.get(tag, 1.0) * 0.7
        else:
            self.learn(cid, 0.04 + (0.4 * self.kind.gain[help_style] if help_style else 0))
            for tag in (item.misconceptions or {}).values():
                self.traps[tag] = self.traps.get(tag, 1.0) * (0.85 if tip_shown else 0.97)
        t.last_day = self.day


def test_score(learner: Learner, items_by_concept: dict) -> float:
    """Expected mark on every question of the chosen chapters, with no hints and full attention. Nothing is learnt."""
    ps = [learner.p_correct(i, cid, attention=False) for cid, items in items_by_concept.items() for i in items]
    return 100 * sum(ps) / len(ps)


def run(seed: int) -> dict:
    from fastapi.testclient import TestClient

    from app import models
    from app.db import SessionLocal
    from app.main import app
    from app.models import (
        Chapter,
        Concept,
        Consent,
        Decision,
        Item,
        Mastery,
        Subject,
        User,
    )
    from app.seed import DEMO_PASSWORD
    from app.seed import seed as seed_db

    # A clock the simulation moves forward between lab periods (reviews and forgetting need days to pass).
    clock = {"offset": timedelta(0)}
    models._SIM_CLOCK = clock
    models.timedelta = timedelta

    def _now():
        return datetime.now(timezone.utc).replace(tzinfo=None) + _SIM_CLOCK["offset"]  # noqa: F821

    models.utcnow.__code__ = _now.__code__

    # Engine settings to try without changing the code: SIM_P_TRANSIT=0.1 SIM_MIN_ATTEMPTS=5
    from app.engine import mastery
    if os.environ.get("SIM_P_TRANSIT"):
        mastery.P_TRANSIT = float(os.environ["SIM_P_TRANSIT"])
    if os.environ.get("SIM_MIN_ATTEMPTS"):
        mastery.MIN_ATTEMPTS_TO_SECURE = int(os.environ["SIM_MIN_ATTEMPTS"])
    if os.environ.get("SIM_SECURE"):
        mastery.SECURE_THRESHOLD = float(os.environ["SIM_SECURE"])
    if os.environ.get("SIM_REVIEW_DAYS"):
        mastery.REVIEW_INTERVALS_DAYS = [int(x) for x in os.environ["SIM_REVIEW_DAYS"].split(",")]
    if os.environ.get("SIM_CAPS"):
        from app.engine import methods
        methods.CAPS.update(subject=float(os.environ["SIM_CAPS"]), overall=float(os.environ["SIM_CAPS"]))

    random.seed(seed)
    with SessionLocal() as db:
        seed_db(db)
        guardian = db.query(User).filter_by(email="parent@demo.syniq").one()
        group_id = db.query(User).filter_by(email="anu@demo.syniq").one().class_group_id
        chapters = []
        for code, number in CHAPTERS:
            subj = db.query(Subject).filter_by(code=code).one()
            ch = db.query(Chapter).filter_by(subject_id=subj.id, number=number).one()
            chapters.append((ch.id, f"{subj.name} {number}: {ch.title}"))
        concept_ids = {ch_id: [c.id for c in db.query(Concept).filter_by(chapter_id=ch_id).order_by(Concept.order)] for ch_id, _ in chapters}
        items = {i.id: i for i in db.query(Item).filter(Item.status == "approved").all() if any(i.concept_id in v for v in concept_ids.values())}
        for i in items.values():
            db.expunge(i)
        users = {}
        for kind in KINDS:
            u = User(name=kind.name, email=f"sim-{kind.key}@demo.syniq", password_hash=guardian.password_hash, role="student", class_group_id=group_id, settings={})
            db.add(u)
            db.flush()
            db.add(Consent(student_id=u.id, guardian_id=guardian.id, scope="core_learning", granted=True, method="school_form"))
            users[kind.key] = u.id
        db.commit()
    items_by_concept: dict = {}
    for i in items.values():
        items_by_concept.setdefault(i.concept_id, []).append(i)
    concept_title = {}
    with SessionLocal() as db:
        for ids in concept_ids.values():
            for cid in ids:
                concept_title[cid] = db.get(Concept, cid).title

    client = TestClient(app)
    out = {"seed": seed, "chapters": [t for _, t in chapters], "learners": {}}

    for kind in KINDS:
        syn = Learner(kind, random.Random(f"{seed}-{kind.key}-learner"))
        fixed = Learner(kind, random.Random(f"{seed}-{kind.key}-learner"))  # the same child, a second time
        for cid in concept_title:
            syn.topic(cid)
            fixed.topic(cid)
        pre = test_score(syn, items_by_concept)
        clock["offset"] = timedelta(0)
        log = {"styles_read": [], "help_modes": [], "false_secure": 0, "secure_events": 0, "steps": 0, "questions": 0,
               "right": 0, "repeats_in_period": 0, "stuck": [], "breaks": 0, "watch_out": 0, "rules": {}}
        fixed_state = {"pos": {ch: 0 for ch, _ in chapters}}
        secured: set = set()
        day = 0.0
        email = f"sim-{kind.key}@demo.syniq"
        absent_rng = random.Random(f"{seed}-{kind.key}-absent")
        for period in range(SITTINGS):
            today = todays_chapter(period)
            ch_id, _ = chapters[today]
            if absent_rng.random() < kind.absent:
                log["missed"] = log.get("missed", 0) + 1
                gap = DAYS_BETWEEN[period % len(DAYS_BETWEEN)]
                day += gap
                clock["offset"] = timedelta(days=day)
                syn.rest_days(gap)
                fixed.rest_days(gap)
                continue
            token = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD}).json()["token"]
            h = {"Authorization": f"Bearer {token}"}
            current = None
            seen_items: set = set()
            per_concept_steps: dict = {}
            ch_order = [c for c, _ in chapters]
            ch_idx = ch_order.index(ch_id)
            steps = 0
            while steps < STEPS:
                r = client.post("/learn/next", json={"chapter_id": ch_id, "current_concept_id": current}, headers=h)
                assert r.status_code == 200, r.text
                s = r.json()
                with SessionLocal() as db:
                    rule = db.get(Decision, s["decision_id"]).rule_id
                log["rules"][rule] = log["rules"].get(rule, 0) + 1
                if s["kind"] == "chapter_complete":
                    # Done with today's chapter: carry on with the next one, as a student would.
                    ch_idx = (ch_idx + 1) % len(ch_order)
                    ch_id = ch_order[ch_idx]
                    current = None
                    if ch_idx == today:
                        break
                    continue
                cid = s["concept"]["id"]
                current = cid
                steps += 1
                per_concept_steps[cid] = per_concept_steps.get(cid, 0) + 1
                if s["kind"] == "explain":
                    run = log["explain_run"] = log.get("explain_run", 0) + 1
                    log["max_explain_run"] = max(log.get("max_explain_run", 0), run)
                    style = s["explanation"]["style"]
                    syn.read(cid, style)
                    # About half the time they answer "did this way help?", and not always accurately.
                    if TAPS and syn.rng.random() < 0.5:
                        helped = syn.rng.random() < min(0.9, 0.2 + 1.5 * kind.gain[style])
                        client.post("/learn/explanation-feedback", json={"concept_id": cid, "style": style, "helped": helped}, headers=h)
                    log["styles_read"].append(style)
                    if rule == "R4_introduce":
                        log.setdefault("first_styles", []).append(style)
                    continue
                log["explain_run"] = 0
                item_pub = s["item"]
                if not item_pub:
                    log["stuck"].append(f"no question for {concept_title[cid]}")
                    break
                item = items[item_pub["id"]]
                if item.id in seen_items:
                    log["repeats_in_period"] += 1
                seen_items.add(item.id)
                watch = bool(item_pub.get("watch_out"))
                log["watch_out"] += watch
                if syn.topic(cid).k > 0.9:
                    log["known_answers"] = log.get("known_answers", 0) + 1
                resp, hints = syn.answer(item, cid, item_pub.get("options"), watch)
                for n in range(1, hints + 1):
                    client.get(f"/items/{item.id}/hints/{n}", headers=h)
                a = client.post("/learn/attempts", json={"item_id": item.id, "response": resp, "hints_used": hints}, headers=h).json()
                log["questions"] += 1
                log["right"] += a["correct"]
                mode = a["response"].get("mode")
                if mode:
                    log["help_modes"].append(mode)
                syn.after(item, cid, a["correct"], MODE_STYLE.get(mode) if mode else None, bool(a.get("tip")), watch)
                if a["progress"] == "secure" and cid not in secured:
                    secured.add(cid)
                    log["secure_events"] += 1
                    if syn.topic(cid).k < 0.7:
                        log["false_secure"] += 1
                if a.get("offer_break") and kind.takes_breaks:
                    log["breaks"] += 1
                    syn.in_period = max(0, syn.in_period - 10)
            if max(per_concept_steps.values(), default=0) >= STEPS:
                log["stuck"].append(f"whole period on one topic (period {period + 1})")
            log["steps"] += steps
            log["idle"] = log.get("idle", 0) + (STEPS - steps)

            # The fixed version: same child, same period, same chapter, same number of steps.
            run_fixed_period(fixed, chapters[today][0], concept_ids, items_by_concept, fixed_state)

            gap = DAYS_BETWEEN[period % len(DAYS_BETWEEN)]
            day += gap
            clock["offset"] = timedelta(days=day)
            syn.rest_days(gap)
            fixed.rest_days(gap)

        post_syn, post_fixed = test_score(syn, items_by_concept), test_score(fixed, items_by_concept)
        syn.rest_days(DELAYED_DAYS)
        fixed.rest_days(DELAYED_DAYS)
        late_syn, late_fixed = test_score(syn, items_by_concept), test_score(fixed, items_by_concept)

        with SessionLocal() as db:
            rows = db.query(Mastery).filter_by(student_id=users[kind.key]).all()
            est = {r.concept_id: (r.p_known, r.attempts) for r in rows}
        # How well SYNiq's own estimate matches the hidden truth, topic by topic (before the delayed gap).
        best = max(kind.gain, key=kind.gain.get)
        half = log["styles_read"][len(log["styles_read"]) // 2:]
        out["learners"][kind.key] = {
            "name": kind.name,
            "about": kind.about,
            "best_style": best,
            "pre": round(pre, 1),
            "post": round(post_syn, 1),
            "delayed": round(late_syn, 1),
            "fixed_post": round(post_fixed, 1),
            "fixed_delayed": round(late_fixed, 1),
            "share_best_style_all": round(log["styles_read"].count(best) / max(1, len(log["styles_read"])), 2),
            "share_best_first": round(log.get("first_styles", []).count(best) / max(1, len(log.get("first_styles", []))), 2),
            "share_best_style_late": round(half.count(best) / max(1, len(half)), 2),
            "styles_read": {s: log["styles_read"].count(s) for s in STYLES},
            "help_modes": {m: log["help_modes"].count(m) for m in MODE_STYLE},
            "questions": log["questions"],
            "right_pct": round(100 * log["right"] / max(1, log["questions"]), 1),
            "topics_secured": len(secured),
            "topics": len(concept_title),
            "false_secure": log["false_secure"],
            "repeats_in_period": log["repeats_in_period"],
            "watch_out": log["watch_out"],
            "breaks": log["breaks"],
            "stuck": log["stuck"],
            "rules": log["rules"],
            "topics_reached": len(est),
            "idle_steps": log.get("idle", 0),
            "missed": log.get("missed", 0),
            "known_answers": log.get("known_answers", 0),
            "max_explain_run": log.get("max_explain_run", 0),
            "other_reviews": log["rules"].get("R3_other_chapter", 0),
            "reviews": log["rules"].get("R3_spaced_review", 0),
            "secure_end": sum(1 for p, n in est.values() if mastery.is_secure(p, n)),
        }
    return out


def run_fixed_period(learner: Learner, ch_id: int, concept_ids: dict, items_by_concept: dict, state: dict) -> None:
    """No adapting: the text explanation, then six questions of any level, then the next topic, round and round."""
    ids = concept_ids[ch_id]
    steps = 0
    while steps < STEPS:
        cid = ids[state["pos"][ch_id] % len(ids)]
        learner.read(cid, "text")
        steps += 1
        pool = items_by_concept.get(cid, [])
        for item in learner.rng.sample(pool, min(6, len(pool))):
            if steps >= STEPS:
                break
            resp, _ = learner.answer(item, cid, item.options, False)
            correct = resp == item.answer
            # The answer and its worked solution are shown; no tip about the trap, no other way of explaining.
            learner.after(item, cid, correct, "text" if not correct else None, False, False)
            steps += 1
        state["pos"][ch_id] += 1


def summarise(paths: list[str]) -> None:
    runs = []
    for p in paths:
        with open(p) as f:
            runs.append(json.load(f))
    print(f"{len(runs)} runs (seeds {', '.join(str(r['seed']) for r in runs)})")
    print("Chapters:", "; ".join(runs[0]["chapters"]))
    keys = list(runs[0]["learners"])
    for key in keys:
        rs = [r["learners"][key] for r in runs]

        def m(field_, rs=rs):
            return round(statistics.mean(x[field_] for x in rs), 1)

        print(f"\n{rs[0]['name']} ({key}): {rs[0]['about']}")
        print(f"  test: before {m('pre')}%  after SYNiq {m('post')}%  two weeks later {m('delayed')}%")
        print(f"        fixed version after {m('fixed_post')}%  two weeks later {m('fixed_delayed')}%")
        print(f"  explanations in their best way ({rs[0]['best_style']}): {round(100 * m('share_best_style_all'))}% overall, "
              f"{round(100 * m('share_best_style_late'))}% in the second half, {round(100 * m('share_best_first'))}% of first explanations of a topic")
        print(f"  questions {m('questions')}, right {m('right_pct')}%, topics secured {m('topics_secured')}/{rs[0]['topics']}, "
              f"secured too early (hidden knowledge under 70%) {m('false_secure')}")
        print(f"  periods missed {m('missed')}, questions on topics already known well {m('known_answers')}, "
              f"reviews {m('reviews')} in-chapter + {m('other_reviews')} other chapters, most explanations in a row {m('max_explain_run')}")
        print(f"  steps left unused because SYNiq had nothing more to give {m('idle_steps')} of {SITTINGS * STEPS}")
        print(f"  repeats within a period {m('repeats_in_period')}, watch-out nudges {m('watch_out')}, breaks {m('breaks')}")
        stuck = [s for x in rs for s in x["stuck"]]
        if stuck:
            print(f"  stuck: {stuck[:5]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    ap.add_argument("--summarise", nargs="*")
    a = ap.parse_args()
    if a.summarise:
        summarise(sorted({p for pat in a.summarise for p in glob.glob(pat)}))
        return
    result = run(a.seed)
    text = json.dumps(result, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
