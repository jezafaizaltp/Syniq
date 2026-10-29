# How SYNiq responds to answers (no AI needed)

SYNiq has ten ways of responding when a student answers a question. They run on simple rules, so they cost nothing per student. The AI tutor is only suggested when these have not helped after several tries.

Code: `backend/app/engine/responses.py`. Tests: `backend/tests/test_responses.py`.

## Support modes (switched on in Settings)

The student, a parent or a teacher turns these on under **Settings → How SYNiq helps me**. They describe what helps, not a diagnosis. SYNiq never guesses them and never labels a student. Several can be on at once.

| Mode | Setting name shown | Often helps | What changes |
| --- | --- | --- | --- |
| `focus` | Help me stay focused | Students with ADHD or who lose focus easily | One piece at a time behind a "Show me more" button, short steps (at most 4), a quick challenge at the end |
| `easy_read` | Make reading easier | Students with dyslexia | One sentence per line, clearer font, everything read aloud |
| `screen_reader` | I use a screen reader or find pictures hard to see | Blind and low-vision students | Pictures are replaced by the same meaning in words ("10 stars plus 10 stars makes 20"), read aloud |
| `visual_first` | I'm deaf or hard of hearing | Deaf and hard-of-hearing students | Nothing depends on sound; picture explanations are chosen first |
| `tap_to_answer` | Let me tap my answers | Non-speaking students, or students who find typing hard | Number questions show four answers to tap, built from likely mistakes |
| `small_steps` | Show maths with objects and smaller numbers | Students with dyscalculia or other learning differences | Counting pictures first, then a smaller question with the same idea, sooner |

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
