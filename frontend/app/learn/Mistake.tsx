"use client";

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

/**
 * The mistake is the way in: the learner's answer sits next to the right one, drawn
 * where the numbers are small, then the topic's own picture.
 */
export default function Mistake({ yours, right, picture }: { yours: string; right: string; picture?: PictureSpec | null }) {
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
      {shown && (
        <div className="mistake-picture">
          <p className="mistake-label">{t("fb.see_it")}</p>
          <Picture picture={shown} />
        </div>
      )}
    </div>
  );
}
