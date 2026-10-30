// Draws the small diagrams the SYNiq tutor sends, e.g. "your way" next to "the right path".
//
// The tutor writes a JSON block (see DIAGRAM_SPEC in server/tutor.js). Coordinates are on a
// 100 x 60 canvas with y going up, like graph paper. Only known shapes and named colours are
// drawn, and every piece of text goes in with textContent, so a diagram can never inject markup.

const SVG = "http://www.w3.org/2000/svg";
const W = 100;
const H = 60;

const COLORS = {
  ink: "#2b211c",
  try: "#c0682e",
  right: "#4f7a55",
  accent: "#a63d2a",
  highlight: "#e0a21a",
  muted: "#8a7b70",
  blue: "#3f6f95",
};
const SOFT = {
  ink: "#e9e0d2",
  try: "#f6dcc4",
  right: "#d8e7d3",
  accent: "#f3d9cf",
  highlight: "#fce7ae",
  muted: "#efe7da",
  blue: "#d6e4ef",
};
const SIZES = { s: 4.4, m: 5.2, l: 6.4 };
const TONE_LABEL = { try: "Your way", right: "The right path", neutral: "" };

const MAX_PANELS = 3;
const MAX_SHAPES = 80;

function num(v, fallback = 0) {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(-40, Math.min(160, n));
}
function str(v, max = 90) {
  return typeof v === "string" ? v.slice(0, max) : v == null ? "" : String(v).slice(0, max);
}
function color(name, fallback = "ink") {
  return COLORS[name] || COLORS[fallback];
}
function fill(value, colorName) {
  if (!value || value === "none") return "none";
  if (value === "soft") return SOFT[colorName] || SOFT.ink;
  if (value === "solid") return color(colorName);
  if (SOFT[value]) return SOFT[value];
  return "none";
}
// Canvas y goes up; SVG y goes down.
const Y = (y) => H - num(y);
const X = (x) => num(x);

function el(name, attrs = {}, parent) {
  const node = document.createElementNS(SVG, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== undefined && v !== null) node.setAttribute(k, String(v));
  }
  if (parent) parent.appendChild(node);
  return node;
}

function text(parent, content, x, y, opts = {}) {
  const t = el(
    "text",
    {
      x: X(x),
      y: Y(y),
      fill: color(opts.color, "ink"),
      "font-size": SIZES[opts.size] || SIZES.m,
      "text-anchor": ["start", "middle", "end"].includes(opts.anchor) ? opts.anchor : "middle",
      "dominant-baseline": "middle",
      "font-weight": opts.bold ? 700 : 400,
      class: "sq-text",
    },
    parent,
  );
  t.textContent = str(content);
  return t;
}

