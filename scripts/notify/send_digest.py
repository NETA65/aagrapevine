"""Monthly bilingual (English + Spanish) e-mail digest for the districts: LAST month on the site.

One EDITION per calendar month P (America/Chicago), named after it — "September 2026 digest" /
"Resumen de septiembre de 2026" — and sent once, early in the next month K
(.github/workflows/monthly-digest.yml: from 7 AM Central on the 1st, as soon as every source has been
updated since P ended; at the latest from noon on the 3rd). It is the same edition as the website's
/digest/ page (eleventy/filters/community.js → buildMonthlyDigest; keep the two in step —
tests/test_digest_parity.py compares what each one picks): what happened or was published on the site
in P, read from the FULL data files (never whatsnew.json, which keeps only its newest 150 entries), a
day being its Central calendar day:

  * the bulletin's posts (announcements.json) by the day they were added to the site — the day the site
    first had them (first_seen; their date on that same day), never before their `publish` day (a
    scheduled post) —, not expired
  * the events that took place in P (events.json: the month an event starts in) and P's committee
    meeting — its record, else the config/site.yml `meeting:` rule (events.json drops a meeting once it
    is over) — with their days only; events are never "news" on their own
  * the committee's uploads (drive.json) by the later of their date and the day the site first had them
    (first_seen) — a file named after an earlier meeting is in the edition of the month it was added —,
    each file with its own date (a dated flyer is an event, not an upload), the photos ONE row per album
  * the magazine issues whose stories came out online in P (articles.json extra.pub_date; a story without
    one: the day its issue came out online, never first_seen), each with a few highlights — free to read
    first, then members' stories (the writers' stories are in their own section) — and a link to all its
    stories on /read/
  * stories by writers from Area 65 and the rest of Texas published in P (spotlight.json)
  * podcast episodes (a YouTube upload of the same episode is folded into it), videos, the magazines'
    Instagram posts (instagram.json: per account, how many and the 3 newest, and one link to the site's
    /instagram/ page — the text part gives only the counts and the link), documents
  * ONE pointer: "Coming up in K" → the toolkit of the month it goes out in (/monthly/K/), the home of
    everything current (the committee meeting — its Zoom details stay on /meetings/ —, events not over
    yet, story deadlines, this month's issues, Book of the Month …)
  * each section in English first, then in Spanish (titles are already translated)

Standard library only (smtplib + email.mime) so it runs anywhere without installing the sync
pipeline. PyYAML is used when available to read config/site.yml; a small built-in reader is the
fallback.

Usage (from the repo root):

    python -m scripts.notify.send_digest --dry-run                    # last month → .tmp/digest.html + .tmp/digest.txt
    python -m scripts.notify.send_digest --dry-run --month 2026-09 --as-of 2026-10-01   # the September digest, as on Oct 1
    python -m scripts.notify.send_digest                              # sends (needs the SMTP_* env vars below)

Environment (GitHub secrets in .github/workflows/monthly-digest.yml):

    SMTP_SERVER     e.g. smtp.gmail.com                  (required to send)
    SMTP_PORT       587 (STARTTLS, default) or 465 (SSL). On any port but 465 the server MUST offer
                    STARTTLS: the password is never sent unencrypted (the run stops instead)
    SMTP_USERNAME   the mailbox login                    (required to send)
    SMTP_PASSWORD   an APP password, not your normal one (required to send)
    DIGEST_TO       one address (e.g. a Google Group) or several, comma-separated
                    (several addresses are sent as Bcc so nobody sees the others)
    DIGEST_FROM     optional "From" address (default: SMTP_USERNAME)
    DIGEST_REPLY_TO optional reply-to (default: site.contact_email from config)
    SITE_URL        optional public site address (overrides site.url from config)

Sending: connecting and logging in are tried up to 3 times; the message itself is handed over
ONCE — if the connection breaks at that point the run fails with "it MAY have been sent" instead of
trying again (a second try could e-mail every district twice).

Waiting for the data: a month's last items come in with the first updates after it ends (a podcast
out at 11:15 PM on the 30th). Before it sends, data/site/status.json must show every source the digest
reads (FRESH_SOURCES) tried since 00:00 Central on the 1st of K; otherwise it sends nothing and exits 3
("not yet" — the workflow tries again later). A source whose last try was more than FRESH_IDLE_DAYS
before that has stopped running and is not waited for (/status/ shows it). --stale-ok (the workflow's
last tries, from noon on the 3rd, and a manual send) and --force send anyway.

Exit codes: 0 = sent / previewed / nothing new in the month, 1 = sending failed, 2 = not configured, a
--month that is not YYYY-MM, or (sending) a month that is not over yet, 3 = the data has not been
updated since the month ended yet (nothing sent).
"""
from __future__ import annotations

import argparse
import calendar
import html
import json
import os
import re
import smtplib
import socket
import ssl
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "site.yml"
SITE_DIR = ROOT / "data" / "site"
ASSET_DIR = ROOT / "src"   # the site's own files (/assets/… → src/assets/…)

# Copies of rules in scripts/sync/ and eleventy/filters/ (kept here so this script runs with the
# standard library alone, without importing the sync pipeline) — keep them equal
# (tests/test_digest_parity.py builds the same editions with community.js and compares them):
MULTI_DAY_MIN_HOURS = 18                             # build_data.MULTI_DAY_MIN_H: a timed event over several days
EVERY_ISSUE = re.compile(r"(?i)in every issue|en cada (?:edici[oó]n|n[uú]mero)")  # build_data._EVERY_ISSUE
SE_SUFFIX = re.compile(r"(?i)\s*[\[(]\s*(?:season|temporada)\s*\d+\s*[,;.·-]?\s*(?:episode|episodio|ep\.?)\s*\d+\s*[\])]\s*$")
ONE_SUFFIX = re.compile(r"(?i)\s*[\[(]\s*(?:season|temporada|episode|episodio)\s*\d+\s*[\])]\s*$")  # media.js
NEWS_GROUPS = ("announcement", "article", "episode", "video", "post", "pdf", "drive")   # community.js MONTH_NEWS
NEWS_SOURCES = ("announcements", "episodes", "videos", "instagram", "pdfs", "drive")      # community.js MONTH_SOURCES (+ articles)
COUNT_ORDER = ("article", "episode", "video", "post", "pdf", "drive", "album", "announcement")  # community.js COUNT_ORDER
IG_NEWEST = 3                                        # community.js IG_NEWEST: an Instagram account's newest posts shown
IG_GENERIC_TITLE = re.compile(r"(?i)^\s*(?:aa\s+grapevine|la\s+vi[ñn]a)\s*[—–-]\s*instagram\s*$")  # media.js: a post without a caption
PHOTO_KINDS = ("photo", "video_file")                # committee.js isPhotoItem: the media of an album on /photos/
WEEKDAYS = {"sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4, "friday": 5, "saturday": 6}  # monthly.js WD
# The sources the e-mail waits for (their data must be tried after the month ended — status.json
# sources[].attempted) and how long a source may have been idle before it no longer counts as running.
FRESH_SOURCES = ("announcements", "manual_events", "drive", "articles", "pdfs", "youtube", "podcasts", "instagram")
FRESH_IDLE_DAYS = 3

# Brand colors (same tokens as src/assets/css/main.css, light theme). Every text in the e-mail is at least
# 4.5:1 against its background (WCAG 1.4.3 — tests/test_send_digest.py checks it): the small print (dates,
# counts, labels, the translation note) is "muted", never the site's lighter "faint" (#8a8599: 3.6:1).
C = {
    "paper": "#fbf8f2", "surface": "#ffffff", "surface2": "#f4efe6", "ink": "#1d1a26",
    "muted": "#57526a", "line": "#e6dfd2",
    "gv": "#0a5fa8", "gv_strong": "#07457c", "gv_soft": "#e5f0fa",
    "lv": "#b8430b", "lv_strong": "#8f3308", "lv_soft": "#fdeee3", "grape": "#5b2a86", "grape_soft": "#f1e8f8",
    "vine": "#2f6e2c", "vine_soft": "#e7f3e3",
}

# ---------------------------------------------------------------------------- words
# The website's wording (src/_i18n/community.json → community.digest.*), in the e-mail's own table.
T = {
    "en": {
        "lang_name": "English",
        "masthead": "Monthly digest",
        "edition": "{month} digest",
        "edition_sub": "Everything new on the site in {prev}",
        "intro": "In {prev}: {list}.",
        "intro_quiet": "A quiet {prev} on the site.",
        "and": "and",
        "n": {"article": ("{n} magazine stories", "1 magazine story"), "episode": ("{n} podcast episodes", "1 podcast episode"),
              "video": ("{n} videos", "1 video"), "post": ("{n} Instagram posts", "1 Instagram post"), "pdf": ("{n} documents", "1 document"),
              "drive": ("{n} committee files", "1 committee file"), "album": ("{n} photo albums", "1 photo album"),
              "announcement": ("{n} bulletin posts", "1 bulletin post")},
        "announcement": "Bulletin",
        "events": "Events in {prev}",
        "committee_meeting": "Committee meeting",
        "issues": "New in the magazines",
        "stories": ("{n} stories", "1 story"),
        "free_n": "{n} free to read",
        "free": "free to read",
        "subscriber": "subscriber story",
        "issue_more": "See all {n} stories",
        "writers": "Writers from Area 65 & Texas",
        "writers_sub": "Their stories came out in Grapevine or La Viña in {prev} — Area 65 writers first.",
        "group_neta65": "Area 65 (Northeast Texas)",
        "group_texas": "Elsewhere in Texas",
        "anonymous": "Anonymous",
        "episode": "Podcasts",
        "video": "Videos",
        "post": "Instagram",
        "pdf": "Documents",
        "drive": "Committee uploads",
        "twin": "also on YouTube",
        "album_plain": "New photos",
        "new_photos": "{n} new photos",
        "new_photo": "1 new photo",
        "ig_n": ("{n} posts", "1 post"),
        "ig_link": "See the latest posts from both magazines",
        "ig_post": "An Instagram post from {name}",
        "coming": "Coming up in {month}",
        "toolkit": "This month's toolkit ({month})",
        "toolkit_text": "The committee meeting, events and story deadlines, this month's magazine issues and the Book of the Month.",
        "see_all": "See all",
        "details": "Details",
        "more": "and {n} more on the website",
        "nothing": "A quiet month — nothing new was published in {prev}. The website still has hundreds of stories, podcasts and service resources.",
        "cta_site": "Open the website",
        "cta_new": "Everything new",
        "machine": "Some titles were translated automatically.",
        "online": "Online",
        "footer_why": "You are receiving this monthly summary from the {committee}.",
        "footer_unsub": "To stop receiving it, reply with \"unsubscribe\".",
        "footer_anon": "Feel free to forward it to your group or district — and please protect everyone's anonymity.",
        "pages": ("{n} pages", "1 page"),
        "min": "{n} min",
        "episode_se": "S{s} · E{e}",
        "in_other": "in Spanish",          # after something written in the other language
        "weekly_open": "Weekly Open",      # the pill of the Grapevine Weekly Open podcast
    },
    "es": {
        "lang_name": "Español",
        "masthead": "Resumen mensual",
        "edition": "Resumen de {month}",
        "edition_sub": "Todo lo nuevo del sitio en {prev}",
        "intro": "En {prev}: {list}.",
        "intro_quiet": "Un {prev} tranquilo en el sitio.",
        "and": "y",
        "n": {"article": ("{n} historias de las revistas", "1 historia de las revistas"),
              "episode": ("{n} episodios de podcast", "1 episodio de podcast"),
              "video": ("{n} videos", "1 video"), "post": ("{n} publicaciones de Instagram", "1 publicación de Instagram"),
              "pdf": ("{n} documentos", "1 documento"),
              "drive": ("{n} archivos del comité", "1 archivo del comité"), "album": ("{n} álbumes de fotos", "1 álbum de fotos"),
              "announcement": ("{n} avisos del boletín", "1 aviso del boletín")},
        "announcement": "Boletín",
        "events": "Eventos en {prev}",
        "committee_meeting": "Reunión del comité",
        "issues": "Lo nuevo en las revistas",
        "stories": ("{n} historias", "1 historia"),
        "free_n": "{n} gratis para leer",
        "free": "gratis para leer",
        "subscriber": "historia para suscriptores",
        "issue_more": "Ver las {n} historias",
        "writers": "Escritores del Área 65 y de Texas",
        "writers_sub": "Sus historias salieron en Grapevine o La Viña en {prev} — primero los del Área 65.",
        "group_neta65": "Área 65 (Noreste de Texas)",
        "group_texas": "En el resto de Texas",
        "anonymous": "Anónimo",
        "episode": "Podcasts",
        "video": "Videos",
        "post": "Instagram",
        "pdf": "Documentos",
        "drive": "Archivos del comité",
        "twin": "también en YouTube",
        "album_plain": "Fotos nuevas",
        "new_photos": "{n} fotos nuevas",
        "new_photo": "1 foto nueva",
        "ig_n": ("{n} publicaciones", "1 publicación"),
        "ig_link": "Ver las publicaciones recientes de las dos revistas",
        "ig_post": "Una publicación de Instagram de {name}",
        "coming": "Lo que viene en {month}",
        "toolkit": "El kit de este mes ({month})",
        "toolkit_text": "La reunión del comité, los eventos y las fechas límite para historias, las revistas de este mes y el libro del mes.",
        "see_all": "Ver todo",
        "details": "Detalles",
        "more": "y {n} más en el sitio web",
        "nothing": "Un mes tranquilo — no se publicó nada nuevo en {prev}. El sitio web tiene cientos de historias, podcasts y recursos de servicio.",
        "cta_site": "Abrir el sitio web",
        "cta_new": "Todas las novedades",
        "machine": "Algunos títulos se tradujeron automáticamente.",
        "online": "En línea",
        "footer_why": "Recibes este resumen mensual del {committee}.",
        "footer_unsub": "Para dejar de recibirlo, responde con \"cancelar\".",
        "footer_anon": "Puedes reenviarlo a tu grupo o distrito — y, por favor, protege el anonimato de todos.",
        "pages": ("{n} páginas", "1 página"),
        "min": "{n} min",
        "episode_se": "T{s} · E{e}",
        "in_other": "en inglés",
        "weekly_open": "Reunión Abierta Semanal",
    },
}

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
           "octubre", "noviembre", "diciembre"],
}
# The short names the website writes (Intl.DateTimeFormat "en-US" / "es-US": "Sat, Sep 12" / "sáb, 12 de
# sept" — no periods, "sept"), so a day reads the same on /digest/, in its texts and in this e-mail.
MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
}
DAYS_SHORT = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
}
DRIVE_CATEGORIES = {
    "reports": ("Reports", "Informes"), "notes": ("Notes", "Notas"), "slides": ("Slides", "Presentaciones"),
    "flyers": ("Flyers", "Volantes"), "photos": ("Photos", "Fotos"), "workshops": ("Workshops", "Talleres"),
    "announcements": ("Bulletin", "Boletín"), "forms": ("Forms", "Formularios"), "other": ("Files", "Archivos"),
}

