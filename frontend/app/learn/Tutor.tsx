"use client";

import { useEffect, useState } from "react";
import { ApiError, post } from "@/lib/api";
import { speak, useSession } from "@/lib/session";
import Picture, { PictureSpec } from "./Picture";

type Action = "explain" | "picture" | "example" | "steps" | "test" | "hint";
type Turn = {
  role: "student" | "tutor";
  text: string;
  source?: "notes" | "ai" | "none";
  picture?: PictureSpec | null;
  options?: string[] | null;
};
type TutorReply = {
  reply: string;
  source: "notes" | "ai" | "none";
  picture: PictureSpec | null;
  quiz: { prompt: string; options: string[] | null } | null;
  chips: Action[];
  state: Record<string, unknown>;
};

const FIRST_CHIPS: Action[] = ["explain", "picture", "example", "steps", "test"];

/**
 * Ask SYNiq about the current topic. It answers from the topic's own explanations,
 * pictures and questions first; only what those don't cover goes further. The
 * conversation stays in this page and is not saved.
 */
export default function Tutor({
  conceptId,
  conceptTitle,
  readAloud,
  itemId,
}: {
  conceptId: number;
  conceptTitle: string;
  readAloud: boolean;
  /** The question being answered on this page: the tutor gives hints for it, never the answer. */
  itemId?: number | null;
}) {
  const { t } = useSession();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [chips, setChips] = useState<Action[]>(FIRST_CHIPS);
  const [state, setState] = useState<Record<string, unknown>>({});
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // A new topic starts a fresh conversation.
  useEffect(() => {
    setTurns([]);
    setChips(FIRST_CHIPS);
    setState({});
    setError("");
  }, [conceptId]);

  async function ask(question: string, action: Action | null = null) {
    if (!question.trim() || busy) return;
    const history: Turn[] = [...turns, { role: "student", text: question }];
    setTurns(history);
    setText("");
    setBusy(true);
    setError("");
    try {
      // Only the last few turns are sent, to keep each request small.
      const r = await post<TutorReply>("/tutor", {
        concept_id: conceptId,
        history: history.slice(-12).map(({ role, text }) => ({ role, text })),
        action,
        state,
        item_id: itemId ?? null,
      });
      setTurns([
        ...history,
        { role: "tutor", text: r.reply, source: r.source, picture: r.picture, options: r.quiz?.options ?? null },
      ]);
      setChips(r.chips ?? []);
      setState(r.state ?? {});
      if (readAloud) speak(r.reply);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("tutor.failed"));
    } finally {
      setBusy(false);
    }
  }

  function send(e: React.FormEvent) {
    e.preventDefault();
    ask(text.trim());
  }

  if (!open) {
    return (
      <div className="row">
        <button className="secondary" onClick={() => setOpen(true)}>
          {t("tutor.open")}
        </button>
      </div>
    );
  }

  const last = turns[turns.length - 1];
  return (
    <section className="card" aria-label={t("tutor.title")}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("tutor.title")}</h2>
        <button className="secondary" onClick={() => setOpen(false)}>
          {t("tutor.close")}
        </button>
      </div>
      <p className="muted">{t("tutor.note", { topic: conceptTitle })}</p>
      <div className="chat" aria-live="polite">
        {turns.map((turn, i) => (
          <div key={i} className={turn.role}>
            <span className="sr-only">{turn.role === "student" ? t("tutor.you") : "SYNiq: "}</span>
            <p>{turn.text}</p>
            {turn.picture && <Picture picture={turn.picture} />}
            {turn.options && turn === last && (
              <div className="tutor-options">
                {turn.options.map((o) => (
                  <button key={o} type="button" className="option" disabled={busy} onClick={() => ask(o)}>
                    {o}
                  </button>
                ))}
              </div>
            )}
            {turn.role === "tutor" && turn.source === "ai" && <span className="tutor-source">{t("tutor.from_ai")}</span>}
          </div>
        ))}
        {busy && <p className="tutor muted">{t("tutor.thinking")}</p>}
      </div>
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      {chips.length > 0 && (
        <div className="tutor-chips" aria-label={t("tutor.quick")}>
          {chips.map((c) => (
            <button key={c} type="button" className="secondary chip" disabled={busy} onClick={() => ask(t(`tutor.chip.${c}`), c)}>
              {t(`tutor.chip.${c}`)}
            </button>
          ))}
        </div>
      )}
      <form onSubmit={send}>
        <label htmlFor="tutor-q">{t("tutor.question")}</label>
        <textarea id="tutor-q" value={text} maxLength={600} onChange={(e) => setText(e.target.value)} />
        <div className="row" style={{ marginTop: 8 }}>
          <button type="submit" disabled={!text.trim() || busy}>
            {t("tutor.ask")}
          </button>
        </div>
      </form>
    </section>
  );
}
