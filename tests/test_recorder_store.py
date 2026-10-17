"""The story recorder keeps every take on the device until the visitor deletes it (round 10, r10/DESIGN.md D1–D11):
src/assets/js/recorder.js and recorder-core.js run in Node, page load after page load, over a pretend browser storage
that can fail the way phones fail (tests/fakeidb.js: IndexedDB, Web Locks, navigator.storage, a clock the test moves).

  * Bytes        — Safari's private window refuses every Blob in IndexedDB (WebKit 156347): takes are still saved, and
                   no value the recorder ever writes holds a Blob; the take is there on the next page
  * Recording    — a take is on the device while it is made: its draft at Start, its sound every 3 seconds (one row
                   per write, in order), and Stop's one final write (PCM bytes = samples × 2, MP3 rows of at most
                   1 MiB); Discard drops it all; a write that fails is done again with the same row number (nothing
                   twice, nothing missing); Stop during a write; a page that dies mid-take leaves a draft that the
                   next page brings back; a final write that fails says so and leaves the draft for that
  * No latch     — one failed write leaves THAT take "not saved yet" (badge, the "unsaved" box, leaving asks first), it is
                   tried again until it works (every 20 s, when the page is shown again, after another take is saved),
                   and a later take is saved as usual; a full device says "full", and deleting a take saves the one
                   waiting; a write that throws halfway leaves nothing half-written; short of room, the visitor is told
                   before a take
  * Listing      — one take that can't be read is shown as damaged, nothing is deleted and the others are listed; a take
                   40 days old is still there; drafts: a leftover one comes back as "Recovered recording", one under a
                   second goes, one another tab is making (its Web Lock) is left alone; the first recorder's Blob rows are
                   moved to the new store (and its crash pieces recovered); unreadable ones stay until Delete
  * Reaching it  — an open that never answers or a newer database: the box says "reload", Try again recovers;
                   an open that answers too late is closed; a connection the browser drops is opened again; an older
                   Safari (no getAll / getAllKeys / commit) lists and deletes through cursors
  * Choices      — "Keep my recordings" off takes only this page's takes off the device; Delete all spares a take
                   another tab is making; deleting a take while it is being written leaves nothing behind
  * Leaving      — a link click while a take is not saved (or being made) asks first, in the page (an iPhone shows no
                   beforeunload question): Cancel stays, OK goes; links that don't leave are not asked about
  * The browser  — persist() is asked once a page, from the tap that saves; Back from the back-forward cache (pageshow
                   persisted) lists the device's takes again and keeps the ones only in this page
  * Edges        — the sound so far is written when the page is hidden and on pagehide; Stop, then a link at once: the
                   take comes back whole; a take another tab is recording is left alone; an added recording (an import,
                   an edit) whose page closes mid-save comes back (D2: its PCM is on the device before the final write)
  The review's fixes (r10 fix-list.md, unit A):
  * LostStore    — a private window whose database the browser lost (iOS ended the process holding it) saves its takes
                   again from the page's own copy, on visible and on Back — also when both come at once (N1); a normal
                   window keeps no sound of a saved take; a loss while a take is recorded, or between an added take's
                   writes, never leaves it "saved" with its start missing (N2); another iPhone browser's private tab keeps
                   the sound too, and a saved take lost with no copy in the page says so, never "saved" (N3)
  * OneTake      — Stop finishing while the list is read again: the take's own draft is never adopted; one id, one entry
  * Records      — a star, a name or an MP3 never brings back a take deleted in another tab, and changes only its fields;
                   a v1 record written back over a moved take is read from its rows and put right
  * KeepSwitch   — "Keep" off and on during a write: the take is whole the moment it says "saved" — also when the
                   stopped write's drop is tried again (N5); "Keep" off takes back the main button's "not saved" notice
                   (V5)
  * Retries      — tried again 3, 6, 12, 20 s after a failure, then every 20 s, and when the page is hidden or goes; a write
                   that keeps failing shows the take's size (a full iPhone says UnknownError); "saved" said once it is;
                   Stop's failed save is pointed at by the main button until it is saved; a Try again that fails again
                   says so (V6)
  * Mending      — a database made without its "sound" store is mended one version up, and opened by later pages
  * Asking       — an MP3 being made asks nothing, an edit does; an encoder whose files — or the .wasm's body — never
                   come gives up after 60 s and the jobs behind it run (N4); mail / phone / calendar links ask nothing and
                   let the browser's question pass once (3 s); a #record link with a modifier key is the browser's
  * Telling      — the "This device" line per browser (private, Safari, "this browser" on an iPhone or iPad — Chrome,
                   Firefox, Edge there send a Mac's address line —, a Mac, none in an app's browser), the private-tab check
                   asked of every iPhone / iPad browser and of Safari, and "private" said by Safari only
  (N1–N5, V1–V8: the findings of r10's second review.)
Every test also checks that the page's own code threw nothing and left no promise rejection unhandled.
Skipped without Node.js.

    python -m unittest tests.test_recorder_store -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_recorder_page import config_like_the_partial  # noqa: E402

# The page (/contribute/ with the recorder), as many times as a test loads it, over one pretend browser storage W:
#   page(W, {ua, touch, install, audio, encoder, noLocks, noStorage, limits, label}) → P = {C (the component), R (GVRec),
#     tab (W.client), said (what was announced), classes (html's classes), click(href, attrs, init) → true when the click
#     was stopped, pageshow(persisted), hidden(), visible(), leave() (pagehide, then the page goes), crash() (it just
#     goes), leaveGuard() (beforeunload listeners)}
#     (touch: navigator.maxTouchPoints — 5 for UA.iphone, else 0; install: install-core.js loaded too, so an app's own
#     browser is known: inApp)
#   audioKit() + feed(P, kit, seconds): a microphone (ScriptProcessor blocks of 4096 samples at 48 kHz, block i at
#     level(i), the clock moving on with them); encoderKit(): an MP3 encoder (3 bytes a sample: a 10-second take's MP3
#     needs two rows)
#   device(W) → the database as stored ({version, stores, takes: [...], sound: [...]}); rows(W, id, kind) → its sound
#     rows in key order; meta(W, id, seconds, extra) / sound(seconds, mp3Bytes) → what add() takes; view(C) → the list
HARNESS = r"""
import vm from "node:vm";
const { createWorld, hasBlob } = await imp("tests/fakeidb.js");
const CORE = fs.readFileSync("src/assets/js/recorder-core.js", "utf8");
const APP = fs.readFileSync("src/assets/js/recorder.js", "utf8");
const INSTALL = fs.readFileSync("src/assets/js/install-core.js", "utf8");
const unhandled = [];
process.on("unhandledRejection", (e) => { unhandled.push(String((e && (e.stack || e.message)) || e)); });
const UA = {
  iphone: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
  chrome: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
};
const HERE = "https://neta65.github.io/aagrapevine/contribute/";
const DB = "gvlv-recorder", LOCK = "gvlv-rec:", DAY = 864e5;
let urls = 0;

function audioKit(rate) {
  const kit = { sp: null, rate: rate || 48000, i: 0 };
  function AC() { this.sampleRate = kit.rate; this.state = "running"; this.destination = {}; this.onstatechange = null; }
  AC.prototype.createScriptProcessor = function () { const sp = { connect() {}, disconnect() {}, onaudioprocess: null }; kit.sp = sp; return sp; };
  AC.prototype.createGain = function () { return { gain: { value: 1 }, connect() {}, disconnect() {} }; };
  AC.prototype.createMediaStreamSource = function () { return { connect() {}, disconnect() {} }; };
  AC.prototype.resume = function () { this.state = "running"; return Promise.resolve(); };
  AC.prototype.suspend = function () { return Promise.resolve(); };
  AC.prototype.close = function () { this.state = "closed"; return Promise.resolve(); };
  const track = { readyState: "live", muted: false, stop() {}, getSettings: () => ({ deviceId: "mic-1" }) };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  kit.AC = AC;
  kit.media = { getUserMedia: () => Promise.resolve(stream), enumerateDevices: () => Promise.resolve([]) };
  return kit;
}
// block i of a take holds level(i) all through: each block can be found again in what was stored
const level = (i) => ((i % 40) + 5) / 100;
async function feed(P, kit, sec) {
  const n = Math.round(sec * kit.rate / 4096);
  for (let k = 0; k < n; k++) {
    const f = new Float32Array(4096).fill(level(kit.i++));
    kit.sp.onaudioprocess({ inputBuffer: { getChannelData: () => f } });
    await P.W.tick(4096 / kit.rate * 1000);
  }
}
function encoderKit(perSample) {
  const kit = { per: perSample || 3 };
  const enc = () => ({ configure() {}, encode: (chs) => new Uint8Array(Math.round(chs[0].length * kit.per)).fill(0xab),
    finalize: () => new Uint8Array(417).fill(0xcd) });
  kit.lib = { createEncoder: (type, mod, cb) => { if (cb) cb({ compiled: true }); return Promise.resolve(enc()); } };
  kit.fetch = () => Promise.resolve({ ok: true, status: 200, arrayBuffer: () => Promise.resolve(new ArrayBuffer(16)) });
  return kit;
}

function page(W, o) {
  o = o || {};
  const tab = W.client(o.label), reg = {}, said = [], classes = new Set(), win = {}, doc = {};
  const add = (where) => (type, fn, cap) => { (where[type] = where[type] || []).push({ fn, cap: cap === true || !!(cap && cap.capture) }); };
  const remove = (where) => (type, fn) => { const l = where[type] || [], i = l.findIndex((x) => x.fn === fn); if (i >= 0) l.splice(i, 1); };
  W.ls = W.ls || {};
  const ua = o.ua || UA.chrome;
  const navigator = { userAgent: ua, maxTouchPoints: o.touch !== undefined ? o.touch : ua === UA.iphone ? 5 : 0 };
  if (!o.noLocks) navigator.locks = tab.locks;
  if (!o.noStorage) navigator.storage = tab.storage;
  if (o.audio) navigator.mediaDevices = o.audio.media;
  const document = {
    addEventListener: add(doc), removeEventListener: remove(doc), visibilityState: "visible", URL: HERE, activeElement: null, body: {}, head: {},
    getElementById: (id) => (id === "rec-config" ? { textContent: JSON.stringify(input.cfg) } : null),
    documentElement: { classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c) } },
    querySelectorAll: () => [], createElement: () => { throw new Error("no DOM in these tests"); },
  };
  const ctx = vm.createContext(Object.assign({
    console, Blob, File, document, navigator, screen: { width: 390, height: 844 }, isSecureContext: true,
    URL: { createObjectURL: () => "blob:" + HERE + (++urls), revokeObjectURL() {} },
    localStorage: { getItem: (k) => (k in W.ls ? W.ls[k] : null), setItem: (k, v) => { W.ls[k] = String(v); } },
    matchMedia: () => ({ matches: false }), addEventListener: add(win), removeEventListener: remove(win),
  }, tab.globals, o.audio ? { AudioContext: o.audio.AC } : {}, o.encoder ? { WasmMediaEncoder: o.encoder.lib, fetch: o.encoder.fetch } : {}));
  if (!o.encoder) vm.runInContext("delete globalThis.WebAssembly;", ctx);      // no MP3 encoder: takes stay WAV
  vm.runInContext("var window = globalThis; window.GV = { announce: function (m) { window.__said.push(m); } };" +
    "window.Alpine = { data: function (n, f) { window.__reg[n] = f; } };", Object.assign(ctx, { __reg: reg, __said: said }));
  if (o.install) vm.runInContext(INSTALL, ctx, { filename: "install-core.js" });
  vm.runInContext(CORE, ctx, { filename: "recorder-core.js" });
  if (o.limits) Object.assign(ctx.GVRec.LIMITS, o.limits);
  vm.runInContext(APP, ctx, { filename: "recorder.js" });
  (doc["alpine:init"] || []).forEach((l) => l.fn());
  const C = reg.storyRecorder();
  C.$root = { scrollIntoView() {} }; C.$nextTick = (f) => f(); C.$refs = {};
  C.init();
  const fire = (where, type, ev) => { for (const l of (where[type] || []).slice()) l.fn(ev || { type }); };
  return {
    W, tab, C, R: ctx.GVRec, ctx, said, classes, win, doc,
    leaveGuard: () => (win.beforeunload || []).length,
    pageshow: (persisted) => fire(win, "pageshow", { type: "pageshow", persisted: !!persisted }),
    hidden() { document.visibilityState = "hidden"; fire(doc, "visibilitychange"); },
    visible() { document.visibilityState = "visible"; fire(doc, "visibilitychange"); },
    // a click on a link (capture listeners first, then the bubbling ones) → true when the page stopped it
    click(href, attrs, init) {
      attrs = attrs || {};
      const mine = ["data-rec-go", "data-copy", "data-share"].some((k) => k in attrs);
      const a = {
        href: new URL(href, HERE).href,
        getAttribute: (n) => (n in attrs ? attrs[n] : n === "href" ? href : null),
        hasAttribute: (n) => n in attrs,
        closest: (sel) => (sel === "a[href]" ? a : sel === "[data-rec-go]" ? ("data-rec-go" in attrs ? a : null)
          : sel === 'a[href="#record"]' ? (href === "#record" ? a : null) : /data-copy/.test(sel) ? (mine ? a : null) : null),
      };
      const ev = Object.assign({ type: "click", target: { closest: (s) => a.closest(s) }, button: 0, defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; } }, init || {});
      for (const l of (doc.click || []).filter((x) => x.cap)) l.fn(ev);
      for (const l of (doc.click || []).filter((x) => !x.cap)) l.fn(ev);
      return ev.defaultPrevented;
    },
    // the browser's own question as the page would go (beforeunload) → true when the page asks it
    unload() {
      const ev = { type: "beforeunload", returnValue: undefined, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
      for (const l of (win.beforeunload || []).slice()) l.fn(ev);
      return ev.defaultPrevented;
    },
    // the visitor goes to another page: pagehide, then this page is gone (its timers, transactions, locks)
    leave() { fire(win, "pagehide", { type: "pagehide", persisted: false }); tab.close(); },
    // the page is killed (iOS ended the tab): no event at all
    crash() { tab.close(); },
  };
}

function device(W) {
  const d = W.idb.database(DB);
  if (!d) return null;
  const out = { version: d.version, stores: d.storeNames() };
  for (const n of out.stores) out[n] = d.store(n).all();
  return out;
}
const rows = (W, id, kind) => ((device(W) || {}).sound || []).filter((r) => r.id === id && (!kind || r.kind === kind));
const row = (W, id) => ((device(W) || {}).takes || []).find((r) => r.id === id) || null;
const total = (list) => list.reduce((n, r) => n + r.buf.byteLength, 0);
const tag = (v) => Object.prototype.toString.call(v);
const view = (C) => C.takes.map((t) => ({ id: t.id, saved: t.saved, saving: t.saving, failed: t.failed, damaged: t.damaged, v: t.v,
  src: t.src, url: !!t.url, mp3Size: t.mp3Size, samples: t.samples, name: t.name, starred: t.starred }));
const meta = (W, id, sec, extra) => Object.assign({ id, pub: "gv", n: 1, name: "", created: W.now, rate: 44100, samples: Math.round(sec * 44100),
  peak: 0.5, bins: [], src: "file", noise: false, starred: false, gaps: false, from: 0 }, extra || {});
