import Link from "next/link";
import type { Key } from "@/lib/i18n";

export type Strength =
  | { kind: "subject"; subject: string; family: string }
  | { kind: "thinking"; domain: string }
  | { kind: "explore"; area: string; next: { id: string; title: string }[] }
  | { kind: "hands_on" };
export type StrengthsView = { strengths: Strength[]; try_new: { id: string; title: string; area: string } | null };

type T = (key: Key, vars?: Record<string, string | number>) => string;

/**
 * What comes easily and what the learner loves, each with a way to grow it. Shown to the
 * learner in their own words, and to a parent with the child's name. Never a score or label.
 */
export default function Strengths({ view, t, name }: { view: StrengthsView; t: T; name?: string }) {
  const line = (s: Strength): string => {
    switch (s.kind) {
      case "subject":
        return name ? t("strengths.parent_subject", { subject: s.subject, name }) : t("strengths.subject", { subject: s.subject });
      case "thinking":
        return t("strengths.thinking", { kind: t(`thinking.${s.domain}` as Key) });
      case "explore": {
        const area = t(`explore.area.${s.area}` as Key).toLowerCase();
        return name ? t("strengths.parent_explore", { name, area }) : t("strengths.explore", { area });
      }
      case "hands_on":
        return name ? t("strengths.parent_hands_on", { name }) : t("strengths.hands_on");
    }
  };
  const grow = (s: Strength): string[] => {
    switch (s.kind) {
      case "subject":
        return [t(`grow.${s.family}` as Key), t("grow.teach")];
      case "thinking":
        return [t("grow.thinking")];
      case "explore":
        return [t(`grow.area.${s.area}` as Key)];
      case "hands_on":
        return [t("grow.hands_on")];
    }
  };

  if (!view.strengths.length) {
    return (
      <>
        <p>{t("strengths.none")}</p>
        {view.try_new && !name && <TryNew t={t} item={view.try_new} />}
      </>
    );
  }
  return (
    <>
      <ul className="strengths">
        {view.strengths.map((s, i) => (
          <li key={i}>
            <strong>{line(s)}</strong>
            <div className="muted">{t("strengths.grow")}</div>
            <ul>
              {grow(s).map((g) => (
                <li key={g}>{g}</li>
              ))}
              {s.kind === "explore" &&
                !name &&
                s.next.map((a) => (
                  <li key={a.id}>
                    <Link href={`/explore?open=${a.id}`}>{t("strengths.next_activity", { title: a.title })}</Link>
                  </li>
                ))}
            </ul>
          </li>
        ))}
      </ul>
      {view.try_new && !name && <TryNew t={t} item={view.try_new} />}
    </>
  );
}

function TryNew({ t, item }: { t: T; item: { id: string; title: string } }) {
  return (
    <p>
      <Link href={`/explore?open=${item.id}`}>{t("strengths.try_new", { title: item.title })}</Link>
    </p>
  );
}
