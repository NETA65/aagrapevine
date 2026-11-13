"""The magazine covers on /photos/ (round 29): the page's side of the Grapevine and La Viña covers the committee keeps on
its Drive (photos/AAGrapevine_covers/<year>/GV_2026-11_November.jpg, photos/AALavina_covers/<year>/LaVina_2026-06_
Noviembre-Diciembre.jpg). The Drive sync marks each with extra.cover = { pub, year, month | issue, months, key } and
files it in the album "Grapevine covers 2026" / "La Viña covers 2026" (docs/DATA_SCHEMA.md); here, with covers made
in that shape:

  * Albums (eleventy/filters/committee.js photoAlbums, coverIssueLabel) — the covers are grouped by magazine and
    year (never by Drive's folder names), after the committee's own albums: the newest year first, Grapevine before
    La Viña in a year, covers without a year last; each block's covers newest issue first, named as /read/ names
    the issues ("November 2026" / "Noviembre 2026"; La Viña "November–December 2026" / "Noviembre–Diciembre 2026"),
    with the alt text and the lightbox's lines (the publisher's credit). Each block keeps the generic ids a link
    made the usual way points at (albumAnchors' slug — photoAlbumSlugs, the digest's — and What's New's alias, the
    twin of build_data.album_slug). The committee's own albums and the loose photos are as before.
  * The shelf (coverShelf): the two collections ("131 covers · 2015–2026", the 3 newest at =w300), the years, the
    total, the earlier years the page folds away at first (every year but the 2 newest); a block's tiles at =w400
    (driveImageWidth: a Drive thumbnail's "=w600" ending, an address without one as it is).
  * Search (eleventy/filters/library.js): one entry per cover album, found by any of its issues in both languages,
    linking to the album with the filter set (/photos/?mag=gv&year=2019#covers-gv-2019) — never one per cover.
  * The filter in the browser (src/assets/js/committee.js cmCovers, on the page stand-in of
    tests/test_central_time.py): its chips' counts follow the magazine, a year the magazine lacks falls back to All
    years, the address keeps the filter (unknown values left out), a link to a magazine / a block / a block's
    generic id sets it (or resets it) and brings into view the filter (when the link set it) or the target, the
    live count speaks only after a change; with no filter on only the 2 newest years show until "Show earlier
    years" (a filter shows every block it matches; clearing it folds them away again until that was asked for).
  * The page (src/pages/photos.njk, built with Eleventy, English and Spanish): the hero's copyright line (always,
    also without covers), its numbers (albums and photos: the committee's own; magazine covers apart; "1 album"),
    the description (it names the covers only when there are some), "Protecting anonymity" right after the
    committee's albums and before the covers, the covers section with its filter, blocks (Full screen and Share
    only with JavaScript, ↑ back to the filter), the earlier years folded away behind "Show earlier years
    (2015–2024)", anchors (no id twice), tiles and the member help's covers step (last); without covers no covers
    section.
  * What's New and the RSS feed (whats-new.njk, feed.11ty.js): the covers' entries (build_data.cover_news) carry no
    "Originally in …" language pill (their words are written in both languages), and the feed files them under
    "Magazine covers", not "Committee uploads".

Skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_photos_covers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
import test_central_time as TCT  # noqa: E402  (the page stand-in, TCT.DOM — a module, so its tests don't run twice)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]
MONTHS_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre"]
SEEN = "2026-11-13T12:00:00Z"


def photo(iid: str, date: str | None, album: str | None, title: str, **extra) -> dict:
    """A Drive photo as data/site/drive.json has it."""
    x = {"file_id": iid, "mime": "image/jpeg", "name": title + ".jpg", "panel": 77, "panel_label": "Panel 77 (2027–2028)",
         "path": ["photos"] + ([album] if album else []), "album": album,
         "thumb_url": f"https://lh3.googleusercontent.com/d/{iid}=w600", "image_url": f"https://lh3.googleusercontent.com/d/{iid}=w1600",
         "view_url": f"https://drive.google.com/file/d/{iid}/view", "is_image": True, **extra}
    return {"id": f"drive:{iid}", "source": "drive", "kind": "photo", "url": x["view_url"], "title": title, "summary": "",
            "lang": "en", "date": date, "first_seen": SEEN, "image": x["thumb_url"], "tags": [], "category": "photos",
            "status": "ok", "extra": x, "i18n": {"title": {"en": title, "es": title}}, "machine": [], "is_new": False}


def cover(pub: str, year: int | None, n: int | None, *, name: str = "", new: bool = False, status: str = "ok") -> dict:
    """A cover in the data contract (DESIGN-29 §1): n = Grapevine's month or La Viña's issue (1–6); None: a file whose
    name gives no issue (`name` then is its title)."""
    if pub == "gv":
        months = [n] if n else []
        stem = name or f"GV_{year}-{n:02d}_{MONTHS_EN[n - 1]}"
        t_en = name or f"Grapevine — {MONTHS_EN[n - 1]} {year}"
        t_es = name or f"Grapevine — {MONTHS_ES[n - 1]} {year}"
        album = f"Grapevine covers {year}" if year else "Grapevine covers"
        album_es = f"Portadas de Grapevine {year}" if year else "Portadas de Grapevine"
        folder = "AAGrapevine_covers"
    else:
        months = [2 * n - 1, 2 * n] if n else []
        stem = name or f"LaVina_{year}-{n:02d}_{MONTHS_ES[2 * n - 2]}-{MONTHS_ES[2 * n - 1]}"
        t_en = name or f"La Viña — {MONTHS_EN[2 * n - 2]}–{MONTHS_EN[2 * n - 1]} {year}"
        t_es = name or f"La Viña — {MONTHS_ES[2 * n - 2]}–{MONTHS_ES[2 * n - 1]} {year}"
        album = f"La Viña covers {year}" if year else "La Viña covers"
        album_es = f"Portadas de La Viña {year}" if year else "Portadas de La Viña"
        folder = "AALavina_covers"
    key = f"{year}-{months[0]:02d}" if months else ""
    iid = re.sub(r"[^A-Za-z0-9]", "", stem) + "x"
    it = photo(iid, (key + "-01") if key else (f"{year}-01-01" if year else None), album, t_en,
               cover={"pub": pub, "year": year, "month": n if pub == "gv" else None, "issue": n if pub == "lv" else None,
                      "months": months, "key": key})
    it["extra"]["path"] = ["photos", folder] + ([str(year)] if year else [])
    it["lang"] = "en" if pub == "gv" else "es"
    it["i18n"] = {"title": {"en": t_en, "es": t_es}, "album": {"en": album, "es": album_es}}
    it["is_new"] = new
    it["status"] = status
    return it


def sample() -> list[dict]:
    """Two albums of the committee's own (and the 2 loose photos), and covers of both magazines over some years —
    one new issue, a file whose name gives no issue, one without a year, one gone."""
    return [
        photo("loose1", "2026-11-11", None, "2026 Dallas Gathering Of Eagles"),
        photo("loose2", "2026-10-30", None, "2025 Sales Report"),
        photo("fall1", "2026-10-03", "Fall Assembly 2026", "Booth"),
        photo("fall2", "2026-10-03", "Fall Assembly 2026", "Table"),
        cover("gv", 2026, 1), cover("gv", 2026, 11, new=True), cover("gv", 2026, 10),
        cover("lv", 2026, 1), cover("lv", 2026, 6),
        cover("gv", 2025, 12),
        cover("gv", 2024, None, name="GV special edition 2024"),
        cover("lv", 2016, 3),
        cover("gv", 2015, 7),
        cover("gv", None, None, name="GV poster"),
        cover("gv", 2023, 5, status="gone"),
    ]


ALBUMS_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const res = {};
for (const lang of ["en", "es"]) {
  const albums = filters.cmAlbums(input.items, lang);
  const shelf = filters.cmCovers(albums, lang);
  res[lang] = {
    albums: albums.map((a) => ({ slug: a.slug, alias: a.alias, title: a.title, count: a.count, covers: a.covers, anchors: a.anchors,
      items: a.items.map((p) => ({ id: p.id, label: p.label || null, alt: p.alt || null, lbTitle: p.lbTitle || null, lbDesc: p.lbDesc || null })) })),
    shelf: { total: shelf.total, years: shelf.years, earlier: shelf.earlier,
      mags: shelf.mags.map((m) => ({ ...m, cover: m.cover.map((p) => p.id), coverThumbs: m.cover.map((p) => p.thumb) })),
      firsts: shelf.albums.filter((a) => a.covers.first).map((a) => a.slug),
      early: shelf.albums.filter((a) => a.covers.early).map((a) => a.slug) },
    tiles: albums.filter((a) => a.covers).flatMap((a) => a.items.map((p) => [p.tile, p.thumb, p.full])),
  };
}
res.slugs = Object.fromEntries(C.photoAlbumSlugs(input.items));
res.labels = ["en", "es"].map((l) => [C.coverIssueLabel({ pub: "gv", key: "2026-11" }, l), C.coverIssueLabel({ pub: "lv", key: "2026-11" }, l),
  C.coverIssueLabel({ pub: "lv", key: "2027-01" }, l), C.coverIssueLabel({ pub: "gv", key: "" }, l)]);
res.widths = [C.driveImageWidth("https://lh3.googleusercontent.com/d/abc=w600", 300), C.driveImageWidth("https://lh3.googleusercontent.com/d/abc=w1600", 400),
  C.driveImageWidth("https://lh3.googleusercontent.com/d/abc", 300), C.driveImageWidth("https://drive.google.com/thumbnail?id=abc&sz=w600", 300),
  C.driveImageWidth("https://example.org/covers/gv-2026-11.jpg", 300),
  C.driveImageWidth("", 300), C.driveImageWidth(null, 300), C.driveImageWidth("https://lh3.googleusercontent.com/d/abc=w600", 0)];
out(res);
"""

