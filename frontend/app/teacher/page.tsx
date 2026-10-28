"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PROGRESS_WORDS, api, post } from "@/lib/api";
import { useSession } from "@/lib/session";

type Overview = {
  students: number;
  concepts: { concept_id: number; title: string; counts: Record<string, number>; common_misconceptions: string[] }[];
};
type Support = { student_id: number; name: string; concepts: string[] }[];
type Queue = {
  items: { id: number; concept: string; prompt: string; options: string[]; answer: string; hints: string[]; solution: string; difficulty: number }[];
  explanations: { id: number; concept: string; style: string; body: string }[];
};

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

export default function Teacher() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [classId, setClassId] = useState<number | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [support, setSupport] = useState<Support>([]);
  const [queue, setQueue] = useState<Queue | null>(null);

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
                  <td>{c.common_misconceptions.map((m) => MISCONCEPTION_WORDS[m] ?? m).join("; ") || "—"}</td>
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

      <section className="card">
        <h2>Content waiting for review</h2>
        <p className="muted">Nothing reaches students until a teacher approves it.</p>
        {queue?.items.length === 0 && queue?.explanations.length === 0 && <p>All caught up.</p>}
        {queue?.items.map((i) => (
          <div key={i.id} className="card">
            <p className="muted">
              {i.concept} · difficulty {i.difficulty}
            </p>
            <p>
              <strong>{i.prompt}</strong>
            </p>
            {i.options.length > 0 && <p>Options: {i.options.join(" | ")}</p>}
            <p>Answer: {i.answer}</p>
            <p>Hints: {i.hints.join(" / ")}</p>
            <p>Solution: {i.solution}</p>
            <div className="row">
              <button onClick={() => review("items", i.id, "approve")}>Approve</button>
              <button className="secondary" onClick={() => review("items", i.id, "reject")}>
                Reject
              </button>
            </div>
          </div>
        ))}
        {queue?.explanations.map((e) => (
          <div key={e.id} className="card">
            <p className="muted">
              {e.concept} · {e.style}
            </p>
            <p>{e.body}</p>
            <div className="row">
              <button onClick={() => review("explanations", e.id, "approve")}>Approve</button>
              <button className="secondary" onClick={() => review("explanations", e.id, "reject")}>
                Reject
              </button>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
