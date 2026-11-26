"""Round 33c · the magazine covers' slideshow holds exactly the covers on screen (src/assets/js/committee.js cmCovers
recount, on the page stand-in of tests/test_central_time.py — the real browser: tests/browser/test_cover_slideshow_browser.py).

The bug (live, 2026-11-17): /photos/?year=1948&month=9 showed 1 cover, yet its slideshow held 93 — every September of
every year, both magazines — and Next went to "Grapevine — September 1947", which was not on screen. With a Month
chosen the covers on screen share one slideshow ("covers-month": GLightbox groups the links by data-gallery), and
recount() put a cover in it when its MONTH matched — also inside the blocks the Magazine, Decade or Year hides.

Here, for every combination — a month alone, a year and a month, a decade and a month, a magazine and a month, a link
to a block while a month is on, then the filters cleared —:

  * the links in "covers-month" are exactly the covers on screen (their block shows — cmCovers.shows() — and the cover
    is of the month), in the page's order (the order they flow in on the flat grid);
  * every other cover is out of it (its block's id + "-off"), and with no Month each cover is back in its own block's
    slideshow (the gallery the page gave it: data-cm-gallery);
  * the slideshow reads the links again (CM.lightbox.elements = getElements() — never reload(), which would add a
    second click handler) whenever a cover moved, also when only the year changed and the month stayed.

Skipped without Node.js (tests/nodejs.py).

    python -m unittest tests.test_cover_slideshow -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
import test_central_time as TCT  # noqa: E402  (the page stand-in, TCT.DOM — a module, so its tests don't run twice)

ROOT = Path(__file__).resolve().parents[1]
COMMITTEE_JS = ROOT / "src" / "assets" / "js" / "committee.js"

SLIDES_JS = r"""
const chip = (attr, v) => el("button", { [attr]: v }, [el("span", { class: "cm-chip-count" }, [], "0")]);
const opt = (attr, v) => el("option", { value: v, [attr]: v, "data-label": v }, [], v);
const range = (a, b) => Array.from({ length: b - a + 1 }, (_, i) => String(a + i));
const LV = ["1 2", "3 4", "5 6", "7 8", "9 10", "11 12"];
function setup(search) {
  // the blocks as photos.njk makes them (the newest year first, Grapevine before La Viña; the newest issue first),
  // each cover's link in its block's slideshow (data-gallery = the block's id) and named by its block and months
  const lis = (id, ms) => ms.map((m) => el("li", { "data-months": m }, [
    el("a", { class: "cm-photo cm-cover glightbox-cm", "data-gallery": id, "data-title": id + " " + m })]));
  const block = (pub, year, ms) => {
    const id = `covers-${pub}-${year}`;
    return el("section", { id, "data-cm-cover": "", "data-mag": pub, "data-year": String(year), "data-count": String(ms.length),
      ...(year < 2025 ? { "data-cm-early": "" } : {}) }, lis(id, ms));
  };
  const blocks = [
    block("gv", 2026, range(1, 11).reverse()),
    block("lv", 2026, [...LV].reverse()),
    block("gv", 2025, range(1, 12).reverse()),
    block("lv", 2025, [...LV].reverse()),
    block("gv", 1948, range(1, 12).reverse()),
    block("gv", 1947, range(6, 12).reverse()),
  ];
  const bar = el("div", { class: "cm-covers-filter" }, [
    el("div", {}, ["", "gv", "lv"].map((m) => chip("data-cm-mag", m))),
    el("div", {}, ["", "2020", "1940"].map((d) => chip("data-cm-decade", d))),
    el("select", {}, ["2026", "2025", "1948", "1947"].map((y) => opt("data-cm-year", y))),
    el("select", {}, range(1, 12).map((m) => opt("data-cm-month", m)))]);
  const root = el("section", { id: "covers", "data-count-label": "Showing {n} covers", "data-count-label-one": "Showing 1 cover" },
                  [bar, ...blocks]);
  const p = page([root], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true });
  const L = p.win.location;
  L.pathname = "/photos/"; L.search = search || ""; L.hash = "";
  p.win.history.replaceState = (s, t, u) => {
    const m = /^([^?#]*)(\?[^#]*)?(#.*)?$/.exec(u);
    L.pathname = m[1]; L.search = m[2] || ""; L.hash = m[3] || "";
  };
  p.ready();
  // the slideshow (committee.js initLightbox: CM.lightbox) — how often it read the links' galleries again
  const lb = { reads: 0, elements: [], getElements() { this.reads++; return ["read " + this.reads]; } };
  p.win.CM.lightbox = lb;
  const c = p.comps.cmCovers();
  c.$root = root; c.$nextTick = (fn) => fn();
  El.prototype.scrollIntoView = function () {};
  El.prototype.focus = function () {};
  c.init();
  const links = () => blocks.flatMap((b) => b.querySelectorAll("a"));
  const snap = () => ({
    state: [c.mag, c.decade, c.year, c.month], n: c.visibleCount, reads: lb.reads, elements: lb.elements,
    // the covers on screen: their block shows (its x-show) and the cover is not hidden inside it — page order
    onScreen: blocks.filter((b) => c.shows(b)).flatMap((b) => b.querySelectorAll("li").filter((li) => !li.hidden))
      .map((li) => li.querySelector("a").getAttribute("data-title")),
    month: links().filter((a) => a.getAttribute("data-gallery") === "covers-month").map((a) => a.getAttribute("data-title")),
    // every other link: [its gallery, the block it is in]
    others: links().filter((a) => a.getAttribute("data-gallery") !== "covers-month")
      .map((a) => [a.getAttribute("data-gallery"), a.closest("[data-cm-cover]").attrs.id]),
    home: links().every((a) => a.getAttribute("data-cm-gallery") === a.closest("[data-cm-cover]").attrs.id),
  });
  return { c, snap, hash: (h) => { L.hash = h; p.fireWin("hashchange"); return snap(); } };
}
const res = {};
// the bug's own address, then a link that sets the filter, then other years and the month let go
{
  const { c, snap } = setup("?year=1948&month=9");
  res.y1948m9 = snap();
  c.setYear("1947"); res.y1947m9 = snap();
  c.setYear("2026"); res.y2026m9 = snap();
  c.setMonth(""); res.y2026 = snap();
  c.clear(); res.cleared = snap();
}
// a month alone; then a decade, a magazine (the decade has no La Viña: it lets go), a year, clear
{
  const { c, snap } = setup("?month=9");
  res.m9 = snap();
  c.setDecade("1940"); res.d1940m9 = snap();
  c.setMag("lv"); res.lvm9 = snap();
  c.setMonth("3"); res.lvm3 = snap();
  c.setYear("2025"); res.lv2025m3 = snap();
  c.setMag(""); res.y2025m3 = snap();
  c.clear(); res.cleared2 = snap();
}
// the address with a decade and a month; with a magazine and a month
res.urlDecade = setup("?decade=1940&month=12").snap();
res.urlMag = setup("?mag=gv&month=7").snap();
// a link to a block while only a month is on: that block's magazine and year, the month let go — back in its block
{
  const { hash } = setup("?month=9");
  res.link = hash("#covers-gv-1947");
}
out(res);
"""


class SlideshowHoldsTheCoversOnScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if SlideshowHoldsTheCoversOnScreen.r is None:
            SlideshowHoldsTheCoversOnScreen.r = run_js(self, TCT.DOM + SLIDES_JS, needs_modules=True, timeout=120)
        self.r = SlideshowHoldsTheCoversOnScreen.r

    def same(self, key: str, state: list, covers: list[str]):
        s = self.r[key]
        self.assertEqual(s["state"], state, key)
        self.assertEqual(s["onScreen"], covers, f"{key}: the covers on screen")
        self.assertEqual(s["month"], covers, f"{key}: the slideshow holds exactly them, in the page's order")
        self.assertEqual(s["n"], len(covers), f"{key}: the live count says so too")
        for gallery, block in s["others"]:
            self.assertEqual(gallery, block + "-off", f"{key}: every other cover is out of it ({block})")
        self.assertTrue(s["home"], f"{key}: each link still knows its own block's slideshow")

    def test_the_bugs_address_a_year_and_a_month(self):
        # /photos/?year=1948&month=9: ONE cover on screen, ONE slide (it was every September: 4 here, 93 live)
        self.same("y1948m9", ["", "1940", "1948", "9"], ["covers-gv-1948 9"])
        self.same("y1947m9", ["", "1940", "1947", "9"], ["covers-gv-1947 9"])
        self.same("y2026m9", ["", "2020", "2026", "9"], ["covers-gv-2026 9", "covers-lv-2026 9 10"])

    def test_a_month_alone_every_september_in_the_pages_order(self):
        self.same("m9", ["", "", "", "9"], ["covers-gv-2026 9", "covers-lv-2026 9 10", "covers-gv-2025 9",
                                             "covers-lv-2025 9 10", "covers-gv-1948 9", "covers-gv-1947 9"])

    def test_a_decade_and_a_month(self):
        self.same("d1940m9", ["", "1940", "", "9"], ["covers-gv-1948 9", "covers-gv-1947 9"])
        self.same("urlDecade", ["", "1940", "", "12"], ["covers-gv-1948 12", "covers-gv-1947 12"])

    def test_a_magazine_and_a_month(self):
        # La Viña has no 1940s: the decade lets go, the month stays — La Viña's Septembers only
        self.same("lvm9", ["lv", "", "", "9"], ["covers-lv-2026 9 10", "covers-lv-2025 9 10"])
        self.same("lvm3", ["lv", "", "", "3"], ["covers-lv-2026 3 4", "covers-lv-2025 3 4"])
        self.same("lv2025m3", ["lv", "2020", "2025", "3"], ["covers-lv-2025 3 4"])
        self.same("y2025m3", ["", "2020", "2025", "3"], ["covers-gv-2025 3", "covers-lv-2025 3 4"])
        self.same("urlMag", ["gv", "", "", "7"], ["covers-gv-2026 7", "covers-gv-2025 7", "covers-gv-1948 7", "covers-gv-1947 7"])

    def test_no_month_each_cover_back_in_its_own_blocks_slideshow(self):
        for key in ("y2026", "cleared", "cleared2", "link"):
            with self.subTest(key=key):
                s = self.r[key]
                self.assertEqual(s["state"][3], "", key)
                self.assertEqual(s["month"], [], f"{key}: no shared slideshow")
                for gallery, block in s["others"]:
                    self.assertEqual(gallery, block, f"{key}: back in its block's slideshow")
        # a link to a block while a month was on: that magazine and year, the month let go
        self.assertEqual(self.r["link"]["state"], ["gv", "1940", "1947", ""])

    def test_the_slideshow_reads_the_links_again_when_a_cover_moved(self):
        # each change above moved covers in or out (also a year changed with the month kept): read again each time
        reads = [self.r[k]["reads"] for k in ("y1948m9", "y1947m9", "y2026m9", "y2026", "cleared")]
        self.assertEqual(reads, [1, 2, 3, 4, 4], "cleared from a year alone: nothing moved, nothing read")
        self.assertEqual(self.r["cleared"]["elements"], ["read 4"], "CM.lightbox.elements = getElements()")

    def test_the_script_never_reloads_the_slideshow(self):
        src = COMMITTEE_JS.read_text(encoding="utf-8")
        body = src[src.index('Alpine.data("cmCovers"'):src.index("/* /portfolio/")]
        code = "\n".join(line.split("//")[0] for line in body.splitlines())
        self.assertNotIn(".reload(", code, "reload() would add a second click handler (round 31)")
        self.assertRegex(code, r"lb\.elements = lb\.getElements\(\)")
        # the cover's gallery looks at its block on screen (shows()), not at its month alone
        self.assertRegex(code, r"self\.shows\(b\)")
        # (ES5 in this script: no arrows, ?. or ?? in the part that changed)
        recount = body[body.index("recount: function"):body.index("readUrl: function")]
        self.assertFalse(re.search(r"=>|\?\.|\?\?", recount), "ES5 style")


if __name__ == "__main__":
    unittest.main()
