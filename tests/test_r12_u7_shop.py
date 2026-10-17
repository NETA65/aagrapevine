"""/shop/ "What it would cost" (#group-cost): the group-subscription calculator and its information sheet.

  * The numbers — eleventy/filters/shop.js shopCost: the U.S. store's plans of both magazines (no Canadian or
    international listing), each with its price per copy and the store's own volume tiers as the page shows them at
    build time, the same from the day of an announced change still ahead (`after`: the browser switches at that
    instant), the "From January 1, 2027" price while AA Grapevine's notice is up (`next`) and that window for a plan
    the notice names no price for (`none`); the labels in both languages.
  * The sums — src/assets/js/shop.js GV.shopQuote (in Node's vm, as the browser runs it): the volume tier for the
    number of copies (1 · 2–19 · 20–39 · 40+), the total, a month and a year, the price-change rule at 11:59 PM and
    midnight Central on December 31 / January 1, and the words (English and Spanish) the result and the sheet show.
  * The component — shopCost: the choice it starts with, a term the magazine does not sell, the number field, and
    "Print an information sheet" (html[data-shop-print] while it prints, gone afterwards).
  * The page — the card, its no-JavaScript links, the as-of line and the print rules.

Every check runs at a fixed moment (run_js now=…, or the instant handed to GV.shopQuote): none depends on the day
the tests run.

    python -m unittest tests.test_r12_u7_shop -v
"""
from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from nodejs import run_js  # noqa: E402

A_AT = "2026-10-01T05:00:00Z"          # 00:00 Central on October 1, 2026: AA Grapevine's notice
E_AT = "2027-01-01T06:00:00Z"          # 00:00 Central (CST) on January 1, 2027: the new prices
N_AT = "2027-02-01T06:00:00Z"          # the "New prices since …" notice is over
OCT15 = "2026-10-15T15:00:00Z"
DEC31_2359 = "2027-01-01T05:59:00Z"    # 11:59 PM Central on December 31
JAN1_0800 = "2027-01-01T14:00:00Z"

CHANGE = {"key": "2027-01", "announced": "2026-10-01", "effective": "2027-01-01", "notice_until": "2027-01-31",
          "at": {"announced": A_AT, "effective": E_AT, "notice_end": N_AT}, "books_more": 2.0,
          "yearly": [{"pub": "gv", "type": "print", "new": 39.0, "now": 36.0, "after": 39.0},
                     {"pub": "gv", "type": "digital", "new": 34.0, "now": 29.99, "after": 34.0},
                     {"pub": "lv", "type": "print", "new": 19.5, "now": 18.0, "after": 19.5},
                     {"pub": "lv", "type": "digital", "new": 17.0, "now": 14.99, "after": 17.0}]}
GV_VOL = [{"min": 2, "max": 19, "price": 35.5}, {"min": 20, "max": 39, "price": 35.0}, {"min": 40, "max": None, "price": 34.0}]
GV_VOL2 = [{"min": 2, "max": 19, "price": 67.5}, {"min": 20, "max": 39, "price": 67.0}, {"min": 40, "max": None, "price": 66.0}]
LV_VOL = [{"min": 2, "max": 19, "price": 17.5}, {"min": 20, "max": 39, "price": 17.0}, {"min": 40, "max": None, "price": 16.0}]


def plan(pub: str, typ: str, months: int, price: float, vol=None, new: float | None = None, stale: bool = True) -> dict:
    p = {"type": typ, "term_months": months, "title": f"{pub} {typ} {months}", "price": price, "currency": "USD",
         "sku": f"{pub}{typ}{months}".upper(), "url": f"https://www.example.org/{pub}-{typ}-{months}", "volume": vol or []}
    if new is not None:
        p["change"] = {"key": "2027-01", "new": new, "stale": stale}
    return p


