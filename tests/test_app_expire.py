"""Things whose time has passed hide themselves between the daily builds (src/assets/js/app.js GV.expire):

  * [data-gv-expire="<ISO instant>"] — hidden (and data-gv-expired) once that moment has passed; a bare date
    or anything else that is not a moment with its zone is ignored;
  * [data-gv-expire-list] — hidden once every [data-gv-expire-item] inside it is hidden, and its
    data-gv-expire-empty="#id" note shown instead; a [data-gv-expire-spare="<class>"] item (the home page's
    4th event, hidden on a phone) drops that class once an earlier item has gone;
  * [data-gv-expire-count] — a number of things that end (the committee pages' Events and Bulletin counts,
    the home page's "See the 3 upcoming themes") goes down as they end, and is hidden at 0 (Counts);
  * the attributes are GV.expire's alone: committee.js and read.js, which hide their own [data-cm-expire]
    (their own marker, counts and lists), never see them (committee.js is loaded on /bulletin/ too);
  * the element holding keyboard focus (or a list around it) is never hidden under the reader — it goes once
    focus leaves it; committee.js (/events/, /meetings/) and read.js (/contribute/'s next workshops) keep the
    same rule for their [data-cm-expire] (CommitteeExpire, WorkshopsExpire); a [data-gv-from] part whose old
    state, right before it, still holds focus waits with it — the two swap together (/shop/'s price lists);
  * it runs when the page is ready, every minute and when the page is shown again — and so do the monthly
    toolkit's "Over" marks (monthly.js), /contribute/'s next workshops (read.js) and the digest's "last
    month's edition" note (community.js): PageLeftOpen;
  * the moments come from eleventy/filters/freshness.js fsDayEnd (the end of a Central-time day: a post's
    `expires`, a story deadline) and home.js homeEventEnd (the end of an event, as the home page's
    upcoming-events row counts it); the home page and /bulletin/ carry the attributes.

app.js (and committee.js, read.js) run in a Node.js vm with a small stand-in for the page (elements with
attributes, `hidden`, contains(), focus, listeners, a clock and timers the test moves by hand).

    python -m unittest tests.test_app_expire -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# The page stand-in: el(tag, attrs, children) builds elements; `page(children, files)` loads app.js (or the
# given scripts, in order) on a document holding them → { G (window.GV), doc, win, clock: {now}, timers,
# intervals, fire(type) (DOMContentLoaded …), run() (due timeouts) }. document.readyState is "loading", so
# the scripts wait for DOMContentLoaded.
DOM = r"""
import vm from "node:vm";
class El {
  constructor(tag, attrs, children) {
    this.tagName = String(tag).toUpperCase();
    this.attrs = Object.assign({}, attrs || {});
    this.children = children || [];
    this.parent = null;
    for (const c of this.children) c.parent = this;
    this.hidden = "hidden" in this.attrs;
    this.listeners = {};
    this.style = {};
    const self = this, cls = () => String(self.attrs.class || "").split(/\s+/).filter(Boolean);
    this.classList = {
      add(c) { if (!cls().includes(c)) self.attrs.class = [...cls(), c].join(" "); },
      remove(c) { self.attrs.class = cls().filter((x) => x !== c).join(" "); },
      toggle(c, on) { if (on === undefined ? !cls().includes(c) : on) this.add(c); else this.remove(c); },
      contains: (c) => cls().includes(c),
    };
  }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = String(v); }
  hasAttribute(n) { return n in this.attrs; }
  removeAttribute(n) { delete this.attrs[n]; }
  contains(o) { for (let n = o; n; n = n.parent) if (n === this) return true; return false; }
  get previousElementSibling() { const s = this.parent ? this.parent.children : []; const i = s.indexOf(this); return i > 0 ? s[i - 1] : null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  *walk() { for (const c of this.children) { yield c; yield* c.walk(); } }
  // "[attr]" selectors, comma-separated (all this script's own); anything else finds nothing
  querySelectorAll(sel) {
    const parts = String(sel).split(",").map((s) => s.trim());
    const want = parts.every((p) => /^\[[\w-]+\]$/.test(p)) ? parts.map((p) => p.slice(1, -1)) : null;
    const byId = /^#([\w-]+)$/.exec(String(sel).trim());
    return [...this.walk()].filter((e) => (want ? want.some((a) => e.hasAttribute(a)) : byId ? e.attrs.id === byId[1] : false));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(t, fn, o) { (this.listeners[t] ||= []).push({ fn, once: !!(o && o.once) }); }
  dispatch(t, ev) { const ls = this.listeners[t] || []; this.listeners[t] = ls.filter((l) => !l.once); for (const l of ls) l.fn(Object.assign({ type: t }, ev || {})); }
}
const el = (tag, attrs, children) => new El(tag, attrs, children);
const page = (children, files) => {
  const clock = { now: Date.parse("2026-10-03T20:00:00Z") };
  const timers = [], intervals = [];
  class FakeDate extends Date { static now() { return clock.now; } }
  const body = el("body", {}, children || []);
  const root = el("html", { lang: "en" }, [body]);
  const docListeners = {}, winListeners = {};
  const doc = {
    readyState: "loading", documentElement: root, body, activeElement: body, visibilityState: "visible",
    addEventListener: (t, fn) => { (docListeners[t] ||= []).push(fn); },
    querySelectorAll: (s) => root.querySelectorAll(s), querySelector: (s) => root.querySelector(s),
    getElementById: (id) => root.querySelector("#" + id),
    createElement: (t) => el(t),
  };
  const win = {
    addEventListener: (t, fn) => { (winListeners[t] ||= []).push(fn); },
    dispatchEvent() {}, matchMedia: () => ({ matches: false }),
  };
  const ctx = {
    console, JSON, Math, Object, Array, String, Number, RegExp, Intl, Promise, isNaN, isFinite, Date: FakeDate,
    document: doc, navigator: {}, localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setTimeout: (fn, ms) => { timers.push({ fn, at: clock.now + (ms || 0) }); return timers.length; },
    clearTimeout() {}, setInterval: (fn, ms) => { intervals.push({ fn, ms }); return intervals.length; },
    NodeFilter: {}, CustomEvent: function () {}, URLSearchParams,
    location: { hash: "", search: "", pathname: "/" }, history: { replaceState() {} },
  };
  ctx.window = Object.assign(ctx, win);
  vm.createContext(ctx);
  for (const f of files || ["src/assets/js/app.js"]) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
  const run = () => { const due = timers.splice(0).filter((t) => t.at <= clock.now); due.forEach((t) => t.fn()); };
  const fire = (t, ev) => { for (const fn of docListeners[t] || []) fn(Object.assign({ type: t }, ev || {})); };
  const fireWin = (t, ev) => { for (const fn of winListeners[t] || []) fn(Object.assign({ type: t }, ev || {})); };
  return { G: ctx.GV, doc, win: ctx, clock, timers, intervals, run, fire, fireWin };
};
const PAST = "2026-10-03T19:00:00Z", SOON = "2026-10-03T21:30:00.000Z", LATER = "2026-10-15T05:00:00.000Z";
"""


def js(case: unittest.TestCase, script: str):
    return run_js(case, DOM + script, needs_modules=False, timeout=60)


class Expire(unittest.TestCase):
    def test_passed_moments_hide_and_future_ones_stay(self):
        r = js(self, r"""
          const a = el("li", { "data-gv-expire": PAST }), b = el("li", { "data-gv-expire": LATER }),
                c = el("li", { "data-gv-expire": "2026-10-03T14:00:00-05:00" }), d = el("li", { "data-gv-expire": "2026-10-03T13:59-05:00" });
          const p = page([a, b, c, d]);
          const n = p.G.expire();
          out({ n, a: [a.hidden, a.hasAttribute("data-gv-expired")], b: [b.hidden, b.hasAttribute("data-gv-expired")],
                c: c.hidden, d: d.hidden, again: p.G.expire() });""")
        self.assertEqual(r["n"], 3)
        self.assertEqual(r["a"], [True, True])
        self.assertEqual(r["b"], [False, False])
        self.assertTrue(r["c"], "an offset instant (-05:00) is a moment too")
        self.assertTrue(r["d"], "without seconds too")
        self.assertEqual(r["again"], 0, "idempotent: a second pass hides nothing more")

    def test_bare_dates_and_junk_are_ignored(self):
        r = js(self, r"""
          // a bare date (no moment), no zone (the visitor's own clock), a compact zone some browsers
          // cannot read, words, nothing, a space instead of the T
          const vals = ["2026-10-01", "2026-10-01T05:00", "2026-10-01T05:00-0500", "soon", "", "2026-10-01 05:00Z", "yesterdayT00:00:00Z"];
          const els = vals.map((v) => el("li", { "data-gv-expire": v }));
          const p = page(els);
          out({ n: p.G.expire(), hidden: els.map((e) => e.hidden) });""")
        self.assertEqual(r["n"], 0)
        self.assertEqual(r["hidden"], [False] * 7)

    def test_a_list_goes_when_all_its_items_have(self):
        r = js(self, r"""
          const i1 = el("article", { "data-gv-expire-item": "", "data-gv-expire": PAST });
          const i2 = el("article", { "data-gv-expire-item": "", "data-gv-expire": SOON });
          const list = el("section", { "data-gv-expire-list": "", "data-gv-expire-empty": "#none" }, [el("h2"), i1, i2]);
          const note = el("div", { id: "none", hidden: "" });
          // a list with an item that never expires (an evergreen theme) never goes
          const keep = el("ul", { "data-gv-expire-list": "" }, [el("li", { "data-gv-expire-item": "", "data-gv-expire": PAST }), el("li", { "data-gv-expire-item": "" })]);
          const p = page([list, note, keep]);
          p.G.expire();
          const first = { list: list.hidden, i1: i1.hidden, i2: i2.hidden, note: note.hidden };
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          const n = p.G.expire();
          out({ first, n, list: list.hidden, i2: i2.hidden, note: note.hidden, keep: keep.hidden });""")
        self.assertEqual(r["first"], {"list": False, "i1": True, "i2": False, "note": True})
        self.assertEqual(r["n"], 2)                      # the last item, then its list
        self.assertTrue(r["list"])
        self.assertFalse(r["note"], "the empty note shows instead")
        self.assertFalse(r["keep"])

    def test_a_spare_steps_in_for_an_item_that_has_gone(self):
        # The home page's events on a phone: three, and a 4th hidden there by a class (max-sm:hidden). Once
        # the first has ended the 4th shows in its place; the section goes only when all four have.
        r = js(self, r"""
          const at = ["2026-10-03T19:00:00Z", "2026-10-03T21:00:00Z", "2026-10-03T22:00:00Z", "2026-10-03T23:00:00Z"];
          const ev = at.map((t, i) => el("li", Object.assign({ "data-gv-expire-item": "", "data-gv-expire": t },
                                                           i === 3 ? { class: "max-sm:hidden", "data-gv-expire-spare": "max-sm:hidden" } : {})));
          const cta = el("li", { class: "home-cal-cta" });             // not an item: never counted
          const list = el("section", { "data-gv-expire-list": "" }, [el("h2"), el("ul", {}, [...ev, cta])]);
          const p = page([list]);
          const seen = [];
          const snap = () => seen.push({ shown: ev.map((e) => !e.hidden), spareClass: ev[3].getAttribute("class"), list: list.hidden });
          snap();                                                     // 20:00: nothing over yet
          p.G.expire(); snap();                                       // the 19:00 one is over
          p.clock.now = Date.parse("2026-10-03T22:30:00Z"); p.G.expire(); snap();
          p.clock.now = Date.parse("2026-10-03T23:30:00Z"); p.G.expire(); snap();
          out(seen);""")
        self.assertEqual(r[0], {"shown": [True, True, True, True], "spareClass": "max-sm:hidden", "list": False})
        self.assertEqual(r[1], {"shown": [False, True, True, True], "spareClass": "", "list": False},
                         "one gone: the spare shows on a phone too")
        self.assertEqual(r[2], {"shown": [False, False, False, True], "spareClass": "", "list": False})
        self.assertEqual(r[3], {"shown": [False, False, False, False], "spareClass": "", "list": True})

    def test_a_spare_that_ended_first_steps_in_for_nobody(self):
        r = js(self, r"""
          const a = el("li", { "data-gv-expire-item": "", "data-gv-expire": LATER });
          const s = el("li", { "data-gv-expire-item": "", "data-gv-expire": PAST, class: "max-sm:hidden", "data-gv-expire-spare": "max-sm:hidden" });
          const list = el("ul", { "data-gv-expire-list": "" }, [a, s]);
          const p = page([list]);
          p.G.expire();
          out({ a: a.hidden, s: s.hidden, cls: s.getAttribute("class"), list: list.hidden });""")
        self.assertEqual(r, {"a": False, "s": True, "cls": "max-sm:hidden", "list": False})

    def test_the_focused_element_is_never_hidden_under_the_reader(self):
        r = js(self, r"""
          const link = el("a", { href: "#" });
          const card = el("li", { "data-gv-expire-item": "", "data-gv-expire": PAST }, [link]);
          const head = el("a", { href: "/events/" });
          const list = el("section", { "data-gv-expire-list": "" }, [head, card]);
          const p = page([list]);
          p.doc.activeElement = link;
          const n0 = p.G.expire();
          const kept = card.hidden;
          p.doc.activeElement = head;                  // focus moves on (Tab) — still inside the list
          card.dispatch("focusout");
          p.run();
          const cardAfter = card.hidden, listWhileFocused = list.hidden;
          p.doc.activeElement = p.doc.body;            // focus leaves the list
          list.dispatch("focusout");
          p.run();
          out({ n0, kept, cardAfter, listWhileFocused, list: list.hidden });""")
        self.assertEqual(r["n0"], 0)
        self.assertFalse(r["kept"])
        self.assertTrue(r["cardAfter"], "hidden once focus left the card")
        self.assertFalse(r["listWhileFocused"], "the list holding focus stays")
        self.assertTrue(r["list"])

    def test_a_pair_swaps_together_once_focus_leaves_the_old_state(self):
        # /shop/ at midnight Central on January 1: a plan card holds its two price lists (data-gv-expire, then
        # data-gv-from at the same moment). The old list's Buy link still has keyboard focus (the store opened in
        # a new tab, the visitor comes back after midnight): the old list stays — and the new one waits with it,
        # never two lists with two prices for one plan; both swap once focus leaves.
        r = js(self, r"""
          const buy = el("a", { href: "#" });
          const old = el("ul", { "data-gv-when": "", "data-gv-expire": PAST }, [el("li", {}, [buy])]);
          const neu = el("ul", { "data-gv-when": "", "data-gv-from": PAST, hidden: "" }, [el("li", {}, [el("a", { href: "#" })])]);
          // a part whose moment has come with no old state right before it shows at once
          const note = el("span", { "data-gv-when": "", "data-gv-from": PAST, hidden: "" });
          const card = el("article", {}, [el("header"), old, neu, el("p", {}, [note])]);
          const p = page([card]);
          p.doc.activeElement = buy;
          p.G.expire();
          const during = { old: old.hidden, neu: neu.hidden, note: note.hidden };
          p.doc.activeElement = p.doc.body;            // focus leaves the old list
          old.dispatch("focusout");
          p.run();
          out({ during, after: { old: old.hidden, neu: neu.hidden, started: neu.hasAttribute("data-gv-started") } });""")
        self.assertEqual(r["during"], {"old": False, "neu": True, "note": False}, "exactly one price list while focus holds the old one")
        self.assertEqual(r["after"], {"old": True, "neu": False, "started": True})

    def test_runs_when_ready_every_minute_and_when_shown_again(self):
        r = js(self, r"""
          const a = el("li", { "data-gv-expire-item": "", "data-gv-expire": PAST });
          const b = el("li", { "data-gv-expire-item": "", "data-gv-expire": SOON });
          const c = el("li", { "data-gv-expire-item": "", "data-gv-expire": "2026-10-03T22:00:00Z" });
          const p = page([el("ul", { "data-gv-expire-list": "" }, [a, b, c])]);
          const before = a.hidden;
          p.fire("DOMContentLoaded");
          const ready = a.hidden, every = p.intervals.map((i) => i.ms);
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals[0].fn();
          const minute = b.hidden;
          p.clock.now = Date.parse("2026-10-03T22:05:00Z");
          p.fire("visibilitychange");
          out({ before, ready, every, minute, shown: c.hidden });""")
        self.assertFalse(r["before"])
        self.assertTrue(r["ready"])
        self.assertEqual(r["every"], [60000])
        self.assertTrue(r["minute"])
        self.assertTrue(r["shown"])

    def test_a_page_without_them_starts_nothing(self):
        r = js(self, r"""
          const p = page([el("p")]);
          p.fire("DOMContentLoaded");
          out({ intervals: p.intervals.length });""")
        self.assertEqual(r["intervals"], 0)


class Counts(unittest.TestCase):
    """[data-gv-expire-count]: a number of things that end — the committee pages' Events and Bulletin counts,
    the home page's "See the 3 upcoming themes" — goes down as they end between builds, and is hidden at 0
    (never while it holds keyboard focus). Before, /bulletin/'s sub-nav kept "Bulletin 3" next to "Nothing
    on the bulletin right now" once every post had expired."""

    def test_the_number_goes_down_and_goes_at_zero(self):
        r = js(self, r"""
          const n = el("span", { "data-gv-expire-count": [PAST, SOON, LATER, "-"].join(" ") });
          n.textContent = "4";
          const text = el("span", { "data-gv-expire-text": "" });
          const link = el("a", { href: "#", "data-gv-expire-count": SOON + " 2026-10-03T21:45:00Z",
                                 "data-gv-expire-one": "See the upcoming theme", "data-gv-expire-n": "See the {n} upcoming themes" }, [text]);
          const p = page([n, link]);
          p.fire("DOMContentLoaded");
          const boot = [n.textContent, text.textContent, link.hidden];
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();
          const minute = [n.textContent, text.textContent, link.hidden];
          p.doc.activeElement = link;                      // it has keyboard focus when its last theme ends
          p.clock.now = Date.parse("2026-10-03T21:46:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();
          const focused = link.hidden;
          p.doc.activeElement = p.doc.body;
          link.dispatch("focusout");
          p.run();
          out({ boot, minute, focused, after: [link.hidden, n.hidden, n.textContent] });""")
        self.assertEqual(r["boot"], ["3", "See the 2 upcoming themes", False], "one had ended already")
        self.assertEqual(r["minute"], ["2", "See the upcoming theme", False])
        self.assertFalse(r["focused"], "never hidden under the reader")
        self.assertEqual(r["after"], [True, False, "2"], "gone once focus left it; '-' never ends")

    def test_the_committee_counts_carry_their_moments(self):
        # committeeNav writes one moment per thing it counts: an event's end (the instant /events/ hides its
        # card at), a monthly series once — its last listed date's —, a post's `expires` day end ("-": none)
        ev = lambda iid, start, end, **x: {"id": iid, "kind": "event", "status": "ok", "source": "committee", "category": x.pop("category", "manual"),
                                           "title": iid, "url": "/events/", "date": start, "lang": "en", "i18n": {}, "machine": [],
                                           "extra": {"start": start, "end": end, **x}}
        ann = lambda iid, **x: {"id": iid, "kind": "announcement", "status": "ok", "source": "committee", "title": iid, "date": "2030-01-02",
                                "lang": "en", "i18n": {}, "machine": [], "extra": {"slug": iid, **x}}
        db = {"events": {"items": [
                  ev("ev:ws", "2030-03-02T15:00:00Z", "2030-03-02T18:00:00Z"),
                  ev("ev:rec:1", "2030-03-09T23:00:00Z", "2030-03-10T02:00:00Z", category="recurring", recurring=True, series="booth"),
                  ev("ev:rec:2", "2030-04-13T23:00:00Z", "2030-04-14T02:00:00Z", category="recurring", recurring=True, series="booth")]},
              "announcements": {"items": [ann("ann:a", expires="2030-01-14"), ann("ann:b"), ann("ann:old", expires="2020-01-01")]},
              "drive": {"items": []}}
        html = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const sc = {};
          C.default(new Proxy({}, { get: (_t, name) => (name === "addShortcode" ? (n, fn) => { sc[n] = fn; } : () => {}) }));
          out(sc.committeeNav("en", "bulletin", input.db));""", data={"db": db})
        import re
        counts = dict(re.findall(r'href="/(events|bulletin)/"[^>]*>(?:(?!</a>).)*?<span class="cm-subnav-count" data-gv-expire-count="([^"]*)">\d+</span>',
                                 html, re.S))
        self.assertEqual(counts["events"].split(), ["2030-03-02T18:00:00.000Z", "2030-04-14T02:00:00.000Z"])
        self.assertEqual(counts["bulletin"].split(), ["2030-01-15T06:00:00.000Z", "-"])
        self.assertNotIn('data-gv-expire-count', re.search(r'href="/meetings/".*?</a>', html, re.S).group(0))


class CommitteeExpire(unittest.TestCase):
    """committee.js expire() (/events/ cards, /meetings/ dates): a passed [data-cm-expire] moment hides its
    element (data-cm-expired) and a [data-cm-max] list shows its first N left — but the element that holds
    keyboard focus is never hidden under the reader: it goes once focus leaves it (GV.expire's rule)."""

    def test_passed_moments_hide_and_the_list_keeps_its_first_n(self):
        r = js(self, r"""
          const items = [PAST, SOON, LATER, LATER].map((t) => el("li", { "data-cm-expire": t }));
          const list = el("ul", { "data-cm-max": "2" }, items);
          const p = page([list], ["src/assets/js/committee.js"]);
          const boot = items.map((i) => [i.hidden, i.hasAttribute("data-cm-expired"), i.classList.contains("hidden")]);
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();
          // what shows: gone, or [hidden by the list's max, the first one left]
          out({ boot, minute: items.map((i) => (i.hidden ? "gone" : [i.classList.contains("hidden"), i.classList.contains("is-next")])) });""")
        self.assertEqual(r["boot"], [[True, True, False], [False, False, False], [False, False, False], [False, False, True]])
        self.assertEqual(r["minute"], ["gone", "gone", [False, True], [False, False]])

    def test_the_focused_element_is_never_hidden_under_the_reader(self):
        r = js(self, r"""
          const link = el("a", { href: "#" });
          const card = el("li", { "data-cm-expire": SOON }, [link]);
          const other = el("li", { "data-cm-expire": "2026-10-03T21:00:00Z" });
          const next = el("li", { "data-cm-expire": LATER });
          const list = el("ul", { "data-cm-max": "2" }, [card, other, next]);
          const p = page([list], ["src/assets/js/committee.js"]);
          p.doc.activeElement = link;                    // the card's link has keyboard focus …
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();  // … when both events are over (the minute tick)
          const tick = { card: card.hidden, marked: card.hasAttribute("data-cm-expired"), other: other.hidden,
                         nextShown: !next.classList.contains("hidden") };
          const link2 = el("a", { href: "#" });
          card.appendChild(link2);
          p.doc.activeElement = link2;                   // Tab to another link in the same card: still there
          card.dispatch("focusout");
          p.run();
          const moved = card.hidden;
          p.doc.activeElement = p.doc.body;              // focus leaves the card
          card.dispatch("focusout");
          p.run();
          out({ tick, moved, after: [card.hidden, card.hasAttribute("data-cm-expired")], nextFirst: next.classList.contains("is-next") });""")
        self.assertEqual(r["tick"], {"card": False, "marked": False, "other": True, "nextShown": True})
        self.assertFalse(r["moved"], "focus is still inside the card")
        self.assertEqual(r["after"], [True, True], "hidden once focus left it")
        self.assertTrue(r["nextFirst"], "the list is counted again without it")


class WorkshopsExpire(unittest.TestCase):
    """read.js on /contribute/ ("Next workshops", [data-ws-list]): a workshop that has ended hides itself, and
    the list with it when none is left — never the row that holds keyboard focus (GV.expire's rule)."""

    def test_the_focused_row_waits_then_the_list_goes(self):
        r = js(self, r"""
          const link = el("a", { href: "#" });
          const row = el("li", { "data-cm-expire": PAST }, [link]);
          const gone = el("li", { "data-cm-expire": PAST });
          const list = el("ul", { "data-ws-list": "" }, [gone, row]);
          const p = page([list], ["src/assets/js/read.js"]);
          p.doc.activeElement = link;
          p.fire("DOMContentLoaded");
          const kept = { gone: gone.hidden, row: row.hidden, list: list.hidden };
          p.doc.activeElement = p.doc.body;
          row.dispatch("focusout");
          p.run();
          out({ kept, after: { row: row.hidden, list: list.hidden } });""")
        self.assertEqual(r["kept"], {"gone": True, "row": False, "list": False})
        self.assertEqual(r["after"], {"row": True, "list": True})

    def test_rows_still_to_come_stay(self):
        r = js(self, r"""
          const a = el("li", { "data-cm-expire": PAST }), b = el("li", { "data-cm-expire": LATER });
          const list = el("ul", { "data-ws-list": "" }, [a, b]);
          const p = page([list], ["src/assets/js/read.js"]);
          p.fire("DOMContentLoaded");
          out([a.hidden, b.hidden, list.hidden]);""")
        self.assertEqual(r, [True, False, False])


class PageLeftOpen(unittest.TestCase):
    """The other between-builds marks keep time like GV.expire and committee.js: now, every minute and when the
    page is shown again — a month page shown at a district meeting marks the meeting "Over" as it ends
    (monthly.js), /contribute/'s next workshops drop one that has ended (read.js), and the digest says it is
    last month's edition once the new one is due (community.js digestPage). Before, only a reload or a tab
    switch did it, so a page left open kept a finished meeting without "Over"."""

    def test_the_toolkit_marks_over_every_minute(self):
        r = js(self, r"""
          const link = el("a", { href: "#" });
          const chip = el("li", { "data-mp-chip": "", "data-mp-over": SOON }, [link]);
          const later = el("li", { "data-mp-chip": "", "data-mp-over": LATER });
          const chips = el("ul", { "data-mp-chips": "" }, [chip, later]);
          const badge = el("span", { "data-mp-over-badge": "", hidden: "" });
          const row = el("li", { "data-mp-over": SOON }, [badge]);
          const p = page([chips, row], ["src/assets/js/monthly.js"]);
          p.fire("DOMContentLoaded");
          const boot = [chip.hidden, row.classList.contains("is-past"), badge.hidden];
          p.doc.activeElement = link;                    // the chip's link has keyboard focus when it ends
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();
          const minute = [chip.hidden, row.classList.contains("is-past"), badge.hidden, chips.hidden];
          p.doc.activeElement = p.doc.body;              // focus leaves it: it goes
          chip.dispatch("focusout");
          p.run();
          const after = [chip.hidden, later.hidden, chips.hidden];
          p.clock.now = Date.parse("2026-10-16T00:00:00Z");
          p.fireWin("pageshow", { persisted: true });    // a page restored by the Back button
          out({ boot, minute, after, restored: [later.hidden, chips.hidden] });""")
        self.assertEqual(r["boot"], [False, False, True])
        self.assertEqual(r["minute"], [False, True, False, False], "the row is Over; the focused chip waits")
        self.assertEqual(r["after"], [True, False, False])
        self.assertEqual(r["restored"], [True, True], "the last chip, then its list")

    def test_the_next_workshops_drop_one_that_ended(self):
        r = js(self, r"""
          const a = el("li", { "data-cm-expire": SOON }), b = el("li", { "data-cm-expire": LATER });
          const list = el("ul", { "data-ws-list": "" }, [a, b]);
          const p = page([list], ["src/assets/js/read.js"]);
          p.fire("DOMContentLoaded");
          const boot = [a.hidden, b.hidden];
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();
          const minute = [a.hidden, b.hidden, list.hidden];
          p.clock.now = Date.parse("2026-10-16T00:00:00Z");
          p.fireWin("pageshow", { persisted: true });
          out({ boot, minute, restored: [b.hidden, list.hidden] });""")
        self.assertEqual(r["boot"], [False, False])
        self.assertEqual(r["minute"], [True, False, False])
        self.assertEqual(r["restored"], [True, True])

    def test_the_digest_notices_it_is_last_months(self):
        r = js(self, r"""
          const p = page([], ["src/assets/js/community.js"]);
          const comps = {};
          p.win.Alpine = { data: (name, fn) => { comps[name] = fn; } };
          p.fire("alpine:init");
          const c = comps.digestPage();
          Object.assign(c, { $el: el("div", { "data-stale-after": SOON }), $watch() {} });
          c.init();
          const boot = c.stale;
          p.clock.now = Date.parse("2026-10-03T21:31:00Z");
          p.intervals.find((i) => i.ms === 60000).fn();
          out({ boot, minute: c.stale });""")
        self.assertEqual(r, {"boot": False, "minute": True})


class Moments(unittest.TestCase):
    """fsDayEnd (freshness.js) and homeEventEnd (home.js): the instants the pages write."""

    def test_day_end_in_central_time(self):
        r = run_js(self, """
          const f = filters.fsDayEnd;
          out(["2026-10-14", "2026-12-14", "2026-10-31", "2027-03-13", "2026-10-14T09:00:00Z", "2026-02-30", "soon", "", null, 20261014]
              .map((v) => f(v)));""")
        self.assertEqual(r, ["2026-10-15T05:00:00.000Z", "2026-12-15T06:00:00.000Z", "2026-11-01T05:00:00.000Z",
                             "2027-03-14T06:00:00.000Z", "2026-10-15T05:00:00.000Z", "", "", "", "", ""])

    def test_event_end_as_the_home_page_counts_it(self):
        r = run_js(self, """
          const f = filters.homeEventEnd;
          out([
            f({ date: "2026-10-03T19:00:00Z", extra: { start: "2026-10-03T19:00:00Z", end: "2026-10-03T22:00:00Z" } }),
            f({ date: "2026-10-03T19:00:00Z", extra: { start: "2026-10-03T19:00:00Z" } }),
            f({ date: "2027-03-19", extra: { start: "2027-03-19", end: "2027-03-21", all_day: true } }),
            f({ date: "2026-11-07", extra: { start: "2026-11-07", all_day: true } }),
            f({ extra: {} }),
            f(null),
          ]);""")
        # a timed event without an end: one hour (committee.js eventSpan — every page's rule, OneEndRule)
        self.assertEqual(r, ["2026-10-03T22:00:00.000Z", "2026-10-03T20:00:00.000Z", "2027-03-22T05:00:00.000Z",
                             "2026-11-08T06:00:00.000Z", "", ""])


class OneEndRule(unittest.TestCase):
    """Every page that lists an event says it is over at the SAME instant — /events/ and /meetings/
    (committee.js normalizeEvents → the card's data-cm-expire and the calendars' end), the home page
    (homeEventEnd → data-gv-expire), the monthly toolkit (monthModel dates[].overAt → data-mp-over) and the
    district report (upcomingEvents lists it until then) — through committee.js eventSpan. Before, a timed
    event without an end was over after 1 hour on /events/, 2 on the home page and 6 in the toolkit and the
    report, so between builds the pages disagreed for five hours."""
    SITE = {"url": "https://example.org/site", "title": "Grapevine / La Viña", "recurring_events": [],
            "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Zoom"}}

    def test_the_pages_agree(self):
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const M = await imp("eleventy/filters/monthly.js");
          const R = await imp("eleventy/filters/report.js");
          const ev = (id, start, end, extra = {}) => ({ id, kind: "event", status: "ok", source: "committee", category: "manual",
            title: id, url: "/events/", date: start, lang: "en", i18n: {}, machine: [], extra: { start, end, ...extra } });
          const items = [
            ev("no-end", "2026-10-02T00:00:00Z", null),                          // 7 PM CDT on the 1st, no end
            ev("timed", "2026-10-03T15:00:00Z", "2026-10-03T18:00:00Z"),
            ev("bad-end", "2026-10-04T15:00:00Z", "2026-10-04T14:00:00Z"),       // an end before the start
            ev("junk-end", "2026-10-05T15:00:00Z", "soon"),                       // an end that cannot be read
            ev("date-end", "2026-10-09T23:00:00Z", "2026-10-10"),                 // a date as its end: through it
            ev("assembly", "2026-10-16", "2026-10-18", { all_day: true }),
            ev("one-day", "2026-10-20", null, { all_day: true }),
            ev("exclusive", "2026-10-23", "2026-10-25T05:00:00Z", { all_day: true }),   // 00:00 after the 24th
          ];
          const cm = Object.fromEntries(C.normalizeEvents(items, input.site, "en").filter((e) => !e.committee)
            .map((e) => [e.id, [e.expireIso, e.endIso]]));
          const home = Object.fromEntries(items.map((e) => [e.id, filters.homeEventEnd(e)]));
          const mm = M.monthModel("2026-10", { events: { items } }, { ways: [], tips: {}, wayById: {} }, input.site, "en",
                                  new Date("2026-10-01T15:00:00Z"));
          const tk = Object.fromEntries(mm.dates.filter((d) => items.some((e) => e.id === d.id)).map((d) => [d.id, d.overAt]));
          const rep = {};
          for (const e of items) {
            const at = Date.parse(home[e.id]);
            const listed = (ms) => R.upcomingEvents({ events: { items } }, new Date(ms)).some((x) => x.id === e.id);
            rep[e.id] = [listed(at - 60e3), listed(at + 60e3)];
          }
          const noEnd = C.normalizeEvents([items[0]], input.site, "en").find((e) => e.id === "no-end");
          out({ cm, home, tk, rep, label: noEnd.timeLabel });""", data={"site": self.SITE})
        want = {"no-end": "2026-10-02T01:00:00.000Z", "timed": "2026-10-03T18:00:00.000Z",
                "bad-end": "2026-10-04T16:00:00.000Z", "junk-end": "2026-10-05T16:00:00.000Z",
                "date-end": "2026-10-11T05:00:00.000Z", "assembly": "2026-10-19T05:00:00.000Z",
                "one-day": "2026-10-21T05:00:00.000Z", "exclusive": "2026-10-25T05:00:00.000Z"}
        self.assertEqual({k: v[0] for k, v in r["cm"].items()}, want, "/events/ (data-cm-expire)")
        self.assertEqual(r["home"], want, "the home page (data-gv-expire)")
        self.assertEqual(r["tk"], want, "the monthly toolkit (data-mp-over)")
        self.assertEqual(r["rep"], {k: [True, False] for k in want}, "the district report lists it until then")
        # the calendars get the same hour; the card shows the start alone — never an end the data did not give
        self.assertEqual(r["cm"]["no-end"][1], "2026-10-02T01:00:00.000Z")
        self.assertEqual(r["label"], "7:00 PM CDT")


class Pages(unittest.TestCase):
    def test_their_attributes_are_gv_expires_alone(self):
        # committee.js (loaded on /bulletin/) and read.js hide [data-cm-expire] with their own marker, counts and
        # lists: the home page and /bulletin/ must never carry it, and they must never read GV.expire's attributes
        for page in ("index.njk", "bulletin.njk"):
            self.assertNotIn("data-cm-expire", (ROOT / "src" / "pages" / page).read_text(encoding="utf-8"), page)
        for f in ("committee.js", "read.js"):
            text = (ROOT / "src" / "assets" / "js" / f).read_text(encoding="utf-8")
            self.assertNotIn("data-gv-expire", text, f)
        app = (ROOT / "src" / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('querySelectorAll("[data-cm-expire', app)

    def test_home_and_bulletin_carry_the_attributes(self):
        home = (ROOT / "src" / "pages" / "index.njk").read_text(encoding="utf-8")
        # the bulletin section and the events section are lists; their cards are items with a moment
        self.assertRegex(home, r'<section[^>]*aria-labelledby="ann-title"[^>]*data-gv-expire-list')
        self.assertRegex(home, r'<section[^>]*aria-labelledby="events-title"[^>]*data-gv-expire-list')
        self.assertRegex(home, r'<article class="home-ann[^"]*"[^>]*data-gv-expire-item\{% if annEnd %\} data-gv-expire="\{\{ annEnd \}\}"')
        self.assertIn('(a.extra.expires | fsDayEnd)', home)
        self.assertIn('(th.extra.deadline | fsDayEnd)', home)
        self.assertRegex(home, r'<li class="home-theme[^"]*"[^>]*data-gv-expire-item\{% if thEnd %\} data-gv-expire="\{\{ thEnd \}\}"')
        self.assertIn('{%- set evEndAt = e | homeEventEnd -%}', home)
        self.assertRegex(home, r'data-gv-expire-item\{% if evEndAt %\} data-gv-expire="\{\{ evEndAt \}\}"')
        # the 4th event (hidden on a phone) is a spare that steps in there
        self.assertIn('<li{% if loop.index > 3 %} class="max-sm:hidden" data-gv-expire-spare="max-sm:hidden"{% endif %} '
                      'data-gv-expire-item', home)
        # the calendar card in the events row is not an event: never an item
        cta = home.split('class="home-cal-cta', 1)[1].split("</article>", 1)[0]
        self.assertNotIn("data-gv-expire", cta)
        bulletin = (ROOT / "src" / "pages" / "bulletin.njk").read_text(encoding="utf-8")
        self.assertIn('data-gv-expire-list data-gv-expire-empty="#ann-empty"', bulletin)
        self.assertRegex(bulletin, r'<li class="min-w-0" data-gv-expire-item\{% if annEnd %\} data-gv-expire="\{\{ annEnd \}\}"')
        self.assertRegex(bulletin, r'<div id="ann-empty"[^>]*\{% if anns \| length %\} hidden\{% endif %\}>')
        self.assertIn('{% for k in ["1", "2", "3", "4"] %}', bulletin)


if __name__ == "__main__":
    unittest.main()
