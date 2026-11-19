"""The Texas writers archive: the owner's exports of the Grapevine and La Viña online archives (CSV files in
content/archive/) → data/raw/writers_archive.json — every story by a writer from Texas, Area 65 or not, since
1944 (Grapevine) and 1996 (La Viña). build_data joins these rows with the Texas stories the daily capture
holds (data/raw/articles.json, any age — so the list keeps growing after the files' date) into
data/site/writers_archive.json: the "Texas writers since 1944" archive on /published/ (docs/DATA_SCHEMA.md).

The files (the folder's top level; README.md and anything that is not a .csv file is ignored — one named
like an archive file but saved in another format, "aagrapevine_archive_2026-11-05.xlsx", is named in the run
summary: save it as CSV):

    content/archive/aagrapevine_archive_2026-10-04.csv     Grapevine (about 36,000 rows)
    content/archive/aalavina_archive_2026-10-04.csv        La Viña (about 3,600 rows)

The newest file of each magazine is used, by the date in its NAME (git keeps no file times): "2026-10-04",
"2026_10_4", "20261004" (a time may follow), "10-04-2026"; a browser's "(1)" copy and "_v2" break a tie,
and a name without a date loses to every dated one. The magazine is read from the name ("grapevine" /
"gv" / "la viña" / "la_vina" / "lv", then "archive", any case) and confirmed by the links inside: when the
links say the other magazine, the links win (and the run summary says so — also when that magazine already
has its file, so the file is not used). An older copy left in the folder is not used — the run summary names
it ("may be deleted"); a magazine without a file keeps the rows of its last one.

A new file is checked before it replaces the last one: it needs the columns Link, Title, Month, Year,
Written By, Location (as published) and Texas Author? (matched by how the header starts, any case), and at
least `writers_archive.min_rows_ratio` (config/site.yml, 0.8) × the rows of the file used before — a
cut-off export would silently drop writers. A file that fails keeps its magazine's older rows (the file they
came from "stays in use until" it is fixed); the source then shows as failed on /status/ (the error names the
file and what is wrong). Only a magazine with no rows and no file on record yet (a first run) takes its
newest older file that passes instead — never an older copy in place of the rows the site already has.

Each row is cleaned (HTML entities and tags, text saved twice as UTF-8 — "MazatlÃ¡n" —, accents written
in two pieces, ligatures, soft hyphens) and kept when its writer is from Texas: the file's "Texas Author?"
says Yes, or the place — the better reading of the printed byline and the file's own City / State columns
(geo.classify_writer) — is in Texas. The issue comes from the Month / Year columns, never from the address
(older addresses, audio pages and "/magazine/<slug>" carry none or another). Bylines are kept exactly as
printed ("H.t.b." → "H.T.B." is the only repair: the export's title case); a letters column lists each of
its Texas writers. Kept: the title, the publisher's own subtitle ("Brief", at most 300 characters), the
theme, the bylines and the link — never a story's text. Where each writer is from is NOT stored: build_data
reads the places again on every run, so a change of the Area 65 counties (config/site.yml
spotlight.neta65_counties) shows at once.

Change detection: a hash of the text with the line ends made equal (the owner's PC saves CRLF, git checks
the file out with LF), so one file has one hash everywhere. `files.<pub>.imported_at` moves only when that
magazine's file (its name or contents) or this parser (PARSER_VERSION) changed. Each row keeps `first_seen`,
the run its address first came in (from the last envelope, by address; a new address: this run) — /status/
counts the stories found in the last 7 days from it —, so the same files give the same rows run after run.
Reading both files takes a few seconds and asks nothing of any web site.

    python -m scripts.sync.writers_archive [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .common import (CONTENT_DIR, MONTHS, ROOT, clean_text, get_logger, load_config, load_raw, now_iso, run_module,
                     save_raw, short_hash, truncate)
from .geo import SCOPES, classify_writer, fold

SOURCE = "writers_archive"
log = get_logger(SOURCE)

PARSER_VERSION = 1           # raise it when a change here changes the rows: every file is imported again
MIN_ROWS_RATIO = 0.8         # config writers_archive.min_rows_ratio (0 = always use the newest file)
BRIEF_MAX = 300              # the publisher's subtitle, cut on a word
PUBS = ("gv", "lv")
PUB_NAME = {"gv": "Grapevine", "lv": "La Viña"}
# The rows' language (their titles are translated from it) and the bylines' (geo). Not guessed from the title:
# a word guesser reads Grapevine's "P. O. Box 1980" and "Viva Las Vegas" as Spanish.
PUB_LANG = {"gv": "en", "lv": "es"}
TEXAS_SCOPES = ("neta65", "texas")
EN_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December")
ES_MONTHS = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre")

# --------------------------------------------------------------------------- file names
NAME_RE = re.compile(r"""(?ix)^
    (?:aa[\s_.-]*)?                                  # "aa" of aagrapevine / aalavina (optional)
    (?P<mag>grapevine|gv|la[\s_.-]*vi(?:n|ñ)a|lv)    # the magazine
    [\s_.-]*archives?                                # "archive"
    (?P<rest>.*?)                                    # the date, " (1)", "_v2", a time … anything
    \.csv$""")
# The date in what follows "archive" — the first that is a real day. (groups: year, month, day)
NAME_DATES = (
    (re.compile(r"(?<!\d)((?:19|20)\d{2})[-_. ](\d{1,2})[-_. ](\d{1,2})(?!\d)"), (1, 2, 3)),   # 2026-10-04, 2026_10_4
    (re.compile(r"(?<!\d)((?:19|20)\d{2})(\d{2})(\d{2})(?!\d)"), (1, 2, 3)),                  # 20261004
    (re.compile(r"(?<!\d)((?:19|20)\d{2})(\d{2})(\d{2})(?=\d{2,6}(?!\d))"), (1, 2, 3)),       # 202610041530 (+ a time)
    (re.compile(r"(?<!\d)(\d{1,2})[-_.](\d{1,2})[-_.]((?:19|20)\d{2})(?!\d)"), (3, 1, 2)),    # 10-04-2026 (U.S. order)
)
COPY_RE = re.compile(r"\((\d{1,3})\)")                              # "… (1).csv": a browser's second download
VERSION_RE = re.compile(r"(?i)(?:^|[\s_.-])v(\d{1,3})(?![a-z\d])")  # "…_v2.csv"


def parse_name(name: str) -> dict | None:
    """'aagrapevine_archive_2026-10-04 (1).csv' → {name, pub, date, copy, version}; None when the name is not an
    archive file's."""
    m = NAME_RE.match(unicodedata.normalize("NFC", name.strip()))
    if not m:
        return None
    rest = m["rest"]
    day = None
    for rx, (yi, mi, di) in NAME_DATES:
        for d in rx.finditer(rest):
            try:
                day = date(int(d[yi]), int(d[mi]), int(d[di]))
                break
            except ValueError:            # "2026-13-40" is no day
                continue
        if day:
            break
    cp, ver = COPY_RE.search(rest), VERSION_RE.search(rest)
    return {"name": name, "pub": "gv" if m["mag"].lower() in ("grapevine", "gv") else "lv", "date": day,
            "copy": int(cp[1]) if cp else 0, "version": int(ver[1]) if ver else 0}


