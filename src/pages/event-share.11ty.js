// One small page per event of /events/ (and /es/events/): /events/<its card's anchor>/ — the address its card's
// Share button sends (events.njk). The apps that show a link's preview (WhatsApp, Facebook, iMessage …) read the
// event here: its title, its day and place, and its flyer as the picture (a Drive flyer's, an outside calendar's
// image — else the committee's card). A person who opens the link goes straight on to the event's card on
// /events/ (JavaScript; without it, a link to it). There is no meta refresh on purpose: Facebook follows one and
// would show the Events page's preview instead. A date that has passed keeps its page while the event is still in
// data/site/events.json (a link shared earlier still works): a one-off event's leads to its row under "Past
// events", a monthly date's to the top of /events/ (its date has no row there). Committee meetings have none:
// their page is /meetings/. Kept out of the sitemap, the search index and page lists (noindex: the event's card is
// the page to find).
import { normalizeEvents } from "../../eleventy/filters/committee.js";

const EMPTY = !!process.env.COMMITTEE_EMPTY;
// A Drive file's id in its link ("…/file/d/<id>/view", "…open?id=<id>"): Google's picture of it, 1200 px wide, is
// the preview's picture (the card's own is 320 px — too small for a preview).
const DRIVE_ID = /drive\.google\.com\/(?:file\/d\/|open\?(?:[^#]*&)?id=|uc\?(?:[^#]*&)?id=)([\w-]{10,})/;

/** The address of an event's share page in a language: "/events/<anchor>/" ("/es/events/<anchor>/"). */
export function eventSharePath(ev, lang) {
  return `${lang && lang !== "en" ? "/" + lang : ""}/events/${ev.anchor}/`;
}

/** The share picture of an event (its flyer), for base.njk-style meta: an address, or "" (the committee's card). */
export function eventSharePicture(ev) {
  const f = ev && ev.flyer;
  if (!f) return "";
  const id = (String(f.view || "").match(DRIVE_ID) || [])[1];
  return id ? `https://lh3.googleusercontent.com/d/${id}=w1200` : String(f.thumb || "");
}

/**
 * The share pages: every event /events/ shows a card or a row for (normalizeEvents — the same list, in each
 * language), but the committee meetings → [{ lang, ev, path, target }]. `target`: where the page sends people —
 * the card (/events/#anchor), or the page's top for a monthly date that has passed. An anchor met twice (it never
 * should be: it is an id on /events/) keeps its first event, so no two pages share an address.
 */
export function eventSharePages(items, site, langs = ["en", "es"]) {
  const out = [];
  for (const lang of langs) {
    const seen = new Set();
    for (const ev of EMPTY ? [] : normalizeEvents(items || [], site, lang)) {
      if (!ev || ev.committee || !/^[a-z0-9][a-z0-9-]*$/.test(ev.anchor || "") || seen.has(ev.anchor)) continue;
      seen.add(ev.anchor);
      const events = lang === "en" ? "/events/" : `/${lang}/events/`;
      out.push({ lang, ev, path: eventSharePath(ev, lang), target: events + (ev.past && ev.recurring ? "" : "#" + ev.anchor) });
    }
  }
  return out;
}

export const data = {
  pagination: {
    data: "db.events.items", size: 1, alias: "share",
    before: (items, full) => eventSharePages(items, full.site, full.languages),
  },
  permalink: (data) => data.share.path + "index.html",
  layout: false,
  sitemap: false,
  eleventyExcludeFromCollections: true,
};

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const line = (s) => String(s ?? "").replace(/\s+/g, " ").trim();
const clip = (s, n) => (s.length > n ? s.slice(0, n).replace(/\s+\S*$/, "") + "…" : s);

export function render(data) {
  const { share, site } = data;
  const { ev, lang } = share;
  const t = (key, vars) => this.t(key, lang, vars);
  const siteTitle = line((lang !== "en" && site[`title_${lang}`]) || site.title);
  const self = this.siteUrl(share.path, site);
  const when = line(ev.multiDay ? ev.rangeLabel : ev.shareWhen);
  const place = line(ev.locationTba ? "" : ev.location) || (ev.isOnline ? line(ev.platform ? t("committee.events.online_on", { platform: ev.platform }) : t("committee.events.online")) : "");
  const where = [when, place].filter(Boolean).join(" · ");
  const desc = clip([where, line(ev.summary)].filter(Boolean).join(" — "), 200);
  const title = line(ev.title);
  const picture = this.shareImage(eventSharePicture(ev), site);
  const card = this.siteUrl(lang === "es" ? "/assets/img/og-default-es.png?v=2" : "/assets/img/og-default.png?v=2", site);
  const alt = picture ? t("committee.events.flyer_alt", { title }) : `${siteTitle} — ${t("site.tagline")}`;
  const meta = [
    `<meta property="og:type" content="website">`,
    `<meta property="og:site_name" content="${esc(siteTitle)} — NETA 65">`,
    `<meta property="og:title" content="${esc(title)}">`,
    `<meta property="og:description" content="${esc(desc)}">`,
    `<meta property="og:url" content="${esc(self)}">`,
    `<meta property="og:image" content="${esc(picture ? picture.url : card)}">`,
    ...(picture ? [] : [`<meta property="og:image:width" content="1200">`, `<meta property="og:image:height" content="630">`]),
    `<meta property="og:image:alt" content="${esc(alt)}">`,
    `<meta property="og:locale" content="${lang === "es" ? "es_US" : "en_US"}">`,
    `<meta name="twitter:card" content="summary_large_image">`,
    `<meta name="twitter:image" content="${esc(picture ? picture.url : card)}">`,
    `<meta name="twitter:image:alt" content="${esc(alt)}">`,
  ];
  // the base plugin does not rewrite script text, so the url filter adds the path prefix there; a ?query the link
  // came with (utm=…) goes before the #card
  const cut = share.target.indexOf("#");
  const js = (s) => JSON.stringify(s).replace(/</g, "\\u003c");
  const go = cut < 0 ? `${js(this.url(share.target))} + location.search`
    : `${js(this.url(share.target.slice(0, cut)))} + location.search + ${js(share.target.slice(cut))}`;
  return `<!doctype html>
<html lang="${esc(lang)}">
<head>
<meta charset="utf-8">
<script>location.replace(${go});</script>
<meta name="robots" content="noindex">
<link rel="canonical" href="${esc(self)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/favicon.ico" sizes="any">
<title>${esc(title)} · ${esc(t("nav.events"))} — NETA 65</title>
<meta name="description" content="${esc(desc)}">
${meta.join("\n")}
<style>
  :root { color-scheme: light dark; --paper: #fbf8f2; --ink: #1d1a26; --muted: #57526a; --link: #0a5fa8; }
  @media (prefers-color-scheme: dark) { :root { --paper: #121019; --ink: #eeeaf6; --muted: #b3adc4; --link: #8cc2f2; } }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; box-sizing: border-box;
         font: 17px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background: var(--paper); color: var(--ink); }
  main { max-width: 34rem; text-align: center; overflow-wrap: anywhere; }
  h1 { font-family: Georgia, "Times New Roman", serif; font-size: 1.6rem; margin: 0 0 .5rem; }
  p { margin: .5rem 0; color: var(--muted); }
  img { display: block; max-width: 100%; max-height: 60vh; margin: 1rem auto; border-radius: 8px; }
  a { color: var(--link); font-weight: 600; }
</style>
</head>
<body>
<main>
  <h1>${esc(title)}</h1>
  ${where ? `<p>${esc(where)}</p>` : ""}
  ${picture ? `<img src="${esc(picture.url)}" alt="${esc(alt)}" referrerpolicy="no-referrer">` : ""}
  <p><a href="${esc(share.target)}">${esc(t("committee.events.share_go"))} →</a></p>
</main>
</body>
</html>
`;
}
