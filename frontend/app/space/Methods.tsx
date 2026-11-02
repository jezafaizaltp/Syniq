import type { Key } from "@/lib/i18n";

/** Per subject: how often answers were right just after each way of explaining. */
export type MethodSubject = {
  subject_id: number;
  subject: string;
  methods: { style: string; right_after: number; answers_after: number }[];
  clearest: string | null;
};

type T = (key: Key, vars?: Record<string, string | number>) => string;

export function methodName(t: T, style: string): string {
  return t(`method.${style}` as Key);
}

/** What has helped lately, in words and counts. Never a score or a label, and it changes as they learn. */
export default function Methods({ subjects, t }: { subjects: MethodSubject[]; t: T }) {
  if (subjects.length === 0) return <p className="muted">{t("space.helps_none")}</p>;
  return (
    <ul className="list">
      {subjects.map((s) => (
        <li key={s.subject_id}>
          <span>
            <strong>{s.subject}</strong>
            <br />
            {s.clearest ? t("space.helps_clear", { method: methodName(t, s.clearest) }) : t("space.helps_unclear")}
            {s.methods.map((m) => (
              <span key={m.style} className="muted" style={{ display: "block" }}>
                {t("space.helps_counts", { method: methodName(t, m.style), right: m.right_after, total: m.answers_after })}
              </span>
            ))}
          </span>
        </li>
      ))}
    </ul>
  );
}
