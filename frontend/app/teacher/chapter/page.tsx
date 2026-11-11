"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type ChapterChoice = { chapter_id: number; subject: string; number: number; title: string };
type Sheet = {
  chapter: string;
  number: number;
  students: number;
  topics: { topic: string; secure: number; getting_there: number; learning: number; not_started: number }[];
};

/** A printable planning sheet for one chapter: how many students are where on each topic. Counts only, no names. */
function ChapterSheet() {
  const { me, loading } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const classId = Number(params.get("class"));
  const [chapters, setChapters] = useState<ChapterChoice[]>([]);
  const [chapterId, setChapterId] = useState<number | null>(Number(params.get("chapter")) || null);
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [className, setClassName] = useState("");
  useEffect(() => {
    if (!loading && (!me || (me.role !== "teacher" && me.role !== "admin"))) router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (!me || !classId) return;
    api<ChapterChoice[]>(`/teacher/classes/${classId}/chapters`).then(setChapters).catch(() => setChapters([]));
    api<{ id: number; name: string }[]>("/teacher/classes").then((cs) => setClassName(cs.find((c) => c.id === classId)?.name ?? ""));
  }, [me, classId]);
  useEffect(() => {
    if (!me || !classId || !chapterId) return;
    api<Sheet>(`/teacher/classes/${classId}/chapter-progress?chapter_id=${chapterId}`).then(setSheet).catch(() => setSheet(null));
  }, [me, classId, chapterId]);
  if (!me) return null;
  return (
    <div className="wrap wide">
      <div className="no-print">
        <p>
          <Link href="/teacher">← Your class</Link>
        </p>
        <label htmlFor="sheet-chapter">Chapter</label>
        <select id="sheet-chapter" value={chapterId ?? ""} onChange={(e) => setChapterId(Number(e.target.value) || null)}>
          <option value="">Choose a chapter</option>
          {chapters.map((c) => (
            <option key={c.chapter_id} value={c.chapter_id}>
              {c.subject}: {c.number}. {c.title}
            </option>
          ))}
        </select>
        {sheet && (
          <p>
            <button onClick={() => window.print()}>Print</button>
          </p>
        )}
      </div>
      {sheet && (
        <section className="print-sheet">
          <h1>
            Chapter {sheet.number}: {sheet.chapter}
            {className ? ` · ${className}` : ""}
          </h1>
          <p className="muted">
            How many of the {sheet.students} students sharing progress with school are at each stage, per topic. Counts only:
            no names and no marks. Use it to plan which topics to go over together.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Secure</th>
                  <th>Getting there</th>
                  <th>Learning</th>
                  <th>Not started</th>
                </tr>
              </thead>
              <tbody>
                {sheet.topics.map((t) => (
                  <tr key={t.topic}>
                    <td>{t.topic}</td>
                    <td>{t.secure}</td>
                    <td>{t.getting_there}</td>
                    <td>{t.learning}</td>
                    <td>{t.not_started}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="sign-line">Plan: ____________________________________________</p>
        </section>
      )}
    </div>
  );
}

export default function ChapterProgress() {
  return (
    <Suspense fallback={null}>
      <ChapterSheet />
    </Suspense>
  );
}
