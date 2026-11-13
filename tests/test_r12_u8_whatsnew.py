"""What's New: "New since your last visit" (round 12) — remembered on the visitor's device only, nothing sent anywhere.

  * When an entry first appeared (eleventy/filters/community.js wnSeenOf → cmWnSeen, cmWnSeenList): the time the
    site first had it (first_seen), not its news date — a video YouTube dates two weeks back but found today is new;
    a date-only news date (noon UTC) never moves it later; a bulletin post scheduled for a later day counts from that
    day; a folded magazine issue and an episode with its YouTube upload count from the first of their parts; the
    page's list counts a folded issue as its stories (as the day headings do).
  * The page's own script (whats-new.njk, right after the line — taken from the template and run as it is): this
    device's record of its visits ("gv-wn-seen"); nothing on a first visit, without storage or with nothing new; on
    a later visit "New since your last visit (Oct 13): 3 updates" and a "New for you" mark on exactly those entries
    (a <style> for their data-seen), before the feed is drawn; a reload within 30 minutes is the same visit (the
    marks stay); "(earlier today)", the year when it is another one, Spanish ("13 oct").
  * The line's buttons and the visit's time (src/assets/js/community.js whatsNew sinceDone, watchVisit): "Mark all as
    read" hides the line and the marks and the next visit counts from this one; "Forget my last visit" removes the
    record; screen readers are told, and keyboard focus goes to the first day's heading; leaving the page keeps the
    visit's time, and never brings a forgotten record back.
  * The template: data-seen and the mark on both kinds of entry, the line hidden without JavaScript, the strings
    in English and Spanish.

Every clock is fixed (run_js now=…, the pretend page's own clock): nothing here depends on the day the tests run.

    python -m unittest tests.test_r12_u8_whatsnew -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "pages" / "whats-new.njk"
STRINGS = json.loads((ROOT / "src" / "_i18n" / "community.json").read_text(encoding="utf-8"))
NOW = "2026-10-15T15:00:00Z"


def sec(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def inline_script() -> str:
    src = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'<script>(\(function \(box\) \{\s*try \{\s*var KEY = "gv-wn-seen"[\s\S]*?'
                  r'\}\)\(document\.getElementById\("wn-since"\)\);)</script>', src)
    if not m:
        raise AssertionError("whats-new.njk: the line's script is not there")
    return m.group(1)


def s(key: str, lang: str) -> str:
    return STRINGS[key][lang]


# ------------------------------------------------------------------------------------------- when an entry appeared
class WhenAnEntryAppeared(unittest.TestCase):
    ITEMS = [
        # four stories of one issue the same day: one entry; one story found later does not make it new again
        *[{"id": f"a{i}", "source": "grapevine", "kind": "article", "category": "gv", "title": f"Story {i}", "lang": "en",
           "date": "2026-10-14T13:00:00Z", "first_seen": "2026-10-15T09:00:00Z" if i == 3 else "2026-10-14T13:05:00Z",
           "wn_date": "2026-10-14T13:00:00Z", "status": "ok",
           "extra": {"publication": "gv", "issue_key": "2026-11", "free": True}} for i in range(1, 5)],
        # an episode and its YouTube upload (the video found an hour later): one entry, from the episode
        {"id": "ep1", "source": "podcast", "kind": "episode", "title": "Gated Communities", "lang": "en",
         "date": "2026-10-15T10:00:00Z", "first_seen": "2026-10-15T10:10:00Z", "wn_date": "2026-10-15T10:00:00Z", "status": "ok",
         "extra": {}},
        {"id": "yt1", "source": "youtube", "kind": "video", "title": "Gated Communities", "lang": "en",
         "date": "2026-10-15T10:00:00Z", "first_seen": "2026-10-15T11:10:00Z", "wn_date": "2026-10-15T10:00:00Z", "status": "ok",
         "extra": {}},
        # YouTube dates it two weeks back; the site found it this morning
        {"id": "yt2", "source": "youtube", "kind": "video", "title": "An older talk", "lang": "en",
         "date": "2026-09-30T18:00:00Z", "first_seen": "2026-10-15T08:00:00Z", "wn_date": "2026-09-30T18:00:00Z", "status": "ok",
         "extra": {}},
        # a document dated by day only (noon UTC) found earlier that morning
        {"id": "pdf1", "source": "crawl", "kind": "pdf", "title": "LV News", "lang": "es",
         "date": "2026-10-15", "first_seen": "2026-10-15T08:30:00Z", "wn_date": "2026-10-15T12:00:00Z", "status": "ok",
         "extra": {}},
        # a bulletin post written on Oct 10 for Oct 14 (Central): from that day
        {"id": "b1", "source": "committee", "kind": "announcement", "title": "Workshop", "lang": "en",
         "date": "2026-10-10", "first_seen": "2026-10-10T16:00:00Z", "wn_date": "2026-10-14T05:00:00Z", "status": "ok",
         "extra": {"publish": "2026-10-14"}},
        # no first_seen: its news date
        {"id": "ev1", "source": "committee", "kind": "event", "title": "Assembly", "lang": "en",
         "date": "2026-11-07", "wn_date": "2026-10-13T20:00:00Z", "status": "ok", "extra": {}},
    ]

    def run_days(self):
        return run_js(self, r"""
          const days = filters.cmWnDays(filters.cmWnPrepare(input), "en");
          out({ entries: days.flatMap((d) => d.items.map((e) => [e.id, filters.cmWnSeen(e)])),
                list: filters.cmWnSeenList(days),
                none: [filters.cmWnSeen(null), filters.cmWnSeen({ id: "x", kind: "post" })] });""",
                      data=self.ITEMS, now=NOW)

    def test_each_entry_from_when_the_site_first_had_it(self):
        r = self.run_days()
        got = dict(r["entries"])
        self.assertEqual(got["bundle:gv|2026-11"], sec("2026-10-14T13:05:00Z"), "the issue: its first story")
        self.assertEqual(got["ep1"], sec("2026-10-15T10:10:00Z"), "the episode with its video: the first of them")
        self.assertNotIn("yt1", got, "the video is folded into its episode")
        self.assertEqual(got["yt2"], sec("2026-10-15T08:00:00Z"), "found today, whatever date YouTube gives it")
        self.assertEqual(got["pdf1"], sec("2026-10-15T08:30:00Z"), "a day-only news date never makes it later")
        self.assertEqual(got["b1"], sec("2026-10-14T05:00:00Z"), "a scheduled post: from its day")
        self.assertEqual(got["ev1"], sec("2026-10-13T20:00:00Z"), "no first_seen: its news date")
        self.assertEqual(r["none"], ["", ""])

    def test_the_pages_list_counts_a_folded_issue_as_its_stories(self):
        r = self.run_days()
        seen = dict(r["entries"])
        self.assertEqual(len(r["list"]), len(r["entries"]))
        self.assertEqual([x[0] for x in r["list"]], [seen[k] for k, _ in r["entries"]], "in the page's order")
        n = {k: x[1] for (k, _), x in zip(r["entries"], r["list"])}
        self.assertEqual(n["bundle:gv|2026-11"], 4)
        self.assertEqual({v for k, v in n.items() if k != "bundle:gv|2026-11"}, {1})


# ------------------------------------------------------------------------------------------- the page's own script
# The line as whats-new.njk renders it, in front of the feed: the x-data root with the day headings' "1 update" /
# "{n} updates", the list, the line (hidden) and the entries with their marks. input: { lang, store (the record, or
# null; "blocked": storage throws), now, list: [[seconds, items]], code } → what the script did.
RUN_LINE = PAGE_JS + r"""
const LINE = (c) => `<html lang="${c.lang}"><head></head><body>
  <div class="cm-wn-main" data-day-one="${c.one}" data-day-many="${c.many}" data-showing="${c.showing}">
    <script type="application/json" id="wn-seen">${JSON.stringify(c.list)}</script>
    <div id="wn-since" hidden data-line="${c.line}" data-earlier="${c.earlier}" data-read="${c.read}" data-forgot="${c.forgot}">
      <p><span data-wn-since-text></span></p>
    </div>
    <ol class="cm-days">
      ${c.days.map((d) => `<li class="cm-day" data-day="${d.ymd}" data-counts='{"post":${d.seen.length}}' data-total="${d.seen.length}"
          data-icounts='{"post":${d.seen.length}}' data-itotal="${d.seen.length}"><h2 class="cm-day-head">${d.ymd}</h2><ul>
        ${d.seen.map((x) => `<li class="cm-entry" data-kind="post" data-seen="${x}"><span class="cm-wn-new">New</span></li>`).join("")}
      </ul></li>`).join("")}
    </ol>
  </div></body></html>`;
