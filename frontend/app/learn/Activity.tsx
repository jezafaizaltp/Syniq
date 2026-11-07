"use client";

import { useMemo, useState } from "react";
import type { Key } from "@/lib/i18n";
import { useSession } from "@/lib/session";

/**
 * Hands-on activities (backend/app/activities.py checks the format).
 * Everything is changed with buttons, never by dragging, so a switch, a keyboard or a screen
 * reader works too; the state is always said in words in a live region. A wrong try shows what
 * the child made next to what the goal wanted (the mistake principle), never just "wrong".
 */

type Goal = {
  prompt: string;
  hint?: string;
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
};
type Zone = { from: number; to: number; label: string };
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
  items?: { label: string; bin: string; why?: string }[];
  steps?: string[];
  categories?: { label: string; value: number }[];
  show?: "tally" | "table";
  unit?: string;
  orientation?: "horizontal" | "vertical";
  zones?: Zone[];
  rule?: string;
  max_step?: number;
};

type T = (key: Key, vars?: Record<string, string | number>) => string;
/** What a type's panel reports back on Check: right, or what the child made and what was wanted. */
type Verdict = { right: boolean; yours?: string; want?: string; note?: string };

export default function Activity({ spec, onDone }: { spec: ActivitySpec; onDone?: () => void }) {
  const { t } = useSession();
  const goals = spec.goals?.length ? spec.goals : [{ prompt: "" }];
  const [g, setG] = useState(0);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [finished, setFinished] = useState(false);
  const [round, setRound] = useState(0); // remounts the panel for "Start again"
  const goal = goals[g];

  function report(v: Verdict) {
    setVerdict(v);
    if (v.right && g === goals.length - 1) {
      setFinished(true);
      onDone?.();
    }
  }

  function nextGoal() {
    setVerdict(null);
    setG(g + 1);
  }

  const Panel = PANELS[spec.type];
  if (!Panel) return null;
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
      <Panel key={`${round}-${g}`} spec={spec} goal={goal} t={t} verdict={verdict} onCheck={report} onChange={() => setVerdict(null)} />
      <div aria-live="polite">
        {verdict && (
          <div className={`feedback ${verdict.right ? "good" : "warn"}`}>
            <p style={{ margin: 0 }}>{verdict.right ? (finished ? t("act.all_done") : t("act.right")) : t("act.not_yet")}</p>
            {!verdict.right && verdict.yours !== undefined && (
              <p style={{ margin: "6px 0 0" }}>{t("act.yours", { yours: verdict.yours, want: verdict.want ?? "" })}</p>
            )}
            {verdict.note && <p style={{ margin: "6px 0 0" }}>{verdict.note}</p>}
            {!verdict.right && goal.hint && <p style={{ margin: "6px 0 0" }}>{goal.hint}</p>}
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

type PanelProps = { spec: ActivitySpec; goal: Goal; t: T; verdict: Verdict | null; onCheck: (v: Verdict) => void; onChange: () => void };

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

const near = (a: number, b: number) => Math.abs(a - b) < 1e-9;

// --- Number line -------------------------------------------------------------------------

function NumberLine({ spec, goal, t, verdict, onCheck, onChange }: PanelProps) {
  const lo = spec.min!, hi = spec.max!, step = spec.step!;
  const [v, setV] = useState(spec.start ?? lo);
  const show = (x: number) => fmt(x, step, spec.denominator);
  const move = (d: number) => {
    setV((x) => Math.min(hi, Math.max(lo, Math.round((x + d * step) / step) * step)));
    onChange();
  };
  const ticks = Math.round((hi - lo) / step);
  const X = (x: number) => 20 + ((x - lo) / (hi - lo)) * 320;
  const labelEvery = Math.max(1, Math.ceil(ticks / 10));
  const target = goal.target!;
  const missed = verdict && !verdict.right;
  return (
    <>
      <svg viewBox="0 0 360 90" className="activity-svg number-line-svg" role="img" aria-label={t("act.nl.at", { v: show(v) })}>
        <line x1={20} y1={40} x2={340} y2={40} className="act-axis" />
        {Array.from({ length: ticks + 1 }, (_, i) => {
          const x = lo + i * step;
          return (
            <g key={i}>
              <line x1={X(x)} y1={34} x2={X(x)} y2={46} className="act-axis" />
              {i % labelEvery === 0 && (
                <text x={X(x)} y={68} textAnchor="middle" className="act-label">
                  {show(x)}
                </text>
              )}
            </g>
          );
        })}
        {missed && <circle cx={X(target)} cy={40} r={9} className="act-ghost" />}
        <path d={`M ${X(v)} 32 l -10 -18 h 20 z`} className="act-marker" />
      </svg>
      <p className="activity-state" role="status">{t("act.nl.at", { v: show(v) })}</p>
      <div className="row">
        <button className="secondary" onClick={() => move(-1)} disabled={v <= lo}>
          ← {t("act.left")}
        </button>
        <button className="secondary" onClick={() => move(1)} disabled={v >= hi}>
          {t("act.right_dir")} →
        </button>
        <CheckButton
          t={t}
          onClick={() =>
            onCheck(
              near(v, target)
                ? { right: true }
                : { right: false, yours: show(v), want: show(target), note: v < target ? t("act.go_right") : t("act.go_left") }
            )
          }
        />
      </div>
    </>
  );
}

// --- Fraction bar ------------------------------------------------------------------------

function gcd(a: number, b: number): number {
  return b ? gcd(b, a % b) : a;
}

function FractionBar({ spec, goal, t, onCheck, onChange, verdict }: PanelProps) {
  const most = spec.max_parts ?? 12;
  const [parts, setParts] = useState(2);
  const [shaded, setShaded] = useState<boolean[]>([false, false]);
  const count = shaded.filter(Boolean).length;
  function cut(n: number) {
    setParts(n);
    setShaded(Array(n).fill(false));
    onChange();
  }
  const want = `${goal.num}/${goal.den}`;
  function check() {
    const same = goal.equivalent === false ? parts === goal.den && count === goal.num : count * goal.den! === goal.num! * parts;
    if (same) return onCheck({ right: true });
    const note =
      goal.equivalent === false && count * goal.den! === goal.num! * parts
        ? t("act.fb.same_amount", { parts: goal.den! })
        : parts % goal.den! !== 0 && goal.den! % parts !== 0 && gcd(parts, goal.den!) === 1
          ? t("act.fb.cut_into", { den: goal.den! })
          : undefined;
    onCheck({ right: false, yours: `${count}/${parts}`, want, note });
  }
  return (
    <>
      {verdict && !verdict.right && <p className="frac-caption">{t("act.yours_label")}</p>}
      <div className="frac-bar" role="group" aria-label={t("act.fb.state", { parts, shaded: count })}>
        {shaded.map((on, i) => (
          <button
            key={i}
            className={`frac-part${on ? " on" : ""}`}
            aria-pressed={on}
            aria-label={t("act.fb.part", { n: i + 1 })}
            onClick={() => {
              setShaded(shaded.map((s, j) => (j === i ? !s : s)));
              onChange();
            }}
          />
        ))}
      </div>
      {verdict && !verdict.right && <p className="frac-caption">{t("act.goal_label", { want })}</p>}
      {verdict && !verdict.right && (
        <div className="frac-bar ghost" aria-hidden="true">
          {Array.from({ length: goal.den! }, (_, i) => (
            <span key={i} className={`frac-part${i < goal.num! ? " on" : ""}`} />
          ))}
        </div>
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

function Rectangle({ spec, goal, t, onCheck, onChange }: PanelProps) {
  const most = spec.max_side ?? 10;
  const [w, setW] = useState(2);
  const [h, setH] = useState(2);
  const area = w * h, per = 2 * (w + h);
  const state = t("act.rect.state", { w, h, a: area, p: per });
  const keys = (["width", "height", "area", "perimeter"] as const).filter((k) => goal[k] !== undefined);
  const now = { width: w, height: h, area, perimeter: per };
  const word = (k: (typeof keys)[number]) => t(`act.rect.${k}` as Key);
  function check() {
    if (keys.every((k) => now[k] === goal[k])) return onCheck({ right: true });
    onCheck({
      right: false,
      yours: keys.map((k) => `${word(k)} ${now[k]}`).join(", "),
      want: keys.map((k) => `${word(k)} ${goal[k]}`).join(", "),
    });
  }
  const set = (f: (n: number) => void, n: number) => {
    f(Math.min(most, Math.max(1, n)));
    onChange();
  };
  return (
    <>
      <div className="rect-grid" style={{ gridTemplateColumns: `repeat(${most}, 1fr)` }} role="img" aria-label={state}>
        {Array.from({ length: most * most }, (_, i) => {
          const c = i % most, r = Math.floor(i / most);
          return <span key={i} className={c < w && r < h ? "on" : ""} />;
        })}
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

function Mirror({ spec, t, onCheck, onChange, verdict }: PanelProps) {
  const left = spec.left!;
  const half = left[0].length;
  const [right, setRight] = useState<boolean[][]>(left.map(() => Array(half).fill(false)));
  // The right half, read outwards from the mirror, must match the left read inwards.
  const want = (r: number, c: number) => left[r][half - 1 - c] === "#";
  const wrong = right.flatMap((row, r) => row.map((on, c) => on !== want(r, c))).filter(Boolean).length;
  const filled = right.flat().filter(Boolean).length;
  return (
    <>
      <div className="mirror" style={{ "--cells": half * 2 } as React.CSSProperties} role="group" aria-label={t("act.mirror.state", { n: filled })}>
        {left.map((row, r) => (
          <div key={r} className="mirror-row">
            {[...row].map((ch, c) => (
              <span key={c} className={`mirror-cell${ch === "#" ? " on" : ""}`} aria-hidden="true" />
            ))}
            <span className="mirror-line" aria-hidden="true" />
            {right[r].map((on, c) => (
              <button
                key={c}
                className={`mirror-cell${on ? " on" : ""}${verdict && !verdict.right && on !== want(r, c) ? " miss" : ""}`}
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
        <CheckButton t={t} onClick={() => onCheck(wrong === 0 ? { right: true } : { right: false, note: t("act.mirror.wrong", { n: wrong }) })} />
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

function Angle({ goal, t, onCheck, onChange, verdict }: PanelProps) {
  const [d, setD] = useState(30);
  const kindWord = (k: string) => t(`act.kind.${k}` as Key);
  const state = t("act.angle.state", { d, kind: kindWord(angleKind(d)) });
  const rad = (d * Math.PI) / 180;
  const cx = 110, cy = 110, R = 90;
  const ex = cx + R * Math.cos(rad), ey = cy - R * Math.sin(rad);
  const arcR = 30;
  const large = d > 180 ? 1 : 0;
  const ax = cx + arcR * Math.cos(rad), ay = cy - arcR * Math.sin(rad);
  const turn = (n: number) => {
    setD((x) => Math.min(360, Math.max(5, x + n)));
    onChange();
  };
  function check() {
    const right = goal.degrees !== undefined ? d === goal.degrees : angleKind(d) === goal.kind;
    if (right) return onCheck({ right: true });
    onCheck({
      right: false,
      yours: goal.degrees !== undefined ? `${d}°` : kindWord(angleKind(d)),
      want: goal.degrees !== undefined ? `${goal.degrees}°` : kindWord(goal.kind!),
      note: goal.degrees !== undefined ? (d < goal.degrees ? t("act.angle.open") : t("act.angle.close")) : undefined,
    });
  }
  return (
    <>
      <svg viewBox="0 0 220 220" className="activity-svg angle-svg" role="img" aria-label={state}>
        <line x1={cx} y1={cy} x2={cx + R} y2={cy} className="act-arm" />
        {verdict && !verdict.right && goal.degrees !== undefined && (
          <line
            x1={cx}
            y1={cy}
            x2={cx + R * Math.cos((goal.degrees * Math.PI) / 180)}
            y2={cy - R * Math.sin((goal.degrees * Math.PI) / 180)}
            className="act-arm goal"
          />
        )}
        <line x1={cx} y1={cy} x2={ex} y2={ey} className="act-arm moving" />
        {d < 360 && <path d={`M ${cx + arcR} ${cy} A ${arcR} ${arcR} 0 ${large} 0 ${ax} ${ay}`} className="act-arc" />}
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

function Sort({ spec, t, onCheck, onChange, verdict }: PanelProps) {
  const items = useMemo(() => shuffled(spec.items!, spec.prompt), [spec]);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const allChosen = items.every((it) => choice[it.label]);
  const wrong = items.filter((it) => choice[it.label] && choice[it.label] !== it.bin);
  function check() {
    if (!wrong.length) return onCheck({ right: true });
    onCheck({
      right: false,
      note: wrong
        .map((it) => `${t("act.sort.wrong", { label: it.label, yours: choice[it.label], right: it.bin })}${it.why ? ` ${it.why}` : ""}`)
        .join(" "),
    });
  }
  return (
    <>
      <ul className="sort-list">
        {items.map((it) => (
          <li key={it.label} className={verdict && !verdict.right && choice[it.label] !== it.bin ? "miss" : ""}>
            <span className="sort-item">{it.label}</span>
            <span className="row" role="group" aria-label={it.label}>
              {spec.bins!.map((b) => (
                <button
                  key={b}
                  className="secondary sort-bin"
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
        ))}
      </ul>
      <div className="row">
        <CheckButton t={t} onClick={check} disabled={!allChosen} />
      </div>
    </>
  );
}

// --- Order --------------------------------------------------------------------------------

function Order({ spec, t, onCheck, onChange }: PanelProps) {
  const steps = spec.steps!;
  const pool = useMemo(() => shuffled(steps, spec.prompt), [steps, spec.prompt]);
  const [mine, setMine] = useState<string[]>([]);
  function check() {
    const at = mine.findIndex((s, i) => s !== steps[i]);
    if (at < 0) return onCheck({ right: true });
    onCheck({ right: false, note: t("act.order.wrong", { n: at + 1, yours: mine[at], right: steps[at] }) });
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
        {mine.map((s) => (
          <li key={s}>{s}</li>
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
        <CheckButton t={t} onClick={check} disabled={mine.length < steps.length} />
      </div>
    </>
  );
}

// --- Bar graph ----------------------------------------------------------------------------

function tally(n: number): string {
  return "卌 ".repeat(Math.floor(n / 5)) + "|".repeat(n % 5);
}

function Bars({ spec, t, onCheck, onChange }: PanelProps) {
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
    onCheck({
      right: false,
      yours: bad.map(({ c, v }) => `${c.label} ${v}`).join(", "),
      want: bad.map(({ c }) => `${c.label} ${c.value}`).join(", "),
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
          <div key={c.label} className="act-bar-col">
            <span className="act-bar-num">{vals[i]}</span>
            <span className="act-bar" style={{ height: `${(vals[i] / most) * 100}%` }} />
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

function ArrayPanel({ goal, t, onCheck, onChange }: PanelProps) {
  const n = goal.n!;
  const [rows, setRows] = useState(1);
  const [found, setFound] = useState<number[]>([]);
  const cols = Math.ceil(n / rows);
  const full = n % rows === 0;
  const divisors = Array.from({ length: n }, (_, i) => i + 1).filter((r) => n % r === 0);
  const state = full ? t("act.arr.full", { r: rows, c: n / rows, n }) : t("act.arr.left", { r: rows, c: Math.floor(n / rows), left: n % rows });
  function check() {
    if (goal.find !== undefined && goal.find !== "all") {
      return onCheck(rows === goal.find && full ? { right: true } : { right: false, yours: t("act.arr.rows", { r: rows }), want: t("act.arr.rows", { r: goal.find }) });
    }
    const missing = divisors.filter((d) => !found.includes(d));
    if (!missing.length) return onCheck({ right: true, note: t("act.arr.factors", { n, list: divisors.join(", ") }) });
    onCheck({ right: false, note: t("act.arr.need", { k: found.length, total: divisors.length }) });
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
          <button className="secondary" disabled={!full || found.includes(rows)} onClick={() => setFound([...found, rows].sort((a, b) => a - b))}>
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

function Scale({ spec, goal, t, onCheck, onChange, verdict }: PanelProps) {
  const lo = spec.min!, hi = spec.max!, step = spec.step!;
  const [v, setV] = useState(spec.start ?? lo);
  const zones = spec.zones ?? [];
  const zoneOf = (x: number) => zones.find((z) => x >= z.from && (x < z.to || (x === hi && z.to === hi)))?.label;
  const show = (x: number) => `${fmt(x, step)} ${spec.unit}`;
  const z = zoneOf(v);
  const state = z ? t("act.scale.state_zone", { v: show(v), zone: z }) : t("act.scale.state", { v: show(v) });
  const move = (k: number) => {
    setV((x) => Math.min(hi, Math.max(lo, Math.round((x + k * step) / step) * step)));
    onChange();
  };
  const vertical = spec.orientation === "vertical";
  const frac = (x: number) => (x - lo) / (hi - lo);
  const big = (hi - lo) / step >= 40 ? 10 : 5; // a bigger jump, so long scales need few presses
  function check() {
    if (goal.value !== undefined) {
      if (near(v, goal.value)) return onCheck({ right: true });
      return onCheck({ right: false, yours: show(v), want: show(goal.value), note: v < goal.value ? t("act.scale.higher") : t("act.scale.lower") });
    }
    if (zoneOf(v) === goal.zone) return onCheck({ right: true });
    return onCheck({ right: false, yours: zoneOf(v) ?? show(v), want: goal.zone! });
  }
  const missed = verdict && !verdict.right && goal.value !== undefined;
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
              className="act-zone"
              style={vertical ? { bottom: `${frac(zn.from) * 100}%`, height: `${(frac(zn.to) - frac(zn.from)) * 100}%` } : { left: `${frac(zn.from) * 100}%`, width: `${(frac(zn.to) - frac(zn.from)) * 100}%` }}
            >
              <span className="act-zone-label">{zn.label}</span>
            </span>
          ))}
          <span className="act-fill" style={vertical ? { height: `${frac(v) * 100}%` } : { width: `${frac(v) * 100}%` }} />
          {missed && <span className="act-scale-ghost" style={vertical ? { bottom: `${frac(goal.value!) * 100}%` } : { left: `${frac(goal.value!) * 100}%` }} />}
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

/** Dot positions for step n, so the shape of the pattern is visible, not just the count. */
function dots(rule: string, n: number): { x: number; y: number; layer: number }[] {
  const out: { x: number; y: number; layer: number }[] = [];
  if (rule === "square") for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) out.push({ x, y, layer: Math.max(x, y) });
  else if (rule === "triangle") for (let y = 0; y < n; y++) for (let x = 0; x <= y; x++) out.push({ x: x + (n - 1 - y) / 2, y, layer: y });
  else if (rule === "odd") {
    for (let x = 0; x < n; x++) out.push({ x, y: n - 1, layer: 0 });
    for (let y = 0; y < n - 1; y++) out.push({ x: 0, y, layer: 1 });
  } else {
    const count = RULES[rule](n);
    const per = rule === "even" ? n : 8;
    for (let i = 0; i < count; i++) out.push({ x: i % per, y: Math.floor(i / per), layer: 0 });
  }
  return out;
}

function Pattern({ spec, goal, t, onCheck, onChange }: PanelProps) {
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
  return (
    <>
      <svg viewBox={`-1 -1 ${size + 1} ${size + 1}`} className="activity-svg pattern-svg" role="img" aria-label={state}>
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={0.32} className={`act-dot layer-${p.layer % 2}`} />
        ))}
      </svg>
      <p className="activity-state" role="status">{state}</p>
      <div className="row">
        <button className="secondary" onClick={() => grow(-1)} disabled={s <= 1}>
          {t("act.pat.shrink")}
        </button>
        <button className="secondary" onClick={() => grow(1)} disabled={s >= most}>
          {t("act.pat.grow")}
        </button>
        <CheckButton
          t={t}
          onClick={() => onCheck(count === goal.count ? { right: true } : { right: false, yours: String(count), want: String(goal.count), note: count < goal.count! ? t("act.pat.more") : t("act.pat.fewer") })}
        />
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
};
