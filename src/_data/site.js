// Loads config/site.yml and exposes it as `site` in every template.
import fs from "node:fs";
import * as yaml from "js-yaml";
// the site's time zone as the build reads it (eleventy.config.js: site.timezone, America/Chicago when it is not one)
import { TZ } from "../../eleventy.config.js";

export default function () {
  const cfg = yaml.load(fs.readFileSync("config/site.yml", "utf8"));
  const s = cfg.site || {};
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
    meeting: cfg.meeting || {},
    // The monthly series (CityWide booth …): /monthly/ works out months past events.json's
    // `months_ahead` dates from these rules (eleventy/filters/monthly.js).
    // (a single event written without the leading "- " counts too, as in build_data.recurring_specs)
    recurring_events: Array.isArray(cfg.recurring_events) ? cfg.recurring_events
      : cfg.recurring_events && typeof cfg.recurring_events === "object" ? [cfg.recurring_events] : [],
    drive: cfg.drive || {},
    sources: cfg.sources || {},
    links: cfg.links || {},
    // Zoom dial-in numbers + callers' passcodes for /accessibility/#phone (eleventy/filters/access.js)
    phone_access: cfg.phone_access || {},
    digest: cfg.digest || {},
    // La Viña's weekly open meeting (the data itself comes from data/site/weekly_open.json); the page
    // reads `flyer_match` here — the "View flyer" link on /meetings/#weekly-open
    lavina_weekly_open: cfg.lavina_weekly_open || {},
    // Build timestamp (UTC ISO) — shown as "Last updated" in the footer.
    built: new Date().toISOString(),
    // No link to the Drive ROOT on purpose: it can hold private files (e.g. sign-up response sheets).
    // Pages link the current Panel folder instead (eleventy/filters/committee.js → driveInfo).
  };
}
