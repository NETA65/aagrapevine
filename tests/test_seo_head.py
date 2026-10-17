"""What search engines read in every page's <head> and at the end of its <body> (src/_includes/layouts/base.njk), and
the files around it — as the build renders them:

  * robots      — a page search engines may show says "max-image-preview:large, max-snippet:-1, max-video-preview:-1"
                  (never "noindex", never "index, follow": the default); a page with `noindex: true` in its front
                  matter (the Update status page) says "noindex", keeps its canonical, has no hreflang links, no
                  structured data, and is not in the sitemap; the 404 page stays as it was;
  * previews    — twitter:title / twitter:description are og:title / og:description (the tab title and the meta
                  description); og:image:type when the picture's file name says it (the committee's card: PNG) —
                  the shareImage filter;
  * titles      — a GVR / RLV 101 session: "<session> · GVR / RLV 101 — NETA 65" (its `titleTail`); every other
                  page keeps "<page> · <site title> — NETA 65";
  * verification — the Bing / Yandex codes of config/site.yml site.search_engines are on the home page (both
                  languages) only, and only when filled in;
  * OpenSearch  — /opensearch.xml and /es/opensearch.xml (src/pages/opensearch.11ty.js) are valid descriptions whose
                  search address is the page language's /search/?q={searchTerms}, named in every page's <head>;
  * structured data — ONE schema.org graph at the end of each indexable page's <body>, after the page's own block:
                  the same Organization (the committee, from config/site.yml — never the magazines' accounts) and
                  WebSite on every page in both languages, a WebPage of the page's own type, a BreadcrumbList
                  (Home → the menu page above it → the page, in the page language) and, on /contribute/, a FAQPage
                  with exactly the questions and answers the page shows.

The expectations come from config/site.yml and src/_i18n (the committee may reword its name or e-mail: GateLists).

    python -m unittest tests.test_seo_head -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


CFG = yaml.safe_load(read("config", "site.yml"))
SITE = CFG["site"]
SITE_URL = SITE["url"].rstrip("/")
ROOT_URL = SITE_URL + "/"
I18N = {k: v for f in sorted((ROOT / "src" / "_i18n").glob("*.json")) for k, v in json.loads(f.read_text(encoding="utf-8")).items()}
MAX_ROBOTS = "max-image-preview:large, max-snippet:-1, max-video-preview:-1"
FAKE_BING = "0123456789ABCDEF0123456789ABCDEF"


def t(key: str, lang: str) -> str:
    return I18N[key][lang]


# The pages that show each case, as the build renders them: Eleventy with the site's own config and data, only
# these templates (its ONLY switch: the home page, About, Share your story, GVR / RLV 101 and its sessions, the
# Monthly toolkit and its months, Search, Events, Read, Update status, the 404 page, the sitemap and the OpenSearch
# files), a Bing code in the settings (no Yandex one), and three test pages with their own share pictures.
PAGES_JS = r"""
process.env.ONLY = "index,about,contribute,orientation,monthly.,monthly-month,search.,events.njk,read.,status,404,sitemap,opensearch";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-seo-head-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        site: (data) => ({ ...data.site, search_engines: { ...(data.site.search_engines || {}), bing_verification: input.bing, yandex_verification: "" } }),
      });
      const page = { layout: "layouts/base.njk", lang: "en", pageKey: "og-test", title: "Test", sitemap: false, eleventyExcludeFromCollections: true };
      cfg.addTemplate("og-jpg.njk", "<p>jpg</p>", { ...page, permalink: "/og-jpg/index.html", ogImage: { src: "/assets/img/poster.JPG?v=3", width: 1080, height: 1350 } });
      cfg.addTemplate("og-drive.njk", "<p>drive</p>", { ...page, permalink: "/og-drive/index.html", ogImage: "https://lh3.googleusercontent.com/d/abc123def456=w1200" });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def metas(page: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in re.finditer(r'<meta (?:property|name)="([^"]+)" content="([^"]*)">', page):
        out.setdefault(m.group(1), []).append(m.group(2))
    return out


def head(page: str) -> str:
    return page.split("</head>")[0]


def ld_blocks(page: str) -> list[str]:
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)


