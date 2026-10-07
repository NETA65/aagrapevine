// All synced content (written by scripts/sync/build_data.py into data/site/*.json).
// Templates use e.g. db.videos.items, db.status.sources …
//
// Link safety: every URL field is passed through safeUrl() (eleventy.config.js) here, once, so
// no page, filter or JSON index can print a "javascript:" link or a broken "www.example.org"
// one. Hand-edited content is the realistic source (content/events/*.md `url` / `online_url` / `flyer`, content/bulletin/*.md `url` / `image`).
// "www.x.org" and "zoom.us/j/1" are repaired to https://…; unusable values become "" (the
// templates hide empty links). An item whose own `url` is unusable points to its anchor on our
// page (committee event / bulletin post) or is left out. Every repaired or dropped value is
// written to the build log and listed in db.status.link_problems [{where, field, value, fixed}].
// A value that had to be hidden, an item left out, or any other change is a build warning
// (eleventy/build-warnings.js: the Code check fails on it). A repair that only adds the
// forgotten "https://" (or "https:" before "//host") loses nothing — the link works, and the
// committee's guides say such a link is fine — so it stays a plain log line ("[links] note: …").
import fs from "node:fs";
import path from "node:path";
import { safeUrl } from "../../eleventy.config.js";
import { buildWarning } from "../../eleventy/build-warnings.js";

// "spotlight" = the published-writers file (Grapevine / La Viña stories by Texas writers, Area 65
// first — docs/DATA_SCHEMA.md → "spotlight.json"), read by the home page, /published/, /read/,
// /contribute/ and the search index as db.spotlight. Its links (url, image, extra.issue_url) get the
// same cleaning as every other file here. Without the file, db.spotlight is { updated: null, items: [] }.
// "shop" = the official stores' Book of the Month offers, bulk-book discounts and subscription prices
// (scripts/sync/shop.py → build_data; docs/DATA_SCHEMA.md → "shop.json"): db.shop.botm, db.shop.bulk_discounts,
// db.shop.subscriptions, db.shop.types. It has no `items` list of its own (db.js adds an empty one).
// "meetings" = Grapevine meetings (TSML type "GR") of the intergroups in and next to our Area
// (scripts/sync/meetings.py → build_data; docs/DATA_SCHEMA.md → "meetings.json"): db.meetings.items,
// db.meetings.groups, db.meetings.sources, db.meetings.type_labels.
// "audio_project" = the record-your-story phone lines of Grapevine (Audio Project) and La Viña
// ("Graba tu historia") as their official pages give them (scripts/sync/audio_project.py → build_data;
// docs/DATA_SCHEMA.md → "audio_project.json"): db.audio_project.gv / .lv (null when unknown), read by
// /contribute/#record. No `items` list of its own (an empty one is added here).
// "quote" = Grapevine's Daily Quote and La Viña's Cita Diaria as published on their home pages
// (scripts/sync/quote.py → build_data; docs/DATA_SCHEMA.md → "quote.json"): db.quote.items (the newest
// quote of each, Grapevine first; url + signup_url cleaned below), read by the home page. (The past days'
// quotes stay in data/raw/quote.json — a guard for the sync, not shown anywhere.)
// "writers_archive" = the Texas writers archive: every story by a Texas writer in the magazines' online
// archives (the owner's CSV files in content/archive/) plus every captured Texas story, any age
// (scripts/sync/build_data.py; docs/DATA_SCHEMA.md → "writers_archive.json"): db.writers_archive.items, read by
// /published/#archive, its JSON (/published/texas-archive.json), the home page's archive line and the search
// index. Without the file the archive is simply left out.
// WRITERS_ARCHIVE=tests/fixtures/writers_archive/site_sample.json reads another file instead (the sample: tests, previews).
const ARCHIVE_FILE = process.env.WRITERS_ARCHIVE || "";
// SITE_DATA=<folder> reads every file from that folder instead of data/site (tests: a build that must not depend on
// the day's data; a file missing there is an empty list, as here).
const DATA_DIR = process.env.SITE_DATA || path.join("data", "site");
const FILES = [
  "episodes", "videos", "instagram", "articles", "pdfs", "drive", "events",
  "announcements", "editorial", "weekly_open", "whatsnew", "status",
  "spotlight", "shop", "meetings", "audio_project", "quote", "writers_archive",
];

// Field names that hold a link or an image address: url, image, extra.online_url, extra.thumbs[],
// referrers[].url, shows[].apple, issues[].cover, profiles.gv.avatar …
// Only string values are touched (extra.is_image is a boolean); extra.host (a bare host name),
// extra.file (a repository path) and extra.link_texts do not match.
const URL_KEY = /(?:^|_)(?:url|link|image|website|thumbs?|cover|avatar|feed|web|hub|apple|spotify|amazon|permalink)$/i;

