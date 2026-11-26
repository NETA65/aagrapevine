// Round 37 · what an event's own page and a monthly series' page SAY beyond the event itself: its one-sentence
// lede, its quick facts, "Get ready" (the kind's presentation, its GVR/RLV Bingo card, the pages and guides that go
// with it), the next dates of its series, the next event of its kind, what else is coming up, past events like it,
// the flyers of similar events and the magazines of its month. Worked out at build time from the data alone — the
// page plan (eleventy/event-pages.js eventPagePlan: which event gets which page), the event's kind (eventKind, the
// judge's spec §4) and the data the rest of the site shows (db.drive's flyers, db.pdfs' guides, the presentations,
// the photo albums, the bulletin, the month models) — so an event file, a dated Drive flyer or a recurring_events
// entry added tomorrow gets a full page with every section of its kind at the next build, and nobody writes one.
// A pure module (not in eleventy/filters/, whose files are plugins whose filters must all be used —
// test_unused_code), read by the three page templates' pagination `before` (src/pages/event-share-leaf.njk,
// event-share-date.njk, event-share-series.njk), which hand each page its entry (`share`):
//
//   eventPageData(full) → { pages, hubs } — memoized: one answer for the three templates of a build (the same plan,
//                         the same data); full: a template's data (db, site, languages, presentations,
//                         orientation, monthlyKeys).
//     pages[]  { lang, anchor, path, tier, index, ld, target, hubKey, hubPath, head, ev, kind, m }   (plan.pages)
//     hubs[]   { lang, key, path, index, target, head, kind, ev (its next date), series, m }        (plan.hubs)
//     m        the page's model (below) — plain data: the other events as small copies (mini), never a page of the
//              plan, so no cycle (Eleventy deep-copies a pagination's items: a cycle would never end)
//
// The model gives TRANSLATION KEYS and values; the templates translate them (src/_includes/partials/event-page.njk,
// macros/event-page.njk — every key in src/_i18n/evpage.json, evkind.json):
//   mode        "event" | "series"
//   summary     an event that is over: its summary without how to join (else "": the page shows the whole text)
//   lede        { key ("evpage.lede.*"), when, from, to, place, platform, recurrence, next, hybrid (a platform for
//               "You can also join online …", else ""), held ("evpage.lede.es", "…_past" once it is over: only for
//               an event the data says is held in Spanish — never a guess that the others are in English; "" too when
//               its title says its language), org (the organizer's name in the page's language: our committee's
//               committee_es on a Spanish page — orgName —, else ""), orgKey ("evpage.lede.org", "…_past"; our
//               committee: "evpage.lede.org_ours", "…_past" — "It is organized by the …") } — one plain sentence for
//               people, search engines and AI answers alike; never a meeting link, ID or code (only the platform's
//               name), never a person's name
//   facts       [{ k ("what" | "when" | "where" | "language" | "organizer" | "cost" | "who" | "repeats" | "contact"),
//               v (a value) | vKey (a key to translate) | vOnline (a platform: "Online on …"), href, ext (outside),
//               mail, map (a map link: an upcoming event held at a real address) }]
//   banners     { past, tentative, partOf ({ title, href }: its series' page) }
//   crumbs      [{ key | label, href }] — Home › Events › [its series ›] (the page itself last, no link)
//   prep        { heading ("evpage.sec.prep", "evpage.sec.more" once it is over), deck ({ id, href (start it:
//               /orientation/?present=<id>), card (/orientation/#pres-<id>), title, summary, minutes, close } | null),
//               bingo (bingoHref: the builder filled in — upcoming events only), resources: [{ id, labelKey, label,
//               textKey, text (its line as written: a GVR / RLV 101 lesson's own summary, when there is no textKey),
//               href, ext, icon, links: [{ href, labelKey, label, vars, ext, file (a file of the site — the deadlines'
//               .ics —: the template gives it its language, `| lurl(lang)`, once the build knows which files it
//               writes in each language) }] }] }
//   dates       a series' next dates (its page's list; a date page's too, its own marked) → [mini]
//   nextSame    the next event of the same kind (mini) | null
//   coming      the next events of any kind (mini × ≤ 3)
//   meeting     the committee's next meeting ({ when }: its day and time — its page is /meetings/#committee-meeting)
//   pastSame    past events of the same kind (mini × ≤ 3, newest first)
//   flyers      flyers of similar events (Drive: [{ title, titleLang, view, preview, thumb }] × ≤ 4, never its own)
//   flyer       a series page's own flyer ({ view, preview, thumb }) | null
//   month       { key, current (this month), toolkit (/monthly/<key>/ when the toolkit has it), gv, lv ({ pub,
//               label, theme, themeLang, url, cover, soon }) } | null — the magazines of the event's month
//               (monthly.js monthModel: an issue not out yet has its theme and "Coming soon")
//   latest      "gv" when the page shows Grapevine's newest issue too (the Grapevine Meeting: we read from it)
//   mini        { href, title, when, tile, location, locationTba, isOnline, platform, tone, tentative, thumb,
//               current } — another event as a small card (its own page); a date in its own series' list leaves out
//               what every date shares (title and location ""): its day and time are its name
//
// Never `?booth=start&bs=…` (booth.js: `bs` REPLACES the settings that device keeps for its booth — the event's name,
// the languages, the slides). The "Booth display" link is the About page's #booth section (its preview, its own
// "Start" and Settings buttons, its words); its "Start the display" link is /about/?booth=start with NO `bs`: the
// show opens at once with the settings the device already has (or the defaults), and changes none of them
// (booth.js startPage: only a `bs` value is ever saved).
import { eventPagePlan, relatedEvents, bingoHref } from "./event-pages.js";
import {
  eventOrganizer, isCommitteeOrganizer, eventPlace, driveMatch, photoAlbums, announcementList, flyerLinks,
  withoutJoinDetails, withoutJoinValues, normalizeEvents, ownPageOf, platformOf,
} from "./filters/committee.js";
import { eventTone } from "./filters/event-tone.js";
import { writerKit } from "./filters/read.js";
import { monthModel } from "./filters/monthly.js";
import { langPath, pickLang, siteUrl } from "../eleventy.config.js";

