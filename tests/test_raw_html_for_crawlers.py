"""Round 35 · what a crawler that runs no script reads on the home page, /meetings/, /share/, /bulletin/, /published/
and /photos/. Most AI crawlers and fetchers (GPTBot, ClaudeBot, PerplexityBot, ChatGPT-User …) read a page's HTML as
it comes — no script, no CSS — so words the page keeps hidden until a script shows them were read as page text: "Happening
now — come on in!" a month before the meeting, "Nothing on the bulletin right now" next to two posts, "No Area 65
stories in the last 60 days" above a list of them. The same in a real browser: tests/browser/test_later_words_browser.py.

  * PhotoAlt   — eleventy/filters/photo-alt.js photoAlts / photoAlt: a photo title that is a file name
                 ("1951-10-Gv-Report-00") becomes the magazine — or the album — and the month in the page's language
                 ("Grapevine, October 1951" / "Grapevine, octubre de 1951"); nothing else of the file name (a person's
                 name in it never reaches the alt text); any other title stays as it is; words several photos of an
                 album share get each one's place ("Grapevine, November 1960 (2 of 4)" / "(2 de 4)").
  * Say        — app.js GV.say writes the words an element keeps in data-gv-say; GV.expire writes a list's empty note's
                 words as it shows it (/bulletin/); home.js writes Published writers' "no story" notes as they show
                 and the daily quote's "Today" / "Yesterday" and its other link name.
  * Built      — the six pages as the site builds them (its own data), English and Spanish:
                 - a hidden or x-cloak element never holds words that wait in data-gv-say (they are written in when
                   true), and an element with data-gv-say holds text only;
                 - the live labels ("Happening now", "Starting soon", "Live now", "Meets today", "Now playing", "No
                   meetings match", the header's "(your settings are on)") are never in the raw text, and an empty
                   state is there only when it is true
                   (the bulletin's with no post, /published/'s with no story in the view, Home's with no story);
                 - Home's "Read more" names its post for screen readers and crawlers ("Read more: <title>");
                 - every join value printed (the Meet code, the Zoom ID, the passcode) is inside an element with
                   data-nosnippet, and data-nosnippet is only ever on a <span> (never a whole card, never a <dd>);
                 - no photo's alt text or "Open photo: …" name is a file name.

    python -m unittest tests.test_raw_html_for_crawlers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

I18N: dict = {}
for _f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
    I18N.update(json.loads(_f.read_text(encoding="utf-8")))


def t(key: str, lang: str) -> str:
    return I18N[key][lang]


def words_re(key: str, lang: str) -> re.Pattern:
    """An i18n string with its {placeholders} as "any word": "No Area 65 stories in the last {days} days"."""
    parts = re.split(r"\{\w+\}", t(key, lang))
    return re.compile(r"\S+".join(re.escape(p) for p in parts))


# ----------------------------------------------------------------------------------------------- photoAlt
class PhotoAlt(unittest.TestCase):
    CASES = [
        # (title, album) → (en, es)
        (("1951-10-Gv-Report-00", "Historical Archive"), ("Grapevine, October 1951", "Grapevine, octubre de 1951")),
        (("1947-11-00-Gv-Subscription", "Historical Archive"), ("Grapevine, November 1947", "Grapevine, noviembre de 1947")),
        (("1960-11-Gv-01-Intl-Western-Union-Eisenhower", "To Organize"), ("Grapevine, November 1960", "Grapevine, noviembre de 1960")),
        (("1998-03-LV-Portada", "Archivo"), ("La Viña, March 1998", "La Viña, marzo de 1998")),
        (("1965-10-00-I-Am-Responsible", "Historical Archive"), ("Historical Archive, October 1965", "Historical Archive, octubre de 1965")),
        (("1965-00-Gv-Annual", "Historical Archive"), ("Grapevine, 1965", "Grapevine, 1965")),
        (("2026-10-15-Booth-01", ""), ("October 2026", "octubre de 2026")),
        # not file names: kept as they are
        (("Panel 75 Displays", "2026 Displays"), ("Panel 75 Displays", "Panel 75 Displays")),
        (("Austria Gemeinsam 1993-09", "International-Equivalent"), ("Austria Gemeinsam 1993-09", "Austria Gemeinsam 1993-09")),
        (("2026-10-15 booth at CityWide", "Booths"), ("2026-10-15 booth at CityWide", "2026-10-15 booth at CityWide")),
        (("1234-10-Gv-00", "Old"), ("1234-10-Gv-00", "1234-10-Gv-00")),
        (("", "Album"), ("", "")),
    ]

    def test_file_names_become_the_magazine_or_album_and_the_month(self):
        r = run_js(self, "const one = (t, a, l) => filters.photoAlts([{ title: t }], a, l)[0]; "
                         "out(input.map(([t, a]) => [one(t, a, 'en'), one(t, a, 'es')]))",
                   data=[list(c[0]) for c in self.CASES])
        for (args, want), got in zip(self.CASES, r):
            with self.subTest(title=args[0]):
                self.assertEqual(tuple(got), want)

    def test_never_a_word_of_the_file_name_but_the_magazine(self):
        r = run_js(self, "out(filters.photoAlts([{ title: '1960-11-Gv-01-Intl-Western-Union-Eisenhower' }], 'To Organize', 'en')[0])")
        self.assertNotIn("Eisenhower", r)
        self.assertNotIn("Western", r)

    def test_the_same_words_get_their_place_in_the_album(self):
        album = [{"title": t} for t in ("1960-11-Gv-00-Intl-Cover-Full-0", "1955-12-Gv-01-Report", "1960-11-Gv-03-Intl-Long-Beach-01",
                                         "Panel 75 Displays", "1960-11-Gv-03-Intl-Long-Beach-02", "Panel 75 Displays", "")]
        r = run_js(self, "out(['en', 'es'].map((l) => filters.photoAlts(input, 'Historical Archive', l)))", data=album)
        self.assertEqual(r[0], ["Grapevine, November 1960 (1 of 3)", "Grapevine, December 1955", "Grapevine, November 1960 (2 of 3)",
                                "Panel 75 Displays (1 of 2)", "Grapevine, November 1960 (3 of 3)", "Panel 75 Displays (2 of 2)", ""])
        self.assertEqual(r[1], ["Grapevine, noviembre de 1960 (1 de 3)", "Grapevine, diciembre de 1955",
                                "Grapevine, noviembre de 1960 (2 de 3)", "Panel 75 Displays (1 de 2)",
                                "Grapevine, noviembre de 1960 (3 de 3)", "Panel 75 Displays (2 de 2)", ""])


# ----------------------------------------------------------------------------------------------- GV.say, home.js
class Say(unittest.TestCase):
    def test_gv_say_and_the_bulletins_empty_note(self):
        r = run_js(self, PAGE_JS + r"""
          const p = page({ html:
            '<ol data-gv-expire-list data-gv-expire-empty="#ann-empty"><li data-gv-expire-item data-gv-expire="2026-10-01T05:00:00.000Z">Post</li></ol>' +
            '<div id="ann-empty" hidden><section><h2 id="h" data-gv-say="Nothing on the bulletin right now"></h2>' +
            '<p id="t" data-gv-say="When the committee has news …"></p></section></div>' +
            '<p id="solo" data-gv-say="Its own words">old words</p>',
            scripts: ["src/assets/js/app.js"], globals: { SITE: { lang: "en", base: "/" } } });
          const before = { h: p.$("#h").textContent, hidden: p.$("#ann-empty").hidden };
          p.win.GV.expire();
          const after = { h: p.$("#h").textContent, t: p.$("#t").textContent, hidden: p.$("#ann-empty").hidden };
          p.win.GV.say(p.$("#solo"));
          out({ before, after, solo: p.$("#solo").textContent, none: p.win.GV.say(null), errors: p.errors.map(String) });""",
                   needs_modules=False)
        self.assertEqual(r["before"], {"h": "", "hidden": True})
        self.assertEqual(r["after"], {"h": "Nothing on the bulletin right now", "t": "When the committee has news …", "hidden": False})
        self.assertEqual(r["solo"], "Its own words", "the element itself too: its words replace what is inside")
        self.assertIsNone(r["none"])
        self.assertEqual(r["errors"], [])

    SPOT = r"""
      const spot = (pubs) => '<section data-home-spot data-days="60"><div data-spot-grid>' +
        '<ul data-spot-list>' + pubs.a65.map((d) => '<li data-pub="' + d + '" data-scope="neta65">A</li>').join("") + '</ul>' +
        '<div id="none" data-spot-none-a65 hidden><h3 id="none-h" data-gv-say="No Area 65 stories in the last 60 days"></h3>' +
        '<p id="none-p" data-gv-say="Yours could be next!"></p></div>' +
        '<ul data-spot-list>' + pubs.tx.map((d) => '<li data-pub="' + d + '" data-scope="texas">T</li>').join("") + '</ul>' +
        '<a data-spot-fill></a></div>' +
        '<div id="empty" data-spot-empty hidden><h3 id="empty-h" data-gv-say="No stories from Texas writers in the last 60 days"></h3></div></section>';
    """

    def test_published_writers_notes_get_their_words_as_they_show(self):
        r = run_js(self, PAGE_JS + self.SPOT + r"""
          const res = {};
          for (const [name, pubs] of Object.entries({ a65gone: { a65: ["2026-07-01"], tx: ["2026-09-30"] },
                                                     allgone: { a65: ["2026-07-01"], tx: ["2026-07-02"] },
                                                     both: { a65: ["2026-09-29"], tx: ["2026-09-30"] } })) {
            const p = page({ html: spot(pubs), scripts: ["src/assets/js/app.js", "src/assets/js/home.js"], globals: { SITE: { lang: "en", base: "/" } } });
            await p.ready();
            res[name] = { none: [p.$("#none").hidden, p.$("#none-h").textContent, p.$("#none-p").textContent],
                          empty: [p.$("#empty").hidden, p.$("#empty-h").textContent], errors: p.errors.map(String) };
          }
          out(res);""", needs_modules=False)
        # (the page's clock: October 6, 2026 — 60 days back is August 7)
        self.assertEqual(r["a65gone"]["none"], [False, "No Area 65 stories in the last 60 days", "Yours could be next!"])
        self.assertEqual(r["a65gone"]["empty"], [True, ""])
        self.assertEqual(r["allgone"]["empty"], [False, "No stories from Texas writers in the last 60 days"])
        self.assertEqual(r["allgone"]["none"][0], True)
        self.assertEqual(r["both"]["none"], [True, "", ""], "a note that stays hidden stays wordless")
        self.assertEqual(r["both"]["empty"], [True, ""])
        for v in r.values():
            self.assertEqual(v["errors"], [])

    def test_the_daily_quotes_today_and_yesterday(self):
        r = run_js(self, PAGE_JS + r"""
          const q = (id, day, fresh) => '<article id="' + id + '" data-quote-day="' + day + '">' +
            '<span class="t" data-quote-today hidden data-gv-say="Today"></span><span class="y" data-quote-yesterday hidden data-gv-say="Yesterday"></span>' +
            '<a><span class="this" data-quote-link="this"' + (fresh ? '' : ' hidden') + ' data-gv-say="Read it on aagrapevine.org">' + (fresh ? 'Read it on aagrapevine.org' : '') + '</span>' +
            '<span class="today" data-quote-link="today"' + (fresh ? ' hidden' : '') + ' data-gv-say="Today’s quote on aagrapevine.org">' + (fresh ? '' : 'Today’s quote on aagrapevine.org') + '</span></a></article>';
          const p = page({ html: q("a", "2026-10-06", true) + q("b", "2026-10-05", true), scripts: ["src/assets/js/app.js", "src/assets/js/home.js"],
                           globals: { SITE: { lang: "en", base: "/" } } });
          await p.ready();
          const show = (id) => Object.fromEntries(["t", "y", "this", "today"].map((c) => { const e = p.$("#" + id + " ." + c); return [c, e.hidden ? null : e.textContent]; }));
          out({ a: show("a"), b: show("b"), errors: p.errors.map(String) });""", needs_modules=False)
        # October 6, 10 AM in Texas: a's quote is today's, b's yesterday's (its link: "Today's quote on …")
        self.assertEqual(r["a"], {"t": "Today", "y": None, "this": "Read it on aagrapevine.org", "today": None})
        self.assertEqual(r["b"], {"t": None, "y": "Yesterday", "this": None, "today": "Today’s quote on aagrapevine.org"})
        self.assertEqual(r["errors"], [])


# ----------------------------------------------------------------------------------------------- the built pages
PAGES_JS = r"""
process.env.ONLY = "index.njk,meetings.njk,share.njk,bulletin.njk,published.njk,photos.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r35-raw-"));
const want = /^\/(es\/)?(meetings\/|share\/|bulletin\/|published\/|photos\/)?$/;
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  out(Object.fromEntries((await elev.toJSON()).filter((p) => want.test(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Raw(HTMLParser):
    """The page as a crawler that runs no script reads it: every text node outside <script> / <style> (a <template>'s,
    a hidden element's too). Also: the elements with data-gv-say (their text, child elements, whether they sit in a
    hidden / x-cloak element), the elements with data-nosnippet, and the text nodes inside one."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.text: list[str] = []
        self.nodes: list[tuple[str, bool]] = []         # (text, inside data-nosnippet)
        self.say: list[dict] = []
        self.nosnippet: list[str] = []
        self.links: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-nosnippet" in a:
            self.nosnippet.append(tag)
        for e in self.stack:
            if e.get("say") is not None:
                e["say"]["children"] += 1
        if tag in VOID:
            return
        e = {"tag": tag, "skip": tag in ("script", "style"), "hid": "hidden" in a or "x-cloak" in a,
             "nosnip": "data-nosnippet" in a, "say": None, "link": None, "sr": "sr-only" in (a.get("class") or "").split()}
        if "data-gv-say" in a:
            e["say"] = {"tag": tag, "words": a["data-gv-say"], "text": "", "children": 0,
                        "hidden": e["hid"] or any(x["hid"] for x in self.stack)}
            self.say.append(e["say"])
        if tag == "a":
            e["link"] = {"href": a.get("href", ""), "text": "", "sr": ""}
            self.links.append(e["link"])
        self.stack.append(e)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, d):
        if any(e["skip"] for e in self.stack):
            return
        self.text.append(d)
        if d.strip():
            self.nodes.append((d.strip(), any(e["nosnip"] for e in self.stack)))
        for e in self.stack:
            if e["say"] is not None:
                e["say"]["text"] += d
            if e["link"] is not None:
                e["link"]["text"] += d
        # the visually hidden part of a link ("Read more<span class=sr-only>: …</span>")
        for i, e in enumerate(self.stack):
            if e["link"] is not None and any(x["sr"] for x in self.stack[i + 1:]):
                e["link"]["sr"] += d


def scan(page: str) -> Raw:
    r = Raw()
    r.feed(page)
    return r


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


class Built(unittest.TestCase):
    pages: dict | None = None

    def setUp(self):
        if Built.pages is None:
            Built.pages = run_js(self, PAGES_JS, timeout=900)
        self.assertEqual(sorted(Built.pages), sorted(f"/{l}{p}" for l in ("", "es/") for p in ("", "meetings/", "share/", "bulletin/", "published/", "photos/")))

    def each(self):
        for url, page in sorted(self.pages.items()):
            yield url, ("es" if url.startswith("/es/") else "en"), page

    def test_words_that_wait_are_not_in_the_html(self):
        for url, lang, page in self.each():
            with self.subTest(url=url):
                r = scan(page)
                for s in r.say:
                    self.assertEqual(s["children"], 0, f"data-gv-say holds text only: {s}")
                    if s["hidden"]:
                        self.assertEqual(s["text"].strip(), "", f"hidden, yet its words are in the HTML: {s}")
                    else:
                        self.assertIn(s["text"].strip(), ("", s["words"].strip()), s)

    def test_live_labels_are_never_in_the_raw_text(self):
        keys = {"/": ["home.meeting_live", "home.now_playing"],
                "/meetings/": ["committee.meeting.starting_soon", "committee.meeting.live_now", "committee.gvm.meets_today", "committee.gvm.none"]}
        for url, lang, page in self.each():
            base = url[3:] if lang == "es" else url[1:]
            # (and on every page, the header's "Aa" button: "(your settings are on)" / "(reading aloud)")
            for key in keys.get("/" + base, []) + ["comfort.custom_on", "comfort.reading_on"]:
                with self.subTest(url=url, key=key):
                    text = flat(" ".join(scan(page).text))
                    self.assertNotIn(t(key, lang), text)
                    self.assertRegex(page, f'data-gv-say=" ?{re.escape(t(key, lang))}"', "…but the browser has them")
            if base == "":
                with self.subTest(url=url, what="Continue listening"):
                    self.assertNotIn(t("media.continue_listening", lang) + ":", flat(" ".join(scan(page).text)))

    def test_an_empty_state_is_there_only_when_it_is_true(self):
        for url, lang, page in self.each():
            text = flat(" ".join(scan(page).text))
            base = url[4:] if lang == "es" else url[1:]
            with self.subTest(url=url):
                if base == "bulletin/":
                    posts = len(re.findall(r'<li class="min-w-0" data-gv-expire-item', page))
                    self.assertEqual(t("committee.ann.empty_title", lang) in text, posts == 0, f"{posts} posts")
                    self.assertIn(f'data-gv-say="{t("committee.ann.empty_title", lang)}"' if posts else 'id="ann-empty-h"', page)
                elif base == "published/":
                    shown = len(re.findall(r'<article class="pw-card"(?![^>]*\shidden)[^>]*>', page))
                    empty = any(words_re(f"published.empty.{s}", lang).search(text) for s in ("neta65", "texas", "all"))
                    self.assertEqual(empty, shown == 0, f"{shown} stories shown")
                    self.assertEqual(t("published.empty.text", lang) in text, shown == 0)
                    if 'id="pw-arc-empty"' in page:
                        rows = len(re.findall(r'<li class="pw-arc-row', page))
                        self.assertEqual(t("published.archive.empty_title", lang) in text, rows == 0, f"{rows} archive rows")
                elif base == "":
                    a65 = len(re.findall(r'data-scope="neta65">', page))
                    tx = len(re.findall(r'data-scope="texas">', page))
                    self.assertEqual(bool(words_re("home.spot_none_a65_title", lang).search(text)), a65 == 0 and tx > 0, (a65, tx))
                    self.assertEqual(bool(words_re("home.spot_empty_title", lang).search(text)), a65 + tx == 0, (a65, tx))
                    # the daily quote never says "Today" / "Yesterday" in the HTML
                    for key in ("home.quote_today", "home.quote_yesterday"):
                        self.assertRegex(page, rf'data-quote-(today|yesterday) hidden data-gv-say="{t(key, lang)}"></span>')

    def test_read_more_names_its_post(self):
        for url, lang, page in self.each():
            if url not in ("/", "/es/"):
                continue
            more = [l for l in scan(page).links if flat(l["text"]).startswith(t("common.read_more", lang))]
            with self.subTest(url=url):
                for l in more:
                    self.assertRegex(flat(l["sr"]), r"^: \S", l)
                    self.assertEqual(flat(l["text"]), t("common.read_more", lang) + flat(l["sr"]))
                    self.assertNotEqual(flat(l["text"]), t("common.read_more", lang), "a bare Read more says nothing")

    def test_join_values_are_never_quoted(self):
        # the values themselves: what the copy buttons on /meetings/ copy (the code, the Zoom ID, the passcode — not
        # the links), as the pages print them (the ID in groups of digits)
        for lang in ("en", "es"):
            pre = "/es/" if lang == "es" else "/"
            meetings = self.pages[pre + "meetings/"]
            values = {v for v in re.findall(r'data-copy="([^"]+)"', meetings) if not v.startswith("http") and "@" not in v}
            self.assertTrue(values, "the page prints how to join")
            for url in (pre + "meetings/", pre + "share/", pre):
                with self.subTest(url=url):
                    r = scan(self.pages[url])
                    found = [(n, inside) for n, inside in r.nodes if any(v in n.replace(" ", "").replace(" ", "") for v in values)]
                    if url != pre:
                        self.assertTrue(found, "the page prints them")
                    self.assertEqual([n for n, inside in found if not inside], [], "a join value Google or Bing could quote")
                    self.assertEqual(set(r.nosnippet) - {"span"}, set(), "data-nosnippet only on a span (never a card, a dd or an li)")

    def test_no_photo_is_named_by_its_file_name(self):
        name = re.compile(r"^\d{4}-\d{2}(-\d{2})?(-[^\s-]+)+$")
        for url, lang, page in self.each():
            if not url.endswith("photos/"):
                continue
            with self.subTest(url=url):
                alts = re.findall(r'<img [^>]*\balt="([^"]*)"', page)
                labels = re.findall(r'aria-label="' + re.escape(t("committee.photos.open_photo", lang).split("{")[0]) + r'([^"]*)"', page)
                self.assertTrue(alts)
                self.assertEqual([a for a in alts + labels if name.match(a)], [])
                # each photo's alt and its link's name say the same
                for label in labels:
                    self.assertIn(f'alt="{label}"', page)
                # no two photo links of one album share a name (several photos of the same words: "(2 of 4)")
                for album in re.findall(r'<ul class="cm-photo-grid.*?</ul>', page, re.S):
                    names = re.findall(r'aria-label="([^"]*)"', album)
                    self.assertEqual(len(names), len(set(names)), [n for n in names if names.count(n) > 1][:5])


if __name__ == "__main__":
    unittest.main()
