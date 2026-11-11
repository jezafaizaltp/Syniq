import Link from "next/link";
import type { Key } from "@/lib/i18n";

export type Achievement = { id: string; earned_on: string };
export type RewardsView =
  | { on: false }
  | {
      on: true;
      stars: number;
      stickers: { unlocked: string[]; locked: number; stars_to_next: number | null };
      achievements: Achievement[];
      practice_days: number;
    };

export const ACH_KEYS: Record<string, Key> = {
  first_secure: "ach.first_secure",
  chapter_done: "ach.chapter_done",
  first_hard_right: "ach.first_hard_right",
  pattern_fixed: "ach.pattern_fixed",
  spotted_10: "ach.spotted_10",
  back_after_break: "ach.back_after_break",
};

/** Stickers from spotting mistakes, achievements, and practice days. Mine alone, never compared. */
export default function Rewards({ view, t }: { view: RewardsView | null; t: (key: Key, vars?: Record<string, string | number>) => string }) {
  if (!view || !view.on) return null;
  const { stickers, achievements, practice_days } = view;
  return (
    <section className="card rewards" aria-labelledby="rewards">
      <h2 id="rewards">{t("rewards.title")}</h2>
      <p>{practice_days === 1 ? t("rewards.days_one") : practice_days > 1 ? t("rewards.days", { n: practice_days }) : t("rewards.days_none")}</p>

      <h3>{t("sticker.title")}</h3>
      <ul className="sticker-grid" aria-label={t("sticker.title")}>
        {stickers.unlocked.map((s, i) => (
          <li key={i} className="sticker">
            {s}
          </li>
        ))}
        {Array.from({ length: Math.min(stickers.locked, 4) }, (_, i) => (
          <li key={`l${i}`} className="sticker locked" aria-label={t("sticker.locked")}>
            ?
          </li>
        ))}
      </ul>
      <p className="muted">
        {stickers.stars_to_next == null
          ? t("sticker.all")
          : stickers.stars_to_next === 1
            ? t("sticker.next_one")
            : t("sticker.next", { n: stickers.stars_to_next })}
      </p>

      <h3>{t("ach.title")}</h3>
      {achievements.length === 0 ? (
        <p className="muted">{t("ach.none")}</p>
      ) : (
        <ul className="achievement-list">
          {achievements.map((a) => (
            <li key={a.id}>
              <span aria-hidden="true">🏅</span> {t(ACH_KEYS[a.id] ?? "ach.title")}{" "}
              <span className="muted">· {new Date(a.earned_on).toLocaleDateString()}</span>
            </li>
          ))}
        </ul>
      )}
      {achievements.length > 0 && (
        <p>
          <Link href="/space/card">{t("card.make")}</Link>
        </p>
      )}
    </section>
  );
}
