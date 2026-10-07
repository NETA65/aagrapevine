"""The service worker's BEHAVIOUR ("works with a weak signal"): /sw.js is built from src/pages/sw.11ty.js
+ src/_includes/pwa/sw-core.js and run in Node.js against a pretend network and pretend caches.

  * install    — the app shell and both offline pages are kept; a missing required file (the CSS, the
                 scripts, an offline page) makes the install fail so the browser tries again; a missing
                 optional file does not (a font, install-core.js — the "Install as an app" rules).
  * activate   — old versions' gvlv-* caches go; visitors' pages, saved pages, the booth display's copy and
                 other sites' caches stay; the page open during a first visit is kept WITH its own styles and
                 scripts — after activation, in the background (class Updates: "Reload" after an update never
                 waits for the open tabs; a tab whose page never answers is given up in time).
  * pages      — online: the page from the site (kept for later); offline, a server error or no answer
                 in time: the kept copy (and pwa.js is told it is a copy); no copy: the offline page in
                 the address's language; GitHub Pages' 404 passes through and is never kept; an old
                 address's forwarding page is kept (it still forwards offline), marked so the offline page
                 doesn't list it; an address without its last slash ("…/es") is the same page offline.
  * stand-in   — the offline pages follow the daily content, which brings no new worker: a page opened
                 online brings the one in its language up to date once a day; /offline/ opened online
                 replaces it at once (fetched once).
  * files      — the site's own GET requests only (other sites, POST, byte ranges, the worker, the manifest
                 and the build note are never touched); styles/images/JSON work offline once seen.
  * Save       — "Save key pages for offline" keeps the visitor's pages in their language, this month's
                 toolkit page when there is one, and reports progress and what failed.
  * the booth  — the booth display's offline copy (gvlv-booth-v1, class Booth): BOOTH_SAVE saves the About
                 page like a key page and the booth's files (the show always fetched again, kept photos and
                 videos not), with progress after each file — and while a big one downloads, or while the
                 save waits its turn —, the failed ones (at most 20 listed), prune (once the show is saved
                 fresh), a stop in time ("more"), on a full device and when BOOTH_CLEAR comes, a broken
                 download tried once more, one save at a time; BOOTH_STATUS counts;
                 BOOTH_CLEAR removes the copy. Its photos and videos answer from the copy, in the parts a
                 media player asks for (206 / 416 — "Range: bytes=a-b, a-, -n"); a file not saved goes to
                 the network with its range and is never kept; the show (/about/booth.json) is network
                 first, then the booth's copy, then the data cache's.
  * fresh      — saved pages not opened for a week are fetched again once a page opened online shows there
                 is a signal — and says Data saver is off (HOW_SERVED; else the browser's Save-Data / 2G):
                 one at a time, the first that fails ends the round, at most every 6 hours; a page gone (404),
                 or one whose new styles and scripts did not all come, keeps its copy; a save stops a running
                 round and none runs beside it; a page removed meanwhile stays removed (class Updates).
  * versions   — a page kept (opened, not saved) keeps its own area stylesheet offline after new versions:
                 the old static cache's stylesheets go on into the new one (class Updates).
  * the page   — pwa.js's side, run against a pretend page and worker: "Save key pages" gives up only
                 after 45 s without news from the worker (a weak signal saves slowly, not never), ignores
                 what a save it gave up on still says (a worker ready only by then gets no SAVE) and saves
                 again when asked, and asks the browser to keep the pages (navigator.storage.persist: its
                 answer joins the result line, or follows it when it comes late — with what helps on this
                 device: an iPhone's installed app keeps its own copy); each page tells the worker whether
                 Data saver is on (HOW_SERVED); "Reload" applies a new
                 version — or, applied already in another tab, just reloads; a YouTube preview is told to
                 keep youtube-nocookie.com before it starts (a click, Enter or Space).

Skipped without Node.js (tests/nodejs.py). The page-level checks (the panel, the banner) are in the
browser QA scripts; the static contract checks are in tests/test_pwa.py.

    python -m unittest tests.test_pwa_worker -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

# The pretend world each worker script below starts with: /sw.js built for "/aagrapevine/", world() → a fresh
# worker with its own pretend network and caches. (Two scripts, not one: Node gets each on its command line,
# which Windows caps at 32 767 characters.)
HARNESS_JS = r"""
import vm from "node:vm";
const SW = await imp("src/pages/sw.11ty.js");
const ORIGIN = "https://example.test";
const B = "/aagrapevine/";
const build = (version) => SW.render({
  build: { version },
  collections: { all: ["/", "/meetings/", "/monthly/", "/contribute/", "/shop/", "/accessibility/", "/orientation/",
                       "/orientation/magazines/"].map((url) => ({ url })) },
  orientation: { lessons: [{ id: "magazines" }] },
});
const code = build("t1");

const html = (title, extra = "") => `<!doctype html><html><head><title>${title}</title>` +
  `<link rel="stylesheet" href="${B}assets/css/main.css?v=t1"><script src="${B}assets/js/app.js?v=t1"></script></head><body>${extra}</body></html>`;
const marker = (res) => (res && res.body ? (/<body>(.*?)<\/body>/.exec(res.body) || [])[1] : res);   // which page answered

// world({ v, store }): another version of the worker (v: "t2" …) on the same device — the caches `store` of an earlier one
function world({ v = "t1", store: kept = null } = {}) {
  const store = kept || new Map();
  // absolute URL → { status, body, ct, ranges (answers "Range: bytes=a-b" with 206), takes (ms the clock moves on
  // before it arrives), chunks + gap (a body arriving in parts, the clock moving on `gap` ms between them),
  // breaksOnce (the first download breaks off), wait (a promise: no answer before it resolves) }
  // | "offline" | "hang" (never answers — until let go: AbortSignal)
  const net = new Map();
  const fetched = [];
  const log = [];                 // every fetch: { url, range, cache } (the Range header and cache mode it was asked with)
  const order = [];               // "<tag>:<type>" of the answers to messages sent with a tag, in the order they came
  const hooks = {};               // hooks.onFetch(url): called as each fetch starts
  const intervals = new Map();    // the worker's setInterval timers (id → { fn, ms }): a test runs them by hand
  let intervalId = 0;
  let fast = false;
  const handlers = {};
  const make = (url, status, body, headers) => {
    const res = new Response(body, { status, headers });
    Object.defineProperty(res, "type", { value: "basic" });
    Object.defineProperty(res, "url", { value: url });
    return res;
  };
  class FakeCache {
    constructor() { this.m = new Map(); this.room = Infinity; }   // room: puts left before the device is full
    key(r) { return typeof r === "string" ? new URL(r, ORIGIN).href : r.url; }
    async put(r, res) {
      if (this.room <= 0) throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
      this.room -= 1;
      const k = this.key(r); const body = await res.arrayBuffer(); this.m.delete(k); this.m.set(k, { body, status: res.status, headers: [...res.headers] });
    }
    async match(r, o = {}) {
      const k = this.key(r);
      if (this.m.has(k)) { const e = this.m.get(k); return make(k, e.status, e.body, e.headers); }
      if (o.ignoreSearch) for (const [kk, e] of this.m) if (kk.split("?")[0] === k.split("?")[0]) return make(kk, e.status, e.body, e.headers);
      return undefined;
    }
    async delete(r) { return this.m.delete(this.key(r)); }
    async keys() { return [...this.m.keys()].map((u) => new Request(u)); }
  }
  const caches = {
    async open(n) { if (!store.has(n)) store.set(n, new FakeCache()); return store.get(n); },
    async keys() { return [...store.keys()]; },
    async delete(n) { return store.delete(n); },
    async has(n) { return store.has(n); },
    async match(r, o) { for (const c of store.values()) { const hit = await c.match(r, o); if (hit) return hit; } return undefined; },
  };
  async function fetch(input, init = {}) {
    const url = new URL(typeof input === "string" ? input : input.url, ORIGIN).href;
    fetched.push(url);
    const asked = new Headers(typeof input === "string" ? init.headers : input.headers);
    log.push({ url, range: asked.get("range"), cache: init.cache || (typeof input === "string" ? "default" : input.cache) });
    if (hooks.onFetch) hooks.onFetch(url);
    const spec = net.has(url) ? net.get(url) : "offline";
    if (spec === "offline") throw new TypeError("Failed to fetch");
    if (spec === "hang") {
      const signal = init.signal || (typeof input === "string" ? null : input.signal);
      return new Promise((resolve, reject) => {
        if (signal) signal.addEventListener("abort", () => reject(new DOMException("The operation was aborted.", "AbortError")));
      });
    }
    if (spec.wait) await spec.wait;
    if (spec.takes) ctx.__skew += spec.takes;
    const headers = { "content-type": spec.ct || "text/html; charset=utf-8", date: new Date().toUTCString() };
    if (spec.breaksOnce && !spec.broke) {                          // the first download breaks off after 100 bytes
      spec.broke = true;
      let sent = false;
      return make(url, 200, new ReadableStream({
        pull(c) { if (sent) c.error(new TypeError("network error")); else { sent = true; c.enqueue(new TextEncoder().encode(String(spec.body).slice(0, 100))); } },
      }), headers);
    }
    if (spec.chunks) {
      let i = 0;
      const enc = new TextEncoder();
      return make(url, spec.status || 200, new ReadableStream({
        pull(c) {
          if (i >= spec.chunks.length) { c.close(); return; }
          if (i > 0) ctx.__skew += spec.gap || 0;
          c.enqueue(enc.encode(spec.chunks[i++]));
        },
      }), headers);
    }
    const r = /^bytes=(\d+)-(\d*)$/.exec(asked.get("range") || "");
    if (spec.ranges && r) {
      const body = String(spec.body ?? ""), a = Number(r[1]), b = r[2] ? Math.min(Number(r[2]), body.length - 1) : body.length - 1;
      return make(url, 206, body.slice(a, b + 1), { ...headers, "content-range": `bytes ${a}-${b}/${body.length}` });
    }
    return make(url, spec.status || 200, spec.body ?? "", headers);
  }
  let skipped = false;
  const wins = [];                // the tabs open while the worker starts (a first visit)
  const self = {
    addEventListener: (t, fn) => { handlers[t] = fn; },
    location: { origin: ORIGIN },
    navigator: {},                // (a test sets navigator.connection: the browser's own data saver, 2G)
    registration: {},
    clients: { claim: async () => {}, matchAll: async () => wins.slice() },
    skipWaiting: () => { skipped = true; },
  };
  // In a worker a relative address is read against the worker's own; Node's Request needs it whole.
  class WorkerRequest extends Request {
    constructor(input, init) { super(typeof input === "string" ? new URL(input, ORIGIN).href : input, init); }
  }
  const ctx = vm.createContext({
    self, caches, fetch, Request: WorkerRequest, Response, Headers, URL, console, TransformStream, AbortController,
    setTimeout: (fn, ms, ...a) => (fast ? (queueMicrotask(() => fn(...a)), 0) : setTimeout(fn, ms, ...a)),
    clearTimeout: (t) => { if (t) clearTimeout(t); },
    setInterval: (fn, ms) => { intervalId += 1; intervals.set(intervalId, { fn, ms }); return intervalId; },
    clearInterval: (id) => { intervals.delete(id); },
  });
  // the worker's clock (Date.now) runs __skew ms ahead: a download that "takes" minutes moves it on
  ctx.__skew = 0;
  vm.runInContext("{ const now = Date.now; Date.now = () => now() + __skew; }", ctx);
  vm.runInContext(v === "t1" ? code : build(v), ctx);
  const CONFIG = vm.runInContext("CONFIG", ctx);
  const until = async (waits) => { let n = -1; while (n !== waits.length) { n = waits.length; await Promise.allSettled(waits.slice()); } };

  return {
    CONFIG, store, net, fetched, log, order, hooks, intervals, handlers, wins, self,
    set fast(v) { fast = v; },
    get skipped() { return skipped; },
    cache: (name) => caches.open(name),
    page: (path, spec) => net.set(ORIGIN + path, spec),
    async lifecycle(type) {
      const waits = [];
      handlers[type]({ waitUntil: (p) => waits.push(p) });
      await until(waits);
      return (await Promise.allSettled(waits)).map((x) => x.status);
    },
    async request(path, { navigate = false, method = "GET", headers = {}, settle = true } = {}) {
      const req = new Request(new URL(path, ORIGIN).href, { method, headers });
      if (navigate) Object.defineProperty(req, "mode", { value: "navigate" });
      const waits = [];
      let answer = null;
      handlers.fetch({ request: req, clientId: "", resultingClientId: "tab-1", respondWith: (p) => { answer = p; }, waitUntil: (p) => waits.push(p) });
      if (!answer) return null;
      let res;
      try { res = await answer; } catch (e) { return { error: String(e && e.message || e) }; }
      if (settle) await until(waits);
      return { status: res.status, body: await res.text(), saved: res.headers.get("x-gvlv-saved"), title: res.headers.get("x-gvlv-title"),
               headers: Object.fromEntries(res.headers) };
    },
    async message(data) {
      const replies = [];
      const waits = [];
      handlers.message({ data, ports: [{ postMessage: (m) => replies.push(m) }], source: { id: "tab-1", postMessage: (m) => replies.push(m) },
                         waitUntil: (p) => waits.push(p) });
      await until(waits);
      return replies;
    },
    // a message whose answers aren't waited for: { replies (as they come), settled (once its work is done) };
    // tag: its answers are also noted in `order`; port: false — no MessageChannel port (answers go to event.source)
    send(data, tag = "", { port = true } = {}) {
      const replies = [];
      const waits = [];
      const got = (m) => { replies.push(m); if (tag) order.push(tag + ":" + m.type); };
      handlers.message({ data, ports: port ? [{ postMessage: got }] : [], source: { id: "tab-1", postMessage: got }, waitUntil: (p) => waits.push(p) });
      return { replies, settled: until(waits) };
    },
    async keys(name) { return store.has(name) ? [...store.get(name).m.keys()] : null; },
    // the open tabs being kept after activation (keepOpenTabs), done
    settled: () => Promise.resolve(vm.runInContext("settling", ctx)),
    // the worker's clock moves on
    skew(ms) { ctx.__skew += ms; },
    // a line run inside the worker (a test watching one of its functions)
    run: (src) => vm.runInContext(src, ctx),
  };
}

