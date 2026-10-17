"""AA Grapevine's announced price changes (config/site.yml `price_changes:`), shared by the store read and the
site data:

  * scripts/sync/shop.py — `remember()`: the last 1-year prices (and Book of the Month prices) read from the
    stores BEFORE each change took effect (data/raw/shop.json `price_memory`), so that after the day the site can
    tell a store page that still shows the old price (not updated yet) from one that shows anything else (the
    store wins);
  * scripts/sync/build_data.py — `specs()` (the settings, checked: a mistake is a reported problem, never a
    crash), `resolve()`: what an affected plan shows from the day the new prices start, and `book_stale()`: a
    Book of the Month read after a book price change took effect that still shows its old price.

One change, as the settings give it (README → "When Grapevine announces new prices"):
    key            a short name (letters, numbers, dashes) — default: the effective month, "2027-01"
    effective      the day the new prices start (Central time)                       — required
    announced      the day AA Grapevine announced them: the notice shows from this day — default: the effective day
                   (no advance notice)
    notice_until   the last day of the "New prices since …" notice                   — default: 30 days after `effective`
    source         where they were announced ("AA Grapevine's letter …"); source_es in Spanish
    doc_match      finds AA Grapevine's notice among the committee's Drive files (a regular expression, capitals
                   ignored — like lavina_weekly_open.flyer_match)
    yearly         the new prices of the 1-YEAR subscriptions, U.S. dollars: {gv|lv: {print|digital|complete: 39.00}}
    books_more     how much more every Grapevine and La Viña book costs from that day (U.S. dollars)

Only what the announcement says is changed: a 1-year plan of the publication and format named in `yearly`, in
every region the stores list it for (the 2- and 3-year, monthly and other plans keep the stores' prices). Books
have no announced price of their own: before the day the site says "{books_more} more"; after it, the stores'
prices (the Book of the Month is read again on the 1st) — once they differ from the ones read before the day, or
a new book starts (book_stale).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .common import clean_text, slugify

PUBS = ("gv", "lv")
TYPES = ("print", "digital", "complete")
YEARLY_MONTHS = 12
MAX_PRICE = 1000.0          # a price above this is a typo (the dearest plan, 3-year Complete, is $130)
NOTICE_DAYS = 30            # no notice_until: the "New prices since …" notice shows for this many days
KEY_MAX = 32
# How long the price memory of a change that is no longer in the settings is kept (a block that a typo made
# unreadable must not lose the prices read before its day: they cannot be read again afterwards).
MEMORY_KEEP_DAYS = 400


def _day(v: Any) -> date | None:
    """A day from the settings: an unquoted 2027-01-01 (YAML gives a date) or the text "2027-01-01"."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = clean_text(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None
    return None


