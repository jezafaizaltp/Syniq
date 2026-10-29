# SYNiq

SYNiq by REAXIS is an adaptive learning platform: an adaptive teacher that remembers how each student learns, notices their mistake patterns, and changes how it explains things. It never turns a student into a score or a label.

This repository holds the Phase 1 MVP for the **Class 9 Kerala State (SCERT) syllabus pilot** with Providence School, Calicut.

## What works today

- **Accounts and roles:** student, guardian, teacher and admin, with server-side permission checks.
- **Consent first:** a student can't learn until a guardian consents. Mood check-ins and sharing with the school each need their own consent. Consent records are append-only.
- **Curriculum model:** subject → chapter → concept, with prerequisites. All nine Class 9 subjects exist. Only a demo Mathematics chapter has content so far.
- **Adaptive teacher engine** (`backend/app/engine/`):
  - Bayesian Knowledge Tracing estimates mastery for each concept. Hints and lucky guesses count for less.
  - Ordered, versioned rules pick the next step: introduce, practise, explain differently, revisit a prerequisite, or space out reviews.
  - Every decision is logged with its rule, version and evidence, and students can ask "Why am I seeing this?".
  - Guardrails: no adaptation based on one answer, nothing inferred from speed, and support offers that the student can always decline.
- **Student app:** optional mood check-in, explanations in four styles (words, picture, step by step, real-life) that the student can switch between at any time, practice with graded hints, misconception-specific tips, worked solutions, and a "take a break" button.
- **Accessibility settings, no diagnosis needed:** text size, high contrast, easier-to-read font, reduced motion, read-aloud, extra time, and a preferred explanation style.
- **Teacher dashboard:** class progress by topic shown as counts (never rankings), common mistakes, students who may need a hand, and a content review queue. Nothing reaches students until a teacher approves it.
- **Parent view:** consent toggles and progress shown in words, not numbers.
- **Ten ways to respond, without AI** ([details](docs/response-modes.md)): six support modes chosen in settings (stay focused, easier reading, screen reader, deaf or hard of hearing, tap to answer, objects and smaller numbers) and four modes picked from the student's answers (count it out with stars, step by step, a real-life story, a smaller similar question). SYNiq names common mistakes in sums, e.g. for 10 + 10 answered 15 it draws both and shows the difference. A "Demo: Number sense warm-up" chapter lets you try it.
- **Ask SYNiq (AI tutor, Claude API):** students can ask about the topic they are on. Answers are grounded in the teacher's topic notes and approved explanations, and guide rather than hand over answers. No student name, id, progress or mood is sent, phone numbers and emails typed by mistake are removed, and chats are not saved. Messages about self-harm or abuse get a fixed reply pointing to a trusted adult and Tele-MANAS (14416) without calling the AI. Limited to 60 questions per student per day.
- **Teacher content pipeline:** teachers set up SCERT chapters and topics, write short notes on what the textbook covers, and can ask Claude to draft explanations in all four styles plus practice questions with hints, solutions and common mistakes. Drafts are marked "AI draft", carry Claude's notes on what to check, can be edited, and only reach students after a teacher approves them. Unmarkable questions (e.g. an answer that isn't one of the options) are dropped automatically.

## Not built yet

- Malayalam and Hindi interfaces.
- Real SCERT chapter content for every subject.
- Interest exploration activities.
- Picture explanations: the "picture" style is still described in text.
- Production auth (password reset, rate limits) and deployment.

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

The Claude requests use server-side fallbacks (`fallbacks: "default"`): if Claude declines a request, the API retries it on Anthropic's recommended fallback model within the same call.

After pulling this change, delete `backend/syniq.db` and run `python -m app.seed` again: new columns were added and there are no migrations yet.
