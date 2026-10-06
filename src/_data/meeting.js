// Computes upcoming committee meeting dates from config/site.yml `meeting`
// (e.g. 3rd Wednesday, 19:00–20:00 Central). Client JS recomputes live (app.js GV.nextMeeting, the same
// rule through the same helper: eleventy/central-time.js ruleDate — right on the days the clocks change).
// (Only the default export here: with a named one, Eleventy would hand the pages the module object as
// `meeting` instead of calling it — the shared readers live in eleventy.config.js.)
import fs from "node:fs";
import * as yaml from "js-yaml";
import { monthlyRule, TZ } from "../../eleventy.config.js";
import { ruleDate } from "../../eleventy/central-time.js";

const WD = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };

function plusHour(hhmm) {
  const [h, m] = String(hhmm || "19:00").split(":").map(Number);
  return `${String((h + 1) % 24).padStart(2, "0")}:${String(m || 0).padStart(2, "0")}`;
}

export default function () {
  // Read the way the daily sync reads it (eleventy.config.js monthlyRule = scripts/sync/meeting.py
  // meeting_rule): "7:00 PM", "7pm" or 19 → "19:00" (a time as written never stops the build), "sábado",
  // a week it cannot read ("third") → the 3rd, one skip date without brackets, and an end that is missing
  // or not after the start → one hour (the countdown's rule gets that end too) — except an overnight one
  // ("22:00"–"01:00": the next morning, as the sync has it).
  const cfg = monthlyRule(yaml.load(fs.readFileSync("config/site.yml", "utf8")).meeting || {});
  const weekday = WD[String(cfg.weekday || "wednesday").toLowerCase()] ?? 3;
  const n = Number(cfg.week_of_month || 3);
  // Unquoted YAML dates arrive as Date objects — normalize everything to "YYYY-MM-DD".
  const skip = new Set((cfg.skip_dates || []).map((d) => (d instanceof Date ? d.toISOString().slice(0, 10) : String(d))));
  const rule = { weekday, n, start: cfg.start || "19:00", end: cfg.end || "", skip: [...skip] };
  const now = Date.now();
  const today = new Date(now);
  const dates = [];
  for (let i = -1; i < 14 && dates.length < 13; i++) {
    // (a month's meeting in Central time; an overnight end is the next morning; no end, or one not after the
    // start: one hour)
    const d = ruleDate(today.getUTCFullYear(), today.getUTCMonth() + i, rule, TZ);
    if (!d || d.end < now) continue;
    dates.push({ ymd: d.ymd, start: new Date(d.start).toISOString(), end: new Date(d.end).toISOString() });
  }
  return {
    // Client countdown uses the same rule; a missing end means a 1-hour meeting.
    rule: { weekday, n, start: cfg.start, end: cfg.end || plusHour(cfg.start), skip: [...skip] },
    next: dates[0] || null,
    upcoming: dates.slice(0, 12),
  };
}