const LOCALES = { en: "en-US", es: "es-US" };
const lurl = (p, lang) => langPath(p, lang);
const lowerFirst = (s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s);
const line = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
// a title that names its language already ("… (in Spanish)", "Reunión de Grapevine (en inglés)": committee.js
// SAYS_LANG) — its lede says it no second time
const SAYS_LANG = /\((?:in|en) (?:english|spanish|inglés|español)\)/i;
const FLYERS_SHOWN = 4;

/* ------------------------------------------------------------------ */
/*  The resource catalogue (the judge's spec §4)                       */
/* ------------------------------------------------------------------ */
// Each kind's "Get ready" links, by id (eleventy/event-pages.js EVENT_KINDS resources). A resource the data cannot
// give (no writer's guide in the Library, no display album, no pinned bulletin post, no official page) is left out.
// Labels: "evpage.res." + id (and + "_t" for its line), a lesson's own title and summary (config/orientation.yml),
// or a key.
const LESSON = { omag: "magazines", osubs: "subscriptions", role: "role", littable: "literature-table", stories: "stories" };
// A kind with no list of its own ("other": an event the rules cannot place — the judge's spec §4 gives it none): the
// magazines' own links, so that every event's page still has some — read them, buy them, write for them, our
// committee's latest news (the owner: "making sure they all get some information and links").
const GENERIC_RESOURCES = ["read", "mags", "contribute", "bulletin"];
const DRIVE_OR_DOCS = /^https?:\/\/(?:drive|docs)\.google\.com\//;
const ICON = {
  contribute: "pen-line", tips: "lightbulb", submit: "send", deadlines: "calendar-clock", kit: "file-text", record: "mic",
  published: "book-open-check", stories: "graduation-cap", booth: "monitor-play", littable: "table-2", displays: "images",
  offers: "tag", mags: "book-open", omag: "graduation-cap", osubs: "graduation-cap", listen: "headphones", watch: "play",
  sessions: "graduation-cap", gvr: "users", register: "user-plus", role: "graduation-cap", area: "landmark",
  official: "external-link", gvm: "video", weekly: "calendar-sync", read: "newspaper", lvshare: "send",
  calfilter: "calendar-search", bulletin: "megaphone",
};

