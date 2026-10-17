// The sitemap's <lastmod>: the day and time each page's CONTENT last changed — not the build's (the site is built
// four or more times a day, and a date that always moves teaches search engines to ignore it: Google uses lastmod
// only "if it's consistently and verifiably accurate", Bing distrusts dates "consistently set to the current
// date"). GitHub Pages gives every file the deploy's time as its Last-Modified, so this is the only change signal
// engines get from the site — and Website update's IndexNow step (.github/workflows/update.yml) tells Bing and
// the other IndexNow engines about exactly these changed pages after each publish.
//
// How: once the pages are written (eleventy.config.js, "eleventy.after"), each page the sitemap lists gets a
// fingerprint — sha256 of its <title>, its meta description and what its <main> SAYS (below) — and is compared with
// the fingerprints of the LAST PUBLISHED site, its lastmod.json (written here by the build before):
//   * the store: LASTMOD_STORE=<file> — Website update restores it from GitHub's Actions cache, where its
//     "publish" job keeps the lastmod.json of each site it published (so a build that is never published moves
//     nothing on, and no commit is needed). Not read back from the live site first: GitHub Pages' cache serves a
//     file — and a 404 — for a while after a deploy whatever the query, so a build could compare with an old one;
//   * else (the first time, or a cache GitHub dropped after 7 days unused) the live site's /lastmod.json.
//   same fingerprint      the page keeps its date;
//   changed, or new       this build's time (build.json "built", src/pages/build-info.11ty.js);
//   none published yet    (404: the very first time) every page gets this build's time, once — the first
//                         publish of these dates also brought every page its structured data;
//   unreadable            (no answer, an error, not this file's format) NO page gets a date this time and no
//                         store is written, so the next run compares with the last good one again — the build
//                         log and the run's summary say why.
// Then _site/lastmod.json is written (the next build's store; outside the collections and the sitemap, never
// linked: the service worker never saves it — not in its list, and visitors never ask for it) and each <url> of
// _site/sitemap.xml gets "<lastmod>2026-10-14T08:33:05Z</lastmod>" right after its <loc> (the sitemap schema's
// order: loc, lastmod, changefreq, priority).
// LASTMOD_CHANGED=<file> (Website update) gets the pages for IndexNow: {"site": the site's address, "changed":
// [absolute addresses], "total": pages in the sitemap, "dated_now": pages given this build's time, "previous":
// "ok" | "missing" | "error", "from": "store" | "live", "version_changed": the code fingerprint differs from the
// last published one's}. "changed" =
// the pages whose fingerprint changed, the new ones and the ones that left the sitemap (an engine then finds them
// gone or noindex); on the first run every page; after an unreadable lastmod.json NONE — a passing hiccup never
// sends the whole site again.
//
// What a fingerprint leaves out, so a page "changes" only when what it says does:
//   * the markup: what counts of <main> is its text, the addresses it links to or shows (href, src), the words of
//     its pictures and labels (alt, title, aria-label), its dates (datetime) and the data of its scripts (JSON) —
//     not its tags, classes, styles, ids, data-* attributes or icons (<svg>), so a change of the code that only
//     moves or restyles things (a new class in a shared macro, another icon) dates no page again and sends none to
//     IndexNow;
//   * the code fingerprint in the CSS / JS / data links, ?v=<10 hex characters> (src/_data/build.js) — only that
//     form: a YouTube link's ?v=<video id> is content;
//   * whatever the templates mark as moving with the clock, not with the content — data-lastmod="skip" on an
//     element leaves out the element and all it holds ("Updated 2 hours ago", "Prepared on October 14",
//     "due in 18 days", "Last day!" …); data-lastmod="skip:a,b" keeps the element but leaves out its attributes
//     a and b and, on a <script> holding JSON, its top-level members a and b (published.njk's pw-config
//     "today");
//   * spaces: any run of white space counts as one.
// The head (stylesheets, share pictures), the header, the footer ("Last updated …") and the site-wide JSON-LD at
// the end of <body> are outside <main>: never part of it. A page whose text moves every day without a mark makes
// every build date it again — Website update's "Check the build" warns when more than 30 pages changed while the
// code did not.
// Only in Website update's builds (LASTMOD=1 there; the Code check, the tests, `npm start` and ONLY= builds never
// fetch anything or change the sitemap) and with a site address. It never fails a build: any error leaves the
// sitemap without <lastmod> and says so in the log — and publishes the live site's lastmod.json again as it was
// (when it could be read), so one failed run never looks like a first run to the next one (which would date and
// send every page again). The store is written last, after the sitemap and the IndexNow list.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pageFacts, pathOf, siteAddress, sitemapLocs, unescapeHtml } from "./seo-check.js";