function shellOnline(w) {
  for (const u of w.CONFIG.shell) {
    const offline = u === w.CONFIG.offline.en || u === w.CONFIG.offline.es;
    w.net.set(ORIGIN + u, offline ? { body: html(u.includes("/es/") ? "Sin conexión" : "Offline", u.includes("/es/") ? "OFFLINE-ES" : "OFFLINE-EN") }
                                  : { body: "/* " + u + " */", ct: /\.css/.test(u) ? "text/css" : /\.js/.test(u) ? "text/javascript" : "application/octet-stream" });
  }
}
const R = {};
"""

WORLD_JS = HARNESS_JS + r"""
/* ---------------- install / activate ---------------- */
{
  const w = world();
  shellOnline(w);
  w.net.set(ORIGIN + B + "assets/fonts/fraunces-latin-opsz-normal.woff2", { status: 404, body: "" });   // an optional file is missing
  R.config = { base: w.CONFIG.base, save: w.CONFIG.save, required: w.CONFIG.required, offline: w.CONFIG.offline, shell: w.CONFIG.shell,
               booth: w.CONFIG.booth };
  R.install = await w.lifecycle("install");

  const nc = world();                                                                                   // install-core.js is missing:
  shellOnline(nc);                                                                                      // pwa.js falls back to links to the steps
  R.coreUrl = nc.CONFIG.shell.find((u) => u.includes("assets/js/install-core.js")) || "";
  nc.net.set(ORIGIN + R.coreUrl, { status: 404, body: "" });
  R.installNoCore = await nc.lifecycle("install");
  R.shellNoCore = await nc.keys("gvlv-shell-t1");
  R.shell = await w.keys("gvlv-shell-t1");
  const off = await w.store.get("gvlv-shell-t1").match(ORIGIN + w.CONFIG.offline.es);
  R.offlineStamped = !!(off && off.headers.get("x-gvlv-saved"));
  R.skippedOnInstall = w.skipped;

  const bad = world();
  shellOnline(bad);
  bad.net.set(ORIGIN + bad.CONFIG.required[0], { status: 404, body: "" });                              // the CSS is missing
  R.installBad = await bad.lifecycle("install");

  for (const n of ["gvlv-shell-t0", "gvlv-static-t0", "gvlv-pages-v1", "gvlv-saved-v1", "gvlv-img-v1", "gvlv-booth-v1", "someone-else"]) await w.store.set(n, new (w.store.get("gvlv-shell-t1").constructor)());
  R.activate = await w.lifecycle("activate");
  R.cachesAfter = [...w.store.keys()].sort();

  /* ---------------- pages ---------------- */
  w.page(B + "meetings/", { body: html("Meetings &amp; more", "ONLINE") });
  R.online = await w.request(B + "meetings/", { navigate: true });
  R.kept = await w.keys("gvlv-pages-v1");
  const copy = await w.store.get("gvlv-pages-v1").match(ORIGIN + B + "meetings/");
  R.keptTitle = copy && decodeURIComponent(copy.headers.get("x-gvlv-title") || "");
  R.howServedOnline = (await w.message({ type: "HOW_SERVED" }))[0];

  w.net.delete(ORIGIN + B + "meetings/");                                                                // the signal is gone
  R.offlineCopy = await w.request(B + "meetings/", { navigate: true });
  R.howServedCopy = (await w.message({ type: "HOW_SERVED" }))[0];
  R.offlineEs = await w.request(B + "es/shop/", { navigate: true });
  R.offlineEn = await w.request(B + "shop/", { navigate: true });

  // an old address's forwarding page (a meta refresh): kept like any page, and marked
  w.page(B + "meeting/", { body: `<!doctype html><html lang="en"><head><meta charset="utf-8"><script>location.replace("${B}meetings/");</script>` +
    `<meta http-equiv="refresh" content="0; url=${B}meetings/"><title>Meetings</title></head><body>MOVED</body></html>` });
  await w.request(B + "meeting/", { navigate: true });
  const fwd = await w.store.get("gvlv-pages-v1").match(ORIGIN + B + "meeting/");
  R.moved = { forwarding: fwd ? fwd.headers.get("x-gvlv-moved") : "not kept", page: copy.headers.get("x-gvlv-moved") };
  w.net.delete(ORIGIN + B + "meeting/");
  R.movedOffline = await w.request(B + "meeting/", { navigate: true });

  w.page(B + "meetings/", { status: 503, body: "Server trouble" });
  R.serverError = await w.request(B + "meetings/", { navigate: true });
  w.page(B + "nope/", { status: 404, body: html("Page not found", "404") });
  R.notFound = await w.request(B + "nope/", { navigate: true });
  R.keptAfter404 = await w.keys("gvlv-pages-v1");

  w.page(B + "meetings/", "hang");                                                                        // a weak signal: no answer in time
  w.fast = true;
  R.slow = await w.request(B + "meetings/", { navigate: true, settle: false });
  w.fast = false;

  /* ---------------- other requests ---------------- */
  R.untouched = {
    otherSite: await w.request("https://www.aagrapevine.org/store", { navigate: true }),
    otherProject: await w.request("/another-project/", { navigate: true }),
    post: await w.request(B + "search.json", { method: "POST" }),
    range: await w.request(B + "assets/audio/x.mp3", { headers: { range: "bytes=0-" } }),
    worker: await w.request(B + "sw.js"),
    manifest: await w.request(B + "manifest.webmanifest"),
    feed: await w.request(B + "feed.xml"),
    buildNote: await w.request(B + "build.json?booth=3"),       // the booth display's "are we online?" check
  };
  R.cssOffline = await w.request(w.CONFIG.required[0]);                                                  // from the app shell
  w.page(B + "assets/img/cover.webp", { body: "IMG", ct: "image/webp" });
  R.imgOnline = await w.request(B + "assets/img/cover.webp");
  w.net.delete(ORIGIN + B + "assets/img/cover.webp");
  R.imgOffline = await w.request(B + "assets/img/cover.webp");
  R.imgNever = await w.request(B + "assets/img/never-seen.webp");
  w.page(B + "search-index.json?x=1", { body: '{"v":1}', ct: "application/json" });
  R.jsonOnline = await w.request(B + "search-index.json?x=1");
  w.net.delete(ORIGIN + B + "search-index.json?x=1");
  R.jsonOffline = await w.request(B + "search-index.json?x=2");

  /* ---------------- a first visit: the open page is kept with its own files; then the signal goes ---------------- */
  const f = world();
  shellOnline(f);
  await f.lifecycle("install");
  const own = [B + "assets/js/home.js?v=t1", B + "assets/vendor/lite-yt-embed.css?v=t1"];
  f.page(B, { body: html("Home", `<script src="${own[0]}" defer></script><link rel="stylesheet" href="${own[1]}">FIRST`) });
  f.page(own[0], { body: "/* home */", ct: "text/javascript" });
  f.page(own[1], { body: "/* lyt */", ct: "text/css" });
  f.wins.push({ url: ORIGIN + B });
  R.firstActivate = await f.lifecycle("activate");
  await f.settled();                                                                                     // (kept after activation)
  for (const u of [B, ...own]) f.net.delete(ORIGIN + u);
  R.firstVisit = { page: await f.request(B, { navigate: true }), js: await f.request(own[0]), css: await f.request(own[1]) };

  /* ---------------- "Save key pages for offline" (Spanish) ---------------- */
  const s = world();
  shellOnline(s);
  await s.lifecycle("install");
  const pages = s.CONFIG.save.filter((p) => !p.includes("{month}"));
  for (const p of pages) s.page(B + "es/" + p, { body: html("ES " + (p || "inicio")) });
  s.page(B + "es/contribute/", "offline");                                                               // one page can't be reached
  const before = s.fetched.length;
  R.saveReplies = await s.message({ type: "SAVE", lang: "es" });
  R.saved = (await s.keys("gvlv-saved-v1")) || [];
  R.savePages = pages;
  R.saveFetchedEnglish = s.fetched.slice(before).some((u) => u.startsWith(ORIGIN + B) && !u.startsWith(ORIGIN + B + "es/") && !u.includes("/assets/"));

  /* ---------------- the stand-in follows the daily content (a content-only deploy: the same worker) ---------------- */
  const o = world();
  shellOnline(o);
  await o.lifecycle("install");
  const EN = ORIGIN + o.CONFIG.offline.en, ES = ORIGIN + o.CONFIG.offline.es;
  const n = (u) => o.fetched.filter((x) => x === u).length;
  const age = (u, hours) => {                                                                            // the copy was stamped that long ago
    const e = o.store.get("gvlv-shell-t1").m.get(u);
    e.headers = e.headers.map(([k, v]) => [k, k === "x-gvlv-saved" ? new Date(Date.now() - hours * 3600e3).toISOString() : v]);
  };
  const standIn = async (path) => marker(await o.request(path, { navigate: true }));                    // a page not saved, no signal for it
  o.net.set(EN, { body: html("Offline", "EN-NEW-ID") });                                                 // the next day's sync: a new meeting ID
  o.net.set(ES, { body: html("Sin conexión", "ES-NEW-ID") });
  for (const p of ["meetings/", "contribute/", "es/meetings/"]) o.page(B + p, { body: html(p) });
  await o.request(B + "meetings/", { navigate: true });
  R.standIn = { sameDay: { fetched: n(EN), shown: await standIn(B + "shop/") } };
  age(EN, 25); age(ES, 25);
  await o.request(B + "meetings/", { navigate: true });
  R.standIn.nextDay = { fetchedEn: n(EN), fetchedEs: n(ES), en: await standIn(B + "shop/"), es: await standIn(B + "es/shop/") };
  await o.request(B + "es/meetings/", { navigate: true });
  R.standIn.spanishPage = { fetchedEs: n(ES), es: await standIn(B + "es/shop/") };
  age(EN, 25);
  let was = n(EN);
  await Promise.all([o.request(B + "meetings/", { navigate: true }), o.request(B + "contribute/", { navigate: true })]);
  R.standIn.twoPagesAtOnce = n(EN) - was;
  // /offline/ itself opened online: its answer is the new copy — a day-old copy or not, and fetched once
  o.net.set(EN, { body: html("Offline", "EN-OPENED") });
  age(EN, 25);
  was = n(EN);
  await o.request(B + "offline/", { navigate: true });
  R.standIn.opened = { fetched: n(EN) - was, shown: await standIn(B + "shop/") };
  o.net.set(EN + "?from=menu", { body: html("Offline", "EN-OPENED-AGAIN") });
  await o.request(B + "offline/?from=menu", { navigate: true });
  R.standIn.openedAgain = await standIn(B + "shop/");
  const kept = await o.store.get("gvlv-shell-t1").match(EN);
  R.standIn.stamped = !!(kept && kept.headers.get("x-gvlv-saved"));
  R.standIn.inPages = ((await o.keys("gvlv-pages-v1")) || []).filter((u) => u.includes("/offline/"));

  /* ---------------- an address without its last slash (typed, or printed: the Spanish poster's …/aagrapevine/es) ---------------- */
  const ns = world();
  shellOnline(ns);
  await ns.lifecycle("install");
  for (const [p, m] of [["meetings/", "EN-MEETINGS"], ["es/meetings/", "ES-MEETINGS"]]) {
    ns.page(B + p, { body: html(p, m) });
    await ns.request(B + p, { navigate: true });
    ns.net.delete(ORIGIN + B + p);                                                                        // then the signal goes
  }
  const at = async (path) => marker(await ns.request(path, { navigate: true }));
  R.noSlash = { es: await at(B + "es"), esMeetings: await at(B + "es/meetings"), meetings: await at(B + "meetings"),
                esShop: await at(B + "es/shop"), shop: await at(B + "shop") };
  ns.page(B + "es/", { body: html("Inicio", "ES-HOME") });
  await ns.request(B + "es/", { navigate: true });
  ns.net.delete(ORIGIN + B + "es/");
  R.noSlash.esKept = await at(B + "es");
  R.noSlash.kept = ((await ns.keys("gvlv-pages-v1")) || []).map((u) => u.slice(ORIGIN.length)).sort();
}
out(R);
"""

# A new version taking over, and the saved pages kept fresh: their own worlds, same harness.
UPDATE_JS = HARNESS_JS + r"""
const kept = async (w, p) => ((await w.keys("gvlv-pages-v1")) || []).includes(ORIGIN + B + p);
// a page opened online, then its script's word as it loads (pwa.js HOW_SERVED — saver: Data saver on; null: an older
// script, which says nothing about it): what starts a round over the saved pages
const opened = async (w, path, saver = false) => {
  await w.request(path, { navigate: true });
  return w.message(saver === null ? { type: "HOW_SERVED" } : { type: "HOW_SERVED", saver });
};
const rel = (u) => u.slice(ORIGIN.length + B.length) || "home";
const aged = (w, pages, days) => {                                    // saved that many days ago
  for (const p of pages) {
    const e = w.store.get("gvlv-saved-v1").m.get(ORIGIN + B + p);
    e.headers = e.headers.map(([n, v]) => [n, n === "x-gvlv-saved" ? new Date(Date.now() - days * 864e5).toISOString() : v]);
  }
};
// a world whose pages were saved a week ago and have changed since; accessibility/: a page to open
const savedWeekAgo = async (pages) => {
  const w = world();
  shellOnline(w);
  await w.lifecycle("install");
  for (const p of pages) w.page(B + p, { body: html(rel(ORIGIN + B + p), "OLD") });
  await w.message({ type: "SAVE", lang: "en" });
  aged(w, pages, 8);
  for (const p of pages) w.page(B + p, { body: html(rel(ORIGIN + B + p), "NEW") });
  w.page(B + "accessibility/", { body: html("Accessibility", "A11Y") });
  return w;
};
const pagesAsked = async (w, go) => {
  const from = w.fetched.length;
  await go();
  return w.fetched.slice(from).map(rel).filter((x) => !x.includes("assets/"));
};
const savedNow = async (w) => ((await w.keys("gvlv-saved-v1")) || []).map(rel);
const copyOf = (w, p) => marker({ body: new TextDecoder().decode(w.store.get("gvlv-saved-v1").m.get(ORIGIN + B + p).body) });
/* ---------------- "Reload" after an update: activation never waits for the open tabs ---------------- */
{
  const u = world();
  shellOnline(u);
  await u.lifecycle("install");
  let release = null;
  u.page(B + "shop/", { body: html("Shop", "SHOP-TAB"), wait: new Promise((r) => { release = r; }) });   // an open tab, its page slow
  u.page(B + "meetings/", { body: html("Meetings", "RELOADED") });
  u.wins.push({ url: ORIGIN + B + "shop/" });
  R.update = { activate: await Promise.race([u.lifecycle("activate"), new Promise((r) => setTimeout(r, 3000, "still waiting"))]) };
  R.update.reload = marker(await u.request(B + "meetings/", { navigate: true, settle: false }));   // the reloaded page: at once
  R.update.keptMeanwhile = await kept(u, "shop/");
  release();
  await u.settled();
  R.update.keptAfter = await kept(u, "shop/");                                                    // the tab, kept afterwards

  const h = world();                                                                               // a tab whose page never comes
  shellOnline(h);
  await h.lifecycle("install");
  h.page(B + "shop/", "hang");
  h.wins.push({ url: ORIGIN + B + "shop/" });
  h.fast = true;                                                                                   // (its time limit: at once)
  R.hang = { activate: await h.lifecycle("activate") };
  await h.settled();
  h.fast = false;
  R.hang.kept = await kept(h, "shop/");
}