const sound = (sec, mp3n) => ({ pcm: new Int16Array(Math.round(sec * 44100)).fill(1000), mp3: mp3n ? new Uint8Array(mp3n).fill(0xfb) : null });
// every write the pages made: none ever held a Blob
const blobPuts = (W) => W.idb.log.filter((e) => e.blob).length;
const health = (W) => ({ errors: W.errors.map((e) => String((e && e.stack) || e)), unhandled });
"""


class Store(unittest.TestCase):
    """A test runs one Node script: HARNESS, then its own lines; out({...}) hands the result back."""

    def run_pages(self, js: str) -> dict:
        r = run_js(self, HARNESS + js, data={"cfg": config_like_the_partial("en")}, needs_modules=False, timeout=170)
        h = r.get("health") or {}
        self.assertEqual(h.get("errors"), [], "the page's code threw (in a timer or an event handler)")
        self.assertEqual(h.get("unhandled"), [], "a promise was rejected and nothing handled it")
        return r


class Bytes(Store):
    def test_safari_private_refuses_blobs_and_the_take_is_still_saved(self):
        # WebKit's private window: every value holding a Blob is refused (UnknownError "Error preparing Blob/File data");
        # getDirectory() rejects there, so the page knows it is a private window (kept until the window closes)
        r = self.run_pages(r"""
          const W = createWorld(); W.idb.refuseBlobs = true; W.storage.private = true;
          const P = page(W, { ua: UA.iphone });
          await W.until(() => P.C.loaded); await W.idle();
          const first = { kept: P.C.kept, priv: P.C.priv, note: P.C.storeNote(), line: P.C.keptLine() };
          const ok = await W.wait(P.C.add(meta(W, "tpriv1", 3), sound(3, 48000)));
          const after = { ok, view: view(P.C), note: P.C.storeNote(), hold: P.classes.has("cm-rec-hold"), guard: P.leaveGuard() };
          P.leave();
          const P2 = page(W, { ua: UA.iphone });
          await W.until(() => P2.C.loaded); await W.idle();
          // (the pretend store does refuse a Blob, as Safari's private one does)
          const probe = await W.wait(new Promise((res) => {
            const q = P2.tab.indexedDB.open(DB, 2);
            q.onsuccess = () => { const tx = q.result.transaction("sound", "readwrite"); tx.objectStore("sound").put({ k: "probe", buf: new Blob(["x"]) });
              tx.onabort = () => res(tx.error.name); tx.oncomplete = () => res("stored"); };
          }));
          const d = device(W);
          out({ first, after, next: view(P2.C), stores: d.stores, version: d.version, probe,
            sound: d.sound.map((x) => ({ k: x.k, kind: x.kind, seq: x.seq, type: tag(x.buf), bytes: x.buf.byteLength })),
            takes: d.takes.map((x) => ({ id: x.id, v: x.v, draft: x.draft, mp3: x.mp3, size: x.size })),
            pageBlobPuts: W.idb.log.filter((e) => e.blob && e.key !== "probe").length,
            pageFailed: W.idb.log.filter((e) => !e.ok && e.key !== "probe").length, health: health(W) });""")
        # ("This device" says the same as the box: kept until the private tab is closed — not the 7-day rule, r10 A13)
        self.assertEqual(r["first"], {"kept": True, "priv": True, "note": "private", "line": "private"})
        self.assertTrue(r["after"]["ok"])                              # saved on the device, in a private window
        self.assertEqual(r["after"]["view"][0]["saved"], True)
        self.assertEqual(r["after"]["view"][0]["failed"], False)
        self.assertEqual((r["after"]["note"], r["after"]["hold"], r["after"]["guard"]), ("private", False, 0))
        self.assertEqual(r["probe"], "UnknownError")
        # the next page (a link away and back) lists it, saved, with its sound
        self.assertEqual([(t["id"], t["saved"], t["url"], t["mp3Size"]) for t in r["next"]], [("tpriv1", True, True, 48000)])
        self.assertEqual((r["version"], r["stores"]), (2, ["sound", "takes"]))
        self.assertEqual(r["sound"], [
            {"k": "tpriv1:mp3:000000", "kind": "mp3", "seq": 0, "type": "[object ArrayBuffer]", "bytes": 48000},
            {"k": "tpriv1:pcm:000000", "kind": "pcm", "seq": 0, "type": "[object ArrayBuffer]", "bytes": 3 * 44100 * 2}])
        self.assertEqual(r["takes"], [{"id": "tpriv1", "v": 2, "draft": False, "mp3": True, "size": 3 * 44100 * 2 + 48000}])
        self.assertEqual(r["pageBlobPuts"], 0)                        # no value the recorder wrote held a Blob
        self.assertEqual(r["pageFailed"], 0)


# A recording from Start to its draft on the device (RECORD), and what the stored PCM says (PCM_CHECK: every block where it
# belongs — sample j × 4096 is block j's level — and the rows numbered 0, 1, 2… with no gap and none twice)
RECORD = r"""
  const kit = audioKit(), enc = encoderKit();
  const P = page(W, { audio: kit, encoder: enc });
  await W.until(() => P.C.loaded); await W.idle();
  P.C.open("record");
  await W.until(() => P.C.state === "recording", 10000);
  await W.until(() => ((device(W) || {}).takes || []).some((x) => x.draft), 2000);
  const id = device(W).takes.find((x) => x.draft).id;
"""
PCM_CHECK = r"""
  const pcmCheck = (W, id, blocks) => {
    const list = rows(W, id, "pcm"), F32 = vm.runInContext("Float32Array", P.ctx);
    const all = new Int16Array(total(list) / 2);
    let o = 0;
    for (const x of list) { all.set(new Int16Array(x.buf), o); o += x.buf.byteLength / 2; }
    let misplaced = 0;
    for (let j = 0; j < blocks; j++) {
      const want = P.R.toInt16(new F32([level(j)]))[0];
      if (all[j * 4096] !== want || all[j * 4096 + 4095] !== want) misplaced++;
    }
    return { seqs: list.map((x) => x.seq), bytes: all.length * 2, misplaced, keys: list.map((x) => x.k) };
  };
"""


class Recording(Store):
    def test_a_take_is_on_the_device_while_it_is_made(self):
        # D2: the draft at Start, the sound every LIMITS.flushEvery (3) seconds, Stop's one final write — in a store that
        # refuses Blobs (Safari's private window), with an MP3 big enough to need two rows
        r = self.run_pages(r"""
          const W = createWorld(); W.idb.refuseBlobs = true;""" + RECORD + PCM_CHECK + r"""
          const d0 = row(W, id);
          const atStart = { state: P.C.state, draft: [d0.v, d0.draft, d0.mp3, d0.samples, d0.size], sound: rows(W, id).length,
            lock: W.locks.names().includes(LOCK + id), cls: [...P.classes].sort(), atRisk: P.C.atRisk() };
          await feed(P, kit, 2);
          const at2 = rows(W, id, "pcm").map((x) => x.seq);
          await feed(P, kit, 1.5);
          const at3 = { seqs: rows(W, id, "pcm").map((x) => x.seq), samples: row(W, id).samples, bytes: total(rows(W, id, "pcm")), draft: row(W, id).draft };
          await feed(P, kit, 3.2);
          const at6 = { seqs: rows(W, id, "pcm").map((x) => x.seq), samples: row(W, id).samples };
          await feed(P, kit, 3.3);
          const blocks = kit.i;
          P.C.stop(true);
          const saving = P.C.state;
          await W.until(() => P.C.state === "idle" && P.C.takes.length > 0 && P.C.takes[0].saved, 30000);
          await W.idle();
          const t = P.C.takes[0], fin = row(W, id);
          const said = P.C.t("a_saved", { name: P.C.name(t), time: P.R.spoken(P.R.duration(t), P.C.s.words) });
          out({ atStart, at2, at3, at6, blocks, saving, take: view(P.C)[0], mp3Size: t.mp3Size,
            fin: { v: fin.v, draft: fin.draft, mp3: fin.mp3, samples: fin.samples, size: fin.size, src: fin.src },
            pcm: pcmCheck(W, id, blocks), mp3Rows: rows(W, id, "mp3").map((x) => [x.seq, x.buf.byteLength]),
            takesRows: device(W).takes.length, lockAfter: W.locks.names().includes(LOCK + id), clsAfter: [...P.classes],
            guard: P.leaveGuard(), saidSaved: P.said.includes(said), persist: W.storage.calls.persist, blobPuts: blobPuts(W),
            failed: W.idb.log.filter((e) => !e.ok).length, health: health(W) });""")
        self.assertEqual(r["atStart"], {"state": "recording", "draft": [2, True, False, 0, 0], "sound": 0, "lock": True,
                                        "cls": ["cm-rec-hold", "cm-rec-on"], "atRisk": True})
        self.assertEqual(r["at2"], [])                                  # nothing to write before 3 seconds
        # at 3.072 s (block 36 of 4096 samples at 48 kHz): row 0, and the draft says how much is on the device
        self.assertEqual(r["at3"], {"seqs": [0], "samples": 36 * 4096, "bytes": 36 * 4096 * 2, "draft": True})
        self.assertEqual(r["at6"], {"seqs": [0, 1], "samples": 72 * 4096})
        self.assertEqual(r["saving"], "saving")
        n = r["blocks"]
        self.assertEqual(n, 118)
        self.assertEqual(r["fin"], {"v": 2, "draft": False, "mp3": True, "samples": n * 4096, "size": n * 4096 * 2 + r["mp3Size"], "src": "mic"})
        # the PCM: every block in its place, rows numbered in order with none missing or twice, bytes = samples × 2
        self.assertEqual(r["pcm"]["seqs"], list(range(len(r["pcm"]["seqs"]))))
        self.assertEqual(r["pcm"]["bytes"], n * 4096 * 2)
        self.assertEqual(r["pcm"]["misplaced"], 0)
        # the MP3: rows of at most 1 MiB that add up to it
        self.assertEqual(r["mp3Size"], n * 4096 * 3 + 417)
        self.assertEqual([seq for seq, _ in r["mp3Rows"]], [0, 1])
        self.assertTrue(all(b <= 1048576 for _, b in r["mp3Rows"]))
        self.assertEqual(sum(b for _, b in r["mp3Rows"]), r["mp3Size"])
        self.assertEqual(r["takesRows"], 1)                             # the draft became the take: no second record
        self.assertEqual((r["take"]["saved"], r["take"]["failed"], r["take"]["url"]), (True, False, True))
        self.assertFalse(r["lockAfter"])                                # its lock goes once it is saved
        self.assertEqual((r["clsAfter"], r["guard"]), ([], 0))
        self.assertTrue(r["saidSaved"])
        self.assertEqual(r["persist"], 1)                               # Stop and save asked to keep the takes
        self.assertEqual((r["blobPuts"], r["failed"]), (0, 0))

    def test_discard_drops_the_draft_and_its_sound(self):
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 4);
          const before = { draft: !!row(W, id), pcm: rows(W, id, "pcm").length };
          P.C.askDiscard(); P.C.stop(false);
          await W.until(() => P.C.state === "idle"); await W.idle();
          out({ before, after: { take: row(W, id), sound: rows(W, id).length, list: P.C.takes.length },
            lock: W.locks.names().includes(LOCK + id), cls: [...P.classes], guard: P.leaveGuard(),
            discarded: P.said.includes(P.C.s.a_discarded), persist: W.storage.calls.persist, health: health(W) });""")
        self.assertEqual(r["before"], {"draft": True, "pcm": 1})
        self.assertEqual(r["after"], {"take": None, "sound": 0, "list": 0})
        self.assertFalse(r["lock"])
        self.assertEqual((r["cls"], r["guard"]), ([], 0))
        self.assertTrue(r["discarded"])
        self.assertEqual(r["persist"], 0)                               # nothing kept: nothing asked

    def test_a_failed_write_is_done_again_with_the_same_row_number(self):
        # the write at 6 s fails three times (attempt's three tries): the place does not move on; the next write, 6 s of
        # sound later (it backs off), puts row 1 again with more sound in it — no row missing, none twice
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + PCM_CHECK + r"""
          await feed(P, kit, 3.5);
          const f = W.idb.fail({ op: "put", store: "sound", name: "UnknownError", times: 3 });
          await feed(P, kit, 4);
          const during = { hits: f.hits, seqs: rows(W, id, "pcm").map((x) => x.seq), samples: row(W, id).samples };
          await feed(P, kit, 5.5);
          const blocks = kit.i;
          P.C.stop(true);
          await W.until(() => P.C.state === "idle" && P.C.takes.length > 0 && P.C.takes[0].saved, 30000);
          const puts = W.idb.log.filter((e) => e.store === "sound" && e.op === "put" && e.key.indexOf(":pcm:") > 0);
          out({ during, blocks, pcm: pcmCheck(W, id, blocks), samples: row(W, id).samples,
            failedKeys: puts.filter((e) => !e.ok).map((e) => e.key.slice(-6)),
            committedKeys: puts.filter((e) => e.committed).map((e) => e.key.slice(-6)), health: health(W) });""")
        self.assertEqual(r["during"], {"hits": 3, "seqs": [0], "samples": 36 * 4096})
        self.assertEqual(r["failedKeys"], ["000001"] * 3)
        committed = r["committedKeys"]
        self.assertEqual(committed, sorted(set(committed)))              # each row written once, in order
        self.assertEqual(committed[:2], ["000000", "000001"])
        self.assertEqual(r["pcm"]["seqs"], list(range(len(r["pcm"]["seqs"]))))
        self.assertEqual(r["pcm"]["bytes"], r["blocks"] * 4096 * 2)
        self.assertEqual(r["samples"], r["blocks"] * 4096)
        self.assertEqual(r["pcm"]["misplaced"], 0)

    def test_stop_during_a_write(self):
        # every request takes 300 ms: Stop comes while the write at 3 s is still on its way; what it wrote is not written
        # again and nothing after it is missing
        r = self.run_pages(r"""
          const W = createWorld(); W.idb.latency = 300;""" + RECORD + PCM_CHECK + r"""
          const begun = () => W.idb.log.some((e) => e.key === P.R.soundKey(id, "pcm", 0));
          while (!begun()) await feed(P, kit, 0.09);
          const inFlight = W.idb.log.find((e) => e.key === P.R.soundKey(id, "pcm", 0)).ok;
          const blocks = kit.i;
          P.C.stop(true);
          await W.until(() => P.C.state === "idle" && P.C.takes.length > 0 && P.C.takes[0].saved, 60000);
          const committed = W.idb.log.filter((e) => e.committed && e.store === "sound").map((e) => e.key);
          out({ inFlight, blocks, pcm: pcmCheck(W, id, blocks), samples: row(W, id).samples, draft: row(W, id).draft,
            twice: committed.filter((k, i) => committed.indexOf(k) !== i), health: health(W) });""")
        self.assertIsNone(r["inFlight"])                                 # (the write had not answered yet)
        self.assertEqual(r["pcm"]["seqs"], list(range(len(r["pcm"]["seqs"]))))
        self.assertEqual(r["pcm"]["bytes"], r["blocks"] * 4096 * 2)
        self.assertEqual((r["samples"], r["draft"]), (r["blocks"] * 4096, False))
        self.assertEqual(r["pcm"]["misplaced"], 0)
        self.assertEqual(r["twice"], [])

    def test_a_page_that_dies_mid_take_leaves_a_draft_the_next_page_recovers(self):
        # iOS ends the tab 5 s into a take (no pagehide): what the 3-second write put on the device comes back
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 5);
          P.crash();
          const P2 = page(W);
          await W.until(() => P2.C.loaded); await W.idle();
          const t = P2.C.takes[0], fin = row(W, id);
          out({ list: view(P2.C), notice: P2.C.notice, said: P2.said.includes(P2.C.s.n_recovered),
            fin: { draft: fin.draft, v: fin.v, samples: fin.samples, src: fin.src }, bytes: total(rows(W, id, "pcm")),
            note: P2.C.storeNote(), lock: W.locks.names().includes(LOCK + id), health: health(W) });""")
        self.assertEqual([(t["id"][:1], t["saved"], t["src"], t["samples"], t["url"]) for t in r["list"]], [("t", True, "recovered", 36 * 4096, True)])
        self.assertEqual(r["notice"], "recovered")
        self.assertTrue(r["said"])
        self.assertEqual(r["fin"], {"draft": False, "v": 2, "samples": 36 * 4096, "src": "recovered"})
        self.assertEqual(r["bytes"], 36 * 4096 * 2)
        self.assertEqual((r["note"], r["lock"]), ("", False))

    def test_a_final_write_that_fails_says_so_and_leaves_the_draft(self):
        # the final record can't be written: the take stays in the page, "not saved yet" (announced, the box, leaving asks),
        # keeps its lock; its draft and all its sound stay on the device — a page that dies now loses nothing
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.draft === false, name: "UnknownError" });
          await feed(P, kit, 5);
          const blocks = kit.i;
          P.C.stop(true);
          await W.until(() => P.C.state === "idle", 30000); await W.idle();
          const t = P.C.takes[0], d = row(W, id);
          const page1 = { take: view(P.C)[0], note: P.C.storeNote(), lastErr: P.C.lastErr, kept: P.C.kept,
            unsaved: P.said.includes(P.C.t("a_unsaved", { name: P.C.name(t) })),
            saved: P.said.some((m) => m === P.C.t("a_saved", { name: P.C.name(t), time: P.R.spoken(P.R.duration(t), P.C.s.words) })),
            hold: P.classes.has("cm-rec-hold"), guard: P.leaveGuard(), lock: W.locks.names().includes(LOCK + id),
            draft: { draft: d.draft, samples: d.samples }, bytes: total(rows(W, id, "pcm")) };
          P.crash(); f.off();
          const P2 = page(W);
          await W.until(() => P2.C.loaded); await W.idle();
          out({ blocks, page1, page2: view(P2.C), fin: row(W, id).draft, health: health(W) });""")
        p1, n = r["page1"], r["blocks"]
        self.assertEqual((p1["take"]["saved"], p1["take"]["failed"], p1["take"]["saving"]), (False, True, False))
        self.assertEqual((p1["note"], p1["lastErr"], p1["kept"]), ("unsaved", "UnknownError", True))
        self.assertTrue(p1["unsaved"])
        self.assertFalse(p1["saved"])                                   # a_saved only when it is really saved
        self.assertEqual((p1["hold"], p1["guard"], p1["lock"]), (True, 1, True))
        self.assertEqual(p1["draft"], {"draft": True, "samples": n * 4096})
        self.assertEqual(p1["bytes"], n * 4096 * 2)
        self.assertEqual([(t["saved"], t["src"], t["samples"]) for t in r["page2"]], [(True, "recovered", n * 4096)])
        self.assertFalse(r["fin"])


# a page with the device's takes listed (and nothing left running)
LOADED = r"""
  const P = page(W);
  await W.until(() => P.C.loaded); await W.idle();
"""


