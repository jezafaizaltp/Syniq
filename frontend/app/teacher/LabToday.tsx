"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, post } from "@/lib/api";

type Student = {
  id: number;
  name: string;
  login: string;
  first_sign_in_pending: boolean;
  shared: boolean;
  answered_today?: number;
  quiet?: boolean;
};
type Today = { class: string; students: Student[]; today: { active: number; answers: number; topics: number }; quiet_days: number };

function status(s: Student, quietDays: number) {
  if (s.first_sign_in_pending) return { text: "Not signed in yet", cls: "pill warn" };
  if (!s.shared) return { text: "Signed in · progress not shared by family", cls: "pill" };
  if (s.answered_today) return { text: `Practised today (${s.answered_today} answers)`, cls: "pill good" };
  if (s.quiet) return { text: `Quiet for ${quietDays}+ days`, cls: "pill warn" };
  return { text: "Not today", cls: "pill" };
}

/** The lab period at a glance: who is in, who needs a new password, and signing everyone out at the end. */
export default function LabToday({ classId }: { classId: number }) {
  const [data, setData] = useState<Today | null>(null);
  const [message, setMessage] = useState("");
  const [confirmEnd, setConfirmEnd] = useState(false);

  const load = useCallback(async () => setData(await api<Today>(`/teacher/classes/${classId}/today`)), [classId]);
  useEffect(() => {
    load();
  }, [load]);

  async function newPassword(s: Student) {
    try {
      const r = await post<{ name: string; login: string; temporary_password: string }>(
        `/teacher/classes/${classId}/students/${s.id}/reset-password`,
        {},
      );
      setMessage(`${r.name}: sign in as ${r.login} with ${r.temporary_password}. They choose their own password straight after.`);
      load();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Couldn't make a new password.");
    }
  }

  async function endPeriod() {
    const r = await post<{ signed_out: number }>(`/teacher/classes/${classId}/end-period`, {});
    setConfirmEnd(false);
    setMessage(`Lab period ended. ${r.signed_out} sign-in${r.signed_out === 1 ? "" : "s"} closed on the class's computers.`);
    load();
  }

  if (!data) return null;
  const quiet = data.students.filter((s) => s.quiet);
  const notIn = data.students.filter((s) => s.first_sign_in_pending);
  return (
    <section className="card">
      <h2>Today in the lab</h2>
      <p>
        <strong>{data.today.active}</strong> students practised today: <strong>{data.today.answers}</strong> answers across{" "}
        <strong>{data.today.topics}</strong> topics. Counts only include families who share progress with the school.
      </p>
      {notIn.length > 0 && <p className="muted">Not signed in yet: {notIn.map((s) => s.name).join(", ")}.</p>}
      {quiet.length > 0 && (
        <p className="muted">
          Quiet for {data.quiet_days} days or more: {quiet.map((s) => s.name).join(", ")}. A friendly word, not a telling-off.
        </p>
      )}
      {message && (
        <p className="feedback good" role="status">
          {message}
        </p>
      )}
      <details>
        <summary>All students ({data.students.length}), in alphabetical order</summary>
        <table className="stack-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Login</th>
              <th>Today</th>
              <th>
                <span className="sr-only">Password</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => {
              const st = status(s, data.quiet_days);
              return (
                <tr key={s.id}>
                  <td data-label="Student">{s.name}</td>
                  <td data-label="Login">
                    <code>{s.login}</code>
                  </td>
                  <td data-label="Today">
                    <span className={st.cls}>{st.text}</span>
                  </td>
                  <td>
                    <button className="secondary" onClick={() => newPassword(s)}>
                      New password
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </details>
      <div className="row" style={{ marginTop: 12 }}>
        {!confirmEnd ? (
          <button className="secondary" onClick={() => setConfirmEnd(true)}>
            End lab period: sign everyone out
          </button>
        ) : (
          <>
            <span>Sign out every student in {data.class} on all computers?</span>
            <button onClick={endPeriod}>Yes, sign them out</button>
            <button className="secondary" onClick={() => setConfirmEnd(false)}>
              Cancel
            </button>
          </>
        )}
      </div>
    </section>
  );
}
