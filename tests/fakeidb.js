/* A pretend browser storage world for running the site's scripts in Node.js tests: IndexedDB, Web Locks,
   navigator.storage, a clock with timers the test moves on, and window.confirm — shared by every "page" (vm
   context) made from it, so what one page stores is there for the next page load, as in a browser.
   An ES module, run in Node's own realm (tests import it: imp("tests/fakeidb.js")); the pages get its objects.

     const W = createWorld();                       // one browser profile (one origin)
     const tab = W.client("page 1");                // one page load: tab.globals → put into the page's vm context
     … the page runs …
     await W.tick(3000);                            // the clock moves on 3 s: every timer due runs, in order
     await W.until(() => C.loaded);                 // …or until something is true (false after `within` ms)
     const v = await W.wait(C.add(…));              // …or until a promise settles (its value, or it throws)
     await W.idle();                                // …or until no timeout is waiting (intervals go on)
     W.errors                                       // what a timer or an event handler of a page threw
     tab.close();                                   // the page goes: its timers, transactions, locks and connections
     const tab2 = W.client("page 2");               // the next page load: the same databases

   TIME — W.now (Date.now()), W.perf() (performance.now()); nothing runs until the test moves the clock. Between two
   timers every promise settles (microtasks), as between two tasks in a browser.

   INDEXEDDB (W.idb) — what a page sees is the API (open with versions and onupgradeneeded(oldVersion), blocked and
   versionchange, objectStoreNames, keyPath / autoIncrement stores, get / getAll / getAllKeys / count / put / add /
   delete(key | range) / clear / openCursor / openKeyCursor, IDBKeyRange.only / bound / lowerBound / upperBound,
   transactions with scopes, auto-commit and tx.commit()). As in a browser:
     * values are structured clones (structuredClone: a view's WHOLE buffer is copied; a function → DataCloneError,
       thrown by put()); keys compare as IndexedDB keys (number < Date < string < binary < array)
     * requests are answered one per task, in order; a transaction completes after its last request, once the page
       can no longer add one (it stays "active" only in the task that made it and in its requests' events, with their
       promises — TransactionInactiveError after that)
     * transactions whose scopes overlap run one after the other (readonly ones together); a readwrite transaction's
       writes reach the database only when it commits, all of them or none
     * a request that fails fires "error" at the request, then the transaction, then the database (tx.error is still
       null then); unless an onerror called preventDefault(), the transaction aborts: the requests still waiting fail
       with AbortError, then "abort" fires with tx.error = the first error (WebKit's order, r10 repro-report.md)
     * an exception thrown in a request's onsuccess / onerror aborts its transaction (AbortError)
   What the test can do (W.idb):
     log                every request a page made: {op, db, store, key, value (the clone), blob (the value held a
                        Blob), client, ok, error}
     fail(rule)         make requests fail → a handle {off(), seen, hits}. rule = {op: "put" | "add" | "get" | "getAll"
                        | "getAllKeys" | "count" | "delete" | "clear" | "cursor" | "read" (any read) | "write" (any
                        write) | "commit" | "transaction" | "open" | "any", store, db, key (a key, or a function of
                        it — a read fails when it would return that record), match(info), name ("QuotaExceededError",
                        "UnknownError", "AbortError", "VersionError", "InvalidStateError" …), message, nth (only the
                        nth matching op, 1-based), times (how many failures; default: all, or 1 with nth), hang (it
                        never answers), blocked (an open: "blocked", then it waits for handle.release()), sync (a put /
                        add that throws at once, as put() throws DataCloneError: nothing is requested)}
                        "transaction" makes db.transaction() throw; "commit" aborts the transaction when it would commit
     clearFaults()
     refuseBlobs        true: every value holding a Blob or File is refused — UnknownError "Error preparing Blob/File
                        data to be stored in object store" (Safari's Private Browsing, WebKit 156347)
     quota              bytes: a commit that would leave more than this stored aborts with QuotaExceededError
                        (as browsers report it: tx.error in onabort, no request error)
     latency            ms each request takes (0: the next task)
     features           {getAll, getAllKeys, commit, openKeyCursor}: false hides that method (older Safari)
     database(name)     the database as it is stored: {version, storeNames(), store(n) → {keyPath, keys(), get(k),
                        all(), put(v), delete(k), clear(), size}} — to put rows in place (a v1 database, a damaged row)
                        or look at them; create(name, version, {store: {keyPath, autoIncrement}}) makes one
     loseConnections({db, client, name, silent})   the browser drops the connections (WebKit "Connection to Indexed
                        Database server lost"): their transactions abort, then "close" fires (not with silent: iOS 17-18
                        were seen not to fire it); db.transaction() throws InvalidStateError meanwhile
     loseAll()          …and every database is gone with them (Safari's private window: iOS ended the process that
                        held them) — the next open makes a new one
     bytes()            what is stored (as navigator.storage.estimate() reports it)
   LOCKS (W.locks) — navigator.locks.request(name, {ifAvailable, mode}, cb) and query(); a page's locks go with it.
     W.locks.hold(name) → release(): another tab holds that lock. W.locks.names() → the held names.
   STORAGE (W.storage) — navigator.storage: estimate() {quota, usage: stored bytes + extra}, persist() (answers
     `grant`; counted in calls.persist), persisted(), getDirectory() (rejects in a private window: private = true).
   DIALOGS — tab.confirm(message): tab.dialogs gets the message; tab.answer(message) → {answer, after: ms} (default:
     Cancel after 100 ms): the clock moves on `after` ms while the dialog is up (no timer runs meanwhile). */

const START = Date.parse("2026-10-14T15:00:00Z");

export function named(name, message) {
  return new DOMException(message || name, name);
}
const toTag = (v) => Object.prototype.toString.call(v);
const isBlob = (v) => v != null && typeof v === "object" && (toTag(v) === "[object Blob]" || toTag(v) === "[object File]");
const isBytes = (v) => v != null && typeof v === "object" && typeof v.byteLength === "number" &&
  (toTag(v) === "[object ArrayBuffer]" || ArrayBuffer.isView(v));

