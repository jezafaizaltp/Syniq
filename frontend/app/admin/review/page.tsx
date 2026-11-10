"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, post } from "@/lib/api";
import { useSession } from "@/lib/session";
import { BOARD_WORDS, classWords } from "@/lib/subjects";

type SubjectRow = { id: number; name: string; grade: number; syllabus: string; questions: number };
type Question = {
  n: number;
  id: number;
  prompt: string;
  options: string[];
  answer: string;
  solution: string;
  difficulty: number;
  status: string;
  fix_note: string;
  mistakes: { wrong: string; tip: string }[];
};
type Sheet = {
  subject: SubjectRow;
  questions: number;
  chapters: { number: number; title: string; topics: { title: string; questions: Question[] }[] }[];
};

type Fix = { id: number; subject: string; chapter: string; topic: string; prompt: string; answer: string; note: string };
type UploadResult = { ok: number; to_fix: number; not_checked: number; unknown_ids: string[] };

const LEVEL_WORDS = ["", "Easy", "Medium", "Harder"];

function csvCell(v: string | number) {
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** The same sheet as a spreadsheet, with empty columns for the teacher's verdict. */
function toCsv(sheet: Sheet) {
  const head = ["no", "id", "chapter", "topic", "question", "choices", "answer", "solution", "wrong answers and tips", "ok (yes/no)", "what to fix"];
  const lines = [head.join(",")];
  for (const ch of sheet.chapters)
    for (const t of ch.topics)
      for (const q of t.questions)
        lines.push(
          [
            q.n,
            q.id,
            `${ch.number}. ${ch.title}`,
            t.title,
            q.prompt,
            q.options.join(" | "),
            q.answer,
            q.solution,
            q.mistakes.map((m) => `${m.wrong}: ${m.tip}`).join(" | "),
            "",
            "",
          ]
            .map(csvCell)
            .join(","),
        );
  return lines.join("\n") + "\n";
}

/** Every question in a subject, printable, so a teacher can check it on paper and mark what to fix. */
export default function ReviewSheet() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [subjects, setSubjects] = useState<SubjectRow[]>([]);
  const [chosen, setChosen] = useState<number | null>(null);
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [chapter, setChapter] = useState<number | null>(null);
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState("");
  const staff = me?.role === "admin" || me?.role === "teacher";

  useEffect(() => {
    if (!loading && !staff) router.replace("/");
  }, [staff, loading, router]);

  useEffect(() => {
    if (!staff) return;
    api<SubjectRow[]>("/admin/review-sheet").then(setSubjects).catch(() => setError("Couldn't load the subjects."));
    api<Fix[]>("/admin/review-fixes").then(setFixes).catch(() => {});
  }, [staff]);

  async function readFilledSheet(file: File | undefined) {
    setUpload(null);
    setUploadError("");
    if (!file) return;
    try {
      setUpload(await post<UploadResult>("/admin/review-sheet/upload", { csv: await file.text() }));
      setFixes(await api<Fix[]>("/admin/review-fixes"));
    } catch (e) {
      setUploadError(e instanceof ApiError ? e.message : "Couldn't read that file.");
    }
  }

  async function markFixed(id: number) {
    await post(`/admin/review-fixes/${id}/done`, {});
    setFixes((f) => f.filter((x) => x.id !== id));
  }

  useEffect(() => {
    if (chosen === null) return;
    setBusy(true);
    setSheet(null);
    setChapter(null);
    setError("");
    api<Sheet>(`/admin/review-sheet/${chosen}`)
      .then(setSheet)
      .catch(() => setError("Couldn't load that subject."))
      .finally(() => setBusy(false));
  }, [chosen]);

  if (!staff) return null;

  // One chapter at a time keeps a printout short enough for a teacher to finish in one sitting.
  const shown: Sheet | null = sheet && {
    ...sheet,
    chapters: sheet.chapters.filter((c) => chapter === null || c.number === chapter),
  };
  const shownCount = shown ? shown.chapters.reduce((n, c) => n + c.topics.reduce((m, t) => m + t.questions.length, 0), 0) : 0;
  const fileName = sheet
    ? `syniq-review-${classWords(sheet.subject.grade)}-${sheet.subject.name}${chapter === null ? "" : `-chapter-${chapter}`}.csv`
        .replace(/\s+/g, "-")
        .toLowerCase()
    : "";

  return (
    <div className="wrap wide">
      <p className="no-print">
        <Link className="back-link" href={me?.role === "admin" ? "/admin" : "/teacher"}>
          ← Back
        </Link>
      </p>
      <h1>Teacher review sheet</h1>
      <div className="no-print">
        <p className="muted">
          Every question in a subject, with the right answer, the worked solution and the tip a student gets for each planned
          wrong answer. Print it or download it as a spreadsheet, tick what is right and write what to fix. Question numbers
          and ids let us find each one again.
        </p>
        <label>
          Subject{" "}
          <select value={chosen ?? ""} onChange={(e) => setChosen(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Choose a subject</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {BOARD_WORDS[s.syllabus] ?? s.syllabus} {classWords(s.grade)}: {s.name} ({s.questions} questions)
              </option>
            ))}
          </select>
        </label>
        {sheet && (
          <label>
            {" "}
            Chapter{" "}
            <select value={chapter ?? ""} onChange={(e) => setChapter(e.target.value ? Number(e.target.value) : null)}>
              <option value="">All chapters</option>
              {sheet.chapters.map((c) => (
                <option key={c.number} value={c.number}>
                  {c.number}. {c.title}
                </option>
              ))}
            </select>
          </label>
        )}
        {busy && <p className="muted">Loading…</p>}
        {error && <p role="alert">{error}</p>}
        {sheet && (
          <p>
            <button onClick={() => window.print()}>Print</button>{" "}
            <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(toCsv(shown!))}`} download={fileName}>
              Download spreadsheet (CSV)
            </a>
          </p>
        )}

        <section className="card">
          <h2>Bring back a filled-in spreadsheet</h2>
          <p className="muted">
            Upload the CSV after a teacher has written yes or no and what to fix. Questions marked no, or with a note, go on the fix
            list below. Nothing changes for students until the question itself is corrected.
          </p>
          <label htmlFor="filled">Filled-in sheet (CSV)</label>{" "}
          <input id="filled" type="file" accept=".csv,text/csv" onChange={(e) => readFilledSheet(e.target.files?.[0])} />
          {uploadError && (
            <p className="feedback warn" role="alert">
              {uploadError}
            </p>
          )}
          {upload && (
            <p role="status">
              {upload.to_fix} to fix, {upload.ok} marked correct, {upload.not_checked} not checked yet.
              {upload.unknown_ids.length > 0 && ` These ids weren't found: ${upload.unknown_ids.join(", ")}.`}
            </p>
          )}
          <h3>Fix list ({fixes.length})</h3>
          {fixes.length === 0 && <p className="muted">Nothing waiting to be fixed.</p>}
          <ul className="fix-list">
            {fixes.map((f) => (
              <li key={f.id}>
                <p>
                  <strong>{f.prompt}</strong> <span className="muted">(id {f.id}, answer {f.answer})</span>
                </p>
                <p className="muted">
                  {f.subject}, chapter {f.chapter}, {f.topic}
                </p>
                <p style={{ whiteSpace: "pre-line" }}>{f.note}</p>
                <button className="secondary" onClick={() => markFixed(f.id)}>
                  Fixed, take it off the list
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {shown && (
        <div className="print-sheet review-sheet">
          <h2>
            {BOARD_WORDS[shown.subject.syllabus] ?? shown.subject.syllabus} {classWords(shown.subject.grade)}: {shown.subject.name}
          </h2>
          <p className="muted">
            {chapter === null ? "" : `Chapter ${chapter} only. `}
            {shownCount} questions. Reviewer: ____________________ Date: ____________
          </p>
          {shown.chapters.map((ch) => (
            <section key={ch.number} className="card review-chapter">
              <h3>
                Chapter {ch.number}. {ch.title}
              </h3>
              {ch.topics.map((t) => (
                <div key={t.title}>
                  <h4>{t.title}</h4>
                  <ol className="review-list">
                    {t.questions.map((q) => (
                      <li key={q.id} value={q.n}>
                        <p>
                          <strong>{q.prompt}</strong>{" "}
                          <span className="muted">
                            ({LEVEL_WORDS[q.difficulty] ?? q.difficulty}, id {q.id}
                            {q.status !== "approved" ? `, ${q.status}` : ""})
                          </span>
                        </p>
                        {q.options.length > 0 && (
                          <ul className="review-options">
                            {q.options.map((o) => (
                              <li key={o}>{o === q.answer ? <strong>{o} ✓</strong> : o}</li>
                            ))}
                          </ul>
                        )}
                        {q.options.length === 0 && <p>Answer: <strong>{q.answer}</strong></p>}
                        {q.solution && <p className="muted">Solution: {q.solution}</p>}
                        {q.mistakes.length > 0 && (
                          <ul className="review-mistakes">
                            {q.mistakes.map((m) => (
                              <li key={m.wrong}>
                                If they answer <strong>{m.wrong}</strong>: {m.tip || <em>no tip</em>}
                              </li>
                            ))}
                          </ul>
                        )}
                        {q.fix_note && <p className="feedback warn no-print">Waiting to be fixed: {q.fix_note}</p>}
                        <p className="review-verdict">☐ Correct ☐ Fix: ______________________________________________</p>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
