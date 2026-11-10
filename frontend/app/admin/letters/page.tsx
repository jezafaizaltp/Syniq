"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Person = { id: number; name: string; login: string };
type Student = Person & { guardians: Person[] };
type People = { classes: { id: number; name: string; students: Student[] }[] };

type Vars = { school: string; cls: string; child: string };

const WORDS = {
  en: ({ school, cls, child }: Vars) => ({
    title: "SYNiq learning pilot: letter to parents",
    dear: (parents: string) => `Dear ${parents || "parent or guardian"},`,
    intro: `${school} is trying SYNiq, a learning app, with some students in Class ${cls}. Students practise in the computer lab during school hours. SYNiq notices how each child learns best and changes how it explains things. It shows no marks and never ranks children.`,
    keepsHead: "What SYNiq keeps:",
    keeps: `${child}'s answers and how they are getting on with each topic, so lessons can adapt. It does not show adverts, sell data or label children. You can see your child's progress with your own login, change these choices there at any time, ask the school for a copy of everything SYNiq holds about your child, or ask the school to withdraw your child, which deletes what SYNiq has learned about them.`,
    marksHead: "School marks:",
    marks: "to see whether SYNiq helps, the school will compare term-exam marks before and after the pilot. Marks are used only for this comparison, are seen only by the school admin, and are never shown to the app, teachers in the app, or other families. Results are reported only for groups of five or more.",
    questions: (who: string) => `Questions: ${who}`,
    formTitle: `Consent form for ${child}`,
    boxes: [
      ["Learning (needed to take part):", `SYNiq may save ${child}'s answers and progress to adapt lessons, and the school may use term-exam marks to compare before and after.`],
      ["Mood check-ins (optional):", `SYNiq may save how ${child} says they feel at the start of a lesson. They can always skip it.`],
      ["Share with the school (optional):", `${child}'s class teacher may see which topics they are working on.`],
      ["Thinking puzzles and pace (optional):", `short puzzles inside lessons, and answer times compared only with ${child}'s own usual pace. No IQ or score is ever worked out.`],
    ] as [string, string][],
    signName: "Parent or guardian name: ______________________________",
    signature: "Signature: ______________________ Date: ____________",
  }),
  ml: ({ school, cls, child }: Vars) => ({
    title: "SYNiq പഠന പൈലറ്റ്: രക്ഷിതാക്കൾക്കുള്ള കത്ത്",
    dear: (parents: string) => `പ്രിയപ്പെട്ട ${parents || "രക്ഷിതാവേ"},`,
    intro: `${school}, ${cls} ക്ലാസിലെ ചില കുട്ടികളോടൊപ്പം SYNiq എന്ന പഠന ആപ്പ് പരീക്ഷിക്കുകയാണ്. സ്കൂൾ സമയത്ത് കമ്പ്യൂട്ടർ ലാബിലാണ് കുട്ടികൾ പരിശീലിക്കുക. ഓരോ കുട്ടിയും എങ്ങനെയാണ് നന്നായി പഠിക്കുന്നത് എന്ന് SYNiq ശ്രദ്ധിക്കുകയും, അതനുസരിച്ച് വിശദീകരിക്കുന്ന രീതി മാറ്റുകയും ചെയ്യും. ഇത് മാർക്ക് കാണിക്കുന്നില്ല, കുട്ടികളെ റാങ്ക് ചെയ്യുന്നുമില്ല.`,
    keepsHead: "SYNiq സൂക്ഷിക്കുന്നത്:",
    keeps: `പാഠങ്ങൾ കുട്ടിക്ക് അനുയോജ്യമാക്കാൻ, ${child}-ന്റെ ഉത്തരങ്ങളും ഓരോ വിഷയത്തിലെ പുരോഗതിയും. പരസ്യങ്ങൾ കാണിക്കുകയോ വിവരങ്ങൾ വിൽക്കുകയോ കുട്ടികൾക്ക് ലേബൽ നൽകുകയോ ചെയ്യില്ല. നിങ്ങളുടെ സ്വന്തം ലോഗിനിൽ കുട്ടിയുടെ പുരോഗതി കാണാം, ഈ തീരുമാനങ്ങൾ എപ്പോൾ വേണമെങ്കിലും മാറ്റാം, SYNiq കുട്ടിയെക്കുറിച്ച് സൂക്ഷിക്കുന്ന എല്ലാ വിവരങ്ങളുടെയും പകർപ്പ് സ്കൂളിനോട് ചോദിക്കാം, അല്ലെങ്കിൽ കുട്ടിയെ പിൻവലിക്കാൻ ആവശ്യപ്പെടാം; അപ്പോൾ SYNiq കുട്ടിയെക്കുറിച്ച് മനസ്സിലാക്കിയതെല്ലാം മായ്ക്കും.`,
    marksHead: "സ്കൂൾ മാർക്കുകൾ:",
    marks: "SYNiq സഹായിക്കുന്നുണ്ടോ എന്നറിയാൻ, പൈലറ്റിന് മുമ്പും ശേഷവുമുള്ള ടേം പരീക്ഷാ മാർക്കുകൾ സ്കൂൾ താരതമ്യം ചെയ്യും. ഈ താരതമ്യത്തിന് മാത്രമാണ് മാർക്കുകൾ ഉപയോഗിക്കുക; സ്കൂൾ അഡ്മിൻ മാത്രമേ അവ കാണൂ. ആപ്പിനോ, ആപ്പിലെ അധ്യാപകർക്കോ, മറ്റ് കുടുംബങ്ങൾക്കോ ഒരിക്കലും കാണിക്കില്ല. അഞ്ചോ അതിലധികമോ കുട്ടികളുള്ള ഗ്രൂപ്പുകളുടെ ഫലം മാത്രമേ റിപ്പോർട്ട് ചെയ്യൂ.",
    questions: (who: string) => `സംശയങ്ങൾക്ക്: ${who}`,
    formTitle: `${child}-നുള്ള സമ്മതപത്രം`,
    boxes: [
      ["പഠനം (പങ്കെടുക്കാൻ ആവശ്യം):", `പാഠങ്ങൾ അനുയോജ്യമാക്കാൻ ${child}-ന്റെ ഉത്തരങ്ങളും പുരോഗതിയും SYNiq-ന് സൂക്ഷിക്കാം; മുമ്പും ശേഷവും താരതമ്യം ചെയ്യാൻ സ്കൂളിന് ടേം പരീക്ഷാ മാർക്കുകൾ ഉപയോഗിക്കാം.`],
      ["മൂഡ് ചെക്ക്-ഇൻ (ഐച്ഛികം):", `പാഠം തുടങ്ങുമ്പോൾ ${child} പറയുന്ന മാനസികാവസ്ഥ SYNiq-ന് സൂക്ഷിക്കാം. കുട്ടിക്ക് എപ്പോഴും ഇത് ഒഴിവാക്കാം.`],
      ["സ്കൂളുമായി പങ്കുവെക്കൽ (ഐച്ഛികം):", `${child} ഏതൊക്കെ വിഷയങ്ങളിലാണ് പഠിക്കുന്നതെന്ന് ക്ലാസ് ടീച്ചർക്ക് കാണാം.`],
      ["ചിന്താ പസിലുകളും വേഗതയും (ഐച്ഛികം):", `പാഠങ്ങൾക്കിടയിൽ ചെറിയ പസിലുകൾ; ഉത്തരം നൽകാനെടുക്കുന്ന സമയം ${child}-ന്റെ സ്വന്തം സാധാരണ വേഗതയുമായി മാത്രം താരതമ്യം ചെയ്യും. IQ-വോ സ്കോറോ ഒരിക്കലും കണക്കാക്കില്ല.`],
    ] as [string, string][],
    signName: "രക്ഷിതാവിന്റെ പേര്: ______________________________",
    signature: "ഒപ്പ്: ______________________ തീയതി: ____________",
  }),
};

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
  const [lang, setLang] = useState<"en" | "ml">("en");

  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    if (me?.role !== "admin") return;
    api<People>("/admin/people").then(setPeople);
    api<{ name: string; contact: string }>("/admin/school").then((d) => {
      setSchool(d.name);
      setContact(d.contact);
    });
  }, [me]);

  if (me?.role !== "admin" || !people) return null;
  const classes = people.classes.filter((c) => classId === "all" || c.id === classId);
  const schoolName = school.trim() || (lang === "ml" ? "ഞങ്ങളുടെ സ്കൂൾ" : "our school");
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
        <input id="l-school" value={school} onChange={(e) => setSchool(e.target.value)} placeholder="Set it once under School details" />
        <label htmlFor="l-contact">Who parents can ask (name and phone or email)</label>
        <input id="l-contact" value={contact} onChange={(e) => setContact(e.target.value)} />
        <label htmlFor="l-lang">Language</label>
        <select id="l-lang" value={lang} onChange={(e) => setLang(e.target.value as "en" | "ml")}>
          <option value="en">English</option>
          <option value="ml">മലയാളം (Malayalam, not yet checked by a native teacher)</option>
        </select>
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
        c.students.map((s) => {
          const w = WORDS[lang]({ school: schoolName, cls: c.name, child: s.name });
          const parents = s.guardians.map((g) => g.name).join(" / ");
          return (
            <article key={s.id} className="card letter" lang={lang}>
              <p className="muted">
                {schoolName} · {c.name}
              </p>
              <h2>{w.title}</h2>
              <p>{w.dear(parents)}</p>
              <p>{w.intro}</p>
              <p>
                <strong>{w.keepsHead}</strong> {w.keeps}
              </p>
              <p>
                <strong>{w.marksHead}</strong> {w.marks}
              </p>
              {contact.trim() && <p>{w.questions(contact.trim())}</p>}
              <h3>{w.formTitle}</h3>
              <ul className="boxes">
                {w.boxes.map(([head, text]) => (
                  <li key={head}>
                    <span className="box" /> <strong>{head}</strong> {text}
                  </li>
                ))}
              </ul>
              <p className="sign-line">{w.signName}</p>
              <p className="sign-line">{w.signature}</p>
            </article>
          );
        }),
      )}
    </div>
  );
}
