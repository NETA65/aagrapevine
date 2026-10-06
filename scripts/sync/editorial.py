"""Upcoming editorial themes & submission deadlines → data/raw/editorial.json

Sources (config: sources.grapevine.contribute, sources.lavina.contribute, sources.lavina.themes_page /
themes_link) — three PARTS, each read, kept and reported on its own:

* "gv" — Grapevine: https://www.aagrapevine.org/contribute ("Editorial Calendar")
  The page lists, per calendar year, every monthly issue with its theme and deadline:
      Grapevine Editorial Calendar 2027
        JANUARY
        Spiritual Awakenings (stories due June 1, 2026)
        Share your personal journey with Step Two. …
  One issue can carry two themes (December: "Remote Communities" + "Sober Holidays!"), and
  some have no deadline ("Classic Grapevine"). A PDF version is linked from the page.

* "lv" — La Viña's suggested topics: https://www.aalavina.org/temas-sugeridos ("Temas sugeridos")
  A list of evergreen story suggestions, stored as topics with extra.evergreen = true and no
  issue/deadline. (If a suggestion ever carries a "fecha límite …" date, it is picked up as the deadline.)

* "lv-themes" — La Viña's yearly themes: a document linked from https://www.aalavina.org/recursos
  La Viña puts no issue-by-issue calendar on a web page. Once a year it posts a document (January 2026:
  "Temas de LV 2026 y 2027" → /sites/default/files/2026-01/Temas_de_LV_2027_2026.pdf) with one page per year:
  "Temas de la revista para 2027", the six bimonthly issues ("Enero/Febrero" … "Noviembre/Diciembre"), each
  with its theme and "Fecha límite para enviar tu historial: 30 de julio del 2026", and at its foot the address
  to send stories to ("Envía tu historial a lveditorial@aagrapevine.org"). The newest link on that page to a
  document whose file name, text or picture names `themes_link` ("temas") and a year is read (find_themes_link):
  downloaded with the shared polite session (the committee's own User-Agent, robots.txt, the 5 s Crawl-delay;
  at most LV_THEMES_MAX_MB), its text taken page by page with pypdfium2 (document_pages) and EVERY year in it
  parsed (parse_lv_themes). The text layer of such a designed page is not in reading order — on the 2027 page
  the six issues come first, then the themes with their deadlines, the title last; the 2026 page's title is a
  picture (no text) — so the issues and the themes are paired in the order they come and then checked: as many
  themes as issues, every deadline readable, the issues and the deadlines in order, each deadline 1–15 months
  before its issue. The year is the page's "Temas de la revista para <year>", else the one the deadlines give
  (the first issue month after the deadline). A line drawn twice in the design comes out with every letter
  doubled ("EEnnvvííaa ttuu …"): such lines are read once. Anything not understood — no link, a document that
  cannot be downloaded or read, a changed layout — is an error of this part only: the previous dated La Viña
  topics are kept and the envelope says why (ok=false → /status/).
  These topics are labelled like La Viña's issues everywhere on the site: issue_key is the first month
  ("2027-05"), issue_label the two months as articles.py writes them ("Mayo / Junio 2027"; build_data adds
  i18n.issue_label "May / June 2027" / "Mayo / Junio 2027"). The pages, the district report, the digest and the
  presentations name the issue from its key, in ONE style (eleventy/filters/read.js issueName; send_digest.py
  issue_name): "May–June 2027", in Spanish "Mayo–Junio 2027" and inside a sentence "mayo–junio de 2027".
  The theme is Spanish (lang "es"; the English pages show it with lang="es").

Items (kind "topic", see docs/DATA_SCHEMA.md):
    title = theme, summary = the editors' prompt text, date = deadline (YYYY-MM-DD) or null
    extra = publication, issue_label, issue_key, deadline, due_text, theme, evergreen, pdf_url, submit_url,
            guidelines_url; La Viña's dated themes: pdf_url = the themes document (to visitors a "document",
            never a "PDF"; it is also the item's url), submit_email = the address that year's page gives

Only the current/future issues plus the most recent past one are kept (keep_window, the same rule for both
magazines). Each part is authoritative, so when it parses successfully its list REPLACES that part's previous
topics, field by field (a deadline or a description the page no longer gives disappears; first_seen is still
preserved) — the themes document only for the YEARS it covers: a dated La Viña
topic of a year the newest document no longer lists (a document of 2028 alone) is kept until it leaves the
window. When a part can't be fetched/parsed, its previous topics are kept and the envelope reports ok=false
with a clear error.

Run:  python -m scripts.sync.editorial [--dry-run] [--only gv|lv|lv-themes] [--gv-html FILE] [--lv-html FILE]
                                       [--lv-resources-html FILE] [--lv-themes-doc FILE] [--force]
      (--lv-themes-doc: the document itself, or its text as a .txt file with the pages separated by form feeds)
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .common import (MONTHS, clean_text, date_from_text, detect_lang, get_logger, load_config, load_raw,
                     make_item, merge_items, run_module, save_raw, shared_session, slugify, truncate)
from .crawl_pdf import download_pdf

SOURCE = "editorial"
log = get_logger(SOURCE)

EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]
ES_MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
             "Octubre", "Noviembre", "Diciembre"]
_FULL_MONTH_RE = re.compile(r"(?i)^(" + "|".join(EN_MONTHS + ES_MONTHS) + r")\s*:?$")
_CAL_YEAR_RE = re.compile(r"(?i)(?:editorial\s+calendar|calendario\s+editorial)\D{0,20}(20\d\d)")
# "Spiritual Awakenings (stories due June 1, 2026) optional description…"
_THEME_RE = re.compile(
    r"^(?P<theme>.+?)\s*\(\s*(?:stories|articles|submissions|historias|art[íi]culos)?\s*"
    r"(?:due|deadline|fecha\s+l[íi]mite)\s*(?:by|on|:)?\s*(?P<due>[^)]*)\)\s*(?P<rest>.*)$", re.I)
_BLOCK_TAGS = ["p", "li", "div", "ul", "ol", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section",
               "article"]

# La Viña's yearly themes document (part "lv-themes")
LV_THEMES_MAX_MB = 20          # the 2026–2027 document is 1.9 MB: two designed pages with photographs
LV_THEMES_MAX_PAGES = 12       # one page per year: more than this is not the themes document
PARTS = ("gv", "lv", "lv-themes")
_ES_MONTH = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
# "Enero/Febrero", "Noviembre / Diciembre", "Mayo y Junio" (a lone month too, should La Viña ever print one)
_LV_ISSUE_RE = re.compile(rf"(?i)^{_ES_MONTH}(?:\s*(?:/|-|–|—|&|\by\b)\s*{_ES_MONTH})?\s*:?$")
_LV_DEADLINE_RE = re.compile(r"(?i)\bfecha\s+l[íi]mite\b")
_LV_TITLE_RE = re.compile(r"(?i)^temas\b.*?(?<!\d)20\d\d(?!\d)")    # "Temas de la revista para 2027" (any year in it)
LV_THEMES_LINK = r"\btemas\b"  # the default of sources.lavina.themes_link (file names are read with "_" as a space)
_LV_DAY_MONTH_RE = re.compile(rf"(?i)\b(\d{{1,2}})\s+(?:de\s+)?{_ES_MONTH}\b")   # "30 de julio" (no year)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_YEAR_RE = re.compile(r"(?<!\d)(20\d\d)(?!\d)")


class ThemesError(Exception):
    """La Viña's themes document could not be found, read or understood (the part keeps its previous topics)."""


