// Round 37 · the SPINE of the events' own pages: which event gets which page, of what kind, at what address, with
// what title — one answer that the page templates, the links to them, /llms.txt and the site search all read, so
// no two of them ever disagree. Pure functions (no Eleventy registration: this file is not in eleventy/filters/,
// whose files are loaded as plugins and whose filters must all be used — test_unused_code). The templates import it
// in their JavaScript front matter (`import { eventPagePlan } from "./eleventy/event-pages.js"`), as
// src/pages/event-share-leaf.njk imports committee.js.
//
// ============================================================================================== INTERFACE
//
//   EVENT_KINDS                       { [kind]: { family, label, phrase, who, deck, deckMag, deckClose, where,
//                                     flyers, resources, resourceFallback, resourceAnchors } } — the one table of the
//                                     kinds (frozen). label / phrase / who: i18n keys (src/_i18n/evkind.json; who:
//                                     "" when the kind has no "Who can come" line); deck: a presentations.decks id
//                                     ("" none — link it only when presentations.decks has it), deckMag: the deck
//                                     only for that magazine's events ("gv": the Grapevine Meeting deck), deckClose:
//                                     the deck is the closest one, not the kind's own ("The closest presentation");
//                                     where: the bingo card's occasion (bingo-core.js WHERES); flyers: the
//                                     "similar flyers" pattern for driveMatch (a RegExp source, case-insensitive),
//                                     "series" (the series' own config/site.yml flyer_match) or ""; resources: the
//                                     ids of the "Get ready" links, in order (the resource catalogue: the judge's
//                                     spec §4 — evpage.res.<id>); resourceFallback: { id: other id } when the first
//                                     is missing ("official" → "area"); resourceAnchors: { id: [anchors] } when only
//                                     some of a resource's anchors fit ("gvr" → ["job"]).
//   EVENT_KIND_KEYS                   the kinds' names (= Python EVENT_TYPES: content/events `type:`)
//   SERIES_KIND                       { "citywide-dallas": "booth", "grapevine-meeting": "online-meeting",
//                                     "lv-monthly-workshop": "magazine-workshop" }
//   EVENT_TIERS                       { leaf, page, date, cancelled, none } → { index, ld }
//
//   eventKind(ev, site?)              → { kind, family, mag ("lv" | "gv" | "both"), spanish, outside, series (its
//                                     series' key or ""), source (which rule decided: "type" | "series-type" |
//                                     "committee" | "series" | "tag" | "title" | "calendar" | "tone" | "default"),
//                                     label, phrase, who, deck (resolved for the magazine: "" none), deckClose,
//                                     where, flyers (resolved: a pattern or ""), resources, resourceFallback,
//                                     resourceAnchors }. ev: a /events/ event (normalizeEvents) or a data item.
//   eventPageTier(ev, site, langs)    → "leaf" | "page" | "date" | "cancelled" | "none" — in ONE language (the plan
//                                     pairs the languages).
//   bingoHref(ev, kind?, lang)        → "/[es/]gvr/bingo/#lang=…&mag=…&where=…&event=…&date=…", or "" for an event
//                                     that is over or cancelled. ev: a /events/ event (a plan page's ev) — a data
//                                     item gets "" (it does not say whether it is over).
//   eventPagePlan(items, site, langs, { cancelled })
//                                     → { pages, hubs, hubKeys, byAnchor, byPath, cancelledAnchors, langs, now } —
//                                     memoized (the same items array, site.built, site.url, languages and cancelled
//                                     list: one plan for every template of a build).
//     pages[]  { lang, anchor, path ("/[es/]events/<anchor>/"), ev (shaped in that language), tier ("leaf" | "page"
//              | "date", the same in every language), index (indexable, in the sitemap), ld (the page carries its
//              Event's structured data: cmEventPageLd), kind (eventKind), hubKey / hubPath (its series' page, "" when
//              the series has none), target (where "See all events" goes: "/events/#<anchor>", or "/events/" for a
//              series date that is over), titleSuffix ("" — or the words that keep two titles apart), head ({ title,
//              titleTail, description, ogImage }: eventPageHead) }
//              — every event /events/ lists but the committee meetings, an anchor unfit for an address, an anchor
//              met twice and a cancelled event; in each language's date order (normalizeEvents).
//     hubs[]   { lang, key, path ("/[es/]events/series/<key>/"), kind, series (seriesNext's answer, with these next
//              and dates), next (its next date: a shaped event), dates (its next 6 dates in date order: the rule's
//              and those the host moved — ev.seriesOf, a month the rule skips —, never a cancelled one), datePages
//              (each date's page in `pages`, or null), target ("/events/"), index (true), titleSuffix, head
//              (seriesPageMeta) }
//              — one per enabled config/site.yml recurring_events entry whose key is fit for an address and that
//              has a date still to come in the data, in every language. A series date's page lists its series'
//              next dates from its hub (plan.byPath[page.hubPath].dates), not from seriesNext: a moved date is
//              among them.
//     hubKeys  the hubs' keys, in config/site.yml's order
//     byAnchor { [anchor]: { [lang]: page } }        byPath { [path]: page | hub }
//     cancelledAnchors  the anchors kept out (cancelled events: opt.cancelled — db.events.cancelled — and any item
//              that says cancelled itself): their notice pages are src/pages/event-share-cancelled.njk's
//   eventPageHead(pageOrHub, site)    → { title, titleTail, description (≤ 160), ogImage }: committee.js
//                                     eventPageMeta for an event, seriesPageMeta for a hub, the title with its
//                                     titleSuffix.
//   relatedEvents(planOrList, page, { sameKind, n, past, site, lang })
//                                     → [pages]: the next `n` (3) upcoming events — of the page's kind (sameKind),
//                                     or of any kind —, or (past) the last `n` that are over, newest first. Never the
//                                     page's own event, a date of its own series, a committee meeting or a cancelled
//                                     event; one date per series. planOrList: a plan (its pages in the page's
//                                     language), a list of plan pages, or a list of /events/ events. page: a plan's
//                                     page or hub (its .lang), or a /events/ event — one of the plan's own (p.ev), or
//                                     any with opt.lang; a list of pages in several languages and no language known
//                                     for the page is a mistake of the caller's: it throws.
//
// From eleventy/filters/committee.js (round 37 too): seriesPagePath(key, lang), eventPageHref(x, lang, { now, plan
// }), seriesPageMeta(hub, site, lang), eventOrganizer(ev, site, lang), isCommitteeOrganizer(org, site),
// heldInSpanish(ev), eventCancelled(x), withoutJoinValues(text, values) (a text without the sentences that give a
// meeting's own ID, code or link — for any other copy made for machines: /llms.txt, the search).
//
// Use (a pagination template's front matter — every template of one tier, so the sitemap reads it whole):
//   const plan = (full) => eventPagePlan(full.db.events.items, full.site, full.languages,
//     { cancelled: full.db.events.cancelled });
//   pagination: { data: "db.events.items", size: 1, alias: "share", before: (items, full) => plan(full).pages
//     .filter((p) => p.index) }                    (the noindex template: !p.index; the series' pages: .hubs)
//   eleventyComputed: { title: (d) => d.share.head.title, description: (d) => d.share.head.description, … }
// Pass full.db.events.items, not the `items` the pagination hands `before`: Eleventy gives each template its own
// copy of those (checked with Eleventy 3.1), while full.db.events.items is one array for every template — the memo
// keys on it (a copy is another plan, worked out again: about half a second each).
// ==========================================================================================================
//
// Which page (the judge's spec §3; `now` is site.built, one moment for every template of the build):
//   leaf       an upcoming one-off event that eventLeaf takes (a place with a real address in every language, no
//              page elsewhere …): indexable, with its Event's structured data — a tentative one too (content/events
//              `tentative: true`), as before round 37: EventScheduled (schema.org has no "to be confirmed" status;
//              its page says "Details to be confirmed");
//   page       any other upcoming one-off event (a place to be announced, online only, its own page on neta65.org,
//              an address in one language only …): indexable, no Event markup;
//   date       a date of a monthly series (ev.recurring, or a date the host moved: ev.seriesOf), an event from
//              Grapevine's or La Viña's own calendar, and any event that is over (while events.json keeps it): a
//              page all the same, noindex and out of the sitemap — many near-copies, or theirs to describe;
//   cancelled  a cancelled event still to come: its notice page (indexable; U1's template) — never in `pages`;
//   none       a committee meeting (its page is /meetings/#committee-meeting), an anchor unfit for an address, a
//              cancelled event that is over: no page.
// A page is indexable, or has its Event, only when it is so in EVERY language (its twin by hreflang): an anchor that
// one language's list lacks is a "date" page in the others.

