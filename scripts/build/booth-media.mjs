// Downloads the booth display's photos and videos, so the booth keeps playing offline at a table with no internet —
// the step "Download the booth display's photos and videos" of .github/workflows/update.yml (job "Build website"),
// run just before Eleventy builds the site:
//
//     node scripts/build/booth-media.mjs              (from the repository's folder)
//     node scripts/build/booth-media.mjs --dry-run    only says what a run would do now (nothing is downloaded,
//                                                     deleted or written)
//
// What it does (r5 SPEC §2.3; the rules themselves — the plan, the names, the limits, reading a picture's size —
// are in booth-media-core.mjs next to this file, where tests/test_booth_media.py checks them):
//   1. reads data/site/booth.json (the files of the committee's Drive booth folder, written by the daily sync) and
//      the two size limits in config/site.yml: booth.max_file_mb (95) for one video or sound file and
//      booth.max_total_mb (400) for the whole folder;
//   2. keeps every file an earlier run saved in .cache/booth-media/files/ (GitHub's Actions cache brings the folder
//      back at the start of the job), deletes the ones no longer listed, and downloads the rest one at a time — a
//      photo or poster as Google's 1920-pixel picture of it, a video or sound file whole, written straight to disk;
//      60 seconds for a picture, 8 minutes for a video or sound file, 3 tries each;
//   3. writes .cache/booth-media/manifest.json: which saved file is which Drive file, with its size, its type and —
//      for a picture — its width and height. Eleventy publishes the folder at /about/booth/media/
//      (eleventy.config.js), and the show's data (src/_data/booth.js) points each slide at its saved copy.
//
// A file that can't be saved is SKIPPED, never a reason to stop: too big (over booth.max_file_mb), over the folder's
// limit (booth.max_total_mb — the files marked "first", then the ones listed first, are kept first; a video or
// sound file whose size booth.json does not give — it has none without GOOGLE_API_KEY — may take the room really
// left, and its download stops when it would pass it), Drive answering with a web page instead of the file ("too
// many downloads", "can't scan for viruses"), an incomplete download, no answer. Each one is named in the step's log
// and as a yellow warning on the run's page. The booth then shows that picture from Google's copy while it is online
// (a video without a saved copy is left out of the show); a download that failed is simply tried again by the next
// run. The script ends with exit code 0 whatever happened to the downloads; only a mistake in the script itself ends
// it with an error — and even then the website is built and published (the step has continue-on-error), just
// without the saved copies: the old manifest is deleted first, and the new one, written as soon as the kept files
// are known and again after each download, only ever names files that are in the folder.
//
// Its time: every download ends by the 15th minute (BOOTH_MEDIA_MINUTES; one still going then is stopped), inside the
// step's own limit of 20, so the job always gets to publish the site; whatever is left waits for the next run.
// Without data/site/booth.json, or with one that lists nothing (or only sample data), it writes an empty manifest
// and empties the folder; with one it can't read, it writes an empty manifest and keeps the folder for next time.
//
// Settings (environment variables):
//   BOOTH_MEDIA=0              do nothing at all: the folder and its manifest stay exactly as they are
//   BOOTH_MEDIA_MINUTES=15     the time for downloads, in minutes (0 = start none)
//   BOOTH_MEDIA_RETRY_WAITS    the waits before the 2nd and 3rd try, in milliseconds ("3000,10000"; tests: "0,0")
// Options: --dry-run, --root <folder> (another copy of the repository; the default is the one this file is in).
// Node.js 20 or newer (its own fetch); no npm package.

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as core from "./booth-media-core.mjs";

// The committee's robot, named as config/site.yml names it to the websites the sync reads (sources.crawler.user_agent).
const USER_AGENT = "NETA65-GrapevineCommitteeBot/2.0 (+https://github.com/NETA65/aagrapevine)";
const TZ = "America/Chicago";
const DEFAULT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const IN_ACTIONS = process.env.GITHUB_ACTIONS === "true";
const WARNING_TITLE = "Booth display: a file was not saved for offline";
const MAX_WARNINGS = 10;                                     // GitHub shows about 10 warnings a step; the log has all