// does a value hold a Blob or File anywhere inside it?
export function hasBlob(v, seen = new Set()) {
  if (v == null || typeof v !== "object") return false;
  if (isBlob(v)) return true;
  if (isBytes(v) || seen.has(v)) return false;
  seen.add(v);
  if (v instanceof Map || toTag(v) === "[object Map]") { for (const [k, x] of v) if (hasBlob(k, seen) || hasBlob(x, seen)) return true; return false; }
  if (v instanceof Set || toTag(v) === "[object Set]") { for (const x of v) if (hasBlob(x, seen)) return true; return false; }
  for (const k of Object.keys(v)) if (hasBlob(v[k], seen)) return true;
  return false;
}
// roughly what a value takes on the device (bytes)
export function sizeOf(v, seen = new Set()) {
  if (v == null) return 0;
  if (typeof v === "string") return v.length * 2;
  if (typeof v !== "object") return 8;
  if (isBlob(v)) return v.size;
  if (isBytes(v)) return v.byteLength;
  if (seen.has(v)) return 0;
  seen.add(v);
  let n = 16;
  for (const k of Object.keys(v)) n += k.length * 2 + sizeOf(v[k], seen);
  return n;
}

/* ---------------------------------------------------------------- IndexedDB keys */
function keyType(k) {
  if (typeof k === "number") return Number.isNaN(k) ? null : 1;
  if (k instanceof Date || toTag(k) === "[object Date]") return Number.isNaN(k.getTime()) ? null : 2;
  if (typeof k === "string") return 3;
  if (isBytes(k)) return 4;
  if (Array.isArray(k)) return k.every((x) => keyType(x) != null) ? 5 : null;
  return null;
}
export function validKey(k) { return keyType(k) != null; }
const bytesOfKey = (k) => (ArrayBuffer.isView(k) ? new Uint8Array(k.buffer, k.byteOffset, k.byteLength) : new Uint8Array(k));
export function cmp(a, b) {
  const ta = keyType(a), tb = keyType(b);
  if (ta == null || tb == null) throw named("DataError", "Data provided to an operation does not meet requirements.");
  if (ta !== tb) return ta < tb ? -1 : 1;
  if (ta === 1) return a === b ? 0 : a < b ? -1 : 1;
  if (ta === 2) { const x = a.getTime(), y = b.getTime(); return x === y ? 0 : x < y ? -1 : 1; }
  if (ta === 3) return a === b ? 0 : a < b ? -1 : 1;            // (UTF-16 code units, as IndexedDB)
  if (ta === 4) {
    const x = bytesOfKey(a), y = bytesOfKey(b);
    for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
    return x.length === y.length ? 0 : x.length < y.length ? -1 : 1;
  }
  for (let i = 0; i < Math.min(a.length, b.length); i++) { const c = cmp(a[i], b[i]); if (c) return c; }
  return a.length === b.length ? 0 : a.length < b.length ? -1 : 1;
}
export class FakeKeyRange {
  constructor(lower, upper, lowerOpen, upperOpen) {
    this.lower = lower; this.upper = upper; this.lowerOpen = !!lowerOpen; this.upperOpen = !!upperOpen;
  }
  includes(k) {
    if (this.lower !== undefined) { const c = cmp(k, this.lower); if (c < 0 || (c === 0 && this.lowerOpen)) return false; }
    if (this.upper !== undefined) { const c = cmp(k, this.upper); if (c > 0 || (c === 0 && this.upperOpen)) return false; }
    return true;
  }
  static only(k) { if (!validKey(k)) throw named("DataError"); return new FakeKeyRange(k, k, false, false); }
  static lowerBound(k, open) { if (!validKey(k)) throw named("DataError"); return new FakeKeyRange(k, undefined, open, true); }
  static upperBound(k, open) { if (!validKey(k)) throw named("DataError"); return new FakeKeyRange(undefined, k, true, open); }
  static bound(lo, hi, lo2, hi2) {
    if (!validKey(lo) || !validKey(hi)) throw named("DataError");
    const c = cmp(lo, hi);
    if (c > 0 || (c === 0 && (lo2 || hi2))) throw named("DataError", "The lower key is greater than the upper key.");
    return new FakeKeyRange(lo, hi, lo2, hi2);
  }
}
// a query (a key, a range, or nothing) → a range; null = every record
function toRange(q, needed) {
  if (q === undefined || q === null) { if (needed) throw named("DataError", "No key or key range specified."); return null; }
  if (q instanceof FakeKeyRange) return q;
  if (!validKey(q)) throw named("DataError", "The parameter is not a valid key.");
  return FakeKeyRange.only(q);
}
function keyAt(value, path) {
  if (Array.isArray(path)) { const out = path.map((p) => keyAt(value, p)); return out.some((k) => k === undefined) ? undefined : out; }
  if (path === "") return value;
  let v = value;
  for (const part of path.split(".")) { if (v == null || typeof v !== "object" || !(part in v)) return undefined; v = v[part]; }
  return v;
}
function setKeyAt(value, path, key) {
  const parts = path.split("."), last = parts.pop();
  let v = value;
  for (const p of parts) { if (v[p] == null) v[p] = {}; v = v[p]; }
  v[last] = key;
}
const strList = (names) => {
  const a = [...names].sort();
  const list = { length: a.length, contains: (n) => a.includes(String(n)), item: (i) => (i >= 0 && i < a.length ? a[i] : null), [Symbol.iterator]: () => a[Symbol.iterator]() };
  a.forEach((n, i) => { list[i] = n; });
  return list;
};

/* ---------------------------------------------------------------- events */
class Target {
  addEventListener(type, fn) { if (!fn) return; ((this._l = this._l || {})[type] = this._l[type] || []).push(fn); }
  removeEventListener(type, fn) { const l = this._l && this._l[type]; if (l) { const i = l.indexOf(fn); if (i >= 0) l.splice(i, 1); } }
}
function makeEvent(type, init) {
  return Object.assign({
    type, bubbles: false, cancelable: false, defaultPrevented: false, target: null, currentTarget: null, _stop: false, _threw: null,
    preventDefault() { if (this.cancelable) this.defaultPrevented = true; },
    stopPropagation() { this._stop = true; }, stopImmediatePropagation() { this._stop = true; },
  }, init || {});
}
// fire `ev` at path[0], bubbling up the rest when it bubbles; an exception in a handler is kept (ev._threw)
function dispatch(W, path, ev) {
  ev.target = ev.target || path[0];
  for (const t of ev.bubbles ? path : path.slice(0, 1)) {
    if (ev._stop) break;
    ev.currentTarget = t;
    const fns = [];
    if (typeof t["on" + ev.type] === "function") fns.push(t["on" + ev.type]);
    if (t._l && t._l[ev.type]) fns.push(...t._l[ev.type]);
    for (const f of fns) {
      try { f.call(t, ev); } catch (e) { ev._threw = ev._threw || e; W.errors.push(e); }
    }
  }
  return ev;
}

