"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, api, put } from "@/lib/api";
import { useSession } from "@/lib/session";

type SubjectRow = { id: number; name: string; grade: number; syllabus: string };
type SignVideo = { word: string; url: string };
type Topic = { id: number; title: string; videos: SignVideo[] };
type ChapterRow = { chapter: string; topics: Topic[] };

/**
 * Sign-language videos per topic, for deaf students who chose "pictures and text first".
 * A school (or a special educator) records its own Indian Sign Language videos for a topic's
 * key words, or links to a published ISL dictionary entry, and pastes the links here.
 */
export default function SignVideos() {
  const { me, loading } = useSession();
  const router = useRouter();
  const staff = me?.role === "admin" || me?.role === "teacher";
  const [subjects, setSubjects] = useState<SubjectRow[]>([]);
  const [subject, setSubject] = useState("");
  const [chapters, setChapters] = useState<ChapterRow[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!loading && !staff) router.replace("/");
  }, [staff, loading, router]);
  useEffect(() => {
    if (staff) api<SubjectRow[]>("/admin/review-sheet").then(setSubjects).catch(() => setSubjects([]));
  }, [staff]);
  useEffect(() => {
    if (subject) api<ChapterRow[]>(`/admin/signs/${subject}`).then(setChapters).catch(() => setChapters([]));
    else setChapters([]);
  }, [subject]);

  async function save(topic: Topic, videos: SignVideo[]) {
    setMessage("");
    try {
      const r = await put<{ videos: SignVideo[] }>(`/admin/signs/${topic.id}`, { videos });
      setChapters((all) => all.map((c) => ({ ...c, topics: c.topics.map((x) => (x.id === topic.id ? { ...x, videos: r.videos } : x)) })));
      setMessage(`Saved for ${topic.title}.`);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Couldn't save.");
    }
  }

  if (!staff) return null;
  return (
    <div className="wrap">
      <p>
        <Link href="/admin">← School</Link>
      </p>
      <h1>Sign-language videos</h1>
      <p className="muted">
        Deaf students who use &quot;pictures and text first&quot; see these beside each lesson, with a link to the Indian Sign Language
        dictionary from ISLRTC. Add links to your own recorded signs or to a dictionary entry. Links must start with https:// and open
        in a new tab; no student details are sent with them.
      </p>
      <label htmlFor="sign-subject">Subject</label>
      <select id="sign-subject" value={subject} onChange={(e) => setSubject(e.target.value)}>
        <option value="">Choose a subject</option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name} (Class {s.grade})
          </option>
        ))}
      </select>
      {message && (
        <p className="feedback note" role="status">
          {message}
        </p>
      )}
      {chapters.map((c) => (
        <section key={c.chapter} className="card">
          <h2>{c.chapter}</h2>
          {c.topics.map((topic) => (
            <TopicSigns key={topic.id} topic={topic} onSave={save} />
          ))}
        </section>
      ))}
    </div>
  );
}

function TopicSigns({ topic, onSave }: { topic: Topic; onSave: (t: Topic, v: SignVideo[]) => void }) {
  const [word, setWord] = useState("");
  const [url, setUrl] = useState("");
  return (
    <div className="sign-topic">
      <h3>{topic.title}</h3>
      {topic.videos.length > 0 && (
        <ul>
          {topic.videos.map((v, i) => (
            <li key={v.url + i}>
              <a href={v.url} target="_blank" rel="noopener noreferrer">
                {v.word}
              </a>{" "}
              <button className="secondary" onClick={() => onSave(topic, topic.videos.filter((_, j) => j !== i))}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      {topic.videos.length < 10 && (
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            if (!word.trim() || !url.trim()) return;
            onSave(topic, [...topic.videos, { word: word.trim(), url: url.trim() }]);
            setWord("");
            setUrl("");
          }}
        >
          <label className="sr-only" htmlFor={`w-${topic.id}`}>
            Word
          </label>
          <input id={`w-${topic.id}`} placeholder="Word, e.g. fraction" value={word} maxLength={40} onChange={(e) => setWord(e.target.value)} />
          <label className="sr-only" htmlFor={`u-${topic.id}`}>
            Video link
          </label>
          <input id={`u-${topic.id}`} placeholder="https://…" value={url} maxLength={300} onChange={(e) => setUrl(e.target.value)} />
          <button type="submit" className="secondary">
            Add
          </button>
        </form>
      )}
    </div>
  );
}