def shop(store_updated: bool = False, change: bool = True) -> dict:
    """data/site/shop.json (its subscriptions and price_changes) as build_data writes it — the store's prices of
    October 2026; store_updated: the store's own page shows the new 1-year print price and new volume prices."""
    gv_print1 = (plan("gv", "print", 12, 39.0, [{"min": 2, "max": 19, "price": 38.5}, {"min": 20, "max": None, "price": 38.0}], 39.0, False)
                 if store_updated else plan("gv", "print", 12, 36.0, GV_VOL, 39.0))
    doc = {
        "updated": "2026-10-15T12:50:38Z",
        "subscriptions": [
            {"pub": "gv", "region": "us", "url": "https://www.example.org/gv-us", "plans": [
                gv_print1, plan("gv", "print", 24, 68.0, GV_VOL2), plan("gv", "digital", 1, 2.99),
                plan("gv", "digital", 12, 29.99, None, 34.0), plan("gv", "complete", 12, 56.0)]},
            {"pub": "gv", "region": "ca", "url": "https://www.example.org/gv-ca", "plans": [plan("gv", "print", 12, 36.0, GV_VOL, 39.0)]},
            {"pub": "gv", "region": "intl", "url": "https://www.example.org/gv-intl", "plans": [plan("gv", "digital", 12, 29.99, None, 34.0)]},
            {"pub": "lv", "region": "us", "url": "https://www.example.org/lv-us", "plans": [
                plan("lv", "print", 12, 18.0, LV_VOL, 19.5), plan("lv", "print", 24, 34.0),
                plan("lv", "digital", 12, 14.99, None, 17.0)]},
        ],
        "price_changes": [copy.deepcopy(CHANGE)] if change else [],
    }
    if not change:
        for s in doc["subscriptions"]:
            for p in s["plans"]:
                p.pop("change", None)
    return doc


def cost(case: unittest.TestCase, doc: dict, now: str, lang: str = "en") -> dict:
    return run_js(case, "out(filters.shopCost(input.shop, input.lang));", data={"shop": doc, "lang": lang}, now=now)


def by(c: dict, pub: str, typ: str, months: int) -> dict:
    return next(p for p in c["plans"] if (p["pub"], p["type"], p["months"]) == (pub, typ, months))


