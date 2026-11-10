"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Week = { week_of: string; active_students: number | null; answers: number | null; topics: number | null; days_used: number; hidden: boolean };

/** How much SYNiq was used each week: counts for the pilot report, never names. */
export default function Usage() {
  const [data, setData] = useState<{ min_group: number; weeks: Week[] } | null>(null);
  useEffect(() => {
    api<{ min_group: number; weeks: Week[] }>("/admin/usage").then(setData).catch(() => undefined);
  }, []);
  if (!data) return null;
  return (
    <section className="card">
      <h2>How much SYNiq was used, week by week</h2>
      <p className="muted">
        Students in school classes only. A week with fewer than {data.min_group} active students shows no numbers, so no child
        can be picked out.
      </p>
      {data.weeks.length === 0 ? (
        <p>No practice yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="stack-table">
            <thead>
              <tr>
                <th>Week starting</th>
                <th>Students active</th>
                <th>Answers</th>
                <th>Topics practised</th>
                <th>Days used</th>
              </tr>
            </thead>
            <tbody>
              {data.weeks.map((w) => (
                <tr key={w.week_of}>
                  <td data-label="Week starting">{w.week_of}</td>
                  <td data-label="Students active">{w.hidden ? `fewer than ${data.min_group}` : w.active_students}</td>
                  <td data-label="Answers">{w.answers ?? "hidden"}</td>
                  <td data-label="Topics practised">{w.topics ?? "hidden"}</td>
                  <td data-label="Days used">{w.days_used}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