# The lists after the magazines (and the writers), in order, with the site page "See all" points to (for
# Instagram: the site's Instagram page, the one link of its section); the committee's uploads come right
# after the events (DRIVE_PAGE).
MEDIA_GROUPS = [
    ("episode", "/listen/"),
    ("video", "/watch/"),
    ("post", "/instagram/"),
    ("pdf", "/library/"),
]
DRIVE_PAGE = "/portfolio/"


def log(msg: str) -> None:
    line = f"[digest] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:             # a console that is not UTF-8 (Windows cp1252): keep the log line
        print(line.encode("ascii", "backslashreplace").decode("ascii"), flush=True)


# ---------------------------------------------------------------------------- config
def _mini_yaml(text: str) -> dict:
    """Fallback reader for config/site.yml when PyYAML is missing: understands the
    simple `section:` / `  key: scalar` shape used by the settings we need."""
    out: dict[str, Any] = {}
    section = None
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            section = m.group(1)
            out[section] = {} if not m.group(2) else _scalar(m.group(2))
            continue
        m = re.match(r"^  ([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and section and isinstance(out.get(section), dict) and m.group(2):
            out[section][m.group(1)] = _scalar(m.group(2))
    return out


def _scalar(v: str) -> Any:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v


def load_config() -> dict:
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
    except OSError as e:
        log(f"could not read {CONFIG_PATH}: {e}")
        return {}
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return _mini_yaml(text)
    except Exception as e:  # malformed YAML → use what the simple reader can get
        log(f"config/site.yml could not be parsed fully ({e}); using the simple reader")
        return _mini_yaml(text)


def load_file(name: str) -> dict:
    """A whole data/site file ({} when missing or broken — a broken file never stops the digest)."""
    try:
        with open(SITE_DIR / f"{name}.json", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"could not read data/site/{name}.json: {e}")
        return {}


def load_items(name: str) -> list[dict]:
    p = SITE_DIR / f"{name}.json"
    shown = f"data/site/{name}.json"
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items") if isinstance(data, dict) else None
        return [i for i in (items or []) if isinstance(i, dict)]
    except FileNotFoundError:
        log(f"{shown} not found — section will be empty")
    except Exception as e:  # corrupt JSON must never stop the digest
        log(f"could not read {shown}: {e}")
    return []


# ---------------------------------------------------------------------------- time
try:
    from zoneinfo import ZoneInfo

    TZ: Any = ZoneInfo("America/Chicago")
except Exception:  # pragma: no cover — no tz database (rare on Windows without tzdata)
    TZ = None


def to_central(dt: datetime) -> datetime:
    if TZ is not None:
        return dt.astimezone(TZ)
    # Fallback: US DST rule (2nd Sunday of March → 1st Sunday of November, 2 AM local).
    y = dt.year
    mar = date(y, 3, 8 + (6 - date(y, 3, 8).weekday()) % 7)
    nov = date(y, 11, 1 + (6 - date(y, 11, 1).weekday()) % 7)
    dst_start = datetime(y, 3, mar.day, 8, tzinfo=timezone.utc)
    dst_end = datetime(y, 11, nov.day, 7, tzinfo=timezone.utc)
    off = -5 if dst_start <= dt.astimezone(timezone.utc) < dst_end else -6
    return dt.astimezone(timezone(timedelta(hours=off), "CDT" if off == -5 else "CST"))


def parse_dt(v: Any) -> datetime | None:
    """ISO string / date-only → aware UTC datetime (date-only = noon UTC, like the site)."""
    if not v or not isinstance(v, str):
        return None
    s = v.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return datetime.fromisoformat(s + "T12:00:00+00:00")
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_date_only(v: Any) -> bool:
    return isinstance(v, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()))


def central_day(v: Any) -> date | None:
    """The calendar day (America/Chicago) of an ISO timestamp; a date-only value is that day."""
    if is_date_only(v):
        return date.fromisoformat(v.strip())
    dt = parse_dt(v)
    return to_central(dt).date() if dt else None


def end_of_day(v: str | date) -> datetime:
    """Date-only 'YYYY-MM-DD' → the midnight after that day, Central time (committee.js chicagoDayEndMs).
    waiting_for uses it for the moment a month ends: 00:00 Central on the 1st of the next month."""
    d = v if isinstance(v, date) else date.fromisoformat(v.strip())
    nxt = d + timedelta(days=1)
    if TZ is not None:
        return datetime(nxt.year, nxt.month, nxt.day, 0, 0, tzinfo=TZ)
    off = to_central(datetime(nxt.year, nxt.month, nxt.day, 12, tzinfo=timezone.utc)).utcoffset() or timedelta(hours=-6)
    return datetime(nxt.year, nxt.month, nxt.day, 0, 0, tzinfo=timezone(off))