function polar(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arrowHead(parent, x1, y1, x2, y2, stroke) {
  const ang = Math.atan2(Y(y2) - Y(y1), X(x2) - X(x1));
  const size = 2.6;
  const ax = X(x2);
  const ay = Y(y2);
  const p1 = [ax - size * Math.cos(ang - 0.45), ay - size * Math.sin(ang - 0.45)];
  const p2 = [ax - size * Math.cos(ang + 0.45), ay - size * Math.sin(ang + 0.45)];
  el("polygon", { points: `${ax},${ay} ${p1.join(",")} ${p2.join(",")}`, fill: stroke }, parent);
}

const DRAW = {
  line(g, s, arrow = false) {
    const [x1, y1, x2, y2] = (Array.isArray(s.line) ? s.line : s.arrow || []).map((v) => num(v));
    const stroke = color(s.color);
    el(
      "line",
      {
        x1: X(x1), y1: Y(y1), x2: X(x2), y2: Y(y2),
        stroke,
        "stroke-width": s.width === "thick" ? 1.3 : 0.8,
        "stroke-dasharray": s.dash ? "2 1.6" : null,
        "stroke-linecap": "round",
      },
      g,
    );
    if (arrow || s.arrow === true) arrowHead(g, x1, y1, x2, y2, stroke);
    if (s.label) {
      // Put the label beside the middle of the line, on the side away from the canvas centre.
      const mx = (x1 + x2) / 2;
      const my = (y1 + y2) / 2;
      const len = Math.hypot(x2 - x1, y2 - y1) || 1;
      let nx = -(y2 - y1) / len;
      let ny = (x2 - x1) / len;
      if (nx * (mx - W / 2) + ny * (my - H / 2) < 0) { nx = -nx; ny = -ny; }
      text(g, s.label, mx + nx * 4, my + ny * 4, { color: s.color, size: s.size || "s", bold: s.bold });
    }
  },
  arrow(g, s) {
    DRAW.line(g, { ...s, line: s.arrow }, true);
  },
  point(g, s) {
    const [x, y] = (s.point || []).map((v) => num(v));
    el("circle", { cx: X(x), cy: Y(y), r: 1.1, fill: color(s.color) }, g);
    if (s.label) {
      const dx = s.label_side === "left" ? -2.2 : 2.2;
      text(g, s.label, x + dx, y + 2.4, {
        color: s.color, size: s.size || "s", anchor: dx < 0 ? "end" : "start", bold: true,
      });
    }
  },
  text(g, s) {
    const [x, y] = (s.at || [W / 2, H / 2]).map((v) => num(v));
    text(g, s.text, x, y, s);
  },
  angle(g, s) {
    const [cx, cy] = (s.angle || []).map((v) => num(v));
    const r = Math.max(2, Math.min(30, num(s.r, 8)));
    let a1 = num(s.from, 0);
    let a2 = num(s.to, 30);
    if (a2 < a1) [a1, a2] = [a2, a1];
    const [sx, sy] = polar(cx, cy, r, a1);
    const [ex, ey] = polar(cx, cy, r, a2);
    const large = a2 - a1 > 180 ? 1 : 0;
    const stroke = color(s.color, "accent");
    // Sweep flag 0: counter-clockwise on screen once y is flipped.
    el(
      "path",
      {
        d: `M ${X(sx)} ${Y(sy)} A ${r} ${r} 0 ${large} 0 ${X(ex)} ${Y(ey)}`,
        fill: s.fill ? fill(s.fill, s.color || "accent") : "none",
        stroke,
        "stroke-width": 0.8,
      },
      g,
    );
    if (s.label) {
      const [lx, ly] = polar(cx, cy, r + 4.5, (a1 + a2) / 2);
      text(g, s.label, lx, ly, { color: s.color || "accent", size: s.size || "s", bold: true });
    }
  },
  right_angle(g, s) {
    const [cx, cy] = (s.right_angle || []).map((v) => num(v));
    const size = Math.max(1.5, Math.min(8, num(s.size, 3.5)));
    const a = num(s.from, 0);
    const [p1x, p1y] = polar(cx, cy, size, a);
    const [p3x, p3y] = polar(cx, cy, size, a + 90);
    const p2x = p1x + (p3x - cx);
    const p2y = p1y + (p3y - cy);
    el(
      "polyline",
      {
        points: `${X(p1x)},${Y(p1y)} ${X(p2x)},${Y(p2y)} ${X(p3x)},${Y(p3y)}`,
        fill: "none",
        stroke: color(s.color),
        "stroke-width": 0.6,
      },
      g,
    );
  },
  rect(g, s) {
    const [x, y, w, h] = (s.rect || []).map((v) => num(v));
    el(
      "rect",
      {
        x: X(x), y: Y(y + h), width: Math.abs(w), height: Math.abs(h), rx: 0.6,
        fill: fill(s.fill, s.color || "ink"), stroke: color(s.color), "stroke-width": 0.6,
      },
      g,
    );
    if (s.label) text(g, s.label, x + w / 2, y + h / 2, { color: s.color, size: s.size || "s", bold: s.bold });
  },
  circle(g, s) {
    const [cx, cy, r] = (s.circle || []).map((v) => num(v));
    el(
      "circle",
      {
        cx: X(cx), cy: Y(cy), r: Math.abs(r),
        fill: fill(s.fill, s.color || "ink"), stroke: color(s.color), "stroke-width": 0.7,
      },
      g,
    );
    if (s.label) text(g, s.label, cx, cy, { color: s.color, size: s.size || "s", bold: s.bold });
  },
  polygon(g, s) {
    const pts = (Array.isArray(s.polygon) ? s.polygon : [])
      .slice(0, 40)
      .filter((p) => Array.isArray(p))
      .map(([x, y]) => `${X(x)},${Y(y)}`)
      .join(" ");
    el(
      "polygon",
      {
        points: pts,
        fill: fill(s.fill, s.color || "ink"),
        stroke: color(s.color),
        "stroke-width": 0.7,
        "stroke-linejoin": "round",
      },
      g,
    );
  },
  highlight(g, s) {
    // A dashed yellow ring that says "look here", for the exact spot a step went off course.
    const [cx, cy] = (s.highlight || []).map((v) => num(v));
    const r = Math.max(2, Math.min(20, num(s.r, 6)));
    el(
      "circle",
      {
        cx: X(cx), cy: Y(cy), r,
        fill: SOFT.highlight, "fill-opacity": 0.55,
        stroke: COLORS.highlight, "stroke-width": 0.8, "stroke-dasharray": "1.6 1.2",
      },
      g,
    ).classList.add("sq-pulse");
    if (s.label) text(g, s.label, cx, cy + r + 3, { color: "ink", size: "s", bold: true });
  },
  numberline(g, s) {
    const n = s.numberline || {};
    const from = num(n.from, 0);
    const to = num(n.to, 10);
    const step = Math.max(Math.abs(num(n.step, 1)), (to - from) / 40 || 1);
    const y = num(n.y, 30);
    const x0 = 6;
    const x1 = 94;
    const at = (v) => x0 + ((v - from) / (to - from || 1)) * (x1 - x0);
    el("line", { x1: x0 - 3, y1: Y(y), x2: x1 + 3, y2: Y(y), stroke: COLORS.ink, "stroke-width": 0.7 }, g);
    arrowHead(g, x1, y, x1 + 3.5, y, COLORS.ink);
    arrowHead(g, x0, y, x0 - 3.5, y, COLORS.ink);
    for (let v = from, i = 0; v <= to + 1e-9 && i < 41; v += step, i++) {
      const x = at(v);
      el("line", { x1: x, y1: Y(y - 1.4), x2: x, y2: Y(y + 1.4), stroke: COLORS.ink, "stroke-width": 0.5 }, g);
      const label = Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : String(+v.toFixed(2));
      text(g, label, x, y - 4.2, { size: "s", color: "muted" });
    }
    for (const m of (Array.isArray(n.marks) ? n.marks : []).slice(0, 8)) {
      const x = at(num(m.at));
      el("circle", { cx: x, cy: Y(y), r: 1.5, fill: color(m.color, "accent") }, g);
      if (m.label) text(g, m.label, x, y + 5, { size: "s", color: m.color || "accent", bold: true });
    }
    for (const h of (Array.isArray(n.hops) ? n.hops : []).slice(0, 12)) {
      // A curved jump from one number to another, e.g. counting on.
      const xa = at(num(h.from));
      const xb = at(num(h.to));
      const lift = Math.min(14, Math.abs(xb - xa) / 2 + 3);
      const stroke = color(h.color, "right");
      el(
        "path",
        {
          d: `M ${xa} ${Y(y + 1)} Q ${(xa + xb) / 2} ${Y(y + 1 + lift * 2)} ${xb} ${Y(y + 1)}`,
          fill: "none", stroke, "stroke-width": 0.7,
        },
        g,
      );
      if (h.label) text(g, h.label, (xa + xb) / 2, y + 2 + lift + 2, { size: "s", color: h.color || "right" });
    }
  },
  bar(g, s) {
    // A fraction bar: a rectangle split into equal parts with some shaded.
    const b = s.bar || {};
    const x = num(b.x, 10);
    const y = num(b.y, 30);
    const w = Math.max(4, num(b.w, 60));
    const h = Math.max(2, num(b.h, 8));
    const parts = Math.max(1, Math.min(24, Math.round(num(b.parts, 4))));
    const shaded = Math.max(0, Math.min(parts, Math.round(num(b.shaded, 0))));
    const c = b.color || "right";
    for (let i = 0; i < parts; i++) {
      el(
        "rect",
        {
          x: x + (w / parts) * i, y: Y(y + h), width: w / parts, height: h,
          fill: i < shaded ? SOFT[c] || SOFT.right : "#fffdf8",
          stroke: color(c), "stroke-width": 0.5,
        },
        g,
      );
    }
    if (b.label) text(g, b.label, x + w + 3, y + h / 2, { anchor: "start", size: "m", color: c, bold: true });
  },
};

function shapeKind(s) {
  for (const k of Object.keys(DRAW)) if (k in s) return k;
  return null;
}

function drawPanel(panel) {
  const tone = ["try", "right"].includes(panel.tone) ? panel.tone : "neutral";
  const box = document.createElement("div");
  box.className = `sq-panel sq-${tone}`;

  const caption = str(panel.caption, 60) || TONE_LABEL[tone];
  if (caption) {
    const chip = document.createElement("div");
    chip.className = "sq-chip";
    chip.textContent = caption;
    box.appendChild(chip);
  }

  const svg = el("svg", {
    viewBox: `-6 -6 ${W + 12} ${H + 12}`,
    role: "presentation",
    focusable: "false",
    class: "sq-svg",
  });
  const g = el("g", { "font-family": "Atkinson Hyperlegible, system-ui, sans-serif" }, svg);
  const shapes = Array.isArray(panel.shapes) ? panel.shapes.slice(0, MAX_SHAPES) : [];
  // Highlights go underneath, so the ring never hides the label it points at.
  shapes.sort((a, b) => (b && "highlight" in b ? 1 : 0) - (a && "highlight" in a ? 1 : 0));
  for (const s of shapes) {
    if (!s || typeof s !== "object") continue;
    const kind = shapeKind(s);
    if (!kind) continue;
    try {
      DRAW[kind](g, s);
    } catch {
      // One odd shape shouldn't lose the rest of the picture.
    }
  }
  box.appendChild(svg);

  if (panel.note) {
    const note = document.createElement("p");
    note.className = "sq-note";
    note.textContent = str(panel.note, 240);
    box.appendChild(note);
  }
  return box;
}

export function renderDiagram(spec) {
  const panels = Array.isArray(spec.panels) ? spec.panels : [{ shapes: spec.shapes, caption: spec.caption, note: spec.note }];
  const fig = document.createElement("figure");
  fig.className = "sq-diagram";
  if (spec.title) {
    const cap = document.createElement("figcaption");
    cap.textContent = str(spec.title, 120);
    fig.appendChild(cap);
  }
  const row = document.createElement("div");
  row.className = "sq-panels";
  row.dataset.count = String(Math.min(panels.length, MAX_PANELS));
  for (const p of panels.slice(0, MAX_PANELS)) {
    if (p && typeof p === "object") row.appendChild(drawPanel(p));
  }
  fig.appendChild(row);

  // Screen readers get the tutor's description instead of the drawing.
  const alt = str(spec.alt, 600);
  if (alt) {
    row.setAttribute("role", "img");
    row.setAttribute("aria-label", alt);
    const desc = document.createElement("p");
    desc.className = "sq-alt";
    desc.textContent = alt;
    fig.appendChild(desc);
  }
  return fig;
}

export function parseDiagram(source) {
  try {
    const spec = JSON.parse(source);
    return spec && typeof spec === "object" ? spec : null;
  } catch {
    return null;
  }
}