function resource(id, c) {
  const { ev, kind, lang, site, db, full } = c;
  const mag = kind.mag;
  const r = (href, extra = {}) => ({
    id, labelKey: `evpage.res.${id}`, label: "", textKey: `evpage.res.${id}_t`, text: "", href, ext: /^https?:/.test(href || ""),
    icon: ICON[id] || "arrow-right", links: [], ...extra,
  });
  const sub = (href, labelKey, vars = null) => ({ href, labelKey, label: "", vars, ext: /^https?:/.test(href || "") });
  const pick = (o) => (o && typeof o === "object" ? o[lang] || o.en || "" : String(o || ""));
  switch (id) {
    case "contribute": return r(lurl("/contribute/#workshop", lang));
    case "tips": return r(lurl("/contribute/#tips", lang));
    case "submit": return r(lurl("/contribute/#submit", lang));
    // (the deadlines' calendar is a FILE, written in each language — /es/deadlines.ics is La Viña's —: its address in
    // the page's language only once the build knows its files, which a pagination's `before` runs ahead of; so the
    // template gives it its language, `file`)
    case "deadlines": return r(lurl("/contribute/#deadlines", lang), { links: [{ ...sub("/deadlines.ics", "evpage.res.deadlines_ics"), file: true }] });
    case "kit": {
      const kit = writerKit(db.pdfs?.items || [], 4);
      if (!kit.length) return null;
      return r("", { links: kit.map((p) => ({ href: p.url, labelKey: "", label: line(p.title), lang: p.lang && p.lang !== lang ? p.lang : "", ext: true })) });
    }
    case "record": {
      const line_ = db.audio_project?.[mag === "both" ? (lang === "es" ? "lv" : "gv") : mag];
      const phone = line_ && line_.phone && line_.tel ? line_ : null;
      return r(lurl("/contribute/#record", lang), phone ? { links: [sub(`tel:${phone.tel}`, "evpage.res.record_call", { phone: phone.phone })] } : {});
    }
    case "published": return r(lurl(`/published/?scope=neta65${mag === "both" ? "" : `&pub=${mag}`}`, lang));
    case "booth":
      // (see the top of this file: the section with its own Start button, and a start link WITHOUT `bs`)
      return r(lurl("/about/#booth", lang), { links: [sub(lurl("/about/?booth=start", lang), "evpage.res.booth_start")] });
    case "displays": {
      const album = c.displays;
      return album ? r(lurl(`/photos/#${album.slug}`, lang)) : null;
    }
    case "offers": return r(lurl("/shop/#offers", lang));
    case "mags": {
      const links = mag === "both" ? [] : [sub(lurl(`/shop/#mag-${mag}`, lang), `evpage.res.mag_${mag}`)];
      return r(lurl("/shop/#magazines", lang), { links });
    }
    case "listen": return r(lurl(`/listen/${mag === "lv" ? "?show=lvo" : mag === "gv" ? "?show=wo" : ""}`, lang));
    case "watch": return r(lurl("/watch/", lang));
    case "sessions": return r(lurl("/orientation/#sessions", lang));
    case "gvr": {
      const anchors = (kind.resourceAnchors && kind.resourceAnchors.gvr) || ["job", "steps", "kits"];
      return r(lurl(`/gvr/#${anchors[0]}`, lang), {
        links: anchors.length > 1 ? anchors.map((a) => sub(lurl(`/gvr/#${a}`, lang), `evpage.res.gvr_${a}`)) : [],
      });
    }
    case "register": {
      const links = [];
      if (mag !== "lv" && site.links?.gvr_register) links.push(sub(site.links.gvr_register, "evpage.res.register_gvr"));
      if (mag !== "gv" && site.links?.rlv_register) links.push(sub(site.links.rlv_register, "evpage.res.register_rlv"));
      if (!links.length) return null;
      return r(links.length === 1 ? links[0].href : "", { links: links.length > 1 ? links : [] });
    }
    case "area": return site.area_website ? r(site.area_website) : null;
    case "official": {
      // an event from the magazines' own calendars: their page about it (its link); one of ours: its own page on
      // another site by eventLeaf's rule (committee.js ownPageOf: never a site's home page — the Area's, CityWide's —
      // nor a page of our own site); never its flyer on Drive / Docs, nor a meeting's room (Zoom, Google Meet …: how
      // to join, which a page that is over never shows). None: the kind's fallback (an assembly: the Area's site).
      // (round 37's fixer) a monthly series' page: the series' own site, its `url:` ("https://citywidedallasaa.org"
      // — the booth's dates link it as "Event details"; the series' page is the one place search engines may list)
      const own = !ev ? "" : kind.outside || c.hub ? (ev.linkExternal ? String(ev.link || "") : "") : ownPageOf(ev, siteUrl("/", site));
      const link = own && own !== (ev.flyer ? ev.flyer.view : "") && !DRIVE_OR_DOCS.test(own) && !platformOf(own) ? own : "";
      return !link ? null : c.hub ? r(link, { labelKey: "evpage.res.official_series", textKey: "evpage.res.official_series_t" })
        : r(link, { labelKey: "evpage.sec.official" });
    }
    // (the Grapevine Meeting's own pages: its section on /meetings/ is what happens at it — not a link to "the
    // Grapevine Meeting" under its own presentation's card of the same name)
    case "gvm": return r(lurl("/meetings/#grapevine-meeting", lang), kind.series === "grapevine-meeting"
      ? { labelKey: "evpage.res.gvm_more", textKey: "evpage.res.gvm_more_t" } : {});
    case "weekly": return r(lurl("/meetings/#weekly-open", lang));
    case "read": return r(lurl("/read/", lang));
    case "lvshare": return site.links?.lv_share_story ? r(site.links.lv_share_story) : null;
    case "calfilter": return r(lurl("/events/?filter=calendar", lang));
    case "bulletin": return c.bulletin ? r(lurl(`/bulletin/#${c.bulletin}`, lang)) : null;
    default: {
      if (LESSON[id]) {
        // (its title and its own one-line summary — "Set up a table people stop at …" —; a lesson without one: "A
        // short session of GVR / RLV 101.")
        const lesson = (full.orientation?.lessons || []).find((l) => l && l.id === LESSON[id]);
        if (!lesson) return null;
        const text = line(pick(lesson.summary));
        return r(lurl(`/orientation/${LESSON[id]}/`, lang), { labelKey: "", label: line(pick(lesson.title)),
          textKey: text ? "" : "evpage.res.lesson_t", text });
      }
      return null;
    }
  }
}

