"""The service expense tracker's logic (src/assets/js/expenses-core.js, window.GVX) run in Node.js.

People's money: every amount is checked against numbers worked out by hand (in the comments).
  * money / numbers / dates — "$1,234.50", "1.234,50", "(12.00)", Excel serial dates, month names …
  * mileage              — round(miles × 1000 × round(rate × 1000) / 10000), exact, half up
  * entries              — normalizeEntry (never throws, idempotent) and validateEntry
  * CSV                  — the writer (BOM, CRLF, quotes, formula guard), the reader (delimiters, line
                           ends, quoted line breaks, blank and ragged rows), the ROUND-TRIP LAW with
                           nasty values (also through "Excel": ; + decimal commas + day-first dates),
                           planImport on garbage (never throws), limits, the mapping step, dedupe/merge,
                           an export trimmed in a spreadsheet, the date order a file shows by itself
  * totals               — summary / funderBalances / peopleOwed / inventory / renewals / budgets /
                           stale claims / requests, on a hand-computed ledger
  * backup, settings     — readBackup rejects foreign JSON, migrates the older list; mergeDefaults
                           keeps the visitor's edits and adds new built-ins
  * 1.1.0                — several trips on one entry, "rode with someone" (no miles), the role,
                           service activities (settings, import by name, filters, totals),
                           subscriptions (statuses, counts, the calendar file), the giveaways of a
                           period, the service report (a GVR's 2026 report, number for number — its names, references and
                           distances invented),
                           and the files written before 1.1.0 (tests/fixtures/expenses/) read as they did
  * 1.2.0                — what is owed is the balance at a period's end; Area 65's service panels by rule;
                           UTF-16 text; the .zip backup's receipts by file name (expenses-files.js has its own
                           tests: tests/test_expenses_files.py)
  * examples             — a realistic GVR season, first names only, one of each kind
The file runs in a vm context, as tests/test_pwa_worker.py runs sw-core.js. Skipped without Node.js.

    python -m unittest tests.test_expenses_core -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

CORE = "src/assets/js/expenses-core.js"
# what the tracker wrote before 1.1.0 (frozen from that code: OlderFiles)
FIXTURES = ROOT / "tests" / "fixtures" / "expenses"
# the fields 1.1.0 added to an entry, at their defaults (an entry from before reads with these)
NEW_FIELDS = {"activity": "", "role": "", "trips": "", "no_miles": False, "ref": ""}


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
    "activities": [{"id": a, "name": {"en": en, "es": es}, "builtin": True, "hidden": False, "order": i}
                   for i, (a, en, es) in enumerate([
                       ("assembly", "Assemblies & Area committee meetings", "Asambleas y reuniones del comité de Área"),
                       ("district", "District meetings", "Reuniones del distrito"),
                       ("table", "Information tables & conventions", "Mesas de información y convenciones"),
                       ("workshop", "Workshops & events", "Talleres y eventos"),
                       ("committee", "Grapevine / La Viña committee meetings", "Reuniones del comité de Grapevine / La Viña"),
                       ("group", "Groups & group visits", "Grupos y visitas a grupos"),
                       ("other", "Other service", "Otro servicio")])],
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
      round_trip: i % 2 === 0, amount_cents: i % 4 === 2 ? 4321 : 0, trips: [3, "", 7, 1][i % 4], no_miles: i === 16 });
    // 1.1.0's fields: a service activity (an id the settings have, as a visitor's entries do), the
    // role and a reference (the nasty values too); trips and "no miles" above
    Object.assign(raw, { activity: ["assembly", "district", "", "table", "workshop", "other"][i % 6], role: v, ref: v });
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
    # the columns of 1.0.0, in their order (a file written before 1.1.0 has exactly these) …
    HEADER_V1 = ("id,date,end_date,type,category,category_label,description,amount,signed_amount,funder,funder_name,claim_status,"
                 "claim_date,claim_ref,paid_date,method,vendor,event,place,person,item,format,quantity,unit_cost,giveaway,miles,rate,"
                 "from,to,round_trip,odometer_start,odometer_end,nights,attendees,sub_product,sub_term,sub_start,sub_end,sub_kind,"
                 "repaid,receipt,receipt_ref,tags,notes,created,updated")
    # … and 1.1.0's, after them (never in between: the contract)
    HEADER = HEADER_V1 + ",activity,activity_label,role,trips,no_miles,ref"

    def test_the_file(self):
        r = core(self, WITH_CUSTOM + """
          const a = N({ id: "xa", type: "expense", date: "2026-09-02", category: "books", description: 'He said "hi", ok', amount_cents: 2400,
            funder: "district", vendor: "=SUM(A1)", claim_ref: "-5", notes: "@home\\nline 2", tags: ["+1", "b"], giveaway: true,
            sub_start: "2026-01-31", sub_term: 1, created: "2026-09-02T10:00:00.000Z", custom: { cf_yes: false, cf_num: 2.5, cf_text: "=1+1" },
            activity: "assembly", role: "=Tech setup", ref: "-52817" }, S2);
          const b = N({ id: "xb", type: "received", date: "2026-09-03", category: "reimbursement", description: "Check", amount_cents: 5, funder: "area" }, S2);
          const m = N({ id: "xm", type: "mileage", date: "2026-09-04", miles: 12.3, rate: "0.655", funder: "me", from: "Home", to: "Tyler", trips: 3 }, S2);
          const csv = G.toCSV([a, b, m], S2, { lang: "es" });
          const rows = G.parseCSV(csv);
          const H = rows[0];
          const col = (row, name) => row[H.indexOf(name)];
          out({ bom: csv.charCodeAt(0) === 0xfeff, crlf: csv.split("\\r\\n").length, loneLF: /[^\\r]\\n/.test(csv.replace(/"[^"]*"/g, "")),
                head: csv.slice(1).split("\\r\\n")[0], end: csv.slice(-2) === "\\r\\n",
                quoted: csv.includes('"He said ""hi"", ok"'),
                a: ["amount", "signed_amount", "category_label", "funder_name", "vendor", "claim_ref", "notes", "tags", "giveaway", "sub_end", "created",
                    "custom:Approved?", "custom:Pages", "custom:Sponsor note, private", "activity", "activity_label", "role", "ref"].map((k) => col(rows[1], k)),
                b: ["amount", "signed_amount", "giveaway", "funder_name", "claim_status", "activity", "trips", "no_miles"].map((k) => col(rows[2], k)),
                m: ["amount", "signed_amount", "miles", "rate", "description", "round_trip", "funder_name", "trips", "no_miles"].map((k) => col(rows[3], k)),
                en: G.parseCSV(G.toCSV([a], S2, { lang: "en" }))[1][5] });""")
        self.assertTrue(r["bom"])
        self.assertTrue(r["end"])
        self.assertEqual(r["crlf"], 5)                   # header + 3 rows + the final line end
        self.assertFalse(r["loneLF"])                    # a bare LF only inside quotes
        self.assertEqual(r["head"], self.HEADER + ',"custom:Sponsor note, private",custom:Pages,custom:Approved?,custom:Revisado el,custom:Size')
        self.assertTrue(r["quoted"])
        self.assertEqual(r["a"], ["24.00", "-24.00", "Libros y literatura", "Mi distrito", "'=SUM(A1)", "'-5", "'@home\nline 2", "'+1; b", "yes",
                                  "2026-02-28", "2026-09-02T10:00:00.000Z", "no", "2.5", "'=1+1",
                                  "assembly", "Asambleas y reuniones del comité de Área", "'=Tech setup", "'-52817"])
        self.assertEqual(r["b"], ["0.05", "0.05", "", "Área 65 (NETA 65)", "none", "", "", ""])
        # 12.3 × 0.655 = $8.0565 → 8.06 (the miles are the whole distance: 3 trips are in them); spending is
        # negative; numbers are never guarded
        self.assertEqual(r["m"], ["8.06", "-8.06", "12.3", "0.655", "Home → Tyler", "", "Yo (autofinanciado)", "3", ""])
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

    def test_which_sign_is_spending(self):
        """A card statement lists charges as positive and a refund with a minus; a bank account puts the
        minus on spending. Mapped sheets with no type column: the header or the sign most rows carry
        decides, and the visitor's answer (opts.positive) always wins."""
        r = core(self, r"""
          const card = "Date,Description,Amount\n09/02/2026,Office Depot,45.00\n09/03/2026,Kinko's copies,12.00\n09/04/2026,Refund Office Depot,-10.00\n";
          const bank = "Date,Description,Amount\n09/02/2026,Office Depot,-45.00\n09/03/2026,Copies,-12.00\n09/04/2026,District check,40.00\n";
          const map = { date: 0, description: 1, amount: 2 };
          const plan = (text, o) => G.planImport(text, [], S, Object.assign({ mapping: map }, o || {}));
          const read = (p) => ({ signs: p.signs, positive: p.positive, rows: p.add.map((e) => [e.description, e.type, e.amount_cents, e.category]) });
          const guess = (head, rows) => plan("Date,Description," + head + "\n" + rows.map((v, i) => "09/0" + (i + 1) + "/2026,Row " + i + "," + v).join("\n") + "\n").positive;
          out({
            card: read(plan(card)), cardFlipped: read(plan(card, { positive: "received" })),
            bank: read(plan(bank)), bankFlipped: read(plan(bank, { positive: "spent" })),
            // one sign only: every row is spending — unless the visitor says they are money received
            allPositive: read(plan("Date,Description,Amount\n09/02/2026,Books,20\n09/03/2026,Hotel,90\n")),
            allPositiveReceived: read(plan("Date,Description,Amount\n09/02/2026,Area check,20\n", { positive: "received" })),
            allNegative: read(plan("Date,Description,Amount\n09/02/2026,Books,-20\n")),
            heads: {
              debit: guess("Debit", ["1234.50", "(12.00)", "-40.00"]), cargo: guess("Cargo", ["-5", "-6", "7"]),
              deposit: guess("Deposits", ["5", "6", "-7"]), abono: guess("Abono", ["5", "6", "-7"]),
              creditCard: guess("Credit card amount", ["5", "6", "-7"]), both: guess("Debit/Credit", ["-5", "-6", "7"]),
              tie: guess("Amount", ["5", "-6"]),
            },
            // our own file never asks: signed_amount above zero is money received
            ours: G.planImport("date,type,amount,signed_amount,description\n2026-09-01,,12.00,12.00,Check\n2026-09-02,,12.00,-12.00,Books\n", [], S, { positive: "spent" })
              .add.map((e) => e.type),
            oursSigns: G.planImport("date,type,amount\n2026-09-01,expense,12.00\n", [], S, {}).signs,
          });""")
        # the card: most rows are positive, so positive is spending and the refund is money back
        self.assertEqual(r["card"], {"signs": {"positive": 2, "negative": 1}, "positive": "spent", "rows": [
            ["Office Depot", "expense", 4500, "books"], ["Kinko's copies", "expense", 1200, "books"],
            ["Refund Office Depot", "received", 1000, "reimbursement"]]})
        self.assertEqual(r["cardFlipped"]["rows"], [
            ["Office Depot", "received", 4500, "reimbursement"], ["Kinko's copies", "received", 1200, "reimbursement"],
            ["Refund Office Depot", "expense", 1000, "books"]])
        self.assertEqual(r["cardFlipped"]["positive"], "received")
        # the bank: most rows carry the minus, so the minus is spending and the check is money received
        self.assertEqual(r["bank"], {"signs": {"positive": 1, "negative": 2}, "positive": "received", "rows": [
            ["Office Depot", "expense", 4500, "books"], ["Copies", "expense", 1200, "books"],
            ["District check", "received", 4000, "reimbursement"]]})
        self.assertEqual([x[1] for x in r["bankFlipped"]["rows"]], ["received", "received", "expense"])
        self.assertEqual((r["allPositive"]["positive"], [x[1] for x in r["allPositive"]["rows"]]), ("spent", ["expense", "expense"]))
        self.assertEqual([x[1] for x in r["allPositiveReceived"]["rows"]], ["received"])
        self.assertEqual((r["allNegative"]["positive"], [x[1] for x in r["allNegative"]["rows"]]), ("received", ["expense"]))
        self.assertEqual(r["heads"], {
            "debit": "spent", "cargo": "spent",            # the header says spending, whatever most rows carry
            "deposit": "received", "abono": "received",    # … or money in
            "creditCard": "spent",                         # "credit card" says nothing: most rows are positive
            "both": "received",                            # "Debit/Credit" says both: most rows carry the minus
            "tie": "received",                             # a tie keeps the minus as spending
        })
        self.assertEqual(r["ours"], ["received", "expense"])
        self.assertIsNone(r["oursSigns"])


class ImportShapes(unittest.TestCase):
    """Which files are the tracker's own, and what a spreadsheet may change in one."""

    def test_other_peoples_sheets_go_to_the_mapping_step(self):
        r = core(self, r"""
          const ask = (text, o) => { const p = G.planImport(text, [], S, o || {}); return [p.needsMapping, p.format, p.add.length, p.errors.map((e) => e.message_key)]; };
          out({
            idItemCost: ask("ID,Date,Item,Cost\n1,2026-03-01,Parking,5.00\n"),
            idAmount: ask("ID,Date,Amount,Description\n1,2026-03-01,5.00,Parking\n"),
            bank: ask("Date,Description,Type,Amount\n2026-03-01,Coffee,Debit,-3.50\n2026-03-02,Refund,Credit,3.50\n"),
            ours: ask("date,type,category,description,amount\n2026-03-01,expense,books,Big Book,12\n"),
            oursNoCategory: ask("type,date,amount\nexpense,2026-03-01,12\n"),
            forced: ask("date,type,category,description,amount\n2026-03-01,expense,books,Big Book,12\n", { forceMapping: true }),
            forcedMapped: ask("date,type,category,description,amount\n2026-03-01,expense,books,Big Book,12\n", { forceMapping: true, mapping: { date: 0, description: 3, amount: 4 } }),
          });""")
        self.assertEqual(r["idItemCost"], [True, "", 0, []])      # only an "ID" in common: ask, never overwrite by id
        self.assertEqual(r["idAmount"], [True, "", 0, []])
        self.assertEqual(r["bank"], [True, "", 0, []])            # Type = Debit / Credit is not ours
        self.assertEqual(r["ours"], [False, "ours", 1, []])
        self.assertEqual(r["oursNoCategory"], [False, "ours", 1, []])
        self.assertEqual(r["forced"], [True, "", 0, []])          # "Map the columns myself"
        self.assertEqual(r["forcedMapped"], [False, "mapped", 1, []])

    def test_an_export_edited_in_a_spreadsheet(self):
        r = core(self, r"""
          const A = N({ id: "xa", type: "expense", date: "2026-09-01", description: "Big Book", amount_cents: 2400, created: "2026-09-01T00:00:00.000Z", updated: "2026-09-02T00:00:00.000Z" });
          const B = N({ id: "xb", type: "expense", date: "2026-09-02", description: "Hotel", amount_cents: 9000, created: "2026-09-02T00:00:00.000Z", updated: "2026-09-02T00:00:00.000Z" });
          const csv = G.toCSV([A, B], S, { lang: "en" });
          const edited = csv.replace(",24.00,-24.00,", ",29.00,-29.00,");
          const plan = G.planImport(edited, [A, B], S, {});
          const upd = plan.update[0] || {};
          // a spreadsheet that re-saved the stamps its own way (not ISO any more): an edit still counts
          const excel = edited.replace(/2026-09-0\dT00:00:00\.000Z/g, "9/2/2026 0:00");
          const plan2 = G.planImport(excel, [A, B], S, {});
          // the old file again after the import: older now, skipped
          const after = G.applyImport({ v: 1, entries: [A, B], settings: S, meta: {} }, plan, {}).entries;
          const plan3 = G.planImport(csv, after, S, {});
          out({ update: plan.update.map((e) => [e.id, e.amount_cents]), same: plan.skip.map((s) => s.reason), newer: upd.updated > "2026-09-02T00:00:00.000Z",
                created: upd.created, excel: [plan2.update.map((e) => e.id), plan2.skip.map((s) => s.reason), (plan2.update[0] || {}).created],
                old: plan3.skip.map((s) => [s.row, s.reason]), all: plan.all.length });""")
        self.assertEqual(r["update"], [["xa", 2900]])
        self.assertEqual(r["same"], ["same"])
        self.assertTrue(r["newer"])                               # stamped now: the file's words win
        self.assertEqual(r["created"], "2026-09-01T00:00:00.000Z")
        self.assertEqual(r["excel"], [["xa"], ["same"], "2026-09-01T00:00:00.000Z"])
        self.assertEqual(r["old"], [[2, "older"], [3, "same"]])
        self.assertEqual(r["all"], 2)                             # "replace" has every row of the file

    def test_an_export_trimmed_in_a_spreadsheet(self):
        """Columns deleted from our own file before it comes back: a row for an entry the ledger has
        changes only what the file still has — a column that is gone is not a cell that was cleared."""
        r = core(self, WITH_CUSTOM + r"""
          const stamps = (d) => ({ created: d + "T10:00:00.000Z", updated: d + "T11:00:00.000Z" });
          const E = [
            N({ id: "xh", type: "expense", date: "2026-07-18", end_date: "2026-07-20", category: "lodging", description: "Hotel for the Fall Assembly",
                amount_cents: 23800, funder: "district", claim_status: "submitted", claim_date: "2026-07-20", claim_ref: "D22-07", notes: "two nights",
                tags: ["assembly"], receipt: "paper", custom: { cf_text: "Ask the DCM", cf_num: 2 }, ...stamps("2026-07-21") }, S2),
            N({ id: "xb", type: "expense", date: "2026-08-01", category: "books", description: "Big Books", amount_cents: 4800, quantity: 4, unit_cost_cents: 1200,
                funder: "area", claim_status: "paid", claim_date: "2026-08-01", paid_date: "2026-08-20", receipt: "photo", ...stamps("2026-08-20") }, S2),
            N({ id: "xm", type: "mileage", date: "2026-07-18", from: "Home", to: "Tyler", miles: 50, rate: "0.655", funder: "district",
                claim_status: "to_request", event: "Fall Assembly", ...stamps("2026-07-18") }, S2),
          ];
          const rows = G.parseCSV(G.toCSV(E, S2, { lang: "en" })), H = rows[0];
          const q = (v) => (/[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v);
          // the columns kept, and the cells changed (by id)
          const trimmed = (cols, edits) => rows.map((row, i) => cols.map((c) => {
            const e = i ? edits[row[H.indexOf("id")]] : null;
            return q(e && c in e ? e[c] : row[H.indexOf(c)]);
          }).join(",")).join("\r\n") + "\r\n";
          const pick = (e) => [e.description, e.category, e.funder, e.claim_status, e.claim_date, e.claim_ref, e.notes, e.tags, e.receipt, e.end_date, e.custom];
          const t1 = trimmed(["id", "date", "type", "description", "amount", "updated", "custom:Pages"],
                             { xh: { description: "Hotel for the Fall Assembly (Tyler)", "custom:Pages": "3" } });
          const plan = G.planImport(t1, E, S2, {});
          const after = G.applyImport({ v: 1, entries: E, settings: S2, meta: {} }, plan, {}).entries;
          // no "updated" column, no rate: the trip keeps its own rate (not today's default)
          const t2 = trimmed(["id", "date", "type", "description", "miles"], { xm: { description: "Home → Tyler (Fall Assembly)" } });
          const plan2 = G.planImport(t2, E, S2, {});
          const m = plan2.update[0] || {};
          out({ update: plan.update.map((e) => e.id), skip: plan.skip.map((s) => [s.row, s.reason]), errors: plan.errors, hotel: pick(after[0]),
                others: [JSON.stringify(after[1]) === JSON.stringify(E[1]), JSON.stringify(after[2]) === JSON.stringify(E[2])],
                update2: plan2.update.map((e) => e.id), skip2: plan2.skip.map((s) => s.reason),
                trip: [m.description, m.miles, m.rate, m.amount_cents, m.funder, m.claim_status, m.event, m.created] });""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["update"], ["xh"])                     # only the row that was edited …
        self.assertEqual(r["skip"], [[3, "same"], [4, "same"]])   # … the others are unchanged
        self.assertEqual(r["hotel"], ["Hotel for the Fall Assembly (Tyler)", "lodging", "district", "submitted", "2026-07-20", "D22-07", "two nights",
                                      ["assembly"], "paper", "2026-07-20", {"cf_text": "Ask the DCM", "cf_num": 3}])
        self.assertEqual(r["others"], [True, True])               # the photo receipt, the funder, the paid request all kept
        self.assertEqual((r["update2"], r["skip2"]), (["xm"], ["same", "same"]))
        # 50 mi × $0.655 = $32.75 (at the default $0.14 it would have become $7.00)
        self.assertEqual(r["trip"], ["Home → Tyler (Fall Assembly)", 50, "0.655", 3275, "district", "to_request", "Fall Assembly", "2026-07-18T10:00:00.000Z"])

    def test_the_date_order_a_file_shows(self):
        """3/9/2026 depends on the date order; 9/15/2026 decides itself. A date column whose dates show
        the order (never both ways) is read in that order throughout — whatever the page's choice."""
        r = core(self, r"""
          const map = { date: 0, description: 1, amount: 2 };
          const read = (text, o) => { const p = G.planImport(text, [], S, o); return [p.dateOrder, p.add.map((e) => e.date)]; };
          const us = "Date,Description,Amount\n09/03/2026,Office Depot,45.00\n09/05/2026,Copies,12.00\n09/15/2026,Hotel,90.00\n";
          out({
            usOnEs: read(us, { mapping: map, dateOrder: "dmy" }), usOnEn: read(us, { mapping: map }),
            dmyOnEn: read("Fecha,Concepto,Importe\n03/09/2026,Libros,12\n15/09/2026,Hotel,90\n", { mapping: map, dateOrder: "mdy" }),
            // both ways (a file that is not consistent): the visitor's choice, each clear date for itself
            mixed: read("Date,Description,Amount\n03/04/2026,A,1\n15/04/2026,B,2\n04/15/2026,C,3\n", { mapping: map, dateOrder: "dmy" }),
            // nothing decides: the visitor's choice
            none: read("Date,Description,Amount\n03/04/2026,A,1\n2026-04-05,B,2\n", { mapping: map, dateOrder: "dmy" }),
            // our own file re-saved by a US spreadsheet, read on the Spanish page: every date column follows
            ours: G.planImport("date,type,amount,funder,claim_date\n09/15/2026,expense,12.00,district,09/03/2026\n", [], S, { dateOrder: "dmy" })
              .add.map((e) => [e.date, e.claim_date]),
          });""")
        self.assertEqual(r["usOnEs"], ["mdy", ["2026-09-03", "2026-09-05", "2026-09-15"]])
        self.assertEqual(r["usOnEn"], ["mdy", ["2026-09-03", "2026-09-05", "2026-09-15"]])
        self.assertEqual(r["dmyOnEn"], ["dmy", ["2026-09-03", "2026-09-15"]])
        self.assertEqual(r["mixed"], ["dmy", ["2026-04-03", "2026-04-15", "2026-04-15"]])
        self.assertEqual(r["none"], ["dmy", ["2026-04-03", "2026-04-05"]])
        self.assertEqual(r["ours"], [["2026-09-15", "2026-09-03"]])

    def test_our_mileage_without_a_rate_column_and_quotes_after_spaces(self):
        r = core(self, r"""
          const plan = G.planImport("date;type;category;description;amount;funder;miles\n14/02/2026;mileage;mileage;Casa → Tyler;;district;45,5\n", [], S, { dateOrder: "dmy" });
          const withRate = G.planImport("date,type,miles,rate\n2026-02-14,mileage,10,\n", [], S, {});
          out({ miles: plan.add.map((e) => [e.miles, e.rate, e.amount_cents]), warn: plan.warnings.map((w) => w.message_key),
                blankRate: withRate.add.map((e) => [e.rate, e.amount_cents]),
                spaced: G.parseCSV('Date, "Description, long", Amount\n2026-03-01, "Coffee, tea",3\n').map((r) => r.slice()),
                tab: G.parseCSV('a\t "b\tc"\td\n').map((r) => r.slice()) });""")
        self.assertEqual(r["miles"], [[45.5, "0.14", 637]])       # 45.5 × $0.14 = $6.37 (the default rate)
        self.assertEqual(r["warn"], [])
        self.assertEqual(r["blankRate"], [["", 0]])               # a rate column left blank: the visitor's choice
        self.assertEqual(r["spaced"], [["Date", "Description, long", " Amount"], ["2026-03-01", "Coffee, tea", "3"]])
        self.assertEqual(r["tab"], [["a", "b\tc", "d"]])

    def test_what_a_picked_file_is(self):
        r = core(self, r"""const b = (a) => new Uint8Array(a);
          out({ kinds: [G.importKind("backup.json", ""), G.importKind("Backup.JSON", "x"), G.importKind("x.txt", "﻿  {\"format\""),
                   G.importKind("x.txt", "[{"), G.importKind("x.csv", "date,amount"), G.importKind(null, null)],
                   // by the first bytes, whatever the name: a .zip (a backup or an .xlsx) and Excel's older .xls
                   bytes: [G.importKind("x.xlsx", "PK", b([0x50, 0x4b, 3, 4, 20])), G.importKind("backup.json", "PK", b([0x50, 0x4b, 3, 4])),
                           G.importKind("old.xls", "", b([0xd0, 0xcf, 0x11, 0xe0, 0xa1])), G.importKind("x.csv", "date", b([0x64, 0x61]))],
                   limits: [G.importLimit("csv"), G.importLimit("backup"), G.importLimit("zip"), G.importLimit("?")],
                   bigBackup: G.readBackup(G.toBackup(G.emptyState(CONFIG), [{ id: "p1", type: "image/jpeg", dataUrl: "data:image/jpeg;base64," + "A".repeat(12 * 1048576) }]), CONFIG).ok });""")
        self.assertEqual(r["kinds"], ["backup", "backup", "backup", "backup", "csv", "csv"])
        self.assertEqual(r["bytes"], ["zip", "zip", "xls", "csv"])
        self.assertEqual(r["limits"], [10485760, 4 * 1024 ** 3, 4 * 1024 ** 3, 10485760])   # a backup is the visitor's own: no real limit
        self.assertTrue(r["bigBackup"])                            # a backup over 10 MB (photos) is read


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

    def test_the_request_csv(self):
        # what the printed request shows, one row per line: names only when the request includes them,
        # never the notes, ids or stamps of the full export; a formula-looking cell is guarded
        r = core(self, LEDGER + r"""
          const E = L.concat([N({ id: "g1", type: "expense", date: "2026-09-12", category: "subscriptions", description: "=Gift for Rosa T.",
                                  person: "Rosa T.", sub_kind: "gift", sub_product: "gv_print", sub_term: 12, amount_cents: 3600, funder: "district",
                                  notes: "Rosa's birthday" }, SP)]);
          const strings = { "field.date": "Fecha", "field.amount": "Monto", "req.receipt_paper": "En papel", "sub_kind.gift": "Regalo" };
          const hidden = G.claimCSV(G.claimLines(E, SP, { funder: "district", ...SEPT, lang: "es", strings }), strings, "es");
          const shown = G.claimCSV(G.claimLines(E, SP, { funder: "district", ...SEPT, lang: "es", strings, includeNames: true }), strings, "es");
          out({ hidden, shown, junk: [G.claimCSV(null), G.claimCSV({})] });""")
        rows = r["hidden"].lstrip("﻿").split("\r\n")
        self.assertTrue(r["hidden"].startswith("﻿") and r["hidden"].endswith("\r\n"))
        self.assertEqual(rows[0], "Fecha,Description,Category,From,To,Miles,Rate,Monto,Receipt")   # the page's words, else English
        self.assertEqual(rows[1:4], [
            "2026-09-02,Big Book,Libros y literatura,,,,,24.00,En papel",
            "2026-09-05,Home → Tyler,Millas recorridas,Home,Tyler,184.6,0.14,25.84,",
            "2026-09-12,Suscripciones a revistas · Regalo · 12 months,Suscripciones a revistas,,,,,36.00,",
        ])
        self.assertNotIn("Rosa", r["hidden"])
        self.assertIn(",'=Gift for Rosa T.,", r["shown"])                        # names asked for; the guard '
        self.assertNotIn("birthday", r["shown"])
        self.assertEqual(r["junk"], ["", "﻿Date,Description,Category,From,To,Miles,Rate,Amount,Receipt\r\n"])

    def test_money_back_from_a_person_settles_their_purchases(self):
        r = core(self, LEDGER + r"""
          const E = [
            N({ id: "h1", type: "expense", date: "2026-08-01", category: "subscriptions", sub_kind: "helped", person: "José R.", description: "A", amount_cents: 1500, funder: "p_jose", claim_status: "to_request" }, SP),
            N({ id: "h2", type: "expense", date: "2026-08-05", category: "subscriptions", sub_kind: "helped", person: "José R.", description: "B", amount_cents: 3600, funder: "p_jose", claim_status: "submitted" }, SP),
            N({ id: "h3", type: "expense", date: "2026-08-09", category: "subscriptions", sub_kind: "helped", person: "José R.", description: "C", amount_cents: 1000, funder: "p_jose", claim_status: "to_request" }, SP),
            N({ id: "x", type: "expense", date: "2026-08-02", category: "books", description: "Mine", amount_cents: 999, funder: "district", claim_status: "to_request" }, SP),
          ];
          const got = (cents) => G.settleRepayments(E.concat(cents ? [N({ id: "r", type: "received", date: "2026-09-01", category: "repayment", amount_cents: cents, funder: "p_jose" }, SP)] : []), SP, "p_jose");
          const settledBefore = E.map((e) => e.id === "h1" ? { ...e, repaid: "repaid", claim_status: "paid" } : e)
            .concat([N({ id: "r1", type: "received", date: "2026-09-01", category: "repayment", amount_cents: 1500, funder: "p_jose" }, SP),
                     N({ id: "r2", type: "received", date: "2026-09-02", category: "repayment", amount_cents: 3600, funder: "p_jose" }, SP)]);
          out({ none: got(0), part: got(1400), one: got(2000), two: got(5100), all: got(9999),
                again: G.settleRepayments(settledBefore, SP, "p_jose"), notAPerson: G.settleRepayments(E, SP, "district"), junk: G.settleRepayments(null, null, "") });""")
        self.assertEqual(r["none"], [])
        self.assertEqual(r["part"], [])                     # $14 does not cover the first ($15): nothing marked
        self.assertEqual(r["one"], ["h1"])                  # oldest first, stopping at the first it does not cover
        self.assertEqual(r["two"], ["h1", "h2"])
        self.assertEqual(r["all"], ["h1", "h2", "h3"])
        self.assertEqual(r["again"], ["h2"])                # a repayment already matched is not counted twice
        self.assertEqual((r["notAPerson"], r["junk"]), ([], []))


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
                photo: ex.filter((e) => e.receipt === "photo").length,
                trips: ex.filter((e) => e.type === "mileage").map((e) => [e.miles, e.trips, e.no_miles, e.amount_cents, e.claim_status, e.activity, e.role]),
                activities: G.summary(ex, S, {}).by_activity.map((a) => [a.id, a.miles, a.trips]) });""")
        self.assertEqual(r["n"], 21)
        self.assertTrue(r["allExample"])
        self.assertTrue(r["dated"])
        self.assertEqual(r["invalid"], [])
        self.assertEqual(r["types"], ["expense", "giveaway", "mileage", "received", "stock"])
        self.assertEqual(r["templates"], sorted(["general", "books", "subscription", "lodging", "meal", "printing", "travel", "mileage", "received", "giveaway", "stock"]))
        self.assertEqual(r["cats"], ["books", "giveaways", "giveaways", "subscriptions", "subscriptions", "lodging", "meals", "printing", "travel",
                                     "registration", "contributions", "mileage", "mileage", "reimbursement", "advance", "stock_in", "given", "given", "given",
                                     "mileage", "mileage"])
        self.assertEqual(r["people"], ["Maria G.", "José R.", "Rosa T."])       # first name + initial only
        # the Assembly (round trip), the district meeting (odometer: 38 mi), three days at a convention's table
        # (27.3 × 2 × 3 = 163.8 mi × $0.14 = $22.932 → 2293) and a workshop reached riding with someone (no miles)
        self.assertEqual(r["trips"], [[184.6, "", False, 2584, "submitted", "assembly", "Attended"],
                                      [38, "", False, 532, "none", "district", "Gave the GVR report"],
                                      [163.8, 3, False, 2293, "none", "table", "Table support"],
                                      ["", "", True, 0, "none", "workshop", "Tech setup"]])
        self.assertEqual(r["activities"], [["assembly", 184.6, 1], ["district", 38, 1], ["table", 163.8, 3], ["workshop", 0, 1], ["", 0, 0]])
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
        self.assertEqual(r["ids"], 21)
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

    def test_sort_by_the_names_in_the_page_language(self):
        # categories and funders sort by the names the visitor reads ("Comidas" first on the Spanish
        # page, not "Libros" because "Books" comes first in English); English when no language is given
        r = core(self, LEDGER + r"""
          const T = (k, lang) => ids(G.sortEntries(L, k, "asc", SP, lang));
          out([T("category", "es"), T("category", "en"), T("category"), T("funder", "es"), T("funder", "en")]);""")
        # es: Comidas d · Contribuciones i · Cuotas f · Dinero m · Estacionamiento e · Hotel h b · Impresiones r · Libros a ·
        #     Literatura g · Me lo devolvió n · Millas c · Otros s · Recibido o · Reembolso l · Regalado q p · Suscripciones k j
        self.assertEqual(r[0], "difmehbragncsolqpkj")
        # en: Books a · Given q p · Hotel h b · Literature g · Magazine k j · Meals d · Miles c · Money m · Other s · Paid back n ·
        #     Parking e · Printing r · Received o · Registration f · Reimbursement l · Seventh i   (ties: newest first)
        self.assertEqual(r[1], "aqphbgkjdcmsnerofli")
        self.assertEqual(r[2], r[1])
        # no funder (the giveaways) first; then Área 65 · José R. · Mi distrito · Mi grupo base · Yo (es)
        #                                   and Area 65 · José R. · Me (self-supported) · My district · My home group (en)
        self.assertEqual(r[3], "qplhognjrcbafdmkies")
        self.assertEqual(r[4], "qplhognjkiesrcbafdm")


class TripsAndRides(unittest.TestCase):
    """Several trips on one entry (one-way × 2 × trips) and a trip with no miles ("rode with someone")."""

    def test_trip_miles_and_the_one_way_back(self):
        r = core(self, r"""
          out({
            miles: [G.tripMiles(58.7, true, "", "", 3), G.tripMiles(21.4, true, "", "", 7), G.tripMiles(27.3, true, "", "", 3),
                    G.tripMiles(10, false, "", "", 4), G.tripMiles(10, true, "", "", ""), G.tripMiles(10, true, "", "", 0), G.tripMiles(10, true, "", "", "x"),
                    G.tripMiles(10, true, 100, 150, 3), G.tripMiles(1, false, "", "", 5000)],
            counts: [G.tripCount(""), G.tripCount(null), G.tripCount(0), G.tripCount(-2), G.tripCount("3"), G.tripCount(2.6), G.tripCount(1e6)],
            oneWay: [G.oneWayMiles(352.2, true, 3), G.oneWayMiles(25.3, true, ""), G.oneWayMiles(63.7, true, 1), G.oneWayMiles(10, true, 3),
                     G.oneWayMiles(38, false, ""), G.oneWayMiles("", true, 2), G.oneWayMiles(0, true, 2)],
            // every total of 0.1 … 300 mi over 1 … 9 trips, one way or there and back: the one-way miles the
            // form shows multiply back to the same total
            grid: (() => { const bad = []; for (let t = 1; t <= 3000; t++) for (let n = 1; n <= 9; n++) for (const rt of [false, true]) {
              const total = t / 10, v = G.oneWayMiles(total, rt, n);
              if (G.tripMiles(v, rt, "", "", n) !== total) bad.push([total, rt, n, v]);
              if (String(v).replace(/^\d+\.?/, "").length > 6) bad.push(["long", total, rt, n, v]);
            } return bad.slice(0, 5); })(),
          });""")
        # 58.7 × 2 × 3 = 352.2 (the State Convention); 21.4 × 2 × 7 = 299.6 (seven CityWide Saturdays); the odometer is
        # the whole trip; 999 trips at most
        self.assertEqual(r["miles"], [352.2, 299.6, 163.8, 40, 20, 20, 20, 50, 999])
        self.assertEqual(r["counts"], [1, 1, 1, 1, 3, 3, 999])
        self.assertEqual(r["oneWay"], [58.7, 12.65, 31.85, 1.67, 38, "", ""])
        self.assertEqual(r["grid"], [])

    def test_the_entry(self):
        r = core(self, r"""
          const pick = (e) => [e.miles, e.trips, e.round_trip, e.no_miles, e.rate, e.amount_cents, e.claim_status, e.odometer_start, e.description];
          const v = (e) => G.validateEntry(e, S).map((x) => x.field + ":" + x.key.replace("expenses.err.", ""));
          const base = { type: "mileage", date: "2026-07-24", from: "Home", to: "Hilton Fort Worth", rate: "0.30", funder: "district", claim_status: "to_request" };
          const three = N({ ...base, round_trip: true, trips: 3, miles: 352.2 });
          const one = N({ ...base, round_trip: true, trips: "1", miles: 68 });
          const odo = N({ ...base, trips: 3, odometer_start: 100, odometer_end: 150 });
          const junk = N({ ...base, trips: "abc", miles: 10 });
          const notMileage = N({ type: "expense", date: "2026-07-24", description: "x", amount_cents: 100, trips: 3, no_miles: true });
          // Big Country: rode with someone — no miles, no money, nothing to ask, whatever the row says
          const ride = N({ ...base, no_miles: "yes", miles: 412, round_trip: true, trips: 2, odometer_start: 5, odometer_end: 9, amount_cents: 999,
                           person: "Area Archives", event: "Big Country 41st AA Conference", from: "", to: "" });
          const blank = N({ ...base, miles: "" });
          out({ three: pick(three), one: pick(one), odo: pick(odo), junk: pick(junk), notMileage: [notMileage.trips, notMileage.no_miles],
                ride: pick(ride).concat([ride.person, v(ride)]), blank: v(blank), again: JSON.stringify(N(ride)) === JSON.stringify(ride) });""")
        # 352.2 × $0.30 = $105.66: the miles are the whole distance (the trips are in them)
        self.assertEqual(r["three"], [352.2, 3, True, False, "0.30", 10566, "to_request", "", "Home → Hilton Fort Worth"])
        self.assertEqual(r["one"], [68, "", True, False, "0.30", 2040, "to_request", "", "Home → Hilton Fort Worth"])   # one trip: blank
        self.assertEqual(r["odo"], [50, "", False, False, "0.30", 1500, "to_request", 100, "Home → Hilton Fort Worth"])  # the odometer: no trips
        self.assertEqual(r["junk"][1], "")
        self.assertEqual(r["notMileage"], ["", False])
        self.assertEqual(r["ride"], ["", "", False, True, "", 0, "none", "", "Big Country 41st AA Conference", "Area Archives", []])
        self.assertEqual(r["blank"], ["miles:miles_required"])                 # a trip that was driven still needs its miles
        self.assertTrue(r["again"])

    def test_requests_say_how_many_trips(self):
        r = core(self, r"""
          const E = [N({ id: "t3", type: "mileage", date: "2026-07-24", from: "Home", to: "Fort Worth", round_trip: true, trips: 3, miles: 352.2, rate: "0.30",
                         funder: "district", event: "State Convention" }),
                     N({ id: "t1", type: "mileage", date: "2026-03-14", from: "Home", to: "Dallas", trips: 2, miles: 46.2, rate: "0.30", funder: "district" }),
                     N({ id: "nm", type: "mileage", date: "2026-09-04", no_miles: true, event: "Big Country", funder: "district", claim_status: "to_request" })];
          const c = G.claimLines(E, S, { funder: "district", lang: "en", strings: { "claim.trips_round": "{n} round trips" } });
          out({ ids: c.ids, lines: c.lines.map((l) => l.description), trips: c.mileage.map((m) => m.trips), text: G.claimText(c, {}, "en") });""")
        self.assertEqual(r["ids"], ["t1", "t3"])                                 # a trip with no miles is never asked for
        self.assertEqual(r["lines"], ["Home → Dallas · 2 trips", "Home → Fort Worth · 3 round trips"])
        self.assertEqual(r["trips"], [2, 3])
        self.assertIn("Home → Fort Worth · 3 round trips · 352.2 mi × $0.30 · $105.66", r["text"])


class Activities(unittest.TestCase):
    """The service activities: a list of the settings (built-in from config/expenses.yml, renamed,
    hidden and extended by the visitor), one per entry, read back from a CSV by id or by name."""

    def test_settings(self):
        r = core(self, r"""
          // a visitor's settings from before 1.1.0: no activities, and builtins_seen without them
          const old = plain(S); delete old.activities; delete old.builtins_seen.activities;
          const m = G.mergeDefaults(CONFIG, old);
          const st = plain(m);
          st.activities.find((a) => a.id === "district").name = "District 22 meetings";
          st.activities.find((a) => a.id === "other").hidden = true;
          st.activities.push({ id: "x_retreat", name: "Retreats", hidden: false, order: 20, builtin: false });
          const cfg2 = plain(CONFIG);
          cfg2.activities.push({ id: "fair", name: { en: "Service fairs", es: "Ferias de servicio" }, builtin: true, hidden: false, order: 7 });
          cfg2.activities.find((a) => a.id === "table").name = { en: "Information tables, booths & conventions", es: "Mesas, puestos y convenciones" };
          const m2 = G.mergeDefaults(cfg2, st);
          const st2 = plain(m2); st2.activities = st2.activities.filter((a) => a.id !== "x_retreat");
          out({ first: m.activities.map((a) => [a.id, a.builtin, a.hidden]), seen: m.builtins_seen.activities.length,
                later: m2.activities.map((a) => [a.id, G.label(a.name, "es"), !!a.hidden]),
                gone: G.mergeDefaults(cfg2, st2).activities.some((a) => a.id === "x_retreat"),
                fresh: G.emptyState(CONFIG).settings.activities.length, none: G.mergeDefaults({}, null).activities });""")
        self.assertEqual(r["first"], [[a, True, False] for a in ["assembly", "district", "table", "workshop", "committee", "group", "other"]])
        self.assertEqual(r["seen"], 7)
        self.assertEqual(r["later"], [["assembly", "Asambleas y reuniones del comité de Área", False], ["district", "District 22 meetings", False],
                                      ["table", "Mesas, puestos y convenciones", False], ["workshop", "Talleres y eventos", False],
                                      ["committee", "Reuniones del comité de Grapevine / La Viña", False], ["group", "Grupos y visitas a grupos", False],
                                      ["other", "Otro servicio", True], ["x_retreat", "Retreats", False], ["fair", "Ferias de servicio", False]])
        self.assertFalse(r["gone"])                                              # a deleted custom one never comes back
        self.assertEqual(r["fresh"], 7)
        self.assertEqual(r["none"], [])

    def test_import_by_id_or_name(self):
        r = core(self, r"""
          const csv = "date,type,amount,miles,rate,activity,activity_label,role,trips,no_miles,ref,description\n" +
            "2026-03-20,mileage,,63,0.30,,Assemblies & Area committee meetings,Attended,,,,\n" +
            "2026-05-10,mileage,,60.4,0.30,,reuniones del DISTRITO,,,,,\n" +
            "2026-07-24,mileage,,352.2,0.30,table,whatever it says,Table support,3,,,\n" +
            "2026-09-04,mileage,,,,,Service fairs,Table support,,yes,,\n" +
            "2026-09-05,expense,12,,,,Service fairs,,,,Conf. 7,Badges\n";
          const plan = G.planImport(csv, [], S, {});
          const after = G.applyImport({ v: 1, entries: [], settings: S, meta: {} }, plan, {});
          const mapped = G.planImport("Date,Miles,Kind of service\n2026-03-20,63,Workshops & events\n", [], S, { mapping: { date: 0, miles: 1, activity: 2 } });
          out({ errors: plan.errors, rows: plan.add.map((e) => [e.type, e.activity, e.role, e.trips, e.no_miles, e.miles, e.amount_cents, e.ref]),
                news: plan.newActivities.map((a) => [a.id, a.name, a.builtin]), kept: after.settings.activities.slice(-1).map((a) => a.id),
                mapped: mapped.add.map((e) => e.activity), invalid: G.validateEntry(N({ type: "expense", date: "2026-09-01", description: "x", activity: "nope" }), S)
                  .map((x) => x.field + ":" + x.key) });""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["rows"], [
            ["mileage", "assembly", "Attended", "", False, 63, 1890, ""],          # by its English name
            ["mileage", "district", "", "", False, 60.4, 1812, ""],                # by its Spanish name (case and accents aside)
            ["mileage", "table", "Table support", 3, False, 352.2, 10566, ""],     # by id
            ["mileage", "a_service_fairs", "Table support", "", True, "", 0, ""],  # a new one …
            ["expense", "a_service_fairs", "", "", False, "", 1200, "Conf. 7"],    # … made once
        ])
        self.assertEqual(r["news"], [["a_service_fairs", "Service fairs", False]])
        self.assertEqual(r["kept"], ["a_service_fairs"])
        self.assertEqual(r["mapped"], ["workshop"])
        self.assertEqual(r["invalid"], ["activity:expenses.err.activity_unknown"])

    def test_filters_search_and_totals(self):
        r = core(self, r"""
          const E = [
            N({ id: "a", type: "mileage", date: "2026-03-20", miles: 63, rate: "0.30", activity: "assembly", role: "Attended" }),
            N({ id: "b", type: "mileage", date: "2026-07-24", miles: 352.2, round_trip: true, trips: 3, rate: "0.30", activity: "table", role: "Table support" }),
            N({ id: "c", type: "mileage", date: "2026-09-04", no_miles: true, activity: "workshop", person: "Area Archives" }),
            N({ id: "d", type: "expense", date: "2026-03-20", category: "lodging", description: "Room", amount_cents: 15000, activity: "assembly", ref: "Check #101" }),
            N({ id: "e", type: "expense", date: "2026-03-21", category: "books", description: "Books", amount_cents: 2400 }),
            N({ id: "f", type: "expense", date: "2026-03-21", category: "lodging", description: "Paid by the Area", amount_cents: 9000, method: "direct", funder: "area", activity: "assembly" }),
          ];
          const F = (f) => G.filterEntries(E, f, S).map((e) => e.id).join("");
          out({ f: [F({ activities: ["assembly"] }), F({ activities: [""] }), F({ q: "mesas" }), F({ q: "check #101" }), F({ q: "table support" }), F({ q: "archives" })],
                by: G.summary(E, S, {}).by_activity, trips: G.summary(E, S, {}).trips });""")
        self.assertEqual(r["f"], ["adf", "e", "b", "d", "b", "c"])
        # assembly: 63 mi × $0.30 = $18.90 + the room $150 (the one the Area paid is not your spending: no cents, still an entry)
        self.assertEqual(r["by"], [
            {"id": "assembly", "count": 3, "cents": 16890, "miles": 63, "mileage_cents": 1890, "trips": 1, "no_miles": 0},
            {"id": "table", "count": 1, "cents": 10566, "miles": 352.2, "mileage_cents": 10566, "trips": 3, "no_miles": 0},
            {"id": "workshop", "count": 1, "cents": 0, "miles": 0, "mileage_cents": 0, "trips": 1, "no_miles": 1},
            {"id": "", "count": 1, "cents": 2400, "miles": 0, "mileage_cents": 0, "trips": 0, "no_miles": 0},
        ])
        self.assertEqual(r["trips"], 5)


