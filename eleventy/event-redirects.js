// The old addresses of the events' pages (since the events list's redesign, November 2026): an event made from a dated
// Drive flyer or taken from an outside calendar had its page at /events/ev-flyer-<its Drive id>/ or
// /events/ev-lvcal-<a hash>/ (committee.js eventAnchor: "ev-" and its id, without a slug of its own); the sync now
// gives it a readable one — its day and title, pinned (scripts/sync/build_data.py pin_event_slugs) —, and a day that
// changes makes a new one, keeping the old in extra.slug_aliases. src/pages/event-share-redirect.njk writes a small page
// at each such old address that sends the visitor on to the page the event has now, in each language.
// Worked out from the records alone, never from the event pages' plan: a pagination's `before` sees the data before
// the computed `site` (a test's own recurring_events), and the plan is memoized for the whole build.
// (A module of its own, not in eleventy/filters/ — every file there is loaded as a plugin — as eleventy/cancelled-pages.js.)
import { eventAnchor, eventPagePath, eventCancelled, eventEndMs, slugify, tidyBrackets, EVENT_PAGE_ANCHOR } from "./filters/committee.js";

const OWN_ADDRESS = new Set(["manual", "recurring", "committee"]);

/** An events.json record's old anchors: "ev-<its id>" (eventAnchor without a slug) and its extra.slug_aliases — never
 *  its anchor now; [] for an event that keeps its address (a content/events file, a monthly date, a committee meeting). */
export function oldAnchors(it) {
  if (!it || typeof it !== "object" || OWN_ADDRESS.has(it.category)) return [];
  const x = it.extra || {};
  const now = eventAnchor(it);
  const legacy = "ev-" + slugify(String(it.id || "").replace(/^ev:/, ""));
  const aliases = Array.isArray(x.slug_aliases) ? x.slug_aliases.map(String) : [];
  return [...new Set([legacy, ...aliases])].filter((a) => a && a !== now && EVENT_PAGE_ANCHOR.test(a));
}

/**
 * The redirect pages → [{ lang, path ("/[es/]events/<old anchor>/"), target (the event's page now: "/[es/]events/
 * <its anchor>/" — its own page, or the notice of a cancelled event still to come), title (its title in that
 * language, as its page writes it: without the spaces a calendar left inside its brackets — tidyBrackets, "… ( A.A.
 * Un camino a la vida )" → "… (A.A. Un camino a la vida)", since round 38b) }]: for every event of events.json (items
 * and cancelled) with an old address, but a cancelled one that is over (it has no page any more); never at the
 * address of an event of the file. COMMITTEE_EMPTY builds: none.
 * now: the build's moment (site.built).
 */
export function eventRedirects(items, cancelled, site, langs = ["en", "es"]) {
  const list = [...(Array.isArray(items) ? items : []), ...(Array.isArray(cancelled) ? cancelled : [])]
    .filter((it) => it && typeof it === "object" && it.status !== "gone");
  if (process.env.COMMITTEE_EMPTY) return [];
  const built = Date.parse(String(site?.built || ""));
  const now = Number.isFinite(built) ? built : Date.now();
  const anchors = new Set(list.map(eventAnchor));
  const out = [];
  const seen = new Set();
  for (const it of list) {
    const olds = oldAnchors(it).filter((a) => !anchors.has(a));
    const anchor = eventAnchor(it);
    if (!olds.length || !EVENT_PAGE_ANCHOR.test(anchor)) continue;
    if (eventCancelled(it) && (it.extra?.past === true || (eventEndMs(it) ?? 0) <= now)) continue;
    for (const lang of langs) {
      const title = tidyBrackets(String(it.i18n?.title?.[lang] || it.title || "").replace(/\s+/g, " ").trim());
      for (const a of olds) {
        const path = eventPagePath({ anchor: a }, lang);
        if (seen.has(path)) continue;
        seen.add(path);
        out.push({ lang, path, target: eventPagePath({ anchor }, lang), title });
      }
    }
  }
  return out;
}
