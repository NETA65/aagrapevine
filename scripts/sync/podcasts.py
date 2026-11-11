"""Podcasts → data/raw/podcasts.json  (AA Grapevine's Podcast, the two weekly open meetings + any show added to config)

Every show listed under `sources.podcasts` in config/site.yml is read from its
public RSS feed (fetched with requests, parsed with feedparser). Another show is
added by adding one more entry to that list:

    - key: "lvo"                     # short id, becomes the item category (never "wo"/"gv"/"lv")
      name: "Reunión abierta semanal de Alcohólicos Anónimos de La Viña"
      feed: "https://…/rss"
      lang: "es"                     # the show's language: wins over the feed's <language> (show metadata)
                                     #   and is the hint for the per-episode language detector
      weekly_open: "lavina"          # optional: the show records this weekly open meeting
                                     #   (data/site/weekly_open.json `source`: "grapevine" | "lavina")
      web / apple / spotify / amazon # optional show links (shown on the site)

Each episode becomes one Item (docs/DATA_SCHEMA.md, kind "episode"). Episodes are
never dropped: if a feed has a bad day the previous episodes stay; an episode that
disappears from a healthy feed is only marked "gone" once its audio file is really
gone (HTTP 404/410).

A weekly open meeting's show (`weekly_open`): each episode gets extra.weekly_open (the meeting),
extra.meeting_date (YYYY-MM-DD: the date in its title, else the meeting's date in its description —
"del 5 de noviembre de 2026", "held on November 4, 2026"; meeting_date()) and extra.generic_title
(true when the title is only the show's name — La Viña's "<show name> [Temporada 1, episodio 1]"):
the site then writes "Meeting of November 5, 2026" / "Reunión del 5 de noviembre de 2026" for it
(eleventy/filters/media.js titleOf), or the title and its episode number when no date is found.

One show whose feed fails does not fail the others: the source stays ok (so its "updated" time
still moves with the other shows' news) and the failing show is named in stats.warnings — the
/status/ page and the run summary show it — and in stats.shows[key] (ok false, its error, `updated`
= its last good read, `failing_since`). The run summary's "stopped updating" check counts a show
failing for 7 days as a source that stopped (.github/workflows/update.yml). Every show failing
fails the source.

Artwork: feeds link full-size cover art (1500–3000 px, ~0.5 MB). Each distinct image is downloaded
once and stored as a ≤480 px WebP in src/assets/cache/pod/; its site path is saved as
`extra.thumb` on episodes and `thumb` on the show metadata (`image` keeps the original URL).

Weekly "discovery": the podcast pages of aagrapevine.org (and the La Viña home
page) are checked — politely, through the shared 5-second-delay bot session — for
podcast feeds that are NOT in the config yet (e.g. a new Spanish show). Nothing is
added automatically; findings are listed in stats.discovered_feeds of data/raw/podcasts.json
(copied to data/site/status.json) so a person can decide to add them to config/site.yml.
A feed that has since been added to the config is dropped from that list on the next run.

Run:  python -m scripts.sync.podcasts [--limit N] [--discover | --no-discover] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser

from .common import (
    CACHE_ASSETS,
    PoliteSession,
    clean_text,
    detect_lang,
    get_logger,
    load_config,
    load_raw,
    make_item,
    merge_items,
    now_iso,
    parse_iso,
    run_module,
    save_raw,
    shared_session,
    short_hash,
    strip_html,
    to_iso,
)

SOURCE = "podcasts"        # data/raw/podcasts.json
ITEM_SOURCE = "podcast"    # Item.source value (docs/DATA_SCHEMA.md)
log = get_logger(SOURCE)

DISCOVERY_EVERY_DAYS = 7
# Local artwork: the feeds link 1500–3000 px originals (~0.5 MB each) that the site shows at
# 56–304 px, so each distinct image is downloaded ONCE and kept as a small WebP (extra.thumb).
ART_DIR = CACHE_ASSETS / "pod"
ART_URL = "/assets/cache/pod/"
ART_MAX_PX = 480
ART_MAX_BYTES = 15 * 1024 * 1024
DISCOVERY_MAX_PAGES = 8        # pages fetched from aagrapevine.org / aalavina.org per discovery
DISCOVERY_MAX_FEEDS = 6        # candidate feeds verified per discovery
GONE_CHECKS_PER_RUN = 10

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_UUID_RE = re.compile(_UUID, re.I)
# Brand names skew the tiny EN/ES word-count detector ("La Viña" in an English title).
_BRANDS_RE = re.compile(r"(?i)\bla\s+vi[ñn]a\b|\bgrapevine(?:'s)?\b|\bgvrs?\b|\brlvs?\b|(?<![\w.])a\.?\s?a\.?(?![\w.])")

# Hosts / URL shapes that are podcast RSS feeds (used by discovery)
_FEED_HOSTS = ("feeds.captivate.fm", "feeds.buzzsprout.com", "feeds.libsyn.com", "feeds.megaphone.fm",
               "feed.podbean.com", "rss.art19.com", "feeds.simplecast.com", "feeds.transistor.fm",
               "anchor.fm", "feeds.acast.com", "rss.buzzsprout.com", "feeds.soundcloud.com",
               "feeds.redcircle.com", "media.rss.com", "feeds.fireside.fm", "rss.com")


# --------------------------------------------------------------------------- parsing helpers
def parse_duration(v: Any) -> int | None:
    """itunes:duration → seconds. Accepts '1938', '32:18', '1:02:03', '1938.4', 'PT32M18S'."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return int(float(s))
    parts = s.split(":")
    if 2 <= len(parts) <= 3 and all(re.fullmatch(r"\d+(?:\.\d+)?", p.strip()) for p in parts):
        secs = 0.0
        for p in parts:
            secs = secs * 60 + float(p)
        return int(secs)
    m = re.fullmatch(r"(?i)P?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", s)
    if m and any(m.groups()):
        return int(int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + float(m[3] or 0))
    return None


