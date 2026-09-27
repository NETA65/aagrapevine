"""Committee-written content that lives in the repository (edited on github.com):

  content/bulletin/*.md       → data/raw/announcements.json   (kind "announcement": the /bulletin/ page)
  content/events/*.md         → data/raw/manual_events.json   (kind "event")

(The bulletin was called "Announcements" until 2026-09: the data file, the kind and the item ids
"ann:…" kept that name, so nothing already on the site changes identity. A post saved in the old
content/announcements/ folder still shows; /status/ asks for it to be moved to content/bulletin/.)

Each file is Markdown with a small YAML header ("front matter"), e.g.

    ---
    title: Welcome, new GVRs and RLVs!
    date: 2027-01-10
    expires: 2027-03-31     # optional — hidden after this date
    pinned: false           # optional — keep at the top
    ---
    Write in English **or** Spanish — the site translates automatically.

A bulletin post needs no header at all: without `title:` the title is the first line when it is a
heading ("# Welcome"), else the first "# " heading, else the file name ("welcome-new-GVRs.md" →
"Welcome new GVRs"); without `date:` the date is the one the file name starts with
("2027-01-10-welcome.md"), else the day the post first appeared on the site. Simple HTML is turned
into Markdown (<b>, <i>, <a href>, <br>, <img>, headings, lists) and the rest of it is taken out —
scripts and styles with everything inside them. Pictures and documents (.jpg .jpeg .png .gif .webp
.pdf) saved next to the posts are published at /bulletin/files/ (eleventy.config.js), and a post's
links to them — ![Flyer](flyer.jpg), [the form](Sign-up form.pdf), `image: flyer.jpg` — are pointed
there.

Events use `title, start, end, location, url` (+ optional `online_url`, `flyer`, `image`).
Both may add the other language by hand — `title_es` / `summary_es` for a file written in English
(`title_en` / `summary_en` for one written in Spanish): build_data shows those words instead of a
machine translation (`extra.own_i18n`; the summary also stands in for the text below the header).
An event's place in the other language is `location_es` (`location_en`) — `own_i18n.location`; a
place is never machine-translated. `tentative: true` (also yes / sí) marks an event whose details
are not final yet (`extra.tentative`: a "Details to be confirmed" badge, STATUS:TENTATIVE in the
calendar feeds).
Files whose name starts with "_" or "README" are ignored; other files that do not end in .md
(any capitalization) are skipped and listed on /status/ — except a bulletin post's pictures and
documents. The folder is the source of truth:
deleting a file removes the item, and deleting a header line removes that value. A file with a
formatting mistake is reported on the /status/ page instead of breaking the daily update; if it
was already on the site, its last good version stays there until the mistake is fixed.

    python -m scripts.sync.announcements [--dry-run]
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote
from zoneinfo import ZoneInfo

import yaml

from .common import (CONTENT_DIR, clean_text, date_from_text, get_logger, load_config, load_raw, make_item,
                     merge_items, run_module, save_raw, slugify, sort_items, to_iso, truncate)
from .translate import detect_language

log = get_logger("announcements")

ANN_DIR = CONTENT_DIR / "bulletin"
# the folder's name until 2026-09: a post saved there by habit still shows, and /status/ asks for it
# to be moved (its pictures are published too: eleventy.config.js)
LEGACY_ANN_DIR = CONTENT_DIR / "announcements"
EVENTS_DIR = CONTENT_DIR / "events"
# The bulletin's own page, and where the pictures and documents saved next to its posts are
# published (eleventy.config.js copies content/bulletin/*.<ATTACH_EXT> there).
BULLETIN_URL = "/bulletin/"
ATTACH_URL = "/bulletin/files/"
ATTACH_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf")
# The header lines are optional ("---\n---\nbody" is a file with an empty header).
_FM = re.compile(r"\A\ufeff?---[ \t]*\r?\n(?:(.*?)\r?\n)?---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.S)
_FM_OPEN = re.compile(r"\A\ufeff?---[ \t]*(?:\r?\n|\Z)")
_KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:(?:[ \t]+(.*?))?[ \t]*$")
_QUOTE_HINT = ('if a value contains ": " (for example a title like "Reminder: Assembly"), '
               'put the whole value in quotes: title: "Reminder: Assembly"')


# --------------------------------------------------------------------------- parsing helpers
MD_SUFFIXES = (".md", ".markdown")


def _skipped_name(name: str) -> bool:
    """Help files and hidden files are never content: _template.md, README.md, .gitkeep …"""
    return name.startswith(("_", ".")) or name.upper().startswith("README")


def content_files(folder: Path) -> list[Path]:
    """The Markdown files of a content folder. The extension is matched case-insensitively
    ('Spring.MD' works) — the same on Windows and on the Linux machine of the daily update."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in MD_SUFFIXES and not _skipped_name(p.name))


