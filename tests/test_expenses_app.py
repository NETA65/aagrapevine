"""The service expense tracker's screen logic (src/assets/js/expenses.js, the Alpine app "xpApp") run in
Node.js — the rules that live in the app itself, not in the core (tests/test_expenses_core.py):

  * the add / edit form — an empty amount is refused (0 is fine, a minus sign is not); a request
    status the form does not show survives an edit of a purchase made for someone; "Record the
    renewal" starts the new term where the old one ends (and the reminder goes — for a gift with no
    name too, recorded on time or late); a duplicate is a
    new trip (no odometer); money received from a person settles what was bought for them; miles,
    odometer readings and quantities typed with a thousands separator ("42,150") are read as the
    money field reads them; a round trip's one-way miles come back exact (an edit never moves the
    total); a purchase made for someone and left on "me" (the example) saves again as it is
  * storage — a save the browser refuses never says "Saved"; the screen's own choices (the view,
    the period) are kept apart, so another tab does not reload for them; an entry deleted in another
    tab while it is being edited here is saved again as itself, its receipt photo with it, and the
    dialog says so; a "replace" import whose save is refused keeps the receipt photos of the ledger
    that stays
  * requests — "Download CSV" is the request's own lines, without people's names unless the request
    includes them; the files are named in the page's language
  * import — a full backup bigger than a CSV may be is still restored; a mileage log with no amount
    column can be mapped; a problem names the visitor's own column; a card statement's charges are
    spending, and the preview can flip what a positive amount means; a statement's dates are read
    in the order they show (a US statement on the Spanish page); a backup merged in brings back the
    photos this device lacks
  * trips, roles, activities — several trips on one entry (one way × 2 × trips; an edit shows them back
    and moves nothing; the odometer is the whole trip); "I didn't drive" keeps the event and the role
    with no miles, no money and no request (and the dialog is named for a trip, not "Miles driven"); a
    trip that was driven keeps the name it came with through an edit; a hotel's confirmation and a
    store's order number; several subscriptions at once count as that many; the activity filter; a
    request says a line's trips once
  * subscriptions — the list's statuses (ending, ended, active, renewed), its filters and counts (as
    many as were bought: 10 at once count 10), whom each is for (your own, the group's), the calendar
    file (one event per subscription to renew, CRLF, named in the page's language; a renewal moves
    its event)
  * giveaways — the literature follows the period: on hand at its start, in and out, on hand at its end;
    an empty period says so ("in this period", not "yet")
  * the service report — the summary rows and totals, the lines (names only when asked; one-way miles
    exact; a date's words kept together), "Prepared for" and the note kept with the settings, its CSV
    named in the page's language
  * service activities in Settings — add, rename, merge a used one (a built-in is hidden, never deleted)
  * the tab bar — on a phone the open tab is scrolled into sight (a reopened view, a link, a tap)
  * backups (1.2.0) — the full backup is a .zip (backup.json + each photo a file) another device restores, photos
    and all; its size is said first and a big one is asked about; "without photos" (.json) keeps this device's
    photos; an unpacked .zip restores from its backup.json picked with its photos; a pre-1.2.0 .json of 88 MB
    restores in slices; UTF-16 CSVs and Excel workbooks import; what a browser can't read says why; a photo the
    browser can't read is left out of the backup and named (never the whole backup); one that fails all the same
    points to "Back up without photos"; photos that fail to restore are said (read out)
  * an edit keeps the fields its form doesn't show (an imported trip's nights, quantity, item, attendees);
    "Who owes you" is the balance at the period's end; the service panels come from Area 65's rule; the
    Requests view and the report make their formatters once (not per cell)
  * stored data — an unreadable ledger is set aside (or, with no room, never saved over) and offered as a file,
    with the receipt photos it names (restored with them once repaired); a newer page's ledger is not saved
    over; closing the tab asks only while something is unsaved (the form, or changes the browser did not
    keep); a photo survives a delete another tab can still undo, or whose entry another tab brought back or
    saved again from its open form
  * the rest — the examples are added once; a CSV export is not a backup; the Summary's badge counts
    what its Reminders card lists, and "By category" counts subscriptions as subscriptions; "Sort:
    Category" follows the names on screen; two items that
    differ by an accent are two rows; "Last backup" counts calendar days

The app is loaded as the page loads it (expenses-core.js, expenses-files.js, then expenses.js) into a vm context with a
small stand-in for the browser: localStorage (that can be made to refuse), no IndexedDB (the photos'
calls fail softly, as in a private window) unless a test hands it the photos to keep, a document
that records downloads, and an Alpine that hands back the component. The words and defaults come
from src/_data/expenses.js, as on the page.

    python -m unittest tests.test_expenses_app -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

# The browser stand-in and the app: `make(lang, seed, moreEls, o)` → a fresh component (its own storage,
# seeded from `seed`; `moreEls` are extra elements getElementById finds; o.photos: a Map that stands in
# for IndexedDB's receipt photos, by entry id — two components handed the same Map share them, as two
# visits do; o.now: a fixed clock, in ms), `tick()` lets promises settle, `downloads` are the files the
# app saved ({name, text}).
LOAD = r"""
import vm from "node:vm";
const data = (await imp("src/_data/expenses.js")).default();
// IndexedDB with the one store the app opens, over a Map; a request settles a microtask later
const fakeIDB = (recs) => ({
  open() {
    const req = {};
    queueMicrotask(() => {
      const run = (fn) => ({ result: fn() });
      req.result = {
        objectStoreNames: { contains: () => true },
        createObjectStore() {},
        transaction() {
          const tx = {};
          tx.objectStore = () => ({
            get: (id) => run(() => recs.get(id)), put: (rec) => run(() => { recs.set(rec.id, rec); return rec.id; }),
            delete: (id) => run(() => { recs.delete(id); }), getAll: () => run(() => [...recs.values()]),
            getAllKeys: () => run(() => [...recs.keys()]), clear: () => run(() => { recs.clear(); }),
          });
          queueMicrotask(() => tx.oncomplete && tx.oncomplete());
          return tx;
        },
      };
      if (req.onsuccess) req.onsuccess();
    });
    return req;
  },
});
const make = (lang, seed, moreEls, o) => {
  o = o || {};
  // (o.store: a Map two components share — two tabs of one browser; o.full: storage full from the start)
  const store = o.store || new Map(Object.entries(seed || {}));
  let full = !!o.full;
  const listeners = {}, docListeners = {}, blobs = new Map(), downloads = [];
  let n = 0;
  const els = {
    "xp-config": { textContent: JSON.stringify(data.config) },
    "xp-ui": { textContent: JSON.stringify(data.ui[lang]) },
    "xp-events": { textContent: "[]" },
    ...(moreEls || {}),
  };
  const now = o.now;
  const clock = now == null ? Date : class extends Date { constructor(...a) { if (a.length) super(...a); else super(now); } static now() { return now; } };
  const ctx = {
    console, TextDecoder, TextEncoder, Blob, Promise, JSON, Math, Date: clock, Intl: o.intl || Intl, Object, Array, String, Number, isFinite, isNaN,
    Uint8Array, atob, DecompressionStream: o.noInflate ? undefined : DecompressionStream,
    // (a toast's 10 seconds never keep Node waiting; a breath between two restored photos — 0 ms — is waited for)
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); if (ms > 0) t.unref?.(); return t; },
    clearTimeout, requestAnimationFrame: (fn) => setTimeout(fn, 0),
    getComputedStyle: (el) => (el && el.style) || {},      // an element's "computed" style is its own style
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => { if (full) { const e = new Error("full"); e.name = "QuotaExceededError"; throw e; } store.set(k, String(v)); },
      removeItem: (k) => { store.delete(k); },
      get length() { return store.size; },
      key: (i) => [...store.keys()][i] ?? null,
    },
    indexedDB: o.photos ? fakeIDB(o.photos) : undefined,
    URL: { createObjectURL: (b) => { const u = "blob:" + (++n); blobs.set(u, b); return u; }, revokeObjectURL() {} },
    location: { hash: "" }, history: { pushState() {} },
    navigator: { storage: { persist: () => Promise.resolve(false), persisted: () => Promise.resolve(false), estimate: () => Promise.resolve({ usage: 0 }) } },
    matchMedia: () => ({ matches: true, addEventListener() {} }),
    addEventListener: (type, fn) => { (listeners[type] ||= []).push(fn); },
    removeEventListener: (type, fn) => { listeners[type] = (listeners[type] || []).filter((f) => f !== fn); },
    confirm: () => true,
    GV: {},
    document: {
      addEventListener: (type, fn) => { (docListeners[type] ||= []).push(fn); },
      getElementById: (id) => els[id] || null,
      querySelector: () => null, querySelectorAll: () => [],
      createElement: () => ({ style: {}, setAttribute() {}, remove() {}, click() { downloads.push({ name: this.download, url: this.href }); } }),
      body: { appendChild() {} },
      documentElement: { getAttribute: () => null, setAttribute() {}, removeAttribute() {} },
      contains: () => false, activeElement: null,
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const f of ["src/assets/js/expenses-core.js", "src/assets/js/expenses-files.js", "src/assets/js/expenses.js"]) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
  let factory = null;
  ctx.Alpine = { directive() {}, data: (name, fn) => { if (name === "xpApp") factory = fn; } };
  for (const fn of docListeners["alpine:init"] || []) fn();
  const a = factory(lang);
  a.$nextTick = (fn) => fn && fn();
  a.$refs = {};
  a.$watch = () => {};
  a.init();
  return {
    a, ctx, store, downloads, listeners, G: ctx.GVX, F: ctx.GVF,
    setFull: (v) => { full = v; },
    text: async (d) => await blobs.get(d.url).text(),
    blob: (d) => blobs.get(d.url),
  };
};
const tick = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };
// a file the visitor picks: a Blob with a name (it can be sliced, as a browser's File can)
const fileOf = (name, data, type) => Object.assign(new Blob(Array.isArray(data) ? data : [data], { type: type || "" }), { name });
const KEY = "gv-expenses:v1";
const state = (w) => JSON.parse(w.store.get(KEY));
// the form for an entry of `type` (category optional), filled with `fields`, saved → the app's messages
const add = (w, type, fields, cat) => {
  w.a.openAdd(type, cat);
  Object.assign(w.a.form, fields);
  w.a.saveForm(false);
  return { errs: w.a.formErrs.map((e) => [e.field, e.text]), toast: w.a.toastMsg };
};
"""


def app(case: unittest.TestCase, js: str, **kw):
    return run_js(case, LOAD + js, timeout=120, **kw)


class Form(unittest.TestCase):
    def test_the_amount_is_required(self):
        r = app(self, r"""
          const w = make("en"), t = (k) => w.a.t(k);
          const blank = add(w, "expense", { description: "Stamps", amount: "" }, "other");
          const received = add(w, "received", { description: "Check", amount: " " });
          const minus = add(w, "expense", { description: "Stamps", amount: "-5" }, "other");
          const n0 = w.a.E().length;
          const zero = add(w, "expense", { description: "Free coffee", amount: "0" }, "other");
          const es = make("es");
          const esBlank = add(es, "expense", { description: "Sellos", amount: "" }, "other");
          out({ blank: blank.errs, received: received.errs, minus: minus.errs, n0, zero: zero.errs, n1: w.a.E().length,
                saved0: w.a.E().map((e) => e.amount_cents), required: t("form.err_amount_required"), negative: t("form.err_amount_negative"),
                es: esBlank.errs });""")
        self.assertEqual(r["blank"], [["amount", r["required"]]])
        self.assertEqual(r["received"], [["amount", r["required"]]])
        self.assertEqual(r["minus"], [["amount", r["negative"]]])
        self.assertEqual((r["n0"], r["zero"], r["n1"], r["saved0"]), (0, [], 1, [0]))    # a typed 0 is an amount
        self.assertEqual(r["es"], [["amount", "Escribe el monto (0 también vale)"]])

    def test_a_helped_purchase_keeps_its_request_status(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { sub_kind: "helped", person_name: "Pat K.", description: "La Viña online", amount: "15" }, "subscriptions");
          const id = w.a.E()[0].id;
          const pick = () => { const e = w.a.E().find((x) => x.id === id); return [e.claim_status, e.repaid, e.claim_date, e.claim_ref]; };
          const first = pick();
          // the request is sent (Requests → "Mark as submitted"), then the entry is edited: a note only
          w.a.patch([id], (e) => { e.claim_status = "submitted"; e.claim_date = "2026-09-27"; e.claim_ref = "2026-09"; });
          w.a.openEdit(id); w.a.form.notes = "called her"; w.a.saveForm(false);
          const afterNote = pick();
          // …the pay-back chosen in the form still decides
          w.a.openEdit(id); w.a.form.repaid = "forgiven"; w.a.saveForm(false);
          const forgiven = pick();
          w.a.openEdit(id); w.a.form.repaid = "owed"; w.a.saveForm(false);
          const owedAgain = pick();
          // marked paid in bulk: paid back (the two never disagree)
          w.a.sel = { [id]: true }; w.a.bulkStatus("paid");
          const bulkPaid = pick();
          w.a.openEdit(id); w.a.form.notes = "thanks"; w.a.saveForm(false);
          out({ first, afterNote, forgiven: forgiven.slice(0, 2), owedAgain: owedAgain.slice(0, 2), bulkPaid: bulkPaid.slice(0, 2), after: pick().slice(0, 2),
                owed: w.G.summary(w.a.E(), w.a.st(), {}).owed_cents });""")
        self.assertEqual(r["first"][:2], ["to_request", "owed"])
        self.assertEqual(r["afterNote"], ["submitted", "owed", "2026-09-27", "2026-09"])
        self.assertEqual(r["forgiven"], ["none", "forgiven"])
        self.assertEqual(r["owedAgain"], ["to_request", "owed"])
        self.assertEqual(r["bulkPaid"], ["paid", "repaid"])
        self.assertEqual(r["after"], ["paid", "repaid"])
        self.assertEqual(r["owed"], 0)

    def test_money_received_from_a_person_settles_what_was_bought_for_them(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { sub_kind: "helped", person_name: "Luis M.", description: "La Viña online", amount: "15", date: "2026-08-01" }, "subscriptions");
          add(w, "expense", { sub_kind: "helped", person_name: "Luis M.", description: "Grapevine print", amount: "36", date: "2026-08-10" }, "subscriptions");
          const luis = w.a.E()[0].funder;
          const owed0 = w.G.summary(w.a.E(), w.a.st(), {}).owed_cents;
          // $20 back: covers the first ($15), not the second ($36)
          const r1 = add(w, "received", { description: "Luis paid me back", amount: "20", funder: luis, date: "2026-09-01" }, "repayment");
          const st1 = w.a.E().filter((e) => e.type === "expense").map((e) => [e.description, e.claim_status, e.repaid, e.paid_date]);
          w.a.rq.funder = luis; w.a.rq.period = "all";
          const lines = [w.a.rqLines().length, w.a.rqTotals().total];
          // the rest: the second one too
          add(w, "received", { description: "The rest", amount: "31", funder: luis, date: "2026-09-10" }, "repayment");
          const st2 = w.a.E().filter((e) => e.type === "expense").map((e) => [e.claim_status, e.repaid]);
          out({ owed0, toast: r1.toast, st1, lines, st2, owed: w.G.summary(w.a.E(), w.a.st(), {}).owed_cents });""")
        self.assertEqual(r["owed0"], 5100)
        self.assertEqual(r["st1"], [["La Viña online", "paid", "repaid", "2026-09-01"], ["Grapevine print", "to_request", "owed", ""]])
        self.assertIn("1 purchase for them marked paid back", r["toast"])
        self.assertEqual(r["lines"], [1, "$36.00"])                         # the settled one left the request
        self.assertEqual(r["st2"], [["paid", "repaid"], ["paid", "repaid"]])
        self.assertEqual(r["owed"], 0)

    def test_record_the_renewal_and_duplicate(self):
        r = app(self, r"""
          const w = make("en"), today = w.G.todayISO();
          // a gift subscription that ends in 20 days (started 11 months and 10 days ago)
          const start = w.G.addDays(w.G.addMonths(today, -12), 20);
          add(w, "expense", { sub_kind: "gift", person: "Maria G.", sub_product: "gv_print", sub_term: "12", sub_start: start, description: "Gift", amount: "36", date: start }, "subscriptions");
          const id = w.a.E()[0].id, end = w.G.subEnd(w.a.E()[0]);
          const due0 = w.a.renewalRows().length;
          w.a.renew(id);
          const form = [w.a.form.date, w.a.form.sub_start, w.a.formMode];
          w.a.saveForm(false);
          const renewed = w.a.E().find((e) => e.id !== id);
          // a plain duplicate: the start follows the new date; a trip's odometer readings are left out
          w.a.duplicate(id);
          const dupStart = w.a.form.sub_start;
          w.a.closeForm(); w.a.form = null;
          add(w, "mileage", { from: "Home", to: "Tyler", odometer_start: "100", odometer_end: "150" });
          const trip = w.a.E().find((e) => e.type === "mileage");
          w.a.duplicate(trip.id);
          out({ today, end, due0, form, renewedStart: renewed.sub_start, due1: w.a.renewalRows().length, dupStart,
                odo: [w.a.form.odometer_start, w.a.form.odometer_end, w.a.form.miles] });""")
        self.assertEqual(r["due0"], 1)
        self.assertEqual(r["form"], [r["today"], r["end"], "add"])           # dated today, starting where the last ends
        self.assertEqual(r["renewedStart"], r["end"])
        self.assertEqual(r["due1"], 0)                                        # the reminder is gone
        self.assertEqual(r["dupStart"], "")                                   # a plain copy: the start is the new date
        self.assertEqual(r["odo"], ["", "", "50"])

    def test_record_the_renewal_of_a_gift_with_no_name(self):
        # a gift typed without a name (anonymity) is renewed by "Record the renewal" too: on time (the new term
        # starts the day the old one ends) and late (it ended two months ago: the new term starts today)
        r = app(self, r"""
          const w = make("en"), today = w.G.todayISO();
          const gift = (start, desc) => add(w, "expense", { sub_kind: "gift", person: "", sub_product: "gv_print", sub_term: "12", sub_start: start,
                                                             date: start, description: desc, amount: "36" }, "subscriptions");
          gift(w.G.addDays(w.G.addMonths(today, -12), 20), "Ends in 20 days");
          gift(w.G.addMonths(today, -14), "Ended 2 months ago");
          const [soon, late] = w.a.E();
          const before = [w.a.renewalRows().map((x) => x.id), w.a.subStatusCount("ending"), w.a.subStatusCount("ended")];
          const starts = [];
          for (const e of [soon, late]) { w.a.renew(e.id); starts.push(w.a.form.sub_start); w.a.saveForm(false); }
          const st = (id) => w.a.subsAll().find((s) => s.id === id);
          out({ before, soon: soon.id, starts, end: w.G.subEnd(soon), n: w.a.E().length,
                after: [st(soon.id).status, st(late.id).status, w.a.renewalRows().length, w.a.subStatusCount("ending"), w.a.subStatusCount("ended")] });""")
        self.assertEqual(r["before"], [[r["soon"]], 1, 1])
        self.assertEqual(r["starts"], [r["end"], ""])                         # (blank: the late one starts on its date, today)
        self.assertEqual(r["n"], 4)
        self.assertEqual(r["after"], ["renewed", "renewed", 0, 0, 0])          # no reminder, nothing "ended"

    def test_numbers_typed_with_a_thousands_separator(self):
        # "42,150" on an odometer is 42150 (as the money field reads "1,000"), never 42.15; "12,5" is still 12.5
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang);
            w.a.openAdd("mileage");
            Object.assign(w.a.form, { from: "Home", to: "Tyler", odometer_start: "42,150", odometer_end: "42,238" });
            const preview = w.a.mileagePreview();
            w.a.saveForm(false);
            const trip = w.a.E().at(-1);
            add(w, "giveaway", { item: "Grapevine", quantity: "1,000", event: "Fall Assembly" });
            const given = w.a.E().at(-1).quantity;
            w.a.openAdd("expense", "books");
            Object.assign(w.a.form, { description: "Big Books", quantity: "1,000", unit_cost: "0.25" });
            const total = w.a.booksTotal();
            w.a.saveForm(false);
            const books = w.a.E().at(-1);
            add(w, "mileage", { from: "Home", to: "Dallas", miles: "1,204" });
            add(w, "mileage", { from: "Home", to: "Sherman", miles: "12,5" });
            res[lang] = { preview, odo: [trip.odometer_start, trip.odometer_end, trip.miles, trip.amount_cents], given, total,
                          books: [books.quantity, books.amount_cents], miles: w.a.E().slice(-2).map((e) => e.miles),
                          want: [w.a.t("form.mileage_preview", { miles: w.a.count(88), rate: "0.14", amount: w.a.money(1232) }),
                                 w.a.t("form.books_total", { qty: w.a.count(1000), unit: w.a.money(25), total: w.a.money(25000) })] };
          }
          out(res);""")
        for lang, x in r.items():
            with self.subTest(lang=lang):
                self.assertEqual(x["odo"], [42150, 42238, 88, 1232])                   # 88 mi × $0.14 = $12.32
                self.assertEqual([x["preview"], x["total"]], x["want"])
                self.assertEqual(x["given"], 1000)
                self.assertEqual(x["books"], [1000, 25000])                           # 1,000 × $0.25 = $250.00
                self.assertEqual(x["miles"], [1204, 12.5])

    def test_a_purchase_for_someone_left_on_me_saves_as_it_is(self):
        # the example "bought for someone who pays me back" is on "me" with the person's name (the site
        # has no funder of kind person): the form shows the name, so saving it unchanged just works
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang);
            w.a.addExamples();
            const h = w.a.E().find((e) => e.sub_kind === "helped"), id = h.id;
            const before = [h.funder, h.person];
            w.a.openEdit(id);
            const name = w.a.form.person_name;
            w.a.saveForm(false);
            const x = w.a.E().find((e) => e.id === id), f = w.a.funder(x.funder) || {};
            const owed = w.G.peopleOwed(w.a.E(), w.a.st()).map((p) => [p.person, p.owed_cents]);
            w.a.sel = { [id]: true }; w.a.bulkStatus("paid");
            const paid = w.a.E().find((e) => e.id === id);
            // made a gift instead, for someone else: the name typed on screen is the one kept
            const g = make(lang);
            g.a.addExamples();
            const gid = g.a.E().find((e) => e.sub_kind === "helped").id;
            g.a.openEdit(gid);
            g.a.form.sub_kind = "gift"; g.a.onSubKind();
            g.a.form.person = "Ana P.";
            g.a.saveForm(false);
            const gift = g.a.E().find((e) => e.id === gid);
            res[lang] = { before, name, errs: w.a.formErrs.map((e) => e.field), funder: [f.kind, w.a.lbl(f.name), x.person], owed,
                          paid: [paid.claim_status, paid.repaid], owedAfter: w.G.peopleOwed(w.a.E(), w.a.st()).length,
                          gift: [gift.sub_kind, gift.person, gift.funder, g.a.formErrs.length] };
          }
          out(res);""")
        for lang, x in r.items():
            with self.subTest(lang=lang):
                self.assertEqual(x["before"], ["me", "José R."])
                self.assertEqual(x["name"], "José R.")
                self.assertEqual(x["errs"], [])                                     # "Who pays you back?" is answered
                self.assertEqual(x["funder"], ["person", "José R.", "José R."])     # as a new purchase for someone is kept
                self.assertEqual(x["owed"], [["José R.", 1500]])                    # still owed once, not twice
                self.assertEqual(x["paid"], ["paid", "repaid"])                     # and "Paid" in bulk reaches it
                self.assertEqual(x["owedAfter"], 0)
                self.assertEqual(x["gift"], ["gift", "Ana P.", "me", 0])

    def test_the_one_way_miles_of_a_round_trip(self):
        # a round trip keeps its total (1 decimal); the form shows half of it, exactly: an edit of the
        # description alone never moves the miles or the amount (25.3 mi is 12.65 one way, not 12.7)
        r = app(self, r"""
          const w = make("en");
          const file = (name, t) => ({ name, size: t.length, arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          add(w, "mileage", { from: "Home", to: "District 22 meeting", miles: "12.65", round_trip: true, date: "2026-09-01" });
          w.a.impFile(file("log.csv", "id,date,type,description,miles,rate,round_trip\nm1,2026-09-02,mileage,Trip one,25.3,0.14,yes\nm2,2026-09-03,mileage,Trip two,63.7,0.14,yes\n"));
          await tick();
          w.a.impApply();
          const before = w.a.E().map((e) => [e.miles, e.amount_cents]), shown = [];
          for (const e of w.a.E().slice()) {
            w.a.openEdit(e.id);
            shown.push(w.a.form.miles);
            w.a.form.description = e.description + " (edited)";
            w.a.saveForm(false);
          }
          out({ before, shown, after: w.a.E().map((e) => [e.miles, e.amount_cents, e.description.endsWith("(edited)")]) });""")
        self.assertEqual(r["before"], [[25.3, 354], [25.3, 354], [63.7, 892]])   # 25.3 × $0.14 = $3.542; 63.7 × $0.14 = $8.918
        self.assertEqual(r["shown"], ["12.65", "12.65", "31.85"])
        self.assertEqual(r["after"], [[25.3, 354, True], [25.3, 354, True], [63.7, 892, True]])


class Storage(unittest.TestCase):
    def test_a_refused_save_never_says_saved(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { description: "Books", amount: "12" }, "books");
          w.setFull(true);
          const r1 = add(w, "expense", { description: "Hotel", amount: "90" }, "lodging");
          const warn = [w.a.storageOk, r1.toast];
          w.a.sel = Object.fromEntries(w.a.E().map((e) => [e.id, true]));
          w.a.bulkStatus("submitted");
          const bulk = w.a.toastMsg;
          w.setFull(false);
          add(w, "expense", { description: "Stamps", amount: "3" }, "other");
          out({ warn, bulk, back: [w.a.storageOk, w.a.toastMsg], kept: state(w).entries.length, off: w.a.t("storage_off") });""")
        self.assertEqual(r["warn"], [False, r["off"]])
        self.assertEqual(r["bulk"], r["off"])
        self.assertEqual(r["back"], [True, "Saved"])                          # space again: the warning goes
        self.assertEqual(r["kept"], 3)

    def test_the_screens_choices_are_kept_apart(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { description: "Books", amount: "12" }, "books");
          const before = w.store.get(KEY);
          w.a.go("summary"); w.a.setPeriod("all");
          const ui = JSON.parse(w.store.get(KEY + ":ui"));
          // the next visit opens where this one was
          const w2 = make("en", Object.fromEntries(w.store));
          out({ same: w.store.get(KEY) === before, ui: [ui.view, ui.period], reopened: [w2.a.view, w2.a.f.period] });""")
        self.assertTrue(r["same"])                                            # another tab sees no change of data
        self.assertEqual(r["ui"], ["summary", "all"])
        self.assertEqual(r["reopened"], ["summary", "all"])

    def test_an_entry_deleted_in_another_tab_while_edited_here(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { description: "Books", amount: "12" }, "books");
          const id = w.a.E()[0].id;
          w.a.openEdit(id);
          // the other tab deletes it (the storage event of this tab)
          const s = state(w); s.entries = []; w.store.set(KEY, JSON.stringify(s));
          for (const fn of w.listeners.storage || []) fn({ key: KEY });
          const mode = [w.a.formMode, w.a.form.id, w.a.dlgMsg];
          w.a.saveForm(false);
          out({ mode, id, n: w.a.E().length, sameId: w.a.E()[0].id === id, msg: w.a.t("form.deleted_elsewhere") });""")
        self.assertEqual(r["mode"], ["add", r["id"], r["msg"]])
        self.assertEqual(r["n"], 1)
        self.assertTrue(r["sameId"])                      # saved again as itself (the other tab's "Undo" finds it there)

    def test_a_refused_replace_keeps_the_photos(self):
        # "Replace" with a CSV or a full backup while the browser refuses the new ledger (a full
        # localStorage): the old ledger stays stored, so its receipt photos stay too
        r = app(self, r"""
          const file = (name, t) => ({ name, size: t.length, arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          const setup = () => {
            const photos = new Map(), w = make("en", null, null, { photos });
            add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
            add(w, "expense", { description: "Books", amount: "12", receipt: "photo" }, "books");
            add(w, "expense", { description: "Stamps", amount: "3" }, "other");
            for (const e of w.a.E()) if (e.receipt === "photo") photos.set(e.id, { id: e.id, type: "image/jpeg", blob: new Blob(["jpeg"]) });
            return { w, photos, old: [...photos.keys()] };
          };
          const replace = {
            csv: async (w) => {
              w.a.impFile(file("bank.csv", "Date,Description,Amount\n09/02/2026,Office Depot,45.00\n")); await tick();
              w.a.imp.map.date = "0"; w.a.imp.map.description = "1"; w.a.imp.map.amount = "2"; w.a.impUseMap();
              w.a.imp.mode = "replace"; await w.a.impApply(); await tick();
            },
            backup: async (w) => {
              const e = w.G.normalizeEntry({ id: "b1", type: "expense", date: "2026-09-01", category: "other", description: "From the backup", amount_cents: 100, receipt: "photo" }, w.a.st()).entry;
              w.a.impFile(file("backup.json", w.G.toBackup({ entries: [e], settings: w.a.st(), meta: {} }, [{ id: "b1", type: "image/jpeg", dataUrl: "data:image/jpeg;base64,/9j/4AAQ" }])));
              await tick();
              w.a.imp.mode = "replace"; await w.a.impApply(); await tick();
            },
          };
          const res = {};
          for (const kind of ["csv", "backup"]) {
            const { w, photos, old } = setup();
            w.setFull(true);
            await replace[kind](w);
            const refused = [w.a.toastMsg === w.a.t("storage_off"), state(w).entries.map((e) => e.description), old.every((id) => photos.has(id))];
            // the next visit reads the old ledger: every photo it points to is there (start-up's clean-up runs)
            const w2 = make("en", Object.fromEntries(w.store), null, { photos });
            await w2.a.cleanPhotos();
            const reopened = [w2.a.E().filter((e) => e.receipt === "photo").map((e) => e.id).sort(), [...photos.keys()].sort()];
            // with room again, a replace takes the old ledger's photos with it
            await replace[kind](w2);
            res[kind] = { refused, reopened, replaced: [...photos.keys()] };
          }
          out(res);""")
        for kind, x in r.items():
            with self.subTest(kind=kind):
                self.assertEqual(x["refused"], [True, ["Hotel", "Books", "Stamps"], True])
                self.assertEqual(x["reopened"][0], x["reopened"][1])
                self.assertEqual(len(x["reopened"][0]), 2)
        self.assertEqual(r["csv"]["replaced"], [])
        self.assertEqual(r["backup"]["replaced"], ["b1"])                   # the backup's own photo


