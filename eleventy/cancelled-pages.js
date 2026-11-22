// The notice pages of the cancelled events (since round 37): src/pages/event-share-cancelled.njk paginates over
// cancelledPages(db.events.cancelled, db.events.items, site, languages). A module of its own — not in eleventy/filters/
// (every file there is loaded as a plugin) and not in the template's front matter (whose top-level names all become
// page data, merged deep into every page).
import { normalizeEvents, eventLd, eventLeaf, eventPagePath, cancelledPageMeta, withoutJoinDetails, EVENT_PAGE_ANCHOR } from "./filters/committee.js";
import { eventTone } from "./filters/event-tone.js";

const RELATED_MAX = 3;
const tagsOf = (ev) => new Set((Array.isArray(ev.item?.tags) ? ev.item.tags : []).map((t) => String(t).trim().toLowerCase()).filter(Boolean));

/**
 * The notice pages: one per cancelled event (db.events.cancelled — src/_data/db.js, eleventy/cancelled-events.js;
 * content/events `cancelled: true`) and language whose day is not over at the build's own moment (site.built, as the
 * event pages read it) → [{ lang, ev, path, target, ld, meta, note, related }]. Its address is the one its page had
 * (committee.js eventPagePath: /events/<anchor>/), so a link shared before still works — but never one an event of
 * the lists has (the event pages write those, src/pages/event-share*.11ty.js / .njk: no address is written twice); an
 * anchor not fit for an address, or met twice, gets none. In every language alike (each page has its twin):
 *   target   where "See all events" goes: /events/ (the event has no card there any more);
 *   ld       its Event, EventCancelled (committee.js eventLd) — only when it was to be held at a place with a real
 *            address in every language, as for every event page;
 *   meta     its title, description and words (committee.js cancelledPageMeta);
 *   note     its summary without how to join (withoutJoinDetails);
 *   related  up to RELATED_MAX events still to come of the same kind — the same colour (eventTone) and a tag in
 *            common (a La Viña workshop: the next La Viña workshops and events) —, a monthly series by its next date
 *            only, soonest first: { ev, tone, href } — its own page (eventLeaf), else its card on /events/.
 * Once its day is over, the next build writes no page: the address is a 404 again, which sends people on to /events/
 * (src/assets/js/community.js), and it leaves the sitemap. The calendar feeds keep its STATUS:CANCELLED entry 90 days.
 * COMMITTEE_EMPTY builds: none.
 */
export function cancelledPages(cancelled, items, site, langs) {
  const ls = Array.isArray(langs) && langs.length ? langs : ["en", "es"];
  const built = Date.parse(String(site?.built || ""));
  const now = Number.isFinite(built) ? new Date(built) : new Date();
  const out = [];
  if (process.env.COMMITTEE_EMPTY || !(cancelled || []).length) return out;
  for (const lang of ls) {
    const listed = normalizeEvents(items || [], site, lang, { now }).filter((e) => !e.committee);
    const taken = new Set(listed.map((e) => e.anchor));
    const events = lang === "en" ? "/events/" : `/${lang}/events/`;
    const seen = new Set();
    for (const ev of normalizeEvents(cancelled, site, lang, { now })) {
      if (!ev.cancelled || ev.committee || ev.past || ev.endMs <= now.getTime()) continue;
      if (!EVENT_PAGE_ANCHOR.test(ev.anchor || "") || taken.has(ev.anchor) || seen.has(ev.anchor)) continue;
      seen.add(ev.anchor);
      const path = eventPagePath(ev, lang);
      const abs = String(site?.url || "").replace(/\/+$/, "") + path;
      const tone = eventTone(ev), tags = tagsOf(ev);
      const series = new Set();
      const related = listed.filter((e) => {
        if (e.past || e.cancelled || e.anchor === ev.anchor || eventTone(e) !== tone) return false;
        if (![...tagsOf(e)].some((t) => tags.has(t))) return false;
        if (e.recurring && e.series) {
          if (series.has(e.series)) return false;
          series.add(e.series);
        }
        return true;
      }).slice(0, RELATED_MAX).map((e) => ({ ev: e, tone: eventTone(e),
        href: eventLeaf(e, site, ls) ? eventPagePath(e, lang) : `${events}#${e.anchor}` }));
      out.push({ lang, ev, path, target: events, ld: eventLd([ev], site, lang, abs, 1, { url: abs }).length > 0,
                 meta: cancelledPageMeta(ev, site, lang), note: withoutJoinDetails(ev.summary), related });
    }
  }
  // in every language alike: a page only when every language has one; its Event only when every language has it
  const all = new Map();
  for (const s of out) all.set(s.ev.anchor, [...(all.get(s.ev.anchor) || []), s]);
  return out.filter((s) => {
    const list = all.get(s.ev.anchor);
    s.ld = list.every((x) => x.ld);
    return list.length === ls.length;
  });
}