SEARCH_JS = r"""
const site = (await imp("src/_data/site.js")).default;
const S = typeof site === "function" ? await site() : site;
const res = {};
for (const lang of ["en", "es"]) {
  const items = JSON.parse(filters.searchIndexJson({ drive: { items: input.items } }, [], lang, S)).items;
  res[lang] = items.filter((e) => e.k === "album" || e.k === "photo");
}
out(res);
"""


class Albums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = sample()

    def setUp(self):
        if not hasattr(Albums, "_r"):
            Albums._r = run_js(self, ALBUMS_JS, data={"items": self.items})
        self.r = Albums._r

    def test_the_committees_albums_first_then_the_covers_by_year_and_magazine(self):
        slugs = [a["slug"] for a in self.r["en"]["albums"]]
        self.assertEqual(slugs, ["album-panel-77-2027-2028", "album-fall-assembly-2026",
                                 "covers-gv-2026", "covers-lv-2026", "covers-gv-2025", "covers-gv-2024", "covers-lv-2016",
                                 "covers-gv-2015", "covers-gv-undated"])
        # the committee's own albums are as before: their anchors (the What's New alias), no covers
        own = {a["slug"]: a for a in self.r["en"]["albums"][:2]}
        self.assertEqual(own["album-panel-77-2027-2028"]["alias"], "photos")
        self.assertEqual(own["album-fall-assembly-2026"]["alias"], "fall-assembly-2026")
        self.assertEqual(own["album-panel-77-2027-2028"]["title"], "Panel 77 (2027–2028) — photos")
        self.assertTrue(all(a["covers"] is None for a in own.values()))
        # a cover marked gone is not shown; nothing is lost or counted twice
        self.assertEqual(sum(a["count"] for a in self.r["en"]["albums"]), len(self.items) - 1)

    def test_cover_albums_are_named_by_rule_in_both_languages(self):
        for lang, want in (("en", ["Grapevine covers 2026", "La Viña covers 2026", "Grapevine covers"]),
                           ("es", ["Portadas de Grapevine 2026", "Portadas de La Viña 2026", "Portadas de Grapevine"])):
            by = {a["slug"]: a for a in self.r[lang]["albums"]}
            self.assertEqual([by["covers-gv-2026"]["title"], by["covers-lv-2026"]["title"], by["covers-gv-undated"]["title"]], want)
            self.assertEqual(by["covers-lv-2026"]["covers"]["heading"], "La Viña · 2026")
            self.assertEqual(by["covers-gv-2026"]["covers"]["pub"], "gv")
        self.assertEqual(self.r["en"]["albums"][2]["covers"],
                         {"pub": "gv", "year": 2026, "id": "covers-gv-2026", "name": "Grapevine", "heading": "Grapevine · 2026", "first": True,
                          "early": False})

    def test_covers_run_newest_issue_first_named_as_read_names_issues(self):
        en = {a["slug"]: a for a in self.r["en"]["albums"]}
        es = {a["slug"]: a for a in self.r["es"]["albums"]}
        self.assertEqual([p["label"] for p in en["covers-gv-2026"]["items"]], ["November 2026", "October 2026", "January 2026"])
        self.assertEqual([p["label"] for p in es["covers-gv-2026"]["items"]], ["Noviembre 2026", "Octubre 2026", "Enero 2026"])
        self.assertEqual([p["label"] for p in en["covers-lv-2026"]["items"]], ["November–December 2026", "January–February 2026"])
        self.assertEqual([p["label"] for p in es["covers-lv-2026"]["items"]], ["Noviembre–Diciembre 2026", "Enero–Febrero 2026"])
        self.assertEqual(es["covers-lv-2016"]["items"][0]["label"], "Mayo–Junio 2016")
        # alt text and the lightbox: the issue, the year, the publisher's credit
        g, l = en["covers-gv-2026"]["items"][0], es["covers-lv-2026"]["items"][0]
        self.assertEqual((g["alt"], g["lbTitle"], g["lbDesc"]),
                         ("Grapevine cover, November 2026", "Grapevine — November 2026", "Grapevine · 2026 · © The AA Grapevine, Inc."))
        self.assertEqual((l["alt"], l["lbTitle"], l["lbDesc"]),
                         ("Portada de La Viña, Noviembre–Diciembre 2026", "La Viña — Noviembre–Diciembre 2026",
                          "La Viña · 2026 · © The AA Grapevine, Inc."))
        # a file whose name gives no issue: its own title; one without a year: no year in its lines
        self.assertEqual(en["covers-gv-2024"]["items"][0]["label"], "GV special edition 2024")
        self.assertEqual(en["covers-gv-undated"]["items"][0]["lbDesc"], "Grapevine · © The AA Grapevine, Inc.")
        # the helper itself (read.js issueName; Grapevine without Intl's Spanish "de")
        self.assertEqual(self.r["labels"], [["November 2026", "November–December 2026", "January–February 2027", ""],
                                            ["Noviembre 2026", "Noviembre–Diciembre 2026", "Enero–Febrero 2027", ""]])

    def test_a_cover_block_keeps_the_generic_anchors(self):
        from scripts.sync import build_data as B
        by = {a["slug"]: a for a in self.r["en"]["albums"]}
        # albumAnchors' slug (photoAlbumSlugs: the ids the digest links to) and What's New's alias (build_data.album_slug)
        self.assertEqual(by["covers-gv-2026"]["anchors"], ["album-grapevine-covers-2026", "grapevine-covers-2026"])
        self.assertEqual(self.r["slugs"]["f:Grapevine covers 2026"], "album-grapevine-covers-2026")
        self.assertEqual(B.album_slug("Grapevine covers 2026"), "grapevine-covers-2026")
        self.assertEqual(B.album_slug("La Viña covers 2026"), by["covers-lv-2026"]["anchors"][1])
        # every id of the page once
        ids = [i for a in self.r["en"]["albums"] for i in [a["slug"], a["alias"], *(a["anchors"] or [])] if i]
        ids += ["covers", "covers-gv", "covers-lv"]
        self.assertEqual(len(ids), len(set(ids)), ids)

    def test_a_cover_without_its_album_takes_no_other_albums_anchor(self):
        # (the pipeline always files a cover in "… covers <year>"; without it the cover would share the panel album's
        # key — its block must not repeat that album's ids, "#photos" among them)
        items = sample()[:2] + [cover("lv", 2017, 2)]
        items[-1]["extra"]["album"] = None
        del items[-1]["i18n"]["album"]
        r = run_js(self, "out(filters.cmAlbums(input.items, 'en').map((a) => [a.slug, a.alias, a.anchors, a.title]))", data={"items": items})
        self.assertEqual(r, [["album-panel-77-2027-2028", "photos", [], "Panel 77 (2027–2028) — photos"],
                             ["covers-lv-2017", "", [], "La Viña covers 2017"]])

    def test_the_shelf(self):
        s = self.r["en"]["shelf"]
        self.assertEqual(s["total"], 10)
        gv, lv = s["mags"]
        self.assertEqual((gv["pub"], gv["id"], gv["title"], gv["count"], gv["range"], gv["hasNew"]),
                         ("gv", "covers-gv", "Grapevine covers", 7, "2015–2026", True))
        self.assertEqual((lv["count"], lv["range"], lv["hasNew"]), (2 + 1, "2016–2026", False))
        # the 3 newest covers of the collection
        by = {a["slug"]: a for a in self.r["en"]["albums"]}
        self.assertEqual(gv["cover"], [p["id"] for p in by["covers-gv-2026"]["items"]])
        self.assertEqual(s["years"][0], {"year": 2026, "count": 5, "gv": 3, "lv": 2})
        self.assertEqual([y["year"] for y in s["years"]], [2026, 2025, 2024, 2016, 2015])
        self.assertEqual(s["firsts"], ["covers-gv-2026", "covers-lv-2026"])
        self.assertEqual(self.r["es"]["shelf"]["mags"][1]["title"], "Portadas de La Viña")
        # with no filter on the page shows the 2 newest years (2026, 2025) at first: the others — and the covers
        # without a year, last — are folded away behind "Show earlier years (2015–2024)"
        self.assertEqual(s["early"], ["covers-gv-2024", "covers-lv-2016", "covers-gv-2015", "covers-gv-undated"])
        self.assertEqual(s["earlier"], {"from": 2015, "to": 2024, "n": 4})

    def test_the_folded_years_need_earlier_ones(self):
        # two years only: nothing to fold (a cover without a year shows with them)
        items = [cover("gv", 2026, 11), cover("lv", 2025, 6), cover("gv", None, None, name="GV poster")]
        r = run_js(self, "const s = filters.cmCovers(filters.cmAlbums(input.items, 'en'), 'en');"
                         "out([s.earlier, s.albums.map((a) => [a.slug, a.covers.early])])", data={"items": items})
        self.assertEqual(r, [None, [["covers-gv-2026", False], ["covers-lv-2025", False], ["covers-gv-undated", False]]])
        # one earlier year
        r = run_js(self, "out(filters.cmCovers(filters.cmAlbums(input.items, 'en'), 'en').earlier)",
                   data={"items": items[:2] + [cover("gv", 2019, 3)]})
        self.assertEqual(r, {"from": 2019, "to": 2019, "n": 1})

    def test_smaller_pictures_for_the_small_tiles(self):
        # the collection cards' mosaics at =w300, the grid's tiles at =w400, the lightbox at =w1600 (the same picture)
        for t in self.r["en"]["shelf"]["mags"][0]["coverThumbs"]:
            self.assertRegex(t, r"^https://lh3\.googleusercontent\.com/d/\w+=w300$")
        for tile, thumb, full in self.r["en"]["tiles"]:
            self.assertEqual(tile, thumb.replace("=w600", "=w400"))
            self.assertTrue(full.endswith("=w1600"), full)
        # driveImageWidth: only an address that ends with a width ("=w600") changes
        self.assertEqual(self.r["widths"], ["https://lh3.googleusercontent.com/d/abc=w300", "https://lh3.googleusercontent.com/d/abc=w400",
                                            "https://lh3.googleusercontent.com/d/abc", "https://drive.google.com/thumbnail?id=abc&sz=w300",
                                            "https://example.org/covers/gv-2026-11.jpg",
                                            "", "", "https://lh3.googleusercontent.com/d/abc=w600"])


