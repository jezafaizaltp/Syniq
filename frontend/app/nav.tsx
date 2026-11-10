"use client";

import { useEffect, useState } from "react";
import BeforeYouGo, { loadToday, type Today } from "./BeforeYouGo";
import IdleSignOut from "./IdleSignOut";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { Key } from "@/lib/i18n";
import { LANGS } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import type { Role } from "@/lib/api";

type Tab = { href: string; label: Key; icon: string };

const TABS: Record<Role, Tab[]> = {
  student: [
    { href: "/learn", label: "nav.learn", icon: "📚" },
    { href: "/space", label: "nav.space", icon: "🌱" },
    { href: "/explore", label: "nav.explore", icon: "🧭" },
    { href: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  guardian: [
    { href: "/parent", label: "nav.children", icon: "👨‍👩‍👧" },
    { href: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  specialist: [
    { href: "/specialist", label: "nav.children", icon: "🤝" },
    { href: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  teacher: [
    { href: "/teacher", label: "nav.class", icon: "🏫" },
    { href: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  admin: [
    { href: "/admin", label: "nav.school", icon: "🏛️" },
    { href: "/teacher", label: "nav.class", icon: "🏫" },
    { href: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
};

export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="11" fill="#a63d2a" />
      <path d="M9 29c5 0 6-6 11-6s5-8 11-8" fill="none" stroke="#fbf7ee" strokeWidth="3.4" strokeLinecap="round" />
      <circle cx="31" cy="15" r="4" fill="#f2b630" />
    </svg>
  );
}

export default function Nav() {
  const { me, signOut, lang, setLang, t } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const other = LANGS.find((l) => l.code !== lang)!;
  // The quick switch is for the Kerala pilot: signed-out screens, Kerala students and school
  // parents. CBSE families are English first and pick Hindi or Malayalam in Settings. Anyone
  // already in another language always keeps a way back to English.
  const showLanguage =
    !me ||
    lang !== "en" ||
    (me.role === "student" && me.class?.board === "kerala_scert") ||
    (me.role === "guardian" && !me.family);
  const [today, setToday] = useState<Today | null>(null);
  const leave = () => {
    setToday(null);
    signOut();
    router.push("/");
  };
  let tabs = me ? TABS[me.role] ?? [] : [];
  if (me?.role === "guardian" && me.family) tabs = [{ href: "/family", label: "nav.family", icon: "🏡" }, ...tabs];

  // Room at the bottom of the page for the phone tab bar.
  useEffect(() => {
    document.body.classList.toggle("has-tabs", tabs.length > 0);
  }, [tabs.length]);

  return (
    <>
    <header className="nav">
      <Link href="/" className="brand" aria-label="SYNiq">
        <BrandMark />
        <span className="brand-name">
          SYN<em>iq</em>
        </span>
      </Link>
      {tabs.length > 0 && (
        <nav className="tabs" aria-label="Main">
          {tabs.map((tab) => (
            <Link key={tab.href} href={tab.href} aria-current={pathname?.startsWith(tab.href) ? "page" : undefined}>
              <span className="tab-icon" aria-hidden="true">
                {tab.icon}
              </span>
              {t(tab.label)}
            </Link>
          ))}
        </nav>
      )}
      <div className="nav-actions">
        {showLanguage && (
          <button
            className="secondary"
            lang={other.code}
            aria-label={`${t("nav.language")}: ${other.name}`}
            onClick={() => setLang(other.code)}
          >
            {other.code === "ml" ? "മല" : "EN"}
          </button>
        )}
        {me && (
          <button
            className="secondary"
            onClick={async () => {
              // A student hears what they did today first, unless they did nothing yet.
              const day = me.role === "student" ? await loadToday() : null;
              if (day && day.answered > 0) setToday(day);
              else leave();
            }}
          >
            {t("nav.sign_out")}
          </button>
        )}
      </div>
    </header>
      {today && <BeforeYouGo today={today} onSignOut={leave} onStay={() => setToday(null)} />}
      <IdleSignOut />
    </>
  );
}
