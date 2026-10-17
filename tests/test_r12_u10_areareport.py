"""Round 12 · the chair's report to the Area ("For: District meeting | Area" on /monthly/#report).

eleventy/filters/report.js areaModel() hands the editor dated pieces, each written in English and Spanish;
src/assets/js/report.js (areaSections) keeps the ones of the dates the chair picks and joins them — one document,
the English part, then the Spanish one. Every check runs on a small data set with a FIXED clock (never today's
date):

  * Pieces       — our events only (a content/events file, a dated Drive flyer, a monthly series we hold — not La
                   Viña's own series, not the other calendars, not the committee meeting), the Area assemblies of any
                   calendar once a day (the assembly itself is not one of our activities), what each row's blanks ask
                   for, the dates and towns, a place still to be announced, the committee meetings from the rule
                   (skip_dates honoured), Area 65 writers as printed (the archive + the spotlight, once each), and
                   the first day our past events are complete from (`hz`).
  * KeptAsTheSync — the two numbers the model reads the sync's windows by are the sync's own.
  * Sections     — the dates offered first (the day after the last assembly, to today), the sections for them in both
                   languages: recent (a monthly series on one line, blanks, the meetings held), next (until the next
                   assembly; a series once), writers (the issues whose first day is in the dates), the next committee
                   meeting (a skipped month left out) with its Zoom details.
  * Editor       — For: Area in the page's editor, the redesign's one working report ("gv-report:area:work") and its
                   archive ("gv-report:area:done"): (1) the document (English then Spanish, the blanks the details
                   fill, the dated file name, the Word file); dates are only dates — changing From or To moves, copies
                   or drops nothing, an edited section keeps the chair's words and the others show the site's text for
                   the new dates; To follows today on each load until a To is picked by hand; a From typed first waits
                   for its To. (2) "Next report": shown once a To picked by hand is before today, asks first, files the
                   working report (newest first, 12 at most — the question says which one goes) and starts a fresh one
                   from the day after it to today with the offer "Start from your … report?" (only the carry-over).
                   (3) "Earlier reports": Word and print from what was filed (its dates, parts, the site's text then,
                   the name and meeting), read-only; Delete asks first. (4) "Start over": this part only, the dates and
                   the other part as they are, said so (EN + ES). (5) For: District meeting exactly as before (its
                   drafts, offer, Start over, pruning). (6) Storage that fails or is blocked: nothing throws, the words
                   stay on screen, the page says it can't save, nothing is filed. (7) Safari's 7-day rule: which line
                   shows (Safari on an iPhone or iPad, another browser there, Safari on a Mac; none in a Home Screen
                   app or elsewhere), and navigator.storage.persist() asked once a page, once the Area report is
                   saved or filed.
  * Walks        — seeded random walks (90 × 40 steps, from an empty device, from 12 earlier reports, from a report
                   following today): edits in either part, From / To (in and out of reach, before / after each other),
                   part / mode / page language switches, reloads, the clock moved 0–40 days (with or without a
                   reload), Next report, Start over, Start from, deleting an earlier report, a district edit — after
                   every step, against a shadow of what the chair did: (I1) nothing typed is lost but by Start over
                   (that part) or a deleted (or 13th) earlier report; (I2) the report shows exactly the working
                   report's words; (I3) earlier reports never change; (I4) 12 at most, newest first; (I5) district
                   drafts untouched; the dates as picked (To today while it follows); Next report and the offer shown
                   exactly when they apply; only the editor's own keys on the device.
  * Lastmod      — #rp-area's today / min / max (they move every day) leave /monthly/'s sitemap date as it was.
  * Page         — /monthly/'s markup: the pieces' script (marked for the sitemap date), the switch, labelled date
                   fields bound to the dates typed, the reason under them, Next report, Earlier reports, the Area's
                   Start over label; none of the old period-keyed machinery left in report.js.

    python -m unittest tests.test_r12_u10_areareport -v
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

NOW = "2026-11-20T18:00:00Z"          # Friday, November 20, 2026, noon in Texas
SITE_URL = "https://example.org/site"
STRINGS = json.loads((ROOT / "src" / "_i18n" / "report.json").read_text(encoding="utf-8"))


def ev(iid: str, start: str, end: str | None = None, *, title: str, es: str | None = None, source: str = "committee",
       category: str = "manual", past: bool = False, **extra) -> dict:
    return {"id": iid, "kind": "event", "status": extra.pop("status", "ok"), "source": source, "category": category,
            "title": title, "lang": "en", "date": start, "url": f"https://example.com/{iid}", "machine": [],
            "i18n": {"title": {"en": title, "es": es or title}},
            "extra": {"start": start, "end": end, "past": past, **extra}}


def data() -> dict:
    cw = lambda d, past: ev(f"ev:recurring:citywide-dallas:{d}", f"{d}T23:00:00Z", None, title="GV/LV booth at CityWide Dallas",
                            es="Mesa de GV/LV en CityWide Dallas", category="recurring", past=past, series="citywide-dallas",
                            host="neta", recurring=True, location="Lover's Lane UMC, 9200 Inwood Road, Dallas, TX 75220")
    events = [
        ev("ev:manual:2026-09-26-lv-writing", "2026-09-27T00:00:00Z", "2026-09-27T02:00:00Z", past=True,
           title="La Viña Writing Workshop (in Spanish) — Fort Worth", es="Taller de escritura de La Viña — Fort Worth",
           location="Grupo La Nueva Esperanza, 123 Main St, Fort Worth, TX 76104"),
        ev("ev:manual:2026-10-17-lv-recording", "2026-10-17T19:00:00Z", "2026-10-17T21:00:00Z", past=True,
           title="La Viña Recording Workshop (in Spanish) — Duncanville", es="Taller de grabación de La Viña — Duncanville"),
        ev("ev:flyer:crash", "2026-10-31T16:00:00Z", "2026-10-31T18:00:00Z", source="drive", category="flyer", past=True,
           title="Grapevine Committee Crash", es="Visita del Comité de Grapevine",
           location="Grand Prairie Group, 921 W Pioneer Pkwy, Grand Prairie, TX 75051"),
        cw("2026-09-12", True), cw("2026-10-10", True), cw("2026-11-14", True), cw("2026-12-12", False), cw("2027-01-09", False),
        # not ours: La Viña's own monthly workshop, La Viña's calendar, the committee meeting, a gone event
        ev("ev:recurring:lv-monthly-workshop:2026-10-22", "2026-10-22T19:00:00Z", None, title="La Viña Monthly Virtual Workshop",
           category="recurring", series="lv-monthly-workshop", host="lv", past=True),
        ev("ev:lvcal:1", "2026-10-24", None, title="Taller en Houston", source="calendar", category="lv-calendar", past=True),
        ev("ev:committee:2026-10-21", "2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", title="Committee meeting", category="committee"),
        ev("ev:manual:gone", "2026-10-03T19:00:00Z", None, title="Cancelled workshop", status="gone", past=True),
        # the Area's assemblies: the fall one from another calendar (over), the spring one ours, the summer one tentative
        ev("ev:ics:fall", "2026-09-18", "2026-09-20", title="NETA 65 Fall Assembly 2026", source="calendar", category="ics",
           all_day=True, past=True),
        ev("ev:manual:2027-03-19-spring", "2027-03-19", "2027-03-21", title="NETA 65 Spring Assembly 2027",
           es="Asamblea de Primavera 2027 de NETA 65", all_day=True, location="Hilton, 1600 Main St, Dallas, TX 75201"),
        ev("ev:manual:2027-06-25-summer", "2027-06-25", "2027-06-27", title="NETA 65 Summer Assembly 2027",
           es="Asamblea de Verano 2027 de NETA 65", all_day=True, tentative=True, location="Venue to be announced", location_tba=True),
    ]
    archive = [
        {"id": "wa:1", "key": "https://www.aagrapevine.org/magazine/2026/oct/gps", "url": "https://www.aagrapevine.org/magazine/2026/oct/gps",
         "pub": "gv", "lang": "en", "title": "My Spiritual GPS", "issue_key": "2026-10", "issue_label": "October 2026", "scope": "neta65",
         "writers": [{"name": "Jim B.", "anonymous": False, "place": "Pottsboro, Texas", "geo": {"scope": "neta65", "city": "Pottsboro"}}]},
        {"id": "wa:2", "key": "https://www.aalavina.org/2026/09/despertar", "url": "https://www.aalavina.org/2026/09/despertar",
         "pub": "lv", "lang": "es", "title": "El despertar del espíritu", "issue_key": "2026-09", "scope": "neta65",
         "writers": [{"name": "Victor R.", "geo": {"scope": "neta65", "city": "Grand Prairie"}}]},
        {"id": "wa:3", "key": "https://www.aagrapevine.org/magazine/2026/oct/austin", "url": "https://www.aagrapevine.org/magazine/2026/oct/austin",
         "pub": "gv", "title": "Not our Area", "issue_key": "2026-10", "scope": "texas",
         "writers": [{"name": "Kim L.", "geo": {"scope": "texas", "city": "Austin"}}]},
        {"id": "wa:4", "key": "https://www.aagrapevine.org/magazine/2026/nov/anon", "url": "https://www.aagrapevine.org/magazine/2026/nov/anon",
         "pub": "gv", "title": "Nameless", "issue_key": "2026-11", "scope": "neta65",
         "writers": [{"name": "Anonymous", "anonymous": True, "geo": {"scope": "neta65", "city": "Tyler"}}]},
        {"id": "wa:5", "key": "https://www.aagrapevine.org/magazine/2026/dec/letters", "url": "https://www.aagrapevine.org/magazine/2026/dec/letters",
         "pub": "gv", "title": "Dear Grapevine", "issue_key": "2026-12", "scope": "neta65",
         "writers": [{"name": "Ana P.", "geo": {"scope": "neta65", "city": "Dallas"}}, {"name": "Bob K.", "geo": {"scope": "texas", "city": "Austin"}}]},
    ]
    spot = [
        # the archive has it already: once
        {"id": "sp:1", "kind": "article", "status": "ok", "url": "https://www.aagrapevine.org/magazine/2026/oct/gps", "title": "My Spiritual GPS",
         "extra": {"publication": "gv", "pub_date": "2026-10-01", "author": "Jim B.", "geo": {"scope": "neta65", "city": "Pottsboro"}}},
        {"id": "sp:2", "kind": "article", "status": "ok", "url": "https://www.aagrapevine.org/magazine/2026/nov/darkness", "title": "Back from the Darkness",
         "extra": {"publication": "gv", "pub_date": "2026-11-01", "author": "Will J.", "issue_label": "November 2026",
                   "geo": {"scope": "neta65", "city": "Waco"}}, "i18n": {"issue_label": {"en": "November 2026", "es": "Noviembre 2026"}}},
    ]
    return {"events": {"items": events}, "writers_archive": {"items": archive}, "spotlight": {"items": spot}}


SITE = {"url": SITE_URL, "contact_email": "grapevine@neta65.org", "links": {},
        "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Zoom",
                    "meeting_id": "949 476 7497", "passcode": "neta65", "chair_title": "Grapevine / La Viña Chair",
                    "chair_title_es": "Coordinador(a) de Grapevine / La Viña", "chair_email": "grapevine@neta65.org",
                    "note": "All AA members are welcome to attend.", "note_es": "Todos los miembros de AA pueden asistir.",
                    "skip_dates": ["2026-12-16"]}}

MODEL_JS = """
const R = await imp("eleventy/filters/report.js");
out({ A: R.areaModel(input.db, input.site, new Date(input.now)), keep: [R.KEEP_RECURRING_DAYS, R.KEEP_PAST_EVENTS] });
"""

# The page's editor in a vm context, with the Area pieces the filter builds from the data above (#rp-area), a small
# district model (#rp-data), the page's own strings (#rp-ui: input.uiLang), a localStorage over one Map (input.store)
# and a fixed clock for the browser (input.clock). boot() = the page opened (again) on the same storage. The page's
# confirm() answers `answer` (and keeps the questions: asked); print() keeps the title and the preview printed;
# `failing` makes the storage fail: "set" (a full store: every write throws), "all" (blocked: every access throws);
# `navi` is the next boot's navigator (its user agent, touch points, standalone, storage) and `media` its matchMedia.
EDITOR_JS = r"""
import vm from "node:vm";
const R = await imp("eleventy/filters/report.js");
const A = R.areaModel(input.db, input.site, new Date(input.now));
const lang = (L) => ({
  month: L === "es" ? "noviembre de 2026" : "November 2026",
  sections: ["header", "committee", "asks", "notes"].map((id) => ({ id, title: id + " (" + L + ")",
    text: id === "header" ? "District [##] report" : id === "notes" ? "" : "Text of " + id })),
  tokens: { district: "[##]", name: "[name]", role: "[role]", group: "[group]" }, roles: { gvr: "GVR" },
  custom: "My section", paste: "(paste)", meet: { pick: "Meetings in {where}:", none: "none", more: "more" },
});
const D = { v: 1, month: "2026-11", langs: { en: lang("en"), es: lang("es") }, meetings: { options: [] } };
const UI = R.uiStrings(input.uiLang || "en");
const store = new Map(Object.entries(input.store || {}).map(([k, v]) => [k, JSON.stringify(v)]));
let clock = Date.parse(input.clock || input.now);
class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(clock); } static now() { return clock; } }
let saved = null, cur = null, answer = true, failing = "", navi = {}, media = null;
const said = [], asked = [], printed = [], files = [];
const no = (what) => { throw new Error(what); };
const LS = {
  getItem: (k) => (failing === "all" ? no("SecurityError") : store.has(k) ? store.get(k) : null),
  setItem: (k, v) => { if (failing) no("QuotaExceededError"); store.set(k, String(v)); },
  removeItem: (k) => { if (failing === "all") no("SecurityError"); store.delete(k); },
  get length() { return failing === "all" ? no("SecurityError") : store.size; },
  key: (i) => (failing === "all" ? no("SecurityError") : [...store.keys()][i] ?? null),
};
const boot = (pageLang = "en") => {
  const docL = {};
  const doc = { title: "Monthly", addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); }, querySelector: () => null,
    createElement: () => { const el = { click() { if (el.download) files.push(el.download); }, remove() {}, setAttribute() {}, style: {} }; return el; },
    body: { appendChild() {} },
    getElementById: (id) => (id === "rp-data" ? { textContent: JSON.stringify(D) } : id === "rp-ui" ? { textContent: JSON.stringify(UI) }
      : id === "rp-area" ? { textContent: JSON.stringify(A) } : null) };
  const ctx = {
    console, JSON, Math, Date: FakeDate, Intl, Object, Array, String, Number, Promise, Blob, TextEncoder,
    URL: { createObjectURL: (b) => { saved = b; return "blob:report"; }, revokeObjectURL() {} },
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); t.unref?.(); return t; }, clearTimeout,
    localStorage: LS, navigator: navi, GV: { announce: (m) => said.push(m) }, addEventListener() {}, removeEventListener() {},
    ...(media ? { matchMedia: media } : {}),
    confirm: (q) => { asked.push(q); return answer; },
    print: () => { printed.push({ title: doc.title, html: cur.preview() }); },
    document: doc,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/report.js", "utf8"), ctx, { filename: "report.js" });
  let factory = null;
  ctx.Alpine = { data: (name, fn) => { if (name === "rpEditor") factory = fn; } };
  for (const fn of docL["alpine:init"] || []) fn();
  const a = factory(pageLang);
  a.$nextTick = (fn) => fn && fn();
  a.$refs = {};
  a.$root = { querySelector: () => null, querySelectorAll: () => [] };
  a.init();
  cur = a;
  return a;
};
const secs = (a, L) => Object.fromEntries(a.D.langs[L].sections.map((s) => [s.id, s.text]));
const docxBytes = async () => Buffer.from(await saved.arrayBuffer()).toString("base64");
const ld = (k) => (store.has(k) ? JSON.parse(store.get(k)) : null);
const keys = () => [...store.keys()].sort();
const work = () => ld("gv-report:area:work");
const done = () => ld("gv-report:area:done");
"""


def period(start: str, end: str, follows: bool) -> dict:
    """The working report's dates: To following today, or picked by hand."""
    return {"from": start, "to": end, "toFollowsToday": follows}


