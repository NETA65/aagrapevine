"""Round 12, Listen & Watch (unit u1): La Viña's spoken stories on Listen, Watch filters in the address, one episode /
video / story to share, and Home's player keeping Listen's saved places. Run in Node.js: the filters as the pages run
them (tests/nodejs.py) and the browser scripts on a pretend page (tests/fakedom.py), its clock stopped at
2026-10-06 15:00 UTC — nothing here depends on the day the tests run.

  * SpanishStories   — eleventy/filters/media.js mediaSpanishStories: La Viña's Spanish playlists for Listen's card,
                       titles as La Viña writes them (capitals softened), each counted as Watch counts it (Shorts
                       too: review u1-7), a story in two playlists counted once in the total; type playlists, English
                       ones, playlists with fewer than 3 videos that are not Shorts and playlists without a usable
                       YouTube id are left out. Every playlist carries its YouTube id, and Watch's page JSON lists
                       them (plIds) in the menu's order.
  * WatchAddress     — media.js videoPage: ?pl=<playlist id>, ?lang=es|en (gv|lv) and ?type= open the list filtered;
                       a playlist wins over a type; unknown values leave the address; the chips and the playlist menu
                       keep it up to date (replaceState).
  * ListenLink       — media.js podcastPage: /listen/?ep=<id> loads that episode without playing it (nothing saved
                       until it is played, skipped or seeked: the visitor's own "Continue listening" stays), marks and
                       scrolls to its row (the full list first when it is not among the newest 24, shown as far as
                       the row); an episode the list no longer has, or a malformed id, leaves the address; another
                       episode in the player unmarks it. Each episode's share link is the page's address + ?ep=.
                       The speed button has 0.75×.
  * ListenLinkWaits  — (review u1-1, pwa-2) one not among the newest 24 waits for the full list and the page says so;
                       if the visitor plays something or searches meanwhile it is offered ("Go to episode": then the
                       keyboard goes to its row), not forced on them; no list (offline): the link waits, ?ep= kept,
                       the visitor told, and "Try again" (the list's or the note's, the focus kept) opens it.
  * HomePlayer       — home.js homePlayer: the same saved places as Listen (gv:audio:pos / gv:audio:last, same
                       format): it resumes, marks a finished episode, offers "Continue listening: … — 20 min left",
                       and what it saves is what Listen reads back. Nothing else is stored. HomeResumeFocus (review
                       u1-3): keyboard focus in that box, which goes away once something plays, goes to the player.
                       HomeResumeWords (release check R12-HOME-ES-QUEDAN): on /es/ "— quedan 20 min", in lower case.
  * SearchResults    — the search index sends an episode to /listen/?ep=<id> (the language's own page) and keeps the
                       podcast host's page as `u2`; search.js shows that second link beside the result, never inside it.
  * ShareWords, SharePages — (review u1-4 / XC-2, u1-5 / XC-4) a story's or a video's Share sends the title its
                       magazine (or YouTube) published, never our translation — but a Weekly Open meeting's "Meeting of
                       …", the site's own words, in the page's language; on /es/ the issue as Spanish writes it in
                       a sentence ("— La Viña, septiembre–octubre de 2026"). SharePages builds Read, its archive file,
                       Published and Watch in memory and checks every Share button on them (its Spanish credit lines
                       judge the day's issue names too: scripts/ops/gate_tests.py DATA_TESTS); SpanishCredits builds
                       them from data of its own and checks every credit line, word for word.
  * ShareSheet       — (release check R12-SHARE-TITLE-DROPPED) app.js GV.share: the share sheet gets the title at the
                       start of its text too (Messages and WhatsApp drop `title`), never twice; the copy as before.
  * Pages           — the templates: La Viña's card names "videos" / "historias habladas", never "podcast"; the share
                       buttons sit beside a link, never inside it; What's New sends episodes to the site's player.

    python -m unittest tests.test_r12_u1_listen -v
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import ROOT, run_js  # noqa: E402


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def vid(i, playlists, secs=300, short=False, lang="es"):
    return {"id": f"yt:v{i:02d}xxxxxxx", "kind": "video", "title": f"Historia {i}", "lang": lang, "category": "lv" if lang == "es" else "gv",
            "date": f"2026-09-{i:02d}T12:00:00Z", "status": "ok",
            "extra": {"video_id": f"v{i:02d}xxxxxxx", "playlists": playlists, "duration_sec": secs, "is_short": short}}


VIDEOS = {
    "playlists": [
        {"id": "PLaaaaaaaaaaaaaa", "title": "AMOR Y SERVICIO", "lang": "es", "i18n": {"title": {"en": "LOVE AND SERVICE", "es": "AMOR Y SERVICIO"}}},
        {"id": "PLbbbbbbbbbbbbbb", "title": "Tocaron Fondo", "lang": "es"},
        {"id": "PLcccccccccccccc", "title": "Sober Women", "lang": "en"},
        {"id": "PLdddddddddddddd", "title": "La Viña", "lang": "es"},
        {"id": "PLeeeeeeeeeeeeee", "title": "Reunión Abierta Semanal de La Viña", "lang": "es"},
        {"id": "bad id!", "title": "Raros", "lang": "es"},
    ],
    "items": [
        vid(1, ["AMOR Y SERVICIO"]), vid(2, ["AMOR Y SERVICIO"]), vid(3, ["AMOR Y SERVICIO", "Tocaron Fondo"]),
        vid(4, ["AMOR Y SERVICIO"], secs=60, short=True),
        vid(5, ["Tocaron Fondo"], secs=400), vid(6, ["Tocaron Fondo"], secs=None),
        vid(7, ["La Viña"]), vid(8, ["La Viña"]), vid(9, ["La Viña"], short=True), vid(10, ["La Viña"], short=True),
        vid(11, ["Sober Women"], lang="en"), vid(12, ["Sober Women"], lang="en"), vid(13, ["Sober Women"], lang="en"),
        vid(14, ["Reunión Abierta Semanal de La Viña"]), vid(15, ["Reunión Abierta Semanal de La Viña"]),
        vid(16, ["Reunión Abierta Semanal de La Viña"]),
        vid(17, ["Raros"]), vid(18, ["Raros"]), vid(19, ["Raros"]),
    ],
}


class SpanishStories(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if SpanishStories.r is None:
            SpanishStories.r = run_js(self, r"""
              const items = filters.mediaItems(input, "videos");
              const st = filters.mediaSpanishStories(input, items);
              const pls = filters.mediaPlaylists(input, items, "en");
              const init = JSON.parse(filters.mediaInitialJson(items, "videos", "en", pls));
              out({ st, pls: pls.map((p) => [p.id, p.title, p.count]), plIds: init.plIds, titles: init.playlists });""",
                                       data=VIDEOS)

    def test_the_spoken_story_playlists(self):
        st = self.r["st"]
        self.assertEqual([(p["id"], p["title"], p["count"], p["secs"]) for p in st["lists"]],
                         [("PLaaaaaaaaaaaaaa", "Amor y servicio", 4, 960), ("PLbbbbbbbbbbbbbb", "Tocaron Fondo", 3, 700)],
                         "every video counted, its Short too; English, type, too-small and id-less playlists left out")
        self.assertEqual((st["count"], st["secs"]), (6, 1360), "a story in two playlists counts once; no length counts 0")

    def test_each_count_is_what_watch_then_shows(self):
        watch = {p[0]: p[2] for p in self.r["pls"]}
        for p in self.r["st"]["lists"]:
            self.assertEqual(p["count"], watch[p["id"]], f"{p['title']}: the card's count, Watch's ({p['id']})")

    def test_every_playlist_has_its_youtube_id_and_watch_lists_them_in_order(self):
        ids = [p[0] for p in self.r["pls"]]
        self.assertIn("PLaaaaaaaaaaaaaa", ids)
        self.assertIn("", ids, "an id that could not be an address part is left empty")
        self.assertEqual(self.r["plIds"], ids)
        self.assertEqual(len(self.r["titles"]), len(ids))
        self.assertEqual(self.r["titles"][ids.index("PLaaaaaaaaaaaaaa")], "Love and Service")


# ------------------------------------------------------------------------------------------- media.js on a page
MEDIA_JS = PAGE_JS + r"""
function mediaPage(url, initial, rootAttrs, more, globals) {
  const json = (id, o) => '<script type="application/json" id="' + id + '">' + JSON.stringify(o) + '</script>';
  const attrs = Object.entries(rootAttrs || {}).map(([k, v]) => " " + k + '="' + v + '"').join("");
  const p = page({ url, globals: globals || {},
                   html: json("media-initial", initial) + json("media-i18n", { share: "Share", showing: "Showing {n} of {total}",
                                                                              from_link: "From your link", link_fail: "The episode from your link didn't open" }) +
                         '<div id="root"' + attrs + '>' + (more || "") + '</div>',
                   scripts: ["src/assets/js/media.js"] });
  const made = {}, stores = {}, watchers = {}, scrolled = [];
  p.win.Element.prototype.scrollIntoView = function (o) { scrolled.push([this.getAttribute("data-ep"), o && o.block]); };
  p.win.Alpine = { data: (n, f) => { made[n] = f; }, store: (n, v) => (v ? (stores[n] = v) : stores[n]) };
  p.doc.dispatchEvent(new p.win.Event("alpine:init"));
  if (stores.audio) stores.audio.init();
  const make = (name) => {
    const c = made[name]();
    Object.assign(c, { $el: p.$("#root"), $refs: {}, $store: { audio: stores.audio },
                       $watch: (k, fn) => { watchers[k] = fn; }, $nextTick: (fn) => fn() });
    c.init();
    return c;
  };
  const where = () => p.win.location.search + p.win.location.hash;
  return { p, make, stores, watchers, scrolled, where };
}
"""

WATCH_INITIAL = {"playlists": ["Amor y servicio", "Tocaron Fondo", "Sober Women"],
                 "plIds": ["PLaaaaaaaaaaaaaa", "PLbbbbbbbbbbbbbb", "PLcccccccccccccc"], "items": []}


class WatchAddress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if WatchAddress.r is not None:
            return
        WatchAddress.r = run_js(self, MEDIA_JS + r"""
          const W = "https://example.test/aagrapevine/es/watch/";
          const open = (q) => { const m = mediaPage(W + q, input, { "data-index": "", "data-total": "0" }); const c = m.make("videoPage");
                                return { m, c, got: { coll: c.coll, vlang: c.vlang, at: m.where() } }; };
          const res = {};
          res.playlist = open("?pl=PLbbbbbbbbbbbbbb&lang=es#videos").got;
          res.unknown = open("?type=short&pl=PLzzzzzzzzzzzzzz&lang=fr&x=1#videos").got;
          res.both = open("?type=podcast&pl=PLaaaaaaaaaaaaaa").got;
          res.aliases = open("?lang=gv").got;
          const { m, c } = open("");
          const steps = [m.where()];
          c.coll = "pl:2"; m.watchers.coll(); steps.push(m.where());
          c.vlang = "lv"; m.watchers.vlang(); steps.push(m.where());
          c.coll = "weekly"; m.watchers.coll(); steps.push(m.where());
          c.coll = ""; c.vlang = ""; m.watchers.coll(); steps.push(m.where());
          res.steps = steps;
          res.label = c.shareLabel({ t: "Gladys - El milagro" });
          res.yt = c.ytUrl({ id: "abc123def45", k: "video" });
          out(res);""", data=WATCH_INITIAL, needs_modules=False)

    def test_a_link_opens_one_playlist_in_spanish(self):
        self.assertEqual(self.r["playlist"], {"coll": "pl:1", "vlang": "lv", "at": "?pl=PLbbbbbbbbbbbbbb&lang=es#videos"})

    def test_unknown_values_leave_the_address(self):
        self.assertEqual(self.r["unknown"], {"coll": "short", "vlang": "", "at": "?type=short&x=1#videos"})

    def test_a_playlist_wins_over_a_type_and_the_aliases_work(self):
        self.assertEqual(self.r["both"], {"coll": "pl:0", "vlang": "", "at": "?pl=PLaaaaaaaaaaaaaa"})
        self.assertEqual(self.r["aliases"], {"coll": "", "vlang": "gv", "at": "?lang=en"})

    def test_the_filters_keep_the_address_up_to_date(self):
        self.assertEqual(self.r["steps"], ["", "?pl=PLcccccccccccccc", "?pl=PLcccccccccccccc&lang=es", "?lang=es&type=weekly", ""])

    def test_a_card_shares_the_official_youtube_link(self):
        self.assertEqual(self.r["label"], "Share: Gladys - El milagro")
        self.assertEqual(self.r["yt"], "https://www.youtube.com/watch?v=abc123def45")
        card = read("src", "pages", "watch.njk")
        self.assertIn(':data-share="ytUrl(v)"', card)
        self.assertIn('data-share="{{ href }}"', card)


def ep(i, show="gv"):
    return {"id": f"pod:{show}:e{i:02d}", "t": f"Episode {i}", "s": "", "d": f"2026-09-{(i % 28) + 1:02d}", "du": 1800, "se": 11, "ep": i,
            "a": f"https://episodes.example.test/e{i:02d}.mp3", "sh": show, "l": "en", "u": f"https://player.example.test/e{i:02d}"}


EPISODES = [ep(i) for i in range(40)]


class ListenLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if ListenLink.r is not None:
            return
        ListenLink.r = run_js(self, MEDIA_JS + r"""
          const L = "https://example.test/aagrapevine/listen/";
          const eps = input.eps, first = eps.slice(0, 24);
          const initial = { shows: { gv: { name: "AA Grapevine's Podcast", short: "AA Grapevine's Podcast", i: null } }, latest: {}, items: first };
          const rows = first.map((e) => '<li data-ep="' + e.id + '"></li>').join("");
          const attrs = { "data-index": "/episodes-index.json", "data-total": String(eps.length), "data-mixed": "false", "data-share-base": L };
          const fetches = [];
          const fetch = async (u) => { fetches.push(String(u)); return { ok: true, json: async () => ({ items: JSON.parse(JSON.stringify(eps)) }) }; };
          const open = (q) => { const m = mediaPage(L + q, initial, attrs, "<ol>" + rows + "</ol>", { fetch }); return { m, c: m.make("podcastPage") }; };
          const ls = (m) => ({ last: m.p.win.localStorage.getItem("gv:audio:last"), pos: m.p.win.localStorage.getItem("gv:audio:pos") });
          const res = {};

          // one of the newest 24
          let { m, c } = open("?ep=pod:gv:e03");
          const S = m.stores.audio;
          res.near = { cur: S.cur && S.cur.id, held: S.held, playing: S.playing, linked: c.linked, at: m.where(), scrolled: m.scrolled.slice(),
                       marked: c.rowCls(first[3]), other: c.rowCls(first[4]), saved: ls(m), fetches: fetches.length,
                       share: c.shareUrl(first[3]), label: c.shareLabel(first[3]) };
          S.skip(30);
          res.touched = { held: S.held, saved: ls(m) };
          S.load(first[5], false);
          m.watchers["$store.audio.cur"](S.cur);
          res.moved = { linked: c.linked, at: m.where(), marked: c.rowCls(first[3]) };

          // further down the list: the full list first, shown as far as the row
          ({ m, c } = open("?ep=pod:gv:e30"));
          await m.p.tick(0);
          const ready = { shown: c.shown, linked: c.linked, cur: m.stores.audio.cur && m.stores.audio.cur.id, at: m.where(), fetched: fetches.length };
          m.p.$("ol").insertAdjacentHTML("beforeend", '<li data-ep="pod:gv:e30"></li>');   // (Alpine renders the row)
          await m.p.tick(200);
          res.far = Object.assign(ready, { scrolled: m.scrolled.slice() });

          // gone from the list, or not an episode id
          ({ m, c } = open("?ep=pod:gv:gone&show=gv"));
          await m.p.tick(0);
          res.gone = { linked: c.linked, at: m.where(), cur: m.stores.audio.cur };
          ({ m, c } = open("?ep=%3Cscript%3E"));
          res.bad = { at: m.where(), linkEp: c.linkEp };

          // the speed button
          const s = m.stores.audio, seen = [];
          for (let i = 0; i < 5; i++) { s.cycleRate(); seen.push(s.rate); }
          res.rates = seen;
          out(res);""", data={"eps": EPISODES}, needs_modules=False)

    def test_a_shared_episode_is_ready_and_marked(self):
        n = self.r["near"]
        self.assertEqual((n["cur"], n["held"], n["playing"], n["linked"]), ("pod:gv:e03", True, False, "pod:gv:e03"))
        self.assertEqual(n["at"], "?ep=pod:gv:e03", "the address keeps it, readable")
        self.assertEqual(n["scrolled"], [["pod:gv:e03", "center"]])
        self.assertIn("is-linked", n["marked"])
        self.assertNotIn("is-linked", n["other"])
        self.assertEqual(n["fetches"], 0, "one of the newest 24: no download")

    def test_nothing_is_saved_until_the_visitor_touches_it(self):
        self.assertEqual(self.r["near"]["saved"], {"last": None, "pos": None}, "the visitor's own Continue listening stays")
        t = self.r["touched"]
        self.assertFalse(t["held"])
        self.assertEqual(json.loads(t["saved"]["pos"])["pod:gv:e03"][0], 30)
        self.assertEqual(json.loads(t["saved"]["last"])["id"], "pod:gv:e03")

    def test_another_episode_unmarks_it(self):
        self.assertEqual(self.r["moved"], {"linked": "", "at": "", "marked": ""})

    def test_an_older_episode_loads_the_list_first(self):
        f = self.r["far"]
        self.assertEqual((f["linked"], f["cur"], f["shown"]), ("pod:gv:e30", "pod:gv:e30", 48))
        self.assertEqual(f["at"], "?ep=pod:gv:e30")
        self.assertEqual(f["scrolled"], [["pod:gv:e30", "center"]], "found once the list shows it")

    def test_a_gone_or_malformed_episode_leaves_the_address(self):
        self.assertEqual(self.r["gone"], {"linked": "", "at": "", "cur": None})
        self.assertEqual(self.r["bad"], {"at": "", "linkEp": ""})

    def test_each_episode_shares_its_own_link(self):
        n = self.r["near"]
        self.assertEqual(n["share"], "https://example.test/aagrapevine/listen/?ep=pod:gv:e03")
        self.assertEqual(n["label"], "Share: Episode 3")

    def test_a_slower_speed(self):
        self.assertEqual(self.r["rates"], [1.25, 1.5, 2, 0.75, 1])


class ListenLinkWaits(unittest.TestCase):
    """Round-12 review (u1-1, pwa-2): a shared episode that is not among the newest 24 waits for the full list. The page
    says so; if the visitor plays something or searches meanwhile, the episode is offered once found, not forced on
    them (it stopped what played, emptied the search and jumped the page); if the list does not load, the link waits —
    ?ep= kept, the visitor told — and "Try again" (the list's or the note's) opens it."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if ListenLinkWaits.r is not None:
            return
        ListenLinkWaits.r = run_js(self, MEDIA_JS + r"""
          const L = "https://example.test/aagrapevine/listen/";
          const eps = input.eps, first = eps.slice(0, 24);
          const initial = { shows: { gv: { name: "AA Grapevine's Podcast", short: "AA Grapevine's Podcast", i: null } }, latest: {}, items: first };
          const row = (id) => '<li data-ep="' + id + '"><button type="button" class="ep-art"></button></li>';
          const attrs = { "data-index": "/episodes-index.json", "data-total": String(eps.length), "data-mixed": "false", "data-share-base": L };
          // the full list: held back (a slow phone) until the test lets it through, or failing (offline)
          let mode = "hold", held = [];
          const fetch = () => (mode === "fail" ? Promise.reject(new TypeError("Failed to fetch"))
            : new Promise((res) => { const go = () => res({ ok: true, json: async () => ({ items: JSON.parse(JSON.stringify(eps)) }) });
                                     if (mode === "hold") held.push(go); else go(); }));
          const letThrough = () => { mode = "ok"; held.splice(0).forEach((go) => go()); };
          const said = [];
          const GV = { announce: (msg) => said.push(msg) };
          const open = (q) => {
            const m = mediaPage(L + q, initial, attrs, '<div id="note" tabindex="-1"><button id="again">Try again</button></div><ol>' +
                                first.map((e) => row(e.id)).join("") + "</ol>", { fetch, GV });
            const c = m.make("podcastPage");
            c.$refs.linkNote = m.p.$("#note");
            return { m, c, S: m.stores.audio };
          };
          const audioSrc = (m) => { const a = m.p.$("#gv-audio"); return a ? a.src : null; };
          const focused = (m) => { const a = m.p.doc.activeElement; return a.id || (a.closest("[data-ep]") || { getAttribute: () => a.tagName })
                                                                              .getAttribute("data-ep"); };
          const res = {};

          // the visitor plays the latest episode while the list is on its way
          let { m, c, S } = open("?ep=pod:gv:e30");
          res.waiting = { wait: c.linkWait, cur: S.cur, at: m.where() };
          S.toggleEp(first[0]);
          const playing = audioSrc(m);
          letThrough();
          await m.p.tick(200);
          res.played = { cur: S.cur && S.cur.id, src: audioSrc(m) === playing, wait: c.linkWait, offer: c.linkOffer && c.linkOffer.id,
                         linked: c.linked, at: m.where(), scrolled: m.scrolled.slice(), said: said.splice(0) };
          m.p.$("ol").insertAdjacentHTML("beforeend", row("pod:gv:e30"));       // (Alpine renders the row)
          c.$el = m.p.$("#again");     // (Alpine: a method run from a button in the note sees that button as $el)
          c.openOffer();                                                         // "Go to episode"
          await m.p.tick(200);
          res.opened = { cur: S.cur.id, held: S.held, linked: c.linked, offer: c.linkOffer, at: m.where(), scrolled: m.scrolled.slice(),
                         focus: focused(m) };

          // the visitor searches while the list is on its way
          mode = "hold";
          ({ m, c, S } = open("?ep=pod:gv:e31"));
          c.q = "episode 3"; m.watchers.q();
          letThrough();
          await m.p.tick(200);
          res.searched = { q: c.q, cur: S.cur, offer: c.linkOffer && c.linkOffer.id, at: m.where(), scrolled: m.scrolled.slice(), said: said.splice(0) };

          // the visitor does nothing: as before, it opens
          mode = "hold";
          ({ m, c, S } = open("?ep=pod:gv:e32"));
          letThrough();
          m.p.$("ol").insertAdjacentHTML("beforeend", row("pod:gv:e32"));
          await m.p.tick(200);
          res.quiet = { cur: S.cur && S.cur.id, held: S.held, linked: c.linked, offer: c.linkOffer, wait: c.linkWait, at: m.where(),
                        scrolled: m.scrolled.slice(), focus: focused(m) };

          // no list (offline): the link waits; the list's "Try again" opens it
          mode = "fail";
          ({ m, c, S } = open("?ep=pod:gv:e33"));
          await m.p.tick(0);
          res.failed = { fail: c.linkFail, wait: c.linkWait, failed: c.failed, linkEp: c.linkEp, at: m.where(), cur: S.cur, said: said.splice(0) };
          mode = "ok";
          m.p.$("ol").insertAdjacentHTML("beforeend", row("pod:gv:e33"));
          c.retryIndex();
          await m.p.tick(200);
          res.retried = { cur: S.cur && S.cur.id, held: S.held, linked: c.linked, fail: c.linkFail, at: m.where(), scrolled: m.scrolled.slice() };

          // the note's own "Try again", from the keyboard: the focus stays in the note, then goes to the episode's row
          mode = "fail";
          ({ m, c, S } = open("?ep=pod:gv:e34"));
          await m.p.tick(0);
          m.p.$("#again").focus();
          mode = "hold";
          c.$el = m.p.$("#again");
          c.retryLink();
          res.again = { wait: c.linkWait, fail: c.linkFail, focus: focused(m) };
          m.p.$("ol").insertAdjacentHTML("beforeend", row("pod:gv:e34"));
          letThrough();
          await m.p.tick(200);
          res.again.after = { cur: S.cur && S.cur.id, linked: c.linked, at: m.where(), focus: focused(m) };
          out(res);""", data={"eps": EPISODES}, needs_modules=False)

    def test_the_page_says_it_is_opening_the_link(self):
        self.assertEqual(self.r["waiting"], {"wait": True, "cur": None, "at": "?ep=pod:gv:e30"})

    def test_what_the_visitor_plays_meanwhile_keeps_playing(self):
        p = self.r["played"]
        self.assertEqual((p["cur"], p["src"]), ("pod:gv:e00", True), "the latest episode stays in the player")
        self.assertEqual((p["wait"], p["offer"], p["linked"]), (False, "pod:gv:e30", ""), "offered, not loaded")
        self.assertEqual(p["at"], "?ep=pod:gv:e30", "the address still names it")
        self.assertEqual(p["scrolled"], [], "the page does not jump")
        self.assertEqual(p["said"], ["From your link: Episode 30"])

    def test_go_to_episode_opens_it_and_the_keyboard_follows(self):
        o = self.r["opened"]
        self.assertEqual((o["cur"], o["held"], o["linked"], o["offer"]), ("pod:gv:e30", True, "pod:gv:e30", None))
        self.assertEqual((o["at"], o["scrolled"]), ("?ep=pod:gv:e30", [["pod:gv:e30", "center"]]))
        self.assertEqual(o["focus"], "pod:gv:e30", "its row's play button")

    def test_a_search_typed_meanwhile_stays(self):
        self.assertEqual(self.r["searched"], {"q": "episode 3", "cur": None, "offer": "pod:gv:e31", "at": "?ep=pod:gv:e31", "scrolled": [],
                                              "said": ["From your link: Episode 31"]})

    def test_left_alone_it_opens_as_before(self):
        q = self.r["quiet"]
        self.assertEqual((q["cur"], q["held"], q["linked"], q["offer"], q["wait"]), ("pod:gv:e32", True, "pod:gv:e32", None, False))
        self.assertEqual((q["at"], q["scrolled"]), ("?ep=pod:gv:e32", [["pod:gv:e32", "center"]]))
        self.assertNotEqual(q["focus"], "pod:gv:e32", "the keyboard is not moved at page load")

    def test_no_list_the_link_waits_and_says_so(self):
        f = self.r["failed"]
        self.assertEqual((f["fail"], f["wait"], f["failed"], f["linkEp"], f["cur"]), (True, False, True, "pod:gv:e33", None))
        self.assertEqual(f["at"], "?ep=pod:gv:e33", "the address keeps it: a reload tries again")
        self.assertEqual(f["said"], ["The episode from your link didn't open"])

    def test_the_lists_try_again_opens_it(self):
        self.assertEqual(self.r["retried"], {"cur": "pod:gv:e33", "held": True, "linked": "pod:gv:e33", "fail": False,
                                             "at": "?ep=pod:gv:e33", "scrolled": [["pod:gv:e33", "center"]]})

    def test_the_notes_try_again_keeps_the_keyboard(self):
        a = self.r["again"]
        self.assertEqual((a["wait"], a["fail"], a["focus"]), (True, False, "note"), "the button hides: the note takes the focus")
        self.assertEqual(a["after"], {"cur": "pod:gv:e34", "linked": "pod:gv:e34", "at": "?ep=pod:gv:e34", "focus": "pod:gv:e34"})


