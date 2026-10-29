# SYNiq

SYNiq by REAXIS is an adaptive learning platform: an adaptive teacher that remembers how each student learns, notices their mistake patterns, and changes how it explains things. It never turns a student into a score or a label.

This repository holds the Phase 1 MVP for the **Class 9 Kerala State (SCERT) syllabus pilot** with Providence School, Calicut.

## What works today

- **Accounts and roles:** student, guardian, teacher and admin, with server-side permission checks.
- **Consent first:** a student can't learn until a guardian consents. Mood check-ins and sharing with the school each need their own consent. Consent records are append-only.
- **Curriculum model:** subject → chapter → concept, with prerequisites. All nine Class 9 subjects exist. Mathematics chapters 1 to 4 have full content (17 topics, 122 questions, [content packs](backend/content/README.md)), written and checked by Claude with every computable answer re-checked by computer; other chapters and subjects have none yet.
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
- **Pilot results** ([method](docs/pilot-results.md)): the admin uploads the school's own exam marks from before and after SYNiq, for pilot students and an anonymous comparison group, and sees per subject how much more the pilot group changed, with a likely range, by starting marks and by practice. Group averages only, groups under 5 hidden, marks never reach the teaching engine, teachers, parents or students, and can all be deleted after the pilot.
- **Safer sign-in:** everyone must choose their own password the first time they sign in, wrong passwords are limited to 10 in 15 minutes, people are signed out after 14 days without use, and changing a password signs out other devices.
- **Ready to host** ([guide](docs/deploy.md)): Docker Compose with PostgreSQL, automatic HTTPS (Caddy) and a nightly database backup, on one small server in India.
- **Malayalam:** students and parents can switch the whole app to Malayalam (button at the top, or Settings), and the choice is saved to their account. Feedback, star pictures, stories, reasons, errors and spoken read-aloud all follow it, and Ask SYNiq replies in Malayalam. Lessons and questions stay in the language the teacher wrote them in. The teacher and school admin screens are English for now. All Malayalam wording is in `backend/app/i18n.py` and `frontend/lib/i18n.ts` and should be checked by a Malayalam teacher before the pilot.
- **Teacher content pipeline:** teachers set up SCERT chapters and topics, write short notes on what the textbook covers, and can ask Claude to draft explanations in all four styles plus practice questions with hints, solutions and common mistakes. Drafts are marked "AI draft", carry Claude's notes on what to check, can be edited, and only reach students after a teacher approves them. Unmarkable questions (e.g. an answer that isn't one of the options) are dropped automatically.

## Not built yet

- Hindi interface, and Malayalam for the teacher and school admin screens.
- Content for Mathematics chapters 5 to 15 and the other eight subjects, and a teacher's check of chapters 1 to 4 against the 2024 SCERT book.
- Interest exploration activities.
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
