"""The bingo cards' CSV (content/bingo/bingo.csv → the GVR / RLV corner's bingo, /gvr/bingo/ and /es/gvr/bingo/, and
the sample card of the /gvr/ teaser): every row stays complete, correct and in line with AA's principles.

This file is the CHECKER the committee's Code check runs, and the Python twin of the build's own checker
(eleventy/filters/bingo.js checkBingoCsv, which leaves a row with a mistake out of the cards): the same rules, the same
problem lines, the same items — the tests hold the two together. The rules (aagrapevine-ops/r34/SPEC.md §2; the
owner's guide is content/bingo/README.md):

  * the file: UTF-8 (a BOM is fine), commas, the first row the header; RFC 4180 quotes — read by the booth's reader
    (booth.js parseCsv, here test_booth_csv.parse_csv: bingo.js reuses it, so this file does too); a cell that opens a
    quote and never closes it is named;
  * the header: column names in any order and capitalization, unknown columns ignored, a known one twice named (the
    first one is used); `id`, `type` and `cat` needed;
  * each row (a blank row and a row whose id starts with "#" are skipped; a row switched off with on = no is checked
    all the same; every cell read as one line: NFC, each run of white space one space): a unique id (a-z, 0-9,
    dashes, 48 characters at most), on, type (check, name, phone, write, sign, info), pub, cat (people … fun, or a new
    category src/_i18n/bingo.json names: "bingo.cat.<cat>" in English and Spanish), an info square only in cat
    meetings, where (group … online), pin, weight (0.5–5), from / until (real days of the years 2000–2099), source_url
    (https://); the languages (a row is offered in a language when it has that language's text_*; short_* / label_*
    without it is a mistake, and so is a row with no text at all); the lengths (text 90, short 36 — needed when the
    text is longer than 36 —, label 24; a placeholder counts as 20; characters as a person counts them); label_* only
    on name, phone, write and sign rows; only the PLACEHOLDERS in a shown cell; no refused word — the booth's
    (test_booth_csv.refused_in, the twin of booth.js refusedIn, which bingo.js reuses: PDF, donations, contributions to
    Grapevine, sales and urgency words, the unverified claims, "Conference-approved" said of the magazines, "today
    only" without {event}) and bingo's own (no selfies or photos of people, no last or full names: anonymity, first
    names only); two rows that are on never with the same text in a language, nor with the same big-grid words
    (short_*, else the text: what a 7×7 and up prints) — capitals ignored; the first one keeps them, rows with other
    mistakes take no part.

The items are the build's (SPEC §2 data contract), placeholders as written — the build fills them in afterwards
(bingo.js fillItems; Real.test_the_build_fills_every_square holds the real file to it):
{ id, type, pub, cat, where: [...] ([] = everywhere), pin, weight, from, until, text: {en, es}, short: {en, es},
label: {en, es} } — a language the row is not offered in is "" in all three; short is short_* or the text itself.

  * Real — the real content/bingo/bingo.csv (the committee's pool of squares): no problem at all, at least 200
    squares, both languages on every row, enough squares for a 10×10 card with each magazine and wherever a GVR takes
    it, every category, occasion and type used, the meetings and the contact pinned on every card, the meeting lines
    filled in by the build — in the words config/site.yml's meetings give (day, time range, zone, platform). A
    CONTENT test (scripts/ops/gate_tests.py): the Code check runs it, Website update leaves it out;
  * Fixtures — tests/fixtures/bingo_csv/*.csv, one kind of mistake each, named line by line (good.csv and pool.csv
    have none: pool.csv is the pool tests/test_r34_bingo.py builds its pages from);
  * Rules — a few rules best shown with a few lines of CSV (and the shape of an item);
  * Twin — the build's JavaScript checker gives the same lines, items, rows and row numbers for every fixture, the
    inline cases and the real file, a Spanish line for every problem, and the same constants, lengths, refused words
    and categories (through tests/nodejs.py; skipped without Node.js or node_modules);
  * Info — the meeting lines the build writes from fixed meetings (bingo.js bingoInfo, through tests/nodejs.py):
    our Grapevine Meeting's and the committee meeting's long, mid and short lines, word for word and against this
    file's twin (meeting_lines), and the weekly open meetings' words for big grids ({gv_weekly_short} /
    {lv_weekly_short}) — every hour kept on one line with its AM / PM (clock_split).
No Reader class: the reader is the booth's, and tests/test_booth_csv.py Reader holds it to Python's csv module.

    .venv\\Scripts\\python.exe tests\\test_bingo_csv.py content\\bingo\\bingo.csv     (one file: its problems)
    python -m unittest tests.test_bingo_csv -v
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import unittest
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
# the booth's reader, refused words, link and day readers — what bingo.js imports from booth.js (parseCsv, refusedIn,
# splitUrl; its validDay is booth.js's rule word for word), each one held to booth.js by test_booth_csv's own Twin
from test_booth_csv import parse_csv, read_csv_file, refused_in, split_url, valid_day  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "content" / "bingo" / "bingo.csv"
I18N_FILE = ROOT / "src" / "_i18n" / "bingo.json"
FIXTURES = ROOT / "tests" / "fixtures" / "bingo_csv"

# ------------------------------------------------------------------------------------------- bingo.js's constants
COLUMNS = ["id", "on", "type", "pub", "cat", "where", "pin", "weight", "from", "until",
           "text_en", "short_en", "label_en", "text_es", "short_es", "label_es", "source_url", "notes"]
TYPES = ["check", "name", "phone", "write", "sign", "info"]
LABEL_TYPES = ["name", "phone", "write", "sign"]
CATS = ["people", "read", "write", "listen", "service", "meetings", "history", "fun"]
INFO_CAT = "meetings"
WHERES = ["group", "district", "assembly", "acm", "workshop", "booth", "committee", "online"]
PLACEHOLDERS = ["event", "committee", "area", "email", "site", "gv_meeting", "gv_meeting_short",
                "committee_meeting", "committee_meeting_short", "gv_weekly", "gv_weekly_short", "lv_weekly",
                "lv_weekly_short"]
# the meeting lines too long for a big grid, and their words for one (bingo.js bingoInfo: "1st Wed · 7 PM",
# "Wed 11 AM · Zoom") — short_* uses the second
SHORT_OF = {"gv_meeting": "gv_meeting_short", "committee_meeting": "committee_meeting_short",
            "gv_weekly": "gv_weekly_short", "lv_weekly": "lv_weekly_short"}
LIMITS = {"id": 48, "text": 90, "short": 36, "label": 24, "placeholder": 20, "weightMin": 0.5, "weightMax": 5}
LANGS = ["en", "es"]
LANG_NAME = {"en": "English", "es": "Spanish"}
ON_YES = ["yes", "y", "true", "1", "si", "sí"]
ON_NO = ["no", "n", "false", "0"]
PUBS = {
    "gv": "gv", "grapevine": "gv", "lv": "lv", "lavina": "lv", "laviña": "lv", "both": "both", "all": "both",
    "aa": "both", "ambos": "both", "ambas": "both", "gvlv": "both", "gv/lv": "both", "gv-lv": "both", "gv+lv": "both",
    "gv&lv": "both",
}
# the magazine filter of the builder (Both / Grapevine / La Viña) → the squares' pub it offers
MAGAZINES = {"both": ("gv", "lv", "both"), "gv": ("gv", "both"), "lv": ("lv", "both")}

# White space, spelled out (booth.js WS_CHARS): Python's \s and strip() and JavaScript's \s and trim() disagree on a few
# characters (U+FEFF, U+001C–U+001F, U+0085), and the two checkers must read every cell alike.
WS_CHARS = " \\t\\n\\r\\f\\v\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff"
WS = f"[{WS_CHARS}]"
TRIM = re.compile(rf"\A{WS}+|{WS}+\Z")
SPACES = re.compile(rf"{WS}+")
LIST_SPLIT = re.compile(rf"(?:[;,]|{WS})+")
MARK = re.compile(r"\{([^{}]*)\}")
ID = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
CAT_KEY = re.compile(r"\Abingo\.cat\.([a-z0-9]+(?:-[a-z0-9]+)*)\Z")

# ------------------------------------------------------------------------------- the words a bingo card never says
# (bingo.js BINGO_REFUSED — its W, [\p{L}\p{N}_], is Python's \w.) Anonymity (Traditions Eleven and Twelve): a card asks
# for a FIRST name, and only with the person's OK — never a last or full name, never a photo of a person. A photo of a
# thing ("a picture of the first cover", "una foto de mi libro") is not caught: the words after "photo of" / "foto de"
# (and any of a, the, your … / un, la, tu, mi …) must name a person — "él" and "mí" only with their accents.
PEOPLE_EN = (r"(?:someone|somebody|anyone|anybody|everyone|everybody|people|persons?|members?|friends?|sponsors?|"
             r"sponsees?|newcomers?|old-?timers?|speakers?|groups?|gvrs?|rlvs?|reps?|representatives?|delegates?|dcms?|"
             rf"chair(?:person)?s?|trusted{WS}+servants?|committee|yourself|yourselves|you|us|them|him|her|me|"
             rf"each{WS}+other)")
DET_EN = (r"(?:(?:a|an|the|your|my|our|their|his|her|this|that|these|those|another|other|each|every|one|two|three|"
          rf"some|any|new|fellow|whole){WS}+)*")
PEOPLE_ES = (r"(?:alguien|todos|todas|gente|personas?|miembros?|compañer[oa]s?|amig[oa]s?|padrinos?|madrinas?|"
             rf"ahijad[oa]s?|reci[eé]n{WS}+llegad[oa]s?|nuev[oa]s?|oradore?s?|oradoras?|grupos?|rlvs?|gvrs?|"
             r"representantes?|delegad[oa]s?|mcds?|coordinador(?:a|es|as)?|servidore?s?|servidoras?|comit[eé]|ti|"
             r"ustedes|nosotr[oa]s|ell[oa]s?|él|mí)")
DET_ES = (r"(?:(?:un|una|unos|unas|el|la|los|las|tu|tus|su|sus|mi|mis|nuestro|nuestra|nuestros|nuestras|otro|otra|"
          r"otros|otras|alg[uú]n|alguna|algunos|algunas|cada|este|esta|estos|estas|ese|esa|todo|toda|todos|todas)"
          rf"{WS}+)*")
PHOTO_EN = r"(?:photo(?:graph)?s?|pictures?|pics?|snapshots?)"
PHOTO_ES = r"(?:fotos?|fotograf[ií]as?|im[aá]gen(?:es)?)"
PHOTOS_WHY = "no photos of people: anonymity (first names only, no faces)"
NAMES_WHY = "first names only, never a last name: anonymity"
BINGO_REFUSED: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?<!\w)(?:selfies?|selfis?|autofotos?)(?!\w)", re.I), PHOTOS_WHY),
    (re.compile(rf"(?<!\w)(?:{PHOTO_EN}{WS}+(?:of|with){WS}+{DET_EN}{PEOPLE_EN}|(?:group|team){WS}+{PHOTO_EN})(?!\w)",
                re.I), PHOTOS_WHY),
    (re.compile(rf"(?<!\w)(?:{PHOTO_ES}{WS}+(?:de|del|con){WS}+{DET_ES}{PEOPLE_ES}|fotos?{WS}+grupal(?:es)?)(?!\w)",
                re.I), PHOTOS_WHY),
    (re.compile(rf"(?<!\w)(?:(?:last|full|family){WS}*names?|surnames?)(?!\w)", re.I), NAMES_WHY),
    (re.compile(rf"(?<!\w)(?:apellidos?|nombres?{WS}+completos?)(?!\w)", re.I), NAMES_WHY),
]


# ----------------------------------------------------------------------------------------------------------------
# Small readers (bingo.js's, one for one)
# ----------------------------------------------------------------------------------------------------------------
def one_line(v) -> str:
    """A cell as the checks read it: Unicode NFC, every run of white space one space, nothing around it."""
    s = unicodedata.normalize("NFC", "" if v is None else str(v))
    return TRIM.sub("", SPACES.sub(" ", s))


def measure(s: str) -> int:
    """A cell's length as the limits count it: its characters (code points: "ñ" is one), each {…} counting 20 (its
    words are filled in later, and differ between builds)."""
    rest, marks = MARK.subn("", s or "")
    return len(rest) + marks * LIMITS["placeholder"]


def bingo_refused_in(text: str) -> list[tuple[str, str]]:
    """Every refused word in a shown cell → [(word as written, why)]: the booth's, then bingo's own."""
    out = refused_in(text)
    for rx, why in BINGO_REFUSED:
        m = rx.search(text)
        if m:
            out.append((m[0], why))
    return out


def cat_names_of(data) -> list[str]:
    """src/_i18n/bingo.json (its data) → the categories it names: every key "bingo.cat.<cat>" whose English and
    Spanish are both filled in, in the file's order (bingo.js catNamesOf)."""
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    for k, v in data.items():
        m = CAT_KEY.match(k)
        if m and isinstance(v, dict) and one_line(v.get("en")) and one_line(v.get("es")) and m[1] not in out:
            out.append(m[1])
    return out