class NoLatch(Store):
    def test_one_failed_write_leaves_that_take_unsaved_and_later_takes_are_saved(self):
        # D4: no latch — take A's final record can't be written; A is "not saved yet" and tried again; take B, made after
        # it, is saved as usual; once writes work again A is saved by the retry every LIMITS.retryEvery (20) seconds
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === "tfa" && i.value.draft === false, name: "UnknownError" });
          const a = await W.wait(P.C.add(meta(W, "tfa", 2), sound(2)));
          await W.idle();
          const A = { ok: a, take: view(P.C)[0], note: P.C.storeNote(), kept: P.C.kept, hold: P.classes.has("cm-rec-hold"), guard: P.leaveGuard(),
            draft: row(W, "tfa").draft, lock: W.locks.names().includes(LOCK + "tfa"), tries: f.seen };
          const b = await W.wait(P.C.add(meta(W, "tfb", 2, { n: 2, created: W.now + 1 }), sound(2)));
          await W.idle();
          const B = { ok: b, a: P.C.find("tfa").saved, b: P.C.find("tfb").saved, rowB: row(W, "tfb").draft, note: P.C.storeNote(), tries: f.seen };
          f.off();
          const t0 = W.now;
          const retried = await W.until(() => P.C.find("tfa").saved, 21000);
          await W.idle();
          const timers = W._timers.filter((t) => t.every && t.owner === P.tab).length;
          out({ A, B, retried, waited: W.now - t0, after: { list: view(P.C), note: P.C.storeNote(), hold: P.classes.has("cm-rec-hold"),
            guard: P.leaveGuard(), rowA: row(W, "tfa").draft, lock: W.locks.names().includes(LOCK + "tfa"), timers }, health: health(W) });""")
        A, B, after = r["A"], r["B"], r["after"]
        self.assertFalse(A["ok"])
        self.assertEqual((A["take"]["saved"], A["take"]["failed"], A["take"]["saving"]), (False, True, False))
        self.assertEqual((A["note"], A["kept"]), ("unsaved", True))     # kept stays true: nothing is latched
        self.assertEqual((A["hold"], A["guard"]), (True, 1))            # leaving asks first; pwa.js holds its Reload
        self.assertTrue(A["draft"])                                     # its draft stays for recovery
        self.assertTrue(A["lock"])                                      # and its lock (no other tab adopts it)
        self.assertEqual(A["tries"], 3)                                 # attempt(): at once, after 250 ms, after 1 s
        self.assertTrue(B["ok"])
        self.assertEqual((B["a"], B["b"], B["rowB"]), (False, True, False))
        self.assertEqual(B["note"], "unsaved")
        self.assertGreater(B["tries"], A["tries"])                      # B saved → A tried again at once
        self.assertTrue(r["retried"])
        self.assertLessEqual(r["waited"], 20000)
        self.assertEqual([(t["id"], t["saved"], t["failed"]) for t in after["list"]], [("tfb", True, False), ("tfa", True, False)])
        self.assertEqual((after["note"], after["hold"], after["guard"], after["rowA"], after["lock"]), ("", False, 0, False, False))
        self.assertEqual(after["timers"], 0)                            # the retry timer stops once nothing waits

    def test_a_full_device_says_full_and_deleting_a_take_saves_the_waiting_one(self):
        # D7: QuotaExceededError (reported at commit, as browsers do) → "full", sizes shown, not retried in a loop; the
        # visitor deletes a take → the waiting one is saved at once
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tq1", 20), sound(20)));
          W.idb.quota = W.idb.bytes() + 100000;
          const ok = await W.wait(P.C.add(meta(W, "tq2", 20, { n: 2, created: W.now + 1 }), sound(20)));
          await W.idle();
          // (the write the full device refused: tq2's PCM — all of it goes before the final record, r10 A6)
          const finals = () => W.idb.log.filter((e) => e.store === "sound" && e.key === "tq2:pcm:000000").length;
          const mid = { ok, take: view(P.C).find((t) => t.id === "tq2"), note: P.C.storeNote(), full: P.C.full, sizes: P.C.showSizes(),
            lastErr: P.C.lastErr, draft: !!row(W, "tq2") && row(W, "tq2").draft, finals: finals(), size: P.C.takeSize(P.C.find("tq2")) };
          P.C.remove(P.C.find("tq1"));
          const saved = await W.until(() => P.C.find("tq2").saved, 5000);
          await W.idle();
          out({ mid, saved, after: { note: P.C.storeNote(), sizes: P.C.showSizes(), tq1: [row(W, "tq1"), rows(W, "tq1").length],
            tq2: row(W, "tq2").draft, list: view(P.C).map((t) => t.id), fits: W.idb.bytes() <= W.idb.quota,
            deleted: P.said.includes(P.C.t("a_deleted", { name: "Take 1" })) }, health: health(W) });""")
        mid, after = r["mid"], r["after"]
        self.assertFalse(mid["ok"])
        self.assertEqual((mid["take"]["saved"], mid["take"]["failed"]), (False, True))
        self.assertEqual((mid["note"], mid["full"], mid["sizes"], mid["lastErr"]), ("full", True, True, "QuotaExceededError"))
        self.assertTrue(mid["draft"])
        self.assertEqual(mid["finals"], 1)                              # a full device is not tried three times
        self.assertEqual(mid["size"], 20 * 44100 * 2)
        self.assertTrue(r["saved"])
        self.assertEqual((after["note"], after["sizes"]), ("", False))
        self.assertEqual(after["tq1"], [None, 0])
        self.assertFalse(after["tq2"])
        self.assertEqual(after["list"], ["tq2"])
        self.assertTrue(after["fits"])
        self.assertTrue(after["deleted"])

    def test_a_write_that_throws_halfway_leaves_nothing_half_written(self):
        # run(): an exception while the requests are being made (put() throws DataCloneError) aborts the transaction —
        # the rows already requested in it must not reach the device on their own (audit L11)
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", sync: true, name: "DataCloneError", match: (i) => !!i.value && i.value.draft === false });
          const ok = await W.wait(P.C.add(meta(W, "th1", 2), sound(2, 20000)));
          await W.idle();
          const mid = { ok, sound: rows(W, "th1").map((x) => x.k), draft: row(W, "th1").draft, note: P.C.storeNote(), hits: f.hits };
          f.off();
          P.C.retry();
          await W.until(() => P.C.find("th1").saved, 5000);
          out({ mid, after: { sound: rows(W, "th1").map((x) => x.k), draft: row(W, "th1").draft, note: P.C.storeNote() }, health: health(W) });""")
        self.assertFalse(r["mid"]["ok"])
        # no orphan rows from the aborted write (its MP3 row): the PCM is there from the write before it, with the draft
        # (all of a take's PCM goes before its final write, r10 A6)
        self.assertEqual(r["mid"]["sound"], ["th1:pcm:000000"])
        self.assertTrue(r["mid"]["draft"])
        self.assertEqual(r["mid"]["note"], "unsaved")
        self.assertEqual(r["mid"]["hits"], 3)
        self.assertEqual(r["after"], {"sound": ["th1:mp3:000000", "th1:pcm:000000"], "draft": False, "note": ""})

    def test_short_of_storage_the_visitor_is_told_before_a_take(self):
        # D7: before Start, navigator.storage.estimate(): less room than a 10-minute take needs (R.takeBytes(600, 48000))
        # → "low" with the free space — nothing is stopped; deleting a take clears it
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tl1", 2), sound(2)));
          W.storage.quota = W.idb.bytes() + 10 * 1048576;
          P.C.roomFor(P.R.takeBytes(P.R.LIMITS.hardStop, 48000));
          await W.idle();
          const low = { notice: P.C.notice, free: P.C.lowFree, sizes: P.C.showSizes(), said: P.said.includes(P.C.t("n_low", { free: P.C.size(10 * 1048576) })) };
          P.C.remove(P.C.find("tl1"));
          await W.idle();
          out({ low, need: P.R.takeBytes(600, 48000), after: P.C.notice, health: health(W) });""")
        self.assertEqual(r["need"], 67200000)
        self.assertEqual(r["low"], {"notice": "low", "free": 10 * 1048576, "sizes": True, "said": True})
        self.assertEqual(r["after"], "")


# drafts a closed page left (DRAFTS: draft(id, {at, rate}) and pcmRow(id, seq, samples) put rows on the device as
# flushSound writes them)
DRAFTS = r"""
  const store = (n) => W.idb.database(DB).store(n);
  const draft = (id, o) => store("takes").put(Object.assign(P.R.clean({ id, pub: "gv", n: 3, created: W.now - 6 * 60e3, rate: 48000, samples: 0 }),
    { v: 2, draft: true, mp3: false, at: W.now - 5 * 60e3 }, o || {}));
  const pcmRow = (id, seq, samples) => store("sound").put({ k: P.R.soundKey(id, "pcm", seq), id, kind: "pcm", seq, buf: new Int16Array(samples).fill(500).buffer });
"""


class Listing(Store):
    def test_one_unreadable_take_is_shown_as_damaged_and_nothing_is_deleted(self):
        # D9: each take is read on its own; one whose sound can't be read (WebKitBlobResource, a lost file) is listed as
        # damaged — never deleted, never hiding the others, never turning the storage off; Delete still works on it
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          for (const [id, n] of [["td1", 1], ["td2", 2], ["td3", 3]]) await W.wait(P.C.add(meta(W, id, 1, { n, created: W.now + n }), sound(1, 4000)));
          P.leave();
          const keys = () => { const d = device(W); return [d.takes.map((x) => x.id), d.sound.map((x) => x.k)]; };
          const before = keys();
          W.idb.fail({ op: "read", store: "sound", key: (k) => String(k).startsWith("td2:"), name: "NotReadableError" });
          const P2 = page(W, { label: "page 2" });
          await W.until(() => P2.C.loaded); await W.idle();
          const listed = view(P2.C), mid = keys();
          const changes = W.idb.log.filter((e) => e.client === "page 2").map((e) => e.op + " " + e.key);
          const state = { note: P2.C.storeNote(), kept: P2.C.kept, reload: P2.C.reload, atRisk: P2.C.atRisk(), hold: P2.classes.has("cm-rec-hold") };
          P2.C.remove(P2.C.find("td2"));
          await W.idle();
          out({ before, mid, listed, changes, state, after: keys(), deleted: P2.said.includes(P2.C.t("a_deleted", { name: "Take 2" })), health: health(W) });""")
        self.assertEqual(r["mid"], r["before"])                         # nothing deleted
        self.assertEqual(r["changes"], [])                              # nothing written at all by listing
        self.assertEqual([(t["id"], t["saved"], t["damaged"], t["url"]) for t in r["listed"]],
                         [("td3", True, False, True), ("td2", True, True, False), ("td1", True, False, True)])
        self.assertEqual(r["state"], {"note": "", "kept": True, "reload": False, "atRisk": False, "hold": False})
        self.assertEqual(r["after"], [["td1", "td3"], ["td1:mp3:000000", "td1:pcm:000000", "td3:mp3:000000", "td3:pcm:000000"]])
        self.assertTrue(r["deleted"])

    def test_a_take_40_days_old_is_still_listed(self):
        # D6: nothing is deleted for its age (the first recorder removed takes after 30 days)
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "told", 3), sound(3, 6000)));
          P.leave();
          W.now += 40 * DAY;
          const P2 = page(W, { label: "40 days on" });
          await W.until(() => P2.C.loaded); await W.idle();
          out({ list: view(P2.C), notice: P2.C.notice, row: !!row(W, "told"), sound: rows(W, "told").length,
            changes: W.idb.log.filter((e) => e.client === "40 days on").length, health: health(W) });""")
        self.assertEqual([(t["id"], t["saved"], t["url"]) for t in r["list"]], [("told", True, True)])
        self.assertEqual((r["notice"], r["row"], r["sound"], r["changes"]), ("", True, 2, 0))

    def test_drafts_left_by_closed_pages(self):
        # D9: a draft no page is making comes back as "Recovered recording" (its stale MP3 rows dropped); one under a
        # second, or an empty one written long ago, goes; one another tab is making (its Web Lock) is left alone, and so
        # is an empty one written moments ago (a take just begun)
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + DRAFTS + r"""
          draft("tdr1"); pcmRow("tdr1", 0, 48000); pcmRow("tdr1", 1, 48000);
          store("sound").put({ k: P.R.soundKey("tdr1", "mp3", 0), id: "tdr1", kind: "mp3", seq: 0, buf: new ArrayBuffer(99) });
          draft("tdr2"); pcmRow("tdr2", 0, 24000);
          draft("tdr3"); pcmRow("tdr3", 0, 96000); W.locks.hold(LOCK + "tdr3");
          draft("tdr4", { at: W.now - 10e3 });
          draft("tdr5");
          P.leave();
          const P2 = page(W);
          await W.until(() => P2.C.loaded); await W.idle();
          const r1 = row(W, "tdr1");
          out({ list: view(P2.C), notice: P2.C.notice, said: P2.said.includes(P2.C.s.n_recovered),
            tdr1: { draft: r1.draft, src: r1.src, samples: r1.samples, sound: rows(W, "tdr1").map((x) => x.k) },
            tdr2: [row(W, "tdr2"), rows(W, "tdr2").length], tdr3: [row(W, "tdr3").draft, rows(W, "tdr3").length],
            tdr4: !!row(W, "tdr4"), tdr5: row(W, "tdr5"), locks: W.locks.names(), health: health(W) });""")
        self.assertEqual([(t["id"], t["saved"], t["src"], t["samples"]) for t in r["list"]], [("tdr1", True, "recovered", 96000)])
        self.assertEqual((r["notice"], r["said"]), ("recovered", True))
        self.assertEqual(r["tdr1"], {"draft": False, "src": "recovered", "samples": 96000, "sound": ["tdr1:pcm:000000", "tdr1:pcm:000001"]})
        self.assertEqual(r["tdr2"], [None, 0])                          # under a second: not a recording
        self.assertEqual(r["tdr3"], [True, 1])                          # another tab is making it
        self.assertTrue(r["tdr4"])                                      # just begun somewhere
        self.assertIsNone(r["tdr5"])                                    # empty and old
        self.assertEqual(r["locks"], ["gvlv-rec:tdr3"])                 # this page let go of the drafts it looked at

    def test_without_web_locks_a_recent_draft_is_left_alone(self):
        # iOS before 15.4: no Web Locks — a draft written in the last LIMITS.partFresh (120) seconds may be a take another
        # tab is recording: left; an older one is recovered
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + DRAFTS + r"""
          draft("tnl1", { at: W.now - 30e3 }); pcmRow("tnl1", 0, 96000);
          draft("tnl2"); pcmRow("tnl2", 0, 96000);
          P.leave();
          const P2 = page(W, { noLocks: true });
          await W.until(() => P2.C.loaded); await W.idle();
          out({ list: view(P2.C).map((t) => [t.id, t.saved, t.src]), tnl1: row(W, "tnl1").draft, tnl2: row(W, "tnl2").draft, health: health(W) });""")
        self.assertEqual(r["list"], [["tnl2", True, "recovered"]])
        self.assertEqual((r["tnl1"], r["tnl2"]), (True, False))


# the first recorder's database (v1: Blob rows in takes / pcm / mp3 / parts)
V1 = r"""
  const v1 = W.idb.create(DB, 1, { takes: { keyPath: "id" }, pcm: { keyPath: "id" }, mp3: { keyPath: "id" }, parts: { keyPath: "k" } });
  const old = (id, o) => Object.assign({ id, pub: "lv", n: 1, name: "", created: W.now - 90 * DAY, rate: 48000, samples: 96000, peak: 0.4,
    bins: [1, 2, 3], src: "mic", noise: false, starred: false, gaps: false, from: 0 }, o || {});
  const part = (id, seq, o) => Object.assign({ k: id + ":" + String(seq).padStart(6, "0"), id, seq, pub: "gv", n: 3, created: W.now - DAY, rate: 48000,
    noise: false, at: W.now - DAY, blob: new Blob([new Int16Array(48000).fill(100)]) }, o || {});
"""


