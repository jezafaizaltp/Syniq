"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, post } from "@/lib/api";

type Entry = { kind: string; round_id: number | null; students: number; average_right: number | null; change_from_start: number | null };
type Report = {
  rounds: { id: number; kind: "end" | "retention"; opened_at: string; open: boolean }[];
  subjects: { subject: string; checks: Entry[] }[];
  min_group: number;
};

const KIND_WORDS: Record<string, string> = { start: "Starting check", end: "End-of-term check", retention: "Remember-it check" };

/** SYNiq's own subject checks: start, end of term, and four weeks later. Group results only. */
export default function SubjectChecks() {
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    api<Report>("/admin/checks").then(setReport).catch(() => setReport(null));
  }, []);
  useEffect(load, [load]);

  async function act(path: string, body: unknown, done: string) {
    setMessage("");
    try {
      await post(path, body);
      setMessage(done);
      load();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Something went wrong");
    }
  }

  if (!report) return null;
  const open = report.rounds.filter((r) => r.open);
  const roundName = (e: Entry) => {
    if (e.kind === "start") return KIND_WORDS.start;
    const r = report.rounds.find((x) => x.id === e.round_id);
    return `${KIND_WORDS[e.kind]}${r ? `, opened ${r.opened_at.slice(0, 10)}` : ""}`;
  };

  return (
    <section className="card">
      <h2>SYNiq&apos;s subject checks</h2>
      <p className="muted">
        Every student is offered a short starting check in each subject (up to 12 questions, optional). Open the end-of-term check
        near the end of the pilot, and the remember-it check about 4 weeks after that, to see what was learnt and what stayed.
        Students never see a score. Here you see the share of questions answered right, for groups of {report.min_group} or more.
        The change from start counts only students who took both checks.
      </p>
      <div className="row">
        {(["end", "retention"] as const).map((kind) => {
          const r = open.find((x) => x.kind === kind);
          return r ? (
            <button key={kind} className="secondary" onClick={() => act(`/admin/check-rounds/${r.id}/close`, {}, `${KIND_WORDS[kind]} closed.`)}>
              Close the {KIND_WORDS[kind].toLowerCase()}
            </button>
          ) : (
            <button key={kind} onClick={() => act("/admin/check-rounds", { kind }, `${KIND_WORDS[kind]} opened for every student.`)}>
              Open the {KIND_WORDS[kind].toLowerCase()}
            </button>
          );
        })}
      </div>
      {message && <p className="feedback good">{message}</p>}
      {report.subjects.length === 0 ? (
        <p className="muted">No checks finished yet.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Subject</th>
                <th>Check</th>
                <th>Students</th>
                <th>Answered right</th>
                <th>Change from start</th>
              </tr>
            </thead>
            <tbody>
              {report.subjects.flatMap((s) =>
                s.checks.map((e, i) => (
                  <tr key={`${s.subject}-${e.kind}-${e.round_id}`}>
                    <td>{i === 0 ? s.subject : ""}</td>
                    <td>{roundName(e)}</td>
                    <td>{e.students}</td>
                    <td>{e.average_right === null ? <span className="muted">Too few to show</span> : `${e.average_right}%`}</td>
                    <td>
                      {e.kind === "start" ? "" : e.change_from_start === null ? <span className="muted">Too few</span> : `${e.change_from_start > 0 ? "+" : ""}${e.change_from_start} points`}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