/* ---------------- saved pages not opened for a week are fetched again once there is a signal ---------------- */
{
  const k = world();
  shellOnline(k);
  await k.lifecycle("install");
  const PAGES = ["", "meetings/", "monthly/", "contribute/", "shop/"];
  const name = (p) => p.slice(0, -1) || "home";
  for (const p of PAGES) k.page(B + p, { body: html(name(p), "OLD-" + name(p)) });
  await k.message({ type: "SAVE", lang: "en" });
  const entry = (p) => k.store.get("gvlv-saved-v1").m.get(ORIGIN + B + p);
  const age = (p, days) => {
    const e = entry(p);
    e.headers = e.headers.map(([n, v]) => [n, n === "x-gvlv-saved" ? new Date(Date.now() - days * 864e5).toISOString() : v]);
  };
  const copies = () => Object.fromEntries(PAGES.map((p) => [name(p), marker({ body: new TextDecoder().decode(entry(p).body) })]));
  const asked = (from) => k.fetched.slice(from).map((x) => x.slice(ORIGIN.length + B.length) || "home").filter((x) => !x.includes("assets/"));
  for (const p of PAGES) k.page(B + p, { body: html(name(p), "NEW-" + name(p)) });
  k.page(B + "monthly/", { status: 404, body: html("Page not found", "404") });                 // gone: its copy stays
  k.page(B + "accessibility/", { body: html("Accessibility", "A11Y") });
  age("", 8); age("meetings/", 8); age("monthly/", 9); age("contribute/", 2); age("shop/", 10);
  k.page(B + "meetings/", "offline");                                                              // the signal fails on it
  let from = k.fetched.length;
  await opened(k, B + "accessibility/");                                                            // a page opened online
  R.refresh = { weak: { copies: copies(), asked: asked(from) } };
  from = k.fetched.length;
  await opened(k, B + "accessibility/");                                                            // again soon: no new round
  R.refresh.soon = asked(from);
  k.page(B + "meetings/", { body: html("meetings", "NEW-meetings") });
  k.skew(7 * 3600e3);                                                                              // 7 hours later
  from = k.fetched.length;
  await opened(k, B + "accessibility/");
  R.refresh.later = { copies: copies(), asked: asked(from) };
  R.refresh.stamped = Math.abs(Date.now() - Date.parse(entry("shop/").headers.find(([n]) => n === "x-gvlv-saved")[1])) < 60e3;   // (stamped now)
}

/* ---------------- a saved page whose new copy's own files don't come keeps its old copy ---------------- */
{
  const k = world();
  shellOnline(k);
  await k.lifecycle("install");
  k.page(B + "shop/", { body: html("shop", "OLD-shop") });
  k.page(B + "meetings/", { body: html("meetings", "OLD-meetings") });
  await k.message({ type: "SAVE", lang: "en" });
  const entry = (p) => k.store.get("gvlv-saved-v1").m.get(ORIGIN + B + p);
  for (const p of ["shop/", "meetings/"]) {
    const e = entry(p);
    e.headers = e.headers.map(([n, v]) => [n, n === "x-gvlv-saved" ? new Date(Date.now() - 8 * 864e5).toISOString() : v]);
  }
  const copy = (p) => marker({ body: new TextDecoder().decode(entry(p).body) });
  const SCRIPT = `<script src="${B}assets/js/shop.js?v=t2"></script>`;                 // a new version's script …
  k.page(B + "shop/", { body: html("shop", "NEW-shop" + SCRIPT) });                    // … not reachable yet
  k.page(B + "meetings/", { body: html("meetings", "NEW-meetings") });
  k.page(B + "accessibility/", { body: html("Accessibility", "A11Y") });
  await opened(k, B + "accessibility/");
  R.partial = { shop: copy("shop/"), meetings: copy("meetings/") };
  k.page(B + "assets/js/shop.js?v=t2", { body: "/* shop */", ct: "text/javascript" });   // there now
  k.skew(7 * 3600e3);
  await opened(k, B + "accessibility/");
  R.partial.later = copy("shop/");
  R.partial.script = ((await k.keys("gvlv-saved-assets-v1")) || []).includes(ORIGIN + B + "assets/js/shop.js?v=t2");
}

/* ---------------- Data saver on: no round (the page's word; an older page's: the browser's) ---------------- */
{
  const k = await savedWeekAgo(["", "meetings/", "shop/"]);
  const go = (saver) => pagesAsked(k, () => opened(k, B + "accessibility/", saver));
  R.saver = { on: await go(true) };                                                   // the visitor's Data saver
  k.self.navigator.connection = { saveData: true };                                   // the browser's own data saver …
  R.saver.browser = await go(null);                                                   // … an older page's script says nothing
  k.self.navigator.connection = { saveData: false, effectiveType: "2g" };
  R.saver.slow = await go(null);
  k.net.delete(ORIGIN + B + "accessibility/");
  R.saver.offline = await go(false);                                                  // the stand-in answered: no signal
  k.page(B + "accessibility/", { body: html("Accessibility", "A11Y") });
  R.saver.unsaid = await pagesAsked(k, () => k.request(B + "accessibility/", { navigate: true }));   // no word yet
  R.saver.off = await go(false);                     // off: the visitor's choice (over the browser's 2G) — the round
  R.saver.copies = ["", "meetings/", "shop/"].map((p) => copyOf(k, p));
}

/* ---------------- a save stops a running round, and none starts beside it ---------------- */
{
  const k = await savedWeekAgo(["", "meetings/", "shop/"]);
  let release = null, homes = 0;
  const at = [];                                                                       // the round's, then the save's, on home
  const onHome = [new Promise((r) => { at[0] = r; }), new Promise((r) => { at[1] = r; })];
  k.page(B, { body: html("home", "NEW"), wait: new Promise((r) => { release = r; }) });          // a slow first page
  k.hooks.onFetch = (u) => { if (u === ORIGIN + B && homes < 2) at[homes++](); };
  await k.request(B + "accessibility/", { navigate: true });
  const from = k.fetched.length;
  const round = k.send({ type: "HOW_SERVED", saver: false });
  await onHome[0];                                                                     // the round is on its first page …
  const save = k.send({ type: "SAVE", lang: "en" });                                   // … when "Save key pages" is tapped
  await onHome[1];
  const during = await pagesAsked(k, () => opened(k, B + "accessibility/"));           // a page opened meanwhile: no round
  release();
  await save.settled;
  await round.settled;
  const n = (p) => k.fetched.slice(from).filter((u) => u === ORIGIN + B + p).length;
  R.lock = { fetched: { home: n(""), meetings: n("meetings/"), shop: n("shop/") }, during,
             copies: ["", "meetings/", "shop/"].map((p) => copyOf(k, p)), done: save.replies[save.replies.length - 1].type };
}

/* ---------------- a round stopped by a save leaves the pruning of the saved files to it ---------------- */
{
  const k = await savedWeekAgo(["", "meetings/", "shop/"]);
  let release = null, reached = null;
  const onMeetings = new Promise((r) => { reached = r; });
  k.page(B + "meetings/", { body: html("meetings", "NEW"), wait: new Promise((r) => { release = r; }) });   // slow
  k.hooks.onFetch = (u) => { if (u === ORIGIN + B + "meetings/") reached(); };
  k.run("globalThis.__prunes = 0; { const prune = pruneSavedAssets; pruneSavedAssets = () => { __prunes += 1; return prune(); }; }");
  await k.request(B + "accessibility/", { navigate: true });
  const round = k.send({ type: "HOW_SERVED", saver: false });
  await onMeetings;                                                     // home refreshed; the round is on meetings/ …
  const save = k.send({ type: "SAVE", lang: "en" });                    // … when "Save key pages" is tapped
  release();
  await save.settled;
  await round.settled;
  R.stoppedPrune = { prunes: k.run("__prunes"), copies: ["", "meetings/", "shop/"].map((p) => copyOf(k, p)),
                     done: save.replies[save.replies.length - 1].type };
}

/* ---------------- a page removed while the round runs stays removed ---------------- */
{
  const k = await savedWeekAgo(["", "meetings/", "contribute/", "shop/"]);
  const drop = (p) => k.store.get("gvlv-saved-v1").m.delete(ORIGIN + B + p);
  // removed before the round reaches it (meetings/), and while it downloads (shop/)
  k.hooks.onFetch = (u) => { if (u === ORIGIN + B) drop("meetings/"); if (u === ORIGIN + B + "shop/") drop("shop/"); };
  R.removed = { asked: await pagesAsked(k, () => opened(k, B + "accessibility/")), saved: await savedNow(k) };
}

/* ---------------- a page kept (opened, not saved) keeps its own stylesheet offline after new versions ---------------- */
{
  const a = world();
  shellOnline(a);
  await a.lifecycle("install");
  await a.lifecycle("activate");
  const AREA = B + "assets/css/monthly.css?v=t1", JS = B + "assets/js/monthly.js?v=t1";
  a.page(B + "monthly/2026-11/", { body: html("November", `<link rel="stylesheet" href="${AREA}"><script src="${JS}"></script>NOV`) });
  a.page(AREA, { body: "/* monthly t1 */", ct: "text/css" });
  a.page(JS, { body: "/* monthly */", ct: "text/javascript" });
  await a.request(B + "monthly/2026-11/", { navigate: true });
  await a.request(AREA);                                                               // (the page's files, as the
  await a.request(JS);                                                                 //  browser asks for them)
  R.carry = {};
  let c = null;
  for (const v of ["t2", "t3"]) {                                                      // two new versions on this device
    c = world({ v, store: a.store });
    shellOnline(c);
    await c.lifecycle("install");
    R.carry[v] = await c.lifecycle("activate");
  }
  // then the signal is gone (t3's network knows nothing but its app shell's addresses)
  for (const u of [...c.net.keys()]) c.net.delete(u);
  R.carry.page = marker(await c.request(B + "monthly/2026-11/", { navigate: true }));
  R.carry.css = await c.request(AREA);
  R.carry.main = (await c.request(B + "assets/css/main.css?v=t1")).body;
  R.carry.caches = [...a.store.keys()].filter((n) => /^gvlv-(shell|static)-/.test(n)).sort();
  R.carry.static = ((await c.keys("gvlv-static-t3")) || []).map((u) => u.slice(ORIGIN.length));
}
out(R);
"""

# The booth display's offline copy (class Booth): its own worlds, same harness.
BOOTH_JS = HARNESS_JS + r"""
/* ---------------- the booth display (the About page's #booth): its offline copy, gvlv-booth-v1 ---------------- */
const MEDIA = B + "about/booth/media/", SHOW = B + "about/booth.json";
const abs = (p) => ORIGIN + p;
const rel = (u) => u.replace(ORIGIN, "");
const show = (v) => ({ body: `{"version":"${v}"}`, ct: "application/json" });                       // 16 bytes (a 2-character v)
const aboutPage = (title, mark) => ({ body: `<!doctype html><html><head><title>${title}</title><link rel="stylesheet" href="${B}assets/css/main.css?v=t1">` +
  `<script src="${B}assets/js/app.js?v=t1"></script><script src="${B}assets/js/booth.js?v=t1" defer></script></head><body>${mark}</body></html>` });
