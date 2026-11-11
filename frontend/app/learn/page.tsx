"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, del, effectiveSupport, post } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { ageBand, readsAloud } from "@/lib/age";
import { speak, useSession } from "@/lib/session";
import MathsHelper from "./MathsHelper";
import Signs from "./Signs";
import TalkBoard from "./TalkBoard";

/** A short sound after an answer, for listeners: two rising notes when right, one soft low note when not yet. */
function chime(right: boolean) {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const notes = right ? [523, 784] : [330];
    notes.forEach((f, i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.frequency.value = f;
      g.gain.setValueAtTime(0.12, ctx.currentTime + i * 0.15);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.15 + 0.3);
      o.connect(g).connect(ctx.destination);
      o.start(ctx.currentTime + i * 0.15);
      o.stop(ctx.currentTime + i * 0.15 + 0.3);
    });
    setTimeout(() => ctx.close(), 1000);
  } catch {
    /* no sound available: the words still say it */
  }
}

/** Count a help button press: one of the signs SYNiq uses to notice what helps. */
function helpPressed(kind: "read_aloud" | "break" | "activity") {
  post("/learn/events", { kind }).catch(() => undefined);
}
import Check, { CheckState } from "./Check";
import Feedback, { AdaptiveResponse } from "./Feedback";
import Mistake from "./Mistake";
import { methodName } from "../space/Methods";
import Picture, { type PictureSpec } from "./Picture";
import Activity, { type ActivitySpec } from "./Activity";
import Lesson, { type LessonStep } from "./Lesson";
import Notes from "./Notes";
import ReadAlong from "./ReadAlong";
import Tutor from "./Tutor";

type Subject = { id: number; code: string; name: string; chapters: number; language: string };

/** A symbol and colour per subject, so the subject list can be scanned at a glance. */
const SUBJECT_LOOK: Record<string, { icon: string; color: string }> = {
  mal: { icon: "അ", color: "#a63d2a" },
  eng: { icon: "Aa", color: "#3d5a80" },
  hin: { icon: "अ", color: "#c9793f" },
  hinb: { icon: "अ", color: "#c9793f" },
  math: { icon: "÷", color: "#7e2c1e" },
  phy: { icon: "⚡", color: "#b8860b" },
  chem: { icon: "⚗", color: "#6b4e9b" },
  bio: { icon: "🌿", color: "#4f7a55" },
  ss: { icon: "🌍", color: "#2f6f73" },
  it: { icon: "⌨", color: "#4a3d35" },
  sci: { icon: "🔬", color: "#4f6f9b" },
  evs: { icon: "🌱", color: "#4f7a55" },
  world: { icon: "🏡", color: "#4f7a55" },
};
type CheckRow = {
  subject_id: number;
  subject: string;
  start: "not_started" | CheckState["status"];
  rounds: { round_id: number; kind: "end" | "retention"; status: "not_started" | CheckState["status"] }[];
};
type ActiveCheck = { subjectId: number; name: string; kind: CheckState["kind"] };
type Chapter = { id: number; number: number; title: string };
type ChapterDetail = { id: number; title: string; concepts: { id: number; title: string; progress: string }[] };
type Item = {
  id: number;
  kind: "mcq" | "numeric";
  prompt: string;
  options: string[];
  hint_count: number;
  choices?: string[];
  keyboard?: "text" | "decimal";
  /** The question has a trap this student has fallen into before. */
  watch_out?: boolean;
  /** 1 easy to 3 harder. Harder ones carry a "challenge" tag so a slip there feels normal. */
  difficulty?: number;
};
type NextStep =
  | { kind: "secure_in"; n: number; topic: string }
  | { kind: "secured"; topic: string; next_topic: string | null };
type Puzzle = { id: string; prompt: string; sequence: string[]; options: string[] };
type PuzzleResult = { correct: boolean; answer: string; explain: string };
const PUZZLE_EVERY = 8; // a brain teaser now and then; the server decides whether one is due
type Spot = { item_id: number; friend: string; prompt: string; their_answer: string; options: string[] };
type SpotResult = {
  correct: boolean;
  right_answer: string;
  why: string | null;
  careful?: boolean;
  star_earned?: boolean;
  stars: number | null;
  new_sticker?: string | null;
};
type Overview = {
  subjects: { id: number; name: string; carry_on: { chapter_id: number; title: string } }[];
  review_due: { concept_id: number; title: string; chapter_id: number }[];
};
/** What the student said before starting: easier first questions if they feel low, and how long they have. */
type Prefs = { gentle: boolean; minutes: number };
const GENTLE_STEPS = 3;
const SPOT_EVERY = 5; // a spot-the-mistake puzzle after every few answers
type Explanation = { style: string; body: string; picture?: PictureSpec | null };
type Step = {
  decision_id: number;
  kind: "explain" | "practice" | "review" | "prereq_review" | "chapter_complete";
  reason: string;
  concept: { id: number; title: string; signs?: { word: string; url: string }[] } | null;
  offer_support: boolean;
  explanation?: Explanation | null;
  styles?: string[];
  item?: Item | null;
  method_why?: "history" | "similar" | "everyone";
  activity?: ActivitySpec | null;
  lesson?: LessonStep[] | null;
  has_lesson?: boolean;
  next_chapter?: { id: number; number: number; title: string } | null;
};
type Result = {
  correct: boolean;
  feedback: string;
  progress: string;
  tip?: string | null;
  solution?: string;
  your_answer?: string;
  right_answer?: string;
  picture?: PictureSpec | null;
  response: AdaptiveResponse;
  next_step?: NextStep;
  offer_break?: boolean;
  tip_tag?: string;
};

