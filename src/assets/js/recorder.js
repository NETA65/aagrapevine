/* Share your story › "Record it here" — the story recorder (the card at the top of /contribute/#record;
   markup src/_includes/partials/story-recorder.njk, logic src/assets/js/recorder-core.js = window.GVRec).
   Loaded (defer) after app.js and recorder-core.js, before Alpine: the component registers on "alpine:init".
   All user-visible words come from the page (the #rec-config JSON and the markup, rendered from
   src/_i18n/community.json), never from this file.

   HOW IT RECORDS — the microphone (getUserMedia; the browser's voice processing OFF unless "Reduce background
   noise" is on: it pumps and smears a voice in a quiet room) → Web Audio: an AudioWorklet (a Blob URL made
   here, so a saved copy of the page has it offline) posts 4096-sample Float32 blocks; browsers without
   AudioWorklet use a ScriptProcessor. No MediaRecorder: it gives WebM in Chrome / Firefox and MP4 in Safari,
   neither of which the magazines take ("WAV and MP3 files will be accepted"). Each block is kept as 16-bit
   PCM (the WAV) and fed to the MP3 encoder at once (LAME in WebAssembly, assets/vendor/, fetched on the first
   tap and then kept by the service worker), so a take's MP3 is ready the moment it is stopped. A new
   AudioContext per session, at the device's own rate (a forced rate breaks Firefox and old Safari), closed
   and every track stopped after it (iOS plays back through the earpiece while the microphone is open).

   INTERRUPTIONS — a phone call, a locked screen or another app stops the sound (iOS mutes or ends the track,
   or suspends the context): no block for LIMITS.gap seconds, a muted / ended track or a context that is not
   "running" pauses the take, says so, and Resume asks for the microphone again when needed. The screen is
   kept on while recording (Screen Wake Lock, where there is one). The recorder never changes location.hash:
   iOS home-screen apps forget the microphone permission on a hash change (WebKit 215884); the cards' "Record
   it here" links scroll instead.

   WHERE TAKES LIVE — on this device only, nothing is uploaded, and nothing is deleted but by the visitor:
   IndexedDB "gvlv-recorder" v2 — takes = the records (R.clean), sound = the sound as BYTES (ArrayBuffers of at
   most LIMITS.chunkBytes, keyed R.soundKey(id, "pcm" | "mp3", seq)). Never a Blob: Safari's private store
   refuses every Blob value (WebKit 156347) and a normal tab sometimes does too (188438). A take is on the
   device while it is being made: a "draft" record, then every LIMITS.flushEvery seconds (and on pause or when
   the page is hidden) the PCM since the last write; Stop writes the rest of it, then the MP3 and the final
   record — that one transaction is the moment it is saved. Edits and added recordings go the same way (draft,
   all their PCM, final). A page closed or killed mid-take leaves a draft that the next page opens as a
   "Recovered recording"; a take being made or not saved yet holds a Web Lock (LOCK + id), so another tab — and
   this page's own recover() — never takes it for a crashed one. A write that fails is tried again (a few times
   at once, then 3, 6, 12 and 20 s later and every LIMITS.retryEvery seconds, whenever the page is shown or
   hidden, goes online, another take is saved or a take is deleted, and on "Try again"); until it works the take
   stays in this page with all its sound, says "Not saved on this device yet", and leaving asks first — on
   iPhone too (no beforeunload prompt there: in-site link taps are asked in the page). A saved take's sound is
   not kept in the page (read back when needed) — but in a private tab (getDirectory() refused: Safari, or any
   browser on an iPhone or iPad) or once the page saw the browser lose the database, where the device's copy
   may go with a process iOS ends: the page keeps it, checks, and saves it again from its own copy; a saved take
   lost that way with no copy in the page says so ("lost": never "saved"). A write the loss cut short (a take
   being recorded or saved) starts again from its first row in the new database — never just its tail.
   A rename or a star changes only those two fields of the stored record. One unreadable take is shown as such
   (Try again reads it again), never deleted and never hides the others. A v1 database (the first recorder's Blob
   stores pcm, mp3, parts) is read and moved into sound, then its old rows emptied; a database missing a store
   is mended (idb). "Keep my recordings on this device" off (localStorage "gvlv-rec-keep" = "0"): the takes live
   in this page only and leaving asks first.

   SENDING — a take's file (MP3, or WAV: over LIMITS.bigMail it is too big for most e-mail) is made before the
   buttons work: Download is a real <a download> link, Share (navigator.share with the file — Mail, Gmail,
   Drive, Files…) must run inside the tap. E-mail: a mailto: / Gmail / Outlook.com link with the address,
   subject and a message in the magazine's language (a mailto: link cannot attach a file: the page says which
   file to attach), or the magazine's own upload form.

   THE TOPIC — "What will you talk about?" under the magazine (optional): the magazine's own topics in its own
   words (#rec-config topics: the coming issues' themes with their deadlines — the days left counted here, on the
   device: the built page never holds a count —, La Viña's suggested topics), or one the visitor writes. It is
   send.topic — the e-mail's Topic, its subject, and the file's name while the take's Send panel is open, until that
   take's file is first downloaded or shared: from then on the name keeps the topic it had (namedAs), the one of the
   file on the device —, kept in this page only (never stored) and cleared with the e-mail's details. namedAs is page
   memory too (a topic is never stored): after a reload the page no longer knows the saved file's name, and the
   name follows the topic chosen then (README §16: the take is downloaded again). The topics'
   "Record a story on this topic" links (data-rec-go + data-rec-topic) choose it and scroll here.

   THE DEVICE CHECK — "Having trouble? Check this device" (diagnose): what this device and browser can do for the
   recorder, as a report (R.report) the visitor copies or e-mails to the committee themselves. It asks for
   nothing — the microphone's permission is only read, never requested — and names no take: they are counted. */