const bodyOf = async (w, name, path) => { const c = w.store.get(name); const r = c && (await c.match(abs(path))); return r ? r.text() : null; };
const keptIn = async (w, name) => ((await w.keys(name)) || []).map(rel).sort();
const booted = async () => { const w = world(); shellOnline(w); await w.lifecycle("install"); return w; };
{
  const b = await booted();
  const vid = MEDIA + "a1b2c3-welcome.mp4", pic = MEDIA + "d4e5f6-table.jpg", lost = MEDIA + "a0a0a0-lost.mp4";
  const thumb = B + "assets/cache/pod/ep1.webp";
  const VIDEO = "0123456789".repeat(100);                                                                  // 1000 bytes: byte i is the digit i % 10
  b.page(SHOW, show("v1"));
  b.page(vid, { body: VIDEO, ct: "video/mp4" });
  b.page(pic, { body: "p".repeat(300), ct: "image/jpeg" });
  b.page(thumb, { body: "t".repeat(50), ct: "image/webp" });
  b.page(lost, { status: 404, body: "Not found" });
  b.page(B + "about/", aboutPage("About", "ABOUT-EN"));
  b.page(B + "es/about/", aboutPage("Acerca de", "ABOUT-ES"));
  b.page(B + "assets/js/booth.js?v=t1", { body: "/* booth */", ct: "text/javascript" });
  const pages = [abs(B + "about/"), abs(B + "es/about/")];
  // other sites, another Pages project, a file twice, the photo again by its address from the base: left out
  const files = [abs(SHOW), abs(vid), abs(pic), abs(thumb), abs(lost), "https://www.youtube.com/watch?v=abc", abs("/another-project/x.mp4"),
                 abs(vid), "about/booth/media/d4e5f6-table.jpg"];
  const n0 = b.log.length;
  const save = await b.message({ type: "BOOTH_SAVE", pages, files, prune: true });
  R.booth = {
    save: save.map((m) => (m.type === "BOOTH_PROGRESS" ? [m.done, m.total, m.bytes] : m)),
    asked: b.log.slice(n0).map((x) => rel(x.url)),
    kept: await keptIn(b, "gvlv-booth-v1"),
    saved: await keptIn(b, "gvlv-saved-v1"),
    assets: await keptIn(b, "gvlv-saved-assets-v1"),
  };

  // offline: the About page (either language, the kiosk address too) from its saved copy, its script, the show, the posters
  for (const p of [B + "about/", B + "es/about/", B + "assets/js/booth.js?v=t1", SHOW, vid, pic, thumb]) b.net.delete(abs(p));
  const aboutEn = await b.request(B + "about/", { navigate: true });
  R.booth.offline = {
    about: [marker(aboutEn), !!aboutEn.saved],
    aboutEs: marker(await b.request(B + "es/about/?booth=start", { navigate: true })),
    script: (await b.request(B + "assets/js/booth.js?v=t1")).body,
    show: (await b.request(SHOW + "?t=17")).body,
    thumb: (await b.request(thumb)).body,
    pic: (await b.request(pic)).body.length,
  };

  // the video: the saved copy first (the site has another one now — never asked), in the parts a media player asks for
  b.page(vid, { body: "THE-SITE-HAS-ANOTHER-COPY", ct: "video/mp4" });
  const n1 = b.log.length;
  const part = async (range) => {
    const r = await b.request(vid, { headers: range === null ? {} : { range } });
    return { status: r.status, body: r.body, range: r.headers["content-range"] || null, length: r.headers["content-length"] || null,
             accept: r.headers["accept-ranges"] || null, type: r.headers["content-type"] || null };
  };
  R.booth.ranges = {
    whole: await part(null), first100: await part("bytes=0-99"), tail: await part("bytes=990-"), last10: await part("bytes=-10"),
    clamped: await part("bytes=900-5000"), bigSuffix: await part("bytes=-5000"), spaced: await part("bytes = 10 - 19"),
    pastEnd: await part("bytes=1000-"), farPast: await part("bytes=2000-3000"), lastZero: await part("bytes=-0"),
    backwards: await part("bytes=9-3"), several: await part("bytes=0-1,5-6"), otherUnit: await part("items=0-5"),
  };
  R.booth.rangesAskedSite = b.log.slice(n1).length;

  // a file not saved: the network, its range passed on — and never kept
  const fresh = MEDIA + "b7b7b7-new.mp4";
  b.page(fresh, { body: "NEW-VIDEO-BYTES", ct: "video/mp4", ranges: true });
  const n2 = b.log.length;
  const net = await b.request(fresh, { headers: { range: "bytes=0-3" } });
  R.booth.notSaved = {
    answer: [net.status, net.body, net.headers["content-range"] || null],
    asked: b.log.slice(n2).map((x) => [rel(x.url), x.range]),
    keptIn: [...b.store.entries()].filter(([, c]) => c.m.has(abs(fresh))).map(([n]) => n),
  };
  b.net.delete(abs(fresh));
  R.booth.notSavedOffline = await b.request(fresh, { headers: { range: "bytes=0-" } });

  // saved again (the show listed last): the show first and fetched again, like the thumbnail ("no-cache");
  // the video and the photo are kept already — not fetched
  b.page(B + "about/", aboutPage("About", "ABOUT-EN-2"));
  b.page(B + "es/about/", aboutPage("Acerca de", "ABOUT-ES-2"));
  b.page(SHOW, show("v2"));
  b.page(thumb, { body: "T".repeat(60), ct: "image/webp" });
  b.page(vid, { body: "NEVER-FETCHED", ct: "video/mp4" });
  b.page(pic, { body: "NEVER-FETCHED", ct: "image/jpeg" });
  const n3 = b.log.length;
  const again = await b.message({ type: "BOOTH_SAVE", pages, files: [abs(vid), abs(pic), abs(thumb), abs(SHOW)] });
  R.booth.again = {
    done: again.at(-1),
    asked: b.log.slice(n3).map((x) => [rel(x.url), x.cache]),
    show: await bodyOf(b, "gvlv-booth-v1", SHOW),
    video: (await bodyOf(b, "gvlv-booth-v1", vid)) === VIDEO,
    thumb: await bodyOf(b, "gvlv-booth-v1", thumb),
    about: await bodyOf(b, "gvlv-saved-v1", B + "about/"),
  };

  // prune: the new show no longer uses the photo or the thumbnail — they go once it is saved, before the new file downloads
  const added = MEDIA + "c8c8c8-new.jpg";
  b.page(SHOW, show("v3"));
  b.page(added, { body: "n".repeat(40), ct: "image/jpeg" });
  let whenAdded = null;
  b.hooks.onFetch = (url) => { if (url === abs(added)) whenAdded = [...b.store.get("gvlv-booth-v1").m.keys()].map(rel).sort(); };
  const pruning = await b.message({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(vid), abs(added)], prune: true });
  b.hooks.onFetch = null;
  R.booth.prune = { done: pruning.at(-1), kept: await keptIn(b, "gvlv-booth-v1"), whenAdded };
  // …but not while the show can't be fetched (the copy keeps what its show still names); a list without files prunes nothing
  b.page(SHOW, { status: 500, body: "Server trouble" });
  const stale = await b.message({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(vid)], prune: true });
  R.booth.noPrune = { done: stale.at(-1), kept: await keptIn(b, "gvlv-booth-v1"), show: await bodyOf(b, "gvlv-booth-v1", SHOW) };
  b.page(B + "about/", aboutPage("About", "ABOUT-EN-3"));
  const pagesOnly = await b.message({ type: "BOOTH_SAVE", pages: [abs(B + "about/")], files: [], prune: true });
  R.booth.emptyList = { done: pagesOnly.at(-1), kept: await keptIn(b, "gvlv-booth-v1") };

  // how much of a list is saved
  const absent = Array.from({ length: 25 }, (_, i) => abs(MEDIA + `zz${i}.jpg`));
  R.booth.absent = absent;
  R.booth.status = (await b.message({ type: "BOOTH_STATUS", files: [abs(SHOW), abs(vid), abs(added), ...absent, "https://elsewhere.test/x.jpg"] }))[0];

  // 30 files that can't be saved: the first 20 listed
  b.page(SHOW, show("v4"));
  const broken = Array.from({ length: 30 }, (_, i) => abs(MEDIA + `bad${i}.mp4`));
  R.booth.broken = broken;
  const capped = await b.message({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), ...broken] });
  R.booth.capped = { done: capped.at(-1), progress: capped.filter((m) => m.type === "BOOTH_PROGRESS").length };

  // the copy removed: nothing of it answers any more; the About page stays among the saved pages
  R.booth.clear = await b.message({ type: "BOOTH_CLEAR" });
  R.booth.afterClear = {
    status: (await b.message({ type: "BOOTH_STATUS", files: [abs(SHOW)] }))[0],
    cache: b.store.has("gvlv-booth-v1"),
    saved: await keptIn(b, "gvlv-saved-v1"),
  };
  b.net.delete(abs(vid));
  R.booth.afterClear.video = await b.request(vid, { headers: { range: "bytes=0-" } });
}

/* ---------------- the show (/about/booth.json): network first; offline the booth's copy, then the data cache's ---------------- */
{
  const j = await booted();
  const text = async (path, opts) => { const r = await j.request(path, opts); return r.error ? "ERROR" : r.body; };
  const S = {};
  S.none = await text(SHOW);                                                                                // offline, no copy anywhere
  j.page(SHOW + "?t=1", show("n1"));
  S.online = await text(SHOW + "?t=1");
  S.dataKeys = await keptIn(j, "gvlv-data-v1");                                                            // kept without its ?query
  S.boothCache = j.store.has("gvlv-booth-v1");                                                             // no empty copy made
  j.net.delete(abs(SHOW + "?t=1"));
  S.offlineData = await text(SHOW);
  j.page(SHOW, show("v1"));
  await j.message({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW)] });                                   // the booth saves its copy
  j.page(SHOW, show("v2"));
  S.online2 = await text(SHOW);
  S.copies = { booth: await bodyOf(j, "gvlv-booth-v1", SHOW), data: await bodyOf(j, "gvlv-data-v1", SHOW) };
  await j.store.get("gvlv-data-v1").put(abs(SHOW), new Response("DATA-COPY", { headers: { "content-type": "application/json" } }));
  j.net.delete(abs(SHOW));
  S.offline = await text(SHOW + "?t=2");
  j.page(SHOW, "hang");                                                                                     // no answer in time
  j.fast = true;
  S.slow = await text(SHOW, { settle: false });
  j.fast = false;
  j.page(SHOW, { status: 503, body: "Server trouble" });
  S.serverError = await text(SHOW);
  await j.message({ type: "BOOTH_CLEAR" });
  j.net.delete(abs(SHOW));
  S.afterClear = await text(SHOW);
  j.page(SHOW, show("v3"));
  S.onlineAfterClear = await text(SHOW);
  S.boothAfterClear = j.store.has("gvlv-booth-v1");                                                         // not brought back by the show
  S.dataAfterClear = await bodyOf(j, "gvlv-data-v1", SHOW);
  R.boothShow = S;
}