class Requests(unittest.TestCase):
    def test_the_request_csv_leaves_names_out(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { sub_kind: "group", person: "Rosa T.", sub_product: "gv_online", sub_term: "12", description: "Grapevine online for Rosa",
                              amount: "20", notes: "Rosa's birthday", funder: "group", claim_status: "to_request", date: "2026-08-15" }, "subscriptions");
          add(w, "mileage", { from: "Home", to: "District 22 meeting", miles: "10", round_trip: true, funder: "group", claim_status: "to_request", date: "2026-08-20" });
          w.a.rq.funder = "group"; w.a.rq.period = "all";
          w.a.rqCsv();
          const off = await w.text(w.downloads.at(-1));
          w.a.rq.names = true;
          w.a.rqCsv();
          const on = await w.text(w.downloads.at(-1));
          out({ off, on, name: w.downloads[0].name });""")
        off = r["off"].lstrip("﻿").split("\r\n")
        self.assertEqual(off[0], "Date,Description,Category,From,To,Miles,Mileage rate,Amount,Receipt")
        self.assertNotIn("Rosa", r["off"])                                    # no name, no notes, no ids
        self.assertIn("Magazine subscriptions · For the group", off[1])
        self.assertTrue(off[1].endswith(",20.00,"))
        self.assertRegex(off[2], r",Home,District 22 meeting,20,0\.14,2\.80,$")
        self.assertIn("Grapevine online for Rosa", r["on"])                    # the toggle includes them
        self.assertRegex(r["name"], r"^service-expenses-request-my-home-group-\d{4}-\d{2}-\d{2}\.csv$")

    def test_file_names_in_the_page_language(self):
        # the request's CSV and "Export selected" are named in the page's language, as the backup is
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang);
            add(w, "expense", { description: "Books", amount: "12", funder: "district", claim_status: "to_request" }, "books");
            w.a.rq.funder = "district"; w.a.rq.period = "all";
            w.a.rqCsv();
            const toast = w.a.toastMsg;
            w.a.sel = { [w.a.E()[0].id]: true };
            w.a.bulkExport();
            res[lang] = { names: w.downloads.map((d) => d.name), toast };
          }
          out(res);""")
        day = r"\d{4}-\d{2}-\d{2}\.csv$"
        self.assertRegex(r["en"]["names"][0], r"^service-expenses-request-my-district-" + day)
        self.assertRegex(r["en"]["names"][1], r"^service-expenses-selected-" + day)
        self.assertRegex(r["es"]["names"][0], r"^gastos-de-servicio-solicitud-mi-distrito-" + day)
        self.assertRegex(r["es"]["names"][1], r"^gastos-de-servicio-seleccion-" + day)
        self.assertIn(r["es"]["names"][0], r["es"]["toast"])                  # "Se descargó …" names it