# ------------------------------------------------------------------------------------------- home.js
HOME_JS = PAGE_JS + r"""
const NOW = Date.parse("2026-10-06T15:00:00Z");
function home(store, left) {
  const p = page({ url: "https://example.test/aagrapevine/",
                   html: '<div id="hp" data-left="' + (left || "{t} left") + '" data-resume="Resume"><h3 id="t">Latest</h3><p id="m">Oct 1 · 30:00</p><img id="art">' +
                         '<div id="box"><button id="resume">Resume</button></div><button id="elsewhere">Share</button>' +
                         '<audio id="a" data-id="pod:gv:f" data-src="https://ep.example.test/f.mp3" data-title="Latest" data-img="/aagrapevine/f.webp" data-du="1800" data-sh="gv" data-u="https://player.example.test/f"></audio>' +
                         '<a id="row" href="https://ep.example.test/r.mp3" data-id="pod:wo:r" data-src="https://ep.example.test/r.mp3" data-title="Weekly Open · Meeting of October 1" data-meta="Oct 1 · 1:00:00" data-img="" data-du="3600" data-sh="wo" data-u="https://player.example.test/r"></a></div>',
                   scripts: ["src/assets/js/home.js"] });
  for (const k in store) p.win.localStorage.setItem(k, store[k]);
  const made = {};
  p.win.Alpine = { data: (n, f) => { made[n] = f; } };
  p.doc.dispatchEvent(new p.win.Event("alpine:init"));
  const c = made.homePlayer();
  Object.assign(c, { $root: p.$("#hp"), $refs: { audio: p.$("#a"), title: p.$("#t"), meta: p.$("#m"), art: p.$("#art"), resume: p.$("#box") },
                     $nextTick: (fn) => fn() });
  c.init();
  return { p, c, a: p.$("#a") };
}
"""


class HomePlayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if HomePlayer.r is not None:
            return
        day = 864e5
        store = {
            "gv:audio:pos": json.dumps({"pod:gv:x": [600, 0], "pod:gv:f": [120, 0], "pod:gv:done": [-1, 0]}),
            "gv:audio:last": json.dumps({"id": "pod:gv:x", "t": "Half heard", "a": "https://ep.example.test/x.mp3", "art": "", "du": 1800,
                                         "sh": "gv", "u": "", "at": "AT"}),
        }
        HomePlayer.r = run_js(self, HOME_JS + r"""
          const store = input.store;
          store["gv:audio:last"] = store["gv:audio:last"].replace('"AT"', String(NOW - 2 * 864e5));
          const res = {};
          let { p, c, a } = home(store);
          res.start = { resume: c.resume && c.resume.t, left: c.resumeLeft(), label: c.resumeLabel(), done: c.isDone("pod:gv:done"),
                        doneX: c.isDone("pod:gv:x"), want: c.want, started: c.started };
          // the latest episode: the native play button → its saved place
          p.fire(a, "play"); a.duration = 1800; p.fire(a, "loadedmetadata");
          res.featured = { at: a.currentTime, started: c.started };
          a.currentTime = 400; p.fire(a, "pause");
          const after = () => ({ pos: JSON.parse(p.win.localStorage.getItem("gv:audio:pos")), last: JSON.parse(p.win.localStorage.getItem("gv:audio:last")) });
          res.paused = after();
          // a "More episodes" row, played to the end
          c.play(p.$("#row"));
          res.row = { src: a.src, current: c.current, title: c.title, meta: c.meta, want: c.want };
          p.fire(a, "play"); a.duration = 3600; a.currentTime = 3590; p.fire(a, "ended");
          res.ended = { saved: c.saved["pod:wo:r"], doneWhileLoaded: c.isDone("pod:wo:r"), stored: after().pos["pod:wo:r"][0] };
          // "Continue listening"
          c.resumeLast();
          res.resumed = { src: a.src, title: c.title, want: c.want, resume: c.resume };
          a.duration = NaN; p.fire(a, "loadedmetadata");
          res.resumed.at = a.currentTime;
          p.fire(a, "play"); a.currentTime = 700; p.fire(a, "pause");
          res.final = after();
          res.now = NOW;
          res.keys = Object.keys(Object.fromEntries([...Array(p.win.localStorage.length)].map((_, i) => [p.win.localStorage.key(i), 1]))).sort();
          // nothing left part-way, or too long ago: no card
          res.none = home({}).c.resume;
          res.old = home({ "gv:audio:pos": store["gv:audio:pos"], "gv:audio:last": store["gv:audio:last"].replace(String(NOW - 2 * 864e5), String(NOW - 61 * 864e5)) }).c.resume;
          // what Home saved is what Listen reads (media.js)
          const L = "https://example.test/aagrapevine/listen/";
          const lp = page({ url: L, html: '<script type="application/json" id="media-initial">{"shows":{},"latest":{},"items":[]}</script>' +
                                  '<script type="application/json" id="media-i18n">{"left":"{t} left"}</script><div id="root" data-total="0" data-share-base="' + L + '"></div>',
                            scripts: ["src/assets/js/media.js"] });
          for (let i = 0; i < p.win.localStorage.length; i++) lp.win.localStorage.setItem(p.win.localStorage.key(i), p.win.localStorage.getItem(p.win.localStorage.key(i)));
          const made = {}, stores = {};
          lp.win.Alpine = { data: (n, f) => { made[n] = f; }, store: (n, v) => (v ? (stores[n] = v) : stores[n]) };
          lp.doc.dispatchEvent(new lp.win.Event("alpine:init"));
          stores.audio.init();
          const lc = made.podcastPage();
          Object.assign(lc, { $el: lp.$("#root"), $refs: {}, $store: { audio: stores.audio }, $watch() {}, $nextTick: (fn) => fn() });
          lc.init();
          res.listen = { resume: lc.resumeEp && lc.resumeEp.id, left: lc.leftText(lc.resumeEp), done: stores.audio.isDone("pod:wo:r"),
                         featured: stores.audio.resumeAt({ id: "pod:gv:f" }) };
          out(res);""", data={"store": store}, needs_modules=False)

    def test_it_starts_where_the_visitor_left_off(self):
        s = self.r["start"]
        self.assertEqual((s["resume"], s["left"], s["label"]), ("Half heard", "20 min left", "Resume: Half heard"))
        self.assertEqual((s["done"], s["doneX"], s["want"], s["started"]), (True, False, 120, False))
        self.assertEqual(self.r["featured"], {"at": 120, "started": True})

    def test_it_saves_as_listen_does(self):
        p = self.r["paused"]
        now = self.r["now"]
        self.assertEqual(p["pos"]["pod:gv:f"], [400, now])
        self.assertEqual(p["last"], {"id": "pod:gv:f", "t": "Latest", "a": "https://ep.example.test/f.mp3", "art": "/aagrapevine/f.webp",
                                     "du": 1800, "sh": "gv", "u": "https://player.example.test/f", "at": now})
        self.assertEqual(self.r["keys"], ["gv:audio:last", "gv:audio:pos"], "nothing else is stored")

    def test_a_row_plays_from_its_place_and_ends_finished(self):
        self.assertEqual(self.r["row"], {"src": "https://ep.example.test/r.mp3", "current": "pod:wo:r",
                                         "title": "Weekly Open · Meeting of October 1", "meta": "Oct 1 · 1:00:00", "want": 0})
        self.assertEqual(self.r["ended"], {"saved": -1, "doneWhileLoaded": False, "stored": -1})

    def test_continue_listening(self):
        r = self.r["resumed"]
        self.assertEqual((r["src"], r["title"], r["want"], r["resume"], r["at"]), ("https://ep.example.test/x.mp3", "Half heard", 600, None, 600))
        self.assertEqual(self.r["final"]["pos"]["pod:gv:x"][0], 700)
        self.assertEqual(self.r["final"]["last"]["id"], "pod:gv:x")
        self.assertIsNone(self.r["none"])
        self.assertIsNone(self.r["old"], "after 60 days the card is gone")

    def test_listen_reads_what_home_saved(self):
        self.assertEqual(self.r["listen"], {"resume": "pod:gv:x", "left": "18 min left", "done": True, "featured": 400})


