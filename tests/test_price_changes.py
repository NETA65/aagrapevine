"""Price changes AA Grapevine announces (config/site.yml `price_changes:`) — the January 1, 2027 change:

  * Settings — scripts/sync/price_changes.py `specs`: the block is read and checked; a mistake is skipped or
    corrected and reported (status.json problems.price_changes → a Settings problem in the Actions run
    summary), never a crash;
  * Memory — the last 1-year prices read before the day (shop.py price_memory → price_changes.remember), frozen
    from the day on;
  * SiteData — build_data.build_shop: each affected 1-year plan's `change` {key, new, stale} — stale while the
    store data is from before the day, or was read after it and still shows the old price (the store's page not
    updated yet); the store wins once it shows anything else — and `price_changes[]` (the moments the pages
    switch, 00:00 Central; the notice's rows);
  * Pages — eleventy/filters/shop.js: both states around the day (Dec 31, 11:59 PM and Jan 1, 0:00 Central), each
    in its window; the Book of the Month never shows a "you save" sum on an old price; the notices' windows;
    stale and updated store data; after the notice ends;
  * Browser — app.js GV.expire (data-gv-from / data-gv-expire) and base.njk's head script switch at the moment,
    in a browser in any time zone;
  * Report, Monthly, Digest — the GV/LV report (its shop section, and its text from the day: report.js
    swapTexts), the monthly toolkit's message, the monthly digest's pointer row and its e-mail twin
    (send_digest.py) in the months before and in January;
  * Announcements — the two bulletin posts (dates, publish, expires, pinned, their own Spanish over several
    lines), the letter on Drive (its date and title), the hand translations in data/translations/overrides.yml.

    python -m unittest tests.test_price_changes -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from nodejs import run_js  # noqa: E402
import test_monthly as TM  # noqa: E402  (its October 2026 data set and site settings)
import test_send_digest as SD  # noqa: E402  (its e-mail digest fixture)
from scripts.notify import send_digest as SDM  # noqa: E402
from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import drive as D  # noqa: E402
from scripts.sync import price_changes as PC  # noqa: E402
from scripts.sync import shop as S  # noqa: E402
from scripts.sync import translate as T  # noqa: E402
from scripts.sync.common import load_config  # noqa: E402
from scripts.sync.drive_listing import Entry  # noqa: E402

E_AT = "2027-01-01T06:00:00Z"          # 00:00 Central (CST) on January 1, 2027: the new prices
N_AT = "2027-02-01T06:00:00Z"          # 00:00 Central on February 1: the "New prices since …" notice is over
DEC31_2359 = "2027-01-01T05:59:00Z"    # 11:59 PM Central on December 31
JAN1_0000 = E_AT
NEW_NAME = "2026-10-01 Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf"
OLD_NAME = "Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf"

CHANGE = {"key": "2027-01", "effective": "2027-01-01", "announced": "2026-10-01", "notice_until": "2027-01-31",
          "source": "AA Grapevine's letter to Intergroups and Central Offices, October 1, 2026",
          "source_es": "Carta de AA Grapevine a las oficinas intergrupales y centrales, 1 de octubre de 2026",
          "doc_match": "pricing update.*2027|actualizaci[oó]n de precios.*2027",
          "yearly": {"gv": {"print": 39.00, "digital": 34.00}, "lv": {"print": 19.50, "digital": 17.00}},
          "books_more": 2.00}


def plan(pub: str, region: str, sku: str, typ: str, months: int, price: float, pos: int, volume=None) -> dict:
    return {"id": f"sub:{pub}:{region}:{sku}", "kind": "subscription", "title": f"{sku} plan", "lang": "en",
            "url": f"https://www.aagrapevine.org/store/{sku.lower()}",
            "extra": {"pub": pub, "region": region, "type": typ, "term_months": months, "price": price, "sku": sku,
                      "currency": "USD", "position": pos, "volume": volume or []}}


VOL = [{"min": 2, "max": 19, "price": 35.5}, {"min": 20, "max": None, "price": 35.0}]
PLANS = [
    plan("gv", "us", "GVUS1", "print", 12, 36.0, 0, VOL), plan("gv", "us", "GVUS2", "print", 24, 68.0, 1,
                                                            [{"min": 2, "max": 19, "price": 67.5}]),
    plan("gv", "us", "GVUS3", "print", 36, 90.0, 2), plan("gv", "us", "GO1M", "digital", 1, 2.99, 3),
    plan("gv", "us", "GO1Y", "digital", 12, 29.99, 4), plan("gv", "us", "GVV1Y", "complete", 12, 56.0, 5),
    plan("gv", "intl", "GOINTL1", "digital", 12, 29.99, 0),
    plan("lv", "us", "LVUS1", "print", 12, 18.0, 0), plan("lv", "us", "LO1A", "digital", 12, 14.99, 1),
]
MEMORY = {"2027-01-01": {"sub:gv:us:GVUS1": 36.0, "sub:gv:us:GO1Y": 29.99, "sub:gv:intl:GOINTL1": 29.99,
                         "sub:lv:us:LVUS1": 18.0, "sub:lv:us:LO1A": 14.99}}


def botm(read: str | None) -> dict:
    ex = {"pub": "gv", "page_url": "https://www.aagrapevine.org/BOTM", "price": 14.99, "sale_price": 11.99,
          "discount_pct": 20, "currency": "USD", "sku": "GV31", "starts": "2026-12-15", "ends": "2027-01-14", "month": 1,
          "month_label": "January"}
    if read:
        ex["read"] = read
    return {"id": "botm:gv", "kind": "botm", "title": "No Matter What", "summary": "Stories about adversity.", "lang": "en",
            "url": "https://www.aagrapevine.org/store/no-matter-what", "extra": ex}


def config(*changes) -> dict:
    cfg = copy.deepcopy(load_config())
    cfg["price_changes"] = list(changes) if changes else [copy.deepcopy(CHANGE)]
    return cfg


def ctx_at(now: str, items: list[dict], memory=None, attempted: str | None = None, cfg: dict | None = None) -> B.Ctx:
    c = B.Ctx(offline=True)
    c.cfg = cfg if cfg is not None else config()
    c.now = datetime.fromisoformat(now.replace("Z", "+00:00"))
    c.now_ts = c.now.timestamp()
    c.today_local = c.now.astimezone(c.tz).date()
    env = {"items": items, "updated": attempted, "attempted": attempted}
    if memory is not None:
        env["price_memory"] = memory
    c.raw = {"shop": env}
    return c


def shop_doc(now: str, items: list[dict] | None = None, memory=None, attempted: str | None = None) -> dict:
    """data/site/shop.json as build_data writes it at `now` (Central)."""
    c = ctx_at(now, items if items is not None else PLANS + [botm("2026-12-31")], memory, attempted)
    i18n = B.I18n(None)
    doc, wanted = B.build_shop(c, i18n)
    B.finish_shop(doc, wanted, i18n)
    return json.loads(json.dumps(doc, default=list))


def priced(items: list[dict], prices: dict[str, float]) -> list[dict]:
    """The same plans with some prices as a later store read found them."""
    out = copy.deepcopy(items)
    for it in out:
        if it["id"] in prices:
            it["extra"]["price"] = prices[it["id"]]
    return out


def rows(doc: dict) -> dict[str, dict]:
    return {f"{s['pub']}:{s['region']}:{p['sku']}": p for s in doc["subscriptions"] for p in s["plans"]}


# =========================================================================== settings
class Settings(unittest.TestCase):
    def test_the_settings_file_has_no_mistakes(self):
        # Only "no mistakes": the chair adds the next block or deletes this one (config/site.yml, README) — neither
        # may turn the Code check red. The values are checked on the block as written (CHANGE, below).
        cfg = load_config()
        if not cfg.get("price_changes"):
            self.skipTest("config/site.yml has no price_changes block")
        changes, problems = PC.specs(cfg)
        self.assertEqual(problems, [])
        self.assertTrue(changes)

    def test_the_january_2027_block(self):
        changes, problems = PC.specs({"price_changes": [copy.deepcopy(CHANGE)]})
        self.assertEqual(problems, [])
        self.assertEqual(len(changes), 1)
        c = changes[0]
        self.assertEqual((c["key"], c["effective"], c["announced"], c["notice_until"]),
                         ("2027-01", date(2027, 1, 1), date(2026, 10, 1), date(2027, 1, 31)))
        self.assertEqual(c["yearly"], {("gv", "print"): 39.0, ("gv", "digital"): 34.0, ("lv", "print"): 19.5, ("lv", "digital"): 17.0})
        self.assertEqual(c["books_more"], 2.0)
        self.assertEqual(c["source"][0], "AA Grapevine's letter to Intergroups and Central Offices, October 1, 2026")
        self.assertTrue(c["source"][1].startswith("Carta de AA Grapevine"))
        # the pattern finds the letter by its new and its old file name, and by the Spanish title
        for text in (NEW_NAME, OLD_NAME, "Actualización de precios de Grapevine y La Viña - A partir del 1 de enero de 2027"):
            self.assertRegex(text, re.compile(c["doc_match"], re.I))
        self.assertNotRegex("Grapevine Area Chair Meeting Agenda", re.compile(c["doc_match"], re.I))

    def test_an_entry_without_a_key_is_named_by_its_day(self):
        _, problems = PC.specs({"price_changes": [{"effective": "2027-13-40", "yearly": {"gv": {"print": 40}}},
                                                  {"effective": "2027-02-01"}, {"yearly": {"gv": {"print": 40}}}]})
        self.assertEqual(len(problems), 3, problems)
        self.assertTrue(problems[0].startswith("price_changes entry 1 (2027-13-40): effective “2027-13-40” is not a date"))
        self.assertTrue(problems[1].startswith("price_changes entry 2 (2027-02-01): it changes no price"))
        self.assertTrue(problems[2].startswith("price_changes entry 3 (no name): it needs effective"))
        self.assertFalse(any("(item)" in p for p in problems))

    def test_mistakes_are_skipped_or_noted_never_raised(self):
        cfg = {"price_changes": [
            {"key": "a", "announced": "2026-10-01", "yearly": {"gv": {"print": 39}}},                  # no effective
            {"key": "b", "effective": "2027-13-01", "yearly": {"gv": {"print": 39}}},                 # not a date
            {"key": "c", "effective": "2027-01-01"},                                                  # changes nothing
            {"key": "d", "effective": date(2027, 1, 1), "announced": "soon", "notice_until": "2026-12-01",
             "yearly": {"gv": {"print": "thirty", "paper": 3, "digital": "$34.00"}, "xx": {"print": 1}, "lv": "19.50"},
             "books_more": "two", "doc_match": "("},
            {"key": "d", "effective": "2027-02-01", "books_more": 1},                                 # the key again
            "oops",
        ]}
        changes, problems = PC.specs(cfg)
        self.assertEqual([c["key"] for c in changes], ["d"])
        d = changes[0]
        self.assertEqual(d["announced"], date(2027, 1, 1), "no readable announced day: no notice before the day")
        self.assertEqual(d["notice_until"], date(2027, 1, 31), "notice_until before the day: 30 days")
        self.assertEqual(d["yearly"], {("gv", "digital"): 34.0})
        self.assertEqual((d["books_more"], d["doc_match"]), (0.0, ""))
        text = " | ".join(problems)
        self.assertEqual(len(problems), 6, problems)
        for needle in ("entry 1 (a): it needs effective", "entry 2 (b): effective “2027-13-01” is not a date",
                       "entry 3 (c): it changes no price", "announced “soon” is not a date", "notice_until 2026-12-01 is before",
                       "yearly gv print: “thirty” is not a price", "yearly gv: “paper” is not print, digital or complete",
                       "yearly: “xx” is not gv or lv", "yearly lv: not understood", "books_more “two” is not an amount",
                       "doc_match “(” is not a valid pattern", "the key “d” is used twice", "entry 6: not understood"):
            self.assertIn(needle, text)
        self.assertTrue(all(p.endswith("— skipped") for p in problems if "(a)" in p or "(b)" in p or "(c)" in p))

    def test_other_shapes(self):
        self.assertEqual(PC.specs({}), ([], []))
        self.assertEqual(PC.specs({"price_changes": []}), ([], []))
        changes, problems = PC.specs({"price_changes": "yes"})
        self.assertEqual(changes, [])
        self.assertIn("must be a list", problems[0])
        # one change written without the leading "- "; announced after effective → the notice starts on the day
        changes, problems = PC.specs({"price_changes": {"effective": "2027-03-01", "announced": "2027-04-01",
                                                        "books_more": 1.5}})
        self.assertEqual((changes[0]["key"], changes[0]["announced"], changes[0]["books_more"]), ("2027-03", date(2027, 3, 1), 1.5))
        self.assertIn("is after effective", problems[0])

    def test_a_mistake_never_stops_the_build_and_is_reported(self):
        c = ctx_at("2026-10-02T15:00:00Z", PLANS, cfg=config({"key": "x", "effective": "someday"}, copy.deepcopy(CHANGE)))
        doc, _ = B.build_shop(c, B.I18n(None))
        self.assertEqual([p["key"] for p in doc["price_changes"]], ["2027-01"], "the good block still applies")
        self.assertTrue(c.raw_problems["price_changes"].startswith("config/site.yml price_changes entry 1 (x): effective “someday”"))
        st = B.build_status(c, None, B.I18n(None), {}, False, 0.0)
        self.assertIn("price_changes", st["problems"])
        # even a broken shape
        c2 = ctx_at("2026-10-02T15:00:00Z", PLANS, cfg={**config(), "price_changes": 42})
        doc2, _ = B.build_shop(c2, B.I18n(None))
        self.assertEqual(doc2["price_changes"], [])
        self.assertIn("must be a list", c2.raw_problems["price_changes"])

    def test_the_run_summary_names_the_problem(self):
        wf = yaml.safe_load((ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8"))
        step = next(s for s in wf["jobs"]["sync"]["steps"] if s.get("name") == "Write run summary")
        code = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        tmp = Path(tempfile.mkdtemp(prefix="gv-pc-summary-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "data" / "site").mkdir(parents=True)
        status = {"fixture": False, "sources": [], "problems": {
            "price_changes": "config/site.yml price_changes entry 1 (2027-01): yearly gv print: “thirty” is not a price like 39.00 — left out"}}
        (tmp / "data" / "site" / "status.json").write_text(json.dumps(status), encoding="utf-8")
        (tmp / "script.py").write_text(code, encoding="utf-8")
        env = dict(os.environ, GITHUB_STEP_SUMMARY=str(tmp / "summary.md"), GITHUB_OUTPUT=str(tmp / "out.txt"),
                   PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("::warning title=Settings problem (price_changes)::config/site.yml price_changes entry 1", r.stdout)
        self.assertIn("- config/site.yml price_changes entry 1 (2027-01): yearly gv print", (tmp / "summary.md").read_text(encoding="utf-8"))


# =========================================================================== the price memory
class Memory(unittest.TestCase):
    def setUp(self):
        self.changes, _ = PC.specs(config())

    def test_before_the_day_it_follows_each_read(self):
        mem = PC.remember(PLANS, {}, self.changes, date(2026, 12, 31))
        self.assertEqual(mem, MEMORY, "only the 1-year print / digital plans the change names (not 2-year, monthly, Complete)")
        later = PC.remember(priced(PLANS, {"sub:gv:us:GVUS1": 37.0}), mem, self.changes, date(2026, 12, 31))
        self.assertEqual(later["2027-01-01"]["sub:gv:us:GVUS1"], 37.0)

    def test_from_the_day_it_is_frozen(self):
        mem = PC.remember(priced(PLANS, {"sub:gv:us:GVUS1": 39.0}), MEMORY, self.changes, date(2027, 1, 1))
        self.assertEqual(mem, MEMORY)
        self.assertEqual(PC.remember(PLANS, {}, self.changes, date(2027, 1, 2)), {}, "nothing to remember after the day")

    def test_a_plan_missing_from_the_last_read_keeps_its_price(self):
        # December 31: the Canada listing answered, but without its 1-year print card that day
        ca = plan("gv", "ca", "GVCAN1", "print", 12, 36.0, 0)
        dec30 = PC.remember(PLANS + [ca], {}, self.changes, date(2026, 12, 30))
        dec31 = PC.remember(priced(PLANS, {"sub:gv:us:GVUS1": 36.5}), dec30, self.changes, date(2026, 12, 31))
        self.assertEqual(dec31["2027-01-01"]["sub:gv:ca:GVCAN1"], 36.0, "not read that day: its last price is kept")
        self.assertEqual(dec31["2027-01-01"]["sub:gv:us:GVUS1"], 36.5, "read that day: the new reading")
        c = self.changes[0]
        self.assertEqual(PC.resolve(c, 39.0, "sub:gv:ca:GVCAN1", 36.0, dec31, date(2027, 1, 2)), (39.0, True),
                         "back on January 2 at the old price: still the store's old page, the new price shows")

    def test_two_changes_on_one_day_share_the_memory(self):
        changes, problems = PC.specs({"price_changes": [
            {"key": "gv-2027", "effective": "2027-01-01", "yearly": {"gv": {"print": 39}}},
            {"key": "lv-2027", "effective": "2027-01-01", "yearly": {"lv": {"print": 19.5}}}]})
        self.assertEqual(problems, [])
        mem = PC.remember(PLANS, {}, changes, date(2026, 12, 31))
        self.assertEqual(mem, {"2027-01-01": {"sub:gv:us:GVUS1": 36.0, "sub:lv:us:LVUS1": 18.0}})
        gv = next(c for c in changes if c["key"] == "gv-2027")
        self.assertEqual(PC.resolve(gv, 39.0, "sub:gv:us:GVUS1", 36.0, mem, date(2027, 1, 2)), (39.0, True))
        again = PC.remember(priced(PLANS, {"sub:lv:us:LVUS1": 18.5}), mem, changes, date(2026, 12, 31))
        self.assertEqual(again["2027-01-01"], {"sub:gv:us:GVUS1": 36.0, "sub:lv:us:LVUS1": 18.5})

    def test_the_book_of_the_month_is_remembered_by_its_book(self):
        mem = PC.remember(PLANS + [botm("2026-12-31")], {}, self.changes, date(2026, 12, 31))
        self.assertEqual(mem["2027-01-01"]["botm:gv:GV31"], 14.99, "its regular price, by the offer and its book")
        no_books = PC.specs({"price_changes": [{**copy.deepcopy(CHANGE), "books_more": None}]})[0]
        self.assertNotIn("botm:gv:GV31", PC.remember(PLANS + [botm("2026-12-31")], {}, no_books, date(2026, 12, 31))["2027-01-01"],
                         "a change that leaves the books alone does not remember them")
        nosku = botm("2026-12-31")
        del nosku["extra"]["sku"]
        self.assertEqual(PC.book_key("botm:gv", None), "")
        self.assertNotIn("botm:gv:", "".join(PC.remember([nosku], {}, self.changes, date(2026, 12, 31)).get("2027-01-01", {})))
        self.assertEqual(S.price_memory(PLANS + [botm("2026-12-31")], {}, config(), date(2026, 12, 31))["2027-01-01"]["botm:gv:GV31"], 14.99,
                         "the store read passes the offers too")

    def test_a_block_that_is_gone_or_unreadable_keeps_the_memory_for_a_while(self):
        self.assertEqual(PC.remember(PLANS, MEMORY, [], date(2027, 1, 5)), MEMORY)
        self.assertEqual(PC.remember(PLANS, MEMORY, [], date(2028, 3, 1)), {}, "dropped 400 days after its day")
        prev = {"price_memory": MEMORY}
        self.assertEqual(S.price_memory(PLANS, prev, {"price_changes": "nonsense"}, date(2027, 1, 5)), MEMORY)
        self.assertEqual(S.price_memory(PLANS, {}, config(), date(2026, 11, 1)), MEMORY)

    def test_the_store_read_writes_the_memory_and_the_offer_its_day(self):
        src = (ROOT / "scripts" / "sync" / "shop.py").read_text(encoding="utf-8")
        self.assertIn('"price_memory": memory', src)
        self.assertIn('memory = price_memory(res["items"], prev, load_config(), datetime.now(tz).date())', src)
        self.assertIn('"read": today.isoformat()', src)


# =========================================================================== the site data
class SiteData(unittest.TestCase):
    def test_before_the_day(self):
        doc = shop_doc("2026-12-31T23:00:00Z")
        r = rows(doc)
        self.assertEqual(r["gv:us:GVUS1"]["change"], {"key": "2027-01", "new": 39.0, "stale": True})
        self.assertEqual(r["gv:us:GO1Y"]["change"], {"key": "2027-01", "new": 34.0, "stale": True})
        self.assertEqual(r["gv:intl:GOINTL1"]["change"]["new"], 34.0, "every region the stores list it for")
        self.assertEqual(r["lv:us:LVUS1"]["change"]["new"], 19.5)
        for sku in ("gv:us:GVUS2", "gv:us:GVUS3", "gv:us:GO1M", "gv:us:GVV1Y"):
            self.assertNotIn("change", r[sku], "only the 1-year plans the announcement names")
        self.assertEqual(r["gv:us:GVUS1"]["price"], 36.0, "the store's own price is never overwritten")
        pc = doc["price_changes"][0]
        self.assertEqual(pc["at"], {"announced": "2026-10-01T05:00:00Z", "effective": E_AT, "notice_end": N_AT})
        self.assertEqual([(y["pub"], y["type"], y["now"], y["new"], y["after"]) for y in pc["yearly"]],
                         [("gv", "print", 36.0, 39.0, 39.0), ("gv", "digital", 29.99, 34.0, 34.0),
                          ("lv", "print", 18.0, 19.5, 19.5), ("lv", "digital", 14.99, 17.0, 17.0)])
        self.assertEqual((pc["books_more"], pc["source_lang"]), (2.0, {"en": "en", "es": "es"}))
        self.assertEqual(doc["botm"][0]["read"], "2026-12-31")

    def test_on_the_day_before_any_new_read(self):
        # the morning of January 1: the stores were last read on December 31
        doc = shop_doc("2027-01-01T08:00:00Z", memory=MEMORY, attempted="2026-12-31T13:00:00Z")
        self.assertTrue(all(p["change"]["stale"] for p in rows(doc).values() if "change" in p))
        doc = shop_doc("2027-01-01T08:00:00Z", memory={}, attempted="2026-12-31T13:00:00Z")
        self.assertTrue(rows(doc)["gv:us:GVUS1"]["change"]["stale"], "without a memory the read day still tells")

    def test_read_on_the_day_the_store_not_updated_yet(self):
        doc = shop_doc("2027-01-01T11:00:00Z", memory=MEMORY, attempted="2027-01-01T10:30:00Z")
        r = rows(doc)
        self.assertTrue(r["gv:us:GVUS1"]["change"]["stale"])
        self.assertEqual(doc["price_changes"][0]["yearly"][0]["after"], 39.0)

    def test_the_store_updated_or_with_another_price_wins(self):
        items = priced(PLANS, {"sub:gv:us:GVUS1": 39.0, "sub:gv:us:GO1Y": 33.5})
        doc = shop_doc("2027-01-02T11:00:00Z", items, memory=MEMORY, attempted="2027-01-02T10:30:00Z")
        r = rows(doc)
        self.assertEqual((r["gv:us:GVUS1"]["change"]["stale"], r["gv:us:GVUS1"]["price"]), (False, 39.0))
        self.assertEqual((r["gv:us:GO1Y"]["change"]["stale"], r["gv:us:GO1Y"]["price"]), (False, 33.5))
        self.assertTrue(r["lv:us:LVUS1"]["change"]["stale"], "La Viña's store not updated yet")
        after = {(y["pub"], y["type"]): y["after"] for y in doc["price_changes"][0]["yearly"]}
        self.assertEqual(after, {("gv", "print"): 39.0, ("gv", "digital"): 33.5, ("lv", "print"): 19.5, ("lv", "digital"): 17.0})

    def test_a_product_the_memory_does_not_know_follows_the_store(self):
        items = [plan("gv", "us", "GVUS1-27", "print", 12, 36.0, 0)]
        doc = shop_doc("2027-01-02T11:00:00Z", items, memory=MEMORY, attempted="2027-01-02T10:30:00Z")
        self.assertFalse(rows(doc)["gv:us:GVUS1-27"]["change"]["stale"])

    def test_a_book_read_on_the_day_still_at_its_old_price(self):
        # January 1: the morning read finds the same book at the price remembered from December 31 — the store's
        # page is not updated yet; any other price, or the next book (another SKU, from the 15th), is the store's
        memory = {"2027-01-01": {**MEMORY["2027-01-01"], "botm:gv:GV31": 14.99}}
        def stale(now: str, book: dict) -> bool:
            return shop_doc(now, PLANS + [book], memory=memory, attempted=now)["botm"][0]["price_stale"]
        self.assertTrue(stale("2027-01-01T11:00:00Z", botm("2027-01-01")))
        newer = botm("2027-01-01")
        newer["extra"].update(price=16.99, sale_price=13.59)
        self.assertFalse(stale("2027-01-01T11:00:00Z", newer))
        next_book = botm("2027-01-15")
        next_book["extra"].update(sku="GV32", starts="2027-01-15", ends="2027-02-14")
        self.assertFalse(stale("2027-01-15T11:00:00Z", next_book))
        self.assertFalse(stale("2026-12-31T23:00:00Z", botm("2026-12-31")), "before the day: nothing to compare yet")
        self.assertFalse(stale("2027-01-01T11:00:00Z", botm("2026-12-31")),
                         "read before the day: the pages leave its prices out by its read day already")

    def test_no_store_data_still_gives_the_notice(self):
        doc = shop_doc("2026-10-02T15:00:00Z", items=[])
        self.assertEqual([(y["now"], y["new"]) for y in doc["price_changes"][0]["yearly"]],
                         [(None, 39.0), (None, 34.0), (None, 19.5), (None, 17.0)])
        self.assertEqual(B.empty_shop()["price_changes"], [])


# =========================================================================== the pages (eleventy/filters/shop.js)
VIEWS_JS = r"""
const v = (lang) => {
  const subs = filters.shopSubs(input.shop, lang);
  const pub = subs.pubs.find((p) => p.pub === (lang === "es" ? "lv" : "gv"));
  const us = pub.regions.find((r) => r.region === "us");
  const pick = (tp) => tp && { terms: tp.terms.map((x) => ({ label: x.label, price: x.price, save: x.save, best: x.best, note: x.note })),
                               volume: tp.volume, swap: tp.swap && { at: tp.swap.at, terms: tp.swap.terms.map((x) => ({ price: x.price, save: x.save, note: x.note })), volume: tp.swap.volume } };
  return {
    types: Object.fromEntries(us.types.map((tp) => [tp.type, pick(tp)])),
    pcNote: subs.pcNote,
    notices: filters.shopPriceChanges(input.shop, lang).map((n) => ({ date: n.date, dateShort: n.dateShort, before: n.before, after: n.after,
                                                                     source: n.source, sourceLang: n.sourceLang, docMatch: n.docMatch })),
    botm: filters.shopBotm(input.shop, lang).map((b) => ({ hasPrices: b.hasPrices, sale: b.sale, price: b.price, save: b.save, pct: b.pct,
                                                          pcStale: b.pcStale, pcBefore: b.pcBefore, pcSwap: b.pcSwap })),
  };
};
out({ en: v("en"), es: v("es") });
"""


def views(case: unittest.TestCase, shop: dict, now: str) -> dict:
    return run_js(case, VIEWS_JS, data={"shop": shop}, env={"MONTHLY_NOW": now})


class Pages(unittest.TestCase):
    """What /shop/ shows: built at a moment (MONTHLY_NOW, the build's clock) from shop.json built at a moment."""

    @classmethod
    def setUpClass(cls):
        cls.dec31 = shop_doc("2026-12-31T23:00:00Z")
        cls.jan1 = shop_doc("2027-01-01T08:00:00Z", memory=MEMORY, attempted="2026-12-31T13:00:00Z")
        upd = priced(PLANS, {"sub:gv:us:GVUS1": 39.0, "sub:gv:us:GO1Y": 34.0, "sub:gv:intl:GOINTL1": 34.0, "sub:lv:us:LVUS1": 19.5,
                             "sub:lv:us:LO1A": 17.0}) + [botm("2027-01-01")]
        cls.updated = shop_doc("2027-01-01T11:00:00Z", upd, memory=MEMORY, attempted="2027-01-01T10:30:00Z")
        other = priced(PLANS, {"sub:gv:us:GVUS1": 38.5}) + [botm("2027-01-01")]
        cls.other = shop_doc("2027-01-01T11:00:00Z", other, memory=MEMORY, attempted="2027-01-01T10:30:00Z")

    def test_built_at_1159_pm_on_december_31_both_states(self):
        r = views(self, self.dec31, DEC31_2359)["en"]
        pr = r["types"]["print"]
        self.assertEqual([t["price"] for t in pr["terms"]], ["$36.00", "$68.00", "$90.00"])
        self.assertEqual(pr["terms"][0]["note"], {"text": "From Jan 1, 2027: $39.00", "win": {"from": "", "until": E_AT, "hidden": False}, "tone": "soon"})
        self.assertEqual(pr["terms"][1]["save"], "Save $4.00 vs. renewing yearly")
        self.assertEqual(pr["swap"]["at"], E_AT)
        self.assertEqual([t["price"] for t in pr["swap"]["terms"]], ["$39.00", "$68.00", "$90.00"])
        self.assertEqual(pr["swap"]["terms"][0]["note"]["text"], "New price since Jan 1, 2027")
        self.assertEqual([t["save"] for t in pr["swap"]["terms"]], [None, None, None],
                         "no saving set against an announced price (the store may change the others the same day)")
        self.assertEqual(pr["volume"]["cols"], ["1 year", "2 years"])
        self.assertEqual((pr["swap"]["volume"]["cols"], pr["swap"]["volume"]["note"]),
                         (["2 years"], "Volume prices for 1 year: see the store."),
                         "the 1-year plan's old volume prices are left out — and the note claims nothing about them")
        dg = r["types"]["digital"]
        self.assertEqual([t["price"] for t in dg["terms"]], ["$2.99", "$29.99"])
        self.assertEqual([t["price"] for t in dg["swap"]["terms"]], ["$2.99", "$34.00"])
        self.assertIsNone(r["types"]["complete"]["swap"], "Complete is not in the announcement")
        self.assertEqual(r["pcNote"], {"date": "Jan 1, 2027", "win": {"from": E_AT, "until": "", "hidden": True}})
        n = r["notices"][0]
        self.assertEqual(n["before"]["win"], {"from": "", "until": E_AT, "hidden": False})
        self.assertEqual(n["after"]["win"], {"from": E_AT, "until": N_AT, "hidden": True})
        self.assertEqual([(x["mag"], x["typeName"], x["now"], x["new"]) for x in n["before"]["rows"]],
                         [("Grapevine", "Print", "$36.00", "$39.00"), ("Grapevine", "Digital", "$29.99", "$34.00"),
                          ("La Viña", "Print", "$18.00", "$19.50"), ("La Viña", "Digital", "$14.99", "$17.00")])
        self.assertEqual((n["before"]["books"], n["after"]["books"]), ("$2.00", True))
        self.assertEqual(n["date"], "January 1, 2027")
        b = r["botm"][0]
        self.assertTrue(b["hasPrices"])
        self.assertEqual(b["pcBefore"]["text"], "From January 1, 2027, Grapevine and La Viña books cost $2.00 more.")
        self.assertEqual(b["pcSwap"], {"at": E_AT, "text": "Book prices changed on January 1, 2027: the store shows this book's current price."})
        es = views(self, self.dec31, DEC31_2359)["es"]
        lv = es["types"]["print"]
        self.assertEqual(lv["terms"][0]["note"]["text"], "Desde el 1 de enero de 2027: $19.50")
        self.assertEqual(lv["swap"]["terms"][0]["note"]["text"], "Precio nuevo desde el 1 de enero de 2027")
        self.assertEqual([x["mag"] for x in es["notices"][0]["before"]["rows"]], ["La Viña", "La Viña", "Grapevine", "Grapevine"])
        self.assertEqual((es["notices"][0]["source"], es["notices"][0]["sourceLang"]),
                         ("Carta de AA Grapevine a las oficinas intergrupales y centrales, 1 de octubre de 2026", "es"))

    def test_a_page_built_before_the_announcement_waits_for_it(self):
        r = views(self, self.dec31, "2026-09-30T12:00:00Z")["en"]
        self.assertEqual(r["notices"][0]["before"]["win"], {"from": "2026-10-01T05:00:00Z", "until": E_AT, "hidden": True})
        self.assertTrue(r["types"]["print"]["terms"][0]["note"]["win"]["hidden"])
        self.assertTrue(r["botm"][0]["pcBefore"]["win"]["hidden"])

    def test_built_at_midnight_on_january_1_with_old_store_data(self):
        r = views(self, self.jan1, JAN1_0000)["en"]
        pr = r["types"]["print"]
        self.assertIsNone(pr["swap"])
        self.assertEqual([t["price"] for t in pr["terms"]], ["$39.00", "$68.00", "$90.00"])
        self.assertEqual(pr["terms"][0]["note"], {"text": "New price since Jan 1, 2027", "win": {"from": "", "until": "", "hidden": False}, "tone": "new"})
        self.assertEqual([t["save"] for t in pr["terms"]], [None, None, None])
        self.assertEqual(r["types"]["digital"]["terms"][1]["price"], "$34.00")
        self.assertEqual(r["pcNote"], {"date": "Jan 1, 2027", "win": None})
        n = r["notices"][0]
        self.assertIsNone(n["before"])
        self.assertEqual(n["after"]["win"], {"from": "", "until": N_AT, "hidden": False})
        self.assertEqual([x["after"] for x in n["after"]["rows"]], ["$39.00", "$34.00", "$19.50", "$17.00"])
        b = r["botm"][0]
        self.assertEqual((b["hasPrices"], b["sale"], b["save"], b["pct"]), (False, "", "", 20),
                         "prices read on December 31: no amounts, no 'you save' — the percent stays")
        self.assertEqual(b["pcStale"], "Book prices changed on January 1, 2027: the store shows this book's current price.")
        self.assertIsNone(b["pcBefore"])
        self.assertIsNone(b["pcSwap"])

    def test_the_store_updated_wins_and_the_book_shows_its_prices(self):
        r = views(self, self.updated, "2027-01-01T12:00:00Z")["en"]
        pr = r["types"]["print"]
        self.assertEqual(pr["terms"][0]["price"], "$39.00")
        self.assertEqual(pr["terms"][0]["note"]["win"], {"from": "", "until": N_AT, "hidden": False}, "only while the notice runs")
        self.assertEqual(pr["terms"][1]["save"], "Save $10.00 vs. renewing yearly", "the store's own prices: the saving is real")
        self.assertIsNone(r["pcNote"])
        b = r["botm"][0]
        self.assertEqual((b["hasPrices"], b["sale"]), (True, "$11.99"), "read on January 1 (no remembered price): what the store says")
        r2 = views(self, self.other, "2027-01-01T12:00:00Z")["en"]
        self.assertEqual(r2["types"]["print"]["terms"][0]["price"], "$38.50", "anything else after the day: the store wins")

    def test_a_book_still_at_its_old_price_on_the_day_shows_no_amounts(self):
        # the morning read of January 1 finds the book at the regular price remembered from December 31
        memory = {"2027-01-01": {**MEMORY["2027-01-01"], "botm:gv:GV31": 14.99}}
        doc = shop_doc("2027-01-01T11:00:00Z", PLANS + [botm("2027-01-01")], memory=memory, attempted="2027-01-01T10:30:00Z")
        b = views(self, doc, "2027-01-01T12:00:00Z")["en"]["botm"][0]
        self.assertEqual((b["hasPrices"], b["sale"], b["save"], b["pct"]), (False, "", "", 20), "no 'you save' on the old price")
        self.assertEqual(b["pcStale"], "Book prices changed on January 1, 2027: the store shows this book's current price.")
        updated = botm("2027-01-01")
        updated["extra"].update(price=16.99, sale_price=13.59)
        doc2 = shop_doc("2027-01-02T11:00:00Z", PLANS + [updated], memory=memory, attempted="2027-01-02T10:30:00Z")
        b2 = views(self, doc2, "2027-01-02T12:00:00Z")["en"]["botm"][0]
        self.assertEqual((b2["hasPrices"], b2["sale"], b2["price"], b2["save"]), (True, "$13.59", "$16.99", "$3.40"),
                         "the store's new price: its own amounts again")

    def test_after_the_notice_ends(self):
        r = views(self, self.updated, "2027-02-02T14:00:00Z")["en"]
        self.assertEqual(r["notices"], [])
        self.assertIsNone(r["types"]["print"]["terms"][0]["note"])
        stale = views(self, self.jan1, "2027-02-02T14:00:00Z")["en"]
        self.assertEqual(stale["types"]["print"]["terms"][0]["price"], "$39.00")
        self.assertEqual(stale["types"]["print"]["terms"][0]["note"]["text"], "New price since Jan 1, 2027",
                         "the announced price still stands in: it keeps saying so")

    def test_windows(self):
        r = run_js(self, r"""
          const S = await imp("eleventy/filters/shop.js");
          const now = new Date("2027-01-01T05:59:00Z");
          out([S.shopWindow("2026-10-01T05:00:00Z", "2027-01-01T06:00:00Z", now), S.shopWindow("2027-01-01T06:00:00Z", "2027-02-01T06:00:00Z", now),
               S.shopWindow("", "2027-01-01T05:00:00Z", now), S.shopWindow("2027-01-01", "soon", now), S.shopWindow("", "", now)]);""")
        self.assertEqual(r, [{"from": "", "until": E_AT, "hidden": False}, {"from": E_AT, "until": N_AT, "hidden": True}, None,
                             {"from": "", "until": "", "hidden": False}, {"from": "", "until": "", "hidden": False}])

    def test_the_page_writes_both_states(self):
        page = (ROOT / "src" / "pages" / "shop.njk").read_text(encoding="utf-8")
        for needle in ('id="price-changes"', "termList(tp, tp.swap.terms", "{ from: tp.swap.at, hidden: true }",
                       "ui.when({ until: b.pcSwap.at }) if b.pcSwap", "{{ ui.when(n.win) }}", 'priceNotice(pc, lang)',
                       "driveMatch(pc.docMatch)", '"shop.pc_prices_note"',
                       # AA Grapevine's notice in another language than the page's says so ("(en inglés)")
                       'hreflang="{{ doc.lang }}"', '("access.in_english" if doc.lang == "en" else "access.in_spanish")',
                       # the notice's table: one small block per plan on a phone with larger text (shop.css), still a
                       # table for screen readers
                       'class="shop-table shop-pc-table w-full text-sm" role="table"', '<tr role="row">',
                       '<span class="shop-pc-label" aria-hidden="true">{{ colNew }}</span>'):
            self.assertIn(needle, page)
        css = (ROOT / "src" / "assets" / "css" / "areas" / "shop.css").read_text(encoding="utf-8")
        self.assertIn(".shop-pc-label { display: none; }", css)
        self.assertIn('.shop-pc-table :is(tbody, tr, th) { display: block; }', css)
        ui = (ROOT / "src" / "_includes" / "macros" / "ui.njk").read_text(encoding="utf-8")
        self.assertIn("{% macro when(w) %}", ui)
        self.assertIn("data-gv-when", ui)


# =========================================================================== the browser
BROWSER_JS = r"""
import vm from "node:vm";
const run = (atIso) => {
  const mk = (attrs) => ({ attrs: Object.assign({}, attrs), hidden: "hidden" in attrs, children: [], parent: null,
    getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }, setAttribute(n, v) { this.attrs[n] = String(v); },
    hasAttribute(n) { return n in this.attrs; }, contains(o) { return o === this; }, addEventListener() {} });
  const before = mk({ "data-gv-when": "", "data-gv-expire": "2027-01-01T06:00:00Z" });
  const after = mk({ "data-gv-when": "", "data-gv-from": "2027-01-01T06:00:00Z", "data-gv-expire": "2027-02-01T06:00:00Z", hidden: "" });
  const over = mk({ "data-gv-when": "", "data-gv-from": "2026-12-01T06:00:00Z", "data-gv-expire": "2026-12-15T06:00:00Z", hidden: "" });
  const els = [before, after, over];
  const now = Date.parse(atIso);
  class FakeDate extends Date { static now() { return now; } }
  const body = { contains: () => false };
  const doc = { readyState: "loading", documentElement: { lang: "en", getAttribute: () => null, setAttribute() {}, classList: { add() {}, toggle() {} } },
    body, activeElement: body, addEventListener() {},
    querySelectorAll: (sel) => els.filter((e) => String(sel).split(",").map((s) => s.trim().slice(1, -1)).some((a) => e.hasAttribute(a))),
    querySelector: (sel) => els.find((e) => String(sel).split(",").map((s) => s.trim().slice(1, -1)).some((a) => e.hasAttribute(a))) || null };
  const ctx = { console, JSON, Math, Object, Array, String, Number, RegExp, Intl, Promise, Date: FakeDate, document: doc, navigator: {},
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} }, setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0,
    addEventListener() {}, dispatchEvent() {}, matchMedia: () => ({ matches: false }), CustomEvent: function () {} };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/app.js", "utf8"), ctx, { filename: "app.js" });
  ctx.GV.expire();
  return els.map((e) => [e.hidden, e.hasAttribute("data-gv-started"), e.hasAttribute("data-gv-expired")]);
};
// base.njk's first head script, run on the same three parts as the parser adds them (a stand-in MutationObserver)
const head = (atIso) => {
  const base = fs.readFileSync("src/_includes/layouts/base.njk", "utf8");
  const code = base.slice(base.indexOf("    (function () {\n      if (!window.MutationObserver)"), base.indexOf("  </script>", base.indexOf("if (!window.MutationObserver)")));
  const mk = (attrs) => ({ nodeType: 1, attrs: Object.assign({}, attrs), hidden: "hidden" in attrs,
    getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }, setAttribute(n, v) { this.attrs[n] = String(v); },
    hasAttribute(n) { return n in this.attrs; } });
  const els = [mk({ "data-gv-when": "", "data-gv-expire": "2027-01-01T06:00:00Z" }),
               mk({ "data-gv-when": "", "data-gv-from": "2027-01-01T06:00:00Z", hidden: "" }),
               mk({ "data-gv-expire": "2026-10-03T05:00:00Z" })];       // a bulletin post's (no data-gv-when): left to GV.expire
  let cb = null, observed = null, disconnected = false, onReady = null;
  const now = Date.parse(atIso);
  class FakeDate extends Date { static now() { return now; } }
  const ctx = { Date: FakeDate, String, RegExp,
    MutationObserver: class { constructor(f) { cb = f; } observe(t, o) { observed = o; } disconnect() { disconnected = true; } },
    document: { documentElement: {}, addEventListener: (t, f) => { if (t === "DOMContentLoaded") onReady = f; } } };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  cb([{ addedNodes: [els[0], { nodeType: 3 }] }, { addedNodes: [els[1], els[2]] }]);
  onReady();
  return { observed, disconnected, els: els.map((e) => [e.hidden, e.hasAttribute("data-gv-started"), e.hasAttribute("data-gv-expired")]) };
};
out({ before: run("2027-01-01T05:59:59Z"), after: run("2027-01-01T06:00:00Z"), headBefore: head("2027-01-01T05:59:59Z"), headAfter: head("2027-01-01T06:00:01Z") });
"""


class Browser(unittest.TestCase):
    """The switch between builds — 11:59:59 PM and midnight Central on December 31 / January 1, by instants, so a
    browser in any time zone switches at the same moment."""

    def check(self, tz: str):
        r = run_js(self, BROWSER_JS, needs_modules=False, env={"TZ": tz})
        self.assertEqual(r["before"], [[False, False, False], [True, False, False], [True, False, True]])
        self.assertEqual(r["after"], [[True, False, True], [False, True, False], [True, False, True]])
        self.assertEqual(r["headBefore"]["els"], [[False, False, False], [True, False, False], [False, False, False]])
        self.assertEqual(r["headAfter"]["els"], [[True, False, True], [False, True, False], [False, False, False]],
                         "only the parts marked data-gv-when are set while the page loads")
        self.assertEqual(r["headAfter"]["observed"], {"childList": True, "subtree": True})
        self.assertTrue(r["headAfter"]["disconnected"])

    def test_central_time(self):
        self.check("America/Chicago")

    def test_a_browser_in_another_time_zone(self):
        self.check("Asia/Tokyo")
        self.check("America/Los_Angeles")


# =========================================================================== the GV/LV report
REPORT_JS = r"""
const R = await imp("eleventy/filters/report.js");
const res = {};
for (const [name, now, shop] of input.runs) {
  const model = R.reportModel({ shop }, {}, { ways: [], tips: {}, wayById: {} }, { url: "https://example.org/site" }, new Date(now));
  res[name] = Object.fromEntries(["en", "es"].map((l) => [l, model.langs[l].sections.find((s) => s.id === "shop")]));
}
out(res);
"""

EDITOR_JS = r"""
import vm from "node:vm";
const D = { v: 1, month: "2026-12", meetings: { options: [] }, langs: {} };
for (const L of ["en", "es"]) D.langs[L] = { month: "December 2026", tokens: {}, roles: {}, custom: "x", paste: "x", meet: {},
  sections: [{ id: "header", title: "h", text: "District [##] report" },
             { id: "shop", title: "Shop", text: "Grapevine: $36.00 a year in print", after: { at: "2027-01-01T06:00:00Z", text: "Grapevine: $39.00 a year in print" } }] };
const boot = (atIso) => {
  const now = Date.parse(atIso);
  class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(now); } static now() { return now; } }
  const docL = {};
  const ctx = { console, JSON, Math, Date: FakeDate, Intl, Object, Array, String, Number, Promise, setTimeout: () => 0, clearTimeout() {},
    localStorage: { getItem: () => null, setItem() {}, removeItem() {}, length: 0, key: () => null }, navigator: {}, GV: {}, addEventListener() {},
    document: { addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); }, querySelector: () => null,
                getElementById: (id) => (id === "rp-data" ? { textContent: JSON.stringify(D) } : id === "rp-ui" ? { textContent: "{}" } : null) } };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/report.js", "utf8"), ctx, { filename: "report.js" });
  let factory = null;
  ctx.Alpine = { data: (name, fn) => { if (name === "rpEditor") factory = fn; } };
  for (const fn of docL["alpine:init"] || []) fn();
  const a = factory("en");
  a.$nextTick = (fn) => fn && fn();
  a.$refs = {};
  a.$root = { querySelector: () => null, querySelectorAll: () => [] };
  a.init();
  return a.D.langs.en.sections.find((s) => s.id === "shop").text;
};
out({ before: boot("2027-01-01T05:59:59Z"), after: boot("2027-01-01T06:00:00Z") });
"""


class Report(unittest.TestCase):
    """The GV/LV report's "Book of the Month and subscriptions" (eleventy/filters/report.js shopSection): the new
    prices to pass on to the district before the day, the section's text from the day (`after`)."""

    def test_the_shop_section(self):
        runs = [["dec", "2026-12-15T18:00:00Z", shop_doc("2026-12-15T18:00:00Z", PLANS + [botm("2026-12-15")])],
                ["jan", "2027-01-01T14:00:00Z", shop_doc("2027-01-01T08:00:00Z", memory=MEMORY, attempted="2026-12-31T13:00:00Z")]]
        r = run_js(self, REPORT_JS, data={"runs": runs})
        dec = r["dec"]["en"]
        self.assertIn("No Matter What” — $11.99 (regular price $14.99)", dec["text"])
        self.assertIn("• Grapevine: $36.00 a year in print · digital from $2.99 a month", dec["text"])
        self.assertIn("New prices from January 1, 2027, as announced by AA Grapevine:\n• Grapevine, 1 year: print $39.00, digital $34.00\n"
                      "• La Viña, 1 year: print $19.50, digital $17.00\n• Grapevine and La Viña books: $2.00 more each", dec["text"])
        self.assertEqual(dec["after"]["at"], E_AT)
        self.assertIn("• Grapevine: $39.00 a year in print", dec["after"]["text"])
        self.assertIn("• Grapevine: “No Matter What”\n", dec["after"]["text"], "from the day: the book without its old prices")
        # from the day: AA Grapevine's own list again — never "the prices above are the new ones" (the lowest price
        # above is the monthly digital plan, which the letter does not name)
        self.assertIn("New prices since January 1, 2027, as announced by AA Grapevine:\n• Grapevine, 1 year: print $39.00, digital $34.00\n"
                      "• La Viña, 1 year: print $19.50, digital $17.00\n• Grapevine and La Viña books: $2.00 more each", dec["after"]["text"])
        self.assertNotIn("prices above", dec["after"]["text"])
        self.assertIn("Nuevos precios desde el 1 de enero de 2027, según el anuncio de AA Grapevine:\n• La Viña, 1 año: impresa $19.50, digital $17.00",
                      r["dec"]["es"]["text"])
        self.assertIn("Nuevos precios desde el 1 de enero de 2027, según el anuncio de AA Grapevine:\n• La Viña, 1 año: impresa $19.50, digital $17.00\n"
                      "• Grapevine, 1 año: impresa $39.00, digital $34.00", r["dec"]["es"]["after"]["text"])
        self.assertNotIn("de arriba", r["dec"]["es"]["after"]["text"])
        jan = r["jan"]["en"]
        self.assertNotIn("after", jan)
        self.assertIn("• Grapevine: $39.00 a year in print", jan["text"])
        self.assertIn("New prices since January 1, 2027, as announced by AA Grapevine:\n• Grapevine, 1 year: print $39.00, digital $34.00", jan["text"])
        self.assertNotIn("$14.99", jan["text"])

    def test_the_editor_switches_at_midnight_central(self):
        r = run_js(self, EDITOR_JS, needs_modules=False)
        self.assertEqual(r, {"before": "Grapevine: $36.00 a year in print", "after": "Grapevine: $39.00 a year in print"})


# =========================================================================== the monthly toolkit
MONTHLY_JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const { db, site, carry } = input;
const res = {};
for (const key of input.keys) {
  const d = new Date(input.now);
  const mm = { en: M.monthModel(key, db, carry, site, "en", d), es: M.monthModel(key, db, carry, site, "es", d) };
  const nw = { en: M.monthNow(db, site, "en", d), es: M.monthNow(db, site, "es", d) };
  const iss = { en: M.monthIssueLinks(db, mm.en), es: M.monthIssueLinks(db, mm.es) };
  res[key] = { price: mm.en.price, wa: M.monthMessage({ mm, nw, iss }, ["en"], "whatsapp", site, t),
               bi: M.monthMessage({ mm, nw, iss }, ["es", "en"], "email", site, t) };
}
out(res);
"""


class Monthly(unittest.TestCase):
    """The month's message (a group chat, an e-mail): the months from the announcement to the day say the prices
    change; the day's month says they changed; the others say nothing."""

    def test_the_months_messages(self):
        db = TM.full_db()
        db["shop"] = {**db.get("shop", {}), "price_changes": shop_doc("2026-10-02T15:00:00Z")["price_changes"]}
        keys = ["2026-09", "2026-10", "2026-11", "2026-12", "2027-01", "2027-02"]
        r = run_js(self, MONTHLY_JS, data={"db": db, "site": TM.SITE, "carry": TM.CARRY, "keys": keys, "now": "2026-10-05T17:00:00Z"})
        self.assertEqual({k: (v["price"] or {}).get("kind") for k, v in r.items()},
                         {"2026-09": None, "2026-10": "before", "2026-11": "before", "2026-12": "before", "2027-01": "after", "2027-02": None})
        line = "📢 Grapevine and La Viña prices change on January 1, 2027: https://example.org/site/shop/#price-changes"
        for k in ("2026-10", "2026-11", "2026-12"):
            self.assertIn(line, r[k]["wa"])
        self.assertIn("📢 New Grapevine and La Viña prices since January 1, 2027: https://example.org/site/shop/#price-changes", r["2027-01"]["wa"])
        for k in ("2026-09", "2027-02"):
            self.assertNotIn("📢", r[k]["wa"])
        self.assertIn("Los precios de Grapevine y La Viña cambian el 1 de enero de 2027 / Grapevine and La Viña prices change on January 1, 2027: "
                      "https://example.org/site/es/shop/#price-changes", r["2026-12"]["bi"])

    def test_keep_up_all_month(self):
        page = (ROOT / "src" / "pages" / "monthly-month.njk").read_text(encoding="utf-8")
        self.assertIn("{% for pc in (db.shop | shopPriceChanges(lang)) %}", page)
        self.assertIn("<li{{ ui.when(n.win) }}>", page)
        self.assertLess(page.index("shopPriceChanges(lang)"), page.index("{% if nx.subsFrom %}"),
                        "before the subscription line (a hidden last row would leave a stray divider)")
        # the row says what it opens — not the headline, which the Bulletin row above may show as its newest post
        self.assertIn('("monthly.pc_link_" + part) | t(lang)', page)
        self.assertIn('("monthly.pc_" + part) | t(lang, { date: pc.date })', page)
        self.assertNotIn('("shop.pc_line_" + part)', page)
        strings = {**json.loads((ROOT / "src" / "_i18n" / "monthly.json").read_text(encoding="utf-8")),
                   **json.loads((ROOT / "src" / "_i18n" / "shop.json").read_text(encoding="utf-8"))}
        for part in ("before", "after"):
            for lang in ("en", "es"):
                with self.subTest(part=part, lang=lang):
                    head = strings[f"shop.pc_line_{part}"][lang].split("{")[0].strip().lower()
                    self.assertNotIn(head, strings[f"monthly.pc_link_{part}"][lang].lower())
                    self.assertIn("{date}", strings[f"monthly.pc_{part}"][lang], "the day is in the row's line")


# =========================================================================== the monthly digest and its e-mail
DIGEST_JS = r"""
const C = await imp("eleventy/filters/community.js");
const out_ = {};
for (const now of input.nows) out_[now] = C.buildMonthlyDigest(input.db, { site: { url: "https://example.org/site" }, now: new Date(now) }).toolkit.price;
const md = C.buildMonthlyDigest(input.db, { site: { url: "https://example.org/site" }, now: new Date("2026-12-01T15:00:00Z") });
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
out({ prices: out_, text: C.monthlyDigestText(md, ["en", "es"], "whatsapp", { url: "https://example.org/site" }, t) });
"""
NOWS = ["2026-09-30T17:00:00Z", "2026-10-01T15:05:00Z", "2026-11-01T15:05:00Z", "2026-12-01T15:05:00Z", "2027-01-01T15:05:00Z",
        "2027-01-31T17:00:00Z", "2027-02-01T15:05:00Z"]
KINDS = [None, "before", "before", "before", "after", "after", None]


class Digest(SD.DigestCase):
    """The e-mails sent on Nov 1 (October's edition), Dec 1 and Jan 1 — and the /digest/ page — carry one pointer row
    after the toolkit's while the notice is on; the page (community.js digestPrice) and the e-mail
    (send_digest.py price_change) pick the same."""

    def setUp(self):
        super().setUp()
        self.shop = shop_doc("2026-10-02T15:00:00Z")
        self.write("shop", self.shop)

    def test_the_page_and_the_email_pick_the_same(self):
        r = run_js(self, DIGEST_JS, data={"db": {"shop": self.shop}, "nows": NOWS})
        self.assertEqual([(r["prices"][n] or {}).get("kind") for n in NOWS], KINDS)
        self.assertEqual(r["prices"]["2026-12-01T15:05:00Z"]["date"], {"en": "January 1, 2027", "es": "1 de enero de 2027"})
        py = [(SDM.price_change(SDM.to_central(datetime.fromisoformat(n.replace("Z", "+00:00"))).date()) or {}).get("kind") for n in NOWS]
        self.assertEqual(py, KINDS)
        self.assertIn("📢 Grapevine and La Viña prices change on January 1, 2027 / Los precios de Grapevine y La Viña cambian el 1 de enero "
                      "de 2027: https://example.org/site/shop/#price-changes", r["text"])

    def test_the_email_rows(self):
        html, text = self.preview("2026-12-01")
        self.assertIn("Grapevine and La Viña prices change on January 1, 2027", html)
        self.assertIn(f"{SD.SITE}/shop/#price-changes", html)
        self.assertIn("What changes, and why →", html)
        en, es = self.halves(text)
        self.assertIn(f"Grapevine and La Viña prices change on January 1, 2027: {SD.SITE}/shop/#price-changes", en)
        self.assertIn(f"Los precios de Grapevine y La Viña cambian el 1 de enero de 2027: {SD.SITE}/es/shop/#price-changes", es)
        html, text = self.preview("2027-01-01")
        self.assertIn("New Grapevine and La Viña prices since January 1, 2027", html)
        self.assertIn("See the new prices →", html)
        html, text = self.preview("2027-02-01")
        self.assertNotIn("#price-changes", html + text)


# =========================================================================== the announcements
FIRST_POST = ROOT / "content" / "bulletin" / "2026-10-01-prices-change-january-1-2027.md"
SECOND_POST = ROOT / "content" / "bulletin" / "2027-01-01-new-prices-in-effect.md"


def teaser(text: str, n: int = 320) -> str:
    """What the home page's card shows of a long post (eleventy.config.js `excerpt`, 320 characters)."""
    s = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", text or "")).strip()
    return re.sub(r"\s+\S*$", "", s[:n]) + "…" if len(s) > n else s


class Bulletin(unittest.TestCase):
    """content/bulletin: the heads-up (October 1, pinned, through December 31) and "now in effect" (scheduled for
    January 1, through January 31), each with its own Spanish over several lines. (Content: once the posts are
    deleted after their time, these checks are skipped.)"""

    @classmethod
    def setUpClass(cls):
        if not (FIRST_POST.exists() and SECOND_POST.exists()):
            raise unittest.SkipTest("the price change posts are no longer in content/bulletin")
        cls.first = A.parse_announcement(FIRST_POST)
        cls.second = A.parse_announcement(SECOND_POST)

    def test_the_two_posts(self):
        f, s = self.first, self.second
        self.assertEqual((f["title"], f["date"], f["lang"], f["extra"]["expires"], f["extra"]["pinned"]),
                         ("Grapevine and La Viña prices change on January 1, 2027", "2026-10-01", "en", "2026-12-31", True))
        self.assertNotIn("publish", f["extra"])
        self.assertEqual((s["title"], s["date"], s["extra"]["publish"], s["extra"]["expires"], s["extra"]["pinned"]),
                         ("New Grapevine and La Viña prices are now in effect", "2027-01-01", "2027-01-01", "2027-01-31", False))
        for post in (f, s):
            self.assertNotIn("missing_files", post["extra"])
            body, es = post["extra"]["body_md"], post["extra"]["own_i18n"]["body_md"]["es"]
            # the teaser — the home page's pinned card, What's New, the feed — is the start of the text: every new
            # price is in its first sentence, in both languages (a list there would run together into one line)
            for text in (post["summary"], post["extra"]["own_i18n"]["summary"]["es"]):
                for price in ("$39.00", "$34.00", "$19.50", "$17.00", "$2.00"):
                    self.assertIn(price, teaser(text).split(". ")[0])
            self.assertIn("(/shop/#subscriptions)", body)
            self.assertIn("https://drive.google.com/file/d/1S2PrbkYC4auxUSlgdwpoQKwZW3QeaI-p/view", body)
            self.assertIn("\n\n", es, "the Spanish text keeps its paragraphs")
        self.assertEqual(f["extra"]["own_i18n"]["body_md"]["es"].count("\n- "), 2, "…and its list of links")
        # calm and informative: no pressure to buy, no claim the letter does not make
        for text in (f["extra"]["body_md"], f["extra"]["own_i18n"]["body_md"]["es"], s["extra"]["body_md"],
                     s["extra"]["own_i18n"]["body_md"]["es"]):
            self.assertNotRegex(text.lower(), r"buy now|before prices|hurry|don't miss|renew (?:now|early|before)|ahora antes|renueva")
            self.assertNotRegex(text, r"(?i)2-year|3-year|2 años|3 años|canad|international|internacional|monthly|mensual|complete|completa")
            # only Grapevine and La Viña books change price, not "literature" (to a treasurer: AA World Services' too)
            self.assertNotRegex(text, r"(?i)literature|literatura")
        self.assertIn("treasurer", f["extra"]["body_md"])
        self.assertIn("Grapevine or La Viña books or subscriptions", f["extra"]["body_md"])
        self.assertIn("libros o suscripciones de Grapevine y La Viña", f["extra"]["own_i18n"]["body_md"]["es"])
        self.assertIn("printing, paper and materials, fulfillment, postage and shipping", f["extra"]["body_md"])

    def ctx(self, now: str) -> B.Ctx:
        c = B.Ctx(offline=True)
        c.now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        c.now_ts = c.now.timestamp()
        c.today_local = c.now.astimezone(c.tz).date()
        f = {**copy.deepcopy(self.first), "first_seen": "2026-10-01T23:00:00Z"}
        s = {**copy.deepcopy(self.second), "first_seen": "2026-10-01T23:00:00Z"}
        c.raw = {"announcements": {"items": [f, s]}, "drive": {"items": []}}
        c.births = {"announcements": 0.0}
        return c

    def test_the_schedule(self):
        def shown(now):
            c = self.ctx(now)
            return [a["id"].split(":")[1][:10] for a in B.build_announcements(c)], [x["publish"] for x in c.scheduled]
        self.assertEqual(shown("2026-10-02T15:00:00Z"), (["2026-10-01"], ["2027-01-01"]))
        self.assertEqual(shown("2027-01-01T05:30:00Z"), (["2026-10-01"], ["2027-01-01"]), "11:30 PM on December 31")
        self.assertEqual(shown("2027-01-01T11:00:00Z"), (["2027-01-01"], []), "the morning update of January 1")
        self.assertEqual(shown("2027-01-31T23:00:00Z"), (["2027-01-01"], []))
        self.assertEqual(shown("2027-02-01T11:00:00Z"), ([], []))

    def test_october_edition_carries_the_heads_up(self):
        f = {**copy.deepcopy(self.first), "first_seen": "2026-10-01T23:00:00Z", "kind": "announcement", "status": "ok",
             "i18n": {"title": {"en": self.first["title"], "es": self.first["extra"]["own_i18n"]["title"]["es"]}}}
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/community.js");
          const md = (now) => C.buildMonthlyDigest(input.db, { site: {}, now: new Date(now) }).news.announcement.map((i) => i.id);
          out({ oct: md("2026-11-01T15:05:00Z"), nov: md("2026-12-01T15:05:00Z") });""", data={"db": {"announcements": {"items": [f]}}})
        self.assertEqual(r, {"oct": [f["id"]], "nov": []})


class DriveLetter(unittest.TestCase):
    """The letter in the Panel's notes folder: its name starts with the letter's own date."""

    def item(self, name: str) -> dict:
        e = Entry(id="1S2PrbkYC4auxUSlgdwpoQKwZW3QeaI-p", name=name, mime="application/pdf", modified="2026-10-01")
        f = D.Found(entry=e, panel=D.Panel(77, "Panel 77 (2027–2028)", "p", "2027-2028_Panel77_GVLV"), path=["notes"], chain=["r", "p", "n"])
        return D.build_item(f, {})

    def test_the_new_name_dates_it_by_the_letter(self):
        it = self.item(NEW_NAME)
        self.assertEqual((it["date"], it["title"], it["category"], it["lang"]),
                         ("2026-10-01", "Grapevine & La Viña Pricing Update - Effective January 1, 2027", "notes", "en"))
        old = self.item(OLD_NAME)
        self.assertEqual((old["date"], old["title"]), ("2027-01-01", "Grapevine & La Viña Pricing Update - Effective"),
                         "the old name: dated by the effective day, the date cut from the title")

    def test_magazine_names_do_not_make_a_title_spanish(self):
        self.assertEqual(self.item("Grapevine and La Viña Writing Workshop.pptx")["lang"], "en")
        self.assertEqual(self.item("Taller Mensual y Virtual de La Viña - último jueves de cada mes.png")["lang"], "es")


class Translations(unittest.TestCase):
    """data/translations/overrides.yml: the letter's Spanish title, and the Drive bulletin post's hand translation
    for both its current text ("about 8 cents a day") and the corrected one ("less than 10 cents a day"). (Content:
    an entry the committee removes once its text is gone from Drive skips its check.)"""

    LETTER = "Grapevine & La Viña Pricing Update - Effective January 1, 2027"

    @classmethod
    def setUpClass(cls):
        cls.data = yaml.safe_load((ROOT / "data" / "translations" / "overrides.yml").read_text(encoding="utf-8")) or {}
        cls.ov = T.Overrides(cls.data)

    def test_the_letters_title(self):
        if self.LETTER not in self.data:
            self.skipTest("the letter's title is no longer in overrides.yml")
        self.assertEqual(self.ov.get(self.LETTER, "es"),
                         "Actualización de precios de Grapevine y La Viña - A partir del 1 de enero de 2027")

    def test_both_versions_of_the_post(self):
        keys = [k for k in self.data if isinstance(k, str) and k.startswith("A living list") and "# Why it matters" in k]
        if len(keys) < 2:
            self.skipTest("overrides.yml no longer holds both versions of the Drive post")
        self.assertEqual(len(keys), 2)
        old = next(k for k in keys if "about 8 cents a day" in k)
        new = next(k for k in keys if "less than 10 cents a day" in k)
        self.assertEqual(old.replace("costs about 8 cents a day", "costs less than 10 cents a day"), new,
                         "only that phrase differs")
        self.assertIn("unos 8 centavos al día", self.ov.get(old, "es"))
        es_new = self.ov.get(new, "es")
        self.assertIn("menos de 10 centavos al día", es_new)
        self.assertEqual(self.ov.get(old, "es").replace("unos 8 centavos al día", "menos de 10 centavos al día"), es_new)
        # spaces and line breaks do not matter for a match (the Drive text as the sync normalizes it)
        self.assertEqual(self.ov.get("\n\n".join(new.split("\n")), "es"), es_new)
        self.assertLess(34.00 / 365 * 100, 10, "true at the new price too")


class OwnSpanish(unittest.TestCase):
    """A bulletin post's summary_es over several lines keeps its paragraphs and lists; one line is as before."""

    def test_several_lines_and_one(self):
        own = A.own_translations({"summary_es": "Uno:\n\n- **dos**\n- [tres](/shop/)\n", "title_es": "T"})
        self.assertEqual(own["body_md"]["es"], "Uno:\n\n- **dos**\n- [tres](/shop/)")
        self.assertEqual(own["summary"]["es"], "Uno: dos tres")
        one = A.own_translations({"summary_es": "Una  línea **así**."})
        self.assertEqual(one["body_md"]["es"], "Una línea **así**.")
        self.assertEqual(one["summary"]["es"], "Una línea **así**.")


class Strings(unittest.TestCase):
    def test_both_languages_and_the_same_placeholders(self):
        ph = re.compile(r"\{(\w+)\}")
        for f in ("shop.json", "report.json", "monthly.json", "community.json"):
            data = json.loads((ROOT / "src" / "_i18n" / f).read_text(encoding="utf-8"))
            for k, v in data.items():
                if not re.search(r"\.(pc_|price_link)", k):
                    continue
                with self.subTest(key=k):
                    self.assertTrue(v.get("en", "").strip() and v.get("es", "").strip())
                    self.assertEqual(sorted(ph.findall(v["en"])), sorted(ph.findall(v["es"])))
                    self.assertNotRegex(v["en"] + v["es"], r"(?i)\bpdf\b|buy now|hurry")
        # what the letter does not say is never claimed: the volume prices (the note only sends readers to the
        # store), and the reason is AA Grapevine's own list, whole
        shop = json.loads((ROOT / "src" / "_i18n" / "shop.json").read_text(encoding="utf-8"))
        self.assertNotRegex(shop["shop.pc_volume"]["en"] + shop["shop.pc_volume"]["es"], r"(?i)chang|cambi|\{date\}|has them|los tiene")
        self.assertIn("publications and products keep rising, including printing, paper and materials, fulfillment, postage and shipping",
                      shop["shop.pc_why"]["en"])
        self.assertIn("publicaciones y productos", shop["shop.pc_why"]["es"])
        # the e-mail (standard library only, its own strings) says it in the website's words
        site = {**json.loads((ROOT / "src" / "_i18n" / "shop.json").read_text(encoding="utf-8")),
                **json.loads((ROOT / "src" / "_i18n" / "community.json").read_text(encoding="utf-8"))}
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertEqual(SDM.T[lang]["pc_before"], site["shop.pc_line_before"][lang])
                self.assertEqual(SDM.T[lang]["pc_after"], site["shop.pc_line_after"][lang])
                self.assertEqual(SDM.T[lang]["pc_link_before"], site["community.digest.price_link_before"][lang])
                self.assertEqual(SDM.T[lang]["pc_link_after"], site["community.digest.price_link_after"][lang])


if __name__ == "__main__":
    unittest.main()
