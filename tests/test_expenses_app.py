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
    tab while it is being edited here is saved as a new one, and the dialog says so; a "replace"
    import whose save is refused keeps the receipt photos of the ledger that stays
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
  * the rest — the examples are added once; a CSV export is not a backup; the Summary's badge counts
    what its Reminders card lists, and "By category" counts subscriptions as subscriptions; "Sort:
    Category" follows the names on screen; two items that
    differ by an accent are two rows; "Last backup" counts calendar days

The app is loaded as the page loads it (expenses-core.js, then expenses.js) into a vm context with a
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
from nodejs import run_js  # noqa: E402

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
  const store = new Map(Object.entries(seed || {}));
  let full = false;
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
    console, TextDecoder, Blob, Promise, JSON, Math, Date: clock, Intl, Object, Array, String, Number, isFinite, isNaN, Uint8Array, atob,
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); t.unref?.(); return t; },
    clearTimeout, requestAnimationFrame: (fn) => setTimeout(fn, 0),
    getComputedStyle: (el) => (el && el.style) || {},      // an element's "computed" style is its own style
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => { if (full) { const e = new Error("full"); e.name = "QuotaExceededError"; throw e; } store.set(k, String(v)); },
      removeItem: (k) => { store.delete(k); },
    },
    indexedDB: o.photos ? fakeIDB(o.photos) : undefined,
    URL: { createObjectURL: (b) => { const u = "blob:" + (++n); blobs.set(u, b); return u; }, revokeObjectURL() {} },
    location: { hash: "" }, history: { pushState() {} },
    navigator: { storage: { persist: () => Promise.resolve(false), persisted: () => Promise.resolve(false), estimate: () => Promise.resolve({ usage: 0 }) } },
    matchMedia: () => ({ matches: true, addEventListener() {} }),
    addEventListener: (type, fn) => { (listeners[type] ||= []).push(fn); },
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
  for (const f of ["src/assets/js/expenses-core.js", "src/assets/js/expenses.js"]) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
  let factory = null;
  ctx.Alpine = { directive() {}, data: (name, fn) => { if (name === "xpApp") factory = fn; } };
  for (const fn of docListeners["alpine:init"] || []) fn();
  const a = factory(lang);
  a.$nextTick = (fn) => fn && fn();
  a.$refs = {};
  a.$watch = () => {};
  a.init();
  return {
    a, ctx, store, downloads, listeners, G: ctx.GVX,
    setFull: (v) => { full = v; },
    text: async (d) => await blobs.get(d.url).text(),
  };
};
const tick = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };
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
          out({ mode, n: w.a.E().length, sameId: w.a.E()[0].id === id, msg: w.a.t("form.deleted_elsewhere") });""")
        self.assertEqual(r["mode"], ["add", "", r["msg"]])
        self.assertEqual(r["n"], 1)
        self.assertFalse(r["sameId"])                                         # saved as a new entry, knowingly

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
              w.a.imp.mode = "replace"; w.a.impApply(); await tick();
            },
            backup: async (w) => {
              const e = w.G.normalizeEntry({ id: "b1", type: "expense", date: "2026-09-01", category: "other", description: "From the backup", amount_cents: 100, receipt: "photo" }, w.a.st()).entry;
              w.a.impFile(file("backup.json", w.G.toBackup({ entries: [e], settings: w.a.st(), meta: {} }, [{ id: "b1", type: "image/jpeg", dataUrl: "data:image/jpeg;base64,/9j/4AAQ" }])));
              await tick();
              w.a.imp.mode = "replace"; w.a.impApply(); await tick();
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
        r = app(self, r"""
          const w = make("en");
          const G = w.G, big = "data:image/jpeg;base64," + "A".repeat(400 * 1024);
          const entries = [], receipts = [];
          for (let i = 0; i < 40; i++) {
            const id = "b" + i;
            entries.push(G.normalizeEntry({ id, type: "expense", date: "2026-09-01", description: "Receipt " + i, amount_cents: 100 + i, receipt: "photo" }, w.a.st()).entry);
            receipts.push({ id, type: "image/jpeg", dataUrl: big });
          }
          const text = G.toBackup({ entries, settings: w.a.st(), meta: {} }, receipts);
          const file = (name, t) => ({ name, size: Buffer.byteLength(t), arrayBuffer: async () => new TextEncoder().encode(t).buffer });
          w.a.impFile(file("big-backup.json", text)); await tick();
          const backup = [w.a.imp.step, w.a.imp.err, w.a.imp.counts && w.a.imp.counts.entries];
          const csv = "date,amount\n" + "2026-09-01,1\n".repeat(Math.ceil(11 * 1048576 / 13));
          w.a.impFile(file("big.csv", csv)); await tick();
          out({ mb: +(text.length / 1048576).toFixed(1), backup, csv: w.a.imp.err, limits: [G.importLimit("csv"), G.importLimit("backup")],
                kinds: [G.importKind("x.json", ""), G.importKind("backup.txt", "﻿ {"), G.importKind("a.csv", "date,amount")] });""", )
        self.assertGreater(r["mb"], 15)
        self.assertEqual(r["backup"], ["backup", "", 40])
        self.assertEqual(r["csv"], "The file is larger than 10 MB.")
        self.assertEqual(r["limits"], [10 * 1048576, 80 * 1048576])
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
          w.a.impApply(); await tick();
          photos.set("p2", { id: "p2", type: "image/jpeg", blob: new Blob(["mine"]), mine: true });
          w.a.impFile(file("service-expenses-backup.json", backup)); await tick();
          const preview = [w.a.imp.step, w.a.imp.counts.entries, w.a.imp.counts.photos];
          w.a.impApply(); await tick();
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
              w.a.impApply(); await tick();
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
            const w = make(lang);
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
          out(res);""")
        en = r["en"]
        # $150 room + 63 mi × $0.30 = $18.90 + 352.2 mi × $0.30 = $105.66 (+ the ride: $0) = $274.56; 2025's trip is out
        self.assertEqual(en["rows"], [["money", "Hotel & lodging", "$150.00"], ["miles", "Assemblies & Area committee meetings", "$18.90"],
                                      ["miles", "Information tables & conventions", "$105.66"], ["miles", "Workshops & events", "$0.00"],
                                      ["miles_total", "Mileage total", "$124.56"], ["total", "Total cost of service", "$274.56"]])
        self.assertEqual(en["rates"], "$0.30 a mile")
        self.assertEqual(en["periods"][:2], ["y:2026", "y:2025"])
        self.assertEqual(en["money"], [[["2026-03-20 – 2026-03-22", "Check · Check #101", "Room shared with a member"]]])
        self.assertEqual(en["miles"][1], ["Information tables & conventions", [["State Convention", "3", "58.7", "352.2", "Home → Fort Worth", "Table support"]]])
        # whom you rode with is a name: out unless names are in
        self.assertEqual(en["miles"][2][1], [["Big Country", "—", "—", "0", "Rode with someone: no miles", "Table support"]])
        self.assertEqual(en["named"], "Rode with Area Archives")
        self.assertEqual(en["totals"], ["$274.56", "$0.00", "$0.00", "$0.00"])     # all of it self-supported
        self.assertEqual(en["report"], {"prepared_for": "District 22 treasurer", "note": "A record,\nnot a request."})
        self.assertEqual(en["saved"], en["report"])                                 # kept with the settings (and the backup)
        self.assertRegex(en["name"], r"^service-expenses-report-2026-\d{4}-\d{2}-\d{2}\.csv$")
        self.assertRegex(r["es"]["name"], r"^gastos-de-servicio-informe-2026-\d{4}-\d{2}-\d{2}\.csv$")
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


if __name__ == "__main__":
    unittest.main()
