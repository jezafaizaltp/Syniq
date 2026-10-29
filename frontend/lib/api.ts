export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "student" | "guardian" | "teacher" | "admin";

export type Settings = {
  font_scale?: number;
  high_contrast?: boolean;
  dyslexia_font?: boolean;
  reduced_motion?: boolean;
  read_aloud?: boolean;
  extra_time?: boolean;
  preferred_style?: string | null;
  support_modes?: string[];
  auto_support?: Record<string, { reason: string; since: string }>;
  auto_off?: string[];
};

/** Support for sight, hearing or speech: chosen by a parent or the student. */
export const CHOSEN_SUPPORT: { key: string; me: string; child: string; help: string }[] = [
  {
    key: "screen_reader",
    me: "I use a screen reader or find pictures hard to see",
    child: "Uses a screen reader or finds pictures hard to see",
    help: "Everything is said in words, not only shown in pictures.",
  },
  {
    key: "visual_first",
    me: "I'm deaf or hard of hearing",
    child: "Is deaf or hard of hearing",
    help: "Nothing depends on sound. Pictures and text come first.",
  },
  {
    key: "tap_to_answer",
    me: "Let me tap answers instead of typing or speaking",
    child: "Taps answers instead of typing or speaking",
    help: "Number questions show answers to choose from.",
  },
];

/** Support SYNiq turns on itself when a student's answers show it helps. */
export const NOTICED_SUPPORT: Record<string, string> = {
  focus: "Shorter steps, one at a time, with quick challenges",
  easy_read: "Shorter lines, a clearer font, and reading aloud",
  small_steps: "Pictures and smaller numbers first",
};

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

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });

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