# --------------------------------------------------------------------------- helpers
def _today_central() -> date:
    tz = load_config().get("site", {}).get("timezone", "America/Chicago")
    return datetime.now(ZoneInfo(tz)).date()


def _add_months(key: str, n: int) -> str:
    y, m = map(int, key.split("-"))
    m += n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


def _block_lines(el) -> list[str]:
    """Visible text split on block elements / <br>, keeping inline elements (em, strong, a) together."""
    for br in el.find_all("br"):
        br.replace_with("\n")
    for b in el.find_all(_BLOCK_TAGS):
        b.insert_before("\n")
        b.insert_after("\n")
    return [ln for ln in (clean_text(x) for x in el.get_text("").split("\n")) if ln]


def _main(soup: BeautifulSoup):
    main = soup.find("main") or soup.body or soup
    for t in main.find_all(["script", "style", "noscript", "svg", "nav", "form", "iframe"]):
        t.decompose()
    return main


def parse_deadline(text: str, issue_year: int, issue_month: int) -> str | None:
    """'June 1, 2026' / 'Sept. 1, 2026' / 'Jan 1 2027' → ISO date. When the year is missing
    ('June 1') pick the latest such date before the issue month (deadlines precede issues)."""
    iso, _ = date_from_text(text, "en")   # needs a 20xx year; "Month YYYY" alone → 1st of that month
    if iso:
        return iso
    m = re.search(r"(?i)\b([a-záéíóú]+)\.?\s+(\d{1,2})\b", text)
    if m and m[1].lower() in MONTHS:
        mo, d = MONTHS[m[1].lower()], int(m[2])
        return _latest_before(mo, d, issue_year, issue_month)
    return None


def _latest_before(mo: int, d: int, issue_year: int, issue_month: int) -> str | None:
    """The latest day `mo`/`d` before the 1st of the issue month (this year's or last year's)."""
    for y in (issue_year, issue_year - 1):
        try:
            cand = date(y, mo, d)
        except ValueError:
            continue
        if cand < date(issue_year, issue_month, 1):
            return cand.isoformat()
    return None