/* ---------------------------------------------------------------- IndexedDB: what is stored */
class StoreData {
  constructor(name, keyPath, autoIncrement) {
    this.name = name; this.keyPath = keyPath === undefined ? null : keyPath; this.autoIncrement = !!autoIncrement;
    this.gen = 1; this.recs = [];                          // [{key, value}] in key order
  }
  copy() { const s = new StoreData(this.name, this.keyPath, this.autoIncrement); s.gen = this.gen; s.recs = this.recs.slice(); return s; }
  find(key) {
    let lo = 0, hi = this.recs.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1, c = cmp(this.recs[mid].key, key);
      if (c === 0) return { i: mid, found: true };
      if (c < 0) lo = mid + 1; else hi = mid;
    }
    return { i: lo, found: false };
  }
  get(key) { const f = this.find(key); return f.found ? this.recs[f.i] : undefined; }
  set(key, value) {
    const f = this.find(key);
    if (f.found) this.recs[f.i] = { key, value }; else this.recs.splice(f.i, 0, { key, value });
    if (this.autoIncrement && typeof key === "number" && key >= this.gen) this.gen = Math.floor(key) + 1;
  }
  del(range) { this.recs = this.recs.filter((r) => !range.includes(r.key)); }
  inRange(range) { return range ? this.recs.filter((r) => range.includes(r.key)) : this.recs.slice(); }
  bytes() { return this.recs.reduce((n, r) => n + sizeOf(r.value), 0); }
}
class DbData {
  constructor(name) { this.name = name; this.version = 0; this.stores = new Map(); this.conns = new Set(); this.txs = []; this.waiting = []; }
}

/* ---------------------------------------------------------------- IndexedDB: the page's objects */
class FakeRequest extends Target {
  constructor(source, tx) {
    super();
    this.source = source; this.transaction = tx; this.readyState = "pending";
    this.onsuccess = null; this.onerror = null;
    this._result = undefined; this._error = null; this._run = null; this._entry = null; this._hang = false;
  }
  get result() { if (this.readyState !== "done") throw named("InvalidStateError", "The request has not finished."); return this._result; }
  get error() { if (this.readyState !== "done") throw named("InvalidStateError", "The request has not finished."); return this._error; }
}