const USAGE = `Usage: node scripts/build/booth-media.mjs [--dry-run] [--root <folder>]
  Saves the booth display's photos and videos (data/site/booth.json) in .cache/booth-media/ for the build.
  --dry-run        only print what a run would do now
  --root <folder>  the repository's folder (default: the one this script is in)
  BOOTH_MEDIA=0 in the environment: do nothing.`;

const log = (...a) => console.log(...a);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class UsageError extends Error {}

function parseArgs(argv) {
  const out = { dryRun: false, help: false, root: DEFAULT_ROOT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dry-run" || a === "-n") out.dryRun = true;
    else if (a === "--help" || a === "-h") out.help = true;
    else if (a === "--root" || a.startsWith("--root=")) {
      const v = a === "--root" ? argv[++i] : a.slice("--root=".length);
      if (!v) throw new UsageError("--root needs a folder");
      out.root = path.resolve(v);
    } else throw new UsageError(`unknown option: ${a}`);
  }
  return out;
}

function envNumber(name, fallback, lo, hi) {
  const raw = String(process.env[name] ?? "").trim();
  const n = raw === "" ? NaN : Number(raw);
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback;
}

function retryWaits() {
  const raw = String(process.env.BOOTH_MEDIA_RETRY_WAITS ?? "").trim();
  if (!raw) return [...core.RETRY_WAITS_MS];
  const waits = raw.split(/[,\s]+/).filter(Boolean).map(Number).filter((n) => Number.isFinite(n) && n >= 0);
  return waits.length ? waits.map((n) => Math.min(n, 120000)) : [...core.RETRY_WAITS_MS];
}

// Today in Central time ("2026-10-02"): a file whose "until" day has passed is not saved any more.
const centralToday = () =>
  new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

function readText(file) {
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return "";
  }
}

// data/site/booth.json → { state, items, error }: "ok", "missing", "empty" (nothing in the file), "fixture" (sample
// data, which names no real Drive file) or "broken" (it can't be read — the saved copies are then kept).
function readBooth(file) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch (e) {
    return e && e.code === "ENOENT" ? { state: "missing", items: [] } : { state: "broken", items: [], error: String(e?.message || e) };
  }
  text = text.replace(/^﻿/, "");
  if (!text.trim()) return { state: "empty", items: [] };
  let doc;
  try {
    doc = JSON.parse(text);
  } catch (e) {
    return { state: "broken", items: [], error: `it is not valid JSON (${e.message})` };
  }
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) return { state: "broken", items: [], error: "it is not a JSON object" };
  if (doc.fixture === true) return { state: "fixture", items: [] };
  const items = Array.isArray(doc.items) ? doc.items : [];
  return { state: items.length ? "ok" : "empty", items };
}

// What is in .cache/booth-media/files/ now: the files with their sizes, and anything else (a folder) by name.
function listSaved(dir) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return { files: [], others: [] };
  }
  const files = [];
  const others = [];
  for (const e of entries) {
    if (!e.isFile()) { others.push(e.name); continue; }
    let bytes = null;
    try {
      bytes = fs.statSync(path.join(dir, e.name)).size;
    } catch { /* gone meanwhile: counted as unknown */ }
    files.push({ name: e.name, bytes });
  }
  files.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  return { files, others };
}

// A kept file's manifest entry (its type from its name; a picture's width and height from its first bytes), or null
// when it can't be read.
async function describe(fileId, file, filePath, group) {
  try {
    const bytes = (await fsp.stat(filePath)).size;
    const entry = { file_id: fileId, file, bytes, type: core.typeForExt(path.extname(file)), w: null, h: null };
    if (group === "picture") {
      const size = core.imageSize(await fsp.readFile(filePath));
      if (size) Object.assign(entry, { w: size.w, h: size.h });
    }
    return entry;
  } catch {
    return null;
  }
}

async function readHead(file, n) {
  const fh = await fsp.open(file, "r");
  try {
    const buf = Buffer.alloc(n);
    const { bytesRead } = await fh.read(buf, 0, n, 0);
    return buf.subarray(0, bytesRead);
  } finally {
    await fh.close();
  }
}

// Written to a temporary name first, then renamed: a stopped run never leaves half a manifest.
async function writeManifest(file, entries, skipped) {
  const doc = core.manifestOf(entries, skipped, new Date().toISOString());
  const tmp = `${file}.tmp`;
  await fsp.writeFile(tmp, JSON.stringify(doc, null, 1) + "\n", "utf8");
  await fsp.rename(tmp, file);
}