class Migration(Store):
    def test_v1_blob_takes_are_listed_and_moved_to_bytes(self):
        # D10: the first recorder's takes are listed from their Blobs, then written as sound rows with a v2 record in the
        # transaction that empties their old rows; its crash pieces (parts) become a recovered take; the old stores stay
        # (never deleted by a version change) but end up empty
        r = self.run_pages(r"""
          const W = createWorld();""" + V1 + r"""
          v1.store("takes").put(old("tv1", { name: "Mi toma", starred: true }));
          v1.store("pcm").put({ id: "tv1", blob: new Blob([new Int16Array(96000).fill(300)]) });
          v1.store("mp3").put({ id: "tv1", blob: new Blob([new Uint8Array(32000).fill(0xfb)]) });
          v1.store("takes").put(old("tv2", { n: 2 }));
          v1.store("pcm").put({ id: "tv2", blob: new Blob([new Int16Array(96000).fill(200)]) });
          v1.store("parts").put(part("tv3", 0)); v1.store("parts").put(part("tv3", 1));
          const P = page(W);
          await W.until(() => P.C.loaded); await W.idle();
          const d = device(W);
          out({ version: d.version, stores: d.stores, list: view(P.C).map((t) => [t.id, t.saved, t.v, t.src, t.name, t.starred, t.mp3Size, t.damaged]),
            takes: d.takes.map((x) => [x.id, x.v, x.draft, x.mp3, x.size, x.name, x.starred, x.samples]),
            sound: d.sound.map((x) => [x.k, x.buf.byteLength, tag(x.buf)]), legacy: [d.pcm.length, d.mp3.length, d.parts.length],
            first: new Int16Array(d.sound.find((x) => x.k === "tv1:pcm:000000").buf)[0], notice: P.C.notice, blobPuts: blobPuts(W), health: health(W) });""")
        self.assertEqual((r["version"], r["stores"]), (2, ["mp3", "parts", "pcm", "sound", "takes"]))
        self.assertEqual(sorted(r["list"]), [["tv1", True, 2, "mic", "Mi toma", True, 32000, False], ["tv2", True, 2, "mic", "", False, 0, False],
                                             ["tv3", True, 2, "recovered", "", False, 0, False]])
        self.assertEqual(sorted(r["takes"]), [["tv1", 2, False, True, 192000 + 32000, "Mi toma", True, 96000],
                                              ["tv2", 2, False, False, 192000, "", False, 96000],
                                              ["tv3", 2, False, False, 192000, "", False, 96000]])
        self.assertEqual(r["sound"], [["tv1:mp3:000000", 32000, "[object ArrayBuffer]"], ["tv1:pcm:000000", 192000, "[object ArrayBuffer]"],
                                      ["tv2:pcm:000000", 192000, "[object ArrayBuffer]"], ["tv3:pcm:000000", 192000, "[object ArrayBuffer]"]])
        self.assertEqual(r["first"], 300)                               # its own sound, byte for byte
        self.assertEqual(r["legacy"], [0, 0, 0])
        self.assertEqual(r["notice"], "recovered")
        self.assertEqual(r["blobPuts"], 0)

    def test_unreadable_v1_rows_are_damaged_until_deleted(self):
        # a v1 take whose Blobs can't be read: listed as damaged, its rows kept (not migrated, not dropped); Delete removes
        # them all. Crash pieces that can't be read stay for the next visit.
        r = self.run_pages(r"""
          const W = createWorld();""" + V1 + r"""
          v1.store("takes").put(old("tv9"));
          v1.store("pcm").put({ id: "tv9", blob: new Blob([new Int16Array(96000)]) });
          v1.store("mp3").put({ id: "tv9", blob: new Blob([new Uint8Array(100)]) });
          v1.store("parts").put(part("tv8", 0));
          W.idb.fail({ op: "get", key: "tv9", name: "NotReadableError" });
          W.idb.fail({ op: "read", store: "parts", name: "NotReadableError" });
          const P = page(W);
          await W.until(() => P.C.loaded); await W.idle();
          const legacy = () => { const d = device(W); return [d.takes.map((x) => x.id + ":" + ("v" in x ? x.v : "as v1 wrote it")), d.pcm.length, d.mp3.length, d.parts.length]; };
          const mid = { list: view(P.C).map((t) => [t.id, t.saved, t.damaged, t.url]), rows: legacy(), note: P.C.storeNote() };
          P.C.remove(P.C.find("tv9"));
          await W.idle();
          out({ mid, after: legacy(), list: P.C.takes.length, health: health(W) });""")
        self.assertEqual(r["mid"]["list"], [["tv9", True, True, False]])
        self.assertEqual(r["mid"]["rows"], [["tv9:as v1 wrote it"], 1, 1, 1])   # nothing moved, nothing dropped
        self.assertEqual(r["mid"]["note"], "")
        self.assertEqual(r["after"], [[], 0, 0, 1])                     # Delete: its record and Blobs; tv8's pieces stay
        self.assertEqual(r["list"], 0)


class Reaching(Store):
    def test_an_open_that_never_answers_says_reload_and_try_again_recovers(self):
        # D4/D5: indexedDB.open() that never answers (WebKit 226547): each try gives up after LIMITS.idbOpen (10) s, three
        # tries; the box says "reload" — and the visitor's Try again, once the database answers, lists the takes
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tr1", 2), sound(2)));
          P.leave();
          const f = W.idb.fail({ op: "open", hang: true });
          const t0 = W.now;
          const P2 = page(W, { label: "page 2" });
          await W.until(() => P2.C.loaded, 120000);
          const mid = { waited: W.now - t0, note: P2.C.storeNote(), kept: P2.C.kept, list: P2.C.takes.length,
            opens: W.idb.opens.filter((o) => o.client === "page 2").length };
          await W.tick(15000);                                          // (the visitor reads the box)
          // (nothing else is tried meanwhile: no draft recovered or take moved from a device that can't be read, A5)
          const quiet = W.idb.opens.filter((o) => o.client === "page 2").length - mid.opens;
          f.off();
          P2.C.retry();
          const listed = await W.until(() => P2.C.takes.length === 1, 60000);
          await W.idle();
          out({ mid, quiet, listed, after: { note: P2.C.storeNote(), reload: P2.C.reload, list: view(P2.C).map((t) => [t.id, t.saved, t.url]) }, health: health(W) });""")
        mid = r["mid"]
        self.assertEqual((mid["note"], mid["kept"], mid["list"]), ("reload", True, 0))
        self.assertEqual(mid["opens"], 3)                               # three tries for the list, nothing else
        self.assertGreaterEqual(mid["waited"], 30000)                   # 10 s + 250 ms + 10 s + 1 s + 10 s
        self.assertLess(mid["waited"], 35000)
        self.assertEqual(r["quiet"], 0)
        self.assertTrue(r["listed"], "Try again did not list the device's takes")
        self.assertEqual(r["after"], {"note": "", "reload": False, "list": [["tr1", True, True]]})

    def test_an_open_that_answers_after_it_gave_up_is_closed(self):
        # the first open is "blocked" past its 10 s; the page tries again; when both answer, the late one is closed and
        # the page goes on with one connection
        r = self.run_pages(r"""
          const W = createWorld();
          const f = W.idb.fail({ op: "open", blocked: true });
          const P = page(W);
          await W.tick(12000);
          f.release();
          await W.until(() => P.C.loaded, 60000); await W.idle();
          const ok = await W.wait(P.C.add(meta(W, "tlate", 1), sound(1)));
          out({ ok, opens: W.idb.opens.length, conns: W.idb.dbs.get(DB).conns.size, note: P.C.storeNote(), health: health(W) });""")
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["opens"], 2)
        self.assertEqual(r["conns"], 1)
        self.assertEqual(r["note"], "")

    def test_a_newer_database_says_reload(self):
        # an old copy of the page (the service worker's) meets a database a newer page made (VersionError): nothing is
        # written, "reload" — and Try again keeps saying so while the newer database is there; a VersionError that goes
        # away (Try again after it) recovers
        r = self.run_pages(r"""
          const W = createWorld();
          W.idb.create(DB, 3, { takes: { keyPath: "id" }, sound: { keyPath: "k" } });
          const P = page(W);
          await W.until(() => P.C.loaded); await W.idle();
          const first = { note: P.C.storeNote(), kept: P.C.kept, reload: P.C.reload };
          const ok = await W.wait(P.C.add(meta(W, "tnew", 1), sound(1)));
          await W.idle();
          const added = { ok, take: view(P.C)[0], note: P.C.storeNote() };
          P.C.retry();
          await W.idle();
          const again = P.C.storeNote();
          const W2 = createWorld();
          const f = W2.idb.fail({ op: "open", name: "VersionError" });
          const Q = page(W2);
          await W2.until(() => Q.C.loaded); await W2.idle();
          const q1 = Q.C.storeNote();
          f.off(); Q.C.retry();
          await W2.idle();
          const ok2 = await W2.wait(Q.C.add(meta(W2, "tback", 1), sound(1)));
          out({ first, added, again, q1, q2: Q.C.storeNote(), ok2, rows: device(W).takes.length, health: health(W),
            health2: health(W2) });""")
        self.assertEqual(r["first"], {"note": "reload", "kept": True, "reload": True})
        self.assertFalse(r["added"]["ok"])
        self.assertEqual((r["added"]["take"]["saved"], r["added"]["take"]["failed"]), (False, True))
        self.assertEqual(r["added"]["note"], "reload")
        self.assertEqual(r["again"], "reload")
        self.assertEqual(r["rows"], 0)                                  # the newer database is left as it is
        self.assertEqual((r["q1"], r["q2"], r["ok2"]), ("reload", "", True))
        self.assertEqual(r["health2"], {"errors": [], "unhandled": []})

    def test_a_dropped_connection_is_opened_again(self):
        # iOS ends the networking process (WebKit "Connection to Indexed Database server lost"): the connection is opened
        # again — for the next take, for a write that was on its way, and when db.transaction() throws (closing)
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tc1", 1), sound(1)));
          W.idb.loseConnections();
          const ok2 = await W.wait(P.C.add(meta(W, "tc2", 1, { n: 2, created: W.now + 1 }), sound(1)));
          const p3 = P.C.add(meta(W, "tc3", 1, { n: 3, created: W.now + 2 }), sound(1));
          await W.until(() => W.idb.log.some((e) => e.key === "tc3"));
          W.idb.loseConnections();
          const ok3 = await W.wait(p3);
          const f = W.idb.fail({ op: "transaction", name: "InvalidStateError", times: 1 });
          const ok4 = await W.wait(P.C.add(meta(W, "tc4", 1, { n: 4, created: W.now + 3 }), sound(1)));
          await W.idle();
          out({ oks: [ok2, ok3, ok4], hits: f.hits, list: view(P.C).map((t) => [t.id, t.saved]), finals: device(W).takes.map((x) => [x.id, x.draft]),
            note: P.C.storeNote(), kept: P.C.kept, health: health(W) });""")
        self.assertEqual(r["oks"], [True, True, True])
        self.assertEqual(r["hits"], 1)
        self.assertEqual(r["list"], [["tc4", True], ["tc3", True], ["tc2", True], ["tc1", True]])
        self.assertEqual(r["finals"], [["tc1", False], ["tc2", False], ["tc3", False], ["tc4", False]])
        self.assertEqual((r["note"], r["kept"]), ("", True))

    def test_an_older_safari_without_getall_or_commit(self):
        # Safari before 14 / 15: no getAll / getAllKeys / openKeyCursor / tx.commit() — cursors and auto-commit instead
        r = self.run_pages(r"""
          const W = createWorld();
          Object.assign(W.idb.features, { getAll: false, getAllKeys: false, openKeyCursor: false, commit: false });""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tos1", 1), sound(1, 3000)));
          await W.wait(P.C.add(meta(W, "tos2", 1, { n: 2, created: W.now + 1 }), sound(1)));
          P.leave();
          const P2 = page(W);
          await W.until(() => P2.C.loaded); await W.idle();
          const list = view(P2.C).map((t) => [t.id, t.saved, t.url]);
          P2.C.removeAll();
          await W.idle();
          const d = device(W);
          out({ list, left: [d.takes.length, d.sound.length], health: health(W) });""")
        self.assertEqual(r["list"], [["tos2", True, True], ["tos1", True, True]])
        self.assertEqual(r["left"], [0, 0])


