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
