"""Round 30 — the committee's pinned flyers on the Portfolio (/portfolio/): config/site.yml drive.pinned_flyers, a list of
patterns in the committee's order (eleventy/filters/committee.js docTeaser — the cmDocTeaser filter — and documentTabs,
src/pages/portfolio.njk):

  * "Flyers to share", the hero's right-hand card (docTeaser): the pinned flyers first, in the settings' order — each
    the newest flyer its pattern finds (title as uploaded, English or Spanish title, file name; capitals ignored) that
    an earlier pattern did not take —, then the newest others, max(2, min(4, patterns)) files in all: a pattern that
    finds nothing leaves its place to the newest other flyer; one file two patterns find shows once; a pattern the
    site cannot read is skipped (it counts for nothing) and nothing warns; one pattern written without "- " counts;
    no patterns → the 2 newest flyers; Flyers as the list's first category → "Latest upload", pins playing no part;
    /es/ finds the same files and shows their Spanish titles;
  * the Flyers list (documentTabs with the same patterns): the same pinned flyers first, `pinned: true`, the others
    newest first; the other categories never change order (and without patterns nothing is pinned);
  * the built /portfolio/ (ONLY portfolio.njk, the test's own Drive files and settings), English and Spanish: four
    patterns → four compact rows in the hero (hero-aside-rows, square pictures, the title only), in the settings'
    order; the Flyers list opens with the same four, each "Pinned" / "Fijado", the fifth without; no patterns → two
    tiles, the two newest, and no badge;
  * RealSettings (the publish gate's CONTENT_TESTS): config/site.yml's four patterns find, in order, "2027 Guest
    Speaker Series - flyer", "Our online meetings - flyer", "Grapevine Meeting - flyer" and "Committee Meeting -
    flyer" among the committee's Drive names — each exactly its own file, never "August 2027 Committee Meeting -
    guest speaker".

    python -m unittest tests.test_r30_portfolio -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from nodejs import run_js  # noqa: E402

PINS = ["guest speaker series *[-–—] *flyer", "our online meetings *[-–—] *flyer", "^grapevine meeting *[-–—] *flyer",
        "^committee meeting *[-–—] *flyer"]


def drive_item(n: int, title: str, date: str, es: str | None = None, category: str = "flyers", kind: str = "photo",
               mime: str = "image/png", name: str | None = None) -> dict:
    """A Drive file as data/site/drive.json lists it (the fields the Portfolio reads)."""
    view = f"https://drive.google.com/file/d/file{n:02d}/view"
    return {
        "id": f"drive:file{n:02d}", "source": "drive", "kind": kind, "category": category, "status": "ok",
        "title": title, "lang": "en", "date": date, "first_seen": date + "T08:00:00Z", "url": view, "is_new": False,
        "extra": {"name": name or title + (".png" if kind == "photo" else ".pdf"), "mime": mime, "panel": 77,
                  "panel_label": "Panel 77", "path": [category], "view_url": view,
                  "thumb_url": f"https://lh3.googleusercontent.com/d/file{n:02d}=w600"},
        "i18n": {"title": {"en": title, "es": es or title}},
    }


# The committee's flyers (the Drive's names, some of them; dated as uploaded — the four pinned ones are NOT the
# newest) and a report, so that Flyers is not the list's first category
FILES = [
    drive_item(1, "Annual report 2027", "2026-11-20", "Informe anual 2027", category="reports", kind="document", mime="application/pdf"),
    drive_item(2, "Taller de Escritura de La Viña - Grupo Libro Grande, Tyler", "2026-11-14"),
    drive_item(3, "August 2027 Committee Meeting - guest speaker", "2026-11-13", "Reunión del comité de agosto de 2027 - oradora invitada"),
    drive_item(4, "Committee Meeting - flyer", "2026-11-12", "Reunión del comité - volante"),
    drive_item(5, "Grapevine Meeting - flyer", "2026-11-12", "Reunión de Grapevine (en inglés) - volante"),
    drive_item(6, "Our online meetings - flyer", "2026-11-12", "Nuestras reuniones en línea - volante"),
    drive_item(7, "2027 Guest Speaker Series - flyer", "2026-11-10", "Ciclo de oradores invitados 2027 - volante"),
    drive_item(8, "Free shipping on all Grapevine products - banner", "2026-11-02", "Envío gratis en todos los productos de Grapevine - banner"),
]
TITLES = {it["id"]: it["title"] for it in FILES}

TEASER_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const ids = (t) => t && { kind: t.kind, tab: t.tab.key, ids: t.docs.map((d) => d.id), titles: t.docs.map((d) => d.title), pinned: t.pinned };
const res = {};
for (const [name, pins, lang, files] of input.cases) {
  const dt = C.documentTabs(files || input.files, lang || "en", pins);
  res[name] = ids(C.docTeaser(dt, pins));
  // the same through the page's filter
  res[name + ":filter"] = ids(filters.cmDocTeaser(dt, pins));
}
// the Flyers list (documentTabs with the patterns); the other categories as they were
const tabs = (pins, lang) => Object.fromEntries(C.documentTabs(input.files, lang || "en", pins).tabs.filter((t) => t.count)
  .map((t) => [t.key, t.items.map((d) => [d.id, !!d.pinned])]));
res.tabs = tabs(input.pins);
res.tabsEs = tabs(input.pins, "es");
res.tabsNone = tabs(undefined);
res.filterTabs = Object.fromEntries(filters.cmDocTabs(input.files, "en", input.pins).tabs.filter((t) => t.count).map((t) => [t.key, t.items.map((d) => d.id)]));
out(res);
"""


