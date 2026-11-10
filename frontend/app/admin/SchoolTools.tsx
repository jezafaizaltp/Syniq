"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, api, apiText, post, put } from "@/lib/api";

type Account = {
  class: string;
  student: string;
  student_login: string;
  student_password: string;
  guardian: string;
  guardian_login: string;
  guardian_password: string;
  learning_consent: boolean;
};
type AiUsage = {
  outside_ai_on: boolean;
  provider: string | null;
  answered_by_outside_ai_today: number;
  saved_unanswered_today: number;
  per_student_daily_limit: number;
};

export function saveFile(text: string, name: string, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** The school's name and who parents can ask: shown on sign-in, letters, slips and the lab poster. */
export function SchoolDetails() {
  const [f, setF] = useState({ name: "", contact: "" });
  const [saved, setSaved] = useState("");
  useEffect(() => {
    api<{ name: string; contact: string }>("/admin/school").then(setF);
  }, []);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setF(await put<{ name: string; contact: string }>("/admin/school", f));
    setSaved("Saved. The sign-in page, letters, slips and poster now use it.");
  }
  return (
    <section className="card">
      <h2>School details</h2>
      <form onSubmit={save}>
        <label htmlFor="s-name">School name</label>
        <input id="s-name" value={f.name} maxLength={120} onChange={(e) => setF({ ...f, name: e.target.value })} />
        <label htmlFor="s-contact">Who parents can ask (name and phone or email)</label>
        <input id="s-contact" value={f.contact} maxLength={200} onChange={(e) => setF({ ...f, contact: e.target.value })} />
        <div className="row" style={{ marginTop: 12 }}>
          <button type="submit">Save</button>
          <Link href="/admin/poster">Print the lab-wall poster →</Link>
        </div>
      </form>
      {saved && (
        <p className="feedback good" role="status">
          {saved}
        </p>
      )}
    </section>
  );
}

const YES = (b: boolean) => (b ? "yes" : "no");
const csvCell = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

/** A late joiner, without making a spreadsheet: the same checks and accounts as the import. */
export function AddOneStudent({ onCreated }: { onCreated: (accounts: Account[]) => void }) {
  const blank = { student: "", cls: "", guardian: "", email: "", learning: false, mood: false, school: false, puzzles: false };
  const [f, setF] = useState(blank);
  const [error, setError] = useState("");
  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const row = [f.student, f.cls, f.guardian, f.email, "", YES(f.learning), YES(f.mood), YES(f.school), YES(f.puzzles)].map(csvCell).join(",");
    const csv =
      "student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school,consent_puzzles\n" + row + "\n";
    try {
      const r = await post<{ ok: boolean; accounts?: Account[]; errors: { problems: string[] }[] }>("/admin/import", { csv, dry_run: false });
      if (!r.ok) {
        setError(r.errors.flatMap((x) => x.problems).join("; "));
        return;
      }
      setF(blank);
      onCreated(r.accounts ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add the student");
    }
  }
  const box = (k: "learning" | "mood" | "school" | "puzzles", label: string) => (
    <label className="check">
      <input type="checkbox" checked={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.checked })} />
      {label}
    </label>
  );
  return (
    <details className="card">
      <summary>
        <strong>Add one student</strong> <span className="muted">(a late joiner, without a spreadsheet)</span>
      </summary>
      <form onSubmit={add}>
        <label htmlFor="o-student">Student name</label>
        <input id="o-student" required value={f.student} onChange={(e) => setF({ ...f, student: e.target.value })} />
        <label htmlFor="o-class">Class (e.g. 9 B)</label>
        <input id="o-class" required value={f.cls} onChange={(e) => setF({ ...f, cls: e.target.value })} />
        <label htmlFor="o-guardian">Parent or guardian name</label>
        <input id="o-guardian" required value={f.guardian} onChange={(e) => setF({ ...f, guardian: e.target.value })} />
        <label htmlFor="o-email">Parent email (optional; a sibling&apos;s parent email links to the same parent login)</label>
        <input id="o-email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <p className="muted">From the signed paper form:</p>
        {box("learning", "Learning")}
        {box("mood", "Mood check-ins")}
        {box("school", "Share with school")}
        {box("puzzles", "Puzzles and pace")}
        {error && (
          <p className="feedback warn" role="alert">
            {error}
          </p>
        )}
        <div className="row" style={{ marginTop: 12 }}>
          <button type="submit">Add student</button>
        </div>
      </form>
    </details>
  );
}

/** Records the school keeps: the consent register, and Ask SYNiq's outside-AI use today. */
export function Records() {
  const [ai, setAi] = useState<AiUsage | null>(null);
  useEffect(() => {
    api<AiUsage>("/admin/ai-usage").then(setAi).catch(() => undefined);
  }, []);
  return (
    <section className="card">
      <h2>Records</h2>
      <div className="row">
        <button className="secondary" onClick={async () => saveFile(await apiText("/admin/consents.csv"), "syniq-consent-register.csv")}>
          Download the consent register (CSV)
        </button>
        <Link href="/admin/logins">Login reminder sheet (no passwords) →</Link>
      </div>
      <p className="muted">
        Every consent ever recorded, with the date and who recorded it. Keep it with the signed paper forms.
      </p>
      {ai && (
        <p>
          <strong>Ask SYNiq today:</strong>{" "}
          {ai.outside_ai_on
            ? `${ai.answered_by_outside_ai_today} questions went to the outside AI (${ai.provider}); each student can send up to ${ai.per_student_daily_limit} a day.`
            : "no outside AI is switched on, so every answer comes from SYNiq's own content."}{" "}
          {ai.saved_unanswered_today} question{ai.saved_unanswered_today === 1 ? "" : "s"} saved for the content to grow.
        </p>
      )}
    </section>
  );
}
