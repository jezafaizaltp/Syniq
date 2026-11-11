"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Row = {
  subject_id: number;
  subject: string;
  code: string;
  chapters: number;
  topics: number;
  questions: number;
  by_level: Record<string, number>;
  topics_without_questions: number;
  topics_without_explanations: number;
  topics_without_activity: number;
  topics_without_hard: number;
};

/** What content each subject has, and where it is thin: no questions, no explanation, no activity, no harder question. */
export default function Coverage() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [filter, setFilter] = useState("");
  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role === "admin") api<Row[]>("/admin/coverage").then(setRows).catch(() => setRows([]));
  }, [me]);
  if (!rows) return null;
  const shown = rows.filter((r) => !filter || `${r.subject} ${r.code}`.toLowerCase().includes(filter.toLowerCase()));
  const gap = (n: number) => (n > 0 ? "gap" : undefined);
  return (
    <div className="wrap wide">
      <p>
        <Link href="/admin">← School setup</Link>
      </p>
      <h1>Content coverage</h1>
      <p className="muted">
        Approved questions per subject at each level (1 easier, 3 harder), and how many topics still lack something. A
        number in orange is worth a look before students reach that subject.
      </p>
      <label htmlFor="cov-filter">Find a subject</label>
      <input id="cov-filter" value={filter} placeholder="e.g. Kerala Class 9" onChange={(e) => setFilter(e.target.value)} />
      <div className="table-scroll">
        <table className="coverage-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Chapters</th>
              <th>Topics</th>
              <th>Questions</th>
              <th>Level 1 / 2 / 3</th>
              <th>Topics with no questions</th>
              <th>no explanation</th>
              <th>no activity</th>
              <th>no harder question</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.subject_id}>
                <td>
                  {r.subject} <span className="muted">({r.code})</span>
                </td>
                <td>{r.chapters}</td>
                <td>{r.topics}</td>
                <td>{r.questions}</td>
                <td>
                  {r.by_level["1"]} / {r.by_level["2"]} / {r.by_level["3"]}
                </td>
                <td className={gap(r.topics_without_questions)}>{r.topics_without_questions}</td>
                <td className={gap(r.topics_without_explanations)}>{r.topics_without_explanations}</td>
                <td className={gap(r.topics_without_activity)}>{r.topics_without_activity}</td>
                <td>{r.topics_without_hard}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
