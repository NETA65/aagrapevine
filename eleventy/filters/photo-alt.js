// The /photos/ albums' alt text (since round 35). Auto-loaded by eleventy.config.js.
//
//   photoAlts(items, album, lang)  an album's photos → each one's words (photoAlt, below), in order; when several
//                                  photos of the album have the same words, each gets its place among them —
//                                  "Grapevine, November 1960 (2 of 4)", "Panel 75 Displays (12 of 66)"
//                                  (committee.photos.alt_nth) — so no two links of an album share one name (a
//                                  screen reader's list of links; the photos are different pictures).
//   photoAlt(title, album, lang)   a photo's title (its Drive file name, without the extension) → the words for its
//                                  picture's alt text (and the photo link's "Open photo: …"). A title that is a
//                                  file name — a YYYY-MM or YYYY-MM-DD date first, then dash-separated words, no
//                                  spaces: "1951-10-Gv-Report-00", "1960-11-Gv-03-Intl-Long-Beach-01" — says nothing
//                                  to a screen reader or an image search, and the English file names showed on
//                                  /es/photos/ too. Such a title becomes the magazine (a "Gv" word: Grapevine; "Lv":
//                                  La Viña) or else the album's title, and the month and year in the page language:
//                                  "Grapevine, October 1951" / "Grapevine, octubre de 1951", "Historical Archive,
//                                  December 1955". Nothing else of the file name is kept: its other words can be
//                                  anything — a person's name among them ("…-Western-Union-Eisenhower"), and the
//                                  site never puts a name in alt text. A month "00" (or none that is a month) leaves
//                                  the year alone; a day is never said (most of these are magazine pages, dated by
//                                  their issue's month). Any other title is kept as it is: the owner's own words
//                                  ("Panel 75 Displays", "Austria Gemeinsam 1993-09").
//
// The visible caption and the slideshow's title keep the file's name (they are what the committee called it;
// renaming the file on Drive changes all of them).

const FILE_NAME = /^(\d{4})-(\d{2})(?:-(\d{2}))?((?:-[\p{L}\p{N}]+)+)$/u;
const MAGAZINES = { gv: "Grapevine", lv: "La Viña" };

/* "1951-10-Gv-Report-00" → { year: 1951, month: 10, words: ["Gv", "Report", "00"] }; null for any other title */
export function fileNameParts(title) {
  const m = FILE_NAME.exec(String(title || "").trim());
  if (!m) return null;
  const year = Number(m[1]), month = Number(m[2]);
  if (year < 1900 || year > 2099) return null;
  return { year, month: month >= 1 && month <= 12 ? month : 0, words: m[4].slice(1).split("-") };
}

export function photoAlt(title, album, lang, fmtDate) {
  const t = String(title || "").trim();
  const parts = fileNameParts(t);
  if (!parts) return t;
  const mag = parts.words.map((w) => MAGAZINES[w.toLowerCase()]).find(Boolean);
  const what = mag || String(album || "").trim();
  const ym = parts.year + "-" + String(parts.month).padStart(2, "0");
  const when = parts.month && fmtDate ? fmtDate(ym, lang === "es" ? "es" : "en", "month") : String(parts.year);
  return what ? what + ", " + (when || parts.year) : when || String(parts.year);
}

/* An album's photos → their words (photoAlt), a repeated one with its place: nth(words, n, total) */
export function photoAlts(items, album, lang, fmtDate, nth = (w, n, total) => `${w} (${n}/${total})`) {
  const alts = (Array.isArray(items) ? items : []).map((p) => photoAlt(p && p.title, album, lang, fmtDate));
  const total = new Map(), seen = new Map();
  for (const a of alts) total.set(a, (total.get(a) || 0) + 1);
  return alts.map((a) => {
    if (!a || total.get(a) < 2) return a;
    const n = (seen.get(a) || 0) + 1;
    seen.set(a, n);
    return nth(a, n, total.get(a));
  });
}

export default function (eleventyConfig, helpers = {}) {
  const nth = (lang) => (title, n, total) => (helpers.translateKey
    ? helpers.translateKey("committee.photos.alt_nth", lang, { title, n, total }) : `${title} (${n}/${total})`);
  eleventyConfig.addFilter("photoAlts", (items, album, lang) => photoAlts(items, album, lang, helpers.fmtDate, nth(lang)));
}