class FakeStore {
  constructor(tx, name) {
    const d = tx.db._D.stores.get(name), f = tx._W.idb.features;
    this.transaction = tx; this.name = name; this.keyPath = d.keyPath; this.autoIncrement = d.autoIncrement;
    this.indexNames = strList([]);
    if (!f.getAll) this.getAll = undefined;
    if (!f.getAllKeys) this.getAllKeys = undefined;
    if (!f.openKeyCursor) this.openKeyCursor = undefined;
  }
  _check(write) {
    const tx = this.transaction;
    if (!tx.db._D.stores.has(this.name)) throw named("InvalidStateError", "The object store has been deleted.");
    if (tx._state !== "active") throw named("TransactionInactiveError", "The transaction is not active.");
    if (write && tx.mode === "readonly") throw named("ReadOnlyError", "The transaction is read-only.");
  }
  // a request: keys(data) → the records it reads (what a fault rule's `key` is checked against); fn(data) → its result
  _req(op, info, keys, fn, write) {
    this._check(write);
    const tx = this.transaction, W = tx._W;
    info = Object.assign({ op, db: tx.db.name, store: this.name, mode: tx.mode, client: tx.db._client ? tx.db._client.label : "" }, info);
    const req = new FakeRequest(this, tx);
    if (write) { req._entry = W.idb._logWrite(info); tx._entries.push(req._entry); }
    req._run = () => {
      const data = tx._data(this.name);
      info.keys = keys(data);
      const f = W.idb._fault(info);
      if (f && f.hang) { req._hang = true; return undefined; }
      if (f) throw named(f.name || "UnknownError", f.message);
      if (write && info.blob && W.idb.refuseBlobs) throw named("UnknownError", "Error preparing Blob/File data to be stored in object store");
      return fn(data);
    };
    tx._add(req);
    return req;
  }
  _write(op, value, key) {
    this._check(true);
    let clone;
    try { clone = structuredClone(value); } catch (e) { throw named("DataCloneError", String((e && e.message) || e)); }
    let k;
    if (this.keyPath != null) {
      if (key !== undefined) throw named("DataError", "The object store uses in-line keys and the key parameter was provided.");
      k = keyAt(clone, this.keyPath);
      if (k === undefined && !this.autoIncrement) throw named("DataError", "Evaluating the object store's key path did not yield a value.");
    } else {
      k = key;
      if (k === undefined && !this.autoIncrement) throw named("DataError", "The object store uses out-of-line keys and has no key generator and the key parameter was not provided.");
    }
    if (k !== undefined && !validKey(k)) throw named("DataError", "The key is not a valid key.");
    const tx = this.transaction;
    const thrown = tx._W.idb._fault({ op, sync: true, db: tx.db.name, store: this.name, mode: tx.mode, key: k, keys: k === undefined ? [] : [k],
      value: clone, client: tx.db._client ? tx.db._client.label : "" });
    if (thrown) throw named(thrown.name || "DataCloneError", thrown.message);
    return this._req(op, { key: k, value: clone, blob: hasBlob(clone) }, () => (k === undefined ? [] : [k]), (data) => {
      let kk = k;
      if (kk === undefined) { kk = data.gen++; if (this.keyPath != null) setKeyAt(clone, this.keyPath, kk); }
      if (op === "add" && data.get(kk)) throw named("ConstraintError", "Key already exists in the object store.");
      data.set(kk, clone);
      return kk;
    }, true);
  }
  put(value, key) { return this._write("put", value, key); }
  add(value, key) { return this._write("add", value, key); }
  get(q) {
    const range = toRange(q, true);
    const first = (d) => d.inRange(range)[0];
    return this._req("get", { range }, (d) => (first(d) ? [first(d).key] : []), (d) => (first(d) ? structuredClone(first(d).value) : undefined));
  }
  getKey(q) {
    const range = toRange(q, true);
    return this._req("getKey", { range }, () => [], (d) => { const r = d.inRange(range)[0]; return r ? structuredClone(r.key) : undefined; });
  }
  getAll(q, count) {
    const range = toRange(q, false), n = count ? Number(count) : 0;
    const list = (d) => { const a = d.inRange(range); return n > 0 ? a.slice(0, n) : a; };
    return this._req("getAll", { range }, (d) => list(d).map((r) => r.key), (d) => list(d).map((r) => structuredClone(r.value)));
  }
  getAllKeys(q, count) {
    const range = toRange(q, false), n = count ? Number(count) : 0;
    return this._req("getAllKeys", { range }, () => [], (d) => { const a = d.inRange(range); return (n > 0 ? a.slice(0, n) : a).map((r) => structuredClone(r.key)); });
  }
  count(q) {
    const range = toRange(q, false);
    return this._req("count", { range }, () => [], (d) => d.inRange(range).length);
  }
  delete(q) {
    const range = toRange(q, true);
    return this._req("delete", { range, key: range.lower === range.upper ? range.lower : undefined }, (d) => d.inRange(range).map((r) => r.key),
      (d) => { d.del(range); return undefined; }, true);
  }
  clear() {
    return this._req("clear", {}, (d) => d.recs.map((r) => r.key), (d) => { d.recs = []; return undefined; }, true);
  }
  openCursor(q, dir) { return this._cursor(q, dir, true); }
  openKeyCursor(q, dir) { return this._cursor(q, dir, false); }
  _cursor(q, dir, withValue) {
    const range = toRange(q, false), back = /^prev/.test(dir || ""), self = this;
    let last, next = null, skip = 0, req = null;
    const find = (d) => {
      const a = d.inRange(range);
      if (back) a.reverse();
      next = a.find((r) => last === undefined || (back ? cmp(r.key, last) < 0 : cmp(r.key, last) > 0)) || null;
    };
    const cursor = {
      source: self, direction: dir || "next", key: undefined, primaryKey: undefined, value: undefined,
      get request() { return req; },
      continue() {
        self._check(false);
        if (req.readyState !== "done") throw named("InvalidStateError", "The cursor is being iterated or has iterated past its end.");
        req.readyState = "pending";
        self.transaction._add(req);
      },
      advance(n) { if (!(n > 0)) throw new TypeError("advance: the count must be above 0"); skip = n - 1; cursor.continue(); },
    };
    req = this._req("cursor", { range }, (d) => {
      find(d);
      while (skip > 0 && next) { skip--; last = next.key; find(d); }
      return next && withValue ? [next.key] : [];
    }, () => {
      if (!next) return null;
      last = next.key;
      cursor.key = structuredClone(next.key); cursor.primaryKey = cursor.key;
      if (withValue) cursor.value = structuredClone(next.value);
      return cursor;
    });
    return req;
  }
  index(name) { throw named("NotFoundError", `No index named "${name}".`); }
  createIndex() { throw named("InvalidStateError", "Indexes are not part of this fake."); }
}

