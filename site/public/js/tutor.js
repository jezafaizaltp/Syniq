// The SYNiq tutor chat. Keeps the conversation in memory only (closing the tab forgets it),
// sends it with the learner's settings to /api/chat, and draws any diagrams in the reply.
import { renderDiagram, parseDiagram } from "./diagram.js";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const messagesEl = $("#messages");
const form = $("#composer");
const input = $("#composer-input");
const sendBtn = $("#send");
const side = $("#side");

const PREFS_KEY = "syniq.prefs.v1";
const SIZES = [0.9, 1, 1.1, 1.25, 1.4, 1.6];
const AVATAR = `<svg class="avatar" viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="11" fill="#a63d2a"/><path d="M9 29c5 0 6-6 11-6s5-8 11-8" fill="none" stroke="#fbf7ee" stroke-width="3.4" stroke-linecap="round"/><circle cx="31" cy="15" r="4" fill="#f2b630"/></svg>`;

let history = [];
let busy = false;

/* ---------- Settings (this device only) ---------- */

function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
  } catch {
    return {};
  }
}
function savePrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    // Private windows can refuse storage; settings then last for this visit only.
  }
}

let prefs = { size: 1, ...loadPrefs() };

function readForm() {
  prefs.styles = $$('input[name="styles"]:checked', side).map((i) => i.value);
  prefs.reading = $('input[name="reading"]', side).checked ? "short" : "normal";
  prefs.screen_reader = $('input[name="screen_reader"]', side).checked;
  prefs.level = $('input[name="level"]', side).value.trim();
  prefs.note = $('textarea[name="note"]', side).value.trim();
  prefs.easy_font = $('input[name="easy_font"]', side).checked;
  prefs.contrast = $('input[name="contrast"]', side).checked;
  prefs.read_aloud = $('input[name="read_aloud"]', side).checked;
  savePrefs(prefs);
  applyLook();
}

function fillForm() {
  for (const box of $$('input[name="styles"]', side)) box.checked = (prefs.styles || []).includes(box.value);
  $('input[name="reading"]', side).checked = prefs.reading === "short";
  $('input[name="screen_reader"]', side).checked = !!prefs.screen_reader;
  $('input[name="level"]', side).value = prefs.level || "";
  $('textarea[name="note"]', side).value = prefs.note || "";
  $('input[name="easy_font"]', side).checked = !!prefs.easy_font;
  $('input[name="contrast"]', side).checked = !!prefs.contrast;
  $('input[name="read_aloud"]', side).checked = !!prefs.read_aloud;
}

function applyLook() {
  const root = document.documentElement;
  root.style.setProperty("--text-scale", String(prefs.size || 1));
  root.classList.toggle("easy-font", !!prefs.easy_font);
  root.classList.toggle("contrast", !!prefs.contrast);
  $("#size-label").textContent = `Text ${Math.round((prefs.size || 1) * 100)}%`;
}

side.addEventListener("change", readForm);
side.addEventListener("input", (e) => {
  if (e.target.matches('input[type="text"], textarea')) readForm();
});
for (const btn of $$("[data-size]")) {
  btn.addEventListener("click", () => {
    const i = SIZES.indexOf(prefs.size || 1);
    const next = SIZES[Math.max(0, Math.min(SIZES.length - 1, (i < 0 ? 1 : i) + Number(btn.dataset.size)))];
    prefs.size = next;
    savePrefs(prefs);
    applyLook();
  });
}

const openSide = () => {
  side.classList.add("open");
  $('input[name="styles"]', side).focus();
};
const closeSide = () => side.classList.remove("open");
$("[data-open-side]").addEventListener("click", openSide);
$("[data-close-side]").addEventListener("click", closeSide);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSide();
});

// Mobile menu, same as the home page.
const toggle = $(".nav-toggle");
const nav = $("#nav");
toggle.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  toggle.setAttribute("aria-expanded", String(open));
});

/* ---------- Rendering replies ---------- */

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function inline(s) {
  return escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

// A small, safe Markdown subset: paragraphs, bullet and numbered lists, bold, italics, code.
// Everything is escaped first, so nothing in a reply can become live HTML.
function renderText(text) {
  const out = [];
  let list = null;
  let para = [];
  const flushPara = () => {
    if (para.length) out.push(`<p>${para.map(inline).join("<br>")}</p>`);
    para = [];
  };
  const flushList = () => {
    if (list) out.push(`<${list.tag}>${list.items.map((i) => `<li>${inline(i)}</li>`).join("")}</${list.tag}>`);
    list = null;
  };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const heading = line.match(/^#{1,4}\s+(.*)$/);
    if (bullet || numbered) {
      flushPara();
      const tag = bullet ? "ul" : "ol";
      if (!list || list.tag !== tag) {
        flushList();
        list = { tag, items: [] };
      }
      list.items.push((bullet || numbered)[1]);
    } else if (!line.trim()) {
      flushPara();
      flushList();
    } else if (heading) {
      flushPara();
      flushList();
      out.push(`<p><strong>${inline(heading[1])}</strong></p>`);
    } else {
      flushList();
      para.push(line);
    }
  }
  flushPara();
  flushList();
  return out.join("");
}

// Split a reply into text and ```diagram blocks. An unfinished block is treated as a miss.
function splitReply(reply) {
  const parts = [];
  const re = /```diagram\s*\n?([\s\S]*?)(```|$)/g;
  let last = 0;
  let m;
  while ((m = re.exec(reply))) {
    if (m.index > last) parts.push({ type: "text", value: reply.slice(last, m.index) });
    parts.push({ type: "diagram", value: m[1] });
    last = re.lastIndex;
  }
  if (last < reply.length) parts.push({ type: "text", value: reply.slice(last) });
  return parts;
}

