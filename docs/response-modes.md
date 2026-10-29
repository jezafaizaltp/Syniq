# How SYNiq responds to answers (no AI needed)

SYNiq has ten ways of responding when a student answers a question. They run on simple rules, so they cost nothing per student. The AI tutor is only suggested when these have not helped after several tries.

Code: `backend/app/engine/responses.py`. Tests: `backend/tests/test_responses.py`.

## Support modes

Support modes change how every response is presented. They describe what helps, never a condition: SYNiq never names or suggests ADHD, dyslexia or any other diagnosis.

### Noticed from answers

SYNiq switches these on by itself when a student's answers show a clear pattern (code: `backend/app/engine/detect.py`). It never decides from fewer than 10 answers, never from a single answer, and never from how fast the student answered. When one switches on, the student is told why, and can switch it off in Settings. Once switched off, SYNiq never turns it back on. Each switch is logged as a decision (`A_<mode>`) with its evidence, and parents can see it with the reason.

| Mode | What changes | Switched on when |
| --- | --- | --- |
| `focus` | One piece at a time behind "Show me more", at most 4 steps, a quick challenge | Answers slip in the second half of a session, in 2 or more sessions of 6+ answers; or 3+ "take a break" presses in two weeks |
| `easy_read` | One sentence per line, clearer font, read aloud | Long questions (15+ words) are answered right at least 30 points less often than short ones (4+ of each); or 3+ read-aloud presses in two weeks |
| `small_steps` | Counting pictures first, then a smaller question sooner | 3+ counting or number-step slips in the last 20 answers; or answers after pictures are right much more often (40+ points) than after worded explanations |

### Chosen by a parent (or the student)

Sight, hearing and speech can't be read from answers, so a parent ticks them on the parent page. The student can also set them in Settings.

| Mode | Shown as | What changes |
| --- | --- | --- |
| `screen_reader` | Uses a screen reader or finds pictures hard to see | Pictures are replaced by the same meaning in words ("10 stars plus 10 stars makes 20"), read aloud |
| `visual_first` | Is deaf or hard of hearing | Nothing depends on sound; picture explanations are chosen first |
| `tap_to_answer` | Taps answers instead of typing or speaking | Number questions show four answers to tap, built from likely mistakes |

## Answer-driven modes (picked automatically)

Each time the same topic goes wrong in a row, the response gets more concrete:

| Wrong in a row | Mode | What the student sees |
| --- | --- | --- |
| 1st | `count_it_out` | What went wrong, in words, plus a picture. For 10 + 10 answered 15: ⭐×10 + ⭐×5 = 15 (what you wrote) and ⭐×10 + ⭐×10 = 20 (the right way) |
| 2nd | `step_by_step` | The worked solution, one step per line |
| 3rd | `real_life` | The same idea as a story ("You have 10 mangoes. Your friend gives you 10 more…") |
| 4th and after | `try_similar` | A smaller question with the same idea (5 + 5) to try straight away, plus a note that the AI tutor can help, if it is switched on |

For algebra and other questions that can't be drawn with objects, the first response is the worked steps, and the picture and story come from the teacher-approved explanations for that topic.

## Mistakes SYNiq can name in sums

For whole-number +, −, × and ÷ questions it spots: took away instead of adding (and the reverse), multiplied instead of adding, one group too many or too few, counted only one group, off by one, digits swapped, and a slip in the tens. Teachers don't need to tag anything: SYNiq reads the sum from the question and checks it against the answer.

Numbers up to 20 are drawn as stars. Bigger numbers (up to 100) use 🟦 for each ten and ⭐ for each one.

## Every response is logged

Each response is recorded as an adaptation decision (rule `F_<mode>`, version `2026.10-1`) with the reason, just like the rest of the engine, so teachers and audits can see why SYNiq chose it.

## Ideas for later

- More stories and pictures for fractions, decimals and algebra tiles.
- Malayalam versions of every message.
- Sign-language video clips for deaf students, made with a teacher.
