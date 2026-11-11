"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { ACH_KEYS, earnedOn, type RewardsView } from "../Rewards";

/**
 * An achievement card the learner can print and show, if they want to. They choose what goes on it.
 * No marks, no levels, nothing that compares them with anyone.
 */
export default function AchievementCard() {
  const { me, loading, t, lang } = useSession();
  const router = useRouter();
  const [view, setView] = useState<RewardsView | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!loading && (!me || me.role !== "student")) router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role !== "student") return;
    api<RewardsView>("/me/rewards")
      .then((v) => {
        setView(v);
        if (v.on) setChosen(new Set(v.achievements.map((a) => a.id)));
      })
      .catch(() => setView({ on: false }));
  }, [me]);

  if (!me || !view) return null;
  if (!view.on) {
    return (
      <div className="wrap">
        <p>{t("rewards.off")}</p>
        <Link href="/space">{t("card.back")}</Link>
      </div>
    );
  }
  const shown = view.achievements.filter((a) => chosen.has(a.id));
  const toggle = (id: string) =>
    setChosen((c) => {
      const n = new Set(c);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <div className="wrap">
      <div className="no-print">
        <p>
          <Link href="/space">{t("card.back")}</Link>
        </p>
        <p className="muted">{t("card.choose")}</p>
        <fieldset className="card-choose">
          {view.achievements.map((a) => (
            <label key={a.id} className="check-line">
              <input type="checkbox" checked={chosen.has(a.id)} onChange={() => toggle(a.id)} /> {t(ACH_KEYS[a.id] ?? "ach.title")}
            </label>
          ))}
        </fieldset>
        <button onClick={() => window.print()} disabled={shown.length === 0}>
          {t("card.print")}
        </button>
      </div>
      <section className="achievement-card" aria-label={t("card.title")}>
        <p className="card-brand">SYNiq</p>
        <h1>{me.name}</h1>
        <p className="muted">{t("card.title")}</p>
        <ul>
          {shown.map((a) => (
            <li key={a.id}>
              <span aria-hidden="true">🏅</span> {t(ACH_KEYS[a.id] ?? "ach.title")}
              <span className="muted"> · {earnedOn(a.earned_on, lang)}</span>
            </li>
          ))}
        </ul>
        {view.stickers.unlocked.length > 0 && <p className="card-stickers">{view.stickers.unlocked.join(" ")}</p>}
        <p className="muted small">{t("card.footer")}</p>
      </section>
    </div>
  );
}