def _int_or_str(v: Any) -> int | str | None:
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip()
    return int(s) if s.isdigit() else s


def _struct_to_iso(st: Any) -> str | None:
    try:
        return to_iso(datetime(*st[:6], tzinfo=timezone.utc)) if st else None
    except (TypeError, ValueError):
        return None


def _norm_feed(url: str) -> str:
    """Normalize a feed URL for comparison (scheme/host case, trailing slash)."""
    p = urlparse((url or "").strip())
    host = p.netloc.lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/')}{'?' + p.query if p.query else ''}"


def _explicit(v: Any) -> bool | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("yes", "true", "explicit")


def _lang_text(s: str) -> str:
    return _BRANDS_RE.sub(" ", s or "")


# --------------------------------------------------------------------------- weekly open meetings
# A meeting's date in the words of its title or description: "5 de noviembre de 2026", "1.º de
# diciembre del 2026", "November 4, 2026", "4 November 2026" (abbreviations too: "nov.", "Sept."). A
# date without its year ("del 5 de noviembre") is only used when nothing better is there, with the
# year that puts it closest before the episode's publication.
_MONTHS = {
    "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3, "abril": 4, "abr": 4,
    "mayo": 5, "may": 5, "junio": 6, "jun": 6, "julio": 7, "jul": 7, "agosto": 8, "ago": 8,
    "septiembre": 9, "setiembre": 9, "sept": 9, "sep": 9, "set": 9, "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12,
    "january": 1, "jan": 1, "february": 2, "march": 3, "april": 4, "apr": 4, "june": 6,
    "july": 7, "august": 8, "aug": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "dec": 12,
}
_MON = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DAY_ES = r"(?P<d>\d{1,2}|primero)(?:\s*(?:\.?º|°|\.?o(?![a-zñ])))?"
_DATE_RES = (
    # 5 de noviembre de 2026 · 1.º de diciembre del 2026 · 5 de nov. de 2026 · 5 de noviembre, 2026
    re.compile(rf"(?i)(?<![\w.]){_DAY_ES}\s+de\s+(?P<m>{_MON})\.?(?:\s*,?\s+(?:de\s+|del\s+)?(?P<y>\d{{4}})(?!\d))?(?![a-zñ])"),
    # November 4, 2026 · Nov. 4th 2026 · November 4
    re.compile(rf"(?i)(?<![\w.])(?P<m>{_MON})\.?\s+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?(?!\d)(?:,?\s+(?P<y>\d{{4}})(?!\d))?"),
    # 4 November 2026 · 4th of November, 2026
    re.compile(rf"(?i)(?<![\w.])(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m>{_MON})\.?(?:,?\s+(?P<y>\d{{4}})(?!\d))?(?![a-z])"),
)
# Words just before the date that say it is THIS meeting's: "… reunión abierta de AA en español del 5 de
# noviembre", "held on November 4", "celebrada el jueves 5 de noviembre", "meeting of October 7".
_DATE_CONTEXT_RE = re.compile(
    r"(?i)(?:\bdel|\bcelebrada\s+el|\brealizada\s+el|\bgrabada\s+el|\bheld\s+on|\brecorded\s+on|\bmeeting\s+of|\bmeeting\s+on)"
    r"\s+(?:(?:el\s+)?(?:lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo|monday|tuesday|wednesday|thursday"
    r"|friday|saturday|sunday),?\s+)?$")
MEETING_DATE_BEFORE_DAYS = 60     # a meeting is published within weeks: an older date is something else (an anniversary)


def _date_candidates(text: str) -> list[tuple[int, date, bool, bool]]:
    """(position, date, has its year, said to be the meeting's) for every date written in `text`."""
    out = []
    taken: list[tuple[int, int]] = []
    for rx in _DATE_RES:
        for m in rx.finditer(text or ""):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue                 # (one date matched by two patterns counts once)
            day = 1 if m["d"].lower() == "primero" else int(m["d"])
            month = _MONTHS.get(m["m"].lower().rstrip("."))
            year = int(m["y"]) if m["y"] else None
            if not month:
                continue
            try:
                d = date(year or 2000, month, day)
            except ValueError:
                continue
            taken.append((m.start(), m.end()))
            before = text[max(0, m.start() - 40):m.start()]
            out.append((m.start(), d, year is not None, bool(_DATE_CONTEXT_RE.search(before))))
    return sorted(out)


