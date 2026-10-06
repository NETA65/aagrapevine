/* NETA 65 Grapevine / La Viña — service worker (offline use, installable app).
   Published as <site>/sw.js by src/pages/sw.11ty.js, which puts `const CONFIG = {…}` (this build's
   version, the site's base path, the app shell, the offline pages, the pages to save, the booth
   display's addresses) above this file.
   Scope: the site's base path (/aagrapevine/ on GitHub Pages). README → "Install the app, offline use".

   What it does with each request — only GET requests to OUR site; anything else is not touched:
   * never: other sites (YouTube, podcast audio, aagrapevine.org, aalavina.org, Drive…), POST, audio
     or video byte ranges (except the booth display's own files, below), feeds and calendar files
     (.xml, .ics — the big /events.ics feeds are never kept), the worker, the manifest and the build note
     (/build.json: the booth display asks it "are we online?" — a kept copy would always say yes).
   * a month page's own calendar file (/monthly/YYYY-MM/<name>.ics, the "Add October's dates to my calendar"
     link beside the page): kept with the page when the page is saved for offline use (keepCalendars), then
     NETWORK FIRST with that copy offline (calendarFile); a month not saved goes to the network, never kept.
   * pages (navigations): NETWORK FIRST, revalidated with the site (cache: "no-cache": not even the
     browser's HTTP cache can hand back an old page). Online, you always get the page from the site;
     the copy is kept (the last 80 pages, plus the ones saved with "Save key pages for offline" — a saved
     page not opened for a week is fetched again in the background once there is a signal: refreshSaved).
     The saved copy is used only when the network fails, answers with a server error, or takes more than 4 s —
     then the page is told (pwa.js shows "Slow connection — this is a saved copy"). A page that is not
     saved → the offline page, in the language of the address. An address without its last slash
     ("…/es", "…/es/meetings": typed, or printed on a poster) is the same page as with it. GitHub
     Pages' "page not found" (404) is passed through and never kept.
     The offline pages (in the app shell, the stand-in above) carry the daily content — the "Join by
     phone" IDs, the footer — which doesn't change the version: opened online, their copy is replaced
     by the answer; otherwise the one in the address's language is fetched again at most once a day.
   * CSS / JS / fonts / images of the site: STALE-WHILE-REVALIDATE from versioned caches (answer from
     the cache, refresh it in the background at most every 6 hours). Files with ?v=<version> (the
     CSS and JS links of base.njk) and fonts never change under the same address: cache first.
     Capped: 120 static files, 200 images (the oldest go first).
   * JSON indexes (search, media, library, the Texas writers archive) and the workshop presentations
     (/orientation/presentations/<id>.json): NETWORK FIRST, the saved copy when offline or after 6 s. "Save
     key pages for offline" also fetches CONFIG.files (the presentations, the archive's rest of Texas) into
     that copy, so they open offline before ever being opened online (saveFiles).
   * the booth display (the About page's #booth, src/assets/js/booth.js — it plays unattended for hours
     at the committee's table, and keeps playing offline once opened online; CONFIG.booth):
     its photos, videos and sounds (/about/booth/media/<file>, names that never change): CACHE FIRST
     from the booth's copy, byte ranges too — a video asks for a part of the file ("Range: bytes=…")
     and gets exactly that part of the saved copy (206), so it plays and seeks offline; a file not
     saved goes to the network as it is (its range passed on) and is never kept here: the booth's copy
     is made only when the booth asks for it (BOOTH_SAVE). The show (/about/booth.json): NETWORK
     FIRST, kept like the JSON indexes, and the booth's copy replaced too when there is one; offline,
     on a server error or after 6 s, the booth's copy (else the data cache's).
   Caches: gvlv-shell-<version> (app shell) and gvlv-static-<version> are replaced by each new
   version; gvlv-pages-v1, gvlv-saved-v1, gvlv-saved-assets-v1, gvlv-img-v1 and gvlv-data-v1 are kept
   across versions, so a site update never deletes what a visitor saved — including the styles and
   scripts a saved page asks for (its old ?v= address): gvlv-saved-assets-v1 holds exactly the files
   the saved pages use (pruneSavedAssets). gvlv-booth-v1 (the booth display's offline copy: its show,
   photos, videos, posters) is kept across versions too and never trimmed — the booth's own list says
   what goes (BOOTH_SAVE prune, BOOTH_CLEAR). activate deletes every other gvlv-* cache.
   Only addresses inside the scope (the base path) are ever stored: other sites on the same origin
   (GitHub Pages projects) are never kept or listed.
   Messages: from pwa.js — SAVE ("Save key pages for offline"), HOW_SERVED, VERSION, SKIP_WAITING; from
   booth.js — BOOTH_SAVE (save the About page and the booth's files for offline, with progress),
   BOOTH_STATUS (how much of a list is saved), BOOTH_CLEAR (remove the booth's copy), and SKIP_WAITING
   before its own save or removal while this version's worker still waits. Answers go back through the
   MessageChannel port sent with the message, else to the page that sent it.
   Updates: a new version installs in the background and WAITS; pwa.js shows "Updated — reload" and
   sends SKIP_WAITING when the visitor chooses it (otherwise it takes over once every tab is closed). Its
   activation only clears the old caches: the open tabs are kept afterwards, in the background, each download
   with a time limit (keepOpenTabs), so the reloaded page never waits for them. */
"use strict";

const V = CONFIG.version;
const BASE = CONFIG.base;
const PREFIX = "gvlv-";
const CACHE = {
  shell: PREFIX + "shell-" + V,
  static: PREFIX + "static-" + V,
  pages: PREFIX + "pages-v1",
  saved: PREFIX + "saved-v1",
  savedAssets: PREFIX + "saved-assets-v1",
  img: PREFIX + "img-v1",
  data: PREFIX + "data-v1",
  booth: PREFIX + "booth-v1", // the booth display's offline copy: no LIMIT (never trimmed)
};
const LIMIT = { static: 120, pages: 80, img: 200, data: 24 };
const NAV_TIMEOUT = 4000;
const DATA_TIMEOUT = 6000;
const REVALIDATE_AFTER = 6 * 3600e3;
const BOOTH = CONFIG.booth; // { media: "about/booth/media/", json: "about/booth.json" } (from the base)