def i18n_cat_names(path: Path = I18N_FILE) -> list[str]:
    """The categories src/_i18n/bingo.json names, read as loadBingo reads it (no file, or one that is not JSON: none)."""
    try:
        return cat_names_of(json.loads(path.read_bytes().decode("utf-8", errors="replace")))
    except (OSError, ValueError):
        return []


# ----------------------------------------------------------------------------------------------------------------
# The checker (the build's checkBingoCsv, line for line)
# ----------------------------------------------------------------------------------------------------------------
class Checked(NamedTuple):
    items: list[dict]       # the squares the cards can use, in file order (placeholders as written)
    problems: list[str]     # one line per mistake: "bingo.csv row 14 (people-gvr-today): …" (the build's where: en)
    rows: int               # the rows after the header
    row_of: dict[str, int]  # each item's row


def check_bingo_csv(text: str, file: str = "bingo.csv", cat_names=()) -> Checked:
    """A CSV text → Checked(items, problems, rows, row_of). cat_names: the categories src/_i18n/bingo.json names
    (i18n_cat_names) — a cat outside CATS is accepted when it is one of them."""
    cat_names = list(cat_names or [])
    items: list[dict] = []
    problems: list[str] = []
    row_of: dict[str, int] = {}
    if "�" in text:
        problems.append(f"{file}: the file is not saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)")
    rows, unclosed = parse_csv(text)
    if unclosed:
        problems.append(f"{file} row {unclosed}: a cell starts with a double quote (\") that is never closed: everything after it was read as that one cell")
    header = rows[0] if rows else []
    if not any(one_line(c) for c in header):
        problems.append(f"{file}: the file is empty: the first row must be the header (id,on,type,…)")
        return Checked(items, problems, 0, row_of)
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
    needed = ("id", "type", "cat")
    for need in needed:
        if need not in col:
            problems.append(f"{file} header: the header (first row) has no {need} column")
    if any(k not in col for k in needed):
        return Checked(items, problems, len(rows) - 1, row_of)

    seen: dict[str, int] = {}                                         # id → the row it was first used in
    texts: dict[str, dict[str, tuple[int, str]]] = {"en": {}, "es": {}}  # a shown text (lower case) → its first row
    shorts: dict[str, dict[str, tuple[int, str, str]]] = {"en": {}, "es": {}}  # big-grid words → first row, id, cell
    types, cats, wheres_all = ", ".join(TYPES), ", ".join(CATS), ", ".join(WHERES)
    marks_all = ", ".join(f"{{{p}}}" for p in PLACEHOLDERS)
    label_types = ", ".join(LABEL_TYPES[:-1]) + " and " + LABEL_TYPES[-1]
    for r in range(1, len(rows)):
        cells = rows[r]
        row_no = r + 1
        if not any(one_line(c) for c in cells):
            continue                                                  # a blank row

        def get(k: str) -> str:
            return cells[col[k]] if k in col and col[k] < len(cells) else ""

        id_raw = one_line(get("id"))
        if id_raw.startswith("#"):
            continue                                                  # a comment
        where = f"{file} row {row_no}" + (f" ({id_raw[:LIMITS['id']]})" if id_raw else "")
        errs: list[str] = []
        err = errs.append

        # more cells than the header has: a comma in a text that is not in quotes moved every cell after it
        if len(cells) > len(header) and any(one_line(c) for c in cells[len(header):]):
            err(f"the row has {len(cells)} cells but the header has {len(header)}: a comma inside a text needs the whole cell in double quotes")
            problems.extend(f"{where}: {e}" for e in errs)
            continue

        # id, on, type, pub, cat, where, pin, weight, dates, source_url
        rid = ""
        if not id_raw:
            err("id is empty")
        elif not ID.match(id_raw) or len(id_raw) > LIMITS["id"]:
            err(f'id "{id_raw}": use only a–z, 0–9 and dashes (no spaces or capitals), at most {LIMITS["id"]} characters')
        elif id_raw in seen:
            err(f'id "{id_raw}" is already used in row {seen[id_raw]}')
        else:
            rid = id_raw
            seen[rid] = row_no

        def yes_no(k: str) -> bool | None:
            v = one_line(get(k))
            lc = v.lower()
            if not v:
                return None
            if lc in ON_YES:
                return True
            if lc in ON_NO:
                return False
            err(f'{k} "{v}": write yes or no')
            return None

        on = yes_no("on")
        on = True if on is None else on
        type_raw = one_line(get("type"))
        typ = type_raw.lower()
        type_ok = typ in TYPES
        if not type_raw:
            err(f"type is empty ({types})")
        elif not type_ok:
            err(f'type "{type_raw}" is not one of: {types}')
        pub_raw = one_line(get("pub"))
        pub = "both" if not pub_raw else PUBS.get(SPACES.sub("", pub_raw.lower()))
        if not pub:
            err(f'pub "{pub_raw}": write gv, lv or both')
        cat_raw = one_line(get("cat"))
        cat = cat_raw.lower()
        cat_ok = cat in CATS or cat in cat_names
        if not cat_raw:
            err(f"cat is empty ({cats})")
        elif not cat_ok:
            err(f'cat "{cat_raw}" is not one of: {cats} — a new category also needs its name in src/_i18n/bingo.json '
                f'("bingo.cat.{cat}", in English and Spanish)')
        if type_ok and typ == "info" and cat_ok and cat != INFO_CAT:
            err(f"type info is only for cat {INFO_CAT} rows (an information square: our meetings, events and contact)")
        wheres: list[str] = []
        for w in [x for x in LIST_SPLIT.split(one_line(get("where")).lower()) if x]:
            if w not in WHERES:
                err(f'where: "{w}" is not one of: {wheres_all}')
            elif w not in wheres:
                wheres.append(w)
        pin = yes_no("pin")
        pin = False if pin is None else pin
        w_raw = one_line(get("weight"))
        weight: float = 1
        if w_raw:
            n = float(w_raw.replace(",", ".", 1)) if re.fullmatch(r"[0-9]{1,3}(?:[.,][0-9]{1,3})?", w_raw) else float("nan")
            if LIMITS["weightMin"] <= n <= LIMITS["weightMax"]:
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
        src_raw = one_line(get("source_url"))
        if src_raw and not split_url(src_raw):
            err(f'source_url "{src_raw}": not an https:// link')

        # the two languages: what each one has, what a shown language needs, the lengths, the placeholders and words
        L = {lang: {f: one_line(get(f"{f}_{lang}")) for f in ("text", "short", "label")} for lang in LANGS}
        langs: list[str] = []
        partial = False          # a language with short / label but no text (named: no "no text at all" line on top)
        for lang in LANGS:
            v = L[lang]
            if v["label"] and type_ok and typ not in LABEL_TYPES:
                err(f"label_{lang} is only for {label_types} rows")
            if not v["text"]:
                others = [f"{f}_{lang}" for f in ("short", "label") if v[f]]
                if others:
                    partial = True
                    err(f"text_{lang} is empty, but other {LANG_NAME[lang]} cells are filled ({', '.join(others)}): fill it in, or empty them")
                continue
            langs.append(lang)
            for f in ("text", "short", "label"):
                n = measure(v[f])
                if v[f] and n > LIMITS[f]:
                    note = f"; each {{…}} counts as {LIMITS['placeholder']}" if MARK.search(v[f]) else ""
                    err(f"{f}_{lang}: {n} characters ({LIMITS[f]} at most{note})")
            n = measure(v["text"])
            if n > LIMITS["short"] and not v["short"]:
                err(f"short_{lang} is empty, but text_{lang} has {n} characters (more than {LIMITS['short']}): write the words for big grids (7×7 and up)")
        if not langs and not partial:
            err("the row has no text in English or Spanish: fill in text_en, text_es or both")
        for lang in LANGS:
            for f in ("text", "short", "label"):
                v = L[lang][f]
                if not v or not L[lang]["text"]:
                    continue
                name = f"{f}_{lang}"
                marks: list[str] = []
                for m in MARK.finditer(v):
                    if m[1] not in PLACEHOLDERS and m[1] not in marks:
                        marks.append(m[1])
                for mk in marks:
                    err(f"{name}: {{{mk}}} is not a placeholder bingo knows ({marks_all})")
                for word, why in bingo_refused_in(v):
                    err(f"{name}: “{word}” is not used on bingo cards — {why}")
        # two rows that are on with the same text: a card could show the same square twice (the first one keeps it); then
        # the same for the big grids' words — short_*, else the text itself: what a 7×7 and up (or a card with small
        # squares) prints, every square in them —, checked only when the texts differ (one line for one mistake)
        if not errs and on:
            for lang in langs:
                first = texts[lang].get(L[lang]["text"].lower())
                if first:
                    err(f"text_{lang} is the same as in row {first[0]} ({first[1]}): a card could show the same square twice")

            def big(lang: str) -> tuple[str, str]:
                # a row's big-grid words, and the cell they come from: "short_en", or "text_en" when short_en is blank
                return (L[lang]["short"] or L[lang]["text"]).lower(), f"{'short' if L[lang]['short'] else 'text'}_{lang}"

            if not errs:
                for lang in langs:
                    key, cell = big(lang)
                    first = shorts[lang].get(key)
                    if first:
                        there = "" if first[2] == cell else f"{first[2]} "
                        err(f"{cell} is the same as {there}in row {first[0]} ({first[1]}): a big card could show the same "
                            "words twice")
            if not errs:
                for lang in langs:
                    texts[lang][L[lang]["text"].lower()] = (row_no, rid)
                    key, cell = big(lang)
                    shorts[lang][key] = (row_no, rid, cell)

        if errs:
            problems.extend(f"{where}: {e}" for e in errs)
            continue
        if not on:
            continue

        def pick(f) -> dict[str, str]:
            return {lang: (f(L[lang]) if lang in langs else "") for lang in LANGS}

        items.append({
            "id": rid, "type": typ, "pub": pub, "cat": cat, "where": wheres, "pin": pin, "weight": weight,
            "from": dates["from"], "until": dates["until"],
            "text": pick(lambda x: x["text"]), "short": pick(lambda x: x["short"] or x["text"]),
            "label": pick(lambda x: x["label"]),
        })
        row_of[rid] = row_no
    return Checked(items, problems, len(rows) - 1, row_of)


