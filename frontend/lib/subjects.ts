/** Words for a subject's board and class, so lists that mix boards and classes can be told apart. */
export const BOARD_WORDS: Record<string, string> = { kerala_scert: "Kerala SCERT", cbse: "CBSE" };

export function classWords(grade: number) {
  return grade === -1 ? "LKG" : grade === 0 ? "UKG" : `Class ${grade}`;
}

type Labelled = { name: string; grade?: number; syllabus?: string };

/** "Kerala SCERT Class 9: English". Falls back to the plain name if board or class is unknown. */
export function subjectLabel(s: Labelled) {
  if (s.grade === undefined || !s.syllabus) return s.name;
  return `${BOARD_WORDS[s.syllabus] ?? s.syllabus} ${classWords(s.grade)}: ${s.name}`;
}

/** Kerala pilot subjects first, then each board by class, keeping the original order inside a class. */
export function bySchoolOrder<T extends Labelled>(list: T[]): T[] {
  const board = (s: T) => (s.syllabus === "kerala_scert" ? 0 : 1);
  return list
    .map((s, i) => ({ s, i }))
    .sort((a, b) => board(a.s) - board(b.s) || (a.s.syllabus ?? "").localeCompare(b.s.syllabus ?? "") || (a.s.grade ?? 0) - (b.s.grade ?? 0) || a.i - b.i)
    .map((x) => x.s);
}
