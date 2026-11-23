// /search-index.json and /es/search-index.json — everything on the site for the
// /search/ page (and nothing private: only what the site already shows).
// Entry fields: id, k (kind: page|section|month|presentation|issue|flyer|article|topic|pdf|document|slides|form|
//   episode|video|post|album|announcement|event|meeting), t (title in page language),
//   o (other/original-language title), s (snippet), x (extra keywords), u (URL —
//   internal URLs start with "/" and already carry the /es prefix), u2 (a second link: an episode's
//   page at its podcast host, a presentation's "Start the presentation"), d (YYYY-MM-DD),
//   dp ("m" = only the month is known), l (content language),
//   src (gv|lv|neta|podcast|youtube|site), im (image), yt (YouTube id → thumbnail),
//   ic (icon for site pages, sections and meetings), m (machine-translated), n (new),
//   pw (subscriber story), z (de-emphasized: PDF no longer linked, past or cancelled event, a past event's flyer),
//   tb (an upcoming event whose details are to be confirmed — content/events `tentative: true`),
//   lw (ranked lower: a year of magazine covers, whose keywords name every month),
//   a (a story's byline: writer · hometown, e.g. "Victor R. · Grand Prairie, Texas" —
//   searched and shown under the result). The Published Writers page entry is also
//   found by the names, cities and counties of the Texas writers it spotlights.
// Since round 37 (eleventy/filters/library.js searchIndex): an event links its own page, a monthly series its
// series' page (/events/series/<key>/, once built), an upcoming cancelled event its notice ("Cancelled: …", z); and the long
// pages' sections (eleventy/search-sections.js), the month toolkits, the presentations, the current issues, the
// Drive's flyers, the shop's offers and the next committee meeting have entries of their own. The build checks
// the result (eleventy/seo-check.js searchProblems, "[search]" warnings): every page the sitemap lists is found,
// every #anchor exists, each file stays under 1,400,000 bytes.
// Built by the searchIndexJson filter in eleventy/filters/library.js.
export default class SearchIndex {
  data() {
    return {
      pagination: { data: "languages", size: 1, alias: "lang" },
      permalink: (data) => (data.lang === "en" ? "/search-index.json" : `/${data.lang}/search-index.json`),
      eleventyExcludeFromCollections: true,
      layout: null,
    };
  }

  render(data) {
    // (the presentations: the `presentations` global, src/_data/presentations.js — search.njk hands over the same)
    return this.searchIndexJson(data.db, data.nav, data.lang, data.site, data.presentations);
  }
}
