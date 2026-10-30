# SYNiq website and tutor

The public website for SYNiq (home page, tutor, privacy page) and the SYNiq tutor chatbot, which uses the OpenAI API.

```
site/
  public/            the website (plain HTML, CSS and JavaScript, nothing to build)
    index.html       home page
    tutor.html       the tutor chat
    privacy.html     how the tutor handles messages
    js/diagram.js    draws the tutor's "your way / the right path" pictures
  functions/api/chat.js   Cloudflare Pages Function: POST /api/chat
  server/tutor.js    the tutor itself: SYNiq teaching prompt, safety checks, OpenAI call
  dev-server.mjs     runs everything locally with plain Node
  tests/             node --test
```

It is separate from the SYNiq app in `frontend/` and `backend/`: the website needs no database and no server of its own, so it can be hosted free.

## How the tutor works

- The browser sends the recent chat (last 20 messages) and the learner's "How I like to learn" choices to `/api/chat`. Nothing is saved on the server; the chat is forgotten when the page is closed.
- The OpenAI key lives only in the server's settings (`OPENAI_API_KEY`). It is never sent to the browser.
- Before OpenAI is asked: emails and phone numbers are removed; messages about self-harm or abuse get a fixed reply pointing to a trusted adult, Tele-MANAS (14416) and 112, without calling the model (same words and patterns as the app's tutor); OpenAI's free moderation check also stops sexual or threatening messages.
- The teaching rules are in `SYSTEM_PROMPT` in `server/tutor.js`: find where the learner is, teach in their way, small steps, guide with a hint ladder instead of giving answers, find the exact step where an answer went wrong and draw "your way" next to "the right path", hand it back to the learner to fix, never name a diagnosis or use labels.
- Diagrams: the model writes a small JSON block (format in `DIAGRAM_SPEC`), and `public/js/diagram.js` draws it as SVG. Only known shapes and colours are drawn and all text is inserted as plain text. Every diagram carries a description for screen readers.
- Each visitor can send 20 messages per 5 minutes.

## Run it locally

Needs Node 18 or newer. No `npm install`.

```bash
cd site
TUTOR_MOCK=1 node dev-server.mjs          # canned reply, no OpenAI key needed
OPENAI_API_KEY=sk-... node dev-server.mjs # real tutor
# open http://localhost:8788
npm test
```

## Host it free on Cloudflare Pages (no credit card)

1. Create a free account at https://dash.cloudflare.com/sign-up (email only).
2. **Workers & Pages → Create → Pages → Connect to Git**, pick `jezafaizaltp/syniq`.
3. Build settings: framework preset **None**, build command empty, build output directory `public`, **root directory `site`**.
4. **Settings → Variables and Secrets** (Production): add `OPENAI_API_KEY` as a **Secret**. Optional: `OPENAI_MODEL`, `ALLOWED_ORIGINS`.
5. Deploy. The site is live at `https://<project>.pages.dev`; a custom domain can be added later.

Every push to `main` redeploys. The free plan allows 100,000 tutor requests a day, far more than needed.

### Settings

| Variable | What it does | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required. Without it the tutor says it isn't switched on yet. | none |
| `OPENAI_MODEL` | Which OpenAI model writes replies. | `gpt-4.1-mini` |
| `OPENAI_REASONING_EFFORT` | Only for reasoning models (e.g. `low`). | not sent |
| `OPENAI_MAX_TOKENS` | Longest reply. | `1400` |
| `ALLOWED_ORIGINS` | Comma-separated site addresses allowed to call the tutor, e.g. `https://syniq.pages.dev`. Stops other websites using your credits. | allow all |
| `TUTOR_MODERATION` | `off` skips OpenAI's moderation check. | on |

### Keeping the $200 of credits safe

- In the OpenAI dashboard, make a separate **project** for the website, create the key inside it, and set a **monthly budget** for that project, so a surprise can never use up all the credits.
- Set `ALLOWED_ORIGINS` once the site address is known.
- Rough cost with `gpt-4.1-mini` at current prices: about a quarter of a US cent per message, so $200 is very roughly 80,000 messages. Check https://openai.com/api/pricing as prices change.
- Credits on two different OpenAI accounts can't be pooled: the key comes from one account. Use one account's key first and swap the secret to the other account's key when it runs low.