function spokenText(reply) {
  return splitReply(reply)
    .map((p) => {
      if (p.type === "text") return p.value.replace(/[*`#]/g, "");
      const spec = parseDiagram(p.value);
      return spec?.alt ? `Picture: ${spec.alt}` : "";
    })
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  if (/[ഀ-ൿ]/.test(text)) u.lang = "ml-IN";
  else if (/[ऀ-ॿ]/.test(text)) u.lang = "hi-IN";
  else u.lang = "en-IN";
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

function scrollToEnd(node, block = "end") {
  node.scrollIntoView({ block, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

function addUser(text) {
  const row = document.createElement("div");
  row.className = "msg msg-user";
  row.innerHTML = `<div class="bubble">${renderText(text)}</div>`;
  messagesEl.appendChild(row);
  scrollToEnd(row);
}

function addTutor(reply, { note = false, retry = null } = {}) {
  const row = document.createElement("div");
  row.className = `msg msg-tutor${note ? " msg-note" : ""}`;
  row.innerHTML = AVATAR;
  const bubble = document.createElement("div");
  bubble.className = "bubble";

  for (const part of splitReply(reply)) {
    if (part.type === "text") {
      if (part.value.trim()) bubble.insertAdjacentHTML("beforeend", renderText(part.value.trim()));
      continue;
    }
    const spec = parseDiagram(part.value);
    if (spec) {
      bubble.appendChild(renderDiagram(spec));
    } else {
      const miss = document.createElement("p");
      miss.className = "diagram-miss";
      miss.textContent = "I tried to draw a picture here but it didn't come out. Ask me to draw it again.";
      bubble.appendChild(miss);
    }
  }

  const tools = document.createElement("div");
  tools.className = "msg-tools";
  if ("speechSynthesis" in window) {
    const say = document.createElement("button");
    say.type = "button";
    say.textContent = "🔊 Read aloud";
    say.addEventListener("click", () => speak(spokenText(reply)));
    tools.appendChild(say);
  }
  if (retry) {
    const again = document.createElement("button");
    again.type = "button";
    again.textContent = "Try again";
    again.addEventListener("click", () => {
      row.remove();
      retry();
    });
    tools.appendChild(again);
  }
  if (tools.children.length) bubble.appendChild(tools);

  row.appendChild(bubble);
  messagesEl.appendChild(row);
  // Show a reply from its first line, so a long one with pictures is read from the top.
  scrollToEnd(row, "start");
  if (prefs.read_aloud && !note) speak(spokenText(reply));
}

function addTyping() {
  const row = document.createElement("div");
  row.className = "msg msg-tutor";
  row.innerHTML = `${AVATAR}<div class="bubble" aria-label="SYNiq is thinking"><span class="typing"><span></span><span></span><span></span></span></div>`;
  messagesEl.appendChild(row);
  scrollToEnd(row);
  return row;
}

/* ---------- Talking to the tutor ---------- */

function payloadPrefs() {
  const { styles, reading, screen_reader, level, note } = prefs;
  return { styles, reading, screen_reader, level, note };
}

async function ask() {
  busy = true;
  sendBtn.disabled = true;
  const typing = addTyping();
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ messages: history.slice(-20), prefs: payloadPrefs() }),
    });
    const data = await res.json().catch(() => ({}));
    typing.remove();
    if (res.ok && data.reply) {
      history.push({ role: "assistant", content: data.reply });
      addTutor(data.reply);
    } else {
      addTutor(data.error || "Something went wrong. Please try again.", { note: true, retry: ask });
    }
  } catch {
    typing.remove();
    addTutor("I couldn't connect. Check your internet and try again.", { note: true, retry: ask });
  } finally {
    busy = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

function send(text) {
  const clean = text.trim();
  if (!clean || busy) return;
  $("#welcome")?.remove();
  history.push({ role: "user", content: clean });
  addUser(clean);
  input.value = "";
  autoGrow();
  ask();
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  send(input.value);
});
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send(input.value);
  }
});
function autoGrow() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
}
input.addEventListener("input", autoGrow);

for (const b of $$(".starter")) b.addEventListener("click", () => send(b.textContent));
for (const b of $$("[data-say]")) b.addEventListener("click", () => send(b.dataset.say));

$("#new-chat").addEventListener("click", () => {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  history = [];
  location.reload();
});

/* ---------- Speaking instead of typing ---------- */

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (Recognition) {
  const mic = $("#mic");
  mic.hidden = false;
  let rec = null;
  mic.addEventListener("click", () => {
    if (rec) {
      rec.stop();
      return;
    }
    rec = new Recognition();
    rec.lang = navigator.language?.startsWith("ml") ? "ml-IN" : navigator.language?.startsWith("hi") ? "hi-IN" : "en-IN";
    rec.interimResults = true;
    const before = input.value ? `${input.value} ` : "";
    rec.onresult = (e) => {
      input.value = before + [...e.results].map((r) => r[0].transcript).join("");
      autoGrow();
    };
    rec.onend = () => {
      rec = null;
      mic.classList.remove("listening");
      mic.setAttribute("aria-label", "Speak instead of typing");
      input.focus();
    };
    rec.onerror = rec.onend;
    mic.classList.add("listening");
    mic.setAttribute("aria-label", "Stop listening");
    rec.start();
  });
}

fillForm();
applyLook();