function visit(c, store) {
  const p = page({ html: LINE(c), globals: { SITE: { tz: "America/Chicago" } } });
  p.win.__clock.now = Date.parse(c.now);
  if (store === "blocked") {
    p.win.localStorage = { getItem() { throw new Error("SecurityError"); }, setItem() { throw new Error("SecurityError"); }, removeItem() {} };
  } else if (store !== null && store !== undefined) {
    p.win.localStorage.setItem("gv-wn-seen", typeof store === "string" ? store : JSON.stringify(store));
  }
  vm.runInContext(c.code, p.win);
  const box = p.$("#wn-since"), css = p.$("#wn-since-css");
  let rec = null;
  if (store !== "blocked") { try { rec = JSON.parse(p.win.localStorage.getItem("gv-wn-seen")); } catch (e) { rec = "unreadable"; } }
  return { p, shown: !box.hidden, text: p.$("[data-wn-since-text]").textContent, css: css ? css.textContent : null, rec };
}
"""


class TheLine(unittest.TestCase):
    # three days of entries; the last visit's newest entry was Oct 13, 18:00
    DAYS = [
        {"ymd": "2026-10-15", "seen": [sec("2026-10-15T12:53:43Z"), sec("2026-10-15T12:46:57Z")]},
        {"ymd": "2026-10-14", "seen": [sec("2026-10-14T12:57:06Z")]},
        {"ymd": "2026-10-13", "seen": [sec("2026-10-13T18:00:00Z"), sec("2026-10-13T09:00:00Z")]},
    ]
    UPTO = sec("2026-10-13T18:00:00Z")
    LAST = "2026-10-13T20:15:00Z"            # Oct 13, 3:15 PM Central

    def case(self, lang="en", now=NOW, days=None, list_=None):
        days = days or self.DAYS
        lst = list_ if list_ is not None else [[x, 1] for d in days for x in d["seen"]]
        return {"lang": lang, "now": now, "days": days, "list": lst, "code": inline_script(),
                "one": s("community.wn.day_items_one", lang), "many": s("community.wn.day_items", lang),
                "showing": s("community.wn.showing", lang),
                "line": s("community.wn.since", lang), "earlier": s("community.wn.since_today", lang),
                "read": s("community.wn.since_read_done", lang), "forgot": s("community.wn.since_forgot", lang)}

    def record(self, last=None, upto=None, base=None):
        return {"upto": upto if upto is not None else self.UPTO,
                "last": int(datetime.fromisoformat((last or self.LAST).replace("Z", "+00:00")).timestamp() * 1000),
                "base": base}

    def visits(self, cases):
        """cases: [(case, store)] → each visit's result (without the page)."""
        return run_js(self, RUN_LINE + r"""
          out(input.map(([c, store]) => { const r = visit(c, store); delete r.p; return r; }));""",
                      data=cases, needs_modules=False)

    def test_nothing_on_a_first_visit_and_the_visit_is_remembered(self):
        (r,) = self.visits([(self.case(), None)])
        self.assertFalse(r["shown"])
        self.assertIsNone(r["css"])
        self.assertEqual(r["rec"], {"upto": sec("2026-10-15T12:53:43Z"), "last": int(datetime.fromisoformat(
            NOW.replace("Z", "+00:00")).timestamp() * 1000), "base": None})

    def test_a_later_visit_says_how_much_is_new_and_marks_exactly_those(self):
        (r,) = self.visits([(self.case(), self.record())])
        self.assertTrue(r["shown"])
        self.assertEqual(r["text"], "New since your last visit (Oct\u00a013): 3 updates")
        fresh = sorted(re.findall(r'data-seen="(\d+)"', r["css"]))
        self.assertEqual(fresh, sorted(str(x) for x in (sec("2026-10-15T12:53:43Z"), sec("2026-10-15T12:46:57Z"),
                                                        sec("2026-10-14T12:57:06Z"))))
        self.assertTrue(r["css"].endswith("{display:inline-flex}"))
        self.assertIn(".cm-wn-new", r["css"])
        self.assertEqual(r["rec"]["base"], {"upto": self.UPTO, "at": self.record()["last"]})
        self.assertEqual(r["rec"]["upto"], sec("2026-10-15T12:53:43Z"))

    def test_a_folded_issue_counts_its_stories_and_one_is_singular(self):
        days = [{"ymd": "2026-10-15", "seen": [sec("2026-10-15T12:00:00Z")]}, {"ymd": "2026-10-13", "seen": [self.UPTO]}]
        issue, single = self.visits([
            (self.case(days=days, list_=[[sec("2026-10-15T12:00:00Z"), 27], [self.UPTO, 1]]), self.record()),
            (self.case(days=days, list_=[[sec("2026-10-15T12:00:00Z"), 1], [self.UPTO, 1]]), self.record()),
        ])
        self.assertEqual(issue["text"], "New since your last visit (Oct\u00a013): 27 updates")
        self.assertEqual(single["text"], "New since your last visit (Oct\u00a013): 1 update")

    def test_a_reload_within_half_an_hour_is_the_same_visit(self):
        r = run_js(self, RUN_LINE + r"""
          const c = input.c;
          const one = visit(c, input.rec);
          const again = visit(Object.assign({}, c, { now: input.soon }), one.rec);      // a reload 20 minutes later
          const later = visit(Object.assign({}, c, { now: input.later }), again.rec);   // back the next day: nothing new
          out([one, again, later].map((r) => ({ shown: r.shown, text: r.text, base: r.rec.base })));""",
                   data={"c": self.case(), "rec": self.record(), "soon": "2026-10-15T15:20:00Z", "later": "2026-10-16T15:00:00Z"},
                   needs_modules=False)
        one, again, later = r
        self.assertEqual((one["shown"], again["shown"]), (True, True))
        self.assertEqual(again["text"], one["text"])
        self.assertEqual(again["base"], one["base"], "the same visit compares with the same one before it")
        self.assertFalse(later["shown"], "the next day, with no new entries: nothing")
        self.assertEqual(later["base"]["at"], int(datetime.fromisoformat("2026-10-15T15:20:00+00:00").timestamp() * 1000))

    def test_nothing_new_without_storage_or_with_a_record_it_cannot_read(self):
        same, blocked, junk, half = self.visits([
            (self.case(), self.record(upto=sec("2026-10-15T12:53:43Z"))),
            (self.case(), "blocked"),
            (self.case(), "{not json"),
            (self.case(), {"upto": "soon", "last": 1}),
        ])
        for name, r in (("nothing new", same), ("blocked storage", blocked), ("bad JSON", junk), ("bad record", half)):
            with self.subTest(name):
                self.assertFalse(r["shown"])
                self.assertIsNone(r["css"])
        self.assertIsNone(blocked["rec"], "nothing is remembered")
        self.assertIsNone(junk["rec"]["base"], "an unreadable record: a first visit")

    def test_earlier_today_another_year_and_spanish(self):
        today, year, es, es_today = self.visits([
            (self.case(), self.record(last="2026-10-15T13:00:00Z")),                           # 8:00 AM Central today
            (self.case(), self.record(last="2025-12-28T18:00:00Z")),
            (self.case("es"), self.record()),
            (self.case("es"), self.record(last="2026-10-15T13:00:00Z")),
        ])
        self.assertEqual(today["text"], "New since your last visit (earlier today): 3 updates")
        self.assertEqual(year["text"], "New since your last visit (Dec\u00a028,\u00a02025): 3 updates")
        self.assertEqual(es["text"], "Desde tu última visita (13\u00a0oct): 3 novedades")
        self.assertEqual(es_today["text"], "Desde tu última visita (hoy, más temprano): 3 novedades")

    def test_the_day_is_central_time(self):
        # 11:30 PM Central on Oct 13 is Oct 14 in UTC: the line says Oct 13, as the day headings would
        (r,) = self.visits([(self.case(), self.record(last="2026-10-14T04:30:00Z"))])
        self.assertEqual(r["text"], "New since your last visit (Oct\u00a013): 3 updates")


