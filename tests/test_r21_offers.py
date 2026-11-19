"""Offers the official stores announce (config/site.yml `store_offers:` — November 2026: free shipping at both stores,
then the holiday gift offers):

  * Offers      — eleventy/filters/shop.js shopOffers / shopOfferIn / offerDates, on settings of the test's own: the
                  window (from 00:00 Central on `starts` to the midnight after `ends`: written hidden before it, gone
                  after it), the words in the page's language (La Viña first on /es/), the store links
                  (links.gv_store / lv_store; a store's own page for the offer — url, url_ca — instead), the banner
                  the Drive's `flyers` folder holds (banner_match) or none, a block with a mistake left out and
                  named, the month's lines, an offer whose stores give no first day (show_starts: false, "Through
                  December 31, 2026"); Home's committee uploads leave the banners out (shopOfferBanners → homeDrive);
  * DriveNames  — scripts/sync/drive.py build_item: the banners' names in `flyers` make no event (no date, no month)
                  and say their language;
  * Message     — the monthly toolkit's message (monthly.js monthMessage) names the offer in the months it runs, with
                  a link to its own section (/shop/#offers-<key>; 🎁 for a gift offer, else 📦);
  * BuiltPages  — one build of /shop/ and the monthly toolkit with settings of the test's own, at three moments
                  (MONTHLY_NOW): before the offer (#offers written hidden, waiting for its first day), during it
                  (#offers under the page nav and above the Book of the Month: both cards, links, banners, the days;
                  the November page's "Keep up all month" row and message line, to #offers-<key>) and after it
                  (nothing left);
  * RealSettings — the committee's own block (CONTENT_TESTS: the free shipping of 2026 as AA Grapevine's and La
                  Viña's e-mails and banners say it, nothing more; its banner patterns find the two banners and
                  nothing else).
  (The bulletin post about it is now a section of the pinned post of November 11, 2026, with the holiday gift
  offers and the prices of January 1, 2027 — tests/test_r25_holiday_offers.py, with the gift offers' own block.)

    python -m unittest tests.test_r21_offers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from nodejs import run_js  # noqa: E402
import test_monthly as TM  # noqa: E402  (its October 2026 data set and site settings)
from scripts.sync.drive import Found, Panel, build_item  # noqa: E402
from scripts.sync.drive_listing import Entry  # noqa: E402

FROM = "2026-11-01T05:00:00Z"          # 00:00 Central (CDT) on November 1, 2026: the offer starts
UNTIL = "2027-01-01T06:00:00Z"         # 00:00 Central (CST) on January 1, 2027: it is over
GV_BANNER = "Free shipping on all Grapevine products - banner.jpg"
LV_BANNER = "Envíos gratuitos en todos los productos de La Viña - banner.jpg"
LINKS = {"gv_store": "https://www.gv.example.org/store-test", "lv_store": "https://www.lv.example.org/tienda-test"}
# The committee's block as written (November 2026), the test's own copy — the code is tested on it, never on the file
OFFER = {
    "key": "free-shipping-2026",
    "title": "Free shipping at the Grapevine and La Viña stores",
    "title_es": "Envío gratis en las tiendas de La Viña y Grapevine",
    "starts": "2026-11-01", "ends": "2026-12-31",
    "source": "AA Grapevine's and La Viña's e-mails (November 2, 2026) and their stores' banners",
    "source_es": "Correos de La Viña y AA Grapevine (2 de noviembre de 2026) y los banners de sus tiendas",
    "gv": {"text": "Free shipping on all Grapevine products to U.S. and Canadian addresses. Grapevine says the offer can't "
                   "be combined with any other offer.",
           "text_es": "Envío gratis en todos los productos de Grapevine a direcciones en EE. UU. y Canadá. Según Grapevine, "
                      "la oferta no se puede combinar con ninguna otra.",
           "banner_match": "free shipping on all grapevine products",
           "banner_alt": "AA Grapevine's banner: Free shipping on all Grapevine products. Available November 1 – December 31.",
           "banner_alt_es": "Banner de AA Grapevine (en inglés): envío gratis en todos los productos de Grapevine, del 1 "
                            "de noviembre al 31 de diciembre."},
    "lv": {"text": "Free shipping on all La Viña products to the U.S. and Canada.",
           "text_es": "Envío gratis en todos los productos de La Viña a EE. UU. y Canadá.",
           "banner_match": "env[ií]os? gratuitos? en todos los productos de la vi[nñ]a",
           "banner_alt": "La Viña's banner (in Spanish): free shipping on all La Viña products, November 1 – December 31.",
           "banner_alt_es": "Banner de La Viña: envíos gratuitos en todos los productos de La Viña, del 1 de noviembre al "
                            "31 de diciembre."},
}
SITE = {"links": LINKS, "store_offers": [OFFER]}


def drive_item(fid: str, name: str, lang: str, en: str, es: str, category: str = "flyers", mime: str = "image/jpeg",
               date: str = "2026-11-02") -> dict:
    """A Drive file as data/site/drive.json has it (shaped like the "¡Tarjetas de ocasión …" flyer there)."""
    title = name.rsplit(".", 1)[0]
    image = mime.startswith("image/")
    return {
        "id": f"drive:{fid}", "source": "drive", "kind": "photo" if image else "pdf",
        "url": f"https://drive.google.com/file/d/{fid}/view", "title": title, "summary": "", "lang": lang, "date": date,
        "first_seen": f"{date}T23:00:00Z", "image": f"https://lh3.googleusercontent.com/d/{fid}=w600" if image else None,
        "tags": ["panel-77"], "category": category, "status": "ok",
        "extra": {"file_id": fid, "mime": mime, "name": name, "panel": 77, "path": [category], "album": None,
                  "view_url": f"https://drive.google.com/file/d/{fid}/view",
                  "thumb_url": f"https://lh3.googleusercontent.com/d/{fid}=w600" if image else None,
                  "image_url": f"https://lh3.googleusercontent.com/d/{fid}=w1600" if image else None,
                  "is_image": image, "is_video": False, "is_pdf": not image},
        "i18n": {"title": {"en": en, "es": es}, "summary": {"en": "", "es": ""}},
        "machine": ["es" if lang == "en" else "en"], "is_new": False,
    }


GV_ITEM = drive_item("GVbanner1", GV_BANNER, "en", "Free shipping on all Grapevine products - banner",
                     "Envío gratis en todos los productos de Grapevine - banner")
LV_ITEM = drive_item("LVbanner1", LV_BANNER, "es", "Free shipping on all La Viña products - banner",
                     "Envíos gratuitos en todos los productos de La Viña - banner")
# a flyer of La Viña's in the same folder (the real one), the e-mail kept as a PDF in another folder, an older banner
OTHER_ITEMS = [
    drive_item("Cards1", "¡Tarjetas de ocasión para las fiestas! Paquete de 12 por $22 en La Viña.png", "es",
               "Holiday greeting cards! Pack of 12 for $22 at La Viña",
               "¡Tarjetas de ocasión para las fiestas! Paquete de 12 por $22 en La Viña", mime="image/png"),
    drive_item("Notes1", "Free shipping on all Grapevine products - e-mail.pdf", "en", "x", "x", category="notes",
               mime="application/pdf"),
]

OFFERS_JS = r"""
const S = await imp("eleventy/filters/shop.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const res = {};
for (const [name, c] of Object.entries(input.cases)) {
  const warnings = [];
  const warn = (kind, text) => warnings.push(`[${kind}] ${text}`);
  res[name] = { offers: S.shopOffers(c.site, c.lang, c.items || [], t, new Date(c.now), warn), warnings };
}
res.dates = input.dates.map(([a, b, l]) => S.offerDates(a, b, l, t));
res.months = Object.fromEntries(input.months.map(([f, l, today]) => [f, S.shopOfferIn(input.site, f, l, "es", today)]));
out(res);
"""


def offers(case: unittest.TestCase, cases: dict, dates: list | None = None, months: list | None = None) -> dict:
    return run_js(case, OFFERS_JS, data={"cases": cases, "dates": dates or [], "months": months or [], "site": SITE})


# =========================================================================== the filters
class Offers(unittest.TestCase):
    def test_the_window(self):
        moments = {"before": "2026-10-31T12:00:00Z", "first": FROM, "nov2": "2026-11-02T18:00:00Z",
                   "last_minute": "2027-01-01T05:59:00Z", "over": UNTIL, "later": "2027-02-01T12:00:00Z"}
        r = offers(self, {k: {"site": SITE, "lang": "en", "now": v} for k, v in moments.items()})
        win = {k: [o["win"] for o in v["offers"]] for k, v in r.items() if k in moments}
        self.assertEqual(win["before"], [{"from": FROM, "until": UNTIL, "hidden": True}],
                         "written before its first day, hidden until 00:00 Central on November 1 (GV.expire shows it)")
        for k in ("first", "nov2", "last_minute"):
            self.assertEqual(win[k], [{"from": "", "until": UNTIL, "hidden": False}], k)
        self.assertEqual((win["over"], win["later"]), ([], []), "from 00:00 Central on January 1 it is not written")
        self.assertEqual([v["warnings"] for v in r.values() if isinstance(v, dict) and "warnings" in v], [[]] * len(moments))

    def test_the_words_in_each_language(self):
        r = offers(self, {"en": {"site": SITE, "lang": "en", "now": "2026-11-02T18:00:00Z", "items": [GV_ITEM, LV_ITEM]},
                          "es": {"site": SITE, "lang": "es", "now": "2026-11-02T18:00:00Z", "items": [GV_ITEM, LV_ITEM]}})
        en, es = r["en"]["offers"][0], r["es"]["offers"][0]
        self.assertEqual((en["key"], en["starts"], en["ends"], en["icon"]), ("free-shipping-2026", "2026-11-01", "2026-12-31", "truck"))
        self.assertEqual((en["title"], en["titleLang"]), (OFFER["title"], "en"))
        self.assertEqual((es["title"], es["titleLang"]), (OFFER["title_es"], "es"))
        self.assertEqual((en["dates"], en["dateRange"]), ("November 1 – December 31, 2026",) * 2)
        self.assertEqual((es["dates"], es["dateRange"]), ("Del 1 de noviembre al 31 de diciembre de 2026",
                                                         "del 1 de noviembre al 31 de diciembre de 2026"))
        # the page language's magazine first; each store's own link (the settings' links), its button's words
        self.assertEqual([(s["key"], s["href"], s["label"]) for s in en["stores"]],
                         [("gv", LINKS["gv_store"], "Grapevine store"), ("lv", LINKS["lv_store"], "La Viña store")])
        self.assertEqual([(s["key"], s["href"], s["label"]) for s in es["stores"]],
                         [("lv", LINKS["lv_store"], "Tienda de La Viña"), ("gv", LINKS["gv_store"], "Tienda de Grapevine")])
        self.assertEqual([(s["text"], s["textLang"], s["alt"]) for s in en["stores"]],
                         [(OFFER["gv"]["text"], "en", OFFER["gv"]["banner_alt"]), (OFFER["lv"]["text"], "en", OFFER["lv"]["banner_alt"])])
        self.assertEqual([(s["text"], s["textLang"], s["alt"]) for s in es["stores"]],
                         [(OFFER["lv"]["text_es"], "es", OFFER["lv"]["banner_alt_es"]),
                          (OFFER["gv"]["text_es"], "es", OFFER["gv"]["banner_alt_es"])])
        self.assertEqual((en["source"], es["source"], es["sourceLang"]), (OFFER["source"], OFFER["source_es"], "es"))

    def test_a_missing_spanish_text_shows_the_english_one_marked(self):
        site = {"links": LINKS, "store_offers": [{**OFFER, "title_es": "", "gv": {"text": "Only in English."}, "lv": None}]}
        es = offers(self, {"es": {"site": site, "lang": "es", "now": "2026-11-02T18:00:00Z"}})["es"]["offers"][0]
        self.assertEqual((es["title"], es["titleLang"]), (OFFER["title"], "en"))
        self.assertEqual([(s["key"], s["text"], s["textLang"], s["banner"]) for s in es["stores"]],
                         [("gv", "Only in English.", "en", None)], "only the stores the block has words for")

    def test_the_banners_from_the_drive(self):
        items = [*OTHER_ITEMS, LV_ITEM, GV_ITEM,
                 {**drive_item("GVold", "Free shipping on all Grapevine products - banner (old).jpg", "en", "x", "x",
                               date="2025-11-01")}]
        r = offers(self, {"both": {"site": SITE, "lang": "en", "now": "2026-11-02T18:00:00Z", "items": items},
                          "none": {"site": SITE, "lang": "en", "now": "2026-11-02T18:00:00Z", "items": OTHER_ITEMS},
                          "pdf": {"site": SITE, "lang": "en", "now": "2026-11-02T18:00:00Z",
                                  "items": [drive_item("GVpdf", "Free shipping on all Grapevine products - banner.pdf", "en",
                                                       "x", "x", mime="application/pdf")]},
                          "newer-pdf": {"site": SITE, "lang": "en", "now": "2026-11-06T18:00:00Z",
                                        "items": [GV_ITEM, drive_item("GVpdf2", "Free shipping on all Grapevine products - details.pdf",
                                                                      "en", "x", "x", mime="application/pdf", date="2026-11-05")]}})
        both = {s["key"]: s["banner"] for s in r["both"]["offers"][0]["stores"]}
        self.assertEqual(both, {
            "gv": {"src": "https://lh3.googleusercontent.com/d/GVbanner1=w1200", "view": "https://drive.google.com/file/d/GVbanner1/view"},
            "lv": {"src": "https://lh3.googleusercontent.com/d/LVbanner1=w1200", "view": "https://drive.google.com/file/d/LVbanner1/view"},
        }, "each store's own banner (the newest picture it matches in flyers), 1200px wide")
        self.assertEqual([s["banner"] for s in r["none"]["offers"][0]["stores"]], [None, None], "no banner: the card has none")
        self.assertEqual([s["banner"] for s in r["pdf"]["offers"][0]["stores"]], [None, None], "only a picture is a banner")
        self.assertEqual([s["banner"] for s in r["newer-pdf"]["offers"][0]["stores"]],
                         [both["gv"], None], "a newer PDF that matches too never hides the banner (the newest picture)")

    def test_homes_uploads_leave_the_banners_out(self):
        # Home's "Shared by the committee" (index.njk: homeDrive with shopOfferBanners) — a banner stands next to the
        # offer's conditions on /shop/#offers, never alone; the folder's other flyers stay, before and after the days
        items = [*OTHER_ITEMS, LV_ITEM, GV_ITEM]
        r = run_js(self, r"""
          const S = await imp("eleventy/filters/shop.js");
          const res = {};
          for (const [name, site] of Object.entries(input.sites)) {
            const skip = filters.shopOfferBanners(site, input.items);
            res[name] = { skip, home: filters.homeDrive(input.items, 6, skip).map((i) => i.id) };
          }
          res.plain = filters.homeDrive(input.items, 6).map((i) => i.id);
          res.direct = S.shopOfferBanners(input.sites.offer, input.items);
          out(res);""", data={"items": items, "sites": {
            "offer": SITE, "later": {"links": LINKS, "store_offers": [{**OFFER, "starts": "2027-03-01", "ends": "2027-03-31"}]},
            "none": {"links": LINKS}, "gv-only": {"links": LINKS, "store_offers": [{k: v for k, v in OFFER.items() if k != "lv"}]}}})
        self.assertEqual(r["offer"]["skip"], ["drive:GVbanner1", "drive:LVbanner1"])
        self.assertEqual(r["direct"], r["offer"]["skip"])
        self.assertEqual(r["offer"]["home"], ["drive:Cards1", "drive:Notes1"])
        self.assertEqual(r["later"]["home"], ["drive:Cards1", "drive:Notes1"], "also before (and after) its days")
        self.assertEqual(r["none"]["skip"], [])
        self.assertEqual(sorted(r["none"]["home"]), sorted(r["plain"]), "no store_offers: every upload, as before")
        self.assertEqual(r["gv-only"]["skip"], ["drive:GVbanner1"], "only the banners a block finds")

    def test_a_block_with_a_mistake_is_left_out_and_named(self):
        good = {**OFFER, "key": "good", "starts": "2026-11-20", "ends": "2026-11-30"}
        blocks = [
            {**OFFER, "key": "bad-day", "starts": "2026-02-30"},
            {**OFFER, "key": "no-end", "ends": None},
            {**OFFER, "key": "backwards", "starts": "2026-12-31", "ends": "2026-11-01"},
            {**OFFER, "key": "untitled", "title": "", "title_es": ""},
            {**OFFER, "key": "wordless", "gv": {"banner_match": "x"}, "lv": "free shipping"},
            "free shipping",
            good,
            {**good, "title": "Again"},
            {**OFFER, "key": "bad-pattern", "gv": {**OFFER["gv"], "banner_match": "(free"}},
        ]
        r = offers(self, {"list": {"site": {"links": LINKS, "store_offers": blocks}, "lang": "en",
                                   "now": "2026-11-02T18:00:00Z", "items": [GV_ITEM]},
                          "one": {"site": {"links": LINKS, "store_offers": OFFER}, "lang": "en", "now": "2026-11-02T18:00:00Z"},
                          "none": {"site": {"links": LINKS}, "lang": "en", "now": "2026-11-02T18:00:00Z"},
                          "junk": {"site": {"links": LINKS, "store_offers": "free shipping"}, "lang": "en",
                                   "now": "2026-11-02T18:00:00Z"}})
        self.assertEqual([(o["key"], o["win"]["hidden"]) for o in r["list"]["offers"]], [("bad-pattern", False), ("good", True)],
                         "the rest still shows (first day first); a pattern that cannot be read only loses its banner")
        self.assertEqual([s["banner"] for s in r["list"]["offers"][0]["stores"]], [None, None])
        self.assertEqual(r["list"]["warnings"], [
            '[settings] store_offers entry 1 (bad-day): starts “2026-02-30” is not a day like "2026-11-01" — left out',
            '[settings] store_offers entry 2 (no-end): ends “” is not a day like "2026-11-01" — left out',
            "[settings] store_offers entry 3 (backwards): ends 2026-11-01 is before starts 2026-12-31 — left out",
            "[settings] store_offers entry 4 (untitled): it has no title — left out",
            "[settings] store_offers entry 5 (wordless): it has no text for either store (gv / lv) — left out",
            "[settings] store_offers entry 6: not a block of settings — left out",
            "[settings] store_offers entry 8 (good): the key “good” is used twice (each offer needs its own) — left out",
            "[settings] store_offers entry 9 (bad-pattern): gv banner_match “(free” is not a valid pattern — no banner",
        ])
        self.assertEqual([o["key"] for o in r["one"]["offers"]], ["free-shipping-2026"], "one block written without its “- ”")
        self.assertEqual((r["none"]["offers"], r["junk"]["offers"]), ([], []))

    def test_a_day_written_without_quotes(self):
        # YAML reads 2026-11-01 written without quotes as a date (src/_data/site.js: js-yaml)
        r = run_js(self, r"""
          const S = await imp("eleventy/filters/shop.js");
          const yaml = await import("js-yaml");
          const site = { links: {}, store_offers: yaml.load(input.text) };
          out(S.shopOffers(site, "en", [], (k) => k, new Date("2026-10-31T12:00:00Z")).map((o) => [o.starts, o.ends, o.win]));""",
                   data={"text": "- title: x\n  starts: 2026-11-01\n  ends: 2026-12-31\n  gv: { text: x }\n"})
        self.assertEqual(r, [["2026-11-01", "2026-12-31", {"from": FROM, "until": UNTIL, "hidden": True}]])

    def test_the_days_in_words_and_the_months(self):
        r = offers(self, {}, dates=[["2026-11-01", "2026-12-31", "en"], ["2026-11-01", "2026-12-31", "es"],
                                    ["2026-12-15", "2027-01-05", "en"], ["2026-12-15", "2027-01-05", "es"],
                                    ["2026-11-27", "2026-11-27", "en"], ["2026-11-27", "2026-11-27", "es"]],
                   months=[["2026-10-01", "2026-10-31", "2026-10-05"], ["2026-11-01", "2026-11-30", "2026-11-02"],
                           ["2026-12-01", "2026-12-31", "2026-12-31"], ["2027-01-01", "2027-01-31", "2027-01-01"]])
        self.assertEqual(r["dates"], ["November 1 – December 31, 2026", "del 1 de noviembre al 31 de diciembre de 2026",
                                      "December 15, 2026 – January 5, 2027", "del 15 de diciembre de 2026 al 5 de enero de 2027",
                                      "November 27, 2026", "27 de noviembre de 2026"])
        m = r["months"]
        self.assertEqual((m["2026-10-01"], m["2027-01-01"]), ([], []))
        one = {"key": "free-shipping-2026", "title": OFFER["title_es"], "titleLang": "es", "starts": "2026-11-01",
               "ends": "2026-12-31", "showStarts": True, "icon": "truck", "past": False}
        self.assertEqual((m["2026-11-01"], m["2026-12-01"]), ([one], [one]), "its last day is not past yet")

    def test_a_stores_own_page_for_the_offer(self):
        # a store with its own page for the offer (AA Grapevine's /2gifts): its button goes there, in words of its
        # own, and its page for Canadian addresses gets a link beside it; the other store keeps its store front.
        # The block's own icon (a gift), else the truck
        gifts = {**OFFER, "key": "gifts", "icon": "gift", "gv": {"text": "A second gift.", "url": "https://www.gv.example.org/2gifts",
                                                 "url_ca": "www.gv.example.org/canada-2gifts"},
                 "lv": {"text": "A second gift.", "text_es": "Un segundo regalo."}}
        bad = {**OFFER, "key": "bad-links", "icon": "no-such-icon", "gv": {"text": "x", "url": "javascript:alert(1)",
                                                                           "url_ca": "/shop/"}, "lv": None}
        site = {"links": LINKS, "store_offers": [gifts, bad]}
        r = offers(self, {"en": {"site": site, "lang": "en", "now": "2026-11-12T18:00:00Z"},
                          "es": {"site": site, "lang": "es", "now": "2026-11-12T18:00:00Z"}})
        en, es = ({o["key"]: o for o in r[k]["offers"]} for k in ("en", "es"))
        self.assertEqual([(s["key"], s["href"], s["label"], s["hrefCa"], s["labelCa"]) for s in en["gifts"]["stores"]], [
            ("gv", "https://www.gv.example.org/2gifts", "Grapevine's offer page", "https://www.gv.example.org/canada-2gifts",
             "Grapevine's page for Canadian addresses"),
            ("lv", LINKS["lv_store"], "La Viña store", "", "")])
        self.assertEqual([(s["key"], s["href"], s["label"], s["hrefCa"], s["labelCa"]) for s in es["gifts"]["stores"]], [
            ("lv", LINKS["lv_store"], "Tienda de La Viña", "", ""),
            ("gv", "https://www.gv.example.org/2gifts", "Página de la oferta de Grapevine",
             "https://www.gv.example.org/canada-2gifts", "Página de Grapevine para direcciones en Canadá")])
        # an address that is not a web page: the button goes to the store, no Canada link; an icon the site does not
        # have: the truck — each named; the block still shows
        self.assertEqual([(s["href"], s["label"], s["hrefCa"]) for s in en["bad-links"]["stores"]],
                         [(LINKS["gv_store"], "Grapevine store", "")])
        self.assertEqual((en["gifts"]["icon"], en["bad-links"]["icon"]), ("gift", "truck"))
        self.assertEqual(r["en"]["warnings"], [
            "[settings] store_offers entry 2 (bad-links): gv url “javascript:alert(1)” is not a web address — the button "
            "goes to the store",
            "[settings] store_offers entry 2 (bad-links): gv url_ca “/shop/” is not a web address — no Canada link",
            "[settings] store_offers entry 2 (bad-links): icon “no-such-icon” is not one of the site's icons — the truck"])

    def test_an_offer_whose_stores_give_no_first_day(self):
        # show_starts: false (or "no") — its days say only the last one; `starts` still decides when it shows, and the
        # toolkit's months
        site = {"links": LINKS, "store_offers": [{**OFFER, "key": "gifts", "starts": "2026-11-11", "show_starts": False},
                                                 {**OFFER, "key": "gifts-2", "starts": "2026-11-11", "show_starts": "no"}]}
        r = run_js(self, r"""
          const S = await imp("eleventy/filters/shop.js");
          const conf = await imp("eleventy.config.js");
          const t = (k, l, v) => conf.translateKey(k, l, v);
          const at = (now, lang) => S.shopOffers(input.site, lang, [], t, new Date(now)).map((o) => [o.key, o.dates, o.dateRange, o.win]);
          out({ before: at("2026-11-10T12:00:00Z", "en"), en: at("2026-11-12T12:00:00Z", "en"), es: at("2026-11-12T12:00:00Z", "es"),
                oct: S.shopOfferIn(input.site, "2026-10-01", "2026-10-31", "en"),
                nov: S.shopOfferIn(input.site, "2026-11-01", "2026-11-30", "en"),
                days: [S.offerDates("", "2026-12-31", "en", t), S.offerDates("", "2026-12-31", "es", t),
                       S.offerDates("2026-11-11", "", "en", t)] });""", data={"site": site})
        shown = {"from": "", "until": UNTIL, "hidden": False}
        self.assertEqual(r["en"], [["gifts", "Through December 31, 2026", "through December 31, 2026", shown],
                                   ["gifts-2", "Through December 31, 2026", "through December 31, 2026", shown]])
        self.assertEqual([x[1:3] for x in r["es"]], [["Hasta el 31 de diciembre de 2026", "hasta el 31 de diciembre de 2026"]] * 2)
        self.assertEqual([x[3] for x in r["before"]], [{"from": "2026-11-11T06:00:00Z", "until": UNTIL, "hidden": True}] * 2,
                         "written hidden until 00:00 Central on its starts day")
        self.assertEqual(r["oct"], [], "October's toolkit: before the day the site shows it from")
        self.assertEqual([(o["key"], o["showStarts"]) for o in r["nov"]], [("gifts", False), ("gifts-2", False)])
        self.assertEqual(r["days"], ["through December 31, 2026", "hasta el 31 de diciembre de 2026", ""])


# =========================================================================== the banners' names on the Drive
class DriveNames(unittest.TestCase):
    """The banners sit in the Panel's `flyers` folder: their names have no date, so they make no event, no month's
    flyer — and their language is read from the words (the Spanish one is Spanish)."""

    def test_the_two_names(self):
        for name, lang in ((GV_BANNER, "en"), (LV_BANNER, "es")):
            with self.subTest(name=name):
                e = Entry(id="FILE123", name=name, mime="image/jpeg", modified="2026-11-02")
                f = Found(entry=e, panel=Panel(77, "Panel 77", "P", "2027-2028_Panel77_GVLV"), path=["flyers"],
                          chain=["R", "P", "C"], seq=1)
                it = build_item(f, {})
                x = it["extra"]
                self.assertEqual((it["category"], it["kind"], it["lang"], it["title"]), ("flyers", "photo", lang, name[:-4]))
                for key in ("event_date", "event_end_date", "event_month", "expires"):
                    self.assertFalse(x.get(key), key)
                self.assertTrue(x["is_image"])


# =========================================================================== the monthly toolkit's message
MESSAGE_JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const { db, site, carry } = input;
const res = {};
for (const [key, now] of input.runs) {
  const d = new Date(now);
  const mm = { en: M.monthModel(key, db, carry, site, "en", d), es: M.monthModel(key, db, carry, site, "es", d) };
  const nw = { en: M.monthNow(db, site, "en", d), es: M.monthNow(db, site, "es", d) };
  const iss = { en: M.monthIssueLinks(db, mm.en), es: M.monthIssueLinks(db, mm.es) };
  res[`${key}@${now}`] = { offers: mm.en.offers, wa: M.monthMessage({ mm, nw, iss }, ["en"], "whatsapp", site, t),
    es: M.monthMessage({ mm, nw, iss }, ["es"], "email", site, t), bi: M.monthMessage({ mm, nw, iss }, ["es", "en"], "email", site, t) };
}
out(res);
"""


class Message(unittest.TestCase):
    """The month's message (a group chat, an e-mail) names the offer in the months it runs, with a link to its own
    section, /shop/#offers-<key> — this month's message only while it is not over."""

    def test_the_months(self):
        site = {**TM.SITE, "links": LINKS, "store_offers": [OFFER]}
        runs = [["2026-10", "2026-10-05T17:00:00Z"], ["2026-11", "2026-10-05T17:00:00Z"], ["2026-12", "2026-10-05T17:00:00Z"],
                ["2027-01", "2026-10-05T17:00:00Z"], ["2026-11", "2026-11-03T17:00:00Z"]]
        r = run_js(self, MESSAGE_JS, data={"db": TM.full_db(), "site": site, "carry": TM.CARRY, "runs": runs})
        # under its own heading, a paragraph apart from the Book of the Month (never read as one deal)
        block = ("\n\n📦 *Free shipping at the Grapevine and La Viña stores*\n"
                 "November 1 – December 31, 2026: https://example.org/site/shop/#offers-free-shipping-2026\n\n")
        es_title = "ENVÍO GRATIS EN LAS TIENDAS DE LA VIÑA Y GRAPEVINE"
        for k in ("2026-11@2026-10-05T17:00:00Z", "2026-12@2026-10-05T17:00:00Z", "2026-11@2026-11-03T17:00:00Z"):
            with self.subTest(k):
                self.assertIn(block, r[k]["wa"])
                self.assertIn(f"\n\n{es_title}\n{'-' * len(es_title)}\nDel 1 de noviembre al 31 de diciembre de "
                              "2026: https://example.org/site/es/shop/#offers-free-shipping-2026\n", r[k]["es"])
                self.assertNotIn("📦", r[k]["es"], "the e-mail has no emoji")
                self.assertIn("ENVÍO GRATIS EN LAS TIENDAS DE LA VIÑA Y GRAPEVINE / FREE SHIPPING AT THE GRAPEVINE AND LA VIÑA "
                              "STORES\n", r[k]["bi"])
                self.assertIn("\nDel 1 de noviembre al 31 de diciembre de 2026 / November 1 – December 31, 2026: "
                              "https://example.org/site/es/shop/#offers-free-shipping-2026\n", r[k]["bi"])
        for k in ("2026-10@2026-10-05T17:00:00Z", "2027-01@2026-10-05T17:00:00Z"):
            self.assertNotIn("#offers", r[k]["wa"] + r[k]["bi"], k)
            self.assertEqual(r[k]["offers"], [], k)

    def test_this_months_message_leaves_out_an_offer_that_is_over(self):
        site = {**TM.SITE, "store_offers": [{**OFFER, "key": "early", "starts": "2026-11-01", "ends": "2026-11-10"}, OFFER]}
        r = run_js(self, MESSAGE_JS, data={"db": TM.full_db(), "site": site, "carry": TM.CARRY,
                                           "runs": [["2026-11", "2026-11-12T17:00:00Z"], ["2026-11", "2026-10-20T17:00:00Z"]]})
        now, ahead = r["2026-11@2026-11-12T17:00:00Z"], r["2026-11@2026-10-20T17:00:00Z"]
        self.assertEqual([(o["key"], o["past"]) for o in now["offers"]], [("early", True), ("free-shipping-2026", False)])
        self.assertEqual(now["wa"].count("📦"), 1, "November 12: the offer that ended on the 10th is left out")
        self.assertEqual(ahead["wa"].count("📦"), 2, "a later month's message gives its whole plan")

    def test_an_offer_whose_stores_give_no_first_day(self):
        # show_starts: false — "Through December 31, 2026", after the free shipping (first day first); icon: gift —
        # 🎁, not the parcel (a gift offer is not about shipping)
        gifts = {**OFFER, "key": "gifts", "title": "Holiday gift offers", "title_es": "Ofertas de regalo", "starts": "2026-11-11",
                 "show_starts": False, "icon": "gift"}
        site = {**TM.SITE, "links": LINKS, "store_offers": [gifts, OFFER]}
        r = run_js(self, MESSAGE_JS, data={"db": TM.full_db(), "site": site, "carry": TM.CARRY,
                                           "runs": [["2026-11", "2026-11-12T17:00:00Z"]]})["2026-11@2026-11-12T17:00:00Z"]
        self.assertIn("\n\n🎁 *Holiday gift offers*\nThrough December 31, 2026: https://example.org/site/shop/#offers-gifts\n\n",
                      r["wa"])
        self.assertIn("\nHasta el 31 de diciembre de 2026 / Through December 31, 2026: "
                      "https://example.org/site/es/shop/#offers-gifts\n", r["bi"])
        self.assertLess(r["wa"].index("📦 *Free shipping"), r["wa"].index("🎁 *Holiday gift offers"))
        self.assertEqual(r["wa"].count("📦"), 1)
        self.assertNotIn("🎁", r["bi"], "the e-mail has no emoji")
        self.assertNotIn("November 11", r["wa"] + r["bi"])


# =========================================================================== the pages
PAGES_JS = r"""
process.env.ONLY = "shop.njk,monthly-month";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const result = {};
for (const [name, now] of Object.entries(input.builds)) {
  process.env.MONTHLY_NOW = now;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-offers-"));
  try {
    const elev = new Eleventy("src", dir, {
      quietMode: true, configPath: "eleventy.config.js",
      config(cfg) {
        cfg.addGlobalData("eleventyComputed", {
          site: (data) => ({ ...data.site, links: { ...data.site.links, ...input.links }, store_offers: input.offers }),
          db: (data) => ({ ...data.db, drive: { ...(data.db.drive || {}), items: input.drive } }),
        });
      },
    });
    const pages = await elev.toJSON();
    const want = new Set(input.want);
    result[name] = Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content]));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
out(result);
"""
BUILDS = {"before": "2026-10-31T12:00:00Z", "during": "2026-11-03T15:00:00Z", "after": "2027-01-01T06:30:00Z"}
URLS = ["/shop/", "/es/shop/", "/monthly/2026-10/", "/monthly/2026-11/", "/es/monthly/2026-11/", "/monthly/2027-01/"]


def section(page: str, sid: str) -> str:
    """<section id="…">…</section> (holding no other section)."""
    i = page.index(f'<section id="{sid}"')
    return page[i:page.index("</section>", i) + len("</section>")]


def keep_rows(page: str) -> list[str]:
    """The "Keep up all month" rows (#mp-keep) of a month's page."""
    return re.findall(r"<li\b.*?</li>", section(page, "mp-keep"), re.S)


def text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip().replace("&#39;", "'")


class BuiltPages(unittest.TestCase):
    built: dict | None = None

    @classmethod
    def pages(cls, case: unittest.TestCase) -> dict:
        if cls.built is None:
            cls.built = run_js(case, PAGES_JS, data={"builds": BUILDS, "want": URLS, "links": LINKS, "offers": [OFFER],
                                                     "drive": [GV_ITEM, LV_ITEM, *OTHER_ITEMS]}, timeout=900)
        return cls.built

    def test_during_the_offer(self):
        p = self.pages(self)["during"]
        for url, lang in (("/shop/", "en"), ("/es/shop/", "es")):
            with self.subTest(url=url):
                page = p[url]
                sec = section(page, "offers")
                head = sec[:sec.index(">") + 1]
                self.assertIn('data-gv-expire="2027-01-01T06:00:00Z"', head)
                self.assertNotIn("data-gv-from", head)
                self.assertNotIn(" hidden", head)
                self.assertIn('aria-labelledby="offer-free-shipping-2026-title"', head)
                # the first offer is #offers, and #offers-<key> too (a bulletin post links its own offer by its key)
                self.assertIn('<div class="shop-offer" id="offers-free-shipping-2026">', sec)
                self.assertIn('id="offer-free-shipping-2026-title"', sec)
                # right under the page nav, above the Book of the Month (when the stores have one) and the magazines
                at = page.index('<section id="offers"')
                self.assertLess(page.index('class="page-nav'), at)
                self.assertLess(at, page.index('id="magazines"'))
                if 'id="botm"' in page:
                    self.assertLess(at, page.index('id="botm"'))
                self.assertNotIn('href="#offers"', page, "no chip in the page nav (a chip cannot hide by date)")
                stores = [m.group(1) for m in re.finditer(r'<a class="btn-(?:primary|lv)" href="([^"]+)"', sec)]
                self.assertEqual(stores, [LINKS["gv_store"], LINKS["lv_store"]] if lang == "en" else [LINKS["lv_store"], LINKS["gv_store"]])
                banners = re.findall(r'<a class="shop-offer-art" href="([^"]+)"[^>]*><img src="([^"]+)" alt="([^"]*)"', sec)
                self.assertEqual([(h, s) for h, s, _ in banners],
                                 [(LINKS["gv_store"], "https://lh3.googleusercontent.com/d/GVbanner1=w1200"),
                                  (LINKS["lv_store"], "https://lh3.googleusercontent.com/d/LVbanner1=w1200")][::1 if lang == "en" else -1])
                self.assertEqual(len(re.findall(r'width="1920" height="770" loading="lazy"', sec)), 2)
                words = text(sec)
                if lang == "en":
                    self.assertIn("Free shipping at the Grapevine and La Viña stores November 1 – December 31, 2026", words)
                    self.assertIn("Free shipping on all Grapevine products to U.S. and Canadian addresses.", words)
                    self.assertIn("Free shipping on all La Viña products to the U.S. and Canada.", words)
                    self.assertIn("The store shows the final price at checkout. Source: AA Grapevine's", words)
                    self.assertEqual(sec.count("(opens a new tab)"), 4)
                else:
                    self.assertIn("Envío gratis en las tiendas de La Viña y Grapevine Del 1 de noviembre al 31 de diciembre de 2026", words)
                    self.assertIn("Envío gratis en todos los productos de La Viña a EE. UU. y Canadá.", words)
                    self.assertIn("Según Grapevine, la oferta no se puede combinar con ninguna otra.", words)
                    self.assertLess(words.index("Tienda de La Viña"), words.index("Tienda de Grapevine"))
        # November's toolkit: a row in "Keep up all month", in the offer's window, and a line in the month's message
        for url, href, title, days, mid in (("/monthly/2026-11/", "/shop/#offers-free-shipping-2026", OFFER["title"],
                                             "November 1 – December 31, 2026",
                                             "November 1 – December 31, 2026"),
                                            ("/es/monthly/2026-11/", "/es/shop/#offers-free-shipping-2026", OFFER["title_es"],
                                             "Del 1 de noviembre al 31 de diciembre de 2026", "del 1 de noviembre al 31 de diciembre de 2026")):
            with self.subTest(url=url):
                rows = [r for r in keep_rows(p[url]) if f'href="{href}"' in r]
                self.assertEqual(len(rows), 1)
                self.assertTrue(rows[0].startswith('<li data-gv-when data-gv-expire="2027-01-01T06:00:00Z">')
                                or rows[0].startswith('<li data-gv-when="" data-gv-expire="2027-01-01T06:00:00Z">'), rows[0][:120])
                self.assertEqual(text(rows[0]), f"{title} {days}")
                self.assertIn(f"{title}*\n{days}: ", p[url].replace("&#39;", "'"), "the month's message (WhatsApp)")

    def test_the_rows_place(self):
        # after the price change's rows, before the subscription line (a hidden last row would leave a stray divider)
        page = (ROOT / "src" / "pages" / "monthly-month.njk").read_text(encoding="utf-8")
        at = page.index("{% for o in (site | shopOffers(lang)) %}{% if o.starts <= m.last %}")
        self.assertLess(page.index("shopPriceChanges(lang)"), at)
        self.assertLess(at, page.index("{% if nx.subsFrom %}"))
        self.assertIn("<li{{ ui.when(o.win) }}>", page[at:])

    def test_before_the_offer(self):
        p = self.pages(self)["before"]
        for url in ("/shop/", "/es/shop/"):
            head = section(p[url], "offers")
            head = head[:head.index(">") + 1]
            self.assertIn(f'data-gv-from="{FROM}"', head, url)
            self.assertIn(f'data-gv-expire="{UNTIL}"', head, url)
            self.assertRegex(head, r"\shidden(?:=\"\")?>$", "written hidden: GV.expire shows it at 00:00 Central on November 1")
        self.assertNotIn("#offers", section(p["/monthly/2026-10/"], "mp-keep"), "October's toolkit: not an offer of its month")

    def test_after_the_offer(self):
        p = self.pages(self)["after"]
        for url in ("/shop/", "/es/shop/"):
            self.assertNotIn('id="offers"', p[url], url)
            self.assertNotIn("shop-offer", p[url], url)
        self.assertNotIn("#offers", p["/monthly/2027-01/"])


# =========================================================================== the committee's own block
CONFIG = ROOT / "config" / "site.yml"
FORBIDDEN = (r"(?i)hurry|don.t miss|prisa|no code|\bcode\b|c[oó]digo|minimum|m[ií]nimo|subscri|suscrip|[uú]ltima|"
             r"combina con|combines|stack|international|internacional|last chance|\bnow\b|ahora|!")


class RealSettings(unittest.TestCase):
    """config/site.yml store_offers as the committee wrote it (the Code check: scripts/ops/gate_tests.py CONTENT_TESTS):
    every block can be shown; the free shipping of November–December 2026 says what AA Grapevine's and La Viña's
    e-mails and banners say — free shipping on all products, U.S. and Canadian addresses only, Grapevine's offer not
    combined with any other — and nothing they don't; its banner patterns find the two banners in Drive `flyers` and
    nothing else (not the committee's other flyers, not PR #10's flyer names)."""

    @classmethod
    def setUpClass(cls):
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        cls.cfg = cfg
        cls.block = next((o for o in (cfg.get("store_offers") or []) if isinstance(o, dict) and o.get("key") == "free-shipping-2026"), None)

    def test_every_block_can_be_shown(self):
        r = run_js(self, r"""
          const S = await imp("eleventy/filters/shop.js");
          const site = (await imp("src/_data/site.js")).default();
          const warnings = [];
          S.shopOffers(site, "en", [], (k) => k, new Date("2000-01-01T00:00:00Z"), (k, t) => warnings.push(t));
          out(warnings);""")
        self.assertEqual(r, [], "config/site.yml store_offers: a block with a mistake is left out of the site")

    def test_the_free_shipping_of_2026(self):
        o = self.block
        if o is None:
            self.skipTest("the free shipping block of 2026 is no longer in config/site.yml")
        self.assertEqual((o["starts"], o["ends"]), ("2026-11-01", "2026-12-31"))
        self.assertEqual((o["title"], o["title_es"]), ("Free shipping at the Grapevine and La Viña stores",
                                                       "Envío gratis en las tiendas de La Viña y Grapevine"))
        gv, lv = o["gv"], o["lv"]
        for store in (gv, lv):
            self.assertRegex(store["text"], r"^Free shipping on all (Grapevine|La Viña) products to .*U\.S\. and Canad")
            self.assertRegex(store["text_es"], r"^Envío gratis en todos los productos de (Grapevine|La Viña) a .*EE\. UU\. y Canadá")
        self.assertIn("can't be combined with any other offer", gv["text"])
        self.assertIn("no se puede combinar con ninguna otra", gv["text_es"])
        self.assertNotRegex(lv["text"] + lv["text_es"], r"(?i)combin", "La Viña says nothing about combining")
        words = [o[k] for k in ("title", "title_es", "source", "source_es")] + \
            [s[k] for s in (gv, lv) for k in ("text", "text_es", "banner_alt", "banner_alt_es")]
        for w in words:
            self.assertNotRegex(w, FORBIDDEN, w)
            self.assertNotIn("trackingcode", w)
        # Spanish: La Viña first where both are named; the days in Spanish words (not the banner's "Noviembre 1˚ - December")
        for w in (o["title_es"], o["source_es"]):
            self.assertLess(w.index("La Viña"), w.index("Grapevine"), w)
        self.assertNotRegex(" ".join(words), r"December 31\b.*Noviembre|Noviembre 1|1˚")
        self.assertEqual(self.cfg["links"]["gv_store"], "https://www.aagrapevine.org/store")
        self.assertEqual(self.cfg["links"]["lv_store"], "https://www.aalavina.org/tienda")

    def test_the_banner_patterns_find_the_banners_and_nothing_else(self):
        o = self.block
        if o is None:
            self.skipTest("the free shipping block of 2026 is no longer in config/site.yml")
        pats = {pub: re.compile(o[pub]["banner_match"], re.I) for pub in ("gv", "lv")}
        own = {"gv": GV_BANNER, "lv": LV_BANNER}
        for pub, name in own.items():
            self.assertRegex(name, pats[pub])
            self.assertRegex(name[:-4], pats[pub])
            self.assertNotRegex(own["lv" if pub == "gv" else "gv"], pats[pub], "never the other store's banner")
        # PR #10's flyer names (test_r20_meeting.RealSettings.test_the_flyer_names) and the e-mails kept in `private`
        others = ["Grapevine Meeting - flyer.png", "Our online meetings - flyer.png", "2027 Guest Speaker Series - flyer.png",
                  "Committee Meeting - flyer.png", "January 2027 Committee Meeting - guest speaker.png",
                  "AA Grapevine - Free Shipping Sale - e-mail of 2026-11-02.png",
                  "La Viña - Rebajas de fin de año - correo del 2026-11-02.png"]
        drive = json.loads((ROOT / "data" / "site" / "drive.json").read_text(encoding="utf-8")).get("items", [])
        for it in drive:
            texts = [it.get("title"), *((it.get("i18n") or {}).get("title") or {}).values(), (it.get("extra") or {}).get("name")]
            for pub, pat in pats.items():
                if any(t and pat.search(t) for t in texts):
                    self.assertEqual((it.get("extra") or {}).get("name"), own[pub], f"{pub} banner_match finds {it.get('title')!r}")
        for name in others:
            for pat in pats.values():
                self.assertNotRegex(name, pat)
        # … and the settings' other patterns never take a banner for a series' flyer or AA Grapevine's notice
        patterns = [x.get("flyer_match") for x in (self.cfg.get("recurring_events") or []) if isinstance(x, dict)]
        patterns += [(self.cfg.get("lavina_weekly_open") or {}).get("flyer_match")]
        patterns += [x.get("doc_match") for x in (self.cfg.get("price_changes") or []) if isinstance(x, dict)]
        for pattern in filter(None, patterns):
            for name in own.values():
                self.assertNotRegex(name, re.compile(pattern, re.I), pattern)


if __name__ == "__main__":
    unittest.main()