def site_graph(page: str) -> dict[str, dict]:
    """The site-wide graph (the last ld+json block) by @type (BreadcrumbList, FAQPage …; the page's own node: "page")."""
    graph = json.loads(ld_blocks(page)[-1])
    assert graph["@context"] == "https://schema.org"
    out = {}
    for node in graph["@graph"]:
        key = "page" if node["@id"].endswith("#webpage") else node["@type"]
        assert key not in out, key
        out[key] = node
    return out


class Built(unittest.TestCase):
    pages: dict | None = None

    def built(self) -> dict:
        if Built.pages is None:
            Built.pages = run_js(self, PAGES_JS, data={"bing": FAKE_BING}, timeout=600)
        return Built.pages

    def html_pages(self) -> dict[str, str]:
        return {u: p for u, p in self.built().items() if u.endswith("/") or u.endswith(".html")}

    def sitemap_paths(self) -> set[str]:
        xml = self.built()["/sitemap.xml"]
        return {loc[len(SITE_URL):] for loc in re.findall(r"<loc>([^<]+)</loc>", xml)}

    def indexable(self) -> dict[str, str]:
        """The built pages of the sitemap (the test pages are left out of it)."""
        listed = self.sitemap_paths()
        pages = {u: p for u, p in self.html_pages().items() if u in listed}
        self.assertGreater(len(pages), 20)
        return pages


# ------------------------------------------------------------------------------------------------------ robots
class Robots(Built):
    def test_a_page_to_find_lets_results_show_it_whole(self):
        for url, page in self.indexable().items():
            with self.subTest(url=url):
                m = metas(head(page))
                self.assertEqual(m["robots"], [MAX_ROBOTS])
                self.assertEqual(len(re.findall(r'<link rel="alternate" hreflang=', page)), 3)
                self.assertIn(f'<link rel="canonical" href="{SITE_URL}{url}">', page)
        self.assertNotIn("noindex", MAX_ROBOTS)                    # (pwa.js reads any robots "noindex")

    def test_the_status_page_is_kept_out_of_search(self):
        pages, listed = self.html_pages(), self.sitemap_paths()
        for url in ("/status/", "/es/status/"):
            with self.subTest(url=url):
                page = pages[url]
                self.assertEqual(metas(page)["robots"], ["noindex"])
                self.assertIn(f'<link rel="canonical" href="{SITE_URL}{url}">', page)     # its own address
                self.assertNotIn('<link rel="alternate" hreflang=', page)
                self.assertEqual(ld_blocks(page), [])
                self.assertNotIn(url, listed)
                self.assertEqual(metas(page)["og:url"], [SITE_URL + url])                # still shared as itself
        self.assertIn("/about/", listed)
        fm = re.match(r"---\n(.*?)\n---\n", read("src", "pages", "status.njk"), re.S).group(1)
        data = yaml.safe_load(fm)
        self.assertIs(data.get("noindex"), True)
        self.assertIs(data.get("sitemap"), False)

    def test_the_404_page_is_as_it_was(self):
        for url in ("/404.html", "/es/404.html"):
            page = self.html_pages()[url]
            self.assertEqual(metas(page)["robots"], ["noindex"])
            self.assertNotIn('rel="canonical"', page)
            self.assertNotIn("og:url", page)
            self.assertEqual(ld_blocks(page), [])

    def test_the_template_keeps_the_404_block_and_writes_the_flag_on_its_own(self):
        base = read("src", "_includes", "layouts", "base.njk")
        self.assertIn('{%- if pageKey == "404" %}', base)
        self.assertNotRegex(base, r'pageKey == "404" or noindex|noindex or pageKey == "404"')
        self.assertIn('{% if noindex %}', base)
        self.assertNotRegex(base, r'name="robots" content="[^"]*\bindex\b')         # indexing is the default


