"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, api, apiText, del, post } from "@/lib/api";
import { useSession } from "@/lib/session";

type Subject = { id: number; name: string };
type Test = {
  id: number;
  name: string;
  subject: string;
  max_marks: number;
  phase: "before" | "after";
  taken_on: string;
  pilot_scores: number;
  comparison_scores: number;
};
type Summary = { n: number; too_few: boolean; before?: number; after?: number; change?: number; sd_change?: number };
type SubjectReport = {
  subject: string;
  before: string | null;
  after: string | null;
  pilot?: Summary;
  comparison?: Summary;
  difference?: { points: number; low: number; high: number; clear: boolean } | null;
  by_starting_marks?: { third: string; pilot: Summary; comparison: Summary }[];
  by_practice?: { practice: string; questions_from?: number; questions_up_to?: number; pilot: Summary }[];
};
type Report = { min_group: number; subjects: SubjectReport[] };
type Check = { ok: boolean; errors: { row: number; problems: string[] }[]; pilot: number; comparison: number; absent: number; dry_run: boolean };

const THIRDS: Record<string, string> = {
  lower: "Started in the lower third",
  middle: "Started in the middle third",
  upper: "Started in the upper third",
};

function signed(n: number) {
  return `${n > 0 ? "+" : ""}${n}`;
}

function Cells({ s }: { s: Summary | undefined }) {
  if (!s || s.too_few) {
    return (
      <>
        <td>{s?.n ?? 0}</td>
        <td colSpan={3} className="muted">
          Too few to show
        </td>
      </>
    );
  }
  return (
    <>
      <td>{s.n}</td>
      <td>{s.before}%</td>
      <td>{s.after}%</td>
      <td>
        <strong>{signed(s.change!)}</strong>
      </td>
    </>
  );
}