/* ---------------- the booth's long saves ---------------- */
{
  const L = {};
  // a big video's news while it downloads: bytes growing, `done` unchanged
  const k = await booted();
  const big = MEDIA + "d9d9d9-big.mp4";
  k.page(SHOW, show("v1"));
  k.page(big, { chunks: ["a".repeat(100), "b".repeat(100), "c".repeat(100), "d".repeat(100)], gap: 2500, ct: "video/mp4" });
  const news = await k.message({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(big)] });
  L.news = news.map((m) => [m.type, m.done, m.bytes]);
  L.big = ((await bodyOf(k, "gvlv-booth-v1", big)) || "").length;

  // four minutes gone: no new file starts — BOOTH_DONE says "more" — and the next save goes on from there
  const t = await booted();
  const [m1, m2, m3] = ["e1", "e2", "e3"].map((x) => MEDIA + x + ".jpg");
  t.page(SHOW, show("v1"));
  t.page(m1, { body: "1".repeat(10), ct: "image/jpeg", takes: 5 * 60e3 });                                  // arrives five minutes later
  t.page(m2, { body: "2".repeat(10), ct: "image/jpeg" });
  t.page(m3, { body: "3".repeat(10), ct: "image/jpeg" });
  const list = [abs(SHOW), abs(m1), abs(m2), abs(m3)];
  L.list = list;
  const first = await t.message({ type: "BOOTH_SAVE", pages: [], files: list });
  const n = t.log.length;
  const next = await t.message({ type: "BOOTH_SAVE", pages: [], files: list });
  L.more = { first: first.at(-1), next: next.at(-1), nextAsked: t.log.slice(n).map((x) => rel(x.url)) };

  // the device is full: the save stops (nothing more is downloaded) and says so
  const q = await booted();
  q.page(SHOW, show("v1"));
  for (const m of [m1, m2, m3]) q.page(m, { body: "x".repeat(10), ct: "image/jpeg" });
  (await q.cache("gvlv-booth-v1")).room = 2;
  const full = await q.message({ type: "BOOTH_SAVE", pages: [], files: list });
  L.full = { done: full.at(-1), asked: q.log.map((x) => rel(x.url)).filter((u) => u.includes("/booth")) };

  // a video whose download breaks off: fetched once more, and kept whole
  const f = await booted();
  const flaky = MEDIA + "a9a9a9-flaky.mp4";
  f.page(flaky, { body: "F".repeat(500), ct: "video/mp4", breaksOnce: true });
  const flakyDone = await f.message({ type: "BOOTH_SAVE", pages: [], files: [abs(flaky)] });
  L.flaky = { done: flakyDone.at(-1), asked: f.log.filter((x) => x.url === abs(flaky)).length, kept: await bodyOf(f, "gvlv-booth-v1", flaky) };

  // a removal stops the saves asked before it (the download under way is let go); a save asked after it runs
  const c = await booted();
  const slow = MEDIA + "f0f0f0-slow.mp4";
  c.page(SHOW, show("v1"));
  c.page(slow, "hang");
  c.page(m2, { body: "2".repeat(10), ct: "image/jpeg" });
  const running = c.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(slow), abs(m2)] }, "running");
  while (!c.log.some((x) => x.url === abs(slow))) await new Promise((r) => setImmediate(r));
  const waiting = c.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(m2)] }, "waiting");
  const clear = c.send({ type: "BOOTH_CLEAR" }, "clear");
  await Promise.all([running.settled, waiting.settled, clear.settled]);
  const after = c.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(m2)] }, "after");
  await after.settled;
  L.clear = {
    slow: abs(slow),
    running: running.replies.at(-1), waiting: waiting.replies.at(-1), cleared: clear.replies, after: after.replies.at(-1),
    order: c.order.filter((x) => !x.endsWith("PROGRESS")),
    m2Asked: c.log.filter((x) => x.url === abs(m2)).length,
    kept: await keptIn(c, "gvlv-booth-v1"),
  };

  // two saves at once: one after the other — the second finds the files kept (nothing downloaded twice)
  const d = await booted();
  d.page(SHOW, show("v1"));
  d.page(m1, { body: "1".repeat(10), ct: "image/jpeg" });
  const one = d.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(m1)] }, "one");
  const two = d.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(m1)] }, "two");
  await Promise.all([one.settled, two.settled]);
  L.twice = { first: [one.replies[0], two.replies[0]], order: d.order.slice(), m1Asked: d.log.filter((x) => x.url === abs(m1)).length,
              done: [one.replies.at(-1), two.replies.at(-1)] };

  // a save waiting for its turn keeps saying so (every 10 s) — and stops once its turn comes
  const g = await booted();
  let open = null;
  const held = MEDIA + "b1b1b1-held.mp4";
  g.page(SHOW, show("v1"));
  g.page(held, { body: "h".repeat(10), ct: "video/mp4", wait: new Promise((r) => { open = r; }) });   // arrives when let through
  const ahead = g.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW), abs(held)] }, "ahead");
  while (!g.log.some((x) => x.url === abs(held))) await new Promise((r) => setImmediate(r));
  const behind = g.send({ type: "BOOTH_SAVE", pages: [], files: [abs(SHOW)] }, "behind");
  const beats = [...g.intervals.values()];
  for (let i = 0; i < 2; i++) for (const b of beats) b.fn();                                               // 20 s go by
  L.waiting = { every: beats.map((b) => b.ms), meanwhile: behind.replies.map((m) => [m.type, m.done]) };
  open();
  await Promise.all([ahead.settled, behind.settled]);
  L.waiting.after = behind.replies.map((m) => [m.type, m.done ?? null]);
  L.waiting.timersLeft = g.intervals.size;

  // no MessageChannel port: the answer goes to the page that asked (event.source), as for SAVE
  const p = d.send({ type: "BOOTH_STATUS", files: [abs(SHOW)] }, "", { port: false });
  await p.settled;
  L.noPort = p.replies;
  R.boothLong = L;
}
out(R);
"""

# pwa.js on a pretend page, talking to a pretend worker: boot({ lang, waiting, installing }) → { tick(ms) (the clock
# moves on and the timers due by then run), click(button(act)) (a [data-pwa-act] control), announced (GV.announce),
# saves() (the SAVE messages posted, each with its reply port: port.peer.onmessage({ data }) is the worker answering),
# activate() (installing: the worker is in charge at last), reloads, sw (the service worker container's listeners:
# controllerchange) }. The page is loaded; the worker registers at tick(0).
PAGE_JS = r"""
import vm from "node:vm";
// ua: the device (install-core.js, window.GVInstall, then says which); app: running as the installed app; connection:
// navigator.connection (the browser's own data saver, 2G)
function boot({ lang = "en", waiting = null, installing = false, storage = undefined, ua = "", app = false, connection = undefined } = {}) {
  const clock = { now: Date.parse("2026-10-03T20:00:00Z") };
  let activate = () => {};
  let timers = [], seq = 0;
  class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(clock.now); } static now() { return clock.now; } }
  const announced = [], posted = [], reloads = { n: 0 }, sw = {}, docL = {}, winL = {};
  const on = (bag) => (t, fn) => { (bag[t] ||= []).push(fn); };
  class El {
    constructor(tag) {
      this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.hidden = false; this.innerHTML = ""; this.className = "";
      const s = new Set();
      this.classList = { add: (...c) => c.forEach((x) => s.add(x)), remove: (...c) => c.forEach((x) => s.delete(x)),
                         toggle: (c, v) => ((v === undefined ? !s.has(c) : v) ? s.add(c) : s.delete(c)), contains: (c) => s.has(c) };
      this.style = { setProperty() {}, removeProperty() {} };
    }
    getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
    setAttribute(n, v) { this.attrs[n] = String(v); }
    hasAttribute(n) { return n in this.attrs; }
    removeAttribute(n) { delete this.attrs[n]; }
    addEventListener() {}
    appendChild(c) { return c; }
    contains(o) { return o === this; }
    closest() { return null; }
    querySelector() { return null; }
    querySelectorAll() { return []; }
    getBoundingClientRect() { return { width: 320, height: this.hidden ? 0 : 56 }; }
    focus() {}
  }
  const root = new El("html"), body = new El("body");
  root.lang = lang;
  const document = { documentElement: root, body, readyState: "complete", hidden: false, visibilityState: "visible", activeElement: body,
                     querySelector: () => null, querySelectorAll: () => [], getElementById: () => null, createElement: (t) => new El(t),
                     addEventListener: on(docL) };
  const active = { state: "activated", postMessage(msg, ports) { posted.push({ msg, port: ports && ports[0] }); } };
  const reg = { active, waiting, installing: null, addEventListener() {}, update: () => Promise.resolve() };
  // installing: a first visit — no worker in charge yet, `ready` waits until activate()
  const ready = installing ? new Promise((r) => { activate = () => r(reg); }) : Promise.resolve(reg);
  const serviceWorker = { controller: installing ? null : active, ready, register: () => Promise.resolve(reg), addEventListener: on(sw) };
  class MessageChannel { constructor() { this.port1 = {}; this.port2 = { peer: this.port1 }; } }
  class MutationObserver { observe() {} disconnect() {} }
  const store = { getItem: () => null, setItem() {}, removeItem() {} };
  const path = "/aagrapevine/" + (lang === "es" ? "es/" : "") + "meetings/";
  const ctx = {
    console, URL, Date: FakeDate, document, MessageChannel, MutationObserver,
    navigator: { onLine: true, serviceWorker, userAgent: ua, maxTouchPoints: /iPhone|iPad|Android/.test(ua) ? 5 : 0, storage, connection,
                 standalone: app || undefined },
    location: { pathname: path, search: "", hash: "", href: "https://example.test" + path, reload: () => { reloads.n += 1; } },
    history: { state: null, replaceState() {} }, sessionStorage: store, localStorage: store, isSecureContext: true,
    caches: { has: () => Promise.resolve(false), open: () => Promise.resolve({ keys: () => Promise.resolve([]) }) },
    GV: { announce: (m) => announced.push(m) }, SITE: { lang, base: "/aagrapevine/" },
    matchMedia: () => ({ matches: false }), requestAnimationFrame: () => 0, screen: { width: 390, height: 844 }, scrollY: 0,
    performance: { getEntriesByType: () => [] }, addEventListener: on(winL), removeEventListener() {},
    setTimeout: (fn, ms, ...a) => { seq += 1; timers.push({ id: seq, fn, a, at: clock.now + (ms || 0) }); return seq; },
    clearTimeout: (id) => { timers = timers.filter((t) => t.id !== id); },
    setInterval: () => 0, clearInterval() {},
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  if (ua) vm.runInContext(fs.readFileSync("src/assets/js/install-core.js", "utf8"), ctx, { filename: "install-core.js" });
  vm.runInContext(fs.readFileSync("src/assets/js/pwa.js", "utf8"), ctx, { filename: "pwa.js" });
  const flush = () => new Promise((r) => setImmediate(r));
  const tick = async (ms) => {
    const end = clock.now + ms;
    for (;;) {
      await flush();
      timers.sort((x, y) => x.at - y.at || x.id - y.id);
      if (!timers.length || timers[0].at > end) break;
      const t = timers.shift();
      clock.now = t.at;
      t.fn(...t.a);
    }
    clock.now = end;
    await flush();
  };
  const button = (act) => ({ disabled: false, closest() { return this; }, hasAttribute: () => false, getAttribute: (n) => (n === "data-pwa-act" ? act : null) });
  const click = async (b) => { for (const fn of docL.click || []) fn({ target: b, preventDefault() {} }); await flush(); return b; };
  return { announced, reloads, sw, tick, click, button, activate: () => activate(), saves: () => posted.filter((p) => p.msg.type === "SAVE"), docL,
           posted };
}
const R = {};

/* ---------------- "Save key pages" on a weak signal: 15 pages, one every 6 s (90 s in all) ---------------- */
{
  const p = boot({ lang: "es" });
  await p.tick(0);
  await p.click(p.button("save"));
  const port = p.saves()[0].port.peer;
  port.onmessage({ data: { type: "SAVE_PROGRESS", done: 0, total: 15 } });
  for (let i = 1; i <= 15; i++) { await p.tick(6000); port.onmessage({ data: { type: "SAVE_PROGRESS", done: i, total: 15 } }); }
  port.onmessage({ data: { type: "SAVE_DONE", saved: 15, total: 15, failed: [] } });
  await p.tick(0);
  R.slow = { saves: p.saves().length, said: p.announced.slice() };
}

/* ---------------- a save that stops giving news: given up after 45 s of silence; then tapped again ---------------- */
{
  const p = boot({ lang: "es" });
  await p.tick(0);
  await p.click(p.button("save"));
  const first = p.saves()[0].port.peer;
  first.onmessage({ data: { type: "SAVE_PROGRESS", done: 0, total: 15 } });
  await p.tick(20000);
  first.onmessage({ data: { type: "SAVE_PROGRESS", done: 1, total: 15 } });
  await p.tick(44000);
  const quiet = p.announced.slice(1);                                             // 44 s without news: still saving
  await p.tick(2000);
  const gaveUp = p.announced.slice(1);
  first.onmessage({ data: { type: "SAVE_PROGRESS", done: 2, total: 15 } });      // that save's late news …
  await p.click(p.button("save"));                                                // … and "Try again": a new save
  const second = p.saves()[1] && p.saves()[1].port.peer;
  first.onmessage({ data: { type: "SAVE_DONE", saved: 15, total: 15, failed: [] } });   // the first one's end is not this one's
  if (second) {
    second.onmessage({ data: { type: "SAVE_PROGRESS", done: 0, total: 15 } });
    await p.tick(3000);
    second.onmessage({ data: { type: "SAVE_DONE", saved: 14, total: 15, failed: ["/aagrapevine/es/shop/"] } });
  }
  await p.tick(0);
  R.stalled = { quiet, gaveUp, saves: p.saves().length, said: p.announced.slice() };
}

/* ---------------- a first visit: tapped while the worker is still installing, which takes longer than 45 s ---------------- */
{
  const p = boot({ lang: "es", installing: true });
  await p.tick(0);
  await p.click(p.button("save"));
  await p.tick(46000);
  const gaveUp = p.announced.slice(1);
  p.activate();                                                                   // the worker is in charge at last
  await p.tick(0);
  const behindTheBack = p.saves().length;                                         // no save the page no longer follows
  await p.click(p.button("save"));
  R.late = { gaveUp, behindTheBack, saves: p.saves().length };
}

/* ---------------- a new version: "Reload" applies it; in a second tab, after the first has, "Reload" reloads ---------------- */
for (const [name, appliedElsewhere] of [["update", false], ["secondTab", true]]) {
  const w = { state: "installed", sent: [], postMessage(m) { this.sent.push(m.type); } };
  const p = boot({ waiting: w });
  await p.tick(0);                                                                // the "Updated — Reload" toast
  const offered = p.announced.slice();
  if (appliedElsewhere) {
    w.state = "activated";                                                        // the other tab chose Reload …
    for (const fn of p.sw.controllerchange || []) fn();                           // … and the new version claimed this one too
  }
  const before = p.reloads.n;
  const b = await p.click(p.button("update"));
  const pressed = { reloads: p.reloads.n - before, sent: w.sent.slice(), disabled: b.disabled };
  if (!appliedElsewhere) {
    w.state = "activated";
    for (const fn of p.sw.controllerchange || []) fn();                           // it takes over: this tab reloads
  }
  R[name] = { offered, before, pressed, reloads: p.reloads.n };
}

/* ---------------- "Save key pages" asks the browser to keep them (navigator.storage.persist) ---------------- */
const saveWith = async (lang, persist, late, device = {}) => {
  let answer = null, asked = 0;
  const storage = persist === undefined ? undefined : { persist: () => { asked += 1; return late ? new Promise((r) => { answer = () => r(persist); }) : Promise.resolve(persist); } };
  const p = boot({ lang, storage, ...device });
  await p.tick(0);
  await p.click(p.button("save"));
  const port = p.saves()[0].port.peer;
  port.onmessage({ data: { type: "SAVE_PROGRESS", done: 0, total: 9 } });
  await p.tick(3000);
  port.onmessage({ data: { type: "SAVE_DONE", saved: 9, total: 9, failed: [] } });
  await p.tick(0);
  if (answer) { answer(); await p.tick(0); }                                      // Firefox: the visitor answered its question late
  return { asked, said: p.announced.slice() };
};
R.persist = { yes: await saveWith("en", true), no: await saveWith("es", false), none: await saveWith("en", undefined),
              late: await saveWith("en", true, true) };
// "no": what helps on this device — an iPhone's (or iPad's) installed app keeps a storage of its own
const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const IPAD = "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36";
const MAC_SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15";
const EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0";
const FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0";
const FACEBOOK = "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.0.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/480.0.0.0;]";
const lastSaid = async (lang, device) => (await saveWith(lang, false, false, device)).said[1];
R.persistNo = { iphone: await lastSaid("en", { ua: IPHONE }), iphoneEs: await lastSaid("es", { ua: IPHONE }), ipad: await lastSaid("en", { ua: IPAD }),
                android: await lastSaid("en", { ua: ANDROID }), androidEs: await lastSaid("es", { ua: ANDROID }),
                iphoneApp: await lastSaid("en", { ua: IPHONE, app: true }), androidApp: await lastSaid("es", { ua: ANDROID, app: true }),
                // a Mac's Safari ("Add to Dock": an app with its own storage too); Edge on a computer (it shares the
                // browser's); browsers that can't install one: Firefox on a computer, an app's own browser (Facebook)
                mac: await lastSaid("en", { ua: MAC_SAFARI }), edge: await lastSaid("en", { ua: EDGE }),
                firefox: await lastSaid("en", { ua: FIREFOX }), facebookEs: await lastSaid("es", { ua: FACEBOOK }) };

/* ---------------- each page tells the worker whether Data saver is on (its round over the saved pages waits for it) ---- */
const howServed = async (o) => { const p = boot(o); await p.tick(0); return p.posted.filter((x) => x.msg.type === "HOW_SERVED").map((x) => x.msg); };
R.howServed = { plain: await howServed({}), saveData: await howServed({ connection: { saveData: true } }),
                slow: await howServed({ connection: { effectiveType: "2g" } }), fast: await howServed({ connection: { effectiveType: "4g", saveData: false } }) };