import {
  normalizeEvents, eventLeaf, eventPagePath, eventPageMeta, eventAnchor, eventHost, eventPlace, seriesNext,
  seriesPagePath, seriesPageMeta, eventsTitleTail, heldInSpanish, eventCancelled, tidyBrackets, withoutJoinValues, EVENT_PAGE_ANCHOR,
} from "./filters/committee.js";
import { eventTone, titlesOf, areaOrientation } from "./filters/event-tone.js";

const EMPTY = !!process.env.COMMITTEE_EMPTY;

/* ------------------------------------------------------------------ */
/*  Kinds                                                              */
/* ------------------------------------------------------------------ */
// (the i18n keys written out in full: test_unused_code counts a key as read when the code names it)
const AREA_RESOURCES = ["official", "booth", "littable", "displays", "offers"];
const KINDS = {
  "writing-workshop": {
    family: "workshop", label: "evkind.writing-workshop.label", phrase: "evkind.writing-workshop.phrase",
    who: "evkind.writing-workshop.who", deck: "writing-workshop", where: "workshop",
    flyers: "writing workshop|taller de escritura",
    resources: ["contribute", "tips", "submit", "deadlines", "kit", "record", "published", "stories", "booth"],
  },
  "recording-workshop": {
    family: "workshop", label: "evkind.recording-workshop.label", phrase: "evkind.recording-workshop.phrase",
    who: "evkind.recording-workshop.who", deck: "recording-workshop", where: "workshop",
    flyers: "recording workshop|audio workshop|taller de (grabaci|audio)",
    resources: ["record", "kit", "listen", "published", "tips", "booth"],
  },
  "information-workshop": {
    family: "workshop", label: "evkind.information-workshop.label", phrase: "evkind.information-workshop.phrase",
    who: "evkind.information-workshop.who", deck: "information-workshop", where: "workshop",
    // (never "taller informativo": La Viña's monthly flyer says it — config/site.yml lv-monthly-workshop)
    flyers: "information workshop|taller de informaci",
    resources: ["mags", "omag", "osubs", "listen", "watch", "booth", "littable"],
  },
  "gvr-orientation": {
    family: "workshop", label: "evkind.gvr-orientation.label", phrase: "evkind.gvr-orientation.phrase",
    who: "evkind.gvr-orientation.who", deck: "orientation-workshop", where: "workshop",
    // ("orienta": "Orientación para RLV y GVR" and "GVR Orientation" alike)
    flyers: "(gvr|rlv).*orienta|orienta.*(gvr|rlv)",
    resources: ["sessions", "gvr", "register", "role"],
  },
  "gsr-dcm-orientation": {
    family: "area", label: "evkind.gsr-dcm-orientation.label", phrase: "evkind.gsr-dcm-orientation.phrase",
    where: "assembly", resources: ["area", "role", "gvr", "booth", "littable"], resourceAnchors: { gvr: ["job"] },
  },
  assembly: {
    family: "area", label: "evkind.assembly.label", phrase: "evkind.assembly.phrase", where: "assembly",
    resources: AREA_RESOURCES, resourceFallback: { official: "area" },
  },
  acm: {
    family: "area", label: "evkind.acm.label", phrase: "evkind.acm.phrase", where: "acm",
    resources: AREA_RESOURCES, resourceFallback: { official: "area" },
  },
  "town-hall": {
    family: "area", label: "evkind.town-hall.label", phrase: "evkind.town-hall.phrase", where: "assembly",
    resources: AREA_RESOURCES, resourceFallback: { official: "area" },
  },
  intergroup: {
    family: "meeting", label: "evkind.intergroup.label", phrase: "evkind.intergroup.phrase", where: "group",
    resources: ["mags", "offers", "booth"],
  },
  booth: {
    family: "booth", label: "evkind.booth.label", phrase: "evkind.booth.phrase", where: "booth", flyers: "series",
    resources: ["booth", "littable", "displays", "offers", "mags", "bulletin"],
  },
  "online-meeting": {
    family: "meeting", label: "evkind.online-meeting.label", phrase: "evkind.online-meeting.phrase",
    deck: "grapevine-meeting", deckMag: "gv", where: "online", flyers: "series",
    resources: ["gvm", "weekly", "read", "listen"],
  },
  "magazine-workshop": {
    family: "workshop", label: "evkind.magazine-workshop.label", phrase: "evkind.magazine-workshop.phrase",
    where: "online", flyers: "series", resources: ["listen", "lvshare", "record"],
  },
  calendar: {
    family: "calendar", label: "evkind.calendar.label", phrase: "evkind.calendar.phrase", where: "any",
    resources: ["official", "calfilter"],
  },
  // (no page of its own: /meetings/#committee-meeting — its kind for the places that name it)
  "committee-meeting": {
    family: "committee", label: "evkind.committee-meeting.label", phrase: "evkind.committee-meeting.phrase",
    deck: "committee-meeting", where: "committee", resources: [],
  },
  other: { family: "other", label: "evkind.other.label", phrase: "evkind.other.phrase", where: "any", resources: [] },
};
const freeze = (o) => {
  for (const v of Object.values(o)) if (v && typeof v === "object") freeze(v);
  return Object.freeze(o);
};
/** The one table of the kinds (see INTERFACE). Every kind has every field ("" / false / [] / {} when unused). */
export const EVENT_KINDS = freeze(Object.fromEntries(Object.entries(KINDS).map(([k, d]) => [k, {
  who: "", deck: "", deckMag: "", deckClose: false, flyers: "", resourceFallback: {}, resourceAnchors: {},
  ...d, resources: [...d.resources],
}])));
/** The kinds' names, in the table's order: content/events `type:` takes one of these (Python EVENT_TYPES). */
export const EVENT_KIND_KEYS = Object.freeze(Object.keys(EVENT_KINDS));

