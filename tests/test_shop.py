"""Book of the Month / subscriptions / specialty items (scripts/sync/shop.py → build_data →
data/site/shop.json) and La Viña's weekly open meeting (scripts/sync/weekly_open.py, second item).

Fixtures in tests/fixtures/shop/ are trimmed copies of the official store pages (September 2026; the
specialty pages — gv_greeting_cards, gv_pocket_planner, gv_wall_calendar, lv_articulos_especiales —
from September 27, 2026, before the holiday cards were on sale; the holiday cards' pages and the two
listings that show them — gv_holiday_cards, lv_holiday_cards, gv_specialty_items,
lv_articulos_especiales_holidays — from October 1, 2026, in season).
Run:  python -m unittest tests.test_shop -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "tests"))

from nodejs import run_js  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import shop as S  # noqa: E402
from scripts.sync.common import merge_items  # noqa: E402
from scripts.sync import weekly_open as W  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "shop"
TODAY = date(2026, 9, 24)
GV, LV = "https://www.aagrapevine.org", "https://www.aalavina.org"
GV_PRODUCT = f"{GV}/store/no-matter-what-dealing-adversity-sobriety"
LV_PRODUCT = f"{LV}/tienda/frente-frente"
GV_HOLIDAY = f"{GV}/store/holiday-greeting-cards-12-pack"
LV_HOLIDAY = f"{LV}/tienda/tarjetas-de-ocasion-para-las-fiestas-paquete-de-12"
GV_SPECIALTY, LV_SPECIALTY = f"{GV}/store/specialty-items", f"{LV}/tienda/articulos-especiales"


def fx(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


# Every page the module asks for, answered from the fixtures (anything else = a failed fetch).
PAGES = {
    f"{GV}/BOTM": "gv_botm.html", GV_PRODUCT: "gv_product.html",
    f"{LV}/libro-del-mes": "lv_botm.html", LV_PRODUCT: "lv_product.html",
    f"{GV}/store/grapevine-subscriptions": "gv_subscriptions.html",
    f"{LV}/tienda/suscripciones": "lv_subscriptions.html",
    f"{GV}/store/us-subscriptions": "gv_us_listing.html", f"{LV}/US-suscripciones": "lv_us_listing.html",
    f"{GV}/store/grapevine-complete-subscription-1-year": "gv_complete_product.html",
    f"{GV}/store/greeting-cards": "gv_greeting_cards.html", f"{GV}/store/annual-pocket-planner": "gv_pocket_planner.html",
    f"{GV}/store/annual-wall-calendar": "gv_wall_calendar.html",
    GV_HOLIDAY: "gv_holiday_cards.html", GV_SPECIALTY: "gv_specialty_items.html",
    LV_SPECIALTY: "lv_articulos_especiales_holidays.html", LV_HOLIDAY: "lv_holiday_cards.html",
}
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fixture_fetch(url: str) -> str | None:
    name = PAGES.get(url)
    return fx(name) if name else None


# The price and SKU fields as Drupal renders them with their "Price" / "SKU" label hidden (one value):
# .field__item moves onto the field's own div — the form the listing cards' title and image fields already have.
LABEL_SHOWN = re.compile(r'<div class="([^"]*field--name-(?:price|sku)[^"]*) field--label-inline">\s*'
                         r'<div class="field__label">[^<]*</div>\s*<div class="field__item">([^<]*)</div>\s*</div>')


def label_hidden(html: str) -> str:
    out, n = LABEL_SHOWN.subn(r'<div class="\1 field--label-hidden field__item">\2</div>', html)
    assert n, "the fixture's price / SKU markup changed"
    return out


def without_holiday_cards(html: str) -> str:
    """A specialty listing as the store shows it after the season: its holiday cards' card taken out."""
    soup = BeautifulSoup(html, "lxml")
    for row in soup.select(".views-row"):
        if S.specialty_kind(row.get_text(" ")) == "holiday":
            row.decompose()
    return str(soup)


def out_of_season(url: str) -> str | None:
    """The stores after the holidays: the holiday cards' own pages are gone (404) and the listings no longer
    show them (La Viña's: as it was on September 27); every other page as in fixture_fetch."""
    if url in (GV_HOLIDAY, LV_HOLIDAY):
        return None
    if url == LV_SPECIALTY:
        return fx("lv_articulos_especiales.html")
    html = fixture_fetch(url)
    return without_holiday_cards(html) if html and url == GV_SPECIALTY else html


def specialty(res: dict) -> dict[str, dict]:
    return {i["id"]: i for i in res["items"] if i["kind"] == "specialty"}


SPECIAL_IDS = {"special:gv:GVGC01", "special:gv:MS09", "special:gv:MS08", "special:gv:GVGCH1",
               "special:lv:LVGC01", "special:lv:MS09LV", "special:lv:MS08LV", "special:lv:LVGCH1"}


def listing_fetch(change):
    """fixture_fetch with `change` applied to the two subscription listings."""
    def fetch(url: str) -> str | None:
        html = fixture_fetch(url)
        return change(html) if html and PAGES.get(url, "").endswith("_listing.html") else html
    return fetch


class BookOfTheMonth(unittest.TestCase):
    def test_grapevine_offer(self):
        o = S.parse_botm(fx("gv_botm.html"), f"{GV}/BOTM", "en", TODAY)
        self.assertEqual(o["title"], "No Matter What: Dealing With Adversity in Sobriety")
        self.assertEqual(o["url"], GV_PRODUCT)
        self.assertEqual(o["discount_pct"], 20)
        self.assertEqual((o["month"], o["month_label"]), (10, "October"))
        self.assertEqual((o["starts"], o["ends"]), ("2026-09-15", "2026-10-14"))   # "SEPT. 15 thru OCt. 14"
        self.assertTrue(o["blurb"].startswith("All recovering alcoholics"))

    def test_la_vina_offer_in_spanish(self):
        o = S.parse_botm(fx("lv_botm.html"), f"{LV}/libro-del-mes", "es", TODAY)
        self.assertEqual(o["title"], "Frente a Frente: El apadrinamiento en acción")
        self.assertEqual(o["url"], LV_PRODUCT)
        self.assertEqual(o["month_label"], "Octubre")
        self.assertEqual((o["starts"], o["ends"]), ("2026-08-15", "2026-10-14"))   # "del 15 de AGOSTO al 14 de OCTUbre"
        self.assertTrue(o["blurb"].startswith("Detrás de cada historia"))

    def test_the_percent_comes_from_the_page(self):
        html = fx("gv_botm.html").replace("20% off", "25% off")
        o = S.parse_botm(html, f"{GV}/BOTM", "en", TODAY)
        self.assertEqual(o["discount_pct"], 25)
        self.assertEqual(S.sale_price(14.99, 25), 11.24)
        self.assertEqual(S.sale_price(14.99, 20), 11.99)

    def test_years_are_inferred_around_today(self):
        line = "Offer good for this title: DEC. 15 thru JAN. 14 Only."
        self.assertEqual(S.offer_dates(line, date(2027, 1, 5)), ("2026-12-15", "2027-01-14"))
        self.assertEqual(S.offer_dates(line, date(2026, 12, 20)), ("2026-12-15", "2027-01-14"))
        self.assertEqual(S.offer_dates("Oferta válida del 15 de diciembre al 14 de enero", date(2026, 12, 1)),
                         ("2026-12-15", "2027-01-14"))
        self.assertEqual(S.offer_dates("Offer good: Oct. 1, 2026 through Oct. 31, 2026", TODAY), ("2026-10-01", "2026-10-31"))

    def test_an_old_offer_left_on_the_page_is_past_not_next_year(self):
        self.assertEqual(S.offer_dates("APRIL 15 thru MAY 14", date(2026, 11, 20)), ("2026-04-15", "2026-05-14"))

    def test_no_offer_and_broken_offer(self):
        empty = ("<html><head><title>Book of the month! | AA Grapevine</title></head><body><main>"
                 "<div id='block-neatosub-content'><p>Check back soon!</p></div></main></body></html>")
        self.assertIsNone(S.parse_botm(empty, f"{GV}/BOTM", "en", TODAY))
        # an unrelated 200 page (maintenance, a redirect home) is an error, so the previous offer is kept
        maint = "<html><head><title>We'll be back soon</title></head><body><main><p>Maintenance</p></main></body></html>"
        with self.assertRaises(S.ShopParseError):
            S.parse_botm(maint, f"{GV}/BOTM", "en", TODAY)
        no_link = fx("gv_botm.html").replace("/store/no-matter-what-dealing-adversity-sobriety", "/somewhere")
        with self.assertRaises(S.ShopParseError):
            S.parse_botm(no_link, f"{GV}/BOTM", "en", TODAY)