def lv_issue_label(year: int, month: int, month2: int | None = None) -> str:
    """La Viña's label of an issue as the site stores it (scripts/sync/articles.py label_from_key): bimonthly,
    "Mayo / Junio 2027"; the two months as the document names them, else the month after an odd first month."""
    if not month2 and month % 2 == 1 and month < 12:
        month2 = month + 1
    if month2 and month2 != month:
        return f"{ES_MONTHS[month - 1]} / {ES_MONTHS[month2 - 1]} {year}"
    return f"{ES_MONTHS[month - 1]} {year}"


# --------------------------------------------------------------------------- Grapevine
def parse_gv(html: str, page_url: str) -> tuple[list[dict], dict]:
    """Return (rows, meta). rows: dicts with issue_year, issue_month, theme, deadline, description."""
    soup = BeautifulSoup(html, "lxml")
    main = _main(soup)
    meta: dict = {}
    for a in main.find_all("a", href=True):
        href, label = a["href"], clean_text(a.get_text(" "))
        if href.lower().endswith(".pdf") and not meta.get("pdf_url"):
            meta["pdf_url"] = urljoin(page_url, href)
        elif re.search(r"(?i)submit", href + " " + label) and not meta.get("submit_url"):
            meta["submit_url"] = urljoin(page_url, href)
        elif re.search(r"(?i)guideline", href) and not meta.get("guidelines_url"):
            meta["guidelines_url"] = urljoin(page_url, href)
    m = re.search(r"(?i)no later than\s+(\w+)\s+months?\s+before", main.get_text(" "))
    if m:
        meta["lead_time"] = clean_text(m[0])

    rows: list[dict] = []
    year = month = None
    cur: dict | None = None
    just_saw_month = False
    for line in _block_lines(main):
        ym = _CAL_YEAR_RE.search(line)
        if ym:
            year, month, cur, just_saw_month = int(ym[1]), None, None, False
            continue
        if year is None:
            continue
        mm = _FULL_MONTH_RE.match(line)
        if mm:
            month = MONTHS[mm[1].lower()]
            cur, just_saw_month = None, True
            continue
        if month is None:
            continue
        tm = _THEME_RE.match(line)
        if tm and len(tm["theme"]) <= 120:
            cur = {"issue_year": year, "issue_month": month, "theme": clean_text(tm["theme"]).strip(" -–—:"),
                   "deadline": parse_deadline(tm["due"], year, month), "due_text": clean_text(tm["due"]),
                   "description": clean_text(tm["rest"])}
            rows.append(cur)
            just_saw_month = False
            continue
        if just_saw_month and len(line) <= 80 and not re.search(r"[.?!]$", line):
            # A theme with no deadline, e.g. "Classic Grapevine".
            cur = {"issue_year": year, "issue_month": month, "theme": line, "deadline": None,
                   "due_text": "", "description": ""}
            rows.append(cur)
            just_saw_month = False
            continue
        just_saw_month = False
        if cur is not None and len(cur["description"]) < 600:
            cur["description"] = clean_text(cur["description"] + " " + line)
    return rows, meta


# --------------------------------------------------------------------------- La Viña: suggested topics
def parse_lv(html: str, page_url: str) -> tuple[list[dict], dict]:
    """Evergreen suggestions = the bulleted (<li>) items of the page's main content. No bullets → no
    rows (the caller then keeps yesterday's list instead of publishing random page text)."""
    soup = BeautifulSoup(html, "lxml")
    main = _main(soup)
    meta: dict = {}
    intro = main.find(["p", "h1", "h2"])
    if intro:
        meta["intro"] = truncate(clean_text(intro.get_text(" ")), 300)
    content = main.select_one(".node--type-page, article") or main
    cands = [clean_text(li.get_text(" ")) for li in content.find_all("li")
             if not li.find_parent(["nav", "header", "footer"]) and not li.find("a", href=re.compile(r"^(?!#)"))]
    rows, seen = [], set()
    for c in cands:
        if not c or len(c) > 200 or re.search(r"(?i)regresar|p[áa]gina anterior|iniciar sesi[óo]n", c):
            continue
        key = c.lower()
        if key in seen:
            continue
        seen.add(key)
        deadline = None
        issue_year = issue_month = None
        if re.search(r"(?i)fecha\s+l[íi]mite|antes del|hasta el", c):
            deadline, _ = date_from_text(c, "es")
        theme = c.rstrip(" .")
        rows.append({"issue_year": issue_year, "issue_month": issue_month, "theme": theme,
                     "deadline": deadline, "due_text": "", "description": ""})
    return rows, meta