# ------------------------------------------------------------------------------------------- the buttons (community.js)
class TheButtons(unittest.TestCase):
    def run_page(self, script: str):
        c = TheLine.case(TheLine)
        rec = TheLine.record(TheLine)
        return run_js(self, RUN_LINE + r"""
          const c = input.c;
          const r = visit(c, input.rec), p = r.p;
          vm.runInContext(fs.readFileSync("src/assets/js/community.js", "utf8"), p.win, { filename: "community.js" });
          const comps = {};
          p.win.Alpine = { data: (name, fn) => { comps[name] = fn; } };
          p.fire(p.doc, "alpine:init");
          const root = p.$(".cm-wn-main");
          const w = Object.assign(comps.whatsNew({ cap: 6, days: 10 }), { $el: root, $root: root, $nextTick: (fn) => fn() });
          w.init();
          const store = () => { try { return JSON.parse(p.win.localStorage.getItem("gv-wn-seen")); } catch (e) { return "unreadable"; } };
          const state = () => ({ shown: !p.$("#wn-since").hidden, css: !!p.$("#wn-since-css"), status: w.status, rec: store(),
                                 focus: p.doc.activeElement.getAttribute("class"), tabindex: p.doc.activeElement.getAttribute("tabindex") });
        """ + script, data={"c": c, "rec": rec}, needs_modules=False)

    def test_mark_all_as_read(self):
        r = self.run_page(r"""
          const before = state();
          w.sinceDone(false);
          const after = state();
          p.win.__clock.now = Date.parse("2026-10-15T15:20:00Z");
          vm.runInContext(c.code, p.win);                      // a reload in the same visit: nothing comes back
          out({ before, after, reload: state(), errors: p.errors.map(String) });""")
        self.assertEqual((r["before"]["shown"], r["before"]["css"]), (True, True))
        a = r["after"]
        self.assertEqual((a["shown"], a["css"]), (False, False))
        self.assertIsNone(a["rec"]["base"], "the next visit counts from this one")
        self.assertEqual(a["rec"]["upto"], sec("2026-10-15T12:53:43Z"))
        self.assertEqual(a["status"], s("community.wn.since_read_done", "en"))
        self.assertEqual((a["focus"], a["tabindex"]), ("cm-day-head", "-1"), "focus: the first day's heading")
        self.assertEqual((r["reload"]["shown"], r["reload"]["css"]), (False, False))
        self.assertEqual(r["errors"], [])

    def test_forget_my_last_visit(self):
        r = self.run_page(r"""
          w.sinceDone(true);
          const after = state();
          p.fire(p.win, "pagehide");                           // leaving the page never brings the record back
          const left = state();
          p.win.__clock.now = Date.parse("2026-10-16T15:00:00Z");
          vm.runInContext(c.code, p.win);                      // the next visit: a first one again
          out({ after, left, next: state() });""")
        self.assertEqual((r["after"]["shown"], r["after"]["css"], r["after"]["rec"]), (False, False, None))
        self.assertEqual(r["after"]["status"], s("community.wn.since_forgot", "en"))
        self.assertEqual(r["after"]["focus"], "cm-day-head")
        self.assertIsNone(r["left"]["rec"])
        self.assertFalse(r["next"]["shown"])
        self.assertIsNone(r["next"]["rec"]["base"])

    def test_leaving_the_page_keeps_the_visits_time(self):
        r = self.run_page(r"""
          p.win.__clock.now = Date.parse("2026-10-15T15:25:00Z");
          p.fire(p.win, "pagehide");
          out(state().rec);""")
        self.assertEqual(r["last"], int(datetime.fromisoformat("2026-10-15T15:25:00+00:00").timestamp() * 1000))
        self.assertEqual(r["base"]["upto"], TheLine.UPTO, "the visit before is kept")


