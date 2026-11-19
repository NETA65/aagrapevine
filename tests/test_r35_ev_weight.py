"""Round 35 · /events/ for readers that run no script — an AI tool's fetch, a crawler that reads the HTML as it comes.

A live AI fetch (November 2026) stopped reading /events/ at 100,000 of its 253,218 characters, among the events of
June 2027: the Fall Assembly and every 2028 date never reached it. About three quarters of what it read were the cards' Google / Outlook links, each
carrying the event's whole description, and one sentence (the menus' note) 111 times. And it took the hidden "Live
now" for the page's news.

  * Links      — eleventy/filters/committee.js calendarLinks(ev, { brief: true }): the same Google / Outlook address
                 WITHOUT the description (no details=, no body=), every other field as the full one has it, in its
                 order; shapeEvent gives every event both (ev.gcal / ev.outlook as before, ev.gcalBrief /
                 ev.outlookBrief). The browser's CM.calLinks (src/assets/js/committee.js), fed the card's own .ics data
                 (ev.icsData, the page's data-cm-ics), makes exactly the build's full links — for every event of the
                 settings and the test's own, in both languages — so a visitor who opens a menu gets today's links.
  * NoSnippet  — committee.js noSnippetJoin (the cmNoSnippet filter): in some HTML people read, each value that says
                 how to join an online meeting — a meeting ID after its words, a Google Meet code after "Meet",
                 "code" or "código", a passcode after its word, a Zoom or Meet address written out — is wrapped in
                 <span data-nosnippet>; the words around it, tags and their attributes are left alone, and so are
                 ordinary words ("The password is required", "a two-week-old idea"). A span never ends inside an
                 entity of the escaped text (`&quot;` around an address), and a value's words may sit in an inline
                 tag before it ("**Meeting code:** rva-tmst-vdb"). The text people read stays the same.
  * ThePage    — src/pages/events.njk and the events' own pages (src/pages/event-share-leaf.njk), built with Eleventy
                 on November 13, 2026 with the test's events (SITE_DATA) and round 20's settings (the committee meeting
                 and the Grapevine Meeting on Google Meet):
                   - every card's "Add to calendar" menu and the pinned cards' carry the brief links: the title, the
                     times, the place, the zone — the description nowhere (only the weekly open meetings' "every week"
                     Google link keeps its own, two links); an event's own page keeps the full ones (one card);
                   - the menus' note: no words in a card (data-cm-note="timed" | "day"), its two texts once, on the
                     agenda (data-cm-note-timed / -day);
                   - no live-state label that is not true at the build is text in the page: no "Live now" / "En vivo
                     ahora"; the Grapevine Meeting's card says "First meeting:" (its first date is to come), never
                     "Next meeting:" too — each one's words wait in data-label for Alpine (x-text);
                   - every meeting ID, Meet code, passcode and meeting address people read on /events/ and on an
                     event's own page is inside an element with data-nosnippet (the card's own line; the description's
                     values) — and still on the page, word for word.
  * Budget     — /events/ as the site ships it (data/site, today): its <main> as such a reader takes it — the text and
                 the link addresses — stays under 170,000 characters in each language (it was 292,000 / 320,000 in
                 round 35, before; 145,000 / 155,000 after), and no card's static link carries a description.
  * Wiring     — committee.js fills a menu (fillMenu) as it opens, before the panel is placed; the CSS, for the record.

Skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_r35_ev_weight -v
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
import test_central_time as TCT  # noqa: E402  (the page stand-in: TCT.DOM)
import test_r20_meeting as R20  # noqa: E402  (round 20's settings: the committee meeting + the Grapevine Meeting)
import test_r21_weekly as R21  # noqa: E402  (the weekly open meetings of round 21's tests)
from test_r30_events_list import at, event  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-11-13T18:00:00Z"             # Fri Nov 13, 2026, noon CST (round 30's day: the Grapevine Meeting starts Dec 2)
T = R21.T                                # every i18n string, by key
BASE = "https://x.test"
GOOGLE = "https://calendar.google.com/calendar/render?"
OUTLOOK = "https://outlook.live.com/calendar/0/action/compose?"
PLACE = {"location": "Grupo Uno, 100 Main St, Tyler, TX 75702", "city": "Tyler", "state": "TX"}
JOIN = "Come in person, or join on Zoom (meeting ID 123 456 7890, passcode zz65). Coffee after the workshop."
BODY = (JOIN + "\n\nThe link: https://us02web.zoom.us/j/1234567890 — or, on Google Meet, meet.google.com/qrs-tuvw-xyz "
        "(meeting code qrs-tuvw-xyz).")
FLYER_DOC = ("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456/view",
             "https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/edit")


def items() -> list[dict]:
    """A hybrid workshop at a place (a leaf: its own page) whose words say how to join; an online-only one on Zoom with
    its meeting ID; one on Google Meet with its code; an all-day ACM (a leaf); a monthly booth."""
    out = [
        event("ev:manual:zz-hybrid", "manual", "Hybrid Writing Workshop", at(date(2026, 12, 5), "19:00"),
              at(date(2026, 12, 5), "21:00"), slug="zz-hybrid", title_es="Taller de Escritura Híbrido",
              online_url="https://us02web.zoom.us/j/1234567890?pwd=abc", platform="Zoom", body_md=BODY, **PLACE),
        event("ev:manual:zz-zoom", "manual", "Online Workshop on Zoom", at(date(2027, 1, 9), "10:00"),
              at(date(2027, 1, 9), "12:00"), slug="zz-zoom", online_url="https://us06web.zoom.us/j/81595931777",
              platform="Zoom", meeting_id="815 9593 1777"),
        event("ev:manual:zz-meet", "manual", "Online Workshop on Google Meet", at(date(2027, 2, 6), "10:00"),
              at(date(2027, 2, 6), "12:00"), slug="zz-meet", online_url="https://meet.google.com/qrs-tuvw-xyz",
              platform="Google Meet", meeting_id="qrs-tuvw-xyz"),
        event("ev:manual:zz-acm", "manual", "Winter ACM 2027", "2027-02-21", "2027-02-21", slug="zz-acm",
              title_es="ACM de Invierno 2027", tags=["neta65", "acm"], **PLACE),
        # a leaf with its flyer on the Drive and an outside link that is not its flyer (a Google Doc)
        {**event("ev:manual:zz-flyer-doc", "manual", "Workshop With a Flyer and a Doc", at(date(2027, 1, 16), "13:00"),
                 at(date(2027, 1, 16), "15:00"), slug="zz-flyer-doc", flyer_url=FLYER_DOC[0], **PLACE), "url": FLYER_DOC[1]},
    ]
    for d in (date(2026, 12, 12), date(2027, 1, 9), date(2027, 2, 13)):
        out.append(event(f"ev:recurring:zz-booth:{d.isoformat()}", "recurring", "GV/LV booth at Test Hall",
                         at(d, "17:00"), at(d, "19:00"), title_es="Mesa de GV/LV en Test Hall", series="zz-booth",
                         recurring=True, host="neta", rule={"week_of_month": 2, "weekday": "saturday", "start": "17:00",
                                                            "end": "19:00"}, **PLACE))
    for it in out:
        it["summary"] = JOIN if it["id"] != "ev:manual:zz-acm" else "The Area's winter committee meeting."
    return out


def query(href: str) -> list[tuple[str, str]]:
    return parse_qsl(urlparse(html.unescape(href)).query, keep_blank_values=True)


def main_of(page: str) -> str:
    return page[page.index('<main id="main"'):page.index("</main>")]


def readable(fragment: str) -> str:
    """What a reader that runs no script and no CSS takes as text: no script, style or template, no tags."""
    t = re.sub(r"<(script|style|template)\b.*?</\1>|<svg\b.*?</svg>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def words(fragment: str) -> str:
    """The words as they read on the screen: an inline <span> (data-nosnippet's) adds no space."""
    return readable(re.sub(r"</?span\b[^>]*>", "", fragment))


def cal_hrefs(fragment: str) -> list[str]:
    return [html.unescape(h) for h in re.findall(r'href="([^"]*)"', fragment) if h.startswith((GOOGLE, OUTLOOK))]


def cards(page: str) -> dict[str, str]:
    """The list's cards: anchor → its <li> … </li>."""
    out = {}
    for m in re.finditer(r'<li id="([^"]+)" data-group="[^"]*"[^>]*>(.*?)</article>\s*</li>', page, re.S):
        out[m.group(1)] = m.group(2)
    return out


# The values that say how to join, as this test finds them in text people read (its own patterns, not the filter's):
# a meeting ID's number, a Google Meet code, a Zoom / Meet address, a passcode's value right after its word
VALUE = re.compile(r"\d{3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}|\b[a-z]{3}-[a-z]{4}-[a-z]{3}\b|zoom\.us/|meet\.google\.com/|"
                   r"(?:pass\s*code|password|contrase[ñn]a|c[oó]digo de acceso)\s*[:#]?\s*[A-Za-z0-9]", re.I)


class SnippetText(HTMLParser):
    """Each text node of some HTML → (its text, inside an element with data-nosnippet?)."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.nodes: list[tuple[str, bool]] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "svg"):
            self.skip += 1
        if tag in self.VOID:
            return
        inside = bool(self.stack and self.stack[-1][1]) or any(k == "data-nosnippet" for k, _ in attrs)
        self.stack.append((tag, inside))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "svg"):
            self.skip = max(0, self.skip - 1)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if data.strip() and not self.skip:
            self.nodes.append((data, bool(self.stack and self.stack[-1][1])))


def unshielded(fragment: str) -> list[str]:
    """The join values in text people read that are NOT inside an element with data-nosnippet."""
    p = SnippetText()
    p.feed(fragment)
    return [t.strip() for t, inside in p.nodes if not inside and VALUE.search(t)]


# --------------------------------------------------------------------------- the links
LINKS_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const site = (await imp("src/_data/site.js")).default();
const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"] });
const res = {};
for (const lang of ["en", "es"]) {
  const evs = C.normalizeEvents(input.items, site, lang, { now: new Date(input.now) });
  res[lang] = evs.map((e) => ({ id: e.id, gcal: e.gcal, outlook: e.outlook, gcalBrief: e.gcalBrief, outlookBrief: e.outlookBrief,
    desc: e.calDescription, js: p.win.CM.calLinks(JSON.parse(JSON.stringify(e.icsData))) }));
}
const one = res.en.find((e) => e.id === "ev:manual:zz-hybrid");
out({ res, direct: C.calendarLinks({ title: "T", calDescription: "D", calLocation: "L", allDay: true, startYmd: "2027-02-21", endYmd: "2027-02-21" }, { brief: true }), one });
"""


class Links(unittest.TestCase):
    r: dict | None = None

    def got(self) -> dict:
        if Links.r is None:
            Links.r = run_js(self, TCT.DOM + LINKS_JS, data={"items": items(), "now": NOW}, timeout=180)
        return Links.r

    def test_brief_is_the_full_link_without_the_description(self):
        r = self.got()
        n = 0
        for lang, evs in r["res"].items():
            for e in evs:
                with self.subTest(lang=lang, id=e["id"]):
                    full, brief = query(e["gcal"]), query(e["gcalBrief"])
                    self.assertEqual([k for k, _ in full], ["action", "text", "dates", "details", "location", "ctz"])
                    self.assertEqual(brief, [kv for kv in full if kv[0] != "details"])
                    self.assertEqual(dict(full)["details"], e["desc"], "the full link keeps the whole description")
                    full, brief = query(e["outlook"]), query(e["outlookBrief"])
                    self.assertEqual([k for k, _ in full], ["rru", "subject", "startdt", "enddt", "allday", "body", "location"])
                    self.assertEqual(brief, [kv for kv in full if kv[0] != "body"])
                    self.assertTrue(e["gcalBrief"].startswith(GOOGLE) and e["outlookBrief"].startswith(OUTLOOK))
                    n += 1
        self.assertGreater(n, 30, "the settings' committee meetings and the test's events")
        d = r["direct"]
        self.assertEqual(query(d["gcal"]), [("action", "TEMPLATE"), ("text", "T"), ("dates", "20270221/20270222"),
                                            ("location", "L"), ("ctz", "America/Chicago")])
        self.assertEqual(query(d["outlook"]), [("rru", "addevent"), ("subject", "T"), ("startdt", "2027-02-21"),
                                               ("enddt", "2027-02-22"), ("allday", "true"), ("location", "L")])

    def test_the_browser_makes_the_builds_full_links_from_the_cards_data(self):
        for lang, evs in self.got()["res"].items():
            for e in evs:
                with self.subTest(lang=lang, id=e["id"]):
                    self.assertEqual(e["js"], {"gcal": e["gcal"], "outlook": e["outlook"]})


# --------------------------------------------------------------------------- data-nosnippet
NOSNIPPET_JS = r"""
const C = await imp("eleventy/filters/committee.js");
out(input.map((s) => C.noSnippetJoin(s)));
"""
# (an event's description as the pages write it: its Markdown through the site's md, as events.njk and
# event-share-leaf.njk do — `ev.body | md(…) | cmNoSnippet`)
NOSNIPPET_MD_JS = r"""
const C = await imp("eleventy/filters/committee.js");
out(input.map((s) => C.noSnippetJoin(filters.md(s, { h: 4, lang: "en", name: "Test" }))));
"""


class NoSnippet(unittest.TestCase):
    def check(self, script: str, cases: list[tuple[str, str]]):
        got = run_js(self, script, data=[c[0] for c in cases])
        for (src, want), have in zip(cases, got):
            with self.subTest(src=src):
                self.assertEqual(have, want)
                # people read the same words: the text without the marks is the text as it was
                self.assertEqual(html.unescape(re.sub(r"<[^>]*>", "", have)), html.unescape(re.sub(r"<[^>]*>", "", want)))

    def test_an_address_ends_before_an_entity(self):
        """A summary is escaped (`| escape`) before cmNoSnippet: a quote around an address is `&quot;` or `&#39;`,
        and the span closes before it — never inside it (a stray ";" on the page) — while an `&amp;` of the
        address's query stays in."""
        self.check(NOSNIPPET_JS, [
            ("Entrar por Zoom: &quot;https://us06web.zoom.us/j/81595931777&quot; o en persona.",
             "Entrar por Zoom: &quot;<span data-nosnippet>https://us06web.zoom.us/j/81595931777</span>&quot; o en persona."),
            ("Join &#39;meet.google.com/rva-tmst-vdb&#39; tonight.",
             "Join &#39;<span data-nosnippet>meet.google.com/rva-tmst-vdb</span>&#39; tonight."),
            ("At &lt;meet.google.com/rva-tmst-vdb&gt; or zoom.us/j/1?pwd=abc&amp; …",
             "At &lt;<span data-nosnippet>meet.google.com/rva-tmst-vdb</span>&gt; or <span data-nosnippet>zoom.us/j/1?pwd=abc</span>&amp; …"),
        ])
        # …and the Markdown path: an address with no scheme is no link there, so its quotes are entities too
        self.check(NOSNIPPET_MD_JS, [
            ('Join "meet.google.com/rva-tmst-vdb" tonight.',
             '<p>Join &quot;<span data-nosnippet>meet.google.com/rva-tmst-vdb</span>&quot; tonight.</p>\n'),
            ("Join <meet.google.com/rva-tmst-vdb> tonight.",
             "<p>Join &lt;<span data-nosnippet>meet.google.com/rva-tmst-vdb</span>&gt; tonight.</p>\n"),
            ("**Meeting code:** rva-tmst-vdb · **Passcode:** 051617",
             "<p><strong>Meeting code:</strong> <span data-nosnippet>rva-tmst-vdb</span> · <strong>Passcode:</strong> "
             "<span data-nosnippet>051617</span></p>\n"),
        ])

    def test_words_are_no_values(self):
        """"is" / "es" after a passcode's word is no value, nor a word with no digit after it (only after a ":" or "#");
        a 3-4-3 phrase is a Meet code only in lowercase, as a word of its own, a few words after "Meet", "code" or
        "código"."""
        same = [
            "<p>The password is required at the door.</p>",
            "<p>La contraseña es necesaria para entrar.</p>",
            "<p>A non-stop-fun day and a two-week-old idea; ask-them-now. A one-year-old group, FUN-DAYS-OUT.</p>",
            "<p>Meet code: RVA-TMST-VDB.</p>",
            "<p>Meet us there.</p><p>rva-tmst-vdb</p>",
            "<p>Meeting code talk: bring the ask-them-now-list.</p>",
        ]
        self.check(NOSNIPPET_JS, [(s, s) for s in same] + [
            ("<p>Google Meet: rva-tmst-vdb</p>", "<p>Google Meet: <span data-nosnippet>rva-tmst-vdb</span></p>"),
            ("<p>Código de Meet rva-tmst-vdb.</p>", "<p>Código de Meet <span data-nosnippet>rva-tmst-vdb</span>.</p>"),
            ("<p>The passcode is 051617.</p>", "<p>The passcode is <span data-nosnippet>051617</span>.</p>"),
            ("<p>Password: grapevine.</p>", "<p>Password: <span data-nosnippet>grapevine</span>.</p>"),
            ("<p>Meet code &quot;rva-tmst-vdb&quot;.</p>", "<p>Meet code &quot;<span data-nosnippet>rva-tmst-vdb</span>&quot;.</p>"),
        ])

    def test_the_values_and_nothing_else(self):
        cases = [
            ("<p>Zoom meeting ID 445 571 1924, passcode 051617.</p>",
             "<p>Zoom meeting ID <span data-nosnippet>445 571 1924</span>, passcode <span data-nosnippet>051617</span>.</p>"),
            ("<p>ID de reunión de Zoom 445 571 1924, código de acceso 051617.</p>",
             "<p>ID de reunión de Zoom <span data-nosnippet>445 571 1924</span>, código de acceso <span data-nosnippet>051617</span>.</p>"),
            ('<p>On Google Meet: <a href="https://meet.google.com/rva-tmst-vdb">https://meet.google.com/rva-tmst-vdb</a> (meeting code rva-tmst-vdb).</p>',
             '<p>On Google Meet: <a href="https://meet.google.com/rva-tmst-vdb"><span data-nosnippet>https://meet.google.com/rva-tmst-vdb</span></a>'
             ' (meeting code <span data-nosnippet>rva-tmst-vdb</span>).</p>'),
            ("Meeting ID: 815 9593 1777. Contraseña: abc123. us02web.zoom.us/j/1234567890?pwd=abc&amp;x=1.",
             "Meeting ID: <span data-nosnippet>815 9593 1777</span>. Contraseña: <span data-nosnippet>abc123</span>. "
             "<span data-nosnippet>us02web.zoom.us/j/1234567890?pwd=abc&amp;x=1</span>."),
            # a phone number, the words alone, an attribute: left as they are
            ('<p title="meeting ID 123 456 7890">Call 214 555 1234. Ask for the meeting ID.</p>',
             '<p title="meeting ID 123 456 7890">Call 214 555 1234. Ask for the meeting ID.</p>'),
            ("", ""),
        ]
        got = run_js(self, NOSNIPPET_JS, data=[c[0] for c in cases])
        for (src, want), have in zip(cases, got):
            with self.subTest(src=src):
                self.assertEqual(have, want)


# --------------------------------------------------------------------------- the page
PAGE_JS = r"""
process.env.ONLY = "events.njk,event-share";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const yaml = await import("js-yaml");
const { Eleventy } = await import("@11ty/eleventy");
const cfg = yaml.load(input.yaml);
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r35-ev2-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(c) {
      const none = (o) => Object.fromEntries(Object.keys(o || {}).map((k) => [k, null]));
      c.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, weekly_open: { updated: "2026-11-02T12:00:00Z", items: input.weekly } }),
        site: (data) => ({ ...data.site, meeting: { ...none(data.site.meeting), ...cfg.meeting }, recurring_events: cfg.recurring_events }),
      });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => /\/events\//.test(p.url || "")).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class ThePage(unittest.TestCase):
    r: dict | None = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gv-r35-ev2-data-"))
        (cls.tmp / "events.json").write_text(json.dumps({"updated": NOW, "items": items()}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def pages(self) -> dict:
        if ThePage.r is None:
            ThePage.r = run_js(self, PAGE_JS, data={"yaml": R20.YAML, "weekly": R21.WEEKLY}, timeout=900, now=NOW,
                               env={"SITE_DATA": str(self.tmp), "SITE_URL": BASE, "STRICT_BUILD": "", "LASTMOD": ""})
        return ThePage.r

    def test_the_cards_carry_brief_links(self):
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            page = main_of(self.pages()[url])
            with self.subTest(url=url):
                cs = cards(page)
                self.assertGreater(len(cs), 10)
                for anchor, card in cs.items():
                    links = cal_hrefs(card)
                    self.assertEqual(len(links), 2, anchor)
                    ics = json.loads(html.unescape(re.search(r'data-cm-ics="([^"]*)"', card).group(1)))
                    g = dict(query(links[0]))
                    self.assertEqual(list(g), ["action", "text", "dates", "location", "ctz"], anchor)
                    self.assertEqual((g["text"], g["location"], g["ctz"]), (ics["title"], ics["location"], "America/Chicago"))
                    o = dict(query(links[1]))
                    self.assertEqual(list(o), ["rru", "subject", "startdt", "enddt", "allday", "location"], anchor)
                    self.assertEqual(o["allday"], "true" if ics["allDay"] else "false")
                    # the description is in the card's .ics data, for the browser
                    self.assertTrue(ics["description"], anchor)
                hybrid = dict(query(cal_hrefs(cs["zz-hybrid"])[0]))
                self.assertEqual((hybrid["dates"], hybrid["location"]), ("20261206T010000Z/20261206T030000Z", PLACE["location"]))
                # nowhere a description in the page's calendar links but the weekly open meetings' own (cmWeeklyCal:
                # "every week", two links)
                full = [h for h in cal_hrefs(page) if any(k in ("details", "body") for k, _ in query(h))]
                self.assertEqual(len(full), 2, full)
                self.assertTrue(all("recur=RRULE" in h for h in full))
                pinned = page[page.index('<section id="ev-pinned"'):page.index('<section id="ev-weekly"')]
                self.assertEqual(len(cal_hrefs(pinned)), 4)
                self.assertIn(':href="gcal" href="https://calendar.google.com/', pinned, "Alpine puts the full ones in")

    def test_the_menus_note_once(self):
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            page = main_of(self.pages()[url])
            with self.subTest(url=url):
                notes = re.findall(r'<p class="cm-menu-note" data-cm-js data-cm-note="(\w+)">(.*?)</p>', page)
                self.assertEqual(len(notes), len(cards(page)))
                self.assertEqual({w for _, w in notes}, {""}, "no words in a card's note")
                self.assertEqual({k for k, _ in notes}, {"timed", "day"})
                self.assertEqual(re.search(r'<p class="cm-menu-note" data-cm-js data-cm-note="(\w+)">', cards(page)["zz-acm"]).group(1), "day")
                for key in ("timed", "day"):
                    words = html.escape(T[f"committee.cal.reminder_{key}"][lang], quote=True)
                    self.assertEqual(page.count(f'data-cm-note-{key}="{words}"'), 1)
                # the pinned cards' and the weekly open meetings' notes stay written out (four menus)
                self.assertEqual(readable(page).count(T["committee.cal.reminder_timed"][lang]), 4)
                self.assertNotIn(T["committee.cal.reminder_day"][lang], readable(page))

    def test_no_live_label_that_is_not_true(self):
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            page = self.pages()[url]
            with self.subTest(url=url):
                text = readable(main_of(page))
                self.assertNotIn(T["committee.meeting.live_now"][lang], text)
                for k in ("join_live", "join_soon"):
                    self.assertNotIn(T[f"committee.meeting.{k}"][lang], text)
                gvm = readable(page[page.index('<article id="ev-next-gvm"'):page.index("</article>", page.index('<article id="ev-next-gvm"'))])
                self.assertIn(T["committee.events.first_meeting"][lang], gvm, "its first date is to come: true")
                self.assertNotIn(T["committee.weekly.next"][lang], gvm, "…and only that")
                # the words wait for Alpine: data-label + x-text, each label once
                for k in ("committee.meeting.live_now", "committee.events.first_meeting", "committee.weekly.next"):
                    attr = 'data-label="' + html.escape(T[k][lang], quote=True) + '" x-text="$el.dataset.label"'
                    self.assertIn(attr, page, k)
                pinned = page[page.index('<article class="cm-pinned'):page.index("</article>", page.index('<article class="cm-pinned'))]
                self.assertRegex(pinned, r'x-cloak class="inline-flex items-center gap-2"><span class="cm-live-dot"></span>'
                                         r'<span data-label="[^"]+" x-text="\$el\.dataset\.label"></span></span>')

    def test_an_outside_link_beside_a_flyer(self):
        """A leaf with a flyer: its card's title goes to its own page, so its outside link (not its flyer) is the
        card's "Event details" button, as on its own page — the outside page is never left to that page alone."""
        flyer, doc = FLYER_DOC
        for url, lang, pre in (("/events/", "en", ""), ("/es/events/", "es", "/es")):
            card = cards(main_of(self.pages()[url]))["zz-flyer-doc"]
            with self.subTest(url=url):
                self.assertRegex(card, r'<h3 [^>]*><a href="' + re.escape(f"{pre}/events/zz-flyer-doc/") + '"')
                self.assertRegex(card, r'<a class="btn-secondary btn-sm" href="' + re.escape(doc) + '" target="_blank"')
                self.assertIn(T["committee.events.details"][lang], readable(card))
                self.assertIn(flyer, card, "View flyer, as before")
        leaf = main_of(self.pages()["/events/zz-flyer-doc/"])
        self.assertIn(f'href="{doc}"', leaf)
        # a card whose link is its own (no outside page): no "Event details", as before
        acm = cards(main_of(self.pages()["/events/"]))["zz-acm"]
        self.assertNotIn(T["committee.events.details"]["en"], readable(acm))

    def test_join_values_are_never_quoted_by_search_engines(self):
        p = self.pages()
        leaves = [u for u in p if re.fullmatch(r"(/es)?/events/zz-(hybrid|acm)/", u)]
        self.assertEqual(len(leaves), 4, sorted(p))
        for url in ["/events/", "/es/events/", *leaves]:
            page = main_of(p[url])
            with self.subTest(url=url):
                self.assertEqual(unshielded(page), [])
        for url in ("/events/", "/es/events/"):
            page = main_of(p[url])
            with self.subTest(url=url):
                cs = cards(page)
                # the card's own line: the value, not its words
                self.assertRegex(cs["zz-zoom"], r'translate="no" data-nosnippet>815 9593 1777</span>')
                self.assertRegex(cs["zz-meet"], r'translate="no" data-nosnippet>qrs-tuvw-xyz</span>')
                # the description's values (the card shows it whole: body_md), still there for people, word for word
                said = words(cs["zz-hybrid"])
                self.assertIn("join on Zoom (meeting ID 123 456 7890, passcode zz65)", said)
                self.assertIn("meet.google.com/qrs-tuvw-xyz (meeting code qrs-tuvw-xyz)", said)
                self.assertIn("<span data-nosnippet>123 456 7890</span>", cs["zz-hybrid"])
                self.assertIn("<span data-nosnippet>zz65</span>", cs["zz-hybrid"])
                # a summary (no body): escaped first, then the values
                self.assertIn("(meeting ID <span data-nosnippet>123 456 7890</span>, passcode <span data-nosnippet>zz65</span>)",
                              cs["ev-recurring-zz-booth-2026-12-12"])
        leaf = main_of(p["/events/zz-hybrid/"])
        self.assertIn("join on Zoom (meeting ID 123 456 7890, passcode zz65)", words(leaf))
        self.assertIn("<span data-nosnippet>https://us02web.zoom.us/j/1234567890</span>", leaf)
        # an event's own page keeps the FULL calendar links and its note (one card)
        self.assertEqual(sorted({k for h in cal_hrefs(leaf) for k, _ in query(h)} & {"details", "body"}), ["body", "details"])
        self.assertIn(T["committee.cal.reminder_timed"]["en"], readable(leaf))


# --------------------------------------------------------------------------- the weight, as the site ships it
BUDGET = 170_000
SHIPPED_JS = r"""
process.env.ONLY = "events.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r35-ev2-real-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => /\/events\/$/.test(p.url || "")).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class Budget(unittest.TestCase):
    def test_what_a_reader_without_a_browser_takes_from_the_page(self):
        p = run_js(self, SHIPPED_JS, timeout=900, env={"SITE_URL": BASE, "STRICT_BUILD": "", "LASTMOD": ""})
        for url in ("/events/", "/es/events/"):
            page = main_of(p[url])
            with self.subTest(url=url):
                body = re.sub(r"<(script|style|template)\b.*?</\1>|<svg\b.*?</svg>", " ", page, flags=re.S)
                hrefs = sum(len(html.unescape(h)) for h in re.findall(r'href="([^"]*)"', body))
                size = len(readable(page)) + hrefs
                self.assertLess(size, BUDGET, f"{url}: {size:,} characters of text and link addresses")
                for anchor, card in cards(page).items():
                    for h in cal_hrefs(card):
                        self.assertFalse({k for k, _ in query(h)} & {"details", "body"}, anchor)


# --------------------------------------------------------------------------- the wiring
class Wiring(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_the_browser_fills_a_menu_as_it_opens(self):
        js = self.read("src/assets/js/committee.js")
        self.assertIn("function fillMenu(d) {", js)
        self.assertIn('var links = CM.calLinks(JSON.parse(b.getAttribute("data-cm-ics")));', js)
        self.assertIn('var key = "data-cm-note-" + note.getAttribute("data-cm-note"), src = note.closest("[" + key + "]");', js)
        toggle = js[js.index('document.addEventListener("toggle", function (e) {'):]
        # before the panel is placed (the note changes its size)
        self.assertLess(toggle.index("fillMenu(d);"), toggle.index('var panel = d.querySelector(".cm-menu-panel");'))
        page = self.read("src/pages/events.njk")
        self.assertIn('<a href="{{ ev.gcalBrief }}" target="_blank" rel="noopener">', page)
        self.assertIn('<a href="{{ ev.outlookBrief }}" target="_blank" rel="noopener">', page)
        self.assertNotIn("{{ ev.gcal }}", page)
        self.assertNotIn("{{ ev.outlook }}", page)

    def test_the_covers_blocks_are_drawn_only_near_the_screen(self):
        css = self.read("src/assets/css/areas/committee.css")
        sup = css[css.index("@supports (overflow-clip-margin: 1rem) {"):]
        sup = sup[:sup.index("\n  }\n")]
        self.assertIn(".cm-cover-album { content-visibility: auto; overflow-clip-margin: 1rem; contain-intrinsic-block-size: auto 118rem; }", sup)
        for w, h in (("30rem", "80rem"), ("48rem", "76rem"), ("72rem", "45rem"), ("96rem", "52rem"), ("120rem", "63rem")):
            self.assertIn(f"@media (width >= {w}) {{ .cm-cover-album {{ contain-intrinsic-block-size: auto {h}; }} }}", sup)
        self.assertIn("@media print { .cm-cover-album { content-visibility: visible; } }", css)
        # the Month view's blocks have no box: nothing to skip
        self.assertIn(".cm-covers.is-flat :is(.cm-cover-album, .cm-cover-grid) { display: contents; }", css)


if __name__ == "__main__":
    unittest.main()