(function () {
  "use strict";

  var R = window.GVRec;
  if (!R) return;
  var L = R.LIMITS;
  var GV = window.GV || {};

  function announce(m) { if (m && GV.announce) GV.announce(m); }
  function perf() { return window.performance && performance.now ? performance.now() : Date.now(); }
  function yieldNow() { return new Promise(function (r) { setTimeout(r, 0); }); }
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage blocked */ } }
  // a Blob's bytes (FileReader where blob.arrayBuffer is missing: Safari before 14)
  function bufferOf(blob) {
    if (blob.arrayBuffer) return blob.arrayBuffer();
    return new Promise(function (res, rej) {
      var fr = new FileReader();
      fr.onload = function () { res(fr.result); };
      fr.onerror = function () { rej(fr.error); };
      fr.readAsArrayBuffer(blob);
    });
  }
  function revoke(url) { if (url) { try { URL.revokeObjectURL(url); } catch (e) { /* gone */ } } }
  function named(name) { var e = new Error(name); e.name = name; return e; }
  // the take was deleted (or "Keep" switched off) while it was being written: stop, try nothing again
  function gone() { var e = named("GoneError"); e.gone = true; return e; }
  // a typed array's OWN bytes as an ArrayBuffer of exactly that length (IndexedDB would store a view's whole buffer);
  // an ArrayBuffer as it is. (Duck-typed: a buffer from another window or a test's realm is one too.)
  function bytesOf(v) {
    if (!v || typeof v.byteLength !== "number") return null;
    if (v.buffer && typeof v.byteOffset === "number") {
      return v.byteOffset === 0 && v.byteLength === v.buffer.byteLength ? v.buffer : v.buffer.slice(v.byteOffset, v.byteOffset + v.byteLength);
    }
    return v;
  }
  // ArrayBuffers → one
  function join(bufs) {
    if (bufs.length === 1) return bufs[0];
    var n = 0, o = 0;
    bufs.forEach(function (b) { n += b.byteLength; });
    var out = new Uint8Array(n);
    bufs.forEach(function (b) { out.set(new Uint8Array(b), o); o += b.byteLength; });
    return out.buffer;
  }
  // blocks of 16-bit PCM [from, to) → one ArrayBuffer
  function pcmBytes(chunks, from, to) {
    var n = 0, o = 0, i;
    for (i = from; i < to; i++) n += chunks[i].length;
    var out = new Int16Array(n);
    for (i = from; i < to; i++) { out.set(chunks[i], o); o += chunks[i].length; }
    return out.buffer;
  }
  // the encoder's Uint8Array pieces → one ArrayBuffer (null for none)
  function mp3Of(parts) {
    if (!parts || !parts.length) return null;
    return join(parts.map(function (u8) { return bytesOf(u8); }));
  }
  // what a take's player plays: its MP3, else the WAV (a header + its PCM); "" without its sound
  function playUrl(S, t) {
    if (S && S.mp3) return URL.createObjectURL(new Blob([S.mp3], { type: "audio/mpeg" }));
    if (S && S.pcm) return URL.createObjectURL(new Blob([R.wavHeader(t.rate, S.pcm.byteLength >> 1), S.pcm], { type: "audio/wav" }));
    return "";
  }

  /* ------------------------------------------------------------------ IndexedDB */
  // (WHERE TAKES LIVE above. A v1 database keeps its old stores, read only to move takes out of them: the store
  // lists are built from what the database has — a transaction naming a missing store throws.)
  var STORES = ["takes", "sound", "pcm", "mp3", "parts"];
  var PER_TX = 4;                                   // sound rows per transaction when a whole take is written
  // A database whose stores were made by a mismatched page (an old saved copy's recorder.js with today's core made a
  // v2 database without "sound", r10 storage F6) is mended: opened again one version up, which makes what is missing,
  // plus this empty store — the mark that a version past R.SCHEMA is still this schema (raised only to mend it), not a
  // newer page's database. (A newer schema's upgrade must delete it.)
  var MENDED = "mended";
  // seconds after a write of a take failed when it is tried again (then every LIMITS.retryEvery seconds: guard)
  var RETRY_AT = [3, 6, 12, 20];
  var dbP = null;
  function has(d, s) { return d.objectStoreNames.contains(s); }
  function idb() {
    if (dbP) return dbP;
    var p = dbP = new Promise(function (res, rej) {
      if (!window.indexedDB) return rej(named("NotSupportedError"));
      var done = false;
      var end = function (ok, v) { if (done) return false; done = true; clearTimeout(timer); (ok ? res : rej)(v); return true; };
      var shut = function (d) { try { d.close(); } catch (e) { /* closed */ } };
      // an open that never answers (iOS 14.6, or after a lost connection) counts as failed; a late success is closed
      var timer = setTimeout(function () { end(false, named("TimeoutError")); }, L.idbOpen * 1000);
      // ver: the version asked for (0: the one it has — a mended database's); step: how many reopens so far
      function open(ver, step) {
        var r;
        try { r = ver ? indexedDB.open(R.DB_NAME, ver) : indexedDB.open(R.DB_NAME); } catch (e) { end(false, e); return; }
        r.onupgradeneeded = function (e) {
          var d = r.result;
          // the database is new although this page had it open before: the browser lost it (Safari's private store
          // lives in a process iOS ends in the background) — the takes this page thinks are saved are not (A1). E.gen
          // moves on: a write whose first rows went into the old one starts again from its first row (r10 N2); and
          // from now on this page keeps its saved takes' sound (ephemeral), the copy that can save them again (N3)
          if (E.opened && !(e && e.oldVersion)) {
            E.lost = E.lostNow = true;
            E.gen++;
            if (E.vm) E.vm.ephemeral = true;
          }
          if (!has(d, "takes")) d.createObjectStore("takes", { keyPath: "id" });
          if (!has(d, "sound")) d.createObjectStore("sound", { keyPath: "k" });
          if (d.version > R.SCHEMA && !has(d, MENDED)) d.createObjectStore(MENDED);
        };
        r.onsuccess = function () {
          var d = r.result;
          if (done) { shut(d); return; }
          if (d.version > R.SCHEMA && !has(d, MENDED)) { shut(d); end(false, named("VersionError")); return; }   // a newer page's
          if (!(has(d, "takes") && has(d, "sound"))) {
            shut(d);
            if (step < 2) open(d.version + 1, step + 1); else end(false, named("NotFoundError"));
            return;
          }
          // a connection the browser drops (iOS after the app was in the background, site data cleared) or a newer
          // page's upgrade: opened again next time instead of failing every later transaction
          // (in a private tab a dropped connection is how a lost store first shows while the page is on screen: the
          // takes are looked for at once, not at the next focus — a link tapped meanwhile would lose them, r10 repro K2)
          d.onclose = function () {
            if (dbP === p) dbP = null;
            setTimeout(function () { if (E.vm) E.vm.checkLost(true); }, 300);
          };
          d.onversionchange = function () { shut(d); if (dbP === p) dbP = null; };
          E.opened = true; E.dbv = d.version;
          if (!end(true, d)) shut(d);
          else if (E.lostNow) { E.lostNow = false; setTimeout(function () { if (E.vm) E.vm.checkLost(true); }, 0); }
        };
        r.onerror = function (e) {
          // asked for R.SCHEMA, the database is further on: mended by a page like this one (MENDED), or a newer page's
          if (ver && r.error && r.error.name === "VersionError" && step < 2) {
            if (e && e.preventDefault) e.preventDefault();
            open(0, step + 1);
            return;
          }
          end(false, r.error);
        };
        // (onblocked: an older page still has it open; the open goes on once that closes — the timer covers a stall)
      }
      open(E.dbv || R.SCHEMA, 0);
    });
    p["catch"](function () { if (dbP === p) dbP = null; });   // try again next time
    return p;
  }
  // the next transaction opens the database again (a connection that failed may be dead)
  function reset() {
    var p = dbP;
    dbP = null;
    if (p) p.then(function (d) { try { d.close(); } catch (e) { /* closed */ } }, function () {});
  }
  // one transaction over those of `stores` the database has; fn(stores by name, tx) issues its requests at once and
  // may return a request (or {result}) whose result is the answer. A throw in fn aborts it (nothing half-written);
  // the reason is the transaction's error, else the first request's; LIMITS.idbTx seconds without an end: aborted.
  // late: fn issues more requests from its requests' answers (a read, then the write it decides on — one transaction,
  // so nothing can change the record in between): the browser commits it on its own once they are done.
  // A database without "takes" or "sound" (made by a mismatched page): MissingStoreError — the next open mends it.
  function run(stores, mode, fn, late) {
    return idb().then(function (d) {
      return new Promise(function (res, rej) {
        var have = stores.filter(function (s) { return d.objectStoreNames.contains(s); });
        if (stores.some(function (s) { return (s === "takes" || s === "sound") && !has(d, s); })) {
          reset();
          var miss = named("MissingStoreError");
          miss.mend = true;
          return rej(miss);
        }
        if (!have.length) return res(undefined);
        var tx, os = {}, out, first = null, done = false, timer = 0;
        var end = function (ok, v) { if (done) return; done = true; clearTimeout(timer); (ok ? res : rej)(v); };
        try { tx = d.transaction(have, mode); } catch (e) { reset(); return rej(e); }   // (a connection that is closing)
        timer = setTimeout(function () {
          try { tx.abort(); } catch (e) { /* ended */ }
          reset();
          end(false, named("TimeoutError"));
        }, L.idbTx * 1000);
        tx.oncomplete = function () { end(true, out ? out.result : undefined); };
        tx.onerror = function (e) { if (!first) first = (e && e.target && e.target.error) || tx.error; };
        tx.onabort = function () { end(false, tx.error || first || named("AbortError")); };
        try {
          have.forEach(function (s) { os[s] = tx.objectStore(s); });
          out = fn(os, tx);
          // every request is made: the browser need not wait for more (Safari 15, Chrome 76)
          if (mode === "readwrite" && !late && tx.commit) { try { tx.commit(); } catch (e) { /* it commits on its own */ } }
        } catch (e) {
          try { tx.abort(); } catch (x) { /* ended */ }
          end(false, e);
        }
      });
    });
  }
  // fn, again after 250 ms and 1 s when what failed may work next time (R.storeError "transient"), each time over a
  // connection opened again (a database with a store missing: at once, the open mends it); quota, a browser that keeps
  // nothing, a newer database: at once
  function attempt(fn) {
    var waits = [250, 1000];
    function go(i) {
      return Promise.resolve().then(fn)["catch"](function (err) {
        if ((err && err.gone) || R.storeError(err) !== "transient" || i >= waits.length) throw err;
        reset();
        return wait(err && err.mend ? 0 : waits[i]).then(function () { return go(i + 1); });
      });
    }
    return go(0);
  }
  function range(r) { return IDBKeyRange.bound(r[0], r[1]); }
  // a store's records (in key order; no getAll: Safari 10 — a cursor)
  function readAll(store, q) {
    return run([store], "readonly", function (os) {
      if (!os[store]) return null;
      if (os[store].getAll) return q ? os[store].getAll(q) : os[store].getAll();
      var out = { result: [] }, c = q ? os[store].openCursor(q) : os[store].openCursor();
      c.onsuccess = function () { var k = c.result; if (k) { out.result.push(k.value); k["continue"](); } };
      return out;
    });
  }
  function keysOf(store) {
    return run([store], "readonly", function (os) {
      var s = os[store];
      if (!s) return null;
      if (s.getAllKeys) return s.getAllKeys();
      var out = { result: [] }, c = s.openKeyCursor ? s.openKeyCursor() : s.openCursor();
      c.onsuccess = function () { var k = c.result; if (k) { out.result.push(k.key); k["continue"](); } };
      return out;
    });
  }
  // a take's sound rows of one kind [from, to) of `buf`, numbered from seq0 (at most LIMITS.chunkBytes each)
  function soundRows(id, kind, buf, from, to, seq0) {
    return R.split(to - from, L.chunkBytes).map(function (p, i) {
      var a = from + p[0], b = from + p[1];
      return { k: R.soundKey(id, kind, seq0 + i), id: id, kind: kind, seq: seq0 + i,
        buf: a === 0 && b === buf.byteLength ? buf : buf.slice(a, b) };
    });
  }
  function putRows(os, rows) { rows.forEach(function (r) { os.sound.put(r); }); }
  // the record written for a take: R.clean(t) and what this write says (v, draft, mp3, size…)
  function row(t, extra) {
    var r = R.clean(t);
    Object.keys(extra || {}).forEach(function (k) { r[k] = extra[k]; });
    return r;
  }
  // a take, its sound and anything the first recorder kept of it
  function dropIn(os, id) {
    var all = range(R.soundRange(id));
    if (os.takes) os.takes["delete"](id);
    if (os.sound) os.sound["delete"](all);
    if (os.pcm) os.pcm["delete"](id);
    if (os.mp3) os.mp3["delete"](id);
    if (os.parts) os.parts["delete"](all);
  }
  var db = {
    list: function () { return readAll("takes"); },
    // a take's sound of one kind → {buf: its rows' bytes in order, as ONE ArrayBuffer (empty for none), rows: how many}:
    // a cursor copies each row into a buffer made once (hint: the bytes expected — a take's samples × 2), so a long
    // take is never held twice. A row that is not bytes aborts it (the take can't be read).
    bytes: function (id, kind, hint) {
      return run(["sound"], "readonly", function (os, tx) {
        var out = { result: null }, buf = new Uint8Array(Math.max(0, Math.floor(hint) || 0)), at = 0, n = 0;
        var c = os.sound.openCursor(range(R.soundRange(id, kind)));
        c.onsuccess = function () {
          var k = c.result, b = k && k.value && k.value.buf;
          if (!k) { out.result = { buf: at === buf.length ? buf.buffer : buf.buffer.slice(0, at), rows: n }; return; }
          if (!b || typeof b.byteLength !== "number") { try { tx.abort(); } catch (e) { /* ended */ } return; }
          if (at + b.byteLength > buf.length) {
            var more = new Uint8Array(Math.max(at + b.byteLength, buf.length * 2));
            more.set(buf.subarray(0, at));
            buf = more;
          }
          buf.set(new Uint8Array(b), at);
          at += b.byteLength; n++;
          k["continue"]();
        };
        return out;
      });
    },
    // a read and the write it decides on, in one transaction (run's late): fn(stores) reads, and writes from the answer
    update: function (fn) { return run(STORES, "readwrite", fn, true); },
    // the first recorder's Blob of a take ("pcm" | "mp3") → its bytes (null without one)
    legacy: function (store, id) {
      return run([store], "readonly", function (os) { return os[store] ? os[store].get(id) : null; })
        .then(function (r) { return r && r.blob ? bufferOf(r.blob) : null; });
    },
    // one write: fn(stores) puts and deletes
    write: function (fn) { return run(STORES, "readwrite", fn); },
    drop: function (id) { return run(STORES, "readwrite", function (os) { dropIn(os, id); }); }
  };
  // what a write that stopped (the take deleted, "Keep" switched off) put on the device goes — unless a newer write of
  // that take began meanwhile ("Keep" back on: its PLAN): a try 250 ms or 1 s later would wipe that write's first rows,
  // and it would still end "saved" (r10 N5)
  function dropQuiet(id) {
    attempt(function () { if (PLAN[id]) throw gone(); return db.drop(id); })["catch"](function () {});
  }
  // a take's sound → the device, from where P says it got to (P.done bytes of PCM, P.seq the next row; P.clear: its
  // old rows go first): ALL its PCM, a few rows per transaction — so a page closed before the end leaves a draft with
  // its whole sound, which the next page recovers —, then ONE transaction with the MP3 (its rows replaced), finalRow()
  // and the end of anything the first recorder kept of it — the moment the take is on the device. P moves on only with
  // what commits; alive() throws (gone) to stop between transactions.
  // P.gen: the database (E.gen) its rows went into. One that came back new since (the browser lost it, A1) has none of
  // them: the whole sound again from the first row, the rows a write put into the new one deleted first, and the draft
  // record (draftRow(), when given) with them — a write whose open found the database new is not counted either: what it
  // wrote is only the tail (r10 N2).
  function writeSound(id, pcm, mp3, P, finalRow, alive, draftRow) {
    var step = function (fn) { return attempt(function () { alive(); return db.write(fn); }); };
    var batch = L.chunkBytes * PER_TX;
    var fresh = function () {
      if (P.gen === E.gen) return;
      P.gen = E.gen; P.done = 0; P.seq = 0; P.clear = true; P.redraft = !!draftRow;
    };
    function more() {
      fresh();
      if (P.done >= pcm.byteLength) return Promise.resolve();
      var gen = P.gen, end = Math.min(pcm.byteLength, P.done + batch), rows = soundRows(id, "pcm", pcm, P.done, end, P.seq);
      var clear = P.clear, redraft = P.redraft;
      return step(function (os) {
        if (clear) os.sound["delete"](range(R.soundRange(id)));
        if (redraft) os.takes.put(draftRow());
        putRows(os, rows);
      }).then(function () {
        if (gen === E.gen) { P.done = end; P.seq += rows.length; P.clear = P.redraft = false; }
        return more();
      });
    }
    function last() {
      fresh();
      if (P.done < pcm.byteLength) return more().then(last);
      var gen = P.gen, mrows = mp3 ? soundRows(id, "mp3", mp3, 0, mp3.byteLength, 0) : [], clear = P.clear;
      return step(function (os) {
        os.sound["delete"](range(R.soundRange(id, clear ? "" : "mp3")));
        putRows(os, mrows);
        os.takes.put(finalRow());
        if (os.pcm) os.pcm["delete"](id);
        if (os.mp3) os.mp3["delete"](id);
        if (os.parts) os.parts["delete"](range(R.soundRange(id)));
      }).then(function () {
        if (gen !== E.gen) return last();                // (into a new database: all of it again — fresh)
        P.clear = P.redraft = false;
      });
    }
    return more().then(last);
  }
  // a take's sound of one kind read back (its rows; v1: its Blob — or, when that is gone, its rows: a record a stale
  // page wrote back as v1 after the take was moved, r10 F2) → its bytes, null for none
  function readKind(c, kind) {
    var rows = function () {
      return attempt(function () { return db.bytes(c.id, kind, kind === "pcm" ? c.samples * 2 : 0); })
        .then(function (got) { return got && got.rows ? got.buf : null; });
    };
    if (c.v >= 2) return rows();
    return attempt(function () { return db.legacy(kind, c.id); }).then(function (b) { return b || rows(); });
  }
  // a saved take's sound read back → {mp3, pcm}: its MP3, else its PCM (played as a WAV; its MP3 is made again) — both
  // when `both` (a private window: the page's copy is the only one that lasts). Rejects when neither can be read.
  function readSound(c, both) {
    var mp3 = c.v < 2 || c.mp3 ? readKind(c, "mp3")["catch"](function () { return null; }) : Promise.resolve(null);
    return mp3.then(function (b) {
      if (b && b.byteLength && !both) return { mp3: b, pcm: null };
      return readKind(c, "pcm").then(function (p) {
        if (p && p.byteLength) return { mp3: b && b.byteLength ? b : null, pcm: p };
        if (b && b.byteLength) return { mp3: b, pcm: null };
        throw new Error("sound");
      }, function (err) { if (b && b.byteLength) return { mp3: b, pcm: null }; throw err; });
    });
  }

  /* ------------------------------------------------------------------ the MP3 encoder */
  // assets/vendor/wasm-media-encoder.min.js (window.WasmMediaEncoder) + lame-mp3.wasm, fetched on the first
  // tap; the compiled module is kept for every later take. Fails (offline on a first visit, no WebAssembly):
  // the takes stay WAV, and the MP3 is made when it loads.
  var encP = null, encMod = null;
  function loadScript(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement("script");
      s.src = src; s.async = true;
      s.onload = function () { res(); };
      s.onerror = function () { s.remove(); rej(new Error("script")); };
      document.head.appendChild(s);
    });
  }
  // p, or a TimeoutError after `sec` seconds (a stalled connection: the encoder's files never come)
  function within(p, sec) {
    return new Promise(function (res, rej) {
      var t = setTimeout(function () { rej(named("TimeoutError")); }, sec * 1000);
      p.then(function (v) { clearTimeout(t); res(v); }, function (e) { clearTimeout(t); rej(e); });
    });
  }
  // seconds the encoder's script, and its .wasm — the answer AND its body: a weak connection may send the headers and
  // stall (r10 N4) —, may each take; then the MP3 jobs give up (mp3Fail) and the queue moves on
  var ENC_WAIT = 60;
  function encoderReady(cfg) {
    if (encP) return encP;
    encP = new Promise(function (res, rej) {
      if (typeof WebAssembly !== "object" || !cfg || !cfg.enc) return rej(new Error("wasm"));
      var at = function (p) { return GV.url ? GV.url(p) : p; };
      var lib = window.WasmMediaEncoder ? Promise.resolve() : within(loadScript(at(cfg.enc.js)), ENC_WAIT);
      lib.then(function () {
        return within(fetch(at(cfg.enc.wasm)).then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.arrayBuffer(); }), ENC_WAIT);
      })
        .then(function (buf) { return window.WasmMediaEncoder.createEncoder("audio/mpeg", buf, function (m) { encMod = m; }); })
        .then(function () { res(true); }, rej);
    });
    encP.catch(function () { encP = null; });
    return encP;
  }
  function newEncoder(cfg, rate) {
    return encoderReady(cfg).then(function () {
      return window.WasmMediaEncoder.createEncoder("audio/mpeg", encMod);
    }).then(function (enc) {
      enc.configure({ sampleRate: rate, channels: 1, bitrate: L.mp3Kbps, outputSampleRate: L.mp3Rate });
      return enc;
    });
  }
  // the encoder owns the bytes it returns: copy them
  function copyOut(u8) { return u8 && u8.length ? new Uint8Array(u8) : null; }
  // 16-bit PCM → the MP3's bytes, a second of sound at a time, giving the page room between slices
  function encodePcm(cfg, i16, rate, onPct) {
    return newEncoder(cfg, rate).then(function (enc) {
      var parts = [], pos = 0, step = Math.round(rate);
      return new Promise(function (res, rej) {
        (function slice() {
          try {
            var t0 = perf();
            while (pos < i16.length && perf() - t0 < 40) {
              var o = copyOut(enc.encode([R.toFloat32(i16.subarray(pos, Math.min(i16.length, pos + step)))]));
              if (o) parts.push(o);
              pos += step;
            }
            if (onPct) onPct(i16.length ? pos / i16.length : 1);
            if (pos < i16.length) { setTimeout(slice, 0); return; }
            var last = copyOut(enc.finalize());
            if (last) parts.push(last);
            var mp3 = mp3Of(parts);
            if (!mp3) throw new Error("mp3");
            res(mp3);
          } catch (e) { rej(e); }
        })();
      });
    });
  }

  /* ------------------------------------------------------------------ capture */
  // ("stop": process() returns false, so the node ends on its own before its context is closed — closing a context
  // whose worklet is still processing sometimes left Chrome unable to load the next page)
  var WORKLET = [
    "class GVCapture extends AudioWorkletProcessor {",
    "  constructor() { super(); this.b = new Float32Array(4096); this.n = 0; this.on = true;",
    "    this.port.onmessage = function (e) { if (e.data === 'stop') this.on = false; }.bind(this); }",
    "  process(inputs) {",
    "    if (!this.on) return false;",
    "    var ch = inputs[0] && inputs[0][0];",
    "    if (ch) for (var i = 0; i < ch.length; i++) {",
    "      this.b[this.n++] = ch[i];",
    "      if (this.n === 4096) { this.port.postMessage(this.b, [this.b.buffer]); this.b = new Float32Array(4096); this.n = 0; }",
    "    }",
    "    return true;",
    "  }",
    "}",
    "registerProcessor('gv-capture', GVCapture);"
  ].join("\n");
  var workletUrl = null;

  // E: the session (never reactive: Alpine would wrap an AudioContext in a Proxy and break it)
  // (locks: the Web Locks this page holds, by take id — their release functions; own: the ids of takes this page is
  // making that are not in its list yet — Stop finishing the MP3 —, never adopted by its own recover(); opened: this
  // page has had the database open; lost: since then it came back new — the browser lost it, A1; gen: how many times
  // it did (a write, or a saved take, knows the database it went into by it); risky: edits and added recordings
  // running or waiting, whose take is not in the list yet)
  var E = { vm: null, ctx: null, stream: null, src: null, node: null, mute: null, take: null, last: 0, hold: 0,
    win: [], watch: 0, cd: 0, lock: null, after: "", leave: null, locks: {}, own: {}, opened: false, lost: false,
    lostNow: false, gen: 0, dbv: 0, risky: 0, pending: 0, checked: -1e9 };
  // a take's sound in this page, as BYTES (no Blob is kept: Safari keeps a Blob's data in a process iOS may end while
  // the page is in the background): mp3 (ArrayBuffer), pcm (ArrayBuffer of 16-bit samples). A take not saved on the
  // device keeps both. A saved one keeps none — its player's address is enough; Share, Download, an edit and its MP3
  // read them back from the device when they are needed — except in a private window, where it keeps both: there the
  // device's copy goes with the browser's networking process (iOS ends it in the background), and this page's copy
  // is what saves it again (A1; also in another iPhone browser's private tab, or once the page saw the database lost:
  // ephemeral). FILES: the File each format becomes for Share / Download. PLAN: how far a take's write has got
  // (writeSound; one being written keeps it — dropQuiet stops for it). REPLAY: when a take's player last got a new
  // address (replay).
  var SND = {};
  var FILES = {};
  var PLAN = {};
  var REPLAY = {};
  function snd(id) { return SND[id] || (SND[id] = { mp3: null, pcm: null }); }

  function getMic(id, noise) {
    var c = { echoCancellation: !!noise, noiseSuppression: !!noise, autoGainControl: !!noise, channelCount: { ideal: 1 } };
    if (id) c.deviceId = { exact: id };
    return navigator.mediaDevices.getUserMedia({ audio: c }).catch(function (err) {
      // a microphone that has gone (unplugged, a headset's battery) or settings this one can't do: the usual
      // microphone with the SAME voice-processing choice (a plain {audio: true} would turn it all on mid-take),
      // and only then any microphone at all
      if (/Overconstrained|NotFound|ConstraintNotSatisfied/.test(err && err.name) && (id || R.errorKind(err) === "constraint")) {
        if (E.vm && id) E.vm.micId = "";
        delete c.deviceId;
        return navigator.mediaDevices.getUserMedia({ audio: c }).catch(function () {
          return navigator.mediaDevices.getUserMedia({ audio: true });
        });
      }
      throw err;
    });
  }
  function stopStream(s) { if (s) s.getTracks().forEach(function (t) { try { t.stop(); } catch (e) { /* stopped */ } }); }

  // (every step checks the session is still this one: Cancel while the browser was asking closes it)
  function wire(ctx, stream, mode) {
    var src = ctx.createMediaStreamSource(stream);
    // the capture node must reach the speakers to run; through a muted gain, so nothing is heard
    var mute = ctx.createGain();
    mute.gain.value = 0;
    mute.connect(ctx.destination);
    E.src = src; E.mute = mute;
    function viaScript() {
      if (E.ctx !== ctx) return;
      var sp = ctx.createScriptProcessor(4096, 1, 1);
      sp.onaudioprocess = function (ev) { onBlock(new Float32Array(ev.inputBuffer.getChannelData(0))); };
      E.node = sp; src.connect(sp); sp.connect(mute);
    }
    if (mode !== "worklet") { viaScript(); return Promise.resolve(); }
    if (!workletUrl) workletUrl = URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }));
    return ctx.audioWorklet.addModule(workletUrl).then(function () {
      if (E.ctx !== ctx) return;
      var n = new AudioWorkletNode(ctx, "gv-capture", { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1],
        channelCount: 1, channelCountMode: "explicit", channelInterpretation: "speakers" });
      n.port.onmessage = function (ev) { onBlock(ev.data); };
      E.node = n; src.connect(n); n.connect(mute);
    })["catch"](function () { viaScript(); });
  }
  // a new source on the same context (Resume after the track ended)
  function rewire(stream) {
    try { E.src.disconnect(); } catch (e) { /* gone */ }
    E.src = E.ctx.createMediaStreamSource(stream);
    E.src.connect(E.node);
  }

  // one block of sound (Float32, mono) from the microphone
  function onBlock(f32) {
    var vm = E.vm;
    if (!vm || !f32 || !f32.length) return;
    E.last = perf();
    var p = R.peak(f32);
    E.hold = Math.max(p, E.hold * 0.8);          // the meter falls back slowly: a needle, not a flicker
    var m = R.meter(E.hold);
    if (m !== vm.meterPct) vm.meterPct = m;
    E.win.push(p);
    if (E.win.length > 6) E.win.shift();          // the words judge the last half second
    var lv = R.level(Math.max.apply(null, E.win));
    if (lv !== vm.lvl) { vm.lvl = lv; E.lvlAt = E.last; }
    // the test's result, for a screen reader: the words once they have held for a second (never while
    // recording — what is said then goes into the take)
    if (vm.state === "testing" && lv !== E.lvlSaid && E.last - (E.lvlAt || 0) >= 1000) {
      E.lvlSaid = lv;
      announce(vm.s["lv_" + lv]);
    }
    var t = E.take;
    if (!t || vm.state !== "recording") return;
    // nothing but digital zeros: a live microphone never gives them — Android hands a call or another app the
    // microphone and feeds this one silence, with no event; the take pauses as for any interruption
    if (p === 0) {
      if (!E.zeroSince) E.zeroSince = E.last;
      else if (E.last - E.zeroSince > L.zeroFor * 1000) { E.zeroSince = 0; vm.interrupt(); return; }
    } else E.zeroSince = 0;
    t.chunks.push(R.toInt16(f32));
    t.peaks.push(p);
    if (p > t.peak) t.peak = p;
    var before = t.samples / t.rate;
    t.samples += f32.length;
    var sec = t.samples / t.rate;
    vm.sec = sec;
    // the MP3, as it goes (the encoder may still be loading: it catches up)
    if (t.enc && !t.catching && t.encIdx === t.chunks.length - 1) {
      try {
        var o = copyOut(t.enc.encode([f32]));
        if (o) t.mp3.push(o);
        t.encIdx++;
      } catch (e) { t.enc = null; }                // the MP3 is made from the PCM after the take
    } else if (t.enc && !t.catching) catchUp(t);
    R.crossed(before, sec, t.rule).forEach(function (k) { announce(R.fill(vm.s["m_" + k], { time: R.spoken(sec, vm.s.words) })); });
    if (sec >= t.rule.hard) { vm.stop(true, "hard"); return; }
    if (!t.heard && p >= L.silent) { t.heard = true; if (vm.notice === "silent") vm.notice = ""; }
    if (!t.heard && !t.toldSilent && sec >= L.silentFor) { t.toldSilent = true; vm.notice = "silent"; announce(vm.s.n_silent); }
    // (writes that keep failing — the device full — are tried less often: each one copies all the sound not written)
    if (sec - t.flushTry >= L.flushEvery * (1 + Math.min(9, t.flushFails))) flushSound(t);
  }
  // the encoder arrived after the take began: encode the blocks it missed, a few at a time
  function catchUp(t) {
    if (t.catching) return t.catchP;
    if (!t.enc) return Promise.resolve();
    t.catching = true;
    return (t.catchP = new Promise(function (res) {
      (function step() {
        try {
          var t0 = perf();
          while (t.encIdx < t.chunks.length && perf() - t0 < 30) {
            var o = copyOut(t.enc.encode([R.toFloat32(t.chunks[t.encIdx])]));
            if (o) t.mp3.push(o);
            t.encIdx++;
          }
        } catch (e) { t.enc = null; t.catching = false; res(); return; }   // the MP3 is made from the PCM later
        if (t.encIdx < t.chunks.length) { setTimeout(step, 0); return; }
        t.catching = false; res();
      })();
    }));
  }
  // …until every block is in (Stop: no more blocks come)
  function drain(t) {
    return catchUp(t).then(function () { if (t.enc && t.encIdx < t.chunks.length) return drain(t); });
  }
  // the take being recorded → the device: ONE transaction with the PCM since the last write that committed (rows of
  // LIMITS.chunkBytes) and its draft record brought up to date (the first one: the draft alone). One at a time; the
  // place (flushIdx, flushN samples, seq) moves on only when it commits, so a failed write is done again next time
  // with more sound — never lost, never twice. Not once the take is handed to add() (final), nor when the takes are
  // not kept. → the write's promise (t.flushP).
  // t.gen: the database (E.gen) its writes went into. One that came back new since (the browser lost it, A1) has none
  // of them: the next write is all of it again from the first block, the take's rows deleted first (t.clear: a write
  // that went into the new one before the loss was seen put only the tail there); a write whose own open found the
  // database new moves nothing on (r10 N2).
  function flushSound(t) {
    var vm = E.vm;
    if (!t || !vm || t.final || t.flushing || !vm.keep || !vm.kept) return (t && t.flushP) || Promise.resolve();
    if (t.gen !== E.gen) { t.gen = E.gen; t.flushIdx = t.flushN = t.seq = 0; t.drafted = false; t.clear = true; }
    var to = t.chunks.length, gen = t.gen, clear = t.clear;
    if (to <= t.flushIdx && t.drafted) return t.flushP || Promise.resolve();
    t.flushing = true;
    t.flushTry = t.samples / t.rate;
    var buf = to > t.flushIdx ? pcmBytes(t.chunks, t.flushIdx, to) : null;
    var n = t.flushN + (buf ? buf.byteLength >> 1 : 0);
    var rows = buf ? soundRows(t.id, "pcm", buf, 0, buf.byteLength, t.seq) : [];
    var draft = row(record(t), { v: 2, draft: true, mp3: false, samples: n, size: n * 2, at: Date.now() });
    t.flushP = attempt(function () {
      if (t.gone) throw gone();
      return db.write(function (os) { if (clear) os.sound["delete"](range(R.soundRange(t.id))); putRows(os, rows); os.takes.put(draft); });
    }).then(function () {
      if (gen !== E.gen) return;                     // (into a database that came back new: the next write starts over)
      t.flushIdx = Math.max(t.flushIdx, to); t.flushN = n; t.seq += rows.length; t.drafted = true; t.flushFails = 0; t.clear = false;
    }, function () { t.flushFails++; /* the take is still in this page: the next write takes this sound too */ })
      .then(function () { t.flushing = false; });
    return t.flushP;
  }

  function wakeOn() {
    if (E.lock || !("wakeLock" in navigator) || document.visibilityState !== "visible") return;
    try {
      navigator.wakeLock.request("screen").then(function (l) {
        E.lock = l;
        l.addEventListener("release", function () { if (E.lock === l) E.lock = null; });
      })["catch"](function () { /* low battery, or not allowed */ });
    } catch (e) { /* no wake lock */ }
  }
  function wakeOff() { if (E.lock) { try { E.lock.release(); } catch (e) { /* released */ } E.lock = null; } }

  // While a take is being made, saved, or is not saved yet, this page holds a Web Lock named after it: another
  // tab's recover() leaves its draft alone (without Web Locks: a draft written in the last LIMITS.partFresh
  // seconds is left alone instead). lockTake(id, onlyFree) → true once it is this page's (onlyFree: false at once
  // when another tab has it — or this page: a take it is making, saving or dropping is never "free" to recover);
  // always true without Web Locks.
  var LOCK = "gvlv-rec:";
  function hasLocks() { return !!(navigator.locks && navigator.locks.request); }
  function lockTake(id, onlyFree) {
    if (E.locks[id]) return Promise.resolve(!onlyFree);
    if (!hasLocks()) return Promise.resolve(true);
    return new Promise(function (res) {
      try {
        navigator.locks.request(LOCK + id, onlyFree ? { ifAvailable: true } : {}, function (lock) {
          if (!lock) { res(false); return null; }
          return new Promise(function (r) { E.locks[id] = r; res(true); });
        })["catch"](function () { res(false); });
      } catch (e) { res(true); }
    });
  }
  function unlockTake(id) { var r = E.locks[id]; if (r) { delete E.locks[id]; r(); } }
  function heldTakes() {
    if (!navigator.locks || !navigator.locks.query) return Promise.resolve(null);
    return navigator.locks.query().then(function (q) {
      var ids = {};
      (q.held || []).concat(q.pending || []).forEach(function (l) { if (l.name && l.name.indexOf(LOCK) === 0) ids[l.name.slice(LOCK.length)] = true; });
      return ids;
    }, function () { return null; });
  }

  // the take being recorded → the take's record (the sound goes in SND / IndexedDB)
  function record(t, extra) {
    var o = { id: t.id, pub: t.pub, n: t.n, name: "", created: t.created, rate: t.rate, samples: t.samples,
      peak: Math.round(t.peak * 1e4) / 1e4, bins: R.bins(t.peaks), src: t.src || "mic", noise: !!t.noise, starred: false,
      gaps: !!t.gaps, from: t.from || 0 };
    if (extra) Object.keys(extra).forEach(function (k) { o[k] = extra[k]; });
    return o;
  }
  // PCM (Int16Array) → its blocks' peaks (one per 4096 samples), for the waveform
  function peaksOf(i16) {
    var out = [];
    for (var i = 0; i < i16.length; i += 4096) out.push(R.peak(i16.subarray(i, Math.min(i16.length, i + 4096))));
    return out;
  }
  // a context that must run again (Resume, Continue): resume(); one left "interrupted" by iOS sometimes needs a
  // suspend first. → true when it runs.
  function wake(ctx) {
    if (!ctx) return Promise.resolve(false);
    if (ctx.state === "running") return Promise.resolve(true);
    var again = function () { return ctx.resume().then(null, function () {}); };
    return again().then(function () {
      if (ctx.state === "running") return true;
      return ctx.suspend().then(null, function () {}).then(again).then(function () { return ctx.state === "running"; });
    }, function () { return false; });
  }
  // a file's length from its own header (an <audio> element reads only that), within 5 seconds: 0 = unknown
  function probeLength(file) {
    return new Promise(function (res) {
      var a = document.createElement("audio"), url = URL.createObjectURL(file), done = false;
      var end = function (v) { if (done) return; done = true; revoke(url); a.removeAttribute("src"); res(v); };
      a.preload = "metadata";
      a.onloadedmetadata = function () { end(isFinite(a.duration) ? a.duration : 0); };
      a.onerror = function () { end(0); };
      setTimeout(function () { end(0); }, 5000);
      a.src = url;
    });
  }
  // decode a recording the visitor chose (any format the browser plays) at 44.1 kHz
  function decode(buf) {
    var OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    return new Promise(function (res, rej) {
      var oc = new OAC(1, 1, 44100);
      var p = oc.decodeAudioData(buf, res, rej);   // (old Safari: callbacks only)
      if (p && p.then) p.then(res, rej);
    });
  }

  /* ------------------------------------------------------------------ the device check */
  // (THE DEVICE CHECK above.) The microphone's permission as the browser has it — "granted", "denied", "prompt" —, only
  // read (the Permissions API; "" where it can't say: Firefox and older browsers don't know "microphone")
  function micState() {
    try {
      if (!navigator.permissions || !navigator.permissions.query) return Promise.resolve("");
      return navigator.permissions.query({ name: "microphone" }).then(function (p) { return (p && p.state) || ""; }, function () { return ""; });
    } catch (e) { return Promise.resolve(""); }
  }
  // IndexedDB tried as the takes use it — bytes written, then read back — in a database of its own (never the takes'),
  // deleted after → "ok", {code: "failed", more: the error's name}, "none" (no IndexedDB). At most LIMITS.idbOpen seconds.
  var CHECK_DB = "gvlv-rec-check";
  function storageCheck() {
    if (!window.indexedDB) return Promise.resolve("none");
    var drop = function (d) {
      try { if (d) d.close(); } catch (e) { /* closed */ }
      try { indexedDB.deleteDatabase(CHECK_DB); } catch (e) { /* gone */ }
    };
    return within(new Promise(function (res, rej) {
      var r;
      try { r = indexedDB.open(CHECK_DB, 1); } catch (e) { rej(e); return; }
      r.onupgradeneeded = function () { r.result.createObjectStore("check", { keyPath: "k" }); };
      r.onerror = function (e) { if (e && e.preventDefault) e.preventDefault(); rej(r.error || named("UnknownError")); };
      r.onsuccess = function () {
        var d = r.result, end = function (err) { drop(d); if (err) rej(err); else res(); };
        try {
          var w = d.transaction(["check"], "readwrite");
          w.objectStore("check").put({ k: 1, buf: new Uint8Array(64).buffer });
          w.onabort = function () { end(w.error || named("AbortError")); };
          w.oncomplete = function () {
            try {
              var t = d.transaction(["check"], "readonly"), g = t.objectStore("check").get(1);
              t.onabort = function () { end(t.error || named("AbortError")); };
              t.oncomplete = function () { var v = g.result; end(v && v.buf && v.buf.byteLength === 64 ? null : named("DataError")); };
            } catch (e) { end(e); }
          };
        } catch (e) { end(e); }
      };
    }), L.idbOpen).then(function () { return "ok"; }, function (err) {
      return { code: "failed", more: String((err && err.name) || "Error") };
    });
  }

  document.addEventListener("alpine:init", function () {
    window.Alpine.data("storyRecorder", function () {
      return {
        cfg: null,
        s: {},
        can: { record: "", why: "", share: false, wasm: false, import: false },
        inApp: false, ios: false, standalone: false, help: "other",
        safari: false,       // Safari itself (iPhone, iPad, Mac) — not Chrome, Firefox, Edge… on iPhone or iPad, nor an app's browser
        pub: "gv",
        noise: false,
        mics: [], micId: "",
        keep: true,          // the visitor's choice
        kept: true,          // this browser can keep takes at all (false: no IndexedDB, or site data blocked)
        loaded: false,       // the device's takes are listed (the keep switch waits for it)
        reload: false,       // the device's takes could not be listed (or a newer page changed the database)
        full: false,         // the last write that failed found the device full
        priv: false,         // a private window (Safari: kept until it is closed — the "private" box)
        ephemeral: false,    // the browser may lose the device's copy while this page lives (a private tab of any iPhone or
                             // iPad browser, or the page saw the database lost): saved takes keep their sound here too
        persisted: null,     // navigator.storage.persisted(): true = kept until the visitor deletes them
        lowFree: 0,          // the free space "low" told of (bytes)
        lastErr: "",         // the last storage error's name (for a report from a phone)
        maxTakes: L.maxTakes,
        state: "idle",       // idle | asking | testing | countdown | recording | paused | blocked | saving
        count: 0,
        sec: 0,
        meterPct: 0,
        lvl: "",
        notice: "",          // silent | interrupted | limit | recovered | encoder | low | blocked | unsaved
        noticeId: "",        // "unsaved": the take it is about (its name: noticeName())
        error: "",           // R.errorKind, R.support().why, import_big / import_long / import_bad
        confirmDiscard: false,
        confirmKeep: false,  // "Keep my recordings on this device" switched off with takes saved: confirm first
        importErr: "",       // a file that could not be added (shown beside "Add a recording"): import_big / _long / _bad / limit
        mp3Fail: false,      // the MP3 encoder could not load (offline the first time): WAV only for now
        takes: [],           // each: its record + url, mp3Size, saved (on the device), saving (being written), failed
                             // (a write failed: tried again), damaged (its sound can't be read from the device)
        openId: "", panel: "",
        confirmId: "", confirmAll: false,
        renameId: "", renameText: "",
        job: null,           // {id, label, pct}
        send: { pub: "gv", fmt: "mp3", topic: "", name: "", phone: "", email: "", address: "", place: "", credit: "" },
        topicOther: false,   // "Another topic" chosen in the topic list (send.topic is then the visitor's own words)
        namedAs: {},         // take id → the topic in its file's name when that file was first saved (fileName, savedAs)
        prep: { key: "", url: "", size: 0, ready: false, failed: false },
        edit: { start: 0, end: 0, even: false },
        diag: { busy: false, text: "" },   // "Having trouble? Check this device": the report (R.report), while it is made

        init: function () {
          var self = this;
          try { this.cfg = JSON.parse(document.getElementById("rec-config").textContent); } catch (e) { this.cfg = null; }
          if (!this.cfg) return;
          this.s = this.cfg.s || {};
          this.s.words = { min1: this.s.w_min1, min: this.s.w_min, sec1: this.s.w_sec1, sec: this.s.w_sec };
          this.pub = this.cfg.pub === "lv" ? "lv" : "gv";
          this.send.pub = this.pub;
          var ua = navigator.userAgent || "", touch = navigator.maxTouchPoints || 0;
          try {
            var small = Math.min(screen.width, screen.height) < 600;
            this.inApp = !!(window.GVInstall && window.GVInstall.detect(ua, { touch: touch, small: small }).inApp);
          } catch (e) { this.inApp = false; }
          this.help = R.helpFor(ua, touch);
          this.ios = this.help === "ios";
          // (the other iPhone and iPad browsers: install-core.js IOS_OTHER's list — on an iPad, Chrome, Firefox and Edge
          // send a Mac's address line, "Chrome/" or "Firefox/" in it; a Mac's Chrome, Firefox or Edge are not help
          // "safari" at all. Its own copy: GVInstall may not have loaded, and Safari's private check depends on it.)
          this.safari = (this.ios || this.help === "safari") && !this.inApp &&
            !/\b(CriOS|FxiOS|EdgiOS|OPiOS|OPT|YaBrowser|DuckDuckGo|Firefox|Chrome|Edg)\//.test(ua);
          try { this.standalone = navigator.standalone === true || window.matchMedia("(display-mode: standalone)").matches; } catch (e) { /* old */ }
          var AC = window.AudioContext || window.webkitAudioContext;
          var sup = R.support({
            secure: window.isSecureContext !== false,
            media: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
            audio: !!AC,
            worklet: !!(AC && window.AudioWorkletNode && AC.prototype && "audioWorklet" in AC.prototype),
            script: !!(AC && AC.prototype && AC.prototype.createScriptProcessor)
          });
          this.can.record = sup.record;
          this.can.why = sup.why;
          if (!sup.record) this.error = sup.why;            // said before any tap, with the other ways
          this.can.wasm = typeof WebAssembly === "object";
          this.can.import = !!(window.OfflineAudioContext || window.webkitOfflineAudioContext);
          try {
            this.can.share = !!(navigator.share && navigator.canShare &&
              navigator.canShare({ files: [new File([new Uint8Array(4)], "test.mp3", { type: "audio/mpeg" })] }));
          } catch (e) { this.can.share = false; }
          this.keep = lsGet(R.KEEP_KEY) !== "0";
          E.vm = this;
          this.checkStorage();
          this.load();
          // the page goes, or is hidden: the sound so far to the device, and a take waiting to be saved tried once more
          // (best effort: Chrome often finishes it, Safari ends the page first)
          window.addEventListener("pagehide", function () { flushSound(E.take); self.retryAll(); });
          document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "hidden") {
              flushSound(E.take);
              self.retryAll();
              // a phone: another app or a call takes the microphone (Android feeds this page silence, iOS stops
              // it): pause, as the page says. A computer keeps recording (notes in another tab).
              if ((self.help === "ios" || self.help === "android") && self.state === "recording") self.interrupt();
            } else {
              if (self.state === "recording" || self.state === "paused") wakeOn();
              self.retryAll();
              self.checkLost();
            }
          });
          // back from another page by Back (the back-forward cache): the list as the device has it now (another page or
          // tab may have changed it), the takes only in this page kept, and their writes tried again
          window.addEventListener("pageshow", function (e) {
            E.letGo = 0;
            if (e && e.persisted) self.load(); else { self.retryAll(); self.checkLost(); }
            self.guard();
          });
          window.addEventListener("focus", function () { self.retryAll(); self.checkLost(); });
          // back online: the MP3s that could not be made (the encoder needs the network once), and the writes
          window.addEventListener("online", function () {
            if (self.notice === "encoder") self.notice = "";
            self.mp3Fail = false;
            self.takes.forEach(function (t) { if (!t.mp3Size && !t.damaged) self.makeMp3(t.id); });
            self.retryAll();
          });
          // the cards' "Record it here" links (data-rec-go="gv" | "lv"; "" keeps the magazine chosen; data-rec-topic: La
          // Viña's topics' "Record a story on this topic" choose that topic too), and the page's own #record links (the
          // page menu, the hero's card): a scroll, never a change of address
          // (a click with a modifier key or another button opens a new tab or window, as the browser does it)
          document.addEventListener("click", function (e) {
            if (e.defaultPrevented || e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
            var a = e.target && e.target.closest ? e.target.closest("[data-rec-go]") || e.target.closest('a[href="#record"]') : null;
            if (!a) return;
            e.preventDefault();
            self.go(a.getAttribute("data-rec-go"), a.getAttribute("data-rec-topic"));
          });
          // leaving by a link while a take is being made or is not saved on this device: asked first, in the page —
          // an iPhone shows no question on beforeunload (a click handler's confirm() works there)
          document.addEventListener("click", function (e) { self.askLeave(e); }, true);
        },

        /* ---------------- words and numbers for the markup */
        t: function (k, vars) { return R.fill(this.s[k] || "", vars); },
        clock: function (sec) { return R.clock(sec); },
        size: function (b) { return GV.fileSize ? GV.fileSize(b) : Math.round(b / 1048576) + " MB"; },
        ruleOf: function (pub) { return R.rule(this.cfg && this.cfg.pubs[pub]); },
        rec: function () { return this.state === "recording" || this.state === "paused"; },
        busy: function () { return this.state !== "idle" && this.state !== "testing"; },
        // a take is being made or written, or an edit or an added recording is being made (running or waiting: its take
        // is not in the list yet) — what leaving would cut short. (Not an MP3 being made for a take: a saved one loses
        // nothing — it is made again next visit —, an unsaved one is atRisk anyway.)
        recBusy: function () {
          return ["asking", "countdown", "recording", "paused", "saving"].indexOf(this.state) >= 0 || E.risky > 0;
        },
        // …or a take is only in this page
        atRisk: function () { return this.recBusy() || this.takes.some(function (t) { return !t.saved && !t.damaged; }); },
        // what the lasting storage box says (D5): "none" (keep on, but this browser keeps nothing), "reload" (the
        // device's takes can't be reached), "full" (a take isn't saved: no room), "unsaved" (a write failed: tried
        // again), "private" (a private window: kept until it closes), or nothing
        storeNote: function () {
          if (!this.keep) return "";
          if (!this.kept) return "none";
          if (this.reload) return "reload";
          var waiting = this.takes.some(function (t) { return !t.saved && !t.damaged && t.failed; });
          if (waiting) return this.full ? "full" : "unsaved";
          return this.priv ? "private" : "";
        },
        // the "This device" box's line on how long the browser keeps them: "private" (a private tab or window: at most
        // until it is closed), "yes" (persisted), the 7-day rule of a tab on an iPhone or iPad — "safari" (Safari),
        // "browser" (Chrome, Firefox, Edge… there: "this browser") — or on a Mac ("mac"), "may" (elsewhere; it names a
        // private or Incognito window too: never detected there, r10 V4); none while they are not kept, nor in an app's
        // browser (the warning at the top says they may not be kept)
        keptLine: function () {
          if (!this.keep || !this.kept || this.inApp) return "";
          if (this.priv) return "private";
          if (this.persisted === true) return "yes";
          if (this.standalone) return "may";
          if (this.ios) return this.safari ? "safari" : "browser";
          return this.help === "safari" ? "mac" : "may";
        },
        // each take's size on the device, while room is short — or looks it: a take whose write keeps failing while the
        // device can still be read (a full iPhone says UnknownError, not QuotaExceededError: r10 storage F3)
        showSizes: function () {
          return this.notice === "low" || this.storeNote() === "full" ||
            this.takes.some(function (t) { return t.stuck && !t.saved && !t.damaged; });
        },
        // the take the "unsaved" notice is about
        noticeName: function () { var t = this.find(this.noticeId); return t ? this.name(t) : ""; },
        takeSize: function (t) { return t.size || (t.samples * 2 + (t.mp3Size || 0)); },
        // "rest" (no take yet: the line gives the magazine's length), else R.zone
        zone: function () { return this.rec() ? R.zone(this.sec, this.ruleOf(E.take ? E.take.pub : this.pub)) : "rest"; },
        barPct: function () { return R.pct(this.sec, this.ruleOf(E.take ? E.take.pub : this.pub)); },
        markPct: function (which) {
          var r = this.ruleOf(this.pub);
          return r[which] ? R.pct(r[which], r) : -1;
        },
        name: function (t) { return t.name || this.t("take", { n: t.n }); },
        dur: function (t) { return R.clock(R.duration(t)); },
        durSpoken: function (t) { return R.spoken(R.duration(t), this.s.words); },
        // a take against a magazine's length: its own, or (in its Send panel) the one it is being sent to
        verdict: function (t, pub) { return R.verdict(R.duration(t), this.ruleOf(pub || t.pub)); },
        wave: function (t) { return R.wavePath(t.bins, 240, 40); },
        when: function (t) {
          try {
            return new Intl.DateTimeFormat(this.cfg.locale, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(t.created));
          } catch (e) { return ""; }
        },
        quiet: function (t) { return t.peak > 0 && t.peak < L.quiet; },
        loud: function (t) { return t.peak >= L.clip; },
        // the file is named after the magazine it goes to (the Send panel's choice while it is open) and, there, the topic
        // — the one it had when the take's file was first saved (Download, Share, Save to Files: savedAs), so a topic
        // typed in "Details for the email" afterwards never names a file the member does not have
        fileName: function (t, fmt) {
          var open = this.openId === t.id && this.panel === "send", pub = open ? this.send.pub : t.pub;
          var topic = !open ? "" : Object.prototype.hasOwnProperty.call(this.namedAs, t.id) ? this.namedAs[t.id] : this.send.topic;
          return R.fileName(pub === t.pub ? t : Object.assign({}, t, { pub: pub }), fmt || "mp3", topic);
        },
        // the take's file left the page under its name: that name's topic stays the file's (this page only)
        savedAs: function (t, topic) {
          if (Object.prototype.hasOwnProperty.call(this.namedAs, t.id)) return;
          var o = {};
          for (var k in this.namedAs) if (Object.prototype.hasOwnProperty.call(this.namedAs, k)) o[k] = this.namedAs[k];
          o[t.id] = topic === undefined ? this.send.topic : topic;
          this.namedAs = o;
        },
        // the take whose MP3 is being made right now
        making: function (t) { return !!(this.job && this.job.id === t.id); },

        /* ---------------- the magazine and the "Record it here" links */
        // (a topic from the other magazine's list goes with it — its words, its themes; one the visitor wrote stays)
        setPub: function (p) {
          if (this.rec() || this.state === "countdown") return;
          var was = this.pub;
          this.pub = p === "lv" ? "lv" : "gv";
          if (was !== this.pub && !this.topicOther && this.topicIndex(was) >= 0) { this.send.topic = ""; this.reprep(); }
        },
        // topic: a "Record a story on this topic" link's (data-rec-topic) — chosen, and said
        go: function (p, topic) {
          if (p === "gv" || p === "lv") this.setPub(p);
          if (topic && !this.rec() && this.state !== "countdown") {
            this.topicOther = false;
            this.send.topic = String(topic).replace(/\s+/g, " ").trim().slice(0, 120);
            this.reprep();
            announce(this.t("a_topic", { topic: this.send.topic }));
          }
          var el = this.$root, head = document.getElementById("recorder-title");
          try { el.scrollIntoView({ block: "start", behavior: GV.reducedMotion && GV.reducedMotion() ? "auto" : "smooth" }); } catch (e) { el.scrollIntoView(); }
          if (head) setTimeout(function () { head.focus({ preventScroll: true }); }, 50);
        },

        /* ---------------- what the story is about (THE TOPIC above) */
        // the magazine's topics (#rec-config topics[pub]: {t: its words, l: their language, g: the page language's words —
        // "" when they are the same —, m: g is a machine translation, d: a deadline "YYYY-MM-DD" or "", dated}), in the
        // order the list shows them: the coming issues' themes first
        topicList: function (p) { var c = this.cfg && this.cfg.topics; return (c && c[p === "lv" ? "lv" : "gv"]) || []; },
        // send.topic's place in that list (-1: none, or the visitor's own words)
        topicIndex: function (p) {
          var v = String(this.send.topic || "").trim(), list = this.topicList(p);
          if (!v) return -1;
          for (var i = 0; i < list.length; i++) if (list[i] && list[i].t === v) return i;
          return -1;
        },
        // the list's value: "" (none yet), "other" (the visitor's own words — also ones typed in the e-mail's Topic), or
        // the topic's number
        topicPick: function (p) {
          if (this.topicOther) return "other";
          var i = this.topicIndex(p);
          return i >= 0 ? String(i) : String(this.send.topic || "").trim() ? "other" : "";
        },
        pickTopic: function (p, v) {
          var self = this, o = this.topicList(p)[Number(v)];
          if (v === "other") {
            if (this.topicIndex(p) >= 0) this.send.topic = "";
            this.topicOther = true;
            this.$nextTick(function () { if (self.$refs && self.$refs.topicOwn) self.$refs.topicOwn.focus(); });
          } else {
            this.topicOther = false;
            this.send.topic = v !== "" && o ? o.t : "";
          }
          this.reprep();
        },
        // a topic as the list shows it: its words and, for a theme with a deadline, the days left — counted on this
        // device (the page is built once a day): "Recaídas · 2 days left"
        topicText: function (p, i) {
          var o = this.topicList(p)[i];
          if (!o) return "";
          var n = o.d ? R.daysLeft(o.d, Date.now()) : null;
          if (n === null) return o.t;
          return o.t + " · " + (n < 0 ? this.s.tp_closed : n === 0 ? this.s.tp_today : n === 1 ? this.s.tp_day1 : this.t("tp_days", { n: n }));
        },
        // the chosen topic in the page's language (a La Viña topic on the English page): its words, and whether a machine
        // translated them (the page marks that)
        topicGloss: function () {
          var i = this.topicOther ? -1 : this.topicIndex(this.pub);
          return i >= 0 ? this.topicList(this.pub)[i].g || "" : "";
        },
        topicMachine: function () {
          var i = this.topicOther ? -1 : this.topicIndex(this.pub);
          return i >= 0 && !!this.topicList(this.pub)[i].m;
        },
        // the open Send panel's file made again under its new name (the topic is in it)
        reprep: function () {
          var t = this.openId && this.panel === "send" ? this.find(this.openId) : null;
          if (t && !t.damaged) this.prepare(t);
        },

        // the one main button: Start → (Cancel while asking / counting) → Stop and save; Continue when iOS held the sound
        primary: function (ev) {
          var st = this.state;
          // (the second click of a double-click, or a tap within half a second of the change, is not a Cancel)
          if (ev && ev.detail > 1) return;
          if ((st === "asking" || st === "countdown") && perf() - (E.changed || 0) < 600) return;
          if (st === "idle" || st === "testing") this.open("record");
          else if (st === "asking") this.close();
          else if (st === "countdown") { clearInterval(E.cd); E.cd = 0; this.close(); }
          else if (st === "recording" || st === "paused") this.stop(true);
          else if (st === "blocked") this.unblock();
        },
        wavSize: function (t) { return R.wavBytes(R.duration(t), t.rate); },

        /* ---------------- the microphone */
        // kind: "test" (the meter only) | "record" (3, 2, 1 — then the take)
        open: function (kind) {
          var self = this;
          if (kind === "record" && this.takes.length >= L.maxTakes) { this.notice = "limit"; announce(this.t("n_limit", { max: L.maxTakes })); return; }
          // the screen stays on while a take is made: asked for inside the tap (Safari grants it only there); room for
          // a long take on the device (said, nothing stopped)
          if (kind === "record") { wakeOn(); this.roomFor(R.takeBytes(L.hardStop, 48000)); }
          if (this.state === "testing") { if (kind === "record") this.countdown(); else this.close(); return; }
          if (this.state !== "idle") return;
          this.error = "";
          if (["recovered", "low", "unsaved"].indexOf(this.notice) < 0) this.notice = "";
          if (!this.can.record) { this.error = this.can.why || "no_audio"; announce(this.s["e_" + this.error]); return; }
          var AC = window.AudioContext || window.webkitAudioContext, ctx;
          try { ctx = new AC(); } catch (e) { this.error = "no_audio"; announce(this.s["e_no_audio"]); return; }
          E.ctx = ctx;
          // iOS starts every context suspended until a tap: this tap
          try { var r = ctx.resume(); if (r && r["catch"]) r["catch"](function () {}); } catch (e) { /* old */ }
          if (this.can.wasm) encoderReady(this.cfg)["catch"](function () {});
          this.state = "asking";
          E.changed = perf();
          getMic(this.micId, this.noise).then(function (stream) {
            if (E.ctx !== ctx) { stopStream(stream); return; }        // closed meanwhile
            E.stream = stream;
            return wire(ctx, stream, self.can.record).then(function () {
              if (E.ctx !== ctx) return;
              self.watchTrack(stream);
              self.listMics(stream);
              E.ctx.onstatechange = function () { if (E.ctx === ctx && ctx.state !== "running" && self.state === "recording") self.interrupt(); };
              if (ctx.state === "running") return self.opened(kind);
              return ctx.resume().then(null, function () {}).then(function () {
                if (E.ctx !== ctx) return;
                if (ctx.state === "running") self.opened(kind);
                else self.block(kind);
              });
            });
          })["catch"](function (err) {
            if (E.ctx !== ctx) return;                                // a session the visitor already closed
            self.close();
            self.error = R.errorKind(err);
            announce(self.s["e_" + self.error]);
          });
        },
        // iOS kept the sound off after the permission prompt: say so, and the main button says Continue
        block: function (kind) {
          var self = this;
          E.after = kind; this.state = "blocked";
          announce(this.s.st_blocked);
          this.$nextTick(function () { if (self.$refs.go) self.$refs.go.focus(); });
        },
        opened: function (kind) {
          E.hold = 0; E.win = []; E.lvlSaid = ""; E.lvlAt = perf();
          if (kind === "record") this.countdown();
          else { this.state = "testing"; announce(this.s.a_testing); }
        },
        // iOS kept the sound off: one more tap starts it (a context left "interrupted" sometimes needs a suspend
        // first). Still off: the hint again — the Cancel button beside it closes the microphone.
        unblock: function () {
          var self = this, ctx = E.ctx;
          if (!ctx) { this.state = "idle"; return; }
          wake(ctx).then(function (ok) {
            if (E.ctx !== ctx) return;
            if (ok) self.opened(E.after || "test"); else announce(self.s.st_blocked);
          });
        },
        watchTrack: function (stream) {
          var self = this, tr = stream.getAudioTracks()[0];
          if (!tr) return;
          tr.onended = function () { if (E.stream === stream && self.state === "recording") self.interrupt(); else if (E.stream === stream && self.state === "testing") self.close(); };
          tr.onmute = function () { if (E.stream === stream && self.state === "recording") self.interrupt(); };
        },
        listMics: function (stream) {
          var self = this;
          try {
            var cur = stream.getAudioTracks()[0].getSettings().deviceId || "";
            navigator.mediaDevices.enumerateDevices().then(function (list) {
              var mics = [];
              list.forEach(function (d) { if (d.kind === "audioinput" && d.deviceId && d.deviceId !== "default" && d.deviceId !== "communications") mics.push({ id: d.deviceId, label: d.label || self.t("mic_n", { n: mics.length + 1 }) }); });
              self.mics = mics;
              if (cur && mics.some(function (m) { return m.id === cur; })) self.micId = cur;
            })["catch"](function () {});
          } catch (e) { /* no device list */ }
        },
        // another microphone, or noise reduction switched: a test that is on starts again with it
        reopen: function () { if (this.state === "testing") { this.close(); this.open("test"); } },
        close: function () {
          clearInterval(E.cd); clearInterval(E.watch); E.cd = E.watch = 0;
          if (E.node && E.node.port) { try { E.node.port.onmessage = null; E.node.port.postMessage("stop"); } catch (e) { /* gone */ } }
          if (E.node) E.node.onaudioprocess = null;
          [E.src, E.node, E.mute].forEach(function (n) { if (n) { try { n.disconnect(); } catch (e) { /* gone */ } } });
          stopStream(E.stream);
          // the context goes a moment later, once the capture node has stopped (see WORKLET)
          var old = E.ctx;
          if (old) setTimeout(function () { try { var c = old.close(); if (c && c["catch"]) c["catch"](function () {}); } catch (e) { /* closed */ } }, 200);
          E.ctx = E.stream = E.src = E.node = E.mute = null;
          wakeOff();
          document.documentElement.classList.remove("cm-rec-on");
          this.meterPct = 0; this.lvl = ""; this.count = 0; E.zeroSince = 0;
          if (this.state !== "saving") this.state = "idle";
          this.guard();
        },

        /* ---------------- a take */
        countdown: function () {
          var self = this;
          this.state = "countdown"; this.count = 3; this.confirmDiscard = false;
          E.changed = perf();
          announce(this.t("a_countdown", { n: 3 }));
          clearInterval(E.cd);
          E.cd = setInterval(function () {
            self.count--;
            if (self.count <= 0) { clearInterval(E.cd); E.cd = 0; self.begin(); }
          }, 1000);
        },
        begin: function () {
          var self = this;
          if (!E.ctx) { this.state = "idle"; return; }
          var t = E.take = {
            id: R.newId(Date.now(), Math.random()), pub: this.pub, n: R.nextNumber(this.takes), created: Date.now(),
            rate: E.ctx.sampleRate, rule: this.ruleOf(this.pub), noise: this.noise, src: "mic",
            chunks: [], peaks: [], samples: 0, peak: 0, mp3: [], enc: null, encIdx: 0, catching: false,
            // what is on the device (flushSound): blocks, samples and rows written, the draft, the write in flight, the
            // database they went into (gen) and whether its rows go first (clear)
            flushIdx: 0, flushN: 0, flushTry: 0, flushFails: 0, seq: 0, drafted: false, flushing: false, flushP: null,
            gen: E.gen, clear: false,
            wall: 0, since: perf(), heard: false, toldSilent: false, gaps: false
          };
          this.sec = 0; this.state = "recording";
          if (this.notice !== "low" && this.notice !== "unsaved") this.notice = "";     // (said until it is saved, or room made)
          document.documentElement.classList.add("cm-rec-on");
          E.last = perf(); E.zeroSince = 0;
          wakeOn();
          // (its lock, then its draft: on the device from its first second; this page's own until it is listed)
          E.own[t.id] = true;
          lockTake(t.id);
          flushSound(t);
          this.guard();
          // (no "Recording" announcement: the countdown said when it starts, and speech now would be in the take)
          clearInterval(E.watch);
          E.watch = setInterval(function () {
            if (self.state === "recording" && perf() - E.last > L.gap * 1000) self.interrupt();
          }, 500);
          if (this.can.wasm) {
            newEncoder(this.cfg, t.rate).then(function (enc) {
              if (E.take !== t) return;
              t.enc = enc;
              catchUp(t);
            }, function () { /* no MP3 yet: it is made from the PCM later */ });
          }
        },
        pause: function () {
          var t = E.take;
          if (!t || this.state !== "recording") return;
          t.wall += perf() - t.since;
          this.state = "paused";
          flushSound(t);
          announce(this.s.a_paused);
        },
        interrupt: function () {
          if (this.state !== "recording") return;
          this.pause();
          this.notice = "interrupted";
          announce(this.s.n_interrupted);
        },
        resume: function () {
          var self = this, t = E.take;
          if (!t || this.state !== "paused" || E.resuming) return;
          var ctx = E.ctx, tr = E.stream && E.stream.getAudioTracks()[0];
          wakeOn();                                   // (inside the tap: see open)
          E.resuming = true;
          var go = function (ok) {
            E.resuming = false;
            if (E.take !== t || self.state !== "paused") return;
            if (!ok) { self.notice = "blocked"; announce(self.s.st_blocked); return; }   // still off: stays paused
            t.since = perf(); E.last = perf(); E.zeroSince = 0;
            self.state = "recording"; self.notice = ""; self.confirmDiscard = false;
            announce(self.s.a_resumed);
          };
          var live = tr && tr.readyState === "live" && !tr.muted;
          // the microphone was taken away (a call, the screen locked): ask for it again, then the sound
          (live ? Promise.resolve() : getMic(this.micId, t.noise).then(function (stream) {
            if (E.take !== t) { stopStream(stream); throw new Error("gone"); }
            stopStream(E.stream);
            E.stream = stream;
            rewire(stream);
            self.watchTrack(stream);
          })).then(function () { return wake(ctx); }).then(go, function (err) {
            E.resuming = false;
            if (E.take !== t) return;
            self.error = R.errorKind(err);
            announce(self.s["e_" + self.error]);
          });
        },
        // Stop: keep it (save) or throw it away. Saved: the last seconds go to the device at once (a page left while the
        // MP3 is finished keeps them), then add() writes the rest, the MP3 and the final record in one transaction.
        stop: function (save, why) {
          var self = this, t = E.take;
          if (!t) { this.close(); return; }
          if (this.state === "recording") t.wall += perf() - t.since;
          if (save && t.samples) { this.askPersist(); flushSound(t); }
          E.take = null;
          this.confirmDiscard = false;
          this.state = save && t.samples ? "saving" : "idle";
          this.close();
          // the keyboard stays on the main button (Discard / Pause / the confirm row are gone now)
          this.$nextTick(function () {
            var a = document.activeElement;
            if ((!a || a === document.body || !a.offsetParent) && self.$refs.go) self.$refs.go.focus();
          });
          if (!save || !t.samples) {
            // its draft and its sound go (after a write still in flight), then its lock
            t.final = t.gone = true;
            (t.flushP || Promise.resolve()).then(function () { return attempt(function () { return db.drop(t.id); }); })["catch"](function () {})
              .then(function () { unlockTake(t.id); delete E.own[t.id]; });
            this.sec = 0;
            this.state = "idle";
            announce(save ? "" : this.s.a_discarded);
            this.guard();
            return;
          }
          if (why === "hard") announce(this.s.m_hard);
          t.gaps = t.samples / t.rate < 0.9 * (t.wall / 1000) - 1;
          // the MP3: what the encoder has (after any catching up), or later from the PCM
          var mp3P = t.enc ? drain(t).then(function () {
            if (!t.enc) return null;
            var last = copyOut(t.enc.finalize());
            if (last) t.mp3.push(last);
            return mp3Of(t.mp3);
          })["catch"](function () { return null; }) : Promise.resolve(null);
          mp3P.then(function (mp3) {
            // (after the write in flight: what it wrote is not written again)
            return (t.flushP || Promise.resolve()).then(function () { return mp3; });
          }).then(function (mp3) {
            t.final = true;
            var pcm = pcmBytes(t.chunks, 0, t.chunks.length);
            // (numbered when it is kept: an edit or a file added meanwhile may have taken the next number)
            t.n = Math.max(t.n, R.nextNumber(self.takes));
            var meta = record(t), plan = { done: t.flushN * 2, seq: t.seq, drafted: t.drafted, locked: true, gen: t.gen, clear: t.clear };
            t.chunks = t.mp3 = t.peaks = null;
            var saved = self.add(meta, { pcm: pcm, mp3: mp3 }, plan);
            delete E.own[t.id];                                    // (listed now)
            return saved.then(function (ok) {
              self.state = "idle";
              self.sec = 0;
              self.told(ok, meta, self.t("a_saved", { name: self.name(meta), time: R.spoken(R.duration(meta), self.s.words) }));
              self.guard();
            });
          })["catch"](function () { delete E.own[t.id]; self.state = "idle"; self.guard(); });
        },
        // what Stop, Add a recording and Apply say once their take is in the list: `words` when it is saved on the device
        // — or kept in this page by the visitor's choice ("Keep" off), or by a browser that keeps nothing (the box says
        // so) —, else that it is only in this page, with a notice by the main button too (on a phone the takes' box is
        // a screen or two below it): until it is saved
        told: function (ok, meta, words) {
          if (ok || !this.keep || !this.kept) { announce(words); return; }
          var x = this.find(meta.id);
          if (!x || x.saved) { if (x) announce(words); return; }
          this.notice = "unsaved"; this.noticeId = meta.id;
          announce(this.t("a_unsaved", { name: this.name(meta) }));
        },
        askDiscard: function () { if (this.state === "recording") this.pause(); this.confirmDiscard = true; },

        /* ---------------- the takes */
        // a new take — its record (record()) and its sound {pcm, mp3} (ArrayBuffers or typed arrays: their own bytes
        // are kept) — into the list, then onto the device (save). plan: how far the device has it already (a recording:
        // done = PCM bytes written, seq = its next row, drafted, locked = its Web Lock is this page's, gen = the
        // database those went into — this one when not said —, clear = its rows there go first).
        // → a promise of true once it is saved on the device (false: it is in this page only, for now)
        // One entry per id: a take listed with this id already is replaced (never two in the list, never two writes of
        // one take at once — a write of the one replaced stops at its next step, leaving what it wrote, and this one's
        // waits for it to end).
        add: function (meta, sound, plan) {
          var self = this, id = meta.id, old = this.find(id), prev = PLAN[id];
          var S = SND[id] = { pcm: bytesOf(sound && sound.pcm) || new ArrayBuffer(0), mp3: bytesOf(sound && sound.mp3) };
          var t = Object.assign({}, meta, { v: 2, draft: false, mp3: false, size: S.pcm.byteLength + (S.mp3 ? S.mp3.byteLength : 0),
            url: "", mp3Size: S.mp3 ? S.mp3.byteLength : 0, saved: false, saving: false, failed: false, damaged: false, lost: false,
            stuck: false, fails: 0, gen: E.gen });
          t.url = playUrl(S, t);
          if (old) revoke(old.url);
          if (prev) prev.stale = true;
          if (plan) {
            PLAN[id] = { done: plan.done || 0, seq: plan.seq || 0, drafted: !!plan.drafted, locked: !!plan.locked,
              gen: plan.gen === undefined ? E.gen : plan.gen, clear: !!plan.clear };
          } else delete PLAN[id];
          this.takes = R.sortTakes([t].concat(this.takes.filter(function (x) { return x.id !== id; })));
          var go = function () { return self.save(id); };
          var saved = prev && prev.busy ? prev.busy.then(go, go) : go();
          if (!S.mp3) this.makeMp3(id);
          this.guard();
          return saved;
        },
        // a take in this page → the device (D2): its draft record, its PCM, then ONE transaction with the MP3 and the final
        // record — the moment it is saved. One write per take at a time (a second call gets the one on its way), holding
        // the take's lock until it is saved, tied to its PLAN: deleted, "Keep" switched off or replaced (add) meanwhile,
        // it stops at its next step. A failure leaves it in this page with all its sound (failed: tried again — guard),
        // and what is on the device stays for it.
        save: function (id) {
          var self = this, x = this.find(id), S = SND[id];
          if (!x || x.saved || x.damaged || !S || !S.pcm) return Promise.resolve(!!(x && x.saved));
          var P = PLAN[id] || (PLAN[id] = { done: 0, seq: 0, drafted: false, locked: false, gen: E.gen, clear: false });
          if (P.busy) return P.busy;
          if (!this.keep || !this.kept) return Promise.resolve(false);
          var pcm = S.pcm, mp3 = S.mp3, size = pcm.byteLength + (mp3 ? mp3.byteLength : 0), written = null;
          // (still this write's take: not replaced by a newer one — its PLAN gone means it was deleted: alive() says so)
          var mine = function () { return !P.stale && (!PLAN[id] || PLAN[id] === P); };
          var alive = function () { var y = self.find(id); if (!y || !self.keep || PLAN[id] !== P || P.stale) throw gone(); return y; };
          var draftRow = function () { return row(alive(), { v: 2, draft: true, mp3: false, samples: 0, size: 0, at: Date.now() }); };
          x.saving = true;
          P.busy = (P.locked ? Promise.resolve(true) : lockTake(id)).then(function () {
            P.locked = true;
            if (P.drafted) return null;
            return attempt(function () {
              var d = draftRow();
              return db.write(function (os) { os.takes.put(d); });
            }).then(function () { P.drafted = true; });
          }).then(function () {
            return writeSound(id, pcm, mp3, P, function () {
              return (written = row(alive(), { v: 2, draft: false, mp3: !!mp3, size: size, at: 0 }));
            }, alive, draftRow);
          }).then(function () {
            var y = self.find(id);
            if (!mine()) return false;                             // replaced: the newer write tells
            if (!y || !self.keep || PLAN[id] !== P) { delete PLAN[id]; dropQuiet(id); return false; }
            var was = y.failed;
            y.saved = true; y.saving = false; y.failed = false; y.stuck = false; y.fails = 0; y.v = 2; y.mp3 = !!mp3; y.size = size;
            y.gen = P.gen;                                         // (the database it is in: checkLost)
            delete PLAN[id];
            unlockTake(id);
            if (S.mp3 && S.mp3 !== mp3) self.storeMp3(id);          // its MP3 was made while it was being written
            else self.lighten(id);
            if (written && (written.name !== y.name || written.starred !== y.starred)) self.saveMeta(y);
            if (self.notice === "unsaved" && self.noticeId === id) self.notice = "";
            // (it was "not saved yet", and the box that said so goes quietly: said)
            if (was) announce(self.t("a_saved", { name: self.name(y), time: R.spoken(R.duration(y), self.s.words) }));
            self.retryAll();                                       // it worked: the others waiting, now
            return true;
          }, function (err) {
            var y = self.find(id);
            if (!mine()) return false;
            // deleted, or "Keep" switched off, meanwhile: what got onto the device goes
            if ((err && err.gone) || !y) { delete PLAN[id]; dropQuiet(id); return false; }
            y.saving = false; y.failed = true; y.fails = (y.fails || 0) + 1;
            self.storeFail(err);
            if (y.fails >= 2 && R.storeError(err) === "transient") self.probe(y);
            return false;
          }).then(function (ok) { P.busy = null; self.guard(); return ok; });
          return P.busy;
        },
        // a saved take's sound leaves the page (its player's address is enough: Share, Download, an edit and its MP3 read
        // it back) — not where the browser may lose the device's copy (ephemeral), where this page's copy is the one
        // that lasts (A1)
        lighten: function (id) { var S = SND[id]; if (S && !this.ephemeral) { S.pcm = null; S.mp3 = null; } },
        // a private tab or window (ephemeral): every saved take's sound back into this page
        holdBytes: function () {
          var self = this;
          if (!this.ephemeral) return Promise.resolve();
          return this.takes.reduce(function (p, t) {
            return p.then(function () {
              var S = SND[t.id];
              if (!t.saved || t.damaged || (S && S.pcm && (S.mp3 || !t.mp3Size))) return null;
              return readSound(t, true).then(function (s) {
                var y = self.find(t.id), Z = snd(t.id);
                if (y && y.saved) { Z.pcm = Z.pcm || s.pcm; Z.mp3 = Z.mp3 || s.mp3; }
              }, function () { /* read again next time */ });
            });
          }, Promise.resolve());
        },
        // a write of this take failed again (twice now, "transient") while the device can still be read: most likely it is
        // full — an iPhone says UnknownError then, not QuotaExceededError (r10 storage F3): its size is shown
        probe: function (y) {
          attempt(function () { return keysOf("takes"); }).then(function () { if (!y.saved) y.stuck = true; }, function () {});
        },
        // an MP3 made after its take was saved → the device: its rows and the record's mp3 / size, in ONE transaction that
        // reads the record first — only onto the take's own final v2 record (never one deleted meanwhile — in another tab,
        // or by "Keep" off —, a draft, or a v1 record)
        storeMp3: function (id) {
          var self = this, S = SND[id], x = this.find(id);
          if (!x || !x.saved || x.damaged || x.v < 2 || !S || !S.mp3) return Promise.resolve(false);
          var mp3 = S.mp3, rows = soundRows(id, "mp3", mp3, 0, mp3.byteLength, 0);
          return attempt(function () {
            if (!self.find(id)) throw gone();
            return db.update(function (os) {
              var out = { result: 0 }, g = os.takes.get(id);
              g.onsuccess = function () {
                var r = g.result;
                if (!r || r.draft || !(r.v >= 2)) return;
                r.mp3 = true;
                r.size = Math.max(0, Math.floor(Number(r.samples) || 0)) * 2 + mp3.byteLength;
                os.sound["delete"](range(R.soundRange(id, "mp3")));
                putRows(os, rows);
                os.takes.put(r);
                out.result = r.size;
              };
              return out;
            });
          }).then(function (size) {
            if (!size) return false;
            var y = self.find(id);
            if (y) { y.mp3 = true; y.size = size; }
            if (SND[id] === S && S.mp3 === mp3) self.lighten(id);
            return true;
          }, function () { return false; });
        },
        // a write that failed for good (after attempt's tries): what the storage box says
        storeFail: function (err) {
          var k = R.storeError(err);
          this.lastErr = String((err && err.name) || k);
          if (k === "none") this.kept = false;
          else if (k === "version") this.reload = true;
          this.full = k === "quota";
        },
        // every take not saved yet: written again (another take was saved or deleted, the page is shown again or hidden,
        // back online, guard's timer, "Try again") → a promise of each one's answer
        retryAll: function () {
          var self = this;
          if (!this.keep || !this.kept) return Promise.resolve([]);
          return Promise.all(this.takes.filter(function (t) { return !t.saved && !t.damaged; }).map(function (t) { return self.save(t.id); }));
        },
        // "Try again": over a new connection; the device's list read again when it could not be (after a listing still on
        // its way; "reload" goes only once a list works). → a promise; then, if the keyboard was on the button and the box
        // went with it (Alpine hides it a frame later), it goes to the takes' heading. Still not working: said — the box's
        // words are the same, so its live region says nothing, and nothing else changes (r10 V6)
        retry: function () {
          var self = this, from = document.activeElement;
          reset();
          var p = this.reload ? (E.loadP || Promise.resolve()).then(function () { return self.load(); }) : this.retryAll();
          return Promise.resolve(p)["catch"](function () {}).then(function () { return wait(150); }).then(function () {
            var k = self.storeNote();
            if (k === "reload") announce(self.s.a_reload_failed);
            else if (k === "unsaved" || k === "full") announce(self.s.a_retry_failed);
            var a = document.activeElement, h = document.getElementById("rec-takes-title");
            if (h && (!a || a === document.body || (a === from && !a.offsetParent))) h.focus();
          });
        },
        // the device's copy of the takes this page shows as saved: still there? A private tab keeps it in a process iOS
        // ends in the background — the database then comes back empty (A1); so on visible, pageshow and focus (at most
        // every 5 s), in a private tab or once the page saw it happen (ephemeral): a take missing whose sound this page
        // holds is "not saved" again and written again; one it holds no sound of (saved before the page knew to keep
        // it), when the database came back new since it was saved, is "lost" — said, never "saved" (r10 N3). (Any other
        // one missing was deleted in another tab: load() takes it from the list.)
        checkLost: function (now) {
          var self = this;
          if (!this.ephemeral || !this.loaded || !this.keep || !this.kept) return Promise.resolve();
          if (!now && perf() - E.checked < 5000) return Promise.resolve();
          E.checked = perf();
          return attempt(function () { return keysOf("takes"); }).then(function (keys) {
            var on = {}, again = [], lost = [];
            (keys || []).forEach(function (k) { on[k] = true; });
            self.takes.forEach(function (t) {
              if (!t.saved || t.damaged || on[t.id]) return;
              var S = SND[t.id];
              if (S && S.pcm) again.push(t);
              else if ((t.gen || 0) < E.gen) lost.push(t);
            });
            // (their player's blob: address died with the process too: a new one from the page's copy)
            again.forEach(function (t) {
              t.saved = false; t.failed = true; delete PLAN[t.id];
              var old = t.url;
              t.url = playUrl(SND[t.id], t);
              revoke(old);
            });
            self.lose(lost);
            if (!again.length && !lost.length) return null;
            self.guard();
            return self.retryAll();
          }, function () { /* tried again next time */ });
        },
        // saved takes the browser lost from the device (its database came back new since) whose sound this page doesn't
        // hold: nothing can save them again — each says so ("lost", shown like a take that can't be read, with Delete),
        // never "saved", and it is said once (r10 N3)
        lose: function (list) {
          if (!list.length) return;
          list.forEach(function (t) {
            t.saved = t.saving = t.failed = false; t.damaged = t.lost = true;
            revoke(t.url); t.url = "";
            delete SND[t.id]; delete PLAN[t.id];
          });
          announce(list.length > 1 ? this.t("a_lost_n", { n: list.length }) : this.t("a_lost", { name: this.name(list[0]) }));
        },
        // "keep them until I delete them": asked once a page, from a tap that saves a take (Stop and save, Add a
        // recording, Apply) — the answer is the "This device" box's line
        askPersist: function () {
          var self = this;
          if (E.persistAsked || this.persisted === true || !this.keep) return;
          E.persistAsked = true;
          try { navigator.storage.persist().then(function (v) { self.persisted = !!v; }, function () {}); } catch (e) { /* no Storage API */ }
        },
        // what the browser says: kept until deleted (persisted); a private tab or window (no origin-private file system
        // there), asked of WebKit's browsers — Safari, and every browser on an iPhone or iPad, whose private tabs keep
        // the takes in the same process iOS ends —: then every saved take's sound is kept in this page too (ephemeral,
        // A1). Only Safari itself is told "private" (priv: the box): known for Safari only — Chrome, Firefox or Edge on
        // an iPhone, and an app's browser, may refuse it for other reasons (r10 A21, N3)
        checkStorage: function () {
          var self = this;
          try { navigator.storage.persisted().then(function (v) { self.persisted = !!v; }, function () {}); } catch (e) { /* no Storage API */ }
          if (!this.ios && this.help !== "safari") return;
          try {
            navigator.storage.getDirectory().then(function () {}, function () {
              self.ephemeral = true;
              if (self.safari) self.priv = true;
              if (self.loaded) self.holdBytes();
            });
          } catch (e) { /* older Safari */ }
        },
        // room on the device for `need` bytes (D7): when it looks short, "low" says how much is free — nothing is stopped
        roomFor: function (need) {
          var self = this;
          if (!this.keep || !this.kept) return;
          try {
            navigator.storage.estimate().then(function (e) {
              if (!e || !(e.quota > 0)) return;
              var free = Math.max(0, e.quota - (e.usage || 0));
              if (free < need) {
                self.lowFree = free;
                if (self.notice !== "low") { self.notice = "low"; announce(self.t("n_low", { free: self.size(free) })); }
              } else if (self.notice === "low") self.notice = "";
            }, function () {});
          } catch (e) { /* no Storage API */ }
        },
        // a player that can't read its sound (iOS after the app was in the background: "WebKitBlobResource error 1"):
        // a new address made from the bytes (read back again when they are not in this page), at most every 30 s a take
        replay: function (t) {
          var self = this, x = this.find(t.id), now = perf();
          if (!x || x.damaged || now - (REPLAY[t.id] || -1e9) < 30000) return;
          REPLAY[t.id] = now;
          var S = SND[t.id];
          (S && (S.mp3 || S.pcm) ? Promise.resolve(S) : readSound(x, this.ephemeral).then(function (s) {
            if (self.ephemeral) SND[t.id] = s;
            return s;
          })).then(function (s) {
            var y = self.find(t.id);
            if (!y) return;
            var old = y.url;
            y.url = playUrl(s, y);
            revoke(old);
          }, function () {});
        },
        // "Try again" on a take that couldn't be read: read again (a lost connection, the browser busy) — it plays again
        // (the keyboard goes to it), or it is still damaged: said in other words than the note's, which asks for this very
        // tap (r10 V6). (Not a take the browser lost: there is nothing to read.)
        reread: function (t) {
          var self = this, c = R.clean(t);
          if (!c || !t.damaged || t.lost) return;
          reset();
          readSound(c, this.ephemeral).then(function (s) {
            var y = self.find(c.id);
            if (!y || !y.damaged) return;
            SND[c.id] = s;
            y.url = playUrl(s, y);
            y.mp3Size = s.mp3 ? s.mp3.byteLength : 0;
            y.damaged = false;
            self.lighten(c.id);
            if (!y.mp3Size) self.makeMp3(c.id);
            self.focusTake(c.id);
          }, function () { announce(self.s.a_damaged_again); });
        },
        // a name or a star → the take's record on the device: read and written in ONE transaction, its name and star only
        // (never a record that is gone — deleted in another tab, or "Keep" off —, a draft being written, nor this page's
        // older idea of the rest: v, mp3, size — r10 F2)
        saveMeta: function (t) {
          if (!t.saved || t.damaged) return;
          var id = t.id, name = t.name || "", starred = !!t.starred;
          attempt(function () {
            return db.update(function (os) {
              var g = os.takes.get(id);
              g.onsuccess = function () {
                var r = g.result;
                if (!r || r.draft || (r.name === name && !!r.starred === starred)) return;
                r.name = name; r.starred = starred;
                os.takes.put(r);
              };
            });
          })["catch"](function () {});
        },
        find: function (id) { for (var i = 0; i < this.takes.length; i++) if (this.takes[i].id === id) return this.takes[i]; return null; },
        // a take's bytes of one kind ("pcm": its 16-bit samples, "mp3"): from this page, or read back from the device
        kindOf: function (id, kind) {
          var S = snd(id), t = this.find(id);
          if (S[kind]) return Promise.resolve(S[kind]);
          if (!t) return Promise.reject(new Error(kind));
          return readKind(t, kind).then(function (b) { if (!b || !b.byteLength) throw new Error(kind); return b; });
        },
        pcmOf: function (id) { return this.kindOf(id, "pcm"); },
        // a take kept without an MP3 (the encoder was not there): make it now, or when it loads
        makeMp3: function (id) {
          var self = this;
          if (!this.can.wasm) { this.mp3Fail = true; return; }
          this.queue(function () {
            var t = self.find(id);
            if (!t || t.mp3Size || t.damaged) return null;
            self.job = { id: id, label: self.t("j_mp3", { name: self.name(t) }), pct: 0 };
            return self.pcmOf(id).then(function (buf) {
              return encodePcm(self.cfg, new Int16Array(buf), t.rate, function (p) { if (self.job) self.job.pct = Math.round(p * 100); });
            }).then(function (mp3) {
              var x = self.find(id);
              if (!x) return;
              var S = snd(id), old = x.url;
              S.mp3 = mp3;
              x.mp3Size = mp3.byteLength;
              x.url = playUrl(S, x);
              revoke(old);
              if (x.saved) self.storeMp3(id);       // (not saved yet: its write takes it, or writes it after — save)
              if (self.openId === id && self.panel === "send") self.prepare(x);
            });
          }, function () { self.mp3Fail = true; self.notice = "encoder"; });
        },
        // one heavy job at a time (making an MP3, an edit, a file the visitor added). E.pending counts the ones running or
        // waiting (the keep switch and Delete all wait for them); E.risky those whose take is not in the list yet — an
        // edit, a file added (risky): the page asks before it is left while one is (an MP3 being made loses nothing)
        queue: function (fn, onFail, risky) {
          var self = this;
          E.pending++;
          if (risky) E.risky++;
          E.jobs = (E.jobs || Promise.resolve()).then(function () {
            return Promise.resolve().then(fn)["catch"](function (e) { if (onFail) onFail(e); });
          }).then(function () { E.pending--; if (risky) E.risky--; self.job = null; self.guard(); });
          this.guard();
          return E.jobs;
        },

        // the takes kept on this device (D9), each read on its own: one whose sound can't be read is listed as such —
        // never deleted, never hiding the others; drafts no page is making come back as "Recovered recording"; the
        // first recorder's takes move to the new store. Again on Back (pageshow) and "Try again": the takes only in
        // this page stay. (A device whose list can't be read: "reload" — nothing recovered or moved from it meanwhile.)
        load: function () {
          var self = this;
          if (E.loadP) return E.loadP;
          if (!window.indexedDB) { this.kept = false; this.loaded = true; this.guard(); return Promise.resolve(); }
          var drafts = [], old = [], had = {}, listedOk = false;
          this.takes.forEach(function (t) { if (t.saved) had[t.id] = true; });
          E.loadP = attempt(function () { return db.list(); }).then(function (rows) {
            var seen = {}, found = [];
            listedOk = true;
            self.reload = false;
            return (rows || []).reduce(function (p, r) {
              return p.then(function () {
                var c = R.clean(r);
                if (!c) return null;                                   // not a take: left as it is
                seen[c.id] = true;
                if (c.draft) { drafts.push(c); return null; }
                if (c.v < 2) old.push(c.id);
                return self.listed(c).then(function (t) { if (t) found.push(t); });
              });
            }, Promise.resolve()).then(function () {
              // a take this page showed as saved — when the list was asked for AND still now (checkLost may have found it
              // missing meanwhile and be writing it again: then it stays, r10 N1) — that is gone from the device: deleted
              // in another tab — it goes from the list; unless this page holds its sound (a private tab, where the browser
              // lost the device's copy: A1) — then it is "not saved", and written again —, or the database came back new
              // since it was saved, with no copy here — "lost" (N3). A take not saved stays.
              var lost = [];
              var stay = self.takes.filter(function (t) {
                if (had[t.id] && !seen[t.id] && t.saved) {
                  var S = SND[t.id];
                  if (S && S.pcm) { t.saved = false; t.failed = true; delete PLAN[t.id]; return true; }
                  if ((t.gen || 0) < E.gen) { lost.push(t); return true; }
                  revoke(t.url); delete SND[t.id]; return false;
                }
                return !found.some(function (f) { return f.id === t.id; });
              });
              self.takes = R.sortTakes(found.concat(stay));
              self.lose(lost);
              self.takes.forEach(function (t) { if (!t.mp3Size && !t.damaged) self.makeMp3(t.id); });
            });
          }, function (err) {
            if (R.storeError(err) === "none") self.kept = false; else self.reload = true;
          }).then(function () {
            self.loaded = true;
            self.guard();
            if (!listedOk) return null;
            return self.recover(drafts).then(function () { return self.recoverOld(); }).then(function () { return self.migrate(old); });
          })["catch"](function () {})
            .then(function () { E.loadP = null; if (self.ephemeral) self.holdBytes(); self.retryAll(); self.guard(); });
          return E.loadP;
        },
        // one take of the device's list → the take in this page: its MP3 rows read back (else its PCM's, played as a
        // WAV; v1: its Blobs; a private tab: both, kept) — a take whose sound can't be read is "damaged" (listed, no
        // player; Try again reads it again, Delete works). gen: the database it was found in (checkLost).
        listed: function (c) {
          var self = this, x = this.find(c.id);
          if (x && x.saved && !x.damaged && x.url) {
            ["name", "starred", "pub", "v", "mp3", "size"].forEach(function (k) { x[k] = c[k]; });
            x.gen = E.gen;
            return Promise.resolve(x);
          }
          if (x && !x.saved && !x.lost) return Promise.resolve(null); // only in this page (its write may be on its way)
          var t = Object.assign({}, c, { url: "", mp3Size: 0, saved: true, saving: false, failed: false, damaged: false, lost: false,
            stuck: false, fails: 0, gen: E.gen });
          return readSound(c, this.ephemeral).then(function (s) {
            SND[c.id] = s;
            t.url = playUrl(s, c);
            t.mp3Size = s.mp3 ? s.mp3.byteLength : 0;
            self.lighten(c.id);
            return t;
          }, function () { t.damaged = true; return t; });
        },
        // drafts no page is making any more (not this page's own — being made, saved or dropped —, not locked — without
        // Web Locks: untouched for LIMITS.partFresh seconds — and this page gets the lock): their PCM → a "Recovered
        // recording" (its MP3 made again); one under a second, or an empty draft that old, goes; one whose sound can't be
        // read is left for the next visit
        recover: function (drafts) {
          var self = this, now = Date.now();
          return drafts.reduce(function (p, c) {
            return p.then(function () {
              if (self.find(c.id) || (E.take && E.take.id === c.id) || E.own[c.id] || E.locks[c.id]) return null;
              if (!hasLocks() && now - c.at < L.partFresh * 1000) return null;
              return lockTake(c.id, true).then(function (mine) {
                if (!mine) return null;                                // another tab is making it
                return attempt(function () { return db.bytes(c.id, "pcm", c.samples * 2); }).then(function (got) {
                  var pcm = got ? got.buf : new ArrayBuffer(0), rows = got ? got.rows : 0, total = pcm.byteLength >> 1;
                  if (!rows && now - c.at < L.partFresh * 1000) { unlockTake(c.id); return null; }   // only just begun
                  if (total < c.rate) {
                    return attempt(function () { return db.drop(c.id); })["catch"](function () {}).then(function () { unlockTake(c.id); });
                  }
                  var i16 = new Int16Array(pcm, 0, total), pk = peaksOf(i16);
                  var meta = record({ id: c.id, pub: c.pub, n: Math.max(c.n, R.nextNumber(self.takes)), created: c.created, rate: c.rate,
                    samples: total, peak: Math.max.apply(null, pk.concat([0])), peaks: pk, src: "recovered", noise: c.noise });
                  self.notice = "recovered";
                  announce(self.s.n_recovered);
                  // (its sound is on the device already: the final record — and its MP3, once made — is what is left)
                  return self.add(meta, { pcm: i16, mp3: null }, { done: total * 2, seq: rows, drafted: true, locked: true });
                }, function () { unlockTake(c.id); });
              });
            });
          }, Promise.resolve())["catch"](function () {});
        },
        // the first recorder's crash-recovery pieces (Blobs in "parts") of a take no page is making → its bytes → a
        // "Recovered recording" in the new store (whose final write empties them); pieces that can't be read stay
        recoverOld: function () {
          var self = this, now = Date.now();
          return attempt(function () { return readAll("parts"); }).then(function (parts) {
            var by = {};
            (parts || []).forEach(function (p) { if (p && typeof p.id === "string" && p.blob) (by[p.id] = by[p.id] || []).push(p); });
            return Object.keys(by).reduce(function (q, id) {
              return q.then(function () {
                var list = by[id].sort(function (a, b) { return a.seq - b.seq; }), f = R.clean({ id: id, pub: list[0].pub, n: list[0].n,
                  created: list[0].created, rate: list[0].rate, samples: 0, noise: list[0].noise });
                if (!f || self.find(id) || E.own[id] || E.locks[id]) return null;
                var last = Math.max.apply(null, list.map(function (p) { return Number(p.at) || 0; }));
                if (!hasLocks() && now - last < L.partFresh * 1000) return null;
                return lockTake(id, true).then(function (mine) {
                  if (!mine) return null;
                  return list.reduce(function (r, p) {
                    return r.then(function (bufs) { return bufferOf(p.blob).then(function (b) { bufs.push(b); return bufs; }); });
                  }, Promise.resolve([])).then(function (bufs) {
                    var pcm = join(bufs), total = pcm.byteLength >> 1;
                    if (total < f.rate) {
                      return attempt(function () { return db.write(function (os) { if (os.parts) os.parts["delete"](range(R.soundRange(id))); }); })
                        ["catch"](function () {}).then(function () { unlockTake(id); });
                    }
                    var i16 = new Int16Array(pcm, 0, total), pk = peaksOf(i16);
                    var meta = record({ id: id, pub: f.pub, n: Math.max(f.n, R.nextNumber(self.takes)), created: f.created || now, rate: f.rate,
                      samples: total, peak: Math.max.apply(null, pk.concat([0])), peaks: pk, src: "recovered", noise: f.noise });
                    self.notice = "recovered";
                    announce(self.s.n_recovered);
                    return self.add(meta, { pcm: i16, mp3: null }, { locked: true });
                  }, function () { unlockTake(id); });
                });
              });
            }, Promise.resolve());
          })["catch"](function () {});
        },
        // the first recorder's takes (v1: Blob rows) → the new store, one at a time: their bytes as sound rows, then the
        // v2 record in the transaction that empties their old rows. One whose PCM can't be read stays as it is (it
        // still plays from its MP3), tried again next visit. One with no Blob left whose sound rows are there (a record a
        // stale page wrote back as v1 after the move, r10 F2): its record is put right (relabel).
        migrate: function (ids) {
          var self = this;
          return ids.reduce(function (p, id) {
            return p.then(function () {
              var x = self.find(id);
              if (!x || x.v >= 2 || x.damaged || !self.keep || !self.kept || E.locks[id]) return null;
              return lockTake(id, true).then(function (mine) {
                if (!mine) return null;
                return attempt(function () { return db.legacy("pcm", id); }).then(function (pcm) {
                  if (!pcm || !pcm.byteLength) return self.relabel(id);
                  var S = snd(id);
                  return (S.mp3 ? Promise.resolve(S.mp3) : attempt(function () { return db.legacy("mp3", id); })["catch"](function () { return null; }))
                    .then(function (m) {
                      var mp3 = m && m.byteLength ? m : null, size = pcm.byteLength + (mp3 ? mp3.byteLength : 0);
                      var alive = function () { var y = self.find(id); if (!y || !self.keep) throw gone(); return y; };
                      return writeSound(id, pcm, mp3, { done: 0, seq: 0, clear: true, gen: E.gen }, function () {
                        return row(alive(), { v: 2, draft: false, mp3: !!mp3, size: size });
                      }, alive).then(function () {
                        var y = self.find(id);
                        if (y) { y.v = 2; y.mp3 = !!mp3; y.size = size; }
                        self.lighten(id);
                      });
                    });
                })["catch"](function () {}).then(function () { unlockTake(id); });
              });
            });
          }, Promise.resolve());
        },
        // a v1 record whose sound is in the new store already: v 2, mp3 and size from its rows — the record alone, read and
        // written in one transaction (never one gone, nor one already v2)
        relabel: function (id) {
          var self = this, sizeOf = function (kind) {
            return attempt(function () { return db.bytes(id, kind, 0); }).then(function (got) { return got && got.rows ? got.buf.byteLength : 0; });
          };
          return Promise.all([sizeOf("pcm"), sizeOf("mp3")]).then(function (n) {
            if (!n[0]) return null;
            return attempt(function () {
              return db.update(function (os) {
                var out = { result: false }, g = os.takes.get(id);
                g.onsuccess = function () {
                  var r = g.result;
                  if (!r || r.draft || r.v >= 2) return;
                  r.v = 2; r.mp3 = n[1] > 0; r.size = n[0] + n[1];
                  os.takes.put(r);
                  out.result = true;
                };
                return out;
              });
            }).then(function (ok) {
              var y = self.find(id);
              if (ok && y) { y.v = 2; y.mp3 = n[1] > 0; y.size = n[0] + n[1]; }
            });
          });
        },

        star: function (t) {
          var on = !t.starred, self = this;
          this.takes.forEach(function (x) { if (x.starred && x !== t) { x.starred = false; self.saveMeta(x); } });
          t.starred = on;
          this.saveMeta(t);
          announce(this.t(on ? "a_starred" : "a_unstarred", { name: this.name(t) }));
        },
        startRename: function (t) {
          this.renameId = t.id; this.renameText = this.name(t);
          this.$nextTick(function () { var i = document.getElementById("rec-rename-" + t.id); if (i) { i.focus(); i.select(); } });
        },
        saveRename: function (t) {
          if (this.renameId !== t.id) return;
          var v = String(this.renameText || "").replace(/\s+/g, " ").trim().slice(0, 80);
          t.name = v === this.t("take", { n: t.n }) ? "" : v;
          this.renameId = "";
          this.saveMeta(t);
          if (this.openId === t.id && this.panel === "send") this.prepare(t);
          this.focusTake(t.id);
        },
        cancelRename: function (t) { this.renameId = ""; this.focusTake(t.id); },
        focusTake: function (id) {
          this.$nextTick(function () { var h = document.getElementById("rec-take-" + id); if (h) h.focus(); });
        },
        remove: function (t) {
          var i = this.takes.indexOf(t), id = t.id, was = t.saved;
          if (this.openId === id) this.closePanel();
          revoke(t.url);
          delete SND[id]; delete PLAN[id]; delete REPLAY[id];
          Object.keys(FILES).forEach(function (k) { if (k.indexOf(id + ":") === 0) delete FILES[k]; });
          this.takes = this.takes.filter(function (x) { return x !== t; });
          this.confirmId = "";
          if (this.notice === "low" || (this.notice === "unsaved" && this.noticeId === id)) this.notice = "";
          var self = this, said = this.t("a_deleted", { name: this.name(t) });
          // (a write of it still on its way stops at its next step: save's alive)
          attempt(function () { return db.drop(id); }).then(function () { announce(said); }, function () { announce(self.keep && was ? self.s.e_delete : said); })
            .then(function () { unlockTake(id); self.retryAll(); });     // room made: the takes waiting for it, at once
          var next = this.takes[Math.min(i, this.takes.length - 1)];
          this.$nextTick(function () {
            var el = next ? document.getElementById("rec-take-" + next.id) : document.getElementById("rec-takes-title");
            if (el) el.focus();
          });
          this.guard();
        },
        // every take on this device (D11) — but a draft another tab is making (its lock; without Web Locks: written in
        // the last LIMITS.partFresh seconds) —, sound no take owns and no tab holds, and the first recorder's stores.
        // (Not while a take is being made or a job runs: they would write a take back afterwards — the button is
        // hidden then.)
        removeAll: function () {
          var self = this, now = Date.now();
          if (this.busy() || E.pending) return;
          // this page's own takes (listed, or still holding their lock): theirs go too, drafts included
          var own = Object.keys(E.locks).concat(this.takes.map(function (t) { return t.id; }));
          this.closePanel();
          this.takes.forEach(function (t) { revoke(t.url); });
          SND = {}; FILES = {}; PLAN = {}; REPLAY = {};
          this.takes = [];
          this.confirmAll = false;
          this.notice = "";
          this.clearDetails();                         // a shared computer: the next person starts blank
          attempt(function () { return Promise.all([readAll("takes"), keysOf("sound"), heldTakes()]); }).then(function (got) {
            var rows = got[0] || [], keys = got[1] || [], held = got[2], ids = {}, drop = {};
            own.forEach(function (id) { if (held) delete held[id]; });       // this page's own takes go too
            rows.forEach(function (r) {
              if (!r || typeof r.id !== "string") return;
              ids[r.id] = true;
              var busy = r.draft && (held ? held[r.id] : now - (Number(r.at) || 0) < L.partFresh * 1000);
              if (!busy || own.indexOf(r.id) >= 0) drop[r.id] = true;
            });
            keys.forEach(function (k) { var id = String(k).split(":")[0]; if (!ids[id] && !(held && held[id])) drop[id] = true; });
            return attempt(function () {
              return db.write(function (os) {
                Object.keys(drop).forEach(function (id) { os.takes["delete"](id); os.sound["delete"](range(R.soundRange(id))); });
                if (os.pcm) os.pcm.clear();
                if (os.mp3) os.mp3.clear();
                if (os.parts) os.parts.clear();
              });
            });
          }).then(function () { announce(self.s.a_deleted_all); }, function () { announce(self.s.e_delete); })
            .then(function () { own.forEach(unlockTake); });
          this.$nextTick(function () { var el = document.getElementById("rec-takes-title"); if (el) el.focus(); });
          this.guard();
        },
        clearDetails: function () {
          var v = this.send;
          v.topic = v.name = v.phone = v.email = v.address = v.place = v.credit = "";
          this.topicOther = false;
          this.reprep();
        },
        // "Keep my recordings on this device". Off with takes saved: asked first (confirmKeep), then the takes move
        // into this page and leave the device. Each change waits for the one before (E.keepP), so off-then-on
        // quickly never ends with an empty device; a take whose sound could not be read back stays on it.
        toggleKeep: function (ev) {
          var on = ev.target.checked;
          if (!on && this.takes.some(function (t) { return t.saved; })) {
            ev.target.checked = true;                 // not yet: the question first
            this.confirmKeep = true;
            this.$nextTick(function () { var b = document.getElementById("rec-keep-no"); if (b) b.focus(); });
            return;
          }
          this.setKeep(on);
        },
        setKeep: function (on) {
          var self = this, gen = E.keepGen = (E.keepGen || 0) + 1;
          this.keep = !!on; this.confirmKeep = false;
          // (off: "{name} isn't saved on this device yet — see Your takes" points at nothing now — no badge, no box —, and
          // nothing will be tried: it goes; on again, a save that fails says it again — r10 V5)
          if (!on && this.notice === "unsaved") this.notice = "";
          lsSet(R.KEEP_KEY, on ? "1" : "0");
          E.keepP = (E.keepP || Promise.resolve()).then(function () {
            if (gen !== E.keepGen) return null;
            if (on) {
              self.kept = !!window.indexedDB;
              // ("kept on this device" only when every take is; else what the storage box says)
              return Promise.all(self.takes.map(function (t) { return self.save(t.id); })).then(function (oks) {
                var why = { none: self.s.st_none, reload: self.s.st_reload, full: self.s.st_full, unsaved: self.s.st_unsaved }[self.storeNote()];
                announce(oks.every(Boolean) || !why ? self.s.a_keep_on : why);
              });
            }
            // each listed take's sound into this page, then that take off the device, one by one (never the whole
            // database: another tab's takes stay) — after a write of it still on its way, which stops (A4): what it
            // wrote goes with it; a take whose sound can't be read back stays on the device
            return self.takes.reduce(function (p, t) {
              return p.then(function () { return PLAN[t.id] && PLAN[t.id].busy; }).then(null, function () {}).then(function () {
                if (gen !== E.keepGen || t.damaged || !self.find(t.id)) return null;
                var S = snd(t.id);
                var got = t.saved ? Promise.all([self.pcmOf(t.id), t.mp3Size && !S.mp3 ? self.kindOf(t.id, "mp3") : null])
                  : Promise.resolve([S.pcm, null]);
                return got.then(function (b) {
                  if (!b[0] || gen !== E.keepGen) return null;
                  S.pcm = b[0]; S.mp3 = S.mp3 || b[1];
                  return attempt(function () { return db.drop(t.id); }).then(function () {
                    t.saved = false; t.failed = false; t.stuck = false; t.fails = 0; t.v = 2; t.mp3 = false;
                    t.size = S.pcm.byteLength + (S.mp3 ? S.mp3.byteLength : 0);
                    delete PLAN[t.id];
                  });
                }, function () { /* its sound can't be read back: it stays on the device */ });
              });
            }, Promise.resolve()).then(function () { announce(self.s.a_keep_off); });
          })["catch"](function () {}).then(function () { self.guard(); });
          this.guard();
        },

        /* ---------------- edit (a new take; the original stays) */
        openPanel: function (t, panel) {
          if (this.openId === t.id && this.panel === panel) { this.closePanel(); return; }
          this.closePanel();
          this.openId = t.id; this.panel = panel;
          if (panel === "send") {
            this.send.pub = t.pub;
            this.send.fmt = t.mp3Size ? "mp3" : "wav";
            this.prepare(t);
          } else if (panel === "edit") {
            this.edit = { start: 0, end: Math.round(R.duration(t) * 10) / 10, even: this.quiet(t) };
          }
        },
        closePanel: function () {
          this.openId = ""; this.panel = "";
          revoke(this.prep.url);
          this.prep = { key: "", url: "", size: 0, ready: false, failed: false };
          this.stopPreview();
        },
        // preview a trim: from the start mark, or the last 5 seconds before the end mark
        preview: function (t, where) {
          var a = document.getElementById("rec-audio-" + t.id);
          if (!a) return;
          var from = where === "end" ? Math.max(this.edit.start, this.edit.end - 5) : this.edit.start, end = this.edit.end;
          this.stopPreview();
          var stop = function () { if (a.currentTime >= end) { a.pause(); a.removeEventListener("timeupdate", stop); } };
          E.previewStop = function () { a.removeEventListener("timeupdate", stop); };
          a.addEventListener("timeupdate", stop);
          try { a.currentTime = from; } catch (e) { /* not loaded yet */ }
          var p = a.play();
          if (p && p["catch"]) p["catch"](function () {});
        },
        stopPreview: function () { if (E.previewStop) { E.previewStop(); E.previewStop = null; } },
        trimLabel: function (sec) { return R.clockTenths(sec); },
        clampEdit: function (t, which) {
          var d = R.duration(t), e = this.edit;
          e.start = Math.max(0, Math.min(Number(e.start) || 0, d));
          e.end = Math.max(0, Math.min(Number(e.end) || 0, d));
          if (e.end - e.start < L.minTake) {
            if (which === "start") e.start = Math.max(0, e.end - L.minTake); else e.end = Math.min(d, e.start + L.minTake);
          }
        },
        applyEdit: function (t) {
          var self = this, e = Object.assign({}, this.edit);
          if (this.takes.length >= L.maxTakes || this.rec()) return;     // (the panel says why; the button is off)
          this.askPersist();                           // (inside the tap)
          this.focusTake(t.id);                        // (the panel and its button go: the keyboard stays on the take)
          this.closePanel();
          this.queue(function () {
            self.job = { id: "", label: self.t("j_edit", { name: self.name(t) }), pct: 0 };
            return self.pcmOf(t.id).then(function (buf) {
              var all = new Int16Array(buf), r = R.trimRange(all.length, t.rate, e.start, e.end);
              var part = all.subarray(r.from, r.to), info = {};
              var gain = e.even ? R.gainFor(R.peak(part)) : 1;
              var out = gain !== 1 ? R.applyGain(part, gain, info) : part.slice();
              var pk = peaksOf(out);
              return encodePcm(self.cfg, out, t.rate, function (p) { if (self.job) self.job.pct = Math.round(p * 100); })
                .then(null, function () { return null; })
                .then(function (mp3) {
                  var meta = record({ id: R.newId(Date.now(), Math.random()), pub: t.pub, n: R.nextNumber(self.takes), created: Date.now(),
                    rate: t.rate, samples: out.length, peak: gain !== 1 ? info.peak : R.peak(out), peaks: pk, src: "edit", noise: t.noise,
                    from: t.n });
                  return self.add(meta, { pcm: out, mp3: mp3 }).then(function (ok) {
                    self.told(ok, meta, self.t("a_edited", { name: self.name(meta), from: self.name(t) }));
                    self.focusTake(meta.id);
                  });
                });
            });
          }, function () { announce(self.s.e_job); }, true);
        },

        /* ---------------- a recording made elsewhere (Voice Memos .m4a …) → a take */
        accept: function () { return R.accept(this.ios); },
        addFile: function (ev) {
          var self = this, input = ev.target, file = input.files && input.files[0];
          input.value = "";
          if (!file) return;
          this.importErr = "";
          var fail = function (k) { self.importErr = k; announce(k === "limit" ? self.t("n_limit", { max: L.maxTakes }) : self.s["e_" + k]); };
          if (this.takes.length >= L.maxTakes) { fail("limit"); return; }
          if (file.size > L.importBytes) { fail("import_big"); return; }
          this.askPersist();                           // (from the tap that chose the file)
          // (the file's own name is shown while it converts, never kept: Voice Memos names recordings after places)
          var base = String(file.name || "").replace(/\.[^.]+$/, "").slice(0, 80);
          this.queue(function () {
            self.job = { id: "", label: self.t("j_import", { name: base || "…" }), pct: 0 };
            // its length BEFORE decoding: a short file on disk can be an hour of sound, too much to hold whole
            return probeLength(file).then(function (sec) {
              if (sec > L.importSec) { fail("import_long"); return null; }
              return bufferOf(file).then(decode);
            }).then(function (ab) {
              if (!ab) return null;
              if (ab.duration > L.importSec) { fail("import_long"); return null; }
              self.roomFor(R.takeBytes(ab.duration, 44100));     // (room for it on the device: said, nothing stopped)
              var chans = [];
              for (var c = 0; c < ab.numberOfChannels; c++) chans.push(ab.getChannelData(c));
              var n = ab.length, out = new Int16Array(n), pos = 0, step = 44100;
              return new Promise(function (res) {
                (function slice() {
                  var t0 = perf();
                  while (pos < n && perf() - t0 < 40) {
                    var z = Math.min(n, pos + step);
                    out.set(R.toInt16(R.downmix(chans.map(function (ch) { return ch.subarray(pos, z); }))), pos);
                    pos = z;
                  }
                  if (self.job) self.job.pct = Math.round(pos / n * 50);
                  if (pos < n) setTimeout(slice, 0); else res(out);
                })();
              });
            }).then(function (i16) {
              if (!i16) return null;
              var pk = peaksOf(i16);
              return encodePcm(self.cfg, i16, 44100, function (p) { if (self.job) self.job.pct = 50 + Math.round(p * 50); })
                .then(null, function () { return null; })
                .then(function (mp3) {
                  var meta = record({ id: R.newId(Date.now(), Math.random()), pub: self.pub, n: R.nextNumber(self.takes), created: Date.now(),
                    rate: 44100, samples: i16.length, peak: Math.max.apply(null, pk.concat([0])), peaks: pk, src: "file", noise: false });
                  return self.add(meta, { pcm: i16, mp3: mp3 }).then(function (ok) {
                    self.told(ok, meta, self.t("a_imported", { name: self.name(meta), time: R.spoken(R.duration(meta), self.s.words) }));
                    self.focusTake(meta.id);
                  });
                });
            });
          }, function () { fail("import_bad"); }, true);
        },

        /* ---------------- send */
        // the file for Share / Download, made before the tap (share() must run inside it)
        prepare: function (t) {
          var self = this, fmt = this.send.fmt, key = t.id + ":" + fmt + ":" + this.fileName(t, fmt);
          if (this.prep.key === key && (this.prep.ready || !this.prep.failed)) return;
          revoke(this.prep.url);
          this.prep = { key: key, url: "", size: 0, ready: false, failed: false };
          var name = this.fileName(t, fmt), made;
          if (FILES[key]) made = Promise.resolve(FILES[key]);
          else if (fmt === "mp3") {
            made = this.kindOf(t.id, "mp3").then(function (b) { return new File([b], name, { type: "audio/mpeg" }); });
          } else {
            made = this.pcmOf(t.id).then(function (b) { return new File([R.wavHeader(t.rate, b.byteLength >> 1), b], name, { type: "audio/wav" }); });
          }
          made.then(function (f) {
            if (self.prep.key !== key) return;
            FILES = {}; FILES[key] = f;                      // one prepared file at a time (a WAV can be 50 MB)
            self.prep = { key: key, url: URL.createObjectURL(f), size: f.size, ready: true, failed: false };
          }, function () { if (self.prep.key === key) self.prep.failed = true; });
        },
        setFmt: function (t, fmt) { this.send.fmt = fmt; this.prepare(t); },
        // the magazine it goes to (the address, the message's language, the file's name)
        setTo: function (t, pub) { this.send.pub = pub === "lv" ? "lv" : "gv"; this.prepare(t); },
        file: function () { return FILES[this.prep.key] || null; },
        shareable: function () {
          var f = this.file();
          if (!this.can.share || !f) return false;
          // (Chrome and Edge refuse more than 50 MiB; Safari decides for itself through canShare)
          if (f.size > L.shareMax && this.help !== "ios" && this.help !== "safari") return false;
          try { return navigator.canShare({ files: [f] }); } catch (e) { return false; }
        },
        // Share (Mail, Gmail, WhatsApp to a sponsor, Drive…): with the message as text; "Save to Files": the file only
        share: function (t, withText) {
          var self = this, f = this.file();
          if (!f || !this.prep.ready) return;
          var data = { files: [f] }, topic = this.send.topic;
          if (withText) { data.title = this.subject(t); data.text = this.body(t); }
          try {
            // (shared: the file left the page under its name — savedAs; closed without sharing: it did not)
            navigator.share(data).then(function () { self.savedAs(t, topic); }, function (err) {
              // (AbortError: closed without sharing; InvalidStateError: a second tap while the sheet is up)
              if (err && err.name !== "AbortError" && err.name !== "InvalidStateError") announce(self.s.e_share);
            });
          } catch (e) { announce(self.s.e_share); }
        },
        // (Download: the browser saves it under this name — savedAs)
        downloaded: function (t) { this.savedAs(t); announce(this.t("a_downloaded", { file: this.fileName(t, this.send.fmt) })); },
        mag: function () { return this.cfg.pubs[this.send.pub] || {}; },
        mailTo: function () { return this.mag().email || ""; },
        values: function (t) {
          var v = this.send, m = this.cfg.mail[v.pub], cr = (this.cfg.credit[v.pub] || [])[Number(v.credit) - 1] || "";
          var o = { topic: v.topic.trim(), length: R.clock(R.duration(t)), file: this.fileName(t, v.fmt), format: v.fmt.toUpperCase(),
            name: v.name.trim(), phone: v.phone.trim(), email: v.email.trim(), address: v.address.trim(), place: v.place.trim(),
            credit: cr, permission: m.permission || "" };
          // the heading over the details ({?details}) only when there is a detail under it
          o.details = o.name || o.phone || o.email || o.address || o.place || o.credit ? "1" : "";
          return o;
        },
        subject: function (t) {
          var m = this.cfg.mail[this.send.pub], v = this.values(t);
          return R.fill(v.topic ? m.subject : m.subject_plain, v);
        },
        body: function (t) { return R.mailBody(this.cfg.mail[this.send.pub].body, this.values(t)); },
        short: function (t) { return R.fill(this.cfg.mail[this.send.pub].short, this.values(t)); },
        // Gmail / Outlook.com open in a new tab with the SHORT message: a web address stays in the browser's history
        // (on a shared computer, for the next person), so the details never go into it — the whole message is
        // copied as the link opens. mailto: hands the whole message to the mail program (cut when too long).
        mailLink: function (t, kind) {
          if (kind === "gmail" || kind === "outlook") {
            var r = (kind === "gmail" ? R.gmail : R.outlook)(this.mailTo(), this.subject(t), this.short(t), this.short(t));
            r.cut = true;
            return r;
          }
          return R.mailto(this.mailTo(), this.subject(t), this.body(t), this.short(t));
        },
        mailClick: function (t, kind) {
          if (this.mailLink(t, kind).cut && GV.copy) { GV.copy(this.body(t)); announce(this.s.a_body_copied); }
        },
        big: function () { return this.prep.size > L.bigMail; },

        /* ---------------- "Having trouble? Check this device" (THE DEVICE CHECK above) */
        // the panel opened: the check, the first time (then "Check again")
        checkOpen: function (ev) { if (ev && ev.target && ev.target.open && !this.diag.text && !this.diag.busy) this.diagnose(); },
        // What the report says (R.report keeps only REPORT's facts, each on one line): the day; the page's language and
        // version; the browser, its version and system (install-core.js detect(), when it has loaded) and its own words
        // (the user agent); a tab, the installed app or an app's built-in browser; online; a secure page; the microphone:
        // the browser has the means, and its permission (read, never asked); recording (R.support: the AudioWorklet or the
        // older ScriptProcessor, or why not); WebAssembly and the MP3 encoder (fetched as a take fetches it: ready, not
        // yet, or failed); IndexedDB written and read back (storageCheck); "Keep my recordings on this device"; kept until
        // the visitor deletes them (persisted); signs of a private window (priv; ephemeral: the browser may lose the
        // device's copy); free and used space (rounded); the screen kept on (wake lock); sharing a file; the takes on this
        // device — how many, not saved yet, can't be read —; the last storage error's name. No take's name, topic or
        // sound, no microphone's name.
        diagnose: function () {
          var self = this, cfg = this.cfg || {}, words = cfg.d || {}, run = E.checkN = (E.checkN || 0) + 1;
          var ua = navigator.userAgent || "", det = {};
          this.diag = { busy: true, text: this.diag.text };
          try {
            if (window.GVInstall) det = window.GVInstall.detect(ua, { touch: navigator.maxTouchPoints || 0, small: Math.min(screen.width, screen.height) < 600 }) || {};
          } catch (e) { det = {}; }
          var count = function (f) { return self.takes.filter(f).length; };
          var facts = {
            when: R.ymd(Date.now()),
            page: String(cfg.locale || "") + ((cfg.diag && cfg.diag.ver) ? " · " + cfg.diag.ver : ""),
            browser: { code: det.browser || "", more: det.version || "" },
            system: det.os || "",
            app: this.inApp ? { code: "inapp", more: det.app || "" } : this.standalone ? "installed" : "tab",
            online: navigator.onLine !== false,
            secure: window.isSecureContext !== false,
            mic_api: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
            record: this.can.record || this.can.why || "no_audio",
            wasm: !!this.can.wasm,
            keep: this.keep ? "on" : "off",
            priv: this.priv ? "yes" : this.ephemeral ? "maybe" : "no",
            wake: "wakeLock" in navigator,
            share: !!this.can.share,
            takes: this.takes.length,
            unsaved: count(function (t) { return !t.saved && !t.damaged; }),
            unreadable: count(function (t) { return !!t.damaged; }),
            error: this.lastErr || "none",
            ua: ua
          };
          var storage = navigator.storage || {};
          var ask = function (fn) { try { return Promise.resolve(fn()).then(null, function () { return null; }); } catch (e) { return Promise.resolve(null); } };
          var mp3 = !this.can.wasm ? Promise.resolve("none") : encMod ? Promise.resolve("ready")
            : within(encoderReady(cfg), 8).then(function () { return "ready"; }, function (err) { return err && err.name === "TimeoutError" ? "wait" : "failed"; });
          Promise.all([
            micState(), storageCheck(), mp3,
            ask(function () { return storage.persisted ? storage.persisted() : null; }),
            ask(function () { return storage.estimate ? storage.estimate() : null; })
          ]).then(function (r) {
            if (run !== E.checkN) return;
            var est = r[4] || {}, quota = Number(est.quota) || 0, used = Number(est.usage) || 0;
            facts.mic = r[0];
            facts.idb = r[1];
            facts.mp3 = r[2];
            facts.persisted = typeof r[3] === "boolean" ? r[3] : null;
            facts.free = quota > 0 ? self.size(Math.max(0, quota - used)) || "0" : null;
            facts.used = quota > 0 ? self.size(used) || "0" : null;
            self.diag = { busy: false, text: R.report(facts, words) };
            announce(words.ready);
          })["catch"](function () {
            if (run !== E.checkN) return;
            self.diag = { busy: false, text: R.report(facts, words) };
            announce(words.ready);
          });
        },
        // "E-mail it to the committee": the report to the site's address, sent by the visitor (a mailto: link — nothing is
        // sent by the page); too long for the link, the short message goes and the whole report is copied (mailClick)
        checkTo: function () { var c = this.cfg && this.cfg.diag; return (c && c.to) || ""; },
        checkMail: function () {
          var w = (this.cfg && this.cfg.d) || {};
          return R.mailto(this.checkTo(), w.title || "", this.diag.text + (w.ask ? "\n\n" + w.ask : ""), w.short || "");
        },
        checkMailClick: function () {
          var w = (this.cfg && this.cfg.d) || {};
          if (this.checkMail().cut && GV.copy) { GV.copy(this.diag.text); announce(w.short); }
        },

        /* ---------------- leaving the page */
        // while a take is being made or saved, an edit or an added recording is being made, or a take is only in this page
        // (atRisk): leaving asks first — beforeunload (closing the tab, Back: computers and Android) and the in-page
        // question on links (askLeave); html.cm-rec-hold tells pwa.js to hold its "Updated — Reload" notice. While a
        // take waits to be saved, it is tried again (RETRY_AT, then every LIMITS.retryEvery seconds).
        guard: function () {
          var self = this, need = this.atRisk(), root = document.documentElement;
          if (root && root.classList) root.classList[need ? "add" : "remove"]("cm-rec-hold");
          // (the browser's question stays on while it is needed; it lets the page go — once — for 3 s after a link the
          // visitor chose to follow anyway, or a mail, phone or calendar link, which leaves nothing: askLeave)
          if (need && !E.leave) {
            E.leave = function (e) {
              if (E.letGo && perf() - E.letGo < 3000) return;
              e.preventDefault(); e.returnValue = ""; return "";
            };
            window.addEventListener("beforeunload", E.leave);
          } else if (!need && E.leave) {
            window.removeEventListener("beforeunload", E.leave);
            E.leave = null;
          }
          // a take waiting to be saved: tried again RETRY_AT seconds after its write failed (soon: an iPhone asks nothing
          // before a reload), then every LIMITS.retryEvery seconds — and whenever the page is shown or hidden, goes
          // online, another take is saved or a take is deleted
          var waiting = this.keep && this.kept && this.takes.some(function (t) { return !t.saved && !t.damaged && t.failed; });
          if (waiting && !E.retryT) {
            E.retryN = 0;
            E.retryAt = perf() + RETRY_AT[0] * 1000;
            E.retryT = setInterval(function () {
              if (perf() < E.retryAt) return;
              E.retryN++;
              E.retryAt = perf() + 1000 * (E.retryN < RETRY_AT.length ? RETRY_AT[E.retryN] - RETRY_AT[E.retryN - 1] : L.retryEvery);
              self.retryAll();
            }, 1000);
            if (E.retryT && E.retryT.unref) E.retryT.unref();      // (Node's tests: never what keeps them running)
          } else if (!waiting && E.retryT) { clearInterval(E.retryT); E.retryT = 0; }
        },
        // a click (capture phase) on a link that takes this tab to another page (R.leaves) while atRisk(): the page asks
        // (window.confirm — it shows on iPhone too). Stay: the click does nothing (a link in the phone's menu: the menu
        // closes, so the take and its buttons are in view). Leave: it goes on as it was, with no beforeunload question
        // after it. A browser that shows no dialog (confirm answers false at once): it goes on. A plain click on a mail,
        // phone or text link, or on a calendar file (.ics): nothing is asked — nothing leaves —, and the browser's own
        // question lets that one pass (Chrome runs beforeunload for them).
        askLeave: function (e) {
          if (!e || !this.atRisk() || typeof window.confirm !== "function") return;
          var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
          if (!a || typeof a.href !== "string") return;
          var target = String(a.getAttribute("target") || "").toLowerCase(), keys = !!(e.ctrlKey || e.metaKey || e.shiftKey || e.altKey);
          var plain = !e.defaultPrevented && !keys && !(e.button || 0) && (!target || target === "_self" || target === "_top" || target === "_parent");
          if (plain && (/^(mailto|tel|sms):/i.test(a.href) || /\.ics$/i.test(a.href.split(/[?#]/)[0]))) { E.letGo = perf(); return; }
          var mine = !!a.closest("[data-rec-go], [data-copy], [data-share]") || a.getAttribute("href") === "#record";
          var leaving = R.leaves({ href: a.href, target: a.getAttribute("target") || "", download: a.hasAttribute("download"), go: mine,
            button: e.button || 0, keys: keys, prevented: !!e.defaultPrevented }, document.URL);
          if (!leaving) return;
          var t0 = perf(), ok = window.confirm(this.recBusy() ? this.s.leave_rec : this.s.leave_unsaved);
          if (!ok && perf() - t0 > 50) {
            e.preventDefault();
            var menu = a.closest("#mobile-drawer"), shut = menu && menu.querySelector('[x-ref="drawerClose"]');
            if (shut) shut.click();
            return;
          }
          E.letGo = perf();
        },
        // one take plays at a time
        onPlay: function (ev) {
          document.querySelectorAll("[data-rec-audio]").forEach(function (a) { if (a !== ev.target && !a.paused) a.pause(); });
        }
      };
    });
  });
})();