/* ---------------- YouTube previews: the plain youtube-nocookie.com player on every page ---------------- */
{
  const p = boot();
  await p.tick(0);
  const preview = { needsYTApi: true };                                            // lite-youtube on a phone: true
  const inside = { closest: (s) => (s === "lite-youtube" ? preview : null), getAttribute: () => null, hasAttribute: () => false };
  for (const fn of p.docL.click || []) fn({ target: inside, preventDefault() {} });
  const keyed = { needsYTApi: true };
  const btn = { closest: (s) => (s === "lite-youtube" ? keyed : null) };
  for (const fn of p.docL.keydown || []) fn({ key: "Enter", target: btn, preventDefault() {} });
  const other = { needsYTApi: true };
  for (const fn of p.docL.keydown || []) fn({ key: "a", target: { closest: (s) => (s === "lite-youtube" ? other : null) }, preventDefault() {} });
  R.youtube = { click: preview.needsYTApi, enter: keyed.needsYTApi, otherKey: other.needsYTApi };
}
out(R);
"""

ORIGIN = "https://example.test"
B = "/aagrapevine/"


class Worker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Worker.r is None:
            Worker.r = run_js(self, WORLD_JS, needs_modules=False, env={"PATH_PREFIX": B}, timeout=120)
        self.r = Worker.r

    def test_the_build_settings(self):
        c = self.r["config"]
        self.assertEqual(c["base"], B)
        self.assertEqual(c["offline"], {"en": B + "offline/", "es": B + "es/offline/"})
        for p in ("", "meetings/", "monthly/", "monthly/{month}/", "contribute/", "shop/", "published/", "accessibility/",
                  "orientation/", "orientation/magazines/"):
            self.assertIn(p, c["save"])
        self.assertEqual(len(c["save"]), len(set(c["save"])))
        self.assertTrue(all(u.startswith(B) for u in c["required"]))
        self.assertEqual(c["booth"], {"media": "about/booth/media/", "json": "about/booth.json"})   # the booth display

    def test_install(self):
        self.assertEqual(self.r["install"], ["fulfilled"])                   # an optional font missing is fine
        for u in self.r["config"]["required"]:
            self.assertIn(ORIGIN + u, self.r["shell"])
        self.assertTrue(self.r["offlineStamped"])
        self.assertFalse(self.r["skippedOnInstall"])                         # a new version waits for the visitor
        self.assertEqual(self.r["installBad"], ["rejected"])                 # the CSS missing: try again later

    def test_install_core_is_optional(self):
        # the install notice's rules (install-core.js) are kept for offline use, but a worker installs
        # without them: pwa.js then makes every install control a plain link to the steps (/offline/#steps)
        r = self.r
        self.assertEqual(r["coreUrl"], B + "assets/js/install-core.js?v=t1")
        self.assertIn(r["coreUrl"], r["config"]["shell"])
        self.assertNotIn(r["coreUrl"], r["config"]["required"])
        self.assertIn(ORIGIN + r["coreUrl"], r["shell"])
        self.assertEqual(r["installNoCore"], ["fulfilled"])
        self.assertNotIn(ORIGIN + r["coreUrl"], r["shellNoCore"])
        for u in r["config"]["required"]:
            self.assertIn(ORIGIN + u, r["shellNoCore"])

    def test_activate_keeps_what_visitors_saved(self):
        self.assertEqual(self.r["activate"], ["fulfilled"])
        after = self.r["cachesAfter"]
        for gone in ("gvlv-shell-t0", "gvlv-static-t0"):
            self.assertNotIn(gone, after)
        for kept in ("gvlv-shell-t1", "gvlv-pages-v1", "gvlv-saved-v1", "gvlv-img-v1", "gvlv-booth-v1", "someone-else"):
            self.assertIn(kept, after)

    def test_a_first_visit_works_offline(self):
        # the page open while the worker starts is kept, and so are the scripts and styles it asked for
        # (they loaded before the worker was in charge): offline, it opens whole, with its own scripts
        r = self.r
        self.assertEqual(r["firstActivate"], ["fulfilled"])
        self.assertIn("FIRST", r["firstVisit"]["page"]["body"])
        self.assertEqual(r["firstVisit"]["js"]["body"], "/* home */")
        self.assertEqual(r["firstVisit"]["css"]["body"], "/* lyt */")

    def test_pages_online_offline_and_slow(self):
        r = self.r
        self.assertEqual((r["online"]["status"], r["online"]["saved"]), (200, None))
        self.assertIn("ONLINE", r["online"]["body"])
        self.assertIn(ORIGIN + B + "meetings/", r["kept"])
        self.assertEqual(r["keptTitle"], "Meetings & more")
        self.assertFalse(r["howServedOnline"]["copy"])
        # offline: the kept copy, and the page is told so
        self.assertIn("ONLINE", r["offlineCopy"]["body"])
        self.assertTrue(r["offlineCopy"]["saved"])
        self.assertTrue(r["howServedCopy"]["copy"])
        self.assertTrue(r["howServedCopy"]["savedAt"])
        # never seen: the offline page in the address's language
        self.assertIn("OFFLINE-ES", r["offlineEs"]["body"])
        self.assertIn("OFFLINE-EN", r["offlineEn"]["body"])
        # a server error → the copy; GitHub Pages' 404 → as it is, never kept
        self.assertIn("ONLINE", r["serverError"]["body"])
        self.assertEqual(r["notFound"]["status"], 404)
        self.assertNotIn(ORIGIN + B + "nope/", r["keptAfter404"])
        # no answer in time → the copy
        self.assertIn("ONLINE", r["slow"]["body"])

    def test_forwarding_pages_are_kept_and_marked(self):
        # an old address's forwarding page (its meta refresh sends the visitor on: /meeting/, the old install page …)
        # is kept like any page, so an old link still forwards offline; x-gvlv-moved tells the offline page not to
        # list it (pwa.js offlineList) — a page of its own has no such mark
        r = self.r
        self.assertEqual(r["moved"], {"forwarding": "1", "page": None})
        self.assertIn("MOVED", r["movedOffline"]["body"])
        self.assertTrue(r["movedOffline"]["saved"])

    def test_only_the_sites_own_get_requests(self):
        for name, res in self.r["untouched"].items():
            with self.subTest(request=name):
                self.assertIsNone(res)

    def test_files_work_offline_once_seen(self):
        r = self.r
        self.assertEqual(r["cssOffline"]["status"], 200)
        self.assertEqual(r["imgOnline"]["body"], "IMG")
        self.assertEqual(r["imgOffline"]["body"], "IMG")
        self.assertIn("error", r["imgNever"])                                 # offline and never seen: a network error
        self.assertEqual(r["jsonOnline"]["body"], '{"v":1}')
        self.assertEqual(r["jsonOffline"]["body"], '{"v":1}')                 # any ?query: the same index

    def test_save_key_pages(self):
        r = self.r
        replies = r["saveReplies"]
        self.assertEqual(replies[0]["type"], "SAVE_PROGRESS")
        done = replies[-1]
        self.assertEqual(done["type"], "SAVE_DONE")
        self.assertEqual(done["failed"], [B + "es/contribute/"])            # the page that could not be reached
        self.assertEqual(done["saved"], len(r["savePages"]) - 1)
        self.assertEqual(done["total"], len(r["savePages"]))                 # no page for this month yet: not counted
        for p in r["savePages"]:
            if p != "contribute/":
                self.assertIn(ORIGIN + B + "es/" + p, r["saved"])
        self.assertFalse(r["saveFetchedEnglish"])                            # only the visitor's language

    def test_the_stand_in_follows_the_daily_content(self):
        # The offline pages are fetched on install, and a new version installs only when the CODE changes — the daily
        # sync changes their "Join by phone" IDs and footer (config/site.yml, the synced data) without one. So pages
        # opened online bring the stand-in in their language up to date once a day, and /offline/ opened online
        # replaces it at once (its own answer: fetched once, not twice); it is never listed among the pages kept.
        s = self.r["standIn"]
        self.assertEqual(s["sameDay"], {"fetched": 1, "shown": "OFFLINE-EN"})           # fetched on install only
        self.assertEqual(s["nextDay"], {"fetchedEn": 2, "fetchedEs": 1, "en": "EN-NEW-ID", "es": "OFFLINE-ES"})
        self.assertEqual(s["spanishPage"], {"fetchedEs": 2, "es": "ES-NEW-ID"})         # a Spanish page: the Spanish one
        self.assertEqual(s["twoPagesAtOnce"], 1)                                          # pages opened in a row: one check
        self.assertEqual(s["opened"], {"fetched": 1, "shown": "EN-OPENED"})
        self.assertEqual(s["openedAgain"], "EN-OPENED-AGAIN")                            # a fresh copy too; ?query or not
        self.assertTrue(s["stamped"])
        self.assertEqual(s["inPages"], [])

    def test_an_address_without_its_last_slash(self):
        # "…/aagrapevine/es" (the Spanish Monthly poster prints it) and "…/es/meetings" typed: online GitHub Pages sends
        # them on to the address with the slash; offline they are the same page — its kept copy, or the stand-in in
        # the address's language (the Spanish one for "…/es", not the English one); nothing is kept twice
        r = self.r["noSlash"]
        self.assertEqual(r, {"es": "OFFLINE-ES", "esMeetings": "ES-MEETINGS", "meetings": "EN-MEETINGS", "esShop": "OFFLINE-ES",
                             "shop": "OFFLINE-EN", "esKept": "ES-HOME",
                             "kept": [B + "es/", B + "es/meetings/", B + "meetings/"]})


class Updates(unittest.TestCase):
    """UPDATE_JS: a new version taking over; the saved pages kept fresh."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Updates.r is None:
            Updates.r = run_js(self, UPDATE_JS, needs_modules=False, env={"PATH_PREFIX": B}, timeout=120)
        self.r = Updates.r

    def test_reload_never_waits_for_the_open_tabs(self):
        # P5-1: activation used to download every open tab (and its files) again before any page could load — a
        # "Reload" after an update hung 10 s and more on a weak signal. Now the tabs are kept afterwards.
        u = self.r["update"]
        self.assertEqual(u["activate"], ["fulfilled"])
        self.assertEqual(u["reload"], "RELOADED")
        self.assertFalse(u["keptMeanwhile"])
        self.assertTrue(u["keptAfter"])

    def test_a_tab_that_never_answers_is_given_up(self):
        self.assertEqual(self.r["hang"], {"activate": ["fulfilled"], "kept": False})

    def test_saved_pages_older_than_a_week_are_fetched_again(self):
        # F-7: a page opened online starts a round over the saved pages: those saved over a week ago are fetched
        # again, one at a time; the first that fails ends the round (the signal is weak again)
        r = self.r["refresh"]
        self.assertEqual(r["weak"]["copies"], {"home": "NEW-home", "meetings": "OLD-meetings", "monthly": "OLD-monthly",
                                               "contribute": "OLD-contribute", "shop": "OLD-shop"})
        self.assertEqual(r["weak"]["asked"], ["accessibility/", "home", "meetings/"])
        self.assertEqual(r["soon"], ["accessibility/"])                       # at most every 6 hours
        # 7 hours later: the rest that is over a week old; a page now gone (404) keeps its copy; a fresh one is left
        self.assertEqual(r["later"]["asked"], ["accessibility/", "meetings/", "monthly/", "shop/"])
        self.assertEqual(r["later"]["copies"], {"home": "NEW-home", "meetings": "NEW-meetings", "monthly": "OLD-monthly",
                                                "contribute": "OLD-contribute", "shop": "NEW-shop"})
        self.assertTrue(r["stamped"])

    def test_a_new_copy_whose_files_did_not_come_leaves_the_old_one(self):
        # the old copy opens whole offline; the new one, without its new script, would not: it waits for the next round
        r = self.r["partial"]
        self.assertEqual(r["shop"], "OLD-shop")
        self.assertEqual(r["meetings"], "NEW-meetings")
        self.assertTrue(r["later"].startswith("NEW-shop"), r["later"])
        self.assertTrue(r["script"])

    def test_no_round_with_data_saver_on(self):
        # Round-7 review: the weekly round downloaded every saved page a week old (both languages: 32) with Data saver
        # on. It now starts only once the page the site answered says Data saver is off (pwa.js HOW_SERVED); an older
        # page's script says nothing — then the browser's own word (Save-Data, 2G); no word, or a stand-in: no round
        r = self.r["saver"]
        for case in ("on", "browser", "slow", "offline", "unsaid"):
            with self.subTest(case=case):
                self.assertEqual(r[case], ["accessibility/"])
        self.assertEqual(r["off"], ["accessibility/", "home", "meetings/", "shop/"])   # the visitor's "off" (over 2G)
        self.assertEqual(r["copies"], ["NEW", "NEW", "NEW"])

    def test_a_save_stops_the_round_and_none_runs_beside_it(self):
        # Round-7 review: the round and "Save key pages" downloaded the same pages side by side. The save lets the
        # round's download go (the round ends), and a page opened while it saves starts no round
        r = self.r["lock"]
        self.assertEqual(r["fetched"], {"home": 2, "meetings": 1, "shop": 1})   # home: the round's (let go), the save's
        self.assertEqual(r["during"], ["accessibility/"])
        self.assertEqual(r["copies"], ["NEW", "NEW", "NEW"])
        self.assertEqual(r["done"], "SAVE_DONE")

    def test_a_round_stopped_by_a_save_leaves_the_pruning_to_it(self):
        # the round had refreshed a page when the save stopped it: it doesn't prune the saved pages' files then — the
        # save is keeping pages and their new files at that moment (a file kept for a page not yet put back would go);
        # the save prunes once, at its end
        r = self.r["stoppedPrune"]
        self.assertEqual(r["prunes"], 1)
        self.assertEqual(r["copies"], ["NEW", "NEW", "NEW"])
        self.assertEqual(r["done"], "SAVE_DONE")

    def test_a_page_removed_meanwhile_is_not_put_back(self):
        # Round-7 review: a page removed while the round ran (last month's, by "Save key pages") came back seconds later
        r = self.r["removed"]
        self.assertEqual(r["asked"], ["accessibility/", "home", "contribute/", "shop/"])   # meetings/: gone before its turn
        self.assertEqual(r["saved"], ["home", "contribute/"])                               # shop/: gone while it downloaded

    def test_a_kept_pages_own_stylesheet_works_offline_after_new_versions(self):
        # Round-7 review (P5-2): a page area's own stylesheet (monthly.css …) came with a page opened online into the
        # static cache, which each new version replaced — offline, the page kept from before (not saved) lost its look.
        # Its stylesheets now go on into each new version's static cache (scripts do not); main.css comes from the shell
        r = self.r["carry"]
        self.assertEqual((r["t2"], r["t3"]), (["fulfilled"], ["fulfilled"]))
        self.assertTrue(r["page"].endswith("NOV"), r["page"])                             # the copy kept from t1
        self.assertEqual((r["css"]["status"], r["css"]["body"]), (200, "/* monthly t1 */"))
        self.assertEqual(r["main"], "/* " + B + "assets/css/main.css?v=t3 */")
        self.assertEqual(r["caches"], ["gvlv-shell-t3", "gvlv-static-t3"])                 # the old versions' caches: gone
        self.assertEqual(r["static"], [B + "assets/css/monthly.css?v=t1"])


