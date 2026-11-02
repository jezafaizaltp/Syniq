"use client";

import { useEffect, useState } from "react";
import { ApiError, api, del, post } from "@/lib/api";
import { useSession } from "@/lib/session";

export type NoteRow = { id: number; body: string; concept_id: number | null; topic: string | null; updated_at: string };

/** The student's own notes for the topic they are on. Only they can see them. */
export default function Notes({ conceptId, conceptTitle }: { conceptId: number; conceptTitle: string }) {
  const { t } = useSession();
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState<NoteRow[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setText("");
    setError("");
    if (open) api<NoteRow[]>(`/me/notes?concept_id=${conceptId}`).then(setNotes).catch(() => setNotes([]));
  }, [conceptId, open]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      const n = await post<NoteRow>("/me/notes", { body: text.trim(), concept_id: conceptId });
      setNotes([n, ...notes]);
      setText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("notes.failed"));
    }
  }

  return (
    <div className="card">
      <button className="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        📝 {t("notes.button", { topic: conceptTitle })}
      </button>
      {open && (
        <>
          <p className="muted">{t("notes.private")}</p>
          <form onSubmit={save}>
            <label htmlFor="note">{t("notes.label")}</label>
            <textarea id="note" maxLength={2000} rows={3} value={text} onChange={(e) => setText(e.target.value)} />
            <div className="row" style={{ marginTop: 8 }}>
              <button type="submit" disabled={!text.trim()}>
                {t("notes.save")}
              </button>
            </div>
          </form>
          {error && (
            <p className="feedback warn" role="alert">
              {error}
            </p>
          )}
          <ul className="list">
            {notes.map((n) => (
              <li key={n.id}>
                <span style={{ whiteSpace: "pre-wrap" }}>{n.body}</span>
                <button
                  className="secondary"
                  aria-label={t("notes.delete")}
                  onClick={async () => {
                    await del(`/me/notes/${n.id}`).catch(() => undefined);
                    setNotes(notes.filter((x) => x.id !== n.id));
                  }}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
