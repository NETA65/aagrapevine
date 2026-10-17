// The booth display (the About page's "Booth display": the show that plays by itself at the committee's Grapevine /
// La Viña table) — the owner's files, read and checked once per build, exposed as `booth` in every template:
//   booth.csv       { file, found, rows, items, problems }   content/booth/booth.csv — every row checked (SPEC §1.2,
//                                                             §4) and shaped as an item of /about/booth.json; a row
//                                                             with a mistake is left out and named in `problems`
//   booth.drive     { file, found, updated, items, collections, problems }   data/site/booth.json — the Drive panel
//                                                             folder's booth\ files (the daily sync), each with the copy
//                                                             the deploy saved (.cache/booth-media/manifest.json —
//                                                             without it: pictures online only, videos and sound files
//                                                             left out); no file → no Drive items
//   booth.manifest  { file, found, built, files }            the saved copies (scripts/build/booth-media.mjs)
//   booth.config    { defaults, max_file_mb, max_total_mb }  config/site.yml `booth:` — the player's starting
//                                                             settings ({ event: { en, es }, lang, sound })
//   booth.base      the base path of the site's files ("/aagrapevine/" on GitHub Pages)
//   booth.items     the CSV's and the Drive folder's items, in that order
//   booth.problems  [{ where, en, es }] — all of the above's (the player's Settings → Items lists them)
// The page src/pages/booth-json.11ty.js adds the live items of the day (events, daily quotes, videos, podcast, story
// themes, prices, Books of the Month, meetings, bulletin) and writes /about/booth.json. Reading, checking and
// shaping: eleventy/filters/booth.js loadBooth (content/booth/README.md is the owner's guide to the CSV).
// Problems never stop the build — they are written to the log; the Code check stops on the CSV's instead
// (tests/test_booth_csv.py: the real file must have none).
// For tests and previews, other files: BOOTH_CSV=…/x.csv, BOOTH_DRIVE=…/booth.json, BOOTH_MANIFEST=…/manifest.json.
// (Only the default export here: with a named one, Eleventy would hand the pages the module object instead.)
import fs from "node:fs";
import * as yaml from "js-yaml";
import siteData from "./site.js";
import { loadBooth } from "../../eleventy/filters/booth.js";

export default function () {
  // config/site.yml as the site reads it: its address (SITE_URL from the GitHub Action wins) through src/_data/site.js,
  // the `booth:` section from the same file
  let cfg = {};
  try {
    cfg = yaml.load(fs.readFileSync("config/site.yml", "utf8")) || {};
  } catch (e) {
    console.warn(`[booth] config/site.yml could not be read: ${e.message}`);
  }
  const booth = loadBooth({
    csv: process.env.BOOTH_CSV || "content/booth/booth.csv",
    drive: process.env.BOOTH_DRIVE || "data/site/booth.json",
    manifest: process.env.BOOTH_MANIFEST || ".cache/booth-media/manifest.json",
    config: cfg && typeof cfg === "object" ? cfg.booth : null,
    site: siteData(),
  });
  if (booth.problems.length) {
    const lines = booth.problems.slice(0, 40).map((p) => `${p.where}: ${p.en}`);
    if (booth.problems.length > 40) lines.push(`… and ${booth.problems.length - 40} more (Settings → Items in the player lists them all)`);
    console.warn(`[booth] ${booth.problems.length} problem(s) — left out of the booth display:\n  ${lines.join("\n  ")}`);
  }
  return booth;
}
