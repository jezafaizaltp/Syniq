# How SYNiq responds to answers (no AI needed)

SYNiq has ten ways of responding when a student answers a question. They run on simple rules, so they cost nothing per student. The AI tutor is only suggested when these have not helped after several tries.

Code: `backend/app/engine/responses.py`. Tests: `backend/tests/test_responses.py`.

## Every wrong answer shows the mistake

Before any of the modes below, a wrong answer puts the learner's own answer next to the right one ("You said 7 · The answer 20"). Small whole numbers (up to 20) are also drawn as dots in groups of five, so the gap can be counted. Then the topic's own picture follows; on a number line, both answers are marked on it. The mistake is the way into the concept, without handing over a worked solution first.

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

Sight, hearing, speech, movement and how a child copes with change can't be read from answers, so a parent ticks them on the parent page ("Help you can switch on"). The student can also set them in Settings. None of them is a label: each says what helps.

| Mode | Shown as | What changes |
| --- | --- | --- |
| `screen_reader` | Uses a screen reader or finds pictures hard to see | Pictures are replaced by the same meaning in words ("10 stars plus 10 stars makes 20"), read aloud |
| `visual_first` | Is deaf or hard of hearing | Nothing depends on sound; picture explanations are chosen first |
| `tap_to_answer` | Taps answers instead of typing or speaking | Number questions show four answers to tap, built from likely mistakes |
| `calm` | Likes calm lessons that go the same way every time | A picture plan (Learn, Practise, Finish) with the time chosen; no surprise brain teasers or spot-the-mistake; nothing moves; the lesson never changes shape without warning |
| `motor` | Finds tapping, typing or keeping a hand steady hard | Bigger buttons with more space; number questions become answers to tap; on a keyboard or switch, keys 1 to 9 pick an answer, Enter checks it, and the Next button takes focus so one press moves on |
| `listen` | Is blind or finds the screen hard to see, without a screen reader | SYNiq speaks everything itself, for lab computers with no screen reader: each question with its numbered choices, the explanation with its picture described, what was chosen, a short sound and the result (yours against the right answer). Number keys choose, Enter checks or moves on, R repeats, H gives a hint. Number questions become choices, so nothing has to be typed blind |
| `talk_board` | Finds speaking up or asking out loud hard | A board of picture buttons: I need help, I don't understand, I need a break, It's too loud, I've finished, Toilet please, I feel upset. In a class it tells the teacher (their Today panel shows what is needed); at home it shows the need big, to point at |
| `fewer_choices` | Does better with fewer answers to choose from | Two choices instead of four: the right answer and the mistake the question expects most, so the choice still teaches |
| `maths_helper` | Finds it hard to hold numbers in their head | A number line (0-20, or 0-100 in tens) and counters in rows of ten beside every number question. Buttons only; it never checks or gives the answer. Also offered when SYNiq has noticed pictures and smaller numbers help (`small_steps`) |

These often help autistic children (`calm`, `talk_board`), children with cerebral palsy or other movement difficulties (`motor`), blind children (`listen`), non-speaking children (`talk_board`), and children with learning disabilities such as dyscalculia (`maths_helper`, `fewer_choices`), but SYNiq never says so: they are offered to anyone they help.

### Sign language for deaf learners

Students with `visual_first` see an "In sign language" card beside every lesson: links to Indian Sign Language videos for the topic's key words, and a link to the national ISL dictionary from ISLRTC. Schools add the videos per topic on **School → Sign-language videos** (`/admin/signs`): their own recordings or dictionary entries, https links only, up to 10 per topic, opened in a new tab with nothing about the student sent. SYNiq doesn't ship sign videos itself: signing must come from Deaf signers, not from a machine.

### Strengths and talents (every child)

My space shows **Your strengths** and the parent page **Where {name} shines** (`app/strengths.py`). Four signals, each against the child's own record, never against other children:

- a subject where first-try answers are clearly better than in the child's other subjects (at least 15 answers in each of two subjects, at least 60% and 10 points above their own overall rate);
- thinking-puzzle kinds that are growing (only with the parent's thinking-puzzles consent);
- Explore areas they loved: making, fixing, finding out, people, ideas, and now movement and sport, nature and animals, technology and building;
- using the hands-on activities a lot.

Each strength comes with ways to grow it at home (low cost, including para-sport and adapted games), the next Explore activity in that area, and always something new to try so nobody is boxed in. No scores, no ranks, no "gifted" label. Every Explore activity says it can be done by touch, by sound, sitting down, by talking it through, or with a helper doing the hands while the child leads.

### Reading help for everyone (Settings)

- **Easier-to-read text**: a rounder font (Lexend) with more space.
- **More space between letters and lines**: wider letter, word and line spacing.
- **Page colour**: cream, soft blue, green or pink instead of white. Some readers find this easier; it is a comfort setting, not a treatment.
- **Read-along**: whenever SYNiq reads a lesson or question aloud, the word being read is highlighted, so the child can follow. Works in browsers that report word positions (Chrome, Edge, Safari); others just read without the highlight.

### A gentle note for parents (never a label)

Owner's choice, 2026-11-07. SYNiq never tells anyone a child might have dyslexia, ADHD, autism or any other condition: it can't know, and a wrong guess harms. But when a child has kept finding the work hard for weeks, even after SYNiq changed how it teaches, the parent sees one calm note: there may be a simple reason (eyesight, hearing, or the way a child takes in reading, numbers or instructions), a free check is available at the government District Early Intervention Centre (DEIC, RBSK) at the district hospital, the school or a children's doctor, and SYNiq doesn't diagnose anything.

The rule (`backend/app/engine/checkup.py`), all of it needed: at least 80 answers spread over at least 28 days; then in the last 28 days either fewer than half right, or SYNiq has turned on two or more kinds of help and the child is stuck on 3 or more topics. It never uses answer speed, mood check-ins or puzzles. The child never sees the note. The parent can hide it; it stays hidden for 180 days (kept on the parent's account, not the child's). A test checks the note's words never name a condition.

### Screen-reader check (2026-11-07)

Every page (sign-in, sign-up, home, subjects, chapters, check-in, brain teaser, lesson, question, answer feedback, My space, Explore, Settings, parent, family, baby, early years, pregnancy, teacher, admin, results, audit, specialist) was checked with axe-core (WCAG 2.2 AA plus best practice) in light and dark mode, and with calm, movement and reading settings on. Fixes: the lesson screens now have a main heading for screen readers; two colours in dark mode were too faint. A check by a real screen-reader user (TalkBack on Android, NVDA on Windows) is still worth doing before the pilot.

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

## In Malayalam

Every message above has a Malayalam version (`backend/app/i18n.py`), used when the student reads SYNiq in Malayalam. The stories keep the same everyday objects: മാങ്ങ, പഴം, അപ്പം, മിഠായി. Logged decisions always keep the English wording.

## Every response is logged

Each response is recorded as an adaptation decision (rule `F_<mode>`, version `2026.10-1`) with the reason, just like the rest of the engine, so teachers and audits can see why SYNiq chose it.

## Ideas for later

- More stories and pictures for fractions, decimals and algebra tiles.
- Sign-language video clips for deaf students, made with a teacher.
