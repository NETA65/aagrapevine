"""The holiday gift offers of 2026 (AA Grapevine's second gift for $16, La Viña's for $8, through December 31), in ONE
pinned bulletin post with free shipping and the prices of January 1, 2027, and on /shop/ (config/site.yml
store_offers "holiday-gifts-2026"):

  * Bulletin     — content/bulletin/2026-11-11-holiday-gift-offers-free-shipping-and-new-prices.md (CONTENT_TESTS):
                   pinned through December 31, its own Spanish with the same three sections; the opening names the
                   three (its first sentence under 140 characters — Share —, its first paragraph within the booth's
                   280, and what Home's card, What's New and the feed show is that opening, never a heading run into
                   it); each section's facts and links (the offers' pages exactly as AA Grapevine and La Viña write
                   them: /2gifts without a "/" at the end); calm words (no "!", "just", "hurry", "Save 55%", "ahead
                   of the new prices", "antes de los nuevos precios" …); the offers never tied to the price change
                   (the gift-offer and free-shipping sections never mention it, no sentence holds December 31 and the
                   new prices, the opening names them once, in its first sentence), free
                   shipping never said of the gift offers, nothing said about combining but AA Grapevine's own words
                   (neither of its two offers combines with any other); on the site from November 11 through December 31
                   (Central), in the e-mail of December 1 (November's edition: the opening — in the HTML half whole, in
                   the text half its first paragraphs —, the gift prices in both, then "Details →"), on the booth with its first paragraph in each language;
  * RealSettings — config/site.yml store_offers "holiday-gifts-2026" (CONTENT_TESTS): its days (no first day said:
                   the stores give none), both stores' words and their offer pages;
  * ShopPages    — one build of /shop/, /es/shop/ and November's toolkit with the committee's settings
                   (CONTENT_TESTS): free shipping is still #offers, the gift offers come next (#offers-holiday-
                   gifts-2026), "Through December 31, 2026", each store's button to its offer page and the link to
                   its page for Canada ("La Viña" in one piece: a no-break space); every /shop/ link of the
                   bulletin post finds its section; November's toolkit links the gift offers' own section (its
                   row, and the month's message with 🎁).

    python -m unittest tests.test_r25_holiday_offers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import copy
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from nodejs import run_js  # noqa: E402
from scripts.notify import send_digest as SDM  # noqa: E402
from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402

POST = ROOT / "content" / "bulletin" / "2026-11-11-holiday-gift-offers-free-shipping-and-new-prices.md"
CONFIG = ROOT / "config" / "site.yml"
KEY = "holiday-gifts-2026"
# The offers' own pages, exactly as AA Grapevine and La Viña write them (aagrapevine.org/2gifts/ with a "/" at the
# end opens a dead page; aalavina.org/2gifts and aagrapevine.org/2regalos are no offer of this year)
GV_PAGE, GV_CA = "https://www.aagrapevine.org/2gifts", "https://www.aagrapevine.org/canada-2gifts"
LV_PAGE, LV_CA = "https://www.aalavina.org/2regalos", "https://www.aalavina.org/canada-2regalos"
LETTER = "https://drive.google.com/file/d/1S2PrbkYC4auxUSlgdwpoQKwZW3QeaI-p/view"
HEADINGS = {"en": ["Holiday gift offers", "Free shipping", "New prices from January 1, 2027"],
            "es": ["Ofertas de regalo para las fiestas", "Envío gratis", "Nuevos precios a partir del 1 de enero de 2027"]}
# Attraction rather than promotion: the stores' own sales words ("just $16 (Save 55%!)", "por solo $8 (¡Ahorra un
# 55%!)", "limited time", "hurry"), no urgency, no "buy before the prices change", nothing the stores don't say
CALM = (r"(?i)!|¡|\bjust\b|\bpor solo\b|\bsolo \$|hurry|prisa|ap[uú]rate|don.t miss|last chance|[uú]ltima oportunidad|"
        r"limited time|tiempo limitado|\bnow\b|\bahora\b|\bsave\b|ahorr|lock in|before (?:the )?(?:new )?prices?|"
        r"before january|ahead of|in time (?:for|before)|antes de que|antes de (?:l[oa]s? )?(?:nuev[oa]s? )?precios?|"
        r"antes del? (?:1 de )?enero|a tiempo|while (?:today.s|the current|these|current) prices|mientras (?:duren|sigan)|"
        r"good time|buen momento|take advantage|aprovech|hoy mismo|\btoday\b(?!.s prices)|(?<!precios de )\bhoy\b|"
        r"\btonight\b|esta noche|\bsoon\b|pronto|\bquick|r[aá]pido|"
        r"renew|renov|\bcode\b|c[oó]digo|minimum|m[ií]nimo|international|internacional|\bstack|combines with|"
        r"se combina con|trackingcode|%|percent|por ciento")
# The price change in words: what the gift-offer and free-shipping sections never mention (they stand beside the price
# section as facts of their own — never "on January 1 the first one becomes $39.00", "Desde el 1 de enero …"), and
# what only the opening's first sentence names, there without December 31
PRICE_WORDS = (r"(?i)january|enero|2027|\$39|\$19\.50|\$34|\$17\.00|\bprices\b|\bprecios\b|price (?:change|increase|rise)|"
               r"cambio de precio|aumento|\brais|\bincreas|\brise|\bgo(?:es)? up\b|\bsub(?:e|en|ir|ir[aá]n?)\b")
OFFERS_LAST_DAY = r"December 31|31 de diciembre|diciembre|December"


# The opening's second paragraph: the gift offers' prices (the e-mail of December 1 shows the opening)
PRICES = {
    "en": "The holiday gift offers: a second 1-year print subscription as a gift is $16.00 at Grapevine and $8.00 at "
          "La Viña, with the first, for yourself or as a gift, at its regular price ($36.00 at Grapevine, $18.00 at La Viña).",
    "es": "Las ofertas de regalo: $8.00 en La Viña y $16.00 en Grapevine por una segunda suscripción impresa de 1 año "
          "como regalo, con la primera, para ti o para regalar, a su precio habitual ($18.00 / $36.00).",
}


# What the post says about combining: AA Grapevine's words only, of its two offers (the opening), of its gift offer
# and of its free shipping (their sections) — nothing else, and never that free shipping and the gift offer combine
COMBINING = {
    "en": ["AA Grapevine says neither of its two offers can be combined with any other offer.",
           "AA Grapevine says its offer can't be combined with any other offer and is available only through its page.",
           "AA Grapevine says its offer can't be combined with any other offer."],
    "es": ["Según AA Grapevine, ninguna de sus dos ofertas se puede combinar con ninguna otra.",
           "Según AA Grapevine, su oferta no se puede combinar con ninguna otra y se obtiene únicamente en su página.",
           "Según AA Grapevine, su oferta no se puede combinar con ninguna otra."],
}


def plain(md: str) -> str:
    """Markdown → the plain line the sync makes of it (announcements.markdown_to_text)."""
    return A.markdown_to_text(md)


def excerpt(s: str, n: int) -> str:
    """eleventy.config.js `excerpt`: Home's card (320), What's New (220), Share (140)."""
    s = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", s or "")).strip()
    return re.sub(r"\s+\S*$", "", s[:n]) + "…" if len(s) > n else s


def sections(body: str) -> tuple[str, dict[str, str]]:
    """A post's text → (the opening before its first heading, {heading: its section's text})."""
    parts = re.split(r"(?m)^# (.+)$", body)
    return parts[0].strip(), {h.strip(): t.strip() for h, t in zip(parts[1::2], parts[2::2])}


def sentences(md: str) -> list[str]:
    """A text's sentences, block by block (a paragraph, a heading, a list item), in plain words."""
    out: list[str] = []
    for block in re.split(r"\n\s*\n|\n(?=[-*] |# )", md):
        text = plain(block).replace("EE. UU.", "EEUU")
        out += [s for s in re.split(r"(?<=[.:;])\s+(?=[A-Z¿¡])|\s+·\s+", text) if s.strip()]
    return out