# Subscriptions on 1 October 2026 (renewal reminders 60 days ahead), worked out by hand in the test.
SUBS = r"""
const TODAY = "2026-10-01";
const sub = (id, date, person, product, kind, start, term, more) => N(Object.assign({ id, type: "expense", date, category: "subscriptions",
  description: "Sub " + id, person, sub_product: product, sub_kind: kind, sub_start: start, sub_term: term, amount_cents: 3600, funder: "me" }, more || {}));
const SUBS = [
  sub("s1", "2025-10-15", "Maria G.", "gv_print", "gift", "2025-10-20", 12),                 // ends Oct 20 — but renewed by s2
  sub("s2", "2026-10-01", "maria  g.", "gv_complete", "gift", "2026-10-20", 12),             // the renewal (an upgrade: still Grapevine), starts later
  sub("s3", "2025-06-01", "Luis M.", "lv_print", "gift", "2025-06-01", 12),                  // ended June 1, nothing followed
  sub("s4", "2026-03-01", "Carry the Message", "gv_print", "gift", "2026-03-01", 12, { quantity: 5 }),   // five at once
  sub("s5", "2026-03-01", "Carry the Message", "gv_print", "gift", "2026-03-01", 12),        // the same day: not a renewal of s4
  sub("s6", "2025-11-15", "", "lv_online", "self", "2025-11-15", 12),                        // my own, ends in 45 days
  sub("s7", "2026-09-01", "Rosa T.", "gv_print", "helped", "2026-09-01", 12),
  sub("s8", "2026-05-05", "Juan S.", "gv_print", "gift", "", ""),                            // no start, no term: no end
  sub("s9", "2025-12-01", "", "gv_print", "group", "2025-12-01", 12),                        // the group's: ends in 61 days
  N({ id: "bk", type: "expense", date: "2026-03-01", category: "books", description: "Big Book", amount_cents: 1200 }),
];
"""


