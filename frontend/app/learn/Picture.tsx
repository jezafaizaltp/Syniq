"use client";

// Draws a "Show me a picture" explanation from the small description in a content pack
// (checked on the server by app/pictures.py). Drawn, not downloaded: free, offline, sharp,
// and it follows the app's colours, dark mode and high contrast. Drawings carry the pack's
// `alt` sentence for screen readers; flow and compare pictures are real lists, read as they are.

import React from "react";

type Pt = { at: number; label: string };
type Jump = { from: number; to: number; label?: string };
type Part = { size: number; label: string };
type Bar = { label: string; value: number };

export type PictureSpec = {
  kind: "number_line" | "area_grid" | "bars" | "flow" | "compare" | "geometry";
  alt: string;
  caption?: string;
  // number_line
  from?: number;
  to?: number;
  step?: number;
  points?: Pt[] | Record<string, [number, number]>;
  jumps?: Jump[];
  // area_grid
  cols?: Part[];
  rows?: Part[];
  cells?: string[][];
  // bars
  bars?: Bar[];
  unit?: string;
  touching?: boolean;
  // flow
  steps?: string[];
  // compare
  columns?: { title: string; points: string[] }[];
  // geometry
  axes?: boolean;
  range?: [number, number];
  x_label?: string;
  y_label?: string;
  segments?: (string[])[];
  circles?: { centre: string; radius: number }[];
  angles?: { at: string; from: string; to: string; label?: string }[];
};

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100));

function NumberLine({ p }: { p: PictureSpec }) {
  const lo = p.from!, hi = p.to!, step = p.step ?? 1;
  const W = 600, pad = 30;
  const hasJumps = (p.jumps ?? []).length > 0;
  // Later jumps arc higher, so their labels never sit on top of each other.
  const lift = 30;
  const y = hasJumps ? 100 + ((p.jumps ?? []).length - 1) * lift : 30, H = y + 52;
  const x = (v: number) => pad + ((v - lo) / (hi - lo)) * (W - 2 * pad);
  const ticks: number[] = [];
  for (let v = lo; v <= hi + 1e-9; v += step) ticks.push(Math.round(v * 1e6) / 1e6);
  const every = ticks.length > 21 ? 2 : 1;
  const points = (p.points as Pt[] | undefined) ?? [];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={p.alt} className="pic-svg">
      <defs>
        <marker id="pic-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="pic-fill-accent" />
        </marker>
      </defs>
      <line x1={pad - 14} y1={y} x2={W - pad + 14} y2={y} className="pic-axis" />
      {ticks.map((v, i) => (
        <g key={v}>
          <line x1={x(v)} y1={y - 6} x2={x(v)} y2={y + 6} className="pic-axis" />
          {i % every === 0 && (
            <text x={x(v)} y={y + 24} textAnchor="middle" className="pic-text-muted">{fmt(v)}</text>
          )}
        </g>
      ))}
      {(p.jumps ?? []).map((j, i) => {
        const x1 = x(j.from), x2 = x(j.to), h = Math.min(60, 18 + Math.abs(x2 - x1) / 4) + i * lift;
        return (
          <g key={i}>
            <path d={`M${x1},${y - 8} Q${(x1 + x2) / 2},${y - 8 - h * 2} ${x2},${y - 8}`} className="pic-jump" markerEnd="url(#pic-arrow)" />
            {j.label && (
              <text x={(x1 + x2) / 2} y={y - 12 - h} textAnchor="middle" className="pic-text-accent">{j.label}</text>
            )}
          </g>
        );
      })}
      {points.map((pt, i) => (
        <g key={i}>
          <circle cx={x(pt.at)} cy={y} r={7} className="pic-fill-accent" />
          <text x={x(pt.at)} y={y + 44} textAnchor="middle" className="pic-text-strong">{pt.label}</text>
        </g>
      ))}
    </svg>
  );
}

// Very small parts would squash their labels, so each part gets at least a fair share.
function shares(parts: Part[]) {
  const total = parts.reduce((s, q) => s + q.size, 0);
  const raw = parts.map((q) => Math.max(q.size / total, 0.2));
  const sum = raw.reduce((s, v) => s + v, 0);
  return raw.map((v) => v / sum);
}

function AreaGrid({ p }: { p: PictureSpec }) {
  const cols = p.cols!, rows = p.rows!, cells = p.cells!;
  const W = 600, H = 360, left = 90, top = 40;
  const gw = W - left - 20, gh = H - top - 20;
  const cw = shares(cols).map((s) => s * gw), rh = shares(rows).map((s) => s * gh);
  const cx = cw.map((_, i) => left + cw.slice(0, i).reduce((s, v) => s + v, 0));
  const ry = rh.map((_, i) => top + rh.slice(0, i).reduce((s, v) => s + v, 0));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={p.alt} className="pic-svg">
      {cols.map((c, i) => (
        <text key={i} x={cx[i] + cw[i] / 2} y={top - 12} textAnchor="middle" className="pic-text-muted">{c.label}</text>
      ))}
      {rows.map((r, i) => (
        <text key={i} x={left - 12} y={ry[i] + rh[i] / 2 + 6} textAnchor="end" className="pic-text-muted">{r.label}</text>
      ))}
      {cells.map((row, r) =>
        row.map((label, c) => (
          <g key={`${r}-${c}`}>
            <rect x={cx[c]} y={ry[r]} width={cw[c]} height={rh[r]} className={(r + c) % 2 ? "pic-cell-b" : "pic-cell-a"} />
            <text x={cx[c] + cw[c] / 2} y={ry[r] + rh[r] / 2 + 7} textAnchor="middle" className="pic-text-strong">{label}</text>
          </g>
        )),
      )}
    </svg>
  );
}