def money(v: Any) -> float | None:
    """39, 39.0, "39.00" or "$39.00" → 39.0; anything else (a word, 0, a negative or absurd amount) → None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        n = float(str(v).strip().lstrip("$").replace(",", "")) if isinstance(v, str) else float(v)
    except (TypeError, ValueError):
        return None
    if not 0 < n <= MAX_PRICE:
        return None
    return round(n, 2)


def day_start(d: date, tz: ZoneInfo) -> str:
    """00:00 on day `d` in the site's time zone, as a UTC instant: 2027-01-01 → "2027-01-01T06:00:00Z" (CST).
    The pages switch at these moments (app.js GV.expire: data-gv-from / data-gv-expire)."""
    return datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def specs(cfg: dict | None) -> tuple[list[dict], list[str]]:
    """config/site.yml `price_changes:` → (the changes, soonest effective day first; problems).

    Hand-edited settings, read like recurring_events: a change with a real mistake (no effective day, nothing to
    change, a key used twice) is SKIPPED and named in the problems; a smaller slip (an announced or notice_until
    day that is not a date, one price that is not a price, a pattern that is not valid) is noted and the rest of
    the change still applies. Never raises."""
    raw = (cfg or {}).get("price_changes")
    if raw is None or raw == "" or raw == []:
        return [], []
    if isinstance(raw, dict):              # a single change written without the leading "- "
        raw = [raw]
    if not isinstance(raw, list):
        return [], ["price_changes: not understood — it must be a list, each change starting with “- key:”"]
    out: list[dict] = []
    problems: list[str] = []
    seen: set[str] = set()
    for n, e in enumerate(raw, 1):
        if not isinstance(e, dict):
            problems.append(f"price_changes entry {n}: not understood (its settings must be indented under “- key:”)"
                            f" — skipped")
            continue
        try:
            spec, errors, notes = _one(e)
        except Exception as ex:  # noqa: BLE001 — a setting never stops the build
            spec, errors, notes = None, [f"not understood ({type(ex).__name__})"], []
        # the entry's name in a problem: its key, else its effective day as written (slugify("") would say "item")
        raw_key = clean_text(e.get("key"))
        key = (spec or {}).get("key") or (slugify(raw_key, KEY_MAX).strip("-") if raw_key else "")
        name = f"price_changes entry {n} ({key or clean_text(e.get('effective')) or 'no name'})"
        if spec and spec["key"] in seen:
            errors.append(f"the key “{spec['key']}” is used twice (each change needs its own)")
        if errors or spec is None:
            problems.append(f"{name}: " + "; ".join(errors or ["not understood"]) + " — skipped")
            continue
        if notes:
            problems.append(f"{name}: " + "; ".join(notes))
        seen.add(spec["key"])
        out.append(spec)
    out.sort(key=lambda s: (s["effective"], s["key"]))
    return out, problems


def _one(e: dict) -> tuple[dict | None, list[str], list[str]]:
    """One entry → (the change or None, errors that skip it, notes)."""
    errors: list[str] = []
    notes: list[str] = []

    def given(k: str) -> bool:
        return e.get(k) not in (None, "")

    effective = _day(e.get("effective"))
    if effective is None:
        errors.append(f"effective “{clean_text(e.get('effective'))}” is not a date like \"2027-01-01\"" if given("effective")
                      else "it needs effective: the day the new prices start (like \"2027-01-01\")")
        return None, errors, notes
    key = slugify(clean_text(e.get("key")), KEY_MAX).strip("-") if clean_text(e.get("key")) else ""
    key = key or effective.isoformat()[:7]

    announced = _day(e.get("announced"))
    if given("announced") and announced is None:
        notes.append(f"announced “{clean_text(e.get('announced'))}” is not a date like \"2026-10-01\" — no notice before "
                     f"the effective day")
    if announced is None or announced > effective:
        if announced is not None:
            notes.append(f"announced {announced.isoformat()} is after effective {effective.isoformat()} — the notice "
                         f"starts on the effective day")
        announced = effective
    until = _day(e.get("notice_until"))
    default_until = effective + timedelta(days=NOTICE_DAYS)
    if given("notice_until") and until is None:
        notes.append(f"notice_until “{clean_text(e.get('notice_until'))}” is not a date like \"2027-01-31\" — the "
                     f"notice ends {default_until.isoformat()}")
    elif until is not None and until < effective:
        notes.append(f"notice_until {until.isoformat()} is before effective {effective.isoformat()} — the notice "
                     f"ends {default_until.isoformat()}")
        until = None
    until = until or default_until

    yearly: dict[tuple[str, str], float] = {}
    raw_y = e.get("yearly")
    if raw_y not in (None, "", {}) and not isinstance(raw_y, dict):
        notes.append("yearly: not understood — write it like  gv: { print: 39.00, digital: 34.00 }")
        raw_y = {}
    for pub, kinds in (raw_y or {}).items():
        p = clean_text(pub).lower()
        if p not in PUBS:
            notes.append(f"yearly: “{clean_text(pub)}” is not gv or lv — left out")
            continue
        if not isinstance(kinds, dict):
            notes.append(f"yearly {p}: not understood — write it like  {p}: {{ print: 39.00 }}")
            continue
        for typ, price in kinds.items():
            t = clean_text(typ).lower()
            if t not in TYPES:
                notes.append(f"yearly {p}: “{clean_text(typ)}” is not print, digital or complete — left out")
                continue
            v = money(price)
            if v is None:
                notes.append(f"yearly {p} {t}: “{clean_text(price)}” is not a price like 39.00 — left out")
                continue
            yearly[(p, t)] = v
    books = 0.0
    if given("books_more"):
        b = money(e.get("books_more"))
        if b is None:
            notes.append(f"books_more “{clean_text(e.get('books_more'))}” is not an amount like 2.00 — left out")
        else:
            books = b
    if not yearly and not books:
        errors.append("it changes no price (no valid yearly price and no books_more)")
        return None, errors, notes

    pattern = clean_text(e.get("doc_match"))
    if pattern:
        try:
            re.compile(pattern)
        except re.error:
            notes.append(f"doc_match “{pattern}” is not a valid pattern — no link to the notice")
            pattern = ""
    return {
        "key": key, "effective": effective, "announced": announced, "notice_until": until,
        "source": (clean_text(e.get("source")), clean_text(e.get("source_es"))),
        "doc_match": pattern, "yearly": yearly, "books_more": books,
    }, errors, notes


def new_price(change: dict, pub: Any, typ: Any, term_months: Any) -> float | None:
    """The announced price of a plan (a 1-year plan of a publication and format the change names), else None."""
    try:
        months = int(term_months)
    except (TypeError, ValueError):
        return None
    if months != YEARLY_MONTHS:
        return None
    return change["yearly"].get((str(pub), str(typ)))


def mem_key(change: dict) -> str:
    """A change's place in the price memory: its effective day (a renamed key keeps the memory)."""
    return change["effective"].isoformat()


