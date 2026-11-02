import type { Me, Role } from "./api";

const HOME: Record<Role, string> = { student: "/learn", teacher: "/teacher", admin: "/admin", guardian: "/parent", specialist: "/specialist" };

/** Where each person lands after signing in. Family accounts open on the family page. */
export function homeFor(me: Me): string {
  return me.role === "guardian" && me.family ? "/family" : HOME[me.role];
}
