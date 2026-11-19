"""Round 33 · Search and Library (the review's search group), run in Node.js: the browser scripts on a pretend page
(tests/fakedom.py, its clock moved by the test) and the templates / styles as written. The browser side (what the
page draws, the jumps it makes, where a tap lands) is in tests/browser/test_r33_search.py.

  * IndexWait     — (jscode-1) a server that doesn't ANSWER (no response headers) within 20 s counts as failed:
                    Search (search.js kit.fetchJson) shows its error box and Retry, typing or Retry starts a fresh
                    request; the Library (library.js) stops dimming its cards and shows its Retry, which never
                    stacks a second request while one is under way. Only that wait is timed, NEVER the download: a
                    body that takes 40 s after the headers came (a slow phone connection, the index is ~200 KB
                    compressed) still arrives and shows its results.
  * DeckWait      — presentations.js fetchDeck: the same 20 s on a deck's file; the failure clears PENDING[id], so the
                    next click (Retry, or the click after a pointer's prefetch that stalled) starts a fresh request;
                    a slow download is never cut off.
  * OlderIssues   — read.js readPage.loadOlder ("Show older issues" on /read/): the same — "Couldn't load", and the
                    button works again.
  * FirstPaint    — (layout-1) search.njk's small script after #site-search: a visit that arrives with ?q= gets the
                    query state (results layout, type filters, "Loading…") before the first paint, by `hidden`
                    attributes only; no ?q= changes nothing; if search.js never runs the start state comes back on
                    load. library.css keeps the layout a screen tall while it loads (align-content: start).
  * SearchStyles  — layout-3 (the type chips keep the chip utility's 44px on phones / touch: only a mouse on a wider
                    screen gets 40px), layout-5 (.ss-alt above the result's own link), layout-6 (.lib-ref has room for
                    its link's padded hit area on phones), layout-7 (.lib-find-input ends a long placeholder in "…").
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import ROOT, run_js  # noqa: E402

MINISEARCH = "node_modules/minisearch/dist/umd/index.js"


def need_minisearch(case: unittest.TestCase) -> None:
    if not (ROOT / MINISEARCH).is_file():
        case.skipTest("node_modules is not installed (npm ci)")


def read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


# A fetch() that behaves as the browser's does with an AbortSignal: the request rejects with an AbortError when the
# signal aborts — before the headers came (fetch's promise) or while the body still downloads (json()'s promise).
# mode: "stall" (the server never answers), "ok" (answers at once), "slow" (headers at once, the body after
# input.bodyMs on the page's clock).
FAKE_FETCH = r"""
const calls = [];
let mode = "stall", P = null;
const aborted = () => new DOMException("The operation was aborted.", "AbortError");
const onAbort = (o, rej) => { if (o && o.signal) o.signal.addEventListener("abort", () => rej(aborted())); };
const fetch = (url, o) => {
  calls.push({ url: String(url), signal: !!(o && o.signal) });
  if (mode === "stall") return new Promise((res, rej) => onAbort(o, rej));
  const json = () => mode === "slow"
    ? new Promise((res, rej) => { onAbort(o, rej); P.win.setTimeout(() => res(input.body), input.bodyMs); })
    : Promise.resolve(input.body);
  return Promise.resolve({ ok: true, status: 200, json });
};
"""

SS_IDS = ["ss-q", "ss-clear", "ss-status", "ss-results", "ss-more", "ss-jump-wrap", "ss-jump", "ss-kinds-wrap", "ss-start",
          "ss-none", "ss-partial", "ss-error", "ss-loading", "ss-did", "ss-none-kind", "ss-layout", "ss-none-title",
          "ss-none-kind-btn", "ss-retry"]
SS_CFG = {"lang": "en", "locale": "en-US", "index": "/search-index.json", "title": "Search", "kinds": {"article": "Article"},
          "groups": {}, "src": {}, "langTitle": {},
          "s": {"count": "{n} results", "countOne": "1 result", "countIn": "", "noneTitle": "Nothing for {q}", "noneKind": "",
                "isNew": "New", "auto": "", "autoHelp": "", "external": "", "subscriber": "", "subscriberTitle": "", "byline": "",
                "tbc": "", "tbcHelp": "", "episodePage": "Episode page"}}
SS_ITEMS = [{"k": "article", "t": "Sponsorship and service", "u": "/read/a/", "src": "gv"},
            {"k": "article", "t": "My sponsor and me", "u": "/read/b/", "src": "gv"}]


def search_html() -> str:
    hidden = {"ss-clear", "ss-more", "ss-jump-wrap", "ss-kinds-wrap", "ss-none", "ss-partial", "ss-error", "ss-loading", "ss-did",
              "ss-none-kind", "ss-layout"}
    inner = "".join(('<ol id="ss-results"></ol>' if i == "ss-results" else
                     f'<div id="{i}"{" hidden" if i in hidden else ""}></div>') for i in SS_IDS[1:])
    return ('<form id="ss-form"><input id="ss-q"></form><section id="site-search">' + inner + "</section>"
            '<template id="ss-icons"></template><script type="application/json" id="ss-config">' + json.dumps(SS_CFG) + "</script>")


SS_STATE = r"""
const ssState = () => ({ loading: !p.$("#ss-loading").hidden, error: !p.$("#ss-error").hidden, results: p.$$("#ss-results li").length,
                         calls: calls.length, signal: calls.every((c) => c.signal) });