def meeting_date(title: str, summary: str, published: str | None = None) -> str | None:
    """The date of the meeting an episode records (YYYY-MM-DD), or None.

    The title's own date wins (the Grapevine Weekly Open's "…, November 4, 2026"); else the description's:
    one said to be the meeting's ("del 5 de noviembre de 2026", "held on …") first, else the latest one
    before the episode came out. With a publication date, a date after it (+1 day: time zones) — the next
    meeting — or more than MEETING_DATE_BEFORE_DAYS before it is never the meeting's. A date written
    without its year gets the year that puts it closest before the publication (needs that date)."""
    pub = parse_iso(published).date() if published and parse_iso(published) else None

    def fits(d: date) -> bool:
        return pub is None or (pub - timedelta(days=MEETING_DATE_BEFORE_DAYS) <= d <= pub + timedelta(days=1))

    def with_year(d: date) -> date | None:
        if pub is None:
            return None
        for y in (pub.year, pub.year - 1):
            try:
                c = d.replace(year=y)
            except ValueError:
                continue
            if fits(c):
                return c
        return None

    for text in (title, summary):
        full, yearless = [], []
        for _pos, d, has_year, said in _date_candidates(text):
            if has_year:
                if fits(d):
                    full.append((d, said))
            else:
                c = with_year(d)
                if c:
                    yearless.append((c, said))
        for found in (full, yearless):
            if not found:
                continue
            said = [d for d, s in found if s]
            if said:
                return said[0].isoformat()
            return (max(d for d, _s in found) if pub else found[0][0]).isoformat()
    return None


def _norm_words(s: str) -> str:
    """Letters and digits only, lower case, accents removed — to compare a title with a show's name."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", s))


# The "[Season 1, Episode 2]" / "[Temporada 1, episodio 2]" tail (eleventy/filters/media.js SE_SUFFIX / ONE_SUFFIX).
_SE_TAIL_RE = re.compile(r"(?i)\s*[\[(]\s*(?:(?:season|temporada)\s*\d+\s*[,;.·-]?\s*)?(?:(?:episode|episodio|ep\.?)\s*\d+)?\s*[\])]\s*$")


def is_generic_title(title: str, *names: str) -> bool:
    """True when an episode's title, without its numbering, is only its show's name (or nothing):
    La Viña's "Reunión abierta semanal de Alcohólicos Anónimos de La Viña [Temporada 1, episodio 1]"."""
    bare = _norm_words(_SE_TAIL_RE.sub("", title or ""))
    return not bare or any(bare == _norm_words(n) for n in names if n)


# --------------------------------------------------------------------------- feed → items
def fetch_feed(http: PoliteSession, url: str) -> tuple[Any | None, str | None]:
    """→ (feedparser result, error). A feed must parse and contain at least one entry."""
    r = http.get(url, headers={"Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.5"})
    if r is None:
        return None, "network error"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    f = feedparser.parse(r.content)
    if not f.entries:
        why = f" ({f.bozo_exception})" if getattr(f, "bozo", False) and f.get("bozo_exception") else ""
        return None, f"no episodes in feed{why}"[:200]
    return f, None


def _enclosure(e: Any) -> dict:
    for l in e.get("links") or []:
        if l.get("rel") == "enclosure" and l.get("href"):
            return {"url": l["href"], "type": l.get("type"), "length": l.get("length")}
    for enc in e.get("enclosures") or []:
        if enc.get("href"):
            return {"url": enc["href"], "type": enc.get("type"), "length": enc.get("length")}
    return {}


def _player_url(guid: str, audio_url: str | None) -> str | None:
    """Captivate-hosted shows have a public per-episode page: player.captivate.fm/episode/<uuid>."""
    if audio_url and "captivate.fm" in audio_url:
        m = _UUID_RE.search(audio_url)
        if m:
            return f"https://player.captivate.fm/episode/{m[0].lower()}"
        if _UUID_RE.fullmatch(guid or ""):
            return f"https://player.captivate.fm/episode/{guid.lower()}"
    return None


# Show-level pages of the magazine sites: an episode <link> to one of these is never an episode page.
_GENERIC_PODCAST_PAGES = {"aagrapevine.org/podcast", "aagrapevine.org/podcasts",
                          "aalavina.org/podcast", "aalavina.org/podcasts"}


def shared_link_info(shows: list[dict], feeds: dict[str, Any]) -> tuple[dict[str, int], set[str]]:
    """Episode <link> counts over EVERY fetched feed, and every show's own pages.

    A link that many episodes share is a general page, even when it appears only once in the
    feed of another show (e.g. one Weekly Open episode linking aagrapevine.org/podcast)."""
    counts: dict[str, int] = {}
    generic = set(_GENERIC_PODCAST_PAGES)
    for show in shows:
        generic.update(_norm_feed(u) for u in (show.get("web"), show.get("feed")) if u)
    for f in feeds.values():
        if f is None:
            continue
        if f.feed.get("link"):
            generic.add(_norm_feed(f.feed["link"]))
        for e in f.entries:
            if e.get("link"):
                counts[e["link"]] = counts.get(e["link"], 0) + 1
    return counts, generic


