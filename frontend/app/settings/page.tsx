"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CHOSEN_SUPPORT, NOTICED_SUPPORT, STYLE_WORDS, Settings } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function SettingsPage() {
  const { me, loading, saveSettings } = useSession();
  const router = useRouter();
  const [saved, setSaved] = useState("");

  useEffect(() => {
    if (!loading && !me) router.replace("/");
  }, [me, loading, router]);

  if (!me) return null;
  const s = me.settings ?? {};

  async function change(patch: Settings) {
    await saveSettings(patch);
    setSaved("Saved");
    setTimeout(() => setSaved(""), 1500);
  }

  const toggles: [keyof Settings, string, string][] = [
    ["high_contrast", "High contrast", "Strong colours that are easier to see."],
    ["dyslexia_font", "Easier-to-read text", "A clearer font with more space between letters and lines."],
    ["reduced_motion", "Reduce movement", "Turns off animations."],
    ["read_aloud", "Read aloud automatically", "SYNiq reads explanations and questions to you."],
    ["extra_time", "Extra time", "Never hurry me. (SYNiq has no timers, and this keeps it that way.)"],
  ];

  const modes = s.support_modes ?? [];
  const off = s.auto_off ?? [];
  const noticed = Object.entries(s.auto_support ?? {});
  function toggleMode(mode: string, on: boolean) {
    change({ support_modes: on ? [...modes.filter((m) => m !== mode), mode] : modes.filter((m) => m !== mode) });
  }
  function toggleNoticed(mode: string, on: boolean) {
    change({ auto_off: on ? off.filter((m) => m !== mode) : [...off, mode] });
  }

  return (
    <div className="wrap">
      <h1>Settings</h1>
      <p className="muted">Change anything here at any time. You don&apos;t need anyone&apos;s permission.</p>
      <div className="card">
        <label htmlFor="scale">Text size</label>
        <input
          id="scale"
          type="range"
          min={0.8}
          max={2}
          step={0.1}
          value={s.font_scale ?? 1}
          onChange={(e) => change({ font_scale: Number(e.target.value) })}
        />
        {toggles.map(([key, title, help]) => (
          <div key={key} style={{ marginTop: 12 }}>
            <label className="check">
              <input type="checkbox" checked={!!s[key]} onChange={(e) => change({ [key]: e.target.checked })} />
              {title}
            </label>
            <p className="muted" style={{ margin: "0 0 0 34px" }}>
              {help}
            </p>
          </div>
        ))}
        {me.role === "student" && (
          <>
            <label htmlFor="style">How I like things explained</label>
            <select
              id="style"
              value={s.preferred_style ?? ""}
              onChange={(e) => change({ preferred_style: e.target.value || null })}
            >
              <option value="">No preference</option>
              {Object.entries(STYLE_WORDS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </>
        )}
        {me.role === "student" && (
          <>
            <fieldset style={{ border: 0, padding: 0, margin: "16px 0 0" }}>
              <legend style={{ fontWeight: 600 }}>What SYNiq has noticed helps you</legend>
              {noticed.length === 0 ? (
                <p className="muted" style={{ margin: "4px 0" }}>
                  Nothing yet. As you practise, SYNiq notices if shorter steps, easier reading or pictures help you, and
                  tells you when it changes something.
                </p>
              ) : (
                noticed.map(([mode, info]) => (
                  <div key={mode} style={{ marginTop: 12 }}>
                    <label className="check">
                      <input type="checkbox" checked={!off.includes(mode)} onChange={(e) => toggleNoticed(mode, e.target.checked)} />
                      {NOTICED_SUPPORT[mode] ?? mode}
                    </label>
                    <p className="muted" style={{ margin: "0 0 0 34px" }}>
                      {info.reason}
                    </p>
                  </div>
                ))
              )}
            </fieldset>
            <fieldset style={{ border: 0, padding: 0, margin: "16px 0 0" }}>
              <legend style={{ fontWeight: 600 }}>Seeing, hearing and speaking</legend>
              <p className="muted" style={{ margin: "4px 0" }}>
                Your parent can set these too.
              </p>
              {CHOSEN_SUPPORT.map(({ key, me: title, help }) => (
                <div key={key} style={{ marginTop: 12 }}>
                  <label className="check">
                    <input type="checkbox" checked={modes.includes(key)} onChange={(e) => toggleMode(key, e.target.checked)} />
                    {title}
                  </label>
                  <p className="muted" style={{ margin: "0 0 0 34px" }}>
                    {help}
                  </p>
                </div>
              ))}
            </fieldset>
          </>
        )}
        <p role="status" className="muted">
          {saved}
        </p>
      </div>
    </div>
  );
}