def links(md: str) -> list[str]:
    return re.findall(r"\]\(([^)\s]+)\)", md)


class Bulletin(unittest.TestCase):
    """The pinned post of November 11, 2026 (the Code check: CONTENT_TESTS). (Content: once the post is deleted
    after its time, these checks are skipped.)"""

    @classmethod
    def setUpClass(cls):
        if not POST.exists():
            raise unittest.SkipTest("the holiday offers post is no longer in content/bulletin")
        cls.post = A.parse_announcement(POST)
        x = cls.post["extra"]
        cls.body = {"en": x["body_md"], "es": x["own_i18n"]["body_md"]["es"]}
        cls.summary = {"en": cls.post["summary"], "es": x["own_i18n"]["summary"]["es"]}
        cls.parts = {lang: sections(b) for lang, b in cls.body.items()}
        cls.links = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["links"]

    def section(self, lang: str, i: int) -> str:
        return self.parts[lang][1][HEADINGS[lang][i]]

    def test_the_post(self):
        p, x = self.post, self.post["extra"]
        self.assertEqual((p["id"], p["date"], p["lang"], x["expires"], x["pinned"]),
                         ("ann:2026-11-11-holiday-gift-offers-free-shipping-and-new-prices", "2026-11-11", "en", "2026-12-31", True))
        self.assertNotIn("publish", x)
        self.assertNotIn("missing_files", x)
        self.assertIsNone(x["link"], "no url: the item's own link is the post (Home's Read more too)")
        self.assertEqual(p["title"], "Grapevine and La Viña: holiday gift offers, free shipping and new prices")
        self.assertEqual(x["own_i18n"]["title"]["es"], "La Viña y Grapevine: ofertas de regalo, envío gratis y nuevos precios")

    def test_the_same_three_sections_in_both_languages(self):
        # the ids come from the English headings when the counts match: a section's link finds it on both pages
        for lang in ("en", "es"):
            self.assertEqual(re.findall(r"(?m)^# (.+)$", self.body[lang]), HEADINGS[lang], lang)
            self.assertNotRegex(self.body[lang], r"(?m)^#{2,} ", "one level of headings")

    def test_the_opening(self):
        names = {"en": ("holiday gift offers", "free shipping", "new prices"),
                 "es": ("ofertas de regalo", "envío gratis", "nuevos precios")}
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                opening = self.parts[lang][0]
                first = plain(opening.split("\n\n")[0])
                s1 = sentences(opening)[0]
                # the Share button sends the summary's first 140 characters: the first sentence fits, and names the three
                self.assertLessEqual(len(s1), 140, s1)
                self.assertTrue(excerpt(self.summary[lang], 140).startswith(s1))
                for name in names[lang]:
                    self.assertIn(name, s1)
                # the booth shows the first paragraph whole (280 characters at most)
                self.assertLessEqual(len(first), 280, first)
                # Home's card (320), What's New (220) and the feed (the whole summary, 400) show the opening's prose,
                # never a heading run into it ("… lets everyone know. Holiday gift offers Through …")
                prose = plain(opening)
                self.assertGreaterEqual(len(prose), 400, "the opening is longer than the summary")
                self.assertTrue(prose.startswith(self.summary[lang].rstrip("…").rstrip()), self.summary[lang])
                for n in (140, 220, 320):
                    self.assertTrue(prose.startswith(excerpt(self.summary[lang], n).rstrip("…")), n)
        self.assertIn("U.S. and Canadian addresses and run through December 31, 2026", self.parts["en"][0])
        self.assertIn("valen para direcciones en EE. UU. y Canadá hasta el 31 de diciembre de 2026", self.parts["es"][0])
        self.assertIn(COMBINING["en"][0], self.parts["en"][0])
        self.assertIn(COMBINING["es"][0], self.parts["es"][0])
        self.assertIn("GVRs and RLVs", self.parts["en"][0])
        self.assertIn("RLV y GVR", self.parts["es"][0])
        # the gift offers' prices in the opening's second paragraph (the committee, 2026-11-11: the e-mail of December
        # 1, which shows the opening, gives them too) — prices only, no percentage
        self.assertEqual(self.parts["en"][0].split("\n\n")[1], PRICES["en"])
        self.assertEqual(self.parts["es"][0].split("\n\n")[1], PRICES["es"])

    def test_only_aa_grapevines_words_on_combining(self):
        # AA Grapevine says it of its two offers (the gift offer, free shipping), and the post says only that: never
        # that free shipping and the gift offer go together, nor anything of the Book of the Month (the stores say
        # nothing of it) — in the opening and in each section, sentence by sentence
        for lang in ("en", "es"):
            opening, secs = self.parts[lang]
            said = [[s for s in sentences(t) if re.search(r"(?i)combin", s)]
                    for t in (opening, *(secs[h] for h in HEADINGS[lang]))]
            self.assertEqual(said, [[COMBINING[lang][0]], [COMBINING[lang][1]], [COMBINING[lang][2]], []], lang)

    def test_the_holiday_gift_offers(self):
        en, es = self.section("en", 0), self.section("es", 0)
        for fact in ("Through **December 31, 2026**", "1-year print subscription at its regular price, for yourself or as a gift",
                     "a second 1-year print subscription as a gift is **$16.00** at Grapevine and **$8.00** at La Viña",
                     "the first is $36.00, the second $16.00", "the first is $18.00, the second $8.00",
                     "Both offers are for U.S. and Canadian addresses, and the details are on each store's page.",
                     "AA Grapevine says its offer can't be combined with any other offer and is available only through its page."):
            self.assertIn(fact, en)
        for fact in ("Hasta el **31 de diciembre de 2026**", "suscripción impresa de 1 año a su precio habitual, para ti o para regalar",
                     "una segunda suscripción impresa de 1 año como regalo cuesta **$8.00** en La Viña y **$16.00** en Grapevine",
                     "la primera, $18.00; la segunda, $8.00", "la primera, $36.00; la segunda, $16.00",
                     "Las dos ofertas son para direcciones en EE. UU. y Canadá, y los detalles están en la página de cada tienda.",
                     "Según AA Grapevine, su oferta no se puede combinar con ninguna otra y se obtiene únicamente en su página."):
            self.assertIn(fact, es)
        # the offers' pages, exactly; La Viña's first in Spanish; the other language's page said
        for body in (en, es):
            self.assertEqual(sorted(links(body)), sorted([GV_PAGE, GV_CA, LV_PAGE, LV_CA, "/shop/#offers-holiday-gifts-2026"]))
        self.assertIn(f"({LV_PAGE}) (in Spanish)", en)
        self.assertIn(f"({LV_CA}) (in Spanish)", en)
        self.assertIn(f"({GV_PAGE}) (en inglés)", es)
        self.assertIn(f"({GV_CA}) (en inglés)", es)
        self.assertLess(en.index(GV_PAGE), en.index(LV_PAGE))
        self.assertLess(es.index(LV_PAGE), es.index(GV_PAGE))
        # nothing the pages don't say: print only, one second gift (not "$16 each"), no renewal alone, no percentage;
        # and nothing about shipping (free shipping was never said of subscriptions)
        for body in (en, es):
            self.assertNotRegex(plain(body), r"(?i)digital|\$\d+(?:\.\d\d)? (?:each|cada)|renew|renov|55|shipping|env[ií]o")
            # and nothing about the price change: it has its own section ("regular price" is today's)
            self.assertNotRegex(plain(body), PRICE_WORDS)

    def test_free_shipping(self):
        en, es = self.section("en", 1), self.section("es", 1)
        self.assertIn("From **November 1 through December 31, 2026**, AA Grapevine and La Viña offer **free shipping on all "
                      "products** to U.S. and Canadian addresses. AA Grapevine says its offer can't be combined with any other "
                      "offer.", en)
        self.assertIn("Del **1 de noviembre al 31 de diciembre de 2026**, La Viña y AA Grapevine ofrecen **envío gratis en todos "
                      "sus productos** a EE. UU. y Canadá. Según AA Grapevine, su oferta no se puede combinar con ninguna otra.", es)
        gv, lv = self.links["gv_store"], self.links["lv_store"]
        for body in (en, es):
            self.assertEqual(sorted(links(body)), sorted(["/shop/#offers-free-shipping-2026", gv, lv]))
            # the stores' words: all products — never subscriptions or the gift offers; and never the price change
            self.assertNotRegex(plain(body), r"(?i)subscri|suscrip|gift|regalo")
            self.assertNotRegex(plain(body), PRICE_WORDS)
        self.assertIn(f"({lv}) (in Spanish)", en)
        self.assertIn(f"({gv}) (en inglés)", es)
        self.assertLess(es.index(lv), es.index(gv))

    def test_the_new_prices(self):
        en, es = self.section("en", 2), self.section("es", 2)
        # every new price in the section's first sentence, in both languages
        for body in (en, es):
            first = sentences(body)[0]
            for price in ("$39.00", "$34.00", "$19.50", "$17.00", "$2.00"):
                self.assertIn(price, first)
            self.assertEqual(sorted(links(body)), sorted(["/shop/#subscriptions", LETTER]))
            # no claim the letter does not make: other plans, other regions, "literature" (AA World Services' too);
            # and the offers stay in their own sections
            self.assertNotRegex(body, r"(?i)2-year|3-year|2 años|3 años|canad|international|internacional|monthly|mensual|"
                                      r"complete|completa|literature|literatura")
            self.assertNotRegex(plain(body), r"(?i)gift|regalo|free shipping|env[ií]o gratis|offer|oferta|december|diciembre")
        self.assertIn("printing, paper and materials, fulfillment, postage and shipping", en)
        self.assertIn("impresión, papel y materiales, preparación de pedidos, correo y envío", es)
        self.assertIn("If your group buys Grapevine or La Viña books or subscriptions, your treasurer may want to plan next "
                      "year's budget with the new prices.", en)
        self.assertIn("Si tu grupo compra libros o suscripciones de Grapevine y La Viña, quizás el tesorero quiera planear el "
                      "presupuesto del próximo año con los nuevos precios.", es)
        self.assertIn("(en inglés): [Grapevine & La Viña Pricing Update]", es)

    def test_calm_words(self):
        for lang in ("en", "es"):
            body = self.body[lang]
            self.assertNotRegex(re.sub(r"\]\([^)]*\)", "]", body), CALM, lang)
            self.assertNotIn("trackingcode", body)
            self.assertNotRegex(body, r"2gifts/|aalavina\.org/2gifts|aagrapevine\.org/2regalos|http://", "the pages exactly")
            # the offers and the price change side by side as facts: no sentence holds the offers' last day and the
            # price change (never "… until December 31, before the prices change on January 1", "… through December
            # 31, 2026, ahead of the new prices")
            for s in sentences(body):
                both = re.search(OFFERS_LAST_DAY, s) and re.search(
                    r"(?i)January|enero|2027|new prices|nuevos precios|price change|cambio de precio", s)
                self.assertFalse(both, s)
            # the opening names the new prices once, in its first sentence (with the offers and free shipping, never
            # their last day): no later sentence of it comes back to them ("After that, the new prices begin.")
            opening = sentences(self.parts[lang][0])
            self.assertEqual([s for s in opening if re.search(PRICE_WORDS, s)], opening[:1], lang)
            self.assertNotRegex(opening[0], OFFERS_LAST_DAY)

    def test_the_schedule(self):
        def shown(now: str) -> list[str]:
            c = B.Ctx(offline=True)
            c.now = datetime.fromisoformat(now.replace("Z", "+00:00"))
            c.now_ts = c.now.timestamp()
            c.today_local = c.now.astimezone(c.tz).date()
            c.raw = {"announcements": {"items": [{**copy.deepcopy(self.post), "first_seen": "2026-11-11T20:00:00Z"}]},
                     "drive": {"items": []}}
            c.births = {"announcements": 0.0}
            return [a["id"] for a in B.build_announcements(c)]
        post = [self.post["id"]]
        self.assertEqual(shown("2026-11-12T03:00:00Z"), post, "9 PM on November 11")
        self.assertEqual(shown("2027-01-01T05:30:00Z"), post, "11:30 PM on December 31")
        self.assertEqual(shown("2027-01-01T06:30:00Z"), [], "January 1, Central time")

    def item(self) -> dict:
        """The post as the site data has it (its own Spanish as its i18n)."""
        x = self.post["extra"]
        return {**copy.deepcopy(self.post), "first_seen": "2026-11-11T20:00:00Z", "status": "ok",
                "i18n": {"title": {"en": self.post["title"], "es": x["own_i18n"]["title"]["es"]},
                         "summary": dict(self.summary), "body_md": dict(self.body)}, "machine": []}

    def test_in_novembers_edition_of_the_digest(self):
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/community.js");
          const md = (now) => C.buildMonthlyDigest(input.db, { site: {}, now: new Date(now) }).news.announcement.map((i) => i.id);
          out({ oct: md("2026-11-01T15:05:00Z"), nov: md("2026-12-01T15:05:00Z") });""",
                   data={"db": {"announcements": {"items": [self.item()]}}})
        self.assertEqual(r, {"oct": [], "nov": [self.post["id"]]}, "the e-mail of December 1 (sent before it expires)")
        # the e-mail: the opening's whole paragraphs — exactly, never a heading whose section was cut ("…
        # everyone know. # Holiday gift offers") —, then "Details →"
        for lang in ("en", "es"):
            short, cut = SDM.md_excerpt(self.body[lang], 700)
            self.assertTrue(cut)
            self.assertEqual(short, self.parts[lang][0], lang)
            self.assertNotRegex(short.rstrip().rsplit("\n", 1)[-1], r"^#", "it does not end with a heading")
            # the text half (up to 600 characters): the opening's first whole paragraphs, the gift prices among them
            text, cut = SDM.md_excerpt(self.body[lang], 600)
            self.assertTrue(cut)
            self.assertTrue(self.parts[lang][0].startswith(text), lang)
            self.assertIn(text.split("\n\n")[-1], self.parts[lang][0].split("\n\n"), "whole paragraphs")
            self.assertIn(PRICES[lang], text)
        # Home's card (the summary's first 320 characters) names the offers' own prices, never only the first
        # subscription's regular ones
        for lang, want in (("en", "$16.00 at Grapevine and $8.00 at La Viña"), ("es", "$8.00 en La Viña y $16.00 en Grapevine")):
            self.assertIn(want, excerpt(self.summary[lang], 320), lang)

    def test_on_the_booth(self):
        # the booth's bulletin slide: the title and the first paragraph in each language, whole; no refused word
        r = run_js(self, r"""
          const B = await imp("eleventy/filters/booth.js");
          const site = (await imp("src/_data/site.js")).default();
          const res = B.liveItems({ db: { announcements: { items: [input.item] } }, site, now: new Date("2026-11-12T18:00:00Z"),
                                    base: "/aagrapevine/" });
          out({ items: res.items.filter((i) => i.channel === "live-bulletin"), problems: res.problems });""",
                   data={"item": self.item()})
        self.assertEqual(len(r["items"]), 1, r["problems"])
        slide = r["items"][0]
        for lang in ("en", "es"):
            first = plain(self.parts[lang][0].split("\n\n")[0])
            self.assertEqual(slide[lang]["text"], first, lang)
            self.assertEqual(slide[lang]["title"], self.item()["i18n"]["title"][lang])
        self.assertTrue(slide["qr"].endswith("/bulletin/#2026-11-11-holiday-gift-offers-free-shipping-and-new-prices"), slide["qr"])


# =========================================================================== the committee's block
class RealSettings(unittest.TestCase):
    """config/site.yml store_offers "holiday-gifts-2026" (the Code check: CONTENT_TESTS): what AA Grapevine's and La
    Viña's offer pages say, in the committee's words, with each store's page for the offer."""

    @classmethod
    def setUpClass(cls):
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        cls.block = next((o for o in (cfg.get("store_offers") or []) if isinstance(o, dict) and o.get("key") == KEY), None)
        if cls.block is None:
            raise unittest.SkipTest("the holiday gift offers block is no longer in config/site.yml")

    def test_the_days(self):
        o = self.block
        # the stores give no first day: none is said ("Through December 31, 2026"); the site shows it from the day it
        # went up — after free shipping's first day, so free shipping stays the Shop's #offers
        self.assertEqual((o["starts"], o["ends"], o["show_starts"]), ("2026-11-11", "2026-12-31", False))
        self.assertEqual(o["icon"], "gift", "not the truck: nothing in it is about shipping")

    def test_the_words(self):
        o = self.block
        self.assertEqual((o["title"], o["title_es"]), ("Holiday gift offers at the Grapevine and La Viña stores",
                                                       "Ofertas de regalo para las fiestas en las tiendas de La Viña y Grapevine"))
        gv, lv = o["gv"], o["lv"]
        for store, first, second in ((gv, "$36.00", "$16.00"), (lv, "$18.00", "$8.00")):
            self.assertIn(f"print subscription ({first}), for yourself or as a gift, a second 1-year print subscription as a "
                          f"gift is {second}. For U.S. and Canadian addresses; the details are on the offer's page.", store["text"])
            self.assertIn(f"suscripción impresa de 1 año a {'Grapevine' if store is gv else 'La Viña'} ({first}), para ti o "
                          f"para regalar, una segunda suscripción impresa de 1 año como regalo cuesta {second}. Para "
                          "direcciones en EE. UU. y Canadá; los detalles están en la página de la oferta.", store["text_es"])
            self.assertNotIn("banner_match", store, "no banner: the cards show without a picture")
        self.assertTrue(gv["text"].endswith("Grapevine says the offer can't be combined with any other offer."))
        self.assertTrue(gv["text_es"].endswith("Según Grapevine, la oferta no se puede combinar con ninguna otra."))
        self.assertNotRegex(lv["text"] + lv["text_es"], r"(?i)combin", "La Viña says nothing about combining")
        words = [o[k] for k in ("title", "title_es", "source", "source_es")] + [s[k] for s in (gv, lv) for k in ("text", "text_es")]
        for w in words:
            self.assertNotRegex(w, CALM, w)
            self.assertNotRegex(w, r"(?i)digital|\$\d+(?:\.\d\d)? (?:each|cada)|55|shipping|env[ií]o|january|enero|2027", w)
        for w in (o["title_es"], o["source_es"]):
            self.assertLess(w.index("La Viña"), w.index("Grapevine"), w)

    def test_the_offer_pages(self):
        self.assertEqual((self.block["gv"]["url"], self.block["gv"]["url_ca"]), (GV_PAGE, GV_CA))
        self.assertEqual((self.block["lv"]["url"], self.block["lv"]["url_ca"]), (LV_PAGE, LV_CA))


