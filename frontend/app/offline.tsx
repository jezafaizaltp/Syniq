"use client";

import { useEffect, useState } from "react";
import { useSession } from "@/lib/session";

/** Turns on offline support and tells the reader when there is no internet. */
export default function Offline() {
  const { t } = useSession();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (!offline) return null;
  return (
    <p className="feedback warn" role="status" style={{ margin: 0, borderRadius: 0, textAlign: "center" }}>
      {t("offline.banner")}
    </p>
  );
}