class ProductPages(unittest.TestCase):
    TIERS = [{"min": 1, "max": 4, "off": 0.0}, {"min": 5, "max": 9, "off": 0.5}, {"min": 10, "max": 19, "off": 1.0},
             {"min": 20, "max": 29, "off": 2.0}, {"min": 30, "max": None, "off": 3.0}]

    def test_grapevine_book(self):
        p = S.parse_product(fx("gv_product.html"), GV_PRODUCT)
        self.assertEqual((p["price"], p["currency"], p["sku"]), (14.99, "USD", "GV31"))
        self.assertIn("/styles/product_feature_image/", p["image"])
        self.assertEqual(p["tiers"], self.TIERS)
        self.assertIn("physical books", p["tiers_note"])

    def test_la_vina_book(self):
        p = S.parse_product(fx("lv_product.html"), LV_PRODUCT)
        self.assertEqual((p["price"], p["sku"]), (14.99, "SGV04"))
        self.assertEqual(p["tiers"], self.TIERS)                      # "5 a 9 libros: $0.50 de descuento por libro."
        self.assertIn("libros físicos", p["tiers_note"])

    def test_visible_price_when_there_is_no_json_ld(self):
        html = fx("gv_product.html").replace("application/ld+json", "text/plain")
        p = S.parse_product(html, GV_PRODUCT)
        self.assertEqual((p["price"], p["sku"]), (14.99, "GV31"))
        p = S.parse_product(label_hidden(html), GV_PRODUCT)                 # also with the labels hidden
        self.assertEqual((p["price"], p["sku"]), (14.99, "GV31"))

    def test_type_description_is_the_first_feature(self):
        p = S.parse_product(fx("gv_complete_product.html"), f"{GV}/store/grapevine-complete-subscription-1-year")
        self.assertTrue(S.short_description(p).startswith("Combines the Grapevine print magazine"))


class Subscriptions(unittest.TestCase):
    def test_region_links_from_the_category_pages(self):
        self.assertEqual(S.parse_categories(fx("gv_subscriptions.html"), f"{GV}/store/grapevine-subscriptions"), {
            "us": f"{GV}/store/us-subscriptions", "ca": f"{GV}/store/canada-subscriptions",
            "intl": f"{GV}/store/international-subscriptions"})
        self.assertEqual(S.parse_categories(fx("lv_subscriptions.html"), f"{LV}/tienda/suscripciones"), {
            "us": f"{LV}/US-suscripciones", "ca": f"{LV}/tienda/canada-suscripciones",
            "intl": f"{LV}/tienda/internacional-suscripciones"})

    def test_grapevine_us_listing(self):
        plans, nxt = S.parse_listing(fx("gv_us_listing.html"), f"{GV}/store/us-subscriptions")
        self.assertIsNone(nxt)
        self.assertEqual(len(plans), 11)
        first = plans[0]
        self.assertEqual((first["type"], first["term_months"], first["price"], first["sku"]), ("print", 12, 36.0, "GVUS1"))
        self.assertEqual(first["volume"], [{"min": 2, "max": 19, "price": 35.5}, {"min": 20, "max": 39, "price": 35.0},
                                           {"min": 40, "max": None, "price": 34.0}])
        self.assertEqual(first["url"], f"{GV}/store/grapevine-print-subscriptions-1-year")
        self.assertEqual({p["type"] for p in plans}, {"print", "digital", "complete"})
        self.assertEqual(sorted({p["term_months"] for p in plans}), [1, 12, 24, 36])

    def test_prices_and_skus_are_read_with_their_labels_hidden(self):
        url = f"{GV}/store/us-subscriptions"
        shown, _ = S.parse_listing(fx("gv_us_listing.html"), url)
        hidden, _ = S.parse_listing(label_hidden(fx("gv_us_listing.html")), url)
        self.assertEqual([(p["price"], p["sku"]) for p in hidden], [(p["price"], p["sku"]) for p in shown])
        self.assertEqual((hidden[0]["price"], hidden[0]["sku"]), (36.0, "GVUS1"))

    def test_la_vina_us_listing_spanish_titles(self):
        plans, _ = S.parse_listing(fx("lv_us_listing.html"), f"{LV}/US-suscripciones")
        by_sku = {p["sku"]: p for p in plans}
        self.assertEqual((by_sku["LVUS1"]["type"], by_sku["LVUS1"]["term_months"]), ("print", 12))
        self.assertEqual((by_sku["LVV1M"]["type"], by_sku["LVV1M"]["term_months"]), ("complete", 1))
        self.assertEqual((by_sku["LO3A"]["type"], by_sku["LO3A"]["term_months"]), ("digital", 36))

    def test_type_and_term_words(self):
        self.assertEqual(S.plan_type("Suscripción revista impresa de La Viña: 2 años"), "print")
        self.assertEqual(S.plan_type("Grapevine Complete Subscription: 1-Month"), "complete")
        self.assertEqual(S.plan_type("Gift Certificate"), "other")
        self.assertEqual(S.term_months("Grapevine Print Subscriptions: 2-Years"), 24)
        self.assertEqual(S.term_months("Suscripción completa a La Viña: 1 mes"), 1)
        self.assertIsNone(S.term_months("Gift Certificate"))