// ---------------------------------------------------------------------------------------------- one download
// Why a download did not work: core.reasonText words each `code`; `retry` = worth another try now.
class Stop extends Error {
  constructor(code, detail = "", retry = false, extra = {}) {
    super(detail || code);
    Object.assign(this, { code, detail, retry, extra });
  }
}

// Answers worth another try a few seconds later (busy, a hiccup); 403 / 404 are not: the file is not public (any
// more) or not there — the next run asks again anyway.
const RETRY_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

const netError = (e) => String(e?.cause?.code || e?.cause?.message || e?.message || e || "no answer");

// One try: the answer is checked (no web page, the announced size, the file's own size from booth.json) and saved
// under the plan's stem with the extension the answer's type gives. In progress it is a ".part" file in
// .cache/booth-media/tmp/ — outside the published folder, so a stopped run never publishes half a video.
async function fetchOnce(d, timeoutMs, ctx) {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  const tooSlow = () => `no complete answer within ${Math.round(timeoutMs / 1000)} s`;
  const tmp = path.join(ctx.tmpDir, `${d.stem}.part`);
  try {
    let res;
    try {
      res = await fetch(d.url, {
        headers: { "User-Agent": USER_AGENT, Accept: d.group === "picture" ? "image/*,*/*;q=0.8" : "*/*" },
        redirect: "follow", signal: ac.signal,
      });
    } catch (e) {
      throw new Stop("failed", ac.signal.aborted ? tooSlow() : netError(e), true);
    }
    if (!res.ok) {
      res.body?.cancel().catch(() => {});
      // (Google's picture address answers 400 for a file it can't find or show)
      const hint = [400, 403, 404].includes(res.status)
        ? " — is the file still in the booth folder, shared as “Anyone with the link”?" : "";
      throw new Stop("failed", `HTTP ${res.status}${hint}`, RETRY_STATUS.has(res.status));
    }
    const type = res.headers.get("content-type") || "";
    const header = String(res.headers.get("content-length") || "").trim();
    // (a compressed answer announces its compressed size, and fetch hands over the bytes uncompressed: no check then)
    const encoded = !/^(identity)?$/i.test(String(res.headers.get("content-encoding") || "").trim());
    const declared = /^\d+$/.test(header) && !encoded ? Number(header) : null;
    // Over d.max_bytes. A video or sound file of unknown size (d.file_bytes set: main capped it at the room left in
    // the folder) is over the FOLDER's limit when that room was the smaller cap — and, with an announced size,
    // that size is within the one-file limit —; otherwise it is too big for one file.
    const tooBig = (bytes, atLeast) => {
      if (d.group !== "media") {
        return new Stop("failed", `the answer is too big for a picture (${atLeast ? "over " : ""}${core.formatBytes(bytes)})`);
      }
      const room = d.file_bytes !== undefined && d.max_bytes < d.file_bytes && (atLeast || bytes <= d.file_bytes);
      return new Stop(room ? "over_limit" : "too_big", "", false, { bytes, atLeast });
    };
    const refuse = (err) => {
      res.body?.cancel().catch(() => {});
      throw err;
    };
    if (core.isHtml(null, type)) refuse(new Stop("html"));
    if (declared !== null && declared > d.max_bytes) refuse(tooBig(declared, false));
    // (not tried again now: the Drive file has most likely changed since the sync wrote booth.json — the next sync
    // gives its new size)
    if (d.expect_bytes !== null && declared !== null && declared !== d.expect_bytes) {
      refuse(new Stop("incomplete", `Google announced ${declared} bytes, booth.json says ${d.expect_bytes}`));
    }

    // The body: a picture is kept in memory (it is small), a video or sound file goes straight to disk. Leaving the
    // loop early (too big) stops the download.
    const limit = d.expect_bytes ?? d.max_bytes;
    const parts = [];
    let got = 0;
    let fh = null;
    if (!res.body) refuse(new Stop("incomplete", "the answer was empty", true));
    try {
      if (d.group === "media") fh = await fsp.open(tmp, "w");
      for await (const chunk of res.body) {
        got += chunk.byteLength;
        if (got > limit) {
          if (d.expect_bytes !== null) throw new Stop("incomplete", `more than the file's ${d.expect_bytes} bytes`, true);
          throw tooBig(got, true);
        }
        if (fh) await fh.write(chunk);
        else parts.push(chunk);
      }
    } catch (e) {
      if (e instanceof Stop) throw e;
      throw new Stop("failed", ac.signal.aborted ? tooSlow() : netError(e), true);
    } finally {
      if (fh) await fh.close().catch(() => {});
    }
    if (got === 0) throw new Stop("incomplete", "the answer was empty", true);
    if (declared !== null && got !== declared) throw new Stop("incomplete", `${got} of ${declared} bytes arrived`, true);
    if (d.expect_bytes !== null && got !== d.expect_bytes) {
      throw new Stop("incomplete", `${got} of the file's ${d.expect_bytes} bytes arrived`, true);
    }

    const body = fh ? null : Buffer.concat(parts);
    let size = null;
    let ctype = type;
    try {
      if (core.isHtml(body ? body.subarray(0, 1024) : await readHead(tmp, 1024), "")) throw new Stop("html");
      if (d.group === "picture") {
        size = core.imageSize(body);
        if (!size && !core.baseType(type).startsWith("image/")) {
          throw new Stop("failed", `the answer is not a picture (${core.baseType(type) || "no type given"})`);
        }
        if (!core.extFor(type, "") && size) ctype = size.type;   // a vague type ("application/octet-stream"): the bytes say
      }
      const file = `${d.stem}.${core.extOf(ctype, d.name, d.mime)}`;
      if (body) await fsp.writeFile(tmp, body);
      await fsp.rename(tmp, path.join(ctx.filesDir, file));
      return { ok: true, file, bytes: got, type: core.typeForExt(path.extname(file)), w: size?.w ?? null, h: size?.h ?? null };
    } catch (e) {
      if (e instanceof Stop) throw e;
      throw new Stop("failed", `it could not be saved: ${netError(e)}`);
    }
  } catch (e) {
    if (e instanceof Stop) return { ok: false, code: e.code, detail: e.detail, retry: e.retry, ...e.extra };
    throw e;                                                 // a mistake in this script: let it show
  } finally {
    clearTimeout(timer);
    await fsp.rm(tmp, { force: true }).catch(() => {});
  }
}