class HomeResumeFocus(unittest.TestCase):
    """Round-12 review (u1-3): the "Continue listening" box goes away once something plays — keyboard focus in it (its
    Resume button) goes to the player, not to the page's start."""

    def test_the_keyboard_goes_on_from_the_player(self):
        store = {"gv:audio:pos": json.dumps({"pod:gv:x": [600, 0]}),
                 "gv:audio:last": json.dumps({"id": "pod:gv:x", "t": "Half heard", "a": "https://ep.example.test/x.mp3", "art": "", "du": 1800,
                                              "sh": "gv", "u": "", "at": "AT"})}
        r = run_js(self, HOME_JS + r"""
          const store = input;
          store["gv:audio:last"] = store["gv:audio:last"].replace('"AT"', String(NOW - 864e5));
          const at = (p) => p.doc.activeElement.id || p.doc.activeElement.tagName;
          const res = {};
          let { p, c, a } = home(store);
          p.$("#resume").focus();
          c.resumeLast();                                    // Enter on Resume
          res.resumed = { focus: at(p), resume: c.resume, src: a.src };
          ({ p, c, a } = home(store));
          p.$("#resume").focus();
          p.fire(a, "play");                                 // a headset's play key, the focus still on Resume
          res.played = { focus: at(p), started: c.started };
          ({ p, c, a } = home(store));
          p.$("#elsewhere").focus();
          c.resumeLast();
          res.elsewhere = at(p);
          out(res);""", data=store, needs_modules=False)
        self.assertEqual(r["resumed"], {"focus": "a", "resume": None, "src": "https://ep.example.test/x.mp3"})
        self.assertEqual(r["played"], {"focus": "a", "started": True})
        self.assertEqual(r["elsewhere"], "elsewhere", "focus outside the box is left where it is")


