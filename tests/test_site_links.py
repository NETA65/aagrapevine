"""Links, settings and the template helpers (eleventy.config.js, src/_data/site.js, config/site.yml):

  * Spanish twins — a `links:` entry with a Spanish twin ("<name>_es", or lleva_el_mensaje for
                    carry_the_message) is shown in Spanish on /es/ pages: the `langLink` helper, on /shop/ and
                    /accessibility/;
  * settings      — what templates read from `site.*` reaches them (meetings, spotlight): /meetings/ without
                    data/site/meetings.json still names the offices to look at and "Our Area"; every `links:`
                    entry is used and every link a template reads exists; settings that did nothing are gone
                    (site.languages / default_lang, three unused links, contribute's lv_record_story); the
                    committee meeting's `platform` and `note` (+ note_es) are what the pages say;
  * helpers       — siteUrl leaves an absolute address alone; lurl / community.js hrefOf never put /es in front
                    of a file the build does not make for Spanish ("/bulletin/files/flyer.pdf", /assets/), and
                    do for the ones it does (/es/feed.xml, /es/events.ics …); pickLang falls back to the item's
                    own words before English; shareImage takes only pictures the link previews show;
  * counts        — the Library's "new this month" is this calendar month (Central), the /search/ Events tile
                    counts what the Events page's own tab counts, "Subscriptions from" is the U.S. store's;
  * La Viña's monthly workshop has one name, the one La Viña uses ("Taller Mensual y Virtual de La Viña");
  * share pictures — a page's `ogImage` (address or { src, width, height, alt }) → og:image / twitter:image;
                    every event of /events/ has a small share page (/events/<anchor>/) with its flyer as the
                    picture, which its card's Share button sends (once its event has left the list, the 404 page
                    sends that address on to /events/); /events/ names its calendar file in <head>.

    python -m unittest tests.test_site_links -v        (or: python -m unittest discover -s tests)
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


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


CFG = yaml.safe_load(read("config", "site.yml"))
SITE_URL = CFG["site"]["url"].rstrip("/")


# --------------------------------------------------------------------------------------------- Spanish twins
class SpanishTwins(unittest.TestCase):
    def test_lang_link(self):
        links = {"carry_the_message": "https://gv/ctm", "lleva_el_mensaje": "https://lv/lleva",
                 "aa_twelve_and_twelve": "https://aa/12", "aa_twelve_and_twelve_es": "https://aa/es/12",
                 "aa_big_book": "https://aa/bb", "support_phone_es": "(800) 640-8781"}
        r = run_js(self, """
            const L = input;
            const f = filters.langLink;
            out({
              ctm: [f(L, "carry_the_message", "en"), f(L, "carry_the_message", "es")],
              tt: [f(L, "aa_twelve_and_twelve", "en"), f(L, "aa_twelve_and_twelve", "es")],
              bb: f(L, "aa_big_book", "es"), phone: f(L, "support_phone_es", "es"),
              none: f(L, "no_such_link", "es"), noLinks: f(null, "carry_the_message", "es"),
              noTwin: f({ carry_the_message: "https://gv/ctm" }, "carry_the_message", "es"),
            });
        """, data=links)
        self.assertEqual(r["ctm"], ["https://gv/ctm", "https://lv/lleva"])
        self.assertEqual(r["tt"], ["https://aa/12", "https://aa/es/12"])
        self.assertEqual(r["bb"], "https://aa/bb")                         # no twin: the link itself
        self.assertEqual(r["phone"], "(800) 640-8781")                     # an "_es" key is no twin of anything
        self.assertEqual((r["none"], r["noLinks"]), ("", ""))
        self.assertEqual(r["noTwin"], "https://gv/ctm")

    def test_every_twin_in_the_settings_is_shown(self):
        """Each Spanish twin in config/site.yml is read by the pages: by langLink, or picked by hand where the
        page already did (offline.njk's install help, about.njk's aa.org link)."""
        links = CFG["links"]
        twins = {k for k in links if k.endswith("_es") and k[:-3] in links} | {"lleva_el_mensaje"}
        code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src").rglob("*.njk"))
        for twin in sorted(twins):
            base = "carry_the_message" if twin == "lleva_el_mensaje" else twin[:-3]
            with self.subTest(link=twin):
                self.assertTrue(re.search(r"langLink\(\s*['\"]" + base + r"['\"]", code) or "." + twin in code
                                or re.search(r"langLink\(ph\[0\]", code) and base.startswith("support_phone"), twin)
        shop, access = read("src", "pages", "shop.njk"), read("src", "pages", "accessibility.njk")
        self.assertIn("L | langLink('carry_the_message', lang)", shop)
        self.assertNotIn("L.carry_the_message", shop)
        self.assertIn('ln | langLink("aa_twelve_and_twelve", lang)', access)
        # the audio card says "(in English)" only when it is not in the page's language (and its hreflang says so)
        self.assertIn('hreflang="{{ c.hl or \'en\' }}"', access)
        es = json.loads(read("src", "_i18n", "access.json"))["access.aud_aa"]["es"]
        self.assertNotIn("inglés", es)


# --------------------------------------------------------------------------------------------- helpers
HELPERS_JS = r"""
const conf = await imp("eleventy.config.js");
const C = await imp("eleventy/filters/community.js");
const site = { url: "https://example.org/gv" };
const res = { before: {}, after: {} };
const paths = ["/events/", "events/", "/bulletin/files/flyer.pdf", "/bulletin/files/Flyer.JPG", "/assets/img/og.png",
  "/assets/js/app.js", "/feed.xml", "/events.ics", "/manifest.webmanifest", "/search-index.json", "/about/booth.json",
  "/library/?q=x#top", "https://www.aa.org/x", "mailto:a@b.org", "#top", "//cdn.example.org/a.png"];