class Collect(unittest.TestCase):
    def test_a_run_with_some_pages_missing_keeps_the_previous_plans(self):
        prev_ca = {"id": "sub:gv:ca:GVCAN1", "kind": "subscription", "title": "Canada: Grapevine Print Subscription: 1-Year",
                   "url": f"{GV}/store/x", "extra": {"pub": "gv", "region": "ca", "type": "print", "price": 36.0}}
        res = S.collect(fixture_fetch, lambda url: None, {"items": [prev_ca]}, TODAY, cfg={}, refresh_types=True)
        ids = {i["id"] for i in res["items"]}
        self.assertIn("botm:gv", ids)
        self.assertIn("botm:lv", ids)
        botm = next(i for i in res["items"] if i["id"] == "botm:gv")
        self.assertEqual((botm["extra"]["price"], botm["extra"]["sale_price"], botm["extra"]["sku"]), (14.99, 11.99, "GV31"))
        self.assertIn("sub:gv:us:GVUS1", ids)
        self.assertIn("sub:lv:us:LVUS1", ids)
        self.assertIn("sub:gv:ca:GVCAN1", ids, "the region that could not be read keeps its previous plans")
        self.assertTrue(any("region(s) ca, intl" in e for e in res["errors"]))
        self.assertEqual(res["bulk_discounts"]["tiers"][1], {"min": 5, "max": 9, "off": 0.5})
        self.assertEqual(set(res["bulk_discounts"]["note"]), {"en", "es"})
        self.assertIn("complete", res["types"]["gv"])

    def test_cards_without_a_readable_price_keep_the_previous_plans(self):
        prev_us = {"id": "sub:gv:us:GVUS1", "kind": "subscription", "title": "Grapevine Print Subscriptions: 1-Year",
                   "url": f"{GV}/store/grapevine-print-subscriptions-1-year",
                   "extra": {"pub": "gv", "region": "us", "type": "print", "term_months": 12, "price": 36.0, "sku": "GVUS1"}}
        prev = {"items": [prev_us], "types_checked": NOW, "specialty_checked": NOW}
        # the store renames the price field: every card is still there, no price can be read
        renamed = listing_fetch(lambda html: html.replace("field--name-price", "field--name-variation-price"))
        res = S.collect(renamed, lambda url: None, prev, TODAY, cfg={})
        subs = [i for i in res["items"] if i["kind"] == "subscription"]
        self.assertEqual([(i["id"], i["extra"].get("price")) for i in subs], [("sub:gv:us:GVUS1", 36.0)],
                         "never plans without prices: the region keeps its previous plans")
        self.assertTrue(any(e.startswith("gv subscriptions:") and "region(s) us, ca, intl" in e for e in res["errors"]),
                        "… and the run is reported (ok=false), not saved as a success")
        # the same prices with the labels hidden: all read, under the same SKU ids
        hidden = S.collect(listing_fetch(label_hidden), lambda url: None, prev, TODAY, cfg={})
        normal = S.collect(fixture_fetch, lambda url: None, prev, TODAY, cfg={})

        def plans(r):
            return {i["id"]: i["extra"].get("price") for i in r["items"] if i["id"].startswith("sub:gv:us:")}
        self.assertEqual(plans(hidden), plans(normal))
        self.assertEqual(len(plans(hidden)), 11)
        self.assertEqual(plans(hidden)["sub:gv:us:GVUS1"], 36.0)
        self.assertFalse([e for e in hidden["errors"] if "region(s) us" in e])

    def test_nothing_reachable_keeps_everything(self):
        prev = {"items": [{"id": "botm:gv", "kind": "botm", "title": "Old", "url": GV_PRODUCT, "extra": {}},
                          {"id": "sub:lv:us:LVUS1", "kind": "subscription", "title": "T", "url": f"{LV}/x",
                           "extra": {"pub": "lv", "region": "us"}}],
                "bulk_discounts": {"source_url": GV_PRODUCT, "tiers": [{"min": 1, "max": None, "off": 0}]},
                "types_checked": NOW, "specialty_checked": NOW}
        res = S.collect(lambda url: None, lambda url: None, prev, TODAY, cfg={})
        self.assertEqual({i["id"] for i in res["items"]}, {"botm:gv", "sub:lv:us:LVUS1"})
        self.assertEqual(len(res["errors"]), 4)
        self.assertEqual(res["bulk_discounts"]["source_url"], GV_PRODUCT)


class SpecialtyItems(unittest.TestCase):
    def test_grapevine_product_pages(self):
        cards = S.parse_specialty(fx("gv_greeting_cards.html"), f"{GV}/store/greeting-cards")
        self.assertEqual(len(cards), 1)
        c = cards[0]
        self.assertEqual((c["title"], c["kind"], c["price"], c["currency"], c["sku"]), ("Greeting cards", "cards", 36.0, "USD", "GVGC01"))
        self.assertEqual(c["url"], f"{GV}/store/greeting-cards")
        self.assertIn("/styles/product_feature_image/", c["image_src"])
        self.assertTrue(c["text"].startswith("Each card is beautifully illustrated"))
        self.assertLessEqual(len(c["text"]), 230)
        self.assertEqual((c["pack"], c["volume"]), (24, [{"min": 5, "max": None, "price": 34.8}]))
        self.assertFalse(c["trilingual"])
        planner = S.parse_specialty(fx("gv_pocket_planner.html"), f"{GV}/store/annual-pocket-planner")[0]
        self.assertEqual((planner["title"], planner["kind"], planner["price"], planner["sku"]), ("Annual Pocket Planner", "planner", 6.0, "MS09"))
        self.assertIn("month-at-a-glance", planner["text"], "the store's typing slip is evened out")
        self.assertTrue(planner["trilingual"])
        cal = S.parse_specialty(fx("gv_wall_calendar.html"), f"{GV}/store/annual-wall-calendar")[0]
        self.assertEqual((cal["kind"], cal["price"], cal["sku"], cal["trilingual"]), ("calendar", 10.5, "MS08", True))
        self.assertTrue(cal["text"].startswith("Full of beautiful color photographs"))

    def test_la_vina_listing_keeps_only_the_three_kinds(self):
        got = S.parse_specialty(fx("lv_articulos_especiales.html"), f"{LV}/tienda/articulos-especiales")
        self.assertEqual([(g["kind"], g["sku"], g["price"]) for g in got],
                         [("cards", "LVGC01", 36.0), ("planner", "MS09LV", 6.0), ("calendar", "MS08LV", 10.5)])
        self.assertEqual(got[0]["title"], "Tarjetas de Ocasión")
        self.assertEqual(got[1]["url"], f"{LV}/tienda/agenda-de-bolsillo")
        self.assertEqual(got[1]["volume"], [{"min": 10, "max": None, "price": 5.5}])
        self.assertTrue(all(g["image_src"].startswith(f"{LV}/sites/default/files/") for g in got))

    def test_kinds(self):
        self.assertEqual(S.specialty_kind("Agenda de Bolsillo"), "planner")
        self.assertIsNone(S.specialty_kind("Agenda de grupo La Viña", f"{LV}/agenda-de-grupo"))
        self.assertIsNone(S.specialty_kind("Paquetes de 30 Números Anteriores"))
        self.assertEqual(S.specialty_kind("Calendario Anual de Pared"), "calendar")
        self.assertEqual(S.specialty_kind("Tarjetas de Ocasión"), "cards")

    def test_a_page_without_products_is_an_error(self):
        with self.assertRaises(S.ShopParseError):
            S.parse_specialty("<html><body><main><div id='block-neatosub-content'><p>Soon</p></div></main></body></html>",
                              f"{GV}/store/greeting-cards")

    def test_collect_reads_them_weekly_and_keeps_old_items_on_failure(self):
        old = {"id": "special:gv:MS08", "kind": "specialty", "title": "Annual Wall Calendar", "url": f"{GV}/store/annual-wall-calendar",
               "image": "/assets/cache/shop/old.webp",
               "extra": {"pub": "gv", "type": "calendar", "price": 9.5, "page_url": f"{GV}/store/annual-wall-calendar"}}
        base = {"types_checked": NOW}

        def fetch(url):   # the wall calendar page is down today
            return None if url.endswith("annual-wall-calendar") else fixture_fetch(url)
        res = S.collect(fetch, lambda url: None, {**base, "items": [old]}, TODAY, cfg={})
        sp = specialty(res)
        self.assertEqual(set(sp), SPECIAL_IDS)
        self.assertEqual(sp["special:gv:MS08"]["extra"]["price"], 9.5, "the page that failed keeps its previous item")
        self.assertEqual(sp["special:gv:GVGC01"]["extra"]["pack"], 24)
        self.assertEqual(sp["special:lv:MS09LV"]["extra"]["page_url"], f"{LV}/tienda/articulos-especiales")
        self.assertTrue(any("specialty" in e for e in res["errors"]))
        self.assertIsNone(res["specialty_checked"], "not stamped while a page failed: the next run tries again")
        # All pages read → stamped; within the week nothing is fetched and the items are kept as they are.
        res2 = S.collect(fixture_fetch, lambda url: None, {**base, "items": []}, TODAY, cfg={})
        self.assertFalse([e for e in res2["errors"] if "specialty" in e])
        self.assertTrue(res2["specialty_checked"])
        asked = []

        def spy(url):
            asked.append(url)
            return fixture_fetch(url)
        res3 = S.collect(spy, lambda url: "/assets/cache/shop/new.webp",
                         {**base, "items": [{**old, "image": None, "extra": {**old["extra"], "image_src": f"{GV}/x.png"}}],
                          "specialty_checked": NOW}, TODAY, cfg={})
        self.assertFalse([u for u in asked if "greeting" in u or "planner" in u or "articulos" in u])
        kept = next(i for i in res3["items"] if i["id"] == "special:gv:MS08")
        self.assertEqual(kept["image"], "/assets/cache/shop/new.webp", "a missing picture is tried again in between")
        self.assertEqual(res3["specialty_checked"], NOW)


