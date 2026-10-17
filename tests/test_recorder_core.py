"""The story recorder's logic (src/assets/js/recorder-core.js, window.GVRec) run in Node.js.

What a take relies on, checked against values worked out by hand (in the comments):
  * text        — fill() (a missing value leaves its placeholder; no second pass), the clock (m:ss, h:mm:ss; the trim
                  handles' tenths, never 1.2999… shown as "1.2"), the words a screen reader hears (one / many, whole
                  seconds as the clock shows them, English and Spanish), slug() (accents, ñ — also without
                  String.normalize —, the length), the day in the device's own zone (none for a record without a date)
  * samples     — Float32 → Int16 (full scale both ways, over full scale clamped, NaN silent) and back again exactly;
                  downmix; the peak of a Float32 and of an Int16 block; dBFS, the meter, the level words at their
                  thresholds; "Even out the volume" (never quieter, at most ×10, clamped, the new peak)
  * files       — the WAV header byte for byte (RIFF / WAVE / fmt / data, the sizes, rate, byte rate, block align) and
                  read back; the MP3 and WAV sizes (an MP3 always fits an e-mail, an 8-minute WAV never does); what a take
                  keeps on the device (takeBytes); the sound rows' sizes (split: at most LIMITS.chunkBytes, never half a
                  sample)
  * waveform    — bins (the loudest of each group, 0…255), the columns a trim keeps, the SVG path
  * the rules   — Grapevine 6–8 minutes, La Viña up to 7, no data: the bar's zones and marks, a take's verdict, the
                  moments announced (in order, each once), the 10-minute hard stop; trimRange at its edges
  * takes       — ids, numbers, length (and nothing about age: no take is deleted for being old), clean() on garbage
                  (every field checked — v / draft / mp3 / size / at too —, unknown ones dropped, idempotent), newest first,
                  the file names (Grapevine / La Viña, renamed, accents, the day in the device's zone), the sound rows' keys
                  in order (one take's range — and one kind's — never reaching another's)
  * e-mail      — mailBody ({?key} lines, empty lines dropped, no blank-line pile-up, no second pass) — also with the
                  real templates of src/_i18n/community.json —; mailto / Gmail / Outlook.com (CRLF line ends, the
                  address cleaned, the short message past LIMITS.mailMax / linkMax — exactly at the limit)
  * the browser — support(), errorKind() (today's and older error names), helpFor() on real user agents, accept() (an
                  iPhone or iPad gets file extensions only)
  * storage     — storeError() (quota / none / version / transient, by name, code or message), leaves() (only a plain
                  primary click that takes this tab to another document: not a #fragment of this page, a new tab, a
                  download, mailto:, the page's own links)
  * the module  — its exact API, window.GVRec in a browser (globalThis.GVRec in Node), nothing throws on garbage, the
                  plain-script syntax (ES2019, no page objects) and no change to the built-in prototypes
The file runs in a vm context, as tests/test_booth_core.py runs booth-core.js. Skipped without Node.js.

    python -m unittest tests.test_recorder_core -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import math
import re
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

CORE = "src/assets/js/recorder-core.js"
STRINGS = ROOT / "src" / "_i18n" / "community.json"

# Loads the core into a fresh vm context: G = window.GVRec. The device's time zone is pinned (ymd() and fileName() write
# the day the person recorded, where they are): Central time, as most of our visitors.
LOAD = r"""
import vm from "node:vm";
process.env.TZ = "America/Chicago";
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/recorder-core.js", "utf8"), ctx, { filename: "recorder-core.js" });
const G = ctx.GVRec;
// typed arrays made in the core's own realm: peak() tells an Int16 block by instanceof (the page's arrays are its own)
const V = vm.runInContext("({ Int16Array: Int16Array, Float32Array: Float32Array, Uint8Array: Uint8Array })", ctx);
const I16 = (a) => new V.Int16Array(a), F32 = (a) => new V.Float32Array(a);
const arr = (t) => Array.from(t);
const plain = (v) => JSON.parse(JSON.stringify(v));
"""

# The words recorder.js hands spoken() (community.recorder.w_*): English, Spanish, and a language with one form only.
WORDS_EN = {"min1": "{n} minute", "min": "{n} minutes", "sec1": "{n} second", "sec": "{n} seconds"}
WORDS_ES = {"min1": "{n} minuto", "min": "{n} minutos", "sec1": "{n} segundo", "sec": "{n} segundos"}

API = ["VERSION", "SCHEMA", "DB_NAME", "KEEP_KEY", "LIMITS", "FILE",
       "fill", "clock", "clockTenths", "spoken", "slug", "ymd", "daysLeft",
       "toInt16", "toFloat32", "downmix", "peak", "dbfs", "meter", "level", "gainFor", "applyGain", "wavHeader", "readWav",
       "mp3Bytes", "wavBytes", "takeBytes", "split", "bins", "binsBetween", "wavePath",
       "rule", "zone", "verdict", "barEnd", "pct", "crossed", "trimRange",
       "newId", "nextNumber", "duration", "clean", "sortTakes", "fileName", "soundKey", "soundRange",
       "mailBody", "mailto", "gmail", "outlook",
       "support", "errorKind", "helpFor", "accept",
       "storeError", "leaves",
       "REPORT", "report"]   # (round 12: the device check — tests/test_r12_u2_contribute.py)
MIB = 1048576


def core(case: unittest.TestCase, js: str, data=None, **kw):
    """Run `js` (it calls out(value)) with the core loaded; returns the value."""
    return run_js(case, LOAD + js, data=data, needs_modules=False, **kw)


def strings() -> dict:
    return json.loads(STRINGS.read_text(encoding="utf-8"))


def dbfs(p: float) -> float:
    return 20 * math.log10(p)


class Text(unittest.TestCase):
    def test_fill(self):
        r = core(self, r"""out([
          G.fill("{n} of {max}", { n: 2, max: 8 }), G.fill("{n} of {max}", { n: 2 }), G.fill("{n}", { n: null }), G.fill("{n}", { n: 0 }),
          G.fill("{name}", { name: "{n}", n: 5 }), G.fill("{toString} {constructor}", {}), G.fill(null, { n: 1 }), G.fill("plain"),
          G.fill("{a}{a}", { a: "x" }), G.fill("{ n }", { n: 1 }), G.fill("{n}", { n: "" })]);""")
        # a missing (or null) value leaves its placeholder; a value is never filled in again (no second pass); only the
        # vars' own keys count (never Object.prototype's)
        self.assertEqual(r, ["2 of 8", "2 of {max}", "{n}", "0", "{n}", "{toString} {constructor}", "", "plain", "xx", "{ n }", ""])

    def test_clock(self):
        r = core(self, r"""out([0, 0.99, 59.999, 60, 402.6, 599.9, 600, 3599, 3600, 3725, -5, NaN, "65", null, undefined, "x", Infinity]
          .map((s) => G.clock(s)));""")
        self.assertEqual(r, ["0:00", "0:00", "0:59", "1:00", "6:42", "9:59", "10:00", "59:59", "1:00:00", "1:02:05", "0:00", "0:00",
                             "1:05", "0:00", "0:00", "0:00", "0:00"])

    def test_clock_tenths(self):
        # the trim handles step by 0.1 s: a value worked out in floating point (2.3 − 1 = 1.2999999999999998, what
        # clampEdit gives) still shows its tenth; the rest is cut, never rounded up (the clock never runs ahead)
        r = core(self, r"""out([0, 0.1, 0.3, 0.7, 2.3, 62.37, 59.95, 59.99, 60, -1, 1.15, 599.96, 0.05, 2.3 - 1, 1.2 - 1, 4.1 - 1, "x"]
          .map((s) => G.clockTenths(s)));""")
        self.assertEqual(r, ["0:00.0", "0:00.1", "0:00.3", "0:00.7", "0:02.3", "1:02.3", "0:59.9", "0:59.9", "1:00.0", "0:00.0",
                             "0:01.1", "9:59.9", "0:00.0", "0:01.3", "0:00.2", "0:03.1", "0:00.0"])

    def test_spoken(self):
        secs = [402, 402.9, 60, 61, 1, 0, 42, 120, 3600, -3, 59.999, 119.99]
        r = core(self, r"""out({
          en: input.secs.map((s) => G.spoken(s, input.en)), es: [61, 125, 1, 0].map((s) => G.spoken(s, input.es)),
          one: [61, 1].map((s) => G.spoken(s, { min: "{n} min", sec: "{n} s" })), clocks: input.secs.map((s) => G.clock(s)) });""",
                 data={"secs": secs, "en": WORDS_EN, "es": WORDS_ES})
        self.assertEqual(r["en"], ["6 minutes 42 seconds", "6 minutes 42 seconds", "1 minute", "1 minute 1 second", "1 second",
                                   "0 seconds", "42 seconds", "2 minutes", "60 minutes", "0 seconds", "59 seconds", "1 minute 59 seconds"])
        self.assertEqual(r["es"], ["1 minuto 1 segundo", "2 minutos 5 segundos", "1 segundo", "0 segundos"])
        self.assertEqual(r["one"], ["1 min 1 s", "1 s"])                    # no singular words: the plural ones
        # what is heard is what the clock shows (whole seconds: 6:42.9 is "6 minutes 42 seconds")
        for said, shown in zip(r["en"], r["clocks"]):
            m, s = (int(x) for x in shown.split(":")[-2:])
            if shown.count(":") == 2:
                m += 60 * int(shown.split(":")[0])
            nums = [int(x) for x in re.findall(r"\d+", said)]
            self.assertEqual(nums, ([m] if m else []) + ([s] if s or not m else []), (said, shown))

    def test_slug(self):
        r = core(self, r"""
          const bare = vm.createContext({ console });
          vm.runInContext("delete String.prototype.normalize;", bare);
          vm.runInContext(fs.readFileSync("src/assets/js/recorder-core.js", "utf8"), bare);
          out({ s: ["Mi primera toma!", "Canción de Año Nuevo", "ÑANDÚ", "  --Hello__World--  ", "Café, café… ¡olé!", "日本語", "🎙 Take 3",
                    null, undefined, 42, "über"].map((t) => G.slug(t)),
                max: [G.slug("a b c d", 5), G.slug("abc def", 4), G.slug("x".repeat(50), 40), G.slug("short", 40), G.slug("a-b", 0)],
                // an older browser without String.normalize: ñ / Ñ still become n
                old: [vm.runInContext("typeof String.prototype.normalize", bare), bare.GVRec.slug("Año Ñu"), bare.GVRec.slug("Mi toma 2")] });""")
        self.assertEqual(r["s"], ["mi-primera-toma", "cancion-de-ano-nuevo", "nandu", "hello-world", "cafe-cafe-ole", "", "take-3", "", "", "42",
                                  "uber"])
        self.assertEqual(r["max"], ["a-b-c", "abc", "x" * 40, "short", "a-b"])      # cut to the length, never ending in "-"
        self.assertEqual(r["old"], ["undefined", "ano-nu", "mi-toma-2"])

    def test_ymd_is_the_day_on_this_device(self):
        r = core(self, r"""
          const at = (iso) => Date.parse(iso);
          const chicago = ["2026-10-13T04:30:00Z", "2026-10-13T05:00:00Z", "2026-10-12T16:00:00Z", "2027-01-01T05:59:00Z", "2027-01-01T06:00:00Z"]
            .map((d) => G.ymd(at(d)));
          const none = [0, undefined, null, "x", -1, NaN, 1e16].map((v) => G.ymd(v));
          const str = G.ymd(String(at("2026-10-13T17:00:00Z")));
          process.env.TZ = "Asia/Tokyo";                         // the same moments on a phone in Japan
          const tokyo = ["2026-10-13T04:30:00Z", "2026-10-12T16:00:00Z"].map((d) => G.ymd(at(d)));
          out({ chicago, none, tokyo, str });""")
        self.assertEqual(r["chicago"], ["2026-10-12", "2026-10-13", "2026-10-12", "2026-12-31", "2027-01-01"])
        self.assertEqual(r["none"], [""] * 7)                    # a record without a date: no day (never 1969-12-31)
        self.assertEqual(r["tokyo"], ["2026-10-13", "2026-10-13"])
        self.assertEqual(r["str"], "2026-10-13")                  # a time stamp kept as text reads the same


class Samples(unittest.TestCase):
    def test_to_int16(self):
        r = core(self, r"""
          const out16 = G.toInt16(F32([0, 0.5, -0.5, 1, -1, 1.5, -1.5, NaN, Infinity, -Infinity, 1e-6, -1e-6, 0.25, -0.25, 0.1]));
          out({ v: arr(out16), own: out16 instanceof V.Int16Array, plain: arr(G.toInt16([0.5, -2, 2])), empty: G.toInt16(F32([])).length });""")
        # positive samples × 32767, negative ones × 32768 (full scale both ways); over full scale clamped, never wrapped
        # round (1.5 → 32767, not −16384); NaN (a glitch) is silence; 0.1 is 0.100000001… as a Float32 → 3277
        self.assertEqual(r["v"], [0, 16384, -16384, 32767, -32768, 32767, -32768, 0, 32767, -32768, 0, 0, 8192, -8192, 3277])
        self.assertTrue(r["own"])
        self.assertEqual(r["plain"], [16384, -32768, 32767])
        self.assertEqual(r["empty"], 0)

    def test_to_float32_and_back(self):
        r = core(self, r"""
          const all = new V.Int16Array(65536);
          for (let i = 0; i < 65536; i++) all[i] = i - 32768;
          const f = G.toFloat32(all), back = G.toInt16(f);
          let same = true, inRange = true;
          for (let i = 0; i < 65536; i++) { if (back[i] !== all[i]) same = false; if (f[i] < -1 || f[i] > 1) inRange = false; }
          // a float through 16 bits and back: within one step
          let worst = 0, x = 0.123456;
          const xs = new V.Float32Array(5000);
          for (let i = 0; i < xs.length; i++) { x = (x * 9301 + 49297) % 233280; xs[i] = x / 116640 - 1; }
          const ys = G.toFloat32(G.toInt16(xs));
          for (let i = 0; i < xs.length; i++) worst = Math.max(worst, Math.abs(xs[i] - ys[i]));
          out({ same, inRange, ends: arr(G.toFloat32(I16([-32768, 32767, 0, 16384]))), worst, own: f instanceof V.Float32Array });""")
        self.assertTrue(r["same"])                                # every 16-bit value comes back as it was
        self.assertTrue(r["inRange"])
        self.assertEqual(r["ends"][:3], [-1, 1, 0])
        self.assertAlmostEqual(r["ends"][3], 16384 / 32767, places=6)
        self.assertLessEqual(r["worst"], 1 / 32767)
        self.assertTrue(r["own"])

    def test_downmix(self):
        r = core(self, r"""
          const one = F32([0.1, 0.2]);
          out({ none: [G.downmix([]).length, G.downmix(null).length, G.downmix(undefined).length], same: G.downmix([one]) === one,
                two: arr(G.downmix([F32([1, 0.5, 0]), F32([-1, 0.5, 1])])), three: arr(G.downmix([F32([0.3]), F32([0.3]), F32([0.6])])) });""")
        self.assertEqual(r["none"], [0, 0, 0])
        self.assertTrue(r["same"])                                # a mono recording is passed on as it is
        self.assertEqual(r["two"], [0, 0.5, 0.5])                 # the channels' average
        self.assertAlmostEqual(r["three"][0], 0.4, places=6)

    def test_peak(self):
        r = core(self, r"""out([G.peak(F32([0.1, -0.7, 0.3])), G.peak(I16([100, -32768, 5])), G.peak(I16([16384, -100])), G.peak(I16([])),
          G.peak(F32([])), G.peak(F32([1.5])), G.peak(F32([-0.25])), G.peak([0.2, -0.9]), G.peak(I16([32767]))]);""")
        self.assertAlmostEqual(r[0], 0.7, places=6)                # the loudest sample, either sign
        self.assertEqual(r[1], 1)                                 # −32768 is full scale (never above 1)
        self.assertAlmostEqual(r[2], 16384 / 32767, places=9)     # an Int16 block is read as 16-bit
        self.assertEqual(r[3:7], [0, 0, 1, 0.25])
        self.assertAlmostEqual(r[7], 0.9)
        self.assertEqual(r[8], 1)

    def test_dbfs_meter_and_level(self):
        r = core(self, r"""out({
          db: [1, 0.5, 0.1, 0.001, 0, -1, "x"].map((p) => G.dbfs(p)),
          meter: [1, 0.5, 0.1, 0.01, 0.001, 0.0001, 0, 2, -1].map((p) => G.meter(p)),
          level: [1, 0.989, 0.9889, 0.5, 0.1, 0.0999, 0.003, 0.0029, 0, NaN, "0.5", 1.2].map((p) => G.level(p)) });""")
        for got, want in zip(r["db"], [0, -6.0206, -20, -60, -120, -120, -120]):
            self.assertAlmostEqual(got, want, places=4)
        # the meter runs from −60 dBFS (0 %) to full scale (100 %): −6 dB → 90 %, −20 dB → 67 %, −40 dB → 33 %
        self.assertEqual(r["meter"], [100, 90, 67, 33, 0, 0, 0, 100, 0])
        # at the thresholds: clip 0.989 (−0.1 dBFS) is loud; quiet below 0.1 (−20 dBFS); silent below 0.003 (≈ −50 dBFS)
        self.assertEqual(r["level"], ["loud", "loud", "good", "good", "good", "quiet", "quiet", "silent", "silent", "silent", "good", "loud"])

    def test_even_out_the_volume(self):
        r = core(self, r"""
          const src = I16([1000, -1000, 20000, -20000, 0]), o = {};
          const twice = G.applyGain(src, 2, o);
          const p1 = {}, p2 = {}, quiet = I16([1638, -1200]), soft = I16([6553, -6000]);
          const qg = G.gainFor(G.peak(quiet)), sg = G.gainFor(G.peak(soft));
          G.applyGain(quiet, qg, p1); G.applyGain(soft, sg, p2);
          const half = {};
          out({ gain: [0, -1, 0.891, 0.95, 1, 0.5, 0.0891, 0.01, "x", 0.1].map((p) => G.gainFor(p)),
                twice: arr(twice), peak: o.peak, fresh: twice !== src, untouched: arr(src),
                halves: arr(G.applyGain(I16([3, -3]), 0.5)), one: [arr(G.applyGain(I16([16384]), 1, half)), half.peak],
                odd: [arr(G.applyGain(I16([7, -7]), "x")), arr(G.applyGain(I16([7]), undefined))],
                quiet: [qg, p1.peak], soft: [sg, p2.peak] });""")
        g = r["gain"]
        # never quieter (×1 at least), at most ×10 (+20 dB); otherwise the peak goes to 0.891 (−1 dBFS)
        self.assertEqual(g[:5], [1, 1, 1, 1, 1])
        self.assertAlmostEqual(g[5], 1.782)
        self.assertEqual(g[6:9], [10, 10, 1])
        self.assertAlmostEqual(g[9], 8.91)
        self.assertEqual(r["twice"], [2000, -2000, 32767, -32768, 0])   # clamped at full scale, never wrapped round
        self.assertEqual(r["peak"], 1)
        self.assertTrue(r["fresh"])
        self.assertEqual(r["untouched"], [1000, -1000, 20000, -20000, 0])   # a new take: the original's sound is not changed
        self.assertEqual(r["halves"], [2, -1])                    # Math.round: halves go up (1.5 → 2, −1.5 → −1)
        self.assertEqual(r["one"][0], [16384])
        self.assertAlmostEqual(r["one"][1], 16384 / 32767, places=9)
        self.assertEqual(r["odd"], [[7, -7], [7]])                # a gain that is not a number changes nothing
        self.assertEqual(r["quiet"][0], 10)                       # peak 0.05: ×17.8 wanted, ×10 allowed → 0.5
        self.assertAlmostEqual(r["quiet"][1], 16380 / 32767, places=6)
        self.assertAlmostEqual(r["soft"][0], 4.4553, places=3)    # peak 0.2: ×4.455 → −1 dBFS
        self.assertAlmostEqual(r["soft"][1], 0.891, places=3)


class Wav(unittest.TestCase):
    def test_header_byte_for_byte(self):
        r = core(self, r"""out({ mono: arr(G.wavHeader(48000, 1000)), stereo: arr(G.wavHeader(44100, 10, 2)),
          odd: arr(G.wavHeader(44100.4, 10.7)), none: arr(G.wavHeader(16000, -5)), own: G.wavHeader(8000, 1) instanceof V.Uint8Array,
          long: arr(G.wavHeader(48000, 48000 * 600)) });""")

        def header(rate, samples, ch=1):
            data = samples * ch * 2
            return list(struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + data, b"WAVE", b"fmt ", 16, 1, ch, rate, rate * ch * 2,
                                    ch * 2, 16, b"data", data))
        self.assertEqual(r["mono"], header(48000, 1000))          # byte rate 96000, block align 2, 16 bits, 2000 bytes of data
        self.assertEqual(r["stereo"], header(44100, 10, 2))       # byte rate 176400, block align 4
        self.assertEqual(r["odd"], header(44100, 10))             # a rate rounded, a whole number of samples
        self.assertEqual(r["none"], header(16000, 0))
        self.assertEqual(len(r["mono"]), 44)
        self.assertTrue(r["own"])
        self.assertEqual(r["long"], header(48000, 48000 * 600))   # the longest take (10:00 at 48 kHz) fits the 32-bit sizes

    def test_read_back(self):
        r = core(self, r"""
          const big = new V.Uint8Array(100); big.set(G.wavHeader(16000, 8), 4);
          const bad = G.wavHeader(8000, 1); bad[36] = 76;          // "Lata" where "data" belongs
          const riffx = G.wavHeader(8000, 1); riffx[3] = 88;
          out({ round: G.readWav(G.wavHeader(44100, 12345)), stereo: G.readWav(G.wavHeader(48000, 100, 2)),
                inside: G.readWav(big.subarray(4)), buffer: G.readWav(G.wavHeader(22050, 3).buffer),
                bad: [G.readWav(bad), G.readWav(riffx), G.readWav(G.wavHeader(8000, 1).subarray(0, 43)), G.readWav(null), G.readWav("RIFF")],
                sizes: [[480, 48000], [1, 44100], [0, 16000], [0.5, 44100]].map((x) => [G.wavBytes(x[0], x[1]),
                         G.readWav(G.wavHeader(x[1], Math.round(x[0] * x[1]))).size]) });""")
        self.assertEqual(r["round"], {"format": 1, "channels": 1, "rate": 44100, "bits": 16, "samples": 12345, "size": 44 + 24690})
        self.assertEqual(r["stereo"]["samples"], 100)
        self.assertEqual((r["inside"]["rate"], r["inside"]["samples"]), (16000, 8))   # a header that does not start its buffer
        self.assertEqual((r["buffer"]["rate"], r["buffer"]["samples"]), (22050, 3))   # an ArrayBuffer
        self.assertEqual(r["bad"], [None] * 5)
        for estimate, real in r["sizes"]:
            self.assertEqual(estimate, real)                       # wavBytes() is the size of the file Download makes

    def test_sizes(self):
        r = core(self, r"""out({ mp3: [G.mp3Bytes(480), G.mp3Bytes(600), G.mp3Bytes(60, 64), G.mp3Bytes(-5), G.mp3Bytes(60, "x"), G.mp3Bytes("x")],
          wav: [G.wavBytes(480, 48000), G.wavBytes(1, 44100), G.wavBytes(0), G.wavBytes(-1, 48000), G.wavBytes(1), G.wavBytes(0.5, 44100)],
          L: G.LIMITS });""")
        # CBR: seconds × kbit/s × 125 bytes — 8 minutes at 128 kbit/s = 7.68 MB
        self.assertEqual(r["mp3"], [7680000, 9600000, 480000, 0, 960000, 0])
        # 44 bytes of header + 2 bytes a sample (mono): 8 minutes at 48 kHz = 46 MB
        self.assertEqual(r["wav"], [46080044, 88244, 44, 44, 96044, 44144])
        L = r["L"]
        self.assertLess(r["mp3"][1], L["bigMail"])                 # the longest take's MP3 (10:00) still fits an e-mail…
        self.assertLess(r["mp3"][1], L["shareMax"])                # …and a share
        self.assertGreater(r["wav"][0], L["bigMail"])              # an 8-minute WAV does not: "too big for most e-mail"

    def test_what_a_take_keeps_on_the_device(self):
        r = core(self, r"""out({ take: [G.takeBytes(600, 48000), G.takeBytes(1, 44100), G.takeBytes(0), G.takeBytes(-3, 48000), G.takeBytes(2),
                                      G.takeBytes("x", "y")],
          pcm: G.wavBytes(600, 48000) - 44, mp3: G.mp3Bytes(600) });""")
        # 16-bit PCM + its MP3: the room D7 asks for before a 10-minute take at 48 kHz is ≈ 67 MB
        self.assertEqual(r["take"], [57600000 + 9600000, 88200 + 16000, 0, 0, 192000 + 32000, 0])
        self.assertEqual(r["take"][0], r["pcm"] + r["mp3"])

    def test_sound_rows_sizes(self):
        r = core(self, r"""
          const M = G.LIMITS.chunkBytes;
          out({ M, cases: [G.split(0), G.split(1), G.split(10, 4), G.split(10, 5), G.split(M), G.split(M + 2), G.split(3 * M + 7),
                           G.split(9, 2), G.split(-5), G.split("x"), G.split(10, 0), G.split(10, 1), G.split(10, "x")],
                big: G.split(57600000).length, sum: G.split(57600000).reduce((n, p) => n + p[1] - p[0], 0),
                fits: G.split(57600000).every((p) => p[1] - p[0] <= M && p[0] % 2 === 0) });""")
        M = r["M"]
        self.assertEqual(M, 1048576)                               # 1 MiB a row
        c = r["cases"]
        self.assertEqual(c[0], [])                                 # nothing: no row
        self.assertEqual(c[1], [[0, 1]])
        self.assertEqual(c[2], [[0, 4], [4, 8], [8, 10]])
        self.assertEqual(c[3], [[0, 4], [4, 8], [8, 10]])          # an odd size goes down to even: a sample is never cut
        self.assertEqual(c[4], [[0, M]])
        self.assertEqual(c[5], [[0, M], [M, M + 2]])
        self.assertEqual(c[6], [[0, M], [M, 2 * M], [2 * M, 3 * M], [3 * M, 3 * M + 7]])
        self.assertEqual(c[7], [[0, 2], [2, 4], [4, 6], [6, 8], [8, 9]])
        self.assertEqual((c[8], c[9]), ([], []))
        self.assertEqual(c[10], [[0, 10]])                         # no size, or one under a sample: the 1 MiB rows
        self.assertEqual(c[11], [[0, 10]])
        self.assertEqual(c[12], [[0, 10]])
        self.assertEqual(r["big"], 55)                             # 10 minutes at 48 kHz: 55 rows
        self.assertEqual(r["sum"], 57600000)                       # every byte, once
        self.assertTrue(r["fits"])


class Waveform(unittest.TestCase):
    def test_bins(self):
        r = core(self, r"""
          const spike = (n, at) => { const a = new Array(n).fill(0); a[at] = 1; return a; };
          const where = (b) => b.map((v, i) => v ? i : -1).filter((i) => i >= 0);
          let x = 7; const rnd = []; for (let i = 0; i < 1000; i++) { x = (x * 16807) % 2147483647; rnd.push(x / 2147483647); }
          out({ six: G.bins([0.1, 0.5, 0.2, 1, 0, 0.4], 3), few: G.bins([0.2, 0.4], 240), none: [G.bins([]), G.bins(null), G.bins(undefined)],
                odd: G.bins([2, -1, NaN, 0.5], 4), dflt: G.bins(rnd).length, zero: G.bins(rnd, 0).length, top: Math.max(...G.bins(rnd)),
                rndMax: Math.round(Math.max(...rnd) * 255),
                spikes: [where(G.bins(spike(1000, 0))), where(G.bins(spike(1000, 500))), where(G.bins(spike(1000, 999))),
                         where(G.bins(spike(241, 240))), where(G.bins(spike(241, 0)))] });""")
        self.assertEqual(r["six"], [128, 255, 102])               # [0.1, 0.5] [0.2, 1] [0, 0.4]: the loudest of each, × 255
        self.assertEqual(r["few"], [51, 102])                     # fewer peaks than columns: one column each
        self.assertEqual(r["none"], [[], [], []])
        self.assertEqual(r["odd"], [255, 0, 0, 128])              # clamped; NaN is silence
        self.assertEqual((r["dflt"], r["zero"]), (240, 240))      # LIMITS.bins columns
        self.assertEqual(r["top"], r["rndMax"])                    # the loudest moment is never lost
        # every peak falls in exactly one column, in order (a spike lands where it was, never in two columns)
        self.assertEqual(r["spikes"], [[0], [120], [239], [239], [0]])

    def test_bins_between(self):
        r = core(self, r"""
          const b = Array.from({ length: 240 }, (_, i) => i);
          out([G.binsBetween(b, 240000, 0, 240000).length, G.binsBetween(b, 240000, 120000, 240000), G.binsBetween(b, 240000, 0, 1000),
               G.binsBetween(b, 240000, 239999, 240000), G.binsBetween(b, 240000, 240000, 240000), G.binsBetween(b, 240000, 60000, 60500),
               G.binsBetween(b, 0, 0, 10), G.binsBetween([], 100, 0, 10), G.binsBetween(null, 100, 0, 10), G.binsBetween(b, -1, 0, 10)]);""")
        self.assertEqual(r[0], 240)
        self.assertEqual(r[1], list(range(120, 240)))             # the second half
        self.assertEqual(r[2:6], [[0], [239], [239], [60]])        # a short part keeps at least one column
        self.assertEqual(r[6:], [[], [], [], []])

    def test_wave_path(self):
        r = core(self, r"""
          const full = Array.from({ length: 240 }, (_, i) => (i * 37) % 256);
          const p = G.wavePath(full, 240, 40);
          const ys = [...p.matchAll(/M[\d.]+ ([\d.]+)V([\d.]+)/g)].flatMap((m) => [Number(m[1]), Number(m[2])]);
          out({ two: G.wavePath([0, 255], 240, 40), one: G.wavePath([64]), none: [G.wavePath([], 240, 40), G.wavePath(null)],
                clamp: G.wavePath([300, -5], 240, 40), strokes: (p.match(/M/g) || []).length, lo: Math.min(...ys), hi: Math.max(...ys) });""")
        # a silent column is a dot on the middle line (½ px each way); a full one runs from 1 to h − 1
        self.assertEqual(r["two"], "M60 19.5V20.5M180 1V39")
        # default box 240 × 40; a quarter-loud column (64 / 255) is drawn by its square root: half-height 19 × 0.501 = 9.52
        self.assertEqual(r["one"], "M120 10.48V29.52")
        self.assertEqual(r["none"], ["", ""])
        self.assertEqual(r["clamp"], "M60 1V39M180 19.5V20.5")
        self.assertEqual(r["strokes"], 240)
        self.assertGreaterEqual(r["lo"], 1)
        self.assertLessEqual(r["hi"], 39)


class Rules(unittest.TestCase):
    # the magazines' minutes as the partial hands them over (db.audio_project: the official pages say "6-8 minutes" and
    # "hasta 7 minutos" — a fixed copy here: the synced data is not these tests' business)
    GV, LV = {"min": 6, "max": 8}, {"max": 7}

    def run_rules(self, js: str):
        return core(self, "const GV = G.rule(input.gv), LV = G.rule(input.lv), NONE = G.rule({});\n" + js,
                    data={"gv": self.GV, "lv": self.LV})

    def test_rule(self):
        r = core(self, r"""out([G.rule({ min: 6, max: 8 }), G.rule({ max: 7 }), G.rule({}), G.rule(null), G.rule(undefined), G.rule({ min: 8, max: 6 }),
          G.rule({ min: "6", max: "8" }), G.rule({ min: -1, max: 0 }), G.rule({ min: 7.75, max: 8 }), G.rule({ min: 6 }), G.rule({ min: "x", max: null })]);""")
        def rr(mn, mx, warn):
            return {"min": mn, "max": mx, "warn": warn, "hard": 600}
        self.assertEqual(r, [rr(360, 480, 450),                  # Grapevine: "Stories should be 6-8 minutes long"
                             rr(0, 420, 390),                    # La Viña: "hasta 7 minutos"
                             rr(0, 0, 0), rr(0, 0, 0), rr(0, 0, 0),
                             rr(0, 360, 330),                    # a minimum over the maximum is dropped
                             rr(360, 480, 450), rr(0, 0, 0),
                             rr(465, 480, 465),                  # the warning never comes before the minimum
                             rr(360, 0, 0), rr(0, 0, 0)])

    def test_zone(self):
        r = self.run_rules(r"""out({
          gv: [0, 359.9, 360, 449.9, 450, 480, 480.1, 599].map((s) => G.zone(s, GV)),
          lv: [0, 389, 390, 420, 421].map((s) => G.zone(s, LV)),
          none: [0, 599, 700].map((s) => G.zone(s, NONE)), dflt: G.zone(100), min: [100, 400].map((s) => G.zone(s, G.rule({ min: 6 }))) });""")
        self.assertEqual(r["gv"], ["under", "under", "ok", "ok", "near", "near", "over", "over"])
        self.assertEqual(r["lv"], ["ok", "ok", "near", "near", "over"])   # no minimum: "ok" from the start
        self.assertEqual(r["none"], ["ok", "ok", "ok"])
        self.assertEqual(r["dflt"], "ok")
        self.assertEqual(r["min"], ["under", "ok"])

    def test_verdict(self):
        r = self.run_rules(r"""out({ gv: [0, 359, 360, 480, 480.5, 480.6].map((s) => G.verdict(s, GV)), lv: [10, 420.5, 421].map((s) => G.verdict(s, LV)),
          none: [G.verdict(5, NONE), G.verdict(5)], min: [100, 1000].map((s) => G.verdict(s, G.rule({ min: 6 }))) });""")
        self.assertEqual(r["gv"], ["short", "short", "ok", "ok", "ok", "long"])   # half a second of slack for the stop button
        self.assertEqual(r["lv"], ["ok", "ok", "long"])
        self.assertEqual(r["none"], ["none", "none"])              # no rule known: no verdict
        self.assertEqual(r["min"], ["short", "ok"])

    def test_the_bar(self):
        r = self.run_rules(r"""out({ end: [G.barEnd(GV), G.barEnd(LV), G.barEnd(NONE), G.barEnd(G.rule({ max: 9.5 })), G.barEnd(G.rule({ max: 2 })), G.barEnd()],
          pct: [G.pct(300, GV), G.pct(270, LV), G.pct(-1, GV), G.pct(1000, GV), G.pct(1, LV), G.pct(360, GV), G.pct(480, GV), G.pct(420, LV),
                G.pct(300, NONE)] });""")
        # the bar runs to the maximum + 2 minutes (never past the 10-minute stop); without a maximum, to the stop
        self.assertEqual(r["end"], [600, 540, 600, 600, 240, 600])
        # tenths of a percent; the marks: Grapevine's minimum at 60 %, its maximum at 80 %, La Viña's at 77.8 %
        self.assertEqual(r["pct"], [50, 50, 0, 100, 0.2, 60, 80, 77.8, 50])

    def test_crossed(self):
        r = self.run_rules(r"""out({
          gv: [[359.9, 360], [360, 361], [0, 600], [419, 420], [479.9, 480.1], [569, 570], [500, 500], [361, 360]].map((x) => G.crossed(x[0], x[1], GV)),
          lv: [[359, 361], [0, 600], [419.9, 420]].map((x) => G.crossed(x[0], x[1], LV)),
          none: [[0, 600], [569, 571]].map((x) => G.crossed(x[0], x[1], NONE)),
          tight: G.crossed(0, 600, G.rule({ min: 7.5, max: 8 })), dflt: G.crossed(0, 600) });""")
        self.assertEqual(r["gv"], [["min"], [], ["min", "left1", "max", "hard_soon"], ["left1"], ["max"], ["hard_soon"], [], []])
        self.assertEqual(r["lv"], [["left1"], ["left1", "max", "hard_soon"], ["max"]])   # no minimum to reach
        self.assertEqual(r["none"], [["hard_soon"], ["hard_soon"]])                         # every take stops at 10:00
        # "one minute left" never comes before the minimum is reached (7:30 minimum, 8:00 maximum)
        self.assertEqual(r["tight"], ["min", "max", "hard_soon"])
        self.assertEqual(r["dflt"], ["hard_soon"])

    def test_trim_range(self):
        r = core(self, r"""const N = 480000;               // 10 s at 48 kHz
          out([G.trimRange(N, 48000, 0, 10), G.trimRange(N, 48000, 2, 5), G.trimRange(N, 48000, 5, 2), G.trimRange(N, 48000, 9.5, 10),
               G.trimRange(N, 48000, -3, 20), G.trimRange(N, 48000, 2), G.trimRange(24000, 48000, 0, 0.1), G.trimRange(0, 48000, 0, 1),
               G.trimRange(N, "x", 2, 3), G.trimRange(441000, 44100, 1.23, 4.56), G.trimRange(N, 48000, NaN, "x"), G.trimRange(N, 48000, 4, 4.5)]);""")
        self.assertEqual(r, [{"from": 0, "to": 480000}, {"from": 96000, "to": 240000},
                             {"from": 240000, "to": 288000},       # end before start: at least LIMITS.minTake (1 s) from the start
                             {"from": 432000, "to": 480000},       # no room after: the last second
                             {"from": 0, "to": 480000},            # clamped to the take
                             {"from": 96000, "to": 480000},        # no end: to the end
                             {"from": 0, "to": 24000},             # a take under a second: all of it
                             {"from": 0, "to": 0},
                             {"from": 96000, "to": 144000},        # a rate that is not a number: 48 kHz
                             {"from": 54243, "to": 201096},
                             {"from": 0, "to": 480000},
                             {"from": 192000, "to": 240000}])


class Takes(unittest.TestCase):
    def test_ids_numbers_length_age(self):
        r = core(self, r"""
          const now = Date.parse("2026-10-13T12:00:00Z"), day = 864e5;
          out({ ids: [G.newId(1760000000000, 0.5), G.newId(1760000000000, 0), G.newId(1760000000000, 0.999999), G.newId(now, 0.25)],
                ok: [0, 0.5, 0.999999].map((x) => !!G.clean({ id: G.newId(now, x), rate: 48000, samples: 1 })),
                many: (() => { const s = new Set(); for (let i = 0; i < 2000; i++) s.add(G.newId(now + i, (i * 7919 % 2000) / 2000)); return s.size; })(),
                next: [[], null, undefined, [{ n: 3 }, { n: 1 }], [null, { n: "x" }, { n: 2 }], [{ n: 8 }, {}]].map((t) => G.nextNumber(t)),
                dur: [G.duration({ rate: 48000, samples: 480000 }), G.duration({ rate: 0, samples: 5 }), G.duration(null), G.duration({ rate: 44100, samples: 22050 })],
                old: G.clean({ id: "t1", rate: 48000, samples: 1, created: now - 400 * day }), expired: typeof G.expired, keepDays: "keepDays" in G.LIMITS });""")
        # "t" + the time in base 36 + a random number of up to 4 base-36 digits (36⁴ = 1679616)
        self.assertEqual(r["ids"][:3], ["tmgj6k3cwi000", "tmgj6k3cw0", "tmgj6k3cwzzzy"])
        self.assertRegex(r["ids"][3], r"^t[0-9a-z]{9,12}$")
        self.assertEqual(r["ok"], [True, True, True])              # every id passes clean()
        self.assertEqual(r["many"], 2000)
        self.assertEqual(r["next"], [1, 1, 1, 4, 3, 9])
        self.assertEqual(r["dur"], [10, 0, 0, 0.5])
        # a take is kept until the visitor deletes it (D6): a year-old record is still a take, and nothing judges age
        self.assertIsNotNone(r["old"])
        self.assertEqual((r["expired"], r["keepDays"]), ("undefined", False))

    def test_clean(self):
        r = core(self, r"""
          const base = { id: "t1", rate: 48000, samples: 10 };
          const bad = [null, undefined, 42, "t1", [], {}, { id: 5, rate: 48000, samples: 1 }, { ...base, id: "a" }, { ...base, id: "x".repeat(41) },
                       { ...base, id: "bad id" }, { ...base, id: "t-1" }, { ...base, id: "t1:000001" }, { ...base, rate: 2999 }, { ...base, rate: 384001 },
                       { ...base, rate: "x" }, { ...base, samples: -1 }, { ...base, rate: undefined }];
          const full = { id: "TAKE1", pub: "lv", n: "3", name: "Mi toma", created: 1760000000000, rate: "44100.4", samples: 441000.9, peak: 2,
                         bins: [-5, 300, 12.6, "x", 7], src: "file", noise: 1, starred: "yes", gaps: 0, from: 2.9, url: "blob:x", mp3Size: 5, saved: true, extra: {},
                         v: "2", draft: 1, mp3: "yes", size: 1234.9, at: 1760000000500, saving: true, damaged: false, failed: true };
          const c = G.clean(full);
          out({ bad: bad.map((t) => G.clean(t)), full: c, keys: Object.keys(c), again: JSON.stringify(G.clean(c)) === JSON.stringify(c),
                dflt: G.clean(base), edges: [G.clean({ ...base, rate: 3000 }).rate, G.clean({ ...base, rate: 384000 }).rate, G.clean({ ...base, id: "x".repeat(40) }).id.length],
                pub: ["LV", "x", null, "gv", "lv"].map((p) => G.clean({ ...base, pub: p }).pub),
                n: [0, -4, 2.7, "x", null].map((n) => G.clean({ ...base, n }).n),
                name: [5, "x".repeat(100), null].map((name) => G.clean({ ...base, name }).name.length),
                peak: [-1, 0.5, "x"].map((peak) => G.clean({ ...base, peak }).peak),
                bins: [G.clean({ ...base, bins: new Array(300).fill(9) }).bins.length, G.clean({ ...base, bins: "x" }).bins, G.clean({ ...base, bins: { 0: 1 } }).bins],
                src: ["mic2", "recovered", "edit", "file", "mic", "", null].map((src) => G.clean({ ...base, src }).src),
                from: [-2, 3.9, "x"].map((from) => G.clean({ ...base, from }).from),
                v: [undefined, 1, 2, 2.9, "2", 0, -1, "x", 3].map((v) => G.clean({ ...base, v }).v),
                flags: [{}, { draft: 0, mp3: "" }, { draft: "yes", mp3: 1 }].map((o) => { const c = G.clean({ ...base, ...o }); return [c.draft, c.mp3]; }),
                size: [-1, 0, 10.7, "x", 1e9].map((size) => G.clean({ ...base, size }).size),
                at: [-1, 0, 5.5, "x"].map((at) => G.clean({ ...base, at }).at),
                proto: G.clean(JSON.parse('{"id":"t1","rate":48000,"samples":1,"__proto__":{"polluted":true},"bins":[1]}')),
                polluted: vm.runInContext("Object.keys(Object.prototype).length + Object.keys(Array.prototype).length", ctx) });""")
        self.assertEqual(r["bad"], [None] * 17)
        self.assertEqual(r["full"], {"id": "TAKE1", "pub": "lv", "n": 3, "name": "Mi toma", "created": 1760000000000, "rate": 44100,
                                     "samples": 441000, "peak": 1, "bins": [0, 255, 13, 0, 7], "src": "file", "noise": True, "starred": True,
                                     "gaps": False, "from": 2, "v": 2, "draft": True, "mp3": True, "size": 1234, "at": 1760000000500})
        # exactly the record of a take (url, mp3Size, saved, saving, failed, damaged — the page's own — and anything else are
        # dropped); v, draft, mp3, size and at are the device's (D1: a v2 record, a draft being made, its MP3 rows, its bytes)
        self.assertEqual(r["keys"], ["id", "pub", "n", "name", "created", "rate", "samples", "peak", "bins", "src", "noise", "starred", "gaps", "from",
                                     "v", "draft", "mp3", "size", "at"])
        self.assertTrue(r["again"])                                # cleaning twice changes nothing
        # (a record without v is the first recorder's: v 1 — recorder.js moves it to the new store)
        self.assertEqual(r["dflt"], {"id": "t1", "pub": "gv", "n": 1, "name": "", "created": 0, "rate": 48000, "samples": 10, "peak": 0,
                                     "bins": [], "src": "mic", "noise": False, "starred": False, "gaps": False, "from": 0,
                                     "v": 1, "draft": False, "mp3": False, "size": 0, "at": 0})
        self.assertEqual(r["edges"], [3000, 384000, 40])
        self.assertEqual(r["pub"], ["gv", "gv", "gv", "gv", "lv"])
        self.assertEqual(r["n"], [1, 1, 2, 1, 1])
        self.assertEqual(r["name"], [0, 80, 0])
        self.assertEqual(r["peak"], [0, 0.5, 0])
        self.assertEqual(r["bins"], [240, [], []])
        self.assertEqual(r["src"], ["mic", "recovered", "edit", "file", "mic", "mic", "mic"])
        self.assertEqual(r["from"], [0, 3, 0])
        self.assertEqual(r["v"], [1, 1, 2, 2, 2, 1, 1, 1, 3])
        self.assertEqual(r["flags"], [[False, False], [False, False], [True, True]])
        self.assertEqual(r["size"], [0, 0, 10, 0, 1000000000])
        self.assertEqual(r["at"], [0, 0, 5.5, 0])
        self.assertEqual(r["proto"]["bins"], [1])
        self.assertNotIn("polluted", r["proto"])
        self.assertEqual(r["polluted"], 0)

    def test_newest_first(self):
        r = core(self, r"""
          const list = [{ id: "a", created: 100, n: 1 }, { id: "b", created: 300, n: 2 }, { id: "c", created: 300, n: 5 }, { id: "d", created: 200, n: 3 }];
          const sorted = G.sortTakes(list);
          out({ ids: sorted.map((t) => t.id), kept: list.map((t) => t.id), fresh: sorted !== list, none: [G.sortTakes(null), G.sortTakes([])] });""")
        self.assertEqual(r["ids"], ["c", "b", "d", "a"])           # newest first; the same moment: the higher number first
        self.assertEqual(r["kept"], ["a", "b", "c", "d"])          # the list given is not reordered
        self.assertTrue(r["fresh"])
        self.assertEqual(r["none"], [[], []])

    def test_file_names(self):
        r = core(self, r"""
          const at = Date.parse("2026-10-13T17:00:00Z"), late = Date.parse("2026-10-14T03:30:00Z");
          out([G.fileName({ pub: "gv", n: 2, created: at }, "mp3"), G.fileName({ pub: "lv", n: 2, created: at }, "wav"),
               G.fileName({ pub: "lv", n: 2, name: "Mi primera toma!", created: at }, "wav"),
               G.fileName({ pub: "gv", n: 1, name: "Canción de Año Nuevo", created: at }),
               G.fileName({ pub: "gv", n: 4, name: "!!!", created: at }), G.fileName({ pub: "gv", n: 1, name: "x".repeat(100), created: at }),
               G.fileName({ pub: "xx", n: 3, created: at }), G.fileName(null), G.fileName({ pub: "lv", n: 3 }), G.fileName({ pub: "gv", n: 7, created: late }),
               G.fileName({ pub: "lv", created: at, n: 0 }, "wav")]);""")
        self.assertEqual(r, ["grapevine-story-2026-10-13-take-2.mp3", "la-vina-historia-2026-10-13-toma-2.wav",   # the magazine's language
                             "la-vina-historia-2026-10-13-mi-primera-toma.wav",                                   # an own name instead
                             "grapevine-story-2026-10-13-cancion-de-ano-nuevo.mp3",
                             "grapevine-story-2026-10-13-take-4.mp3",                                             # nothing left of it
                             "grapevine-story-2026-10-13-" + "x" * 40 + ".mp3",
                             "grapevine-story-2026-10-13-take-3.mp3",
                             "grapevine-story-audio-take-1.mp3", "la-vina-historia-audio-toma-3.mp3",            # no date
                             "grapevine-story-2026-10-13-take-7.mp3",       # 10:30 pm in Dallas (already the 14th in UTC)
                             "la-vina-historia-2026-10-13-toma-1.wav"])
        for name in r:
            self.assertRegex(name, r"^[a-z0-9-]+\.(mp3|wav)$")      # ASCII only: safe in any mail program or file system

    def test_sound_keys(self):
        r = core(self, r"""
          const keys = []; for (let s = 0; s <= 1500; s++) keys.push(G.soundKey("t1", "pcm", s));
          const shuffled = keys.slice().sort(() => 0).reverse().sort();
          const [lo, hi] = G.soundRange("t1", "pcm"), [alo, ahi] = G.soundRange("t1"), [mlo, mhi] = G.soundRange("t1", "mp3");
          const inside = (k, a, b) => k >= a && k <= b;
          out({ some: [G.soundKey("t1", "pcm", 0), G.soundKey("t1", "mp3", 12), G.soundKey("t1", "pcm", 1234567), G.soundKey("t1", "pcm", -3),
                       G.soundKey("t1", "pcm", 2.7)],
                ranges: [G.soundRange("t1", "pcm"), G.soundRange("t1"), G.soundRange("t1", "")],
                ordered: shuffled.join() === keys.join(),
                mine: keys.every((k) => inside(k, lo, hi) && inside(k, alo, ahi) && !inside(k, mlo, mhi)),
                mp3: inside(G.soundKey("t1", "mp3", 3), alo, ahi) && !inside(G.soundKey("t1", "mp3", 3), lo, hi),
                // the first recorder's crash-recovery pieces ("t1:000003") are in the take's range too (D10: they go with it)
                v1: inside("t1:000003", alo, ahi),
                others: [G.soundKey("t12", "pcm", 0), G.soundKey("t1a", "pcm", 0), G.soundKey("t", "pcm", 5), G.soundKey("T1", "pcm", 0),
                         "t12:000000", "t1a:000000"].map((k) => inside(k, alo, ahi)) });""")
        self.assertEqual(r["some"], ["t1:pcm:000000", "t1:mp3:000012", "t1:pcm:1234567", "t1:pcm:000000", "t1:pcm:000002"])
        self.assertEqual(r["ranges"], [["t1:pcm:", "t1:pcm:\uffff"], ["t1:", "t1:\uffff"], ["t1:", "t1:\uffff"]])
        self.assertTrue(r["ordered"])                              # as text, in the order they were written
        # recorder.js reads and deletes one take's rows by [id + ":" (+ kind + ":"), … + "\uffff"]: never another take's
        # (ids are letters and digits; ":" sorts apart from all of them), nor one kind's another kind's
        self.assertTrue(r["mine"])
        self.assertTrue(r["mp3"])
        self.assertTrue(r["v1"])
        self.assertEqual(r["others"], [False] * 6)


class Mail(unittest.TestCase):
    T = "Hello,\n\nTopic: {topic}\nLength: {length}\n\nMy details:{?details}\nName: {name}\nPhone: {phone}\n\n\nThanks!\n\n"

    def test_mail_body(self):
        r = core(self, r"""const T = input.t;
          out([G.mailBody(T, { length: "6:42" }), G.mailBody(T, { length: "6:42", details: "1", name: "Ana" }),
               G.mailBody(T, { topic: "  ", length: "1:00" }), G.mailBody(T, { topic: "Faith  ", length: "1:00" }), G.mailBody(T, {}),
               G.mailBody("a\r\n\r\nb"), G.mailBody("\n\nHi"), G.mailBody(null), G.mailBody(undefined, { a: 1 }),
               G.mailBody("Both:{?a}{?b}\nX", { a: "1" }), G.mailBody("Both:{?a}{?b}\nX", { a: "1", b: "2" }),
               G.mailBody("Topic: {topic}", { topic: "{name}", name: "Ana" }), G.mailBody("N: {n}", { n: 0 }),
               G.mailBody("Address: {address}\nEnd", { address: "1 Main St\nDallas, TX" }), G.mailBody("Head:{?x}\nA: {a}", { x: " ", a: "1" })]);""",
                 data={"t": self.T})
        self.assertEqual(r, ["Hello,\n\nLength: 6:42\n\nThanks!",                         # empty lines go; one blank line between parts
                             "Hello,\n\nLength: 6:42\n\nMy details:\nName: Ana\n\nThanks!",  # the heading only over details
                             "Hello,\n\nLength: 1:00\n\nThanks!",                         # blanks are empty
                             "Hello,\n\nTopic: Faith\nLength: 1:00\n\nThanks!",           # no spaces at a line's end
                             "Hello,\n\nThanks!",
                             "a\n\nb", "Hi", "", "",
                             "X", "Both:\nX",                                              # {?a}{?b}: both must be there
                             "Topic: {name}",                                              # a value is never filled in again
                             "N: 0",                                                       # 0 is a value
                             "Address: 1 Main St\nDallas, TX\nEnd", "A: 1"])

    def test_the_real_messages(self):
        """The templates of src/_i18n/community.json in each magazine's language (Grapevine: English; La Viña: Spanish —
        what the partial hands the script), with every detail and with none."""
        s = strings()
        tpl = {"gv": s["community.recorder.mail_gv_body"]["en"], "lv": s["community.recorder.mail_lv_body"]["es"]}
        full = {"topic": "Gratitude", "length": "6:42", "file": "grapevine-story-2026-10-13-take-2.mp3", "format": "MP3", "name": "Jane Doe",
                "phone": "555-0100", "email": "jane@example.org", "address": "1 Main St\nDallas, TX 75201", "place": "Dallas, Texas",
                "credit": "First name and last initial", "details": "1",
                "permission": "Yo, cedo a La Viña los derechos de autor de esta grabación."}
        bare = {"topic": "", "length": "6:42", "file": "la-vina-historia-2026-10-13-toma-1.mp3", "format": "MP3", "name": "", "phone": "",
                "email": "", "address": "", "place": "", "credit": "", "details": "", "permission": ""}
        r = core(self, r"""out({ full: { gv: G.mailBody(input.tpl.gv, input.full), lv: G.mailBody(input.tpl.lv, input.full) },
          bare: { gv: G.mailBody(input.tpl.gv, input.bare), lv: G.mailBody(input.tpl.lv, input.bare) } });""",
                 data={"tpl": tpl, "full": full, "bare": bare})
        for kind in ("full", "bare"):
            for pub in ("gv", "lv"):
                body = r[kind][pub]
                with self.subTest(kind=kind, pub=pub):
                    self.assertNotRegex(body, r"[{}]")                  # every placeholder and {?mark} filled or gone
                    self.assertNotIn("\n\n\n", body)
                    self.assertEqual(body, body.strip())
                    self.assertIn("6:42", body)
                    self.assertIn(full["file"] if kind == "full" else bare["file"], body)
        for pub in ("gv", "lv"):
            for k in ("topic", "name", "phone", "email", "place", "credit"):
                self.assertIn(full[k], r["full"][pub], (pub, k))
            self.assertIn("1 Main St\nDallas, TX 75201", r["full"][pub])
            self.assertLess(len(r["bare"][pub].splitlines()), len(r["full"][pub].splitlines()) - 6)
        # the details' heading only over details; La Viña's sentence quoted when there is one (Grapevine's message has its own)
        self.assertIn("in case my story is chosen:\nName: Jane Doe", r["full"]["gv"])
        self.assertNotIn("in case my story is chosen", r["bare"]["gv"])
        self.assertIn("por si mi historia es seleccionada:\nNombre completo: Jane Doe", r["full"]["lv"])
        self.assertNotIn("por si mi historia es seleccionada", r["bare"]["lv"])
        self.assertIn("\n«" + full["permission"] + "»\n", r["full"]["lv"])
        self.assertEqual(r["bare"]["lv"].count("«"), 1)            # only «Graba tu historia»
        self.assertNotIn(full["permission"], r["full"]["gv"])
        self.assertIn("I give AA Grapevine permission to use my story.", r["bare"]["gv"])
        for gone in ("Topic:", "Name:", "Phone:", "Email:", "Mailing address:", "Location:", "Please show my name as:"):
            self.assertNotIn(gone, r["bare"]["gv"])
        for gone in ("Tema:", "Nombre completo:", "Teléfono:", "Correo electrónico:", "Dirección postal:", "Lugar:", "Por favor mostrar"):
            self.assertNotIn(gone, r["bare"]["lv"])

    def test_mailto(self):
        r = core(self, r"""
          const head = "mailto:x@y.org?subject=S&body=".length, room = G.LIMITS.mailMax - head;
          out({ link: G.mailto("webcoord@aagrapevine.org", "Audio Project story: Faith & hope", "Hello,\n\nLine 2", "short"),
                crlf: G.mailto("x@y.org", "S", "a\r\nb\nc").href, cr: G.mailto("x@y.org", "S", "a\r\n\r\nb").href,
                to: [" x@y.org?cc=evil@z.org&bcc=a@b ", "x@y.org\r\nBcc: e@z", "Ana <ana@x.org>", null, "ana+gv@x.org"].map((t) => G.mailto(t, "S", "b").href),
                es: G.mailto("manuscritoslv@aagrapevine.org", "Graba tu historia: Año", "Tema: Fe").href,
                edge: [G.mailto("x@y.org", "S", "a".repeat(room), "Short"), G.mailto("x@y.org", "S", "a".repeat(room + 1), "Short"),
                       G.mailto("x@y.org", "S", "a".repeat(room + 1))],
                max: G.LIMITS.mailMax, room });""")
        self.assertEqual(r["link"], {"href": "mailto:webcoord@aagrapevine.org?subject=Audio%20Project%20story%3A%20Faith%20%26%20hope"
                                             "&body=Hello%2C%0D%0A%0D%0ALine%202", "cut": False})
        # line ends are CRLF in a mailto: link (RFC 6068), whatever the message had — never a doubled CR
        self.assertEqual(r["crlf"], "mailto:x@y.org?subject=S&body=a%0D%0Ab%0D%0Ac")
        self.assertEqual(r["cr"], "mailto:x@y.org?subject=S&body=a%0D%0A%0D%0Ab")
        # the address keeps only what an address has: no "?" or "&" of its own, no line break (no added Cc / Bcc)
        self.assertEqual(r["to"], ["mailto:x@y.orgccevil@z.orgbcca@b?subject=S&body=b", "mailto:x@y.orgBcce@z?subject=S&body=b",
                                   "mailto:Anaana@x.org?subject=S&body=b", "mailto:?subject=S&body=b", "mailto:ana+gv@x.org?subject=S&body=b"])
        for href in r["to"]:
            self.assertEqual(href.count("?"), 1)
            self.assertEqual(href.count("&"), 1)
        self.assertEqual(r["es"], "mailto:manuscritoslv@aagrapevine.org?subject=Graba%20tu%20historia%3A%20A%C3%B1o&body=Tema%3A%20Fe")
        fits, over, bare = r["edge"]
        self.assertEqual((len(fits["href"]), fits["cut"]), (r["max"], False))   # exactly LIMITS.mailMax: the whole message
        self.assertEqual(over, {"href": "mailto:x@y.org?subject=S&body=Short", "cut": True})   # one more: the short one
        self.assertEqual(bare, {"href": "mailto:x@y.org?subject=S", "cut": True})               # no short one: no message

    def test_web_compose_links(self):
        r = core(self, r"""
          const gh = "https://mail.google.com/mail/?view=cm&fs=1&to=x%40y.org&su=S&body=".length;
          const oh = "https://outlook.live.com/mail/0/deeplink/compose?to=x%40y.org&subject=S&body=".length;
          out({ gmail: G.gmail("x@y.org", "S", "a\nb", "s"), outlook: G.outlook("x@y.org", "S", "a\nb", "s"),
                inject: G.gmail("x@y.org&cc=evil@z.org", "S&body=x", "b").href,
                gEdge: [G.gmail("x@y.org", "S", "a".repeat(G.LIMITS.linkMax - gh), "s"), G.gmail("x@y.org", "S", "a".repeat(G.LIMITS.linkMax - gh + 1), "Short"),
                        G.gmail("x@y.org", "S", "a".repeat(G.LIMITS.linkMax - gh + 1))],
                oEdge: [G.outlook("x@y.org", "S", "a".repeat(G.LIMITS.linkMax - oh), "s").cut, G.outlook("x@y.org", "S", "a".repeat(G.LIMITS.linkMax - oh + 1), "Short")],
                max: G.LIMITS.linkMax });""")
        self.assertEqual(r["gmail"], {"href": "https://mail.google.com/mail/?view=cm&fs=1&to=x%40y.org&su=S&body=a%0D%0Ab", "cut": False})
        self.assertEqual(r["outlook"], {"href": "https://outlook.live.com/mail/0/deeplink/compose?to=x%40y.org&subject=S&body=a%0D%0Ab", "cut": False})
        # every part is encoded: an address or a subject cannot add parameters of its own
        self.assertEqual(r["inject"], "https://mail.google.com/mail/?view=cm&fs=1&to=x%40y.org%26cc%3Devil%40z.org&su=S%26body%3Dx&body=b")
        fits, over, bare = r["gEdge"]
        self.assertEqual((len(fits["href"]), fits["cut"]), (r["max"], False))
        self.assertEqual(over, {"href": "https://mail.google.com/mail/?view=cm&fs=1&to=x%40y.org&su=S&body=Short", "cut": True})
        self.assertEqual(bare, {"href": "https://mail.google.com/mail/?view=cm&fs=1&to=x%40y.org&su=S", "cut": True})
        self.assertFalse(r["oEdge"][0])
        self.assertEqual(r["oEdge"][1], {"href": "https://outlook.live.com/mail/0/deeplink/compose?to=x%40y.org&subject=S&body=Short", "cut": True})


# Real user agents (2026): what helpFor() says for each
UAS = [
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1", 5, "ios"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/140.0.7339.122 Mobile/15E148 Safari/604.1", 5, "ios"),
    ("Mozilla/5.0 (iPad; CPU OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1", 5, "ios"),
    # an iPad asks for the desktop site: a Mac's user agent, but a touch screen
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15", 5, "ios"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15", 0, "safari"),
    ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36", 5, "android"),
    ("Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-S921U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/27.0 Chrome/125.0.0.0 Mobile Safari/537.36", 5, "android"),
    ("Mozilla/5.0 (Android 14; Mobile; rv:143.0) Gecko/143.0 Firefox/143.0", 5, "android"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0", 0, "firefox"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0", 0, "edge"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36", 0, "chrome"),
    ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36", 0, "chrome"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36", 0, "chrome"),
    # headless Chrome (the browser checks): Chrome, not Safari (r10 A24)
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/156.0.0.0 Safari/537.36", 0, "chrome"),
    ("", 0, "other"),
    ("curl/8.0", 0, "other"),
]


class Browser(unittest.TestCase):
    def test_support(self):
        r = core(self, r"""out([{}, null, { secure: true }, { secure: true, media: true }, { secure: true, media: true, audio: true, worklet: true },
          { secure: true, media: true, audio: true, script: true }, { secure: true, media: true, audio: true },
          { secure: true, media: true, audio: true, worklet: true, script: true }, { media: true, audio: true, worklet: true },
          { secure: true, audio: true, worklet: true }].map((e) => G.support(e)));""")
        self.assertEqual(r, [{"record": "", "why": "insecure"}, {"record": "", "why": "insecure"}, {"record": "", "why": "no_media"},
                             {"record": "", "why": "no_audio"}, {"record": "worklet", "why": ""}, {"record": "script", "why": ""},
                             {"record": "", "why": "no_audio"}, {"record": "worklet", "why": ""},       # the worklet when both are there
                             {"record": "", "why": "insecure"},                                          # http:// — no microphone at all
                             {"record": "", "why": "no_media"}])

    def test_error_kind(self):
        r = core(self, r"""out(["NotAllowedError", "PermissionDeniedError", "SecurityError", "NotFoundError", "DevicesNotFoundError", "NotReadableError",
          "TrackStartError", "AbortError", "OverconstrainedError", "ConstraintNotSatisfiedError", "TypeError", "InvalidStateError"]
          .map((name) => G.errorKind({ name })).concat([G.errorKind(null), G.errorKind({}), G.errorKind("NotAllowedError"), G.errorKind({ code: "NotFoundError" }),
          G.errorKind({ message: "NotReadableError: Could not start audio source" }), G.errorKind({ name: 5 })]));""")
        # today's names and the older Chrome / Firefox ones (PermissionDenied, DevicesNotFound, TrackStart, ConstraintNotSatisfied)
        self.assertEqual(r, ["denied", "denied", "denied", "nomic", "nomic", "busy", "busy", "busy", "constraint", "constraint", "other", "other",
                             "other", "other", "other", "nomic", "busy", "other"])

    def test_help_for(self):
        r = core(self, "out(input.uas.map((u) => G.helpFor(u[0], u[1])).concat([G.helpFor(), G.helpFor(null, 'x')]));", data={"uas": UAS})
        self.assertEqual(r, [u[2] for u in UAS] + ["other", "other"])

    def test_accept(self):
        r = core(self, "out([G.accept(true), G.accept(false), G.accept()]);")
        ios, other, dflt = r
        # an iPhone or iPad treats "audio/*" as a video picker (WebKit 242110): file extensions only there
        self.assertNotIn("audio/", ios)
        self.assertEqual(other, "audio/*," + ios)
        self.assertEqual(dflt, other)
        exts = ios.split(",")
        self.assertEqual(len(exts), len(set(exts)))
        for e in exts:
            self.assertRegex(e, r"^\.[a-z0-9]+$")
        for e in (".m4a", ".mp3", ".wav", ".aac", ".caf", ".ogg", ".opus", ".webm", ".flac", ".mp4"):   # Voice Memos, recorders, apps
            self.assertIn(e, exts)


class Storage(unittest.TestCase):
    def test_store_error(self):
        r = core(self, r"""
          const e = (name, message, code) => ({ name, message: message || "", code });
          out([e("QuotaExceededError"), e("UnknownError", "Quota exceeded."), e("Error", "", 22), e("NS_ERROR_DOM_QUOTA_REACHED"),
               e("SecurityError"), e("InvalidAccessError"), e("NotSupportedError"),
               e("UnknownError", "The user denied permission to access the database."),
               e("VersionError"),
               e("UnknownError", "Error preparing Blob/File data to be stored in object store"), e("UnknownError", "Connection to Indexed Database server lost. Refresh the page to try again"),
               e("AbortError"), e("InvalidStateError", "The database connection is closing."), e("TimeoutError"), e("TransactionInactiveError"),
               e("DataError"), e("NotFoundError"), e("GoneError"),
               null, undefined, {}, "x", 5, new Error("boom")].map((x) => G.storeError(x)));""")
        self.assertEqual(r[:4], ["quota"] * 4)                     # the device is full: ask to delete takes (D7)
        # this browser keeps nothing (Lockdown Mode, blocked data — Chrome with site data blocked: UnknownError "The user
        # denied permission to access the database.", r10 A9: not tried again and again, and no "reload")
        self.assertEqual(r[4:8], ["none"] * 4)
        self.assertEqual(r[8], "version")                          # a newer page changed the database: reload
        # what a reopen or a moment may fix — Safari's lost connection and its Blob refusal included: tried again (D4)
        self.assertEqual(r[9:], ["transient"] * 15)

    def test_leaves(self):
        r = core(self, r"""
          const here = "https://neta65.github.io/aagrapevine/contribute/#record";
          const go = (o) => G.leaves(Object.assign({ href: "https://neta65.github.io/aagrapevine/events/", target: "", download: false, go: false,
                                                    button: 0, keys: false, prevented: false }, o), here);
          out({ yes: [go({}), go({ href: "https://neta65.github.io/aagrapevine/es/contribute/" }), go({ target: "_self" }), go({ target: "_TOP" }),
                      go({ target: "_parent" }), go({ href: "https://neta65.github.io/aagrapevine/contribute/" }),
                      go({ href: "https://neta65.github.io/aagrapevine/contribute/?x=1#record" }), go({ href: "https://www.aagrapevine.org/" }),
                      go({ href: "http://example.org/a#b" }), go({ button: undefined })],
                no: [go({ href: "https://neta65.github.io/aagrapevine/contribute/#deadlines" }), go({ href: "https://neta65.github.io/aagrapevine/contribute/#" }),
                     go({ target: "_blank" }), go({ target: "gmail" }), go({ download: true }), go({ go: true }), go({ button: 1 }), go({ button: 2 }),
                     go({ keys: true }), go({ prevented: true }), go({ href: "mailto:a@b.org" }), go({ href: "tel:+15555550100" }),
                     go({ href: "blob:https://neta65.github.io/x" }), go({ href: "javascript:void(0)" }), go({ href: "" })],
                junk: [G.leaves(), G.leaves(null, here), G.leaves("x", here), G.leaves({ href: "https://a.org/" }), G.leaves({ href: "https://a.org/#x" }, null)] });""")
        # a link that loads another page in this tab (another page, the other language, this page again without its
        # #fragment, another site): the take would be gone — asked first
        self.assertEqual(r["yes"], [True] * 10)
        # nothing leaves: a #fragment of this page, a new tab or window, a download, the page's own links, a middle or right
        # click, a modifier key, a click already handled, mail / phone / blob: / javascript: addresses
        self.assertEqual(r["no"], [False] * 15)
        self.assertEqual(r["junk"], [False, False, False, True, True])


class Module(unittest.TestCase):
    def test_shape_and_constants(self):
        r = core(self, r"""
          const w = {}, c = vm.createContext({ window: w });
          vm.runInContext(fs.readFileSync("src/assets/js/recorder-core.js", "utf8"), c);
          out({ keys: Object.keys(G), browser: Object.keys(w.GVRec), notGlobal: vm.runInContext("typeof GVRec", c), node: typeof ctx.GVRec,
                v: [G.VERSION, G.SCHEMA, G.DB_NAME, G.KEEP_KEY], L: G.LIMITS, FILE: G.FILE,
                db: [G.dbfs(G.LIMITS.quiet), G.dbfs(G.LIMITS.clip), G.dbfs(G.LIMITS.silent), G.dbfs(G.LIMITS.normalizeTo)] });""")
        self.assertEqual(r["keys"], API)                           # exactly these, in this order
        self.assertEqual(r["browser"], API)                        # window.GVRec in a browser…
        self.assertEqual(r["notGlobal"], "undefined")              # …and nothing else on the page's global
        self.assertEqual(r["node"], "object")                      # globalThis.GVRec without a window
        # one origin hosts every NETA65 project: prefixed; the database's name never changes, its schema is 2 (the sound as bytes)
        self.assertEqual(r["v"], ["1.0.0", 2, "gvlv-recorder", "gvlv-rec-keep"])
        L = r["L"]
        self.assertEqual(L, {"maxTakes": 8, "hardStop": 600, "warnBefore": 30, "quiet": 0.1, "clip": 0.989, "silent": 0.003,
                             "silentFor": 5, "gap": 1.5, "zeroFor": 3, "flushEvery": 3, "partFresh": 120, "chunkBytes": MIB, "idbOpen": 10,
                             "idbTx": 30, "retryEvery": 20, "bins": 240, "mp3Kbps": 128, "mp3Rate": 44100, "normalizeTo": 0.891,
                             "maxGain": 10, "minTake": 1, "bigMail": 18 * MIB, "shareMax": 50 * MIB, "mailMax": 1800, "linkMax": 7000,
                             "importBytes": 80 * MIB, "importSec": 1200})
        self.assertEqual(r["FILE"], {"gv": {"base": "grapevine-story", "take": "take"}, "lv": {"base": "la-vina-historia", "take": "toma"}})
        # the levels in decibels, as the comments say: −20 dBFS quiet, clipping from −0.1 dBFS, silence under −50, "Even out" to −1
        self.assertAlmostEqual(r["db"][0], -20, places=6)
        self.assertTrue(-0.1 < r["db"][1] < 0)
        self.assertTrue(-51 < r["db"][2] < -50)
        self.assertAlmostEqual(r["db"][3], -1, places=2)
        self.assertAlmostEqual(dbfs(L["maxGain"]), 20)             # at most +20 dB
        # what LAME in WebAssembly takes: a constant bit rate it knows, an output rate it knows
        self.assertIn(L["mp3Kbps"], (8, 16, 24, 32, 40, 48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320))
        self.assertIn(L["mp3Rate"], (8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000))
        self.assertLess(L["warnBefore"], 60)                       # "near" comes after "one minute left"
        # a 3-second flush of 48 kHz PCM (288 kB) is one row; a whole take's rows go a few to a transaction
        self.assertLess(L["flushEvery"] * 48000 * 2, L["chunkBytes"])
        self.assertLess(L["idbOpen"], L["idbTx"])

    def test_never_throws_on_garbage(self):
        """What the page hands these comes from storage, the markup and the visitor: garbage gives an answer, never an error.
        (The sample functions — toInt16, toFloat32, peak, applyGain, downmix — get the audio engine's own arrays; readWav is the
        tests' own.)"""
        r = core(self, r"""
          const names = ["fill", "clock", "clockTenths", "spoken", "slug", "ymd", "dbfs", "meter", "level", "gainFor", "wavHeader", "mp3Bytes",
            "wavBytes", "takeBytes", "split", "bins", "binsBetween", "wavePath", "rule", "zone", "verdict", "barEnd", "pct", "crossed", "trimRange",
            "newId", "duration", "clean", "fileName", "soundKey", "soundRange", "mailBody", "mailto", "gmail", "outlook", "support", "errorKind",
            "helpFor", "accept", "storeError", "leaves"];
          const junk = [undefined, null, NaN, -1, 0, "x", "", {}, [], true, Infinity, { length: 3 }, JSON.parse('{"__proto__":{"evil":1}}')];
          const threw = [];
          for (const n of names) for (const j of junk) for (const k of [1, 2, 4]) {
            try { G[n](...new Array(k).fill(j)); } catch (e) { threw.push(n + "(" + String(j) + " ×" + k + "): " + e.message); }
          }
          out({ threw, polluted: vm.runInContext("Object.keys(Object.prototype).length + Object.keys(Array.prototype).length", ctx) });""")
        self.assertEqual(r["threw"], [])
        self.assertEqual(r["polluted"], 0)                          # nothing changed the built-in prototypes

    def test_plain_script(self):
        src = (ROOT / CORE).read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = "\n".join(line.split("//")[0] if not re.search(r"https?:\\?/", line) else line for line in code.splitlines())
        # old Safari: no optional chaining, no ??, no modules, no arrow functions or let / const in this file; no page objects
        # (recorder.js owns the microphone, the storage and the screen)
        self.assertNotRegex(code, r"(?m)\?\.[A-Za-z_(\[]|\?\?|^\s*(import|export)\s")
        for bad in ("=>", "let ", "const ", "class ", "async ", "document", "localStorage", "sessionStorage", "fetch(", "navigator",
                    "XMLHttpRequest", "indexedDB", "location", "AudioContext", "Blob", "setTimeout", "Date.now", "Math.random"):
            self.assertNotIn(bad, code, bad)
        self.assertIn('typeof window !== "undefined" ? window : globalThis', code)
        self.assertIn('"use strict";', code)
        acorn = ROOT / "node_modules" / "acorn" / "dist" / "acorn.mjs"
        if not acorn.is_file():
            self.skipTest("node_modules (acorn, with Eleventy) is not installed")
        r = run_js(self, r"""
          const acorn = await imp("node_modules/acorn/dist/acorn.mjs");
          const res = {};
          for (const v of [2019, 5]) {
            try { acorn.parse(fs.readFileSync("src/assets/js/recorder-core.js", "utf8"), { ecmaVersion: v, sourceType: "script" }); res[v] = "ok"; }
            catch (e) { res[v] = e.message; }
          }
          out(res);""", needs_modules=False)
        self.assertEqual(r, {"2019": "ok", "5": "ok"})             # the site's browsers' language — and even ES5


if __name__ == "__main__":
    unittest.main()
