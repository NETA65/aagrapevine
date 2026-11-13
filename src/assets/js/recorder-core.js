/* The story recorder's logic (Share your story → "Record your story", the recorder card at the top of
   src/pages/contribute.njk #record; its screen and audio engine are src/assets/js/recorder.js, its markup
   src/_includes/partials/story-recorder.njk).
   Pure functions, no DOM, no storage, no audio devices: recorder.js owns the microphone, the encoder, the
   IndexedDB takes and the screen; this file only knows about samples, bytes, the magazines' rules, takes'
   records and text.
   Tested in Node by tests/test_recorder_core.py (the file runs in a vm context, as booth-core.js does).
   A plain script (no imports; no optional chaining or ??; no arrow functions, let / const or classes —
   an older phone's Safari must run it): it defines window.GVRec (globalThis.GVRec in Node).

   THE SOUND — the microphone gives Float32 samples (−1…1, mono, at the device's own rate: usually 48000,
   44100 on some, 16000 / 24000 over a Bluetooth headset). They are kept as 16-bit PCM (toInt16) — the
   WAV file is that PCM behind a 44-byte header (wavHeader) — and encoded to MP3 (CBR 128 kbps mono, 44.1 kHz:
   LAME in WebAssembly, assets/vendor/; recorder.js). Both formats are what the magazines accept ("WAV and
   MP3 files will be accepted", aagrapevine.org/audio-portal; "Se aceptarán archivos WAV y MP3",
   aalavina.org/graba-tu-historia). MP3 is the one to e-mail: 8 minutes ≈ 7.7 MB (WAV ≈ 46 MB at 48 kHz).

   THE RULES — rule(data) from db.audio_project's part (data/site/audio_project.json; the template passes
   {min, max} in minutes, either may be missing): Grapevine "Stories should be 6-8 minutes long" (min 6,
   max 8); La Viña "hasta 7 minutos" (max 7). zone() colours the live bar, verdict() judges a take,
   crossed() names the moments to announce. Every take stops at LIMITS.hardStop (10:00) whatever the rule.

   THE TAKES — a take's record (recorder.js keeps it in IndexedDB "gvlv-recorder" › takes; its sound as
   bytes in › sound, rows keyed soundKey(id, kind, seq) — never Blobs: Safari's private store refuses them):
     { id, pub: "gv"|"lv", n: 1…, name: "" (= "Take n") | own name, created: ms, rate: Hz,
       samples: count, peak: 0…1, bins: [0…255 ×≤ LIMITS.bins] (the waveform), src: "mic"|"file"|"edit"|
       "recovered", noise: bool (background-noise reduction on), starred: bool, gaps: bool (audio went
       missing while recording), from: the number of the take an edit was made from (0: none),
       v: 1 (a Blob record of the first recorder) | 2, draft: bool (still being recorded or saved: its sound
       so far is on the device, the record is not final), mp3: bool (its MP3 rows are on the device),
       size: bytes on the device, at: ms (a draft's last write) }
   clean() checks one read back from storage (null when it is not a take).

   FILES — fileName(): "grapevine-story-2026-10-13-take-2.mp3", "la-vina-historia-2026-10-13-toma-2.wav" (the
   magazine's own language; an own name instead of "take-2" when the take was renamed; the topic chosen in "What
   will you talk about?" before it, shortened: "la-vina-historia-2026-10-13-recaidas-toma-2.mp3"). No other
   personal data: the files go by e-mail.

   TOPICS — daysLeft(): the days from the device's own today to a theme's deadline ("2 days left" beside the
   theme in the recorder's topic list: the page is built once a day, the visitor's day is counted here).

   THE DEVICE CHECK — report(facts, words): "Having trouble? Check this device" as text the visitor copies or
   e-mails to the committee themselves. Only the facts REPORT names, in its order, each on one line: never a
   take's name, topic, length or file name, nor anything typed in the e-mail's details (recorder.js diagnose()
   gathers them; the takes are counted, nothing else).

   E-MAIL — mailBody(template, values): the template (src/_i18n/community.json, in the magazine's language)
   is one line per detail; a line whose {placeholders} are all empty is left out. mailto() / gmail() /
   outlook() build the compose links (a mailto: link cannot attach a file: the page says "attach <file>");
   a mailto: link longer than LIMITS.mailMax (Outlook on Windows stops near 2,000) gets the short body, and
   recorder.js copies the whole message instead (report.js does the same).

   STORAGE — storeError() sorts what IndexedDB threw into what recorder.js does about it (try again, ask to
   delete takes, reload, or keep the takes in the page); leaves() tells a click that would take this tab to
   another page (an iPhone never asks before leaving: recorder.js asks then). */
