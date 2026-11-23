// The [seo] check: once the pages are written (eleventy.config.js, "eleventy.after"), the build reads what search
// engines read — /sitemap.xml and the head of every page — and makes each problem a build warning
// (eleventy/build-warnings.js: the Code check's strict build fails on it; Website update only lists it):
//   * every page the sitemap lists is built, is its own canonical (<link rel="canonical"> = its <loc>), may be
//     indexed (no robots "noindex") and has a <title> and a meta description;
//   * no two pages the sitemap lists IN ONE LANGUAGE share a <title> (an English page and its Spanish twin may:
//     /instagram/ and /es/instagram/ are both "Instagram");
//   * every page that names itself as its canonical and may be indexed is in the sitemap (a new page whose
//     front matter left it out by mistake) — a page meant to stay out says `noindex: true` (as the events' noindex
//     pages do, src/pages/event-share-date.njk) or is a redirect with a canonical elsewhere;
//   * (since round 35) no page the sitemap lists is over 1.8 MB of HTML (PAGE_LIMIT, counted in UTF-8 bytes as the
//     file is sent, uncompressed): Googlebot reads only the first 2 MB of a page — "any bytes that exist after that
//     2MB threshold are entirely ignored" (Google Search Central, "Inside Googlebot", March 31, 2026) — so the
//     check speaks well before anything is lost. /photos/ (1.5 MB in November 2026) grows with every cover album,
//     /events/ with every event. And ALL of a page's structured data (<script type="application/ld+json">: since
//     round 35 the site-wide graph at the end of the <head>, base.njk, then a page's own block first in its
//     <body> — the Events of /events/ and of an event's own page) ends within the first 1.5 MB (LD_LIMIT): the
//     check measures where the page's LAST block ends, so it speaks when any one block drifts down the page;
//   * (since round 35) config/site.yml search_engines.ai_training is "allow" or "disallow" (src/robots.njk): any
//     other value counts as "allow", and this says so (aiTrainingProblem);
//   * (since round 37, "[search]" warnings) the site's own search finds every page the sitemap lists, its links lead
//     to pages and #anchors that exist, and each language's index stays under its size budget (searchProblems).
// Never the lengths of titles and descriptions: what fits in a result changes with the engine and the screen, and
// a long one is a choice of words, not a fault. Not in a dev build of some pages (ONLY=), a `npm start` rebuild
// (incremental) or a build that writes no files (the tests' toJSON builds): a partial site would be all problems.
// The address the pages are checked against is site.url as the pages get it (src/_data/site.js: SITE_URL on
// GitHub, else config/site.yml site.url).
import fs from "node:fs";
import * as yaml from "js-yaml";
import { buildWarning } from "./build-warnings.js";

/** The site's public address without its last slash ("https://neta65.github.io/aagrapevine"), as src/_data/site.js
    works it out; "" when there is none. */
export function siteAddress(env = process.env, configFile = "config/site.yml") {
  let url = env.SITE_URL || "";
  if (!url) {
    try { url = ((yaml.load(fs.readFileSync(configFile, "utf8")) || {}).site || {}).url || ""; } catch { url = ""; }
  }
  return String(url).replace(/\/+$/, "");
}

const ENTITIES = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&#x27;": "'" };
/** HTML text → plain text (the few entities the templates write). */
export const unescapeHtml = (s) => String(s ?? "").replace(/&(?:amp|lt|gt|quot|#39|#x27);/g, (e) => ENTITIES[e]);

/** What search engines read in a page's head: { title, description, canonical, noindex } ("" when missing). */
export function pageFacts(html) {
  const text = String(html ?? "");
  const end = text.indexOf("</head>");
  const head = end < 0 ? text : text.slice(0, end);
  const title = /<title>([\s\S]*?)<\/title>/i.exec(head);
  const desc = /<meta\s+name="description"\s+content="([^"]*)"/i.exec(head);
  const canon = /<link\s+rel="canonical"\s+href="([^"]*)"/i.exec(head);
  // "noindex" or "none" in a robots meta (any robot: robots, googlebot, bingbot …)
  const noindex = [...head.matchAll(/<meta\s+name="(?:robots|googlebot|bingbot)"\s+content="([^"]*)"/gi)]
    .some((m) => /\b(?:noindex|none)\b/i.test(m[1]));
  return {
    title: title ? unescapeHtml(title[1]).replace(/\s+/g, " ").trim() : "",
    description: desc ? unescapeHtml(desc[1]).trim() : "",
    canonical: canon ? unescapeHtml(canon[1]).trim() : "",
    noindex,
  };
}