def check_file(path: Path, cat_names=None) -> Checked:
    """A CSV file checked as the build checks it (the categories of src/_i18n/bingo.json unless given)."""
    return check_bingo_csv(read_csv_file(path), file=path.name,
                           cat_names=i18n_cat_names() if cat_names is None else cat_names)


# ----------------------------------------------------------------------------------------------------------------
# A monthly meeting's lines on the cards (bingo.js meetingLines and BINGO_WORDS, word for word): Info and Real hold
# the build's lines to these, for fixed meetings and for config/site.yml's
# ----------------------------------------------------------------------------------------------------------------
ORD = {"en": {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", -1: "last"},
       "es": {1: "1.er", 2: "2.º", 3: "3.er", 4: "4.º", 5: "5.º", -1: "último"}}
WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
DAY_NAME = {"en": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "es": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]}
DAY_ABBR = {"en": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "es": ["dom.", "lun.", "mar.", "mié.", "jue.", "vie.", "sáb."]}
COMMITTEE_I18N = ROOT / "src" / "_i18n" / "committee.json"


def plain(s: str) -> str:
    """Intl's and esMeridiem's thin, narrow and no-break spaces read as spaces."""
    return re.sub(r"[\u2009\u202f\u00a0]", " ", s)


def clock_split(lines: list) -> list[str]:
    """The lines ({en, es} each, or None) where an hour and its AM / PM ("7 PM", "8 PM" of "7 – 8 PM", "7 p. m.") may
    go on two lines: a plain space between them, or inside "p. m." — bingo.js clockJoin (the meeting lines, the
    weekly meetings' "when") joins them with a narrow no-break space in English, esMeridiem's no-break space in
    Spanish (the strip's "3rd Wed · 7" / "PM · Google Meet" in round 34's last review)."""
    return [s for v in lines if v for s in v.values() if re.search(r"\d (?:[AP]M|[ap]\.)|[ap]\. m\.", s)]


def clock_text(start: str, end: str, lang: str, start_only: bool = False) -> str:
    """A meeting's clock times as bingo.js clockText writes them (spaces plain): "7 – 8 PM" / "7–8 p. m.", "7:30 –
    9:00 AM", "11:30 AM – 12:30 PM", overnight "10 PM – 1 AM" / "10 p. m. – 1 a. m."; start_only "7 PM" / "7 p. m."."""
    (sh, sm), (eh, em) = (map(int, start.split(":")), map(int, end.split(":")))
    minutes = bool(sm or (not start_only and em))

    def at(h: int, m: int) -> str:
        return f"{h % 12 or 12}:{m:02d}" if minutes else f"{h % 12 or 12}"

    def meridiem(h: int) -> str:
        return ("AM", "PM")[h >= 12] if lang == "en" else ("a. m.", "p. m.")[h >= 12]

    if start_only:
        return f"{at(sh, sm)} {meridiem(sh)}"
    if (eh, em) > (sh, sm) and meridiem(sh) == meridiem(eh):
        return f"{at(sh, sm)}{' – ' if lang == 'en' else '–'}{at(eh, em)} {meridiem(eh)}"
    return f"{at(sh, sm)} {meridiem(sh)} – {at(eh, em)} {meridiem(eh)}"


def meeting_lines(n: int, weekday: str, start: str, end: str, where: str, place: bool = False) -> dict:
    """A monthly meeting (the n-th weekday, -1 the last; start and end "HH:MM", Central time; where its platform or,
    place, its place) → {"long", "mid", "short": {en, es}} — the Spanish day in the site's own words (committee.rule,
    committee.ord.*: "cada tercer miércoles del mes"), the zone as the site writes it ("Central", "(hora del Centro)")."""
    i18n = json.loads(COMMITTEE_I18N.read_text(encoding="utf-8"))
    wd = WEEKDAYS.index(weekday)
    rule_es = i18n["committee.rule"]["es"].format(ord=i18n[f"committee.ord.{'last' if n == -1 else n}"]["es"],
                                                  weekday=DAY_NAME["es"][wd])
    day = {"en": f"{ORD['en'][n]} {DAY_NAME['en'][wd]} of the month", "es": rule_es[0].lower() + rule_es[1:]}
    zone = {"en": "{} Central", "es": "{} (hora del Centro)"}
    at = {"en": where, "es": f"{'en' if place else 'por'} {where}"}
    out: dict = {"long": {}, "mid": {}, "short": {}}
    for lang in LANGS:
        first = clock_text(start, end, lang, start_only=True)
        out["long"][lang] = ", ".join(x for x in (day[lang], zone[lang].format(clock_text(start, end, lang)),
                                                 where and at[lang]) if x)
        out["short"][lang] = f"{ORD[lang][n]} {DAY_ABBR['en'][wd] if lang == 'en' else DAY_NAME['es'][wd]} · {first}"
        out["mid"][lang] = " · ".join(x for x in (f"{ORD[lang][n]} {DAY_ABBR[lang][wd]} · {first}", where) if x)
    return out


