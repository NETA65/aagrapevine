// The [seo] check: once the pages are written (eleventy.config.js, "eleventy.after"), the build reads what search
// engines read — /sitemap.xml and the head of every page — and makes each problem a build warning
// (eleventy/build-warnings.js: the Code check's strict build fails on it; Website update only lists it):
//   * every page the sitemap lists is built, is its own canonical (<link rel="canonical"> = its <loc>), may be
//     indexed (no robots "noindex") and has a <title> and a meta description;
//   * no two pages the sitemap lists IN ONE LANGUAGE share a <title> (an English page and its Spanish twin may:
//     /instagram/ and /es/instagram/ are both "Instagram");
//   * every page that names itself as its canonical and may be indexed is in the sitemap (a new page whose
//     front matter left it out by mistake) — a page meant to stay out says `noindex: true` (or is a redirect or
//     share page with a canonical elsewhere).
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

/** The "eleventy.after" hook: each problem → buildWarning("seo", …). Synchronous, so it is registered before the
    build's summing-up (finishBuild) and its warnings count. → the problems ([] when skipped). */
export function seoCheck({ results, outputMode, incremental } = {}, env = process.env) {
  if (env.ONLY || incremental || (outputMode && outputMode !== "fs")) return [];
  const problems = seoProblems(results, siteAddress(env));
  for (const p of problems) buildWarning("seo", p);
  return problems;
}
