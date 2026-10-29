"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, PROGRESS_WORDS, STYLE_WORDS, api, post, put } from "@/lib/api";
import { useSession } from "@/lib/session";
import ContentTools from "./ContentTools";

type Overview = {
  students: number;
  concepts: { concept_id: number; title: string; counts: Record<string, number>; common_misconceptions: string[] }[];
};
type Support = { student_id: number; name: string; concepts: string[] }[];
type Draft = { id: number; concept: string; source: string; review_note: string };
type QueueItem = Draft & {
  kind: string;
  prompt: string;
  options: string[];
  answer: string;
  hints: string[];
  solution: string;
  difficulty: number;
};
type QueueExplanation = Draft & { style: string; body: string };
type Queue = { items: QueueItem[]; explanations: QueueExplanation[] };

const MISCONCEPTION_WORDS: Record<string, string> = {
  square_each_term: "Squares each term, missing 2ab",
  missing_double: "Middle term not doubled",
  sign_middle: "Wrong sign on the middle term",
  sign_last: "Negative last term",
  sum_not_difference: "Adds instead of subtracting squares",
  extra_middle_term: "Keeps a middle term that should cancel",
  product_terms: "Multiplies only first and last terms",
  arithmetic: "Arithmetic slip",
};

const mistakeWords = (tag: string) => MISCONCEPTION_WORDS[tag] ?? tag.replace(/_/g, " ");

function DraftLabel({ d }: { d: Draft }) {
  return (
    <>
      <p className="muted">
        {d.concept}
        {d.source === "ai" && <span className="badge">AI draft</span>}
      </p>
      {d.review_note && <p className="feedback warn">Check: {d.review_note}</p>}
    </>
  );
}

const lines = (s: string) =>
  s
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