# ----------------------------------------------------------------------------------------------------------------
# What each fixture must give, line by line (tests/fixtures/bingo_csv/*.csv — one kind of mistake per file)
# ----------------------------------------------------------------------------------------------------------------
ID_RULE = "use only a–z, 0–9 and dashes (no spaces or capitals), at most 48 characters"
DATE_RULE = "a date written YYYY-MM-DD, year 2000–2099 (Excel may have changed it: format the column as Text)"
TYPE_LIST = ", ".join(TYPES)
CAT_LIST = ", ".join(CATS)
WHERE_LIST = ", ".join(WHERES)
NOT_PLACEHOLDER = "is not a placeholder bingo knows (" + ", ".join(f"{{{p}}}" for p in PLACEHOLDERS) + ")"
BIG_GRIDS = "write the words for big grids (7×7 and up)"
LABEL_ONLY = "is only for name, phone, write and sign rows"
NOT_USED = "is not used on bingo cards —"
PHOTOS = f"{NOT_USED} {PHOTOS_WHY}"
NAMES = f"{NOT_USED} {NAMES_WHY}"
SAME = "a card could show the same square twice"
SAME_BIG = "a big card could show the same words twice"
EXPECTED: dict[str, tuple[list[str], list[str]]] = {   # fixture → (the ids it shows, its problem lines)
    "categories.csv": (["cat-caps", "info-ok"], [
        f"categories.csv row 2 (cat-empty): cat is empty ({CAT_LIST})",
        f'categories.csv row 3 (cat-unknown): cat "games" is not one of: {CAT_LIST} — a new category also needs its name '
        'in src/_i18n/bingo.json ("bingo.cat.games", in English and Spanish)',
        "categories.csv row 5 (info-wrong-cat): type info is only for cat meetings rows (an information square: our "
        "meetings, events and contact)",
        f'categories.csv row 7 (info-unknown-cat): cat "games" is not one of: {CAT_LIST} — a new category also needs its '
        'name in src/_i18n/bingo.json ("bingo.cat.games", in English and Spanish)',
    ]),
    # the same text, then the same big-grid words (short_*, else the text: what a 7×7 and up prints)
    "duplicates.csv": (["dup-first", "dup-after-bad", "short-first"], [
        f"duplicates.csv row 3 (dup-caps): text_en is the same as in row 2 (dup-first): {SAME}",
        f"duplicates.csv row 4 (dup-es): text_es is the same as in row 2 (dup-first): {SAME}",
        f'duplicates.csv row 6 (dup-bad): type "trivia" is not one of: {TYPE_LIST}',
        f"duplicates.csv row 8 (dup-en-only): text_en is the same as in row 2 (dup-first): {SAME}",
        f"duplicates.csv row 9 (dup-spaces): text_en is the same as in row 7 (dup-after-bad): {SAME}",
        f"duplicates.csv row 11 (short-caps): short_en is the same as in row 10 (short-first): {SAME_BIG}",
        f"duplicates.csv row 12 (short-is-text): short_en is the same as text_en in row 7 (dup-after-bad): {SAME_BIG}",
        f"duplicates.csv row 13 (text-is-short): text_en is the same as short_en in row 10 (short-first): {SAME_BIG}",
        f"duplicates.csv row 15 (short-es): short_es is the same as in row 10 (short-first): {SAME_BIG}",
    ]),
    "empty.csv": ([], ["empty.csv: the file is empty: the first row must be the header (id,on,type,…)"]),
    "fields.csv": (["people-alias", "fun-alias"], [
        'fields.csv row 4 (bad-on): on "maybe": write yes or no',
        'fields.csv row 5 (bad-pin): pin "always": write yes or no',
        f"fields.csv row 6 (bad-type-empty): type is empty ({TYPE_LIST})",
        f'fields.csv row 7 (bad-type): type "trivia" is not one of: {TYPE_LIST}',
        'fields.csv row 8 (bad-pub): pub "AA Grapevine": write gv, lv or both',
        f'fields.csv row 9 (bad-where): where: "home-group" is not one of: {WHERE_LIST}',
        f'fields.csv row 9 (bad-where): where: "zoom" is not one of: {WHERE_LIST}',
        'fields.csv row 10 (bad-weight): weight "0.25": a number from 0.5 to 5',
        'fields.csv row 11 (bad-weight-word): weight "six": a number from 0.5 to 5',
        'fields.csv row 12 (bad-weight-heavy): weight "5.5": a number from 0.5 to 5',
        f'fields.csv row 13 (bad-dates): from "3/1/2027": {DATE_RULE}',
        f'fields.csv row 13 (bad-dates): until "2027-02-30": {DATE_RULE}',
        "fields.csv row 14 (bad-order): until (2027-04-01) is before from (2027-05-01)",
        f'fields.csv row 15 (bad-year): from "0027-03-01": {DATE_RULE}',
        f'fields.csv row 15 (bad-year): until "2207-10-03": {DATE_RULE}',
        'fields.csv row 16 (bad-source): source_url "www.aagrapevine.org": not an https:// link',
        'fields.csv row 17 (bad-source-http): source_url "http://www.aagrapevine.org/": not an https:// link',
    ]),
    # a good file: every type, category and occasion, pins, weights, a dated row, a row switched off, a comment —
    # Fixtures.test_what_the_good_rows_become (and a pool other tests can build cards from: BINGO_CSV=…/good.csv)
    "good.csv": (["people-gvr-today", "people-trade-numbers", "people-came-farthest", "read-this-month",
                  "write-story-topic", "listen-lv-podcast", "service-why-serve", "meetings-gv-meeting",
                  "meetings-committee", "meetings-contact", "meetings-site", "history-first-gv", "fun-slogan",
                  "fun-anniversary-month"], []),
    "header-missing.csv": ([], [
        "header-missing.csv header: the header (first row) has no type column",
        "header-missing.csv header: the header (first row) has no cat column",
    ]),
    "header-twice.csv": (["fun-first"], [
        "header-twice.csv header: column text_en is in the header twice: the first one is used",
        "header-twice.csv header: column type is in the header twice: the first one is used",
    ]),
    "ids.csv": (["fun-ok"], [
        "ids.csv row 3: id is empty",
        f'ids.csv row 4 (Fun-Caps): id "Fun-Caps": {ID_RULE}',
        f'ids.csv row 5 (fun with spaces): id "fun with spaces": {ID_RULE}',
        f'ids.csv row 6 (fun--double): id "fun--double": {ID_RULE}',
        f'ids.csv row 7 (-fun-lead): id "-fun-lead": {ID_RULE}',
        f'ids.csv row 8 (fun-{"a" * 44}): id "fun-{"a" * 45}": {ID_RULE}',
        'ids.csv row 9 (fun-ok): id "fun-ok" is already used in row 2',
        "ids.csv row 14 (fun-off-bad): the row has no text in English or Spanish: fill in text_en, text_es or both",
    ]),
    "languages.csv": (["en-only", "es-only", "label-ok"], [
        "languages.csv row 2 (es-short-only): text_es is empty, but other Spanish cells are filled (short_es): fill it "
        "in, or empty them",
        "languages.csv row 3 (es-label-only): text_es is empty, but other Spanish cells are filled (label_es): fill it "
        "in, or empty them",
        "languages.csv row 6 (no-text): the row has no text in English or Spanish: fill in text_en, text_es or both",
        f"languages.csv row 7 (no-text-label): label_en {LABEL_ONLY}",
        "languages.csv row 7 (no-text-label): text_en is empty, but other English cells are filled (label_en): fill it "
        "in, or empty them",
        f"languages.csv row 8 (label-check): label_en {LABEL_ONLY}",
        f"languages.csv row 8 (label-check): label_es {LABEL_ONLY}",
        f"languages.csv row 9 (label-info): label_en {LABEL_ONLY}",
        "languages.csv row 11 (short-only): text_en is empty, but other English cells are filled (short_en): fill it "
        "in, or empty them",
        "languages.csv row 11 (short-only): text_es is empty, but other Spanish cells are filled (short_es): fill it "
        "in, or empty them",
    ]),
    "lengths.csv": (["len-text-90", "len-36-no-short", "len-emoji"], [
        "lengths.csv row 3 (len-text-91): text_en: 91 characters (90 at most)",
        f"lengths.csv row 5 (len-37-no-short): short_en is empty, but text_en has 37 characters (more than 36): {BIG_GRIDS}",
        "lengths.csv row 6 (len-short-37): short_en: 37 characters (36 at most)",
        "lengths.csv row 7 (len-label-25): label_en: 25 characters (24 at most)",
        "lengths.csv row 8 (len-placeholder): text_en: 94 characters (90 at most; each {…} counts as 20)",
        "lengths.csv row 9 (len-short-placeholder): short_en: 43 characters (36 at most; each {…} counts as 20)",
        f"lengths.csv row 10 (len-placeholder-no-short): short_en is empty, but text_en has 41 characters (more than "
        f"36): {BIG_GRIDS}",
    ]),
    "not-utf8.csv": (["fun-latin"], [
        "not-utf8.csv: the file is not saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)",
    ]),
    "placeholders.csv": (["ph-gv", "ph-committee", "ph-gv-weekly", "ph-lv-weekly", "ph-names", "ph-contact",
                          "ph-event"], [
        f"placeholders.csv row 9 (ph-unknown): text_en: {{Event}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 9 (ph-unknown): text_es: {{evento}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 10 (ph-twice): text_en: {{foo}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 10 (ph-twice): short_en: {{foo}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 10 (ph-twice): text_es: {{foo}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 10 (ph-twice): short_es: {{foo}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 11 (ph-label): label_en: {{name}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 11 (ph-label): label_es: {{nombre}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 12 (ph-empty): text_en: {{}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 12 (ph-empty): text_es: {{}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 13 (ph-dash): text_en: {{gv-meeting}} {NOT_PLACEHOLDER}",
        f"placeholders.csv row 13 (ph-dash): text_es: {{gv-meeting}} {NOT_PLACEHOLDER}",
    ]),
    # the pool tests/test_r34_bingo.py builds its pages from (BINGO_CSV): 48 rows copied from the real file in
    # November 2026 and three pinned squares whose words are markup — a good file, every row on the cards
    "pool.csv": (["people-gvr-today", "people-rlv-today", "people-phone-newcomer", "people-phone-other-district",
                  "people-drove-100-miles", "people-sign-committee", "read-this-month", "read-this-issue-lv",
                  "read-aloud-group", "read-language-heart", "read-issues-on-site", "read-talk-after", "write-topic",
                  "write-means-gv", "write-means-lv", "write-where-to-send", "write-recorder", "write-walls-room",
                  "listen-gv-podcast", "listen-lv-podcast", "listen-weekly-share", "listen-show-the-app",
                  "listen-quote-line", "listen-youtube", "service-elect-gvr", "service-elect-rlv",
                  "service-announce-theme", "service-lit-table", "service-old-issues", "service-ctm-explain",
                  "meetings-gv-meeting", "meetings-committee", "meetings-contact", "meetings-site-events",
                  "meetings-find-gv-meeting", "meetings-ask-workshop", "history-gv-began", "history-gv-founders",
                  "history-man-on-bed", "history-lv-began", "history-gvr-1962", "history-tables-1978", "fun-slogan",
                  "fun-birthday-month", "fun-purple", "fun-made-you-smile", "fun-new-friend", "fun-lv-30",
                  "fun-markup-script", "fun-markup-at", "fun-markup-entity"], []),
    "structure.csv": (["fun-ok", "fun-multi"], [
        'structure.csv row 8: a cell starts with a double quote (") that is never closed: everything after it was read '
        "as that one cell",
        "structure.csv row 3 (fun-comma): the row has 6 cells but the header has 5: a comma inside a text needs the whole "
        "cell in double quotes",
        f"structure.csv row 8 (fun-unclosed): short_en is empty, but text_en has 81 characters (more than 36): {BIG_GRIDS}",
    ]),
    "words.csv": (["w-today-event", "w-ok-cover", "w-ok-book", "w-ok-first-name", "w-ok-notes"], [
        f"words.csv row 2 (w-pdf): text_en: “PDF” {NOT_USED} say “document” instead",
        f"words.csv row 3 (w-donate): text_en: “donate” {NOT_USED} Grapevine and La Viña take no donations (say “Carry "
        "the Message gift”)",
        f"words.csv row 4 (w-donativo): text_es: “donativo” {NOT_USED} Grapevine and La Viña take no donations (say "
        "“Carry the Message gift”)",
        f"words.csv row 5 (w-sales): text_en: “Subscribe today” {NOT_USED} no sales or urgency words: attraction, not "
        "promotion",
        f"words.csv row 6 (w-today): text_en: “Today only” {NOT_USED} “today only” needs {{event}} (the booth shows the "
        "same rows on many days)",
        f"words.csv row 8 (w-selfie): text_en: “selfie” {PHOTOS}",
        f"words.csv row 8 (w-selfie): text_es: “selfi” {PHOTOS}",
        f"words.csv row 9 (w-photo-sponsor): text_en: “photo of your sponsor” {PHOTOS}",
        f"words.csv row 9 (w-photo-sponsor): text_es: “foto de tu padrino” {PHOTOS}",
        f"words.csv row 10 (w-picture-with): text_en: “picture with someone” {PHOTOS}",
        f"words.csv row 10 (w-picture-with): text_es: “foto con alguien” {PHOTOS}",
        f"words.csv row 11 (w-group-photo): text_en: “group photo” {PHOTOS}",
        f"words.csv row 11 (w-group-photo): text_es: “foto grupal” {PHOTOS}",
        f"words.csv row 12 (w-photo-you): text_en: “snapshot of yourself” {PHOTOS}",
        f"words.csv row 12 (w-photo-you): text_es: “foto con él” {PHOTOS}",
        f"words.csv row 13 (w-last-name): text_en: “last name” {NAMES}",
        f"words.csv row 13 (w-last-name): label_en: “Full name” {NAMES}",
        f"words.csv row 13 (w-last-name): text_es: “apellido” {NAMES}",
        f"words.csv row 13 (w-last-name): label_es: “Nombre completo” {NAMES}",
        f"words.csv row 14 (w-lastname): text_en: “lastname” {NAMES}",
        f"words.csv row 14 (w-lastname): label_en: “Surname” {NAMES}",
        f"words.csv row 14 (w-lastname): text_es: “apellidos” {NAMES}",
        f"words.csv row 14 (w-lastname): label_es: “Nombres completos” {NAMES}",
        f"words.csv row 15 (w-two-hits): text_en: “PDF” {NOT_USED} say “document” instead",
        f"words.csv row 15 (w-two-hits): text_en: “selfie” {PHOTOS}",
        f"words.csv row 15 (w-two-hits): text_es: “autofoto” {PHOTOS}",
    ]),
}

