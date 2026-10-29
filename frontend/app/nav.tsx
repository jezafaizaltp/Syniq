"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";

export default function Nav() {
  const { me, signOut } = useSession();
  const router = useRouter();

  return (
    <header className="nav">
      <Link href="/" className="brand">
        SYNiq
      </Link>
      {me?.role === "student" && <Link href="/learn">Learn</Link>}
      {me?.role === "admin" && <Link href="/admin">School</Link>}
      {(me?.role === "teacher" || me?.role === "admin") && <Link href="/teacher">Class</Link>}
      {me?.role === "guardian" && <Link href="/parent">My children</Link>}
      {me && <Link href="/settings">Settings</Link>}
      {me && (
        <button
          className="secondary"
          onClick={() => {
            signOut();
            router.push("/");
          }}
        >
          Sign out
        </button>
      )}
    </header>
  );
}