def ignored_files(folder: Path, keep: tuple[str, ...] = ()) -> list[Path]:
    """Other files in a content folder (e.g. 'Assembly.txt'): not read, reported on /status/.
    `keep`: extensions that belong there all the same (the bulletin's pictures and documents)."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() not in MD_SUFFIXES + keep and not _skipped_name(p.name))


def read_text(path: Path) -> str:
    """A file's text. UTF-8 (with or without a BOM); a file saved by an old Windows editor
    (Windows-1252: "Viña" as one byte) is read too, instead of being turned away."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
        log.info("%s: not saved as UTF-8 — read as Windows-1252", path.name)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_front_matter(path: Path) -> tuple[dict, str]:
    """Return (front matter dict, Markdown body). Raises ValueError with a friendly message."""
    text = read_text(path)
    m = _FM.match(text)
    if not m:
        if _FM_OPEN.match(text):
            raise ValueError("the header has no closing --- line (add a line with just --- below the header)")
        return {}, text.strip()
    header = m.group(1) or ""
    try:
        meta = yaml.safe_load(header) or {}
    except yaml.YAMLError as e:
        meta = lenient_header(header)
        if meta is None:
            mark = getattr(e, "problem_mark", None)
            where = f" (line {mark.line + 2})" if mark else ""
            raise ValueError(f"the header between the --- lines is not valid{where}: "
                             f"{getattr(e, 'problem', e)} — {_QUOTE_HINT}")
        log.info("%s: header read line by line (a value contains ': ')", path.name)
    if not isinstance(meta, dict):
        raise ValueError("the header between the --- lines must be 'name: value' lines")
    return meta, m.group(2).strip()


def lenient_header(header: str) -> dict | None:
    """Read a header that is not valid YAML only because a value contains ': '
    ('title: Reminder: Assembly Saturday'). Every line must be 'name: value' (or a comment),
    otherwise None. A value is read like YAML when that gives a plain value (a date,
    true/false, a number, a [list]); anything else is kept exactly as written."""
    meta: dict = {}
    for line in header.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = _KEY_LINE.match(line)
        if not km:
            return None
        key, raw = km.group(1), (km.group(2) or "")
        if raw[:1] in ("\"", "'"):
            if len(raw) < 2 or raw[-1] != raw[0]:
                return None                          # an opening quote that is never closed
            meta[key] = raw[1:-1]
            continue
        raw = re.sub(r"\s+#.*$", "", raw).strip()   # a trailing '# comment', as in YAML
        try:
            val = yaml.safe_load(raw) if raw else None
        except yaml.YAMLError:
            val = raw
        meta[key] = raw if isinstance(val, dict) else val
    return meta