class Import(unittest.TestCase):
    def test_a_big_full_backup_is_restored(self):
        # P1-2: a .json backup with its photos inside (every full backup before 1.2.0), well over the 80 MB it
        # used to be refused at, is read in slices (GVF.jsonBackup) and every photo restored, each to its own
        # entry; a CSV still stops at 10 MB
        r = app(self, r"""
          const photos = new Map(), w = make("en", null, null, { photos });
          const G = w.G, fill = "A".repeat(400 * 1024);
          const entries = [], receipts = [];
          for (let i = 0; i < 220; i++) {
            const id = "b" + i;
            entries.push(G.normalizeEntry({ id, type: "expense", date: "2026-09-01", description: "Receipt " + i, amount_cents: 100 + i, receipt: "photo" }, w.a.st()).entry);
            // each photo starts with its own 6 bytes ("ph-007"), so the right one is checked at the right entry
            receipts.push({ id, type: "image/jpeg", dataUrl: "data:image/jpeg;base64," + btoa("ph-" + String(i).padStart(3, "0")) + fill });
          }
          const text = G.toBackup({ entries, settings: w.a.st(), meta: {} }, receipts);
          const mb = +(text.length / 1048576).toFixed(1);
          await w.a.impFile(fileOf("big-backup.json", text)); await tick();
          const backup = [w.a.imp.step, w.a.imp.err, w.a.imp.counts && w.a.imp.counts.entries, w.a.imp.counts && w.a.imp.counts.photos];
          await w.a.impApply();
          const head = async (id) => new TextDecoder().decode((await photos.get(id).blob.arrayBuffer()).slice(0, 6));
          const restored = [photos.size, await head("b0"), await head("b137"), await head("b219"), w.a.imp.photosDone, w.a.imp.photoErrs, w.a.E().length];
          const csv = "date,amount\n" + "2026-09-01,1\n".repeat(Math.ceil(11 * 1048576 / 13));
          await w.a.impFile(fileOf("big.csv", csv)); await tick();
          out({ mb, backup, restored, csv: w.a.imp.err, limits: [G.importLimit("csv"), G.importLimit("backup"), G.importLimit("zip")],
                kinds: [G.importKind("x.json", ""), G.importKind("backup.txt", "﻿ {"), G.importKind("a.csv", "date,amount")] });""", )
        self.assertGreater(r["mb"], 85)
        self.assertEqual(r["backup"], ["backup", "", 220, 220])
        self.assertEqual(r["restored"], [220, "ph-000", "ph-137", "ph-219", 220, 0, 220])
        self.assertEqual(r["csv"], "The file is larger than 10 MB.")
        self.assertEqual(r["limits"], [10 * 1048576, 4 * 1024 ** 3, 4 * 1024 ** 3])     # a backup: no limit that matters
        self.assertEqual(r["kinds"], ["backup", "backup", "csv"])

    def test_the_mapping_step(self):
        r = app(self, r"""
          const w = make("es");
          const file = (name, t) => ({ name, size: t.length, arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          w.a.impFile(file("millas.csv", "Fecha,Millas,Motivo\n27/09/2026,45.5,Asamblea\n")); await tick();
          const step = w.a.imp.step;
          w.a.imp.map.date = "0"; w.a.imp.map.miles = "1";
          const ready = w.a.impMapReady();
          w.a.impUseMap();
          const plan = [w.a.imp.step, w.a.imp.counts.add];
          w.a.impFile(file("gastos.csv", "Fecha,Importe,Concepto\nayer,abc,Café\n")); await tick();
          w.a.imp.map.date = "0"; w.a.imp.map.amount = "1"; w.a.imp.map.description = "2"; w.a.impUseMap();
          out({ step, ready, plan, problems: w.a.imp.errorList.map((x) => x.text) });""")
        self.assertEqual(r["step"], "map")
        self.assertTrue(r["ready"])                                           # a date and miles: no amount needed
        self.assertEqual(r["plan"], ["preview", 1])
        self.assertIn("Fila 2 · Importe: El monto no es un número como 12.50.", r["problems"])   # the visitor's own column

    def test_a_card_statement_and_the_sign_choice(self):
        r = app(self, r"""
          const w = make("en");
          const file = (name, t) => ({ name, size: t.length, arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          const rows = () => w.a.imp.sampleRows.map((x) => [x.desc, x.cat, x.amount]);
          w.a.impFile(file("amex.csv", "Date,Description,Amount\n09/02/2026,Office Depot,45.00\n09/03/2026,Kinko's copies,12.00\n09/04/2026,Refund Office Depot,-10.00\n")); await tick();
          w.a.imp.map.date = "0"; w.a.imp.map.description = "1"; w.a.imp.map.amount = "2"; w.a.impUseMap();
          const guessed = [w.a.imp.step, w.a.imp.opts.positive, JSON.parse(JSON.stringify(w.a.imp.signs)), rows()];
          w.a.imp.opts.positive = "received"; w.a.impPlan();          // the select's change
          const flipped = [w.a.imp.opts.positive, rows()];
          w.a.impApply();
          const stored = state(w).entries.map((e) => [e.description, e.type]).sort();
          // positive amounts only: still asked (a sheet of checks received), spending until told otherwise
          w.a.impFile(file("books.csv", "Date,Description,Amount\n09/02/2026,Books,20\n")); await tick();
          w.a.imp.map.date = "0"; w.a.imp.map.description = "1"; w.a.imp.map.amount = "2"; w.a.impUseMap();
          const oneSign = [w.a.imp.signs && w.a.imp.signs.negative, w.a.imp.opts.positive];
          // every amount with a minus: spending, nothing to ask
          const neg = make("en");
          neg.a.impFile(file("bank.csv", "Date,Description,Amount\n09/02/2026,Books,-20\n")); await tick();
          neg.a.imp.map.date = "0"; neg.a.imp.map.description = "1"; neg.a.imp.map.amount = "2"; neg.a.impUseMap();
          out({ guessed, flipped, stored, oneSign, allMinus: neg.a.imp.signs });""")
        self.assertEqual(r["guessed"], ["preview", "spent", {"positive": 2, "negative": 1}, [
            ["Office Depot", "Books & literature", "$45.00"], ["Kinko's copies", "Books & literature", "$12.00"],
            ["Refund Office Depot", "Reimbursement", "+$10.00"]]])
        self.assertEqual(r["flipped"], ["received", [
            ["Office Depot", "Reimbursement", "+$45.00"], ["Kinko's copies", "Reimbursement", "+$12.00"],
            ["Refund Office Depot", "Books & literature", "$10.00"]]])
        self.assertEqual(r["stored"], [["Kinko's copies", "received"], ["Office Depot", "received"], ["Refund Office Depot", "expense"]])
        self.assertEqual(r["oneSign"], [0, "spent"])                     # all positive: asked (they may be money in), spending by default
        self.assertIsNone(r["allMinus"])                                 # all with a minus: spending, nothing to ask

    def test_a_statement_read_in_the_date_order_it_shows(self):
        # a US card statement on the Spanish page (day-first by default): 09/15 shows the file is
        # month-first, so 09/03 is September 3 too — and the preview's select says what was used
        r = app(self, r"""
          const file = (name, t) => ({ name, size: t.length, arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          const w = make("es");
          w.a.impFile(file("tarjeta.csv", "Date,Description,Amount\n09/03/2026,Office Depot,45.00\n09/05/2026,Kinko's copies,12.00\n" +
                                          "09/15/2026,Hotel,90.00\n09/21/2026,Books,20.00\n09/28/2026,Parking,8.00\n"));
          await tick();
          const asked = w.a.imp.opts.dateOrder;
          w.a.imp.map.date = "0"; w.a.imp.map.description = "1"; w.a.imp.map.amount = "2"; w.a.impUseMap();
          const used = w.a.imp.opts.dateOrder;
          w.a.impApply();
          out({ asked, used, dates: state(w).entries.map((e) => e.date) });""")
        self.assertEqual((r["asked"], r["used"]), ("dmy", "mdy"))
        self.assertEqual(r["dates"], ["2026-09-03", "2026-09-05", "2026-09-15", "2026-09-21", "2026-09-28"])

    def test_a_backup_merged_in_brings_the_photos_this_device_lacks(self):
        # this device read the CSV first (the entries say "photo", same stamps, no photos); the full
        # backup, merged in, puts back the photos it lacks — and keeps the one it already has
        r = app(self, r"""
          const file = (name, t) => ({ name, size: t.length, arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          const photos = new Map(), w = make("en", null, null, { photos }), G = w.G, st = w.a.st();
          const E = ["p1", "p2"].map((id, i) => G.normalizeEntry({ id, type: "expense", date: "2026-09-0" + (i + 1), category: "books", description: "Receipt " + id,
            amount_cents: 1200, receipt: "photo", created: "2026-09-01T10:00:00.000Z", updated: "2026-09-01T10:00:00.000Z" }, st).entry);
          const backup = G.toBackup({ entries: E, settings: st, meta: {} }, E.map((e) => ({ id: e.id, type: "image/jpeg", dataUrl: "data:image/jpeg;base64,/9j/4AAQ" })));
          w.a.impFile(file("service-expenses.csv", G.toCSV(E, st, { lang: "en" }))); await tick();
          await w.a.impApply(); await tick();
          photos.set("p2", { id: "p2", type: "image/jpeg", blob: new Blob(["mine"]), mine: true });
          w.a.impFile(file("service-expenses-backup.json", backup)); await tick();
          const preview = [w.a.imp.step, w.a.imp.counts.entries, w.a.imp.counts.photos];
          await w.a.impApply(); await tick();
          out({ preview, entries: w.a.E().map((e) => [e.id, e.receipt]), photos: [...photos.keys()].sort(), mine: !!photos.get("p2").mine,
                blob: photos.has("p1") && photos.get("p1").blob instanceof Blob });""")
        self.assertEqual(r["preview"], ["backup", 2, 2])
        self.assertEqual(r["entries"], [["p1", "photo"], ["p2", "photo"]])
        self.assertEqual(r["photos"], ["p1", "p2"])
        self.assertTrue(r["mine"])                                       # the photo this device had stays as it was
        self.assertTrue(r["blob"])

    def test_done_counts_the_entries_the_merge_updated(self):
        # the tracker's own export, two descriptions edited in a spreadsheet, merged back: "Done" and the
        # toast count the 2 updated entries the Import button promised (they said "0 entries imported"),
        # and one entry reads "1 entry", in both languages
        r = app(self, r"""
          const file = (name, t) => ({ name, size: Buffer.byteLength(t), arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          const res = {};
          for (const lang of ["en", "es"]) {
            const run = async (n) => {            // a fresh tracker each time: its examples, exported, n rows edited
              const w = make(lang), G = w.G;
              w.a.addExamples();
              const lines = G.toCSV(w.a.E(), w.a.st(), { lang: "en" }).split("\n");
              for (let i = 1; i <= n; i++) {
                const cells = G.parseCSV(lines[i])[0];
                const d = G.parseCSV(lines[0])[0].indexOf("description"), u = G.parseCSV(lines[0])[0].indexOf("updated");
                cells[d] = cells[d] + " (checked)"; if (u >= 0) cells[u] = "2099-01-01T00:00:00.000Z";
                lines[i] = cells.map((c) => (/[",\n]/.test(c) ? '"' + String(c).replace(/"/g, '""') + '"' : c)).join(",");
              }
              w.a.impFile(file("service-expenses.csv", lines.join("\n"))); await tick();
              w.a.imp.mode = "merge";
              const button = w.a.plural(w.a.imp.counts.add + w.a.imp.counts.update, "imp.apply_one", "imp.apply");
              await w.a.impApply(); await tick();
              return { counts: [w.a.imp.added, w.a.imp.updated], button, done: w.a.plural(w.a.imp.added + w.a.imp.updated, "imp.done_one", "imp.done"), toast: w.a.toastMsg };
            };
            res[lang] = { two: await run(2), one: await run(1) };
          }
          out(res);""")
        self.assertEqual(r["en"]["two"]["counts"], [0, 2])
        self.assertEqual((r["en"]["two"]["button"], r["en"]["two"]["done"], r["en"]["two"]["toast"]),
                         ("Import 2 entries", "Done: 2 entries imported.", "2 entries imported"))
        self.assertEqual((r["en"]["one"]["button"], r["en"]["one"]["done"], r["en"]["one"]["toast"]),
                         ("Import 1 entry", "Done: 1 entry imported.", "1 entry imported"))
        self.assertEqual((r["es"]["two"]["button"], r["es"]["two"]["done"], r["es"]["two"]["toast"]),
                         ("Importar 2 registros", "Listo: 2 registros importados.", "2 registros importados"))
        self.assertEqual((r["es"]["one"]["done"], r["es"]["one"]["toast"]), ("Listo: 1 registro importado.", "1 registro importado"))


class TabBar(unittest.TestCase):
    def test_the_open_tab_is_scrolled_into_sight(self):
        # A phone's tab row as main.css draws it: 288px wide from x=25, 0.25rem of room before the tabs and
        # 2rem after them, where it fades (and as much at the start once scrolled); five 125px tabs 8px
        # apart; each tab snaps 2rem in from the left (expenses.css scroll-padding). The row is 693px
        # wide in all, so it scrolls 405px at most. A tab is "clear" between x = 57 (25 when not
        # scrolled) and x = 281.
        r = app(self, r"""
          const views = ["entries", "summary", "giveaways", "requests", "settings"];
          const row = { scrollLeft: 0, scrollWidth: 693, clientWidth: 288, style: { paddingRight: "32px", scrollPaddingLeft: "32px" },
                        getBoundingClientRect: () => ({ left: 25, right: 313 }) };
          const els = {};
          views.forEach((v, i) => { els["xp-tab-" + v] = { parentElement: row, focus() {},
            getBoundingClientRect: () => ({ left: 29 + i * 133 - row.scrollLeft, right: 29 + i * 133 + 125 - row.scrollLeft }) }; });
          const seen = (v) => { const b = els["xp-tab-" + v].getBoundingClientRect(); return [v, row.scrollLeft, b.left >= (row.scrollLeft > 4 ? 57 : 25) && b.right <= 281]; };
          // the next visit reopens Settings, the last tab
          const w = make("en", { [KEY + ":ui"]: JSON.stringify({ view: "settings" }) }, els);
          const reopened = seen(w.a.view);
          w.a.go("summary"); const tapped = seen("summary");
          w.a.go("summary"); const again = seen("summary");
          w.ctx.location.hash = "#requests"; w.listeners.hashchange.forEach((f) => f()); const linked = seen(w.a.view);
          w.a.tabKey({ key: "Home", preventDefault() {} }); const home = seen(w.a.view);
          w.a.tabKey({ key: "ArrowRight", preventDefault() {} }); const next = seen(w.a.view);
          // a wide screen: the row does not scroll, nothing moves
          row.clientWidth = 693; row.scrollLeft = 0; w.a.go("settings"); const wide = [w.a.view, row.scrollLeft];
          out({ reopened, tapped, again, linked, home, next, wide });""")
        self.assertEqual(r["reopened"], ["settings", 405, True])            # the row's end
        self.assertEqual(r["tapped"], ["summary", 105, True])               # its start at 57: 405 + (162 − 405) − 57
        self.assertEqual(r["again"], ["summary", 105, True])                # already clear: nothing moves
        self.assertEqual(r["linked"], ["requests", 371, True])
        self.assertEqual(r["home"], ["entries", 0, True])
        self.assertEqual(r["next"], ["summary", 105, True])                 # 162–287 ran into the end fade
        self.assertEqual(r["wide"], ["settings", 0])


class TheRest(unittest.TestCase):
    def test_examples_once_csv_not_a_backup_badge(self):
        r = app(self, r"""
          const w = make("en");
          w.a.addExamples(); const n1 = w.a.E().length;
          w.a.addExamples(); const n2 = w.a.E().length;
          w.a.exportAll();
          const meta = state(w).meta;
          out({ n1, n2, csv: [!!meta.lastExport, meta.lastBackup], badge: w.a.reminderCount(), card: w.a.staleRows().length + (w.a.backupDue() ? 1 : 0),
                renewals: w.a.renewalRows().length, file: w.downloads[0].name });""")
        self.assertEqual(r["n1"], r["n2"])                                    # the examples are added once
        self.assertEqual(r["csv"], [True, None])                              # an export, not a backup
        self.assertEqual(r["badge"], r["card"])                               # the badge counts what the card lists
        self.assertGreaterEqual(r["renewals"], 1)                             # (the renewal is in its own card)
        self.assertRegex(r["file"], r"^service-expenses-\d{4}-\d{2}-\d{2}\.csv$")

    def test_the_summary_counts_subscriptions_as_subscriptions(self):
        # "By category": 3 gift subscriptions bought at once are "3 subscriptions" (the word the Giveaways list
        # and the report use), books stay items
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang);
            add(w, "expense", { sub_kind: "gift", person: "Maria G.", sub_product: "gv_print", sub_term: "12", quantity: "3", description: "Gifts", amount: "108" }, "subscriptions");
            add(w, "expense", { sub_kind: "gift", person: "Luis M.", sub_product: "gv_print", sub_term: "12", description: "Gift", amount: "36" }, "subscriptions");
            add(w, "expense", { description: "Books", item: "Big Book", quantity: "2", unit_cost: "12" }, "books");
            w.a.f.period = "all";
            res[lang] = w.a.byCat().map((c) => [c.id, c.items]);
          }
          out(res);""")
        self.assertEqual(dict(r["en"]), {"subscriptions": "4 subscriptions", "books": "2 items"})
        self.assertEqual(dict(r["es"]), {"subscriptions": "4 suscripciones", "books": "2 artículos"})

    def test_sort_by_category_follows_the_names_on_screen(self):
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang);
            add(w, "expense", { description: "Pizza", amount: "42" }, "meals");
            add(w, "expense", { description: "Hotel", amount: "90" }, "lodging");
            add(w, "expense", { description: "Big Book", amount: "12" }, "books");
            w.a.sort = "category"; w.a.f.period = "all";
            res[lang] = w.a.rows().map((x) => x.cat);
          }
          out(res);""")
        self.assertEqual(r["en"], ["Books & literature", "Hotel & lodging", "Meals"])
        self.assertEqual(r["es"], ["Comidas", "Hotel y hospedaje", "Libros y literatura"])   # not in the English names' order

    def test_items_that_differ_by_an_accent_are_two_rows(self):
        # the core counts "La Viña" and "La Vina" apart (accents are part of a title): each row has its
        # own key, so the table's x-for shows all three (a repeated key shows one row for two)
        r = app(self, r"""
          const w = make("en");
          add(w, "stock", { item: "La Viña", quantity: "10", description: "From the Area" });
          add(w, "stock", { item: "La Vina", quantity: "4", description: "From the district" });
          add(w, "stock", { item: "Grapevine", quantity: "7", description: "From the Area" });
          const rows = w.a.inv();
          out({ rows: rows.map((x) => [x.item, x.onHand]).sort(), keys: new Set(rows.map((x) => x.key)).size, core: w.G.inventory(w.a.E()).length });""")
        self.assertEqual(r["rows"], [["Grapevine", 7], ["La Vina", 4], ["La Viña", 10]])
        self.assertEqual((r["keys"], r["core"]), (3, 3))

    def test_last_backup_counts_calendar_days(self):
        # Wednesday, September 30, 8 AM: a backup made last night was "yesterday", not "today"; the
        # reminder counts the same days (30 by default: due once the last backup is 31 days back)
        r = app(self, r"""
          const now = new Date(2026, 8, 30, 8, 0).getTime();
          const at = (m, d, h) => new Date(2026, m - 1, d, h, 0).toISOString();
          const w = make("en", null, null, { now });
          const due = (iso) => make("en", { [KEY]: JSON.stringify({ v: 1, entries: [{ id: "a1", type: "expense", date: "2026-09-01", category: "books",
            description: "Books", amount_cents: 1200 }], settings: {}, meta: { lastBackup: iso } }) }, null, { now }).a.backupDue();
          out({ got: [at(9, 30, 7), at(9, 29, 23), at(9, 29, 9), at(9, 28, 23), at(9, 27, 12)].map((iso) => w.a.ago(iso)),
                want: [w.a.t("time.today"), w.a.t("time.yesterday"), w.a.t("time.yesterday"), w.a.t("time.days_ago", { n: 2 }), w.a.t("time.days_ago", { n: 3 })],
                due: [due(at(8, 31, 23)), due(at(8, 30, 23)), due(null)] });""", env={"TZ": "America/Chicago"})
        self.assertEqual(r["got"], r["want"])
        self.assertEqual(r["due"], [False, True, True])                     # 30 days back: not yet; 31: due; never: due