// Up to core.ATTEMPTS tries with a wait between them, never past the time for downloads.
async function download(d, ctx) {
  let result = { ok: false, code: "out_of_time" };
  for (let attempt = 1; attempt <= core.ATTEMPTS; attempt++) {
    const left = ctx.deadline - Date.now();
    if (left < 1000) return { ok: false, code: "out_of_time" };
    result = await fetchOnce(d, Math.min(d.timeout_ms, left), ctx);
    if (result.ok || !result.retry || attempt === core.ATTEMPTS) return result;
    const wait = ctx.waits[Math.min(attempt - 1, ctx.waits.length - 1)] ?? 0;
    if (Date.now() + wait + 1000 >= ctx.deadline) return { ok: false, code: "out_of_time" };
    log(`    try ${attempt} of ${core.ATTEMPTS}: ${result.detail || result.code} — trying again in ${Math.round(wait / 1000)} s`);
    await sleep(wait);
  }
  return result;
}

// ---------------------------------------------------------------------------------------------- the run
const STATE_WORDS = {
  ok: "read", missing: "not there (nothing to save)", empty: "lists no booth files",
  fixture: "sample data (nothing to save)", broken: "could not be read",
};
const limitWords = (limits) =>
  `${core.mbLabel(limits.fileBytes)} for one video or sound file, ${core.mbLabel(limits.totalBytes)} in all`;
const who = (x) => x.name || x.file_id || "(a file without a name)";