class Subscriptions(unittest.TestCase):
    def test_statuses_and_order(self):
        r = core(self, SUBS + r"""
          const list = G.subscriptions(SUBS, S, TODAY, 60);
          out({ rows: list.map((s) => [s.id, s.status, s.end, s.days_left, s.qty, s.magazine, s.upcoming, s.renewed_by]),
                renewals: G.renewals(SUBS, TODAY, 60).map((x) => [x.entry.id, x.days_left]), mileage: G.subscriptions([N({ type: "mileage", date: TODAY, miles: 5, rate: "0.14", sub_kind: "gift" })], S, TODAY).length });""")
        self.assertEqual(r["rows"], [
            ["s6", "ending", "2026-11-15", 45, 1, "lv", False, ""],
            ["s3", "ended", "2026-06-01", -122, 1, "lv", False, ""],
            ["s9", "active", "2026-12-01", 61, 1, "gv", False, ""],
            ["s4", "active", "2027-03-01", 151, 5, "gv", False, ""],
            ["s5", "active", "2027-03-01", 151, 1, "gv", False, ""],
            ["s7", "active", "2027-09-01", 335, 1, "gv", False, ""],
            ["s2", "active", "2027-10-20", 384, 1, "gv", True, ""],
            ["s8", "no_end", "", None, 1, "gv", False, ""],
            ["s1", "renewed", "2026-10-20", 19, 1, "gv", False, "s2"],
        ])
        self.assertEqual(r["renewals"], [["s6", 45]])
        self.assertEqual(r["mileage"], 0)

    def test_gifts_with_no_name(self):
        # Two unnamed gift subscriptions months apart are two gifts: overlapping, they never renew each other.
        # One with no name is renewed by another with no name, of the same magazine and kind, that starts the
        # day it ends ("Record the renewal" writes that) — or, failing that, by the earliest that starts after
        # it ended (a renewal recorded late starts that day); each renews one. Your own subscription needs no
        # name to be renewed by the next one.
        r = core(self, SUBS + r"""
          const anon = [sub("a1", "2026-01-10", "", "gv_print", "gift", "2026-01-10", 12), sub("a2", "2026-03-10", "", "gv_print", "gift", "2026-03-10", 12),
                        sub("o1", "2025-01-01", "", "lv_online", "self", "2025-01-01", 12), sub("o2", "2026-01-01", "", "lv_online", "self", "2026-01-01", 12)];
          const cont = [
            sub("g1", "2025-11-15", "", "gv_print", "gift", "2025-11-15", 12), sub("g1r", "2026-09-30", "", "gv_complete", "gift", "2026-11-15", 12),  // renewed on time
            sub("g2", "2025-11-25", "", "gv_print", "gift", "2025-11-25", 12), sub("g3", "2025-11-25", "", "gv_print", "gift", "2025-11-25", 12),     // two that end Nov 25 …
            sub("g23", "2026-09-30", "", "gv_print", "gift", "2026-11-25", 12),                                                                     // … renewed by one
            sub("g4", "2025-03-05", "", "lv_print", "gift", "2025-03-05", 12), sub("g4r", "2026-06-10", "", "lv_print", "gift", "2026-06-10", 12),     // ended March, renewed in June
            sub("g5", "2025-03-05", "", "lv_print", "", "2025-03-05", 12),                                                                          // no kind said: not a gift's
          ];
          // a continuation is matched before a late one: e2r starts the day e2 ends, so it is e2's (e1, ended before, stays ended)
          const order = [sub("e1", "2025-01-10", "", "gv_print", "gift", "2025-01-10", 12), sub("e2", "2025-03-01", "", "gv_print", "gift", "2025-03-01", 12),
                         sub("e2r", "2026-02-20", "", "gv_print", "gift", "2026-03-01", 12)];
          const st = (l) => G.subscriptions(l, S, TODAY, 60).map((s) => [s.id, s.status, s.renewed_by]);
          out({ anon: st(anon), cont: st(cont), order: st(order), reminders: G.renewals(cont, TODAY, 60).map((x) => [x.entry.id, x.days_left]) });""")
        self.assertEqual(sorted(r["anon"]), [["a1", "active", ""], ["a2", "active", ""], ["o1", "renewed", "o2"], ["o2", "active", ""]])
        self.assertEqual(sorted(r["cont"]), [["g1", "renewed", "g1r"], ["g1r", "active", ""], ["g2", "renewed", "g23"], ["g23", "active", ""],
                                             ["g3", "ending", ""], ["g4", "renewed", "g4r"], ["g4r", "active", ""], ["g5", "ended", ""]])
        self.assertEqual(sorted(r["order"]), [["e1", "ended", ""], ["e2", "renewed", "e2r"], ["e2r", "active", ""]])
        # the reminder goes once a renewal is recorded: only g3 (ends in 55 days) still asks
        self.assertEqual(r["reminders"], [["g3", 55]])

    def test_counts(self):
        r = core(self, SUBS + r"""
          const list = G.subscriptions(SUBS, S, TODAY, 60);
          out({ y2026: G.subscriptionCounts(list, { from: "2026-01-01", to: "2026-12-31" }), all: G.subscriptionCounts(list, {}), junk: G.subscriptionCounts(null) });""")
        # bought in 2026: s2, s4 (× 5), s5, s7 (helped), s8 — 9 subscriptions, 8 of them gifts, all Grapevine
        y = r["y2026"]
        self.assertEqual((y["bought"], y["gifted"], y["by_kind"], y["by_magazine"], y["gifted_by_magazine"]),
                         (9, 8, {"gift": 8, "helped": 1}, {"gv": 9}, {"gv": 8}))
        # today: running = s1 (renewed, still running until Oct 20) + s4 × 5 + s5 + s6 + s7 + s9; s2 starts later
        self.assertEqual((y["running"], y["ending"], y["ended"], y["renewed"]), (10, 1, 1, 1))
        self.assertEqual((r["all"]["bought"], r["all"]["by_kind"]), (13, {"gift": 10, "helped": 1, "self": 1, "group": 1}))
        self.assertEqual(r["junk"]["bought"], 0)

    def test_the_calendar_file(self):
        r = core(self, SUBS + r"""
          const list = G.subscriptions(SUBS.concat([sub("s10", "2026-02-02", "Ana, P.; x\\y", "lv_complete", "gift", "2026-02-02", 12)]), S, TODAY, 60);
          const strings = { "sub_product.gv_print": "Grapevine — print", "sub_product.lv_online": "La Viña — online", "sub_kind.gift": "A gift",
                            "expenses.subs.ics_summary": "Renew: {product}" };
          const text = G.subscriptionsICS(list, { days: 60, lang: "en", strings, url: "https://neta65.github.io/aagrapevine/tracker/#giveaways",
                                                  now: new Date("2026-10-01T15:04:05.678Z") });
          const one = G.subscriptionsICS(list.filter((s) => s.id === "s6"), { days: 1, now: new Date("2026-10-01T15:04:05Z") });
          out({ text, one, empty: G.subscriptionsICS([], {}), junk: G.subscriptionsICS([null, {}, { id: "x y", end: "2027-01-01", status: "active" }], {}) });""")
        text = r["text"]
        self.assertTrue(text.endswith("\r\n"))
        self.assertNotRegex(text.replace("\r\n", ""), r"[\r\n]")                  # CRLF only
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75, line)            # folded at 75 octets (an accent is 2)
        lines = text.replace("\r\n ", "").split("\r\n")                          # unfolded
        self.assertEqual(lines[:2], ["BEGIN:VCALENDAR", "VERSION:2.0"])
        self.assertEqual(lines[-2:], ["END:VCALENDAR", ""])
        uids = [x for x in lines if x.startswith("UID:")]
        # the ones to renew, in the list's order: ending, then active (s1 renewed, s3 ended, s8 no end are not);
        # s2 renewed s1, so its event is s1's, moved (UID of the line's first, SEQUENCE 1)
        self.assertEqual(uids, ["UID:gvlv-sub-" + i + "@neta65-tracker" for i in ["s6", "s9", "s10", "s4", "s5", "s7", "s1"]])
        self.assertEqual([x for x in lines if x.startswith("SEQUENCE:")], ["SEQUENCE:0"] * 6 + ["SEQUENCE:1"])
        events = text.replace("\r\n ", "").split("BEGIN:VEVENT")
        ev = events[1]
        self.assertIn("DTSTAMP:20261001T150405Z", ev)
        self.assertIn("DTSTART;VALUE=DATE:20261115\r\nDTEND;VALUE=DATE:20261116", ev)
        self.assertIn("SUMMARY:Renew: La Viña — online", ev)
        # s6 ends in 45 days, sooner than the 60 of the reminder (that day has gone by): 9 AM tomorrow, Oct 2 —
        # 43 days and 15 hours before Nov 15; s9, 61 days away, gets its 60 days (also Oct 2, 9 AM)
        self.assertIn("TRIGGER:-P43DT15H", ev)
        self.assertIn("TRIGGER:-P59DT15H", events[2])
        self.assertIn("URL:https://neta65.github.io/aagrapevine/tracker/#giveaways", ev)
        self.assertIn("SUMMARY:Renew: Grapevine — print · Rosa T.", text.replace("\r\n ", ""))
        self.assertIn("SUMMARY:Renew: lv_complete · Ana\\, P.\\; x\\\\y", text.replace("\r\n ", ""))   # escaped
        self.assertIn("TRIGGER:-PT15H", r["one"])                                 # 1 day before: 9 AM the day before
        self.assertEqual(r["empty"].count("BEGIN:VEVENT"), 0)
        self.assertEqual(r["junk"].count("BEGIN:VEVENT"), 0)

    def test_no_alarm_in_the_past_and_a_renewal_moves_its_event(self):
        r = core(self, SUBS + r"""
          const now = new Date("2026-10-01T15:04:05Z");
          // with the ones that end today and tomorrow, at 60 days of reminder and at 7
          const list = G.subscriptions(SUBS.concat([sub("t0", "2025-10-01", "Ana P.", "gv_print", "gift", "2025-10-01", 12),
                                                    sub("t1", "2025-10-02", "Ben K.", "gv_print", "gift", "2025-10-02", 12)]), S, TODAY, 60);
          const files = [60, 7, 1].map((days) => G.subscriptionsICS(list, { days, now }));
          // "Record the renewal" (the new term starts where the old one ends), and the next year's too
          const old = [sub("o2", "2025-11-15", "Ana P.", "lv_print", "gift", "2025-11-15", 12)];
          const renewed = old.concat([sub("n2", "2026-10-01", "Ana P.", "lv_print", "gift", "2026-11-15", 12)]);
          const again = renewed.concat([sub("n3", "2027-10-01", "Ana P.", "lv_print", "gift", "2027-11-15", 12)]);
          // …and a gift with no name renewed the same way
          const anon = [sub("u1", "2025-11-15", "", "gv_print", "gift", "2025-11-15", 12), sub("u1r", "2026-10-01", "", "gv_print", "gift", "2026-11-15", 12)];
          const file = (l) => G.subscriptionsICS(G.subscriptions(l, S, TODAY, 60), { days: 60, now });
          out({ files, before: file(old), after: file(renewed), twice: file(again), anon: file(anon) });""")
        now = dt.datetime(2026, 10, 1, 15, 4, 5)        # the visitor's wall clock: an all-day event and its alarm are "floating"

        def events(text):                                # each event's fields (the alarm's TRIGGER among them)
            return [dict(x.split(":", 1) for x in ev.split("\r\n") if ":" in x and not x.startswith(("BEGIN", "END")))
                    for ev in text.replace("\r\n ", "").split("BEGIN:VEVENT")[1:]]

        def alarm(ev):                                   # when it rings: midnight of the (all-day) end date + TRIGGER
            day = dt.datetime.strptime(ev["DTSTART;VALUE=DATE"], "%Y%m%d")
            if "TRIGGER" not in ev:
                return None
            m = re.fullmatch(r"(-?)P(?:(\d+)D)?T(\d+)H", ev["TRIGGER"])
            self.assertTrue(m, ev["TRIGGER"])
            delta = dt.timedelta(days=int(m.group(2) or 0), hours=int(m.group(3)))
            return day - delta if m.group(1) else day + delta

        for days, text in zip((60, 7, 1), r["files"]):
            evs = events(text)
            self.assertEqual(len(evs), 8, days)                                   # 6 to renew + the ones ending today and tomorrow
            for ev in evs:
                a = alarm(ev)
                if ev["DTSTART;VALUE=DATE"] == "20261001":
                    self.assertIsNone(a, "ends today: no alarm")
                    continue
                self.assertGreater(a, now, (days, ev["UID"], ev.get("TRIGGER")))   # never an alarm already past …
                self.assertEqual(a.hour, 9)                                       # … always at 9 AM
                self.assertLessEqual(a, dt.datetime.strptime(ev["DTSTART;VALUE=DATE"], "%Y%m%d") + dt.timedelta(hours=9))
        # the one that ends tomorrow: 9 AM on that day; the 60-day reminder of one 384 days away: 60 days before
        by_uid = {e["UID"]: e for e in events(r["files"][0])}
        self.assertEqual(by_uid["gvlv-sub-t1@neta65-tracker"]["TRIGGER"], "PT9H")
        self.assertEqual(by_uid["gvlv-sub-s1@neta65-tracker"]["TRIGGER"], "-P59DT15H")
        # a renewal moves the event of its line (the same UID, a higher SEQUENCE, the new date) — never a second one
        line = [[(e["UID"], e["SEQUENCE"], e["DTSTART;VALUE=DATE"]) for e in events(r[k])] for k in ("before", "after", "twice", "anon")]
        self.assertEqual(line[0], [("gvlv-sub-o2@neta65-tracker", "0", "20261115")])
        self.assertEqual(line[1], [("gvlv-sub-o2@neta65-tracker", "1", "20271115")])
        self.assertEqual(line[2], [("gvlv-sub-o2@neta65-tracker", "2", "20281115")])
        self.assertEqual(line[3], [("gvlv-sub-u1@neta65-tracker", "1", "20271115")])


