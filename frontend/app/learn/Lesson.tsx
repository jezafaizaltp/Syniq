"use client";

import { useEffect, useRef, useState } from "react";
import { post } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { speak, useSession } from "@/lib/session";
import Picture, { type PictureSpec } from "./Picture";
import ReadAlong from "./ReadAlong";

export type LessonWay = { style: string; teach: string; picture?: PictureSpec | null };
export type LessonStep = {
  teach: string;
  picture?: PictureSpec | null;
  ways?: LessonWay[];
  check: { prompt: string; options: string[] };
};
type Marked = { right: boolean; answer?: string; why?: string; retry?: boolean };
type Outcome = { first: boolean; helped: string | null };

const WAY_ICON: Record<string, string> = { text: "💬", visual: "🖼️", step_by_step: "🪜", real_world: "🏠" };

/**
 * Teaching before practice: one idea at a time, each followed by one quick question about just that idea.
 *
 * Each idea can be explained in more than one way; the server puts first the way most likely to work for this
 * learner, and "Explain another way" shows the next. A wrong answer brings another way and one more try before the
 * answer is shown, so the mistake becomes a second way in, not a dead end. "I know some of this" turns it round:
 * the question first, and the teaching only for the ideas that need it. Nothing is marked.
 */
export default function Lesson({
  conceptId,
  steps,
  onDone,
  suggestCheckFirst = null,
}: {
  conceptId: number;
  steps: LessonStep[];
  onDone: () => void;
  // The server's reason to start with the questions: "seen_before" or "knows_some" (learning.lesson_check_first).
  suggestCheckFirst?: string | null;
}) {
  const { t } = useSession();
  const [at, setAt] = useState(0);
  const [wayAt, setWayAt] = useState(0);
  const [switched, setSwitched] = useState(false);
  const [attempt, setAttempt] = useState<1 | 2>(1);
  const [tried, setTried] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [marked, setMarked] = useState<Marked | null>(null);
  const [busy, setBusy] = useState(false);
  const [checkFirst, setCheckFirst] = useState(!!suggestCheckFirst);
  // In "check first", the teaching opens only after a wrong answer (or when asked for).
  const [opened, setOpened] = useState(false);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [summary, setSummary] = useState(false);
  const top = useRef<HTMLDivElement>(null);
  const step = steps[at];
  const ways: LessonWay[] = step?.ways?.length ? step.ways : step ? [{ style: "text", teach: step.teach, picture: step.picture }] : [];
  const way = ways[wayAt % Math.max(ways.length, 1)];
  const last = at === steps.length - 1;
  const teaching = !checkFirst || opened;

  useEffect(() => {
    top.current?.focus();
  }, [at, summary]);

  function anotherWay() {
    setWayAt((wayAt + 1) % ways.length);
    if (!marked) setSwitched(true);
  }

  async function choose(option: string) {
    if ((marked && !marked.retry) || busy || option === tried) return;
    setChosen(option);
    setBusy(true);
    const style = teaching ? way.style : null;
    // A second try is offered when there is something new to look at: another way, or the teaching itself.
    const canRetry = attempt === 1 && (!teaching || ways.length > 1);
    try {
      const r = await post<Marked>("/learn/lesson-check", {
        concept_id: conceptId,
        step: at,
        choice: option,
        style,
        attempt,
        switched: switched && attempt === 1,
        can_retry: canRetry,
      });
      if (r.retry) {
        // Not yet: the same idea another way, then one more go with the first answer set aside.
        setTried(option);
        setAttempt(2);
        setChosen(null);
        if (teaching) setWayAt((wayAt + 1) % ways.length);
        setOpened(true);
        setMarked(r);
        top.current?.focus();
      } else {
        setMarked(r);
        const helped = r.right && (attempt === 2 || switched) && style ? style : null;
        setOutcomes((o) => [...o.slice(0, at), { first: r.right && attempt === 1, helped }]);
      }
    } catch {
      setChosen(null);
    } finally {
      setBusy(false);
    }
  }

  function nextIdea() {
    if (last) {
      const first = outcomes.filter((o) => o.first).length;
      post("/learn/lesson-done", { concept_id: conceptId, steps: steps.length, first_time: first, check_first: checkFirst }).catch(() => undefined);
      setSummary(true);
      return;
    }
    setAt(at + 1);
    setWayAt(0);
    setSwitched(false);
    setAttempt(1);
    setTried(null);
    setChosen(null);
    setMarked(null);
    setOpened(false);
  }

  if (summary) {
    const first = outcomes.filter((o) => o.first).length;
    const helped = outcomes.map((o, i) => ({ ...o, n: i + 1 })).filter((o) => o.helped);
    return (
      <div className="lesson lesson-summary" ref={top} tabIndex={-1} aria-live="polite">
        <h3>{t("lesson.summary_title")}</h3>
        <p>{first === steps.length ? t("lesson.summary_all", { n: steps.length }) : t("lesson.summary_some", { n: first, total: steps.length })}</p>
        {helped.length > 0 && (
          <ul>
            {helped.map((o) => (
              <li key={o.n}>
                {WAY_ICON[o.helped!]} {t("lesson.summary_helped", { n: o.n, way: t(`way.${o.helped}` as Key) })}
              </li>
            ))}
          </ul>
        )}
        {first < steps.length && <p className="muted">{t("lesson.summary_practice")}</p>}
        <div className="row" style={{ marginTop: 12 }}>
          <button onClick={onDone}>{t("lesson.summary_go")}</button>
        </div>
      </div>
    );
  }

  const answered = marked && !marked.retry;
  return (
    <div className="lesson" ref={top} tabIndex={-1} aria-live="polite">
      <p className="lesson-steps" aria-label={t("lesson.step_of", { n: at + 1, total: steps.length })}>
        {steps.map((_, i) => (
          <span key={i} className={i < at ? "dot done" : i === at ? "dot now" : "dot"} aria-hidden="true" />
        ))}
        <span className="muted">{t("lesson.step_of", { n: at + 1, total: steps.length })}</span>
      </p>

      {at === 0 && attempt === 1 && !marked && (
        <p className="lesson-mode">
          {checkFirst && suggestCheckFirst && <span className="muted">{t(`lesson.suggest_${suggestCheckFirst}` as Key)} </span>}
          <button className="secondary small" aria-pressed={checkFirst} onClick={() => setCheckFirst(!checkFirst)}>
            {checkFirst ? t("lesson.teach_me") : t("lesson.check_first")}
          </button>
        </p>
      )}

      {marked?.retry && <p className="feedback warn">{teaching && ways.length > 1 && !checkFirst ? t("lesson.another_way_try") : t("lesson.look_then_try")}</p>}

      {teaching ? (
        <>
          {ways.length > 1 && (
            <p className="muted lesson-way">
              {WAY_ICON[way.style]} {t("lesson.explained", { way: t(`way.${way.style}` as Key) })}
            </p>
          )}
          <ReadAlong key={`${at}-${wayAt}`} style={{ fontSize: "1.1rem" }} text={way.teach} />
          <div className="row">
            <button className="secondary" onClick={() => speak(way.teach)} aria-label={t("learn.read_aloud")}>
              🔊
            </button>
            {ways.length > 1 && (
              <button className="secondary" onClick={anotherWay}>
                🔄 {t("lesson.another_way")}
              </button>
            )}
          </div>
          {way.picture && <Picture picture={way.picture} />}
        </>
      ) : (
        <p className="muted">{t("lesson.check_first_note")}</p>
      )}

      <div className="lesson-check">
        <p>
          <strong>{t("lesson.quick_check")}</strong> {step.check.prompt}
        </p>
        <div className="options" role="group" aria-label={t("learn.choices")}>
          {step.check.options.map((o) => (
            <button
              key={o}
              className={
                answered && o === marked!.answer
                  ? "option right"
                  : (answered && o === chosen && !marked!.right) || o === tried
                    ? "option wrong"
                    : "option"
              }
              aria-pressed={chosen === o}
              disabled={busy || o === tried || (!!answered && o !== chosen && o !== marked!.answer)}
              onClick={() => choose(o)}
            >
              {o}
            </button>
          ))}
        </div>
        {answered && (
          <div className={marked!.right ? "feedback good" : "feedback warn"} role="status">
            <p>
              {marked!.right
                ? attempt === 2
                  ? t("lesson.right_second")
                  : t("lesson.right")
                : t("lesson.not_quite", { answer: marked!.answer ?? "" })}
            </p>
            <p>{marked!.why}</p>
          </div>
        )}
      </div>
      {answered && (
        <div className="row" style={{ marginTop: 12 }}>
          {checkFirst && !opened && (
            <button className="secondary" onClick={() => setOpened(true)}>
              📖 {t("lesson.show_teaching")}
            </button>
          )}
          <button onClick={nextIdea}>{last ? t("lesson.finish") : t("lesson.next_idea")}</button>
        </div>
      )}
    </div>
  );
}