class Search(unittest.TestCase):
    def test_one_entry_per_cover_album_found_by_its_issues(self):
        r = run_js(self, SEARCH_JS, data={"items": sample()})
        for lang, pre in (("en", ""), ("es", "/es")):
            covers = [e for e in r[lang] if e["id"].startswith("covers:")]
            self.assertEqual(len(covers), 7, [e["id"] for e in covers])
            self.assertFalse([e for e in r[lang] if e["k"] == "photo"], "never one entry per cover")
            e = next(e for e in covers if e["id"] == "covers:covers-lv-2026")
            self.assertEqual(e["u"], pre + "/photos/?mag=lv&year=2026#covers-lv-2026")
            self.assertEqual(e["t"], "La Viña covers 2026" if lang == "en" else "Portadas de La Viña 2026")
            self.assertEqual(e["s"], "2 covers" if lang == "en" else "2 portadas")
            self.assertEqual(e["src"], "lv")
            for word in ("November–December 2026", "Noviembre–Diciembre 2026", "Enero–Febrero 2026", "portada", "cover"):
                self.assertIn(word, e["x"])
            g = next(e for e in covers if e["id"] == "covers:covers-gv-2026")
            self.assertEqual(g.get("n"), 1, "a new issue in it")
            self.assertIn("Noviembre 2026", g["x"])
            self.assertEqual(next(e for e in covers if e["id"] == "covers:covers-gv-undated")["u"], pre + "/photos/?mag=gv#covers-gv-undated")
            # the committee's own albums as before
            own = [e for e in r[lang] if e["id"].startswith("album:")]
            self.assertEqual([e["u"] for e in own], [pre + "/photos/#album-panel-77-2027-2028", pre + "/photos/#album-fall-assembly-2026"])


