"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Person = { id: number; name: string; login: string };
type Student = Person & { guardians: Person[] };
type People = { classes: { id: number; name: string; students: Student[] }[] };

const SCHOOL_KEY = "syniq_letter_school";

/**
 * A letter and consent form for every student, with names filled in, to send home and collect
 * back signed. What the admin then enters on the School page comes from these forms.
 */
export default function Letters() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [people, setPeople] = useState<People | null>(null);
  const [classId, setClassId] = useState<number | "all">("all");
  const [school, setSchool] = useState("");
  const [contact, setContact] = useState("");

  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role === "admin") api<People>("/admin/people").then(setPeople);
    try {
      const saved = JSON.parse(localStorage.getItem(SCHOOL_KEY) ?? "{}");
      setSchool(saved.school ?? "");
      setContact(saved.contact ?? "");
    } catch {
      /* private window */
    }
  }, [me]);
  useEffect(() => {
    try {
      localStorage.setItem(SCHOOL_KEY, JSON.stringify({ school, contact }));
    } catch {
      /* private window */
    }
  }, [school, contact]);

  if (me?.role !== "admin" || !people) return null;
  const classes = people.classes.filter((c) => classId === "all" || c.id === classId);
  const schoolName = school.trim() || "our school";
  const count = classes.reduce((n, c) => n + c.students.length, 0);

  return (
    <div className="wrap wide">
      <div className="no-print">
        <p>
          <Link href="/admin">← School setup</Link>
        </p>
        <h1>Parent letters and consent forms</h1>
        <p className="muted">
          One page per student, with names filled in. Send them home, collect them signed, then tick the same boxes for each
          student on the School page. Keep the signed forms safe: they are your record of consent. Have a lawyer read the
          wording once before the pilot starts.
        </p>
        <label htmlFor="l-school">School name</label>
        <input id="l-school" value={school} onChange={(e) => setSchool(e.target.value)} placeholder="e.g. the school's full name" />
        <label htmlFor="l-contact">Who parents can ask (name and phone or email)</label>
        <input id="l-contact" value={contact} onChange={(e) => setContact(e.target.value)} />
        <label htmlFor="l-class">Class</label>
        <select id="l-class" value={classId} onChange={(e) => setClassId(e.target.value === "all" ? "all" : Number(e.target.value))}>
          <option value="all">All classes</option>
          {people.classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <div className="row" style={{ marginTop: 12 }}>
          <button onClick={() => window.print()}>Print {count} letters</button>
        </div>
      </div>

      {classes.flatMap((c) =>
        c.students.map((s) => (
          <article key={s.id} className="card letter">
            <p className="muted">
              {schoolName} · Class {c.name}
            </p>
            <h2>SYNiq learning pilot: letter to parents</h2>
            <p>Dear {s.guardians.map((g) => g.name).join(" / ") || "parent or guardian"},</p>
            <p>
              {schoolName} is trying SYNiq, a learning app, with some students in Class {c.name}. Students practise in the
              computer lab during school hours. SYNiq notices how each child learns best and changes how it explains things. It
              shows no marks and never ranks children.
            </p>
            <p>
              <strong>What SYNiq keeps:</strong> {s.name}&apos;s answers and how they are getting on with each topic, so lessons
              can adapt. It does not show adverts, sell data or label children. You can see your child&apos;s progress with your
              own login, change these choices there at any time, or ask the school to withdraw your child, which deletes what
              SYNiq has learned about them.
            </p>
            <p>
              <strong>School marks:</strong> to see whether SYNiq helps, the school will compare term-exam marks before and after
              the pilot. Marks are used only for this comparison, are seen only by the school admin, and are never shown to the
              app, teachers in the app, or other families. Results are reported only for groups of five or more.
            </p>
            {contact.trim() && <p>Questions: {contact.trim()}.</p>}

            <h3>Consent form for {s.name}</h3>
            <ul className="boxes">
              <li>
                <span className="box" /> <strong>Learning (needed to take part):</strong> SYNiq may save {s.name}&apos;s
                answers and progress to adapt lessons, and the school may use term-exam marks to compare before and after.
              </li>
              <li>
                <span className="box" /> <strong>Mood check-ins (optional):</strong> SYNiq may save how {s.name} says they feel
                at the start of a lesson. They can always skip it.
              </li>
              <li>
                <span className="box" /> <strong>Share with the school (optional):</strong> {s.name}&apos;s class teacher may see
                which topics they are working on.
              </li>
              <li>
                <span className="box" /> <strong>Thinking puzzles and pace (optional):</strong> short puzzles inside lessons, and
                answer times compared only with {s.name}&apos;s own usual pace. No IQ or score is ever worked out.
              </li>
            </ul>
            <p className="sign-line">Parent or guardian name: ______________________________</p>
            <p className="sign-line">Signature: ______________________ Date: ____________</p>
          </article>
        )),
      )}
    </div>
  );
}