# ------------------------------------------------------------------------------------------- link previews, titles
class Previews(Built):
    def test_twitter_says_what_open_graph_says(self):
        for url, page in self.html_pages().items():
            with self.subTest(url=url):
                m = metas(head(page))
                title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
                self.assertEqual(m["twitter:title"], [title])
                self.assertEqual(m["og:title"], [title])
                self.assertEqual(m["twitter:description"], m["og:description"])
                self.assertEqual(m["twitter:description"], m["description"])
                self.assertEqual(len(m["og:image"]), 1)

    def test_the_picture_type_when_its_file_name_says_it(self):
        p = self.html_pages()
        for url in ("/", "/es/", "/about/", "/es/events/"):
            m = metas(p[url])
            self.assertTrue(m["og:image"][0].endswith("/og-default-es.png?v=2" if url.startswith("/es/") else "/og-default.png?v=2"))
            self.assertEqual(m["og:image:type"], ["image/png"])
        m = metas(p["/og-jpg/"])
        self.assertEqual((m["og:image"], m["og:image:type"]), ([SITE_URL + "/assets/img/poster.JPG?v=3"], ["image/jpeg"]))
        m = metas(p["/og-drive/"])
        self.assertEqual(m["og:image"], ["https://lh3.googleusercontent.com/d/abc123def456=w1200"])
        self.assertNotIn("og:image:type", m)                          # a Drive picture's address says no type

    def test_the_filter_knows_the_types(self):
        r = run_js(self, """
            const S = (src) => filters.shareImage(src, { url: "https://example.org/gv" });
            out(["/a.png", "/a.png?v=2", "/a.JPG", "/a.jpeg", "/a.gif", "https://x.org/a.WebP#top",
                 "https://lh3.googleusercontent.com/d/abc=w1200", "https://i.ytimg.com/vi/xyz/hqdefault.jpg"].map((u) => S(u).type));
        """)
        self.assertEqual(r, ["image/png", "image/png", "image/jpeg", "image/jpeg", "image/gif", "image/webp", "", "image/jpeg"])

    def test_session_titles_name_the_course_not_the_site(self):
        pages = self.indexable()
        sessions = {u: p for u, p in pages.items() if re.fullmatch(r"(?:/es)?/orientation/[^/]+/", u)}
        self.assertGreaterEqual(len(sessions), 2)
        for url, page in sessions.items():
            lang = "es" if url.startswith("/es/") else "en"
            title = html.unescape(re.search(r"<title>(.*?)</title>", page).group(1))
            with self.subTest(url=url):
                self.assertRegex(title, r"^.+ · " + re.escape(t("nav.orientation", lang)) + " — NETA 65$")
                self.assertNotIn(SITE["title"], title)
        # every other page keeps the site's name after its own
        for url, key, lang in (("/about/", "nav.about", "en"), ("/es/about/", "nav.about", "es"), ("/orientation/", "nav.orientation", "en")):
            title = html.unescape(re.search(r"<title>(.*?)</title>", pages[url]).group(1))
            site_title = (SITE.get("title_es") or SITE["title"]) if lang == "es" else SITE["title"]
            self.assertEqual(title, f"{t(key, lang)} · {site_title} — NETA 65")


# ------------------------------------------------------------------------------------------- ownership checks
class Verification(Built):
    def test_only_the_home_page_and_only_a_code_that_is_there(self):
        for url, page in self.html_pages().items():
            with self.subTest(url=url):
                m = metas(head(page))
                self.assertEqual(m.get("msvalidate.01"), [FAKE_BING] if url in ("/", "/es/") else None)
                self.assertNotIn("yandex-verification", m)            # its setting is empty

    def test_the_settings_are_read_where_they_are_written(self):
        base = read("src", "_includes", "layouts", "base.njk")
        for key, tag in (("bing_verification", "msvalidate.01"), ("yandex_verification", "yandex-verification")):
            self.assertIn(f'<meta name="{tag}" content="{{{{ site.search_engines.{key} }}}}">', base)


