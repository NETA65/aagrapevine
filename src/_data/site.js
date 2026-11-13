// Loads config/site.yml and exposes it as `site` in every template.
import fs from "node:fs";
import * as yaml from "js-yaml";
// the site's time zone as the build reads it (eleventy.config.js: site.timezone, America/Chicago when it is not one)
import { TZ } from "../../eleventy.config.js";

export default function () {
  const cfg = yaml.load(fs.readFileSync("config/site.yml", "utf8"));
  const s = cfg.site || {};
  const m = cfg.meeting && typeof cfg.meeting === "object" ? cfg.meeting : {};
  return {
    ...s,
    // the zone every page and the browser's scripts use (window.SITE.tz): a name that is not a time zone, or none,
    // is America/Chicago here as in the build
    timezone: TZ,
    // The GitHub Action exports SITE_URL from actions/configure-pages (custom domains, renames)
    url: String(process.env.SITE_URL || s.url || "").replace(/\/+$/, ""),
    // The repository (the Status page's links to its Actions tab and content/events/README.md): on GitHub
    // the one the build runs in (a rename or a move to another account is picked up by itself), else config.
    repository: String(process.env.GITHUB_REPOSITORY
      ? `${process.env.GITHUB_SERVER_URL || "https://github.com"}/${process.env.GITHUB_REPOSITORY}`
      : s.repository || "").replace(/\/+$/, ""),
    // The committee meeting. `platform` names where it is held in the pages' words ("Join on Google Meet", "on
    // Google Meet"): "Zoom" when the setting is left out; `online_url` is the link to join (an older `zoom_url` still
    // counts: the pages read online_url only); `note` / `note_es` is the line about who may come (/meetings/, the
    // calendar entries). No `meeting:` section at all stays {} (the pages and decks then show no rule of theirs).
    meeting: Object.keys(m).length
      ? { ...m, platform: String(m.platform ?? "").trim() || "Zoom", online_url: String(m.online_url || m.zoom_url || "").trim() }
      : {},
    // The monthly series (CityWide booth …): /monthly/ works out months past events.json's
    // dates from these rules (eleventy/filters/monthly.js).
    // (a single event written without the leading "- " counts too, as in build_data.recurring_specs)
    recurring_events: Array.isArray(cfg.recurring_events) ? cfg.recurring_events
      : cfg.recurring_events && typeof cfg.recurring_events === "object" ? [cfg.recurring_events] : [],
    // The last day the committee meeting and each monthly event are listed (/events/, /events.ics, the event share
    // pages): every date through this day's month, at least this month and the 12 after it — "2028-12-31", the end of
    // Panel 77 (eleventy/filters/committee.js meetingMonthsAhead; the sync's twin: scripts/sync/meeting.py
    // window_months). As written: a "YYYY-MM-DD" text, or the Date an unquoted YAML date becomes; "" when it is left
    // out (then this month and the 12 after it, as before round 30).
    events_until: cfg.events_until ?? "",
    drive: cfg.drive || {},
    sources: cfg.sources || {},
    links: cfg.links || {},
    // Zoom dial-in numbers + callers' passcodes for /accessibility/#phone (eleventy/filters/access.js): the weekly
    // open meetings' (the committee's Google Meet room has none)
    phone_access: cfg.phone_access || {},
    digest: cfg.digest || {},
    // La Viña's weekly open meeting (the data itself comes from data/site/weekly_open.json); the page
    // reads `flyer_match` here — the "View flyer" link on /meetings/#weekly-open
    lavina_weekly_open: cfg.lavina_weekly_open || {},
    // …and the Grapevine Weekly Open's (its data is read from aagrapevine.org; its full join link, `zoom_url`, is the
    // sync's — data/site/weekly_open.json): `flyer_match`, the "View flyer" link on its card
    grapevine_weekly_open: cfg.grapevine_weekly_open || {},
    // The Grapevine meetings' offices (/meetings/#grapevine-meetings, eleventy/filters/committee.js gvMeetings):
    // without data/site/meetings.json the page still names "Our Area" (area_label) and links each office's
    // own site (feeds[].name / site) for people to look there.
    meetings: cfg.meetings || {},
    // The published-writers spotlight: the home page's window (home_days) and the /published/ choices (list_days)
    spotlight: cfg.spotlight || {},
    // Offers the official stores announced (free shipping …): /shop/#offers and the monthly toolkit, each in its own
    // days (eleventy/filters/shop.js shopOffers); a block with a mistake is left out there, never here
    store_offers: cfg.store_offers ?? [],
    // Build timestamp (UTC ISO) — shown as "Last updated" in the footer.
    built: new Date().toISOString(),
    // No link to the Drive ROOT on purpose: it can hold private files (e.g. sign-up response sheets).
    // Pages link the current Panel folder instead (eleventy/filters/committee.js → driveInfo).
  };
}
