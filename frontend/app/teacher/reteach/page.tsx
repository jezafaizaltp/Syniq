"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type HardTrouble = { concept_id: number; topic: string; chapter: string; students: { student_id: number; name: string }[] };
type LessonTrouble = {
  concept_id: number;
  topic: string;
  chapter: string;
  idea: number;
  check: string;
  tried: number;
  missed_first: number;
  helped: string | null;
};
const HELPED: Record<string, string> = {
  text: "explaining it in plain words",
  visual: "drawing it",
  step_by_step: "going step by step",
  real_world: "a real-life example",
};
type Mistake = { tag: string; text: string; working_on: { student_id: number; name: string }[]; fixed: number; topics: string[] };

/** One page for a short re-teach: each repeated mistake, the topics it shows up in, and who to sit with. */
function Sheet() {
  const { me, loading } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const classId = Number(params.get("class"));
  const [rows, setRows] = useState<Mistake[] | null>(null);
  const [name, setName] = useState("");
  const [hard, setHard] = useState<HardTrouble[]>([]);
  const [ideas, setIdeas] = useState<LessonTrouble[]>([]);
  useEffect(() => {
    if (!loading && (!me || (me.role !== "teacher" && me.role !== "admin"))) router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (!me || !classId) return;
    api<Mistake[]>(`/teacher/classes/${classId}/mistakes`).then(setRows);
    api<HardTrouble[]>(`/teacher/classes/${classId}/hard-trouble`).then(setHard).catch(() => setHard([]));
    api<LessonTrouble[]>(`/teacher/classes/${classId}/lesson-trouble`).then(setIdeas).catch(() => setIdeas([]));
    api<{ id: number; name: string }[]>("/teacher/classes").then((cs) => setName(cs.find((c) => c.id === classId)?.name ?? ""));
  }, [me, classId]);
  if (!rows) return null;
  const open = rows.filter((r) => r.working_on.length > 0);
  return (
    <div className="wrap wide">
      <div className="no-print">
        <p>
          <Link href="/teacher">← Your class</Link>
        </p>
        <button onClick={() => window.print()}>Print</button>
      </div>
      <section className="print-sheet">
        <h1>Re-teach sheet{name ? `: ${name}` : ""}</h1>
        <p className="muted">
          Mistakes students in this class have made more than once and are still working on. Students are listed in
          alphabetical order, never ranked. Keep this sheet with you; don&apos;t put it on the wall.
        </p>
        {open.length === 0 && hard.length === 0 && ideas.length === 0 && <p>Nothing to re-teach right now.</p>}
        {open.map((m) => (
          <article key={m.tag} className="reteach">
            <h2>{m.text}</h2>
            {m.topics.length > 0 && <p className="muted">Seen in: {m.topics.join(", ")}</p>}
            <p>
              <strong>Sit with:</strong> {m.working_on.map((s) => s.name).join(", ")}
              {m.fixed > 0 && <span className="muted"> · {m.fixed} already fixed it</span>}
            </p>
            <p className="sign-line">Notes: ____________________________________________</p>
          </article>
        ))}
        {hard.length > 0 && (
          <>
            <h2>Harder questions to go through together</h2>
            <p className="muted">
              Topics where several students have missed the harder questions twice or more and not got one right yet. Work one
              through on the board, step by step.
            </p>
            {hard.map((h) => (
              <article key={h.concept_id} className="reteach">
                <h3>
                  {h.topic} <span className="muted">({h.chapter})</span>
                </h3>
                <p>
                  <strong>Sit with:</strong> {h.students.map((s) => s.name).join(", ")}
                </p>
              </article>
            ))}
          </>
        )}
        {ideas.length > 0 && (
          <>
            <h2>Lesson ideas the class found hard</h2>
            <p className="muted">
              Ideas from SYNiq&apos;s lessons that half or more of the students who reached them missed the first time.
              Counts only: it&apos;s about the idea, not who. Where one way of explaining helped most on the second try,
              it&apos;s named, so you can use it on the board.
            </p>
            {ideas.map((l) => (
              <article key={`${l.concept_id}-${l.idea}`} className="reteach">
                <h3>
                  {l.topic}, idea {l.idea} <span className="muted">({l.chapter})</span>
                </h3>
                <p>
                  <strong>Its check:</strong> {l.check}
                </p>
                <p className="muted">
                  {l.missed_first} of {l.tried} missed it the first time.
                  {l.helped && ` What helped most after: ${HELPED[l.helped] ?? l.helped}.`}
                </p>
              </article>
            ))}
          </>
        )}
      </section>
    </div>
  );
}

export default function Reteach() {
  return (
    <Suspense fallback={null}>
      <Sheet />
    </Suspense>
  );
}