# --------------------------------------------------------------------------- La Viña: the yearly themes
def find_themes_link(html: str, page_url: str, pattern: str = LV_THEMES_LINK) -> dict | None:
    """The newest yearly themes document linked from La Viña's resources page → {"url", "label", "year"} or None.

    A candidate is a link to a document (a .pdf address) whose file name, link text or picture's alt text
    matches `pattern` (a regular expression, capitals ignored; config sources.lavina.themes_link) and names a
    year (20xx) — "Temas_de_LV_2027_2026.pdf" / "Temas de LV 2026 y 2027". The page links each document twice
    (its cover picture, then its name): one candidate per address. Newest = the highest year named, then the
    newest upload folder (/files/2026-01/), then the first on the page. Menus, headers and footers are left out."""
    try:
        rx = re.compile(pattern or LV_THEMES_LINK, re.I)
    except re.error:
        log.warning("sources.lavina.themes_link %r is not a valid regular expression — using %r", pattern,
                    LV_THEMES_LINK)
        rx = re.compile(LV_THEMES_LINK, re.I)
    soup = BeautifulSoup(html or "", "lxml")
    root = soup.find("main") or soup.body or soup
    found: dict[str, dict] = {}
    for order, a in enumerate(root.find_all("a", href=True)):
        if a.find_parent(["nav", "header", "footer"]):
            continue
        url = urljoin(page_url, a["href"].strip())
        path = unquote(urlparse(url).path)
        if not path.lower().endswith(".pdf"):
            continue
        name = path.rsplit("/", 1)[-1]
        text = clean_text(a.get_text(" "))
        alts = [clean_text(img.get("alt")) for img in a.find_all("img") if clean_text(img.get("alt"))]
        c = found.setdefault(url, {"url": url, "order": order, "names": [], "texts": []})
        c["names"].append(re.sub(r"[_+]+", " ", name))
        c["texts"] += [t for t in [text, *alts] if t]
    best = None
    for c in found.values():
        words = " ".join(c["names"] + c["texts"])
        years = [int(y) for y in _YEAR_RE.findall(words)]
        if not years or not rx.search(words):
            continue
        upload = re.search(r"/(20\d\d)-(\d\d)/", urlparse(c["url"]).path)
        key = (max(years), upload.group(1) + upload.group(2) if upload else "", -c["order"])
        if best is None or key > best[0]:
            label = next((t for t in c["texts"] if rx.search(t)), "") or (c["texts"] or c["names"])[0]
            best = (key, {"url": c["url"], "label": label, "year": max(years)})
    return best[1] if best else None


def document_pages(data: bytes) -> list[str]:
    """The text of each page of a document (pypdfium2), at most LV_THEMES_MAX_PAGES pages. Raises ThemesError
    for a file that is not a readable document. (Only the text is read — never its author metadata.)"""
    try:
        import pypdfium2 as pdfium
    except Exception as e:  # pragma: no cover - dependency missing
        raise ThemesError(f"pypdfium2 is missing ({e})") from e
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as e:  # pdfium.PdfiumError: not a PDF, damaged, password-protected …
        raise ThemesError(f"the document could not be opened ({type(e).__name__}: {str(e)[:80]})") from e
    try:
        n = len(pdf)
        if not n:
            raise ThemesError("the document has no pages")
        if n > LV_THEMES_MAX_PAGES:
            raise ThemesError(f"the document has {n} pages — not La Viña's yearly themes?")
        pages = []
        for i in range(n):
            page = textpage = None
            try:
                page = pdf[i]
                textpage = page.get_textpage()
                pages.append(textpage.get_text_range() or "")
            finally:
                for obj in (textpage, page):
                    try:
                        obj and obj.close()
                    except Exception:  # noqa: BLE001 — closing never matters
                        pass
        return pages
    except ThemesError:
        raise
    except Exception as e:  # anything unexpected inside pdfium
        raise ThemesError(f"the document's text could not be read ({type(e).__name__}: {str(e)[:80]})") from e
    finally:
        try:
            pdf.close()
        except Exception:  # noqa: BLE001
            pass


def _undouble(line: str) -> str:
    """'EEnnvvííaa ttuu hhiissttoorriiaall' → 'Envía tu historial'. A line the design draws twice (an outline over
    the letters) comes out of the text layer with every character doubled. Only a line of two or more words that
    are ALL doubled is changed — 'AA' alone, or 'Hispanos Veteranos en AA', stays as it is."""
    words = line.split()
    if len(words) < 2 or not all(len(w) % 2 == 0 and w[0::2] == w[1::2] for w in words):
        return line
    return " ".join(w[0::2] for w in words)