/** Our monthly series' kinds, by their config/site.yml key (a recurring_events entry's own `type:` comes first). */
export const SERIES_KIND = Object.freeze({
  "citywide-dallas": "booth",
  "grapevine-meeting": "online-meeting",
  "lv-monthly-workshop": "magazine-workshop",
});

// the bingo card's occasions (src/assets/js/bingo-core.js WHERES) and magazines (PUBS)
const BINGO_WHERE = new Set(["any", "group", "district", "assembly", "acm", "workshop", "booth", "committee", "online"]);
const BINGO_MAG = new Set(["both", "gv", "lv"]);
// The titles' words (titlesOf's form: lower case, no accents), each in English and Spanish
const RE = {
  acm: /\bacms?\b|\barea committee meetings?\b|\breunion(?:es)? del comite (?:de|del) area\b/,
  townHall: /\btown ?halls?\b/,
  assembly: /assembl|asamblea/,
  gvrRlv: /\b(?:gvrs?|rlvs?)\b/,
  orientation: /orienta/,
  writing: /\bwriting workshops?\b|\btaller(?:es)? de escritura\b/,
  recording: /\b(?:recording|audio) workshops?\b|\btaller(?:es)? de (?:grabaci|audio)/,
  information: /\binformation(?:al)? workshops?\b|\btaller(?:es)? de informaci/,
  // "intergroup", "intergrupo", "intergrupal"
  intergroup: /\bintergr[ou]p/,
  lv: /\bla vina\b/,
  gv: /\bgrapevine\b/,
};
// the categories of our own events (committee.js GROUP_OF's "neta" and "committee" ones)
const OURS = new Set(["committee", "recurring", "flyer", "manual", "ics", "neta65"]);

