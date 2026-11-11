"""Round 25, unit B — La Viña's weekly open meeting is a podcast of its own on the site ("lvo", config sources.podcasts:
"Reunión abierta semanal de Alcohólicos Anónimos de La Viña", in Spanish, weekly_open "lavina"), and the podcasts keep
updating when one feed fails:

  * Sync         — scripts/sync/podcasts.py on a saved copy of the real feed (tests/fixtures/podcasts/
                   reunin-abierta-semanal.xml, read 2026-11-11: its first episode, the meeting of Thursday November 5,
                   published Monday November 9): the episode's address (Captivate's episode page — its <link> is only
                   the show's page), language (Spanish), length, numbers, the show's links, and — a weekly open
                   meeting's show — extra.weekly_open, extra.meeting_date (from its description: the title has no
                   date) and extra.generic_title (the title is only the show's name). The show's language is the
                   config's "es" although its feed says <language>en</language>. Made-up next episodes: a weekday and
                   the next meeting's date in the text, no date at all, a title of its own; a show of no meeting gets
                   none of those fields.
  * RealSettings — config/site.yml as the committee keeps it (a content test): the shows as this file's copies, La
                   Viña's meeting show, its meeting's page. Every other class uses this file's copies of the shows.
  * MeetingDate  — meeting_date(): the title's own date wins (the Grapevine Weekly Open's — even when its description
                   names another day, as the real "May 6, 2026" episode does); else the description's date said to be
                   the meeting's ("del …", "held on …"), else the latest before publication; Spanish and English
                   forms, abbreviations, "1.º", "1ro", "1er", "1ero" and "primero", a date without its year (the year
                   that puts it just before publication); a date after publication (the next meeting), long before it
                   (an anniversary), impossible or in figures only ("05/11/2026": either way round) is never the
                   meeting's.
  * BuildData    — build_data: episodes out at the same moment (so far AA Grapevine's Podcast and La Viña's meeting,
                   Mondays 00:15 Eastern) in config order, whatever their ids (sort_episodes); a show description that
                   carries its own translation in parentheses is split into its two languages (given_translation).
  * BuildDataRun — build_data.main over a raw podcasts.json as an older sync wrote it: episodes.json in config order on
                   a tied Monday, La Viña's show in Spanish (the config's language, not its feed's) with its
                   description's two halves.
  * GenericTitle — is_generic_title(): only the show's name (accents, case, the numbering tail — bracketed or not —
                   aside) — never a title with words of its own ("Introducing The Grapevine Open AA Meeting"); a title
                   that several episodes of a meeting show share is generic too (shared_titles); the three copies of the
                   unbracketed-numbering rule (podcasts.py, media.js, send_digest.py) are the same.
  * OneShowFails — main(): one show's feed failing keeps the source ok (its `updated` moves with the other shows'
                   news), names the show in stats.warnings and keeps its episodes; stats.shows[key] says ok false,
                   its error, its last good read (`updated`, which a failing run never moves) and `failing_since`
                   (kept while it keeps failing — checked with an older one, since runs in one second write the same
                   time; also for a show never read, whose 7-day alarm counts from it). Every show failing fails the
                   source; a show that answers again is ok again.
  * RunSummary   — .github/workflows/update.yml "Write run summary": a show failing names itself on the run page
                   (a warning) and, once it has failed for 7 days, is a source that stopped updating ("Podcasts —
                   <show>") — also in a run where every show failed (the source's own last good read is recent), never
                   twice when the whole source stopped; the report issue's advice for it.
  * Display      — eleventy/filters/media.js (Node.js): La Viña's episode is "Meeting of November 5, 2026" / "Reunión del
                   5 de noviembre de 2026" (and that is what its Share sends), "<title>, episode 2" without a date
                   (an unbracketed numbering taken off first);
                   the Grapevine Weekly Open's titles as before; the shows: language (config first), meeting, label
                   ("Grapevine Weekly Open" / "La Viña Open Meeting"); each meeting's own day; a weekly video's badge
                   by its meeting, and its lang attribute; the show that records a meeting (/meetings/' "Listen to past
                   meetings" — only once it has an episode); the feed's and the search's title; which titles name the
                   meeting's date (mediaTitleDated); the episodes' order per page language (/episodes-index.json: one
                   day's episodes in the page's language first); a failing show on /status/ (statusView partsDown);
                   a show's language (mediaShowLang: config, else episodes.json, else the episode's).
  * Pages        — /listen/, /meetings/, Home, What's New, the RSS feed and the search index built by Eleventy with
                   this file's episodes: three show cards (the first across the row from 1024px, the two meetings side
                   by side), each meeting's own day, language and "How to join" name, "1 episode", the language
                   note; the "Latest episode" on a Monday
                   when two shows came out at once (AA Grapevine's on /listen/, La Viña's on /es/listen/); La Viña's
                   card on /meetings/ links its episodes; Home's rows name La Viña's meeting and say an episode's
                   language where it is not the page's, and its weekly-meetings line says «abiertas» for two; the feed
                   and the search call La Viña's episode by its meeting and date; the search's /listen/ entry names the
                   three shows; What's New marks a show's name in the show's language; the "tell your group" text says
                   the language of each show in another language than the page's.
  * HomeDates    — Home built with a La Viña episode whose date was not found (featured) and the Grapevine Weekly Open's
                   "Introducing …" (a row): both keep their own date.
  * EmailTitle   — the e-mail's title of a dateless meeting episode.

    python -m unittest tests.test_r25_lavina_podcast -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

import feedparser
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_sync_health import NOW, RunSummary, iso, src  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.notify import send_digest as D  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import podcasts as P  # noqa: E402
from scripts.sync import weekly_open as W  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "podcasts" / "reunin-abierta-semanal.xml"
# La Viña's page for its meeting (the committee's choice, 2026-11-11): its podcast's page. Exactly so: with a "/" at
# the end, aalavina.org sends it on to another address
LV_MEETING_PAGE = "https://www.aalavina.org/podcast"
GUID = "7d2cc913-c2b5-46d6-b176-d347a12913c3"
NAME = "Reunión abierta semanal de Alcohólicos Anónimos de La Viña"
# The three shows as config/site.yml has them today (sources.podcasts). The code tests use these copies, never the
# committee's file — a show the committee renames, moves or deletes must not fail them (the publish gate runs them:
# scripts/ops/gate_tests.py); RealSettings checks the file itself (a content test).
LVO = {"key": "lvo", "name": NAME, "feed": "https://feeds.captivate.fm/reunin-abierta-semanal/", "lang": "es",
       "weekly_open": "lavina", "web": LV_MEETING_PAGE,
       "apple": "https://podcasts.apple.com/us/podcast/reuni%C3%B3n-abierta-semanal-de-alcoh%C3%B3licos-an%C3%B3nimos-de-la-vi%C3%B1a/id6832543655",
       "spotify": "https://open.spotify.com/show/5LFFf4NfjdZni1TJcG4jZC"}
CFG_SHOWS = [
    {"key": "gv", "name": "AA Grapevine's Podcast", "feed": "https://feeds.captivate.fm/aa-grapevine/",
     "apple": "https://podcasts.apple.com/us/podcast/aa-grapevines-podcast/id1591924167",
     "spotify": "https://open.spotify.com/show/714djcL57SFf0Nzf40CL8Q",
     "amazon": "https://music.amazon.com/podcasts/de231bfa-837b-4a27-a331-a927019cb5d7",
     "web": "https://www.aagrapevine.org/podcasts"},
    {"key": "wo", "name": "Grapevine Weekly Open AA Meeting", "feed": "https://feeds.captivate.fm/grapevine-weekly-open/",
     "weekly_open": "grapevine", "web": "https://www.aagrapevine.org/grapevine-weekly-open",
     "apple": "https://podcasts.apple.com/us/podcast/grapevine-weekly-open-aa-meeting/id1874809908",
     "spotify": "https://open.spotify.com/show/2jk469TmDC31spPqf8L0SF",
     "amazon": "https://music.amazon.com/podcasts/8dfb5269-8733-42f3-b075-2d9e596bf4c5/grapevine-weekly-open-aa-meeting"},
    LVO,
]
# La Viña's weekly open meeting as config/site.yml lavina_weekly_open has it (the parts lavina_item needs)
LV_MEETING_CFG = {"title_es": "Reunión Abierta de La Viña", "title_en": "La Viña's Open Meeting", "day": "thursday",
                  "time": "12:00", "timezone": "America/New_York", "starts": "2026-11-05", "zoom_id": "871 2036 8287",
                  "passcode": "238047", "summary_es": "Una reunión abierta virtual de AA en español.",
                  "summary_en": "A virtual open AA meeting in Spanish.", "url": LV_MEETING_PAGE}


def feed_xml() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def variant(n: int, title: str, description: str, pub: str) -> str:
    """The fixture's one <item>, made into another episode: its number, title, description and publication date."""
    xml = feed_xml()
    item = re.search(r"<item>.*?</item>", xml, re.S).group(0)
    guid = f"{n:08d}-0000-4000-8000-{n:012d}"
    item = item.replace(GUID, guid).replace("[Temporada 1, episodio 1]", f"[Temporada 1, episodio {n}]")
    item = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", item, flags=re.S)
    item = re.sub(r"<itunes:title>.*?</itunes:title>", f"<itunes:title>{title}</itunes:title>", item, flags=re.S)
    item = re.sub(r"<description>.*?</description>", f"<description><![CDATA[<p>{description}</p>]]></description>", item, flags=re.S)
    item = re.sub(r"<content:encoded>.*?</content:encoded>", "", item, flags=re.S)
    item = re.sub(r"<pubDate>.*?</pubDate>", f"<pubDate>{pub}</pubDate>", item)
    item = re.sub(r"<itunes:episode>1</itunes:episode>", f"<itunes:episode>{n}</itunes:episode>", item)
    return item


