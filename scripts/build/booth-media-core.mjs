// The booth display's photos and videos, saved for offline use — the PURE half of scripts/build/booth-media.mjs
// (the downloader that runs in the "Build & publish website" job of .github/workflows/update.yml, just before
// Eleventy builds the site). Nothing here goes on the network or writes a file, so tests/test_booth_media.py can
// check every rule through Node.js, offline.
//
// The whole story (r5 SPEC §2.3): data/site/booth.json (written by the daily sync, scripts/sync/build_data.py)
// lists the files of the committee's Drive booth folder. Each photo or poster is fetched as Google's picture of it,
// 1920 pixels at most (`image_url`; for a document or a slide deck the same address gives a picture of its first
// page), and each video or sound file as the file itself (`download_url`). A message (a text file) needs nothing.
// The files are kept in .cache/booth-media/files/ — never in git (far too big), but in GitHub's Actions cache from
// one run to the next, so a run only downloads what is new or changed — and Eleventy publishes that folder at
// /about/booth/media/ (eleventy.config.js). .cache/booth-media/manifest.json says which saved file belongs to which
// Drive file; the show's data (src/_data/booth.js) points a slide at the saved copy only when the manifest lists
// it, and that is what lets a device keep the booth playing offline once it has saved the show.
//
//   DEFAULTS, CEILING_MB          the size limits: config/site.yml booth.max_file_mb (95) and booth.max_total_mb
//                                 (400); whatever the file says, neither goes above CEILING_MB (800): GitHub Pages
//                                 refuses a site over 1 GB, and the rest of the site needs its room (about 30 MB)
//   parseBoothConfig(text)        → { max_file_mb, max_total_mb } from config/site.yml's TEXT. A tiny reader of
//                                 the `booth:` section, not a YAML library: the downloader needs no npm package
//                                 (a number it can't read keeps its default)
//   caps(cfg)                     → { fileBytes, totalBytes } (1 MB = 1,048,576 bytes, as the site counts sizes)
//   plan(booth, cfg, cached)      → what this run does, in booth.json's order (the files marked "first" first):
//                                   downloads [{ file_id, name, kind, group, stem, url, estimate, expect_bytes,
//                                               max_bytes, timeout_ms }]   (estimate: a picture's guess, a video's
//                                               or sound file's size — 0 when booth.json gives none: the
//                                               downloader then caps it at the room really left)
//                                   reuse     [{ file_id, name, kind, group, file, bytes }]   (kept from last run)
//                                   delete    ["<name in files/>", …]   (no longer listed, or not ours)
//                                   skipped   [{ file_id, name, kind, code, reason }]
//                                   bytes     the folder's size once done, as far as it is known before the
//                                             downloads (saved files, known sizes, the pictures' guesses — not
//                                             the video and sound files of unknown size)
//                                   limits    { fileBytes, totalBytes }
//                                 cfg = { max_file_mb, max_total_mb, today: "YYYY-MM-DD" (Central; optional) };
//                                 cached = the files already in .cache/booth-media/files: [{ name, bytes }]
//   fileName(item, contentType)   → "<stamp>-<slug>.<ext>": the stamp changes whenever the Drive file does (its id,
//                                 modified time and size), so a saved file never has to be checked again
//   stemOf(item), stampOf(item)   → "<stamp>-<slug>" / "<stamp>"
//   extFor(contentType, name)     → "jpg", "mp4" … from the answer's content type, else from the file's name;
//                                 "" when neither says
//   extOf(contentType, name, mime) → the same, then booth.json's `mime`, then "bin" (what fileName uses)
//   typeForExt(ext)               → "image/jpeg" … (what GitHub Pages will serve the file as)
//   imageSize(bytes)              → { type, w, h } | null — read from the file's first bytes: PNG, JPEG (a phone
//                                 photo turned by its EXIF note reports its turned size), GIF, WebP (VP8, VP8L,
//                                 VP8X)
//   isHtml(bytes, contentType)    → true when Google answered with a web page instead of the file (Drive's "can't
//                                 scan this file for viruses", "too many downloads", a sign-in page)
//   manifestOf(entries, skipped, built) → the manifest.json object
//   reasonText(code, values)      → the English words of a skipped file's reason
//   fits(used, bytes, limits)     → does the folder stay within its limit? (the downloader, with the real sizes)
//   annotation(title, message)    → "::warning title=…::…" (a yellow line on the run's page on GitHub)
//   formatBytes(n), mbLabel(n)    → "12.3 MB" (a size), "95 MB" (a limit)
//
// The skipped files' `code` (the manifest keeps it next to the English `reason`, so the show's data can word the
// note in both languages): too_big · over_limit · expired (past its "until" day: never shown again, so not saved;
// no warning) · no_file (no Drive file id) · failed · html · incomplete · out_of_time (the run's time for downloads
// ran out). Each run plans afresh: the last five are simply tried again; the first three stay so until the file, the
// limits or the day change.

