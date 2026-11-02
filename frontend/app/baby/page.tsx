"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, api, del, post, put } from "@/lib/api";
import { useSession } from "@/lib/session";

type Source = { name: string; url: string };
type Log = { id: number; kind: string; at: string; minutes: number | null; note: string };
type Baby = {
  child: { id: number; name: string; age: string; months: number };
  today: string;
  play: { title: string; ideas: string[] };
  every_child: string[];
  milestones: { months: number; status: "past" | "now" | "next"; mention_to_doctor: boolean; items: { id: string; text: string; seen: boolean }[] }[];
  vaccines: { id: string; name: string; when: string; due_on: string; status: "given" | "overdue" | "due" | "upcoming"; given_on: string | null; optional?: boolean }[];
  vaccine_note: string;
  food: { points: string[] };
  sleep: string[];
  log_kinds: Record<string, { label: string; icon: string }>;
  log_today: Log[];
  log_week: { day: string; counts: Record<string, number>; sleep_minutes: number }[];
  questions: { id: string; q: string; a: string; source: string }[];
  see_doctor_now: string[];
  together_time: boolean;
  sources: Record<string, Source>;
  disclaimer: string;
};

const VACCINE_WORDS = { given: "Given", overdue: "Not marked as given yet, was due", due: "Due now", upcoming: "Coming up" };

export default function BabyPage() {
  return (
    <Suspense>
      <BabyView />
    </Suspense>
  );
}