// The problems that are only a forgotten scheme (each problem object; see the header): a log line, not a warning.
const schemeOnly = new WeakSet();

function fixOne(value, field, where, problems) {
  const fixed = safeUrl(value);
  const v = value.trim();
  if (fixed !== v) {
    const pr = { where, field, value: value.slice(0, 160), fixed };
    if (fixed && (fixed === "https://" + v || fixed === "https:" + v)) schemeOnly.add(pr);
    problems.push(pr);
  }
  return fixed;
}

function cleanLinks(node, key, file, where, problems) {
  if (Array.isArray(node)) {
    node.forEach((v, i) => {
      if (typeof v === "string") { if (URL_KEY.test(key)) node[i] = fixOne(v, key, where, problems); }
      else if (v && typeof v === "object") cleanLinks(v, key, file, v.id ? `${file} ${v.id}` : where, problems);
    });
    return;
  }
  for (const [k, v] of Object.entries(node)) {
    if (k === "i18n") continue; // translated text only
    if (typeof v === "string") { if (URL_KEY.test(k)) node[k] = fixOne(v, k, where, problems); }
    else if (v && typeof v === "object") cleanLinks(v, k, file, !Array.isArray(v) && v.id ? `${file} ${v.id}` : where, problems);
  }
}

export default function () {
  const out = {};
  const problems = [];
  for (const name of FILES) {
    const p = name === "writers_archive" && ARCHIVE_FILE ? ARCHIVE_FILE : path.join(DATA_DIR, `${name}.json`);
    let data = { updated: null, items: [] };
    try {
      if (fs.existsSync(p)) data = JSON.parse(fs.readFileSync(p, "utf8"));
    } catch (e) {
      console.warn(`[content] could not read ${p}: ${e.message}`);
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) data = { updated: null, items: [] };
    if (!Array.isArray(data.items)) data.items = [];
    const hadUrl = new Set(data.items.filter((it) => it && typeof it.url === "string" && it.url.trim()));
    cleanLinks(data, "", `${name}.json`, `${name}.json`, problems);
    // An item whose own link was unusable: a committee event / bulletin post falls back to its
    // anchor on our page (as if no url had been given); anything else would be a card that goes
    // nowhere, so it is left out (it is listed in the log and in link_problems).
    // The bulletin was /announcements/ until 2026-09 (announcements-redirect.njk keeps that address
    // working): a link to it written before then goes straight to /bulletin/ instead.
    data.items = data.items.filter((it) => {
      if (it && typeof it.url === "string" && /^\/announcements\/(?=#|$)/.test(it.url)) it.url = "/bulletin/" + it.url.slice(15);
      if (!hadUrl.has(it) || it.url) return true;
      const slug = it.extra && typeof it.extra.slug === "string" ? encodeURIComponent(it.extra.slug) : "";
      if (slug && it.kind === "event") { it.url = `/events/#${slug}`; return true; }
      if (slug && it.kind === "announcement") { it.url = `/bulletin/#${slug}`; return true; }
      problems.push({ where: `${name}.json ${it.id || ""}`.trim(), field: "item", value: "(left out: no usable link)", fixed: "" });
      return false;
    });
    out[name] = data;
  }
  // Build warnings (eleventy/build-warnings.js: the Code check fails on them; Website update lists them) — all but
  // the scheme-only repairs, which are plain log lines.
  const warned = problems.filter((pr) => !schemeOnly.has(pr));
  if (warned.length) buildWarning("links", `${warned.length} link value(s) in data/site repaired or hidden:`);
  // The same item is often in two files (events.json + whatsnew.json): log each value once.
  for (const [list, say] of [[warned, (line) => buildWarning("links", line)],
                             [problems.filter((pr) => schemeOnly.has(pr)), (line) => console.log(`[links] note: ${line}`)]]) {
    const seen = new Set();
    for (const pr of list) {
      const k = pr.field === "item" ? pr.where : pr.field + "\u0000" + pr.value;
      if (seen.has(k)) continue;
      seen.add(k);
      if (seen.size > 25) { say("… more in db.status.link_problems"); break; }
      say(pr.field === "item" ? `${pr.where}: left out — its link is not usable`
        : pr.fixed ? `${pr.where}: ${pr.field} ${JSON.stringify(pr.value)} → ${pr.fixed}`
        : `${pr.where}: ${pr.field} ${JSON.stringify(pr.value)} is not a usable link — hidden`);
    }
  }
  out.status.link_problems = problems;
  return out;
}
