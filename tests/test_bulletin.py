"""The Bulletin (/bulletin/, the committee's notices; it was /announcements/ until 2026-09).

Any Markdown file dropped in content/bulletin must read well on the page:
  * a post without a header gets its title from its first heading or its file name, and its date from
    the date its name starts with (else the day it first appears);
  * HTML pasted into a post becomes Markdown, scripts go (scripts/sync/announcements.py tidy_html);
  * pictures and documents saved next to the posts are linked at /bulletin/files/;
  * the post's own headings start one level under its title (eleventy.config.js `md`, option h);
  * the Drive folder may be called bulletin / boletín (or the older announcements / anuncios);
  * the old /announcements/ address keeps working (src/pages/announcements-redirect.njk).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import common  # noqa: E402

try:
    from nodejs import run_js  # tests/ is on sys.path under "unittest discover -s tests"
except ImportError:  # pragma: no cover — run from another folder
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from nodejs import run_js


class Folder(unittest.TestCase):
    """A temporary content/bulletin (and data/raw) for each test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-bulletin-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dir = self.tmp / "bulletin"
        self.dir.mkdir()
        (self.tmp / "events").mkdir()
        (self.tmp / "raw").mkdir()
        for obj, name, val in ((A, "ANN_DIR", self.dir), (A, "EVENTS_DIR", self.tmp / "events"),
                               (A, "LEGACY_ANN_DIR", self.tmp / "announcements"), (common, "RAW_DIR", self.tmp / "raw")):
            p = mock.patch.object(obj, name, val)
            p.start()
            self.addCleanup(p.stop)

    def write(self, name: str, text: str, encoding: str = "utf-8") -> Path:
        p = self.dir / name
        p.write_text(text, encoding=encoding)
        return p

    def parse(self, name: str, text: str) -> dict:
        return A.parse_announcement(self.write(name, text))

    def run_sync(self) -> dict:
        A.main([])
        return json.loads((self.tmp / "raw" / "announcements.json").read_text(encoding="utf-8"))


class NoHeader(Folder):
    def test_title_from_the_first_heading(self):
        it = self.parse("welcome.md", "# Welcome, **new** GVRs!\n\nCome to our meeting.\n\n## Details\n\nSoon.")
        self.assertEqual(it["title"], "Welcome, new GVRs!")
        self.assertEqual(it["extra"]["body_md"], "Come to our meeting.\n\n## Details\n\nSoon.")  # heading taken out once
        self.assertEqual(it["url"], "/bulletin/#welcome")
        self.assertEqual(it["extra"]["file"], "content/bulletin/welcome.md")

    def test_title_from_an_underlined_first_line(self):
        it = self.parse("x.md", "Literature table volunteers\n===\n\nWe need two volunteers.")
        self.assertEqual((it["title"], it["extra"]["body_md"]), ("Literature table volunteers", "We need two volunteers."))

    def test_a_later_section_heading_is_not_the_title(self):
        it = self.parse("2027-01-10-welcome-new-GVRs.md", "Thank you all.\n\n## Details\n\n- one\n- two")
        self.assertEqual(it["title"], "Welcome new GVRs")           # the file name, its capitals kept
        self.assertIn("## Details", it["extra"]["body_md"])
        # … but a "# " heading after a picture is the title
        it = self.parse("flyer-first.md", "![Flyer](https://x.org/f.png)\n\n# Spring Assembly\n\nSee you there.")
        self.assertEqual(it["title"], "Spring Assembly")

    def test_date_from_the_name_else_the_day_it_first_appears(self):
        self.assertEqual(self.parse("2027-01-10-welcome.md", "Hi.")["date"], "2027-01-10")
        self.write("no-date.md", "Just text, no header, no heading.")
        self.write("2027-02-03 Spring Assembly.md", "Hello.")
        env = self.run_sync()
        by = {i["extra"]["slug"]: i for i in env["items"]}
        self.assertEqual(by["no-date"]["title"], "No date")
        self.assertEqual(by["no-date"]["date"], by["no-date"]["first_seen"][:10])
        self.assertEqual((by["2027-02-03-spring-assembly"]["title"], by["2027-02-03-spring-assembly"]["date"]),
                         ("Spring Assembly", "2027-02-03"))

    def test_a_header_title_is_not_repeated_by_the_text(self):
        it = self.parse("botm.md", "---\ntitle: Book of the Month is here\n---\n# Book of the Month is here\n\nOn sale now.")
        self.assertEqual(it["extra"]["body_md"], "On sale now.")

    def test_a_file_saved_as_windows_1252_is_read(self):
        p = self.write("octubre.md", "# Reunión de octubre\r\n\r\n¡Te esperamos!\r\n", encoding="cp1252")
        it = A.parse_announcement(p)
        self.assertEqual((it["title"], it["extra"]["body_md"], it["lang"]), ("Reunión de octubre", "¡Te esperamos!", "es"))


