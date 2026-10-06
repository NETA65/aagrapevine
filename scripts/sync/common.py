"""Shared helpers for the content-sync pipeline.

Every sync module (drive.py, youtube.py, …) uses:
  * CONFIG / load_config()          – config/site.yml
  * PoliteSession                   – requests with UA, robots.txt, per-server crawl-delay, retries,
                                      and a per-run page memo (a magazine page is asked for once per run)
  * load_raw() / save_raw()         – data/raw/<source>.json envelope (see docs/DATA_SCHEMA.md); save_raw
                                      holds back a sudden mass drop of items until the next run confirms it
  * merge_items()                   – cumulative merge that preserves first_seen and never drops items
                                      (authoritative=True for sources that are their own full truth)
  * detect_lang(), clean_text(), date helpers
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import sys
import time
import unicodedata
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import requests
import yaml

try:
    from protego import Protego
except Exception:  # pragma: no cover
    Protego = None

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "site.yml"
RAW_DIR = ROOT / "data" / "raw"
SITE_DIR = ROOT / "data" / "site"
STATE_DIR = ROOT / "data" / "state"
TRANSLATIONS_DIR = ROOT / "data" / "translations"
CACHE_ASSETS = ROOT / "src" / "assets" / "cache"  # committed thumbnails (pdf/, ig/)
CONTENT_DIR = ROOT / "content"
MODELS_DIR = Path(os.environ.get("GV_MODELS_DIR", ROOT / ".cache" / "models"))

for _d in (RAW_DIR, SITE_DIR, STATE_DIR, TRANSLATIONS_DIR, CACHE_ASSETS):
    _d.mkdir(parents=True, exist_ok=True)

# Host names served by ONE server. PoliteSession spaces requests per server, so the magazine sites'
# Crawl-delay (5 s) holds across both of them for every module sharing shared_session().
SAME_SERVER_HOSTS = {h: "aagrapevine.org+aalavina.org" for h in (
    "www.aagrapevine.org", "aagrapevine.org", "www.aalavina.org", "aalavina.org")}

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)


# --------------------------------------------------------------------------- logging
def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s %(name)-12s %(levelname)-7s %(message)s", "%H:%M:%S"))
        log.addHandler(h)
        log.setLevel(os.environ.get("GV_LOG_LEVEL", "INFO"))
        log.propagate = False
    return log


# --------------------------------------------------------------------------- config
_CONFIG: dict | None = None


def load_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _CONFIG = yaml.safe_load(f) or {}
    return _CONFIG


# --------------------------------------------------------------------------- time
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def to_iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.isoformat()


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return datetime.fromisoformat(s + "T12:00:00+00:00")
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def site_tz() -> ZoneInfo:
    """The site's time zone: config site.timezone (Central when it is missing or unknown)."""
    try:
        return ZoneInfo(str((load_config().get("site") or {}).get("timezone") or "America/Chicago"))
    except Exception:  # noqa: BLE001 — an unknown name, no settings file
        return ZoneInfo("America/Chicago")