class HolidayCards(unittest.TestCase):
    """The fourth specialty kind: the holiday cards, a pack of 12 that both stores sell in season only."""

    def test_both_stores_product_pages(self):
        got = S.parse_specialty(fx("gv_holiday_cards.html"), GV_HOLIDAY)
        self.assertEqual(len(got), 1)
        gv = got[0]
        self.assertEqual((gv["title"], gv["kind"], gv["price"], gv["currency"], gv["sku"], gv["pack"], gv["listed"]),
                         ("Holiday Greeting Cards - 12 pack", "holiday", 22.0, "USD", "GVGCH1", 12, False))
        self.assertEqual(gv["url"], GV_HOLIDAY)
        self.assertEqual(gv["volume"], [{"min": 5, "max": None, "price": 20.0}])
        self.assertIn("/styles/product_feature_image/", gv["image_src"])
        self.assertFalse(gv["trilingual"])
        self.assertEqual(gv["text"], "Two different cartoons illustrated by AA members! Each card is beautifully "
                                     "illustrated with a cartoon about humorous moments in sobriety.",
                         "a first paragraph shorter than the minimum goes on with the next one")
        lv = S.parse_specialty(fx("lv_holiday_cards.html"), LV_HOLIDAY)[0]
        self.assertEqual((lv["title"], lv["kind"], lv["price"], lv["currency"], lv["sku"], lv["pack"]),
                         ("¡Tarjetas de ocasión para las fiestas! Paquete de 12", "holiday", 22.0, "USD", "LVGCH1", 12))
        self.assertEqual(lv["volume"], [{"min": 5, "max": None, "price": 20.0}])
        self.assertTrue(lv["text"].startswith("¡Dos diseños diferentes, ilustrados por miembros de AA! Cada tarjeta"))
        for text in (gv["text"], lv["text"]):
            self.assertNotIn("$", text, "a sentence with a price is never part of a description")
        self.assertNotIn("Ordena en línea", lv["text"], "a short call to action is not a description")

    def test_kinds_and_pack_sizes(self):
        for title in ("Holiday Greeting Cards - 12 pack", "¡Tarjetas de ocasión para las fiestas! Paquete de 12",
                      "Christmas cards", "Tarjetas de Navidad"):
            self.assertEqual(S.specialty_kind(title), "holiday", title)
        self.assertEqual(S.specialty_kind("Greeting cards"), "cards", "the year-round cards stay their own kind")
        self.assertEqual(S.specialty_kind("Tarjetas de Ocasión", f"{LV}/tarjetas-de-ocasion"), "cards")
        self.assertIsNone(S.specialty_kind("Fiesta de aniversario"), "a holiday word alone is not a card")
        self.assertEqual(S.specialty_kind("", GV_HOLIDAY), "holiday", "the page address alone says it")
        for text, n in (("Holiday Greeting Cards - 12 pack", 12), ("Paquete de 12", 12),
                        ("Comes with four different cards in a box of 24 for $36 (USD).", 24),
                        ("Cada caja contiene 12 tarjetas, con dos diseños diferentes", 12),
                        ("Traditions Checklist (pack of 50)", 50), ("Annual Wall Calendar", None)):
            self.assertEqual(S.pack_size(text), n, text)

    def test_listings_in_season_give_the_first_card_of_each_kind(self):
        gv = S.parse_specialty(fx("gv_specialty_items.html"), GV_SPECIALTY)
        self.assertEqual([(g["kind"], g["sku"]) for g in gv],
                         [("holiday", "GVGCH1"), ("cards", "GVGC01"), ("planner", "MS09"), ("calendar", "MS08")],
                         "in the listing's order; the Preamble, the checklist … are not specialty kinds")
        self.assertTrue(all(g["listed"] for g in gv))
        self.assertEqual((gv[0]["url"], gv[0]["pack"]), (GV_HOLIDAY, 12))
        lv = S.parse_specialty(fx("lv_articulos_especiales_holidays.html"), LV_SPECIALTY)
        self.assertEqual([(g["kind"], g["sku"]) for g in lv],
                         [("holiday", "LVGCH1"), ("cards", "LVGC01"), ("planner", "MS09LV"), ("calendar", "MS08LV")])
        self.assertEqual((lv[0]["url"], lv[0]["pack"]), (LV_HOLIDAY, 12))

    def test_in_season_each_store_has_four_kinds_and_the_holiday_cards_once(self):
        res = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": []}, TODAY, cfg={})
        sp = specialty(res)
        self.assertEqual(set(sp), SPECIAL_IDS)
        self.assertFalse([e for e in res["errors"] if "specialty" in e])
        self.assertTrue(res["specialty_checked"])
        gv, lv = sp["special:gv:GVGCH1"], sp["special:lv:LVGCH1"]
        self.assertEqual((gv["extra"]["type"], gv["extra"]["pack"], gv["extra"]["price"]), ("holiday", 12, 22.0))
        self.assertEqual(lv["extra"]["page_url"], LV_HOLIDAY,
                         "read from its own page (La Viña's description), never a second time from the listing")
        self.assertTrue(lv["summary"].startswith("¡Dos diseños"))
        self.assertEqual(sp["special:lv:MS09LV"]["extra"]["page_url"], LV_SPECIALTY, "the listing still gives the other three")
        self.assertEqual(sp["special:gv:GVGC01"]["extra"]["page_url"], f"{GV}/store/greeting-cards",
                         "Grapevine's listing adds nothing a product page already gave")
        self.assertFalse([i for i in sp.values() if "missing_since" in i["extra"]])
        self.assertNotIn("specialty_out_of_season", res["stats"])

    def test_out_of_season_the_last_good_cards_are_kept_without_an_error(self):
        first = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": []}, TODAY, cfg={})
        res = S.collect(out_of_season, lambda url: None, {"types_checked": NOW, "items": first["items"]},
                        date(2027, 1, 12), cfg={})
        sp = specialty(res)
        self.assertEqual(set(sp), SPECIAL_IDS, "one missing kind never takes the other three with it")
        self.assertFalse([e for e in res["errors"] if "specialty" in e], "a store that takes its holiday cards down is not failing")
        self.assertTrue(res["specialty_checked"], "…so the week's read counts as done (no daily retries all winter)")
        for sid in ("special:gv:GVGCH1", "special:lv:LVGCH1"):
            ex = sp[sid]["extra"]
            self.assertEqual((ex["missing_since"], ex["price"], ex["pack"]), ("2027-01-12", 22.0, 12), "kept as last read, marked")
        self.assertEqual(sorted(res["stats"]["specialty_out_of_season"]), ["special:gv:GVGCH1", "special:lv:LVGCH1"])
        self.assertFalse([i for i in sp.values() if i["extra"]["type"] != "holiday" and "missing_since" in i["extra"]])
        # The next day (no weekly read): the items keep their mark, and so do the run's stats (save_raw rewrites
        # them every run).
        between = S.collect(out_of_season, lambda url: None, {"types_checked": NOW, "items": res["items"],
                                                              "specialty_checked": res["specialty_checked"]},
                            date(2027, 1, 13), cfg={})
        self.assertFalse(between["stats"]["specialty_refreshed"])
        self.assertEqual(sorted(between["stats"]["specialty_out_of_season"]), ["special:gv:GVGCH1", "special:lv:LVGCH1"])
        # A week later: still marked from the first day it was missed (build_data counts its grace from there).
        res2 = S.collect(out_of_season, lambda url: None, {"types_checked": NOW, "items": res["items"]},
                         date(2027, 1, 19), cfg={})
        self.assertEqual(specialty(res2)["special:gv:GVGCH1"]["extra"]["missing_since"], "2027-01-12")
        # Next season the store shows them again: read fresh, the mark is gone (also after main()'s merge).
        res3 = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": res2["items"]},
                         date(2027, 9, 20), cfg={})
        merged, _ = merge_items(res2["items"], res3["items"], drop_missing=True, authoritative=True)
        back = {i["id"]: i for i in merged}
        for sid in ("special:gv:GVGCH1", "special:lv:LVGCH1"):
            self.assertNotIn("missing_since", back[sid]["extra"])
        # The first run ever, out of season: no holiday cards and no error.
        res4 = S.collect(out_of_season, lambda url: None, {"types_checked": NOW, "items": []}, date(2027, 1, 12), cfg={})
        self.assertEqual(set(specialty(res4)), SPECIAL_IDS - {"special:gv:GVGCH1", "special:lv:LVGCH1"})
        self.assertFalse([e for e in res4["errors"] if "specialty" in e])

    def test_a_holiday_page_that_moved_is_found_on_the_listing(self):
        moved = f"{GV}/store/holiday-greeting-cards-2027"

        def fetch(url):                   # next season the store gives the cards a new address
            if url == GV_HOLIDAY:
                return None
            html = fixture_fetch(url)
            return html.replace(GV_HOLIDAY, moved) if html and url == GV_SPECIALTY else html
        first = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": []}, TODAY, cfg={})
        res = S.collect(fetch, lambda url: None, {"types_checked": NOW, "items": first["items"]}, TODAY, cfg={})
        gv = [i for i in specialty(res).values() if i["id"].startswith("special:gv:") and i["extra"]["type"] == "holiday"]
        self.assertEqual(len(gv), 1)
        self.assertEqual((gv[0]["url"], gv[0]["extra"]["page_url"]), (moved, GV_SPECIALTY))
        self.assertNotIn("missing_since", gv[0]["extra"])
        self.assertFalse([e for e in res["errors"] if "specialty" in e])

    def test_a_holiday_page_that_is_broken_in_season_is_an_error_not_out_of_season(self):
        """Out of season means GONE: not fetched at all, and no listing shows the cards at that address. A page
        that answers in a layout we no longer read, or is down while La Viña's listing still sells the cards
        there, is reported (ok=false, read again tomorrow) and its item kept as it was — never marked, so
        build_data cannot drop the card mid-season without anyone hearing of it."""
        new_layout = ("<html><body><main><div id='block-neatosub-content'><h1>¡Tarjetas de ocasión para las fiestas! "
                      "Paquete de 12</h1><div class='product-v2'><span>$22.00</span></div></div></main></body></html>")
        first = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": []}, TODAY, cfg={})
        for why, answer in (("a 200 page not understood", new_layout), ("down (5xx, timeout …)", None)):
            def fetch(url, answer=answer):
                return answer if url == LV_HOLIDAY else fixture_fetch(url)
            self.assertTrue([p for p in S.parse_specialty(fetch(LV_SPECIALTY), LV_SPECIALTY) if p["kind"] == "holiday"],
                            "the listing still shows the cards at the configured address")
            res = S.collect(fetch, lambda url: None, {"types_checked": NOW, "items": first["items"]},
                            date(2026, 11, 2), cfg={})
            self.assertTrue([e for e in res["errors"] if e.startswith("lv specialty:")], why)
            self.assertIsNone(res["specialty_checked"], why)
            lv = specialty(res)["special:lv:LVGCH1"]
            self.assertEqual(lv["extra"]["page_url"], LV_HOLIDAY, why)
            self.assertNotIn("missing_since", lv["extra"], why)
            self.assertNotIn("specialty_out_of_season", res["stats"], why)
        # Out of season too: a page that answers but is not understood is never taken for "gone".
        def broken(url):
            return new_layout if url == LV_HOLIDAY else out_of_season(url)
        res = S.collect(broken, lambda url: None, {"types_checked": NOW, "items": first["items"]}, date(2027, 1, 12), cfg={})
        self.assertTrue([e for e in res["errors"] if e.startswith("lv specialty:")])
        self.assertNotIn("missing_since", specialty(res)["special:lv:LVGCH1"]["extra"])
        self.assertEqual(specialty(res)["special:gv:GVGCH1"]["extra"]["missing_since"], "2027-01-12",
                         "Grapevine's page is really gone: out of season, as before")

    def test_specialty_skip_hides_a_kind_of_one_store(self):
        """Deleting a product page's line only moves that item to the listing, so `specialty_skip` is the off
        switch: the kind is never added, from any page, and its previous item is dropped."""
        cfg = {"sources": {"lavina": {"specialty_skip": ["holiday"]}, "grapevine": {"specialty_skip": ["Calendar", "posters"]}}}
        with self.assertLogs(S.log, "WARNING") as logs:
            st = S.settings(cfg)
        self.assertEqual((st["lv"]["specialty_skip"], st["gv"]["specialty_skip"]), (["holiday"], ["calendar"]))
        self.assertTrue(any("posters" in m for m in logs.output), "a word that is not a kind is named in the log")
        first = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": []}, TODAY, cfg={})
        res = S.collect(fixture_fetch, lambda url: None, {"types_checked": NOW, "items": first["items"]}, TODAY, cfg=cfg)
        self.assertEqual(set(specialty(res)), SPECIAL_IDS - {"special:lv:LVGCH1", "special:gv:MS08"},
                         "not from the product page, not from the listing, not kept from the last read")
        self.assertFalse([e for e in res["errors"] if "specialty" in e])
        # A skipped kind's page failing is no error either (it would not be shown anyway).
        res2 = S.collect(lambda url: None if url == LV_HOLIDAY else fixture_fetch(url), lambda url: None,
                         {"types_checked": NOW, "items": first["items"]}, TODAY, cfg=cfg)
        self.assertFalse([e for e in res2["errors"] if "specialty" in e])
        self.assertNotIn("special:lv:LVGCH1", specialty(res2))

    def test_a_failing_listing_is_still_an_error(self):
        def fetch(url):                   # Grapevine's listing is down: not seasonal, reported (and read again tomorrow)
            return None if url == GV_SPECIALTY else fixture_fetch(url)
        res = S.collect(fetch, lambda url: None, {"types_checked": NOW, "items": []}, TODAY, cfg={})
        self.assertTrue([e for e in res["errors"] if "specialty" in e])
        self.assertIsNone(res["specialty_checked"])
        self.assertEqual(set(specialty(res)), SPECIAL_IDS, "…and the four kinds are all there anyway")