class GiveawayLedger(unittest.TestCase):
    def test_a_period(self):
        r = core(self, LEDGER + r"""
          const row = (it) => [it.item, it.format, it.start, it.bought_qty, it.received_qty, it.given_qty, it.on_hand, it.negative, it.cost_cents, it.avg_unit_cents];
          const L5 = G.giveawayLedger(L, { from: "2026-09-05", to: "2026-09-30" }), sept = G.giveawayLedger(L, SEPT), oct = G.giveawayLedger(L, { from: "2026-10-01", to: "2026-10-31" });
          out({ l5: L5.items.map(row), t5: L5.totals, sept: sept.items.map(row), all: JSON.stringify(G.giveawayLedger(L, {})) === JSON.stringify(sept),
                oct: oct.items.map(row), events: L5.items.map((it) => it.events) });""")
        # before the 5th: 20 bought + 15 received = 35 Grapevine on hand; from the 5th: 12 given at the Assembly, 30 La Viña at
        # the workshop (more than was ever recorded: −30, flagged); the period bought nothing, so "each" is the earlier $2.50
        self.assertEqual(r["l5"], [["Grapevine", "gv", 35, 0, 0, 12, 23, False, 0, 250], ["La Viña", "lv", 0, 0, 0, 30, -30, True, 0, 0]])
        self.assertEqual(r["t5"], {"start": 35, "bought": 0, "received": 0, "given": 42, "on_hand": -7, "cost_cents": 0,
                                   "by_format": {"gv": {"start": 35, "bought": 0, "received": 0, "given": 12, "on_hand": 23},
                                                 "lv": {"start": 0, "bought": 0, "received": 0, "given": 30, "on_hand": -30}}})
        self.assertEqual(r["sept"], [["Grapevine", "gv", 0, 20, 15, 12, 23, False, 5000, 250], ["La Viña", "lv", 0, 0, 0, 30, -30, True, 0, 0]])
        self.assertTrue(r["all"])
        # a later month with nothing given: what is on hand is still there (start = end)
        self.assertEqual(r["oct"], [["Grapevine", "gv", 23, 0, 0, 0, 23, False, 0, 250], ["La Viña", "lv", -30, 0, 0, 0, -30, True, 0, 0]])
        self.assertEqual(r["events"], [[{"event": "Fall Assembly", "qty": 12}], [{"event": "Workshop", "qty": 30}]])


