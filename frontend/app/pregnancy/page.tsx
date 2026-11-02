"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { speak, useSession } from "@/lib/session";

type Month = { month: number; baby: string; you: string };
type Pregnancy = {
  child: { id: number; name: string; due_date: string; due_words: string };
  week: number;
  month: Month;
  next_month: Month | null;
  care: string[];
  calm: { id: string; title: string; minutes: number; steps: string[] }[];
  go_to_hospital_now: string[];
  sources: Record<string, { name: string; url: string }>;
  disclaimer: string;
};

export default function PregnancyPage() {
  return (
    <Suspense>
      <PregnancyView />
    </Suspense>
  );
}

/** For the mother: what to expect, check-ups, warning signs, and calm moments for herself. */
function PregnancyView() {
  const { me, loading } = useSession();
  const router = useRouter();
  const childId = Number(useSearchParams().get("child"));
  const [view, setView] = useState<Pregnancy | null>(null);
  const [error, setError] = useState("");
  const [calm, setCalm] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!me || me.role !== "guardian")) router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role === "guardian" && childId)
      api<Pregnancy>(`/pregnancy/${childId}`)
        .then(setView)
        .catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load. Check your internet and try again."));
  }, [me, childId]);

  if (!me || me.role !== "guardian") return null;
  if (!view)
    return error ? (
      <div className="wrap">
        <p className="feedback warn">{error}</p>
        <Link href="/family">← Family</Link>
      </div>
    ) : null;

  const open = view.calm.find((c) => c.id === calm);
  return (
    <div className="wrap">
      <Link href="/family">← Family</Link>
      <div className="hello" style={{ marginTop: 12 }}>
        <span className="wave" aria-hidden="true">
          🤰
        </span>
        <div>
          <h1 style={{ margin: 0 }}>Week {view.week}</h1>
          <p className="muted" style={{ margin: 0 }}>
            {view.child.due_words} · due {view.child.due_date}
          </p>
        </div>
      </div>
      <p className="muted">{view.disclaimer}</p>

      <section className="card sunny" aria-labelledby="month">
        <h2 id="month">Month {view.month.month}</h2>
        <p>
          <strong>Your baby:</strong> {view.month.baby}
        </p>
        <p>
          <strong>For you:</strong> {view.month.you}
        </p>
        {view.next_month && (
          <p className="muted">
            Next month: {view.next_month.baby} {view.next_month.you}
          </p>
        )}
      </section>

      <details className="card urgent" open>
        <summary>
          <strong>Go to hospital now if you have…</strong>
        </summary>
        <ul>
          {view.go_to_hospital_now.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <p>
          Call <strong>108</strong> or <strong>102</strong> for free transport.
        </p>
      </details>

      <section className="card" aria-labelledby="calm">
        <h2 id="calm">A calm moment for you</h2>
        <p className="muted">Small things for your own peace of mind. Do them whenever you like; there&apos;s nothing to keep up with.</p>
        {open ? (
          <div>
            <h3>
              {open.title} <span className="muted">· {open.minutes} min</span>
            </h3>
            <ol>
              {open.steps.map((s) => (
                <li key={s} style={{ marginBottom: 8 }}>
                  {s}
                </li>
              ))}
            </ol>
            <div className="row">
              <button className="secondary" onClick={() => speak(open.steps.join(" "))}>
                🔊 Read it to me
              </button>
              <button className="secondary" onClick={() => setCalm(null)}>
                Done
              </button>
            </div>
          </div>
        ) : (
          <div className="early-grid">
            {view.calm.map((c) => (
              <button key={c.id} className="early-tile" onClick={() => setCalm(c.id)}>
                <span>{c.title}</span>
                <span className="muted">{c.minutes} min</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="care">
        <h2 id="care">Check-ups and care</h2>
        <ul>
          {view.care.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </section>

      <details className="card">
        <summary>Where this comes from</summary>
        <ul>
          {Object.values(view.sources).map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.name}
              </a>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