export default function Results() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [tests, setTests] = useState<Test[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [form, setForm] = useState({ name: "", subject_id: "", max_marks: "", phase: "before", taken_on: "" });
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState<{ test: Test; csv: string; check: Check } | null>(null);

  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async () => {
    const [s, t, r] = await Promise.all([
      api<Subject[]>("/subjects"),
      api<Test[]>("/admin/results/assessments"),
      api<Report>("/admin/results/report"),
    ]);
    setSubjects(s);
    setTests(t);
    setReport(r);
  }, []);

  useEffect(() => {
    if (me?.role === "admin") load();
  }, [me, load]);

  async function addTest(e: React.FormEvent) {
    e.preventDefault();
    try {
      await post("/admin/results/assessments", { ...form, subject_id: Number(form.subject_id), max_marks: Number(form.max_marks) });
      setForm({ ...form, name: "", max_marks: "", taken_on: "" });
      setMessage("Test added. Now upload its marks.");
      load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not add the test");
    }
  }

  async function chooseMarks(test: Test, file: File | undefined) {
    setPending(null);
    setMessage("");
    if (!file) return;
    const csv = await file.text();
    try {
      const check = await post<Check>(`/admin/results/assessments/${test.id}/scores`, { csv, dry_run: true });
      setPending({ test, csv, check });
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not read the sheet");
    }
  }

  async function saveMarks() {
    if (!pending) return;
    await post(`/admin/results/assessments/${pending.test.id}/scores`, { csv: pending.csv, dry_run: false });
    setMessage(`Marks saved for ${pending.test.name}.`);
    setPending(null);
    load();
  }

  async function download() {
    const text = await apiText("/admin/results/export.csv");
    const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "syniq-pilot-results.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (me?.role !== "admin") return null;

  return (
    <div className="wrap wide">
      <p>
        <Link href="/admin">← School setup</Link>
      </p>
      <h1>Pilot results</h1>
      <p className="muted">
        Did SYNiq help? Upload the school&apos;s own exam marks from before students started SYNiq and from after some weeks of
        using it, for the pilot students and for a comparison group of Class 9 students who don&apos;t use SYNiq. If both groups
        change by the same amount, the exam just got easier or harder. The difference between the two changes is what SYNiq may
        have added. Only you can see this page. Teachers, parents, students and SYNiq&apos;s teaching never see these marks.
      </p>

      {report && report.subjects.length > 0 && (
        <section className="card">
          <h2>Results</h2>
          <p className="muted">
            Averages in percent of the maximum marks, for students with marks in both tests. Any group of fewer than{" "}
            {report.min_group} students is hidden so no one&apos;s marks can be worked out.
          </p>
          {report.subjects.map((s) => (
            <div key={s.subject} style={{ marginTop: 16 }}>
              <h3>{s.subject}</h3>
              {!s.before || !s.after ? (
                <p className="muted">Add a &quot;before&quot; and an &quot;after&quot; test for {s.subject} to see results.</p>
              ) : (
                <>
                  <p className="muted">
                    {s.before} → {s.after}
                  </p>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Group</th>
                          <th>Students</th>
                          <th>Before</th>
                          <th>After</th>
                          <th>Change (points)</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>Using SYNiq</td>
                          <Cells s={s.pilot} />
                        </tr>
                        <tr>
                          <td>Comparison group</td>
                          <Cells s={s.comparison} />
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  {s.difference ? (
                    <p className={`feedback ${s.difference.clear && s.difference.points > 0 ? "good" : "warn"}`}>
                      Students using SYNiq changed by <strong>{signed(s.difference.points)} points</strong> compared with the
                      comparison group (likely somewhere between {signed(s.difference.low)} and {signed(s.difference.high)}).{" "}
                      {s.difference.clear
                        ? s.difference.points > 0
                          ? "That range is above zero, so this is a clear gain."
                          : "That range is below zero, so pilot students did worse. Worth looking into."
                        : "That range includes zero, so we can't yet tell this apart from chance. More students or more time would help."}
                    </p>
                  ) : (
                    <p className="muted">Each group needs at least {report.min_group} students with both marks to compare them.</p>
                  )}
                  {s.by_starting_marks && s.by_starting_marks.length > 0 && (
                    <>
                      <h4>By starting marks</h4>
                      <p className="muted">Does SYNiq help students who started lower as much as those who started higher?</p>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th></th>
                              <th>Using SYNiq: students</th>
                              <th>Change</th>
                              <th>Comparison: students</th>
                              <th>Change</th>
                            </tr>
                          </thead>
                          <tbody>
                            {s.by_starting_marks.map((t) => (
                              <tr key={t.third}>
                                <td>{THIRDS[t.third]}</td>
                                <td>{t.pilot.n}</td>
                                <td>{t.pilot.too_few ? <span className="muted">Too few</span> : signed(t.pilot.change!)}</td>
                                <td>{t.comparison.n}</td>
                                <td>{t.comparison.too_few ? <span className="muted">Too few</span> : signed(t.comparison.change!)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                  {s.by_practice && s.by_practice.length > 0 && (
                    <>
                      <h4>By how much they practised</h4>
                      <ul className="list">
                        {s.by_practice.map((p) => (
                          <li key={p.practice}>
                            <span>
                              {p.practice === "more"
                                ? `${p.questions_from} or more questions in SYNiq`
                                : `Up to ${p.questions_up_to} questions in SYNiq`}
                            </span>
                            <span>
                              {p.pilot.too_few ? "Too few" : `${p.pilot.n} students, ${signed(p.pilot.change!)} points`}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              )}
            </div>
          ))}
          <div className="row" style={{ marginTop: 16 }}>
            <button className="secondary" onClick={download}>
              Download anonymous results (CSV)
            </button>
          </div>
        </section>
      )}

      <section className="card">
        <h2>Tests</h2>
        {tests.length === 0 ? (
          <p className="muted">No tests yet. Add the last exam before SYNiq started, then a later one.</p>
        ) : (
          <ul className="list">
            {tests.map((t) => (
              <li key={t.id} style={{ flexWrap: "wrap" }}>
                <span>
                  <strong>{t.name}</strong> · {t.subject} · {t.phase === "before" ? "before SYNiq" : "after SYNiq"} · {t.taken_on}{" "}
                  · out of {t.max_marks}
                  <br />
                  <span className="muted">
                    Marks for {t.pilot_scores} pilot and {t.comparison_scores} comparison students
                  </span>
                </span>
                <span className="row">
                  <label className="btn secondary" style={{ margin: 0 }} htmlFor={`marks-${t.id}`}>
                    Upload marks
                  </label>
                  <input
                    id={`marks-${t.id}`}
                    type="file"
                    accept=".csv,text/csv"
                    className="sr-only"
                    onChange={(e) => {
                      chooseMarks(t, e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                  <button
                    className="secondary"
                    onClick={async () => {
                      if (!confirm(`Delete ${t.name} and all its marks?`)) return;
                      await del(`/admin/results/assessments/${t.id}`);
                      load();
                    }}
                  >
                    Delete
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}

        {pending && !pending.check.ok && (
          <div className="feedback warn" role="alert">
            <strong>Please fix these rows and upload again. Nothing has been saved.</strong>
            <ul>
              {pending.check.errors.map((e) => (
                <li key={e.row}>
                  Row {e.row}: {e.problems.join("; ")}
                </li>
              ))}
            </ul>
          </div>
        )}
        {pending?.check.ok && (
          <div className="feedback good" role="status">
            <p>
              {pending.test.name}: marks for {pending.check.pilot} pilot and {pending.check.comparison} comparison students
              {pending.check.absent ? `, ${pending.check.absent} absent` : ""}.
            </p>
            <button onClick={saveMarks}>Save marks</button>
          </div>
        )}
        {message && (
          <p className="feedback good" role="status">
            {message}
          </p>
        )}

        <details style={{ marginTop: 16 }}>
          <summary>How to fill in the marks sheet</summary>
          <p className="muted">
            Two columns: <code>student</code> and <code>marks</code>. For pilot students, use their SYNiq login from the login
            sheet. For the comparison group, give each student a code like C1, C2, C3 and keep the list of who is who at school,
            never in SYNiq. Use the same code for the same student in every test. Write AB for absent.
          </p>
          <p>
            <a
              href={`data:text/csv;charset=utf-8,${encodeURIComponent("student,marks\nmeera482,31\nC1,28\nC2,AB\n")}`}
              download="syniq-marks.csv"
            >
              Download an example sheet
            </a>
          </p>
        </details>

        <form onSubmit={addTest} style={{ marginTop: 16 }}>
          <h3>Add a test</h3>
          <label htmlFor="r-name">Name, e.g. First term 2027</label>
          <input id="r-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <label htmlFor="r-subject">Subject</label>
          <select id="r-subject" value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })} required>
            <option value="" disabled>
              Choose a subject
            </option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <label htmlFor="r-max">Maximum marks</label>
          <input id="r-max" inputMode="decimal" value={form.max_marks} onChange={(e) => setForm({ ...form, max_marks: e.target.value })} required />
          <label htmlFor="r-date">Date of the test</label>
          <input id="r-date" type="date" value={form.taken_on} onChange={(e) => setForm({ ...form, taken_on: e.target.value })} required />
          <fieldset style={{ border: 0, padding: 0, margin: "12px 0 0" }}>
            <legend style={{ fontWeight: 600 }}>When was it?</legend>
            <label className="check">
              <input type="radio" name="phase" checked={form.phase === "before"} onChange={() => setForm({ ...form, phase: "before" })} />
              Before students started SYNiq
            </label>
            <label className="check">
              <input type="radio" name="phase" checked={form.phase === "after"} onChange={() => setForm({ ...form, phase: "after" })} />
              After some weeks of using SYNiq
            </label>
          </fieldset>
          <div className="row" style={{ marginTop: 12 }}>
            <button type="submit">Add test</button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>When the pilot is over</h2>
        <p className="muted">
          Once the pilot report is written, delete every test and mark from SYNiq. Download the anonymous results first if you
          need them.
        </p>
        <button
          className="secondary"
          onClick={async () => {
            if (!confirm("Delete every test and all marks? This can't be undone.")) return;
            await del("/admin/results");
            setMessage("All tests and marks deleted.");
            load();
          }}
        >
          Delete all results
        </button>
      </section>
    </div>
  );
}
