# SYNiq

SYNiq by REAXIS is an adaptive learning platform: an adaptive teacher that remembers how each student learns, notices their mistake patterns, and changes how it explains things. It never turns a student into a score or a label.

This repository holds the Phase 1 MVP for the **Class 9 Kerala State (SCERT) syllabus pilot** with Providence School, Calicut.

## What works today

- **Accounts and roles:** student, guardian, teacher, specialist and admin, with server-side permission checks.
- **Consent first:** a student can't learn until a guardian consents. Mood check-ins and sharing with the school each need their own consent. Consent records are append-only.
- **Curriculum model:** subject → chapter → concept, with prerequisites. All nine Class 9 subjects exist. Mathematics chapters 1 to 15 (57 topics, 379 questions), Physics 1 to 8 (27 topics, 166 questions), Chemistry 1 to 8 (26 topics, 158 questions) Biology 1 to 6 (19 topics, 124 questions), Social Science I 1 to 8 (24 topics, 149 questions), Social Science II 1 to 8 (stored as Social Science 9 to 16; 36 topics, 289 questions), IT 1 to 10 (30 topics, 223 questions), English units I to V (25 topics, 165 questions), Malayalam Kerala Padavali units 1 to 5 and Adisthana Padavali units 1 to 3 (32 topics, 202 questions) and Hindi units 1 to 5 (17 topics, 106 questions) have full content ([content packs](backend/content/README.md)), written and checked by Claude with every computable answer re-checked by computer; other chapters and subjects have none yet.
- **Adaptive teacher engine** (`backend/app/engine/`):
  - Bayesian Knowledge Tracing estimates mastery for each concept. Hints and lucky guesses count for less.
  - Ordered, versioned rules pick the next step: introduce, practise, explain differently, revisit a prerequisite, or space out reviews.
  - Every decision is logged with its rule, version and evidence, and students can ask "Why am I seeing this?".
  - Guardrails: no adaptation based on one answer, nothing inferred from speed, and support offers that the student can always decline.