class TripsRolesActivities(unittest.TestCase):
    """The form's new fields: several trips on one entry, "I didn't drive", the role, the service activity,
    the store's reference, several subscriptions at once."""

    def test_several_trips_on_one_entry(self):
        # 58.7 mi one way, there and back on 3 days: 352.2 mi; an edit shows 58.7 and 3 again, and saving it
        # unchanged moves nothing; the odometer is the whole trip (the trips don't multiply it)
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang);
            w.a.openAdd("mileage");
            Object.assign(w.a.form, { from: "Home", to: "Hilton Fort Worth", miles: "58.7", round_trip: true, trips: "3", rate: "0.30", rate_id: "service",
                                      date: "2026-07-24", end_date: "2026-07-26", event: "Texas State Convention", activity: "table", role: "Table support" });
            const preview = w.a.mileagePreview();
            w.a.saveForm(false);
            const e = w.a.E()[0];
            w.a.openEdit(e.id);
            const shown = [w.a.form.miles, w.a.form.trips, w.a.form.round_trip, w.a.has("trips"), w.a.has("end_date"), w.a.has("role")];
            w.a.saveForm(false);
            const again = w.a.E()[0];
            add(w, "mileage", { from: "Home", to: "Tyler", odometer_start: "100", odometer_end: "150", trips: "4", rate: "0.30" });
            const odo = w.a.E().at(-1);
            w.a.f.period = "all";
            const row = w.a.rowOf(e);
            res[lang] = { e: [e.miles, e.trips, e.amount_cents, e.end_date, e.activity, e.role], preview, shown,
                          same: [again.miles, again.trips, again.amount_cents].join() === [e.miles, e.trips, e.amount_cents].join(),
                          odo: [odo.miles, odo.trips], sub: row.sub,
                          want: w.a.t("form.preview_round_trips", { n: "3", each: w.a.count(117.4), miles: w.a.count(352.2), rate: "0.30", amount: w.a.money(10566) }) };
          }
          out(res);""")
        for lang, x in r.items():
            with self.subTest(lang=lang):
                # 352.2 mi × $0.30 = $105.66
                self.assertEqual(x["e"], [352.2, 3, 10566, "2026-07-26", "table", "Table support"])
                self.assertEqual(x["preview"], x["want"])
                self.assertEqual(x["shown"], ["58.7", "3", True, True, True, True])
                self.assertTrue(x["same"])
                self.assertEqual(x["odo"], [50, ""])
        self.assertIn("3 round trips", r["en"]["sub"])
        self.assertIn("Table support", r["en"]["sub"])
        self.assertIn("Information tables & conventions", r["en"]["sub"])
        self.assertIn("3 viajes de ida y vuelta", r["es"]["sub"])

    def test_i_didnt_drive(self):
        # Big Country: rode with Area Archives — on record with the event, the role and the activity; no
        # miles, $0, nothing to ask (even when the form had a funder and miles typed before the box was ticked)
        r = app(self, r"""
          const w = make("en");
          w.a.openAdd("mileage");
          Object.assign(w.a.form, { miles: "212.5", round_trip: true, trips: "2", funder: "district", claim_status: "to_request", date: "2026-09-04",
                                    end_date: "2026-09-06", from: "Home", to: "Abilene" });
          w.a.form.no_miles = true;
          const shows = ["funder", "status", "method", "receipt", "trips", "role", "activity", "end_date"].map((k) => k + ":" + w.a.has(k));
          const title = [w.a.formTitle()];
          Object.assign(w.a.form, { person: "Area Archives", event: "Big Country 41st AA Conference", role: "GV/LV table support", activity: "workshop" });
          w.a.saveForm(false);
          const e = w.a.E()[0];
          w.a.f.period = "all";
          const row = w.a.rowOf(e);
          w.a.rq.funder = "district"; w.a.rq.period = "all";
          // a trip driven to the next one, then "Save and add another": the event's activity and role come along
          w.a.openAdd("mileage");
          title.push(w.a.formTitle());
          Object.assign(w.a.form, { from: "Home", to: "Tyler", miles: "98.5", round_trip: true, event: "Summer Assembly", activity: "assembly", role: "Attended" });
          w.a.saveForm(true);
          const next = [w.a.form.event, w.a.form.activity, w.a.form.role, w.a.form.miles];
          w.a.openEdit(e.id);
          title.push(w.a.formTitle());
          out({ errs: w.a.formErrs, shows, title, e: [e.no_miles, e.miles, e.trips, e.round_trip, e.from, e.to, e.amount_cents, e.funder, e.claim_status, e.person, e.role, e.activity],
                row: [row.amount, row.miles, row.funder, row.sub], asked: w.a.rqEntries().length, next,
                sum: w.G.summary(w.a.E(), w.a.st(), {}).by_activity.map((a) => [a.id, a.trips, a.no_miles]) });""")
        self.assertEqual(r["errs"], [])
        self.assertEqual(r["shows"], ["funder:false", "status:false", "method:false", "receipt:false", "trips:false", "role:true", "activity:true", "end_date:true"])
        # the dialog's name says what it is: a trip with no miles is not "Miles driven" (form.title_*_ride)
        self.assertEqual(r["title"], ["A trip (no miles)", "Miles driven", "Edit a trip (no miles)"])
        self.assertEqual(r["e"], [True, "", "", False, "", "", 0, "me", "none", "Area Archives", "GV/LV table support", "workshop"])
        self.assertEqual(r["row"][:3], ["No miles", "", ""])
        self.assertIn("Rode with Area Archives", r["row"][3])
        self.assertEqual(r["asked"], 0)                                         # never in a request
        self.assertEqual(r["next"], ["Summer Assembly", "assembly", "Attended", ""])
        self.assertEqual(r["sum"], [["assembly", 1, 0], ["workshop", 1, 1]])

    def test_an_edit_keeps_the_name_a_driven_trip_came_with(self):
        # A trip imported with a name in its person column: the form shows no such field on a trip that was
        # driven, so an edit of its event keeps the name (it is never dropped unseen), and so does a duplicate.
        # A name typed for a ride ("I didn't drive") and then unticked is not kept; a ride keeps whom you rode with.
        r = app(self, r"""
          const w = make("en");
          w.a.impReset();
          w.a.impCsvText("date,type,miles,rate,person,event,round_trip\n2026-09-12,mileage,30,0.30,Rosa T.,District meeting,yes\n");
          w.a.impApply();
          const id = w.a.E()[0].id, before = w.a.E()[0].person;
          w.a.openEdit(id); w.a.form.event = "District 22 business meeting"; w.a.saveForm(false);
          const edited = w.a.E().find((e) => e.id === id);
          w.a.duplicate(id); w.a.saveForm(false);
          const dup = w.a.E().at(-1);
          w.a.openAdd("mileage");
          Object.assign(w.a.form, { no_miles: true, person: "Luis M." });
          Object.assign(w.a.form, { no_miles: false, from: "Home", to: "Allen", miles: "20.7", round_trip: true });
          w.a.saveForm(false);
          const unticked = w.a.E().at(-1);
          w.a.openAdd("mileage");
          Object.assign(w.a.form, { no_miles: true, person: "Ana P.", event: "Big Country" });
          w.a.saveForm(false);
          out({ before, edited: [edited.person, edited.event, edited.miles], dup: [dup.person, dup.id !== id], unticked: unticked.person, ride: w.a.E().at(-1).person });""")
        self.assertEqual(r["before"], "Rosa T.")
        self.assertEqual(r["edited"], ["Rosa T.", "District 22 business meeting", 30])   # (a CSV's miles are the whole trip)
        self.assertEqual(r["dup"], ["Rosa T.", True])
        self.assertEqual(r["unticked"], "")
        self.assertEqual(r["ride"], "Ana P.")

    def test_the_reference_and_several_subscriptions_at_once(self):
        r = app(self, r"""
          const w = make("en");
          // a hotel's confirmation sits in the form itself; elsewhere it is under "More details" (opened on edit)
          add(w, "expense", { description: "Summer Assembly", amount: "152.50", vendor: "A hotel", place: "Tyler", ref: "Conf. 12345AB678901",
                              date: "2026-06-26", end_date: "2026-06-28", activity: "assembly" }, "lodging");
          add(w, "expense", { description: "Badges", amount: "12", ref: "Order 1042" }, "supplies");
          add(w, "giveaway", { item: "Grapevine", quantity: "10", ref: "never kept", role: "nor this", event: "CityWide" });
          add(w, "expense", { description: "Gifts for the jail", amount: "180", person: "Carry the Message", sub_product: "gv_print", quantity: "10", date: "2026-09-01" }, "subscriptions");
          const [hotel, badges, given, subs] = w.a.E();
          w.a.openEdit(hotel.id); const moreHotel = w.a.formMore; w.a.closeForm(); w.a.form = null;
          w.a.openEdit(badges.id); const moreBadges = w.a.formMore; w.a.closeForm(); w.a.form = null;
          w.a.f.period = "all";
          out({ refs: [hotel.ref, hotel.nights, badges.ref, given.ref, given.role, given.activity], more: [moreHotel, moreBadges],
                subs: [subs.quantity, subs.sub_kind, w.a.subsAll()[0].qty], row: w.a.rowOf(subs).sub,
                counts: w.G.subscriptionCounts(w.a.subsAll(), { from: "2026-01-01", to: "2026-12-31" }).gifted });""")
        self.assertEqual(r["refs"], ["Conf. 12345AB678901", 2, "Order 1042", "", "", ""])
        self.assertEqual(r["more"], [False, True])
        self.assertEqual(r["subs"], [10, "gift", 10])
        self.assertIn("10 subscriptions", r["row"])
        self.assertEqual(r["counts"], 10)                                       # ten gifts, not one

    def test_the_activity_filter_and_the_request_trips(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "mileage", { from: "Home", to: "Lover's Lane UMC", miles: "21.4", round_trip: true, trips: "7", activity: "table", funder: "district",
                              claim_status: "to_request", event: "Dallas CityWide" });
          add(w, "mileage", { from: "Home", to: "Allen", miles: "20.7", round_trip: true, funder: "district", claim_status: "to_request" });
          add(w, "expense", { description: "Books", amount: "12", activity: "table" }, "books");
          w.a.f.period = "all";
          const ids = (f) => { w.a.f.activity = f; return w.a.filtered().length; };
          const counts = [ids(""), ids("table"), ids("-"), ids("district")];
          w.a.f.activity = "table";
          const more = w.a.moreCount();
          w.a.clearFilters();
          w.a.rq.funder = "district"; w.a.rq.period = "all";
          out({ counts, more, cleared: w.a.f.activity, purposes: w.a.rqMileage().map((m) => m.purpose), text: w.a.rqText() });""")
        self.assertEqual(r["counts"], [3, 2, 1, 0])
        self.assertEqual((r["more"], r["cleared"]), (1, ""))
        # the trips said once on the printed request (the event, or the core's words that already say them)
        self.assertEqual(r["purposes"], ["Dallas CityWide · 7 round trips", "Home → Allen"])
        self.assertIn("7 round trips", r["text"])


class SubscriptionsView(unittest.TestCase):
    def test_the_list_its_counts_and_the_calendar_file(self):
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang), today = w.G.todayISO();
            const none = (w.a.subsIcs(), [w.downloads.length, w.a.toastMsg === w.a.t("subs.ics_none")]);
            // ends in 20 days (bought 11 months and 10 days ago), ended 3 months ago, and one renewed by a later one
            const start = (m, d) => w.G.addDays(w.G.addMonths(today, m), d);
            add(w, "expense", { sub_kind: "gift", person: "Maria G.", sub_product: "gv_print", sub_term: "12", sub_start: start(-12, 20), date: start(-12, 20), description: "Gift", amount: "36" }, "subscriptions");
            add(w, "expense", { sub_kind: "gift", person: "Luis M.", sub_product: "lv_print", sub_term: "12", sub_start: start(-15, 0), date: start(-15, 0), description: "Gift", amount: "30" }, "subscriptions");
            add(w, "expense", { sub_kind: "gift", person: "Rosa T.", sub_product: "gv_print", sub_term: "12", sub_start: start(-13, 0), date: start(-13, 0), description: "Gift", amount: "36" }, "subscriptions");
            add(w, "expense", { sub_kind: "gift", person: "Rosa T.", sub_product: "gv_complete", sub_term: "12", sub_start: start(-1, 0), date: start(-1, 0), description: "Renewed", amount: "40" }, "subscriptions");
            const statuses = w.a.subRows().map((s) => [s.who, s.status]);
            w.a.subToggle("ending");
            const ending = w.a.subRows().map((s) => s.who);
            w.a.subToggle("ending");
            w.a.subF.kind = "helped";
            const helped = w.a.subRows().length;
            w.a.subF.kind = "";
            w.a.subsIcs();
            const d = w.downloads.at(-1), ics = await w.text(d);
            res[lang] = { none, statuses, ending, helped, counts: ["", "ending", "ended", "renewed", "active"].map((s) => w.a.subStatusCount(s)),
                          tiles: w.a.subTiles().map((t) => [t.id, t.value]), name: d.name, events: ics.split("BEGIN:VEVENT").length - 1,
                          uids: (ics.match(/UID:[^\r\n]+/g) || []).length, crlf: ics.includes("\r\n") && !/[^\r]\n/.test(ics), toast: w.a.toastMsg };
          }
          out(res);""")
        for lang, x in r.items():
            with self.subTest(lang=lang):
                self.assertEqual(x["none"], [0, True])                          # nothing to renew: no file, a word why
                self.assertEqual(x["statuses"], [["Maria G.", "ending"], ["Luis M.", "ended"], ["Rosa T.", "active"], ["Rosa T.", "renewed"]])
                self.assertEqual(x["ending"], ["Maria G."])
                self.assertEqual(x["helped"], 0)
                self.assertEqual(x["counts"], [4, 1, 1, 1, 1])
                self.assertEqual(dict(x["tiles"])["ending"], "1")
                # the ones still to renew: Maria's (ending) and Rosa's renewal (active); one UID each
                self.assertEqual((x["events"], x["uids"]), (2, 2))
                self.assertTrue(x["crlf"])
                self.assertIn(x["name"], x["toast"])
        self.assertRegex(r["en"]["name"], r"^service-expenses-renewals-\d{4}-\d{2}-\d{2}\.ics$")
        self.assertRegex(r["es"]["name"], r"^gastos-de-servicio-renovaciones-\d{4}-\d{2}-\d{2}\.ics$")

    def test_counts_follow_the_subscriptions_and_whom_they_are_for(self):
        # One entry of 10 subscriptions for the group counts 10 in the chips and the line over the list, as on the
        # tiles. Your own and the group's say so in the list; "No name given" is for a gift typed without a name.
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang), today = w.G.todayISO(), start = w.G.addDays(w.G.addMonths(today, -12), 20);
            add(w, "expense", { sub_kind: "group", funder: "group", sub_product: "lv_print", sub_term: "12", sub_start: start, date: start, quantity: "10",
                                description: "For the jail", amount: "300" }, "subscriptions");
            add(w, "expense", { sub_kind: "self", sub_product: "lv_online", sub_term: "12", sub_start: today, date: today, description: "Mine", amount: "15" }, "subscriptions");
            add(w, "expense", { sub_kind: "gift", person: "", sub_product: "gv_print", sub_term: "12", sub_start: today, date: today, description: "Gift", amount: "36" }, "subscriptions");
            const chips = ["", "ending", "active"].map((s) => w.a.subStatusCount(s)), who = w.a.subRows().map((s) => s.who);
            w.a.subToggle("ending");
            res[lang] = { chips, who, shownEnding: w.a.subShown(), line: w.a.plural(w.a.subShown(), "subs.shown_one", "subs.shown"),
                          tiles: w.a.subTiles().map((t) => [t.id, t.value]) };
          }
          out(res);""")
        en = r["en"]
        self.assertEqual(en["chips"], [12, 10, 2])                              # every one, ending soon, active
        self.assertEqual((en["shownEnding"], en["line"]), (10, "10 subscriptions"))   # one row, ten subscriptions
        self.assertEqual(dict(en["tiles"])["ending"], "10")
        self.assertEqual(sorted(en["who"]), ["No name given", "The group", "Your own use"])
        self.assertEqual(sorted(r["es"]["who"]), ["El grupo", "Sin nombre", "Tu propio uso"])

    def test_the_calendar_file_after_a_renewal(self):
        # "Record the renewal", then the calendar file again: the same event (its UID), moved to the new end date
        r = app(self, r"""
          const w = make("en"), today = w.G.todayISO(), start = w.G.addDays(w.G.addMonths(today, -12), 20);
          add(w, "expense", { sub_kind: "gift", person: "Maria G.", sub_product: "gv_print", sub_term: "12", sub_start: start, date: start, description: "Gift", amount: "36" }, "subscriptions");
          const old = w.a.E()[0];
          const ev = async () => { w.a.subsIcs(); const t = await w.text(w.downloads.at(-1));
            return [(t.match(/UID:[^\r\n]+/g) || []), (t.match(/SEQUENCE:\d+/g) || []), (t.match(/DTSTART;VALUE=DATE:\d+/g) || [])]; };
          const before = await ev();
          w.a.renew(old.id); w.a.saveForm(false);
          const after = await ev();
          out({ before, after, old: old.id, end1: w.G.subEnd(old).replace(/-/g, ""), end2: w.G.addMonths(w.G.subEnd(old), 12).replace(/-/g, "") });""")
        uid = "UID:gvlv-sub-" + r["old"] + "@neta65-tracker"
        self.assertEqual(r["before"], [[uid], ["SEQUENCE:0"], ["DTSTART;VALUE=DATE:" + r["end1"]]])
        self.assertEqual(r["after"], [[uid], ["SEQUENCE:1"], ["DTSTART;VALUE=DATE:" + r["end2"]]])


class GiveawaysPeriod(unittest.TestCase):
    def test_the_literature_follows_the_period(self):
        r = app(self, r"""
          const w = make("en");
          add(w, "expense", { description: "Issues", item: "Grapevine", format: "gv", quantity: "20", unit_cost: "2.50", giveaway: true, date: "2025-11-02" }, "giveaways");
          add(w, "giveaway", { item: "Grapevine", format: "gv", quantity: "12", event: "Fall Assembly", date: "2026-03-20" });
          add(w, "stock", { item: "La Viña", format: "lv", quantity: "6", date: "2026-04-01" });
          const at = (p, from, to) => { w.a.f.period = p; w.a.f.from = from || ""; w.a.f.to = to || "";
            return { rows: w.a.inv().map((x) => [x.item, x.start, x.bought, x.received, x.given, x.onHand]), start: w.a.anyStart(),
                     tiles: w.a.giveTiles().map((t) => [t.id, t.value, t.note]), events: w.a.giveEvents().map((g) => g.name) }; };
          out({ y2026: at("custom", "2026-01-01", "2026-12-31"), all: at("all"), y2025: at("custom", "2025-01-01", "2025-12-31") });""")
        y = r["y2026"]
        # 20 bought in 2025 were on hand when 2026 began: 20 + 0 + 6 − 12 = 14 on hand
        self.assertEqual(y["rows"], [["Grapevine", "20", "0", "0", "12", 8], ["La Viña", "0", "0", "6", "0", 6]])
        self.assertTrue(y["start"])
        self.assertEqual(y["tiles"][0], ["given", "12", "Grapevine 12 · La Viña 0"])
        self.assertEqual(y["tiles"][3][:2], ["on_hand", "14"])
        self.assertEqual(y["events"], ["Fall Assembly"])
        self.assertFalse(r["all"]["start"])                                    # all dates: nothing before them
        self.assertEqual(r["all"]["rows"], [["Grapevine", "0", "20", "0", "12", 8], ["La Viña", "0", "0", "6", "0", 6]])
        self.assertEqual((r["y2025"]["rows"], r["y2025"]["events"]), ([["Grapevine", "0", "20", "0", "0", 20]], []))

    def test_an_empty_period_says_so(self):
        # nothing given in the period: "in this period" once something was given at another time, "yet" before
        r = app(self, r"""
          const w = make("en");
          const first = [w.a.everLit(), w.a.everGiven()];
          add(w, "giveaway", { item: "Grapevine", format: "gv", quantity: "12", event: "Fall Assembly", date: "2026-03-20" });
          w.a.f.period = "custom"; w.a.f.from = "2025-01-01"; w.a.f.to = "2025-12-31";
          out({ first, then: [w.a.everLit(), w.a.everGiven(), w.a.inv().length, w.a.giveEvents().length],
                words: ["give.inventory_none_period", "give.by_event_none_period"].map((k) => w.a.t(k)) });""")
        self.assertEqual(r["first"], [False, False])
        self.assertEqual(r["then"], [True, True, 0, 0])                       # (the page then shows these words)
        self.assertEqual(r["words"], ["Nothing to give away in this period.", "Nothing given away in this period."])