def site_day(when: str | datetime | None = None, tz: ZoneInfo | None = None) -> str:
    """The calendar day ('YYYY-MM-DD') of a moment in the site's time zone (Central) — not the UTC day, which
    is already tomorrow after about 7 PM Central. `when`: an ISO time ('…Z', with an offset; without one it is
    UTC, as now_iso() writes), a datetime, or None for now. A date alone ('YYYY-MM-DD') is that day; text that
    is not a time is None's day (now)."""
    tz = tz or site_tz()
    if isinstance(when, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", when.strip()):
        return when.strip()
    dt = when if isinstance(when, datetime) else None
    if isinstance(when, str):
        try:
            dt = datetime.fromisoformat(when.strip().replace("Z", "+00:00"))
        except ValueError:
            dt = None
    dt = dt or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date().isoformat()


MONTHS = {
    # English
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
    "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    # Spanish
    "enero": 1, "ene": 1, "febrero": 2, "marzo": 3, "abril": 4, "abr": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "ago": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12, "dic": 12,
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                "November", "December")

# Dates written with numbers only: "14-03-2027" can only be day-month-year (there is no 14th month), "03-14-2027"
# only month-day-year; "05-10-2026" can be either. Those are read day first when the name is in Spanish ("Taller
# 05-10-2026" is 5 October), month first when it is in English (as in the US), and month first with a note
# (`notes` / take_date_notes) when its words do not tell — so the chair can write it year-month-day instead. The
# site is English and Spanish: no other language reads the day first (a French-looking "ET" / "EST" is a time zone).
_DAY_FIRST_LANGS = ("es",)
_RANGE_MAX_DAYS = 62                     # "March 14 - 16, 2027": a range longer than this is not one event's days
_ORD = r"(?:st|nd|rd|th)?"
_SEP = r"\s*(?:[-–—]|\b(?:to|through|thru|until|al|a|hasta)\b)\s*"          # "14 - 16", "14 al 16", "14 to 16"
_FROM = r"(?:\b(?:from|desde|del)\s+)?"                                         # "del 14 al 16 de marzo de 2027"
_YEAR_END = r",?\s+(?:de\s+|del\s+)?(20\d{2})\b"
# A number right after one of these words counts something ("Distrito 7 - 14 de marzo de 2027" is the 14th, not
# the 7th to the 14th): a range written with a dash after it is not read as one.
_COUNTED = re.compile(r"(?i)(?:\b(?:distrito|district|panel|grupo|group|[aá]rea|paso|pasos|step|steps|tradici[oó]n|"
                      r"tradiciones|tradition|traditions|concepto|concept|n[oº]|n[uú]m|number|n[uú]mero|part|parte|"
                      r"session|sesi[oó]n|week|semana|lesson|lecci[oó]n|chapter|cap[ií]tulo|vol|volume|volumen|"
                      r"unit|unidad|module|m[oó]dulo)\.?|#)\s*$")
# The magazines' names say nothing about the language of the words around a date ("La Viña Report 05-10-2026" is
# English): _text_lang leaves them out, as drive.py does for a file's language.
_PUB_NAMES = re.compile(r"(?i)\b(?:aa\s+)?(?:grapevine|la\s+vi[ñn]a)\b")
# Nor do a time zone's letters ("7pm ET" — "et" / "est" are French words), the place after "@" ("… 7pm @ Grupo Solo
# por Hoy, Tyler") or a group's or a town's own name written in the name ("… - Grupo Progreso Latino, Duncanville",
# "… El Paso"): an English name that names a Spanish-named group or town stays English. A group's or a town's name
# that STARTS the text is its subject, not a place ("Grupo de Escritura 05-10-2026"), and is kept.
_ZONE_LETTERS = re.compile(r"\b[ECMP][SD]?T\b")                     # ET EST EDT · CT CST CDT · MT … · PT PST PDT
_AT_PLACE = re.compile(r"@.*", re.S)
_LINK = r"(?:de|del|la|las|los|el|por|en|y|al|of|the|and)"
_CAPITAL_WORD = r"[A-ZÁÉÍÓÚÑÜ0-9][\w'’.]*"
_NAMED_PLACE = re.compile(rf"\b(?:[Gg]rupo|GRUPO)\s+(?:{_LINK}\s+)*{_CAPITAL_WORD}"
                          rf"(?:\s+(?:{_LINK}\s+)*{_CAPITAL_WORD})*"
                          rf"|\b(?:El|La|Las|Los|Del)\s+[A-ZÁÉÍÓÚÑÜ][\w'’.]*")

# Notes about dates that could be read two ways, for callers that pass no `notes` list (drive.py's names): the
# module that saves the source takes them with take_date_notes() into its stats["warnings"] (→ /status/).
_DATE_NOTES: list[str] = []


def _md(mo: int, d: int) -> str:
    return f"{_MONTH_NAMES[mo - 1]} {d}"


def _note(notes: list[str] | None, msg: str) -> None:
    target = _DATE_NOTES if notes is None else notes
    if msg not in target:
        target.append(msg)


def take_date_notes() -> list[str]:
    """The notes date_from_text() made since the last call for callers without a `notes` list (each once, in
    order) — and forget them, so the next module of the same run starts empty."""
    out = list(_DATE_NOTES)
    _DATE_NOTES.clear()
    return out


def _text_lang(text: str, lang: str | None) -> str:
    """The language a numbers-only date in `text` is written in: the caller's when it knows it, else the
    language of the words around the date — the magazines' names, a time zone's letters and the places named
    left out (_PUB_NAMES, _ZONE_LETTERS, _AT_PLACE, _NAMED_PLACE) — and only when they clearly tell: Spanish or
    English words alone, or two more of one than of the other ("Taller …" → "es", "Writing Workshop …" → "en");
    "und" otherwise ("La Viña Report …", "Sober Workshop … - Grupo X": read month first, with a note)."""
    if lang:
        return lang[:2].lower()
    t = _ZONE_LETTERS.sub(" ", _AT_PLACE.sub(" ", _PUB_NAMES.sub(" ", text)))

    def place(m: re.Match) -> str:     # (only a date or punctuation before it: the name's subject — kept)
        return m[0] if not t[: m.start()].strip(" -–—_.,·|:;([0123456789/") else " "
    es, en, _fr = _lang_scores(_NAMED_PLACE.sub(place, t))
    if es > en and (not en or es - en >= 2):
        return "es"
    if en > es and (not es or en - es >= 2):
        return "en"
    return "und"


def _numeric(m: re.Match, text: str, lang: str | None) -> tuple[date, None, str | None]:
    """'14-03-2027' / '03-14-2027' / '05-10-2026' → (the day, no end, a note when it could be read two ways:
    both numbers 12 or less in a name whose language does not tell — read month first, as before)."""
    a, b, y = int(m[1]), int(m[2]), int(m[3])
    if a > 12 >= b:
        return date(y, b, a), None, None                      # 14-03-2027: day first
    if a > 12 or b > 12 or a == b:
        return date(y, a, b), None, None                      # 03-14-2027: month first (both > 12 → ValueError)
    words = _text_lang(text, lang)
    if words in _DAY_FIRST_LANGS:
        return date(y, b, a), None, None                      # "Taller 05-10-2026": 5 October
    if words == "en":
        return date(y, a, b), None, None                      # "Writing Workshop 05-10-2026": May 10
    alt = date(y, b, a)
    where = "" if clean_text(text) == m[0] else f"“{clean_text(text)}”: "
    note = (f"{where}“{m[0]}” could be {_md(a, b)} or {_md(b, a)}, {y} — read as {_md(a, b)} (month first). "
            f"Write the date year-month-day ({date(y, a, b).isoformat()} or {alt.isoformat()}) to be sure")
    return date(y, a, b), None, note


def _counted_before(m: re.Match, text: str) -> bool:
    return bool(_COUNTED.search(text[: m.start(1)]))


def _ymd(m: re.Match, text: str, _lang) -> tuple[date, None, None]:
    """'2027-03-14' / '2027.03.14' / '2027_03_14' / '2027 03 14' — the same mark twice (a year written in words and
    then a time is no date: "October 17, 2026 7-9 PM", "March 14 2027 6.30 PM"; nor "2027 6 30 PM")."""
    if m[2] == " " and re.match(r"\s*[ap]\.?\s?m\b", text[m.end():], re.I):
        raise ValueError("a time of day")
    return date(int(m[1]), int(m[3]), int(m[4])), None, None


def _day_range(m: re.Match, text: str, _lang) -> tuple[date, date, None] | None:
    """'14 - 16 de marzo de 2027' / 'del 14 al 16 de marzo' / '14-16 March 2027' → (14 March, 16 March)."""
    if re.fullmatch(r"\s*[-–—]\s*", m[2]) and _counted_before(m, text):
        return None
    y, mo = int(m[5]), MONTHS[m[4].lower()]
    return date(y, mo, int(m[1])), date(y, mo, int(m[3])), None


# (pattern, reader): a reader gives (start, end or None, a note or None), or None / ValueError for "not a date
# here" (the next pattern is tried). The ranges come before the single dates they contain, so "March 30 - April 2,
# 2027" starts on March 30 (not April 2) and "14 - 16 de marzo de 2027" on the 14th (not the 16th).
_DATE_PATS: list[tuple[re.Pattern, Any]] = [
    (re.compile(r"(?<!\d)(20\d{2})([-._ ])(\d{1,2})\2(\d{1,2})(?!\d)"), _ymd),
    (re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
     lambda m, t, lang: (date(int(m[1]), int(m[2]), int(m[3])), None, None)),
    (re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})(?!\d)"), _numeric),
    # "March 30 - April 2, 2027", "Oct. 30 – Nov. 1, 2026"
    (re.compile(rf"(?i){_FROM}\b({_MONTH_RE})\.?\s+(\d{{1,2}}){_ORD}{_SEP}({_MONTH_RE})\.?\s+(\d{{1,2}}){_ORD}{_YEAR_END}"),
     lambda m, t, lang: (date(int(m[5]) - (MONTHS[m[1].lower()] > MONTHS[m[3].lower()]), MONTHS[m[1].lower()],
                              int(m[2])), date(int(m[5]), MONTHS[m[3].lower()], int(m[4])), None)),
    # "March 14 - 16, 2027", "March 14-16 2027", "marzo 14 al 16, 2027"
    (re.compile(rf"(?i){_FROM}\b({_MONTH_RE})\.?\s+(\d{{1,2}}){_ORD}{_SEP}(\d{{1,2}}){_ORD}{_YEAR_END}"),
     lambda m, t, lang: (date(int(m[4]), MONTHS[m[1].lower()], int(m[2])),
                         date(int(m[4]), MONTHS[m[1].lower()], int(m[3])), None)),
    # "30 de marzo al 2 de abril de 2027", "30 March - 2 April 2027"
    (re.compile(rf"(?i){_FROM}\b(\d{{1,2}})\s+(?:de\s+)?({_MONTH_RE})\.?{_SEP}(\d{{1,2}})\s+(?:de\s+)?({_MONTH_RE})\.?"
                rf"{_YEAR_END}"),
     lambda m, t, lang: (date(int(m[5]) - (MONTHS[m[2].lower()] > MONTHS[m[4].lower()]), MONTHS[m[2].lower()],
                              int(m[1])), date(int(m[5]), MONTHS[m[4].lower()], int(m[3])), None)),
    # "14 - 16 de marzo de 2027", "del 14 al 16 de marzo de 2027", "14-16 March 2027"
    (re.compile(rf"(?i){_FROM}\b(\d{{1,2}})({_SEP})(\d{{1,2}})\s+(?:de\s+)?({_MONTH_RE})\.?{_YEAR_END}"), _day_range),
    (re.compile(rf"(?i)\b({_MONTH_RE})\.?\s+(\d{{1,2}}){_ORD},?\s+(20\d{{2}})\b"),
     lambda m, t, lang: (date(int(m[3]), MONTHS[m[1].lower()], int(m[2])), None, None)),
    # "14 de marzo de 2027", "14 March 2027", "2nd March 2027", "1° / 1º / 1.º / 1ro de marzo de 2027"
    (re.compile(rf"(?i)\b(\d{{1,2}})(?:st|nd|rd|th|ro|er|o|\.?\s?[°º])?\.?\s+(?:de\s+)?({_MONTH_RE})\.?,?\s+"
                rf"(?:de\s+|del\s+)?(20\d{{2}})\b"),
     lambda m, t, lang: (date(int(m[3]), MONTHS[m[2].lower()], int(m[1])), None, None)),
    # "primero de marzo de 2027": the 1st, written out
    (re.compile(rf"(?i)\bprimer[oa]?\s+(?:de\s+)?({_MONTH_RE})\.?,?\s+(?:de\s+|del\s+)?(20\d{{2}})\b"),
     lambda m, t, lang: (date(int(m[2]), MONTHS[m[1].lower()], 1), None, None)),
    # a month alone ("March 2027", "marzo de 2027"): its 1st — a date without its day (date_has_day)
    (re.compile(rf"(?i)\b({_MONTH_RE})\.?,?\s+(?:de\s+|del\s+)?(20\d{{2}})\b"),
     lambda m, t, lang: (date(int(m[2]), MONTHS[m[1].lower()], 1), None, None)),
]
# the patterns of ONE whole day (no range, not a month alone): a second one after a dash is the end of a range
# ("2027-03-14 - 2027-03-16", "March 14, 2027 – March 16, 2027")
_DAY_PATS = [_DATE_PATS[i] for i in (0, 1, 2, 7, 8, 9)]
_MONTH_ALONE = _DATE_PATS[-1]
_SEP_RX = re.compile(rf"(?i){_SEP}")