for (const p of paths) res.before[p] = filters.lurl(p, "es");
res.hrefFile = C.hrefOf({ url: "/bulletin/files/flyer.pdf" }, "es");
res.hrefPage = C.hrefOf({ url: "/bulletin/#post" }, "es");
// what a build does before rendering: it tells the config every address it writes (eleventy.contentMap)
const handlers = {};
conf.default(new Proxy({}, { get(_t, name) {
  if (name === "on") return (ev, fn) => { handlers[ev] = fn; };
  return () => ({ add() {} });
} }));
handlers["eleventy.contentMap"]({ urlToInputPath: Object.fromEntries(
  ["/feed.xml", "/es/feed.xml", "/events.ics", "/es/events.ics", "/manifest.webmanifest", "/es/manifest.webmanifest",
   "/search-index.json", "/es/search-index.json", "/about/booth.json", "/events/", "/es/events/"].map((u) => [u, "x"])) });
for (const p of paths) res.after[p] = filters.lurl(p, "es");
res.en = filters.lurl("/feed.xml", "en");
res.hrefFileAfter = C.hrefOf({ url: "/bulletin/files/flyer.pdf" }, "es");
res.site = ["/es/library/", "es/x/", "https://lh3.googleusercontent.com/d/abc=w1200", "//cdn.example.org/a.png",
  "http://old.example.org/x", "", null].map((u) => filters.siteUrl(u, site));
res.siteNoBase = filters.siteUrl("/x/", {});
// an address of no kind these helpers know ("javascript:", "data:") stays a harmless address on the site
res.odd = { lurl: ["javascript:alert(1)", "data:text/html,x"].map((u) => filters.lurl(u, "es")),
            site: ["javascript:alert(1)", "webcal://example.org/gv/events.ics"].map((u) => filters.siteUrl(u, site)) };