class SiteShopJson(unittest.TestCase):
    def _ctx(self, items, **env):
        ctx = B.Ctx(offline=True)
        ctx.raw = {"shop": {"items": items, "updated": "2026-09-24T12:00:00Z", **env}}
        return ctx

    def _item(self, pub, ends, lang):
        return {"id": f"botm:{pub}", "kind": "botm", "title": f"Book {pub}", "summary": "About it.", "lang": lang,
                "url": f"{GV}/store/{pub}", "image": "/assets/cache/shop/x.webp",
                "extra": {"pub": pub, "page_url": f"{GV}/BOTM", "price": 14.99, "sale_price": 11.99, "discount_pct": 20,
                          "sku": "GV31", "starts": "2026-09-15", "ends": ends, "month": 10, "month_label": "October"}}

    def test_contract_order_expiry_and_labels(self):
        today = B.Ctx(offline=True).today_local
        past = date.fromordinal(today.toordinal() - 1).isoformat()
        future = date.fromordinal(today.toordinal() + 10).isoformat()
        plans = [{"id": f"sub:{pub}:{reg}:{sku}", "kind": "subscription", "title": sku, "url": f"{GV}/store/{sku}",
                  "extra": {"pub": pub, "region": reg, "type": "print", "term_months": 12, "price": 36, "sku": sku,
                            "position": pos, "volume": [{"min": 2, "max": None, "price": 35.5}]}}
                 for pub, reg, sku, pos in (("lv", "us", "LVUS1", 0), ("gv", "ca", "GVCAN1", 0), ("gv", "us", "GVUS2", 1),
                                            ("gv", "us", "GVUS1", 0))]
        ctx = self._ctx([self._item("gv", future, "en"), self._item("lv", past, "es"), *plans],
                        types={"gv": {"print": {"text": "Enjoy 12 issues.", "lang": "en"}}},
                        bulk_discounts={"source_url": GV_PRODUCT, "tiers": [{"min": 1, "max": 4, "off": 0}],
                                        "note": {"en": "Books only."}})
        i18n = B.I18n(None)
        doc, wanted = B.build_shop(ctx, i18n)
        B.finish_shop(doc, wanted, i18n)
        self.assertEqual([b["id"] for b in doc["botm"]], ["botm:gv"], "an offer past its end date is left out")
        b = doc["botm"][0]
        for key in ("id", "pub", "lang", "title", "url", "page_url", "image", "price", "sale_price", "discount_pct",
                    "currency", "sku", "starts", "ends", "month_label", "blurb", "i18n", "machine"):
            self.assertIn(key, b)
        self.assertEqual(b["i18n"]["month_label"], {"en": "October", "es": "Octubre"})
        self.assertEqual(b["i18n"]["title"], {"en": "Book gv", "es": "Book gv"})     # no model → original kept
        self.assertEqual([(s["pub"], s["region"]) for s in doc["subscriptions"]], [("gv", "us"), ("gv", "ca"), ("lv", "us")])
        self.assertEqual([p["sku"] for p in doc["subscriptions"][0]["plans"]], ["GVUS1", "GVUS2"])
        self.assertEqual(doc["subscriptions"][0]["plans"][0]["volume"], [{"min": 2, "max": None, "price": 35.5}])
        self.assertEqual(doc["types"]["gv"]["print"], {"en": "Enjoy 12 issues.", "es": "Enjoy 12 issues."})
        self.assertEqual(set(doc["bulk_discounts"]["note"]), {"en", "es"})
        self.assertEqual(B.shop_count(doc), 1 + 4)

    def test_specialty_rows(self):
        items = [{"id": "special:lv:MS08LV", "kind": "specialty", "title": "Calendario Anual de Pared", "lang": "es",
                  "url": f"{LV}/tienda/calendario-anual-de-pared", "image": "/assets/cache/shop/c.webp",
                  "extra": {"pub": "lv", "type": "calendar", "price": 10.5, "sku": "MS08LV", "position": 0,
                            "volume": [{"min": 5, "max": None, "price": 10.0}], "page_url": f"{LV}/tienda/articulos-especiales"}},
                 {"id": "special:gv:MS08", "kind": "specialty", "title": "Annual Wall Calendar", "lang": "en",
                  "summary": "Full of beautiful color photographs.", "url": f"{GV}/store/annual-wall-calendar",
                  "extra": {"pub": "gv", "type": "calendar", "price": 10.5, "sku": "MS08", "trilingual": True, "position": 2}},
                 {"id": "special:gv:X", "kind": "specialty", "title": "No price", "url": f"{GV}/store/x", "extra": {"pub": "gv"}}]
        i18n = B.I18n(None)
        doc, wanted = B.build_shop(self._ctx(items), i18n)
        B.finish_shop(doc, wanted, i18n)
        self.assertEqual([r["id"] for r in doc["specialty"]], ["special:gv:MS08", "special:lv:MS08LV"], "Grapevine first; no price: left out")
        gv, lv = doc["specialty"]
        for key in ("id", "pub", "lang", "type", "title", "url", "image", "price", "currency", "sku", "volume",
                    "trilingual", "pack", "text", "page_url"):
            self.assertIn(key, gv)
        self.assertEqual((gv["type"], gv["trilingual"], gv["image"]), ("calendar", True, None))
        self.assertEqual(gv["text"], "Full of beautiful color photographs.")
        self.assertNotIn("Full of beautiful color photographs.", [w[2] for w in wanted], "never machine-translated")
        self.assertEqual((lv["lang"], lv["text"], lv["volume"]), ("es", "", [{"min": 5, "max": None, "price": 10.0}]))
        self.assertEqual(B.shop_count(doc), 2)

    def test_holiday_cards_out_of_season_leave_the_site_after_the_grace(self):
        today = B.Ctx(offline=True).today_local

        def holiday(pub, sku, missing_days):
            ex = {"pub": pub, "type": "holiday", "price": 22.0, "sku": sku, "pack": 12, "position": 3,
                  "page_url": GV_HOLIDAY if pub == "gv" else LV_HOLIDAY}
            if missing_days is not None:
                ex["missing_since"] = (today - timedelta(days=missing_days)).isoformat()
            return {"id": f"special:{pub}:{sku}", "kind": "specialty", "title": "Holiday Greeting Cards - 12 pack",
                    "lang": "en" if pub == "gv" else "es", "url": ex["page_url"], "extra": ex}
        items = [holiday("gv", "IN", None), holiday("gv", "LAST", B.SHOP_SEASONAL_GRACE_DAYS),
                 holiday("lv", "GONE", B.SHOP_SEASONAL_GRACE_DAYS + 1)]
        doc, _ = B.build_shop(self._ctx(items), B.I18n(None))
        self.assertEqual([r["id"] for r in doc["specialty"]], ["special:gv:IN", "special:gv:LAST"],
                         "a store page down for a few days keeps the card; gone past the grace: left out")
        row = doc["specialty"][0]
        self.assertEqual((row["type"], row["pack"], row["price"]), ("holiday", 12, 22.0))
        self.assertNotIn("missing_since", row, "not part of the site contract")

    def test_no_raw_file_gives_an_empty_document(self):
        ctx = self._ctx([])
        doc, wanted = B.build_shop(ctx, B.I18n(None))
        self.assertEqual((doc["botm"], doc["subscriptions"], doc["types"], doc["specialty"]), ([], [], {}, []))
        self.assertEqual(doc["bulk_discounts"]["tiers"], [])


