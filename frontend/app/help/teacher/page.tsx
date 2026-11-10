import Link from "next/link";

export const metadata = { title: "A lab period with SYNiq" };

/** For class teachers: one lab period, step by step. Plain page, readable without signing in. */
export default function TeacherHelp() {
  return (
    <div className="wrap help-page">
      <p>
        <Link href="/teacher">← Your class</Link>
      </p>
      <h1>A lab period with SYNiq</h1>
      <p className="muted">About 40 minutes. You don&apos;t need to teach the app; it explains each topic itself.</p>

      <h2>Before the students come in</h2>
      <ol>
        <li>Switch on the lab computer that runs SYNiq at least 10 minutes early, and run the lab check.</li>
        <li>
          On your <strong>Class</strong> page, choose <strong>Today&apos;s chapter</strong> if you want everyone on the same
          chapter. Students see it first. It clears itself tomorrow.
        </li>
      </ol>

      <h2>First five minutes</h2>
      <ol>
        <li>Students sign in with their own login. New students use the slip, then choose their own password.</li>
        <li>
          Forgotten password? Open <strong>Today in the lab</strong>, then <strong>All students</strong>, and press{" "}
          <strong>New password</strong>. Read the new one to the student; they choose their own straight after.
        </li>
        <li>
          <strong>Not signed in yet</strong> on the panel shows who still needs help getting in.
        </li>
      </ol>

      <h2>During the period</h2>
      <ul>
        <li>
          A student who presses <strong>I need help</strong> appears at the top of Today in the lab, oldest first, with the
          topic. Press <strong>Helped</strong> when you have been to them. The panel refreshes by itself every 30 seconds.
        </li>
        <li>
          Let students make mistakes. SYNiq shows their answer next to the right one and a clue; the mistake is the way in.
        </li>
        <li>There are no marks and no rankings. Please don&apos;t compare students out loud.</li>
        <li>
          <strong>May need a hand</strong> and <strong>Mistakes that keep coming back</strong> show who to sit with. Print a
          re-teach sheet for a short small-group session.
        </li>
      </ul>

      <h2>Last five minutes</h2>
      <ol>
        <li>Students press Sign out. They see what they did today first.</li>
        <li>
          Then press <strong>End lab period: sign everyone out</strong>, so the next class can&apos;t open their accounts.
        </li>
      </ol>

      <h2>What you can and can&apos;t see</h2>
      <p>
        You see topic progress only for students whose families agreed to share it with the school. You never see marks,
        mood check-ins, notes or goals. A raised hand always reaches you, because the student asked for you.
      </p>
    </div>
  );
}
