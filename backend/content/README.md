# Content packs

Each YAML file here is one textbook chapter: its topics, an explanation of each topic in four styles, practice questions and tips for common mistakes. SYNiq loads them when the server starts, when the admin is first set up (`python -m app.bootstrap`) and in the demo (`python -m app.seed`).

| Chapter | Topics | Questions |
| --- | --- | --- |
| Maths 1: Pairs of Equations | sum and difference, adding or subtracting equations, making the numbers match, word problems | 31 |
| Maths 2: New Numbers | square roots, lengths like √2, estimating square roots, recurring decimals | 30 |
| Maths 3: Parallel Lines | equally spaced lines, parallel lines and ratios, a line parallel to a side of a triangle, dividing a line in a ratio | 27 |
| Maths 4: Multiplication Identities | multiplying two sums, (a + b)², (a − b)², (a + b)(a − b), quick calculation | 34 |
| Maths 5: Irrational Multiplication | multiplying, simplifying, adding and dividing square roots, identities with roots | 35 |
| Maths 6: Similar Triangles | same angles, sides in the same ratio, matching sides, heights, shadows and maps | 25 |
| Maths 7: Negative Numbers | adding and subtracting, multiplying and dividing, putting negatives into expressions, equations with negative answers | 28 |
| Maths 8: Circle Measures | π, circumference, area, half circles and rings | 25 |
| Maths 9: Real Numbers | rational and irrational numbers, the number line, distance between points | 21 |
| Maths 10: Polynomials | terms, coefficients and degree, value of a polynomial, adding, subtracting and multiplying | 19 |
| Maths 11: Parts of Circles | chords and the centre, angles in circles, arcs and sectors | 20 |
| Maths 12: Prisms | volume, surface area, bigger and smaller prisms | 18 |
| Maths 13: Polynomial Pictures | points and coordinates, lines from equations, slope | 18 |
| Maths 14: Proportion | ratios, direct proportion, inverse proportion, sharing in a ratio | 24 |
| Maths 15: Statistics | mean, median, mode, averages from a frequency table | 24 |
| Physics 1: Refraction of Light | bending of light, refractive index, apparent depth, total internal reflection | 24 |
| Physics 2: Equations of Motion | distance and displacement, speed and velocity, acceleration, the three equations, motion graphs | 24 |
| Physics 3: Laws of Motion | inertia, momentum and F = ma, action and reaction, conservation of momentum | 24 |
| Physics 4: Gravitation | the universal law, mass, weight and g, free fall | 19 |
| Chemistry 1: Structure of Atom | protons, neutrons and electrons, isotopes, shells, subshells | 24 |
| Chemistry 2: Periodic Table | groups and periods, finding an element's place, trends | 18 |
| Chemistry 3: Chemical Bonding | octet and valency, ionic bonds, covalent bonds | 18 |
| Chemistry 4: Redox Reactions | oxidation and reduction, oxidation numbers, oxidising and reducing agents | 18 |
| Chemistry 5: Chemical Kinetics | rate of reaction, factors affecting rate, collision theory | 18 |
| Chemistry 6: Solutions | solute and solvent, concentration, solubility, colloids and suspensions | 24 |
| Chemistry 7: Non-Metals | properties, hydrogen, oxygen and ozone, nitrogen and ammonia | 19 |
| Chemistry 8: Organic Chemistry | carbon, alkanes, alkenes and alkynes, naming and functional groups | 19 |
| Biology 1: Life Processes | life processes, photosynthesis, the leaf and gas exchange | 20 |
| Biology 2: Digestion and Transport of Nutrients | digestive system, enzymes, blood and vessels, the heart | 24 |
| Biology 3: Respiration and Excretion | respiration in cells, breathing, the kidneys | 18 |

## Who checked it

Claude wrote these chapters and checked them, because no subject teacher is available to the project yet. Every question is marked "Written and checked by Claude for SYNiq. Not yet reviewed by a school teacher." in the teacher's review screen. In detail:

- **Every answer that can be worked out by computer is**, on every test run: 436 of the 690 questions. Each one carries a `check`, a calculation done a different way from the answer (for example `expand((x + 4)*(x + 5))` for an expansion, or `(34 + 10)/2` for a sum-and-difference problem), and the test fails if the stored answer differs, or if a wrong option of a choice question also turns out to be right.
- The other 254 were checked by hand (most of them in Chemistry and Biology, where many questions are about facts and ideas): choice questions that no single calculation can check, such as "Add them", "Which is the smallest?" or, in science, "Which way does the ray bend?", and a few questions whose answer is read off a list or stated in the question, such as a mode.
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

Mistake tags already translated into Malayalam in `backend/app/i18n.py` (`tip.<tag>`) can be used without a tip here. New tags need a tip in a pack (any pack: tips are shared), shown in English.

## Changing a pack

```
cd backend
python -m app.content_packs --check   # checks everything, saves nothing
python -m pytest tests/test_content_packs.py
```

The pack is the source of truth for what it loaded. Editing a question's wording replaces it (the old wording is withdrawn, so students no longer see it). Explanations and questions that teachers add in the app are never touched. Changing a pack-loaded question in the app is overwritten the next time the server starts, so change the pack instead.