# =========================================================================== the numbers (the build)
class Numbers(unittest.TestCase):
    def test_before_the_day(self):
        c = cost(self, shop(), OCT15)
        self.assertEqual(c["pubs"], ["gv", "lv"])
        self.assertEqual(c["types"], ["print", "digital", "complete"])
        self.assertEqual([t["months"] for t in c["terms"]], [1, 12, 24])
        self.assertEqual(len(c["plans"]), 8, "the U.S. listings only (no Canadian or international plan)")
        p = by(c, "gv", "print", 12)
        self.assertEqual(p["now"], {"price": 36.0, "vol": GV_VOL, "subst": False, "date": None})
        dates = {"en": "January 1, 2027", "es": "1 de enero de 2027"}
        self.assertEqual(p["after"], {"at": E_AT, "price": 39.0, "vol": None, "subst": True, "date": dates},
                         "from the day: the announced price, and no volume prices (the store's are the old ones)")
        self.assertEqual(p["next"], {"from": "", "until": E_AT, "price": 39.0, "date": dates})
        self.assertIsNone(p["none"])
        self.assertTrue(p["hasVol"])
        two = by(c, "gv", "print", 24)
        self.assertEqual((two["after"], two["next"]), (None, None))
        self.assertEqual(two["none"], {"from": "", "until": E_AT, "date": dates}, "the notice names no price for it")
        self.assertEqual(by(c, "gv", "complete", 12)["none"]["until"], E_AT)
        dg = by(c, "gv", "digital", 12)
        self.assertEqual((dg["now"]["vol"], dg["hasVol"], dg["after"]["price"]), ([], False, 34.0))
        self.assertEqual(by(c, "lv", "print", 12)["next"]["price"], 19.5)

    def test_the_labels_in_both_languages(self):
        c = cost(self, shop(), OCT15, "es")
        self.assertEqual(c["pubs"], ["lv", "gv"], "the page language's magazine first")
        en, es = c["s"]["en"], c["s"]["es"]
        self.assertEqual((en["locale"], es["locale"]), ("en-US", "es-US"))
        self.assertEqual((en["term"]["24"], es["term"]["24"], es["term"]["1"]), ("2 years", "2 años", "1 mes"))
        self.assertEqual((en["type"]["print"], es["type"]["print"], es["type"]["complete"]), ("Print", "Impresa", "Completa"))
        self.assertEqual(en["desc"]["lv.print"], "The magazine in your mailbox — 6 issues a year.")
        self.assertEqual(es["desc"]["gv.print"], "La revista en tu buzón: 12 ediciones al año.")
        self.assertEqual(es["mag"]["lv"], "La Viña")
        self.assertEqual(es["next_one"], "Desde el {date}: {price}")
        self.assertEqual(en["unit"], "{price} a copy")

    def test_a_page_built_before_the_announcement_waits_for_it(self):
        c = cost(self, shop(), "2026-09-30T12:00:00Z")
        self.assertEqual(by(c, "gv", "print", 12)["next"]["from"], A_AT)
        self.assertEqual(by(c, "gv", "print", 24)["none"]["from"], A_AT)

    def test_built_on_the_day_with_the_store_data_of_the_day_before(self):
        c = cost(self, shop(), JAN1_0800)
        p = by(c, "gv", "print", 12)
        self.assertEqual(p["now"], {"price": 39.0, "vol": None, "subst": True, "date": {"en": "January 1, 2027", "es": "1 de enero de 2027"}})
        self.assertEqual((p["after"], p["next"], p["none"]), (None, None, None))
        self.assertIsNone(by(c, "gv", "print", 24)["none"], "the notice's window has closed")

    def test_the_store_updated_wins(self):
        c = cost(self, shop(store_updated=True), JAN1_0800)
        p = by(c, "gv", "print", 12)
        self.assertEqual(p["now"]["price"], 39.0)
        self.assertEqual(p["now"]["vol"], [{"min": 2, "max": 19, "price": 38.5}, {"min": 20, "max": None, "price": 38.0}],
                         "the store's own new volume prices")
        self.assertFalse(p["now"]["subst"])

    def test_without_a_price_change(self):
        c = cost(self, shop(change=False), OCT15)
        for p in c["plans"]:
            self.assertEqual((p["after"], p["next"], p["none"], p["now"]["subst"]), (None, None, None, False))

    def test_no_store_data(self):
        c = run_js(self, "out(filters.shopCost(null, 'en'));", now=OCT15)
        self.assertEqual((c["plans"], c["pubs"], c["types"], c["terms"]), ([], [], [], []))


