"use client";

import type { ReactNode } from "react";
import { useSession } from "@/lib/session";
import Picture, { PictureSpec } from "./Picture";

/** A small whole number we can draw as dots, so a child can see how far off they were. */
function countable(s: string): number | null {
  const v = s.trim();
  if (!/^\d{1,2}$/.test(v)) return null;
  const n = Number(v);
  return n >= 0 && n <= 20 ? n : null;
}

function Dots({ n, label }: { n: number; label: string }) {
  return (
    <span className="mistake-dots" role="img" aria-label={label}>
      {Array.from({ length: Math.ceil(n / 5) }, (_, g) => (
        <span key={g} className="dot-group">
          {Array.from({ length: Math.min(5, n - g * 5) }, (_, i) => (
            <span key={i} className="dot" />
          ))}
        </span>
      ))}
    </span>
  );
}

const squash = (x: string) => x.replace(/\s+/g, "").replace(/[−–]/g, "-").toLowerCase();

/** Whether the picture shows an expression from the question (5+ characters with a digit), e.g. "x²-5x+6". */
export function drawsPrompt(picture: PictureSpec | null | undefined, prompt: string): boolean {
  if (!picture || !prompt) return false;
  const drawn = squash(JSON.stringify(picture));
  const mathy = (w: string) => /\d/.test(w) || /^[+\-−×÷=<>]$/.test(w) || /^[a-z][²³]?$/i.test(w);
  const runs: string[] = [];
  let run: string[] = [];
  for (const w of prompt.split(/\s+/)) {
    const clean = w.replace(/[.,;:?!]+$/, "");
    if (clean && mathy(clean)) run.push(clean);
    if (!clean || !mathy(clean) || clean !== w) {
      if (run.length) runs.push(run.join(""));
      run = [];
    }
  }
  if (run.length) runs.push(run.join(""));
  const chunks = runs.flatMap((r) => squash(r).split("=")).filter((c) => c.length >= 5 && /\d/.test(c));
  return chunks.some((c) => drawn.includes(c));
}

/**
 * The mistake is the way in: the learner's answer sits next to the right one, drawn
 * where the numbers are small. The tip about this exact mistake (children) comes next,
 * before the topic's own picture, so on a phone the personal hint isn't pushed below the fold.
 */
export default function Mistake({
  yours,
  right,
  picture,
  prompt = "",
  children,
}: {
  yours: string;
  right: string;
  prompt?: string;
  picture?: PictureSpec | null;
  children?: ReactNode;
}) {
  const { t } = useSession();
  const a = countable(yours);
  const b = countable(right);
  const draw = a !== null && b !== null;
  // On a number line, mark where the learner's answer sits and where the right one does.
  const ya = Number(yours.trim()), rb = Number(right.trim());
  const onLine =
    picture?.kind === "number_line" &&
    yours.trim() !== "" &&
    Number.isFinite(ya) &&
    Number.isFinite(rb) &&
    ya !== rb &&
    [ya, rb].every((v) => v >= picture.from! && v <= picture.to!);
  const shown: PictureSpec | null | undefined = onLine
    ? {
        ...picture!,
        jumps: [],
        points: [
          { at: ya, label: t("fb.you_said") },
          { at: rb, label: t("fb.right_answer") },
        ],
        alt: `${t("fb.you_said")} ${yours}, ${t("fb.right_answer")} ${right}. ${picture!.alt}`,
      }
    : picture;
  // The topic's picture often works a different example. Call it this question's only when it is drawn on this
  // question's own numbers: the answers marked on its number line, or an expression from the question written in
  // it. Small numbers turn up in almost any picture, so the right answer alone doesn't count.
  const aboutThis = onLine || drawsPrompt(picture, prompt);
  return (
    <div className="mistake">
      <div className="mistake-pair">
        <div className="mistake-side yours">
          <span className="mistake-label">{t("fb.you_said")}</span>
          <span className="mistake-value">{yours}</span>
          {draw && <Dots n={a} label={`${a}`} />}
        </div>
        <div className="mistake-side right">
          <span className="mistake-label">{t("fb.right_answer")}</span>
          <span className="mistake-value">{right}</span>
          {draw && <Dots n={b} label={`${b}`} />}
        </div>
      </div>
      {children}
      {shown && (
        <div className="mistake-picture">
          <p className="mistake-label">{t(aboutThis ? "fb.see_it" : "fb.see_example")}</p>
          <Picture picture={shown} />
        </div>
      )}
    </div>
  );
}