def blank(**text) -> dict:
    """A part as the editor keeps it: the Area sections in their order, nothing else changed but `text`."""
    return {"order": ["header", "recent", "next", "writers", "invite", "meeting", "notes"], "off": {}, "text": text, "titles": {},
            "custom": [], "meet": []}


# Random walks on the Area report (Walks): seeded steps (input.walk.seeds — the same on every run) from a start
# (input.walk.start: a store and a clock), against a shadow of what the chair did (S: the working report's words per
# part, the earlier reports as filed; Dt: the dates; dist: the district drafts). After every step:
#   I1     nothing typed is lost — the working report (on the page; stored once nothing waits to be saved) and every
#          earlier report hold exactly the shadow's words (Start over, a deleted or 13th report: the shadow drops them)
#   I2     the report shows exactly the working report's words: none of another report's (but through "Start from")
#   I3     an earlier report never changes (byte for byte, as stored when it was filed)
#   I4     12 earlier reports at most, newest first
#   I5     the district drafts as they were (or as the district edits left them)
#   DATES  the dates as picked (a To typed by hand stops following today; To is today on each load while it follows)
#   NEXT   "Next report" shown exactly when a To picked by hand is before today; FILED: it files the report shown
#   PREV   the offer "Start from …" only while this part is empty and the newest earlier report has something to carry
#   PART   the parts being edited are the working report's; MODEL: the sections are the dates' own
#   KEYS   only the editor's own keys on the device (none of the old period-keyed drafts)
#   ERR    no script error
WALK_JS = r"""
const Wk = input.walk;
const OPS = ["edit", "edit", "edit", "edit", "from", "to", "to", "lang", "mode", "reload", "clock", "clock", "next", "next", "next", "reset",
  "prev", "del", "district"];
const rng = (s) => () => { s |= 0; s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const addD = (ymd, n) => new globalThis.Date(globalThis.Date.parse(ymd + "T12:00:00Z") + n * 864e5).toISOString().slice(0, 10);
const todayC = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Chicago", year: "numeric", month: "2-digit", day: "2-digit" }).format(new globalThis.Date(clock));
const WORK = "gv-report:area:work", DONE = "gv-report:area:done";
const ALLOWED = /^gv-report:(mode|lang|profile|area:work|area:done|\d{4}-\d{2}:(en|es))$/;
const toks = (s) => [...String(s).matchAll(/§\d+§/g)].map((m) => m[0]).sort();
const textOf = (x) => (x && typeof x === "object" && x.text) || {};
const same = (x, y) => { const k = (o) => JSON.stringify(Object.keys(o || {}).sort().map((i) => [i, o[i]])); return k(x) === k(y); };
const carries = (e) => ["en", "es"].some((L) => e[L].invite !== undefined || e[L].notes !== undefined);
const results = [], counts = { next: 0, cancelled: 0, reset: 0, prev: 0, del: 0, district: 0, full: 0, back: 0 };
for (const seed of Wk.seeds) {
  const RND = rng(seed * 7919 + Wk.salt), pick = (arr) => arr[Math.floor(RND() * arr.length)];
  store.clear();
  for (const [k, v] of Object.entries(Wk.start.store)) store.set(k, JSON.stringify(v));
  clock = globalThis.Date.parse(Wk.start.clock);
  answer = true;
  let a = boot(), tok = 0;
  const AA = a.A, log = [], viol = [];
  const bad = (code, msg) => viol.push([code, log.length, msg]);
  const step = (name, fn) => { log.push(name); try { fn(); } catch (e) { bad("ERR", name + ": " + String((e && e.stack) || e).split("\n").slice(0, 3).join(" | ")); } };
  const tc = () => { const t = todayC(); return t < AA.min ? AA.min : t > AA.max ? AA.max : t; };
  // the shadow
  const W0 = Wk.start.store[WORK];
  const S = { work: { en: { ...textOf(W0 && W0.parts.en) }, es: { ...textOf(W0 && W0.parts.es) } },
              done: (Wk.start.store[DONE] || []).map((e) => ({ json: JSON.stringify(e), en: { ...textOf(e.parts.en) }, es: { ...textOf(e.parts.es) } })) };
  const dist = {};
  for (const [k, v] of Object.entries(Wk.start.store)) if (/^gv-report:\d{4}-\d{2}:/.test(k)) dist[k] = { raw: JSON.stringify(v), text: { ...v.text } };
  const Dt = W0 ? { from: W0.from, to: W0.to, follow: W0.toFollowsToday } : {};
  const booted = () => {
    if (!store.has(WORK)) {
      Dt.from = a.range.from; Dt.to = a.range.to; Dt.follow = true;
      if (a.range.toFollowsToday !== true || a.range.to !== tc()) bad("DATES", "the dates offered: " + JSON.stringify(a.range));
    } else if (Dt.follow && tc() >= Dt.from) Dt.to = tc();
  };
  booted();
  for (let n = 0; n < Wk.steps && viol.length < 3; n++) {
    const op = pick(OPS);
    let recompute = false;
    if (op === "edit") {
      const L = pick(["en", "es"]), sec = pick(["recent", "invite", "notes", "writers"]), t = "§" + (++tok) + "§";
      step(`edit ${L}.${sec}=${t}`, () => { if (a.mode !== "area") a.setMode("area"); if (a.rl !== L) a.setLang(L); a.setText(sec, t); if (RND() < 0.6) a.saveNow(); });
      S.work[L][sec] = t;
    } else if (op === "from" || op === "to") {
      if (a.mode !== "area") step("mode area", () => a.setMode("area"));
      const T = tc(), d = pick([T, addD(T, -1), addD(T, -3), addD(T, -12), addD(T, -40), addD(T, 6), Dt.from, Dt.to, addD(Dt.to, 1),
        addD(Dt.from, -3), addD(Dt.from, 9), addD(AA.min, -1), addD(AA.max, 1), addD(AA.min, Math.floor(RND() * 700))]);
      const r = { from: a.rangeIn.from, to: a.rangeIn.to };
      r[op] = d;
      step(`${op} ${d}`, () => a.setRange(op, d));
      if (r.from >= AA.min && r.from <= AA.max && r.to >= AA.min && r.to <= AA.max && r.from <= r.to) {
        Dt.follow = op === "from" && Dt.follow && r.to === Dt.to;
        Dt.from = r.from;
        Dt.to = r.to;
      }
    } else if (op === "lang") {
      step(`switch to ${a.other()}`, () => a.setLang(a.other()));
      recompute = true;
    } else if (op === "mode") {
      const m = a.mode === "area" ? "district" : "area";
      step(`mode ${m}`, () => a.setMode(m));
      recompute = true;
    } else if (op === "reload") {
      const pl = pick(["en", "es"]);
      step(`reload(${pl})`, () => { if (a._pending) a.saveNow(); a = boot(pl); });   // (pagehide saves what waits)
      booted();
      recompute = true;
    } else if (op === "clock") {
      const k = Math.floor(RND() * 41), again = RND() < 0.85, at = addD(todayC(), k) + "T" + pick(["06:30", "12:00", "18:00", "23:30"]) + ":00Z";
      step(`clock ${at}${again ? " + reload" : " (the page left open)"}`, () => { if (again && a._pending) a.saveNow(); clock = globalThis.Date.parse(at); if (again) a = boot(); });
      if (again) { booted(); recompute = true; }
    } else if (op === "next") {
      if (a.mode === "area" && a.newPeriodText()) {
        const yes = RND() < 0.85, full = S.done.length >= 12;
        answer = yes;
        step(`next report${yes ? "" : " (cancelled)"}`, () => a.newPeriod());
        answer = true;
        if (yes) {
          const e = (done() || [])[0];
          if (!e || e.from !== Dt.from || e.to !== Dt.to || !same(textOf(e.parts.en), S.work.en) || !same(textOf(e.parts.es), S.work.es))
            bad("FILED", "the newest earlier report is not the report filed: " + JSON.stringify(e));
          if (full !== asked[asked.length - 1].includes(UI.ar_next_full.split("{")[0])) bad("FULL", "the question: " + asked[asked.length - 1]);
          S.done.unshift({ json: JSON.stringify(e), en: S.work.en, es: S.work.es });
          S.done.splice(12);
          S.work = { en: {}, es: {} };
          Dt.from = addD(Dt.to, 1); Dt.to = tc(); Dt.follow = true;
          recompute = true;
          counts.next++;
          if (full) counts.full++;
        } else counts.cancelled++;
      }
    } else if (op === "reset") {
      if (a.mode === "area") {
        const yes = RND() < 0.85, L = a.rl;
        answer = yes;
        step(`start over ${L}${yes ? "" : " (cancelled)"}`, () => a.resetAll());
        answer = true;
        if (yes) { S.work[L] = {}; recompute = true; counts.reset++; }
      }
    } else if (op === "prev") {
      if (a.mode === "area" && a.prev) {
        const top = S.done[0], L = a.rl;
        step("start from", () => a.startFromPrev());
        for (const P of ["en", "es"]) {
          if (P !== L && Object.keys(S.work[P]).length) continue;
          S.work[P] = Object.fromEntries(["invite", "notes"].filter((k) => top[P][k] !== undefined).map((k) => [k, top[P][k]]));
        }
        counts.prev++;
      }
    } else if (op === "del") {
      if (S.done.length) {
        const i = Math.floor(RND() * S.done.length), yes = RND() < 0.8;
        answer = yes;
        step(`delete earlier report ${i}${yes ? "" : " (cancelled)"}`, () => a.doneDelete(i));
        answer = true;
        if (yes) { S.done.splice(i, 1); recompute = true; counts.del++; }
      }
    } else if (op === "district") {
      const back = RND() < 0.5, t = "§" + (++tok) + "§";
      let k = "";
      step(`district asks=${t}${back ? " + back to Area" : ""}`, () => { a.setMode("district"); k = a.key(a.rl); a.setText("asks", t); a.saveNow(); if (back) a.setMode("area"); });
      dist[k] = { raw: null, text: { ...(dist[k] ? dist[k].text : {}), asks: t } };
      recompute = true;
      counts.district++;
      if (back) counts.back++;
    }

    // ---- the promises, after every step
    const T2 = tc();
    for (const k of store.keys()) if (!ALLOWED.test(k)) bad("KEYS", k);
    for (const [k, v] of Object.entries(dist)) if (v.raw !== null ? store.get(k) !== v.raw : !same(textOf(ld(k)), v.text)) bad("I5", k + " = " + store.get(k));
    const dn = done() || [];
    if (dn.length > 12) bad("I4", dn.length + " earlier reports");
    if (dn.length !== S.done.length || dn.some((e, i) => JSON.stringify(e) !== S.done[i].json)) bad("I3", "the earlier reports changed: " + dn.map((e) => e.from + "…" + e.to).join(", "));
    S.done.forEach((e, i) => { if (dn[i] && !(same(textOf(dn[i].parts.en), e.en) && same(textOf(dn[i].parts.es), e.es))) bad("I1", "earlier report " + i); });
    if (JSON.stringify(a.done) !== JSON.stringify(dn)) bad("I3", "the page's list is not the stored one");
    if (!a._pending && store.has(WORK)) {
      const w = work();
      for (const L of ["en", "es"]) if (!same(textOf(w.parts && w.parts[L]), S.work[L])) bad("I1", `stored ${L} ${JSON.stringify(textOf(w.parts && w.parts[L]))} ≠ typed ${JSON.stringify(S.work[L])}`);
      if (w.from !== Dt.from || w.toFollowsToday !== Dt.follow || (Dt.follow ? w.to > Dt.to : w.to !== Dt.to)) bad("DATES", "stored " + JSON.stringify([w.from, w.to, w.toFollowsToday]) + " ≠ " + JSON.stringify(Dt));
    }
    if (!store.has(WORK) && (Object.keys(S.work.en).length || Object.keys(S.work.es).length) && !a._pending && a.mode === "area") bad("I1", "nothing stored");
    if (a.mode !== "area") continue;
    for (const L of ["en", "es"]) if (!same(a.work[L].text, S.work[L])) bad("I1", `page ${L} ${JSON.stringify(a.work[L].text)} ≠ typed ${JSON.stringify(S.work[L])}`);
    if (a.d !== a.work[a.rl] || a.d2 !== a.work[a.other()]) bad("PART", "the parts edited are not the working report's");
    if (a.range.from !== Dt.from || a.range.to !== Dt.to || a.range.toFollowsToday !== Dt.follow) bad("DATES", JSON.stringify(a.range) + " ≠ " + JSON.stringify(Dt));
    if (a.D.from !== a.range.from || a.D.to !== a.range.to) bad("MODEL", a.D.from + "…" + a.D.to);
    const want = toks(Object.values(S.work.en).concat(Object.values(S.work.es)).join(" ")), got = toks(a.plain());
    if (JSON.stringify(want) !== JSON.stringify(got)) bad("I2", `the report shows ${got.join(" ")} — typed ${want.join(" ")}`);
    if (!!a.newPeriodText() !== (!Dt.follow && Dt.to < T2)) bad("NEXT", `"${a.newPeriodText()}" with ${JSON.stringify(Dt)} on ${T2}`);
    const offer = S.done.length > 0 && !Object.keys(S.work[a.rl]).length && carries(S.done[0]);
    if (a.prev ? !offer || a.prev.r !== a.done[0] : recompute && offer) bad("PREV", `offer ${!!a.prev}, expected ${offer}`);
  }
  results.push({ seed, viol: viol.slice(0, 3), log: viol.length ? log : undefined });
}
out({ walks: results, counts });
"""


