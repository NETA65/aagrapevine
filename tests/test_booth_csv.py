"""The booth display's CSV (content/booth/booth.csv → the About page's "Booth display", the show that plays by itself
at the committee's table): every row stays complete, correct and in line with AA's principles.

This file is the CHECKER the committee's Code check runs, and the Python twin of the build's own checker
(eleventy/filters/booth.js checkCsv, which leaves a row with a mistake out of /about/booth.json): the same rules, the
same problem lines, the same items — the tests hold the two together. The rules (SPEC §1.2 and §4; the owner's guide
is content/booth/README.md):

  * the file: UTF-8 (a BOM is fine), commas, the first row the header; RFC 4180 quotes ("" inside quotes, line breaks
    inside quotes); a cell that opens a quote and never closes it is named;
  * the header: column names in any order and capitalization, unknown columns ignored, `id` and `type` needed;
  * each row (a blank row and a row whose id starts with "#" are skipped; a row switched off with on = no is checked
    all the same): a unique id (a-z, 0-9, dashes, 48 characters at most), on, type, pub, tags, weight, from / until
    (real days of the years 2000–2099), seconds, reveal; the languages (a row is shown in a language when it has that
    language's words — and then it has everything the type needs in it); choices (2–6, the same number in both
    languages) and `correct`; a fill's blank (___), a scramble's word; the lengths a slide has room for; links only to
    the allowed sites (YouTube, AA, Grapevine, La Viña, NETA 65, the podcast host, this site), a QR code's link to a
    page, never a document file (the player prints its address under the code); `source_url` for every fact; no
    refused word (PDF, donations, contributions to Grapevine, sales and urgency words, the unverified claims,
    "Conference-approved" said of the magazines, "today only" without {event}); only the placeholders {event},
    {committee} and {site}. A qr_url written
    "{site}contribute/" gives two codes — the English page on English slides (qr), the Spanish one under /es/ on
    Spanish slides (qr_es); "{site_es}…" the Spanish page on both; another site's link one code (qr_es null).

  * Real — the real content/booth/booth.csv (the committee's fact-checked rows) has no problem at all;
  * Reader — the CSV reader against Python's csv module, a BOM, CRLF / LF / CR, quotes, line breaks in quotes, an
    unclosed quote;
  * Fixtures — tests/fixtures/booth_csv/*.csv, one kind of mistake each, named line by line;
  * Twin — the build's JavaScript checker gives the same lines and the same items for every fixture and the real file
    (through tests/nodejs.py; skipped without Node.js or node_modules).

    .venv\\Scripts\\python.exe tests\\test_booth_csv.py content\\booth\\booth.csv     (one file: its problems)
    python -m unittest tests.test_booth_csv -v
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import re
import sys
import unicodedata
import unittest
from pathlib import Path
from urllib.parse import unquote_plus

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "content" / "booth" / "booth.csv"
FIXTURES = ROOT / "tests" / "fixtures" / "booth_csv"
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
# the site's address as src/_data/site.js reads it (SITE_URL from the GitHub Action wins), with one "/" at the end
BASE = (os.environ.get("SITE_URL") or SITE["site"]["url"]).rstrip("/") + "/"

COLUMNS = [
    "id", "on", "type", "pub", "tags", "weight", "from", "until", "seconds", "reveal",
    "title_en", "text_en", "choices_en", "correct", "answer_en", "explain_en", "credit_en",
    "title_es", "text_es", "choices_es", "answer_es", "explain_es", "credit_es",
    "media_url", "start", "end", "qr_url", "source_url", "notes",
]
TYPES = ["quiz", "truefalse", "fact", "quote", "history", "fill", "scramble", "poll", "prompt", "message",
         "qr", "video", "audio", "image"]
CSV_CHANNEL = {
    "quiz": "quiz", "truefalse": "quiz", "fill": "puzzles", "scramble": "puzzles", "fact": "facts", "history": "facts",
    "quote": "quotes", "poll": "polls", "prompt": "prompts", "message": "messages", "qr": "qr", "video": "web-video",
    "audio": "web-audio", "image": "web-image",
}
# What each type needs in every language the row is shown in ("a|b": one of the two)
NEEDS = {
    "quiz": ["text", "choices"], "truefalse": ["text"], "fact": ["text"], "quote": ["text", "credit"],
    "history": ["title", "text"], "fill": ["text", "answer"], "scramble": ["text", "answer"], "poll": ["text", "choices"],
    "prompt": ["text"], "message": ["text"], "qr": ["title|text"], "video": ["title|text"], "audio": ["title|text"],
    "image": ["title|text"],
}
MEDIA_TYPES = ["video", "audio", "image"]
CHOICE_TYPES = ["quiz", "poll"]
ANSWER_TYPES = ["fill", "scramble"]
REVEAL_TYPES = ["quiz", "truefalse", "fill", "scramble"]
SOURCE_TYPES = ["quiz", "truefalse", "fact", "history", "fill"]
SHORT_TEXT = ["quiz", "truefalse", "fill"]
LANGS = ["en", "es"]
LANG_FIELDS = ["title", "text", "choices", "answer", "explain", "credit"]
MAX = {"title": 80, "text": 300, "short_text": 180, "explain": 240, "credit": 200, "choice": 70, "answer": 60}
LANG_NAME = {"en": ("English", "inglés"), "es": ("Spanish", "español")}
# (the podcast's host, Captivate: its feed's links, its file server — where they lead, and where every episode of 2021
# to mid-2025 is — and an episode's page; never *.captivate.fm, any podcast's own site)
ALLOWED_HOSTS = [
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
    "aagrapevine.org", "www.aagrapevine.org", "aalavina.org", "www.aalavina.org", "aa.org", "www.aa.org",
    "neta65.org", "www.neta65.org", "neta65.github.io", "episodes.captivate.fm", "podcasts.captivate.fm",
    "player.captivate.fm",
]
YT_HOSTS = ["youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"]
HOSTS_EN = "YouTube, aagrapevine.org, aalavina.org, aa.org, neta65.org, the podcast's captivate.fm, this website"
PLACEHOLDERS = ["event", "committee", "site"]
ON_YES = ["yes", "y", "true", "1", "si", "sí"]
ON_NO = ["no", "n", "false", "0"]
TF_TRUE = ["true", "t", "yes", "y", "v", "verdadero", "cierto", "sí", "si"]
TF_FALSE = ["false", "f", "no", "n", "falso"]
PUBS = {
    "gv": "gv", "grapevine": "gv", "lv": "lv", "lavina": "lv", "laviña": "lv", "both": "both", "all": "both",
    "aa": "both", "ambos": "both", "ambas": "both", "gvlv": "both", "gv/lv": "both", "gv-lv": "both", "gv+lv": "both",
    "gv&lv": "both",
}

# White space, spelled out: Python's \s and strip() and JavaScript's \s and trim() disagree on a few characters
# (U+FEFF, U+001C–U+001F, U+0085), and the two checkers must read every cell alike.
WS_CHARS = " \\t\\n\\r\\f\\v\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff"
WS = f"[{WS_CHARS}]"
TRIM = re.compile(rf"\A{WS}+|{WS}+\Z")
TRIM_END = re.compile(rf"{WS}+\Z")
SPACES = re.compile(rf"{WS}+")
TAG_SPLIT = re.compile(rf"(?:[;,]|{WS})+")
TYPE_PUNCT = re.compile(rf"(?:{WS}|[_/-])+")
TAG = re.compile(r"\A[^\W_][\w-]*\Z")
ID = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
URL_RE = re.compile(rf"\Ahttps://([^/?#@:{WS_CHARS}]+)(:[0-9]+)?([/?#][^{WS_CHARS}]*)?\Z", re.I)

SALES = "no sales or urgency words: attraction, not promotion"
# "PDF" / "PDFs" as a word — in a shown cell, and in the part of a qr_url the player prints under the code
PDF_WORD = re.compile(r"(?<!\w)pdfs?(?!\w)", re.I)
# The words the booth never shows (in every shown cell): (pattern, why, only when the cell …)
REFUSED: list[tuple[re.Pattern, str, object]] = [
    (PDF_WORD, "say “document” instead", None),
    (re.compile(r"\w*donat\w*", re.I), "Grapevine and La Viña take no donations (say “Carry the Message gift”)", None),
    (re.compile(rf"(?<!\w)contributions?{WS}+to{WS}+(?:the{WS}+)?(?:aa{WS}+)?(?:grapevine|la{WS}+vi[ñn]a)(?!\w)", re.I),
     "AA Grapevine, Inc. does not accept contributions", None),
    (re.compile(rf"(?<!\w)contribu(?:ir|ciones|ción|cion){WS}+(?:a|para){WS}+(?:la{WS}+)?(?:aa{WS}+)?(?:grapevine|la{WS}+vi[ñn]a)(?!\w)", re.I),
     "AA Grapevine, Inc. does not accept contributions", None),
    (re.compile(rf"(?<!\w)(?:buy{WS}+now|hurry|limited(?:{WS}|-)+time|act{WS}+now|last{WS}+chance|don[’']?t{WS}+miss|subscribe{WS}+(?:now|today)|download{WS}+(?:it{WS}+|them{WS}+)?(?:now|today))(?!\w)", re.I),
     SALES, None),
    (re.compile(r"(?<!\w)sale!", re.I), SALES, None),
    (re.compile(rf"(?<!\w)before{WS}+(?:the{WS}+)?prices?{WS}+(?:go(?:es)?{WS}+up|rises?|increases?|changes?)(?!\w)", re.I), SALES, None),
    (re.compile(rf"(?<!\w)(?:compra{WS}+(?:ya|ahora)|ap[uú]rate|apres[uú]rate|date{WS}+prisa|tiempo{WS}+limitado|[uú]ltima{WS}+oportunidad|suscr[ií]bete{WS}+(?:ya|hoy|ahora)|desc[aá]rg(?:a|ue)(?:l[aoe]s?)?{WS}+(?:ya|ahora|hoy))(?!\w)", re.I),
     SALES, None),
    (re.compile(rf"(?<!\w)antes{WS}+de{WS}+que{WS}+(?:suba|suban|cambie|cambien){WS}+(?:el{WS}+|los{WS}+)?precios?(?!\w)", re.I), SALES, None),
    (re.compile(r"(?<!\w)(?:subscribe|suscr[ií]b(?:ete|ase))!", re.I), SALES, None),
    (re.compile(rf"(?<!\w)(?:reach(?:es|ing)?{WS}+millions|lleg(?:a|an){WS}+a{WS}+millones|183{WS}+challenge|reto{WS}+183)(?!\w)", re.I),
     "an unverified claim (no source found): leave it out", None),
    (re.compile(rf"(?<!\w)(?:conference(?:{WS}|-)+approved|aprobad[oa]s?{WS}+por{WS}+la{WS}+conferencia)(?!\w)", re.I),
     "say “recognized by the Conference as the international journal of AA”",
     lambda s: bool(re.search(rf"grapevine|la{WS}+vi[ñn]a", s, re.I))),
    (re.compile(rf"(?<!\w)(?:today{WS}+only|s[oó]lo{WS}+hoy|[uú]nicamente{WS}+hoy)(?!\w)", re.I),
     "“today only” needs {event} (the booth shows the same rows on many days)", lambda s: "{event}" not in s),
]


# ----------------------------------------------------------------------------------------------------------------
# Reading the CSV (the build's parseCsv, the way Python's csv module reads a file opened with newline="")
# ----------------------------------------------------------------------------------------------------------------
def parse_csv(text: str) -> tuple[list[list[str]], int | None]:
    """The records of a CSV text and the row (1 = the header) where a quoted cell starts and never ends, or None."""
    s = text[1:] if text.startswith("﻿") else text
    rows: list[list[str]] = []
    rec: list[str] | None = None
    cell = ""
    state = "start"   # start (of a cell) | plain | quoted | closed (a quote just closed a quoted cell)
    unclosed = None

    def end_record():
        nonlocal rec, cell, state
        if rec is None and state == "start" and cell == "":
            rows.append([])
        else:
            rows.append((rec or []) + [cell])
        rec, cell, state = None, "", "start"

    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if state == "quoted":
            if c == '"':
                if i + 1 < n and s[i + 1] == '"':
                    cell += '"'
                    i += 1
                else:
                    state = "closed"
            else:
                cell += c
        elif c in "\r\n":
            end_record()
            if c == "\r" and i + 1 < n and s[i + 1] == "\n":
                i += 1
        elif c == ",":
            rec = (rec or []) + [cell]
            cell, state = "", "start"
        elif c == '"' and state == "start":
            rec = rec if rec is not None else []
            state = "quoted"
            unclosed = len(rows) + 1
        else:
            rec = rec if rec is not None else []
            cell += c
            state = "plain"
        i += 1
    if state == "quoted":
        rows.append((rec or []) + [cell])
        return rows, unclosed
    if rec is not None or cell != "" or state == "closed":
        end_record()
    return rows, None


def cell_text(v) -> str:
    """A cell as the checks read it: NFC, line breaks "\\n" (no spaces at a line's end, at most one empty line in a
    row), nothing around it."""
    s = unicodedata.normalize("NFC", "" if v is None else str(v))
    s = re.sub(r"\r\n?", "\n", s)
    s = "\n".join(TRIM_END.sub("", line) for line in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    return TRIM.sub("", s)


def one_line(v) -> str:
    return SPACES.sub(" ", cell_text(v))


def valid_day(v: str) -> bool:
    """A real calendar day YYYY-MM-DD, years 2000–2099 (booth.js validDay: the same rule — its Date.UTC would read
    the years 0–99 as 1900–1999)."""
    if not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", v):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def seconds_of(v: str) -> int | None:
    s = TRIM.sub("", v or "")
    m = re.fullmatch(r"([0-9]{1,5})", s)
    if m:
        return int(m[1])
    m = re.fullmatch(r"([0-9]{1,3}):([0-5][0-9])", s)
    if m:
        return int(m[1]) * 60 + int(m[2])
    m = re.fullmatch(r"([0-9]{1,2}):([0-5][0-9]):([0-5][0-9])", s)
    return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) if m else None


def clock(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def split_url(v: str) -> dict | None:
    m = URL_RE.match(v or "")
    if not m:
        return None
    rest = m[3] or ""
    q, h = rest.find("?"), rest.find("#")
    path_end = min(q if q >= 0 else len(rest), h if h >= 0 else len(rest))
    query = "" if q < 0 or (0 <= h < q) else rest[q + 1:(h if h > q else len(rest))]
    return {"host": m[1].lower(), "path": rest[:path_end] or "/", "query": query}


def params(query: str) -> dict:
    out: dict[str, str] = {}
    for part in (query or "").split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        if k not in out:
            out[k] = unquote_plus(v)
    return out


def yt_time(v: str) -> int | None:
    m = re.fullmatch(r"([0-9]{1,6})s?", v)
    if m:
        return int(m[1])
    m = re.fullmatch(r"(?:([0-9]{1,2})h)?(?:([0-9]{1,3})m)?(?:([0-9]{1,5})s)?", v)
    if m and (m[1] or m[2] or m[3]):
        return int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + int(m[3] or 0)
    return None


def youtube_of(url: str) -> dict | None:
    """watch?v=, youtu.be/, shorts/ (short), embed/ → {id, short, start} (start: ?t= / ?start=, else None)."""
    u = split_url(url)
    if not u:
        return None
    seg = [x for x in u["path"].split("/") if x]
    q = params(u["query"])
    vid, short = "", False
    if u["host"] == "youtu.be":
        vid = seg[0] if len(seg) == 1 else ""
    elif u["host"] in YT_HOSTS:
        head = (seg[0] if seg else "").lower()
        if head == "watch" and len(seg) == 1:
            vid = q.get("v", "")
        elif head in ("shorts", "embed") and len(seg) == 2:
            vid, short = seg[1], head == "shorts"
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return None
    tv = q["t"] if "t" in q else q.get("start")
    return {"id": vid, "short": short, "start": None if tv is None else yt_time(tv)}


def resolve_site(v: str, base: str) -> dict | None:
    """qr_url → {"en": the code on English slides, "es": the code on Spanish slides or None} (SPEC update 1):
    "{site}x/" → the English page and the same page under the Spanish home; "{site_es}x/" → the Spanish page on
    both; any other link → that link, no Spanish one of its own."""
    for tok, both in (("{site_es}", True), ("{site}", False)):
        if not v.startswith(tok):
            continue
        if not base:
            return None
        rest = v[len(tok):].lstrip("/")
        if re.search(r"[{}]", rest):
            return None
        es = base + ("" if re.match(r"es(?:[/?#]|$)", rest) else "es/") + rest
        return {"en": es if both else base + rest, "es": es}
    return None if re.search(r"[{}]", v) else {"en": v, "es": None}


def refused_in(text: str) -> list[tuple[str, str]]:
    """The refused words in a text → [(word as written, why)], one per rule that catches something."""
    out = []
    for rx, why, when in REFUSED:
        m = rx.search(text)
        if m and (when is None or when(text)):
            out.append((m[0], why))
    return out


def media_block(**o) -> dict:
    return {"kind": o["kind"], "src": o["src"], "id": o.get("id"), "short": bool(o.get("short")), "local": False,
            "poster": o.get("poster"), "start": o.get("start") or 0, "end": o.get("end"), "muted": False,
            "fit": "contain", "w": None, "h": None, "bytes": None}


# ----------------------------------------------------------------------------------------------------------------
# The checker (the build's checkCsv, line for line)
# ----------------------------------------------------------------------------------------------------------------
def check_csv(text: str, file: str = "booth.csv", site_url: str = BASE) -> tuple[list[dict], list[str]]:
    """A CSV text → (items, problems): the rows the show uses, as the build's items, and one line per mistake —
    "booth.csv row 14 (quiz-12): …" (the build's `where` and English `en`)."""
    base = site_url.rstrip("/") + "/" if site_url else ""
    own = (split_url(base) or {}).get("host", "") if base else ""

    def host_ok(h: str) -> bool:
        return h in ALLOWED_HOSTS or (bool(own) and h == own)

    items: list[dict] = []
    problems: list[str] = []
    if "�" in text:
        problems.append(f"{file}: the file is not saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)")
    rows, unclosed = parse_csv(text)
    if unclosed:
        problems.append(f"{file} row {unclosed}: a cell starts with a double quote (\") that is never closed: everything after it was read as that one cell")
    header = rows[0] if rows else []
    if not any(cell_text(c) for c in header):
        problems.append(f"{file}: the file is empty: the first row must be the header (id,on,type,…)")
        return items, problems
    col: dict[str, int] = {}
    twice: set[str] = set()
    for i, h in enumerate(header):
        k = one_line(h).lower()
        if not k:
            continue
        if k not in col:
            col[k] = i
        elif k in COLUMNS and k not in twice:
            twice.add(k)
            problems.append(f"{file} header: column {k} is in the header twice: the first one is used")
    for need in ("id", "type"):
        if need not in col:
            problems.append(f"{file} header: the header (first row) has no {need} column")
    if "id" not in col or "type" not in col:
        return items, problems

    seen: dict[str, int] = {}
    for r in range(1, len(rows)):
        cells = rows[r]
        row_no = r + 1
        if not any(cell_text(c) for c in cells):
            continue

        def get(k: str) -> str:
            return cells[col[k]] if k in col and col[k] < len(cells) else ""

        id_raw = one_line(get("id"))
        if id_raw.startswith("#"):
            continue
        where = f"{file} row {row_no}" + (f" ({id_raw[:48]})" if id_raw else "")
        errs: list[str] = []
        err = errs.append

        if len(cells) > len(header) and any(cell_text(c) for c in cells[len(header):]):
            err(f"the row has {len(cells)} cells but the header has {len(header)}: a comma inside a text needs the whole cell in double quotes")
            problems.extend(f"{where}: {e}" for e in errs)
            continue

        rid = ""
        if not id_raw:
            err("id is empty")
        elif not ID.match(id_raw) or len(id_raw) > 48:
            err(f'id "{id_raw}": use only a–z, 0–9 and dashes (no spaces or capitals), at most 48 characters')
        elif id_raw in seen:
            err(f'id "{id_raw}" is already used in row {seen[id_raw]}')
        else:
            rid = id_raw
            seen[rid] = row_no
        on_raw = one_line(get("on"))
        on_lc = on_raw.lower()
        on = True if not on_raw else True if on_lc in ON_YES else False if on_lc in ON_NO else None
        if on is None:
            err(f'on "{on_raw}": write yes or no')
        type_raw = one_line(get("type"))
        typ = TYPE_PUNCT.sub("", type_raw.lower())
        type_ok = typ in TYPES
        if not type_raw:
            err(f"type is empty ({', '.join(TYPES)})")
        elif not type_ok:
            err(f'type "{type_raw}" is not one of: {", ".join(TYPES)}')
        pub_raw = one_line(get("pub"))
        pub = "both" if not pub_raw else PUBS.get(SPACES.sub("", pub_raw.lower()))
        if not pub:
            err(f'pub "{pub_raw}": write gv, lv or both')
        tags: list[str] = []
        for tg in [x for x in TAG_SPLIT.split(one_line(get("tags")).lower()) if x]:
            if not TAG.match(tg) or len(tg) > 32:
                err(f'tags: "{tg}" is not a tag (one word: letters, digits, dashes; at most 32 characters)')
            elif tg not in tags:
                tags.append(tg)
        w_raw = one_line(get("weight"))
        weight: float = 1
        if w_raw:
            n = float(w_raw.replace(",", ".")) if re.fullmatch(r"[0-9]{1,3}(?:[.,][0-9]{1,3})?", w_raw) else float("nan")
            if 0.5 <= n <= 5:
                weight = n
            else:
                err(f'weight "{w_raw}": a number from 0.5 to 5')
        dates: dict[str, str | None] = {"from": None, "until": None}
        for k in ("from", "until"):
            v = one_line(get(k))
            if not v:
                continue
            if valid_day(v):
                dates[k] = v
            else:
                err(f'{k} "{v}": a date written YYYY-MM-DD, year 2000–2099 (Excel may have changed it: format the column as Text)')
        if dates["from"] and dates["until"] and dates["until"] < dates["from"]:
            err(f"until ({dates['until']}) is before from ({dates['from']})")

        def whole(k: str, lo: int, hi: int) -> int | None:
            v = one_line(get(k))
            if not v:
                return None
            if re.fullmatch(r"[0-9]{1,4}", v) and lo <= int(v) <= hi:
                return int(v)
            err(f'{k} "{v}": a whole number from {lo} to {hi}')
            return None

        seconds = whole("seconds", 4, 180)
        reveal = whole("reveal", 4, 60)
        if type_ok and one_line(get("reveal")) and typ not in REVEAL_TYPES:
            err("reveal is only for quiz, truefalse, fill and scramble rows")
        if not type_ok:
            problems.extend(f"{where}: {e}" for e in errs)
            continue

        def takes(f: str) -> bool:
            return typ in CHOICE_TYPES if f == "choices" else typ in ANSWER_TYPES if f == "answer" else True

        L = {lang: {"title": one_line(get(f"title_{lang}")), "text": cell_text(get(f"text_{lang}")),
                    "choices": one_line(get(f"choices_{lang}")), "answer": one_line(get(f"answer_{lang}")),
                    "explain": cell_text(get(f"explain_{lang}")), "credit": one_line(get(f"credit_{lang}")), "list": None}
             for lang in LANGS}
        for lang in LANGS:
            if L[lang]["choices"] and not takes("choices"):
                err(f"choices_{lang} is only for quiz and poll rows")
            if L[lang]["answer"] and not takes("answer"):
                err(f"answer_{lang} is only for fill and scramble rows")
        langs: list[str] = []
        for lang in LANGS:
            v = L[lang]
            used = [f for f in LANG_FIELDS if takes(f) and v[f]]
            if not used:
                continue
            langs.append(lang)
            others = ", ".join(f"{f}_{lang}" for f in used)
            for need in NEEDS[typ]:
                opts = need.split("|")
                if any(v[f] for f in opts):
                    continue
                if len(opts) == 1:
                    err(f"{need}_{lang} is empty, but other {LANG_NAME[lang][0]} cells are filled ({others}): fill it in, or empty them")
                else:
                    err(f"{' and '.join(f'{f}_{lang}' for f in opts)} are both empty, but other {LANG_NAME[lang][0]} cells are filled ({others}): fill one in, or empty them")

            def too_long(f: str, mx: int):
                n = len(v[f])
                if v[f] and n > mx:
                    err(f"{f}_{lang} is {n} characters long: at most {mx}")

            too_long("title", MAX["title"])
            too_long("text", MAX["short_text"] if typ in SHORT_TEXT else MAX["text"])
            if typ == "fill":
                too_long("answer", MAX["answer"])
            too_long("explain", MAX["explain"])
            too_long("credit", MAX["credit"])
            if takes("choices") and v["choices"]:
                lst = [TRIM.sub("", c) for c in v["choices"].split("|")]
                if len(lst) < 2 or len(lst) > 6:
                    err(f"choices_{lang}: give 2 to 6 choices separated by |")
                else:
                    for k, c in enumerate(lst):
                        if not c:
                            err(f"choices_{lang}: choice {k + 1} is empty")
                        elif len(c) > MAX["choice"]:
                            err(f"choices_{lang}: choice {k + 1} is {len(c)} characters long: at most {MAX['choice']}")
                    lower = [c.lower() for c in lst]
                    dup = next((k for k, c in enumerate(lower) if c and lower.index(c) != k), -1)
                    if dup >= 0:
                        err(f'choices_{lang}: two choices are the same ("{lst[dup]}")')
                    v["list"] = lst
            if typ == "fill" and v["text"]:
                blanks = len(re.findall(r"_{3,}", v["text"]))
                if not blanks:
                    err(f"text_{lang}: put ___ (three underscores) where the answer goes")
                elif blanks > 1:
                    err(f"text_{lang}: has more than one ___ blank")
            if typ == "scramble" and v["answer"]:
                letters = sum(1 for ch in v["answer"] if ch.isalpha())
                if not all(ch.isalpha() or ch == " " for ch in v["answer"]) or letters < 3 or letters > 16:
                    err(f'answer_{lang} "{v["answer"]}": letters and spaces only, 3 to 16 letters')
        if takes("choices") and L["en"]["list"] and L["es"]["list"] and len(L["en"]["list"]) != len(L["es"]["list"]):
            err(f"choices_en has {len(L['en']['list'])} choices and choices_es has {len(L['es']['list'])}: both languages need the same number, in the same order")
        if not langs and typ not in MEDIA_TYPES:
            err("the row has no text in English or Spanish: fill in text_en, text_es or both")

        cor_raw = one_line(get("correct"))
        cor_lc = cor_raw.lower()
        correct = None
        if typ == "quiz":
            count = len(next((L[x]["list"] for x in langs if L[x]["list"]), None) or [])
            idx = int(cor_raw) - 1 if re.fullmatch(r"[1-6]", cor_raw) else ord(cor_lc) - 97 if re.fullmatch(r"[a-f]", cor_lc) else -1
            if not cor_raw:
                err("correct is empty: the number (1–6) or letter (A–F) of the right choice")
            elif idx < 0:
                err(f'correct "{cor_raw}": the number (1–6) or letter (A–F) of the right choice')
            elif count and idx >= count:
                err(f'correct "{cor_raw}": there are only {count} choices')
            else:
                correct = idx
        elif typ == "truefalse":
            if not cor_raw:
                err("correct is empty: write true or false")
            elif cor_lc in TF_TRUE:
                correct = True
            elif cor_lc in TF_FALSE:
                correct = False
            else:
                err(f'correct "{cor_raw}": write true or false')
        elif cor_raw:
            err("correct is only for quiz and truefalse rows")

        media_raw = one_line(get("media_url"))
        media = None
        yt = None
        if typ in MEDIA_TYPES:
            u = split_url(media_raw) if media_raw else None
            if not media_raw:
                err("media_url is empty")
            elif not u:
                err(f'media_url "{media_raw}": not an https:// link')
            elif not host_ok(u["host"]):
                err(f"media_url: {u['host']} is not one of the allowed sites ({HOSTS_EN})")
            elif typ == "video":
                yt = youtube_of(media_raw)
                if yt:
                    src = f"https://www.youtube.com/shorts/{yt['id']}" if yt["short"] else f"https://www.youtube.com/watch?v={yt['id']}"
                    media = {"kind": "youtube", "src": src, "id": yt["id"], "short": yt["short"],
                             "poster": f"https://i.ytimg.com/vi/{yt['id']}/hqdefault.jpg"}
                elif re.search(r"\.(?:mp4|webm)\Z", u["path"], re.I):
                    media = {"kind": "video", "src": media_raw}
                else:
                    err(f'media_url "{media_raw}": a YouTube video or an https .mp4 / .webm file')
            elif typ == "audio":
                if re.search(r"\.(?:mp3|m4a|ogg)\Z", u["path"], re.I):
                    media = {"kind": "audio", "src": media_raw}
                else:
                    err(f'media_url "{media_raw}": an https .mp3 / .m4a / .ogg file')
            elif re.search(r"\.(?:jpe?g|png|webp)\Z", u["path"], re.I):
                media = {"kind": "image", "src": media_raw}
            else:
                err(f'media_url "{media_raw}": an https .jpg / .png / .webp picture')
        elif media_raw:
            err("media_url is only for video, audio and image rows")
        times: dict[str, int | None] = {"start": None, "end": None}
        for k in ("start", "end"):
            v = one_line(get(k))
            if not v:
                continue
            if typ not in ("video", "audio"):
                err(f"{k} is only for video and audio rows")
                continue
            s = seconds_of(v)
            if s is None:
                err(f'{k} "{v}": seconds (90) or m:ss (1:30)')
            else:
                times[k] = s
        start = times["start"] if times["start"] is not None else (yt["start"] if yt else None)
        if start is not None and times["end"] is not None and times["end"] <= start:
            err(f"end ({clock(times['end'])}) is not after start ({clock(start)})")

        qr_raw = one_line(get("qr_url"))
        qr = qr_es = None
        if not qr_raw:
            if typ == "qr":
                err("qr_url is empty")
        else:
            resolved = resolve_site(qr_raw, base)
            u = split_url(resolved["en"]) if resolved else None
            if not u:
                err(f'qr_url "{qr_raw}": an https:// link, or {{site}}… for a page of this website')
            elif not host_ok(u["host"]):
                err(f"qr_url: {u['host']} is not one of the allowed sites ({HOSTS_EN})")
            elif PDF_WORD.search(u["path"]):   # the player prints the address (host and path) under the code
                err("qr_url: a link to a document file (its address shows under the code): link to the page that offers the document")
            else:
                qr, qr_es = resolved["en"], resolved["es"]
        src_raw = one_line(get("source_url"))
        if not src_raw:
            if typ in SOURCE_TYPES:
                err("source_url is empty: where can this be checked? (an https:// link)")
        elif not split_url(src_raw):
            err(f'source_url "{src_raw}": not an https:// link')

        for lang in LANGS:
            for f in LANG_FIELDS:
                v = L[lang][f]
                if not v or not takes(f):
                    continue
                name = f"{f}_{lang}"
                marks: list[str] = []
                for m in re.finditer(r"\{([^{}]*)\}", v):
                    if m[1] not in PLACEHOLDERS and m[1] not in marks:
                        marks.append(m[1])
                for mk in marks:
                    err(f"{name}: {{{mk}}} is not a placeholder the booth knows ({{event}}, {{committee}}, {{site}})")
                for word, why in refused_in(v):
                    err(f"{name}: “{word}” is not used on the booth — {why}")

        if errs:
            problems.extend(f"{where}: {e}" for e in errs)
            continue
        if not on:
            continue

        def block(lang: str) -> dict | None:
            if lang not in langs:
                return None
            x = L[lang]
            return {"title": x["title"] or None, "text": x["text"] or None,
                    "choices": (x["list"] or []) if takes("choices") else [],
                    "answer": (x["answer"] or None) if takes("answer") else None,
                    "explain": x["explain"] or None, "credit": x["credit"] or None, "rows": []}

        mb = media_block(**media, start=start or 0, end=times["end"]) if media else None
        items.append({
            "id": rid, "source": "csv", "type": typ, "channel": CSV_CHANNEL[typ], "pub": pub, "langs": langs,
            "en": block("en"), "es": block("es"),
            "correct": correct, "seconds": seconds, "reveal": reveal, "weight": weight,
            "from": dates["from"], "until": dates["until"], "tags": tags,
            "collection": "csv", "first": False, "order": None,
            "media": mb, "online": bool(mb), "qr": qr, "qr_es": qr_es,
            "url": qr or (mb["src"] if mb and mb["kind"] == "youtube" else None),
            "until_ts": None,
        })
    return items, problems


def read_csv_file(path: Path) -> str:
    """A CSV file's text as the build reads it (UTF-8; a byte that is not UTF-8 becomes U+FFFD)."""
    return path.read_bytes().decode("utf-8", errors="replace")


def check_file(path: Path) -> list[str]:
    return check_csv(read_csv_file(path), file=path.name)[1]


# ----------------------------------------------------------------------------------------------------------------
# What each fixture must give, line by line (tests/fixtures/booth_csv/*.csv — one kind of mistake per file)
# ----------------------------------------------------------------------------------------------------------------
HOSTS_LINE = f"is not one of the allowed sites ({HOSTS_EN})"
ID_RULE = "use only a–z, 0–9 and dashes (no spaces or capitals), at most 48 characters"
DATE_RULE = "a date written YYYY-MM-DD, year 2000–2099 (Excel may have changed it: format the column as Text)"
TAG_RULE = "is not a tag (one word: letters, digits, dashes; at most 32 characters)"
TYPE_LIST = ", ".join(TYPES)
SALES_LINE = "is not used on the booth — no sales or urgency words: attraction, not promotion"
UNVERIFIED_LINE = "is not used on the booth — an unverified claim (no source found): leave it out"
EXPECTED: dict[str, tuple[list[str], list[str]]] = {   # fixture → (the ids it shows, its problem lines)
    "correct.csv": (["quiz-letter", "tf-f", "tf-si", "tf-cierto"], [
        "correct.csv row 2 (quiz-no-correct): correct is empty: the number (1–6) or letter (A–F) of the right choice",
        'correct.csv row 3 (quiz-bad-correct): correct "first": the number (1–6) or letter (A–F) of the right choice',
        'correct.csv row 4 (quiz-range): correct "4": there are only 3 choices',
        'correct.csv row 6 (quiz-letter-range): correct "E": there are only 3 choices',
        "correct.csv row 7 (tf-empty): correct is empty: write true or false",
        'correct.csv row 8 (tf-bad): correct "maybe": write true or false',
    ]),
    "empty.csv": ([], ["empty.csv: the file is empty: the first row must be the header (id,on,type,…)"]),
    "fields.csv": (["tf-alias", "qr-alias"], [
        'fields.csv row 4 (bad-on): on "maybe": write yes or no',
        f"fields.csv row 5 (bad-type-empty): type is empty ({TYPE_LIST})",
        f'fields.csv row 6 (bad-type): type "trivia" is not one of: {TYPE_LIST}',
        'fields.csv row 7 (bad-pub): pub "AA Grapevine": write gv, lv or both',
        f'fields.csv row 8 (bad-tags): tags: "#hash" {TAG_RULE}',
        f'fields.csv row 8 (bad-tags): tags: "toolongtagtoolongtagtoolongtagxyz" {TAG_RULE}',
        'fields.csv row 9 (bad-weight): weight "0.25": a number from 0.5 to 5',
        'fields.csv row 10 (bad-weight-word): weight "six": a number from 0.5 to 5',
        f'fields.csv row 11 (bad-dates): from "3/1/2027": {DATE_RULE}',
        f'fields.csv row 11 (bad-dates): until "2027-02-30": {DATE_RULE}',
        "fields.csv row 12 (bad-order): until (2027-04-01) is before from (2027-05-01)",
        'fields.csv row 13 (bad-seconds): seconds "200": a whole number from 4 to 180',
        "fields.csv row 13 (bad-seconds): reveal is only for quiz, truefalse, fill and scramble rows",
        'fields.csv row 14 (bad-reveal): reveal "2": a whole number from 4 to 60',
        f'fields.csv row 15 (bad-year): from "0027-03-01": {DATE_RULE}',
        f'fields.csv row 15 (bad-year): until "2207-10-03": {DATE_RULE}',
    ]),
    "header-missing.csv": ([], ["header-missing.csv header: the header (first row) has no type column"]),
    "header-twice.csv": (["fact-1"], ["header-twice.csv header: column text_en is in the header twice: the first one is used"]),
    "ids.csv": (["fact-ok"], [
        "ids.csv row 3: id is empty",
        f'ids.csv row 4 (Fact-Caps): id "Fact-Caps": {ID_RULE}',
        f'ids.csv row 5 (fact with spaces): id "fact with spaces": {ID_RULE}',
        f'ids.csv row 6 (fact--double): id "fact--double": {ID_RULE}',
        f'ids.csv row 7 (-fact-lead): id "-fact-lead": {ID_RULE}',
        f'ids.csv row 8 (fact-{"a" * 43}): id "fact-{"a" * 44}": {ID_RULE}',
        'ids.csv row 9 (fact-ok): id "fact-ok" is already used in row 2',
        "ids.csv row 14 (fact-off-bad): the row has no text in English or Spanish: fill in text_en, text_es or both",
    ]),
    "languages.csv": (["image-neutral"], [
        "languages.csv row 2 (quiz-es-no-choices): choices_es is empty, but other Spanish cells are filled (text_es): fill it in, or empty them",
        "languages.csv row 3 (quote-no-credit): credit_en is empty, but other English cells are filled (text_en): fill it in, or empty them",
        "languages.csv row 4 (history-no-title): title_en is empty, but other English cells are filled (text_en): fill it in, or empty them",
        "languages.csv row 5 (qr-credit-only): title_es and text_es are both empty, but other Spanish cells are filled (credit_es): fill one in, or empty them",
        "languages.csv row 6 (video-credit-only): title_en and text_en are both empty, but other English cells are filled (credit_en): fill one in, or empty them",
        "languages.csv row 7 (prompt-empty): the row has no text in English or Spanish: fill in text_en, text_es or both",
        "languages.csv row 9 (long-texts): title_en is 81 characters long: at most 80",
        "languages.csv row 9 (long-texts): text_en is 301 characters long: at most 300",
        "languages.csv row 9 (long-texts): explain_en is 241 characters long: at most 240",
        "languages.csv row 9 (long-texts): credit_en is 201 characters long: at most 200",
        "languages.csv row 10 (quiz-long-question): text_en is 181 characters long: at most 180",
        "languages.csv row 11 (choices-one): choices_en: give 2 to 6 choices separated by |",
        "languages.csv row 12 (choices-seven): choices_en: give 2 to 6 choices separated by |",
        "languages.csv row 13 (choices-empty): choices_en: choice 2 is empty",
        "languages.csv row 14 (choices-long): choices_en: choice 2 is 71 characters long: at most 70",
        'languages.csv row 15 (choices-dup): choices_en: two choices are the same ("yes")',
        "languages.csv row 16 (choices-mismatch): choices_en has 3 choices and choices_es has 2: both languages need the same number, in the same order",
        "languages.csv row 17 (fill-no-blank): text_en: put ___ (three underscores) where the answer goes",
        "languages.csv row 18 (fill-two-blanks): text_en: has more than one ___ blank",
        'languages.csv row 19 (scramble-digits): answer_en "AA2026": letters and spaces only, 3 to 16 letters',
        'languages.csv row 20 (scramble-long): answer_en "ABCDEFGHIJKLMNOPQ": letters and spaces only, 3 to 16 letters',
        'languages.csv row 21 (scramble-short): answer_en "AA": letters and spaces only, 3 to 16 letters',
        "languages.csv row 22 (wrong-columns): choices_en is only for quiz and poll rows",
        "languages.csv row 22 (wrong-columns): answer_en is only for fill and scramble rows",
        "languages.csv row 22 (wrong-columns): correct is only for quiz and truefalse rows",
        "languages.csv row 22 (wrong-columns): media_url is only for video, audio and image rows",
    ]),
    "links.csv": (["qr-site", "qr-site-es", "message-qr"], [
        "links.csv row 2 (qr-missing): qr_url is empty",
        'links.csv row 5 (qr-site-middle): qr_url "https://www.aa.org/{site}": an https:// link, or {site}… for a page of this website',
        f"links.csv row 6 (qr-host): qr_url: www.facebook.com {HOSTS_LINE}",
        'links.csv row 7 (qr-mailto): qr_url "mailto:grapevine@neta65.org": an https:// link, or {site}… for a page of this website',
        "links.csv row 8 (fact-no-source): source_url is empty: where can this be checked? (an https:// link)",
        'links.csv row 9 (fact-bad-source): source_url "www.aa.org": not an https:// link',
        "links.csv row 11 (qr-document): qr_url: a link to a document file (its address shows under the code): link to the page that offers the document",
    ]),
    "media.csv": (["vid-youtu-be", "vid-shorts", "vid-embed", "vid-mobile", "vid-file", "audio-file", "vid-times",
                   "audio-podcasts-host"], [
        "media.csv row 2 (vid-empty): media_url is empty",
        'media.csv row 3 (vid-http): media_url "http://www.youtube.com/watch?v=V3RzyHdgQCY": not an https:// link',
        f"media.csv row 4 (vid-host): media_url: vimeo.com {HOSTS_LINE}",
        'media.csv row 5 (vid-userinfo): media_url "https://www.aa.org@evil.example/x.mp4": not an https:// link',
        'media.csv row 6 (vid-mp3): media_url "https://episodes.captivate.fm/episode/x.mp3": a YouTube video or an https .mp4 / .webm file',
        'media.csv row 7 (audio-youtube): media_url "https://www.youtube.com/watch?v=V3RzyHdgQCY": an https .mp3 / .m4a / .ogg file',
        'media.csv row 8 (image-gif): media_url "https://www.aa.org/picture.gif": an https .jpg / .png / .webp picture',
        'media.csv row 13 (vid-bad-id): media_url "https://www.youtube.com/watch?v=short": a YouTube video or an https .mp4 / .webm file',
        'media.csv row 17 (vid-bad-times): start "1:75": seconds (90) or m:ss (1:30)',
        'media.csv row 17 (vid-bad-times): end "abc": seconds (90) or m:ss (1:30)',
        "media.csv row 18 (vid-end-before): end (1:30) is not after start (2:00)",
        "media.csv row 19 (vid-url-start-end): end (1:30) is not after start (2:00)",
        "media.csv row 20 (image-start): start is only for video and audio rows",
    ]),
    "not-utf8.csv": (["fact-latin"], [
        "not-utf8.csv: the file is not saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)",
    ]),
    # the good file tests/test_booth_build.py builds a show from
    "show.csv": (["quiz-one", "video-short", "video-dupe", "audio-dupe", "message-event"], []),
    "structure.csv": (["fact-ok", "fact-multi"], [
        'structure.csv row 5: a cell starts with a double quote (") that is never closed: everything after it was read as that one cell',
        "structure.csv row 3 (fact-comma): the row has 5 cells but the header has 4: a comma inside a text needs the whole cell in double quotes",
        "structure.csv row 5 (fact-unclosed): source_url is empty: where can this be checked? (an https:// link)",
    ]),
    "words.csv": (["w-conference-ok", "w-today-event", "w-notes", "w-app-ok"], [
        "words.csv row 2 (w-pdf): text_en: “PDF” is not used on the booth — say “document” instead",
        "words.csv row 3 (w-pdfs): text_en: “PDFs” is not used on the booth — say “document” instead",
        "words.csv row 4 (w-donate): text_en: “donate” is not used on the booth — Grapevine and La Viña take no donations (say “Carry the Message gift”)",
        "words.csv row 5 (w-donativo): text_es: “donativo” is not used on the booth — Grapevine and La Viña take no donations (say “Carry the Message gift”)",
        "words.csv row 6 (w-contribution): text_en: “contribution to Grapevine” is not used on the booth — AA Grapevine, Inc. does not accept contributions",
        "words.csv row 7 (w-contribuir): text_es: “contribuir a La Viña” is not used on the booth — AA Grapevine, Inc. does not accept contributions",
        f"words.csv row 8 (w-sales): text_en: “Buy now” {SALES_LINE}",
        f"words.csv row 9 (w-sale): text_en: “sale!” {SALES_LINE}",
        f"words.csv row 10 (w-before-prices): text_en: “before prices go up” {SALES_LINE}",
        f"words.csv row 11 (w-subscribe-today): text_en: “Subscribe today” {SALES_LINE}",
        f"words.csv row 12 (w-spanish-sales): text_es: “Apúrate” {SALES_LINE}",
        "words.csv row 13 (w-conference): text_en: “Conference-approved” is not used on the booth — say “recognized by the Conference as the international journal of AA”",
        "words.csv row 15 (w-aprobada): text_es: “aprobada por la Conferencia” is not used on the booth — say “recognized by the Conference as the international journal of AA”",
        "words.csv row 16 (w-today): text_en: “Today only” is not used on the booth — “today only” needs {event} (the booth shows the same rows on many days)",
        "words.csv row 18 (w-placeholder): text_en: {Event} is not a placeholder the booth knows ({event}, {committee}, {site})",
        "words.csv row 18 (w-placeholder): text_en: {foo} is not a placeholder the booth knows ({event}, {committee}, {site})",
        "words.csv row 19 (w-explain): explain_en: “PDF” is not used on the booth — say “document” instead",
        f"words.csv row 21 (w-download): text_en: “Download now” {SALES_LINE}",
        f"words.csv row 22 (w-descargala): text_es: “Descárgala ahora” {SALES_LINE}",
        f"words.csv row 23 (w-subscribe-shout): text_en: “Subscribe!” {SALES_LINE}",
        f"words.csv row 24 (w-millions): text_en: “reach millions” {UNVERIFIED_LINE}",
        f"words.csv row 25 (w-reto): text_es: “Reto 183” {UNVERIFIED_LINE}",
    ]),
}

# Cases held in the test itself: what a repository's line ends cannot keep (CRLF, a BOM before the header), and the
# shapes of the items
INLINE: dict[str, str] = {
    "crlf-bom.csv": "﻿id,type,text_en,text_es,credit_en,credit_es,source_url\r\n"
                    'quote-1,quote,"I am responsible.\r\nAnd for that: I am responsible.",'
                    '"Yo soy responsable.",Source,Fuente,\r\n'
                    "#note,,,,,,\r\n\r\n",
    "cr-only.csv": "id,type,text_en\rprompt-1,prompt,What would you tell a newcomer?\r",
    "shapes.csv": "id,on,type,pub,tags,weight,seconds,reveal,title_en,text_en,choices_en,correct,answer_en,explain_en,"
                  "text_es,choices_es,answer_es,media_url,start,end,qr_url,source_url\n"
                  "quiz-b,,quiz,lv,Writing;Service writing,\"1,5\",30,15,,Which?,a | b | c,B,,Because.,¿Cuál?,"
                  "x | y | z,,,,,{site_es},https://www.aa.org/\n"
                  "fill-x,yes,fill,,,,,,,The ___ of AA.,,,journal,,La ___ de AA.,,revista,,,,,https://www.aa.org/\n"
                  "short-1,,video,gv,,,,,A Short,,,,,,,,,https://youtube.com/shorts/0uyVPlTcSeI?feature=share,0:05,0:40,,\n"
                  "pod-1,,audio,,podcast,,,,An episode,,,,,,,,,https://episodes.captivate.fm/episode/abc.m4a,1:02:03,,"
                  "https://www.aagrapevine.org/podcasts,\n",
}


def _main(argv: list[str]) -> int:
    """`python tests/test_booth_csv.py file.csv …` — each file's rows shown and its problems (exit 1 with any)."""
    files = [Path(a) for a in argv]
    bad = 0
    for path in files:
        items, problems = check_csv(read_csv_file(path), file=path.name)
        print(f"{path}: {len(items)} row(s) shown, {len(problems)} problem(s)")
        for p in problems:
            print(f"  {p}")
        bad += len(problems)
    return 1 if bad else 0


# ----------------------------------------------------------------------------------------------------------------
# The tests
# ----------------------------------------------------------------------------------------------------------------
class Real(unittest.TestCase):
    """content/booth/booth.csv, the file the committee edits."""

    @classmethod
    def setUpClass(cls):
        cls.text = read_csv_file(CSV_FILE)
        cls.items, cls.problems = check_csv(cls.text)
        cls.rows, _ = parse_csv(cls.text)

    def test_no_problem_at_all(self):
        self.assertEqual(self.problems, [], "fix these rows in content/booth/booth.csv (content/booth/README.md says how)")

    def test_utf8_with_the_header_first(self):
        CSV_FILE.read_bytes().decode("utf-8")   # strict: never a byte that is not UTF-8
        header = [one_line(h).lower() for h in self.rows[0]]
        self.assertIn("id", header)
        self.assertIn("type", header)

    def test_the_shown_rows(self):
        self.assertGreater(len(self.items), 20)
        ids = [i["id"] for i in self.items]
        self.assertEqual(len(ids), len(set(ids)))
        for it in self.items:
            with self.subTest(id=it["id"]):
                self.assertTrue(it["langs"] or it["type"] in MEDIA_TYPES)
                for lang in it["langs"]:
                    self.assertIsNotNone(it[lang])
                if it["type"] == "quote":   # a quote always carries its credit line
                    self.assertTrue(all(it[lang]["credit"] for lang in it["langs"]))

    def test_videos_and_episodes_are_the_official_ones(self):
        # YouTube plays any channel: a video row must play an official Grapevine / La Viña video, one the site's list
        # of the official channel knows (data/site/videos.json — a video the channel has just published is in it after
        # the next daily update); an audio row an AA Grapevine podcast episode (data/site/episodes.json)
        videos = json.loads((ROOT / "data" / "site" / "videos.json").read_text(encoding="utf-8"))
        episodes = json.loads((ROOT / "data" / "site" / "episodes.json").read_text(encoding="utf-8"))
        vids = {(it.get("extra") or {}).get("video_id") for it in videos.get("items", [])}
        mp3s = {(it.get("extra") or {}).get("audio_url") for it in episodes.get("items", [])}
        for it in self.items:
            m = it["media"]
            if m and m["kind"] == "youtube":
                self.assertIn(m["id"], vids, f"{it['id']}: not a video of the official Grapevine / La Viña channel the site knows")
            if m and m["kind"] == "audio" and "captivate.fm" in m["src"]:
                self.assertIn(m["src"], mp3s, f"{it['id']}: not an episode of the podcasts the site knows")


class Reader(unittest.TestCase):
    """The CSV reader (the build's parseCsv) reads a file exactly as Python's csv module does."""

    CASES = [
        "a,b\r\nc,d\r\n", "a,b\nc,d", "a,b\rc,d\r", "a,b\r\n\r\nc,d\r\n", "\n\na\n",
        '"x, y","He said ""hi"""\r\n', '"line1\r\nline2",z\n', '"line1\nline2"\n', "a,,b\n,\n",
        ' "q" ,x\n', '"ab"c,d\n', 'a"b,c\n', '""\n', '"",""\n', "trailing,\n", 'a,"b\nc',
        "ñ,é,“quotes”\n", 'x,"multi\n\nline"\r\ny\n',
    ]

    def test_like_the_csv_module(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(parse_csv(text)[0], list(csv.reader(io.StringIO(text, newline=""))))

    def test_a_bom_is_dropped_and_an_open_quote_named(self):
        self.assertEqual(parse_csv("﻿id,type\r\n1,2\r\n"), ([["id", "type"], ["1", "2"]], None))
        self.assertEqual(parse_csv('h\nok\n"never closed\nnext'), ([["h"], ["ok"], ["never closed\nnext"]], 3))
        self.assertEqual(parse_csv('h\n"closed"\n'), ([["h"], ["closed"]], None))

    def test_cells_as_the_checks_read_them(self):
        self.assertEqual(cell_text("  Line one  \r\nLine two\r\n\r\n\r\n\r\nLine three  "), "Line one\nLine two\n\nLine three")
        self.assertEqual(one_line(" A  title\n here "), "A title here")
        self.assertEqual(cell_text("Viña"), "Viña")   # NFC


class Fixtures(unittest.TestCase):
    """tests/fixtures/booth_csv: each file's rows shown and its problems, line by line."""

    def test_every_fixture_is_listed(self):
        self.assertEqual(sorted(f.name for f in FIXTURES.glob("*.csv")), sorted(EXPECTED))

    def test_each_fixture_line_by_line(self):
        for name, (ids, lines) in EXPECTED.items():
            with self.subTest(fixture=name):
                items, problems = check_csv(read_csv_file(FIXTURES / name), file=name)
                self.assertEqual(problems, lines)
                self.assertEqual([i["id"] for i in items], ids)

    def test_what_the_good_rows_become(self):
        items = {i["id"]: i for f in ("fields.csv", "media.csv", "links.csv", "structure.csv", "correct.csv")
                 for i in check_csv(read_csv_file(FIXTURES / f), file=f)[0]}
        tf = items["tf-alias"]
        self.assertEqual((tf["type"], tf["channel"], tf["pub"], tf["correct"], tf["weight"]), ("truefalse", "quiz", "gv", True, 1.5))
        self.assertEqual((tf["tags"], tf["from"], tf["until"], tf["seconds"], tf["reveal"]), (["history", "writing", "humor"], "2027-03-01", "2027-03-15", 20, 10))
        qr = items["qr-alias"]
        self.assertEqual((qr["type"], qr["pub"], qr["weight"], qr["qr"], qr["url"]), ("qr", "both", 2.5, BASE, BASE))
        self.assertEqual((items["qr-site"]["qr"], items["qr-site"]["qr_es"]), (BASE + "contribute/", BASE + "es/contribute/"))
        self.assertEqual((items["qr-site-es"]["qr"], items["qr-site-es"]["qr_es"]), (BASE + "es/meetings/", BASE + "es/meetings/"))
        self.assertEqual((qr["qr"], qr["qr_es"]), (BASE, BASE + "es/"))
        self.assertEqual(items["fact-multi"]["en"]["text"], 'Line one\nLine two with "quotes"')
        self.assertEqual((items["quiz-letter"]["correct"], items["tf-f"]["correct"], items["tf-si"]["correct"]), (2, False, True))
        yt = items["vid-youtu-be"]["media"]
        self.assertEqual((yt["kind"], yt["id"], yt["short"], yt["start"], yt["src"]), ("youtube", "V3RzyHdgQCY", False, 90, "https://www.youtube.com/watch?v=V3RzyHdgQCY"))
        self.assertEqual(items["vid-youtu-be"]["url"], yt["src"])
        sh = items["vid-shorts"]["media"]
        self.assertEqual((sh["short"], sh["src"], sh["poster"]), (True, "https://www.youtube.com/shorts/0uyVPlTcSeI", "https://i.ytimg.com/vi/0uyVPlTcSeI/hqdefault.jpg"))
        self.assertEqual(items["vid-mobile"]["media"]["start"], 45)
        self.assertEqual((items["vid-times"]["media"]["start"], items["vid-times"]["media"]["end"]), (90, 165))
        self.assertEqual(items["vid-file"]["media"]["kind"], "video")
        self.assertEqual(items["audio-file"]["media"]["kind"], "audio")
        # an episode of 2021 to mid-2025: the feed points it at the podcast host's file server
        pod = items["audio-podcasts-host"]["media"]
        self.assertEqual((pod["kind"], pod["src"].split("/")[2]), ("audio", "podcasts.captivate.fm"))
        for it in items.values():
            self.assertEqual(it["online"], it["media"] is not None)


class Rules(unittest.TestCase):
    """Rules best shown with a few lines of CSV."""

    def check(self, body: str, header: str = "id,type,text_en,source_url", site_url: str = BASE):
        return check_csv(header + "\n" + body + "\n", file="t.csv", site_url=site_url)

    def test_crlf_bom_and_line_breaks_in_quotes(self):
        items, problems = check_csv(INLINE["crlf-bom.csv"], file="crlf-bom.csv")
        self.assertEqual(problems, [])
        self.assertEqual(items[0]["en"]["text"], "I am responsible.\nAnd for that: I am responsible.")
        self.assertEqual((items[0]["langs"], items[0]["es"]["credit"]), (["en", "es"], "Fuente"))
        self.assertEqual(check_csv(INLINE["cr-only.csv"], file="cr-only.csv")[0][0]["id"], "prompt-1")

    def test_the_item_shape(self):
        items, problems = check_csv(INLINE["shapes.csv"], file="shapes.csv")
        self.assertEqual(problems, [])
        quiz, fill, short, pod = items
        self.assertEqual(list(quiz), ["id", "source", "type", "channel", "pub", "langs", "en", "es", "correct", "seconds",
                                      "reveal", "weight", "from", "until", "tags", "collection", "first", "order", "media",
                                      "online", "qr", "qr_es", "url", "until_ts"])
        self.assertEqual(list(quiz["en"]), ["title", "text", "choices", "answer", "explain", "credit", "rows"])
        self.assertEqual((quiz["correct"], quiz["weight"], quiz["tags"], quiz["qr"]), (1, 1.5, ["writing", "service"], BASE + "es/"))
        self.assertEqual(quiz["qr_es"], BASE + "es/", "{site_es}: the Spanish home on every slide")
        self.assertIsNone(pod["qr_es"], "another site's link: the same code on every slide")
        self.assertEqual((quiz["en"]["choices"], quiz["es"]["choices"], quiz["es"]["explain"]), (["a", "b", "c"], ["x", "y", "z"], None))
        self.assertEqual((quiz["source"], quiz["collection"], quiz["first"], quiz["order"], quiz["until_ts"]), ("csv", "csv", False, None, None))
        self.assertEqual((fill["en"]["answer"], fill["es"]["answer"], fill["en"]["choices"]), ("journal", "revista", []))
        self.assertEqual(short["media"], {"kind": "youtube", "src": "https://www.youtube.com/shorts/0uyVPlTcSeI", "id": "0uyVPlTcSeI",
                                          "short": True, "local": False, "poster": "https://i.ytimg.com/vi/0uyVPlTcSeI/hqdefault.jpg",
                                          "start": 5, "end": 40, "muted": False, "fit": "contain", "w": None, "h": None, "bytes": None})
        self.assertEqual((pod["media"]["kind"], pod["media"]["start"], pod["langs"], pod["qr"]), ("audio", 3723, ["en"], "https://www.aagrapevine.org/podcasts"))

    def test_a_row_switched_off_is_checked_but_not_shown(self):
        items, problems = self.check("a,yes,fact,Shown.,https://www.aa.org/\nb,no,fact,Off.,https://www.aa.org/\n"
                                     "c,no,fact,,https://www.aa.org/", header="id,on,type,text_en,source_url")
        self.assertEqual([i["id"] for i in items], ["a"])
        self.assertEqual(problems, ["t.csv row 4 (c): the row has no text in English or Spanish: fill in text_en, text_es or both"])

    def test_the_sites_own_address_is_allowed(self):
        body = "own,image,A picture,https://gvlv.example.org/assets/img/table.jpg\nother,image,A picture,https://example.org/x.jpg"
        items, problems = self.check(body, header="id,type,title_en,media_url", site_url="https://gvlv.example.org")
        self.assertEqual([i["id"] for i in items], ["own"])
        self.assertEqual(problems, [f"t.csv row 3 (other): media_url: example.org {HOSTS_LINE}"])
        _, problems = self.check("q,qr,Scan,{site}", header="id,type,title_en,qr_url", site_url="")
        self.assertEqual(problems, ['t.csv row 2 (q): qr_url "{site}": an https:// link, or {site}… for a page of this website'])

    def test_a_language_alone(self):
        items, _ = self.check("es-only,fact,,Un dato.,https://www.aa.org/", header="id,type,text_en,text_es,source_url")
        self.assertEqual((items[0]["langs"], items[0]["en"], items[0]["es"]["text"]), (["es"], None, "Un dato."))

    def test_placeholders_stay_for_the_player(self):
        items, problems = self.check("m,message,Welcome to {event}! We are the {committee}: {site}", header="id,type,text_en")
        self.assertEqual(problems, [])
        self.assertEqual(items[0]["en"]["text"], "Welcome to {event}! We are the {committee}: {site}")


class Twin(unittest.TestCase):
    """The build's checker (eleventy/filters/booth.js checkCsv) gives the same lines and the same items as this one —
    for every fixture, the inline cases and the real file — and a Spanish line for every problem."""

    def test_the_same_lines_and_items(self):
        files = [{"name": f.name, "text": read_csv_file(f)} for f in sorted(FIXTURES.glob("*.csv"))]
        files += [{"name": n, "text": t} for n, t in INLINE.items()]
        files.append({"name": CSV_FILE.name, "text": read_csv_file(CSV_FILE)})
        res = run_js(self, """
            const B = await imp("eleventy/filters/booth.js");
            out(input.files.map((f) => {
              const r = B.checkCsv(f.text, { site: { url: input.site }, file: f.name });
              return { items: r.items, lines: r.problems.map((p) => `${p.where}: ${p.en}`), es: r.problems.map((p) => p.es) };
            }));
        """, data={"files": files, "site": BASE})
        self.assertEqual(len(res), len(files))
        for f, js in zip(files, res):
            with self.subTest(file=f["name"]):
                items, problems = check_csv(f["text"], file=f["name"])
                self.assertEqual(js["lines"], problems)
                self.assertEqual(js["items"], items)
                for en_line, es in zip(js["lines"], js["es"]):
                    self.assertTrue(es.strip(), en_line)
                    self.assertNotEqual(es, en_line.split(": ", 1)[1], "the Spanish line is a translation")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".csv"):
        sys.exit(_main(sys.argv[1:]))
    unittest.main()
