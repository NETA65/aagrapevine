"""Round 33 · the audit's page fixes (group "pages"): what the source must keep, and what a real build of /read/,
/contribute/ and /offline/ (Eleventy, ONLY=read,contribute,offline, both languages) writes. tests/browser/
test_audit_page_fixes.py measures the same things in a real browser (focus-ring contrast, sideways scroll, layout shift).

  * FocusRings   — the dark magazine panels (.read-cover--gv / --lv: /read/'s cover headers, /contribute/'s "Submit
                   online" panels and workshop band, the Shop and About cover panels) give their focus ring white
                   (the site's blue one was 1.1–2.3 : 1 on them); in high contrast a YouTube player's Play button and
                   the inset scrolling panels keep their ring INSIDE (in the same @layer base as the high-contrast
                   rule, with !important — anywhere else it would silently lose).
  * SmallText    — the small words that were just under 4.5 : 1: the writer's-guide EN / ES badges on /contribute/,
                   the La Viña line above the magazine's name on the home page, the Shop's "On sale this month"
                   eyebrow, the date and account over an Instagram picture.
  * Inputs       — a placeholder wider than its box ends in "…" (the input utility).
  * OfflineCard  — /offline/'s "Saved on this device" card keeps the empty state's height while it says "Loading…".
  * Built        — no unfilled {placeholder} in the pages' words or attributes (the recorder's La Viña "at least {min}
                   minutes"); the /read/ story lists Alpine skips (x-ignore) hold no Alpine directive; an archive
                   row's theme may wrap (whitespace-normal!).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def layer_blocks(css: str, name: str) -> list[str]:
    """The text of each `@layer <name> { … }` (braces counted; main.css has more than one @layer base)."""
    out, at = [], 0
    while (start := css.find(f"@layer {name} {{", at)) >= 0:
        depth = 0
        for i in range(start, len(css)):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append(css[start:i + 1])
                    at = i + 1
                    break
        else:
            raise AssertionError(f"@layer {name} is not closed")
    return out


class FocusRings(unittest.TestCase):
    def test_the_dark_magazine_panels_give_the_ring_white(self):
        css = read("src", "assets", "css", "areas", "read.css")
        self.assertIn(":is(.read-cover--gv, .read-cover--lv) :focus-visible { outline-color: #fff; }", css)
        # (after the panels' own rules, at the top level — not inside a media query)
        self.assertGreater(css.index(":is(.read-cover--gv, .read-cover--lv) :focus-visible"), css.index(".read-cover--lv {"))

    def test_high_contrast_keeps_the_inset_rings_inside(self):
        general = ':root[data-contrast="high"] :focus-visible { outline-style: solid !important; outline-width: 4px !important; outline-offset: 3px !important; }'
        base = next((b for b in layer_blocks(read("src", "assets", "css", "main.css"), "base") if general in b), "")
        lyt = ':root[data-contrast="high"] lite-youtube > .lyt-playbtn:focus-visible { outline-offset: -8px !important; }'
        inset = ':root[data-contrast="high"] :is(.cm-pre, .rp-doc-wrap, .xp-panel):focus-visible { outline-offset: -4px !important; }'
        for rule in (general, lyt, inset):
            self.assertIn(rule, base)
        self.assertGreater(base.index(lyt), base.index(general))
        self.assertGreater(base.index(inset), base.index(general))
        # the inset panels the rule names still have an inset ring of their own
        for area, sel in (("community", ".cm-pre:focus-visible"), ("report", ".rp-doc-wrap:focus-visible"), ("expenses", ".xp-panel:focus-visible")):
            rule = read("src", "assets", "css", "areas", f"{area}.css")
            rule = rule[rule.index(sel):]
            self.assertRegex(rule[:rule.index("}")], r"outline-offset: -\d+px", area)


class SmallText(unittest.TestCase):
    def test_the_writer_guide_badges_are_white_on_a_dark_chip(self):
        page = read("src", "pages", "contribute.njk")
        badge = re.search(r'<span class="rounded-md ([^"]*) px-1\.5 py-0\.5 text-\[0\.65rem\] font-bold uppercase ([^"]*)"', page)
        self.assertIsNotNone(badge)
        self.assertEqual((badge.group(1), badge.group(2)), ("bg-black/25", "text-white"))

    def test_the_magazine_tagline_takes_the_names_darker_tone(self):
        page = read("src", "pages", "index.njk")
        line = next(ln for ln in page.splitlines() if "home.lv_tagline" in ln)
        self.assertIn('class="home-mag-tagline ', line)
        self.assertNotIn("opacity-", line)
        css = read("src", "assets", "css", "areas", "home.css")
        self.assertIn(".home-mag-head h3, .home-mag-head .home-mag-tagline { color: color-mix(in srgb, var(--tone) 85%, var(--c-ink)); }", css)

    def test_the_shop_eyebrow_is_the_strong_orange(self):
        page = read("src", "pages", "shop.njk")
        self.assertIn('"shop.nav_bulk") | t(lang), tone: "text-lv-strong", id: "botm-title"', page)

    def test_the_instagram_scrim_is_dark_enough_at_the_words(self):
        css = read("src", "assets", "css", "areas", "home.css")
        rule = re.search(r"\.home-ig-meta\.has-pic \{ color: #fff; background: linear-gradient\(to top, rgb\(10 8 20 / ([\d.]+)\), "
                         r"rgb\(10 8 20 / ([\d.]+)\) 60%, transparent\); \}", css)
        self.assertIsNotNone(rule)
        self.assertGreaterEqual(float(rule.group(1)), 0.8)
        self.assertGreaterEqual(float(rule.group(2)), 0.55)


class Inputs(unittest.TestCase):
    def test_a_long_placeholder_ends_in_an_ellipsis(self):
        util = re.search(r"@utility input \{([^}]*)\}", read("src", "assets", "css", "main.css")).group(1)
        self.assertIn("text-ellipsis", util)


class OfflineCard(unittest.TestCase):
    RULE = (":root.js [data-pwa-saved]:has(> [data-pwa-saved-list]:empty):has(> [data-pwa-saved-empty][hidden])"
            ":has(> [data-pwa-saved-unsupported][hidden]) { min-height: 19.5rem; }")

    def test_the_card_keeps_the_empty_states_height_while_loading(self):
        self.assertIn(self.RULE, read("src", "assets", "css", "areas", "pwa.css"))

    def test_the_three_it_tests_are_the_cards_own_children(self):
        page = read("src", "pages", "offline.njk")
        card = page[page.index("data-pwa-saved\n"):]
        card = card[:card.index("</section>")]
        for marker in ("data-pwa-saved-unsupported hidden>", "data-pwa-saved-empty hidden>", 'data-pwa-saved-list></div>'):
            self.assertIn(marker, card)
        # (direct children: each sits on its own line at the card's first indent, not inside another box)
        for attr in ("data-pwa-saved-unsupported", "data-pwa-saved-empty", "data-pwa-saved-list"):
            self.assertRegex(card, r"\n    <(p|div) [^>]*" + attr)


class _Scan(HTMLParser):
    """Unfilled {placeholders} in the words and the plain attributes (not data-*, Alpine's or the scripts'); Alpine
    attributes inside an x-ignore element."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    PH = re.compile(r"\{[a-zA-Z_]\w*\}")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.skip, self.found, self.inside, self.roots, self.ignored = [], 0, [], [], 0, 0

    def handle_starttag(self, tag, attrs):
        ignored = any(i for _, i in self.stack)
        names = [a for a, _ in attrs]
        if ignored:
            self.ignored += 1
            self.inside += [f"<{tag} {a}>" for a in names if a.startswith(("x-", "@", ":"))]
        elif "x-ignore" in names:
            self.roots += 1
        if not self.skip:
            self.found += [f"{a}={v!r}" for a, v in attrs if v and not a.startswith(("data-", "x-", "@", ":")) and self.PH.search(v)]
        if tag in ("script", "style", "template"):
            self.skip += 1
        if tag not in self.VOID:
            self.stack.append((tag, ignored or "x-ignore" in names))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template") and self.skip:
            self.skip -= 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.skip and self.PH.search(data):
            self.found.append(data.strip()[:120])