class FakeTx extends Target {
  constructor(W, db, scope, mode) {
    super();
    this._W = W; this.db = db; this.mode = mode; this.error = null; this.durability = "default";
    this.oncomplete = null; this.onerror = null; this.onabort = null;
    this._scope = scope.slice(); this._state = "active"; this._started = false; this._busy = false; this._queue = [];
    this._work = null; this._hung = null; this._entries = []; this._onDone = null; this._id = ++W.idb._n;
    if (!W.idb.features.commit) this.commit = undefined;
    db._D.txs.push(this);
    W._cleanup.push(() => this._deactivate());
    W.idb._schedule(db._D);
  }
  get objectStoreNames() { return strList(this._scope); }
  objectStore(name) {
    if (this._state === "finished") throw named("InvalidStateError", "The transaction has finished.");
    if (!this._scope.includes(name)) throw named("NotFoundError", `The object store "${name}" is not in this transaction's scope.`);
    return new FakeStore(this, name);
  }
  abort() {
    if (this._state === "finished" || this._state === "committing") throw named("InvalidStateError", "The transaction is inactive or finished.");
    this._abort(null);
  }
  commit() {
    if (this._state !== "active") throw named("InvalidStateError", "The transaction is not active.");
    this._state = "committing";
    this._pump();
  }
  _deactivate() { if (this._state === "active") { this._state = "inactive"; this._pump(); } }
  // the store as this transaction sees it: its own copy once it writes (its writes land only when it commits)
  _data(name) {
    if (this.mode === "readonly") return this.db._D.stores.get(name);
    this._work = this._work || new Map();
    if (!this._work.has(name)) this._work.set(name, this.db._D.stores.get(name).copy());
    return this._work.get(name);
  }
  _add(req) { this._queue.push(req); this._pump(); }
  _pump() {
    if (!this._started || this._state === "finished" || this._busy) return;
    if (this._queue.length) { this._busy = true; this._W._post(() => this._step(), this._W.idb.latency); return; }
    if (this._state === "inactive" || this._state === "committing") { this._busy = true; this._W._post(() => this._commit(), 0); }
  }
  _step() {
    this._busy = false;
    if (this._state === "finished") return;
    const W = this._W, req = this._queue.shift();
    if (!req) { this._pump(); return; }
    let ok = true, result, error = null;
    try { result = req._run(); } catch (e) { ok = false; error = e; }
    if (req._hang) { this._busy = true; this._hung = req; return; }          // it never answers
    req.readyState = "done"; req._result = ok ? result : undefined; req._error = ok ? null : error;
    if (req._entry) { req._entry.ok = ok; req._entry.error = ok ? null : error.name; }
    if (this._state === "inactive") this._state = "active";
    const ev = ok ? makeEvent("success") : makeEvent("error", { bubbles: true, cancelable: true });
    dispatch(W, ok ? [req] : [req, this, this.db], ev);
    W._cleanup.push(() => this._deactivate());
    if (this._state === "finished") return;
    if (!ok && !ev.defaultPrevented) { this._abort(error); return; }
    if (ev._threw) { this._abort(named("AbortError", "An exception was thrown in an event handler.")); return; }
    this._pump();
  }
  _commit() {
    this._busy = false;
    if (this._state === "finished") return;
    if (this._queue.length || this._state === "active") { this._pump(); return; }
    const W = this._W, D = this.db._D;
    if (this.mode !== "readonly") {
      const f = W.idb._fault({ op: "commit", db: D.name, stores: this._scope, mode: this.mode, client: this.db._client ? this.db._client.label : "" });
      if (f && f.hang) { this._busy = true; return; }
      if (f) { this._abort(named(f.name || "AbortError", f.message)); return; }
      if (W.idb.quota != null && this._work) {
        let after = W.idb.bytes();
        for (const [n, s] of this._work) after += s.bytes() - (D.stores.has(n) ? D.stores.get(n).bytes() : 0);
        if (after > W.idb.quota) { this._abort(named("QuotaExceededError", "The quota has been exceeded.")); return; }
      }
      if (this._work) for (const [n, s] of this._work) if (D.stores.has(n)) D.stores.set(n, s);
    }
    this._entries.forEach((e) => { e.committed = true; });
    this._end();
    W._post(() => { dispatch(W, [this], makeEvent("complete")); if (this._onDone) this._onDone(true); }, 0);
  }
  // aborted: nothing it wrote stays; its waiting requests fail (AbortError), then "abort" — tx.error = why (null: abort())
  _abort(error, silent) {
    if (this._state === "finished") return;
    const W = this._W;
    this._work = null; this.error = error;
    const pending = (this._hung ? [this._hung] : []).concat(this._queue.splice(0));
    this._hung = null;
    for (const r of pending) {
      r.readyState = "done"; r._result = undefined; r._error = named("AbortError", "The transaction was aborted, so the request cannot be fulfilled.");
      if (r._entry) { r._entry.ok = false; r._entry.error = "AbortError"; }
    }
    this._entries.forEach((e) => { e.committed = false; });
    this._end();
    W._post(() => {
      if (!silent) {
        for (const r of pending) dispatch(W, [r, this, this.db], makeEvent("error", { bubbles: true, cancelable: true }));
        dispatch(W, [this, this.db], makeEvent("abort", { bubbles: true }));
      }
      if (this._onDone) this._onDone(false);
    }, 0);
  }
  _end() {
    this._state = "finished"; this._busy = false;
    const D = this.db._D, i = D.txs.indexOf(this);
    if (i >= 0) D.txs.splice(i, 1);
    this._W.idb._schedule(D);
  }
}

class FakeDB extends Target {
  constructor(W, D, version, client) {
    super();
    this._W = W; this._D = D; this._client = client; this._closed = false; this._upgrade = null;
    this.name = D.name; this.version = version;
    this.onabort = null; this.onclose = null; this.onerror = null; this.onversionchange = null;
  }
  get objectStoreNames() { return strList(this._D.stores.keys()); }
  _upgrading() {
    const tx = this._upgrade;
    if (!tx || tx._state === "finished") throw named("InvalidStateError", "Not in a version change transaction.");
    if (tx._state !== "active") throw named("TransactionInactiveError", "The version change transaction is not active.");
    return tx;
  }
  createObjectStore(name, opts) {
    const tx = this._upgrading();
    opts = opts || {};
    name = String(name);
    if (this._D.stores.has(name)) throw named("ConstraintError", `An object store named "${name}" already exists.`);
    const kp = opts.keyPath === undefined ? null : opts.keyPath;
    if (opts.autoIncrement && (kp === "" || Array.isArray(kp))) throw named("InvalidAccessError", "autoIncrement with an empty or array key path.");
    this._D.stores.set(name, new StoreData(name, kp, opts.autoIncrement));
    if (!tx._scope.includes(name)) tx._scope.push(name);
    return new FakeStore(tx, name);
  }
  deleteObjectStore(name) {
    this._upgrading();
    if (!this._D.stores.has(name)) throw named("NotFoundError", `No object store named "${name}".`);
    this._D.stores.delete(name);
  }
  transaction(names, mode, options) {
    const W = this._W;
    mode = mode === undefined ? "readonly" : mode;
    if (this._closed) throw named("InvalidStateError", "The database connection is closing.");
    if (this._upgrade && this._upgrade._state !== "finished") throw named("InvalidStateError", "A version change transaction is running.");
    const scope = [...new Set((typeof names === "string" ? [names] : [...names]).map(String))];
    if (!scope.length) throw named("InvalidAccessError", "The storeNames parameter was empty.");
    for (const n of scope) if (!this._D.stores.has(n)) throw named("NotFoundError", "One of the specified object stores was not found.");
    if (mode !== "readonly" && mode !== "readwrite") throw new TypeError(`'${mode}' is not a valid transaction mode.`);
    const f = W.idb._fault({ op: "transaction", db: this.name, stores: scope, mode, client: this._client ? this._client.label : "" });
    if (f) throw named(f.name || "InvalidStateError", f.message || "The database connection is closing.");
    const tx = new FakeTx(W, this, scope, mode);
    if (options && options.durability) tx.durability = options.durability;
    return tx;
  }
  close() {
    if (this._closed) return;
    this._closed = true;
    this._D.conns.delete(this);
    this._W.idb._retryOpens(this._D);
  }
}

