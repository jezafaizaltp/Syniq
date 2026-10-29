"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, post } from "@/lib/api";
import { useSession } from "@/lib/session";

type Check = { ok: boolean; errors: { row: number; problems: string[] }[]; students?: number; classes?: string[]; without_learning_consent?: number };
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
type Person = { id: number; name: string; login: string; first_sign_in_pending: boolean };
type Student = Person & { consent: Record<string, boolean>; guardians: Person[] };
type SyllabusCheck = {
  ok: boolean;
  errors: { row: number; problems: string[] }[];
  chapters?: number;
  new_chapters?: number;
  topics?: number;
  added_chapters?: number;
  added_topics?: number;
};
type People = { classes: { id: number; name: string; teacher: string | null; students: Student[] }[]; teachers: Person[] };

const TEMPLATE =
  "student_name,class,guardian_name,guardian_email,guardian_phone,consent_learning,consent_mood,consent_school\n" +
  "Anu Krishna,9 A,Lakshmi Krishna,lakshmi@example.com,,yes,yes,yes\n";

const SYLLABUS_TEMPLATE =
  "subject,chapter_number,chapter_title,topic\n" +
  "math,1,Pairs of Equations,Equations with two unknowns\n" +
  "math,1,Pairs of Equations,Solving a pair of equations\n";

const SCOPE_WORDS: Record<string, string> = {
  core_learning: "Learning",
  mood_checkins: "Mood check-ins",
  school_sharing: "Share with school",
};

