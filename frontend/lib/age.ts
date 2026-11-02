import type { Me } from "./api";

/**
 * Which look a student gets, from their class alone:
 * little (LKG to Class 2): big pictures, large text, words read aloud;
 * middle (Classes 3 to 5): brighter and more playful;
 * big (Classes 6 to 12): the grown-up look.
 * Every look stays calm: no streaks, countdowns or flashing rewards.
 */
export type AgeBand = "little" | "middle" | "big";

export function ageBand(me: Me | null | undefined): AgeBand | undefined {
  if (me?.role !== "student" || !me.class) return undefined;
  const g = me.class.grade;
  return g <= 2 ? "little" : g <= 5 ? "middle" : "big";
}

/** Little ones hear words read aloud unless a parent has switched it off. */
export function readsAloud(me: Me | null | undefined): boolean {
  const chosen = me?.settings?.read_aloud;
  return chosen ?? ageBand(me) === "little";
}