const recordOf = (ev) => (ev && ev.item && typeof ev.item === "object" ? ev.item : ev || {});
const typeOf = (v) => {
  const s = String(v ?? "").trim().toLowerCase();
  return Object.hasOwn(EVENT_KINDS, s) ? s : "";
};

/** A config/site.yml recurring_events entry by its key (an entry written without "- " counts too), else null. */
function seriesEntry(site, key) {
  if (!key) return null;
  const raw = site?.recurring_events;
  const list = Array.isArray(raw) ? raw : raw && typeof raw === "object" ? [raw] : [];
  return list.find((e) => e && typeof e === "object" && String(e.key ?? "") === key) || null;
}

/** The series an event is a date of: its key ("citywide-dallas") — a monthly date's (ev.series, a data item's
 *  extra.series) or a date the host moved (ev.seriesOf, extra.series_of) —, else "". */
function seriesKeyOf(ev) {
  if (!ev || typeof ev !== "object") return "";
  const rec = recordOf(ev);
  const x = rec.extra || {};
  return String(ev.series || ev.seriesOf || (rec.category === "recurring" ? x.series : x.series_of) || "");
}

/** Who holds it: "lv" / "gv", else "" (a /events/ event's host, else its record's: committee.js eventHost). */
const hostOf = (ev) => (typeof ev.host === "string" && ev.host !== "neta" ? ev.host : eventHost(recordOf(ev)));

/** From Grapevine's or La Viña's own calendar (not one of their events the committee shares)? */
function isOutside(ev) {
  if (hostOf(ev)) return false;
  if (typeof ev.group === "string") return ev.group === "calendar";
  const rec = recordOf(ev);
  return rec.category === "gv-calendar" || rec.category === "lv-calendar" || (!OURS.has(rec.category) && rec.source === "calendar");
}

/** Which magazine an event is about: "lv" / "gv" — who holds it, its tag (la-vina / grapevine), the magazine's own
 *  calendar, else the magazine its titles name —, "both" when nothing says one (or both are said). */
function magOf(ev, titles, host, tags) {
  const cat = recordOf(ev).category;
  const lv = host === "lv" || tags.includes("la-vina") || cat === "lv-calendar";
  const gv = host === "gv" || tags.includes("grapevine") || cat === "gv-calendar";
  if (lv !== gv) return lv ? "lv" : "gv";
  if (!lv) {
    const lvT = titles.some((t) => RE.lv.test(t)), gvT = titles.some((t) => RE.gv.test(t));
    if (lvT !== gvT) return lvT ? "lv" : "gv";
  }
  return "both";
}

/** Is an online event with no place (a series of ours of an unknown key, held only online)? */
function onlineOnly(ev) {
  if (typeof ev.isOnline === "boolean") return ev.isOnline && !ev.location;
  const x = recordOf(ev).extra || {};
  return !!(x.online === true || x.online_url || x.platform) && !String(x.location || "").trim();
}

/**
 * The kind of an event (a /events/ event, a data item) → { kind, family, mag, spanish, outside, series, source,
 * and the kind's table row resolved: label, phrase, who, deck, deckClose, where, flyers, resources,
 * resourceFallback, resourceAnchors } (INTERFACE). The first rule that matches wins; titles are read in every
 * language the event has (titlesOf, the same order on each language's page — so the English and the Spanish page
 * give one kind):
 *    1. `type:` — a content/events file's (extra.type), else its series' config/site.yml recurring_events entry's —
 *       when it is one of EVENT_KINDS (anything else is not read: the sync lists it on /status/);
 *    2. a committee meeting → committee-meeting;
 *    3. a date of a series (its key): SERIES_KIND's kind; a series of another key → booth (a booth's words:
 *       eventTone), magazine-workshop (La Viña's or Grapevine's own), online-meeting (online, with no place) — else
 *       the rules below;
 *    4. gsr-dcm-orientation (its tag, or the Area's orientation words: event-tone.js areaOrientation);
 *    5. acm (its tag; "ACM", "Area Committee Meeting", "Reunión del Comité de Área");
 *    6. town-hall (its tag town-hall or delegate; "town hall");
 *    7. assembly (its tag; "assembl…", "asamblea");
 *    8. gvr-orientation ("GVR" / "RLV" with "orienta…");
 *    9. writing-workshop ("writing workshop", "taller de escritura");
 *   10. recording-workshop ("recording / audio workshop", "taller de grabación / audio");
 *   11. information-workshop ("information(al) workshop", "taller de información" — never "taller informativo");
 *   12. intergroup (its tag; "intergroup", "intergrupal");
 *   13. calendar (from Grapevine's or La Viña's own calendar);
 *   14. booth (a booth's words: eventTone "booth");
 *   15. other.
 * Flags: mag (magOf), spanish (heldInSpanish: the language it is held in, as its Event's inLanguage), outside
 * (from the magazines' own calendars), series (its series' key, or ""). site: for 1 and for a series' flyer_match
 * (the kind's "series" flyers); without it neither is read.
 */