/** The <loc> addresses of a sitemap, in order (plain text). */
export const sitemapLocs = (xml) => [...String(xml ?? "").matchAll(/<loc>([^<]*)<\/loc>/g)].map((m) => unescapeHtml(m[1]).trim());

/** A <loc> on the site → its page's path ("/about/"), or null for an address that is not under `base`. */
export function pathOf(loc, base) {
  if (!loc.startsWith(base + "/")) return null;
  return loc.slice(base.length);
}

const langOf = (p) => (p === "/es/" || p.startsWith("/es/") ? "es" : "en");

/** The largest page the check lets pass: 1.8 MB (1,887,437 bytes) — Googlebot reads the first 2 MB (2,097,152). */
export const PAGE_LIMIT = Math.ceil(1.8 * 1024 * 1024);
/** The byte by which all of a page's structured data must have ended: 1.5 MB (1,572,864 bytes). */
export const LD_LIMIT = 1.5 * 1024 * 1024;
const MB = (bytes) => `${(bytes / 1048576).toFixed(1)} MB`;
const LD_START = '<script type="application/ld+json"';

/** A page's size problems (see the header): its HTML over PAGE_LIMIT, the end of its last ld+json block past
    LD_LIMIT, in UTF-8 bytes — each the rest of a problem's text after the page's path (" is 1.9 MB of HTML …",
    ": its structured data …"). → [] when it is fine. */
export function sizeProblems(html) {
  const text = String(html ?? "");
  const out = [];
  const bytes = Buffer.byteLength(text, "utf8");
  if (bytes > PAGE_LIMIT) {
    // (the byte count says how far over: "1.8 MB" alone can be just over the limit, 1,887,438 bytes)
    out.push(` is ${MB(bytes)} of HTML (${bytes.toLocaleString("en-US")} bytes), over the 1.8 MB limit — Googlebot reads only the first 2 MB of a page`);
  }
  // the LAST block ends last: one check covers every block (the head's graph, a page's own block in its body)
  const at = text.lastIndexOf(LD_START);
  if (at >= 0) {
    const close = text.indexOf("</script>", at);
    const end = Buffer.byteLength(text.slice(0, close < 0 ? text.length : close + "</script>".length), "utf8");
    if (end > LD_LIMIT) {
      out.push(`: its structured data (ld+json) ends at ${MB(end)} (byte ${end.toLocaleString("en-US")}) — keep all of it within the first 1.5 MB, where Googlebot surely reads it`);
    }
  }
  return out;
}

/** config/site.yml search_engines.ai_training (src/robots.njk): "" when it is "allow", "disallow", empty or left
    out; else the problem's text (the value then counts as "allow"). Read as robots.njk reads it: trimmed, any
    capitals. */
export function aiTrainingProblem(value) {
  if (value === undefined || value === null) return "";
  const v = String(value).trim().toLowerCase();
  if (v === "" || v === "allow" || v === "disallow") return "";
  return `config/site.yml search_engines.ai_training is "${String(value)}" — write "allow" or "disallow" (robots.txt allows AI training until then)`;
}