# --------------------------------------------------------------------------- the filter in the browser
FILTER_JS = r"""
const chip = (attr, v, n) => el("button", { [attr]: v }, [el("span", { class: "cm-chip-count" }, [], String(n))]);
const scrolled = [];
El.prototype.scrollIntoView = function () { scrolled.push(this.attrs.id); };
function setup(search, startHash) {
  const mags = [chip("data-cm-mag", "", 36), chip("data-cm-mag", "gv", 24), chip("data-cm-mag", "lv", 12)];
  const years = ["", "2026", "2025", "2015"].map((y) => chip("data-cm-year", y, 0));
  // (the 2 newest years show at first; 2015 is folded away: data-cm-early, photos.njk)
  const block = (pub, year, n, kids) => el("section", { id: `covers-${pub}-${year}`, "data-cm-cover": "", "data-mag": pub,
    "data-year": String(year), "data-count": String(n), ...(year < 2025 ? { "data-cm-early": "" } : {}) }, kids || []);
  const blocks = [
    block("gv", 2026, 11, [el("span", { id: "covers-gv" }), el("span", { id: "album-grapevine-covers-2026" })]),
    block("lv", 2026, 6, [el("span", { id: "covers-lv" })]),
    block("gv", 2025, 12),
    block("lv", 2025, 6),
    block("gv", 2015, 1, [el("span", { id: "grapevine-covers-2015" }), el("a", { class: "cm-photo", id: "gv2015-first" })]),
  ];
  // the filter bar (its id only for this log of what was scrolled to)
  const bar = el("div", { class: "cm-covers-filter", id: "filter-bar" }, [el("div", {}, mags), el("div", {}, years)]);
  const root = el("section", { id: "covers", "data-count-label": "Showing {n} covers", "data-count-label-one": "Showing 1 cover" },
                  [bar, ...blocks]);
  const p = page([el("section", { id: "album-panel-77" }), root], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true });
  const urls = [];
  const L = p.win.location;
  L.pathname = "/photos/"; L.search = search || ""; L.hash = startHash || "";
  p.win.history.replaceState = (s, t, u) => {
    urls.push(u);
    const m = /^([^?#]*)(\?[^#]*)?(#.*)?$/.exec(u);
    L.pathname = m[1]; L.search = m[2] || ""; L.hash = m[3] || "";
  };
  p.ready();
  const c = p.comps.cmCovers();
  c.$root = root; c.$nextTick = (fn) => fn();
  scrolled.length = 0;
  const focused = [];
  El.prototype.focus = function () { focused.push(this.attrs.id); };
  c.init();
  const snap = () => ({
    mag: c.mag, year: c.year, url: L.pathname + L.search + L.hash, text: c.countText(), n: c.visibleCount, filtered: c.filtered,
    folded: c.folded, all: c.all, focused: [...focused],
    years: years.map((b) => [b.getAttribute("data-cm-year"), b.querySelector(".cm-chip-count").textContent, b.hidden]),
    shown: blocks.filter((b) => c.shows(b)).map((b) => b.attrs.id), scrolled: [...scrolled],
  });
  const hash = (h) => { L.hash = h; scrolled.length = 0; p.fireWin("hashchange"); return snap(); };
  return { c, snap, hash, urls, bar, win: p.win, ready: p.doc.documentElement.classList.contains("cm-covers-ready") };
}
const res = {};
// opened with no filter: the 2 newest years; "Show earlier years"; a filter shows every block it matches, and
// clearing it keeps what the visitor asked for
{
  const { c, snap, ready } = setup("", "");
  res.plain = snap();
  res.plainReady = ready;
  c.setMag("gv"); res.plainGv = snap();
  c.clear(); res.plainCleared = snap();
  c.showEarlier(); res.earlier = snap();
  c.setYear("2015"); c.clear(); res.earlierCleared = snap();
}
// a generic link to a block that is folded away: shown (and landed on)
{
  const { snap } = setup("", "#grapevine-covers-2015");
  res.foldedLink = snap();
}
// opened with the filter in the address (a search result): La Viña 2025
{
  const { c, snap, hash, urls } = setup("?mag=lv&year=2025", "");
  res.opened = snap();
  res.openedUrls = [...urls];
  c.setMag("gv");                       // Grapevine has 2025 too: kept
  res.gv = snap();
  c.setYear("2015"); res.gv2015 = snap();
  c.setMag("lv");                       // La Viña has no 2015: back to All years
  res.lv = snap();
  c.setMag("xx"); res.unknownMag = snap();
  c.setYear("1999"); res.unknownYear = snap();
  c.setYear("2026"); c.setYear(""); res.yearOff = snap();
  c.setMag("gv"); c.setYear("2026"); c.clear();
  res.cleared = snap();
  // links into the covers
  res.hashBlock = hash("#covers-gv-2015");
  c.setMag("lv");
  res.afterChip = snap();
  res.hashGeneric = hash("#grapevine-covers-2015");      // hidden by "La Viña": the filter is reset
  res.hashMag = hash("#covers-lv");
  res.hashOther = hash("#album-panel-77");               // not a covers link: nothing changes
  res.hashSection = hash("#covers");                     // (a filter is on: the filter)
  c.clear();
  res.hashSectionPlain = hash("#covers");                // (none: the section)
}
// a search result: the filter and a block of it in the address
{
  const { snap } = setup("?mag=gv&year=2015", "#covers-gv-2015");
  res.searchResult = snap();
}
// a link to a magazine, with values the page has no covers for
{
  const { snap } = setup("?mag=xx&year=1999", "#covers-gv");
  res.fresh = snap();
}
// a generic link to a block the address's filter would hide
{
  const { snap } = setup("?mag=lv", "#album-grapevine-covers-2026");
  res.generic = snap();
}
// a phone at large text: the filter is taller than half the screen, so a link that sets the filter lands on its
// block (the covers it was for), not on the filter; #covers itself while a filter is on still lands on the filter
{
  const { hash, bar, win } = setup("", "");
  bar.getBoundingClientRect = () => ({ top: 0, bottom: 900, left: 0, right: 360, width: 360, height: 900 });
  win.innerHeight = 800;
  res.tallBlock = hash("#covers-gv-2015");
  res.tallSection = hash("#covers");
}
// a block's ↑ when the address already ends in #covers (a second ↑: no hashchange): up() brings the filter into
// view; the first ↑ (another hash) is left to the link and its hashchange
{
  const { c, snap } = setup("?mag=lv", "#covers");
  scrolled.length = 0;
  let prevented = false;
  c.up({ preventDefault() { prevented = true; } });
  res.upAgain = { ...snap(), prevented };
}
{
  const { c, snap } = setup("?mag=lv", "");
  scrolled.length = 0;
  let prevented = false;
  c.up({ preventDefault() { prevented = true; } });
  res.upFirst = { ...snap(), prevented };
}
out(res);
"""


