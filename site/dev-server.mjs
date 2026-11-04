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

const MOCK_COUNT = `Good try! You counted the first group right. Let's count all the stars together.

\`\`\`diagram
{"alt":"Your way: 4 stars plus 5 stars with 8 as the answer. The right path: 4 plus 5 stars makes 9; the missed star is circled.","panels":[{"tone":"try","count":{"a":4,"op":"+","b":5,"result":8,"icon":"star"},"note":"You got 8"},{"tone":"right","count":{"a":4,"op":"+","b":5,"result":9,"icon":"star"},"note":"Count them all: 9"}]}
\`\`\`

Can you count the stars in the right path, one by one?`;

const MOCK_FRACTION = `Nice, you counted **3 pieces left** correctly! The bottom number is the one to look at.

\`\`\`diagram
{"alt":"Your way: a bar of 5 pieces with 3 shaded. The right path: a bar of 8 pieces with 3 shaded.","panels":[{"tone":"try","fraction":[{"num":3,"den":5,"label":"left"}],"note":"A bar of 5 pieces"},{"tone":"right","fraction":[{"num":3,"den":8,"label":"left"}],"note":"The bar had 8 pieces"}]}
\`\`\`

How many pieces was the whole bar cut into?`;

const MOCK_CARD = `Good thinking: you knew this was a nerve cell! The word is just a small mix-up, and it's a common one.

\`\`\`diagram
{"alt":"Your way: neutron, a tiny particle in the centre of an atom. The right path: neuron, a nerve cell that carries messages.","panels":[{"tone":"try","caption":"What you wrote: neutron","card":{"emoji":"⚛️","title":"Neutron","points":["A tiny particle in the **centre of an atom**","Part of chemistry and physics"]}},{"tone":"right","caption":"What this is: neuron","card":{"emoji":"🧠","title":"Neuron","points":["A **nerve cell**","Carries messages around your body and brain"]}}]}
\`\`\`

Can you spot the one letter that changes **neutron** into **neuron**? Then label the picture again.`;

const MOCKS = [MOCK_COUNT, MOCK_FRACTION, MOCK_CARD, MOCK_REPLY];
let mockTurn = 0;

async function mockFetch(url) {
  const body = url.endsWith("/moderations")
    ? { results: [{ categories: {} }] }
    : { choices: [{ message: { content: MOCKS[mockTurn++ % MOCKS.length] } }] };
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
