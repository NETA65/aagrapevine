// Area filters: access — the Accessibility page (src/pages/accessibility.njk).
//   axPhone(site, weekly, lang)  joining the Zoom meetings by phone (/accessibility/#phone), and which of our own
//                                meetings have no number to call (Google Meet: `online`)
//   axAudioTypes(shop, lang)     what the official stores' subscription descriptions say about audio
//   axAslPlaylist(videos, site, lang)  AA Grapevine's American Sign Language playlist on YouTube
//   platformOf(url)              where an online link is held: "Google Meet", "Zoom" … (the district report too)
// Nothing here copies meeting details: the IDs and passcodes come from `meeting:` (config/site.yml)
// and the weekly open meetings (db.weekly_open via cmWeeklyAll); the dial-in numbers and the
// callers' passcodes from `phone_access:` (config/site.yml).

import { TZ } from "../../eleventy.config.js"; // the site's time zone (config/site.yml site.timezone)

const digitsOf = (s) => String(s ?? "").replace(/\D+/g, "");
// a title that already names its language: "La Viña Open Meeting (in Spanish)", "… (en inglés)"
const LANG_NOTE = /\((?:in|en) (?:english|spanish|inglés|español)\)/i;
const isDigits = (s) => /^\d+$/.test(String(s ?? "").trim());

/** "+1 346 248 7799" → "+13462487799" (U.S. numbers only; anything else → ""). */
export function telOf(number) {
  const d = digitsOf(number);
  if (/^1\d{10}$/.test(d)) return "+" + d;
  if (/^\d{10}$/.test(d)) return "+1" + d;
  return "";
}

/** Zoom's "one tap mobile" link: dial, then the meeting ID and # after a pause; with a passcode,
 *  ",,,,*<passcode>#" (the form Zoom prints in its invitations). In a URL a raw "#" starts the
 *  fragment (Android's dialer drops everything after it), so it is written %23 (RFC 3966). */
export function oneTap(tel, meetingDigits, passcode) {
  if (!tel || !meetingDigits) return "";
  return `tel:${tel},,${meetingDigits}%23` + (isDigits(passcode) ? `,,,,*${String(passcode).trim()}%23` : "");
}

/** The passcode a caller types: the configured phone passcode, else the meeting passcode when it
 *  is numbers only (Zoom accepts it by phone as is), else "" (unknown: "ask the chair"). */
export function phonePasscode(configured, meetingPasscode) {
  if (isDigits(configured)) return String(configured).trim();
  if (isDigits(meetingPasscode)) return String(meetingPasscode).trim();
  return "";
}

/**
 * → { numbers: [{ display, tel, city }], meetings: [{ key, titles, notes, starts, id, digits, pass, askChair,
 *      details, call, callCity }], online: [{ platform, items: [{ key, title, details }] }], ok }
 * notes[i]: "(en inglés)" / "(in Spanish)" when titles[i] is a meeting held in the other language and
 * its title doesn't say so already (La Viña's English title does: "… (in Spanish)"), else "".
 * starts[i]: "November 5" / "5 de noviembre" while titles[i] (a weekly open meeting) has not started yet
 * (weeklyOpen's `starts`), else "".
 * meetings: the committee meeting while it is on Zoom (a meeting ID of digits), then one entry per Zoom ROOM of
 * the weekly open meetings (the Grapevine Weekly Open and La Viña's open meeting share one room: one entry, both
 * titles, the page language's meeting first — cmWeeklyAll's order).
 * online: our own meetings that callers cannot dial in to, one group per platform — the committee meeting on Google
 * Meet (a meeting code: "rva-tmst-vdb") and our online monthly series (config/site.yml recurring_events of ours with
 * an online_url and no place: the Grapevine Meeting) outside Zoom. A Google Meet room on a personal account has no
 * phone numbers, so the page says so instead of listing a number (details: the meeting's section on /meetings/).
 */