function printPlan(p, booth) {
  log("Booth display media — what a run would do now (--dry-run: nothing is downloaded, deleted or written)");
  log(`  data/site/booth.json: ${STATE_WORDS[booth.state]}${booth.error ? ` (${booth.error})` : ""}`);
  log(`  limits: ${limitWords(p.limits)}`);
  const list = (title, rows, line) => {
    log(`  ${title}: ${rows.length}`);
    for (const r of rows) log(`    - ${line(r)}`);
  };
  list("download", p.downloads, (d) => `${who(d)} → ${d.stem}.* (${d.group === "picture" ? "a picture" : d.expect_bytes !== null
    ? core.formatBytes(d.expect_bytes) : "size not known"}) from ${d.url}`);
  list("keep (saved by an earlier run)", p.reuse, (r) => `${who(r)} = ${r.file} (${core.formatBytes(r.bytes)})`);
  list("delete", p.delete, (n) => n);
  list("skip", p.skipped, (s) => `${who(s)}: ${s.reason}`);
  const unknown = p.downloads.filter((d) => d.group === "media" && d.expect_bytes === null).length;
  log(`  the folder afterwards: about ${core.formatBytes(p.bytes)}`
    + `${unknown ? ` + ${unknown} video or sound file(s) of unknown size (each fills at most the room left)` : ""}`);
}