def build_items(show: dict, f: Any, limit: int | None = None, *,
                link_counts: dict[str, int] | None = None, generic_pages: set[str] | None = None) -> list[dict]:
    """Episodes of one show. `link_counts` / `generic_pages` (from shared_link_info) let links
    be judged across all shows; without them only this feed is looked at."""
    key = str(show.get("key") or "gv")
    feed_title = clean_text(f.feed.get("title"))
    show_name = show.get("name") or feed_title or key
    show_web = show.get("web") or f.feed.get("link") or show.get("feed")
    show_img = (f.feed.get("image") or {}).get("href") if isinstance(f.feed.get("image"), dict) else None
    prior = show_lang(show, f)
    # the weekly open meeting this show records ("grapevine" | "lavina"), from config — see the module docstring
    meeting = str(show.get("weekly_open") or "").strip().lower()

    # A per-episode <link> that is the same for many episodes (or is just the show
    # page) is not an episode page — prefer the host's episode page then.
    if link_counts is None:
        link_counts = {}
        for e in f.entries:
            if e.get("link"):
                link_counts[e["link"]] = link_counts.get(e["link"], 0) + 1
    generic = set(_GENERIC_PODCAST_PAGES) | set(generic_pages or ())
    generic |= {_norm_feed(u) for u in (show_web, f.feed.get("link"), show.get("feed")) if u}

    items = []
    for e in f.entries[: limit or None]:
        try:
            title = clean_text(e.get("itunes_title") or e.get("title"))
            if not title:
                continue
            enc = _enclosure(e)
            guid = str(e.get("id") or enc.get("url") or f"{title}|{e.get('published', '')}")
            html_desc = e.get("summary") or ""
            if e.get("content"):
                longest = max((c.get("value") or "" for c in e["content"]), key=len)
                if len(longest) > len(html_desc):
                    html_desc = longest
            summary = strip_html(html_desc)
            link = e.get("link") or ""
            player = _player_url(guid, enc.get("url"))
            is_generic = (not link) or link_counts.get(link, 0) > 1 or _norm_feed(link) in generic
            url = link if not is_generic else (player or link or show_web)
            img = e.get("image")
            image = (img.get("href") if isinstance(img, dict) else None) or show_img
            season = _int_or_str(e.get("itunes_season") or e.get("podcast_season"))
            number = _int_or_str(e.get("itunes_episode") or e.get("podcast_episode"))
            ep_type = str(e.get("itunes_episodetype") or "full").lower()
            lang = detect_lang(_lang_text(title) + " " + _lang_text(summary[:300]), prior)
            if lang not in ("en", "es", "fr"):
                lang = prior
            tags = []
            if isinstance(season, int):
                tags.append(f"season-{season}")
            if ep_type in ("trailer", "bonus"):
                tags.append(ep_type)
            transcript = e.get("podcast_transcript")
            transcript_url = transcript.get("url") if isinstance(transcript, dict) else None
            extra = {
                "audio_url": enc.get("url"),
                "audio_type": enc.get("type"),
                "audio_bytes": int(enc["length"]) if str(enc.get("length") or "").isdigit() and int(enc["length"]) > 0 else None,
                "duration_sec": parse_duration(e.get("itunes_duration")),
                "season": season,
                "episode": number,
                "episode_type": ep_type,
                "show": key,
                "show_name": show_name,
                "link": link or None,
                "player_url": player,
                "explicit": _explicit(e.get("itunes_explicit")),
                "show_web": show.get("web"),
                "apple": show.get("apple"),
                "spotify": show.get("spotify"),
                "amazon": show.get("amazon"),
                "transcript_url": transcript_url,
            }
            published = _struct_to_iso(e.get("published_parsed") or e.get("updated_parsed"))
            if meeting:
                extra["weekly_open"] = meeting
                extra["meeting_date"] = meeting_date(title, summary, published)
                # written either way (false too): a title that later names its date is no longer "generic"
                extra["generic_title"] = is_generic_title(title, show_name, feed_title)
            items.append(make_item(
                id=f"pod:{key}:{short_hash(guid)}", source=ITEM_SOURCE, kind="episode",
                url=url, title=title, summary=summary, lang=lang,
                date=published,
                image=image, tags=tags, category=key,
                extra={k: v for k, v in extra.items() if v is not None},
            ))
        except Exception as ex:  # noqa: BLE001 — one odd episode must not stop the show
            log.warning("[%s] skipped an episode (%s): %s", key, e.get("title", "?")[:60], ex)
    return items


def show_lang(show: dict, f: Any) -> str:
    """The show's language: the config's `lang` first — a feed can say the wrong one (La Viña's Spanish
    open meeting declares <language>en</language>) —, else the feed's own (en/es/fr), else "en"."""
    own = str(show.get("lang") or "").lower()[:2]
    if own in ("en", "es", "fr"):
        return own
    feed_lang = str(f.feed.get("language") or "").lower()[:2]
    return feed_lang if feed_lang in ("en", "es", "fr") else "en"


