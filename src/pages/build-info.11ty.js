// /build.json — a small note about THIS build, for the Morning check (.github/workflows/morning.yml: its
// first job reads the LIVE copy, and scripts/ops/morning_check.py → is_done()): is today's update on the
// site — the build's day in Central time, and the day of each daily quote it carries? — and is the full
// daily update due (when did the last one run)?
//   { v: 1,
//     built:   the build's time (UTC ISO; the footer's "Last updated"),
//     day:     that time's calendar day in the site's time zone (config site.timezone, Central),
//     tz:      that time zone,
//     quotes:  { gv, lv } — the day of the Grapevine and the La Viña quote on the home page (data/site/quote.json),
//     data:    when build_data last wrote the site data (status.json `generated`), or null,
//     full:    when the last FULL daily update ran (status.json `full_update`: the newest `attempted` of
//              the sources only it reads), or null — the Morning check starts one on the 1st of the month
//              and after a day GitHub skipped (morning_check.full_run_reason),
//     run:     the GitHub Actions run that built it (GITHUB_RUN_ID; "" on a computer) — the Morning check
//              waits until the live copy shows the run it started,
//     version, commit: the code fingerprint and commit (src/_data/build.js) }
// Nothing in it is new: /status/ shows the same facts to people. It is not linked from any page and is
// left out of the collections, the sitemap and the search; the service worker treats .json network-first,
// and visitors never ask for it.
const ymdIn = (iso, tz) => {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(iso));
  } catch {
    return String(iso).slice(0, 10);   // an unknown time zone name: the UTC day
  }
};

export const data = {
  permalink: "/build.json",
  eleventyExcludeFromCollections: true,
  layout: false,
};

export function render(data) {
  const tz = data.site?.timezone || "America/Chicago";
  const built = data.site?.built || new Date().toISOString();
  const quotes = {};
  for (const q of data.db?.quote?.items || []) {
    if (q && q.pub && /^\d{4}-\d{2}-\d{2}/.test(String(q.date || ""))) quotes[q.pub] = String(q.date).slice(0, 10);
  }
  return JSON.stringify({
    v: 1,
    built,
    day: ymdIn(built, tz),
    tz,
    quotes,
    data: data.db?.status?.generated || null,
    full: data.db?.status?.full_update || null,
    run: process.env.GITHUB_RUN_ID || "",
    version: data.build?.version || "",
    commit: data.build?.commit || "",
  }) + "\n";
}