class SpecialtyView(unittest.TestCase):
    """eleventy/filters/shop.js shopSpecialty — the /shop/#specialty cards and the hero teaser."""
    SHOP = {"specialty": [
        {"id": "special:gv:GVGC01", "pub": "gv", "lang": "en", "type": "cards", "title": "Greeting cards", "url": f"{GV}/store/greeting-cards",
         "image": "/assets/cache/shop/a.webp", "price": 36.0, "currency": "USD", "sku": "GVGC01", "pack": 24, "trilingual": False,
         "volume": [{"min": 5, "max": None, "price": 34.8}], "text": "Each card is beautifully illustrated."},
        {"id": "special:gv:MS08", "pub": "gv", "lang": "en", "type": "calendar", "title": "Annual Wall Calendar", "url": f"{GV}/store/annual-wall-calendar",
         "image": "/assets/cache/shop/c.webp", "price": 10.5, "currency": "USD", "sku": "MS08", "trilingual": True, "volume": [], "text": "Full of photographs."},
        {"id": "special:lv:LVGC01", "pub": "lv", "lang": "es", "type": "cards", "title": "Tarjetas de Ocasión", "url": f"{LV}/tarjetas-de-ocasion",
         "image": None, "price": 36.0, "currency": "USD", "sku": "LVGC01", "volume": [], "text": ""},
        {"id": "special:lv:MS08LV", "pub": "lv", "lang": "es", "type": "calendar", "title": "Calendario Anual de Pared", "url": f"{LV}/tienda/calendario-anual-de-pared",
         "image": None, "price": 10.5, "currency": "USD", "sku": "MS08LV", "volume": [{"min": 5, "max": None, "price": 10.0}], "text": ""},
        {"id": "special:lv:X", "pub": "lv", "lang": "es", "type": "other", "title": "Otro", "url": f"{LV}/x", "price": 5.0},
    ]}

    # In season (October 1, 2026): both stores' holiday cards — different products (GVGCH1 / LVGCH1), as the
    # greeting cards are.
    HOLIDAY = [
        {"id": "special:gv:GVGCH1", "pub": "gv", "lang": "en", "type": "holiday", "title": "Holiday Greeting Cards - 12 pack",
         "url": GV_HOLIDAY, "image": "/assets/cache/shop/h.webp", "price": 22.0, "currency": "USD", "sku": "GVGCH1", "pack": 12,
         "trilingual": False, "volume": [{"min": 5, "max": None, "price": 20.0}], "text": "Two different cartoons illustrated by AA members!"},
        {"id": "special:lv:LVGCH1", "pub": "lv", "lang": "es", "type": "holiday", "title": "¡Tarjetas de ocasión para las fiestas! Paquete de 12",
         "url": LV_HOLIDAY, "image": "/assets/cache/shop/f.webp", "price": 22.0, "currency": "USD", "sku": "LVGCH1", "pack": 12,
         "trilingual": False, "volume": [{"min": 5, "max": None, "price": 20.0}], "text": "¡Dos diseños diferentes, ilustrados por miembros de AA!"},
    ]

    def views(self, lang, shop=None):
        return run_js(self, "out(filters.shopSpecialty(input.shop, input.lang))", data={"shop": shop or self.SHOP, "lang": lang})

    def test_holiday_cards_come_fourth_paired_with_the_other_store(self):
        shop = {"specialty": self.SHOP["specialty"] + self.HOLIDAY}
        en = self.views("en", shop)
        self.assertEqual([x["type"] for x in en], ["cards", "calendar", "holiday"], "last: out of season the others keep their places")
        h = en[-1]
        self.assertEqual((h["pub"], h["title"], h["pack"], h["seasonal"], h["anchor"], h["price"], h["volume"]),
                         ("gv", "Holiday Greeting Cards", "Pack of 12", True, "special-holiday", "$22.00", "5 or more: $20.00 each"))
        self.assertEqual((h["also"]["title"], h["also"]["mag"], h["also"]["url"]), ("¡Tarjetas de ocasión para las fiestas!", "La Viña", LV_HOLIDAY),
                         "the pack size is the badge, not part of the title")
        self.assertFalse(h["also"]["same"], "different cards: a La Viña edition link, as for the greeting cards")
        self.assertEqual(en[0]["pack"], "Box of 24", "the greeting cards still come by the box")
        self.assertFalse(en[0]["seasonal"])
        es = self.views("es", shop)
        h = es[-1]
        self.assertEqual((h["pub"], h["title"], h["pack"], h["store"], h["volume"]),
                         ("lv", "¡Tarjetas de ocasión para las fiestas!", "Paquete de 12", "aalavina.org", "5 o más: $20.00 c/u"))
        self.assertEqual((h["text"], h["textLang"]), ("¡Dos diseños diferentes, ilustrados por miembros de AA!", "es"))
        self.assertEqual((h["also"]["title"], h["also"]["titleLang"]), ("Holiday Greeting Cards", "en"))

    def test_a_kind_only_the_other_store_sells_is_named_in_the_page_language(self):
        es = self.views("es", {"specialty": self.SHOP["specialty"] + self.HOLIDAY[:1]})   # only Grapevine's this week
        h = es[-1]
        self.assertEqual((h["pub"], h["titleLang"], h["typeName"], h["also"]), ("gv", "en", "Tarjetas para las fiestas", None))
        self.assertTrue(h["text"].startswith("Tarjetas para la temporada de fiestas"), "our own line, never the English store text")
        self.assertEqual(h["pack"], "Paquete de 12")

    def test_english_page(self):
        v = self.views("en")
        self.assertEqual([(x["type"], x["pub"]) for x in v], [("cards", "gv"), ("calendar", "gv")], "one card per kind, Grapevine first; 'other' left out")
        cards, cal = v
        self.assertEqual((cards["price"], cards["pack"], cards["volume"]), ("$36.00", "Box of 24", "5 or more: $34.80 each"))
        self.assertEqual((cards["text"], cards["textLang"]), ("Each card is beautifully illustrated.", "en"))
        self.assertEqual(cards["also"]["title"], "Tarjetas de Ocasión")
        self.assertFalse(cards["also"]["same"], "different cards (GVGC01 / LVGC01): an edition link, not 'also at'")
        self.assertTrue(cal["also"]["same"], "MS08 / MS08LV: the same calendar")
        self.assertEqual(cal["anchor"], "special-calendar")

    def test_spanish_page_uses_la_vina_and_never_a_machine_translation(self):
        v = self.views("es")
        cards, cal = v
        self.assertEqual((cards["pub"], cards["title"], cards["store"]), ("lv", "Tarjetas de Ocasión", "aalavina.org"))
        self.assertEqual(cards["image"], "", "different product: no borrowed picture")
        self.assertTrue(cards["text"].startswith("Tarjetas ilustradas"), "no Spanish store text: our own line")
        self.assertEqual(cal["image"], "/assets/cache/shop/c.webp", "the same calendar: Grapevine's picture")
        self.assertTrue(cal["trilingual"])
        self.assertEqual(cal["volume"], "5 o más: $10.00 c/u")
        self.assertNotIn("photographs", cal["text"])