/* ------------------------------------------------------------------ install / activate */
self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE.shell);
    await Promise.all(CONFIG.shell.map(async (u) => {
      const required = CONFIG.required.includes(u);
      try {
        // Versioned files (?v=) and fonts are the same bytes the page just loaded: the browser's HTTP
        // cache may answer (no second download on a first visit). Everything else is checked with the
        // site ("no-cache": a tiny "not modified" when unchanged), so the shell is this deploy's.
        const same = /[?&]v=|\/assets\/fonts\//.test(u);
        const res = await fetch(new Request(u, { cache: same ? "default" : "no-cache", credentials: "same-origin" }));
        if (res.ok) await cache.put(u, CONFIG.offline.en === u || CONFIG.offline.es === u ? await stamp(res) : res);
        else if (required) throw new Error(u + " → HTTP " + res.status);
      } catch (e) {
        if (required) throw e; // the install fails and the browser tries again on the next visit
      }
    }));
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keep = new Set(Object.values(CACHE));
    for (const name of await caches.keys()) if (name.startsWith(PREFIX) && !keep.has(name)) await caches.delete(name);
    // No navigation preload: its request would use the browser's HTTP cache (up to 10 minutes old on
    // GitHub Pages); page() asks the site itself instead.
    if (self.registration.navigationPreload) { try { await self.registration.navigationPreload.disable(); } catch (e) { /* not supported */ } }
    await self.clients.claim(); // the first visit is looked after at once (offline works after one visit)
    // The open tabs are kept AFTER activation, in the background: while activate runs, no page of the site
    // loads — "Reload" after an update would wait for every open tab and its files to download again (10 s
    // and more on a weak signal).
    settling = keepOpenTabs().catch(() => {}).finally(() => { settling = null; });
  })());
});

/* The page(s) open while the worker takes over (a first visit) are kept too, with the styles and scripts they
   asked for — usually straight from the browser's HTTP cache, so this costs no extra data. (Those files loaded
   before the worker was in charge: without them the page would open offline with none of its own scripts —
   Home's countdown and player, for one.) Each download gets SETTLE_TIMEOUT: a weak signal gives up on it,
   never holds anything up. Until it is done, the requests that come meanwhile keep the worker running for it
   (settling: their waitUntil). (matchAll returns every tab of the ORIGIN — on GitHub Pages other projects
   share it: only ours.) */
const SETTLE_TIMEOUT = 8000;
let settling = null;
async function keepOpenTabs() {
  const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  await Promise.all(wins.map(async (c) => {
    if (!inScope(c.url)) return;
    const key = pageKey(c.url);
    try {
      const got = await within(SETTLE_TIMEOUT, async (signal) => {
        const res = await fetch(c.url, { credentials: "same-origin", signal });
        return keepable(res, key) ? { res, html: await res.clone().text() } : null;
      });
      if (!got) return;
      await keepPage(key, got.res);
      await keepFiles(got.html, c.url);
    } catch (e) { /* offline, or too slow */ }
  }));
}

/* work(signal) with a time limit: past `ms` its downloads are let go (AbortController, where there is one) and
   the promise fails — the work behind it is not waited for. */
function within(ms, work) {
  const abort = typeof AbortController === "function" ? new AbortController() : null;
  let timer = 0;
  const job = Promise.resolve().then(() => work(abort ? abort.signal : undefined));
  job.catch(() => {});
  const late = new Promise((resolve, reject) => {
    timer = setTimeout(() => { if (abort) abort.abort(); reject(new Error("timeout")); }, ms);
  });
  return Promise.race([job, late]).finally(() => clearTimeout(timer));
}

/* ------------------------------------------------------------------ routing */
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return; // never other sites
  if (settling) event.waitUntil(settling); // (the open tabs still being kept after activation: keepOpenTabs)
  // the booth display's photos and videos: its saved copy first — byte ranges too (a video plays offline)
  if (url.pathname.startsWith(BASE + BOOTH.media)) { event.respondWith(boothMedia(event, url)); return; }
  if (req.headers.has("range")) return;
  const p = url.pathname;
  // (before the pages: the month page's link to it is followed as a navigation — a tap on it is one)
  if (MONTH_ICS.test(p)) { event.respondWith(calendarFile(event, url)); return; }
  if (req.mode === "navigate") { event.respondWith(page(event, url)); return; }
  if (/\/sw\.js$|\/build\.json$|\.(webmanifest|xml|ics|txt)$/.test(p)) return;
  if (p === BASE + BOOTH.json) { event.respondWith(boothJson(event, url)); return; }
  if (/\.json$/.test(p)) { event.respondWith(networkFirst(event)); return; }
  if (/\.(css|js|mjs|woff2?)$/.test(p)) { event.respondWith(staleWhileRevalidate(event, url, "static")); return; }
  if (/\.(png|jpe?g|webp|gif|svg|ico|avif)$/.test(p)) { event.respondWith(staleWhileRevalidate(event, url, "img")); return; }
  // anything else (documents, downloads): straight to the network, as without a worker
});

/* ------------------------------------------------------------------ pages */
const served = new Map(); // client id → when the saved copy we answered with was saved (pwa.js asks)