class Filter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Filter.r is None:
            Filter.r = run_js(self, TCT.DOM + FILTER_JS, needs_modules=True, timeout=120)
        self.r = Filter.r

    def test_at_first_the_two_newest_years_then_the_rest_when_asked(self):
        p = self.r["plain"]
        self.assertEqual((p["mag"], p["year"], p["folded"], p["filtered"], p["text"]), ("", "", True, False, ""))
        self.assertEqual(p["shown"], ["covers-gv-2026", "covers-lv-2026", "covers-gv-2025", "covers-lv-2025"])
        self.assertEqual(p["n"], 35, "the covers on screen")
        self.assertTrue(self.r["plainReady"], "x-show owns the folded blocks now (committee.css .cm-covers-ready)")
        # a filter shows every block it matches; clearing it folds the earlier years away again
        self.assertEqual(self.r["plainGv"]["shown"], ["covers-gv-2026", "covers-gv-2025", "covers-gv-2015"])
        self.assertFalse(self.r["plainGv"]["folded"])
        self.assertEqual((self.r["plainCleared"]["shown"], self.r["plainCleared"]["text"]),
                         (p["shown"], "Showing 35 covers"))
        # "Show earlier years": all of them, the keyboard on the first cover that was folded away, the address unchanged
        e = self.r["earlier"]
        self.assertEqual((e["folded"], e["all"], e["n"], e["text"], e["url"]), (False, True, 36, "Showing 36 covers", "/photos/"))
        self.assertEqual(e["shown"], ["covers-gv-2026", "covers-lv-2026", "covers-gv-2025", "covers-lv-2025", "covers-gv-2015"])
        self.assertEqual(e["focused"][-1], "gv2015-first")
        # …and after that, clearing a filter keeps them all
        self.assertEqual(len(self.r["earlierCleared"]["shown"]), 5)
        self.assertFalse(self.r["earlierCleared"]["folded"])
        # a generic link to a folded block shows them and lands on it
        f = self.r["foldedLink"]
        self.assertEqual((f["mag"], f["all"], f["scrolled"]), ("", True, ["grapevine-covers-2015"]))
        self.assertIn("covers-gv-2015", f["shown"])

    def test_the_address_sets_it_and_the_years_follow_the_magazine(self):
        o = self.r["opened"]
        self.assertEqual((o["mag"], o["year"], o["n"], o["shown"]), ("lv", "2025", 6, ["covers-lv-2025"]))
        self.assertEqual(o["years"], [["", "12", False], ["2026", "6", False], ["2025", "6", False], ["2015", "0", True]])
        self.assertEqual(self.r["openedUrls"], [], "the address already said it")
        self.assertEqual(o["text"], "", "the live count speaks only after a change")
        g = self.r["gv"]
        self.assertEqual((g["mag"], g["year"], g["url"], g["text"]), ("gv", "2025", "/photos/?mag=gv&year=2025", "Showing 12 covers"))
        self.assertEqual(g["years"], [["", "24", False], ["2026", "11", False], ["2025", "12", False], ["2015", "1", False]])
        self.assertEqual(self.r["gv2015"]["text"], "Showing 1 cover")

    def test_a_magazine_without_the_year_falls_back_to_all_years(self):
        lv = self.r["lv"]
        self.assertEqual((lv["mag"], lv["year"], lv["url"], lv["n"]), ("lv", "", "/photos/?mag=lv", 12))
        self.assertEqual(lv["shown"], ["covers-lv-2026", "covers-lv-2025"])
        self.assertTrue(lv["years"][3][2], "2015 hides for La Viña")
        self.assertEqual(self.r["unknownMag"]["mag"], "")
        self.assertEqual(self.r["unknownMag"]["url"], "/photos/")
        self.assertEqual((self.r["unknownYear"]["year"], self.r["unknownYear"]["url"]), ("", "/photos/"))
        self.assertEqual((self.r["yearOff"]["year"], self.r["yearOff"]["url"]), ("", "/photos/"))
        cl = self.r["cleared"]
        self.assertEqual((cl["mag"], cl["year"], cl["url"], cl["filtered"], cl["n"], cl["folded"]), ("", "", "/photos/", False, 35, True))
        self.assertEqual(cl["text"], "Showing 35 covers")

    def test_links_into_the_covers_set_the_filter_and_land(self):
        # a link that sets the filter lands on the filter (its pressed chips and "Clear filters"), the block under it
        h = self.r["hashBlock"]
        self.assertEqual((h["mag"], h["year"], h["shown"], h["scrolled"]), ("gv", "2015", ["covers-gv-2015"], ["filter-bar"]))
        # (a chip was used before: the address keeps the filter and "#covers", not the block's own link)
        self.assertEqual(h["url"], "/photos/?mag=gv&year=2015#covers")
        self.assertEqual(self.r["afterChip"]["url"], "/photos/?mag=lv#covers")
        g = self.r["hashGeneric"]
        self.assertEqual((g["mag"], g["year"], g["scrolled"]), ("", "", ["grapevine-covers-2015"]))
        self.assertIn("covers-gv-2015", g["shown"])
        m = self.r["hashMag"]
        self.assertEqual((m["mag"], m["year"], m["scrolled"]), ("lv", "", ["filter-bar"]))
        o = self.r["hashOther"]
        self.assertEqual((o["mag"], o["scrolled"]), ("lv", []), "a link elsewhere on the page changes nothing")
        # #covers (a block's ↑): the filter while one is on, else the section; the filter is kept
        self.assertEqual((self.r["hashSection"]["scrolled"], self.r["hashSection"]["mag"]), (["filter-bar"], "lv"))
        self.assertEqual(self.r["hashSectionPlain"]["scrolled"], ["covers"])
        # opened with a link to a magazine: unknown values left out, the link kept (nothing was touched yet)
        f = self.r["fresh"]
        self.assertEqual((f["mag"], f["year"], f["url"], f["scrolled"], f["text"]),
                         ("gv", "", "/photos/?mag=gv#covers-gv", ["filter-bar"], ""))
        # a search result (/photos/?mag=gv&year=2015#covers-gv-2015): the filter in view, that block alone under it
        sr = self.r["searchResult"]
        self.assertEqual((sr["mag"], sr["year"], sr["shown"], sr["scrolled"], sr["url"]),
                         ("gv", "2015", ["covers-gv-2015"], ["filter-bar"], "/photos/?mag=gv&year=2015#covers-gv-2015"))
        # a generic link to a block the address's filter would hide: the filter is reset
        gen = self.r["generic"]
        self.assertEqual((gen["mag"], gen["url"], gen["scrolled"]), ("", "/photos/#album-grapevine-covers-2026", ["album-grapevine-covers-2026"]))

    def test_a_filter_taller_than_half_the_screen_lands_on_the_block(self):
        t = self.r["tallBlock"]
        self.assertEqual((t["mag"], t["year"], t["shown"], t["scrolled"]), ("gv", "2015", ["covers-gv-2015"], ["covers-gv-2015"]))
        self.assertEqual(self.r["tallSection"]["scrolled"], ["filter-bar"], "#covers with a filter on: still the filter")

    def test_a_second_up_arrow_still_brings_the_filter_into_view(self):
        a = self.r["upAgain"]
        self.assertEqual((a["prevented"], a["scrolled"], a["mag"]), (True, ["filter-bar"], "lv"))
        f = self.r["upFirst"]
        self.assertEqual((f["prevented"], f["scrolled"]), (False, []), "the link and its hashchange do it")


