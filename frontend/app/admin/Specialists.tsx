"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, post } from "@/lib/api";

type Specialist = { id: number; name: string; title: string; login: string; children: number };

/** Counsellors and special educators. They see a child only after a parent shares them. */
export default function Specialists() {
  const [list, setList] = useState<Specialist[]>([]);
  const [form, setForm] = useState({ name: "", email: "", title: "School counsellor" });
  const [result, setResult] = useState("");
  const [passwords, setPasswords] = useState<Record<number, string>>({});

  const load = useCallback(() => {
    api<Specialist[]>("/admin/specialists").then(setList).catch(() => setList([]));
  }, []);
  useEffect(load, [load]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await post<{ login: string; temporary_password: string }>("/admin/specialists", form);
      setResult(`Added. Login: ${r.login}  Temporary password: ${r.temporary_password}`);
      setForm({ name: "", email: "", title: "School counsellor" });
      load();
    } catch (err) {
      setResult(err instanceof ApiError ? err.message : "Could not add the specialist");
    }
  }

  return (
    <section className="card">
      <h2>Specialists</h2>
      <p className="muted">
        A school counsellor, special educator or therapist. They see nothing until a parent shares a child with them from the
        parent&apos;s page, and then only support, progress in words and repeated mistakes. Never moods, marks, notes or goals.
      </p>
      <form onSubmit={add}>
        <label htmlFor="s-name">Name</label>
        <input id="s-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <label htmlFor="s-email">Email (their login)</label>
        <input id="s-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <label htmlFor="s-title">Role</label>
        <input id="s-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <div className="row" style={{ marginTop: 8 }}>
          <button type="submit">Add specialist</button>
        </div>
      </form>
      {result && <p className="feedback good">{result}</p>}
      {list.length > 0 && (
        <ul className="list">
          {list.map((s) => (
            <li key={s.id}>
              <span>
                {s.name} <span className="muted">· {s.title}</span> <code>{s.login}</code>
                <br />
                <span className="muted">
                  {s.children === 1 ? "1 child shared" : `${s.children} children shared`} by parents
                </span>
              </span>
              {passwords[s.id] ? (
                <code>{passwords[s.id]}</code>
              ) : (
                <button
                  className="secondary"
                  onClick={async () => {
                    const r = await post<{ temporary_password: string }>(`/admin/users/${s.id}/reset-password`, {});
                    setPasswords({ ...passwords, [s.id]: r.temporary_password });
                  }}
                >
                  New password
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
