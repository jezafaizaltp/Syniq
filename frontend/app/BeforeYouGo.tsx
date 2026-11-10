"use client";

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export type Today = { answered: number; right: number; topics: { title: string; progress: string }[] };

export async function loadToday(): Promise<Today | null> {
  try {
    return await api<Today>("/me/today");
  } catch {
    return null;
  }
}

/** Said back to a student as they sign out: what they did today, in words, with no marks. */
export default function BeforeYouGo({ today, onSignOut, onStay }: { today: Today; onSignOut: () => void; onStay: () => void }) {
  const { t } = useSession();
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => first.current?.focus(), []);
  return (
    <div className="modal-backdrop">
      <div className="card modal" role="dialog" aria-modal="true" aria-labelledby="byg-title">
        <h2 id="byg-title">{t("today.title")}</h2>
        <p>{t("today.answered", { n: today.answered })}</p>
        {today.topics.length > 0 && (
          <>
            <p>{t("today.topics")}</p>
            <ul>
              {today.topics.map((x) => (
                <li key={x.title}>
                  {x.title} <span className="muted">· {t(`progress.${x.progress}` as Key)}</span>
                </li>
              ))}
            </ul>
          </>
        )}
        <p className="muted">{t("today.see_you")}</p>
        <div className="row">
          <button ref={first} onClick={onSignOut}>
            {t("nav.sign_out")}
          </button>
          <button className="secondary" onClick={onStay}>
            {t("today.keep")}
          </button>
        </div>
      </div>
    </div>
  );
}