class HomeResumeWords(unittest.TestCase):
    """Release check R12-HOME-ES-QUEDAN: Home's "Continue listening: <title> — 23 min left" puts the time left after a
    dash, inside the sentence — in Spanish "— quedan 23 min", lower case (Listen's own label, on its own, keeps
    "Quedan 23 min"). The words are the ones Home's template gives home.js (data-left)."""

    def test_the_time_left_inside_the_sentence(self):
        media = json.loads(read("src", "_i18n", "media.json"))
        key = re.search(r"data-left=\"\{\{ '(media\.\w+)' \| t\(L\) \}\}\"", read("src", "pages", "index.njk")).group(1)
        store = {"gv:audio:pos": json.dumps({"pod:gv:x": [600, 0]}),
                 "gv:audio:last": json.dumps({"id": "pod:gv:x", "t": "Half heard", "a": "https://ep.example.test/x.mp3", "art": "", "du": 1800,
                                              "sh": "gv", "u": "", "at": "AT"})}
        r = run_js(self, HOME_JS + r"""
          const store = input.store;
          store["gv:audio:last"] = store["gv:audio:last"].replace('"AT"', String(NOW - 864e5));
          out(Object.fromEntries(Object.entries(input.left).map(([l, w]) => [l, home(store, w).c.resumeLeft()])));""",
                   data={"store": store, "left": media[key]}, needs_modules=False)
        self.assertEqual(r, {"en": "20 min left", "es": "quedan 20 min"})
        self.assertEqual(media["media.left"]["es"], "Quedan {t}", "Listen's label, on its own, keeps its capital")


# ------------------------------------------------------------------------------------------- search
class SearchResults(unittest.TestCase):
    EPISODE = {"id": "pod:gv:c8fe55f36619", "kind": "episode", "source": "podcast", "status": "ok", "lang": "en", "date": "2026-10-12T04:15:00Z",
               "url": "https://player.captivate.fm/episode/ded1749e", "title": "Hot Topic: Sponsorship [Season 11, Episode 15]",
               "summary": "Meg and Leslie join Don and Sam.", "extra": {"show_name": "AA Grapevine's Podcast"}}

    def test_the_index_sends_an_episode_to_the_sites_player(self):
        r = run_js(self, r"""
          const one = (lang) => JSON.parse(filters.searchIndexJson({ episodes: { items: [input] } }, [], lang, {})).items.find((e) => e.k === "episode");
          out({ en: one("en"), es: one("es") });""", data=self.EPISODE)
        self.assertEqual((r["en"]["u"], r["en"]["u2"]), ("/listen/?ep=pod:gv:c8fe55f36619", "https://player.captivate.fm/episode/ded1749e"))
        self.assertEqual(r["es"]["u"], "/es/listen/?ep=pod:gv:c8fe55f36619")

    def test_the_host_page_is_a_second_link_beside_the_result(self):
        if not (ROOT / "node_modules" / "minisearch").is_dir():
            self.skipTest("node_modules is not installed (npm ci)")
        r = run_js(self, PAGE_JS + r"""
          const ids = ["ss-q", "ss-clear", "ss-status", "ss-results", "ss-more", "ss-jump-wrap", "ss-jump", "ss-kinds-wrap", "ss-start",
                       "ss-none", "ss-partial", "ss-error", "ss-loading", "ss-did", "ss-none-kind", "ss-layout", "ss-none-title", "ss-none-kind-btn", "ss-retry"];
          const cfg = { lang: "en", locale: "en-US", index: "/search-index.json", title: "Search", kinds: { episode: "Podcast episode" }, groups: {},
                        src: { podcast: "Podcast" }, langTitle: {}, s: { count: "{n} results", countOne: "1 result", countIn: "", noneTitle: "", noneKind: "",
                        isNew: "New", auto: "", autoHelp: "", external: "opens a new tab", subscriber: "", subscriberTitle: "", byline: "", tbc: "", tbcHelp: "",
                        episodePage: "Episode page" } };
          const html = '<form id="ss-form"><input id="ss-q"></form><section id="site-search">' + ids.slice(1).map((i) => (i === "ss-results" ? '<ol id="' + i + '"></ol>' : '<div id="' + i + '"></div>')).join("") +
                       '</section><template id="ss-icons"></template><script type="application/json" id="ss-config">' + JSON.stringify(cfg) + '</script>';
          const fetch = async () => ({ ok: true, json: async () => ({ items: [input] }) });
          const p = page({ url: "https://example.test/aagrapevine/search/?q=sponsorship", html, globals: { SITE: { lang: "en", base: "/aagrapevine/" }, fetch },
                           scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js", "src/assets/js/search.js"] });
          await p.ready();
          await p.tick(500);
          const li = p.$("#ss-results li");
          out({ main: li && li.querySelector("a[data-nav]").getAttribute("href"), mainHasAlt: !!(li && li.querySelector("a[data-nav] .ss-alt")),
                alt: li && li.querySelector("a.ss-alt") && li.querySelector("a.ss-alt").getAttribute("href"),
                altText: li && li.querySelector("a.ss-alt") && li.querySelector("a.ss-alt").textContent,
                altTab: li && li.querySelector("a.ss-alt") && li.querySelector("a.ss-alt").getAttribute("target") });""",
                   data={"id": "pod:gv:c8fe55f36619", "k": "episode", "t": "Hot Topic: Sponsorship", "u": "/listen/?ep=pod:gv:c8fe55f36619",
                         "u2": "https://player.captivate.fm/episode/ded1749e", "src": "podcast"}, needs_modules=False)
        self.assertEqual(r["main"], "/aagrapevine/listen/?ep=pod:gv:c8fe55f36619")
        self.assertFalse(r["mainHasAlt"], "never a link inside the result's link")
        self.assertEqual((r["alt"], r["altTab"]), ("https://player.captivate.fm/episode/ded1749e", "_blank"))
        self.assertIn("Episode page", r["altText"])
        self.assertIn("player.captivate.fm", r["altText"])