import crypto from "node:crypto";

// ---------------------------------------------------------------------------------------------- the folders
// Relative to the repository (the downloader and Eleventy both run from its root).
export const CACHE_DIR = ".cache/booth-media";
export const FILES_DIR = ".cache/booth-media/files";        // published as /about/booth/media/
export const TMP_DIR = ".cache/booth-media/tmp";            // downloads in progress (never published)
export const MANIFEST = ".cache/booth-media/manifest.json";

// ---------------------------------------------------------------------------------------------- the limits
export const MB = 1024 * 1024;
export const DEFAULTS = Object.freeze({ max_file_mb: 95, max_total_mb: 400 });
export const CEILING_MB = 800;
// A photo's or poster's size before it is downloaded is a guess: booth.json gives the ORIGINAL file's size (a
// 12 MB camera photo, a 5 MB document), but Google's 1920-pixel picture of it is usually well under 1 MB.
export const PICTURE_GUESS_BYTES = 2 * MB;
// …and an answer bigger than this is not a picture of that size (it is refused; pictures are read into memory).
export const PICTURE_MAX_BYTES = 30 * MB;
// Each download's time: a picture 60 s, a video or sound file 8 minutes; 3 attempts, waiting 3 s and then 10 s.
export const TIMEOUT_MS = Object.freeze({ picture: 60 * 1000, media: 8 * 60 * 1000 });
export const ATTEMPTS = 3;
export const RETRY_WAITS_MS = Object.freeze([3000, 10000]);

// What each kind of booth file needs (booth.json `kind`, from the Drive name's file type — scripts/sync/booth_names.py).
const GROUP = { photo: "picture", poster: "picture", video: "media", audio: "media" };

