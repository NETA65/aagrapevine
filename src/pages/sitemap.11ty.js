// /sitemap.xml — every HTML page in both languages, each with hreflang
// alternates (en / es / x-default) so search engines pair the translations.
// Built from collections.all, so new pages are picked up automatically.
// A page opts out with `sitemap: false` in its front matter; a page marked `noindex: true` (the layout tells search
// engines not to index it) is left out too — a sitemap lists only pages meant to be found.
// <lastmod> is added after the build by eleventy/lastmod.js, and only in Website update's builds: each page's own
// date — when its content last changed (a fingerprint of its title, description and <main>, compared with the live
// site's /lastmod.json) — never the build's date (the site is built several times a day, and search engines learn
// to ignore a date that always moves). No <changefreq> (Google and Bing ignore it); <priority> stays (ignored too,
// harmless). Every page this lists is checked after the build — built, its own canonical, indexable, with a title and
// a description — by eleventy/seo-check.js ([seo] build warnings).
// Pages that must always be listed (both languages) are checked at build time: if one is
// missing (renamed, excluded by mistake) the build log says so — a build warning (eleventy/build-warnings.js:
// the Code check fails on it). Not checked in ONLY= dev builds.
// /offline/ ("Saved pages & app") holds the steps the committee sends to install the site on a phone.
// The events' own pages (since round 37 every event has one: one plan for all of them, eleventy/event-pages.js
// eventPagePlan) are in the collections like any page when search engines may list them, so each is listed with its
// twin: an event still to come (src/pages/event-share-leaf.njk — with its Event markup for the leaves, eventLeaf),
// a monthly series' page (/events/series/<key>/, event-share-series.njk) and a cancelled event's notice while its day
// is to come (event-share-cancelled.njk). The rest — each date of a monthly series, an event from Grapevine's or La
// Viña's own calendar, an event that is over — are noindex pages out of the collections (event-share-date.njk), so an
// event leaves the list by itself once it is over. (Until round 37 only the leaves had a page; every other event's
// address was a small noindex page that sent people on to its card, src/pages/event-share.11ty.js, now gone.)
import { buildWarning } from "../../eleventy/build-warnings.js";

const REQUIRED = ["/", "/whats-new/", "/published/", "/read/", "/monthly/", "/digest/", "/offline/"];

export const data = {
  permalink: "/sitemap.xml",
  eleventyExcludeFromCollections: true,
  layout: false,
};

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function render(data) {
  const base = String(data.site?.url || "").replace(/\/$/, "");
  const abs = (u) => base + u;

  // Collect HTML page URLs (skip feeds, JSON, .ics, 404, opted-out and noindex pages).
  // Eleventy only puts the FIRST page of a paginated template in collections
  // (our pages paginate over languages), so also add every pagination href.
  const urls = new Set();
  const isPage = (u) => typeof u === "string" && (u.endsWith("/") || u.endsWith(".html")) && !/\/404(\.html)?$/.test(u);
  for (const p of data.collections?.all || []) {
    if (p.data?.sitemap === false) continue;
    if (p.data?.noindex) continue;
    if (isPage(p.url)) urls.add(p.url);
    for (const h of p.data?.pagination?.hrefs || []) if (isPage(h)) urls.add(h);
  }

  // "/es/x/" ⇄ "/x/"
  const enOf = (u) => (u.startsWith("/es/") ? u.slice(3) : u === "/es" ? "/" : u);
  const esOf = (u) => "/es" + enOf(u);

  if (!process.env.ONLY) {
    const missing = REQUIRED.flatMap((u) => [u, esOf(u)]).filter((u) => !urls.has(u));
    if (missing.length) buildWarning("sitemap", `missing page(s): ${missing.join(", ")}`);
  }

  const isEs = (u) => (u.startsWith("/es/") ? 1 : 0);
  const sorted = [...urls].sort((a, b) => enOf(a).localeCompare(enOf(b)) || isEs(a) - isEs(b));
  const out = ['<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'];
  for (const u of sorted) {
    const en = enOf(u), es = esOf(u);
    const hasEn = urls.has(en), hasEs = urls.has(es);
    const depth = en.split("/").filter(Boolean).length;
    out.push("  <url>");
    out.push(`    <loc>${esc(abs(u))}</loc>`);
    out.push(`    <priority>${en === "/" ? "1.0" : depth <= 1 ? "0.8" : "0.5"}</priority>`);
    if (hasEn && hasEs) {
      out.push(`    <xhtml:link rel="alternate" hreflang="en" href="${esc(abs(en))}"/>`);
      out.push(`    <xhtml:link rel="alternate" hreflang="es" href="${esc(abs(es))}"/>`);
      out.push(`    <xhtml:link rel="alternate" hreflang="x-default" href="${esc(abs(en))}"/>`);
    }
    out.push("  </url>");
  }
  out.push("</urlset>");
  return out.join("\n") + "\n";
}
