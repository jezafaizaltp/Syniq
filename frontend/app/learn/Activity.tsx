"use client";

import { useMemo, useState } from "react";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { evaluate, parseFormula, wanted } from "./formula";

/**
 * Hands-on activities (backend/app/activities.py checks the format).
 * Everything is changed with buttons, never by dragging, so a switch, a keyboard or a screen
 * reader works too; the state is always said in words in a live region.
 *
 * A wrong try is coached, never just marked wrong (the mistake principle), in three parts:
 *   where   the picture marks where the try went wrong (outlined squares, an arrow, a gap)
 *   effect  what that mistake causes ("3 rows of 4 is 12 squares, not 18"); a goal's own
 *           `mistakes` (written for the topic's common slips) say it best, so they win
 *   fix     a nudge in the right direction that leaves the thinking to the child
 * The help grows with each wrong try at the same goal: try 1 is direction and a question,
 * try 2 adds the goal's hint, and from try 3 the goal is drawn dashed beside the child's
 * own try. Even then the child moves it there themselves.
 */

/** From this many wrong tries at one goal, the goal is drawn next to the child's try. */
const REVEAL = 3;

type Want = number | [number, number];
type Mistake = { when: Record<string, Want>; say: string };
type Goal = {
  prompt: string;
  hint?: string;
  mistakes?: Mistake[];
  target?: number;
  num?: number;
  den?: number;
  equivalent?: boolean;
  area?: number;
  perimeter?: number;
  width?: number;
  height?: number;
  degrees?: number;
  kind?: string;
  n?: number;
  find?: "all" | number;
  value?: number;
  zone?: string;
  count?: number;
  want?: Record<string, Want>;
  x?: number;
  y?: number;
  m?: number;
  c?: number;
  through?: [number, number][];
};
type Input = { name: string; label: string; min: number; max: number; step: number; start?: number; unit?: string };
type Output = { name: string; label: string; expr: string; unit?: string; places?: number };
type Zone = { from: number; to: number; label: string; says?: string };
export type ActivitySpec = {
  type: string;
  prompt: string;
  goals?: Goal[];
  min?: number;
  max?: number;
  step?: number;
  start?: number;
  denominator?: number;
  max_parts?: number;
  max_side?: number;
  left?: string[];
  bins?: string[];
  items?: { label: string; bin: string; why?: string; clue?: string }[];
  steps?: string[];
  reasons?: Record<string, string>;
  categories?: { label: string; value: number }[];
  show?: "tally" | "table";
  unit?: string;
  orientation?: "horizontal" | "vertical";
  zones?: Zone[];
  rule?: string;
  max_step?: number;
  inputs?: Input[];
  outputs?: Output[];
  mode?: "point" | "line";
  range?: [number, number];
  x_label?: string;
  y_label?: string;
  m_step?: number;
};

type T = (key: Key, vars?: Record<string, string | number>) => string;
/**
 * What a panel reports on Check. A wrong try says where it went wrong, what that causes and a
 * nudge; `vals` are the try's numbers, matched against the goal's `mistakes`.
 */
type Verdict = { right: boolean; where?: string; effect?: string | string[]; nudge?: string; vals?: Record<string, number>; note?: string };

function said(goal: Goal, vals?: Record<string, number>): string | undefined {
  if (!vals) return undefined;
  return goal.mistakes?.find((m) => Object.entries(m.when).every(([k, w]) => vals[k] !== undefined && wanted(vals[k], w)))?.say;
}

export default function Activity({ spec, onDone }: { spec: ActivitySpec; onDone?: () => void }) {
  const { t } = useSession();
  const goals = spec.goals?.length ? spec.goals : [{ prompt: "" }];
  const [g, setG] = useState(0);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [fresh, setFresh] = useState(false); // false once the child changes something after a Check
  const [tries, setTries] = useState(0); // wrong tries at this goal
  const [finished, setFinished] = useState(false);
  const [round, setRound] = useState(0); // remounts the panel for "Play again"
  const goal = goals[g];

  function report(v: Verdict) {
    setVerdict(v);
    setFresh(true);
    if (!v.right) setTries((n) => n + 1);
    else if (g === goals.length - 1) {
      setFinished(true);
      onDone?.();
    }
  }

  function changed() {
    if (verdict?.right) setVerdict(null);
    setFresh(false);
  }

  function nextGoal() {
    setVerdict(null);
    setTries(0);
    setG(g + 1);
  }

  const Panel = PANELS[spec.type];
  if (!Panel) return null;
  const effect = verdict && !verdict.right ? (said(goal, verdict.vals) ?? verdict.effect) : undefined;
  const fix = verdict && !verdict.right ? (tries === 2 && goal.hint ? goal.hint : verdict.nudge) : undefined;
  return (
    <section className="activity" aria-labelledby="activity-title">
      <h3 id="activity-title">
        <span aria-hidden="true">🧪 </span>
        {t("act.title")}
      </h3>
      <p>{spec.prompt}</p>
      {goal.prompt && (
        <p className="activity-goal">
          {goals.length > 1 && <span className="muted">{t("act.goal", { n: g + 1, total: goals.length })} </span>}
          <strong>{goal.prompt}</strong>
        </p>
      )}
      <Panel
        // A number line keeps its marker from goal to goal, so a run of goals is one journey
        // ("start at 3, take away 8, now add 7"); every other panel starts fresh for each goal.
        key={`${round}-${spec.type === "number_line" ? 0 : g}`}
        spec={spec}
        goal={goal}
        t={t}
        missed={!!verdict && !verdict.right && fresh}
        tries={tries}
        onCheck={report}
        onChange={changed}
      />
      <div aria-live="polite">
        {verdict?.right && (
          <div className="feedback good">
            <p style={{ margin: 0 }}>{finished ? t("act.all_done") : t("act.right")}</p>
            {verdict.note && <p style={{ margin: "6px 0 0" }}>{verdict.note}</p>}
          </div>
        )}
        {verdict && !verdict.right && (
          <div className={`feedback warn act-coach${fresh ? "" : " stale"}`}>
            <p className="act-coach-head">{fresh ? t("act.not_yet") : t("act.changed")}</p>
            {verdict.where && (
              <p>
                <span aria-hidden="true">👀 </span>
                <strong>{t("act.where_h")}</strong> {verdict.where}
              </p>
            )}
            {effect && (
              <div className="act-coach-part">
                <span aria-hidden="true">⚡ </span>
                <strong>{t("act.effect_h")}</strong>{" "}
                {Array.isArray(effect) ? (
                  <ul>
                    {effect.map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                ) : (
                  effect
                )}
              </div>
            )}
            {fix && (
              <p>
                <span aria-hidden="true">🧭 </span>
                <strong>{t("act.fix_h")}</strong> {fix}
              </p>
            )}
          </div>
        )}
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        {verdict?.right && !finished && <button onClick={nextGoal}>{t("act.next_goal")}</button>}
        {finished && (
          <button
            className="secondary"
            onClick={() => {
              setFinished(false);
              setVerdict(null);
              setTries(0);
              setG(0);
              setRound(round + 1);
            }}
          >
            {t("act.again_all")}
          </button>
        )}
      </div>
    </section>
  );
}

/**
 * `missed`: the last Check was wrong and nothing has changed since, so the picture marks the
 * mistake. `tries`: wrong tries at this goal so far; the try being checked now is tries + 1.
 */
type PanelProps = { spec: ActivitySpec; goal: Goal; t: T; missed: boolean; tries: number; onCheck: (v: Verdict) => void; onChange: () => void };

function CheckButton({ onClick, t, disabled }: { onClick: () => void; t: T; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled}>
      {t("act.check")}
    </button>
  );
}

/** Numbers the way a child reads them: whole numbers with separators, fractions when asked, no float noise. */
function fmt(v: number, step = 1, denominator?: number): string {
  if (denominator) {
    const n = Math.round(v * denominator);
    if (n % denominator === 0) return String(n / denominator);
    return `${n < 0 ? "−" : ""}${Math.abs(n)}/${denominator}`;
  }
  const places = Math.max(0, (String(step).split(".")[1] ?? "").length);
  const s = Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: places, maximumFractionDigits: places });
  return v < 0 ? `−${s}` : s;
}

