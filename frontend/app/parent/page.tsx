"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CHOSEN_SUPPORT, api, post, put } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";

type Child = {
  id: number;
  name: string;
  consent: Record<string, boolean>;
  support_modes: string[];
  noticed: { mode: string; reason: string; on: boolean }[];
};
type Progress = { questions_practised: number; note: string; concepts: { title: string; progress: string }[] };

const CONSENT_SCOPES = ["core_learning", "mood_checkins", "school_sharing"] as const;

export default function Parent() {
  const { me, loading, lang, t } = useSession();
  const router = useRouter();
  const [children, setChildren] = useState<Child[]>([]);
  const [progress, setProgress] = useState<Record<number, Progress>>({});

  useEffect(() => {
    if (!loading && (!me || me.role !== "guardian")) router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(async () => {
    const kids = await api<Child[]>("/guardian/children");
    const entries = await Promise.all(
      kids.map(async (k) => [k.id, await api<Progress>(`/guardian/children/${k.id}/progress`)] as const)
    );
    setProgress(Object.fromEntries(entries));
    setChildren(kids);
  }, []);

  useEffect(() => {
    if (me?.role === "guardian") load();
  }, [me, load, lang]); // reload so reasons and notes come in the chosen language

  async function setSupport(child: Child, mode: string, on: boolean) {
    const modes = on ? [...child.support_modes.filter((m) => m !== mode), mode] : child.support_modes.filter((m) => m !== mode);
    await put(`/guardian/children/${child.id}/support`, { modes });
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
      {children.map((c) => (
        <section key={c.id} className="card">
          <h2>{c.name}</h2>
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
          {progress[c.id] && (
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
        </section>
      ))}
    </div>
  );
}
