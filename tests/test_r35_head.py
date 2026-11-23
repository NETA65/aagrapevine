"""Round 35 · what search engines and AI tools read first about the site (the owner's "best SEO results for all major
search engines and major AI platforms"; the head of every page, the share card, robots.txt, llms.txt) — offline:

  * SaysAA      — the home page's title says "AA committee, Northeast Texas Area 65" (Grapevine is also a city in the
                  same part of Texas; "La Viña" means "the vineyard"), about 60 characters at most; the home and
                  About descriptions and the footer's words (the committee's description for search engines) say
                  Alcoholics Anonymous, in both languages — and never that this is the magazines' official site.
  * SiteName    — the site's name in the structured data, "<site.title> — NETA 65", is the installed app's name too
                  (src/pages/manifest.11ty.js); tests/test_seo_head.py checks it against the home page's og:site_name.
  * ShareCard   — og-default.png / og-default-es.png: 1200 × 630 truecolor PNG pictures, 300 KB at most (the size
                  WhatsApp is often said to skip above), asked for as ?v=3 (base.njk) — the cards say
                  grapevine.neta65.org now.
  * PageWeight  — eleventy/seo-check.js: a page the sitemap lists that is over 1.8 MB of HTML, counted in UTF-8 bytes,
                  is an [seo] problem (Googlebot reads the first 2 MB only), and so is a page whose structured data
                  — any block of it: the head's graph or a block in the <body> — ends past 1.5 MB; a smaller page,
                  or one whose structured data all comes early, is not.
  * LcpImage    — the built pages: only /listen/ and /watch/ (both languages) ask for their largest picture early —
                  the YouTube poster the page shows (its very address) —, from the first head script, inside the Data
                  saver guard (run in Node: with Data saver on, no picture is asked for); an lcpImage that is not an
                  https://i.ytimg.com/ address (or holds a quote) is left out.
                  (The build gets settings of its own for what these judge — /listen/'s Short, the committee meeting,
                  the monthly series —, so the committee's edits of config/site.yml never fail them: the gate's rule,
                  scripts/ops/gate_tests.py, tests/test_automation.py GateLists.)
  * LlmsTxt     — /llms.txt and /es/llms.txt: "# <the site's name>", a "> " summary of who runs the site (the
                  committee, Alcoholics Anonymous, Northeast Texas Area 65; not AA Grapevine, Inc.'s or A.A.W.S.'s
                  site; the magazines' and the Area's own addresses, the contact e-mail), the monthly meetings as
                  rules only (ours, online, read like the pages read them: "7:00 PM" counts), "## " lists of the
                  menu's pages and (since round 37) of the events still to come — every link absolute on the site, to
                  a page this build made (the events' own pages are among the build's: ONLY's event-share), with that
                  page's own meta description — and the other language's file last; no way to join
                  an online meeting (no link, meeting ID or code, passcode), no guest speaker's name (outside the
                  events' own lines: the day's events in their own words, which tests/test_r37_links.py checks on
                  made-up events), under 16 KB, plain text; kept out of the sitemap.

    python -m unittest tests.test_r35_head -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import struct
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

CFG = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
SITE = CFG["site"]
SITE_URL = SITE["url"].rstrip("/")
I18N = {k: v for f in sorted((ROOT / "src" / "_i18n").glob("*.json"))
        for k, v in json.loads(f.read_text(encoding="utf-8")).items()}
SITE_NAME = SITE["title"] + " — NETA 65"


def t(key: str, lang: str) -> str:
    return I18N[key][lang]


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------------------- words
class SaysAA(unittest.TestCase):
    def test_the_home_title_says_what_the_site_is(self):
        for lang, aa in (("en", "AA committee"), ("es", "Comité de AA")):
            title = f"Grapevine / La Viña — {t('site.home_title_tail', lang)}"     # (the title as delivered)
            with self.subTest(lang=lang, title=title):
                self.assertIn(aa, title)
                self.assertIn("Northeast Texas Area 65" if lang == "en" else "Área 65 del Noreste de Texas", title)
                self.assertLessEqual(len(title), 60 if lang == "en" else 65, "about what a result shows of a title")
        self.assertIn('("site.home_title_tail" | t(L))', read("src", "_includes", "layouts", "base.njk"))

    def test_the_descriptions_and_the_committees_words_say_alcoholics_anonymous(self):
        for key in ("home.meta_desc", "read.about.meta_desc", "footer.about"):
            for lang, name in (("en", "Alcoholics Anonymous"), ("es", "Alcohólicos Anónimos")):
                text = t(key, lang)
                with self.subTest(key=key, lang=lang):
                    self.assertIn(name, text)
                    # plain facts: never "the official site", never a superlative
                    self.assertNotRegex(text.lower(), r"\boficial|\bofficial|\bbest\b|\bmejor")
                    if key != "footer.about":
                        self.assertLessEqual(len(text), 160)
        # the magazines by their names, as the committee shares them
        self.assertIn("AA Grapevine and La Viña", t("home.meta_desc", "en"))
        self.assertIn("La Viña y AA Grapevine", t("home.meta_desc", "es"))


class SiteName(unittest.TestCase):
    def test_one_name_for_the_site(self):
        base = read("src", "_includes", "layouts", "base.njk")
        self.assertIn('{%- set ldSiteName = site.title + " — NETA 65" -%}', base)
        self.assertIn('<meta property="og:site_name" content="{{ siteTitle }} — NETA 65">', base)
        # (the installed app's name says the same: tests/test_pwa.py pins it)


# ------------------------------------------------------------------------------------------------- share card
class ShareCard(unittest.TestCase):
    def test_the_cards(self):
        for name in ("og-default.png", "og-default-es.png"):
            data = (ROOT / "src" / "assets" / "img" / name).read_bytes()
            with self.subTest(name=name):
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(data[12:16], b"IHDR")
                self.assertEqual(struct.unpack(">II", data[16:24]), (1200, 630))
                self.assertLessEqual(len(data), 300 * 1024)
                # 8-bit truecolor, never a 256-colour palette: the gradient then speckles beside the grapes (round 35
                # tried it); a stronger lossless compression (zopfli) keeps it under 300 KB
                self.assertEqual((data[24], data[25]), (8, 2), "bit depth 8, colour type 2 (RGB)")

    def test_a_new_address_for_the_new_cards(self):
        base = read("src", "_includes", "layouts", "base.njk")
        self.assertIn("'/assets/img/og-default-es.png?v=3' if L == 'es' else '/assets/img/og-default.png?v=3'", base)
        self.assertNotRegex(base, r"og-default(?:-es)?\.png\?v=[0-24-9]")


# ------------------------------------------------------------------------------------------------ page weight
BASE = "https://x.test/site"


def page(body: str = "<p>x</p>", head_extra: str = "", path: str = "/") -> str:
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>T{path}</title>'
            f'<meta name="description" content="D"><link rel="canonical" href="{BASE}{path}">{head_extra}</head>'
            f"<body><main>{body}</main></body></html>")


LD = '<script type="application/ld+json">{"@context":"https://schema.org"}</script>'


class PageWeight(unittest.TestCase):
    def problems(self, pages: dict[str, str]) -> list[str]:
        sm = "<urlset>" + "".join(f"<url><loc>{BASE}{u}</loc></url>" for u in pages) + "</urlset>"
        results = [{"url": "/sitemap.xml", "outputPath": "_site/sitemap.xml", "content": sm}]
        results += [{"url": u, "outputPath": f"_site{u}index.html", "content": h} for u, h in pages.items()]
        return run_js(self, r"""
          const C = await imp("eleventy/seo-check.js");
          out({ problems: C.seoProblems(input.results, input.base), limits: [C.PAGE_LIMIT, C.LD_LIMIT] });""",
                      data={"results": results, "base": BASE})

    def test_a_page_near_googlebots_limit_is_a_problem(self):
        mb = 1024 * 1024
        big_ld = '<script type="application/ld+json">{"x":"' + "y" * 10_000 + '"}</script>'      # a 10 KB block
        just = 1887437 + 1 - len(page("", LD, "/just/").encode("utf-8"))                       # 1 byte too many
        r = self.problems({
            "/": page(),                                                            # small
            "/fine/": page("x" * (int(1.8 * mb) - 400), LD, "/fine/"),              # just under 1.8 MB
            "/just/": page("x" * just, LD, "/just/"),                               # 1,887,438 bytes: just over
            "/big/": page("x" * int(1.85 * mb), LD, "/big/"),                       # 1.85 MB: too big
            "/accents/": page("ñ" * int(0.95 * mb), LD, "/accents/"),             # 0.95 M characters, 1.9 MB of UTF-8
            "/late/": page("x" * int(1.6 * mb) + LD, path="/late/"),                # its structured data at 1.6 MB
            # the site's graph in <head>, and a page's own block late in its <body> (the Events, drifted down)
            "/late-body/": page("x" * int(1.6 * mb) + LD, LD, "/late-body/"),
            # a block that starts before 1.5 MB but ends after it
            "/across/": page("x" * (1572864 - 5000) + big_ld, LD, "/across/"),
            # the same size, the graph in <head> and the page's own block first in its <body> (as /events/ has them)
            "/early/": page(LD + "x" * int(1.6 * mb), LD, "/early/"),
            "/none/": page("x" * int(1.6 * mb), path="/none/"),                     # no structured data at all
        })
        self.assertEqual(r["limits"], [1887437, 1572864])
        probs = r["problems"]
        self.assertEqual(len(probs), 6, probs)
        self.assertEqual(probs[0], "/just/ is 1.8 MB of HTML (1,887,438 bytes), over the 1.8 MB limit — Googlebot reads "
                                   "only the first 2 MB of a page")
        self.assertRegex(probs[1], r"^/big/ is 1\.9 MB of HTML \(1,9\d\d,\d{3} bytes\), over the 1\.8 MB limit — Googlebot "
                                   r"reads only the first 2 MB of a page$")
        self.assertRegex(probs[2], r"^/accents/ is 1\.9 MB of HTML \(1,99\d,\d{3} bytes\)")      # bytes, not characters
        for n, path in ((3, "/late/"), (4, "/late-body/")):
            self.assertRegex(probs[n], "^" + path + r": its structured data \(ld\+json\) ends at 1\.6 MB \(byte 1,67\d,\d{3}\) "
                                       r"— keep all of it within the first 1\.5 MB")
        self.assertRegex(probs[5], r"^/across/: its structured data \(ld\+json\) ends at 1\.5 MB \(byte 1,57\d,\d{3}\)")

    def test_the_real_site_puts_its_structured_data_first(self):
        # (the built pages themselves: LcpImage's build — every page's first ld+json block is in its <head>)
        pages = LcpImage.built(self)
        listed = [u for u in pages if u.endswith("/") and '<script type="application/ld+json">' in pages[u]]
        self.assertGreater(len(listed), 20)
        for u in listed:
            with self.subTest(url=u):
                self.assertLess(pages[u].index('<script type="application/ld+json">'), pages[u].index("</head>"))


# ---------------------------------------------------------------------------- built pages (one Eleventy build)
# The menu's pages (src/_data/nav.js) and the home page, llms.txt and the sitemap — by the start of their file names
# (eleventy.config.js ONLY) — and three test pages with an lcpImage of their own. The settings these tests judge are
# the test's own (input): /listen/'s Short, the committee meeting's rule (its other settings stay the real ones) and
# the monthly series — so an edit of config/site.yml never fails them.
ONLY = ("index,whats-new,read.,listen,watch,library.,shop,gvr.,orientation.,monthly.,digest,contribute,published.,"
        "meetings.,events.njk,portfolio,photos,bulletin,tracker,instagram,share.,about,accessibility,offline,search.,"
        "status,llms,sitemap,event-share")
# (event-share: the events' own pages — since round 37 /llms.txt lists the ones still to come, "## Upcoming events")
PAGES_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r35-head-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        site: (data) => ({ ...data.site, listen: input.listen, meeting: { ...(data.site.meeting || {}), ...input.meeting },
                           recurring_events: input.recurring }),
      });
      const page = { layout: "layouts/base.njk", lang: "en", pageKey: "lcp-test", sitemap: false, eleventyExcludeFromCollections: true };
      cfg.addTemplate("lcp-good.njk", "<p>good</p>", { ...page, title: "Good", permalink: "/lcp-good/index.html", lcpImage: "https://i.ytimg.com/vi/abcDEF_-123/hqdefault.jpg" });
      cfg.addTemplate("lcp-other.njk", "<p>other</p>", { ...page, title: "Other", permalink: "/lcp-other/index.html", lcpImage: "https://example.org/vi/abc/hqdefault.jpg" });
      cfg.addTemplate("lcp-quote.njk", "<p>quote</p>", { ...page, title: "Quote", permalink: "/lcp-quote/index.html", lcpImage: 'https://i.ytimg.com/vi/a"+alert(1)+"/x.jpg' });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
LISTEN = {"sidebar_short": "zzShort-123", "sidebar_short_title": "A Short"}
MEETING = {"week_of_month": 3, "weekday": "wednesday", "start": "7:00 PM", "end": "20:00", "platform": "Google Meet",
           "online_url": "https://meet.google.com/zzz-yyyy-xxx", "meeting_id": "zzz-yyyy-xxx", "passcode": "grape2099"}
RECURRING = [
    # ours and online: listed (with its first date, still to come)
    {"key": "zz-ours-online", "title": "Our Online Meeting", "title_es": "Nuestra reunión en línea", "week_of_month": 1,
     "weekday": "tuesday", "start": "18:30", "end": "19:30", "starts": "2099-01-06",
     "online_url": "https://us02web.zoom.us/j/12345678901?pwd=abc", "meeting_id": "123 4567 8901"},
    # La Viña's (host lv), ours at a place, one switched off: never listed
    {"key": "zz-lv-online", "title": "La Viña Workshop", "host": "lv", "week_of_month": 2, "weekday": "thursday",
     "start": "19:00", "end": "20:00", "online_url": "https://meet.google.com/aaa-bbbb-ccc"},
    {"key": "zz-booth", "title": "Our Booth", "week_of_month": 2, "weekday": "saturday", "start": "17:30", "end": "19:30",
     "location": "Hall, 1 Main St, Dallas, TX 75201"},
    {"key": "zz-off", "title": "Paused Meeting", "enabled": False, "week_of_month": 4, "weekday": "monday",
     "start": "19:00", "online_url": "https://meet.google.com/ddd-eeee-fff"},
]
PRELOAD = re.compile(r'var i = document\.createElement\("link"\);\s*i\.rel = "preload"; i\.as = "image"; '
                     r'i\.href = "([^"]*)"; i\.fetchPriority = "high";\s*document\.head\.appendChild\(i\);')
GUARD = 'if (d.getAttribute("data-saver") !== "on") {'


def head_script(page: str) -> str:
    head = page.split("</head>")[0]
    return head[head.index("<script>") + len("<script>"):head.index("</script>")]


class LcpImage(unittest.TestCase):
    _pages: dict | None = None

    @staticmethod
    def built(case: unittest.TestCase) -> dict:
        if LcpImage._pages is None:
            LcpImage._pages = run_js(case, PAGES_JS, data={"only": ONLY, "listen": LISTEN, "meeting": MEETING,
                                                           "recurring": RECURRING}, timeout=900)
        return LcpImage._pages

    def test_only_listen_and_watch_ask_for_their_poster_early(self):
        pages = self.built(self)
        html_pages = {u: p for u, p in pages.items() if u.endswith("/")}
        self.assertGreater(len(html_pages), 40)
        found = {u: PRELOAD.search(head_script(p)) for u, p in html_pages.items()}
        # /watch/ when it shows a latest video (the day's data: data/site/videos.json)
        watch = {u for u in ("/watch/", "/es/watch/") if 'class="media-lyt' in html_pages[u]}
        self.assertEqual({u for u, m in found.items() if m}, {"/listen/", "/es/listen/", "/lcp-good/"} | watch)
        self.assertEqual(found["/listen/"].group(1), "https://i.ytimg.com/vi/zzShort-123/hqdefault.jpg")
        for u in ("/listen/", "/es/listen/", *sorted(watch)):
            p, src = html_pages[u], found[u].group(1)
            with self.subTest(url=u):
                self.assertRegex(src, r"^https://i\.ytimg\.com/vi/[\w-]+/hqdefault\.jpg$")
                # the very poster the page shows: the hero's Short on /listen/, the latest video on /watch/
                cls = "hero-aside-lyt" if "listen" in u else "media-lyt"
                lyt = re.search(r'<lite-youtube videoid="[^"]+" class="' + cls + r'[^"]*"[^>]*style="background-image: url\(\'([^\']+)\'\);"', p)
                self.assertIsNotNone(lyt, cls)
                self.assertEqual(lyt.group(1), src)
                # inside the Data saver guard of the first head script (and nowhere else)
                script = head_script(p)
                self.assertLess(script.index(GUARD), script.index('i.as = "image"'))
                self.assertEqual(p.count('as = "image"'), 1)
        self.assertEqual(found["/lcp-good/"].group(1), "https://i.ytimg.com/vi/abcDEF_-123/hqdefault.jpg")

    def test_another_address_is_never_written(self):
        pages = self.built(self)
        for u in ("/lcp-other/", "/lcp-quote/"):
            with self.subTest(url=u):
                self.assertNotIn('as = "image"', pages[u])
                self.assertNotIn("example.org/vi", pages[u])
                self.assertNotIn("alert(1)", pages[u])

    def test_with_data_saver_on_no_picture_is_asked_for(self):
        script = head_script(self.built(self)["/listen/"])
        res = run_js(self, r"""