# A District GVR's 2026 expense report (a record of what the service cost, not a request), entered as the
# tracker keeps it — modeled on a real one, its names, references and distances invented: three
# assemblies' lodging and every trip at $0.30 a mile, round trips from home, grouped by service activity.
# Worked out by hand: lodging $469.46; assemblies & ACMs 485.6 mi $145.68; district meetings 221.2 mi
# $66.36; information tables & conventions 815.6 mi $244.68; workshops & events 1,037.8 mi $311.34;
# mileage 2,560.2 mi $768.06; total cost of service $1,237.52.
OWNERS_REPORT = r"""
const R = plain(S);
R.profile = { name: "Maria G.", position: "GVR", district: "District 22", email: "" };
R.report = { prepared_for: "District 22 Treasurer and the next GVR", note: "This is a record, not a request for payment." };
let n = 0;
const trip = (date, end, activity, event, oneWay, trips, role, more) => N(Object.assign({ id: "m" + (++n), type: "mileage", date, end_date: end, activity, event,
  from: "Home", to: event, round_trip: true, trips, miles: G.tripMiles(oneWay, true, "", "", trips), rate: "0.30", role, funder: "me" }, more || {}), R);
const room = (date, end, event, vendor, ref, cents, method) => N({ id: "h" + (++n), type: "expense", date, end_date: end, category: "lodging", activity: "assembly",
  description: "Lodging, " + event, event, vendor, ref, amount_cents: cents, method, funder: "me" }, R);
const E = [
  room("2026-03-20", "2026-03-22", "Spring Assembly", "Room shared with a member", "Check #101", 15000, "check"),
  room("2026-06-26", "2026-06-28", "Summer Assembly", "A hotel in Tyler", "Conf. 12345AB678901", 15250, "card"),
  room("2026-09-18", "2026-09-20", "Fall Assembly", "A hotel in Fort Worth", "Priceline trip 123-456-789-00 · Hotel conf. 1234567890", 16696, "card"),
  trip("2026-03-20", "2026-03-22", "assembly", "Spring Assembly", 31.5, 1, ""),
  trip("2026-04-12", "", "assembly", "Spring ACM", 19.8, 1, ""),
  trip("2026-06-26", "2026-06-28", "assembly", "Summer Assembly", 98.5, 1, ""),
  trip("2026-07-12", "", "assembly", "Summer ACM", 38.4, 1, ""),
  trip("2026-09-18", "2026-09-20", "assembly", "Fall Assembly", 54.6, 1, ""),
  trip("2026-05-10", "", "district", "District 22 meeting", 30.2, 1, ""),
  trip("2026-06-14", "", "district", "District 22 meeting", 33.6, 1, ""),
  trip("2026-07-12", "", "district", "District 22 meeting", 26.1, 1, ""),
  trip("2026-09-13", "", "district", "District 22 meeting", 20.7, 1, ""),
  trip("2026-07-24", "2026-07-26", "table", "Texas State Convention, GV/LV table", 58.7, 3, "Table support"),
  trip("2026-03-14", "2026-09-12", "table", "Dallas CityWide, GV/LV table", 21.4, 7, "Table support", { notes: "Mar 14 · Apr 11 · May 9 · Jun 13 · Jul 11 · Aug 8 · Sep 12" }),
  trip("2026-05-21", "2026-05-24", "table", "40th Gathering of Eagles, GV/LV table", 27.3, 3, "Table support"),
  trip("2026-03-28", "", "workshop", "LV Writing Workshop", 23.8, 1, "Tech setup"),
  trip("2026-04-18", "", "workshop", "GV Writing Workshop", 17.6, 1, "Zoom setup"),
  trip("2026-04-25", "", "workshop", "Abilene AA 80th Anniversary", 212.5, 1, "Projector & screen"),
  trip("2026-05-02", "", "workshop", "GV Writing Workshop", 49.7, 1, "Zoom setup"),
  trip("2026-05-09", "", "workshop", "LV Writing Workshop", 16.4, 1, "Attended"),
  trip("2026-06-06", "", "workshop", "GV Writing Workshop", 19.8, 1, "Zoom setup"),
  trip("2026-06-13", "", "workshop", "GV Writing Workshop", 77.3, 1, "Attended"),
  trip("2026-07-18", "", "workshop", "Grape-a-Thon / La Viña-a-Thon", 23.8, 1, "Attended"),
  trip("2026-08-09", "", "workshop", "GV Writing Workshop", 22.9, 1, "Tech support", { notes: "Missed the district meeting to support this workshop." }),
  N({ id: "ride", type: "mileage", date: "2026-09-04", end_date: "2026-09-06", activity: "workshop", event: "Big Country 41st AA Conference", role: "GV/LV table support",
      no_miles: true, person: "Area Archives", funder: "me" }, R),
  trip("2026-09-26", "", "workshop", "LV Writing Workshop", 55.1, 1, "Attended"),
];
const YEAR = { from: "2026-01-01", to: "2026-12-31", lang: "en", today: "2026-09-30" };
"""