def book_key(item_id: Any, sku: Any) -> str:
    """A Book of the Month's place in the price memory: the offer AND its book — "botm:gv:GV31" (the offer's id is
    the same every month; a new book starts on the 15th). "" without a SKU (one book cannot be told from the
    next: not remembered)."""
    s = clean_text(sku)
    return f"{item_id}:{s}" if item_id and s else ""


def remember(items: list[dict], prev: Any, changes: list[dict], today: date) -> dict[str, dict[str, float]]:
    """The price memory (data/raw/shop.json `price_memory`): {effective day: {key: price}} — for each change, the
    prices it affects as the stores showed them BEFORE its day: each 1-year plan it names (key: the subscription
    item id) and, when it changes the book prices (books_more), the Book of the Month's regular price (book_key).
    Every read until the day before updates the prices it found; a plan or book it did not find (one card missing
    from a listing that day, a listing that did not answer) keeps its last price, and the changes that start on
    the same day share one memory — so after the day no plan loses the price it had. From the effective day on it
    is frozen (`prev` kept as it was). The memory of a change no longer in the settings is kept for
    MEMORY_KEEP_DAYS after its day (a typo that makes the block unreadable must not lose it), then dropped.
    `items` are the run's store items (shop.py): subscriptions (extra.pub / type / term_months / price) and Book
    of the Month offers (extra.sku / price); others are ignored."""
    prev = prev if isinstance(prev, dict) else {}
    out: dict[str, dict[str, float]] = {}
    for k, v in prev.items():
        d = _day(k)
        if d is not None and isinstance(v, dict) and today - d <= timedelta(days=MEMORY_KEEP_DAYS):
            out[k] = dict(v)
    done: set[str] = set()          # the days this read has already updated (two changes on one day: one memory)
    for c in changes:
        k = mem_key(c)
        old = {i: p for i, p in prev[k].items() if money(p) is not None} if isinstance(prev.get(k), dict) else {}
        if today >= c["effective"]:
            if old:
                out[k] = old
            else:
                out.pop(k, None)
            continue
        acc = out.get(k, {}) if k in done else dict(old)
        for it in items:
            ex = it.get("extra") or {}
            price = money(ex.get("price"))
            if not it.get("id") or price is None:
                continue
            if it.get("kind") == "subscription" and new_price(c, ex.get("pub"), ex.get("type"), ex.get("term_months")):
                acc[it["id"]] = price
            elif it.get("kind") == "botm" and c["books_more"] and (bk := book_key(it["id"], ex.get("sku"))):
                acc[bk] = price
        done.add(k)
        # nothing read and nothing known (the stores' listings did not answer and there were no older prices)
        if acc:
            out[k] = acc
        else:
            out.pop(k, None)
    return out


def resolve(change: dict, new: float, item_id: Any, price: float | None, memory: Any, today: date,
            read_before: bool = False) -> tuple[float, bool]:
    """What an affected plan shows from the change's effective day → (price, stale). `new` is its announced price.

    `stale`: the synced store price is still the one from before the change — read before the day (`today` is
    before it, or `read_before`: the stores have not been read since the day began), or read on or after it
    but equal to the last price read before it (`memory`, shop.py: the store's own page not updated yet). Then
    the announced price is shown. Once the store shows anything else after the day, the store's price wins
    (stale False). A plan the memory does not know (a new product) follows the store too."""
    if today < change["effective"] or read_before:
        return new, True
    mem = memory.get(mem_key(change)) if isinstance(memory, dict) else None
    was = money(mem.get(item_id)) if isinstance(mem, dict) and item_id else None
    if was is not None and price is not None and abs(price - was) < 0.005:
        return new, True
    return (price if price is not None else new), False


def book_stale(changes: list[dict], item_id: Any, sku: Any, price: Any, read: date | None, memory: Any,
               today: date) -> bool:
    """A Book of the Month read ON or AFTER the day of the latest book price change in effect (books_more) whose
    regular price is still the one read before that day (`memory`, the same book: book_key) — the store's page not
    updated yet. Its prices are then not shown, like those of a read made before the day (eleventy/filters/shop.js
    botmPriceState: no "you save" sum on an old price). The store's prices show again once its regular price is
    anything else, or a new book starts (another SKU, on the 15th). A read before the day → False (the pages
    already leave its prices out)."""
    done = [c for c in changes if c["books_more"] and c["effective"] <= today]
    if not done or read is None or read < done[-1]["effective"]:
        return False
    c = done[-1]                                       # (specs are sorted by effective day)
    mem = memory.get(mem_key(c)) if isinstance(memory, dict) else None
    bk = book_key(item_id, sku)
    was = money(mem.get(bk)) if isinstance(mem, dict) and bk else None
    now = money(price)
    return was is not None and now is not None and abs(now - was) < 0.005