# =========================================================================== the sums (the browser)
BROWSER_JS = r"""
import vm from "node:vm";
const SRC = fs.readFileSync("src/assets/js/shop.js", "utf8");
/** shop.js in a pretend page at `atIso` (its clock), with the calculator's data (#shop-cost-data). */
const page = (atIso, cfg, search = "") => {
  const now = Date.parse(atIso);
  class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(now); } static now() { return now; } }
  const docL = {}, winL = {}, attrs = {};
  const root = { setAttribute(n, v) { attrs[n] = String(v); }, removeAttribute(n) { delete attrs[n]; } };
  const ctx = { console, JSON, Math, Object, Array, String, Number, RegExp, Intl, Date: FakeDate, URLSearchParams,
    setInterval: () => 0, setTimeout: (fn) => { fn(); return 0; }, clearTimeout() {}, location: { search }, onafterprint: null,
    printed: [], print() { ctx.printed.push({ attr: attrs["data-shop-print"], title: ctx.document.title }); },
    addEventListener: (t, fn) => { (winL[t] ||= []).push(fn); },
    removeEventListener: (t, fn) => { winL[t] = (winL[t] || []).filter((f) => f !== fn); },
    document: { readyState: "complete", hidden: false, title: "Shop", documentElement: root, querySelectorAll: () => [],
      addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); },
      getElementById: (id) => (id === "shop-cost-data" ? { textContent: JSON.stringify(cfg) } : null) } };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx, { filename: "shop.js" });
  let factory = null;
  ctx.Alpine = { data: (name, fn) => { if (name === "shopCost") factory = fn; } };
  for (const fn of docL["alpine:init"] || []) fn();
  const make = (lang) => {
    const a = factory(lang);
    a.$watch = () => {};
    a.$nextTick = (fn) => fn();
    a.init();
    return a;
  };
  return { GV: ctx.GV, make, attrs, ctx, winL };
};
const cfgEn = filters.shopCost(input.shop, "en");
const find = (pub, type, months) => cfgEn.plans.find((p) => p.pub === pub && p.type === type && p.months === months);
const { GV } = page(input.dec31, cfgEn);
const q = (plan, n, at) => GV.shopQuote(plan, n, Date.parse(at));
const pick = (r) => ({ copies: r.copies, unit: r.unit, note: r.note, total: r.total, perMonth: r.perMonth, perYear: r.perYear,
                       tier: r.tier && [r.tier.min, r.tier.max], since: r.since && r.since.en, next: r.next && [r.next.price, r.next.total, r.next.vol],
                       none: r.none && r.none.en });
const gv1 = find("gv", "print", 12), gv2 = find("gv", "print", 24), dg1 = find("gv", "digital", 12), dg1m = find("gv", "digital", 1);
const res = {};
res.tiers = [1, 2, 19, 20, 39, 40, 999, 1000, 0, "", "abc", "10.7", -3].map((n) => pick(q(gv1, n, input.oct15)));
res.two = pick(q(gv2, 10, input.oct15));
res.monthly = pick(q(dg1m, 10, input.oct15));
res.dec31 = [pick(q(gv1, 10, input.dec31)), pick(q(gv1, 1, input.dec31))];
res.jan1 = [pick(q(gv1, 10, input.jan1)), pick(q(gv1, 1, input.jan1)), pick(q(dg1, 3, input.jan1)), pick(q(gv2, 10, input.jan1))];
res.digitalBefore = pick(q(dg1, 3, input.dec31));
const words = (plan, n, at, L, cfg = cfgEn) => GV.shopQuoteWords(GV.shopQuote(plan, n, Date.parse(at)), plan, cfg.s[L], L);
res.words = {
  en: words(gv1, 10, input.oct15, "en"), es: words(gv1, 10, input.oct15, "es"),
  enOne: words(gv1, 1, input.oct15, "en"), esOne: words(gv1, 1, input.oct15, "es"),
  enJan1: words(gv1, 10, input.jan1, "en"), esJan1: words(gv1, 10, input.jan1, "es"),
  enTwo: words(gv2, 40, input.oct15, "en"), esTwo: words(gv2, 40, input.oct15, "es"),
  enMonthly: words(dg1m, 3, input.oct15, "en"), esDigital: words(dg1, 3, input.oct15, "es"),
};
// the component
const cmp = {};
{
  const P = page(input.oct15, filters.shopCost(input.shop, "es"));
  const a = P.make("es");
  cmp.start = { pub: a.pub, type: a.type, months: a.months, copies: a.copies, sheet: a.sheet, hint: a.volHint() };
  a.copies = "25";
  cmp.es25 = a.w("es");
  cmp.en25 = a.w("en");
  a.pub = "lv"; a.type = "digital"; a.months = 1; a.fix();
  cmp.lvMonthly = { type: a.type, months: a.months, hasTerm1: a.hasTerm(1), hint: a.volHint() };
  a.type = "print";
  cmp.lvMonthly.hasPrint24 = a.hasTerm(24);
  a.type = "complete"; a.fix();
  cmp.lvNoComplete = { type: a.type, months: a.months };
  a.copies = "1200"; a.tidy(); cmp.tidyHigh = a.copies;
  a.copies = ""; a.tidy(); cmp.tidyEmpty = a.copies;
  a.pub = "gv"; a.type = "print"; a.months = 12; a.copies = 5; a.sheet = "both";
  a.print();
  cmp.printed = P.ctx.printed;
  cmp.during = P.attrs["data-shop-print"];
  for (const fn of P.winL.afterprint || []) fn();
  cmp.after = { attr: P.attrs["data-shop-print"] || null, title: P.ctx.document.title, listeners: (P.winL.afterprint || []).length };
}
{
  const P = page(input.oct15, cfgEn, "?pub=lv");
  cmp.query = P.make("en").pub;
  const later = page(input.jan1, cfgEn).make("en");
  later.copies = 10;
  cmp.jan1 = { total: later.w("en").total, since: later.w("en").since, unit: later.w("en").unit, hint: later.volHint() };
}
res.cmp = cmp;
out(res);
"""


