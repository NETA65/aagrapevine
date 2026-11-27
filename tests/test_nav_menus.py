"""The menus since the UX review of November 2026 (src/_data/nav.js, partials/header.njk, partials/footer.njk):

  * Meetings  — a top link of its own (it was the first entry under Committee, where a newcomer looking for a meeting
                never looked), right after What's new; not repeated under Committee.
  * Words     — the GVR pages say what they are in the menus, in plain words ("Group reps (GVR/RLV)", "New rep
                orientation"; Spanish: "Representantes de grupo (RLV/GVR)", "Orientación para nuevos representantes"):
                `menuKey`, used by the header's dropdown, the phone menu and the footer — the pages keep their own names
                (their titles, breadcrumbs and site-search entries: `key`). No classroom words (AA's own wording: the
                orientation is sessions, never a course).
  * Order     — "Share your story", the one entry for any member, leads Get involved.
  * Phone     — the drawer is short: Home and the top links, then Get involved, Committee and More as three folded
                groups (<details>, so they open without JavaScript too); the group that holds the current page starts
                open.
  * Desktop   — nine entries fit beside the full site name from 1280px: 8px each side (12px from 1536px), never on two
                lines.

    python -m unittest tests.test_nav_menus -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COMMON = json.loads((ROOT / "src" / "_i18n" / "common.json").read_text(encoding="utf-8"))
CLASSROOM = re.compile(r"\b(lessons?|lecci[oó]n(es)?|trainers?|training|course|curso|class(es)?|clases?|capacitaci[oó]n)\b", re.I)


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class Data(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nav = None

    def setUp(self):
        if Data.nav is None:
            Data.nav = run_js(self, 'out((await imp("src/_data/nav.js")).default)', needs_modules=False)
        self.n = Data.nav

    def test_meetings_is_a_top_link(self):
        top = [(i.get("key"), i.get("url")) for i in self.n["primary"]]
        self.assertEqual(top[:2], [("nav.whats_new", "/whats-new/"), ("nav.meetings", "/meetings/")])
        committee = next(i for i in self.n["primary"] if i["key"] == "nav.committee")
        self.assertNotIn("/meetings/", [c["url"] for c in committee["children"]])
        self.assertEqual([c["url"] for c in committee["children"]], ["/events/", "/portfolio/", "/photos/", "/bulletin/", "/tracker/"])

    def test_share_your_story_first_and_the_plain_words(self):
        gi = next(i for i in self.n["primary"] if i["key"] == "nav.get_involved")
        self.assertEqual([c["url"] for c in gi["children"]], ["/contribute/", "/gvr/", "/orientation/", "/monthly/", "/digest/", "/published/"])
        menu = {c["url"]: c.get("menuKey") for c in gi["children"]}
        self.assertEqual(menu["/gvr/"], "nav.gvr_menu")
        self.assertEqual(menu["/orientation/"], "nav.orientation_menu")
        self.assertEqual(COMMON["nav.gvr_menu"], {"en": "Group reps (GVR/RLV)", "es": "Representantes de grupo (RLV/GVR)"})
        self.assertEqual(COMMON["nav.orientation_menu"], {"en": "New rep orientation", "es": "Orientación para nuevos representantes"})
        for k in ("nav.gvr_menu", "nav.orientation_menu"):
            for lang in ("en", "es"):
                self.assertIsNone(CLASSROOM.search(COMMON[k][lang]), COMMON[k][lang])
        # the pages keep their own names (titles, breadcrumbs, the site search)
        self.assertEqual(next(c for c in gi["children"] if c["url"] == "/gvr/")["key"], "nav.gvr")


class Templates(unittest.TestCase):
    def test_the_menus_use_the_menu_words(self):
        header, footer = read("src", "_includes", "partials", "header.njk"), read("src", "_includes", "partials", "footer.njk")
        self.assertIn("{{ (c.menuKey or c.key) | t(L) }}</span><span class=\"block text-xs text-muted\">", header)   # dropdown
        self.assertIn("{{ (c.menuKey or c.key) | t(L) }}</a>", header)                                              # drawer
        self.assertIn("{{ (c.menuKey or c.key) | t(L) }}</a></li>", footer)

    def test_a_short_phone_menu(self):
        header = read("src", "_includes", "partials", "header.njk")
        drawer = header[header.index('<template x-teleport="body">'):header.index("</template>")]
        self.assertEqual(drawer.count('<details class="site-drawer-group'), 1, "one loop over the three groups")
        self.assertIn('{% if pageKey in g.pages %} open{% endif %}', drawer)
        self.assertIn('groups.push({ key: "nav.more"', drawer)
        self.assertNotIn('<p class="eyebrow mt-4 mb-1 px-3">', drawer, "no long headed lists any more")

    def test_nine_entries_fit_from_1280px(self):
        header = read("src", "_includes", "partials", "header.njk")
        nav = header[header.index('<nav class="site-nav'):header.index("</nav>")]
        self.assertEqual(len(re.findall(r"whitespace-nowrap rounded-full px-2 text-sm 2xl:px-3", nav)), 2, "the dropdown buttons and the top links")


BUILT_JS = r"""
process.env.ONLY = "events.njk,gvr.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-nav-"));
try {
  const pages = await new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" }).toJSON();
  out(Object.fromEntries(pages.filter((p) => ["/events/", "/es/gvr/"].includes(p.url)).map((p) => [p.url, p.content])));
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""


class Built(unittest.TestCase):
    def test_the_drawer_on_two_pages(self):
        p = run_js(self, BUILT_JS, timeout=600)
        for url, open_group in (("/events/", "Committee"), ("/es/gvr/", "Participa")):
            page = p[url]
            drawer = page[page.index('id="mobile-drawer"'):]
            drawer = drawer[:drawer.index("</nav>")]
            groups = re.findall(r'<details class="site-drawer-group group/dg mt-1"( open)?>\s*<summary[^>]*>.*?<span class="min-w-0 flex-1">([^<]+)</span>', drawer, re.S)
            with self.subTest(url=url):
                self.assertEqual(len(groups), 3)
                self.assertEqual([g for o, g in groups if o], [open_group], "the group that holds the page starts open")
                top = re.findall(r'<a href="[^"]+" class="flex min-h-11 items-center gap-3 rounded-xl px-3 font-semibold', drawer)
                self.assertEqual(len(top) + len(groups), 11, "Home, seven top links and three groups")
        es = p["/es/gvr/"]
        self.assertIn("Representantes de grupo (RLV/GVR)", es)
        self.assertIn('href="/es/meetings/"', es[es.index('<nav class="site-nav'):es.index("</nav>", es.index('<nav class="site-nav'))])


if __name__ == "__main__":
    unittest.main()