function Bars({ p }: { p: PictureSpec }) {
  const bars = p.bars!;
  const W = 600, H = 300, left = 20, base = 240, top = 30;
  const max = Math.max(...bars.map((b) => b.value));
  const slot = (W - 2 * left) / bars.length;
  const bw = p.touching ? slot : slot * 0.62;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={p.alt} className="pic-svg">
      {bars.map((b, i) => {
        const h = (b.value / max) * (base - top);
        const x = left + i * slot + (slot - bw) / 2;
        return (
          <g key={i}>
            <rect x={x} y={base - h} width={bw} height={h} rx={p.touching ? 0 : 6} className={i % 2 ? "pic-bar-b" : "pic-bar-a"} />
            <text x={x + bw / 2} y={base - h - 8} textAnchor="middle" className="pic-text-strong">{fmt(b.value)}</text>
            <text x={left + i * slot + slot / 2} y={base + 24} textAnchor="middle" className="pic-text-muted pic-small">{b.label}</text>
          </g>
        );
      })}
      <line x1={left} y1={base} x2={W - left} y2={base} className="pic-axis" />
      {p.unit && <text x={W - left} y={H - 8} textAnchor="end" className="pic-text-muted pic-small">{p.unit}</text>}
    </svg>
  );
}

function Geometry({ p }: { p: PictureSpec }) {
  const pts = (p.points as Record<string, [number, number]>) ?? {};
  const [lo, hi] = p.axes ? p.range ?? [-6, 6] : [0, 10];
  // Axes keep a fixed square; a plain figure is fitted to its own size so it fills the space.
  let x0 = lo, x1 = hi, y0 = lo, y1 = hi;
  if (!p.axes) {
    const xs: number[] = [], ys: number[] = [];
    for (const [x, y] of Object.values(pts)) { xs.push(x); ys.push(y); }
    for (const c of p.circles ?? []) {
      const [x, y] = pts[c.centre] ?? [5, 5];
      xs.push(x - c.radius, x + c.radius); ys.push(y - c.radius, y + c.radius);
    }
    [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  }
  const pad = p.axes ? 30 : 48;
  const k = p.axes ? 340 / (hi - lo) : Math.min(480 / Math.max(x1 - x0, 0.1), 340 / Math.max(y1 - y0, 0.1));
  const VW = (x1 - x0) * k + 2 * pad, VH = (y1 - y0) * k + 2 * pad;
  const sx = (v: number) => pad + (v - x0) * k;
  const sy = (v: number) => VH - pad - (v - y0) * k;
  const unit = k;
  const P = (n: string) => [sx(pts[n][0]), sy(pts[n][1])] as const;
  const names = Object.keys(pts);
  const cxm = names.reduce((s, n) => s + P(n)[0], 0) / names.length;
  const cym = names.reduce((s, n) => s + P(n)[1], 0) / names.length;
  // Labels go on the side away from the shape they belong to: the points joined to them.
  const near: Record<string, string[]> = {};
  for (const seg of p.segments ?? []) {
    (near[seg[0]] ??= []).push(seg[1]);
    (near[seg[1]] ??= []).push(seg[0]);
  }
  const centreOf = (ns: string[]) => {
    const list = ns.filter((n) => pts[n]);
    if (list.length < 2) return [cxm, cym] as const;
    return [list.reduce((s, n) => s + P(n)[0], 0) / list.length, list.reduce((s, n) => s + P(n)[1], 0) / list.length] as const;
  };
  const gridStep = hi - lo > 12 ? 2 : 1;
  const grid: number[] = [];
  for (let v = Math.ceil(lo / gridStep) * gridStep; v <= hi; v += gridStep) grid.push(v);
  return (
    <svg viewBox={`0 0 ${VW} ${VH}`} role="img" aria-label={p.alt} className={p.axes ? "pic-svg pic-square" : "pic-svg pic-figure"}>
      {p.axes && (
        <g>
          {grid.map((v) => (
            <g key={v}>
              <line x1={sx(v)} y1={sy(lo)} x2={sx(v)} y2={sy(hi)} className="pic-grid" />
              <line x1={sx(lo)} y1={sy(v)} x2={sx(hi)} y2={sy(v)} className="pic-grid" />
              {v !== 0 && <text x={sx(v)} y={sy(0) + 18} textAnchor="middle" className="pic-text-muted pic-small">{v}</text>}
              {v !== 0 && <text x={sx(0) - 8} y={sy(v) + 5} textAnchor="end" className="pic-text-muted pic-small">{v}</text>}
            </g>
          ))}
          <line x1={sx(lo)} y1={sy(0)} x2={sx(hi)} y2={sy(0)} className="pic-axis" />
          <line x1={sx(0)} y1={sy(lo)} x2={sx(0)} y2={sy(hi)} className="pic-axis" />
          <text x={sx(hi) - 4} y={sy(0) - 8} textAnchor="end" className="pic-text-muted">{p.x_label ?? "x"}</text>
          <text x={sx(0) + 10} y={sy(hi) + 14} className="pic-text-muted">{p.y_label ?? "y"}</text>
        </g>
      )}
      {(p.circles ?? []).map((c, i) => (
        <circle key={i} cx={P(c.centre)[0]} cy={P(c.centre)[1]} r={c.radius * unit} className="pic-shape" />
      ))}
      {(p.segments ?? []).map((s, i) => {
        const [x1, y1] = P(s[0]), [x2, y2] = P(s[1]);
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        // Put the label on the side away from the middle of the figure.
        let nx = -(y2 - y1), ny = x2 - x1;
        const len = Math.hypot(nx, ny) || 1;
        nx /= len; ny /= len;
        const [gx, gy] = centreOf([...(near[s[0]] ?? []), ...(near[s[1]] ?? [])]);
        if ((mx - gx) * nx + (my - gy) * ny < 0) { nx = -nx; ny = -ny; }
        // Far enough out that the whole label clears the line, whichever way the line runs.
        const off = 10 + Math.abs(nx) * (s[2]?.length ?? 0) * 5 + Math.abs(ny) * 9;
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} className="pic-shape" />
            {s[2] && <text x={mx + nx * off} y={my + ny * off + 6} textAnchor="middle" className="pic-text-accent">{s[2]}</text>}
          </g>
        );
      })}
      {(p.angles ?? []).map((a, i) => {
        const [vx, vy] = P(a.at), [fx, fy] = P(a.from), [tx, ty] = P(a.to);
        const a1 = Math.atan2(fy - vy, fx - vx), a2 = Math.atan2(ty - vy, tx - vx);
        let d = a2 - a1;
        while (d <= -Math.PI) d += 2 * Math.PI;
        while (d > Math.PI) d -= 2 * Math.PI;
        const r = 26, mid = a1 + d / 2;
        const ex = vx + r * Math.cos(a2), ey = vy + r * Math.sin(a2);
        return (
          <g key={i}>
            <path d={`M${vx + r * Math.cos(a1)},${vy + r * Math.sin(a1)} A${r},${r} 0 0 ${d > 0 ? 1 : 0} ${ex},${ey}`} className="pic-angle" />
            {a.label && <text x={vx + 46 * Math.cos(mid)} y={vy + 46 * Math.sin(mid) + 6} textAnchor="middle" className="pic-text-accent">{a.label}</text>}
          </g>
        );
      })}
      {names.filter((n) => !n.startsWith("_")).map((n) => {
        const [x, y] = P(n);
        const [gx, gy] = centreOf([n, ...(near[n] ?? [])]);
        let dx = x - gx, dy = y - gy;
        const len = Math.hypot(dx, dy);
        if (len < 1) { dx = -0.7; dy = -0.7; } else { dx /= len; dy /= len; }
        return (
          <g key={n}>
            <circle cx={x} cy={y} r={4.5} className="pic-fill-accent" />
            <text x={x + dx * 16} y={y + dy * 16 + 6} textAnchor="middle" className="pic-text-strong">{n}</text>
          </g>
        );
      })}
    </svg>
  );
}