class Choices(Store):
    def test_keep_off_takes_only_this_pages_takes_off_the_device(self):
        # D11: "Keep my recordings on this device" off — asked first while takes are saved; then each take THIS page lists
        # comes into the page and leaves the device, by id: a take another tab saved meanwhile and a draft another tab is
        # making stay; on again, they are saved again
        r = self.run_pages(r"""
          const W = createWorld();
          const P = page(W, { label: "tab 1" });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tk1", 1), sound(1, 2000)));
          await W.wait(P.C.add(meta(W, "tk2", 1, { n: 2, created: W.now + 1 }), sound(1)));
          const T2 = page(W, { label: "tab 2" });
          await W.until(() => T2.C.loaded); await W.idle();
          await W.wait(T2.C.add(meta(W, "tk3", 1, { n: 3, created: W.now + 2 }), sound(1)));
          const store = (n) => W.idb.database(DB).store(n);
          store("takes").put(Object.assign(P.R.clean({ id: "tk4", rate: 48000, samples: 0 }), { v: 2, draft: true, at: W.now }));
          store("sound").put({ k: P.R.soundKey("tk4", "pcm", 0), id: "tk4", kind: "pcm", seq: 0, buf: new ArrayBuffer(96000) });
          W.locks.hold(LOCK + "tk4");
          P.C.toggleKeep({ target: { checked: false } });
          const asked = { confirm: P.C.confirmKeep, keep: P.C.keep, rows: device(W).takes.length };
          P.C.setKeep(false);
          await W.idle();
          const d = device(W);
          const off = { keep: P.C.keep, ls: W.ls["gvlv-rec-keep"], list: view(P.C).map((t) => [t.id, t.saved, t.url]),
            rows: d.takes.map((x) => x.id), sound: [...new Set(d.sound.map((x) => x.id))], note: P.C.storeNote(), atRisk: P.C.atRisk(),
            hold: P.classes.has("cm-rec-hold"), said: P.said.includes(P.C.s.a_keep_off) };
          P.C.setKeep(true);
          await W.until(() => P.C.takes.every((t) => t.saved), 10000); await W.idle();
          out({ asked, off, on: { ls: W.ls["gvlv-rec-keep"], rows: device(W).takes.map((x) => [x.id, x.draft]), hold: P.classes.has("cm-rec-hold") },
            health: health(W) });""")
        self.assertEqual(r["asked"], {"confirm": True, "keep": True, "rows": 4})   # nothing goes before the question
        off = r["off"]
        self.assertEqual((off["keep"], off["ls"]), (False, "0"))
        self.assertEqual(off["list"], [["tk2", False, True], ["tk1", False, True]])   # still here, in the page
        self.assertEqual(off["rows"], ["tk3", "tk4"])
        self.assertEqual(off["sound"], ["tk3", "tk4"])
        self.assertEqual((off["note"], off["atRisk"], off["hold"]), ("", True, True))  # only in this page: leaving asks
        self.assertTrue(off["said"])
        self.assertEqual(r["on"], {"ls": "1", "rows": [["tk1", False], ["tk2", False], ["tk3", False], ["tk4", True]], "hold": False})

    def test_delete_all_spares_a_take_another_tab_is_making(self):
        # D11: Delete all — every take on the device (drafts too, sound no take owns) but a draft another tab holds the lock of
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + DRAFTS + r"""
          await W.wait(P.C.add(meta(W, "ta1", 1), sound(1, 2000)));
          await W.wait(P.C.add(meta(W, "ta2", 1, { n: 2, created: W.now + 1 }), sound(1)));
          draft("tother", { at: W.now }); pcmRow("tother", 0, 48000); W.locks.hold(LOCK + "tother");
          draft("tstale"); pcmRow("tstale", 0, 48000);
          store("sound").put({ k: P.R.soundKey("torph", "pcm", 0), id: "torph", kind: "pcm", seq: 0, buf: new ArrayBuffer(10) });
          P.C.removeAll();
          await W.idle();
          const d = device(W);
          out({ rows: d.takes.map((x) => x.id), sound: d.sound.map((x) => x.k), list: P.C.takes.length, locks: W.locks.names(),
            said: P.said.includes(P.C.s.a_deleted_all), health: health(W) });""")
        self.assertEqual(r["rows"], ["tother"])
        self.assertEqual(r["sound"], ["tother:pcm:000000"])
        self.assertEqual(r["list"], 0)
        self.assertEqual(r["locks"], ["gvlv-rec:tother"])
        self.assertTrue(r["said"])

    def test_deleting_a_take_while_it_is_being_written_leaves_nothing_behind(self):
        # a 60-second take (5 MB: its PCM goes in two writes) is deleted while its first write is on its way: the write
        # stops at its next step and what got onto the device goes
        r = self.run_pages(r"""
          const W = createWorld(); W.idb.latency = 20;""" + LOADED + r"""
          const p = P.C.add(meta(W, "tdel", 60), sound(60));
          await W.until(() => W.idb.log.some((e) => e.key === "tdel:pcm:000000"));
          const inFlight = W.idb.log.find((e) => e.key === "tdel:pcm:000000").ok;
          P.C.remove(P.C.find("tdel"));
          const ok = await W.wait(p);
          await W.idle();
          out({ inFlight, ok, row: row(W, "tdel"), sound: rows(W, "tdel").length, list: P.C.takes.length, lock: W.locks.names(),
            guard: P.leaveGuard(), hold: P.classes.has("cm-rec-hold"), health: health(W) });""")
        self.assertIsNone(r["inFlight"])
        self.assertFalse(r["ok"])
        self.assertEqual((r["row"], r["sound"], r["list"], r["lock"]), (None, 0, 0, []))
        self.assertEqual((r["guard"], r["hold"]), (0, False))

    def test_two_takes_added_at_once_are_both_saved(self):
        # two quick takes (an import and an edit finishing together): each gets its own write and its own rows
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const a = P.C.add(meta(W, "tq1", 2), sound(2, 1000)), b = P.C.add(meta(W, "tq2", 3, { n: 2, created: W.now + 1 }), sound(3, 2000));
          const oks = [await W.wait(a), await W.wait(b)];
          await W.idle();
          out({ oks, rows: device(W).takes.map((x) => [x.id, x.draft, x.size]), sound: device(W).sound.map((x) => [x.k, x.buf.byteLength]), health: health(W) });""")
        self.assertEqual(r["oks"], [True, True])
        self.assertEqual(r["rows"], [["tq1", False, 2 * 44100 * 2 + 1000], ["tq2", False, 3 * 44100 * 2 + 2000]])
        self.assertEqual(r["sound"], [["tq1:mp3:000000", 1000], ["tq1:pcm:000000", 176400], ["tq2:mp3:000000", 2000], ["tq2:pcm:000000", 264600]])


class Leaving(Store):
    def test_a_link_click_while_a_take_is_not_saved_asks_first(self):
        # D8: an iPhone shows no beforeunload question — a link that would take this tab away asks in the page
        # (window.confirm). Cancel (answered after 100 ms) stays; OK goes, with no second question from the browser.
        # Links that don't leave the page are not asked about; once the take is saved, nothing is asked.
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === "tlv" && i.value.draft === false, name: "UnknownError" });
          await W.wait(P.C.add(meta(W, "tlv", 2), sound(2)));
          await W.idle();
          P.tab.answer = () => ({ answer: false, after: 100 });
          const cancel = P.click("/aagrapevine/events/");
          const asked = P.tab.dialogs.slice();
          P.tab.answer = () => ({ answer: true, after: 400 });
          const go = P.click("/aagrapevine/events/");
          // (the browser's question stays on, but lets this one go: 3 s — then it asks again by itself, r10 A22)
          const afterGo = { guard: P.leaveGuard(), asks: P.unload() };
          await W.tick(3100);
          const later = { guard: P.leaveGuard(), asks: P.unload() };
          P.tab.dialogs.length = 0;
          P.tab.answer = () => ({ answer: false, after: 100 });
          const quiet = { hash: P.click("#deadlines"), blank: P.click("/aagrapevine/events/", { target: "_blank" }),
            download: P.click("/aagrapevine/story.mp3", { download: "" }), mail: P.click("mailto:gv@example.org"),
            recGo: P.click("#recorder", { "data-rec-go": "gv" }), keys: P.click("/aagrapevine/events/", {}, { metaKey: true }) };
          const quietAsked = P.tab.dialogs.length;
          f.off(); P.C.retry();
          await W.until(() => P.C.find("tlv").saved, 5000); await W.idle();
          P.tab.dialogs.length = 0;
          const saved = { stopped: P.click("/aagrapevine/events/"), asked: P.tab.dialogs.length, guard: P.leaveGuard() };
          out({ cancel, asked, words: P.C.s.leave_unsaved, go, afterGo, later, quiet, quietAsked, saved, health: health(W) });""")
        self.assertTrue(r["cancel"])                                    # the link did not go
        self.assertEqual(r["asked"], [r["words"]])
        self.assertTrue(r["words"])
        self.assertFalse(r["go"])                                       # OK: the link goes on
        self.assertEqual(r["afterGo"], {"guard": 1, "asks": False})     # …with no second question from the browser
        self.assertEqual(r["later"], {"guard": 1, "asks": True})        # a link that did not leave: asked again later
        self.assertEqual(r["quiet"], {"hash": False, "blank": False, "download": False, "mail": False, "recGo": True, "keys": False})
        self.assertEqual(r["quietAsked"], 0)                            # (recGo: its own scroll, not a question)
        self.assertEqual(r["saved"], {"stopped": False, "asked": 0, "guard": 0})

    def test_a_link_click_while_recording_asks_with_the_recording_words(self):
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 1);
          P.tab.answer = () => ({ answer: false, after: 150 });
          const stopped = P.click("/aagrapevine/events/");
          await feed(P, kit, 0.5);
          out({ stopped, dialogs: P.tab.dialogs, words: P.C.s.leave_rec, state: P.C.state, health: health(W) });""")
        self.assertTrue(r["stopped"])
        self.assertEqual(r["dialogs"], [r["words"]])
        self.assertEqual(r["state"], "recording")                      # the take goes on


class Browser(Store):
    def test_persist_is_asked_once_from_the_taps_that_save(self):
        # D6: navigator.storage.persist() — never on load, once a page from Stop and save (two quick takes: one question),
        # never while "Keep" is off; its answer is the "This device" line
        r = self.run_pages(r"""
          const W = createWorld(); W.storage.grant = true;""" + RECORD + r"""
          const atLoad = W.storage.calls.persist;
          await feed(P, kit, 2);
          P.C.stop(true);
          await W.until(() => P.C.state === "idle" && P.C.takes.length === 1 && P.C.takes[0].saved, 30000);
          const first = { persist: W.storage.calls.persist, persisted: P.C.persisted, line: P.C.keptLine() };
          kit.i = 0;
          P.C.open("record");
          await W.until(() => P.C.state === "recording", 10000);
          await feed(P, kit, 1.5);
          P.C.stop(true);
          await W.until(() => P.C.state === "idle" && P.C.takes.length === 2 && P.C.takes.every((t) => t.saved), 30000);
          await W.idle();
          const second = { persist: W.storage.calls.persist, ids: new Set(P.C.takes.map((t) => t.id)).size, ns: P.C.takes.map((t) => t.n),
            rows: device(W).takes.map((x) => x.draft) };
          P.leave();
          W.ls["gvlv-rec-keep"] = "0"; W.storage.persisted = false; W.storage.grant = false;
          const kit2 = audioKit(), Q = page(W, { audio: kit2 });
          await W.until(() => Q.C.loaded); await W.idle();
          Q.C.open("record");
          await W.until(() => Q.C.state === "recording", 10000);
          await feed(Q, kit2, 1.5);
          Q.C.stop(true);
          await W.until(() => Q.C.state === "idle", 30000); await W.idle();
          const off = { persist: W.storage.calls.persist, list: view(Q.C).map((t) => t.saved), rows: device(W).takes.length, note: Q.C.storeNote(),
            atRisk: Q.C.atRisk(), line: Q.C.keptLine() };
          out({ atLoad, first, second, off, health: health(W) });""")
        self.assertEqual(r["atLoad"], 0)
        self.assertEqual(r["first"], {"persist": 1, "persisted": True, "line": "yes"})
        self.assertEqual(r["second"], {"persist": 1, "ids": 2, "ns": [2, 1], "rows": [False, False]})
        # (Keep off: the new take is in the page only; the two on the device are still listed)
        self.assertEqual(r["off"], {"persist": 1, "list": [False, True, True], "rows": 2, "note": "", "atRisk": True, "line": ""})

    def test_back_from_the_cache_lists_the_device_again(self):
        # D9: Back to a page kept in the back-forward cache (pageshow, persisted): the list as the device has it now —
        # another tab deleted one take and added another — and the take only in this page is kept, and tried again.
        # That tab never adopts the unsaved take's draft: this page holds its lock.
        r = self.run_pages(r"""
          const W = createWorld();
          const P = page(W, { label: "tab 1" });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tb1", 1), sound(1)));
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === "tbu" && i.value.draft === false, name: "UnknownError" });
          await W.wait(P.C.add(meta(W, "tbu", 60, { n: 2, created: W.now + 1 }), sound(60)));
          await W.idle();
          const onDevice = { draft: row(W, "tbu").draft, pcm: rows(W, "tbu", "pcm").length, lock: W.locks.names().includes(LOCK + "tbu") };
          const T2 = page(W, { label: "tab 2" });
          await W.until(() => T2.C.loaded); await W.idle();
          const tab2 = view(T2.C).map((t) => t.id);
          T2.C.remove(T2.C.find("tb1"));
          await W.wait(T2.C.add(meta(W, "tb2", 1, { n: 3, created: W.now + 2 }), sound(1)));
          await W.idle();
          P.pageshow(true);
          await W.until(() => !!P.C.find("tb2"), 10000); await W.idle();
          const back = view(P.C).map((t) => [t.id, t.saved, t.failed]);
          f.off();
          P.pageshow(true);
          const saved = await W.until(() => P.C.find("tbu").saved, 10000);
          await W.idle();
          out({ onDevice, tab2, back, saved, rows: device(W).takes.map((x) => [x.id, x.draft]), note: P.C.storeNote(), health: health(W) });""")
        # 60 s (5.05 MiB): all six rows (a write of 4 MiB, one of the rest) went before the final write (r10 A6)
        self.assertEqual(r["onDevice"], {"draft": True, "pcm": 6, "lock": True})
        self.assertEqual(r["tab2"], ["tb1"])                            # not adopted as a "Recovered recording"
        self.assertEqual(r["back"], [["tb2", True, False], ["tbu", False, True]])
        self.assertTrue(r["saved"])
        self.assertEqual(r["rows"], [["tb2", False], ["tbu", False]])
        self.assertEqual(r["note"], "")


class Edges(Store):
    def test_the_sound_so_far_goes_to_the_device_when_the_page_is_hidden(self):
        # D2: on visibilitychange → hidden and on pagehide the sound since the last write goes at once (a computer: the
        # take goes on recording in the background)
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 1.5);
          const before = rows(W, id, "pcm").length;
          P.hidden();
          await W.until(() => rows(W, id, "pcm").length === 1, 2000);
          const hidden = { seqs: rows(W, id, "pcm").map((x) => x.seq), samples: row(W, id).samples, blocks: kit.i, state: P.C.state };
          P.visible();
          await feed(P, kit, 1);
          for (const l of P.win.pagehide || []) l.fn({ type: "pagehide", persisted: true });
          await W.until(() => rows(W, id, "pcm").length === 2, 2000);
          out({ before, hidden, pagehide: { seqs: rows(W, id, "pcm").map((x) => x.seq), samples: row(W, id).samples, blocks: kit.i }, health: health(W) });""")
        self.assertEqual(r["before"], 0)
        h = r["hidden"]
        self.assertEqual((h["seqs"], h["samples"], h["state"]), ([0], h["blocks"] * 4096, "recording"))
        p = r["pagehide"]
        self.assertEqual((p["seqs"], p["samples"]), ([0, 1], p["blocks"] * 4096))

    def test_stop_then_a_link_at_once_the_take_comes_back_whole(self):
        # Stop writes the last seconds at once; a link tapped before the final write lands (the browser aborts it as the
        # page goes) still leaves the whole take on the device: the next page brings it back, every second of it
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 5);
          const blocks = kit.i;
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.draft === false, hang: true });
          P.C.stop(true);
          await W.until(() => row(W, id).samples === blocks * 4096, 5000);
          await W.until(() => f.hits > 0, 5000);
          P.leave();
          f.off();
          const P2 = page(W);
          await W.until(() => P2.C.loaded); await W.idle();
          out({ blocks, list: view(P2.C).map((t) => [t.saved, t.src, t.samples]), bytes: total(rows(W, id, "pcm")), health: health(W) });""")
        n = r["blocks"]
        self.assertEqual(r["list"], [[True, "recovered", n * 4096]])
        self.assertEqual(r["bytes"], n * 4096 * 2)

    def test_a_take_being_recorded_in_another_tab_is_left_alone(self):
        # tab 1 is recording (its draft and Web Lock); tab 2 opens /contribute/: it does not adopt the draft, and tab 1's
        # take is saved once, as usual
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 4);
          const T2 = page(W, { label: "tab 2" });
          await W.until(() => T2.C.loaded); await W.idle();
          const tab2 = { list: T2.C.takes.length, draft: row(W, id).draft, pcm: rows(W, id, "pcm").length, notice: T2.C.notice,
            changes: W.idb.log.filter((e) => e.client === "tab 2").length };
          await feed(P, kit, 1);
          P.C.stop(true);
          await W.until(() => P.C.state === "idle" && P.C.takes.length === 1 && P.C.takes[0].saved, 30000);
          out({ tab2, rows: device(W).takes.map((x) => [x.id === id, x.draft, x.src]), health: health(W) });""")
        self.assertEqual(r["tab2"], {"list": 0, "draft": True, "pcm": 1, "notice": "", "changes": 0})
        self.assertEqual(r["rows"], [[True, False, "mic"]])

    def test_an_unsaved_take_is_tried_again_when_the_page_is_shown_again(self):
        # D4: back to the page (visibilitychange → visible): the takes waiting are written at once, not 20 s later
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === "tvz" && i.value.draft === false, name: "AbortError" });
          await W.wait(P.C.add(meta(W, "tvz", 1), sound(1)));
          await W.idle();
          const was = P.C.find("tvz").failed;
          P.hidden();
          f.off();
          await W.tick(2000);
          P.visible();
          const saved = await W.until(() => P.C.find("tvz").saved, 1500);
          out({ was, saved, health: health(W) });""")
        self.assertTrue(r["was"])
        self.assertTrue(r["saved"])

    def test_an_added_recording_closed_mid_save_comes_back(self):
        # D2: "Edits and imports use the same path: draft row → PCM rows (several short transactions) → final row with the
        # MP3. So a page closed mid-save leaves a recoverable draft, not an orphan." A 10-second recording the visitor added
        # is being written when the page goes (the final write never lands): the next page brings it back.
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === "timp" && i.value.draft === false, hang: true });
          P.C.add(meta(W, "timp", 10), sound(10, 160000));
          await W.until(() => f.hits > 0, 10000);
          const pcmBefore = W.idb.log.filter((e) => e.store === "sound" && e.committed && String(e.key).startsWith("timp:pcm:")).length;
          P.crash();
          f.off();
          W.now += 3 * 60e3;                                         // (a later visit: the draft is not "just begun")
          const P2 = page(W);
          await W.until(() => P2.C.loaded); await W.idle();
          out({ pcmBefore, list: view(P2.C).map((t) => [t.saved, t.src, t.samples]), row: row(W, "timp") && row(W, "timp").draft, health: health(W) });""")
        self.assertGreater(r["pcmBefore"], 0, "the PCM was not on the device before the final write")
        self.assertEqual(r["list"], [[True, "recovered", 10 * 44100]])
        self.assertFalse(r["row"])