# ------------------------------------------------------------------------------------------- what a Share sends
SHARE_NOW = "2026-10-06T15:00:00Z"
ES_MONTH = re.compile(r"\b(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Setiembre|Octubre|Noviembre|Diciembre)\b")


class ShareWords(unittest.TestCase):
    """Round-12 review (u1-4 / XC-2, u1-5 / XC-4): a story's or a video's Share sends the title its magazine (or
    YouTube) published — never our translation, which the message cannot mark as one, credited "— La Viña" — and,
    on the Spanish pages, the issue as Spanish writes it inside a sentence: "— La Viña, septiembre–octubre de 2026"."""

    def test_the_issue_inside_a_sentence(self):
        r = run_js(self, r"""
          const f = filters.readInSentence;
          out([f("Septiembre–Octubre 2026", "es", "lv"), f("Agosto 2026", "es", "gv"), f("October 2026", "en", "gv"),
               f("September–October 2026", "en", "lv"), f("Edición especial", "es", "gv")]);""")
        self.assertEqual(r, ["septiembre–octubre de 2026", "agosto de 2026", "October 2026", "September–October 2026", "Edición especial"])

    def test_a_video_keeps_the_title_youtube_shows(self):
        item = {"id": "yt:abcdefghijk", "kind": "video", "title": "Hot Topic: Sponsorship", "lang": "en", "category": "gv",
                "date": "2026-09-01T12:00:00Z", "status": "ok", "machine": ["es"],
                "i18n": {"title": {"en": "Hot Topic: Sponsorship", "es": "Tema candente: padrinazgo"}},
                "extra": {"video_id": "abcdefghijk", "playlists": [], "duration_sec": 300}}
        r = run_js(self, r"""
          const items = filters.mediaItems({ items: [input] }, "videos");
          const one = (lang) => JSON.parse(filters.mediaInitialJson(items, "videos", lang, [])).items[0];
          out({ es: one("es"), en: one("en"), orig: filters.mediaOrigTitle(items[0], "es"), shown: filters.mediaTitle(items[0], "es") });""",
                   data=item)
        self.assertEqual((r["es"]["t"], r["es"]["o"]), ("Tema candente: padrinazgo", "Hot Topic: Sponsorship"))
        self.assertNotIn("o", r["en"], "nothing extra where the card shows the title as published")
        self.assertEqual((r["orig"], r["shown"]), ("Hot Topic: Sponsorship", "Tema candente: padrinazgo"))

    def test_a_weekly_open_meeting_shares_the_title_the_page_shows(self):
        """(follow-up to XC-2) A Weekly Open meeting's card shows the site's own short form, "Meeting of October 7,
        2026" — nobody's published title (YouTube's is "Grapevine Weekly Open AA Meeting, October 7, 2026 [Season 2,
        Episode 15]"): its Share sends what the page shows, in the page's language. A Weekly Open video whose title
        says more than its date keeps YouTube's words, as any video."""
        def weekly(vid, en, es):
            return {"id": f"yt:{vid}", "kind": "video", "title": en, "lang": "en", "category": "gv",
                    "date": "2026-10-07T16:00:00Z", "status": "ok", "machine": ["es"], "i18n": {"title": {"en": en, "es": es}},
                    "extra": {"video_id": vid, "playlists": ["Grapevine Weekly Open AA Meeting"], "duration_sec": 3600}}
        items = [weekly("wo000000001", "Grapevine Weekly Open AA Meeting, October 7, 2026 [Season 2, Episode 15]",
                        "Grapevine Weekly Open AA Meeting, 7 de octubre de 2026 [Temporada 2, Episodio 15]"),
                 weekly("wo000000002", "Grapevine Weekly Open AA Meeting: Gratitude in Action",
                        "Grapevine Weekly Open AA Meeting: Gratitud en acción")]
        r = run_js(self, r"""
          const items = filters.mediaItems({ items: input }, "videos");
          const cards = (lang) => JSON.parse(filters.mediaInitialJson(items, "videos", lang, [])).items;
          out({ es: cards("es"), en: cards("en"), orig: items.map((i) => [filters.mediaOrigTitle(i, "es"), filters.mediaOrigTitle(i, "en")]) });""",
                   data=items)
        es = {c["id"]: c for c in r["es"]}
        en = {c["id"]: c for c in r["en"]}
        self.assertEqual(es["wo000000001"]["t"], "Reunión del 7 de octubre de 2026")
        self.assertNotIn("o", es["wo000000001"], "the Spanish card's Share sends its own Spanish words (o || t)")
        self.assertEqual((en["wo000000001"]["t"], en["wo000000001"].get("o")), ("Meeting of October 7, 2026", None))
        self.assertEqual(r["orig"][0], ["Reunión del 7 de octubre de 2026", "Meeting of October 7, 2026"])
        # a title of its own: YouTube's words (show name taken off, as the card shows it), never our translation
        self.assertEqual((es["wo000000002"]["t"], es["wo000000002"]["o"]), ("Gratitud en acción", "Gratitude in Action"))
        self.assertEqual(r["orig"][1], ["Gratitude in Action", "Gratitude in Action"])