class Sums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Sums.r is None:
            Sums.r = run_js(self, BROWSER_JS, data={"shop": shop(), "oct15": OCT15, "dec31": DEC31_2359, "jan1": JAN1_0800},
                            now=OCT15)
        self.r = Sums.r

    def test_the_volume_tiers(self):
        t = self.r["tiers"]
        # 1 · 2 · 19 · 20 · 39 · 40 · 999 · 1000 (999 at most) · 0, "", "abc", "10.7", -3
        self.assertEqual([(x["copies"], x["unit"], x["total"]) for x in t],
                         [(1, 36, 36), (2, 35.5, 71), (19, 35.5, 674.5), (20, 35, 700), (39, 35, 1365), (40, 34, 1360),
                          (999, 34, 33966), (999, 34, 33966), (1, 36, 36), (1, 36, 36), (1, 36, 36), (10, 35.5, 355), (1, 36, 36)])
        self.assertEqual([x["tier"] for x in t[:6]], [None, [2, 19], [2, 19], [20, 39], [20, 39], [40, None]])
        self.assertEqual([x["note"] for x in t[:3]], ["", "vol", "vol"])
        self.assertEqual((t[11]["perMonth"], t[11]["perYear"]), (29.58, 355))

    def test_a_month_and_a_year(self):
        self.assertEqual((self.r["two"]["total"], self.r["two"]["perMonth"], self.r["two"]["perYear"]), (675, 28.13, 337.5))
        m = self.r["monthly"]
        self.assertEqual((m["unit"], m["total"], m["perYear"], m["note"]), (2.99, 29.9, 358.8, "novol"),
                         "no volume price for a digital plan: each copy at the store's price")

    def test_at_1159_pm_on_december_31(self):
        ten, one = self.r["dec31"]
        self.assertEqual((ten["unit"], ten["total"], ten["since"]), (35.5, 355, None))
        self.assertEqual(ten["next"], [39, 390, True], "the announced price for 10 copies — and the volume prices are the store's to say")
        self.assertEqual(one["next"], [39, 39, False])
        self.assertEqual(self.r["digitalBefore"]["next"], [34, 102, False])

    def test_from_midnight_on_january_1(self):
        ten, one, digital, two = self.r["jan1"]
        self.assertEqual((ten["unit"], ten["total"], ten["note"], ten["tier"], ten["since"], ten["next"]),
                         (39, 390, "later", None, "January 1, 2027", None),
                         "the announced price stands in: no volume price of the old list is used")
        self.assertEqual((one["unit"], one["note"], one["since"]), (39, "", "January 1, 2027"))
        self.assertEqual((digital["unit"], digital["total"], digital["note"]), (34, 102, "novol"))
        self.assertEqual((two["unit"], two["total"], two["none"], two["since"]), (67.5, 675, None, None))
        self.assertEqual(self.r["two"]["none"], "January 1, 2027", "before the day: the notice names no price for it")

    def test_the_words_in_english(self):
        w = self.r["words"]["en"]
        self.assertEqual((w["mag"], w["plan"], w["count"], w["copies"]), ("Grapevine", "Print · 1 year", "10", "10 copies"))
        self.assertEqual(w["desc"], "The magazine in your mailbox — 12 issues a year.")
        self.assertEqual((w["total"], w["totalFor"], w["perMonth"], w["perYear"]), ("$355.00", "for 1 year", "≈ $29.58 a month", ""))
        self.assertEqual(w["unit"], "$35.50 a copy (volume price for 2–19 copies)")
        self.assertEqual(w["unitAmt"], "$35.50 (volume price for 2–19 copies)")
        self.assertEqual(w["next"], "From January 1, 2027, the regular price is $39.00 a copy: $390.00 for 10 copies. "
                                    "The store will list the new volume prices.")
        self.assertEqual((w["since"], w["none"]), ("", ""))
        self.assertEqual(w["store"], "See this plan on aagrapevine.org")
        self.assertEqual(w["order"], "How the group orders: directly from the official store, online at "
                                     "example.org/gv-print-12 or with its order form.")
        one = self.r["words"]["enOne"]
        self.assertEqual((one["copies"], one["unit"], one["unitAmt"], one["next"]), ("1 copy", "", "$36.00", "From January 1, 2027: $39.00"))
        jan1 = self.r["words"]["enJan1"]
        self.assertEqual((jan1["total"], jan1["unit"], jan1["since"], jan1["next"]),
                         ("$390.00", "$39.00 a copy (volume prices: see the store)", "New price since January 1, 2027", ""))
        two = self.r["words"]["enTwo"]
        self.assertEqual((two["total"], two["totalFor"], two["perMonth"], two["perYear"], two["unit"]),
                         ("$2,640.00", "for 2 years", "≈ $110.00 a month", "≈ $1,320.00 a year", "$66.00 a copy (volume price for 40 or more)"))
        self.assertEqual(two["none"], "AA Grapevine announced new prices from January 1, 2027, but none for this plan.")
        m = self.r["words"]["enMonthly"]
        self.assertEqual((m["total"], m["totalFor"], m["perMonth"], m["perYear"], m["unit"]),
                         ("$8.97", "each month", "", "≈ $107.64 a year", "$2.99 a copy (no volume price listed)"))

    def test_the_words_in_spanish(self):
        w = self.r["words"]["es"]
        self.assertEqual((w["plan"], w["copies"], w["totalFor"], w["perMonth"]), ("Impresa · 1 año", "10 ejemplares", "por 1 año", "≈ $29.58 al mes"))
        self.assertEqual(w["unit"], "$35.50 por ejemplar (precio por cantidad para 2 a 19 ejemplares)")
        self.assertEqual(w["next"], "Desde el 1 de enero de 2027, el precio regular es de $39.00 por ejemplar: $390.00 por 10 ejemplares. "
                                    "La tienda publicará los nuevos precios por cantidad.")
        self.assertEqual(w["store"], "Ver este plan en aagrapevine.org")
        self.assertEqual(self.r["words"]["esOne"]["next"], "Desde el 1 de enero de 2027: $39.00")
        self.assertEqual(self.r["words"]["esJan1"]["since"], "Precio nuevo desde el 1 de enero de 2027")
        self.assertEqual(self.r["words"]["esTwo"]["unit"], "$66.00 por ejemplar (precio por cantidad para 40 o más)")
        self.assertEqual(self.r["words"]["esTwo"]["none"], "AA Grapevine anunció precios nuevos desde el 1 de enero de 2027, pero ninguno para este plan.")
        self.assertEqual(self.r["words"]["esDigital"]["unit"], "$29.99 por ejemplar (sin precio por cantidad)")

    def test_the_component(self):
        c = self.r["cmp"]
        self.assertEqual(c["start"], {"pub": "lv", "type": "print", "months": 12, "copies": 1, "sheet": "es",
                                      "hint": "Precios por cantidad desde 2 ejemplares"},
                         "/es/: La Viña, print, 1 year, 1 copy, the sheet in Spanish")
        self.assertEqual((c["es25"]["total"], c["es25"]["unit"]), ("$425.00", "$17.00 por ejemplar (precio por cantidad para 20 a 39 ejemplares)"))
        self.assertEqual((c["en25"]["mag"], c["en25"]["copies"]), ("La Viña", "25 copies"), "the sheet's English part")
        self.assertEqual(c["lvMonthly"], {"type": "digital", "months": 12, "hasTerm1": False, "hasPrint24": True, "hint": ""},
                         "La Viña has no 1-month plan here: the 1-year one")
        self.assertEqual(c["lvNoComplete"], {"type": "print", "months": 12}, "no Complete plan for La Viña: the first format it has")
        self.assertEqual((c["tidyHigh"], c["tidyEmpty"]), (999, 1))
        self.assertEqual(c["printed"], [{"attr": "both", "title": "What a group subscription would cost — Grapevine"}])
        self.assertEqual(c["during"], "both")
        self.assertEqual(c["after"], {"attr": None, "title": "Shop", "listeners": 0}, "after printing the page is as it was")
        self.assertEqual(c["query"], "lv", "?pub=lv preselects, as for the price switch")
        self.assertEqual(c["jan1"], {"total": "$390.00", "since": "New price since January 1, 2027",
                                     "unit": "$39.00 a copy (volume prices: see the store)", "hint": ""})


