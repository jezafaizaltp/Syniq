"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type DaysOut = { days: { date: string; answered: number }[]; week: { days: number; answered: number } };

/** The last four weeks as a grid of days. Quiet, no streak counter, nothing lost for a missed day. */
export default function Days() {
  const { t, lang } = useSession();
  const [data, setData] = useState<DaysOut | null>(null);
  useEffect(() => {
    api<DaysOut>("/me/days").then(setData).catch(() => undefined);
  }, []);
  if (!data) return null;
  const fmt = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString(lang === "ml" ? "ml-IN" : "en-IN", { weekday: "short", day: "numeric", month: "short" });
  return (
    <section className="card" aria-labelledby="days">
      <h2 id="days">{t("space.days_title")}</h2>
      <p className="muted">{t("space.days_note")}</p>
      <p>{t("space.days_week", { days: data.week.days, answered: data.week.answered })}</p>
      <ol className="days-grid">
        {data.days.map((d) => (
          <li key={d.date} className={d.answered ? "on" : ""} title={t("space.day_label", { date: fmt(d.date), n: d.answered })}>
            <span className="sr-only">{t("space.day_label", { date: fmt(d.date), n: d.answered })}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
