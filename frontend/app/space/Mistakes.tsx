import type { Key } from "@/lib/i18n";

export type MistakePattern = { tag: string; text: string; status: "working_on" | "fixed"; times: number; topics: string[] };

/** Mistakes made more than once, and which are fixed. Words only: no counts, no scores. */
export default function Mistakes({
  patterns,
  t,
}: {
  patterns: MistakePattern[];
  t: (key: Key, vars?: Record<string, string | number>) => string;
}) {
  if (!patterns.length) return <p className="muted">{t("mistakes.none")}</p>;
  return (
    <ul className="mistake-list">
      {patterns.map((p) => (
        <li key={p.tag}>
          <span className={`mistake-status ${p.status === "fixed" ? "fixed" : ""}`}>
            {p.status === "fixed" ? t("mistakes.fixed") : t("mistakes.working_on")}
          </span>
          <span>{p.text}</span>
          {p.topics.length > 0 && <div className="muted">{t("mistakes.where", { topics: p.topics.join(", ") })}</div>}
        </li>
      ))}
    </ul>
  );
}
