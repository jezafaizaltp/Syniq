"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

/** One A4 page for the lab wall: the address in big letters and the four steps, in English and Malayalam. */
export default function Poster() {
  const { me, loading } = useSession();
  const router = useRouter();
  const [school, setSchool] = useState("");
  useEffect(() => {
    if (!loading && me?.role !== "admin") router.replace("/");
  }, [me, loading, router]);
  useEffect(() => {
    api<{ name: string }>("/school").then((s) => setSchool(s.name));
  }, []);
  if (me?.role !== "admin") return null;
  const site = typeof window === "undefined" ? "" : window.location.origin.replace(/^https?:\/\//, "");
  return (
    <div className="wrap">
      <div className="no-print">
        <p>
          <Link href="/admin">← School setup</Link>
        </p>
        <p className="muted">Print on A4 and put it up in the lab. The address is the one this computer is using now.</p>
        <button onClick={() => window.print()}>Print the poster</button>
      </div>
      <article className="poster">
        {school && <p className="poster-school">{school}</p>}
        <h1>
          SYN<em>iq</em>
        </h1>
        <p className="poster-label">Open the browser and type / ബ്രൗസർ തുറന്ന് ടൈപ്പ് ചെയ്യൂ</p>
        <p className="poster-site">{site}</p>
        <ol>
          <li>
            Type the login and password from your slip.
            <span lang="ml">സ്ലിപ്പിലെ ലോഗിനും പാസ്‌വേഡും ടൈപ്പ് ചെയ്യൂ.</span>
          </li>
          <li>
            The first time, choose your own password and write it in your notebook.
            <span lang="ml">ആദ്യ തവണ, സ്വന്തം പാസ്‌വേഡ് തിരഞ്ഞെടുത്ത് നോട്ട്ബുക്കിൽ എഴുതിവെക്കൂ.</span>
          </li>
          <li>
            Stuck? Press &quot;I need help&quot; and your teacher will come.
            <span lang="ml">സംശയമുണ്ടോ? &quot;I need help&quot; അമർത്തൂ, ടീച്ചർ വരും.</span>
          </li>
          <li>
            At the end, press Sign out.
            <span lang="ml">അവസാനം Sign out അമർത്തൂ.</span>
          </li>
        </ol>
        <p className="poster-foot">No marks. Mistakes help you learn. / മാർക്കില്ല. തെറ്റുകൾ പഠിക്കാൻ സഹായിക്കും.</p>
      </article>
    </div>
  );
}