function pageKey(url) {
  const u = new URL(url);
  let p = u.pathname.replace(/index\.html$/, "");
  // "…/es", "…/es/meetings" (typed, or printed: the Spanish Monthly poster's address): the page with its
  // last slash — online GitHub Pages sends the visitor on there; offline, its kept copy answers
  if (!p.endsWith("/") && !/\.[a-z0-9]{2,5}$/i.test(p)) p += "/";
  return u.origin + p;
}
// A Spanish address: under /es/ — or "/es" itself, without its slash
function spanish(url) { return url.pathname.startsWith(BASE + "es/") || url.pathname === BASE + "es"; }
function isHtml(res) { return /text\/html/i.test(res.headers.get("content-type") || ""); }
function inScope(url) {
  try { const u = new URL(url); return u.origin === self.location.origin && u.pathname.startsWith(BASE); } catch (e) { return false; }
}
// The offline pages live in the app shell (never among the pages kept: they are the stand-in, keepOffline)
function isOfflinePage(key) { return key === self.location.origin + CONFIG.offline.en || key === self.location.origin + CONFIG.offline.es; }
function keepable(res, key) {
  return res && res.status === 200 && res.type === "basic" && isHtml(res) && inScope(key) && !/\/404\.html$/.test(key) && !isOfflinePage(key);
}
const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'", "#x27": "'", nbsp: " " };
function decode(s) { return s.replace(/&(#39|#x27|amp|lt|gt|quot|nbsp);/g, (m, k) => ENT[k] || m); }

/* The copy we keep: the page's HTML + when it was saved + its title (the offline page lists both
   without reading every page again) + x-gvlv-moved when it is only a forwarding page (an old address
   whose meta refresh sends the visitor on — /meeting/, the old install page, a month gone from
   /monthly/ …: kept, so an old link still works offline, but the offline page doesn't list it). Only
   safe headers are carried over. */
async function stamp(res) {
  const text = await res.text();
  const head = text.slice(0, 12000);
  const m = /<title>([^<]*)<\/title>/i.exec(head);
  const h = new Headers({ "content-type": res.headers.get("content-type") || "text/html; charset=utf-8", "x-gvlv-saved": new Date().toISOString() });
  if (m) h.set("x-gvlv-title", encodeURIComponent(decode(m[1]).trim()));
  if (/<meta\b[^>]*\bhttp-equiv=["']?refresh\b/i.test(head)) h.set("x-gvlv-moved", "1");
  return new Response(text, { status: 200, statusText: "OK", headers: h });
}

async function keepPage(key, res) {
  const copy = await stamp(res);
  const pages = await caches.open(CACHE.pages);
  await pages.delete(key); // re-added at the end: the list stays in "last opened" order
  await pages.put(key, copy.clone());
  const saved = await caches.open(CACHE.saved);
  if (await saved.match(key)) {
    // a saved page stays fresh too — and so do the styles and scripts it asks for (this version's)
    const html = await copy.clone().text();
    await saved.put(key, copy);
    await keepCalendars(html, key);
    if (await keepAssets(html, key)) await pruneSavedAssets();
  }
  await trim("pages");
}

async function savedCopy(key) {
  return (await (await caches.open(CACHE.saved)).match(key)) || (await (await caches.open(CACHE.pages)).match(key)) || null;
}

function answeredFromCopy(event, res) {
  const id = event.resultingClientId || event.clientId;
  if (id) {
    served.set(id, res.headers.get("x-gvlv-saved") || "");
    if (served.size > 30) served.delete(served.keys().next().value);
  }
  return res;
}

async function offlinePage(url) {
  const es = spanish(url);
  const res = (await caches.match(es ? CONFIG.offline.es : CONFIG.offline.en)) || (await caches.match(CONFIG.offline.en));
  if (res) return res;
  const msg = es ? "Estás sin conexión. Intenta de nuevo cuando vuelvas a tener señal." : "You're offline. Try again when you have a signal.";
  return new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Offline</title><p style="font:1.1rem/1.5 system-ui,sans-serif;margin:2rem">${msg}</p>`,
    { status: 503, headers: { "content-type": "text/html; charset=utf-8" } });
}

async function page(event, url) {
  const key = pageKey(url.href);
  const network = (async () => {
    // cache: "no-cache" — always ask the site (a changed page comes back in full, an unchanged one
    // as a tiny "not modified"), so a page shown online is never an old copy from the HTTP cache.
    const res = await fetch(new Request(event.request, { cache: "no-cache" }));
    if (keepable(res, key)) event.waitUntil(keepPage(key, res.clone()).catch(() => {}));
    // The offline page itself: its answer is the stand-in's new copy. Any other page: the stand-in in its
    // language, checked once a day (not both: the offline page would be fetched twice).
    else if (isOfflinePage(key) && res.status === 200 && res.type === "basic" && isHtml(res)) event.waitUntil(keepOffline(key, res.clone()).catch(() => {}));
    if (res.ok && !isOfflinePage(key)) event.waitUntil(refreshOffline(url).catch(() => {}));
    // (an answer from the site: there is a signal — saved pages not opened for a week are fetched again)
    if (res.ok) event.waitUntil(refreshSaved().catch(() => {}));
    return res;
  })();
  let timer = 0;
  const slow = new Promise((resolve) => { timer = setTimeout(resolve, NAV_TIMEOUT, null); });
  try {
    const res = await Promise.race([network, slow]);
    if (res) {
      clearTimeout(timer);
      if (res.status >= 500) { const copy = await savedCopy(key); if (copy) return answeredFromCopy(event, copy); }
      return res; // includes GitHub Pages' 404 page for a missing address
    }
    // No answer after 4 s (a weak signal): the saved copy if there is one; the page keeps loading
    // in the background and replaces the copy, so "Try again" gets the new one.
    const copy = await savedCopy(key);
    if (copy) { event.waitUntil(network.catch(() => {})); return answeredFromCopy(event, copy); }
    return await network;
  } catch (err) {
    clearTimeout(timer);
    const copy = await savedCopy(key);
    return copy ? answeredFromCopy(event, copy) : offlinePage(url);
  }
}

/* The offline pages are the stand-in for every page not saved; their "Join by phone" IDs, footer and
   words change with the daily content, not with the code (the version) — and only a new version's
   install fetches the app shell: keep their copies fresh. Stamped like a kept page (x-gvlv-saved: when). */
async function keepOffline(key, res) { await (await caches.open(CACHE.shell)).put(key, await stamp(res)); }
const OFFLINE_REFRESH = 24 * 3600e3;
const refreshing = {};
function refreshOffline(url) {
  const u = spanish(url) ? CONFIG.offline.es : CONFIG.offline.en;
  // (one check at a time: pages opened in a row on a weak signal don't each fetch it)
  return refreshing[u] || (refreshing[u] = (async () => {
    const shell = await caches.open(CACHE.shell);
    const have = await shell.match(u);
    if (Date.now() - (Date.parse((have && have.headers.get("x-gvlv-saved")) || "") || 0) < OFFLINE_REFRESH) return;
    const res = await fetch(u, { cache: "no-cache", credentials: "same-origin" });
    if (res.status === 200 && res.type === "basic" && isHtml(res)) await shell.put(u, await stamp(res));
  })().finally(() => { delete refreshing[u]; }));
}

/* The pages saved for offline ("Save key pages", the booth display's About page) stay fresh: one opened online is
   kept again then (keepPage); one not opened for a WEEK is fetched again in the background, once a page opened
   online shows there is a signal — one page at a time, each given SETTLE_TIMEOUT, and its styles and scripts
   (keepAssets) SETTLE_TIMEOUT more; the first that fails or is too slow ends the round (the signal is weak again:
   the next round tries). A page gone (404) or moved elsewhere keeps its copy as it is, and so does one whose files
   did not all come (the old copy opens whole offline). Looked at most every 6 hours, one round at a time. */
const SAVED_REFRESH = 7 * 24 * 3600e3;
let savedLooked = 0, savedRound = null;
function refreshSaved() {
  if (savedRound) return savedRound;
  if (Date.now() - savedLooked < REVALIDATE_AFTER) return Promise.resolve();
  savedLooked = Date.now();
  savedRound = (async () => {
    if (!(await caches.has(CACHE.saved))) return;
    const saved = await caches.open(CACHE.saved);
    let fresh = 0;
    for (const req of await saved.keys()) {
      const have = await saved.match(req);
      const at = Date.parse((have && have.headers.get("x-gvlv-saved")) || "") || 0;
      if (Date.now() - at < SAVED_REFRESH || !inScope(req.url)) continue;
      let copy;
      try {
        copy = await within(SETTLE_TIMEOUT, async (signal) => {
          const res = await fetch(req.url, { credentials: "same-origin", cache: "no-cache", signal });
          return keepable(res, req.url) && pageKey(res.url || req.url) === req.url ? stamp(res) : null;
        });
      } catch (e) { break; }
      if (!copy) continue;
      // its styles and scripts (a new version's, after a deploy) within the time limit too — and the new copy only
      // replaces the old one when they are all there: without them it would open offline unstyled, its scripts gone
      const html = await copy.clone().text();
      let whole = false;
      try {
        whole = await within(SETTLE_TIMEOUT, async () => {
          await keepAssets(html, req.url);
          await keepCalendars(html, req.url);
          return assetsKept(html, req.url);
        });
      } catch (e) { break; }
      if (!whole) continue;
      await saved.put(req.url, copy);
      fresh += 1;
    }
    if (fresh) await pruneSavedAssets();
  })().finally(() => { savedRound = null; });
  return savedRound;
}

/* ------------------------------------------------------------------ static files */
function immutable(url) { return url.searchParams.has("v") || /\/assets\/fonts\//.test(url.pathname); }

async function staleWhileRevalidate(event, url, which) {
  const req = event.request;
  // The app shell (logo, icons, favicon, this version's CSS and JS) is answered as it is: it was
  // fetched fresh when this version installed, and a new version brings a new shell. (Refreshing it
  // would put the copy into another cache that caches.match never reaches — every page view again.)
  const shellHit = await (await caches.open(CACHE.shell)).match(req);
  if (shellHit) return shellHit;
  const hit = await caches.match(req);
  const refresh = () => fetch(req).then(async (res) => {
    if (res.ok && res.status === 200 && res.type === "basic") {
      const copy = res.clone();
      event.waitUntil((async () => { const c = await caches.open(CACHE[which]); await c.put(req, copy); await trim(which); })().catch(() => {}));
    }
    return res;
  });
  if (hit) {
    const age = Date.now() - (Date.parse(hit.headers.get("date") || "") || 0);
    if (!immutable(url) && age > REVALIDATE_AFTER) event.waitUntil(refresh().catch(() => {}));
    return hit;
  }
  try {
    return await refresh();
  } catch (err) {
    // Offline and not kept: any version of the same file (a saved page can ask for an older ?v=).
    const any = await caches.match(req, { ignoreSearch: true });
    if (any) return any;
    throw err;
  }
}

/* ------------------------------------------------------------------ JSON indexes */
async function networkFirst(event) {
  const req = event.request;
  const cache = await caches.open(CACHE.data);
  const hit = await cache.match(req, { ignoreSearch: true });
  const u = new URL(req.url);
  return fromNetwork(event, hit, (copy) => cache.put(u.origin + u.pathname, copy).then(() => trim("data")));
}

/* NETWORK FIRST (the JSON indexes, the booth display's show): the site's answer — a good one (200, our
   site) is handed to keep(copy) in the background; the saved copy `hit` when the network fails, answers
   with a server error or takes more than 6 s (that answer is still kept when it comes). No copy: the
   network, however long it takes. */
async function fromNetwork(event, hit, keep) {
  const net = fetch(event.request).then((res) => {
    if (res.ok && res.status === 200 && res.type === "basic") event.waitUntil(keep(res.clone()).catch(() => {}));
    return res;
  });
  if (!hit) return net;
  let timer = 0;
  const slow = new Promise((resolve) => { timer = setTimeout(resolve, DATA_TIMEOUT, null); });
  try {
    const res = await Promise.race([net, slow]);
    clearTimeout(timer);
    if (res && res.status < 500) return res;
    event.waitUntil(net.catch(() => {}));
    return hit;
  } catch (err) {
    clearTimeout(timer);
    return hit;
  }
}

/* ------------------------------------------------------------------ the booth display */
/* The booth display (the About page's #booth, src/assets/js/booth.js) plays unattended for hours at the
   committee's table at assemblies and events — where the Wi-Fi is weak or missing. Its offline copy,
   gvlv-booth-v1, holds the show (/about/booth.json), its photos, videos and sounds (/about/booth/media/)
   and the posters and thumbnails its slides use; the booth fills it (BOOTH_SAVE, below) and empties it
   (BOOTH_CLEAR) — nothing else does: it is not trimmed, and a new version of the worker keeps it.
   A photo, video or sound and the show are kept under their address without any ?query (names that
   never change, and one show: one copy whatever the page adds); anything else (posters, thumbnails —
   the image rule finds them in any of our caches by their exact address) exactly as asked. */
function boothKey(href) {
  const u = new URL(href, self.location.origin);
  const plain = u.pathname.startsWith(BASE + BOOTH.media) || u.pathname === BASE + BOOTH.json;
  return u.origin + u.pathname + (plain ? "" : u.search);
}
function isBoothMedia(href) { return new URL(href, self.location.origin).pathname.startsWith(BASE + BOOTH.media); }
function isBoothShow(href) { return new URL(href, self.location.origin).pathname === BASE + BOOTH.json; }
// A match in the booth's copy — without making an empty copy (caches.open would) on a device that saved none
async function boothHit(key) {
  if (!(await caches.has(CACHE.booth))) return undefined;
  return (await caches.open(CACHE.booth)).match(key);
}

/* A photo, video or sound of the booth: the saved copy, else the network as it is (its Range header
   passed on; never kept here — the copy is made only by BOOTH_SAVE, within the booth's size limits).
   A media player reads a file in parts — "Range: bytes=0-", then "bytes=1048576-" when it seeks — and
   each part comes from the saved copy, exactly those bytes (206 Partial Content, with Content-Range,
   Accept-Ranges and Content-Length): so a video plays, and seeks, offline. A part past the end → 416;
   a range we don't read (several parts at once, another unit) → the whole file, as a server may. */
async function boothMedia(event, url) {
  const req = event.request;
  const hit = await boothHit(boothKey(url.href)).catch(() => undefined);
  if (!hit) return fetch(req);
  const r = byteRange(req.headers.get("range"));
  if (!r) return hit;
  try {
    const blob = await hit.blob();
    const size = blob.size, span = inFile(r, size);
    if (!span) return new Response(null, { status: 416, statusText: "Range Not Satisfiable", headers: { "content-range": "bytes */" + size } });
    const [first, last] = span;
    return new Response(blob.slice(first, last + 1), {
      status: 206,
      statusText: "Partial Content",
      headers: {
        "content-type": hit.headers.get("content-type") || blob.type || "application/octet-stream",
        "content-length": String(last - first + 1),
        "content-range": `bytes ${first}-${last}/${size}`,
        "accept-ranges": "bytes",
      },
    });
  } catch (e) {
    return fetch(req); // the copy can't be read: the network, as without it
  }
}

/* "bytes=a-b", "bytes=a-" (to the end), "bytes=-n" (the last n bytes) → { a, b } (null where left out);
   null when it isn't one range of bytes (several parts, another unit, the end before the start). */
function byteRange(header) {
  const m = /^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$/i.exec(header || "");
  if (!m || (!m[1] && !m[2])) return null;
  const a = m[1] ? Number(m[1]) : null, b = m[2] ? Number(m[2]) : null;
  return a !== null && b !== null && b < a ? null : { a, b };
}
/* → [first, last] (byte positions, both included) within a file of `size` bytes; null when not one byte
   of the file is asked for (a start at or past the end, "the last 0 bytes", an empty file) */
function inFile(r, size) {
  if (r.a === null) return r.b > 0 && size > 0 ? [Math.max(0, size - r.b), size - 1] : null;
  return r.a < size ? [r.a, r.b === null ? size - 1 : Math.min(r.b, size - 1)] : null;
}

/* The show (/about/booth.json — one file for both languages, rebuilt with every deploy): NETWORK FIRST
   like the JSON indexes, kept in the data cache (so the About page's preview works offline after one
   visit); and when the booth saved its copy, that copy is replaced by each new answer too (a booth that
   plays online stays up to date offline). Offline, on a server error or after 6 s: the booth's copy,
   else the data cache's. */
async function boothJson(event, url) {
  const key = url.origin + url.pathname;
  const data = await caches.open(CACHE.data);
  const kept = await boothHit(key);
  const hit = kept || (await data.match(key));
  return fromNetwork(event, hit, async (copy) => {
    const booth = kept ? copy.clone() : null;
    await data.put(key, copy);
    await trim("data");
    // (still there: a copy removed meanwhile — BOOTH_CLEAR — is not brought back by the show alone)
    if (booth && (await boothHit(key))) await (await caches.open(CACHE.booth)).put(key, booth);
  });
}

/* ------------------------------------------------------------------ caps (oldest first) */
const trimming = {};
function trim(which) {
  const max = LIMIT[which];
  if (!max) return Promise.resolve();
  trimming[which] = (trimming[which] || Promise.resolve()).then(async () => {
    const c = await caches.open(CACHE[which]);
    const keys = await c.keys();
    for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
  }).catch(() => {});
  return trimming[which];
}

/* ------------------------------------------------------------------ "Save key pages for offline" */
// This month in the site's zone (CONFIG.tz: config/site.yml site.timezone — the worker has no window.SITE)
function chicagoMonth() {
  try {
    const p = new Intl.DateTimeFormat("en-US", { timeZone: CONFIG.tz || "America/Chicago", year: "numeric", month: "2-digit" }).formatToParts(new Date());
    return p.find((x) => x.type === "year").value + "-" + p.find((x) => x.type === "month").value;
  } catch (e) {
    return new Date().toISOString().slice(0, 7);
  }
}

function saveList(lang) {
  const pre = lang === "es" ? BASE + "es/" : BASE;
  const hasHub = CONFIG.save.includes("monthly/");
  return CONFIG.save.map((path) => {
    // "monthly/{month}/" = this month's toolkit page (the hub if that page isn't there — unless the hub
    // is on the list anyway: then a missing month page is simply skipped)
    if (path.includes("{month}")) {
      const month = pre + path.replace("{month}", chicagoMonth());
      return hasHub ? [month] : [month, pre + path.replace("{month}/", "")];
    }
    return [pre + path];
  });
}

/* The site's own styles, scripts and fonts a page asks for (<script src>, <link rel=stylesheet|preload>). */
const ASSET_RE = /<(?:script|link)\b[^>]*?\b(?:src|href)="([^"]+)"[^>]*>/gi;
function assetUrls(html, pageUrl) {
  const urls = new Set();
  let m;
  ASSET_RE.lastIndex = 0;
  while ((m = ASSET_RE.exec(html))) {
    const tag = m[0];
    if (/^<link/i.test(tag) && !/rel="(?:stylesheet|preload)"/i.test(tag)) continue;
    try {
      const u = new URL(m[1].replace(/&amp;/g, "&"), pageUrl);
      if (inScope(u.href) && /\.(css|js|woff2)$/.test(u.pathname)) urls.add(u.href);
    } catch (e) { /* not a URL */ }
  }
  return urls;
}

/* A first visit's page (kept after activation: keepOpenTabs): the styles and scripts it asked for, into this
   version's static cache (they are not in any of our caches yet) — each download within SETTLE_TIMEOUT. */
async function keepFiles(html, pageUrl) {
  const cache = await caches.open(CACHE.static);
  await Promise.all([...assetUrls(html, pageUrl)].map(async (u) => {
    try {
      if (await caches.match(u)) return;
      await within(SETTLE_TIMEOUT, async (signal) => {
        const res = await fetch(u, { credentials: "same-origin", signal });
        if (res && res.ok && res.type === "basic") await cache.put(u, res);
      });
    } catch (e) { /* offline again, or too slow */ }
  }));
  await trim("static");
}

/* A saved page's files go into gvlv-saved-assets-v1, which outlives site updates: the saved copy asks
   for them by their ?v= address, and gvlv-static-<version> is deleted by the next version. Copied from
   the caches when they are there (no download), fetched otherwise. → how many files were added. */
async function keepAssets(html, pageUrl) {
  const cache = await caches.open(CACHE.savedAssets);
  let added = 0;
  await Promise.all([...assetUrls(html, pageUrl)].map(async (u) => {
    if (await cache.match(u)) return;
    try {
      const have = await caches.match(u);
      const res = have || await fetch(u, { credentials: "same-origin" });
      if (res && res.ok && res.type === "basic") { await cache.put(u, have ? have.clone() : res); added += 1; }
    } catch (e) { /* offline again */ }
  }));
  return added;
}
// Every style and script the page asks for is among the saved pages' files (a font may be missing: the page shows
// in the device's own)
async function assetsKept(html, pageUrl) {
  const cache = await caches.open(CACHE.savedAssets);
  for (const u of assetUrls(html, pageUrl)) if (/\.(css|js)$/.test(new URL(u).pathname) && !(await cache.match(u))) return false;
  return true;
}

/* A month page's calendar file ("Add October's dates to my calendar": /monthly/YYYY-MM/<name>.ics, beside the page
   that links it — src/pages/monthly-ics.11ty.js). Saved with the page into gvlv-saved-assets-v1 (and pruned with it:
   last month's goes with last month's page), so the link works offline too. Only such a file, never the big
   /events.ics feeds (they stay network only). Fetched again each time its page is saved (its dates change with the
   daily content); a download that fails keeps the copy there is. */
const MONTH_ICS = /\/monthly\/\d{4}-\d{2}\/[^/]+\.ics$/;
const CAL_RE = /<a\b[^>]*?\bhref="([^"]+)"[^>]*>/gi;
function calendarUrls(html, pageUrl) {
  const urls = new Set();
  const dir = new URL(pageKey(pageUrl)).pathname;
  let m;
  CAL_RE.lastIndex = 0;
  while ((m = CAL_RE.exec(html))) {
    try {
      const u = new URL(m[1].replace(/&amp;/g, "&"), pageUrl);
      // beside the page itself (its own folder), a month's file
      if (inScope(u.href) && MONTH_ICS.test(u.pathname) && u.pathname.startsWith(dir) && !u.pathname.slice(dir.length).includes("/")) {
        urls.add(u.origin + u.pathname);
      }
    } catch (e) { /* not a URL */ }
  }
  return urls;
}
async function keepCalendars(html, pageUrl) {
  const files = [...calendarUrls(html, pageUrl)];
  if (!files.length) return;
  const cache = await caches.open(CACHE.savedAssets);
  await Promise.all(files.map(async (u) => {
    try {
      const res = await fetch(u, { credentials: "same-origin", cache: "no-cache" });
      if (res && res.ok && res.status === 200 && res.type === "basic") await cache.put(u, res);
    } catch (e) { /* offline again: the copy there is stays */ }
  }));
}
// A month's calendar file asked for — a tap on the page's link is a navigation: kept with its saved page → NETWORK
// FIRST (the answer replaces the copy), that copy offline, on a server error or after 6 s; not kept → the network,
// as without a worker (nothing is kept; a tap on the link offline gets the offline page, as any page not saved)
async function calendarFile(event, url) {
  const key = url.origin + url.pathname;
  const cache = await caches.open(CACHE.savedAssets);
  const hit = await cache.match(key);
  if (!hit) return event.request.mode === "navigate" ? page(event, url) : fetch(event.request);
  return fromNetwork(event, hit, (copy) => cache.put(key, copy));
}

/* Keep only the files the saved pages still ask for (older versions' files go once no saved copy
   needs them any more). */
let pruning = Promise.resolve();
function pruneSavedAssets() {
  pruning = pruning.then(async () => {
    const saved = await caches.open(CACHE.saved);
    const need = new Set();
    for (const req of await saved.keys()) {
      const res = await saved.match(req);
      if (res) {
        const html = await res.text();
        for (const u of [...assetUrls(html, req.url), ...calendarUrls(html, req.url)]) need.add(u);
      }
    }
    const cache = await caches.open(CACHE.savedAssets);
    for (const req of await cache.keys()) if (!need.has(req.url)) await cache.delete(req);
  }).catch(() => {});
  return pruning;
}

/* Last month's toolkit page, saved last month, is not this month's key page: it goes (in this language). */
async function dropOldMonths(lang, saved) {
  const re = new RegExp("^" + (self.location.origin + BASE + (lang === "es" ? "es/" : "")).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "monthly/(\\d{4}-\\d{2})/$");
  const now = chicagoMonth();
  for (const req of await saved.keys()) {
    const m = re.exec(req.url);
    if (m && m[1] !== now) await saved.delete(req);
  }
}

/* One page saved for offline ("Save key pages", and the booth display's About page: BOOTH_SAVE): the first
   of its addresses that answers with a page of our site — stamped (stamp), the styles and scripts it asks
   for kept in gvlv-saved-assets-v1 (keepAssets), the copy in gvlv-saved-v1. `keys`: the pages saved in
   this run. → "saved", "dup" (the same page again: a redirect to one saved in this run) or "" (none of
   its addresses could be saved). */
async function savePage(saved, tries, keys) {
  for (const u of tries) {
    try {
      const res = await fetch(u, { credentials: "same-origin", cache: "no-cache" });
      if (!res.ok || res.type !== "basic" || !isHtml(res)) continue;
      const key = pageKey(res.url || u);
      if (!inScope(key)) continue;
      if (keys.has(key)) return "dup"; // the same page again (a redirect): counted once
      const copy = await stamp(res);
      const html = await copy.clone().text();
      await keepAssets(html, key);
      await keepCalendars(html, key);
      await saved.put(key, copy);
      keys.add(key);
      return "saved";
    } catch (e) { /* try the next address, or give up on this page */ }
  }
  return "";
}

async function savePages(lang, reply) {
  const list = saveList(lang);
  const saved = await caches.open(CACHE.saved);
  await dropOldMonths(lang, saved).catch(() => {});
  let done = 0, ok = 0, total = list.length;
  const failed = [], keys = new Set();
  reply({ type: "SAVE_PROGRESS", done, total });
  for (const tries of list) {
    const got = await savePage(saved, tries, keys);
    const good = got === "saved", dup = got === "dup";
    // no page for this month (yet) while the hub is saved anyway: not a failure, not counted
    const noMonth = !good && tries.length === 1 && /\/monthly\/\d{4}-\d{2}\/$/.test(tries[0]) && CONFIG.save.includes("monthly/");
    if (dup || noMonth) total -= 1;
    else {
      done += 1;
      if (good) ok += 1; else failed.push(tries[0]);
    }
    reply({ type: "SAVE_PROGRESS", done, total });
  }
  await saveFiles();
  await pruneSavedAssets();
  reply({ type: "SAVE_DONE", saved: ok, total, failed });
}

/* The data files saved with the pages (CONFIG.files: the workshop presentations' JSON and the Texas writers
   archive's, the same in both languages) go where the network-first rule for JSON looks — the data cache,
   under the address without its ?query (networkFirst) — so a presentation, or the whole archive, opens
   offline. They are not pages: not counted in "Saved N pages", and one that can't be fetched is skipped like
   a page's own files (its page fetches it again, and keeps a copy, when it is opened online). */
async function saveFiles() {
  const files = CONFIG.files || [];
  if (!files.length) return;
  const cache = await caches.open(CACHE.data);
  for (const path of files) {
    try {
      const u = new URL(BASE + path, self.location.origin);
      const res = await fetch(u.href, { credentials: "same-origin", cache: "no-cache" });
      if (res && res.ok && res.status === 200 && res.type === "basic") await cache.put(u.origin + u.pathname, res);
    } catch (e) { /* offline again */ }
  }
  await trim("data");
}

/* ------------------------------------------------------------------ the booth display's offline copy */
/* Messages from booth.js (its swCall): each one comes with a MessageChannel port, as pwa.js's SAVE does, and every
   answer below goes back through that port. The page posts it to the worker of the site's registration that knows
   these messages: the active one — but on a device that had the site before, this version's worker may still be
   WAITING behind an old one that knows none of them. Then a BOOTH_STATUS goes to the waiting worker as it is (a
   visitor's page never swaps workers), while before a BOOTH_SAVE or BOOTH_CLEAR the page sends the waiting one
   SKIP_WAITING and posts to it once it has taken over (its activate claims the page) — or still waiting, after
   10 s: a waiting worker answers too.
   * BOOTH_SAVE { pages, files, prune } — on start and after a content update, while online. `pages` (the
     About page in both languages) are saved the way "Save key pages" saves one (savePage), so the page
     opens offline; then the `files` go into gvlv-booth-v1: the show (booth.json) first and always
     fetched again; a photo, video or sound only when it isn't kept yet (its name never changes);
     anything else (posters, thumbnails) fetched again. Only our site's own good answers (200) are kept.
     Answers: BOOTH_PROGRESS { done, total, bytes } at once, after each page and file, every 2 s while
     a big file downloads (bytes growing — so a page waiting for news doesn't give up on a 90 MB video
     on a busy hall's Wi-Fi) and every 10 s while the save waits for its turn (done 0: another save asked
     before it is still running); then BOOTH_DONE { saved, total, failed (the first 20 addresses not
     saved), bytes (of the files now kept) }. prune: the files the list no longer names leave the copy —
     once the show itself was saved fresh (a copy never loses the files its booth.json still names), and
     before the new files download (room for them); a list without files prunes nothing.
     BOOTH_DONE may also say why it ended early — the rest are among `failed` and are simply tried again
     by the next save (every file is kept the moment it arrives): `more` (4 minutes passed: a browser
     lets one task run about 5, then stops the worker — post BOOTH_SAVE again to go on), `full` (no
     room left on the device), `stopped` (BOOTH_CLEAR came).
   * BOOTH_STATUS { files } → BOOTH_STATUS { have, total, bytes, missing (the first 20) }: how much of
     that list the copy holds (Settings → Offline: "Ready offline: 86 files · 240 MB"); at once, during
     a save too.
   * BOOTH_CLEAR → the copy removed → BOOTH_CLEARED ("Remove the offline copy"). The About page stays
     among the saved pages (the offline page lists it, and removes it from there).
   One save or removal at a time, in the order asked: two saves never download the same video twice, a
   save's prune never races another save, and a removal first stops the saves asked before it (the
   file downloading is let go). Addresses outside the site (another site, another GitHub Pages
   project) are left out — never fetched, never counted. */
const BOOTH_BUDGET = 4 * 60e3; // a save starts no new file after 4 minutes (→ BOOTH_DONE { more: true })
const BOOTH_NEWS = 2000;       // a big file's progress while it downloads: at most every 2 s
const BOOTH_WAIT_NEWS = 10000; // a save waiting for its turn says so (BOOTH_PROGRESS, done 0) every 10 s
const BOOTH_LISTED = 20;       // addresses listed in an answer (failed, missing): at most
let boothJob = Promise.resolve();
let boothGen = 0;              // + 1 with each BOOTH_CLEAR: the saves asked before it stop
let boothAbort = null;         // the running save's downloads (AbortController), let go by BOOTH_CLEAR
function boothQueue(fn) {
  const run = boothJob.then(fn);
  boothJob = run.catch(() => {});
  return run;
}

/* A list from booth.js → our own addresses (absolute, or relative to the site's base), each once (by
   keyOf: pageKey for pages, boothKey for files), without #fragment. */
function boothList(list, keyOf) {
  const out = [], seen = new Set();
  for (const item of Array.isArray(list) ? list : []) {
    let u;
    try { u = new URL(String(item), self.location.origin + BASE); } catch (e) { continue; }
    u.hash = "";
    if (!inScope(u.href)) continue;
    const k = keyOf(u.href);
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(u.href);
  }
  return out;
}

// The size of a kept file: its Content-Length, else its body's size
async function sizeOf(res) {
  const n = Number(res.headers.get("content-length"));
  if (n > 0) return n;
  try { return (await res.blob()).size; } catch (e) { return 0; }
}

/* A big file's news while it downloads: its body passes through a counter on its way into the copy
   (nothing is held in memory). Without streams (an old browser) the file is kept as it comes. */
function counted(res, onBytes) {
  if (!res.body || typeof TransformStream !== "function") return res;
  let n = 0, last = Date.now();
  const body = res.body.pipeThrough(new TransformStream({
    transform(chunk, ctl) {
      n += chunk.byteLength;
      if (Date.now() - last >= BOOTH_NEWS) { last = Date.now(); onBytes(n); }
      ctl.enqueue(chunk);
    },
  }));
  return new Response(body, { status: res.status, statusText: res.statusText, headers: res.headers });
}

/* One file into the booth's copy → { ok, bytes, full }. The show: always fetched again ("no-cache": a
   tiny "not modified" when it hasn't changed); a photo, video or sound already kept: nothing to fetch;
   anything else: fetched again. Kept only when it is our site's whole file (200) — never a part of one
   (206) or an error page. A photo or video whose download breaks off (or a browser whose cache won't
   take the counted stream) is fetched once more and kept as it comes — not after "no room" or a
   removal (BOOTH_CLEAR). */
async function boothFile(cache, href, abort, onBytes) {
  const key = boothKey(href), media = isBoothMedia(href);
  const get = () => fetch(href, { credentials: "same-origin", cache: media ? "default" : "no-cache", signal: abort ? abort.signal : undefined });
  const whole = (res) => !!res && res.status === 200 && res.type === "basic";
  try {
    if (media) {
      const have = await cache.match(key);
      if (have) return { ok: true, bytes: await sizeOf(have) };
    }
    const res = await get();
    if (!whole(res)) return { ok: false };
    if (!media) await cache.put(key, res);
    else {
      try {
        await cache.put(key, counted(res, onBytes));
      } catch (e) {
        if (e && (e.name === "QuotaExceededError" || e.name === "AbortError")) throw e;
        const again = await get();
        if (!whole(again)) return { ok: false };
        await cache.put(key, again);
      }
    }
    const kept = await cache.match(key);
    return { ok: true, bytes: kept ? await sizeOf(kept) : 0 };
  } catch (e) {
    return { ok: false, full: !!e && e.name === "QuotaExceededError" };
  }
}

// The files the booth's list no longer names leave its copy (a list without files prunes nothing)
async function boothPrune(cache, files) {
  if (!files.length) return;
  const keep = new Set(files.map(boothKey));
  for (const req of await cache.keys()) if (!keep.has(req.url)) await cache.delete(req);
}

async function boothSave(job, reply) {
  const show = job.files.filter(isBoothShow);
  const list = [...job.pages.map((u) => ["page", u]), ...show.map((u) => ["file", u]),
    ...job.files.filter((u) => !isBoothShow(u)).map((u) => ["file", u])];
  const total = list.length, failed = [];
  let done = 0, saved = 0, bytes = 0, pagesSaved = 0, end = "";
  let fresh = !show.length, pruned = !job.prune; // fresh: the show saved in this run (or not in the list)
  const fail = (u) => { if (failed.length < BOOTH_LISTED) failed.push(u); };
  const news = (more = 0) => reply({ type: "BOOTH_PROGRESS", done, total, bytes: bytes + more });
  // "stopped" (BOOTH_CLEAR), "more" (out of time: the page asks again), "full" (no room), "error" (no storage)
  const halt = () => end || (job.gen !== boothGen ? "stopped" : Date.now() > job.until ? "more" : "");
  const abort = typeof AbortController === "function" ? new AbortController() : null;
  boothAbort = abort;
  try {
    let shelf = null, cache = null;
    try { shelf = await caches.open(CACHE.saved); cache = await caches.open(CACHE.booth); } catch (e) { end = "error"; }
    const keys = new Set();
    for (const [kind, u] of list) {
      if ((end = halt())) { fail(u); continue; } // not reached: tried again by the next save
      if (kind === "page") {
        if (await savePage(shelf, [u], keys)) { saved += 1; pagesSaved += 1; } else fail(u);
      } else {
        if (fresh && !pruned && !isBoothShow(u)) { await boothPrune(cache, job.files).catch(() => {}); pruned = true; }
        const got = await boothFile(cache, u, abort, news);
        if (got.ok) { saved += 1; bytes += got.bytes; if (isBoothShow(u)) fresh = true; }
        else { fail(u); if (got.full) end = "full"; }
      }
      done += 1;
      news();
    }
    if (cache && fresh && !pruned && end !== "stopped") await boothPrune(cache, job.files).catch(() => {});
    if (pagesSaved) await pruneSavedAssets();
  } catch (e) {
    /* a surprise: what was saved is still reported (BOOTH_DONE always comes) */
  } finally {
    if (boothAbort === abort) boothAbort = null;
  }
  const why = end === "more" || end === "full" || end === "stopped" ? { [end]: true } : {};
  reply({ type: "BOOTH_DONE", saved, total, failed, bytes, ...why });
}

async function boothStatus(files, reply) {
  let have = 0, bytes = 0;
  const missing = [];
  try {
    const cache = (await caches.has(CACHE.booth)) ? await caches.open(CACHE.booth) : null;
    for (const u of files) {
      const hit = cache && (await cache.match(boothKey(u)));
      if (hit) { have += 1; bytes += await sizeOf(hit); }
      else if (missing.length < BOOTH_LISTED) missing.push(u);
    }
  } catch (e) { /* storage unavailable: what was counted */ }
  reply({ type: "BOOTH_STATUS", have, total: files.length, bytes, missing });
}

async function boothClear(reply) {
  try { await caches.delete(CACHE.booth); } catch (e) { /* nothing to remove */ }
  reply({ type: "BOOTH_CLEARED" });
}

/* ------------------------------------------------------------------ messages from pwa.js and booth.js */
self.addEventListener("message", (event) => {
  const d = event.data || {};
  const port = event.ports && event.ports[0];
  const reply = (msg) => { try { if (port) port.postMessage(msg); else if (event.source) event.source.postMessage(msg); } catch (e) { /* page gone */ } };
  if (d.type === "SKIP_WAITING") self.skipWaiting();
  else if (d.type === "HOW_SERVED") {
    const id = event.source && event.source.id;
    const s = id && served.has(id) ? served.get(id) : null;
    if (id) served.delete(id);
    reply({ type: "HOW_SERVED", copy: s !== null, savedAt: s || null, version: V });
  } else if (d.type === "SAVE") event.waitUntil(savePages(d.lang === "es" ? "es" : "en", reply));
  else if (d.type === "VERSION") reply({ type: "VERSION", version: V });
  else if (d.type === "BOOTH_SAVE") {
    const job = { pages: boothList(d.pages, pageKey), files: boothList(d.files, boothKey), prune: !!d.prune, gen: boothGen, until: Date.now() + BOOTH_BUDGET };
    // at once — and, while a save asked before it is still running (this one waits its turn), every 10 s
    const waiting = () => reply({ type: "BOOTH_PROGRESS", done: 0, total: job.pages.length + job.files.length, bytes: 0 });
    waiting();
    const beat = setInterval(waiting, BOOTH_WAIT_NEWS);
    event.waitUntil(boothQueue(() => { clearInterval(beat); return boothSave(job, reply); }));
  } else if (d.type === "BOOTH_STATUS") event.waitUntil(boothStatus(boothList(d.files, boothKey), reply));
  else if (d.type === "BOOTH_CLEAR") {
    boothGen += 1;
    if (boothAbort) boothAbort.abort();
    event.waitUntil(boothQueue(() => boothClear(reply)));
  }
});
