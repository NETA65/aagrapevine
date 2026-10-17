// "Add this month's dates to my calendar": one calendar file per month page, beside the page that links it
// (monthly-month.njk, the Dates card) — /monthly/YYYY-MM/neta65-grapevine-YYYY-MM-en.ics and the Spanish
// /es/monthly/YYYY-MM/neta65-grapevine-YYYY-MM-es.ics (eleventy/filters/monthly.js icsPath). Written at build time
// from the month's model (monthIcs): the month's dates as /events.ics writes them (same UIDs) and its story deadlines
// as all-day entries. A static file: the link works without JavaScript and opens straight in a phone's calendar.
// Not a page: out of the collections, so out of the sitemap, the feeds and the search index.
import { icsPath } from "../../eleventy/filters/monthly.js";

export const data = {
  pagination: { data: "monthlyPages", size: 1, alias: "mpage" },
  permalink: (data) => icsPath(data.mpage.key, data.mpage.lang),
  eleventyExcludeFromCollections: true,
  layout: null,
};

export function render(data) {
  const { mpage, db, carry, site } = data;
  return this.mpIcs(mpage.key, db, carry, site, mpage.lang);
}
