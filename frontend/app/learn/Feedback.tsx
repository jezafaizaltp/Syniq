"use client";

import { useEffect, useState } from "react";
import { speak, useSession } from "@/lib/session";

type Block =
  | { type: "text"; text: string }
  | { type: "steps"; steps: string[]; plain?: boolean }
  | { type: "visual"; rows: { label: string; symbols: string; alt: string }[]; caption: string }
  | { type: "challenge"; prompt: string; answer: string };

export type AdaptiveResponse = {
  correct: boolean;
  mode: string | null;
  headline: string;
  blocks: Block[];
  why: string;
  suggest_tutor?: boolean;
  one_at_a_time: boolean;
  speak: boolean;
  script: string;
  adapted?: { mode: string; message: string }[];
};

/** The response to an answer, shown in the way that suits this student. */
export default function Feedback({ r, readAloud, tutorOn }: { r: AdaptiveResponse; readAloud: boolean; tutorOn: boolean }) {
  const { t } = useSession();
  // In focus mode, one piece at a time.
  const [shown, setShown] = useState(r.one_at_a_time ? 1 : r.blocks.length);

  useEffect(() => {
    if (r.speak || readAloud) speak(r.script);
  }, [r, readAloud]);

  const blocks = r.blocks.slice(0, shown);
  return (
    <div className={`feedback ${r.correct ? "good" : "warn"}`} role="status">
      <strong>{r.headline}</strong>
      {blocks.map((b, i) => (
        <FeedbackBlock key={i} b={b} />
      ))}
      {shown < r.blocks.length && (
        <div className="row" style={{ marginTop: 8 }}>
          <button className="secondary" onClick={() => setShown(shown + 1)}>
            {t("fb.show_more", { n: r.blocks.length - shown })}
          </button>
        </div>
      )}
      {r.suggest_tutor && tutorOn && <p>{t("fb.tricky")}</p>}
      {r.why && <p className="muted">{t("fb.why", { why: r.why })}</p>}
      {r.adapted?.map((a) => (
        <p key={a.mode} className="adapted">
          ✨ {a.message}
        </p>
      ))}
    </div>
  );
}

function FeedbackBlock({ b }: { b: Block }) {
  if (b.type === "text") return <p>{b.text}</p>;
  if (b.type === "steps") {
    const List = b.plain ? "ul" : "ol";
    return (
      <List className={b.plain ? "plain-lines" : undefined}>
        {b.steps.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </List>
    );
  }
  if (b.type === "visual") {
    return (
      <figure className="visual">
        {b.rows.map((row, i) => (
          <div key={i} className="visual-row">
            <span className="visual-label">{row.label}</span>
            <span role="img" aria-label={row.alt} className="visual-symbols">
              {row.symbols}
            </span>
          </div>
        ))}
        <figcaption>{b.caption}</figcaption>
      </figure>
    );
  }
  return <Challenge prompt={b.prompt} answer={b.answer} />;
}

/** A practice question to try right away. It is not marked or saved. */
function Challenge({ prompt, answer }: { prompt: string; answer: string }) {
  const { t } = useSession();
  const [value, setValue] = useState("");
  const [result, setResult] = useState<boolean | null>(null);
  return (
    <form
      className="challenge"
      onSubmit={(e) => {
        e.preventDefault();
        setResult(value.trim() === answer);
      }}
    >
      <label htmlFor="challenge">{prompt}</label>
      <div className="row">
        <input id="challenge" inputMode="numeric" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 120 }} />
        <button type="submit" disabled={!value.trim()}>
          {t("learn.check")}
        </button>
      </div>
      {result === true && <p>{t("fb.yes")}</p>}
      {result === false && <p>{t("fb.not_yet")}</p>}
    </form>
  );
}
