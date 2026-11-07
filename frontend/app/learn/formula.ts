/**
 * The tiny arithmetic language used by formula activities, the same as backend/app/activities.py:
 * numbers, names, + - * / ^ (power), brackets, pi, and sqrt, min, max, abs. Nothing else runs.
 */
type Node =
  | { k: "num"; v: number }
  | { k: "name"; n: string }
  | { k: "neg"; a: Node }
  | { k: "call"; f: string; args: Node[] }
  | { k: "op"; op: string; a: Node; b: Node };

const FUNCS: Record<string, (...xs: number[]) => number> = {
  sqrt: Math.sqrt,
  min: Math.min,
  max: Math.max,
  abs: Math.abs,
};

export function parseFormula(text: string): Node {
  const toks = text.match(/\d+\.?\d*|\.\d+|[a-z][a-z0-9_]*|[-+*/^(),]/g) ?? [];
  let i = 0;
  const peek = () => toks[i];
  const take = (want?: string) => {
    const t = toks[i++];
    if (t === undefined || (want && t !== want)) throw new Error(`expected ${want ?? "more"}`);
    return t;
  };
  const sum = (): Node => {
    let n = product();
    while (peek() === "+" || peek() === "-") n = { k: "op", op: take(), a: n, b: product() };
    return n;
  };
  const product = (): Node => {
    let n = unary();
    while (peek() === "*" || peek() === "/") n = { k: "op", op: take(), a: n, b: unary() };
    return n;
  };
  const unary = (): Node => {
    if (peek() === "-") {
      take();
      return { k: "neg", a: unary() };
    }
    return power();
  };
  const power = (): Node => {
    const base = atom();
    if (peek() === "^") {
      take();
      return { k: "op", op: "^", a: base, b: unary() };
    }
    return base;
  };
  const atom = (): Node => {
    const t = take();
    if (t === "(") {
      const n = sum();
      take(")");
      return n;
    }
    if (/^[\d.]/.test(t)) return { k: "num", v: Number(t) };
    if (FUNCS[t]) {
      take("(");
      const args = [sum()];
      while (peek() === ",") {
        take();
        args.push(sum());
      }
      take(")");
      return { k: "call", f: t, args };
    }
    return { k: "name", n: t };
  };
  const n = sum();
  if (i !== toks.length) throw new Error("unexpected text");
  return n;
}

export function evaluate(n: Node, env: Record<string, number>): number {
  switch (n.k) {
    case "num":
      return n.v;
    case "name":
      return n.n === "pi" ? Math.PI : env[n.n];
    case "neg":
      return -evaluate(n.a, env);
    case "call":
      return FUNCS[n.f](...n.args.map((a) => evaluate(a, env)));
    case "op": {
      const a = evaluate(n.a, env), b = evaluate(n.b, env);
      return n.op === "+" ? a + b : n.op === "-" ? a - b : n.op === "*" ? a * b : n.op === "/" ? a / b : a ** b;
    }
  }
}

export function wanted(v: number, want: number | [number, number]): boolean {
  return Array.isArray(want) ? v >= want[0] - 1e-9 && v <= want[1] + 1e-9 : Math.abs(v - want) < 1e-6;
}