# =========================================================================== the pages
PAGES_JS = r"""
process.env.ONLY = "shop.njk,monthly-month";
process.env.PATH_PREFIX = "/";
process.env.MONTHLY_NOW = input.now;
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-gifts-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  const want = new Set(input.want);
  out(Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def section_of(page: str, sid: str) -> str:
    """<section id="…">…</section> (holding no other section)."""
    i = page.index(f'<section id="{sid}"')
    return page[i:page.index("</section>", i) + len("</section>")]


def text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip().replace("&#39;", "'")


class ShopPages(unittest.TestCase):
    """/shop/, /es/shop/ and November's toolkit built with the committee's settings, on November 12, 2026
    (the Code check: CONTENT_TESTS)."""

    built: dict | None = None

    @classmethod
    def setUpClass(cls):
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        if not any(isinstance(o, dict) and o.get("key") == KEY for o in (cfg.get("store_offers") or [])):
            raise unittest.SkipTest("the holiday gift offers block is no longer in config/site.yml")

    def pages(self) -> dict:
        if ShopPages.built is None:
            ShopPages.built = run_js(self, PAGES_JS, data={"now": "2026-11-12T15:00:00Z", "want": [
                "/shop/", "/es/shop/", "/monthly/2026-11/", "/es/monthly/2026-11/"]}, timeout=900)
        return ShopPages.built

    def test_the_two_offers(self):
        p = self.pages()
        for url, lang in (("/shop/", "en"), ("/es/shop/", "es")):
            with self.subTest(url=url):
                page = p[url]
                # free shipping is still #offers (first day first), the gift offers right after it
                first = section_of(page, "offers")
                self.assertIn('aria-labelledby="offer-free-shipping-2026-title"', first[:first.index(">") + 1])
                self.assertIn('id="offers-free-shipping-2026"', first)
                sec = section_of(page, f"offers-{KEY}")
                head = sec[:sec.index(">") + 1]
                self.assertLess(page.index('<section id="offers"'), page.index(f'<section id="offers-{KEY}"'))
                self.assertLess(page.index(f'<section id="offers-{KEY}"'), page.index('id="magazines"'))
                self.assertIn('data-gv-expire="2027-01-01T06:00:00Z"', head)
                self.assertNotIn(" hidden", head)
                self.assertNotIn("shop-offer-art", sec, "no banner")
                self.assertIn('<use href="#i-gift"/>', sec[:sec.index("</h2>")], "a gift, not the truck")
                self.assertIn('<use href="#i-truck"/>', first[:first.index("</h2>")])
                buttons = re.findall(r'<a class="btn-(?:primary|lv)" href="([^"]+)"', sec)
                ca = re.findall(r'<a class="link tap-link[^"]*" href="([^"]+)"', sec)
                # each store card's button row: with a page for Canada, its link on a line of its own in both cards
                rows = re.findall(r'<p class="mt-auto flex ([^"]*)"><a class="btn-', sec)
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(r.startswith("flex-col items-start") for r in rows), rows)
                free_rows = re.findall(r'<p class="mt-auto flex ([^"]*)"><a class="btn-', first)
                self.assertTrue(free_rows and all(r.startswith("flex-wrap items-center") for r in free_rows), free_rows)
                words = text(sec)
                # on a phone the buttons and links never break the magazine's name ("… de La / Viña"): a no-break space
                raw = sec.replace("&#39;", "'")
                for w in ({"en": ("La\u00a0Viña's offer page", "La\u00a0Viña's page for Canadian addresses"),
                           "es": ("Página de la oferta de La\u00a0Viña", "Página de La\u00a0Viña para direcciones en Canadá")}[lang]):
                    self.assertIn(w, raw)
                if lang == "en":
                    self.assertEqual((buttons, ca), ([GV_PAGE, LV_PAGE], [GV_CA, LV_CA]))
                    self.assertIn("Holiday gift offers at the Grapevine and La Viña stores Through December 31, 2026", words)
                    for w in ("Grapevine's offer page", "La Viña's offer page", "Grapevine's page for Canadian addresses",
                              "La Viña's page for Canadian addresses",
                              "a second 1-year print subscription as a gift is $16.00", "is $8.00",
                              "The store shows the final price at checkout. Source: AA Grapevine's and La Viña's holiday gift"):
                        self.assertIn(w, words)
                    self.assertNotRegex(words, r"November 11|October 1[34]", "no first day")
                else:
                    self.assertEqual((buttons, ca), ([LV_PAGE, GV_PAGE], [LV_CA, GV_CA]))
                    self.assertIn("Ofertas de regalo para las fiestas en las tiendas de La Viña y Grapevine Hasta el 31 de "
                                  "diciembre de 2026", words)
                    for w in ("Página de la oferta de La Viña", "Página de la oferta de Grapevine",
                              "Página de La Viña para direcciones en Canadá", "Página de Grapevine para direcciones en Canadá",
                              "como regalo cuesta $8.00", "cuesta $16.00"):
                        self.assertIn(w, words)
                    self.assertLess(words.index("Página de la oferta de La Viña"), words.index("Página de la oferta de Grapevine"))
                    self.assertNotRegex(words, r"11 de noviembre|1[34] de octubre", "no first day")

    def test_the_bulletin_posts_links_find_their_sections(self):
        if not POST.exists():
            self.skipTest("the holiday offers post is no longer in content/bulletin")
        x = A.parse_announcement(POST)["extra"]
        p = self.pages()
        for url, body in (("/shop/", x["body_md"]), ("/es/shop/", x["own_i18n"]["body_md"]["es"])):
            ids = [m for m in re.findall(r"\]\(/shop/#([^)]+)\)", body)]
            self.assertEqual(sorted(ids), ["offers-free-shipping-2026", f"offers-{KEY}", "subscriptions"])
            for i in ids:
                self.assertIn(f'id="{i}"', p[url], (url, i))

    def test_novembers_toolkit(self):
        p = self.pages()
        for url, title, days, shop in (("/monthly/2026-11/", "Holiday gift offers at the Grapevine and La Viña stores",
                                        "Through December 31, 2026", "/shop/"),
                                       ("/es/monthly/2026-11/", "Ofertas de regalo para las fiestas en las tiendas de La Viña y "
                                        "Grapevine", "Hasta el 31 de diciembre de 2026", "/es/shop/")):
            with self.subTest(url=url):
                keep = section_of(p[url], "mp-keep")
                rows = [r for r in re.findall(r"<li\b.*?</li>", keep, re.S) if title in r]
                self.assertEqual(len(rows), 1)
                self.assertEqual(text(rows[0]), f"{title} {days}")
                self.assertIn('<use href="#i-gift"/>', rows[0])
                # its own section, not the top of the offers (free shipping)
                self.assertIn(f'href="{shop}#offers-{KEY}"', rows[0])
                # the month's message (WhatsApp): a gift, not the parcel, and the same section
                self.assertRegex(p[url].replace("&#39;", "'"),
                                 re.escape(f"🎁 *{title}*\n{days}: ") + r"\S*" + re.escape(f"{shop}#offers-{KEY}\n"))


if __name__ == "__main__":
    unittest.main()