function resources(c) {
  const out = [];
  const listed = c.kind.resources && c.kind.resources.length ? c.kind.resources : GENERIC_RESOURCES;
  // (a series' page: its own site first, when it has one — the "official" resource, which the kind may list too)
  const ids = c.hub && !listed.includes("official") ? ["official", ...listed] : listed;
  for (const id of ids) {
    let res = resource(id, c);
    const fb = c.kind.resourceFallback && c.kind.resourceFallback[id];
    if (!res && fb) res = resource(fb, c);
    if (res && !out.some((o) => o.id === res.id)) out.push(res);
  }
  return out;
}

/* ------------------------------------------------------------------ */
/*  Words                                                              */
/* ------------------------------------------------------------------ */
// An event's day (and time) in words for a sentence: "Saturday, December 12, 2026, 10:00 AM – 2:00 PM CST" — in
// Spanish its first letter small, after "el" ("el sábado, 12 de diciembre de 2026, …").
function whenWords(ev, lang) {
  const s = line(ev.allDay || !ev.timeLabel ? ev.dateLabel : `${ev.dateLabel}, ${ev.timeLabel}`);
  return lang === "es" ? lowerFirst(s) : s;
}

// The first and last day of an event over several days, in full words: { from: "Friday, March 19", to: "Sunday,
// March 21, 2027" } (the year once, on the last day; on both when they differ) — "from … to …", "del … al …".
function dayRange(ev, lang) {
  const tz = ev.allDay ? "UTC" : "America/Chicago";
  const a = ev.allDay ? new Date(`${ev.startYmd}T12:00:00Z`) : new Date(ev.startMs);
  const b = ev.allDay ? new Date(`${ev.endYmd}T12:00:00Z`) : new Date(ev.endMs - 1);
  const f = (d, year) => new Intl.DateTimeFormat(LOCALES[lang] || "en-US", { weekday: "long", month: "long", day: "numeric", ...(year ? { year: "numeric" } : {}), timeZone: tz }).format(d);
  const sameYear = ev.startYmd.slice(0, 4) === ev.endYmd.slice(0, 4);
  const from = f(a, !sameYear), to = f(b, true);
  return lang === "es" ? { from: lowerFirst(from), to: lowerFirst(to) } : { from, to };
}

// An event's place for people, its platform's name only (never a link): "Online on Zoom".
function onlinePlatform(ev) {
  return ev.isOnline ? line(ev.platform) : "";
}

// Held at a place with a real address (committee.js heldAt's rule: a city, a state or a ZIP code; never one "to be
// announced", never an outside calendar's online event) → its place's text, else "".
function realAddress(ev) {
  if (!ev || ev.locationTba || !ev.location || ev.item?.extra?.scope === "online") return "";
  const p = eventPlace(String(ev.location), ev.item?.extra);
  const a = (p && p.address) || {};
  return a.addressLocality || a.addressRegion || a.postalCode ? line(ev.location) : "";
}