def newest_key(c: dict) -> tuple:
    """Sort key, newest last: the date in the name (none: older than any), then "_v2", then "(1)", then the name."""
    return (c["date"] or date.min, c["version"], c["copy"], c["name"])


def archive_dir(cfg: dict | None = None) -> Path:
    """content/archive, or config writers_archive.folder (a folder of the repository)."""
    wa = (cfg or {}).get("writers_archive")
    folder = clean_text(wa.get("folder")) if isinstance(wa, dict) else ""
    return ROOT / folder if folder else CONTENT_DIR / "archive"


def min_rows_ratio(cfg: dict | None) -> tuple[float, str | None]:
    """(config writers_archive.min_rows_ratio, a note when it is not understood)."""
    wa = (cfg or {}).get("writers_archive")
    v = wa.get("min_rows_ratio") if isinstance(wa, dict) else None
    if v is None or v == "":
        return MIN_ROWS_RATIO, None
    try:
        r = float(v)
    except (TypeError, ValueError):
        return MIN_ROWS_RATIO, (f"writers_archive.min_rows_ratio “{v}” in config/site.yml is not a number like 0.8 "
                                f"— {MIN_ROWS_RATIO} is used")
    return min(max(r, 0.0), 1.0), None


# --------------------------------------------------------------------------- reading
def read_text(path: Path) -> tuple[str, str | None]:
    """The file's text — UTF-8 with or without a BOM; a file saved as Windows-1252 is read too — and a warning
    when it is not clean UTF-8. The BOM is dropped before either reading (read as Windows-1252 it would become
    "ï»¿" in front of the first column's name: "the column Link is missing"). A UTF-8 file with a few bytes that
    are not UTF-8 stays UTF-8 — those bytes show as "\ufffd" —, since read as Windows-1252 every accent of the rest
    would break ("Ã¡"; "Á" and the closing quote ” not even mendable)."""
    raw = path.read_bytes()
    body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        return body.decode("utf-8"), None
    except UnicodeDecodeError as e:
        first = e.start
    text = body.decode("utf-8", errors="replace")
    bad = text.count("\ufffd")
    if len(text) - len(text.encode("ascii", "ignore")) - bad > bad:        # more good UTF-8 letters than bad bytes
        line = body.count(b"\n", 0, first) + 1
        return text, (f"{path.name}: {bad:,} character(s) are not UTF-8 (the first on line {line:,}) — they show "
                      "as “\ufffd”; save it as “CSV UTF-8” again")
    return (body.decode("cp1252", errors="replace"),
            f"{path.name} is not saved as UTF-8 — it was read as Windows-1252 (save it as “CSV UTF-8” next time)")