class TheServiceReport(unittest.TestCase):
    def test_a_gvrs_2026_report_number_for_number(self):
        r = core(self, OWNERS_REPORT + r"""
          const rep = G.serviceReport(E, R, YEAR);
          out({ rows: rep.rows.map((x) => [x.kind, x.id, x.label, x.miles === undefined ? null : x.miles, x.cents, x.trips === undefined ? null : x.trips]),
                header: rep.header, totals: rep.totals,
                lodging: rep.money[0].lines.map((l) => [l.date, l.end_date, l.description, l.vendor, l.method, l.ref, l.amount_cents]),
                tables: rep.miles[2].lines.map((l) => [l.date, l.event, l.role, l.trips, l.one_way, l.miles, l.amount_cents]),
                ride: rep.miles[3].lines.filter((l) => l.no_miles).map((l) => [l.event, l.description, l.miles, l.trips, l.one_way, l.ride, l.amount_cents, l.role]),
                notes: rep.miles[3].lines.map((l) => l.notes).filter(Boolean), summary: G.summary(E, R, YEAR).spent_cents });""")
        self.assertEqual(r["rows"], [
            ["money", "lodging", "Hotel & lodging", None, 46946, None],
            ["miles", "assembly", "Assemblies & Area committee meetings", 485.6, 14568, 5],
            ["miles", "district", "District meetings", 221.2, 6636, 4],
            ["miles", "table", "Information tables & conventions", 815.6, 24468, 13],      # 3 + 7 + 3 round trips
            ["miles", "workshop", "Workshops & events", 1037.8, 31134, 11],                 # Big Country: on record, no miles
            ["miles_total", "", "Mileage total", 2560.2, 76806, 33],
            ["total", "", "Total cost of service", None, 123752, None],
        ])
        self.assertEqual(r["summary"], 123752)                                   # the Summary's "Spent" is the same total
        h = r["header"]
        self.assertEqual((h["first"], h["last"], h["rates"], h["name"], h["prepared_for"], h["note"]),
                         ("2026-03-14", "2026-09-26", ["0.30"], "Maria G.", "District 22 Treasurer and the next GVR", "This is a record, not a request for payment."))
        self.assertEqual({k: r["totals"][k] for k in ("spent_cents", "money_cents", "mileage_cents", "miles", "trips", "self_cents", "owed_cents")},
                         {"spent_cents": 123752, "money_cents": 46946, "mileage_cents": 76806, "miles": 2560.2, "trips": 33, "self_cents": 123752, "owed_cents": 0})
        self.assertEqual(r["lodging"], [
            ["2026-03-20", "2026-03-22", "Lodging, Spring Assembly", "Room shared with a member", "check", "Check #101", 15000],
            ["2026-06-26", "2026-06-28", "Lodging, Summer Assembly", "A hotel in Tyler", "card", "Conf. 12345AB678901", 15250],
            ["2026-09-18", "2026-09-20", "Lodging, Fall Assembly", "A hotel in Fort Worth", "card", "Priceline trip 123-456-789-00 · Hotel conf. 1234567890", 16696],
        ])
        # 7 CityWide Saturdays: 21.4 mi one way × 2 × 7 = 299.6 mi × $0.30 = $89.88
        self.assertEqual(r["tables"], [
            ["2026-03-14", "Dallas CityWide, GV/LV table", "Table support", 7, 21.4, 299.6, 8988],
            ["2026-05-21", "40th Gathering of Eagles, GV/LV table", "Table support", 3, 27.3, 163.8, 4914],
            ["2026-07-24", "Texas State Convention, GV/LV table", "Table support", 3, 58.7, 352.2, 10566],
        ])
        # names stay out unless asked: whom you rode with is a name
        self.assertEqual(r["ride"], [["Big Country 41st AA Conference", "", 0, "", "", "Rode with someone: no miles", 0, "GV/LV table support"]])
        self.assertEqual(r["notes"], [])

    def test_names_notes_and_the_csv(self):
        r = core(self, OWNERS_REPORT + r"""
          E.push(N({ id: "gift", type: "expense", date: "2026-09-01", category: "subscriptions", description: "=Gift for Rosa T.", person: "Rosa T.",
                     sub_kind: "gift", sub_product: "gv_print", sub_term: 12, amount_cents: 3600, funder: "me", notes: "Her birthday" }, R));
          const strings = { "rep.rode_with": "Rode with {name}", "field.date": "Fecha", "sub_kind.gift": "A gift", "sub_product.gv_print": "Grapevine — print" };
          const hidden = G.serviceReport(E, R, { ...YEAR, strings }), shown = G.serviceReport(E, R, { ...YEAR, strings, includeNames: true, includeNotes: true });
          const subs = hidden.money.find((g) => g.id === "subscriptions");
          out({ hidden: [subs.lines[0].description, subs.items], shown: shown.money.find((g) => g.id === "subscriptions").lines[0].description,
                ride: shown.miles[3].lines.filter((l) => l.no_miles).map((l) => [l.ride, l.description]),
                notes: shown.miles.map((g) => g.lines.map((l) => l.notes).filter(Boolean)).flat(),
                csvHidden: G.reportCSV(hidden, strings, "en"), csvShown: G.reportCSV(shown, strings, "en"), junk: [G.reportCSV(null), G.serviceReport(null, null, null).rows] });""")
        self.assertEqual(r["hidden"], ["Magazine subscriptions · A gift · Grapevine — print · 12 months", 1])
        self.assertEqual(r["shown"], "=Gift for Rosa T.")
        self.assertEqual(r["ride"], [["Rode with Area Archives", "Big Country 41st AA Conference"]])
        self.assertEqual(r["notes"], ["Mar 14 · Apr 11 · May 9 · Jun 13 · Jul 11 · Aug 8 · Sep 12", "Missed the district meeting to support this workshop."])

        def row(*cells):                                                      # a CSV row as the core writes one
            return ",".join('"' + c.replace('"', '""') + '"' if any(x in c for x in ',;"\r\n\t') else c for c in cells)
        rows = r["csvHidden"].lstrip("﻿").split("\r\n")
        self.assertTrue(r["csvHidden"].startswith("﻿") and r["csvHidden"].endswith("\r\n"))
        self.assertEqual(rows[0], "Section,Fecha,End date,Description,Event,Role,From,To,Trips,One way (mi),Miles,Rate,Store or vendor,Place,Paid with,Reference,Amount")
        # the money first, in the categories' order (subscriptions before lodging), then the miles by activity
        self.assertEqual(rows[1], row("Magazine subscriptions", "2026-09-01", "", "Magazine subscriptions · A gift · Grapevine — print · 12 months", "",
                                      "", "", "", "", "", "", "", "", "", "cash", "", "36.00"))
        self.assertEqual(rows[2], row("Hotel & lodging", "2026-03-20", "2026-03-22", "Lodging, Spring Assembly", "Spring Assembly",
                                      "", "", "", "", "", "", "", "Room shared with a member", "", "check", "Check #101", "150.00"))
        self.assertIn(row("Information tables & conventions", "2026-03-14", "2026-09-12", "Home → Dallas CityWide, GV/LV table", "Dallas CityWide, GV/LV table",
                          "Table support", "Home", "Dallas CityWide, GV/LV table", "7", "21.4", "299.6", "0.30", "", "", "", "", "89.88"), rows)
        self.assertIn(row("Workshops & events", "2026-09-04", "2026-09-06", "Rode with someone: no miles", "Big Country 41st AA Conference",
                          "GV/LV table support", "", "", "", "", "0", "", "", "", "", "", "0.00"), rows)
        self.assertEqual(len(rows), 1 + 4 + 23 + 1)                           # the header, 4 money lines, 23 trips, the last line end
        self.assertNotIn("Rosa", r["csvHidden"])
        self.assertNotIn("Area Archives", r["csvHidden"])
        self.assertIn(",'=Gift for Rosa T.,", r["csvShown"])                     # the formula guard
        self.assertIn("Her birthday", r["csvShown"])
        self.assertTrue(r["csvShown"].split("\r\n")[0].endswith(",Amount,Notes"))
        self.assertEqual(r["junk"], ["", [{"kind": "total", "id": "", "label": "Total cost of service", "cents": 0}]])


