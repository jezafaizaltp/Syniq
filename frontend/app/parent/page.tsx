"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CHOSEN_SUPPORT, NOTICED_SUPPORT, PROGRESS_WORDS, api, post, put } from "@/lib/api";
import { useSession } from "@/lib/session";

type Child = {
  id: number;
  name: string;
  consent: Record<string, boolean>;
  support_modes: string[];
  noticed: { mode: string; reason: string; on: boolean }[];
};
type Progress = { questions_practised: number; note: string; concepts: { title: string; progress: string }[] };

const CONSENT_WORDS: Record<string, [string, string]> = {
  core_learning: ["Use SYNiq for learning", "Required. Lets SYNiq save answers and adapt lessons for your child."],
  mood_checkins: ["Save mood check-ins", "Optional. Your child can always skip check-ins either way."],
  school_sharing: ["Share progress with the school", "Optional. Lets your child's teacher see topic progress."],
};

export default function Parent() {
  const { me, loading } = useSession();
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
  }, [me, load]);

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
      <h1>My children</h1>
      {children.map((c) => (
        <section key={c.id} className="card">
          <h2>{c.name}</h2>
          {Object.entries(CONSENT_WORDS).map(([scope, [title, help]]) => (
            <div key={scope} style={{ marginTop: 8 }}>
              <label className="check">
                <input type="checkbox" checked={!!c.consent[scope]} onChange={(e) => setConsent(c.id, scope, e.target.checked)} />
                {title}
              </label>
              <p className="muted" style={{ margin: "0 0 0 34px" }}>
                {help}
              </p>
            </div>
          ))}
          <h3>Seeing, hearing and speaking</h3>
          <p className="muted">SYNiq can&apos;t tell these from answers, so please tick any that apply.</p>
          {CHOSEN_SUPPORT.map(({ key, child, help }) => (
            <div key={key} style={{ marginTop: 8 }}>
              <label className="check">
                <input type="checkbox" checked={c.support_modes.includes(key)} onChange={(e) => setSupport(c, key, e.target.checked)} />
                {child}
              </label>
              <p className="muted" style={{ margin: "0 0 0 34px" }}>
                {help}
              </p>
            </div>
          ))}
          {c.noticed.length > 0 && (
            <>
              <h3>What SYNiq has noticed helps {c.name}</h3>
              <ul className="list">
                {c.noticed.map((n) => (
                  <li key={n.mode}>
                    <span>
                      {NOTICED_SUPPORT[n.mode] ?? n.mode}
                      <br />
                      <span className="muted">{n.reason}</span>
                    </span>
                    <span className="pill">{n.on ? "On" : `Turned off by ${c.name}`}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {progress[c.id] && (
            <>
              <h3>Progress</h3>
              <p className="muted">
                {progress[c.id].questions_practised} questions practised. {progress[c.id].note}
              </p>
              {progress[c.id].concepts.length === 0 ? (
                <p>Nothing practised yet.</p>
              ) : (
                <ul className="list">
                  {progress[c.id].concepts.map((p) => (
                    <li key={p.title}>
                      <span>{p.title}</span>
                      <span className="pill">{PROGRESS_WORDS[p.progress] ?? p.progress}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="muted">
                Tip: ask {c.name} to explain one topic to you in their own words. Teaching someone else is one of the best ways to
                remember.
              </p>
            </>
          )}
        </section>
      ))}
    </div>
  );
}
