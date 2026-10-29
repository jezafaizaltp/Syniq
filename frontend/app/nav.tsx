"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LANGS } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export default function Nav() {
  const { me, signOut, lang, setLang, t } = useSession();
  const router = useRouter();
  const other = LANGS.find((l) => l.code !== lang)!;

  return (
    <header className="nav">
      <Link href="/" className="brand">
        SYNiq
      </Link>
      {me?.role === "student" && <Link href="/learn">{t("nav.learn")}</Link>}
      {me?.role === "admin" && <Link href="/admin">{t("nav.school")}</Link>}
      {(me?.role === "teacher" || me?.role === "admin") && <Link href="/teacher">{t("nav.class")}</Link>}
      {me?.role === "guardian" && <Link href="/parent">{t("nav.children")}</Link>}
      {me && <Link href="/settings">{t("nav.settings")}</Link>}
      <button
        className="secondary"
        lang={other.code}
        aria-label={`${t("nav.language")}: ${other.name}`}
        onClick={() => setLang(other.code)}
      >
        {other.name}
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
    </header>
  );
}
