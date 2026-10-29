"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, Me, Settings, api, effectiveSupport, hasToken, post, put, setApiLang, setToken } from "./api";
import { Key, Lang, isLang, translate } from "./i18n";

type SessionValue = {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => void;
  saveSettings: (patch: Settings) => Promise<void>;
  lang: Lang;
  setLang: (lang: Lang) => Promise<void>;
  t: (key: Key, vars?: Record<string, string | number>) => string;
};

/** The language chosen on this device, used before sign-in. */
function deviceLang(): Lang {
  try {
    const v = localStorage.getItem("syniq_lang");
    return isLang(v) ? v : "en";
  } catch {
    return "en";
  }
}

function applyLang(lang: Lang) {
  setApiLang(lang);
  document.documentElement.lang = lang;
  try {
    localStorage.setItem("syniq_lang", lang);
  } catch {
    /* storage unavailable: the choice lasts for this page only */
  }
}

const SessionContext = createContext<SessionValue | null>(null);

/** Mirror accessibility settings onto <html> so CSS can respond to them. */
function applySettings(s: Settings | undefined) {
  const root = document.documentElement;
  root.style.setProperty("--font-scale", String(s?.font_scale ?? 1));
  root.dataset.contrast = s?.high_contrast ? "high" : "normal";
  root.dataset.font = s?.dyslexia_font || effectiveSupport(s).includes("easy_read") ? "dyslexia" : "default";
  root.dataset.motion = s?.reduced_motion ? "reduced" : "full";
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLangState] = useState<Lang>("en");

  const refresh = useCallback(async () => {
    const local = deviceLang();
    applyLang(local);
    setLangState(local);
    if (!hasToken()) {
      setLoading(false);
      return;
    }
    try {
      let data = await api<Me>("/me");
      const saved = data.settings?.ui_language;
      if (isLang(saved) && saved !== local) {
        // The account's language wins; ask again so server words come in that language.
        applyLang(saved);
        setLangState(saved);
        data = await api<Me>("/me");
      }
      setMe(data);
      applySettings(data.settings);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setToken(null);
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signOut = () => {
    post("/auth/logout", {}).catch(() => undefined);
    setToken(null);
    setMe(null);
    applySettings(undefined);
  };

  const saveSettings = async (patch: Settings) => {
    // Apply at once so the change is felt immediately, then confirm with the server.
    const previous = me?.settings ?? {};
    const optimistic = { ...previous, ...patch };
    applySettings(optimistic);
    setMe((m) => (m ? { ...m, settings: optimistic } : m));
    try {
      const settings = await put<Settings>("/me/settings", patch);
      applySettings(settings);
      setMe((m) => (m ? { ...m, settings } : m));
    } catch (e) {
      applySettings(previous);
      setMe((m) => (m ? { ...m, settings: previous } : m));
      throw e;
    }
  };

  const setLang = async (next: Lang) => {
    applyLang(next);
    setLangState(next);
    if (me) await saveSettings({ ui_language: next });
  };

  const t = useCallback((key: Key, vars?: Record<string, string | number>) => translate(lang, key, vars), [lang]);

  return (
    <SessionContext.Provider value={{ me, loading, refresh, signOut, saveSettings, lang, setLang, t }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const v = useContext(SessionContext);
  if (!v) throw new Error("useSession outside SessionProvider");
  return v;
}

/** Read text aloud with the browser's speech engine, in Malayalam when the text is in Malayalam. */
export function speak(text: string, lang = /[\u0D00-\u0D7F]/.test(text) ? "ml-IN" : "en-IN") {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}