const item = (o) => ({ title: "Original", ...o });
res.pick = {
  // a Spanish story without a Spanish entry: its own Spanish words, not the English translation
  esOwn: filters.tx(item({ lang: "es", title: "Decisiones", i18n: { title: { en: "Decisions" } } }), "title", "es"),
  esToEn: filters.tx(item({ lang: "es", title: "Decisiones", i18n: { title: { en: "Decisions" } } }), "title", "en"),
  // its language's entry (a tidied original) before the raw field
  ownEntry: filters.tx(item({ lang: "es", title: "decisiones ", i18n: { title: { es: "Decisiones" } } }), "title", "fr"),
  // a field written for the language wins over another language's translation
  fieldLang: filters.tx(item({ lang: "en", title: "Spring", title_es: "Primavera", i18n: { title: { en: "Spring" } } }), "title", "es"),
  // English only when the item has no words of its own
  enLast: filters.tx({ lang: "es", title: "", i18n: { title: { en: "Only English" } } }, "title", "es"),
  extra: filters.tx({ lang: "en", extra: { location: "Tyler" }, i18n: {} }, "location", "es"),
  emptyEs: filters.tx(item({ lang: "en", title: "Fall", i18n: { title: { en: "Fall", es: "" } } }), "title", "es"),
};
const S = filters.shareImage;
res.share = {
  png: S("/assets/img/poster.png?v=3", site),
  obj: S({ src: "/assets/img/poster.png", width: 1080, height: 1350, alt: "  The  poster " }, site),
  half: S({ src: "/assets/img/poster.jpg", width: 1080 }, site),
  lh3: S("https://lh3.googleusercontent.com/d/abc123def456=w1200", site),
  yt: S("https://i.ytimg.com/vi/xyz/hqdefault.jpg", site),
  svg: S("/assets/img/logo.svg", site), pdf: S("https://www.aa.org/files/x.pdf", site),
  page: S("https://www.aagrapevine.org/store", site), js: S("javascript:alert(1)", site), none: S(undefined, site),
  webp: S({ src: "https://www.aalavina.org/files/flyer.WEBP" }, site),
};
out(res);
"""


class TemplateHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def res(self):
        if TemplateHelpers.r is None:
            TemplateHelpers.r = run_js(self, HELPERS_JS)
        return TemplateHelpers.r

    def test_lurl_pages_and_links_elsewhere(self):
        b = self.res()["before"]
        self.assertEqual((b["/events/"], b["events/"], b["/library/?q=x#top"]), ("/es/events/", "/es/events/", "/es/library/?q=x#top"))
        for u in ("https://www.aa.org/x", "mailto:a@b.org", "#top", "//cdn.example.org/a.png"):
            self.assertEqual(b[u], u)
        self.assertEqual(self.res()["en"], "/feed.xml")

    def test_lurl_never_sends_a_file_to_a_spanish_copy_that_does_not_exist(self):
        r = self.res()
        for when in ("before", "after"):
            for u in ("/bulletin/files/flyer.pdf", "/bulletin/files/Flyer.JPG", "/assets/img/og.png", "/assets/js/app.js"):
                with self.subTest(when=when, url=u):
                    self.assertEqual(r[when][u], u)
        # outside a build (no list of what it writes): no file is sent to /es/
        for u in ("/feed.xml", "/events.ics", "/manifest.webmanifest", "/search-index.json"):
            self.assertEqual(r["before"][u], u)
        # in a build: the files made for Spanish too keep their /es/ address; one made once does not
        for u in ("/feed.xml", "/events.ics", "/manifest.webmanifest", "/search-index.json"):
            self.assertEqual(r["after"][u], "/es" + u)
        self.assertEqual(r["after"]["/about/booth.json"], "/about/booth.json")
        # community.js (What's New, the feeds, the digest) goes through the same rule
        self.assertEqual((r["hrefFile"], r["hrefFileAfter"], r["hrefPage"]),
                         ("/bulletin/files/flyer.pdf", "/bulletin/files/flyer.pdf", "/es/bulletin/#post"))

    def test_site_url(self):
        s = self.res()["site"]
        self.assertEqual(s, ["https://example.org/gv/es/library/", "https://example.org/gv/es/x/",
                             "https://lh3.googleusercontent.com/d/abc=w1200", "https://cdn.example.org/a.png",
                             "http://old.example.org/x", "https://example.org/gv/", "https://example.org/gv/"])
        self.assertEqual(self.res()["siteNoBase"], "/x/")

    def test_no_link_of_an_unknown_kind_is_let_through(self):
        odd = self.res()["odd"]
        self.assertEqual(odd["lurl"], ["/es/javascript:alert(1)", "/es/data:text/html,x"])
        self.assertEqual(odd["site"], ["https://example.org/gv/javascript:alert(1)", "webcal://example.org/gv/events.ics"])

    def test_pick_lang_falls_back_to_the_items_own_words_before_english(self):
        p = self.res()["pick"]
        self.assertEqual(p["esOwn"], "Decisiones")
        self.assertEqual(p["esToEn"], "Decisions")
        self.assertEqual(p["ownEntry"], "Decisiones")
        self.assertEqual(p["fieldLang"], "Primavera")
        self.assertEqual(p["enLast"], "Only English")
        self.assertEqual(p["extra"], "Tyler")
        self.assertEqual(p["emptyEs"], "Fall")
        # one pickLang for the pages and community.js (no copy of its own any more)
        self.assertNotIn("function pickLang", read("eleventy", "filters", "community.js"))
        self.assertIn("langPath, pickLang } from \"../../eleventy.config.js\"", read("eleventy", "filters", "community.js"))

    def test_share_image(self):
        s = self.res()["share"]
        self.assertEqual(s["png"], {"url": "https://example.org/gv/assets/img/poster.png?v=3", "width": 0, "height": 0, "alt": ""})
        self.assertEqual(s["obj"], {"url": "https://example.org/gv/assets/img/poster.png", "width": 1080, "height": 1350, "alt": "The poster"})
        self.assertEqual((s["half"]["width"], s["half"]["height"]), (0, 0))      # a size is given whole or not at all
        self.assertEqual(s["lh3"]["url"], "https://lh3.googleusercontent.com/d/abc123def456=w1200")
        self.assertEqual(s["yt"]["url"], "https://i.ytimg.com/vi/xyz/hqdefault.jpg")
        self.assertEqual(s["webp"]["url"], "https://www.aalavina.org/files/flyer.WEBP")
        for k in ("svg", "pdf", "page", "js", "none"):
            self.assertIsNone(s[k], k)


# --------------------------------------------------------------------------------------------- settings
class Settings(unittest.TestCase):
    def test_settings_that_did_nothing_are_gone(self):
        self.assertNotIn("default_lang", CFG["site"])
        self.assertNotIn("languages", CFG["site"])
        for k in ("sobriety_calculator", "instagram_gv", "instagram_lv"):
            self.assertNotIn(k, CFG["links"])
        contribute = read("src", "pages", "contribute.njk")
        self.assertNotIn("lv_record_story", contribute)
        # La Viña's "Graba tu historia" page: the one scripts/sync/audio_project.py reads
        self.assertIn("site.sources.lavina.record_story", contribute)
        self.assertEqual(CFG["sources"]["lavina"]["record_story"], "/graba-tu-historia")

    def test_every_link_in_the_settings_is_used(self):
        links = CFG["links"]
        files = [p for d in ("src", "eleventy", "scripts") for p in (ROOT / d).rglob("*")
                 if p.is_file() and p.suffix in {".njk", ".js", ".mjs", ".py"} and "cache" not in p.parts]
        code = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files) + read("eleventy.config.js")
        used = {k for k in links if re.search(r"\b" + re.escape(k) + r"\b", code)}
        # a twin is used when its link is: "<name>_es" through langLink / pick, lleva_el_mensaje through langLink
        twins = {k for k in links if k.endswith("_es") and k[:-3] in used}
        self.assertIn("carry_the_message", used)
        self.assertIn('{ es: { carry_the_message: "lleva_el_mensaje" } }', read("eleventy.config.js"))
        twins.add("lleva_el_mensaje")
        self.assertEqual(sorted(set(links) - used - twins), [])

    def test_every_link_a_template_reads_exists(self):
        links = set(CFG["links"])
        missing = []
        for p in sorted((ROOT / "src").rglob("*.njk")):
            t = p.read_text(encoding="utf-8")
            aliases = {"site.links"} | set(re.findall(r"set (\w+) = site\.links\b", t))
            for a in aliases:
                for k in re.findall(r"(?<![\w.])" + re.escape(a) + r"\.([a-z][a-z0-9_]*)", t):
                    if k not in links:
                        missing.append(f"{p.relative_to(ROOT).as_posix()}: {a}.{k}")
            for k in re.findall(r"langLink\(\s*['\"]([a-z0-9_]+)['\"]", t):
                if k not in links:
                    missing.append(f"{p.relative_to(ROOT).as_posix()}: langLink {k}")
        self.assertEqual(missing, [])

    def test_meeting_platform_and_note(self):
        m = CFG["meeting"]
        self.assertEqual(m["platform"], "Zoom")
        self.assertTrue(m["note"] and m["note_es"])
        strings = {}
        for f in ("committee", "community", "home", "orientation", "read"):
            strings.update(json.loads(read("src", "_i18n", f + ".json")))
        keys = ["committee.meeting.hero_sub", "committee.meeting.join", "committee.meeting.join_hint",
                "committee.meeting.how_to_join_text", "committee.meeting.cal_desc", "committee.meeting.cal_join",
                "committee.meeting.copy_link", "committee.meeting.tip_phone", "committee.meeting.contact_text",
                "committee.meetings.committee_eyebrow", "committee.meetings.meta_desc", "home.meeting_join",
                "home.meeting_cal_desc", "orientation.live_meeting_sub", "orientation.ns_meeting_cta", "read.gvr.s_meeting",
                "committee.events.src_meetings_text", "community.share.msg_long_text"]
        for k in keys:
            for lang in ("en", "es"):
                with self.subTest(key=k, lang=lang):
                    self.assertIn("{platform}", strings[k][lang])
                    self.assertNotIn("Zoom", strings[k][lang])
        # the note is who may come: the calendar line and the Who card no longer say it themselves
        for k in ("committee.meeting.cal_desc", "home.meeting_cal_desc", "committee.meeting.who_text"):
            self.assertNotRegex(strings[k]["en"], r"(?i)all AA members are welcome")
        # no "Zoom" written into the pages for the committee meeting (the weekly open meetings are Zoom's own)
        self.assertNotRegex(read("src", "pages", "events.njk"), r'%\}\s*Zoom</span>')

    def test_meeting_text_from_the_settings(self):
        """The committee meeting's calendar line and its join line in the calendars name the platform and add the
        note in the page's language (eleventy/filters/committee.js normalizeEvents)."""
        site = {"url": "https://example.org/gv", "meeting": {
            "week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet",
            "zoom_url": "https://meet.example.org/abc", "note": "Open to every AA member.", "note_es": "Abierta a todo miembro de AA."}}
        r = run_js(self, """
            const C = await imp("eleventy/filters/committee.js");
            const one = (site, lang) => C.normalizeEvents([], site, lang, { monthsBack: 0, monthsAhead: 2 }).find((e) => e.committee);
            const a = one(input, "en"), b = one(input, "es");
            const plain = one({ url: input.url, meeting: { ...input.meeting, platform: "", note: "", note_es: "" } }, "en");
            const noEs = one({ url: input.url, meeting: { ...input.meeting, note_es: "" } }, "es");
            out({ en: [a.summary, a.calDescription], es: [b.summary, b.calDescription], plain: plain.summary, noEs: noEs.summary });
        """, data=site)
        self.assertEqual(r["en"][0], "Monthly NETA 65 Grapevine / La Viña committee meeting on Google Meet. Open to every AA member.")
        self.assertIn("Join on Google Meet: https://meet.example.org/abc", r["en"][1])
        self.assertTrue(r["es"][0].endswith("por Google Meet. Abierta a todo miembro de AA."), r["es"][0])
        self.assertIn("Entrar por Google Meet: https://meet.example.org/abc", r["es"][1])
        self.assertEqual(r["plain"], "Monthly NETA 65 Grapevine / La Viña committee meeting on Zoom.")
        self.assertTrue(r["noEs"].endswith("Open to every AA member."))       # as every _es setting: English then

    def test_site_data(self):
        r = run_js(self, r"""
            const os = await import("node:os");
            const mod = await imp("src/_data/site.js");
            const real = mod.default();
            const runIn = (yamlText) => {
              const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-site-"));
              fs.mkdirSync(path.join(dir, "config"));
              fs.writeFileSync(path.join(dir, "config", "site.yml"), yamlText);
              const here = process.cwd();
              process.chdir(dir);
              try { return mod.default(); } finally { process.chdir(here); fs.rmSync(dir, { recursive: true, force: true }); }
            };
            out({
              meetings: real.meetings, spotlight: real.spotlight, platform: real.meeting.platform, note: real.meeting.note,
              noPlatform: runIn("meeting:\n  weekday: wednesday\n").meeting,
              noMeeting: runIn("site:\n  title: x\n").meeting,
              blank: runIn("meeting:\n  platform: '  '\n").meeting.platform,
            });
        """)
        self.assertEqual(r["meetings"]["area_label"], CFG["meetings"]["area_label"])
        self.assertEqual(len(r["meetings"]["feeds"]), len(CFG["meetings"]["feeds"]))
        self.assertEqual(r["spotlight"]["home_days"], CFG["spotlight"]["home_days"])
        self.assertEqual((r["platform"], r["note"]), ("Zoom", CFG["meeting"]["note"]))
        self.assertEqual(r["noPlatform"], {"weekday": "wednesday", "platform": "Zoom"})
        self.assertEqual(r["noMeeting"], {})                    # no meeting settings: still none (no rule of the pages')
        self.assertEqual(r["blank"], "Zoom")

    def test_meetings_without_their_data_name_the_offices(self):
        r = run_js(self, """
            const site = (await imp("src/_data/site.js")).default();
            out({ en: filters.cmGvMeetings({ updated: null, items: [] }, "en", site),
                  es: filters.cmGvMeetings({ updated: null, items: [] }, "es", site) });
        """)
        feeds = CFG["meetings"]["feeds"]
        for lang in ("en", "es"):
            g = r[lang]
            self.assertEqual(g["total"], 0)
            self.assertEqual([o["name"] for o in g["offices"]], [f["name"] for f in feeds])
            self.assertEqual([o["url"] for o in g["offices"]], [f["site"] for f in feeds])
            self.assertEqual(g["areaGroup"]["label"], CFG["meetings"]["area_label"][lang])


