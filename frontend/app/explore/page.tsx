"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, post } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { speak, useSession } from "@/lib/session";

type Card = { id: string; area: string; title: string; minutes: number; feeling: string | null };
type Overview = { areas: { area: string; activities: Card[] }[]; suggested: Card[]; enjoyed: Card[] };
type Activity = Card & { intro: string; steps: string[]; reflect: string; note: string };

const FEELINGS = ["loved", "okay", "not_for_me"] as const;
const AREA_ICON: Record<string, string> = { creative: "🎨", practical: "🛠️", scientific: "🔬", social: "🤝", enterprise: "💡" };

/** Short activities across five areas. What a student enjoyed is shown back to them, never turned into a label. */
export default function Explore() {
  const { me, loading, t } = useSession();
  const router = useRouter();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [open, setOpen] = useState<Activity | null>(null);
  const canLearn = me?.role === "student" && !!me.consent?.core_learning;

  useEffect(() => {
    if (!loading && (!me || me.role !== "student")) router.replace("/");
  }, [me, loading, router]);

  function load() {
    api<Overview>("/explore").then(setOverview).catch(() => setOverview(null));
  }
  useEffect(() => {
    if (canLearn) load();
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

  if (open) {
    return (
      <ActivityView
        activity={open}
        onDone={() => {
          setOpen(null);
          load();
        }}
      />
    );
  }

  const cardButton = (c: Card) => (
    <li key={c.id}>
      <span>
        {AREA_ICON[c.area]} {c.title}
        <br />
        <span className="muted">
          {t("explore.minutes", { n: c.minutes })}
          {c.feeling && ` · ${t(`explore.felt.${c.feeling}` as Key)}`}
        </span>
      </span>
      <button className="secondary" onClick={async () => setOpen(await api<Activity>(`/explore/${c.id}`))}>
        {c.feeling ? t("explore.again") : t("explore.try")}
      </button>
    </li>
  );

  return (
    <div className="wrap">
      <h1>{t("explore.title")}</h1>
      <p className="muted">{t("explore.intro")}</p>
      {overview && (
        <>
          {overview.suggested.length > 0 && (
            <section className="card" aria-labelledby="suggested">
              <h2 id="suggested">{t("explore.suggested")}</h2>
              <ul className="list">{overview.suggested.map(cardButton)}</ul>
            </section>
          )}
          {overview.enjoyed.length > 0 && (
            <section className="card" aria-labelledby="enjoyed">
              <h2 id="enjoyed">{t("explore.enjoyed")}</h2>
              <p className="muted">{t("explore.enjoyed_help")}</p>
              <ul className="list">{overview.enjoyed.map(cardButton)}</ul>
            </section>
          )}
          {overview.areas.map((a) => (
            <section key={a.area} className="card" aria-labelledby={`area-${a.area}`}>
              <h2 id={`area-${a.area}`}>
                {AREA_ICON[a.area]} {t(`explore.area.${a.area}` as Key)}
              </h2>
              <ul className="list">{a.activities.map(cardButton)}</ul>
            </section>
          ))}
        </>
      )}
    </div>
  );
}

function ActivityView({ activity, onDone }: { activity: Activity; onDone: () => void }) {
  const { t } = useSession();
  const [feeling, setFeeling] = useState<string | null>(null);
  const [note, setNote] = useState(activity.note ?? "");
  const [error, setError] = useState("");

  async function save() {
    if (!feeling) return;
    try {
      await post(`/explore/${activity.id}/reflect`, { feeling, note });
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("notes.failed"));
    }
  }

  const all = [activity.title, activity.intro, ...activity.steps].join(". ");
  return (
    <div className="wrap">
      <button className="secondary" onClick={onDone}>
        ← {t("explore.title")}
      </button>
      <div className="card" style={{ marginTop: 16 }}>
        <p className="muted">
          {AREA_ICON[activity.area]} {t(`explore.area.${activity.area}` as Key)} · {t("explore.minutes", { n: activity.minutes })}
        </p>
        <h2>{activity.title}</h2>
        <p>{activity.intro}</p>
        <ol>
          {activity.steps.map((s, i) => (
            <li key={i} style={{ marginBottom: 8 }}>
              {s}
            </li>
          ))}
        </ol>
        <button className="secondary" onClick={() => speak(all)}>
          {t("learn.read_aloud")}
        </button>
      </div>
      <div className="card">
        <h2>{t("explore.after")}</h2>
        <p>{activity.reflect}</p>
        <div className="options" role="group" aria-label={t("explore.how_felt")}>
          {FEELINGS.map((f) => (
            <button key={f} type="button" className="option" aria-pressed={feeling === f} onClick={() => setFeeling(f)}>
              {t(`explore.feel.${f}` as Key)}
            </button>
          ))}
        </div>
        <label htmlFor="reflect-note">{t("explore.note")}</label>
        <textarea id="reflect-note" rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
        <p className="muted">{t("explore.private")}</p>
        {error && (
          <p className="feedback warn" role="alert">
            {error}
          </p>
        )}
        <div className="row">
          <button disabled={!feeling} onClick={save}>
            {t("explore.save")}
          </button>
          <button className="secondary" onClick={onDone}>
            {t("explore.not_yet")}
          </button>
        </div>
      </div>
    </div>
  );
}