class ServiceReport(unittest.TestCase):
    def test_the_report_on_screen_and_its_csv(self):
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const w = make(lang, null, null, { now: Date.UTC(2026, 9, 6, 17) });      // a fixed today: Tuesday, October 6, 2026
            add(w, "expense", { description: "Spring Assembly room", amount: "150", vendor: "Room shared with a member", method: "check", ref: "Check #101",
                                date: "2026-03-20", end_date: "2026-03-22", activity: "assembly" }, "lodging");
            add(w, "mileage", { from: "Home", to: "Duncanville", miles: "31.5", round_trip: true, rate: "0.30", event: "Spring Assembly", activity: "assembly",
                                date: "2026-03-20", end_date: "2026-03-22" });
            add(w, "mileage", { from: "Home", to: "Fort Worth", miles: "58.7", round_trip: true, trips: "3", rate: "0.30", event: "State Convention",
                                activity: "table", role: "Table support", date: "2026-07-24" });
            add(w, "mileage", { no_miles: true, person: "Area Archives", event: "Big Country", activity: "workshop", role: "Table support", date: "2026-09-04" });
            add(w, "mileage", { from: "Home", to: "Dallas", miles: "10", rate: "0.30", date: "2025-12-01", activity: "district" });
            w.a.rp.period = "y:2026";
            w.a.setReport("prepared_for", "  District 22 treasurer  ");
            w.a.setReport("note", "A record,\r\nnot a request.");
            const v = w.a.rpView();
            const periods = w.a.rpPeriods().map((p) => p.id);
            w.a.rpCsv();
            const d = w.downloads.at(-1), csv = await w.text(d);
            w.a.rp.names = true;
            const named = w.a.rpView().miles.flatMap((s) => s.lines).find((l) => l.rode).route;
            w.a.rp.period = "y:2024";
            const empty = [w.a.rpView().empty, (w.a.rpCsv(), w.a.toastMsg === w.a.t("toast.nothing_to_export"))];
            res[lang] = { rows: v.rows.map((x) => [x.kind, x.label, x.amount]), period: v.period, rates: v.rates, periods,
                          money: v.money.map((s) => s.lines.map((l) => [l.dates, l.paid, l.where])), miles: v.miles.map((s) => [s.label, s.lines.map((l) => [l.what, l.trips, l.oneWay, l.miles, l.route, l.role])]),
                          totals: v.totals.map((x) => x.value), report: w.a.st().report, saved: JSON.parse(w.store.get(KEY)).settings.report,
                          name: d.name, csv, named, empty, title: w.a.rpPeriodLabel() };
          }
          // on New Year's Day the new year comes first, before last year's entries
          const ny = make("en", null, null, { now: Date.UTC(2027, 0, 1, 12) });
          add(ny, "mileage", { from: "Home", to: "Dallas", miles: "10", rate: "0.30", date: "2026-12-01", activity: "district" });
          res.newYear = ny.a.rpPeriods().map((p) => p.id).slice(0, 2);
          out(res);""")
        en = r["en"]
        # $150 room + 63 mi × $0.30 = $18.90 + 352.2 mi × $0.30 = $105.66 (+ the ride: $0) = $274.56; 2025's trip is out
        self.assertEqual(en["rows"], [["money", "Hotel & lodging", "$150.00"], ["miles", "Assemblies & Area committee meetings", "$18.90"],
                                      ["miles", "Information tables & conventions", "$105.66"], ["miles", "Workshops & events", "$0.00"],
                                      ["miles_total", "Mileage total", "$124.56"], ["total", "Total cost of service", "$274.56"]])
        self.assertEqual(en["rates"], "$0.30 a mile")
        self.assertEqual(en["periods"][:2], ["y:2026", "y:2025"])           # this year (the page's clock) first
        self.assertEqual(r["newYear"], ["y:2027", "y:2026"])
        # (a date's words kept together: no-break spaces; the year once)
        self.assertEqual(en["money"], [[["Mar 20 – Mar 22, 2026", "Check · Check #101", "Room shared with a member"]]])
        self.assertEqual(en["miles"][1], ["Information tables & conventions", [["State Convention", "3", "58.7", "352.2", "Home → Fort Worth", "Table support"]]])
        # whom you rode with is a name: out unless names are in
        self.assertEqual(en["miles"][2][1], [["Big Country", "—", "—", "0", "Rode with someone: no miles", "Table support"]])
        self.assertEqual(en["named"], "Rode with Area Archives")
        self.assertEqual(en["totals"], ["$274.56", "$0.00", "$0.00", "$0.00"])     # all of it self-supported
        self.assertEqual(en["report"], {"prepared_for": "District 22 treasurer", "note": "A record,\nnot a request."})
        self.assertEqual(en["saved"], en["report"])                                 # kept with the settings (and the backup)
        self.assertEqual(en["name"], "service-expenses-report-2026-2026-10-06.csv")      # the period, then today
        self.assertEqual(r["es"]["name"], "gastos-de-servicio-informe-2026-2026-10-06.csv")
        self.assertTrue(en["csv"].startswith("Section,Date,"))                     # (the BOM is the file's; Blob.text() drops it)
        self.assertTrue(r["es"]["csv"].startswith("Sección,Fecha,"))
        self.assertNotIn("Area Archives", en["csv"])
        self.assertEqual(en["empty"], [True, True])
        self.assertEqual(r["es"]["rows"][-1], ["total", "Costo total del servicio", r["es"]["rows"][-1][2]])

    def test_the_one_way_miles_multiply_back(self):
        # 25.3 mi there and back is 12.65 mi one way: the report says 12.65 — as its CSV does — never 12.7,
        # which doubles to 25.4; and a date keeps its words together (no-break spaces), a range breaks at its dash
        r = app(self, r"""
          const w = make("en");
          w.ctx.GV.fmtDate = (iso, o) => new Intl.DateTimeFormat("en-US", Object.assign({ timeZone: "UTC" }, o)).format(new Date(iso));
          add(w, "mileage", { from: "Home", to: "Grand Prairie", miles: "12.65", round_trip: true, rate: "0.30", event: "Summer ACM", activity: "assembly",
                              date: "2026-07-12", end_date: "2026-07-13" });
          w.a.rp.period = "y:2026";
          const l = w.a.rpView().miles[0].lines[0];
          w.a.rpCsv();
          out({ miles: w.a.E()[0].miles, line: [l.oneWay, l.miles, l.tripLine], dates: l.dates, csv: await w.text(w.downloads.at(-1)) });""")
        self.assertEqual(r["miles"], 25.3)
        self.assertEqual(r["line"], ["12.65", "25.3", "round trip · 12.65 mi one way"])
        self.assertIn(",12.65,25.3,", r["csv"])
        self.assertEqual(r["dates"], "Jul 12 – Jul 13, 2026")


class ActivitiesSettings(unittest.TestCase):
    def test_add_rename_merge_and_delete(self):
        r = app(self, r"""
          const w = make("en");
          const built = w.a.list("activities").map((a) => a.id);
          w.a.addActivity();
          const mine = w.a.list("activities").at(-1);
          w.a.setName("activities", mine.id, "name", "  Retreats ");
          const named = w.a.actName(mine.id);
          const unused = w.a.canDelete("activities", mine.id);
          add(w, "mileage", { from: "Home", to: "Camp", miles: "40", activity: mine.id });
          add(w, "mileage", { from: "Home", to: "Hall", miles: "5", activity: "other" });
          const deletable = [unused, w.a.canDelete("activities", mine.id), w.a.canDelete("activities", "other")];
          // "other" is used: its entries move to "Retreats" first; a built-in is hidden, never deleted
          w.a.confirm = () => Promise.resolve(true);
          w.a.merge("activities", "other", mine.id);
          await tick();
          const other = w.a.item("activities", "other");
          w.a.move("activities", mine.id, -1);
          out({ built, named, deletable, moved: w.a.E().map((e) => e.activity), other: [!!other, other && other.hidden],
                order: w.a.list("activities").map((a) => a.id).slice(-2), shown: w.a.activities().map((a) => a.id).includes("other"),
                canNow: w.a.canDelete("activities", "other") });""")
        self.assertEqual(r["built"], ["assembly", "district", "table", "workshop", "committee", "group", "other"])
        self.assertEqual(r["named"], "Retreats")
        self.assertEqual(r["deletable"], [True, False, False])                   # an unused own one can go; a used one or a built-in, no
        self.assertEqual(r["moved"], [r["moved"][0], r["moved"][0]])
        self.assertEqual(r["other"], [True, True])
        self.assertFalse(r["shown"])                                            # hidden from the form's list
        self.assertFalse(r["canNow"])


class Backups(unittest.TestCase):
    """P1-2 / F-8: the full backup is a .zip — backup.json and each receipt photo a file of its own — and another
    device restores it, photos and all; its size is said first, a big one is asked about (or backed up without
    photos); a .json without photos leaves this device's photos alone; an unpacked .zip restores from its
    backup.json picked with its photos; the backups made before 1.2.0 (photos inside the .json) restore; a photo
    the browser can't read is left out and named; photos that fail to restore are said."""

    def test_the_zip_round_trip(self):
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const photos = new Map(), w = make(lang, null, null, { photos });
            add(w, "expense", { description: "Hotel for the Fall Assembly", amount: "90", receipt: "photo", date: "2026-09-26" }, "lodging");
            add(w, "expense", { description: "Big Book", amount: "12", receipt: "photo", date: "2026-09-27" }, "books");
            add(w, "expense", { description: "Stamps", amount: "3", date: "2026-09-28" }, "other");
            const [hotel, book] = w.a.E();
            photos.set(hotel.id, { id: hotel.id, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 1, 2, 3])], { type: "image/jpeg" }), w: 1200, h: 900,
                                   name: "IMG_1.jpg", added: "2026-09-26T10:00:00.000Z" });
            photos.set(book.id, { id: book.id, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 9])], { type: "image/jpeg" }) });
            photos.set("gone", { id: "gone", type: "image/jpeg", blob: new Blob(["x"]) });          // no entry points to it: not backed up
            await w.a.exportBackup();
            const d = w.downloads.at(-1), zip = w.blob(d), ar = await w.F.readZip(zip);
            const inside = JSON.parse(await ar.text("backup.json"));
            // another device: a fresh tracker restores the .zip, photos and all
            const photos2 = new Map(), w2 = make(lang, null, null, { photos: photos2 });
            await w2.a.impFile(fileOf(d.name, zip));
            const preview = [w2.a.imp.step, JSON.parse(JSON.stringify(w2.a.imp.counts))];
            await w2.a.impApply();
            const back = async (m, id) => Array.from(new Uint8Array(await m.get(id).blob.arrayBuffer()));
            res[lang] = { name: d.name, toast: w.a.toastMsg, files: ar.entries.map((e) => e.name), receipts: inside.receipts.map((x) => [x.id, x.file, x.name || "", x.w || 0]),
                          lastBackup: !!state(w).meta.lastBackup, preview, entries: w2.a.E().map((e) => e.description), photos: [...photos2.keys()].sort(),
                          same: [await back(photos2, hotel.id), await back(photos2, book.id)], want: [await back(photos, hotel.id), await back(photos, book.id)],
                          meta: [photos2.get(hotel.id).w, photos2.get(hotel.id).name, photos2.get(hotel.id).type], ids: [hotel.id, book.id], done: [w2.a.imp.photosDone, w2.a.imp.photoErrs] };
          }
          out(res);""")
        en = r["en"]
        hotel, book = en["ids"]
        self.assertRegex(en["name"], r"^service-expenses-backup-\d{4}-\d{2}-\d{2}\.zip$")
        self.assertRegex(r["es"]["name"], r"^gastos-de-servicio-respaldo-\d{4}-\d{2}-\d{2}\.zip$")
        self.assertRegex(en["toast"], r"^Downloaded service-expenses-backup-[\d-]+\.zip · \d+ KB$")    # the size, at export
        self.assertEqual(en["files"], ["backup.json", f"2026-09-26-hotel-for-the-fall-assembly-{hotel}.jpg", f"2026-09-27-big-book-{book}.jpg"])
        self.assertEqual(en["receipts"], [[hotel, en["files"][1], "IMG_1.jpg", 1200], [book, en["files"][2], "", 0]])
        self.assertTrue(en["lastBackup"])
        self.assertEqual(en["preview"], ["backup", {"entries": 3, "photos": 2, "missing": 0}])
        self.assertEqual(en["entries"], ["Hotel for the Fall Assembly", "Big Book", "Stamps"])
        self.assertEqual(en["photos"], sorted([hotel, book]))
        self.assertEqual(en["same"], en["want"])                           # each photo, byte for byte, at its own entry
        self.assertEqual(en["meta"], [1200, "IMG_1.jpg", "image/jpeg"])
        self.assertEqual(en["done"], [2, 0])
        self.assertEqual(r["es"]["preview"], en["preview"])

    def test_the_preview_says_one_entry_and_one_photo(self):
        # the restore preview counts with the tracker's singular/plural keys: "1 entry, 1 receipt photo", not
        # "1 entries, 1 photos" — and a backup without photos says so
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const photos = new Map(), w = make(lang, null, null, { photos });
            add(w, "expense", { description: "Big Book", amount: "12", receipt: "photo", date: "2026-09-27" }, "books");
            const [book] = w.a.E();
            photos.set(book.id, { id: book.id, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 9])], { type: "image/jpeg" }) });
            await w.a.exportBackup();
            const d = w.downloads.at(-1), w2 = make(lang, null, null, { photos: new Map() });
            await w2.a.impFile(fileOf(d.name, w.blob(d)));
            res[lang] = { one: [w2.a.imp.step, w2.a.backupCounts(w2.a.imp.counts)],
                          many: w2.a.backupCounts({ entries: 12, photos: 3 }), none: w2.a.backupCounts({ entries: 2, photos: 0 }) };
          }
          out(res);""")
        self.assertEqual(r["en"], {"one": ["backup", "1 entry, 1 receipt photo"], "many": "12 entries, 3 receipt photos",
                                   "none": "2 entries, no receipt photos"})
        self.assertEqual(r["es"], {"one": ["backup", "1 registro, 1 foto de comprobante"],
                                   "many": "12 registros, 3 fotos de comprobantes", "none": "2 registros, sin fotos de comprobantes"})
        page = (ROOT / "src" / "pages" / "tracker.njk").read_text(encoding="utf-8")
        self.assertIn('x-text="backupCounts(imp.counts)"', page)

    def test_the_size_without_photos_and_a_big_one(self):
        r = app(self, r"""
          const photos = new Map(), w = make("en", null, null, { photos });
          add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
          add(w, "expense", { description: "Books", amount: "12", receipt: "photo" }, "books");
          const [a, b] = w.a.E();
          const mb = (n) => new Blob([new Uint8Array(n * 1048576)], { type: "image/jpeg" });
          photos.set(a.id, { id: a.id, type: "image/jpeg", blob: mb(1) });
          photos.set(b.id, { id: b.id, type: "image/jpeg", blob: mb(2) });
          const bk = JSON.parse(JSON.stringify(await w.a.measureBackup()));
          const line = w.a.bkLine(), bigNow = w.a.bkBig();
          // without photos: the ledger alone (.json); restored here with "Replace", this device keeps the photos its entries point to
          await w.a.exportBackup("plain");
          const plain = w.downloads.at(-1), plainText = await w.text(plain);
          await w.a.impFile(fileOf(plain.name, plainText));
          w.a.imp.mode = "replace";
          await w.a.impApply();
          const kept = [...photos.keys()].sort();
          // 19 MB more of photos: too big for e-mail — asked first (save it anyway, without photos, or not now)
          photos.set(b.id, { id: b.id, type: "image/jpeg", blob: mb(19) });
          w.a.$refs.ask = { open: false, showModal() { this.open = true; }, close() { this.open = false; }, querySelector: () => null };
          const n0 = w.downloads.length;
          const p1 = w.a.exportBackup(); await tick();
          const asked = [w.a.ask.msg, w.a.ask.ok, w.a.ask.alt];
          w.a.askDone("alt"); await p1;
          const alt = w.downloads.slice(n0).map((d) => d.name);
          const p2 = w.a.exportBackup(); await tick(); w.a.askDone(true); await p2;
          const full = w.downloads.at(-1), n3 = w.downloads.length;
          const p3 = w.a.exportBackup(); await tick(); w.a.askDone(false); await p3;
          out({ bk, line, bigNow, plain: plain.name, plainReceipts: JSON.parse(plainText).receipts, kept, ids: [a.id, b.id].sort(), asked, alt,
                full: [full.name, w.blob(full).size], cancel: w.downloads.length - n3, bigAfter: w.a.bkBig() });""")
        self.assertEqual(r["bk"]["photos"], 2)
        self.assertTrue(3 * 1048576 < r["bk"]["bytes"] < 3 * 1048576 + 50000, r["bk"])
        self.assertLess(r["bk"]["plain"], 50000)
        self.assertRegex(r["line"], r"^Full backup: about 3 MB, 2 receipt photos\. Without photos: about \d+ KB\.$")
        self.assertFalse(r["bigNow"])
        self.assertRegex(r["plain"], r"^service-expenses-backup-no-photos-\d{4}-\d{2}-\d{2}\.json$")
        self.assertEqual(r["plainReceipts"], [])
        self.assertEqual(r["kept"], r["ids"])
        self.assertIn("about 20 MB (2 receipt photos): too big to send by e-mail", r["asked"][0])
        self.assertEqual(r["asked"][1:], ["Save the full backup", "Without photos"])
        self.assertEqual(len(r["alt"]), 1)
        self.assertRegex(r["alt"][0], r"-backup-no-photos-[\d-]+\.json$")
        self.assertRegex(r["full"][0], r"-backup-[\d-]+\.zip$")
        self.assertGreater(r["full"][1], 20 * 1048576)
        self.assertEqual(r["cancel"], 0)
        self.assertTrue(r["bigAfter"])

    def test_an_unpacked_backup_and_a_v1_backup(self):
        r = app(self, r"""
          const photos = new Map(), w = make("en", null, null, { photos });
          add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
          add(w, "expense", { description: "Books", amount: "12", receipt: "photo" }, "books");
          for (const e of w.a.E()) photos.set(e.id, { id: e.id, type: "image/jpeg", blob: new Blob([e.id], { type: "image/jpeg" }) });
          await w.a.exportBackup();
          const ar = await w.F.readZip(w.blob(w.downloads.at(-1)));
          const parts = await Promise.all(ar.entries.map(async (e) => fileOf(e.name, await ar.blob(e.name, "image/jpeg"))));
          // a computer unpacked it: its backup.json alone says the photos are not with it …
          const p2 = new Map(), w2 = make("en", null, null, { photos: p2 });
          await w2.a.impFile(parts[0]);
          const alone = [w2.a.imp.step, w2.a.imp.counts.photos, w2.a.imp.counts.missing, w2.a.t("imp.photos_missing", { n: "2" })];
          // … picked together with them (in any order), it restores them too
          await w2.a.impFiles(parts.slice().reverse());
          const together = JSON.parse(JSON.stringify(w2.a.imp.counts));
          await w2.a.impApply();
          const restored = await Promise.all([...p2.values()].map(async (x) => (await x.blob.text()) === x.id));
          // the backup the tracker made before 1.2.0 (tests/fixtures/expenses: its photo inside, as a data: URL — the
          // entry it belongs to marked "photo" here, so it is one to restore)
          const old = JSON.parse(input.v1);
          old.entries.find((e) => e.id === "x0n").receipt = "photo";
          const p3 = new Map(), w3 = make("en", null, null, { photos: p3 });
          await w3.a.impFile(fileOf("service-expenses-backup-2026-09-27.json", JSON.stringify(old)));
          const v1 = [w3.a.imp.step, JSON.parse(JSON.stringify(w3.a.imp.counts))];
          await w3.a.impApply();
          out({ alone, together, restored, v1, v1after: [w3.a.E().length, [...p3.keys()], p3.size && p3.values().next().value.blob.type] });""",
                data={"v1": (ROOT / "tests" / "fixtures" / "expenses" / "v1-backup.json").read_text(encoding="utf-8")})
        self.assertEqual(r["alone"][:3], ["backup", 0, 2])
        self.assertIn("choose its backup.json together with all its photos", r["alone"][3])
        self.assertEqual(r["together"], {"entries": 2, "photos": 2, "missing": 0})
        self.assertEqual(r["restored"], [True, True])
        self.assertEqual(r["v1"], ["backup", {"entries": 45, "photos": 1, "missing": 0}])
        self.assertEqual(r["v1after"], [45, ["x0n"], "image/jpeg"])

    def test_an_unpacked_backup_zipped_again_and_photos_alone(self):
        r = app(self, r"""
          const photos = new Map(), w = make("en", null, null, { photos });
          add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
          const e = w.a.E()[0];
          photos.set(e.id, { id: e.id, type: "image/jpeg", blob: new Blob([e.id], { type: "image/jpeg" }) });
          await w.a.exportBackup();
          const d = w.downloads.at(-1), ar = await w.F.readZip(w.blob(d));
          // unpacked into its folder, then the folder zipped again (a Mac adds its __MACOSX copies)
          const dir = d.name.replace(/\.zip$/, "") + "/";
          const again = await w.F.zip([{ name: "__MACOSX/" + dir + "._backup.json", data: "not json" }]
            .concat(await Promise.all(ar.entries.map(async (x) => ({ name: dir + x.name, data: await ar.bytes(x.name) })))));
          const p2 = new Map(), w2 = make("en", null, null, { photos: p2 });
          await w2.a.impFile(fileOf("again.zip", again));
          const preview = [w2.a.imp.step, w2.a.imp.err, JSON.parse(JSON.stringify(w2.a.imp.counts || null))];
          await w2.a.impApply();
          const restored = [[...p2.keys()], p2.size && await p2.get(e.id).blob.text(), w2.a.E().map((x) => x.description)];
          // photos picked without their backup.json: nothing to import, and the message says what to choose
          const w3 = make("en");
          await w3.a.impFiles([fileOf("IMG_0001.jpg", "jpeg", "image/jpeg"), fileOf("IMG_0002.JPG", "jpeg", "image/jpeg")]);
          out({ preview, restored, id: e.id, alone: [w3.a.imp.step, w3.a.imp.err, w3.a.t("imp.photos_alone"), w3.a.E().length] });""")
        self.assertEqual(r["preview"], ["backup", "", {"entries": 1, "photos": 1, "missing": 0}])
        self.assertEqual(r["restored"], [[r["id"]], r["id"], ["Hotel"]])
        self.assertEqual(r["alone"][0], "pick")
        self.assertEqual(r["alone"][1], r["alone"][2])
        self.assertIn("backup.json", r["alone"][1])
        self.assertEqual(r["alone"][3], 0)

    def test_a_photo_this_browser_cannot_read_is_left_out_and_named(self):
        # One stored photo whose file the browser lost (Chrome's NotReadableError): the full backup is made with the
        # others and names the one left out; it restores elsewhere. Every later backup works the same way. The photo
        # store failing as a whole names every photo. A backup that fails all the same points to "Back up without
        # photos" (or says its own reason), never to a CSV.
        r = app(self, r"""
          const res = {}, now = Date.parse("2026-10-06T15:00:00Z");
          for (const lang of ["en", "es"]) {
            const photos = new Map(), w = make(lang, null, null, { photos, now });
            add(w, "expense", { description: "Hotel for the Fall Assembly", amount: "90", receipt: "photo", date: "2026-09-26" }, "lodging");
            add(w, "expense", { description: "Big Book", amount: "12", receipt: "photo", date: "2026-09-27" }, "books");
            add(w, "expense", { description: "Copies", amount: "3", receipt: "photo", date: "2026-09-28" }, "printing");
            const [hotel, book, copies] = w.a.E();
            const jpeg = (id, b) => ({ id, type: "image/jpeg", blob: new Blob([new Uint8Array(b)], { type: "image/jpeg" }) });
            photos.set(hotel.id, jpeg(hotel.id, [0xff, 0xd8, 1]));
            photos.set(book.id, jpeg(book.id, [0xff, 0xd8, 2]));
            photos.get(book.id).blob.arrayBuffer = () => Promise.reject(Object.assign(new Error("A requested file or directory could not be found"), { name: "NotReadableError" }));
            photos.set(copies.id, jpeg(copies.id, [0xff, 0xd8, 3]));
            const runs = [];
            for (let i = 0; i < 2; i++) {
              const n0 = w.downloads.length;
              await w.a.exportBackup();
              const d = w.downloads.at(-1), ar = await w.F.readZip(w.blob(d));
              runs.push({ made: w.downloads.length - n0, files: ar.entries.length, receipts: JSON.parse(await ar.text("backup.json")).receipts.map((x) => x.id), toast: w.a.toastMsg });
            }
            const d = w.downloads.at(-1);
            // another device restores it: the two photos it has, and every entry
            const p2 = new Map(), w2 = make(lang, null, null, { photos: p2 });
            await w2.a.impFile(fileOf(d.name, w.blob(d)));
            const preview = JSON.parse(JSON.stringify(w2.a.imp.counts));
            await w2.a.impApply();
            // the photo store fails as a whole (no IndexedDB): each photo is named, none is said to be in it
            const w3 = make(lang, Object.fromEntries(w.store), null, { now });
            await w3.a.exportBackup();
            const zipped = (await w3.F.readZip(w3.blob(w3.downloads.at(-1)))).entries.map((e) => e.name);
            res[lang] = { ids: [hotel.id, book.id, copies.id], runs, left: JSON.parse(JSON.stringify(w.a.bkLeft)), bookName: w.a.entryName(book.id),
                          lastBackup: !!state(w).meta.lastBackup, preview, restored: [...p2.keys()].sort(), entries: w2.a.E().length,
                          whole: [w3.downloads.length, zipped, w3.a.toastMsg, w3.a.bkLeft.map((x) => x.text), [hotel, book, copies].map((e) => w3.a.entryName(e.id))],
                          failed: w.a.t("toast.backup_failed"), tooBig: w.a.t("err.backup_too_big") };
            // a backup that fails all the same: its own reason when it has one, else the backup without photos
            const zip = w.F.zip;
            w.F.zip = () => Promise.reject(Object.assign(new Error("big"), { key: "expenses.err.backup_too_big" }));
            await w.a.exportBackup(); res[lang].saidBig = w.a.toastMsg;
            w.F.zip = () => Promise.reject(new Error("disk"));
            await w.a.exportBackup(); res[lang].saidFailed = w.a.toastMsg;
            w.F.zip = zip;
          }
          out(res);""")
        for lang, x in r.items():
            with self.subTest(lang=lang):
                hotel, book, copies = x["ids"]
                for run in x["runs"]:                                          # the first backup, and every one after it
                    self.assertEqual(run["made"], 1)
                    self.assertEqual(run["files"], 3)                         # backup.json and the two photos it can read
                    self.assertEqual(run["receipts"], [hotel, copies])        # (never one that is not in the .zip)
                    self.assertIn(x["bookName"], run["toast"])
                self.assertEqual(x["left"], [{"id": book, "text": x["bookName"]}])
                self.assertTrue(x["lastBackup"])
                self.assertEqual(x["preview"], {"entries": 3, "photos": 2, "missing": 0})
                self.assertEqual(x["restored"], sorted([hotel, copies]))
                self.assertEqual(x["entries"], 3)
                made, zipped, toast, named, names = x["whole"]
                self.assertEqual((made, zipped, named), (1, ["backup.json"], names))
                for n in names:
                    self.assertIn(n, toast)
                self.assertEqual(x["saidBig"], x["tooBig"])
                self.assertEqual(x["saidFailed"], x["failed"])
                self.assertNotIn("CSV", x["failed"])
        self.assertRegex(r["en"]["runs"][0]["toast"],
                         r"^Downloaded service-expenses-backup-2026-10-06\.zip · \d+ KB — without 1 receipt photo this browser couldn't read: Big Book · Sep 27\.$")
        self.assertIn("— sin 1 foto de comprobante que este navegador no pudo leer: Big Book", r["es"]["runs"][0]["toast"])
        self.assertIn("without 3 receipt photos this browser couldn't read", r["en"]["whole"][2])
        self.assertIn("Back up without photos", r["en"]["failed"])
        self.assertIn("Respalda sin fotos", r["es"]["failed"])
        page = (ROOT / "src" / "pages" / "tracker.njk").read_text(encoding="utf-8")
        self.assertIn('x-for="x in bkLeft"', page)                           # listed under the backup buttons too

    def test_photos_that_fail_to_restore_are_said(self):
        # A restored .zip with a photo damaged on the way: "Done: 2 entries imported" is read out at once; the photo
        # that could not be restored is said too, once, when the photos are done (the toast, a live region) — beside
        # an "Undo" on screen (kept) through the page's own live region (GV.announce)
        r = app(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const photos = new Map(), w = make(lang, null, null, { photos });
            add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
            add(w, "expense", { description: "Books", amount: "12", receipt: "photo" }, "books");
            const [a, b] = w.a.E();
            photos.set(a.id, { id: a.id, type: "image/jpeg", blob: new Blob(["PHOTO-A-1234"], { type: "image/jpeg" }) });
            photos.set(b.id, { id: b.id, type: "image/jpeg", blob: new Blob(["PHOTO-B-5678"], { type: "image/jpeg" }) });
            await w.a.exportBackup();
            const bytes = new Uint8Array(await w.blob(w.downloads.at(-1)).arrayBuffer());
            bytes[Buffer.from(bytes).indexOf("PHOTO-B-5678")] = 0x51;           // its bytes no longer match their CRC
            const said = [], w2 = make(lang, null, null, { photos: new Map() });
            w2.ctx.GV.announce = (m) => said.push(m);
            await w2.a.impFile(fileOf("backup.zip", bytes));
            await w2.a.impApply(); await tick();
            const said3 = [], w3 = make(lang, null, null, { photos: new Map() });
            w3.ctx.GV.announce = (m) => said3.push(m);
            await w3.a.impFile(fileOf("backup.zip", bytes));
            const p = w3.a.impApply();
            w3.a.say(w3.a.plural(1, "toast.deleted_one", "toast.deleted"), true);   // an entry deleted meanwhile: "Undo" on screen
            await p; await tick();
            res[lang] = { done: [w2.a.imp.photosDone, w2.a.imp.photoErrs], toast: w2.a.toastMsg, said,
                          beside: [w3.a.toastMsg, w3.a.toastUndo, said3], want: w2.a.t("imp.photos_failed", { n: "1" }), deleted: w3.a.plural(1, "toast.deleted_one", "toast.deleted") };
          }
          out(res);""")
        for lang, x in r.items():
            with self.subTest(lang=lang):
                self.assertEqual(x["done"], [1, 1])
                self.assertEqual(x["toast"], x["want"])
                self.assertEqual(x["said"], [])                               # (the toast says it: not twice)
                self.assertEqual(x["beside"], [x["deleted"], True, [x["want"]]])
        self.assertEqual(r["en"]["want"], "Receipt photos that couldn't be restored: 1.")
        self.assertEqual(r["es"]["want"], "Fotos de comprobantes que no se pudieron restaurar: 1.")


class ImportFiles(unittest.TestCase):
    """F-8 / P8-4: a UTF-16 CSV reads as its UTF-8 twin; an Excel workbook (.xlsx) imports — its first sheet, dates
    by their format — through the same preview; what this browser can't read says why."""

    def test_utf16_csv(self):
        r = app(self, r"""
          const text = "Date,Description,Amount\r\n09/27/2026,Café con leche,4.50\r\n09/28/2026,Año nuevo,12\r\n";
          const le = Buffer.from(text, "utf16le"), variants = { utf8: Buffer.from(text, "utf8"), le_bom: Buffer.concat([Buffer.from([0xff, 0xfe]), le]),
            be_bom: Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from(le).swap16()]), le_bare: le };
          const res = {};
          for (const [k, b] of Object.entries(variants)) {
            const w = make("en");
            await w.a.impFile(fileOf("bank-" + k + ".csv", new Uint8Array(b)));
            if (w.a.imp.step === "map") w.a.impUseMap();          // (the columns guessed from the headers)
            res[k] = [w.a.imp.step, w.a.imp.err, (w.a.imp.sampleRows || []).map((x) => [x.desc, x.amount])];
          }
          // our own export, saved by a spreadsheet as "Unicode text" (UTF-16, tabs): read as ours
          const w = make("es");
          add(w, "expense", { description: "Libros de La Viña", amount: "36" }, "books");
          const tab = w.G.toCSV(w.a.E(), w.a.st(), { lang: "es" }).replace(/^﻿/, "").replace(/,/g, "\t");
          const w2 = make("es");
          await w2.a.impFile(fileOf("registro.txt", new Uint8Array(Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(tab, "utf16le")]))));
          out({ res, ours: [w2.a.imp.step, w2.a.imp.ours, w2.a.imp.counts && w2.a.imp.counts.add, w2.a.imp.sampleRows && w2.a.imp.sampleRows[0].desc] });""")
        want = ["preview", "", [["Café con leche", "$4.50"], ["Año nuevo", "$12.00"]]]
        for k, v in r["res"].items():
            self.assertEqual(v, want, k)
        self.assertEqual(r["ours"], ["preview", True, 1, "Libros de La Viña"])

    def test_an_excel_workbook(self):
        from test_expenses_files import NS, workbook, serial  # the workbook builder (Excel's own layout)
        sheet = (f'<worksheet {NS}><sheetData>'
                 '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
                 '<row r="2"><c r="A2" s="1"><v>46292</v></c><c r="B2" t="s"><v>4</v></c><c r="C2"><v>120.5</v></c></row>'
                 '<row r="3"><c r="A3" s="2"><v>46293</v></c><c r="B3" t="inlineStr"><is><t>Café</t></is></c><c r="C3"><v>12.339999999999998</v></c></row>'
                 '</sheetData></worksheet>')
        ours = (f'<worksheet {NS}><sheetData><row r="1">' + "".join(f'<c r="{c}1" t="inlineStr"><is><t>{h}</t></is></c>' for c, h in zip("ABCD", ["date", "type", "amount", "description"]))
                + '</row><row r="2"><c r="A2" s="1"><v>46295</v></c><c r="B2" t="inlineStr"><is><t>mileage</t></is></c><c r="C2"><v>0</v></c>'
                '<c r="D2" t="inlineStr"><is><t>To the assembly</t></is></c></row></sheetData></worksheet>')
        import base64
        r = app(self, r"""
          const bytes = (b64) => new Uint8Array(Buffer.from(b64, "base64"));
          const w = make("en");
          await w.a.impFile(fileOf("Expenses.xlsx", bytes(input.wb)));
          const map = [w.a.imp.step, w.a.imp.from, w.a.imp.headers.map((h) => h.name), JSON.parse(JSON.stringify(w.a.imp.map))];
          w.a.impUseMap();
          await w.a.impApply();
          const w2 = make("en");
          await w2.a.impFile(fileOf("mine.xlsx", bytes(input.ours)));
          out({ map, entries: w.a.E().map((e) => [e.date, e.description, e.amount_cents]), ours: [w2.a.imp.step, w2.a.imp.ours, w2.a.imp.counts.add] });""",
                data={"wb": base64.b64encode(workbook(sheet2=sheet)).decode(), "ours": base64.b64encode(workbook(sheet2=ours)).decode()})
        day = lambda n: serial(n).strftime("%Y-%m-%d")  # noqa: E731
        self.assertEqual(r["map"], ["map", "xlsx", ["Date", "Description", "Amount"], {"date": "0", "description": "1", "amount": "2", "category": "", "miles": "", "notes": ""}])
        self.assertEqual(r["entries"], [[day(46292), "Hotel & parking", 12050], [day(46293), "Café", 1234]])
        self.assertEqual(r["ours"], ["preview", True, 1])

    def test_what_this_browser_cannot_read_says_why(self):
        from test_expenses_files import workbook, a_zip
        import base64
        import zipfile
        r = app(self, r"""
          const bytes = (b64) => new Uint8Array(Buffer.from(b64, "base64"));
          const err = async (w, f) => { await w.a.impFile(f); return w.a.imp.err; };
          const w = make("en"), old = make("en", null, null, { noInflate: true });
          out([await err(w, fileOf("old.xls", new Uint8Array([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1, 0, 0]))),
               await err(old, fileOf("Expenses.xlsx", bytes(input.wb))), await err(w, fileOf("photos.zip", bytes(input.other))),
               await err(w, fileOf("backup.zip", bytes(input.wb).slice(0, 200))),
               [w.a.t("err.xls_old"), w.a.t("err.xlsx_browser"), w.a.t("err.backup_foreign"), w.a.t("err.zip_damaged")]]);""",
                data={"wb": base64.b64encode(workbook()).decode(), "other": base64.b64encode(a_zip([("cat.jpg", b"\xff\xd8", zipfile.ZIP_STORED)])).decode()})
        self.assertEqual(r[:4], r[4])
        self.assertIn("(.xls)", r[0])