# =========================================================================== the clock (a page left open)
# shopCost in a pretend page whose clock moves (input.start, then input.steps: minutes, each followed by the page's
# minute timers — and once by "visibilitychange"): every value `now` takes. The sum is a live region (aria-live): a
# change of `now` redraws it and a screen reader says it again, so `now` may only move when a quote changes.
CLOCK_JS = r"""
import vm from "node:vm";
const SRC = fs.readFileSync("src/assets/js/shop.js", "utf8");
let now = Date.parse(input.start);
class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(now); } static now() { return now; } }
const docL = {}, timers = [];
const cfg = filters.shopCost(input.shop, "en");
const ctx = { console, JSON, Math, Object, Array, String, Number, RegExp, Intl, Date: FakeDate, URLSearchParams,
  setInterval: (fn, ms) => { timers.push([fn, ms]); return timers.length; }, setTimeout: (fn) => { fn(); return 0; },
  clearTimeout() {}, location: { search: "" }, addEventListener() {}, removeEventListener() {},
  document: { readyState: "complete", hidden: false, title: "Shop", documentElement: { setAttribute() {}, removeAttribute() {} },
    querySelectorAll: () => [], addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); },
    getElementById: (id) => (id === "shop-cost-data" ? { textContent: JSON.stringify(cfg) } : null) } };
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(SRC, ctx, { filename: "shop.js" });
let factory = null;
ctx.Alpine = { data: (name, fn) => { if (name === "shopCost") factory = fn; } };
for (const fn of docL["alpine:init"] || []) fn();
const a = factory("en");
a.$watch = () => {};
a.$nextTick = (fn) => fn();
a.init();
a.copies = 10;
let value = a.now;
const writes = [];
Object.defineProperty(a, "now", { get: () => value, set: (v) => { writes.push(new Date(v).toISOString()); value = v; } });
const sums = [a.w("en").total];
input.steps.forEach((minutes, i) => {
  now += minutes * 60000;
  for (const [fn, ms] of timers) if (ms === 60000) fn();
  if (i === 0) for (const fn of docL.visibilitychange || []) fn();
  sums.push(a.w("en").total);
});
out({ writes, sums, since: a.w("en").since });
"""


