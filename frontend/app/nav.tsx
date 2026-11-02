"use client";

import { useEffect } from "react";
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
  const tabs = me ? TABS[me.role] ?? [] : [];

  // Room at the bottom of the page for the phone tab bar.
  useEffect(() => {
    document.body.classList.toggle("has-tabs", tabs.length > 0);
  }, [tabs.length]);

  return (
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
        <button
          className="secondary"
          lang={other.code}
          aria-label={`${t("nav.language")}: ${other.name}`}
          onClick={() => setLang(other.code)}
        >
          {other.code === "ml" ? "മല" : "EN"}
        </button>
        {me && (
          <button
            className="secondary"
            onClick={() => {
              signOut();
              router.push("/");
            }}
          >
            {t("nav.sign_out")}
          </button>
        )}
      </div>
    </header>
  );
}