class OlderFiles(unittest.TestCase):
    """Files written by the tracker before 1.1.0 — frozen in tests/fixtures/expenses/ from the code of the
    time (45 entries: every kind, every awkward value, the examples): they read exactly as they did, every
    field as before and the new ones at their defaults; and an old file merged into a ledger that uses the
    new fields changes none of them."""

    def setUp(self):
        self.expected = json.loads((FIXTURES / "v1-expected.json").read_text(encoding="utf-8"))
        # the files as a visitor's device holds them (BOM, CRLF: .gitattributes keeps the bytes)
        self.csv = {lang: (FIXTURES / f"v1-export-{lang}.csv").read_bytes().decode("utf-8") for lang in ("en", "es")}
        self.backup = (FIXTURES / "v1-backup.json").read_bytes().decode("utf-8")

    def same(self, got: list, want: list):
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertEqual({k: v for k, v in g.items() if k not in NEW_FIELDS}, w, w["id"])
            self.assertEqual({k: g[k] for k in NEW_FIELDS}, NEW_FIELDS, w["id"])

    def test_the_files_are_as_saved(self):
        self.assertTrue(self.csv["en"].startswith("﻿" + CsvWrite.HEADER_V1 + ","))
        self.assertIn("\r\n", self.csv["en"])
        self.assertEqual(self.expected["columns"], CsvWrite.HEADER_V1.split(","))

    def test_an_older_csv_imports_identically(self):
        r = core(self, WITH_CUSTOM + r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const plan = G.planImport(input.csv[lang], [], S2, {});
            res[lang] = { errors: plan.errors, warnings: plan.warnings.length, skip: plan.skip.length,
                          news: [plan.newCategories.length, plan.newFunders.length, plan.newActivities.length, plan.newCustomFields.length], got: plan.add };
          }
          out(res);""", {"csv": self.csv})
        for lang, x in r.items():
            with self.subTest(lang=lang):
                self.assertEqual((x["errors"], x["skip"], x["news"]), ([], 0, [0, 0, 0, 0]))
                self.same(x["got"], self.expected["csv_entries"])

    def test_an_older_backup_restores_identically(self):
        r = core(self, r"""
          const back = G.readBackup(input.backup, CONFIG);
          out({ ok: back.ok, entries: back.state.entries, receipts: back.receipts, activities: back.state.settings.activities.map((a) => a.id),
                custom: back.state.settings.custom_fields.length, v: back.state.v });""", {"backup": self.backup})
        self.assertTrue(r["ok"])
        self.same(r["entries"], self.expected["backup_entries"])
        self.assertEqual(r["receipts"], self.expected["backup_receipts"])
        self.assertEqual(r["activities"], ["assembly", "district", "table", "workshop", "committee", "group", "other"])   # the list arrives
        self.assertEqual((r["custom"], r["v"]), (5, 1))

    def test_an_older_file_merged_in_changes_none_of_the_new_fields(self):
        # the ledger restored from the old backup, then given activities, roles and a reference in 1.1.0
        # (edited later); the old CSV imported into it again: nothing to update, nothing lost
        r = core(self, WITH_CUSTOM + r"""
          const st = G.readBackup(input.backup, CONFIG).state;
          const ids = [];
          st.entries = st.entries.map((e, i) => {
            if (i % 3) return e;
            ids.push(e.id);
            return N({ ...e, activity: "workshop", role: "Tech setup", ref: "Conf. " + i, updated: "2027-01-01T00:00:00.000Z" }, st.settings);
          });
          const plan = G.planImport(input.csv, st.entries, st.settings, {});
          const after = G.applyImport(st, plan, { mode: "merge" });
          out({ update: plan.update.length, add: plan.add.length, kept: after.entries.filter((e) => ids.includes(e.id)).every((e) => e.activity === "workshop" && e.role === "Tech setup" && e.ref.startsWith("Conf. ")),
                same: JSON.stringify(after.entries) === JSON.stringify(st.entries), reasons: [...new Set(plan.skip.map((s) => s.reason))].sort() });""",
                 {"backup": self.backup, "csv": self.csv["en"]})
        self.assertEqual((r["update"], r["add"]), (0, 0))
        self.assertTrue(r["kept"])
        self.assertTrue(r["same"])
        self.assertEqual(r["reasons"], ["same"])                                 # what the file says, the ledger says too


class OwedAtTheEnd(unittest.TestCase):
    """P1-4: what is owed is a balance — everything up to the period's end counts, not the period alone."""

    def test_a_december_claim_paid_back_in_january(self):
        r = core(self, r"""
          const E = [N({ id: "h", type: "expense", date: "2026-12-10", category: "lodging", description: "Hotel", amount_cents: 30000, funder: "district",
                         claim_status: "submitted", claim_date: "2026-12-12" }),
                     N({ id: "r", type: "received", date: "2027-01-15", category: "reimbursement", description: "District check", amount_cents: 30000, funder: "district" })];
          const y27 = { from: "2027-01-01", to: "2027-12-31" }, y26 = { from: "2026-01-01", to: "2026-12-31" };
          const bal = (range) => G.funderBalances(E, S, range).map((b) => [b.funder, b.claimed_cents, b.received_cents, b.balance_cents]);
          out({ owed27: G.summary(E, S, y27).owed_cents, owed26: G.summary(E, S, y26).owed_cents, all: G.summary(E, S, {}).owed_cents,
                upTo27: bal({ to: y27.to }), within27: bal(y27), received27: G.summary(E, S, y27).received_cents });""")
        self.assertEqual(r["owed27"], 0)                       # January's view: the check settled December's hotel
        self.assertEqual(r["owed26"], 30000)                   # at the end of 2026 the district still owed it
        self.assertEqual(r["all"], 0)
        self.assertEqual(r["upTo27"], [["district", 30000, 30000, 0]])
        self.assertEqual(r["within27"], [["district", 0, 30000, 30000]])   # the period alone: "you hold $300" — what the views no longer say
        self.assertEqual(r["received27"], 30000)               # (the period's own totals stay the period's)

    def test_a_claim_marked_paid_after_the_periods_end_was_still_owed_then(self):
        """Round 7 polish: a December claim marked paid (paid_date January 10) — with or without the check
        recorded — is still owed at the end of December; settled in January's view; a blank paid_date can't say
        when, so it stays settled (as before). A person's repaid purchase follows its paid_date too."""
        r = core(self, r"""
          const hotel = (extra) => N(Object.assign({ id: "h", type: "expense", date: "2025-12-12", category: "lodging", description: "Hotel December",
                                                     amount_cents: 30000, funder: "area", claim_status: "paid", claim_date: "2025-12-15", paid_date: "2026-01-10" }, extra || {}));
          const check = N({ id: "c", type: "received", date: "2026-01-10", category: "reimbursement", description: "Area check", amount_cents: 30000, funder: "area" });
          const y25 = { from: "2025-01-01", to: "2025-12-31" }, y26 = { from: "2026-01-01", to: "2026-12-31" };
          const row = (E, range) => G.funderBalances(E, S, range).map((b) => [b.funder, b.to_request_cents, b.submitted_cents, b.paid_cents, b.settled_cents, b.balance_cents]);
          const owed = (E, range) => G.summary(E, S, range).owed_cents;
          const paidOnly = [hotel()], withCheck = [hotel(), check], noDate = [hotel({ paid_date: "" })];
          // asked for after the period's end too: not yet asked for at its end
          const lateAsk = [hotel({ date: "2025-12-12", claim_date: "2026-01-05" })];
          // a subscription bought for José, repaid on January 10
          const SJ = JSON.parse(JSON.stringify(S));
          SJ.funders.push({ id: "p_jose", kind: "person", name: "José R.", hidden: false, order: 9, builtin: false });
          const sub = N({ id: "s", type: "expense", date: "2025-12-01", category: "subscriptions", description: "La Viña", amount_cents: 1500, funder: "p_jose",
                          sub_kind: "helped", repaid: "repaid", claim_status: "paid", paid_date: "2026-01-10" }, SJ);
          const people = (range) => G.peopleOwed([sub], SJ, { to: range.to }).map((p) => [p.funder, p.owed_cents, p.entries.map((e) => e.id)]);
          out({ paid25: [row(paidOnly, { to: y25.to }), owed(paidOnly, y25)], paid26: [row(paidOnly, { to: y26.to }), owed(paidOnly, y26)],
                check25: owed(withCheck, y25), check26: owed(withCheck, y26), all: owed(withCheck, {}),
                noDate25: owed(noDate, y25), lateAsk25: row(lateAsk, { to: y25.to }),
                people25: people(y25), people26: people(y26), status: hotel().claim_status });""")
        self.assertEqual(r["paid25"], [[["area", 0, 30000, 0, 0, -30000]], 30000])   # at the end of 2025 the Area still owed it: submitted
        self.assertEqual(r["paid26"], [[["area", 0, 0, 30000, 30000, 0]], 0])        # even, once paid
        self.assertEqual((r["check25"], r["check26"], r["all"]), (30000, 0, 0))     # the January check doesn't settle December
        self.assertEqual(r["noDate25"], 0)                                          # no paid date: settled, as before
        self.assertEqual(r["lateAsk25"], [["area", 30000, 0, 0, 0, -30000]])        # asked for in January: "to request" at December's end
        self.assertEqual(r["people25"], [["p_jose", 1500, ["s"]]])                  # José still owed it at the end of 2025
        self.assertEqual(r["people26"], [])
        self.assertEqual(r["status"], "paid", "the entry itself is never changed")