# --------------------------------------------------------------------------------------------- counts
class Counts(unittest.TestCase):
    def test_library_new_this_month_is_this_calendar_month(self):
        docs = [
            {"s": "gv", "ft": "pdf", "d": "2026-10-01", "or": False},      # the 1st: this month
            {"s": "gv", "ft": "pdf", "d": "2026-10-06", "or": False},      # today
            {"s": "lv", "ft": "pdf", "d": "2026-10-07", "or": False},      # tomorrow: not yet
            {"s": "lv", "ft": "pdf", "d": "2026-09-30", "or": False},      # last month (within 31 days)
            {"s": "neta", "ft": "doc", "d": "2026-10-02", "or": True},     # no page links it any more
            {"s": "neta", "ft": "doc", "d": "", "or": False},              # undated
        ]
        r = run_js(self, """
            const L = await imp("eleventy/filters/library.js");
            out({
              oct6: L.libraryStats(input, Date.parse("2026-10-06T17:00:00Z")).recent,
              // 10 PM Central on Sept 30 is already Oct 1 in UTC: still September in Central time
              sep30: L.libraryStats(input, Date.parse("2026-10-01T03:00:00Z")).recent,
              nov1: L.libraryStats(input, Date.parse("2026-11-01T12:00:00Z")).recent,
            });
        """, data=docs)
        self.assertEqual(r, {"oct6": 2, "sep30": 1, "nov1": 0})
        self.assertEqual(json.loads(read("src", "_i18n", "library.json"))["library.stat_new"]["en"], "new this month")

    def test_events_tile_counts_like_the_events_tab(self):
        items = [
            ev("ev:manual:2099-03-19-spring-assembly", "manual", "2099-03-19T14:00:00Z", "2099-03-21T20:00:00Z", slug="2099-03-19-spring-assembly"),
            ev("ev:recurring:citywide-dallas:2099-04-11", "recurring", "2099-04-11T22:00:00Z", "2099-04-12T01:00:00Z", series="citywide-dallas"),
            ev("ev:recurring:citywide-dallas:2099-05-09", "recurring", "2099-05-09T22:00:00Z", "2099-05-10T01:00:00Z", series="citywide-dallas"),
            ev("ev:manual:2000-02-05-old-workshop", "manual", "2000-02-05T15:00:00Z", "2000-02-05T17:00:00Z", slug="2000-02-05-old-workshop"),
            ev("ev:committee:2099-04-15", "committee", "2099-04-16T00:00:00Z", "2099-04-16T01:00:00Z"),
        ]
        r = run_js(self, "out({ en: filters.cmEventEnds({ events: { items: input } }, 'en'), none: filters.cmEventEnds({}, 'en') });", data=items)
        # the assembly once, the monthly booth once (until its last listed date is over), no past event, no meeting
        self.assertEqual(r["en"], ["2099-03-21T20:00:00.000Z", "2099-05-10T01:00:00.000Z"])
        self.assertEqual(r["none"], [])
        search, committee = read("src", "pages", "search.njk"), read("eleventy", "filters", "committee.js")
        self.assertIn("db | cmEventEnds(lang)", search)
        self.assertNotIn('where("extra.past", false)', search)
        self.assertIn("const eventEnds = upcomingEventEnds(db, L);", committee)

    def test_subscriptions_from_the_us_store(self):
        shop = {"subscriptions": [
            {"pub": "gv", "region": "ca", "plans": [{"term_months": 1, "price": 1.99}]},
            {"pub": "gv", "region": "intl", "plans": [{"term_months": 12, "price": 12.0}]},
            {"pub": "gv", "region": "us", "plans": [{"term_months": 1, "price": 2.99}, {"term_months": 12, "price": 39.0}]},
            {"pub": "lv", "region": "us", "plans": [{"term_months": 12, "price": 24.0}]},
        ]}
        r = run_js(self, """
            const S = await imp("eleventy/filters/shop.js");
            out({ all: S.shopFromMonthly(input), noUs: S.shopFromMonthly({ subscriptions: input.subscriptions.filter((s) => s.region !== "us") }),
                  yearlyUs: S.shopFromMonthly({ subscriptions: [input.subscriptions[3]] }), none: S.shopFromMonthly(null) });
        """, data=shop)
        self.assertEqual(r, {"all": 2.99, "noUs": None, "yearlyUs": 2.0, "none": None})


