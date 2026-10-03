// Freshness filters: how current the site is, and when things stop being current. Auto-loaded by
// eleventy.config.js. Every filter is defensive: status.json may be old (no quote_days yet), empty or odd.
//
//   fsQuoteMornings(status, now)  /status/ → the line under "Daily quote" and, in "Behind the scenes", the
//                                 last 7 mornings: when each day's Grapevine and La Viña quotes came in
//                                 (status.json quote_days — build_data.quote_days, from quote.py's
//                                 history[].seen: the time the sync first READ that day's quote, not the
//                                 time it went live; the Morning check's run summary has that) against the
//                                 goal, config site.morning_goal (the Morning check, .github/workflows/
//                                 morning.yml, puts the new day and both quotes on the site by then).
//   fsShortDay(ymd, lang)         'YYYY-MM-DD' → "Tue, Sep 29" / "Mar, 29 de sept" (no year: the rows of
//                                 the last 7 mornings, where the page already says the times are Central).
//   fsClock(iso, lang)            an instant → its Central clock time without the zone ("5:52 AM" /
//                                 "5:52 a. m."), for the same rows; '' for anything else.
//   fsDayEnd(ymd)                 'YYYY-MM-DD' → the ISO instant that day ends in Central time (midnight
//                                 after it), for [data-gv-expire] (src/assets/js/app.js GV.expire): a
//                                 bulletin post's `expires` day, a story deadline. '' for anything else.

// The end of a Central-time day, right across daylight saving (the same rule as /events/).
import { chicagoDayEndMs } from "./committee.js";

const TZ = "America/Chicago";
const LOCALES = { en: "en-US", es: "es-US" };
const isYmd = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
const ms = (v) => { const t = Date.parse(v || ""); return Number.isNaN(t) ? null : t; };

/* One day of status.json quote_days → the row /status/ shows.
   Each magazine: "on_time" (came in by the goal), "late" (after it), "waiting" (not yet, and the day is
   not over at `now` — the build's clock: today before its quote is out), "none" (the day ended without it).
   `both`: when the day's quotes were all in (the later of the two); `one`: exactly one of them is in —
   { pub, at, other } (the /status/ line then names the one still missing). */
export function quoteMorning(row, now = Date.now()) {
  const r = row && typeof row === "object" ? row : {};
  const goal = ms(r.goal_at);
  const dayOver = isYmd(r.day) ? now >= chicagoDayEndMs(r.day) : true;
  const state = (seen) => {
    const t = ms(seen);
    if (t === null) return dayOver ? "none" : "waiting";
    return goal !== null && t <= goal ? "on_time" : "late";
  };
  const gv = ms(r.gv) === null ? null : r.gv;
  const lv = ms(r.lv) === null ? null : r.lv;
  // both quotes in: the later of the two is when "the day's quotes" were in
  const both = gv && lv ? (ms(gv) >= ms(lv) ? gv : lv) : null;
  const one = !both && (gv || lv) ? (gv ? { pub: "gv", at: gv, other: "lv" } : { pub: "lv", at: lv, other: "gv" }) : null;
  return {
    day: isYmd(r.day) ? r.day : "",
    goal_at: goal === null ? "" : r.goal_at,
    gv, lv, both, one,
    gvState: state(gv),
    lvState: state(lv),
    gvOnTime: state(gv) === "on_time",
    lvOnTime: state(lv) === "on_time",
    onTime: !!both && goal !== null && ms(both) <= goal,
  };
}

/* status.json → { goal: "05:30", days: [quoteMorning…] (newest first), today: days[0] }, or null when the
   status file has no quote_days (an older build) or no day to show — then /status/ shows neither the line
   nor the table. */
export function quoteMornings(status, now = Date.now()) {
  const qd = status && status.quote_days;
  if (!qd || typeof qd !== "object" || !Array.isArray(qd.days)) return null;
  const days = qd.days.filter((r) => r && isYmd(r.day)).map((r) => quoteMorning(r, now));
  if (!days.length) return null;
  return { goal: typeof qd.goal === "string" ? qd.goal : "", days, today: days[0] };
}

/* 'YYYY-MM-DD' (or an ISO date-time: its date part) → ISO of midnight Central after that day
   ('2026-10-14' → '2026-10-15T05:00:00.000Z'); '' for anything else, a day that does not exist included. */
export function dayEnd(ymd) {
  const s = typeof ymd === "string" ? ymd.trim() : "";
  if (!/^\d{4}-\d{2}-\d{2}(?:$|T)/.test(s)) return "";
  const day = s.slice(0, 10);
  const real = new Date(`${day}T12:00:00Z`);
  if (Number.isNaN(real.getTime()) || real.toISOString().slice(0, 10) !== day) return "";   // "2026-02-30"
  const t = chicagoDayEndMs(day);
  return Number.isFinite(t) ? new Date(t).toISOString() : "";
}

/* The two labels of the 7-morning rows. `meridiem` is eleventy.config.js esMeridiem (Intl's Spanish
   "5:52 a.m." → the site's "5:52 a. m."); Spanish capitalises the day, which starts its row. */
export function shortDay(ymd, lang = "en") {
  if (!isYmd(ymd) || dayEnd(ymd) === "") return "";
  const s = new Intl.DateTimeFormat(LOCALES[lang] || LOCALES.en, { weekday: "short", month: "short", day: "numeric", timeZone: TZ })
    .format(new Date(`${ymd}T12:00:00Z`));
  return lang === "es" ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export function clock(iso, lang = "en", meridiem = (s) => s) {
  const t = ms(typeof iso === "string" ? iso : "");
  if (t === null) return "";
  const s = new Intl.DateTimeFormat(LOCALES[lang] || LOCALES.en, { hour: "numeric", minute: "2-digit", timeZone: TZ }).format(new Date(t));
  return lang === "es" ? meridiem(s) : s;
}

export default function (eleventyConfig, helpers = {}) {
  eleventyConfig.addFilter("fsQuoteMornings", (status, now) => quoteMornings(status, Number(now) || Date.now()));
  eleventyConfig.addFilter("fsDayEnd", dayEnd);
  eleventyConfig.addFilter("fsShortDay", (ymd, lang) => shortDay(ymd, lang));
  eleventyConfig.addFilter("fsClock", (iso, lang) => clock(iso, lang, helpers.esMeridiem || ((s) => s)));
}