def month_add(key: str, n: int) -> str:
    """'2026-01' + (-1) → '2025-12'."""
    y, m = (int(x) for x in key.split("-"))
    i = y * 12 + (m - 1) + n
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def month_days(key: str) -> tuple[date, date]:
    """'2026-02' → (2026-02-01, 2026-02-28)."""
    y, m = (int(x) for x in key.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def edition_of(now: datetime, key: str | None = None) -> dict:
    """The edition shown at `now`: the Central-time month BEFORE now's (October 1–31 → the September
    digest), or the one covering an explicit 'YYYY-MM': the month it covers (key, first, last) and the
    month it comes out in (out, out_first — its toolkit pointer). (community.js digestEdition)"""
    k = key if key and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", key) else month_add(to_central(now).strftime("%Y-%m"), -1)
    first, last = month_days(k)
    out = month_add(k, 1)
    return {"key": k, "first": first, "last": last, "out": out, "out_first": month_days(out)[0]}


def month_word(key: str, lang: str) -> str:
    """'2026-09' → "September" / "septiembre"."""
    return MONTHS[lang][int(key[5:7]) - 1]


def month_label(key: str, lang: str) -> str:
    """'2026-09' → "September 2026" / "septiembre de 2026" (the /monthly/ page's label)."""
    return f"{month_word(key, lang)} de {key[:4]}" if lang == "es" else f"{month_word(key, lang)} {key[:4]}"


def fmt_day(dt: datetime, lang: str, weekday: bool = True, year: bool = False) -> str:
    """A Central-time day as the website writes it (Intl, see MONTHS_SHORT): "Sat, Sep 12" / "sáb, 12 de
    sept" (+ ", 2027" / " de 2027"); without the weekday "Sep 12" / "12 sept" (+ ", 2027" / " 2027").
    Spanish stays lower-case: the caller capitalizes a day that starts a line."""
    d = to_central(dt)
    if lang == "es":
        mon = MONTHS_SHORT["es"][d.month - 1]
        if weekday:
            return f"{DAYS_SHORT['es'][d.weekday()]}, {d.day} de {mon}" + (f" de {d.year}" if year else "")
        return f"{d.day} {mon}" + (f" {d.year}" if year else "")
    s = f"{MONTHS_SHORT['en'][d.month - 1]} {d.day}"
    if weekday:
        s = f"{DAYS_SHORT['en'][d.weekday()]}, {s}"
    return s + (f", {d.year}" if year else "")


# ---------------------------------------------------------------------------- item helpers
def tx(item: dict, field: str, lang: str) -> str:
    """Field in the requested language (build_data's i18n block), else the original."""
    i18n = (item.get("i18n") or {}).get(field) or {}
    val = i18n.get(lang) or i18n.get(item.get("lang") or "") or item.get(field)
    if val is None and field == "body_md":
        val = (item.get("extra") or {}).get("body_md")
    return str(val or "").strip()


def tr(item: dict | None, field: str, lang: str) -> str:
    """The /monthly/ month model's rule (monthly.js tr): i18n[lang], else i18n.en, else the field
    (or extra[field]) as written."""
    if not item:
        return ""
    i = (item.get("i18n") or {}).get(field) or {}
    for k in (lang, "en"):
        if isinstance(i.get(k), str) and i[k].strip():
            return i[k].strip()
    return str(item.get(field) or (item.get("extra") or {}).get(field) or "").strip()


def tx_extra(item: dict, field: str, lang: str) -> str:
    """An `extra` field (issue_label, topic, section, album …) in the requested language: build_data's
    i18n copy when it has that language, else the original value."""
    val = ((item.get("i18n") or {}).get(field) or {}).get(lang) or (item.get("extra") or {}).get(field)
    return str(val or "").strip()


def is_machine(item: dict, lang: str) -> bool:
    return lang in (item.get("machine") or [])


def one_line(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


# JavaScript's a.localeCompare(b) (en-US, the Unicode root order) — how the website sorts ids and titles
# that tie — so the e-mail lists things in the same order: spaces and punctuation < digits < letters;
# accents, then case (lower-case first) only break ties. Curly quotes and the no-break space count as
# their plain forms ("variants"). Characters not listed here go after the letters.
_COLLATE = {c: i for i, c in enumerate(
    " _-\u2013\u2014,;:!\u00a1?\u00bf.\u2026\u00b7'\"\u00ab\u00bb()[]{}@*/\\&#%\u2022`^\u00b0\u00a9\u00ae+<=>|~$\u00a3\u20ac"
    "0123456789abcdefghijklmnopqrstuvwxyz")}
_VARIANT = {"\u00a0": (" ", 1), "\u2018": ("'", 1), "\u2019": ("'", 2), "\u201c": ('"', 1), "\u201d": ('"', 2)}


def js_order(v: Any) -> tuple:
    """A sort key: sorted(xs, key=js_order) == xs.sort((a, b) => a.localeCompare(b)) for ids and titles."""
    s = str(v or "")
    primary: list[int] = []
    accent: list[int] = []
    case: list[int] = []
    for c in unicodedata.normalize("NFD", s):
        if unicodedata.combining(c):
            if accent:
                accent[-1] = 1
            continue
        plain, variant = _VARIANT.get(c, (c, 1 if c.isupper() else 0))
        primary.append(_COLLATE.get(plain.lower(), 1000 + ord(plain.lower())))
        accent.append(0)
        case.append(variant)
    return tuple(primary), tuple(accent), tuple(case), s


def media_title(item: dict, lang: str) -> str:
    """A podcast episode / video title without its "[Season 11, Episode 12]" tail (the badge says it),
    like the website's media titles."""
    t = tx(item, "title", lang)
    s = ONE_SUFFIX.sub("", SE_SUFFIX.sub("", t)).strip()
    return s or t


def title_of(item: dict, lang: str) -> str:
    return media_title(item, lang) if item.get("kind") in ("episode", "video") else (tx(item, "title", lang) or str(item.get("title") or ""))


def group_of(item: dict) -> str:
    """Which What's New group an item belongs to (community.js groupOf)."""
    k = item.get("kind")
    if k in ("announcement", "event", "article", "episode", "post", "topic"):
        return k
    if k == "video":
        return "drive" if item.get("source") == "drive" else "video"
    if k == "pdf":
        return "drive" if item.get("source") == "drive" else "pdf"
    if item.get("source") == "drive" or k in ("document", "slides", "photo", "video_file", "form"):
        return "drive"
    return "other"


def is_department(item: dict) -> bool:
    """An "In Every Issue" page (AA News, Dear Grapevine, Discussion Topic …), not a member's story."""
    ex = item.get("extra") or {}
    return ex.get("department") is True or bool(EVERY_ISSUE.search(str(ex.get("section") or "")))


class Links:
    def __init__(self, site_url: str):
        self.base = site_url.rstrip("/")

    def page(self, path: str, lang: str) -> str:
        path = path if path.startswith("/") else "/" + path
        return self.base + ("/es" if lang == "es" else "") + path

    def asset(self, path: str) -> str:
        """A site file (never language-prefixed): '/assets/cache/…' → the full address."""
        return path if path.startswith(("http://", "https://")) else self.base + ("" if path.startswith("/") else "/") + path

    def site_path(self, path: str, lang: str) -> str:
        """A site path written in a bulletin post: a file ("/bulletin/files/flyer.pdf") or a path that
        names its language as it is; a page in the e-mail's language ("/events/" → …/es/events/)."""
        bare = path.split("#")[0].split("?")[0]
        if re.search(r"(?i)[.][a-z0-9]{2,5}$", bare) or re.match(r"/(en|es)(/|$)", bare):
            return self.asset(path)
        return self.page(path, lang)

    def item(self, item: dict, lang: str, fallback_page: str) -> str:
        ex = item.get("extra") or {}
        url = item.get("url") or ex.get("view_url") or ""
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("/"):
            return self.page(url, lang)
        return self.page(fallback_page, lang)


def item_label(item: dict, lang: str) -> tuple[str, str, str]:
    """(label, text color, background) for the little pill in front of an item."""
    src, kind = item.get("source"), item.get("kind")
    if kind == "article":
        return ("La Viña", C["lv"], C["lv_soft"]) if item.get("category") == "lv" or src == "lavina" \
            else ("Grapevine", C["gv"], C["gv_soft"])
    if kind == "episode":
        # Two shows (config sources.podcasts): the magazine's podcast ("gv") and the
        # Grapevine Weekly Open AA Meeting ("wo"), which gets its own pill.
        show = item.get("category") or (item.get("extra") or {}).get("show")
        return (T[lang]["weekly_open"] if show == "wo" else "Podcast"), C["grape"], C["grape_soft"]
    if kind in ("video", "video_file") and src != "drive":
        return "Video", C["grape"], C["grape_soft"]
    if kind == "pdf" and src != "drive":
        host = (item.get("extra") or {}).get("host") or ""
        doc = "Documento" if lang == "es" else "Document"
        return (f"{doc} · La Viña", C["lv"], C["lv_soft"]) if "lavina" in host else (f"{doc} · Grapevine", C["gv"], C["gv_soft"])
    if kind == "announcement":
        return ("Boletín" if lang == "es" else "Bulletin"), C["vine"], C["vine_soft"]
    if src == "drive":
        en, es = DRIVE_CATEGORIES.get(item.get("category") or "other", DRIVE_CATEGORIES["other"])
        return (es if lang == "es" else en), C["vine"], C["vine_soft"]
    return "", C["muted"], C["surface2"]


def localize_months(label: str, lang: str) -> str:
    """'October 2026' ⇄ 'octubre 2026' so issue labels read naturally in each section (Spanish month
    names are lower-case; in_sentence adds the "de")."""
    src, dst = ("en", "es") if lang == "es" else ("es", "en")
    for a, b in zip(MONTHS[src], MONTHS[dst]):
        label = re.sub(rf"\b{a}\b", b if lang == "es" else b.capitalize(), label, flags=re.I)
    return label


def in_sentence(label: str, lang: str) -> str:
    """An issue label inside a line of text (community.js issueInSentence): Spanish months lower-case
    and "de" before the year — "Septiembre / Octubre 2026" → "septiembre/octubre de 2026"."""
    s = one_line(label)
    if lang != "es":
        return s
    m = re.fullmatch(r"(.*?)\s+(?:de\s+)?(\d{4})", s)
    if not m:
        return s
    months = [w.lower() if w.lower() in MONTHS["es"] else w for w in re.split(r"\s*/\s*", m.group(1))]
    return f"{'/'.join(months)} de {m.group(2)}"


def issue_label(item: dict, lang: str) -> str:
    """The item's issue as it reads inside a line: "October 2026" / "octubre de 2026"."""
    label = ((item.get("i18n") or {}).get("issue_label") or {}).get(lang)
    return in_sentence(str(label).strip() if label else localize_months(str((item.get("extra") or {}).get("issue_label") or ""), lang), lang)


def pub_of(item: dict) -> str:
    """'lv' for La Viña (in Spanish), 'gv' for Grapevine (in English)."""
    ex = item.get("extra") or {}
    return "lv" if ex.get("publication") == "lv" or item.get("source") == "lavina" or item.get("category") == "lv" else "gv"


def other_lang(pub: str, lang: str) -> str:
    """" (in Spanish)" after La Viña in the English half, " (en inglés)" after Grapevine in the
    Spanish half (like the website and the district report); "" when the magazine is in `lang`."""
    return f" ({T[lang]['in_other']})" if (pub == "lv") != (lang == "es") else ""


def item_meta(item: dict, lang: str) -> str:
    """The small line under an item: an issue and its section, "S11 · E12 · 32 min" … and the item's own
    date — a committee file's is the date in its name, which may be before the month it was added in (the
    year then too, when it differs)."""
    ex = item.get("extra") or {}
    kind = item.get("kind")
    parts: list[str] = []
    d = parse_dt(item.get("date") or item.get("_when"))
    counted = parse_dt(item.get("_when"))
    other_year = bool(d and counted and to_central(d).year != to_central(counted).year)
    if kind == "article":
        if ex.get("issue_label"):
            parts.append(issue_label(item, lang))
        topic_field = "topic" if ex.get("topic") else "section" if ex.get("section") else None
        if topic_field:
            parts.append(tx_extra(item, topic_field, lang))
    elif kind == "episode":
        if ex.get("season") and ex.get("episode"):
            parts.append(T[lang]["episode_se"].format(s=ex["season"], e=ex["episode"]))
        if ex.get("duration_sec"):
            parts.append(T[lang]["min"].format(n=max(1, round(int(ex["duration_sec"]) / 60))))
        if d:
            parts.append(fmt_day(d, lang, weekday=False))
    elif kind == "video":
        if d:
            parts.append(fmt_day(d, lang, weekday=False))
        if ex.get("duration_sec"):
            parts.append(T[lang]["min"].format(n=max(1, round(int(ex["duration_sec"]) / 60))))
    elif kind == "pdf" and item.get("source") != "drive":
        if ex.get("pages"):
            many, one = T[lang]["pages"]
            parts.append(one if str(ex["pages"]).strip() == "1" else many.format(n=ex["pages"]))
        host = str(ex.get("host") or "").replace("www.", "")
        if host:
            parts.append(host)
    else:
        if d:
            parts.append(fmt_day(d, lang, weekday=False, year=other_year))
    return " · ".join(p for p in parts if p)


def _link_url(url: str, resolve=None) -> str:
    """A post's link as a full address: a web or mail address as it is; a site path ("/events/", a
    file saved next to the post: "/bulletin/files/…") through `resolve` (Links.site_path); else ""."""
    if re.match(r"https?://|mailto:", url):
        return url
    return resolve(url) if resolve and url.startswith("/") and not url.startswith("//") else ""


# ---- a bulletin post's Markdown in the e-mail
# A post is whatever the chair wrote (content/bulletin/README.md: headings, lists inside lists,
# quotations, tables, lines of ---, code, pictures, links). md_blocks reads it into blocks; md_to_html
# draws them with inline styles (what e-mail programs keep) and md_to_text writes them as plain lines —
# never the raw marks ("| Time | What |", "> …", "---").
_MD_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_MD_HEAD = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
_MD_RULE = re.compile(r"^\s{0,3}(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")
_MD_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$")
_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _md_cells(line: str) -> list[str]:
    t = line.strip()
    t = t[1:] if t.startswith("|") else t
    t = t[:-1] if t.endswith("|") and not t.endswith("\\|") else t
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", t)]


def md_blocks(s: str) -> list[tuple[str, Any]]:
    """A post's Markdown → [(kind, data)]: ("p", [lines]) · ("h", text) · ("list", [(depth, ordered,
    text)]) · ("quote", [lines]) · ("table", {"head": [cells] | None, "rows": [[cells]]}) · ("hr", None)
    · ("code", [lines])."""
    blocks: list[tuple[str, Any]] = []
    lines = (s or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _MD_FENCE.match(line):
            fence, body = _MD_FENCE.match(line).group(1), []
            i += 1
            while i < n and not lines[i].lstrip().startswith(fence):
                body.append(lines[i])
                i += 1
            blocks.append(("code", body))
            i += 1
            continue
        if m := _MD_HEAD.match(line):
            blocks.append(("h", m.group(2)))
            i += 1
            continue
        if _MD_RULE.match(line):
            blocks.append(("hr", None))
            i += 1
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while i < n and lines[i].strip() and lines[i].lstrip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]).lstrip(">").strip())
                i += 1
            blocks.append(("quote", [q for q in quote if q]))
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i])
                i += 1
            head = None
            if len(rows) > 1 and _MD_TABLE_SEP.match(rows[1]):
                head, rows = _md_cells(rows[0]), rows[2:]
            blocks.append(("table", {"head": head, "rows": [_md_cells(r) for r in rows if not _MD_TABLE_SEP.match(r)]}))
            continue
        if _MD_ITEM.match(line):
            items: list[list] = []
            indents: list[int] = []
            while i < n and lines[i].strip():
                m = _MD_ITEM.match(lines[i])
                if m:
                    ind = len(m.group(1).expandtabs(4))
                    if items and ind <= indents[0] and (m.group(2)[-1] in ".)") != items[0][1]:
                        break                                  # "- a" then "1. b": a new list
                    while indents and indents[-1] > ind:
                        indents.pop()
                    if not indents or indents[-1] < ind:
                        indents.append(ind)
                    items.append([len(indents) - 1, m.group(2)[-1] in ".)", m.group(3).strip()])
                elif items:
                    items[-1][2] += "\n" + lines[i].strip()      # a line that goes on the item above
                i += 1
            blocks.append(("list", [tuple(x) for x in items]))
            continue
        para = []
        while i < n and lines[i].strip() and not (_MD_FENCE.match(lines[i]) or _MD_HEAD.match(lines[i]) or _MD_ITEM.match(lines[i])
                                                  or lines[i].lstrip().startswith((">", "|"))):
            if para and re.match(r"^\s{0,3}(=+|-+)\s*$", lines[i]):   # "Title" underlined: a heading
                blocks.append(("h", " ".join(para)))
                para = []
                i += 1
                break
            if _MD_RULE.match(lines[i]):
                break
            para.append(lines[i].strip())
            i += 1
        if para:
            blocks.append(("p", para))
    return blocks


def _md_inline_text(t: str, resolve=None) -> str:
    t = re.sub(r"!\[([^\]]*)\]\(<?([^\s)>]+)>?\)", lambda m: f"[{m.group(1).strip() or m.group(2).rsplit('/', 1)[-1]}]({m.group(2)})", t)
    t = re.sub(r"\[([^\]]+)\]\(<?([^\s)>]+)>?\)", lambda m: f"{m.group(1)} ({u})" if (u := _link_url(m.group(2), resolve)) else m.group(1), t)
    t = re.sub(r"<(https?://[^>\s]+)>", r"\1", t)
    t = re.sub(r"(\*\*|__|~~)(?=\S)(.+?)(?<=\S)\1", r"\2", t)
    t = re.sub(r"(?<![\w*])([*_])(?=\S)(.+?)(?<=\S)\1(?![\w*])", r"\2", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def _md_inline_html(t: str, link_color: str, resolve=None) -> str:
    t = html.escape(t.strip(), quote=False)
    # a picture: a link to it (its words, else its file name); "<…>" around an address was escaped above
    t = re.sub(r"!\[([^\]]*)\]\((?:&lt;(.+?)&gt;|([^\s)]+))\)",
               lambda m: f"[{m.group(1).strip() or (m.group(2) or m.group(3)).rsplit('/', 1)[-1]}]({m.group(2) or m.group(3)})", t)

    def link(m: re.Match) -> str:
        url = _link_url(html.unescape(m.group(2) or m.group(3)), resolve)
        return f'<a href="{html.escape(url)}" style="color:{link_color};">{m.group(1)}</a>' if url else m.group(1)
    t = re.sub(r"\[([^\]]+)\]\((?:&lt;(.+?)&gt;|([^\s)]+))\)", link, t)
    t = re.sub(r"&lt;(https?://[^\s&]+)&gt;", lambda m: f'<a href="{m.group(1)}" style="color:{link_color};">{m.group(1)}</a>', t)
    t = re.sub(r"`([^`]+)`", r'<code style="font-family:Consolas,Menlo,monospace;font-size:13px;">\1</code>', t)
    t = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"<strong>\2</strong>", t)
    t = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"<s>\1</s>", t)
    t = re.sub(r"(?<![\w*])([*_])(?=\S)(.+?)(?<=\S)\1(?![\w*])", r"<em>\2</em>", t)
    return t


def md_to_text(s: str, resolve=None) -> str:
    """A post as plain text lines (the e-mail's text part): headings and paragraphs on lines of their
    own, list items as "• item" (indented under their parent), a table's rows as "cell · cell", quotes
    without their ">", links as "words (address)"."""
    out = []
    for kind, data in md_blocks(s):
        if kind == "p":
            out.append("\n".join(_md_inline_text(x, resolve) for x in data))
        elif kind == "h":
            out.append(_md_inline_text(data, resolve))
        elif kind == "list":
            out.append("\n".join("  " * d + ("– " if d else "• ") + _md_inline_text(t, resolve).replace("\n", " ") for d, _o, t in data))
        elif kind == "quote":
            out.append("\n".join("“" + _md_inline_text(x, resolve) + "”" if len(data) == 1 else _md_inline_text(x, resolve) for x in data))
        elif kind == "table":
            rows = ([data["head"]] if data["head"] else []) + data["rows"]
            out.append("\n".join(" · ".join(_md_inline_text(c, resolve) for c in r if c.strip()) for r in rows))
        elif kind == "code":
            out.append("\n".join(data))
    return "\n\n".join(b for b in out if b.strip()).strip()