# --------------------------------------------------------------------------------------------- La Viña's workshop
class LaVinaWorkshopName(unittest.TestCase):
    NAME = "Taller Mensual y Virtual de La Viña"

    def test_one_name(self):
        lv = next(e for e in CFG["recurring_events"] if e["key"] == "lv-monthly-workshop")
        self.assertEqual(lv["title_es"], self.NAME)
        for f in sorted((ROOT / "config" / "presentations").glob("*.yml")):
            with self.subTest(deck=f.name):
                t = f.read_text(encoding="utf-8")
                self.assertNotRegex(t, r"(?i)taller informativo mensual|monthly information workshop")
        decks = read("config", "presentations", "information-workshop.yml")
        self.assertIn("{lang:es}" + self.NAME + "{/lang}", decks)
        orientation = json.loads(read("src", "_i18n", "orientation.json"))["orientation.pres_kind_lv_workshop"]
        self.assertEqual(orientation["es"], self.NAME)
        # an older flyer name is still found on the Drive
        self.assertRegex("taller informativo mensual de la viña", lv["flyer_match"])
        self.assertRegex(self.NAME.lower(), lv["flyer_match"])


# --------------------------------------------------------------------------------------------- the pages, built
def ev(id_: str, category: str, start: str, end: str, **extra) -> dict:
    """An event as data/site/events.json has it."""
    title = extra.pop("title", id_.split(":")[-1].replace("-", " ").title())
    return {"id": id_, "source": "committee", "kind": "event", "url": "/events/", "title": title, "summary": "",
            "lang": "en", "date": start, "first_seen": "2026-09-01T00:00:00Z", "category": category, "status": "ok",
            "extra": {"start": start, "end": end, "all_day": False, "location": extra.pop("location", ""),
                      "recurring": category == "recurring", **extra},
            "i18n": {"title": {"en": title, "es": extra.get("title_es", title)}}, "machine": []}


