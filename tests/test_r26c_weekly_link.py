"""Round 26c — the weekly open meetings' full Zoom link and their flyers (November 12, 2026):

  * the join link — each weekly open meeting's Join on Zoom opens its FULL link (with its "?pwd=…": nobody types the
                    passcode), from config/site.yml `grapevine_weekly_open.zoom_url` / `lavina_weekly_open.zoom_url`
                    (scripts/sync/weekly_open.py join_link): used, exactly as written, only when it is a Zoom join link
                    (https://<server>.zoom.us/j/<ID>[?pwd=…]) whose meeting number is the meeting's own Zoom ID —
                    Grapevine's as aagrapevine.org gives it that day (or kept from the day before), La Viña's
                    `zoom_id`; otherwise the plain https://zoom.us/j/<ID> and a note on /status/ (stats.warnings,
                    without the "?pwd=…" part). Also when aagrapevine.org cannot be read that day. A push that edits
                    `grapevine_weekly_open` runs the source again (scripts/ops/push_modules.py);
  * the pages     — /meetings/#weekly-open, English and Spanish: both cards' Join is the full link; their Add to
                    calendar carries it — Google's link (encoded) and the .ics files (escaped, folded at 75 octets) —
                    as do the /events/ cards' calendar links (How to join there still leads to /meetings/); the
                    Grapevine card links AA Grapevine's flyer on the Drive (grapevine_weekly_open.flyer_match, in
                    flyers/ only), with a source line that says the flyer is AA Grapevine's, and no link when nothing
                    matches; La Viña's card links its NEWEST flyer;
  * RealSettings  — the committee's settings as written (scripts/ops/gate_tests.py CONTENT_TESTS): both full links
                    point to their meeting's Zoom room; the two flyer patterns each find their own flyer and nothing
                    else the settings name; their titles in the other language (data/translations/overrides.yml);
                    La Viña's summaries from its newest flyer, the sign-off last, word for word.

The pages are built by Eleventy with the site's own config on a fixed clock, with weekly open meetings and Drive files
of the test's own (not the day's data).

    python -m unittest tests.test_r26c_weekly_link -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.ops import push_modules as P  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import weekly_open as W  # noqa: E402

FULL = "https://us02web.zoom.us/j/87120368287?pwd=VYskKcQbHB4KtZiTk0EmDcMuJO95kV.1"
PLAIN = "https://zoom.us/j/87120368287"
ZOOM_ID = "871 2036 8287"
OTHER_ROOM = "https://us06web.zoom.us/j/81595931777?pwd=SomeOtherToken.1"
PAGE = ROOT / "tests" / "fixtures" / "weekly_open" / "gv_weekly_open.html"
GV_PAGE_URL = "https://www.aagrapevine.org/grapevine-weekly-open"
# The two flyers on the committee's Drive (flyers/, 2026-11-12), their file names without the extension
GV_FLYER = "Grapevine Weekly Open AA Meeting - every Wednesday, 11 AM Central (noon Eastern), on Zoom"
LV_FLYER = "Reunión abierta de La Viña - todos los jueves, 11 a. m. hora del Centro (mediodía del Este), por Zoom"
LV_NOVEMBER = "Nueva reunión abierta de La Viña - jueves a las 12 p. m. (hora del Este) por Zoom"   # stays until Nov 30


def i18n() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


T = i18n()


def config() -> dict:
    return yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------- the sync
class JoinLink(unittest.TestCase):
    def test_the_full_link_of_the_meetings_own_room_is_used_as_written(self):
        for link in (FULL, "https://zoom.us/j/87120368287?pwd=abc.1", "https://US02WEB.zoom.us/j/87120368287",
                     "https://zoom.us/j/87120368287", f"  {FULL}  "):
            with self.subTest(link=link):
                notes: list[str] = []
                self.assertEqual(W.join_link(link, ZOOM_ID, "grapevine_weekly_open", notes), link.strip())
                self.assertEqual(notes, [])
        # the token keeps its capitals and its ".1"
        self.assertTrue(W.join_link(FULL, "87120368287", "x").endswith("?pwd=VYskKcQbHB4KtZiTk0EmDcMuJO95kV.1"))

    def test_another_room_gives_the_plain_link_and_a_note(self):
        notes: list[str] = []
        self.assertEqual(W.join_link(OTHER_ROOM, ZOOM_ID, "lavina_weekly_open", notes), PLAIN)
        self.assertEqual(len(notes), 1)
        self.assertIn("lavina_weekly_open", notes[0])
        self.assertIn("815 9593 1777", notes[0])
        self.assertIn(ZOOM_ID, notes[0])
        self.assertNotIn("SomeOtherToken", notes[0], "the note never repeats the link's passcode part")

    def test_what_is_not_a_zoom_join_link_gives_the_plain_link_and_a_note(self):
        for link in ("http://us02web.zoom.us/j/87120368287?pwd=abc",          # not https
                     "https://us02web.zoom.us/w/87120368287?pwd=abc",          # a webinar address
                     "https://us02web.zoom.us/j/87120368287?pwd=abc&uname=Ana",  # more than the passcode
                     "https://us02web.zoom.us.example.org/j/87120368287",      # another site
                     "https://example.org/zoom.us/j/87120368287",
                     "https://meet.google.com/rva-tmst-vdb", "zoom.us/j/87120368287", "87120368287"):
            with self.subTest(link=link):
                notes: list[str] = []
                self.assertEqual(W.join_link(link, ZOOM_ID, "grapevine_weekly_open", notes), PLAIN)
                self.assertEqual(len(notes), 1)
                self.assertIn("not a Zoom join link", notes[0])
                self.assertNotIn("pwd=abc", notes[0])

    def test_nothing_set_or_no_meeting_id(self):
        for empty in (None, "", "  ", 42):
            notes: list[str] = []
            self.assertEqual(W.join_link(empty, ZOOM_ID, "x", notes), PLAIN)
            self.assertEqual(notes, [])
        notes = []
        self.assertIsNone(W.join_link(FULL, "", "grapevine_weekly_open", notes))
        self.assertEqual(len(notes), 1)
        self.assertIsNone(W.join_link(None, "8712", "x"))

    def test_la_vinas_item(self):
        cfg = {"day": "thursday", "time": "12:00", "timezone": "America/New_York", "zoom_id": ZOOM_ID, "passcode": "238047"}
        self.assertEqual(W.lavina_item(cfg)["extra"]["zoom_url"], PLAIN)
        self.assertEqual(W.lavina_item({**cfg, "zoom_url": FULL})["extra"]["zoom_url"], FULL)
        notes: list[str] = []
        self.assertEqual(W.lavina_item({**cfg, "zoom_url": OTHER_ROOM}, notes=notes)["extra"]["zoom_url"], PLAIN)
        self.assertEqual(len(notes), 1)


class Run(unittest.TestCase):
    """main() over the saved aagrapevine.org page with settings of the test's own (data/raw in a temporary folder)."""

    LV = {"enabled": True, "day": "thursday", "time": "12:00", "timezone": "America/New_York", "starts": "2026-11-05",
          "zoom_id": ZOOM_ID, "passcode": "238047"}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-r26c-"))
        p = mock.patch.object(common, "RAW_DIR", self.tmp)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_main(self, page: str, gv: dict | None, lv: dict | None) -> dict:
        cfg = {"sources": {"grapevine": {"base": "https://www.aagrapevine.org", "weekly_open": "/grapevine-weekly-open"}},
               "lavina_weekly_open": lv, **({"grapevine_weekly_open": gv} if gv is not None else {})}
        f = self.tmp / "page.html"
        f.write_text(page, encoding="utf-8")
        with mock.patch.object(W, "load_config", return_value=cfg):
            W.main(["--html", str(f)])
        return json.loads((self.tmp / "weekly_open.json").read_text(encoding="utf-8"))

    def test_both_meetings_get_their_full_link(self):
        env = self.run_main(PAGE.read_text(encoding="utf-8"), {"zoom_url": FULL}, {**self.LV, "zoom_url": FULL})
        self.assertTrue(env["ok"])
        self.assertEqual([(i["id"], i["extra"]["zoom_url"]) for i in env["items"]],
                         [("weekly_open", FULL), ("weekly_open_lv", FULL)])
        self.assertNotIn("warnings", env["stats"])

    def test_without_the_settings_the_plain_links(self):
        env = self.run_main(PAGE.read_text(encoding="utf-8"), None, self.LV)
        self.assertEqual([i["extra"]["zoom_url"] for i in env["items"]], [PLAIN, PLAIN])
        self.assertNotIn("warnings", env["stats"])

    def test_a_link_to_another_room_is_said_on_the_status_page(self):
        env = self.run_main(PAGE.read_text(encoding="utf-8"), {"zoom_url": OTHER_ROOM}, {**self.LV, "zoom_url": OTHER_ROOM})
        self.assertEqual([i["extra"]["zoom_url"] for i in env["items"]], [PLAIN, PLAIN])
        self.assertEqual([w.split(":")[0] for w in env["stats"]["warnings"]], ["grapevine_weekly_open", "lavina_weekly_open"])
        # fixed: the next run's notes are its own
        env = self.run_main(PAGE.read_text(encoding="utf-8"), {"zoom_url": FULL}, {**self.LV, "zoom_url": FULL})
        self.assertNotIn("warnings", env["stats"])

    def test_the_link_follows_the_id_kept_from_the_day_before(self):
        self.run_main(PAGE.read_text(encoding="utf-8"), None, self.LV)
        no_id = PAGE.read_text(encoding="utf-8").replace("use Zoom code 871 2036 8287 with password", "with password")
        self.assertNotIn("871 2036 8287", no_id)
        env = self.run_main(no_id, {"zoom_url": FULL}, self.LV)
        self.assertEqual(env["stats"]["kept_from_previous"], ["zoom_id"])
        self.assertEqual(env["items"][0]["extra"]["zoom_url"], FULL)

    def test_a_page_that_cannot_be_read_keeps_the_item_with_todays_link(self):
        self.run_main(PAGE.read_text(encoding="utf-8"), None, self.LV)
        env = self.run_main("", {"zoom_url": FULL}, {**self.LV, "zoom_url": FULL})
        self.assertFalse(env["ok"])
        self.assertEqual([i["extra"]["zoom_url"] for i in env["items"]], [FULL, FULL])
        env = self.run_main("<html><body><main><h1>Page not found</h1></main></body></html>", {"zoom_url": OTHER_ROOM}, self.LV)
        self.assertFalse(env["ok"])
        self.assertEqual(env["items"][0]["extra"]["zoom_url"], PLAIN)
        self.assertEqual(len(env["stats"]["warnings"]), 1)

    def test_a_push_that_edits_the_setting_runs_the_source(self):
        old = "sources:\n  grapevine:\n    weekly_open: \"/grapevine-weekly-open\"\ngrapevine_weekly_open:\n  zoom_url: \"\"\n"
        new = old.replace('zoom_url: ""', f'zoom_url: "{FULL}"')
        also, why, notices = P.decide(["config/site.yml"], old, new)
        self.assertEqual((also, notices), (["weekly_open"], []))
        self.assertEqual(P.reason(why["weekly_open"]), "config/site.yml: grapevine_weekly_open")


