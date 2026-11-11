"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Health = { backup_folder: boolean; newest_backup_hours: number | null; backups: number; disk_free_gb: number; backup_ok: boolean; disk_ok: boolean };

/** The newest backup and free disk space, as two more lines on the card. */
function HealthLines() {
  const [h, setH] = useState<Health | null>(null);
  useEffect(() => {
    api<Health>("/admin/health").then(setH).catch(() => setH(null));
  }, []);
  if (!h) return null;
  return (
    <>
      <li className={h.backup_ok ? "ready-done" : "ready-must"}>
        <span aria-hidden="true">{h.backup_ok ? "✓" : "!"}</span>{" "}
        <strong>
          {!h.backup_folder
            ? "Backups: this computer can't see the backups folder"
            : h.newest_backup_hours == null
              ? "Backups: none yet"
              : `Newest backup: ${h.newest_backup_hours < 1 ? "less than an hour" : `${Math.round(h.newest_backup_hours)} hours`} old (${h.backups} kept)`}
        </strong>
        {!h.backup_ok && <span className="muted"> (make one now: docker compose restart backup)</span>}
      </li>
      <li className={h.disk_ok ? "ready-done" : "ready-must"}>
        <span aria-hidden="true">{h.disk_ok ? "✓" : "!"}</span> <strong>Free disk space: {h.disk_free_gb} GB</strong>
        {!h.disk_ok && <span className="muted"> (below 2 GB: SYNiq may stop saving work)</span>}
      </li>
    </>
  );
}

type Person = { id: number; name: string; first_sign_in_pending: boolean };
type Student = Person & { consent: Record<string, boolean>; guardians: Person[] };
type People = { classes: { id: number; name: string; teacher: string | null; students: Student[] }[]; teachers: Person[] };

/** How many of these are done, with the first few names still waiting. */
function Line({ label, done, total, waiting, must }: { label: string; done: number; total: number; waiting: string[]; must: boolean }) {
  const complete = total > 0 && done === total;
  return (
    <li className={complete ? "ready-done" : must ? "ready-must" : "ready-later"}>
      <span aria-hidden="true">{complete ? "✓" : must ? "!" : "…"}</span>{" "}
      <strong>
        {label}: {done} of {total}
      </strong>
      {!complete && waiting.length > 0 && (
        <span className="muted">
          {" "}
          (still waiting: {waiting.slice(0, 6).join(", ")}
          {waiting.length > 6 ? ` and ${waiting.length - 6} more` : ""})
        </span>
      )}
    </li>
  );
}

/**
 * Is the pilot ready to start? Paper consent and a teacher for every class must be in place before
 * day one. First sign-ins happen on day one itself, so they are shown but don't block.
 */
export default function Readiness({ people }: { people: People }) {
  const students = people.classes.flatMap((c) => c.students.map((s) => ({ ...s, cls: c.name })));
  const parents = Array.from(new Map(students.flatMap((s) => s.guardians).map((g) => [g.id, g])).values());
  const noConsent = students.filter((s) => !s.consent.core_learning);
  const noTeacher = people.classes.filter((c) => !c.teacher);
  const ready = students.length > 0 && noConsent.length === 0 && noTeacher.length === 0 && people.teachers.length > 0;

  return (
    <section className="card readiness" aria-labelledby="readiness-title">
      <h2 id="readiness-title">Ready for the pilot?</h2>
      {students.length === 0 ? (
        <p className="muted">Add students below first. This card then shows what is still missing before day one.</p>
      ) : (
        <>
          <p className={`feedback ${ready ? "good" : "warn"}`} role="status">
            {ready
              ? "Everything needed before day one is in place. Sign-ins below happen on the day."
              : "A few things are still needed before students start (marked !)."}
          </p>
          <ul className="ready-list">
            <Line
              label="Students with a signed consent form for learning"
              done={students.length - noConsent.length}
              total={students.length}
              waiting={noConsent.map((s) => `${s.name} (${s.cls})`)}
              must
            />
            <Line
              label="Classes with a teacher"
              done={people.classes.length - noTeacher.length}
              total={people.classes.length}
              waiting={noTeacher.map((c) => c.name)}
              must
            />
            <Line
              label="Teachers who have signed in"
              done={people.teachers.filter((t) => !t.first_sign_in_pending).length}
              total={people.teachers.length}
              waiting={people.teachers.filter((t) => t.first_sign_in_pending).map((t) => t.name)}
              must={false}
            />
            <Line
              label="Students who have signed in"
              done={students.filter((s) => !s.first_sign_in_pending).length}
              total={students.length}
              waiting={students.filter((s) => s.first_sign_in_pending).map((s) => s.name)}
              must={false}
            />
            <Line
              label="Parents who have signed in"
              done={parents.filter((p) => !p.first_sign_in_pending).length}
              total={parents.length}
              waiting={parents.filter((p) => p.first_sign_in_pending).map((p) => p.name)}
              must={false}
            />
            <HealthLines />
          </ul>
          <p className="muted">
            Before each lab period, also run the lab check (check.sh on Ubuntu, check-windows.bat on Windows). Mood check-ins,
            sharing with school and puzzles each need their own yes on the form; students without them still learn.
          </p>
        </>
      )}
    </section>
  );
}