def _page_lines(text: str) -> list[str]:
    """A page's text → its lines (cleaned, doubled lines read once), a deadline that the design wraps over two
    or three lines ("Fecha límite para enviar tu" / "historial: 30 de julio del 2026") joined into one."""
    lines = [_undouble(clean_text(x)) for x in re.split(r"\r\n|\r|\n|\f", text or "")]
    lines = [x for x in lines if x]
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if _LV_DEADLINE_RE.search(ln):
            j = i
            while (not _YEAR_RE.search(ln) and not _LV_DAY_MONTH_RE.search(ln.split(":", 1)[-1])
                   and j + 1 < len(lines) and j - i < 2):
                j += 1
                ln = f"{ln} {lines[j]}"
            i = j
        out.append(ln)
        i += 1
    return out


def _lv_deadline(line: str, title_year: int | None, month: int) -> tuple[str | None, str]:
    """A deadline line → (ISO date or None, the date as written). "Fecha límite para enviar tu historial: 30 de
    julio del 2026" → ("2026-07-30", "30 de julio del 2026"). Without a year ("30 de julio") the page's year is
    needed: the latest such day before the issue."""
    due_text = clean_text(line.split(":", 1)[1]) if ":" in line else clean_text(_LV_DEADLINE_RE.split(line)[-1])
    iso, _ = date_from_text(due_text or line, "es")
    if iso:
        return iso, due_text
    m = _LV_DAY_MONTH_RE.search(due_text or line)
    if m and title_year:
        return _latest_before(MONTHS[m[2].lower()], int(m[1]), title_year, month), due_text
    return None, due_text


def _months_between(d: date, year: int, month: int) -> int:
    """Whole months from the deadline's month to the issue's (July 30, 2026 → January 2027 = 6)."""
    return (year * 12 + month) - (d.year * 12 + d.month)


def _parse_lv_page(text: str, n: int) -> tuple[list[dict], list[str]] | None:
    """One page of the themes document → (rows, e-mail addresses), or None for a page without issues or deadlines
    (a cover, a note). Raises ThemesError for a page whose issues and themes do not pair up."""
    issues: list[tuple[int, int | None, str]] = []      # (first month, second month, as printed)
    pairs: list[tuple[str, str]] = []                    # (theme, deadline line)
    titles: list[int] = []
    emails: list[str] = []
    buf: list[str] = []                                  # lines since the last issue / deadline / title / address
    for ln in _page_lines(text):
        m = _LV_ISSUE_RE.match(ln)
        if m:
            m1 = MONTHS[m[1].lower()]
            m2 = MONTHS[m[2].lower()] if m[2] else None
            issues.append((m1, m2, ln))
            buf = []
            continue
        dm = _LV_DEADLINE_RE.search(ln)
        if dm:      # the theme: the lines before it (and words before "Fecha límite" on its own line, if any)
            pairs.append((clean_text(" ".join([*buf, ln[:dm.start()]])).strip(" -–—:·•\"“”'«»"), ln[dm.start():]))
            buf = []
            continue
        if _LV_TITLE_RE.match(ln):          # "Temas de la revista para 2027" ("… 2026 y 2027": both)
            titles += [int(y) for y in _YEAR_RE.findall(ln)]
            buf = []
            continue
        e = _EMAIL_RE.search(ln)
        if e:
            emails.append(e[0].lower())
            buf = []
            continue
        buf.append(ln)
    if not issues and not pairs:
        return None
    where = f"page {n}"
    if len(issues) != len(pairs):
        raise ThemesError(f"{where}: {len(issues)} issues but {len(pairs)} themes with a deadline — has the "
                          f"document's layout changed?")
    title_year = titles[0] if len(set(titles)) == 1 else None
    rows: list[dict] = []
    for (m1, m2, printed), (theme, line) in zip(issues, pairs):
        if not theme or len(theme) > 100:
            raise ThemesError(f"{where}: the theme for {printed} could not be read — has the layout changed?")
        iso, due_text = _lv_deadline(line, title_year, m1)
        if not iso:
            raise ThemesError(f"{where}: the deadline for {printed} could not be read (“{clean_text(line)[:80]}”)")
        dl = date.fromisoformat(iso)
        if title_year:
            year = title_year
        else:   # the first time that issue's month comes after its deadline
            year = dl.year if date(dl.year, m1, 1) > dl else dl.year + 1
            if titles and year not in titles:
                raise ThemesError(f"{where}: the deadline for {printed} ({iso}) fits none of the years on the page")
        if not 1 <= _months_between(dl, year, m1) <= 15:
            raise ThemesError(f"{where}: the deadline for {printed} ({iso}) does not fit an issue of {year}")
        rows.append({"issue_year": year, "issue_month": m1, "issue_month2": m2, "theme": theme, "deadline": iso,
                     "due_text": due_text, "description": "", "lang": "es",
                     "issue_label": lv_issue_label(year, m1, m2)})
    keys = [(r["issue_year"], r["issue_month"]) for r in rows]
    if keys != sorted(set(keys)):
        raise ThemesError(f"{where}: the issues are not in order — has the layout changed?")
    dls = [r["deadline"] for r in rows]
    if dls != sorted(dls):
        raise ThemesError(f"{where}: the deadlines are not in the issues' order — has the layout changed?")
    return rows, emails