class PastedHtml(unittest.TestCase):
    def test_html_becomes_markdown_and_scripts_go(self):
        md = A.tidy_html('<p>Hello <b>all</b><!-- note --></p><script>alert("x")</script>\n'
                         '<a href="https://neta65.org" onclick="x()">the <i>site</i></a><br>next\n'
                         '<ul><li>one</li><li>two</li></ul><img src="flyer.jpg" alt="Flyer" onerror="x()">\n'
                         '<iframe src="https://evil.example"></iframe><h2>More</h2>')
        self.assertNotIn("<", md)
        for bit in ("Hello **all**", "[the *site*](https://neta65.org)\nnext", "- one\n- two", "![Flyer](flyer.jpg)", "## More"):
            self.assertIn(bit, md)
        for gone in ("alert", "note", "evil", "onclick", "onerror"):
            self.assertNotIn(gone, md)

    def test_pictures_and_links_that_cannot_work(self):
        # an e-mail's inline signature picture, a bare "x", a javascript: link: never a broken picture or
        # a literal "[click me](javascript:…)" — the words stay, and the pictures are reported
        dropped: list[str] = []
        md = A.tidy_html('Hi <img src="cid:image001.png@01DA0000" alt="Signature logo"> <img src=x onerror=alert(1)> '
                         '<a href="javascript:alert(1)">click me</a> <a href="mailto:gv@x.org">mail</a> '
                         '<a href="/events/">events</a> <img src="//cdn.x.org/a.png" alt="web"> <img src="Flyer.JPG" alt="f">', dropped)
        self.assertEqual(md, "Hi *Signature logo*  click me [mail](mailto:gv@x.org) [events](/events/) ![web](//cdn.x.org/a.png) ![f](Flyer.JPG)")
        self.assertEqual(dropped, ["image001.png", "x"])

    def test_what_is_not_html_stays(self):
        text = "The <Panel 77> folder, <https://x.org> and `<b>code</b>`.\n```\n<div>kept</div>\n```"
        self.assertEqual(A.tidy_html(text), text)
        self.assertEqual(A.tidy_html("<b>Bold</b> `<b>x</b>`\n```\n<i>y</i>\n```"), "**Bold** `<b>x</b>`\n```\n<i>y</i>\n```")
        self.assertEqual(A.tidy_html("| a | b<br>c |"), "| a | b c |")      # a row stays one row

    def test_a_teaser_is_prose(self):
        self.assertEqual(A.markdown_to_text("Intro.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- one\n    - two\n\n---\nEnd."),
                         "Intro. one two End.")


class TitlesAndOldFolder(Folder):
    def test_a_title_pasted_with_tags_is_text(self):
        it = self.parse("t.md", "---\ntitle: 'Pasted from an e-mail: <b>bold</b> & \"quotes\"'\n---\nText")
        self.assertEqual(it["title"], 'Pasted from an e-mail: bold & "quotes"')

    def test_a_post_in_the_old_folder_still_shows(self):
        old = self.tmp / "announcements"
        old.mkdir()
        (old / "2026-09-26-old-folder.md").write_text("# Old folder post\n\nHello.", encoding="utf-8")
        (old / "same.md").write_text("# The old copy", encoding="utf-8")
        self.write("same.md", "# The new copy")
        env = self.run_sync()
        titles = sorted(i["title"] for i in env["items"])
        self.assertEqual(titles, ["Old folder post", "The new copy"])     # the one in bulletin/ wins
        errors = " ".join(env["stats"]["errors"])
        self.assertIn("announcements/2026-09-26-old-folder.md: the folder is now content/bulletin/", errors)
        self.assertIn("announcements/same.md: a post of the same name is in content/bulletin/", errors)


