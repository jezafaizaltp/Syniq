"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Topic = {
  subject: string;
  chapter: string;
  topic: string;
  questions: { text: string; answered_by: string; asked: string }[];
};

const ANSWERED_WORDS: Record<string, string> = {
  ai: "Answered by outside AI",
  none: "Not answered (no AI switched on)",
};

/** What students asked Ask SYNiq that the lessons didn't cover, so the content can grow. No student details are kept. */
export default function TutorQuestions() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [subject, setSubject] = useState("");
  const [error, setError] = useState("");
  const staff = me?.role === "admin" || me?.role === "teacher";

  useEffect(() => {
    if (!loading && !staff) router.replace("/");
  }, [staff, loading, router]);

  useEffect(() => {
    if (staff)
      api<Topic[]>("/admin/tutor-questions")
        .then(setTopics)
        .catch(() => setError("Couldn't load the questions."));
  }, [staff]);

  if (!staff) return null;

  const subjects = Array.from(new Set((topics ?? []).map((t) => t.subject))).sort();
  const shown = (topics ?? []).filter((t) => !subject || t.subject === subject);
  const total = shown.reduce((n, t) => n + t.questions.length, 0);

  return (
    <div className="wrap wide">
      <p>
        <Link className="back-link" href={me?.role === "admin" ? "/admin" : "/teacher"}>
          ← Back
        </Link>
      </p>
      <h1>Questions students asked</h1>
      <p className="muted">
        When a student asks Ask SYNiq something the lesson doesn&apos;t cover, the question is saved here without their name,
        class or any contact details. Topics asked about most come first. Use them to add explanations or questions where
        students are getting stuck.
      </p>
      {error && <p role="alert">{error}</p>}
      {topics && topics.length === 0 && <p className="card muted">No saved questions yet.</p>}
      {topics && topics.length > 0 && (
        <>
          <label>
            Subject{" "}
            <select value={subject} onChange={(e) => setSubject(e.target.value)}>
              <option value="">All subjects</option>
              {subjects.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <p className="muted">
            {total} questions across {shown.length} topics.
          </p>
          {shown.map((t) => (
            <section key={`${t.subject}|${t.chapter}|${t.topic}`} className="card">
              <h2>
                {t.topic} <span className="muted">({t.questions.length})</span>
              </h2>
              <p className="muted">
                {t.subject}, chapter {t.chapter}
              </p>
              <ul>
                {t.questions.map((q, i) => (
                  <li key={i}>
                    {q.text}
                    <br />
                    <span className="muted">
                      {q.asked} · {ANSWERED_WORDS[q.answered_by] ?? q.answered_by}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </div>
  );
}
