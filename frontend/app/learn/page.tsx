"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, post } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { speak, useSession } from "@/lib/session";

/** Count a help button press: one of the signs SYNiq uses to notice what helps. */
function helpPressed(kind: "read_aloud" | "break") {
  post("/learn/events", { kind }).catch(() => undefined);
}
import Feedback, { AdaptiveResponse } from "./Feedback";
import Tutor from "./Tutor";

type Subject = { id: number; name: string; chapters: number; language: string };
type Chapter = { id: number; number: number; title: string };
type ChapterDetail = { id: number; title: string; concepts: { id: number; title: string; progress: string }[] };
type Item = { id: number; kind: "mcq" | "numeric"; prompt: string; options: string[]; hint_count: number; choices?: string[] };
type Step = {
  decision_id: number;
  kind: "explain" | "practice" | "review" | "prereq_review" | "chapter_complete";
  reason: string;
  concept: { id: number; title: string } | null;
  offer_support: boolean;
  explanation?: { style: string; body: string } | null;
  styles?: string[];
  item?: Item | null;
};
type Result = {
  correct: boolean;
  feedback: string;
  progress: string;
  tip?: string | null;
  solution?: string;
  response: AdaptiveResponse;
};

const KIND_HEADINGS: Record<string, Key> = {
  practice: "learn.practice",
  review: "learn.review",
  prereq_review: "learn.prereq_review",
};