class Teaser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        only_flyers = [f for f in FILES if f["category"] == "flyers"] + [
            drive_item(9, "Sign-up sheet", "2026-11-25", category="forms", kind="form", mime="application/vnd.google-apps.form")]
        cases = [
            ["four", PINS], ["none", None], ["empty", []], ["blank", ["", "  "]], ["object", [{"a": 1}]],
            ["reversed", list(reversed(PINS))],
            ["missing", [PINS[0], "no such flyer", PINS[2], PINS[3]]],
            ["two", [PINS[2], PINS[3]]], ["one", PINS[2]], ["string", "^grapevine meeting"],
            ["bad", ["(", PINS[2]]], ["allBad", ["(", "[", "*"]],
            ["twice", ["meeting *[-–—] *flyer", PINS[2], PINS[3]]],
            ["six", PINS + ["banner", "taller"]],
            ["es", PINS, "es"], ["firstTab", PINS, "en", only_flyers],
        ]
        cls.r = run_js(cls, TEASER_JS, data={"cases": cases, "files": FILES, "pins": PINS})

    def ids(self, name: str) -> list[str]:
        return self.r[name]["ids"]

    def test_the_settings_order_beats_the_newest(self):
        self.assertEqual(self.ids("four"), ["drive:file07", "drive:file06", "drive:file05", "drive:file04"])
        self.assertEqual([TITLES[i] for i in self.ids("four")], ["2027 Guest Speaker Series - flyer", "Our online meetings - flyer",
                                                                 "Grapevine Meeting - flyer", "Committee Meeting - flyer"])
        self.assertEqual((self.r["four"]["kind"], self.r["four"]["tab"], self.r["four"]["pinned"]), ("flyers", "flyers", 4))
        self.assertEqual(self.ids("reversed"), list(reversed(self.ids("four"))))
        for name in [k for k in self.r if k.endswith(":filter")]:
            self.assertEqual(self.r[name], self.r[name.split(":")[0]], name)

    def test_no_patterns_the_two_newest(self):
        for name in ("none", "empty", "blank", "object", "allBad"):
            with self.subTest(name):
                self.assertEqual(self.ids(name), ["drive:file02", "drive:file03"])
                self.assertEqual(self.r[name]["pinned"], 0)

    def test_a_pattern_that_finds_nothing_leaves_its_place_to_the_newest(self):
        self.assertEqual(self.ids("missing"), ["drive:file07", "drive:file05", "drive:file04", "drive:file02"])
        self.assertEqual(self.r["missing"]["pinned"], 3)

    def test_as_many_as_the_patterns_two_to_four(self):
        self.assertEqual(self.ids("two"), ["drive:file05", "drive:file04"])
        # one pattern: the pinned one and the newest other (one written without "- " counts too)
        self.assertEqual(self.ids("one"), ["drive:file05", "drive:file02"])
        self.assertEqual(self.ids("string"), ["drive:file05", "drive:file02"])
        self.assertEqual(self.r["string"]["pinned"], 1)
        # six patterns: four at most
        self.assertEqual(self.ids("six"), self.ids("four"))

    def test_a_pattern_the_site_cannot_read_is_skipped(self):
        self.assertEqual(self.ids("bad"), ["drive:file05", "drive:file02"])

    def test_one_file_two_patterns_find_shows_once(self):
        # "meeting - flyer" takes the newest it finds (Committee Meeting - flyer: the same day, A→Z first), "^grapevine
        # meeting" the Grapevine Meeting's, "^committee meeting" nothing left: its place goes to the newest other one
        got = self.ids("twice")
        self.assertEqual(len(got), len(set(got)))
        self.assertEqual(got, ["drive:file04", "drive:file05", "drive:file02"])

    def test_spanish_page_same_files_spanish_titles(self):
        self.assertEqual(self.ids("es"), self.ids("four"))
        self.assertEqual(self.r["es"]["titles"], ["Ciclo de oradores invitados 2027 - volante", "Nuestras reuniones en línea - volante",
                                                  "Reunión de Grapevine (en inglés) - volante", "Reunión del comité - volante"])

    def test_flyers_as_the_first_category_latest_upload(self):
        self.assertEqual((self.r["firstTab"]["kind"], self.r["firstTab"]["ids"], self.r["firstTab"]["pinned"]),
                         ("latest", ["drive:file09"], 0))

    def test_the_flyers_list_starts_with_them(self):
        flyers = self.r["tabs"]["flyers"]
        self.assertEqual(flyers[:5], [["drive:file07", True], ["drive:file06", True], ["drive:file05", True],
                                      ["drive:file04", True], ["drive:file02", False]])
        self.assertEqual([i for i, _ in flyers[4:]], ["drive:file02", "drive:file03", "drive:file08"], "the others newest first")
        self.assertEqual(self.r["tabsEs"]["flyers"], flyers)
        self.assertEqual(self.r["tabs"]["reports"], [["drive:file01", False]])
        self.assertEqual([i for i, _ in self.r["tabsNone"]["flyers"]], ["drive:file02", "drive:file03", "drive:file04", "drive:file05",
                                                                        "drive:file06", "drive:file07", "drive:file08"])
        self.assertFalse([p for _, p in self.r["tabsNone"]["flyers"] if p])
        self.assertEqual(self.r["filterTabs"]["flyers"], [i for i, _ in flyers])