class FakeFactory {
  constructor(W, client) { this._W = W; this._client = client; }
  open(name, version) {
    const W = this._W, client = this._client;
    name = String(name);
    if (version !== undefined) {
      version = Number(version);
      if (!Number.isInteger(version) || version < 1) throw new TypeError("The version provided must be a whole number above 0.");
    }
    const req = new FakeRequest(null, null);
    req.onupgradeneeded = null; req.onblocked = null;
    W.idb.opens.push({ db: name, version, client: client.label });
    W._post(() => W.idb._open(req, name, version, client), W.idb.latency);
    return req;
  }
  deleteDatabase(name) {
    const W = this._W, req = new FakeRequest(null, null);
    req.onblocked = null; req.onupgradeneeded = null;
    W._post(() => {
      const D = W.idb.dbs.get(String(name)), old = D ? D.version : 0;
      const done = () => { W.idb.dbs.delete(String(name)); req.readyState = "done"; req._result = undefined; dispatch(W, [req], makeEvent("success", { oldVersion: old, newVersion: null })); };
      if (!D || !D.conns.size) { done(); return; }
      for (const c of D.conns) dispatch(W, [c], makeEvent("versionchange", { oldVersion: old, newVersion: null }));
      W._post(() => {
        if (D.conns.size) { dispatch(W, [req], makeEvent("blocked", { oldVersion: old, newVersion: null })); D.waiting.push(done); } else done();
      }, 0);
    }, 0);
    return req;
  }
  databases() {
    return Promise.resolve([...this._W.idb.dbs.values()].filter((d) => d.version > 0).map((d) => ({ name: d.name, version: d.version })));
  }
  cmp(a, b) { return cmp(a, b); }
}

/* ---------------------------------------------------------------- IndexedDB: the browser's side */
const READS = ["get", "getKey", "getAll", "getAllKeys", "count", "cursor"];
const WRITES = ["put", "add", "delete", "clear"];
const OTHER = ["open", "transaction", "commit"];
function ruleMatches(rule, info) {
  const op = rule.op || "any";
  if (op === "read") { if (!READS.includes(info.op)) return false; }
  else if (op === "write") { if (!WRITES.includes(info.op)) return false; }
  else if (op === "any") { if (OTHER.includes(info.op)) return false; }
  else if (op !== info.op) return false;
  if (!!rule.sync !== !!info.sync) return false;
  if (rule.db && rule.db !== info.db) return false;
  if (rule.client && rule.client !== info.client) return false;
  if (rule.store && rule.store !== info.store && !(info.stores || []).includes(rule.store)) return false;
  if ("key" in rule) {
    const want = rule.key, test = typeof want === "function" ? want : (k) => { try { return cmp(k, want) === 0; } catch (e) { return false; } };
    if (!(info.keys || []).some((k) => test(k))) return false;
  }
  if (rule.match && !rule.match(info)) return false;
  return true;
}
function makeServer(W) {
  const S = {
    dbs: new Map(), log: [], opens: [], rules: [], refuseBlobs: false, quota: null, latency: 0, _n: 0,
    features: { getAll: true, getAllKeys: true, commit: true, openKeyCursor: true },
  };
  S.fail = (rule) => {
    const r = Object.assign({ seen: 0, hits: 0 }, rule);
    if (r.times === undefined) r.times = r.nth ? 1 : Infinity;
    r._waiting = [];
    r.off = () => { const i = S.rules.indexOf(r); if (i >= 0) S.rules.splice(i, 1); return r; };
    r.release = () => { r.off(); const w = r._waiting.splice(0); w.forEach((go) => W._post(go, 0)); return r; };
    S.rules.push(r);
    return r;
  };
  S.clearFaults = () => { S.rules.splice(0).forEach((r) => r.release()); };
  S._fault = (info) => {
    for (const r of S.rules) {
      if (!ruleMatches(r, info)) continue;
      r.seen++;
      if ((r.nth && r.seen !== r.nth) || r.hits >= r.times) continue;
      r.hits++;
      return r;
    }
    return null;
  };
  S._logWrite = (info) => {
    const e = { op: info.op, db: info.db, store: info.store, key: info.key, value: info.value, blob: !!info.blob, client: info.client,
      ok: null, error: null, committed: null };
    S.log.push(e);
    return e;
  };
  S.bytes = () => { let n = 0; for (const D of S.dbs.values()) for (const s of D.stores.values()) n += s.bytes(); return n; };
  // transactions start in order; two whose scopes overlap wait for each other unless both only read
  S._schedule = (D) => {
    D.txs.forEach((t, i) => {
      if (t._started) return;
      const wait = D.txs.slice(0, i).some((e) => e._scope.some((n) => t._scope.includes(n)) && (e.mode !== "readonly" || t.mode !== "readonly"));
      if (!wait) { t._started = true; t._pump(); }
    });
  };
  S._retryOpens = (D) => {
    if ([...D.conns].some((c) => !c._closed) || !D.waiting.length) return;
    D.waiting.splice(0).forEach((go) => W._post(go, 0));
  };
  const failOpen = (req, err) => {
    req.readyState = "done"; req._result = undefined; req._error = err;
    dispatch(W, [req], makeEvent("error", { bubbles: true, cancelable: true }));
  };
  const succeed = (req, conn) => {
    if (conn._client.closed) { conn.close(); return; }
    req.readyState = "done"; req._result = conn; req._error = null;
    dispatch(W, [req], makeEvent("success"));
  };
  S._open = (req, name, version, client) => {
    if (client.closed) return;
    const D0 = S.dbs.get(name);
    const f = S._fault({ op: "open", db: name, version, client: client.label });
    if (f && f.hang) return;
    if (f && f.blocked) {
      dispatch(W, [req], makeEvent("blocked", { oldVersion: D0 ? D0.version : 0, newVersion: version === undefined ? null : version }));
      f._waiting.push(() => S._open2(req, name, version, client));
      return;
    }
    if (f) { failOpen(req, named(f.name || "UnknownError", f.message)); return; }
    S._open2(req, name, version, client);
  };
  S._open2 = (req, name, version, client) => {
    if (client.closed) return;
    let D = S.dbs.get(name);
    if (!D) { D = new DbData(name); S.dbs.set(name, D); }
    const v = version === undefined ? (D.version || 1) : version;
    if (v < D.version) { failOpen(req, named("VersionError", `The requested version (${v}) is less than the existing version (${D.version}).`)); return; }
    if (v === D.version) { const c = new FakeDB(W, D, v, client); D.conns.add(c); succeed(req, c); return; }
    // an upgrade: the other connections are asked to close first ("versionchange"); "blocked" while one stays open
    for (const c of [...D.conns]) if (!c._closed) dispatch(W, [c], makeEvent("versionchange", { oldVersion: D.version, newVersion: v }));
    W._post(() => {
      const go = () => S._upgrade(req, D, v, client);
      if ([...D.conns].some((c) => !c._closed)) {
        dispatch(W, [req], makeEvent("blocked", { oldVersion: D.version, newVersion: v }));
        D.waiting.push(go);
      } else go();
    }, 0);
  };
  S._upgrade = (req, D, v, client) => {
    if (client.closed) return;
    const old = D.version, before = new Map([...D.stores].map(([n, s]) => [n, s.copy()]));
    D.version = v;
    const conn = new FakeDB(W, D, v, client);
    D.conns.add(conn);
    const tx = new FakeTx(W, conn, [...D.stores.keys()], "versionchange");
    conn._upgrade = tx;
    req.readyState = "done"; req._result = conn; req.transaction = tx;
    tx._onDone = (ok) => {
      conn._upgrade = null; req.transaction = null;
      if (ok) { succeed(req, conn); return; }
      D.version = old; D.stores = before;
      conn._closed = true; D.conns.delete(conn);
      failOpen(req, named("AbortError", "The version change transaction was aborted."));
      S._retryOpens(D);
    };
    const ev = dispatch(W, [req], makeEvent("upgradeneeded", { oldVersion: old, newVersion: v }));
    if (ev._threw && tx._state !== "finished") tx._abort(named("AbortError", "An exception was thrown in onupgradeneeded."));
  };
  // the browser drops connections (WebKit: the networking process ended): their transactions abort, then "close"
  S.loseConnections = (o) => {
    o = o || {};
    for (const D of S.dbs.values()) {
      if (o.db && o.db !== D.name) continue;
      for (const c of [...D.conns]) {
        if (o.client && c._client.label !== o.client) continue;
        c._closed = true; D.conns.delete(c);
        D.txs.filter((t) => t.db === c).forEach((t) => t._abort(named(o.name || "UnknownError", o.message || "Connection to Indexed Database server lost. Refresh the page to try again")));
        if (!o.silent) W._post(() => dispatch(W, [c], makeEvent("close")), 0);
      }
      S._retryOpens(D);
    }
  };
  // the browser's storage process ends where it holds the databases in memory (WebKit's private window: its networking
  // process, which iOS ends in the background): the connections are lost (as loseConnections) and every database is
  // gone — the next open makes a new one (upgradeneeded with oldVersion 0)
  S.loseAll = (o) => { S.loseConnections(o); S.dbs.clear(); };
  // a page that goes: its connections close and what it was writing is aborted (no event reaches it any more)
  S._dropClient = (client) => {
    for (const D of S.dbs.values()) {
      for (const c of [...D.conns]) {
        if (c._client !== client) continue;
        c._closed = true; D.conns.delete(c);
        D.txs.filter((t) => t.db === c).forEach((t) => t._abort(named("AbortError", "The page was closed."), true));
      }
      S._retryOpens(D);
    }
  };
  S.create = (name, version, stores) => {
    const D = new DbData(name);
    D.version = version;
    for (const [n, o] of Object.entries(stores || {})) D.stores.set(n, new StoreData(n, (o || {}).keyPath, (o || {}).autoIncrement));
    S.dbs.set(name, D);
    return S.database(name);
  };
  S.database = (name) => {
    const D = S.dbs.get(name);
    if (!D) return null;
    return {
      name, get version() { return D.version; }, storeNames: () => [...D.stores.keys()].sort(),
      store: (n) => {
        const s = D.stores.get(n);
        if (!s) return null;
        return {
          keyPath: s.keyPath, get size() { return s.recs.length; },
          keys: () => s.recs.map((r) => r.key), all: () => s.recs.map((r) => r.value),
          get: (k) => { const r = s.get(k); return r ? r.value : undefined; },
          put: (v, k) => { const c = structuredClone(v); s.set(k !== undefined ? k : keyAt(c, s.keyPath), c); },
          set: (k, v) => s.set(k, v),                       // as it is, not cloned: a row no clone could make
          delete: (k) => s.del(toRange(k, true)), clear: () => { s.recs = []; },
        };
      },
    };
  };
  return S;
}