function Flow({ p }: { p: PictureSpec }) {
  return (
    <ol className="pic-flow">
      {p.steps!.map((s, i) => (
        <li key={i}>
          <span className="pic-flow-n" aria-hidden="true">{i + 1}</span>
          <span>{s}</span>
        </li>
      ))}
    </ol>
  );
}

function Compare({ p }: { p: PictureSpec }) {
  return (
    <div className="pic-compare" style={{ gridTemplateColumns: `repeat(${p.columns!.length}, minmax(0, 1fr))` }}>
      {p.columns!.map((c, i) => (
        <section key={i} className={i % 2 ? "pic-col-b" : "pic-col-a"}>
          <h3>{c.title}</h3>
          <ul>
            {c.points.map((pt, j) => <li key={j}>{pt}</li>)}
          </ul>
        </section>
      ))}
    </div>
  );
}

const DRAW: Record<PictureSpec["kind"], (props: { p: PictureSpec }) => React.ReactElement> = {
  number_line: NumberLine,
  area_grid: AreaGrid,
  bars: Bars,
  flow: Flow,
  compare: Compare,
  geometry: Geometry,
};

export default function Picture({ picture }: { picture: PictureSpec }) {
  const Draw = DRAW[picture.kind];
  if (!Draw) return null;
  return (
    <figure className={`picture pic-${picture.kind}`}>
      <Draw p={picture} />
      {picture.caption && <figcaption>{picture.caption}</figcaption>}
    </figure>
  );
}
