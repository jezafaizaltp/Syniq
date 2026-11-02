"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, post, setToken } from "@/lib/api";
import { homeFor } from "@/lib/home";
import { useSession } from "@/lib/session";
import { RELATIONS } from "../family/words";

/** Start a family account. The person who signs up holds it and decides who else joins. */
export default function SignUp() {
  const { me, loading, refresh } = useSession();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [relation, setRelation] = useState("mother");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (me) router.replace(homeFor(me));
  }, [me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await post<{ token: string }>("/auth/signup", { name, email, password, relation });
      setToken(res.token);
      await refresh();
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "";
      setError(detail.includes("at least 8") ? "Use a password of at least 8 characters." : detail.includes("valid") || detail.includes("pattern") ? "Check the email address." : detail || "Couldn't create the account. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  return (
    <div className="wrap signin">
      <div className="signin-hero">
        <span className="family-hero" aria-hidden="true">
          🏡
        </span>
        <h1>Start your family account</h1>
        <p className="muted">One account for your family, from pregnancy to Class 12. Free to start.</p>
      </div>
      <form className="card" onSubmit={submit}>
        <label htmlFor="name">Your name</label>
        <input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        <label htmlFor="relation">You are the child&apos;s</label>
        <select id="relation" value={relation} onChange={(e) => setRelation(e.target.value)}>
          {Object.entries(RELATIONS).map(([value, word]) => (
            <option key={value} value={value}>
              {word}
            </option>
          ))}
        </select>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="email" autoCapitalize="none" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="password">Choose a password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          aria-describedby="password-help"
        />
        <p id="password-help" className="muted">
          At least 8 characters.
        </p>
        {error && (
          <p className="feedback warn" role="alert">
            {error}
          </p>
        )}
        <div className="row" style={{ marginTop: 8 }}>
          <button type="submit" disabled={busy} style={{ width: "100%" }}>
            Create account
          </button>
        </div>
      </form>
      <p className="muted">
        You hold the account: you add your children, choose who else in the family can see them, and can remove anyone at any time.
      </p>
      <p>
        Already have an account? <Link href="/">Sign in</Link>
      </p>
    </div>
  );
}