/* ---------------------------------------------------------------- Web Locks */
function makeLocks(W) {
  const L = { held: [], queue: [] };
  const conflicts = (a, b) => a.name === b.name && (a.mode === "exclusive" || b.mode === "exclusive");
  const release = (h) => { const i = L.held.indexOf(h); if (i >= 0) { L.held.splice(i, 1); grant(); } };
  const settle = (r, call, after) => {
    let p;
    try { p = Promise.resolve(call()); } catch (e) { p = Promise.reject(e); }
    p.then((v) => { if (after) after(); r.resolve(v); }, (e) => { if (after) after(); r.reject(e); });
  };
  function grant() {
    for (const r of L.queue.slice()) {
      const i = L.queue.indexOf(r);
      if (i < 0 || L.held.some((h) => conflicts(h, r)) || L.queue.slice(0, i).some((q) => q.name === r.name)) continue;
      L.queue.splice(i, 1);
      const h = { name: r.name, mode: r.mode, client: r.client };
      L.held.push(h);
      W._post(() => {
        if (r.client && r.client.closed) { release(h); return; }
        settle(r, () => r.cb({ name: r.name, mode: r.mode }), () => release(h));
      }, 0);
    }
  }
  L.request = (client, name, opts, cb) => {
    if (typeof opts === "function") { cb = opts; opts = {}; }
    opts = opts || {};
    if (typeof cb !== "function") return Promise.reject(new TypeError("navigator.locks.request: no callback"));
    name = String(name);
    if (name.startsWith("-")) return Promise.reject(named("NotSupportedError", "Lock names starting with '-' are reserved."));
    const mode = opts.mode === "shared" ? "shared" : "exclusive";
    return new Promise((resolve, reject) => {
      const r = { name, mode, client, cb, resolve, reject };
      if (opts.ifAvailable && (L.held.some((h) => conflicts(h, r)) || L.queue.some((q) => q.name === name))) {
        W._post(() => settle(r, () => cb(null)), 0);          // not free: the callback gets null
        return;
      }
      L.queue.push(r);
      grant();
    });
  };
  L.query = () => Promise.resolve({
    held: L.held.map((h) => ({ name: h.name, mode: h.mode, clientId: h.client ? h.client.id : "another-tab" })),
    pending: L.queue.map((q) => ({ name: q.name, mode: q.mode, clientId: q.client ? q.client.id : "another-tab" })),
  });
  L._dropClient = (client) => {
    L.queue = L.queue.filter((q) => q.client !== client);
    L.held.filter((h) => h.client === client).forEach(release);
  };
  // another tab holds `name` (until the function this returns is called)
  L.hold = (name, mode) => { const h = { name: String(name), mode: mode === "shared" ? "shared" : "exclusive", client: null }; L.held.push(h); return () => release(h); };
  L.names = () => L.held.map((h) => h.name);
  return L;
}