function ItemEditor({ item, onDone }: { item: QueueItem; onDone: () => void }) {
  const [f, setF] = useState({
    prompt: item.prompt,
    options: item.options.join("\n"),
    answer: item.answer,
    hints: item.hints.join("\n"),
    solution: item.solution,
    difficulty: item.difficulty,
  });
  const [error, setError] = useState("");
  const field = (k: keyof typeof f) => ({
    id: `edit-${item.id}-${k}`,
    value: f[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value }),
  });

  async function save() {
    try {
      await put(`/teacher/items/${item.id}`, {
        ...f,
        options: lines(f.options),
        hints: lines(f.hints),
        difficulty: Number(f.difficulty),
      });
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save");
    }
  }

  return (
    <div>
      <label htmlFor={`edit-${item.id}-prompt`}>Question</label>
      <textarea {...field("prompt")} />
      {item.kind === "mcq" && (
        <>
          <label htmlFor={`edit-${item.id}-options`}>Options, one per line</label>
          <textarea {...field("options")} />
        </>
      )}
      <label htmlFor={`edit-${item.id}-answer`}>Answer</label>
      <input {...field("answer")} />
      <label htmlFor={`edit-${item.id}-hints`}>Hints, one per line</label>
      <textarea {...field("hints")} />
      <label htmlFor={`edit-${item.id}-solution`}>Worked solution</label>
      <textarea {...field("solution")} />
      <label htmlFor={`edit-${item.id}-difficulty`}>Difficulty</label>
      <select
        id={`edit-${item.id}-difficulty`}
        value={f.difficulty}
        onChange={(e) => setF({ ...f, difficulty: Number(e.target.value) })}
      >
        <option value={1}>1 (easier)</option>
        <option value={2}>2</option>
        <option value={3}>3 (harder)</option>
      </select>
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      <div className="row" style={{ marginTop: 8 }}>
        <button onClick={save}>Save changes</button>
        <button className="secondary" onClick={onDone}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ExplanationEditor({ exp, onDone }: { exp: QueueExplanation; onDone: () => void }) {
  const [body, setBody] = useState(exp.body);
  return (
    <div>
      <label htmlFor={`edit-exp-${exp.id}`}>Explanation</label>
      <textarea id={`edit-exp-${exp.id}`} rows={6} value={body} onChange={(e) => setBody(e.target.value)} />
      <div className="row" style={{ marginTop: 8 }}>
        <button
          onClick={async () => {
            await put(`/teacher/explanations/${exp.id}`, { body });
            onDone();
          }}
          disabled={!body.trim()}
        >
          Save changes
        </button>
        <button className="secondary" onClick={onDone}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function Teacher() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [classId, setClassId] = useState<number | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [support, setSupport] = useState<Support>([]);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [editing, setEditing] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!me || (me.role !== "teacher" && me.role !== "admin"))) router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async () => {
    const classes = await api<{ id: number; name: string }[]>("/teacher/classes");
    if (!classes.length) return;
    const id = classes[0].id;
    const [o, s, q] = await Promise.all([
      api<Overview>(`/teacher/classes/${id}/overview`),
      api<Support>(`/teacher/classes/${id}/support`),
      api<Queue>("/teacher/review-queue"),
    ]);
    setOverview(o);
    setSupport(s);
    setQueue(q);
    setClassId(id);
  }, []);

  useEffect(() => {
    if (me && (me.role === "teacher" || me.role === "admin")) load();
  }, [me, load]);

  async function review(kind: "items" | "explanations", id: number, decision: "approve" | "reject") {
    await post(`/teacher/${kind}/${id}/review`, { decision });
    await reloadQueue();
  }

  async function reloadQueue() {
    setEditing(null);
    setQueue(await api<Queue>("/teacher/review-queue"));
  }

  if (!me || !classId) return null;

  return (
    <div className="wrap wide">
      <h1>Your class</h1>
      <p className="muted">
        {overview?.students ?? 0} students whose families share progress with the school. Students are never ranked.
      </p>

      <section className="card">
        <h2>Where the class is, by topic</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                {Object.values(PROGRESS_WORDS).map((w) => (
                  <th key={w}>{w}</th>
                ))}
                <th>Common mistakes</th>
              </tr>
            </thead>
            <tbody>
              {overview?.concepts.map((c) => (
                <tr key={c.concept_id}>
                  <td>{c.title}</td>
                  {Object.keys(PROGRESS_WORDS).map((k) => (
                    <td key={k}>{c.counts[k] ?? 0}</td>
                  ))}
                  <td>{c.common_misconceptions.map(mistakeWords).join("; ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>May need a hand</h2>
        <p className="muted">Students who have practised a topic several times without it clicking yet.</p>
        {support.length === 0 ? (
          <p>No one right now.</p>
        ) : (
          <ul className="list">
            {support.map((s) => (
              <li key={s.student_id}>
                <span>{s.name}</span>
                <span className="muted">{s.concepts.join(", ")}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <ContentTools onDrafted={reloadQueue} />

      <section className="card">
        <h2>Content waiting for review</h2>
        <p className="muted">Nothing reaches students until a teacher approves it.</p>
        {queue?.items.length === 0 && queue?.explanations.length === 0 && <p>All caught up.</p>}
        {queue?.items.map((i) => (
          <div key={`i${i.id}`} className="card">
            <DraftLabel d={i} />
            {editing === `i${i.id}` ? (
              <ItemEditor item={i} onDone={reloadQueue} />
            ) : (
              <>
                <p className="muted">Difficulty {i.difficulty}</p>
                <p>
                  <strong>{i.prompt}</strong>
                </p>
                {i.options.length > 0 && <p>Options: {i.options.join(" | ")}</p>}
                <p>Answer: {i.answer}</p>
                <p>Hints: {i.hints.join(" / ")}</p>
                <p>Solution: {i.solution}</p>
                <div className="row">
                  <button onClick={() => review("items", i.id, "approve")}>Approve</button>
                  <button className="secondary" onClick={() => setEditing(`i${i.id}`)}>
                    Edit
                  </button>
                  <button className="secondary" onClick={() => review("items", i.id, "reject")}>
                    Reject
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
        {queue?.explanations.map((e) => (
          <div key={`e${e.id}`} className="card">
            <DraftLabel d={e} />
            {editing === `e${e.id}` ? (
              <ExplanationEditor exp={e} onDone={reloadQueue} />
            ) : (
              <>
                <p className="muted">Style: {STYLE_WORDS[e.style] ?? e.style}</p>
                <p>{e.body}</p>
                <div className="row">
                  <button onClick={() => review("explanations", e.id, "approve")}>Approve</button>
                  <button className="secondary" onClick={() => setEditing(`e${e.id}`)}>
                    Edit
                  </button>
                  <button className="secondary" onClick={() => review("explanations", e.id, "reject")}>
                    Reject
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>
    </div>
  );
}
