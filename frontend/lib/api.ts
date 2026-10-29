import type { Lang } from "./i18n";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// The language the server should answer in: feedback, reasons and errors.
let apiLang: Lang = "en";
export function setApiLang(lang: Lang) {
  apiLang = lang;
}

export type Role = "student" | "guardian" | "teacher" | "admin";

export type Settings = {
  font_scale?: number;
  high_contrast?: boolean;
  dyslexia_font?: boolean;
  reduced_motion?: boolean;
  read_aloud?: boolean;
  extra_time?: boolean;
  preferred_style?: string | null;
  ui_language?: Lang;
  support_modes?: string[];
  auto_support?: Record<string, { reason: string; since: string }>;
  auto_off?: string[];
};

/** Support for sight, hearing or speech: chosen by a parent or the student. Words: support.<key>.* in i18n.ts. */
export const CHOSEN_SUPPORT = ["screen_reader", "visual_first", "tap_to_answer"] as const;

/** Support SYNiq turns on itself when a student's answers show it helps. Words: noticed.<key> in i18n.ts. */
export const NOTICED_SUPPORT = ["focus", "easy_read", "small_steps"] as const;

export function effectiveSupport(s: Settings | undefined): string[] {
  const off = s?.auto_off ?? [];
  return [...(s?.support_modes ?? []), ...Object.keys(s?.auto_support ?? {}).filter((m) => !off.includes(m))];
}

export type Me = {
  id: number;
  name: string;
  role: Role;
  settings: Settings;
  consent?: { core_learning: boolean; mood_checkins: boolean };
  must_change_password?: boolean;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function token(): string | null {
  try {
    return localStorage.getItem("syniq_token");
  } catch {
    return null;
  }
}

export function hasToken(): boolean {
  return token() !== null;
}

export function setToken(value: string | null) {
  try {
    if (value) localStorage.setItem("syniq_token", value);
    else localStorage.removeItem("syniq_token");
  } catch {
    /* storage unavailable: session lasts for this page only */
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("Accept-Language", apiLang);
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Something went wrong");
  }
  return res.json() as Promise<T>;
}

/** A plain-text response, such as a CSV download. */
export async function apiText(path: string): Promise<string> {
  const headers = new Headers({ "Accept-Language": apiLang });
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  const res = await fetch(`${API_URL}${path}`, { headers });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return res.text();
}

export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });
export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });

// English words for the teacher screens. Student and parent screens use i18n.ts.
export const PROGRESS_WORDS: Record<string, string> = {
  not_started: "Not started",
  learning: "Learning",
  getting_there: "Getting there",
  secure: "Secure",
};

export const STYLE_WORDS: Record<string, string> = {
  text: "Explain in words",
  visual: "Show me a picture",
  step_by_step: "Step by step",
  real_world: "Real-life example",
};