# Cases held in the test itself: what a repository's line ends cannot keep (CRLF, a BOM before the header, a lone CR),
# and the shapes of the items
INLINE: dict[str, str] = {
    "crlf-bom.csv": "﻿id,on,type,cat,text_en,text_es\r\n"
                    'people-hello,yes,check,people,"Say hello\r\nto someone new","Saluda a\r\nalguien nuevo"\r\n'
                    "#note,,,,,\r\n\r\n",
    "cr-only.csv": "id,type,cat,text_en\rfun-cr,check,fun,Hum a tune\r",
    "shapes.csv": "id,type,pub,cat,where,pin,weight,from,until,text_en,short_en,label_en,text_es,short_es,label_es\n"
                  'read-favorite,write,lv,read,"booth; Booth, online",yes,"1,5",2027-01-01,2027-01-31,'
                  "Your favorite story in this month's issue,Favorite story this month,Story,"
                  "Tu historia favorita del número de este mes,Tu historia favorita,Historia\n"
                  "people-es-only,name,,people,,,,,,,,,Encuentra a alguien de otro distrito,Alguien de otro distrito,\n"
                  "fun-short-is-text,check,gv,fun,,no,,,,Hum a tune,,,Tararea una melodía,,\n",
}
ITEM_KEYS = ["id", "type", "pub", "cat", "where", "pin", "weight", "from", "until", "text", "short", "label"]


def _main(argv: list[str]) -> int:
    """`python tests/test_bingo_csv.py file.csv …` — each file's squares and its problems (exit 1 with any)."""
    bad = 0
    for path in (Path(a) for a in argv):
        checked = check_file(path)
        print(f"{path}: {len(checked.items)} square(s) on the cards, {len(checked.problems)} problem(s)")
        for p in checked.problems:
            print(f"  {p}")
        bad += len(checked.problems)
    return 1 if bad else 0