# ---------------------------------------------------------------------------------------------- the pages
NOW = "2026-11-12T18:00:00Z"        # Thu Nov 12, noon Central: both meetings meet every week


def weekly_item(lv: bool) -> dict:
    """A weekly_open.json item as scripts/sync/weekly_open.py writes it, with the full link."""
    extra = {"zoom_id": ZOOM_ID, "passcode": "238047", "zoom_url": FULL, "start_local": "12:00",
             "timezone": "America/New_York", "time_central": "11 AM Central"}
    if lv:
        extra.update({"day": "Jueves", "time": "12 p. m. (hora del Este)", "weekday": "thursday",
                      "next_start": "2026-11-12T17:00:00Z", "starts": "2026-11-05"})
        title = {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"}
        summary = {"en": "A virtual open AA meeting in Spanish.", "es": "Una reunión abierta virtual de AA en español."}
        day = {"en": "Thursdays", "es": "Jueves"}
    else:
        extra.update({"day": "Wednesdays", "time": "Noon Eastern", "weekday": "wednesday", "url": GV_PAGE_URL,
                      "next_start": "2026-11-18T17:00:00Z"})
        title = {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"}
        summary = {"en": "Each week AA Grapevine holds an open virtual AA meeting.", "es": "Cada semana AA Grapevine celebra una reunión abierta."}
        day = {"en": "Wednesdays", "es": "Miércoles"}
    return {
        "id": "weekly_open_lv" if lv else "weekly_open", "source": "lavina" if lv else "grapevine", "kind": "meeting",
        "url": "https://www.aalavina.org/podcast" if lv else GV_PAGE_URL, "title": title["es" if lv else "en"],
        "summary": summary["es" if lv else "en"], "lang": "es" if lv else "en", "status": "ok", "extra": extra,
        "i18n": {"title": title, "summary": summary, "day": day,
                 "time": {"en": "Noon Eastern", "es": "mediodía (hora del Este)"},
                 "time_central": {"en": "11:00 AM Central", "es": "11:00 a. m. (hora del Centro)"},
                 "when": {"en": f"{day['en']} at 11:00 AM Central", "es": f"Los {day['es'].lower()} a las 11:00 a. m. (hora del Centro)"}},
    }


def drive_item(fid: str, title: str, date: str, en: str = "", es: str = "", category: str = "flyers") -> dict:
    return {"id": f"drive:{fid}", "source": "drive", "kind": "photo", "category": category, "title": title,
            "date": date, "first_seen": f"{date}T15:00:00Z", "status": "ok", "lang": "",
            "url": f"https://drive.google.com/file/d/{fid}/view",
            "i18n": {"title": {"en": en or title, "es": es or title}},
            "extra": {"name": title + ".png", "mime": "image/png", "is_image": True, "path": [category], "panel": 77,
                      "view_url": f"https://drive.google.com/file/d/{fid}/view"}}


DRIVE = [
    drive_item("gvFlyer", GV_FLYER, "2026-11-12", es="Reunión abierta semanal de Grapevine (en inglés) - todos los miércoles"),
    drive_item("lvNewest", LV_FLYER, "2026-11-12", en="La Viña Open Meeting (in Spanish) - Every Thursday"),
    drive_item("lvNovember", LV_NOVEMBER, "2026-09-25", en="New La Viña Open Meeting - Thursdays at 12 PM Eastern on Zoom"),
    # newer, and named like it, but not a flyer: never the card's link
    drive_item("gvSlides", "Grapevine Weekly Open AA Meeting - slides", "2026-11-13", category="slides"),
]
NO_GV_FLYER = [d for d in DRIVE if d["id"] != "drive:gvFlyer"]
GV_MATCH, LV_MATCH = "grapevine weekly open", "reuni[oó]n abierta de la vi[nñ]a|la vi[nñ]a open meeting"

PAGES_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r26c-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, weekly_open: { updated: "2026-11-12T12:00:00Z", items: input.weekly },
                         drive: { updated: "2026-11-12T12:00:00Z", items: input.drive } }),
        // the flyer patterns of the test's own (the committee's are RealSettings')
        site: (data) => ({ ...data.site, grapevine_weekly_open: { flyer_match: input.gv_match },
                           lavina_weekly_open: { ...data.site.lavina_weekly_open, flyer_match: input.lv_match } }),
      });
    },
  });
  const pages = await elev.toJSON();
  const want = new Set(input.urls);
  out(Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
BUILT: dict[str, dict] = {}


def built(case: unittest.TestCase, drive: str = "all") -> dict:
    """/meetings/ (+ its weekly .ics files and /events/ with the whole Drive list) in both languages."""
    if drive not in BUILT:
        if drive == "all":
            only, paths = "meetings,events.njk", ["meetings/", "meetings/weekly-open-gv.ics", "meetings/weekly-open-lv.ics",
                                                  "events/"]
        else:
            only, paths = "meetings.njk", ["meetings/"]
        urls = [pre + p for p in paths for pre in ("/", "/es/")]
        BUILT[drive] = run_js(case, PAGES_JS, data={"only": only, "urls": urls, "weekly": [weekly_item(False), weekly_item(True)],
                                                    "drive": DRIVE if drive == "all" else NO_GV_FLYER,
                                                    "gv_match": GV_MATCH, "lv_match": LV_MATCH},
                              timeout=600, now=NOW)
    return BUILT[drive]


def cards(page: str) -> dict[str, str]:
    """/meetings/' weekly open cards: {"gv" | "lv": the card's HTML}."""
    return {m.group(1): m.group(0) for m in re.finditer(r'<article [^>]*aria-labelledby="wo-(gv|lv)-title">.*?</article>', page, re.S)}


def visible(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", " ", fragment, flags=re.S)))).strip()


def gcal_query(fragment: str) -> dict[str, str]:
    hrefs = [html.unescape(h) for h in re.findall(r'href="(https://calendar\.google\.com/calendar/render\?[^"]+)"', fragment)]
    assert len(hrefs) == 1, hrefs
    return {k: v[0] for k, v in parse_qs(urlsplit(hrefs[0]).query).items()}


def flyer_link(card: str, lang: str) -> str | None:
    m = re.search(r'<a class="btn-ghost btn-sm" href="([^"]+)"[^>]*>(?:(?!</a>).)*?' + re.escape(T["committee.events.view_flyer"][lang]),
                  card, re.S)
    return html.unescape(m.group(1)) if m else None


class MeetingsPage(unittest.TestCase):
    def test_join_is_the_full_link_on_both_cards(self):
        p = built(self)
        for lang, pre in (("en", "/"), ("es", "/es/")):
            for key, card in cards(p[pre + "meetings/"]).items():
                with self.subTest(lang=lang, card=key):
                    join = re.findall(r'<a class="btn-primary" href="([^"]+)"', card)
                    self.assertEqual([html.unescape(h) for h in join], [FULL])
                    self.assertIn(T["committee.meeting.join"][lang].replace("{platform}", "Zoom"), visible(card))
            self.assertEqual(sorted(cards(p[pre + "meetings/"])), ["gv", "lv"])

    def test_google_calendar_carries_the_full_link(self):
        p = built(self)
        for lang, pre in (("en", "/"), ("es", "/es/")):
            for key, card in cards(p[pre + "meetings/"]).items():
                with self.subTest(lang=lang, card=key):
                    q = gcal_query(card)
                    self.assertEqual(q["location"], FULL)
                    self.assertIn(f": {FULL}\n", q["details"])
                    self.assertIn("87120368287%3Fpwd%3DVYskKcQbHB4KtZiTk0EmDcMuJO95kV.1", card, "encoded in the address")

    def test_the_calendar_files_carry_the_full_link(self):
        p = built(self)
        for lang, pre in (("en", "/"), ("es", "/es/")):
            for key in ("gv", "lv"):
                with self.subTest(lang=lang, file=key):
                    ics = p[f"{pre}meetings/weekly-open-{key}.ics"]
                    self.assertTrue(all(len(ln.encode("utf-8")) <= 75 for ln in ics.split("\r\n")), "folded at 75 octets")
                    lines = ics.replace("\r\n ", "").split("\r\n")
                    self.assertIn("LOCATION:" + FULL, lines)
                    desc = next(ln for ln in lines if ln.startswith("DESCRIPTION:"))
                    self.assertIn(f": {FULL}\\n", desc)          # (RFC 5545 escapes no ":", "?", "=" or ".")

    def test_the_events_cards_calendar_links_carry_it_and_how_to_join_still_leads_to_meetings(self):
        p = built(self)
        for lang, pre in (("en", "/"), ("es", "/es/")):
            with self.subTest(lang=lang):
                page = p[pre + "events/"]
                i = page.index('<section id="ev-weekly"')
                block = page[i:page.index("</section>", i)]
                for m in re.finditer(r'<article class="card ev-accent ev-tone-(gv|lv)[^"]*".*?</article>', block, re.S):
                    self.assertEqual(gcal_query(m.group(0))["location"], FULL)
                    self.assertFalse(re.search(r'href="https?://([\w-]+\.)*zoom\.us/', m.group(0)))
                    self.assertIn(f'href="{pre}meetings/#weekly-open"', m.group(0))

    def test_each_card_links_its_own_flyer(self):
        p = built(self)
        for lang, pre in (("en", "/"), ("es", "/es/")):
            c = cards(p[pre + "meetings/"])
            with self.subTest(lang=lang):
                self.assertEqual(flyer_link(c["gv"], lang), "https://drive.google.com/file/d/gvFlyer/view")
                # one source line: the plain one, then the short flyer sentence (whole, on its own line if it wraps)
                self.assertIn(T["committee.weekly.source_gv"][lang] + " " + T["committee.weekly.source_gv_flyer"][lang],
                              visible(c["gv"]))
                self.assertEqual(visible(c["gv"]).count(T["committee.weekly.source_gv"][lang]), 1)
                self.assertIn(T["committee.weekly.source_gv_flyer"][lang],
                              [html.unescape(s) for s in re.findall(r'<span class="inline-block">([^<]*)</span>', c["gv"])])
                # La Viña's newest flyer, never November's (older) or the Grapevine one
                self.assertEqual(flyer_link(c["lv"], lang), "https://drive.google.com/file/d/lvNewest/view")
                self.assertIn(T["committee.weekly.source_lv"][lang], visible(c["lv"]))

    def test_no_grapevine_flyer_no_link(self):
        p = built(self, drive="no-gv")
        for lang, pre in (("en", "/"), ("es", "/es/")):
            c = cards(p[pre + "meetings/"])
            with self.subTest(lang=lang):
                self.assertIsNone(flyer_link(c["gv"], lang), "the newer slides file is not a flyer")
                self.assertIn(T["committee.weekly.source_gv"][lang], visible(c["gv"]))
                self.assertNotIn(T["committee.weekly.source_gv_flyer"][lang], visible(c["gv"]))
                self.assertEqual(flyer_link(c["lv"], lang), "https://drive.google.com/file/d/lvNewest/view")

    def test_the_words(self):
        for lang in ("en", "es"):
            text = T["committee.weekly.source_gv_flyer"][lang]
            self.assertNotRegex(text, r"(?i)\bpdf\b|automatic")
            self.assertIn("AA Grapevine", text)
            # one short sentence after the card's plain line (which names aagrapevine.org)
            self.assertLess(len(text), 40, text)
            self.assertIn("aagrapevine.org", T["committee.weekly.source_gv"][lang])


# ---------------------------------------------------------------------------------------------- the settings
class RealSettings(unittest.TestCase):
    """config/site.yml and data/translations/overrides.yml as the committee keeps them."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = config()
        cls.gv = cls.cfg.get("grapevine_weekly_open") or {}
        cls.lv = cls.cfg.get("lavina_weekly_open") or {}

    def test_both_full_links_open_their_meetings_room(self):
        gv_id = W.parse_page(PAGE.read_text(encoding="utf-8"), GV_PAGE_URL)["zoom_id"]    # the page as it reads today
        for name, block, zid in (("grapevine_weekly_open", self.gv, gv_id), ("lavina_weekly_open", self.lv, self.lv["zoom_id"])):
            with self.subTest(setting=name):
                link = block.get("zoom_url")
                self.assertRegex(link, W.JOIN_LINK_RE)
                self.assertIn("?pwd=", link, "the full link: nobody types the passcode")
                notes: list[str] = []
                self.assertEqual(W.join_link(link, zid, name, notes), link)
                self.assertEqual(notes, [])

    def test_each_flyer_pattern_finds_its_own_flyer_only(self):
        gv, lv = (re.compile(b["flyer_match"], re.I) for b in (self.gv, self.lv))
        overrides = yaml.safe_load((ROOT / "data" / "translations" / "overrides.yml").read_text(encoding="utf-8"))
        gv_es, lv_en = overrides[GV_FLYER]["es"], overrides[LV_FLYER]["en"]
        for text in (GV_FLYER, GV_FLYER + ".png"):
            self.assertRegex(text, gv)
            self.assertNotRegex(text, lv)
        for text in (LV_FLYER, LV_FLYER + ".jpg", lv_en):
            self.assertRegex(text, lv)
            self.assertNotRegex(text, gv)
        self.assertNotRegex(gv_es, lv, "the Grapevine flyer's Spanish title is not La Viña's flyer")
        # the settings' other patterns never take the two flyers, and these two never take the other files they name
        others = [self.cfg["meeting"].get("flyer_match")]
        others += [e.get("flyer_match") for e in self.cfg.get("recurring_events") or [] if isinstance(e, dict)]
        others += [o.get("banner_match") for o in self.cfg.get("store_offers") or [] if isinstance(o, dict)]
        others += [c.get("doc_match") for c in self.cfg.get("price_changes") or [] if isinstance(c, dict)]
        for pattern in filter(None, others):
            for text in (GV_FLYER, LV_FLYER, gv_es, lv_en):
                self.assertNotRegex(text, re.compile(pattern, re.I), pattern)
        for name in ("Grapevine Meeting - flyer", "Committee Meeting - flyer", "Our online meetings - flyer",
                     "2027 Guest Speaker Series - flyer", "January 2027 Committee Meeting - guest speaker",
                     "Free shipping on all Grapevine products - banner", "Grapevine Writing Workshop - Primary Purpose Group, Arlington",
                     "Grapevine Editorial - Share your story - Fun in Sobriety and Emotional Sobriety",
                     "Taller Mensual y Virtual de La Viña - jueves, 3 p. m. (hora del Este), por Zoom"):
            self.assertNotRegex(name, gv)
            self.assertNotRegex(name, lv)

    def test_their_titles_in_the_other_language(self):
        overrides = yaml.safe_load((ROOT / "data" / "translations" / "overrides.yml").read_text(encoding="utf-8"))
        self.assertEqual(overrides[GV_FLYER], {"es": "Reunión abierta semanal de Grapevine (en inglés) - todos los "
                                                     "miércoles, 11 a. m. hora del Centro (mediodía del Este), por Zoom"})
        self.assertEqual(overrides[LV_FLYER], {"en": "La Viña Open Meeting (in Spanish) - every Thursday, 11 AM Central "
                                                     "(noon Eastern), on Zoom"})

    def test_la_vinas_summaries_follow_its_newest_flyer(self):
        item = W.lavina_item(self.lv)
        self.assertTrue(item["summary"].endswith(T["committee.weekly.closing"]["es"]), "the synced summary, not cut off")
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                s = self.lv[f"summary_{lang}"]
                self.assertTrue(s.endswith(" " + T["committee.weekly.closing"][lang]), "the sign-off last, word for word")
                self.assertEqual(s.count(T["committee.weekly.closing"][lang]), 1)
                self.assertLessEqual(len(s), 400, "make_item cuts a summary at 400 characters: the sign-off would be lost")
                self.assertTrue(item["extra"]["own_i18n"]["summary"][lang].endswith(T["committee.weekly.closing"][lang]))
                self.assertNotRegex(s, r"(?i)\bpdf\b|automatic|\bnuevo pódcast|\bnew podcast")
                self.assertIn("La Viña", s)
                self.assertIn("YouTube", s)
        self.assertIn("dos oradores que son miembros de AA", self.lv["summary_es"])
        self.assertIn("two speakers who are AA members", self.lv["summary_en"])
        self.assertIn("tus plataformas", self.lv["summary_es"], "tú, never usted")
        self.assertIn("2026-11-12", self.lv["source"])


if __name__ == "__main__":
    unittest.main()
