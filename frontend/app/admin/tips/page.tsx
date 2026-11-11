"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Row = { tag: string; tip: string; yes: number; no: number };

/** Mistake tips students said did not help, most first. Counts only: no student is named. */
export default function TipFeedback() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role === "admin") api<Row[]>("/admin/tip-feedback").then(setRows).catch(() => setRows([]));
  }, [me]);
  if (!rows) return null;
  return (
    <div className="wrap wide">
      <p>
        <Link href="/admin">← School setup</Link>
      </p>
      <h1>Mistake tips to improve</h1>
      <p className="muted">
        After a mistake tip, students can tap &ldquo;Was this tip helpful?&rdquo;. Tips with the most &ldquo;Not really&rdquo; come
        first. To change a tip&apos;s wording, note it on the review sheet (it carries each tip&apos;s tag) or send it to whoever
        looks after the content.
      </p>
      {rows.length === 0 ? (
        <p>No answers yet.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Tip</th>
                <th>Tag</th>
                <th>Helped</th>
                <th>Not really</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.tag}>
                  <td>{r.tip}</td>
                  <td className="muted">{r.tag}</td>
                  <td>{r.yes}</td>
                  <td className={r.no > r.yes ? "gap" : undefined}>{r.no}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