def show_meta(show: dict, f: Any, count: int) -> dict:
    img = f.feed.get("image")
    feed_lang = str(f.feed.get("language") or "")[:5] or None
    return {
        "key": show.get("key"), "name": show.get("name") or clean_text(f.feed.get("title")),
        "title": clean_text(f.feed.get("title")), "feed": show.get("feed"),
        "description": strip_html(f.feed.get("summary") or f.feed.get("subtitle") or "")[:600],
        "image": img.get("href") if isinstance(img, dict) else None,
        # the config's `lang` wins (show_lang): build_data translates the title and description from it
        "language": str(show.get("lang") or "").lower()[:5] or feed_lang,
        "feed_language": feed_lang,
        "weekly_open": str(show.get("weekly_open") or "").strip().lower() or None,
        "web": show.get("web") or f.feed.get("link"),
        "apple": show.get("apple"), "spotify": show.get("spotify"), "amazon": show.get("amazon"),
        "episodes": count,
    }


# --------------------------------------------------------------------------- discovery
_FOLLOW_RE = re.compile(r"(?i)podcast|listen|esc[uú]ch|episod|variety-hour|weekly-open|audio")
_SKIP_PATH_RE = re.compile(r"(?i)/(store|tienda|cart|carrito|user|login|search|buscar|node/add)\b|\.(pdf|jpe?g|png|gif|mp3|zip)$")


def _page_links(html: str, base: str) -> list[tuple[str, str]]:
    """(absolute url, anchor text) for every href/src/data-src on a page (+ RSS <link>s)."""
    from bs4 import BeautifulSoup  # local import: only needed on discovery runs

    soup = BeautifulSoup(html, "lxml")
    out = []
    for tag in soup.find_all(["a", "iframe", "link", "source", "audio", "embed"]):
        for attr in ("href", "src", "data-src"):
            v = tag.get(attr)
            if v and not str(v).startswith(("mailto:", "tel:", "javascript:", "#")):
                out.append((urljoin(base, str(v).strip()), tag.get_text(" ", strip=True)[:80]))
    # feed URLs sometimes only appear inside scripts / data attributes
    for m in re.finditer(r"https?://[^\s\"'<>\\]+", html):
        u = m.group(0)
        if re.search(r"captivate\.fm|podcasts\.apple\.com|/rss|\.rss|/feed", u):
            out.append((u.rstrip(").,;"), ""))
    return out


