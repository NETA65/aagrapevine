"""robots.txt: ours, the one at the root of the address, and the weekly check that guards it — offline (no network).

Crawlers read robots.txt only at the root of an address, so on the GitHub Pages project site our own
/aagrapevine/robots.txt (src/robots.njk) is never read: https://neta65.github.io/robots.txt counts, published by the
NETA65/neta65.github.io repository from the files in docs/user-site/ (README → "Search engines").

  * OurFile     — src/robots.njk builds exactly "User-agent: *", "Allow: /" and the sitemap's full address (an
                  Eleventy build of no page but it, with a custom domain's address): it is the root file once the
                  site has its own address, so it allows everything and names no Disallow;
  * UserSite    — docs/user-site (documentation: scripts/ops/gate_tests.py CONTENT_TESTS): robots.txt lets
                  Googlebot, Bingbot and OAI-SearchBot into /aagrapevine/ and /GV_Booth/ and names the sitemap
                  (Protego AND urllib.robotparser); its optional block is off as delivered, and once its six lines
                  are uncommented keeps GPTBot … out while Google, Bing and the AI-search crawlers stay in; the
                  weekly check finds nothing wrong with it; index.html is a valid page that moves visitors and
                  search engines to the site (instant refresh + canonical, no noindex, no script), with both
                  languages' links; .nojekyll is there and empty;
  * WeeklyCheck — scripts/ops/root_robots.py with stand-in answers: 404 = "not set up yet" (no problem), 200 is
                  judged (Google and Bing allowed in, the sitemap named), anything else is a problem; a custom
                  domain is skipped; what it writes (the report file, the run summary, the step output) and its
                  exit code (always 0); one request with the site's robot, robots.txt not read first.
                  (The workflow's wiring and the issue: tests/test_automation.py LinkCheck.)

    python -m unittest tests.test_seo_robots -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import codecs
import html
import io
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock
from urllib import robotparser
from urllib.parse import urlsplit

import yaml
from protego import Protego

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.ops import root_robots as R  # noqa: E402

USER_SITE = ROOT / "docs" / "user-site"
SITE = "https://neta65.github.io/aagrapevine"          # (WeeklyCheck's stand-in address; UserSite reads the settings)
# what Googlebot and Bingbot must be able to fetch (root_robots.PATHS), as a report lists it
FETCH = (f"{SITE}/, {SITE}/es/, {SITE}/assets/css/main.css, {SITE}/assets/js/app.js, {SITE}/search-index.json, "
         f"{SITE}/sitemap.xml")


def uncomment_the_option(text: str) -> str:
    """robots.txt as the owner turns the optional block on: the "# " deleted before its six lines."""
    return re.sub(r"(?m)^# ((?:User-agent|Disallow):)", r"\1", text)


def both_parsers(text: str):
    """(Protego's can_fetch(url, agent), urllib's) and both parsers' sitemaps."""
    p = Protego.parse(text)
    u = robotparser.RobotFileParser()
    u.parse(text.splitlines())
    return p, u


# ============================================================================ src/robots.njk
class OurFile(unittest.TestCase):
    def test_the_three_lines(self):
        content = run_js(self, r"""
          process.env.ONLY = "no-page-of-the-site";
          const os = await import("node:os");
          const { Eleventy } = await import("@11ty/eleventy");
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-robots-"));
          try {
            const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
            const pages = await elev.toJSON();
            out((pages.find((p) => p.url === "/robots.txt") || {}).content ?? null);
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }""",
                         env={"SITE_URL": "https://grapevine.example.org/", "STRICT_BUILD": "", "BUILD_WARNINGS": "",
                              "GITHUB_ACTIONS": ""})
        self.assertEqual(content, "User-agent: *\nAllow: /\nSitemap: https://grapevine.example.org/sitemap.xml\n")

    def test_the_template_explains_where_the_real_file_is(self):
        t = (ROOT / "src" / "robots.njk").read_text(encoding="utf-8")
        self.assertNotRegex(t, r"(?im)^\s*disallow", "no Disallow lines: with a custom domain this IS the root file")
        for needle in ("https://neta65.github.io/robots.txt", "NETA65/neta65.github.io", "docs/user-site/",
                       'README → "Search engines"', "only with a custom domain", "scripts/ops/root_robots.py"):
            self.assertIn(needle, t)


