"""The service expense tracker's logic (src/assets/js/expenses-core.js, window.GVX) run in Node.js.

People's money: every amount is checked against numbers worked out by hand (in the comments).
  * money / numbers / dates — "$1,234.50", "1.234,50", "(12.00)", Excel serial dates, month names …
  * mileage              — round(miles × 1000 × round(rate × 1000) / 10000), exact, half up
  * entries              — normalizeEntry (never throws, idempotent) and validateEntry
  * CSV                  — the writer (BOM, CRLF, quotes, formula guard), the reader (delimiters, line
                           ends, quoted line breaks, blank and ragged rows), the ROUND-TRIP LAW with
                           nasty values (also through "Excel": ; + decimal commas + day-first dates),
                           planImport on garbage (never throws), limits, the mapping step, dedupe/merge
  * totals               — summary / funderBalances / peopleOwed / inventory / renewals / budgets /
                           stale claims / requests, on a hand-computed ledger
  * backup, settings     — readBackup rejects foreign JSON, migrates the older list; mergeDefaults
                           keeps the visitor's edits and adds new built-ins
  * examples             — a realistic GVR season, first names only, one of each kind
The file runs in a vm context, as tests/test_pwa_worker.py runs sw-core.js. Skipped without Node.js.

    python -m unittest tests.test_expenses_core -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

CORE = "src/assets/js/expenses-core.js"


def _cat(i, cid, typ, template, en, es, **extra):
    return {"id": cid, "type": typ, "template": template, "icon": "circle", "color": "slate",
            "label": {"en": en, "es": es}, "builtin": True, "hidden": False, "order": i, **extra}


# The site's defaults as src/_data/expenses.js hands them to the page (a fixed copy: these tests don't
# depend on edits to config/expenses.yml; ConfigFile below checks the real file when it is there).
CONFIG = {
    "categories": [
        _cat(0, "books", "expense", "books", "Books & literature", "Libros y literatura"),
        _cat(1, "giveaways", "expense", "books", "Literature to give away (carry the message)",
             "Literatura para regalar (llevar el mensaje)", giveaway_default=True),
        _cat(2, "subscriptions", "expense", "subscription", "Magazine subscriptions", "Suscripciones a revistas"),
        _cat(3, "lodging", "expense", "lodging", "Hotel & lodging", "Hotel y hospedaje"),
        _cat(4, "meals", "expense", "meal", "Meals", "Comidas"),
        _cat(5, "printing", "expense", "printing", "Printing & copies", "Impresiones y copias"),
        _cat(6, "registration", "expense", "general", "Registration fees", "Cuotas de inscripción"),
        _cat(7, "travel", "expense", "travel", "Parking, tolls & fares", "Estacionamiento, peajes y pasajes"),
        _cat(8, "contributions", "expense", "general", "Seventh Tradition contributions",
             "Contribuciones de la Séptima Tradición", default_funder="me", default_claim="none"),
        _cat(9, "other", "expense", "general", "Other", "Otros"),
        _cat(10, "mileage", "mileage", "mileage", "Miles driven", "Millas recorridas"),
        _cat(11, "reimbursement", "received", "received", "Reimbursement", "Reembolso"),
        _cat(12, "advance", "received", "received", "Money advanced to me", "Dinero adelantado"),
        _cat(13, "repayment", "received", "received", "Paid back by a person", "Me lo devolvió una persona"),
        _cat(14, "given", "giveaway", "giveaway", "Given away at an event", "Regalado en un evento"),
        _cat(15, "stock_in", "stock", "stock", "Received to give away (no cost)", "Recibido para regalar (sin costo)"),
    ],
    "funders": [
        {"id": "me", "kind": "self", "name": {"en": "Me (self-supported)", "es": "Yo (autofinanciado)"}, "builtin": True, "hidden": False, "order": 0},
        {"id": "area", "kind": "area", "name": {"en": "Area 65 (NETA 65)", "es": "Área 65 (NETA 65)"}, "builtin": True, "hidden": False, "order": 1},
        {"id": "district", "kind": "district", "name": {"en": "My district", "es": "Mi distrito"}, "builtin": True, "hidden": False, "order": 2},
        {"id": "group", "kind": "group", "name": {"en": "My home group", "es": "Mi grupo base"}, "builtin": True, "hidden": False, "order": 3},
        {"id": "committee", "kind": "committee", "name": {"en": "Grapevine / La Viña committee", "es": "Comité de Grapevine / La Viña"},
         "builtin": True, "hidden": False, "order": 4},
    ],
    "methods": [{"id": m, "name": {"en": m, "es": m}, "builtin": True, "hidden": False, "order": i}
                for i, m in enumerate(["cash", "card", "check", "app", "direct"])],
    "rates": [
        {"id": "irs_charity", "name": {"en": "IRS charitable rate", "es": "Tarifa benéfica del IRS"}, "rate": "0.14", "builtin": True},
        {"id": "service", "name": {"en": "My district's / Area's rate", "es": "Tarifa de mi distrito / Área"}, "rate": "", "builtin": True},
    ],
    "default_rate": "irs_charity",
    "defaults": {"funder": "me", "method": "cash", "round_trip": False},
    "panels": [{"id": "77", "from": "2027-01-01", "to": "2028-12-31"}],
    "renewal_days": 60,
    "backup_reminder_days": 30,
}

# Loads the core into a fresh vm context: G = window.GVX, S = the default settings.
LOAD = r"""
import vm from "node:vm";
const ctx = vm.createContext({ console, TextDecoder });
vm.runInContext(fs.readFileSync("src/assets/js/expenses-core.js", "utf8"), ctx, { filename: "expenses-core.js" });
const G = ctx.GVX;
const CONFIG = input.config;
const S = G.emptyState(CONFIG).settings;
const N = (raw, s) => G.normalizeEntry(raw, s || S).entry;
const plain = (v) => JSON.parse(JSON.stringify(v));
"""


def core(case: unittest.TestCase, js: str, data: dict | None = None, **kw):
    """Run `js` (it calls out(value)) with the core loaded; returns the value."""
    return run_js(case, LOAD + js, data={"config": CONFIG, **(data or {})}, needs_modules=False, **kw)


class Money(unittest.TestCase):
    def test_parse_money(self):
        # [text as typed / exported, opts, integer cents]
        cases = [
            ["$1,234.50", None, 123450], ["1.234,50", None, 123450], ["12,50", None, 1250], ["12.5", None, 1250],
            ["(12.00)", None, -1200], ["-12.00", None, -1200], ["12.00-", None, -1200], ["−7.25", None, -725],
            ["$ 1 234,56", None, 123456], ["1 234", None, 123400], ["1'234.50", None, 123450],
            # one separator + exactly 3 digits: opts.decimal decides ("." by default)
            ["1,234", None, 123400], ["1,234", {"decimal": ","}, 123], ["1.234", None, 123], ["1.234", {"decimal": ","}, 123400],
            ["0,655", None, 66],                                   # "0,655" is never thousands: 65.5 ¢ → 66 ¢
            ["US$ 999,999.99", None, 99999999], ["999999.99", None, 99999999], ["12.345.678,9", None, 1234567890],
            ["0", None, 0], ["0.00", None, 0], ["12.", None, 1200], [".5", None, 50], ["  42  ", None, 4200],
            ["-$5", None, -500], ["$-5", None, -500], ["5 $", None, 500],
            # half a cent rounds up, on the digits (never a float): 2.675 is 2.67499… as a float
            [12.5, None, 1250], [1.005, None, 101], ["1.005", None, 101], ["2.675", None, 268], ["0.125", None, 13],
            # not money
            ["", None, None], ["   ", None, None], ["abc", None, None], ["1,2,3", None, None], ["1.2.3", None, None],
            ["$", None, None], ["--5", None, None], ["1e5", None, None], ["'=1", None, None], ["1,234.567,89", None, None],
            ["12abc", None, None], ["=SUM(A1)", None, None],
        ]
        got = core(self, "out(input.cases.map(([v, o]) => G.parseMoney(v, o || undefined)));", {"cases": [c[:2] for c in cases]})
        for (v, o, want), g in zip(cases, got):
            self.assertEqual(g, want, f"parseMoney({v!r}, {o})")

    def test_cents_text_and_format(self):
        r = core(self, """out({
          text: [0, 5, 1250, -1200, 99999999, -0].map(G.centsText),
          en: [123450, -500, 0].map((c) => G.fmtMoney(c, "en")),
          es: G.fmtMoney(123450, "es"),
          date: [G.fmtDate("2026-09-27", "en"), G.fmtDate("2026-09-27", "es"), G.fmtDate("nope", "en")],
        });""")
        self.assertEqual(r["text"], ["0.00", "0.05", "12.50", "-12.00", "999999.99", "0.00"])
        self.assertEqual(r["en"], ["$1,234.50", "-$5.00", "$0.00"])
        self.assertIn("234", r["es"])
        self.assertEqual(r["date"][0], "Sep 27, 2026")
        self.assertIn("2026", r["date"][1])
        self.assertEqual(r["date"][2], "nope")

    def test_numbers_and_rates(self):
        r = core(self, """out({
          rates: ["0.14", "0.140", "0.655", 0.655, "0,14", "0,655", ".5", "0.1", "abc", "-0.14", "100", "", null, "$0.14"].map(G.rateText),
          nums: ["12,3", "1.234,5", "12.3", "abc", "", "-4"].map((v) => G.parseNumber(v)),
        });""")
        self.assertEqual(r["rates"], ["0.14", "0.14", "0.655", "0.655", "0.14", "0.655", "0.50", "0.10", "", "", "", "", "", "0.14"])
        self.assertEqual(r["nums"], [12.3, 1234.5, 12.3, None, None, -4])


class Mileage(unittest.TestCase):
    def test_hand_computed(self):
        r = core(self, """out([
          G.mileageCents(12.3, "0.655"),   // 12.3 × 0.655 = 8.0565 → 805.65 ¢ → 806
          G.mileageCents(12.3, 0.655),
          G.mileageCents("12.3", "0.655"),
          G.mileageCents(100, "0.14"),     // 14.00
          G.mileageCents(184.6, "0.14"),   // 25.844 → 2584
          G.mileageCents(1, "0.005"),      // exactly half a cent → 1
          G.mileageCents(0.1, "0.005"),    // 0.05 ¢ → 0
          G.mileageCents(4.35, "0.655"),   // 2.849250 → 284.925 ¢ → 285 (the float product is 284.92499…)
          G.mileageCents(38, "0.14"),      // 5.32
          G.mileageCents(0, "0.14"), G.mileageCents(10, ""), G.mileageCents(10, "abc"), G.mileageCents(-5, "0.14"),
          G.mileageCents(1000000, "99.999"),
        ]);""")
        self.assertEqual(r, [806, 806, 806, 1400, 2584, 1, 0, 285, 532, 0, 0, 0, 0, 9999900000])

    def test_the_spec_formula_on_a_grid(self):
        # The spec: Math.round(miles*1000 * Math.round(rate*1000) / 10000). The core does the same in whole
        # numbers; the two may only differ where the exact value is half a cent and float error moved it.
        r = core(self, """
          const spec = (m, r) => Math.round(m * 1000 * Math.round(r * 1000) / 10000);
          let n = 0; const diff = [];
          for (let t = 1; t <= 6000; t++) {
            const m = t / 10;
            for (const r of ["0.14", "0.655", "0.67", "0.21", "0.585", "0.725", "0.1", "0.005"]) {
              n++;
              const a = G.mileageCents(m, r), b = spec(m, Number(r));
              if (a !== b) diff.push({ m, r, a, b, rem: (t * 100 * Math.round(Number(r) * 1000)) % 10000 });
            }
          }
          out({ n, diff });""")
        self.assertEqual(r["n"], 48000)
        for d in r["diff"]:
            self.assertEqual(d["rem"], 5000, d)          # only exact half cents …
            self.assertEqual(d["a"], d["b"] + 1, d)      # … which the core rounds up

    def test_trip_miles_and_the_entry(self):
        r = core(self, """
          const trip = N({ type: "mileage", date: "2026-09-05", from: "Home", to: "Assembly, Tyler", round_trip: true,
                           miles: G.tripMiles(92.3, true), rate: "0.14", funder: "district" });
          const odo = N({ type: "mileage", date: "2026-09-06", round_trip: true, odometer_start: 42150, odometer_end: 42188.5,
                          miles: 999, rate: "0.655" });
          out({ t: [G.tripMiles(92.3, true), G.tripMiles(10, false, 42150, 42188), G.tripMiles(92.3, true, 100, 150),
                    G.tripMiles("", false), G.tripMiles("12,5", true)],
                trip: [trip.miles, trip.amount_cents, trip.description, trip.claim_status, trip.rate],
                odo: [odo.miles, odo.amount_cents, odo.description] });""")
        self.assertEqual(r["t"], [184.6, 38, 50, 0, 25])
        # 184.6 × 0.14 = 25.844 → $25.84; a funder other than me → "to request"
        self.assertEqual(r["trip"], [184.6, 2584, "Home → Assembly, Tyler", "to_request", "0.14"])
        # the odometer is the whole trip (not doubled): 38.5 mi × 0.655 = 25.2175 → $25.22
        self.assertEqual(r["odo"], [38.5, 2522, ""])


class Dates(unittest.TestCase):
    def test_parse_date(self):
        cases = [
            ["2026-09-27", None, "2026-09-27"], ["2026-9-7", None, "2026-09-07"], ["2026/09/27", None, "2026-09-27"],
            ["2026-09-27T23:30:00-05:00", None, "2026-09-27"], ["2026-09-27 10:00", None, "2026-09-27"],
            ["9/27/2026", None, "2026-09-27"], ["27/9/2026", None, "2026-09-27"],          # the day > 12 decides
            ["3/4/2026", None, "2026-03-04"], ["3/4/2026", {"dateOrder": "dmy"}, "2026-04-03"],
            ["3/4/26", None, "2026-03-04"], ["3.4.2026", {"dateOrder": "dmy"}, "2026-04-03"], ["03-04-2026", None, "2026-03-04"],
            ["27 Sep 2026", None, "2026-09-27"], ["Sep 27, 2026", None, "2026-09-27"], ["27-sep-26", None, "2026-09-27"],
            ["27 de septiembre de 2026", None, "2026-09-27"], ["Sunday, September 27, 2026", None, "2026-09-27"],
            ["martes 3 de marzo de 2026", None, "2026-03-03"], ["1 ene. 2027", None, "2027-01-01"],
            # Excel serial numbers, only for a date column: 45658 = 2025-01-01; 46000 = 342 days later
            ["45658", {"serial": True}, "2025-01-01"], ["46000", {"serial": True}, "2025-12-09"], [46000, {"serial": True}, "2025-12-09"],
            ["46000", None, None], ["19999", {"serial": True}, None],
            ["2024-02-29", None, "2024-02-29"], ["2025-02-29", None, None], ["2026-02-30", None, None], ["2026-13-01", None, None],
            ["1899-12-31", None, None], ["hello", None, None], ["", None, None], ["12", None, None], ["31/31/2026", None, None],
            ["'2026-09-27", None, "2026-09-27"],
        ]
        got = core(self, "out(input.cases.map(([v, o]) => G.parseDate(v, o || undefined)));", {"cases": [c[:2] for c in cases]})
        for (v, o, want), g in zip(cases, got):
            self.assertEqual(g, want, f"parseDate({v!r}, {o})")

    def test_months_and_days(self):
        r = core(self, """out([
          G.addMonths("2026-01-31", 1), G.addMonths("2024-01-31", 1), G.addMonths("2026-09-27", 12), G.addMonths("2026-11-15", 3),
          G.addMonths("2026-03-31", -1), G.addMonths("bad", 1), G.daysBetween("2026-09-01", "2026-09-27"), G.addDays("2026-03-01", -1),
        ]);""")
        self.assertEqual(r, ["2026-02-28", "2024-02-29", "2027-09-27", "2027-02-15", "2026-02-28", "", 26, "2026-02-28"])


# Settings with one custom field of each kind (a comma in a label: the header cell must be quoted).
WITH_CUSTOM = r"""
const S2 = plain(S);
S2.custom_fields = [
  { id: "cf_text", label: "Sponsor note, private", type: "text", options: [], types: [] },
  { id: "cf_num", label: "Pages", type: "number", options: [], types: [] },
  { id: "cf_yes", label: "Approved?", type: "yesno", options: [], types: [] },
  { id: "cf_date", label: { en: "Reviewed on", es: "Revisado el" }, type: "date", options: [], types: [] },
  { id: "cf_pick", label: "Size", type: "choice", options: ["A", "B"], types: [] },
];
"""

# Values that break naive CSV code and spreadsheets.
NASTY = r"""
const NASTY = ["Comma, inside", 'Quote "inside"', "Line\nbreak", "CRLF\r\ninside", "Emoji 🙏📖 ok", "Acentos: Viña, niño, José",
  "=SUM(A1)", "+1", "-5", "@cmd", "007", "'=already guarded", "العربية مرحبا", "עברית ושלום", "tab\tinside", "  spaces  ",
  "semi; colon", "", "'", "''", '"', "a\rb", "=HYPERLINK(\"http://x\")", "‏RTL mark", "0", "1,234.50"];
