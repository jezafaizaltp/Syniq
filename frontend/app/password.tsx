"use client";

import { useState } from "react";
import { ApiError, post, setToken } from "@/lib/api";
import { useSession } from "@/lib/session";

/** Change your password. Shown in place of everything else on first sign-in with a temporary password. */
export function ChangePassword({ first }: { first: boolean }) {
  const { refresh } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [message, setMessage] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== again) {
      setMessage("The two new passwords are different. Please type them again.");
      return;
    }
    try {
      const r = await post<{ token: string }>("/me/password", { current, new: next });
      setToken(r.token);
      setCurrent("");
      setNext("");
      setAgain("");
      setMessage("Your new password is saved.");
      await refresh();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not change the password");
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>{first ? "Choose your own password" : "Change password"}</h2>
      {first && <p className="muted">You signed in with a password from your school. Please choose your own to keep your account safe.</p>}
      <label htmlFor="pw-current">{first ? "Password from your school" : "Current password"}</label>
      <input id="pw-current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
      <label htmlFor="pw-new">New password (at least 8 letters or numbers)</label>
      <input id="pw-new" type="password" autoComplete="new-password" minLength={8} value={next} onChange={(e) => setNext(e.target.value)} required />
      <label htmlFor="pw-again">New password again</label>
      <input id="pw-again" type="password" autoComplete="new-password" minLength={8} value={again} onChange={(e) => setAgain(e.target.value)} required />
      {message && (
        <p className="feedback warn" role="status">
          {message}
        </p>
      )}
      <div className="row" style={{ marginTop: 16 }}>
        <button type="submit">Save password</button>
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
