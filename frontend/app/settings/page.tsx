"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CHOSEN_SUPPORT, Settings } from "@/lib/api";
import { Key, LANGS, isLang } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { ChangePassword } from "../password";

export default function SettingsPage() {
  const { me, loading, saveSettings, lang, setLang, t } = useSession();
  const router = useRouter();
  const [saved, setSaved] = useState("");

  useEffect(() => {
    if (!loading && !me) router.replace("/");
  }, [me, loading, router]);

  if (!me) return null;
  const s = me.settings ?? {};

  async function change(patch: Settings) {
    await saveSettings(patch);
    setSaved(t("settings.saved"));
    setTimeout(() => setSaved(""), 1500);
  }

  const toggles: [keyof Settings, Key, Key][] = [
    ["high_contrast", "settings.high_contrast", "settings.high_contrast_help"],
    ["dyslexia_font", "settings.easy_text", "settings.easy_text_help"],
    ["reduced_motion", "settings.motion", "settings.motion_help"],
    ["read_aloud", "settings.read_aloud", "settings.read_aloud_help"],
    ["extra_time", "settings.extra_time", "settings.extra_time_help"],
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
      <h1>{t("settings.title")}</h1>
      <p className="muted">{t("settings.intro")}</p>
      <div className="card">
        <label htmlFor="lang">{t("settings.language")}</label>
        <select
          id="lang"
          value={lang}
          onChange={async (e) => {
            if (!isLang(e.target.value)) return;
            await setLang(e.target.value);
            setSaved(t("settings.saved"));
            setTimeout(() => setSaved(""), 1500);
          }}
        >
          {LANGS.map((l) => (
            <option key={l.code} value={l.code} lang={l.code}>
              {l.name}
            </option>
          ))}
        </select>
        <label htmlFor="scale">{t("settings.text_size")}</label>
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
              {t(title)}
            </label>
            <p className="muted" style={{ margin: "0 0 0 34px" }}>
              {t(help)}
            </p>
          </div>
        ))}
        {me.role === "student" && (
          <>
            <label htmlFor="style">{t("settings.style")}</label>
            <select
              id="style"
              value={s.preferred_style ?? ""}
              onChange={(e) => change({ preferred_style: e.target.value || null })}
            >
              <option value="">{t("settings.no_preference")}</option>
              {(["text", "visual", "step_by_step", "real_world"] as const).map((k) => (
                <option key={k} value={k}>
                  {t(`style.${k}`)}
                </option>
              ))}
            </select>
          </>
        )}
        {me.role === "student" && (
          <>
            <fieldset style={{ border: 0, padding: 0, margin: "16px 0 0" }}>
              <legend style={{ fontWeight: 600 }}>{t("settings.noticed")}</legend>
              {noticed.length === 0 ? (
                <p className="muted" style={{ margin: "4px 0" }}>
                  {t("settings.noticed_none")}
                </p>
              ) : (
                noticed.map(([mode, info]) => (
                  <div key={mode} style={{ marginTop: 12 }}>
                    <label className="check">
                      <input type="checkbox" checked={!off.includes(mode)} onChange={(e) => toggleNoticed(mode, e.target.checked)} />
                      {t(`noticed.${mode}` as Key)}
                    </label>
                    <p className="muted" style={{ margin: "0 0 0 34px" }}>
                      {info.reason}
                    </p>
                  </div>
                ))
              )}
            </fieldset>
            <fieldset style={{ border: 0, padding: 0, margin: "16px 0 0" }}>
              <legend style={{ fontWeight: 600 }}>{t("settings.senses")}</legend>
              <p className="muted" style={{ margin: "4px 0" }}>
                {t("settings.parent_too")}
              </p>
              {CHOSEN_SUPPORT.map((key) => (
                <div key={key} style={{ marginTop: 12 }}>
                  <label className="check">
                    <input type="checkbox" checked={modes.includes(key)} onChange={(e) => toggleMode(key, e.target.checked)} />
                    {t(`support.${key}.me`)}
                  </label>
                  <p className="muted" style={{ margin: "0 0 0 34px" }}>
                    {t(`support.${key}.help`)}
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
      <ChangePassword first={false} />
    </div>
  );
}