class LostStore(Store):
    def test_a_private_window_that_loses_its_database_saves_the_takes_again(self):
        # A1 (r10 storage F1): Safari's private window keeps its databases in a process iOS ends in the background — the
        # page lives on, the device's copy is gone. There the page keeps every saved take's sound, sees the loss when it is
        # shown again (or on Back), and saves the takes again: "not saved" meanwhile (leaving asks first), then saved
        r = self.run_pages(r"""
          const W = createWorld(); W.storage.private = true;
          const P = page(W, { ua: UA.iphone });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tl1", 3), sound(3, 6000)));
          await W.wait(P.C.add(meta(W, "tl2", 2, { n: 2, created: W.now + 1 }), sound(2)));
          await W.idle();
          const first = { priv: P.C.priv, saved: P.C.takes.map((t) => t.saved), rows: device(W).takes.length };
          W.idb.loseAll({ silent: true });                           // (no "close": what iOS 17-18 were seen to do)
          await W.tick(1000);
          const lost = { device: device(W), saved: P.C.takes.map((t) => t.saved) };
          P.said.length = 0;
          P.visible();
          await W.until(() => P.C.takes.some((t) => !t.saved), 5000);
          const seen = { list: view(P.C).map((t) => [t.id, t.saved, t.failed]), hold: P.classes.has("cm-rec-hold"), atRisk: P.C.atRisk() };
          await W.until(() => P.C.takes.every((t) => t.saved), 10000); await W.idle();
          const back = { list: view(P.C).map((t) => [t.id, t.saved, t.failed]), hold: P.classes.has("cm-rec-hold"), note: P.C.storeNote(),
            takes: device(W).takes.map((x) => [x.id, x.draft, x.size]), pcm: [total(rows(W, "tl1", "pcm")), total(rows(W, "tl2", "pcm"))],
            mp3: total(rows(W, "tl1", "mp3")), said: P.said.slice() };
          // again — and this time the visitor comes Back to the page (pageshow, from the back-forward cache)
          W.idb.loseAll();
          await W.tick(1000);
          P.pageshow(true);
          await W.until(() => P.C.takes.length === 2 && P.C.takes.every((t) => t.saved) && ((device(W) || {}).takes || []).length === 2, 10000);
          await W.idle();
          const again = { list: view(P.C).map((t) => [t.id, t.saved]), takes: device(W).takes.map((x) => [x.id, x.draft]),
            pcm: [total(rows(W, "tl1", "pcm")), total(rows(W, "tl2", "pcm"))] };
          const words = [P.C.t("a_saved", { name: "Take 2", time: P.R.spoken(2, P.C.s.words) }), P.C.t("a_saved", { name: "Take 1", time: P.R.spoken(3, P.C.s.words) })];
          out({ first, lost, seen, back, again, words, health: health(W) });""")
        self.assertEqual(r["first"], {"priv": True, "saved": [True, True], "rows": 2})
        self.assertEqual(r["lost"], {"device": None, "saved": [True, True]})   # (nothing tells the page until it looks)
        # shown again: it looks, and says so — not saved, leaving asks first
        self.assertEqual(r["seen"]["list"], [["tl2", False, True], ["tl1", False, True]])
        self.assertEqual((r["seen"]["hold"], r["seen"]["atRisk"]), (True, True))
        # saved again from the page's own copy, every byte
        self.assertEqual(r["back"]["list"], [["tl2", True, False], ["tl1", True, False]])
        self.assertEqual((r["back"]["hold"], r["back"]["note"]), (False, "private"))
        self.assertEqual(sorted(r["back"]["takes"]), [["tl1", False, 3 * 44100 * 2 + 6000], ["tl2", False, 2 * 44100 * 2]])
        self.assertEqual(r["back"]["pcm"], [3 * 44100 * 2, 2 * 44100 * 2])
        self.assertEqual(r["back"]["mp3"], 6000)
        self.assertEqual(sorted(r["back"]["said"]), sorted(r["words"]))       # "saved", now that it is (A14)
        self.assertEqual(r["again"], {"list": [["tl2", True], ["tl1", True]], "takes": [["tl1", False], ["tl2", False]],
                                      "pcm": [3 * 44100 * 2, 2 * 44100 * 2]})

    def test_a_normal_window_keeps_no_sound_of_a_saved_take(self):
        # A11: a normal window keeps a saved take's player only (its sound is read back when needed) — so a take the device
        # no longer has (deleted in another tab, or site data cleared) goes from the list on Back, and Share / Download
        # still get its bytes from the device
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tn1", 2), sound(2, 4000)));
          await W.wait(P.C.add(meta(W, "tn2", 1, { n: 2, created: W.now + 1 }), sound(1, 2000)));
          await W.idle();
          const mp3 = await W.wait(P.C.kindOf("tn1", "mp3")), pcm = await W.wait(P.C.pcmOf("tn1"));
          const fromDevice = [mp3.byteLength, pcm.byteLength];
          // (deleted in another tab, as the device has it now)
          const st = (n) => W.idb.database(DB).store(n);
          st("takes").delete("tn1");
          for (const k of st("sound").keys()) if (String(k).startsWith("tn1:")) st("sound").delete(k);
          P.pageshow(true);
          await W.until(() => P.C.takes.length === 1, 10000); await W.idle();
          out({ fromDevice, list: view(P.C).map((t) => [t.id, t.saved]), note: P.C.storeNote(), health: health(W) });""")
        self.assertEqual(r["fromDevice"], [4000, 2 * 44100 * 2])
        self.assertEqual(r["list"], [["tn2", True]])
        self.assertEqual(r["note"], "")

    def test_shown_again_and_back_at_once_keep_the_takes(self):
        # r10 N1: a private window whose database the browser lost; the page is shown again (visibilitychange: checkLost
        # finds the takes missing and starts writing them again) and, in the same moment, restored by Back (pageshow:
        # load() lists the device again) — the list read must not take the takes checkLost just marked "not saved" for
        # ones deleted in another tab: they stay, and are saved again, every byte
        r = self.run_pages(r"""
          const res = {};
          for (const [k, order, latency] of [["visibleThenBack", ["visible", "back"], 0], ["focusThenBack", ["focus", "back"], 0],
                                             ["slowStorage", ["visible", "back"], 20]]) {
            const W = createWorld(); W.storage.private = true; W.idb.latency = latency;
            const P = page(W, { ua: UA.iphone });
            await W.until(() => P.C.loaded); await W.idle();
            await W.wait(P.C.add(meta(W, "tl1", 3), sound(3, 6000)));
            await W.wait(P.C.add(meta(W, "tl2", 2, { n: 2, created: W.now + 1 }), sound(2)));
            await W.idle();
            await W.tick(6000);                                       // (checkLost asks at most every 5 s)
            W.idb.loseAll();
            await W.tick(1000);
            for (const ev of order) {
              if (ev === "visible") P.visible();
              else if (ev === "focus") for (const l of P.win.focus || []) l.fn({ type: "focus" });
              else P.pageshow(true);
            }
            const seen = [];
            for (let i = 0; i < 40; i++) { await W.tick(250); seen.push(P.C.takes.length); }
            await W.idle();
            res[k] = { fewest: Math.min(...seen), list: view(P.C).map((t) => [t.id, t.saved, t.failed]),
              takes: device(W).takes.map((x) => [x.id, x.draft]).sort(), pcm: [total(rows(W, "tl1", "pcm")), total(rows(W, "tl2", "pcm"))],
              mp3: total(rows(W, "tl1", "mp3")), hold: P.classes.has("cm-rec-hold"), errors: health(W).errors };
          }
          out({ res, health: { errors: Object.values(res).flatMap((v) => v.errors), unhandled } });""")
        for k, v in r["res"].items():
            with self.subTest(order=k):
                self.assertEqual(v["fewest"], 2, "a take left the list")
                self.assertEqual(v["list"], [["tl2", True, False], ["tl1", True, False]])
                self.assertEqual(v["takes"], [["tl1", False], ["tl2", False]])
                self.assertEqual(v["pcm"], [3 * 44100 * 2, 2 * 44100 * 2])
                self.assertEqual((v["mp3"], v["hold"]), (6000, False))

    def test_a_loss_while_the_page_stays_on_screen_is_found_at_once(self):
        # r10 repro K2/K4/K8: a private window's database is lost while the page is in front — no focus, no
        # visibilitychange, no pageshow follows. The dropped connection's "close" is enough: the takes are looked for,
        # found missing and saved again from the page's copy within a moment (before a link could take the visitor away),
        # each with a new player address (the old blob: one died with the process)
        r = self.run_pages(r"""
          const W = createWorld(); W.storage.private = true;
          const P = page(W, { ua: UA.iphone });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tk1", 3), sound(3, 6000)));
          await W.wait(P.C.add(meta(W, "tk2", 2, { n: 2, created: W.now + 1 }), sound(2)));
          await W.idle();
          const before = P.C.takes.map((t) => t.url);
          P.said.length = 0;
          W.idb.loseAll();
          await W.tick(10);
          const gone = device(W);
          await W.tick(400);                                         // ("close", then the look 300 ms later)
          const soon = device(W);
          await W.idle();
          out({ gone, soon: soon && soon.takes.map((x) => [x.id, x.draft]).sort(), said: P.said.slice(),
            words: [P.C.t("a_saved", { name: "Take 2", time: P.R.spoken(2, P.C.s.words) }), P.C.t("a_saved", { name: "Take 1", time: P.R.spoken(3, P.C.s.words) })],
            list: view(P.C).map((t) => [t.id, t.saved, t.failed]),
            pcm: [total(rows(W, "tk1", "pcm")), total(rows(W, "tk2", "pcm"))],
            newUrls: P.C.takes.every((t, i) => t.url && t.url !== before[i]), health: health(W) });""")
        self.assertIsNone(r["gone"])
        self.assertEqual(r["soon"], [["tk1", False], ["tk2", False]], "saved again before any focus / visibility / pageshow")
        self.assertEqual(sorted(r["said"]), sorted(r["words"]))     # (each said again: it had been "not saved" meanwhile)
        self.assertEqual(r["list"], [["tk2", True, False], ["tk1", True, False]])
        self.assertEqual(r["pcm"], [3 * 44100 * 2, 2 * 44100 * 2])
        self.assertTrue(r["newUrls"])

    def test_a_loss_while_recording_keeps_the_whole_take(self):
        # r10 N2: the browser loses the database while a take is being recorded (after its first writes): the writes after
        # it start again from the take's first block in the new database (what a write put there before the loss was seen
        # goes first) — the take is saved whole, and the next page's WAV has every sample, each where it belongs
        r = self.run_pages(r"""
          const W = createWorld(); W.storage.private = true;
          const kit = audioKit(), enc = encoderKit();
          const P = page(W, { audio: kit, encoder: enc, ua: UA.iphone });
          await W.until(() => P.C.loaded); await W.idle();
          P.C.open("record");
          await W.until(() => P.C.state === "recording", 10000);
          await W.until(() => ((device(W) || {}).takes || []).some((x) => x.draft), 2000);
          const id = device(W).takes.find((x) => x.draft).id;
          await feed(P, kit, 7);
          const before = rows(W, id, "pcm").map((x) => x.seq);
          W.idb.loseAll();
          // (the next write finds the database new — what it put there, the tail, is not counted —, the one after it
          // writes the take from its first block, the tail deleted first)
          await feed(P, kit, 7);
          const during = { seqs: rows(W, id, "pcm").map((x) => x.seq), draft: !!row(W, id) && row(W, id).draft };
          await feed(P, kit, 3);
          const blocks = kit.i;
          P.C.stop(true);
          await W.until(() => P.C.state === "idle" && P.C.takes.length > 0 && P.C.takes[0].saved, 30000);
          await W.tick(10000); await W.idle();""" + PCM_CHECK + r"""
          const stored = pcmCheck(W, id, blocks), x = row(W, id);
          P.leave();
          const P2 = page(W, { ua: UA.iphone, encoder: enc, label: "page 2" });
          await W.until(() => P2.C.loaded); await W.idle();
          const t = P2.C.takes[0], wav = (await W.wait(P2.C.pcmOf(t.id))).byteLength;
          out({ before, during, blocks, stored, rec: [x.draft, x.samples], next: [t.saved, t.damaged, t.samples, wav], health: health(W) });""")
        n = r["blocks"]
        self.assertEqual(r["before"], [0, 1])
        self.assertTrue(r["during"]["draft"], "the new database has no draft of the take being recorded")
        self.assertTrue(r["during"]["seqs"])
        self.assertEqual(r["during"]["seqs"], list(range(len(r["during"]["seqs"]))), "the new database holds only the tail of the take")
        self.assertEqual(r["stored"]["seqs"], list(range(len(r["stored"]["seqs"]))))     # 0, 1, 2… none missing, none twice
        self.assertEqual((r["stored"]["bytes"], r["stored"]["misplaced"]), (n * 4096 * 2, 0))
        self.assertEqual(r["rec"], [False, n * 4096])
        self.assertEqual(r["next"], [True, False, n * 4096, n * 4096 * 2])

    def test_a_loss_between_an_added_takes_writes_keeps_it_whole(self):
        # r10 N2: an added recording (60 s: its PCM in two transactions, then the final one) whose database the browser
        # loses after the first: the rest goes into the new database only with the first part again — saved whole, never
        # "saved" with the start of its sound missing
        r = self.run_pages(r"""
          const W = createWorld(); W.storage.private = true; W.idb.latency = 50;
          const P = page(W, { ua: UA.iphone });
          await W.until(() => P.C.loaded); await W.idle();
          const p = P.C.add(meta(W, "tb1", 60), sound(60, 9000));
          await W.until(() => rows(W, "tb1", "pcm").length >= 4, 20000);
          const first = rows(W, "tb1", "pcm").map((x) => x.seq);
          W.idb.loseAll();
          const ok = await W.wait(p);
          await W.tick(20000); await W.idle();
          const x = row(W, "tb1");
          out({ first, ok, list: view(P.C).map((t) => [t.id, t.saved]), rec: [x.draft, x.samples, x.size], seqs: rows(W, "tb1", "pcm").map((s) => s.seq),
            pcm: total(rows(W, "tb1", "pcm")), mp3: total(rows(W, "tb1", "mp3")), health: health(W) });""")
        self.assertEqual(r["first"], [0, 1, 2, 3])
        self.assertTrue(r["ok"])
        self.assertEqual(r["list"], [["tb1", True]])
        self.assertEqual(r["rec"], [False, 60 * 44100, 60 * 44100 * 2 + 9000])
        self.assertEqual((r["seqs"], r["pcm"], r["mp3"]), ([0, 1, 2, 3, 4, 5], 60 * 44100 * 2, 9000))

    def test_another_iphone_browsers_private_tab_keeps_the_sound_too(self):
        # r10 N3: Chrome on an iPhone (CriOS) in a private tab keeps its databases where Safari's private tab does — in the
        # process iOS ends. It is not told "private" (A21), but its takes' sound stays in the page, so each loss is seen
        # and the takes are saved again, as in Safari
        r = self.run_pages(r"""
          const CRIOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.6723.90 Mobile/15E148 Safari/604.1";
          const W = createWorld(); W.storage.private = true;
          const P = page(W, { ua: CRIOS });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tc1", 3), sound(3, 6000)));
          await W.idle();
          const first = { priv: P.C.priv, ephemeral: P.C.ephemeral, line: P.C.keptLine(), note: P.C.storeNote() };
          const lose = async () => { await W.tick(6000); W.idb.loseAll(); await W.tick(1000); P.visible(); await W.tick(20000); await W.idle(); };
          await lose();
          const once = { list: view(P.C).map((t) => [t.id, t.saved]), device: device(W).takes.map((x) => x.id) };
          await W.wait(P.C.add(meta(W, "tc2", 2, { n: 2, created: W.now + 1 }), sound(2, 3000)));
          await W.idle();
          await lose();
          out({ first, once, twice: { list: view(P.C).map((t) => [t.id, t.saved]), device: device(W).takes.map((x) => x.id).sort(),
            pcm: [total(rows(W, "tc1", "pcm")), total(rows(W, "tc2", "pcm"))], hold: P.classes.has("cm-rec-hold") }, health: health(W) });""")
        self.assertEqual(r["first"], {"priv": False, "ephemeral": True, "line": "browser", "note": ""})
        self.assertEqual(r["once"], {"list": [["tc1", True]], "device": ["tc1"]})
        self.assertEqual(r["twice"], {"list": [["tc2", True], ["tc1", True]], "device": ["tc1", "tc2"],
                                      "pcm": [3 * 44100 * 2, 2 * 44100 * 2], "hold": False})

    def test_a_saved_take_lost_with_no_copy_in_the_page_says_so(self):
        # r10 N3: where the page could not know the browser may lose its database (here: Chrome on an iPhone that does not
        # refuse getDirectory), a take saved before the loss keeps no sound in the page. Once the page sees the loss (the
        # next write finds the database new) that take is "lost" — said, shown with its own words and Delete, never as
        # saved, and leaving does not ask for it; from then on the page keeps its takes' sound and saves them again. A
        # normal window that finds its database new on Back (site data cleared) says the same of its takes — whereas a
        # take deleted in another tab just goes (test_a_normal_window_keeps_no_sound_of_a_saved_take)
        r = self.run_pages(r"""
          const CRIOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.6723.90 Mobile/15E148 Safari/604.1";
          const W = createWorld();
          const P = page(W, { ua: CRIOS });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tq1", 3), sound(3, 6000)));
          await W.idle();
          const first = { ephemeral: P.C.ephemeral, saved: P.C.find("tq1").saved };
          W.idb.loseAll();
          await W.tick(6000);
          P.visible();                                                // (nothing to look with yet: not known to be ephemeral)
          await W.tick(1000);
          const unseen = view(P.C).map((t) => [t.id, t.saved]);
          P.said.length = 0;
          await W.wait(P.C.add(meta(W, "tq2", 2, { n: 2, created: W.now + 1 }), sound(2)));
          await W.tick(1000); await W.idle();
          const tq1 = P.C.find("tq1");
          const seen = { tq1: [tq1.saved, tq1.damaged, tq1.lost, !!tq1.url], tq2: P.C.find("tq2").saved, ephemeral: P.C.ephemeral,
            said: P.said.slice(), atRisk: P.C.atRisk(), note: P.C.storeNote(), hold: P.classes.has("cm-rec-hold"),
            device: device(W).takes.map((x) => x.id) };
          P.C.reread(tq1);                                            // (no Try again for it: nothing to read)
          await W.tick(6000);
          W.idb.loseAll();
          await W.tick(1000);
          P.visible();
          await W.tick(20000); await W.idle();
          const again = { list: view(P.C).map((t) => [t.id, t.saved, t.damaged]), device: device(W).takes.map((x) => x.id) };
          P.pageshow(true);
          await W.tick(5000); await W.idle();
          const back = view(P.C).map((t) => [t.id, t.saved, t.damaged]);
          P.C.remove(P.C.find("tq1"));
          await W.idle();
          const removed = view(P.C).map((t) => t.id);
          // a normal window, site data cleared, then Back
          const W2 = createWorld();
          const Q = page(W2);
          await W2.until(() => Q.C.loaded); await W2.idle();
          await W2.wait(Q.C.add(meta(W2, "tw1", 2), sound(2)));
          await W2.idle();
          W2.idb.loseAll();
          Q.said.length = 0;
          Q.pageshow(true);
          await W2.tick(5000); await W2.idle();
          const cleared = { list: view(Q.C).map((t) => [t.id, t.saved, t.damaged]), lost: Q.C.find("tw1") && Q.C.find("tw1").lost, said: Q.said.slice() };
          const words = { one: P.C.t("a_lost", { name: "Take 1" }), two: P.C.t("a_lost_n", { n: 2 }) };
          out({ first, unseen, seen, again, back, removed, cleared, words,
            health: { errors: health(W).errors.concat(health(W2).errors), unhandled } });""")
        self.assertEqual(r["first"], {"ephemeral": False, "saved": True})
        self.assertEqual(r["unseen"], [["tq1", True]])                  # (nothing tells the page until it writes)
        seen = r["seen"]
        self.assertEqual(seen["tq1"], [False, True, True, False])      # not saved, shown as lost, no player
        self.assertTrue(seen["tq2"])
        self.assertTrue(seen["ephemeral"])
        self.assertIn(r["words"]["one"], seen["said"])
        self.assertEqual((seen["atRisk"], seen["note"], seen["hold"]), (False, "", False))
        self.assertEqual(seen["device"], ["tq2"])
        # the next loss: tq2's sound was kept, so it is saved again; tq1 stays lost
        self.assertEqual(r["again"], {"list": [["tq2", True, False], ["tq1", False, True]], "device": ["tq2"]})
        self.assertEqual(r["back"], [["tq2", True, False], ["tq1", False, True]])
        self.assertEqual(r["removed"], ["tq2"])
        self.assertEqual(r["cleared"], {"list": [["tw1", False, True]], "lost": True, "said": [r["words"]["one"]]})


class OneTake(Store):
    def test_stop_finishing_while_the_list_is_read_again_keeps_one_take(self):
        # A2 (r10 correctness F1): Stop is still finishing — its last write failed once and waits to be tried again — when
        # the list is read again (Try again, Back): the take's own draft is not adopted as a "Recovered recording" (this
        # page holds its lock) — one take, one id, all its sound
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          await feed(P, kit, 4);
          const blocks = kit.i;
          W.idb.fail({ op: "put", store: "sound", name: "UnknownError", times: 1 });
          P.C.stop(true);
          await W.tick(100);
          P.C.load();                                         // (as "Try again" or Back would, meanwhile)
          await W.until(() => P.C.state === "idle" && P.C.takes.length > 0 && P.C.takes.every((t) => t.saved), 30000);
          await W.idle();
          out({ list: view(P.C).map((t) => [t.id === id, t.src, t.samples]), notice: P.C.notice,
            rows: device(W).takes.map((x) => [x.id === id, x.draft, x.src, x.samples]), bytes: total(rows(W, id, "pcm")), blocks,
            locks: W.locks.names(), health: health(W) });""")
        n = r["blocks"]
        self.assertEqual(r["list"], [[True, "mic", n * 4096]])
        self.assertNotEqual(r["notice"], "recovered")
        self.assertEqual(r["rows"], [[True, False, "mic", n * 4096]])
        self.assertEqual(r["bytes"], n * 4096 * 2)
        self.assertEqual(r["locks"], [])

    def test_a_take_added_twice_with_one_id_is_listed_once(self):
        # A2: add() replaces a take listed with the same id — never two entries, never two writes of one take at once
        r = self.run_pages(r"""
          const W = createWorld(); W.idb.latency = 20;""" + LOADED + r"""
          const a = P.C.add(meta(W, "tsame", 2), sound(2)), b = P.C.add(meta(W, "tsame", 3), sound(3, 1000));
          const ids = P.C.takes.map((t) => t.id);
          const oks = [await W.wait(a), await W.wait(b)];
          await W.idle();
          const x = row(W, "tsame");
          out({ ids, oks, after: P.C.takes.map((t) => [t.id, t.saved, t.samples]), row: [x.draft, x.samples, x.size, x.mp3],
            pcm: total(rows(W, "tsame", "pcm")), mp3: total(rows(W, "tsame", "mp3")), health: health(W) });""")
        self.assertEqual(r["ids"], ["tsame"])
        self.assertEqual(r["oks"], [False, True])                     # the first write stopped (replaced); the second saved it
        self.assertEqual(r["after"], [["tsame", True, 3 * 44100]])
        self.assertEqual(r["row"], [False, 3 * 44100, 3 * 44100 * 2 + 1000, True])
        self.assertEqual((r["pcm"], r["mp3"]), (3 * 44100 * 2, 1000))