export function eventKind(ev, site) {
  const e = ev && typeof ev === "object" ? ev : {};
  const rec = recordOf(e);
  const x = rec.extra || {};
  const tags = Array.isArray(rec.tags) ? rec.tags.map((t) => String(t).toLowerCase()) : [];
  const titles = titlesOf(e);
  const host = hostOf(e);
  const series = seriesKeyOf(e);
  const entry = seriesEntry(site, series);
  const outside = isOutside(e);
  const tone = eventTone(e);
  const say = (re) => titles.some((t) => re.test(t));
  const decide = () => {
    const own = typeOf(x.type);
    if (own) return [own, "type"];
    const cfg = typeOf(entry && entry.type);
    if (cfg) return [cfg, "series-type"];
    if (e.committee === true || rec.category === "committee" || String(rec.id || e.id || "").startsWith("ev:committee:")) return ["committee-meeting", "committee"];
    if (series) {
      if (SERIES_KIND[series]) return [SERIES_KIND[series], "series"];
      if (tone === "booth") return ["booth", "series"];
      if (host) return ["magazine-workshop", "series"];
      if (onlineOnly(e)) return ["online-meeting", "series"];
    }
    if (tags.includes("gsr-dcm-orientation")) return ["gsr-dcm-orientation", "tag"];
    if (titles.some(areaOrientation)) return ["gsr-dcm-orientation", "title"];
    if (tags.includes("acm")) return ["acm", "tag"];
    if (say(RE.acm)) return ["acm", "title"];
    if (tags.includes("town-hall") || tags.includes("delegate")) return ["town-hall", "tag"];
    if (say(RE.townHall)) return ["town-hall", "title"];
    if (tags.includes("assembly")) return ["assembly", "tag"];
    if (say(RE.assembly)) return ["assembly", "title"];
    if (titles.some((t) => RE.gvrRlv.test(t) && RE.orientation.test(t))) return ["gvr-orientation", "title"];
    if (say(RE.writing)) return ["writing-workshop", "title"];
    if (say(RE.recording)) return ["recording-workshop", "title"];
    if (say(RE.information)) return ["information-workshop", "title"];
    if (tags.includes("intergroup")) return ["intergroup", "tag"];
    if (say(RE.intergroup)) return ["intergroup", "title"];
    if (outside) return ["calendar", "calendar"];
    if (tone === "booth") return ["booth", "tone"];
    return ["other", "default"];
  };
  const [kind, source] = decide();
  const def = EVENT_KINDS[kind];
  const mag = magOf(e, titles, host, tags);
  const flyers = def.flyers === "series" ? String((entry && entry.flyer_match) || "").trim() : def.flyers;
  return {
    kind, family: def.family, mag, spanish: heldInSpanish(e), outside, series, source,
    label: def.label, phrase: def.phrase, who: def.who,
    deck: def.deck && (!def.deckMag || def.deckMag === mag) ? def.deck : "", deckClose: def.deckClose,
    where: def.where, flyers, resources: def.resources, resourceFallback: def.resourceFallback,
    resourceAnchors: def.resourceAnchors,
  };
}

/* ------------------------------------------------------------------ */
/*  Tiers                                                              */
/* ------------------------------------------------------------------ */
/** What each tier's page is (see the top of this file): indexable (in the sitemap) and with its Event markup. */
export const EVENT_TIERS = Object.freeze({
  leaf: Object.freeze({ index: true, ld: true }),
  page: Object.freeze({ index: true, ld: false }),
  date: Object.freeze({ index: false, ld: false }),
  // (its notice page: EventCancelled when it was to be held at a place — U1's template decides its markup)
  cancelled: Object.freeze({ index: true, ld: false }),
  none: Object.freeze({ index: false, ld: false }),
});

/** The tier of a /events/ event's page in ONE language (eventPagePlan pairs the languages): see the top of this
 *  file. langs: the site's languages (eventLeaf asks for a real address in every one). */
export function eventPageTier(ev, site, langs = ["en", "es"]) {
  if (!ev || typeof ev !== "object" || ev.committee) return "none";
  if (typeof ev.anchor !== "string" || !EVENT_PAGE_ANCHOR.test(ev.anchor)) return "none";
  if (eventCancelled(ev)) return ev.past ? "none" : "cancelled";
  if (ev.past || ev.recurring || ev.seriesOf || (ev.group === "calendar" && !ev.host)) return "date";
  return eventLeaf(ev, site, langs) ? "leaf" : "page";
}

/* ------------------------------------------------------------------ */
/*  The bingo card for an event                                        */
/* ------------------------------------------------------------------ */
const BINGO_TEXT_MAX = 60;          // bingo-core.js TEXT_MAX.event

/** A title cut to `n` characters at a word (one word longer than that: cut inside it), no "…" — the bingo card
 *  prints it whole. Never a bracket left open: a cut inside "(…)" keeps the words before it ("XLII Reunión de A.A.
 *  Zona Norte de Texas (A.A. Un camino a la libertad)" → "XLII Reunión de A.A. Zona Norte de Texas"). */
function cutAtWord(s, n) {
  const t = String(s ?? "").replace(/\s+/g, " ").trim();
  if (t.length <= n) return t;
  const w = t.slice(0, n + 1).replace(/\s+\S*$/, "");
  let c = w && w.length <= n ? w : t.slice(0, n);
  const open = c.lastIndexOf("(");
  if (open > 0 && !c.includes(")", open)) c = c.slice(0, open);
  return c.replace(/[\s,;:·—–-]+$/, "");
}

/** An event's title in a language: the page's own (ev.title) in the page's language, else its record's
 *  translation or original in that language, else the page's. */
function titleIn(ev, L, pageLang) {
  if (L === pageLang && ev.title) return ev.title;
  const rec = recordOf(ev);
  const tr = rec.i18n && rec.i18n.title && rec.i18n.title[L];
  return tidyBrackets(tr || (rec.lang === L ? rec.title : "") || ev.title || rec.title || "");
}