def markdown_to_text(md: str) -> str:
    """Plain-text teaser from Markdown (links → their label, formatting marks removed)."""
    t = re.sub(r"```.*?```", " ", md or "", flags=re.S)
    t = re.sub(r"(?m)^\s*\|.*$", " ", t)                            # tables (a teaser is prose)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)                     # images
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)                  # links → label
    t = re.sub(r"<(https?://[^>]+)>", r"\1", t)
    t = re.sub(r"(?m)^\s*(#{1,6}|>|[-*+]|\d+[.)])\s+", "", t)       # headings, quotes, bullets (nested too)
    t = re.sub(r"(?m)^\s*(?:[-*_]\s*){3,}$", " ", t)                # --- / *** lines
    t = re.sub(r"(\*\*|__|\*|_|~~|`)(?=\S)(.+?)(?<=\S)\1", r"\2", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return clean_text(t)


def as_date(v) -> str | None:
    """YAML date / 'YYYY-MM-DD' / 'March 5, 2027' → 'YYYY-MM-DD'."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return date.fromisoformat(s).isoformat()
        except ValueError:
            return None
    d, _ = date_from_text(s)
    return d


def as_when(v, tz: ZoneInfo) -> tuple[str | None, bool]:
    """Event start/end → (ISO UTC datetime 'Z' or 'YYYY-MM-DD', all_day)."""
    if v is None or v == "":
        return None, False
    if isinstance(v, datetime):
        dt = v if v.tzinfo else v.replace(tzinfo=tz)
        return to_iso(dt), False
    if isinstance(v, date):
        return v.isoformat(), True
    s = str(v).strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return date.fromisoformat(s).isoformat(), True
        dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T", 1))
        return to_iso(dt if dt.tzinfo else dt.replace(tzinfo=tz)), False
    except ValueError:
        pass
    try:  # "March 14, 2027 9:00 AM" — or only a date: "March 14, 2027", "03/14/2027"
        from dateutil import parser as dparser
        base = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        dt = dparser.parse(s, default=base)
        if dparser.parse(s, default=base.replace(hour=13)).hour != dt.hour:
            return dt.date().isoformat(), True   # no time was written → an all-day event
        return to_iso(dt if dt.tzinfo else dt.replace(tzinfo=tz)), False
    except Exception:
        d = as_date(s)
        return (d, True) if d else (None, False)


def as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v or "").strip().lower() in ("1", "true", "yes", "y", "si", "sí", "on")


def pick_lang(meta: dict, text: str) -> str:
    lang = str(meta.get("lang") or meta.get("language") or "").strip().lower()[:2]
    return lang if lang in ("en", "es") else detect_language(text, "en")


def as_tags(v) -> list[str]:
    if not v:
        return []
    if isinstance(v, str):
        v = re.split(r"[,;]", v)
    return [clean_text(t) for t in v if clean_text(t)]


def own_translations(meta: dict) -> dict[str, dict[str, str]]:
    """The author's own words in the other language → `extra.own_i18n` {field: {lang: text}}:
    `title_es` / `summary_es` (`title_en` / `summary_en` for a file written in Spanish). build_data uses
    them instead of a machine translation. The pages show the text below the header (`body_md`), not
    the summary, so the hand-written summary is that language's text as well. A value in the file's
    own language is ignored there (the header's `title` and the text are the originals)."""
    out: dict[str, dict[str, str]] = {}
    for lang in ("en", "es"):
        title, summary = clean_text(meta.get(f"title_{lang}")), clean_text(meta.get(f"summary_{lang}"))
        if title:
            out.setdefault("title", {})[lang] = title
        if summary:
            out.setdefault("summary", {})[lang] = truncate(summary, 400)
            out.setdefault("body_md", {})[lang] = summary
    return out


def city_state(location: str) -> tuple[str | None, str | None]:
    m = re.search(r"([A-Za-zÀ-ÿ .'-]+),\s*(TX|Texas|[A-Z]{2})\b", location or "")
    if not m:
        return None, None
    st = "TX" if m.group(2) in ("TX", "Texas") else m.group(2)
    return clean_text(m.group(1).split(",")[-1]), st


# --------------------------------------------------------------------------- bulletin posts
# A post is whatever Markdown the chair drops in the folder — often pasted from somewhere else, with
# or without a header. These helpers make any such file read well on the page (the page shows the
# title as a heading of its own and renders the text with markdown-it, raw HTML shown as text).

_ATX = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_ATX_H1 = re.compile(r"^ {0,3}#[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_SETEXT = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(```|~~~)")


def _heading_text(s: str) -> str:
    return clean_text(markdown_to_text(s))


def title_from_body(body: str) -> tuple[str, str]:
    """(title, the text without it) for a post without `title:`: its first line when that is a
    heading ("# Welcome", "### Welcome", or "Welcome" underlined with === / ---), else its first
    "# " heading (a flyer picture may come first) — ("", body) when it has neither."""
    lines = body.split("\n")
    first = next((k for k, line in enumerate(lines) if line.strip()), None)
    if first is None:
        return "", body
    m = _ATX.match(lines[first])
    if m:
        return _heading_text(m.group(2)), "\n".join(lines[:first] + lines[first + 1:]).strip()
    if (first + 1 < len(lines) and _SETEXT.match(lines[first + 1])
            and not re.match(r"^\s*([-*+>|]|\d+[.)])", lines[first])):
        return _heading_text(lines[first]), "\n".join(lines[:first] + lines[first + 2:]).strip()
    in_code = False
    for k, line in enumerate(lines):
        if _FENCE.match(line):
            in_code = not in_code
        elif not in_code and (m := _ATX_H1.match(line)):
            return _heading_text(m.group(1)), "\n".join(lines[:k] + lines[k + 1:]).strip()
    return "", body


def title_from_name(rest: str) -> str:
    """'welcome-new-GVRs' → 'Welcome new GVRs' (only the first letter is raised: GVR stays GVR)."""
    t = clean_text(re.sub(r"[-_]+", " ", rest))
    return t[:1].upper() + t[1:]


# HTML: markdown-it shows raw HTML as text (never a way to put a script on the page), so a post
# pasted from an e-mail or a web page would show its tags. The common ones become Markdown, the
# rest are taken out (their text stays), and scripts, styles and embeds go with all they hold.
# Only real HTML element names count: "<Panel 77>" or <https://…> stay as they were written, and so
# does anything inside `code`.
_HTML_NAMES = ("a|abbr|address|article|aside|audio|b|big|blockquote|body|br|button|caption|center|cite|code|col|"
               "colgroup|dd|del|details|dfn|div|dl|dt|em|embed|figcaption|figure|font|footer|form|h[1-6]|head|"
               "header|hr|html|i|iframe|img|input|ins|kbd|label|li|link|main|mark|meta|nav|noscript|object|ol|"
               "option|p|picture|pre|q|s|samp|script|section|select|small|source|span|strike|strong|style|sub|"
               "summary|sup|svg|table|tbody|td|template|textarea|tfoot|th|thead|title|tr|tt|u|ul|var|video")
_HTML_TAG = re.compile(rf"</?(?:{_HTML_NAMES})(?=[\s/>])[^<>]*>", re.I)
_HTML_HINT = re.compile(rf"<(?:!--|/?(?:{_HTML_NAMES})(?=[\s/>]))", re.I)
_HTML_DROP = re.compile(r"<(script|style|noscript|iframe|object|embed|svg|template|head|title|select|textarea|button)"
                        r"\b[^>]*>.*?</\1\s*>", re.I | re.S)


def _attr(tag: str, name: str) -> str:
    m = re.search(rf"""\b{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", tag, re.I)
    return html.unescape(next((g for g in m.groups() if g is not None), "")).strip() if m else ""


def _web_or_site(url: str) -> bool:
    """A web address (https://…, //…) or a page / file of the site (/events/)."""
    return bool(re.match(r"(?i)^(?:https?:)?//|^/(?![/\\])", url))


def _html_img(tag: str, dropped: list[str] | None) -> str:
    """<img> → ![alt](src) when the picture can show: a web address, a site path, or a picture or
    document saved next to the post (link_attachments points it there, or reports it missing).
    Anything else — an e-mail's inline picture (cid:…), data:, a bare "x" — never becomes a broken
    picture: its description stays in italics, and the update's report names it (status.json)."""
    src, alt = _attr(tag, "src"), clean_text(_attr(tag, "alt"))
    if not src:
        return ""
    if _web_or_site(src) or (not re.match(r"(?i)^[a-z][a-z0-9+.-]*:", src) and unquote(src.split("?")[0]).lower().endswith(ATTACH_EXT)):
        return f"![{alt}]({src})"
    if dropped is not None:
        name = re.sub(r"(?i)^cid:", "", src).split("@")[0].strip()
        dropped.append((name or src)[:80])
    return f"*{alt}*" if alt else ""


def _html_chunk(t: str, dropped: list[str] | None = None) -> str:
    """One stretch of a post outside code blocks (see tidy_html)."""
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = _HTML_DROP.sub("", t)
    t = re.sub(r"<img\b[^>]*>", lambda m: _html_img(m.group(0), dropped), t, flags=re.I)

    def link(m: re.Match) -> str:
        # a link keeps its address only when it is one a reader can follow (web, mail, phone, a page of
        # the site, an anchor, a file saved next to the post); "javascript:" and the like: the words only
        href, label = _attr(m.group(1), "href"), clean_text(m.group(2))
        if href and re.match(r"(?i)^[a-z][a-z0-9+.-]*:", href) and not re.match(r"(?i)^(?:https?|mailto|tel):", href):
            href = ""
        return f"[{label or href}]({href})" if href else label
    t = re.sub(r"(<a\b[^>]*>)(.*?)</a\s*>", link, t, flags=re.I | re.S)
    for tags, mark in (("b|strong", "**"), ("i|em", "*"), ("s|strike|del", "~~"), ("code|tt|kbd", "`")):
        t = re.sub(rf"<({tags})\b[^>]*>(.*?)</\1\s*>",
                   lambda m, k=mark: f"{k}{m.group(2).strip()}{k}" if m.group(2).strip() else "", t, flags=re.I | re.S)
    t = re.sub(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", lambda m: f"\n\n{'#' * int(m.group(1))} {clean_text(m.group(2))}\n\n",
               t, flags=re.I | re.S)
    # a line break inside a table row would end the row: there it is a space
    t = "\n".join(re.sub(r"<br\s*/?>", " " if line.lstrip().startswith("|") else "\n", line, flags=re.I)
                  for line in t.split("\n"))
    t = re.sub(r"<hr\b[^>]*>", "\n\n***\n\n", t, flags=re.I)
    t = re.sub(r"<li\b[^>]*>", "\n- ", t, flags=re.I)
    t = re.sub(r"</?(?:ul|ol|p|div|section|article|header|footer|main|nav|aside|blockquote|figure|figcaption|"
               r"table|thead|tbody|tfoot|tr|center|details|summary|dl|pre)\b[^>]*>", "\n\n", t, flags=re.I)
    t = re.sub(r"</?(?:td|th|dt|dd|caption)\b[^>]*>", " ", t, flags=re.I)
    return _HTML_TAG.sub("", t)


def tidy_html(md: str, dropped: list[str] | None = None) -> str:
    """A post's HTML → Markdown (see above). Fenced code blocks and `code` are left alone; a post
    with no HTML comes back exactly as it was. `dropped` collects the pictures that could not be kept
    (an e-mail's inline picture …: _html_img)."""
    if not _HTML_HINT.search(md or ""):
        return md or ""
    out, chunk, in_code = [], [], False

    def flush() -> None:
        if chunk:
            keep: list[str] = []
            text = re.sub(r"`[^`\n]+`", lambda m: f"\x00{keep.append(m.group(0)) or len(keep) - 1}\x00", "\n".join(chunk))
            text = re.sub("\x00(\\d+)\x00", lambda m: keep[int(m.group(1))], _html_chunk(text, dropped))
            out.append(text)
            chunk.clear()
    for line in md.split("\n"):
        if _FENCE.match(line):
            if not in_code:
                flush()
            in_code = not in_code
            out.append(line)
        elif in_code:
            out.append(line)
        else:
            chunk.append(line)
    flush()
    text = "\n".join(out)
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# Links to the pictures and documents saved next to the posts: ![Flyer](flyer.jpg),
# [the form](<Sign-up form.pdf>), [x][ref] … [ref]: flyer.pdf — any "](target)" or reference line.
_MD_TARGET = re.compile(r"\]\(\s*(<[^>\n]+>|[^)\n]*?)(\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)")
_MD_REFDEF = re.compile(r"(?m)^( {0,3}\[[^\]\n]+\]:[ \t]*)(<[^>\n]+>|\S+)")
# a whole picture (its words: group 1) or link (group 2), its target: group 3
_MD_IMG_LINK = re.compile(r"(?:!\[([^\]\n]*)\]|(?<!!)\[([^\]\n]+)\])\(\s*(<[^>\n]+>|[^)\n]*?)"
                          r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)")


def attachment_url(target: str, folder: Path) -> tuple[str | None, str | None]:
    """(site address, None) for a file of `folder` named by a relative link ('flyer.jpg',
    './Spring%20flyer.JPG'); (None, name) when it names a picture or document that is not there;
    (None, None) for anything else (a web address, a page of the site, an anchor)."""
    t = (target or "").strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1].strip()
    if not t or re.match(r"(?i)^(?:[a-z][a-z0-9+.-]*:|/|#|www\.)", t):
        return None, None
    name = re.sub(r"^(?:\./)+", "", unquote(re.split(r"[?#]", t)[0]).replace("\\", "/"))
    if "/" in name or not name.lower().endswith(ATTACH_EXT):
        return None, None
    for p in (folder.iterdir() if folder.is_dir() else ()):
        if p.is_file() and p.name.lower() == name.lower():
            return ATTACH_URL + quote(p.name), None
    return None, name


def link_attachments(body: str, folder: Path) -> tuple[str, list[str]]:
    """(the text with its links to files of `folder` pointed at ATTACH_URL, names it links to that are
    not in the folder). A picture or link whose file is missing becomes its own words (never a broken
    picture on the page); collect() reports the name (status.json). Code is left alone."""
    missing: list[str] = []

    def drop(m: re.Match) -> str:
        miss = attachment_url(m.group(3), folder)[1]
        if not miss:
            return m.group(0)
        missing.append(miss)
        if m.group(1) is not None:                      # a picture: its description, in italics
            return f"*{m.group(1).strip()}*" if m.group(1).strip() else ""
        return m.group(2)

    def fix(m: re.Match, g: int) -> str:
        url, miss = attachment_url(m.group(g), folder)
        if miss:
            missing.append(miss)
        return m.group(0) if not url else m.group(0)[:m.start(g) - m.start(0)] + url + m.group(0)[m.end(g) - m.start(0):]
    out, in_code = [], False
    for line in body.split("\n"):
        if _FENCE.match(line):
            in_code = not in_code
        elif not in_code and ("](" in line or _MD_REFDEF.match(line)):
            line = _MD_TARGET.sub(lambda m: fix(m, 1), _MD_IMG_LINK.sub(drop, line))
            line = _MD_REFDEF.sub(lambda m: fix(m, 2), line)
        out.append(line)
    return "\n".join(out), sorted(set(missing))


# --------------------------------------------------------------------------- builders
def parse_announcement(path: Path) -> dict:
    """A bulletin post (content/bulletin/<name>.md). The header is optional: see the module notes."""
    meta, body = read_front_matter(path)
    dropped: list[str] = []
    body = tidy_html(body, dropped)
    stem = path.stem
    file_date, rest = date_from_text(stem)
    title = clean_text(meta.get("title"))
    if _HTML_HINT.search(title):
        # a title pasted with its tags ("<b>Assembly</b>"): the page shows it as text, so the words only
        title = clean_text(markdown_to_text(tidy_html(title)))
    if title:
        # the text repeats the header's title as its first heading: shown once
        head, without = title_from_body(body)
        if head and head.casefold() == title.casefold() and _ATX.match(body.lstrip().split("\n", 1)[0]):
            body = without
    else:
        title, body = title_from_body(body)
        title = title or title_from_name(rest or stem)
    if not title:
        raise ValueError("it has no title (add a line 'title: …' to the header)")
    when = as_date(meta.get("date")) or file_date
    if meta.get("date") and not as_date(meta.get("date")):
        raise ValueError(f"the date '{meta.get('date')}' is not a date (use YYYY-MM-DD)")
    expires = as_date(meta.get("expires"))
    if meta.get("expires") and not expires:
        raise ValueError(f"the expires date '{meta.get('expires')}' is not a date (use YYYY-MM-DD)")
    body, missing = link_attachments(body, path.parent)
    missing += dropped
    slug = slugify(stem)
    text = markdown_to_text(body)
    summary = clean_text(meta.get("summary")) or text
    image = clean_text(meta.get("image")) or None
    if image:
        url, miss = attachment_url(image, path.parent)
        image = url or image
        missing += [miss] if miss else []
    link = clean_text(meta.get("url") or meta.get("link")) or None
    if link:
        url, miss = attachment_url(link, path.parent)
        link = url or link
        missing += [miss] if miss else []
    # the item's own address: its `url:`, unless that is a file saved next to it (then the post itself,
    # and the file is its "More information" button)
    item_url = link if link and not link.startswith(ATTACH_URL) else f"{BULLETIN_URL}#{slug}"
    extra = {"body_md": body, "expires": expires, "pinned": as_bool(meta.get("pinned")), "slug": slug,
             "file": f"content/{path.parent.name}/{path.name}", "link": link}
    if missing:
        extra["missing_files"] = sorted(set(missing))   # reported by collect() (status.json); the post still shows
    own = own_translations(meta)
    if own:
        extra["own_i18n"] = own
    return make_item(
        id=f"ann:{slug}", source="committee", kind="announcement", url=item_url,
        title=title, summary=truncate(summary, 400), lang=pick_lang(meta, f"{title}. {text}"), date=when,
        image=image, tags=as_tags(meta.get("tags")), category="manual", extra=extra,
    )


def parse_event(path: Path, tz: ZoneInfo) -> dict:
    meta, body = read_front_matter(path)
    stem = path.stem
    file_date, rest = date_from_text(stem)
    title = clean_text(meta.get("title")) or clean_text(re.sub(r"[-_]+", " ", rest or stem)).capitalize()
    start, all_day = as_when(meta.get("start") or meta.get("date"), tz)
    if not start and file_date:
        start, all_day = file_date, True
    if not start:
        raise ValueError("it has no start date (add a line 'start: 2027-03-14' or "
                         "'start: 2027-03-14T09:00:00-05:00' to the header)")
    end, _ = as_when(meta.get("end"), tz)
    location = clean_text(meta.get("location"))
    city, state = city_state(location)
    slug = slugify(stem)
    text = markdown_to_text(body)
    online = clean_text(meta.get("online_url") or meta.get("zoom")) or None
    flyer = clean_text(meta.get("flyer") or meta.get("flyer_url")) or None
    image = clean_text(meta.get("image") or meta.get("flyer_thumb")) or None
    extra = {"start": start, "end": end, "all_day": all_day, "location": location or None, "online_url": online,
             "flyer_url": flyer, "flyer_thumb": image, "city": city, "state": state, "body_md": body,
             "slug": slug, "file": f"content/events/{path.name}"}
    if as_bool(meta.get("tentative")):
        extra["tentative"] = True        # details not final yet: "Details to be confirmed", STATUS:TENTATIVE
    if as_bool(meta.get("confirmed")):
        extra["confirmed"] = True        # the committee checked date, time and place: no calendar feed changes them
    own = own_translations(meta)
    for lang in ("en", "es"):            # the place in the other language (never machine-translated)
        loc = clean_text(meta.get(f"location_{lang}"))
        if loc:
            own.setdefault("location", {})[lang] = loc
    if own:
        extra["own_i18n"] = own
    return make_item(
        id=f"ev:manual:{slug}", source="committee", kind="event",
        url=clean_text(meta.get("url")) or f"/events/#{slug}", title=title, summary=truncate(text, 400),
        lang=pick_lang(meta, f"{title}. {text}"), date=start, image=image, tags=as_tags(meta.get("tags")),
        category="manual", extra=extra,
    )


def collect(folder: Path, parser, label: str, keep: tuple[str, ...] = ()
            ) -> tuple[list[dict], list[str], set[str]]:
    """(items, problems, files that could not be read). The last are 'content/<folder>/<name>'
    paths, so finalize() can keep the version that was already on the site. `keep`: extensions of
    the other files that belong in the folder (the bulletin's pictures and documents)."""
    items, errors = [], []
    failed: set[str] = set()
    seen: set[str] = set()
    for path in content_files(folder):
        try:
            it = parser(path)
        except Exception as e:  # one bad file never blocks the others
            msg = f"{folder.name}/{path.name}: {e}"
            log.warning("skipped %s", msg)
            errors.append(msg[:400])
            failed.add(f"content/{folder.name}/{path.name}")
            continue
        if it["id"] in seen:
            errors.append(f"{folder.name}/{path.name}: duplicate name")
            continue
        seen.add(it["id"])
        items.append(it)
        # a link to a picture or document that is not in the folder: the post shows, the link is listed
        for name in (it.get("extra") or {}).pop("missing_files", None) or ():
            errors.append(f"{folder.name}/{path.name}: links to “{name}”, which is not in the folder "
                          f"(save it next to the post, with exactly that name)"[:400])
    for path in ignored_files(folder, keep):
        msg = (f"{folder.name}/{path.name}: ignored — only files ending in .md are read (rename it to end in .md)"
               + (f"; pictures and documents ({', '.join(keep)}) are published for the posts to link to" if keep else ""))
        log.warning("%s", msg)
        errors.append(msg[:240])
    log.info("%s: %d file(s), %d problem(s)", label, len(items), len(errors))
    return items, errors, failed


def finalize(prev: list[dict], new: list[dict], failed_files: set[str] | frozenset = frozenset()
             ) -> tuple[list[dict], int]:
    """The folder is the source of truth → drop items whose file was deleted, and take every field
    from today's file (a line removed from the header really disappears — authoritative merge; only
    first_seen is remembered). Items without a date get the day they first appeared on the site.

    A file that is still there but has a formatting mistake today keeps its last good version
    (and its first_seen) until it is fixed — a typo never makes a live announcement vanish."""
    merged, added = merge_items(prev, new, drop_missing=True, authoritative=True)
    have = {i["id"] for i in merged}
    for p in prev:
        if p.get("id") and p["id"] not in have and (p.get("extra") or {}).get("file") in failed_files:
            merged.append(p)
            have.add(p["id"])
    merged = sort_items(merged)
    for it in merged:
        if not it.get("date") and it.get("first_seen"):
            it["date"] = it["first_seen"][:10]
    return merged, added


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the items, do not write data/raw")
    a = ap.parse_args(argv)
    tz = ZoneInfo(load_config().get("site", {}).get("timezone", "America/Chicago"))

    anns, ann_err, ann_failed = collect(ANN_DIR, parse_announcement, "bulletin", keep=ATTACH_EXT)
    old, old_err, old_failed = collect(LEGACY_ANN_DIR, parse_announcement, "bulletin (old folder)", keep=ATTACH_EXT)
    have = {i["id"] for i in anns}
    for it in old:
        name = it["extra"]["file"].rsplit("/", 1)[-1]
        if it["id"] in have:
            ann_err.append(f"{LEGACY_ANN_DIR.name}/{name}: a post of the same name is in content/bulletin/ — this copy is left out")
            continue
        anns.append(it)
        ann_err.append(f"{LEGACY_ANN_DIR.name}/{name}: the folder is now content/bulletin/ — the post shows, but move it there")
    ann_err += old_err
    ann_failed |= old_failed
    events, ev_err, ev_failed = collect(EVENTS_DIR, lambda p: parse_event(p, tz), "events")

    if a.dry_run:
        print(json.dumps({"announcements": anns, "events": events, "errors": ann_err + ev_err},
                         ensure_ascii=False, indent=1, default=str))
        return

    today = datetime.now(timezone.utc).date().isoformat()
    ann_items, ann_new = finalize(load_raw("announcements").get("items", []), anns, ann_failed)
    save_raw("announcements", ann_items, ok=True, stats={
        "files": len(anns), "new": ann_new, "problems": len(ann_err), "errors": ann_err,
        "active": sum(1 for i in ann_items if not (i["extra"].get("expires") and i["extra"]["expires"] < today)),
    })
    ev_items, ev_new = finalize(load_raw("manual_events").get("items", []), events, ev_failed)
    save_raw("manual_events", ev_items, ok=True, stats={
        "files": len(events), "new": ev_new, "problems": len(ev_err), "errors": ev_err,
    })


if __name__ == "__main__":
    raise SystemExit(run_module("announcements", main))
