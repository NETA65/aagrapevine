"""The Tracker page (/tracker/, the service expense tracker): src/pages/tracker.njk, src/assets/js/expenses.js,
src/_i18n/expenses.json, config/expenses.yml (src/_data/expenses.js). The tracker's logic has its own
tests (tests/test_expenses_core.py).

  * Strings — every expenses.* text in English AND Spanish, with the same {placeholders} in both; every
              key the page and the app use exists (literal keys, the keys built from a list — types,
              statuses, templates … — and every message key expenses-core.js can return); the words
              the core's claimText and claimLines ask for (claim.*, sub_kind.*, sub_product.*).
  * Config  — config/expenses.yml: unique ids, known types / templates / colours / funder kinds, both
              labels, icons in the picker list, the default rate and funder; src/_data/expenses.js
              builds it under I18N_STRICT=1 (Node.js).
  * Page    — the front matter (the core loads first), no x-html, the page is in the service worker's
              "Save key pages" list (sw.11ty.js rendered with Node.js), its stylesheet is imported, the
              menu and the GVR corner link to it.

    python -m unittest tests.test_expenses_page -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

STRINGS = ROOT / "src" / "_i18n" / "expenses.json"
PAGE = ROOT / "src" / "pages" / "tracker.njk"
APP = ROOT / "src" / "assets" / "js" / "expenses.js"
CORE = ROOT / "src" / "assets" / "js" / "expenses-core.js"
CONFIG = ROOT / "config" / "expenses.yml"
PLACEHOLDER = re.compile(r"\{(\w+)\}")

TYPES = ["expense", "mileage", "received", "giveaway", "stock"]
TEMPLATES = ["general", "books", "subscription", "lodging", "meal", "printing", "travel", "mileage", "received", "giveaway", "stock"]
FUNDER_KINDS = ["self", "area", "district", "group", "committee", "person", "other"]
TONES = ["gv", "lv", "grape", "vine", "rose", "teal", "gold", "slate"]
# the first part of every short key the app uses ("toast.saved" → expenses.toast.saved)
PREFIXES = ("aside", "ask", "bulk", "claim", "cf_type", "data", "device", "err", "f", "field", "form", "format", "give", "icon",
            "imp", "kind", "list", "period", "privacy", "prof", "receipt", "repaid", "req", "set", "sort", "status", "sub",
            "sub_kind", "sub_kind_hint", "sub_product", "tab", "time", "toast", "tone", "tpl", "type", "type_add", "type_hint",
            "warn", "year")


def strings() -> dict:
    return json.loads(STRINGS.read_text(encoding="utf-8"))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def config() -> dict:
    return yaml.safe_load(read(CONFIG)) or {}


class Strings(unittest.TestCase):
    def setUp(self):
        self.s = strings()

    def test_both_languages_same_placeholders(self):
        for key, v in self.s.items():
            self.assertTrue(key.startswith("expenses."), key)
            for lang in ("en", "es"):
                self.assertIsInstance(v.get(lang), str, f"{key} [{lang}]")
                self.assertTrue(v[lang].strip(), f"{key} [{lang}] is empty")
            self.assertEqual(sorted(PLACEHOLDER.findall(v["en"])), sorted(PLACEHOLDER.findall(v["es"])), f"{key}: placeholders differ")

    def test_wording_rules(self):
        for key, v in self.s.items():
            for lang in ("en", "es"):
                text = v[lang].lower()
                self.assertNotRegex(text, r"\bjob\b|\btrabajo\b", f"{key} [{lang}]: a service position, never a job")
                self.assertNotIn("pdf", text, f"{key} [{lang}]: say documents")
                self.assertNotRegex(text, r"crawl|scrap|\bbot\b|robot", f"{key} [{lang}]")
        self.assertEqual(self.s["expenses.data.erase_word"]["en"], "ERASE")
        self.assertEqual(self.s["expenses.data.erase_word"]["es"], "BORRAR")

    def test_literal_keys_exist(self):
        page, app = read(PAGE), read(APP)
        used = set(re.findall(r"""["'](expenses\.[a-z0-9_.]+)["']\s*\|\s*t\(""", page))
        for src in (page, app):
            # t('x') / t("x"), plural(n, 'a', 'b') and every quoted "prefix.key" (ternaries: t(a ? "x.y" : "x.z"))
            used |= {"expenses." + k for k in re.findall(r"""\bt\(\s*["']([a-z0-9_]+\.[a-z0-9_.]+)["']""", src)}
            for a, b in re.findall(r"""plural\([^,]+,\s*["']([a-z0-9_.]+)["']\s*,\s*["']([a-z0-9_.]+)["']""", src):
                used |= {"expenses." + a, "expenses." + b}
        # the app's own quoted "prefix.key" strings (ternaries: t(a ? "x.y" : "x.z")); not the page's, where
        # "form.date" / "f.q" are Alpine expressions
        for k in re.findall(r"""["']([a-z_]+\.[a-z0-9_]+)["']""", app):
            if k.split(".")[0] in PREFIXES and not k.endswith("_"):
                used.add("expenses." + k)
        used = {k for k in used if not k.endswith(".") and not k.endswith("_")}
        self.assertGreater(len(used), 300)
        missing = sorted(k for k in used if k not in self.s)
        self.assertEqual(missing, [], "keys used but missing from src/_i18n/expenses.json")
        # the page's other strings (shared keys) exist too
        common = json.loads((ROOT / "src" / "_i18n" / "common.json").read_text(encoding="utf-8"))
        for k in set(re.findall(r"""["']((?:common|nav)\.[a-z0-9_.]+)["']\s*\|\s*t""", page)) | {"nav.expenses", "nav.expenses_desc"}:
            self.assertIn(k, common, k)

    def test_keys_built_from_lists_exist(self):
        cfg = config()
        need = []
        for t in TYPES:
            need += [f"type.{t}", f"type_add.{t}", f"type_hint.{t}", f"field.description_{t}", f"form.description_ph_{t}",
                     f"form.title_add_{t}", f"form.title_edit_{t}"]
        need += [f"status.{s}" for s in ["none", "to_request", "submitted", "paid", "denied"]]
        need += [f"period.{p}" for p in ["this_month", "last_month", "this_year", "last_year", "panel", "all", "custom"]]
        need += [f"sort.{s}" for s in ["date_desc", "date_asc", "amount_desc", "amount_asc", "category", "updated"]]
        need += [f"format.{f}" for f in ["gv", "lv", "other", "none"]]
        need += [f"receipt.{r}" for r in ["none", "paper", "photo", "file"]] + [f"req.receipt_{r}" for r in ["none", "paper", "photo", "file"]]
        need += [f"sub_product.{p}" for p in ["gv_print", "gv_online", "gv_complete", "lv_print", "lv_online", "lv_complete", "other"]]
        need += [f"sub_kind.{k}" for k in ["gift", "helped", "group", "self"]] + [f"sub_kind_hint.{k}" for k in ["gift", "helped", "group", "self"]]
        need += [f"repaid.{r}" for r in ["owed", "repaid", "forgiven"]]
        need += [f"kind.{k}" for k in FUNDER_KINDS] + [f"tpl.{t}" for t in TEMPLATES]
        need += [f"cf_type.{c}" for c in ["text", "number", "date", "yesno", "choice"]]
        need += [f"tone.{t}" for t in cfg.get("tones", TONES)]
        need += ["icon." + i.replace("-", "_") for i in cfg.get("icons", [])]
        need += [f"tab.{v}" for v in ["entries", "summary", "giveaways", "requests", "settings"]]
        need += [f"set.{s}" for s in ["data", "profile", "categories", "funders", "methods", "mileage", "budgets", "fields", "reminders"]]
        need += [f"set.{k}{h}" for k in ["renewal_days", "backup_reminder_days"] for h in ("", "_hint")]
        need += [f"prof.{p}{h}" for p in ["name", "position", "district", "email"] for h in ("", "_hint")]
        need += [f"privacy.p{i}{h}" for i in range(1, 5) for h in ("", "_t")]
        need += [f"imp.map_{m}" for m in ["date", "description", "amount", "category", "miles", "notes"]]
        need += [f"field.quantity_{t}" for t in ["books", "printing", "giveaway", "stock"]]
        missing = sorted(k for k in need if "expenses." + k not in self.s)
        self.assertEqual(missing, [])

    def test_every_core_message_exists(self):
        if not CORE.exists():
            self.skipTest("expenses-core.js is not there yet")
        core = read(CORE)
        keys = set(re.findall(r'"(expenses\.(?:err|warn)\.[a-z0-9_]+)"', core))
        self.assertTrue(keys, "the core returns message keys")
        missing = sorted(k for k in keys if k not in self.s)
        self.assertEqual(missing, [], "message keys the core can return")
        # the words claimText / claimLines ask for by name
        words = {w for w in re.findall(r'word\(strings,\s*"([a-z_.]+)"', core) if not w.endswith(".")}
        self.assertTrue(words)
        self.assertEqual(sorted(w for w in words if "expenses." + w not in self.s), [])
        # …and the ones claimLines builds ("sub_kind." + e.sub_kind, "sub_product." + …) are covered above


class Config(unittest.TestCase):
    def setUp(self):
        self.c = config()

    def pairs_ok(self, v, where):
        self.assertIsInstance(v, dict, where)
        for lang in ("en", "es"):
            self.assertTrue(str(v.get(lang, "")).strip(), f"{where}: missing {lang}")

    def test_lists(self):
        c = self.c
        icons = c.get("icons", [])
        self.assertEqual(len(icons), len(set(icons)))
        for key in ("categories", "funders", "methods", "rates"):
            ids = [str(x["id"]) for x in c[key]]
            self.assertEqual(len(ids), len(set(ids)), f"{key}: duplicate id")
            for i in ids:
                self.assertRegex(i, r"^[a-z0-9_]+$")
        for cat in c["categories"]:
            where = f"category {cat['id']}"
            self.assertIn(cat["type"], TYPES, where)
            self.assertIn(cat["template"], TEMPLATES, where)
            self.assertIn(cat["color"], c.get("tones", TONES), where)
            self.assertIn(cat["icon"], icons, where)
            self.pairs_ok(cat["label"], where)
        for t in TYPES:
            self.assertTrue(any(cat["type"] == t for cat in c["categories"]), f"no category for {t}")
        funders = {f["id"]: f for f in c["funders"]}
        self.assertEqual(funders["me"]["kind"], "self")
        for f in c["funders"]:
            self.assertIn(f["kind"], FUNDER_KINDS)
            self.pairs_ok(f["name"], f"funder {f['id']}")
        for m in c["methods"]:
            self.pairs_ok(m["name"], f"method {m['id']}")
        self.assertIn("direct", [m["id"] for m in c["methods"]])
        for r in c["rates"]:
            self.pairs_ok(r["name"], f"rate {r['id']}")
            self.assertRegex(str(r.get("rate", "")), r"^(\d{1,2}(\.\d{1,3})?)?$")
        self.assertIn(c["default_rate"], [r["id"] for r in c["rates"]])
        self.assertIn(c["defaults"]["funder"], funders)
        self.assertIn(c["defaults"]["method"], [m["id"] for m in c["methods"]])
        for cat in c["categories"]:
            if "default_funder" in cat:
                self.assertIn(cat["default_funder"], funders)
        for p in c.get("panels", []):
            self.assertRegex(str(p["from"]), r"^\d{4}-\d{2}-\d{2}$")
            self.assertLessEqual(str(p["from"]), str(p["to"]))

    def test_the_spec_categories(self):
        ids = [cat["id"] for cat in self.c["categories"]]
        for i in ["books", "giveaways", "subscriptions", "lodging", "meals", "printing", "registration", "travel", "supplies", "postage",
                  "tech", "contributions", "other", "mileage", "reimbursement", "advance", "repayment", "sales", "received_other", "given", "stock_in"]:
            self.assertIn(i, ids)
        gift = next(cat for cat in self.c["categories"] if cat["id"] == "giveaways")
        self.assertTrue(gift.get("giveaway_default"))
        seventh = next(cat for cat in self.c["categories"] if cat["id"] == "contributions")
        self.assertEqual((seventh.get("default_funder"), seventh.get("default_claim")), ("me", "none"))

    def test_loader_builds_it_strictly(self):
        out = run_js(self, 'const m = await imp("src/_data/expenses.js"); out(m.default());')
        cfg = out["config"]
        self.assertTrue(all(cat["builtin"] and cat["label"]["en"] and cat["label"]["es"] for cat in cfg["categories"]))
        self.assertEqual([cat["order"] for cat in cfg["categories"]], list(range(len(cfg["categories"]))))
        self.assertEqual(cfg["default_rate"], "irs_charity")
        self.assertIn("book-open", out["icons"])
        self.assertEqual(out["ui"]["es"]["data.erase_word"], "BORRAR")
        self.assertNotIn("expenses.eyebrow", out["ui"]["en"])  # the prefix is taken off
        self.assertEqual(out["ui"]["en"]["eyebrow"], "Committee · Service expenses")


class Page(unittest.TestCase):
    def setUp(self):
        self.page, self.app = read(PAGE), read(APP)

    def test_front_matter(self):
        head = self.page.split("---", 2)[1]
        self.assertIn("pageKey: expenses", head)
        self.assertIn("titleKey: nav.expenses", head)
        self.assertIn("descKey: expenses.meta_desc", head)
        # the core first; committee.js runs the committee sub-nav
        self.assertIn('pageScripts: ["/assets/js/expenses-core.js", "/assets/js/expenses.js", "/assets/js/committee.js"]', head)

    def test_no_html_from_data(self):
        self.assertNotIn("x-html", self.page)
        self.assertEqual(len(re.findall(r"\.innerHTML\s*=[^=]", self.app)), 1)  # only x-xp-icon: the build's own icons
        self.assertIn('Alpine.data("xpApp"', self.app)
        self.assertIn('x-data="xpApp(', self.page)
        for i in ("xp-config", "xp-ui", "xp-events"):
            self.assertIn(f'id="{i}"', self.page)
            self.assertIn(f'"{i}"', self.app)

    def test_privacy_promises_hold(self):
        self.assertIn('var KEY = "gv-expenses:v1";', self.app)
        self.assertIn('var DB_NAME = "gv-expenses";', self.app)
        self.assertIn("navigator.storage.persist()", self.app)
        self.assertNotRegex(self.app, r"\bfetch\(|XMLHttpRequest|sendBeacon")   # nothing is uploaded

    def test_in_the_save_key_pages_list(self):
        out = run_js(self, """
          const SW = await imp("src/pages/sw.11ty.js");
          const code = SW.render({ build: { version: "t" }, orientation: { lessons: [] },
            collections: { all: ["/", "/tracker/", "/es/tracker/"].map((url) => ({ url })) } });
          out(JSON.parse(code.slice(code.indexOf("{"), code.indexOf("};") + 1)).save);
        """)
        self.assertIn("tracker/", out)

    def test_wired_into_the_site(self):
        css = read(ROOT / "src" / "assets" / "css" / "main.css")
        self.assertIn('@import "./areas/expenses.css";', css)
        nav = read(ROOT / "src" / "_data" / "nav.js")
        # under Committee, after the Bulletin (it was under Get involved at /expenses/)
        self.assertLess(nav.index('key: "nav.committee"'), nav.index('url: "/tracker/"'))
        self.assertLess(nav.index('url: "/bulletin/"'), nav.index('url: "/tracker/"'))
        self.assertNotIn('url: "/expenses/"', nav)
        self.assertIn('{ key: "tracker", url: "/tracker/"', read(ROOT / "eleventy" / "filters" / "committee.js"))
        self.assertIn('{% committeeNav lang, "tracker", db %}', read(PAGE))
        gvr = read(ROOT / "src" / "pages" / "gvr.njk")
        self.assertEqual(gvr.count("'/tracker/' | lurl(lang)"), 1, "one link from the GVR corner")
        # the old address still leads here
        stub = read(ROOT / "src" / "pages" / "expenses-redirect.njk")
        self.assertIn("expenses/index.html", stub)
        self.assertIn('"/tracker/" | lurl(lang)', stub)


if __name__ == "__main__":
    unittest.main()
