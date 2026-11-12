"use client";

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { stepTitle, type MentorStep } from "./learn/Mentor";

export type Today = {
  answered: number;
  right: number;
  topics: { title: string; progress: string }[];
  lessons?: number;
  next?: MentorStep | null;
};

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
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => first.current?.focus(), []);
  // Escape goes back to learning; Tab stays inside the dialog, so a keyboard or switch user can't get lost behind it.
  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      onStay();
      return;
    }
    if (e.key !== "Tab" || !box.current) return;
    const items = Array.from(box.current.querySelectorAll<HTMLElement>("button"));
    if (!items.length) return;
    const [start, end] = [items[0], items[items.length - 1]];
    if (e.shiftKey && document.activeElement === start) {
      e.preventDefault();
      end.focus();
    } else if (!e.shiftKey && document.activeElement === end) {
      e.preventDefault();
      start.focus();
    }
  }
  return (
    <div className="modal-backdrop" onKeyDown={onKey}>
      <div ref={box} className="card modal" role="dialog" aria-modal="true" aria-labelledby="byg-title">
        <h2 id="byg-title">{t("today.title")}</h2>
        {today.answered > 0 && <p>{t("today.answered", { n: today.answered })}</p>}
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
        {!!today.lessons && <p>{t(today.lessons === 1 ? "today.lessons_one" : "today.lessons", { n: today.lessons })}</p>}
        {today.next && (
          <p>
            {t("today.next")} <strong>{stepTitle(t, today.next)}</strong>
          </p>
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