SITE = ROOT / "_site"
STYLES = (ROOT / "src" / "assets" / "css" / "areas" / "shop.css").read_text(encoding="utf-8")


def fresh_build(*pages: Path) -> bool:
    """A build newer than the shop page, its styles, its filter and the committed shop data (an older one would
    show an older page). The tests job in CI does not build the site: these checks run after a local build."""
    sources = [ROOT / "src" / "pages" / "shop.njk", ROOT / "src" / "assets" / "css" / "areas" / "shop.css",
               ROOT / "eleventy" / "filters" / "shop.js", ROOT / "data" / "site" / "shop.json"]
    if not all(p.exists() for p in pages):
        return False
    built = min(p.stat().st_mtime for p in pages)
    return all(built >= s.stat().st_mtime for s in sources)


@unittest.skipUnless(fresh_build(SITE / "shop" / "index.html", SITE / "es" / "shop" / "index.html"),
                     "no fresh build (npx @11ty/eleventy) to check")
class BuiltSpecialtySection(unittest.TestCase):
    """The built /shop/ and /es/shop/ #specialty: one card per kind the committed data gives — four, in the
    order cards · planner · calendar · holiday, while the stores sell the holiday cards — and data-count for
    the four-card layout (shop.css)."""

    def test_one_card_per_kind_in_both_languages(self):
        shop = json.loads((ROOT / "data" / "site" / "shop.json").read_text(encoding="utf-8"))
        for lang, page in (("en", SITE / "shop" / "index.html"), ("es", SITE / "es" / "shop" / "index.html")):
            with self.subTest(lang=lang):
                views = run_js(self, "out(filters.shopSpecialty(input.shop, input.lang))", data={"shop": shop, "lang": lang})
                soup = BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")
                grid = soup.select_one("#specialty ul.shop-special-grid")
                self.assertIsNotNone(grid)
                cards = grid.select(":scope > li.shop-special")
                self.assertEqual([c["id"] for c in cards], ["special-" + v["type"] for v in views])
                self.assertEqual(grid["data-count"], str(len(views)))
                for c, v in zip(cards, views):
                    self.assertEqual(c.select_one("h3").get_text(strip=True), v["title"])
                    self.assertIn(v["url"], [a["href"] for a in c.select("a[href]")])
                if any(v["type"] == "holiday" for v in views):
                    self.assertEqual(len(cards), 4)
                    holiday = grid.select_one("#special-holiday")
                    self.assertIn("Pack of 12" if lang == "en" else "Paquete de 12", holiday.get_text(" "))
                    self.assertIn("Comprar en aalavina.org" if lang == "es" else "Buy on aagrapevine.org", holiday.get_text(" "))
                # the hero's teaser lists the same items, linking to them
                teaser = [a["href"] for a in soup.select(".shop-aside a.hero-aside-item")]
                self.assertEqual(teaser, ["#special-" + v["type"] for v in views])

    def test_card_parts_fit_the_shared_rows(self):
        """Each part of a card's body sits on its own row shared with the cards beside it (shop.css subgrid):
        never more parts than rows; the price and the button are two parts (so the buttons stay level); the
        holiday cards' "Seasonal" is a pill on the picture tile, not a badge-row line (screen readers still
        hear it in the badge row); an edition link's arrow is glued to its last word."""
        body_rows = int(re.search(r"\.shop-special-body \{[^}]*grid-row: span (\d)", STYLES).group(1))
        for lang, page in (("en", SITE / "shop" / "index.html"), ("es", SITE / "es" / "shop" / "index.html")):
            with self.subTest(lang=lang):
                soup = BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")
                for card in soup.select("#specialty li.shop-special"):
                    body = card.select_one(":scope > .shop-special-body")
                    parts = body.find_all(recursive=False)
                    self.assertLessEqual(len(parts), body_rows, card["id"])
                    buy, price = body.select_one("a.btn-primary, a.btn-lv"), body.select_one(".font-display.text-2xl")
                    self.assertIs(buy.parent.parent, body, "the button has a row of its own…")
                    self.assertIs(price.parent.parent, body, "…and so has the price")
                    self.assertIsNot(buy.parent, price.parent)
                    for a in body.select(":scope > p:last-child a.link"):
                        self.assertIsNotNone(a.select_one(".shop-special-glue > svg"), "the arrow sits with the last word")
                    if card["id"] == "special-holiday":
                        flag = card.select_one(".shop-special-img > .shop-special-flag")
                        word = "Seasonal" if lang == "en" else "De temporada"
                        self.assertIn(word, flag.get_text(" "))
                        self.assertIn(word, body.select_one(":scope > p:first-child .sr-only").get_text(" "))
                        self.assertIsNone(body.select_one(":scope > p:first-child .badge-grape"))