/** For the mother and family: everything here is done together with the baby, off screen. */
function BabyView() {
  const { me, loading } = useSession();
  const router = useRouter();
  const childId = Number(useSearchParams().get("child"));
  const [view, setView] = useState<Baby | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && (!me || me.role !== "guardian")) router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(() => {
    api<Baby>(`/baby/${childId}`)
      .then(setView)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load. Check your internet and try again."));
  }, [childId]);
  useEffect(() => {
    if (me?.role === "guardian" && childId) load();
  }, [me, childId, load]);

  if (!me || me.role !== "guardian") return null;
  if (!view)
    return error ? (
      <div className="wrap">
        <p className="feedback warn">{error}</p>
        <Link href="/family">← Family</Link>
      </div>
    ) : null;

  const name = view.child.name;
  return (
    <div className="wrap">
      <Link href="/family">← Family</Link>
      <div className="hello" style={{ marginTop: 12 }}>
        <span className="wave" aria-hidden="true">
          🍼
        </span>
        <div>
          <h1 style={{ margin: 0 }}>{name}</h1>
          <p className="muted" style={{ margin: 0 }}>
            {view.child.age}
          </p>
        </div>
      </div>
      <p className="muted">{view.disclaimer}</p>

      <details className="card urgent">
        <summary>
          <strong>See a doctor now if…</strong>
        </summary>
        <ul>
          {view.see_doctor_now.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <p>
          Call <strong>108</strong> for a free ambulance.
        </p>
      </details>

      <CareLogCard view={view} onChange={load} />

      <section className="card" aria-labelledby="play">
        <h2 id="play">Play together: {view.play.title}</h2>
        <ul>
          {view.play.ideas.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
        <details>
          <summary>Ideas for every child, at their own pace</summary>
          <ul>
            {view.every_child.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </details>
        {view.together_time && (
          <p>
            <Link className="btn secondary" href={`/early?child=${view.child.id}`}>
              Together-time on screen (10 minutes)
            </Link>
          </p>
        )}
      </section>

      <Milestones view={view} onChange={load} />
      <Vaccines view={view} onChange={load} />

      <section className="card" aria-labelledby="food">
        <h2 id="food">Food</h2>
        <ul>
          {view.food.points.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
        <h2>Safe sleep</h2>
        <ul>
          {view.sleep.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </section>

      <section className="card" aria-labelledby="questions">
        <h2 id="questions">Common questions</h2>
        {view.questions.map((q) => (
          <details key={q.id} className="qa">
            <summary>{q.q}</summary>
            <p>{q.a}</p>
            <p className="muted">
              Source:{" "}
              <a href={view.sources[q.source]?.url} target="_blank" rel="noreferrer">
                {view.sources[q.source]?.name}
              </a>
            </p>
          </details>
        ))}
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

function CareLogCard({ view, onChange }: { view: Baby; onChange: () => void }) {
  const [kind, setKind] = useState<string | null>(null);
  const [minutes, setMinutes] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const timed = kind === "breastfeed" || kind === "sleep";

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await post(`/baby/${view.child.id}/log`, { kind, minutes: minutes ? Number(minutes) : null, note });
      setKind(null);
      setMinutes("");
      setNote("");
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save");
    }
  }

  const today = view.log_week[view.log_week.length - 1];
  return (
    <section className="card" aria-labelledby="log">
      <h2 id="log">Today</h2>
      <div className="log-buttons">
        {Object.entries(view.log_kinds).map(([k, v]) => (
          <button key={k} type="button" className="option" aria-pressed={kind === k} onClick={() => setKind(kind === k ? null : k)}>
            <span aria-hidden="true">{v.icon}</span> {v.label}
          </button>
        ))}
      </div>
      {kind && (
        <form onSubmit={save} className="row" style={{ alignItems: "flex-end" }}>
          {timed && (
            <div>
              <label htmlFor="log-min">Minutes (optional)</label>
              <input id="log-min" type="number" min={0} max={1440} inputMode="numeric" value={minutes} onChange={(e) => setMinutes(e.target.value)} style={{ width: 120 }} />
            </div>
          )}
          <div style={{ flex: 1, minWidth: 160 }}>
            <label htmlFor="log-note">Note (optional)</label>
            <input id="log-note" maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} placeholder={kind === "food" ? "e.g. ragi porridge, 4 spoons" : ""} />
          </div>
          <button type="submit">Save {view.log_kinds[kind].label.toLowerCase()}</button>
        </form>
      )}
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      {view.log_today.length > 0 ? (
        <ul className="list">
          {view.log_today.map((l) => (
            <li key={l.id}>
              <span>
                {view.log_kinds[l.kind]?.icon} {l.at.slice(11, 16)} · {view.log_kinds[l.kind]?.label}
                {l.minutes ? `, ${l.minutes} min` : ""}
                {l.note && <span className="muted"> · {l.note}</span>}
              </span>
              <button
                className="secondary"
                aria-label="Remove"
                onClick={async () => {
                  await del(`/baby/${view.child.id}/log/${l.id}`).catch(() => undefined);
                  onChange();
                }}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Tap above to note a feed, meal, sleep or nappy. Anyone in the family can add to it.</p>
      )}
      {today && (
        <p className="muted">
          Today so far: {today.counts.breastfeed + today.counts.bottle} feeds, {today.counts.food} meals, {today.counts.nappy} nappies,{" "}
          {Math.round(today.sleep_minutes / 6) / 10} hours of sleep logged.
        </p>
      )}
    </section>
  );
}

function Milestones({ view, onChange }: { view: Baby; onChange: () => void }) {
  async function toggle(id: string, seen: boolean) {
    await put(`/baby/${view.child.id}/milestones/${id}`, { seen });
    onChange();
  }
  return (
    <section className="card" aria-labelledby="milestones">
      <h2 id="milestones">Milestones</h2>
      <p className="muted">
        Things most babies (3 in 4) do by each age. Tick what you&apos;ve seen. Every baby is different, and this is not a test.
      </p>
      {view.milestones.some((g) => g.mention_to_doctor) && (
        <p className="feedback note">
          Some earlier ones aren&apos;t ticked yet. If you haven&apos;t seen them, mention it at your next check-up. Asking early is always fine, and your
          doctor can tell you what helps.
        </p>
      )}
      {view.milestones.map((g) => (
        <details key={g.months} open={g.status === "now"} className="milestone-group">
          <summary>
            <strong>By {g.months} months</strong>
            {g.status === "now" && <span className="pill">Now</span>}
            {g.status === "next" && <span className="muted"> · coming up</span>}
            {g.status === "past" && (
              <span className="muted">
                {" "}
                · {g.items.filter((i) => i.seen).length} of {g.items.length} ticked
              </span>
            )}
          </summary>
          {g.items.map((i) => (
            <label key={i.id} className="check">
              <input type="checkbox" checked={i.seen} onChange={(e) => toggle(i.id, e.target.checked)} />
              {i.text}
            </label>
          ))}
        </details>
      ))}
    </section>
  );
}

function Vaccines({ view, onChange }: { view: Baby; onChange: () => void }) {
  const [editing, setEditing] = useState<string | null>(null);
  const [day, setDay] = useState(view.today);
  const [error, setError] = useState("");

  async function save(id: string, given_on: string | null) {
    setError("");
    try {
      await put(`/baby/${view.child.id}/vaccines/${id}`, { given_on });
      setEditing(null);
      onChange();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't save");
    }
  }

  return (
    <section className="card" aria-labelledby="vaccines">
      <h2 id="vaccines">Vaccines</h2>
      <p className="muted">{view.vaccine_note}</p>
      <ul className="list vaccine-list">
        {view.vaccines.map((v) => (
          <li key={v.id}>
            <span>
              <strong>{v.when}</strong>
              <br />
              {v.name}
              <br />
              <span className={`pill vaccine-${v.status}`}>{v.status === "given" ? `Given ${v.given_on}` : `${VACCINE_WORDS[v.status]} · ${v.due_on}`}</span>
            </span>
            {editing === v.id ? (
              <span className="row" style={{ flexWrap: "nowrap" }}>
                <input type="date" aria-label="Date given" value={day} max={view.today} onChange={(e) => setDay(e.target.value)} />
                <button onClick={() => save(v.id, day)}>Save</button>
              </span>
            ) : v.status === "given" ? (
              <button className="secondary" onClick={() => save(v.id, null)}>
                Undo
              </button>
            ) : (
              <button className="secondary" onClick={() => (setEditing(v.id), setDay(view.today))}>
                Mark given
              </button>
            )}
          </li>
        ))}
      </ul>
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