def parsed(*items: str):
    xml = feed_xml()
    if items:
        xml = xml.replace("<item>", "".join(items) + "<item>", 1)
    return feedparser.parse(xml.encode("utf-8"))


# ------------------------------------------------------------------------------------------- the sync
class Sync(unittest.TestCase):
    def test_the_first_episode(self):
        [it] = P.build_items(LVO, parsed())
        self.assertEqual(it["id"], "pod:lvo:" + common.short_hash(GUID))
        self.assertEqual((it["source"], it["kind"], it["category"], it["lang"]), ("podcast", "episode", "lvo", "es"))
        self.assertEqual(it["url"], f"https://player.captivate.fm/episode/{GUID}", "its <link> is only aalavina.org/podcast")
        self.assertEqual(it["date"], "2026-11-09T05:15:00Z")
        self.assertEqual(it["title"], f"{NAME} [Temporada 1, episodio 1]")
        ex = it["extra"]
        self.assertEqual((ex["duration_sec"], ex["season"], ex["episode"], ex["audio_bytes"]), (3320, 1, 1, 79688040))
        self.assertEqual(ex["audio_url"], f"https://episodes.captivate.fm/episode/{GUID}.mp3")
        self.assertEqual((ex["show"], ex["show_name"], ex["show_web"]), ("lvo", NAME, "https://www.aalavina.org/podcast"))
        self.assertIn("id6832543655", ex["apple"])
        self.assertEqual(ex["spotify"], "https://open.spotify.com/show/5LFFf4NfjdZni1TJcG4jZC")
        self.assertNotIn("amazon", ex, "no Amazon Music listing")
        # the meeting it records, its date (from the description: "… en español del 5 de noviembre de 2026"),
        # and a title that is only the show's name
        self.assertEqual((ex["weekly_open"], ex["meeting_date"], ex["generic_title"]), ("lavina", "2026-11-05", True))
        self.assertNotRegex(json.dumps(it, ensure_ascii=False), r"[\w.+-]+@(?!aagrapevine\.org)[\w-]+\.\w+",
                            "no member's e-mail address")

    def test_the_show_is_spanish_although_its_feed_says_english(self):
        f = parsed()
        self.assertEqual(f.feed.get("language"), "en")
        meta = P.show_meta(LVO, f, 1)
        self.assertEqual((meta["language"], meta["feed_language"], meta["weekly_open"]), ("es", "en", "lavina"))
        self.assertEqual((meta["key"], meta["name"], meta["episodes"]), ("lvo", NAME, 1))
        self.assertIsNone(meta["amazon"])
        self.assertEqual(P.show_lang(LVO, f), "es")
        bare = {k: v for k, v in LVO.items() if k != "lang"}
        self.assertEqual((P.show_meta(bare, f, 1)["language"], P.show_lang(bare, f)), ("en", "en"), "without it: the feed's")
        self.assertEqual(P.build_items(bare, f)[0]["lang"], "es", "the episode's own words are Spanish anyway")

    def test_the_next_episodes(self):
        e2 = variant(2, f"{NAME} [Temporada 1, episodio 2]",
                     "En este podcast de La Viña, escucharás la grabación de nuestra reunión abierta de AA en español del "
                     "jueves 12 de noviembre de 2026. Nuestra próxima reunión será el 19 de noviembre de 2026.",
                     "Mon, 16 Nov 2026 00:15:00 -0500")
        e3 = variant(3, f"{NAME} [Temporada 1, episodio 3]", "Esta semana, Paola da la bienvenida a dos miembros de AA.",
                     "Mon, 23 Nov 2026 00:15:00 -0500")
        e4 = variant(4, "Especial de Navidad [Temporada 1, episodio 4]",
                     "Grabación de la reunión del 24 de diciembre de 2026.", "Mon, 28 Dec 2026 00:15:00 -0500")
        items = {i["extra"]["episode"]: i for i in P.build_items(LVO, parsed(e4, e3, e2))}
        self.assertEqual(sorted(items), [1, 2, 3, 4])
        self.assertEqual((items[2]["extra"]["meeting_date"], items[2]["extra"]["generic_title"]), ("2026-11-12", True),
                         "the meeting's date, not the next meeting's")
        self.assertNotIn("meeting_date", items[3]["extra"], "no date: none")
        self.assertTrue(items[3]["extra"]["generic_title"])
        self.assertEqual((items[4]["extra"]["meeting_date"], items[4]["extra"]["generic_title"]), ("2026-12-24", False))
        self.assertTrue(all(i["extra"]["weekly_open"] == "lavina" for i in items.values()))
        # a show that records no meeting gets none of these fields
        gv = P.build_items({"key": "gv", "name": "AA Grapevine's Podcast", "feed": "https://feeds.example/gv/"}, parsed())
        self.assertFalse({"weekly_open", "meeting_date", "generic_title"} & set(gv[0]["extra"]))