/**
 * A GVR/RLV Bingo card made for an event, ready to print (/gvr/bingo/, src/assets/js/bingo-core.js fromHash): the
 * builder's page in the page's language, "/[es/]gvr/bingo/#lang=<card language>&mag=<lv | gv | both>&where=<the
 * kind's occasion>&event=<its title, at most 60 characters, cut at a word>&date=<its day, YYYY-MM-DD>" — the card in
 * Spanish for an event held in Spanish (kind.spanish), else in the page's language, its title in the card's language.
 * Only for an event still to come and not cancelled ("" otherwise). ev: a /events/ event (normalizeEvents — a plan
 * page's ev): it says whether it is over (ev.past) and its day (ev.startYmd); a data item says neither, and gets ""
 * (never a card for a day that may be over). kind: eventKind's answer (worked out when left out). Never ?booth=…: that
 * would replace the settings saved on that device (booth.js).
 */
export function bingoHref(ev, kind, lang = "en") {
  if (!ev || typeof ev !== "object" || typeof ev.past !== "boolean" || ev.past || eventCancelled(ev)) return "";
  const k = kind && typeof kind === "object" && kind.kind ? kind : eventKind(ev);
  const page = lang === "es" ? "es" : "en";
  const L = k.spanish ? "es" : page;
  const date = /^20\d{2}-\d{2}-\d{2}$/.test(String(ev.startYmd || "")) ? ev.startYmd : "";
  const parts = [
    ["lang", L], ["mag", BINGO_MAG.has(k.mag) ? k.mag : "both"], ["where", BINGO_WHERE.has(k.where) ? k.where : "any"],
    ["event", cutAtWord(titleIn(ev, L, page), BINGO_TEXT_MAX)], ["date", date],
  ].filter(([, v]) => v);
  return `${page === "es" ? "/es" : ""}/gvr/bingo/#` + parts.map(([n, v]) => `${n}=${encodeURIComponent(v)}`).join("&");
}

/* ------------------------------------------------------------------ */
/*  The plan                                                           */
/* ------------------------------------------------------------------ */
const eventsPath = (lang) => (lang && lang !== "en" ? `/${lang}/events/` : "/events/");
const plans = new WeakMap();          // items → [{ key, cancelled, plan }]
const NO_ITEMS = [];

/** The head of an event's page or a series' page (a plan's page / hub) → { title, titleTail, description, ogImage }:
 *  committee.js eventPageMeta (an event's title with its day) or seriesPageMeta (a series' title with its rule), and
 *  the title with its titleSuffix (" — Tyler": eventPagePlan's, when two pages of a language would share a title).
 *  An event's description never gives its own meeting ID, code or link, not even bare (committee.js
 *  withoutJoinValues: its summary without those sentences, before eventPageMeta's plainLine). */
export function eventPageHead(page, site) {
  if (!page || typeof page !== "object") return null;
  const hub = !!(page.key && page.series);
  const head = hub ? seriesPageMeta(page, site, page.lang) : eventPageMeta(withoutOwnJoin(page.ev), site, page.lang);
  if (!page.titleSuffix) return head;
  const title = `${head.title} — ${page.titleSuffix}`;
  return { ...head, title, titleTail: eventsTitleTail(title, page.lang) };
}

// A /events/ event whose summary gives none of its own ways in (withoutJoinValues: its meeting ID or code, its online
// link) — the event itself when there is nothing to leave out, else a copy with that summary.
function withoutOwnJoin(ev) {
  if (!ev || typeof ev !== "object") return ev;
  const summary = withoutJoinValues(ev.summary, [ev.meetingId, ev.online]);
  return summary === String(ev.summary ?? "") ? ev : { ...ev, summary };
}

// An event's city, for the words that tell two titles apart: the data's, else its place's (eventPlace).
function cityOf(ev) {
  const x = ev.item?.extra || {};
  if (x.city) return String(x.city).trim();
  const p = ev.location ? eventPlace(String(ev.location), x) : null;
  return (p && p.address && p.address.addressLocality) || "";
}

/** Titles unique in each language (the [seo] check: no two pages of a language share a <title>): the hubs first,
 *  then the indexable pages, then the others, each in date order. The first page of a title keeps it as it is; a
 *  later one gets " — <its city>" when no earlier page of that title is in that city, else " — <its time>" (no
 *  earlier one at that time), else both, else " — 2", " — 3" … — always a title not taken yet. */
function setHeads(list, site) {
  const taken = new Set();
  const earlier = new Map();          // a title → the [city, time] of the pages that had it before
  for (const p of list) {
    p.titleSuffix = "";
    p.head = eventPageHead(p, site);
    const base = p.head.title;
    const ev = p.ev || p.next || {};
    const facts = [cityOf(ev), ev.multiDay ? "" : String(ev.timeLabel || "").trim()];
    if (taken.has(base)) {
      const before = earlier.get(base) || [];
      const differs = (i) => facts[i] && before.every((f) => f[i] !== facts[i]);
      const tries = [differs(0) ? facts[0] : "", differs(1) ? facts[1] : "",
        facts[0] && facts[1] && before.every((f) => f[0] !== facts[0] || f[1] !== facts[1]) ? `${facts[0]}, ${facts[1]}` : ""];
      let suffix = tries.find((s) => s && !taken.has(`${base} — ${s}`)) || "";
      for (let n = 2; !suffix; n++) if (!taken.has(`${base} — ${n}`)) suffix = String(n);
      p.titleSuffix = suffix;
      p.head = eventPageHead(p, site);
    }
    earlier.set(base, [...(earlier.get(base) || []), facts]);
    taken.add(p.head.title);
  }
}