// Who organizes an event in the page's words: our committee by its name in the page's language (config/site.yml
// committee_es — "Comité de Grapevine y La Viña de NETA 65" — on a Spanish page), anyone else as the data names them.
// (eventOrganizer keeps the committee's one name, site.committee: its Organization in the structured data.)
function orgName(org, site, lang) {
  if (!org || !org.name) return "";
  return line(isCommitteeOrganizer(org, site) ? (lang !== "en" && site[`committee_${lang}`]) || org.name : org.name);
}

function lede(ev, kind, site, lang, opt = {}) {
  const org = opt.outside ? null : eventOrganizer(ev, site, lang);
  const ours = isCommitteeOrganizer(org, site);
  const named = SAYS_LANG.test(String(ev.title || "")) || (opt.series && opt.series.saysLang);
  // (an event that is over: "It was held in Spanish.", "It was organized by …")
  const was = !opt.series && ev.past ? "_past" : "";
  // (its language only when the data says Spanish — heldInSpanish —: one that does not say so may be in English, in
  // both languages — our literature table — or interpreted — an Area assembly —; the Language fact says the rest)
  const held = named || !kind.spanish ? "" : `evpage.lede.es${was}`;
  // (our committee: "It is organized by the NETA 65 Grapevine & La Viña Committee." — "Lo organiza el Comité …")
  // (round 37's fixer: the Area by its name, with its article in Spanish — "Lo organiza el Área 65 del Noreste de
  // Texas" —, as eventOrganizer names it for an assembly; any other organizer as the data writes it)
  const area = !ours && org && org.name && line(org.name) === line((lang !== "en" && site[`area_${lang}`]) || site.area);
  const base = { when: "", from: "", to: "", place: "", platform: "", recurrence: "", next: "", hybrid: "", held,
    org: orgName(org, site, lang),
    orgKey: ours ? `evpage.lede.org_ours${was}` : area ? `evpage.lede.org_area${was}` : `evpage.lede.org${was}` };
  if (opt.series) {
    const s = opt.series;
    const next = line(s.next.multiDay ? s.next.rangeLabel : s.next.allDay ? s.next.dateLabel : `${s.next.dateLabel}, ${s.next.timeLabel}`);
    // (in Spanish after "Próxima fecha:" its first letter small, as after any colon)
    return { ...base, key: "evpage.lede.series", recurrence: lowerFirst(line(s.recurrenceDay || s.recurrence)),
      next: lang === "es" ? lowerFirst(next) : next };
  }
  const range = ev.multiDay ? dayRange(ev, lang) : null;
  const when = range ? "" : whenWords(ev, lang);
  const R = range ? "_range" : "";
  if (ev.past) return { ...base, key: `evpage.lede.past${R}`, when, ...(range || {}) };
  const platform = onlinePlatform(ev);
  const place = ev.locationTba ? "" : line(ev.location);
  if (ev.locationTba) return { ...base, key: `evpage.lede.tba${R}`, when, ...(range || {}) };
  if (place) return { ...base, key: `evpage.lede.place${R}`, when, place, hybrid: platform, ...(range || {}) };
  // (a kind that says "online" itself — "an online AA meeting" —: "… on <its day>, on Google Meet", never "online … held
  // online"; over several days: "… held online on Zoom, from <its first day> to <its last>")
  const saysOnline = kind.kind === "online-meeting" || kind.kind === "magazine-workshop";
  if (ev.isOnline) {
    const key = !platform ? `evpage.lede.online_plain${R}` : saysOnline ? `evpage.lede.online_on${R}` : `evpage.lede.online${R}`;
    return { ...base, key, when, platform, ...(range || {}) };
  }
  return { ...base, key: `evpage.lede.date${R}`, when, ...(range || {}) };
}

