"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Entry = { id: number; when: string; who: string; role: string; what: string; student: string | null };

const ROLE_WORDS: Record<string, string> = { admin: "School admin", teacher: "Teacher", guardian: "Parent", student: "Student" };

/** Who looked at or changed what: read-only, newest first. */
export default function Audit() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [more, setMore] = useState(false);

  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async (before?: number) => {
    const r = await api<{ entries: Entry[]; more: boolean }>(`/admin/audit${before ? `?before_id=${before}` : ""}`);
    setEntries((old) => (before ? [...old, ...r.entries] : r.entries));
    setMore(r.more);
  }, []);

  useEffect(() => {
    if (me?.role === "admin") load().catch(() => undefined);
  }, [me, load]);

  if (me?.role !== "admin") return null;

  return (
    <div className="wrap wide">
      <p>
        <Link href="/admin">← School setup</Link>
      </p>
      <h1>Audit log</h1>
      <p className="muted">
        Every time someone views a class or a child&apos;s progress, changes consent or support, resets a password, or works with
        pilot marks, it is written here. Nobody can edit or delete these entries. Times are in UTC.
      </p>
      <div className="card table-scroll">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>What</th>
              <th>Student</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id}>
                <td>{e.when.replace("T", " ")}</td>
                <td>
                  {e.who}
                  <br />
                  <span className="muted">{ROLE_WORDS[e.role] ?? e.role}</span>
                </td>
                <td>{e.what}</td>
                <td>{e.student ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {entries.length === 0 && <p className="muted">Nothing recorded yet.</p>}
      </div>
      {more && (
        <button className="secondary" onClick={() => load(entries[entries.length - 1]?.id)}>
          Show older
        </button>
      )}
    </div>
  );
}
