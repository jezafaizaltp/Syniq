"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, PROGRESS_WORDS, STYLE_WORDS, api, post } from "@/lib/api";
import { speak, useSession } from "@/lib/session";
import Tutor from "./Tutor";

type Subject = { id: number; name: string; chapters: number; language: string };
type Chapter = { id: number; number: number; title: string };
type ChapterDetail = { id: number; title: string; concepts: { id: number; title: string; progress: string }[] };
type Item = { id: number; kind: "mcq" | "numeric"; prompt: string; options: string[]; hint_count: number };
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
type Result = { correct: boolean; feedback: string; progress: string; tip?: string | null; solution?: string };

const KIND_HEADINGS: Record<string, string> = {
  practice: "Practice",
  review: "Quick review",
  prereq_review: "A quick refresher first",
};

export default function Learn() {
  const { me, loading } = useSession();
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
          <h1>Almost ready</h1>
          <p>Your parent or guardian needs to give permission before you can start. Ask them to open SYNiq and check the box for you.</p>
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
      <h1>Hi {me.name}</h1>
      {!subject ? (
        <>
          <p className="muted">What would you like to learn today?</p>
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
                    Open
                  </button>
                ) : (
                  <span className="muted">Coming soon</span>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <>
          <button className="secondary" onClick={() => setSubject(null)}>
            ← All subjects
          </button>
          <h2 style={{ marginTop: 16 }}>{subject.name}</h2>
          <ul className="list card">
            {chapters.map((c) => (
              <li key={c.id}>
                <span>
                  {c.number}. {c.title}
                </span>
                <button onClick={async () => setChapter(await api<ChapterDetail>(`/chapters/${c.id}`))}>Start</button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function CheckIn({ onDone }: { onDone: () => void }) {
  const [message, setMessage] = useState("");
  const moods = [
    ["great", "😀 Great"],
    ["okay", "🙂 Okay"],
    ["low", "😕 Not great"],
    ["frustrated", "😣 Frustrated"],
  ];

  if (message) {
    return (
      <div className="wrap">
        <div className="card">
          <p>{message}</p>
          <button onClick={onDone}>Let&apos;s start</button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="card">
        <h2>How are you feeling right now?</h2>
        <p className="muted">This is optional. You can skip it.</p>
        <div className="options">
          {moods.map(([value, label]) => (
            <button
              key={value}
              className="option"
              onClick={async () => {
                const r = await post<{ message: string }>("/checkins", { mood: value });
                setMessage(r.message);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="row" style={{ marginTop: 16 }}>
          <button className="secondary" onClick={onDone}>
            Skip
          </button>
        </div>
      </div>
    </div>
  );
}

function Session({ chapter, onExit }: { chapter: ChapterDetail; onExit: () => void }) {
  const { me } = useSession();
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
      setError(e instanceof ApiError ? e.message : "Could not load the next step");
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
    if (readAloud) speak([r.feedback, r.tip].filter(Boolean).join(". "));
  }

  if (onBreak) {
    return (
      <div className="wrap">
        <div className="card">
          <h2>Take a short break</h2>
          <p>Stretch, drink some water, look out of the window. Come back whenever you are ready.</p>
          <button onClick={() => setOnBreak(false)}>I&apos;m back</button>
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
        <button className="secondary" onClick={() => setOnBreak(true)}>
          Take a break
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
                Chapter complete
              </h2>
              <p>Every topic here looks secure. SYNiq will bring a few back for quick reviews later so they stay fresh.</p>
              <button onClick={onExit}>Choose another chapter</button>
            </>
          )}

          {step.kind === "explain" && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {step.offer_support ? "Let's try this a different way" : "Let's learn"}
              </h2>
              {step.offer_support && (
                <p className="feedback warn">
                  Would a different explanation help? You can also take a break, or carry on practising if you prefer.
                </p>
              )}
              <p style={{ fontSize: "1.1rem" }}>{step.explanation?.body ?? "No explanation is available yet."}</p>
              <div className="row" role="group" aria-label="Other ways to explain">
                {(step.styles ?? []).map((s) => (
                  <button
                    key={s}
                    className="secondary"
                    aria-pressed={step.explanation?.style === s}
                    onClick={() => switchStyle(s)}
                  >
                    {STYLE_WORDS[s] ?? s}
                  </button>
                ))}
                {step.explanation && (
                  <button className="secondary" onClick={() => speak(step.explanation!.body)}>
                    🔊 Read aloud
                  </button>
                )}
              </div>
              <div className="row" style={{ marginTop: 16 }}>
                <button onClick={next}>I&apos;m ready to practise</button>
              </div>
            </>
          )}

          {step.item && (
            <>
              <h2 ref={headingRef} tabIndex={-1}>
                {KIND_HEADINGS[step.kind]}
              </h2>
              <p style={{ fontSize: "1.2rem" }}>{step.item.prompt}</p>
              <button className="secondary" onClick={() => speak(step.item!.prompt)} aria-label="Read the question aloud">
                🔊
              </button>
              <form onSubmit={submit} style={{ marginTop: 12 }}>
                {step.item.kind === "mcq" ? (
                  <div className="options" role="group" aria-label="Answer choices">
                    {step.item.options.map((o) => (
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
                    <label htmlFor="answer">Your answer</label>
                    <input id="answer" inputMode="decimal" value={answer} disabled={!!result} onChange={(e) => setAnswer(e.target.value)} />
                  </>
                )}

                {hints.map((h, i) => (
                  <p key={i} className="feedback warn">
                    Hint {i + 1}: {h}
                  </p>
                ))}

                {!result && (
                  <div className="row" style={{ marginTop: 16 }}>
                    <button type="submit" disabled={!answer.trim()}>
                      Check
                    </button>
                    {hints.length < step.item.hint_count && (
                      <button type="button" className="secondary" onClick={showHint}>
                        Give me a hint
                      </button>
                    )}
                  </div>
                )}
              </form>

              {result && (
                <div className={`feedback ${result.correct ? "good" : "warn"}`} role="status">
                  <strong>{result.feedback}</strong>
                  {result.tip && <p>{result.tip}</p>}
                  {result.solution && <p>Worked solution: {result.solution}</p>}
                  <p className="muted">This topic: {PROGRESS_WORDS[result.progress] ?? result.progress}</p>
                  <button onClick={next}>Next</button>
                </div>
              )}
            </>
          )}

          {step.kind !== "chapter_complete" && step.concept && !step.item && step.kind !== "explain" && (
            <p className="muted">No approved questions for this topic yet. Your teacher is reviewing them.</p>
          )}

          <p className="why">
            <button className="secondary" onClick={() => setShowWhy(!showWhy)} aria-expanded={showWhy}>
              Why am I seeing this?
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
