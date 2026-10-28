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
};

export type Me = {
  id: number;
  name: string;
  role: Role;
  settings: Settings;
  consent?: { core_learning: boolean; mood_checkins: boolean };
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
