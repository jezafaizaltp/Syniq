# Thinking puzzles and own pace

Short brain teasers appear inside lessons, and answer times are compared with the child's own usual pace. Both are used only to teach the child better. Code: `backend/app/thinking.py` (pure rules), `backend/app/routers/thinking.py`, `frontend/app/learn/page.tsx`.

## Switched on by the parent

Nothing here runs without the consent scope `thinking_puzzles`:

- the parent page has a "Thinking puzzles and pace" switch;
- the admin sheet has an optional `consent_puzzles` column (older sheets without it still import, as "no");
- an admin can tick it for paper consent.

Without consent, no puzzle is shown, no puzzle answer is stored, and answer times are not used for anything. They are still saved with each answer, as before, and never used to set levels.

### Line for the paper consent form

> **Thinking puzzles and pace (optional).** During lessons your child may see short brain-teaser puzzles (patterns, number sequences, odd one out, word links), and the time your child takes to answer is compared only with their own usual pace. SYNiq uses this to choose how to explain things and when to offer a break. No IQ or score is worked out, your child is never compared with other children, and you can switch this off at any time on your parent page. ☐ Yes ☐ No

Have a lawyer check this wording before charging money for SYNiq.

## The puzzles

| Kind | Levels | Who gets it |
| --- | --- | --- |
| Patterns ("what comes next?" with emoji) | ABAB, ABCABC, AABC | everyone |
| Number sequences | +1/2/5/10; +3..9 or take away; doubling, squares, growing gaps | everyone |
| Odd one out | 3 or 4 of a kind (fruit, animals, vehicles…) plus one; times-table numbers | everyone |
| Word links ("hot goes with cold, up goes with …?") | three levels of word pairs | Class 3 and up |

- Puzzles are made from a seed, so the server checks answers without storing puzzles.
- The level goes up after two right in a row in that kind of puzzle and down after a miss. LKG to Class 5 start at level 1; Class 6 and up start at level 2.
- **When puzzles appear:** one at the start of a lesson if one is due, then one every 8 answers if one is due.
  - The first 2 of each kind make up a start set, at up to 4 a day.
  - After that, at most 2 a day.
- To the child, each puzzle is a "Brain teaser" with a friendly reply ("Nice thinking!" or "Good try!") and why the answer is right. There is no score, no timer on screen and no test wording. The app never receives the kind or level.

## What the results change

- **The first explanation of a new topic.** When one kind of puzzle is clearly the child's strongest, it moves one way of explaining to the front:
  - patterns or odd one out → the picture explanation;
  - numbers → step by step;
  - word links → explanation in words.

  "Clearly" means at least 4 answers in two or more kinds, with the top kind clearly ahead. This only applies until the child's own answers after explanations show what works (`engine/methods.py`), and evidence from other learners on the topic still counts. Logged as `puzzle_lean` in the decision.
- **Parents** see, per kind, "just started", "steady" or "getting stronger", compared only with the child's own earlier puzzles. They never see a number.

## Own pace

- A break is offered when the child's last 4 answers in this sitting were each more than twice as slow as their usual time (the median of their earlier answers, once there are at least 15) and at least 2 of the 4 were wrong.
- Slow but right is fine: thinking hard is not a problem.
- A slow-and-steady child is never flagged, because they are compared only with themselves.
- The offer is not repeated within 20 minutes of a break or an earlier offer. It is logged as `P_pace_break`.
- Speed never changes the level of questions and is never used to judge ability.

## What this never does

- Work out an IQ or any other number about the child.
- Rank children or compare them with each other.
- Show anything about puzzles to teachers.