# A month page's calendar file (class MonthCalendar): its own world, same harness.
CALENDAR_JS = HARNESS_JS + r"""
const parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", year: "numeric", month: "2-digit" }).formatToParts(new Date());
const MONTH = parts.find((x) => x.type === "year").value + "-" + parts.find((x) => x.type === "month").value;
const PAGE = B + "monthly/" + MONTH + "/", ICS = PAGE + "neta65-grapevine-" + MONTH + "-en.ics";
const OLD_PAGE = B + "monthly/2020-01/", OLD_ICS = OLD_PAGE + "neta65-grapevine-2020-01-en.ics";
const FEED = B + "events.ics", ELSEWHERE = B + "monthly/2020-02/neta65-grapevine-2020-02-en.ics";
const cal = (v) => ({ body: "BEGIN:VCALENDAR\r\nX-V:" + v + "\r\nEND:VCALENDAR\r\n", ct: "text/calendar; charset=utf-8" });
const w = world();
shellOnline(w);
await w.lifecycle("install");
for (const p of w.CONFIG.save.filter((p) => !p.includes("{month}"))) w.page(B + p, { body: html(p || "home") });
w.page(PAGE, { body: html("Month", `<a class="link" href="${ICS}" type="text/calendar">Add this month's dates</a> ` +
                                    `<a href="${FEED}">every event</a> <a href="${ELSEWHERE}">another month</a> MONTH`) });
w.page(ICS, cal(1));
w.page(FEED, cal("FEED"));
// last month's page, saved last month, with its calendar file: both go with this save (dropOldMonths, the prune)
await (await w.cache("gvlv-saved-v1")).put(ORIGIN + OLD_PAGE, new Response(html("Old", `<a href="${OLD_ICS}">Add</a>`), { headers: { "content-type": "text/html" } }));
await (await w.cache("gvlv-saved-assets-v1")).put(ORIGIN + OLD_ICS, new Response("OLD"));
R.reply = (await w.message({ type: "SAVE", lang: "en" })).at(-1);
R.assets = ((await w.keys("gvlv-saved-assets-v1")) || []).filter((u) => u.endsWith(".ics")).map((u) => u.slice(ORIGIN.length));
const asked = (u) => w.fetched.filter((x) => x === ORIGIN + u).length;
R.feedAsked = asked(FEED);
// online: the site's answer, which becomes the copy
w.page(ICS, cal(2));
R.online = (await w.request(ICS)).body;
// a tap on the page's link is a NAVIGATION to the file: the same route (never the page handler)
R.onlineTap = (await w.request(ICS, { navigate: true })).body;
// offline: the copy; the feed and a month not saved are not answered by the worker (straight to the network)
for (const u of [ICS, FEED, ELSEWHERE]) w.net.delete(ORIGIN + u);
R.offline = await w.request(ICS);
R.offlineTap = await w.request(ICS, { navigate: true });
// a month not saved, its link tapped offline: the offline page, as for any page not saved
R.elsewhereTap = await w.request(ELSEWHERE, { navigate: true });
R.feed = await w.request(FEED);
w.page(ELSEWHERE, cal("ELSEWHERE"));
R.elsewhere = (await w.request(ELSEWHERE)).body;
R.assetsAfter = ((await w.keys("gvlv-saved-assets-v1")) || []).filter((u) => u.endsWith(".ics")).map((u) => u.slice(ORIGIN.length));
// the month page opened online again: its calendar file is fetched again with it (a saved page stays fresh)
w.page(PAGE, { body: html("Month", `<a href="${ICS}">Add</a> MONTH-2`) });
w.page(ICS, cal(3));
await w.request(PAGE, { navigate: true });
w.net.delete(ORIGIN + ICS);
R.refreshed = (await w.request(ICS)).body;
R.month = MONTH;

/* ---------------- the site's zone (config/site.yml site.timezone): "this month" is the month there ---------------- */
R.zones = {};
for (const tz of [null, "America/Chicago", "Pacific/Kiritimati", "Pacific/Pago_Pago"]) {
  const code = SW.render({ build: { version: "t1" }, collections: { all: [] }, site: tz ? { timezone: tz } : {} });
  const ctx = vm.createContext({ self: { addEventListener() {}, location: { origin: ORIGIN } }, console, URL, Request, Response, Headers });
  vm.runInContext(code, ctx);
  // 2026-10-31 12:00 UTC: still October in Central time and in Samoa, already November on Kiritimati (UTC+14)
  vm.runInContext("{ const D = Date; Date = class extends D { constructor(...a) { if (a.length) super(...a); else super(D.UTC(2026, 9, 31, 12)); } }; }", ctx);
  R.zones[tz || "none"] = [vm.runInContext("CONFIG.tz", ctx), vm.runInContext("chicagoMonth()", ctx)];
}
out(R);
"""


class MonthCalendar(unittest.TestCase):
    """A month page saved for offline use opens its own calendar file ("Add October's dates to my calendar") offline
    too: the file is kept with the page (in gvlv-saved-assets-v1, pruned with it); the big /events.ics feeds and a
    month not saved are never kept nor answered by the worker. And "this month" is the month in the site's zone."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if MonthCalendar.r is None:
            MonthCalendar.r = run_js(self, CALENDAR_JS, needs_modules=False, env={"PATH_PREFIX": B}, timeout=120)
        self.r = MonthCalendar.r

    def test_the_month_file_is_saved_with_its_page(self):
        r, m = self.r, self.r["month"]
        self.assertEqual(r["reply"]["type"], "SAVE_DONE")
        self.assertEqual(r["assets"], [f"{B}monthly/{m}/neta65-grapevine-{m}-en.ics"], "last month's went with its page")
        self.assertEqual(r["feedAsked"], 0, "the feed a saved page links is never fetched for it")

    def test_online_the_site_offline_the_copy(self):
        r = self.r
        self.assertIn("X-V:2", r["online"])
        self.assertEqual(r["offline"]["status"], 200)
        self.assertIn("X-V:2", r["offline"]["body"], "the copy the last online answer left")
        # the link tapped (a navigation): the file too — online the site's, offline the copy, never the offline page
        self.assertIn("X-V:2", r["onlineTap"])
        self.assertEqual(r["offlineTap"]["status"], 200)
        self.assertIn("X-V:2", r["offlineTap"]["body"])
        self.assertNotIn("OFFLINE-EN", r["offlineTap"]["body"])
        self.assertIn("X-V:3", r["refreshed"], "the page opened online again brings its file up to date")

    def test_feeds_and_months_not_saved_are_left_alone(self):
        r, m = self.r, self.r["month"]
        self.assertIsNone(r["feed"], "/events.ics: not answered by the worker")
        self.assertIn("X-V:ELSEWHERE", r["elsewhere"], "a month not saved: the network")
        self.assertIn("OFFLINE-EN", r["elsewhereTap"]["body"], "its link tapped offline: the offline page")
        self.assertEqual(r["assetsAfter"], [f"{B}monthly/{m}/neta65-grapevine-{m}-en.ics"], "and never kept")

    def test_this_month_is_the_month_in_the_sites_zone(self):
        self.assertEqual(self.r["zones"], {"none": ["America/Chicago", "2026-10"], "America/Chicago": ["America/Chicago", "2026-10"],
                                           "Pacific/Kiritimati": ["Pacific/Kiritimati", "2026-11"],
                                           "Pacific/Pago_Pago": ["Pacific/Pago_Pago", "2026-10"]})


MEDIA = B + "about/booth/media/"
SHOW = B + "about/booth.json"
VIDEO = "0123456789" * 100                                   # the saved video in BOOTH_JS: byte i is the digit i % 10


def done(n_saved: int, total: int, failed: list[str], size: int, **why: bool) -> dict:
    return {"type": "BOOTH_DONE", "saved": n_saved, "total": total, "failed": failed, "bytes": size, **why}


class Booth(unittest.TestCase):
    """The booth display's offline copy (BOOTH_JS): gvlv-booth-v1, the messages BOOTH_SAVE / BOOTH_STATUS / BOOTH_CLEAR,
    the photos and videos answered from the copy (byte ranges too), the show (/about/booth.json) network first."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Booth.r is None:
            Booth.r = run_js(self, BOOTH_JS, needs_modules=False, env={"PATH_PREFIX": B}, timeout=120)
        self.r = Booth.r
        self.b = self.r["booth"]

    def test_save_reports_progress_after_each_page_and_file(self):
        # 2 pages + 5 files of ours (other sites, another Pages project, a file listed twice — once by its address from
        # the base — are left out: never fetched, never counted); BOOTH_PROGRESS at once and after each; bytes = the
        # files kept so far (16 + 1000 + 300 + 50); the file the site doesn't have is the one failed
        self.assertEqual(self.b["save"], [[0, 7, 0], [1, 7, 0], [2, 7, 0], [3, 7, 16], [4, 7, 1016], [5, 7, 1316], [6, 7, 1366], [7, 7, 1366],
                                          done(6, 7, [ORIGIN + MEDIA + "a0a0a0-lost.mp4"], 1366)])
        self.assertEqual([u for u in self.b["asked"] if "/assets/js/" not in u],
                         [B + "about/", B + "es/about/", SHOW, MEDIA + "a1b2c3-welcome.mp4", MEDIA + "d4e5f6-table.jpg",
                          B + "assets/cache/pod/ep1.webp", MEDIA + "a0a0a0-lost.mp4"])
        self.assertEqual(self.b["kept"], sorted([SHOW, MEDIA + "a1b2c3-welcome.mp4", MEDIA + "d4e5f6-table.jpg", B + "assets/cache/pod/ep1.webp"]))

    def test_the_about_page_is_saved_like_a_key_page(self):
        # saved the way "Save key pages" saves one: in gvlv-saved-v1, its styles and scripts in gvlv-saved-assets-v1 —
        # so it opens offline, in both languages and at the kiosk address (?booth=start), with its own script
        b = self.b
        self.assertEqual(b["saved"], [B + "about/", B + "es/about/"])
        for a in ("assets/css/main.css?v=t1", "assets/js/app.js?v=t1", "assets/js/booth.js?v=t1"):
            self.assertIn(B + a, b["assets"])
        self.assertEqual(b["offline"]["about"], ["ABOUT-EN", True])            # the saved copy (stamped: pwa.js is told)
        self.assertEqual(b["offline"]["aboutEs"], "ABOUT-ES")
        self.assertEqual(b["offline"]["script"], "/* booth */")
        self.assertEqual(b["offline"]["show"], '{"version":"v1"}')            # any ?query: the one copy
        self.assertEqual(b["offline"]["thumb"], "t" * 50)
        self.assertEqual(b["offline"]["pic"], 300)

    def test_media_come_from_the_copy_in_the_parts_asked_for(self):
        rg = self.b["ranges"]
        self.assertEqual(self.b["rangesAskedSite"], 0)                         # cache first: the site is never asked
        self.assertEqual((rg["whole"]["status"], rg["whole"]["body"], rg["whole"]["type"]), (200, VIDEO, "video/mp4"))
        parts = {   # name: (body, Content-Range)
            "first100": (VIDEO[:100], "bytes 0-99/1000"), "tail": (VIDEO[990:], "bytes 990-999/1000"),
            "last10": (VIDEO[990:], "bytes 990-999/1000"), "clamped": (VIDEO[900:], "bytes 900-999/1000"),
            "bigSuffix": (VIDEO, "bytes 0-999/1000"), "spaced": (VIDEO[10:20], "bytes 10-19/1000"),
        }
        for name, (body, content_range) in parts.items():
            with self.subTest(range=name):
                self.assertEqual(rg[name], {"status": 206, "body": body, "range": content_range, "length": str(len(body)),
                                            "accept": "bytes", "type": "video/mp4"})
        for name in ("pastEnd", "farPast", "lastZero"):                        # not one byte of the file: 416
            with self.subTest(range=name):
                self.assertEqual((rg[name]["status"], rg[name]["body"], rg[name]["range"]), (416, "", "bytes */1000"))
        for name in ("backwards", "several", "otherUnit"):                     # not a range we read: the whole file
            with self.subTest(range=name):
                self.assertEqual((rg[name]["status"], rg[name]["body"]), (200, VIDEO))

    def test_a_file_not_saved_goes_to_the_network_and_is_not_kept(self):
        n = self.b["notSaved"]
        self.assertEqual(n["answer"], [206, "NEW-", "bytes 0-3/15"])           # the site's own part …
        self.assertEqual(n["asked"], [[MEDIA + "b7b7b7-new.mp4", "bytes=0-3"]])  # … the Range header passed on
        self.assertEqual(n["keptIn"], [])
        self.assertIn("error", self.b["notSavedOffline"])

    def test_saved_again_the_show_first_and_kept_media_not_fetched(self):
        a = self.b["again"]
        self.assertEqual(a["done"], done(6, 6, [], 1000 + 300 + 60 + 16))      # kept media count, with their size
        self.assertEqual(a["asked"], [[B + "about/", "no-cache"], [B + "es/about/", "no-cache"], [SHOW, "no-cache"],
                                      [B + "assets/cache/pod/ep1.webp", "no-cache"]])
        self.assertEqual(a["show"], '{"version":"v2"}')
        self.assertTrue(a["video"])
        self.assertEqual(a["thumb"], "T" * 60)
        self.assertIn("ABOUT-EN-2", a["about"])

    def test_prune(self):
        b = self.b
        # the files the list no longer names go — once the new show is saved, before the new file downloads
        self.assertEqual(b["prune"]["done"], done(3, 3, [], 16 + 1000 + 40))
        self.assertEqual(b["prune"]["kept"], sorted([SHOW, MEDIA + "a1b2c3-welcome.mp4", MEDIA + "c8c8c8-new.jpg"]))
        self.assertEqual(b["prune"]["whenAdded"], sorted([SHOW, MEDIA + "a1b2c3-welcome.mp4"]))
        # the show can't be fetched: nothing pruned (the copy keeps what its show still names), the old show kept
        self.assertEqual(b["noPrune"]["done"], done(1, 2, [ORIGIN + SHOW], 1000))
        self.assertEqual(b["noPrune"]["kept"], b["prune"]["kept"])
        self.assertEqual(b["noPrune"]["show"], '{"version":"v3"}')
        # a list without files prunes nothing (BOOTH_CLEAR removes the copy)
        self.assertEqual(b["emptyList"]["done"], done(1, 1, [], 0))
        self.assertEqual(b["emptyList"]["kept"], b["prune"]["kept"])

    def test_status(self):
        self.assertEqual(self.b["status"], {"type": "BOOTH_STATUS", "have": 3, "total": 28, "bytes": 16 + 1000 + 40,
                                            "missing": self.b["absent"][:20]})

    def test_failed_lists_at_most_20(self):
        c = self.b["capped"]
        self.assertEqual(c["done"], done(1, 31, self.b["broken"][:20], 16))
        self.assertEqual(c["progress"], 32)                                    # at once + after each of the 31

    def test_clear(self):
        b = self.b
        self.assertEqual(b["clear"], [{"type": "BOOTH_CLEARED"}])
        self.assertEqual(b["afterClear"]["status"], {"type": "BOOTH_STATUS", "have": 0, "total": 1, "bytes": 0, "missing": [ORIGIN + SHOW]})
        self.assertFalse(b["afterClear"]["cache"])                             # gone (a status doesn't make an empty one)
        self.assertEqual(b["afterClear"]["saved"], [B + "about/", B + "es/about/"])   # the saved pages stay
        self.assertIn("error", b["afterClear"]["video"])

    def test_the_show_is_network_first_with_the_booth_copy_then_the_data_copy(self):
        s = self.r["boothShow"]
        self.assertEqual(s["none"], "ERROR")                                   # offline, never seen
        self.assertEqual(s["online"], '{"version":"n1"}')
        self.assertEqual(s["dataKeys"], [SHOW])                                # kept like the JSON indexes, without ?t=1
        self.assertFalse(s["boothCache"])                                      # the booth saved nothing: no copy made
        self.assertEqual(s["offlineData"], '{"version":"n1"}')
        self.assertEqual(s["online2"], '{"version":"v2"}')
        self.assertEqual(s["copies"], {"booth": '{"version":"v2"}', "data": '{"version":"v2"}'})   # the booth's copy follows
        for when in ("offline", "slow", "serverError"):                        # the booth's copy before the data cache's
            with self.subTest(when=when):
                self.assertEqual(s[when], '{"version":"v2"}')
        self.assertEqual(s["afterClear"], "DATA-COPY")                         # no booth copy: the data cache's
        self.assertEqual(s["onlineAfterClear"], '{"version":"v3"}')
        self.assertFalse(s["boothAfterClear"])                                 # a removed copy isn't brought back
        self.assertEqual(s["dataAfterClear"], '{"version":"v3"}')

    def test_a_big_file_gives_news_while_it_downloads(self):
        L = self.r["boothLong"]
        news = L["news"]
        self.assertEqual(news[:2], [["BOOTH_PROGRESS", 0, 0], ["BOOTH_PROGRESS", 1, 16]])
        self.assertEqual(news[-2:], [["BOOTH_PROGRESS", 2, 416], ["BOOTH_DONE", None, 416]])
        during = news[2:-2]
        self.assertGreaterEqual(len(during), 2)                                # every 2 s of its download
        self.assertTrue(all(m[0] == "BOOTH_PROGRESS" and m[1] == 1 and 16 < m[2] < 416 for m in during), during)
        self.assertEqual([m[2] for m in during], sorted({m[2] for m in during}))   # growing
        self.assertEqual(L["big"], 400)                                        # kept whole

    def test_a_long_save_stops_in_time_and_goes_on_when_asked_again(self):
        m = self.r["boothLong"]["more"]
        rest = self.r["boothLong"]["list"][2:]
        self.assertEqual(m["first"], done(2, 4, rest, 26, more=True))          # 4 minutes passed: no new file started
        self.assertEqual(m["next"], done(4, 4, [], 46))
        self.assertEqual(m["nextAsked"], [SHOW, MEDIA + "e2.jpg", MEDIA + "e3.jpg"])   # the kept one not fetched again

    def test_a_full_device_stops_the_save(self):
        f = self.r["boothLong"]["full"]
        self.assertEqual(f["done"], done(2, 4, self.r["boothLong"]["list"][2:], 26, full=True))
        self.assertEqual(f["asked"], [SHOW, MEDIA + "e1.jpg", MEDIA + "e2.jpg"])   # not tried again, nothing more downloaded

    def test_a_broken_download_is_tried_once_more(self):
        f = self.r["boothLong"]["flaky"]
        self.assertEqual(f["done"], done(1, 1, [], 500))
        self.assertEqual(f["asked"], 2)
        self.assertEqual(f["kept"], "F" * 500)                                  # whole, not the 100 bytes of the first try

    def test_a_removal_stops_the_saves_asked_before_it(self):
        c = self.r["boothLong"]["clear"]
        e2 = ORIGIN + MEDIA + "e2.jpg"
        self.assertEqual(c["running"], done(1, 3, [c["slow"], e2], 16, stopped=True))   # its download let go
        self.assertEqual(c["waiting"], done(0, 2, [ORIGIN + SHOW, e2], 0, stopped=True))
        self.assertEqual(c["cleared"], [{"type": "BOOTH_CLEARED"}])
        self.assertEqual(c["after"], done(2, 2, [], 26))                      # a save asked after it runs
        self.assertEqual(c["order"], ["running:BOOTH_DONE", "waiting:BOOTH_DONE", "clear:BOOTH_CLEARED", "after:BOOTH_DONE"])
        self.assertEqual(c["m2Asked"], 1)
        self.assertEqual(c["kept"], sorted([SHOW, MEDIA + "e2.jpg"]))

    def test_one_save_at_a_time(self):
        t = self.r["boothLong"]["twice"]
        self.assertEqual(t["first"], [{"type": "BOOTH_PROGRESS", "done": 0, "total": 2, "bytes": 0}] * 2)   # both answered at once
        self.assertEqual(t["order"], ["one:BOOTH_PROGRESS", "two:BOOTH_PROGRESS", "one:BOOTH_PROGRESS", "one:BOOTH_PROGRESS", "one:BOOTH_DONE",
                                      "two:BOOTH_PROGRESS", "two:BOOTH_PROGRESS", "two:BOOTH_DONE"])
        self.assertEqual(t["m1Asked"], 1)                                      # the second found it kept
        self.assertEqual(t["done"], [done(2, 2, [], 26)] * 2)

    def test_a_waiting_save_keeps_giving_news(self):
        # a page that hears nothing for a while gives up (pwa.js: 45 s) — a save waiting behind another one says
        # "still here" every 10 s, and its timer is gone once its turn comes
        w = self.r["boothLong"]["waiting"]
        self.assertEqual(w["every"], [10000])
        self.assertEqual(w["meanwhile"], [["BOOTH_PROGRESS", 0]] * 3)          # at once, then each 10 s
        self.assertEqual(w["after"], [["BOOTH_PROGRESS", 0]] * 3 + [["BOOTH_PROGRESS", 1], ["BOOTH_DONE", None]])
        self.assertEqual(w["timersLeft"], 0)

    def test_answers_without_a_port_go_to_the_page(self):
        self.assertEqual(self.r["boothLong"]["noPort"], [{"type": "BOOTH_STATUS", "have": 1, "total": 1, "bytes": 16, "missing": []}])


