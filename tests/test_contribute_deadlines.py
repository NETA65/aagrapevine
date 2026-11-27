"""Share your story's "Next story deadlines" card (src/pages/contribute.njk #next-deadlines, since November 2026: the
deadlines were nine screens down the page): right under the page nav, each magazine's next dated deadline — the date,
the days left (read.js keeps them current), its theme and issue, and "Add to my calendar" (Google, Outlook.com, the
.ics file) —, then "Subscribe to all deadlines": the story deadlines calendar (/deadlines.ics) as a webcal:// address,
Google Calendar's link and the how-to (#deadlines-calendar). A magazine without a dated deadline says so. A theme in
the card that is a machine translation (on /es/: Grapevine's) is marked as such, with the magazine's own title under
it, as in the rows further down. No backend.

The how-to section (#deadlines-calendar) is there only while a dated deadline is open, so the links to it from Home
("Story deadlines in my calendar") and from Stay updated ("Step-by-step help for each calendar app") are there only
then too — never a link to a section that is not on the page.

One build of /contribute/, Home and Stay updated (English and Spanish) from data of the test's own (SITE_DATA:
editorial.json), at a fixed moment; and the hero's card is now "Record your story" (the deadlines are not repeated
there).

    python -m unittest tests.test_contribute_deadlines -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_home import topic  # noqa: E402  (an editorial theme as scripts/sync/editorial.py writes it)

ROOT = Path(__file__).resolve().parents[1]
READ = json.loads((ROOT / "src" / "_i18n" / "read.json").read_text(encoding="utf-8"))
COMMON = json.loads((ROOT / "src" / "_i18n" / "common.json").read_text(encoding="utf-8"))
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))["site"]
NOW = "2026-11-26T15:00:00Z"

PAGES_JS = r"""
process.env.ONLY = "contribute.njk,deadlines-ics,index.njk,stay-updated";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-contrib-dl-"));
try {
  const pages = await new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" }).toJSON();
  const want = ["/contribute/", "/es/contribute/", "/", "/es/", "/stay-updated/", "/es/stay-updated/"];
  out(Object.fromEntries(pages.filter((p) => want.includes(p.url)).map((p) => [p.url, p.content])));
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""


def build(case, items):
    with tempfile.TemporaryDirectory(prefix="gv-contrib-dl-data-") as folder:
        Path(folder, "editorial.json").write_text(json.dumps({"updated": "2026-11-25T12:00:00Z", "items": items}), encoding="utf-8")
        return run_js(case, PAGES_JS, now=NOW, timeout=600, env={"SITE_DATA": folder, "WRITERS_ARCHIVE": ""})


def card(page: str) -> str:
    i = page.index('<section id="next-deadlines"')
    return page[i:page.index("</section>", i)]


def text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


# (Grapevine's next theme has a machine translation into Spanish, as scripts/sync/editorial.py writes it)
PRISON = dict(topic("ed:gv:2027-07", "Annual Prison Issue", "gv", "2026-12-01", issue_key="2027-07"),
              i18n={"title": {"en": "Annual Prison Issue", "es": "Edición anual sobre las prisiones"}}, machine=["es"])
BOTH = [PRISON,
        topic("ed:gv:2027-08", "Fun in Sobriety", "gv", "2027-01-01", issue_key="2027-08"),
        topic("ed:lv:2027-07:prisiones", "Prisiones", "lv", "2026-12-15", issue_key="2027-07"),
        topic("ed:lv:any:miedo", "Cómo trato con el miedo hoy", "lv")]
GV_ONLY = [BOTH[0], BOTH[1], BOTH[3]]
UNDATED = [topic("ed:lv:any:miedo", "Cómo trato con el miedo hoy", "lv"), topic("ed:lv:any:rezo", "Como rezo", "lv")]
CASES = {"both": BOTH, "gv": GV_ONLY, "undated": UNDATED}


class Card(unittest.TestCase):
    built: dict = {}

    def pages(self, name: str) -> dict:
        if name not in Card.built:
            Card.built[name] = build(self, CASES[name])
        return Card.built[name]

    def test_both_magazines_next_deadline(self):
        for url, lang, pre in (("/contribute/", "en", ""), ("/es/contribute/", "es", "/es")):
            page = self.pages("both")[url]
            c = card(page)
            with self.subTest(url=url):
                # right under the page nav, before "Why write"
                self.assertLess(page.index('class="page-nav'), page.index('<section id="next-deadlines"'))
                self.assertLess(page.index('<section id="next-deadlines"'), page.index('<section id="why"'))
                self.assertIn(READ["read.contrib.nd_title"][lang], text(c))
                rows = re.findall(r'<div class="p-5 sm:p-6 read-deadline-row" data-deadline-row data-deadline="([^"]+)"', c)
                # the page language's magazine first
                self.assertEqual(rows, ["2026-12-15", "2026-12-01"] if lang == "es" else ["2026-12-01", "2026-12-15"])
                self.assertEqual(c.count('<details class="cm-menu ct-dl-cal mt-3">'), 2, "Add to my calendar, each")
                self.assertEqual(len(re.findall(r'data-days-num data-lastmod="skip">(\d+)<', c)), 2)
                self.assertIn(">5<", c.replace(" ", ""))   # December 1 is 5 days after November 26
                feed = SITE["url"].rstrip("/") + pre + "/deadlines.ics"
                webcal = re.sub(r"^https?://", "webcal://", feed)
                self.assertIn(f'href="{webcal}"', c)
                self.assertIn(READ["read.contrib.nd_subscribe"][lang], text(c))
                gcal = [unquote(h) for h in re.findall(r'href="https://calendar\.google\.com/calendar/r\?cid=([^"]+)"', c)]
                self.assertEqual(gcal, [webcal])
                self.assertIn('href="#deadlines-calendar"', c)
                self.assertIn('href="#deadlines"', c)

    def test_a_magazine_without_a_dated_deadline(self):
        for url, lang in (("/contribute/", "en"), ("/es/contribute/", "es")):
            c = card(self.pages("gv")[url])
            with self.subTest(url=url):
                self.assertEqual(len(re.findall(r"data-deadline-row", c)), 1)
                self.assertIn(READ["read.contrib.aside_lv"][lang], text(c))
                self.assertIn(READ["read.contrib.nd_topics"][lang], text(c))

    def test_a_machine_translated_theme_says_so(self):
        es, en = card(self.pages("both")["/es/contribute/"]), card(self.pages("both")["/contribute/"])
        row = es[es.index('data-deadline="2026-12-01"'):]
        row = row[:row.index('<details class="cm-menu')]
        self.assertRegex(row, r'<span lang="es">Edición anual sobre las prisiones</span> <span class="auto-note align-middle" title="'
                         + re.escape(COMMON["common.auto_translated"]["es"]))
        self.assertIn(f'<span class="sr-only">{COMMON["common.auto_translated"]["es"]}</span>', row)
        self.assertIn('<p class="text-xs italic text-muted" lang="en">Annual Prison Issue</p>', row)
        # in English it is the magazine's own title: no mark, no second title; La Viña's, in Spanish, is its own too
        self.assertNotIn("auto-note", en)
        self.assertEqual(es.count("auto-note"), 1)

    def test_links_to_the_deadlines_calendar_only_while_it_is_there(self):
        for name, there in (("both", True), ("undated", False)):
            pages = self.pages(name)
            for lang, pre in (("en", ""), ("es", "/es")):
                with self.subTest(case=name, lang=lang):
                    self.assertEqual('id="deadlines-calendar"' in pages[pre + "/contribute/"], there)
                    home, stay = pages[pre + "/"], pages[pre + "/stay-updated/"]
                    self.assertEqual(f'href="{pre}/contribute/#deadlines-calendar"' in home, there, "Home")
                    self.assertEqual(f'href="{pre}/contribute/#deadlines-calendar"' in stay, there, "Stay updated")
                    # what stays: Home's line to the themes, and the calendar to subscribe to (it fills in by itself)
                    self.assertIn(f'href="{pre}/contribute/#deadlines"', home)
                    self.assertIn(f'data-copy="{SITE["url"].rstrip("/")}{pre}/deadlines.ics"', stay)

    def test_the_hero_card_is_record_your_story(self):
        page = self.pages("both")["/contribute/"]
        aside = page[page.index('aria-labelledby="ct-aside-title"'):]
        aside = aside[:aside.index("</section>")]
        self.assertIn(READ["read.contrib.aside_record_title"]["en"], text(aside))
        self.assertIn(READ["read.contrib.aside_record_text"]["en"], text(aside))
        self.assertNotIn("data-deadline", aside)


if __name__ == "__main__":
    unittest.main()
