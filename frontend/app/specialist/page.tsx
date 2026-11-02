"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { STYLE_WORDS, METHOD_WORDS, api } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";

type Student = {
  id: number;
  name: string;
  chosen_support: string[];
  noticed_support: { mode: string; reason: string; since: string; on: boolean }[];
  settings: Record<string, unknown>;
  subjects: { subject: string; secure?: number; getting_there?: number; learning?: number }[];
  methods: { subject_id: number; subject: string; methods: { style: string; right_after: number; answers_after: number }[]; clearest: string | null }[];
  repeated_mistakes: { tag: string; times: number; tip: string | null }[];
  last_14_days: { read_aloud: number; breaks: number; responses: Record<string, number> };
};

const SETTING_WORDS: Record<string, string> = {
  font_scale: "Bigger text",
  high_contrast: "High contrast",
  dyslexia_font: "Easier-to-read font",
  reduced_motion: "Less motion",
  read_aloud: "Read aloud",
  extra_time: "Extra time",
  preferred_style: "Preferred explanation",
};

const RESPONSE_WORDS: Record<string, string> = {
  count_it_out: "Count it out with stars",
  step_by_step: "Step by step",
  real_life: "A real-life story",
  try_similar: "A smaller similar question",
};

/** Children a parent has shared with this specialist: support and patterns, never ranks, moods or marks. */
export default function SpecialistPage() {
  const { me, loading, t } = useSession();
  const router = useRouter();
  const [students, setStudents] = useState<Student[] | null>(null);

  useEffect(() => {
    if (!loading && me?.role !== "specialist") router.replace("/");
  }, [me, loading, router]);

  useEffect(() => {
    if (me?.role === "specialist") api<Student[]>("/specialist/students").then(setStudents).catch(() => setStudents([]));
  }, [me]);

  if (me?.role !== "specialist") return null;

  return (
    <div className="wrap wide">
      <h1>Children shared with you</h1>
      <p className="muted">
        A parent chose to share each child here, and can stop at any time. You see the support each child uses, progress in words
        and mistakes that keep coming back, to help you plan support. Mood check-ins, marks, notes and goals are never shown, and
        SYNiq never suggests a diagnosis. Each time you open this page it is recorded in the school&apos;s audit log.
      </p>
      {students && students.length === 0 && (
        <div className="card">
          <p>No children have been shared with you yet. A parent can share their child from their SYNiq page.</p>
        </div>
      )}
      {students?.map((s) => (
        <section key={s.id} className="card">
          <h2>{s.name}</h2>

          <h3>Support in use</h3>
          {s.chosen_support.length === 0 && s.noticed_support.length === 0 && Object.keys(s.settings).length === 0 ? (
            <p className="muted">None switched on.</p>
          ) : (
            <ul className="list">
              {s.chosen_support.map((m) => (
                <li key={m}>
                  <span>
                    {t(`support.${m}.child` as Key)}
                    <br />
                    <span className="muted">Chosen by a parent or the student</span>
                  </span>
                </li>
              ))}
              {s.noticed_support.map((n) => (
                <li key={n.mode}>
                  <span>
                    {t(`noticed.${n.mode}` as Key)}
                    <br />
                    <span className="muted">
                      Noticed by SYNiq{n.since && ` on ${n.since}`}: {n.reason}
                    </span>
                  </span>
                  <span className="pill">{n.on ? "On" : "Turned off by the student"}</span>
                </li>
              ))}
              {Object.entries(s.settings).map(([k, v]) => (
                <li key={k}>
                  <span>
                    {SETTING_WORDS[k] ?? k}
                    {k === "preferred_style" && typeof v === "string" && `: ${STYLE_WORDS[v] ?? v}`}
                    {k === "font_scale" && `: ${v}×`}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <h3>Progress by subject</h3>
          {s.subjects.length === 0 ? (
            <p className="muted">Nothing practised yet.</p>
          ) : (
            <ul className="list">
              {s.subjects.map((x) => (
                <li key={x.subject}>
                  <span>{x.subject}</span>
                  <span className="muted">
                    {x.secure ?? 0} secure · {x.getting_there ?? 0} getting there · {x.learning ?? 0} learning
                  </span>
                </li>
              ))}
            </ul>
          )}

          <h3>Ways of explaining that help</h3>
          {s.methods.length === 0 ? (
            <p className="muted">Not enough answers after explanations yet.</p>
          ) : (
            <ul className="list">
              {s.methods.map((m) => (
                <li key={m.subject_id}>
                  <span>
                    <strong>{m.subject}</strong>
                    {m.clearest ? ` (most helpful lately: ${METHOD_WORDS[m.clearest]})` : " (no one way stands out yet)"}
                    {m.methods.map((x) => (
                      <span key={x.style} className="muted" style={{ display: "block" }}>
                        {METHOD_WORDS[x.style]}: right {x.right_after} of {x.answers_after} times just after
                      </span>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <h3>Mistakes that keep coming back</h3>
          {s.repeated_mistakes.length === 0 ? (
            <p className="muted">None so far.</p>
          ) : (
            <ul className="list">
              {s.repeated_mistakes.map((m) => (
                <li key={m.tag}>
                  <span>
                    {m.tip ?? m.tag.replace(/_/g, " ")}
                    <br />
                    <span className="muted">{m.times} times</span>
                  </span>
                </li>
              ))}
            </ul>
          )}

          <h3>Last 14 days</h3>
          <p>
            Read aloud pressed {s.last_14_days.read_aloud} times. Took a break {s.last_14_days.breaks} times.
            {Object.keys(s.last_14_days.responses).length > 0 && (
              <>
                {" "}
                Ways SYNiq responded to wrong answers:{" "}
                {Object.entries(s.last_14_days.responses)
                  .map(([k, n]) => `${RESPONSE_WORDS[k] ?? k} (${n})`)
                  .join(", ")}
                .
              </>
            )}
          </p>
        </section>
      ))}
    </div>
  );
}