def date_range_from_text(text: str, lang: str | None = None,
                         notes: list[str] | None = None) -> tuple[str | None, str | None, str]:
    """Find a date — or a range of days — inside a file name / title.

    Returns (start_or_None, end_or_None, text_without_the_dates). Recognizes:
      2026-10-05, 2026.10.05, 2026_10_05, 20261005, 14-03-2027, 03/14/2027, 05-10-2026 (see _numeric),
      "Oct 5 2026", "October 5, 2026", "5 de octubre de 2026", "1° de marzo de 2027", "March 2026" (→ 2026-03-01,
      no end — date_has_day tells it apart), and ranges: "March 14 - 16, 2027", "March 30 - April 2, 2027",
      "14 al 16 de marzo de 2027", "30 de marzo al 2 de abril de 2027", "2027-03-14 - 2027-03-16" (end = the last
      day; None for one day).
    `lang`: the language of the text when the caller knows it ("es": numbers-only dates are day first);
    else the text's own words decide. `notes`: a list that gets a line for a date that could be read two
    ways ("05-10-2026" in an English or unknown-language name); without one the line is kept for
    take_date_notes()."""
    found = _find_date(text, lang, notes)
    return found[:3] if found else (None, None, text)


def date_has_day(text: str, lang: str | None = None) -> bool | None:
    """Whether the date date_range_from_text() finds in `text` names its day: False for a month alone ("March
    2027", "marzo de 2027" — read as the 1st), True for every other date ("1° de marzo de 2027" too), None when
    there is no date. Makes no note."""
    found = _find_date(text, lang, [])
    return None if not found else not found[3]


def _find_date(text: str, lang: str | None, notes: list[str] | None) -> tuple[str, str | None, str, bool] | None:
    """(start, end or None, the rest of the text, read from a month alone) of the first date in `text`, or None."""
    t = text or ""
    for rx, read in _DATE_PATS:
        m = rx.search(t)
        if not m:
            continue
        try:
            got = read(m, t, lang)
        except (ValueError, KeyError):
            continue
        if not got:
            continue
        start, end, note = got
        stop = m.end()
        if end is not None and not start < end <= start + timedelta(days=_RANGE_MAX_DAYS):
            continue                     # "March 16 - 14, 2027", "14 - 3 de marzo": not a range of days
        if end is None and (rx, read) in _DAY_PATS:
            sm = _SEP_RX.match(t, stop)
            for rx2, read2 in _DAY_PATS if sm else ():
                m2 = rx2.match(t, sm.end())
                try:
                    got2 = read2(m2, t, lang) if m2 else None
                except (ValueError, KeyError):
                    got2 = None
                if got2 and start < got2[0] <= start + timedelta(days=_RANGE_MAX_DAYS):
                    end, stop = got2[0], m2.end()
                    note = note or got2[2]
                    break
        if note:
            _note(notes, note)
        rest = (t[: m.start()] + " " + t[stop:]).strip(" -_.,·|")
        return (start.isoformat(), (end.isoformat() if end else None), re.sub(r"\s{2,}", " ", rest).strip(),
                (rx, read) == _MONTH_ALONE)
    return None


def date_from_text(text: str, lang: str | None = None, notes: list[str] | None = None) -> tuple[str | None, str]:
    """Find a date inside a file name / title → (iso_date_or_None, text_without_the_date). Every form
    date_range_from_text() reads; a range of days gives its FIRST day (and the whole range leaves the text)."""
    start, _end, rest = date_range_from_text(text, lang, notes)
    return start, rest


# --------------------------------------------------------------------------- text
_WS = re.compile(r"\s+")


def clean_text(s: Any) -> str:
    if s is None:
        return ""
    s = html.unescape(str(s))
    s = s.replace(" ", " ").replace(" ", " ").replace("​", "")
    return _WS.sub(" ", s).strip()


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return clean_text(s)


def truncate(s: str, n: int = 400) -> str:
    s = clean_text(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",;:.- ") + "…"


def pretty_filename(name: str) -> str:
    """'GV_Catalog_2026-final (1).pdf' → 'GV Catalog 2026 final'."""
    base = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", name)
    base = re.sub(r"\s*\(\d+\)\s*$", "", base)
    base = re.sub(r"[_]+", " ", base)
    base = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", base)
    base = re.sub(r"%20", " ", base)
    base = re.sub(r"\s{2,}", " ", base).strip(" -.")
    return base


def slugify(s: str, maxlen: int = 80) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "item"


def short_hash(s: str, n: int = 12) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