class EditKeepsWhatTheFormDoesNotShow(unittest.TestCase):
    """P1-3: an edit starts from the entry: an imported entry's fields its form doesn't show (a trip's nights,
    quantity, item, attendees) survive a description fix, and a move to another category with the same form; a
    category with another form drops what it has no place for, as a new entry would; a pay-back mark stays only
    while the request it settled stays as it was."""

    def test_an_imported_travel_entry(self):
        r = app(self, r"""
          const w = make("en");
          const csv = "id,date,type,category,description,amount,funder,claim_status,nights,quantity,item,attendees,end_date,vendor,role,activity,miles,rate,from,to,trips\n" +
            "t1,2026-09-20,expense,travel,Bus to the Assembly,45.00,district,to_request,2,3,Bus pass,4,2026-09-22,Greyhound,Driver,assembly,,,,,\n" +
            "t2,2026-09-21,mileage,mileage,To Tyler,,district,to_request,,5,Gas card,,,Shell,Driver,assembly,50,0.14,Home,Tyler,2\n";
          await w.a.impFile(fileOf("trips.csv", csv)); await w.a.impApply();
          const pick = (id) => { const e = w.a.E().find((x) => x.id === id);
            return [e.description, e.nights, e.quantity, e.item, e.attendees, e.end_date, e.vendor, e.role, e.activity, e.amount_cents, e.funder, e.claim_status, e.miles, e.trips]; };
          const before = [pick("t1"), pick("t2")];
          w.a.openEdit("t1"); w.a.form.description = "Bus to the Fall Assembly"; w.a.saveForm(false);
          w.a.openEdit("t2"); w.a.form.description = "To Tyler and back"; w.a.saveForm(false);
          const after = [pick("t1"), pick("t2"), w.a.formErrs.length];
          // a new category (another form): what it has no place for goes, as on a new entry
          w.a.openEdit("t1"); w.a.form.category = "other"; w.a.onCat(); w.a.saveForm(false);
          const moved = pick("t1");
          // literature bought to give away, moved to Meals: no longer stock to give away
          add(w, "expense", { description: "GV issues", item: "Grapevine", format: "gv", quantity: "20", unit_cost: "2.50" }, "giveaways");
          const g = w.a.E().at(-1);
          w.a.openEdit(g.id); w.a.form.category = "meals"; w.a.onCat(); w.a.form.amount = "50"; w.a.saveForm(false);
          const meal = w.a.E().find((e) => e.id === g.id);
          out({ before, after, moved, meal: [g.giveaway, meal.giveaway, meal.item, meal.quantity, meal.amount_cents, w.a.inv().length] });""")
        t1 = ["Bus to the Assembly", 2, 3, "Bus pass", 4, "2026-09-22", "Greyhound", "Driver", "assembly", 4500, "district", "to_request", "", ""]
        t2 = ["To Tyler", "", 5, "Gas card", "", "", "Shell", "Driver", "assembly", 700, "district", "to_request", 50, 2]
        self.assertEqual(r["before"], [t1, t2])
        self.assertEqual(r["after"], [["Bus to the Fall Assembly"] + t1[1:], ["To Tyler and back"] + t2[1:], 0])   # nothing lost, nothing moved
        self.assertEqual(r["moved"], ["Bus to the Fall Assembly", "", "", "", "", "", "Greyhound", "", "assembly", 4500, "district", "to_request", "", ""])
        self.assertEqual(r["meal"], [True, False, "", "", 5000, 0])

    def test_the_same_form_in_another_category_and_a_pay_back(self):
        r = app(self, r"""
          const w = make("en");
          const csv = "id,date,type,category,description,amount,funder,claim_status,quantity,item,attendees,giveaway\n" +
            "o1,2026-09-20,expense,other,Coffee for the workshop,45.00,district,to_request,3,Coffee,12,yes\n";
          await w.a.impFile(fileOf("bank.csv", csv)); await w.a.impApply();
          const pick = (id, ks) => { const e = w.a.E().find((x) => x.id === id); return ks.map((k) => e[k]); };
          const K = ["category", "quantity", "item", "attendees", "giveaway"];
          const imported = pick("o1", K);
          w.a.openEdit("o1"); w.a.form.description = "Coffee for the fall workshop"; w.a.saveForm(false);
          const typo = pick("o1", K);
          // "Other" → "Supplies": the same form (general) — what it doesn't show stays; the hidden "to give away"
          // mark was the old category's
          w.a.openEdit("o1"); w.a.form.category = "supplies"; w.a.onCat(); w.a.saveForm(false);
          const moved = pick("o1", K);
          // a book bought for Pat, settled when Pat paid it back …
          add(w, "expense", { description: "Big Book for Pat", amount: "20" }, "books");
          const pat = w.a.ensurePerson("Pat"), b = w.a.E().at(-1).id;
          w.a.openEdit(b); w.a.form.funder = pat; w.a.onFunder(); w.a.saveForm(false);
          add(w, "received", { description: "Pat paid me back", amount: "20", funder: pat }, "repayment");
          const R = ["repaid", "claim_status"], settled = pick(b, R);
          w.a.openEdit(b); w.a.form.description = "Big Book for Pat K."; w.a.saveForm(false);
          const fixed = pick(b, R);
          // … and its request set back to "Submitted": owed again, not still marked paid back
          w.a.openEdit(b); w.a.form.claim_status = "submitted"; w.a.saveForm(false);
          out({ imported, typo, moved, settled, fixed, reopened: pick(b, R) });""")
        self.assertEqual(r["imported"], ["other", 3, "Coffee", 12, True])
        self.assertEqual(r["typo"], r["imported"])
        self.assertEqual(r["moved"], ["supplies", 3, "Coffee", 12, False])
        self.assertEqual(r["settled"], ["repaid", "paid"])
        self.assertEqual(r["fixed"], ["repaid", "paid"])
        self.assertEqual(r["reopened"], ["owed", "submitted"])


