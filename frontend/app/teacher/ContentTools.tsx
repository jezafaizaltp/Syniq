"use client";

import { useEffect, useState } from "react";
import { ApiError, api, post, put } from "@/lib/api";

type Subject = { id: number; name: string; code: string };
type Chapter = { id: number; number: number; title: string };
type Topic = { id: number; title: string };
type TopicDetail = {
  id: number;
  title: string;
  notes: string;
  items: Record<string, number>;
  explanations: Record<string, number>;
};
type DraftResult = { explanations: number; items: number; dropped: number; reviewer_notes: string };

function counts(c: Record<string, number>) {
  return `${c.approved ?? 0} approved, ${c.draft ?? 0} waiting for review`;
}

/** Set up SCERT chapters, write topic notes, and draft content for review. */
export default function ContentTools({ onDrafted }: { onDrafted: () => void }) {
  const [aiOn, setAiOn] = useState(false);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chapterId, setChapterId] = useState<number | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [count, setCount] = useState(6);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [newChapter, setNewChapter] = useState({ number: "", title: "", topics: "" });

  useEffect(() => {
    api<{ enabled: boolean }>("/ai/status")
      .then((s) => setAiOn(s.enabled))
      .catch(() => setAiOn(false));
    api<Subject[]>("/subjects").then(setSubjects);
  }, []);

  async function chooseSubject(id: number) {
    setSubjectId(id);
    setChapterId(null);
    setTopics([]);
    setTopic(null);
    setChapters(await api<Chapter[]>(`/subjects/${id}/chapters`));
  }

  async function chooseChapter(id: number) {
    setChapterId(id);
    setTopic(null);
    setTopics((await api<{ concepts: Topic[] }>(`/chapters/${id}`)).concepts);
  }

  async function chooseTopic(id: number) {
    const t = await api<TopicDetail>(`/teacher/concepts/${id}`);
    setTopic(t);
    setNotes(t.notes);
    setMessage("");
  }

  async function addChapter(e: React.FormEvent) {
    e.preventDefault();
    if (!subjectId) return;
    const titles = newChapter.topics
      .split("\n")
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      const r = await post<{ id: number }>("/teacher/chapters", {
        subject_id: subjectId,
        number: Number(newChapter.number),
        title: newChapter.title,
        concepts: titles.map((title) => ({ title })),
      });
      setNewChapter({ number: "", title: "", topics: "" });
      setChapters(await api<Chapter[]>(`/subjects/${subjectId}/chapters`));
      await chooseChapter(r.id);
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not add the chapter");
    }
  }

  async function saveNotes() {
    if (!topic) return;
    await put(`/teacher/concepts/${topic.id}/notes`, { notes });
    setTopic({ ...topic, notes });
    setMessage("Notes saved.");
  }

  async function draft() {
    if (!topic) return;
    setBusy(true);
    setMessage("Drafting. This can take a minute or two…");
    try {
      if (notes !== topic.notes) await put(`/teacher/concepts/${topic.id}/notes`, { notes });
      const r = await post<DraftResult>(`/teacher/concepts/${topic.id}/draft`, { count });
      const skipped = r.dropped ? ` ${r.dropped} unusable question${r.dropped > 1 ? "s were" : " was"} left out.` : "";
      setMessage(
        `Added ${r.explanations} explanation${r.explanations === 1 ? "" : "s"} and ${r.items} question${r.items === 1 ? "" : "s"} to the review queue.${skipped}`
      );
      setTopic(await api<TopicDetail>(`/teacher/concepts/${topic.id}`));
      onDrafted();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Drafting failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Add chapter content</h2>
      <p className="muted">
        Set up a chapter from the SCERT textbook, write short notes for each topic on what the textbook covers, then draft
        explanations and questions{aiOn ? " with AI" : ""}. Everything goes to the review queue below first.
      </p>

      <label htmlFor="ct-subject">Subject</label>
      <select id="ct-subject" value={subjectId ?? ""} onChange={(e) => chooseSubject(Number(e.target.value))}>
        <option value="" disabled>
          Choose a subject
        </option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      {subjectId && (
        <>
          <label htmlFor="ct-chapter">Chapter</label>
          <select id="ct-chapter" value={chapterId ?? ""} onChange={(e) => chooseChapter(Number(e.target.value))}>
            <option value="" disabled>
              {chapters.length ? "Choose a chapter" : "No chapters yet: add one below"}
            </option>
            {chapters.map((c) => (
              <option key={c.id} value={c.id}>
                {c.number}. {c.title}
              </option>
            ))}
          </select>

          <details style={{ marginTop: 12 }}>
            <summary>Add a new chapter</summary>
            <form onSubmit={addChapter}>
              <label htmlFor="nc-number">Chapter number</label>
              <input
                id="nc-number"
                inputMode="numeric"
                value={newChapter.number}
                onChange={(e) => setNewChapter({ ...newChapter, number: e.target.value })}
              />
              <label htmlFor="nc-title">Chapter title, as in the textbook</label>
              <input id="nc-title" value={newChapter.title} onChange={(e) => setNewChapter({ ...newChapter, title: e.target.value })} />
              <label htmlFor="nc-topics">Topics, one per line, in teaching order</label>
              <textarea id="nc-topics" value={newChapter.topics} onChange={(e) => setNewChapter({ ...newChapter, topics: e.target.value })} />
              <div className="row" style={{ marginTop: 8 }}>
                <button type="submit" disabled={!newChapter.number || !newChapter.title.trim() || !newChapter.topics.trim()}>
                  Add chapter
                </button>
              </div>
            </form>
          </details>
        </>
      )}

      {chapterId && (
        <>
          <label htmlFor="ct-topic">Topic</label>
          <select id="ct-topic" value={topic?.id ?? ""} onChange={(e) => chooseTopic(Number(e.target.value))}>
            <option value="" disabled>
              Choose a topic
            </option>
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </>
      )}

      {topic && (
        <>
          <p className="muted">
            Questions: {counts(topic.items)}. Explanations: {counts(topic.explanations)}.
          </p>
          <label htmlFor="ct-notes">What the textbook says about this topic</label>
          <textarea
            id="ct-notes"
            rows={6}
            value={notes}
            placeholder="Key ideas, methods and notation the textbook uses, and the kind of examples it gives."
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="row" style={{ marginTop: 8, alignItems: "center" }}>
            <button className="secondary" onClick={saveNotes} disabled={notes === topic.notes}>
              Save notes
            </button>
            {aiOn && (
              <>
                <label htmlFor="ct-count" className="sr-only">
                  Number of questions
                </label>
                <select id="ct-count" value={count} onChange={(e) => setCount(Number(e.target.value))} style={{ width: "auto" }}>
                  {[3, 6, 10].map((n) => (
                    <option key={n} value={n}>
                      {n} questions
                    </option>
                  ))}
                </select>
                <button onClick={draft} disabled={busy}>
                  Draft with AI
                </button>
              </>
            )}
          </div>
          {!aiOn && <p className="muted">AI drafting is not switched on for this server.</p>}
        </>
      )}

      {message && (
        <p className="feedback good" role="status">
          {message}
        </p>
      )}
    </section>
  );
}