export default function Learn() {
  const { me, loading, t } = useSession();
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [checkedIn, setCheckedIn] = useState(false);

  useEffect(() => {
    if (!loading && (!me || me.role !== "student")) router.replace("/");
  }, [me, loading, router]);

  useEffect(() => {
    if (me?.role === "student") api<Subject[]>("/subjects").then(setSubjects).catch(() => setSubjects([]));
  }, [me]);

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

  if (chapter && !checkedIn) {
    return <CheckIn onDone={() => setCheckedIn(true)} />;
  }

  if (chapter) {
    return <Session chapter={chapter} onExit={() => setChapter(null)} />;
  }

  return (
    <div className="wrap">
      <h1>{t("learn.hi", { name: me.name })}</h1>
      {!subject ? (
        <>
          <p className="muted">{t("learn.what_today")}</p>
          <ul className="list card">
            {subjects.map((s) => (
              <li key={s.id}>
                <span>{s.name}</span>
                {s.chapters ? (
                  <button
                    className="secondary"
                    onClick={async () => {
                      setSubject(s);
                      setChapters(await api<Chapter[]>(`/subjects/${s.id}/chapters`));
                    }}
                  >
                    {t("learn.open")}
                  </button>
                ) : (
                  <span className="muted">{t("learn.coming_soon")}</span>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <>
          <button className="secondary" onClick={() => setSubject(null)}>
            {t("learn.all_subjects")}
          </button>
          <h2 style={{ marginTop: 16 }}>{subject.name}</h2>
          <ul className="list card">
            {chapters.map((c) => (
              <li key={c.id}>
                <span>
                  {c.number}. {c.title}
                </span>
                <button onClick={async () => setChapter(await api<ChapterDetail>(`/chapters/${c.id}`))}>{t("learn.start")}</button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function CheckIn({ onDone }: { onDone: () => void }) {
  const { t } = useSession();
  const [message, setMessage] = useState("");
  const moods = ["great", "okay", "low", "frustrated"] as const;

  if (message) {
    return (
      <div className="wrap">
        <div className="card">
          <p>{message}</p>
          <button onClick={onDone}>{t("checkin.start")}</button>
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
                const r = await post<{ message: string }>("/checkins", { mood: value });
                setMessage(r.message);
              }}
            >
              {t(`checkin.${value}`)}
            </button>
          ))}
        </div>
        <div className="row" style={{ marginTop: 16 }}>
          <button className="secondary" onClick={onDone}>
            {t("checkin.skip")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Session({ chapter, onExit }: { chapter: ChapterDetail; onExit: () => void }) {
  const { me, t } = useSession();
  const [step, setStep] = useState<Step | null>(null);
  const [answer, setAnswer] = useState("");
  const [hints, setHints] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const [onBreak, setOnBreak] = useState(false);
  const [error, setError] = useState("");
  const conceptRef = useRef<number | null>(null);
  const styleRef = useRef<string | null>(null);
  const startedRef = useRef<number>(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const readAloud = !!me?.settings?.read_aloud;
  const [tutorOn, setTutorOn] = useState(false);

  useEffect(() => {
    api<{ enabled: boolean }>("/ai/status")
      .then((s) => setTutorOn(s.enabled))
      .catch(() => setTutorOn(false));
  }, []);

  async function next() {
    setError("");
    try {
      const s = await post<Step>("/learn/next", { chapter_id: chapter.id, current_concept_id: conceptRef.current });
      conceptRef.current = s.concept?.id ?? null;
      if (s.explanation) styleRef.current = s.explanation.style;
      setStep(s);
      setAnswer("");
      setHints([]);
      setResult(null);
      setShowWhy(false);
      startedRef.current = Date.now();
      if (readAloud) speak(s.explanation?.body ?? s.item?.prompt ?? s.reason);
      requestAnimationFrame(() => headingRef.current?.focus());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("learn.load_failed"));
    }
  }

  useEffect(() => {
    next();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function switchStyle(style: string) {
    if (!step?.concept) return;
    const exp = await api<{ style: string; body: string }>(`/concepts/${step.concept.id}/explanations/${style}`);
    styleRef.current = exp.style;
    setStep({ ...step, explanation: exp });
    if (readAloud) speak(exp.body);
  }

  async function showHint() {
    if (!step?.item) return;
    const h = await api<{ hint: string }>(`/items/${step.item.id}/hints/${hints.length + 1}`);
    setHints([...hints, h.hint]);
    if (readAloud) speak(h.hint);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!step?.item || !answer.trim()) return;
    const r = await post<Result>("/learn/attempts", {
      item_id: step.item.id,
      response: answer.trim(),
      hints_used: hints.length,
      time_ms: Date.now() - startedRef.current,
      explanation_style: styleRef.current,
    });
    setResult(r);
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
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <button className="secondary" onClick={onExit}>
          ← {chapter.title}
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

      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}

      {step && (
        <div className="card" aria-live="polite">
          {step.concept && <p className="muted">{step.concept.title}</p>}

          {step.kind === "chapter_complete" && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {t("learn.chapter_complete")}
              </h2>
              <p>{t("learn.chapter_complete_body")}</p>
              <button onClick={onExit}>{t("learn.another_chapter")}</button>
            </>
          )}

          {step.kind === "explain" && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {step.offer_support ? t("learn.different_way") : t("learn.lets_learn")}
              </h2>
              {step.offer_support && (
                <p className="feedback warn">{t("learn.offer_support")}</p>
              )}
              <p style={{ fontSize: "1.1rem" }}>{step.explanation?.body ?? t("learn.no_explanation")}</p>
              <div className="row" role="group" aria-label={t("learn.other_ways")}>
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
                {step.explanation && (
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
              <p style={{ fontSize: "1.2rem" }}>{step.item.prompt}</p>
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
              <form onSubmit={submit} style={{ marginTop: 12 }}>
                {step.item.kind === "mcq" || step.item.choices?.length ? (
                  <div className="options" role="group" aria-label={t("learn.choices")}>
                    {(step.item.choices?.length ? step.item.choices : step.item.options).map((o) => (
                      <button
                        type="button"
                        key={o}
                        className="option"
                        aria-pressed={answer === o}
                        disabled={!!result}
                        onClick={() => setAnswer(o)}
                      >
                        {o}
                      </button>
                    ))}
                  </div>
                ) : (
                  <>
                    <label htmlFor="answer">{t("learn.your_answer")}</label>
                    <input id="answer" inputMode="decimal" value={answer} disabled={!!result} onChange={(e) => setAnswer(e.target.value)} />
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
                  <Feedback key={step.decision_id} r={result.response} readAloud={readAloud} tutorOn={tutorOn} />
                  <p className="muted">{t("learn.this_topic", { progress: t(`progress.${result.progress}` as Key) })}</p>
                  <button onClick={next}>{t("learn.next")}</button>
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
        <Tutor conceptId={step.concept.id} conceptTitle={step.concept.title} readAloud={readAloud} />
      )}
    </div>
  );
}
