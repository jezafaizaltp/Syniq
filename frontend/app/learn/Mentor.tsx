"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";

type MentorStep = {
  kind: "fix_mistake" | "relearn" | "review" | "carry_on" | "start_topic" | "first_lesson";
  concept_id?: number | null;
  topic?: string | null;
  chapter_id?: number;
  chapter?: string;
  subject?: string;
  mistake?: string;
};
type Week = {
  answered: number;
  days: number;
  secured: number;
  fixed: number;
  lessons: number;
  came_back: number;
  helped_most: string | null;
};
export type MentorPlan = { part_of_day: "morning" | "afternoon" | "evening"; steps: MentorStep[]; week: Week };

const ICON: Record<string, string> = { fix_mistake: "🎯", relearn: "🔄", review: "🔁", carry_on: "➡️", start_topic: "🌱" };

/**
 * The learner's mentor, at the top of their home page: hello, at most three next steps (most useful first), and what
 * went well this week. Each step opens its chapter; the engine then picks the right topic and way. No marks, no ranks.
 */
export default function Mentor({ onOpen }: { onOpen: (chapterId: number) => void }) {
  const { me, t } = useSession();
  const [plan, setPlan] = useState<MentorPlan | null>(null);

  useEffect(() => {
    api<MentorPlan>("/me/mentor").then(setPlan).catch(() => setPlan(null));
  }, []);

  if (!plan || !me) return null;

  function title(s: MentorStep): string {
    const topic = s.topic ?? "";
    switch (s.kind) {
      case "fix_mistake":
        return t("mentor.fix_mistake");
      case "relearn":
        return t("mentor.relearn", { topic });
      case "review":
        return t("mentor.review", { topic });
      case "carry_on":
        return t("mentor.carry_on", { topic });
      default:
        return s.topic ? t("mentor.start_topic", { topic }) : t("mentor.next_chapter", { chapter: s.chapter ?? "" });
    }
  }

  function why(s: MentorStep): string {
    if (s.kind === "fix_mistake") return t("mentor.why_fix_mistake", { topic: s.topic ?? "" });
    if (s.kind === "relearn") return t("mentor.why_relearn");
    if (s.kind === "review") return t("mentor.why_review");
    return t("mentor.why_next", { subject: s.subject ?? "", chapter: s.chapter ?? "" });
  }

  const w = plan.week;
  const growth: string[] = [];
  if (w.days) growth.push(t("mentor.week_days", { n: w.days }));
  if (w.secured) growth.push(t("mentor.week_secured", { n: w.secured }));
  if (w.fixed) growth.push(t("mentor.week_fixed", { n: w.fixed }));
  if (w.lessons) growth.push(t("mentor.week_lessons", { n: w.lessons }));
  if (w.came_back) growth.push(t("mentor.week_came_back", { n: w.came_back }));
  if (w.helped_most) growth.push(t("mentor.week_helped", { way: t(`way.${w.helped_most}` as Key) }));
  const steps = plan.steps.filter((s) => s.kind !== "first_lesson");

  return (
    <section className="card mentor-card" aria-labelledby="mentor-hello">
      <h2 id="mentor-hello">{t(`mentor.${plan.part_of_day}` as Key, { name: me.name.split(" ")[0] })}</h2>
      {steps.length > 0 ? (
        <>
          <p className="muted">{t("mentor.plan")}</p>
          <ol className="mentor-steps">
            {steps.map((s, i) => (
              <li key={`${s.kind}-${i}`}>
                <button className={i === 0 ? "mentor-step first" : "mentor-step secondary"} onClick={() => s.chapter_id && onOpen(s.chapter_id)}>
                  <span aria-hidden="true">{ICON[s.kind] ?? "➡️"}</span>
                  <span>
                    <strong>{title(s)}</strong>
                    <br />
                    <span className="mentor-why">{why(s)}</span>
                    {s.mistake && (
                      <>
                        <br />
                        <span className="mentor-why">{s.mistake}</span>
                      </>
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </>
      ) : (
        <p>{t("mentor.first_lesson")}</p>
      )}
      {(growth.length > 0 || w.answered === 0) && steps.length > 0 && (
        <div className="mentor-week">
          <h3>{t("mentor.week")}</h3>
          {growth.length ? (
            <ul>
              {growth.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">{t("mentor.week_none")}</p>
          )}
        </div>
      )}
    </section>
  );
}
