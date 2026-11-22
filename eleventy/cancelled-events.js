// Cancelled events, as the build reads them (since round 37). An event that will not take place — content/events
// `cancelled: true` (also `canceled:` / `cancelado:` / `cancelada:`, or `status: cancelled`: scripts/sync/
// announcements.py event_cancelled → extra.cancelled) — is in data/site/events.json's own list, `cancelled`
// (build_data split_cancelled), never in its `items`: no page lists it (Events, Home, the monthly toolkit, the search,
// the booth, What's New …). Its address shows a "Cancelled" notice until its day is over (src/pages/
// event-share-cancelled.njk), and the calendar feeds mark it cancelled (src/pages/events-ics.11ty.js, eleventy/
// filters/monthly.js monthIcs).
// src/_data/db.js makes the same cut itself (splitCancelled), so the event never shows while the data has not caught
// up with its file:
//   · an item of `items` marked cancelled (events.json written before round 37's sync; the last build's items that
//     build_data carried over);
//   · a hand-written event (category manual) whose own file says so — a `cancelled:` / `canceled:` / `cancelado:` /
//     `cancelada:` line with true / yes / sí …, or `status: cancelled`, the sync's own words: a build made before the
//     sync has read the file (a local build, a run whose sync failed) hides it all the same (cancelledInFile).
// It also leaves out of drive.items and whatsnew.items the Drive flyers only cancelled events use (hideCancelledFlyers:
// the Portfolio, What's New, the search — the sync's What's New leaves them out too, build_data cancelled_flyer_ids),
// so the flyer of an event that will not take place is never offered to share, even while it is still in the Drive's
// flyers folder.
// (A module of its own, not in eleventy/filters/ — every file there is loaded as a plugin — and not in src/_data/db.js:
// a data file with named exports would hand the pages the module object instead of the data.)
import fs from "node:fs";
import path from "node:path";

const CANCELLED_KEY = /^(?:cancelled|canceled|cancelado|cancelada)$/;
const CANCELLED_WORD = /^(?:cancelled|canceled|cancelado|cancelada)$/i;
const TRUE_WORD = /^(?:1|true|yes|y|si|sí|on)$/i;        // announcements.as_bool's words
const FRONT = /^﻿?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;
// a line of the header: its key (unindented: never one under another key) and its value — quoted, or up to a comment
const LINE = /^([a-z_]+)[ \t]*:[ \t]*(?:"([^"]*)"|'([^']*)'|([^#]*?))[ \t]*(?:#.*)?$/;
// what each file said, with the moment it was last changed and its size: a file is read again once either moves (a
// preview that keeps running — `npm start` — sees a `cancelled:` line added or taken out at its next rebuild)
const fileSays = new Map();

/** Does the hand-written file of an events.json item say the event is cancelled? Its file, extra.file
 *  ("content/events/<name>.md"), is read in `dir` (content/events): the lines of its header, as the sync reads them.
 *  false for any other item, and for a file that is gone or cannot be read (then the data decides). */
export function cancelledInFile(it, dir = path.join("content", "events")) {
  const file = it && it.category === "manual" && it.extra && typeof it.extra.file === "string" ? it.extra.file : "";
  if (!/^content\/events\/[^/\\]+\.md$/i.test(file)) return false;
  const p = path.join(dir, path.basename(file));
  let stamp = "";
  try {
    const st = fs.statSync(p);
    stamp = `${st.mtimeMs}:${st.size}`;
  } catch {
    fileSays.delete(p);
    return false; // gone, or not readable
  }
  const known = fileSays.get(p);
  if (known && known.stamp === stamp) return known.says;
  let says = false;
  try {
    const head = FRONT.exec(fs.readFileSync(p, "utf8"));
    for (const line of head ? head[1].split(/\r?\n/) : []) {
      const m = LINE.exec(line);
      if (!m) continue;
      const v = String(m[2] ?? m[3] ?? m[4] ?? "").trim();
      if ((CANCELLED_KEY.test(m[1]) && TRUE_WORD.test(v)) || (m[1] === "status" && CANCELLED_WORD.test(v))) says = true;
    }
  } catch { /* gone, or not readable */ }
  fileSays.set(p, { stamp, says });
  return says;
}

/** events.json as the pages read it: `items` without its cancelled events, which join `cancelled` (always a list;
 *  each event once, marked extra.cancelled) → the ids moved out of `items` (the sync had not split them yet). An
 *  event in both lists (the sync never writes one so) is the cancelled one. `dir`: where the hand-written events'
 *  files are (cancelledInFile). */
export function splitCancelled(events, dir) {
  if (!Array.isArray(events.items)) events.items = [];
  events.cancelled = (Array.isArray(events.cancelled) ? events.cancelled : [])
    .filter((it) => it && typeof it === "object" && it.kind === "event" && it.extra && typeof it.extra === "object");
  for (const it of events.cancelled) it.extra.cancelled = true;
  const have = new Set(events.cancelled.map((it) => it.id));
  const moved = [];
  events.items = events.items.filter((it) => {
    if (it && have.has(it.id)) {
      moved.push(it.id);
      return false;
    }
    if (!it || it.kind !== "event" || !it.extra || (it.extra.cancelled !== true && !cancelledInFile(it, dir))) return true;
    it.extra.cancelled = true;
    if (!have.has(it.id)) events.cancelled.push(it);
    have.add(it.id);
    moved.push(it.id);
    return false;
  });
  return moved;
}

// A Drive file's id in a link to it ("…/file/d/<id>/view", "…open?id=<id>", Google's picture of it "…/d/<id>=w600"):
// build_data's _DRIVE_FILE_ID
const DRIVE_FILE_ID = /(?:drive\.google\.com\/(?:file\/d\/|open\?(?:[^#]*&)?id=|uc\?(?:[^#]*&)?id=)|googleusercontent\.com\/d\/)([\w-]{10,})/;
function eventDriveIds(it) {
  const x = (it && it.extra) || {};
  const ids = [x.flyer_url, x.flyer_thumb, it && it.image].map((v) => (typeof v === "string" ? (DRIVE_FILE_ID.exec(v) || [])[1] : "")).filter(Boolean);
  return x.drive_id ? [...ids, String(x.drive_id)] : ids;
}
const driveFileId = (it) => String((it && it.extra && it.extra.file_id) || String((it && it.id) || "").replace(/^drive:/, ""));

/** The site's files once the events are split (splitCancelled) — { events, drive, whatsnew }, each with its `items` —:
 *  drive.items and whatsnew.items without the Drive flyers that cancelled events use and no other event does, and
 *  whatsnew.items without the cancelled events themselves → the Drive ids left out. */
export function hideCancelledFlyers(out) {
  const cancelled = (out.events && out.events.cancelled) || [];
  if (!cancelled.length) return [];
  const gone = new Set(cancelled.flatMap(eventDriveIds));
  for (const it of out.events.items || []) for (const id of eventDriveIds(it)) gone.delete(id);
  const ids = new Set(cancelled.map((it) => it.id));
  if (gone.size && out.drive && Array.isArray(out.drive.items)) out.drive.items = out.drive.items.filter((it) => !gone.has(driveFileId(it)));
  if (out.whatsnew && Array.isArray(out.whatsnew.items)) {
    out.whatsnew.items = out.whatsnew.items.filter((it) => !(it && (ids.has(it.id)
      || (String(it.id || "").startsWith("drive:") && gone.has(driveFileId(it))))));
  }
  return [...gone];
}