# ------------------------------------------------------------------------------------------------- OpenSearch
class OpenSearch(Built):
    NS = {"os": "http://a9.com/-/spec/opensearch/1.1/"}

    def test_both_files_describe_the_search_of_their_language(self):
        names = set()
        for lang, prefix in (("en", ""), ("es", "/es")):
            with self.subTest(lang=lang):
                xml = self.built()[f"{prefix}/opensearch.xml"]
                self.assertTrue(xml.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
                doc = ET.fromstring(xml.encode("utf-8"))
                self.assertEqual(doc.tag, "{http://a9.com/-/spec/opensearch/1.1/}OpenSearchDescription")
                short = doc.findtext("os:ShortName", namespaces=self.NS)
                self.assertEqual(short, t("site.search_engine_name", lang))
                self.assertLessEqual(len(short), 16)                         # OpenSearch's limit
                names.add(short)
                self.assertEqual(doc.findtext("os:Description", namespaces=self.NS), t("search.meta_desc", lang))
                urls = {u.get("type"): u for u in doc.findall("os:Url", self.NS)}
                self.assertEqual(urls["text/html"].get("template"), f"{SITE_URL}{prefix}/search/?q={{searchTerms}}")
                self.assertEqual(urls["text/html"].get("method"), "get")
                self.assertEqual(urls["application/opensearchdescription+xml"].get("template"), f"{SITE_URL}{prefix}/opensearch.xml")
                self.assertEqual(urls["application/opensearchdescription+xml"].get("rel"), "self")
                img = doc.find("os:Image", self.NS)
                self.assertEqual((img.get("width"), img.get("height"), img.get("type")), ("32", "32", "image/png"))
                self.assertEqual(img.text, SITE_URL + "/assets/img/logo-32x32.png")
                self.assertTrue((ROOT / "src" / "assets" / "img" / "logo-32x32.png").is_file())
                self.assertEqual(doc.findtext("os:InputEncoding", namespaces=self.NS), "UTF-8")
                self.assertEqual(doc.findtext("os:Language", namespaces=self.NS), "es-US" if lang == "es" else "en-US")
                # every page names its language's file
                for url, page in self.html_pages().items():
                    if url.startswith("/es/") == (lang == "es"):
                        self.assertIn(f'<link rel="search" type="application/opensearchdescription+xml" title="{html.escape(short)}" '
                                      f'href="{prefix}/opensearch.xml">', page, url)
        self.assertEqual(len(names), 2, "each language its own name: a bilingual visitor can keep both")
        # the search page reads ?q= — the address the files give
        self.assertRegex(read("src", "assets", "js", "search.js"), r'\.get\("q"\)')

    def test_not_a_page(self):
        src = read("src", "pages", "opensearch.11ty.js")
        self.assertRegex(src, r"layout:\s*false")
        self.assertRegex(src, r"eleventyExcludeFromCollections:\s*true")
        self.assertNotIn("/opensearch", self.built()["/sitemap.xml"])


# -------------------------------------------------------------------------------------------- structured data
class StructuredData(Built):
    def test_one_graph_at_the_end_of_every_indexable_page(self):
        for url, page in self.indexable().items():
            with self.subTest(url=url):
                blocks = ld_blocks(page)
                for b in blocks:
                    json.loads(b)
                self.assertEqual(sum((ROOT_URL + "#website") in b for b in blocks), 1)
                self.assertGreater(page.rfind("application/ld+json"), page.rfind("</footer>"), "after the page and its footer")
                self.assertNotRegex(blocks[-1], r"&(?:amp|#\d+|quot|lt|gt);", "plain text, never HTML entities")
        # the Events page's own block (its events) stays the first one
        events = self.indexable()["/events/"]
        if len(ld_blocks(events)) > 1:
            self.assertNotIn("#website", ld_blocks(events)[0])
        # the home page's old block is gone: one Organization on it
        self.assertEqual(len(ld_blocks(self.indexable()["/"])), 1)
        self.assertNotIn("application/ld+json", read("src", "pages", "index.njk"))

    def test_the_same_committee_and_site_on_every_page(self):
        orgs, sites = set(), set()
        for url, page in self.indexable().items():
            g = site_graph(page)
            orgs.add(json.dumps(g["Organization"], sort_keys=True))
            sites.add(json.dumps(g["WebSite"], sort_keys=True))
        self.assertEqual((len(orgs), len(sites)), (1, 1), "one entity: the same values on every page, in both languages")
        org, web = json.loads(orgs.pop()), json.loads(sites.pop())
        self.assertEqual(org["@id"], ROOT_URL + "#committee")
        self.assertEqual(org["name"], SITE["committee"])
        self.assertEqual(org["url"], ROOT_URL)
        # (a setting left empty leaves its key out)
        self.assertEqual(org.get("alternateName"), SITE.get("committee_es") or None)
        self.assertEqual(org.get("email"), SITE.get("contact_email") or None)
        self.assertEqual(org.get("sameAs"), [SITE["committee_page"]] if SITE.get("committee_page") else None,
                         "only the Area's page about the committee")
        self.assertEqual(org["description"], t("footer.about", "en"))
        self.assertEqual(org["knowsLanguage"], ["en", "es"])
        self.assertEqual(org["logo"], {"@type": "ImageObject", "url": SITE_URL + "/assets/img/app-icon-512.png", "width": 512, "height": 512})
        self.assertTrue((ROOT / "src" / "assets" / "img" / "app-icon-512.png").is_file())
        parent = {"@type": "Organization", "name": SITE["area"], "alternateName": "NETA 65"}
        if SITE.get("area_website"):
            parent["url"] = SITE["area_website"]
        self.assertEqual(org["parentOrganization"], parent)
        self.assertEqual(web, {"@type": "WebSite", "@id": ROOT_URL + "#website", "url": ROOT_URL, "name": SITE["title"],
                               "alternateName": "GV/LV 65", "inLanguage": ["en-US", "es-US"], "publisher": {"@id": ROOT_URL + "#committee"}})
        # never the magazines' own accounts (they are AA Grapevine's and La Viña's, not the committee's)
        everything = json.dumps(org)
        for host in ("instagram.com", "youtube.com", "aagrapevine.org", "aalavina.org"):
            self.assertNotIn(host, everything)

    def test_each_page_its_own_node(self):
        kinds = {"/": "WebPage", "/about/": "AboutPage", "/search/": "SearchResultsPage", "/events/": "CollectionPage",
                 "/read/": "CollectionPage", "/orientation/": "CollectionPage", "/monthly/": "CollectionPage",
                 "/contribute/": "WebPage"}
        pages = self.indexable()
        for url, page in pages.items():
            lang = "es" if url.startswith("/es/") else "en"
            node = site_graph(page)["page"]
            m = metas(head(page))
            with self.subTest(url=url):
                self.assertEqual(node["@id"], SITE_URL + url + "#webpage")
                self.assertEqual(node["url"], SITE_URL + url)
                self.assertEqual(node["inLanguage"], "es-US" if lang == "es" else "en-US")
                self.assertEqual(node["description"], html.unescape(m["description"][0]))
                self.assertEqual(node["isPartOf"], {"@id": ROOT_URL + "#website"})
                self.assertEqual(node["publisher"], {"@id": ROOT_URL + "#committee"})
                self.assertEqual(node["primaryImageOfPage"]["url"], html.unescape(m["og:image"][0]))
                self.assertEqual(node["primaryImageOfPage"].get("width"), int(m["og:image:width"][0]) if "og:image:width" in m else None)
                en = url[3:] if lang == "es" else url
                if en in kinds:
                    self.assertEqual(node["@type"], kinds[en])
                self.assertEqual("mainEntity" in node, node["@type"] == "AboutPage")
                if url not in ("/", "/es/"):
                    title = html.unescape(re.search(r"<title>(.*?)</title>", page).group(1))
                    self.assertEqual(node["name"], title.split(" · ")[0])
        self.assertEqual(site_graph(pages["/about/"])["page"]["mainEntity"], {"@id": ROOT_URL + "#committee"})
        self.assertEqual(site_graph(pages["/"])["page"]["name"], SITE["title"])
        # the template: every type it is given is one of these
        for f in (ROOT / "src" / "pages").glob("*.njk"):
            m = re.search(r"(?m)^ldType: (\w+)$", read("src", "pages", f.name))
            if m:
                self.assertIn(m.group(1), {"AboutPage", "CollectionPage", "SearchResultsPage"}, f.name)

    def crumbs(self, url: str) -> list[tuple]:
        g = site_graph(self.indexable()[url])
        self.assertEqual(g["page"].get("breadcrumb"), {"@id": SITE_URL + url + "#breadcrumb"})
        bl = g["BreadcrumbList"]
        self.assertEqual(bl["@id"], SITE_URL + url + "#breadcrumb")
        self.assertEqual([i["position"] for i in bl["itemListElement"]], list(range(1, len(bl["itemListElement"]) + 1)))
        self.assertTrue(all(i["@type"] == "ListItem" for i in bl["itemListElement"]))
        return [(i["name"], i.get("item")) for i in bl["itemListElement"]]

    def test_breadcrumbs(self):
        pages = self.indexable()
        # the home page has none
        for url in ("/", "/es/"):
            g = site_graph(pages[url])
            self.assertNotIn("BreadcrumbList", g)
            self.assertNotIn("breadcrumb", g["page"])
        for lang, prefix in (("en", ""), ("es", "/es")):
            home = (t("nav.home", lang), f"{SITE_URL}{prefix}/")
            # a page of the menu: Home → the page (the last step has no address: it is the page itself)
            self.assertEqual(self.crumbs(f"{prefix}/about/"), [home, (t("nav.about", lang), None)])
            self.assertEqual(self.crumbs(f"{prefix}/orientation/"), [home, (t("nav.orientation", lang), None)])
            # a GVR / RLV 101 session: Home → GVR / RLV 101 → the session's own name
            sessions = [u for u in pages if re.fullmatch(re.escape(prefix) + r"/orientation/[^/]+/", u)]
            self.assertTrue(sessions)
            for url in sessions:
                title = html.unescape(re.search(r"<title>(.*?)</title>", pages[url]).group(1))
                with self.subTest(url=url):
                    self.assertEqual(self.crumbs(url), [home, (t("nav.orientation", lang), f"{SITE_URL}{prefix}/orientation/"),
                                                        (title.split(" · ")[0], None)])
            # a month of the toolkit: Home → Monthly toolkit → the month
            months = [u for u in pages if re.fullmatch(re.escape(prefix) + r"/monthly/\d{4}-\d{2}/", u)]
            self.assertTrue(months)
            for url in months:
                title = html.unescape(re.search(r"<title>(.*?)</title>", pages[url]).group(1))
                with self.subTest(url=url):
                    self.assertEqual(self.crumbs(url), [home, (t("nav.monthly", lang), f"{SITE_URL}{prefix}/monthly/"),
                                                        (title.split(" · ")[0], None)])

    def test_the_faq_is_the_one_the_page_shows(self):
        for lang, url in (("en", "/contribute/"), ("es", "/es/contribute/")):
            page = self.indexable()[url]
            g = site_graph(page)
            faq = g["FAQPage"]
            with self.subTest(url=url):
                self.assertEqual(faq["@id"], SITE_URL + url + "#faq")
                self.assertEqual(faq["isPartOf"], {"@id": SITE_URL + url + "#webpage"})
                self.assertEqual(faq["inLanguage"], "es-US" if lang == "es" else "en-US")
                shown = re.findall(r'<details class="read-faq[^"]*">\s*<summary[^>]*>\s*<span>(.*?)</span>.*?</summary>\s*<p[^>]*>(.*?)</p>',
                                   page, re.S)
                self.assertGreaterEqual(len(shown), 3)
                self.assertEqual(len(faq["mainEntity"]), len(shown), "as many questions as the page shows")
                for q, (sq, sa) in zip(faq["mainEntity"], shown):
                    self.assertEqual(q["@type"], "Question")
                    self.assertEqual(q["name"], html.unescape(re.sub(r"<[^>]+>", "", sq)).strip())
                    self.assertEqual(q["acceptedAnswer"], {"@type": "Answer", "text": html.unescape(re.sub(r"<[^>]+>", "", sa)).strip()})
        # only the page that shows questions and answers has them
        for url, page in self.indexable().items():
            if not url.endswith("/contribute/"):
                self.assertNotIn("FAQPage", site_graph(page), url)

    def test_no_names_dates_or_search_box(self):
        for url, page in self.indexable().items():
            text = ld_blocks(page)[-1]
            with self.subTest(url=url):
                for word in ("SearchAction", "potentialAction", "Person", "author", "datePublished", "dateModified"):
                    self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
