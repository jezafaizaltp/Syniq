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

## Not built yet

- The AI tutor and AI-drafted content (Claude API).
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