- **Student app:** optional mood check-in, explanations in four styles (words, picture, step by step, real-life) that the student can switch between at any time, practice with graded hints, misconception-specific tips, worked solutions, and a "take a break" button.
- **Accessibility settings, no diagnosis needed:** text size, high contrast, easier-to-read font, reduced motion, read-aloud, extra time, and a preferred explanation style.
- **Teacher dashboard:** class progress by topic shown as counts (never rankings), common mistakes, students who may need a hand, and a content review queue. Content drafted in the app reaches students only after a teacher approves it; content packs arrive already checked.
- **Parent view:** consent toggles and progress shown in words, not numbers.
- **Ten ways to respond, without AI** ([details](docs/response-modes.md)): three support modes SYNiq notices from a student's answers and switches on itself, telling the student why (shorter steps, easier reading, pictures and smaller numbers), three that parents choose (screen reader, deaf or hard of hearing, tap to answer), and four modes picked from the student's answers (count it out with stars, step by step, a real-life story, a smaller similar question). SYNiq names common mistakes in sums, e.g. for 10 + 10 answered 15 it draws both and shows the difference. A "Demo: Number sense warm-up" chapter lets you try it.
- **Ask SYNiq (AI tutor, Claude API):** students can ask about the topic they are on. Answers are grounded in the teacher's topic notes and approved explanations, and guide rather than hand over answers. No student name, id, progress or mood is sent, phone numbers and emails typed by mistake are removed, and chats are not saved. Messages about self-harm or abuse get a fixed reply pointing to a trusted adult and Tele-MANAS (14416) without calling the AI. Limited to 60 questions per student per day.
- **School setup for the pilot** (admin's **School** page): upload one spreadsheet (CSV) of students and parents with consent from the paper forms, check it before anything is created, and print a login sheet with temporary passwords. Siblings share one parent login, phone numbers are never saved, and marks or ability groups are never uploaded. The admin can add teachers, give anyone a new password, and record changed paper consent.
- **Class 9 syllabus from a sheet:** the admin uploads chapters and topics for all nine subjects as a CSV (one row per topic), checked before anything is added and safe to upload again as it grows. A draft list of chapters is in [content/](content/README.md), to check against the textbooks. Students only see chapters once a teacher has approved content in them.
- **Subject checks** (no marks, ever): when a student opens a subject, SYNiq offers an optional starting check of up to 12 questions, one per topic across the subject, with an "I haven't learnt this yet" button. Afterwards the student sees, in words, which topics they seem to know and where SYNiq will start, and the engine starts there (one answer only nudges a topic's estimate; it never marks it secure). The admin opens an end-of-term check and, about 4 weeks later, a remember-it check from **Pilot results**, and sees per subject the share answered right and the change from the start, for groups of 5 or more. Check answers are kept apart from practice, so they never switch on support modes.
- **My space** for students: what's due for a quick revision (with a Revise button), how each subject is going in words (secure, getting there, learning) with a "carry on" link, goals they set themselves with an optional date, and notes they write while learning a topic. Goals and notes are private to the student: teachers, parents and the engine can't read them, and the student can delete them.
- **Explore** (interest exploration): 20 short off-screen activities across five areas (making and imagining, hands-on and fixing, finding out, people and helping, ideas and business), each with steps and a question to think about afterwards. The student says how it felt (loved it, okay, not for me) and can note what they made. SYNiq suggests one area they haven't tried yet alongside more of what they loved, and never turns this into a label such as "creative type". Reflections are private to the student.
- **Audit log** (admin's **Audit log** page): every view of a class or a child's progress, consent and support change, password reset, check opened or closed, and use of pilot marks, in plain words, newest first. Read-only.
- **Works on patchy internet:** once opened, SYNiq installs like an app and keeps opening without internet. My space, notes, goals, Explore and the subject lists show the last saved copy, with a banner saying practice needs internet (the adaptive teacher runs on the server). Saved answers are stored per signed-in person and wiped on sign-out, so shared school computers stay private.
- **Specialist view:** the admin adds a school counsellor, special educator or therapist. A parent ticks which specialist may see their child, and can untick at any time. The specialist sees the support the child uses (chosen and noticed, with reasons), progress per subject in words, mistakes that keep coming back and which help buttons they use. Never mood check-ins, marks, notes, goals or Explore reflections, and no diagnosis. Every share, stop and view is in the audit log.
- **Family accounts** (SYNiq outside school): anyone can sign up at **/signup** and holds the account (usually the mother). They add children from pregnancy onwards, and SYNiq places each child in a section from their dates and class alone: pregnancy, baby (0 to 2), healthy screen time (2 to 4) or school (LKG to Class 12). The holder invites fathers, grandparents or other carers with their own logins, can remove them at any time (their login stops working), and gives a school-age child a login, which is their consent for SYNiq to adapt to that child. Each child's class and syllabus (CBSE or Kerala State) is set by the parent and decides which subjects the child sees; pilot students without one stay on Kerala State Class 9. The pregnancy, baby and 2 to 4 sections are shown but not built yet. Every family change is in the audit log.
- **Pilot results** ([method](docs/pilot-results.md)): the admin uploads the school's own exam marks from before and after SYNiq, for pilot students and an anonymous comparison group, and sees per subject how much more the pilot group changed, with a likely range, by starting marks and by practice. Group averages only, groups under 5 hidden, marks never reach the teaching engine, teachers, parents or students, and can all be deleted after the pilot.
- **Safer sign-in:** everyone must choose their own password the first time they sign in, wrong passwords are limited to 10 in 15 minutes, people are signed out after 14 days without use, and changing a password signs out other devices.
- **Ready to host** ([guide](docs/deploy.md)): Docker Compose with PostgreSQL, automatic HTTPS (Caddy) and a nightly database backup, on one small server in India.
- **Malayalam:** students and parents can switch the whole app to Malayalam (button at the top, or Settings), and the choice is saved to their account. Feedback, star pictures, stories, reasons, errors and spoken read-aloud all follow it, and Ask SYNiq replies in Malayalam. Lessons and questions stay in the language the teacher wrote them in. The teacher and school admin screens are English for now. All Malayalam wording is in `backend/app/i18n.py` and `frontend/lib/i18n.ts` and should be checked by a Malayalam teacher before the pilot.
- **Teacher content pipeline:** teachers set up SCERT chapters and topics, write short notes on what the textbook covers, and can ask Claude to draft explanations in all four styles plus practice questions with hints, solutions and common mistakes. Drafts are marked "AI draft", carry Claude's notes on what to check, can be edited, and only reach students after a teacher approves them. Unmarkable questions (e.g. an answer that isn't one of the options) are dropped automatically.

- **Public website and SYNiq tutor** ([site/](site/README.md)): a home page in SYNiq's ivory, brick and yellow, and a free tutor chatbot (OpenAI) that teaches any topic the SYNiq way, for any learner, and draws "your way" next to "the right path" when an answer goes wrong. Plain static files plus one small function, hosted free on Cloudflare Pages.

## Not built yet

- Hindi interface, and Malayalam for the teacher and school admin screens.
- A teacher's check of all content against the 2024 SCERT books (including a native speaker's read of the Malayalam and Hindi questions).
- Picture explanations: the "picture" style is still described in text.

## Run locally

```bash
# API (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000

# Web app (http://localhost:3000)
cd frontend
npm install
npm run dev
```

Demo accounts all use the password `syniq-demo`:

| Account | Email |
| --- | --- |
| Student | `anu@demo.syniq` |
| Student | `rahul@demo.syniq` |
| Student, no consent yet | `fathima@demo.syniq` |
| Teacher | `teacher@demo.syniq` |
| Guardian of all three | `parent@demo.syniq` |
| School admin | `admin@demo.syniq` |
| Specialist (school counsellor) | `specialist@demo.syniq` |
| Family account holder (a baby, a toddler and one on the way) | `mother@demo.syniq` |

The demo accounts and the sign-in hint are only for local use. A live server starts with no demo accounts (see [docs/deploy.md](docs/deploy.md)) and its web app is built with the hint hidden (`NEXT_PUBLIC_SHOW_DEMO=0`).

The demo maths content was written to exercise the engine. It has **not** been checked against the current SCERT textbook and must be reviewed by a teacher before any pilot student sees it.

## Tests

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./syniq.db` | Use a PostgreSQL URL in production |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of web app origins |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API address used by the web app |
| `ANTHROPIC_API_KEY` | not set | Turns on the AI tutor and AI drafting. Without it the app works as before and the AI buttons are hidden |
| `SYNIQ_AI_MODEL` | `claude-opus-5-5` | Claude model used for the tutor and drafting |
| `SYNIQ_ENV` | not set | `production` switches off the API docs pages |
| `NEXT_PUBLIC_SHOW_DEMO` | shown | `0` hides the demo account hint on the sign-in page |

The Claude requests use server-side fallbacks (`fallbacks: "default"`): if Claude declines a request, the API retries it on Anthropic's recommended fallback model within the same call.

## Database changes

Locally, SQLite tables are created on start, so after pulling a change that adds columns, delete `backend/syniq.db` and run `python -m app.seed` again.

PostgreSQL uses Alembic migrations (`backend/migrations/`). The API container runs `alembic upgrade head` each time it starts. After changing `backend/app/models.py`, create a migration and check it before committing:

```bash
cd backend
DATABASE_URL=postgresql://... alembic revision --autogenerate -m "what changed"
DATABASE_URL=postgresql://... alembic upgrade head
```

## Putting it online

See [docs/deploy.md](docs/deploy.md): one small server, `docker compose up -d --build`, then create the school admin with `python -m app.bootstrap`.