export default function Admin() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [people, setPeople] = useState<People | null>(null);
  const [sheet, setSheet] = useState("");
  const [check, setCheck] = useState<Check | null>(null);
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [error, setError] = useState("");
  const [newPasswords, setNewPasswords] = useState<Record<number, string>>({});
  const [teacher, setTeacher] = useState({ name: "", email: "", classes: "" });
  const [teacherResult, setTeacherResult] = useState("");
  const [syllabus, setSyllabus] = useState("");
  const [syllabusCheck, setSyllabusCheck] = useState<SyllabusCheck | null>(null);
  const [syllabusError, setSyllabusError] = useState("");

  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async () => setPeople(await api<People>("/admin/people")), []);
  useEffect(() => {
    if (me?.role === "admin") load();
  }, [me, load]);

  async function readFile(file: File | undefined) {
    setAccounts(null);
    setError("");
    if (!file) return;
    const text = await file.text();
    setSheet(text);
    try {
      setCheck(await post<Check>("/admin/import", { csv: text, dry_run: true }));
    } catch (e) {
      setCheck(null);
      setError(e instanceof ApiError ? e.message : "Could not read the sheet");
    }
  }

  async function createAccounts() {
    try {
      const r = await post<{ ok: boolean; accounts: Account[]; errors: Check["errors"] }>("/admin/import", { csv: sheet, dry_run: false });
      if (!r.ok) {
        setCheck({ ok: false, errors: r.errors });
        return;
      }
      setAccounts(r.accounts);
      setCheck(null);
      setSheet("");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create the accounts");
    }
  }

  async function readSyllabus(file: File | undefined) {
    setSyllabusCheck(null);
    setSyllabusError("");
    if (!file) return;
    const text = await file.text();
    setSyllabus(text);
    try {
      setSyllabusCheck(await post<SyllabusCheck>("/admin/syllabus", { csv: text, dry_run: true }));
    } catch (e) {
      setSyllabusError(e instanceof ApiError ? e.message : "Could not read the sheet");
    }
  }

  async function addSyllabus() {
    try {
      const r = await post<SyllabusCheck>("/admin/syllabus", { csv: syllabus, dry_run: false });
      setSyllabusCheck(r);
      setSyllabus("");
    } catch (e) {
      setSyllabusError(e instanceof ApiError ? e.message : "Could not add the chapters");
    }
  }

  async function reset(person: Person) {
    if (!confirm(`Give ${person.name} a new temporary password? Their old one will stop working.`)) return;
    const r = await post<{ temporary_password: string }>(`/admin/users/${person.id}/reset-password`, {});
    setNewPasswords({ ...newPasswords, [person.id]: r.temporary_password });
    load();
  }

  async function setConsent(student: Student, scope: string, granted: boolean) {
    await post(`/admin/students/${student.id}/consent`, { scope, granted });
    load();
  }

  async function addTeacher(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await post<{ login: string; temporary_password: string }>("/admin/teachers", {
        name: teacher.name,
        email: teacher.email,
        classes: teacher.classes
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
      });
      setTeacherResult(`Added. Login: ${r.login}  Temporary password: ${r.temporary_password}`);
      setTeacher({ name: "", email: "", classes: "" });
      load();
    } catch (err) {
      setTeacherResult(err instanceof ApiError ? err.message : "Could not add the teacher");
    }
  }

  if (me?.role !== "admin") return null;

  if (accounts) {
    return (
      <div className="wrap wide">
        <div className="no-print">
          <h1>New accounts</h1>
          <p className="feedback warn">
            These passwords are shown only now. Print this sheet or save it as a PDF before you leave the page. Everyone
            chooses their own password the first time they sign in.
          </p>
          <div className="row">
            <button onClick={() => window.print()}>Print login sheet</button>
            <button
              className="secondary"
              onClick={() => {
                setAccounts(null);
                load();
              }}
            >
              Done
            </button>
          </div>
        </div>
        <section className="print-sheet">
          <h2>SYNiq logins</h2>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Student</th>
                  <th>Student login</th>
                  <th>Student password</th>
                  <th>Parent</th>
                  <th>Parent login</th>
                  <th>Parent password</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.student_login}>
                    <td>{a.class}</td>
                    <td>
                      {a.student}
                      {!a.learning_consent && <span className="badge">No consent yet</span>}
                    </td>
                    <td>
                      <code>{a.student_login}</code>
                    </td>
                    <td>
                      <code>{a.student_password}</code>
                    </td>
                    <td>{a.guardian}</td>
                    <td>
                      <code>{a.guardian_login}</code>
                    </td>
                    <td>{a.guardian_password.startsWith("(") ? "Same as above" : <code>{a.guardian_password}</code>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">Sign in at this site. You will be asked to choose your own password.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="wrap wide">
      <h1>School setup</h1>

      <section className="card">
        <h2>Add students and parents from a spreadsheet</h2>
        <p className="muted">
          One row per student, saved as CSV from Excel or Google Sheets. Enter consent from the paper forms as yes or no. Don&apos;t
          include marks or ability groups. Siblings with the same parent get one parent login.
        </p>
        <p>
          <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE)}`} download="syniq-students.csv">
            Download the template
          </a>
        </p>
        <label htmlFor="sheet">Choose the CSV file</label>
        <input id="sheet" type="file" accept=".csv,text/csv" onChange={(e) => readFile(e.target.files?.[0])} />
        {error && (
          <p className="feedback warn" role="alert">
            {error}
          </p>
        )}
        {check && !check.ok && (
          <div className="feedback warn" role="alert">
            <strong>Please fix these rows and choose the file again. Nothing has been created.</strong>
            <ul>
              {check.errors.map((e) => (
                <li key={e.row}>
                  Row {e.row}: {e.problems.join("; ")}
                </li>
              ))}
            </ul>
          </div>
        )}
        {check?.ok && (
          <div className="feedback good" role="status">
            <p>
              Ready: {check.students} students in {check.classes?.join(", ")}.
              {check.without_learning_consent
                ? ` ${check.without_learning_consent} without consent for learning yet; they can sign in but can't start until a parent agrees.`
                : ""}
            </p>
            <button onClick={createAccounts}>Create accounts</button>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Class 9 chapters and topics</h2>
        <p className="muted">
          One row per topic, copied from the SCERT textbooks. Subjects: mal, eng, hin, math, phy, chem, bio, ss, it. Leave
          the topic empty to add a chapter now and split it into topics later. Upload the same sheet again as it grows:
          chapters and topics already added are skipped. Students only see a chapter once a teacher has approved content
          for it.
        </p>
        <p>
          <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(SYLLABUS_TEMPLATE)}`} download="syniq-syllabus.csv">
            Download the template
          </a>
        </p>
        <label htmlFor="syllabus">Choose the CSV file</label>
        <input id="syllabus" type="file" accept=".csv,text/csv" onChange={(e) => readSyllabus(e.target.files?.[0])} />
        {syllabusError && (
          <p className="feedback warn" role="alert">
            {syllabusError}
          </p>
        )}
        {syllabusCheck && !syllabusCheck.ok && (
          <div className="feedback warn" role="alert">
            <strong>Please fix these rows and choose the file again. Nothing has been added.</strong>
            <ul>
              {syllabusCheck.errors.map((e) => (
                <li key={e.row}>
                  Row {e.row}: {e.problems.join("; ")}
                </li>
              ))}
            </ul>
          </div>
        )}
        {syllabusCheck?.ok && syllabusCheck.added_topics === undefined && (
          <div className="feedback good" role="status">
            <p>
              Ready: {syllabusCheck.chapters} chapters ({syllabusCheck.new_chapters} new) and {syllabusCheck.topics} topic rows.
            </p>
            <button onClick={addSyllabus}>Add chapters</button>
          </div>
        )}
        {syllabusCheck?.ok && syllabusCheck.added_topics !== undefined && (
          <p className="feedback good" role="status">
            Added {syllabusCheck.added_chapters} chapters and {syllabusCheck.added_topics} topics. Teachers can now add notes and
            content on the Class page.
          </p>
        )}
      </section>

      <section className="card">
        <h2>Add a teacher</h2>
        <form onSubmit={addTeacher}>
          <label htmlFor="t-name">Name</label>
          <input id="t-name" value={teacher.name} onChange={(e) => setTeacher({ ...teacher, name: e.target.value })} required />
          <label htmlFor="t-email">Email (their login)</label>
          <input id="t-email" type="email" value={teacher.email} onChange={(e) => setTeacher({ ...teacher, email: e.target.value })} required />
          <label htmlFor="t-classes">Classes, separated by commas (e.g. 9 A, 9 B)</label>
          <input id="t-classes" value={teacher.classes} onChange={(e) => setTeacher({ ...teacher, classes: e.target.value })} />
          <div className="row" style={{ marginTop: 12 }}>
            <button type="submit">Add teacher</button>
          </div>
        </form>
        {teacherResult && (
          <p className="feedback good" role="status">
            {teacherResult}
          </p>
        )}
      </section>

      {people?.classes.map((c) => (
        <section key={c.id} className="card">
          <h2>
            Class {c.name} <span className="muted">· {c.teacher ? `Teacher: ${c.teacher}` : "No teacher yet"}</span>
          </h2>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Consent (from paper form)</th>
                  <th>Parent</th>
                </tr>
              </thead>
              <tbody>
                {c.students.map((s) => (
                  <tr key={s.id}>
                    <td>
                      {s.name}
                      <br />
                      <code>{s.login}</code>
                      {s.first_sign_in_pending && <span className="badge">Not signed in yet</span>}
                      <br />
                      {newPasswords[s.id] ? (
                        <span>
                          New password: <code>{newPasswords[s.id]}</code>
                        </span>
                      ) : (
                        <button className="secondary" onClick={() => reset(s)}>
                          New password
                        </button>
                      )}
                    </td>
                    <td>
                      {Object.entries(SCOPE_WORDS).map(([scope, word]) => (
                        <label key={scope} className="check">
                          <input type="checkbox" checked={!!s.consent[scope]} onChange={(e) => setConsent(s, scope, e.target.checked)} />
                          {word}
                        </label>
                      ))}
                    </td>
                    <td>
                      {s.guardians.map((g) => (
                        <div key={g.id}>
                          {g.name}
                          <br />
                          <code>{g.login}</code>
                          <br />
                          {newPasswords[g.id] ? (
                            <span>
                              New password: <code>{newPasswords[g.id]}</code>
                            </span>
                          ) : (
                            <button className="secondary" onClick={() => reset(g)}>
                              New password
                            </button>
                          )}
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      {people && people.teachers.length > 0 && (
        <section className="card">
          <h2>Teachers</h2>
          <ul className="list">
            {people.teachers.map((t) => (
              <li key={t.id}>
                <span>
                  {t.name} <code>{t.login}</code>
                </span>
                {newPasswords[t.id] ? (
                  <code>{newPasswords[t.id]}</code>
                ) : (
                  <button className="secondary" onClick={() => reset(t)}>
                    New password
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
