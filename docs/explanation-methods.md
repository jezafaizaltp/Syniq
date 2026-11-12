# Matching students to the ways of explaining that work for them

Every topic has four explanations: in words, with a picture, step by step and
with a real-life example. SYNiq learns which of these helps each student, and
starts each new topic with the one most likely to work.

## How it learns

After an explanation, the next three answers on that topic count for it: right
answers say it helped, wrong ones say it didn't yet. The server decides which
explanation an answer belongs to (the last one shown on that topic), so the
counts can't be thrown off by the app.

## How it chooses

When a new topic starts (rule R4), or a student gets two wrong in a row (rule
R2), the engine (`backend/app/engine/methods.py`) scores each method from:

1. this topic, for this student: the strongest evidence;
2. the same subject, for this student (counts at most as much as 6 answers);
3. the student's other subjects (at most as much as 3 answers);
4. this topic, for **learners who learn in a similar way**: other students
   whose clearest method is the same as this student's (at most as much as 4
   answers). Until a student's own pattern is clear, all learners on the topic
   count instead.

The caps mean what happens on the topic itself always wins: two answers here
outweigh fifty elsewhere. With no evidence at all, it starts in words, as
before.

Rules that always hold:

- A choice the student or parent made in settings (`preferred_style`, or
  pictures first for a deaf or hard of hearing student) comes first.
- After two wrong answers, the student always gets a method not yet tried on
  that topic.
- The student can switch to any method at any time.
- Every choice is logged with why (`method_why` in the decision evidence:
  `preferred`, `this_topic`, `history`, `similar`, `everyone` or `default`), and
  the student sees one line saying why, for example "Pictures first, since this
  has helped you before."

## Inside each lesson

A new topic is taught first, one idea at a time. A lesson step can be written
in more than one way (`ways` in the pack, see `backend/content/README.md`,
"Lessons"). The same scores order each step's ways for each learner
(`learning.style_order`), so a learner whose answers go well after real-life
examples sees the real-life way first.

- "Explain another way" shows the next way at any time.
- A wrong check answer is not the end of the idea: the next way appears, the
  answer they tried is set aside, and they get one more try before the answer
  and the reason are shown.
- "I know some of this: check me first" turns it round: the check comes first,
  and the teaching opens only for ideas they miss. The lesson starts this way
  by itself when there is real evidence the learner knows some of it (a right
  answer in the start check, or the lesson done before and remembered:
  `learning.lesson_check_first`), but never while they are stuck on the topic.
  It says why, and "Teach me each idea first" is always one tap away.
- Credit: a wrong first answer counts against the way on screen; a right
  answer on the second try, or after the learner asked for another way, counts
  for that way. These go into the same per-topic counts as the "did this
  help?" taps, so the next lesson and the next first explanation adapt.
- At the end, the learner sees how many ideas they got first time and which
  way helped with which idea. Nothing is marked.

Teachers see the other side on the re-teach sheet (`GET
/teacher/classes/{id}/lesson-trouble`): lesson ideas that half or more of the
students who reached them missed the first time, with the idea's check and,
where one stands out, the way of explaining that helped most on the second try.
Counts only, never names.

## The mentor

The student's home page opens with their mentor (`app/mentor.py`, `GET
/me/mentor`): a hello for the time of day in India, at most three next steps,
most useful first, the learner's own goal from My space that comes due first,
and what went well this week.

1. A mistake made more than once and not fixed yet (a few questions that
   catch it; three right and it is fixed).
2. A topic stuck right now (three wrong in a row): learn it again another way.
3. The topic most overdue for revision.
4. Carry on: the next topic not yet secure in the chapter they worked on last,
   or the next chapter; a brand-new learner is asked to pick a subject.

"This week" lists only good news that is true: days practised, topics made
secure, repeated mistakes fixed, lessons finished, times they got something
wrong and later right, and the way of explaining that has helped most lately.
Never marks, ranks or comparisons with anyone else.

When the learner signs out, "Before you go" (`GET /me/today`) says back what
they did today, lessons included, and the mentor's most useful step to start
with next time.

Parents see the same good news on My children, in their own words
(`mentor.growth`, part of `GET /guardian/children/{id}/week`): lessons finished,
topics made secure, repeated mistakes fixed, times the child got past a wrong
answer, and the way of explaining that has helped most lately.

## What people see

| Who | Where | What |
|---|---|---|
| Student | My space, "What helps you learn" | per subject: right X of Y times just after each method, and the clearest one lately |
| Parent | My children | the same, for each child |
| Specialist (if a parent shares) | Specialist view | the same |
| Teacher | Your class, "How students learn best right now" | per subject, students grouped by the method that helps them most; others counted as "still finding out" |

A method is only described after at least 3 answers following it, and a
"clearest" method needs at least 6 answers in that subject and a real gap over
the next best. Groups are by how students learn, never by marks. They change
as students answer and are never labels.

## Adding more ways of explaining

Methods are listed once, in `STYLES` in `engine/methods.py`. A new style needs
an explanation of that style in the content packs, a word for it in
`frontend/lib/i18n.ts` (`style.*` and `method.*`) and in `METHOD_WORDS` /
`STYLE_WORDS` in `frontend/lib/api.ts`. The matcher handles any number of
styles.
