# Simulated learners

`backend/tools/learner_sim.py` runs simulated students through the Kerala Class 9 lab install, using the real API the
same way the browser does. It is a check on the **engine**, not on real children: each simulated learner behaves the
way the file says learners behave, so it can show whether SYNiq adapts as intended, but not whether real students learn
more. The pilot answers that.

## How it works

- Five chapters: Maths 1 and 2, Physics 1, Biology 1, Social Science 1 (18 topics).
- 15 lab periods of 30 steps each (an explanation read or a question answered is one step), with 1 to 3 days off
  between periods. A test 14 days after the last period measures what was kept.
- Each learner has hidden knowledge of each topic. Explanations teach a share of what's missing, by how well that style
  suits them. Mistakes teach a little, more when the help after the mistake suits them. Knowledge fades between periods,
  more slowly once it has been practised on different days. Question traps catch careless learners, and a trap is
  learnt faster when a tip is shown.
- The **test score** is the expected mark on every question of the five chapters, with no hints.
- The same learner also goes through a **fixed version**: the text explanation, six questions, the next topic, round
  and round, for the same number of steps.

| Learner | How they learn (the simulation's assumption) |
| --- | --- |
| Meera | Learns best from pictures; long text doesn't stick |
| Arjun | Slow and careful, needs one step at a time |
| Zara | Quick and already knows a lot, but rushes and falls into traps |
| Vishnu | Finds reading hard, starts with gaps, learns from everyday examples, attention fades |
| Control | Every way of explaining works the same (adapting can't help; it must not hurt) |

## Results (November 2026, 5 runs each)

Test scores, before → after the 15 periods → two weeks later:

| Learner | SYNiq at first | After fix 1 | After fix 2 | Fixed version |
| --- | --- | --- | --- | --- |
| Meera | 33 → 45 → 37 | 33 → 50 → 39 | 33 → 52 → 41 | 33 → 48 → 37 |
| Arjun | 26 → 42 → 31 | 26 → 46 → 34 | 26 → 50 → 35 | 26 → 46 → 32 |
| Zara | 33 → 48 → 43 | 33 → 52 → 46 | 33 → 54 → 47 | 33 → 49 → 40 |
| Vishnu | 22 → 41 → 28 | 22 → 45 → 29 | 22 → 48 → 32 | 22 → 35 → 25 |
| Control | 34 → 45 → 38 | 34 → 51 → 41 | 34 → 51 → 41 | 34 → 56 → 41 |

### Fix 1: what was wrong

- **Topics were called secure far too early.** Three right multiple-choice answers in a row were enough, so a learner
  who knew a topic only half-way could get there by luck. 4 to 12 of the 18 topics were marked secure while hidden
  knowledge was under 70%, and then SYNiq had nothing more to give: up to 40% of lab time went unused. The plain fixed
  version beat SYNiq for three of the five learners.
  Fix (`engine/mastery.py`): learning per answer 0.15 → 0.08, secure at 0.98 instead of 0.95, at least 5 answers
  instead of 3, first review the next day instead of after 2 days.
- **The same question came back within one period** while the topic had others. Now a question answered in the last
  12 hours is not asked again while others are left, and the least recently seen comes first (`learning.pick_item`).

After fix 1 SYNiq was as good as or better than the fixed version for every learner two weeks later. The gains were
largest for Zara (the mistake tips and watch-out nudges fix her traps) and Vishnu (more practice where he struggles,
hints, and everyday examples).

### Fix 2: the weak spots fix 1 left

- **Forgetting.** Spaced reviews only came up when the student opened that same chapter again, so a topic from last
  week's chapter was never reviewed. Now each sitting brings in up to 4 reviews from the student's other chapters
  (`learning.other_review`, rule `R3_other_chapter`): topics that are due, and topics that were secure once and have
  slipped since. Two weeks later every learner keeps more, most of all Vishnu (29% → 32%).
- **Running out of questions.** When every question of a topic has been answered in this sitting, the topic waits and
  SYNiq moves to another open topic in the chapter (`set_aside` in `engine/rules.py`). Repeats within a period roughly
  halved (Vishnu 118 → 59).
- **Judging which way of explaining helps.** Answers after an explanation are now compared with what was expected from
  what the learner knew just before it (`expected` in the method counts), so an explanation is no longer blamed for
  coming when the topic was new or hard. After each explanation the learner can also tap "👍 Yes, I get it" or
  "🤔 Not really"; that counts too (`POST /learn/explanation-feedback`).

### Still weak

- **Finding each learner's way is still barely better than chance** in these runs (20–40% of explanations in their best
  way, against 25% by chance; Meera's first explanations are the exception at 60%). The fairer judging and the taps did
  not move it much over 18 topics. The most reliable signal is the learner's own choice: "How I like things explained"
  in Settings is used first when set.
- **4 to 14 topics are still marked secure while hidden knowledge is under 70%.** The reviews now catch slipped topics
  and bring them back, which is why scores two weeks later still rose.
- **Ten or so questions per topic is still not enough** for learners who need a lot of practice. Switching topics
  halves the repeats, but more questions are the real fix.
- **Forgetting is still large**: about a third of the gain is lost in two weeks without practice.

## Running it

```
cd backend
python -m tools.learner_sim --seed 1 --out /tmp/sim-1.json   # about 2–3 minutes, fresh database
python -m tools.learner_sim --summarise "/tmp/sim-*.json"
```

Engine settings can be tried without changing code: `SIM_P_TRANSIT`, `SIM_MIN_ATTEMPTS`, `SIM_SECURE`,
`SIM_REVIEW_DAYS` (for example `1,3,7,21,60`), `SIM_CAPS` (method-matching caps) and `SIM_TAPS=0` (learners don't
answer "did this help?").