# --------------------------------------------------------------------------- who holds an event
# config/site.yml `recurring_events:` → `host:` and a content/events file's `host:`: our committee ("neta", the
# default), or Grapevine / La Viña themselves ("gv" / "lv": THEIR event, which the site shares — the pages show it
# with the Grapevine / La Viña calendars and in that magazine's colour, never as a NETA 65 event). Hand-written,
# so capitals, accents and the long names count too.
EVENT_HOSTS = {"neta": "neta", "neta65": "neta", "neta 65": "neta", "committee": "neta", "comite": "neta",
               "lv": "lv", "la vina": "lv", "lavina": "lv", "gv": "gv", "grapevine": "gv", "aa grapevine": "gv"}


def event_host(v: Any) -> str | None:
    """'lv' / 'La Viña' / 'GV' / 'Grapevine' / 'NETA 65' → "lv" / "gv" / "neta"; nothing given → "neta"; None
    for a value that is not understood (the caller tells the chair)."""
    s = unicodedata.normalize("NFKD", clean_text(v)).encode("ascii", "ignore").decode().lower().strip()
    return EVENT_HOSTS.get(re.sub(r"\s+", " ", s)) if s else "neta"


# --------------------------------------------------------------------------- language detection
_ES_WORDS = set("""el la los las de del que y en un una por para con es su sus al lo como más pero le ya o este sí porque
esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso
ante ellos esto mí antes algunos qué unos yo otro otras otra él tanto esa estos mucho quienes nada muchos cual poco ella estar
estas algunas algo nosotros mi mis tú te ti tu tus somos soy fue era mujer hombre vida día días año años grupo grupos reunión
reuniones sobriedad sobrio sobria historia historias distrito taller escritura revista servicio comité alcohólicos anónimos
padrino madrina paso pasos tradición tradiciones mensaje viña amor humildad fuerza""".split())
_EN_WORDS = set("""the and of to in is you that it he was for on are as with his they i at be this have from or one had by
but not what all were we when your can said there an each which she do how their if will up other about out many then them
these so some her would make like him into time has look two more write go see my our me sober sobriety meeting meetings story
stories group groups service committee alcoholics anonymous sponsor step steps tradition traditions message love life day
days year years new free book books podcast episode season""".split())
_FR_WORDS = set("""le les des est et une pour dans avec sur pas qui ce ne au du vous nous leur sont été être vigne
réunion sobriété mouvement groupe histoire""".split())


def _lang_scores(text: str) -> tuple[int, int, int]:
    """(Spanish, English, French) evidence in a short text: its known words, accents and word endings."""
    t = clean_text(text).lower()
    words = re.findall(r"[a-záéíóúüñàâçèêëîïôûœ']+", t)
    es = sum(1 for w in words if w in _ES_WORDS)
    en = sum(1 for w in words if w in _EN_WORDS)
    fr = sum(1 for w in words if w in _FR_WORDS)
    es += 2 * len(re.findall(r"[ñ¿¡]", t)) + len(re.findall(r"[áíóú]", t))
    es += sum(1 for w in words if re.search(r"(ción|ciones|dad|dades|mente|amos|aron)$", w))
    en += sum(1 for w in words if re.search(r"(ing|tion|ness|ship|ly)$", w) and not w.endswith("ción"))
    fr += 2 * len(re.findall(r"[àâçèêëîïôûœ]", t))
    return es, en, fr


def detect_lang(text: str, prior: str | None = None) -> str:
    """Tiny, dependency-free EN/ES/FR detector tuned for short titles.

    `prior` (e.g. 'es' for aalavina.org) wins when the text is inconclusive.
    """
    if not clean_text(text):
        return prior or "und"
    es, en, fr = _lang_scores(text)
    best = max((es, "es"), (en, "en"), (fr, "fr"))
    runner = sorted([es, en, fr])[-2]
    if best[0] == 0 or best[0] - runner < 1:
        return prior or (best[1] if best[0] else "und")
    return best[1]


# --------------------------------------------------------------------------- raw data I/O
def raw_path(source: str) -> Path:
    return RAW_DIR / f"{source}.json"


class UnreadableRaw(RuntimeError):
    """data/raw/<source>.json exists but cannot be read (a bad hand edit, a broken merge, an interrupted restore).
    The source is never rebuilt from scratch over it — a source that builds up over time (YouTube, the articles,
    the library, Instagram) would keep only what it lists today, and Instagram would delete the pictures of every
    older post: the file stays as it is, nothing is written over it (load_raw raises, so every save_raw does too),
    run_all does not run the source's module, and build_data keeps what the last build made of it
    (carry_unreadable) and shows the source as failed on /status/ until a person restores the file from git."""

    def __init__(self, source: str, reason: str):
        self.source, self.reason = source, reason
        super().__init__(unreadable_message(source, reason))


def unreadable_message(source: str, reason: str = "") -> str:
    """The plain line for /status/ and the run summary about a raw file that cannot be read."""
    return (f"data/raw/{source}.json cannot be read{f' ({reason})' if reason else ''} — restore it from git; the "
            "site keeps the last build's items")


def _read_raw_file(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("items", []), list):
        raise ValueError("not a raw envelope (expected an object with an 'items' list)")
    data.setdefault("items", [])
    return data


def raw_unreadable(source: str) -> str | None:
    """Why data/raw/<source>.json cannot be read ("JSONDecodeError: …"), or None when it can — or does not exist."""
    p = raw_path(source)
    if not p.exists():
        return None
    try:
        _read_raw_file(p)
    except Exception as e:  # noqa: BLE001 — any reason it cannot be read
        return f"{type(e).__name__}: {str(e)[:80]}"
    return None


def load_raw(source: str) -> dict:
    """The raw envelope of a source (an empty one if the file does not exist yet — a new source, or one a person
    deleted on purpose to read it again from scratch).

    A file that exists but cannot be parsed raises UnreadableRaw and is left exactly as it is: the source is not
    rebuilt from scratch over it (see UnreadableRaw)."""
    p = raw_path(source)
    if p.exists():
        try:
            return _read_raw_file(p)
        except Exception as e:
            raise UnreadableRaw(source, f"{type(e).__name__}: {str(e)[:80]}") from e
    return {"source": source, "updated": None, "ok": False, "error": None, "stats": {}, "items": []}


def _json_default(o: Any) -> Any:
    """Last-resort conversion so an unexpected value (e.g. a YAML date) never crashes a write."""
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=str)
    return str(o)


def as_json(data: Any) -> Any:
    """`data` as write_json() stores it (dates → ISO text, sets → sorted lists, tuples → lists): what reading
    the file back gives, so a fresh value can be compared with a written one."""
    return json.loads(json.dumps(data, ensure_ascii=False, default=_json_default))


def write_json(path: Path, data: Any, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        if compact:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=False, default=_json_default)
        else:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=False, default=_json_default)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_capped(r: Any, cap: int) -> tuple[bytes, bool]:
    """The body of a response asked for with stream=True, read no further than `cap` bytes → (data, cut):
    cut = the file is longer, and the rest is never downloaded (a size cap applied while reading, not after
    the whole download). A response object without iter_content gives its `content`, cut the same way."""
    if not hasattr(r, "iter_content"):
        data = getattr(r, "content", None) or b""
        return data[:cap], len(data) > cap
    buf = bytearray()
    for chunk in r.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        buf += chunk
        if len(buf) > cap:
            return bytes(buf[:cap]), True
    return bytes(buf), False


