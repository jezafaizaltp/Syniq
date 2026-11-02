"use client";

import { useEffect, useRef, useState } from "react";
import { speak } from "@/lib/session";

export type Pic = { pic: string; word: string };
export type Activity = {
  id: string;
  area: string;
  title: string;
  pic: string;
  kind: "name" | "find" | "count";
  items?: (Pic & { say: string })[];
  rounds?: ({ ask: string; options: Pic[]; answer: number } | (Pic & { n: number }))[];
  together: string;
  after: string;
};

const NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five"];

/**
 * One calm activity. Nothing moves or speaks until the child taps; there are no points,
 * no timer they can see, and a wrong tap only hears the right word again.
 */
export function PlayActivity({ activity, onFinished }: { activity: Activity; onFinished: () => void }) {
  const [step, setStep] = useState(0);
  const total = activity.kind === "name" ? activity.items!.length : activity.rounds!.length;

  function next() {
    if (step + 1 >= total) onFinished();
    else setStep(step + 1);
  }

  return (
    <div className="play-stage">
      {activity.kind === "name" && <NameIt key={step} item={activity.items![step]} onNext={next} />}
      {activity.kind === "find" && <FindIt key={step} round={activity.rounds![step] as { ask: string; options: Pic[]; answer: number }} onNext={next} />}
      {activity.kind === "count" && <CountIt key={step} round={activity.rounds![step] as Pic & { n: number }} onNext={next} />}
    </div>
  );
}

function NextButton({ onNext, show }: { onNext: () => void; show: boolean }) {
  return (
    <button className="play-next" onClick={onNext} style={{ visibility: show ? "visible" : "hidden" }} aria-label="Next">
      ➜
    </button>
  );
}

function NameIt({ item, onNext }: { item: Pic & { say: string }; onNext: () => void }) {
  const [heard, setHeard] = useState(false);
  return (
    <>
      <button
        className="play-big"
        onClick={() => {
          speak(item.say);
          setHeard(true);
        }}
        aria-label={item.word}
      >
        <span aria-hidden="true">{item.pic}</span>
      </button>
      <p className="play-word">{heard ? item.word : "Tap me"}</p>
      <NextButton onNext={onNext} show={heard} />
    </>
  );
}

function FindIt({ round, onNext }: { round: { ask: string; options: Pic[]; answer: number }; onNext: () => void }) {
  const [found, setFound] = useState(false);
  const [tried, setTried] = useState<number | null>(null);
  const asked = useRef(false);
  useEffect(() => {
    if (!asked.current) {
      asked.current = true;
      speak(round.ask);
    }
  }, [round.ask]);

  function tap(i: number) {
    const o = round.options[i];
    if (i === round.answer) {
      setFound(true);
      speak(`Yes, the ${o.word}.`);
    } else {
      setTried(i);
      // No buzzer and no "wrong": name what they tapped, then ask again.
      speak(`That's the ${o.word}. ${round.ask}.`);
    }
  }

  return (
    <>
      <button className="play-ask" onClick={() => speak(round.ask)}>
        🔊 {round.ask}
      </button>
      <div className="play-options">
        {round.options.map((o, i) => (
          <button
            key={i}
            className="play-option"
            aria-label={o.word}
            aria-pressed={found && i === round.answer}
            data-dim={found && i !== round.answer ? "yes" : undefined}
            data-tried={tried === i && !found ? "yes" : undefined}
            onClick={() => !found && tap(i)}
          >
            <span aria-hidden="true">{o.pic}</span>
          </button>
        ))}
      </div>
      <NextButton onNext={onNext} show={found} />
    </>
  );
}

function CountIt({ round, onNext }: { round: Pic & { n: number }; onNext: () => void }) {
  const [counted, setCounted] = useState<number[]>([]);
  const done = counted.length === round.n;
  function tap(i: number) {
    if (counted.includes(i)) return;
    const next = [...counted, i];
    setCounted(next);
    speak(next.length === round.n ? `${NUMBER_WORDS[next.length]}. ${NUMBER_WORDS[round.n]} ${round.word}!` : NUMBER_WORDS[next.length]);
  }
  return (
    <>
      <p className="play-word">{done ? `${round.n} ${round.word}` : "Tap each one to count"}</p>
      <div className="play-options">
        {Array.from({ length: round.n }, (_, i) => (
          <button key={i} className="play-option" aria-pressed={counted.includes(i)} aria-label={`${round.word} ${i + 1}`} onClick={() => tap(i)}>
            <span aria-hidden="true">{round.pic}</span>
            {counted.includes(i) && <span className="play-count">{counted.indexOf(i) + 1}</span>}
          </button>
        ))}
      </div>
      <NextButton onNext={onNext} show={done} />
    </>
  );
}

/** A button an adult holds for 2 seconds: easy for a grown-up, not something a toddler does by chance. */
export function HoldButton({ label, onDone }: { label: string; onDone: () => void }) {
  const [holding, setHolding] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const start = () => {
    setHolding(true);
    timer.current = setTimeout(() => {
      setHolding(false);
      onDone();
    }, 2000);
  };
  const stop = () => {
    setHolding(false);
    if (timer.current) clearTimeout(timer.current);
  };
  useEffect(() => stop, []);
  return (
    <button
      className="secondary hold"
      data-holding={holding ? "yes" : undefined}
      onPointerDown={start}
      onPointerUp={stop}
      onPointerLeave={stop}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !holding && start()}
      onKeyUp={stop}
      onContextMenu={(e) => e.preventDefault()}
    >
      {label}
    </button>
  );
}