# ----------------------------------------------------------------------------------------------------------------
# The tests
# ----------------------------------------------------------------------------------------------------------------
class Real(unittest.TestCase):
    """content/bingo/bingo.csv, the file the committee edits (a CONTENT test: scripts/ops/gate_tests.py)."""

    @classmethod
    def setUpClass(cls):
        cls.text = read_csv_file(CSV_FILE)
        cls.checked = check_bingo_csv(cls.text, cat_names=i18n_cat_names())
        cls.items = cls.checked.items
        cls.rows, _ = parse_csv(cls.text)

    def test_no_problem_at_all(self):
        self.assertEqual(self.checked.problems, [], "fix these rows in content/bingo/bingo.csv (content/bingo/README.md says how)")

    def test_utf8_with_the_header_first(self):
        CSV_FILE.read_bytes().decode("utf-8")   # strict: never a byte that is not UTF-8
        # every column bingo reads is there (in any order: a column of the committee's own may be added anywhere)
        header = [one_line(h).lower() for h in self.rows[0]]
        self.assertEqual([c for c in COLUMNS if c not in header], [], "columns missing from the header")

    def test_a_large_pool(self):
        self.assertGreaterEqual(len(self.items), 200, "at least 200 squares that are on")
        ids = [i["id"] for i in self.items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_both_languages_on_every_row(self):
        """Every row of the file — one switched off too, ready to switch on — in English and in Spanish: a card's
        language is the GVR's choice, never the row's."""
        head = [one_line(h).lower() for h in self.rows[0]]
        col = {k: head.index(k) for k in ("id", "text_en", "text_es")}
        missing = []
        for n, cells in enumerate(self.rows[1:], 2):
            cell = lambda k: one_line(cells[col[k]]) if col[k] < len(cells) else ""  # noqa: E731
            if any(one_line(c) for c in cells) and not cell("id").startswith("#") and not (cell("text_en") and cell("text_es")):
                missing.append(f"row {n} ({cell('id')})")
        self.assertEqual(missing, [], "these rows need text_en and text_es")
        for it in self.items:
            self.assertTrue(it["text"]["en"] and it["text"]["es"], it["id"])

    def test_enough_squares_for_a_10x10_card(self):
        """A 10×10 card (100 squares, no free square) in either language with each magazine filter — counting only
        the squares offered on every day (no from / until) and no information square (the builder caps those)."""
        for lang in LANGS:
            for magazine, pubs in MAGAZINES.items():
                with self.subTest(lang=lang, magazine=magazine):
                    usable = [i for i in self.items if i["text"][lang] and i["pub"] in pubs and i["type"] != "info"
                              and not i["from"] and not i["until"]]
                    self.assertGreaterEqual(len(usable), 100)

    def test_enough_squares_wherever_a_gvr_takes_it(self):
        """The default card (5×5 with its free square: 24 squares) for each occasion of "Where are you taking it?",
        in either language with each magazine filter (a blank where = everywhere)."""
        for where in WHERES:
            for lang in LANGS:
                for magazine, pubs in MAGAZINES.items():
                    with self.subTest(where=where, lang=lang, magazine=magazine):
                        usable = [i for i in self.items if i["text"][lang] and i["pub"] in pubs and i["type"] != "info"
                                  and not i["from"] and not i["until"] and (not i["where"] or where in i["where"])]
                        self.assertGreaterEqual(len(usable), 24)

    def test_every_category_occasion_and_type_is_used(self):
        self.assertEqual([c for c in CATS if not any(i["cat"] == c for i in self.items)], [], "categories with no square")
        self.assertEqual([w for w in WHERES if not any(w in i["where"] for i in self.items)], [], "occasions no square names")
        self.assertEqual([t for t in TYPES if not any(i["type"] == t for i in self.items)], [], "types with no square")

    def test_the_meetings_and_the_contact_on_every_card(self):
        """The owner's ask: every card says when and where our Grapevine Meeting and committee meeting are, and how to
        reach us — three information squares pinned ("Always on every card"), in both languages."""
        for mark in ("{gv_meeting}", "{committee_meeting}", "{email}"):
            with self.subTest(mark=mark):
                found = [i["id"] for i in self.items if i["type"] == "info" and i["cat"] == INFO_CAT and i["pin"]
                         and mark in i["text"]["en"] and mark in i["text"]["es"]]
                self.assertTrue(found, f"a pinned info square with {mark} in text_en and text_es")

    def test_big_grids_use_the_short_meeting_lines(self):
        """short_* is what a 7×7 to 10×10 card prints: a meeting there is {gv_meeting_short} /
        {committee_meeting_short} ("1st Wed · 7 PM") or, for the weekly open meetings, {gv_weekly_short} /
        {lv_weekly_short} ("Wed 11 AM · Zoom"), never the whole line."""
        self.assertEqual([p for p in [*SHORT_OF, *SHORT_OF.values()] if p not in PLACEHOLDERS], [])
        long_marks = [f"{{{m}}}" for m in SHORT_OF]
        self.assertEqual([i["id"] for i in self.items if any(m in i["short"][lang] for m in long_marks for lang in LANGS)], [])

    def test_the_build_fills_every_square(self):
        """The build fills in every placeholder but {event} from config/site.yml and the day's weekly open meetings
        (data/site/weekly_open.json) — no square left out for a meeting line it cannot write (bingo.js fillItems). A
        DATA test too (scripts/ops/gate_tests.py): the weekly meetings are the sync's."""
        res = run_js(self, """
            const B = await imp("eleventy/filters/bingo.js");
            const site = (await imp("src/_data/site.js")).default();
            const r = B.loadBingo({ site });
            out({ found: r.found, problems: r.problems.map((p) => `${p.where}: ${p.en}`), ids: r.items.map((i) => i.id),
                  info: r.info, texts: r.items.flatMap((i) => ["text", "short", "label"].flatMap((f) => [i[f].en, i[f].es])) });
        """)
        self.assertTrue(res["found"])
        self.assertEqual(res["problems"], [], "the cards leave these squares out")
        self.assertEqual(res["ids"], [i["id"] for i in self.items])
        for key in ("gvMeeting", "gvMeetingMid", "gvMeetingShort", "committeeMeeting", "committeeMeetingMid",
                    "committeeMeetingShort"):
            self.assertTrue(res["info"][key] and res["info"][key]["en"] and res["info"][key]["es"], key)
        self.assertTrue(res["info"]["email"])
        left = sorted({m for t in res["texts"] for m in MARK.findall(t)} - {"event"})
        self.assertEqual(left, [], "placeholders the build did not fill in")

    def test_the_meeting_lines_say_when_and_where(self):
        """The owner's ask, in the words the cards print: our Grapevine Meeting and the committee meeting — the day,
        the time range, the zone and where — worked out from config/site.yml as it is (no time written here), in the
        long, mid and short lines of both languages; and the shape of each line."""
        import yaml   # (as test_booth_csv reads the settings)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.sync.events_external import platform_of   # the sync's twin of committee.js platformOf

        cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))

        def rule(o: dict, defaults: dict) -> tuple[int, str, str, str]:
            """A meeting's rule as monthlyRule reads it, for the shapes config/site.yml uses: its end one hour after
            the start when it is missing or not after it (an overnight end stays)."""
            o = {**defaults, **{k: v for k, v in o.items() if v not in (None, "")}}
            start, end = str(o["start"]), str(o.get("end") or "")
            a = int(start[:2]) * 60 + int(start[3:])
            b = int(end[:2]) * 60 + int(end[3:]) if end else -1
            if b <= a and not (0 <= b < a and 24 * 60 - a + b <= 12 * 60):
                end = f"{min(a // 60 + 1, 23):02d}:{a % 60 if a // 60 < 23 else 59:02d}"
            return int(o["week_of_month"]), str(o["weekday"]).lower(), start, end

        cm = cfg["meeting"]
        gv = next(e for e in cfg["recurring_events"] if e.get("key") == "grapevine-meeting" and e.get("enabled") is not False)
        gv_platform = platform_of(gv.get("online_url"))
        want = {
            "committee": meeting_lines(*rule(cm, {"week_of_month": 3, "weekday": "wednesday", "start": "19:00"}),
                                       cm.get("platform") or "Zoom"),
            "gv": meeting_lines(*rule(gv, {}), gv_platform or str(gv.get("location") or "").split(",")[0].strip(),
                                place=not gv_platform),
        }
        res = run_js(self, """
            const B = await imp("eleventy/filters/bingo.js");
            const site = (await imp("src/_data/site.js")).default();
            out(B.bingoInfo(site, []));
        """)
        for who, prefix in (("gv", "gvMeeting"), ("committee", "committeeMeeting")):
            for form, key in (("long", prefix), ("mid", prefix + "Mid"), ("short", prefix + "Short")):
                with self.subTest(meeting=who, line=form):
                    self.assertEqual({k: plain(v) for k, v in (res[key] or {}).items()}, want[who][form])
        # the shapes: the long line names the day of the month, the time range, the zone and the platform
        days = {lang: "|".join(DAY_NAME[lang]) for lang in LANGS}
        clock = r"\d{1,2}(?::\d\d)?"
        en_m, es_m = r"[AP]M", r"[ap]\. m\."
        where = {"gv": gv_platform or "", "committee": cm.get("platform") or "Zoom"}
        for who, prefix in (("gv", "gvMeeting"), ("committee", "committeeMeeting")):
            with self.subTest(meeting=who):
                got = {form: {k: plain(v) for k, v in res[prefix + suffix].items()}
                       for form, suffix in (("long", ""), ("mid", "Mid"), ("short", "Short"))}
                self.assertRegex(got["long"]["en"], rf"\A(?:1st|2nd|3rd|4th|5th|last) (?:{days['en']}) of the month, "
                                 rf"{clock}(?: {en_m})? – {clock} {en_m} Central, \S")
                self.assertRegex(got["long"]["es"], rf"\Acada (?:primer|segundo|tercer|cuarto|quinto|último) "
                                 rf"(?:{days['es']}) del mes, {clock}(?: {es_m} – |–){clock} {es_m} \(hora del Centro\), "
                                 r"(?:por|en) \S")
                self.assertRegex(got["mid"]["en"], rf"\A\S+ (?:{'|'.join(DAY_ABBR['en'])}) · {clock} {en_m} · \S")
                self.assertRegex(got["short"]["es"], rf"\A\S+ (?:{days['es']}) · {clock} {es_m}\Z")
                if where[who]:
                    self.assertTrue(got["long"]["en"].endswith(f", {where[who]}"), got["long"]["en"])
                    self.assertTrue(got["long"]["es"].endswith(f", por {where[who]}"), got["long"]["es"])
                    self.assertTrue(all(got["mid"][lang].endswith(f" · {where[who]}") for lang in LANGS), got["mid"])


class Fixtures(unittest.TestCase):
    """tests/fixtures/bingo_csv: each file's squares and its problems, line by line."""

    def test_every_fixture_is_listed(self):
        self.assertEqual(sorted(f.name for f in FIXTURES.glob("*.csv")), sorted(EXPECTED))

    def test_each_fixture_line_by_line(self):
        for name, (ids, lines) in EXPECTED.items():
            with self.subTest(fixture=name):
                checked = check_file(FIXTURES / name, cat_names=[])
                self.assertEqual(checked.problems, lines)
                self.assertEqual([i["id"] for i in checked.items], ids)

    def test_what_the_good_rows_become(self):
        good = check_file(FIXTURES / "good.csv", cat_names=[])
        items = {i["id"]: i for i in good.items}
        self.assertEqual(good.rows, 16)
        self.assertEqual(good.row_of["people-gvr-today"], 2)
        self.assertEqual(items["people-came-farthest"], {
            "id": "people-came-farthest", "type": "name", "pub": "both", "cat": "people",
            "where": ["assembly", "acm", "workshop", "booth"], "pin": False, "weight": 1.5, "from": None, "until": None,
            "text": {"en": "Find who came the farthest to {event}", "es": "Encuentra a quien vino de más lejos a {event}"},
            "short": {"en": "Who came the farthest?", "es": "¿Quién vino de más lejos?"},
            "label": {"en": "Name & town", "es": "Nombre y ciudad"},
        })
        self.assertEqual(items["meetings-gv-meeting"], {
            "id": "meetings-gv-meeting", "type": "info", "pub": "gv", "cat": "meetings", "where": [], "pin": True,
            "weight": 1, "from": None, "until": None,
            "text": {"en": "Our Grapevine Meeting: {gv_meeting}", "es": "Nuestra Reunión de Grapevine (en inglés): {gv_meeting}"},
            "short": {"en": "GV Meeting: {gv_meeting_short}", "es": "Reunión de GV: {gv_meeting_short}"},
            "label": {"en": "", "es": ""},
        })
        self.assertEqual((items["read-this-month"]["weight"], items["listen-lv-podcast"]["weight"]), (2.5, 0.5))
        self.assertEqual(items["read-this-month"]["text"]["en"], "Read a story from this month's issue: your one favorite?")
        self.assertEqual((items["fun-anniversary-month"]["from"], items["fun-anniversary-month"]["until"]), ("2026-11-01", "2027-12-31"))
        self.assertEqual(items["fun-slogan"]["short"], items["fun-slogan"]["text"], "no short_*: the text itself")
        self.assertEqual(items["people-trade-numbers"]["pub"], "both", "pub blank = both")
        self.assertEqual(items["service-why-serve"]["where"], ["group", "district", "committee"])
        self.assertNotIn("fun-off", items)
        self.assertEqual(sorted({i["type"] for i in good.items}), sorted(TYPES))
        self.assertEqual(sorted({i["cat"] for i in good.items}), sorted(CATS))
        self.assertEqual(sorted({w for i in good.items for w in i["where"]}), sorted(WHERES))
        # the spellings a spreadsheet may have: capitals, "Sí", "Y", "1,5", the magazine's name, "GV & LV", where lists
        alias = {i["id"]: i for i in check_file(FIXTURES / "fields.csv", cat_names=[]).items}
        self.assertEqual({k: alias["people-alias"][k] for k in ("type", "pub", "cat", "where", "pin", "weight", "from", "until")},
                         {"type": "name", "pub": "gv", "cat": "people", "where": ["group", "acm", "booth"], "pin": True,
                          "weight": 1.5, "from": "2027-03-01", "until": "2027-03-15"})
        self.assertEqual({k: alias["fun-alias"][k] for k in ("type", "pub", "pin", "weight")},
                         {"type": "check", "pub": "both", "pin": False, "weight": 5})
        # the lengths: characters as a person counts them — 90 / 36 exactly, "ñ" and an emoji one each
        lengths = {i["id"]: i for i in check_file(FIXTURES / "lengths.csv", cat_names=[]).items}
        self.assertEqual((len(lengths["len-text-90"]["text"]["en"]), len(lengths["len-text-90"]["text"]["es"])), (90, 90))
        self.assertEqual(len(lengths["len-emoji"]["text"]["en"]), 36)
        # a cell in quotes keeps its commas and quotes; a line break inside is one space
        structure = {i["id"]: i for i in check_file(FIXTURES / "structure.csv", cat_names=[]).items}
        self.assertEqual(structure["fun-ok"]["text"], {"en": 'Say "hi", with a comma in quotes', "es": 'Di "hola", con una coma'})
        self.assertEqual(structure["fun-multi"]["text"]["en"], "Line one Line two")