class Built(unittest.TestCase):
    """/read/, /contribute/ and /offline/ in both languages, built for real."""

    tmp: Path | None = None

    @classmethod
    def setUpClass(cls):
        cls.pages = {}
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="r33-pages-"))
        env = {**os.environ, "ONLY": "read,contribute,offline", "PATH_PREFIX": "/", "I18N_STRICT": "1", "NODE_NO_WARNINGS": "1"}
        env.pop("STRICT_BUILD", None)
        cls.built = subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                                    "--output", str(cls.tmp / "site")], cwd=ROOT, env=env, capture_output=True, text=True,
                                   encoding="utf-8", timeout=600)
        for lang in ("", "es/"):
            for page in ("read", "contribute", "offline"):
                f = cls.tmp / "site" / lang / page / "index.html"
                if f.is_file():
                    cls.pages[f"/{lang}{page}/"] = f.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            self.skipTest("Node.js or the site's npm packages (npm ci) are missing")
        self.assertEqual(self.built.returncode, 0, self.built.stderr[-3000:])
        self.assertEqual(len(self.pages), 6, sorted(self.pages))

    def scan(self, path: str) -> _Scan:
        s = _Scan()
        s.feed(self.pages[path])
        return s

    def test_no_unfilled_placeholder(self):
        for path in self.pages:
            with self.subTest(path=path):
                self.assertEqual(self.scan(path).found, [])

    def test_the_recorder_writes_only_the_lines_a_rule_can_lead_to(self):
        for path in ("/contribute/", "/es/contribute/"):
            html = self.pages[path]
            spans = re.findall(r"<span x-show=\"pub === '(gv|lv)' (?:&&|&amp;&amp;) zone\(\) === '(\w+)'\"[^>]*>([^<]*)</span>", html)
            self.assertGreater(len(spans), 4, path)
            for pub, zone, words in spans:
                with self.subTest(path=path, pub=pub, zone=zone):
                    self.assertNotIn("{", words)
                    self.assertTrue(words.strip())

    def test_alpine_skips_the_read_story_lists_and_they_hold_no_directive(self):
        for path in ("/read/", "/es/read/"):
            s = self.scan(path)
            html = self.pages[path]
            with self.subTest(path=path):
                self.assertEqual(s.inside, [], "an Alpine directive inside x-ignore never runs")
                issues = len(re.findall(r'class="read-issue-in [^"]*" x-ignore>', html))
                rows = len(re.findall(r'<details class="read-past [^"]*" data-pub=', html))   # (not the x-for template's)
                bodies = len(re.findall(r'<div class="border-t border-line p-2 sm:p-3" x-ignore>', html))
                self.assertGreater(issues, 0)
                self.assertEqual(issues, html.count('class="read-issue-in '))
                self.assertEqual(bodies, rows)
                self.assertEqual(s.roots, issues + bodies)
                self.assertGreater(s.ignored, 1000, "the big story lists are the ones skipped")
        # the older issues' copy (an x-for template Alpine fills in) is NOT skipped
        src = read("src", "pages", "read.njk")
        tpl = src[src.index('<template x-for="is in older"'):]
        tpl = tpl[:tpl.index("\n      </template>\n    </div>")]
        self.assertIn('<div class="border-t border-line p-2 sm:p-3">', tpl)
        self.assertNotIn("x-ignore", tpl)

    def test_an_archive_rows_theme_may_wrap(self):
        for path in ("/read/", "/es/read/"):
            html = self.pages[path]
            topics = re.findall(r'<span class="meta-row mt-0\.5 text-sm text-muted">(<span[^>]*>)', html)
            with self.subTest(path=path):
                self.assertTrue(topics)
                for first in topics:
                    if 'lang="' in first:                     # (a row with a theme: its first item is the theme)
                        self.assertIn('class="whitespace-normal!"', first)
        src = read("src", "pages", "read.njk")
        self.assertIn('<span :lang="is.tl" class="whitespace-normal!" x-text="is.topic"></span>', src)


if __name__ == "__main__":
    unittest.main()
