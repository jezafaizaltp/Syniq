"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Role, post, setToken } from "@/lib/api";
import { homeFor } from "@/lib/home";
import { useSession } from "@/lib/session";

export default function SignIn() {
  const { me, loading, refresh, t } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (me) router.replace(homeFor(me));
  }, [me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await post<{ token: string; role: Role }>("/auth/login", { email, password });
      setToken(res.token);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("signin.failed"));
    }
  }

  if (loading) return null;

  return (
    <div className="wrap signin">
      <div className="signin-hero">
        <svg className="signin-mark" viewBox="0 0 40 40" aria-hidden="true">
          <rect width="40" height="40" rx="11" fill="#a63d2a" />
          <path d="M9 29c5 0 6-6 11-6s5-8 11-8" fill="none" stroke="#fbf7ee" strokeWidth="3.4" strokeLinecap="round" />
          <circle cx="31" cy="15" r="4" fill="#f2b630" />
        </svg>
        <h1>{t("signin.title")}</h1>
        <p className="muted">{t("signin.tagline")}</p>
      </div>
      <form className="card" onSubmit={submit}>
        <label htmlFor="email">{t("signin.username")}</label>
        <input
          id="email"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">{t("signin.password")}</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && (
          <p className="feedback warn" role="alert">
            {error}
          </p>
        )}
        <div className="row" style={{ marginTop: 16 }}>
          <button type="submit" style={{ width: "100%" }}>
            {t("signin.button")}
          </button>
        </div>
      </form>
      {process.env.NEXT_PUBLIC_SHOW_DEMO !== "0" && (
        <p className="muted">
          Demo accounts: anu@demo.syniq (student), teacher@demo.syniq, parent@demo.syniq, mother@demo.syniq (family), specialist@demo.syniq, admin@demo.syniq. Password:
          syniq-demo
        </p>
      )}
      <p className="muted">{t("signin.forgot")}</p>
      <p>
        <Link href="/signup">{t("signin.new_family")}</Link>
      </p>
    </div>
  );
}