/** A result the way a child reads it: at most `places` decimals, no trailing zeros. */
function show(v: number, places = 2): string {
  if (!Number.isFinite(v)) return "—";
  const r = Math.round(v * 10 ** places) / 10 ** places;
  const s = Math.abs(r).toLocaleString("en-IN", { maximumFractionDigits: places });
  return r < 0 ? `−${s}` : s;
}

const near = (a: number, b: number) => Math.abs(a - b) < 1e-9;

/** The text for a try's nudge: direction first, the goal drawn beside it from try REVEAL. */
function ladder(t: T, attempt: number, nudge: string, reveal?: string): string {
  return attempt >= REVEAL ? (reveal ?? t("act.reveal")) : nudge;
}

// --- Number line -------------------------------------------------------------------------

function NumberLine({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const lo = spec.min!, hi = spec.max!, step = spec.step!;
  const [v, setV] = useState(spec.start ?? lo);
  const say = (x: number) => fmt(x, step, spec.denominator);
  const move = (d: number) => {
    setV((x) => Math.min(hi, Math.max(lo, Math.round((x + d * step) / step) * step)));
    onChange();
  };
  const ticks = Math.round((hi - lo) / step);
  const X = (x: number) => 20 + ((x - lo) / (hi - lo)) * 320;
  const labelEvery = Math.max(1, Math.ceil(ticks / 10));
  const target = goal.target!;
  const dir = v < target ? 1 : -1;
  function check() {
    if (near(v, target)) return onCheck({ right: true });
    const attempt = tries + 1;
    const away = Math.round(Math.abs(target - v) / step);
    onCheck({
      right: false,
      vals: { v },
      where: t(v > target ? "act.nl.where_big" : "act.nl.where_small", { v: say(v) }),
      nudge: ladder(t, attempt, attempt === 1 ? t(v > target ? "act.nl.go_left" : "act.nl.go_right") : t("act.nl.away", { k: away })),
    });
  }
  // The arrow points the way to go from the marker, without showing how far.
  const ax = Math.min(330, Math.max(30, X(v)));
  return (
    <>
      <svg viewBox="0 0 360 90" className="activity-svg number-line-svg" role="img" aria-label={t("act.nl.at", { v: say(v) })}>
        <line x1={20} y1={40} x2={340} y2={40} className="act-axis" />
        {Array.from({ length: ticks + 1 }, (_, i) => {
          const x = lo + i * step;
          return (
            <g key={i}>
              <line x1={X(x)} y1={34} x2={X(x)} y2={46} className="act-axis" />
              {i % labelEvery === 0 && (
                <text x={X(x)} y={68} textAnchor="middle" className="act-label">
                  {say(x)}
                </text>
              )}
            </g>
          );
        })}
        {tries >= REVEAL && <circle cx={X(target)} cy={40} r={9} className="act-ghost" />}
        <path d={`M ${X(v)} 32 l -10 -18 h 20 z`} className={`act-marker${missed ? " wrong" : ""}`} />
        {missed && (
          <g className="act-arrow">
            <line x1={ax + dir * 14} y1={22} x2={ax + dir * 34} y2={22} />
            <path d={`M ${ax + dir * 42} 22 l ${-dir * 9} -6 v 12 z`} />
          </g>
        )}
      </svg>
      <p className="activity-state" role="status">{t("act.nl.at", { v: say(v) })}</p>
      <div className="row">
        <button className="secondary" onClick={() => move(-1)} disabled={v <= lo}>
          ← {t("act.left")}
        </button>
        <button className="secondary" onClick={() => move(1)} disabled={v >= hi}>
          {t("act.right_dir")} →
        </button>
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Fraction bar ------------------------------------------------------------------------

function FractionBar({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const most = spec.max_parts ?? 12;
  const [parts, setParts] = useState(2);
  const [shaded, setShaded] = useState<boolean[]>([false, false]);
  const count = shaded.filter(Boolean).length;
  const num = goal.num!, den = goal.den!;
  function cut(n: number) {
    setParts(n);
    setShaded(Array(n).fill(false));
    onChange();
  }
  const want = `${num}/${den}`;
  function check() {
    const same = count * den === num * parts;
    const exact = goal.equivalent === false;
    if (exact ? parts === den && count === num : same) return onCheck({ right: true });
    const attempt = tries + 1;
    const cmp = same ? "act.cmp.same" : count * den < num * parts ? "act.cmp.less" : "act.cmp.more";
    // Can these parts make the goal at all? If not, the size of the parts is the mistake.
    const fits = exact ? parts === den : (num * parts) % den === 0;
    const nudge = !fits
      ? exact && same
        ? t("act.fb.same_amount", { parts: den })
        : t("act.fb.cut_q", { want })
      : t(cmp === "act.cmp.less" ? "act.fb.shade_more" : "act.fb.shade_fewer");
    onCheck({
      right: false,
      vals: { shaded: count, parts },
      where: t("act.fb.where", { shaded: count, parts }),
      effect: t("act.fb.effect", { parts, shaded: count, cmp: t(cmp as Key), want }),
      nudge: ladder(t, attempt, nudge),
    });
  }
  return (
    <>
      {tries >= REVEAL && <p className="frac-caption">{t("act.yours_label")}</p>}
      <div className="frac-bar" role="group" aria-label={t("act.fb.state", { parts, shaded: count })}>
        {shaded.map((on, i) => (
          <button
            key={i}
            className={`frac-part${on ? " on" : ""}${missed ? " wrong" : ""}`}
            aria-pressed={on}
            aria-label={t("act.fb.part", { n: i + 1 })}
            onClick={() => {
              setShaded(shaded.map((s, j) => (j === i ? !s : s)));
              onChange();
            }}
          >
            {missed && (
              <span className="frac-unit" aria-hidden="true">
                1/{parts}
              </span>
            )}
          </button>
        ))}
      </div>
      {tries >= REVEAL && (
        <>
          <p className="frac-caption">{t("act.goal_label", { want })}</p>
          <div className="frac-bar ghost" aria-hidden="true">
            {Array.from({ length: den }, (_, i) => (
              <span key={i} className={`frac-part${i < num ? " on" : ""}`} />
            ))}
          </div>
        </>
      )}
      <p className="activity-state" role="status">{t("act.fb.state", { parts, shaded: count })}</p>
      <div className="row">
        <button className="secondary" onClick={() => cut(parts - 1)} disabled={parts <= 1}>
          {t("act.fb.fewer")}
        </button>
        <button className="secondary" onClick={() => cut(parts + 1)} disabled={parts >= most}>
          {t("act.fb.more")}
        </button>
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Rectangle (area and perimeter) ---------------------------------------------------------

type RectKey = "width" | "height" | "area" | "perimeter";

function Rectangle({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const most = spec.max_side ?? 10;
  const [w, setW] = useState(2);
  const [h, setH] = useState(2);
  const [shown, setShown] = useState<RectKey[]>([]); // what the last wrong try got wrong
  const area = w * h, per = 2 * (w + h);
  const state = t("act.rect.state", { w, h, a: area, p: per });
  const keys = (["width", "height", "area", "perimeter"] as const).filter((k) => goal[k] !== undefined);
  const now: Record<RectKey, number> = { width: w, height: h, area, perimeter: per };
  const word = (k: RectKey) => t(`act.rect.${k}` as Key);
  // A rectangle that meets the goal, closest to the child's, drawn dashed from try REVEAL.
  const goalRect = useMemo(() => {
    let best: [number, number] | null = null;
    for (let a = 1; a <= most; a++)
      for (let b = 1; b <= most; b++) {
        const m: Record<RectKey, number> = { width: a, height: b, area: a * b, perimeter: 2 * (a + b) };
        if (keys.every((k) => m[k] === goal[k]) && (!best || Math.abs(a - w) + Math.abs(b - h) < Math.abs(best[0] - w) + Math.abs(best[1] - h))) best = [a, b];
      }
    return best;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goal, most, tries]);
  function check() {
    const bad = keys.filter((k) => now[k] !== goal[k]);
    if (!bad.length) return onCheck({ right: true });
    setShown(bad);
    const attempt = tries + 1;
    const effect: string[] = [];
    if (bad.includes("area")) effect.push(t("act.rect.area_effect", { w, h, a: area }));
    if (bad.includes("perimeter")) effect.push(t("act.rect.per_effect", { w, h, p: per }));
    let nudge: string;
    if (bad.includes("area")) nudge = t(area < goal.area! ? "act.rect.area_more" : "act.rect.area_less", { w, h });
    else if (bad.includes("perimeter"))
      nudge = keys.includes("area") ? t("act.rect.same_area") : t(per < goal.perimeter! ? "act.rect.per_more" : "act.rect.per_less");
    else if (bad.includes("width")) nudge = t(w < goal.width! ? "act.rect.go_wider" : "act.rect.go_narrower");
    else nudge = t(h < goal.height! ? "act.rect.go_taller" : "act.rect.go_shorter");
    onCheck({
      right: false,
      vals: now,
      where: bad.map((k) => t("act.rect.where", { what: word(k), yours: now[k], want: goal[k]! })).join(" "),
      effect,
      nudge: ladder(t, attempt, nudge),
    });
  }
  const set = (f: (n: number) => void, n: number) => {
    f(Math.min(most, Math.max(1, n)));
    onChange();
  };
  const countArea = missed && shown.includes("area");
  const walk = missed && shown.includes("perimeter");
  const ghost = tries >= REVEAL ? goalRect : null;
  return (
    <>
      <div className="rect-wrap">
        <span className="rect-side top" aria-hidden="true" style={{ width: `${(w / most) * 100}%` }}>
          {w}
        </span>
        <div className="rect-grid" style={{ gridTemplateColumns: `repeat(${most}, 1fr)` }} role="img" aria-label={state}>
          {Array.from({ length: most * most }, (_, i) => {
            const c = i % most, r = Math.floor(i / most);
            const on = c < w && r < h;
            const edge = on && walk ? ` edge${r === 0 ? " t" : ""}${r === h - 1 ? " b" : ""}${c === 0 ? " l" : ""}${c === w - 1 ? " r" : ""}` : "";
            const inGoal = ghost && c < ghost[0] && r < ghost[1] ? " goal" : "";
            return (
              <span key={i} className={`${on ? "on" : ""}${edge}${inGoal}`}>
                {countArea && on ? r * w + c + 1 : ""}
              </span>
            );
          })}
        </div>
        <span className="rect-side left" aria-hidden="true" style={{ height: `${(h / most) * 100}%` }}>
          {h}
        </span>
      </div>
      <p className="activity-state" role="status">{state}</p>
      <div className="row">
        <button className="secondary" onClick={() => set(setW, w - 1)} disabled={w <= 1}>
          {t("act.rect.narrower")}
        </button>
        <button className="secondary" onClick={() => set(setW, w + 1)} disabled={w >= most}>
          {t("act.rect.wider")}
        </button>
        <button className="secondary" onClick={() => set(setH, h - 1)} disabled={h <= 1}>
          {t("act.rect.shorter")}
        </button>
        <button className="secondary" onClick={() => set(setH, h + 1)} disabled={h >= most}>
          {t("act.rect.taller")}
        </button>
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Mirror (line symmetry) ----------------------------------------------------------------

function Mirror({ spec, t, missed, tries, onCheck, onChange }: PanelProps) {
  const left = spec.left!;
  const half = left[0].length;
  const [right, setRight] = useState<boolean[][]>(left.map(() => Array(half).fill(false)));
  // The right half, read outwards from the mirror, must match the left read inwards.
  const want = (r: number, c: number) => left[r][half - 1 - c] === "#";
  const isWrong = (r: number, c: number) => right[r][c] !== want(r, c);
  const wrong = right.flatMap((row, r) => row.map((_, c) => isWrong(r, c))).filter(Boolean).length;
  const filled = right.flat().filter(Boolean).length;
  // From the second wrong try, each wrong square's partner on the left gets a ring.
  const partner = (r: number, lc: number) => tries >= 2 && isWrong(r, half - 1 - lc);
  function check() {
    if (wrong === 0) return onCheck({ right: true });
    const attempt = tries + 1;
    onCheck({
      right: false,
      where: t("act.mirror.where", { n: wrong }),
      effect: t("act.mirror.effect"),
      nudge: ladder(t, attempt, attempt === 1 ? t("act.mirror.nudge") : t("act.mirror.nudge2"), t("act.mirror.reveal")),
    });
  }
  return (
    <>
      <div className="mirror" style={{ "--cells": half * 2 } as React.CSSProperties} role="group" aria-label={t("act.mirror.state", { n: filled })}>
        {left.map((row, r) => (
          <div key={r} className="mirror-row">
            {[...row].map((ch, c) => (
              <span key={c} className={`mirror-cell${ch === "#" ? " on" : ""}${partner(r, c) ? " partner" : ""}`} aria-hidden="true" />
            ))}
            <span className="mirror-line" aria-hidden="true" />
            {right[r].map((on, c) => (
              <button
                key={c}
                className={`mirror-cell${on ? " on" : ""}${missed && isWrong(r, c) ? " miss" : ""}${tries >= REVEAL && want(r, c) && !on ? " should" : ""}`}
                aria-pressed={on}
                aria-label={t("act.mirror.cell", { r: r + 1, c: c + 1 })}
                onClick={() => {
                  setRight(right.map((rw, i) => (i === r ? rw.map((x, j) => (j === c ? !x : x)) : rw)));
                  onChange();
                }}
              />
            ))}
          </div>
        ))}
      </div>
      <p className="sr-only">{t("act.mirror.left_says", { rows: left.map((row) => [...row].map((x) => (x === "#" ? "■" : "□")).join("")).join(", ") })}</p>
      <p className="activity-state" role="status">{t("act.mirror.state", { n: filled })}</p>
      <div className="row">
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Angle -------------------------------------------------------------------------------

function angleKind(d: number): string {
  if (d < 90) return "acute";
  if (d === 90) return "right";
  if (d < 180) return "obtuse";
  if (d === 180) return "straight";
  if (d < 360) return "reflex";
  return "full";
}
/** Each kind's range, and an angle well inside it to draw as the goal. */
const KIND_RANGE: Record<string, [number, number, number]> = {
  acute: [5, 85, 45],
  right: [90, 90, 90],
  obtuse: [95, 175, 135],
  straight: [180, 180, 180],
  reflex: [185, 355, 270],
};

function Angle({ goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const [d, setD] = useState(30);
  const kindWord = (k: string) => t(`act.kind.${k}` as Key);
  const state = t("act.angle.state", { d, kind: kindWord(angleKind(d)) });
  const cx = 110, cy = 110, R = 90;
  const end = (deg: number, r = R) => [cx + r * Math.cos((deg * Math.PI) / 180), cy - r * Math.sin((deg * Math.PI) / 180)];
  const [ex, ey] = end(d);
  const arcR = 30;
  const [ax, ay] = end(d, arcR);
  const turn = (n: number) => {
    setD((x) => Math.min(360, Math.max(5, x + n)));
    onChange();
  };
  const goalDeg = goal.degrees ?? KIND_RANGE[goal.kind!]?.[2] ?? 90;
  function check() {
    const attempt = tries + 1;
    if (goal.degrees !== undefined) {
      if (d === goal.degrees) return onCheck({ right: true });
      const small = d < goal.degrees;
      return onCheck({
        right: false,
        vals: { degrees: d },
        where: t(small ? "act.angle.where_small" : "act.angle.where_big", { d }),
        effect: t("act.angle.kind_is", { d, kind: kindWord(angleKind(d)) }),
        nudge: ladder(t, attempt, attempt === 1 ? `${t(small ? "act.angle.open" : "act.angle.close")} ${t("act.angle.bench")}` : t("act.angle.off", { k: Math.abs(goal.degrees - d) })),
      });
    }
    if (angleKind(d) === goal.kind) return onCheck({ right: true });
    const [lo] = KIND_RANGE[goal.kind!];
    onCheck({
      right: false,
      vals: { degrees: d },
      where: t("act.angle.where_kind", { d, kind: kindWord(angleKind(d)) }),
      effect: t(`act.def.${goal.kind}` as Key),
      nudge: ladder(t, attempt, `${t(d < lo ? "act.angle.open" : "act.angle.close")} ${t("act.angle.bench")}`),
    });
  }
  const [gx, gy] = end(goalDeg);
  const [bx, by] = end(90);
  return (
    <>
      <svg viewBox="0 0 220 220" className="activity-svg angle-svg" role="img" aria-label={state}>
        <line x1={cx} y1={cy} x2={cx + R} y2={cy} className="act-arm" />
        {(missed || tries >= REVEAL) && (
          <g className="act-bench" aria-hidden="true">
            <line x1={cx} y1={cy} x2={bx} y2={by} />
            <path d={`M ${cx + 12} ${cy} v -12 h -12`} />
            <text x={bx + 4} y={by + 12} className="act-label small">
              90°
            </text>
          </g>
        )}
        {tries >= REVEAL && <line x1={cx} y1={cy} x2={gx} y2={gy} className="act-arm goal" />}
        <line x1={cx} y1={cy} x2={ex} y2={ey} className={`act-arm moving${missed ? " wrong" : ""}`} />
        {d < 360 && <path d={`M ${cx + arcR} ${cy} A ${arcR} ${arcR} 0 ${d > 180 ? 1 : 0} 0 ${ax} ${ay}`} className="act-arc" />}
        <circle cx={cx} cy={cy} r={4} className="act-marker" />
        <text x={cx + 40} y={cy - 12} className="act-label">
          {d}°
        </text>
      </svg>
      <p className="activity-state" role="status">{state}</p>
      <div className="row">
        <button className="secondary" onClick={() => turn(-15)}>−15°</button>
        <button className="secondary" onClick={() => turn(-5)}>−5°</button>
        <button className="secondary" onClick={() => turn(5)}>+5°</button>
        <button className="secondary" onClick={() => turn(15)}>+15°</button>
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Sort ---------------------------------------------------------------------------------

function shuffled<X>(xs: X[], seed: string): X[] {
  // Stable for this activity, so the order doesn't jump about while the child works.
  let h = 0;
  for (const ch of seed) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const out = [...xs];
  for (let i = out.length - 1; i > 0; i--) {
    h = (h * 1103515245 + 12345) >>> 0;
    const j = h % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function Sort({ spec, t, missed, tries, onCheck, onChange }: PanelProps) {
  const items = useMemo(() => shuffled(spec.items!, spec.prompt), [spec]);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const allChosen = items.every((it) => choice[it.label]);
  const wrong = items.filter((it) => choice[it.label] && choice[it.label] !== it.bin);
  function check() {
    if (!wrong.length) return onCheck({ right: true });
    const attempt = tries + 1;
    // First a question that makes the child look again; the reason itself from the second try.
    const why = (it: (typeof items)[number]) => {
      const ask = t("act.sort.ask", { label: it.label, yours: choice[it.label] });
      if (attempt === 1) return it.clue ? `${it.label}: ${it.clue}` : ask;
      return it.why ? `${it.label}: ${it.why}` : it.clue ? `${it.label}: ${it.clue}` : ask;
    };
    onCheck({
      right: false,
      where: t("act.sort.where", { n: wrong.length, total: items.length }),
      effect: wrong.map(why),
      nudge: ladder(t, attempt, t("act.sort.nudge"), t("act.sort.reveal")),
    });
  }
  return (
    <>
      <ul className="sort-list">
        {items.map((it) => {
          const off = choice[it.label] !== undefined && choice[it.label] !== it.bin;
          return (
            <li key={it.label} className={missed && off ? "miss" : ""}>
              <span className="sort-item">
                {missed && off && <span aria-hidden="true">✗ </span>}
                {it.label}
              </span>
              <span className="row" role="group" aria-label={it.label}>
                {spec.bins!.map((b) => (
                  <button
                    key={b}
                    className={`secondary sort-bin${tries >= REVEAL && off && b === it.bin ? " should" : ""}`}
                    aria-pressed={choice[it.label] === b}
                    onClick={() => {
                      setChoice({ ...choice, [it.label]: b });
                      onChange();
                    }}
                  >
                    {b}
                  </button>
                ))}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="row">
        <CheckButton t={t} onClick={check} disabled={!allChosen} />
      </div>
    </>
  );
}

// --- Order --------------------------------------------------------------------------------

function Order({ spec, t, missed, tries, onCheck, onChange }: PanelProps) {
  const steps = spec.steps!;
  const pool = useMemo(() => shuffled(steps, spec.prompt), [steps, spec.prompt]);
  const [mine, setMine] = useState<string[]>([]);
  const at = mine.findIndex((s, i) => s !== steps[i]);
  function check() {
    if (at < 0) return onCheck({ right: true });
    const attempt = tries + 1;
    const early = mine[at];
    // The prefix before `at` is right, so the step put at `at` belongs later: it came too early.
    const effect = [t("act.order.too_early", { step: early })];
    if (attempt >= 2 && spec.reasons?.[early]) effect.push(spec.reasons[early]);
    onCheck({
      right: false,
      where: at === 0 ? t("act.order.where_first") : t("act.order.where", { k: at, n: at + 1 }),
      effect,
      nudge: ladder(t, attempt, t("act.order.nudge", { n: at + 1 }), t("act.order.reveal", { n: at + 1, right: steps[at] })),
    });
  }
  return (
    <>
      <p className="muted" style={{ margin: "4px 0" }}>
        {t("act.order.tap")}
      </p>
      <div className="order-pool">
        {pool.map((s) => (
          <button
            key={s}
            className="secondary"
            disabled={mine.includes(s)}
            onClick={() => {
              setMine([...mine, s]);
              onChange();
            }}
          >
            {s}
          </button>
        ))}
      </div>
      <h4 style={{ margin: "12px 0 4px" }}>{t("act.order.yours")}</h4>
      <ol className="order-mine">
        {mine.map((s, i) => (
          <li key={s} className={missed ? (i < at ? "ok" : i === at ? "miss" : "after") : ""}>
            {missed && i < at && <span aria-hidden="true">✓ </span>}
            {missed && i === at && <span aria-hidden="true">✗ </span>}
            {s}
          </li>
        ))}
      </ol>
      <div className="row">
        <button
          className="secondary"
          onClick={() => {
            setMine(mine.slice(0, -1));
            onChange();
          }}
          disabled={!mine.length}
        >
          {t("act.undo")}
        </button>
        {missed && at >= 0 && (
          <button
            className="secondary"
            onClick={() => {
              setMine(mine.slice(0, at));
              onChange();
            }}
          >
            {t("act.order.back_to", { n: at + 1 })}
          </button>
        )}
        <CheckButton t={t} onClick={check} disabled={mine.length < steps.length} />
      </div>
    </>
  );
}

// --- Bar graph ----------------------------------------------------------------------------

function tally(n: number): string {
  return "卌 ".repeat(Math.floor(n / 5)) + "|".repeat(n % 5);
}

function Bars({ spec, t, missed, tries, onCheck, onChange }: PanelProps) {
  const cats = spec.categories!;
  const most = spec.max ?? 10;
  const [vals, setVals] = useState<number[]>(cats.map(() => 0));
  function set(i: number, d: number) {
    setVals(vals.map((v, j) => (j === i ? Math.min(most, Math.max(0, v + d)) : v)));
    onChange();
  }
  function check() {
    const bad = cats.map((c, i) => ({ c, v: vals[i] })).filter(({ c, v }) => c.value !== v);
    if (!bad.length) return onCheck({ right: true });
    const attempt = tries + 1;
    onCheck({
      right: false,
      where: t("act.bars.where", { n: bad.length }),
      effect: bad.map(({ c, v }) => t(v < c.value ? "act.bars.effect_low" : "act.bars.effect_high", { label: c.label, v })),
      nudge: ladder(t, attempt, t(spec.show === "table" ? "act.bars.nudge_table" : "act.bars.nudge_tally")),
    });
  }
  return (
    <>
      <table className="act-table">
        <tbody>
          {cats.map((c) => (
            <tr key={c.label}>
              <th scope="row">{c.label}</th>
              <td>
                {spec.show === "table" ? (
                  c.value
                ) : (
                  <>
                    <span aria-hidden="true">{tally(c.value)}</span>
                    <span className="sr-only">{t("act.bars.tally", { n: c.value })}</span>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="act-bars" role="img" aria-label={cats.map((c, i) => `${c.label} ${vals[i]}`).join(", ")}>
        {cats.map((c, i) => (
          <div key={c.label} className={`act-bar-col${missed && vals[i] !== c.value ? " miss" : ""}`}>
            <span className="act-bar-num">{vals[i]}</span>
            <span className="act-bar" style={{ height: `${(vals[i] / most) * 100}%` }} />
            {tries >= REVEAL && vals[i] !== c.value && <span className="act-bar-ghost" style={{ bottom: `${(c.value / most) * 100}%` }} />}
            <span className="act-bar-label">{c.label}</span>
          </div>
        ))}
      </div>
      {cats.map((c, i) => (
        <div key={c.label} className="row act-bar-controls">
          <span style={{ minWidth: "6em" }}>{c.label}</span>
          <button className="secondary" onClick={() => set(i, -1)} aria-label={t("act.bars.less", { label: c.label })} disabled={!vals[i]}>
            −
          </button>
          <button className="secondary" onClick={() => set(i, 1)} aria-label={t("act.bars.more", { label: c.label })} disabled={vals[i] >= most}>
            +
          </button>
        </div>
      ))}
      <div className="row">
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Array (factors) ----------------------------------------------------------------------

function ArrayPanel({ goal, t, tries, onCheck, onChange }: PanelProps) {
  const n = goal.n!;
  const [rows, setRows] = useState(1);
  const [found, setFound] = useState<number[]>([]);
  const cols = Math.ceil(n / rows);
  const full = n % rows === 0;
  const divisors = Array.from({ length: n }, (_, i) => i + 1).filter((r) => n % r === 0);
  const state = full ? t("act.arr.full", { r: rows, c: n / rows, n }) : t("act.arr.left", { r: rows, c: Math.floor(n / rows), left: n % rows });
  function check() {
    const attempt = tries + 1;
    if (goal.find !== undefined && goal.find !== "all") {
      if (rows === goal.find) return onCheck({ right: true });
      return onCheck({
        right: false,
        vals: { rows },
        where: full ? t("act.arr.where_full", { r: rows, c: n / rows }) : t("act.arr.where_left", { r: rows, left: n % rows }),
        effect: full ? t("act.arr.effect_full", { r: rows, c: n / rows, n }) : t("act.arr.effect_left", { r: rows, n }),
        nudge: ladder(t, attempt, t(rows < goal.find ? "act.arr.go_more" : "act.arr.go_fewer"), t("act.arr.reveal_rows", { r: goal.find })),
      });
    }
    const missing = divisors.filter((d) => !found.includes(d));
    if (!missing.length) return onCheck({ right: true, note: t("act.arr.factors", { n, list: divisors.join(", ") }) });
    onCheck({
      right: false,
      where: t("act.arr.where_all", { k: found.length, total: divisors.length }),
      effect: t("act.arr.effect_all"),
      nudge: ladder(t, attempt, attempt === 1 ? t("act.arr.nudge_all", { n }) : t("act.arr.nudge_pairs"), t("act.arr.reveal_all", { list: missing.join(", ") })),
    });
  }
  return (
    <>
      <div className="act-array" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1.4em))` }} role="img" aria-label={state}>
        {Array.from({ length: n }, (_, i) => (
          <span key={i} className={!full && i >= rows * Math.floor(n / rows) ? "left" : ""} />
        ))}
      </div>
      <p className="activity-state" role="status">{state}</p>
      <div className="row">
        <button
          className="secondary"
          onClick={() => {
            setRows(Math.max(1, rows - 1));
            onChange();
          }}
          disabled={rows <= 1}
        >
          {t("act.arr.fewer")}
        </button>
        <button
          className="secondary"
          onClick={() => {
            setRows(Math.min(n, rows + 1));
            onChange();
          }}
          disabled={rows >= n}
        >
          {t("act.arr.more")}
        </button>
        {(goal.find ?? "all") === "all" && (
          <button
            className="secondary"
            disabled={!full || found.includes(rows)}
            onClick={() => {
              setFound([...found, rows].sort((a, b) => a - b));
              onChange();
            }}
          >
            {t("act.arr.keep")}
          </button>
        )}
        <CheckButton t={t} onClick={check} />
      </div>
      {found.length > 0 && <p className="muted">{t("act.arr.found", { list: found.map((r) => `${r} × ${n / r}`).join(", ") })}</p>}
    </>
  );
}

// --- Scale (ruler, thermometer) -------------------------------------------------------------

function Scale({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const lo = spec.min!, hi = spec.max!, step = spec.step!;
  const [v, setV] = useState(spec.start ?? lo);
  const zones = spec.zones ?? [];
  const zoneOf = (x: number) => zones.find((z) => x >= z.from && (x < z.to || (x === hi && z.to === hi)));
  const say = (x: number) => `${fmt(x, step)} ${spec.unit}`;
  const z = zoneOf(v)?.label;
  const state = z ? t("act.scale.state_zone", { v: say(v), zone: z }) : t("act.scale.state", { v: say(v) });
  const move = (k: number) => {
    setV((x) => Math.min(hi, Math.max(lo, Math.round((x + k * step) / step) * step)));
    onChange();
  };
  const vertical = spec.orientation === "vertical";
  const frac = (x: number) => (x - lo) / (hi - lo);
  const big = (hi - lo) / step >= 40 ? 10 : 5; // a bigger jump, so long scales need few presses
  const goalZone = zones.find((zn) => zn.label === goal.zone);
  function check() {
    const attempt = tries + 1;
    const here = zoneOf(v);
    if (goal.value !== undefined) {
      if (near(v, goal.value)) return onCheck({ right: true });
      const low = v < goal.value;
      return onCheck({
        right: false,
        vals: { v },
        where: t(low ? "act.scale.where_low" : "act.scale.where_high", { v: say(v) }),
        effect: here?.says ? `${here.label}: ${here.says}` : undefined,
        nudge: ladder(t, attempt, attempt === 1 ? t(low ? "act.scale.higher" : "act.scale.lower") : t("act.scale.away", { k: say(Math.abs(goal.value - v)) })),
      });
    }
    if (here?.label === goal.zone) return onCheck({ right: true });
    const low = v < goalZone!.from;
    onCheck({
      right: false,
      vals: { v },
      where: here ? t("act.scale.where_zone", { v: say(v), zone: here.label }) : t("act.scale.state", { v: say(v) }),
      effect: here?.says ? `${here.label}: ${here.says}` : undefined,
      nudge: ladder(t, attempt, `${t(low ? "act.scale.higher" : "act.scale.lower")} ${t("act.scale.watch")}`),
    });
  }
  // Round numbers along the scale (every 1, 2, 5, 10, 20, ...), like a real ruler or thermometer.
  const markStep = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000, 5000].find((m) => (hi - lo) / m <= 15) ?? hi - lo;
  const marks: number[] = [];
  for (let m = Math.ceil(lo / markStep - 1e-9) * markStep; m <= hi + 1e-9; m += markStep) marks.push(Math.round(m * 1000) / 1000);
  return (
    <>
      <div className={`act-scale ${vertical ? "vertical" : "horizontal"}`} role="img" aria-label={state}>
        <div className="act-scale-track">
          {zones.map((zn) => (
            <span
              key={zn.label}
              className={`act-zone${tries >= REVEAL && zn === goalZone ? " should" : ""}`}
              style={vertical ? { bottom: `${frac(zn.from) * 100}%`, height: `${(frac(zn.to) - frac(zn.from)) * 100}%` } : { left: `${frac(zn.from) * 100}%`, width: `${(frac(zn.to) - frac(zn.from)) * 100}%` }}
            >
              <span className="act-zone-label">{zn.label}</span>
            </span>
          ))}
          <span className={`act-fill${missed ? " wrong" : ""}`} style={vertical ? { height: `${frac(v) * 100}%` } : { width: `${frac(v) * 100}%` }} />
          {tries >= REVEAL && goal.value !== undefined && (
            <span className="act-scale-ghost" style={vertical ? { bottom: `${frac(goal.value) * 100}%` } : { left: `${frac(goal.value) * 100}%` }} />
          )}
          {marks.map((m, i) => (
            <span key={i} className="act-scale-mark" style={vertical ? { bottom: `${frac(m) * 100}%` } : { left: `${frac(m) * 100}%` }}>
              {fmt(m, markStep >= 1 ? 1 : markStep)}
            </span>
          ))}
        </div>
      </div>
      <p className="activity-state" role="status">{state}</p>
      <div className="row">
        <button className="secondary" onClick={() => move(-big)} disabled={v <= lo}>
          −{fmt(big * step, step)}
        </button>
        <button className="secondary" onClick={() => move(-1)} disabled={v <= lo}>
          −{fmt(step, step)}
        </button>
        <button className="secondary" onClick={() => move(1)} disabled={v >= hi}>
          +{fmt(step, step)}
        </button>
        <button className="secondary" onClick={() => move(big)} disabled={v >= hi}>
          +{fmt(big * step, step)}
        </button>
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Growing pattern ---------------------------------------------------------------------

const RULES: Record<string, (n: number) => number> = {
  square: (n) => n * n,
  triangle: (n) => (n * (n + 1)) / 2,
  odd: (n) => 2 * n - 1,
  even: (n) => 2 * n,
  double: (n) => 2 ** (n - 1),
};

/** Dot positions for step n, so the shape of the pattern is visible, not just the count. `added`: new at this step. */
function dots(rule: string, n: number): { x: number; y: number; added: boolean }[] {
  const out: { x: number; y: number; added: boolean }[] = [];
  if (rule === "square") for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) out.push({ x, y, added: Math.max(x, y) === n - 1 });
  else if (rule === "triangle") for (let y = 0; y < n; y++) for (let x = 0; x <= y; x++) out.push({ x: x + (n - 1 - y) / 2, y, added: y === n - 1 });
  else if (rule === "odd") {
    for (let x = 0; x < n; x++) out.push({ x, y: n - 1, added: x === n - 1 });
    for (let y = 0; y < n - 1; y++) out.push({ x: 0, y, added: y === 0 });
  } else {
    const count = RULES[rule](n);
    const before = n > 1 ? RULES[rule](n - 1) : 0;
    const per = rule === "even" ? n : 8;
    for (let i = 0; i < count; i++) out.push({ x: rule === "even" ? i % 2 === 0 ? i / 2 : (i - 1) / 2 : i % per, y: rule === "even" ? i % 2 : Math.floor(i / per), added: rule === "even" ? i >= count - 2 : i >= before });
  }
  if (n === 1) out.forEach((p) => (p.added = false));
  return out;
}

function Pattern({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const rule = spec.rule!;
  const most = spec.max_step ?? 8;
  const [s, setS] = useState(1);
  const count = RULES[rule](s);
  const pts = dots(rule, s);
  const size = Math.max(...pts.map((p) => Math.max(p.x, p.y))) + 1;
  const state = t("act.pat.state", { s, n: count });
  const grow = (k: number) => {
    setS(Math.min(most, Math.max(1, s + k)));
    onChange();
  };
  const goalStep = Array.from({ length: most }, (_, i) => i + 1).find((k) => RULES[rule](k) === goal.count) ?? 1;
  function check() {
    if (count === goal.count) return onCheck({ right: true });
    const attempt = tries + 1;
    const few = count < goal.count!;
    onCheck({
      right: false,
      vals: { step: s, count },
      where: t(few ? "act.pat.where_few" : "act.pat.where_many", { s, n: count }),
      effect: s > 1 ? t("act.pat.effect", { p: s - 1, s, d: count - RULES[rule](s - 1) }) : undefined,
      nudge: ladder(t, attempt, `${t(few ? "act.pat.more" : "act.pat.fewer")} ${t("act.pat.q")}`, t("act.pat.reveal", { k: goalStep })),
    });
  }
  return (
    <>
      <svg viewBox={`-1 -1 ${size + 1} ${size + 1}`} className="activity-svg pattern-svg" role="img" aria-label={state}>
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={0.32} className={`act-dot ${p.added ? "layer-1" : "layer-0"}`} />
        ))}
      </svg>
      <p className="activity-state" role="status">{state}</p>
      {missed && s > 1 && <p className="muted">{t("act.pat.key")}</p>}
      <div className="row">
        <button className="secondary" onClick={() => grow(-1)} disabled={s <= 1}>
          {t("act.pat.shrink")}
        </button>
        <button className="secondary" onClick={() => grow(1)} disabled={s >= most}>
          {t("act.pat.grow")}
        </button>
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Formula: change the numbers, watch the results -----------------------------------------

const valuesOf = (i: Input) => Array.from({ length: Math.round((i.max - i.min) / i.step) + 1 }, (_, k) => Math.round((i.min + k * i.step) * 1e9) / 1e9);
/** How far a value is from what a goal wants, as a share of the goal's size (0 = met). */
function gap(v: number, w: Want): number {
  if (!Number.isFinite(v)) return Infinity;
  const [a, b] = Array.isArray(w) ? w : [w, w];
  const d = v < a ? a - v : v > b ? v - b : 0;
  return d / (Math.abs((a + b) / 2) + 1);
}

/** A gauge for one wanted value: the goal as a green band, the try as a mark, the gap between in warm red. */
function Meter({ v, w, label }: { v: number; w: Want; label: string }) {
  const [a, b] = Array.isArray(w) ? w : [w, w];
  const lo0 = Math.min(v, a), hi0 = Math.max(v, b);
  const pad = (hi0 - lo0 || Math.abs(a) || 1) * 0.25;
  const lo = lo0 - pad, hi = hi0 + pad;
  const X = (x: number) => 10 + ((x - lo) / (hi - lo)) * 280;
  return (
    <svg viewBox="0 0 300 50" className="act-meter" role="img" aria-label={label}>
      <line x1={10} y1={17} x2={290} y2={17} className="act-meter-track" />
      <rect x={X(a) - 3} y={7} width={Math.max(6, X(b) - X(a) + 6)} height={20} rx={4} className="act-meter-goal" />
      <line x1={X(v)} y1={17} x2={v < a ? X(a) - 3 : X(b) + 3} y2={17} className="act-meter-gap" />
      <circle cx={X(v)} cy={17} r={7} className="act-meter-you" />
      <text x={X(v)} y={44} textAnchor="middle" className="act-label small">
        {show(v)}
      </text>
      <text x={(X(a) + X(b)) / 2} y={44} textAnchor="middle" className="act-label small act-meter-goal-num">
        {Array.isArray(w) ? `${show(a)}–${show(b)}` : show(a)}
      </text>
    </svg>
  );
}

function Formula({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const inputs = spec.inputs!;
  const outputs = useMemo(() => spec.outputs!.map((o) => ({ ...o, tree: parseFormula(o.expr) })), [spec.outputs]);
  const [vals, setVals] = useState<Record<string, number>>(Object.fromEntries(inputs.map((i) => [i.name, i.start ?? i.min])));
  const run = (ins: Record<string, number>) => {
    const env: Record<string, number> = { ...ins };
    for (const o of outputs) env[o.name] = evaluate(o.tree, env);
    return env;
  };
  const env = run(vals);
  const unitOf = (name: string) => inputs.find((i) => i.name === name)?.unit ?? outputs.find((o) => o.name === name)?.unit ?? "";
  const labelOf = (name: string) => inputs.find((i) => i.name === name)?.label ?? outputs.find((o) => o.name === name)?.label ?? name;
  const placesOf = (name: string) => outputs.find((o) => o.name === name)?.places ?? 2;
  const unit = (name: string) => (unitOf(name) ? ` ${unitOf(name)}` : "");
  const say = (name: string, v: number) => `${labelOf(name)} = ${show(v, placesOf(name))}${unit(name)}`;
  const want = goal.want ?? {};
  const bad = Object.entries(want).filter(([k, w]) => !wanted(env[k], w));
  function move(i: Input, k: number) {
    setVals({ ...vals, [i.name]: Math.min(i.max, Math.max(i.min, Math.round((vals[i.name] + k * i.step) / i.step) * i.step)) });
    onChange();
  }
  const total = (e: Record<string, number>) => Object.entries(want).reduce((s, [k, w]) => s + gap(e[k], w), 0);
  /** The one-step change that brings the try closest to the goal: a direction, not an answer. */
  function bestMove(): { input: Input; up: boolean; hurts: boolean } | null {
    const base = total(env);
    let best: { input: Input; up: boolean; hurts: boolean; score: number } | null = null;
    for (const i of inputs) {
      for (const up of [true, false]) {
        const x = Math.round((vals[i.name] + (up ? i.step : -i.step)) * 1e9) / 1e9;
        if (x < i.min - 1e-9 || x > i.max + 1e-9) continue;
        const e = run({ ...vals, [i.name]: x });
        const score = total(e);
        const hurts = Object.entries(want).some(([k, w]) => gap(e[k], w) > gap(env[k], w) + 1e-12);
        if (score < base - 1e-12 && (!best || score < best.score)) best = { input: i, up, hurts, score };
      }
    }
    return best;
  }
  /** One way to meet the goal, as close to the try as possible, so a reveal changes the fewest numbers. */
  function nearestAnswer(): Record<string, number> | null {
    const grids = inputs.map(valuesOf);
    if (grids.reduce((n, g) => n * g.length, 1) > 300_000) return null;
    let best: Record<string, number> | null = null, bestD = Infinity;
    const idx = grids.map(() => 0);
    for (;;) {
      const ins = Object.fromEntries(inputs.map((i, k) => [i.name, grids[k][idx[k]]]));
      const e = run(ins);
      if (Object.entries(want).every(([k, w]) => wanted(e[k], w))) {
        const d = inputs.reduce((s, i) => s + Math.abs(ins[i.name] - vals[i.name]) / i.step, 0);
        if (d < bestD) (best = ins), (bestD = d);
      }
      let k = 0;
      while (k < idx.length && ++idx[k] >= grids[k].length) idx[k++] = 0;
      if (k === idx.length) return best;
    }
  }
  function check() {
    if (!bad.length) return onCheck({ right: true });
    const attempt = tries + 1;
    const where = bad.map(([k, w]) => {
      const v = env[k];
      const [a, b] = Array.isArray(w) ? w : [w, w];
      const low = v < a;
      if (Array.isArray(w)) return t(low ? "act.f.where_below" : "act.f.where_above", { what: say(k, v), lo: show(a, placesOf(k)), hi: show(b, placesOf(k)) });
      return t(low ? "act.f.where_low" : "act.f.where_high", { what: say(k, v), by: `${show(Math.abs(v - (low ? a : b)), placesOf(k))}${unit(k)}` });
    });
    const outBad = bad.map(([k]) => k).filter((k) => outputs.some((o) => o.name === k));
    const effect = outBad.length
      ? t("act.f.effect", { ins: inputs.map((i) => say(i.name, vals[i.name])).join(", "), out: say(outBad[0], env[outBad[0]]) })
      : undefined;
    let nudge: string;
    const step = bestMove();
    if (!step) nudge = t("act.f.stuck");
    else {
      nudge = t(step.up ? "act.f.push_up" : "act.f.push_down", { label: step.input.label, out: labelOf(bad[0][0]) });
      if (step.hurts) nudge += ` ${t("act.f.balance")}`;
    }
    let reveal: string | undefined;
    if (attempt >= REVEAL) {
      const ans = nearestAnswer();
      const off = ans && inputs.filter((i) => !near(ans[i.name], vals[i.name]));
      if (ans && off?.length) {
        const i = off.reduce((a, b) => (Math.abs(ans[b.name] - vals[b.name]) / b.step > Math.abs(ans[a.name] - vals[a.name]) / a.step ? b : a));
        reveal = off.length > 1 ? t("act.f.reveal", { label: i.label, v: `${show(ans[i.name], 4)}${unit(i.name)}` }) : t("act.f.reveal_last", { label: i.label, v: `${show(ans[i.name], 4)}${unit(i.name)}` });
      }
    }
    onCheck({ right: false, vals: env, where: where.join(" "), effect, nudge: ladder(t, attempt, nudge, reveal ?? nudge) });
  }
  const state = [...inputs.map((i) => say(i.name, vals[i.name])), ...outputs.map((o) => say(o.name, env[o.name]))].join(". ");
  const big = (i: Input) => ((i.max - i.min) / i.step >= 40 ? 10 : 0);
  return (
    <>
      <div className="formula-inputs">
        {inputs.map((i) => (
          <div key={i.name} className={`formula-input${missed && bad.some(([k]) => k === i.name) ? " miss" : ""}`} role="group" aria-label={i.label}>
            <span className="formula-name">{i.label}</span>
            <span className="formula-value">
              {show(vals[i.name], 4)}
              {unit(i.name)}
            </span>
            <span className="row formula-buttons">
              {big(i) > 0 && (
                <button className="secondary" onClick={() => move(i, -big(i))} disabled={vals[i.name] <= i.min} aria-label={t("act.f.down_more", { label: i.label })}>
                  −−
                </button>
              )}
              <button className="secondary" onClick={() => move(i, -1)} disabled={vals[i.name] <= i.min} aria-label={t("act.f.down", { label: i.label })}>
                −
              </button>
              <button className="secondary" onClick={() => move(i, 1)} disabled={vals[i.name] >= i.max} aria-label={t("act.f.up", { label: i.label })}>
                +
              </button>
              {big(i) > 0 && (
                <button className="secondary" onClick={() => move(i, big(i))} disabled={vals[i.name] >= i.max} aria-label={t("act.f.up_more", { label: i.label })}>
                  ++
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
      <dl className="formula-outputs">
        {outputs.map((o) => {
          const w = want[o.name];
          const off = missed && w !== undefined && !wanted(env[o.name], w);
          return (
            <div key={o.name} className={off ? "miss" : ""}>
              <dt>{o.label}</dt>
              <dd>
                {show(env[o.name], o.places ?? 2)}
                {unit(o.name)}
              </dd>
              {off && Number.isFinite(env[o.name]) && (
                <dd className="act-meter-dd">
                  <Meter v={env[o.name]} w={w} label={t("act.f.meter", { what: say(o.name, env[o.name]) })} />
                </dd>
              )}
            </div>
          );
        })}
      </dl>
      {missed && <p className="muted act-meter-key">{t("act.f.meter_key")}</p>}
      <p className="sr-only" role="status">
        {state}
      </p>
      <div className="row">
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

// --- Graph: a point or a line on a grid -----------------------------------------------------

function Graph({ spec, goal, t, missed, tries, onCheck, onChange }: PanelProps) {
  const [lo, hi] = spec.range ?? [-6, 6];
  const mStep = spec.m_step ?? 0.5;
  const line = spec.mode === "line";
  const [a, setA] = useState(line ? 1 : 0); // slope, or x
  const [b, setB] = useState(0); // c, or y
  const S = 240 / (hi - lo);
  const X = (x: number) => 20 + (x - lo) * S;
  const Y = (y: number) => 20 + (hi - y) * S;
  const fmtLine = (m: number, c: number) => {
    const mt = m === 0 ? "" : m === 1 ? "x" : m === -1 ? "−x" : `${show(m)}x`;
    const ct = c === 0 ? (m === 0 ? "0" : "") : `${mt ? (c > 0 ? " + " : " − ") : c < 0 ? "−" : ""}${Math.abs(c)}`;
    return `y = ${mt}${ct}`;
  };
  const state = line ? t("act.g.line", { eq: fmtLine(a, b) }) : t("act.g.point", { x: show(a), y: show(b) });
  const through = goal.through ?? [];
  const hits = ([px, py]: [number, number]) => Math.abs(a * px + b - py) < 1e-9;
  /** The goal line, when the goal pins one down: slope and crossing, or two points. */
  const goalLine = ((): [number, number] | null => {
    if (!line) return null;
    let m = goal.m, c = goal.c;
    if (m === undefined && through.length >= 2) m = (through[1][1] - through[0][1]) / (through[1][0] - through[0][0]);
    if (m !== undefined && c === undefined && through.length) c = through[0][1] - m * through[0][0];
    if (c !== undefined && m === undefined && through.length) {
      const p = through.find(([px]) => px !== 0);
      if (p) m = (p[1] - c) / p[0];
    }
    return m !== undefined && c !== undefined ? [m, c] : null;
  })();
  function check() {
    const attempt = tries + 1;
    if (!line) {
      if (a === goal.x && b === goal.y) return onCheck({ right: true });
      const gx = goal.x!, gy = goal.y!;
      const swapped = a === gy && b === gx;
      const dirs = [a < gx ? t("act.g.dir_right") : a > gx ? t("act.g.dir_left") : "", b < gy ? t("act.g.dir_up") : b > gy ? t("act.g.dir_down") : ""].filter(Boolean).join(" ");
      return onCheck({
        right: false,
        vals: { x: a, y: b },
        where: t(a !== gx && b !== gy ? "act.g.where_both" : a !== gx ? "act.g.where_x" : "act.g.where_y"),
        effect: swapped ? t("act.g.swapped", { x: show(a), y: show(b) }) : t("act.g.point_effect", { x: show(a), y: show(b) }),
        nudge: ladder(t, attempt, attempt === 1 ? t("act.g.nudge_dir", { dirs }) : t("act.g.read_axes")),
      });
    }
    const ok = (goal.m === undefined || Math.abs(a - goal.m) < 1e-9) && (goal.c === undefined || b === goal.c) && through.every(hits);
    if (ok) return onCheck({ right: true });
    const misses = through.filter((p) => !hits(p));
    const where = [
      misses.length ? t("act.g.misses_n", { n: misses.length, total: through.length }) : "",
      goal.m !== undefined && Math.abs(a - goal.m) >= 1e-9 ? t("act.g.slope_is", { yours: show(a), want: show(goal.m) }) : "",
      goal.c !== undefined && b !== goal.c ? t("act.g.c_is", { yours: show(b), want: show(goal.c) }) : "",
    ].filter(Boolean);
    const effect = [t(a < 0 ? "act.g.line_effect_down" : "act.g.line_effect", { m: show(Math.abs(a)), c: show(b) })];
    for (const [px, py] of misses.slice(0, 2)) effect.push(t("act.g.misses", { x: show(px), y: show(py), at: show(a * px + b) }));
    let nudge = "";
    if (goalLine) {
      const [m, c] = goalLine;
      const parts = [];
      if (Math.abs(a - m) >= 1e-9) parts.push(t(a < m ? "act.g.tilt_up" : "act.g.tilt_down"));
      if (b !== c) parts.push(t(b < c ? "act.g.lift" : "act.g.lower"));
      nudge = parts.join(" ");
    }
    if (!nudge && misses.length) nudge = t(a * misses[0][0] + b < misses[0][1] ? "act.g.below" : "act.g.above", { x: show(misses[0][0]) });
    onCheck({ right: false, vals: { m: a, c: b }, where: where.join(" "), effect, nudge: ladder(t, attempt, nudge || t("act.g.read_axes"), goalLine ? undefined : nudge) });
  }
  const step = (set: (f: (v: number) => number) => void, d: number, min: number, max: number) => {
    set((v) => Math.min(max, Math.max(min, Math.round((v + d) * 1000) / 1000)));
    onChange();
  };
  const ticks = Array.from({ length: hi - lo + 1 }, (_, i) => lo + i);
  return (
    <>
      <svg viewBox="0 0 280 280" className="activity-svg graph-svg" role="img" aria-label={state}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={X(v)} y1={Y(lo)} x2={X(v)} y2={Y(hi)} className="act-grid" />
            <line x1={X(lo)} y1={Y(v)} x2={X(hi)} y2={Y(v)} className="act-grid" />
            {v !== 0 && (v - lo) % 2 === 0 && (
              <>
                <text x={X(v)} y={Y(0) + 12} textAnchor="middle" className="act-label small">
                  {show(v)}
                </text>
                <text x={X(0) - 4} y={Y(v) + 4} textAnchor="end" className="act-label small">
                  {show(v)}
                </text>
              </>
            )}
          </g>
        ))}
        <line x1={X(lo)} y1={Y(0)} x2={X(hi)} y2={Y(0)} className="act-axis" />
        <line x1={X(0)} y1={Y(lo)} x2={X(0)} y2={Y(hi)} className="act-axis" />
        {spec.x_label && (
          <text x={X(hi)} y={Y(0) - 6} textAnchor="end" className="act-label">
            {spec.x_label}
          </text>
        )}
        {spec.y_label && (
          <text x={X(0) + 6} y={Y(hi) + 12} className="act-label">
            {spec.y_label}
          </text>
        )}
        <clipPath id="graph-clip">
          <rect x={X(lo)} y={Y(hi)} width={(hi - lo) * S} height={(hi - lo) * S} />
        </clipPath>
        {tries >= REVEAL && goalLine && (
          <line x1={X(lo)} y1={Y(goalLine[0] * lo + goalLine[1])} x2={X(hi)} y2={Y(goalLine[0] * hi + goalLine[1])} className="act-arm goal" clipPath="url(#graph-clip)" />
        )}
        {line ? (
          <line x1={X(lo)} y1={Y(a * lo + b)} x2={X(hi)} y2={Y(a * hi + b)} className={`act-arm moving${missed ? " wrong" : ""}`} clipPath="url(#graph-clip)" />
        ) : (
          <>
            {/* Dashed guides show how the point is read: across to x, up to y. */}
            <line x1={X(a)} y1={Y(0)} x2={X(a)} y2={Y(b)} className={`act-guide${missed ? " wrong" : ""}`} />
            <line x1={X(0)} y1={Y(b)} x2={X(a)} y2={Y(b)} className={`act-guide${missed ? " wrong" : ""}`} />
            <circle cx={X(a)} cy={Y(b)} r={6} className={`act-marker${missed ? " wrong" : ""}`} />
          </>
        )}
        {line &&
          missed &&
          through
            .filter((p) => !hits(p))
            .map(([px, py], i) => <line key={i} x1={X(px)} y1={Y(py)} x2={X(px)} y2={Y(Math.max(lo, Math.min(hi, a * px + b)))} className="act-miss-gap" />)}
        {through.map(([px, py], i) => (
          <circle key={i} cx={X(px)} cy={Y(py)} r={6} className="act-target" />
        ))}
        {tries >= REVEAL && !line && goal.x !== undefined && <circle cx={X(goal.x)} cy={Y(goal.y!)} r={8} className="act-ghost" />}
      </svg>
      <p className="activity-state" role="status">
        {state}
      </p>
      <div className="row">
        {line ? (
          <>
            <button className="secondary" onClick={() => step(setA, -mStep, -10, 10)}>{t("act.g.flatter")}</button>
            <button className="secondary" onClick={() => step(setA, mStep, -10, 10)}>{t("act.g.steeper")}</button>
            <button className="secondary" onClick={() => step(setB, -1, lo, hi)}>{t("act.g.down")}</button>
            <button className="secondary" onClick={() => step(setB, 1, lo, hi)}>{t("act.g.up")}</button>
          </>
        ) : (
          <>
            <button className="secondary" onClick={() => step(setA, -1, lo, hi)}>← {t("act.left")}</button>
            <button className="secondary" onClick={() => step(setA, 1, lo, hi)}>{t("act.right_dir")} →</button>
            <button className="secondary" onClick={() => step(setB, -1, lo, hi)}>{t("act.g.down")}</button>
            <button className="secondary" onClick={() => step(setB, 1, lo, hi)}>{t("act.g.up")}</button>
          </>
        )}
        <CheckButton t={t} onClick={check} />
      </div>
    </>
  );
}

const PANELS: Record<string, (p: PanelProps) => React.ReactElement> = {
  number_line: NumberLine,
  fraction_bar: FractionBar,
  rectangle: Rectangle,
  mirror: Mirror,
  angle: Angle,
  sort: Sort,
  order: Order,
  bars: Bars,
  array: ArrayPanel,
  scale: Scale,
  pattern: Pattern,
  formula: Formula,
  graph: Graph,
};
