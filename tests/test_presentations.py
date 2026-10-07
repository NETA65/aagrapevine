"""The presentations (config/presentations/<id>.yml → /orientation/, "Presentations": three workshops and the
committee meeting): every deck file stays complete, safe and in line with AA's principles and the site's wording
rules.

The site build (src/_data/presentations.js, I18N_STRICT=1) stops on the same problems; these tests name the deck
and the slide without running the build. One file at a time (what the people writing a deck run):

    .venv\\Scripts\\python.exe tests\\test_presentations.py config\\presentations\\writing-workshop.yml
    python -m unittest tests.test_presentations -v              (every deck)
"""
from __future__ import annotations

import json
import math
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "config" / "presentations"
DECKS = ("orientation-workshop", "information-workshop", "writing-workshop", "committee-meeting")
# The phone numbers the site itself publishes (published_phones): a deck may show them
SITE_YML = ROOT / "config" / "site.yml"
AUDIO_PROJECT = ROOT / "data" / "site" / "audio_project.json"

ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY = re.compile(r"^[a-z][a-z0-9_]*$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TONES = {"gv", "lv", "vine", "grape"}
ACCENTS = {"gv", "lv", "vine", "grape", "navy"}
LANGS = {"en", "es"}
LIVE_KEYS = {
    "site", "site_url", "email", "panel", "as_of", "month", "year",
    "meeting_next", "meeting_day", "meeting_after", "meeting_month", "meeting_rule", "meeting_time", "meeting_zoom_id",
    "meeting_passcode", "meeting_phone", "meeting_phone_passcode",
    "lv_workshop_next", "lv_workshop_time", "lv_workshop_zoom_id",
    "price_gv_print", "price_gv_digital", "price_lv_print", "price_lv_digital", "price_change_note", "price_change_date",
    "gv_issue", "lv_issue", "gv_next_issue", "lv_next_issue", "gv_theme", "lv_theme", "next_deadline_gv", "next_deadline_lv",
    "botm", "botm_lv", "gv_audio_phone", "lv_audio_phone",
    "assembly_next", "gv_open_meeting", "lv_open_meeting", "open_meeting_zoom",
}
LIVE_KINDS = {
    "deadlines": {"pub", "limit", "limit_each"}, "events": {"limit", "filter", "series"}, "prices": {"pub"}, "meeting": {"limit"},
    "lv-workshop": {"limit"}, "issues": set(), "monthly": {"limit"}, "botm": set(), "bulletin": {"limit"},
    "qr": {"url", "caption"},
}
EVENT_FILTERS = ("all", "workshops", "neta", "calendar", "assemblies")
COMMON = {"id", "layout", "title", "eyebrow", "notes", "minutes", "optional", "starts_off", "facilitator", "handout",
          "accent", "source", "takeaway", "version_notes", "version_minutes", "version_fields", "show_from", "show_until",
          "when", "lang", "print", "allow_words"}
# The layouts with a `style`, and the styles each takes: columns as panels, cards or plain; a text slide as a
# read-aloud announcement card ("script") or a centred pause ("break").
STYLES = {"columns": ("panels", "cards", "plain"), "text": ("script", "break")}
# How a handout page prints (landscape unless it says portrait)
PRINTS = ("portrait", "landscape")
# {ui:<key>}: a control of the player, named in the page's language (Customize → Your details …)
UI_KEYS = ("customize", "version", "slides", "edit", "add", "your_details", "prepare", "save_share", "notes",
           "overview", "presenter_view", "print", "full_screen", "black_screen")
# What a version may NOT give its own value (version_fields): the build makes the slide's data from them, once for
# every version
VERSION_FIXED = {"kind", "options", "qr"}
LAYOUTS = {   # layout → (required fields, optional fields)
    "title": (set(), {"subtitle", "lines"}),
    "section": ({"number"}, {"subtitle"}),
    "bullets": ({"items"}, {"numbered", "checklist"}),
    # checklist: tick boxes in place of the columns' bullets (a printed checklist in two languages …)
    "columns": ({"columns"}, {"style", "checklist"}),
    "table": ({"rows"}, {"header", "widths", "first_col_bold"}),
    "agenda": ({"items"}, set()),
    "quote": ({"quote", "credit"}, set()),
    "activity": ({"steps", "duration"}, {"materials", "numbered"}),
    "qa": (set(), {"prompts", "note"}),
    "resources": ({"links"}, set()),
    "credits": ({"sources"}, {"disclaimer", "note"}),
    "closing": (set(), {"message", "lines", "qr"}),
    "text": ({"body"}, {"style"}),
    "flow": ({"steps"}, set()),
    "live": ({"kind"}, {"intro", "options"}),
}
# Visitor-facing wording rules (slides AND notes — anyone can open the notes). AA shares experience rather than
# teaching; GVR / RLV service is a "position"; the site never talks about how its data is gathered.
BANNED = re.compile(
    r"\b(pdfs?|crawl\w*|scrap(?:e|es|ed|ing|er|ers)|robots?|bots?|automatically|autom[aá]ticamente|lessons?|"
    r"lecci[oó]n(?:es)?|trainers?|training|quiz\w*|courses?|curso|curriculum|class(?:es)?|clases?|teach\w*|taught|"
    r"enseñ\w*|capacitaci[oó]n|jobs?)\b", re.I)
# Attraction rather than promotion: describe, never sell.
PUSHY = re.compile(r"(before (?:the )?prices? (?:go up|goes up|rise|rises|increase|increases|change|changes)|"
                   r"subscribe (?:now|today)|\bhurry\b|last chance|don'?t miss out|limited[- ]time|act now)", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}(?!\d)")
PHONE_OK = re.compile(r"^(?:\+?1[ .-]?)?\(?(?:800|888|877|866|855|844|833|212)\)?")   # toll-free; AA's New York offices
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@(?:aagrapevine\.org|aalavina\.org|aa\.org|neta65\.org)$", re.I)
TOKEN = re.compile(r"\{(fill|live|slide):([^}]*)\}")
BRACE = re.compile(r"\{[a-z_]+(?::[^}]*)?\}")
# Every token a text may hold: the three above, a span in another language {lang:es}…{/lang}, a control's name
# {ui:customize}, and — at the start of a line of the notes — the versions it is for {only:short} / {not:short}
TOKEN_KNOWN = re.compile(r"\{(?:fill|live|slide|lang|ui|only|not):[^}]*\}")
CLOSE_TAG = re.compile(r"\{/[a-z_]*\}")
LANG_TAG = re.compile(r"\{lang:([^}]*)\}|\{/lang\}")
UI_TAG = re.compile(r"\{ui:([^}]*)\}")
VERSION_TAG = re.compile(r"\{(only|not):([^}]*)\}")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
HTML = re.compile(r"<[A-Za-z/!]")


def url_ok(u: str) -> bool:
    return bool(re.match(r"^https://[^\s]+$", u) or re.match(r"^/(?!/)[^\s]*$", u) or EMAIL.fullmatch(u)
                or re.match(r"^mailto:[^\s]+$", u))


def is_int(v) -> bool:
    """A whole number — never true / false (YAML's yes / no), which Python counts as 1 / 0."""
    return isinstance(v, int) and not isinstance(v, bool)


def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def minutes_ok(v) -> bool:
    """A slide's minutes: "about N minutes" as a number (0.25 … 30; 1¼ → 1.25, 30 seconds → 0.5)."""
    return is_num(v) and 0 < v <= 30


def phone_digits(s: str) -> str:
    """A U.S. number's ten digits, however it is written: "+1 346 248 7799" and "(346) 248-7799" → "3462487799"."""
    d = re.sub(r"\D", "", s)
    return d[1:] if len(d) == 11 and d.startswith("1") else d


_PUBLISHED: set[str] | None = None


def published_phones() -> set[str]:
    """The phone numbers the site itself publishes — every number in config/site.yml (Zoom's dial-in numbers, AA
    Grapevine's customer service …) and the magazines' story lines (data/site/audio_project.json gv / lv `phone`) —
    as ten digits. Nobody's personal number: a deck may show them (better: {live:meeting_phone},
    {live:gv_audio_phone}, {live:lv_audio_phone}, which follow the site when a number changes)."""
    global _PUBLISHED
    if _PUBLISHED is None:
        found: set[str] = set()
        try:
            cfg = yaml.safe_load(SITE_YML.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            cfg = None
        for _, text in strings(cfg):
            found.update(phone_digits(m.group(0)) for m in PHONE.finditer(text))
        try:
            audio = json.loads(AUDIO_PROJECT.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            audio = None
        for pub in ("gv", "lv"):
            line = audio.get(pub) if isinstance(audio, dict) else None
            phone = line.get("phone") if isinstance(line, dict) else None
            if isinstance(phone, str) and len(phone_digits(phone)) == 10:
                found.add(phone_digits(phone))
        _PUBLISHED = found
    return _PUBLISHED


def slide_minutes(s: dict, version) -> float:
    """A slide's minutes in a version: its `version_minutes` for that version, else its `minutes` (0 without either)."""
    vm = s.get("version_minutes")
    for v in (vm.get(version) if isinstance(vm, dict) and isinstance(version, str) else None, s.get("minutes")):
        if is_num(v):
            return float(v)
    return 0.0


def pair(v, where: str, out: list[str]) -> None:
    if not isinstance(v, dict) or not all(isinstance(v.get(k), str) and v[k].strip() for k in ("en", "es")):
        out.append(f"{where}: needs an English AND a Spanish text {{en: …, es: …}}")


def strings(node, path: str = ""):
    """(path, text) for every string under a node."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, f"{path}[{i}]")


def check_items(items, where: str, out: list[str], depth: int = 0) -> None:
    if not isinstance(items, list) or not items:
        out.append(f"{where}: needs a list with at least one item")
        return
    for i, it in enumerate(items):
        if isinstance(it, str):
            if not it.strip():
                out.append(f"{where}[{i}]: empty item")
        elif isinstance(it, dict) and depth == 0:
            if set(it) - {"text", "items"} or not isinstance(it.get("text"), str) or not it["text"].strip():
                out.append(f"{where}[{i}]: an item is a string or {{text: …, items: […]}}")
            if "items" in it:
                check_items(it["items"], f"{where}[{i}].items", out, depth + 1)
        else:
            out.append(f"{where}[{i}]: an item is a string" + (" (one level of sub-items only)" if depth else ""))


def changeable_fields(layout) -> set[str]:
    """The fields a version may give its own value on a slide of `layout` (version_fields): its title, eyebrow, source
    and takeaway, and the layout's own fields — not the ones the build makes the slide's data from."""
    req, opt = LAYOUTS.get(layout, (set(), set()))
    return ({"title", "eyebrow", "source", "takeaway"} | req | opt) - VERSION_FIXED


def lang_problems(text: str, pre: str, out: list[str]) -> None:
    """{lang:es}…{/lang} spans of one text (`pre` names it): "en" or "es", opened and closed on the same line, one at
    a time — the player marks each span with its language (a notes line, a paragraph or a few words)."""
    for line in text.split("\n"):
        open_ = None
        for m in LANG_TAG.finditer(line):
            if m.group(0) == "{/lang}":
                if open_ is None:
                    out.append(f"{pre}: {{/lang}} without its {{lang:…}}")
                open_ = None
                continue
            if m.group(1) not in LANGS:
                out.append(f'{pre}: {{lang:{m.group(1)}}} — the language is "en" or "es"')
            if open_ is not None:
                out.append(f"{pre}: a {{lang:…}} inside another one (close the first with {{/lang}})")
            open_ = m.group(1)
        if open_ is not None:
            out.append(f"{pre}: {{lang:{open_}}} without its {{/lang}} on the same line")


def field_problems(s: dict, layout: str, w: str, idset: set) -> list[str]:
    """The rules of a slide's own fields — its title, its texts, its layout's fields — as lines that start with `w`
    ("slide 12 (agenda)"). Run on the slide, and on the slide as each version shows it (version_fields)."""
    out: list[str] = []
    if not isinstance(s.get("title"), str) or not s["title"].strip():
        out.append(f"{w}: title required")
    for k in ("eyebrow", "source", "takeaway", "subtitle", "quote", "credit", "note", "message", "body", "intro"):
        if k in s and (not isinstance(s[k], str) or not s[k].strip()):
            out.append(f"{w}: {k} must be a non-empty string")
    if layout in STYLES and "style" in s and s["style"] not in STYLES[layout]:
        out.append(f"{w}: style {' | '.join(STYLES[layout])}")
    if layout == "title" and "lines" in s and (not isinstance(s["lines"], list)
                                                or not all(isinstance(x, str) for x in s["lines"])):
        out.append(f"{w}: lines — a list of strings")
    if layout == "section" and not (is_int(s.get("number")) or isinstance(s.get("number"), str)):
        out.append(f"{w}: number")
    if layout == "bullets":
        check_items(s.get("items"), f"{w}.items", out)
    if layout == "columns":
        cols = s.get("columns")
        if not isinstance(cols, list) or not 2 <= len(cols) <= 4:
            out.append(f"{w}: columns — 2 to 4")
        else:
            for j, c in enumerate(cols):
                if not isinstance(c, dict) or set(c) - {"heading", "gloss", "text", "items", "accent", "link"}:
                    out.append(f"{w}.columns[{j}]: {{heading, gloss, text | items, accent}}")
                    continue
                if ("text" in c) == ("items" in c):
                    out.append(f"{w}.columns[{j}]: text OR items")
                if "items" in c:
                    check_items(c["items"], f"{w}.columns[{j}].items", out)
                if "accent" in c and c["accent"] not in ACCENTS:
                    out.append(f"{w}.columns[{j}]: accent one of {sorted(ACCENTS)}")
    if layout == "table":
        rows, header = s.get("rows"), s.get("header")
        if not isinstance(rows, list) or not rows or not all(isinstance(r, list) and r for r in rows):
            out.append(f"{w}: rows — a list of rows (lists)")
        else:
            n = len(header) if isinstance(header, list) else len(rows[0])
            if header is not None and (not isinstance(header, list) or not all(isinstance(x, str) for x in header)):
                out.append(f"{w}: header — a list of strings")
            for j, r in enumerate(rows):
                if len(r) != n or not all(isinstance(x, (str, int, float)) for x in r):
                    out.append(f"{w}.rows[{j}]: {n} cells (text)")
            if "widths" in s and (not isinstance(s["widths"], list) or len(s["widths"]) != n
                                  or not all(isinstance(x, (int, float)) and x > 0 for x in s["widths"])):
                out.append(f"{w}: widths — {n} positive numbers")
    if layout == "agenda":
        items = s.get("items")
        if not isinstance(items, list) or not items:
            out.append(f"{w}: items")
        else:
            for j, it in enumerate(items):
                if not isinstance(it, dict) or set(it) - {"time", "title", "detail", "from"} \
                        or not isinstance(it.get("title"), str) or not isinstance(it.get("time"), str):
                    out.append(f"{w}.items[{j}]: {{time: \"0:08\", title, detail, from}}")
                elif "from" in it and it["from"] not in idset:
                    out.append(f"{w}.items[{j}]: from — no slide {it['from']!r}")
    if layout == "activity":
        check_items(s.get("steps"), f"{w}.steps", out)
        dur = s.get("duration")
        if not isinstance(dur, (int, float)) or isinstance(dur, bool) or dur <= 0:
            out.append(f"{w}: duration (the time card's minutes)")
        mat = s.get("materials")
        if mat is not None and not (isinstance(mat, str) or (isinstance(mat, list) and all(isinstance(x, str) for x in mat))):
            out.append(f"{w}: materials — text or a list")
    if layout == "qa" and "prompts" in s:
        check_items(s["prompts"], f"{w}.prompts", out)
    if layout == "resources":
        links = s.get("links")
        if not isinstance(links, list) or not links:
            out.append(f"{w}: links")
        else:
            for j, k in enumerate(links):
                if not isinstance(k, dict) or set(k) - {"label", "url", "note"} or not isinstance(k.get("label"), str):
                    out.append(f"{w}.links[{j}]: {{label, url, note}}")
                elif not isinstance(k.get("url"), str) or not url_ok(k["url"]):
                    out.append(f"{w}.links[{j}]: url {k.get('url')!r} — https://…, a site path /… or an e-mail")
    if layout == "credits":
        src = s.get("sources")
        if not isinstance(src, list) or not src or not all(isinstance(x, str) and x.strip() for x in src):
            out.append(f"{w}: sources — a list of strings")
    if layout == "closing":
        if "lines" in s and (not isinstance(s["lines"], list) or not all(isinstance(x, str) for x in s["lines"])):
            out.append(f"{w}: lines — a list of strings")
        if "qr" in s and (not isinstance(s["qr"], str) or not url_ok(s["qr"]) or EMAIL.fullmatch(s["qr"])):
            out.append(f"{w}: qr — a site path or an https:// address")
    if layout == "flow":
        steps = s.get("steps")
        if not isinstance(steps, list) or not 2 <= len(steps) <= 6:
            out.append(f"{w}: steps — 2 to 6")
        else:
            for j, st in enumerate(steps):
                if not isinstance(st, dict) or set(st) - {"title", "text"} or not isinstance(st.get("title"), str):
                    out.append(f"{w}.steps[{j}]: {{title, text}}")
    if layout == "live":
        kind = s.get("kind")
        if kind not in LIVE_KINDS:
            out.append(f"{w}: kind one of {sorted(LIVE_KINDS)}")
        else:
            opts = s.get("options", {})
            if not isinstance(opts, dict):
                out.append(f"{w}: options — a mapping")
            else:
                for k in opts:
                    if k not in LIVE_KINDS[kind]:
                        out.append(f"{w}: option {k!r} is not used by {kind!r} ({sorted(LIVE_KINDS[kind])})")
                if "limit" in opts and (not is_int(opts["limit"]) or not 1 <= opts["limit"] <= 24):
                    out.append(f"{w}: options.limit 1–24")
                # deadlines of both magazines: this many of EACH (3 + 3), within `limit`
                if "limit_each" in opts and (not is_int(opts["limit_each"]) or not 1 <= opts["limit_each"] <= 12):
                    out.append(f"{w}: options.limit_each 1–12 (rows of each magazine)")
                if "pub" in opts and opts["pub"] not in ("gv", "lv", "both"):
                    out.append(f"{w}: options.pub gv | lv | both")
                if "filter" in opts and opts["filter"] not in EVENT_FILTERS:
                    out.append(f"{w}: options.filter {' | '.join(EVENT_FILTERS)}")
                if "series" in opts and opts["series"] != "all":
                    out.append(f'{w}: options.series "all" (every date of a monthly series; default: once)')
                if kind == "qr" and (not isinstance(opts.get("url"), str) or not url_ok(opts["url"])):
                    out.append(f"{w}: options.url (a site path or https://) for the QR code")
    return out


def check_deck(path: Path) -> list[str]:
    """Every problem in one deck file, as readable lines (empty = fine)."""
    out: list[str] = []
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"{path.name}: not valid YAML: {e}"]
    if not isinstance(d, dict):
        return [f"{path.name}: the file must be a mapping"]
    allowed_top = {"id", "order", "lang", "title", "short", "eyebrow", "footer", "minutes", "icon", "tone",
                   "drive_title", "card", "presets", "fillins", "slides"}
    for k in d:
        if k not in allowed_top:
            out.append(f"unknown top-level field {k!r}")
    if d.get("id") != path.stem:
        out.append(f"id {d.get('id')!r} must be the file name {path.stem!r}")
    if not is_int(d.get("order")) or not 1 <= d["order"] <= 9:
        out.append("order: a whole number 1–9")
    if d.get("lang") != "en":
        out.append('lang: "en" (the content stays English — the owner\'s decision)')
    for k in ("title", "short", "eyebrow", "footer", "icon"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            out.append(f"{k}: a non-empty string")
    if not is_int(d.get("minutes")) or not 5 <= d["minutes"] <= 240:
        out.append("minutes: a whole number 5–240")
    if d.get("tone") not in TONES:
        out.append(f"tone: one of {sorted(TONES)}")
    if "drive_title" in d and (not isinstance(d["drive_title"], str) or not d["drive_title"].strip()):
        out.append("drive_title: a string")
    icon = d.get("icon")
    if isinstance(icon, str) and (ROOT / "node_modules" / "lucide-static").exists():
        if not ((ROOT / "node_modules" / "lucide-static" / "icons" / f"{icon}.svg").exists()
                or (ROOT / "src" / "_includes" / "icons" / f"{icon}.svg").exists()):
            out.append(f"icon {icon!r}: no such lucide icon")
    card = d.get("card") if isinstance(d.get("card"), dict) else {}
    for k in ("title", "summary", "audience"):
        pair(card.get(k), f"card.{k}", out)

    slides = d.get("slides")
    if not isinstance(slides, list) or len(slides) < 5:
        return out + ["slides: a list of at least 5 slides"]
    ids: list[str] = []
    for i, s in enumerate(slides):
        sid = s.get("id") if isinstance(s, dict) else None
        if not isinstance(sid, str) or not ID.match(sid):
            out.append(f"slide {i + 1}: id {sid!r} must be lowercase letters, digits and dashes")
        elif sid in ids:
            out.append(f"slide {i + 1}: duplicate id {sid!r}")
        ids.append(sid if isinstance(sid, str) else f"#{i + 1}")
    idset = set(ids)
    by_id = {s.get("id"): s for s in slides if isinstance(s, dict)}

    # presenter blanks
    fill_keys: dict[str, bool] = {}
    fills = d.get("fillins") if isinstance(d.get("fillins"), list) else []
    if "fillins" in d and not isinstance(d["fillins"], list):
        out.append("fillins: a list")
    for j, f in enumerate(fills):
        w = f"fillins[{j}]"
        if not isinstance(f, dict):
            out.append(f"{w}: a mapping")
            continue
        for k in f:
            if k not in {"key", "label", "hint", "default", "shared", "notes_only"}:
                out.append(f"{w}: unknown field {k!r}")
        key = f.get("key")
        if not isinstance(key, str) or not KEY.match(key):
            out.append(f"{w}: key {key!r} must be lowercase letters, digits and _")
        elif key in fill_keys:
            out.append(f"{w}: duplicate key {key!r}")
        else:
            fill_keys[key] = bool(f.get("notes_only"))
        pair(f.get("label"), f"{w}.label", out)
        if not isinstance(f.get("hint"), str) or not f["hint"].strip():
            out.append(f"{w}: hint (what an empty blank shows) is required")
        for k in ("default",):
            if k in f and not isinstance(f[k], str):
                out.append(f"{w}.{k}: a string")
        for k in ("shared", "notes_only"):
            if k in f and not isinstance(f[k], bool):
                out.append(f"{w}.{k}: true or false")

    # versions
    presets = d.get("presets")
    preset_ids: list[str] = []
    if not isinstance(presets, list) or not presets:
        out.append("presets: at least one (the first is the full version)")
        presets = []
    for j, p in enumerate(presets):
        w = f"presets[{j}]"
        if not isinstance(p, dict):
            out.append(f"{w}: a mapping")
            continue
        for k in p:
            if k not in {"id", "label", "minutes", "hide", "only", "note"}:
                out.append(f"{w}: unknown field {k!r}")
        pid = p.get("id")
        if not isinstance(pid, str) or not ID.match(pid) or pid in preset_ids:
            out.append(f"{w}: id {pid!r} must be unique, lowercase letters, digits and dashes")
        preset_ids.append(pid)
        pair(p.get("label"), f"{w}.label", out)
        if "note" in p:
            pair(p.get("note"), f"{w}.note", out)
        if not is_int(p.get("minutes")) or not 1 <= p["minutes"] <= 240:
            out.append(f"{w}: minutes, a whole number")
        if "hide" in p and "only" in p:
            out.append(f"{w}: hide OR only, not both")
        if j == 0 and ("hide" in p or "only" in p):
            out.append(f"{w}: the first version is the full one (no hide / only)")
        for k in ("hide", "only"):
            if k in p:
                if not isinstance(p[k], list) or not p[k]:
                    out.append(f"{w}.{k}: a list of slide ids")
                    continue
                for x in p[k]:
                    if x not in idset:
                        out.append(f"{w}.{k}: no slide {x!r}")
                    elif by_id[x].get("facilitator"):
                        out.append(f"{w}.{k}: {x!r} is a facilitator slide (never in the show)")

    # slides
    has_disclaimer = False
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            out.append(f"slide {i + 1}: a mapping")
            continue
        sid = s.get("id")
        w = f"slide {i + 1} ({sid})"
        layout = s.get("layout")
        if layout not in LAYOUTS:
            out.append(f"{w}: layout {layout!r} is not one of {sorted(LAYOUTS)}")
            continue
        req, opt = LAYOUTS[layout]
        for k in s:
            if k not in COMMON | req | opt:
                out.append(f"{w}: unknown field {k!r} for layout {layout!r}")
        for k in req:
            if k not in s:
                out.append(f"{w}: {layout!r} needs {k!r}")
        fac = s.get("facilitator") is True
        for k in ("optional", "starts_off", "facilitator", "handout", "numbered", "checklist", "first_col_bold",
                  "disclaimer"):
            if k in s and not isinstance(s[k], bool):
                out.append(f"{w}: {k} must be true or false")
        # (`handout`: printed for the participants — a facilitator page, or a slide that is shown AND printed)
        if fac and (s.get("optional") or s.get("starts_off")):
            out.append(f"{w}: a facilitator slide is never in the show (no optional / starts_off)")
        notes = s.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            out.append(f"{w}: notes required")
        else:
            if not fac and len(notes.split()) < 25:
                out.append(f"{w}: notes look thin (< 25 words): say what to SAY, DO and ASK")
            if re.search(r"(?m)^\s*TIME:", notes):
                out.append(f"{w}: no TIME: line in the notes — give `minutes:` (the player writes the TIME line)")
            if re.search(r"(?i)\b(right-click|hide slide|this file|powerpoint|\.pptx)\b", notes) and not fac:
                out.append(f"{w}: notes still talk about PowerPoint (hidden slides, this file …) — say what to do "
                           f"in the web player (Customize → …)")
        m = s.get("minutes")
        if fac:
            if m not in (None, 0):
                out.append(f"{w}: a facilitator slide has no minutes")
        elif not minutes_ok(m):
            out.append(f"{w}: minutes (0.25–30) required")
        # any slide: on a section slide the colour of its part (the slides after it take it), else this slide's own
        if "accent" in s and s["accent"] not in ACCENTS:
            out.append(f"{w}: accent one of {sorted(ACCENTS)}")
        # a slide written in Spanish (a handout, an announcement to read): the player marks it lang="es"
        if "lang" in s and s["lang"] not in LANGS:
            out.append(f'{w}: lang is "en" or "es" (the language the slide is written in)')
        # a handout page prints landscape, unless it says portrait
        if "print" in s:
            if s["print"] not in PRINTS:
                out.append(f'{w}: print is "portrait" or "landscape"')
            elif s.get("handout") is not True:
                out.append(f"{w}: print is for a handout page (handout: true)")
        if "version_notes" in s:
            vn = s["version_notes"]
            if not isinstance(vn, dict) or not vn:
                out.append(f"{w}: version_notes {{<version id>: text}}")
            else:
                for k, v in vn.items():
                    if k not in preset_ids:
                        out.append(f"{w}: version_notes for an unknown version {k!r}")
                    if not isinstance(v, str) or not v.strip():
                        out.append(f"{w}: version_notes.{k} must be text")
        # this slide's minutes in a version (its schedule, TIME lines and the sums below use them)
        if "version_minutes" in s:
            vm = s["version_minutes"]
            if not isinstance(vm, dict) or not vm:
                out.append(f"{w}: version_minutes {{<version id>: minutes}}")
            else:
                for k, v in vm.items():
                    if k not in preset_ids:
                        out.append(f"{w}: version_minutes for an unknown version {k!r}")
                    if not minutes_ok(v):
                        out.append(f"{w}: version_minutes.{k} must be minutes (0.25–30)")
        for k in ("show_from", "show_until"):
            if k in s and (not isinstance(s[k], str) or not DAY.match(s[k])):
                out.append(f'{w}: {k} must be a quoted "YYYY-MM-DD"')
        if isinstance(s.get("show_from"), str) and isinstance(s.get("show_until"), str) and s["show_from"] > s["show_until"]:
            out.append(f"{w}: show_from is after show_until")
        if "when" in s and s["when"] != "price_notice":
            out.append(f'{w}: when: "price_notice" is the only condition')

        # the slide's own fields (its title, its texts, its layout's fields)
        own = field_problems(s, layout, w, idset)
        out.extend(own)
        # a version's own value for some of them (an agenda's title, an activity's duration …): only a field of the
        # layout, and the slide as that version shows it keeps every rule (only what is new there is named)
        if "version_fields" in s:
            vf = s["version_fields"]
            if not isinstance(vf, dict) or not vf:
                out.append(f"{w}: version_fields {{<version id>: {{<field>: value}}}}")
            else:
                changeable = changeable_fields(layout)
                seen = set(own)
                for k, v in vf.items():
                    if k not in preset_ids:
                        out.append(f"{w}: version_fields for an unknown version {k!r}")
                    if not isinstance(v, dict) or not v:
                        out.append(f"{w}: version_fields.{k} {{<field>: value}}")
                        continue
                    for f in v:
                        if f not in changeable:
                            out.append(f"{w}: version_fields.{k}: {f!r} is not a field a version can change on a {layout!r} slide")
                    pre = f"{w} version_fields.{k}"
                    shown = {**s, **{f: x for f, x in v.items() if f in changeable}}
                    for line in field_problems(shown, layout, pre, idset):
                        if w + line[len(pre):] not in seen:
                            out.append(line)

        # every text of the slide: tokens, links, wording, privacy
        allow = s.get("allow_words") or []
        if not isinstance(allow, list) or not all(isinstance(x, str) for x in allow):
            out.append(f"{w}: allow_words — a list of words")
            allow = []
        allow_l = {x.lower() for x in allow}
        used_allow: set[str] = set()
        for where, text in strings({k: v for k, v in s.items() if k not in ("id", "layout", "accent", "when", "lang", "print",
                                                                           "show_from", "show_until", "allow_words")}):
            if re.search(r"not an official aa grapevine", text, re.I):
                has_disclaimer = True
            # (a version's own quote or sources are as verbatim as the slide's: "version_fields.short.quote" → "quote")
            field = ".".join(where.split(".")[2:]) if where.startswith("version_fields.") else where
            exempt = (layout == "quote" and field == "quote") or (layout == "credits" and field.startswith("sources"))
            for m in TOKEN.finditer(text):
                kind, key = m.group(1), m.group(2)
                if kind == "fill":
                    if key not in fill_keys:
                        out.append(f"{w} {where}: {{fill:{key}}} is not in fillins")
                    elif fill_keys[key] and not where.startswith(("notes", "version_notes")):
                        out.append(f"{w} {where}: {{fill:{key}}} is notes_only (never on a slide)")
                elif kind == "live" and key not in LIVE_KEYS:
                    out.append(f"{w} {where}: unknown {{live:{key}}}")
                elif kind == "slide" and key not in idset:
                    out.append(f"{w} {where}: {{slide:{key}}} — no such slide")
            for m in BRACE.finditer(text):
                if not TOKEN_KNOWN.fullmatch(m.group(0)):
                    out.append(f"{w} {where}: unknown placeholder {m.group(0)}")
            for m in CLOSE_TAG.finditer(text):
                if m.group(0) != "{/lang}":
                    out.append(f"{w} {where}: unknown placeholder {m.group(0)}")
            lang_problems(text, f"{w} {where}", out)
            for m in UI_TAG.finditer(text):
                if m.group(1) not in UI_KEYS:
                    out.append(f"{w} {where}: unknown {{ui:{m.group(1)}}} — a control of the player: {', '.join(UI_KEYS)}")
            # {only:short,visit} / {not:short}: a line of the notes for some versions only (a TRANSITION to a slide
            # another version leaves out …) — at the start of the line, naming versions of the deck
            for m in VERSION_TAG.finditer(text):
                tag, kind, ids = m.group(0), m.group(1), [x.strip() for x in m.group(2).split(",")]
                if where != "notes" or text[text.rfind("\n", 0, m.start()) + 1:m.start()].strip():
                    out.append(f"{w} {where}: {{{kind}:…}} goes at the start of a line of the notes")
                    continue
                if not any(ids):
                    out.append(f"{w} {where}: {tag} names no version")
                for x in ids:
                    if x and x not in preset_ids:
                        out.append(f"{w} {where}: {tag} — no version {x!r}")
            for m in LINK.finditer(text):
                if not url_ok(m.group(2)):
                    out.append(f"{w} {where}: link {m.group(2)!r} — https://…, a site path or an e-mail")
            if HTML.search(text):
                out.append(f"{w} {where}: no HTML in the text (use **bold**, _italic_, [label](url))")
            if not exempt:
                for m in BANNED.finditer(text):
                    word = m.group(0).lower()
                    if word in allow_l:
                        used_allow.add(word)
                        continue
                    out.append(f"{w} {where}: the word {m.group(0)!r} breaks the site's wording rules "
                               f"(…{text[max(0, m.start() - 40):m.end() + 40]}…)")
                if PUSHY.search(text):
                    out.append(f"{w} {where}: sounds like selling ({PUSHY.search(text).group(0)!r}) — describe, never sell")
            for m in PHONE.finditer(text):
                if not PHONE_OK.match(m.group(0)) and phone_digits(m.group(0)) not in published_phones():
                    out.append(f"{w} {where}: a personal-looking phone number {m.group(0)!r} (a Zoom meeting ID? "
                               f"write {{live:meeting_zoom_id}} / {{live:lv_workshop_zoom_id}}; the site's own numbers: "
                               f"{{live:meeting_phone}}, {{live:gv_audio_phone}}, {{live:lv_audio_phone}})")
            for m in EMAIL.finditer(text):
                if not EMAIL_OK.search(m.group(0)):
                    out.append(f"{w} {where}: e-mail {m.group(0)!r} — only service addresses (aagrapevine.org, "
                               f"aalavina.org, aa.org, neta65.org)")
        for word in allow_l - used_allow:
            out.append(f"{w}: allow_words {word!r} is not used on this slide (remove it)")
        if layout == "quote" and isinstance(s.get("credit"), str) and not s["credit"].strip():
            out.append(f"{w}: a quote needs its credit line")

    if not has_disclaimer:
        out.append('no slide says "Not an official AA Grapevine, Inc. presentation" (keep it, as in the deck)')

    # lengths: the full version ≈ the deck's minutes, each version ≈ its own — a slide counts with its
    # version_minutes for that version, else its minutes; a version's `only` shows its slides even when they
    # start off. (Sums are rounded half up, as the build's twin does.)
    def total(shown: list[dict], version) -> float:
        return sum(slide_minutes(x, version) for x in shown)
    full = presets[0].get("id") if presets and isinstance(presets[0], dict) else None
    base = [x for x in slides if isinstance(x, dict) and not x.get("facilitator") and not x.get("starts_off")]
    if is_int(d.get("minutes")) and base:
        t = total(base, full)
        if not 0.75 * d["minutes"] <= t <= 1.25 * d["minutes"]:
            out.append(f"the slides' minutes add up to {math.floor(t + 0.5)}, the deck says {d['minutes']}")
    for p in presets:
        if not isinstance(p, dict) or not is_int(p.get("minutes")):
            continue
        if "only" in p and isinstance(p["only"], list):
            shown = [by_id[x] for x in p["only"] if isinstance(x, str) and x in by_id]
        else:
            hide = {x for x in p["hide"] if isinstance(x, str)} if isinstance(p.get("hide"), list) else set()
            shown = [x for x in base if x.get("id") not in hide]
        t = total(shown, p.get("id"))
        if shown and not 0.7 * p["minutes"] <= t <= 1.3 * p["minutes"]:
            out.append(f"version {p.get('id')!r}: its slides add up to {math.floor(t + 0.5)} minutes, it says {p['minutes']}")
    return out


def update_two_deck() -> dict:
    """A deck of the rules added on 2026-10-02 (SPEC "UPDATE 2"), right and wrong: version_minutes (and the sums that
    use them), a slide's lang, a handout that is also shown, a non-section accent, a version's `only` naming a slide
    that starts off, the phone numbers the site publishes. PresentationFiles names what the checker says of it; the
    build's twin must say the same (tests/test_presentations_build.py)."""
    # the site's own numbers, as it publishes them today (Zoom's first dial-in number, AA Grapevine's customer
    # service abroad, the two story lines)
    cfg = yaml.safe_load(SITE_YML.read_text(encoding="utf-8")) or {}
    dial = (((cfg.get("phone_access") or {}).get("numbers") or [{}])[0] or {}).get("number") or ""
    intl = (cfg.get("links") or {}).get("support_phone_intl") or ""
    try:
        audio = json.loads(AUDIO_PROJECT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        audio = {}
    story = [str(((audio or {}).get(p) or {}).get("phone") or "") for p in ("gv", "lv")]
    notes = "SAY: " + " ".join(["word"] * 30)

    def s(i: str, layout: str = "bullets", **kw) -> dict:
        out = {"id": i, "layout": layout, "title": f"Slide {i}", "notes": notes, "minutes": 1}
        if layout == "bullets":
            out["items"] = ["An item"]
        out.update(kw)
        return out
    return {
        "id": "update-two", "order": 1, "lang": "en", "title": "T", "short": "S", "eyebrow": "E", "footer": "F",
        "minutes": 20, "icon": "book-open", "tone": "gv",
        "card": {k: {"en": "a", "es": "b"} for k in ("title", "summary", "audience")},
        "presets": [
            {"id": "full", "label": {"en": "Full", "es": "Completo"}, "minutes": 20},
            # right only with vm-ok's version_minutes (1 minute instead of 8)
            {"id": "short", "label": {"en": "Short", "es": "Breve"}, "minutes": 10, "hide": ["phones", "bad-lang"]},
            # wrong only because of them (30 minutes instead of 8)
            {"id": "long", "label": {"en": "Long", "es": "Larga"}, "minutes": 18, "hide": ["phones"]},
            # the slide that starts off counts: 1 + 3 + 1
            {"id": "visit", "label": {"en": "Visit", "es": "Visita"}, "minutes": 5, "only": ["title", "off-in-visit", "credits"]},
            # 2.5 minutes: "3" in both checkers (rounded half up)
            {"id": "half", "label": {"en": "Half", "es": "Media"}, "minutes": 10, "only": ["vm-ok"]},
        ],
        "slides": [
            s("title", "title"),
            s("handout-shown", handout=True, minutes=2),
            s("own-accent", accent="lv"),
            s("spanish", "text", lang="es", title="Comparte tu historia",
              body="Escribe a manuscritoslv@aagrapevine.org o graba tu historia por teléfono."),
            s("bad-lang", lang="fr"),
            s("phones", items=[f"By phone: {dial} (Houston)", f"Story lines: {story[0]} · {story[1]}",
                               f"AA Grapevine customer service: {intl}", "A member's cell: 214-555-0142"]),
            s("vm-ok", minutes=8, version_minutes={"short": 1, "long": 30, "half": 2.5}),
            s("vm-unknown", version_minutes={"nope": 2}),
            s("vm-bad", version_minutes={"short": "two"}),
            s("vm-empty", version_minutes={}),
            s("off-in-visit", starts_off=True, optional=True, minutes=3),
            s("credits", "credits", sources=["Not an official AA Grapevine, Inc. presentation."]),
        ],
    }


UPDATE_TWO_PROBLEMS = [
    'slide 5 (bad-lang): lang is "en" or "es" (the language the slide is written in)',
    "slide 6 (phones) items[3]: a personal-looking phone number '214-555-0142' (a Zoom meeting ID? write "
    "{live:meeting_zoom_id} / {live:lv_workshop_zoom_id}; the site's own numbers: {live:meeting_phone}, "
    "{live:gv_audio_phone}, {live:lv_audio_phone})",
    "slide 8 (vm-unknown): version_minutes for an unknown version 'nope'",
    "slide 9 (vm-bad): version_minutes.short must be minutes (0.25–30)",
    "slide 10 (vm-empty): version_minutes {<version id>: minutes}",
    "version 'long': its slides add up to 40 minutes, it says 18",
    "version 'half': its slides add up to 3 minutes, it says 10",
]


def update_three_deck() -> dict:
    """A deck of the rules added on 2026-10-02 after the review (SPEC "UPDATE 3"), right and wrong: version_fields,
    notes lines for some versions only ({only:…} / {not:…}), {lang:es}…{/lang} spans, {ui:…} control names, the text
    styles "script" and "break", `print` on handout pages, the deadlines' limit_each, the events' "assemblies" filter,
    the new {live:…} keys and "taught" among the classroom words — and, from the fix round, `checklist` on columns
    and {live:meeting_day}. PresentationFiles names what the checker says of it; the build's twin must say the same
    (tests/test_presentations_build.py)."""
    notes = "SAY: " + " ".join(["word"] * 30)

    def s(i: str, layout: str = "bullets", **kw) -> dict:
        out = {"id": i, "layout": layout, "title": f"Slide {i}", "notes": notes, "minutes": 1}
        if layout == "bullets":
            out["items"] = ["An item"]
        out.update(kw)
        return out
    return {
        "id": "update-three", "order": 1, "lang": "en", "title": "T", "short": "S", "eyebrow": "E", "footer": "F",
        "minutes": 30, "icon": "book-open", "tone": "gv",
        "card": {k: {"en": "a", "es": "b"} for k in ("title", "summary", "audience")},
        "presets": [
            {"id": "full", "label": {"en": "Full", "es": "Completo"}, "minutes": 30},
            {"id": "short", "label": {"en": "Short", "es": "Breve"}, "minutes": 25, "hide": ["break"]},
            {"id": "visit", "label": {"en": "Visit", "es": "Visita"}, "minutes": 3, "only": ["title", "agenda", "credits"]},
        ],
        "slides": [
            # right: per-version text, notes lines for some versions, spans in Spanish, control names, the new keys
            s("title", "title", notes=notes + "\n{only:short} TRANSITION: the short version goes straight to the agenda."
              "\n{not:visit, short}TRANSITION: the full version stops for a break first."
              "\nDO: open {ui:customize} → {ui:your_details}, then {ui:prepare} and {ui:print}."),
            s("agenda", "agenda", items=[{"time": "0:00", "title": "Welcome", "from": "title"}],
              version_fields={"short": {"title": "Today's plan (about 25 minutes)"}, "visit": {"items": [{"time": "0:00", "title": "Hello"}]}}),
            s("activity", "activity", steps=["Write", "Share"], duration=10,
              version_fields={"short": {"duration": 5, "steps": ["Write three lines"], "takeaway": "Short and sweet"}}),
            s("break", "text", style="break", body="A ten-minute break"),
            s("script", "text", style="script", lang="es", body="Anuncio: ‹fecha› en ‹lugar›.",
              notes=notes + "\n{lang:es}EN ESPAÑOL: léelo despacio.{/lang}\nSAY: then {lang:es}gracias{/lang} in Spanish."),
            s("spans", items=["We say {lang:es}bienvenidos{/lang} and {lang:en}welcome{/lang}"]),
            s("new-keys", items=["{live:meeting_month} meeting, {live:meeting_day} · next assembly {live:assembly_next}",
                                 "{live:gv_open_meeting} · {live:lv_open_meeting} · {live:open_meeting_zoom}",
                                 "Themes: {live:gv_theme} · {live:lv_theme}"]),
            s("deadlines", "live", kind="deadlines", options={"pub": "both", "limit": 6, "limit_each": 3}),
            s("assemblies", "live", kind="events", options={"filter": "assemblies", "limit": 3}),
            s("handout-portrait", "text", facilitator=True, handout=True, print="portrait", minutes=None, body="A handout"),
            s("handout-landscape", handout=True, print="landscape"),
            s("quote", "quote", quote="We teach", credit="X", version_fields={"short": {"quote": "We taught"}}),
            # wrong
            s("notes-versions", notes=notes + "\n{only:nope} TRANSITION: x\n{not:} TRANSITION: y"
              "\nSAY: in the middle {only:short} of a line"),
            s("only-on-slide", items=["{only:short} An item"]),
            s("lang-bad", items=["{lang:fr}Bonjour{/lang}", "{lang:es}abierto", "cerrado{/lang}", "{lang:es}a {lang:en}b{/lang}"],
              takeaway="{lang:es}line one\nline two{/lang}"),
            s("tags-bad", items=["{ui:settings}", "{/bold}", "{lang}"]),
            s("styles-bad", "text", style="panels", body="x"),
            s("columns-style", "columns", style="script", columns=[{"heading": "A", "text": "a"}, {"heading": "B", "text": "b"}]),
            s("print-not-handout", print="portrait"),
            s("print-bad", handout=True, print="sideways"),
            s("vf-unknown", version_fields={"nope": {"title": "x"}}),
            s("vf-fields", version_fields={"short": {"minutes": 3, "notes": "x", "items": ["ok"]}}),
            s("vf-live", "live", kind="deadlines", version_fields={"short": {"options": {"limit": 2}, "intro": "Due soon"}}),
            s("vf-values", "activity", steps=["a"], duration=3, version_fields={"short": {"duration": 0, "steps": [], "title": ""}}),
            s("vf-shape", version_fields={"short": "text"}),
            s("vf-empty", version_fields={}),
            s("vf-words", version_fields={"short": {"title": "Our training"}}),
            s("limit-each-bad", "live", kind="deadlines", options={"limit_each": 0}),
            s("limit-each-events", "live", kind="events", options={"limit_each": 2}),
            s("sponsor-words", items=["What my sponsor taught me"]),
            # the fix round: tick boxes in columns (a printed checklist in English and in Spanish) — and not "yes"
            s("columns-checklist", "columns", checklist=True, facilitator=True, handout=True, minutes=None,
              columns=[{"heading": "Revision checklist", "items": ["Is it true?"]},
                       {"heading": "Lista de revisión", "items": ["¿Es verdad?"]}]),
            s("columns-checklist-bad", "columns", checklist="yes", columns=[{"heading": "A", "text": "a"}, {"heading": "B", "text": "b"}]),
            s("credits", "credits", sources=["Not an official AA Grapevine, Inc. presentation."]),
        ],
    }


UPDATE_THREE_PROBLEMS = [
    "slide 13 (notes-versions) notes: {only:nope} — no version 'nope'",
    "slide 13 (notes-versions) notes: {not:} names no version",
    "slide 13 (notes-versions) notes: {only:…} goes at the start of a line of the notes",
    "slide 14 (only-on-slide) items[0]: {only:…} goes at the start of a line of the notes",
    'slide 15 (lang-bad) items[0]: {lang:fr} — the language is "en" or "es"',
    "slide 15 (lang-bad) items[1]: {lang:es} without its {/lang} on the same line",
    "slide 15 (lang-bad) items[2]: {/lang} without its {lang:…}",
    "slide 15 (lang-bad) items[3]: a {lang:…} inside another one (close the first with {/lang})",
    "slide 15 (lang-bad) takeaway: {lang:es} without its {/lang} on the same line",
    "slide 15 (lang-bad) takeaway: {/lang} without its {lang:…}",
    "slide 16 (tags-bad) items[0]: unknown {ui:settings} — a control of the player: customize, version, slides, edit, "
    "add, your_details, prepare, save_share, notes, overview, presenter_view, print, full_screen, black_screen",
    "slide 16 (tags-bad) items[1]: unknown placeholder {/bold}",
    "slide 16 (tags-bad) items[2]: unknown placeholder {lang}",
    "slide 17 (styles-bad): style script | break",
    "slide 18 (columns-style): style panels | cards | plain",
    "slide 19 (print-not-handout): print is for a handout page (handout: true)",
    'slide 20 (print-bad): print is "portrait" or "landscape"',
    "slide 21 (vf-unknown): version_fields for an unknown version 'nope'",
    "slide 22 (vf-fields): version_fields.short: 'minutes' is not a field a version can change on a 'bullets' slide",
    "slide 22 (vf-fields): version_fields.short: 'notes' is not a field a version can change on a 'bullets' slide",
    "slide 23 (vf-live): version_fields.short: 'options' is not a field a version can change on a 'live' slide",
    "slide 24 (vf-values) version_fields.short: title required",
    "slide 24 (vf-values) version_fields.short.steps: needs a list with at least one item",
    "slide 24 (vf-values) version_fields.short: duration (the time card's minutes)",
    "slide 25 (vf-shape): version_fields.short {<field>: value}",
    "slide 26 (vf-empty): version_fields {<version id>: {<field>: value}}",
    "slide 27 (vf-words) version_fields.short.title: the word 'training' breaks the site's wording rules (…Our training…)",
    "slide 28 (limit-each-bad): options.limit_each 1–12 (rows of each magazine)",
    "slide 29 (limit-each-events): option 'limit_each' is not used by 'events' (['filter', 'limit', 'series'])",
    "slide 30 (sponsor-words) items[0]: the word 'taught' breaks the site's wording rules (…What my sponsor taught me…)",
    "slide 32 (columns-checklist-bad): checklist must be true or false",
]


class PresentationFiles(unittest.TestCase):
    def test_every_deck(self):
        files = sorted(FOLDER.glob("*.yml")) if FOLDER.exists() else []
        for f in files:
            with self.subTest(deck=f.name):
                problems = check_deck(f)
                self.assertEqual(problems, [], "\n" + "\n".join(problems[:60]))

    def test_the_four_decks(self):
        if not FOLDER.exists():
            self.skipTest("config/presentations/ not there yet")
        self.assertEqual(sorted(p.stem for p in FOLDER.glob("*.yml")), sorted(DECKS))
        orders = [yaml.safe_load((FOLDER / f"{d}.yml").read_text(encoding="utf-8")).get("order") for d in DECKS]
        self.assertEqual(len(set(orders)), 4, "each deck has its own order")

    def test_checker_catches_problems(self):
        """The checker itself: a broken deck is reported, line by line."""
        import tempfile
        bad = {
            "id": "sample", "order": 1, "lang": "en", "title": "T", "short": "S", "eyebrow": "E", "footer": "F",
            "minutes": 10, "icon": "book-open", "tone": "gv",
            "card": {"title": {"en": "a", "es": "b"}, "summary": {"en": "a"}, "audience": {"en": "a", "es": "b"}},
            "presets": [{"id": "full", "label": {"en": "Full", "es": "Completo"}, "minutes": 10}],
            "fillins": [{"key": "first_name", "label": {"en": "a", "es": "b"}, "hint": "first name", "notes_only": True}],
            "slides": [{"id": f"s{i}", "layout": "bullets", "title": "Hi", "items": ["Subscribe now before prices go up"],
                        "notes": "SAY: " + "word " * 30 + "{fill:first_name} {live:nope}", "minutes": 2} for i in range(5)]
                      + [{"id": "q", "layout": "quote", "title": "Q", "quote": "We teach", "credit": "X",
                          "notes": "SAY: " + "word " * 30 + "\nTIME: about 2 minutes", "minutes": 1,
                          "eyebrow": "{fill:first_name}"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.yml"
            p.write_text(yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8")
            problems = "\n".join(check_deck(p))
        for expect in ("card.summary", "sounds like selling", "unknown {live:nope}", "no TIME: line",
                       "is notes_only", "Not an official AA Grapevine"):
            self.assertIn(expect, problems)
        self.assertNotIn("'teach'", problems, "a verbatim quote is exempt from the wording rules")

    def test_update_two_rules(self):
        """version_minutes (an unknown version, a value that is not minutes) and the sums that use them; lang;
        handout on a shown slide, accent on any slide, `only` naming a slide that starts off and the site's own phone
        numbers are fine — exactly these lines, nothing more."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "update-two.yml"
            p.write_text(yaml.safe_dump(update_two_deck(), allow_unicode=True), encoding="utf-8")
            self.assertEqual(sorted(check_deck(p)), sorted(UPDATE_TWO_PROBLEMS))

    def test_update_three_rules(self):
        """version_fields (a version of the deck, a field the layout has and a version may change, and the slide as
        that version shows it keeps every rule), {only:…} / {not:…} at the start of a notes line naming versions of
        the deck, {lang:…}…{/lang} in "en" or "es" closed on the same line, {ui:…} naming a control of the player, the
        text styles, `print` on a handout page, limit_each, the "assemblies" filter, the new {live:…} keys, "taught"
        and tick boxes in columns (true or false) — exactly these lines, nothing more."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "update-three.yml"
            p.write_text(yaml.safe_dump(update_three_deck(), allow_unicode=True), encoding="utf-8")
            self.assertEqual(sorted(check_deck(p)), sorted(UPDATE_THREE_PROBLEMS))

    def test_taught_is_a_classroom_word(self):
        # "teach" in every form, the irregular past too ("what my sponsor taught me": shared with me, showed me)
        for text in ("taught", "Taught", "We teach", "teaching", "teacher", "enseñó"):
            self.assertRegex(text, BANNED)
        for text in ("thought", "shared with me", "showed me"):
            self.assertNotRegex(text, BANNED)

    def test_the_numbers_the_site_publishes(self):
        nums = published_phones()
        cfg = yaml.safe_load(SITE_YML.read_text(encoding="utf-8")) or {}
        for n in (cfg.get("phone_access") or {}).get("numbers") or []:
            if PHONE.fullmatch(str(n["number"]).strip()):         # (a U.S. number: what a deck could write)
                self.assertIn(phone_digits(n["number"]), nums, "Zoom's dial-in numbers")
        intl = (cfg.get("links") or {}).get("support_phone_intl")
        if intl:
            self.assertIn(phone_digits(intl), nums, "anywhere in config/site.yml")
        if AUDIO_PROJECT.exists():
            audio = json.loads(AUDIO_PROJECT.read_text(encoding="utf-8"))
            for pub in ("gv", "lv"):
                if (audio.get(pub) or {}).get("phone"):
                    self.assertIn(phone_digits(audio[pub]["phone"]), nums, f"the {pub} story line")
        self.assertEqual(phone_digits("+1 (346) 248-7799"), phone_digits("346.248.7799"))
        self.assertNotIn(phone_digits("214-555-0142"), nums)

    def test_la_vinas_monthly_workshop_is_never_an_information_workshop(self):
        # P7-6: one name for La Viña's monthly Zoom workshop, "Taller Mensual y Virtual de La Viña" (La Viña's monthly
        # virtual workshop) — "an information workshop" is the committee's own workshop (information-workshop.yml)
        said = re.compile(r"(?i)La Viña(?:'s)?(?: office)? (?:holds|hosts|has) an? information workshop")
        for f in sorted(FOLDER.glob("*.yml")):
            with self.subTest(deck=f.name):
                self.assertNotRegex(f.read_text(encoding="utf-8"), said)
        deck = yaml.safe_load((FOLDER / "orientation-workshop.yml").read_text(encoding="utf-8"))
        glance = next(s for s in deck["slides"] if s.get("id") == "month-at-a-glance")
        self.assertIn("its monthly virtual workshop in Spanish on Zoom, the {lang:es}Taller Mensual y Virtual de La Viña{/lang}",
                      glance["notes"])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith(".yml"):
        found = 0
        for arg in sys.argv[1:]:
            probs = check_deck(Path(arg))
            found += len(probs)
            print(f"{arg}: {'OK' if not probs else str(len(probs)) + ' problem(s)'}")
            for line in probs:
                print("  - " + line)
        sys.exit(1 if found else 0)
    unittest.main()
