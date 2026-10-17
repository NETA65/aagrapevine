"""Full-site PDF crawler for www.aagrapevine.org + www.aalavina.org → data/raw/pdfs.json

WHY: the official sites publish flyers, catalogs, order forms, GVR/RLV kits, news sheets… as PDFs
scattered over ~3,100 pages. This module finds ALL of them and keeps the list current, daily.

HOW (one daily run, time-boxed; default 40 min, see config sources.crawler):
  1. Refresh the sitemaps (2-4 requests) → every page + its <lastmod>.
  2. Priority queue of pages to fetch:
       0 hub pages (resource pages, home pages, news…)        – every day, whatever their last answer
                                                                 (a failing one at every run)
       1 never-crawled content pages (sitemap + discovered links); pages awaiting a second 404
       2 pages whose sitemap <lastmod> is newer than our last visit
       3 never-crawled event pages, newest event date first
       4 pages not visited for `recheck_days` (past events: yearly)
  3. Each page: conditional GET (ETag / Last-Modified), collect every PDF link (a/iframe/embed/object,
     viewers, Drupal file links) with its link text, image alt and section heading; discover new
     internal pages (never login/cart/search/paywalled articles – see crawl_rules.SKIP_PATH_PATTERNS).
     A page that answered before keeps its PDF links through one 404/410: they are dropped only after
     a second one at least a day later (one bad answer during a site deploy must not re-file a kit).
  4. ~30 % of the time goes to PDF work: download new PDFs (capped per run) for page count, metadata
     title, language and a WebP thumbnail of page 1 (read in a separate process with a time limit and,
     on Linux, a memory limit; the attempt is recorded first, so a file that crashes or hangs the
     reader is skipped for a while and the run goes on); HEAD the rest; re-check PDFs that vanished
     from every page and, slowly, every PDF about once a month. A PDF becomes "gone" only after TWO
     failing checks at least a day apart (404/410, or an HTML page where the file was); a gone PDF
     that a page still links is checked again after a week, then monthly, and comes back when it
     answers again. A PDF on another site whose host has not answered at all for a month (4+ tries) is
     gone too. Such a host is asked twice before it counts as down for the run; its other PDFs then
     simply wait for the next run (no strike without a request), and a file robots.txt forbids is
     never "unreachable".
  5. Everything is remembered in data/state/crawl-state.json, so tomorrow's run resumes where today's
     stopped (pages that only take room — junk addresses, pages gone for PRUNE_GONE_DAYS that nothing
     links any more — are forgotten: prune()). data/raw/pdfs.json is rebuilt from that state at the
     end of every run, with `hub_problems` (hub / kit pages that did not load this run) and a line
     about them in stats.warnings.

The bot is polite: robots.txt is obeyed (one that answers 5xx or not at all closes its host for now,
RFC 9309 — PoliteSession; a run that could read no page because of it is a failed run, "site down?":
run_verdict) and the 5-second Crawl-delay is applied across BOTH hosts
together (they are one server), through the pipeline's shared_session(). A page (or sitemap) that an
earlier module of the same run already read — the home pages (quote), /BOTM (shop), the sitemap
(events_external)… — is taken from that session's page memo instead of being requested again, so the
daily run asks for each page once.

    python -m scripts.sync.crawl                      # normal daily run (config minutes)
    python -m scripts.sync.crawl --minutes 240        # long seed crawl
    python -m scripts.sync.crawl --minutes 0          # no network: rebuild pdfs.json from state (state untouched)
    python -m scripts.sync.crawl --url https://www.aagrapevine.org/gvr-resources --details 5
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import signal
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from . import crawl_rules as R
from .common import (CACHE_ASSETS, STATE_DIR, PoliteSession, clean_text, detect_lang, get_logger, load_config,
                     load_raw, make_item, merge_items, now_iso, parse_iso, read_json, run_module, save_raw,
                     shared_session, short_hash, to_iso)
from .crawl_pdf import PARSE_MEMORY_MB, PARSE_TIMEOUT_S, analyze_pdf_isolated, download_pdf, head_from_response

SOURCE = "pdfs"
STATE_FILE = STATE_DIR / "crawl-state.json"
THUMB_DIR = CACHE_ASSETS / "pdf"
THUMB_URL = "/assets/cache/pdf/"

STATE_VERSION = 1
PARSER_VERSION = 1           # bump when parse_page() changes → pages are re-parsed (no 304 shortcut)

# ---- scheduling knobs ----------------------------------------------------------------------------
PDF_TIME_SHARE = 0.30        # share of the run spent on PDF downloads / HEAD checks when work is queued
STOP_MARGIN_S = 30           # stop starting new requests when fewer seconds than this remain
HUB_REFRESH_H = 20           # hub pages are re-fetched when older than this (≈ daily)
HUB_RETRY_H = 12             # a hub that did not load (5xx, no answer, a 404…) is tried again after this
                             # (= at every daily run; other pages back off for days, see _fail)
PAST_EVENT_AFTER_DAYS = 60   # an event page this long past its date is "archived" …
PAST_EVENT_RECHECK_DAYS = 365  # … and only re-checked yearly (or when its sitemap lastmod changes)
ERROR_RECHECK_DAYS = {"404": 60, "410": 60, "400": 120, "not-html": 120, "robots": 30, "login": 30, "offsite": 60,
                      "pdf": 120}
GONE_RECHECK_DAYS = (7, 30)  # a "gone" PDF that a page still links is re-checked after 7 days, later monthly
GONE_CONFIRM_H = 24          # a PDF is "gone" — and a page's PDF links are dropped on a 404/410 — only after
                             # two failing checks at least this many hours apart
UNREACHABLE_GONE = (4, 30)   # an external PDF whose host never answers: gone after 4 tries over 30+ days
PERIODIC_HEAD_DAYS = 30      # re-HEAD every PDF about once a month (to notice deletions) …
MIN_PERIODIC_CHECKS = 20     # … at least this many per run (more when the library is large: n/30);
                             # they are the lowest-priority PDF work, so they only use spare time
MAX_PAGE_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 2                # discovered pages: at most 2 links away from a sitemap/hub page
MAX_KNOWN_PAGES = 8000       # runaway guards for link discovery
MAX_PER_SECTION = 400        # … per first path segment (e.g. /store/…)
MAX_REFERRERS = 40
GONE_PAGE_STATUSES = ("404", "410", "400")
PRUNE_GONE_DAYS = 90         # prune(): a page gone (404/410/400) this long that no page linked meanwhile
LINKED_STAMP_DAYS = 7        # a gone page's `linked_at` is refreshed at most this often (state-file churn)
SAVE_EVERY_S = 120           # checkpoint the state file this often during a run
LOGIN_PATH_RE = re.compile(r"(^|/)(user|usuario)/(login|inicio-sesion)|/login$")
# Crawler.last_failure values after which a PDF is simply asked again next run (no strike): robots.txt
# answered 5xx (or, on the magazine sites, gave no answer: host closed for now), the host is down for
# this run, or one miss with no time left to ask again (Crawler.request)
REQUEUE_FAILURES = ("robots-unavailable", "host-down", "no-time")

log = get_logger("crawl")


# ==================================================================================================
#  small helpers
# ==================================================================================================
def _dt(s: str | None) -> datetime | None:
    return parse_iso(s) if s else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _month_num(um: str | None) -> int:
    """'2026-02' → 202602 (0 when unknown) — used for 'newest first' ordering."""
    return int(um.replace("-", "")) if um else 0


def _backoff(tries: int) -> str:
    """next_try after the n-th failed try of a PDF download / analysis: 2, 4, 8, 16, then 30 days."""
    return to_iso(_now() + timedelta(days=min(30, 2 ** tries)))


@lru_cache(maxsize=1)
def _site_tz():
    try:
        return ZoneInfo((load_config().get("site") or {}).get("timezone") or "America/Chicago")
    except Exception:  # noqa: BLE001 — a bad setting or no time-zone data: the magazines' own calendar
        return ZoneInfo("America/Chicago")


def _local_day(iso: str) -> str:
    """'2026-11-01T04:30:00Z' → '2026-10-31': the day in the site's time zone (config site.timezone,
    America/Chicago) — the day the site shows, not the UTC one. A time without an offset is UTC (as
    every time the crawler writes), never the machine's own zone."""
    d = parse_iso(iso)
    if d is None:
        return iso[:10]
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(_site_tz()).date().isoformat()


class _ViaCrawler:
    """The `session` download_pdf() is given: every GET goes through Crawler.request (one retry for a
    silent host, hosts down for the run, robots.txt reasons in Crawler.last_failure, request count)."""

    def __init__(self, crawler: "Crawler"):
        self.crawler = crawler

    def get(self, url: str, **kw):
        return self.crawler.request("GET", url, **kw)


class Budget:
    """Wall-clock budget for one run."""

    def __init__(self, minutes: float):
        self.t0 = time.monotonic()
        self.limit = max(0.0, minutes) * 60.0

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def remaining(self) -> float:
        return self.limit - self.elapsed()

    def ok(self, need: float = STOP_MARGIN_S) -> bool:
        return self.remaining() > need


class Stop(BaseException):
    """Raised by the SIGTERM handler so a cancelled GitHub job still saves its progress. A
    BaseException (like KeyboardInterrupt), so the broad `except Exception` blocks around one page
    or one PDF never swallow it."""


# ==================================================================================================
#  state file
# ==================================================================================================
def empty_state() -> dict:
    return {"version": STATE_VERSION, "updated": None, "sitemaps": {}, "runs": [], "pages": {}, "pdfs": {}}


def load_state() -> tuple[dict, bool]:
    """Returns (state, loaded_ok). A missing/corrupt file is rebuilt from data/raw/pdfs.json so no
    known PDF is ever lost (pages are simply crawled again)."""
    st = read_json(STATE_FILE, None)
    if isinstance(st, dict) and isinstance(st.get("pages"), dict) and isinstance(st.get("pdfs"), dict):
        for k, v in empty_state().items():
            st.setdefault(k, v)
        return st, True
    if STATE_FILE.exists():
        log.warning("state file unreadable — rebuilding PDF records from data/raw/%s.json", SOURCE)
    return recover_state_from_raw(), False