"""

LIB_HTML = r"""
<template id="lib-icons"><svg data-icon="file-text"><path d="M0"/></svg></template>
<script type="application/json" id="lib-config">__CFG__</script>
<h2 id="lib-results-h">Documents</h2>
<form id="lib-form"><input id="lib-q" type="search"><button type="button" id="lib-clear" hidden>x</button></form>
<p id="lib-status"></p><div id="lib-active" hidden></div><p id="lib-partial" hidden></p><p id="lib-error" hidden><button id="lib-retry">Retry</button></p>
<div id="lib-results"><article class="lib-card">server-rendered</article></div>
<div id="lib-empty" hidden><span data-empty-icon></span><p data-empty-title></p><p data-empty-text></p><div class="flex"></div></div>
<div id="lib-more-wrap" hidden><span id="lib-shown"></span><button type="button" id="lib-more">Load more</button></div>
"""
LIB_CFG = {"s": {"countShown": "{shown} of {n}"}, "lang": "en", "locale": "en-US", "index": "/library-index.json", "search": "/search/",
           "pageSize": 12, "cols": [], "src": {}, "srcLong": {}, "langs": {}, "langTitle": {}, "catIcons": {}, "ft": {}}
LIB_DOCS = [{"id": f"d{i}", "t": f"Sponsor document {i}", "s": "gv", "c": "forms", "l": "en", "u": f"https://example.test/{i}.pdf",
             "d": "2026-01-01"} for i in range(3)]


class IndexWait(unittest.TestCase):
    def run_search(self, script: str, start: str = "stall", body_ms: int = 0) -> dict:
        need_minisearch(self)
        return run_js(self, PAGE_JS + FAKE_FETCH + r"""
          mode = input.start;
          P = page({ url: "https://example.test/aagrapevine/search/?q=sponsor", html: input.html,
                     globals: { SITE: { lang: "en", base: "/aagrapevine/" }, fetch },
                     scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js", "src/assets/js/search.js"] });
          const p = P;
          """ + SS_STATE + r"""
          const R = {};
          await p.ready();
          """ + script + r"""
          R.errors = p.errors.map(String);
          out(R);""", data={"html": search_html(), "body": {"items": SS_ITEMS}, "bodyMs": body_ms, "start": start},
                      needs_modules=False)

    def test_search_gives_up_on_a_server_that_never_answers_and_retry_works(self):
        r = self.run_search(r"""
          await p.tick(19000); R.at19 = ssState();
          await p.tick(1500);  R.at20 = ssState();
          mode = "ok";
          p.click(p.$("#ss-retry"));
          R.retrying = ssState();
          await p.tick(500);   R.retried = ssState();""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["at19"], {"loading": True, "error": False, "results": 0, "calls": 1, "signal": True})
        self.assertEqual(r["at20"], {"loading": False, "error": True, "results": 0, "calls": 1, "signal": True},
                         "no answer within 20 s: the error box with its Retry, not 'Loading…' for good")
        self.assertEqual((r["retrying"]["loading"], r["retrying"]["error"], r["retrying"]["calls"]), (True, False, 2),
                         "Retry starts a fresh request ('loading' was freed)")
        self.assertEqual((r["retried"]["error"], r["retried"]["results"]), (False, 2))

    def test_typing_again_after_a_stall_starts_a_fresh_request(self):
        r = self.run_search(r"""
          await p.tick(20500);
          mode = "ok";
          const q = p.$("#ss-q");
          q.value = "sponsorship";
          p.fire(q, "input");
          await p.tick(500); R.typed = ssState();""")
        self.assertEqual((r["typed"]["calls"], r["typed"]["error"], r["typed"]["results"]), (2, False, 1))

    def test_a_slow_download_is_never_cut_off(self):
        # the headers come at once; the body takes 40 s (a slow phone connection) — past the 20 s limit
        r = self.run_search(r"""
          await p.tick(25000); R.at25 = ssState();
          await p.tick(16000); R.at41 = ssState();""", start="slow", body_ms=40000)
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["at25"]["loading"], r["at25"]["error"]), (True, False), "still downloading: no error at 25 s")
        self.assertEqual((r["at41"]["loading"], r["at41"]["error"], r["at41"]["results"], r["at41"]["calls"]), (False, False, 2, 1))

    def run_library(self, script: str, start: str = "stall") -> dict:
        need_minisearch(self)
        html = LIB_HTML.replace("__CFG__", json.dumps(LIB_CFG))
        return run_js(self, PAGE_JS + FAKE_FETCH + r"""
          mode = input.start;
          P = page({ url: "https://example.test/aagrapevine/library/?q=sponsor", html: input.html,
                     globals: { SITE: { lang: "en", base: "/aagrapevine/" }, fetch },
                     scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js", "src/assets/js/search.js", "src/assets/js/library.js"] });
          const p = P;
          const libState = () => ({ busy: p.$("#lib-results").getAttribute("aria-busy"), error: !p.$("#lib-error").hidden,
                                    cards: p.$$("#lib-results .lib-card").length, calls: calls.length, signal: calls.every((c) => c.signal) });
          const R = {};
          await p.ready();
          """ + script + r"""
          R.errors = p.errors.map(String);
          out(R);""", data={"html": html, "body": {"items": LIB_DOCS, "refs": [], "cats": {}}, "bodyMs": 40000,
                                  "start": start}, needs_modules=False)

    def test_library_gives_up_after_20_s_and_retry_never_stacks_requests(self):
        r = self.run_library(r"""
          await p.tick(19000); R.at19 = libState();
          await p.tick(1500);  R.at20 = libState();
          p.click(p.$("#lib-retry"));
          p.click(p.$("#lib-retry"));                  // pressed twice while the request is under way
          R.twice = libState();
          await p.tick(21000); R.again = libState();
          mode = "ok";
          p.click(p.$("#lib-retry"));
          await p.tick(500);   R.ok = libState();""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["at19"], {"busy": "true", "error": False, "cards": 1, "calls": 1, "signal": True})
        self.assertEqual(r["at20"], {"busy": None, "error": True, "cards": 1, "calls": 1, "signal": True},
                         "the cards are no longer dimmed; the error box and its Retry show")
        self.assertEqual((r["twice"]["calls"], r["twice"]["error"]), (2, False), "one request for two presses")
        self.assertEqual((r["again"]["calls"], r["again"]["error"]), (2, True))
        self.assertEqual((r["ok"]["calls"], r["ok"]["error"], r["ok"]["busy"], r["ok"]["cards"]), (3, False, None, 3))

    def test_library_slow_download_is_never_cut_off(self):
        r = self.run_library(r"""
          await p.tick(25000); R.at25 = libState();
          await p.tick(16000); R.at41 = libState();""", start="slow")
        self.assertEqual((r["at25"]["busy"], r["at25"]["error"]), ("true", False))
        self.assertEqual((r["at41"]["busy"], r["at41"]["error"], r["at41"]["cards"], r["at41"]["calls"]), (None, False, 3, 1))

    def test_the_limit_is_on_the_answer_only(self):
        js = read("src", "assets", "js", "search.js")
        fn = re.search(r"function fetchJson\(url, opts\) \{.*?\n  \}\n", js, re.S).group(0)
        self.assertIn('typeof window.AbortController === "function"', fn, "old browsers keep waiting, as before")
        # the timer is cleared as soon as the response (its headers) is there, before the body is read
        self.assertLess(fn.index("clearTimeout(timer)"), fn.index("r.json()"))
        self.assertIn("var HEAD_TIMEOUT = 20000;", js)
        lib = read("src", "assets", "js", "library.js")
        self.assertIn("kit.fetchJson(kit.href(CFG.index)", lib)
        self.assertIn("kit.fetchJson(kit.href(CFG.index)", js)


class DeckWait(unittest.TestCase):
    """presentations.js fetchDeck, taken out of the player as written and run with a short DECK_WAIT."""

    def test_a_stalled_deck_fails_clears_pending_and_the_next_click_starts_afresh(self):
        js = read("src", "assets", "js", "presentations.js")
        self.assertIn("var DECK_WAIT = 20000;", js)
        fn = re.search(r"  function fetchDeck\(id\) \{.*?\n  \}\n", js, re.S).group(0)
        r = run_js(self, r"""
          import vm from "node:vm";
          const deck = { app: "gv-presentation", id: "d", slides: [] };
          let mode = "stall"; const calls = [];
          const aborted = () => new DOMException("The operation was aborted.", "AbortError");
          const fetch = (url, o) => {
            calls.push(url);
            const onAbort = (rej) => o && o.signal && o.signal.addEventListener("abort", () => rej(aborted()));
            if (mode === "stall") return new Promise((res, rej) => onAbort(rej));
            const json = () => mode === "slow" ? new Promise((res, rej) => { onAbort(rej); setTimeout(() => res(deck), 150); }) : Promise.resolve(deck);
            return Promise.resolve({ ok: true, json });
          };
          const ctx = vm.createContext({ window: { AbortController }, fetch, setTimeout, clearTimeout, Promise, Error, Array,
                                         encodeURIComponent, DECKS: {}, PENDING: {}, META: {}, JSON_BASE: "/o/", DECK_WAIT: 50 });
          vm.runInContext(input.fn + "\nthis.fetchDeck = fetchDeck;", ctx);
          const R = {};
          const first = ctx.fetchDeck("d");                    // the pointer's prefetch …
          R.shared = ctx.fetchDeck("d") === first;            // … and the click share one request
          R.failed = await first.then(() => "resolved", (e) => e.name);
          R.pendingCleared = !("d" in ctx.PENDING);
          mode = "slow";
          R.slow = await ctx.fetchDeck("d").then((d) => d.id, (e) => "rejected: " + e.name);   // 150 ms body > 50 ms limit
          R.calls = calls.length;
          R.cached = ctx.fetchDeck("d") instanceof Promise && calls.length === 2;
          out(R);""", data={"fn": fn}, needs_modules=False)
        self.assertEqual(r, {"shared": True, "failed": "AbortError", "pendingCleared": True, "slow": "d", "calls": 2, "cached": True})


class OlderIssues(unittest.TestCase):
    def test_older_issues_give_up_after_20_s_and_the_button_works_again(self):
        r = run_js(self, PAGE_JS + FAKE_FETCH + r"""
          const reg = {};
          P = page({ html: "", globals: { Alpine: { data: (n, f) => { reg[n] = f; } }, fetch },
                     scripts: ["src/assets/js/read.js"] });
          const p = P;
          await p.ready();
          p.fire(p.doc, "alpine:init");
          const c = reg.readPage({ json: "/read-archive.json", remaining: 3 });
          const st = () => ({ loading: c.loading, failed: c.failed, older: c.older.length, calls: calls.length, signal: calls.every((x) => x.signal) });
          const R = {};
          c.loadOlder();
          c.loadOlder();                                   // a second tap waits for the same request
          await p.tick(19000); R.at19 = st();
          await p.tick(1500);  R.at20 = st();
          mode = "slow";
          c.loadOlder();
          await p.tick(30000); R.slow = st();
          out(R);""", data={"body": {"issues": [{"pub": "gv"}, {"pub": "lv"}]}, "bodyMs": 25000}, needs_modules=False)
        self.assertEqual(r["at19"], {"loading": True, "failed": False, "older": 0, "calls": 1, "signal": True})
        self.assertEqual(r["at20"], {"loading": False, "failed": True, "older": 0, "calls": 1, "signal": True})
        self.assertEqual(r["slow"], {"loading": False, "failed": False, "older": 2, "calls": 2, "signal": True},
                         "a 25 s download after the answer still arrives")


def prepaint_script() -> str:
    njk = read("src", "pages", "search.njk")
    m = re.search(r"</section>\s*\{#-.*?-#\}\s*<script>(.*?)</script>", njk, re.S)
    assert m, "search.njk: the script right after #site-search"
    return m.group(1)


class FirstPaint(unittest.TestCase):
    def run_prepaint(self, url: str, with_search_js: bool) -> dict:
        if with_search_js:
            need_minisearch(self)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "prepaint.js"
            f.write_text(prepaint_script(), encoding="utf-8")
            scripts = [str(f)] + (([MINISEARCH, "src/assets/js/app.js", "src/assets/js/search.js"]) if with_search_js else [])
            return run_js(self, PAGE_JS + FAKE_FETCH + r"""
              mode = "stall";
              P = page({ url: input.url, html: input.html, globals: { SITE: { lang: "en", base: "/aagrapevine/" }, fetch }, scripts: input.scripts });
              const p = P;
              const st = () => Object.fromEntries(["ss-start", "ss-layout", "ss-kinds-wrap", "ss-loading", "ss-error"].map((i) => [i, !p.$("#" + i).hidden]));
              const R = { first: st() };                      // before DOMContentLoaded: what the first paint draws
              await p.ready();
              await p.tick(100);
              R.loaded = st();
              R.errors = p.errors.map(String);
              out(R);""", data={"url": url, "html": search_html(), "scripts": scripts}, needs_modules=False)

    def test_a_visit_with_a_query_starts_in_its_query_state(self):
        r = self.run_prepaint("https://example.test/aagrapevine/search/?q=grapevine", True)
        want = {"ss-start": False, "ss-layout": True, "ss-kinds-wrap": True, "ss-loading": True, "ss-error": False}
        self.assertEqual(r["first"], want, "the query state from the first paint")
        self.assertEqual(r["loaded"], want, "search.js keeps it (the index still loading)")
        self.assertEqual(r["errors"], [])

    def test_no_query_changes_nothing(self):
        for url in ("https://example.test/aagrapevine/search/", "https://example.test/aagrapevine/search/?q=%20"):
            with self.subTest(url=url):
                r = self.run_prepaint(url, False)
                self.assertEqual(r["first"], {"ss-start": True, "ss-layout": False, "ss-kinds-wrap": False, "ss-loading": False, "ss-error": False})

    def test_without_search_js_the_start_state_comes_back_on_load(self):
        r = self.run_prepaint("https://example.test/aagrapevine/search/?q=grapevine", False)
        self.assertEqual((r["first"]["ss-start"], r["first"]["ss-layout"]), (False, True))
        self.assertEqual((r["loaded"]["ss-start"], r["loaded"]["ss-layout"]), (True, False),
                         "its tips and browse links (they work without JavaScript) instead of 'Loading…' for good")

    def test_it_only_sets_hidden_and_sits_right_after_the_section(self):
        code = prepaint_script()
        self.assertNotIn("classList", code)
        self.assertNotIn("className", code)
        self.assertNotIn("documentElement", code, "never a class on <html>: search.js keeps full control")
        njk = read("src", "pages", "search.njk")
        self.assertLess(njk.index('<div id="ss-start">'), njk.index(code), "after the elements it sets")
        self.assertLess(njk.index(code), njk.index('<template id="ss-icons">'))

    def test_the_layout_is_a_screen_tall_while_loading(self):
        css = read("src", "assets", "css", "areas", "library.css")
        self.assertRegex(css, r"\.ss-layout \{[^}]*align-content: start;")
        self.assertIn(".ss-layout:has(#ss-loading:not([hidden])) { min-height: 100svh; }", css)


class SearchStyles(unittest.TestCase):
    CSS = None

    @classmethod
    def setUpClass(cls):
        cls.CSS = read("src", "assets", "css", "areas", "library.css")

    def test_type_chips_keep_44px_on_phones_and_touch(self):
        self.assertIn(".ss-kinds .chip { flex-shrink: 0; }", self.CSS)
        self.assertNotRegex(self.CSS, r"\n\.ss-kinds \.chip \{[^}]*min-height", "no 40px for phones and touch screens")
        self.assertIn("@media (width >= 40rem) and (pointer: fine) { .ss-kinds .chip { min-height: 2.5rem; } }", self.CSS)

    def test_episode_page_link_sits_above_the_result_link(self):
        rule = re.search(r"\n\.ss-alt \{([^}]*)\}", self.CSS).group(1)
        self.assertIn("position: relative;", rule)
        self.assertIn("margin: -0.6rem 0 0", rule, "still pulled up into the card's padding")

    def test_found_on_line_has_room_for_its_hit_area(self):
        self.assertIn("@media (width < 40rem), (pointer: coarse) { .lib-ref { padding-block: 0.625rem; } "
                      ".lib-ref a { padding-block: 0.9375rem; } }", self.CSS)

    def test_a_long_placeholder_ends_in_an_ellipsis(self):
        rule = re.search(r"\n\.lib-find-input \{([^}]*)\}", self.CSS).group(1)
        self.assertIn("text-overflow: ellipsis;", rule)


if __name__ == "__main__":
    unittest.main()