class Attachments(Folder):
    def test_pictures_and_documents_next_to_the_post(self):
        (self.dir / "Spring Flyer.JPG").write_bytes(b"\xff\xd8")
        (self.dir / "Sign-up form.pdf").write_bytes(b"%PDF")
        self.write("2027-03-01-assembly.md",
                   "---\nimage: spring flyer.jpg\nurl: Sign-up form.pdf\n---\n# Spring Assembly\n\n"
                   "![Flyer](<Spring Flyer.JPG>) [the form](Sign-up%20form.pdf) [web](https://x.org/a.pdf)\n"
                   "![Gone](gone.png) and [missing](missing.pdf)\n```\n![x](Sign-up form.pdf)\n```")
        (self.dir / "notes.txt").write_text("not a post", encoding="utf-8")
        env = self.run_sync()
        it = env["items"][0]
        body = it["extra"]["body_md"]
        self.assertIn("![Flyer](/bulletin/files/Spring%20Flyer.JPG)", body)
        self.assertIn("[the form](/bulletin/files/Sign-up%20form.pdf)", body)
        self.assertIn("[web](https://x.org/a.pdf)", body)
        self.assertIn("*Gone* and missing", body)                    # never a broken picture on the page
        self.assertIn("```\n![x](Sign-up form.pdf)\n```", body)       # code is left alone
        self.assertEqual(it["image"], "/bulletin/files/Spring%20Flyer.JPG")
        self.assertEqual(it["extra"]["link"], "/bulletin/files/Sign-up%20form.pdf")
        self.assertEqual(it["url"], "/bulletin/#2027-03-01-assembly")   # a file link is the button, not the item
        self.assertNotIn("missing_files", it["extra"])
        errors = " ".join(env["stats"]["errors"])
        self.assertIn("gone.png", errors)
        self.assertIn("missing.pdf", errors)
        self.assertIn("notes.txt: ignored", errors)                   # other files are still reported …
        self.assertNotIn("Flyer.JPG: ignored", errors)                # … the post's own files are not
        self.assertEqual(env["stats"]["problems"], 3)


class Place(unittest.TestCase):
    def test_the_folder_its_help_and_the_example(self):
        self.assertEqual(A.ANN_DIR, common.CONTENT_DIR / "bulletin")
        self.assertFalse((common.CONTENT_DIR / "announcements").exists())
        for name in ("README.md", "_example.md"):
            self.assertTrue((A.ANN_DIR / name).is_file(), name)
        self.assertNotIn("_example.md", [p.name for p in A.content_files(A.ANN_DIR)])   # never published
        it = A.parse_announcement(A.ANN_DIR / "_example.md")        # … but it is a valid post
        self.assertEqual((it["title"], it["date"], it["extra"]["pinned"]), ("Welcome, new GVRs and RLVs!", "2027-01-10", True))
        self.assertEqual(it["extra"]["own_i18n"]["title"], {"es": "¡Bienvenidos, nuevos RLV y GVR!"})

    def test_drive_folder_names(self):
        from scripts.sync.drive import category_for
        for name in ("bulletin", "Bulletin", "Boletín", "BOLETIN 2027", "boletines", "Bulletin Board",
                     "announcements", "Anuncios"):
            self.assertEqual(category_for(name), "announcements", name)

    def test_pages_and_the_old_address(self):
        stub = (ROOT / "src/pages/announcements-redirect.njk").read_text(encoding="utf-8")
        self.assertIn("announcements/index.html", stub)
        self.assertIn('"/bulletin/" | lurl(lang)', stub)
        for bit in ("location.search + location.hash", 'name="robots" content="noindex"', 'rel="canonical"',
                    "sitemap: false", "eleventyExcludeFromCollections: true"):
            self.assertIn(bit, stub)
        page = (ROOT / "src/pages/bulletin.njk").read_text(encoding="utf-8")
        self.assertIn("bulletin/index.html", page)
        self.assertRegex(page, r"(?m)^pageKey: bulletin$")
        self.assertFalse((ROOT / "src/pages/announcements.njk").exists())
        nav = (ROOT / "src/_data/nav.js").read_text(encoding="utf-8")
        self.assertIn('url: "/bulletin/"', nav)
        self.assertNotIn('url: "/announcements/"', nav)
        common_i18n = json.loads((ROOT / "src/_i18n/common.json").read_text(encoding="utf-8"))
        self.assertEqual(common_i18n["nav.bulletin"], {"en": "Bulletin", "es": "Boletín"})
        self.assertEqual(common_i18n["nav.share"], {"en": "QR Post", "es": "Cartel QR"})
        # the footer: QR Post in "Stay updated", right after Instagram
        stay = re.findall(r'key: "(nav\.\w+)"[^}]*group: "stay"', nav)
        self.assertEqual(stay, ["nav.instagram", "nav.share"])


