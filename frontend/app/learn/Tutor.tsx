"use client";

import { useEffect, useState } from "react";
import { ApiError, post } from "@/lib/api";
import { speak } from "@/lib/session";

type Turn = { role: "student" | "tutor"; text: string };

/** Ask SYNiq about the current topic. The conversation stays in this page and is not saved. */
export default function Tutor({ conceptId, conceptTitle, readAloud }: { conceptId: number; conceptTitle: string; readAloud: boolean }) {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // A new topic starts a fresh conversation.
  useEffect(() => {
    setTurns([]);
    setError("");
  }, [conceptId]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const question = text.trim();
    if (!question || busy) return;
    const history: Turn[] = [...turns, { role: "student", text: question }];
    setTurns(history);
    setText("");
    setBusy(true);
    setError("");
    try {
      // Only the last few turns are sent, to keep each request small.
      const r = await post<{ reply: string }>("/tutor", { concept_id: conceptId, history: history.slice(-12) });
      setTurns([...history, { role: "tutor", text: r.reply }]);
      if (readAloud) speak(r.reply);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the tutor");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="row">
        <button className="secondary" onClick={() => setOpen(true)}>
          💬 Ask SYNiq about this topic
        </button>
      </div>
    );
  }

  return (
    <section className="card" aria-label="Ask SYNiq">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Ask SYNiq</h2>
        <button className="secondary" onClick={() => setOpen(false)}>
          Close
        </button>
      </div>
      <p className="muted">
        Ask anything about {conceptTitle}. Please don&apos;t share your name, phone number or address. This chat isn&apos;t
        saved, and SYNiq can make mistakes, so check with your teacher if something seems off.
      </p>
      <div className="chat" aria-live="polite">
        {turns.map((t, i) => (
          <p key={i} className={t.role}>
            <span className="sr-only">{t.role === "student" ? "You: " : "SYNiq: "}</span>
            {t.text}
          </p>
        ))}
        {busy && <p className="tutor muted">Thinking…</p>}
      </div>
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={send}>
        <label htmlFor="tutor-q">Your question</label>
        <textarea id="tutor-q" value={text} maxLength={600} onChange={(e) => setText(e.target.value)} />
        <div className="row" style={{ marginTop: 8 }}>
          <button type="submit" disabled={!text.trim() || busy}>
            Ask
          </button>
        </div>
      </form>
    </section>
  );
}