class ServicePanels(unittest.TestCase):
    """P1-11 / F-17: Area 65's panels by the rule — two-year terms from January 1 of an odd year, Panel N starting
    in 1950 + N — with config/expenses.yml's panels as overrides."""

    def test_the_rule_on_fixed_days(self):
        r = core(self, r"""
          const ids = (list) => list.map((p) => [p.id, p.from, p.to]);
          const e = (date) => N({ type: "expense", date, category: "books", description: "x", amount_cents: 1 });
          out({ oct26: ids(G.servicePanels([], "2026-10-06", [])), oct26cfg: ids(G.servicePanels(CONFIG.panels, "2026-10-06", [])),
                jan27: ids(G.servicePanels([], "2027-01-15", [e("2026-11-02"), e("2027-01-03")])),
                jan29: ids(G.servicePanels(CONFIG.panels, "2029-01-10", [e("2026-03-01"), e("2026-03-01")])),
                override: ids(G.servicePanels([{ id: "75", from: "2025-01-01", to: "2026-11-30" }, { id: "x", from: "bad", to: "2026-01-01" }], "2026-10-06", [])),
                byId: [G.panelById("75"), G.panelById("77"), G.panelById("76"), G.panelById("abc"), G.panelById("")] });""")
        self.assertEqual(r["oct26"], [["75", "2025-01-01", "2026-12-31"]])                     # October 2026: the current term
        self.assertEqual(r["oct26cfg"], [["77", "2027-01-01", "2028-12-31"], ["75", "2025-01-01", "2026-12-31"]])
        self.assertEqual(r["jan27"], [["77", "2027-01-01", "2028-12-31"], ["75", "2025-01-01", "2026-12-31"]])   # newest first
        self.assertEqual(r["jan29"], [["79", "2029-01-01", "2030-12-31"], ["77", "2027-01-01", "2028-12-31"], ["75", "2025-01-01", "2026-12-31"]])
        self.assertEqual(r["override"], [["75", "2025-01-01", "2026-11-30"]])                  # a listed panel's dates win; a bad one is left out
        self.assertEqual(r["byId"], [{"id": "75", "from": "2025-01-01", "to": "2026-12-31"}, {"id": "77", "from": "2027-01-01", "to": "2028-12-31"},
                                     None, None, None])


class Utf16(unittest.TestCase):
    """P8-4 / F-8: a UTF-16 CSV (Excel's "Unicode text", some banks' exports) reads as its UTF-8 twin."""

    def test_utf16_with_and_without_a_mark(self):
        r = core(self, r"""
          const text = "Fecha\tDescripción\tMonto\r\n27/09/2026\tCafé y pan dulce\t12,50\r\n28/09/2026\tAño nuevo — Niño\t3\r\n";
          const le = Buffer.from(text, "utf16le"), be = Buffer.from(le).swap16();
          const mark = (b, m) => new Uint8Array([...m, ...b]);
          const read = (bytes) => G.decodeText(bytes);
          const variants = { le_bom: mark(le, [0xff, 0xfe]), be_bom: mark(be, [0xfe, 0xff]), le: new Uint8Array(le), be: new Uint8Array(be),
                             utf8: new Uint8Array(Buffer.from("﻿" + text, "utf8")), cp1252: new Uint8Array(Buffer.from(text.replace("—", "-"), "latin1")) };
          const res = {};
          for (const [k, b] of Object.entries(variants)) res[k] = G.parseCSV(read(b)).map((row) => row.join("|"));
          const plan = G.planImport(variants.le_bom.buffer.slice(0), [], S, { mapping: { date: 0, description: 1, amount: 2 }, dateOrder: "dmy" });
          out({ res, plan: plan.add.map((e) => [e.date, e.description, e.amount_cents]), errors: plan.errors });""")
        want = ["Fecha|Descripción|Monto", "27/09/2026|Café y pan dulce|12,50", "28/09/2026|Año nuevo — Niño|3"]
        for k in ("le_bom", "be_bom", "le", "be", "utf8"):
            self.assertEqual(r["res"][k], want, k)
        self.assertEqual(r["res"]["cp1252"], [w.replace("—", "-") for w in want])               # Windows-1252 as before
        self.assertEqual(r["plan"], [["2026-09-27", "Café y pan dulce", 1250], ["2026-09-28", "Año nuevo — Niño", 300]])
        self.assertEqual(r["errors"], [])


class ZipBackupFormat(unittest.TestCase):
    """F-8: the backup.json inside the full backup's .zip names each photo's file; the photos inside an older .json
    (data: URLs) keep reading."""

    def test_receipts_by_file_and_their_names(self):
        r = core(self, r"""
          const e = N({ id: "x1abc", type: "expense", date: "2026-09-27", category: "lodging", description: "Hotel for the Fall Assembly — año", amount_cents: 100, receipt: "photo" });
          const st = { v: 1, entries: [e], settings: S, meta: {} };
          const json = G.toBackup(st, [{ id: "x1abc", type: "image/jpeg", file: G.receiptFile(e, "image/jpeg"), name: "IMG_1.jpg", w: 10, h: 20 },
                                       { id: "bad1", type: "image/jpeg", file: "../secret.jpg" }, { id: "bad2", file: "a.exe" }, { id: "bad3", type: "text/html", file: "x.png" },
                                       { id: "old", type: "image/png", dataUrl: "data:image/png;base64,AA" }]);
          const back = G.readBackup(json, CONFIG);
          out({ receipts: back.receipts, names: [G.receiptFile(e, "image/png"), G.receiptFile({ id: "x2", date: "", description: "" }, "image/webp"),
                                                 G.receiptFile({ id: "x3", date: "2026-01-02", description: "", vendor: "Kinko's" }, "")],
                format: JSON.parse(json).app });""")
        self.assertEqual(r["receipts"], [
            {"id": "x1abc", "type": "image/jpeg", "file": "2026-09-27-hotel-for-the-fall-assembly-ano-x1abc.jpg", "name": "IMG_1.jpg", "w": 10, "h": 20},
            {"id": "bad3", "type": "image/jpeg", "file": "x.png"},                # (the type follows: only images)
            {"id": "old", "type": "image/png", "dataUrl": "data:image/png;base64,AA"}])
        self.assertEqual(r["names"], ["2026-09-27-hotel-for-the-fall-assembly-ano-x1abc.png", "x2.webp", "2026-01-02-kinko-s-x3.jpg"])
        self.assertEqual(r["format"], "1.2.0")


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
                funders: ex.map((e) => e.funder).filter((f) => f && !S.funders.some((x) => x.id === f)),
                activities: ex.map((e) => e.activity).filter((a) => a && !S.activities.some((x) => x.id === a)) });""",
                   needs_modules=False, env={"I18N_STRICT": ""})
        self.assertEqual(r["cats"], ["books", "giveaways", "giveaways", "subscriptions", "subscriptions", "lodging", "meals", "printing", "travel",
                                     "registration", "contributions", "mileage", "mileage", "reimbursement", "advance", "stock_in", "given", "given", "given",
                                     "mileage", "mileage"])
        self.assertEqual(r["invalid"], [])
        self.assertEqual(r["funders"], [])
        self.assertEqual(r["activities"], [])                                  # every activity the examples use is a built-in
        self.assertTrue(r["roundTrip"])


if __name__ == "__main__":
    unittest.main()