# ============================================================================ docs/user-site
class UserSite(unittest.TestCase):
    """The files for the NETA65/neta65.github.io repository, against the site's address in config/site.yml."""

    @classmethod
    def setUpClass(cls):
        cls.site = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))["site"]
        cls.url = str(cls.site["url"]).rstrip("/")
        parts = urlsplit(cls.url)
        cls.host = f"{parts.scheme}://{parts.netloc}"
        cls.robots = (USER_SITE / "robots.txt").read_bytes().decode("utf-8")
        cls.index = (USER_SITE / "index.html").read_bytes().decode("utf-8")

    def test_robots_lets_the_search_engines_in_and_names_the_sitemap(self):
        self.assertNotIn("\r", self.robots, "LF line ends")
        self.assertFalse(self.robots.startswith(codecs.BOM_UTF8.decode("utf-8")), "no byte-order mark")
        active = [ln for ln in self.robots.splitlines() if ln.strip() and not ln.startswith("#")]
        self.assertEqual(active, ["User-agent: *", "Allow: /", f"Sitemap: {self.url}/sitemap.xml"])
        p, u = both_parsers(self.robots)
        self.assertEqual(list(p.sitemaps), [f"{self.url}/sitemap.xml"])
        self.assertEqual(u.site_maps(), [f"{self.url}/sitemap.xml"])
        for agent in ("Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "GPTBot"):
            for where in (f"{self.url}/", f"{self.url}/es/", f"{self.url}/assets/css/main.css",
                          f"{self.url}/search-index.json", f"{self.host}/GV_Booth/", f"{self.host}/Archives_Booth/"):
                with self.subTest(agent=agent, url=where):
                    self.assertTrue(p.can_fetch(where, agent), "Protego")
                    self.assertTrue(u.can_fetch(agent, where), "urllib")

    def test_the_comments_say_what_it_covers(self):
        for needle in ("/aagrapevine/", "/GV_Booth/", "/Archives_Booth/", 'never add "Disallow: /"',
                       "NETA65/neta65.github.io", "docs/user-site/robots.txt", '"Search engines"'):
            self.assertIn(needle, self.robots)

    def test_the_optional_block_is_off_and_keeps_only_ai_training_out(self):
        lines = self.robots.splitlines()
        start = next(i for i, ln in enumerate(lines) if "OPTIONAL" in ln)
        self.assertGreater(start, lines.index("Allow: /"), "below the rules")
        block = lines[start:]
        self.assertTrue(all(ln.startswith("# ") for ln in block), "every line of it is a comment as delivered")
        rules = [ln[2:] for ln in block if re.match(r"# (User-agent|Disallow):", ln)]
        self.assertEqual(rules, ["User-agent: GPTBot", "User-agent: ClaudeBot", "User-agent: Google-Extended",
                                 "User-agent: CCBot", "User-agent: Applebot-Extended", "Disallow: /"])
        on = uncomment_the_option(self.robots)
        self.assertNotEqual(on, self.robots)
        p, u = both_parsers(on)
        self.assertEqual(list(p.sitemaps), [f"{self.url}/sitemap.xml"], "the sitemap is still named")
        self.assertEqual(u.site_maps(), [f"{self.url}/sitemap.xml"])
        for where in (f"{self.url}/", f"{self.host}/GV_Booth/"):
            for agent in ("GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "Applebot-Extended"):
                with self.subTest(agent=agent, url=where):
                    self.assertFalse(p.can_fetch(where, agent), "Protego")
                    self.assertFalse(u.can_fetch(agent, where), "urllib")
            for agent in ("Googlebot", "Bingbot", "Applebot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"):
                with self.subTest(agent=agent, url=where):
                    self.assertTrue(p.can_fetch(where, agent), "Protego")
                    self.assertTrue(u.can_fetch(agent, where), "urllib")

    def test_the_weekly_check_finds_nothing_wrong_with_it(self):
        for text, kept_out in ((self.robots, "are not kept out"), (uncomment_the_option(self.robots), "GPTBot, ClaudeBot")):
            problems, notes = R.judge(text, self.url)
            self.assertEqual(problems, [])
            self.assertIn(kept_out, " ".join(notes))
            self.assertNotIn("AI search answers", " ".join(notes))

    def test_index_is_a_valid_page(self):
        self.assertNotIn("\r", self.index, "LF line ends")
        self.assertTrue(self.index.startswith("<!doctype html>\n"))
        checker = PageChecker()
        checker.feed(self.index)
        checker.close()
        self.assertEqual(checker.problems, [])
        self.assertEqual(checker.stack, [], "every element is closed")
        self.assertEqual([checker.count[t] for t in ("html", "head", "body", "title", "main")], [1, 1, 1, 1, 1])
        self.assertEqual(checker.first_in_head, ("meta", {"charset": "utf-8"}), "the character set first in <head>")
        self.assertLess(self.index.index('<meta charset="utf-8">'), 1024, "within the first 1024 bytes")

    def test_index_moves_visitors_and_search_engines_to_the_site(self):
        checker = PageChecker()
        checker.feed(self.index)
        home = f"{self.url}/"
        metas = {(a.get("http-equiv") or a.get("name")): a.get("content") for t, a in checker.tags if t == "meta"}
        self.assertEqual(metas["refresh"], f"0; url={home}", "an instant refresh: a permanent move for Google and Bing")
        self.assertEqual(metas["viewport"], "width=device-width, initial-scale=1")
        self.assertNotIn("robots", metas, "no noindex: it would contradict the move")
        self.assertEqual([a["href"] for t, a in checker.tags if t == "link" and a.get("rel") == "canonical"], [home])
        self.assertNotIn("<script", self.index.lower(), "no JavaScript redirect (search engines may not run it)")
        self.assertEqual(checker.root_lang, "en")
        links = [(a["href"], text) for a, text in checker.links]
        self.assertEqual(links, [(home, self.site["committee"]), (f"{home}es/", self.site["committee_es"])])
        self.assertEqual(checker.link_langs, ["en", "es"], "each link says its language")
        self.assertIn("prefers-color-scheme: dark", self.index, "light and dark")
        # the address to change if the site moves, said where it is used
        self.assertEqual(self.index.count(home), 5, "the note at the top + the refresh, the canonical and the two links")
        self.assertIn("Custom domain", self.index)

    def test_jekyll_is_off(self):
        nojekyll = USER_SITE / ".nojekyll"
        self.assertTrue(nojekyll.is_file())
        self.assertEqual(nojekyll.read_bytes(), b"")


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class PageChecker(HTMLParser):
    """A small HTML check: elements closed in order, void elements never closed, what is where."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        self.problems: list[str] = []
        self.count: dict[str, int] = {}
        self.tags: list[tuple[str, dict]] = []
        self.first_in_head = None
        self.root_lang = None
        self.links: list[tuple[dict, str]] = []
        self.link_langs: list[str | None] = []
        self._text: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        self.count[tag] = self.count.get(tag, 0) + 1
        self.tags.append((tag, a))
        if tag == "html":
            self.root_lang = a.get("lang")
        if self.stack and self.stack[-1][0] == "head" and self.first_in_head is None:
            self.first_in_head = (tag, a)
        if tag == "a":
            self._text = []
            self.link_langs.append(next((s[1].get("lang") for s in reversed(self.stack) if s[1].get("lang")), None))
            self.links.append((a, ""))
        if tag not in VOID:
            self.stack.append((tag, a))

    def handle_startendtag(self, tag, attrs):
        self.problems.append(f"<{tag} … />: not HTML")

    def handle_endtag(self, tag):
        if tag in VOID:
            self.problems.append(f"</{tag}>: a void element has no end tag")
            return
        if not self.stack or self.stack[-1][0] != tag:
            self.problems.append(f"</{tag}> closes {self.stack[-1][0] if self.stack else 'nothing'}")
            return
        self.stack.pop()
        if tag == "a" and self._text is not None:
            self.links[-1] = (self.links[-1][0], html.unescape("".join(self._text)).strip())
            self._text = None

    def handle_data(self, data):
        if self._text is not None:
            self._text.append(data)


# ============================================================================ scripts/ops/root_robots.py
class Answer:
    """A stand-in for requests.Response."""

    def __init__(self, status: int, text: str = "", url: str = "https://neta65.github.io/robots.txt",
                 history: list | None = None):
        self.status_code, self.text, self.url, self.history = status, text, url, history or []


GOOD = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"


class WeeklyCheck(unittest.TestCase):
    def check(self, answer, site: str = SITE):
        asked: list[str] = []

        def get(url):
            asked.append(url)
            return answer
        result = R.check(site, get)
        return result, asked

    def test_the_root_of_the_address(self):
        self.assertEqual(R.root_robots_url("https://neta65.github.io/aagrapevine"), "https://neta65.github.io/robots.txt")
        self.assertEqual(R.root_robots_url("https://neta65.github.io/aagrapevine/"), "https://neta65.github.io/robots.txt")
        self.assertEqual(R.root_robots_url("http://localhost:8080/aagrapevine"), "http://localhost:8080/robots.txt")
        for own in ("https://grapevine.neta65.org", "https://grapevine.neta65.org/", ""):
            self.assertIsNone(R.root_robots_url(own), own)

    def test_a_custom_domain_is_skipped(self):
        result, asked = self.check(Answer(200, "User-agent: *\nDisallow: /\n"), site="https://grapevine.neta65.org")
        self.assertEqual((result.state, result.problems, asked), ("skipped", [], []), "nothing asked")
        self.assertIn("Skipped", R.report(result, "https://grapevine.neta65.org"))

    def test_404_is_not_set_up_yet(self):
        result, asked = self.check(Answer(404, "<html>Site not found · GitHub Pages</html>"))
        self.assertEqual(asked, ["https://neta65.github.io/robots.txt"])
        self.assertEqual((result.state, result.problems), ("missing", []))
        text = R.report(result, SITE)
        self.assertIn("## The root robots.txt (https://neta65.github.io/robots.txt)", text)
        self.assertIn("Not set up yet (owner step: README → Search engines)", text)
        self.assertNotIn("- [ ]", text, "not reported as broken")

    def test_a_good_file(self):
        result, _ = self.check(Answer(200, GOOD))
        self.assertEqual((result.state, result.problems), ("ok", []))
        self.assertEqual(result.notes, ["AI-model training crawlers are not kept out (the default; README → Search "
                                        "engines has the optional lines)."])
        self.assertIn(f"OK: Googlebot and Bingbot may crawl {SITE}/ and it names the sitemap.", R.report(result, SITE))

    def test_the_owners_choice_is_information_only(self):
        text = GOOD + "\nUser-agent: GPTBot\nUser-agent: ClaudeBot\nUser-agent: Google-Extended\nUser-agent: CCBot\n" \
                      "User-agent: Applebot-Extended\nDisallow: /\n"
        result, _ = self.check(Answer(200, text))
        self.assertEqual((result.state, result.problems), ("ok", []))
        self.assertEqual(result.notes, ["AI-model training crawlers kept out (the owner's choice): GPTBot, ClaudeBot, "
                                        "Google-Extended, CCBot, Applebot-Extended."])
        result, _ = self.check(Answer(200, GOOD + "\nUser-agent: OAI-SearchBot\nDisallow: /\n"))
        self.assertEqual((result.state, result.problems), ("ok", []))
        self.assertIn("Kept out of AI search answers: OAI-SearchBot — the site does not show in their answers.",
                      result.notes)

    def test_rules_that_hide_the_site(self):
        result, _ = self.check(Answer(200, "User-agent: *\nDisallow: /\n"))
        self.assertEqual(result.state, "problem")
        self.assertEqual(result.problems, [
            f"Googlebot may not fetch {FETCH} — a Disallow line hides the site from Google",
            f"Bingbot may not fetch {FETCH} — a Disallow line hides the site from Bing",
            f"no line `Sitemap: {SITE}/sitemap.xml` — search engines no longer learn where the sitemap is"])
        text = R.report(result, SITE)
        self.assertIn("Fix it in **the NETA65/neta65.github.io repository** (its robots.txt; the right text is "
                      "**docs/user-site/robots.txt** in this repository, owner step: README → Search engines):", text)
        self.assertEqual(text.count("- [ ] "), 3)
        # one engine, one folder
        result, _ = self.check(Answer(200, "User-agent: Googlebot\nDisallow: /aagrapevine/\n\n" + GOOD))
        self.assertEqual(result.problems, [f"Googlebot may not fetch {FETCH} — a Disallow "
                                           "line hides the site from Google"])
        result, _ = self.check(Answer(200, "User-agent: *\nDisallow: /aagrapevine/assets/\n\n"
                                           f"Sitemap: {SITE}/sitemap.xml\n"))
        self.assertEqual(result.problems, [
            f"Googlebot may not fetch {SITE}/assets/css/main.css, {SITE}/assets/js/app.js — a Disallow line hides the "
            "site from Google",
            f"Bingbot may not fetch {SITE}/assets/css/main.css, {SITE}/assets/js/app.js — a Disallow line hides the "
            "site from Bing"])
        # pattern rules that keep the folders open but hide the files a page needs (round-9 review)
        for rule, shut in (("Disallow: /*.css$", f"{SITE}/assets/css/main.css"),
                           ("Disallow: /*.js$", f"{SITE}/assets/js/app.js"),
                           ("Disallow: /*.json", f"{SITE}/search-index.json")):
            with self.subTest(rule):
                result, _ = self.check(Answer(200, f"User-agent: *\n{rule}\n\nSitemap: {SITE}/sitemap.xml\n"))
                self.assertEqual(result.problems, [
                    f"Googlebot may not fetch {shut} — a Disallow line hides the site from Google",
                    f"Bingbot may not fetch {shut} — a Disallow line hides the site from Bing"])
        # the sitemap of another address only
        result, _ = self.check(Answer(200, "User-agent: *\nAllow: /\nSitemap: https://example.org/sitemap.xml\n"))
        self.assertEqual(result.problems, [f"no line `Sitemap: {SITE}/sitemap.xml` — search engines no longer learn "
                                           "where the sitemap is"])

    def test_any_other_answer_is_a_problem(self):
        for answer, want in ((Answer(503), "HTTP 503 (expected 200, or 404 while the NETA65/neta65.github.io "
                                           "repository is not set up)"),
                             (Answer(403), "HTTP 403 (expected 200"),
                             (None, "no answer"),
                             (Answer(200, GOOD, url="https://grapevine.neta65.org/robots.txt", history=[Answer(301)]),
                              "it redirects to https://grapevine.neta65.org/robots.txt — a custom domain set on the "
                              "NETA65/neta65.github.io repository?")):
            with self.subTest(want=want):
                result, _ = self.check(answer)
                self.assertEqual(result.state, "problem")
                self.assertEqual(len(result.problems), 1)
                self.assertTrue(result.problems[0].startswith(want), result.problems[0])

    def run_main(self, answer, argv=(), env=None, cfg=None):
        tmp = Path(tempfile.mkdtemp(prefix="gv-root-robots-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        summary, output = tmp / "summary.md", tmp / "output.txt"
        asked: list[str] = []

        def get(url):
            asked.append(url)
            return answer
        e = {"GITHUB_STEP_SUMMARY": str(summary), "GITHUB_OUTPUT": str(output), **(env or {})}
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = R.main(list(argv), get=get, env=e, cfg=cfg if cfg is not None else {"site": {"url": SITE}},
                          out=tmp / "lychee" / "robots.md")
        report = (tmp / "lychee" / "robots.md").read_text(encoding="utf-8")
        self.assertEqual(summary.read_text(encoding="utf-8"), report, "the run summary says the same")
        self.assertEqual(buf.getvalue(), report, "… and the log")
        return code, report, output.read_text(encoding="utf-8"), asked

    def test_what_it_writes(self):
        code, report, output, asked = self.run_main(Answer(404))
        self.assertEqual((code, output, asked), (0, "problems=0\n", ["https://neta65.github.io/robots.txt"]))
        self.assertIn("Not set up yet", report)
        code, report, output, _ = self.run_main(Answer(200, "User-agent: *\nDisallow: /\n"))
        self.assertEqual((code, output), (0, "problems=3\n"), "a problem opens the issue — and never fails the job")
        code, _report, output, _ = self.run_main(None)
        self.assertEqual((code, output), (0, "problems=1\n"))

    def test_which_address(self):
        _c, _r, _o, asked = self.run_main(Answer(404), cfg={"site": {"url": "https://example.github.io/gv/"}})
        self.assertEqual(asked, ["https://example.github.io/robots.txt"], "site.url in config/site.yml")
        _c, _r, _o, asked = self.run_main(Answer(404), env={"SITE_URL": "https://other.github.io/x"})
        self.assertEqual(asked, ["https://other.github.io/robots.txt"], "the SITE_URL the workflow may set wins")
        _c, report, output, asked = self.run_main(Answer(404), argv=["--site", "https://grapevine.neta65.org"])
        self.assertEqual((asked, output), ([], "problems=0\n"), "a custom domain: skipped")
        self.assertIn("Skipped", report)
        _c, report, output, asked = self.run_main(Answer(404), cfg={"site": {"url": ""}})
        self.assertEqual((asked, output), ([], "problems=0\n"))
        self.assertIn("Not checked: no site address", report)

    def test_one_request_with_the_sites_robot(self):
        made = []

        class Session:
            def __init__(self, **kw):
                made.append(kw)

            def get(self, url, **kw):
                made.append((url, kw))
                return Answer(404)
        with mock.patch("scripts.sync.common.PoliteSession", Session):
            r = R.polite_get("https://neta65.github.io/robots.txt")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(made[0]["respect_robots"], False, "robots.txt itself is always allowed: not read twice")
        self.assertEqual(made[1:], [("https://neta65.github.io/robots.txt", {"timeout": 40})])
        self.assertNotIn("user_agent", made[0], "the site's own robot name (config/site.yml sources.crawler)")


if __name__ == "__main__":
    unittest.main()