# --------------------------------------------------------------------------- mass-drop guard (save_raw)
# A source that says "ok" but suddenly lists far fewer items than last time — an empty Google Drive folder
# view, a half-rendered page, a feed answering with nothing — is far more often a bad moment at the source
# than a real change. save_raw() then writes the run's items WITH the missing ones put back and marks the
# envelope `held` (since when, how many, a few of their titles, their ids; /status/ shows it); the NEXT run
# that still misses those same items accepts it, so a real removal is only one run late (items that vanish
# only on that next run are a new drop, held back in turn). Counted on live items (status != "gone"):
#   * the list falls to zero (from any size), or
#   * more than half of it disappears, once it held at least DROP_GUARD_MIN items. Below that a few posts or
#     events coming and going is ordinary (today's small sources hold 2–9 items), while every source whose
#     loss would hurt holds more (meetings 23, Drive 35, editorial 44, the store 62, Instagram 71, the
#     library 142, articles 228, podcasts 299, YouTube 533).
DROP_GUARD_MIN = 10
# Sources whose lists may shrink a lot from one run to the next ON PURPOSE: not guarded (save_raw's
# drop_guard=None reads this table; a module may also pass drop_guard=True / False itself). A source switched
# off in the settings (stats.disabled — meetings.enabled: false) is never guarded either.
DROP_GUARD_EXEMPT: dict[str, str] = {
    "announcements": "hand-written content/bulletin files: a removal is the committee's own edit (a file that "
                     "cannot be read is reported in stats.errors)",
    "manual_events": "hand-written content/events files: a removal is the committee's own edit",
    "events_external": "upcoming events only: past events leave the list, often several at once",
    "editorial": "a rolling window of upcoming deadlines, with its own guard (editorial.collect: a part whose list "
                 "shrinks below 40% keeps its previous topics)",
    "instagram": "a bad listing never drops posts (they are merged into the saved ones; a failed account makes the "
                 "run fail); posts leave only on purpose — the newest N kept per account, a post taken off the list "
                 "— and their pictures are deleted in that same run, so a post put back would show without one",
    "writers_archive": "its own guard: a new archive file needs writers_archive.min_rows_ratio of the rows of the "
                       "file before, or the older rows stay",
}
HELD_EXAMPLES = 5               # titles of held items named in the envelope (`held.examples`)
# `held.ids` names EVERY held item (sorted): the next run accepts exactly those that are still missing, and judges
# any other missing item on its own. (A cut list could not tell which missing items are new, and a source that
# loses a few more each run would never be confirmed.) The list exists only while a hold lasts; the items carry the
# same ids anyway, and status.json leaves it out.


def _live_ids(items: Any) -> dict[str, dict]:
    """id → item of the live items (status != "gone") of a raw item list."""
    return {i["id"]: i for i in (items or []) if isinstance(i, dict) and i.get("id")
            and i.get("status", "ok") != "gone"}


def _held_ids(held: dict, prev_live: dict[str, dict]) -> list[str]:
    """The ids a guard hold kept back (`held.ids`); an envelope from before the ids were stored: every item."""
    ids = held.get("ids")
    return [str(i) for i in ids] if isinstance(ids, list) else list(prev_live)


def is_mass_drop(before: int, found: int) -> bool:
    """`found` live items where there were `before`: zero (from any size), or less than half once the list
    held DROP_GUARD_MIN or more."""
    return before > 0 and (found == 0 or (before >= DROP_GUARD_MIN and found * 2 < before))


def save_raw(source: str, items: list[dict], ok: bool = True, error: str | None = None,
             stats: dict | None = None, extra: dict | None = None, *, drop_guard: bool | None = None,
             unconfirmed: Iterable[str] = (), confirmed: Iterable[str] = ()) -> None:
    """Write data/raw/<source>.json. If ok=False and items is empty, previous items are kept.

    `first_harvest` records when the source was first read successfully (even with 0 items) and
    never moves afterwards: build_data uses it to tell the launch-day back catalog from real news.
    (The oldest first_seen cannot be used for that — it moves forward whenever a source drops old
    items, e.g. past events.) When first written it is seeded from the oldest first_seen known.

    The mass-drop guard (above): drop_guard None = DROP_GUARD_EXEMPT decides. A module that keeps items
    itself until a second run confirms they are gone (drive.py: the files of a folder that suddenly looks
    empty) names them in `unconfirmed` — the envelope is marked `held` the same way — and names in
    `confirmed` the items it removes after that second look (they never count as a suspicious drop).

    Every envelope carries `changes` = this run's {"added", "removed", "held"} (live items; "held" = items
    kept although this run did not find them) — plus "confirmed": the `held.since` of a hold whose items this
    run removed (the same drop seen again, or a module's `confirmed`) — and `held` = {"since", "kept",
    "previous", "found", "drop", "examples"[, "ids"]} while items are held back ("drop": the guard put them
    back, "ids" = all of theirs, sorted; false: the module kept them, `unconfirmed`). build_data copies both into
    status.json sources[] (`held` without its "ids").

    A failed run (ok=False) keeps an earlier hold as it was — and while a guard hold lasts, the held items it
    misses or marks gone are put back too: only a run that works confirms a removal. Nothing is written over a
    raw file that cannot be read (load_raw raises UnreadableRaw)."""
    log = get_logger("common")
    now = now_iso()
    prev = load_raw(source)         # (UnreadableRaw: nothing is ever written over a file that cannot be read)
    if not ok and not items:
        items = prev.get("items", [])
    prev_live = _live_ids(prev.get("items"))
    prev_held = prev.get("held") if isinstance(prev.get("held"), dict) else None
    new_live = _live_ids(items)
    unconfirmed = {i for i in unconfirmed if i in new_live}
    confirmed = {i for i in confirmed if i in prev_live and i not in new_live}
    restored: list[dict] = []
    accepted = None
    held = prev_held if not ok else None        # a failed run saw nothing: an earlier hold stays as it was
    guarded = ((drop_guard if drop_guard is not None else source not in DROP_GUARD_EXEMPT)
               and (stats or {}).get("disabled") is not True)
    guard = ok and guarded
    before, found = len(prev_live) - len(confirmed), len(new_live) - len(unconfirmed)
    if ok and confirmed and prev_held:      # the module removed items it had kept back (drive: empty twice)
        accepted = prev_held.get("since")
    held_ids = _held_ids(prev_held, prev_live) if prev_held and prev_held.get("drop") else None
    if not ok and guarded and held_ids is not None:
        # A failed run during a hold is not trusted with the removal either (crawl.py writes its list on a failed run
        # too, the held documents marked gone as its saved state still says): the held items it misses or marks
        # gone are put back as they were — the hold stays as it was, and the next run that works decides. (A hold
        # written before every id was stored — `ids_total` — puts back every item the run misses.)
        cut = isinstance(prev_held.get("ids_total"), int) and prev_held["ids_total"] > len(held_ids)
        mine = set(held_ids)
        restored = [p for i, p in prev_live.items() if i not in new_live and (cut or i in mine)]
    if guard and held_ids is not None:
        # The items the last run held back (`held.ids`) that are still missing: the same drop seen again — it is
        # real, they go now. Items that vanished only in THIS run are judged on their own (below).
        again = {i for i in held_ids if i in prev_live and i not in new_live and i not in confirmed}
        if again:
            accepted = prev_held.get("since")
            confirmed |= again
            before -= len(again)
            log.warning("%s: %d item(s) held back since %s are still missing — their removal is accepted",
                        source, len(again), accepted)
    if guard and is_mass_drop(before, found):
        restored = [p for i, p in prev_live.items() if i not in new_live and i not in confirmed]
        if restored:    # (nothing to put back when the module keeps them itself: `unconfirmed`)
            log.warning("%s: only %d of %d items found — %d held back until the next run confirms the drop",
                        source, found, before, len(restored))
    if restored:        # (an item this run marked "gone" is put back as it was, not listed twice)
        back = {p["id"] for p in restored}
        items = [*(i for i in items if not (isinstance(i, dict) and i.get("id") in back)), *restored]
    if ok and (restored or unconfirmed):
        kept_ids = [p["id"] for p in restored] + sorted(unconfirmed)
        titles = [clean_text((prev_live.get(i) or new_live.get(i) or {}).get("title")) for i in kept_ids]
        held = {"since": (None if accepted else (prev_held or {}).get("since")) or now, "kept": len(kept_ids),
                "previous": before, "found": found, "drop": bool(restored),
                "examples": [t for t in titles if t][:HELD_EXAMPLES]}
        if restored:
            held["ids"] = sorted(back)
    items = sort_items(items)
    final_live = _live_ids(items)
    changes: dict[str, Any] = {"added": len(final_live.keys() - prev_live.keys()),
                               "removed": len(prev_live.keys() - final_live.keys()),
                               "held": (held or {}).get("kept", 0)}
    if accepted:
        changes["confirmed"] = accepted
    first = prev.get("first_harvest")
    if not first and ok:
        seen = sorted(str(i["first_seen"]) for i in [*(prev.get("items") or []), *items]
                      if isinstance(i, dict) and i.get("first_seen"))
        first = seen[0] if seen else now
    env = {
        "source": source,
        "updated": now if ok else prev.get("updated"),
        "attempted": now,
        "ok": ok,
        "error": (error or None) if not ok else None,
        **({"held": held} if held else {}),
        "changes": changes,
        "stats": stats or {},
        "items": items,
    }
    if first:
        env["first_harvest"] = first
    if extra:       # (`held` and `changes` are this function's own: a copy of the last envelope's never wins)
        env.update({k: v for k, v in extra.items() if k not in ("held", "changes")})
    write_json(raw_path(source), env)


