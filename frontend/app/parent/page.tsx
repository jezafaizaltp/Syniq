"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CHOSEN_SUPPORT, api, post, put } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import Link from "next/link";
import { useSession } from "@/lib/session";
import Methods, { type MethodSubject } from "../space/Methods";
import Mistakes, { type MistakePattern } from "../space/Mistakes";
import Strengths, { type StrengthsView } from "../space/Strengths";
import { ACH_KEYS } from "../space/Rewards";

type Child = {
  id: number;
  name: string;
  consent: Record<string, boolean>;
  support_modes: string[];
  noticed: { mode: string; reason: string; on: boolean }[];
  checkup_note?: boolean;
  rewards_on?: boolean;
};
type Specialist = { id: number; name: string; title: string; shared_with: number[] };
type Progress = { questions_practised: number; note: string; concepts: { title: string; progress: string }[] };

type Grew = { lessons: number; secured: number; fixed: number; came_back: number; helped_most: string | null };
type Week = { days: number; answered: number; topics: { title: string; progress: string }[]; achievements?: string[]; grew?: Grew };

const CONSENT_SCOPES = ["core_learning", "mood_checkins", "school_sharing", "thinking_puzzles"] as const;
type Thinking = { on: boolean; puzzles: number; kinds: { domain: string; trend: "growing" | "steady" | "just_started" }[] };