DRIVE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
EVENTS = [
    ev("ev:manual:2099-03-19-spring-assembly", "manual", "2099-03-19T14:00:00Z", "2099-03-21T20:00:00Z",
       slug="2099-03-19-spring-assembly", title="Spring Assembly", location="Tyler Convention Center, Tyler, TX",
       flyer_url=f"https://drive.google.com/file/d/{DRIVE_ID}/view"),
    ev("ev:recurring:citywide-dallas:2099-04-11", "recurring", "2099-04-11T22:00:00Z", "2099-04-12T01:00:00Z", series="citywide-dallas"),
    ev("ev:recurring:citywide-dallas:2099-05-09", "recurring", "2099-05-09T22:00:00Z", "2099-05-10T01:00:00Z", series="citywide-dallas"),
    ev("ev:recurring:citywide-dallas:2000-01-08", "recurring", "2000-01-08T23:00:00Z", "2000-01-09T02:00:00Z", series="citywide-dallas"),
    ev("ev:manual:2000-02-05-old-workshop", "manual", "2000-02-05T15:00:00Z", "2000-02-05T17:00:00Z", slug="2000-02-05-old-workshop"),
    ev("ev:lvcal:svgflyer", "lv-calendar", "2099-06-01T19:00:00Z", "2099-06-01T20:00:00Z",
       flyer_url="https://www.aalavina.org/sites/default/files/flyer.svg", flyer_thumb="https://www.aalavina.org/sites/default/files/flyer.svg"),
    ev("ev:gvcal:jpgflyer", "gv-calendar", "2099-07-01T19:00:00Z", "2099-07-01T20:00:00Z",
       flyer_url="https://www.aagrapevine.org/sites/default/files/flyer.jpg", flyer_thumb="https://www.aagrapevine.org/sites/default/files/flyer.jpg"),
]