def sort_items(items: list[dict]) -> list[dict]:
    def key(i):
        d = (i.get("extra") or {}).get("start") or i.get("date") or i.get("first_seen") or ""
        return str(d)
    return sorted(items, key=key, reverse=True)


def make_item(*, id: str, source: str, kind: str, url: str, title: str, summary: str = "",
              lang: str = "und", date: str | None = None, image: str | None = None,
              tags: Iterable[str] | None = None, category: str | None = None,
              extra: dict | None = None, status: str = "ok") -> dict:
    """Build an Item following docs/DATA_SCHEMA.md (first_seen/last_seen set by merge_items)."""
    return {
        "id": id, "source": source, "kind": kind, "url": url,
        "title": clean_text(title), "summary": truncate(summary or "", 400),
        "lang": lang or "und", "date": date, "first_seen": None, "last_seen": None,
        "image": image, "tags": list(tags or []), "category": category, "status": status,
        "extra": extra or {},
    }


def merge_items(old: list[dict], new: list[dict], *, drop_missing: bool = False,
                mark_gone_missing: bool = False, authoritative: bool = False) -> tuple[list[dict], int]:
    """Cumulative merge by id.

    * keeps `first_seen` of existing items, sets `last_seen` = now for items in `new`
      (refreshed at most weekly)
    * by default a field that is empty in the new item (date/image/summary, or an `extra` key that is
      None/""/[]/{}) keeps its previous value — a scraped page that lacks something today does not wipe it
    * authoritative=True: the new item is the whole truth (hand-written files, items rebuilt from
      their own saved state or cache) → only first_seen/last_seen come from the old item, so a field
      that was removed really disappears
    * items only in `old` are kept (unless drop_missing) — optionally marked status="gone"
    * returns (merged, count_of_new_ids)
    """
    now = now_iso()
    by_id = {i["id"]: i for i in old if i.get("id")}
    added = 0
    seen = set()
    for it in new:
        iid = it.get("id")
        if not iid:
            continue
        seen.add(iid)
        prev = by_id.get(iid)
        it = dict(it)
        if prev and authoritative:
            it["first_seen"] = prev.get("first_seen") or now
        elif prev:
            it["first_seen"] = prev.get("first_seen") or now
            # keep previously-known values when the new fetch lacks them
            for k in ("date", "image", "summary"):
                if not it.get(k) and prev.get(k):
                    it[k] = prev[k]
            pe, ne = prev.get("extra") or {}, it.get("extra") or {}
            it["extra"] = {**pe, **{k: v for k, v in ne.items() if v not in (None, "", [], {})}}
        else:
            it["first_seen"] = it.get("first_seen") or now
            added += 1
        # Refresh last_seen at most weekly so unchanged items don't churn the daily git diff.
        prev_seen = parse_iso(prev.get("last_seen")) if prev else None
        if prev_seen and (datetime.now(timezone.utc) - prev_seen).days < 7:
            it["last_seen"] = prev.get("last_seen")
        else:
            it["last_seen"] = now
        it.setdefault("status", "ok")
        by_id[iid] = it
    if drop_missing:
        by_id = {k: v for k, v in by_id.items() if k in seen}
    elif mark_gone_missing:
        for k, v in by_id.items():
            if k not in seen:
                v["status"] = "gone"
    return sort_items(list(by_id.values())), added