class OwedAtThePeriodsEnd(unittest.TestCase):
    """P1-4: "Who owes you" is the balance at the period's end: a hotel claimed in December and paid back in
    January is even in January's view (not "you hold $300 of theirs"); the period's lists stay the period's."""

    def test_a_december_claim_and_a_january_check(self):
        r = app(self, r"""
          const w = make("en", null, null, { now: Date.UTC(2027, 0, 20, 18) });
          add(w, "expense", { description: "Hotel for the Winter Assembly", amount: "300", funder: "district", claim_status: "submitted", date: "2026-12-10" }, "lodging");
          add(w, "received", { description: "District check", amount: "300", funder: "district", date: "2027-01-15" }, "reimbursement");
          const view = (p) => { w.a.setPeriod(p); return [w.a.balances().map((b) => [b.name, b.balanceText, b.received]), w.a.stats().find((s) => s.id === "owed").value, w.a.filtered().length]; };
          out({ year: view("this_year"), month: view("this_month"), last: view("last_year"), all: view("all") });""")
        self.assertEqual(r["year"], [[["My district", "Even", "$300.00"]], "$0.00", 1])
        self.assertEqual(r["month"], r["year"])
        self.assertEqual(r["last"], [[["My district", "Owes you $300.00", "$0.00"]], "$300.00", 1])   # at the end of 2026 it was still owed
        self.assertEqual(r["all"], [[["My district", "Even", "$300.00"]], "$0.00", 2])


class ServicePanelsInTheFilters(unittest.TestCase):
    """P1-11 / F-17: the period filters offer the current panel by Area 65's rule — no settings needed — and
    the panels config/expenses.yml lists."""

    def test_on_fixed_days(self):
        r = app(self, r"""
          const at = (iso) => make("en", null, null, { now: Date.parse(iso + "T17:00:00Z") });
          const panels = (w) => w.a.periods().filter((p) => p.id.startsWith("panel:")).map((p) => [p.id, p.label]);
          const oct26 = at("2026-10-06"), jan27 = at("2027-01-15"), jan29 = at("2029-01-10"), bare = at("2026-10-06");
          add(jan29, "expense", { description: "Old", amount: "1", date: "2024-03-01" }, "books");
          bare.a.st().panels = []; bare.a.rev++;                                  // no panel listed at all: the rule alone
          oct26.a.setPeriod("panel:75");
          out({ oct26: panels(oct26), jan27: panels(jan27), jan29: panels(jan29), bare: panels(bare), range: oct26.a.range(),
                rule: jan29.a.range("panel:81"), report: oct26.a.rpPeriods().filter((p) => p.id.startsWith("panel:")).map((p) => p.id) });""")
        self.assertEqual(r["oct26"], [["panel:77", "Panel 77"], ["panel:75", "Panel 75"]])
        self.assertEqual(r["jan27"], [["panel:77", "Panel 77"], ["panel:75", "Panel 75"]])
        self.assertEqual(r["jan29"], [["panel:79", "Panel 79"], ["panel:77", "Panel 77"], ["panel:75", "Panel 75"], ["panel:73", "Panel 73"]])
        self.assertEqual(r["bare"], [["panel:75", "Panel 75"]])                   # October 2026: the current term, by the rule
        self.assertEqual(r["range"], {"from": "2025-01-01", "to": "2026-12-31"})
        self.assertEqual(r["rule"], {"from": "2031-01-01", "to": "2032-12-31"})
        self.assertEqual(r["report"], ["panel:77", "panel:75"])


class Speed(unittest.TestCase):
    """P5-4: the Requests view and the service report make their number and date formatters once — not one per
    cell (two years of entries: a purchase a day, a trip every other day, all asked of the district)."""

    def test_formatters_are_made_once(self):
        r = app(self, r"""
          let made = 0;
          const intl = new Proxy(Intl, { get(t, k) { const v = t[k];
            return k === "NumberFormat" || k === "DateTimeFormat" ? new Proxy(v, { construct(T, a) { made++; return new T(...a); } }) : v; } });
          const w = make("en", null, null, { intl });
          // app.js's GV.fmtDate makes a formatter per call: the tracker no longer goes through it for its dates
          w.ctx.GV.fmtDate = (d, o) => new w.ctx.Intl.DateTimeFormat("en-US", Object.assign({ timeZone: "America/Chicago" }, o)).format(new Date(d));
          const G = w.G, st = w.a.st(), E = [];
          for (let day = 0; day < 730; day++) {
            const date = G.addDays("2024-10-01", day);
            E.push(G.normalizeEntry({ id: "e" + E.length, type: "expense", date, category: day % 3 ? "books" : "meals", description: "Purchase " + day,
              amount_cents: 1000 + day, funder: "district", claim_status: "to_request" }, st).entry);
            if (day % 2 === 0) E.push(G.normalizeEntry({ id: "e" + E.length, type: "mileage", date, from: "Home", to: "Place " + day, miles: 20, rate: "0.14",
              funder: "district", claim_status: "to_request", activity: "district" }, st).entry);
          }
          w.store.set(KEY, JSON.stringify({ v: 1, entries: E, settings: st, meta: {} }));
          w.a.loadState();
          w.a.rq.funder = "district"; w.a.rq.period = "all"; w.a.rp.period = "all";
          const before = made;
          for (let i = 0; i < 3; i++) { w.a.rev++; w.a.rqLines(); w.a.rqMileage(); w.a.rqTotals(); w.a.rpView(); w.a.byMonth(); }
          out({ made: made - before, lines: [w.a.rqLines().length, w.a.rqMileage().length], sample: [w.a.rqLines()[0].date, w.a.rpView().miles[0].lines[0].dates] });""")
        self.assertEqual(r["lines"], [730, 365])
        self.assertLessEqual(r["made"], 8)                                      # was one per cell: thousands
        self.assertEqual(r["sample"], ["Oct 1, 2024", "Oct 1, 2024"])