class Clock(unittest.TestCase):
    def run_clock(self, start: str, steps: list[int]) -> dict:
        return run_js(self, CLOCK_JS, data={"shop": shop(), "start": start, "steps": steps}, now=OCT15)

    def test_an_idle_page_says_nothing_again(self):
        # six quiet minutes on October 15 (and the tab brought back): nothing a quote shows has changed
        r = self.run_clock(OCT15, [1, 1, 1, 1, 1, 1])
        self.assertEqual(r["writes"], [], "the sum is not redrawn: a screen reader does not say it again")
        self.assertEqual(set(r["sums"]), {"$355.00"})

    def test_midnight_of_the_price_change_still_moves_it(self):
        # left open at 11:57 PM on December 31: the new prices at midnight, once — then nothing again
        r = self.run_clock("2027-01-01T05:57:00Z", [1, 1, 1, 1, 1])
        self.assertEqual(len(r["writes"]), 1, r["writes"])
        self.assertGreaterEqual(r["writes"][0], E_AT.replace("Z", ".000Z"))
        self.assertEqual(r["sums"], ["$355.00", "$355.00", "$355.00", "$390.00", "$390.00", "$390.00"])
        self.assertEqual(r["since"], "New price since January 1, 2027")


# =========================================================================== the page
class Page(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / "src" / "pages" / "shop.njk").read_text(encoding="utf-8")
        self.css = (ROOT / "src" / "assets" / "css" / "areas" / "shop.css").read_text(encoding="utf-8")

    def test_the_card(self):
        for needle in ('<div id="group-cost" class="shop-cost card card-pad mt-8 sm:mt-10" role="region" aria-labelledby="cost-title" x-data="shopCost(\'{{ lang }}\')">',
                       '<script type="application/json" id="shop-cost-data">{{ cost | jsonScript | safe }}</script>',
                       '{%- set cost = shop | shopCost(lang) -%}', '<div class="shop-cost-grid" x-cloak>',
                       # without JavaScript: where the prices are, and the two stores
                       '<div class="mt-4" data-nojs-only>', '"read.subs.sub_lv" if pub == "lv" else "read.subs.sub_gv"',
                       # every action is a link to the official store
                       ':href="(plan() || {}).url" target="_blank" rel="noopener"',
                       # the as-of line, as under the prices (the day of the store read moves with every sync)
                       '<span data-lastmod="skip">{{ "shop.cost_asof" | t(lang, { date: asOf }) }}</span>',
                       '<p class="shop-sheet-asof" data-lastmod="skip">',
                       # the sum is said once it changes; the number field names its hint
                       '<p class="shop-cost-sum" aria-live="polite" aria-atomic="true">', ':aria-describedby="volHint()',
                       # the volume tables point to it
                       'href="#group-cost">{% icon "calculator", "size-4 shrink-0" %} {{ "shop.cost_link" | t(lang) }}</a>',
                       '<div id="shop-sheet" class="shop-sheet">', '@click="print()"'):
            self.assertIn(needle, self.page)
        block = self.page[self.page.index('<div id="group-cost"'):self.page.index('id="shop-cost-data"')]
        self.assertNotRegex(block, r"\$\d", "no price typed in the page: the store data's only")

    def test_the_sheet_prints_alone(self):
        self.assertIn(".shop-sheet { display: none; }", self.css)
        self.assertIn("html[data-shop-print] body :not(:has(#shop-sheet)):not(#shop-sheet, #shop-sheet *) { display: none !important; }", self.css)
        self.assertIn('html[data-shop-print="both"] .shop-sheet-parts { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);', self.css)
        self.assertIn("@page shop-letter { size: letter;", self.css)

    def test_the_strings(self):
        s = json.loads((ROOT / "src" / "_i18n" / "shop.json").read_text(encoding="utf-8"))
        for k in ("shop.cost_title", "shop.cost_print", "shop.cost_asof", "shop.sheet_decision", "shop.sheet_decides"):
            self.assertTrue(s[k]["en"] and s[k]["es"], k)
        self.assertEqual(s["shop.cost_asof"]["en"], "Prices as of {date}; the store's price is the one that counts.")
        # attraction, not promotion: the group decides, with its own money — no urgency words
        for k, v in s.items():
            if k.startswith(("shop.cost_", "shop.sheet_")):
                self.assertNotRegex(v["en"], re.compile(r"\b(hurry|now only|don't miss|last chance|act now|save big)\b", re.I), k)


if __name__ == "__main__":
    unittest.main()