def earlier(i: int, *, carry: bool = True) -> dict:
    """An earlier report as the editor files it (the i-th newest of a list a week apart; its words §900§ …)."""
    to = date(2027, 3, 14) - timedelta(days=7 * (i + 1))
    en = {"recent": f"§{900 + 3 * i}§"}
    if carry:
        en["invite"] = f"§{901 + 3 * i}§"
    return {"from": (to - timedelta(days=6)).isoformat(), "to": to.isoformat(),
            "parts": {"en": {"text": en}, "es": {"text": {"notes": f"§{902 + 3 * i}§"} if carry else {}}},
            "site": {"en": {}, "es": {}}, "prof": {"name": "", "ameet": ""}}


DISTRICT = {"gv-report:2026-11:en": {"text": {"asks": "§800§ district words"}}, "gv-report:2026-10:es": {"text": {"notes": "§801§ notas"}}}
WALK_STARTS = {
    "an empty device, Nov 13": {"store": {"gv-report:mode": "area", **DISTRICT}, "clock": "2026-11-13T18:00:00Z"},
    "twelve earlier reports, Mar 18": {
        "store": {"gv-report:mode": "area", **DISTRICT, "gv-report:area:done": [earlier(i, carry=i % 3 != 1) for i in range(12)],
                  "gv-report:area:work": {"from": "2026-11-21", "to": "2027-03-14", "toFollowsToday": False,
                                          "parts": {"en": {"text": {"recent": "§950§", "invite": "§951§"}}, "es": {"text": {"notes": "§952§"}}}}},
        "clock": "2027-03-18T18:00:00Z"},
    "a report following today, Jan 5": {
        "store": {"gv-report:mode": "area", **DISTRICT, "gv-report:area:done": [earlier(0)],
                  "gv-report:area:work": {"from": "2026-11-21", "to": "2026-12-20", "toFollowsToday": True,
                                          "parts": {"en": {"text": {"notes": "§960§"}}, "es": {}}}},
        "clock": "2027-01-05T18:00:00Z"},
}


def s(key: str, lang: str, **v) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(v.get(m.group(1), m.group(0))), STRINGS[key][lang])