# Read, its archive file, Published and Watch built in memory (Eleventy: only those pages, both languages)
SHARE_PAGES_JS = r"""
const os = await import("node:os");
process.env.ONLY = "read.njk,read-archive,published.njk,watch.njk";
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r12-u1-"));
try {
  const pages = await new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" }).toJSON();
  const want = ["/read/", "/es/read/", "/es/read-archive.json", "/published/", "/es/published/", "/watch/", "/es/watch/"];
  out(Object.fromEntries(want.map((u) => [u, (pages.find((p) => p.url === u) || {}).content || ""])));
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""


def attr(html: str, name: str) -> str | None:
    m = re.search(r'\s' + re.escape(name) + r'="([^"]*)"', html)
    return m.group(1) if m else None


class SharePages(unittest.TestCase):
    """The same on the built pages, whatever the day's stories and videos are: each Share button sends the title its
    row shows as the original (when it shows one), and no Spanish credit line capitalises its month (that one judges
    the day's issue names too — a "Edición especial 2027" would fail it — so the publish gate leaves it to the Code
    check: scripts/ops/gate_tests.py DATA_TESTS; SpanishCredits tests the same code on data of its own)."""
    built: dict | None = None

    def pages(self) -> dict:
        if SharePages.built is None:
            SharePages.built = run_js(self, SHARE_PAGES_JS, now=SHARE_NOW, timeout=300)
        return SharePages.built

    def credits(self, url: str) -> list[str]:
        return re.findall(r'data-share-text="([^"]*)"', self.pages()[url])

    def test_read_shares_the_magazines_own_title(self):
        bad = []
        for url in ("/read/", "/es/read/"):
            html = self.pages()[url]
            rows = re.findall(r'<li class="read-article.*?</li>', html, re.S)
            self.assertTrue(rows, url)
            for row in rows:
                if ' data-share-title="' not in row:        # (no Share — or the older issues' template, below)
                    continue
                orig = re.search(r'<span class="italic" lang="[^"]*">([^<]*)</span>', row)
                shown = re.search(r'<span class="font-display [^"]*"[^>]*>([^<]*)</span>', row).group(1)
                sent = attr(row.split('class="read-share"', 1)[1], "data-share-title")
                if sent != (orig.group(1) if orig else shown):
                    bad.append(f"{url}: {shown!r} shared as {sent!r}")
        self.assertEqual(bad[:5], [], f"{len(bad)} stories")
        older = self.pages()["/es/read/"]          # the older issues (read-archive.json, read.js): the same
        self.assertIn(':data-share-title="a.o || a.t"', older)
        self.assertIn("(is.ls ? ', ' + is.ls : '')", older)

    def test_published_shares_the_magazines_own_title(self):
        bad = []
        for url in ("/published/", "/es/published/"):
            cards = re.findall(r'<article class="pw-card".*?</article>', self.pages()[url], re.S)
            self.assertTrue(cards, url)
            for card in cards:
                orig = re.search(r'<p class="pw-orig">.*?<span lang="[^"]*">([^<]*)</span>', card, re.S)
                shown = re.search(r'<a class="pw-link"[^>]*>([^<]*)', card).group(1)
                sent = attr(card.split('class="pw-share"', 1)[1], "data-share-title")
                if sent != (orig.group(1) if orig else shown):
                    bad.append(f"{url}: {shown!r} shared as {sent!r}")
        self.assertEqual(bad[:5], [], f"{len(bad)} stories")

    def test_watch_shares_the_title_youtube_shows(self):
        for url in ("/watch/", "/es/watch/"):
            html = self.pages()[url]
            init = json.loads(re.search(r'<script type="application/json" id="media-initial">(.*?)</script>', html, re.S).group(1))
            # the first cards (server-rendered) send what the page's JSON says the list's own cards send: o || t
            cards = [c for c in re.findall(r'<article class="vid-card.*?</article>', html, re.S) if ' data-share-title="' in c]
            shares = [unescape(attr(c.split("data-js-only", 1)[1], "data-share-title")) for c in cards]
            self.assertTrue(shares, url)
            self.assertEqual(shares, [v.get("o", v["t"]) for v in init["items"]][:len(shares)], url)
        self.assertIn(':data-share-title="v.o || v.t"', self.pages()["/watch/"])

    def test_spanish_credit_lines_write_the_month_in_lower_case(self):
        """The day's data (DATA_TESTS: the Code check runs it, the publish gate does not)."""
        for url in ("/es/read/", "/es/published/"):
            credits = self.credits(url)
            self.assertTrue(credits, url)
            bad = [c for c in credits if ES_MONTH.search(c) or (re.search(r"\d{4}", c) and not re.search(r" de \d{4}$", c))]
            self.assertEqual(bad[:5], [], f"{url}: {len(bad)} of {len(credits)}")
        issues = json.loads(self.pages()["/es/read-archive.json"])["issues"]
        undated = json.loads(read("src", "_i18n", "read.json"))["read.undated"]["es"]
        for i in issues:
            with self.subTest(issue=i["label"]):
                self.assertEqual("ls" in i, i["label"] != undated, "an undated issue names no issue in the credit line")
                if "ls" in i:
                    self.assertNotRegex(i["ls"], ES_MONTH)


def story(pub: str, key: str | None, slug: str, label_es: str = "", label_en: str = "", texas: bool = False) -> dict:
    """A story of data/site/articles.json (and spotlight.json: `texas`, a writer from Area 65): one of `pub`'s issue
    `key` ("2026-09"; None: undated), with its issue's label as the data names it (label_en and label_es), if any."""
    lv = pub == "lv"
    extra = {"publication": pub, "author": "Pat R.", "free": True}
    if key:
        extra.update(issue_key=key, issue_date=f"{key}-01", pub_date=f"{key}-01")
    if texas:
        extra["geo"] = {"scope": "neta65", "city": "Tyler", "county": "Smith", "state": "TX", "country": "US",
                        "label_en": "Tyler, Texas", "label_es": "Tyler, Texas"}
    it = {"id": f"{pub}:{key or 'undated'}:{slug}", "source": "lavina" if lv else "grapevine", "kind": "article",
          "url": f"https://www.{'aalavina' if lv else 'aagrapevine'}.org/revista/{slug}", "title": slug.replace("-", " ").capitalize(),
          "lang": "es" if lv else "en", "date": f"{key}-01" if key else None, "category": pub, "status": "ok", "extra": extra}
    if not key and texas:
        it["date"] = extra["pub_date"] = "2026-08-20"
    if label_es:
        extra["issue_label"] = label_en
        it["i18n"] = {"issue_label": {"en": label_en, "es": label_es}}
    return it


# Ten Grapevine issues (Jan–Oct 2026), three of La Viña's and an undated story: the two newest are Read's current
# issues, the next 8 its earlier ones on the page (SSR_ARCHIVE), the rest in /es/read-archive.json. Two issues have a
# name of their own that is no month: it is written as it is.
CREDIT_DATA = {
    "articles": {"updated": "2026-10-06T06:00:00Z", "issues": [], "items": [
        *[story("gv", f"2026-{m:02d}", f"gv-story-{m}") for m in (10, 9, 8, 7, 5, 4, 3, 1)],
        story("gv", "2026-06", "gv-special", "Edición especial 2026", "Special Issue 2026"),
        story("gv", "2026-02", "gv-anniversary", "Número de aniversario", "Anniversary Issue"),
        *[story("lv", f"2026-{m:02d}", f"lv-historia-{m}") for m in (9, 7, 5)],
        story("gv", None, "gv-undated"),
    ]},
    "spotlight": {"updated": "2026-10-06T06:00:00Z", "list_days": [60, 90], "default_scope": "neta65", "items": [
        story("gv", "2026-09", "gv-tyler", "Septiembre 2026", "September 2026", texas=True),
        story("lv", "2026-09", "lv-tyler", texas=True),
        story("gv", "2026-08", "gv-tyler-special", "Edición especial 2026", "Special Issue 2026", texas=True),
        story("gv", None, "gv-tyler-undated", texas=True),
    ]},
}