def discover(shows: list[dict], sources: dict, max_pages: int = DISCOVERY_MAX_PAGES) -> dict:
    """Look for podcast feeds linked from the official sites that are not in config yet."""
    bot = shared_session()                       # aagrapevine.org / aalavina.org — 5 s crawl-delay, robots.txt
    web = PoliteSession(min_delay=1.0, timeout=20, retries=2)   # captivate.fm, itunes lookup
    bot_hosts = {urlparse(h if "//" in h else "https://" + h).netloc.lower()
                 for h in ((sources.get("crawler") or {}).get("hosts") or ["www.aagrapevine.org", "www.aalavina.org"])}

    hubs: list[str] = []
    for s in shows:
        if s.get("web"):
            hubs.append(s["web"])
    gv_base = ((sources.get("grapevine") or {}).get("base") or "https://www.aagrapevine.org").rstrip("/")
    lv_base = ((sources.get("lavina") or {}).get("base") or "https://www.aalavina.org").rstrip("/")
    hubs += [gv_base + "/podcasts", lv_base + "/"]
    seen_pages: set[str] = set()
    queue: list[tuple[str, int]] = []
    for h in hubs:
        if h not in [q[0] for q in queue]:
            queue.append((h, 0))

    feeds: dict[str, dict] = {}          # normalized → {"feed", "found_on", links…}
    captivate_shows: dict[str, str] = {}  # uuid → page
    apple_ids: dict[str, str] = {}        # id → page
    pages_ok = 0

    def add_feed(url: str, page: str, **info) -> None:
        n = _norm_feed(url)
        if n not in feeds:
            feeds[n] = {"feed": url, "found_on": page, **info}

    while queue and len(seen_pages) < max_pages:
        url, depth = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        host = urlparse(url).netloc.lower()
        http = bot if host in bot_hosts else web
        html = http.get_text(url)
        if not html:
            log.info("discovery: could not read %s", url)
            continue
        pages_ok += 1
        for link, text in _page_links(html, url):
            p = urlparse(link)
            lhost = p.netloc.lower()
            if lhost == "feeds.captivate.fm" and re.fullmatch(r"/[\w-]+/?", p.path or ""):
                add_feed(f"https://feeds.captivate.fm{p.path.rstrip('/')}/", url)
            elif lhost == "player.captivate.fm" and "/show/" in p.path:
                m = _UUID_RE.search(p.path)
                if m:
                    captivate_shows.setdefault(m[0].lower(), url)
            elif lhost.endswith(".captivate.fm") and lhost.count(".") == 2 and lhost.split(".")[0] not in (
                    "player", "feeds", "episodes", "artwork", "api", "insights-v2", "www", "app"):
                add_feed(f"https://feeds.captivate.fm/{lhost.split('.')[0]}/", url, via="captivate site")
            elif lhost == "podcasts.apple.com":
                m = re.search(r"/id(\d+)", p.path)
                if m:
                    apple_ids.setdefault(m[1], url)
            elif any(lhost == h or lhost.endswith("." + h) for h in _FEED_HOSTS):
                # a known podcast host: only its feed URLs, not its web pages
                if lhost == "anchor.fm":
                    if "/podcast/rss" in p.path:
                        add_feed(link, url)
                elif re.search(r"(?i)rss|feed|\.xml|/podcast", link):
                    add_feed(link, url)
            elif re.search(r"(?i)(\.rss|/rss/?|/feed/podcast/?|podcast[^/]*\.xml)$", p.path or ""):
                add_feed(link, url)
            # follow podcast-looking sub-pages on the same official site, one level deep
            if (depth == 0 and lhost == host and host in bot_hosts and link not in seen_pages
                    and (_FOLLOW_RE.search(p.path or "") or _FOLLOW_RE.search(text or ""))
                    and not _SKIP_PATH_RE.search(p.path or "") and not p.fragment
                    and all(q[0] != link for q in queue)):
                queue.append((link.split("#")[0], 1))

    # Captivate embedded players → the show's feed URL (+ its Apple/Spotify/Amazon pages)
    for uuid, page in list(captivate_shows.items())[:DISCOVERY_MAX_FEEDS]:
        html = web.get_text(f"https://player.captivate.fm/show/{uuid}")
        if not html:
            continue
        m = re.search(r"https?://feeds\.captivate\.fm/([\w-]+)", html)
        if not m:
            continue
        links = {}
        for name, pat in (("apple", r"https://podcasts\.apple\.com/[^\s\"'<>\\]+"),
                          ("spotify", r"https://open\.spotify\.com/show/[A-Za-z0-9]+"),
                          ("amazon", r"https://music\.amazon\.com/podcasts/[^\s\"'<>\\]+")):
            mm = re.search(pat, html)
            if mm:
                links[name] = mm.group(0)
        n = _norm_feed(f"https://feeds.captivate.fm/{m[1]}/")
        entry = feeds.setdefault(n, {"feed": f"https://feeds.captivate.fm/{m[1]}/", "found_on": page})
        entry.update({"player": f"https://player.captivate.fm/show/{uuid}", **{k: v for k, v in links.items() if k not in entry}})

    # Apple Podcasts ids → feed URL via Apple's public lookup API (no key)
    for aid, page in list(apple_ids.items())[:DISCOVERY_MAX_FEEDS]:
        r = web.get(f"https://itunes.apple.com/lookup?id={aid}&entity=podcast")
        try:
            res = (r.json().get("results") or []) if r is not None and r.status_code == 200 else []
        except ValueError:
            res = []
        for it in res:
            if it.get("feedUrl"):
                e = feeds.setdefault(_norm_feed(it["feedUrl"]), {"feed": it["feedUrl"], "found_on": page})
                e.setdefault("apple", f"https://podcasts.apple.com/podcast/id{aid}")

    configured = {_norm_feed(s.get("feed") or "") for s in shows}
    found = []
    for n, info in feeds.items():
        if n in configured:
            continue
        if len(found) >= DISCOVERY_MAX_FEEDS:
            break
        f, err = fetch_feed(web, info["feed"])
        if f is None:
            log.info("discovery: %s is not a usable feed (%s)", info["feed"], err)
            continue
        latest = max((_struct_to_iso(e.get("published_parsed")) or "" for e in f.entries), default="") or None
        lang = str(f.feed.get("language") or "")[:5] or None
        found.append({
            "feed": info["feed"], "title": clean_text(f.feed.get("title")), "language": lang,
            "episodes": len(f.entries), "latest": latest, "web": f.feed.get("link"),
            "found_on": info.get("found_on"),
            **{k: info[k] for k in ("player", "apple", "spotify", "amazon") if info.get(k)},
            "spanish": (lang or "").lower().startswith("es") or detect_lang(
                _lang_text(clean_text(f.feed.get("title")) + " " + strip_html(f.feed.get("summary") or "")[:300]), None) == "es",
        })
    return {"checked_at": now_iso(), "pages_checked": pages_ok, "feeds": found}


# --------------------------------------------------------------------------- local artwork
def local_art(http: PoliteSession, url: str | None, memo: dict[str, str | None], dry_run: bool = False) -> str | None:
    """Site path of a ≤480 px WebP copy of `url` (made once, kept in src/assets/cache/pod/), or None."""
    if not url or not str(url).startswith(("http://", "https://")):
        return None
    if url in memo:
        return memo[url]
    name = short_hash(url, 16) + ".webp"
    dest = ART_DIR / name
    rel = ART_URL + name
    if dest.exists() and dest.stat().st_size > 0:
        memo[url] = rel
        return rel
    memo[url] = None
    if dry_run:
        return None
    try:
        from PIL import Image
    except Exception:
        return None
    r = http.get(url, timeout=30)
    if r is None or r.status_code != 200:
        log.info("artwork not downloaded (%s): %s", getattr(r, "status_code", "no response"), url)
        return None
    # (the artwork CDN answers "application/octet-stream", so only reject HTML/text error pages;
    # Pillow decides whether the bytes are an image)
    if r.headers.get("Content-Type", "").lower().startswith("text/") or len(r.content) > ART_MAX_BYTES:
        return None
    try:
        ART_DIR.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(r.content)) as im:
            im = im.convert("RGB")
            im.thumbnail((ART_MAX_PX, ART_MAX_PX))
            tmp = dest.with_suffix(".webp.part")
            im.save(tmp, "WEBP", quality=78, method=6)
        os.replace(tmp, dest)
    except Exception as e:  # corrupt / unsupported image → the site keeps using the remote URL
        log.warning("artwork conversion failed for %s: %s", url, e)
        return None
    memo[url] = rel
    return rel