def md_to_html(s: str, link_color: str, resolve=None) -> str:
    """A post's Markdown for the e-mail (md_blocks), with inline styles: paragraphs and line breaks,
    headings as bold lines, lists (inside lists too), quotations, tables, lines of ---, code, **bold**,
    *italic*, ~~crossed out~~, [links](https://…) — a link to the site too, when `resolve` makes it a full
    address (_link_url); a picture becomes a link to it. Everything else is escaped."""
    inl = lambda t: _md_inline_html(t, link_color, resolve)   # noqa: E731
    out = []
    for kind, data in md_blocks(s):
        if kind == "p":
            out.append(f'<p style="margin:0 0 10px;">{"<br>".join(inl(x) for x in data)}</p>')
        elif kind == "h":
            out.append(f'<p style="margin:14px 0 6px;font-weight:bold;">{inl(data)}</p>')
        elif kind == "list":
            html_list, depth_open = [], []
            for d, ordered, t in data:
                while len(depth_open) > d + 1:
                    html_list.append(f"</li></{depth_open.pop()}>")
                if len(depth_open) == d + 1:
                    html_list.append("</li>")
                while len(depth_open) < d + 1:
                    tag = "ol" if ordered else "ul"
                    depth_open.append(tag)
                    html_list.append(f'<{tag} style="margin:{"0 0 10px" if len(depth_open) == 1 else "4px 0 0"};padding-left:22px;">')
                html_list.append(f'<li style="margin:0 0 4px;">{inl(t).replace(chr(10), "<br>")}')
            while depth_open:
                html_list.append(f"</li></{depth_open.pop()}>")
            out.append("".join(html_list))
        elif kind == "quote":
            out.append(f'<blockquote style="margin:0 0 10px;padding:2px 0 2px 12px;border-left:3px solid {C["line"]};color:{C["muted"]};">'
                       f'{"<br>".join(inl(x) for x in data)}</blockquote>')
        elif kind == "table":
            cell = f'padding:5px 8px;border:1px solid {C["line"]};vertical-align:top;text-align:left;'
            rows = []
            if data["head"]:
                rows.append("<tr>" + "".join(f'<th style="{cell}background:{C["surface2"]};">{inl(c)}</th>' for c in data["head"]) + "</tr>")
            rows += ["<tr>" + "".join(f'<td style="{cell}">{inl(c)}</td>' for c in r) + "</tr>" for r in data["rows"]]
            out.append(f'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;margin:0 0 10px;font-size:13px;line-height:1.45;">'
                       f'{"".join(rows)}</table>')
        elif kind == "hr":
            out.append(f'<hr style="border:0;border-top:1px solid {C["line"]};margin:12px 0;">')
        elif kind == "code":
            out.append(f'<pre style="margin:0 0 10px;padding:8px 10px;background:{C["surface2"]};font-family:Consolas,Menlo,monospace;'
                       f'font-size:12px;white-space:pre-wrap;">{html.escape(chr(10).join(data), quote=False)}</pre>')
    return "".join(out)


def md_excerpt(s: str, limit: int) -> tuple[str, bool]:
    """The first whole blocks of a post that fit in `limit` characters (tables, lists and quotes are
    never cut in half) → (Markdown, cut?). A first block longer than that becomes its plain words,
    shortened."""
    s = (s or "").strip()
    if len(s) <= limit:
        return s, False
    parts, size = [], 0
    for chunk in re.split(r"\n\s*\n", s):
        if parts and size + len(chunk) > limit:
            break
        if not parts and len(chunk) > limit:
            return shorten(md_to_text(chunk), limit - 100), True
        parts.append(chunk)
        size += len(chunk) + 2
    while len(parts) > 1 and _MD_RULE.match(parts[-1].strip()):
        parts.pop()                                            # a line of --- that led to what was cut
    return "\n\n".join(parts), True


def shorten(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",;:.- ") + "…"


# ---------------------------------------------------------------------------- collect
def later_of(a: str | None, b: str | None) -> str | None:
    """The later of two news dates by their Central calendar day (community.js laterOf): `b` only when its
    day is after `a`'s (or there is no `a`), so on the same day `a` keeps its own time."""
    da = central_day(a) if a else None
    db = central_day(b) if b else None
    return b if db and (not da or db > da) else (a or None)


def post_when(item: dict) -> str | None:
    """A bulletin post's news date (community.js postWhen): the day it was ADDED to the site — when the site
    first had it (first_seen; its own `date` instead when that is the same Central day, for its time, or when
    there is no first_seen), and never before its `publish` day (a post scheduled with `publish:` appears
    that morning). Its `date` is only the post's label: one dated in an earlier month but added later
    (written on the 28th, saved on the 2nd — after that month's e-mail went out) is in the edition of the
    month it appeared, like a committee upload (upload_when); one dated AHEAD (a notice dated with its
    event's day, saved on the 25th) is in the edition of the month it was added too — by that event's month
    it has usually expired, and it would be in no edition (build_data.effective_ts: a date more than a day
    ahead → first_seen, What's New's rule). Every post is in exactly one edition."""
    pub = str((item.get("extra") or {}).get("publish") or "")[:10]
    seen = item.get("first_seen") or None
    day = item.get("date") or None
    base = day if day and (not seen or central_day(day) == central_day(seen)) else seen
    return later_of(base, pub if is_date_only(pub) else None)


def upload_when(item: dict) -> str | None:
    """A committee upload's news date (community.js uploadWhen): the later of its date (the date its name
    starts with, else when the photo was taken or the file created — drive.py) and when the site first had
    it (first_seen), so each upload is in the edition of the month it was added."""
    return later_of(item.get("date") or None, item.get("first_seen") or None)


def digest_stories(articles: dict) -> list[dict]:
    """The magazine stories the digest reads (community.js digestStories): articles.json stories on the
    site, with a link and an issue."""
    return [a for a in (articles.get("items") or []) if isinstance(a, dict) and a.get("kind") == "article"
            and a.get("status") != "gone" and a.get("url") and (a.get("extra") or {}).get("issue_key")]


def story_day_of(stories: list[dict]):
    """The day a magazine story counts in (community.js storyDayOf): its extra.pub_date (the day it came
    out online — build_data), else the earliest pub_date of its issue's stories (the day the issue came out
    online). Never first_seen: the stories found at the site's launch would all land in one edition. ""
    when neither is known. Returns a function of a story."""
    def issue_of(a: dict) -> str:
        ex = a["extra"]
        return f"{ex.get('publication') or a.get('category')}|{ex['issue_key']}"
    first: dict[str, str] = {}
    for a in stories:
        pd = a["extra"].get("pub_date")
        if is_date_only(pd) and (issue_of(a) not in first or pd < first[issue_of(a)]):
            first[issue_of(a)] = pd

    def day_of(a: dict) -> str:
        pd = a["extra"].get("pub_date")
        return pd if is_date_only(pd) else first.get(issue_of(a), "")
    return day_of


def is_album_media(item: dict) -> bool:
    """A photo or video of an album on /photos/ (committee.js isPhotoItem) — not a flyer or a slide."""
    return item.get("kind") in PHOTO_KINDS and (item.get("category") in ("photos", "other") or not item.get("category"))


def album_key(item: dict) -> str:
    """The album of a photo (committee.js photoAlbumKey): "f:<Drive sub-folder>" (extra.album; for a loose
    file in "other", its first folder), else "p:<panel number>"."""
    ex = item.get("extra") or {}
    folder = ex.get("album") or (item.get("category") == "other" and ex.get("path") and ex["path"][0]) or None
    return f"f:{folder}" if folder else f"p:{ex.get('panel') or 0}"


def merge_twins(items: list[dict]) -> list[dict]:
    """A podcast episode and its YouTube upload (same Central day, same title or same season/episode)
    are ONE entry: the episode, carrying the video as `_twin` (community.js mergeMediaTwins)."""
    def norm(s: Any) -> str:
        return one_line(s).lower()

    def se(i: dict) -> str:
        ex = i.get("extra") or {}
        return f"{ex['season']}|{ex['episode']}" if ex.get("season") is not None and ex.get("episode") is not None else ""

    eps = [i for i in items if i.get("kind") == "episode"]
    if not eps:
        return items
    twin_of: dict[int, dict] = {}
    taken: set[int] = set()
    for v in items:
        if v.get("kind") != "video" or v.get("source") == "drive":
            continue
        day, t, k = central_day(v["_when"]), norm(v.get("title")), se(v)
        for e in eps:
            if id(e) in taken or central_day(e["_when"]) != day:
                continue
            if (t and norm(e.get("title")) == t) or (k and se(e) == k):
                twin_of[id(v)] = e
                taken.add(id(e))
                break
    if not twin_of:
        return items
    videos = {id(e): v for v in items if id(v) in twin_of for e in [twin_of[id(v)]]}
    return [({**i, "_twin": videos[id(i)]} if id(i) in videos else i) for i in items if id(i) not in twin_of]


def month_news(now: datetime, ed: dict) -> dict[str, list[dict]]:
    """The month's news by group, newest first — the bulletin's pinned posts first, a podcast's YouTube
    twin folded into it, the committee's photos one entry per album (community.js monthNews):
    {"id": "album:<key>", "kind": "album", "_album": True, "_count": photos, "_when": the newest photo's
    date, "_names": {"en", "es"}} (the e-mail links /photos/; the page, the album's own anchor).
    `_when` is the date an item counts on (a scheduled post's `publish` day, a post's or an upload's
    first_seen …); the item keeps its own `date` (a committee file's row shows the date in its name)."""
    today = to_central(now).date().isoformat()
    hi = now + timedelta(days=1)
    found: dict[str, dict] = {}
    for name in NEWS_SOURCES:
        for raw in load_items(name):
            iid = raw.get("id")
            if not iid or raw.get("status") == "gone" or iid in found:
                continue
            g = group_of(raw)
            if g not in NEWS_GROUPS:
                continue
            ex = raw.get("extra") or {}
            if name == "drive" and (raw.get("kind") == "announcement" or ex.get("event_date")):
                continue                     # a bulletin document / a dated flyer (an event, not an upload)
            when = post_when(raw) if raw.get("kind") == "announcement" else upload_when(raw) if name == "drive" else raw.get("date")
            t = parse_dt(when)
            if not t or t > hi:              # undated: never news
                continue
            day = central_day(when)
            if not day or not (ed["first"] <= day <= ed["last"]):
                continue
            if raw.get("kind") == "announcement" and ex.get("expires") and str(ex["expires"])[:10] < today:
                continue
            found[iid] = {**raw, "_when": when, "_group": g}
    # the magazine stories that came out online in the month (story_day_of: extra.pub_date, else their issue's)
    first, last = ed["first"].isoformat(), ed["last"].isoformat()
    stories = digest_stories(load_file("articles"))
    day_of = story_day_of(stories)
    for a in stories:
        iid = a.get("id")
        if not iid or iid in found:
            continue
        pd = day_of(a)
        if not pd or not first <= pd <= last:
            continue
        found[iid] = {**a, "_when": pd, "_group": "article"}
    # the committee's photos: one entry per album
    albums: dict[str, list[dict]] = {}
    for it in found.values():
        if it.get("source") == "drive" and is_album_media(it):
            albums.setdefault(album_key(it), []).append(it)
    for k, members in albums.items():
        for p in members:
            found.pop(p["id"], None)
        newest = members[0]
        for p in members[1:]:
            if parse_dt(p["_when"]) > parse_dt(newest["_when"]):
                newest = p
        folder = k[2:] if k.startswith("f:") else ""
        names = {lang: one_line(((members[0].get("i18n") or {}).get("album") or {}).get(lang) or folder) for lang in ("en", "es")}
        found[f"album:{k}"] = {"id": f"album:{k}", "kind": "album", "source": "drive", "category": "photos",
                               "_group": "drive", "_album": True, "_count": len(members), "_when": newest["_when"],
                               "_names": names, "title": folder, "url": "/photos/", "extra": {},
                               "machine": members[0].get("machine") or []}
    items = sorted(found.values(), key=lambda i: js_order(i.get("id")))
    items.sort(key=lambda i: parse_dt(i["_when"]), reverse=True)
    items = merge_twins(items)
    out = {g: [i for i in items if i["_group"] == g] for g in NEWS_GROUPS}
    out["announcement"].sort(key=lambda i: not (i.get("extra") or {}).get("pinned"))
    return out


def story_pub(a: dict) -> str:
    """A story's magazine as the digest reads it (community.js monthIssues / monthly.js storyPub)."""
    return (a.get("extra") or {}).get("publication") or a.get("category") or ""


def read_pub(item: dict) -> str:
    """read.js pubOf — which magazine /read/ files an item under."""
    ex = item.get("extra") or {}
    p = ex.get("publication") or item.get("publication") or item.get("category")
    if p in ("gv", "lv"):
        return p
    if p == "rlv" or item.get("source") == "lavina":
        return "lv"
    if item.get("source") == "grapevine":
        return "gv"
    refs = " ".join(str((r or {}).get("url") or "") for r in (ex.get("referrers") or []) if isinstance(r, dict))
    host = refs if ex.get("host") == "www.aa.org" else ex.get("host") or item.get("url") or ""
    return "lv" if re.search(r"(?i)lavina", str(host)) else "gv"


def newest_issue_key(articles: dict, pub: str) -> str:
    """The newest issue of a magazine on /read/ (read.js groupIssues(file, pub)[0].key): the newest key
    among its stories on the site (issue_key, else the month of the issue date or the date — a story that is
    `gone` is not on /read/: read.js live()) and articles.json issues[]."""
    def ym(v: Any) -> str:
        m = re.match(r"(\d{4})-(\d{2})", str(v or ""))
        return f"{m.group(1)}-{m.group(2)}" if m else ""
    keys = set()
    for it in articles.get("items") or []:
        if (not isinstance(it, dict) or it.get("status") == "gone" or (it.get("kind") and it.get("kind") != "article")
                or read_pub(it) != pub):
            continue
        ex = it.get("extra") or {}
        k = ex.get("issue_key")
        keys.add(k if isinstance(k, str) and re.fullmatch(r"\d{4}-\d{2}", k) else ym(k) or ym(ex.get("issue_date")) or ym(it.get("date")) or "undated")
    raw = articles.get("issues")
    for m in (raw if isinstance(raw, list) else list(raw.values()) if isinstance(raw, dict) else []):
        if not isinstance(m, dict):
            continue
        p = m.get("publication") if m.get("publication") in ("gv", "lv") else read_pub(m)
        k = m.get("key")
        k = k if isinstance(k, str) and re.fullmatch(r"\d{4}-\d{2}", k) else ym(k) or ym((str(m.get("id") or "").split(":") + [""])[1])
        if p == pub and k:
            keys.add(k)
    dated = sorted((k for k in keys if k != "undated"), reverse=True)
    return dated[0] if dated else ("undated" if keys else "")