class SpanishCredits(unittest.TestCase):
    """(follow-up to u1-5) The credit line a story's Share sends on the Spanish pages — Read (its current issues, the
    earlier ones on the page and those of /es/read-archive.json) and Published — built from data of its own
    (SITE_DATA: CREDIT_DATA, never the day's data/site, so only a change of the code can fail it): the month as
    Spanish writes it inside a sentence, an issue's own name as it is, no issue for an undated story. English is
    unchanged."""
    built: dict | None = None

    def pages(self) -> dict:
        if SpanishCredits.built is None:
            with tempfile.TemporaryDirectory(prefix="gv-r12-u1-data-") as folder:
                for name, body in CREDIT_DATA.items():
                    Path(folder, name + ".json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
                SpanishCredits.built = run_js(self, SHARE_PAGES_JS, now=SHARE_NOW, timeout=300,
                                              env={"SITE_DATA": folder, "WRITERS_ARCHIVE": ""})
        return SpanishCredits.built

    def credits(self, url: str, button: str) -> set[str]:
        """The credit lines of the page's Share buttons (not the older issues' template, which has :data-share-text)."""
        buttons = re.findall(r'<button type="button" class="' + button + r'"[^>]*>', self.pages()[url])
        return {unescape(t) for t in (attr(b, "data-share-text") for b in buttons) if t is not None}

    def test_read_and_its_older_issues(self):
        self.assertEqual(self.credits("/es/read/", "read-share"), {
            "— Grapevine, octubre de 2026", "— La Viña, septiembre–octubre de 2026",           # the current issues
            "— Grapevine, septiembre de 2026", "— Grapevine, agosto de 2026", "— Grapevine, julio de 2026",
            "— La Viña, julio–agosto de 2026", "— Grapevine, Edición especial 2026", "— Grapevine, mayo de 2026",
            "— La Viña, mayo–junio de 2026", "— Grapevine, abril de 2026"})
        issues = json.loads(self.pages()["/es/read-archive.json"])["issues"]
        undated = json.loads(read("src", "_i18n", "read.json"))["read.undated"]["es"]
        # read.js writes "— " + its magazine + (is.ls ? ", " + is.ls : "") (test_read_shares_the_magazines_own_title)
        self.assertEqual([(i["key"], i["label"], i.get("ls")) for i in issues], [
            ("2026-03", "Marzo de 2026", "marzo de 2026"), ("2026-02", "Número de aniversario", "Número de aniversario"),
            ("2026-01", "Enero de 2026", "enero de 2026"), ("undated", undated, None)])
        self.assertIn("— Grapevine, October 2026", self.credits("/read/", "read-share"))
        self.assertIn("— La Viña, September–October 2026", self.credits("/read/", "read-share"))

    def test_published(self):
        self.assertEqual(self.credits("/es/published/", "pw-share"), {
            "— Grapevine, septiembre de 2026", "— La Viña, septiembre–octubre de 2026",
            "— Grapevine, Edición especial 2026", "— Grapevine"})
        self.assertEqual(self.credits("/published/", "pw-share"), {
            "— Grapevine, September 2026", "— La Viña, September–October 2026", "— Grapevine, Special Issue 2026",
            "— Grapevine"})


# ------------------------------------------------------------------------------------------- app.js GV.share
class ShareSheet(unittest.TestCase):
    """Release check R12-SHARE-TITLE-DROPPED: the Web Share spec lets a share target ignore `title`, and Messages on
    an iPhone and WhatsApp do (the message is the text and the link; the link's preview names only the page). So the
    share sheet gets the title at the start of its text too: an episode (no text) arrives as its title and its link,
    a story as its title and its credit line — never the title twice; the link is the button's own. Without a share
    sheet the title, the text and the link are copied, as before."""

    BUTTONS = (
        '<button id="ep" data-share="https://example.test/aagrapevine/listen/?ep=pod:gv:c8fe55f36619" data-share-title="Hot Topic: Sponsorship">Share</button>'
        '<button id="lv" data-share="https://example.test/aagrapevine/es/listen/?ep=pod:gv:c8fe55f36619" data-share-title="Tema candente: padrinazgo">Compartir</button>'
        '<button id="story" data-share="https://www.aagrapevine.org/story" data-share-title="A Sense of Belonging" data-share-text="— Grapevine, October 2026">Share</button>'
        '<button id="video" data-share="https://www.youtube.com/watch?v=abcdefghijk" data-share-title="Mi primer paso" data-share-text=" — La Viña, septiembre–octubre de 2026">Share</button>'
        '<button id="named" data-share="https://example.test/aagrapevine/meetings/" data-share-title="Meeting — NETA 65" data-share-text="Meeting — NETA 65: third Wednesday">Share</button>')

    def run_page(self, sheet: bool) -> dict:
        return run_js(self, PAGE_JS + r"""
          const sent = [], copied = [];
          const nav = { clipboard: { writeText: (t) => { copied.push(t); return Promise.resolve(); } } };
          if (input.sheet) nav.share = (d) => { sent.push(JSON.parse(JSON.stringify(d))); return Promise.resolve(); };
          const p = page({ html: input.html, globals: { SITE: { lang: "en", base: "/aagrapevine/" }, navigator: nav },
                           scripts: ["src/assets/js/app.js"] });
          await p.ready();
          for (const id of ["ep", "lv", "story", "video", "named"]) p.click(p.$("#" + id));
          p.win.GV.share({ text: "“A quote.” — Grapevine" });          // (Read's quote: text only)
          await p.tick(10);
          out({ sent, copied, errors: p.errors.map(String) });""", data={"html": self.BUTTONS, "sheet": sheet}, needs_modules=False)

    def test_the_share_sheet_gets_the_title_in_its_text(self):
        r = self.run_page(True)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["sent"], [
            {"title": "Hot Topic: Sponsorship", "text": "Hot Topic: Sponsorship",
             "url": "https://example.test/aagrapevine/listen/?ep=pod:gv:c8fe55f36619"},
            {"title": "Tema candente: padrinazgo", "text": "Tema candente: padrinazgo",
             "url": "https://example.test/aagrapevine/es/listen/?ep=pod:gv:c8fe55f36619"},
            {"title": "A Sense of Belonging", "text": "A Sense of Belonging\n— Grapevine, October 2026", "url": "https://www.aagrapevine.org/story"},
            {"title": "Mi primer paso", "text": "Mi primer paso\n— La Viña, septiembre–octubre de 2026",
             "url": "https://www.youtube.com/watch?v=abcdefghijk"},
            {"title": "Meeting — NETA 65", "text": "Meeting — NETA 65: third Wednesday", "url": "https://example.test/aagrapevine/meetings/"},
            {"text": "“A quote.” — Grapevine"},
        ])
        self.assertEqual(r["copied"], [])

    def test_without_a_share_sheet_the_copy_is_as_before(self):
        r = self.run_page(False)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["sent"], [])
        self.assertEqual(r["copied"], [
            "Hot Topic: Sponsorship\nhttps://example.test/aagrapevine/listen/?ep=pod:gv:c8fe55f36619",
            "Tema candente: padrinazgo\nhttps://example.test/aagrapevine/es/listen/?ep=pod:gv:c8fe55f36619",
            "A Sense of Belonging\n— Grapevine, October 2026\nhttps://www.aagrapevine.org/story",
            "Mi primer paso\n — La Viña, septiembre–octubre de 2026\nhttps://www.youtube.com/watch?v=abcdefghijk",
            "Meeting — NETA 65\nMeeting — NETA 65: third Wednesday\nhttps://example.test/aagrapevine/meetings/",
            "“A quote.” — Grapevine\nhttps://example.test/aagrapevine/",
        ])


# ------------------------------------------------------------------------------------------- the templates
class Pages(unittest.TestCase):
    def test_la_vina_is_videos_and_spoken_stories_never_podcast(self):
        media = json.loads(read("src", "_i18n", "media.json"))
        keys = [k for k in media if k.startswith("media.lv_")]
        self.assertGreaterEqual(len(keys), 8)
        for k in keys:
            for lang in ("en", "es"):
                self.assertNotRegex(media[k][lang], r"(?i)p[oó]d ?cast", f"{k} ({lang})")
        self.assertIn("historias habladas", media["media.lv_title"]["es"].lower())

    def test_the_card_comes_first_on_the_spanish_page(self):
        src = read("src", "pages", "listen.njk")
        self.assertIn('{%- set lvFirst = lang == "es" -%}', src)
        first, shows = src.index("{% if lvFirst and lvStories.lists.length %}"), src.index('<section id="shows"')
        episodes, last = src.index('<section id="episodes"'), src.index("{% if not lvFirst and lvStories.lists.length %}")
        self.assertLess(first, shows)
        self.assertLess(episodes, last)
        self.assertIn("('/watch/?pl=' + p.id + '#videos') | lurl(lang)", src)
        self.assertIn("'/watch/?lang=es#videos' | lurl(lang)", src)
        self.assertIn('lang="es">{{ p.title }}', src, "La Viña's own titles, marked Spanish on the English page")

    def test_share_buttons_sit_beside_links(self):
        for page_, pattern in (("read.njk", r'</a>\s*\{%- if iss %\}\s*<button type="button" class="read-share"'),
                               ("published.njk", r'<button type="button" class="pw-share"')):
            self.assertRegex(read("src", "pages", page_), pattern)
        # no <button> inside an <a> in the rows
        for page_ in ("listen.njk", "watch.njk", "read.njk"):
            src = read("src", "pages", page_)
            for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", src, re.S):
                self.assertNotIn("<button", m.group(1), page_)

    def test_whats_new_sends_episodes_to_the_sites_player(self):
        src = read("src", "pages", "whats-new.njk")
        self.assertIn('(("/listen/?ep=" + it.id) | lurl(lang)) if isEp', src)
        self.assertIn('"media.episode_page" | t(lang)', src)


if __name__ == "__main__":
    unittest.main()