def attach_art(http: PoliteSession, items: list[dict], shows: list[dict], dry_run: bool) -> dict:
    """Set extra.thumb (episodes) and thumb (shows) to the local copy of their artwork, then delete
    cached files nothing uses any more. Returns small stats."""
    memo: dict[str, str | None] = {}
    for s in shows:
        s["thumb"] = local_art(http, s.get("image"), memo, dry_run)
    for it in items:
        ex = it.setdefault("extra", {})
        thumb = local_art(http, it.get("image"), memo, dry_run)
        if thumb:
            ex["thumb"] = thumb
        else:
            ex.pop("thumb", None)
    used = {v.rsplit("/", 1)[-1] for v in memo.values() if v}
    removed = 0
    if not dry_run and used and ART_DIR.is_dir():
        for f in ART_DIR.iterdir():
            if f.is_file() and f.name not in used and f.suffix in (".webp", ".part"):
                f.unlink(missing_ok=True)
                removed += 1
    return {"artwork": len(used), "artwork_missing": sum(1 for v in memo.values() if not v),
            "artwork_removed": removed}


# --------------------------------------------------------------------------- gone check
def audio_gone(http: PoliteSession, url: str | None) -> bool:
    """True only when the episode's audio file answers 404/410 (confirmed deleted)."""
    if not url:
        return False
    r = http.head(url)
    if r is not None and r.status_code == 405:  # some CDNs refuse HEAD
        r = http.get(url, stream=True, headers={"Range": "bytes=0-0"})
        if r is not None:
            r.close()
    return r is not None and r.status_code in (404, 410)


# --------------------------------------------------------------------------- one show's health
def show_title(show: dict, prev_shows: dict[str, dict] | None = None) -> str:
    """The show's name as people know it: the config's `name`, else the last read feed title, else its key."""
    old = (prev_shows or {}).get(show.get("key")) or {}
    return clean_text(show.get("name") or old.get("name") or old.get("title") or show.get("key") or "")


def failed_show(show: dict, err: str | None, prev: dict, prev_items: list[dict],
                prev_shows: dict[str, dict] | None = None) -> dict:
    """stats.shows[key] of a show whose feed failed in this run: ok false, its error, its episodes still on the site,
    `updated` = its last good read (kept from the last run's stats.shows, or — written before that was kept — the
    envelope's own `updated`, when the show was fine in that run) and `failing_since` (when this streak began)."""
    key = str(show.get("key"))
    stats = prev.get("stats") if isinstance(prev.get("stats"), dict) else {}
    before = (stats.get("shows") or {}).get(key) if isinstance(stats.get("shows"), dict) else None
    before = before if isinstance(before, dict) else {}
    if before.get("ok") is False:
        last_ok, since = before.get("updated"), before.get("failing_since") or prev.get("attempted")
    else:
        last_ok = before.get("updated") or (prev.get("updated") if before.get("ok") else None)
        since = None
    kept = sum(1 for i in prev_items if isinstance(i, dict) and i.get("category") == key and i.get("status") != "gone")
    return {"ok": False, "name": show_title(show, prev_shows), "error": err or "failed", "episodes": kept,
            "latest": before.get("latest"), "updated": last_ok, "failing_since": since or now_iso()}