class Rendering(unittest.TestCase):
    """eleventy.config.js `md`: the post's headings under its title, links to our pages in the page's
    language, tables in a box of their own, raw HTML never rendered."""

    def test_headings_links_tables(self):
        out = run_js(self, """
          const md = filters.md;
          out({
            h: md("# One\\n\\n## Two\\n\\n#### Four", { h: 3 }),
            top2: md("## Two\\n\\n### Three", { h: 3 }),
            deep: md("# a\\n\\n## b\\n\\n### c\\n\\n###### f", { h: 5 }),
            jumps: md("## Starts at two\\n\\n#### Jumps to four\\n\\n###### Six\\n\\n# Back to one\\n\\n### Three", { h: 3 }),
            plain: md("# One"),
            es: md("[e](/events/#x) [f](/bulletin/files/a.pdf) [w](https://x.org/) [s](/es/gvr/)", { lang: "es" }),
            en: md("[e](/events/)", { lang: "en" }),
            table: md("| a | b |\\n|---|---|\\n| 1 | 2 |", { lang: "es" }),
            named: md("| a |\\n|---|\\n| 1 |\\n\\ntext\\n\\n| b |\\n|---|\\n| 2 |", { lang: "en", name: "Reminder: Assembly" }),
            html: md('<script>alert(1)</script> <img src=x onerror=alert(1)> [j](javascript:alert(1))'),
          });
        """)
        self.assertIn("<h3>One</h3>", out["h"])
        self.assertIn("<h4>Two</h4>", out["h"])
        self.assertIn("<h5>Four</h5>", out["h"])                     # one level under "Two", never two
        self.assertIn("<h3>Two</h3>", out["top2"])                   # no level skipped under the title
        self.assertIn("<h4>Three</h4>", out["top2"])
        self.assertIn("<h6>c</h6>", out["deep"])                      # never past h6
        self.assertIn("<h6>f</h6>", out["deep"])
        # a text that jumps between levels: each heading at most one level under the one before it
        self.assertEqual(re.findall(r"<(h\d)>", out["jumps"]), ["h3", "h4", "h5", "h3", "h4"])
        self.assertIn("<h1>One</h1>", out["plain"])                   # without the option: as written
        self.assertIn('href="/es/events/#x"', out["es"])
        self.assertIn('href="/bulletin/files/a.pdf"', out["es"])      # a file is the same in both languages
        self.assertIn('href="https://x.org/"', out["es"])
        self.assertIn('href="/es/gvr/"', out["es"])
        self.assertIn('href="/events/"', out["en"])
        self.assertRegex(out["table"], r'<div class="md-table" role="region" tabindex="0" aria-label="Tabla"><table>')
        # a post's tables are named after it, one by one (never two regions of the same name on a page)
        self.assertEqual(re.findall(r'aria-label="([^"]+)"', out["named"]), ["Table 1 · Reminder: Assembly", "Table 2 · Reminder: Assembly"])
        self.assertNotIn("<script", out["html"])
        self.assertNotIn("<img", out["html"])
        self.assertNotIn('href="javascript:', out["html"])


if __name__ == "__main__":
    unittest.main()
