// GVR / RLV Bingo (the GVR / RLV corner's bingo cards: /gvr/bingo/, /es/gvr/bingo/ and the /gvr/ teaser) — the pool
// of squares, read and checked once per build, exposed as `bingo` in every template (SPEC §2, aagrapevine-ops/r34):
//   bingo.file      the CSV's path ("content/bingo/bingo.csv")
//   bingo.found     false when the file is missing (then no squares, and a problem says so)
//   bingo.rows      the rows after the header
//   bingo.items     [{ id, type, pub, cat, where: [...] ([] = everywhere), pin, weight, from, until, text: { en, es },
//                   short: { en, es }, label: { en, es } }] — the rows that are on and have no mistake, in file order,
//                   every placeholder but {event} filled in from the settings (a language the row is not offered in
//                   is ""; short is the text itself when short_* is blank; label "" = the type's default)
//   bingo.problems  [{ where, en, es }] — every row left out and why (the CSV's mistakes, then placeholders without
//                   a value in this build)
//   bingo.cats      the categories in the builder's order (people … fun, then any new one src/_i18n/bingo.json names)
//   bingo.wheres    the occasions ("Where are you taking it?": group … online)
//   bingo.info      { committee, area, email, site, home, gvr, gvMeeting, gvMeetingMid, gvMeetingShort,
//                   committeeMeeting, committeeMeetingMid, committeeMeetingShort, gvWeekly, gvWeeklyShort, lvWeekly,
//                   lvWeeklyShort } — what the cards print about us, in both languages (a monthly meeting's long,
//                   mid and short lines: eleventy/filters/bingo.js BINGO_WORDS)
// Reading, checking and filling in: eleventy/filters/bingo.js loadBingo (content/bingo/README.md is the owner's guide
// to the CSV; tests/test_bingo_csv.py the Python twin of its checks).
// Problems never stop the build — they are written to the log ("[bingo] 2 problem(s) — left out:", logBingoProblems);
// the Code check stops on the real file's instead (tests/test_bingo_csv.py Real: it must have none).
// For tests and previews, other files: BINGO_CSV=…/x.csv, BINGO_WEEKLY=…/weekly_open.json.
// (Only the default export here: with a named one, Eleventy would hand the pages the module object instead.)
import siteData from "./site.js";
import { loadBingo, logBingoProblems } from "../../eleventy/filters/bingo.js";

export default function () {
  // config/site.yml as the site reads it (its address: SITE_URL from the GitHub Action wins) through src/_data/site.js
  const bingo = loadBingo({
    csv: process.env.BINGO_CSV || "content/bingo/bingo.csv",
    weekly: process.env.BINGO_WEEKLY || "data/site/weekly_open.json",
    site: siteData(),
  });
  logBingoProblems(bingo.problems);
  return bingo;
}
