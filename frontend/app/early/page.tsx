"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, api, post, put } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Activity, HoldButton, PlayActivity } from "./play";

type Overview = {
  child: { id: number; name: string; age: string };
  limits: { daily: number; session: number; daily_max: number; session_max: number };
  holder: boolean;
  together_only: boolean;
  today: string;
  left_today: number;
  week: { day: string; minutes: number }[];
  areas: Record<string, string>;
  activities: Activity[];
};
type Sitting = { id: number | null; minutes: number; started: number; childId: number };
type Pending = { child_id: number; activity_id: string; day: string; seconds: number };

const PENDING_KEY = "syniq_early_pending";

function readPending(): Pending[] {
  try {
    return JSON.parse(localStorage.getItem(PENDING_KEY) ?? "[]");
  } catch {
    return [];
  }
}
function writePending(list: Pending[]) {
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify(list));
  } catch {
    /* storage unavailable */
  }
}

/** Sends time played offline, so it counts towards the daily limit. */
async function flushPending() {
  const left: Pending[] = [];
  for (const p of readPending()) {
    try {
      await post(`/early/${p.child_id}/played`, p);
    } catch (e) {
      if (!(e instanceof ApiError)) left.push(p); // still offline: keep it; a refusal from the server: drop it
    }
  }
  writePending(left);
}

export default function EarlyPage() {
  return (
    <Suspense>
      <Early />
    </Suspense>
  );
}

