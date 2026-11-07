"use client";

import { useEffect, useMemo, useState } from "react";
import type { SpeakingDetail } from "@/lib/session";

/**
 * Text that highlights each word while SYNiq reads it aloud, so a child can follow along.
 * Screen readers get the plain text: the word spans add nothing for them.
 * Browsers that don't report word positions simply show no highlight.
 */
export default function ReadAlong({
  text,
  style,
}: {
  text: string;
  style?: React.CSSProperties;
}) {
  const [char, setChar] = useState(-1);
  // Words with their start positions; spaces kept so the text wraps as normal.
  const parts = useMemo(() => {
    const out: { word: string; start: number }[] = [];
    const re = /\S+|\s+/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) out.push({ word: m[0], start: m.index });
    return out;
  }, [text]);

  useEffect(() => {
    setChar(-1);
    function on(e: Event) {
      const d = (e as CustomEvent<SpeakingDetail>).detail;
      setChar(d.text === text ? d.char : -1);
    }
    window.addEventListener("syniq-speaking", on);
    return () => window.removeEventListener("syniq-speaking", on);
  }, [text]);

  return (
    <p className="read-along" style={style}>
      {parts.map((p, i) => {
        const now =
          char >= 0 &&
          p.word.trim() &&
          char >= p.start &&
          char < p.start + p.word.length;
        return now ? (
          <span key={i} className="word-now">
            {p.word}
          </span>
        ) : (
          <span key={i}>{p.word}</span>
        );
      })}
    </p>
  );
}
