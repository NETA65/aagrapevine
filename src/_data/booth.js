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
//   booth.config    { defaults, max_file_mb, max_total_mb, photos }  config/site.yml `booth:` — the player's
//                                                             starting settings ({ event: { en, es }, lang, sound,
//                                                             galleryEvery }) and booth.photos (which of the Photos
//                                                             page's albums play, how many pictures a day)
//   booth.base      the base path of the site's files ("/aagrapevine/" on GitHub Pages)
//   booth.items     the CSV's and the Drive folder's items, in that order
//   booth.problems  [{ where, en, es }] — all of the above's (the player's Settings → Slides lists them)
// The page src/pages/booth-json.11ty.js adds the live items of the day (events, daily quotes, videos, podcast, story
// themes, prices, Books of the Month, meetings, bulletin, the Photos page's pictures) and writes /about/booth.json.
// Reading, checking and shaping: eleventy/filters/booth.js loadBooth (content/booth/README.md is the owner's guide to
// the CSV).
// Problems never stop the build — they are written to the log (eleventy/filters/booth.js logProblems; the live
// items' when /about/booth.json is written); the Code check stops on the CSV's instead (tests/test_booth_csv.py: the
// real file must have none).
// For tests and previews, other files: BOOTH_CSV=…/x.csv, BOOTH_DRIVE=…/booth.json, BOOTH_MANIFEST=…/manifest.json.
// (Only the default export here: with a named one, Eleventy would hand the pages the module object instead.)
import fs from "node:fs";
import * as yaml from "js-yaml";
import siteData from "./site.js";
import { loadBooth, logProblems } from "../../eleventy/filters/booth.js";

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
  // the build log's "[booth] 2 problem(s) — left out of the booth display:" and one line each (the day's live
  // items' are logged when /about/booth.json is written: the boothJson filter)
  logProblems(booth.problems);
  return booth;
}
