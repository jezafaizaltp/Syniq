"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";

const IDLE_MS = 20 * 60 * 1000;
const WARN_MS = 60 * 1000;

/**
 * Lab computers are shared: a student who walks away is signed out after 20 minutes without
 * use, with a minute's warning first, so the next class can't open their account.
 */
export default function IdleSignOut() {
  const { me, signOut, t } = useSession();
  const router = useRouter();
  const last = useRef(Date.now());
  const [warning, setWarning] = useState(false);
  const [signedOut, setSignedOut] = useState(false);
  const active = me?.role === "student";
  const leave = useRef(() => {});
  leave.current = () => {
    signOut();
    router.push("/");
  };

  useEffect(() => {
    if (!active) return;
    const seen = () => {
      last.current = Date.now();
    };
    const events = ["pointerdown", "keydown", "scroll", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, seen, { passive: true }));
    const timer = window.setInterval(() => {
      const idle = Date.now() - last.current;
      if (idle >= IDLE_MS) {
        setWarning(false);
        setSignedOut(true);
        leave.current();
      } else {
        setWarning(idle >= IDLE_MS - WARN_MS);
      }
    }, 5000);
    return () => {
      events.forEach((e) => window.removeEventListener(e, seen));
      window.clearInterval(timer);
    };
  }, [active]);

  if (signedOut && !me) {
    return (
      <div className="wrap">
        <p className="feedback note" role="status">
          {t("idle.signed_out")}{" "}
          <button className="secondary" onClick={() => setSignedOut(false)}>
            {t("idle.ok")}
          </button>
        </p>
      </div>
    );
  }
  if (!active || !warning) return null;
  return (
    <div className="idle-warning" role="alertdialog" aria-live="assertive" aria-label={t("idle.warning")}>
      <p>{t("idle.warning")}</p>
      <button
        onClick={() => {
          last.current = Date.now();
          setWarning(false);
        }}
      >
        {t("idle.here")}
      </button>
    </div>
  );
}
