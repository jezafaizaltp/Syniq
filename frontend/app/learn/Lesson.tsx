"use client";

import { useEffect, useRef, useState } from "react";
import { post } from "@/lib/api";
import { speak, useSession } from "@/lib/session";
import Picture, { type PictureSpec } from "./Picture";
import ReadAlong from "./ReadAlong";

export type LessonStep = { teach: string; picture?: PictureSpec | null; check: { prompt: string; options: string[] } };
type Marked = { right: boolean; answer: string; why: string };

/**
 * Teaching before practice: one idea at a time, each followed by one quick question about just that idea.
 * Whatever the child taps, they see why the right answer is right before the next idea. Nothing is marked.
 */
export default function Lesson({ conceptId, steps, onDone }: { conceptId: number; steps: LessonStep[]; onDone: () => void }) {
  const { t } = useSession();
  const [at, setAt] = useState(0);
  const [chosen, setChosen] = useState<string | null>(null);
  const [marked, setMarked] = useState<Marked | null>(null);
  const [busy, setBusy] = useState(false);
  const top = useRef<HTMLDivElement>(null);
  const step = steps[at];
  const last = at === steps.length - 1;

  useEffect(() => {
    top.current?.focus();
  }, [at]);

  async function choose(option: string) {
    if (marked || busy) return;
    setChosen(option);
    setBusy(true);
    try {
      setMarked(await post<Marked>("/learn/lesson-check", { concept_id: conceptId, step: at, choice: option }));
    } catch {
      setMarked(null);
      setChosen(null);
    } finally {
      setBusy(false);
    }
  }

  function nextIdea() {
    if (last) return onDone();
    setAt(at + 1);
    setChosen(null);
    setMarked(null);
  }

  return (
    <div className="lesson" ref={top} tabIndex={-1} aria-live="polite">
      <p className="lesson-steps" aria-label={t("lesson.step_of", { n: at + 1, total: steps.length })}>
        {steps.map((_, i) => (
          <span key={i} className={i < at ? "dot done" : i === at ? "dot now" : "dot"} aria-hidden="true" />
        ))}
        <span className="muted">{t("lesson.step_of", { n: at + 1, total: steps.length })}</span>
      </p>
      <ReadAlong style={{ fontSize: "1.1rem" }} text={step.teach} />
      <button className="secondary" onClick={() => speak(step.teach)} aria-label={t("learn.read_aloud")}>
        🔊
      </button>
      {step.picture && <Picture picture={step.picture} />}

      <div className="lesson-check">
        <p>
          <strong>{t("lesson.quick_check")}</strong> {step.check.prompt}
        </p>
        <div className="options" role="group" aria-label={t("learn.choices")}>
          {step.check.options.map((o) => (
            <button
              key={o}
              className={
                marked && o === marked.answer ? "option right" : marked && o === chosen && !marked.right ? "option wrong" : "option"
              }
              aria-pressed={chosen === o}
              disabled={busy || (!!marked && o !== chosen && o !== marked.answer)}
              onClick={() => choose(o)}
            >
              {o}
            </button>
          ))}
        </div>
        {marked && (
          <div className={marked.right ? "feedback good" : "feedback warn"} role="status">
            <p>{marked.right ? t("lesson.right") : t("lesson.not_quite", { answer: marked.answer })}</p>
            <p>{marked.why}</p>
          </div>
        )}
      </div>
      {marked && (
        <div className="row" style={{ marginTop: 12 }}>
          <button onClick={nextIdea}>{last ? t("lesson.finish") : t("lesson.next_idea")}</button>
        </div>
      )}
    </div>
  );
}