# --------------------------------------------------------------------------- HTTP
class PoliteSession:
    """requests.Session wrapper: identifies itself, obeys robots.txt + Crawl-delay per server
    (host names of one server share one delay slot — SAME_SERVER_HOSTS), retries transient errors
    with backoff, and never hammers a host. A robots.txt that answers 5xx / 429 or does not answer at
    all closes its whole host for now (RFC 9309 — see ROBOTS_RETRY_S); a 4xx one allows everything.

        http = PoliteSession(min_delay=1.0)           # generic
        r = http.get(url)                             # returns Response or None (robots-disallowed / failed;
                                                      # http.last_failure says which)
        html = http.get_text(url)                     # text of a 200 answer, else None (a magazine page
                                                      # already read in this run is not asked for again)
    """

    # Per-run page memo: the daily run asks the magazines' server (SAME_SERVER_HOSTS) for each page at
    # most ONCE, whichever modules need it — quote, the podcast discovery and the crawl all read the two
    # home pages; shop and the crawl /BOTM and /libro-del-mes; weekly_open and the crawl
    # /grapevine-weekly-open; events_external and the crawl the sitemap. Every such page read with
    # get_text() is kept for the rest of the process (oldest dropped first above MEMO_MAX_CHARS); the
    # next get_text() of it returns that copy, and the crawler takes it through remembered().
    MEMO_MAX_CHARS = 48 * 1024 * 1024
    # robots.txt answered 5xx / 429 or not at all: the host stays closed this long, then the next request
    # asks for robots.txt again — so one bad answer during a site deploy does not silence the magazine
    # sites for the rest of a two-hour run (RFC 9309 §2.3.1.4: assume complete disallow meanwhile).
    ROBOTS_RETRY_S = 600.0

    def __init__(self, user_agent: str | None = None, min_delay: float = 1.0, respect_robots: bool = True,
                 timeout: float = 30.0, retries: int = 3, browser_ua: bool = False):
        cfg = load_config()
        self.ua = user_agent or (BROWSER_UA if browser_ua else (cfg.get("sources", {}).get("crawler", {}) or {}).get(
            "user_agent", "NETA65-GrapevineCommitteeBot/2.0"))
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": self.ua, "Accept-Language": "en-US,en;q=0.8,es;q=0.7"})
        self.min_delay = min_delay
        self.respect_robots = respect_robots
        self.timeout = timeout
        self.retries = retries
        # host → (parser or None, problem or None, monotonic time until which a problem stands)
        self._robots: dict[str, tuple[Any, str | None, float]] = {}
        # why the last request()/get() returned None: "robots" (its rules disallow the URL),
        # "robots-unavailable" (robots.txt answered 5xx / 429), "robots-unreachable" (robots.txt gave no
        # answer, asked twice — nothing was sent for the URL), "unreachable" (the URL gave no answer),
        # "redirects" (too many); None after an answer
        self.last_failure: str | None = None
        self._last: dict[str, float] = {}          # pace key (see pace_key) → time of the last request
        self._delay: dict[str, float] = {}         # pace key → strictest delay seen for that group
        self.requests_made = 0
        self.memo_hits = 0                         # get_text() answers served from the page memo
        self._memo: OrderedDict[str, dict] = OrderedDict()   # memo_key → {url, text, headers}
        self._memo_chars = 0
        self.log = get_logger("http")

    # pacing ---------------------------------------------------------------
    @staticmethod
    def pace_key(url: str) -> str:
        """Requests are spaced per server, not per host name: www.aagrapevine.org and www.aalavina.org
        (and their bare-domain aliases) are one Drupal server and share one Crawl-delay slot."""
        host = (urlparse(url).hostname or "").lower()
        return SAME_SERVER_HOSTS.get(host, host)

    def _pause(self, key: str, delay: float) -> None:
        last = self._last.get(key)
        if last is not None:
            gap = time.monotonic() - last
            if gap < delay:
                time.sleep(delay - gap)

    # robots ---------------------------------------------------------------
    def _robots_for(self, url: str) -> tuple[Any, str | None]:
        """(parser or None, problem or None) for the URL's host, read once per run (RFC 9309 §2.3.1):
          * 200                      → its rules (parser)
          * 4xx, too many redirects  → no rules: everything allowed (None, None)
          * 5xx or 429               → (None, "HTTP 503"): the whole host is disallowed …
          * no answer                → (None, "unreachable"): … likewise
        A problem holds for ROBOTS_RETRY_S, then robots.txt is asked for again. Each failing read is
        tried twice (a single network blip must not close a host)."""
        host = urlparse(url).netloc
        hit = self._robots.get(host)
        if hit is not None and (hit[1] is None or time.monotonic() < hit[2]):
            return hit[0], hit[1]
        rp, problem = None, None
        if self.respect_robots and Protego is not None:
            key = self.pace_key(url)
            for attempt in (1, 2):
                # robots.txt is a request to the same server too (its own delay is not known yet)
                self._pause(key, max(self.min_delay, self._delay.get(key, 0.0)))
                try:
                    r = self.s.get(f"{urlparse(url).scheme}://{host}/robots.txt", timeout=self.timeout)
                    code = r.status_code
                    problem = f"HTTP {code}" if code == 429 or code >= 500 else None
                    if code == 200:
                        try:
                            rp = Protego.parse(r.text)
                        except Exception as e:  # noqa: BLE001 — unparsable rules: none
                            self.log.debug("robots.txt of %s unparsable: %s", host, e)
                except requests.TooManyRedirects:
                    problem = None             # no robots.txt to be found: like a 404 (allowed)
                except Exception as e:  # noqa: BLE001 — timeout, DNS, refused connection …
                    problem = "unreachable"
                    self.log.debug("robots.txt of %s: %s", host, e)
                finally:
                    self._last[key] = time.monotonic()
                if problem is None:
                    break
            if problem:
                self.log.warning("robots.txt of %s: %s — the site is not asked for anything for %d min",
                                 host, "no answer" if problem == "unreachable" else problem,
                                 self.ROBOTS_RETRY_S // 60)
        self._robots[host] = (rp, problem, time.monotonic() + self.ROBOTS_RETRY_S)
        return rp, problem

    def robots_problem(self, url: str) -> str | None:
        """Why robots.txt closes the URL's whole host for now — "unreachable" (no answer) or "HTTP 503"
        (a 5xx / 429 answer) — or None when its rules (if any) apply."""
        return self._robots_for(url)[1]

    def allowed(self, url: str) -> bool:
        rp, problem = self._robots_for(url)
        if problem:
            return False
        if rp is None:
            return True
        try:
            return rp.can_fetch(url, self.ua)
        except Exception:
            return True

    def _refusal(self, url: str) -> str:
        """last_failure for a URL that allowed() refused."""
        problem = self.robots_problem(url)
        return "robots" if not problem else "robots-unreachable" if problem == "unreachable" else "robots-unavailable"

    def delay_for(self, url: str) -> float:
        rp, _problem = self._robots_for(url)
        d = self.min_delay
        if rp is not None:
            try:
                cd = rp.crawl_delay(self.ua)
                if cd:
                    d = max(d, float(cd))
            except Exception:
                pass
        key = self.pace_key(url)
        d = max(d, self._delay.get(key, 0.0))      # hosts on one server: the strictest delay wins
        self._delay[key] = d
        return d

    def _wait(self, url: str) -> None:
        d = self.delay_for(url)
        self._pause(self.pace_key(url), d)

    # requests -------------------------------------------------------------
    MAX_REDIRECTS = 5

    def request(self, method: str, url: str, **kw) -> requests.Response | None:
        """One polite request. Redirects of the magazine server (SAME_SERVER_HOSTS) are followed
        by hand, so every hop also waits the Crawl-delay and is checked against robots.txt (requests
        itself would follow them at once, inside the same call). None → `last_failure` says why."""
        self.last_failure = None
        follow = kw.pop("allow_redirects", True)
        if not follow or (urlparse(url).hostname or "").lower() not in SAME_SERVER_HOSTS:
            return self._send(method, url, allow_redirects=follow, **kw)
        r = None
        for _hop in range(self.MAX_REDIRECTS + 1):
            r = self._send(method, url, allow_redirects=False, **kw)
            loc = r.headers.get("Location") if r is not None and getattr(r, "is_redirect", False) else None
            if not loc:
                return r
            nxt = urljoin(url, loc)
            try:
                r.close()
            except Exception:  # noqa: BLE001 — closing a finished redirect response never matters
                pass
            if not self.allowed(nxt):
                self.last_failure = self._refusal(nxt)
                self.log.info("robots.txt disallows %s (redirected from %s)", nxt, url)
                return None
            url = nxt
        self.last_failure = "redirects"
        self.log.warning("%s %s: too many redirects", method, url)
        return None

    def _send(self, method: str, url: str, **kw) -> requests.Response | None:
        if not self.allowed(url):
            self.last_failure = self._refusal(url)
            if self.last_failure == "robots":
                self.log.info("robots.txt disallows %s", url)
            return None
        self.last_failure = "unreachable"          # until an answer comes
        kw.setdefault("timeout", self.timeout)
        kw.setdefault("allow_redirects", True)
        key = self.pace_key(url)
        for attempt in range(1, self.retries + 1):
            self._wait(url)
            try:
                r = self.s.request(method, url, **kw)
                self._last[key] = time.monotonic()
                self.requests_made += 1
                if r.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    ra = r.headers.get("Retry-After")
                    backoff = float(ra) if ra and ra.isdigit() else 5.0 * attempt
                    self.log.warning("%s %s -> %s, retry in %.0fs", method, url, r.status_code, backoff)
                    # the answer is dropped: give its connection back now (a stream=True one would hold it
                    # until garbage collection)
                    try:
                        r.close()
                    except Exception:  # noqa: BLE001 — closing an answer we drop never matters
                        pass
                    time.sleep(min(backoff, 60))
                    continue
                self.last_failure = None
                return r
            except requests.RequestException as e:
                self._last[key] = time.monotonic()
                if attempt >= self.retries:
                    self.log.warning("%s %s failed: %s", method, url, e)
                    return None
                time.sleep(3 * attempt)
        return None

    def get(self, url: str, **kw) -> requests.Response | None:
        return self.request("GET", url, **kw)

    def head(self, url: str, **kw) -> requests.Response | None:
        return self.request("HEAD", url, **kw)

    def get_text(self, url: str, reuse: bool = True, **kw) -> str | None:
        """GET → the page text (None when robots.txt disallows it, the request failed or the answer is
        not 200). A magazine page (SAME_SERVER_HOSTS) already read in this run is NOT asked for again:
        its copy is returned (reuse=False sends a new request anyway). Plain GETs only — a call with
        `params` is neither reused nor remembered."""
        plain = "params" not in kw
        if reuse and plain:
            hit = self.remembered(url)
            if hit is not None:
                self.memo_hits += 1
                self.log.debug("%s: already read in this run — reused", url)
                return hit["text"]
        r = self.get(url, **kw)
        if r is None or r.status_code != 200:
            return None
        r.encoding = r.encoding or "utf-8"
        if r.encoding.lower() in ("iso-8859-1", "latin-1") and "charset" not in r.headers.get("Content-Type", ""):
            r.encoding = "utf-8"
        text = r.text
        if plain:
            self._remember(url, getattr(r, "url", None) or url, text, r.headers)
        return text

    # page memo --------------------------------------------------------------
    @staticmethod
    def memo_key(url: str) -> str | None:
        """One key per magazine page: https, the www host, "/" for an empty path, no fragment.
        None for every other host (those pages are never remembered)."""
        try:
            p = urlsplit(str(url).strip())
        except ValueError:
            return None
        host = (p.hostname or "").lower()
        if host not in SAME_SERVER_HOSTS:
            return None
        if not host.startswith("www."):
            host = "www." + host
        return urlunsplit(("https", host, p.path or "/", p.query, ""))

    def remembered(self, url: str) -> dict | None:
        """The copy of a magazine page read earlier in this run — {"url": the final URL (after
        redirects), "text", "headers": {Content-Type, ETag, Last-Modified}} — or None."""
        key = self.memo_key(url)
        hit = self._memo.get(key) if key else None
        return {**hit, "headers": dict(hit["headers"])} if hit else None

    def _remember(self, url: str, final_url: str, text: str, headers) -> None:
        keys = {k for k in (self.memo_key(url), self.memo_key(final_url)) if k}
        if not keys or not text or len(text) > self.MEMO_MAX_CHARS // 4:
            return
        hdrs = {}
        for h in ("Content-Type", "ETag", "Last-Modified"):
            try:
                v = headers.get(h) if headers is not None else None
            except Exception:  # noqa: BLE001 — a header object without .get()
                v = None
            if v:
                hdrs[h] = v
        entry = {"url": final_url, "text": text, "headers": hdrs}
        for key in keys:
            old = self._memo.pop(key, None)
            if old is not None:
                self._memo_chars -= len(old["text"])
            self._memo[key] = entry
            self._memo_chars += len(text)
        while self._memo_chars > self.MEMO_MAX_CHARS and self._memo:
            _k, old = self._memo.popitem(last=False)
            self._memo_chars -= len(old["text"])


_SHARED: PoliteSession | None = None


def shared_session() -> PoliteSession:
    """ONE bot session for aagrapevine.org / aalavina.org shared by every module in a run,
    so robots.txt Crawl-delay (5 s) is respected across modules and across BOTH hosts (one server,
    see SAME_SERVER_HOSTS), not just within one module or one host name. It also holds the run's page
    memo (PoliteSession.get_text / remembered), so a page that several modules need is requested once."""
    global _SHARED
    if _SHARED is None:
        _SHARED = PoliteSession(min_delay=5.0, respect_robots=True)
    return _SHARED


def absolute(base: str, href: str) -> str:
    return urljoin(base, href.strip())


def run_module(name: str, fn) -> int:
    """Standard CLI wrapper: `python -m scripts.sync.<name>` → exit code 0 even on soft failure
    (the module is expected to have written ok=false itself). A raw file that cannot be read (UnreadableRaw)
    stops the module and nothing is written over it — not even the failure mark."""
    log = get_logger(name)
    t0 = time.time()
    try:
        fn()
        log.info("done in %.1fs", time.time() - t0)
        return 0
    except KeyboardInterrupt:
        raise
    except UnreadableRaw as e:
        log.error("%s — the source was not updated", e)
        return 0
    except Exception as e:  # never fail the whole pipeline because one source broke
        log.exception("module crashed: %s", e)
        try:
            prev = load_raw(name)
            keep = {k: v for k, v in prev.items() if k not in ("source", "updated", "attempted", "ok", "error", "stats", "items")}
            save_raw(name, prev.get("items", []), ok=False, error=f"{type(e).__name__}: {e}"[:300], stats=prev.get("stats"), extra=keep)
        except Exception:
            pass
        return 0