class Pieces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = None

    def setUp(self):
        if Pieces.res is None:
            Pieces.res = run_js(self, MODEL_JS, data={"db": data(), "site": SITE, "now": NOW}, env={"SITE_URL": SITE_URL})
        self.A = Pieces.res["A"]
        self.rows = {r["id"]: r for r in self.A["ev"]}

    def test_the_window(self):
        self.assertEqual((self.A["today"], self.A["min"], self.A["max"]), ("2026-11-20", "2025-10-16", "2027-12-25"))
        # fewer than 12 past one-off events kept; the booth's oldest date kept (Sep 12) is near the start of the sync's
        # 90 days (Aug 22): the month before it (Aug 8, or Aug 15) may be missing — complete from 27 days before it
        self.assertEqual(self.A["hz"], "2026-08-16")

    def test_ours_and_the_assemblies(self):
        ids = list(self.rows)
        for gone in ("ev:recurring:lv-monthly-workshop:2026-10-22", "ev:lvcal:1", "ev:committee:2026-10-21", "ev:manual:gone"):
            self.assertNotIn(gone, ids)
        self.assertEqual(ids, sorted(ids, key=lambda i: (self.rows[i]["y"], i)), "soonest first")
        ours = {i for i, r in self.rows.items() if r.get("o")}
        self.assertEqual(ours, {"ev:manual:2026-09-26-lv-writing", "ev:manual:2026-10-17-lv-recording", "ev:flyer:crash",
                                *(f"ev:recurring:citywide-dallas:{d}" for d in ("2026-09-12", "2026-10-10", "2026-11-14", "2026-12-12", "2027-01-09"))})
        asm = {i for i, r in self.rows.items() if r.get("a")}
        self.assertEqual(asm, {"ev:ics:fall", "ev:manual:2027-03-19-spring", "ev:manual:2027-06-25-summer"})
        self.assertEqual(self.rows["ev:recurring:citywide-dallas:2026-10-10"]["s"], "citywide-dallas")
        self.assertEqual(self.rows["ev:manual:2027-06-25-summer"].get("tb"), 1)

    def test_blanks_dates_and_towns(self):
        r = self.rows
        self.assertEqual([r[i]["k"] for i in ("ev:manual:2026-09-26-lv-writing", "ev:manual:2026-10-17-lv-recording",
                                               "ev:recurring:citywide-dallas:2026-10-10", "ev:flyer:crash")], ["w", "r", "b", ""])
        self.assertEqual(r["ev:manual:2026-09-26-lv-writing"]["t"]["en"], ["Sep 26", "La Viña Writing Workshop (in Spanish) — Fort Worth"])
        self.assertEqual(r["ev:manual:2026-09-26-lv-writing"]["t"]["es"], ["26 de septiembre", "Taller de escritura de La Viña — Fort Worth"])
        # the town only when the title does not name it; never a place still to be announced
        self.assertEqual(r["ev:flyer:crash"]["t"]["en"][1], "Grapevine Committee Crash — Grand Prairie")
        self.assertEqual(r["ev:recurring:citywide-dallas:2026-10-10"]["t"]["en"][1], "GV/LV booth at CityWide Dallas")
        self.assertEqual(r["ev:manual:2027-06-25-summer"]["t"]["en"], ["Jun 25–27, 2027", "NETA 65 Summer Assembly 2027"])
        self.assertEqual(r["ev:manual:2027-03-19-spring"]["t"]["es"], ["19–21 de marzo de 2027", "Asamblea de Primavera 2027 de NETA 65 — Dallas"])
        self.assertEqual((r["ev:manual:2027-03-19-spring"]["y"], r["ev:manual:2027-03-19-spring"]["z"]), ("2027-03-19", "2027-03-21"))

    def test_committee_meetings_from_the_rule(self):
        days = [m["y"] for m in self.A["mt"]]
        self.assertIn("2026-10-21", days)
        self.assertNotIn("2026-12-16", days, "a skip date is no meeting")
        self.assertEqual(days[0], "2025-11-19")                         # the first one on or after the earliest day offered
        self.assertTrue(all(d >= self.A["min"] for d in days))
        jan = next(m for m in self.A["mt"] if m["y"] == "2027-01-20")
        self.assertEqual(jan["t"]["en"][1].replace("\u00a0", " "), "Next NETA 65 Grapevine / La Viña committee meeting: Wednesday, January 20, 2027, "
                                            "7–8 PM Central time, on Zoom.")
        self.assertIn("miércoles 20 de enero de 2027", jan["t"]["es"][1])

    def test_writers_as_printed(self):
        wr = [(w["y"], w["t"]["en"]) for w in self.A["wr"]]
        self.assertEqual(wr, [
            ("2026-09-01", "Victor R., Grand Prairie — “El despertar del espíritu” (La Viña, September–October 2026)"),
            ("2026-10-01", "Jim B., Pottsboro — “My Spiritual GPS” (Grapevine, October 2026)"),
            ("2026-11-01", "Anonymous, Tyler — “Nameless” (Grapevine, November 2026)"),
            ("2026-11-01", "Will J., Waco — “Back from the Darkness” (Grapevine, November 2026)"),
            ("2026-12-01", "Ana P., Dallas — “Dear Grapevine” (Grapevine, December 2026)"),
        ])
        es = [w["t"]["es"] for w in self.A["wr"]]
        self.assertIn("Anónimo, Tyler — “Nameless” (Grapevine, noviembre de 2026)", es)
        self.assertNotIn("Austin", json.dumps(self.A["wr"]), "only our Area's writers")

    def test_each_language_has_its_words(self):
        for L in ("en", "es"):
            M = self.A["langs"][L]
            self.assertEqual(set(M["titles"]), {"header", "recent", "next", "writers", "invite", "meeting", "notes"})
            self.assertIn(s("report.ar_tok_meeting", L), M["s"]["h_title"])
            self.assertIn("{from}", M["s"]["h_period"])
            self.assertIn("grapevine@neta65.org", M["s"]["invite"])
            self.assertIn("949 476 7497", M["s"]["meet_more"])
            self.assertIn(SITE_URL + ("/es" if L == "es" else "") + "/meetings/", M["s"]["meet_more"])
            self.assertEqual(M["kinds"], {"assembly": s("report.ar_m_assembly", L), "acm": s("report.ar_m_acm", L)})
        self.assertIn("Coordinador(a) de Grapevine / La Viña", self.A["langs"]["es"]["s"]["h_by"])


class TwelvePastEvents(unittest.TestCase):
    def test_the_first_complete_day_is_the_oldest_kept(self):
        db = data()
        db["events"]["items"] = [ev(f"ev:manual:p{i}", f"2026-09-{i + 1:02d}T19:00:00Z", None, title=f"Workshop {i}", past=True)
                                 for i in range(12)]
        r = run_js(self, MODEL_JS, data={"db": db, "site": SITE, "now": NOW})
        self.assertEqual(r["A"]["hz"], "2026-09-01")


class KeptAsTheSync(unittest.TestCase):
    def test_the_windows_are_the_syncs(self):
        src = (ROOT / "scripts" / "sync" / "build_data.py").read_text(encoding="utf-8")
        recurring = int(re.search(r"^RECURRING_KEEP_PAST_DAYS = (\d+)", src, re.M).group(1))
        past = int(re.search(r"^PAST_EVENTS_KEEP = (\d+)", src, re.M).group(1))
        r = run_js(self, MODEL_JS, data={"db": {}, "site": {}, "now": NOW})
        self.assertEqual(r["keep"], [recurring, past])


class Sections(unittest.TestCase):
    def run_editor(self, script: str, store: dict | None = None, clock: str | None = None):
        return run_js(self, EDITOR_JS + script, data={"db": data(), "site": SITE, "now": NOW, "store": store or {"gv-report:mode": "area"},
                                                     "clock": clock}, env={"SITE_URL": SITE_URL})

    def test_the_period_offered_first_and_its_sections(self):
        r = self.run_editor("const a = boot(); out({ range: a.range, mode: a.mode, en: secs(a, 'en'), es: secs(a, 'es'), ids: a.D.langs.en.sections.map((x) => x.id) });")
        self.assertEqual(r["mode"], "area")
        self.assertEqual(r["range"], period("2026-09-21", "2026-11-20", True), "the day after the Fall Assembly, up to today (following it)")
        self.assertEqual(r["ids"], ["header", "recent", "next", "writers", "invite", "meeting", "notes"])
        en, es = r["en"], r["es"]
        self.assertEqual(en["header"].split("\n")[1], "Period: September 21, 2026 – November 20, 2026")
        self.assertEqual(es["header"].split("\n")[1], "Periodo: del 21 de septiembre de 2026 al 20 de noviembre de 2026")
        self.assertEqual(en["recent"], "\n".join([
            "• Sep 26 — La Viña Writing Workshop (in Spanish) — Fort Worth: about [N] attended, [N] stories written",
            "• GV/LV booth at CityWide Dallas — Oct 10 and Nov 14: about [N] visitors",
            "• Oct 17 — La Viña Recording Workshop (in Spanish) — Duncanville: about [N] attended, [N] stories recorded",
            "• Oct 31 — Grapevine Committee Crash — Grand Prairie: about [N] attended",
            "• Committee meetings on Zoom: Oct 21 and Nov 18 — about [N] members each time",
        ]))
        self.assertIn("• Mesa de GV/LV en CityWide Dallas — 10 de octubre y 14 de noviembre: nos visitaron unas [N] personas", es["recent"])
        self.assertIn("asistieron unas [N] personas, se escribieron [N] historias", es["recent"])
        # until the Spring Assembly (within 200 days): the series once, the assembly, the meetings (December's skipped)
        self.assertEqual(en["next"], "\n".join([
            "• Dec 12 · every month — GV/LV booth at CityWide Dallas",
            "• Mar 19–21, 2027 — NETA 65 Spring Assembly 2027 — Dallas",
            "• Committee meetings on Zoom: Jan 20, 2027, Feb 17, 2027, and Mar 17, 2027",
        ]))
        self.assertNotIn("Summer", en["next"])
        self.assertEqual(en["writers"].split("\n")[:4], [s("report.ar_w_intro", "en"),
                                                        "• Jim B., Pottsboro — “My Spiritual GPS” (Grapevine, October 2026)",
                                                        "• Anonymous, Tyler — “Nameless” (Grapevine, November 2026)",
                                                        "• Will J., Waco — “Back from the Darkness” (Grapevine, November 2026)"])
        self.assertNotIn("Victor", en["writers"])                         # its issue began before the period
        self.assertTrue(en["meeting"].startswith("Next NETA 65 Grapevine / La Viña committee meeting: Wednesday, January 20, 2027"))
        self.assertIn("Zoom meeting ID: 949 476 7497 · Passcode: neta65", en["meeting"])
        self.assertIn("ID de reunión de Zoom: 949 476 7497 · Código de acceso: neta65", es["meeting"])
        self.assertEqual(en["notes"], "")
        for L, S in (("en", en), ("es", es)):
            for sid, text in S.items():
                self.assertNotRegex(text, r"\{[a-z_]+\}", (L, sid))
                self.assertNotIn("undefined", text)
                # anonymity: counts only — no attendance list, no names but the writers' as printed
                self.assertNotIn("attendees", text.lower())

    def test_an_empty_period(self):
        r = self.run_editor("const a = boot(); a.setRange('from', '2025-11-01'); a.setRange('to', '2025-11-30'); out(secs(a, 'en'));")
        self.assertEqual(r["recent"], s("report.ar_recent_none", "en") + "\n• Committee meetings on Zoom: Nov 19, 2025 — about [N] members each time")
        self.assertTrue(r["writers"].startswith(s("report.ar_w_none", "en")))


