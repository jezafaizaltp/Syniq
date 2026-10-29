"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Role, post, setToken } from "@/lib/api";
import { useSession } from "@/lib/session";

const HOME: Record<Role, string> = { student: "/learn", teacher: "/teacher", admin: "/admin", guardian: "/parent" };

export default function SignIn() {
  const { me, loading, refresh } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (me) router.replace(HOME[me.role]);
  }, [me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await post<{ token: string; role: Role }>("/auth/login", { email, password });
      setToken(res.token);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
    }
  }

  if (loading) return null;

  return (
    <div className="wrap">
      <h1>Welcome to SYNiq</h1>
      <p className="muted">An adaptive teacher that learns how you learn.</p>
      <form className="card" onSubmit={submit}>
        <label htmlFor="email">Username or email</label>
        <input
          id="email"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">Password</label>
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
          <button type="submit">Sign in</button>
        </div>
      </form>
      {process.env.NEXT_PUBLIC_SHOW_DEMO !== "0" && (
        <p className="muted">
          Demo accounts: anu@demo.syniq (student), teacher@demo.syniq, parent@demo.syniq, admin@demo.syniq. Password:
          syniq-demo
        </p>
      )}
      <p className="muted">Forgotten your password? Ask your school to give you a new one.</p>
    </div>
  );
}