/**
 * Every event's own page and every monthly series' page, in every language (INTERFACE) — the one answer the page
 * templates paginate over (each its tier: `pages.filter((p) => p.index)` …), the links to them read
 * (committee.js eventPageHref with { plan }), /llms.txt lists from and the search points at.
 *   items     db.events.items (the events.json records)
 *   site      the `site` global: site.built is the moment every page is decided at (one build, one moment — the
 *             templates call this a moment apart), site.recurring_events the series
 *   langs     the site's languages (src/_data/languages.js)
 *   opt       { cancelled: db.events.cancelled — the cancelled events' records: no ordinary page at their anchor }
 * The same call (the same items array, site.built, site.url, languages and cancelled list) gives the same plan,
 * worked out once.
 */
export function eventPagePlan(items, site, langs = ["en", "es"], opt = {}) {
  const list = Array.isArray(items) ? items : NO_ITEMS;
  const ls = Array.isArray(langs) && langs.length ? [...langs] : ["en", "es"];
  const cancelled = Array.isArray(opt && opt.cancelled) ? opt.cancelled : NO_ITEMS;
  const key = `${site?.built ?? ""}|${site?.url ?? ""}|${ls.join(",")}|${EMPTY ? 1 : 0}`;
  const memo = plans.get(list) || [];
  const hit = memo.find((m) => m.key === key && m.cancelled === cancelled);
  if (hit) return hit.plan;
  const plan = buildPlan(list, site || {}, ls, cancelled);
  memo.push({ key, cancelled, plan });
  plans.set(list, memo);
  return plan;
}

function buildPlan(items, site, langs, cancelled) {
  const built = Date.parse(String(site.built || ""));
  const now = Number.isFinite(built) ? new Date(built) : new Date();
  const cancelledAnchors = new Set([...cancelled, ...items.filter(eventCancelled)].filter(Boolean).map(eventAnchor));
  // 1) each language's events, as /events/ lists them, and each one's tier in that language
  const rows = [];
  const byLang = {};
  for (const lang of langs) {
    const seen = new Set();
    byLang[lang] = new Map();
    for (const ev of EMPTY ? [] : normalizeEvents(items, site, lang, { now })) {
      if (!ev || ev.committee || !EVENT_PAGE_ANCHOR.test(ev.anchor || "") || seen.has(ev.anchor)) continue;
      seen.add(ev.anchor);
      if (eventCancelled(ev) || cancelledAnchors.has(ev.anchor)) continue;
      const tier = eventPageTier(ev, site, langs);
      if (tier === "none" || tier === "cancelled") continue;
      const row = { lang, anchor: ev.anchor, ev, tier };
      rows.push(row);
      byLang[lang].set(ev.anchor, row);
    }
  }
  // 2) one tier for every language: indexable only with its twin in each language (hreflang), its Event only when it
  //    is a leaf in each
  const anchors = new Set(rows.map((r) => r.anchor));
  for (const a of anchors) {
    const twins = langs.map((l) => byLang[l].get(a));
    const tier = twins.every(Boolean) && twins.every((r) => r.tier === "leaf") ? "leaf"
      : twins.every(Boolean) && twins.every((r) => r.tier === "leaf" || r.tier === "page") ? "page" : "date";
    for (const r of twins) if (r) r.tier = tier;
  }
  // 3) the series' pages: an enabled config/site.yml entry, a key fit for an address, a date still to come in the
  //    data (not cancelled) — in every language
  const raw = site.recurring_events;
  const entries = (Array.isArray(raw) ? raw : raw && typeof raw === "object" ? [raw] : [])
    .filter((e) => e && typeof e === "object" && e.enabled !== false && EVENT_PAGE_ANCHOR.test(String(e.key ?? "")));
  const hubs = [];
  const hubKeys = [];
  for (const entry of entries) {
    const k = String(entry.key);
    if (hubKeys.includes(k)) continue;
    const upcoming = rows.some((r) => !r.ev.past && (r.ev.recurring ? r.ev.series === k : r.ev.seriesOf === k));
    if (!upcoming) continue;
    // (seriesNext makes a date the data lacks from the settings: a cancelled date is left out of the list here)
    const series = langs.map((lang) => seriesNext(site, k, lang, items, { now, n: 6 + cancelledAnchors.size }));
    if (!series.every(Boolean)) continue;
    hubKeys.push(k);
    langs.forEach((lang, i) => {
      const s = series[i];
      // seriesNext reads the rule's dates only (skip_dates honoured): the dates the host moved (ev.seriesOf — its own
      // calendar listing of a month the rule skips, or a dated Drive flyer of the series: La Viña's workshop the week
      // before Thanksgiving) are this language's rows, taken in among them in date order — the next date, the share
      // picture and the list say the day it really is
      const moved = rows.filter((r) => r.lang === lang && r.ev.seriesOf === k && !r.ev.past).map((r) => r.ev);
      const listed = new Set(s.dates.map((d) => d.anchor));
      const dates = [...s.dates, ...moved.filter((d) => !listed.has(d.anchor))]
        .filter((d) => !cancelledAnchors.has(d.anchor) && !eventCancelled(d))
        .sort((a, b) => a.startMs - b.startMs || String(a.anchor).localeCompare(String(b.anchor)))
        .slice(0, 6);
      if (!dates.length) return;
      const hubSeries = { ...s, next: dates[0], dates };
      hubs.push({ lang, key: k, path: seriesPagePath(k, lang), kind: eventKind(dates[0], site), series: hubSeries,
        next: dates[0], dates, datePages: [], target: eventsPath(lang), index: true, titleSuffix: "", head: null });
    });
  }
  // (a hub in one language only — every date of it cancelled there, never — would have no twin: none at all)
  const twinned = hubKeys.filter((k) => langs.every((l) => hubs.some((h) => h.key === k && h.lang === l)));
  const keptHubs = hubs.filter((h) => twinned.includes(h.key));
  // 4) the pages
  const pages = rows.map((r) => {
    const kind = eventKind(r.ev, site);
    const hubKey = kind.series && twinned.includes(kind.series) ? kind.series : "";
    const tier = EVENT_TIERS[r.tier];
    return {
      lang: r.lang, anchor: r.anchor, path: eventPagePath(r.ev, r.lang), ev: r.ev, tier: r.tier, index: tier.index,
      ld: tier.ld, kind, hubKey, hubPath: hubKey ? seriesPagePath(hubKey, r.lang) : "",
      target: eventsPath(r.lang) + (r.ev.past && r.ev.recurring ? "" : "#" + r.anchor), titleSuffix: "", head: null,
    };
  });
  const byAnchor = {};
  const byPath = {};
  for (const p of pages) {
    (byAnchor[p.anchor] ||= {})[p.lang] = p;
    byPath[p.path] = p;
  }
  for (const h of keptHubs) {
    h.datePages = h.dates.map((d) => byAnchor[d.anchor]?.[h.lang] || null);
    byPath[h.path] = h;
  }
  // 5) the heads, titles unique in each language
  for (const lang of langs) {
    setHeads([...keptHubs.filter((h) => h.lang === lang), ...pages.filter((p) => p.lang === lang && p.index),
      ...pages.filter((p) => p.lang === lang && !p.index)], site);
  }
  return { pages, hubs: keptHubs, hubKeys: twinned, byAnchor, byPath, cancelledAnchors: [...cancelledAnchors].sort(),
    langs, now: now.toISOString() };
}