/** search_engines.ai_training as written in config/site.yml (undefined when it is left out or the file is unreadable). */
export function aiTrainingSetting(configFile = "config/site.yml") {
  try {
    const se = ((yaml.load(fs.readFileSync(configFile, "utf8")) || {}).site || {}).search_engines;
    return se && typeof se === "object" ? se.ai_training : undefined;
  } catch {
    return undefined;
  }
}

/** The problems of a built site: `results` = Eleventy's [{ url, outputPath, content }] (the "eleventy.after" event's,
    or toJSON()'s), `base` = the site's address. → ["/x/: …", …] in the order found (none: []). */
export function seoProblems(results, base) {
  const all = Array.isArray(results) ? results : [];
  const sitemap = all.find((r) => r && r.url === "/sitemap.xml");
  if (!sitemap) return [];
  const pages = new Map();
  for (const r of all) {
    if (r && typeof r.url === "string" && typeof r.content === "string" && /\.html$/.test(String(r.outputPath || ""))) pages.set(r.url, r);
  }
  const problems = [];
  const listed = new Set();
  const titles = new Map(); // "en\u0000title" → the first page with it
  for (const loc of sitemapLocs(sitemap.content)) {
    const p = pathOf(loc, base);
    if (p === null) { problems.push(`the sitemap lists ${loc}, which is not under the site's address ${base}/`); continue; }
    listed.add(p);
    const page = pages.get(p);
    if (!page) { problems.push(`${p}: in the sitemap but not built`); continue; }
    const f = pageFacts(page.content);
    if (f.canonical !== loc) problems.push(`${p}: its canonical is ${f.canonical ? `"${f.canonical}"` : "missing"} — the sitemap lists "${loc}"`);
    if (f.noindex) problems.push(`${p}: in the sitemap but marked noindex`);
    if (!f.title) problems.push(`${p}: no <title>`);
    if (!f.description) problems.push(`${p}: no meta description`);
    for (const s of sizeProblems(page.content)) problems.push(p + s);
    if (f.title) {
      const key = langOf(p) + "\u0000" + f.title;
      if (titles.has(key)) problems.push(`${p}: the same <title> as ${titles.get(key)} ("${f.title}")`);
      else titles.set(key, p);
    }
  }
  for (const [p, page] of pages) {
    if (listed.has(p)) continue;
    const f = pageFacts(page.content);
    if (!f.noindex && f.canonical && f.canonical === base + p) {
      problems.push(`${p}: may be indexed (its own canonical, no noindex) but is not in the sitemap — list it, or give it noindex: true`);
    }
  }
  return problems;
}

/** The largest /search-index.json (each language's) the check lets pass, in bytes as written (uncompressed): 1,600,000.
    About 0.9 MB in November 2026 (≈ 200 KB compressed); since round 37's fixer the Texas writers archive's stories too
    (library.js "writers archive": ~1,250 lean entries) — 1.2 MB in English, 1.3 MB in Spanish (≈ 265 / 285 KB
    compressed), so ~300 KB of room for what the site adds each week. /search/ downloads the whole file before its first
    result, so the check speaks well before a phone on a slow connection waits too long for it (search.js HEAD_TIMEOUT). */
export const SEARCH_LIMIT = 1600000;

/**
 * Since round 37, the [search] problems of a built site: what the site search (/search/: /search-index.json and
 * /es/search-index.json, eleventy/filters/library.js searchIndex) can reach — `results` and `base` as seoProblems' →
 * ["…", …] in the order found (none: []):
 *   * every page the sitemap lists is FOUND: an entry of its language's index links it — its `u` once ?… and #… are
 *     taken off (the paths of both are the site's own, without its address or path prefix: an entry's /es/… path is
 *     the Spanish index's, a <loc> under `base` is read as seoProblems reads it);
 *   * every link of an entry to one of our pages (`u`, `u2`: a path ending in "/") is a page of the build, and its
 *     #anchor an id on that page (a section renamed or removed: eleventy/search-sections.js) — a file's path (no page,
 *     a passthrough copy the results do not list) is not looked at;
 *   * each index is at most SEARCH_LIMIT bytes.
 * A monthly series' page (/events/series/<key>/) is checked like any other: the search links one only once the build
 * writes it (library.js, collections.all), so a link to one that is missing — or one the sitemap lists that no entry
 * links (its template left out of the collections) — is a problem like any other.
 */
