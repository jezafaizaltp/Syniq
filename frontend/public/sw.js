/*
 * SYNiq offline support.
 *
 * - The app's own files are kept so SYNiq opens without internet.
 * - Pages are fetched fresh when online and fall back to the last copy when offline.
 * - A few read-only API answers (the student's own space, notes, goals, Explore, subject
 *   lists) are kept too, so they can still be read offline. Each is stored under a key
 *   made from a hash of the signed-in person's token, so on a shared school computer one
 *   person can never be shown another's saved answers. Signing out clears them.
 * - Healthy screen time (ages 2 to 4) plays fully offline from the saved activity list; time
 *   played offline is sent once the phone is back online.
 * - Answering questions needs internet: the adaptive teacher runs on the server.
 */
const VERSION = "syniq-v2";
const SHELL = `${VERSION}-shell`;
const API = `${VERSION}-api`;
const API_PATHS = [/^\/me$/, /^\/me\/(overview|goals|notes)$/, /^\/explore(\/[\w.]+)?$/, /^\/subjects(\/\d+\/chapters)?$/, /^\/chapters\/\d+$/, /^\/checks$/, /^\/ai\/status$/, /^\/family$/, /^\/early\/\d+$/];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(["/", "/learn", "/space", "/explore", "/family", "/early", "/manifest.webmanifest"]).catch(() => undefined)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "sign-out") event.waitUntil(caches.delete(API));
});

async function personKey(request) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth) return null;
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(auth));
  const hex = [...new Uint8Array(digest)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
  const url = new URL(request.url);
  url.searchParams.set("__person", hex);
  url.searchParams.set("__lang", request.headers.get("Accept-Language") || "en");
  return url.toString();
}

async function networkFirst(request, cacheName, key) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(key, response.clone());
    return response;
  } catch (err) {
    const saved = await cache.match(key);
    if (saved) return saved;
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (url.origin === self.location.origin) {
    if (url.pathname.startsWith("/_next/static/")) {
      // Built files never change under the same name: keep the first copy.
      event.respondWith(caches.open(SHELL).then(async (c) => (await c.match(request)) || fetch(request).then((r) => (r.ok && c.put(request, r.clone()), r))));
    } else if (request.mode === "navigate") {
      event.respondWith(networkFirst(request, SHELL, url.pathname).catch(async () => (await caches.match("/")) || Response.error()));
    }
    return;
  }

  if (API_PATHS.some((re) => re.test(url.pathname))) {
    event.respondWith(
      personKey(request).then((key) => (key ? networkFirst(request, API, key) : fetch(request)))
    );
  }
});