def content_hash(text: str) -> str:
    """sha256 of the text with every line end as LF: the same for the owner's CRLF file, git's LF copy and a
    copy without the BOM (read_text already dropped it)."""
    return hashlib.sha256(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")).hexdigest()


# Header → field, by how the header STARTS (spaces tidied, any case): "Has Audio Version (audio icon)" → has_audio.
COLUMNS = (("link", ("link", "url")), ("title", ("title",)), ("has_audio", ("has audio",)), ("month", ("month",)),
           ("year", ("year",)), ("theme", ("theme",)), ("author", ("written by", "author")), ("city", ("city",)),
           ("state", ("state",)), ("brief", ("brief",)), ("audio_only", ("audio only",)),
           ("texas", ("texas author",)), ("location", ("location",)), ("notes", ("notes",)))
REQUIRED = {"link": "Link", "title": "Title", "month": "Month", "year": "Year", "author": "Written By",
            "location": "Location (as published)", "texas": "Texas Author?"}


def map_header(names) -> dict[str, str]:
    """{field: the file's own header} — the first header that starts like each field."""
    found: dict[str, str] = {}
    for h in names or []:
        k = re.sub(r"\s+", " ", str(h or "").replace("\ufeff", "").strip()).casefold()
        for field, starts in COLUMNS:
            if field not in found and k.startswith(starts):
                found[field] = h
                break
    return found


def read_rows(text: str) -> tuple[list[dict], dict[str, str]]:
    """(the rows, {field: header})."""
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = list(reader)
    return rows, map_header(reader.fieldnames)


# --------------------------------------------------------------------------- cleaning
_TAG = re.compile(r"<[^>]+>")
# A line break of the magazine's own archive export, written "<lb" with no closing ">" (181 Grapevine rows):
# "The Home Group<lbHeartbeat of AA", "William Silkworth M.D.<lb1873--1951", "…<lb<em>…" — a dash between the parts.
_LINE_BREAK = re.compile(r"\s*<lb\s*/?>?\s*", re.I)
_EDGE_DASH = re.compile(r"^(?:\s*—\s*)+|(?:\s*—\s*)+$")
_MOJIBAKE = re.compile(r"Ã[\x80-\xBF]|Â[\x80-\xBF]|â€")
_MOJI_PAIR = re.compile(r"[ÂÃ][\x80-\xBF]")


def _latin1_pair(m: re.Match) -> str:
    try:
        return m.group(0).encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        return m.group(0)


def repair_mojibake(s: str) -> str:
    """Text saved as UTF-8 and read back as Windows-1252 — "MazatlÃ¡n", "meetingâ€”an amends", up to four layers
    deep ("dÃƒÆ’Ã†â€™…") — back to what was written; a string that mixes good and broken letters is mended pair by
    pair ("MarÃ\xada Inés")."""
    for _ in range(4):
        if not _MOJIBAKE.search(s):
            break
        try:
            t = s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            t = _MOJI_PAIR.sub(_latin1_pair, s)
        if t == s:
            break
        s = t
    return s


def clean_field(v) -> str | None:
    """One field as the site shows it: HTML entities, then the export's "<lb" line breaks (" — ") and tags (" "), broken UTF-8, accents in one piece (NFC),
    the one-letter ligatures fi / fl and soft hyphens, spaces — None when nothing is left. (Entities go first:
    "&amp;" and "&eacute;" hold a ";", the separator of several writers.)"""
    s = html.unescape(str(v or ""))
    if _LINE_BREAK.search(s):       # (only these dashes are trimmed at the ends — never one the text itself has)
        s = _EDGE_DASH.sub("", _TAG.sub(" ", _LINE_BREAK.sub(" — ", s)))
    s = _TAG.sub(" ", s)
    s = unicodedata.normalize("NFC", repair_mojibake(s))
    s = clean_text(s.replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\u00ad", ""))
    return s or None


# --------------------------------------------------------------------------- one row
def canonical(url: str) -> str:
    """https, lower-case host, no query/fragment/trailing slash (the same as articles.canonical — articles.py
    needs BeautifulSoup, this module only the standard library)."""
    p = urlparse(url.strip())
    path = re.sub(r"/{2,}", "/", p.path).rstrip("/") or "/"
    return f"https://{p.netloc.lower()}{path}"


def url_key(url: str) -> str:
    """The key a story is matched by — in both files and in the daily capture: the canonical address, lower case."""
    return canonical(url).lower()


def pub_of_url(url: str | None) -> str | None:
    host = (urlparse(str(url or "").strip()).hostname or "").lower()
    if host.endswith("aagrapevine.org"):
        return "gv"
    if host.endswith("aalavina.org"):
        return "lv"
    return None


def label_from_key(pub: str, key: str | None) -> str | None:
    """'1991-10' → 'October 1991' (Grapevine); '2016-09' → 'Septiembre / Octubre 2016' (La Viña, bimonthly) —
    the same as articles.label_from_key."""
    if not key:
        return None
    y, m = map(int, key.split("-"))
    if pub == "gv":
        return f"{EN_MONTHS[m - 1]} {y}"
    if m % 2 == 1 and m < 12:
        return f"{ES_MONTHS[m - 1]} / {ES_MONTHS[m]} {y}"
    return f"{ES_MONTHS[m - 1]} {y}"


def tidy_label(label: str | None) -> str | None:
    """"june 2026" → "June 2026": lower-case month names capitalized, the rest as printed (the same as
    articles.tidy_label)."""
    if not label:
        return label
    return re.sub(r"[^\W\d_]+", lambda m: m.group(0).capitalize()
                  if m.group(0).islower() and m.group(0) in MONTHS else m.group(0), label)


def issue_of(pub: str, month: str | None, year: str | None) -> tuple[str | None, str | None, int | None, int | None]:
    """The file's Month / Year → (issue_key "YYYY-MM", issue_label, year, month). Grapevine prints a month name
    (any case: "june"), La Viña a pair ("Septiembre / Octubre" — its issue is keyed by the first month)."""
    y = int(year.strip()) if year and re.fullmatch(r"\d{4}", year.strip()) else None
    words = re.split(r"\s*[/–-]\s*|\s+", (month or "").strip())
    m = MONTHS.get(words[0].lower()) if words and words[0] else None
    key = f"{y:04d}-{m:02d}" if y and m else None
    return key, label_from_key(pub, key), y, m


_ANONYMOUS = re.compile(r"(?i)an[oó]nim[oa]s?\.?|anonymous\.?|anon\.|un alcoh[oó]lico an[oó]nimo")
_INITIALS = re.compile(r"(?:[A-Za-z]\.\s?){2,}")


def is_anonymous(name: str | None) -> bool:
    return bool(name and _ANONYMOUS.fullmatch(name.strip()))


def fix_initials(name: str | None) -> str | None:
    """"H.t.b." (the export title-cased the magazine's initials) → "H.T.B."; any other name exactly as printed."""
    return name.upper() if name and _INITIALS.fullmatch(name) else name


# Columns of letters and short pieces (folded titles): "Dear Grapevine", "PO Box 1980", "At Wit's End" …
COLUMN_TITLE_RE = re.compile(r"^(?:dear grapevine|p ?o box 1980|at wit s end|ham on wry|short takes|mail call.*"
                             r"|from the grass roots|carrying the message|your move|sidebar|distilled spirits"
                             r"|the view from here.*|grass roots.*|dear editors)$")


def folded_title(title: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fold(title)).strip()


def is_column(title: str | None, notes: str | None = None) -> bool:
    """A letters or humor column (several writers, or a column's own title) — not one writer's story."""
    return (bool(re.search(r"(?i)multiple contributors", notes or ""))
            or bool(COLUMN_TITLE_RE.match(folded_title(title))))


def _yes(v: str | None) -> bool:
    return (v or "").strip().casefold() in ("yes", "y", "true", "1", "sí", "si")


def _parts(v: str | None) -> list[str]:
    return [p.strip() for p in (v or "").split(";")]


def writers_of(author: str | None, location: str | None, city: str | None, state: str | None) -> list[dict]:
    """The row's writers. A letters column lists several, separated by ";" in Written By, Location, City and
    State — paired by position (a missing state is the last one given; "(city not given)" is no city). With one
    place, the byline is one writer as printed ("Name; U.S. Journal" stays one)."""
    locs, cities, states = _parts(location), _parts(city), _parts(state)
    if len(locs) > 1:
        names = [a for a in _parts(author) if a]
        n = max(len(names), len(locs))
    else:
        names, n = [author or ""], 1
    out = []
    for i in range(n):
        name = fix_initials(names[i] if i < len(names) else None) or None
        place = (locs[i] if i < len(locs) else "") or None
        c = cities[i] if i < len(cities) else ""
        s = states[i] if i < len(states) else (next((x for x in reversed(states) if x), "") if states else "")
        c = "" if c.casefold() == "(city not given)" else c
        if not (name or place or c or s):
            continue
        out.append({"name": name, "place": place, "city": c or None, "state": s or None,
                    "anonymous": is_anonymous(name)})
    return out


def writer_geo(w: dict, pub: str) -> dict:
    """Where one archive writer is from (geo.classify_writer: the printed place and the file's City / State)."""
    return classify_writer(w.get("place"), w.get("city"), w.get("state"), PUB_LANG.get(pub))


def row_scope(writers: list[dict], pub: str) -> str:
    """The row's scope: its best writer's (SCOPES order)."""
    scopes = [writer_geo(w, pub)["scope"] for w in writers] or ["unknown"]
    return min(scopes, key=lambda s: SCOPES.index(s) if s in SCOPES else len(SCOPES))


def texas_answer(v: str | None) -> bool | None:
    """The file's "Texas Author?": Yes → True, No → False, "Unknown (no location in byline)" → None."""
    s = (v or "").strip().casefold()
    return True if s.startswith("y") else False if s.startswith("n") else None


def row_item(row: dict, hdr: dict[str, str], seen_scope: dict | None = None) -> dict | None:
    """One CSV row → the raw item, or None when the writer is not from Texas or the link is not a magazine's.
    `seen_scope` (optional) receives {key: the row's scope} for the run's counts."""
    def get(field: str) -> str | None:
        h = hdr.get(field)
        return clean_field(row.get(h)) if h else None

    link = get("link")
    pub = pub_of_url(link)
    if not link or not pub:
        return None
    writers = writers_of(get("author"), get("location"), get("city"), get("state"))
    texas_csv = texas_answer(get("texas"))
    scope = row_scope(writers, pub)
    if not (texas_csv or scope in TEXAS_SCOPES):
        return None
    url = re.sub(r"(?i)^http://", "https://", link)
    key = url_key(url)
    title = get("title") or re.sub(r"[-_]+", " ", key.rsplit("/", 1)[-1]).strip().capitalize()
    subtitle = truncate(get("brief") or "", BRIEF_MAX) or None
    theme, notes = get("theme"), get("notes") or ""
    issue_key, issue_label, year, month = issue_of(pub, get("month"), get("year"))
    if seen_scope is not None:
        seen_scope[key] = scope if scope in TEXAS_SCOPES else "texas"
    return {
        "id": f"wa:{short_hash(key, 12)}", "source": SOURCE, "kind": "archive_story", "url": url, "key": key,
        "pub": pub, "lang": PUB_LANG[pub], "title": title,
        "date": f"{issue_key}-01" if issue_key else None, "issue_key": issue_key, "issue_label": issue_label,
        "year": year, "month": month, "undated": year is None, "theme": theme, "subtitle": subtitle,
        "writers": writers,
        "audio": _yes(get("has_audio")), "audio_only": _yes(get("audio_only")),
        "online_exclusive": bool(re.search(r"(?i)web exclusive", notes))
        or (theme or "").casefold() == "grapevine online exclusives",
        "column": is_column(title, notes),
        "signature_byline": bool(re.search(r"(?i)taken from (?:the )?signatures?", notes)),
        "group_byline": bool(re.search(r"(?i)\bgroup/(?:institution|area)\b", notes)),
        "texas_csv": texas_csv,
    }


def drop_content_duplicates(items: list[dict]) -> list[dict]:
    """One story the archive lists twice — same magazine, issue, title and writers, the address differing only by
    a "-0" / "-1" ending (a duplicate page of the magazine's site) — is kept once, by its address without the
    ending (or the first one). Works on raw rows and on build_data's archive items alike."""
    def sig(it: dict) -> tuple:
        ws = it.get("writers") or []
        return (it.get("pub"), it.get("issue_key"), folded_title(it.get("title")),
                tuple(fold(w.get("name") or "") for w in ws), tuple(fold(w.get("place") or "") for w in ws),
                re.sub(r"-\d+$", "", it.get("key") or ""))
    groups: dict[tuple, list[dict]] = {}
    for it in items:
        groups.setdefault(sig(it), []).append(it)
    keep = set()
    for g in groups.values():
        base = next((it for it in g if it.get("key") == re.sub(r"-\d+$", "", it.get("key") or "")), g[0])
        keep.add(id(base))
    return [it for it in items if id(it) in keep]


def sort_rows(items: list[dict]) -> list[dict]:
    """Newest issue first (undated rows last), then by address."""
    items = sorted(items, key=lambda i: i.get("key") or "")
    return sorted(items, key=lambda i: i.get("date") or "", reverse=True)


# --------------------------------------------------------------------------- the folder
def candidates(folder: Path) -> tuple[list[dict], list[str], list[str]]:
    """(the archive files of the folder — parse_name + path, any order; the .csv files whose name is not
    understood; the files named like an archive file in another format — "aagrapevine_archive_2026-11-05.xlsx",
    "….csv.xlsx", "….numbers" —, which are not read)."""
    if not folder.is_dir():
        return [], [], []
    found, unknown, not_csv = [], [], []
    for p in sorted(folder.iterdir()):
        if not p.is_file() or p.name.startswith((".", "~$")):
            continue
        if p.suffix.lower() != ".csv":
            if parse_name(p.stem + ".csv"):          # README.md, notes.txt … are not named like one
                not_csv.append(p.name)
            continue
        c = parse_name(p.name)
        if c:
            found.append({**c, "path": p})
        else:
            unknown.append(p.name)
    return found, unknown, not_csv


def links_pub(rows: list[dict], link_header: str | None) -> str | None:
    """The magazine most of the file's links belong to (aagrapevine.org → gv, aalavina.org → lv); None when no
    link says, or as many say each."""
    if not link_header:
        return None
    n = {"gv": 0, "lv": 0}
    for r in rows:
        p = pub_of_url(r.get(link_header))
        if p:
            n[p] += 1
    return None if n["gv"] == n["lv"] else max(n, key=lambda k: n[k])


def import_archive(folder: Path, cfg: dict | None, prev: dict | None) -> dict:
    """Read the folder against the last raw envelope → {"items", "ok", "error", "stats", "extra"} for save_raw."""
    prev = prev or {}
    prev_files = prev.get("files") if isinstance(prev.get("files"), dict) else {}
    prev_items = [i for i in prev.get("items") or [] if isinstance(i, dict) and i.get("key")]
    same_parser = prev.get("parser_version") == PARSER_VERSION
    ratio, ratio_note = min_rows_ratio(cfg)
    now = now_iso()
    try:
        rel = folder.relative_to(ROOT).as_posix()
    except ValueError:
        rel = folder.name
    warnings: list[str] = [ratio_note] if ratio_note else []
    notes: list[str] = []
    errors: list[str] = []
    cands, unknown, not_csv = candidates(folder)
    for n in unknown:
        warnings.append(f"a .csv file in {rel} whose name is not an archive file's (it is not used): {n} — name it "
                        "like aagrapevine_archive_2026-11-05.csv or aalavina_archive_2026-11-05.csv")
    for n in not_csv:
        warnings.append(f"{n} in {rel} is not read — only .csv files are (in Excel: File → Save As → "
                        "“CSV UTF-8 (Comma delimited)”, same name)")

    # Newest first; the links inside decide the magazine. A file is used once it passes the checks (its columns;
    # not much smaller than the file used before). One that fails keeps its magazine on its older rows — only a
    # magazine with no rows and no file on record (a first run) tries its next older file: an older copy never
    # takes the place of the rows the site already has. The files not read or not used are named after the loop.
    olds = {p: [i for i in prev_items if i.get("pub") == p] for p in PUBS}
    old_files = {p: prev_files[p] if isinstance(prev_files.get(p), dict) else None for p in PUBS}
    chosen: dict[str, dict] = {}
    failed: dict[str, list[dict]] = {p: [] for p in PUBS}         # files that failed the checks, newest first
    left: list[dict] = []                                          # files not used: older ones, another's copy

    def settled(p: str) -> bool:
        return p in chosen or bool(failed[p] and (olds[p] or old_files[p]))

    for c in sorted(cands, key=newest_key, reverse=True):
        if all(settled(p) for p in PUBS):
            left.append(c)
            continue
        try:
            text, decode_note = read_text(c["path"])
            rows, hdr = read_rows(text)
        except (OSError, csv.Error) as e:      # a broken file: its magazine (by the name) does without it
            if settled(c["pub"]):
                left.append(c)
            else:
                failed[c["pub"]].append({**c, "open": True, "problem": f"{c['name']} could not be read "
                                         f"({type(e).__name__}: {str(e)[:80]}) — the file is not used"})
            continue
        pub = links_pub(rows, hdr.get("link")) or c["pub"]
        if settled(pub):
            left.append({**c, "links": pub})
            continue
        if decode_note:
            warnings.append(decode_note)
        if c["date"] is None:
            warnings.append(f"{c['name']} has no date in its name — add the day it was exported, like "
                            f"{'aagrapevine' if pub == 'gv' else 'aalavina'}_archive_2026-11-05.csv, so a newer "
                            "file can be told from it")
        missing = [label for field, label in REQUIRED.items() if field not in hdr]
        before = (old_files[pub] or {}).get("rows")
        if missing:
            failed[pub].append({**c, "open": True, "problem": (
                f"{c['name']}: the column{'s' if len(missing) > 1 else ''} {', '.join(missing)} "
                f"{'are' if len(missing) > 1 else 'is'} missing — the file is not used")})
        elif ratio > 0 and isinstance(before, int) and len(rows) < ratio * before:
            failed[pub].append({**c, "open": False, "problem": (
                f"{c['name']} has {len(rows):,} rows, the file used before had {before:,} — it looks cut off, so the "
                "older data stays. If the smaller file is right, set writers_archive.min_rows_ratio: 0 in "
                "config/site.yml for one run")})
        else:
            if pub != c["pub"]:
                warnings.append(f"{c['name']}: the name says {PUB_NAME[c['pub']]} but its links are "
                                f"{PUB_NAME[pub]}'s — it is used as the {PUB_NAME[pub]} file")
            chosen[pub] = {**c, "text": text, "rows": rows, "hdr": hdr}

    misnamed: set[str] = set()       # magazines whose name the other magazine's export carries (said in its line)
    for c in left:
        named, links = c["pub"], c.get("links") or c["pub"]
        if links != named:           # the other magazine's export under this one's name — and that one has its file
            misnamed.add(named)
            other = (f"{PUB_NAME[links]} already has its file ({chosen[links]['name']})" if links in chosen
                     else f"{PUB_NAME[links]} keeps its older rows")
            own = (f"{PUB_NAME[named]} uses {chosen[named]['name']}" if named in chosen
                   else f"{PUB_NAME[named]} keeps the rows of its last file ({len(olds[named]):,} Texas writers)"
                   if olds[named] else f"there are no {PUB_NAME[named]} rows")
            warnings.append(f"{c['name']}: the name says {PUB_NAME[named]} but its links are {PUB_NAME[links]}'s, "
                            f"and {other} — this file is not used, and {own}; export {PUB_NAME[named]} again and "
                            "save it under this name")
        elif links not in chosen and failed[links] and (old_files[links] or {}).get("name") == c["name"]:
            # the file this magazine's rows on the site came from, while its newer one waits to be fixed
            warnings.append(f"older archive file still in {rel} (it stays in use until {failed[links][0]['name']} is "
                            f"fixed): {c['name']}")
        else:
            warnings.append(f"older archive file still in {rel} (it is not used and may be deleted): {c['name']}")

    def instead(p: str) -> str:
        """How the error of a file that is not used ends: what the site shows of its magazine instead."""
        if olds[p]:
            return ", the older rows stay"
        if p in chosen:
            return f", the older {chosen[p]['name']} is used instead"
        return f", and there are no older {PUB_NAME[p]} rows to keep"

    items: list[dict] = []
    files: dict[str, dict] = {}
    scopes: dict[str, str] = {}
    changed = False
    for pub in PUBS:
        old, old_file, c = olds[pub], old_files[pub], chosen.get(pub)
        errors += [f["problem"] + (instead(pub) if f["open"] else "") for f in failed[pub]]
        if c is None:
            if not failed[pub] and pub not in misnamed and (old or old_file):
                warnings.append(f"no {PUB_NAME[pub]} archive file in {rel} — the rows of the last one are kept "
                                f"({len(old):,} Texas writers)")
            items.extend(old)
            if old_file:
                files[pub] = old_file
            continue
        n_rows = len(c["rows"])
        sha = content_hash(c["text"])
        new_rows: list[dict] = []
        years: list[int] = []
        skipped = 0
        year_h = c["hdr"].get("year")
        for r in c["rows"]:
            y = str(r.get(year_h) or "").strip()
            if re.fullmatch(r"\d{4}", y):
                years.append(int(y))
            if not pub_of_url(clean_field(r.get(c["hdr"]["link"]))):
                skipped += 1
                continue
            it = row_item(r, c["hdr"], scopes)
            if it:
                new_rows.append(it)
        if skipped:
            warnings.append(f"{c['name']}: {skipped:,} row(s) without a Grapevine or La Viña link were left out")
        same = (same_parser and old_file is not None and old_file.get("name") == c["name"]
                and old_file.get("sha256") == sha)
        if not same:
            changed = True
            notes.append(f"New archive file used: {c['name']} ({n_rows:,} rows, {len(new_rows):,} Texas writers)")
        files[pub] = {"name": c["name"], "name_date": c["date"].isoformat() if c["date"] else None, "sha256": sha,
                      "rows": n_rows, "texas_rows": len(new_rows), "first_year": min(years) if years else None,
                      "imported_at": old_file.get("imported_at") if same and old_file.get("imported_at") else now}
        items.extend(new_rows)

    unique: dict[str, dict] = {}
    for it in items:                      # one row per address (the first)
        unique.setdefault(it["key"], it)
    # Each row keeps the time its address first came in (/status/ counts the stories found in the last 7 days):
    # from the last envelope, by address; a new address — this run. (A row saved before rows carried it: its file's
    # imported_at.)
    seen = {i["key"]: i.get("first_seen") or (old_files.get(i.get("pub")) or {}).get("imported_at")
            for i in prev_items}
    items = [{**it, "first_seen": seen.get(it["key"]) or now}
             for it in sort_rows(drop_content_duplicates(list(unique.values())))]
    for it in items:                      # rows kept from the last file: their scope, for the counts
        if it["key"] not in scopes:
            s = row_scope(it.get("writers") or [], it.get("pub") or "gv")
            scopes[it["key"]] = s if s in TEXAS_SCOPES else "texas"
    before_keys = {i["key"] for i in prev_items}
    stats = {
        "files": ", ".join(f["name"] for f in (files.get(p) for p in PUBS) if f and f.get("name")),
        "rows": sum(int(f.get("rows") or 0) for f in files.values()),
        "texas": len(items),
        "neta65": sum(1 for it in items if scopes.get(it["key"]) == "neta65"),
        "new": sum(1 for it in items if it["key"] not in before_keys),
        "changed": changed,
        "notes": notes,
        "warnings": warnings,
    }
    return {"items": items, "ok": not errors, "error": " · ".join(errors) or None, "stats": stats,
            "extra": {"parser_version": PARSER_VERSION, "files": {p: files[p] for p in PUBS if p in files}}}


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print what would be saved, do not write data/raw")
    a = ap.parse_args(argv)
    cfg = load_config()
    res = import_archive(archive_dir(cfg), cfg, load_raw(SOURCE))
    st = res["stats"]
    if a.dry_run:
        print(json.dumps({"ok": res["ok"], "error": res["error"], "stats": st, **res["extra"],
                          "items": res["items"][:3]}, ensure_ascii=False, indent=1, default=str))
        return
    save_raw(SOURCE, res["items"], ok=res["ok"], error=res["error"], stats=st, extra=res["extra"])
    log.info("%s: %d Texas writers (%d from Area 65) in %s rows of %s%s", SOURCE, st["texas"], st["neta65"],
             f"{st['rows']:,}", st["files"] or "no file", "" if res["ok"] else f" — {res['error']}")
    for w in st["warnings"]:
        log.warning("%s", w)


if __name__ == "__main__":
    raise SystemExit(run_module(SOURCE, main))