def show_warning(row: dict, key: str) -> str:
    """A failing show in plain words (stats.warnings → /status/ and the run summary's Notes)."""
    last = f"last read {str(row['updated'])[:10]}" if row.get("updated") else "not read yet"
    n = row.get("episodes") or 0
    kept = ("its 1 episode stays on the site" if n == 1 else f"its {n} episodes stay on the site" if n
            else "nothing of it on the site yet")
    return f"{row.get('name') or key} ({key}): {row.get('error') or 'failed'} — {kept}; {last}"[:300]


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Sync podcast episodes → data/raw/podcasts.json")
    ap.add_argument("--limit", type=int, default=0, help="only the newest N episodes per show (testing)")
    ap.add_argument("--discover", action="store_true", help="run feed discovery now (normally weekly)")
    ap.add_argument("--no-discover", action="store_true", help="skip feed discovery")
    ap.add_argument("--gone-checks", type=int, default=GONE_CHECKS_PER_RUN,
                    help="max audio-file checks for episodes that left their feed")
    ap.add_argument("--dry-run", action="store_true", help="do everything but do not write the JSON")
    # parse_known_args: when a runner imports this module and calls main() without argv,
    # its own command-line flags must not crash us.
    args, unknown = ap.parse_known_args(argv)
    if unknown:
        log.debug("ignoring unknown arguments: %s", unknown)

    t0 = time.monotonic()
    cfg = load_config()
    sources = cfg.get("sources", {}) or {}
    shows = [s for s in (sources.get("podcasts") or []) if isinstance(s, dict) and s.get("feed") and s.get("key")]
    prev = load_raw(SOURCE)
    prev_items = prev.get("items", []) or []
    prev_discovery = prev.get("discovery") if isinstance(prev.get("discovery"), dict) else {}

    http = PoliteSession(min_delay=1.0, timeout=45, retries=3)
    new_items: list[dict] = []
    errors: list[str] = []
    per_show: dict[str, dict] = {}
    show_info: list[dict] = []
    ok_keys: set[str] = set()

    prev_shows = {s.get("key"): s for s in (prev.get("shows") or []) if isinstance(s, dict)}
    fetched: dict[str, Any] = {}
    for show in shows:
        key = str(show["key"])
        f, err = fetch_feed(http, show["feed"])
        fetched[key] = f
        if f is None:
            per_show[key] = failed_show(show, err, prev, prev_items, prev_shows)
            errors.append(show_warning(per_show[key], key))
            log.warning("[%s] feed failed: %s (%s)", key, err, show["feed"])
    link_counts, generic_pages = shared_link_info(shows, fetched)
    for show in shows:
        key = str(show["key"])
        f = fetched.get(key)
        if f is None:
            continue
        items = build_items(show, f, args.limit or None, link_counts=link_counts, generic_pages=generic_pages)
        new_items += items
        ok_keys.add(key)
        latest = max((i["date"] or "" for i in items), default="") or None
        per_show[key] = {"ok": True, "name": show_title(show, prev_shows), "episodes": len(items), "latest": latest,
                         "updated": now_iso()}
        show_info.append(show_meta(show, f, len(items)))
        log.info("[%s] %d episodes (latest %s)", key, len(items), latest)

    merged, added = merge_items(prev_items, new_items)

    # Episodes that left a healthy feed: mark "gone" only if the audio is really gone.
    fresh_ids = {i["id"] for i in new_items}
    missing = [i for i in merged if i.get("category") in ok_keys and i["id"] not in fresh_ids
               and i.get("status", "ok") != "gone"]
    checks = 0
    if not args.limit:
        for it in sorted(missing, key=lambda i: str(i.get("last_seen") or ""))[: args.gone_checks]:
            checks += 1
            if audio_gone(http, (it.get("extra") or {}).get("audio_url")):
                it["status"] = "gone"
    for it in merged:  # an episode that is back in its feed is fine again
        if it["id"] in fresh_ids:
            it["status"] = "ok"

    # Weekly discovery of feeds not yet in config (never fails the module).
    discovery = prev_discovery or {}
    last = parse_iso(discovery.get("checked_at"))
    due = args.discover or (not args.no_discover and (
        last is None or datetime.now(timezone.utc) - last >= timedelta(days=DISCOVERY_EVERY_DAYS)))
    if due:
        try:
            discovery = discover(shows, sources)
            log.info("discovery: %d page(s) checked, %d unconfigured feed(s) found",
                     discovery["pages_checked"], len(discovery["feeds"]))
        except Exception as e:  # noqa: BLE001
            log.warning("discovery failed: %s", e)
            discovery = {**(prev_discovery or {}), "error": f"{type(e).__name__}: {e}"[:200]}

    # A feed found by an earlier discovery that has since been added to the config is not "new".
    configured = {_norm_feed(s.get("feed") or "") for s in shows}
    if discovery.get("feeds"):
        discovery = {**discovery, "feeds": [d for d in discovery["feeds"]
                                            if _norm_feed(d.get("feed") or "") not in configured]}

    active = [i for i in merged if i.get("status") != "gone"]
    stats: dict[str, Any] = {
        "fetched": len(new_items),
        "new": added,
        "total": len(merged),
        "active": len(active),
        "gone": len(merged) - len(active),
        "spanish": sum(1 for i in active if i.get("lang") == "es"),
        "shows": per_show,
        "missing_from_feed": len(missing),
        "gone_checks": checks,
        "discovery_checked": discovery.get("checked_at"),
        "discovered_feeds": [
            {k: d.get(k) for k in ("feed", "title", "language", "episodes", "latest", "spanish", "apple", "spotify")}
            for d in discovery.get("feeds") or []
        ],
        "seconds": round(time.monotonic() - t0, 1),
    }
    if not shows:
        errors.append("no podcast feeds configured (sources.podcasts)")
    # One show that fails never hides the others' news: the source is ok while at least one show was read
    # (its `updated` moves on), and the failing show is named in stats.warnings and stats.shows (see the
    # module docstring). Only every show failing fails the source.
    ok = bool(ok_keys)
    error = "; ".join(errors)[:300] if errors and not ok else None
    if errors and ok:
        stats["warnings"] = errors[:8]
    log.info("episodes: %d total (%d new, %d Spanish, %d gone)", stats["total"], added, stats["spanish"], stats["gone"])
    if args.dry_run:
        log.info("dry run — not writing data/raw/%s.json; stats=%s", SOURCE, {k: v for k, v in stats.items() if k != "shows"})
        return
    # keep show metadata of a show whose feed failed today
    for s in shows:
        if s["key"] not in ok_keys and s["key"] in prev_shows:
            show_info.append(prev_shows[s["key"]])
    try:
        stats.update(attach_art(http, merged, show_info, args.dry_run))
    except Exception as e:  # noqa: BLE001 — artwork is an optimization, never a reason to fail
        log.warning("artwork step failed: %s", e)
    save_raw(SOURCE, merged, ok=ok, error=error, stats=stats,
             extra={"shows": show_info, "discovery": discovery})


if __name__ == "__main__":
    raise SystemExit(run_module(SOURCE, main))