def parse_lv_themes(pages: list[str]) -> tuple[list[dict], dict]:
    """La Viña's yearly themes document (its text, page by page) → (rows, meta).

    rows (oldest issue first): issue_year, issue_month, issue_month2, issue_label ("Mayo / Junio 2027"), theme,
    deadline (ISO), due_text ("17 de octubre del 2026"), lang "es", submit_email (the address on that page, else
    the first one in the document). meta: {"years": [2026, 2027], "pages": 2, "emails": {"2027": "…"}}.
    Raises ThemesError when the document is not understood: no themes at all, or a page whose issues, themes and
    deadlines do not pair up (_parse_lv_page) — a changed layout is never published half-read."""
    per_page: list[tuple[list[dict], list[str]]] = []
    for n, text in enumerate(pages, 1):
        got = _parse_lv_page(text, n)
        if got:
            per_page.append(got)
    if not per_page:
        raise ThemesError("no issues with a theme and a deadline in the document — not La Viña's yearly themes, "
                          "or its layout changed")
    first_email = next((e for _, emails in per_page for e in emails), None)
    rows: list[dict] = []
    by_key: dict[tuple[int, int], dict] = {}
    emails_by_year: dict[str, str] = {}
    for page_rows, emails in per_page:
        for r in page_rows:
            k = (r["issue_year"], r["issue_month"])
            if k in by_key:
                if slugify(by_key[k]["theme"]) != slugify(r["theme"]):
                    raise ThemesError(f"two themes for {r['issue_label']}: “{by_key[k]['theme']}” and “{r['theme']}”")
                continue                    # the same issue twice (a repeated page)
            r["submit_email"] = emails[0] if emails else first_email
            if r["submit_email"]:
                emails_by_year.setdefault(str(r["issue_year"]), r["submit_email"])
            by_key[k] = r
            rows.append(r)
    rows.sort(key=lambda r: (r["issue_year"], r["issue_month"]))
    return rows, {"years": sorted({r["issue_year"] for r in rows}), "pages": len(per_page), "emails": emails_by_year}


def read_document_file(path: str) -> list[str]:
    """--lv-themes-doc FILE: the document itself, or its text (UTF-8) with the pages separated by form feeds."""
    data = Path(path).read_bytes()
    if b"%PDF" in data[:1024]:
        return document_pages(data)
    return data.decode("utf-8").split("\f")


# --------------------------------------------------------------------------- items
def rows_to_items(rows: list[dict], pub: str, page_url: str, meta: dict) -> list[dict]:
    source = "grapevine" if pub == "gv" else "lavina"
    items = []
    for r in rows:
        y, mo = r.get("issue_year"), r.get("issue_month")
        issue_key = f"{y:04d}-{mo:02d}" if y and mo else None
        if issue_key:
            issue_label = r.get("issue_label") or (f"{EN_MONTHS[mo - 1]} {y}" if pub == "gv"
                                                   else lv_issue_label(y, mo, r.get("issue_month2")))
        else:
            issue_label = None
        theme = r["theme"]
        tid = f"ed:{pub}:{issue_key or 'any'}:{slugify(theme, 48)}"
        extra = {
            "publication": pub,
            "issue_label": issue_label,
            "issue_key": issue_key,
            "deadline": r.get("deadline"),
            "theme": theme,
            "evergreen": issue_key is None,
            "due_text": r.get("due_text") or None,
            "pdf_url": meta.get("pdf_url"),
            "submit_url": meta.get("submit_url"),
            "submit_email": r.get("submit_email") or meta.get("submit_email"),
            "guidelines_url": meta.get("guidelines_url"),
        }
        items.append(make_item(
            id=tid, source=source, kind="topic", url=page_url, title=theme,
            summary=r.get("description") or "",
            lang=r.get("lang") or detect_lang(f"{theme} {r.get('description') or ''}", prior="en" if pub == "gv" else "es"),
            date=r.get("deadline"), category=pub,
            extra={k: v for k, v in extra.items() if v is not None},
        ))
    return items