(function (root) {
  "use strict";

  var VERSION = "1.0.0";
  var SCHEMA = 2;                       // 2: the sound as bytes (store "sound"); 1 kept Blobs (pcm, mp3, parts)
  var DB_NAME = "gvlv-recorder";        // one origin hosts every NETA65 Pages project: names carry a prefix
  var KEEP_KEY = "gvlv-rec-keep";       // "0": takes are not kept on this device (recorder.js)
  var LIMITS = {
    maxTakes: 8,                        // ≈ 54 MB each at 8 minutes (PCM + MP3); more → "delete one first"
    hardStop: 600,                      // seconds: every take stops at 10:00
    warnBefore: 30,                     // seconds before the magazine's maximum: the bar turns "near"
    quiet: 0.1,                         // a take's peak below −20 dBFS: "too quiet" (offer "Even out the volume")
    clip: 0.989,                        // a peak at −0.1 dBFS or more: clipping ("too loud")
    silent: 0.003,                      // below −50 dBFS: nothing heard
    silentFor: 5,                       // seconds of nothing at the start → "we can't hear you"
    gap: 1.5,                           // seconds without samples while recording → interrupted (paused)
    zeroFor: 3,                         // seconds of pure digital zeros while recording → interrupted (Android)
    flushEvery: 3,                      // seconds: the recording so far goes to the device (a closing page's
                                        // own last write rarely reaches IndexedDB: these are what count)
    partFresh: 120,                     // seconds: a draft this new may be a take still being recorded in
                                        // another tab (where there are no Web Locks to tell)
    chunkBytes: 1048576,                // a sound row holds at most this many bytes (1 MiB)
    idbOpen: 10,                        // seconds an IndexedDB open may take before it counts as failed…
    idbTx: 30,                          // …and a transaction
    retryEvery: 20,                     // seconds between tries while a take is not saved on the device
    bins: 240,                          // waveform columns per take
    mp3Kbps: 128,
    mp3Rate: 44100,
    normalizeTo: 0.891,                 // "Even out the volume": the peak goes to −1 dBFS…
    maxGain: 10,                        // …at most ×10 (+20 dB)
    minTake: 1,                         // seconds: a trimmed take is at least this long
    bigMail: 18 * 1048576,              // over this a file is too big for most e-mail (25 MB once encoded)
    shareMax: 50 * 1048576,             // Chromium refuses to share more than 50 MiB
    mailMax: 1800,                      // characters in a mailto: link
    linkMax: 7000,                      // characters in a Gmail / Outlook.com compose link
    importBytes: 80 * 1048576,          // a recording to convert: at most 80 MB…
    importSec: 1200                     // …and 20 minutes (it is decoded whole, in memory)
  };
  var FILE = { gv: { base: "grapevine-story", take: "take" }, lv: { base: "la-vina-historia", take: "toma" } };

  function num(v, d) { v = Number(v); return isFinite(v) ? v : (d === undefined ? 0 : d); }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function pad(n, w) { n = String(n); while (n.length < (w || 2)) n = "0" + n; return n; }

  /* ------------------------------------------------------------------ text */
  // "{n} of {max}" + {n: 2, max: 8} → "2 of 8" (a missing value leaves the placeholder as it was)
  function fill(tpl, vars) {
    vars = vars || {};
    return String(tpl == null ? "" : tpl).replace(/\{(\w+)\}/g, function (m, k) {
      return Object.prototype.hasOwnProperty.call(vars, k) && vars[k] != null ? String(vars[k]) : m;
    });
  }
  // 402.6 → "6:42"; 3725 → "1:02:05"
  function clock(sec) {
    sec = Math.max(0, Math.floor(num(sec)));
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return (h ? h + ":" + pad(m) : String(m)) + ":" + pad(s);
  }
  // 62.37 → "1:02.3" (the trim handles' tenths)
  function clockTenths(sec) {
    sec = Math.max(0, num(sec));
    var t = Math.floor(sec * 10 + 1e-6);
    return clock(Math.floor(t / 10)) + "." + (t % 10);
  }
  // words for a screen reader: words = {min1: "{n} minute", min: "{n} minutes", sec1: "{n} second",
  // sec: "{n} seconds"} → "6 minutes 42 seconds"; "1 minute"; "42 seconds"
  function spoken(sec, words) {
    sec = Math.max(0, Math.floor(num(sec)));          // (whole seconds, as the clock shows them)
    words = words || {};
    var m = Math.floor(sec / 60), s = sec % 60, out = [];
    if (m) out.push(fill(m === 1 && words.min1 ? words.min1 : words.min, { n: m }));
    if (s || !m) out.push(fill(s === 1 && words.sec1 ? words.sec1 : words.sec, { n: s }));
    return out.join(" ");
  }
  // "Mi primera toma!" → "mi-primera-toma" (ASCII, for file names)
  function slug(text, max) {
    var s = String(text == null ? "" : text);
    if (s.normalize) s = s.normalize("NFD");
    s = s.replace(/[̀-ͯ]/g, "").replace(/ñ/gi, "n").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    if (max && s.length > max) s = s.slice(0, max).replace(/-+$/, "");
    return s;
  }
  // a time stamp → "2026-10-13" in the device's own time zone (the day the person recorded); "" without one
  // (a record whose date is missing reads as 0: never "1969-12-31", fileName() says "audio" instead)
  function ymd(ms) {
    ms = num(ms);
    var d = new Date(ms);
    if (!(ms > 0) || isNaN(d.getTime())) return "";
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }
  // a deadline "2026-10-17" → the days left from the device's own today (`now`: ms) — 0 today, 1 tomorrow, −1 yesterday;
  // null without a real date. (Both days at noon: a day the clocks change is still one day.)
  function daysLeft(deadline, now) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(deadline == null ? "" : deadline).slice(0, 10));
    now = num(now);
    if (!m || !(now > 0)) return null;
    var y = Number(m[1]), mo = Number(m[2]) - 1, da = Number(m[3]);
    var d = new Date(now), b = new Date(y, mo, da, 12);
    if (isNaN(d.getTime()) || b.getFullYear() !== y || b.getMonth() !== mo || b.getDate() !== da) return null;
    var a = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12);
    return Math.round((b.getTime() - a.getTime()) / 864e5);
  }

  /* ------------------------------------------------------------------ samples */
  // Float32 (−1…1) → 16-bit PCM, clamped (a sample over full scale must not wrap round)
  function toInt16(f32) {
    var n = f32.length, out = new Int16Array(n);
    for (var i = 0; i < n; i++) {
      var s = f32[i];
      if (!(s === s)) s = 0;           // NaN
      s = s < -1 ? -1 : s > 1 ? 1 : s;
      out[i] = s < 0 ? Math.round(s * 32768) : Math.round(s * 32767);
    }
    return out;
  }
  function toFloat32(i16) {
    var n = i16.length, out = new Float32Array(n);
    for (var i = 0; i < n; i++) out[i] = i16[i] < 0 ? i16[i] / 32768 : i16[i] / 32767;
    return out;
  }
  // several channels (Float32Arrays of one length) → one, their average
  function downmix(chans) {
    if (!chans || !chans.length) return new Float32Array(0);
    if (chans.length === 1) return chans[0];
    var n = chans[0].length, c = chans.length, out = new Float32Array(n);
    for (var i = 0; i < n; i++) { var s = 0; for (var j = 0; j < c; j++) s += chans[j][i]; out[i] = s / c; }
    return out;
  }
  // the loudest sample (0…1) of a Float32 or Int16 block
  function peak(block) {
    var p = 0, int = block instanceof Int16Array, n = block.length;
    for (var i = 0; i < n; i++) { var v = block[i]; if (v < 0) v = -v; if (v > p) p = v; }
    return int ? Math.min(1, p / 32767) : Math.min(1, p);
  }
  function dbfs(p) { p = num(p); return p > 0 ? 20 * Math.log(p) / Math.LN10 : -120; }
  // the meter: −60 dBFS … 0 → 0 … 100 (%)
  function meter(p) { return Math.round(clamp((dbfs(p) + 60) / 60, 0, 1) * 100); }
  // what the meter says in words (recorder.js shows it only when it changes)
  function level(p) {
    p = num(p);
    return p >= LIMITS.clip ? "loud" : p < LIMITS.silent ? "silent" : p < LIMITS.quiet ? "quiet" : "good";
  }
  // "Even out the volume": the gain that brings a take's peak to LIMITS.normalizeTo (never below ×1)
  function gainFor(p) {
    p = num(p);
    if (p <= 0) return 1;
    return clamp(LIMITS.normalizeTo / p, 1, LIMITS.maxGain);
  }
  // Int16 × gain → a new Int16Array (clamped); returns the block's new peak through out.peak when out is given
  function applyGain(i16, gain, out) {
    var n = i16.length, r = new Int16Array(n), p = 0;
    gain = num(gain, 1);
    for (var i = 0; i < n; i++) {
      var v = Math.round(i16[i] * gain);
      v = v > 32767 ? 32767 : v < -32768 ? -32768 : v;
      r[i] = v;
      var a = v < 0 ? -v : v; if (a > p) p = a;
    }
    if (out) out.peak = Math.min(1, p / 32767);
    return r;
  }

  /* ------------------------------------------------------------------ WAV */
  // The 44-byte header of a 16-bit PCM WAV file (RIFF, little-endian) for `samples` frames
  function wavHeader(rate, samples, channels) {
    channels = channels || 1;
    rate = Math.round(num(rate));
    var data = Math.max(0, Math.floor(num(samples))) * channels * 2;
    var b = new Uint8Array(44), v = new DataView(b.buffer);
    function str(o, s) { for (var i = 0; i < s.length; i++) b[o + i] = s.charCodeAt(i); }
    str(0, "RIFF"); v.setUint32(4, 36 + data, true); str(8, "WAVE");
    str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, channels, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * channels * 2, true); v.setUint16(32, channels * 2, true);
    v.setUint16(34, 16, true);
    str(36, "data"); v.setUint32(40, data, true);
    return b;
  }
  // Reads a WAV header back (tests; a recording added by the visitor is decoded by the browser instead)
  function readWav(bytes) {
    var b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    if (b.length < 44) return null;
    var v = new DataView(b.buffer, b.byteOffset, b.byteLength);
    function str(o) { return String.fromCharCode(b[o], b[o + 1], b[o + 2], b[o + 3]); }
    if (str(0) !== "RIFF" || str(8) !== "WAVE" || str(12) !== "fmt " || str(36) !== "data") return null;
    var ch = v.getUint16(22, true), bits = v.getUint16(34, true), data = v.getUint32(40, true);
    return { format: v.getUint16(20, true), channels: ch, rate: v.getUint32(24, true), bits: bits,
      samples: data / (ch * bits / 8), size: v.getUint32(4, true) + 8 };
  }

  /* ------------------------------------------------------------------ sizes */
  function mp3Bytes(sec, kbps) { return Math.round(Math.max(0, num(sec)) * num(kbps, LIMITS.mp3Kbps) * 125); }
  function wavBytes(sec, rate) { return 44 + Math.round(Math.max(0, num(sec)) * num(rate, 48000)) * 2; }
  // what a take of `sec` seconds keeps on the device: its 16-bit PCM and its MP3 (a 10-minute take at 48 kHz ≈ 67 MB)
  function takeBytes(sec, rate) { return Math.round(Math.max(0, num(sec)) * num(rate, 48000)) * 2 + mp3Bytes(sec); }
  // n bytes → the pieces [from, to) of at most `size` bytes (LIMITS.chunkBytes; even, so a 16-bit sample is never
  // cut in two), in order; nothing for 0 bytes
  function split(n, size) {
    n = Math.max(0, Math.floor(num(n)));
    size = Math.floor(num(size, LIMITS.chunkBytes));
    if (!(size >= 2)) size = LIMITS.chunkBytes;
    size -= size % 2;
    var out = [];
    for (var a = 0; a < n; a += size) out.push([a, Math.min(n, a + size)]);
    return out;
  }

  /* ------------------------------------------------------------------ the waveform */
  // A take's chunk peaks (one per ~85 ms) → `count` columns (the loudest of each group), 0…255
  function bins(peaks, count) {
    count = count || LIMITS.bins;
    var n = peaks ? peaks.length : 0, out = [];
    if (!n) return out;
    var cols = Math.min(count, n);
    for (var c = 0; c < cols; c++) {
      var a = Math.floor(c * n / cols), z = Math.max(a + 1, Math.floor((c + 1) * n / cols)), p = 0;
      for (var i = a; i < z; i++) if (peaks[i] > p) p = peaks[i];
      out.push(Math.round(clamp(num(p), 0, 1) * 255));
    }
    return out;
  }
  // the columns of the part kept by a trim (from…to of `total` samples)
  function binsBetween(b, total, from, to) {
    if (!b || !b.length || !(total > 0)) return [];
    var a = Math.floor(from / total * b.length), z = Math.ceil(to / total * b.length);
    return b.slice(clamp(a, 0, b.length - 1), clamp(Math.max(z, a + 1), 1, b.length));
  }
  // columns → an SVG path of vertical strokes in a `w` × `h` box (viewBox "0 0 w h"); quiet takes still show
  // (a square-root curve), and a silent column is a dot on the middle line
  function wavePath(b, w, h) {
    if (!b || !b.length) return "";
    w = num(w, 240); h = num(h, 40);
    var mid = h / 2, step = w / b.length, out = [];
    for (var i = 0; i < b.length; i++) {
      var x = Math.round((i + 0.5) * step * 100) / 100;
      var half = Math.max(0.5, Math.sqrt(clamp(num(b[i]) / 255, 0, 1)) * (mid - 1));
      half = Math.round(half * 100) / 100;
      out.push("M" + x + " " + Math.round((mid - half) * 100) / 100 + "V" + Math.round((mid + half) * 100) / 100);
    }
    return out.join("");
  }

  /* ------------------------------------------------------------------ the rules */
  // data = {min, max} in minutes (either may be missing) → seconds
  function rule(data) {
    data = data || {};
    var min = num(data.min) > 0 ? num(data.min) * 60 : 0, max = num(data.max) > 0 ? num(data.max) * 60 : 0;
    if (min && max && min > max) min = 0;
    return { min: min, max: max, warn: max ? Math.max(min, max - LIMITS.warnBefore) : 0, hard: LIMITS.hardStop };
  }
  // where the live timer is: "under" (before the minimum), "ok", "near" (the last 30 s), "over"
  function zone(sec, r) {
    sec = num(sec); r = r || rule();
    if (r.max && sec > r.max) return "over";
    if (r.min && sec < r.min) return "under";
    if (r.max && sec >= r.warn) return "near";
    return "ok";
  }
  // a finished take: "short" (under the minimum), "ok", "long" (over the maximum), "none" (no rule known)
  function verdict(sec, r) {
    sec = num(sec); r = r || rule();
    if (!r.min && !r.max) return "none";
    if (r.max && sec > r.max + 0.5) return "long";             // (half a second of slack: the stop button)
    if (r.min && sec < r.min) return "short";
    return "ok";
  }
  // where the bar's marks are (0…100 % of the bar, which runs to the maximum + 2 minutes, or to the hard stop)
  function barEnd(r) { r = r || rule(); return r.max ? Math.min(r.hard, r.max + 120) : r.hard; }
  function pct(sec, r) { return Math.round(clamp(num(sec) / barEnd(r), 0, 1) * 1000) / 10; }
  // the moments passed between two readings of the timer, in order: "min" (the minimum is reached),
  // "left1" (one minute before the maximum), "max" (the maximum), "hard_soon" (30 s before the hard stop)
  function crossed(prev, now, r) {
    prev = num(prev); now = num(now); r = r || rule();
    var marks = [];
    if (r.min) marks.push(["min", r.min]);
    if (r.max && r.max - 60 > r.min) marks.push(["left1", r.max - 60]);
    if (r.max) marks.push(["max", r.max]);
    marks.push(["hard_soon", r.hard - 30]);
    var out = [];
    for (var i = 0; i < marks.length; i++) if (prev < marks[i][1] && now >= marks[i][1]) out.push(marks[i][0]);
    return out;
  }
  // a trim: start / end in seconds → the samples kept [from, to), at least LIMITS.minTake long
  function trimRange(samples, rate, start, end) {
    samples = Math.max(0, Math.floor(num(samples))); rate = num(rate, 48000);
    var minN = Math.min(samples, Math.round(LIMITS.minTake * rate));
    var from = clamp(Math.round(num(start) * rate), 0, samples);
    var to = clamp(Math.round(num(end, samples / rate) * rate), 0, samples);
    if (to - from < minN) {
      if (from + minN <= samples) to = from + minN; else { to = samples; from = Math.max(0, samples - minN); }
    }
    return { from: from, to: to };
  }

  /* ------------------------------------------------------------------ takes */
  function newId(now, rnd) {
    return "t" + Math.floor(num(now)).toString(36) + Math.floor(num(rnd) * 1679616).toString(36);
  }
  function nextNumber(takes) {
    var n = 0;
    (takes || []).forEach(function (t) { if (t && t.n > n) n = t.n; });
    return n + 1;
  }
  function duration(t) { return t && t.rate > 0 ? t.samples / t.rate : 0; }
  // a record read back from storage → a clean take, or null (a record with no v is the first recorder's: v 1)
  function clean(t) {
    if (!t || typeof t !== "object" || typeof t.id !== "string" || !/^[a-z0-9]{2,40}$/i.test(t.id)) return null;
    var rate = Math.round(num(t.rate)), samples = Math.floor(num(t.samples));
    if (!(rate >= 3000 && rate <= 384000) || !(samples >= 0)) return null;
    return {
      id: t.id, pub: t.pub === "lv" ? "lv" : "gv", n: Math.max(1, Math.floor(num(t.n, 1))),
      name: typeof t.name === "string" ? t.name.slice(0, 80) : "",
      created: num(t.created), rate: rate, samples: samples, peak: clamp(num(t.peak), 0, 1),
      bins: Array.isArray(t.bins) ? t.bins.slice(0, LIMITS.bins).map(function (v) { return clamp(Math.round(num(v)), 0, 255); }) : [],
      src: /^(mic|file|edit|recovered)$/.test(t.src) ? t.src : "mic",
      noise: !!t.noise, starred: !!t.starred, gaps: !!t.gaps, from: Math.max(0, Math.floor(num(t.from))),
      v: Math.max(1, Math.floor(num(t.v, 1))), draft: !!t.draft, mp3: !!t.mp3, size: Math.max(0, Math.floor(num(t.size))),
      at: Math.max(0, num(t.at))
    };
  }
  // newest first
  function sortTakes(list) {
    return (list || []).slice().sort(function (a, b) { return num(b.created) - num(a.created) || num(b.n) - num(a.n); });
  }
  // a take's file: "grapevine-story-2026-10-13-take-2.mp3" (an own name: "…-2026-10-13-mi-primera-toma.wav"); a topic:
  // its first words before them ("…-2026-10-13-recaidas-toma-2.mp3"; not twice when the own name starts with them)
  function fileName(t, ext, topic) {
    var f = FILE[t && t.pub === "lv" ? "lv" : "gv"];
    var own = t && t.name ? slug(t.name, 40) : "";
    var about = typeof topic === "string" ? slug(topic, 24) : "";
    if (about && own && (own + "-").indexOf(about + "-") === 0) about = "";
    return f.base + "-" + (ymd(t && t.created) || "audio") + "-" + (about ? about + "-" : "") + (own || f.take + "-" + ((t && t.n) || 1)) + "." + (ext || "mp3");
  }
  // a row of a take's sound: "t1:pcm:000003" (kind "pcm" | "mp3"; sorts in order as text). One take's rows are the
  // range soundRange(id, kind) — every kind without one: [id + ":", id + ":￿"]. Never another take's: ":" sorts
  // apart from every letter and digit an id has, so "t1:…" is never inside "t12:…" or "t1a:…" (the first recorder's
  // crash-recovery pieces, "t1:000003", fall in the same range).
  function soundKey(id, kind, seq) { return String(id) + ":" + String(kind) + ":" + pad(Math.max(0, Math.floor(num(seq))), 6); }
  function soundRange(id, kind) {
    var lo = String(id) + ":" + (kind ? String(kind) + ":" : "");
    return [lo, lo + "￿"];
  }

  /* ------------------------------------------------------------------ e-mail */
  // template: lines with {placeholders}; values: {name: "…", …}. A line whose placeholders are all empty goes;
  // a line marked {?key} stays only when values[key] is set (a heading over details that may all be empty);
  // blank lines never pile up.
  function mailBody(template, values) {
    values = values || {};
    var lines = String(template || "").split(/\r?\n/), out = [];
    lines.forEach(function (line) {
      var conds = line.match(/\{\?(\w+)\}/g);
      if (conds && !conds.every(function (c) { var v = values[c.slice(2, -1)]; return v != null && String(v).trim() !== ""; })) return;
      line = line.replace(/\{\?\w+\}/g, "");
      var keys = line.match(/\{(\w+)\}/g);
      if (keys && keys.every(function (k) { var v = values[k.slice(1, -1)]; return v == null || String(v).trim() === ""; })) return;
      var text = fill(line, values).replace(/\s+$/, "");
      if (text === "" && (!out.length || out[out.length - 1] === "")) return;
      out.push(text);
    });
    while (out.length && out[out.length - 1] === "") out.pop();
    return out.join("\n");
  }
  function enc(s) { return encodeURIComponent(String(s == null ? "" : s)).replace(/%0A/g, "%0D%0A"); }
  // → {href, cut}: cut = the body was too long and `short` went instead
  function mailto(to, subject, body, short) {
    var head = "mailto:" + String(to || "").replace(/[^\w.@+-]/g, "") + "?subject=" + enc(subject);
    var href = head + "&body=" + enc(String(body || "").replace(/\r?\n/g, "\n"));
    if (href.length <= LIMITS.mailMax) return { href: href, cut: false };
    return { href: head + (short ? "&body=" + enc(short) : ""), cut: true };
  }
  function webLink(base, keys, to, subject, body, short) {
    var head = base + keys[0] + "=" + enc(to) + "&" + keys[1] + "=" + enc(subject);
    var href = head + "&" + keys[2] + "=" + enc(body);
    if (href.length <= LIMITS.linkMax) return { href: href, cut: false };
    return { href: head + (short ? "&" + keys[2] + "=" + enc(short) : ""), cut: true };
  }
  function gmail(to, subject, body, short) {
    return webLink("https://mail.google.com/mail/?view=cm&fs=1&", ["to", "su", "body"], to, subject, body, short);
  }
  function outlook(to, subject, body, short) {
    return webLink("https://outlook.live.com/mail/0/deeplink/compose?", ["to", "subject", "body"], to, subject, body, short);
  }

  /* ------------------------------------------------------------------ the browser */
  // env: {secure, media (getUserMedia), audio (AudioContext), worklet, script (ScriptProcessor), inApp}
  // → {record: "worklet"|"script"|"", why: ""|"insecure"|"no_media"|"no_audio"}
  function support(env) {
    env = env || {};
    if (!env.secure) return { record: "", why: "insecure" };
    if (!env.media) return { record: "", why: "no_media" };
    if (!env.audio) return { record: "", why: "no_audio" };
    if (env.worklet) return { record: "worklet", why: "" };
    if (env.script) return { record: "script", why: "" };
    return { record: "", why: "no_audio" };
  }
  // a getUserMedia / AudioContext failure → what to tell the person
  function errorKind(err) {
    var n = err && (err.name || err.code || err.message) || "";
    if (/NotAllowed|PermissionDenied|Security/i.test(n)) return "denied";
    if (/NotFound|DevicesNotFound/i.test(n)) return "nomic";
    if (/NotReadable|TrackStart|Abort/i.test(n)) return "busy";
    if (/Overconstrained|ConstraintNotSatisfied/i.test(n)) return "constraint";
    return "other";
  }
  // which "allow the microphone" steps fit this browser: ios, android, firefox, edge, chrome, safari, other
  function helpFor(ua, touch) {
    ua = String(ua || "");
    if (/\b(iPhone|iPad|iPod)\b/.test(ua) || (/\bMacintosh\b/.test(ua) && num(touch) > 1)) return "ios";
    if (/\bAndroid\b/.test(ua)) return "android";
    if (/\bFirefox\//.test(ua)) return "firefox";
    if (/\bEdg\//.test(ua)) return "edge";
    if (/\b(HeadlessChrome|Chrome|Chromium|CriOS)\//.test(ua)) return "chrome";   // (HeadlessChrome: a test's own)
    if (/\bSafari\//.test(ua)) return "safari";
    return "other";
  }
  // the file picker's accept list: iPhone / iPad treat "audio/*" as video (WebKit 242110) — extensions only there
  function accept(ios) {
    var ext = ".m4a,.mp3,.wav,.aac,.caf,.ogg,.oga,.opus,.webm,.weba,.flac,.3gp,.amr,.mp4";
    return ios ? ext : "audio/*," + ext;
  }

  /* ------------------------------------------------------------------ storage */
  // what IndexedDB threw → "quota" (the device is full: ask to delete takes), "none" (this browser keeps nothing:
  // no IndexedDB — Lockdown Mode —, blocked site data: Chrome then says UnknownError "The user denied permission to
  // access the database."), "version" (a newer page changed the database: reload), "transient" (anything else: a lost
  // connection, an aborted or timed-out transaction — try again)
  function storeError(err) {
    var n = String(err && (err.name || err.code) || ""), m = String(err && err.message || "");
    if (n === "QuotaExceededError" || (err && err.code === 22) || /quota/i.test(n + " " + m)) return "quota";
    if (/^(SecurityError|InvalidAccessError|NotSupportedError)$/.test(n) || /denied permission/i.test(m)) return "none";
    if (n === "VersionError") return "version";
    return "transient";
  }
  // does a click on a link take THIS tab to another page? click = {href (the link's full address), target,
  // download (bool), go (bool: the page's own script handles it — data-rec-go, data-copy…), button, keys (a modifier
  // key held: a new tab or window), prevented (bool)}; here = this page's address. Only a plain primary click on an
  // http(s) address, in this tab, not a download, and not only a #fragment of this page (that scrolls).
  function leaves(click, here) {
    click = click && typeof click === "object" ? click : {};
    if (click.prevented || click.go || click.download || click.keys || num(click.button) !== 0) return false;
    var href = String(click.href == null ? "" : click.href);
    if (!/^https?:/i.test(href)) return false;
    var tg = String(click.target == null ? "" : click.target).toLowerCase();
    if (tg && tg !== "_self" && tg !== "_top" && tg !== "_parent") return false;
    var cut = function (u) { var i = u.indexOf("#"); return i < 0 ? u : u.slice(0, i); };
    if (href.indexOf("#") >= 0 && cut(href) === cut(String(here == null ? "" : here))) return false;
    return true;
  }

  /* ------------------------------------------------------------------ the device check */
  // The facts a report may hold, in this order (THE DEVICE CHECK above; recorder.js diagnose() says what each one is).
  // Nothing else ever gets in: no take's name, topic, length or file name, no microphone's name (it may be a person's:
  // "Ana's AirPods"), nothing typed in the e-mail's details — the takes are counted.
  var REPORT = ["when", "page", "browser", "system", "app", "online", "secure", "mic_api", "mic", "record", "wasm", "mp3", "idb",
    "keep", "persisted", "priv", "free", "used", "wake", "share", "takes", "unsaved", "unreadable", "error", "ua"];
  // install-core.js detect()'s browsers and systems by their own names (the same in every language); any other: "unknown"
  var BROWSERS = { safari: "Safari", chrome: "Chrome", firefox: "Firefox", edge: "Edge", samsung: "Samsung Internet", opera: "Opera",
    brave: "Brave" };
  var SYSTEMS = { ios: "iOS", ipados: "iPadOS", android: "Android", mac: "macOS", windows: "Windows", chromeos: "ChromeOS", linux: "Linux" };
  // any value → one line of text, at most `max` characters (a value can never start a line of its own)
  function oneLine(v, max) {
    return String(v == null ? "" : v).replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]+/g, " ").replace(/\s+/g, " ")
      .replace(/^\s+|\s+$/g, "").slice(0, max || 300);
  }
  // facts {key: value} → the report: words.title, a blank line, then "label: value" per fact of REPORT that is given.
  // A value: true / false (words.yes / words.no), a number (whole), null or "" (words.unknown), or a code — its own words
  // words["v_" + key + "_" + code] when the page has them ("granted" → "allowed"), else the text itself; {code, more}
  // adds "(more)" — the browser's version without the brackets ("Safari 18"). words: the page's (#rec-config "d").
  function report(facts, words) {
    facts = facts && typeof facts === "object" ? facts : {};
    words = words && typeof words === "object" ? words : {};
    var own = Object.prototype.hasOwnProperty;
    var w = function (k) { return own.call(words, k) && typeof words[k] === "string" ? oneLine(words[k]) : ""; };
    var lines = [];
    REPORT.forEach(function (k) {
      if (!own.call(facts, k)) return;
      var v = facts[k], code = v, more = "", text = "", names = k === "browser" ? BROWSERS : k === "system" ? SYSTEMS : null;
      if (v && typeof v === "object") { code = v.code; more = v.more; }
      if (code === true) text = w("yes");
      else if (code === false) text = w("no");
      else if (typeof code === "number") text = isFinite(code) ? String(Math.round(code)) : "";
      else if (typeof code === "string" && oneLine(code)) {
        code = oneLine(code);
        if (names) text = own.call(names, code) ? names[code] : "";
        else text = w("v_" + k + "_" + code) || code;
      }
      more = typeof more === "number" || typeof more === "string" ? oneLine(more, 120) : "";
      if (text && more && more !== "0") text += k === "browser" ? " " + more : " (" + more + ")";
      lines.push((w("l_" + k) || k) + ": " + (text || w("unknown") || "?"));
    });
    return (w("title") ? w("title") + "\n\n" : "") + lines.join("\n");
  }

  /* ------------------------------------------------------------------ the module */
  root.GVRec = {
    VERSION: VERSION, SCHEMA: SCHEMA, DB_NAME: DB_NAME, KEEP_KEY: KEEP_KEY, LIMITS: LIMITS, FILE: FILE,
    // text
    fill: fill, clock: clock, clockTenths: clockTenths, spoken: spoken, slug: slug, ymd: ymd, daysLeft: daysLeft,
    // samples and files
    toInt16: toInt16, toFloat32: toFloat32, downmix: downmix, peak: peak, dbfs: dbfs, meter: meter, level: level,
    gainFor: gainFor, applyGain: applyGain, wavHeader: wavHeader, readWav: readWav, mp3Bytes: mp3Bytes,
    wavBytes: wavBytes, takeBytes: takeBytes, split: split, bins: bins, binsBetween: binsBetween, wavePath: wavePath,
    // rules
    rule: rule, zone: zone, verdict: verdict, barEnd: barEnd, pct: pct, crossed: crossed, trimRange: trimRange,
    // takes
    newId: newId, nextNumber: nextNumber, duration: duration, clean: clean, sortTakes: sortTakes,
    fileName: fileName, soundKey: soundKey, soundRange: soundRange,
    // e-mail
    mailBody: mailBody, mailto: mailto, gmail: gmail, outlook: outlook,
    // the browser
    support: support, errorKind: errorKind, helpFor: helpFor, accept: accept,
    // storage
    storeError: storeError, leaves: leaves,
    // the device check
    REPORT: REPORT, report: report
  };
})(typeof window !== "undefined" ? window : globalThis);