# /events/, /meetings/, /search/, /orientation/, /share/ and three test pages, as the build renders them: Eleventy with the site's own
# config (only those pages: its ONLY switch), these events, no Grapevine meetings data (as without
# data/site/meetings.json) and the committee meeting "on Google Meet" with its own note.
PAGES_JS = r"""
process.env.ONLY = "events,meetings,search,orientation.njk,share";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-site-links-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { updated: null, items: input.items }, meetings: { updated: null, items: [] } }),
        site: (data) => ({ ...data.site, meeting: { ...data.site.meeting, ...input.meeting } }),
      });
      const page = { layout: "layouts/base.njk", lang: "en", pageKey: "og-test", title: "Test", sitemap: false, eleventyExcludeFromCollections: true };
      cfg.addTemplate("og-poster.njk", "<p>poster</p>", { ...page, permalink: "/og-poster/index.html", ogImage: input.og });
      cfg.addTemplate("og-svg.njk", "<p>svg</p>", { ...page, permalink: "/og-svg/index.html", ogImage: "/assets/img/logo.svg" });
      cfg.addTemplate("og-abs.njk", "<p>abs</p>", { ...page, permalink: "/og-abs/index.html", ogImage: "https://lh3.googleusercontent.com/d/abc123def456=w1200" });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url && p.url.endsWith("/")).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def metas(html: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in re.finditer(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"', html):
        out.setdefault(m.group(1), []).append(m.group(2))
    return out


# The event share pages (src/pages/event-share.11ty.js) for these events, rendered by the template's own render()
# with the build's filters (its `this`; the path prefix "/"), and its pagination's `before` as the build calls it.
SHARE_JS = r"""
const T = await imp("src/pages/event-share.11ty.js");
const site = (await imp("src/_data/site.js")).default();
const list = T.eventSharePages(input.items, site, ["en", "es"]);
const ctx = { t: filters.t, siteUrl: filters.siteUrl, shareImage: filters.shareImage, url: (u) => u };
const html = Object.fromEntries(list.map((s) => [s.path, T.render.call(ctx, { share: s, site })]));
const twice = T.eventSharePages([input.items[0], { ...input.items[0], id: input.items[0].id + "-copy" }], site, ["en", "es"]).map((s) => s.path);
out({
  list: list.map((s) => ({ path: s.path, target: s.target })), html, twice,
  permalinks: list.map((s) => T.data.permalink({ share: s })),
  before: T.data.pagination.before(input.items, { site, languages: ["en", "es"] }).map((s) => s.path),
  data: { layout: T.data.layout, sitemap: T.data.sitemap, eleventyExcludeFromCollections: T.data.eleventyExcludeFromCollections },
});
"""


class BuiltPages(unittest.TestCase):
    pages: dict | None = None
    share_pages: dict | None = None

    def built(self) -> dict:
        if BuiltPages.pages is None:
            BuiltPages.pages = run_js(self, PAGES_JS, data={
                "items": EVENTS, "og": {"src": "/assets/img/poster.png", "width": 1080, "height": 1350, "alt": "This month's poster"},
                "meeting": {"platform": "Google Meet", "note": "Open to every AA member.", "note_es": "Abierta a todo miembro de AA."}})
        return BuiltPages.pages

    def test_share_picture_from_page_data(self):
        p = self.built()
        m = metas(p["/og-poster/"])
        self.assertEqual(m["og:image"], [SITE_URL + "/assets/img/poster.png"])
        self.assertEqual((m["og:image:width"], m["og:image:height"]), (["1080"], ["1350"]))
        self.assertEqual(m["og:image:alt"], ["This month&#39;s poster"])
        self.assertEqual((m["twitter:image"], m["twitter:image:alt"]), (m["og:image"], m["og:image:alt"]))
        # an absolute address stays as it is (no site address in front of it); no size when none is given
        m = metas(p["/og-abs/"])
        self.assertEqual(m["og:image"], ["https://lh3.googleusercontent.com/d/abc123def456=w1200"])
        self.assertNotIn("og:image:width", m)
        # not a picture the previews show: the committee's card, with its size
        for url in ("/og-svg/", "/events/"):
            m = metas(p[url])
            self.assertEqual(m["og:image"], [SITE_URL + "/assets/img/og-default.png?v=2"])
            self.assertEqual((m["og:image:width"], m["og:image:height"]), (["1200"], ["630"]))
            self.assertEqual(m["twitter:image"], m["og:image"])
        self.assertEqual(metas(p["/es/events/"])["twitter:image"], [SITE_URL + "/assets/img/og-default-es.png?v=2"])

    def test_events_page_names_its_calendar_file(self):
        p = self.built()
        for url, ics, name in (("/events/", "/events.ics", "NETA 65 Grapevine / La Viña — Events"),
                               ("/es/events/", "/es/events.ics", "NETA 65 Grapevine / La Viña — Eventos")):
            links = re.findall(r'<link rel="alternate" type="text/calendar"[^>]*>', p[url])
            self.assertEqual(len(links), 1, url)
            self.assertIn(f'href="{ics}"', links[0])
            self.assertIn(f'title="{name}"', links[0])
        self.assertNotIn("text/calendar", p["/meetings/"])

    def test_cards_share_their_page(self):
        p = self.built()
        for lang, prefix in (("en", ""), ("es", "/es")):
            html = p[f"{prefix}/events/"]
            shares = set(re.findall(r'data-share="([^"]+)"', html))
            self.assertIn(f"{SITE_URL}{prefix}/events/2099-03-19-spring-assembly/", shares)
            self.assertIn(f"{SITE_URL}{prefix}/events/ev-recurring-citywide-dallas-2099-04-11/", shares)
            self.assertFalse([s for s in shares if "#2099-03-19" in s])
            # a committee meeting's card is shared as it is
            self.assertTrue([s for s in shares if re.search(r"/events/#ev-committee-\d{4}-\d{2}-\d{2}$", s)], lang)
            # every card shares a page the share pages make (src/pages/event-share.11ty.js: the same events)
            pages = {SITE_URL + s["path"] for s in self.shares()["list"]}
            self.assertEqual({s for s in shares if "#" not in s} - pages, set())

    def shares(self) -> dict:
        if BuiltPages.share_pages is None:
            BuiltPages.share_pages = run_js(self, SHARE_JS, data={"items": EVENTS})
        return BuiltPages.share_pages

    def test_every_event_has_a_share_page(self):
        r = self.shares()
        p = r["html"]
        anchors = ["2099-03-19-spring-assembly", "ev-recurring-citywide-dallas-2099-04-11", "ev-recurring-citywide-dallas-2099-05-09",
                   "ev-recurring-citywide-dallas-2000-01-08", "2000-02-05-old-workshop", "ev-lvcal-svgflyer", "ev-gvcal-jpgflyer"]
        self.assertEqual(sorted(p), sorted([f"/events/{a}/" for a in anchors] + [f"/es/events/{a}/" for a in anchors]))
        # (no page for the committee meetings: theirs is /meetings/); the page's address and its pagination
        self.assertEqual(sorted(r["permalinks"]), sorted(u + "index.html" for u in p))
        self.assertEqual(r["before"], [s["path"] for s in r["list"]])
        html = p["/events/2099-03-19-spring-assembly/"]
        m = metas(html)
        self.assertEqual(m["og:title"], ["Spring Assembly"])
        self.assertEqual(m["og:url"], [SITE_URL + "/events/2099-03-19-spring-assembly/"])
        self.assertIn(f'<link rel="canonical" href="{SITE_URL}/events/2099-03-19-spring-assembly/">', html)
        self.assertEqual(m["og:image"], [f"https://lh3.googleusercontent.com/d/{DRIVE_ID}=w1200"])
        self.assertEqual(m["twitter:image"], m["og:image"])
        self.assertEqual(m["og:image:alt"], ["Flyer: Spring Assembly"])
        self.assertIn("Tyler Convention Center", m["og:description"][0])
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertNotIn("http-equiv", html)                  # no meta refresh: the previews must stay on this page
        # (a ?query the link came with goes before the #card)
        self.assertIn('location.replace("/events/" + location.search + "#2099-03-19-spring-assembly")', html)
        self.assertIn('<a href="/events/#2099-03-19-spring-assembly">See this event on our Events page →</a>', html)
        es = p["/es/events/2099-03-19-spring-assembly/"]
        self.assertIn('<html lang="es">', es)
        self.assertIn('location.replace("/es/events/" + location.search + "#2099-03-19-spring-assembly")', es)
        self.assertEqual(metas(es)["og:locale"], ["es_US"])
        self.assertEqual(metas(es)["og:image:alt"], ["Volante: Spring Assembly"])
        # a monthly date that has passed has no row any more: the top of the page; a past one-off event keeps its row
        self.assertIn('location.replace("/events/" + location.search)', p["/events/ev-recurring-citywide-dallas-2000-01-08/"])
        self.assertIn('location.replace("/events/" + location.search + "#2000-02-05-old-workshop")', p["/events/2000-02-05-old-workshop/"])
        # a flyer that is not a picture the previews show (an SVG): the committee's card; a JPEG: itself
        self.assertEqual(metas(p["/events/ev-lvcal-svgflyer/"])["og:image"], [SITE_URL + "/assets/img/og-default.png?v=2"])
        self.assertEqual(metas(p["/events/ev-gvcal-jpgflyer/"])["og:image"], ["https://www.aagrapevine.org/sites/default/files/flyer.jpg"])
        # the share pages are no pages of their own for search engines, the sitemap or page lists
        self.assertEqual(r["data"], {"layout": False, "sitemap": False, "eleventyExcludeFromCollections": True})
        # an anchor met twice keeps one page (never two pages at one address)
        self.assertEqual(r["twice"], ["/events/2099-03-19-spring-assembly/", "/es/events/2099-03-19-spring-assembly/"])

    def test_search_events_tile_counts_like_the_events_tab(self):
        p = self.built()
        for prefix, word in (("", "items"), ("/es", "elementos")):
            tab = re.search(r'href="' + prefix + r'/events/" class="cm-subnav-link[^"]*"[^>]*>.*?<span class="cm-subnav-count"[^>]*>(\d+)<', p[f"{prefix}/events/"], re.S)
            n = int(tab.group(1))
            self.assertEqual(n, 4)            # the assembly, the monthly booth once and the two calendar events
            tile = re.search(r'<a href="' + prefix + r'/events/" data-tone="vine">.*?<span class="ss-b-n"([^>]*)>([^<]*)<', p[f"{prefix}/search/"], re.S)
            self.assertEqual(tile.group(2).strip(), f"{n} {word}")
            ends = re.search(r'data-gv-expire-count="([^"]+)"', tile.group(1)).group(1).split()
            self.assertEqual(len(ends), n)
            self.assertIn('data-gv-expire-n="{n} ' + word + '"', tile.group(1))

    def test_meetings_page_without_its_data_and_on_another_platform(self):
        p = self.built()
        for prefix, lang in (("", "en"), ("/es", "es")):
            html = p[f"{prefix}/meetings/"]
            empty = html[html.index('class="empty-state"'):]
            empty = empty[:empty.index("</ul>")]
            for f in CFG["meetings"]["feeds"]:
                with self.subTest(lang=lang, office=f["id"]):
                    self.assertRegex(empty, re.compile(r'href="' + re.escape(f["site"]) + r'"[^>]*>(?:(?!</a>).)*'
                                                       + re.escape(f["name"].replace("&", "&amp;")) + "</a>", re.S))
            self.assertNotIn("{platform}", html)
        en, es = p["/meetings/"], p["/es/meetings/"]
        for s in ("Join on Google Meet", "The committee · Monthly on Google Meet", "Central time, on Google Meet.",
                  "Copy Google Meet link", "no Google Meet account needed", "Open to every AA member. GVRs, RLVs, DCMs"):
            self.assertIn(s, en)
        self.assertRegex(en, r'<meta name="description" content="Our committee&#39;s monthly Google Meet meeting')
        for s in ("Entrar por Google Meet", "El comité · Cada mes por Google Meet", "Abierta a todo miembro de AA. Los RLV, GVR"):
            self.assertIn(s, es)
        # the weekly open meetings are Grapevine's and La Viña's own, on Zoom
        self.assertIn("Join on Zoom", en)
        ev_en = p["/events/"]
        self.assertIn("Join on Google Meet", ev_en)
        self.assertIn("the committee meeting (with its Google Meet link)", ev_en)       # where events come from
        self.assertIn("la reunión del comité (con su enlace de Google Meet)", p["/es/events/"])
        self.assertNotIn("{platform}", ev_en + p["/es/events/"])
        # the orientation deck's closing slide and the share kit's announcement name it too
        for url, s in (("/orientation/", " · Google Meet</span>"), ("/es/orientation/", " · Google Meet</span>"),
                       ("/share/", "Our committee meets monthly on Google Meet"),
                       ("/es/share/", "Nuestro comité se reúne cada mes por Google Meet")):
            with self.subTest(page=url):
                self.assertIn(s, p[url])
                self.assertNotIn("{platform}", p[url])
        self.assertNotIn(" · Zoom</span>", p["/orientation/"])


# The 404 page's script (src/assets/js/community.js) on a pretend page: GitHub Pages shows it for every missing
# address, so a shared event's page whose event has since left data/site/events.json lands there.
NOT_FOUND_JS = r"""
import vm from "node:vm";
const run = (pathname, search = "") => {
  const replaced = [], box = { value: "" }, nf = { getAttribute: () => null };
  const document = {
    readyState: "complete", addEventListener() {},
    querySelector: (s) => (s === "[data-nf]" ? nf : null),
    querySelectorAll: (s) => (s === "[data-nf-query]" ? [box] : []),
  };
  const ctx = { console, document, GV: {}, SITE: { lang: "en", base: "/aagrapevine/", tz: "America/Chicago" },
                location: { pathname, search, hash: "", replace: (u) => replaced.push(u) } };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/community.js", "utf8"), ctx, { filename: "community.js" });
  return { replaced, query: box.value };
};
out({
  en: run("/aagrapevine/events/2026-10-07-lv-writing-workshop-mansfield/", "?utm_source=x"),
  es: run("/aagrapevine/es/events/ev-recurring-citywide-dallas-2026-07-11/"),
  noSlash: run("/aagrapevine/events/2026-10-07-lv-writing-workshop-mansfield"),
  deeper: run("/aagrapevine/events/2026/old-page/"),
  other: run("/aagrapevine/library/sponsorship-flyer.pdf"),
});
"""


class GoneEventSharePage(unittest.TestCase):
    def test_a_gone_share_page_leads_on_to_the_events_page(self):
        r = run_js(self, NOT_FOUND_JS, needs_modules=False)
        self.assertEqual(r["en"]["replaced"], ["/aagrapevine/events/?utm_source=x#2026-10-07-lv-writing-workshop-mansfield"])
        self.assertEqual(r["es"]["replaced"], ["/aagrapevine/es/events/#ev-recurring-citywide-dallas-2026-07-11"])
        self.assertEqual(r["noSlash"]["replaced"], ["/aagrapevine/events/#2026-10-07-lv-writing-workshop-mansfield"])
        # any other missing address keeps the 404 page and its search box
        self.assertEqual((r["deeper"]["replaced"], r["other"]["replaced"]), ([], []))
        self.assertEqual(r["other"]["query"], "library sponsorship flyer")


if __name__ == "__main__":
    unittest.main()
