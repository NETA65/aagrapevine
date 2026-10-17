// "Story deadlines in my calendar": /deadlines.ics (English) and /es/deadlines.ics (Spanish) — every open story
// deadline of AA Grapevine and La Viña (data/site/editorial.json: the dated themes /contribute/#deadlines lists; La
// Viña's suggested topics have no date and are not in it), each an all-day entry on its day with one reminder at
// 9 AM the day before. A calendar a member subscribes to once (the card on /contribute/#deadlines-calendar, the
// line on /whats-new/#subscribe): it updates itself when a magazine adds, moves or drops a theme — the same UIDs as
// each month's calendar file (/monthly/YYYY-MM/…ics), so a calendar with both keeps one copy, and a higher SEQUENCE
// in every newer file. RFC 5545 as committee.js buildIcs writes it (CRLF, lines folded at 75 octets, TEXT escaped,
// DATE values). Written by eleventy/filters/monthly.js deadlinesIcs, on the build's clock (nowDate). Not a page: out
// of the collections, so out of the sitemap, the feeds and the search index; the service worker never keeps it
// (network only, like /events.ics).
import { deadlinesIcs, deadlinesIcsPath, nowDate } from "../../eleventy/filters/monthly.js";

export const data = {
  pagination: { data: "languages", size: 1, alias: "lang" },
  permalink: (data) => deadlinesIcsPath(data.lang),
  eleventyExcludeFromCollections: true,
  layout: null,
};

export function render(data) {
  // (READ_EMPTY=1: the build that shows /contribute/ without themes writes an empty calendar too)
  const db = process.env.READ_EMPTY ? {} : data.db || {};
  return deadlinesIcs(db, data.site || {}, data.lang || "en", nowDate());
}
