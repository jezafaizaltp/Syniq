// Runs the website and the tutor on http://localhost:8788 with plain Node (no installs).
//   OPENAI_API_KEY=sk-... node dev-server.mjs
// TUTOR_MOCK=1 answers with a canned reply instead of calling OpenAI, for trying the page offline.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { handleChat } from "./server/tutor.js";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "public");
const PORT = Number(process.env.PORT) || 8788;
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

const MOCK_REPLY = `Nice try, and your **tan** step was right! Let's look at where the angle was measured from.

\`\`\`diagram
{"alt":"Left: the 30 degree angle drawn from straight up. Right: the 30 degree angle drawn from the flat ground.","panels":[{"tone":"try","note":"30° measured from straight up","shapes":[{"line":[2,8,98,8],"color":"muted"},{"line":[82,8,82,48.4],"width":"thick","label":"h"},{"line":[12,8,82,48.4],"dash":true},{"line":[12,8,12,54],"color":"try","dash":true},{"angle":[12,8],"from":30,"to":90,"r":13,"color":"try","label":"30°"},{"highlight":[18,23],"r":7}]},{"tone":"right","note":"Elevation starts at the flat ground","shapes":[{"line":[2,8,98,8],"color":"muted"},{"line":[82,8,82,48.4],"width":"thick","color":"right","label":"h"},{"line":[12,8,82,48.4],"dash":true},{"angle":[12,8],"from":0,"to":30,"r":16,"color":"right","fill":"soft","label":"30°"},{"right_angle":[82,8],"from":90}]}]}
\`\`\`

The angle of elevation always starts at the **flat ground**. Can you try again with the angle in the right place?`;

async function mockFetch(url) {
  const body = url.endsWith("/moderations")
    ? { results: [{ categories: {} }] }
    : { choices: [{ message: { content: MOCK_REPLY } }] };
  return new Response(JSON.stringify(body), { status: 200 });
}

async function toRequest(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return new Request(`http://localhost${req.url}`, {
    method: req.method,
    headers: req.headers,
    body: req.method === "POST" ? Buffer.concat(chunks) : undefined,
  });
}

createServer(async (req, res) => {
  try {
    if (req.url.startsWith("/api/chat")) {
      const mock = process.env.TUTOR_MOCK === "1";
      const env = mock ? { ...process.env, OPENAI_API_KEY: "mock" } : process.env;
      const out = await handleChat(await toRequest(req), env, mock ? mockFetch : fetch);
      res.writeHead(out.status, Object.fromEntries(out.headers));
      res.end(await out.text());
      return;
    }
    let path = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    if (path.endsWith("/")) path += "index.html";
    const file = normalize(join(ROOT, path));
    if (!file.startsWith(ROOT)) throw new Error("outside");
    const data = await readFile(file);
    res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
    res.end(data);
  } catch {
    res.writeHead(404, { "content-type": "text/plain" });
    res.end("Not found");
  }
}).listen(PORT, () => console.log(`SYNiq site on http://localhost:${PORT}`));