def issue_theme(articles: dict, editorial: list[dict], pub: str, key: str, lang: str) -> str:
    """An issue's theme (monthly.js issueTheme — ONE name on the toolkit, the report, the digest): the one
    the issue itself carries (articles.json issues[]: i18n.theme[lang], i18n.theme.en, theme); else the
    one its stories carry (the first story's i18n.issue_theme[lang], else extra.issue_theme); else, for
    Grapevine, the editorial calendar's call for stories (its titles for that issue_key, joined " / ")."""
    meta = next((i for i in (articles.get("issues") or []) if isinstance(i, dict) and i.get("publication") == pub and i.get("key") == key), None)
    own = one_line(tr(meta, "theme", lang)) if meta else ""
    if own:
        return own
    first = next((a for a in (articles.get("items") or []) if isinstance(a, dict) and a.get("kind") == "article"
                  and a.get("status") != "gone" and (a.get("extra") or {}).get("issue_key") == key and story_pub(a) == pub), None)
    told = one_line(((first.get("i18n") or {}).get("issue_theme") or {}).get(lang) or (first.get("extra") or {}).get("issue_theme")) if first else ""
    if told:
        return told
    if pub == "gv":
        themes = [one_line(tr(i, "title", lang)) for i in editorial
                  if (i.get("extra") or {}).get("publication") == "gv" and (i.get("extra") or {}).get("issue_key") == key]
        return " / ".join(t for t in themes if t)
    return ""


def email_image(path: str) -> str:
    """A picture every mail program shows. Classic Outlook for Windows shows no WebP, so one of the
    site's WebP thumbnails (a magazine cover) goes out as the JPEG / PNG copy made next to it
    (scripts/sync/articles.py email_copy) — or not at all (""), never as a blank box."""
    if not path or not path.lower().endswith(".webp"):
        return path or ""
    if path.startswith(("http://", "https://")):
        return ""
    for ext in (".jpg", ".png"):
        alt = path[: -len(".webp")] + ext
        if (ASSET_DIR / alt.lstrip("/")).is_file():
            return alt
    return ""


def month_issues(ed: dict, n: int, skip: set[str] | None = None) -> list[dict]:
    """The magazine issues whose stories came out online in the month (story_day_of; community.js monthIssues):
    Grapevine first, the newest issue key first. Each: the month's stories (count, free), all the
    issue's stories (total), current (the newest issue of its magazine on /read/), label, theme, the
    official page and cover, the /read/ link and `n` highlights — the month's stories minus `skip` (the
    writers' ids / urls), free to read first, then members' stories (not "In Every Issue"), then the
    magazine's order."""
    skip = skip or set()
    data = load_file("articles")
    editorial = load_items("editorial")
    first_day, last_day = ed["first"].isoformat(), ed["last"].isoformat()
    stories = digest_stories(data)
    day_of = story_day_of(stories)
    groups: dict[tuple[str, str], list[dict]] = {}
    for a in stories:
        pub, pd = story_pub(a), day_of(a)
        if pub not in ("gv", "lv") or not pd or not first_day <= pd <= last_day:
            continue
        groups.setdefault((pub, a["extra"]["issue_key"]), []).append(a)
    out = []
    for (pub, key), lst in groups.items():
        meta = next((i for i in (data.get("issues") or []) if isinstance(i, dict)
                     and i.get("publication") == pub and i.get("key") == key), None) or {}
        first = lst[0]

        def label(lang: str) -> str:
            return in_sentence(one_line(((meta.get("i18n") or {}).get("label") or {}).get(lang)) or issue_label(first, lang) or key, lang)

        current = newest_issue_key(data, pub) == key
        ranked = sorted(((i, a) for i, a in enumerate(lst) if a.get("id") not in skip and a.get("url") not in skip),
                        key=lambda x: (x[1]["extra"].get("free") is not True, is_department(x[1]), x[0]))
        out.append({
            "pub": pub, "key": key, "is_lv": pub == "lv", "name": "La Viña" if pub == "lv" else "Grapevine",
            "label": {"en": label("en"), "es": label("es")},
            "theme": {lang: issue_theme(data, editorial, pub, key, lang) for lang in ("en", "es")},
            "url": meta.get("url") or first["extra"].get("issue_url") or "", "cover": meta.get("cover") or "",
            "count": len(lst), "total": sum(1 for a in stories if story_pub(a) == pub and a["extra"]["issue_key"] == key),
            "free": sum(1 for a in lst if a["extra"].get("free") is True),
            "current": current, "read_href": f"/read/#{pub}-current" if current else "/read/",
            "highlights": [a for _, a in ranked[:n]],
        })
    out.sort(key=lambda i: i["key"], reverse=True)
    out.sort(key=lambda i: i["pub"] != "gv")
    return out


def meeting_by_rule(key: str, meeting: dict) -> dict | None:
    """The committee meeting of a month from config/site.yml `meeting:` (monthly.js meetingByRule): the
    `week_of_month`-th `weekday` (default: the 3rd Wednesday; -1 = the last), None on a skip date or
    when the month has no such day; start / end ("HH:MM" Central, default 19:00 / 20:00) as UTC ISO."""
    wd = WEEKDAYS.get(str(meeting.get("weekday") or "wednesday").lower(), 3)
    try:
        n = int(meeting.get("week_of_month") or 3)
    except (TypeError, ValueError):
        return None
    y, m = (int(x) for x in key.split("-"))
    days = calendar.monthrange(y, m)[1]
    if n == -1:
        last_wd = (date(y, m, days).weekday() + 1) % 7            # 0 = Sunday, like JavaScript's getUTCDay()
        d = days - ((last_wd - wd + 7) % 7)
    else:
        first_wd = (date(y, m, 1).weekday() + 1) % 7
        d = 1 + ((wd - first_wd + 7) % 7) + (n - 1) * 7
        if d > days or d < 1:
            return None
    ymd = f"{key}-{d:02d}"
    if ymd in {str(s)[:10] for s in (meeting.get("skip_dates") or [])}:
        return None

    def at(hhmm: Any) -> str:
        h, mi = (int(x) for x in (str(hhmm).split(":") + ["0"])[:2])
        local = datetime(y, m, d, h, mi)
        if TZ is not None:
            return local.replace(tzinfo=TZ).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        off = to_central(datetime(y, m, d, h, mi, tzinfo=timezone.utc)).utcoffset() or timedelta(hours=-6)
        return (local.replace(tzinfo=timezone.utc) - off).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        return {"ymd": ymd, "start": at(meeting.get("start") or "19:00"), "end": at(meeting.get("end") or "20:00")}
    except (TypeError, ValueError):
        return None


def event_start(it: dict) -> str | None:
    return (it.get("extra") or {}).get("start") or it.get("date")


def month_events(now: datetime, ed: dict, cfg: dict) -> list[dict]:
    """The events that took place in the month (community.js monthEventsHeld): every category but the
    committee's, in the month each one starts in, once it has started — plus the month's committee
    meeting (its events.json record, else the `meeting:` rule when there is one) once it has started,
    marked `_committee`. Soonest first. Never "news" on their own (no count, no e-mail)."""
    meeting = cfg.get("meeting") if isinstance(cfg.get("meeting"), dict) else {}
    items = [e for e in load_items("events") if e.get("status") != "gone"]
    out = []
    for e in items:
        s = event_start(e)
        if e.get("category") == "committee" or not s:
            continue
        st, day = parse_dt(s), central_day(s)
        if st and day and ed["first"] <= day <= ed["last"] and st <= now:
            out.append(e)
    rec = next((e for e in items if str(e.get("id") or "").startswith(f"ev:committee:{ed['key']}-")), None)
    cm = None
    if rec and event_start(rec) and central_day(event_start(rec)):
        cm = {"ymd": central_day(event_start(rec)).isoformat(), "start": event_start(rec), "end": (rec.get("extra") or {}).get("end")}
    elif meeting:
        cm = meeting_by_rule(ed["key"], meeting)
    if cm and parse_dt(cm["start"]) and parse_dt(cm["start"]) <= now:
        base = rec or {"kind": "event", "source": "committee", "title": "", "lang": "en", "i18n": {}, "machine": []}
        out.append({**base, "id": f"ev:committee:{cm['ymd']}", "category": "committee", "url": "/meetings/", "date": cm["start"],
                    "extra": {"start": cm["start"], "end": cm["end"], "all_day": False, "location": meeting.get("platform") or "Zoom"},
                    "_committee": True})
    out.sort(key=lambda e: js_order(e.get("id")))
    out.sort(key=lambda e: parse_dt(event_start(e)))
    return out


def month_writers(ed: dict) -> dict[str, list[dict]]:
    """Stories by writers from Area 65 / the rest of Texas published in the month (spotlight.json,
    extra.pub_date in it) — community.js writersPick with since/until."""
    a, b = ed["first"].isoformat(), ed["last"].isoformat()
    out: dict[str, list[dict]] = {"neta65": [], "texas": []}
    seen: set[str] = set()
    for it in load_items("spotlight"):
        ex = it.get("extra") or {}
        scope = (ex.get("geo") or {}).get("scope")
        pd = ex.get("pub_date")
        key = it.get("id") or it.get("url")
        if (it.get("status") == "gone" or it.get("kind") != "article" or not it.get("url") or scope not in out
                or not is_date_only(pd) or not a <= pd <= b or key in seen):
            continue
        seen.add(key)
        out[scope].append(it)
    for lst in out.values():
        lst.sort(key=lambda i: js_order(one_line(i.get("title"))))
        lst.sort(key=lambda i: i["extra"]["pub_date"], reverse=True)
    return out


def month_instagram(posts: list[dict], profiles: dict | None = None) -> list[dict]:
    """The month's Instagram posts (month_news' "post" group, newest first) per account of the magazines
    (community.js monthInstagram) — Grapevine, La Viña, then any other in the order of their key: {key,
    name, username, url (the account on Instagram), count, newest: the IG_NEWEST newest posts}. The e-mail
    shows each account's count and newest posts, its text part only the counts; all of them are on the
    site's /instagram/ page (one link). `profiles` = instagram.json profiles."""
    by: dict[str, list[dict]] = {}
    for p in posts:
        ex = p.get("extra") or {}
        by.setdefault(str(ex.get("account") or p.get("category") or ex.get("username") or ""), []).append(p)
    profiles = profiles if isinstance(profiles, dict) else {}
    out = []
    for key in sorted(sorted(by, key=js_order), key=lambda k: 0 if k == "gv" else 1 if k == "lv" else 2):
        lst = by[key]
        prof = profiles.get(key) if isinstance(profiles.get(key), dict) else {}
        username = re.sub(r"^@", "", str(prof.get("username") or (lst[0].get("extra") or {}).get("username") or ""))
        name = "La Viña" if key == "lv" else "Grapevine" if key == "gv" else one_line(prof.get("name")) or username
        out.append({"key": key, "name": name, "username": username,
                    "url": prof.get("url") or (f"https://www.instagram.com/{username}/" if username else ""),
                    "count": len(lst), "newest": lst[:IG_NEWEST]})
    return out


def post_line(item: dict, lang: str, name: str) -> str:
    """An Instagram post's one line (community.js postLine): its title in `lang` (the caption's first line),
    else — a post without a caption — "An Instagram post from Grapevine"."""
    s = one_line(tx(item, "title", lang))
    generic = IG_GENERIC_TITLE.search(s) or IG_GENERIC_TITLE.search(str(item.get("title") or ""))
    return s if s and not generic else T[lang]["ig_post"].format(name=name)


def collect(now: datetime, month: str | None = None, max_per: int = 5, highlights: int = 3) -> dict:
    """Everything the edition says (the /digest/ page's buildMonthlyDigest): {edition, now, groups,
    issues, writers, events, instagram, machine}."""
    ed = edition_of(now, month)
    data: dict[str, Any] = {"edition": ed, "now": now, "machine": {"en": False, "es": False}}
    data["groups"] = month_news(now, ed)
    data["instagram"] = month_instagram(data["groups"]["post"], load_file("instagram").get("profiles"))
    data["writers"] = month_writers(ed)
    # the writers' stories have their own section: never again among an issue's highlights
    skip = {str(v) for lst in data["writers"].values() for w in lst for v in (w.get("id"), w.get("url")) if v}
    data["issues"] = month_issues(ed, highlights, skip)
    data["events"] = month_events(now, ed, load_config())
    # which languages carry machine translations (for the small footnote): what the HTML shows
    shown = ([i for g, lst in data["groups"].items() if g != "post" for i in lst[:max_per] if not i.get("_album")] + data["events"]
             + [a for iss in data["issues"] for a in iss["highlights"]]
             + [p for acc in data["instagram"] for p in acc["newest"]]
             + [w for lst in data["writers"].values() for w in lst[:max_per]])
    for lang in ("en", "es"):
        data["machine"][lang] = any(is_machine(i, lang) for i in shown)
    return data


def counts(data: dict) -> dict[str, int]:
    """How much the month brought, per kind (COUNT_ORDER; an album counts once)."""
    g = data["groups"]
    drive = g.get("drive") or []
    return {"article": len(g.get("article") or []), "episode": len(g.get("episode") or []), "video": len(g.get("video") or []),
            "post": len(g.get("post") or []), "pdf": len(g.get("pdf") or []), "drive": sum(1 for i in drive if not i.get("_album")),
            "album": sum(1 for i in drive if i.get("_album")), "announcement": len(g.get("announcement") or [])}