export function searchProblems(results, base) {
  const all = Array.isArray(results) ? results : [];
  const sitemap = all.find((r) => r && r.url === "/sitemap.xml");
  const indexes = all.filter((r) => r && typeof r.url === "string" && /^\/(?:[a-z]{2}\/)?search-index\.json$/.test(r.url) && typeof r.content === "string");
  if (!sitemap || !indexes.length) return [];
  const pages = new Map();
  for (const r of all) {
    if (r && typeof r.url === "string" && typeof r.content === "string" && /\.html$/.test(String(r.outputPath || ""))) pages.set(r.url, r);
  }
  const idCache = new Map();
  const idsOf = (url) => {
    if (!idCache.has(url)) idCache.set(url, new Set([...pages.get(url).content.matchAll(/\sid="([^"]+)"/g)].map((m) => unescapeHtml(m[1]))));
    return idCache.get(url);
  };
  const locs = sitemapLocs(sitemap.content).map((loc) => pathOf(loc, base)).filter((p) => p !== null);
  const problems = [];
  for (const idx of indexes) {
    const lang = langOf(idx.url);
    const bytes = Buffer.byteLength(idx.content, "utf8");
    if (bytes > SEARCH_LIMIT) {
      problems.push(`${idx.url} is ${bytes.toLocaleString("en-US")} bytes, over its ${SEARCH_LIMIT.toLocaleString("en-US")}-byte budget — /search/ downloads it whole before its first result (eleventy/seo-check.js SEARCH_LIMIT)`);
    }
    let items = [];
    try { items = JSON.parse(idx.content).items || []; } catch { problems.push(`${idx.url}: not valid JSON`); continue; }
    const found = new Set();
    for (const e of Array.isArray(items) ? items : []) {
      for (const link of [e && e.u, e && e.u2]) {
        if (typeof link !== "string" || !/^\/(?!\/)/.test(link)) continue;
        const path = link.replace(/[?#].*$/, "");
        found.add(path);
        if (!path.endsWith("/")) continue;
        const hash = (/#(.+)$/.exec(link) || [])[1] || "";
        if (!pages.has(path)) {
          problems.push(`${idx.url}: "${e.t}" (${e.id}) links ${link}, a page the build has not written`);
          continue;
        }
        let id = hash;
        try { id = decodeURIComponent(hash); } catch { /* as written */ }
        if (hash && !idsOf(path).has(id)) problems.push(`${idx.url}: "${e.t}" (${e.id}) links ${link}, but ${path} has no id="${id}"`);
      }
    }
    for (const p of locs) {
      if (langOf(p) === lang && !found.has(p)) problems.push(`${p}: in the sitemap, but no entry of ${idx.url} links it — the site search cannot find it`);
    }
  }
  return problems;
}

/** The "eleventy.after" hook: each problem → buildWarning("seo", …), and since round 37 each of the site search's
    (searchProblems) → buildWarning("search", …). Synchronous, so it is registered before the build's summing-up
    (finishBuild) and its warnings count. → the problems ([] when skipped). */
export function seoCheck({ results, outputMode, incremental } = {}, env = process.env, configFile = "config/site.yml") {
  if (env.ONLY || incremental || (outputMode && outputMode !== "fs")) return [];
  const base = siteAddress(env, configFile);
  const problems = seoProblems(results, base);
  // (the robots.txt setting: once per build, beside the pages' problems)
  const ai = aiTrainingProblem(aiTrainingSetting(configFile));
  if (ai) problems.push(ai);
  for (const p of problems) buildWarning("seo", p);
  const search = searchProblems(results, base);
  for (const p of search) buildWarning("search", p);
  return [...problems, ...search];
}
