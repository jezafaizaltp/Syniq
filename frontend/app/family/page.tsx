"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, api, del, post, put } from "@/lib/api";
import { useSession } from "@/lib/session";
import { RELATIONS, SECTION_LOOK } from "./words";

type Child = {
  id: number;
  name: string;
  birth_date: string | null;
  due_date: string | null;
  board: string;
  grade: number | null;
  grade_name: string | null;
  age: string;
  section: string;
  login: string | null;
};
type Adult = { id: number; name: string; relation: string; holder: boolean; you: boolean };
type Family = {
  name: string;
  plan: string;
  you: { relation: string; holder: boolean };
  adults: Adult[];
  children: Child[];
  sections: Record<string, { title: string; about: string; ready: boolean }>;
  boards: Record<string, string>;
  grades: { value: number; name: string }[];
};
type Made = { name: string; login: string; temporary_password: string };

/** The family's home: each child with the part of SYNiq that fits them now, and the adults who can see them. */
export default function FamilyPage() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [family, setFamily] = useState<Family | null>(null);
  const [editing, setEditing] = useState<Child | "new" | null>(null);
  const [made, setMade] = useState<Made | null>(null);

  useEffect(() => {
    if (!loading && (!me || me.role !== "guardian")) router.replace("/");
  }, [me, loading, router]);

  const load = useCallback(() => {
    api<Family>("/family").then(setFamily).catch(() => setFamily(null));
  }, []);
  useEffect(() => {
    if (me?.role === "guardian") load();
  }, [me, load]);

  if (!me || me.role !== "guardian" || !family) return null;
  const holder = family.you.holder;

  return (
    <div className="wrap">
      <h1>{family.name}</h1>
      <p className="muted">
        {holder ? "You hold this account. You decide who's in it and what SYNiq knows about your children." : `You're in this family as ${RELATIONS[family.you.relation]?.toLowerCase() ?? "a carer"}.`}
      </p>

      {made && <LoginMade made={made} onClose={() => setMade(null)} />}

      <section aria-labelledby="children">
        <div className="section-head">
          <h2 id="children">Children</h2>
          {holder && editing !== "new" && (
            <button className="secondary" onClick={() => setEditing("new")}>
              + Add a child
            </button>
          )}
        </div>
        {editing === "new" && <ChildForm family={family} onDone={() => (setEditing(null), load())} />}
        {family.children.length === 0 && editing !== "new" && (
          <div className="card sunny">
            <p style={{ margin: 0 }}>
              Add your first child, or the due date if you&apos;re expecting. SYNiq opens the part that fits their age: pregnancy, baby, the
              early years, or school.
            </p>
          </div>
        )}
        <div className="child-grid">
          {family.children.map((c) =>
            editing !== "new" && editing?.id === c.id ? (
              <ChildForm key={c.id} family={family} child={c} onDone={() => (setEditing(null), load())} />
            ) : (
              <ChildCard key={c.id} child={c} family={family} holder={holder} onEdit={() => setEditing(c)} onMade={(m) => (setMade(m), load())} onRemoved={load} />
            )
          )}
        </div>
      </section>

      <Adults family={family} holder={holder} onChange={load} onMade={setMade} />
    </div>
  );
}

