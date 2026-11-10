"use client";

import { useSession } from "@/lib/session";

/** The official Indian Sign Language Research and Training Centre, which publishes the ISL dictionary. */
export const ISLRTC = "https://islrtc.nic.in/";

/**
 * Sign-language links for deaf learners: videos the school has added for this topic's key
 * words, and the national ISL dictionary for any other word. Links open in a new tab and
 * nothing about the student is sent with them.
 */
export default function Signs({ signs }: { signs: { word: string; url: string }[] }) {
  const { t } = useSession();
  return (
    <div className="card signs" aria-labelledby="signs-title">
      <h3 id="signs-title">
        <span aria-hidden="true">🤟</span> {t("signs.title")}
      </h3>
      {signs.length ? (
        <ul className="sign-list">
          {signs.map((s) => (
            <li key={s.url + s.word}>
              <a href={s.url} target="_blank" rel="noopener noreferrer">
                {t("signs.watch", { word: s.word })}
              </a>{" "}
              <span className="muted">{t("signs.new_tab")}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{t("signs.none")}</p>
      )}
      <p>
        <a href={ISLRTC} target="_blank" rel="noopener noreferrer">
          {t("signs.lookup")}
        </a>{" "}
        <span className="muted">{t("signs.new_tab")}</span>
      </p>
    </div>
  );
}
