# Rewards: stickers and achievements

The owner's design (10 November 2026): reward learning, never time on screen. Nothing is compared with anyone.

## What a learner can earn

**Stars and stickers.** Every few answers a spot-the-mistake puzzle shows a friend's answer with a common mistake in
it. Choosing the right answer earns a star (at most 20 a day, and only once per puzzle). Every 5 stars unlock the next
of 24 stickers (calm pictures from nature and everyday life). Missing the mistake costs nothing: the learner sees the
right answer, the tip, and a gentle "look carefully next time".

**Achievements**, each worked out from the learner's own record (`backend/app/rewards.py`):

| Achievement | Earned when |
| --- | --- |
| Made a topic secure for the first time | the first topic reaches secure |
| Made every topic of a chapter secure | all topics of one chapter are secure |
| Got a harder question right | the first right answer to a difficulty-3 question |
| Fixed a mistake I kept making | a mistake pattern is fixed (3 right on that trap after the last slip) |
| Spotted 10 mistakes | the 10th star |
| Came back to learning after a break | answers again after 7 or more days away |

**Practice days.** My space says "You practised on 3 days this week": days, never minutes. A week with no practice
says "A new week: practise whenever you are ready", never a lost streak.

## Where they show

- **My space**: stickers (with a few locked ones and how many stars to the next), achievements with dates, practice days.
- **Achievement card** (`/space/card`): the learner ticks which achievements to put on it and prints it. Name,
  achievements, stickers. No marks, no levels, nothing that compares.
- **Parent's This week**: new achievements in words.
- **Not shown to teachers** in any class view (a test checks the teacher pages).

## Switching them off

- The **school's default** is on. The admin can switch it off on the School details card.
- A **parent** can switch rewards off or on for their own child (Parent page). The parent's choice wins.
- When off: no stars are counted, My space shows nothing about rewards, the card page says they are off.

## Safety

- A spot answer is only accepted for a puzzle SYNiq gave that learner today, and only its first answer can earn a
  star. At most 60 puzzles a day are handed out; a puzzle never comes back on the same day.
- Nothing is stored for rewards beyond the stars themselves: achievements are recomputed from answers and topic
  progress, so withdrawing a student (which deletes their answers) removes them too. The student data download
  includes the rewards view.
- `tests/test_rewards.py` checks that no reward reads time on screen, sign-ins or answer times.

## Not built (on purpose, for now)

Pooling stickers with friends, shop-style spending, and anything shared outside SYNiq. If they come, they should stay
co-operative (never a leaderboard) and the card should stay the learner's own choice to show.