export const STATE_FILE = "lastmod.json";
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);
const START_TAG = /<([a-zA-Z][\w:-]*)\b([^>]*)>/g;
const MARK = /\sdata-lastmod="skip(?::([^"]*))?"/;
const W3C = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

// Where an element that starts at `from` (just after its start tag) ends: just after its matching end tag, or -1.
function elementEnd(html, name, from) {
  if (/^(?:script|style|textarea|title)$/i.test(name)) {
    const i = html.toLowerCase().indexOf(`</${name.toLowerCase()}`, from);
    return i < 0 ? -1 : html.indexOf(">", i) + 1;
  }
  const tag = new RegExp(`<(/?)${name}\\b[^>]*>`, "gi");
  tag.lastIndex = from;
  let depth = 1, m;
  while ((m = tag.exec(html))) {
    if (m[1]) { if (--depth === 0) return tag.lastIndex; }
    else if (!m[0].endsWith("/>")) depth++;
  }
  return -1;
}

// A JSON text without its top-level members `names` (unchanged when it is not a JSON object).
function withoutMembers(text, names) {
  try {
    const o = JSON.parse(text);
    if (!o || typeof o !== "object" || Array.isArray(o)) return text;
    for (const n of names) delete o[n];
    return JSON.stringify(o);
  } catch {
    return text;
  }
}