def recover_state_from_raw() -> dict:
    st = empty_state()
    for it in load_raw(SOURCE).get("items", []):
        try:
            ex = it.get("extra") or {}
            url = ex.get("file_url") or it["url"]
            key = R.pdf_identity(R.canon_pdf_url(url) or url)
            refs = [{"url": r.get("url"), "title": r.get("title") or "", "section": "", "texts": [], "alts": [],
                     "seen": it.get("last_seen")} for r in ex.get("referrers") or [] if r.get("url")]
            if refs:
                refs[0]["texts"] = list(ex.get("link_texts") or [])
            st["pdfs"][key] = {
                "url": R.canon_pdf_url(url) or url, "first_seen": it.get("first_seen"),
                "last_seen_on_page": it.get("last_seen"), "refs": refs,
                "status": "gone" if it.get("status") == "gone" else "ok",
                "external": bool(ex.get("external")),
                "head": {"status": 200, "size": ex.get("size_bytes"), "checked_at": it.get("last_seen")}
                if ex.get("size_bytes") else None,
                "details": {"pages": ex.get("pages"), "thumb": ex.get("thumb"), "checked_at": it.get("last_seen")}
                if (ex.get("pages") or ex.get("thumb")) else None,
            }
        except Exception as e:  # one broken record must not stop recovery
            log.debug("skip raw item during recovery: %s", e)
    return st


def save_state(st: dict, dry_run: bool = False) -> None:
    """Compact JSON, one page / one PDF per line → small, readable git diffs; atomic replace."""
    if dry_run:
        return
    st["updated"] = now_iso()

    def dumps(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))

    out = ["{"]
    for k in st:
        if k not in ("pages", "pdfs"):
            out.append(f"{dumps(k)}:{dumps(st[k])},")
    for sect in ("pages", "pdfs"):
        rows = [f"{dumps(k)}:{dumps(v)}" for k, v in sorted(st[sect].items())]
        out.append(f'"{sect}":{{')
        if rows:
            out.append(",\n".join(rows))
        out.append("}" + ("," if sect == "pages" else ""))
    out.append("}")
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")      # *.tmp is git-ignored
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, STATE_FILE)


# ==================================================================================================
#  HTML parsing
# ==================================================================================================
_NAV_CLASS = re.compile(r"(?i)menu|navbar|breadcrumb|footer|header")


def _section_of(tag) -> str:
    """Nearest heading above a link (outside header/nav/footer): 'Postcards', 'Tarjetas postales'…"""
    h = tag
    for _ in range(8):
        h = h.find_previous(["h1", "h2", "h3", "h4"])
        if h is None:
            return ""
        if h.find_parent(["header", "nav", "footer"]) is None and h.find_parent(class_=_NAV_CLASS) is None:
            return clean_text(h.get_text(" ", strip=True))[:80]
    return ""


def parse_page(body: bytes, page_url: str, charset: str | None = None) -> tuple[str, list[dict], set[str]]:
    """Return (page title, pdf links, internal page links) of an HTML document."""
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(body, "lxml", from_encoding=charset or None)
    except Exception:
        soup = BeautifulSoup(body.decode("utf-8", "replace"), "lxml")
    base = page_url
    b = soup.find("base", href=True)
    if b:
        try:
            base = urljoin(page_url, b["href"])
        except ValueError:
            pass
    og = soup.find("meta", attrs={"property": "og:title"})
    title = (og.get("content") if og else None) or (soup.title.get_text(" ", strip=True) if soup.title else "")
    title = R.strip_site_suffix(title or "")

    pdfs: list[dict] = []
    links: set[str] = set()
    for tag in soup.find_all(["a", "area", "iframe", "embed", "object"]):
        attr = {"object": "data", "iframe": "src", "embed": "src"}.get(tag.name, "href")
        href = tag.get(attr)
        if not href or not isinstance(href, str):
            continue
        text = tag.get_text(" ", strip=True) if tag.name == "a" else ""
        classes = " ".join(tag.get("class") or [])
        if tag.parent is not None and tag.parent.name:
            classes += " " + " ".join(tag.parent.get("class") or [])
        purl = R.pdf_url_from_href(href, base, type_attr=str(tag.get("type") or ""), classes=classes, text=text)
        if purl:
            img = tag.find("img") if tag.name == "a" else None
            alt = clean_text(img.get("alt") or "") if img is not None else ""
            extra_txt = clean_text(tag.get("title") or tag.get("aria-label") or "")
            pdfs.append({
                "url": purl,
                "text": clean_text(text)[:200],
                "title_attr": extra_txt[:200],
                "alt": alt[:200],
                # (section lookup walks backwards through the page: capped for huge listing pages)
                "section": _section_of(tag) if len(pdfs) < 300 else "",
                "hint": not urlsplit(purl).path.lower().endswith(".pdf"),
            })
            continue
        if tag.name in ("a", "area"):
            nu = R.normalize_page_url(href, base)
            if nu:
                links.add(nu)
    return title, pdfs, links