function facts(ev, kind, site, lang, opt = {}) {
  const out = [];
  const outside = opt.outside;
  out.push({ k: "what", vKey: kind.label });
  out.push({ k: "when", v: line(opt.series ? opt.series.recurrence : ev.multiDay ? ev.rangeLabel : ev.shareWhen) });
  const where = ev.locationTba ? "" : line(ev.location);
  const platform = onlinePlatform(ev);
  if (ev.locationTba) out.push({ k: "where", vKey: "evpage.where_tba" });
  else if (where || ev.isOnline) {
    const addr = !ev.past && !opt.noMap ? realAddress(ev) : "";
    out.push({ k: "where", v: where, vOnline: ev.isOnline ? platform || "-" : "",
      map: addr ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(addr)}` : "" });
  }
  out.push({ k: "language", vKey: kind.spanish ? "evpage.lang_es" : "evpage.lang_en" });
  const org = outside ? null : eventOrganizer(ev, site, lang);
  // (the committee itself: its About page on this site — its Organization's url is the site's own home; anyone else:
  // its own site, when the data gives one)
  const ours = isCommitteeOrganizer(org, site);
  if (org && org.name) out.push({ k: "organizer", v: orgName(org, site, lang), href: ours ? lurl("/about/", lang) : org.url || "", ext: !ours && /^https?:/.test(org.url || "") });
  if (ours) out.push({ k: "cost", vKey: "evpage.free" });
  if (kind.who) out.push({ k: "who", vKey: kind.who });
  if (!opt.series && (ev.recurring || ev.seriesOf) && opt.recurrence) out.push({ k: "repeats", v: line(opt.recurrence) });
  // (who to write to: the event's own contact — La Viña's workshop: lveditorial@ —, else the committee's address for
  // the committee's own events; never ours for an event someone else holds)
  const mail = line(opt.contact || ev.contact || (org && isCommitteeOrganizer(org, site) ? site.contact_email : ""));
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) out.push({ k: "contact", v: mail, mail: true });
  return out;
}

/* ------------------------------------------------------------------ */
/*  Small cards                                                        */
/* ------------------------------------------------------------------ */
// (opt.same: a series' date among its series' dates — { title, location }: what every date shares is left out, so
// the list says each date's day and time, and only what differs)
function mini(ev, href, current = false, same = null) {
  const title = line(ev.title), location = line(ev.location);
  return {
    href, current, title: same && same.title === title ? "" : title, when: line(ev.multiDay ? ev.rangeLabel : ev.shareWhen),
    tile: { ...ev.tile }, location: same && same.location === location ? "" : location, locationTba: !!ev.locationTba,
    isOnline: !!ev.isOnline, platform: line(ev.platform), tone: eventTone(ev), tentative: !!ev.tentative,
    thumb: ev.flyer && ev.flyer.thumb ? ev.flyer.thumb : "",
  };
}
const miniOf = (p) => mini(p.ev, p.path);

function driveIdOf(url) {
  const m = String(url || "").match(/\/d\/([\w-]{10,})/) || String(url || "").match(/[?&]id=([\w-]{10,})/);
  return m ? m[1] : "";
}

function similarFlyers(c, ownView) {
  const pattern = c.kind.flyers;
  if (!pattern) return [];
  const own = driveIdOf(ownView);
  return (driveMatch(c.db.drive?.items || [], pattern, "flyers", FLYERS_SHOWN + 2) || [])
    .filter((it) => !own || driveIdOf(it.extra?.view_url || it.url) !== own)
    .slice(0, FLYERS_SHOWN)
    .map((it) => {
      const title = line(pickLang(it, "title", c.lang) || it.title);
      const f = flyerLinks(it.extra?.view_url || it.url) || {};
      return { title, titleLang: it.lang && it.lang !== c.lang && title === line(it.title) ? it.lang : "", view: f.view || "",
        preview: f.preview || "", thumb: f.thumb || "" };
    })
    .filter((f) => f.view);
}

/* ------------------------------------------------------------------ */
/*  The magazines of a month                                           */
/* ------------------------------------------------------------------ */
function monthOf(c, key) {
  if (!/^\d{4}-\d{2}$/.test(String(key || ""))) return null;
  const memo = c.months;
  const k = `${key}|${c.lang}`;
  if (!memo.has(k)) {
    let m = null;
    try {
      m = monthModel(key, c.db, c.full.carry || {}, c.site, c.lang, c.now);
    } catch {
      m = null;
    }
    const keys = Array.isArray(c.full.monthlyKeys) ? c.full.monthlyKeys : [];
    const issue = (x, pub) => (x && (x.theme || x.url) ? {
      pub, label: line(x.label), theme: line(x.theme), themeLang: pub === "lv" ? x.themeLang || "" : "",
      url: x.url || "", cover: x.cover || "", soon: !x.url,
    } : null);
    const gv = m ? issue(m.gv, "gv") : null, lv = m ? issue(m.lv, "lv") : null;
    memo.set(k, gv || lv || keys.includes(key) ? {
      key, current: keys[0] === key, toolkit: keys.includes(key) ? lurl(`/monthly/${key}/`, c.lang) : "", gv, lv,
    } : null);
  }
  return memo.get(k);
}

/* ------------------------------------------------------------------ */
/*  The models                                                         */
/* ------------------------------------------------------------------ */
function context(full, plan) {
  const db = full.db || {};
  const site = full.site || {};
  const albums = photoAlbums(db.drive?.items || [], "en").filter((a) => /display/.test(String(a.slug || "")));
  albums.sort((a, b) => String(b.newest || "").localeCompare(String(a.newest || "")));
  const pinned = announcementList(db.announcements?.items || [], new Date(plan.now)).find((a) => a._pinned);
  return { full, db, site, plan, now: new Date(plan.now), displays: albums[0] || null, bulletin: pinned ? pinned._anchor : "",
    months: new Map(), meetings: new Map(), decks: Array.isArray(full.presentations?.decks) ? full.presentations.decks : [] };
}

// The kind's presentation (event-pages.js eventKind): for an event held in Spanish, its Spanish deck (deckEs: La
// Viña's writing workshop → taller-de-escritura) while the site has it, else the kind's own; `lang`, the language the
// deck is written in (the card's "Presentation in English / in Spanish" badge where it isn't the page's).
function deckOf(c, kind, lang) {
  const byId = (id) => (id ? c.decks.find((x) => x && x.id === id) : null);
  const d = byId(kind.deckEs) || byId(kind.deck);
  if (!d) return null;
  const pick = (o) => (o && typeof o === "object" ? o[lang] || o.en || "" : String(o || ""));
  return { id: d.id, href: lurl(`/orientation/?present=${encodeURIComponent(d.id)}`, lang),
    card: lurl(`/orientation/#pres-${d.id}`, lang), title: line(pick(d.card?.title) || pick(d.title)),
    summary: line(pick(d.card?.summary)), minutes: Number(d.minutes) || 0, close: !!kind.deckClose,
    lang: d.lang === "es" ? "es" : "en" };
}

function crumbs(lang, hub) {
  const out = [{ key: "nav.home", href: lurl("/", lang) }, { key: "nav.events", href: lurl("/events/", lang) }];
  if (hub) out.push({ label: hub.title, href: hub.href });
  return out;
}

// The committee's next meeting in a language, once per build (its section on /meetings/ is its page): { when } — its
// day and time ("Wednesday, December 16 · 7:00 PM CST"), never its speaker's name — or null.
function nextMeeting(c, lang) {
  if (!c.meetings.has(lang)) {
    const nm = normalizeEvents([], c.site, lang, { monthsBack: 0, monthsAhead: 14, now: c.now }).find((e) => e.committee && !e.past);
    // (in Spanish inside a sentence: "…del comité: miércoles, 16 de diciembre")
    c.meetings.set(lang, nm ? { when: lang === "es" ? lowerFirst(line(nm.whenLabel)) : line(nm.whenLabel) } : null);
  }
  return c.meetings.get(lang);
}

// what a series' dates share (its title, its next date's place): left out of each date's small card
const sameOf = (h) => ({ title: line(h.series.title), location: line(h.next.location) });

function eventModel(c, p) {
  const lang = p.lang, ev = p.ev, kind = p.kind, site = c.site;
  const cl = { ...c, lang, ev, kind };
  const outside = kind.outside;
  const hub = p.hubPath ? c.plan.byPath[p.hubPath] : null;
  const series = hub ? { title: line(hub.series.title), href: hub.path } : null;
  const recurrence = hub ? hub.series.recurrence : ev.recurrence;
  const dates = hub ? hub.dates.map((d, i) => mini(d, hub.datePages[i] ? hub.datePages[i].path : p.target, d.anchor === ev.anchor,
    sameOf(hub))) : [];
  const nextSame = relatedEvents(c.plan, p, { sameKind: true, n: 1, site })[0] || null;
  const coming = relatedEvents(c.plan, p, { n: 4, site }).filter((x) => !nextSame || x.anchor !== nextSame.anchor).slice(0, 3);
  const pastSame = relatedEvents(c.plan, p, { sameKind: true, past: true, n: 3, site });
  return {
    mode: "event",
    // once it is over: its summary without how to join (withoutJoinDetails: the sentences that say it; withoutJoinValues:
    // those that give its own meeting ID or link bare) — never its body, which the page then leaves out
    summary: ev.past ? withoutJoinValues(withoutJoinDetails(ev.summary), [ev.meetingId, ev.online]).trim() : "",
    lede: lede(ev, kind, site, lang, { outside }),
    facts: facts(ev, kind, site, lang, { outside, recurrence, contact: hub ? hub.series.contact : "" }),
    banners: { past: !!ev.past, tentative: !!ev.tentative, partOf: series },
    crumbs: crumbs(lang, series),
    prep: { heading: ev.past ? "evpage.sec.more" : "evpage.sec.prep", deck: ev.past ? null : deckOf(c, kind, lang),
      bingo: bingoHref(ev, kind, lang), resources: resources(cl) },
    dates,
    nextSame: nextSame ? miniOf(nextSame) : null,
    coming: coming.map(miniOf),
    meeting: nextMeeting(c, lang),
    pastSame: pastSame.map(miniOf),
    flyers: similarFlyers(cl, ev.flyer ? ev.flyer.view : ""),
    flyer: null,
    month: monthOf(cl, ev.monthKey),
    latest: kind.kind === "online-meeting" ? "gv" : "",
  };
}

function hubModel(c, h) {
  const lang = h.lang, next = h.next, kind = h.kind, site = c.site;
  const cl = { ...c, lang, ev: next, kind, hub: true };
  const s = h.series;
  const coming = relatedEvents(c.plan, h, { n: 3, site });
  const flyer = next.flyer || null;
  return {
    mode: "series",
    lede: lede(next, kind, site, lang, { series: s }),
    facts: facts(next, kind, site, lang, { series: s, contact: s.contact, noMap: false }),
    banners: { past: false, tentative: false, partOf: null },
    crumbs: crumbs(lang, null),
    prep: { heading: "evpage.sec.prep", deck: deckOf(c, kind, lang), bingo: bingoHref(next, kind, lang), resources: resources(cl) },
    dates: h.dates.map((d, i) => mini(d, h.datePages[i] ? h.datePages[i].path : h.target, false, sameOf(h))),
    nextSame: null,
    coming: coming.map(miniOf),
    meeting: nextMeeting(c, lang),
    pastSame: [],
    flyers: similarFlyers(cl, flyer ? flyer.view : ""),
    flyer: flyer ? { view: flyer.view, preview: flyer.preview, thumb: flyer.thumb } : null,
    month: monthOf(cl, next.monthKey),
    latest: kind.kind === "online-meeting" ? "gv" : "",
  };
}

// a series' words for its page (no dates of it: the model lists those, as small cards)
function leanSeries(s) {
  return { key: s.key, title: line(s.title), summary: String(s.summary ?? "").trim(), recurrence: line(s.recurrence),
    recurrenceDay: line(s.recurrenceDay), time: line(s.time), contact: line(s.contact), saysLang: !!s.saysLang,
    join: { platform: line(s.join?.platform), url: s.join?.url || "", id: s.join?.id || "", idKey: s.join?.idKey || "" } };
}

const memo = new WeakMap();          // plan → [{ keys, data }]

/**
 * Every event page's and series page's entry, with its model (see the top of this file) → { pages, hubs }. One
 * answer per build: the plan is memoized (eventPagePlan), and so is this for that plan and the same data (db's
 * drive, pdfs, announcements, articles and audio_project, the presentations, the GVR / RLV 101 lessons).
 */
export function eventPageData(full) {
  const f = full || {};
  const db = f.db || {};
  const plan = eventPagePlan(db.events?.items, f.site, f.languages, { cancelled: db.events?.cancelled });
  const keys = [db.drive, db.pdfs, db.announcements, db.articles, db.audio_project, f.presentations, f.orientation, f.carry];
  const list = memo.get(plan) || [];
  const hit = list.find((m) => m.keys.every((k, i) => k === keys[i]));
  if (hit) return hit.data;
  const c = context(f, plan);
  const pages = plan.pages.map((p) => ({
    lang: p.lang, anchor: p.anchor, path: p.path, tier: p.tier, index: p.index, ld: p.ld, target: p.target,
    hubKey: p.hubKey, hubPath: p.hubPath, head: { ...p.head }, ev: p.ev, kind: p.kind, m: eventModel(c, p),
  }));
  const hubs = plan.hubs.map((h) => ({
    lang: h.lang, key: h.key, path: h.path, index: h.index, target: h.target, head: { ...h.head }, kind: h.kind,
    ev: h.next, series: leanSeries(h.series), m: hubModel(c, h),
  }));
  const data = { pages, hubs };
  list.push({ keys, data });
  memo.set(plan, list);
  return data;
}