def keep_window(items: list[dict], today: date) -> list[dict]:
    """Keep evergreen topics, plus dated ones from the issue on sale now, later issues, and the one before.

    Magazines are dated ahead: in late September the October issue is on sale. So the "current" issue is
    the latest issue_key <= next month; we also keep the issue just before it."""
    dated = sorted({i["extra"]["issue_key"] for i in items if i["extra"].get("issue_key")})
    if not dated:
        return items
    horizon = _add_months(f"{today.year:04d}-{today.month:02d}", 1)
    past_or_now = [k for k in dated if k <= horizon]
    if past_or_now:
        current = past_or_now[-1]
        idx = dated.index(current)
        start = dated[idx - 1] if idx > 0 else current
    else:
        start = dated[0]
    return [i for i in items if not i["extra"].get("issue_key") or i["extra"]["issue_key"] >= start]


def part_of(item: dict) -> str:
    """Which part an item comes from: "gv", "lv" (La Viña's suggested topics) or "lv-themes" (its dated themes)."""
    e = item.get("extra") or {}
    pub = e.get("publication") or item.get("category") or ""
    return "lv-themes" if pub == "lv" and e.get("issue_key") else pub


# --------------------------------------------------------------------------- collect
def settings(cfg: dict | None = None) -> dict:
    """The pages read (config/site.yml sources.grapevine / sources.lavina)."""
    src = (cfg if cfg is not None else load_config()).get("sources", {}) or {}
    gv, lv = src.get("grapevine") or {}, src.get("lavina") or {}
    gv_base = (gv.get("base") or "https://www.aagrapevine.org").rstrip("/")
    lv_base = (lv.get("base") or "https://www.aalavina.org").rstrip("/")
    return {
        "gv": gv_base + (gv.get("contribute") or "/contribute"),
        "lv": lv_base + (lv.get("contribute") or "/temas-sugeridos"),
        # an address or a path on La Viña's site; without the setting, the representatives' resources page
        "lv_themes_page": urljoin(lv_base + "/", str(lv.get("themes_page") or lv.get("rlv_resources") or "/recursos")),
        "lv_themes_link": str(lv.get("themes_link") or LV_THEMES_LINK),
    }


def _stats(window: list[dict], parsed: int, today: date) -> dict:
    return {"parsed": parsed, "kept": len(window),
            "with_deadline": sum(1 for i in window if i["extra"].get("deadline")),
            "open": sum(1 for i in window if (i["extra"].get("deadline") or "") >= today.isoformat())}


def _uniq(items: list[dict]) -> list[dict]:
    """Duplicate ids can happen if the same theme is listed twice for one issue — keep the first."""
    out: dict[str, dict] = {}
    for it in items:
        out.setdefault(it["id"], it)
    return list(out.values())


def collect(fetch_html: Callable[[str], str | None], fetch_pages: Callable[[str], list[str]], prev_items: list[dict],
            today: date, cfg: dict | None = None, only: str | None = None, force: bool = False) -> dict:
    """Read every part → {"fresh", "kept", "refreshed", "errors", "stats"}.

    fresh: the topics read today (in the window); kept: previous topics carried over unchanged (a part that failed
    or was not asked for, and dated La Viña topics of years the themes document no longer lists); refreshed: the
    parts read successfully (their previous topics are replaced). fetch_html(url) → page text or None;
    fetch_pages(url) → the themes document's text page by page (raises ThemesError)."""
    st = settings(cfg)
    wanted = {"gv": {"gv"}, "lv": {"lv", "lv-themes"}, "lv-themes": {"lv-themes"}}.get(only or "", set(PARTS))
    fresh: list[dict] = []
    kept: list[dict] = []
    refreshed: set[str] = set()
    errors: list[str] = []
    stats: dict = {}
    for part in PARTS:
        prev_part = [i for i in prev_items if part_of(i) == part]
        if part not in wanted:
            kept += prev_part
            continue
        carried: list[dict] = []
        try:
            if part == "lv-themes":
                html = fetch_html(st["lv_themes_page"])
                if not html:
                    raise ThemesError(f"could not fetch {st['lv_themes_page']}")
                link = find_themes_link(html, st["lv_themes_page"], st["lv_themes_link"])
                if not link:
                    raise ThemesError(f"no yearly themes document linked from {st['lv_themes_page']} (a document "
                                      f"whose name matches sources.lavina.themes_link and names a year) — moved or "
                                      f"renamed?")
                rows, meta = parse_lv_themes(fetch_pages(link["url"]))
                items = _uniq(rows_to_items(rows, "lv", link["url"], {"pdf_url": link["url"]}))
                # the document replaces the years it covers; a year it no longer lists stays until it leaves the window
                carried = [i for i in prev_part if str(i["extra"].get("issue_key", ""))[:4] not in
                           {str(y) for y in meta["years"]}]
                extra_stats = {"years": meta["years"], "document": link["url"], "label": link["label"]}
            else:
                url = st[part]
                html = fetch_html(url)
                if not html:
                    errors.append(f"{part}: could not fetch {url}")
                    kept += prev_part
                    continue
                rows, meta = (parse_gv if part == "gv" else parse_lv)(html, url)
                if not rows:
                    errors.append(f"{part}: no themes found on {url} (page layout changed?)")
                    kept += prev_part
                    continue
                items = _uniq(rows_to_items(rows, part, url, meta))
                extra_stats = {}
        except ThemesError as e:
            errors.append(f"{part}: {e}"[:300])
            log.warning("%s: %s — keeping the previous topics", part, e)
            kept += prev_part
            continue
        except Exception as e:  # noqa: BLE001 — one part never stops the others
            log.exception("%s parse error", part)
            errors.append(f"{part}: parse error {type(e).__name__}: {e}"[:200])
            kept += prev_part
            continue
        window = keep_window(items + carried, today)
        # Sanity check: a half-rendered or maintenance page can "parse" into a much shorter list.
        # Losing most topics overnight is far more likely a site glitch than an editorial decision.
        if len(prev_part) >= 6 and len(window) < len(prev_part) * 0.4 and not force:
            errors.append(f"{part}: only {len(window)} themes found (had {len(prev_part)}) — kept the previous "
                          f"list; run with --force to accept")
            kept += prev_part
            continue
        in_window = {id(i) for i in window}
        fresh += [i for i in items if id(i) in in_window]
        kept += [i for i in carried if id(i) in in_window]
        refreshed.add(part)
        stats[part.replace("-", "_")] = {**_stats(window, len(items), today), **extra_stats}
        log.info("%s: %d themes parsed, %d in window", part, len(items), len(window))
    return {"fresh": fresh, "kept": kept, "refreshed": refreshed, "errors": errors, "stats": stats}