export default function Parent() {
  const { me, loading, lang, t } = useSession();
  const router = useRouter();
  const [children, setChildren] = useState<Child[]>([]);
  const [progress, setProgress] = useState<Record<number, Progress>>({});
  const [methods, setMethods] = useState<Record<number, MethodSubject[]>>({});
  const [mistakes, setMistakes] = useState<Record<number, MistakePattern[]>>({});
  const [thinkingViews, setThinkingViews] = useState<Record<number, Thinking>>({});
  const [strengths, setStrengths] = useState<Record<number, StrengthsView>>({});
  const [specialists, setSpecialists] = useState<Specialist[]>([]);
  const [weeks, setWeeks] = useState<Record<number, Week>>({});

  useEffect(() => {
    if (!loading && (!me || me.role !== "guardian")) router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async () => {
    const kids = await api<Child[]>("/guardian/children");
    const entries = await Promise.all(
      kids.map(async (k) => [k.id, await api<Progress>(`/guardian/children/${k.id}/progress`)] as const)
    );
    setProgress(Object.fromEntries(entries));
    const helps = await Promise.all(
      kids.map(async (k) => [k.id, (await api<{ subjects: MethodSubject[] }>(`/guardian/children/${k.id}/methods`).catch(() => ({ subjects: [] }))).subjects] as const)
    );
    setMethods(Object.fromEntries(helps));
    const repeats = await Promise.all(
      kids.map(async (k) => [k.id, (await api<{ patterns: MistakePattern[] }>(`/guardian/children/${k.id}/mistakes`).catch(() => ({ patterns: [] }))).patterns] as const)
    );
    setMistakes(Object.fromEntries(repeats));
    const growth = await Promise.all(
      kids.map(async (k) => [k.id, await api<Thinking>(`/guardian/children/${k.id}/thinking`).catch(() => ({ on: false, puzzles: 0, kinds: [] }))] as const)
    );
    setThinkingViews(Object.fromEntries(growth));
    const shines = await Promise.all(
      kids.map(async (k) => [k.id, await api<StrengthsView>(`/guardian/children/${k.id}/strengths`).catch(() => null)] as const)
    );
    setStrengths(Object.fromEntries(shines.filter(([, v]) => v)) as Record<number, StrengthsView>);
    const lastWeek = await Promise.all(
      kids.map(async (k) => [k.id, await api<Week>(`/guardian/children/${k.id}/week`).catch(() => null)] as const)
    );
    setWeeks(Object.fromEntries(lastWeek.filter(([, w]) => w)) as Record<number, Week>);
    setChildren(kids);
    setSpecialists(await api<Specialist[]>("/guardian/specialists").catch(() => []));
  }, []);

  useEffect(() => {
    if (me?.role === "guardian") load();
  }, [me, load, lang]); // reload so reasons and notes come in the chosen language

  async function setSupport(child: Child, mode: string, on: boolean) {
    const modes = on ? [...child.support_modes.filter((m) => m !== mode), mode] : child.support_modes.filter((m) => m !== mode);
    await put(`/guardian/children/${child.id}/support`, { modes });
    load();
  }

  async function setRewards(childId: number, on: boolean) {
    await put(`/guardian/children/${childId}/rewards`, { on });
    load();
  }

  async function hideCheckup(childId: number) {
    await post(`/guardian/children/${childId}/checkup-note/hide`, {});
    load();
  }

  async function share(childId: number, specialistId: number, on: boolean) {
    await put(`/guardian/children/${childId}/specialists/${specialistId}`, { share: on });
    load();
  }

  async function setConsent(childId: number, scope: string, granted: boolean) {
    await post(`/guardian/children/${childId}/consent`, { scope, granted });
    load();
  }

  if (!me || me.role !== "guardian") return null;

  return (
    <div className="wrap">
      <h1>{t("parent.title")}</h1>
      <p>
        <Link href="/help/parent">{t("parent.help_link")}</Link>
      </p>
      {children.map((c) => (
        <section key={c.id} className="card">
          <h2>{c.name}</h2>
          {!c.consent.core_learning && (
            <div className="feedback note" role="status">
              <p>{t("parent.needs_consent", { name: c.name })}</p>
              <button onClick={() => setConsent(c.id, "core_learning", true)}>{t("parent.give_consent", { name: c.name })}</button>
            </div>
          )}
          {c.consent.core_learning && weeks[c.id] && (
            <>
              <h3>{t("parent.week_title")}</h3>
              {weeks[c.id].answered ? (
                <p>{t("parent.week_line", { name: c.name, days: weeks[c.id].days, answered: weeks[c.id].answered })}</p>
              ) : (
                // A lesson with no practice yet is still learning this week: don't say "hasn't practised" above it.
                !grewAny(weeks[c.id].grew) && <p>{t("parent.week_none", { name: c.name })}</p>
              )}
              {weeks[c.id].topics.length > 0 && (
                <p className="muted">
                  {t("parent.week_topics")} {weeks[c.id].topics.map((x) => `${x.title} (${t(`progress.${x.progress}` as Key)})`).join(", ")}
                </p>
              )}
              {weeks[c.id].grew && <GrewList grew={weeks[c.id].grew!} name={c.name} />}
              {!!weeks[c.id].achievements?.length && (
                <p>
                  🏅 {t("parent.week_achievements", { name: c.name })}{" "}
                  {weeks[c.id].achievements!.map((a) => t(ACH_KEYS[a] ?? "ach.title")).join(", ")}
                </p>
              )}
            </>
          )}
          {c.consent.core_learning && progress[c.id] && (
            <>
              <h3>{t("parent.progress")}</h3>
              <p className="muted">
                {t("parent.practised", { n: progress[c.id].questions_practised, note: progress[c.id].note })}
              </p>
              {progress[c.id].concepts.length === 0 ? (
                <p>{t("parent.nothing_yet")}</p>
              ) : (
                <ul className="list">
                  {progress[c.id].concepts.map((p) => (
                    <li key={p.title}>
                      <span>{p.title}</span>
                      <span className="pill">{t(`progress.${p.progress}` as Key)}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="muted">{t("parent.tip", { name: c.name })}</p>
            </>
          )}
          {strengths[c.id] && (
            <>
              <h3>{t("strengths.parent_title", { name: c.name })}</h3>
              <p className="muted">{t("strengths.parent_note", { name: c.name })}</p>
              <Strengths view={strengths[c.id]} t={t} name={c.name} />
            </>
          )}
          {methods[c.id] && methods[c.id].length > 0 && (
            <>
              <h3>{t("parent.helps", { name: c.name })}</h3>
              <p className="muted">{t("parent.helps_note", { name: c.name })}</p>
              <Methods subjects={methods[c.id]} t={t} />
            </>
          )}
          {thinkingViews[c.id]?.on && thinkingViews[c.id].puzzles > 0 && (
            <>
              <h3>{t("parent.thinking", { name: c.name })}</h3>
              <p className="muted">{t("parent.thinking_help")}</p>
              <ul className="list">
                {thinkingViews[c.id].kinds.map((k) => (
                  <li key={k.domain}>
                    <span>{t(`thinking.${k.domain}` as Key)}</span>
                    <span className="muted">{t(`trend.${k.trend}` as Key)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {mistakes[c.id] && mistakes[c.id].length > 0 && (
            <>
              <h3>{t("parent.mistakes", { name: c.name })}</h3>
              <p className="muted">{t("parent.mistakes_help")}</p>
              <Mistakes patterns={mistakes[c.id]} t={t} />
            </>
          )}
          {c.noticed.length > 0 && (
            <>
              <h3>{t("parent.noticed", { name: c.name })}</h3>
              <ul className="list">
                {c.noticed.map((n) => (
                  <li key={n.mode}>
                    <span>
                      {t(`noticed.${n.mode}` as Key)}
                      <br />
                      <span className="muted">{n.reason}</span>
                    </span>
                    <span className="pill">{n.on ? t("parent.on") : t("parent.turned_off", { name: c.name })}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {c.checkup_note && (
            <aside className="feedback note checkup-note" aria-labelledby={`checkup-${c.id}`}>
              <h3 id={`checkup-${c.id}`}>{t("checkup.title", { name: c.name })}</h3>
              <p>{t("checkup.body", { name: c.name })}</p>
              <p>{t("checkup.where")}</p>
              <p className="muted">{t("checkup.not_diagnosis")}</p>
              <button className="secondary" onClick={() => hideCheckup(c.id)}>
                {t("checkup.hide")}
              </button>
            </aside>
          )}
          <details className="parent-settings" open={!c.consent.core_learning}>
            <summary>{t("parent.settings_for", { name: c.name })}</summary>
            {CONSENT_SCOPES.map((scope) => (
              <div key={scope} style={{ marginTop: 8 }}>
                <label className="check">
                  <input type="checkbox" checked={!!c.consent[scope]} onChange={(e) => setConsent(c.id, scope, e.target.checked)} />
                  {t(`consent.${scope}`)}
                </label>
                <p className="muted" style={{ margin: "0 0 0 34px" }}>
                  {t(`consent.${scope}_help`)}
                </p>
              </div>
            ))}
            <h3>{t("parent.rewards")}</h3>
            <label className="check">
              <input type="checkbox" checked={c.rewards_on !== false} onChange={(e) => setRewards(c.id, e.target.checked)} />
              {t("parent.rewards_on", { name: c.name })}
            </label>
            <p className="muted" style={{ margin: "0 0 0 34px" }}>
              {t("parent.rewards_help")}
            </p>
            <h3>{t("settings.senses")}</h3>
            <p className="muted">{t("parent.senses_note")}</p>
            {CHOSEN_SUPPORT.map((key) => (
              <div key={key} style={{ marginTop: 8 }}>
                <label className="check">
                  <input type="checkbox" checked={c.support_modes.includes(key)} onChange={(e) => setSupport(c, key, e.target.checked)} />
                  {t(`support.${key}.child`)}
                </label>
                <p className="muted" style={{ margin: "0 0 0 34px" }}>
                  {t(`support.${key}.help`)}
                </p>
              </div>
            ))}
            {specialists.length > 0 && (
              <>
                <h3>{t("parent.specialists")}</h3>
                <p className="muted">{t("parent.specialists_help", { name: c.name })}</p>
                {specialists.map((s) => (
                  <label key={s.id} className="check" style={{ marginTop: 8 }}>
                    <input type="checkbox" checked={s.shared_with.includes(c.id)} onChange={(e) => share(c.id, s.id, e.target.checked)} />
                    <span>
                      {s.name}
                      {s.title && <span className="muted"> · {s.title}</span>}
                    </span>
                  </label>
                ))}
              </>
            )}
          </details>
        </section>
      ))}
    </div>
  );
}

const grewAny = (g?: Grew) => !!g && !!(g.lessons || g.secured || g.fixed || g.came_back || g.helped_most);

/** The same good news the child's mentor shows, in a parent's words: one line each, only what is true. */
function GrewList({ grew, name }: { grew: Grew; name: string }) {
  const { t } = useSession();
  const lines: string[] = [];
  const count = (key: string, n: number) => {
    if (n) lines.push(t((n === 1 ? `${key}_one` : key) as Key, { n, name }));
  };
  count("parent.grew_lessons", grew.lessons);
  count("parent.grew_secured", grew.secured);
  count("parent.grew_fixed", grew.fixed);
  count("parent.grew_came_back", grew.came_back);
  if (grew.helped_most) lines.push(t("parent.grew_helped", { name, way: t(`way.${grew.helped_most}` as Key) }));
  if (!lines.length) return null;
  return (
    <ul className="parent-grew">
      {lines.map((l) => (
        <li key={l}>{l}</li>
      ))}
    </ul>
  );
}