# --------------------------------------------------------------------------- the page
PAGE_JS = r"""
process.env.ONLY = "photos.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const res = {};
for (const [name, items] of [["covers", input.items], ["none", input.items.filter((it) => !(it.extra && it.extra.cover))], ["one", input.one]]) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r29-photos-"));
  try {
    const elev = new Eleventy("src", dir, {
      quietMode: true, configPath: "eleventy.config.js",
      config(cfg) {
        cfg.addGlobalData("eleventyComputed", { db: (data) => ({ ...data.db, drive: { updated: "2026-11-13T12:00:00Z", items } }) });
      },
    });
    for (const p of await elev.toJSON()) if (/\/photos\/$/.test(p.url)) res[name + (p.url.startsWith("/es/") ? "-es" : "-en")] = p.content;
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
out(res);
"""


def text(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Page.r is None:
            Page.r = run_js(self, PAGE_JS, data={"items": sample(), "one": [sample()[2], cover("gv", 2026, 11)]}, timeout=360)
        self.r = Page.r

    def test_the_hero_says_whose_the_covers_are_always(self):
        # the footer's own subject ("Grapevine and La Viña material, including …": never the committee's photos)
        credit = {"en": "Grapevine and La Viña material, including magazine covers and other graphics: Copyright © The AA "
                        "Grapevine, Inc. Reprinted with permission. All rights reserved. A.A.W.S. graphics are used with "
                        "permission of A.A. World Services, Inc.",
                  "es": "Material de Grapevine y La Viña, incluidas las portadas de revistas y otras imágenes: Copyright © The AA "
                        "Grapevine, Inc. Reimpreso con permiso. Todos los derechos reservados. Las imágenes de A.A.W.S. se usan "
                        "con permiso de A.A. World Services, Inc."}
        for name in ("covers", "none"):
            for lang in ("en", "es"):
                h = self.r[f"{name}-{lang}"]
                hero = h[h.index('class="gv-hero '):h.index("</section>", h.index('class="gv-hero '))]
                m = re.search(r'<p class="cm-hero-credit">(.*?)</p>', hero)
                self.assertTrue(m, f"{name}-{lang}: no credit line in the hero")
                self.assertEqual(text(m.group(1)), credit[lang])
                # under the numbers
                if "hero-stats" in hero:
                    self.assertLess(hero.index("hero-stats"), hero.index("cm-hero-credit"))

    def test_the_hero_numbers_keep_the_covers_apart(self):
        stats = lambda h: [(text(a), text(b)) for a, b in re.findall(r'<div class="hero-stat"><dt>(.*?)</dt><dd>(.*?)</dd>', h)]
        self.assertEqual(stats(self.r["covers-en"]), [("albums", "2"), ("photos", "4"), ("magazine covers", "10")])
        self.assertEqual(stats(self.r["covers-es"]), [("álbumes", "2"), ("fotos", "4"), ("portadas de las revistas", "10")])
        self.assertEqual(stats(self.r["none-en"]), [("albums", "2"), ("photos", "4")])
        # one album, one photo: the words for one
        self.assertEqual(stats(self.r["one-en"]), [("album", "1"), ("photo", "1"), ("magazine cover", "1")])
        self.assertEqual(stats(self.r["one-es"]), [("álbum", "1"), ("foto", "1"), ("portada de las revistas", "1")])
        # the sub-nav counts everything the page shows
        self.assertRegex(self.r["covers-en"], r'cm-subnav-link is-current"[^>]*>.*?<span class="cm-subnav-count">14</span>')

    def test_the_covers_section(self):
        for lang in ("en", "es"):
            h = self.r[f"covers-{lang}"]
            ids = re.findall(r'\bid="([^"]+)"', h)
            self.assertEqual(sorted({i for i in ids if ids.count(i) > 1}), [], "an id twice")
            self.assertIn('id="covers"', h)
            # the committee's albums, "Protecting anonymity", the covers, the member help (last)
            order = [h.index(x) for x in ('id="album-fall-assembly-2026"', 'aria-labelledby="anon-h"', '<section id="covers"', 'id="share-photos"')]
            self.assertEqual(order, sorted(order))
            sec = h[h.index('<section id="covers"'):]
            sec = sec[:sec.index('id="share-photos"')]
            # the filter: JavaScript only, both rows, the live count
            self.assertRegex(sec, r'<div class="cm-covers-filter" data-js-only>')
            self.assertEqual(re.findall(r'data-cm-mag="(\w*)"', sec), ["", "gv", "lv"])
            self.assertEqual(re.findall(r'data-cm-year="(\d*)"', sec), ["", "2026", "2025", "2024", "2016", "2015"])
            self.assertIn('aria-live="polite"', sec)
            # the blocks and their anchors; the album index's collection cards link to the magazines
            self.assertEqual(re.findall(r'<section id="(covers-[^"]+)" class="cm-cover-album"', sec),
                             ["covers-gv-2026", "covers-lv-2026", "covers-gv-2025", "covers-gv-2024", "covers-lv-2016", "covers-gv-2015", "covers-gv-undated"])
            for a in ("covers-gv", "covers-lv", "album-grapevine-covers-2026", "grapevine-covers-2026", "la-vina-covers-2016"):
                self.assertIn(f'<span id="{a}" class="cm-anchor"', sec)
            self.assertIn('href="#covers-gv" class="card', h)
            self.assertIn('href="#covers-lv" class="card', h)
            # tiles: portrait, lazy, the issue under each, the lightbox's lines escaped (cmLbText)
            tiles = re.findall(r'<a href="([^"]+)" class="cm-photo cm-cover glightbox-cm" data-gallery="(covers-gv-2026)"', sec)
            self.assertEqual(len(tiles), 3)
            self.assertIn('width="600" height="857" referrerpolicy="no-referrer"', sec)
            caps = re.findall(r'<p class="cm-cover-cap" aria-hidden="true">(.*?)</p>', sec)
            self.assertEqual(caps[:3], ["November 2026", "October 2026", "January 2026"] if lang == "en"
                             else ["Noviembre 2026", "Octubre 2026", "Enero 2026"])
            desc = re.search(r'data-gallery="covers-lv-2026" data-type="image" data-title="([^"]*)" data-description="([^"]*)"', sec)
            self.assertEqual(html.unescape(html.unescape(desc.group(2))), "La Viña · 2026 · © The AA Grapevine, Inc.")
            self.assertNotIn("cm-photo-feature", sec)
            self.assertNotIn("cm-more", sec)
            # the pictures: 400 px in the grid, 300 px in the collection cards' mosaics (the same shape: 600 × 857)
            self.assertEqual({re.sub(r".*=", "=", u) for u in re.findall(r'<img src="([^"]+)" alt="[^"]+" loading="lazy"', sec)}, {"=w400"})
            mosaic = re.findall(r'<img src="([^"]+)" alt="" loading="lazy" decoding="async" width="600" height="857"', h)
            self.assertTrue(mosaic and all(u.endswith("=w300") for u in mosaic), mosaic)
            # a block's head: Full screen and Share only with JavaScript; ↑ back to the filter
            back = "Back to the covers filter" if lang == "en" else "Volver al filtro de portadas"
            self.assertEqual(len(re.findall(r'<a class="btn-ghost btn-sm" href="#covers" @click="up\(\$event\)" aria-label="' + back + '">', sec)), 7)
            self.assertEqual(len(re.findall(r'data-cm-open-gallery="covers-[^"]+" data-js-only>', sec)), 7)
            self.assertEqual(len(re.findall(r'data-share="[^"]+#covers-[^"]+" data-share-title="[^"]+" data-js-only>', sec)), 7)
            # …and an event album's too
            self.assertRegex(h, r'data-cm-open-gallery="album-fall-assembly-2026" data-js-only>')
            self.assertRegex(h, r'data-share="[^"]+#album-fall-assembly-2026" data-share-title="[^"]+" data-js-only>')
            # the sub's "Filter by magazine and year." only where the filter is
            sub = ("Grapevine and La Viña front covers, newest first. <span data-js-only>Filter by magazine and year.</span>"
                   if lang == "en" else
                   "Las portadas de Grapevine y La Viña, de la más reciente a la más antigua. <span data-js-only>Filtra por revista y año.</span>")
            self.assertIn(sub, html.unescape(sec))
            # the earlier years folded away at first (with JavaScript): their blocks, and the one button
            self.assertEqual(re.findall(r'<section id="(covers-[^"]+)" class="cm-cover-album"[^>]* data-cm-early ', sec),
                             ["covers-gv-2024", "covers-lv-2016", "covers-gv-2015", "covers-gv-undated"])
            more = re.search(r'<div class="cm-covers-more[^"]*" data-js-only x-show="folded">\s*<button type="button" class="btn-secondary" @click="showEarlier\(\)">(.*?)</button>', sec, re.S)
            self.assertTrue(more, "the Show earlier years button")
            self.assertEqual(text(more.group(1)), "Show earlier years (2015–2024)" if lang == "en" else "Ver años anteriores (2015–2024)")
            self.assertIn('class="cm-covers-row cm-covers-years"', sec)
        # the member help names the covers' folders and files
        self.assertIn("LaVina_2027-01_Enero-Febrero.jpg", self.r["covers-en"])
        self.assertIn("AAGrapevine_covers", self.r["covers-es"])

    def test_the_description_names_the_covers_only_when_there_are_some(self):
        desc = lambda h: html.unescape(re.search(r'<meta name="description" content="([^"]*)"', h).group(1))
        self.assertEqual(desc(self.r["covers-en"]), "Photos from NETA 65 Grapevine / La Viña booths, workshops and service events, "
                         "with anonymity respected, plus the Grapevine and La Viña magazine covers by year.")
        self.assertIn("respetando el anonimato, y las portadas de Grapevine y La Viña por año.", desc(self.r["covers-es"]))
        self.assertEqual(desc(self.r["none-en"]), "Photos from NETA 65 Grapevine / La Viña booths, workshops and service events — "
                         "shared from the committee's Google Drive, with anonymity respected.")

    def test_without_covers_no_covers_section(self):
        for lang in ("en", "es"):
            h = self.r[f"none-{lang}"]
            self.assertNotIn('id="covers"', h)
            self.assertNotIn("cm-cover-album", h)
            self.assertIn('id="album-fall-assembly-2026"', h)
            order = [h.index(x) for x in ('id="album-fall-assembly-2026"', 'aria-labelledby="anon-h"', 'id="share-photos"')]
            self.assertEqual(order, sorted(order))
        self.assertIn("Booths, literature tables, workshops and service in action — always protecting anonymity.", self.r["none-en"])


# --------------------------------------------------------------------------- What's New and the feed
WN_JS = r"""
process.env.ONLY = "whats-new.njk,feed.11ty.js";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const res = {};
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r29-wn-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", { db: (data) => ({ ...data.db, whatsnew: { updated: "2026-11-13T12:00:00Z", items: input.items } }) });
    },
  });
  for (const p of await elev.toJSON()) if (/(whats-new\/|feed\.xml)$/.test(p.url)) res[p.url] = p.content;
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
out(res);
"""


class WhatsNew(unittest.TestCase):
    """The covers' entries (build_data.cover_news: written in both languages by rule) never say "Originally in
    Spanish" / "Original en inglés" — an entry translated by machine still does —, and the RSS feed files them under
    "Magazine covers" / "Portadas de las revistas" (not "Committee uploads": they are the magazines' work)."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if WhatsNew.r is None:
            from scripts.sync import build_data as B
            gv = B.cover_news("gv", "2026-11-13", [cover("gv", 2026, 11), cover("gv", 2026, 10)])
            lv = B.cover_news("lv", "2026-11-13", [cover("lv", 2026, 6), cover("lv", 2026, 1)])
            ctl = photo("ctl1", "2026-11-12", "Fall Assembly 2026", "Mesa de literatura")
            ctl.update(lang="es", machine=["en"], i18n={"title": {"en": "Literature table", "es": "Mesa de literatura"}})
            items = []
            for i, it in enumerate((gv, lv, ctl)):
                items.append({**it, "wn_date": f"2026-11-13T1{i}:00:00Z"})
            WhatsNew.r = run_js(self, WN_JS, data={"items": items}, timeout=360)
        self.r = WhatsNew.r

    @staticmethod
    def entry(h: str, title: str) -> str:
        i = h.index(title)
        return h[h.rindex("<li", 0, i):h.index("</li>", i)]

    def test_no_language_pill_on_the_covers_entries(self):
        en, es = self.r["/whats-new/"], self.r["/es/whats-new/"]
        self.assertNotIn("badge-muted uppercase", self.entry(en, "2 La Viña covers added"))
        self.assertNotIn("badge-muted uppercase", self.entry(es, "Se agregaron 2 portadas de Grapevine"))
        self.assertIn("Magazine covers", self.entry(en, "2 La Viña covers added"))
        # a machine-translated entry still says its language
        self.assertIn("badge-muted uppercase", self.entry(en, "Literature table"))

    def test_the_feed_files_them_under_magazine_covers(self):
        for url, kind, title in (("/feed.xml", "Magazine covers", "2 Grapevine covers added"),
                                 ("/es/feed.xml", "Portadas de las revistas", "Se agregaron 2 portadas de La Viña")):
            feed = self.r[url]
            item = feed[feed.rindex("<item>", 0, feed.index(title)):feed.index("</item>", feed.index(title))]
            self.assertIn(f"<category>{kind}</category>", item)
            self.assertNotIn("Committee uploads", item)
            self.assertNotIn("Archivos del comité", item)


if __name__ == "__main__":
    unittest.main()