function report(p, booth, { entries, skipped, downloaded, removed, seconds }) {
  const total = entries.reduce((n, e) => n + e.bytes, 0);
  const got = downloaded.reduce((n, e) => n + e.bytes, 0);
  const line = `${entries.length} file(s) saved for offline, ${core.formatBytes(total)} (limits: ${limitWords(p.limits)}) — `
    + `${downloaded.length} downloaded (${core.formatBytes(got)}), ${entries.length - downloaded.length} kept from the last run, `
    + `${removed} removed; ${seconds} s`;
  log(`Booth display media: ${line}.`);
  if (booth.state !== "ok") log(`  data/site/booth.json ${STATE_WORDS[booth.state]}${booth.error ? `: ${booth.error}` : ""}.`);
  const notSaved = skipped.filter((s) => s.code !== "expired");
  const expired = skipped.length - notSaved.length;
  if (expired) log(`  ${expired} file(s) past their last day: not saved.`);
  if (notSaved.length) {
    log(`  Not saved (${notSaved.length}) — the booth shows those pictures from Google's copy while online and leaves`
      + " those videos and sounds out:");
    for (const s of notSaved) log(`    - ${who(s)}: ${s.reason}`);
  }
  if (IN_ACTIONS) {
    if (booth.state === "broken") {
      log(core.annotation("Booth display",
        `data/site/booth.json could not be read (${booth.error}); the saved copies are kept for the next run`));
    }
    for (const s of notSaved.slice(0, MAX_WARNINGS)) log(core.annotation(WARNING_TITLE, `${who(s)}: ${s.reason}`));
    if (notSaved.length > MAX_WARNINGS) {
      log(core.annotation(WARNING_TITLE, `…and ${notSaved.length - MAX_WARNINGS} more (see the log of this step)`));
    }
  }
  const summary = process.env.GITHUB_STEP_SUMMARY;
  if (summary) {
    const md = [`**Booth display (copies for offline):** ${line}.`];
    if (notSaved.length) md.push("", ...notSaved.map((s) => `- Not saved: ${who(s).replace(/[|`]/g, "'")} — ${s.reason}`));
    try {
      fs.appendFileSync(summary, md.join("\n") + "\n", "utf8");
    } catch { /* the summary is a nicety */ }
  }
}

async function main(argv) {
  let args;
  try {
    args = parseArgs(argv);
  } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    console.error(`booth-media: ${e.message}\n${USAGE}`);
    return 2;
  }
  if (args.help) { log(USAGE); return 0; }
  if (String(process.env.BOOTH_MEDIA ?? "").trim() === "0") {
    log("BOOTH_MEDIA=0: the booth display's saved files are left as they are (nothing downloaded, nothing deleted).");
    return 0;
  }
  const started = Date.now();
  const at = (p) => path.join(args.root, p);
  const booth = readBooth(at("data/site/booth.json"));
  const cfg = { ...core.parseBoothConfig(readText(at("config/site.yml"))), today: centralToday() };
  const saved = listSaved(at(core.FILES_DIR));
  const p = core.plan({ items: booth.items }, cfg, saved.files);
  // booth.json can't be read: keep every saved copy for the run that can (and save nothing new now).
  p.delete = booth.state === "broken" ? [] : [...p.delete, ...saved.others];
  if (args.dryRun) { printPlan(p, booth); return 0; }

  const ctx = {
    filesDir: at(core.FILES_DIR), tmpDir: at(core.TMP_DIR), waits: retryWaits(),
    deadline: started + envNumber("BOOTH_MEDIA_MINUTES", 15, 0, 120) * 60 * 1000,
  };
  const manifest = at(core.MANIFEST);
  await fsp.mkdir(ctx.filesDir, { recursive: true });
  await fsp.rm(manifest, { force: true });                   // never a manifest naming a file this run may delete
  await fsp.rm(ctx.tmpDir, { recursive: true, force: true });  // what a stopped run left half-downloaded
  await fsp.mkdir(ctx.tmpDir, { recursive: true });

  // 1. The files kept from the last run, then the manifest of just those (before anything is deleted or added).
  const entries = [];
  const skipped = [...p.skipped];
  for (const r of p.reuse) {
    const entry = await describe(r.file_id, r.file, path.join(ctx.filesDir, r.file), r.group);
    if (entry) entries.push(entry);
    else {
      p.delete.push(r.file);
      skipped.push({ file_id: r.file_id, name: r.name, kind: r.kind, code: "failed",
        reason: core.reasonText("failed", { detail: "its saved copy could not be read" }) });
    }
  }
  await writeManifest(manifest, entries, skipped);
  // 2. What is no longer listed.
  let removed = 0;
  for (const name of p.delete) {
    await fsp.rm(path.join(ctx.filesDir, name), { recursive: true, force: true });
    removed++;
  }
  // 3. The downloads, in the plan's order, while the folder stays within its limit (now with the real sizes). A
  //    video or sound file whose size booth.json does not give (none without GOOGLE_API_KEY) may take the room
  //    really left: its download stops there (over the folder's limit) or at the one-file limit (too big),
  //    whichever comes first — and the files after it are still tried.
  let used = entries.reduce((n, e) => n + e.bytes, 0);
  const downloaded = [];
  if (p.downloads.length) log(`Downloading ${p.downloads.length} file(s) for the booth display (limits: ${limitWords(p.limits)})…`);
  for (const d of p.downloads) {
    const base = { file_id: d.file_id, name: d.name, kind: d.kind };
    const room = p.limits.totalBytes - used;
    const unknown = d.group === "media" && d.expect_bytes === null;
    if (unknown ? room <= 0 : !core.fits(used, d.estimate, p.limits)) {
      skipped.push({ ...base, code: "over_limit", reason: core.reasonText("over_limit", { limit: p.limits.totalBytes }) });
      continue;
    }
    const res = await download(unknown ? { ...d, max_bytes: Math.min(d.max_bytes, room), file_bytes: p.limits.fileBytes } : d, ctx);
    if (res.ok && !core.fits(used, res.bytes, p.limits)) {
      await fsp.rm(path.join(ctx.filesDir, res.file), { force: true });
      skipped.push({ ...base, code: "over_limit", reason: core.reasonText("over_limit", { limit: p.limits.totalBytes }) });
      log(`  - ${who(d)}: over the folder's limit once downloaded (${core.formatBytes(res.bytes)}) — not kept`);
      continue;
    }
    if (!res.ok) {
      const limit = res.code === "over_limit" ? p.limits.totalBytes : p.limits.fileBytes;
      const reason = core.reasonText(res.code, { detail: res.detail, bytes: res.bytes, atLeast: res.atLeast, limit });
      skipped.push({ ...base, code: res.code, reason });
      log(`  - ${who(d)}: ${reason}`);
      continue;
    }
    used += res.bytes;
    const entry = { file_id: d.file_id, file: res.file, bytes: res.bytes, type: res.type, w: res.w, h: res.h };
    entries.push(entry);
    downloaded.push(entry);
    log(`  + ${who(d)} → ${res.file} (${core.formatBytes(res.bytes)}${res.w ? `, ${res.w}×${res.h}` : ""})`);
    await writeManifest(manifest, entries, skipped);
  }
  // 4. The final manifest (with every skipped file and why), and the report.
  await writeManifest(manifest, entries, skipped);
  await fsp.rm(ctx.tmpDir, { recursive: true, force: true });
  report(p, booth, { entries, skipped, downloaded, removed, seconds: Math.round((Date.now() - started) / 1000) });
  return 0;
}

process.exitCode = await main(process.argv.slice(2));