// ---------------------------------------------------------------------------------------------- config/site.yml
// `booth:` at the start of a line, then its own lines (indented) until the next top-level key:
//     booth:
//       max_file_mb: 95          # a comment
//       max_total_mb: "400"
//       defaults: { … }          (deeper keys are not looked at)
// The one-line form `booth: { max_file_mb: 95, max_total_mb: 400 }` works too.
function readNumber(raw) {
  let s = String(raw ?? "").trim();
  s = s.replace(/\s+#.*$/, "").trim();                       // "95   # comment" (YAML wants a space before #)
  const q = /^(["'])(.*)\1$/.exec(s);
  if (q) s = q[2].trim();
  if (!/^\+?(\d+(\.\d*)?|\.\d+)$/.test(s)) return null;      // a plain number, nothing else (no "95MB", no "-1")
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

const clampMb = (n, fallback) => (n === null || n === undefined ? fallback : Math.min(CEILING_MB, Math.max(0, n)));

export function parseBoothConfig(text) {
  const found = {};
  const lines = String(text ?? "").replace(/^﻿/, "").split(/\r?\n/);
  const at = lines.findIndex((l) => /^booth\s*:(\s|$)/.test(l));
  if (at >= 0) {
    const flow = /^booth\s*:\s*\{(.*)\}\s*(#.*)?$/.exec(lines[at]);
    if (flow) {
      for (const part of flow[1].split(",")) {
        const m = /^\s*(max_file_mb|max_total_mb)\s*:\s*(.*)$/.exec(part);
        if (m) found[m[1]] = readNumber(m[2]);
      }
    } else if (/^booth\s*:\s*(#.*)?$/.test(lines[at])) {
      let indent = null;
      for (let i = at + 1; i < lines.length; i++) {
        const line = lines[i];
        if (/^\s*(#.*)?$/.test(line)) continue;              // a blank line or a comment
        const lead = /^ */.exec(line)[0].length;
        if (lead === 0) break;                               // the next top-level key: the section is over
        if (indent === null) indent = lead;
        if (lead !== indent) continue;                       // a deeper key (under defaults:)
        const m = /^\s*(max_file_mb|max_total_mb)\s*:(.*)$/.exec(line);
        if (m) found[m[1]] = readNumber(m[2]);
      }
    }
  }
  return {
    max_file_mb: clampMb(found.max_file_mb, DEFAULTS.max_file_mb),
    max_total_mb: clampMb(found.max_total_mb, DEFAULTS.max_total_mb),
  };
}

export function caps(cfg) {
  const c = cfg || {};
  const num = (v, d) => clampMb(typeof v === "number" ? (Number.isFinite(v) ? v : null) : readNumber(v), d);
  return {
    fileBytes: Math.floor(num(c.max_file_mb, DEFAULTS.max_file_mb) * MB),
    totalBytes: Math.floor(num(c.max_total_mb, DEFAULTS.max_total_mb) * MB),
  };
}

// ---------------------------------------------------------------------------------------------- names
// A saved file's name is part of its web address (/about/booth/media/<name>), so it is plain ASCII: the stamp,
// a dash, a few words of the title ("Mi primer número" → "mi-primer-numero") and the extension.
export function slugify(text, max = 40) {
  let s = String(text ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  if (s.length > max) {
    s = s.slice(0, max);
    const cut = s.lastIndexOf("-");
    s = (cut >= max / 2 ? s.slice(0, cut) : s).replace(/-+$/, "");
  }
  return s || "file";
}

const fileIdOf = (item) => {
  const id = String(item?.file_id ?? "").trim() || String(item?.id ?? "").replace(/^drive:/, "").trim();
  return /^[A-Za-z0-9_-]{10,200}$/.test(id) ? id : "";
};
const sizeOf = (item) => {
  const v = item?.size_bytes;
  const n = typeof v === "number" ? v : typeof v === "string" && /^\d+$/.test(v.trim()) ? Number(v) : NaN;
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
};

// booth.json's `stamp` (a short hash of the file's id, modified time and size), tidied to a-z0-9; when a row has
// none, the same kind of hash made here, so a file still gets a name that changes when the file does.
export function stampOf(item) {
  const s = String(item?.stamp ?? "").toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 16);
  if (s) return s;
  const basis = `${fileIdOf(item)}|${item?.modified ?? ""}|${sizeOf(item) ?? ""}`;
  return crypto.createHash("sha1").update(basis).digest("hex").slice(0, 10);
}

const withoutExt = (name) => String(name ?? "").replace(/\.[A-Za-z0-9]{1,5}$/, "");

export function stemOf(item) {
  return `${stampOf(item)}-${slugify(String(item?.title ?? "").trim() || withoutExt(item?.name))}`;
}

// The answer's content type → the extension. The booth's own kinds first (r5 SPEC §2.3), then their usual aliases.
const EXT_BY_TYPE = {
  "image/jpeg": "jpg", "image/jpg": "jpg", "image/pjpeg": "jpg", "image/png": "png", "image/webp": "webp",
  "image/gif": "gif", "image/avif": "avif", "image/svg+xml": "svg", "image/bmp": "bmp",
  "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov", "video/x-m4v": "m4v", "video/ogg": "ogv",
  "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/mpeg3": "mp3", "audio/x-mpeg": "mp3",
  "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/m4a": "m4a", "audio/aac": "aac", "audio/x-aac": "aac",
  "audio/ogg": "ogg", "audio/opus": "opus", "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
  "audio/vnd.wave": "wav", "audio/webm": "webm", "audio/flac": "flac", "audio/x-flac": "flac",
};
// The extensions a saved file may have, with the type GitHub Pages serves each one as. A name's extension outside
// this list says nothing (a file's name never decides that it is, say, ".exe").
const TYPE_BY_EXT = {
  jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", gif: "image/gif", avif: "image/avif",
  svg: "image/svg+xml", bmp: "image/bmp",
  mp4: "video/mp4", m4v: "video/mp4", webm: "video/webm", mov: "video/quicktime", ogv: "video/ogg",
  mp3: "audio/mpeg", m4a: "audio/mp4", aac: "audio/aac", ogg: "audio/ogg", oga: "audio/ogg", opus: "audio/ogg",
  wav: "audio/wav", flac: "audio/flac",
};
const SAME_EXT = { jpeg: "jpg" };

export const baseType = (contentType) => String(contentType ?? "").split(";")[0].trim().toLowerCase();

export function extFor(contentType, name) {
  const byType = EXT_BY_TYPE[baseType(contentType)];
  if (byType) return byType;
  const m = /\.([A-Za-z0-9]{1,5})$/.exec(String(name ?? "").trim());
  const ext = m ? m[1].toLowerCase() : "";
  return Object.hasOwn(TYPE_BY_EXT, ext) ? SAME_EXT[ext] || ext : "";
}

export function typeForExt(ext) {
  const e = String(ext ?? "").replace(/^\./, "").toLowerCase();
  return Object.hasOwn(TYPE_BY_EXT, e) ? TYPE_BY_EXT[e] : "application/octet-stream";
}

// The answer's type, else the file's name, else the type Drive gave the file in booth.json, else ".bin".
export const extOf = (contentType, name, mime) => extFor(contentType, name) || extFor(mime, "") || "bin";

export function fileName(item, contentType) {
  return `${stemOf(item)}.${extOf(contentType, item?.name, item?.mime)}`;
}

// A saved file this script made: "<stamp>-<slug>.<ext>" → its stamp (anything else in the folder is not ours).
const SAVED = /^([a-z0-9]{1,16})-([a-z0-9-]{1,40})\.([a-z0-9]{1,5})$/;
export const savedStamp = (name) => (SAVED.exec(String(name ?? "")) || [])[1] || "";

// ---------------------------------------------------------------------------------------------- the plan
const isWebAddress = (u) => /^https?:\/\/[^\s/?#]+/i.test(String(u ?? ""));
const DAY = /^\d{4}-\d{2}-\d{2}$/;
export const mbLabel = (bytes) => `${Math.round((bytes / MB) * 10) / 10} MB`;   // a limit: "95 MB", "0.5 MB"

// Where to download a file from: booth.json's address, or the one Google gives every public file of that id.
export function sourceUrl(item, group) {
  const id = fileIdOf(item);
  if (group === "picture") {
    if (isWebAddress(item?.image_url)) return String(item.image_url).trim();
    return id ? `https://lh3.googleusercontent.com/d/${id}=s1920` : "";
  }
  if (isWebAddress(item?.download_url)) return String(item.download_url).trim();
  return id ? `https://drive.usercontent.google.com/download?id=${id}&export=download&confirm=t` : "";
}

// The English words of each reason (the run's log, its yellow warnings and the manifest's `reason`).
export function reasonText(code, v = {}) {
  switch (code) {
    case "too_big":
      // (atLeast: the size was not known before the download, which stopped at the limit)
      return v.atLeast
        ? `too big to save for offline (over the ${mbLabel(v.limit)} one video or sound file may have — config/site.yml booth.max_file_mb)`
        : `too big to save for offline (${formatBytes(v.bytes)}; one video or sound file may have ${mbLabel(v.limit)} — config/site.yml booth.max_file_mb)`;
    case "over_limit":
      return `not saved for offline: the booth folder's saved files would pass ${mbLabel(v.limit)} (config/site.yml booth.max_total_mb; the files marked "first" and the ones listed first are kept first)`;
    case "expired":
      return `past its last day (${v.until}), so it is not saved`;
    case "no_file":
      return "no Drive file id in data/site/booth.json";
    case "out_of_time":
      return "not downloaded: this run's time for downloads ran out (the next run tries again)";
    case "html":
      return "Google Drive answered with a web page instead of the file (too many downloads of it today, or Drive could not check it for viruses); the next run tries again";
    case "incomplete":
      return `the download was incomplete or not the file's size (${v.detail || "the sizes did not match"}); the next run tries again`;
    default:
      return `the download failed (${v.detail || "no answer"}); the next run tries again`;
  }
}

function normalizeCached(cached) {
  const out = [];
  const seen = new Set();
  for (const c of Array.isArray(cached) ? cached : []) {
    const name = typeof c === "string" ? c : String(c?.name ?? "");
    if (!name || seen.has(name)) continue;
    seen.add(name);
    const b = c && typeof c === "object" ? c.bytes : null;
    out.push({ name, bytes: typeof b === "number" && Number.isFinite(b) && b >= 0 ? Math.floor(b) : null });
  }
  return out;
}

// booth.json's order (already "first" files first, then the order numbers, then the names — build_data.py), with
// the "first" files moved to the front once more in case: when the folder is over its limit, they are kept first.
function ordered(items) {
  const list = Array.isArray(items) ? items.filter((x) => x && typeof x === "object" && !Array.isArray(x)) : [];
  return [...list.filter((x) => x.first === true), ...list.filter((x) => x.first !== true)];
}

export function plan(booth, cfg, cached) {
  const limits = caps(cfg);
  const today = DAY.test(String(cfg?.today ?? "")) ? String(cfg.today) : "";
  const files = normalizeCached(cached);
  // The saved files by stamp: the stamp alone says "same Drive file, same version" (a new title only changes the
  // words after it, and the file is kept under its old name — a device that saved it keeps its copy).
  const byStamp = new Map();
  for (const f of files) {
    const st = savedStamp(f.name);
    if (st && f.bytes !== 0 && !byStamp.has(st)) byStamp.set(st, f);
  }
  const out = { downloads: [], reuse: [], delete: [], skipped: [], bytes: 0, limits };
  const kept = new Set();
  const seen = new Set();
  let used = 0;
  for (const item of ordered(booth?.items)) {
    const group = GROUP[String(item.kind ?? "")];
    if (!group) continue;                                    // a message or a file the booth can't show: nothing to save
    const base = { file_id: fileIdOf(item) || null, name: String(item.name || item.title || ""), kind: String(item.kind) };
    const skip = (code, v) => out.skipped.push({ ...base, code, reason: reasonText(code, v) });
    if (!base.file_id) { skip("no_file"); continue; }
    if (seen.has(base.file_id)) continue;                    // listed twice: once is enough
    seen.add(base.file_id);
    const until = String(item.until ?? "");
    if (today && DAY.test(until) && until < today) { skip("expired", { until }); continue; }
    const size = sizeOf(item);
    if (group === "media" && size !== null && size > limits.fileBytes) {
      skip("too_big", { bytes: size, limit: limits.fileBytes });
      continue;
    }
    const hit = byStamp.get(stampOf(item));
    if (hit && !kept.has(hit.name)) {
      const bytes = hit.bytes ?? 0;
      if (group === "media" && bytes > limits.fileBytes) { skip("too_big", { bytes, limit: limits.fileBytes }); continue; }
      if (used + bytes > limits.totalBytes) { skip("over_limit", { limit: limits.totalBytes }); continue; }
      used += bytes;
      kept.add(hit.name);
      out.reuse.push({ ...base, group, file: hit.name, bytes });
      continue;
    }
    // Pictures count too, by a guess until they are downloaded; a video or sound file by its size. One of UNKNOWN
    // size (booth.json gives no sizes without GOOGLE_API_KEY — the live sync's usual case) counts as nothing here
    // and is never skipped here: the downloader gives it the room really left once the files before it are saved
    // (at most the one-file limit), and stops it there. (Counted as big as it may be — 95 MB —, a run could plan
    // at most 4 of them in 400 MB, however small they really are, and leave the rest out of the show.)
    const unknown = group === "media" && size === null;
    const estimate = group === "picture" ? PICTURE_GUESS_BYTES : size ?? 0;
    if (!unknown && used + estimate > limits.totalBytes) { skip("over_limit", { limit: limits.totalBytes }); continue; }
    used += estimate;
    out.downloads.push({
      ...base, group, stem: stemOf(item), url: sourceUrl(item, group), estimate,
      expect_bytes: group === "media" ? size : null,
      max_bytes: group === "media" ? limits.fileBytes : PICTURE_MAX_BYTES,
      timeout_ms: TIMEOUT_MS[group], mime: String(item.mime ?? ""),
    });
  }
  out.delete = files.filter((f) => !kept.has(f.name)).map((f) => f.name);
  out.bytes = used;
  return out;
}

// The downloader's check with the REAL sizes, file by file in the same order: a file is kept only while the
// folder stays within the limit.
export const fits = (used, bytes, limits) => used + bytes <= limits.totalBytes;

// ---------------------------------------------------------------------------------------------- pictures
// The width and height the show lays a picture out with (manifest `w` / `h`), read from the first bytes of the file
// — each format keeps them in a fixed place near the start (a JPEG: in its frame header, after any notes).
const bytesOf = (b) => {
  if (b instanceof Uint8Array) return b;                     // (a Node Buffer is one too)
  if (b instanceof ArrayBuffer) return new Uint8Array(b);
  if (ArrayBuffer.isView(b)) return new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
  if (Array.isArray(b)) return Uint8Array.from(b);
  return new Uint8Array(0);
};
const be16 = (b, i) => (b[i] << 8) | b[i + 1];
const le16 = (b, i) => b[i] | (b[i + 1] << 8);
const be32 = (b, i) => ((b[i] << 24) >>> 0) + (b[i + 1] << 16) + (b[i + 2] << 8) + b[i + 3];
const le32 = (b, i) => (b[i] | (b[i + 1] << 8) | (b[i + 2] << 16) | (b[i + 3] << 24)) >>> 0;
const le24 = (b, i) => b[i] | (b[i + 1] << 8) | (b[i + 2] << 16);
const ascii = (b, i, n) => String.fromCharCode(...b.subarray(i, i + n));

// A JPEG's EXIF orientation (1–8; 1 when it has none), from its APP1 segment (bytes start…end). 5–8 = the camera
// was held turned a quarter: browsers show the picture turned, so its width and height trade places.
function exifOrientation(b, start, end) {
  if (end - start < 14 || ascii(b, start, 6) !== "Exif\0\0") return 1;
  const t = start + 6;                                       // the TIFF header: byte order, 42, where IFD0 is
  const order = ascii(b, t, 2);
  if (order !== "II" && order !== "MM") return 1;
  const u16 = (i) => (order === "II" ? le16(b, i) : be16(b, i));
  const u32 = (i) => (order === "II" ? le32(b, i) : be32(b, i));
  if (u16(t + 2) !== 42) return 1;
  const ifd = t + u32(t + 4);
  if (ifd + 2 > end) return 1;
  const count = u16(ifd);
  for (let k = 0; k < count; k++) {
    const e = ifd + 2 + k * 12;                              // tag, type, count, value: 12 bytes an entry
    if (e + 12 > end) break;
    if (u16(e) === 0x0112) {
      const v = u16(e + 8);
      return v >= 1 && v <= 8 ? v : 1;
    }
  }
  return 1;
}

function jpegSize(b) {
  let i = 2;
  let orient = 1;
  while (i + 4 <= b.length) {
    if (b[i] !== 0xff) return null;                          // not a marker where one belongs: not a JPEG we know
    const m = b[i + 1];
    if (m === 0xff) { i += 1; continue; }                    // a fill byte
    if (m === 0xd8 || m === 0x01 || (m >= 0xd0 && m <= 0xd7)) { i += 2; continue; }   // markers without a length
    if (m === 0xd9 || m === 0xda) return null;               // the end, or the picture data, before a frame header
    const len = be16(b, i + 2);
    if (len < 2) return null;
    if (m === 0xe1 && orient === 1) orient = exifOrientation(b, i + 4, Math.min(b.length, i + 2 + len));
    // SOF0–SOF15 (baseline, progressive …), but not DHT (C4), JPG (C8) or DAC (CC), which share the range
    if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) {
      if (i + 9 > b.length) return null;
      const h = be16(b, i + 5);
      const w = be16(b, i + 7);
      if (!w || !h) return null;
      return orient >= 5 ? { type: "image/jpeg", w: h, h: w } : { type: "image/jpeg", w, h };
    }
    i += 2 + len;
  }
  return null;
}

export function imageSize(bytes) {
  const b = bytesOf(bytes);
  let found = null;
  if (b.length >= 24 && be32(b, 0) === 0x89504e47 && be32(b, 4) === 0x0d0a1a0a && ascii(b, 12, 4) === "IHDR") {
    found = { type: "image/png", w: be32(b, 16), h: be32(b, 20) };
  } else if (b.length >= 10 && (ascii(b, 0, 6) === "GIF87a" || ascii(b, 0, 6) === "GIF89a")) {
    found = { type: "image/gif", w: le16(b, 6), h: le16(b, 8) };
  } else if (b.length >= 16 && ascii(b, 0, 4) === "RIFF" && ascii(b, 8, 4) === "WEBP") {
    const chunk = ascii(b, 12, 4);
    if (chunk === "VP8 " && b.length >= 30 && b[23] === 0x9d && b[24] === 0x01 && b[25] === 0x2a) {
      found = { type: "image/webp", w: le16(b, 26) & 0x3fff, h: le16(b, 28) & 0x3fff };      // lossy
    } else if (chunk === "VP8L" && b.length >= 25 && b[20] === 0x2f) {
      const bits = le32(b, 21);                                                               // lossless
      found = { type: "image/webp", w: (bits & 0x3fff) + 1, h: ((bits >>> 14) & 0x3fff) + 1 };
    } else if (chunk === "VP8X" && b.length >= 30) {
      found = { type: "image/webp", w: le24(b, 24) + 1, h: le24(b, 27) + 1 };                // extended
    }
  } else if (b.length >= 4 && b[0] === 0xff && b[1] === 0xd8) {
    found = jpegSize(b);
  }
  return found && found.w > 0 && found.h > 0 ? found : null;
}

// ---------------------------------------------------------------------------------------------- web pages
// Drive sometimes answers a download with a web page and status 200: "Google Drive can't scan this file for
// viruses", "Too many users have viewed or downloaded this file recently", a sign-in page. Its content type says
// text/html — or, now and then, nothing useful — so the first bytes are looked at too.
export function isHtml(bytes, contentType) {
  const t = baseType(contentType);
  if (t === "text/html" || t === "application/xhtml+xml") return true;
  const b = bytesOf(bytes);
  if (!b.length) return false;
  let s = ascii(b, 0, Math.min(b.length, 1024)).replace(/^ï»¿/, "").replace(/^\s+/, "");
  while (s.startsWith("<!--")) {                             // comments before the page starts
    const end = s.indexOf("-->");
    if (end < 0) return false;
    s = s.slice(end + 3).replace(/^\s+/, "");
  }
  return /^<(?:!doctype\s+html|html|head|body|meta|title|script|style|link)\b/i.test(s);
}

// ---------------------------------------------------------------------------------------------- the results
// entries: [{ file_id, file, bytes, type, w, h }] in booth.json's order; skipped: the plan's and the downloads'.
export function manifestOf(entries, skipped, built) {
  const items = {};
  for (const e of Array.isArray(entries) ? entries : []) {
    if (!e || !e.file_id || !e.file) continue;
    items[e.file_id] = {
      file: e.file, bytes: e.bytes ?? 0, type: e.type || typeForExt(String(e.file).split(".").pop()),
      w: e.w ?? null, h: e.h ?? null,
    };
  }
  const skip = (Array.isArray(skipped) ? skipped : []).filter(Boolean)
    .map((s) => ({ file_id: s.file_id ?? null, name: s.name ?? "", reason: s.reason ?? "", code: s.code ?? "failed" }));
  return { built: built ?? null, items, skipped: skip };
}

// A line GitHub shows as a yellow warning on the run's page (and on the job's summary): "%", line breaks — and
// in the title also ":" and "," — are written the way GitHub's workflow commands want them.
const escData = (s) => String(s ?? "").replace(/%/g, "%25").replace(/\r/g, "%0D").replace(/\n/g, "%0A");
const escProp = (s) => escData(s).replace(/:/g, "%3A").replace(/,/g, "%2C");
export const annotation = (title, message, level = "warning") => `::${level} title=${escProp(title)}::${escData(message)}`;

// 0 B, 512 B, 1.5 KB, 12.3 MB — as the site's fileSize filter writes sizes (eleventy.config.js).
export function formatBytes(n) {
  let b = Number(n) || 0;
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return `${b.toFixed(i ? 1 : 0)} ${u[i]}`;
}