class Rules(unittest.TestCase):
    """Rules best shown with a few lines of CSV."""

    def check(self, body: str, header: str = "id,on,type,cat,text_en,text_es", cat_names=()) -> Checked:
        return check_bingo_csv(header + "\n" + body + "\n", file="t.csv", cat_names=cat_names)

    def test_crlf_bom_and_line_breaks_in_quotes(self):
        checked = check_bingo_csv(INLINE["crlf-bom.csv"], file="crlf-bom.csv")
        self.assertEqual(checked.problems, [])
        self.assertEqual(checked.items[0]["text"], {"en": "Say hello to someone new", "es": "Saluda a alguien nuevo"})
        self.assertEqual(check_bingo_csv(INLINE["cr-only.csv"], file="cr-only.csv").items[0]["id"], "fun-cr")

    def test_the_item_shape(self):
        checked = check_bingo_csv(INLINE["shapes.csv"], file="shapes.csv")
        self.assertEqual(checked.problems, [])
        fav, es_only, plain = checked.items
        self.assertEqual(list(fav), ITEM_KEYS)
        self.assertEqual(fav, {
            "id": "read-favorite", "type": "write", "pub": "lv", "cat": "read", "where": ["booth", "online"], "pin": True,
            "weight": 1.5, "from": "2027-01-01", "until": "2027-01-31",
            "text": {"en": "Your favorite story in this month's issue", "es": "Tu historia favorita del número de este mes"},
            "short": {"en": "Favorite story this month", "es": "Tu historia favorita"},
            "label": {"en": "Story", "es": "Historia"},
        })
        # a language the row is not offered in: "" in text, short and label
        self.assertEqual((es_only["text"], es_only["short"], es_only["label"]),
                         ({"en": "", "es": "Encuentra a alguien de otro distrito"}, {"en": "", "es": "Alguien de otro distrito"},
                          {"en": "", "es": ""}))
        self.assertEqual((es_only["pub"], es_only["where"], es_only["pin"], es_only["weight"]), ("both", [], False, 1))
        self.assertEqual(plain["short"], {"en": "Hum a tune", "es": "Tararea una melodía"})
        self.assertEqual(checked.row_of, {"read-favorite": 2, "people-es-only": 3, "fun-short-is-text": 4})

    def test_a_row_switched_off_is_checked_but_not_shown(self):
        checked = self.check("a,yes,check,fun,Shown,Se ve\nb,no,check,fun,Off,Apagada\nc,no,check,fun,,")
        self.assertEqual([i["id"] for i in checked.items], ["a"])
        self.assertEqual(checked.problems, ["t.csv row 4 (c): the row has no text in English or Spanish: fill in text_en, text_es or both"])

    def test_a_new_category_needs_its_words(self):
        """A category outside the eight is fine once src/_i18n/bingo.json names it (bingo.cat.<cat> in English and
        Spanish: cat_names_of); without them the line says what to add."""
        body = "games-1,,check,Games,Play a game,Juega"
        self.assertEqual(self.check(body).problems, [
            f't.csv row 2 (games-1): cat "Games" is not one of: {CAT_LIST} — a new category also needs its name in '
            'src/_i18n/bingo.json ("bingo.cat.games", in English and Spanish)'])
        names = cat_names_of({"bingo.cat.games": {"en": "Games", "es": "Juegos"}, "bingo.cat.half": {"en": "Half", "es": " "},
                              "bingo.cat.Bad": {"en": "x", "es": "y"}, "bingo.title": {"en": "x", "es": "y"},
                              "bingo.cat.list": ["x"]})
        self.assertEqual(names, ["games"])
        self.assertEqual(self.check(body, cat_names=names).items[0]["cat"], "games")
        self.assertEqual(cat_names_of(None), [])

    def test_placeholders_stay_as_written(self):
        checked = self.check("m,,info,meetings,Write to us: {email},Escríbenos: {email}\n"
                             "e,,name,people,A GVR at {event},Un RLV en {event}")
        self.assertEqual(checked.problems, [])
        self.assertEqual([i["text"]["en"] for i in checked.items], ["Write to us: {email}", "A GVR at {event}"])

    def test_the_lengths_count_like_a_person(self):
        self.assertEqual([measure(s) for s in ("", "ñandú", "{event}", "a{b}c", "{}", "{x} y {z}", "🎵")], [0, 5, 20, 22, 20, 43, 1])

    def test_the_refused_words_name_people_not_things(self):
        refused = ["Take a selfie", "una selfi", "a photo of your sponsor", "pictures with the newcomers", "a group photo",
                   "una foto de tu padrino", "fotos con los recién llegados", "una foto con él", "foto de mí",
                   "their last name", "Full names", "family name", "your surname", "su apellido", "nombre completo"]
        fine = ["a picture of the first cover", "una foto de mi libro", "a photo of the table", "una foto de la mesa",
                "your first name", "tu nombre de pila", "the photographer's story", "a pic of a sunset", "el nombre del grupo"]
        for s in refused:
            with self.subTest(refused=s):
                self.assertTrue(bingo_refused_in(s))
        for s in fine:
            with self.subTest(fine=s):
                self.assertEqual(bingo_refused_in(s), [])


class Twin(unittest.TestCase):
    """The build's checker (eleventy/filters/bingo.js checkBingoCsv) gives the same lines, items, rows and row numbers as
    this one — for every fixture, the inline cases and the real file — and a Spanish line for every problem; the
    constants, lengths, refused words and categories are the same too."""

    def test_the_same_lines_and_items(self):
        real_cats = i18n_cat_names()
        cases = [{"name": f.name, "text": read_csv_file(f), "cats": []} for f in sorted(FIXTURES.glob("*.csv"))]
        cases += [{"name": n, "text": t, "cats": []} for n, t in INLINE.items()]
        cases.append({"name": "categories.csv", "text": read_csv_file(FIXTURES / "categories.csv"), "cats": ["games"]})
        cases.append({"name": CSV_FILE.name, "text": read_csv_file(CSV_FILE), "cats": real_cats})
        res = run_js(self, """
            const B = await imp("eleventy/filters/bingo.js");
            out(input.cases.map((c) => {
              const r = B.checkBingoCsv(c.text, { file: c.name, catNames: c.cats });
              return { items: r.items, rows: r.rows, rowOf: r.rowOf,
                       lines: r.problems.map((p) => `${p.where}: ${p.en}`), es: r.problems.map((p) => p.es) };
            }));
        """, data={"cases": cases})
        self.assertEqual(len(res), len(cases))
        for c, js in zip(cases, res):
            with self.subTest(file=c["name"], cats=c["cats"]):
                py = check_bingo_csv(c["text"], file=c["name"], cat_names=c["cats"])
                self.assertEqual(js["lines"], py.problems)
                self.assertEqual(js["items"], py.items)
                self.assertEqual([list(i) for i in js["items"]], [list(i) for i in py.items], "the keys in the same order")
                self.assertEqual((js["rows"], js["rowOf"]), (py.rows, py.row_of))
                for en_line, es in zip(js["lines"], js["es"]):
                    self.assertTrue(es.strip(), en_line)
                    self.assertNotEqual(es, en_line.split(": ", 1)[1], "the Spanish line is a translation")

    def test_the_same_rules(self):
        strings = ["", "ñandú", "{event}", "a{b}c", "{}", "{x} y {z}", "🎵 {email}", "Take a selfie with the PDF",
                   "a photo of your sponsor", "una foto de mi libro", "foto de mí", "Nombre y apellido", "your last name",
                   "a group photo", "una foto grupal", "nombre completo", "Today only",
                   "Today only at {event}", "Subscribe today: donate", "pictures with each other", "un servidor"]
        i18n = [None, [], {"bingo.cat.games": {"en": "Games", "es": "Juegos"}}, {"bingo.cat.half": {"en": "Half", "es": ""}},
                {"bingo.cat.Bad": {"en": "x", "es": "y"}, "bingo.cat.two-words": {"en": 1, "es": True}}]
        if I18N_FILE.is_file():
            i18n.append(json.loads(I18N_FILE.read_text(encoding="utf-8")))
        res = run_js(self, """
            const B = await imp("eleventy/filters/bingo.js");
            out({ COLUMNS: B.COLUMNS, TYPES: B.TYPES, LABEL_TYPES: B.LABEL_TYPES, CATS: B.CATS, INFO_CAT: B.INFO_CAT,
                  WHERES: B.WHERES, PLACEHOLDERS: B.PLACEHOLDERS, LIMITS: B.LIMITS,
                  measure: input.strings.map((s) => B.measure(s)),
                  refused: input.strings.map((s) => B.bingoRefusedIn(s).map((h) => [h.word, h.en])),
                  cats: input.i18n.map((j) => B.catNamesOf(j)) });
        """, data={"strings": strings, "i18n": i18n})
        self.assertEqual({k: res[k] for k in ("COLUMNS", "TYPES", "LABEL_TYPES", "CATS", "INFO_CAT", "WHERES", "PLACEHOLDERS", "LIMITS")},
                         {"COLUMNS": COLUMNS, "TYPES": TYPES, "LABEL_TYPES": LABEL_TYPES, "CATS": CATS, "INFO_CAT": INFO_CAT,
                          "WHERES": WHERES, "PLACEHOLDERS": PLACEHOLDERS, "LIMITS": LIMITS})
        self.assertEqual(res["measure"], [measure(s) for s in strings])
        self.assertEqual(res["refused"], [[list(h) for h in bingo_refused_in(s)] for s in strings])
        self.assertEqual(res["cats"], [cat_names_of(j) for j in i18n])