class Records(Store):
    def test_a_star_or_a_name_never_brings_back_a_take_deleted_in_another_tab(self):
        # A3 (r10 F2): tab B still shows a take tab A deleted; a star or a new name in B writes nothing back (no "damaged"
        # ghost), and changes only the name / star of a take that is there
        r = self.run_pages(r"""
          const W = createWorld();
          const A = page(W, { label: "tab A" });
          await W.until(() => A.C.loaded); await W.idle();
          await W.wait(A.C.add(meta(W, "tx1", 1), sound(1, 2000)));
          await W.wait(A.C.add(meta(W, "tx2", 1, { n: 2, created: W.now + 1 }), sound(1)));
          await W.idle();
          const B = page(W, { label: "tab B" });
          await W.until(() => B.C.loaded); await W.idle();
          A.C.remove(A.C.find("tx1"));
          await W.idle();
          B.C.star(B.C.find("tx1"));
          B.C.renameId = "tx1"; B.C.renameText = "My story"; B.C.saveRename(B.C.find("tx1"));
          B.C.renameId = "tx2"; B.C.renameText = "Kept"; B.C.saveRename(B.C.find("tx2"));
          await W.idle();
          const d = device(W);
          const C = page(W, { label: "tab C" });
          await W.until(() => C.C.loaded); await W.idle();
          out({ rows: d.takes.map((x) => [x.id, x.name, x.starred, x.v, x.mp3, x.size]), sound: [...new Set(d.sound.map((x) => x.id))],
            next: view(C.C).map((t) => [t.id, t.saved, t.damaged, t.name]), health: health(W) });""")
        self.assertEqual(r["rows"], [["tx2", "Kept", False, 2, False, 44100 * 2]])
        self.assertEqual(r["sound"], ["tx2"])
        self.assertEqual(r["next"], [["tx2", True, False, "Kept"]])

    def test_a_v1_record_written_back_over_a_moved_take_is_put_right(self):
        # A3 (r10 F2): a page that still showed a take as v1 wrote its record back after another page moved its sound to
        # the new store (the Blobs gone): it is listed — not damaged —, plays from its rows, and its record is v2 again;
        # a rename then changes the name only
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          await W.wait(P.C.add(meta(W, "tv5", 2, { name: "Mi toma" }), sound(2, 3000)));
          P.leave();
          const takes = W.idb.database(DB).store("takes");
          takes.put(Object.assign({}, takes.get("tv5"), { v: 1, mp3: false, size: 0, starred: true }));   // (R.clean of a v1 take)
          const P2 = page(W, { label: "page 2" });
          await W.until(() => P2.C.loaded); await W.idle();
          const x = row(W, "tv5");
          const list = view(P2.C).map((t) => [t.id, t.saved, t.damaged, t.url, t.mp3Size, t.v, t.name, t.starred]);
          P2.C.renameId = "tv5"; P2.C.renameText = "Gratitud"; P2.C.saveRename(P2.C.find("tv5"));
          await W.idle();
          const y = row(W, "tv5");
          out({ list, row: [x.v, x.mp3, x.size, x.name, x.starred, x.draft], renamed: [y.v, y.mp3, y.size, y.name, y.starred],
            sound: rows(W, "tv5").map((s) => s.k), health: health(W) });""")
        size = 2 * 44100 * 2 + 3000
        self.assertEqual(r["list"], [["tv5", True, False, True, 3000, 2, "Mi toma", True]])
        self.assertEqual(r["row"], [2, True, size, "Mi toma", True, False])
        self.assertEqual(r["renamed"], [2, True, size, "Gratitud", True])
        self.assertEqual(r["sound"], ["tv5:mp3:000000", "tv5:pcm:000000"])

    def test_an_mp3_made_after_the_take_was_deleted_in_another_tab_is_not_stored(self):
        # A3 (r10 F2): tab B makes a take's MP3 (here once back online) after tab A deleted the take: B's MP3 is made, but
        # nothing is written — the take does not come back with MP3 rows and no PCM
        r = self.run_pages(r"""
          const W = createWorld(); W.storage.private = true;
          const A = page(W, { label: "tab A", ua: UA.iphone });
          await W.until(() => A.C.loaded); await W.idle();
          await W.wait(A.C.add(meta(W, "tm1", 2), sound(2)));         // (tab A has no encoder: kept as a WAV)
          await W.idle();
          let online = false;
          const enc = encoderKit();
          enc.fetch = () => Promise.resolve({ ok: online, status: online ? 200 : 503, arrayBuffer: () => Promise.resolve(new ArrayBuffer(16)) });
          const B = page(W, { label: "tab B", ua: UA.iphone, encoder: enc });
          await W.until(() => B.C.loaded); await W.idle();
          const before = { mp3Fail: B.C.mp3Fail, mp3Size: B.C.find("tm1").mp3Size, priv: B.C.priv };
          A.C.remove(A.C.find("tm1"));
          await W.idle();
          online = true;
          for (const l of B.win.online || []) l.fn({ type: "online" });
          await W.until(() => B.C.find("tm1").mp3Size > 0, 10000); await W.idle();
          const d = device(W);
          out({ before, made: B.C.find("tm1").mp3Size, rows: d.takes.map((x) => x.id), sound: d.sound.map((x) => x.k),
            bPuts: W.idb.log.filter((e) => e.client === "tab B" && e.op === "put").length, health: health(W) });""")
        self.assertEqual(r["before"], {"mp3Fail": True, "mp3Size": 0, "priv": True})
        self.assertGreater(r["made"], 0)                               # the MP3 was made in tab B…
        self.assertEqual((r["rows"], r["sound"], r["bPuts"]), ([], [], 0))   # …and not written: the take is gone


class KeepSwitch(Store):
    def test_keep_off_and_on_during_a_write_leaves_the_take_whole(self):
        # A4 (r10 correctness F3): a take not saved yet is being written again (Try again, slow storage) when "Keep" goes
        # off and on: the write in flight ends first — off quickly: it goes on and saves the take; off for longer: it
        # stops and its rows go — and the take is saved whole, its PCM rows numbered from 0 with none missing
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          async function run(id, offFor) {
            const f = W.idb.fail({ op: "put", store: "sound", match: (i) => String(i.key).startsWith(id + ":pcm:") });
            await W.wait(P.C.add(meta(W, id, 60, { created: W.now }), sound(60)));
            await W.idle();
            const failed = P.C.find(id).failed;
            f.off();
            W.idb.latency = 300;
            P.C.retry();
            // (its second write — rows 4 and 5 — on its way: the first one, rows 0–3, is on the device)
            await W.until(() => W.idb.log.some((e) => e.key === id + ":pcm:000004"), 20000);
            const midway = P.C.find(id).saving && W.idb.log.some((e) => e.key === id + ":pcm:000003" && e.committed);
            P.C.setKeep(false);
            if (offFor) await W.tick(offFor);
            P.C.setKeep(true);
            let whenSaved = null;
            await W.until(() => {
              const t = P.C.find(id);
              if (t && t.saved && !whenSaved) whenSaved = { seqs: rows(W, id, "pcm").map((x) => x.seq), bytes: total(rows(W, id, "pcm")), draft: !!row(W, id) && row(W, id).draft };
              return !!whenSaved;
            }, 60000);
            await W.idle();
            W.idb.latency = 0;
            return { failed, midway, whenSaved, after: { seqs: rows(W, id, "pcm").map((x) => x.seq), bytes: total(rows(W, id, "pcm")), draft: row(W, id).draft },
              keep: P.C.keep };
          }
          const quick = await run("tkq", 100), slow = await run("tks", 3000);     // (off 0.1 s: a double tap; 3 s)
          out({ quick, slow, list: view(P.C).map((t) => [t.id, t.saved]), health: health(W) });""")
        whole = {"seqs": [0, 1, 2, 3, 4, 5], "bytes": 60 * 44100 * 2, "draft": False}
        for k in ("quick", "slow"):
            with self.subTest(off=k):
                v = r[k]
                self.assertEqual((v["failed"], v["midway"], v["keep"]), (True, True, True))
                self.assertEqual(v["whenSaved"], whole)                # whole the moment it shows "saved"
                self.assertEqual(v["after"], whole)
        self.assertEqual(sorted(r["list"]), [["tkq", True], ["tks", True]])

    def test_the_stopped_writes_drop_tried_again_never_wipes_a_newer_write(self):
        # r10 N5: "Keep" off stops a take's write, whose leftovers are dropped — that drop fails once (a passing error) and
        # is tried again 250 ms later; meanwhile "Keep" is on again and a new write of the take has begun: the drop's
        # second try stops, so the new write's first rows stay and the take is whole when it says "saved"
        r = self.run_pages(r"""
          const W = createWorld(); W.idb.latency = 40;""" + LOADED + r"""
          const p = P.C.add(meta(W, "tk1", 60), sound(60, 9000));
          await W.until(() => rows(W, "tk1", "pcm").length >= 4, 20000);
          const f = W.idb.fail({ op: "delete", store: "takes", name: "UnknownError", times: 1 });
          P.C.setKeep(false);
          const stopped = await W.wait(p);
          const off = view(P.C).map((t) => [t.id, t.saved]);
          P.C.setKeep(true);
          let whenSaved = null;
          await W.until(() => {
            const t = P.C.find("tk1");
            if (t && t.saved && !whenSaved) whenSaved = { seqs: rows(W, "tk1", "pcm").map((x) => x.seq), bytes: total(rows(W, "tk1", "pcm")) };
            return !!whenSaved;
          }, 60000);
          await W.tick(5000); await W.idle();
          const x = row(W, "tk1");
          out({ stopped, off, whenSaved, after: { seqs: rows(W, "tk1", "pcm").map((s) => s.seq), bytes: total(rows(W, "tk1", "pcm")),
            mp3: total(rows(W, "tk1", "mp3")), rec: [x.draft, x.samples] }, list: view(P.C).map((t) => [t.id, t.saved]), dropFailed: f.hits,
            health: health(W) });""")
        whole = {"seqs": [0, 1, 2, 3, 4, 5], "bytes": 60 * 44100 * 2}
        self.assertFalse(r["stopped"])
        self.assertEqual(r["off"], [["tk1", False]])
        self.assertEqual(r["dropFailed"], 1)                            # (the drop did fail once, and was tried again)
        self.assertEqual(r["whenSaved"], whole)
        self.assertEqual(r["after"], dict(whole, mp3=9000, rec=[False, 60 * 44100]))
        self.assertEqual(r["list"], [["tk1", True]])

    def test_keep_off_takes_back_the_notice_about_a_take_not_saved(self):
        # r10 V5: Stop's save failed — the deck's notice says "Take 1 isn't saved on this device yet — see Your takes".
        # "Keep" off: nothing below says so any more (no badge, no box) and nothing will be tried — the notice goes; on
        # again with the write still failing, the box and what is said tell it again
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === id && i.value.draft === false, name: "UnknownError" });
          await feed(P, kit, 2);
          P.C.stop(true);
          await W.until(() => P.C.state === "idle", 30000); await W.tick(100);
          const before = { notice: P.C.notice, saved: P.C.find(id).saved };
          P.C.setKeep(false);
          await W.tick(2000); await W.idle();
          const off = { notice: P.C.notice, note: P.C.storeNote(), keep: P.C.keep };
          P.said.length = 0;
          P.C.setKeep(true);
          await W.tick(3000); await W.idle();
          const on = { note: P.C.storeNote(), said: P.said.includes(P.C.s.st_unsaved), saved: P.C.find(id).saved };
          f.off();
          await W.wait(P.C.retry()); await W.idle();
          out({ before, off, on, end: { saved: P.C.find(id).saved, note: P.C.storeNote() }, health: health(W) });""")
        self.assertEqual(r["before"], {"notice": "unsaved", "saved": False})
        self.assertEqual(r["off"], {"notice": "", "note": "", "keep": False})
        self.assertEqual(r["on"], {"note": "unsaved", "said": True, "saved": False})
        self.assertEqual(r["end"], {"saved": True, "note": ""})


class Retries(Store):
    def test_a_failed_write_is_tried_again_soon_then_every_20_seconds(self):
        # A7: a take whose write failed is tried again 3, 6, 12 and 20 s later, then every 20 s (an iPhone asks nothing
        # before a reload: the sooner the better); A8: when it keeps failing ("transient") while the device can be read,
        # the device is probably full — its size is shown; A14: once it is saved, that is said; and when the page is hidden
        # (or goes: pagehide) a take waiting is tried at once
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const tries = [];
          let t0 = W.now;
          const f = W.idb.fail({ op: "put", store: "takes", name: "UnknownError",
            match: (i) => { const hit = !!i.value && i.value.id === "trs" && i.value.draft === false; if (hit) tries.push(W.now - t0); return hit; } });
          await W.wait(P.C.add(meta(W, "trs", 1), sound(1)));
          const failedAt = W.now - t0, sizes1 = P.C.showSizes();
          await W.tick(45000);
          const mid = { note: P.C.storeNote(), sizes: P.C.showSizes(), stuck: P.C.find("trs").stuck, fails: P.C.find("trs").fails };
          f.off();
          P.said.length = 0;
          const h0 = W.now;
          P.hidden();
          const hidden = await W.until(() => P.C.find("trs").saved, 2000);
          const hiddenAfter = W.now - h0;
          P.visible();
          await W.idle();
          const saidSaved = P.said.includes(P.C.t("a_saved", { name: "Take 1", time: P.R.spoken(1, P.C.s.words) }));
          // the page goes (pagehide) while another take waits: tried at once
          const g = W.idb.fail({ op: "put", store: "takes", name: "UnknownError", match: (i) => !!i.value && i.value.id === "trp" && i.value.draft === false });
          await W.wait(P.C.add(meta(W, "trp", 1, { n: 2, created: W.now }), sound(1)));
          g.off();
          for (const l of P.win.pagehide || []) l.fn({ type: "pagehide", persisted: false });
          const pagehide = await W.until(() => P.C.find("trp").saved, 2000);
          out({ tries, failedAt, sizes1, mid, hidden, hiddenAfter, saidSaved, pagehide, after: { sizes: P.C.showSizes(), note: P.C.storeNote() }, health: health(W) });""")
        rounds = []                                                     # (tries 0, 250 ms and 1.25 s into a round)
        for t in r["tries"]:
            if not rounds or t - rounds[-1][-1] > 1500:
                rounds.append([t])
            else:
                rounds[-1].append(t)
        self.assertEqual([len(x) for x in rounds], [3] * len(rounds))   # each round: attempt()'s three tries
        starts = [round((x[0] - r["failedAt"]) / 1000) for x in rounds[1:]]
        self.assertEqual(starts, [3, 6, 12, 20, 40])                   # then every 20 s
        self.assertFalse(r["sizes1"])                                   # one failed write: not a full device yet
        self.assertEqual(r["mid"], {"note": "unsaved", "sizes": True, "stuck": True, "fails": 6})
        self.assertTrue(r["hidden"])
        self.assertLess(r["hiddenAfter"], 1000)
        self.assertTrue(r["saidSaved"])
        self.assertTrue(r["pagehide"])
        self.assertEqual(r["after"], {"sizes": False, "note": ""})

    def test_a_take_stop_could_not_save_is_pointed_at_by_the_main_button(self):
        # A12 (r10 ui UI-1): Stop's save failed — the deck's notice by the main button says so (the takes' box is far below
        # on a phone), through the next Start, until the take is saved
        r = self.run_pages(r"""
          const W = createWorld();""" + RECORD + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === id && i.value.draft === false, name: "UnknownError" });
          await feed(P, kit, 2);
          P.C.stop(true);
          await W.until(() => P.C.state === "idle", 30000); await W.tick(100);
          const after = { notice: P.C.notice, name: P.C.noticeName(), saved: P.C.find(id).saved };
          P.C.open("record");
          await W.until(() => P.C.state === "recording", 10000);
          const during = P.C.notice;
          f.off();
          P.C.stop(false);
          await W.wait(P.C.retry());
          await W.idle();
          out({ after, during, end: { notice: P.C.notice, saved: P.C.find(id).saved }, health: health(W) });""")
        self.assertEqual(r["after"], {"notice": "unsaved", "name": "Take 1", "saved": False})
        self.assertEqual(r["during"], "unsaved")
        self.assertEqual(r["end"], {"notice": "", "saved": True})

    def test_try_again_that_fails_again_says_so(self):
        # r10 V6: "Try again" that fails again changes nothing the box says (its live region stays quiet): the page says
        # so in other words — a take still not saved (it will be tried again), the device's takes still out of reach — and
        # a take that still can't be read is not told to tap the button it just tapped
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", name: "UnknownError", match: (i) => !!i.value && i.value.id === "tf1" && i.value.draft === false });
          await W.wait(P.C.add(meta(W, "tf1", 1), sound(1)));
          P.said.length = 0;
          await W.wait(P.C.retry());
          const unsaved = { note: P.C.storeNote(), said: P.said.slice() };
          f.off();
          P.said.length = 0;
          await W.wait(P.C.retry());
          const worked = { note: P.C.storeNote(), said: P.said.slice() };
          // the list can't be read: "reload"; Try again, still failing
          P.leave();
          const g = W.idb.fail({ op: "getAll", store: "takes", name: "UnknownError" });
          const P2 = page(W, { label: "page 2" });
          await W.until(() => P2.C.loaded, 60000); await W.idle();
          const reload1 = P2.C.storeNote();
          await W.wait(P2.C.retry());
          const reload = { before: reload1, note: P2.C.storeNote(), said: P2.said.slice() };
          g.off();
          // a take whose sound can't be read: its Try again, still failing
          const h = W.idb.fail({ op: "read", store: "sound", key: (k) => String(k).startsWith("tf1:"), name: "NotReadableError" });
          P2.leave();
          const P3 = page(W, { label: "page 3" });
          await W.until(() => P3.C.loaded); await W.idle();
          const damaged = P3.C.find("tf1").damaged;
          P3.said.length = 0;
          P3.C.reread(P3.C.find("tf1"));
          await W.tick(3000); await W.idle();
          out({ unsaved, worked, reload, damaged, reread: P3.said.slice(), words: { retry: P.C.s.a_retry_failed, reload: P.C.s.a_reload_failed,
            again: P.C.s.a_damaged_again, saved: P.C.t("a_saved", { name: "Take 1", time: P.R.spoken(1, P.C.s.words) }) }, health: health(W) });""")
        w = r["words"]
        self.assertTrue(all(w.values()))
        self.assertEqual(r["unsaved"], {"note": "unsaved", "said": [w["retry"]]})
        self.assertEqual(r["worked"], {"note": "", "said": [w["saved"]]})
        self.assertEqual(r["reload"], {"before": "reload", "note": "reload", "said": [w["reload"]]})
        self.assertTrue(r["damaged"])
        self.assertEqual(r["reread"], [w["again"]])


