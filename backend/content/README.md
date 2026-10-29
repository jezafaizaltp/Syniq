# Content packs

Each YAML file here is one textbook chapter: its topics, an explanation of each topic in four styles, practice questions and tips for common mistakes. SYNiq loads them when the server starts, when the admin is first set up (`python -m app.bootstrap`) and in the demo (`python -m app.seed`).

| Chapter | Topics | Questions |
| --- | --- | --- |
| Maths 1: Pairs of Equations | sum and difference, adding or subtracting equations, making the numbers match, word problems | 31 |
| Maths 2: New Numbers | square roots, lengths like √2, estimating square roots, recurring decimals | 30 |
| Maths 3: Parallel Lines | equally spaced lines, parallel lines and ratios, a line parallel to a side of a triangle, dividing a line in a ratio | 27 |
| Maths 4: Multiplication Identities | multiplying two sums, (a + b)², (a − b)², (a + b)(a − b), quick calculation | 34 |

## Who checked it

Claude wrote these chapters and checked them, because no subject teacher is available to the project yet. Every question is marked "Written and checked by Claude for SYNiq. Not yet reviewed by a school teacher." in the teacher's review screen. In detail:

- **Every answer that can be worked out by computer is**, on every test run: 106 of the 122 questions. Each one carries a `check`, a calculation done a different way from the answer (for example `expand((x + 4)*(x + 5))` for an expansion, or `(34 + 10)/2` for a sum-and-difference problem), and the test fails if the stored answer differs, or if a wrong option of a choice question also turns out to be right.
- The other 16 are choice questions answered in words ("Add them", "5 and 6"). They were checked by hand.
- **The fit with the textbook is not checked.** The chapter names come from the draft syllabus list (`../../content/class9-syllabus-draft.csv`), and the topics from study-guide websites that list each chapter's exercises. A teacher with the 2024 SCERT book should compare topic order and wording when one is available.

## Format

```yaml
subject: math          # subject code
chapter: 1             # textbook chapter number
title: Pairs of Equations   # must match the chapter's title if it already exists

tips:                  # one sentence per mistake tag used below
  forgot_divide: "That is the total for more than one of the unknown. Divide ..."

concepts:
  - code: math9.pairs.sum_difference   # unique, never changed once students use it
    title: Two numbers from their sum and difference
    after: []                          # topics to learn first (codes)
    notes: |                           # what the textbook teaches; grounds the AI tutor
      ...
    explanations:                      # all four styles
      text: "..."
      visual: "..."
      step_by_step: "Step 1: ... Step 2: ..."
      real_world: "..."
    items:
      - prompt: "The sum of two numbers is 34 and their difference is 10. What is the bigger number?"
        answer: "22"
        check: "(34 + 10)/2"           # required for typed answers
        difficulty: 1                  # 1 to 3; every topic needs 1s and 2s
        hints: ["...", "..."]
        solution: "Step 1: ... Step 2: ..."   # shown after a wrong answer, split at Step n:
        mistakes: {"44": forgot_divide}       # a likely wrong answer and its tag
      - prompt: "Expand (x + 5)²."
        options: ["x² + 10x + 25", "x² + 25", "x² + 5x + 25", "x² + 10x + 10"]   # 3 or 4
        answer: "x² + 10x + 25"
        check: "expand((x + 5)^2)"     # optional for choices; compares by value
        ...
```

Typed answers must be numbers (whole, decimal or a fraction like 3/4). Students' answers are accepted however the number is written: 22, 22.0 and 44/2 are all right. Anything else (an expression, a surd, words) is a choice question.

Mistake tags already translated into Malayalam in `backend/app/i18n.py` (`tip.<tag>`) can be used without a tip here. New tags need a tip in the pack, shown in English.

## Changing a pack

```
cd backend
python -m app.content_packs --check   # checks everything, saves nothing
python -m pytest tests/test_content_packs.py
```

The pack is the source of truth for what it loaded. Editing a question's wording replaces it (the old wording is withdrawn, so students no longer see it). Explanations and questions that teachers add in the app are never touched. Changing a pack-loaded question in the app is overwritten the next time the server starts, so change the pack instead.