const made = [];
const run = (prefs, conn) => {
  const attrs = {}, cls = new Set();
  const d = { setAttribute: (k, v) => { attrs[k] = String(v); }, getAttribute: (k) => (k in attrs ? attrs[k] : null),
              classList: { add: (c) => cls.add(c), contains: (c) => cls.has(c) } };
  const links = [];
  const document = { documentElement: d, head: { appendChild: (l) => links.push(l) }, createElement: () => ({}) };
  const navigator = { connection: conn || {}, onLine: true };
  const localStorage = { getItem: () => (prefs ? JSON.stringify(prefs) : null) };
  new Function("document", "navigator", "localStorage", input.js)(document, navigator, localStorage);
  return { saver: attrs["data-saver"], images: links.filter((l) => l.as === "image").map((l) => [l.href, l.fetchPriority]),
           fonts: links.filter((l) => l.as === "font").length };
};
out({ off: run(null), on: run({ saver: "on" }), auto: run(null, { saveData: true }), slow: run(null, { effectiveType: "2g" }),
      chosenOff: run({ saver: "off" }, { saveData: true }) });
""", data={"js": script}, needs_modules=False)
        poster = PRELOAD.search(script).group(1)
        self.assertEqual(res["off"], {"saver": "off", "images": [[poster, "high"]], "fonts": 1})
        self.assertEqual(res["chosenOff"]["images"], [[poster, "high"]], "Data saver turned off by the visitor")
        for case in ("on", "auto", "slow"):
            with self.subTest(saver=case):
                self.assertEqual(res[case], {"saver": "on", "images": [], "fonts": 0})

    def test_the_value_comes_through_the_pages_data(self):
        for name in ("listen.njk", "watch.njk"):
            fm = yaml.safe_load(re.match(r"---\n(.*?)\n---\n", read("src", "pages", name), re.S).group(1))
            with self.subTest(page=name):
                self.assertIn("lcpImage", fm["eleventyComputed"], "the layout reads it: a set in the page never reaches it")
                self.assertIn("ytThumb", fm["eleventyComputed"]["lcpImage"])


# --------------------------------------------------------------------------------------------------- llms.txt
JOIN = re.compile(r"meet\.google\.com|zoom\.us|teams\.microsoft|\bpwd=|\bmeeting\s*(?:id|code)s?\b|\bzoom\s*id\b|"
                  r"pass\s*code|password|contrase[ñn]a|c[oó]digo de (?:la )?reuni[oó]n|c[oó]digo de acceso|"
                  r"id de (?:la )?reuni[oó]n|\b\d{3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b|\b[a-z]{3}-[a-z]{4}-[a-z]{3}\b", re.I)
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
UPCOMING = {"en": "## Upcoming events", "es": "## Próximos eventos"}


def without_upcoming(text: str, lang: str) -> str:
    """The guide without its "## Upcoming events" list (since round 37: the day's events, up to the next "## ")."""
    lines = text.split("\n")
    if UPCOMING[lang] not in lines:
        return text
    start = lines.index(UPCOMING[lang])
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    return "\n".join(lines[:start] + lines[end:])


class LlmsTxt(unittest.TestCase):
    def files(self) -> dict[str, str]:
        pages = LcpImage.built(self)
        self.assertIn("/llms.txt", pages)
        self.assertIn("/es/llms.txt", pages)
        return {"en": pages["/llms.txt"], "es": pages["/es/llms.txt"]}

    def test_the_layout(self):
        for lang, text in self.files().items():
            lines = text.split("\n")
            with self.subTest(lang=lang):
                self.assertEqual(lines[0], "# " + SITE_NAME, "the site's name, as the structured data gives it")
                self.assertEqual(lines[1], "")
                self.assertTrue(lines[2].startswith("> "))
                self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
                self.assertNotIn("\r", text)
                self.assertNotRegex(text, r"<[a-zA-Z/!]", "plain text, never HTML")
                self.assertLess(len(text.encode("utf-8")), 16 * 1024)
                h2 = [ln[3:] for ln in lines if ln.startswith("## ")]
                self.assertEqual(h2[1:3], [t("nav.get_involved", lang), t("nav.committee", lang)])
                self.assertEqual(h2[-1], "Optional" if lang == "en" else "Opcional")
                # the other language's file, last
                other = f"{SITE_URL}/es/llms.txt" if lang == "en" else f"{SITE_URL}/llms.txt"
                self.assertEqual(LINK.findall(lines[-2])[0][1], other)

    def test_who_runs_the_site(self):
        for lang, text in self.files().items():
            quote = text.split("\n")[2]
            with self.subTest(lang=lang):
                committee = (SITE.get("committee_es") if lang == "es" else None) or SITE.get("committee")
                area = (SITE.get("area_es") if lang == "es" else None) or SITE.get("area")
                for words in ((committee, "Alcoholics Anonymous", area, "not the official site")
                              if lang == "en" else (committee, "Alcohólicos Anónimos", area, "No es el sitio oficial")):
                    self.assertIn(words, quote)
                self.assertIn("AA Grapevine, Inc.", quote)
                self.assertIn("A.A.W.S.", quote)
                if SITE.get("contact_email"):
                    self.assertIn(SITE["contact_email"], quote)
                links = CFG.get("links") or {}
                want = [links.get("gv_home") or "https://www.aagrapevine.org", links.get("lv_home") or "https://www.aalavina.org"]
                if SITE.get("area_website"):
                    want.append(SITE["area_website"])
                self.assertEqual(sorted(u for _l, u in LINK.findall(quote)), sorted(want))

    def test_every_page_link_is_a_page_of_this_build_with_its_own_description(self):
        pages = LcpImage.built(self)
        for lang, text in self.files().items():
            body = text.split("\n", 3)[3]
            links = [(m.group(1), m.group(2), ln) for ln in body.split("\n") for m in [LINK.search(ln)] if m]
            self.assertGreater(len(links), 20)
            with self.subTest(lang=lang):
                for label, url, line in links:
                    self.assertTrue(url.startswith(SITE_URL + "/"), url)
                    path = url[len(SITE_URL):]
                    self.assertIn(path, pages, "a page or file this build made")
                    if path.endswith("/"):
                        desc = re.search(r'<meta name="description" content="([^"]*)">', pages[path]).group(1)
                        self.assertEqual(line, f"- [{label}]({url}): {html.unescape(desc)}")
                        self.assertNotIn('content="noindex"', pages[path])
                # the menu's pages, the home page first; never a page kept out of search (the Update status page)
                paths = [u[len(SITE_URL):] for _l, u, _ln in links]
                home = "/es/" if lang == "es" else "/"
                self.assertEqual(paths[0], home)
                for p in ("whats-new/", "listen/", "watch/", "gvr/", "meetings/", "events/", "about/"):
                    self.assertIn(home + p, paths)
                self.assertNotIn(home + "status/", paths)
                self.assertEqual(len(paths), len(set(paths)))

    def test_the_monthly_meetings_are_rules_only(self):
        # the test's settings (MEETING, RECURRING): the committee meeting ("7:00 PM": read as the pages read it) and
        # our online series with its first date still to come — never La Viña's, a place's or one switched off
        want = {
            "en": ["- Committee meeting: every third Wednesday of the month · 7:00 – 8:00 PM Central time, online "
                   "(Google Meet).",
                   "- Our Online Meeting: every first Tuesday of the month · 6:30 – 7:30 PM Central time, online (Zoom), "
                   "first meeting January 6, 2099."],
            "es": ["- Reunión del comité: cada tercer miércoles del mes · 7:00–8:00 p. m., hora del Centro, en línea "
                   "(Google Meet).",
                   "- Nuestra reunión en línea: cada primer martes del mes · 6:30–7:30 p. m., hora del Centro, en línea "
                   "(Zoom), primera reunión el 6 de enero de 2099."],
        }
        for lang, text in self.files().items():
            lines = [re.sub(r"[\u2009\u202f\xa0]", " ", ln) for ln in text.split("\n")
                     if ln.startswith("- ") and "](" not in ln]
            with self.subTest(lang=lang):
                self.assertEqual(lines, want[lang])
                self.assertNotIn("La Viña Workshop", text)
                self.assertNotIn("Our Booth", text)
                self.assertNotIn("Paused", text)

    def test_no_way_to_join_and_no_names(self):
        meeting = CFG.get("meeting") or {}
        speakers = [s["name"] for s in meeting.get("speakers") or [] if isinstance(s, dict) and s.get("name")]
        codes = [MEETING["meeting_id"], MEETING["passcode"], "pwd=abc", "12345678901", "aaa-bbbb-ccc", "ddd-eeee-fff",
                 *[r.get("meeting_id") for r in RECURRING], meeting.get("meeting_id"), meeting.get("passcode")]
        # (not "## Upcoming events" — since round 37 the day's events, in their own words: the publish gate judges the
        # code, never the synced data — tests/test_r37_links.py LlmsTxt checks those lines on made-up events that give
        # a meeting ID and link, with this JOIN)
        for lang, text in ((lang, without_upcoming(text, lang)) for lang, text in self.files().items()):
            with self.subTest(lang=lang):
                self.assertIsNone(JOIN.search(text), JOIN.search(text) and JOIN.search(text).group(0))
                for code in filter(None, codes):
                    self.assertNotIn(str(code), text)
                for name in speakers:
                    self.assertNotIn(name, text)

    def test_kept_out_of_the_lists(self):
        pages = LcpImage.built(self)
        self.assertNotIn("llms", pages["/sitemap.xml"])
        src = read("src", "pages", "llms-txt.11ty.js")
        self.assertRegex(src, r"eleventyExcludeFromCollections:\s*true")
        self.assertRegex(src, r"layout:\s*false")
        self.assertIn("neither harm nor help", src, "the honest note")


if __name__ == "__main__":
    unittest.main()
