"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, post } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { speak, useSession } from "@/lib/session";

type CheckItem = { id: number; kind: "mcq" | "numeric"; prompt: string; options: string[]; choices?: string[]; keyboard?: "text" | "decimal" };
export type CheckState = {
  id: number;
  kind: "start" | "end" | "retention";
  status: "open" | "done" | "skipped";
  total: number;
  answered: number;
  item: CheckItem | null;
  summary?: { known: string[]; start_with: string[] };
};

/** A short subject check: one question per topic, no right/wrong per question, no score at the end. */
export default function Check({
  subjectId,
  subjectName,
  kind,
  onDone,
}: {
  subjectId: number;
  subjectName: string;
  kind: CheckState["kind"];
  onDone: () => void;
}) {
  const { me, t } = useSession();
  const [check, setCheck] = useState<CheckState | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const readAloud = !!me?.settings?.read_aloud;

  useEffect(() => {
    post<CheckState>("/checks", { subject_id: subjectId, kind })
      .then(setCheck)
      .catch((e) => setError(e instanceof ApiError ? e.message : t("learn.load_failed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjectId, kind]);

  useEffect(() => {
    setAnswer("");
    if (check?.item && readAloud) speak(check.item.prompt);
    requestAnimationFrame(() => headingRef.current?.focus());
  }, [check?.item?.id, check?.status, readAloud]); // eslint-disable-line react-hooks/exhaustive-deps

  async function send(response: string) {
    if (!check?.item || busy) return;
    setBusy(true);
    try {
      setCheck(await post<CheckState>(`/checks/${check.id}/answer`, { item_id: check.item.id, response }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("learn.load_failed"));
    } finally {
      setBusy(false);
    }
  }

  async function skip() {
    if (check) await post(`/checks/${check.id}/skip`, {}).catch(() => undefined);
    else await post("/checks/skip-start", { subject_id: subjectId }).catch(() => undefined);
    onDone();
  }

  const title = t(`check.title.${kind}` as Key, { subject: subjectName });

  if (error) {
    return (
      <div className="wrap">
        <div className="card">
          <h2>{title}</h2>
          <p className="feedback warn" role="alert">
            {error}
          </p>
          <button onClick={onDone}>{t("check.back")}</button>
        </div>
      </div>
    );
  }

  if (!check) return null;

  if (check.status === "done" && check.summary) {
    return (
      <div className="wrap">
        <div className="card" aria-live="polite">
          <h2 ref={headingRef} tabIndex={-1}>
            {t("check.thanks")}
          </h2>
          {kind === "start" ? (
            <>
              {check.summary.known.length > 0 && (
                <>
                  <p>{t("check.known")}</p>
                  <ul>
                    {check.summary.known.map((x, i) => (
                      <li key={i}>{x}</li>
                    ))}
                  </ul>
                </>
              )}
              {check.summary.start_with.length > 0 && (
                <>
                  <p>{t("check.start_with")}</p>
                  <ul>
                    {check.summary.start_with.map((x, i) => (
                      <li key={i}>{x}</li>
                    ))}
                  </ul>
                </>
              )}
              <p className="muted">{t("check.not_a_test")}</p>
            </>
          ) : (
            <p>{t("check.thanks_later")}</p>
          )}
          <button onClick={onDone}>{t("check.continue")}</button>
        </div>
      </div>
    );
  }

  const item = check.item;
  return (
    <div className="wrap">
      <div className="card" aria-live="polite">
        <p className="muted">
          {title} · {t("check.progress", { n: check.answered + 1, total: check.total })}
        </p>
        {check.answered === 0 && <p>{t(`check.intro.${kind}` as Key)}</p>}
        {item && (
          <>
            <h2 ref={headingRef} tabIndex={-1} style={{ fontSize: "1.2rem" }}>
              {item.prompt}
            </h2>
            <button className="secondary" aria-label={t("learn.read_question")} onClick={() => speak(item.prompt)}>
              🔊
            </button>
            <form
              style={{ marginTop: 12 }}
              onSubmit={(e) => {
                e.preventDefault();
                if (answer.trim()) send(answer.trim());
              }}
            >
              {item.kind === "mcq" || item.choices?.length ? (
                <div className="options" role="group" aria-label={t("learn.choices")}>
                  {(item.choices?.length ? item.choices : item.options).map((o) => (
                    <button type="button" key={o} className="option" aria-pressed={answer === o} onClick={() => setAnswer(o)}>
                      {o}
                    </button>
                  ))}
                </div>
              ) : (
                <>
                  <label htmlFor="check-answer">{t("learn.your_answer")}</label>
                  <input id="check-answer" inputMode={item.keyboard ?? "decimal"} value={answer} onChange={(e) => setAnswer(e.target.value)} />
                </>
              )}
              <div className="row" style={{ marginTop: 16 }}>
                <button type="submit" disabled={!answer.trim() || busy}>
                  {t("check.next")}
                </button>
                <button type="button" className="secondary" disabled={busy} onClick={() => send("")}>
                  {t("check.not_learnt")}
                </button>
              </div>
            </form>
          </>
        )}
        <div className="row" style={{ marginTop: 24 }}>
          <button className="secondary" onClick={kind === "start" ? skip : onDone}>
            {kind === "start" ? t("check.skip") : t("check.later")}
          </button>
        </div>
      </div>
    </div>
  );
}