class RealSettings(unittest.TestCase):
    """config/site.yml as the committee keeps it (a content test: scripts/ops/gate_tests.py CONTENT_TESTS): the three
    shows as this file's copies have them, La Viña's meeting show and its meeting's page."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        cls.shows = cls.cfg["sources"]["podcasts"]

    def test_the_shows_are_this_files_copies(self):
        self.assertEqual(self.shows, CFG_SHOWS)

    def test_the_config_entry(self):
        keys = [s["key"] for s in self.shows]
        self.assertEqual(keys[:2], ["gv", "wo"], "AA Grapevine's Podcast stays Home's featured show")
        self.assertEqual(len(set(keys)), len(keys))
        lvo = next(s for s in self.shows if s.get("weekly_open") == "lavina")
        self.assertEqual(lvo["key"], "lvo")
        self.assertEqual(lvo["feed"], "https://feeds.captivate.fm/reunin-abierta-semanal/")
        self.assertEqual((lvo["lang"], lvo["web"]), ("es", "https://www.aalavina.org/podcast"))
        self.assertNotIn("amazon", lvo)
        self.assertEqual(next(s for s in self.shows if s["key"] == "wo").get("weekly_open"), "grapevine")
        self.assertTrue(all(s.get("weekly_open") in (None, "grapevine", "lavina") for s in self.shows))

    def test_the_lavina_meetings_page(self):
        lv = self.cfg["lavina_weekly_open"]
        self.assertEqual(lv["url"], LV_MEETING_PAGE)
        for key in ("day", "time", "timezone", "starts"):
            self.assertEqual(lv[key], LV_MEETING_CFG[key], key)


class LaVinaMeetingPage(unittest.TestCase):
    """lavina_weekly_open.url: La Viña's page for its meeting, in the sync's item (and none when the setting is empty)."""

    def test_the_sync_writes_it(self):
        self.assertEqual(W.lavina_item(LV_MEETING_CFG)["url"], LV_MEETING_PAGE)
        self.assertEqual(W.lavina_item({**LV_MEETING_CFG, "url": ""})["url"], "")


class MeetingDate(unittest.TestCase):
    REAL = ("En este podcast de La Viña, escucharás la grabación de nuestra reunión abierta de AA en español del 5 de "
            "noviembre de 2026. Nos reunimos todos los jueves a las 12:00 del mediodía, hora del Este")

    def test_dates(self):
        cases = [
            # (title, description, published, the meeting's date)
            (f"{NAME} [Temporada 1, episodio 1]", self.REAL, "2026-11-09T05:15:00Z", "2026-11-05"),
            ("Grapevine Weekly Open AA Meeting, November 4, 2026 [Season 2 Episode 19]",
             "you'll hear a recording of Grapevine's open AA meeting, held on November 4, 2026.", "2026-11-06T05:15:00Z", "2026-11-04"),
            # the real feed's episode 14: its title says May 6, its description April 29 — the title wins
            ("Grapevine Weekly Open AA Meeting, May 6, 2026 [Season 1, Episode 14]",
             "a recording of Grapevine's open AA meeting, held on April 29, 2026.", "2026-05-08T05:15:00Z", "2026-05-06"),
            ("Introducing The Grapevine Open AA Meeting [Season 1, Episode 1]",
             "Grapevine's first open AA meeting, held on February 4, 2026. We will meet every Wednesday",
             "2026-02-06T05:15:00Z", "2026-02-04"),
            ("", "la reunión abierta del jueves 12 de noviembre de 2026", "2026-11-16T05:15:00Z", "2026-11-12"),
            ("", "Reunión celebrada el 1.º de diciembre del 2026.", "2026-12-07T05:15:00Z", "2026-12-01"),
            ("", "la reunión del primero de enero de 2027", "2027-01-04T05:15:00Z", "2027-01-01"),
            ("", "la reunión del 1ro de enero de 2027", "2027-01-04T05:15:00Z", "2027-01-01"),
            ("", "la reunión del 1er de enero de 2027", "2027-01-04T05:15:00Z", "2027-01-01"),
            ("", "la reunión del 1ero de enero de 2027", "2027-01-04T05:15:00Z", "2027-01-01"),
            ("", "la reunión del 05/11/2026", "2026-11-09T05:15:00Z", None),             # figures: never read
            ("", "la grabación del 5 de nov. de 2026", "2026-11-09T05:15:00Z", "2026-11-05"),
            ("", "the meeting on the 4th of November, 2026", "2026-11-06T05:15:00Z", "2026-11-04"),
            ("", "recorded on Nov. 4th 2026", "2026-11-06T05:15:00Z", "2026-11-04"),
            # the next meeting (after publication) and an anniversary (long before it) are never the meeting's
            ("", "Nos vemos el 19 de noviembre de 2026. Grabación del 12 de noviembre de 2026.", "2026-11-16T05:15:00Z", "2026-11-12"),
            ("", "Aniversario de AA: 10 de junio de 1935. Grabada en vivo el 12 de noviembre de 2026.", "2026-11-16T05:15:00Z", "2026-11-12"),
            # no word says which: the latest one before publication
            ("", "5 de noviembre de 2026 · 29 de octubre de 2026", "2026-11-09T05:15:00Z", "2026-11-05"),
            # without its year: the year that puts it just before publication
            ("", "la reunión abierta del 5 de noviembre", "2026-11-09T05:15:00Z", "2026-11-05"),
            ("", "la reunión abierta del 31 de diciembre", "2027-01-04T05:15:00Z", "2026-12-31"),
            ("", "la reunión abierta del 5 de noviembre", None, None),
            ("", "31 de noviembre de 2026", "2026-12-03T05:15:00Z", None),       # no such day
            ("", "Esta semana, Paola da la bienvenida a dos miembros de AA.", "2026-11-09T05:15:00Z", None),
            ("", "", None, None),
            # no publication date: the first date said to be the meeting's
            ("", "Próxima: 19 de noviembre de 2026. Grabación del 12 de noviembre de 2026.", None, "2026-11-12"),
        ]
        for title, text, pub, want in cases:
            with self.subTest(text=text[:60], pub=pub):
                self.assertEqual(P.meeting_date(title, text, pub), want)


class GenericTitle(unittest.TestCase):
    def test_only_the_shows_name(self):
        wo = "Grapevine Weekly Open AA Meeting"
        for title, names, want in [
            (f"{NAME} [Temporada 1, episodio 1]", (NAME,), True),
            ("REUNION ABIERTA SEMANAL DE ALCOHOLICOS ANONIMOS DE LA VINA (Temporada 2, Episodio 30)", (NAME,), True),
            (NAME, ("Otro nombre", NAME), True),
            ("[Temporada 1, episodio 1]", (NAME,), True),
            ("Grapevine Weekly Open AA Meeting, November 4, 2026 [Season 2 Episode 19]", (wo,), False),
            ("Introducing The Grapevine Open AA Meeting [Season 1, Episode 1]", (wo,), False),
            ("Especial de Navidad [Temporada 1, episodio 4]", (NAME,), False),
            # the numbering written without brackets
            (f"{NAME} - Temporada 1, episodio 2", (NAME,), True),
            (f"{NAME}: Episodio 2", (NAME,), True),
            (f"{NAME} #2", (NAME,), True),
            (f"{NAME} Temporada 1 Episodio 2", (NAME,), True),
            ("Paso 4, ep 4", ("Paso",), False),
        ]:
            with self.subTest(title=title):
                self.assertIs(P.is_generic_title(title, *names), want)

    def test_one_title_for_several_meetings(self):
        # La Viña's titles drift from the show's name: once two episodes share one title, each is as generic as the name
        drift = "Reunión abierta semanal de AA de La Viña"
        e2 = variant(2, f"{drift} [Temporada 1, episodio 2]", "Grabación de la reunión del 12 de noviembre de 2026.",
                     "Mon, 16 Nov 2026 00:15:00 -0500")
        e3 = variant(3, f"{drift} - Temporada 1, episodio 3", "Grabación de la reunión del 19 de noviembre de 2026.",
                     "Mon, 23 Nov 2026 00:15:00 -0500")
        e4 = variant(4, "Especial de Navidad [Temporada 1, episodio 4]", "Grabación de la reunión del 24 de diciembre de 2026.",
                     "Mon, 28 Dec 2026 00:15:00 -0500")
        got = {i["extra"]["episode"]: i["extra"]["generic_title"] for i in P.build_items(LVO, parsed(e4, e3, e2))}
        self.assertEqual(got, {1: True, 2: True, 3: True, 4: False})
        alone = {i["extra"]["episode"]: i["extra"]["generic_title"] for i in P.build_items(LVO, parsed(e4, e2))}
        self.assertEqual(alone, {1: True, 2: False, 4: False}, "one episode of a title is that episode's own title")
        # a show of no meeting: never
        gv = P.build_items({"key": "gv", "name": "AA Grapevine's Podcast", "feed": "https://feeds.example/gv/"},
                           parsed(e3, e2))
        self.assertFalse(any("generic_title" in i["extra"] for i in gv))

    def test_the_three_copies_of_the_numbering_rule(self):
        # scripts/sync/podcasts.py (which titles are generic), media.js and send_digest.py (the title without its
        # numbering, before ", episode N") take off the same unbracketed numbering
        js = re.search(r"const LOOSE_TAIL = /(.*)/i;", (ROOT / "eleventy" / "filters" / "media.js").read_text(encoding="utf-8"))[1]
        self.assertEqual(P._SE_LOOSE_TAIL_RE.pattern, "(?i)" + js)
        self.assertEqual(D.LOOSE_TAIL.pattern, "(?i)" + js)


class BuildData(unittest.TestCase):
    def test_episodes_out_at_the_same_moment_are_in_config_order(self):
        cfg = {"sources": {"podcasts": CFG_SHOWS}}
        at = "2026-11-09T05:15:00Z"                      # Monday 00:15 Eastern: both shows' episodes
        items = [{"id": "pod:gv:aaaaaaaaaaaa", "category": "gv", "date": at},
                 {"id": "pod:lvo:bbbbbbbbbbbb", "category": "lvo", "date": at},
                 {"id": "pod:wo:cccccccccccc", "category": "wo", "date": "2026-11-06T05:15:00Z"},
                 {"id": "pod:gv:dddddddddddd", "category": "gv", "date": "2026-11-02T06:15:00Z"},
                 {"id": "pod:zz:eeeeeeeeeeee", "category": "zz", "date": at}]       # a show no longer in config: last
        self.assertEqual([i["id"] for i in B.sort_newest(items)][:2], ["pod:zz:eeeeeeeeeeee", "pod:lvo:bbbbbbbbbbbb"],
                         "(by id alone, La Viña's would come first every Monday)")
        self.assertEqual([i["id"] for i in B.sort_episodes(items, cfg)],
                         ["pod:gv:aaaaaaaaaaaa", "pod:lvo:bbbbbbbbbbbb", "pod:zz:eeeeeeeeeeee", "pod:wo:cccccccccccc",
                          "pod:gv:dddddddddddd"])

    def test_a_description_with_its_own_translation(self):
        es = "Cada semana grabamos nuestra reunión abierta en línea y creamos este pódcast."
        en = "Each week we record our online open meeting and create this podcast."
        self.assertEqual(B.given_translation(f"{es} ({en})", "es"), (es, en), "La Viña's show")
        self.assertEqual(B.given_translation(f"{en} ({es})", "en"), (en, es))
        for text, src in ((f"{es} ({en})", "en"),                     # (the text is not in the show's language)
                          ("Interviews with AA members from all over (en español)", "en"),
                          ("AA members interview AA members about their sobriety (Season 2)", "en"),
                          (f"{es} (Cada semana grabamos nuestra reunión abierta en línea.)", "es"),
                          (es, "es"), ("", "es")):
            with self.subTest(text=text[:50], src=src):
                self.assertIsNone(B.given_translation(text, src))


class BuildDataRun(unittest.TestCase):
    """build_data.main over a data/raw/podcasts.json as an older sync wrote it: AA Grapevine's Podcast and La Viña's
    meeting out at the same moment, La Viña's show with its feed's "en" and its two-language description."""

    ES = "Cada semana grabamos nuestra reunión abierta en línea y creamos este pódcast."
    EN = "Each week we record our online open meeting and create this podcast."

    def test_episodes_json(self):
        tmp = Path(tempfile.mkdtemp(prefix="gv-r25-build-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        raw, out = tmp / "raw", tmp / "site"
        raw.mkdir()
        gv_show = {"key": "gv", "name": "AA Grapevine's Podcast", "feed": "https://feeds.example/gv/"}
        gv = P.build_items(gv_show, parsed(variant(7, "Off the Pity Pot [Season 11, Episode 19]",
                                                   "Peyton tells Olis and Sam her story.", "Mon, 09 Nov 2026 00:15:00 -0500")))[0]
        [lv] = P.build_items(LVO, parsed())
        self.assertEqual(gv["date"], lv["date"])
        self.assertGreater(lv["id"], gv["id"], "(by id alone, La Viña's would come first)")
        for it in (gv, lv):
            it.update(status="ok", first_seen="2026-11-09T08:00:00Z", last_seen="2026-11-11T08:00:00Z")
        env = {"source": "podcasts", "updated": "2026-11-11T08:00:00Z", "ok": True, "error": None, "stats": {},
               "items": [lv, gv],
               "shows": [{"key": "gv", "name": gv_show["name"], "title": gv_show["name"], "language": "en",
                          "description": "AA members interview AA members about their sobriety and their lives."},
                         {"key": "lvo", "name": NAME, "title": NAME, "language": "en", "weekly_open": "lavina",
                          "description": f"{self.ES} ({self.EN})"}]}
        (raw / "podcasts.json").write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
        real_translator = B.T.Translator
        # the committee's settings, with this file's copies of the shows (see CFG_SHOWS)
        real = common.load_config()
        cfg = {**real, "sources": {**(real.get("sources") or {}), "podcasts": CFG_SHOWS}}
        with mock.patch.object(common, "RAW_DIR", raw), mock.patch.object(B, "RAW_DIR", raw),                 mock.patch.object(B, "load_config", lambda: cfg), \
                mock.patch.object(B, "STATE_DIR", tmp / "state"), \
                mock.patch.object(B.T, "Translator", lambda **kw: real_translator(cache=False, use_model=False)), \
                mock.patch.object(B.T, "_DEFAULT", None):
            self.assertEqual(B.main(["--out", str(out), "--offline", "--no-translate", "--no-prune"]), 0)
        site = json.loads((out / "episodes.json").read_text(encoding="utf-8"))
        self.assertEqual([i["id"] for i in site["items"]], [gv["id"], lv["id"]], "config order: AA Grapevine's first")
        shows = {s["key"]: s for s in site["shows"]}
        self.assertEqual([s["key"] for s in site["shows"]], ["gv", "lvo"])
        self.assertEqual(shows["lvo"]["lang"], "es", "the config's language, not the feed's")
        self.assertEqual(shows["lvo"]["i18n"]["description"], {"es": self.ES, "en": self.EN}, "each language its writer's half")
        self.assertEqual(shows["lvo"]["description"], self.ES)


# ------------------------------------------------------------------------------------------- one show failing
class OneShowFails(unittest.TestCase):
    GV = {"key": "gv", "name": "AA Grapevine's Podcast", "feed": "https://feeds.example/gv/"}
    OLD = "2026-11-01T00:00:00Z"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-r25-pod-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "raw").mkdir()
        (self.tmp / "art").mkdir()
        self.fail_keys: set[str] = set()

        def fetch(_http, url):
            key = "gv" if "feeds.example/gv" in url else "lvo"
            if key in self.fail_keys:
                return None, "HTTP 503"
            if key == "lvo":
                return parsed(), None
            return parsed(variant(7, "Off the Pity Pot [Season 11, Episode 19]", "Peyton tells Olis and Sam her story.",
                                  "Mon, 09 Nov 2026 00:15:00 -0500")), None

        class NoNet:
            def __init__(self, *a, **k):
                pass

            def get(self, *a, **k):
                return None

            head = get

        self._patch(common, "RAW_DIR", self.tmp / "raw")
        self._patch(P, "ART_DIR", self.tmp / "art")
        self._patch(P, "fetch_feed", fetch)
        self._patch(P, "PoliteSession", NoNet)
        self._patch(P, "load_config", lambda: {"sources": {"podcasts": [self.GV, LVO]}})

    def _patch(self, obj, name, value):
        p = mock.patch.object(obj, name, value)
        p.start()
        self.addCleanup(p.stop)

    def run_sync(self, *fail: str) -> dict:
        self.fail_keys = set(fail)
        P.main(["--no-discover"])
        return json.loads((self.tmp / "raw" / "podcasts.json").read_text(encoding="utf-8"))

    def save(self, env: dict) -> None:
        (self.tmp / "raw" / "podcasts.json").write_text(json.dumps(env), encoding="utf-8")

    def age(self, env: dict) -> None:
        """Make the last run look a week and a half old (its times are this second's otherwise)."""
        env["updated"] = self.OLD
        for sh in env["stats"]["shows"].values():
            if sh.get("ok"):
                sh["updated"] = self.OLD
        self.save(env)

    def streak_began(self, env: dict, key: str, when: str) -> None:
        """Make a failing show's streak look older than this second (a run in the same second writes the same time,
        so only an older one shows that the next failing run keeps it rather than starting it again)."""
        env["stats"]["shows"][key]["failing_since"] = when
        self.save(env)

    def test_one_show_failing_never_hides_the_others(self):
        env = self.run_sync()
        self.assertTrue(env["ok"])
        self.assertEqual({k: v["ok"] for k, v in env["stats"]["shows"].items()}, {"gv": True, "lvo": True})
        self.assertNotIn("warnings", env["stats"])
        self.assertEqual(env["stats"]["shows"]["lvo"]["name"], NAME)
        self.age(env)

        env = self.run_sync("lvo")
        self.assertTrue(env["ok"], "the other show still updated")
        self.assertNotEqual(env["updated"], self.OLD, "so the source's time moves on")
        self.assertIsNone(env["error"])
        lvo = env["stats"]["shows"]["lvo"]
        self.assertEqual((lvo["ok"], lvo["error"], lvo["updated"], lvo["episodes"]), (False, "HTTP 503", self.OLD, 1))
        since = lvo["failing_since"]
        self.assertTrue(since > self.OLD)
        self.assertEqual(env["stats"]["warnings"],
                         [f"{NAME} (lvo): HTTP 503 — its 1 episode stays on the site; last read 2026-11-01"])
        self.assertIn("pod:lvo:" + common.short_hash(GUID), [i["id"] for i in env["items"]], "its episode is kept")
        self.assertIn("lvo", [s["key"] for s in env["shows"]], "and its show's details")

        began = "2026-11-03T05:00:00Z"
        self.streak_began(env, "lvo", began)
        env = self.run_sync("lvo")                     # still failing: the same streak, the same last good read
        self.assertEqual((env["stats"]["shows"]["lvo"]["failing_since"], env["stats"]["shows"]["lvo"]["updated"]),
                         (began, self.OLD), "the streak's start is kept (the 7-day alarm counts from it)")
        updated = env["updated"]

        env = self.run_sync("gv", "lvo")               # every show failing: the source failed
        self.assertFalse(env["ok"])
        self.assertEqual(env["updated"], updated)
        self.assertIn(NAME, env["error"])
        self.assertIn("AA Grapevine's Podcast (gv): HTTP 503", env["error"])
        self.assertEqual(len(env["items"]), 3, "every episode is kept (the stand-in gv feed has two)")

        env = self.run_sync()                          # both answer again
        self.assertTrue(env["ok"])
        self.assertEqual({k: v["ok"] for k, v in env["stats"]["shows"].items()}, {"gv": True, "lvo": True})
        self.assertNotIn("failing_since", env["stats"]["shows"]["lvo"])
        self.assertNotIn("warnings", env["stats"])

    def test_a_new_show_that_never_answered(self):
        env = self.run_sync("lvo")
        lvo = env["stats"]["shows"]["lvo"]
        self.assertEqual((lvo["ok"], lvo["updated"], lvo["episodes"]), (False, None, 0))
        self.assertEqual(env["stats"]["warnings"], [f"{NAME} (lvo): HTTP 503 — nothing of it on the site yet; not read yet"])
        # it keeps failing: its streak's start is kept — with no good read at all, the 7-day alarm counts from it
        began = "2026-11-02T05:00:00Z"
        self.streak_began(env, "lvo", began)
        env = self.run_sync("lvo")
        lvo = env["stats"]["shows"]["lvo"]
        self.assertEqual((lvo["ok"], lvo["updated"], lvo["failing_since"]), (False, None, began))
        self.assertTrue(env["ok"], "AA Grapevine's Podcast still updated")


class RunSummaryShows(RunSummary):
    def podcasts(self, lvo: dict, ok: bool = True, updated_days: int = 0) -> dict:
        row = src("podcasts", "Podcasts", ok=ok, stats={"shows": {"gv": {"ok": True, "name": "AA Grapevine's Podcast"},
                                                                    "lvo": {"name": NAME, "error": "HTTP 404", **lvo}}})
        if updated_days:
            row["updated"] = iso(NOW - timedelta(days=updated_days))
        return {"sources": [row]}

    def test_a_failing_show_is_named_on_the_run_page(self):
        text, out = self.summary(self.podcasts({"ok": False, "updated": iso(NOW - timedelta(days=2)),
                                                "failing_since": iso(NOW - timedelta(days=2))}))
        self.assertIn(f"::warning title=Podcasts — {NAME}::HTTP 404 (its episodes are kept; the other shows still "
                      "update) — not read for 2 days", out)
        self.assertNotIn("Not updating for", text, "not yet a week")

    def test_a_week_of_failing_is_a_source_that_stopped(self):
        text, _out = self.summary(self.podcasts({"ok": False, "updated": iso(NOW - timedelta(days=9)),
                                                "failing_since": iso(NOW - timedelta(days=9))}))
        self.assertIn(f"**Not updating for 7+ days:** Podcasts — {NAME}", text)
        text, _out = self.summary(self.podcasts({"ok": False, "updated": None, "failing_since": iso(NOW - timedelta(days=8))}))
        self.assertIn(f"Podcasts — {NAME}", text, "a show never read yet counts from its first failure")

    def test_a_source_that_failed_is_named_once(self):
        text, _out = self.summary(self.podcasts({"ok": False, "updated": iso(NOW - timedelta(days=9))}, ok=False,
                                                updated_days=9))
        line = next(ln for ln in text.splitlines() if ln.startswith("**Not updating for"))
        self.assertIn("Podcasts", line)
        self.assertNotIn(NAME, line)

    def test_one_bad_run_of_every_show_keeps_a_week_old_failure(self):
        # La Viña's feed has failed for 9 days; today every feed failed once (one host): the source failed, but its
        # own last good read was yesterday — the show still counts, so the report issue is not closed for a day
        st = self.podcasts({"ok": False, "updated": iso(NOW - timedelta(days=9)), "failing_since": iso(NOW - timedelta(days=9))},
                           ok=False, updated_days=1)
        st["sources"][0]["stats"]["shows"]["gv"] = {"ok": False, "name": "AA Grapevine's Podcast", "error": "HTTP 503",
                                                    "updated": iso(NOW - timedelta(days=1))}
        text, out = self.summary(st)
        self.assertIn("**Not updating for 7+ days:**", text, "(the issue would close for a day, and reopen tomorrow)")
        line = next(ln for ln in text.splitlines() if ln.startswith("**Not updating for"))
        self.assertIn(f"Podcasts — {NAME}", line)
        self.assertNotIn("AA Grapevine's Podcast", line, "a day is not a week")
        self.assertNotIn("the other shows still update", out, "they did not, this time: the source's own warning says so")

    def test_the_report_issue_says_what_to_do(self):
        wf = yaml.safe_load((ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8"))
        step = next(s for s in wf["jobs"]["report"]["steps"] if s.get("name") == "Open, update or close the report issue")
        code = step["run"].split("<<'PY'\n", 1)[1]
        part = code[code.index("HINTS = {"):code.index("def gh(")]
        ns: dict = {}
        exec(part, ns)                                                      # noqa: S102 — the workflow's own code
        self.assertTrue(ns["hint"]("podcasts:lvo").startswith("the show's feed no longer answers"))
        self.assertIn("sources.podcasts", ns["hint"]("podcasts:lvo"))
        self.assertTrue(ns["hint"]("drive").startswith("check that the committee folder"))
        self.assertTrue(ns["hint"]("podcasts").startswith("the other website may have changed"))


# ------------------------------------------------------------------------------------------- the pages' filters
def episode(iid, show, title, date_, lang="en", es=None, en=None, **extra):
    return {"id": iid, "source": "podcast", "kind": "episode", "url": f"https://player.captivate.fm/episode/{iid}",
            "title": title, "summary": "", "lang": lang, "date": date_, "category": show, "status": "ok",
            "extra": {"show": show, "audio_url": f"https://episodes.captivate.fm/{iid}.mp3", "duration_sec": 3300, **extra},
            "i18n": {"title": {"en": en or title, "es": es or title}}}


LV_EP = episode("pod:lvo:667729784075", "lvo", f"{NAME} [Temporada 1, Episodio 1]", "2026-11-09T05:15:00Z", lang="es",
                en="La Viña Weekly Open Meeting of Alcoholics Anonymous [Season 1, Episode 1]",
                show_name=NAME, season=1, episode=1, weekly_open="lavina", meeting_date="2026-11-05", generic_title=True)
WO_EP = episode("pod:wo:aaaaaaaaaaaa", "wo", "Grapevine Weekly Open AA Meeting, November 4, 2026 [Season 2 Episode 19]",
                "2026-11-06T05:15:00Z", es="Grapevine Weekly Open AA Meeting, 4 de noviembre de 2026 [Temporada 2 Episodio 19]",
                show_name="Grapevine Weekly Open AA Meeting", season=2, episode=19, weekly_open="grapevine",
                meeting_date="2026-11-04", generic_title=False)
# AA Grapevine's Podcast: its newest episode came out at the same moment as La Viña's (Mondays 00:15 Eastern)
GV_EPS = [episode(f"pod:gv:{n:012d}", "gv", f"Story {n} [Season 11, Episode {n}]", f"2026-11-0{n}T05:15:00Z",
                  show_name="AA Grapevine's Podcast", season=11, episode=n) for n in (2, 9)]
EPISODES = {
    "updated": "2026-11-11T15:00:00Z",
    "shows": [  # as build_data writes them; La Viña's as an older sync wrote it (the feed's "en")
        {"key": "gv", "name": "AA Grapevine's Podcast", "language": "en", "lang": "en", "episodes": 2,
         "i18n": {"description": {"en": "AA members interview AA members.", "es": "Miembros de AA entrevistan a miembros de AA."}}},
        {"key": "wo", "name": "Grapevine Weekly Open AA Meeting", "language": "en", "lang": "en", "episodes": 1,
         "i18n": {"description": {"en": "Each week AA Grapevine holds an open meeting.", "es": "Cada semana AA Grapevine celebra una reunión abierta."}}},
        {"key": "lvo", "name": NAME, "language": "en", "lang": "en", "episodes": 1,
         "i18n": {"description": {"en": "Each week we record our online open meeting and create this podcast.",
                                  "es": "Cada semana grabamos nuestra reunión abierta en línea y creamos este pódcast."}}},
    ],
    "items": [LV_EP, WO_EP, *GV_EPS],
}
WEEKLY = [
    {"id": "weekly_open", "source": "grapevine", "kind": "meeting", "lang": "en", "status": "ok", "title": "Grapevine Weekly Open AA Meeting",
     "extra": {"weekday": "wednesday", "zoom_id": "834 5678 9012", "passcode": "975310", "next_start": "2026-11-11T17:00:00Z",
               "start_local": "12:00", "timezone": "America/New_York", "time_central": "11 AM Central"},
     "i18n": {"title": {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"},
              "day": {"en": "Wednesdays", "es": "Miércoles"}}},
    {"id": "weekly_open_lv", "source": "lavina", "kind": "meeting", "lang": "es", "status": "ok", "title": "Reunión Abierta de La Viña",
     "url": LV_MEETING_PAGE, "extra": {"weekday": "thursday", "zoom_id": "834 5678 9012", "passcode": "975310", "next_start": "2026-11-12T17:00:00Z",
               "start_local": "12:00", "timezone": "America/New_York", "time_central": "11 AM Central", "starts": "2026-11-05"},
     "i18n": {"title": {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"},
              "day": {"en": "Thursdays", "es": "Jueves"}}},
]
NOW_JS = "2026-11-11T18:00:00Z"


class Display(unittest.TestCase):
    r: dict | None = None

    def setUp(self):
        if Display.r is None:
            Display.r = run_js(self, r"""
              const media = await imp("eleventy/filters/media.js");
              const { statusView } = await imp("eleventy/filters/community.js");
              const eps = filters.mediaItems(input.episodes, "episodes");
              const by = {};
              for (const e of eps) by[e.extra.show] ??= e;      // each show's newest
              const res = { titles: {}, shows: {}, days: {}, labels: {}, labelLangs: {}, meetingShow: {}, dated: {}, order: {} };
              for (const L of ["en", "es"]) {
                res.titles[L] = Object.fromEntries(Object.entries(by).map(([k, e]) => [k, filters.mediaTitle(e, L)]));
                res.titles[L].share = filters.mediaOrigTitle(by.lvo, L);
                const noDate = { ...by.lvo, extra: { ...by.lvo.extra, meeting_date: "" } };
                res.titles[L].noDate = filters.mediaTitle(noDate, L);
                res.titles[L].ownTitle = filters.mediaTitle({ ...by.lvo, extra: { ...by.lvo.extra, generic_title: false } }, L);
                // the numbering without brackets: taken off before ", episode N"
                res.titles[L].loose = filters.mediaTitle({ ...noDate, title: input.name + " - Temporada 1, episodio 1",
                  i18n: { title: { es: input.name + " - Temporada 1, episodio 1", en: "La Viña Weekly Open Meeting of Alcoholics Anonymous - Season 1, Episode 1" } } }, L);
                res.dated[L] = { ...Object.fromEntries(Object.entries(by).map(([k, e]) => [k, filters.mediaTitleDated(e, L)])),
                                 noDate: filters.mediaTitleDated(noDate, L) };
                res.shows[L] = filters.mediaShowList(input.episodes, input.cfg, eps, L)
                  .map((s) => ({ key: s.key, lang: s.lang, meeting: s.meeting, weekly: s.weekly, short: s.short, shortLang: s.shortLang, count: s.count }));
                // the page's order (/listen/'s rows, /episodes-index.json) — one day's episodes in the page's language first
                res.order[L] = { page: filters.mediaEpisodeOrder(eps, input.cfg, L).map((e) => e.id),
                                 index: JSON.parse(filters.mediaIndexJson(input.episodes ? { episodes: input.episodes } : {}, "episodes", L, input.cfg)).items.map((e) => e.id) };
                res.days[L] = { gv: filters.mediaWeeklyDays(input.weekly, L, "grapevine"), lv: filters.mediaWeeklyDays(input.weekly, L, "lavina") };
                const vid = (cat, lang, title) => ({ id: "yt:x", kind: "video", category: cat, lang, title, extra: { video_id: "abcdefghijk", playlists: [] } });
                res.labels[L] = [vid("lv", "es", "Reunión abierta semanal de Alcohólicos Anónimos de La Viña [Temporada 1, Episodio 1]"),
                                 vid("gv", "en", "Grapevine Weekly Open AA Meeting, October 28, 2026 [Season 2, Episode 18]"),
                                 vid("gv", "en", "Sober Insurance")].map((v) => filters.mediaMeetingLabel(v, L));
                res.labelLangs[L] = [vid("lv", "es", "Reunión abierta semanal de Alcohólicos Anónimos de La Viña [Temporada 1, Episodio 1]"),
                                     vid("gv", "en", "Grapevine Weekly Open AA Meeting, October 28, 2026 [Season 2, Episode 18]"),
                                     vid("gv", "en", "Sober Insurance")].map((v) => filters.mediaMeetingLang(v, L));
              }
              res.meetingShow = { lavina: filters.mediaMeetingShow(input.cfg, "lavina"), grapevine: filters.mediaMeetingShow(input.cfg, "grapevine"),
                                  none: filters.mediaMeetingShow(input.cfg, "other"),
                                  withEps: filters.mediaMeetingShow(input.cfg, "lavina", input.episodes),
                                  noEpsYet: filters.mediaMeetingShow(input.cfg, "lavina", { ...input.episodes, items: input.episodes.items.filter((i) => i.category !== "lvo") }),
                                  noFile: filters.mediaMeetingShow(input.cfg, "grapevine", {}) };
              res.parts = { lvo: media.meetingTitleParts(by.lvo), wo: media.meetingTitleParts(by.wo) };
              // a show's language, whatever an episode's own words were detected as (What's New marks the show's name)
              const sl = (e) => filters.mediaShowLang(e, input.cfg, input.episodes);
              res.showLang = { lvoWordsEn: sl({ ...by.lvo, lang: "en" }), gvWordsEs: sl({ ...by.gv, lang: "es" }), wo: sl(by.wo),
                               unknown: sl({ id: "pod:zz:1", kind: "episode", category: "zz", lang: "es", extra: { show: "zz" } }) };
              const v = { id: "yt:49LzrLRT4k0", kind: "video", category: "lv", lang: "es", status: "ok", date: "2026-11-09T14:31:49Z",
                          title: "Reunión abierta semanal de Alcohólicos Anónimos de La Viña [Temporada 1, Episodio 1]",
                          extra: { video_id: "49LzrLRT4k0", playlists: [] } };
              res.video = JSON.parse(filters.mediaInitialJson([v], "videos", "en", [])).items[0];
              const st = (ok) => ({ sources: [{ source: "podcasts", ok, updated: "2026-11-11T15:00:00Z",
                                    stats: { shows: { gv: { ok: true }, lvo: { ok: false, name: input.name, updated: "2026-11-02T15:00:00Z" } } } }] });
              res.status = { ok: statusView(st(true)).sources[0].partsDown, failed: statusView(st(false)).sources[0].partsDown };
              out(res);""", data={"episodes": EPISODES, "cfg": CFG_SHOWS, "weekly": WEEKLY, "name": NAME}, now=NOW_JS)

    def test_la_vinas_episode_is_called_by_its_meetings_date(self):
        t = self.r["titles"]
        self.assertEqual((t["en"]["lvo"], t["es"]["lvo"]), ("Meeting of November 5, 2026", "Reunión del 5 de noviembre de 2026"))
        self.assertEqual((t["en"]["share"], t["es"]["share"]), ("Meeting of November 5, 2026", "Reunión del 5 de noviembre de 2026"),
                         "the site's own words: its Share sends them in the page's language")
        self.assertEqual(t["es"]["noDate"], f"{NAME}, episodio 1")
        self.assertEqual(t["en"]["noDate"], "La Viña Weekly Open Meeting of Alcoholics Anonymous, episode 1")
        self.assertEqual(t["en"]["ownTitle"], "La Viña Weekly Open Meeting of Alcoholics Anonymous", "a title of its own stays")
        self.assertEqual((t["es"]["loose"], t["en"]["loose"]),
                         (f"{NAME}, episodio 1", "La Viña Weekly Open Meeting of Alcoholics Anonymous, episode 1"),
                         "the numbering without brackets is not said twice")
        # as before: the Grapevine Weekly Open's and the podcast's
        self.assertEqual((t["en"]["wo"], t["es"]["wo"]), ("Meeting of November 4, 2026", "Reunión del 4 de noviembre de 2026"))
        self.assertEqual(t["en"]["gv"], "Story 9")

    def test_the_shows(self):
        en = {s["key"]: s for s in self.r["shows"]["en"]}
        self.assertEqual([s["key"] for s in self.r["shows"]["en"]], ["gv", "wo", "lvo"], "config order")
        self.assertEqual((en["lvo"]["lang"], en["lvo"]["meeting"], en["lvo"]["weekly"], en["lvo"]["count"]), ("es", "lavina", True, 1),
                         "the config's language, whatever an older sync wrote")
        self.assertEqual((en["wo"]["lang"], en["wo"]["meeting"], en["wo"]["weekly"]), ("en", "grapevine", True))
        self.assertEqual((en["gv"]["meeting"], en["gv"]["weekly"], en["gv"]["short"]), ("", False, "AA Grapevine's Podcast"))
        es = {s["key"]: s for s in self.r["shows"]["es"]}
        self.assertEqual((en["lvo"]["short"], es["lvo"]["short"]), ("La Viña Open Meeting", "Reunión Abierta de La Viña"))
        self.assertEqual((en["wo"]["short"], es["wo"]["short"]), ("Grapevine Weekly Open", "Grapevine Weekly Open"))

    def test_each_meeting_its_own_day(self):
        self.assertEqual(self.r["days"]["en"], {"gv": "Wednesdays", "lv": "Thursdays"})
        self.assertEqual(self.r["days"]["es"], {"gv": "miércoles", "lv": "jueves"})

    def test_a_weekly_videos_badge(self):
        self.assertEqual(self.r["labels"]["en"], ["La Viña Open Meeting", "Grapevine Weekly Open", ""])
        self.assertEqual(self.r["labels"]["es"], ["Reunión Abierta de La Viña", "Grapevine Weekly Open", ""])
        self.assertEqual((self.r["video"]["k"], self.r["video"].get("w")), ("weekly", "lv"), "Watch's list: its own badge")

    def test_the_show_that_records_a_meeting(self):
        self.assertEqual(self.r["meetingShow"], {"lavina": "lvo", "grapevine": "wo", "none": "", "withEps": "lvo",
                                                 "noEpsYet": "", "noFile": ""},
                         "with the episodes: only a show that has one (/listen/ filters only by a show it lists)")

    def test_which_titles_name_the_meetings_date(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertEqual(self.r["dated"][lang], {"lvo": True, "wo": True, "gv": False, "noDate": False},
                                 "Home leaves the date out only where the title names it")

    def test_one_days_episodes_in_the_pages_language_first(self):
        # AA Grapevine's Podcast and La Viña's meeting came out at the same moment (Monday 00:15 Eastern)
        gv, lvo = "pod:gv:000000000009", "pod:lvo:667729784075"
        for lang, first in (("en", [gv, lvo]), ("es", [lvo, gv])):
            with self.subTest(lang=lang):
                self.assertEqual(self.r["order"][lang]["page"][:2], first)
                self.assertEqual(self.r["order"][lang]["index"], self.r["order"][lang]["page"],
                                 "/episodes-index.json in the same order as the page's own rows")
                self.assertEqual(self.r["order"][lang]["page"][2:], ["pod:wo:aaaaaaaaaaaa", "pod:gv:000000000002"])

    def test_the_labels_language(self):
        en = {s["key"]: s["shortLang"] for s in self.r["shows"]["en"]}
        es = {s["key"]: s["shortLang"] for s in self.r["shows"]["es"]}
        self.assertEqual(en, {"gv": "en", "wo": "en", "lvo": "en"})
        self.assertEqual(es, {"gv": "en", "wo": "en", "lvo": "es"}, "the Grapevine Weekly Open's name stays English on /es/")
        self.assertEqual(self.r["labelLangs"], {"en": ["", "", ""], "es": ["", "en", ""]})

    def test_the_feeds_and_the_searchs_title(self):
        self.assertEqual(self.r["parts"], {"lvo": {"label": "media.show_short_weekly_lv", "date": "2026-11-05"}, "wo": None})

    def test_a_shows_language(self):
        self.assertEqual(self.r["showLang"], {"lvoWordsEn": "es", "gvWordsEs": "en", "wo": "en", "unknown": "es"},
                         "the config's, else episodes.json's, else (a show nobody lists) the episode's")

    def test_a_failing_show_on_the_status_page(self):
        self.assertEqual(self.r["status"]["ok"], [{"key": "lvo", "name": NAME, "updated": "2026-11-02T15:00:00Z"}])
        self.assertEqual(self.r["status"]["failed"], [], "a failed source says so itself")


# ------------------------------------------------------------------------------------------- the pages
PAGES_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r25-listen-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        // this file's copies of the shows, not the committee's config/site.yml (see CFG_SHOWS)
        site: (data) => ({ ...data.site, sources: { ...data.site.sources, podcasts: input.cfg } }),
        db: (data) => ({ ...data.db, episodes: input.episodes, weekly_open: { updated: "2026-11-11T12:00:00Z", items: input.weekly },
                         ...(input.whatsnew ? { whatsnew: { updated: "2026-11-11T12:00:00Z", items: input.whatsnew } } : {}) }),
      });
    },
  });
  const pages = await elev.toJSON();
  const want = new Set(input.urls);
  out(Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def visible(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", " ", h, flags=re.S))).strip()


class Pages(unittest.TestCase):
    built: dict | None = None
    T = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        T.update(json.loads(f.read_text(encoding="utf-8")))

    # What's New and the RSS feed (db.whatsnew): La Viña's episode, the Grapevine Weekly Open's, and an AA Grapevine's
    # Podcast episode whose words the sync took for Spanish (its show's name stays English)
    GV_WORDS_ES = {**GV_EPS[1], "id": "pod:gv:000000000099", "lang": "es"}
    WHATSNEW = [LV_EP, WO_EP, GV_WORDS_ES]

    def setUp(self):
        if Pages.built is None:
            urls = [pre + p for p in ("", "listen/", "meetings/", "whats-new/", "feed.xml", "search-index.json")
                    for pre in ("/", "/es/")]
            Pages.built = run_js(self, PAGES_JS, data={"only": "index.njk,listen.njk,meetings.njk,whats-new,feed,search-index",
                                                       "urls": urls, "episodes": EPISODES, "weekly": WEEKLY,
                                                       "whatsnew": self.WHATSNEW, "cfg": CFG_SHOWS},
                                  timeout=600, now=NOW_JS)

    def cards(self, lang: str) -> dict[str, str]:
        page = self.built["/es/listen/" if lang == "es" else "/listen/"]
        return {m.group(2): m.group(0) for m in
                re.finditer(r'<article class="card show-card ([^"]*)" aria-labelledby="show-(\w+)-title".*?</article>', page, re.S)}

    def test_three_show_cards(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                cards = self.cards(lang)
                self.assertEqual(list(cards), ["gv", "wo", "lvo"])
                self.assertIn("lg:col-span-2", cards["gv"].split(">", 1)[0], "the first across the row from 1024px")
                for k in ("wo", "lvo"):
                    self.assertNotIn("lg:col-span-2", cards[k].split(">", 1)[0], "the two meetings side by side")
                self.assertIn("is-weekly is-lv", cards["lvo"].split(">", 1)[0])
                one = self.T["media.show_episodes_one"][lang]
                # "1 episode", never "1 episodes" / "1 episodios" (assertIn alone would take those too)
                self.assertRegex(visible(cards["lvo"]), re.escape(one) + r"(?![\w])", "the singular form")
                # a show name in the other language keeps its lang attribute on the show chips
                chip = re.search(r'<span lang="(\w+)">' + re.escape(html.escape(NAME, quote=False)) + "</span>",
                                 self.built[("/es" if lang == "es" else "") + "/listen/"])
                if lang == "en":
                    self.assertIsNotNone(chip, "La Viña's show name is marked Spanish on /listen/")
                    self.assertEqual(chip.group(1), "es")

    def test_each_meeting_card_says_its_day_language_and_name(self):
        want = {"en": {"wo": ("Live on Zoom: Wednesdays", "In English", "How to join: Grapevine Weekly Open AA Meeting"),
                       "lvo": ("Live on Zoom: Thursdays", "In Spanish", "How to join: La Viña Open Meeting (in Spanish)")},
                "es": {"wo": ("En vivo por Zoom: miércoles", "En inglés", "Cómo unirse: Grapevine Weekly Open AA Meeting"),
                       "lvo": ("En vivo por Zoom: jueves", "En español", "Cómo unirse: Reunión Abierta de La Viña")}}
        for lang in ("en", "es"):
            cards = self.cards(lang)
            for k, (live, language, join) in want[lang].items():
                with self.subTest(lang=lang, show=k):
                    words = visible(cards[k])
                    self.assertIn(live, words)
                    self.assertIn(self.T["media.kind_meeting"][lang], words)
                    self.assertIn(language, words)
                    self.assertIn(f'aria-label="{join}"', cards[k])
                    self.assertIn('href="' + ("/es" if lang == "es" else "") + '/meetings/#weekly-open"', cards[k])
            self.assertNotIn("Live on Zoom", visible(cards["gv"]))
        self.assertIn(f'lang="es">{NAME}</h3>', self.cards("en")["lvo"], "a Spanish name on the English page")
        self.assertNotIn('lang="es"', re.search(r"<h3.*?</h3>", self.cards("es")["lvo"], re.S).group(0))
        self.assertIn('lang="en">AA Grapevine', self.cards("es")["gv"])

    def test_the_episode_rows_and_the_language_note(self):
        for lang, title, badge in (("en", "Meeting of November 5, 2026", "La Viña Open Meeting"),
                                   ("es", "Reunión del 5 de noviembre de 2026", "Reunión Abierta de La Viña")):
            with self.subTest(lang=lang):
                page = self.built["/es/listen/" if lang == "es" else "/listen/"]
                i = page.index('data-ep="pod:lvo:667729784075"')
                row = page[i:page.index("</li>", i)]
                self.assertIn(title, visible(row))
                self.assertIn(badge, visible(row))
                self.assertIn(self.T["media.mixed_audio_note"][lang], page)
                self.assertNotIn(self.T["media.english_audio_note"]["es"], page)

    def test_meetings_links_each_meetings_episodes(self):
        for lang in ("en", "es"):
            pre = "/es" if lang == "es" else ""
            with self.subTest(lang=lang):
                page = self.built[pre + "/meetings/"]
                self.assertIn(f'href="{pre}/listen/?show=lvo#episodes"', page)
                self.assertIn(f'href="{pre}/listen/?show=wo#episodes"', page)
                name = "La Viña Open Meeting (in Spanish)" if lang == "en" else "Reunión Abierta de La Viña"
                self.assertIn('aria-label="' + self.T["committee.weekly.listen_name"][lang].replace("{name}", name) + '"', page)

    def test_la_vinas_card_links_its_page(self):
        # the La Viña card's "Details on aalavina.org" opens its meeting's page, in both languages
        for lang, words in (("en", "Details on "), ("es", "Detalles en ")):
            pre = "/es" if lang == "es" else ""
            with self.subTest(lang=lang):
                page = self.built[pre + "/meetings/"]
                i = page.index(f'href="{LV_MEETING_PAGE}"')
                self.assertIn(words, visible(page[i:page.index("</a>", i)]))

    def test_home_names_la_vinas_meeting(self):
        for lang, label, title in (("en", "La Viña Open Meeting", "Meeting of November 5, 2026"),
                                   ("es", "Reunión Abierta de La Viña", "Reunión del 5 de noviembre de 2026")):
            with self.subTest(lang=lang):
                page = self.built["/es/" if lang == "es" else "/"]
                i = page.index('data-id="pod:lvo:667729784075"')
                li = page[page.rindex("<li", 0, i):i]
                self.assertIn(label, visible(li))
                self.assertIn(title, visible(li))

    def test_the_latest_episode_on_a_monday(self):
        # AA Grapevine's Podcast and La Viña's meeting came out at the same moment: each page features its own language's
        for lang, want_id, want in (("en", "pod:gv:000000000009", "Story 9"),
                                    ("es", "pod:lvo:667729784075", "Reunión del 5 de noviembre de 2026")):
            with self.subTest(lang=lang):
                page = self.built["/es/listen/" if lang == "es" else "/listen/"]
                h2 = re.search(r'<h2 id="featured-ep-title"[^>]*>(.*?)</h2>', page, re.S).group(1)
                self.assertEqual(visible(re.search(r'<span x-show="!alt">(.*?)</span>', h2, re.S).group(1)), want)
                initial = json.loads(re.search(r'<script type="application/json" id="media-initial">(.*?)</script>', page, re.S).group(1))
                self.assertEqual(initial["items"][0]["id"], want_id, "the player's epAt(0) is the same episode")
                rows = page[page.index('<section id="episodes"'):]
                self.assertEqual(re.search(r'data-ep="(pod:[^"]+)"', rows).group(1), want_id, "and the episode list starts with it")

    def test_home_says_an_episodes_language(self):
        def row(lang: str, iid: str) -> str:
            page = self.built["/es/" if lang == "es" else "/"]
            i = page.index(f'data-id="{iid}"')
            return page[page.rindex("<li", 0, i):i]
        pill = r'<span class="badge-muted uppercase"[^>]*>{}</span>'
        self.assertRegex(row("en", "pod:lvo:667729784075"), pill.format("es"), "La Viña's Spanish meeting on English Home")
        self.assertRegex(row("es", "pod:wo:aaaaaaaaaaaa"), pill.format("en"), "the English meeting on Spanish Home")
        self.assertIn('lang="en">Grapevine Weekly Open</p>', row("es", "pod:wo:aaaaaaaaaaaa"), "its English name, marked")
        self.assertNotIn("badge-muted", row("en", "pod:gv:000000000002"), "an English episode on English Home: none")
        self.assertNotIn("badge-muted", row("es", "pod:lvo:667729784075"))
        # the featured episode (AA Grapevine's Podcast, English): its language on Spanish Home only
        for lang, has in (("en", False), ("es", True)):
            page = self.built["/es/" if lang == "es" else "/"]
            head = page[page.index('class="home-episode'):page.index('id="ep-title"')]
            self.assertEqual(bool(re.search(pill.format("en"), head)), has, lang)
        # a row whose title names the meeting's date has no date of its own; the others keep theirs (HomeDates)
        self.assertNotIn("Nov", visible(row("en", "pod:lvo:667729784075")).replace("November 5, 2026", ""))
        self.assertIn("Nov ", visible(row("en", "pod:gv:000000000002")))

    def test_home_says_both_meetings_are_open(self):
        self.assertIn("por Zoom, abiertas a todos", self.built["/es/"], "two meetings: «abiertas»")
        self.assertNotIn("abierta a todos", self.built["/es/"])
        self.assertIn("on Zoom, open to everyone", self.built["/"])

    def test_the_feed_and_the_search_call_la_vinas_episode_by_its_meeting(self):
        for lang, want in (("en", "La Viña Open Meeting, November 5, 2026"), ("es", "Reunión Abierta de La Viña, 5 de noviembre de 2026")):
            pre = "/es" if lang == "es" else ""
            with self.subTest(lang=lang):
                self.assertIn(f"<title>{want}</title>", self.built[pre + "/feed.xml"])
                index = json.loads(self.built[pre + "/search-index.json"])
                entry = next(i for i in index["items"] if i.get("id") == "pod:lvo:667729784075")
                self.assertEqual(entry["t"], want)
                self.assertEqual(entry["o"], LV_EP["title"], "the original title stays searchable")

    def test_the_search_describes_all_three_shows(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                index = json.loads(self.built[("/es" if lang == "es" else "") + "/search-index.json"])
                page = next(i for i in index["items"] if i.get("id") == "page:listen")
                self.assertIn("AA Grapevine", page["s"])
                self.assertIn("La Viña", page["s"])
                self.assertIn("(en inglés)" if lang == "es" else "(in Spanish)", page["s"])

    def test_whats_new_marks_a_shows_name_in_its_own_language(self):
        def labels(url: str) -> dict[str, str]:
            spans = re.findall(r'<span class="min-w-0 whitespace-normal!"(?: lang="(\w+)")?>([^<]*)</span>', self.built[url])
            return {html.unescape(name): lang_ for lang_, name in spans}
        self.assertEqual(labels("/whats-new/"), {NAME: "es", "AA Grapevine's Podcast": "", "Grapevine Weekly Open AA Meeting": ""},
                         "an AA Grapevine's Podcast episode whose words looked Spanish: its show's name is still English")
        self.assertEqual(labels("/es/whats-new/"), {NAME: "", "AA Grapevine's Podcast": "en", "Grapevine Weekly Open AA Meeting": "en"})

    def test_the_announcement_says_each_shows_language(self):
        def quote(url: str) -> str:
            return visible(html.unescape(re.search(r'<blockquote[^>]*>(.*?)</blockquote>', self.built[url], re.S).group(1)))
        en, es = quote("/listen/"), quote("/es/listen/")
        self.assertIn(f"{NAME} (in Spanish)", en)
        self.assertIn("AA Grapevine's Podcast, Grapevine Weekly Open AA Meeting,", en, "English names on the English page: no label")
        self.assertIn("AA Grapevine's Podcast (en inglés), Grapevine Weekly Open AA Meeting (en inglés) y " + NAME + ".", es)


class HomeDates(unittest.TestCase):
    """Home's Listen & Watch built with two meeting episodes whose titles do not name the meeting's date: La Viña's with
    no date found ("…, episode 1") — the featured one, AA Grapevine's Podcast's newest being over a month older — and
    the Grapevine Weekly Open's first ("Introducing …") in "More episodes". Both keep their date."""
    built: dict | None = None
    LV_NO_DATE = {**LV_EP, "extra": {k: v for k, v in LV_EP["extra"].items() if k != "meeting_date"}}
    WO_INTRO = episode("pod:wo:bbbbbbbbbbbb", "wo", "Introducing The Grapevine Open AA Meeting [Season 1, Episode 1]",
                       "2026-02-06T05:15:00Z", show_name="Grapevine Weekly Open AA Meeting", season=1, episode=1,
                       weekly_open="grapevine", meeting_date="2026-02-04", generic_title=False)
    GV_OLD = [episode(f"pod:gv:{n:012d}", "gv", f"Story {n} [Season 11, Episode {n}]", f"2026-09-0{n}T05:15:00Z",
                      show_name="AA Grapevine's Podcast", season=11, episode=n) for n in (2, 9)]

    def setUp(self):
        if HomeDates.built is None:
            eps = {**EPISODES, "items": [self.LV_NO_DATE, *self.GV_OLD, self.WO_INTRO]}
            HomeDates.built = run_js(self, PAGES_JS, data={"only": "index.njk", "urls": ["/", "/es/"], "episodes": eps,
                                                           "weekly": WEEKLY, "cfg": CFG_SHOWS}, timeout=600, now=NOW_JS)

    def row(self, lang: str, iid: str) -> str:
        page = self.built["/es/" if lang == "es" else "/"]
        i = page.index(f'data-id="{iid}"')
        return visible(page[page.rindex("<li", 0, i):i])

    def featured(self, lang: str) -> tuple[str, str]:
        page = self.built["/es/" if lang == "es" else "/"]
        title = re.search(r'<h3 id="ep-title"[^>]*>(.*?)</h3>', page, re.S).group(1)
        return visible(title), visible(re.search(r'<p [^>]*x-ref="meta"[^>]*>(.*?)</p>', page, re.S).group(1))

    def test_a_meeting_title_without_its_date_keeps_the_rows_date(self):
        # (the site's days are Central time's: Monday 00:15 Eastern is Sunday evening)
        for lang, lv_title, lv_day, wo_day in (("en", "La Viña Weekly Open Meeting of Alcoholics Anonymous, episode 1",
                                                 "November 8, 2026", "Feb 5"),
                                                ("es", f"{NAME}, episodio 1", "8 de noviembre de 2026", "5 feb")):
            with self.subTest(lang=lang):
                title, meta = self.featured(lang)
                self.assertEqual(title, lv_title, "the newest episode is featured")
                self.assertIn(lv_day, meta, "no date in its title: the featured episode's own")
                wo = self.row(lang, "pod:wo:bbbbbbbbbbbb")
                self.assertIn("Introducing", wo)
                self.assertIn(wo_day, wo, "and a row's")


class EmailTitle(unittest.TestCase):
    ITEM = {"kind": "episode", "lang": "es", "title": f"{NAME} [Temporada 1, episodio 3]",
            "i18n": {"title": {"es": f"{NAME} [Temporada 1, episodio 3]",
                               "en": "La Viña Weekly Open Meeting of Alcoholics Anonymous [Season 1, Episode 3]"}},
            "extra": {"weekly_open": "lavina", "generic_title": True, "episode": 3}}

    def test_a_meeting_episode_in_the_monthly_email(self):
        it = self.ITEM
        self.assertEqual(D.media_title(it, "es"), f"{NAME}, episodio 3", "no date found: its title and number, as on the site")
        self.assertEqual(D.media_title(it, "en"), "La Viña Weekly Open Meeting of Alcoholics Anonymous, episode 3")
        dated = {**it, "extra": {**it["extra"], "meeting_date": "2026-11-19"}}
        self.assertEqual((D.media_title(dated, "es"), D.media_title(dated, "en")),
                         ("Reunión del 19 de noviembre de 2026", "Meeting of November 19, 2026"))
        own = {**it, "extra": {**it["extra"], "generic_title": False}}
        self.assertEqual(D.media_title(own, "es"), NAME, "a title of its own: as before")
        loose = {**it, "i18n": {"title": {"es": f"{NAME} - Temporada 1, episodio 3"}}}
        self.assertEqual(D.media_title(loose, "es"), f"{NAME}, episodio 3", "the numbering without brackets: once")


if __name__ == "__main__":
    unittest.main()
