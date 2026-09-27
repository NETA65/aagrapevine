"""The service expense tracker's screen logic (src/assets/js/expenses.js, the Alpine app "xpApp") run in
Node.js — the rules that live in the app itself, not in the core (tests/test_expenses_core.py):

  * the add / edit form — an empty amount is refused (0 is fine, a minus sign is not); a request
    status the form does not show survives an edit of a purchase made for someone; "Record the
    renewal" starts the new term where the old one ends (and the reminder goes); a duplicate is a
    new trip (no odometer); money received from a person settles what was bought for them
  * storage — a save the browser refuses never says "Saved"; the screen's own choices (the view,
    the period) are kept apart, so another tab does not reload for them; an entry deleted in another
    tab while it is being edited here is saved as a new one, and the dialog says so
  * requests — "Download CSV" is the request's own lines, without people's names unless the request
    includes them
  * import — a full backup bigger than a CSV may be is still restored; a mileage log with no amount
    column can be mapped; a problem names the visitor's own column
  * the rest — the examples are added once; a CSV export is not a backup; the Summary's badge counts
    what its Reminders card lists

The app is loaded as the page loads it (expenses-core.js, then expenses.js) into a vm context with a
small stand-in for the browser: localStorage (that can be made to refuse), no IndexedDB (the photos'
calls fail softly, as in a private window), a document that records downloads, and an Alpine that
hands back the component. The words and defaults come from src/_data/expenses.js, as on the page.

    python -m unittest tests.test_expenses_app -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

# The browser stand-in and the app: `app(lang)` → a fresh component (its own storage), `tick()` lets
# promises settle, `downloads` are the files the app saved ({name, text}).
LOAD = r"""
import vm from "node:vm";
const data = (await imp("src/_data/expenses.js")).default();
const make = (lang, seed) => {
  const store = new Map(Object.entries(seed || {}));
  let full = false;
  const listeners = {}, docListeners = {}, blobs = new Map(), downloads = [];
  let n = 0;
  const els = {
    "xp-config": { textContent: JSON.stringify(data.config) },
    "xp-ui": { textContent: JSON.stringify(data.ui[lang]) },
    "xp-events": { textContent: "[]" },
  };
  const ctx = {
    console, TextDecoder, Blob, Promise, JSON, Math, Date, Intl, Object, Array, String, Number, isFinite, isNaN, Uint8Array,
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); t.unref?.(); return t; },
    clearTimeout, requestAnimationFrame: (fn) => setTimeout(fn, 0),
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => { if (full) { const e = new Error("full"); e.name = "QuotaExceededError"; throw e; } store.set(k, String(v)); },
      removeItem: (k) => { store.delete(k); },
    },
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


def app(case: unittest.TestCase, js: str):
    return run_js(case, LOAD + js, timeout=120)


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


if __name__ == "__main__":
    unittest.main()