/* ---------------------------------------------------------------- the world */
export function createWorld(opts) {
  opts = opts || {};
  const W = { start: opts.now === undefined ? START : opts.now, errors: [], clients: [], _cleanup: [], _timers: [], _seq: 0 };
  W.now = W.start;
  W.perf = () => W.now - W.start;
  W._post = (fn, delay, owner, every) => {
    const id = ++W._seq;
    W._timers.push({ id, fn, at: W.now + Math.max(0, Number(delay) || 0), every: every || 0, owner: owner || null });
    return id;
  };
  W._clear = (id) => { const i = W._timers.findIndex((t) => t.id === id); if (i >= 0) W._timers.splice(i, 1); };
  const macrotask = () => new Promise((r) => setImmediate(r));
  // every promise settles (and the end of the task: transactions that may take no more requests go inactive)
  W.flush = async () => {
    for (let round = 0; round < 100; round++) {
      await macrotask(); await macrotask();
      const c = W._cleanup.splice(0);
      if (!c.length) return;
      for (const f of c) { try { f(); } catch (e) { W.errors.push(e); } }
    }
  };
  async function step(end) {
    let t = null;
    for (const x of W._timers) if (x.at <= end && (!t || x.at < t.at || (x.at === t.at && x.id < t.id))) t = x;
    if (!t) return false;
    W.now = Math.max(W.now, t.at);
    if (t.every) t.at = W.now + t.every; else W._timers.splice(W._timers.indexOf(t), 1);
    try { t.fn(); } catch (e) { W.errors.push(e); }
    await W.flush();
    return true;
  }
  W.tick = async (ms) => { const end = W.now + (Number(ms) || 0); await W.flush(); while (await step(end)); W.now = Math.max(W.now, end); await W.flush(); };
  W.until = async (cond, within) => {
    const end = W.now + (within === undefined ? 60000 : within);
    await W.flush();
    while (!cond()) { if (!(await step(end))) { W.now = Math.max(W.now, end); return !!cond(); } }
    return true;
  };
  W.wait = async (p, within) => {
    let done = false, ok = false, v;
    Promise.resolve(p).then((x) => { done = true; ok = true; v = x; }, (e) => { done = true; v = e; });
    if (!(await W.until(() => done, within))) throw new Error(`still waiting after ${within === undefined ? 60000 : within} ms`);
    if (!ok) throw v;
    return v;
  };
  // until no timeout is waiting (intervals go on)
  W.idle = (within) => W.until(() => !W._timers.some((t) => !t.every), within);
  const RealDate = Date;
  W.Date = class extends RealDate {
    constructor(...a) { if (a.length) super(...a); else super(W.now); }
    static now() { return W.now; }
  };
  W.performance = { now: () => W.perf(), timeOrigin: W.start };
  W.idb = makeServer(W);
  W.locks = makeLocks(W);
  const ST = W.storage = { quota: 2 * 1024 ** 3, extra: 0, persisted: false, grant: false, private: false,
    calls: { estimate: 0, persist: 0, persisted: 0, getDirectory: 0 } };
  const later = (v, fail) => new Promise((res, rej) => W._post(() => (fail ? rej(v) : res(v)), 0));
  // a page load: what its window and navigator get
  W.client = (label) => {
    const c = { label: label || "page " + (W.clients.length + 1), id: "client-" + (W.clients.length + 1), closed: false, dialogs: [] };
    c.answer = () => ({ answer: false, after: 100 });
    W.clients.push(c);
    const own = (fn, ms, every, args) => W._post(() => fn(...args), ms, c, every);
    c.setTimeout = (fn, ms, ...a) => (typeof fn === "function" ? own(fn, ms, 0, a) : 0);
    c.setInterval = (fn, ms, ...a) => { const every = Math.max(1, Number(ms) || 0); return typeof fn === "function" ? own(fn, every, every, a) : 0; };
    c.clearTimeout = c.clearInterval = (id) => W._clear(id);
    c.confirm = (message) => {
      c.dialogs.push(String(message));
      const a = c.answer(String(message)) || {};
      W.now += Math.max(0, Number(a.after) || 0);           // the dialog is up: time passes, nothing else runs
      return !!a.answer;
    };
    c.indexedDB = new FakeFactory(W, c);
    c.IDBKeyRange = FakeKeyRange;
    c.locks = { request: (n, o, cb) => W.locks.request(c, n, o, cb), query: () => W.locks.query() };
    c.storage = {
      estimate: () => { ST.calls.estimate++; return later({ quota: ST.quota, usage: W.idb.bytes() + ST.extra }); },
      persist: () => { ST.calls.persist++; if (ST.grant) ST.persisted = true; return later(ST.persisted); },
      persisted: () => { ST.calls.persisted++; return later(ST.persisted); },
      getDirectory: () => {
        ST.calls.getDirectory++;
        return ST.private ? later(named("UnknownError", "The operation failed for an unknown transient reason (e.g. out of memory)."), true)
          : later({ kind: "directory", name: "" });
      },
    };
    c.globals = { setTimeout: c.setTimeout, clearTimeout: c.clearTimeout, setInterval: c.setInterval, clearInterval: c.clearInterval,
      Date: W.Date, performance: W.performance, indexedDB: c.indexedDB, IDBKeyRange: FakeKeyRange, confirm: c.confirm };
    c.close = () => {
      if (c.closed) return;
      c.closed = true;
      W._timers = W._timers.filter((t) => t.owner !== c);
      W.locks._dropClient(c);
      W.idb._dropClient(c);
    };
    return c;
  };
  return W;
}