class Mending(Store):
    def test_a_database_made_without_its_sound_store_is_mended(self):
        # A10 (r10 storage F6): an old saved copy of the page with today's core made a v2 database with the first
        # recorder's stores and no "sound" — every save failed for good. The page opens it one version up to add what is
        # missing (and a mark that it is still this schema): takes are saved, and every later page opens it
        r = self.run_pages(r"""
          const W = createWorld();
          W.idb.create(DB, 2, { takes: { keyPath: "id" }, pcm: { keyPath: "id" }, mp3: { keyPath: "id" }, parts: { keyPath: "k" } });
          const P = page(W);
          await W.until(() => P.C.loaded); await W.idle();
          const first = { note: P.C.storeNote(), version: device(W).version, stores: device(W).stores };
          const ok = await W.wait(P.C.add(meta(W, "tmd", 1), sound(1, 500)));
          P.leave();
          const P2 = page(W, { label: "page 2" });
          await W.until(() => P2.C.loaded); await W.idle();
          const ok2 = await W.wait(P2.C.add(meta(W, "tmd2", 1, { n: 2, created: W.now + 1 }), sound(1)));
          out({ first, ok, ok2, next: view(P2.C).map((t) => [t.id, t.saved, t.url]), note: P2.C.storeNote(), version: device(W).version,
            opens: W.idb.opens.filter((o) => o.client === "page 2").map((o) => o.version === undefined ? "as it is" : o.version), health: health(W) });""")
        self.assertEqual(r["first"], {"note": "", "version": 3, "stores": ["mended", "mp3", "parts", "pcm", "sound", "takes"]})
        self.assertTrue(r["ok"])
        self.assertTrue(r["ok2"])
        self.assertEqual(r["next"], [["tmd2", True, True], ["tmd", True, True]])
        self.assertEqual((r["note"], r["version"]), ("", 3))
        self.assertEqual(r["opens"], [2, "as it is"])                  # its schema, then the mended database as it is


class Asking(Store):
    def test_an_mp3_being_made_for_a_saved_take_asks_nothing_an_edit_does(self):
        # A15 (r10 F5 / UI-6): making the MP3 of a saved take loses nothing if the page is left — no question, nothing held;
        # an edit (its take not in the list yet) asks; the encoder's files that never come give up after 60 s
        r = self.run_pages(r"""
          const W = createWorld();
          const enc = encoderKit(); let fetched = 0;
          enc.fetch = () => { fetched++; return new Promise(() => {}); };     // (a stalled connection: the .wasm never comes)
          const P = page(W, { encoder: enc });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tmp3", 2), sound(2)));
          await W.tick(100);
          P.tab.answer = () => ({ answer: false, after: 150 });
          const mp3Job = { job: P.C.job && P.C.job.id, recBusy: P.C.recBusy(), atRisk: P.C.atRisk(), hold: P.classes.has("cm-rec-hold"),
            stopped: P.click("/aagrapevine/events/"), dialogs: P.tab.dialogs.length, guard: P.leaveGuard() };
          P.C.edit = { start: 0, end: 1.5, even: false };
          P.C.applyEdit(P.C.find("tmp3"));
          const edit = { recBusy: P.C.recBusy(), hold: P.classes.has("cm-rec-hold"), stopped: P.click("/aagrapevine/events/"), dialogs: P.tab.dialogs.slice() };
          await W.tick(61000);
          const timedOut = { mp3Fail: P.C.mp3Fail, notice: P.C.notice };
          await W.tick(65000);
          out({ fetched, mp3Job, edit, words: P.C.s.leave_rec, timedOut,
            after: { list: view(P.C).map((t) => [t.src, t.saved, t.mp3Size]), recBusy: P.C.recBusy() }, health: health(W) });""")
        self.assertEqual(r["mp3Job"], {"job": "tmp3", "recBusy": False, "atRisk": False, "hold": False, "stopped": False, "dialogs": 0, "guard": 0})
        self.assertEqual((r["edit"]["recBusy"], r["edit"]["hold"], r["edit"]["stopped"]), (True, True, True))
        self.assertEqual(r["edit"]["dialogs"], [r["words"]])
        self.assertEqual(r["timedOut"], {"mp3Fail": True, "notice": "encoder"})
        self.assertEqual(sorted(r["after"]["list"]), [["edit", True, 0], ["file", True, 0]])   # the edit made, as a WAV
        self.assertFalse(r["after"]["recBusy"])
        self.assertGreaterEqual(r["fetched"], 2)

    def test_an_encoder_whose_wasm_never_finishes_coming_gives_up_too(self):
        # r10 N4: the .wasm answers (its headers) but its body never comes — a weak phone connection: the 60 s covers the
        # body as well, so the MP3 job gives up (the takes stay WAV, "encoder" said) and the jobs behind it run: an edit
        # queued meanwhile is made, and nothing is held or asked once it is
        r = self.run_pages(r"""
          const W = createWorld();
          const enc = encoderKit(); let fetched = 0;
          enc.fetch = () => { fetched++; return Promise.resolve({ ok: true, status: 200, arrayBuffer: () => new Promise(() => {}) }); };
          const P = page(W, { encoder: enc });
          await W.until(() => P.C.loaded); await W.idle();
          await W.wait(P.C.add(meta(W, "tw1", 2), sound(2)));
          await W.tick(30000);
          const mid = { job: P.C.job && P.C.job.id, mp3Fail: P.C.mp3Fail };
          P.C.edit = { start: 0, end: 1.5, even: false };
          P.C.applyEdit(P.C.find("tw1"));
          const queued = { recBusy: P.C.recBusy(), hold: P.classes.has("cm-rec-hold") };
          await W.tick(31000);
          const gaveUp = { mp3Fail: P.C.mp3Fail, notice: P.C.notice };
          await W.tick(130000); await W.idle();
          out({ fetched, mid, queued, gaveUp, after: { job: P.C.job, list: view(P.C).map((t) => [t.src, t.saved, t.mp3Size]), recBusy: P.C.recBusy(),
            hold: P.classes.has("cm-rec-hold"), guard: P.leaveGuard() }, health: health(W) });""")
        self.assertEqual(r["mid"], {"job": "tw1", "mp3Fail": False})
        self.assertEqual(r["queued"], {"recBusy": True, "hold": True})
        self.assertEqual(r["gaveUp"], {"mp3Fail": True, "notice": "encoder"})
        self.assertEqual(r["after"], {"job": None, "list": [["edit", True, 0], ["file", True, 0]], "recBusy": False, "hold": False, "guard": 0})
        self.assertGreaterEqual(r["fetched"], 2)                        # (the edit's MP3 asked for the encoder again)

    def test_mail_phone_and_calendar_links_ask_nothing_and_let_the_browser_pass_once(self):
        # A22 (r10 nav F1 / F3): with a take not saved, a plain click on a mailto: / tel: / sms: link or a calendar file
        # (.ics) asks nothing (the page stays) and lets the browser's own question pass for 3 s — after that it asks again
        # by itself (Chrome runs beforeunload for such links, and nothing calls the page back)
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          const f = W.idb.fail({ op: "put", store: "takes", match: (i) => !!i.value && i.value.id === "tml" && i.value.draft === false, name: "UnknownError" });
          await W.wait(P.C.add(meta(W, "tml", 2), sound(2)));
          await W.tick(100);
          P.tab.answer = () => ({ answer: false, after: 150 });
          const res = {}, before = P.unload();
          for (const [k, href] of [["mail", "mailto:gv@example.org?subject=x"], ["tel", "tel:+15555550100"], ["sms", "sms:+15555550100"],
                                   ["ics", "/aagrapevine/events.ics"], ["icsQuery", "/aagrapevine/events.ics?v=2"]]) {
            const stopped = P.click(href), passes = !P.unload();
            await W.tick(3100);
            res[k] = { stopped, passes, later: P.unload() };
          }
          const blank = P.click("mailto:gv@example.org", { target: "_blank" }), blankPasses = !P.unload();
          out({ before, res, blank, blankPasses, dialogs: P.tab.dialogs.length, guard: P.leaveGuard(), health: health(W) });""")
        self.assertTrue(r["before"])
        for k, v in r["res"].items():
            with self.subTest(link=k):
                self.assertEqual(v, {"stopped": False, "passes": True, "later": True})
        self.assertEqual(r["dialogs"], 0)
        self.assertEqual((r["blank"], r["blankPasses"]), (False, False))   # (a new tab: the page is not left; nothing to pass)
        self.assertEqual(r["guard"], 1)

    def test_a_record_link_with_a_modifier_key_is_left_to_the_browser(self):
        # A23 (r10 nav F6): the page's own "#record" links and the cards' "Record it here" scroll — but a ctrl / ⌘ / shift /
        # alt click, another button, or a click something else handled is the browser's (a new tab or window)
        r = self.run_pages(r"""
          const W = createWorld();""" + LOADED + r"""
          let scrolls = 0;
          P.C.$root = { scrollIntoView() { scrolls++; } };
          const plain = P.click("#record"), go = P.click("#recorder", { "data-rec-go": "lv" }), pub = P.C.pub, n = scrolls;
          const mods = { ctrl: P.click("#record", {}, { ctrlKey: true }), meta: P.click("#recorder", { "data-rec-go": "gv" }, { metaKey: true }),
            shift: P.click("#record", {}, { shiftKey: true }), alt: P.click("#record", {}, { altKey: true }), middle: P.click("#record", {}, { button: 1 }) };
          P.click("#record", {}, { defaultPrevented: true });
          out({ plain, go, pub, n, mods, scrolls, pubAfter: P.C.pub, health: health(W) });""")
        self.assertEqual((r["plain"], r["go"], r["pub"], r["n"]), (True, True, "lv", 2))
        self.assertEqual(r["mods"], {"ctrl": False, "meta": False, "shift": False, "alt": False, "middle": False})
        self.assertEqual((r["scrolls"], r["pubAfter"]), (2, "lv"))


class Telling(Store):
    def test_the_this_device_line_fits_the_browser(self):
        # A13 (r10 ui UI-2 / UI-4): a private tab says "until you close it" (never the 7-day rule); Safari on an iPhone
        # names Safari and Files, Chrome / Firefox / Edge there say "this browser", Safari on a Mac says "download it";
        # A21 (UI-11): only Safari is told it is in a private tab (priv: the box) — N3: but every iPhone / iPad browser is
        # asked (getDirectory), and a private tab there keeps the takes' sound in the page (ephemeral) all the same;
        # V1: Chrome, Firefox and Edge on an iPad send a Mac's address line ("Chrome/" / "Firefox/" in it), and DuckDuckGo
        # or Opera on an iPhone a Safari-like one: none of them is Safari; V4: an app's own browser has no line (the
        # warning at the top says recordings made there may not be kept)
        r = self.run_pages(r"""
          const UAS = { criOS: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/140.0.7339.122 Mobile/15E148 Safari/604.1",
            mac: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
            // (tests/test_pwa_install.py's iPad Chrome / Firefox, with a touch screen)
            iPadChrome: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            iPadFirefox: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0",
            iPadEdge: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
            duck: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 DuckDuckGo/7 Safari/605.1.15",
            opera: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 OPT/5.2.0 Safari/604.1",
            iPadSafari: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
            androidApp: "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A.240905.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.83 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/488.0.0.62.79;IABMV/1;]" };
          const res = {}, errors = [];
          for (const [k, ua, priv, o] of [["iphone", UA.iphone, false], ["iphonePrivate", UA.iphone, true], ["criOS", UAS.criOS, false],
                                          ["criOSPrivate", UAS.criOS, true], ["mac", UAS.mac, false], ["chrome", UA.chrome, true],
                                          ["iPadChrome", UAS.iPadChrome, true, { touch: 5 }], ["iPadFirefox", UAS.iPadFirefox, false, { touch: 5 }],
                                          ["iPadEdge", UAS.iPadEdge, false, { touch: 5 }], ["duck", UAS.duck, false, { touch: 5 }],
                                          ["opera", UAS.opera, false, { touch: 5 }], ["iPadSafari", UAS.iPadSafari, false, { touch: 5 }],
                                          ["androidApp", UAS.androidApp, false, { touch: 5, install: true }]]) {
            const W = createWorld(); W.storage.private = priv;
            const P = page(W, Object.assign({ ua }, o || {}));
            await W.until(() => P.C.loaded); await W.idle();
            res[k] = { line: P.C.keptLine(), safari: P.C.safari, ios: P.C.ios, priv: P.C.priv, ephemeral: P.C.ephemeral, note: P.C.storeNote(),
              asked: W.storage.calls.getDirectory };
            if (P.C.inApp) res[k].inApp = true;
            P.leave();
            errors.push(...health(W).errors);
          }
          out({ res, health: { errors, unhandled } });""")
        line = lambda line, safari, ios, asked, priv=False, eph=False, note="": {  # noqa: E731
            "line": line, "safari": safari, "ios": ios, "priv": priv, "ephemeral": eph, "note": note, "asked": asked}
        self.assertEqual(r["res"], {
            "iphone": line("safari", True, True, 1),
            "iphonePrivate": line("private", True, True, 1, priv=True, eph=True, note="private"),
            "criOS": line("browser", False, True, 1),
            "criOSPrivate": line("browser", False, True, 1, eph=True),      # (its sound kept, nothing said: N3, A21)
            "mac": line("mac", True, False, 1),
            "chrome": line("may", False, False, 0),
            "iPadChrome": line("browser", False, True, 1, eph=True),
            "iPadFirefox": line("browser", False, True, 1),
            "iPadEdge": line("browser", False, True, 1),
            "duck": line("browser", False, True, 1),
            "opera": line("browser", False, True, 1),
            "iPadSafari": line("safari", True, True, 1),
            "androidApp": dict(line("", False, False, 0), inApp=True)})
