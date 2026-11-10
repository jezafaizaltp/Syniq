"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Person = { id: number; name: string; login: string };
type People = { classes: { id: number; name: string; students: (Person & { guardians: Person[] })[] }[] };

/** Logins only, never passwords: for a student who has lost their slip but remembers their own password. */
export default function Logins() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [people, setPeople] = useState<People | null>(null);
  const [classId, setClassId] = useState<number | "all">("all");
  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role === "admin") api<People>("/admin/people").then(setPeople);
  }, [me]);
  if (me?.role !== "admin" || !people) return null;
  const site = typeof window === "undefined" ? "" : window.location.origin.replace(/^https?:\/\//, "");
  return (
    <div className="wrap wide">
      <div className="no-print">
        <p>
          <Link href="/admin">← School setup</Link>
        </p>
        <h1>Login reminder sheet</h1>
        <p className="muted">
          Logins only. Passwords are never shown again: a student who has forgotten theirs needs a new one from their teacher
          or the School page.
        </p>
        <label htmlFor="lg-class">Class</label>
        <select id="lg-class" value={classId} onChange={(e) => setClassId(e.target.value === "all" ? "all" : Number(e.target.value))}>
          <option value="all">All classes</option>
          {people.classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <div className="row" style={{ marginTop: 12 }}>
          <button onClick={() => window.print()}>Print</button>
        </div>
      </div>
      {people.classes
        .filter((c) => classId === "all" || c.id === classId)
        .map((c) => (
          <section key={c.id} className="print-sheet">
            <h2>
              {/^class\b/i.test(c.name) ? c.name : `Class ${c.name}`}: SYNiq logins
            </h2>
            <p>
              Sign in at <strong>{site}</strong>
            </p>
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Student login</th>
                  <th>Parent login</th>
                </tr>
              </thead>
              <tbody>
                {c.students.map((s) => (
                  <tr key={s.id}>
                    <td>{s.name}</td>
                    <td>
                      <code>{s.login}</code>
                    </td>
                    <td>
                      {s.guardians.map((g) => (
                        <code key={g.id}>{g.login}</code>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
    </div>
  );
}