class SpecialtyStyles(unittest.TestCase):
    """shop.css for #specialty: a card's rows and the steps of the four-card layout."""

    def test_a_card_spans_its_body_rows_and_the_picture(self):
        card = int(re.search(r"\.shop-special \{[^}]*grid-row: span (\d)", STYLES).group(1))
        body = int(re.search(r"\.shop-special-body \{[^}]*grid-row: span (\d)", STYLES).group(1))
        self.assertEqual((card, body), (6, 5), "picture · badges · title and text · price · button · edition")
        self.assertIn(f".shop-special-grid:not([data-count=\"4\"]) .shop-special-body {{ grid-row: span {body};", STYLES,
                      "three cards side by side span the same rows")

    def test_relaxed_spacing_starts_the_row_of_four_later(self):
        """Wider letters and words make the buttons ≈ 270px: a row of four from 83rem with relaxed spacing (72rem
        otherwise), the horizontal 2 × 2 until then — so a buy button never wraps onto two lines there."""
        four = 'grid-template-columns: repeat(4, minmax(0, 1fr))'
        at72 = STYLES[STYLES.index("@container shop-special (width >= 72rem)"):]
        self.assertIn(f':root:not([data-spacing="relaxed"]) .shop-special-grid[data-count="4"] {{ {four}', at72.split("}\n}")[0])
        at83 = STYLES[STYLES.index("@container shop-special (width >= 83rem)"):]
        self.assertIn(f':root[data-spacing="relaxed"] .shop-special-grid[data-count="4"] {{ {four}', at83.split("}\n}")[0])
        between = STYLES[STYLES.index("@container shop-special (72rem <= width < 83rem)"):].split("}\n}")[0]
        self.assertIn(':root[data-spacing="relaxed"] .shop-special-grid[data-count="4"] > .shop-special { grid-template-columns: 10rem', between)

    def test_print_keeps_a_card_whole(self):
        self.assertRegex(STYLES, r"@media print \{ \.shop-special \{ break-inside: avoid;")


class LaVinaWeeklyOpen(unittest.TestCase):
    CFG = {"title_es": "Nueva Reunión Abierta de La Viña", "title_en": "La Viña's New Open Meeting",
           "day": "thursday", "time": "12:00", "timezone": "America/New_York", "starts": "2026-11-05",
           "zoom_id": "871 2036 8287", "passcode": "238047", "summary_es": "Dos miembros comparten.",
           "summary_en": "Two members share."}

    def test_item_fields_and_first_date(self):
        it = W.lavina_item(self.CFG, datetime(2026, 9, 24, 15, 0, tzinfo=timezone.utc))
        self.assertEqual((it["id"], it["lang"], it["kind"]), ("weekly_open_lv", "es", "meeting"))
        ex = it["extra"]
        for key in ("zoom_id", "passcode", "day", "time", "weekday", "start_local", "timezone", "time_central",
                    "next_start", "zoom_url", "starts"):
            self.assertIn(key, ex)
        self.assertEqual(ex["next_start"], "2026-11-05T17:00:00Z", "never before the first meeting")
        self.assertEqual((ex["weekday"], ex["start_local"], ex["time_central"]), ("thursday", "12:00", "11 AM Central"))
        self.assertEqual(ex["zoom_url"], "https://zoom.us/j/87120368287")
        self.assertEqual(ex["own_i18n"]["title"]["en"], "La Viña's New Open Meeting")

    def test_after_the_start_it_is_the_next_thursday(self):
        it = W.lavina_item(self.CFG, datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc))
        self.assertEqual(it["extra"]["next_start"], "2026-11-12T17:00:00Z")

    def test_a_start_date_on_another_weekday_moves_to_the_first_meeting(self):
        it = W.lavina_item({**self.CFG, "starts": "2026-11-04"}, datetime(2026, 9, 24, 15, 0, tzinfo=timezone.utc))
        self.assertEqual((it["extra"]["starts"], it["extra"]["next_start"]), ("2026-11-05", "2026-11-05T17:00:00Z"))

    def test_disabled_or_broken_config(self):
        self.assertIsNone(W.lavina_item(None))
        self.assertIsNone(W.lavina_item({**self.CFG, "enabled": False}))
        self.assertIsNone(W.lavina_item({**self.CFG, "day": "someday"}))

    def test_grapevine_item_stays_first(self):
        gv = {"id": "weekly_open", "kind": "meeting", "title": "Grapevine Weekly Open AA Meeting", "extra": {}}
        items = W.with_lavina([gv], [], self.CFG)
        self.assertEqual([i["id"] for i in items], ["weekly_open", "weekly_open_lv"])
        self.assertEqual([i["id"] for i in W.with_lavina([gv], items, None)], ["weekly_open"])
        ctx = B.Ctx(offline=True)
        lv = W.lavina_item(self.CFG)
        lv["first_seen"] = "2026-09-25T00:00:00Z"            # newer than the Grapevine item …
        ctx.raw = {"weekly_open": {"items": [lv, {**gv, "url": "https://www.aagrapevine.org/grapevine-weekly-open",
                                                  "first_seen": "2026-09-01T00:00:00Z"}]}}
        self.assertEqual([i["id"] for i in B.weekly_open_items(ctx)], ["weekly_open", "weekly_open_lv"])   # … still second

    def test_bilingual_labels(self):
        lab = B.weekly_open_labels(W.lavina_item(self.CFG))
        self.assertEqual(lab["day"], {"en": "Thursdays", "es": "Jueves"})
        self.assertEqual(lab["when"]["en"], "Thursdays at 11:00 AM Central")
        self.assertIn("871 2036 8287", lab["sentence"]["es"])


if __name__ == "__main__":
    unittest.main()