function ChildCard({
  child,
  family,
  holder,
  onEdit,
  onMade,
  onRemoved,
}: {
  child: Child;
  family: Family;
  holder: boolean;
  onEdit: () => void;
  onMade: (m: Made) => void;
  onRemoved: () => void;
}) {
  const section = family.sections[child.section];
  const look = SECTION_LOOK[child.section];
  const [username, setUsername] = useState("");
  const [askLogin, setAskLogin] = useState(false);
  const [error, setError] = useState("");

  async function makeLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      onMade(await post<Made>(`/family/children/${child.id}/login`, { username }));
      setAskLogin(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't make the login");
    }
  }

  async function remove() {
    if (!confirm(`Remove ${child.name} from your family account?`)) return;
    try {
      await del(`/family/children/${child.id}`);
      onRemoved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove");
    }
  }

  return (
    <article className="card child-card" style={{ "--tile": look.colour } as React.CSSProperties}>
      <div className="child-top">
        <span className="subject-icon" aria-hidden="true">
          {look.icon}
        </span>
        <div>
          <h3>{child.name}</h3>
          <p className="muted">
            {child.age}
            {child.grade_name && ` · ${child.grade_name}, ${family.boards[child.board] ?? child.board}`}
          </p>
        </div>
      </div>
      <p className="child-section">
        <strong>{section.title}</strong>
        <br />
        {section.about}
      </p>
      {!section.ready && <p className="pill">Coming next in SYNiq</p>}
      {child.section === "early" && (
        <p>
          <Link className="btn" href={`/early?child=${child.id}`}>
            Open healthy screen time
          </Link>
        </p>
      )}
      {child.section === "school" && child.grade === null && <p className="muted">Add {child.name}&apos;s class so SYNiq can show the right subjects.</p>}
      {child.login && (
        <p>
          Signs in as <strong>{child.login}</strong>. <Link href="/parent">See progress</Link>
        </p>
      )}
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      {holder && askLogin && (
        <form onSubmit={makeLogin}>
          <label htmlFor={`login-${child.id}`}>A login name for {child.name}</label>
          <input id={`login-${child.id}`} autoCapitalize="none" spellCheck={false} placeholder="e.g. riya.k" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <p className="muted">Making a login is your consent for SYNiq to adapt to {child.name}. You can change this on the My children page.</p>
          <div className="row">
            <button type="submit">Make login</button>
            <button type="button" className="secondary" onClick={() => setAskLogin(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {holder && !askLogin && (
        <div className="row">
          {child.section === "school" && child.grade !== null && !child.login && <button onClick={() => setAskLogin(true)}>Give {child.name} a login</button>}
          <button className="secondary" onClick={onEdit}>
            Edit
          </button>
          {!child.login && (
            <button className="secondary" onClick={remove}>
              Remove
            </button>
          )}
        </div>
      )}
    </article>
  );
}

function ChildForm({ family, child, onDone }: { family: Family; child?: Child; onDone: () => void }) {
  const [name, setName] = useState(child?.name ?? "");
  const [expecting, setExpecting] = useState(!!child && !child.birth_date);
  const [birth, setBirth] = useState(child?.birth_date ?? "");
  const [due, setDue] = useState(child?.due_date ?? "");
  const [board, setBoard] = useState(child?.board ?? "cbse");
  const [grade, setGrade] = useState(child?.grade === null || child?.grade === undefined ? "" : String(child.grade));
  const [error, setError] = useState("");
  const today = new Date().toISOString().slice(0, 10);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const body = expecting
      ? { name, due_date: due }
      : { name, birth_date: birth, board, grade: grade === "" ? null : Number(grade) };
    try {
      if (child) await put(`/family/children/${child.id}`, body);
      else await post("/family/children", body);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save");
    }
  }

  return (
    <form className="card" onSubmit={save}>
      <h3>{child ? `Edit ${child.name}` : "Add a child"}</h3>
      {!child?.login && (
        <div className="options" role="group" aria-label="Born or expecting">
          <button type="button" className="option" aria-pressed={!expecting} onClick={() => setExpecting(false)}>
            Born
          </button>
          <button type="button" className="option" aria-pressed={expecting} onClick={() => setExpecting(true)}>
            Expecting
          </button>
        </div>
      )}
      <label htmlFor="child-name">{expecting ? "Name, or a nickname for now" : "Name"}</label>
      <input id="child-name" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} required placeholder={expecting ? "e.g. Baby" : ""} />
      {expecting ? (
        <>
          <label htmlFor="child-due">Due date</label>
          <input id="child-due" type="date" min={today} value={due} onChange={(e) => setDue(e.target.value)} required />
        </>
      ) : (
        <>
          <label htmlFor="child-birth">Date of birth</label>
          <input id="child-birth" type="date" max={today} value={birth} onChange={(e) => setBirth(e.target.value)} required />
          <label htmlFor="child-grade">Class at school</label>
          <select id="child-grade" value={grade} onChange={(e) => setGrade(e.target.value)}>
            {!child?.login && <option value="">Not in school yet</option>}
            {family.grades.map((g) => (
              <option key={g.value} value={g.value}>
                {g.name}
              </option>
            ))}
          </select>
          {grade !== "" && (
            <>
              <label htmlFor="child-board">Syllabus</label>
              <select id="child-board" value={board} onChange={(e) => setBoard(e.target.value)}>
                {Object.entries(family.boards).map(([value, word]) => (
                  <option key={value} value={value}>
                    {word}
                  </option>
                ))}
              </select>
            </>
          )}
        </>
      )}
      {error && (
        <p className="feedback warn" role="alert">
          {error}
        </p>
      )}
      <div className="row" style={{ marginTop: 12 }}>
        <button type="submit">Save</button>
        <button type="button" className="secondary" onClick={onDone}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function Adults({ family, holder, onChange, onMade }: { family: Family; holder: boolean; onChange: () => void; onMade: (m: Made) => void }) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [relation, setRelation] = useState("father");
  const [error, setError] = useState("");

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      onMade(await post<Made>("/family/adults", { name, email, relation }));
      setAdding(false);
      setName("");
      setEmail("");
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add");
    }
  }

  async function remove(a: Adult) {
    if (!confirm(`Remove ${a.name}? They won't be able to sign in or see the children any more.`)) return;
    await del(`/family/adults/${a.id}`).catch(() => undefined);
    onChange();
  }

  return (
    <section className="card" aria-labelledby="adults">
      <div className="section-head">
        <h2 id="adults">Adults in this family</h2>
        {holder && !adding && (
          <button className="secondary" onClick={() => setAdding(true)}>
            + Add an adult
          </button>
        )}
      </div>
      <ul className="list">
        {family.adults.map((a) => (
          <li key={a.id}>
            <span>
              {a.name}
              {a.you && " (you)"}
              <br />
              <span className="muted">
                {RELATIONS[a.relation] ?? a.relation}
                {a.holder && " · account holder"}
              </span>
            </span>
            {holder && !a.holder && (
              <button className="secondary" onClick={() => remove(a)}>
                Remove
              </button>
            )}
          </li>
        ))}
      </ul>
      {adding && (
        <form onSubmit={invite}>
          <p className="muted">They get their own login and can see every child in the family. Only you can add or remove people.</p>
          <label htmlFor="adult-name">Name</label>
          <input id="adult-name" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} required />
          <label htmlFor="adult-relation">They are the children&apos;s</label>
          <select id="adult-relation" value={relation} onChange={(e) => setRelation(e.target.value)}>
            {Object.entries(RELATIONS).map(([value, word]) => (
              <option key={value} value={value}>
                {word}
              </option>
            ))}
          </select>
          <label htmlFor="adult-email">Their email</label>
          <input id="adult-email" type="email" autoCapitalize="none" value={email} onChange={(e) => setEmail(e.target.value)} required />
          {error && (
            <p className="feedback warn" role="alert">
              {error}
            </p>
          )}
          <div className="row" style={{ marginTop: 12 }}>
            <button type="submit">Add</button>
            <button type="button" className="secondary" onClick={() => setAdding(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function LoginMade({ made, onClose }: { made: Made; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ block: "center" });
  }, [made]);
  return (
    <div ref={ref} className="card sunny" role="status">
      <h2>Login ready for {made.name}</h2>
      <p>
        Login: <strong>{made.login}</strong>
        <br />
        First password: <strong className="mono">{made.temporary_password}</strong>
      </p>
      <p className="muted">Share this in person or by message. They choose their own password the first time they sign in. It won&apos;t be shown again.</p>
      <button className="secondary" onClick={onClose}>
        Done
      </button>
    </div>
  );
}
