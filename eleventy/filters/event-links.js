// Round 37 · where a link to an event goes, on this site — one rule for every place that links to an event: the
// cards of /events/ (their titles) and its "Save the date" card, the home page's "Upcoming events", the monthly
// toolkit's dates (monthly.js dateRow), What's New, the monthly digest and its texts, the RSS feeds (community.js
// hrefOf), the Bulletin's and Photos' "next event", Contribute's next workshops and the district report's upcoming
// events (report.js). Since round 37 every event has a page of its own (eleventy/event-pages.js eventPagePlan — the
// pages a build writes), so a link goes there, never to the event's card on /events/:
//   - an event → its own page, "/events/<anchor>/" ("/es/events/<anchor>/": committee.js eventPageHref);
//   - a date of a monthly series (config/site.yml recurring_events: the CityWide booth's Saturdays, a date the host
//     moved — ev.seriesOf) → its series' page, "/events/series/<key>/" (committee.js seriesPagePath), the page
//     search engines list for it: each date's own page is noindex, and is linked from there (its list of dates);
//   - a committee meeting → "/meetings/#committee-meeting" (COMMITTEE_MEETING_PATH): it has no page of its own;
//   - a cancelled event → its notice page while its day is still to come, then "/events/" (eventPageHref);
//   - an event the build writes no page for (an anchor unfit for an address, met twice …) → its card,
//     "/events/#<anchor>" — once it is over, "/events/".
// Paths without the site's address or path prefix, already in the page's language (never through lurl again: it
// would add a second "/es"); the `url` filter / the base plugin / siteUrl add the rest.
// (The Details button of a card keeps the event's outside page. The calendars' link — committee.js shapeEvent's
// detailsUrl — is the event's own page too, since round 37; the booth's QR codes and the presentations' rows keep
// their old link, shapeEvent's cardUrl: the event's own link, else its card.)
//
//   {{ ev | evHref(lang, db, site) }}           → the address above (ev: a /events/ event — normalizeEvents — or a
//                                                 data item of db.events.items / db.whatsnew.items)
//   {{ ev | evHref(lang, db, site, "page") }}   → the same, but "" when the event has no page: /events/' own cards
//                                                 (a title linking to its own card goes nowhere)
// JavaScript: eventLink(x, lang, plan, { page }) and eventLinkPlan(db, site, langs) — the plan (one per build:
// eventPagePlan is memoized on db.events.items, site.built, site.url and the languages).
import LANGUAGES from "../../src/_data/languages.js";
import { eventPagePlan } from "../event-pages.js";
import { eventPageHref, seriesPagePath, eventCancelled } from "./committee.js";

/** The build's plan of the events' pages (eleventy/event-pages.js eventPagePlan) from the `db` and `site` globals:
 *  db.events.items and db.events.cancelled, in the site's languages (src/_data/languages.js) — the same plan the page
 *  templates paginate over, worked out once. */
export function eventLinkPlan(db, site, langs = LANGUAGES) {
  const events = (db && db.events) || {};
  return eventPagePlan(events.items, site || {}, langs, { cancelled: events.cancelled });
}

// The series an event is a date of — a /events/ event's (ev.series of a monthly date, ev.seriesOf of a date the host
// moved) or a data item's (extra.series of a "recurring" item, extra.series_of) —, else "".
function seriesKeyOf(x) {
  if (typeof x.recurring === "boolean" || typeof x.seriesOf === "string") return String((x.recurring ? x.series : x.seriesOf) || "");
  const ex = x.extra || {};
  return String((x.category === "recurring" ? ex.series : ex.series_of) || "");
}

/**
 * Where a link to an event goes (see the top of this file) → a path in `lang`, without the site's address.
 *   x     a /events/ event (normalizeEvents) or a data item (db.events.items, db.whatsnew.items, a monthly toolkit's
 *         date's record)
 *   plan  eventLinkPlan's answer (or eventPagePlan's): the series that have a page (plan.hubKeys) and the events that
 *         have one in this language — without it, a series' date links to its own page and every other event to
 *         "/events/<anchor>/" (committee.js eventPageHref's own rules)
 *   opt   { page: true — "" for an event with no page of its own (its card on /events/, or /events/ itself) }
 */
export function eventLink(x, lang = "en", plan = null, opt = {}) {
  const L = lang || "en";
  const events = eventPageHref(null, L);
  if (!x || typeof x !== "object") return opt && opt.page ? "" : events;
  const p = plan && typeof plan === "object" && plan.byAnchor ? plan : null;
  // (a cancelled date of a series: its notice, as any cancelled event — eventPageHref)
  if (p && !eventCancelled(x)) {
    const key = seriesKeyOf(x);
    if (key && Array.isArray(p.hubKeys) && p.hubKeys.includes(key)) return seriesPagePath(key, L);
  }
  const href = eventPageHref(x, L, p ? { plan: p, now: p.now } : {});
  if (opt && opt.page && (href === events || href.startsWith(events + "#"))) return "";
  return href;
}

export default function (eleventyConfig) {
  // {{ ev | evHref(lang, db, site) }} · {{ ev | evHref(lang, db, site, "page") }} — see the top of this file
  eleventyConfig.addFilter("evHref", (x, lang, db, site, mode) =>
    eventLink(x, lang, db && site ? eventLinkPlan(db, site) : null, { page: mode === "page" }));
}