export function axPhone(site, weekly, lang = "en", t = (k) => k) {
  const pa = (site && site.phone_access) || {};
  const numbers = (Array.isArray(pa.numbers) ? pa.numbers : [])
    .map((n) => ({ display: String(n?.number || "").trim(), tel: telOf(n?.number), city: String((lang === "es" && n?.city_es) || n?.city || "").trim() }))
    .filter((n) => n.tel);
  const first = numbers[0];
  const meetings = [];
  const m = (site && site.meeting) || {};
  // the committee meeting only while callers can dial in: a Zoom ID (digits); a Google Meet code ("rva-tmst-vdb",
  // letters) has no number to call — the rule of committee.js meetingJoin (dialIn), not imported: this module needs
  // none of the build's packages
  const id = String(m.meeting_id ?? "").trim();
  const cDigits = /[a-z]/i.test(id) ? "" : digitsOf(id);
  if (cDigits) {
    const passcode = String(m.passcode ?? "").trim();
    const pass = phonePasscode(pa.committee?.phone_passcode, passcode);
    meetings.push({
      key: "committee", titles: [t("nav.meeting")], notes: [""], starts: [""], id, digits: cDigits, pass,
      askChair: !pass && !!passcode, details: "/meetings/#committee-meeting",
      call: first ? oneTap(first.tel, cDigits, pass) : "", callCity: first ? first.city : "",
    });
  }
  const rooms = new Map();
  for (const w of Array.isArray(weekly) ? weekly : []) {
    if (!w || !w.zoomDigits) continue;
    const k = w.zoomDigits + "|" + (w.passcode || "");
    if (!rooms.has(k)) {
      const pass = phonePasscode(pa.weekly_open?.phone_passcode, w.passcode);
      rooms.set(k, {
        key: "weekly-" + w.zoomDigits, titles: [], notes: [], starts: [], id: w.zoomId || w.zoomDigits, digits: w.zoomDigits, pass,
        askChair: false, askHost: !pass && !!w.passcode, details: "/meetings/#weekly-open",
        call: first ? oneTap(first.tel, w.zoomDigits, pass) : "", callCity: first ? first.city : "",
      });
    }
    if (w.title) {
      const r = rooms.get(k);
      const other = (w.lang === "en" || w.lang === "es") && w.lang !== lang && !LANG_NOTE.test(w.title);
      r.titles.push(w.title);
      r.notes.push(other ? t(w.lang === "en" ? "access.in_english" : "access.in_spanish") : "");
      r.starts.push(startsLabel(w.starts, lang));
    }
  }
  meetings.push(...rooms.values());
  // our own meetings with no number to call (see above): the committee meeting off Zoom, then our online series
  const online = [];
  const add = (platform, item) => {
    let g = online.find((x) => x.platform === platform);
    if (!g) online.push((g = { platform, items: [] }));
    g.items.push(item);
  };
  const cPlatform = String(m.platform ?? "").trim() || platformOf(m.online_url || m.zoom_url) || "Zoom";
  if (Object.keys(m).length && !cDigits && cPlatform !== "Zoom" && (m.online_url || m.zoom_url || id)) {
    add(cPlatform, { key: "committee", title: t("nav.meeting"), details: "/meetings/#committee-meeting" });
  }
  for (const r of Array.isArray(site && site.recurring_events) ? site.recurring_events : []) {
    const host = String((r && r.host) || "neta").trim().toLowerCase();
    const url = String((r && r.online_url) || "").trim();
    if (!r || typeof r !== "object" || r.enabled === false || host !== "neta" || !url || String(r.location || "").trim()) continue;
    const platform = platformOf(url);
    if (!platform || platform === "Zoom") continue;      // (a Zoom room of ours would have a number: not listed here)
    const title = String((lang === "es" && r.title_es) || r.title || "").trim();
    const page = String(r.url || "").trim();
    if (title) add(platform, { key: String(r.key || title), title, details: /^\/[^/]/.test(page) ? page : "/meetings/" });
  }
  return { numbers, meetings, online, ok: numbers.length > 0 && meetings.length > 0 };
}

// Where an online link is held, in the pages' words ("https://meet.google.com/rva-tmst-vdb" → "Google Meet"); ""
// for a link it does not know — the sync's names for the same hosts (events_external.py PLATFORM_HOSTS)
const PLATFORM_HOSTS = [["zoom.us", "Zoom"], ["meet.google.com", "Google Meet"], ["teams.microsoft.com", "Microsoft Teams"],
  ["teams.live.com", "Microsoft Teams"], ["webex.com", "Webex"], ["gotomeeting.com", "GoToMeeting"], ["skype.com", "Skype"],
  ["whereby.com", "Whereby"], ["jitsi", "Jitsi"]];
export function platformOf(url) {
  let host = "";
  try { host = new URL(String(url ?? "")).hostname.toLowerCase(); } catch (e) { return ""; }
  const hit = PLATFORM_HOSTS.find(([h]) => host.includes(h));
  return hit ? hit[1] : "";
}

/** A first meeting that is still ahead ({ iso }) → "November 5" / "5 de noviembre" (Central time). */
function startsLabel(starts, lang) {
  const d = starts && starts.iso ? new Date(starts.iso) : null;
  if (!d || Number.isNaN(d.getTime())) return "";
  try {
    return new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", { month: "long", day: "numeric", timeZone: TZ }).format(d);
  } catch (e) { return ""; }
}

const AUDIO_RE = /\baudio|\bp[oó]dcast/i; // "audio", "audiobook(s)", "audiolibro(s)", "podcast", "pódcast"
/**
 * The official stores' descriptions of their subscription types (db.shop.types, from
 * scripts/sync/shop.py) that mention audio, in the page language:
 * → { types: n (how many descriptions there are), audio: [{ pub, type, text }] }.
 * The page says what they say — or that none of them mentions audio — and never more.
 */
export function axAudioTypes(shop, lang = "en") {
  const out = { types: 0, audio: [] };
  const types = (shop && shop.types) || {};
  for (const pub of ["gv", "lv"]) {
    for (const [type, desc] of Object.entries(types[pub] || {})) {
      const text = String((desc && (desc[lang] || desc.en || desc.es)) || "").trim();
      if (!text) continue;
      out.types++;
      if (AUDIO_RE.test(text)) out.audio.push({ pub, type, text });
    }
  }
  return out;
}

/** AA Grapevine's "American Sign Language" playlist (db.videos.playlists) → { url, count, title }
 *  with the verified link in config (links.asl_playlist) as the fallback. */
export function axAslPlaylist(videos, site, lang = "en") {
  const lists = (videos && Array.isArray(videos.playlists)) ? videos.playlists : [];
  const p = lists.find((x) => /american sign language|\bASL\b/i.test(String(x?.title || "")));
  const fallback = (site && site.links && site.links.asl_playlist) || "";
  if (!p) return fallback ? { url: fallback, count: 0, title: "" } : null;
  const title = (p.i18n && p.i18n.title && p.i18n.title[lang]) || p.title || "";
  return { url: p.url || fallback, count: Number(p.count) || 0, title };
}

export default function (eleventyConfig, helpers = {}) {
  const tr = (lang) => (k) => (helpers.translateKey ? helpers.translateKey(k, lang) : k);
  eleventyConfig.addFilter("axPhone", (site, weekly, lang) => axPhone(site, weekly, lang, tr(lang)));
  eleventyConfig.addFilter("axAudioTypes", (shop, lang) => axAudioTypes(shop, lang));
  eleventyConfig.addFilter("axAslPlaylist", (videos, site, lang) => axAslPlaylist(videos, site, lang));
}