# ------------------------------------------------------------------------------------------- the template
class TheTemplate(unittest.TestCase):
    def setUp(self):
        self.src = TEMPLATE.read_text(encoding="utf-8")

    def test_both_kinds_of_entry_carry_the_time_and_the_mark(self):
        self.assertEqual(self.src.count('data-seen="{{ it | cmWnSeen }}"'), 2)
        self.assertEqual(self.src.count('<span class="cm-wn-new badge-new">{{ newForYou }}</span>'), 2)
        self.assertIn('{%- set newForYou = "community.wn.since_pill" | t(lang) -%}', self.src)
        css = (ROOT / "src" / "assets" / "css" / "areas" / "community.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"(?m)^\.cm-wn-new \{ display: none; \}$", "the mark is hidden unless the script shows it")

    def test_the_line_is_hidden_without_javascript_and_comes_before_the_feed(self):
        at = self.src.index('<div id="wn-since"')
        self.assertIn(" hidden\n", self.src[at:self.src.index(">", self.src.index("data-forgot", at))])
        self.assertLess(self.src.index('<script type="application/json" id="wn-seen">'), at)
        self.assertLess(at, self.src.index('var KEY = "gv-wn-seen"'))
        self.assertLess(self.src.index('var KEY = "gv-wn-seen"'), self.src.index('<ol class="cm-days'))
        self.assertIn('@click="sinceDone(false)"', self.src)
        self.assertIn('@click="sinceDone(true)"', self.src)
        self.assertNotIn("{{", inline_script())
        self.assertNotIn("{%", inline_script())

    def test_strings_in_both_languages(self):
        keys = ("since", "since_today", "since_pill", "since_read", "since_note", "since_forget", "since_read_done",
                "since_forgot")
        for k in keys:
            with self.subTest(k):
                v = STRINGS[f"community.wn.{k}"]
                self.assertTrue(v["en"].strip() and v["es"].strip())
                self.assertNotEqual(v["en"], v["es"])
                self.assertIn(f"community.wn.{k}", self.src)
        for lang in ("en", "es"):
            self.assertIn("{date}", s("community.wn.since", lang))
            self.assertIn("{count}", s("community.wn.since", lang))
        self.assertIn("this device", s("community.wn.since_note", "en"))
        self.assertIn("este dispositivo", s("community.wn.since_note", "es"))


if __name__ == "__main__":
    unittest.main()