class Editor(unittest.TestCase):
    WORDS = "Sep 26 workshop: about 25 attended, 9 stories written"
    WORK = "gv-report:area:work"
    DONE = "gv-report:area:done"

    def run_editor(self, script: str, store: dict | None = None, clock: str | None = None, ui: str = "en"):
        return run_js(self, EDITOR_JS + script, data={"db": data(), "site": SITE, "now": NOW, "clock": clock, "uiLang": ui,
                                                     "store": {"gv-report:mode": "area", **(store or {})}}, env={"SITE_URL": SITE_URL})

    # ---- 1. the document; the dates are only dates
    def test_one_document_english_then_spanish(self):
        r = self.run_editor(r"""
          const a = boot();
          a.setProf("name", "Maria G.");
          a.setProf("ameet", "assembly");
          a.download("docx");
          out({ plain: a.plain(), file: a.fileBase(), title: a.titleLine(), blanks: a.blanks(), b64: await docxBytes(),
                hint: a.fileHint(), html: a.preview(), files });""")
        plain = r["plain"]
        en, sep, es = plain.partition("\n\n* * *\n\n")
        self.assertTrue(sep, "the parts are split by * * *")
        self.assertTrue(en.startswith("NETA 65 Grapevine / La Viña Committee — report to the Area 65 Assembly\n"
                                      "Period: September 21, 2026 – November 20, 2026\nPrepared by: Maria G., Grapevine / La Viña Chair\n\n1. Recent activities\n"))
        self.assertTrue(es.startswith("Comité de Grapevine y La Viña de NETA 65 — informe para la Asamblea del Área 65\n"))
        self.assertIn("Preparado por: Maria G., Coordinador(a) de Grapevine / La Viña", es)
        self.assertNotIn("Otras noticias", plain, "an empty section is left out")
        self.assertEqual(r["title"], "NETA 65 Grapevine / La Viña Committee — report to the Area 65 Assembly")
        self.assertEqual(r["file"], "2026-11-20 Grapevine La Vina Area Assembly Report")
        self.assertEqual(r["files"], ["2026-11-20 Grapevine La Vina Area Assembly Report.docx"])
        self.assertEqual(r["hint"], s("report.ar_file_hint", "en", file="2026-11-20 Grapevine La Vina Area Assembly Report.docx"))
        self.assertEqual(r["blanks"], plain.count("[N]"))
        self.assertIn('<hr class="rp-doc-split">', r["html"])
        self.assertIn('data-sec="es:recent" lang="es"', r["html"])
        # the Word file: one document, the Spanish part on a new page with its words marked Spanish
        z = zipfile.ZipFile(io.BytesIO(base64.b64decode(r["b64"])))
        self.assertIsNone(z.testzip())
        for name in z.namelist():
            ET.fromstring(z.read(name).decode("utf-8"))
        doc = z.read("word/document.xml").decode("utf-8")
        self.assertEqual(doc.count('<w:br w:type="page"/>'), 1)
        before, _, after = doc.partition('<w:br w:type="page"/>')
        self.assertIn("Recent activities", before)
        self.assertIn("Actividades recientes", after)
        self.assertNotIn('w:val="es-419"', before)
        self.assertIn('<w:lang w:val="es-419"/>', after)
        self.assertIn('<w:lang w:val="en-US"/>', z.read("word/styles.xml").decode("utf-8"))

    def test_dates_change_only_the_dates(self):
        """One working report, one key: changing From or To changes the dates and nothing else — an edited section
        keeps the chair's words, the others show the site's text for the new dates; the next visit is the same."""
        r = self.run_editor(r"""
          let a = boot();                                       // Nov 20: the dates offered, Sep 21 – Nov 20, To follows today
          const first = [a.range, a.follows()];
          a.setText("recent", "%s");                            // the English part, a section made from the data
          a.setLang("es");
          a.setText("notes", "Nuevo RLV en el Distrito 12");
          a.saveNow();
          const stored = work();
          a.setRange("to", "2026-11-13");                       // a To picked by hand: fixed
          const to = [a.range, a.follows(), a.textOf("notes"), a.textOf("recent") === secs(a, "es").recent, a.textOf("recent")];
          a.setRange("from", "2026-10-01");
          a.setLang("en");
          const from = [a.range, a.textOf("recent"), a.textOf("writers") === secs(a, "en").writers, secs(a, "en").header.split("\n")[1],
                        a.plain().includes("Nuevo RLV en el Distrito 12")];
          a = boot();                                            // the next visit
          out({ first, stored, to, from, again: [a.range, a.rl, a.textOf("recent"), a.d2.text], w: work(), keys: keys() });""" % self.WORDS)
        self.assertEqual(r["first"], [period("2026-09-21", "2026-11-20", True), True])
        self.assertEqual(r["stored"], {"from": "2026-09-21", "to": "2026-11-20", "toFollowsToday": True,
                                       "parts": {"en": blank(recent=self.WORDS), "es": blank(notes="Nuevo RLV en el Distrito 12")}})
        fixed = period("2026-09-21", "2026-11-13", False)
        self.assertEqual(r["to"][:4], [fixed, False, "Nuevo RLV en el Distrito 12", True])
        self.assertNotIn("14 de noviembre", r["to"][4], "the site's text for the new dates (the Nov 14 booth is after them)")
        later = period("2026-10-01", "2026-11-13", False)
        self.assertEqual(r["from"], [later, self.WORDS, True, "Period: October 1, 2026 – November 13, 2026", True])
        self.assertEqual(r["again"], [later, "en", self.WORDS, {"notes": "Nuevo RLV en el Distrito 12"}])
        self.assertEqual(r["w"], {"from": "2026-10-01", "to": "2026-11-13", "toFollowsToday": False,
                                  "parts": {"en": blank(recent=self.WORDS), "es": blank(notes="Nuevo RLV en el Distrito 12")}})
        self.assertEqual(r["keys"], ["gv-report:area:work", "gv-report:lang", "gv-report:mode"], "one key for the working report")

    def test_to_follows_today_until_one_is_picked(self):
        """While toFollowsToday, To is today on each load (a From picked keeps it so); a To picked by hand — today's
        too — is fixed. A page left open past midnight still follows today: no "Next report" for it."""
        r = self.run_editor(r"""
          let a = boot();
          const r1 = [a.range, a.follows(), a.newPeriodText(), a.textOf("recent")];
          a.setRange("from", "2026-10-01");                     // a From picked: To still follows today
          const r2 = a.range;
          clock = Date.parse("2026-11-21T07:00:00Z");           // 1 AM in Texas, the page left open
          const night = [a.range, a.follows(), a.newPeriodText()];
          clock = Date.parse("2026-11-27T18:00:00Z");
          a = boot();
          const r3 = [a.range, a.textOf("recent")];
          a.setRange("to", "2026-11-27");                       // today, picked by hand: fixed
          const r4 = [a.range, a.follows(), a.newPeriodText()];
          clock = Date.parse("2026-12-02T18:00:00Z");
          a = boot();
          out({ r1, r2, night, r3, r4, r5: [a.range, a.follows(), a.newPeriodText(), a.textOf("recent")] });""",
                            store={self.WORK: {"from": "2026-09-21", "to": "2026-11-13", "toFollowsToday": True,
                                               "parts": {"en": {"text": {"recent": self.WORDS}}}}},
                            clock="2026-11-20T18:00:00Z")
        self.assertEqual(r["r1"], [period("2026-09-21", "2026-11-20", True), True, "", self.WORDS])
        self.assertEqual(r["r2"], period("2026-10-01", "2026-11-20", True))
        self.assertEqual(r["night"], [period("2026-10-01", "2026-11-20", True), True, ""])
        self.assertEqual(r["r3"], [period("2026-10-01", "2026-11-27", True), self.WORDS])
        self.assertEqual(r["r4"], [period("2026-10-01", "2026-11-27", False), False, ""], "To = today: no Next report yet")
        self.assertEqual(r["r5"], [period("2026-10-01", "2026-11-27", False), False,
                                   s("report.ar_new_period", "en", date="November 28, 2026"), self.WORDS])

    def test_a_from_typed_first_waits_for_its_to(self):
        """A From after the To stays in its field (with why) until the To comes; a day out of reach says so."""
        r = self.run_editor(r"""
          let a = boot();
          a.setRange("from", "2026-12-01");
          const first = [a.rangeErr, a.rangeIn, a.range, said[said.length - 1], a.rangeErrText()];
          a.setRange("to", "2026-12-31");
          const then = [a.rangeErr, a.range, a.rangeIn, a.rangeErrText()];
          a.setRange("to", "2028-01-01");                     // after the last day the page covers
          const late = [a.rangeErr, a.range, a.rangeIn.to, said[said.length - 1]];
          a.setRange("to", "2026-12-20");
          a.setRange("from", "2025-01-01");                   // before the first
          const early = [a.rangeErr, a.range, a.rangeIn.from];
          a.setLang("es");                                    // another part: the fields show the dates again
          const back = [a.rangeErr, a.rangeIn];
          out({ first, then, late, early, back, w: work() && [work().from, work().to] });""")
        old, new = period("2026-09-21", "2026-11-20", True), period("2026-12-01", "2026-12-31", False)
        self.assertEqual(r["first"], ["order", {"from": "2026-12-01", "to": "2026-11-20"}, old,
                                      s("report.ar_range_bad", "en"), s("report.ar_range_bad", "en")])
        self.assertEqual(r["then"], ["", new, {"from": "2026-12-01", "to": "2026-12-31"}, ""], "December 1 typed first is kept: December 1 – 31")
        out_en = s("report.ar_range_out", "en", **{"from": "October 16, 2025", "to": "December 25, 2027"})
        self.assertEqual(r["late"], ["reach", new, "2028-01-01", out_en])
        self.assertEqual(r["early"], ["reach", period("2026-12-01", "2026-12-20", False), "2025-01-01"])
        self.assertEqual(r["back"], ["", {"from": "2026-12-01", "to": "2026-12-20"}])
        self.assertEqual(r["w"], ["2026-12-01", "2026-12-20"])

    def test_the_note_before_the_first_complete_day(self):
        r = self.run_editor("const a = boot(); const first = a.olderText(); a.setRange('from', '2026-08-01'); out([a.olderText(), a.range, first]);")
        self.assertEqual(r[2], "", "the dates offered first are complete")
        self.assertEqual(r[0], s("report.ar_older", "en", date="August 16, 2026"))
        self.assertEqual(r[1], period("2026-08-01", "2026-11-20", True), "a From picked: the To still follows today")

    # ---- 2. Next report
    FILED_EN = {"order": ["header", "recent", "next", "writers", "invite", "meeting", "notes", "custom-1"],
                "text": {"invite": "Ask us for a workshop!", "recent": "old numbers: 25 attended"},
                "custom": [{"id": "custom-1", "title": "Budget", "text": "In general terms"}]}
    FILED_ES = {"text": {"notes": "Notas de noviembre", "recent": "viejo"}}

    def test_next_report_files_the_report_and_starts_fresh(self):
        r = self.run_editor(r"""
          let a = boot();
          const before = [a.range, a.newPeriodText(), a.prev, a.done];
          answer = false;
          a.newPeriod();                                       // "Cancel": nothing changes
          const cancelled = [asked[asked.length - 1], work(), done(), a.range];
          answer = true;
          a.newPeriod();
          const after = { range: a.range, follows: a.follows(), d: a.d.text, d2: a.d2.text, w: work(), done: done(), said: said[said.length - 1],
                          next: a.newPeriodText(), offer: a.prev && [a.prevTitle(), a.prevBtn(), a.prevText()], recent: a.textOf("recent"),
                          plain: a.plain() };
          a.startFromPrev();
          const started = { en: a.work.en, es: a.work.es.text, recent: a.textOf("recent"), said: said[said.length - 1], prev: a.prev };
          a = boot();
          out({ before, cancelled, after, started, again: [a.range, a.textOf("invite"), a.d.custom.length, done().length, a.prev] });""",
                            store={self.WORK: {"from": "2026-09-21", "to": "2026-11-20", "toFollowsToday": False,
                                               "parts": {"en": self.FILED_EN, "es": self.FILED_ES}},
                                   "gv-report:profile": {"name": "Maria G.", "ameet": "assembly"}},
                            clock="2027-03-25T17:00:00Z")
        dates = "Sep 21 – Nov 20, 2026"
        self.assertEqual(r["before"], [period("2026-09-21", "2026-11-20", False), s("report.ar_new_period", "en", date="November 21, 2026"), None, []])
        self.assertEqual(r["cancelled"][0], s("report.ar_next_confirm", "en", dates=dates, date="November 21, 2026"))
        self.assertEqual(r["cancelled"][1:], [{"from": "2026-09-21", "to": "2026-11-20", "toFollowsToday": False,
                                               "parts": {"en": self.FILED_EN, "es": self.FILED_ES}}, None, period("2026-09-21", "2026-11-20", False)])
        a = r["after"]
        self.assertEqual([a["range"], a["follows"], a["d"], a["d2"], a["next"]], [period("2026-11-21", "2027-03-25", True), True, {}, {}, ""])
        self.assertEqual(a["w"], {"from": "2026-11-21", "to": "2027-03-25", "toFollowsToday": True, "parts": {"en": blank(), "es": blank()}})
        self.assertEqual(a["said"], s("report.ar_next_done", "en", dates=dates))
        # filed as it was: its dates, both parts, the site's text for its dates then, the name and meeting
        self.assertEqual(len(a["done"]), 1)
        e = a["done"][0]
        self.assertEqual([e["from"], e["to"], e["prof"]], ["2026-09-21", "2026-11-20", {"name": "Maria G.", "ameet": "assembly"}])
        self.assertEqual(e["parts"]["en"]["text"], self.FILED_EN["text"])
        self.assertEqual(e["parts"]["en"]["custom"], self.FILED_EN["custom"])
        self.assertEqual(e["parts"]["es"]["text"], self.FILED_ES["text"])
        self.assertEqual(set(e["site"]["en"]), {"header", "recent", "next", "writers", "invite", "meeting", "notes"})
        self.assertTrue(e["site"]["en"]["recent"].startswith("• Sep 26 — La Viña Writing Workshop"))
        self.assertIn("Periodo: del 21 de septiembre de 2026 al 20 de noviembre de 2026", e["site"]["es"]["header"])
        # the fresh report: the site's text, none of the filed words, and the offer
        self.assertNotIn("old numbers", a["plain"])
        self.assertNotIn("Ask us", a["plain"])
        self.assertNotIn("Notas de noviembre", a["plain"])
        self.assertIn("[N]", a["recent"])
        self.assertEqual(a["offer"], [s("report.ar_prev_title", "en", month=dates), s("report.ar_prev_btn", "en", month=dates),
                                      s("report.ar_prev_text", "en", month=dates)])
        # "Start from": the carry-over only — the sections of the chair's own, order, invite / notes; never the counts
        st = r["started"]
        self.assertEqual(st["en"]["text"], {"invite": "Ask us for a workshop!"})
        self.assertEqual(st["en"]["custom"], self.FILED_EN["custom"])
        self.assertEqual(st["en"]["order"], self.FILED_EN["order"])
        self.assertEqual(st["es"], {"notes": "Notas de noviembre"}, "both parts start from it")
        self.assertNotIn("old numbers", st["recent"])
        self.assertEqual([st["said"], st["prev"]], [s("report.ar_prev_done", "en", month=dates), None])
        self.assertEqual(r["again"], [period("2026-11-21", "2027-03-25", True), "Ask us for a workshop!", 1, 1, None])

    def test_next_report_only_once_a_to_picked_is_before_today(self):
        r = self.run_editor(r"""
          const a = boot();
          const follows = a.newPeriodText();
          a.newPeriod();                                       // (not offered: nothing happens)
          const none = [done(), asked.length];
          a.setRange("to", "2026-11-20");                     // today
          const today = a.newPeriodText();
          a.setRange("to", "2026-11-19");
          out({ follows, none, today, yesterday: a.newPeriodText() });""")
        self.assertEqual(r["follows"], "")
        self.assertEqual(r["none"], [None, 0])
        self.assertEqual(r["today"], "")
        self.assertEqual(r["yesterday"], s("report.ar_new_period", "en", date="November 20, 2026"))

    def test_the_archive_keeps_twelve_newest_first(self):
        old = [earlier(i) for i in range(12)]
        r = self.run_editor(r"""
          const a = boot();
          a.newPeriod();
          out({ q: asked[asked.length - 1], done: done(), page: a.done.length, prev: a.prev && a.prev.label });""",
                            store={self.DONE: old, self.WORK: {"from": "2027-03-08", "to": "2027-03-14", "toFollowsToday": False,
                                                               "parts": {"en": {"text": {"notes": "the newest"}}}}},
                            clock="2027-03-18T18:00:00Z")
        self.assertEqual((old[11]["from"], old[11]["to"]), ("2026-12-14", "2026-12-20"))
        self.assertEqual(r["q"], s("report.ar_next_confirm", "en", dates="Mar 8 – Mar 14, 2027", date="March 15, 2027") + " " +
                         s("report.ar_next_full", "en", dates="Dec 14 – Dec 20, 2026"), "the question says which one goes")
        self.assertEqual(len(r["done"]), 12)
        self.assertEqual(r["page"], 12)
        self.assertEqual([r["done"][0]["from"], r["done"][0]["parts"]["en"]["text"]], ["2027-03-08", {"notes": "the newest"}])
        self.assertEqual(r["done"][1:], old[:11], "the others as they were, newest first; the oldest gone")
        self.assertEqual(r["prev"], "Mar 8 – Mar 14, 2027")

    # ---- 3. Earlier reports
    def test_earlier_reports_word_print_and_delete(self):
        filed = {"from": "2026-09-21", "to": "2026-11-20",
                 "parts": {"en": {"text": {"recent": "Filed EN words"}}, "es": {"text": {"notes": "Notas archivadas"}}},
                 "site": {"en": {"writers": "SNAPSHOT of the site's text then", "next": "Then next"}, "es": {}},
                 "prof": {"name": "Ana P.", "ameet": "acm"}}
        older = {"from": "2026-05-01", "to": "2026-06-30", "parts": {"en": {"text": {"notes": "Older"}}, "es": {}}}
        working = {"from": "2026-11-21", "to": "2027-03-20", "toFollowsToday": True, "parts": {"en": {"text": {"notes": "Working words"}}}}
        r = self.run_editor(r"""
          const a = boot();
          const list = [a.doneTitle(), a.done.map((x) => a.doneLabel(x))];
          a.doneDownload(0);
          const word = [files[files.length - 1], said[said.length - 1], await docxBytes()];
          const live = a.preview();
          a.donePrint(0);
          const pr = printed[printed.length - 1];
          const back = [a.preview() === live, a.shown];
          answer = false;
          a.doneDelete(1);
          const kept = [asked[asked.length - 1], done().length];
          answer = true;
          a.doneDelete(1);
          out({ list, word, pr, back, kept, left: done(), said: said[said.length - 1], w: work(), title: a.doneTitle() });""",
                            store={self.DONE: [filed, older], self.WORK: working,
                                   "gv-report:profile": {"name": "Maria G.", "ameet": "assembly"}},
                            clock="2027-03-20T18:00:00Z")
        self.assertEqual(r["list"], [s("report.ar_done_title", "en", n=2), ["Sep 21 – Nov 20, 2026", "May 1 – Jun 30, 2026"]])
        name = "2026-11-20 Grapevine La Vina Area Committee Meeting Report"
        self.assertEqual(r["word"][:2], [name + ".docx", s("report.downloaded", "en", file=name + ".docx")])
        doc = zipfile.ZipFile(io.BytesIO(base64.b64decode(r["word"][2]))).read("word/document.xml").decode("utf-8")
        for words in ("Filed EN words", "SNAPSHOT of the site", "Then next", "Notas archivadas", "Ana P.", "report to the Area 65 Committee Meeting",
                      "Period: September 21, 2026 – November 20, 2026", "Actividades recientes"):
            self.assertIn(words, doc.replace("&apos;", "'"))
        self.assertNotIn("Jim B.", doc.partition("w:type=\"page\"")[0], "the site's text then, not today's")
        for words in ("Working words", "Maria G.", "Area 65 Assembly"):
            self.assertNotIn(words, doc, "the earlier report as filed, not the working one")
        self.assertEqual(doc.count('<w:br w:type="page"/>'), 1)
        self.assertEqual(r["pr"]["title"], name)
        for words in ("Filed EN words", "Notas archivadas", '<hr class="rp-doc-split">'):
            self.assertIn(words, r["pr"]["html"])
        self.assertNotIn("Working words", r["pr"]["html"])
        self.assertEqual(r["back"], [True, ""], "printed, the preview is the working report again")
        self.assertEqual(r["kept"], [s("report.ar_done_del_confirm", "en", dates="May 1 – Jun 30, 2026"), 2])
        self.assertEqual(r["left"], [filed])
        self.assertEqual(r["said"], s("report.ar_done_deleted", "en", dates="May 1 – Jun 30, 2026"))
        self.assertEqual(r["w"], working, "the working report untouched")
        self.assertEqual(r["title"], s("report.ar_done_title", "en", n=1))

    # ---- 4. Start over
    def test_start_over_clears_this_part_only(self):
        for ui, part, other in (("en", "Spanish", "English"), ("es", "español", "inglés")):
            with self.subTest(ui):
                r = self.run_editor(r"""
                  let a = boot();
                  a.setText("recent", "EN words");
                  a.setLang("es");
                  a.setText("notes", "Notas ES");
                  a.setText("recent", "ES recent");
                  a.setRange("to", "2026-11-13");
                  answer = false;
                  a.resetAll();
                  const cancel = [asked[asked.length - 1], a.d.text, work().parts.es.text];
                  answer = true;
                  a.resetAll();
                  const after = [a.d.text, a.d2.text, a.range, work(), said[said.length - 1], a.plain().includes("EN words"), a.plain().includes("Notas ES")];
                  a = boot();
                  out({ cancel, after, again: [a.rl, a.d.text, a.d2.text, a.range] });""", ui=ui)
                self.assertEqual(r["cancel"], [s("report.ar_reset_confirm", ui, part=part, other=other), {"notes": "Notas ES", "recent": "ES recent"},
                                               {"notes": "Notas ES", "recent": "ES recent"}])
                fixed = period("2026-09-21", "2026-11-13", False)
                self.assertEqual(r["after"], [{}, {"recent": "EN words"}, fixed,
                                              {"from": "2026-09-21", "to": "2026-11-13", "toFollowsToday": False,
                                               "parts": {"en": blank(recent="EN words"), "es": blank()}},
                                              s("report.ar_reset_done", ui, part=part, other=other), True, False])
                self.assertEqual(r["again"], ["es", {}, {"recent": "EN words"}, fixed])

    # ---- 5. For: District meeting as before
    def test_for_district_meeting_as_before(self):
        r = self.run_editor(r"""
          let a = boot();
          a.setMode("district");
          a.setText("asks", "District asks");
          a.saveNow();
          const d = [a.mode, a.D.area || false, a.key("en"), a.plain().includes("* * *"), a.fileBase(), store.get("gv-report:mode")];
          a = boot();
          out({ d, back: [a.mode, a.textOf("asks")], said });""")
        self.assertEqual(r["d"], ["district", False, "gv-report:2026-11:en", False, "grapevine-la-vina-report-2026-11-en", '"district"'])
        self.assertEqual(r["back"], ["district", "District asks"])
        self.assertIn(s("report.ar_mode_done", "en", mode=s("report.ar_for_district", "en")), r["said"])

    def test_district_drafts_untouched_by_the_area_report(self):
        """The district drafts as before: whatever the Area report does (edits, dates, Next report, Start over, an
        earlier report deleted), they stay byte for byte; the district editor's offer, Start over and pruning work as
        they did."""
        district = {"gv-report:2026-11:en": {"text": {"asks": "Ours"}}, "gv-report:2026-10:es": {"order": ["header", "asks", "committee", "notes"],
                                                                                                "text": {"notes": "Notas de octubre"}},
                    "gv-report:2026-07:en": {"text": {"notes": "too old"}}}
        r = self.run_editor(r"""
          const raw = () => Object.fromEntries(keys().filter((k) => /^gv-report:\d{4}-\d{2}:/.test(k)).map((k) => [k, store.get(k)]));
          let a = boot();
          const first = raw();
          a.setText("notes", "Area words"); a.setRange("to", "2026-11-13"); a.setLang("es"); a.setText("recent", "x");
          clock = Date.parse("2026-11-25T18:00:00Z"); a = boot(); a.newPeriod(); a.startFromPrev(); a.resetAll(); a.doneDelete(0);
          const area = raw();
          a.setMode("district");                               // Spanish (the report language): October's draft is offered
          const offer = [a.prev && a.prev.month, a.prevTitle()];
          a.startFromPrev();
          const started = [a.d.order, a.d.text, a.textOf("committee")];
          a.resetAll();
          out({ first, area, offer, started, reset: [asked[asked.length - 1], said[said.length - 1], a.saveState, store.has("gv-report:2026-11:es")], last: raw() });""",
                            store=district)
        seed = {k: json.dumps(v, separators=(",", ":"), ensure_ascii=False) for k, v in district.items() if "2026-07" not in k}
        self.assertEqual(r["first"], seed, "pruned as before (older than three months), the others as they were")
        self.assertEqual(r["area"], seed, "the Area report never touches them")
        self.assertEqual(r["offer"], ["2026-10", s("report.prev_title", "en")])
        self.assertEqual(r["started"], [["header", "asks", "committee", "notes"], {"notes": "Notas de octubre"}, "Text of committee"])
        self.assertEqual(r["reset"], [s("report.reset_all_confirm", "en"), s("report.reset_all_done", "en"), "idle", False])
        self.assertEqual(r["last"], seed, "Start over in district mode removes only this month's draft")

    # ---- 6. Storage that fails
    def test_storage_that_fails_keeps_the_words_on_screen(self):
        r = self.run_editor(r"""
          failing = "set";                                      // a full store: every write throws
          let a = boot();
          a.setText("recent", "Typed with a full store");
          a.saveNow();
          const s1 = [a.saveState, a.savedText(), a.textOf("recent")];
          a.setLang("es"); a.setText("notes", "Notas"); a.setLang("en");
          a.setMode("district"); a.setMode("area");
          const s2 = [a.textOf("recent"), a.d2.text];
          a.setRange("to", "2026-11-13");
          const s3 = [a.range, a.textOf("recent"), a.saveState];
          clock = Date.parse("2026-11-21T18:00:00Z");
          a.newPeriod();                                        // can't be filed: the report stays as it is
          const s4 = [a.range, a.textOf("recent"), a.d2.text, said[said.length - 1], a.saveState, a.done, keys()];
          a.resetAll();
          const s5 = [a.d.text, a.d2.text, a.saveState];
          failing = "all";                                      // blocked: every access throws
          const b = boot();
          b.setMode("area");
          b.setText("notes", "Blocked but typed");
          b.saveNow();
          b.setRange("to", "2026-11-13");
          const s6 = [b.mode, b.textOf("notes"), b.saveState, b.done, b.range, b.plain().includes("Blocked but typed")];
          out({ s1, s2, s3, s4, s5, s6 });""")
        failed = STRINGS["report.not_saved"]["en"]
        self.assertEqual(r["s1"], ["failed", failed, "Typed with a full store"])
        self.assertEqual(r["s2"], ["Typed with a full store", {"notes": "Notas"}], "a part or mode switch keeps the words on screen")
        self.assertEqual(r["s3"], [period("2026-09-21", "2026-11-13", False), "Typed with a full store", "failed"])
        self.assertEqual(r["s4"], [period("2026-09-21", "2026-11-13", False), "Typed with a full store", {"notes": "Notas"},
                                   s("report.ar_next_failed", "en"), "failed", [], ["gv-report:mode"]])
        self.assertEqual(r["s5"], [{}, {"notes": "Notas"}, "failed"])
        self.assertEqual(r["s6"], ["area", "Blocked but typed", "failed", [], period("2026-09-21", "2026-11-13", False), True])

    # ---- 7. Safari's 7-day rule; asking the browser to keep the reports
    IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
              "Mobile/15E148 Safari/604.1")
    MAC_SAFARI = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
                  "Safari/605.1.15")

    def test_safaris_seven_days(self):
        """The line on Safari's 7-day rule (the story recorder's checks): Safari on an iPhone or iPad ("tapping"),
        another browser there ("this browser"), Safari on a Mac ("clicking"); none on a Home Screen or Dock app, nor
        in Chrome, Edge or Firefox on a computer or on Android."""
        uas = {
            "iphone": [self.IPHONE, 5, False, False],
            "ipad": [self.MAC_SAFARI, 5, False, False],                       # an iPad asks for desktop sites: a Mac's line
            "iphone_chrome": ["Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                              "CriOS/140.0.7339.122 Mobile/15E148 Safari/604.1", 5, False, False],
            "iphone_app": ["Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                           "Mobile/15E148 [FBAN/FBIOS;FBAV/530.0.0.0]", 5, False, False],
            "mac": [self.MAC_SAFARI, 0, False, False],
            "iphone_home_screen": [self.IPHONE, 5, True, False],
            "mac_dock": [self.MAC_SAFARI, 0, False, True],
            "mac_chrome": ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/140.0.0.0 Safari/537.36", 0, False, False],
            "windows_edge": ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 "
                             "Safari/537.36 Edg/140.0.0.0", 0, False, False],
            "windows_firefox": ["Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0", 0, False, False],
            "android": ["Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile "
                        "Safari/537.36", 5, False, False],
        }
        r = self.run_editor(r"""
          const kinds = {};
          for (const [name, [ua, touch, standalone, dock]] of Object.entries(input.uas)) {
            navi = { userAgent: ua, maxTouchPoints: touch, standalone };
            media = dock ? (q) => ({ matches: q === "(display-mode: standalone)" }) : null;
            kinds[name] = boot().sevenDays;
          }
          out(kinds);""".replace("input.uas", json.dumps(uas)))
        self.assertEqual(r, {"iphone": "safari", "ipad": "safari", "iphone_chrome": "browser", "iphone_app": "browser", "mac": "mac",
                             "iphone_home_screen": "", "mac_dock": "", "mac_chrome": "", "windows_edge": "", "windows_firefox": "",
                             "android": ""})

    def test_the_browser_is_asked_to_keep_the_reports(self):
        """navigator.storage.persist() (as the Tracker and the story recorder ask): once a page, after the Area report
        is first saved or filed — not on opening the page, not for the district report, not when nothing was saved."""
        r = self.run_editor(r"""
          let calls = 0;
          const storage = { persist: () => { calls++; return Promise.resolve(false); } };
          navi = { userAgent: "%s", maxTouchPoints: 5, storage };
          let a = boot();
          const opened = calls;
          a.setMode("district"); a.setText("asks", "District words"); a.saveNow();
          const district = calls;
          a.setMode("area");
          a.setText("recent", "%s");
          const waiting = calls;                                  // (the save waits for the typing to stop)
          a.saveNow();
          const first = calls;
          a.setText("notes", "More"); a.saveNow(); a.setRange("to", "2026-11-13"); a.setProf("name", "Maria G.");
          const again = calls;
          a = boot();                                             // a new page: asks again, once something is saved
          const reopened = calls;
          a.newPeriod();
          const filed = [calls, done().length];
          failing = "set";                                        // a full store: nothing saved, nothing asked
          a = boot();
          a.setText("recent", "Typed with a full store"); a.saveNow();
          out({ opened, district, waiting, first, again, reopened, filed, full: calls, noStorage: (() => {
            failing = ""; navi = { userAgent: "%s" }; const b = boot(); b.setText("notes", "x"); b.saveNow(); return b.saveState; })() });"""
                            % (self.IPHONE, self.WORDS, self.IPHONE))
        self.assertEqual([r["opened"], r["district"], r["waiting"], r["first"], r["again"], r["reopened"]], [0, 0, 0, 1, 1, 1])
        self.assertEqual(r["filed"], [2, 1], "filing a report (a new page) asks")
        self.assertEqual(r["full"], 2, "nothing saved: not asked")
        self.assertEqual(r["noStorage"], "saved", "a browser without navigator.storage saves as before")

    def test_the_strings(self):
        """Every Area string the editor says, in both languages; the questions name what they ask about."""
        for k in ("ar_next_confirm", "ar_next_full", "ar_next_done", "ar_next_failed", "ar_done_title", "ar_done_hint", "ar_done_delete",
                  "ar_done_del_confirm", "ar_done_deleted", "ar_reset_confirm", "ar_reset_done", "ar_reset_part", "ar_part_en", "ar_part_es",
                  "ar_open_hint", "ar_prev_title", "ar_prev_text", "ar_prev_btn", "ar_prev_done", "ar_settings_note"):
            for L in ("en", "es"):
                self.assertTrue(STRINGS["report." + k][L].strip(), (k, L))
            self.assertNotEqual(STRINGS["report." + k]["en"], STRINGS["report." + k]["es"], k)
        self.assertNotIn("report.ar_reset_kept", STRINGS)
        for L in ("en", "es"):
            self.assertIn("{part}", STRINGS["report.ar_reset_confirm"][L])
            self.assertIn("{other}", STRINGS["report.ar_reset_confirm"][L])
            self.assertIn("{dates}", STRINGS["report.ar_next_confirm"][L])
            self.assertIn("{date}", STRINGS["report.ar_next_confirm"][L])
            self.assertIn("{dates}", STRINGS["report.ar_done_del_confirm"][L])
        self.assertIn("Informes anteriores", STRINGS["report.ar_next_confirm"]["es"])
        self.assertIn("Earlier reports", STRINGS["report.ar_next_confirm"]["en"])
        # Safari's 7-day rule: each line names the 7 days, the earlier reports and the Word file to download
        for k in ("ar_keep_safari", "ar_keep_browser", "ar_keep_mac"):
            en, es = STRINGS["report." + k]["en"], STRINGS["report." + k]["es"]
            self.assertTrue(all(w in en for w in ("7 days", "earlier ones", "Word file", "file it")), k)
            self.assertTrue(all(w in es for w in ("7 días", "anteriores", "archivo de Word", "Informes anteriores")), k)
        self.assertIn("Safari", STRINGS["report.ar_keep_safari"]["en"])
        self.assertIn("tapping", STRINGS["report.ar_keep_safari"]["en"])
        self.assertIn("This browser", STRINGS["report.ar_keep_browser"]["en"])
        self.assertIn("Este navegador", STRINGS["report.ar_keep_browser"]["es"])
        self.assertIn("clicking", STRINGS["report.ar_keep_mac"]["en"])
        self.assertIn("hacer clic", STRINGS["report.ar_keep_mac"]["es"])


class Walks(unittest.TestCase):
    def test_random_walks_keep_every_promise(self):
        """90 seeded walks of 40 steps (WALK_JS) from three starts; every promise after every step."""
        total = {}
        for n, (name, start) in enumerate(WALK_STARTS.items()):
            with self.subTest(name):
                res = run_js(self, EDITOR_JS + WALK_JS, data={"db": data(), "site": SITE, "now": NOW, "clock": start["clock"], "store": {},
                                                             "walk": {"seeds": list(range(1, 31)), "steps": 40, "start": start, "salt": n}},
                             env={"SITE_URL": SITE_URL})
                bad = [r for r in res["walks"] if r["viol"]]
                self.assertEqual(bad[:2], [], f"{len(bad)} of {len(res['walks'])} walks broke a promise")
                for k, v in res["counts"].items():
                    total[k] = total.get(k, 0) + v
        # the walks did reach every action, the archive's limit too
        for k in ("next", "cancelled", "reset", "prev", "del", "district", "full", "back"):
            self.assertGreater(total.get(k, 0), 0, k)


LASTMOD_JS = """
const R = await imp("eleventy/filters/report.js");
const L = await imp("eleventy/lastmod.js");
// /monthly/'s <main> with its #rp-area as the template writes it, the pieces built on day `now` from `db`
const page = (tag, now, db) => "<html><head><title>Monthly</title></head><body><main><h2>Your report</h2>" +
  tag.replace("{{ rpa | rpJson | safe }}", () => R.safeJson(R.areaModel(db, input.site, new Date(now)))) + "</main></body></html>";
const fp = (tag, now, db = input.db) => L.fingerprint(page(tag, now, db));
const [d1, d2] = input.days;
const strip = (A) => { const o = { ...A }; for (const k of ["today", "min", "max"]) delete o[k]; return o; };
out({ marked: [fp(input.tag, d1), fp(input.tag, d2)], bare: [fp(input.bare, d1), fp(input.bare, d2)],
      more: fp(input.tag, d2, input.more),
      same: JSON.stringify(strip(R.areaModel(input.db, input.site, new Date(d1)))) === JSON.stringify(strip(R.areaModel(input.db, input.site, new Date(d2)))) });
"""


class Lastmod(unittest.TestCase):
    """#rp-area's today / min / max move every day: /monthly/ (EN + ES) keeps its sitemap date — and stays out of
    IndexNow — until what it says changes (eleventy/lastmod.js, data-lastmod="skip:…")."""

    def test_the_pieces_a_day_apart_keep_the_pages_date(self):
        page = (ROOT / "src" / "pages" / "monthly.njk").read_text(encoding="utf-8")
        tag = re.search(r'<script type="application/json" id="rp-area"[^>]*>\{\{ rpa \| rpJson \| safe \}\}</script>', page).group(0)
        more = data()
        more["events"]["items"].append(ev("ev:manual:2026-11-07-lv-info", "2026-11-07T19:00:00Z", "2026-11-07T21:00:00Z", past=True,
                                          title="Grapevine Information Workshop — Tyler", es="Taller informativo de Grapevine — Tyler"))
        r = run_js(self, LASTMOD_JS, data={"db": data(), "more": more, "site": SITE, "tag": tag,
                                           "bare": re.sub(r'\s+data-lastmod="[^"]*"', "", tag), "days": [NOW, "2026-11-21T18:00:00Z"]},
                   env={"SITE_URL": SITE_URL})
        self.assertTrue(r["same"], "a day apart, only today / min / max move (these dates)")
        self.assertNotEqual(r["bare"][0], r["bare"][1], "unmarked, the moving dates would date the page every day")
        self.assertEqual(r["marked"][0], r["marked"][1], "the page keeps its date")
        self.assertNotEqual(r["more"], r["marked"][1], "a new event of ours still dates it")


class Page(unittest.TestCase):
    def test_the_markup(self):
        page = (ROOT / "src" / "pages" / "monthly.njk").read_text(encoding="utf-8")
        self.assertIn('{%- set rpa = db | rpArea(site) -%}', page)
        self.assertIn('<script type="application/json" id="rp-area" data-lastmod="skip:today,min,max">{{ rpa | rpJson | safe }}</script>', page)
        self.assertIn("setMode('area')", page)
        for fid in ("rp-from", "rp-to", "rp-ameet"):
            self.assertRegex(page, rf'<label class="rp-label" for="{fid}">')
            self.assertRegex(page, rf'id="{fid}"')
        # the error is part of the dates' description only while it shows (a hidden one would still be read)
        described = ":aria-describedby=\"rangeErr ? 'rp-range-hint rp-range-err' : 'rp-range-hint'\""
        self.assertEqual(page.count(described), 2)
        # the fields show the dates typed (rangeIn) — a From after the To stays there until the To comes — and the
        # reason under them is the one that applies (rangeErrText)
        self.assertEqual([page.count(f':value="rangeIn.{f}"') for f in ("from", "to")], [1, 1])
        self.assertIn('<p id="rp-range-err" class="rp-hint rp-err" x-show="rangeErr" x-text="rangeErrText()"></p>', page)
        # Next report; the earlier reports, folded, each with Word / print / delete; the Area's Start over says "this part"
        self.assertIn('data-rp-next x-show="newPeriodText()" @click="newPeriod()"', page)
        self.assertIn('<details class="rp-done" x-show="done.length" x-cloak>', page)
        for call in ("doneDownload(i)", "donePrint(i)", "doneDelete(i)"):
            self.assertIn(f'@click="{call}"', page)
        self.assertIn('{{ "report.ar_reset_part" | t(lang) }}', page)
        # Safari's 7-day rule: its line (report.js sevenDays) under "Earlier reports" and in the Area's saving note
        for k in ("safari", "browser", "mac"):
            self.assertEqual(page.count(f"<span x-show=\"sevenDays === '{k}'\" x-cloak> {{{{ \"report.ar_keep_{k}\" | t(lang) }}}}</span>"), 2, k)
        note = re.search(r'<p class="rp-note" x-show="mode === \'area\'">(.*?)</p>', page, re.S).group(1)
        self.assertIn("report.ar_settings_note", note)
        self.assertIn("report.ar_keep_safari", note)
        done = re.search(r'<details class="rp-done".*?</details>', page, re.S).group(0)
        self.assertRegex(done, r'report\.ar_done_hint" \| t\(lang\) \}\}<span x-show="sevenDays === \'safari\'"')
        css = (ROOT / "src" / "assets" / "css" / "areas" / "report.css").read_text(encoding="utf-8")
        self.assertIn(".rp-doc-split", css)
        self.assertIn(".rp-done-item", css)
        self.assertRegex(css, r"body\.mp-hub \.rp-doc-split \{[^}]*break-after: page")

    def test_the_old_machinery_is_gone(self):
        """The period-keyed drafts (carry, follow, of-marks, held, area-range, the period scans) are gone: one working
        report, one archive."""
        js = (ROOT / "src" / "assets" / "js" / "report.js").read_text(encoding="utf-8")
        for gone in ("area-range", "carry(", "follow(", "isCopy", "markOf", "this.held", "lastAreaDraft", "savedRange", "AREA_KEY", ".of "):
            self.assertNotIn(gone, js, gone)
        self.assertEqual(js.count('"area:work"'), 1)
        self.assertEqual(js.count('"area:done"'), 1)


if __name__ == "__main__":
    unittest.main()