def total_count(data: dict) -> int:
    """How much the edition has to tell about its month — nothing means no e-mail. Events that took
    place come round every month (the booth, the committee meeting), so on their own they never turn a
    quiet month (or a site whose updates stopped) into an e-mail."""
    return sum(counts(data).values()) + sum(len(v) for v in data["writers"].values())


def count_list(data: dict, lang: str) -> str:
    """"89 magazine stories, 8 podcast episodes … and 1 bulletin post" (community.js digestCountList)."""
    parts = []
    for g, n in ((g, counts(data)[g]) for g in COUNT_ORDER):
        if n:
            many, one = T[lang]["n"][g]
            parts.append(one if n == 1 else many.format(n=n))
    if len(parts) < 2:
        return parts[0] if parts else ""
    return f"{', '.join(parts[:-1])} {T[lang]['and']} {parts[-1]}"


def intro(data: dict, lang: str) -> str:
    """The edition's one-sentence intro (community.js digestIntro)."""
    v = {"prev": month_word(data["edition"]["key"], lang)}
    lst = count_list(data, lang)
    return T[lang]["intro"].format(list=lst, **v) if lst else T[lang]["intro_quiet"].format(**v)


# ---------------------------------------------------------------------------- rows (shared by HTML + text)
def build_rows(group: str, items: list[dict], lang: str, links: Links, page: str, max_per: int) -> tuple[list[dict], int]:
    """Turn items into display rows (at most max_per; the number left out is returned too). A photo
    album is one row — the pill "Photos", its name ("New photos" without one) and how many photos,
    linking to /photos/; a podcast episode carries its YouTube twin's link."""
    t = T[lang]
    rows: list[dict] = []
    for it in items:
        if it.get("_album"):
            n = it.get("_count") or 1
            rows.append({"label": DRIVE_CATEGORIES["photos"][1 if lang == "es" else 0], "fg": C["vine"], "bg": C["vine_soft"],
                         "title": (it.get("_names") or {}).get(lang) or t["album_plain"], "url": links.page("/photos/", lang),
                         "meta": t["new_photo"] if n == 1 else t["new_photos"].format(n=n), "twin": ""})
            continue
        label, fg, bg = item_label(it, lang)
        twin = it.get("_twin")
        rows.append({"label": label, "fg": fg, "bg": bg, "title": title_of(it, lang),
                     "url": links.item(it, lang, page), "meta": item_meta(it, lang),
                     "twin": links.item(twin, lang, "/watch/") if twin else ""})
    extra = max(0, len(rows) - max_per)
    return rows[:max_per], extra


def event_row(it: dict, lang: str, links: Links, as_of: date | None = None) -> dict:
    """An event that took place, as the e-mail lists it: its day(s) only — "Sat, Sep 12", or over several
    days "Fri, Jun 25 – Sun, Jun 27" (the website's rule) — never a time, "every month" or "to be
    confirmed" (it is over). The committee meeting under its own name, linking to /meetings/.
    `as_of` = the last day of the month covered: a day of another year says its year, like the page
    (community.js eventWhen → needsYear: "Thu, Dec 31, 2026 – Sat, Jan 2, 2027")."""
    t = T[lang]
    ex = it.get("extra") or {}
    raw_start, raw_end = ex.get("start") or it.get("date"), ex.get("end")
    st = parse_dt(raw_start)
    en = parse_dt(raw_end) if raw_end else None
    timed = bool(st) and not is_date_only(raw_start) and not ex.get("all_day")
    # An event of several days (an Area assembly, Fri–Sun): "Fri, Mar 19 – Sun, Mar 21", like the website —
    # the same rule as the pages (committee.js multiDay, community.js isMultiDay): all-day over several
    # dates, or a timed event longer than 18 hours; a timed one that only runs past midnight is one day.
    last = None
    if st and en:
        end_day = en if is_date_only(raw_end) else en - timedelta(microseconds=1)   # an end at 00:00 is the day before
        if to_central(end_day).date() > to_central(st).date() and (
                not timed or (en - st).total_seconds() > MULTI_DAY_MIN_HOURS * 3600):
            last = end_day
    first_day = to_central(st).date() if st else None
    last_day = to_central(last).date() if last else first_day
    with_year = bool(as_of and last_day and (last_day.year != as_of.year or (last_day - as_of).days > 183))
    when = fmt_day(st, lang, year=with_year and (not last or first_day.year != last_day.year)) if st else ""
    if last:
        when += " – " + fmt_day(last, lang, year=with_year)
    # The place in this language (content/events `location_es` → i18n.location), as written otherwise.
    where = tx_extra(it, "location", lang) or (t["online"] if ex.get("online_url") else "")
    if it.get("_committee"):
        return {"title": t["committee_meeting"], "when": when, "where": where, "url": links.page("/meetings/", lang)}
    url = it.get("url") or ex.get("flyer_url") or ex.get("online_url") or ""
    url = links.item({**it, "url": url}, lang, "/events/")
    return {"title": tx(it, "title", lang), "when": when, "where": where, "url": url}


def toolkit_block(data: dict, lang: str, links: Links) -> dict:
    """The ONE pointer to what is current: the toolkit of the month the edition goes out in
    ("Coming up in October" → /monthly/2026-10/), shared by the HTML and the text."""
    t = T[lang]
    out = data["edition"]["out"]
    return {"title": t["coming"].format(month=month_word(out, lang)), "text": t["toolkit_text"],
            "label": t["toolkit"].format(month=month_label(out, lang)), "url": links.page(f"/monthly/{out}/", lang)}


def ordered_issues(data: dict, lang: str) -> list[dict]:
    """La Viña first in the Spanish half, Grapevine first in the English half."""
    return sorted(data["issues"], key=lambda i: i["is_lv"] != (lang == "es"))


def ordered_accounts(data: dict, lang: str) -> list[dict]:
    """The Instagram accounts of the month: La Viña's first in the Spanish half (community.js
    instagramByLang), else Grapevine's first."""
    return sorted(data["instagram"], key=lambda a: a["key"] != "lv") if lang == "es" else data["instagram"]


def writer_name(item: dict, lang: str) -> str:
    a = one_line((item.get("extra") or {}).get("author"))
    return T[lang]["anonymous"] if not a or re.fullmatch(r"(?i)anonymous|an[oó]nim[oa]|anon\.?", a) else a


def writer_place(item: dict, lang: str) -> str:
    g = (item.get("extra") or {}).get("geo") or {}
    return one_line(g.get("label_es") if lang == "es" else g.get("label_en")) or one_line(g.get("label_en")) \
        or one_line((item.get("extra") or {}).get("author_location"))


# ---------------------------------------------------------------------------- HTML
def _esc(s: Any) -> str:
    return html.escape(str(s or ""), quote=True)


def subject_of(data: dict, cfg: dict) -> str:
    """"Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026" — the edition's name
    (the month it covers) in both languages."""
    title = (cfg.get("site") or {}).get("title") or "Grapevine / La Viña"
    k = data["edition"]["key"]
    return f"{title} — {T['en']['edition'].format(month=month_label(k, 'en'))} · {T['es']['edition'].format(month=month_label(k, 'es'))}"


def render_html(data: dict, cfg: dict, links: Links, max_per: int, subject: str) -> str:
    site = cfg.get("site") or {}
    title = site.get("title") or "Grapevine / La Viña"
    logo = links.base + "/assets/img/logo-180x180.png"
    ed = data["edition"]
    preheader = shorten(intro(data, "en"), 140)

    sections = [render_lang_html(lang, data, cfg, links, max_per) for lang in ("en", "es")]
    divider = f'<tr><td style="padding:0 32px;"><div style="border-top:2px dashed {C["line"]};height:1px;line-height:1px;">&nbsp;</div></td></tr>'
    committee = site.get("committee") or title
    committee_es = site.get("committee_es") or committee
    contact = site.get("contact_email") or ""
    footer = f"""
<tr><td style="padding:24px 32px 28px;background:{C['surface2']};border-radius:0 0 12px 12px;font-size:12px;line-height:1.6;color:{C['muted']};">
  <p style="margin:0 0 8px;">{_esc(T['en']['footer_why'].format(committee=committee))} {_esc(T['en']['footer_anon'])}</p>
  <p lang="es" style="margin:0 0 8px;">{_esc(T['es']['footer_why'].format(committee=committee_es))} {_esc(T['es']['footer_anon'])}</p>
  <p style="margin:0 0 8px;">{_esc(T['en']['footer_unsub'])} · <span lang="es">{_esc(T['es']['footer_unsub'])}</span></p>
  <p style="margin:0;"><a href="{_esc(links.page('/', 'en'))}" style="color:{C['gv']};">{_esc(links.base.split('://')[-1])}</a>
  {f' · <a href="mailto:{_esc(contact)}" style="color:{C["gv"]};">{_esc(contact)}</a>' if contact else ''}</p>
</td></tr>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{_esc(subject)}</title>
</head>
<body style="margin:0;padding:0;background:{C['paper']};-webkit-text-size-adjust:100%;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{_esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{C['paper']};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
  style="width:100%;max-width:600px;background:{C['surface']};border:1px solid {C['line']};border-radius:12px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:{C['ink']};">
<tr><td style="padding:22px 32px;background:{C['gv_strong']};border-radius:12px 12px 0 0;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
    <td style="padding-right:14px;vertical-align:middle;"><img src="{_esc(logo)}" width="48" height="48" alt="" style="display:block;border:0;border-radius:10px;background:#ffffff;"></td>
    <td style="vertical-align:middle;">
      <div style="font-family:Georgia,'Times New Roman',serif;font-size:22px;line-height:1.2;color:#ffffff;font-weight:bold;">{_esc(title)} · {_esc(T['en']['masthead'])}</div>
      <div style="font-size:13px;color:#cfe3f6;margin-top:3px;">{_esc(committee)} · {_esc(month_label(ed['key'], 'en'))}</div>
    </td></tr></table>
</td></tr>
<tr><td style="padding:12px 32px;background:{C['gv_soft']};font-size:13px;color:{C['gv_strong']};">
  English first · <strong lang="es">Versión en español más abajo</strong>
</td></tr>
{sections[0]}
{divider}
{sections[1]}
{footer}
</table>
</td></tr></table>
</body>
</html>
"""


