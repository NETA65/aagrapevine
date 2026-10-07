"""Book of the Month, subscription prices and specialty items from the official stores → data/raw/shop.json

Grapevine and La Viña are published by AA Grapevine, Inc.; this module only READS their public store
pages so our site can show the current offer and prices and link to the official store to buy.

Pages (config/site.yml → sources.grapevine / sources.lavina; defaults below):
  * Book of the Month  — aagrapevine.org/BOTM, aalavina.org/libro-del-mes
      "October 20% off:" / title / "Purchase here!" → product page / blurb /
      "Offer good for this title: SEPT. 15 thru OCt. 14 Only." (years inferred around today)
  * its product page    — JSON-LD Product (price, sku, image) + the bulk-book discount lines
      ("5 – 9 books: $0.50 discount per book." / "5 a 9 libros: $0.50 de descuento por libro.")
  * subscriptions       — the category page (grapevine-subscriptions / tienda/suscripciones) lists the
      region listings (US / Canada / International); each listing has product cards: title, price,
      SKU, optional "Volume Discount Pricing" table, link, image
  * types (monthly at most) — one product page per subscription type per publication, for a short
      official description of print / digital / complete
  * specialty items (weekly at most) — the greeting cards, the annual pocket planner, the annual
      wall calendar and the holiday cards (sources.<pub>.specialty: product pages — title, price, SKU,
      image, a short official description, the pack size, the "5+" volume price — or a category
      listing, which adds the first card of each of those four kinds that no product page gave:
      aalavina.org/tienda/articulos-especiales gives La Viña's cards, planner and calendar;
      aagrapevine.org/store/specialty-items is only a fallback; sources.<pub>.specialty_skip hides a
      kind). The holiday cards are SEASONAL: when a store stops showing them (their page gone, no
      listing showing them), the last good item is kept (no error) and build_data leaves it off the
      site after a two-week grace (collect_specialty)

Cost: ~12 page requests a day (+ robots.txt, + a product page per type once a month, + 7 specialty
pages once a week, + images only the first time they are seen), all through the shared polite
session (5 s between requests).

Output (docs/DATA_SCHEMA.md → "shop"): items
    botm:gv / botm:lv            kind "botm"          (extra: price, sale_price, discount_pct, sku, starts, ends,
                                                       read — the day the prices were read …)
    sub:<pub>:<region>:<sku>     kind "subscription"  (extra: type, term_months, price, sku, volume …)
    special:<pub>:<sku>          kind "specialty"     (extra: type cards|planner|calendar|holiday|other, price,
                                                       sku, volume, trilingual, pack, page_url, position,
                                                       missing_since …)
  + envelope keys `bulk_discounts`, `types`, `listings`, `types_checked`, `specialty_checked` and `price_memory`
    (the 1-year and Book of the Month prices read before each announced price change took effect: price_memory
    below).
build_data.py turns it into data/site/shop.json (translations, expired offers left out, the announced price changes).

Each part (GV offer, LV offer, GV subscriptions, LV subscriptions, each specialty page) is independent:
when one cannot be fetched or parsed, its previous items are kept and the envelope is marked ok=false
(→ /status/ and the "not updating for 7 days" report). A region listing whose cards show no readable price
counts as not parsed: plans are never published without their prices. A Book of the Month page that is up but
shows no offer is not an error: the offer is simply gone. Neither is a seasonal specialty item (the holiday
cards) that a store no longer shows: it is out of season (its last good item is kept, marked missing_since) —
but a seasonal page that answers and is not understood, or is down while a listing still shows it, is an error.

Run:  python -m scripts.sync.shop [--dry-run] [--no-images] [--refresh-types] [--refresh-specialty]
                                  [--html-dir DIR] [--save-html DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from . import price_changes as PC
from .common import (CACHE_ASSETS, MONTHS, clean_text, get_logger, load_config, load_raw, make_item, merge_items,
                     now_iso, parse_iso, run_module, save_raw, shared_session, short_hash, slugify, truncate)

SOURCE = "shop"
log = get_logger(SOURCE)

CACHE_DIR = CACHE_ASSETS / "shop"
SITE_CACHE = "/assets/cache/shop"

# Defaults — config/site.yml sources.grapevine / sources.lavina override every one of them.
PUBS: dict[str, dict] = {
    "gv": {"cfg": "grapevine", "source": "grapevine", "lang": "en", "base": "https://www.aagrapevine.org",
           "botm": "/BOTM", "subscriptions": "/store/grapevine-subscriptions",
           "subscription_regions": {"us": "/store/us-subscriptions", "ca": "/store/canada-subscriptions",
                                    "intl": "/store/international-subscriptions"},
           "specialty": ["/store/greeting-cards", "/store/annual-pocket-planner", "/store/annual-wall-calendar",
                         "/store/holiday-greeting-cards-12-pack", "/store/specialty-items"]},
    "lv": {"cfg": "lavina", "source": "lavina", "lang": "es", "base": "https://www.aalavina.org",
           "botm": "/libro-del-mes", "subscriptions": "/tienda/suscripciones",
           "subscription_regions": {"us": "/US-suscripciones", "ca": "/tienda/canada-suscripciones",
                                    "intl": "/tienda/internacional-suscripciones"},
           "specialty": ["/tienda/articulos-especiales", "/tienda/tarjetas-de-ocasion-para-las-fiestas-paquete-de-12"]},
}
REGIONS = ("us", "ca", "intl")
TYPES = ("print", "digital", "complete")
TYPES_REFRESH_DAYS = 30          # product pages for the type descriptions: at most once a month
MAX_NEW_IMAGES = 4               # new image downloads per run (each is a request to the same server)
MAX_LISTING_PAGES = 3            # a region listing with a pager: follow "next" at most twice
SPECIALTY_REFRESH_DAYS = 7       # the specialty pages (cards, planner, calendar, holiday cards): at most once a week
SPECIALTY_KINDS = ("cards", "planner", "calendar", "holiday")
# Sold only part of the year (the holiday cards, from about September): when a store stops showing one, its last
# good item is kept and marked `missing_since` — not an error (collect_specialty; build_data's grace period).
SEASONAL_KINDS = ("holiday",)
# The pack size in a product's name or text: "box of 24", "Holiday Greeting Cards - 12 pack", "(pack of 50)",
# "Paquete de 12", "caja de 24", "Cada caja contiene 12 tarjetas".
PACK_RE = re.compile(r"(?i)\b(?:box(?:es)?|packs?|paquetes?|cajas?)\s+(?:of|de)\s+(\d{1,3})\b"
                     r"|\b(\d{1,3})[\s-]*pack\b|\bcaja\s+contiene\s+(\d{1,3})\b")
# A line about the size or the price, never part of a short description ("(Dimensions are 5 by 7 inches)",
# "The open calendar …", "Tamaño: 5 × 7 pulgadas"; "… in a box of 12 for $22(USD).": prices come from the data).
SPEC_LINE_RE = re.compile(r"(?i)^\(?\s*(?:dimensions|the (?:open|closed)|tama[ñn]o|medidas|dimensiones)\b")

MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December")
MONTHS_ES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
             "Octubre", "Noviembre", "Diciembre")
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
# "SEPT. 15", "OCt. 14, 2026"  /  "15 de AGOSTO", "14 de octubre de 2026"
DATE_RE = re.compile(
    rf"(?i)\b(?:({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?"
    rf"|(\d{{1,2}})\s+(?:de\s+)?({_MONTH_RE})\.?(?:,?\s+(?:de\s+|del\s+)?(20\d\d))?)\b")
PCT_RE = re.compile(r"(\d{1,2}(?:[.,]\d+)?)\s*%")
OFFER_RE = re.compile(r"(?i)\b(?:offer|good|valid|v[áa]lid[oa]|oferta|thru|through|until|hasta)\b")
MONEY_RE = re.compile(r"(US|CA|C)?\$\s*(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
# The Book of the Month page itself (its <title> / heading), so an unrelated 200 page (maintenance,
# a redirect to the home page) is never read as "no offer today".
BOTM_PAGE_RE = re.compile(r"(?i)book\s+of\s+the\s+month|libro\s+del\s+mes")
TIER_RE = re.compile(r"(?i)(\d+)\s*(?:[–—-]|a|to)\s*(\d+)\s*(?:books?|libros?)\s*:?\s*(?:US)?\$\s*(\d+(?:\.\d+)?)")
TIER_OPEN_RE = re.compile(r"(?i)(\d+)\s*(?:\+|o\s+m[áa]s|or\s+more)\s*(?:books?|libros?)\s*:?\s*(?:US)?\$\s*(\d+(?:\.\d+)?)")
RANGE_RE = re.compile(r"(\d+)\s*(?:[–—-]|a|to)\s*(\d+)|(\d+)\s*(?:\+|o\s+m[áa]s|or\s+more)")
TERM_RE = re.compile(r"(?i)(\d+)\s*[- ]?\s*(months?|mes(?:es)?|years?|anos?)\b")
STORE_PATH_RE = re.compile(r"^/(?:store|tienda)/[^/?#]+")


class ShopParseError(ValueError):
    """The page was fetched but its layout was not understood."""


class PageNotFetched(ShopParseError):
    """The page was not fetched at all (an error answer such as 404, a timeout, robots.txt). Only the specialty
    read tells it apart from a page that answered but was not understood: a seasonal page that is not there any
    more is out of season, one that answers in a layout we no longer read is broken (collect_specialty)."""


# --------------------------------------------------------------------------- small helpers
def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def money(s: str | None) -> float | None:
    m = MONEY_RE.search(s or "")
    return float(m[2].replace(",", "")) if m else None


def money_currency(s: str | None) -> str:
    """"CA$ 30.00" / "C$30" → "CAD"; "$30" / "US$30" → "USD"."""
    m = MONEY_RE.search(s or "")
    return "CAD" if m and m[1] in ("CA", "C") else "USD"


def sale_price(price: float | None, pct: float | None) -> float | None:
    if price is None or pct is None:
        return None
    v = Decimal(str(price)) * (Decimal(1) - Decimal(str(pct)) / Decimal(100))
    return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def month_label(month: int | None, lang: str) -> str | None:
    if not month or not 1 <= month <= 12:
        return None
    return (MONTHS_ES if lang == "es" else MONTHS_EN)[month - 1]


def settings(cfg: dict | None = None) -> dict[str, dict]:
    """Absolute URLs per publication (config/site.yml sources.<grapevine|lavina> over the defaults)."""
    cfg = cfg if cfg is not None else load_config()
    src = cfg.get("sources") or {}
    out: dict[str, dict] = {}
    for pub, d in PUBS.items():
        c = src.get(d["cfg"]) or {}
        base = str(c.get("base") or d["base"]).rstrip("/")

        def url(v, default):
            v = v or default
            return v if re.match(r"(?i)https?://", str(v)) else base + "/" + str(v).lstrip("/")
        regions_cfg = c.get("subscription_regions") if isinstance(c.get("subscription_regions"), dict) else {}
        special = c.get("specialty") if isinstance(c.get("specialty"), list) else d["specialty"]
        # Kinds this store's items are never shown for (`specialty_skip: [holiday]`): the off switch, since
        # deleting a product page's line only moves that item to the listing. A word that is not one of the
        # four kinds is left out with a warning (a typo never hides anything).
        skip_cfg = c.get("specialty_skip") if isinstance(c.get("specialty_skip"), list) else []
        skip = [str(k).strip().lower() for k in skip_cfg if str(k or "").strip()]
        for k in skip:
            if k not in SPECIALTY_KINDS:
                log.warning("sources.%s.specialty_skip: %r is not one of %s — ignored", d["cfg"], k,
                            ", ".join(SPECIALTY_KINDS))
        out[pub] = {
            "pub": pub, "lang": d["lang"], "source": d["source"], "base": base,
            "botm": url(c.get("botm"), d["botm"]),
            "subscriptions": url(c.get("subscriptions"), d["subscriptions"]),
            "regions": {r: url(regions_cfg.get(r), d["subscription_regions"][r]) for r in REGIONS},
            "specialty": [url(v, v) for v in special if v],
            "specialty_skip": [k for k in skip if k in SPECIALTY_KINDS],
        }
    return out


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _content(soup: BeautifulSoup):
    """The page's own content block (Drupal), without menus, footers or the cart widget."""
    main = soup.find("main") or soup.body or soup
    return main.select_one("#block-neatosub-content") or main