# ==================================================================================================
#  the crawler
# ==================================================================================================
class Crawler:
    def __init__(self, st: dict, *, minutes: float, details_cap: int, recheck_days: int, max_mb: float,
                 max_pages: int | None, dry_run: bool, only_urls: list[str] | None, use_sitemap: bool):
        self.st = st
        self.pages: dict = st["pages"]
        self.pdfs: dict = st["pdfs"]
        self.budget = Budget(minutes)
        self.details_cap = max(0, details_cap)
        self.recheck_days = recheck_days
        self.max_bytes = int(max_mb * 1024 * 1024)
        self.max_pages = max_pages
        self.dry_run = dry_run
        self.only_urls = only_urls or []
        self.use_sitemap = use_sitemap and not self.only_urls
        self.http = shared_session()   # aagrapevine.org / aalavina.org (5 s crawl-delay, robots.txt)
        self.ext = PoliteSession(min_delay=2.0, timeout=15, retries=1)  # third-party PDF hosts
        self.via = _ViaCrawler(self)   # download_pdf()'s session: Crawler.request (retry, dead hosts)
        self.dead_hosts: set[str] = set()
        self.last_failure: str | None = None   # why the last request() returned None (see request)
        self.robots_down: dict[str, str] = {}  # host → robots.txt problem met this run (RFC 9309: host closed)
        self.tried: set[str] = set()           # pages actually asked for (or read from the memo) this run
        self.hubs = R.hub_urls()
        self.hub_rank = {u.lower(): i for i, u in enumerate(self.hubs)}
        self._index_pages()
        self.page_q: list = []
        self.pdf_q: list = []
        self.queued_pdf: set[tuple[str, str]] = set()
        self.done_pages: set[str] = set()
        self.c = Counter()     # run counters
        self.new_pdf_keys: list[str] = []
        self.t_pages = 0.0
        self.t_pdfs = 0.0
        self.last_save = time.monotonic()
        self.started = now_iso()
        self.sitemap_ok: bool | None = None
        self.periodic_cap = max(MIN_PERIODIC_CHECKS, -(-len(self.pdfs) * 11 // (10 * PERIODIC_HEAD_DAYS)))

    def _index_pages(self) -> None:
        self.page_lc = {k.lower(): k for k in self.pages}
        self.section_counts = Counter(self._section_key(u) for u, p in self.pages.items() if p.get("src") == "link")

    # ------------------------------------------------------------------ HTTP (polite, budgeted)
    # The Crawl-delay across BOTH Drupal hosts (one server) and all modules is applied by
    # shared_session() itself (PoliteSession paces per server — common.SAME_SERVER_HOSTS).
    def request(self, method: str, url: str, **kw):
        """One polite request → the response, or None with self.last_failure = why (PoliteSession's
        "robots" / "robots-unavailable" / "unreachable" / "redirects", or "host-down" / "no-time").
        Another site that gives no answer is asked once more; a second miss marks the host down for the
        rest of the run ("host-down": nothing is sent — its PDFs wait for the next run, see
        REQUEUE_FAILURES; "no-time": one miss and no time left to ask again, likewise). A robots.txt
        that gave no answer (PoliteSession asked twice; nothing was sent for the URL) is "robots-
        unavailable" on the magazine sites (their pages and files wait for the next run, as for a 5xx)
        and "unreachable" on another site (its host is down for the run)."""
        host = _host(url)
        drupal = host in R.DRUPAL_HOSTS
        sess = self.http if drupal else self.ext
        if not drupal and host in self.dead_hosts:
            self.last_failure = "host-down"
            return None
        old = sess.retries
        if self.budget.remaining() < 150:
            sess.retries = 1       # near the end of the budget: no long retry back-offs
        why = "unreachable"
        try:
            for attempt in (1, 2):
                r = sess.request(method, url, **kw)
                why = getattr(sess, "last_failure", None) or "unreachable"
                if r is not None or why in ("unreachable", "redirects"):
                    self.c["requests"] += 1     # (robots.txt refusals send nothing)
                if r is not None:
                    self.last_failure = None
                    return r
                if why == "robots-unreachable":    # robots.txt was already asked twice: no new try
                    why = "robots-unavailable" if drupal else "unreachable"
                    break
                if drupal or why != "unreachable" or attempt == 2:
                    break
                if not self.budget.ok():
                    why = "no-time"         # no time left to ask again: one miss is no verdict
                    break
                log.info("%s %s: no answer — asking once more", method, url)
        finally:
            sess.retries = old
        if not drupal and why == "unreachable":
            self.dead_hosts.add(host)
            log.warning("%s: no answer twice — its other documents wait for the next run", host)
        elif drupal and why == "robots-unavailable":
            # for the run's notes (run_warnings) — also when only a document met it
            self.robots_down[host] = sess.robots_problem(url) or "unavailable"
        self.last_failure = why
        return None

    # ------------------------------------------------------------------ sitemap
    def refresh_sitemaps(self) -> None:
        """Fetch the sitemap index + children. Adds new pages, updates <lastmod>, flags pages that
        left the sitemap (they are still re-checked, just no longer trusted as current)."""
        seen_maps: set[str] = set()
        queue = [f"https://{R.DRUPAL_HOSTS[0]}/sitemap.xml"]
        found: dict[str, str | None] = {}
        complete = True
        hosts_in_urls: set[str] = set()
        tried_second_index = False
        meta = self.st.setdefault("sitemaps", {})
        while True:
            if not queue:
                # The aalavina.org index normally points to the same children. Only fetch it if the
                # first index yielded no aalavina.org pages (i.e. the sites were split one day).
                if not tried_second_index and R.DRUPAL_HOSTS[1] not in hosts_in_urls:
                    tried_second_index = True
                    queue.append(f"https://{R.DRUPAL_HOSTS[1]}/sitemap.xml")
                    continue
                break
            sm = queue.pop(0)
            if sm in seen_maps:
                continue
            if len(seen_maps) >= 12 or not self.budget.ok():
                complete = False       # some child sitemaps unread → don't flag pages as removed
                continue
            seen_maps.add(sm)
            memo = self.http.remembered(sm)          # already read this run (events_external)
            if memo is not None:
                content, status = memo["text"].encode("utf-8"), 200
                self.c["sitemap_reused"] += 1
            else:
                r = self.request("GET", sm, timeout=(10, 60), headers={"Accept": "application/xml,text/xml;q=0.9,*/*;q=0.5"})
                self.c["sitemap_requests"] += 1
                if r is None or r.status_code != 200:
                    complete = False
                    log.warning("sitemap %s -> %s", sm, getattr(r, "status_code", "no response"))
                    continue
                content, status = r.content, r.status_code
            try:
                from lxml import etree
                root = etree.fromstring(content, parser=etree.XMLParser(recover=True, huge_tree=True,
                                                                        resolve_entities=False, no_network=True))
            except Exception as e:
                complete = False
                log.warning("sitemap %s unparsable: %s", sm, e)
                continue
            if root is None:
                complete = False
                continue
            tag = etree.QName(root).localname
            if tag == "sitemapindex":
                for loc in root.iter("{*}loc"):
                    u = (loc.text or "").strip()
                    try:
                        p = urlsplit(u)
                    except ValueError:
                        continue
                    child = urlunsplit(("https", R.HOST_ALIASES.get(p.hostname or "", p.hostname or ""), p.path, p.query, ""))
                    if child not in seen_maps and _host(child) in R.DRUPAL_HOSTS:
                        queue.append(child)
            elif tag == "urlset":
                for u in root.iter("{*}url"):
                    loc = u.find("{*}loc")
                    lm = u.find("{*}lastmod")
                    if loc is None or not loc.text:
                        continue
                    nu = R.normalize_page_url(loc.text.strip())
                    if not nu:
                        continue
                    hosts_in_urls.add(_host(nu))
                    if not R.should_crawl_path(urlsplit(nu).path):
                        continue        # e.g. /site-search: never fetched, so not kept either (prune())
                    lastmod = None
                    if lm is not None and lm.text:
                        d = parse_iso(lm.text.strip())
                        lastmod = to_iso(d) if d else None
                    found[nu] = lastmod
            meta[sm] = {"fetched": now_iso(), "status": status}
        if not found:
            self.sitemap_ok = False
            log.warning("sitemap refresh failed — continuing with %d known pages", len(self.pages))
            return
        self.sitemap_ok = True
        added = 0
        for url, lastmod in found.items():
            key = self.page_lc.get(url.lower(), url)
            pg = self.pages.get(key)
            if pg is None:
                pg = self.pages[key] = {"src": "sitemap", "depth": 0, "crawled_at": None}
                self.page_lc[key.lower()] = key
                added += 1
            pg["in_sitemap"] = True
            pg["depth"] = 0
            if lastmod:
                pg["lastmod"] = lastmod
        if complete:
            for key, pg in self.pages.items():
                if pg.get("in_sitemap") and key not in found:
                    pg["in_sitemap"] = False
        self.c["sitemap_urls"] = len(found)
        self.c["sitemap_new"] = added
        log.info("sitemap: %d URLs (%d new pages)", len(found), added)

    # ------------------------------------------------------------------ queues
    @staticmethod
    def _section_key(url: str) -> str:
        parts = urlsplit(url).path.split("/")
        return f"{_host(url)}/{parts[1] if len(parts) > 1 else ''}".lower()

    def page_priority(self, url: str, pg: dict, now: datetime):
        """Priority tuple for a page that is due, or None if it is not due."""
        path = urlsplit(url).path
        if not R.should_crawl_path(path):
            return None
        nt = _dt(pg.get("next_try"))
        if nt and nt > now:
            return None
        crawled = _dt(pg.get("crawled_at"))
        hub = self.hub_rank.get(url.lower())
        if hub is not None:
            # before the error rule below: whatever a hub last answered (404, an outage, a login page),
            # it is asked again daily — a failing one at every run (_note_error caps its next_try)
            if crawled is None or pg.get("error_since") or now - crawled > timedelta(hours=HUB_REFRESH_H):
                return (0, hub, 0.0, url)
            return None
        if pg.get("gone_strike_at") and pg.get("status") == 200:
            return (1, -1, 0.0, url)       # one 404/410 so far: the confirming check (_page_gone)
        status = str(pg.get("status"))
        if crawled is not None and status in ERROR_RECHECK_DAYS:    # 404, login, not-html … : rarely
            if now - crawled > timedelta(days=ERROR_RECHECK_DAYS[status]):
                return (4, 0, crawled.timestamp(), url)
            return None
        ev = R.event_date_of(url)
        lastmod = _dt(pg.get("lastmod"))
        if crawled is None:
            if ev:
                return (3, -int(ev.replace("-", "")), 0.0, url)
            return (1, int(pg.get("depth") or 0), -(lastmod.timestamp() if lastmod else 0.0), url)
        if lastmod and lastmod > crawled:
            return (2, 0, -lastmod.timestamp(), url)
        days = self.recheck_days
        if ev:
            try:
                evd = datetime.fromisoformat(ev).replace(tzinfo=timezone.utc)
                if now - evd > timedelta(days=PAST_EVENT_AFTER_DAYS):
                    days = PAST_EVENT_RECHECK_DAYS
            except ValueError:
                pass
        if now - crawled > timedelta(days=days):
            return (4, 0, crawled.timestamp(), url)
        return None

    def push_page(self, url: str, now: datetime | None = None) -> None:
        pr = self.page_priority(url, self.pages[url], now or _now())
        if pr is not None:
            heapq.heappush(self.page_q, (pr, url))

    def _ref_class(self, rec: dict) -> int:
        """0 kit page, 1 hub, 2 content, 3 event, 4 unlinked; +1 for third-party hosts."""
        best = 4
        for ref in rec.get("refs") or []:
            u = ref.get("url") or ""
            c = 0 if u in R.KIT_PAGES else 1 if u.lower() in self.hub_rank else 3 if R.is_event_path(u) else 2
            best = min(best, c)
        return best + (1 if rec.get("external") else 0)

    def needs_details(self, rec: dict, now: datetime) -> bool:
        if rec.get("status") in ("gone", "not-pdf"):
            return False
        d = rec.get("details")
        if not d:
            return True
        if d.get("error") == "too-large":
            # retried automatically when config pdf_max_mb is raised above the file's size
            size = (rec.get("head") or {}).get("size")
            return bool(size) and size <= self.max_bytes
        if d.get("final") or not d.get("error"):
            return False
        nt = _dt(d.get("next_try"))
        return nt is None or nt <= now

    def push_pdf(self, key: str, now: datetime | None = None) -> None:
        """Queue the PDF work a record needs (at most one entry per kind)."""
        now = now or _now()
        rec = self.pdfs[key]
        if rec.get("status") == "not-pdf":
            return
        cls = self._ref_class(rec)
        newest = -_month_num(R.upload_month_of(rec["url"]))
        head = rec.get("head") or {}
        checked = _dt(head.get("checked_at"))
        tasks = []
        if self.needs_details(rec, now) and self.details_cap:
            tasks.append(((0, cls, newest, key), "details"))
        vanished = _dt(rec.get("vanished_at"))
        strike = _dt(rec.get("gone_strike_at"))
        if rec.get("recheck") or (vanished and (checked is None or checked < vanished)):
            # no page links it any more (→ is it deleted?) or a "gone" PDF is linked again (→ back?)
            tasks.append(((1, cls, 0, key), "vanished"))
        elif strike and now - strike >= timedelta(hours=GONE_CONFIRM_H) and rec.get("status") != "gone":
            # one 404 / error page so far: check once more before calling it gone
            tasks.append(((1, cls, 0, key), "vanished"))
        elif rec.get("status") == "gone" and rec.get("refs"):
            # a page still links it: a short outage or a re-upload at the same address must not hide
            # it for good — re-check after a week, later monthly
            since = _dt(rec.get("gone_since")) or checked
            days = GONE_RECHECK_DAYS[0] if since and now - since < timedelta(days=60) else GONE_RECHECK_DAYS[1]
            nt = _dt(head.get("next_try"))
            if (checked is None or now - checked >= timedelta(days=days)) and (nt is None or nt <= now):
                tasks.append(((3, 0, int(checked.timestamp()) if checked else 0, key), "periodic"))
        elif not head.get("status") and not (self.needs_details(rec, now) and self.details_cap):
            nt = _dt(head.get("next_try"))
            if nt is None or nt <= now:
                tasks.append(((2, cls, newest, key), "head"))
        elif checked and now - checked > timedelta(days=PERIODIC_HEAD_DAYS) and rec.get("status") != "gone":
            tasks.append(((3, 0, int(checked.timestamp()), key), "periodic"))
        for prio, kind in tasks:
            if (key, kind) not in self.queued_pdf:
                self.queued_pdf.add((key, kind))
                heapq.heappush(self.pdf_q, (prio, kind, key))

    def build_queues(self) -> None:
        now = _now()
        if self.only_urls:
            for i, u in enumerate(self.only_urls):
                nu = R.normalize_page_url(u)
                if not nu:
                    log.warning("not a crawlable page URL: %s", u)
                    continue
                key = self.page_lc.get(nu.lower(), nu)
                if key not in self.pages:
                    self.pages[key] = {"src": "manual", "depth": 0, "crawled_at": None}
                    self.page_lc[key.lower()] = key
                heapq.heappush(self.page_q, ((0, i, 0.0, key), key))
            return
        for url in self.hubs:        # make sure every hub page is known even if not in the sitemap
            if url.lower() not in self.page_lc:
                self.pages[url] = {"src": "hub", "depth": 0, "crawled_at": None}
                self.page_lc[url.lower()] = url
        for url in list(self.pages):
            self.push_page(url, now)
        for key in list(self.pdfs):
            self.push_pdf(key, now)

    # ------------------------------------------------------------------ pruning
    def prune(self) -> None:
        """Forget the pages that only take room under MAX_KNOWN_PAGES (link discovery stops there):
          * addresses the crawler never fetches (should_crawl_path: an e-mail address or a host name read
            as a relative link, search pages…) — earlier rules let some in; never fetched, never useful;
          * pages gone (404/410/400) for PRUNE_GONE_DAYS that no crawled page has linked meanwhile
            (`linked_at`, see discover()) and that the sitemap does not list.
        Hubs are always kept. A pruned page that some page links again is simply discovered anew."""
        now = _now()
        cut = now - timedelta(days=PRUNE_GONE_DAYS)
        for url in list(self.pages):
            pg = self.pages[url]
            if url.lower() in self.hub_rank:
                continue
            if not R.should_crawl_path(urlsplit(url).path):
                why = "junk"
            elif str(pg.get("status")) in GONE_PAGE_STATUSES and not pg.get("in_sitemap"):
                since = _dt(pg.get("error_since") or pg.get("crawled_at"))
                linked = _dt(pg.get("linked_at"))
                if since is None or since > cut or (linked is not None and linked > cut):
                    continue
                why = "gone"
            else:
                continue
            if pg.get("pdfs"):
                self.set_page_pdfs(url, pg, [])      # its PDFs lose this referrer (as on a 404)
            del self.pages[url]
            self.c[f"pruned_{why}"] += 1
        if self.c["pruned_junk"] or self.c["pruned_gone"]:
            self._index_pages()
            log.info("pruned %d junk and %d long-gone page(s) from the state", self.c["pruned_junk"],
                     self.c["pruned_gone"])

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        self.prune()
        if self.use_sitemap and self.budget.ok():
            self.refresh_sitemaps()
        self.build_queues()
        log.info("queue: %d pages due, %d PDF tasks; budget %.1f min", len(self.page_q), len(self.pdf_q),
                 self.budget.limit / 60)
        while self.budget.ok():
            page_limit = self.max_pages is not None and self.c["pages_fetched"] >= self.max_pages
            has_pages = bool(self.page_q) and not page_limit
            if not has_pages and not self.pdf_q:
                break
            want_pdf = bool(self.pdf_q) and (not has_pages or self.t_pdfs <= PDF_TIME_SHARE * (self.t_pages + self.t_pdfs))
            t0 = time.monotonic()
            if want_pdf:
                self.do_pdf_task()
                self.t_pdfs += time.monotonic() - t0
            else:
                self.do_page_task()
                self.t_pages += time.monotonic() - t0
            if time.monotonic() - self.last_save > SAVE_EVERY_S:
                save_state(self.st, self.dry_run)
                self.last_save = time.monotonic()

    # ------------------------------------------------------------------ pages
    def do_page_task(self) -> None:
        _prio, url = heapq.heappop(self.page_q)
        if url in self.done_pages or url not in self.pages:
            return
        self.done_pages.add(url)
        try:
            self.crawl_page(url, self.pages[url])
        except Stop:
            raise
        except Exception as e:  # never let one page stop the crawl
            log.warning("page %s failed: %s: %s", url, type(e).__name__, e)
            self._fail(url, self.pages[url], f"{type(e).__name__}")

    def _fail(self, url: str, pg: dict, status) -> None:
        """No usable answer (5xx, no answer, a read error): try again after 1, 2, 4 … 30 days — a hub
        after HUB_RETRY_H (_note_error), so five 503s in a row never hide it for weeks."""
        pg["fails"] = int(pg.get("fails") or 0) + 1
        pg["next_try"] = to_iso(_now() + timedelta(days=min(30, 2 ** (pg["fails"] - 1))))
        self._note_error(url, pg, now_iso(), status)
        self.c["page_errors"] += 1

    def _note_error(self, url: str, pg: dict, now: str, label) -> None:
        """Any answer that is not a readable page (an error, a first 404, a login page, robots.txt…):
        `last_error` = what it was, `error_since` = when the streak began (the hub report, prune()). A
        hub gets its next try at the next run (HUB_RETRY_H), whatever the error."""
        pg["last_error"] = str(label)[:60]
        pg.setdefault("error_since", now)
        if pg.get("status") != 200:
            pg.pop("gone_strike_at", None)    # only a page that last answered 200 awaits a confirming 404
        if url.lower() in self.hub_rank:
            cap = _now() + timedelta(hours=HUB_RETRY_H)
            nt = _dt(pg.get("next_try"))
            if nt is None or nt > cap:
                pg["next_try"] = to_iso(cap)

    @staticmethod
    def _clear_error(pg: dict) -> None:
        for k in ("last_error", "error_since", "gone_strike_at", "linked_at"):
            pg.pop(k, None)

    def _page_gone(self, url: str, pg: dict, code: int, now: str) -> None:
        """404 / 410. A page that answered before keeps its PDF links until a SECOND such answer at least
        GONE_CONFIRM_H later (as a PDF must fail twice, _mark_gone): one bad answer during a site deploy
        must not re-file or orphan every document of a kit page. Until then it is asked again the next
        day (priority 1; a hub at every run). Confirmed: status "404"/"410", its PDF links are dropped."""
        if pg.get("status") == 200:
            strike = _dt(pg.get("gone_strike_at"))
            if strike is None:
                strike = _dt(now)
                pg["gone_strike_at"] = now
                self.c["pages_gone_strikes"] += 1
            if _dt(now) - strike < timedelta(hours=GONE_CONFIRM_H):
                pg["next_try"] = to_iso(strike + timedelta(hours=GONE_CONFIRM_H))
                self._note_error(url, pg, now, code)
                log.warning("page %s -> %s: its %d PDF link(s) are kept until a second check confirms it",
                            url, code, len(pg.get("pdfs") or []))
                return
        elif str(pg.get("status")) in GONE_PAGE_STATUSES and not pg.get("error_since"):
            pg["error_since"] = pg.get("crawled_at") or now     # gone since before this was recorded
        pg.update(status=str(code), crawled_at=now, fails=0, next_try=None)
        pg.pop("gone_strike_at", None)
        self._note_error(url, pg, now, code)
        self.set_page_pdfs(url, pg, [])
        self.c["pages_gone"] += 1

    def crawl_page(self, url: str, pg: dict) -> None:
        now = now_iso()
        # PDFs that appear on a page we had crawled before are genuinely new ("fresh")
        known_before = pg.get("status") == 200 and bool(pg.get("crawled_at"))
        if not self.http.allowed(url):
            problem = self.http.robots_problem(url)
            if problem:
                # robots.txt itself did not answer properly: the whole host is off-limits for now (RFC
                # 9309). Nothing is recorded — the page is due again at the next run.
                self.robots_down[_host(url)] = problem
                self.c["robots_unavailable"] += 1
                return
            self.tried.add(url)
            pg.update(status="robots", crawled_at=now)
            self._note_error(url, pg, now, "robots")
            self.c["robots_skipped"] += 1
            return
        self.tried.add(url)
        memo = self.http.remembered(url) if _host(url) in R.DRUPAL_HOSTS else None
        if memo is not None and self.crawl_remembered(url, pg, memo, known_before, now):
            return
        headers = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"}
        if pg.get("pv") == PARSER_VERSION and pg.get("status") == 200:
            if pg.get("etag"):
                headers["If-None-Match"] = pg["etag"]
            if pg.get("last_modified"):
                headers["If-Modified-Since"] = pg["last_modified"]
        r = self.request("GET", url, headers=headers, stream=True, timeout=(10, 30))
        self.c["pages_fetched"] += 1
        if r is None:
            why = self.last_failure
            if why == "robots-unavailable":            # robots.txt failed meanwhile: as above
                self.tried.discard(url)
                self.robots_down[_host(url)] = self.http.robots_problem(url) or "unavailable"
                self.c["robots_unavailable"] += 1
            elif why == "robots":                      # a redirect to a disallowed address
                pg.update(status="robots", crawled_at=now)
                self._note_error(url, pg, now, "robots")
            else:
                self._fail(url, pg, "too many redirects" if why == "redirects" else "no-response")
            return
        body = b""
        try:
            final = R.normalize_page_url(r.url) or r.url
            code = r.status_code
            ctype = (r.headers.get("Content-Type") or "").lower()
            if code == 304:
                pg.update(crawled_at=now, fails=0, next_try=None)
                self._clear_error(pg)
                self.c["not_modified"] += 1
                for key in pg.get("pdfs") or []:
                    if key in self.pdfs:
                        self.pdfs[key]["last_seen_on_page"] = now
                        self.push_pdf(key)     # no-op when already queued / nothing needed
                return
            if code in (404, 410):
                self._page_gone(url, pg, code, now)
                return
            if code == 400:            # a malformed address — asking again soon will not help
                pg.update(status="400", crawled_at=now, fails=0, next_try=None)
                self._note_error(url, pg, now, code)
                return
            if code != 200:
                self._fail(url, pg, code)
                return
            fpath = urlsplit(final).path.lower()
            if LOGIN_PATH_RE.search(fpath):
                pg.update(status="login", crawled_at=now, fails=0, next_try=None)
                self._note_error(url, pg, now, "login")
                return
            if _host(final) not in R.DRUPAL_HOSTS:
                pg.update(status="offsite", crawled_at=now, final=r.url, fails=0, next_try=None)
                self._note_error(url, pg, now, "offsite")
                return
            if "application/pdf" in ctype:
                # the "page" is itself a PDF (e.g. a /node/… that redirects to a file)
                purl = R.canon_pdf_url(r.url)
                ref = pg.get("from")
                if purl and ref and ref in self.pages:
                    self.add_pdf_refs(ref, self.pages[ref], [{"url": purl, "text": "", "title_attr": "", "alt": "",
                                                               "section": "", "hint": True}], replace=False)
                pg.update(status="pdf", crawled_at=now, fails=0, next_try=None)
                self._clear_error(pg)
                return
            if "html" not in ctype and "xml" not in ctype:
                pg.update(status="not-html", crawled_at=now, fails=0, next_try=None)
                self._note_error(url, pg, now, "not-html")
                return
            buf = bytearray()
            for chunk in r.iter_content(chunk_size=64 * 1024):
                buf += chunk
                if len(buf) > MAX_PAGE_BYTES:
                    self.c["pages_truncated"] += 1
                    break
            body = bytes(buf)
            etag = r.headers.get("ETag")
            last_mod = r.headers.get("Last-Modified")
            charset = r.encoding if "charset" in ctype else None
        except Exception as e:
            self._fail(url, pg, f"read: {type(e).__name__}")
            return
        finally:
            try:
                r.close()
            except Exception:
                pass
        self.record_page(url, pg, body, final, charset, etag, last_mod, known_before, now)

    def crawl_remembered(self, url: str, pg: dict, memo: dict, known_before: bool, now: str) -> bool:
        """A page another module already read in this run (the shared session's page memo): parse that
        copy instead of asking the server again. False when the copy can't stand in for a crawl (it
        redirected off the magazine hosts or to a login page, or it is not HTML) → the normal GET."""
        final = R.normalize_page_url(memo.get("url") or url) or url
        ctype = str((memo.get("headers") or {}).get("Content-Type") or "").lower()
        if (_host(final) not in R.DRUPAL_HOSTS or LOGIN_PATH_RE.search(urlsplit(final).path.lower())
                or (ctype and "html" not in ctype and "xml" not in ctype)):
            return False
        body = memo["text"].encode("utf-8")[:MAX_PAGE_BYTES]
        h = memo.get("headers") or {}
        self.c["pages_reused"] += 1
        self.record_page(url, pg, body, final, "utf-8", h.get("ETag"), h.get("Last-Modified"), known_before, now)
        return True

    def record_page(self, url: str, pg: dict, body: bytes, final: str, charset: str | None, etag: str | None,
                    last_mod: str | None, known_before: bool, now: str) -> None:
        """A page read (200, HTML): its PDFs and links → the state."""
        title, pdf_links, links = parse_page(body, final, charset)
        pg.update(status=200, crawled_at=now, etag=etag, last_modified=last_mod, title=title[:200],
                  out_links=len(links), fails=0, next_try=None, pv=PARSER_VERSION)
        self._clear_error(pg)
        if final != url:
            pg["final"] = final
        else:
            pg.pop("final", None)
        self.set_page_pdfs(url, pg, pdf_links, fresh=known_before)
        self.discover(url, pg, links)
        self.c["pages_ok"] += 1
        if pdf_links:
            log.info("page %s: %d PDF links", url, len({p['url'] for p in pdf_links}))

    def discover(self, url: str, pg: dict, links: set[str]) -> None:
        now = _now()
        for link in links:
            # a gone page that a page still links is kept (prune()): note when it was last seen linked
            known = self.pages.get(self.page_lc.get(link.lower(), ""))
            if known is not None and str(known.get("status")) in GONE_PAGE_STATUSES:
                seen = _dt(known.get("linked_at"))
                if seen is None or now - seen >= timedelta(days=LINKED_STAMP_DAYS):
                    known["linked_at"] = to_iso(now)
        depth = int(pg.get("depth") or 0) + 1
        if depth > MAX_DEPTH or self.only_urls:
            return
        for link in sorted(links):
            if link.lower() in self.page_lc:
                continue
            if len(self.pages) >= MAX_KNOWN_PAGES:
                self.c["discover_capped"] += 1
                return
            if not R.should_crawl_path(urlsplit(link).path):
                continue
            sk = self._section_key(link)
            if not R.is_event_path(link) and self.section_counts[sk] >= MAX_PER_SECTION:
                self.c["discover_section_capped"] += 1
                continue
            self.pages[link] = {"src": "link", "depth": depth, "from": url, "in_sitemap": False, "crawled_at": None}
            self.page_lc[link.lower()] = link
            self.section_counts[sk] += 1
            self.c["pages_discovered"] += 1
            self.push_page(link, now)

    # ------------------------------------------------------------------ PDF bookkeeping
    def set_page_pdfs(self, page_url: str, pg: dict, found: list[dict], fresh: bool = False) -> None:
        """Make the PDF records agree with what `page_url` links to right now."""
        keys = self.add_pdf_refs(page_url, pg, found, replace=True, fresh=fresh)
        now = now_iso()
        for key in set(pg.get("pdfs") or []) - set(keys):
            rec = self.pdfs.get(key)
            if not rec:
                continue
            rec["refs"] = [r for r in rec.get("refs") or [] if r.get("url") != page_url]
            if not rec["refs"]:
                rec["vanished_at"] = now
                self.push_pdf(key)
        pg["pdfs"] = sorted(keys)

    def add_pdf_refs(self, page_url: str, pg: dict, found: list[dict], replace: bool,
                     fresh: bool = False) -> list[str]:
        now = now_iso()
        agg: dict[str, dict] = {}
        for f in found:
            key = R.pdf_identity(f["url"])
            a = agg.setdefault(key, {"url": f["url"], "texts": [], "alts": [], "section": "", "hint": True})
            for t in (f.get("text"), f.get("title_attr")):
                if t and t not in a["texts"]:
                    a["texts"].append(t)
            if f.get("alt") and f["alt"] not in a["alts"]:
                a["alts"].append(f["alt"])
            a["section"] = a["section"] or f.get("section") or ""
            a["hint"] = a["hint"] and bool(f.get("hint"))
        for key, a in agg.items():
            rec = self.pdfs.get(key)
            if rec is None:
                rec = self.pdfs[key] = {
                    "url": a["url"], "first_seen": now, "last_seen_on_page": now, "refs": [], "status": "ok",
                    "external": _host(a["url"]) not in R.DRUPAL_HOSTS,
                }
                if a["hint"]:
                    rec["hint"] = True     # not a *.pdf URL: HEAD must confirm it is a PDF
                if fresh:
                    rec["fresh"] = True    # appeared on an already-known page → first_seen ≈ publish date
                self.new_pdf_keys.append(key)
                self.c["new_pdfs"] += 1
            refs = rec.setdefault("refs", [])
            ref = next((r for r in refs if r.get("url") == page_url), None)
            if ref is None:
                if len(refs) >= MAX_REFERRERS:
                    refs.sort(key=lambda r: (R.is_event_path(r.get("url") or ""), r.get("seen") or ""))
                    refs.pop()
                ref = {"url": page_url}
                refs.append(ref)
            ref.update(title=pg.get("title") or "", section=a["section"], texts=a["texts"][:4],
                       alts=a["alts"][:3], seen=now)
            rec["last_seen_on_page"] = now
            if rec.pop("vanished_at", None) and rec.get("status") == "gone":
                rec["recheck"] = True      # linked again → verify it is back
            self.push_pdf(key)
        if not replace:
            pg["pdfs"] = sorted(set(pg.get("pdfs") or []) | set(agg))
        return list(agg)

    # ------------------------------------------------------------------ PDF work
    def do_pdf_task(self) -> None:
        _prio, kind, key = heapq.heappop(self.pdf_q)
        self.queued_pdf.discard((key, kind))
        rec = self.pdfs.get(key)
        if rec is None:
            return
        if rec.get("external") and _host(rec["url"]) in self.dead_hosts:
            self.c["pdfs_requeued"] += 1    # its host did not answer this run: asked again next run, no strike
            return
        now = _now()
        try:
            if kind == "details":
                if self.c["details"] >= self.details_cap:
                    if not (rec.get("head") or {}).get("status"):
                        heapq.heappush(self.pdf_q, ((2, self._ref_class(rec), -_month_num(R.upload_month_of(rec["url"])), key), "head", key))
                        self.queued_pdf.add((key, "head"))
                    return
                if self.needs_details(rec, now):
                    self.fetch_details(key, rec)
            else:
                # re-validate: another task may already have checked this PDF during this run
                head = rec.get("head") or {}
                checked = _dt(head.get("checked_at"))
                if checked and now - checked < timedelta(hours=12) and not rec.get("recheck"):
                    return
                if kind == "periodic":
                    if self.c["periodic_checks"] >= self.periodic_cap:
                        return
                    self.c["periodic_checks"] += 1
                elif kind == "vanished":
                    self.c["vanished_checks"] += 1
                self.fetch_head(key, rec)
                if kind == "periodic" and self.last_failure in REQUEUE_FAILURES:
                    self.c["periodic_checks"] -= 1     # nothing was asked: the run's quota is not used up
        except Stop:
            raise
        except Exception as e:
            log.warning("PDF %s (%s) failed: %s: %s", rec.get("url"), kind, type(e).__name__, e)

    def _mark_gone(self, rec: dict) -> None:
        """A failing check (404/410, or an HTML page instead of the file). The first one is only a
        strike: the PDF is called gone when a second check at least GONE_CONFIRM_H later fails too
        (one bad answer during a site deploy must not hide a linked PDF)."""
        if rec.get("status") == "gone":
            rec.setdefault("gone_since", now_iso())     # records marked gone before this rule existed
            return
        strike = _dt(rec.get("gone_strike_at"))
        if strike is None:
            rec["gone_strike_at"] = now_iso()
            return
        if _now() - strike < timedelta(hours=GONE_CONFIRM_H):
            return
        self.c["pdfs_gone_now"] += 1
        rec["status"] = "gone"
        rec["gone_since"] = now_iso()
        rec.pop("gone_strike_at", None)

    def _apply_head(self, rec: dict, head: dict) -> None:
        code = head.get("status")
        ctype = head.get("type") or ""
        new = {k: v for k, v in head.items() if v is not None}
        if code != 200 or "html" in ctype:
            # an error / HTML page is not the file: its Content-Length and Last-Modified must not become
            # the PDF's size and date (the date decides What's New, and after a first strike the PDF stays
            # "ok" for a day or more) — keep the file's last known ones, also through a second failing
            # check (the head an earlier error answer left holds the file's values, never the page's own)
            old = rec.get("head") or {}
            for k in ("size", "last_modified"):
                new.pop(k, None)
                if old.get(k) is not None:
                    new[k] = old[k]
        rec["head"] = new
        if code in (404, 410):
            self._mark_gone(rec)
        elif code == 200:
            if "html" in ctype and rec.get("hint"):
                rec["status"] = "not-pdf"
            elif "html" in ctype:
                self._mark_gone(rec)       # an error / sign-in page where the file used to be
            elif rec.get("hint") and ctype and "pdf" not in ctype and "octet-stream" not in ctype:
                rec["status"] = "not-pdf"
            else:
                rec["status"] = "ok"
                for k in ("hint", "gone_strike_at", "gone_since"):
                    rec.pop(k, None)
        rec.pop("recheck", None)

    def _unreachable(self, rec: dict) -> None:
        """No answer at all (DNS failure, connection refused). A PDF on another site whose host has
        stopped answering for good (4+ tries over 30+ days) is gone — a dead link helps no one. The
        magazine sites' own files are never retired this way (their outage is not the file's)."""
        head = dict(rec.get("head") or {})
        if head.get("error") == "unreachable":       # records from before this bookkeeping existed
            head.setdefault("unreachable_since", head.get("checked_at"))
        fails = int(head.get("fails") or 0) + 1
        head.update(fails=fails, error="unreachable", checked_at=now_iso(),
                    next_try=to_iso(_now() + timedelta(days=min(60, 2 ** fails))))
        head.setdefault("unreachable_since", head.get("checked_at"))
        rec["head"] = head
        if rec.get("status") == "gone":
            rec.setdefault("gone_since", now_iso())
        since = _dt(head.get("unreachable_since"))
        if (rec.get("external") and rec.get("status") != "gone" and fails >= UNREACHABLE_GONE[0]
                and since and _now() - since >= timedelta(days=UNREACHABLE_GONE[1])):
            self.c["pdfs_gone_now"] += 1
            rec["status"] = "gone"
            rec["gone_since"] = now_iso()

    def _robots_refused(self, rec: dict) -> None:
        """robots.txt does not allow this file: nothing can be learned about it, and it is NOT
        "unreachable" (no strike, never retired for it). The file's last known answer is kept; it is
        asked again after ERROR_RECHECK_DAYS["robots"]."""
        head = dict(rec.get("head") or {})
        head.update(error="robots", checked_at=now_iso(),
                    next_try=to_iso(_now() + timedelta(days=ERROR_RECHECK_DAYS["robots"])))
        rec["head"] = head
        rec.pop("recheck", None)
        self.c["pdfs_robots"] += 1

    def _no_answer(self, rec: dict) -> None:
        """request() gave no response for this PDF: what that means depends on why (last_failure)."""
        why = self.last_failure
        if why in REQUEUE_FAILURES:
            self.c["pdfs_requeued"] += 1   # nothing was asked: nothing recorded, due again next run
        elif why == "robots":
            self._robots_refused(rec)
        else:                              # no answer (twice), too many redirects
            self._unreachable(rec)

    def fetch_head(self, key: str, rec: dict) -> None:
        url = rec["url"]
        r = self.request("HEAD", url, timeout=(10, 20))
        self.c["heads"] += 1
        if r is not None and r.status_code in (403, 405, 501):
            # some servers refuse HEAD → a streamed GET that we close immediately
            r = self.request("GET", url, timeout=(10, 20), stream=True)
            if r is not None:
                r.close()
        if r is None:
            self._no_answer(rec)
            return
        self._apply_head(rec, head_from_response(r))

    def fetch_details(self, key: str, rec: dict) -> None:
        url = rec["url"]
        if rec.get("external") and _host(url) in self.dead_hosts:
            return
        self.c["details"] += 1
        max_s = max(20.0, min(120.0, self.budget.remaining() - 25))
        head, data, err, final = download_pdf(self.via, url, max_bytes=self.max_bytes, max_seconds=max_s)
        if head.get("status"):
            self._apply_head(rec, head)
        elif err == "unreachable":         # no response: why?
            why = self.last_failure
            if why in REQUEUE_FAILURES:
                self.c["details"] -= 1     # nothing was asked: due again next run
                self.c["pdfs_requeued"] += 1
                return
            if why == "robots":
                self._robots_refused(rec)
                err = "robots"
            elif rec.get("external"):
                self._unreachable(rec)
        d = dict(rec.get("details") or {})
        d["checked_at"] = now_iso()
        tries = int(d.get("attempts") or 0) + 1
        if data is not None:
            thumb_name = short_hash(key, 16) + ".webp"
            # The attempt is on record BEFORE the file is read (and saved, if the reader should take the
            # whole run down): a file that crashes or hangs the reader is skipped next time, with the
            # back-off below. A normal result replaces this right away.
            rec["details"] = {**{k: v for k, v in d.items() if k != "final" and v not in (None, "")},
                              "error": "parse: interrupted", "attempts": tries, "next_try": _backoff(tries)}
            save_state(self.st, self.dry_run)
            self.last_save = time.monotonic()
            parse_s = max(15.0, min(float(PARSE_TIMEOUT_S), self.budget.remaining() - 20))
            a = analyze_pdf_isolated(data, None if self.dry_run else THUMB_DIR / thumb_name, timeout=parse_s,
                                     memory_mb=PARSE_MEMORY_MB)
            text = clean_text(a.get("text") or "")
            page_langs = [detect_lang(clean_text(t)[:3000]) if len(clean_text(t)) >= 200 else None
                          for t in a.get("page_texts") or []]
            d.update(title=a.get("title"), pages=a.get("pages"), chars=len(text),
                     text_lang=(detect_lang(text[:3000]) if len(text) >= 200 else None),
                     page_langs=[x if x in ("en", "es", "fr") else None for x in page_langs] or None,
                     heading=R.heading_from_text(a.get("text") or ""))
            if a.get("thumb_written"):
                d["thumb"] = THUMB_URL + thumb_name
            err, final = a.get("error"), a.get("final")
            if err and err.startswith("thumb"):
                final = True       # metadata is fine; a thumbnail failure is not worth re-downloading
            if err and err.startswith("parse:"):
                self.c["parse_failed"] += 1
                log.warning("PDF %s: the PDF reader gave no result (%s) — skipped for %d day(s)", url,
                            err, min(30, 2 ** tries))
            self.c["details_ok"] += 1
        if err:
            d["error"] = err
            if final and rec.get("status") == "ok" and (err in ("http 404", "http 410") or (
                    err == "not-pdf" and "html" in (head.get("type") or ""))):
                # "not found" / an HTML page, but the PDF is not confirmed gone (_mark_gone needs two failing
                # checks a day apart; a page can link a file minutes before it is uploaded): retry with the
                # normal back-off instead of never — once it is gone, needs_details() stops asking
                final = False
            if final:
                d["final"] = True
                d.pop("next_try", None)
            else:
                d.pop("final", None)
                d["attempts"] = tries
                d["next_try"] = _backoff(tries)
        else:
            for k in ("error", "attempts", "next_try", "final"):
                d.pop(k, None)
        rec["details"] = {k: v for k, v in d.items() if v not in (None, "")}
        log.info("PDF %s -> %s%s", url, f"{d.get('pages')} p." if d.get("pages") else "no details",
                 f" ({err})" if err else "")

    # ------------------------------------------------------------------ run log
    def run_record(self) -> dict:
        return {
            "started": self.started, "minutes": round(self.budget.elapsed() / 60, 1),
            "pages_fetched": self.c["pages_fetched"], "not_modified": self.c["not_modified"],
            "page_errors": self.c["page_errors"], "discovered": self.c["pages_discovered"],
            "new_pdfs": self.c["new_pdfs"], "details": self.c["details"], "heads": self.c["heads"],
            "requests": self.c["requests"],
            **{k: self.c[k] for k in ("pruned_junk", "pruned_gone", "parse_failed", "pdfs_requeued",
                                      "robots_unavailable") if self.c[k]},
        }

    def hub_report(self) -> list[dict]:
        """The hub / kit pages (crawl_rules.HUB_PATHS — KIT_PAGES are among them) asked for in this run
        that did not give a readable page: [{"url", "status" (404, 503, "no-response", "login"…),
        "since" (when it began failing, UTC ISO)}], in HUB_PATHS order."""
        out = []
        for url in self.hubs:
            key = self.page_lc.get(url.lower(), url)
            pg = self.pages.get(key) or {}
            if key not in self.tried or not pg.get("error_since"):
                continue
            status = str(pg.get("last_error") or pg.get("status") or "error")
            out.append({"url": key, "status": int(status) if status.isdigit() else status,
                        "since": pg["error_since"]})
        return out


def run_verdict(crawler: Crawler | None) -> tuple[bool, str | None]:
    """(ok, error) of the run, for data/raw/pdfs.json. Not ok when the magazine sites gave nothing to read — so
    /status/ shows the search as failed, its "Last success" stays, and a week of it reaches the failing-sources
    report:
      * pages were asked for and none came back ("site down?"), or
      * robots.txt of a magazine site did not answer properly (5xx / 429 / no answer — the whole host stays closed,
        RFC 9309), pages of it were due, and no page at all was read: a server that is down answers robots.txt no
        better than its pages, so nothing is sent for them and the first rule cannot see it.
    A run where the robots.txt hold lifted and pages were read again stays ok (the note says what happened)."""
    if not crawler:
        return True, None
    c = crawler.c
    read = c["pages_ok"] + c["not_modified"] + c["pages_reused"]
    if c["requests"] > 3 and c["pages_ok"] == 0 and c["not_modified"] == 0 and c["pages_fetched"] > 0:
        return False, f"no page could be fetched ({c['page_errors']} errors) — site down?"
    closed = {h: p for h, p in crawler.robots_down.items() if h in R.DRUPAL_HOSTS}
    if closed and c["robots_unavailable"] > 0 and not read:
        why = ", ".join(f"{h} ({'no answer' if p == 'unreachable' else p})" for h, p in sorted(closed.items()))
        return False, f"no page could be read: robots.txt of {why} did not answer properly — site down?"
    return True, None


def run_warnings(crawler: Crawler | None, hub_problems: list[dict]) -> list[str]:
    """Plain lines for stats.warnings (the run summary's notes): hub / kit pages that did not load, and a
    magazine site whose robots.txt kept the crawl away this run."""
    out = []
    if hub_problems:
        parts = [f"{urlsplit(h['url']).hostname.removeprefix('www.')}{urlsplit(h['url']).path} "
                 f"({h['status']} since {_local_day(str(h['since']))})" for h in hub_problems]
        line = (f"{len(parts)} main page(s) of the magazine sites did not load: " + ", ".join(parts)
                + " — checked again every day")
        out.append(line if len(line) <= 200 else line[:197].rstrip(" ,") + "…")
    for host, problem in sorted((crawler.robots_down if crawler else {}).items()):
        if host in R.DRUPAL_HOSTS:
            why = "no answer" if problem == "unreachable" else problem
            out.append(f"robots.txt of {host} did not answer properly ({why}): its pages were left for the "
                       f"next run")
    return out


# ==================================================================================================
#  output: data/raw/pdfs.json
# ==================================================================================================
def _ref_rank(ref: dict, hub_set: set[str]) -> tuple:
    u = ref.get("url") or ""
    c = 0 if u in R.KIT_PAGES else 1 if u.lower() in hub_set else 3 if R.is_event_path(u) else 2
    return (c, ref.get("seen") or "")


def _item_date(upload_month: str | None, last_modified: str | None, first_seen: str | None,
               fresh: bool) -> str | None:
    """Upload month from the path (Last-Modified day when it falls in that month), else
    Last-Modified, else first_seen — but first_seen only for `fresh` PDFs (ones that appeared on a
    page we had already crawled). During the first crawl of a page first_seen says nothing about
    age, and dating old flyers "today" would flood What's New. Times (UTC) count by their day in the
    site's time zone: a file uploaded on October 31 at 8 PM Central (1 AM UTC on November 1) in the
    2026-10 folder is dated October 31, not October 1."""
    lm_day = _local_day(last_modified) if last_modified else None
    if upload_month:
        if lm_day and lm_day[:7] == upload_month:
            return lm_day
        return upload_month + "-01"
    if lm_day:
        return lm_day
    if fresh and first_seen:
        return _local_day(first_seen)
    return None


def build_items(st: dict) -> list[dict]:
    hub_set = {u.lower() for u in R.hub_urls()}
    items = []
    for key, rec in st["pdfs"].items():
        try:
            if rec.get("status") == "not-pdf":
                continue
            items.append(build_item(key, rec, st["pages"], hub_set))
        except Exception as e:  # one odd record must never break the file
            log.warning("could not build item for %s: %s: %s", key, type(e).__name__, e)
    return items


def build_item(key: str, rec: dict, pages: dict, hub_set: set[str]) -> dict:
    refs = sorted((r for r in rec.get("refs") or [] if not R.is_junk_path(urlsplit(r.get("url") or "").path)),
                  key=lambda r: _ref_rank(r, hub_set))
    ref_urls = [r["url"] for r in refs if r.get("url")]
    # Shared Drupal files are served by both hosts: link them on the host of their best referrer
    # (a La Viña flyer found on aalavina.org keeps its aalavina.org address).
    url = rec["url"]
    best_host = _host(ref_urls[0]) if ref_urls else _host(url)
    p = urlsplit(key)
    if p.hostname in R.DRUPAL_HOSTS and p.path.startswith("/sites/"):
        host = best_host if best_host in R.DRUPAL_HOSTS else _host(url)
        url = urlunsplit(("https", host, p.path, "", ""))
    # A listing page's title ("Calendario de Eventos" on /calendario-de-eventos) says nothing about a
    # PDF — also when the same page is reached through an alias that redirects to it.
    generic_titles = {r["title"] for r in refs if r.get("title") and (
        R.page_title_is_generic(r["title"], r["url"])
        or R.page_title_is_generic(r["title"], (pages.get(r["url"]) or {}).get("final") or r["url"]))}
    specific = [r for r in refs if r.get("title") and r["title"] not in generic_titles]
    det = rec.get("details") or {}
    link_langs = {lk for r in refs for t in (r.get("texts") or []) for lk in [R.language_of_link(t)] if lk}
    page_langs = {x for x in (det.get("page_langs") or []) if x}
    multilingual = len(page_langs) >= 2 or R.is_multilingual(
        link_langs=link_langs, heading=det.get("heading"),
        page_titles=[r.get("title") or "" for r in refs] + [r.get("section") or "" for r in refs])
    texts: list[str] = []
    made_lang: dict[str, str] = {}      # "<name> (Spanish)" built below → the language of <name>
    for r in refs:
        page_lang = "es" if _host(r.get("url") or "") in R.SPANISH_HOSTS else "en"
        for t in r.get("texts") or []:
            lk = R.language_of_link(t)
            if lk and multilingual:
                # "Spanish" / "French and Spanish" links to ONE file holding several languages: the
                # link names no single language, so it adds nothing to the title
                continue
            if lk:
                # a link named just "Spanish" / "leer en Inglés": the page (or file) names the document
                if r in specific:      # page title, written in the page's language
                    base, base_lang = r["title"], R.title_language(r["title"], page_lang)
                else:                  # file name, most likely written in the document's language
                    base = R.strip_lang_tokens(R.title_from_filename(url))
                    base_lang = R.title_language(base, lk if lk in ("en", "es") else page_lang)
                made = f"{base} ({R.language_label(lk, base_lang)})"
                made_lang.setdefault(R.clean_link_text(made) or made, base_lang)
                texts.append(made)
            else:
                texts.append(t)
    alts = [t for r in refs for t in (r.get("alts") or [])]
    sections = [r.get("section") or "" for r in refs if r.get("section")]
    head = rec.get("head") or {}
    event_refs = [r for r in refs if R.is_event_path(r.get("url") or "")]
    only_events = bool(refs) and len(event_refs) == len(refs)
    # a specific (non-listing) page that links only this PDF usually names it well
    single = next((r for r in specific if not R.is_event_path(r["url"])
                   and len((pages.get(r["url"]) or {}).get("pdfs") or []) == 1), None)
    title, src = R.choose_title(link_texts=texts, img_alts=alts, meta_title=det.get("title"),
                                text_heading=det.get("heading"), url=url,
                                event_title=(event_refs[0].get("title") if only_events else None),
                                page_title=single["title"] if single else None)
    host_prior = "es" if best_host in R.SPANISH_HOSTS else "en"
    link_text = next((c for t in [*texts, *alts] for c in [R.clean_link_text(t)] if c), None)
    doc_lang = R.doc_language(url=url, texts=[*texts, *alts, title], text_sample=None,
                              text_lang=det.get("text_lang"), host_prior=host_prior,
                              multilingual=multilingual, heading=det.get("heading"), link_text=link_text)
    # The title's language (what the translator translates from): a link text, image alt or page /
    # event title is written in the REFERRING PAGE's language; metadata, a page-1 heading or the file
    # name in the document's. (French documents: their titles are judged with the page language as
    # prior; real French words still win.)
    title_prior = host_prior if src in ("link", "alt", "page", "event") else (
        doc_lang if doc_lang in ("en", "es") else host_prior)
    title_prior = made_lang.get(title, title_prior)
    override = R.TITLE_OVERRIDES.get(R.filename_of(url))
    if override:
        title, title_prior = override, (doc_lang if doc_lang in ("en", "es") else host_prior)
    lang = R.title_language(title, title_prior)
    if doc_lang != lang and doc_lang in ("en", "es", "fr") and not multilingual \
            and not R.lang_from_markers([title]):
        # e.g. an English title for the Spanish edition → "… (Spanish)", so readers know
        title = f"{title} ({R.language_label(doc_lang, lang)})"
    category, tags = R.classify(referrer_urls=ref_urls, texts=[title, *texts, *alts], sections=sections, url=url)
    um = R.upload_month_of(url)
    thumb = det.get("thumb")
    if thumb and not (THUMB_DIR / thumb.rsplit("/", 1)[-1]).exists():
        thumb = None
    event_dates = sorted({R.event_date_of(r["url"]) for r in event_refs if r.get("url")})
    seen_titles: set[str] = set()
    out_refs = []
    for r in refs:
        t = r.get("title") or urlsplit(r["url"]).path
        sig = (_host(r["url"]), t.lower())
        if sig in seen_titles:
            continue
        seen_titles.add(sig)
        out_refs.append({"url": r["url"], "title": t})
        if len(out_refs) >= 5:
            break
    link_texts = []
    for t in texts:
        c = R.clean_link_text(t)
        if c and c not in link_texts:
            link_texts.append(c)
    extra = {
        "host": _host(url),
        "file_url": url,
        "filename": R.filename_of(url),
        "size_bytes": head.get("size") if head.get("status") == 200 else None,
        "pages": det.get("pages"),
        "thumb": thumb,
        "referrers": out_refs,
        "upload_month": um,
        "link_texts": link_texts[:3],
        "event_date": event_dates[-1] if event_dates else None,
        "doc_lang": doc_lang,
        "multilingual": multilingual or None,
        "section": sections[0] if sections else None,
        "external": bool(rec.get("external")),
        "orphan": not refs,
    }
    item = make_item(id=f"pdf:{short_hash(key, 12)}", source="crawl", kind="pdf", url=url, title=title,
                     summary="", lang=lang, date=_item_date(um, head.get("last_modified"), rec.get("first_seen"),
                                                                bool(rec.get("fresh"))),
                     image=thumb, tags=tags, category=category, extra=extra,
                     status="gone" if rec.get("status") == "gone" else "ok")
    item["first_seen"] = rec.get("first_seen")
    return item


def crawl_stats(st: dict, crawler: Crawler | None, pages_per_run: float) -> dict:
    pages = st["pages"]
    eligible = {u: p for u, p in pages.items() if R.should_crawl_path(urlsplit(u).path)}
    crawled = [u for u, p in eligible.items() if p.get("crawled_at")]
    never = [u for u, p in eligible.items() if not p.get("crawled_at")]
    never_events = sum(1 for u in never if R.is_event_path(u))
    pdf_status = Counter(r.get("status") or "ok" for r in st["pdfs"].values())
    with_details = sum(1 for r in st["pdfs"].values() if (r.get("details") or {}).get("pages"))
    with_thumbs = sum(1 for r in st["pdfs"].values() if (r.get("details") or {}).get("thumb"))
    c = crawler.c if crawler else Counter()
    queue_remaining = len(never)
    if crawler:
        queue_remaining = len({u for _p, u in crawler.page_q if u not in crawler.done_pages})
    return {
        "known_pages": len(eligible),
        "crawled_pages": len(crawled),
        "never_crawled": len(never),
        "never_crawled_events": never_events,
        "pdfs": pdf_status.get("ok", 0),
        "pdfs_gone": pdf_status.get("gone", 0),
        "pdfs_with_details": with_details,
        "pdfs_with_thumbs": with_thumbs,
        "last_run_pages": c["pages_fetched"],
        "fetched": c["pages_fetched"],
        "reused": c["pages_reused"] + c["sitemap_reused"],   # read by an earlier module this run (no request)
        "new": c["new_pdfs"],
        "not_modified": c["not_modified"],
        "page_errors": c["page_errors"],
        "discovered": c["pages_discovered"],
        "details": c["details"],
        "heads": c["heads"],
        "requests": c["requests"],
        "pruned_pages": c["pruned_junk"] + c["pruned_gone"],   # forgotten this run (Crawler.prune)
        "queue_remaining": queue_remaining,
        "est_days_to_full": round(len(never) / pages_per_run, 1) if pages_per_run > 0 else None,
    }


def _pages_per_run(st: dict, cfg_minutes: float) -> float:
    """Typical page fetches per daily run (recent history, else estimated from the time budget)."""
    runs = [r for r in st.get("runs", [])[-10:] if r.get("minutes", 0) >= 0.75 * cfg_minutes and r.get("pages_fetched")]
    if runs:
        return sum(r["pages_fetched"] for r in runs) / len(runs)
    return cfg_minutes * 60 / 5.2 * (1 - PDF_TIME_SHARE)


# merge_items() keeps an old value when the new one is empty. For these fields "empty" is today's
# truth from the crawl state (thumbnail file deleted, no page links the PDF any more, the event page
# is gone), so the freshly built value is put back after the merge.
FRESH_EXTRA_KEYS = ("thumb", "referrers", "event_date", "orphan", "section", "link_texts")


def reapply_fresh_fields(merged: list[dict], fresh_items: list[dict]) -> None:
    fresh = {it["id"]: it for it in fresh_items}
    for it in merged:
        f = fresh.get(it["id"])
        if f is None:
            continue
        it["image"] = f.get("image")
        ex, fx = it.setdefault("extra", {}), f.get("extra") or {}
        for k in FRESH_EXTRA_KEYS:
            ex[k] = fx.get(k)


def _last_seen_changed(current: str | None, on_page: str) -> bool:
    """Copy the crawl's last_seen_on_page into the item only when it moves back in time or by at
    least a week, so PDFs linked from pages visited daily don't change pdfs.json every day."""
    cur, new = parse_iso(current), parse_iso(on_page)
    if cur is None or new is None:
        return True
    return new < cur or new - cur >= timedelta(days=7)


# ==================================================================================================
#  CLI
# ==================================================================================================
def main(argv=None) -> None:
    cfg = (load_config().get("sources") or {}).get("crawler") or {}
    ap = argparse.ArgumentParser(prog="python -m scripts.sync.crawl", description=__doc__.split("\n")[0])
    ap.add_argument("--minutes", type=float, default=float(cfg.get("minutes_per_run", 40)),
                    help="crawl time budget (0 = no network, just rebuild pdfs.json from state)")
    ap.add_argument("--details", type=int, default=int(cfg.get("pdf_details_per_run", 25)),
                    help="max PDFs to download for page count / title / thumbnail this run")
    ap.add_argument("--max-pages", type=int, default=None, help="stop after fetching this many pages (testing)")
    ap.add_argument("--recheck-days", type=int, default=int(cfg.get("recheck_days", 21)))
    ap.add_argument("--max-mb", type=float, default=float(cfg.get("pdf_max_mb", 20)))
    ap.add_argument("--url", action="append", default=[], help="crawl only this page (repeatable; debugging)")
    ap.add_argument("--no-sitemap", action="store_true", help="skip the sitemap refresh")
    ap.add_argument("--dry-run", action="store_true", help="crawl but write nothing (prints a sample)")
    args = ap.parse_args(argv)

    # data/raw/pdfs.json first: one that cannot be read stops the run here (common.UnreadableRaw) — before forty
    # minutes of crawling whose result could not be saved
    prev = load_raw(SOURCE)
    st, loaded_ok = load_state()
    crawler = None
    interrupted = None
    if args.minutes > 0:
        crawler = Crawler(st, minutes=args.minutes, details_cap=args.details, recheck_days=args.recheck_days,
                          max_mb=args.max_mb, max_pages=args.max_pages, dry_run=args.dry_run,
                          only_urls=args.url, use_sitemap=not args.no_sitemap)

        def _on_term(signum, _frame):
            raise Stop(f"signal {signum}")
        old_term = None
        try:
            old_term = signal.signal(signal.SIGTERM, _on_term)
        except (ValueError, OSError, AttributeError):   # not main thread / platform without SIGTERM
            pass
        try:
            crawler.run()
        except (KeyboardInterrupt, Stop) as e:
            interrupted = type(e).__name__
            log.warning("interrupted (%s) — saving progress", interrupted)
        finally:
            if old_term is not None:
                try:
                    signal.signal(signal.SIGTERM, old_term)
                except (ValueError, OSError):
                    pass
        runs = st.setdefault("runs", [])
        runs.append({**crawler.run_record(), **({"interrupted": interrupted} if interrupted else {})})
        del runs[:-30]

    items = build_items(st)
    merged, _added = merge_items(prev.get("items", []), items, drop_missing=loaded_ok)
    reapply_fresh_fields(merged, items)
    last_seen = {f"pdf:{short_hash(k, 12)}": r.get("last_seen_on_page") for k, r in st["pdfs"].items()}
    for it in merged:
        ls = last_seen.get(it["id"])
        if ls and _last_seen_changed(it.get("last_seen"), ls):
            it["last_seen"] = ls
    stats = crawl_stats(st, crawler, _pages_per_run(st, float(cfg.get("minutes_per_run", 40))))
    # hub / kit pages that did not load this run (the run summary reads `hub_problems` from the envelope)
    hub_problems = crawler.hub_report() if crawler else []
    warnings = run_warnings(crawler, hub_problems)
    if warnings:
        stats["warnings"] = warnings
    ok, error = run_verdict(crawler)
    if args.dry_run:
        log.info("dry run: nothing written")
        for it in merged[:8]:
            log.info("  %s | %s | %s | %s | %s", it["category"], it["lang"], it["date"], it["title"], it["url"])
    else:
        if crawler is not None or not loaded_ok:
            # `--minutes 0` only rebuilds pdfs.json: the state it read is unchanged, so it is not
            # rewritten (no git churn, no clash with the daily bot's copy) — unless it was just
            # recovered from pdfs.json, which must be kept.
            save_state(st)
        save_raw(SOURCE, merged, ok=ok, error=error, stats=stats,
                 extra={"crawl": {k: stats[k] for k in ("known_pages", "crawled_pages", "pdfs", "last_run_pages")},
                        "hub_problems": hub_problems})
    print_summary(stats, crawler, len(merged))


def print_summary(stats: dict, crawler: Crawler | None, n_items: int) -> None:
    lines = ["", "PDF crawl summary", "-----------------"]
    if crawler:
        c = crawler.c
        lines += [
            f"  time used              : {crawler.budget.elapsed() / 60:.1f} min of {crawler.budget.limit / 60:.1f}",
            f"  pages fetched          : {c['pages_fetched']} (ok {c['pages_ok']}, not modified {c['not_modified']}, "
            f"errors {c['page_errors']}, gone {c['pages_gone']}); reused from earlier modules: "
            f"{c['pages_reused']} page(s), {c['sitemap_reused']} sitemap(s)",
            f"  new pages discovered   : {c['pages_discovered']}  (sitemap: {c['sitemap_urls']} URLs, {c['sitemap_new']} new)",
            f"  PDF downloads (details): {c['details']} (ok {c['details_ok']}), HEAD checks: {c['heads']} "
            f"(vanished {c['vanished_checks']}, periodic {c['periodic_checks']})",
            f"  new PDFs this run      : {c['new_pdfs']}   total requests: {c['requests']}",
            f"  pages pruned           : {c['pruned_junk']} junk, {c['pruned_gone']} long gone;  first 404s "
            f"(links kept): {c['pages_gone_strikes']}",
            f"  PDF checks left for the next run: {c['pdfs_requeued']} (hosts without answer: "
            f"{', '.join(sorted(crawler.dead_hosts)) or 'none'}; robots.txt unavailable: "
            f"{', '.join(f'{h} ({p})' for h, p in sorted(crawler.robots_down.items())) or 'none'}); "
            f"PDF reader failures: {c['parse_failed']}",
        ]
    lines += [
        f"  PDFs in library        : {stats['pdfs']} ok, {stats['pdfs_gone']} gone ({n_items} items; "
        f"{stats['pdfs_with_details']} with details, {stats['pdfs_with_thumbs']} thumbnails)",
        f"  pages known / crawled  : {stats['known_pages']} / {stats['crawled_pages']} "
        f"(never crawled: {stats['never_crawled']}, of which events {stats['never_crawled_events']})",
        f"  queue remaining (due)  : {stats['queue_remaining']}",
        f"  est. days to full scan : {stats['est_days_to_full']}",
        *[f"  note: {w}" for w in stats.get("warnings") or []],
        "",
    ]
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    raise SystemExit(run_module(SOURCE, main))