# --------------------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Editorial themes & deadlines (Grapevine / La Viña)")
    ap.add_argument("--dry-run", action="store_true", help="print items, do not write data/raw")
    ap.add_argument("--gv-html", help="parse this saved Grapevine /contribute HTML instead of fetching")
    ap.add_argument("--lv-html", help="parse this saved La Viña /temas-sugeridos HTML instead of fetching")
    ap.add_argument("--lv-resources-html", help="parse this saved La Viña /recursos HTML instead of fetching")
    ap.add_argument("--lv-themes-doc", help="read this saved themes document (or its text, pages split by form "
                                            "feeds) instead of downloading it")
    ap.add_argument("--only", choices=["gv", "lv", "lv-themes"], help="process only one publication (lv = both of "
                                                                       "La Viña's parts) or La Viña's themes document")
    ap.add_argument("--force", action="store_true", help="accept a much shorter list than yesterday's")
    args = ap.parse_args(argv)

    st = settings()
    files = {st["gv"]: args.gv_html, st["lv"]: args.lv_html, st["lv_themes_page"]: args.lv_resources_html}
    http = shared_session()

    def fetch_html(url: str) -> str | None:
        if files.get(url):
            return Path(files[url]).read_text(encoding="utf-8")
        return http.get_text(url)

    def fetch_pages(url: str) -> list[str]:
        if args.lv_themes_doc:
            return read_document_file(args.lv_themes_doc)
        _head, data, err, _final = download_pdf(http, url, max_bytes=LV_THEMES_MAX_MB * 1024 * 1024)
        if err or not data:
            raise ThemesError(f"could not download {url} ({err or 'empty'})")
        return document_pages(data)

    prev = load_raw(SOURCE)
    prev_items = prev.get("items", [])
    res = collect(fetch_html, fetch_pages, prev_items, _today_central(), only=args.only, force=args.force)
    fresh, kept, errors, stats = res["fresh"], res["kept"], res["errors"], res["stats"]

    if args.dry_run:
        print(json.dumps(fresh, ensure_ascii=False, indent=1))
        print("kept:", len(kept), "errors:", errors)
        return

    # Previous items of the parts refreshed today are replaced (drop_missing on that subset) — field by field too
    # (authoritative: a deadline or a description the page no longer gives really disappears; only first_seen is
    # remembered); items of failed parts — and the dated La Viña topics of years the document no longer lists —
    # are carried over unchanged.
    old_for_refreshed = [i for i in prev_items if part_of(i) in res["refreshed"]]
    merged, added = merge_items(old_for_refreshed, fresh, drop_missing=True, authoritative=True)
    stats["new"] = added
    carried_ids = {i["id"] for i in kept}
    all_items = [i for i in merged if i["id"] not in carried_ids] + kept
    ok = not errors
    save_raw(SOURCE, all_items, ok=ok, error="; ".join(errors) if errors else None, stats=stats)
    log.info("editorial: %d topics (%d new)%s", len(all_items), added, f" — errors: {errors}" if errors else "")


if __name__ == "__main__":
    raise SystemExit(run_module(SOURCE, main))