def render_lang_html(lang: str, data: dict, cfg: dict, links: Links, max_per: int) -> str:
    """One language's half, in the /digest/ page's order: the headline · the bulletin · the events that
    took place · the committee's uploads · the magazines · the writers · podcasts, videos, Instagram
    (per account: the count and its newest posts; one link to /instagram/), documents · (a quiet month) ·
    the pointer to this month's toolkit · the two links to the site."""
    t = T[lang]
    ed = data["edition"]
    prev_w = month_word(ed["key"], lang)
    parts: list[str] = []
    h2 = f"font-family:Georgia,'Times New Roman',serif;font-size:26px;line-height:1.2;margin:0 0 4px;color:{C['ink']};"
    h3 = (f"font-family:Georgia,'Times New Roman',serif;font-size:18px;margin:0 0 10px;color:{C['ink']};"
          f"border-left:4px solid {{color}};padding-left:10px;")
    link_style = f"color:{C['ink']};text-decoration:none;font-weight:600;"
    small = f"font-size:12px;color:{C['muted']};margin-top:3px;"

    def pill(label: str, fg: str, bg: str) -> str:
        return (f'<span style="display:inline-block;font-size:11px;font-weight:bold;letter-spacing:.02em;color:{fg};'
                f'background:{bg};border-radius:999px;padding:2px 8px;margin-right:6px;vertical-align:1px;">{_esc(label)}</span>') if label else ""

    def table(rows: list[str]) -> str:
        return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(rows)}</table>'

    def row(inner: str) -> str:
        return f'<tr><td style="padding:8px 0;border-bottom:1px solid {C["line"]};font-size:15px;line-height:1.4;">{inner}</td></tr>'

    def section(heading: str, color: str, body: str, page: str | None = None, extra: int = 0, count: int | None = None,
                label: str = "") -> str:
        more = ""
        if page:
            more_txt = label or (t["more"].format(n=extra) if extra else t["see_all"])
            more = (f'<p style="margin:8px 0 0;font-size:13px;"><a href="{_esc(links.page(page, lang))}" '
                    f'style="color:{C["gv"]};">{_esc(more_txt)} →</a></p>')
        n = f' <span style="font-family:Arial,sans-serif;font-size:12px;color:{C["muted"]};font-weight:normal;">({count})</span>' if count else ""
        return f"""<tr><td style="padding:22px 32px 4px;">
  <h3 style="{h3.format(color=color)}">{_esc(heading)}{n}</h3>
  {body}{more}
</td></tr>"""

    # ---- headline
    parts.append(f"""<tr><td style="padding:28px 32px 6px;">
  <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:{C['muted']};font-weight:bold;">{_esc(t['lang_name'])} · {_esc(t['masthead'])}</div>
  <h2 style="{h2}">{_esc(t['edition'].format(month=month_label(ed['key'], lang)))}</h2>
  <p style="margin:0 0 10px;font-size:13px;color:{C['gv']};font-weight:bold;">{_esc(t['edition_sub'].format(prev=prev_w))}</p>
  <p style="margin:0;font-size:15px;line-height:1.6;color:{C['ink']};">{_esc(intro(data, lang))}</p>
</td></tr>""")

    # ---- the bulletin's posts
    ann = data["groups"]["announcement"]
    if ann:
        body = []
        for a in ann[:max_per]:
            text = tx(a, "body_md", lang) or tx(a, "summary", lang)
            site = lambda u, lang=lang: links.site_path(u, lang)  # noqa: E731 — a post's links to the site
            # a long post: its first whole blocks, then "Details →" to the post on the site
            short, cut = md_excerpt(text, 700)
            href = _esc(links.item(a, lang, '/bulletin/'))
            more = f'<p style="margin:0 0 10px;"><a href="{href}" style="color:{C["gv"]};">{_esc(t["details"])} →</a></p>' if cut else ""
            body.append(f"""<div style="margin:0 0 14px;">
  <div style="font-size:16px;font-weight:bold;margin:0 0 4px;"><a href="{href}" style="{link_style}">{_esc(tx(a, 'title', lang))}</a></div>
  <div style="font-size:14px;line-height:1.6;color:{C['ink']};">{md_to_html(short, C['gv'], site)}{more}</div>
</div>""")
        parts.append(section(t["announcement"], C["vine"], "".join(body), "/bulletin/", max(0, len(ann) - max_per), len(ann)))

    # ---- the events that took place (days only; the committee meeting under its own name)
    if data["events"]:
        rows = []
        for ev in data["events"]:
            r = event_row(ev, lang, links, ed["last"])
            when = r["when"][:1].upper() + r["when"][1:]           # the day starts its line: "Sáb, 12 de sept"
            rows.append(row(f'<a href="{_esc(r["url"])}" style="{link_style}">{_esc(r["title"])}</a>'
                            f'<div style="font-size:13px;color:{C["muted"]};margin-top:2px;">{_esc(when)}{(" · " + _esc(r["where"])) if r["where"] else ""}</div>'))
        parts.append(section(t["events"].format(prev=prev_w), C["vine"], table(rows)))

    # ---- the committee's uploads, then (after the magazines and the writers) podcasts, videos, Instagram,
    # documents
    def media_section(g: str, page: str, color: str) -> None:
        items = data["groups"].get(g) or []
        if not items:
            return
        if g == "post":
            # Instagram, per account (La Viña first in Spanish): how many posts, the newest ones (their
            # first line and day, on Instagram) — and ONE link, the site's Instagram page (their home)
            body = []
            for acc in ordered_accounts(data, lang):
                many, one = t["ig_n"]
                n = one if acc["count"] == 1 else many.format(n=acc["count"])
                handle = f' <span style="font-weight:normal;color:{C["muted"]};">@{_esc(acc["username"])}</span>' if acc["username"] else ""
                body.append(f'<h4 style="font-size:14px;margin:10px 0 2px;color:{C["ink"]};">{_esc(acc["name"])}{handle}'
                            f'<span style="font-weight:normal;color:{C["muted"]};"> · {_esc(n)}</span></h4>')
                rows = []
                for post in acc["newest"]:
                    d = parse_dt(post.get("_when"))
                    day = f'<div style="{small}">{_esc(fmt_day(d, lang, weekday=False))}</div>' if d else ""
                    rows.append(row(f'<a href="{_esc(links.item(post, lang, page))}" style="{link_style}">'
                                    f'{_esc(post_line(post, lang, acc["name"]))}</a>{day}'))
                body.append(table(rows))
            parts.append(section(t["post"], color, "".join(body), page, 0, len(items), label=t["ig_link"]))
            return
        rows_data, extra = build_rows(g, items, lang, links, page, max_per)
        rows = []
        for r in rows_data:
            twin = f' · <a href="{_esc(r["twin"])}" style="color:{C["gv"]};">{_esc(t["twin"])}</a>' if r.get("twin") else ""
            meta = f'<div style="{small}">{_esc(r["meta"])}{twin}</div>' if (r["meta"] or twin) else ""
            rows.append(row(f'{pill(r["label"], r["fg"], r["bg"])}<a href="{_esc(r["url"])}" style="{link_style}">{_esc(r["title"])}</a>{meta}'))
        parts.append(section(t[g], color, table(rows), page, extra, len(items)))

    media_section("drive", DRIVE_PAGE, C["vine"])

    # ---- new in the magazines: the issues whose stories came out in the month (La Viña first in Spanish)
    body = []
    for iss in ordered_issues(data, lang):
        color = C["lv"] if iss["is_lv"] else C["gv"]
        pic = email_image(iss["cover"])
        cover = (f'<td width="64" style="padding:0 14px 0 0;vertical-align:top;"><img src="{_esc(links.asset(pic))}" width="64" alt="" '
                 f'style="display:block;width:64px;height:auto;border:0;border-radius:6px;"></td>') if pic else ""
        many, one = t["stories"]
        count = one if iss["count"] == 1 else many.format(n=iss["count"])
        if iss["free"]:
            count += " · " + t["free_n"].format(n=iss["free"])
        theme = f'<div style="font-family:Georgia,serif;font-size:19px;font-weight:bold;margin:4px 0 2px;color:{C["ink"]};">“{_esc(iss["theme"][lang])}”</div>' if iss["theme"][lang] else ""
        hl = []
        for a in iss["highlights"][:max_per]:
            by = writer_name(a, lang) if (a.get("extra") or {}).get("author") else ""
            place = writer_place(a, lang) if by else ""
            meta = " · ".join(x for x in (by, place, t["free"] if (a.get("extra") or {}).get("free") is True else t["subscriber"]) if x)
            hl.append(f'<tr><td style="padding:5px 0 5px 12px;border-left:2px solid {color};font-size:14px;line-height:1.4;">'
                      f'<a href="{_esc(a["url"])}" style="{link_style}">{_esc(title_of(a, lang))}</a>'
                      f'<div style="{small}">{_esc(meta)}</div></td></tr>')
        body.append(f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 16px;"><tr>
  {cover}<td style="vertical-align:top;">
    {pill(iss['name'], color, C['lv_soft'] if iss['is_lv'] else C['gv_soft'])}<span style="font-size:13px;font-weight:bold;color:{C['ink']};">{_esc(iss['label'][lang])}</span>{f'<span style="font-size:12px;color:{C["muted"]};">{_esc(other_lang(iss["pub"], lang))}</span>' if other_lang(iss["pub"], lang) else ""}
    {theme}
    <div style="font-size:12px;color:{C['muted']};margin-bottom:8px;">{_esc(count)}</div>
    {table(hl)}
    <p style="margin:8px 0 0;font-size:13px;"><a href="{_esc(links.page(iss['read_href'], lang))}" style="color:{C['gv']};">{_esc(t['issue_more'].format(n=iss['total']))} →</a></p>
  </td></tr></table>""")
    if body:
        parts.append(section(t["issues"], C["gv"], "".join(body)))

    # ---- writers from Area 65 / Texas, published in the month
    W = data["writers"]
    n_writers = sum(len(v) for v in W.values())
    if n_writers:
        body = [f'<p style="margin:0 0 6px;font-size:13px;color:{C["muted"]};">{_esc(t["writers_sub"].format(prev=prev_w))}</p>']
        for key in ("neta65", "texas"):
            lst = W[key]
            if not lst:
                continue
            body.append(f'<h4 style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:{C["muted"]};font-weight:bold;margin:10px 0 2px;">{_esc(t["group_" + key])}</h4>')
            rows = []
            for it in lst[:max_per]:
                place = writer_place(it, lang)
                label, fg, bg = item_label(it, lang)
                issue = issue_label(it, lang)
                meta = " · ".join(x for x in (writer_name(it, lang) + (f", {place}" if place else ""),
                                              (issue + other_lang(pub_of(it), lang)).strip()) if x)
                rows.append(row(f'{pill(label, fg, bg)}<a href="{_esc(it["url"])}" style="{link_style}">{_esc(tx(it, "title", lang))}</a><div style="{small}">{_esc(meta)}</div>'))
            body.append(table(rows))
        parts.append(section(t["writers"], C["lv"], "".join(body), "/published/", 0, n_writers))

    colors = {"episode": C["grape"], "video": C["grape"], "post": C["grape"], "pdf": C["gv"]}
    for g, page in MEDIA_GROUPS:
        media_section(g, page, colors[g])
    if not total_count(data):
        parts.append(f'<tr><td style="padding:16px 32px 0;font-size:14px;color:{C["muted"]};">{_esc(t["nothing"].format(prev=prev_w))}</td></tr>')

    # ---- the ONE pointer to what is current: this month's toolkit
    kit = toolkit_block(data, lang, links)
    parts.append(f"""<tr><td style="padding:22px 32px 4px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{C['surface2']};border-radius:10px;">
  <tr><td style="padding:14px 16px;">
    <h3 style="font-family:Georgia,'Times New Roman',serif;font-size:17px;font-weight:bold;margin:0;color:{C['ink']};">{_esc(kit['title'])}</h3>
    <div style="font-size:14px;line-height:1.5;color:{C['muted']};margin:4px 0 8px;">{_esc(kit['text'])}</div>
    <a href="{_esc(kit['url'])}" style="color:{C['gv']};font-weight:bold;font-size:14px;">{_esc(kit['label'])} →</a>
  </td></tr></table>
</td></tr>""")

    # ---- call to action + machine translation note
    def btn(label: str, url: str, primary: bool) -> str:
        style = (f"background:{C['gv']};color:#ffffff;border:1px solid {C['gv']};" if primary
                 else f"background:#ffffff;color:{C['gv']};border:1px solid {C['gv']};")
        return (f'<a href="{_esc(url)}" style="display:inline-block;{style}text-decoration:none;font-weight:bold;'
                f'font-size:13px;padding:9px 14px;border-radius:8px;margin:0 6px 8px 0;">{_esc(label)}</a>')

    note = (f'<p style="margin:10px 0 0;font-size:12px;color:{C["muted"]};font-style:italic;">{_esc(t["machine"])}</p>'
            if data["machine"].get(lang) else "")
    parts.append(f"""<tr><td style="padding:22px 32px 26px;">
  {btn(t['cta_new'], links.page('/whats-new/', lang), True)}{btn(t['cta_site'], links.page('/', lang), False)}
  {note}
</td></tr>""")
    # lang on every cell so screen readers switch voice for the Spanish half
    return "\n".join(parts).replace("<tr><td style=", f'<tr><td lang="{lang}" style=')


# ---------------------------------------------------------------------------- plain text
def render_text(data: dict, cfg: dict, links: Links, max_per: int) -> str:
    site = cfg.get("site") or {}
    ed = data["edition"]
    out: list[str] = []
    title = site.get("title") or "Grapevine / La Viña"
    out += [f"{title} — {T['en']['masthead']} · {T['es']['masthead']}", site.get("committee") or "",
            "English first · Versión en español más abajo", ""]

    def head(s: str) -> list[str]:
        return [s.upper(), "-" * min(len(s), 60)]

    for lang in ("en", "es"):
        t = T[lang]
        prev_w = month_word(ed["key"], lang)
        top = t["edition"].format(month=month_label(ed["key"], lang))
        out += ["=" * len(top), top, "=" * len(top), t["edition_sub"].format(prev=prev_w), "", intro(data, lang), ""]
        ann = data["groups"]["announcement"]
        if ann:
            out += head(f"{t['announcement']} ({len(ann)})")
            for a in ann[:max_per]:
                out.append(f"* {tx(a, 'title', lang)}")
                # its lines as they are (a list stays a list), about 600 characters, indented under the title
                short, cut = md_excerpt(tx(a, "body_md", lang) or tx(a, "summary", lang), 600)
                body = md_to_text(short, lambda u: links.site_path(u, lang))
                if body:
                    out += ["  " + x if x else "" for x in body.split("\n")]
                    if cut:
                        out.append(f"  {t['details']}: {links.item(a, lang, '/bulletin/')}")
            out += [f"  → {links.page('/bulletin/', lang)}", ""]
        # the events that took place
        if data["events"]:
            out += head(t["events"].format(prev=prev_w))
            for ev in data["events"]:
                r = event_row(ev, lang, links, ed["last"])
                out.append(f"* {r['title']} — {r['when']}{(' · ' + r['where']) if r['where'] else ''}")
                out.append(f"  {r['url']}")
            out.append("")

        def media(g: str, page: str) -> None:
            items = data["groups"].get(g) or []
            if not items:
                return
            if g == "post":
                # Instagram in text: how many posts each account shared, and the one link (like the page's texts)
                out.extend(head(f"{t[g]} ({len(items)})"))
                for acc in ordered_accounts(data, lang):
                    many, one = t["ig_n"]
                    handle = f" @{acc['username']}" if acc["username"] else ""
                    out.append(f"* {acc['name']}{handle}: {one if acc['count'] == 1 else many.format(n=acc['count'])}")
                out.extend([f"  → {t['ig_link']}: {links.page(page, lang)}", ""])
                return
            rows, extra = build_rows(g, items, lang, links, page, max_per)
            out.extend(head(f"{t[g]} ({len(items)})"))
            for r in rows:
                label = f"[{r['label']}] " if r["label"] else ""
                meta = f" ({r['meta']})" if r["meta"] else ""
                out.append(f"* {label}{r['title']}{meta}")
                out.append(f"  {r['url']}")
                if r.get("twin"):
                    out.append(f"  {t['twin']}: {r['twin']}")
            more = t["more"].format(n=extra) if extra else t["see_all"]
            out.extend([f"  → {more}: {links.page(page, lang)}", ""])

        media("drive", DRIVE_PAGE)
        # new in the magazines
        if data["issues"]:
            out += head(t["issues"])
            for iss in ordered_issues(data, lang):
                many, one = t["stories"]
                count = one if iss["count"] == 1 else many.format(n=iss["count"])
                if iss["free"]:
                    count += " · " + t["free_n"].format(n=iss["free"])
                theme = f": “{iss['theme'][lang]}”" if iss["theme"][lang] else ""
                out.append(f"* {iss['name']} — {iss['label'][lang]}{other_lang(iss['pub'], lang)}{theme} ({count})")
                for a in iss["highlights"][:max_per]:
                    free = f" — {t['free']}" if (a.get("extra") or {}).get("free") is True else ""
                    out.append(f"  - “{title_of(a, lang)}”{free}")
                    out.append(f"    {a['url']}")
                out.append(f"  → {t['issue_more'].format(n=iss['total'])}: {links.page(iss['read_href'], lang)}")
            out.append("")
        # writers
        W = data["writers"]
        n_writers = sum(len(v) for v in W.values())
        if n_writers:
            out += head(f"{t['writers']} ({n_writers})")
            for key in ("neta65", "texas"):
                if not W[key]:
                    continue
                out.append(f"{t['group_' + key]}:")
                for it in W[key][:max_per]:
                    place = writer_place(it, lang)
                    # "(La Viña, September / October 2026, in Spanish)"
                    where = ", ".join(x for x in (item_label(it, lang)[0], issue_label(it, lang),
                                                  T[lang]["in_other"] if other_lang(pub_of(it), lang) else "") if x)
                    out.append(f"* “{tx(it, 'title', lang)}” — {writer_name(it, lang)}{', ' + place if place else ''} ({where})")
                    out.append(f"  {it['url']}")
            out += [f"  → {links.page('/published/', lang)}", ""]
        for g, page in MEDIA_GROUPS:
            media(g, page)
        if not total_count(data):
            out += [t["nothing"].format(prev=prev_w), ""]
        # the one pointer to what is current
        kit = toolkit_block(data, lang, links)
        out += head(kit["title"])
        out += [f"{kit['text']} {kit['url']}", ""]
        out.append(f"{t['cta_new']}: {links.page('/whats-new/', lang)}")
        if data["machine"].get(lang):
            out.append(t["machine"])
        out += ["", ""]
    committee = site.get("committee") or title
    out.append(T["en"]["footer_why"].format(committee=committee) + " " + T["en"]["footer_unsub"])
    out.append(T["es"]["footer_why"].format(committee=site.get("committee_es") or committee) + " " + T["es"]["footer_unsub"])
    out.append(links.page("/", "en"))
    return "\n".join(out).strip() + "\n"


# ---------------------------------------------------------------------------- e-mail
def parse_recipients(s: str) -> list[str]:
    out = []
    for part in re.split(r"[,;\n]+", s or ""):
        addr = parseaddr(part.strip())[1]
        if addr and "@" in addr:
            out.append(addr)
    return list(dict.fromkeys(out))


def build_message(subject: str, html_body: str, text_body: str, from_addr: str, from_name: str,
                  recipients: list[str], reply_to: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")           # RFC 2047 — the subject has ñ and dashes
    msg["From"] = formataddr((from_name, from_addr))    # encodes the non-ASCII display name
    # One address (e.g. a Google Group) → To. Several → Bcc (envelope only) so districts'
    # addresses are not shown to everyone.
    msg["To"] = recipients[0] if len(recipients) == 1 else formataddr((from_name, from_addr))
    if reply_to:
        msg["Reply-To"] = reply_to
        msg["List-Unsubscribe"] = f"<mailto:{reply_to}?subject=unsubscribe>"
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=(from_addr.split("@", 1)[-1] or "localhost"))
    msg["Content-Language"] = "en, es"
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


# Network trouble worth another try — but only while connecting and logging in, never once the
# message itself is on its way (see send()).
TRANSIENT = (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, socket.timeout, ConnectionError,
             TimeoutError, socket.gaierror)
NO_STARTTLS = ("The mail server does not offer STARTTLS; refusing to send the password unencrypted. "
               "Use a server that supports STARTTLS on port 587, or SSL on port 465 (SMTP_PORT).")


def _close(conn: smtplib.SMTP) -> None:
    try:
        conn.quit()
    except (smtplib.SMTPException, OSError):
        try:
            conn.close()
        except OSError:
            pass


def connect(server: str, port: int, user: str, password: str, ctx: ssl.SSLContext) -> smtplib.SMTP:
    """An encrypted, logged-in connection. Port 465 is SSL from the start; any other port must
    switch to TLS with STARTTLS before the password is sent — a server (or anyone in between)
    that leaves STARTTLS out of its EHLO reply gets no password: RuntimeError."""
    if port == 465:
        conn: smtplib.SMTP = smtplib.SMTP_SSL(server, port, context=ctx, timeout=60)
    else:
        conn = smtplib.SMTP(server, port, timeout=60)
    try:
        conn.ehlo()
        if port != 465:
            if not conn.has_extn("starttls"):
                raise RuntimeError(NO_STARTTLS)
            conn.starttls(context=ctx)
            conn.ehlo()
        if user:
            conn.login(user, password)
    except BaseException:
        _close(conn)
        raise
    return conn


def send(msg: MIMEMultipart, from_addr: str, recipients: list[str]) -> None:
    """Connect and log in (up to 3 tries on network trouble), then hand the message over ONCE.
    A failure after that point is never retried: the server may already have accepted the e-mail,
    and a second try could send the whole district list a second copy."""
    server = os.environ.get("SMTP_SERVER", "").strip()
    port = int((os.environ.get("SMTP_PORT") or "587").strip() or 587)
    user = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    ctx = ssl.create_default_context()
    conn: smtplib.SMTP | None = None
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            conn = connect(server, port, user, password, ctx)
            break
        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(
                "The mail server rejected the username/password. For Gmail you need an *App Password* "
                "(Google Account → Security → 2-Step Verification → App passwords), not your normal password."
            ) from e
        except TRANSIENT as e:
            last_err = e
            if attempt < 3:
                log(f"attempt {attempt}/3 failed ({type(e).__name__}: {e}); retrying…")
                time.sleep(10 * attempt)
    if conn is None:
        raise RuntimeError(f"Could not reach the mail server {server}:{port}: {last_err}")
    try:
        refused = conn.send_message(msg, from_addr=from_addr, to_addrs=recipients)
    except smtplib.SMTPRecipientsRefused as e:
        raise RuntimeError(f"All recipients were refused: {list(e.recipients)}") from e
    except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as e:
        raise RuntimeError(f"The mail server refused the e-mail ({type(e).__name__}: {e}); it was not sent.") from e
    except Exception as e:
        raise RuntimeError(
            f"The connection failed while the e-mail was being handed over ({type(e).__name__}: {e}). "
            "It MAY have been sent — check the mailbox or the group before re-running, "
            "so nobody gets it twice.") from e
    finally:
        _close(conn)
    if refused:
        log(f"WARNING: {len(refused)} recipient(s) were refused by the mail server")


def step_summary(lines: list[str]) -> None:
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if not p:
        return
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


def waiting_for(ed: dict, status: dict | None = None) -> list[str]:
    """The sources the e-mail still waits for (FRESH_SOURCES): the ones whose last try (status.json
    sources[].attempted, else updated) was before the month ended — 00:00 Central on the 1st of the next
    month — so the month's last items may be missing. A source whose last try is older than
    FRESH_IDLE_DAYS before that has stopped running (the /status/ page shows it) and is not waited for;
    one that never ran (no date) neither. No or unreadable data/site/status.json: nothing to wait for."""
    if status is None:
        status = load_file("status")
    end = end_of_day(ed["last"])
    idle = end - timedelta(days=FRESH_IDLE_DAYS)
    out = []
    for s in status.get("sources") or []:
        if not isinstance(s, dict) or s.get("source") not in FRESH_SOURCES:
            continue
        last = parse_dt(s.get("attempted") or s.get("updated"))
        if last and idle <= last < end:
            out.append(str(s["source"]))
    return out


# ---------------------------------------------------------------------------- main
def _positive(v: Any, default: int) -> int:
    try:
        n = int(v)
        return n if n > 0 else default
    except (TypeError, ValueError):
        return default


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Send the monthly bilingual e-mail digest (last month on the site).")
    ap.add_argument("--dry-run", action="store_true", help="don't send; write digest.html and digest.txt to --out-dir")
    ap.add_argument("--month", default=None, help="the month the digest covers, YYYY-MM (default: last month, Central time)")
    ap.add_argument("--max-per-section", type=int, default=None, help="items listed per section (default: config digest.per_section or 5)")
    ap.add_argument("--to", default=None, help="override recipients (comma-separated)")
    ap.add_argument("--force", action="store_true", help="send even if nothing was new in the month, and without waiting for the data")
    ap.add_argument("--stale-ok", action="store_true", help="send even if some sources were not updated since the month ended")
    ap.add_argument("--as-of", default=None, help="pretend today is YYYY-MM-DD (testing; 15:05 UTC)")
    ap.add_argument("--out-dir", default=str(ROOT / ".tmp"), help="where --dry-run writes the preview")
    args = ap.parse_args(argv)

    cfg = load_config()
    site = cfg.get("site") or {}
    digest_cfg = cfg.get("digest") if isinstance(cfg.get("digest"), dict) else {}

    if args.as_of:
        d = date.fromisoformat(args.as_of)
        now = datetime(d.year, d.month, d.day, 15, 5, tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc).replace(microsecond=0)
    if args.month is not None and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.month):
        log(f"--month must look like 2026-09 (got {args.month!r}) — nothing was built or sent")
        step_summary(["### E-mail digest", f"Stopped: the month {args.month!r} is not a YYYY-MM month like 2026-09. "
                      "Nothing was sent — run it again with the month written like that, or leave the box empty."])
        return 2
    ed = edition_of(now, args.month)
    name_en = month_label(ed["key"], "en")
    if not args.dry_run and ed["last"] >= to_central(now).date():
        # a month's digest goes out once the month is over (a preview can be made any time)
        log(f"the {name_en} digest can be sent from {ed['out_first'].isoformat()} (the month is not over yet) — nothing was sent")
        step_summary(["### E-mail digest", f"Not sent: {name_en} is not over yet — its digest can be sent from "
                      f"{ed['out_first'].isoformat()}. For a look at it now, run it with *Preview only* ticked."])
        return 2

    max_per = args.max_per_section or _positive(digest_cfg.get("per_section"), 5)
    highlights = _positive(digest_cfg.get("highlights"), 3)
    site_url = (os.environ.get("SITE_URL") or site.get("url") or "").strip().rstrip("/")
    if not site_url:
        log("WARNING: no site URL (config site.url / SITE_URL) — links will be relative")
    links = Links(site_url)

    data = collect(now, ed["key"], max_per, highlights)
    # the edition's own count — the page's "149 new in September", the e-mail's intro; total_count (the
    # writers too, whose stories are among the magazine stories) only decides whether there is anything to send
    items = sum(counts(data).values())
    shown = {k: v for k, v in counts(data).items() if v}
    writers = sum(len(v) for v in data["writers"].values())
    log(f"the {name_en} digest ({ed['first']} to {ed['last']}): {items} item(s) {shown} writers={writers} "
        f"· issues={len(data['issues'])} events={len(data['events'])}")

    subject = subject_of(data, cfg)
    html_body = render_html(data, cfg, links, max_per, subject)
    text_body = render_text(data, cfg, links, max_per)
    waiting = waiting_for(ed)

    if args.dry_run:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "digest.html").write_text(html_body, encoding="utf-8")
        (out / "digest.txt").write_text(text_body, encoding="utf-8")
        log(f"DRY RUN — subject: {subject}")
        log(f"preview written to {out / 'digest.html'} and {out / 'digest.txt'}")
        if waiting:
            log(f"(a scheduled send would wait: not updated since {name_en} ended: {', '.join(waiting)})")
        step_summary(["### E-mail digest preview (not sent)", f"**Subject:** {subject}", "",
                      f"{items} new item(s) in {name_en}: {shown}; writers {writers}; events that took place {len(data['events'])}", "",
                      *([f"A scheduled send would still wait for: {', '.join(waiting)} (not updated since {name_en} ended).", ""] if waiting else []),
                      "Download the `digest-preview` artifact to see it."])
        return 0

    if waiting and not (args.stale_ok or args.force):
        log(f"not sent yet: not updated since {name_en} ended: {', '.join(waiting)} — the next try sends it")
        step_summary(["### E-mail digest: waiting for the data", f"Waiting for {', '.join(waiting)} to be updated since "
                      f"{name_en} ended, so the digest has the whole month. Nothing was sent; the next try sends it "
                      "(at the latest from noon on the 3rd, with the data there is)."])
        return 3

    if not total_count(data) and not args.force:
        log(f"nothing new in {name_en} — not sending (use --force to send anyway)")
        step_summary(["### E-mail digest", f"Nothing new in {name_en} — no e-mail sent."])
        return 0

    recipients = parse_recipients(args.to or os.environ.get("DIGEST_TO", ""))
    missing = [k for k in ("SMTP_SERVER", "SMTP_USERNAME", "SMTP_PASSWORD") if not os.environ.get(k, "").strip()]
    if missing or not recipients:
        log(f"e-mail is not configured (missing: {', '.join(missing + ([] if recipients else ['DIGEST_TO']))}). "
            "See README → 'Monthly e-mail digest'.")
        return 2

    user = os.environ.get("SMTP_USERNAME", "").strip()
    from_addr = parseaddr(os.environ.get("DIGEST_FROM", "").strip())[1] or (user if "@" in user else site.get("contact_email", ""))
    reply_to = parseaddr(os.environ.get("DIGEST_REPLY_TO", "").strip())[1] or site.get("contact_email", "") or from_addr
    from_name = site.get("committee") or site.get("title") or "Grapevine / La Viña"
    msg = build_message(subject, html_body, text_body, from_addr, from_name, recipients, reply_to)
    try:
        send(msg, from_addr, recipients)
    except Exception as e:
        log(f"ERROR: {e}")
        step_summary(["### E-mail digest", f"Sending FAILED: {e}"])
        return 1
    log(f"sent to {len(recipients)} recipient(s): {subject}")
    step_summary(["### E-mail digest sent", f"**Subject:** {subject}", "",
                  f"Recipients: {len(recipients)} · new items in {name_en}: {items} {shown}"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