class Info(unittest.TestCase):
    """The meeting lines bingo.js bingoInfo writes from fixed settings and data. The monthly meetings (our Grapevine
    Meeting, the committee meeting): test_the_monthly_meeting_lines. The weekly open meetings' words for big grids,
    {gv_weekly_short} / {lv_weekly_short}: the day and the start time of the next meeting on Central's clock — Noon
    Eastern is 11 AM; half past midnight Eastern is still the evening before — and the platform. None without a next
    start in the data, or with La Viña's meeting switched off (config/site.yml lavina_weekly_open); the long line
    ({gv_weekly}) stays the data's own "when", then the platform ("por Zoom" in Spanish). In every line an hour and
    its AM / PM never go on two lines (clock_split)."""

    @staticmethod
    def meeting(lv: bool, next_start: str | None, when_en: str, when_es: str) -> dict:
        """A data/site/weekly_open.json item, as the daily update writes it (only what the cards read)."""
        extra = {"zoom_id": "871 2036 8287", "timezone": "America/New_York"}
        if next_start:
            extra["next_start"] = next_start
        return {"id": "weekly_open_lv" if lv else "weekly_open", "source": "lavina" if lv else "grapevine",
                "kind": "meeting", "lang": "es" if lv else "en", "status": "ok", "extra": extra,
                "i18n": {"when": {"en": when_en, "es": when_es}}}

    def test_the_weekly_short_words(self):
        gv_when = ("Wednesdays at 11:00 AM Central", "Los miércoles a las 11:00 a. m. (hora del Centro)")
        noon = [self.meeting(False, "2099-10-21T16:00:00Z", *gv_when),
                self.meeting(True, "2099-10-22T16:00:00Z", "Thursdays at 11:00 AM Central",
                             "Los jueves a las 11:00 a. m. (hora del Centro)")]
        late = [self.meeting(False, "2099-10-22T04:30:00Z", "Wednesdays at 11:30 PM Central",
                             "Los miércoles a las 11:30 p. m. (hora del Centro)")]
        cases = [{"site": {}, "weekly": {"items": noon}}, {"site": {}, "weekly": late},
                 {"site": {}, "weekly": [self.meeting(False, None, *gv_when)]},
                 {"site": {"lavina_weekly_open": {"enabled": False}}, "weekly": noon}]
        res = run_js(self, """
            const B = await imp("eleventy/filters/bingo.js");
            out(input.cases.map((c) => {
              const i = B.bingoInfo(c.site, c.weekly);
              return [i.gvWeekly, i.gvWeeklyShort, i.lvWeekly, i.lvWeeklyShort];
            }));
        """, data={"cases": cases})

        self.assertEqual(clock_split([v for r in res for v in r]), [], "an hour and its AM / PM free to go on two lines")
        got = [[v and {k: plain(x) for k, x in v.items()} for v in r] for r in res]
        gv_long = {"en": "Wednesdays at 11:00 AM Central, Zoom", "es": "los miércoles a las 11:00 a. m. (hora del Centro), por Zoom"}
        self.assertEqual(got[0], [gv_long, {"en": "Wed 11 AM · Zoom", "es": "mié. 11 a. m. · Zoom"},
                                  {"en": "Thursdays at 11:00 AM Central, Zoom",
                                   "es": "los jueves a las 11:00 a. m. (hora del Centro), por Zoom"},
                                  {"en": "Thu 11 AM · Zoom", "es": "jue. 11 a. m. · Zoom"}])
        self.assertEqual(got[1][1], {"en": "Wed 11:30 PM · Zoom", "es": "mié. 11:30 p. m. · Zoom"})
        self.assertEqual(got[1][2:], [None, None], "no La Viña meeting in the data")
        self.assertEqual(got[2][:2], [gv_long, None], "no next start: no big-grid words")
        self.assertEqual(got[3][2:], [None, None], "La Viña's meeting switched off")
        self.assertEqual(got[3][1], got[0][1])

    def test_the_monthly_meeting_lines(self):
        """Our Grapevine Meeting and the committee meeting, from fixed settings — the owner's ask: when and where. The
        long line (squares up to 6×6, the strip when it fits) names the day, the time range, the zone and the platform
        ("por" before it in Spanish, "en" before a place); the mid one (the strip on a small card) the day, the start
        and the platform; the short one (big grids' squares) the day and the start. The minutes only when there are
        some, an overnight meeting's end the next morning, a meeting the settings lack or switch off none."""
        gv = {"key": "grapevine-meeting", "title": "Grapevine Meeting"}
        cases = [
            {"meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet"},
             "recurring_events": [{"key": "other", "week_of_month": 2, "weekday": "saturday", "start": "17:00"},
                                  {**gv, "week_of_month": 1, "weekday": "wednesday", "start": "19:00", "end": "20:00",
                                   "online_url": "https://meet.google.com/abc-defg-hij"}]},
            {"meeting": {"week_of_month": -1, "weekday": "friday", "start": "07:30", "end": "09:00"},
             "recurring_events": {**gv, "week_of_month": "last", "weekday": "Saturdays", "start": "09:00", "end": "10:30",
                                  "location": "Rowlett Public Library, 3900 Main St"}},
            {"meeting": {"week_of_month": 2, "weekday": "saturday", "start": "22:00", "end": "01:00", "platform": "Zoom"},
             "recurring_events": [{**gv, "week_of_month": 4, "weekday": "monday", "start": "11:30", "end": "12:30",
                                   "online_url": "https://us02web.zoom.us/j/123"}]},
            {"meeting": {"start": "18:00"},
             "recurring_events": [{**gv, "enabled": False, "week_of_month": 1, "weekday": "wednesday", "start": "19:00"}]},
            {},
            {"meeting": {}, "recurring_events": [{**gv, "weekday": "wednesday", "start": "19:00"}]},
        ]
        keys = ["gvMeeting", "gvMeetingMid", "gvMeetingShort", "committeeMeeting", "committeeMeetingMid", "committeeMeetingShort"]
        res = run_js(self, """
            const B = await imp("eleventy/filters/bingo.js");
            out(input.cases.map((c) => { const i = B.bingoInfo(c, []); return input.keys.map((k) => i[k]); }));
        """, data={"cases": cases, "keys": keys})
        self.assertEqual(clock_split([v for r in res for v in r]), [], "an hour and its AM / PM free to go on two lines")
        got = [dict(zip(keys, ({k: plain(s) for k, s in v.items()} if v else v for v in r))) for r in res]

        def lines(gv_lines: dict | None, cm_lines: dict | None) -> dict:
            return {"gvMeeting": gv_lines and gv_lines["long"], "gvMeetingMid": gv_lines and gv_lines["mid"],
                    "gvMeetingShort": gv_lines and gv_lines["short"], "committeeMeeting": cm_lines and cm_lines["long"],
                    "committeeMeetingMid": cm_lines and cm_lines["mid"], "committeeMeetingShort": cm_lines and cm_lines["short"]}

        # the words, pinned
        self.assertEqual(got[0], {
            "gvMeeting": {"en": "1st Wednesday of the month, 7 – 8 PM Central, Google Meet",
                          "es": "cada primer miércoles del mes, 7–8 p. m. (hora del Centro), por Google Meet"},
            "gvMeetingMid": {"en": "1st Wed · 7 PM · Google Meet", "es": "1.er mié. · 7 p. m. · Google Meet"},
            "gvMeetingShort": {"en": "1st Wed · 7 PM", "es": "1.er miércoles · 7 p. m."},
            "committeeMeeting": {"en": "3rd Wednesday of the month, 7 – 8 PM Central, Google Meet",
                                 "es": "cada tercer miércoles del mes, 7–8 p. m. (hora del Centro), por Google Meet"},
            "committeeMeetingMid": {"en": "3rd Wed · 7 PM · Google Meet", "es": "3.er mié. · 7 p. m. · Google Meet"},
            "committeeMeetingShort": {"en": "3rd Wed · 7 PM", "es": "3.er miércoles · 7 p. m."},
        })
        self.assertEqual(got[1]["committeeMeeting"], {"en": "last Friday of the month, 7:30 – 9:00 AM Central, Zoom",
                                                      "es": "cada último viernes del mes, 7:30–9:00 a. m. (hora del Centro), por Zoom"})
        self.assertEqual(got[1]["gvMeeting"]["es"],
                         "cada último sábado del mes, 9:00–10:30 a. m. (hora del Centro), en Rowlett Public Library")
        self.assertEqual(got[1]["gvMeetingMid"], {"en": "last Sat · 9 AM · Rowlett Public Library",
                                                  "es": "último sáb. · 9 a. m. · Rowlett Public Library"})
        self.assertEqual(got[2]["committeeMeeting"], {"en": "2nd Saturday of the month, 10 PM – 1 AM Central, Zoom",
                                                      "es": "cada segundo sábado del mes, 10 p. m. – 1 a. m. (hora del Centro), por Zoom"})
        self.assertEqual(got[2]["gvMeeting"]["en"], "4th Monday of the month, 11:30 AM – 12:30 PM Central, Zoom")
        self.assertEqual(got[3]["committeeMeeting"]["en"], "3rd Wednesday of the month, 6 – 7 PM Central, Zoom",
                         "meeting: without a day or a platform: the 3rd Wednesday, an hour long, on Zoom")
        self.assertEqual([got[3]["gvMeeting"], got[4], got[5]], [None, lines(None, None), lines(None, None)])
        # and the same as this file's twin of meetingLines
        self.assertEqual(got[:4], [
            lines(meeting_lines(1, "wednesday", "19:00", "20:00", "Google Meet"),
                  meeting_lines(3, "wednesday", "19:00", "20:00", "Google Meet")),
            lines(meeting_lines(-1, "saturday", "09:00", "10:30", "Rowlett Public Library", place=True),
                  meeting_lines(-1, "friday", "07:30", "09:00", "Zoom")),
            lines(meeting_lines(4, "monday", "11:30", "12:30", "Zoom"), meeting_lines(2, "saturday", "22:00", "01:00", "Zoom")),
            lines(None, meeting_lines(3, "wednesday", "18:00", "19:00", "Zoom")),
        ])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".csv"):
        sys.exit(_main(sys.argv[1:]))
    unittest.main()