class StoredDataSafety(unittest.TestCase):
    """P8-4: a stored ledger this page can't read is never written over (set aside, said, offered as a file, with
    the receipt photos it names); a newer page's ledger is shown, not saved over; closing the tab asks only while
    something is unsaved — the form, or changes the browser did not keep; a receipt photo is never deleted while
    another tab can still undo its delete, has its entry back, or has it open in its form."""

    def test_an_unreadable_ledger(self):
        r = app(self, r"""
          const bad = '{"v":1,"entries":[{"id":"a1","type":"expense","date":"2026-09-01","descr';          // cut off
          const aside = (w) => [...w.store.entries()].filter(([k, v]) => k.startsWith(KEY + ":unreadable-") && v === bad).length;
          const w = make("en", { [KEY]: bad });
          const first = [w.a.damaged, w.a.lock, w.store.get(KEY) === bad, aside(w)];
          add(w, "expense", { description: "New", amount: "5" }, "books");          // the tracker works on; the copy stays aside
          const after = [state(w).entries.map((e) => e.description), aside(w)];
          const w2 = make("en", Object.fromEntries(w.store));                       // the next visit: still said, not copied twice
          await w2.a.damagedDownload();
          const d = w2.downloads.at(-1), dl = [w2.a.damaged, d.name, (await w2.text(d)) === bad];
          w2.a.damagedRemove(); await tick();
          const gone = [w2.a.damaged, aside(w2), state(w2).entries.length];
          // no room to set it aside: it stays where it is, and nothing is saved over it until it is taken away
          const w3 = make("en", { [KEY]: bad }, null, { full: true });
          w3.setFull(false);
          const locked = [w3.a.lock, w3.a.damaged];
          const r3 = add(w3, "expense", { description: "Typed", amount: "1" }, "books");
          const kept = [w3.store.get(KEY) === bad, r3.toast === w3.a.t("toast.not_saved")];
          await w3.a.damagedDownload();
          const dl3 = (await w3.text(w3.downloads.at(-1))) === bad;
          w3.a.damagedRemove(); await tick();
          const freed = [w3.a.lock, state(w3).entries.map((e) => e.description)];
          // a ledger a newer version of the page saved: shown as far as it can be, never saved over
          const newer = JSON.stringify({ v: 2, entries: [{ id: "n1", type: "expense", date: "2026-09-01", category: "books", description: "From a newer page", amount_cents: 100, later_field: 1 }], settings: {}, meta: {} });
          const w4 = make("en", { [KEY]: newer });
          const r4 = add(w4, "expense", { description: "Here", amount: "1" }, "books");
          out({ first, after, dl, gone, locked, kept, dl3, freed,
                newer: [w4.a.lock, w4.a.damaged, w4.a.E().map((e) => e.description), w4.store.get(KEY) === newer, r4.toast === w4.a.t("toast.not_saved")] });""")
        self.assertEqual(r["first"], [1, "", True, 1])
        self.assertEqual(r["after"], [["New"], 1])
        self.assertEqual(r["dl"][0], 1)
        self.assertRegex(r["dl"][1], r"^service-expenses-unreadable-\d{4}-\d{2}-\d{2}\.json$")
        self.assertTrue(r["dl"][2])
        self.assertEqual(r["gone"], [0, 0, 1])
        self.assertEqual(r["locked"], ["unreadable", 1])
        self.assertEqual(r["kept"], [True, True])
        self.assertTrue(r["dl3"])
        self.assertEqual(r["freed"], ["", ["Typed"]])
        self.assertEqual(r["newer"], ["newer", 0, ["From a newer page", "Here"], True, True])

    def test_the_photos_of_a_ledger_set_aside_stay_until_it_is_removed(self):
        r = app(self, r"""
          const photos = new Map(), jpeg = (id) => ({ id, type: "image/jpeg", blob: new Blob([id]) });
          const bad = '{"v":1,"entries":[{"id":"ph1","type":"expense","date":"2026-09-01","receipt":"photo","descr';   // cut off
          photos.set("ph1", jpeg("ph1")); photos.set("stray", jpeg("stray"));
          const w = make("en", { [KEY]: bad }, null, { photos });
          add(w, "expense", { description: "New", amount: "5" }, "books");          // saved: the unreadable one is now only set aside
          // the next visit's clean-up: the photo the set-aside ledger names stays (repaired, it may be restored)
          const w2 = make("en", Object.fromEntries(w.store), null, { photos });
          await w2.a.cleanPhotos(); await tick();
          const kept = [w2.a.damaged, photos.has("ph1"), photos.has("stray")];
          w2.a.damagedRemove(); await tick();
          await w2.a.cleanPhotos(); await tick();
          out({ kept, removed: [w2.a.damaged, photos.has("ph1")] });""")
        self.assertEqual(r["kept"], [1, True, False])
        self.assertEqual(r["removed"], [0, False])

    def test_closing_the_tab_asks_only_while_something_is_unsaved(self):
        r = app(self, r"""
          const w = make("en");
          const armed = () => (w.listeners.beforeunload || []).length;
          const s = [armed()];
          w.a.openAdd("expense", "books"); s.push(armed());                              // open, nothing typed
          w.a.form.description = "Big Book"; w.a.armLeave(); s.push(armed());            // typed
          const ev = { prevented: false, preventDefault() { this.prevented = true; } };
          w.listeners.beforeunload[0](ev); s.push(ev.prevented);
          w.a.form.description = ""; w.a.armLeave(); s.push(armed());                    // back as it was
          w.a.form.description = "Big Book"; w.a.form.amount = "12"; w.a.armLeave(); s.push(armed());
          w.a.saveForm(false); s.push(armed());                                          // saved
          w.a.openAdd("expense", "books"); w.a.form.description = "x"; w.a.armLeave(); w.a.formClosed(); s.push(armed());   // discarded
          out(s);""")
        self.assertEqual(r, [0, 0, 1, True, 0, 1, 0, 0])

    def test_undo_across_two_tabs_keeps_the_photo(self):
        r = app(self, r"""
          const photos = new Map(), shared = new Map();
          const a = make("en", null, null, { photos, store: shared });
          add(a, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
          const e = a.a.E()[0], id = e.id;
          photos.set(id, { id, type: "image/jpeg", blob: new Blob(["jpeg"]) });
          // tab A deletes it ("Undo" for 10 seconds) …
          a.a.remove([id]); await tick();
          const pending = Object.keys(JSON.parse(shared.get(KEY + ":undo") || "{}"));
          // … tab B opens meanwhile: its clean-up reads a ledger without the entry, and leaves the photo alone
          const b = make("en", null, null, { photos, store: shared });
          await b.a.cleanPhotos();
          const duringB = photos.has(id);
          a.a.undo(); await tick();
          const undone = [photos.has(id), a.a.E().length, shared.get(KEY + ":undo") || null];
          // A deletes it again; another tab brings the entry back before A's time is up: A's clean-up spares it
          a.a.remove([id]); await tick();
          const st = state(a); st.entries.push(e); shared.set(KEY, JSON.stringify(st));
          a.a.finishUndo(); await tick();
          const spared = photos.has(id);
          // a delete nobody takes back: once its time is up, the photo goes
          a.a.loadState(); a.a.remove([id]); await tick(); a.a.finishUndo(); await tick();
          out({ pending, duringB, undone, spared, gone: photos.has(id), left: shared.get(KEY + ":undo") || null, ids: [id] });""")
        self.assertEqual(r["pending"], r["ids"])
        self.assertTrue(r["duringB"])
        self.assertEqual(r["undone"], [True, 1, None])
        self.assertTrue(r["spared"])
        self.assertFalse(r["gone"])
        self.assertIsNone(r["left"])

    def test_an_entry_deleted_in_another_tab_keeps_its_photo_when_saved_again(self):
        # Tab B has an entry with a receipt photo open in its edit form; tab A deletes it; B is told, and saves it
        # again. Whatever the order — A's undo time over before B saves (A deletes the photo meanwhile), B saving
        # in time, A's "Undo" before or after B's save — there is one entry, under its own id, with its photo,
        # byte for byte, and the next visit's clean-up keeps it. A's "Undo" stays on screen when B saves.
        r = app(self, r"""
          const photos = new Map(), shared = new Map(), fire = (w) => { for (const fn of w.listeners.storage || []) fn({ key: KEY }); };
          const res = {};
          for (const order of ["undo_over_first", "saved_in_time", "undone_after", "undone_before"]) {
            photos.clear(); shared.clear();
            const a = make("en", null, null, { photos, store: shared });
            add(a, "expense", { description: "Hotel for the assembly", amount: "90", receipt: "photo", nights: "" }, "lodging");
            const id = a.a.E()[0].id, created = a.a.E()[0].created;
            photos.set(id, { id, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 7, 7, 7])], { type: "image/jpeg" }), w: 1200, h: 900, name: "IMG_1.jpg", added: "2026-09-26T10:00:00.000Z" });
            // an imported field this form doesn't show (kept by an edit — and by saving it again)
            const st0 = state(a); st0.entries[0].attendees = 4; shared.set(KEY, JSON.stringify(st0)); a.a.loadState();
            const b = make("en", null, null, { photos, store: shared });
            b.a.openEdit(id); await tick();                                          // the photo is shown
            b.a.form.description = "Hotel for the Fall Assembly";
            a.a.remove([id]); await tick(); fire(b);                                 // A deletes it; B hears of it
            const told = [b.a.formMode, b.a.form.id === id, b.a.dlgMsg === b.a.t("form.deleted_elsewhere"), (b.listeners.beforeunload || []).length];
            if (order === "undo_over_first") { a.a.finishUndo(); await tick(); }      // A's undo time is over: A deletes the photo
            const before = photos.has(id);
            if (order === "undone_before") { a.a.undo(); await tick(); fire(b); }
            b.a.saveForm(false); await tick(); fire(a);
            const aToast = [a.a.toastUndo, a.a.toastMsg];
            if (order === "saved_in_time") { a.a.closeToast(); await tick(); }       // A's undo time is over after B saved
            if (order === "undone_after") { a.a.undoToast(); await tick(); }
            const c = make("en", null, null, { photos, store: shared });             // the next visit, and its clean-up
            await c.a.cleanPhotos(); await tick();
            const p = photos.get(id);
            res[order] = { told, before, aToast, entries: state(c).entries.map((e) => [e.id === id, e.receipt, e.description, e.created === created, e.attendees]),
                           photo: p ? [Array.from(new Uint8Array(await p.blob.arrayBuffer())), p.w, p.h, p.name] : null, keys: photos.size,
                           leave: (b.listeners.beforeunload || []).length };
          }
          out(res);""")
        for order, x in r.items():
            with self.subTest(order=order):
                self.assertEqual(x["told"], ["add", True, True, 1])             # unsaved meanwhile: closing the tab asks
                self.assertEqual(x["before"], order != "undo_over_first")
                self.assertEqual(x["entries"], [[True, "photo", "Hotel for the Fall Assembly", True, 4]])
                self.assertEqual(x["photo"], [[0xFF, 0xD8, 7, 7, 7], 1200, 900, "IMG_1.jpg"])
                self.assertEqual(x["keys"], 1)
                self.assertEqual(x["leave"], 0)                                  # saved: nothing left to lose
        self.assertEqual(r["saved_in_time"]["aToast"], [True, "1 entry deleted"])   # A's "Undo" is still there

    def test_an_edit_that_lets_the_photo_go_deletes_it(self):
        # (the open form keeps its entry's photo safe — not one the visitor has just let go: "Remove photo", or the
        # receipt now kept on paper — that one goes as the edit is saved, as before)
        r = app(self, r"""
          const photos = new Map(), w = make("en", null, null, { photos });
          add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
          add(w, "expense", { description: "Books", amount: "12", receipt: "photo" }, "books");
          const [a, b] = w.a.E();
          for (const e of [a, b]) photos.set(e.id, { id: e.id, type: "image/jpeg", blob: new Blob([e.id], { type: "image/jpeg" }) });
          w.a.openEdit(a.id); await tick(); w.a.removePhoto(); w.a.saveForm(false); await tick();
          w.a.openEdit(b.id); await tick(); w.a.form.receipt = "paper"; w.a.saveForm(false); await tick();
          out({ left: [...photos.keys()], receipts: w.a.E().map((e) => e.receipt) });""")
        self.assertEqual(r["left"], [])
        self.assertEqual(r["receipts"], ["none", "paper"])

    def test_closing_the_tab_asks_while_changes_are_only_in_this_tab(self):
        # The browser keeps nothing (storage full or blocked, a newer page's ledger, an unreadable one with no room to
        # set it aside): every entry added is only in this tab, and closing it asks — until a save works again or a
        # full backup has them
        r = app(self, r"""
          const armed = (w) => (w.listeners.beforeunload || []).length;
          const w = make("en", null, null, { full: true });
          const s = [armed(w)];
          add(w, "expense", { description: "Books", amount: "12" }, "books"); s.push(armed(w));
          add(w, "expense", { description: "Hotel", amount: "90" }, "lodging"); s.push(armed(w));
          const ev = { prevented: false, preventDefault() { this.prevented = true; } };
          w.listeners.beforeunload[0](ev); s.push(ev.prevented);
          await w.a.exportBackup("plain"); s.push(armed(w), w.downloads.length);     // a backup has them
          add(w, "expense", { description: "Stamps", amount: "3" }, "other"); s.push(armed(w));
          w.setFull(false);
          add(w, "expense", { description: "Pens", amount: "2" }, "other"); s.push(armed(w), state(w).entries.length);
          const w2 = make("en", { [KEY]: JSON.stringify({ v: 99, entries: [], settings: {}, meta: {} }) });
          const newer = [w2.a.lock, armed(w2)];
          add(w2, "expense", { description: "Here", amount: "1" }, "books"); newer.push(armed(w2));
          const w3 = make("en", { [KEY]: "{cut" }, null, { full: true }); w3.setFull(false);
          const locked = [w3.a.lock, armed(w3)];
          add(w3, "expense", { description: "Typed", amount: "1" }, "books"); locked.push(armed(w3));
          out({ s, newer, locked });""")
        self.assertEqual(r["s"], [0, 1, 1, True, 0, 1, 1, 0, 4])
        self.assertEqual(r["newer"], ["newer", 0, 1])
        self.assertEqual(r["locked"], ["unreadable", 0, 1])

    def test_the_unreadable_datas_download_has_its_photos(self):
        # The notice says: download it, then remove it. The download is a .zip of its text as it was and the receipt
        # photos it names ("<id>.jpg"); "Remove it" asks, saying the photos go too and that the download has them;
        # repaired, it restores with its photos — picked unpacked, or zipped again. "Erase everything" leaves the
        # set-aside data's photos with it; "Remove it" before anything was saved leaves nothing to set aside again.
        r = app(self, r"""
          const photos = new Map(), jpeg = (id, b) => ({ id, type: "image/jpeg", blob: new Blob([new Uint8Array(b)], { type: "image/jpeg" }) });
          const bad = '{"v":1,"entries":[{"id":"ph1","type":"expense","date":"2026-09-01","category":"lodging","description":"Hotel","amount_cents":9000,"receipt":"photo"},'
                    + '{"id":"ph2","type":"expense","date":"2026-09-02","category":"printing","receipt":"photo","descr';     // cut off
          photos.set("ph1", jpeg("ph1", [0xff, 0xd8, 1])); photos.set("ph2", jpeg("ph2", [0xff, 0xd8, 2])); photos.set("stray", jpeg("stray", [9]));
          const w = make("en", { [KEY]: bad }, null, { photos });
          add(w, "expense", { description: "New", amount: "5" }, "books");          // saved: the unreadable data is only set aside now
          await w.a.damagedDownload();
          const d = w.downloads.at(-1), ar = await w.F.readZip(w.blob(d)), names = ar.entries.map((e) => e.name);
          const textBack = (await ar.text(names[0])) === bad;
          // repaired (the cut entry finished) and restored with the photos of its download: picked unpacked …
          const fixed = bad + 'iption":"Copies","amount_cents":300}]}';
          const pics = await Promise.all(names.slice(1).map(async (n) => fileOf(n, await ar.blob(n, "image/jpeg"), "image/jpeg")));
          const p3 = new Map(), w3 = make("en", null, null, { photos: p3 });
          await w3.a.impFiles([fileOf(names[0], fixed)].concat(pics));
          const preview = JSON.parse(JSON.stringify(w3.a.imp.counts));
          await w3.a.impApply();
          const restored = [[...p3.keys()].sort(), w3.a.E().map((e) => e.description).sort(), Array.from(new Uint8Array(await p3.get("ph2").blob.arrayBuffer()))];
          // … or zipped again
          const again = await w.F.zip([{ name: names[0], data: fixed }].concat(await Promise.all(names.slice(1).map(async (n) => ({ name: n, data: await ar.bytes(n) })))));
          const p4 = new Map(), w4 = make("en", null, null, { photos: p4 });
          await w4.a.impFile(fileOf("repaired.zip", again)); await w4.a.impApply();
          // "Erase everything" (another visit): the set-aside data and its photos stay, with the notice
          const pe = new Map([["ph1", jpeg("ph1", [1])], ["mine", jpeg("mine", [2])]]), we = make("en", Object.fromEntries(w.store), null, { photos: pe });
          we.a.eraseText = "ERASE"; we.a.eraseAll(); await tick();
          const erased = [we.a.damaged, [...pe.keys()]];
          // "Remove it": the question says so — then, the next visit, the photos only it named are gone
          w.a.$refs.ask = { open: false, showModal() { this.open = true; }, close() { this.open = false; }, querySelector: () => null };
          const p = w.a.damagedRemove(); await tick();
          const asked = w.a.ask.msg; w.a.askDone(true); await p;
          const w2 = make("en", Object.fromEntries(w.store), null, { photos }); await w2.a.cleanPhotos(); await tick();
          // removed before anything was saved: the stored text goes too (the notice does not come back)
          const w5 = make("en", { [KEY]: bad }, null, { photos: new Map([["ph1", jpeg("ph1", [1])]]) });
          w5.a.$refs.ask = w.a.$refs.ask;
          const p5 = w5.a.damagedRemove(); await tick();
          const asked5 = w5.a.ask.msg; w5.a.askDone(true); await p5;
          const w6 = make("en", Object.fromEntries(w5.store));
          out({ name: d.name, names, textBack, preview, restored, zipped: [...p4.keys()].sort(), erased, asked, after: [...photos.keys()].sort(), damaged: w2.a.damaged,
                asked5, again: [w5.store.has(KEY), w6.a.damaged] });""")
        self.assertRegex(r["name"], r"^service-expenses-unreadable-\d{4}-\d{2}-\d{2}\.zip$")
        self.assertEqual(r["names"], [r["name"][:-4] + ".json", "ph1.jpg", "ph2.jpg"])   # (not a photo it doesn't name)
        self.assertTrue(r["textBack"])                                         # its text exactly as it was
        self.assertEqual(r["preview"], {"entries": 2, "photos": 2, "missing": 0})
        self.assertEqual(r["restored"], [["ph1", "ph2"], ["Copies", "Hotel"], [0xFF, 0xD8, 2]])
        self.assertEqual(r["zipped"], ["ph1", "ph2"])
        self.assertEqual(r["erased"], [1, ["ph1"]])
        self.assertIn("and its receipt photos (2 receipt photos)?", r["asked"])
        self.assertIn("the download has its photos too", r["asked"])
        self.assertEqual(r["after"], [])                                       # gone once the visitor said so
        self.assertEqual(r["damaged"], 0)
        self.assertIn("(1 receipt photo)", r["asked5"])
        self.assertEqual(r["again"], [False, 0])

    def test_the_form_keeps_saying_so_and_looks_at_the_photo_again(self):
        # Tab A deletes the entry open in B's form, then changes something else: B's dialog still says the entry was
        # deleted; A's "Undo" brings it back: an edit again. B saves; A, not having seen that save yet, deletes the
        # photo just after B looked: B looks once more a moment later and stores it again — but not a photo B itself
        # let go meanwhile ("Remove photo" in a second edit).
        r = app(self, r"""
          const fire = (w) => { for (const fn of w.listeners.storage || []) fn({ key: KEY }); };
          const pair = async () => {
            const photos = new Map(), shared = new Map(), a = make("en", null, null, { photos, store: shared });
            add(a, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
            const id = a.a.E()[0].id;
            photos.set(id, { id, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 5])], { type: "image/jpeg" }) });
            const b = make("en", null, null, { photos, store: shared });
            b.a.openEdit(id); await tick();
            b.a.form.description = "Hotel for the Fall Assembly";
            a.a.remove([id]); await tick(); fire(b);
            return { photos, a, b, id };
          };
          const one = await pair(), two = await pair(), { a, b, id, photos } = one;
          add(a, "expense", { description: "Books", amount: "12" }, "books"); fire(b);
          const still = [b.a.formMode, b.a.dlgMsg === b.a.t("form.deleted_elsewhere")];
          a.a.undo(); await tick(); fire(b);
          const back = [b.a.formMode, b.a.dlgMsg === b.a.t("toast.other_tab")];
          b.a.saveForm(false); await tick();
          const looked = photos.has(id);
          photos.delete(id);                                            // A's late delete
          two.b.a.saveForm(false); await tick();
          two.a.a.finishUndo(); await tick();                          // (A's undo time over: nothing else keeps the photo)
          two.b.a.openEdit(two.id); await tick(); two.b.a.removePhoto(); two.b.a.saveForm(false); await tick();
          const letGo = two.photos.has(two.id);
          await new Promise((res) => setTimeout(res, 2300)); await tick();
          out({ still, back, looked, again: photos.has(id), entries: state(a).entries.map((e) => [e.id === id, e.receipt, e.description]),
                letGo, after: two.photos.has(two.id), receipt: state(two.b).entries.map((e) => e.receipt) });""")
        self.assertEqual(r["still"], ["add", True])
        self.assertEqual(r["back"], ["edit", True])
        self.assertTrue(r["looked"])
        self.assertTrue(r["again"])                                            # stored again, a moment later
        self.assertEqual(r["entries"], [[False, "none", "Books"], [True, "photo", "Hotel for the Fall Assembly"]])
        self.assertEqual((r["letGo"], r["after"], r["receipt"]), (False, False, ["none"]))

    def test_a_backup_without_photos_asks_on_while_a_photo_would_be_lost(self):
        # The browser stops keeping the ledger (storage full): a new entry and its receipt photo are only in this tab (the
        # photo in IndexedDB, which the next visit's clean-up deletes: no stored ledger points to it). "Back up without
        # photos" does not have it, so closing still asks; a full backup has it: no more question. Without photos to
        # lose, the backup without photos is enough. Removing unreadable data saves what was changed meanwhile (a
        # setting too); "Erase everything" clears the list of photos the last backup left out.
        r = app(self, r"""
          const armed = (w) => (w.listeners.beforeunload || []).length;
          const photos = new Map(), w = make("en", null, null, { photos });
          add(w, "expense", { description: "Old", amount: "1", receipt: "photo" }, "books");
          const old = w.a.E()[0].id;
          photos.set(old, { id: old, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 1])], { type: "image/jpeg" }) });
          w.setFull(true);
          add(w, "expense", { description: "Hotel", amount: "90", receipt: "photo" }, "lodging");
          const hotel = w.a.E().find((e) => e.description === "Hotel").id;
          photos.set(hotel, { id: hotel, type: "image/jpeg", blob: new Blob([new Uint8Array([0xff, 0xd8, 2])], { type: "image/jpeg" }) });
          const s = [armed(w)];
          await w.a.exportBackup("plain"); s.push(armed(w));
          await w.a.exportBackup(); s.push(armed(w), w.downloads.at(-1).name.endsWith(".zip"));
          const w2 = make("en", null, null, { full: true });                              // nothing with a photo
          add(w2, "expense", { description: "Books", amount: "12", receipt: "paper" }, "books");
          const s2 = [armed(w2)];
          await w2.a.exportBackup("plain"); s2.push(armed(w2));
          // unreadable data, no room to set it aside: a setting changed meanwhile is saved once it is removed
          const w3 = make("en", { [KEY]: "{cut" }, null, { full: true }); w3.setFull(false);
          w3.a.setProf("name", "Pat K.");
          const s3 = [w3.a.lock, armed(w3)];
          w3.a.damagedRemove(); await tick();
          s3.push(w3.a.lock, armed(w3), w3.store.has(KEY) ? (state(w3).settings.profile || {}).name : null);
          // the photos left out of the last full backup, then "Erase everything"
          photos.get(old).blob.arrayBuffer = () => Promise.reject(new Error("NotReadableError"));
          w.setFull(false);
          await w.a.exportBackup();
          const left = w.a.bkLeft.length;
          w.a.eraseText = w.a.t("data.erase_word"); w.a.eraseAll(); await tick();
          out({ s, s2, s3, left, erased: [w.a.bkLeft.length, w.a.E().length] });""")
        self.assertEqual(r["s"], [1, 1, 0, True])
        self.assertEqual(r["s2"], [1, 0])
        self.assertEqual(r["s3"], ["unreadable", 1, "", 0, "Pat K."])
        self.assertEqual((r["left"], r["erased"]), (1, [0, 0]))


if __name__ == "__main__":
    unittest.main()