/* ------------------------------------------------------------------ */
/*  Related events                                                     */
/* ------------------------------------------------------------------ */
/**
 * Events to show on an event's (or a series') page (INTERFACE): planOrList — a plan (its pages in the page's
 * language), a list of plan pages, or a list of /events/ events; page — a plan's page or hub, or a /events/ event
 * (one of the plan's own, p.ev, or any with opt.lang: a /events/ event does not say its language);
 * opt: { sameKind (false) — only the page's kind (eventKind), n (3), past (false) — the events that are over, newest
 * first, instead of the next ones, soonest first; site — for the kind of a /events/ event (eventKind's `type:` of a
 * series); lang — the page's language when `page` does not say it }. Never the page's own event, another date of its
 * own series (the page lists those itself), a committee meeting or a cancelled event; one date per series (its
 * soonest — or, past, its latest); only pages in the page's language. A list of pages in several languages with no
 * language known for the page throws (the caller's mistake: it would link both twins of an event, and pages in the
 * other language).
 * → the entries themselves (plan pages: link each by its .path).
 */
export function relatedEvents(planOrList, page, opt = {}) {
  const o = opt || {};
  const n = Number.isFinite(Number(o.n)) && Number(o.n) >= 0 ? Number(o.n) : 3;
  const past = !!o.past;
  const list = Array.isArray(planOrList) ? planOrList : planOrList && Array.isArray(planOrList.pages) ? planOrList.pages : [];
  if (!page || typeof page !== "object" || !n) return [];
  const evOf = (x) => (x && x.ev && typeof x.ev === "object" ? x.ev : x);
  const kindOf = (x) => (x && x.kind && typeof x.kind === "object" && x.kind.kind ? x.kind : eventKind(evOf(x), o.site));
  const me = page.key && page.series ? null : evOf(page);
  // the page's language: its own (a plan's page or hub), the caller's, else the plan page this very event is of
  const lang = String(page.lang || o.lang || list.find((x) => x && x.ev === page)?.lang || "");
  if (!lang && new Set(list.map((x) => x && x.lang).filter(Boolean)).size > 1) {
    throw new Error("relatedEvents: the page's language is unknown (a /events/ event): pass a plan page, or opt.lang");
  }
  const myKind = kindOf(page).kind;
  const mySeries = page.key && page.series ? String(page.key) : seriesKeyOf(me);
  const myAnchor = me ? me.anchor : "";
  const out = [];
  const seriesSeen = new Set();
  const pool = list.filter((x) => {
    const ev = evOf(x);
    if (!ev || typeof ev !== "object" || ev.committee || eventCancelled(ev)) return false;
    if (lang && x.lang && x.lang !== lang) return false;
    if (myAnchor && ev.anchor === myAnchor) return false;
    if (!!ev.past !== past) return false;
    const s = seriesKeyOf(ev);
    if (mySeries && s === mySeries) return false;
    return !o.sameKind || kindOf(x).kind === myKind;
  });
  pool.sort((a, b) => (past ? evOf(b).startMs - evOf(a).startMs : evOf(a).startMs - evOf(b).startMs)
    || String(evOf(a).anchor).localeCompare(String(evOf(b).anchor)));
  for (const x of pool) {
    if (out.length >= n) break;
    const s = seriesKeyOf(evOf(x));
    if (s && seriesSeen.has(s)) continue;
    if (s) seriesSeen.add(s);
    out.push(x);
  }
  return out;
}
