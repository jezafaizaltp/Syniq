"use client";

import { useState } from "react";
import { useSession } from "@/lib/session";

/**
 * A number line and counters to work a sum out with, for learners who find it hard to hold
 * numbers in their head. Buttons only (no dragging), the state is always said in words, and
 * nothing here checks or gives away the answer: it is scrap paper that counts.
 */
export default function MathsHelper({ prompt }: { prompt: string }) {
  const { t } = useSession();
  // Big numbers in the question get a 0-100 line in tens; small ones a 0-20 line in ones.
  const biggest = Math.max(0, ...(prompt.match(/\d+/g) ?? []).map(Number).filter((n) => n < 100000));
  const max = biggest > 20 ? 100 : 20;
  const [at, setAt] = useState(0);
  const [counters, setCounters] = useState(0);
  const move = (d: number) => setAt((v) => Math.min(max, Math.max(0, v + d)));
  const ticks = Array.from({ length: max / (max === 100 ? 10 : 1) + 1 }, (_, i) => i * (max === 100 ? 10 : 1));
  const W = 600;
  const x = (v: number) => 20 + (v / max) * (W - 40);

  return (
    <div className="card maths-helper">
      <p className="muted">{t("helper.note")}</p>
      <h3>{t("helper.line")}</h3>
      <svg viewBox={`0 0 ${W} 70`} className="pic-svg" role="img" aria-label={t("helper.at", { v: at })}>
        <line x1={20} y1={30} x2={W - 20} y2={30} stroke="currentColor" strokeWidth={2} />
        {ticks.map((v) => (
          <g key={v}>
            <line x1={x(v)} y1={24} x2={x(v)} y2={36} stroke="currentColor" />
            <text x={x(v)} y={56} textAnchor="middle" fontSize={max === 100 ? 14 : 13}>
              {v}
            </text>
          </g>
        ))}
        <circle cx={x(at)} cy={30} r={9} fill="var(--accent, #c0392b)" />
      </svg>
      <p aria-live="polite">{t("helper.at", { v: at })}</p>
      <div className="row">
        <button type="button" className="secondary" onClick={() => move(-10)} aria-label={t("helper.left10")}>
          −10
        </button>
        <button type="button" className="secondary" onClick={() => move(-1)} aria-label={t("helper.left1")}>
          −1
        </button>
        <button type="button" className="secondary" onClick={() => move(1)} aria-label={t("helper.right1")}>
          +1
        </button>
        <button type="button" className="secondary" onClick={() => move(10)} aria-label={t("helper.right10")}>
          +10
        </button>
      </div>
      <h3>{t("helper.counters")}</h3>
      {/* Rows of ten, with a gap after five, so a count can be seen without counting one by one. */}
      <div className="counters" role="img" aria-label={t("helper.count", { n: counters })}>
        {Array.from({ length: Math.ceil(counters / 10) }, (_, r) => (
          <div key={r} className="counter-row">
            {Array.from({ length: Math.min(10, counters - r * 10) }, (_, i) => (
              <span key={i} className={i === 5 ? "counter gap" : "counter"} />
            ))}
          </div>
        ))}
      </div>
      <p aria-live="polite">{t("helper.count", { n: counters })}</p>
      <div className="row">
        <button type="button" className="secondary" onClick={() => setCounters((n) => Math.min(100, n + 1))}>
          {t("helper.add")}
        </button>
        <button type="button" className="secondary" onClick={() => setCounters((n) => Math.min(100, n + 10))}>
          {t("helper.add10")}
        </button>
        <button type="button" className="secondary" onClick={() => setCounters((n) => Math.max(0, n - 1))}>
          {t("helper.remove")}
        </button>
        <button type="button" className="secondary" onClick={() => setCounters(0)}>
          {t("helper.clear")}
        </button>
      </div>
    </div>
  );
}
