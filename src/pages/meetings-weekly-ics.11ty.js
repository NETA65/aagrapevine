// The weekly open meetings' calendar files — /meetings/weekly-open-gv.ics (AA Grapevine's Weekly Open) and
// /meetings/weekly-open-lv.ics (La Viña's Reunión Abierta), and the same in Spanish under /es/: the "Add to
// calendar → Apple / Outlook (.ics file)" link on each card of /meetings/#weekly-open (meetings.njk). One event
// that repeats every week at the meeting's own clock time in its own zone, an hour long, with the Zoom link,
// meeting ID and passcode in its text (eleventy/filters/committee.js weeklyCalendar + weeklyIcs). A meeting
// without a date (data/site/weekly_open.json) has no file — and no link on its card.
import { weeklyOpenAll, weeklyCalendar, weeklyIcs } from "../../eleventy/filters/committee.js";

const items = (data) => (process.env.COMMITTEE_EMPTY ? [] : data?.db?.weekly_open?.items || []);

export const data = {
  pagination: {
    data: "languages",
    size: 1,
    alias: "file",
    // one file per meeting and language
    before: (langs, full) => (langs || []).flatMap((lang) => weeklyOpenAll(items(full), lang)
      .map((w) => weeklyCalendar(w, full?.site || {}, lang))
      .filter(Boolean)
      .map((cal) => ({ lang, key: cal.key }))),
  },
  permalink: (data) => `${data.file.lang === "en" ? "" : "/" + data.file.lang}/meetings/weekly-open-${data.file.key}.ics`,
  eleventyExcludeFromCollections: true,
  layout: null,
};

export function render(data) {
  const { lang, key } = data.file;
  // one moment for the file: its first date (the next meeting, as on the cards) and its DTSTAMP / SEQUENCE
  const now = new Date();
  const cal = weeklyOpenAll(items(data), lang, now).map((w) => weeklyCalendar(w, data.site || {}, lang)).find((c) => c && c.key === key);
  return weeklyIcs(cal, now);
}
