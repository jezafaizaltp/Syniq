"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, api, del, post, put } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { NoteRow } from "../learn/Notes";
import Methods, { type MethodSubject } from "./Methods";
import Mistakes, { type MistakePattern } from "./Mistakes";
import Days from "./Days";
import Strengths, { type StrengthsView } from "./Strengths";
import Rewards, { type RewardsView } from "./Rewards";

type Overview = {
  subjects: {
    id: number;
    name: string;
    secure: number;
    getting_there: number;
    learning: number;
    carry_on: { chapter_id: number; title: string };
  }[];
  review_due: { concept_id: number; title: string; chapter_id: number; chapter: string; subject: string }[];
  stars?: number;
};
type Goal = { id: number; text: string; due_on: string | null; done: boolean };

/** The student's own space: progress in words, revision due, goals and notes. */
export default function MySpace() {
  const { me, loading, t, lang } = useSession();
  const router = useRouter();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [notes, setNotes] = useState<NoteRow[]>([]);
  const [methods, setMethods] = useState<MethodSubject[]>([]);
  const [mistakes, setMistakes] = useState<MistakePattern[]>([]);
  const [strengths, setStrengths] = useState<StrengthsView | null>(null);
  const [rewards, setRewards] = useState<RewardsView | null>(null);
  const [goalText, setGoalText] = useState("");
  const [goalDate, setGoalDate] = useState("");
  const [error, setError] = useState("");
  const canLearn = me?.role === "student" && !!me.consent?.core_learning;

  useEffect(() => {
    if (!loading && (!me || me.role !== "student")) router.replace("/");
  }, [me, loading, router]);

  useEffect(() => {
    if (!canLearn) return;
    api<Overview>("/me/overview").then(setOverview).catch(() => setOverview(null));
    api<Goal[]>("/me/goals").then(setGoals).catch(() => setGoals([]));
    api<NoteRow[]>("/me/notes").then(setNotes).catch(() => setNotes([]));
    api<{ subjects: MethodSubject[] }>("/me/methods").then((r) => setMethods(r.subjects)).catch(() => setMethods([]));
    api<{ patterns: MistakePattern[] }>("/me/mistakes").then((r) => setMistakes(r.patterns)).catch(() => setMistakes([]));
    api<StrengthsView>("/me/strengths").then(setStrengths).catch(() => setStrengths(null));
    api<RewardsView>("/me/rewards").then(setRewards).catch(() => setRewards(null));
  }, [canLearn]);

  if (!me || me.role !== "student") return null;
  if (!canLearn) {
    return (
      <div className="wrap">
        <div className="card">
          <h1>{t("learn.almost_ready")}</h1>
          <p>{t("learn.need_consent")}</p>
        </div>
      </div>
    );
  }

  async function addGoal(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const g = await post<Goal>("/me/goals", { text: goalText, due_on: goalDate || null });
      setGoals([g, ...goals]);
      setGoalText("");
      setGoalDate("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("notes.failed"));
    }
  }

  async function toggleGoal(g: Goal) {
    const updated = await put<Goal>(`/me/goals/${g.id}`, { done: !g.done });
    setGoals(goals.map((x) => (x.id === g.id ? updated : x)));
  }

  return (
    <div className="wrap">
      <h1>{t("space.title")}</h1>
      <p className="muted">{t("space.private")}</p>

      <Days />

      <section className="card" aria-labelledby="revise">
        <h2 id="revise">{t("space.revise")}</h2>
        {overview && overview.review_due.length > 0 ? (
          <ul className="list">
            {overview.review_due.map((r) => (
              <li key={r.concept_id}>
                <span>
                  {r.title}
                  <br />
                  <span className="muted">
                    {r.subject} · {r.chapter}
                  </span>
                </span>
                <Link className="btn secondary" href={`/learn?chapter=${r.chapter_id}`}>
                  {t("space.revise_now")}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{t("space.nothing_due")}</p>
        )}
      </section>

      <section className="card" aria-labelledby="progress">
        <h2 id="progress">{t("space.progress")}</h2>
        {overview && overview.subjects.length > 0 ? (
          <ul className="list">
            {overview.subjects.map((s) => (
              <li key={s.id}>
                <span>
                  <strong>{s.name}</strong>
                  <br />
                  <span className="muted">
                    {t("space.counts", { secure: s.secure, getting_there: s.getting_there, learning: s.learning })}
                  </span>
                </span>
                <Link className="btn secondary" href={`/learn?chapter=${s.carry_on.chapter_id}`}>
                  {t("space.carry_on", { chapter: s.carry_on.title })}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">
            {t("space.no_progress")} <Link href="/learn">{t("nav.learn")}</Link>
          </p>
        )}
      </section>

      {strengths && (
        <section className="card" aria-labelledby="strengths">
          <h2 id="strengths">{t("strengths.title")}</h2>
          <p className="muted">{t("strengths.note")}</p>
          <Strengths view={strengths} t={t} />
        </section>
      )}

      <section className="card" aria-labelledby="helps">
        <h2 id="helps">{t("space.helps")}</h2>
        <p className="muted">{t("space.helps_note")}</p>
        <Methods subjects={methods} t={t} />
      </section>

      <section className="card" aria-labelledby="mistakes">
        <h2 id="mistakes">{t("mistakes.title")}</h2>
        <p className="muted">{t("mistakes.help")}</p>
        <Mistakes patterns={mistakes} t={t} />
        {rewards?.on && !!overview?.stars && <p>{overview.stars === 1 ? t("stars.count_one") : t("stars.count", { n: overview.stars })}</p>}
      </section>

      <Rewards view={rewards} t={t} lang={lang} />

      <section className="card" aria-labelledby="goals">
        <h2 id="goals">{t("space.goals")}</h2>
        <form onSubmit={addGoal}>
          <label htmlFor="goal">{t("space.goal_label")}</label>
          <input id="goal" maxLength={200} value={goalText} placeholder={t("space.goal_example")} onChange={(e) => setGoalText(e.target.value)} />
          <label htmlFor="goal-date">{t("space.goal_date")}</label>
          <input id="goal-date" type="date" value={goalDate} onChange={(e) => setGoalDate(e.target.value)} />
          <div className="row" style={{ marginTop: 8 }}>
            <button type="submit" disabled={!goalText.trim()}>
              {t("space.goal_add")}
            </button>
          </div>
        </form>
        {error && (
          <p className="feedback warn" role="alert">
            {error}
          </p>
        )}
        <ul className="list">
          {goals.map((g) => (
            <li key={g.id}>
              <label className="check" style={{ margin: 0 }}>
                <input type="checkbox" checked={g.done} onChange={() => toggleGoal(g)} />
                <span style={{ textDecoration: g.done ? "line-through" : undefined }}>
                  {g.text}
                  {g.due_on && <span className="muted"> · {t("space.by", { date: g.due_on })}</span>}
                </span>
              </label>
              <button
                className="secondary"
                aria-label={t("space.goal_remove")}
                onClick={async () => {
                  await del(`/me/goals/${g.id}`).catch(() => undefined);
                  setGoals(goals.filter((x) => x.id !== g.id));
                }}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="card" aria-labelledby="notes">
        <h2 id="notes">{t("space.notes")}</h2>
        {notes.length === 0 ? (
          <p className="muted">{t("space.no_notes")}</p>
        ) : (
          <ul className="list">
            {notes.map((n) => (
              <li key={n.id}>
                <span>
                  {n.topic && <strong>{n.topic}: </strong>}
                  <span style={{ whiteSpace: "pre-wrap" }}>{n.body}</span>
                </span>
                <button
                  className="secondary"
                  aria-label={t("notes.delete")}
                  onClick={async () => {
                    await del(`/me/notes/${n.id}`).catch(() => undefined);
                    setNotes(notes.filter((x) => x.id !== n.id));
                  }}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
