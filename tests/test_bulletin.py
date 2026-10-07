"""The Bulletin (/bulletin/, the committee's notices; it was /announcements/ until 2026-09).

Any Markdown file dropped in content/bulletin must read well on the page:
  * a post without a header gets its title from its first heading or its file name, and its date from
    the date its name starts with (else the day it first appears);
  * HTML pasted into a post becomes Markdown, scripts go (scripts/sync/announcements.py tidy_html);
  * pictures and documents saved next to the posts are linked at /bulletin/files/;
  * the post's own headings start one level under its title (eleventy.config.js `md`, option h), each with an
    id of its own (option ids), listed beside a wide post as "In this post" (`mdToc`, bulletin.njk);
  * every post has a row of its own, at every width — never two side by side (a long post beside a short one
    was a half-width card without "In this post", next to an empty column) — and on a desktop it uses the
    card's width: its text and its aside (In this post, the actions) side by side, by the card's own width
    (committee.css container cm-ann). The home page's teasers stay two a row, and the one left takes the whole
    row when the other ends between builds (GV.expire hides it);
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
# app.js on a stand-in page (Node.js vm): el(), page() — for GV.copy's "Copied!" (Layout)
from test_app_expire import js as app_js  # noqa: E402


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
        # its day in Central time (first_seen is UTC: from 7 PM Central on, the UTC date is already the next day)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        seen = datetime.fromisoformat(by["no-date"]["first_seen"].replace("Z", "+00:00"))
        self.assertEqual(by["no-date"]["date"], seen.astimezone(ZoneInfo("America/Chicago")).date().isoformat())
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
    def test_the_folder(self):
        self.assertEqual(A.ANN_DIR, common.CONTENT_DIR / "bulletin")
        # a file whose name starts with "_" (the folder's example) is never published
        with tempfile.TemporaryDirectory() as d:
            for name in ("_example.md", "2027-01-10-x.md", "README.md"):
                Path(d, name).write_text("---\ntitle: X\n---\nx\n", encoding="utf-8")
            self.assertEqual([p.name for p in A.content_files(Path(d))], ["2027-01-10-x.md"])

    def test_the_folder_its_help_and_the_example(self):
        # the committee's folder as it is (content/bulletin: its README and its example) — left to the Code check
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

    def test_a_plain_text_drive_post_has_no_open_the_document(self):
        # A .md / .txt file from the Drive bulletin folder is shown in full on the page: "Open the document"
        # would only open the same words as raw text on Drive. PDFs, pictures, Google Docs and .docx keep it.
        page = (ROOT / "src/pages/bulletin.njk").read_text(encoding="utf-8")
        rule = re.search(r"\{%- set plainText = (.+?) -%\}", page)
        self.assertIsNotNone(rule)
        for bit in ('a.source == "drive"', "a.extra.body_md", 'a.extra.file_type == "MD"', 'a.extra.file_type == "TXT"',
                    '(a.extra.mime or "").startsWith("text/")'):
            self.assertIn(bit, rule.group(1))
        self.assertIn('(a.url if (a.source == "drive" and a.url and not plainText) else "")', page)


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

    def test_an_events_description_like_a_post(self):
        """An event's description on /events/ (a content/events file's text) is committee Markdown too: under
        the card's h3 title its headings start at h4, links to our pages lead to the page language's page, its
        tables are named after the event, and .cm-md (committee.css) styles it as on the bulletin."""
        page = (ROOT / "src/pages/events.njk").read_text(encoding="utf-8")
        m = re.search(r'<div class="([^"]*)"[^>]*>\{\{ ev\.body \| md(\([^)]*\))? \| safe \}\}</div>', page)
        self.assertIsNotNone(m)
        self.assertIn("cm-md", m.group(1).split())
        self.assertEqual(re.sub(r"\s+", "", m.group(2) or ""), "({h:4,lang:lang,name:ev.title})")
        self.assertRegex(page, r'<h3 class="h-card[^"]*">\s*\{%-? if ev\.link')        # the card's title
        out = run_js(self, """
          out(filters.md("Aprende.\\n\\n## Estacionamiento\\n\\nVer [reuniones](/meetings/).\\n\\n| Hora | Qué |\\n|---|---|\\n| 2:00 | Bienvenida |",
                         { h: 4, lang: "es", name: "Taller de Escritura" }));
        """)
        self.assertIn("<h4>Estacionamiento</h4>", out)
        self.assertIn('href="/es/meetings/"', out)
        self.assertIn('aria-label="Tabla 1 · Taller de Escritura"', out)

    def test_section_ids_and_in_this_post(self):
        """Option ids: every heading gets "<ids>--<its words>" (accents and marks dropped, the same words again
        "-2"), and `mdToc` — given the same { h, ids } — lists the sections with exactly those ids: the top-level
        headings, or the ones under a lone top heading; fewer than two sections, nothing. Without the option
        (events, the home page) no heading gets an id."""
        out = run_js(self, r"""
          const text = "Intro\n\n# Why it **matters**\n\nx\n\n## Sub `code`\n\n# Why it matters\n\n# Él ñandú: ¿qué?";
          out({
            html: filters.md(text, { h: 3, ids: "ann-x" }),
            toc: filters.mdToc(text, { h: 3, ids: "ann-x" }),
            under: filters.mdToc("# Details\n\n## Parking\n\n## Food", { h: 3, ids: "p" }),
            one: filters.mdToc("# Only one\n\ntext\n\n## And one under it", { h: 3, ids: "p" }),
            none: filters.mdToc("Just text", { h: 3, ids: "p" }),
            empty: filters.mdToc("", { h: 3, ids: "p" }),
            plain: filters.md("# A\n\n## B", { h: 4, lang: "es", name: "Taller" }),
          });
        """)
        ids = re.findall(r'<h\d id="([^"]+)"', out["html"])
        self.assertEqual(ids, ["ann-x--why-it-matters", "ann-x--sub-code", "ann-x--why-it-matters-2", "ann-x--el-nandu-que"])
        self.assertIn('<h3 id="ann-x--why-it-matters">Why it <strong>matters</strong></h3>', out["html"])
        self.assertIn('<h4 id="ann-x--sub-code">', out["html"])                          # levels as before
        self.assertEqual(out["toc"], [{"id": "ann-x--why-it-matters", "text": "Why it matters"},
                                      {"id": "ann-x--why-it-matters-2", "text": "Why it matters"},
                                      {"id": "ann-x--el-nandu-que", "text": "Él ñandú: ¿qué?"}])
        self.assertTrue(all(e["id"] in ids for e in out["toc"]))                       # each link finds its heading
        self.assertEqual([e["text"] for e in out["under"]], ["Parking", "Food"])
        self.assertEqual((out["one"], out["none"], out["empty"]), ([], [], []))
        self.assertNotIn(" id=", out["plain"])

    def test_a_translation_keeps_the_originals_ids(self):
        """Option idsFrom (the post in its own language): a translation with as many headings takes the ids of
        the original's headings, one by one — so "#ann-x--why-it-matters" finds its section on the Spanish page
        too (a shared link, or the language switch, which keeps the #) — while its words stay its own. With a
        different number of headings the translation's own words name them (never a wrong section)."""
        out = run_js(self, r"""
          const en = "Intro\n\n# Why it matters\n\nx\n\n# What groups can do\n\ny";
          const es = "Intro\n\n# Por qué importa\n\nx\n\n# Lo que pueden hacer los grupos\n\ny";
          const opts = { h: 3, ids: "ann-x", idsFrom: en };
          out({
            html: filters.md(es, opts),
            toc: filters.mdToc(es, opts),
            own: filters.mdToc(en, opts),
            fewer: filters.mdToc(es + "\n\n# Una más", opts),
          });
        """)
        self.assertEqual(re.findall(r'<h3 id="([^"]+)">', out["html"]), ["ann-x--why-it-matters", "ann-x--what-groups-can-do"])
        self.assertEqual(out["toc"], [{"id": "ann-x--why-it-matters", "text": "Por qué importa"},
                                      {"id": "ann-x--what-groups-can-do", "text": "Lo que pueden hacer los grupos"}])
        self.assertEqual([e["id"] for e in out["own"]], [e["id"] for e in out["toc"]])        # the same on both pages
        self.assertEqual([e["id"] for e in out["fewer"]], ["ann-x--por-que-importa", "ann-x--lo-que-pueden-hacer-los-grupos", "ann-x--una-mas"])

    def test_the_real_post_lists_its_sections(self):
        """The bulletin's posts as synced (data/site/announcements.json — the daily bot's data, so only what the
        code promises for ANY post): on the English and the Spanish page, ids that are valid fragment ids
        (letters, digits, dashes), each link of "In this post" finding its heading in that page's text — and,
        given the original as idsFrom (as bulletin.njk does), the same ids on both pages when both texts have as
        many headings (a machine translation does; a chair's own Spanish text, `summary_es`, may not — its own
        words name its sections then), the same list when they also sit at the same levels."""
        items = json.loads((ROOT / "data/site/announcements.json").read_text(encoding="utf-8")).get("items") or []
        posts = [it for it in items if (it.get("extra") or {}).get("body_md")]
        if not posts:
            self.skipTest("no bulletin post with a text right now")
        pairs = [[it["extra"]["body_md"], ((it.get("i18n") or {}).get("body_md") or {}).get("es") or it["extra"]["body_md"]]
                 for it in posts]
        res = run_js(self, """
          out(input.map(([original, es]) => [original, es].map((t) => {
            const opts = { h: 3, ids: "ann-x", idsFrom: original };
            return { toc: filters.mdToc(t, opts), html: filters.md(t, opts) };
          })));
        """, data=pairs)
        for out in res:
            heads = [re.findall(r'<h(\d) id="([^"]+)"', page["html"]) for page in out]
            for page, hs in zip(out, heads):
                for e in page["toc"]:
                    self.assertRegex(e["id"], r"^ann-x--[a-z0-9]+(-[a-z0-9]+)*$")
                    self.assertTrue(e["text"].strip())
                    self.assertIn(e["id"], [i for _, i in hs])                   # each link finds its heading
            if len(heads[0]) == len(heads[1]):
                self.assertEqual([i for _, i in heads[0]], [i for _, i in heads[1]])
                if [lv for lv, _ in heads[0]] == [lv for lv, _ in heads[1]]:
                    self.assertEqual([e["id"] for e in out[0]["toc"]], [e["id"] for e in out[1]["toc"]])


class Layout(unittest.TestCase):
    """/bulletin/: one post per row at every width, and on a wide screen each post uses the whole card — its text
    and its aside ("In this post" and the actions) side by side, decided by the CARD's width (a size container
    per list item), so phones (and larger text on a laptop) keep the actions bar under the text. The aside comes
    after the text in the page (reading and Tab order); the post anchors and the expiry attributes stay where
    shared links, QR codes and GV.expire look for them."""

    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "src/pages/bulletin.njk").read_text(encoding="utf-8")
        cls.css = (ROOT / "src/assets/css/areas/committee.css").read_text(encoding="utf-8")
        cls.main = (ROOT / "src/assets/css/main.css").read_text(encoding="utf-8")
        cls.js = (ROOT / "src/assets/js/committee.js").read_text(encoding="utf-8")

    def test_the_post_markup(self):
        p = self.page
        # the text gets its section ids from the post's own anchor, in the words of the post's own language (the
        # same ids on both pages); "Show original" none (no duplicate ids); the list is given the same options
        self.assertIn("{%- set original = (a.extra.body_md if a.extra) or a.summary -%}", p)
        self.assertIn("{{ body | md({ h: 3, lang: lang, name: title, ids: a._anchor, idsFrom: original }) | safe }}", p)
        self.assertIn('{%- set toc = body | mdToc({ h: 3, ids: a._anchor, idsFrom: original }) -%}', p)
        self.assertEqual(p.count("ids: a._anchor"), 2)
        self.assertLess(p.index("{%- set original ="), p.index("{%- set toc ="))
        # anchors for shared links / QR codes, the expiry item
        self.assertRegex(p, r'<article id="\{\{ a\._anchor \}\}" class="card cm-ann[^"]*"[^>]*aria-labelledby="\{\{ a\._anchor \}\}-h"')
        self.assertIn('<li class="min-w-0" data-gv-expire-item', p)
        # DOM order: the text, then the aside (In this post, then the actions) — a <div>: no landmark inside the
        # page's named section (test_accessibility.Landmarks)
        body, side, toc, actions = (p.index('class="cm-ann-main"'), p.index('<div class="cm-ann-side">'),
                                    p.index('class="cm-ann-toc"'), p.index('class="cm-ann-actions"'))
        self.assertLess(body, side)
        self.assertLess(side, toc)
        self.assertLess(toc, actions)
        self.assertLess(p.index("</details>"), side)                    # "Show original" stays with the text
        nav = re.search(r'<nav class="cm-ann-toc" ([^>]*)>', p).group(1)
        self.assertIn('aria-labelledby="{{ a._anchor }}-toc {{ a._anchor }}-h"', nav)   # unique name per post
        self.assertIn('{%- if toc | length %}', p)
        self.assertIn('<li><a href="#{{ s.id }}">{{ s.text }}</a></li>', p)
        for bit in ('data-copy="{{ pageAbs }}#{{ a._anchor }}"', 'data-share="{{ pageAbs }}#{{ a._anchor }}"', '"committee.ann.in_post"'):
            self.assertIn(bit, p)
        strings = json.loads((ROOT / "src/_i18n/committee.json").read_text(encoding="utf-8"))
        self.assertEqual(strings["committee.ann.in_post"], {"en": "In this post", "es": "En esta publicación"})

    def test_one_post_per_row(self):
        """Every post has the whole row, at every width — never two side by side: from 1280px the live site put a
        long post in a half-width card without "In this post", beside an empty column as tall as it under the
        short pinned post. So the list is one column in every media query, the page does not count its posts for
        the layout (the old is-multi) and no rule waits for one of two to expire (:has()); GV.expire still hides
        a post whose day is over — its row goes — and shows the visitors' card once none is left."""
        css, page = self.css, self.page
        self.assertIn('<ol class="cm-ann-list" data-gv-expire-list data-gv-expire-empty="#ann-empty">', page)
        self.assertIn('<div id="ann-empty" class="cm-ann-empty is-solo"{% if anns | length %} hidden{% endif %}>', page)
        rules = re.findall(r"\.cm-ann-list([^{]*)\{([^}]*)\}", css)
        self.assertEqual([r for r in rules if "grid-template-columns" in r[1]],
                         [(" ", " display: grid; gap: 1.5rem; grid-template-columns: minmax(0, 1fr); ")])
        for gone in ("is-multi", ":has(> li:not([hidden])"):
            self.assertNotIn(gone, css)
            self.assertNotIn(gone, page)

    def test_the_card_decides(self):
        css = self.css
        self.assertIn(".cm-ann-list > li { container: cm-ann / inline-size; }", css)
        th = {float(x) for x in re.findall(r"@container cm-ann \(width >= ([\d.]+)rem\)", css)}
        self.assertEqual(len(th), 1, "one threshold for the side-by-side layout (and its Copy link look)")
        side = th.pop() * 16
        # every post has the whole row: the page container less its gutters (main.css container-page, --gutter).
        # At 1024px (even with a 17px scrollbar) that is wide enough for the side-by-side layout, on a tablet in
        # portrait (768px) it is not — at 100 % text (larger text raises the threshold: rem in the query)
        def gutter(w): return min(max(16, 0.035 * w), 72)
        self.assertLessEqual(side, (1024 - 17) - 2 * gutter(1024 - 17))
        self.assertGreater(side, 768 - 2 * gutter(768))
        # the side-by-side layout is for screens: on paper a post is the narrow card
        self.assertRegex(css, r"@media screen \{\s*@container cm-ann \(width >= [\d.]+rem\) \{\s*\.cm-ann \{ display: grid;")
        # In this post: hidden on a narrow card, shown beside the text; the aside sticks like sticky-aside
        self.assertIn(".cm-ann-toc { display: none; }", css)
        block = css[css.index("@container cm-ann (width >= "):css.index("/* \"In this post\": its label")]
        for bit in (".cm-ann-toc { display: block; }", "@media (height >= 40rem)", "position: sticky; top: var(--sticky-top);",
                    "max-height: calc(100dvh - var(--sticky-top) - 1rem - var(--sticky-bottom, 0px)); overflow-y: auto;"):
            self.assertIn(bit, block)
        # the one being read is marked by more than colour (the rail's bar, a band), never by a bolder label (it
        # could wrap differently and move the list while the page scrolls); 44px links on a touch screen
        current = re.search(r"\.cm-ann-toc-list a\[aria-current\] \{([^}]*)\}", css).group(1)
        for bit in ("color: var(--c-gv);", "border-left-color: var(--c-gv);", "background: var(--c-gv-soft);"):
            self.assertIn(bit, current)
        self.assertNotIn("font-weight", current)
        self.assertIn("@media (pointer: coarse) { .cm-ann-toc-list a { min-height: 2.75rem; } }", css)
        # forced colours (Windows High Contrast) paint every link's edge and drop the band: there only the
        # current one keeps a visible edge (Highlight), and an underline
        forced = re.search(r"@media \(forced-colors: active\) \{\s*\.cm-ann-toc-list a \{([^}]*)\}\s*"
                           r"\.cm-ann-toc-list a\[aria-current\] \{([^}]*)\}", css)
        self.assertIsNotNone(forced)
        self.assertIn("border-left-color: Canvas;", forced.group(1))
        for bit in ("border-left-color: Highlight;", "text-decoration: underline;"):
            self.assertIn(bit, forced.group(2))
        # the narrowest cards (a 320px phone): Copy link and Share a full row each, never Share alone on the
        # left of a second line ("Copiar enlace" + "Compartir" need more than the bar's 246px there)
        narrow = re.search(r"@container cm-ann \(width < 20rem\) \{([^}]*\}[^}]*\})\s*\}", css)
        self.assertIsNotNone(narrow)
        self.assertIn(".cm-ann-actions > button { flex: 1 1 100%; }", narrow.group(1))
        self.assertIn(".cm-ann-gap { display: none; }", narrow.group(1))
        # …and at 130 %+ text or relaxed spacing it stops sticking, like the other side columns
        self.assertRegex(self.main, r'\[data-spacing="relaxed"\]\) :is\([^)]*\.cm-ann-side\) \{\s*position: static !important;')

    def test_the_post_left_takes_the_row_on_the_home_page(self):
        # The home page's cards are teasers (a short post in full, a long one as its summary and "Read more" — not
        # the bulletin's layout): the two newest posts, two a row from 1024px (lg:grid-cols-2, set by the build
        # when there are two); once one has ended between builds (GV.expire hid it), the other takes the whole
        # row, as a post alone does after the next build. lg:grid-cols-2 is a utility (Tailwind's last layer):
        # the rule wins only because home.css is imported outside any layer.
        home = (ROOT / "src/pages/index.njk").read_text(encoding="utf-8")
        self.assertIn("""<div class="home-ann-grid grid items-start gap-5 {{ 'lg:grid-cols-2' if anns.length > 1 }}">""", home)
        self.assertRegex(home, r'<article class="home-ann[^"]*"[^>]*data-gv-expire-item')
        hcss = (ROOT / "src/assets/css/areas/home.css").read_text(encoding="utf-8")
        self.assertRegex(hcss, r"@media \(width >= 64rem\) \{\s*\.home-ann-grid:not\(:has\(> article:not\(\[hidden\]\) ~ "
                               r"article:not\(\[hidden\]\)\)\) \{ grid-template-columns: minmax\(0, 1fr\); \}\s*\}")
        self.assertNotIn("@layer", hcss)
        self.assertIn('@import "./areas/home.css";\n', self.main)

    def test_in_this_post_follows_the_reading(self):
        js = self.js
        fn = js[js.index("function annToc()"):js.index("/* ---------------- /meetings/ hero card")]
        for bit in ('querySelectorAll(".cm-ann-toc")', 'setAttribute("aria-current", "true")', 'removeAttribute("aria-current")',
                    "scrollPaddingTop", '{ passive: true }', "requestAnimationFrame", "offsetParent === null"):
            self.assertIn(bit, fn)
        self.assertNotIn("scrollIntoView", fn)                           # it never moves the page
        self.assertNotIn(".focus(", fn)
        self.assertRegex(js, r"function ready\(\) \{[^}]*annToc\(\);")

    def test_copied_keeps_the_buttons_in_place(self):
        """Copy link says "Copied!" for 1.6 s (app.js GV.copy) — a shorter label, which must not let the panel
        reflow: Share would slide, or jump up beside it (the Spanish panel), right under the pointer that just
        clicked. The button keeps its width (min-width) until its label comes back; a second click meanwhile
        keeps the first width (the label's own, not the narrower "Copied!")."""
        r = app_js(self, r"""
          const btn = el("button", { class: "btn-ghost btn-sm cm-ann-copy", "data-copy": "https://x/#ann-x" });
          btn.innerHTML = "<svg></svg> Copy link";
          btn.getBoundingClientRect = () => ({ width: 129.5 });
          const p = page([btn]);
          p.win.navigator.clipboard = { writeText: () => Promise.resolve() };
          p.win.isSecureContext = true;
          await p.G.copy("https://x/#ann-x", btn);
          const during = { label: btn.innerHTML, min: btn.style.minWidth, active: btn.classList.contains("is-active") };
          btn.getBoundingClientRect = () => ({ width: 96 });              // as "Copied!" would be, on its own
          await p.G.copy("https://x/#ann-x", btn);
          const again = btn.style.minWidth;
          p.clock.now += 1600; p.run();
          out({ during, again, after: { label: btn.innerHTML, min: btn.style.minWidth, active: btn.classList.contains("is-active") } });""")
        self.assertEqual(r["during"], {"label": "Copied!", "min": "129.5px", "active": True})
        self.assertEqual(r["again"], "129.5px")
        self.assertEqual(r["after"], {"label": "<svg></svg> Copy link", "min": "", "active": False})


class StatusPage(unittest.TestCase):
    """/status/: the Bulletin row says "Nothing on the bulletin right now" only when /bulletin/ has no post —
    its source counts the posts written in content/bulletin/, the Drive bulletin folder's are counted with
    the Drive (status.json counts.announcements is every post on /bulletin/)."""

    def test_the_empty_hint_counts_the_drive_posts(self):
        out = run_js(self, """
          const now = new Date().toISOString();
          const src = (source, count) => ({ source, ok: true, updated: now, count });
          const hints = (counts) => filters.cmStatus({ counts, sources: [src("announcements", 0), src("drive", 0)] })
            .sources.map((s) => s.hint);
          out({ drivePost: hints({ announcements: 1 }), none: hints({ announcements: 0 }), noCounts: hints(undefined) });
        """)
        self.assertEqual(out["drivePost"], ["", "drive_empty"])         # a post from Drive is on /bulletin/
        self.assertEqual(out["none"], ["ann_empty", "drive_empty"])
        self.assertEqual(out["noCounts"], ["ann_empty", "drive_empty"])  # an older status.json: as before


if __name__ == "__main__":
    unittest.main()