class ThePage(unittest.TestCase):
    """pwa.js's side of the conversation with the worker (PAGE_JS)."""
    SAVING = "Guardando páginas para usar sin conexión…"
    FAILED = "No se pudieron guardar las páginas. Intenta de nuevo con mejor señal."

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if ThePage.r is None:
            ThePage.r = run_js(self, PAGE_JS, needs_modules=False, timeout=120)
        self.r = ThePage.r

    def test_a_slow_save_is_not_a_failed_one(self):
        # 15 pages on a 2G-class signal take 90 s: the worker's news keeps the save going — never "couldn't save"
        # half-way through (it used to give up 60 s after the tap while the worker went on saving)
        r = self.r["slow"]
        self.assertEqual(r, {"saves": 1, "said": [self.SAVING, "Se guardaron 15 páginas. Se abren sin conexión."]})

    def test_a_save_without_news_is_given_up_and_can_start_again(self):
        # 45 s without a word from the worker: "couldn't save"; what that save says afterwards changes nothing, and
        # the button starts a new save (it was silently ignored, or its answer taken for the new one's)
        r = self.r["stalled"]
        self.assertEqual(r["quiet"], [])
        self.assertEqual(r["gaveUp"], [self.FAILED])
        self.assertEqual(r["saves"], 2)
        self.assertEqual(r["said"], [self.SAVING, self.FAILED, self.SAVING, "Se guardaron 14 de 15 páginas."])

    def test_a_worker_ready_too_late_starts_no_save(self):
        # a first visit on a weak signal: the worker is still installing 45 s after the tap, so the page has said
        # "couldn't save" — once it is in charge it gets no SAVE the page no longer follows (a new tap starts one)
        self.assertEqual(self.r["late"], {"gaveUp": [self.FAILED], "behindTheBack": 0, "saves": 1})

    def test_reload_applies_the_new_version(self):
        r = self.r["update"]
        self.assertIn("A new version of the site is ready. Reload to use it.", r["offered"])
        self.assertEqual(r["pressed"], {"reloads": 0, "sent": ["SKIP_WAITING"], "disabled": True})   # it takes over …
        self.assertEqual(r["reloads"], 1)                                                             # … then the page reloads

    def test_reload_in_a_second_tab_after_the_first(self):
        # two tabs (or the app and a tab) both show "Updated — Reload"; one applies it — the other's Reload reloads
        # (it used to ask the worker already in charge to take over, and nothing happened)
        r = self.r["secondTab"]
        self.assertEqual(r["before"], 0)                                                              # not on its own
        self.assertEqual(r["pressed"], {"reloads": 1, "sent": [], "disabled": True})

    def test_save_asks_the_browser_to_keep_the_pages(self):
        # F-7: a phone short of space may delete saved pages — the tap also asks the browser to keep them
        # (navigator.storage.persist) and the result line says what it answered, in the page's language
        p = self.r["persist"]
        self.assertEqual(p["yes"], {"asked": 1, "said": ["Saving pages for offline use…",
                                                         "Saved 9 pages. They open without a connection. This browser will keep them until you remove them."]})
        self.assertEqual(p["no"]["asked"], 1)
        self.assertEqual(p["no"]["said"][1], "Se guardaron 9 páginas. Se abren sin conexión. Este navegador aún puede borrarlas si al "
                                             "dispositivo le falta espacio. Instalar el sitio como app y volver a guardarlas desde la "
                                             "app ayuda a conservarlas.")
        self.assertEqual(p["none"], {"asked": 0, "said": ["Saving pages for offline use…", "Saved 9 pages. They open without a connection."]})
        # an answer that comes after the save is done (Firefox asks the visitor): said on its own, then
        self.assertEqual(p["late"]["said"], ["Saving pages for offline use…", "Saved 9 pages. They open without a connection.",
                                             "This browser will keep them until you remove them."])

    def test_what_helps_keep_them_on_this_device(self):
        # Round-7 review: "Installing the site as an app helps keep them" was wrong on iPhone and iPad — the app installed
        # from the Home Screen keeps a storage of its own (the pages saved in Safari are not in it): there they are saved
        # again from the app; on Android and computers the app asks again when they are saved from it; inside the app
        # itself, nothing to install
        may_en = "Saved 9 pages. They open without a connection. This browser may still remove them when the device is short of space."
        may_es = "Se guardaron 9 páginas. Se abren sin conexión. Este navegador aún puede borrarlas si al dispositivo le falta espacio."
        own_en = (" On this device an installed app keeps its own copy: install the site as an app, then open it and save the pages "
                  "there to keep them.")
        r = self.r["persistNo"]
        self.assertEqual(r["iphone"], may_en + own_en)
        self.assertEqual(r["ipad"], may_en + own_en)
        self.assertEqual(r["iphoneEs"], may_es + " En este dispositivo, una app instalada guarda su propia copia: instala el sitio como "
                                                 "app, ábrela y guarda las páginas allí para conservarlas.")
        self.assertEqual(r["android"], may_en + " Installing the site as an app and saving them again from the app helps keep them.")
        self.assertEqual(r["androidEs"], may_es + " Instalar el sitio como app y volver a guardarlas desde la app ayuda a conservarlas.")
        self.assertEqual(r["iphoneApp"], may_en)
        self.assertEqual(r["androidApp"], may_es)
        self.assertEqual(r["mac"], may_en + own_en)
        self.assertEqual(r["edge"], may_en + " Installing the site as an app and saving them again from the app helps keep them.")
        # a browser that can't install the site (install-core.js canInstall): no word about an app
        self.assertEqual(r["firefox"], may_en)
        self.assertEqual(r["facebookEs"], may_es)

    def test_each_page_tells_the_worker_whether_data_saver_is_on(self):
        # the worker's weekly round over the saved pages waits for this word (sw-core.js refreshSaved): with Data saver
        # on — the visitor's choice, else the browser's own data saver or a 2G connection — nothing is fetched ahead
        r = self.r["howServed"]
        for name, saver in (("plain", False), ("saveData", True), ("slow", True), ("fast", False)):
            with self.subTest(connection=name):
                self.assertEqual(r[name], [{"type": "HOW_SERVED", "saver": saver}])

    def test_youtube_previews_keep_privacy_mode(self):
        # P5-6: lite-youtube switches to YouTube's full player (youtube.com) on phones and in Safari; pwa.js (on every
        # page: Home and About too) tells it not to just before it starts — a click, or Enter / Space on its button
        self.assertEqual(self.r["youtube"], {"click": False, "enter": False, "otherKey": True})


if __name__ == "__main__":
    unittest.main()