def _lines(el) -> list[tuple[str, object]]:
    """(text, element) of each text block in document order (innermost blocks only)."""
    out = []
    for b in el.find_all(["p", "h1", "h2", "h3", "h4", "h5", "li", "blockquote"]):
        if b.find(["p", "h1", "h2", "h3", "h4", "h5", "li"]):
            continue
        t = clean_text(b.get_text(" "))
        if t:
            out.append((t, b))
    return out


def _abs(page_url: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(page_url, href.strip())


def _no_query(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def _parse_dates(text: str) -> list[tuple[int, int, int | None]]:
    """[(month, day, year or None), …] in the order written."""
    out = []
    for m in DATE_RE.finditer(text):
        if m[1]:
            mo, d, y = MONTHS.get(m[1].lower()), int(m[2]), m[3]
        else:
            mo, d, y = MONTHS.get(m[5].lower()), int(m[4]), m[6]
        if mo and 1 <= d <= 31:
            out.append((mo, d, int(y) if y else None))
    return out


def _safe_date(y: int, mo: int, d: int) -> date | None:
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def offer_dates(text: str, today: date) -> tuple[str | None, str | None]:
    """'SEPT. 15 thru OCt. 14 Only.' → ('2026-09-15', '2026-10-14') with years inferred around today:
    the latest window that has already started (or starts within a month), so an old offer left on
    the page is read as past, never as next year's; the start is the latest date on or before the end."""
    ds = _parse_dates(text)
    if not ds:
        return None, None
    (smo, sd, sy), (emo, ed, ey) = (ds[0], ds[1]) if len(ds) >= 2 else (ds[0], ds[0])
    if ey:
        end = _safe_date(ey, emo, ed)
    else:
        cands = [c for c in (_safe_date(today.year + k, emo, ed) for k in (-1, 0, 1)) if c]
        if len(ds) >= 2 and not sy:
            def start_of(e: date) -> date | None:
                s0 = _safe_date(e.year, smo, sd)
                return _safe_date(e.year - 1, smo, sd) if s0 and s0 > e else s0
            ok = [c for c in cands if (start_of(c) or c) <= today + timedelta(days=31)]
            end = max(ok) if ok else (min(cands) if cands else None)
        else:
            end = min(cands, key=lambda c: abs((c - today).days)) if cands else None
    if end is None:
        return None, None
    start = _safe_date(sy, smo, sd) if sy else _safe_date(end.year, smo, sd)
    if start and not sy and start > end:
        start = _safe_date(end.year - 1, smo, sd)
    if len(ds) < 2:
        return None, end.isoformat()
    return (start.isoformat() if start else None), end.isoformat()


# --------------------------------------------------------------------------- Book of the Month page
def parse_botm(html: str, page_url: str, lang: str, today: date) -> dict | None:
    """The offer on a Book of the Month page, or None when the page shows no offer.
    Raises ShopParseError when an offer is there but cannot be read (layout change)."""
    soup = _soup(html)
    block = _content(soup)
    for t in block.find_all(["script", "style", "noscript", "form", "nav"]):
        t.decompose()
    lines = _lines(block)
    host = urlsplit(page_url).netloc.lower()

    product_url = None
    for a in block.find_all("a", href=True):
        u = _abs(page_url, a["href"])
        p = urlsplit(u)
        if p.netloc.lower().removeprefix("www.") == host.removeprefix("www.") and STORE_PATH_RE.match(p.path):
            product_url = _no_query(u)
            break
    pct_i = next((i for i, (t, el) in enumerate(lines) if PCT_RE.search(t) and not el.find_parent("a")), None)
    if pct_i is None and not product_url:
        heads = [soup.title.get_text(" ") if soup.title else ""] + [h.get_text(" ") for h in soup.find_all(["h1", "h2"], limit=8)]
        if not soup.select_one("#block-neatosub-content") or not any(BOTM_PAGE_RE.search(h or "") for h in heads):
            raise ShopParseError("page does not look like the Book of the Month page (maintenance? redirect?)")
        return None                                   # no offer on the page today
    if pct_i is None:
        raise ShopParseError("Book of the Month: product link found but no discount percent")
    if not product_url:
        raise ShopParseError("Book of the Month: discount found but no link to the store")
    pct_line = lines[pct_i][0]
    pct = float(PCT_RE.search(pct_line)[1].replace(",", "."))
    if not 0 < pct < 100:
        raise ShopParseError(f"Book of the Month: odd discount {pct}%")

    def is_offer_line(t: str) -> bool:
        return bool(OFFER_RE.search(t)) and len(_parse_dates(t)) >= 1

    # Title: text after the colon of the discount line ("October 20% off: Title"), else the next
    # text block that is not a button, the dates or the blurb.
    title = ""
    after = re.split(r"[:!]\s*", pct_line.split("%", 1)[1], maxsplit=1)
    if len(after) == 2 and len(clean_text(after[1])) > 3:
        title = clean_text(after[1])
    if not title:
        for t, el in lines[pct_i + 1:]:
            if el.find_parent("a") or el.find("a") or is_offer_line(t) or PCT_RE.search(t):
                continue
            if 3 < len(t) <= 160:
                title = t
                break
    blurb = next((t for t, el in lines if len(t) >= 80 and t != title and not is_offer_line(t)
                  and not el.find("a")), "")
    offer_line = next((t for t, _ in lines if is_offer_line(t)), "")
    starts, ends = offer_dates(offer_line, today) if offer_line else (None, None)

    month = None
    for w in re.findall(r"[^\W\d_]+", pct_line):
        if w.lower() in MONTHS and len(w) >= 3:
            month = MONTHS[w.lower()]
            break
    if month is None and ends:
        month = int(ends[5:7])
    img = block.find("img", src=True)
    return {
        "title": title, "url": product_url, "discount_pct": int(pct) if pct.is_integer() else pct,
        "month": month, "month_label": month_label(month, lang), "blurb": blurb,
        "starts": starts, "ends": ends, "offer_text": truncate(offer_line, 200),
        "page_image": _abs(page_url, img["src"]) if img else None,
    }


# --------------------------------------------------------------------------- product page
def _ld_product(soup: BeautifulSoup) -> dict:
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or sc.get_text() or "{}", strict=False)
        except ValueError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data if isinstance(data, list) else []
        for n in nodes:
            if isinstance(n, dict) and "Product" in (n.get("@type") if isinstance(n.get("@type"), list) else [n.get("@type")]):
                return n
    return {}


def parse_tiers(text: str) -> list[dict]:
    """'5 – 9 books: $0.50 discount per book. … 30+ books: $3.00 …' → tiers incl. the implicit
    1–4 = 0 tier; [] when the page lists none."""
    tiers = [{"min": int(a), "max": int(b), "off": float(off)} for a, b, off in TIER_RE.findall(text)]
    tiers += [{"min": int(a), "max": None, "off": float(off)} for a, off in TIER_OPEN_RE.findall(text)]
    seen, out = set(), []
    for t in sorted(tiers, key=lambda t: t["min"]):
        if t["min"] not in seen:
            seen.add(t["min"])
            out.append(t)
    if out and out[0]["min"] > 1:
        out.insert(0, {"min": 1, "max": out[0]["min"] - 1, "off": 0.0})
    return out


def parse_product(html: str, page_url: str) -> dict:
    """Price, SKU, image, name, description and bulk discount tiers of a store product page."""
    soup = _soup(html)
    ld = _ld_product(soup)
    block = _content(soup)
    art = block.select_one("article.product") or block
    out: dict = {"url": _no_query(page_url)}
    out["name"] = clean_text(ld.get("name")) or clean_text((soup.find("h1") or soup.new_tag("x")).get_text(" "))
    offers = ld.get("offers")
    offers = offers[0] if isinstance(offers, list) and offers else offers if isinstance(offers, dict) else {}
    try:
        out["price"] = round(float(offers.get("price")), 2) if offers.get("price") not in (None, "") else None
    except (TypeError, ValueError):
        out["price"] = None
    if out["price"] is None:                     # both Drupal field templates (see parse_listing)
        el = art.select_one(".field--name-price .field__item, .field--name-price.field__item")
        out["price"] = money(el.get_text(" ") if el else "")
    out["currency"] = clean_text(offers.get("priceCurrency")) or "USD"
    sku_el = art.select_one(".field--name-sku .field__item, .field--name-sku.field__item")
    out["sku"] = clean_text(ld.get("sku")) or (clean_text(sku_el.get_text(" ")) if sku_el else None) or None
    img = ld.get("image")
    img = img.get("url") if isinstance(img, dict) else img[0] if isinstance(img, list) and img else img
    if not img:
        el = art.select_one("img.image-style-product-feature-image, img[src*='product_feature_image']")
        img = el.get("src") if el else None
    out["image"] = _abs(page_url, img) if isinstance(img, str) and img else None
    body = art.select_one(".field--name-body") or art
    body_text = clean_text(body.get_text(" "))
    out["tiers"] = parse_tiers(body_text)
    note = next((clean_text(t).lstrip("*").strip() for t in body.stripped_strings
                 if re.search(r"(?i)physical books|libros f[ií]sicos", t)), "")
    out["tiers_note"] = note or None
    paras = [clean_text(p.get_text(" ")) for p in body.find_all("p")]
    paras = [p for p in paras if len(p) >= 40 and p != out["name"] and not TIER_RE.search(p)
             and not re.search(r"(?i)the more books|cuantos m[áa]s libros|physical books|libros f[ií]sicos", p)]
    out["description"] = truncate(" ".join(paras[:2]), 320) if paras else ""
    # The product's feature list ("Combines the Grapevine print magazine, complete online access …").
    out["features"] = [t for t in (clean_text(li.get_text(" ")) for li in body.find_all("li")) if len(t) > 3][:8]
    return out


def short_description(prod: dict, minimum: int = 40) -> str:
    """One short official description: the first feature(s) of the list, else the description."""
    parts: list[str] = []
    for f in prod.get("features") or []:
        parts.append(f.rstrip(" .") + ".")
        if len(" ".join(parts)) >= minimum:
            break
    return truncate(" ".join(parts), 220) if parts else truncate(prod.get("description") or "", 220)


# --------------------------------------------------------------------------- subscriptions
def region_of(text: str) -> str | None:
    f = fold(text)
    if "canad" in f:
        return "ca"
    if "internac" in f or "international" in f:
        return "intl"
    if re.search(r"(?:^|[^a-z])(?:us|u\.s\.?|usa|ee\.?\s*uu\.?)(?:[^a-z]|$)|estados unidos|united states", f):
        return "us"
    return None


def parse_categories(html: str, page_url: str) -> dict[str, str]:
    """{region: listing URL} from a subscriptions category page."""
    block = _content(_soup(html))
    out: dict[str, str] = {}
    for a in block.find_all("a", href=True):
        u = _abs(page_url, a["href"])
        path = urlsplit(u).path
        if not re.search(r"(?i)subscri|suscrip", path) or _no_query(u).rstrip("/") == _no_query(page_url).rstrip("/"):
            continue
        reg = region_of(f"{clean_text(a.get_text(' '))} {path.replace('-', ' ').replace('/', ' ')}")
        if reg and reg not in out:
            out[reg] = _no_query(u)
    return out


def plan_type(title: str) -> str:
    f = fold(title)
    if "complet" in f:
        return "complete"
    if "digital" in f or "online" in f or "en linea" in f:
        return "digital"
    if "print" in f or "impres" in f or "papel" in f:
        return "print"
    return "other"


def term_months(title: str) -> int | None:
    f = fold(title)
    m = TERM_RE.search(f)
    if m:
        n = int(m[1])
        return n if m[2].startswith("mes") or m[2].startswith("month") else n * 12
    if re.search(r"\bmensual\b|\bmonthly\b", f):
        return 1
    if re.search(r"\banual\b|\bannual\b|\byearly\b", f):
        return 12
    return None


def parse_volume(card) -> list[dict]:
    table = card.select_one(".field--name-field-tiered-pricing table") or card.find("table")
    if not table:
        return []
    heads = [clean_text(th.get_text(" ")) for th in table.find_all("th")]
    row = table.find("tbody") or table
    prices = [money(td.get_text(" ")) for td in row.find_all("td")]
    out = []
    for h, p in zip(heads, prices):
        m = RANGE_RE.search(h)
        if not m or p is None:
            continue
        lo, hi = (int(m[1]), int(m[2])) if m[1] else (int(m[3]), None)
        out.append({"min": lo, "max": hi, "price": p})
    return out


def parse_listing(html: str, listing_url: str) -> tuple[list[dict], str | None]:
    """Product cards of a region listing → (plans, next page URL or None)."""
    block = _content(_soup(html))
    plans = []
    for card in block.select("article.product"):
        a = card.select_one("h3 a[href], h2 a[href]") or card.find("a", href=True)
        if not a:
            continue
        title = clean_text(a.get_text(" ")) or clean_text((card.find(["h3", "h2"]) or a).get_text(" "))
        # Drupal's field template: with the label shown ("Price" / "Precio", "SKU") the value is a child
        # .field__item; with the label hidden (one value) .field__item sits on the field's own div — as the
        # title and image fields of these cards already are. Both, so hiding a label never loses the prices.
        price_el = card.select_one(".field--name-price .field__item, .field--name-price.field__item")
        sku_el = card.select_one(".field--name-sku .field__item, .field--name-sku.field__item")
        img = card.select_one(".image-region img[src]") or card.find("img", src=True)
        if not title:
            continue
        plans.append({
            "type": plan_type(title), "term_months": term_months(title), "title": title,
            "price": money(price_el.get_text(" ") if price_el else ""),
            "currency": money_currency(price_el.get_text(" ") if price_el else ""),
            "sku": clean_text(sku_el.get_text(" ")) if sku_el else None,
            "url": _no_query(_abs(listing_url, a["href"])),
            "image_src": _abs(listing_url, img["src"]) if img else None,
            "volume": parse_volume(card),
        })
    nxt = block.select_one(".pager__item--next a[href], a[rel='next'][href]")
    return plans, (_abs(listing_url, nxt["href"]) if nxt else None)


# --------------------------------------------------------------------------- specialty items
def specialty_kind(title: str, url: str = "") -> str | None:
    """'Annual Wall Calendar' / 'Calendario Anual de Pared' → 'calendar'; 'Agenda de Bolsillo' → 'planner';
    'Greeting cards' / 'Tarjetas de Ocasión' → 'cards'; cards for the holidays ('Holiday Greeting Cards - 12 pack',
    '¡Tarjetas de ocasión para las fiestas! Paquete de 12') → 'holiday' (a kind of its own: sold in season, next to
    the year-round greeting cards); anything else (a group agenda, back issues) → None."""
    f = fold(f"{title} {urlsplit(url).path.replace('-', ' ')}")
    cards = re.search(r"greeting card|\bcards?\b|\btarjetas?\b", f)
    if cards and re.search(r"\bholidays?\b|\bchristmas\b|\bnavid\w*|\bfiestas?\b", f):
        return "holiday"
    if re.search(r"greeting card|\btarjetas?\b", f):
        return "cards"
    if re.search(r"planner|agenda de bolsillo|pocket", f):
        return "planner"
    if re.search(r"\bcalendar|\bcalendario", f):
        return "calendar"
    return None


def _tidy(text: str) -> str:
    """The store's own words with two typing slips evened out: 'month-at- a-glance' → 'month-at-a-glance',
    'English/ Spanish/French' → 'English/Spanish/French'."""
    return re.sub(r"(\w)/\s+(\w)", r"\1/\2", re.sub(r"(\w)-\s+(\w)", r"\1-\2", clean_text(text)))


def special_text(paras: list[str], name: str, minimum: int = 90, maximum: int = 230) -> str:
    """A short official description: whole sentences of the first real paragraphs until ≥ `minimum` characters
    (at most `maximum`). Left out: the name line, a short line under 40 characters (a call to action such as
    "¡Ordena en línea!"), a size line and a sentence with a price (prices come from the data, never from a
    description). A first paragraph shorter than `minimum` ("Two different cartoons illustrated by AA
    members!") goes on with the next one."""
    out = ""
    for p in paras:
        p = _tidy(p)
        if len(p) < 40 or fold(p).rstrip(" .!") == fold(name).rstrip(" .!") or SPEC_LINE_RE.match(p):
            continue
        for sent in re.split(r"(?<=[.!?])\s+", p):
            if MONEY_RE.search(sent):
                continue
            nxt = f"{out} {sent}".strip()
            if out and len(nxt) > maximum:
                return truncate(out, maximum)
            out = nxt
            if len(out) >= minimum:
                return truncate(out, maximum)
    return truncate(out, maximum)


def pack_size(*texts: str) -> int | None:
    """The first pack size written in the texts ("Holiday Greeting Cards - 12 pack" → 12, "a box of 24" → 24,
    "Paquete de 12" → 12), or None."""
    for text in texts:
        m = PACK_RE.search(text or "")
        if m:
            return int(next(g for g in m.groups() if g))
    return None


def parse_specialty(html: str, page_url: str) -> list[dict]:
    """A specialty page → [{title, kind, price, currency, sku, url, image_src, text, volume, trilingual,
    pack, listed}]: ONE product (a product page, listed=False) or the first card of each of the four kinds
    (a category listing, listed=True, in the listing's order). Raises ShopParseError when neither is there."""
    soup = _soup(html)
    block = _content(soup)
    full = block.select_one("article.product.view-mode-full")
    if full is not None:
        prod = parse_product(html, page_url)
        name = clean_text(prod.get("name"))
        if not name and soup.title:                       # the <title> without " | AA Grapevine"
            name = clean_text(soup.title.get_text(" ").split("|")[0])
        if not name or prod.get("price") is None:
            raise ShopParseError(f"specialty product without a name or price on {page_url}")
        body = full.select_one(".field--name-body") or full
        paras = [clean_text(p.get_text(" ")) for p in body.find_all("p")]
        words = " ".join(paras)
        price_el = full.select_one(".field--name-price .field__item, .field--name-price.field__item")
        return [{
            "title": name, "kind": specialty_kind(name, page_url) or "other",
            "price": prod["price"], "currency": money_currency(price_el.get_text(" ")) if price_el else (prod.get("currency") or "USD"),
            "sku": prod.get("sku"), "url": _no_query(page_url), "image_src": prod.get("image"),
            "text": special_text(paras, name), "volume": parse_volume(full),
            "trilingual": bool(re.search(r"(?i)triling|english\s*/\s*spanish\s*/\s*french|ingl[ée]s\s*/\s*espa[ñn]ol\s*/\s*franc[ée]s", words)),
            "pack": pack_size(name, words), "listed": False,
        }]
    cards, _ = parse_listing(html, page_url)
    if not cards:
        raise ShopParseError(f"no product on the specialty page {page_url}")
    out, kinds = [], set()
    for c in cards:
        kind = specialty_kind(c["title"], c["url"])
        if kind and kind not in kinds and c.get("price") is not None:
            kinds.add(kind)
            out.append({"title": c["title"], "kind": kind, "price": c["price"], "currency": c.get("currency") or "USD",
                        "sku": c.get("sku"), "url": c["url"], "image_src": c.get("image_src"), "text": "",
                        "volume": c.get("volume") or [], "trilingual": False, "pack": pack_size(c["title"]),
                        "listed": True})
    if not out:
        raise ShopParseError(f"no greeting cards, planner, calendar or holiday cards listed on {page_url}")
    return out


# --------------------------------------------------------------------------- images
class ImageCache:
    """Product images → ≤480 px WebP in src/assets/cache/shop/<hash>.webp (hash of the address
    without its query, so Drupal's changing ?itok= token does not download it again)."""

    def __init__(self, http, budget: int = MAX_NEW_IMAGES, enabled: bool = True, folder: Path = CACHE_DIR):
        self.http, self.budget, self.enabled, self.folder = http, budget, enabled, folder
        self.downloaded = 0

    def path_for(self, url: str) -> tuple[Path, str]:
        name = f"{short_hash(_no_query(url), 16)}.webp"
        return self.folder / name, f"{SITE_CACHE}/{name}"

    def __call__(self, url: str | None) -> str | None:
        if not url:
            return None
        dest, site_path = self.path_for(url)
        if dest.exists():
            return site_path
        if not self.enabled or self.downloaded >= self.budget:
            return None
        try:
            from PIL import Image
        except Exception:
            return None
        self.downloaded += 1
        r = self.http.get(url)
        if r is None or r.status_code != 200 or not r.headers.get("Content-Type", "").startswith("image/") \
                or len(r.content) > 10 * 1024 * 1024:
            log.info("image not cached: %s", url)
            return None
        try:
            im = Image.open(BytesIO(r.content))
            im = im.convert("RGBA" if (im.mode in ("RGBA", "LA", "P") and "transparency" in im.info) or im.mode in ("RGBA", "LA")
                            else "RGB")
            im.thumbnail((480, 720))
            self.folder.mkdir(parents=True, exist_ok=True)
            im.save(dest, "WEBP", quality=76, method=6)
            return site_path
        except Exception as e:
            log.info("image %s could not be converted: %s", url, e)
            dest.unlink(missing_ok=True)
            return None


# --------------------------------------------------------------------------- collection
Fetch = Callable[[str], "str | None"]


def collect_botm(pub: str, s: dict, fetch: Fetch, images: Callable, today: date) -> tuple[list[dict], dict | None]:
    """→ ([botm item] or [], product details for the bulk tiers or None). Raises on failure."""
    html = fetch(s["botm"])
    if not html:
        raise ShopParseError(f"could not fetch {s['botm']}")
    offer = parse_botm(html, s["botm"], s["lang"], today)
    if offer is None:
        log.info("%s: no Book of the Month offer on %s", pub, s["botm"])
        return [], None
    phtml = fetch(offer["url"])
    if not phtml:
        raise ShopParseError(f"could not fetch the offer's product page {offer['url']}")
    prod = parse_product(phtml, offer["url"])
    if prod.get("price") is None:
        raise ShopParseError(f"no price on {offer['url']}")
    image_src = prod.get("image") or offer.get("page_image")
    extra = {
        "pub": pub, "page_url": s["botm"], "price": prod["price"],
        "sale_price": sale_price(prod["price"], offer["discount_pct"]), "discount_pct": offer["discount_pct"],
        "currency": prod.get("currency") or "USD", "sku": prod.get("sku"),
        "starts": offer.get("starts"), "ends": offer.get("ends"), "month": offer.get("month"),
        "month_label": offer.get("month_label"), "offer_text": offer.get("offer_text"),
        "product_name": prod.get("name"), "image_src": image_src,
        # the day these prices were read (Central): on and after an announced book price change
        # (config/site.yml price_changes) a price read before that day is not shown (build_data → shop.json)
        "read": today.isoformat(),
    }
    item = make_item(
        id=f"botm:{pub}", source=s["source"], kind="botm", url=offer["url"],
        title=offer.get("title") or prod.get("name") or "", summary=offer.get("blurb") or prod.get("description") or "",
        lang=s["lang"], date=offer.get("starts"), image=images(image_src), category="botm",
        extra={k: v for k, v in extra.items() if v not in (None, "")},
    )
    if not item["title"]:
        raise ShopParseError(f"Book of the Month on {s['botm']}: no title")
    return [item], prod


def collect_subscriptions(pub: str, s: dict, fetch: Fetch, images: Callable) -> tuple[list[dict], list[dict]]:
    """→ (plan items, listings [{pub, region, url}]). Raises when nothing could be read."""
    regions = dict(s["regions"])
    html = fetch(s["subscriptions"])
    if html:
        found = parse_categories(html, s["subscriptions"])
        if found:
            regions.update(found)
        else:
            log.warning("%s: no region links on %s — using config/site.yml", pub, s["subscriptions"])
    else:
        log.warning("%s: could not fetch %s — using config/site.yml", pub, s["subscriptions"])
    items, listings, failed = [], [], []
    for region in REGIONS:
        url = regions.get(region)
        if not url:
            continue
        listings.append({"pub": pub, "region": region, "url": url})
        plans, page, pages = [], url, 0
        while page and pages < MAX_LISTING_PAGES:
            h = fetch(page)
            pages += 1
            if not h:
                break
            got, page = parse_listing(h, page)
            plans += got
        if not plans or not any(p.get("price") is not None for p in plans):
            # no cards, or cards without one readable price (the store's markup changed): never publish
            # plans without prices — /shop/ would silently drop them all — keep this region's previous
            # plans (PartialFailure below) and report it
            failed.append(region)
            continue
        for pos, p in enumerate(plans):
            key = p.get("sku") or slugify(p["title"], 40)
            extra = {"pub": pub, "region": region, "listing_url": url, "type": p["type"],
                     "term_months": p["term_months"], "price": p["price"], "currency": p.get("currency") or "USD", "sku": p.get("sku"),
                     "volume": p["volume"], "position": pos, "image_src": p.get("image_src")}
            items.append(make_item(
                id=f"sub:{pub}:{region}:{key}", source=s["source"], kind="subscription", url=p["url"],
                title=p["title"], lang=s["lang"], image=images(p.get("image_src")), category="subscription",
                extra={k: v for k, v in extra.items() if v is not None},
            ))
    if failed:
        raise PartialFailure(items, listings, f"no plans with a price read for region(s) {', '.join(failed)}")
    return items, listings


class PartialFailure(ShopParseError):
    def __init__(self, items, listings, msg):
        super().__init__(msg)
        self.items, self.listings = items, listings


def collect_types(pub: str, plans: list[dict], fetch: Fetch) -> dict[str, dict]:
    """One product page per subscription type (US 1-year plan preferred) → {type: {text, lang, url}}."""
    out = {}
    for typ in TYPES:
        cands = [p for p in plans if (p.get("extra") or {}).get("type") == typ]
        cands.sort(key=lambda p: ((p["extra"].get("region") != "us"), p["extra"].get("term_months") != 12,
                                  p["extra"].get("position", 99)))
        if not cands:
            continue
        html = fetch(cands[0]["url"])
        if not html:
            continue
        try:
            d = parse_product(html, cands[0]["url"])
        except Exception as e:  # noqa: BLE001 — a description is optional
            log.info("%s %s: product page not understood: %s", pub, typ, e)
            continue
        text = short_description(d)
        if text:
            out[typ] = {"text": text, "lang": cands[0].get("lang"), "url": cands[0]["url"]}
    return out


def _page_key(url: str) -> str:
    """One spelling per store page, to tell whether a listing's card is a configured page: the host without
    "www.", the path without a trailing slash, no query."""
    p = urlsplit(url or "")
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/').lower()}"


def collect_specialty(pub: str, s: dict, fetch: Fetch, images: Callable, prev_items: list[dict],
                      today: date | None = None) -> tuple[list[dict], list[str]]:
    """Every configured specialty page of one store → (items, errors).

    One item per kind (cards · planner · calendar · holiday). A product page gives its product with the details
    (description, pack size); a category listing then adds the first card of each kind that no product page gave
    — La Viña's greeting cards, planner and calendar, or this season's holiday cards if their product page has
    moved — and never a product whose own page is in the list (so it is never there twice). A kind named in
    `specialty_skip` is never added (and its previous item is dropped).
    A page that cannot be fetched or read keeps its previous items (matched by the page they were read from), as
    before; it is an error (ok=false, read again the next day) — unless it is a SEASONAL page (all its previous
    items are holiday cards, or its address says so) that is really GONE: not fetched at all (404 …) and not
    shown by any listing read in this run. A store that takes its holiday cards down after the season is not
    failing; one whose holiday page answers in a layout we no longer read, or is down while its listing still
    sells the cards at that address, is. A seasonal item that this run did not find anywhere (its page is gone,
    or the listing it came from no longer shows it) is kept as last read, marked `missing_since` (the first day
    it was missed); build_data leaves it off the site once that is SEASONAL_GRACE_DAYS old, and the next read
    that finds it again clears the mark."""
    pages = [p for p in (s.get("specialty") or []) if p]
    configured = {_page_key(p) for p in pages}
    skip = set(s.get("specialty_skip") or [])
    prev_mine = sorted((i for i in prev_items if i["id"].startswith(f"special:{pub}:")
                        and (i.get("extra") or {}).get("page_url") in pages),
                       key=lambda i: (i["extra"].get("position") if isinstance(i["extra"].get("position"), int) else 99))
    found: dict[str, list[dict]] = {}
    failed: dict[str, Exception] = {}
    for page in pages:
        try:
            html = fetch(page)
            if not html:
                raise PageNotFetched(f"could not fetch {page}")
            found[page] = parse_specialty(html, page)
        except Exception as e:  # noqa: BLE001 — one page never stops the others
            failed[page] = e

    items: list[dict] = []
    covered: set[str] = set()           # the four kinds this store already has in this run ("other" never counts)
    pos = 0

    def add(p: dict, page: str) -> None:
        nonlocal pos
        if p["kind"] in skip:           # the owner's off switch (sources.<pub>.specialty_skip)
            return
        key = p.get("sku") or slugify(p["title"], 40)
        extra = {"pub": pub, "type": p["kind"], "price": p["price"], "currency": p.get("currency") or "USD",
                 "sku": p.get("sku"), "volume": p.get("volume") or [], "trilingual": bool(p.get("trilingual")),
                 "pack": p.get("pack"), "page_url": page, "position": pos, "image_src": p.get("image_src")}
        pos += 1
        if p["kind"] in SPECIALTY_KINDS:
            covered.add(p["kind"])
        items.append(make_item(
            id=f"special:{pub}:{key}", source=s["source"], kind="specialty", url=p["url"], title=p["title"],
            summary=p.get("text") or "", lang=s["lang"], image=images(p.get("image_src")), category="specialty",
            extra={k: v for k, v in extra.items() if v not in (None, "")},
        ))

    for page in pages:                  # 1. products read on their own page
        for p in found.get(page, []):
            if not p.get("listed") and p["kind"] not in covered:
                add(p, page)
    for page in pages:                  # 2. a listing fills in the kinds still missing
        for p in found.get(page, []):
            if p.get("listed") and p["kind"] not in covered and _page_key(p["url"]) not in configured:
                add(p, page)

    # Which failed pages are seasonal ones that are really gone (out of season). A listing that still shows a
    # card at the page's address proves the product is on sale, so that page failing is a real failure — the
    # listing's card does not stand in for it (step 2 never adds a configured address), and nobody would hear
    # of it before build_data dropped the card mid-season.
    def page_kinds(page: str) -> set:
        return {(i.get("extra") or {}).get("type") for i in prev_mine if i["extra"].get("page_url") == page} \
            or {specialty_kind("", page)}
    listed_at = {_page_key(p["url"]) for ps in found.values() for p in ps if p.get("listed")}
    gone = {page for page, e in failed.items() if isinstance(e, PageNotFetched)
            and page_kinds(page) <= set(SEASONAL_KINDS) and _page_key(page) not in listed_at}

    # 3. previous items: a page that failed keeps its items (as before); a seasonal item nobody showed is kept
    #    as out of season. A kind read fresh from another page in this run wins over an old item.
    errors: list[str] = []
    for page, e in failed.items():
        if page in gone:
            log.info("%s specialty %s: %s — out of season (a seasonal page that is gone and that no listing "
                     "shows: not an error; its last good item, if any, is kept)", pub, page, e)
        elif page_kinds(page) <= skip:
            log.info("%s specialty %s: %s — not shown anyway (specialty_skip)", pub, page, e)
        else:
            errors.append(f"{pub} specialty: {e}")
            log.warning("%s specialty %s: %s — keeping the previous items", pub, page, e)
    for it in prev_mine:
        ex = it.get("extra") or {}
        kind, page = ex.get("type"), ex.get("page_url")
        if kind in covered or kind in skip:
            continue
        if kind in SEASONAL_KINDS and (page in gone or page not in failed):
            # out of season: its own page is gone, or the listing it came from was read and no longer shows it
            since = ex.get("missing_since") or (today or date.today()).isoformat()
            items.append({**it, "extra": {**ex, "missing_since": since}})
            log.info("%s specialty: %s not shown by the store — kept as last read, missing since %s",
                     pub, it["id"], since)
        elif page in failed:            # its page failed (an error above): kept as it was, never marked
            items.append(it)
        else:
            continue
        if kind in SPECIALTY_KINDS:
            covered.add(kind)
    return items, errors


def collect(fetch: Fetch, images: Callable, prev: dict, today: date, cfg: dict | None = None,
            refresh_types: bool = False, refresh_specialty: bool = False) -> dict:
    """Everything one run finds → {"items", "errors", "bulk_discounts", "types", "listings", "types_checked",
    "specialty_checked", "stats"}. Parts that failed keep their previous items (prev = the previous raw envelope)."""
    st = settings(cfg)
    prev_items = [i for i in prev.get("items", []) if isinstance(i, dict) and i.get("id")]
    items: list[dict] = []
    errors: list[str] = []
    products: dict[str, dict] = {}
    listings: list[dict] = []
    stats: dict = {}

    def keep_prev(prefix: str) -> None:
        items.extend(i for i in prev_items if i["id"].startswith(prefix))

    for pub, s in st.items():
        try:
            got, prod = collect_botm(pub, s, fetch, images, today)
            items += got
            if prod:
                products[pub] = prod
        except Exception as e:  # noqa: BLE001 — one part never stops the others
            errors.append(f"{pub} book of the month: {e}")
            log.warning("%s book of the month: %s — keeping the previous offer", pub, e)
            keep_prev(f"botm:{pub}")
    for pub, s in st.items():
        try:
            got, ls = collect_subscriptions(pub, s, fetch, images)
            items += got
            listings += ls
        except PartialFailure as e:
            errors.append(f"{pub} subscriptions: {e}")
            items += e.items
            listings += e.listings
            done = {(i["extra"]["region"]) for i in e.items}
            items.extend(i for i in prev_items if i["id"].startswith(f"sub:{pub}:")
                         and (i.get("extra") or {}).get("region") not in done)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{pub} subscriptions: {e}")
            log.warning("%s subscriptions: %s — keeping the previous plans", pub, e)
            keep_prev(f"sub:{pub}:")
            listings += [x for x in (prev.get("listings") or []) if isinstance(x, dict) and x.get("pub") == pub]

    # Bulk-book discounts: printed on every book's product page (GV first, LV as a fallback).
    bulk = dict(prev.get("bulk_discounts") or {})
    for pub in ("gv", "lv"):
        prod = products.get(pub)
        if prod and prod.get("tiers") and not bulk.get("_fresh"):
            bulk.update({"source_url": prod["url"], "tiers": prod["tiers"], "_fresh": True})
    notes = dict(bulk.get("note") or {})
    for pub, lang in (("gv", "en"), ("lv", "es")):
        if (products.get(pub) or {}).get("tiers_note"):
            notes[lang] = products[pub]["tiers_note"]
    if notes:
        bulk["note"] = notes
    bulk.pop("_fresh", None)

    # Type descriptions: monthly (or --refresh-types), from one product page per type.
    types = {k: v for k, v in (prev.get("types") or {}).items() if isinstance(v, dict)}
    checked = parse_iso(prev.get("types_checked"))
    due = refresh_types or checked is None or datetime.now(timezone.utc) - checked > timedelta(days=TYPES_REFRESH_DAYS)
    types_checked = prev.get("types_checked")
    if due:
        all_ok = True
        for pub in st:
            plans = [i for i in items if i.get("kind") == "subscription" and i["id"].startswith(f"sub:{pub}:")]
            if plans:
                got = collect_types(pub, plans, fetch)
                if got:
                    types[pub] = {**(types.get(pub) or {}), **got}
                else:
                    all_ok = False
        # Stamped only when every publication's descriptions were read; else tomorrow's run tries again.
        if all_ok:
            types_checked = now_iso()

    # Specialty items (cards, planner, calendar, holiday cards): weekly (or --refresh-specialty). In between, the
    # previous items are kept as they are — an image the download budget skipped is tried again on those days.
    prev_special = [i for i in prev_items if i["id"].startswith("special:")]
    s_checked = parse_iso(prev.get("specialty_checked"))
    s_due = refresh_specialty or s_checked is None or \
        datetime.now(timezone.utc) - s_checked > timedelta(days=SPECIALTY_REFRESH_DAYS)
    specialty_checked = prev.get("specialty_checked")
    if s_due:
        s_errors: list[str] = []
        for pub, s in st.items():
            got, errs = collect_specialty(pub, s, fetch, images, prev_special, today)
            items += got
            s_errors += errs
        errors += s_errors
        # stamped only when every page was read (a seasonal page out of season counts as read); else the
        # next run tries again
        if not s_errors:
            specialty_checked = now_iso()
    else:
        for it in prev_special:
            src = (it.get("extra") or {}).get("image_src")
            items.append({**it, "image": it.get("image") or images(src)} if src and not it.get("image") else it)

    stats.update({"botm": sum(1 for i in items if i.get("kind") == "botm"),
                  "plans": sum(1 for i in items if i.get("kind") == "subscription"),
                  "specialty": sum(1 for i in items if i.get("kind") == "specialty"),
                  "types_refreshed": bool(due), "specialty_refreshed": bool(s_due)})
    # The seasonal items kept as last read (out of season), on EVERY run: save_raw rewrites the stats each day, and
    # the items keep their mark between the weekly reads (→ status.json sources[].stats; not shown on /status/).
    out_of_season = [i["id"] for i in items
                     if i.get("kind") == "specialty" and (i.get("extra") or {}).get("missing_since")]
    if out_of_season:
        stats["specialty_out_of_season"] = out_of_season
    return {"items": items, "errors": errors, "bulk_discounts": bulk, "types": types,
            "listings": listings, "types_checked": types_checked, "specialty_checked": specialty_checked,
            "stats": stats}


def keep_known_images(items: list[dict], prev_items: list[dict]) -> None:
    """An item whose image was not cached this run (download budget, a failed download) keeps its
    previous cached image when the source image is the same."""
    by_id = {i.get("id"): i for i in prev_items}
    for it in items:
        p = by_id.get(it["id"])
        if not it.get("image") and p and p.get("image") and \
                (p.get("extra") or {}).get("image_src") == (it.get("extra") or {}).get("image_src"):
            it["image"] = p["image"]


def price_memory(items: list[dict], prev: dict, cfg: dict | None, today: date) -> dict:
    """The envelope's `price_memory` (scripts/sync/price_changes.py remember): for each price change AA Grapevine
    announced (config/site.yml price_changes), the 1-year prices it affects — and, when it changes the book prices,
    the Book of the Month's — as this read found them, until the day before it takes effect (a plan or book this
    read did not find keeps its last price); from that day on the prices read before it are kept as they were.
    build_data compares a later read with them: still the same price = the store's page is not updated yet (the
    announced price is shown; a book's prices are not); anything else = the store wins. A mistake in the settings
    only leaves the memory as it was."""
    try:
        changes, _ = PC.specs(cfg if cfg is not None else load_config())
        priced = [i for i in items if i.get("kind") in ("subscription", "botm")]
        return PC.remember(priced, prev.get("price_memory"), changes, today)
    except Exception as e:  # noqa: BLE001 — the memory never stops the store read
        log.warning("price memory not updated (%s: %s) — kept as it was", type(e).__name__, e)
        return prev.get("price_memory") if isinstance(prev.get("price_memory"), dict) else {}


# --------------------------------------------------------------------------- main
def _file_key(url: str) -> str:
    p = urlsplit(url)
    return slugify(f"{p.netloc}{p.path}", 120) + ".html"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print a summary, do not write data/raw")
    ap.add_argument("--no-images", action="store_true", help="do not download product images")
    ap.add_argument("--refresh-types", action="store_true", help="re-read the subscription type descriptions now")
    ap.add_argument("--refresh-specialty", action="store_true",
                    help="re-read the specialty items (cards, planner, calendar, holiday cards) now")
    ap.add_argument("--html-dir", help="read saved pages from this folder instead of fetching (testing)")
    ap.add_argument("--save-html", help="also save every fetched page into this folder (fixtures)")
    args = ap.parse_args(argv)

    prev = load_raw(SOURCE)
    http = shared_session()
    before = http.requests_made

    def fetch(url: str) -> str | None:
        if args.html_dir:
            p = Path(args.html_dir) / _file_key(url)
            return p.read_text(encoding="utf-8") if p.exists() else None
        html = http.get_text(url)
        if html and args.save_html:
            Path(args.save_html).mkdir(parents=True, exist_ok=True)
            (Path(args.save_html) / _file_key(url)).write_text(html, encoding="utf-8")
        return html

    images = ImageCache(http, enabled=not (args.no_images or args.html_dir))
    try:
        tz = ZoneInfo((load_config().get("site") or {}).get("timezone") or "America/Chicago")
    except Exception:  # noqa: BLE001
        tz = ZoneInfo("America/Chicago")
    today = datetime.now(tz).date()
    res = collect(fetch, images, prev, today, refresh_types=args.refresh_types, refresh_specialty=args.refresh_specialty)
    keep_known_images(res["items"], prev.get("items") or [])
    # the clock AFTER the reads: a run that started before midnight never files a price read after it as "before"
    memory = price_memory(res["items"], prev, load_config(), datetime.now(tz).date())
    stats = {**res["stats"], "requests": http.requests_made - before, "images_downloaded": images.downloaded}
    if res["errors"]:
        stats["problems"] = res["errors"]
    if args.dry_run:
        print(json.dumps({**res, "stats": stats, "price_memory": memory}, ensure_ascii=False, indent=1))
        return
    merged, _ = merge_items(prev.get("items") or [], res["items"], drop_missing=True, authoritative=True)
    ok = not res["errors"]
    save_raw(SOURCE, merged, ok=ok, error="; ".join(res["errors"])[:300] if not ok else None, stats=stats,
             extra={"bulk_discounts": res["bulk_discounts"], "types": res["types"], "listings": res["listings"],
                    "types_checked": res["types_checked"], "specialty_checked": res["specialty_checked"],
                    "price_memory": memory})
    log.info("shop: %d offer(s), %d subscription plan(s), %d specialty item(s), %d request(s), %d image(s)%s",
             stats["botm"], stats["plans"], stats["specialty"], stats["requests"], images.downloaded,
             f" — problems: {res['errors']}" if res["errors"] else "")


if __name__ == "__main__":
    raise SystemExit(run_module(SOURCE, main))
