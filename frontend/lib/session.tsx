"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, Me, Settings, api, hasToken, put, setToken } from "./api";

type SessionValue = {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => void;
  saveSettings: (patch: Settings) => Promise<void>;
};

const SessionContext = createContext<SessionValue | null>(null);

/** Mirror accessibility settings onto <html> so CSS can respond to them. */
function applySettings(s: Settings | undefined) {
  const root = document.documentElement;
  root.style.setProperty("--font-scale", String(s?.font_scale ?? 1));
  root.dataset.contrast = s?.high_contrast ? "high" : "normal";
  root.dataset.font = s?.dyslexia_font || s?.support_modes?.includes("easy_read") ? "dyslexia" : "default";
  root.dataset.motion = s?.reduced_motion ? "reduced" : "full";
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!hasToken()) {
      setLoading(false);
      return;
    }
    try {
      const data = await api<Me>("/me");
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

  return (
    <SessionContext.Provider value={{ me, loading, refresh, signOut, saveSettings }}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const v = useContext(SessionContext);
  if (!v) throw new Error("useSession outside SessionProvider");
  return v;
}

/** Read text aloud with the browser's speech engine, if the student wants it. */
export function speak(text: string, lang = "en-IN") {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}
