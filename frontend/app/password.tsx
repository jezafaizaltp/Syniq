"use client";

import { useState } from "react";
import { ApiError, post, setToken } from "@/lib/api";
import { useSession } from "@/lib/session";

/** Change your password. Shown in place of everything else on first sign-in with a temporary password. */
export function ChangePassword({ first }: { first: boolean }) {
  const { refresh, t } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [message, setMessage] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== again) {
      setMessage(t("pw.mismatch"));
      return;
    }
    try {
      const r = await post<{ token: string }>("/me/password", { current, new: next });
      setToken(r.token);
      setCurrent("");
      setNext("");
      setAgain("");
      setMessage(t("pw.saved"));
      await refresh();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : t("pw.failed"));
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>{first ? t("pw.choose") : t("pw.change")}</h2>
      {first && <p className="muted">{t("pw.first_note")}</p>}
      <label htmlFor="pw-current">{first ? t("pw.from_school") : t("pw.current")}</label>
      <input id="pw-current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
      <label htmlFor="pw-new">{t("pw.new")}</label>
      <input id="pw-new" type="password" autoComplete="new-password" minLength={8} value={next} onChange={(e) => setNext(e.target.value)} required />
      <label htmlFor="pw-again">{t("pw.again")}</label>
      <input id="pw-again" type="password" autoComplete="new-password" minLength={8} value={again} onChange={(e) => setAgain(e.target.value)} required />
      {message && (
        <p className="feedback warn" role="status">
          {message}
        </p>
      )}
      <div className="row" style={{ marginTop: 16 }}>
        <button type="submit">{t("pw.save")}</button>
      </div>
    </form>
  );
}

export default function PasswordGate({ children }: { children: React.ReactNode }) {
  const { me } = useSession();
  if (me?.must_change_password) {
    return (
      <div className="wrap">
        <ChangePassword first />
      </div>
    );
  }
  return <>{children}</>;
}
