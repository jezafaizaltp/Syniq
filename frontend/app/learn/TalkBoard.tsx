"use client";

import { useState } from "react";
import { post } from "@/lib/api";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";

const NEEDS = ["help", "dont_understand", "break", "too_loud", "finished", "toilet", "upset"] as const;

/**
 * Picture buttons for learners who find it hard to speak up or ask out loud (non-speaking,
 * autistic, shy, or still learning the language). In a class, a press quietly tells the
 * teacher, like a raised hand that says what is needed. At home, it shows the need big, to
 * point at for the grown-up nearby.
 */
export default function TalkBoard({ inClass, conceptId }: { inClass: boolean; conceptId: number | null }) {
  const { t } = useSession();
  const [chosen, setChosen] = useState<string | null>(null);

  async function press(need: string) {
    setChosen(need);
    if (inClass) {
      try {
        await post("/me/help", { concept_id: conceptId, need });
      } catch {
        /* offline: the big card still shows, to point at */
      }
    }
  }

  return (
    <div className="card talk-board" aria-labelledby="talk-board-title">
      <h3 id="talk-board-title">{t("board.title")}</h3>
      <div className="talk-grid">
        {NEEDS.map((n) => (
          <button key={n} type="button" className="secondary talk-button" aria-pressed={chosen === n} onClick={() => press(n)}>
            {t(`need.${n}` as Key)}
          </button>
        ))}
      </div>
      {chosen && (
        <div className="feedback note talk-shown" role="status">
          <p>{inClass ? t("board.sent", { need: t(`need.${chosen}` as Key) }) : t("board.show")}</p>
          {!inClass && <p className="talk-big">{t(`need.${chosen}` as Key)}</p>}
          <button type="button" className="secondary" onClick={() => setChosen(null)}>
            {t("board.clear")}
          </button>
        </div>
      )}
    </div>
  );
}