# =========================================================================== the built page
PAGES_JS = r"""
process.env.ONLY = "portfolio.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const res = {};
for (const [name, pins] of input.cases) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r30-portfolio-"));
  try {
    const elev = new Eleventy("src", dir, {
      quietMode: true, configPath: "eleventy.config.js",
      config(c) {
        c.addGlobalData("eleventyComputed", {
          db: (data) => ({ ...data.db, drive: { updated: null, items: input.files } }),
          site: (data) => ({ ...data.site, drive: { ...data.site.drive, pinned_flyers: pins } }),
        });
      },
    });
    const pages = await elev.toJSON();
    res[name] = Object.fromEntries(pages.filter((p) => p.url === "/portfolio/" || p.url === "/es/portfolio/").map((p) => [p.url, p.content]));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
out(res);
"""


def words(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", " ", fragment, flags=re.S)))).strip()


class BuiltPortfolio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = run_js(cls, PAGES_JS, data={"cases": [["pins", PINS], ["none", None]], "files": FILES}, timeout=900)

    def aside(self, page: str) -> str:
        i = page.index('id="docs-aside-title"')
        return page[page.rindex("<section", 0, i):page.index("</section>", i)]

    def test_four_rows_in_the_hero_in_the_settings_order(self):
        for url, titles in (("/portfolio/", ["2027 Guest Speaker Series - flyer", "Our online meetings - flyer", "Grapevine Meeting - flyer",
                                             "Committee Meeting - flyer"]),
                            ("/es/portfolio/", ["Ciclo de oradores invitados 2027 - volante", "Nuestras reuniones en línea - volante",
                                                "Reunión de Grapevine (en inglés) - volante", "Reunión del comité - volante"])):
            aside = self.aside(self.p["pins"][url])
            with self.subTest(url=url):
                self.assertIn('<ul class="hero-aside-rows" role="list">', aside)
                got = [html.unescape(t) for t in re.findall(r'<span class="hero-aside-item-title">(.*?)</span>', aside)]
                self.assertEqual(got, titles)
                self.assertEqual(aside.count('class="hero-aside-thumb is-square cm-ha-doc"'), 4)
                self.assertNotIn("hero-aside-item-text", aside, "the title only in a row")
                self.assertIn('href="#docs-flyers"', aside)

    def test_the_flyers_list_opens_with_them_pinned(self):
        for url, badge in (("/portfolio/", "Pinned"), ("/es/portfolio/", "Fijado")):
            page = self.p["pins"][url]
            sec = page[page.index('<section id="docs-flyers"'):]
            sec = sec[:sec.index("</section>")]
            cards = re.findall(r'<article class="card cm-doc .*?</article>', sec, re.S)
            with self.subTest(url=url):
                self.assertEqual(len(cards), 7)
                self.assertEqual([badge in words(c) for c in cards], [True] * 4 + [False] * 3)
                self.assertEqual([re.search(r'file/d/(file\d\d)/view', c).group(1) for c in cards[:5]],
                                 ["file07", "file06", "file05", "file04", "file02"])
                self.assertIn("#i-pin", cards[0])
                # the other category stays as it was: no badge
                self.assertNotIn(badge, words(page[page.index('<section id="docs-reports"'):page.index('<section id="docs-flyers"')]))

    def test_without_patterns_two_tiles_and_no_badge(self):
        for url in ("/portfolio/", "/es/portfolio/"):
            page = self.p["none"][url]
            aside = self.aside(page)
            with self.subTest(url=url):
                self.assertIn('<ul class="hero-aside-tiles" role="list">', aside)
                self.assertEqual(len(re.findall(r'<span class="hero-aside-item-title">', aside)), 2)
                self.assertIn("Taller de Escritura de La Viña - Grupo Libro Grande, Tyler", html.unescape(aside))
                self.assertNotRegex(page, r'<span class="badge-lv">\s*<svg[^>]*>\s*<use href="#i-pin"')

    def test_every_id_once(self):
        for name in ("pins", "none"):
            for url, page in self.p[name].items():
                ids = re.findall(r'\sid="([^"]+)"', page)
                with self.subTest(case=name, url=url):
                    self.assertEqual(sorted({i for i in ids if ids.count(i) > 1}), [])


# =========================================================================== config/site.yml as the committee keeps it
# The committee's flyers on the Drive (their file names; data/site/drive.json has the same, November 2026)
REAL_NAMES = [
    "2027 Guest Speaker Series - flyer.png", "Our online meetings - flyer.png", "Grapevine Meeting - flyer.png",
    "Committee Meeting - flyer.png", "Grapevine Weekly Open AA Meeting - every Wednesday, 11 AM Central (noon Eastern), on Zoom.png",
    *[f"{m} 2027 Committee Meeting - guest speaker.png" for m in (
        "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")],
    "Free shipping on all Grapevine products - banner.png", "Grapevine Writing Workshop - Primary Purpose Group, Arlington.png",
]

REAL_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const items = input.names.map((name, i) => ({ id: "drive:f" + i, source: "drive", kind: "photo", category: "flyers", status: "ok",
  title: name.replace(/\.png$/, ""), date: "2026-11-12", extra: { name, mime: "image/png", path: ["flyers"] } }));
const report = { id: "drive:r", source: "drive", kind: "document", category: "reports", status: "ok", title: "Report", date: "2026-11-01",
  extra: { name: "Report.pdf", mime: "application/pdf", path: ["reports"] } };
const t = C.docTeaser(C.documentTabs([report, ...items], "en", input.pins), input.pins);
out({ teaser: t.docs.map((d) => d.item.extra.name), pinned: t.pinned,
      each: input.pins.map((p) => C.driveMatch(items, p, "flyers", 99).map((it) => it.extra.name)),
      august: input.pins.filter((p) => C.driveMatch(items.filter((it) => it.extra.name.startsWith("August")), p, "flyers"))});
"""


class RealSettings(unittest.TestCase):
    """config/site.yml drive.pinned_flyers as the committee keeps it (scripts/ops/gate_tests.py CONTENT_TESTS)."""

    def test_each_pattern_finds_its_flyer(self):
        pins = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))["drive"]["pinned_flyers"]
        self.assertEqual(len(pins), 4)
        r = run_js(self, REAL_JS, data={"names": REAL_NAMES, "pins": pins})
        want = ["2027 Guest Speaker Series - flyer.png", "Our online meetings - flyer.png", "Grapevine Meeting - flyer.png",
                "Committee Meeting - flyer.png"]
        self.assertEqual((r["teaser"], r["pinned"]), (want, 4))
        self.assertEqual(r["each"], [[w] for w in want], "each pattern: exactly its own file")
        self.assertEqual(r["august"], [], "never a month's guest-speaker flyer")


if __name__ == "__main__":
    unittest.main()
