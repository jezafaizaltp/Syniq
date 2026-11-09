"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

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
  mistakes: { wrong: string; tip: string }[];
};
type Sheet = {
  subject: SubjectRow;
  questions: number;
  chapters: { number: number; title: string; topics: { title: string; questions: Question[] }[] }[];
};

const BOARD_WORDS: Record<string, string> = { kerala_scert: "Kerala SCERT", cbse: "CBSE" };
const LEVEL_WORDS = ["", "Easy", "Medium", "Harder"];

function classWords(grade: number) {
  return grade === -1 ? "LKG" : grade === 0 ? "UKG" : `Class ${grade}`;
}

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
  const staff = me?.role === "admin" || me?.role === "teacher";

  useEffect(() => {
    if (!loading && !staff) router.replace("/");
  }, [staff, loading, router]);

  useEffect(() => {
    if (staff) api<SubjectRow[]>("/admin/review-sheet").then(setSubjects).catch(() => setError("Couldn't load the subjects."));
  }, [staff]);

  useEffect(() => {
    if (chosen === null) return;
    setBusy(true);
    setSheet(null);
    setError("");
    api<Sheet>(`/admin/review-sheet/${chosen}`)
      .then(setSheet)
      .catch(() => setError("Couldn't load that subject."))
      .finally(() => setBusy(false));
  }, [chosen]);

  if (!staff) return null;

  const fileName = sheet ? `syniq-review-${classWords(sheet.subject.grade)}-${sheet.subject.name}.csv`.replace(/\s+/g, "-").toLowerCase() : "";

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
        {busy && <p className="muted">Loading…</p>}
        {error && <p role="alert">{error}</p>}
        {sheet && (
          <p>
            <button onClick={() => window.print()}>Print</button>{" "}
            <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(toCsv(sheet))}`} download={fileName}>
              Download spreadsheet (CSV)
            </a>
          </p>
        )}
      </div>

      {sheet && (
        <div className="print-sheet review-sheet">
          <h2>
            {BOARD_WORDS[sheet.subject.syllabus] ?? sheet.subject.syllabus} {classWords(sheet.subject.grade)}: {sheet.subject.name}
          </h2>
          <p className="muted">
            {sheet.questions} questions. Reviewer: ____________________ Date: ____________
          </p>
          {sheet.chapters.map((ch) => (
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