/** HTML without what its data-lastmod="skip" / "skip:a,b" marks leave out (see the header). */
export function dropSkipped(html) {
  const text = String(html ?? "");
  let out = "", at = 0, m;
  START_TAG.lastIndex = 0;
  while ((m = START_TAG.exec(text))) {
    const mark = MARK.exec(m[2]);
    if (!mark) continue;
    const name = m[1], tagEnd = START_TAG.lastIndex;
    out += text.slice(at, m.index);
    if (mark[1] === undefined) {
      // the whole element (a void or self-closing one is its tag; one never closed: its start tag only)
      const end = VOID.has(name.toLowerCase()) || m[0].endsWith("/>") ? tagEnd : elementEnd(text, name, tagEnd);
      at = end < 0 ? tagEnd : end;
    } else {
      const names = mark[1].split(",").map((s) => s.trim()).filter(Boolean);
      const drop = new Set(names.map((n) => n.toLowerCase()));
      // the start tag again, attribute by attribute, without the named ones (a name inside another's value stays)
      const attrs = m[2].replace(/\s+([^\s"'=<>/]+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?/g, (a, n) => (drop.has(n.toLowerCase()) ? "" : a));
      out += `<${name}${attrs}>`;
      at = tagEnd;
      if (name.toLowerCase() === "script") {
        const end = elementEnd(text, name, tagEnd);
        if (end > 0) {
          const close = text.lastIndexOf("</", end);
          out += withoutMembers(text.slice(tagEnd, close), names) + text.slice(close, end);
          at = end;
        }
      }
    }
    START_TAG.lastIndex = at;
  }
  return out + text.slice(at);
}

// The attributes whose values a page shows or links to (see the header); every other one is markup.
const SAID_ATTRS = /\s(href|src|alt|title|aria-label|datetime|poster)\s*=\s*(?:"([^"]*)"|'([^']*)')/gi;

/** What an HTML fragment SAYS (see the header): its text, its scripts' contents and, from each tag, only the values
    of the attributes in SAID_ATTRS — no comments, styles, icons (<svg>), tag names, classes, ids or data-*. */
export function projection(html) {
  return String(html ?? "")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<svg\b[\s\S]*?<\/svg>/gi, " ")
    .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
    .replace(/<script\b[^>]*>([\s\S]*?)<\/script>/gi, (_, body) => ` ${body} `)
    .replace(/<[^>]*>/g, (tag) => {
      const said = [];
      for (const m of tag.matchAll(SAID_ATTRS)) said.push(`${m[1].toLowerCase()}=${m[2] ?? m[3]}`);
      return said.length ? ` [${said.join(" ")}] ` : " ";
    });
}

/** What a page's fingerprint is made of: its <title>, its meta description and what its <main> says (projection),
    with the marked bits, the code fingerprints and the extra spaces left out. */
export function contentOf(html) {
  const text = String(html ?? "");
  const f = pageFacts(text);
  const open = /<main\b[^>]*>/i.exec(text);
  const close = text.lastIndexOf("</main>");
  const main = open && close > open.index ? text.slice(open.index + open[0].length, close) : "";
  return [f.title, f.description, projection(dropSkipped(main))].join("\n")
    .replace(/(?:\?|&amp;|&)v=[0-9a-f]{10}(?![\w-])/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/** A page's fingerprint: 16 hex characters. */
export const fingerprint = (html) => crypto.createHash("sha256").update(contentOf(html)).digest("hex").slice(0, 16);

/** An instant → the sitemap's W3C date-time, to the second, in UTC ("2026-10-14T08:33:05Z"); "" when not one. */
export function w3cTime(v) {
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** The live lastmod.json's text → { status: "ok", state } or { status: "error", why }. */
export function readState(text) {
  let s;
  try { s = JSON.parse(text); } catch { return { status: "error", why: "it is not JSON" }; }
  if (!s || typeof s !== "object" || s.v !== 1) return { status: "error", why: `not version 1 of the file (v: ${JSON.stringify(s && s.v)})` };
  if (!s.pages || typeof s.pages !== "object" || Array.isArray(s.pages)) return { status: "error", why: "it has no pages" };
  return { status: "ok", state: s };
}

/** The store of the last publish (LASTMOD_STORE, see the header) → { status: "ok", state, from: "store" }, or null
    when there is no such file or it is not a readable store (the live site's is asked then). */
export function readStore(file) {
  if (!file) return null;
  let text;
  try { text = fs.readFileSync(file, "utf8"); } catch { return null; }
  const r = readState(text);
  return r.status === "ok" ? { ...r, from: "store" } : null;
}

/** The live site's lastmod.json: { status: "ok", state } | { status: "missing", why } (404: none published yet) |
    { status: "error", why }. 10 s per try, tried again twice after no answer or a server error; a ?t= query and
    "no-cache" ask for a fresh copy, though GitHub Pages' cache may still answer with an older one (why the store
    comes first). deps: { fetch, timeoutMs, retries, waitMs } (tests). */
export async function fetchPrevious(url, deps = {}) {
  const get = deps.fetch || globalThis.fetch;
  const timeoutMs = deps.timeoutMs ?? 10000, retries = deps.retries ?? 2, waitMs = deps.waitMs ?? 2000;
  let why = "no answer";
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt && waitMs) await new Promise((r) => setTimeout(r, waitMs));
    try {
      const res = await get(`${url}?t=${Date.now()}`, { signal: AbortSignal.timeout(timeoutMs), headers: { "cache-control": "no-cache" } });
      if (res.status === 404) return { status: "missing", why: "HTTP 404 — none published yet" };
      if (!res.ok) {
        why = `HTTP ${res.status}`;
        if (res.status < 500 && res.status !== 408 && res.status !== 429) break;   // asking again would not help
        continue;
      }
      return readState(await res.text());
    } catch (e) {
      why = e && e.name === "TimeoutError" ? `no answer within ${Math.round(timeoutMs / 1000)} s` : String((e && e.message) || e);
    }
  }
  return { status: "error", why };
}

/** The dates: `hashes` {path: fingerprint} (the sitemap's pages), `previous` (fetchPrevious), `now` (W3C time) →
    { pages: {path: {h, d}}, changed: [paths for IndexNow], datedNow }. */
export function datePages(hashes, previous, now) {
  const ok = previous && previous.status === "ok";
  const before = ok ? previous.state.pages : {};
  const pages = {}, changed = [];
  let datedNow = 0;
  for (const [p, h] of Object.entries(hashes)) {
    const old = Object.prototype.hasOwnProperty.call(before, p) ? before[p] : null;
    if (ok && old && old.h === h && W3C.test(String(old.d))) {
      pages[p] = { h, d: old.d };
      continue;
    }
    // the last published store could not be read: what changed is not known — no date, nothing sent
    if (previous && previous.status === "error") {
      pages[p] = { h, d: "" };
      continue;
    }
    pages[p] = { h, d: now };
    datedNow++;
    changed.push(p);
  }
  if (ok) for (const p of Object.keys(before)) if (!(p in hashes)) changed.push(p);   // left the sitemap
  return { pages, changed, datedNow };
}

/** _site/lastmod.json's text: small, one page per line. */
export function stateText({ version = "", built = "", pages = {} }) {
  const rows = Object.entries(pages).map(([p, v]) => `${JSON.stringify(p)}:${JSON.stringify({ h: v.h, d: v.d })}`);
  return `{"v":1,"version":${JSON.stringify(version)},"built":${JSON.stringify(built)},"pages":{\n${rows.join(",\n")}\n}}\n`;
}

/** The sitemap with "<lastmod>…</lastmod>" right after each <loc> whose page has a date (any it had before is
    replaced). */
export function insertLastmod(xml, base, pages) {
  return String(xml)
    .replace(/^[ \t]*<lastmod>[^<]*<\/lastmod>\r?\n/gm, "")
    .replace(/^([ \t]*)<loc>([^<]*)<\/loc>$/gm, (line, indent, loc) => {
      const p = pathOf(unescapeHtml(loc).trim(), base);
      const d = p !== null && pages[p] && pages[p].d;
      return d && W3C.test(d) ? `${line}\n${indent}<lastmod>${d}</lastmod>` : line;
    });
}

const say = (deps, line, level = "") => {
  (deps.log || console.log)(`[lastmod] ${line}`);
  if (level && (deps.env || process.env).GITHUB_ACTIONS === "true") {
    (deps.log || console.log)(`::${level} title=Sitemap dates::${String(line).replace(/%/g, "%25").replace(/\r?\n/g, "%0A")}`);
  }
};

/** The "eleventy.after" hook (see the header). → the IndexNow summary, or null when it did nothing. deps (tests):
    { fetch, log, timeoutMs, retries, waitMs }. */
export async function updateLastmod({ results, directories, outputMode, incremental } = {}, env = process.env, deps = {}) {
  if (env.LASTMOD !== "1" || env.ONLY || incremental || (outputMode && outputMode !== "fs")) return null;
  deps = { ...deps, env };
  // A list from an earlier build of this run (the second build after the share pictures) never stands for this one.
  let sitemap = null, previous = null, out = "_site";
  try {
    if (env.LASTMOD_CHANGED) fs.rmSync(env.LASTMOD_CHANGED, { force: true });
    const base = siteAddress(env);
    const all = Array.isArray(results) ? results : [];
    sitemap = all.find((r) => r && r.url === "/sitemap.xml");
    if (!base || !sitemap || !sitemap.outputPath || typeof sitemap.content !== "string") {
      const what = base ? "no sitemap" : "no site address (config/site.yml: site url)";
      say(deps, what + " — no <lastmod> in this build");
      return null;
    }
    let build = {};
    try { build = JSON.parse((all.find((r) => r && r.url === "/build.json") || {}).content || "{}"); } catch { build = {}; }
    const now = w3cTime(build.built || Date.now());
    const version = String(build.version || "");
    out = (directories && directories.output) || "_site";
    // the last published store first (should anything below fail, it is published again as it was: the catch)
    previous = readStore(env.LASTMOD_STORE) || { ...(await fetchPrevious(`${base}/${STATE_FILE}`, deps)), from: "live" };
    const byUrl = new Map(all.filter((r) => r && typeof r.content === "string").map((r) => [r.url, r]));
    const locs = sitemapLocs(sitemap.content);
    const hashes = {};
    for (const loc of locs) {
      const p = pathOf(loc, base);
      if (p !== null && byUrl.has(p)) hashes[p] = fingerprint(byUrl.get(p).content);
    }
    const { pages, changed, datedNow } = datePages(hashes, previous, now);
    fs.writeFileSync(sitemap.outputPath, insertLastmod(sitemap.content, base, pages));
    const summary = {
      site: base,
      changed: changed.map((p) => base + p),
      total: locs.length,
      dated_now: datedNow,
      previous: previous.status,
      from: previous.from || "live",
      version_changed: previous.status === "ok" ? String(previous.state.version || "") !== version : false,
    };
    if (env.LASTMOD_CHANGED) fs.writeFileSync(env.LASTMOD_CHANGED, JSON.stringify(summary) + "\n");
    // the store last: written only when everything before it went through — and never after an unreadable one
    // (the next run then compares with the last good store again)
    if (previous.status !== "error") fs.writeFileSync(path.join(out, STATE_FILE), stateText({ version, built: now, pages }));
    const n = Object.keys(pages).length;
    const where = previous.from === "store" ? "the last publish" : "the live site";
    if (previous.status === "ok") {
      const left = changed.length - datedNow;
      say(deps, `${datedNow} of ${n} sitemap page(s) changed since ${where} — dated ${now}; ` +
        `the other ${n - datedNow} keep their dates${left > 0 ? `; ${left} left the sitemap` : ""}`);
    } else if (previous.status === "missing") {
      say(deps, `no ${STATE_FILE} published yet (${previous.why}): all ${n} sitemap pages are dated ${now} this once; ` +
        "from the next publish on, only the pages that change get a new date", "notice");
    } else {
      say(deps, `the ${STATE_FILE} of the last publish could not be read (${previous.why}): no page gets a date this ` +
        "time and none is sent to IndexNow; the next run compares with the last good one again", "warning");
    }
    return summary;
  } catch (e) {
    // the sitemap as the build wrote it, without any <lastmod>; no IndexNow list; the live store again as it was
    // (or none, when it could not be read: the next run then starts afresh)
    try { if (sitemap && sitemap.outputPath && typeof sitemap.content === "string") fs.writeFileSync(sitemap.outputPath, sitemap.content); } catch { /* as it is */ }
    try { if (env.LASTMOD_CHANGED) fs.rmSync(env.LASTMOD_CHANGED, { force: true }); } catch { /* none */ }
    try {
      const file = path.join(out, STATE_FILE);
      if (previous && previous.status === "ok") fs.writeFileSync(file, stateText(previous.state));
      else fs.rmSync(file, { force: true });
    } catch { /* as it is */ }
    say(deps, `skipped — ${(e && e.message) || e}; the sitemap has no <lastmod> this time` +
      (previous && previous.status === "ok" ? ` (the live ${STATE_FILE} is published again unchanged)` : ""), "warning");
    return null;
  }
}