/** "Was this tip helpful?" after a mistake tip. One tap, then a thank-you; counts only, for improving tips. */
function TipHelpful({ itemId, tag }: { itemId: number; tag: string }) {
  const { t } = useSession();
  const [sent, setSent] = useState(false);
  const send = (helpful: boolean) => {
    setSent(true);
    post("/learn/tip-feedback", { item_id: itemId, tag, helpful }).catch(() => undefined);
  };
  if (sent) return <p className="muted tip-helpful">{t("tip.thanks")}</p>;
  return (
    <p className="tip-helpful">
      <span className="muted">{t("tip.helpful")}</span>{" "}
      <button type="button" className="secondary small" onClick={() => send(true)}>
        {t("tip.yes")}
      </button>{" "}
      <button type="button" className="secondary small" onClick={() => send(false)}>
        {t("tip.no")}
      </button>
    </p>
  );
}

const KIND_HEADINGS: Record<string, Key> = {
  practice: "learn.practice",
  review: "learn.review",
  prereq_review: "learn.prereq_review",
};

export default function Learn() {
  const { me, loading, t, saveSettings } = useSession();
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [checks, setChecks] = useState<CheckRow[]>([]);
  const [activeCheck, setActiveCheck] = useState<ActiveCheck | null>(null);
  const canLearn = me?.role === "student" && !!me.consent?.core_learning;
  const [teacherChapter, setTeacherChapter] = useState<{ chapter_id: number; title: string; number: number; subject: string } | null>(null);

  useEffect(() => {
    if (!loading && (!me || me.role !== "student")) router.replace("/");
  }, [me, loading, router]);

  useEffect(() => {
    if (me?.role === "student") api<Subject[]>("/subjects").then(setSubjects).catch(() => setSubjects([]));
  }, [me]);

  useEffect(() => {
    if (canLearn && !chapter)
      api<{ today_chapter: typeof teacherChapter }>("/me/lesson-today")
        .then((r) => setTeacherChapter(r.today_chapter))
        .catch(() => undefined);
  }, [canLearn, chapter]);

  function loadChecks() {
    api<CheckRow[]>("/checks").then(setChecks).catch(() => setChecks([]));
  }

  useEffect(() => {
    if (canLearn) loadChecks();
  }, [canLearn]);

  useEffect(() => {
    if (canLearn && !chapter) api<Overview>("/me/overview").then(setOverview).catch(() => setOverview(null));
  }, [canLearn, chapter]);

  // Opened from "My space" with ?chapter=<id> (revise a topic, carry on a chapter).
  useEffect(() => {
    if (!canLearn) return;
    const id = Number(new URLSearchParams(window.location.search).get("chapter"));
    if (id) api<ChapterDetail>(`/chapters/${id}`).then(setChapter).catch(() => undefined);
  }, [canLearn]);

  if (!me || me.role !== "student") return null;

  if (me.consent && !me.consent.core_learning) {
    return (
      <div className="wrap">
        <div className="card">
          <h1>{t("learn.almost_ready")}</h1>
          <p>{t("learn.need_consent")}</p>
        </div>
      </div>
    );
  }

  if (activeCheck) {
    return (
      <Check
        subjectId={activeCheck.subjectId}
        subjectName={activeCheck.name}
        kind={activeCheck.kind}
        onDone={() => {
          setActiveCheck(null);
          loadChecks();
        }}
      />
    );
  }

  const checkFor = (subjectId: number) => checks.find((c) => c.subject_id === subjectId);
  const startOffer = subject ? checkFor(subject.id) : undefined;
  const offerStart = !!startOffer && (startOffer.start === "not_started" || startOffer.start === "open");
  const little = ageBand(me) === "little";
  const roundsDue = checks.flatMap((c) =>
    c.rounds.filter((r) => r.status !== "done").map((r) => ({ subjectId: c.subject_id, name: c.subject, kind: r.kind }))
  );

  // During a lesson the chapter name is the page's main heading, for screen readers (it shows on the back button).
  if (chapter && !prefs) {
    return (
      <>
        <h1 className="sr-only">{chapter.title}</h1>
        <CheckIn onDone={setPrefs} />
      </>
    );
  }

  if (chapter && prefs) {
    return (
      <>
        <h1 className="sr-only">{chapter.title}</h1>
        <Session
          chapter={chapter}
          prefs={prefs}
          onExit={() => {
            setChapter(null);
            setPrefs(null);
          }}
          onChapter={async (id) => setChapter(await api<ChapterDetail>(`/chapters/${id}`))}
        />
      </>
    );
  }

  const due = overview?.review_due[0];
  const carryOn = overview?.subjects[0]?.carry_on;

  return (
    <div className="wrap">
      <div className="hello">
        <span className="wave" aria-hidden="true">
          👋
        </span>
        <h1>{t("learn.hi", { name: me.name })}</h1>
        {little && (
          <button className="secondary listen" onClick={() => speak(`${t("learn.hi", { name: me.name })} ${t("learn.what_today")}`)}>
            🔊 {t("learn.listen")}
          </button>
        )}
      </div>
      {!subject ? (
        <>
          {me.role === "student" && !me.settings?.welcome_seen && (
            <div className="card welcome-card">
              <h2>{t("welcome.title")}</h2>
              <ul>
                <li>{t("welcome.no_marks")}</li>
                <li>{t("welcome.mistakes")}</li>
                <li>{t("welcome.pace")}</li>
              </ul>
              <button onClick={() => saveSettings({ welcome_seen: true }).catch(() => undefined)}>{t("welcome.ok")}</button>
            </div>
          )}
          {teacherChapter && (
            <div className="card next-step-card teacher-chapter">
              <h2>{t("today.teacher_chapter")}</h2>
              <button onClick={async () => setChapter(await api<ChapterDetail>(`/chapters/${teacherChapter.chapter_id}`))}>
                {teacherChapter.subject}: {teacherChapter.number}. {teacherChapter.title}
              </button>
            </div>
          )}
          {(due || carryOn) && (
            <div className="card next-step-card">
              <h2>{t("next.title")}</h2>
              <button onClick={async () => setChapter(await api<ChapterDetail>(`/chapters/${due ? due.chapter_id : carryOn!.chapter_id}`))}>
                {due ? t("next.revise", { topic: due.title }) : t("next.carry_on", { chapter: carryOn!.title })}
              </button>
            </div>
          )}
          {roundsDue.length > 0 && (
            <div className="card sunny">
              <h2>{t(`check.round_open.${roundsDue[0].kind}` as Key)}</h2>
              <p className="muted">{t("check.round_help")}</p>
              <div className="row">
                {roundsDue.map((r) => (
                  <button key={`${r.subjectId}-${r.kind}`} className="secondary" onClick={() => setActiveCheck(r)}>
                    {r.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <p className="muted">{t("learn.what_today")}</p>
          <div className="subject-grid">
            {subjects.map((s) => {
              const look = SUBJECT_LOOK[s.code.replace(/^cbse(\d+|lkg|ukg)-/, "")] ?? { icon: s.name.slice(0, 1), color: "#a63d2a" };
              return (
                <button
                  key={s.id}
                  className="subject-tile"
                  style={{ "--tile": look.color } as React.CSSProperties}
                  disabled={!s.chapters}
                  onClick={async () => {
                    if (little) speak(s.name);
                    setSubject(s);
                    setChapters(await api<Chapter[]>(`/subjects/${s.id}/chapters`));
                  }}
                >
                  <span className="subject-icon" aria-hidden="true">
                    {look.icon}
                  </span>
                  <span>
                    <span className="subject-name">{s.name}</span>
                    <br />
                    <span className="subject-meta">{s.chapters ? t("learn.chapters", { n: s.chapters }) : t("learn.coming_soon")}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </>
      ) : (
        <>
          <button className="secondary" onClick={() => setSubject(null)}>
            {t("learn.all_subjects")}
          </button>
          <h1 style={{ marginTop: 16 }}>{subject.name}</h1>
          {offerStart && (
            <div className="card sunny">
              <h2>{t("check.offer_title")}</h2>
              <p>{t("check.offer_body")}</p>
              <div className="row">
                <button onClick={() => setActiveCheck({ subjectId: subject.id, name: subject.name, kind: "start" })}>
                  {t("check.offer_start")}
                </button>
                <button
                  className="secondary"
                  onClick={async () => {
                    await post("/checks/skip-start", { subject_id: subject.id }).catch(() => undefined);
                    loadChecks();
                  }}
                >
                  {t("check.skip")}
                </button>
              </div>
            </div>
          )}
          <ul className="list card chapters">
            {chapters.map((c) => (
              <li key={c.id}>
                <span className="chapter-title" onClick={async () => setChapter(await api<ChapterDetail>(`/chapters/${c.id}`))}>
                  <span className="chapter-num" aria-hidden="true">
                    {c.number}
                  </span>
                  <span>
                    <span className="sr-only">{c.number}. </span>
                    {c.title}
                  </span>
                </span>
                <button className="secondary" onClick={async () => setChapter(await api<ChapterDetail>(`/chapters/${c.id}`))}>
                  {t("learn.start")}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function CheckIn({ onDone }: { onDone: (prefs: Prefs) => void }) {
  const { t } = useSession();
  const [message, setMessage] = useState("");
  const [gentle, setGentle] = useState(false);
  const moods = ["great", "okay", "low", "frustrated"] as const;
  const times = [5, 10, 20, 0] as const;

  if (message) {
    return (
      <div className="wrap">
        <div className="card">
          <p>{message}</p>
          <h2>{t("checkin.time_question")}</h2>
          <div className="options">
            {times.map((m) => (
              <button key={m} className="option" onClick={() => onDone({ gentle, minutes: m })}>
                {t(`checkin.time.${m}` as Key)}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="card">
        <h2>{t("checkin.question")}</h2>
        <p className="muted">{t("checkin.optional")}</p>
        <div className="options">
          {moods.map((value) => (
            <button
              key={value}
              className="option"
              onClick={async () => {
                // Feeling low or frustrated: the first few questions are easier. Not stored unless the parent allowed it.
                setGentle(value === "low" || value === "frustrated");
                const r = await post<{ message: string }>("/checkins", { mood: value });
                setMessage(r.message);
              }}
            >
              {t(`checkin.${value}`)}
            </button>
          ))}
        </div>
        <div className="row" style={{ marginTop: 16 }}>
          <button className="secondary" onClick={() => onDone({ gentle: false, minutes: 0 })}>
            {t("checkin.skip")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Session({
  chapter,
  prefs,
  onExit,
  onChapter,
}: {
  chapter: ChapterDetail;
  prefs: Prefs;
  onExit: () => void;
  onChapter: (id: number) => void;
}) {
  const { me, t } = useSession();
  const gentleLeft = useRef(prefs.gentle ? GENTLE_STEPS : 0);
  const sessionStart = useRef(Date.now());
  const [answered, setAnswered] = useState(0);
  const [secured, setSecured] = useState<string[]>([]);
  const [summary, setSummary] = useState(false);
  const [extended, setExtended] = useState(false);
  const [spot, setSpot] = useState<Spot | null>(null);
  const [spotResult, setSpotResult] = useState<SpotResult | null>(null);
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [puzzleResult, setPuzzleResult] = useState<PuzzleResult | null>(null);
  const puzzleStart = useRef(0);
  const [step, setStep] = useState<Step | null>(null);
  const [answer, setAnswer] = useState("");
  const [hints, setHints] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  // The lesson is taught before the sum-up; this remembers which step's lesson has been finished.
  const [lessonDone, setLessonDone] = useState<number | null>(null);
  // Going over a topic's lesson again during practice.
  const [replay, setReplay] = useState<{ conceptId: number; steps: LessonStep[] } | null>(null);
  // "Did this way help?" for the explanation on screen: the learner's own answer helps SYNiq choose next time.
  const [felt, setFelt] = useState<{ key: string; helped: boolean } | null>(null);
  const [onBreak, setOnBreak] = useState(false);
  const [sending, setSending] = useState(false);
  const [connection, setConnection] = useState("");
  const [lessonInfo, setLessonInfo] = useState<{ in_class: boolean; hand_up: boolean }>({ in_class: false, hand_up: false });
  useEffect(() => {
    api<{ in_class: boolean; hand_up: boolean }>("/me/lesson-today")
      .then(setLessonInfo)
      .catch(() => undefined);
  }, []);

  async function toggleHand() {
    const up = !lessonInfo.hand_up;
    try {
      if (up) await post("/me/help", { concept_id: step?.concept?.id ?? null });
      else await del("/me/help");
      setLessonInfo({ ...lessonInfo, hand_up: up });
    } catch {
      /* offline: the button stays as it was */
    }
  }
  const [error, setError] = useState("");
  const conceptRef = useRef<number | null>(null);
  const styleRef = useRef<string | null>(null);
  const startedRef = useRef<number>(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const support = effectiveSupport(me?.settings);
  // Listening: SYNiq says everything itself, for blind and low-vision learners on a computer with no screen reader.
  const listen = support.includes("listen");
  const readAloud = readsAloud(me) || listen;
  const young = ageBand(me) === "little" || ageBand(me) === "middle";
  // Deaf learners who chose pictures and text first also get the topic's sign-language links.
  const signs = support.includes("visual_first");
  const talkBoard = support.includes("talk_board");
  // The number helper: chosen, or noticed when pictures and smaller numbers help.
  const helperOn = support.includes("maths_helper") || support.includes("small_steps");
  const [showHelper, setShowHelper] = useState(false);
  // Calm: the lesson goes the same way every time, with no surprise puzzles.
  const calm = support.includes("calm");
  // Movement help: number keys choose answers, and the Next button takes focus so one key press moves on.
  const motor = support.includes("motor");
  const nextRef = useRef<HTMLButtonElement>(null);
  const [tutorOn, setTutorOn] = useState(false);

  useEffect(() => {
    api<{ enabled: boolean }>("/ai/status")
      .then((s) => setTutorOn(s.enabled))
      .catch(() => setTutorOn(false));
  }, []);

  /** Everything a listener needs to answer: the question, then each choice with its number key. */
  function sayItem(item: Item): string {
    const options = item.choices?.length ? item.choices : item.kind === "mcq" ? item.options : [];
    const read = options.map((o, i) => t("listen.choice", { n: i + 1, text: o })).join(" ");
    return `${item.prompt} ${read} ${options.length ? t("listen.keys") : t("listen.type")}`;
  }

  function sayExplanation(exp: Explanation | null | undefined): string {
    const picture = exp?.picture?.alt ? ` ${t("listen.picture", { text: exp.picture.alt })}` : "";
    return `${exp?.body ?? t("learn.no_explanation")}${picture} ${t("listen.ready")}`;
  }

  async function next() {
    setError("");
    try {
      const gentle = gentleLeft.current > 0;
      const s = await post<Step>("/learn/next", { chapter_id: chapter.id, current_concept_id: conceptRef.current, gentle });
      if (gentle && s.item) gentleLeft.current -= 1;
      conceptRef.current = s.concept?.id ?? null;
      if (s.explanation) styleRef.current = s.explanation.style;
      setStep(s);
      setAnswer("");
      setHints([]);
      setResult(null);
      setShowWhy(false);
      setShowActivity(false);
      setShowHelper(false);
      startedRef.current = Date.now();
      if (listen) speak(s.item ? sayItem(s.item) : s.kind === "explain" ? sayExplanation(s.explanation) : s.reason);
      else if (readAloud) speak(s.explanation?.body ?? s.item?.prompt ?? s.reason);
      requestAnimationFrame(() => headingRef.current?.focus());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("learn.load_failed"));
    }
  }

  /** A brain teaser if one is due (only when the parent switched puzzles on). Returns whether one is showing. */
  async function tryPuzzle(): Promise<boolean> {
    if (calm) return false;
    try {
      const pz = await api<Puzzle | null>("/thinking/puzzle");
      if (!pz || !pz.id) return false;
      setPuzzle(pz);
      setPuzzleResult(null);
      puzzleStart.current = Date.now();
      if (readAloud) speak(pz.prompt);
      return true;
    } catch {
      return false;
    }
  }

  async function answerPuzzle(choice: string) {
    if (!puzzle) return;
    const r = await post<PuzzleResult>("/thinking/puzzle", { id: puzzle.id, choice, time_ms: Date.now() - puzzleStart.current });
    setPuzzleResult(r);
    if (readAloud) speak(`${r.correct ? t("puzzle.nice") : t("puzzle.try")} ${r.explain}`);
  }

  useEffect(() => {
    // At the start: a brain teaser first when one is due, then the lesson.
    tryPuzzle().then((showing) => {
      if (!showing) next();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Number keys pick an answer (1 = first choice); Enter checks it, wherever focus is.
  const choices = step?.item ? (step.item.choices?.length ? step.item.choices : step.item.kind === "mcq" ? step.item.options : []) : [];
  useEffect(() => {
    if (!choices.length || result) return;
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement;
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable || e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === "Enter" && answer && el.tagName !== "BUTTON" && el.tagName !== "A") {
        e.preventDefault();
        submit();
        return;
      }
      const n = Number(e.key);
      if (Number.isInteger(n) && n >= 1 && n <= choices.length) {
        e.preventDefault();
        setAnswer(choices[n - 1]);
        if (listen) speak(t("listen.chosen", { n, text: choices[n - 1] }));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // Listening keys: R says it again, H gives a hint, Enter moves on from an explanation.
  useEffect(() => {
    if (!listen || !step) return;
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement;
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable || e.altKey || e.ctrlKey || e.metaKey) return;
      const key = e.key.toLowerCase();
      if (key === "r") {
        e.preventDefault();
        if (step!.item) speak(sayItem(step!.item));
        else if (step!.kind === "explain") speak(sayExplanation(step!.explanation));
      } else if (key === "h" && step!.item && !result && hints.length < step!.item.hint_count) {
        e.preventDefault();
        showHint();
      } else if (e.key === "Enter" && step!.kind === "explain" && el.tagName !== "BUTTON" && el.tagName !== "A") {
        e.preventDefault();
        next();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // After an answer, a listener hears a sound, the result and what they said against the answer.
  useEffect(() => {
    if (!listen || !result) return;
    chime(result.correct);
    const compare = !result.correct && result.your_answer && result.right_answer ? `${t("listen.yours_right", { yours: result.your_answer, right: result.right_answer })} ` : "";
    speak(`${compare}${result.response.script} ${t("listen.next")}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listen, result]);

  useEffect(() => {
    if ((motor || listen) && result) requestAnimationFrame(() => nextRef.current?.focus());
  }, [motor, listen, result]);

  async function tellHelped(helped: boolean) {
    if (!step?.concept || !step.explanation) return;
    setFelt({ key: `${step.decision_id}-${step.explanation.style}`, helped });
    try {
      await post("/learn/explanation-feedback", { concept_id: step.concept.id, style: step.explanation.style, helped });
    } catch {
      // Only a nudge for next time: nothing to show if it doesn't reach the server.
    }
  }

  async function switchStyle(style: string) {
    if (!step?.concept) return;
    const exp = await api<Explanation>(`/concepts/${step.concept.id}/explanations/${style}`);
    styleRef.current = exp.style;
    setStep({ ...step, explanation: exp, method_why: undefined });
    if (readAloud) speak(exp.body);
  }

  async function showHint() {
    if (!step?.item) return;
    const h = await api<{ hint: string }>(`/items/${step.item.id}/hints/${hints.length + 1}`);
    setHints([...hints, h.hint]);
    if (readAloud) speak(h.hint);
  }

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!step?.item || !answer.trim() || sending) return;
    const body = {
      item_id: step.item.id,
      response: answer.trim(),
      hints_used: hints.length,
      time_ms: Date.now() - startedRef.current,
      explanation_style: styleRef.current,
    };
    // School Wi-Fi drops for a moment now and then: try again quietly before giving up, keeping the answer.
    let r: Result | null = null;
    setSending(true);
    for (const wait of [0, 2000, 4000, 8000]) {
      if (wait) {
        setConnection(t("net.retrying"));
        await new Promise((ok) => setTimeout(ok, wait));
      }
      try {
        r = await post<Result>("/learn/attempts", body);
        break;
      } catch (err) {
        if (err instanceof ApiError) {
          setSending(false);
          setConnection("");
          throw err;
        }
      }
    }
    setSending(false);
    if (!r) {
      setConnection(t("net.lost"));
      return;
    }
    setConnection("");
    setResult(r);
    setAnswered((n) => n + 1);
    if (r.next_step?.kind === "secured" && r.correct) {
      const topic = r.next_step.topic;
      setSecured((ts) => (ts.includes(topic) ? ts : [...ts, topic]));
    }
  }

  /** After an answer: the time the student had may be up; every few answers, a spot-the-mistake puzzle. */
  async function afterResult() {
    if (prefs.minutes && !extended && Date.now() - sessionStart.current >= prefs.minutes * 60000) {
      setSummary(true);
      return;
    }
    if (answered % PUZZLE_EVERY === 0 && (await tryPuzzle())) return;
    if (!calm && answered % SPOT_EVERY === 0 && step?.concept) {
      try {
        const sp = await api<Spot>(`/learn/spot?concept_id=${step.concept.id}`);
        setSpot(sp);
        setSpotResult(null);
        if (readAloud) speak(`${t("spot.body", { name: sp.friend })} ${sp.prompt} ${t("spot.their", { name: sp.friend, answer: sp.their_answer })}`);
        return;
      } catch {
        // Nothing to spot on this topic: carry on.
      }
    }
    next();
  }

  async function answerSpot(choice: string) {
    if (!spot) return;
    const r = await post<SpotResult>("/learn/spot", { item_id: spot.item_id, their_answer: spot.their_answer, choice });
    setSpotResult(r);
    const said = r.correct ? t(r.star_earned ? "spot.right" : "spot.right_plain") : `${t("spot.wrong", { answer: r.right_answer })} ${r.why ?? ""} ${t("spot.careful")}`;
    if (readAloud) speak(r.new_sticker ? `${said} ${t("sticker.new")}` : said);
  }

  if (summary) {
    return (
      <div className="wrap">
        <div className="card sunny">
          <h2>{t("session.time_up")}</h2>
          <p>{t("session.did", { n: answered })}</p>
          {secured.length > 0 && <p>{t("session.secured", { topics: secured.join(", ") })}</p>}
          {result?.next_step && <NextStepLine step={result.next_step} />}
          <div className="row">
            <button onClick={onExit}>{t("session.finish")}</button>
            <button
              className="secondary"
              onClick={() => {
                setExtended(true);
                setSummary(false);
                next();
              }}
            >
              {t("session.keep_going")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (puzzle) {
    return (
      <div className="wrap">
        <div className="card puzzle" aria-live="polite">
          <h2>{t("puzzle.title")}</h2>
          <p style={{ fontSize: "1.15rem" }}>{puzzle.prompt}</p>
          {puzzle.sequence.length > 0 && (
            <div className="puzzle-sequence" aria-label={puzzle.sequence.join(", ")}>
              {puzzle.sequence.map((s, i) => (
                <span key={i} className="puzzle-tile">
                  {s}
                </span>
              ))}
              <span className="puzzle-tile puzzle-blank">?</span>
            </div>
          )}
          {!puzzleResult ? (
            <div className="puzzle-options">
              {puzzle.options.map((o) => (
                <button key={o} className="option" onClick={() => answerPuzzle(o)}>
                  {o}
                </button>
              ))}
            </div>
          ) : (
            <>
              <p className={`feedback ${puzzleResult.correct ? "good" : "warn"}`}>
                {puzzleResult.correct ? t("puzzle.nice") : t("puzzle.try")}
              </p>
              <p>{puzzleResult.explain}</p>
              <button
                onClick={() => {
                  setPuzzle(null);
                  next();
                }}
              >
                {t("puzzle.continue")}
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  if (spot) {
    return (
      <div className="wrap">
        <div className="card spot" aria-live="polite">
          <h2>🔎 {t("spot.title")}</h2>
          <p className="muted">{t("spot.body", { name: spot.friend })}</p>
          <p style={{ fontSize: "1.15rem" }}>{spot.prompt}</p>
          <p className="spot-theirs">{t("spot.their", { name: spot.friend, answer: spot.their_answer })}</p>
          {!spotResult ? (
            <>
              <p>{t("spot.ask")}</p>
              <div className="options">
                {spot.options.map((o) => (
                  <button key={o} className="option" onClick={() => answerSpot(o)}>
                    {o}
                  </button>
                ))}
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="secondary" onClick={() => { setSpot(null); next(); }}>
                  {t("spot.skip")}
                </button>
              </div>
            </>
          ) : (
            <>
              <p className={`feedback ${spotResult.correct ? "good" : "warn"}`}>
                {spotResult.correct
                  ? t(spotResult.star_earned ? "spot.right" : "spot.right_plain")
                  : t("spot.wrong", { answer: spotResult.right_answer })}
              </p>
              {spotResult.why && <p>{spotResult.why}</p>}
              {spotResult.careful && <p className="muted">{t("spot.careful")}</p>}
              {spotResult.new_sticker && (
                <p className="new-sticker" role="status">
                  <span className="sticker" aria-hidden="true">{spotResult.new_sticker}</span> {t("sticker.new")}
                </p>
              )}
              {spotResult.stars != null && spotResult.stars > 0 && (
                <p className="muted">{spotResult.stars === 1 ? t("stars.count_one") : t("stars.count", { n: spotResult.stars })}</p>
              )}
              <button onClick={() => { setSpot(null); next(); }}>{t("spot.continue")}</button>
            </>
          )}
        </div>
      </div>
    );
  }

  if (onBreak) {
    return (
      <div className="wrap">
        <div className="card">
          <h2>{t("break.title")}</h2>
          <p>{t("break.body")}</p>
          <button onClick={() => setOnBreak(false)}>{t("break.back")}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="row session-top" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <button className="secondary back-chapter" onClick={onExit} aria-label={chapter.title}>
          <span aria-hidden="true">←</span> <span className="back-chapter-title">{chapter.title}</span>
        </button>
        <button
          className="secondary"
          onClick={() => {
            setOnBreak(true);
            helpPressed("break");
          }}
        >
          {t("break.button")}
        </button>
      </div>
      {lessonInfo.in_class && (
        <div className="hand-row">
          <button className={lessonInfo.hand_up ? "" : "secondary"} aria-pressed={lessonInfo.hand_up} onClick={toggleHand}>
            ✋ {lessonInfo.hand_up ? t("help.lower") : t("help.raise")}
          </button>
          {lessonInfo.hand_up && (
            <span className="muted" role="status">
              {t("help.waiting")}
            </span>
          )}
        </div>
      )}
      {talkBoard && <TalkBoard inClass={lessonInfo.in_class} conceptId={step?.concept?.id ?? null} />}

      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      {connection && (
        <p className="feedback note" role="status" aria-live="polite">
          {connection}
        </p>
      )}

      {calm && step && <CalmPlan kind={step.kind} answered={answered} minutes={prefs.minutes} />}

      {step && (
        <div className="card" aria-live="polite">
          {step.concept && <p className="muted">{step.concept.title}</p>}
          {signs && step.concept && step.kind !== "chapter_complete" && <Signs signs={step.concept.signs ?? []} />}

          {step.kind === "chapter_complete" && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {t("learn.chapter_complete")}
              </h2>
              <p>{t("learn.chapter_complete_body")}</p>
              <div className="row">
                {step.next_chapter && (
                  <button onClick={() => onChapter(step.next_chapter!.id)}>
                    {t("learn.next_chapter", { number: step.next_chapter.number, title: step.next_chapter.title })}
                  </button>
                )}
                <button className={step.next_chapter ? "secondary" : undefined} onClick={onExit}>
                  {t("learn.another_chapter")}
                </button>
              </div>
            </>
          )}

          {step.kind === "explain" && step.lesson?.length && lessonDone !== step.decision_id ? (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {t("lesson.heading", { topic: step.concept?.title ?? "" })}
              </h2>
              <Lesson key={step.decision_id} conceptId={step.concept!.id} steps={step.lesson} onDone={() => setLessonDone(step.decision_id)} />
            </>
          ) : null}

          {step.kind === "explain" && (!step.lesson?.length || lessonDone === step.decision_id) && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {step.offer_support ? t("learn.different_way") : step.lesson?.length ? t("lesson.in_short") : t("learn.lets_learn")}
              </h2>
              {step.offer_support && (
                <p className="feedback warn">{t("learn.offer_support")}</p>
              )}
              {step.method_why && step.explanation && (
                <p className="muted">{t(`learn.why_method.${step.method_why}`, { method: methodName(t, step.explanation.style) })}</p>
              )}
              {young && step.explanation?.picture && <Picture picture={step.explanation.picture} />}
              <ReadAlong style={{ fontSize: "1.1rem" }} text={step.explanation?.body ?? t("learn.no_explanation")} />
              {!young && step.explanation?.picture && <Picture picture={step.explanation.picture} />}
              {young && step.explanation && (
                <div className="row">
                  <button
                    className="secondary"
                    onClick={() => {
                      speak(step.explanation!.body);
                      helpPressed("read_aloud");
                    }}
                  >
                    {t("learn.read_aloud")}
                  </button>
                </div>
              )}
              <div className="row style-chips" role="group" aria-label={t("learn.other_ways")}>
                {(step.styles ?? []).map((s) => (
                  <button
                    key={s}
                    className="secondary"
                    aria-pressed={step.explanation?.style === s}
                    onClick={() => switchStyle(s)}
                  >
                    {t(`style.${s}` as Key)}
                  </button>
                ))}
                {!young && step.explanation && (
                  <button
                    className="secondary"
                    onClick={() => {
                      speak(step.explanation!.body);
                      helpPressed("read_aloud");
                    }}
                  >
                    {t("learn.read_aloud")}
                  </button>
                )}
              </div>
              {step.explanation && (
                <div className="row felt" role="group" aria-label={t("learn.felt.ask")}>
                  {felt?.key === `${step.decision_id}-${step.explanation.style}` ? (
                    <p className="muted" role="status">{t(felt.helped ? "learn.felt.thanks" : "learn.felt.try_other")}</p>
                  ) : (
                    <>
                      <span className="muted">{t("learn.felt.ask")}</span>
                      <button className="secondary" onClick={() => tellHelped(true)}>{t("learn.felt.yes")}</button>
                      <button className="secondary" onClick={() => tellHelped(false)}>{t("learn.felt.no")}</button>
                    </>
                  )}
                </div>
              )}
              {step.activity && <Activity key={step.decision_id} spec={step.activity} onDone={() => helpPressed("activity")} />}
              <div className="row" style={{ marginTop: 16 }}>
                <button onClick={next}>{t("learn.ready")}</button>
              </div>
            </>
          )}

          {step.item && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {KIND_HEADINGS[step.kind] ? t(KIND_HEADINGS[step.kind]) : null}
              </h2>
              {(step.item.difficulty ?? 1) >= 3 && <p className="challenge-tag">{t("learn.challenge")}</p>}
              {step.item.watch_out && !result && <p className="feedback warn watch-out">{t("learn.watch_out")}</p>}
              <ReadAlong style={{ fontSize: "1.2rem" }} text={step.item.prompt} />
              <button
                className="secondary"
                onClick={() => {
                  speak(step.item!.prompt);
                  helpPressed("read_aloud");
                }}
                aria-label={t("learn.read_question")}
              >
                🔊
              </button>
              {step.activity && (
                <button className="secondary try-it" aria-expanded={showActivity} onClick={() => setShowActivity(!showActivity)}>
                  <span aria-hidden="true">🧪</span> {showActivity ? t("act.hide") : t("act.open")}
                </button>
              )}
              {showActivity && step.activity && <Activity key={step.decision_id} spec={step.activity} onDone={() => helpPressed("activity")} />}
              {step.concept && step.has_lesson && (
                <button
                  className="secondary"
                  aria-expanded={replay?.conceptId === step.concept.id}
                  onClick={async () => {
                    if (replay?.conceptId === step.concept!.id) return setReplay(null);
                    try {
                      const l = await api<{ steps: LessonStep[] }>(`/learn/lesson/${step.concept!.id}`);
                      setReplay({ conceptId: step.concept!.id, steps: l.steps });
                    } catch {
                      setReplay(null);
                    }
                  }}
                >
                  <span aria-hidden="true">📖</span> {replay?.conceptId === step.concept.id ? t("lesson.hide") : t("lesson.again")}
                </button>
              )}
              {replay && replay.conceptId === step.concept?.id && (
                <Lesson key={`again-${step.decision_id}`} conceptId={replay.conceptId} steps={replay.steps} onDone={() => setReplay(null)} />
              )}
              {helperOn && /\d/.test(step.item.prompt) && (
                <button className="secondary" aria-expanded={showHelper} onClick={() => setShowHelper(!showHelper)}>
                  {showHelper ? t("helper.hide") : t("helper.open")}
                </button>
              )}
              {showHelper && <MathsHelper key={step.decision_id} prompt={step.item.prompt} />}
              <form onSubmit={submit} style={{ marginTop: 12 }}>
                {step.item.kind === "mcq" || step.item.choices?.length ? (
                  <>
                    <div className="options" role="group" aria-label={t("learn.choices")}>
                      {(step.item.choices?.length ? step.item.choices : step.item.options).map((o, i) => (
                        <button
                          type="button"
                          key={o}
                          className="option"
                          aria-pressed={answer === o}
                          aria-keyshortcuts={i < 9 ? String(i + 1) : undefined}
                          disabled={!!result}
                          onClick={() => setAnswer(o)}
                        >
                          {o}
                          {motor && i < 9 && (
                            <span className="key-hint" aria-hidden="true">
                              {t("learn.key", { n: i + 1 })}
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                    {motor && !result && <p className="muted keys-help">{t("learn.keys_hint", { n: Math.min(choices.length, 9) })}</p>}
                  </>
                ) : (
                  <>
                    <label htmlFor="answer">{t("learn.your_answer")}</label>
                    <input id="answer" inputMode={step.item.keyboard ?? "decimal"} value={answer} disabled={!!result} onChange={(e) => setAnswer(e.target.value)} />
                  </>
                )}

                {hints.map((h, i) => (
                  <p key={i} className="feedback warn">
                    {t("learn.hint", { n: i + 1, text: h })}
                  </p>
                ))}

                {!result && (
                  <div className="row" style={{ marginTop: 16 }}>
                    <button type="submit" disabled={!answer.trim()}>
                      {t("learn.check")}
                    </button>
                    {hints.length < step.item.hint_count && (
                      <button type="button" className="secondary" onClick={showHint}>
                        {t("learn.give_hint")}
                      </button>
                    )}
                  </div>
                )}
              </form>

              {result && (
                <>
                  {!result.correct && result.your_answer && result.right_answer ? (
                    <Mistake yours={result.your_answer} right={result.right_answer} picture={result.picture}>
                      <Feedback key={step.decision_id} r={result.response} readAloud={readAloud && !listen} tutorOn={tutorOn} />
                    </Mistake>
                  ) : (
                    <Feedback key={step.decision_id} r={result.response} readAloud={readAloud && !listen} tutorOn={tutorOn} />
                  )}
                  {!result.correct && (step.item.difficulty ?? 1) >= 3 && <p className="muted">{t("learn.challenge_wrong")}</p>}
                  {!result.correct && result.tip_tag && <TipHelpful key={`${step.item.id}-${result.tip_tag}`} itemId={step.item.id} tag={result.tip_tag} />}
                  {result.next_step && <NextStepLine step={result.next_step} />}
                  {result.offer_break && (
                    <div className="feedback note break-offer">
                      <p>{t("break.offer")}</p>
                      <div className="row">
                        <button
                          className="secondary"
                          onClick={() => {
                            setOnBreak(true);
                            helpPressed("break");
                          }}
                        >
                          {t("break.offer_yes")}
                        </button>
                      </div>
                    </div>
                  )}
                  <button ref={nextRef} onClick={afterResult}>
                    {t("learn.next")}
                  </button>
                </>
              )}
            </>
          )}

          {step.kind !== "chapter_complete" && step.concept && !step.item && step.kind !== "explain" && (
            <p className="muted">{t("learn.no_questions")}</p>
          )}

          <p className="why">
            <button className="secondary" onClick={() => setShowWhy(!showWhy)} aria-expanded={showWhy}>
              {t("learn.why")}
            </button>
          </p>
          {showWhy && <p className="muted">{step.reason}</p>}
        </div>
      )}

      {tutorOn && step?.concept && step.kind !== "chapter_complete" && (
        <Tutor
          conceptId={step.concept.id}
          conceptTitle={step.concept.title}
          readAloud={readAloud}
          itemId={step.item && !result ? step.item.id : null}
        />
      )}

      {step?.concept && step.kind !== "chapter_complete" && <Notes conceptId={step.concept.id} conceptTitle={step.concept.title} />}
    </div>
  );
}

/** Calm lessons: a picture plan of the lesson, so nothing comes as a surprise. */
function CalmPlan({ kind, answered, minutes }: { kind: string; answered: number; minutes: number }) {
  const { t } = useSession();
  const now = kind === "explain" ? 0 : kind === "chapter_complete" ? 2 : 1;
  const steps = [
    { icon: "📖", label: t("calm.learn") },
    { icon: "✏️", label: t("calm.practise", { n: answered }) },
    { icon: "🏁", label: t("calm.finish") },
  ];
  return (
    <nav aria-label={t("calm.plan")}>
      <ol className="calm-plan">
        {steps.map((st, i) => (
          <li key={i} aria-current={i === now ? "step" : undefined} className={i < now ? "done" : undefined}>
            <span aria-hidden="true">{st.icon}</span> {st.label}
          </li>
        ))}
      </ol>
      <p className="calm-note">{minutes ? t("calm.time", { n: minutes }) : t("calm.no_time")}</p>
    </nav>
  );
}

/** Where the student is heading: how many more right answers secure this topic, or what comes next. */
function NextStepLine({ step }: { step: NextStep }) {
  const { t } = useSession();
  return (
    <p className="next-step">
      <span aria-hidden="true">🎯 </span>
      {step.kind === "secure_in"
        ? step.n === 1
          ? t("next.secure_in_one", { topic: step.topic })
          : t("next.secure_in", { n: step.n, topic: step.topic })
        : `${t("next.secured", { topic: step.topic })} ${step.next_topic ? t("next.then", { topic: step.next_topic }) : t("next.chapter_done")}`}
    </p>
  );
}