function Early() {
  const { me, loading } = useSession();
  const router = useRouter();
  const childId = Number(useSearchParams().get("child"));
  const [view, setView] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [chosen, setChosen] = useState<Activity | null>(null);
  const [sitting, setSitting] = useState<Sitting | null>(null);
  const [phase, setPhase] = useState<"pick" | "ready" | "play" | "between" | "goodbye">("pick");

  useEffect(() => {
    if (!loading && (!me || me.role !== "guardian")) router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async () => {
    await flushPending();
    try {
      setView(await api<Overview>(`/early/${childId}`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load. Check your internet and try again.");
    }
  }, [childId]);
  useEffect(() => {
    if (me?.role === "guardian" && childId) load();
  }, [me, childId, load]);

  if (!me || me.role !== "guardian") return null;
  if (error && !view)
    return (
      <div className="wrap">
        <p className="feedback warn">{error}</p>
        <Link href="/family">← Family</Link>
      </div>
    );
  if (!view) return null;

  // Offline, the saved copy doesn't know about time played since; take it off here.
  const offlineUsed = readPending()
    .filter((p) => p.child_id === childId && p.day === view.today)
    .reduce((n, p) => n + Math.ceil(p.seconds / 60), 0);
  const left = Math.max(0, view.left_today - offlineUsed);

  async function begin(activity: Activity) {
    setError("");
    try {
      const s = await post<{ id: number; minutes: number }>(`/early/${childId}/sessions`, { activity_id: activity.id });
      setSitting({ id: s.id, minutes: s.minutes, started: Date.now(), childId });
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
        return;
      }
      // No internet: play from the saved activities and record the time later.
      setSitting({ id: null, minutes: Math.min(view!.limits.session, left), started: Date.now(), childId });
    }
    setPhase("play");
  }

  async function finishSitting() {
    if (!sitting) return;
    const seconds = Math.round((Date.now() - sitting.started) / 1000);
    if (sitting.id !== null) {
      try {
        await post(`/early/sessions/${sitting.id}/end`, { seconds });
      } catch {
        /* the server caps an unended sitting at its full length */
      }
    } else {
      writePending([...readPending(), { child_id: childId, activity_id: chosen?.id ?? "offline", day: view!.today, seconds }]);
    }
    setSitting(null);
  }

  if (sitting && (phase === "play" || phase === "between") && chosen) {
    return (
      <PlaySitting
        sitting={sitting}
        activity={chosen}
        phase={phase}
        others={view.activities.filter((a) => a.id !== chosen.id)}
        onFinishedActivity={() => setPhase("between")}
        onChoose={(a) => {
          setChosen(a);
          setPhase("play");
        }}
        onTimeUp={async () => {
          await finishSitting();
          setPhase("goodbye");
        }}
      />
    );
  }

  if (phase === "goodbye" && chosen) {
    return (
      <div className="play-screen">
        <div className="play-stage">
          <p className="play-big-emoji" aria-hidden="true">
            🌙
          </p>
          <h1>All done for now</h1>
          <p className="play-word">Bye bye, screen!</p>
        </div>
        <div className="card play-adult">
          <h2>Something to do together now</h2>
          <p>{chosen.after}</p>
          <button
            onClick={() => {
              setPhase("pick");
              setChosen(null);
              load();
            }}
          >
            Back to {view.child.name}&apos;s page
          </button>
        </div>
      </div>
    );
  }

  if (phase === "ready" && chosen) {
    return (
      <div className="wrap">
        <button className="secondary" onClick={() => setPhase("pick")}>
          ← Back
        </button>
        <div className="card sunny" style={{ marginTop: 16 }}>
          <p className="early-cover" aria-hidden="true">
            {chosen.pic}
          </p>
          <h1>{chosen.title}</h1>
          <h2>{view.together_only ? "Sit together" : "Before you hand over"}</h2>
          <p>{chosen.together}</p>
          <p className="muted">
            Best played together. The screen says goodbye by itself after {Math.min(view.limits.session, left)} minutes, and only you can start
            another.
          </p>
          {error && (
            <p className="feedback warn" role="alert">
              {error}
            </p>
          )}
          <button onClick={() => begin(chosen)}>Start</button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <Link href={view.together_only ? `/baby?child=${view.child.id}` : "/family"}>← Back</Link>
      <h1 style={{ marginTop: 12 }}>{view.together_only ? `Together-time with ${view.child.name}` : `${view.child.name}'s healthy screen time`}</h1>
      <p className="muted">
        {view.together_only
          ? `${view.child.age}. Doctors advise no screens before 2, so this is only for when you really need it: up to 10 minutes a day, with ${view.child.name} on your lap, naming pictures together. Talking and playing with you is always better.`
          : `${view.child.age}. Slow, calm activities with no ads, points or videos. Doctors advise at most an hour a day at this age, and less is better.`}
      </p>

      <section className="card" aria-labelledby="today">
        <h2 id="today">{left > 0 ? `${left} minutes left today` : "Today's screen time is used up"}</h2>
        <WeekBars week={view.week} limit={view.limits.daily} />
        {view.holder ? (
          <Limits view={view} onSaved={load} />
        ) : (
          <p className="muted">
            Limit: {view.limits.daily} minutes a day, {view.limits.session} at a time. The account holder can change it.
          </p>
        )}
      </section>

      {left > 0 ? (
        Object.entries(view.areas).map(([area, title]) => (
          <section key={area} aria-labelledby={`area-${area}`}>
            <h2 id={`area-${area}`}>{title}</h2>
            <div className="early-grid">
              {view.activities
                .filter((a) => a.area === area)
                .map((a) => (
                  <button
                    key={a.id}
                    className="early-tile"
                    onClick={() => {
                      setChosen(a);
                      setPhase("ready");
                    }}
                  >
                    <span className="early-pic" aria-hidden="true">
                      {a.pic}
                    </span>
                    <span>{a.title}</span>
                  </button>
                ))}
            </div>
          </section>
        ))
      ) : (
        <div className="card sunny">
          <h2>Ideas away from the screen</h2>
          <ul>
            {view.activities.slice(0, 4).map((a) => (
              <li key={a.id}>{a.after}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PlaySitting({
  sitting,
  activity,
  phase,
  others,
  onFinishedActivity,
  onChoose,
  onTimeUp,
}: {
  sitting: Sitting;
  activity: Activity;
  phase: "play" | "between";
  others: Activity[];
  onFinishedActivity: () => void;
  onChoose: (a: Activity) => void;
  onTimeUp: () => void;
}) {
  const fired = useRef(false);
  const [share, setShare] = useState(0);
  useEffect(() => {
    const tick = () => {
      const used = (Date.now() - sitting.started) / 1000;
      setShare(Math.min(1, used / (sitting.minutes * 60)));
      if (used >= sitting.minutes * 60 && !fired.current) {
        fired.current = true;
        onTimeUp();
      }
    };
    tick();
    const t = setInterval(tick, 5000);
    return () => clearInterval(t);
  }, [sitting, onTimeUp]);

  // Three gentle choices for what's next, always from different areas.
  const next = others.filter((a, i, all) => all.findIndex((b) => b.area === a.area) === i && a.area !== activity.area).slice(0, 3);

  return (
    <div className="play-screen">
      <div className="play-top">
        {/* A thin bar for the adult, not a countdown for the child. */}
        <div className="play-time" aria-hidden="true">
          <span style={{ width: `${share * 100}%` }} />
        </div>
        <HoldButton
          label="Hold to stop"
          onDone={() => {
            fired.current = true;
            onTimeUp();
          }}
        />
      </div>
      {phase === "play" ? (
        <PlayActivity key={activity.id} activity={activity} onFinished={onFinishedActivity} />
      ) : (
        <div className="play-stage">
          <p className="play-word">What next?</p>
          <div className="play-options">
            {next.map((a) => (
              <button key={a.id} className="play-option" aria-label={a.title} onClick={() => onChoose(a)}>
                <span aria-hidden="true">{a.pic}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function WeekBars({ week, limit }: { week: { day: string; minutes: number }[]; limit: number }) {
  const top = Math.max(limit, ...week.map((w) => w.minutes), 1);
  return (
    <div className="week" role="img" aria-label={`Minutes each day this week: ${week.map((w) => w.minutes).join(", ")}`}>
      {week.map((w, i) => (
        <div key={w.day} className="week-day">
          <div className="week-bar">
            <span style={{ height: `${(w.minutes / top) * 100}%` }} />
          </div>
          <span className="week-label">{i === week.length - 1 ? "Today" : new Date(w.day + "T00:00").toLocaleDateString("en-IN", { weekday: "short" })}</span>
          <span className="week-min">{w.minutes}m</span>
        </div>
      ))}
    </div>
  );
}

function Limits({ view, onSaved }: { view: Overview; onSaved: () => void }) {
  const [daily, setDaily] = useState(view.limits.daily);
  const [session, setSession] = useState(view.limits.session);
  const [saved, setSaved] = useState("");
  const dailyChoices = [10, 15, 20, 30, 45, 60].filter((n) => n <= view.limits.daily_max);
  const sessionChoices = [5, 10, 15].filter((n) => n <= view.limits.session_max);

  async function save() {
    await put(`/early/${view.child.id}/limits`, { daily, session });
    setSaved("Saved");
    setTimeout(() => setSaved(""), 1500);
    onSaved();
  }

  return (
    <div className="row" style={{ alignItems: "flex-end", marginTop: 12 }}>
      <div>
        <label htmlFor="daily">Minutes a day</label>
        <select id="daily" value={daily} onChange={(e) => setDaily(Number(e.target.value))}>
          {dailyChoices.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="session">At a time</label>
        <select id="session" value={session} onChange={(e) => setSession(Number(e.target.value))}>
          {sessionChoices.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>
      <button className="secondary" onClick={save} disabled={daily === view.limits.daily && session === view.limits.session}>
        Save limits
      </button>
      {saved && <span className="muted">{saved}</span>}
    </div>
  );
}