const TYPES5 = ["expense", "mileage", "received", "giveaway", "stock"];
const CATS = { expense: ["books", "giveaways", "subscriptions", "lodging", "meals", "printing"], mileage: ["mileage"],
  received: ["reimbursement", "advance", "repayment"], giveaway: ["given"], stock: ["stock_in"] };
const AMOUNTS = [0, 1, 99, 99999999, 12345, 50, 99999999999, 100];
function nastyLedger(s) {
  return NASTY.map((v, i) => {
    const type = TYPES5[i % 5], cats = CATS[type];
    const raw = { id: "x" + i.toString(36) + "n", type, date: ["2024-02-29", "1900-01-01", "2200-12-31", "2026-09-27"][i % 4],
      category: cats[i % cats.length], description: v, amount_cents: AMOUNTS[i % AMOUNTS.length],
      funder: ["me", "area", "district", "group", "committee"][(i + Math.floor(i / 5)) % 5], vendor: v, event: v, place: v, person: v, item: v,
      claim_ref: v, receipt_ref: v, from: v, to: v, notes: v + "\n" + v, tags: [v, "x" + i],
      format: ["gv", "lv", "other", ""][i % 4], quantity: [0, 1.5, 20, ""][i % 4], unit_cost_cents: [0, 250, "", 1][i % 4],
      giveaway: i % 3 === 0, receipt: ["none", "paper", "photo", "file"][i % 4],
      created: "2026-09-27T18:00:" + String(i % 60).padStart(2, "0") + ".123Z", updated: "2026-09-28T01:02:03.456Z",
      custom: { cf_text: v, cf_num: i * 1.5, cf_yes: i % 2 === 0, cf_date: "2026-02-28", cf_pick: i % 2 ? "A" : "B" } };
    if (type === "mileage") Object.assign(raw, { miles: [0.1, 184.6, 999999.9, 12.3][i % 4], rate: ["0.655", "0.14", "", "0.005"][i % 4],
      round_trip: i % 2 === 0, amount_cents: i % 4 === 2 ? 4321 : 0 });
    if (i % 7 === 0) Object.assign(raw, { odometer_start: 42150, odometer_end: 42188.5 });
    if (type === "expense") Object.assign(raw, { claim_status: ["to_request", "submitted", "paid", "denied"][i % 4],
      claim_date: "2026-09-28", paid_date: i % 2 ? "2026-10-01" : "", method: ["cash", "card", "direct", ""][i % 4],
      end_date: i % 3 === 0 ? "2026-09-30" : "", nights: i % 3 === 0 ? 3 : "", attendees: i % 5 === 0 ? 6 : "",
      sub_product: ["gv_print", "lv_complete", "", "other"][i % 4], sub_term: [12, 24, "", 1][i % 4], sub_start: i % 2 ? "2026-01-31" : "",
      sub_kind: ["gift", "helped", "group", "self", ""][i % 5], repaid: ["", "owed", "repaid", "forgiven"][i % 4] });
    return G.normalizeEntry(raw, s).entry;
  });
}
"""


class Entries(unittest.TestCase):
    def test_garbage_never_throws(self):
        r = core(self, """
          const outs = [null, 42, "x", [], { type: "nope", date: "31/31/2026", amount_cents: "abc" }, { date: {}, tags: 5, custom: "x", id: "a b" },
                        Object.create(null)].map((raw) => G.normalizeEntry(raw, S));
          out(outs.map((o) => ({ p: o.problems, type: o.entry.type, cat: o.entry.category, funder: o.entry.funder, claim: o.entry.claim_status,
                                  method: o.entry.method, keys: Object.keys(o.entry).join(","), id: /^x[0-9a-z]+$/.test(o.entry.id) })));""")
        for o in r:
            self.assertEqual(o["type"], "expense")
            self.assertEqual(o["cat"], "books")          # the first expense category
            self.assertEqual((o["funder"], o["claim"], o["method"]), ("me", "none", "cash"))
            self.assertTrue(o["id"])
        self.assertEqual(r[0]["p"], ["expenses.err.date_required"])
        self.assertEqual(sorted(r[4]["p"]), ["expenses.err.amount", "expenses.err.date", "expenses.err.type"])

    def test_coercion_and_defaults(self):
        r = core(self, WITH_CUSTOM + """
          const d = "2026-09-02";
          const books = N({ type: "expense", date: d, category: "books", description: "  Big Book  ", amount: "$24.00", funder: "district",
            item: "Big Book", quantity: "2", unit_cost_cents: 1200, format: "Grapevine", tags: "a; b; A;  ", vendor: "Store\\nNorth",
            notes: "line1\\r\\nline2\\r", unknown_field: 1 });
          const qty = N({ type: "expense", date: d, category: "books", description: "x", quantity: 3, unit_cost_cents: 1250 });
          const mine = N({ type: "expense", date: d, description: "x", amount_cents: 100, funder: "me", claim_status: "submitted" });
          const direct = N({ type: "expense", date: d, description: "x", amount_cents: 100, funder: "area", method: "direct" });
          const seventh = N({ type: "expense", date: d, category: "contributions", description: "x", amount_cents: 500 });
          const rec = N({ type: "received", date: d, category: "reimbursement", description: "x", amount_cents: 5000, funder: "area", claim_status: "to_request", miles: 5 });
          const give = N({ type: "giveaway", date: d, amount_cents: 500, item: "GV", quantity: 5, giveaway: true });
          const hotel = N({ type: "expense", date: "2026-09-05", end_date: "2026-09-07", category: "lodging", description: "Hotel", amount_cents: 23800, nights: 5 });
          const helped = N({ type: "expense", date: d, category: "subscriptions", description: "x", amount_cents: 1500, sub_kind: "helped", person: "José R." });
          const neg = G.normalizeEntry({ type: "expense", date: d, description: "x", amount_cents: -500 }, S);
          const wrongCat = G.normalizeEntry({ type: "mileage", date: d, category: "books", miles: 10, rate: "0.14" }, S);
          const gv = N({ type: "expense", date: d, category: "giveaways", description: "x", amount_cents: 100 });
          const gvOff = N({ type: "expense", date: d, category: "giveaways", description: "x", amount_cents: 100, giveaway: false });
          const cust = N({ type: "expense", date: d, description: "x", custom: { cf_yes: "sí", cf_num: "12", cf_text: "  ", junk: null, "bad id!": 1 } }, S2);
          out({ books: [books.description, books.amount_cents, books.claim_status, books.format, books.tags, books.vendor, books.notes, "unknown_field" in books],
                qty: qty.amount_cents, mine: mine.claim_status, direct: direct.claim_status, seventh: [seventh.funder, seventh.claim_status],
                rec: [rec.claim_status, rec.funder, rec.miles, rec.method], give: [give.amount_cents, give.category, give.giveaway, give.funder],
                hotel: hotel.nights, helped: [helped.repaid, helped.funder, helped.claim_status],
                neg: [neg.entry.amount_cents, neg.problems], wrongCat: [wrongCat.entry.category, wrongCat.problems, wrongCat.entry.amount_cents],
                gv: [gv.giveaway, gvOff.giveaway], cust: cust.custom });""")
        self.assertEqual(r["books"], ["Big Book", 2400, "to_request", "gv", ["a", "b"], "Store North", "line1\nline2", False])
        self.assertEqual(r["qty"], 3750)                                  # 3 × $12.50
        self.assertEqual(r["mine"], "none")                               # self-supported: nothing to ask
        self.assertEqual(r["direct"], "none")                             # paid by the funder directly
        self.assertEqual(r["seventh"], ["me", "none"])                    # the category's defaults
        self.assertEqual(r["rec"], ["none", "area", "", ""])
        self.assertEqual(r["give"], [0, "given", False, ""])
        self.assertEqual(r["hotel"], 2)                                   # 5 → 7 September: 2 nights
        self.assertEqual(r["helped"], ["owed", "me", "none"])
        self.assertEqual(r["neg"], [500, ["expenses.warn.amount_negative"]])
        self.assertEqual(r["wrongCat"], ["mileage", ["expenses.warn.category_type"], 140])
        self.assertEqual(r["gv"], [True, False])
        self.assertEqual(r["cust"], {"cf_yes": True, "cf_num": 12})

    def test_normalizing_twice_changes_nothing(self):
        r = core(self, WITH_CUSTOM + NASTY + """
          const all = nastyLedger(S2).concat(G.exampleEntries("2026-09-27", S2));
          const again = all.map((e) => N(e, S2));
          out({ n: all.length, same: all.map((e, i) => JSON.stringify(e) === JSON.stringify(again[i])),
                order: all.every((e) => Object.keys(e).join() === Object.keys(G.FIELDS).join()) });""")
        self.assertGreater(r["n"], 30)
        self.assertTrue(all(r["same"]))
        self.assertTrue(r["order"])

    def test_validate(self):
        r = core(self, WITH_CUSTOM + """
          const d = "2026-09-10";
          const v = (raw, s) => G.validateEntry(N(raw, s), s || S).map((x) => x.field + ":" + x.key.replace("expenses.err.", ""));
          out({
            ok: v({ type: "expense", date: d, description: "Books", amount_cents: 100 }),
            none: v(null),
            dates: v({ type: "expense", date: d, end_date: "2026-09-01", description: "", category: "books" }),
            miles: v({ type: "mileage", date: d, rate: "0.14" }),
            odo: G.validateEntry({ ...N({ type: "mileage", date: d, rate: "0.14", miles: 5 }), odometer_start: 100, odometer_end: 90 }, S).map((x) => x.key),
            qty: v({ type: "giveaway", date: d, item: "GV" }),
            funder: v({ type: "expense", date: d, description: "x", funder: "zzz" }),
            cat: v({ type: "expense", date: d, description: "x", category: "nope" }),
            big: v({ type: "expense", date: d, description: "x", amount_cents: 100000000000 }),
            custom: v({ type: "expense", date: d, description: "x", custom: { cf_num: "abc", cf_date: "someday", cf_pick: "Z" } }, S2),
            paid: v({ type: "expense", date: d, description: "x", funder: "area", claim_status: "paid", claim_date: "2026-09-20", paid_date: "2026-09-15" }),
          });""")
        self.assertEqual(r["ok"], [])
        self.assertEqual(r["none"], ["date:date_required", "description:description_required"])
        self.assertEqual(r["dates"], ["end_date:end_before_start", "description:description_required"])
        self.assertEqual(r["miles"], ["miles:miles_required"])
        self.assertEqual(r["odo"], ["expenses.err.odometer"])
        self.assertEqual(r["qty"], ["quantity:quantity_required"])
        self.assertEqual(r["funder"], ["funder:funder_unknown"])
        self.assertEqual(r["cat"], ["category:category_unknown"])
        self.assertEqual(r["big"], ["amount_cents:amount_too_large"])
        self.assertEqual(r["custom"], ["custom:cf_num:custom_number", "custom:cf_date:custom_date", "custom:cf_pick:custom_choice"])
        self.assertEqual(r["paid"], ["paid_date:paid_before_claim"])


class CsvWrite(unittest.TestCase):
    HEADER = ("id,date,end_date,type,category,category_label,description,amount,signed_amount,funder,funder_name,claim_status,"
              "claim_date,claim_ref,paid_date,method,vendor,event,place,person,item,format,quantity,unit_cost,giveaway,miles,rate,"
              "from,to,round_trip,odometer_start,odometer_end,nights,attendees,sub_product,sub_term,sub_start,sub_end,sub_kind,"
              "repaid,receipt,receipt_ref,tags,notes,created,updated")

    def test_the_file(self):
        r = core(self, WITH_CUSTOM + """
          const a = N({ id: "xa", type: "expense", date: "2026-09-02", category: "books", description: 'He said "hi", ok', amount_cents: 2400,
            funder: "district", vendor: "=SUM(A1)", claim_ref: "-5", notes: "@home\\nline 2", tags: ["+1", "b"], giveaway: true,
            sub_start: "2026-01-31", sub_term: 1, created: "2026-09-02T10:00:00.000Z", custom: { cf_yes: false, cf_num: 2.5, cf_text: "=1+1" } }, S2);
          const b = N({ id: "xb", type: "received", date: "2026-09-03", category: "reimbursement", description: "Check", amount_cents: 5, funder: "area" }, S2);
          const m = N({ id: "xm", type: "mileage", date: "2026-09-04", miles: 12.3, rate: "0.655", funder: "me", from: "Home", to: "Tyler" }, S2);
          const csv = G.toCSV([a, b, m], S2, { lang: "es" });
          const rows = G.parseCSV(csv);
          const H = rows[0];
          const col = (row, name) => row[H.indexOf(name)];
          out({ bom: csv.charCodeAt(0) === 0xfeff, crlf: csv.split("\\r\\n").length, loneLF: /[^\\r]\\n/.test(csv.replace(/"[^"]*"/g, "")),
                head: csv.slice(1).split("\\r\\n")[0], end: csv.slice(-2) === "\\r\\n",
                quoted: csv.includes('"He said ""hi"", ok"'),
                a: ["amount", "signed_amount", "category_label", "funder_name", "vendor", "claim_ref", "notes", "tags", "giveaway", "sub_end", "created",
                    "custom:Approved?", "custom:Pages", "custom:Sponsor note, private"].map((k) => col(rows[1], k)),
                b: ["amount", "signed_amount", "giveaway", "funder_name", "claim_status"].map((k) => col(rows[2], k)),
                m: ["amount", "signed_amount", "miles", "rate", "description", "round_trip", "funder_name"].map((k) => col(rows[3], k)),
                en: G.parseCSV(G.toCSV([a], S2, { lang: "en" }))[1][5] });""")
        self.assertTrue(r["bom"])
        self.assertTrue(r["end"])
        self.assertEqual(r["crlf"], 5)                   # header + 3 rows + the final line end
        self.assertFalse(r["loneLF"])                    # a bare LF only inside quotes
        self.assertEqual(r["head"], self.HEADER + ',"custom:Sponsor note, private",custom:Pages,custom:Approved?,custom:Revisado el,custom:Size')
        self.assertTrue(r["quoted"])
        self.assertEqual(r["a"], ["24.00", "-24.00", "Libros y literatura", "Mi distrito", "'=SUM(A1)", "'-5", "'@home\nline 2", "'+1; b", "yes",
                                  "2026-02-28", "2026-09-02T10:00:00.000Z", "no", "2.5", "'=1+1"])
        self.assertEqual(r["b"], ["0.05", "0.05", "", "Área 65 (NETA 65)", "none"])
        # 12.3 × 0.655 = $8.0565 → 8.06; spending is negative; numbers are never guarded
        self.assertEqual(r["m"], ["8.06", "-8.06", "12.3", "0.655", "Home → Tyler", "", "Yo (autofinanciado)"])
        self.assertEqual(r["en"], "Books & literature")


class RoundTrip(unittest.TestCase):
    """planImport(parseCSV(toCSV(E))) into an empty ledger gives back E exactly."""

    def _run(self, transform: str, opts: str = "{}"):
        return core(self, WITH_CUSTOM + NASTY + r"""
          const E = nastyLedger(S2);
          const DATE_COLS = ["date", "end_date", "claim_date", "paid_date", "sub_start", "sub_end", "custom:Revisado el", "custom:Reviewed on"];
          const NUM_COLS = ["amount", "signed_amount", "quantity", "unit_cost", "miles", "rate", "odometer_start", "odometer_end", "custom:Pages"];
          const q = (v, d) => (v.includes(d) || /["\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v);
          // a spreadsheet re-saving the file its own way
          function resave(csv, { delim, eol, bom, date, decimal }) {
            const rows = G.parseCSV(csv), H = rows[0];
            const body = rows.map((row, r) => row.map((v, c) => {
              if (r && DATE_COLS.includes(H[c]) && /^\d{4}-\d{2}-\d{2}$/.test(v)) v = date(v.slice(0, 4), v.slice(5, 7), v.slice(8, 10));
              if (r && NUM_COLS.includes(H[c]) && decimal === ",") v = v.replace(".", ",");
              return q(v, delim);
            }).join(delim));
            return (bom ? "﻿" : "") + body.join(eol) + eol;
          }
          const results = {};
          for (const lang of ["en", "es"]) {
            let csv = G.toCSV(E, S2, { lang });
            csv = (""" + transform + r""")(csv);
            const plan = G.planImport(G.parseCSV(csv), [], S2, """ + opts + r""");
            const got = plan.add.map((e) => JSON.stringify(e)), want = E.map((e) => JSON.stringify(e));
            results[lang] = { n: E.length, add: plan.add.length, errors: plan.errors, warnings: plan.warnings.length, skip: plan.skip.length,
              news: plan.newCategories.length + plan.newFunders.length + plan.newCustomFields.length,
              diff: want.map((w, i) => (w === got[i] ? null : { want: JSON.parse(w), got: got[i] ? JSON.parse(got[i]) : null })).filter(Boolean).slice(0, 2) };
          }
          out(results);""")

    def _check(self, res):
        for lang, r in res.items():
            with self.subTest(lang=lang):
                self.assertEqual(r["errors"], [])
                self.assertEqual((r["add"], r["skip"], r["news"]), (r["n"], 0, 0))
                self.assertEqual(r["diff"], [])

    def test_the_law(self):
        self._check(self._run("(csv) => csv"))

    def test_through_excel_in_spanish(self):
        # semicolons, decimal commas, day-first dates, old-Mac CR line ends, no BOM
        self._check(self._run('(csv) => resave(csv, { delim: ";", eol: "\\r", bom: false, decimal: ",", date: (y, m, d) => d + "/" + m + "/" + y })',
                              '{ dateOrder: "dmy" }'))

    def test_through_excel_in_english(self):
        # US dates without leading zeros, LF line ends, BOM kept
        self._check(self._run('(csv) => resave(csv, { delim: ",", eol: "\\n", bom: true, decimal: ".", date: (y, m, d) => +m + "/" + +d + "/" + y })'))

    def test_tabs(self):
        self._check(self._run('(csv) => resave(csv, { delim: "\\t", eol: "\\r\\n", bom: true, decimal: ".", date: (y, m, d) => y + "-" + m + "-" + d })'))

    def test_into_a_ledger_without_the_custom_fields(self):
        # the only exception to the law: custom fields the ledger doesn't know come back as text fields
        r = core(self, WITH_CUSTOM + NASTY + """
          const E = nastyLedger(S2);
          const plan = G.planImport(G.parseCSV(G.toCSV(E, S2, { lang: "en" })), [], S, {});
          const strip = (e) => { const c = { ...e }; delete c.custom; return JSON.stringify(c); };
          out({ same: plan.add.every((e, i) => strip(e) === strip(E[i])), n: plan.add.length,
                fields: plan.newCustomFields.map((f) => [f.label, f.type]),
                sample: plan.add[1].custom, errors: plan.errors });""")
        self.assertTrue(r["same"])
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["fields"], [["Sponsor note, private", "text"], ["Pages", "text"], ["Approved?", "text"],
                                       ["Reviewed on", "text"], ["Size", "text"]])
        self.assertEqual(r["sample"], {"cf_sponsor_note_private": 'Quote "inside"', "cf_pages": "1.5", "cf_approved": "no",
                                       "cf_reviewed_on": "2026-02-28", "cf_size": "A"})


class CsvRead(unittest.TestCase):
    def test_detection(self):
        r = core(self, r"""
          const p = (t, o) => { const r = G.parseCSV(t, o); return { rows: plain(r), delim: r.delimiter || null, un: !!r.unterminated, err: r.error || null }; };
          out({
            bomCrlf: p("﻿a,b\r\n1,2\r\n"), lf: p("a,b\n1,2\n"), cr: p("a,b\r1,2\r"), mixed: p("a,b\r\n1,2\n3,4\r5,6"),
            semi: p("a;b;c\n1,5;2;3\n"), tab: p("a\tb\n1\t2"), sepLine: p("sep=;\r\na;b\r\n1;2\r\n"), tie: p("a;b,c\n"),
            quoted: p('a,b\r\n"x, ""y""\r\nz",2\r\n'), quotedHeader: p('"a;x",b,c\n1,2,3'),
            blank: p("a,b\r\n\r\n,\r\n  \r\n1,2\r\n\r\n"), ragged: p("a,b,c\n1\n1,2,3,4\n"),
            trailing: p("a,b,\n1,2,\n"), eofDelim: p("a,b\n1,"), unterminated: p('a,b\n"open,2\n3,4'),
            afterQuote: p('a,b\n"x"y,2\n'), innerQuote: p('a,b\n5" disk,2\n'), empty: p(""), notText: p(null),
            utf8: p(new Uint8Array([0xef, 0xbb, 0xbf, 0x61, 0x2c, 0xc3, 0xb1, 0x0a])),
            cp1252: p(new Uint8Array([0x61, 0x2c, 0xf1, 0x0a])),
          });""")
        self.assertEqual((r["bomCrlf"]["rows"], r["bomCrlf"]["delim"]), ([["a", "b"], ["1", "2"]], ","))
        for k in ("lf", "cr"):
            self.assertEqual(r[k]["rows"], [["a", "b"], ["1", "2"]], k)
        self.assertEqual(r["mixed"]["rows"], [["a", "b"], ["1", "2"], ["3", "4"], ["5", "6"]])
        self.assertEqual((r["semi"]["rows"], r["semi"]["delim"]), ([["a", "b", "c"], ["1,5", "2", "3"]], ";"))
        self.assertEqual((r["tab"]["rows"], r["tab"]["delim"]), ([["a", "b"], ["1", "2"]], "\t"))
        self.assertEqual((r["sepLine"]["rows"], r["sepLine"]["delim"]), ([["a", "b"], ["1", "2"]], ";"))
        self.assertEqual(r["tie"]["delim"], ",")
        self.assertEqual(r["quoted"]["rows"], [["a", "b"], ['x, "y"\r\nz', "2"]])
        self.assertEqual(r["quotedHeader"]["delim"], ",")           # the ; inside quotes doesn't count
        self.assertEqual(r["blank"]["rows"], [["a", "b"], ["1", "2"]])
        self.assertEqual(r["ragged"]["rows"], [["a", "b", "c"], ["1"], ["1", "2", "3", "4"]])
        self.assertEqual(r["trailing"]["rows"], [["a", "b", ""], ["1", "2", ""]])
        self.assertEqual(r["eofDelim"]["rows"], [["a", "b"], ["1", ""]])
        self.assertEqual((r["unterminated"]["rows"], r["unterminated"]["un"]), ([["a", "b"], ["open,2\n3,4"]], True))
        self.assertEqual(r["afterQuote"]["rows"], [["a", "b"], ["xy", "2"]])
        self.assertEqual(r["innerQuote"]["rows"], [["a", "b"], ['5" disk', "2"]])
        self.assertEqual((r["empty"]["rows"], r["empty"]["err"]), ([], None))
        self.assertEqual(r["notText"]["err"], "expenses.err.empty")
        self.assertEqual(r["utf8"]["rows"], [["a", "ñ"]])
        self.assertEqual(r["cp1252"]["rows"], [["a", "ñ"]])            # Excel's "CSV" (Windows-1252) still reads

    def test_import_never_throws_on_garbage(self):
        r = core(self, r"""
          let seed = 42;
          const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
          const bytes = (n) => { let t = ""; for (let i = 0; i < n; i++) t += String.fromCharCode(Math.floor(rnd() * 256)); return t; };
          const backup = G.toBackup(G.emptyState(CONFIG));
          const inputs = [bytes(4000), bytes(60), bytes(3), backup, '{"a":1}', "[1,2,3]", "", "   ", "﻿", "a", "id,date,amount", "id,date,amount\r\n",
            "a,b\n1\n1,2,3,4\n", "type,date,amount\nexpense\n,,,\nfoo,bar,baz\n", "PK\u0003\u0004\u0014\u0000 zip", "<html><body>hi</body></html>",
            "\u0000\u0001\u0002", "��,�", null, undefined, 42, {}, [], [[]], [[1, 2], [3]], [["id", "date"], [null, {}]], "id,date\n" + "x,y\n".repeat(3),
            new Uint8Array([1, 2, 3, 250, 251]),
            [["type", "date", "amount"], ["expense", "2026-09-01", "abc"], ["nope", "2026-09-01", "1"], ["expense", "", "1"], ["expense", "2026-02-30", "1"]]];
          const res = [];
          for (const x of inputs) {
            for (const mode of ["rows", "text"]) {
              let plan, threw = null;
              try { plan = G.planImport(mode === "rows" && typeof x === "string" ? G.parseCSV(x) : x, [null, "junk", { id: 5 }], mode === "rows" ? S : null, {}); }
              catch (e) { threw = String(e && e.stack || e); }
              res.push({ threw, errors: plan ? plan.errors.map((e) => e.message_key) : null, rows: plan ? plan.errors.map((e) => e.row) : null,
                         mapping: plan ? plan.needsMapping : null, add: plan ? plan.add.length : null });
            }
          }
          out({ res, keys: G.MESSAGE_KEYS });""")
        keys = set(r["keys"])
        for i, x in enumerate(r["res"]):
            with self.subTest(case=i):
                self.assertIsNone(x["threw"])
                for k in x["errors"]:
                    self.assertIn(k, keys)
                    self.assertTrue(k.startswith("expenses.err."), k)
                self.assertTrue(x["errors"] or x["mapping"] or x["add"] is not None)
        res = r["res"]
        at = lambda i: res[2 * i]                                             # noqa: E731 (the "rows" run of input i)
        self.assertEqual(at(0)["errors"], ["expenses.err.not_csv"])          # random bytes
        self.assertEqual(at(3)["errors"], ["expenses.err.looks_like_backup"])
        self.assertEqual(at(4)["errors"], ["expenses.err.not_csv"])
        self.assertEqual(at(6)["errors"], ["expenses.err.empty"])
        self.assertEqual(at(10)["errors"], ["expenses.err.no_rows"])          # a header only
        self.assertEqual(at(14)["errors"], ["expenses.err.not_csv"])         # a zip (.xlsx)
        self.assertEqual(at(12)["mapping"], True)                             # somebody else's columns: ask
        self.assertEqual(at(28)["errors"], ["expenses.err.amount", "expenses.err.type", "expenses.err.date_required", "expenses.err.date"])
        self.assertEqual(at(28)["rows"], [2, 3, 4, 5])                        # spreadsheet row numbers (the header is row 1)
        self.assertEqual(at(28)["add"], 0)

    def test_limits_and_speed(self):
        r = core(self, WITH_CUSTOM + NASTY + r"""
          const big = G.planImport("a".repeat(10 * 1024 * 1024 + 1), [], S, {});
          const head = "type,date,amount\n";
          const tooMany = G.planImport(head + "expense,2026-09-01,1\n".repeat(20001), [], S, {});
          const justRight = G.planImport(head + "expense,2026-09-01,1\n".repeat(20000), [], S, { allowDuplicates: true });
          // 20,000 varied entries: write, read, plan into an empty ledger and against itself
          const base = nastyLedger(S2), E = [];
          for (let i = 0; i < 20000; i++) E.push({ ...base[i % base.length], id: "p" + i.toString(36) });
          const t0 = Date.now();
          const csv = G.toCSV(E, S2, { lang: "en" });
          const t1 = Date.now();
          const rows = G.parseCSV(csv);
          const t2 = Date.now();
          const plan = G.planImport(rows, [], S2, {});
          const t3 = Date.now();
          const again = G.planImport(rows, E, S2, {});
          const t4 = Date.now();
          out({ big: big.errors.map((e) => e.message_key), tooMany: tooMany.errors.map((e) => e.message_key), justRight: [justRight.errors.length, justRight.add.length],
                n: plan.add.length, errors: plan.errors.length, same: again.skip.filter((s) => s.reason === "same").length,
                ms: { write: t1 - t0, parse: t2 - t1, plan: t3 - t2, replan: t4 - t3 }, mb: +(csv.length / 1048576).toFixed(1) });""", timeout=300)
        self.assertEqual(r["big"], ["expenses.err.too_big"])
        self.assertEqual(r["tooMany"], ["expenses.err.too_many_rows"])
        self.assertEqual(r["justRight"], [0, 20000])
        self.assertEqual((r["n"], r["errors"], r["same"]), (20000, 0, 20000))
        ms = r["ms"]
        print(f"\n  20,000 entries ({r['mb']} MB): write {ms['write']} ms, parse {ms['parse']} ms, plan {ms['plan']} ms, re-plan {ms['replan']} ms",
              file=sys.stderr)
        # about a second on a laptop; generous here so a busy CI machine doesn't fail it
        self.assertLess(ms["write"] + ms["parse"] + ms["plan"], 6000)


class ImportValues(unittest.TestCase):
    def test_somebody_elses_spreadsheet(self):
        r = core(self, r"""
          const text = "Fecha;Concepto;Importe;Categoría;Notas;Extra\r\n" +
            "46000;Comida del taller;(42,00);Comidas;;Mesa 3\r\n" +
            "27/09/2026;Reembolso del distrito;120,50;Reembolso;cheque 12;\r\n" +
            "28/09/2026;Gasolina;-35,10;Gasolina;;x\r\n" +
            "29/09/2026;Libros;-1.234,50;LIBROS Y LITERATURA;;\r\n" +
            "30/09/2026;Sin monto;;;;\r\n";
          const rows = G.parseCSV(text);
          const ask = G.planImport(rows, [], S, {});
          const plan = G.planImport(rows, [], S, { mapping: { date: 0, description: "Concepto", amount: 2, category: 3, notes: "notas" }, dateOrder: "dmy" });
          const noDate = G.planImport(rows, [], S, { mapping: { description: 1, amount: 2 } });
          const miles = G.planImport("Date,Trip,Miles\n9/27/2026,Assembly,184.6\n", [], S, { mapping: { date: 0, description: 1, miles: 2 } });
          const pick = (e) => [e.type, e.date, e.description, e.amount_cents, e.category, e.funder, e.notes];
          out({ ask: [ask.needsMapping, ask.headers, ask.sample.length, ask.delimiter, ask.errors],
                add: plan.add.map(pick), errors: plan.errors, cats: plan.newCategories.map((c) => [c.id, c.label, c.type, c.template]),
                decimal: plan.decimal, noDate: noDate.errors.map((e) => e.message_key),
                miles: miles.add.map((e) => [e.type, e.miles, e.rate, e.amount_cents, e.date]) });""")
        self.assertEqual(r["ask"], [True, ["Fecha", "Concepto", "Importe", "Categoría", "Notas", "Extra"], 5, ";", []])
        self.assertEqual(r["decimal"], ",")                                   # a ; file: decimal commas
        self.assertEqual(r["add"], [
            # Excel serial 46000 = 2025-12-09; (42,00) is spending; "Comidas" is the Spanish label of meals
            ["expense", "2025-12-09", "Comida del taller", 4200, "meals", "me", "Extra: Mesa 3"],
            # the file has negative amounts, so a positive one is money received
            ["received", "2026-09-27", "Reembolso del distrito", 12050, "reimbursement", "", "cheque 12"],
            ["expense", "2026-09-28", "Gasolina", 3510, "c_gasolina", "me", "Extra: x"],
            ["expense", "2026-09-29", "Libros", 123450, "books", "me", ""],
        ])
        self.assertEqual(r["errors"], [{"row": 6, "field": "amount", "message_key": "expenses.err.amount"}])
        self.assertEqual(r["cats"], [["c_gasolina", "Gasolina", "expense", "general"]])
        self.assertEqual(r["noDate"], ["expenses.err.mapping_required"])
        # miles only: the default rate (0.14): 184.6 × 0.14 = $25.844 → 2584
        self.assertEqual(r["miles"], [["mileage", 184.6, "0.14", 2584, "2026-09-27"]])

    def test_our_file_written_by_hand(self):
        r = core(self, r"""
          const text = [
            "Notes , Type,  Date ,amount,category,category_label,funder,funder_name,giveaway,signed_amount,description,foo,vendor",
            "'=SUM(A1),expense,2026-09-01,$1234.50,zz_old,Libros y literatura,district,Whatever,Sí,,Books,ignored,''=x",
            "a,expense,46000,(12.00),c_custom1,Retiro de servicio,f_d22,District 22,x,,Retreat,,'hello",
            "b,,2026-09-02,,,,,Área 65 (NETA 65),no,-5.00,Parking,,",
            "c,,2026-09-03,,reimbursement,,,,,7.00,Check,,",
            "d,expense,2026-09-04,1,books,,,,TRUE,,x,,",
          ].join("\n");
          const plan = G.planImport(text, [], S, {});
          out({ errors: plan.errors, add: plan.add.map((e) => [e.type, e.date, e.amount_cents, e.category, e.funder, e.giveaway, e.notes, e.vendor]),
                cats: plan.newCategories.map((c) => [c.id, c.label, c.type]), funders: plan.newFunders.map((f) => [f.id, f.name, f.kind]),
                warnings: plan.warnings.map((w) => w.message_key) });""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["add"], [
            ["expense", "2026-09-01", 123450, "books", "district", True, "=SUM(A1)", "'=x"],        # the label matched (ES); the guard ' removed once
            ["expense", "2025-12-09", 1200, "c_custom1", "f_d22", True, "a", "'hello"],             # a new category and funder keep their ids
            ["expense", "2026-09-02", 500, "books", "area", False, "b", ""],                        # no type: -5.00 is spending; the funder by name
            ["received", "2026-09-03", 700, "reimbursement", "", False, "c", ""],                   # +7.00 is money received
            ["expense", "2026-09-04", 100, "books", "me", True, "d", ""],
        ])
        self.assertEqual(r["cats"], [["c_custom1", "Retiro de servicio", "expense"]])
        self.assertEqual(r["funders"], [["f_d22", "District 22", "other"]])


class DedupeMerge(unittest.TestCase):
    def test_plan_and_apply(self):
        r = core(self, r"""
          const A = N({ id: "xa", type: "expense", date: "2026-09-01", description: "Big Book", amount_cents: 2400, updated: "2026-09-01T00:00:00.000Z", created: "2026-09-01T00:00:00.000Z" });
          const B = N({ id: "xb", type: "expense", date: "2026-09-02", description: "Hotel", amount_cents: 9000, updated: "2026-09-02T00:00:00.000Z", created: "2026-09-02T00:00:00.000Z" });
          const C = N({ id: "xc", type: "received", date: "2026-09-03", category: "reimbursement", description: "Check", amount_cents: 5000, funder: "area", updated: "2026-09-05T00:00:00.000Z", created: "2026-09-03T00:00:00.000Z" });
          const state = { v: 1, entries: [A, B, C], settings: S, meta: { lastBackup: null, lastExport: null, created: "2026-01-01T00:00:00.000Z" } };
          const before = JSON.stringify(state);
          const B2 = { ...B, description: "Hotel (2 nights)", updated: "2026-09-10T00:00:00.000Z" };
          const C2 = { ...C, description: "Old copy", updated: "2026-09-04T00:00:00.000Z" };
          const X = N({ id: "xn", type: "expense", date: "2026-09-05", description: "Copies", amount_cents: 450, category: "c_new", created: "2026-09-05T00:00:00.000Z" });
          const dupOfA = { ...A, id: "", description: "  big   BOOK " };
          const fresh = { ...N({ type: "expense", date: "2026-09-06", description: "Stamps", amount_cents: 300 }), id: "" };
          let csv = G.toCSV([A, B2, C2, X, dupOfA, fresh, { ...X, description: "again" }], S, { lang: "en" });
          csv = csv.replace(",c_new,c_new,", ",c_new,New things,");
          const plan = G.planImport(csv, state.entries, S, {});
          const merged = G.applyImport(state, plan, { mode: "merge" });
          const withDups = G.applyImport(state, plan, { mode: "merge", includeDuplicates: true });
          const replaced = G.applyImport(state, plan, { mode: "replace" });
          const allow = G.planImport(csv, state.entries, S, { allowDuplicates: true });
          out({ add: plan.add.map((e) => e.description), update: plan.update.map((e) => [e.id, e.description]),
                skip: plan.skip.map((s) => [s.row, s.reason, s.message_key]), dups: plan.duplicates.map((e) => e.description),
                all: plan.all.length, merged: merged.entries.map((e) => e.description), withDups: withDups.entries.length,
                replaced: replaced.entries.map((e) => e.description), allow: allow.add.length, untouched: JSON.stringify(state) === before,
                cat: merged.settings.categories.filter((c) => c.id === "c_new").map((c) => [c.label, c.type, c.builtin]),
                lastImport: typeof merged.meta.lastImport, created: merged.meta.created });""")
        self.assertEqual(r["add"], ["Copies", "Stamps"])
        self.assertEqual(r["update"], [["xb", "Hotel (2 nights)"]])
        self.assertEqual(r["skip"], [[2, "same", "expenses.warn.skip_same"], [4, "older", "expenses.warn.skip_older"],
                                     [6, "duplicate", "expenses.warn.skip_duplicate"], [8, "duplicate_id", "expenses.warn.skip_duplicate_id"]])
        self.assertEqual(r["dups"], ["big   BOOK"])                           # the same fingerprint as A (case and spaces ignored)
        self.assertEqual(r["all"], 6)
        self.assertEqual(r["merged"], ["Big Book", "Hotel (2 nights)", "Check", "Copies", "Stamps"])
        self.assertEqual(r["withDups"], 6)
        self.assertEqual(r["replaced"], ["Big Book", "Hotel (2 nights)", "Old copy", "Copies", "big   BOOK", "Stamps"])
        self.assertEqual(r["allow"], 3)
        self.assertTrue(r["untouched"])                                       # applyImport returns a new state
        self.assertEqual(r["cat"], [["New things", "expense", False]])
        self.assertEqual(r["lastImport"], "string")
        self.assertEqual(r["created"], "2026-01-01T00:00:00.000Z")


# A month of service, worked out by hand below. SP = the settings plus a person funder (José R.).
LEDGER = r"""
const SP = plain(S);
SP.funders.push({ id: "p_jose", kind: "person", name: "José R.", hidden: false, order: 9, builtin: false });
SP.profile = { name: "Maria G.", position: "GVR", district: "District 22", email: "" };
const L = [
  ["a", { type: "expense", date: "2026-09-02", category: "books", description: "Big Book", amount_cents: 2400, funder: "district", claim_status: "to_request", method: "card", receipt: "paper" }],
  ["b", { type: "expense", date: "2026-09-05", end_date: "2026-09-07", category: "lodging", description: "Hotel", amount_cents: 23800, funder: "district", claim_status: "submitted", claim_date: "2026-09-06", method: "card" }],
  ["c", { type: "mileage", date: "2026-09-05", from: "Home", to: "Tyler", round_trip: true, miles: 184.6, rate: "0.14", funder: "district", claim_status: "to_request", event: "Fall Assembly", tags: ["assembly"] }],
  ["d", { type: "expense", date: "2026-09-10", category: "meals", description: "Pizza", amount_cents: 4200, funder: "group", claim_status: "to_request", method: "cash" }],
  ["e", { type: "expense", date: "2026-09-05", category: "travel", description: "Parking", amount_cents: 800, funder: "me" }],
  ["f", { type: "expense", date: "2026-09-01", category: "registration", description: "Registration", amount_cents: 1500, funder: "district", claim_status: "paid", claim_date: "2026-09-02", paid_date: "2026-09-15" }],
  ["g", { type: "expense", date: "2026-09-03", category: "giveaways", description: "GV bulk", item: "Grapevine", format: "gv", quantity: 20, amount_cents: 5000, giveaway: true, funder: "area", claim_status: "paid" }],
  ["h", { type: "expense", date: "2026-09-06", category: "lodging", description: "Hotel paid by the Area", amount_cents: 12000, funder: "area", method: "direct" }],
  ["i", { type: "expense", date: "2026-09-09", category: "contributions", description: "7th Tradition", amount_cents: 500 }],
  ["j", { type: "expense", date: "2026-09-12", category: "subscriptions", description: "LV for José", person: "José R.", sub_kind: "helped", sub_product: "lv_online", sub_term: 12, sub_start: "2026-09-12", amount_cents: 1500, funder: "p_jose" }],
  ["k", { type: "expense", date: "2026-09-12", category: "subscriptions", description: "Gift sub for Maria G.", person: "Maria G.", sub_kind: "gift", sub_product: "gv_print", sub_term: 12, sub_start: "2026-09-12", amount_cents: 3600, funder: "me" }],
  ["l", { type: "received", date: "2026-09-20", category: "reimbursement", description: "Area check", amount_cents: 5000, funder: "area" }],
  ["m", { type: "received", date: "2026-09-08", category: "advance", description: "Group advance", amount_cents: 5000, funder: "group" }],
  ["n", { type: "received", date: "2026-09-25", category: "repayment", description: "José paid part", amount_cents: 500, funder: "p_jose" }],
  ["o", { type: "stock", date: "2026-09-04", item: "grapevine ", format: "gv", quantity: 15, funder: "area", description: "Back issues" }],
  ["p", { type: "giveaway", date: "2026-09-06", item: "GRAPEVINE", format: "gv", quantity: 12, event: "Fall Assembly" }],
  ["q", { type: "giveaway", date: "2026-09-10", item: "La Viña", format: "lv", quantity: 30, event: "Workshop" }],
  ["r", { type: "expense", date: "2026-09-11", category: "printing", description: "Copies", amount_cents: 450, funder: "district", claim_status: "denied" }],
  ["s", { type: "expense", date: "2026-08-31", category: "other", description: "Outside the month", amount_cents: 9900, funder: "me" }],
].map(([id, raw]) => N({ id, ...raw, created: raw.date + "T12:00:00.000Z" }, SP));
const SEPT = { from: "2026-09-01", to: "2026-09-30" };
const ids = (list) => list.map((e) => e.id).join("");
"""


class Totals(unittest.TestCase):
    def test_summary(self):
        r = core(self, LEDGER + "out({ sept: G.summary(L, SP, SEPT), all: G.summary(L, SP, {}) });")
        s = r["sept"]
        # spent (not "direct" h): a 2400 + b 23800 + c 2584 (184.6 mi × $0.14) + d 4200 + e 800 + f 1500 + g 5000
        #                         + i 500 + j 1500 + k 3600 + r 450 = 46334
        self.assertEqual(s["spent_cents"], 46334)
        self.assertEqual(s["self_cents"], 5350)          # e 800 + i 500 + k 3600 + r 450 (denied)
        self.assertEqual(s["claimable_cents"], 40984)    # a + b + c + d + f + g + j; 5350 + 40984 = 46334
        self.assertEqual(s["direct_cents"], 12000)       # h, paid by the Area directly
        self.assertEqual(s["received_cents"], 10500)     # l 5000 + m 5000 + n 500
        self.assertEqual(s["owed_cents"], 29784)         # district 28784 + José 1000 (see test_funder_balances)
        self.assertEqual((s["miles"], s["mileage_cents"]), (184.6, 2584))
        self.assertEqual((s["items_given"], s["items_bought"], s["items_received"], s["items_on_hand"]), (42, 20, 15, 23))
        self.assertEqual(s["count"], 18)
        self.assertEqual([[c["id"], c["cents"], c["count"]] for c in s["by_category"]], [
            ["lodging", 23800, 1], ["subscriptions", 5100, 2], ["giveaways", 5000, 1], ["meals", 4200, 1], ["mileage", 2584, 1],
            ["books", 2400, 1], ["registration", 1500, 1], ["travel", 800, 1], ["contributions", 500, 1], ["printing", 450, 1]])
        self.assertEqual(s["by_month"], [{"ym": "2026-09", "spent": 46334, "received": 10500}])
        a = r["all"]                                      # + s: $99.00 self-supported on 31 August
        self.assertEqual((a["spent_cents"], a["self_cents"], a["count"]), (56234, 15250, 19))
        self.assertEqual(a["by_month"], [{"ym": "2026-08", "spent": 9900, "received": 0}, {"ym": "2026-09", "spent": 46334, "received": 10500}])

    def test_funder_balances_and_people(self):
        r = core(self, LEDGER + r"""
          const cols = ["funder", "claimed_cents", "to_request_cents", "submitted_cents", "paid_cents", "denied_cents", "received_cents", "settled_cents", "balance_cents", "count"];
          const rows = (list) => list.map((b) => cols.map((k) => b[k]));
          const repaid = L.map((e) => (e.id === "j" ? { ...e, repaid: "repaid" } : e));
          const forgiven = L.map((e) => (e.id === "j" ? { ...e, repaid: "forgiven" } : e));
          const areaMarkedPaidNoCheck = L.filter((e) => e.id !== "l");
          const onMe = [N({ id: "t1", type: "expense", date: "2026-09-14", category: "subscriptions", description: "GV for Ana", person: "Ana P.", sub_kind: "helped", amount_cents: 2000 }, SP),
                        N({ id: "t2", type: "received", date: "2026-09-20", category: "repayment", description: "Ana", person: "ana p.", amount_cents: 500 }, SP)];
          out({ sept: rows(G.funderBalances(L, SP, SEPT)),
                people: G.peopleOwed(L, SP, SEPT).map((p) => [p.funder, p.person, p.owed_cents, p.claimed_cents, p.received_cents, ids(p.entries)]),
                repaid: G.peopleOwed(repaid, SP, SEPT).length, forgiven: [G.peopleOwed(forgiven, SP, SEPT).length, G.summary(forgiven, SP, SEPT).self_cents],
                area: rows(G.funderBalances(areaMarkedPaidNoCheck, SP, SEPT)).filter((x) => x[0] === "area"),
                onMe: G.peopleOwed(onMe, SP).map((p) => [p.funder, p.person, p.owed_cents, ids(p.entries)]),
                onMeSummary: [G.summary(onMe, SP, {}).owed_cents, G.summary(onMe, SP, {}).claimable_cents] });""")
        self.assertEqual(r["sept"], [
            # area: g $50 asked and marked paid; its $50 check (l) is the same money: balance 0; h (direct) is not a claim
            ["area", 5000, 0, 0, 5000, 0, 5000, 5000, 0, 2],
            # district: a 2400 + b 23800 + c 2584 + f 1500 = 30284 asked; f paid → settled 1500; r (denied) is not asked
            ["district", 30284, 4984, 23800, 1500, 450, 0, 1500, -28784, 5],
            # the group advanced $50 (m) and d cost $42: you hold $8 of theirs
            ["group", 4200, 4200, 0, 0, 0, 5000, 0, 800, 2],
            # José: $15 helped purchase, paid back $5
            ["p_jose", 1500, 1500, 0, 0, 0, 500, 0, -1000, 2],
        ])
        self.assertEqual(r["people"], [["p_jose", "José R.", 1000, 1500, 500, "j"]])
        self.assertEqual(r["repaid"], 0)                  # marked repaid: settled even without the rest of the money recorded
        self.assertEqual(r["forgiven"], [0, 6850])        # forgiven: no longer owed, and it becomes self-supported (5350 + 1500)
        self.assertEqual(r["area"], [["area", 5000, 0, 0, 5000, 0, 0, 5000, 0, 1]])   # marked paid, check not recorded: still settled
        # a helped purchase left on "me": grouped by the person's name (accents / case ignored)
        self.assertEqual(r["onMe"], [["", "Ana P.", 1500, "t1"]])
        self.assertEqual(r["onMeSummary"], [1500, 2000])

    def test_inventory_and_events(self):
        r = core(self, LEDGER + "out({ inv: G.inventory(L, { to: SEPT.to }), ev: G.eventGiveaways(L, SEPT), before: G.inventory(L, { to: '2026-09-05' }) });")
        gv, lv = r["inv"]
        self.assertEqual([gv[k] for k in ("item", "format", "bought_qty", "received_qty", "given_qty", "on_hand", "cost_cents", "avg_unit_cents", "negative")],
                         ["Grapevine", "gv", 20, 15, 12, 23, 5000, 250, False])     # 20 + 15 − 12 = 23; $50 / 20 = $2.50
        self.assertEqual(gv["events"], [{"event": "Fall Assembly", "qty": 12}])
        self.assertEqual((gv["first_date"], gv["last_date"]), ("2026-09-03", "2026-09-06"))
        self.assertEqual([lv[k] for k in ("item", "on_hand", "negative", "avg_unit_cents")], ["La Viña", -30, True, 0])   # given more than recorded: flagged
        self.assertEqual([[e["event"], e["total_qty"], e["items"]] for e in r["ev"]], [
            ["Workshop", 30, [{"item": "La Viña", "format": "lv", "qty": 30}]],
            ["Fall Assembly", 12, [{"item": "GRAPEVINE", "format": "gv", "qty": 12}]]])
        self.assertEqual([i["on_hand"] for i in r["before"]], [35])            # as of 5 September: 20 + 15, nothing given yet

    def test_renewals_stale_claims_budgets(self):
        r = core(self, LEDGER + r"""
          const sub = (id, person, product, start, term, kind) => N({ id, type: "expense", date: start, category: "subscriptions", description: "Sub",
            person, sub_product: product, sub_start: start, sub_term: term, sub_kind: kind || "gift", amount_cents: 3600 }, SP);
          const R = [sub("r1", "Maria G.", "gv_print", "2025-10-20", 12), sub("r2", "", "lv_print", "2025-09-10", 12, "self"),
                     sub("r3", "Luis M.", "gv_print", "2025-08-01", 12), sub("r4", "Ana P.", "gv_online", "2025-06-01", 12),
                     sub("r5", "ana p.", "gv_online", "2026-06-01", 12), sub("r6", "Rosa T.", "lv_complete", "2024-11-15", 24),
                     sub("r7", "Juan S.", "gv_print", "2025-12-26", 12)];
          const B = [{ id: "b1", funder: "district", year: 2026, amount_cents: 50000 }, { id: "b2", funder: "me", amount_cents: 5000 },
                     { id: "b3", amount_cents: 100000, from: "2026-09-01", to: "2026-09-30" }, { id: "b4", funder: "area", year: 2026, amount_cents: 20000 },
                     { id: "b5", funder: "district", category: "lodging", year: 2026, amount_cents: 30000 }, { id: "b6", funder: "group", amount_cents: 0 }];
          out({ r60: G.renewals(R, "2026-09-27", 60).map((x) => [x.entry.id, x.sub_end, x.days_left]),
                r90: G.renewals(R, "2026-09-27", 90).map((x) => x.entry.id).join(""),
                stale: G.staleClaims(L, "2026-10-20", 30).map((x) => [x.entry.id, x.days]), fresh: G.staleClaims(L, "2026-10-01").length,
                budgets: G.budgets(L, { ...SP, budgets: B }, "2026-09-27").map((b) => [b.budget.id, b.from, b.to, b.used_cents, b.left_cents, b.pct, b.over]) });""")
        # r2 ended 17 days ago (still shown for 30 days), r1 in 23 days, r6 (24 months) in 49; r3 ended 57 days ago; r4 was renewed (r5);
        # r7 ends in 90 days
        self.assertEqual(r["r60"], [["r2", "2026-09-10", -17], ["r1", "2026-10-20", 23], ["r6", "2026-11-15", 49]])
        self.assertEqual(r["r90"], "r2r1r6r7")
        self.assertEqual(r["stale"], [["b", 44]])       # submitted 6 September, 44 days before 20 October
        self.assertEqual(r["fresh"], 0)
        self.assertEqual(r["budgets"], [
            ["b1", "2026-01-01", "2026-12-31", 30284, 19716, 61, False],     # a + b + c + f (r denied); 30284 / 50000 = 60.6 %
            ["b2", "2026-01-01", "2026-12-31", 15250, -10250, 305, True],    # self-funded: e 800 + i 500 + k 3600 + r 450 + s 9900
            ["b3", "2026-09-01", "2026-09-30", 46334, 53666, 46, False],     # all spending in September
            ["b4", "2026-01-01", "2026-12-31", 17000, 3000, 85, False],      # g 5000 + h 12000 (paid by the Area directly counts here)
            ["b5", "2026-01-01", "2026-12-31", 23800, 6200, 79, False],      # district + lodging: b
            ["b6", "2026-01-01", "2026-12-31", 4200, -4200, None, True],
        ])


class Requests(unittest.TestCase):
    def test_lines_and_text(self):
        r = core(self, LEDGER + r"""
          const c1 = G.claimLines(L, SP, { funder: "district", ...SEPT, lang: "en" });
          const c2 = G.claimLines(L, SP, { funder: "district", ...SEPT, statuses: ["to_request", "submitted"], lang: "en" });
          const es = { "expenses.claim.title": "Solicitud de reembolso", "claim.total": "Total: {amount} ({count} gastos)", "claim.from": "De: {name}" };
          out({ lines: c1.lines.map((l) => [l.id, l.date, l.description, l.category, l.miles, l.rate, l.amount_cents, l.receipt]),
                totals: c1.totals, mileage: c1.mileage, ids: c1.ids, header: c1.header, c2: [c2.ids, c2.totals.cents],
                text: G.claimText(c1, {}, "en"), textEs: G.claimText(G.claimLines(L, SP, { funder: "district", ...SEPT, lang: "es" }), es, "es"), empty: G.claimText(G.claimLines(L, SP, { funder: "committee" }), {}, "en"),
                junk: [G.claimText(null), G.claimText({}), G.claimLines(null, null, null).lines.length] });""")
        self.assertEqual(r["lines"], [["a", "2026-09-02", "Big Book", "Books & literature", "", "", 2400, True],
                                      ["c", "2026-09-05", "Home → Tyler", "Miles driven", 184.6, "0.14", 2584, False]])
        self.assertEqual({k: r["totals"][k] for k in ("cents", "miles", "mileage_cents", "count", "receipts")},
                         {"cents": 4984, "miles": 184.6, "mileage_cents": 2584, "count": 2, "receipts": 1})
        self.assertEqual([[c["id"], c["cents"]] for c in r["totals"]["by_category"]], [["mileage", 2584], ["books", 2400]])
        self.assertEqual([[m["from"], m["to"], m["round_trip"], m["purpose"], m["miles"], m["amount_cents"]] for m in r["mileage"]],
                         [["Home", "Tyler", True, "Fall Assembly", 184.6, 2584]])
        self.assertEqual(r["ids"], ["a", "c"])
        self.assertEqual({k: r["header"][k] for k in ("funder_name", "name", "position", "district", "from", "to")},
                         {"funder_name": "My district", "name": "Maria G.", "position": "GVR", "district": "District 22",
                          "from": "2026-09-01", "to": "2026-09-30"})
        self.assertEqual(r["c2"], [["a", "b", "c"], 28784])
        self.assertEqual(r["text"].split("\n"), [
            "Reimbursement request — My district", "From: Maria G. · GVR · District 22", "Period: Sep 1, 2026 – Sep 30, 2026", "",
            "• Sep 2, 2026 · Big Book · $24.00 · receipt ✓", "• Sep 5, 2026 · Home → Tyler · 184.6 mi × $0.14 · $25.84", "",
            "Mileage: 184.6 miles · $25.84", "By category:", "  Miles driven: $25.84", "  Books & literature: $24.00",
            "Total: $49.84 (2 items)", "Receipts kept: 1 of 2"])
        self.assertTrue(r["textEs"].startswith("Solicitud de reembolso — Mi distrito\nDe: Maria G."))
        self.assertIn("Total: $49.84 (2 gastos)", r["textEs"])
        self.assertIn("Millas recorridas", r["textEs"])
        self.assertIn("Nothing to ask for in this period.", r["empty"])
        self.assertEqual(r["junk"], ["", "", 0])

    def test_names_stay_out_unless_asked(self):
        r = core(self, LEDGER + r"""
          const E = [N({ id: "g1", type: "expense", date: "2026-09-12", category: "subscriptions", description: "Gift subscription for Rosa T.",
                         person: "Rosa T.", sub_kind: "gift", sub_product: "gv_print", sub_term: 12, amount_cents: 3600, funder: "area" }, SP),
                     N({ id: "m1", type: "expense", date: "2026-09-13", category: "meals", description: "Lunch with Pedro S.", person: "Pedro S.",
                         amount_cents: 1800, funder: "area" }, SP)];
          const strings = { "sub_kind.gift": "Gift", "sub_product.gv_print": "Grapevine print", "claim.term": "{n} months" };
          const hidden = G.claimLines(E, SP, { funder: "area", lang: "en", strings });
          const shown = G.claimLines(E, SP, { funder: "area", lang: "en", strings, includeNames: true });
          out({ hidden: hidden.lines.map((l) => l.description), shown: shown.lines.map((l) => l.description),
                leak: /Rosa|Pedro/.test(JSON.stringify(hidden) + G.claimText(hidden, strings, "en")) });""")
        self.assertEqual(r["hidden"], ["Magazine subscriptions · Gift · Grapevine print · 12 months", "Meals"])
        self.assertEqual(r["shown"], ["Gift subscription for Rosa T.", "Lunch with Pedro S."])
        self.assertFalse(r["leak"])


class Backup(unittest.TestCase):
    def test_round_trip_and_rejects(self):
        r = core(self, LEDGER + r"""
          const state = { v: 1, entries: L, settings: SP, meta: { lastBackup: null, lastExport: "2026-09-01T00:00:00.000Z", created: "2026-01-01T00:00:00.000Z" } };
          const json = G.toBackup(state, [{ id: "a", type: "image/jpeg", dataUrl: "data:image/jpeg;base64,AAAA", w: 10, h: 20, name: "r.jpg", added: "2026-09-01T00:00:00.000Z" },
                                          { id: "bad", dataUrl: "javascript:alert(1)" }, { id: "x y", dataUrl: "data:image/png;base64,AA" }, null]);
          const back = G.readBackup(json);
          const merged = G.readBackup(json, CONFIG);
          const k = (x) => (x.ok ? "ok" : x.error);
          const stub = G.readBackup('[{"date":"2026-09-01","kind":"expense","amount":12.5,"cat":"books","description":"Old"}]');
          const dupIds = G.readBackup(JSON.stringify({ format: "gv-expenses-backup", v: 1, entries: [L[0], L[0]], settings: SP }));
          out({ head: JSON.parse(json).format, v: JSON.parse(json).v, ok: back.ok, same: JSON.stringify(back.state.entries) === JSON.stringify(L),
                person: back.state.settings.funders.some((f) => f.id === "p_jose"), meta: back.state.meta.lastExport, receipts: back.receipts,
                merged: [merged.ok, merged.state.entries.length, merged.state.settings.funders.some((f) => f.id === "p_jose")],
                rejects: ["not json", "", '{"hello":1}', "[1,2]", "[]", '{"format":"other","v":1,"entries":[]}',
                          JSON.stringify({ format: "gv-expenses-backup", v: 2, entries: [] }), '{"format":"gv-expenses-backup","v":1,"entries":"x"}',
                          '{"name":"neta65","version":"2.0.0","devDependencies":{}}', '{"entries":[{"a":1}]}', "null", "42", '"text"'].map((t) => k(G.readBackup(t))),
                objects: [k(G.readBackup(null)), k(G.readBackup(42)), k(G.readBackup({ v: 1, entries: [], settings: {} }))],
                stored: k(G.readBackup(JSON.stringify({ v: 1, entries: L.slice(0, 2), settings: SP, meta: {} }))),
                stub: [stub.ok, stub.state.entries.map((e) => [e.type, e.amount_cents, e.category, e.description])],
                dupIds: dupIds.state.entries[0].id !== dupIds.state.entries[1].id });""")
        self.assertEqual((r["head"], r["v"], r["ok"], r["same"], r["person"]), ("gv-expenses-backup", 1, True, True, True))
        self.assertEqual(r["meta"], "2026-09-01T00:00:00.000Z")
        self.assertEqual(r["receipts"], [{"id": "a", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AAAA", "name": "r.jpg",
                                          "added": "2026-09-01T00:00:00.000Z", "w": 10, "h": 20}])
        self.assertEqual(r["merged"], [True, 19, True])
        self.assertEqual(r["rejects"], ["expenses.err.backup_invalid", "expenses.err.backup_invalid", "expenses.err.backup_foreign",
                                        "expenses.err.backup_foreign", "expenses.err.backup_foreign", "expenses.err.backup_foreign",
                                        "expenses.err.backup_newer", "expenses.err.backup_invalid", "expenses.err.backup_foreign",
                                        "expenses.err.backup_foreign", "expenses.err.backup_foreign", "expenses.err.backup_foreign",
                                        "expenses.err.backup_foreign"])
        self.assertEqual(r["objects"], ["expenses.err.backup_foreign", "expenses.err.backup_foreign", "ok"])
        self.assertEqual(r["stored"], "ok")
        self.assertEqual(r["stub"], [True, [["expense", 1250, "books", "Old"]]])   # the first version's plain list: dollars → cents
        self.assertTrue(r["dupIds"])


class Settings(unittest.TestCase):
    def test_merge_defaults(self):
        r = core(self, r"""
          const st = G.mergeDefaults(plain(CONFIG), null);
          const cat = (s, id) => s.categories.find((c) => c.id === id);
          // the visitor's edits
          cat(st, "books").label = "Libros (míos)";
          cat(st, "meals").hidden = true;
          cat(st, "printing").color = "rose";
          st.categories = st.categories.filter((c) => c.id !== "other");
          st.categories.push({ id: "c_retreat", type: "expense", template: "general", label: "Retreats", color: "teal", icon: "tent", hidden: false, order: 50, builtin: false });
          st.funders.push({ id: "f_rowlett", kind: "group", name: "Rowlett Group", hidden: false, order: 9, builtin: false });
          st.rates.find((x) => x.id === "service").rate = "0.20";
          st.default_rate = "service";
          st.renewal_days = 45;
          st.profile = { name: "Maria G.", position: "GVR", district: "District 22" };
          st.custom_fields = [{ id: "cf_x", label: "X", type: "text" }];
          const stored = plain(st);
          // a site update: a new built-in, corrected wording, a new note
          const cfg2 = plain(CONFIG);
          cfg2.categories.push({ ...CONFIG.categories[9], id: "postage", label: { en: "Postage & shipping", es: "Correo y envíos" }, order: 16 });
          cfg2.categories.find((c) => c.id === "meals").label = { en: "Meals & coffee", es: "Comidas y café" };
          cfg2.categories.find((c) => c.id === "books").label = { en: "Books", es: "Libros" };
          cfg2.rates[0].note = { en: "check with a tax professional", es: "consulta con un profesional de impuestos" };
          const m = G.mergeDefaults(cfg2, stored);
          const stored2 = plain(m);
          stored2.categories = stored2.categories.filter((c) => c.id !== "c_retreat");
          const m2 = G.mergeDefaults(cfg2, stored2);
          const maxOrder = Math.max(...m.categories.filter((c) => c.id !== "postage").map((c) => c.order));
          out({ books: cat(m, "books").label, meals: [cat(m, "meals").label, cat(m, "meals").hidden], printing: cat(m, "printing").color,
                other: !!cat(m, "other"), postage: [!!cat(m, "postage"), cat(m, "postage").builtin, cat(m, "postage").order > maxOrder],
                retreat: [!!cat(m, "c_retreat"), cat(m, "c_retreat").builtin], rowlett: m.funders.some((f) => f.id === "f_rowlett"),
                rate: m.rates.find((x) => x.id === "service").rate, note: !!m.rates[0].note, defaultRate: m.default_rate, days: m.renewal_days,
                profile: m.profile.name, custom: m.custom_fields.length, seen: ["other", "postage"].map((id) => m.builtins_seen.categories.includes(id)),
                gone: [!!cat(m2, "c_retreat"), !!cat(m2, "other")], idem: JSON.stringify(G.mergeDefaults(cfg2, m)) === JSON.stringify(m),
                fresh: G.mergeDefaults(cfg2, null).categories.length, noMe: G.mergeDefaults(cfg2, { ...stored, funders: [] }).funders.map((f) => f.id),
                noSeen: G.mergeDefaults(cfg2, { categories: [{ id: "books", label: "Mine" }] }).categories.length,
                badDefaults: G.mergeDefaults(cfg2, { defaults: { funder: "ghost", method: "ghost", claim_status: "x", round_trip: 1 } }).defaults,
                noConfig: [cat(G.mergeDefaults(null, stored), "books").builtin, G.mergeDefaults(null, null).funders.map((f) => f.id)],
                panels: m.panels, empty: G.emptyState(CONFIG).entries.length });""")
        self.assertEqual(r["books"], "Libros (míos)")                           # a rename is the visitor's
        self.assertEqual(r["meals"], [{"en": "Meals & coffee", "es": "Comidas y café"}, True])   # site wording follows; hidden stays
        self.assertEqual(r["printing"], "rose")
        self.assertFalse(r["other"])                                            # a deleted built-in stays deleted
        self.assertEqual(r["postage"], [True, True, True])                      # a new built-in arrives, at the end
        self.assertEqual(r["retreat"], [True, False])
        self.assertTrue(r["rowlett"])
        self.assertEqual((r["rate"], r["note"], r["defaultRate"], r["days"], r["profile"], r["custom"]), ("0.20", True, "service", 45, "Maria G.", 1))
        self.assertEqual(r["seen"], [True, True])
        self.assertEqual(r["gone"], [False, False])                             # a deleted custom one never comes back
        self.assertTrue(r["idem"])
        self.assertEqual(r["fresh"], 17)
        self.assertEqual(r["noMe"], ["me"])                                     # "me" is part of the model
        self.assertEqual(r["noSeen"], 17)
        self.assertEqual(r["badDefaults"], {"funder": "me", "method": "cash", "rate": "irs_charity", "round_trip": True, "claim_status": "to_request"})
        self.assertEqual(r["noConfig"], [True, ["me"]])
        self.assertEqual(r["panels"], [{"id": "77", "from": "2027-01-01", "to": "2028-12-31"}])
        self.assertEqual(r["empty"], 0)


class Examples(unittest.TestCase):
    def test_a_realistic_season(self):
        r = core(self, r"""
          const today = "2026-09-27";
          const ex = G.exampleEntries(today, S), exEs = G.exampleEntries(today, S, "es");
          const plan = G.planImport(G.toCSV(ex, S, { lang: "en" }), [], S, {});
          out({ n: ex.length, allExample: ex.every((e) => e.example === true), dated: ex.every((e) => e.date <= today && e.date >= "2025-09-01"),
                invalid: ex.map((e) => G.validateEntry(e, S)).filter((v) => v.length), types: [...new Set(ex.map((e) => e.type))].sort(),
                templates: [...new Set(ex.map((e) => G.templateOf(S, e)))].sort(), people: ex.map((e) => e.person).filter(Boolean),
                statuses: [...new Set(ex.map((e) => e.claim_status))].sort(), cats: ex.map((e) => e.category),
                owed: G.peopleOwed(ex, S).map((p) => [p.person, p.owed_cents]), owedTotal: G.summary(ex, S, {}).owed_cents,
                inv: G.inventory(ex).map((i) => [i.item, i.on_hand]), events: G.eventGiveaways(ex).map((e) => e.event),
                renew: G.renewals(ex, today, 60).map((x) => x.entry.person), stale: G.staleClaims(ex, today, 30).length,
                received: ex.filter((e) => e.type === "received").map((e) => e.category), es: exEs[0].description, en: ex[0].description,
                ids: new Set(ex.map((e) => e.id)).size, roundTrip: JSON.stringify(plan.add.map((e) => ({ ...e, example: true }))) === JSON.stringify(ex),
                photo: ex.filter((e) => e.receipt === "photo").length });""")
        self.assertEqual(r["n"], 19)
        self.assertTrue(r["allExample"])
        self.assertTrue(r["dated"])
        self.assertEqual(r["invalid"], [])
        self.assertEqual(r["types"], ["expense", "giveaway", "mileage", "received", "stock"])
        self.assertEqual(r["templates"], sorted(["general", "books", "subscription", "lodging", "meal", "printing", "travel", "mileage", "received", "giveaway", "stock"]))
        self.assertEqual(r["cats"], ["books", "giveaways", "giveaways", "subscriptions", "subscriptions", "lodging", "meals", "printing", "travel",
                                     "registration", "contributions", "mileage", "mileage", "reimbursement", "advance", "stock_in", "given", "given", "given"])
        self.assertEqual(r["people"], ["Maria G.", "José R."])                  # first name + initial only
        self.assertEqual(r["statuses"], ["none", "paid", "submitted", "to_request"])
        self.assertEqual(r["owed"], [["José R.", 1500]])                        # the helped subscription, not paid back yet
        # district: books 2400 + hotel 23800 + printing 450 + registration 1500 (paid) + 184.6 mi × $0.14 = 2584 → 30734 asked,
        # 1500 settled → owes 29234; the Area paid its 5000; the group advanced 5000 for a 4200 meal; José owes 1500
        self.assertEqual(r["owedTotal"], 29234 + 1500)
        self.assertEqual(r["inv"], [["Grapevine (back issues)", 5], ["Grapevine (this month's issue)", 8], ["La Viña (this issue)", 4]])
        self.assertEqual(r["events"], ["Grapevine & La Viña workshop", "Fall Assembly"])
        self.assertEqual(r["renew"], ["Maria G."])                              # the gift subscription is due soon
        self.assertEqual(r["stale"], 2)                                         # the Assembly request (hotel + miles) sent 70 days ago
        self.assertEqual(r["received"], ["reimbursement", "advance"])
        self.assertNotEqual(r["es"], r["en"])
        self.assertIn("Grapevine", r["es"])
        self.assertEqual(r["ids"], 19)
        self.assertTrue(r["roundTrip"])
        self.assertEqual(r["photo"], 0)                                         # no photo that isn't on the device


class FilterSort(unittest.TestCase):
    def test_filters(self):
        r = core(self, LEDGER + r"""
          const F = (f) => ids(G.filterEntries(L, f, SP));
          out([F({ q: "viña" }), F({ q: "VINA" }), F({ q: "hotel area" }), F({ q: "José" }), F({ types: ["received"] }), F({ funders: ["area"] }),
               F({ statuses: ["submitted"] }), F({ tag: "Assembly" }), F({ event: "fall  assembly" }), F({ from: "2026-09-10", to: "2026-09-12" }),
               F({ hasReceipt: true }), F({ categories: ["lodging"] }), F({ q: "mi distrito" }), F({ format: "lv" }), F(null).length,
               F({ types: [], q: "" }).length, F({ q: "zzz" })]);""")
        self.assertEqual(r, ["q", "q", "h", "jn", "lmn", "ghlo", "b", "c", "cp", "djkqr", "a", "bh", "abcfr", "q", 19, 19, ""])

    def test_sort(self):
        r = core(self, LEDGER + r"""
          const T = (k, d) => ids(G.sortEntries(L, k, d, SP)).slice(0, 4);
          out([T("amount", "desc"), T("amount", "asc"), T("date"), T("description", "asc"), T("category", "asc"), T("status", "desc"), T("nonsense"),
               ids(L) === ids(L.slice())]);""")
        # amounts: b 23800, h 12000, s 9900, then g / l / m at 5000 → newest first (l, 20th); zero amounts tie → newest first (q, p, o), then r 450; dates: n 25th, l 20th, k/j 12th (ids desc)
        self.assertEqual(r[:3], ["bhsl", "qpor", "nlkj"])
        self.assertEqual(r[3][:3], "qpi")                 # no description first (q, p), then "7th Tradition" before letters
        self.assertEqual(r[4][:1], "a")                   # "Books & literature"
        self.assertEqual(r[5][:1], "r")                   # denied is the last status
        self.assertEqual(r[6], "nlkj")                    # unknown key: by date
        self.assertTrue(r[7])


class MessageKeys(unittest.TestCase):
    def test_every_key_is_listed(self):
        import re
        src = (ROOT / CORE).read_text(encoding="utf-8")
        block = src[src.index("var MESSAGE_KEYS = ["):]
        block = block[:block.index("];")]
        listed = set(re.findall(r'"(expenses\.(?:err|warn)\.[a-z_]+)"', block))
        used = set(re.findall(r'"(expenses\.(?:err|warn)\.[a-z_]+)"', src.replace(block, "")))
        self.assertEqual(used, listed)
        self.assertFalse(re.search(r'"expenses\.(?:err|warn)\.[a-z_]*"\s*\+', src), "keys are written out in full (no string building)")
        r = core(self, "out([G.MESSAGE_KEYS, G.STRING_KEYS]);")
        self.assertEqual(set(r[0]), listed)
        self.assertEqual(len(r[0]), len(set(r[0])))
        for k in r[1]:
            self.assertTrue(k.startswith("expenses.claim."), k)
        for k in set(re.findall(r'word\(strings, "(claim\.[a-z_]+)"', src)):
            self.assertIn("expenses." + k, r[1])

    def test_module_shape(self):
        r = core(self, "out(Object.keys(G));")
        for name in ["VERSION", "SCHEMA", "newId", "emptyState", "normalizeEntry", "validateEntry", "mileageCents", "parseMoney", "fmtMoney",
                     "parseDate", "addMonths", "summary", "funderBalances", "peopleOwed", "inventory", "renewals", "budgets", "staleClaims",
                     "filterEntries", "sortEntries", "claimLines", "claimText", "toCSV", "parseCSV", "planImport", "applyImport", "CSV_COLUMNS",
                     "toBackup", "readBackup", "migrate", "mergeDefaults", "exampleEntries"]:
            self.assertIn(name, r)
        src = (ROOT / CORE).read_text(encoding="utf-8")
        # ES2019: no optional chaining, no ?? (the site's browsers list), no imports
        code = "\n".join(line.split("//")[0] for line in src.splitlines())
        self.assertNotRegex(code, r"(?m)\?\.[A-Za-z_(\[]|\?\?|^\s*(import|export)\s")

    def test_new_ids(self):
        r = core(self, "const a = []; for (let i = 0; i < 5000; i++) a.push(G.newId()); out([new Set(a).size, a.every((x) => /^x[0-9a-z]{10,}$/.test(x))]);")
        self.assertEqual(r, [5000, True])


class ConfigFile(unittest.TestCase):
    """The real config/expenses.yml (read by src/_data/expenses.js) works with the core."""

    def test_the_site_defaults(self):
        for p in ("config/expenses.yml", "src/_data/expenses.js", "node_modules/js-yaml"):
            if not (ROOT / p).exists():
                self.skipTest(f"{p} is not there")
        r = run_js(self, r"""
          import vm from "node:vm";
          const mod = await imp("src/_data/expenses.js");
          const cfg = mod.default().config;
          const ctx = vm.createContext({ console, TextDecoder });
          vm.runInContext(fs.readFileSync("src/assets/js/expenses-core.js", "utf8"), ctx);
          const G = ctx.GVX;
          const S = G.emptyState(JSON.parse(JSON.stringify(cfg))).settings;
          const ex = G.exampleEntries("2026-09-27", S);
          const plan = G.planImport(G.toCSV(ex, S, { lang: "es" }), [], S, {});
          out({ cats: ex.map((e) => e.category), invalid: ex.map((e) => G.validateEntry(e, S)).filter((v) => v.length),
                roundTrip: JSON.stringify(plan.add.map((e) => ({ ...e, example: true }))) === JSON.stringify(ex),
                funders: ex.map((e) => e.funder).filter((f) => f && !S.funders.some((x) => x.id === f)) });""",
                   needs_modules=False, env={"I18N_STRICT": ""})
        self.assertEqual(r["cats"], ["books", "giveaways", "giveaways", "subscriptions", "subscriptions", "lodging", "meals", "printing", "travel",
                                     "registration", "contributions", "mileage", "mileage", "reimbursement", "advance", "stock_in", "given", "given", "given"])
        self.assertEqual(r["invalid"], [])
        self.assertEqual(r["funders"], [])
        self.assertTrue(r["roundTrip"])


if __name__ == "__main__":
    unittest.main()
