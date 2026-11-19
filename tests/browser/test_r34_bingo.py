"""Round 34 · the GVR / RLV corner's bingo cards (/gvr/bingo/ and /es/gvr/bingo/), in a real browser
(tests/browser/__init__.py says how to run these; the site server, the browser and the helpers are
test_site_in_browser.py's; tests/test_r34_bingo.py has the built pages' static checks and the card core's own, in
Node). The page: src/pages/gvr-bingo.njk; the builder: src/assets/js/bingo.js (Alpine bingoBuilder); the cards'
logic: src/assets/js/bingo-core.js (window.GVBingo); the squares: content/bingo/bingo.csv.

  * Starts        — both pages: the builder starts (neither of its "couldn't start" notices), draws card 1 of 10 with a
                    game code, goes to card 2 (a different card), lists "Choose squares yourself" (each kind of square
                    folded: opened, every kind) and searches it — and no script error or console error comes up (a
                    request to another site, which never resolves here, is not counted). With bingo.js blocked, the
                    notice outside the builder says it could not start.
  * Grids         — every preset 3×3 … 10×10 and the rectangular 4×6, 6×4, 10×3 and 3×10, an English card on the
                    English page and a Spanish card on the Spanish one: the preview has rows × columns squares laid out
                    in rows × columns, the FREE square only on odd × odd grids and in the middle, never a square twice,
                    the short words from 7 rows or columns up, and no square's words stick out of their box (taller or
                    wider: scrollHeight / scrollWidth at most clientHeight / clientWidth + 1).
  * Printing      — 10 cards on Letter (English page) and A4 (Spanish page), 1, 2 and 4 on a sheet, portrait and
                    landscape (a 3×5 too, two on a sheet: its strip is a narrow column beside the QR code): the
                    browser's own PDF at the page's @page size has exactly ceil(10 ÷ per sheet) pages, each the
                    paper's size the right way round; the 10 printed cards are all different, "Card n of 10 · Game
                    CODE" each, no square twice on a card, no words sticking out on paper, no text under 6 pt (the
                    squares' words, labels, headings, the small print: no printed card goes lower), no word of the
                    meetings strip broken in two (the e-mail breaks only after its "@"), no time ("7 – 8 PM", "7 PM")
                    on two lines, the side column never running over and the meetings strip ending above the small
                    print; a wide card (4 on a landscape sheet, a 10×10 landscape) puts the grid beside the column
                    ("side" or "top", not "stack"); "All cards the same" prints the one card 10 times.
  * TypedHead     — a typed event (about 28 and 60 characters) or title (60) on the smallest cards, 4×4 and 4×3
                    four on a Letter portrait sheet, English and Spanish: printed, every square's words at 6 pt or
                    more, no square giving up its write-in line (.is-tight), no label broken inside a word, the event
                    whole at the top (bingo.js placeCard: a short date, a smaller head — the builder says so under
                    the Event box). The head gets smaller only when the meeting place needs it: a 60-character English
                    title and event, 4 on an A4 sheet, print whole with the mid lines and no note; a 60-character
                    Spanish title on Letter gets the note, and the Event box points to it (aria-describedby). A long
                    piece with no space as the event — a pasted meeting link, a made-up word of 45 letters — on 4×4
                    and 3×4 cards four on a Letter landscape sheet: every square still at 6 pt, the event whole, no
                    time of the meetings strip on two lines. A Spanish 4×4 card of 17 hand-picked squares with a long
                    title and event, opened from its link: every square at 6 pt (a square whose label fills it when
                    small is never taken for one that fits).
  * Link          — "Copy a link to these settings" copies the address with the settings in its #hash; that link
                    gives the very same cards after a reload, in a fresh browser profile and on the page of the
                    other language; a broken link is ignored (the 5×5 default, 10 cards).
  * CardLanguage  — the card's language is chosen apart from the page's: a Spanish card on the English page and an
                    English one on the Spanish page have that language's title, FREE square, "How to play", footer
                    and squares' words (the page's own words stay).
  * MeetingsStrip — the card's "Meetings & contact" strip shows the Grapevine Meeting and the committee meeting
                    exactly as the page's data has them (#bingo-data info — no time is written here; the words
                    themselves are tests/test_bingo_csv.py Info's) and the committee's e-mail (config/site.yml; its
                    one place to break after the "@"): the
                    whole card the long lines (the day, the time with its zone, the place), a small card (4 on a
                    Letter portrait sheet, the smallest the default grid makes) the longest lines that fit, measured by
                    bingo.js — long or mid (short + the place: config/site.yml meeting.platform), the same for both
                    meetings —; the default card has the three "always" information squares (both
                    meetings and the e-mail: GVBingo.DEFAULTS.infoMax 3); "0" meetings & contact squares leaves them
                    off the card.
  * Limits        — the builder at its edges, on the English page: too few squares (10×10 with only "Just for fun":
                    the pool line says so, the way out shows, Print waits, and the browser's own Print makes one page
                    — the note, not the form); black and white (every square white paper; in colour the information
                    squares are tinted); the help lines (small squares: little room to write; a long "How to play" on
                    a small card: the short one prints, and does); the settings remembered after a reload; "Start
                    over" asks first ("Keep my settings" focused, Escape keeps them), then gives the start and a new
                    code that a reload keeps; 60 cards of 10×10 printed (60 sheets, all different) in a few seconds.
  * Phone         — a 390-pixel phone, light and dark, English and Spanish: nothing scrolls sideways (with "Choose
                    squares yourself" open, and with a 10×10 card), no square's words stick out, and the card stays
                    white paper with dark ink in the dark theme too.
  * ReducedMotion — motion reduced, by the device's setting or the site's own ("Aa"): every square's words still fit,
                    in the preview (3×3, 5×5, 10×10, 4×6) and on paper (the other checks run with no motion
                    preference). Its note says what it found in round 34 and what keeps it fixed.
  * NoScript      — JavaScript off: the build's sample card shows (5×5, the page's language, the FREE square in the
                    middle, the squares' words from the CSV, nothing sticking out), the builder is hidden, the note
                    says it needs JavaScript, and the page prints as that one card on one page.
  * Teaser        — /gvr/ and /es/gvr/: the page nav has Bingo, and the #bingo section's button goes to the bingo
                    page of the same language, where the builder draws its card.

The builder's squares carry a zero-width space (U+200B) in addresses (bingo.js breakable(): grapevine@neta65.org may
break after the "@"); the no-JS sample has <wbr> there (no text of its own). Both are taken out before words are
compared. The whole module takes about a minute on a Windows PC with Edge (one browser, one site server:
test_site_in_browser.py's; the PDFs much of it).
"""
from __future__ import annotations

import json
import math
import re
import time
import unittest
from pathlib import Path
from urllib.parse import quote

import yaml

from browser.test_site_in_browser import (S, SIDEWAYS, answered, contrast, new_context, open_page,  # noqa: F401
                                          setUpModule, tearDownModule, url)

ROOT = Path(__file__).resolve().parents[2]
# the page's words (bingo.*) and the /gvr/ teaser's (read.gvr.bingo_*)
WORDS = {k: v for f in ("bingo.json", "read.json") for k, v in
         json.loads((ROOT / "src" / "_i18n" / f).read_text(encoding="utf-8")).items()}
CFG = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
# the address the cards give (eleventy/filters/bingo.js bingoInfo: meeting.chair_email, else site.contact_email)
EMAIL = str((CFG.get("meeting") or {}).get("chair_email") or (CFG.get("site") or {}).get("contact_email") or "").strip()
# where our meetings are held (eleventy/filters/bingo.js bingoInfo: the long and the mid lines end with it)
PLATFORM = str((CFG.get("meeting") or {}).get("platform") or "").strip()
LOCAL = re.compile(r"^https?://127\.0\.0\.1[:/]")
CODE = re.compile(r"^[A-HJ-NP-Z2-9]{4,6}$")             # bingo-core.js ALPHABET: A–Z without I and O, 2–9
PRESETS = [(n, n) for n in range(3, 11)]
RECTANGLES = [(4, 6), (6, 4), (10, 3), (3, 10)]
# the paper's size in points, as the PDF has it (Letter 8.5 × 11 in; A4 210 × 297 mm)
PAPER_PT = {"letter": (612.0, 792.0), "a4": (595.28, 841.89)}
CARDS = 10                                            # GVBingo.DEFAULTS.count


def w(key: str, lang: str) -> str:
    return WORDS[key][lang]


def fmt(tpl: str, **values) -> str:
    """bingo.js fmt(): {n}, {total}, {code} … filled."""
    return re.sub(r"\{(\w+)\}", lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), tpl)


def bingo_path(lang: str) -> str:
    return ("es/" if lang == "es" else "") + "gvr/bingo/"


def watch(page, errors: list, where: str) -> None:
    """Script errors and console errors of this page go into `errors` — not a request to another site (the browser
    never reaches one here: scripts/ops/site_browser.py NO_OUTSIDE)."""
    page.on("pageerror", lambda e: errors.append(f"{where}: {str(e).splitlines()[0][:200]}"))

    def console(msg):
        if msg.type != "error":
            return
        loc = (msg.location or {}).get("url") or ""
        if msg.text.startswith("Failed to load resource") and loc and not LOCAL.match(loc):
            return
        errors.append(f"{where}: console: {msg.text.splitlines()[0][:200]}")
    page.on("console", console)


def settle(page) -> None:
    """Two frames: the builder draws its preview on the next animation frame after a change (bingo.js queueDraw)."""
    page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")


def open_bingo(ctx, lang: str = "en", hash: str = "", errors: list | None = None, motion: str = "no-preference"):
    """The bingo page in this profile, its fonts in and the preview card drawn. motion: the device's reduced-motion
    setting for this page ("no-preference" here, the most common; ReducedMotion checks "reduce")."""
    path = bingo_path(lang)
    page = ctx.new_page()
    page.emulate_media(reduced_motion=motion)
    if errors is not None:
        watch(page, errors, "/" + path + hash)
    answered(page.goto(url(path + hash), wait_until="load", timeout=60_000), path)
    page.evaluate("async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; }")
    page.wait_for_selector(".bgo-stage .bgo-card", timeout=15_000)
    settle(page)
    return page


def data(page) -> dict:
    """The page's #bingo-data (the squares, bingo.info, the card words of both languages, the builder's words)."""
    return page.evaluate("() => JSON.parse(document.getElementById('bingo-data').textContent)")


def card_words(items: list, lang: str) -> set[str]:
    """Every square's words a card in `lang` may show: the text, and the short words of the big grids, {event} as the
    card says it when no event is named ("this event" / "este evento")."""
    this = w("bingo.card.this_event", lang)
    out = set()
    for it in items:
        for k in ("text", "short"):
            v = (it.get(k) or {}).get(lang) or ""
            if v:
                out.add(v.replace("{event}", this))
    return out


# One card as drawn: its squares (row by row), how they are laid out, and what sticks out
CARD = """(root) => {
  const card = document.querySelector(root + " .bgo-card");
  if (!card) return null;
  const cells = [...card.querySelectorAll(".bgo-cell")];
  const clean = (t) => (t || "").replace(/\\u200b/g, "");
  const words = (c) => clean((c.querySelector(".bgo-w") || c).textContent);
  const sticks = (b) => !b || b.scrollHeight > b.clientHeight + 1 || b.scrollWidth > b.clientWidth + 1;
  const text = (sel) => clean((card.querySelector(sel) || {}).textContent);
  return { lang: card.lang, dense: card.getAttribute("data-dense"), n: cells.length,
           rows: new Set(cells.map((c) => c.offsetTop)).size, cols: new Set(cells.map((c) => c.offsetLeft)).size,
           types: cells.map((c) => c.getAttribute("data-type")), words: cells.map(words),
           over: cells.filter((c) => sticks(c.querySelector(".bgo-txt")))
                      .map((c) => words(c) + " (" + ((c.querySelector(".bgo-w") || {}).style || {}).fontSize + ")"),
           title: text(".bgo-title"), meta: text(".bgo-meta"), rulesH: text(".bgo-rules .bgo-h"),
           info: text(".bgo-info"), infoH: text(".bgo-info .bgo-h"),
           lines: [...card.querySelectorAll(".bgo-info .bgo-li")].map((p) => clean(p.textContent)) };
}"""
# What "Print or save as PDF" put in #bgo-print: the sheets, each card's squares and footer, the @page rule — and,
# measured while the page is emulated as printed (the sheets laid out on paper), the words that stick out, the text
# under 6 pt (8 px: a square's words apart from the rest), the side columns that run over and the meetings strips
# that reach the small print
PRINTED = """() => {
  const root = document.getElementById("bgo-print");
  const clean = (t) => (t || "").replace(/\\u200b/g, "");
  const cards = [...root.querySelectorAll(".bgo-card")];
  const over = [...root.querySelectorAll(".bgo-cell .bgo-txt")]
    .filter((b) => b.scrollHeight > b.clientHeight + 1 || b.scrollWidth > b.clientWidth + 1)
    .map((b) => clean(b.textContent));
  const small = [], smallWords = [];
  for (const e of root.querySelectorAll(".bgo-card *")) {
    if (![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const px = parseFloat(getComputedStyle(e).fontSize);
    if (px < 8 - 0.02) (e.closest(".bgo-w") ? smallWords : small).push(clean(e.textContent).trim().slice(0, 50) + " (" + (px * 0.75).toFixed(2) + " pt)");
  }
  const box = (a, sel) => (a.querySelector(sel) || { getBoundingClientRect: () => null }).getBoundingClientRect();
  // a word broken across two lines: two letters or digits on two lines with nothing between them (a zero-width space
  // is a place to break: bingo.js breakable / labelText) — the element's text, else null
  const broken = (e) => {
    const walk = document.createTreeWalker(e, NodeFilter.SHOW_TEXT), rg = document.createRange();
    let prevTop = null, prev = "";
    for (let t = walk.nextNode(); t; t = walk.nextNode()) {
      const s = t.textContent;
      for (let i = 0; i < s.length; i++) {
        if (!/[\\p{L}\\p{N}]/u.test(s[i])) { prev = ""; continue; }
        rg.setStart(t, i); rg.setEnd(t, i + 1);
        const r = rg.getClientRects()[0];
        if (!r) continue;
        if (prev && prevTop !== null && r.top - prevTop > r.height * 0.5) return clean(e.textContent);
        prevTop = r.top; prev = s[i];
      }
    }
    return null;
  };
  const brokenIn = (sel) => [...new Set(cards.flatMap((a) => [...a.querySelectorAll(sel)].map(broken).filter(Boolean)))];
  // a time range ("7 – 8 PM", "7–8 p. m.") or a time and its AM / PM ("7 PM", "8 PM", "7 p. m.") on two lines: its
  // first and last characters on two lines — the element's text, else null
  const rangeSplit = (e) => {
    const walk = document.createTreeWalker(e, NodeFilter.SHOW_TEXT), rg = document.createRange(), at = [];
    for (let t = walk.nextNode(); t; t = walk.nextNode()) for (let i = 0; i < t.textContent.length; i++) at.push([t, i]);
    const s = at.map(([t, i]) => t.textContent[i]).join("");
    const re = /\\d\\s?\\u2013\\s?\\d|\\d\\s?(?:[AP]M\\b|[ap]\\.\\s?m\\.)/g;
    const top = (k) => { rg.setStart(at[k][0], at[k][1]); rg.setEnd(at[k][0], at[k][1] + 1); const r = rg.getClientRects()[0]; return r ? r.top : null; };
    for (let m = re.exec(s); m; m = re.exec(s)) {
      const a = top(m.index), b = top(m.index + m[0].length - 1);
      if (a !== null && b !== null && Math.abs(b - a) > 2) return clean(e.textContent);
      re.lastIndex = m.index + 1;             // (the range's last hour starts a time too: "8 PM" in "7 – 8 PM")
    }
    return null;
  };
  const rangeIn = (sel) => [...new Set(cards.flatMap((a) => [...a.querySelectorAll(sel)].map(rangeSplit).filter(Boolean)))];
  return { sheets: root.querySelectorAll(".bgo-sheet").length,
           cards: cards.map((a) => [...a.querySelectorAll(".bgo-cell .bgo-w")].map((x) => clean(x.textContent))),
           metas: cards.map((a) => clean((a.querySelector(".bgo-meta") || {}).textContent)),
           subs: cards.map((a) => clean((a.querySelector(".bgo-sub") || {}).textContent)),
           layouts: [...new Set(cards.map((a) => a.getAttribute("data-layout")))],
           small: [...new Set(small)], smallWords: [...new Set(smallWords)],
           sideOver: cards.filter((a) => { const s = a.querySelector(".bgo-side"); return s && s.scrollHeight > s.clientHeight + 1; }).length,
           stripLow: cards.filter((a) => { const i = box(a, ".bgo-info"), f = box(a, ".bgo-foot"); return i && f && i.bottom > f.top + 1; }).length,
           stripBroken: brokenIn(".bgo-info .bgo-li"), labelBroken: brokenIn(".bgo-lab:not(.is-hy)"),
           rangeBroken: rangeIn(".bgo-info .bgo-li, .bgo-cell .bgo-w"),
           tight: root.querySelectorAll(".bgo-cell.is-tight").length,
           over, page: (document.getElementById("bgo-page") || {}).textContent || "",
           mode: document.documentElement.getAttribute("data-print") };
}"""


def card(page, root: str = ".bgo-stage") -> dict:
    got = page.evaluate(CARD, root)
    if not got:
        raise AssertionError(f"no card in {root}")
    return got


def grid(page, rows: int, cols: int) -> None:
    """A preset chip (3×3 … 10×10), or Custom's rows and columns; then the preview drawn at that grid."""
    if rows == cols:
        page.click(f".bgo-chip-grid:text-is('{rows}×{cols}')")
    else:
        if not page.locator("#bgo-rows").is_visible():
            page.click(".bgo-chip-grid[aria-controls=bgo-custom]")
        page.select_option("#bgo-rows", str(rows))
        page.select_option("#bgo-cols", str(cols))
    page.wait_for_function("""([r, c]) => { const a = document.querySelector(".bgo-stage .bgo-card");
        return !!a && a.style.getPropertyValue("--rows") === String(r) && a.style.getPropertyValue("--cols") === String(c); }""",
                           arg=[rows, cols], timeout=10_000)
    settle(page)


def chip(page, group: str, index: int) -> None:
    """The index-th chip of a labelled group of chips (bgo-paper-l, bgo-per-l, …), clicked: then it is on."""
    btn = page.locator(f"[aria-labelledby={group}] button").nth(index)
    btn.click()
    settle(page)
    if btn.get_attribute("aria-pressed") != "true":
        raise AssertionError(f"{group} chip {index} did not turn on")


def per_sheet(page, n: int) -> None:
    chip(page, "bgo-per-l", [1, 2, 4].index(n))


def orient(page, o: str) -> None:
    chip(page, "bgo-orient-l", ["portrait", "landscape"].index(o))


# the rows of "Choose squares yourself" as drawn: the square's words, its two boxes, the "Always" box's whole name
PICK_ROWS = """() => [...document.querySelectorAll(".bgo-pick-row")].map((li) => {
  const sp = (t) => (t || "").replace(/\\s+/g, " ").trim();
  return { text: sp(li.querySelector(".bgo-pick-text").textContent), on: li.querySelector(".bgo-pick-use input").checked,
           pin: li.querySelector(".bgo-pick-pin input").checked, pinName: sp(li.querySelector(".bgo-pick-pin").textContent) }; })"""


def open_kinds(page) -> None:
    """"Choose squares yourself" opened, and each kind of square in it (folded until opened: its rows are drawn only
    while it is open)."""
    page.click("summary.bgo-pick-sum")
    page.wait_for_selector("details.bgo-pick-group > summary", timeout=5_000)
    page.evaluate("() => document.querySelectorAll('details.bgo-pick-group:not([open]) > summary').forEach((s) => s.click())")
    page.wait_for_selector(".bgo-pick-row", state="visible", timeout=5_000)
    settle(page)


def pdf_pages(pdf: bytes) -> list[tuple[float, float]]:
    """The PDF's pages, each its size in points: read off the file itself — its /Type /Page objects and their
    /MediaBox, as Chrome writes them (as test_r12_u5_gvr.py counts pages). No PDF library: the browser job installs
    only scripts/ops/requirements-browser.txt (tests/test_automation.py BrowserChecksPackages)."""
    n = len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", pdf))
    boxes = []
    for m in re.finditer(rb"/MediaBox\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\]", pdf):
        x0, y0, x1, y1 = (float(v) for v in m.groups())
        boxes.append((x1 - x0, y1 - y0))
    if len(boxes) != n:                     # (a box given once for every page: the same size each)
        boxes = [boxes[0] if boxes else (0.0, 0.0)] * n
    return boxes


def print_cards(page, pdf: bool = True) -> dict:
    """"Print or save as PDF", the browser's print window stubbed: the sheets the button makes (PRINTED, measured as
    printed; took: the seconds from the click to the print window) and — pdf — the browser's own PDF of them at the
    page's @page size; then the print is over (afterprint)."""
    page.evaluate("() => { window.__printed = 0; window.print = () => { window.__printed++; }; }")
    start = time.monotonic()
    page.click(".bgo-print-btn")
    page.wait_for_function("() => window.__printed > 0", timeout=30_000)
    took = time.monotonic() - start
    page.emulate_media(media="print")
    try:
        got = page.evaluate(PRINTED)
        got["took"] = took
        if pdf:
            got["pdf"] = pdf_pages(page.pdf(prefer_css_page_size=True))
    finally:
        page.emulate_media(media="screen")
        page.evaluate("() => window.dispatchEvent(new Event('afterprint'))")
    return got


# ----------------------------------------------------------------------------------------------- starts
class Starts(unittest.TestCase):
    def test_the_builder_starts_and_runs_without_an_error(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                errors: list[str] = []
                try:
                    page = open_bingo(ctx, lang, errors=errors)
                    self.assertFalse(page.locator(".bgo-alert").is_visible(), "the builder started")
                    self.assertFalse(page.locator(".bgo-alert-load").is_visible(), "bingo.js ran")
                    self.assertTrue(page.locator(".bgo-nojs").is_hidden(), "the no-JS sample is hidden")
                    self.assertTrue(page.locator(".bgo-print-btn").is_enabled())
                    self.assertEqual(page.locator(".bgo-pool.is-short").count(), 0, "enough squares for the default card")
                    self.assertEqual(page.inner_text(".bgo-pager-n").strip(), fmt(w("bingo.ui.card_n", lang), n=1, total=CARDS))
                    self.assertEqual(page.input_value("#bgo-count"), str(CARDS))
                    self.assertRegex(page.input_value("#bgo-code"), CODE)
                    first = card(page)
                    self.assertEqual((first["n"], first["lang"]), (25, lang), "a 5×5 card in the page's language")
                    # card 2: another card
                    page.locator(".bgo-pager button").nth(1).click()
                    page.wait_for_function("(t) => document.querySelector('.bgo-pager-n').textContent.trim() === t",
                                           arg=fmt(w("bingo.ui.card_n", lang), n=2, total=CARDS), timeout=5_000)
                    settle(page)
                    self.assertNotEqual(sorted(card(page)["words"]), sorted(first["words"]), "card 2 is another card")
                    # Choose squares yourself: a folded list for each kind of square (opened: all of them), and searched
                    open_kinds(page)
                    self.assertEqual(page.locator("details.bgo-pick-group").count(), len(data(page)["cats"]))
                    listed = page.locator(".bgo-pick-row").count()
                    self.assertGreater(listed, 100)
                    # each "Always" named with its square's words (a screen reader hears which); ticked only on a
                    # square in use — the three meeting and contact squares are
                    rows = page.evaluate(PICK_ROWS)
                    always = w("bingo.pick_always", lang)
                    self.assertEqual([r for r in rows if r["pinName"] != always + ": " + r["text"]], [])
                    self.assertEqual([r for r in rows if r["pin"] and not r["on"]], [])
                    self.assertGreaterEqual(len([r for r in rows if r["pin"]]), 3)
                    page.fill("#bgo-pick-q", "Grapevine")
                    page.wait_for_function("(n) => document.querySelectorAll('.bgo-pick-row').length < n", arg=listed, timeout=5_000)
                    self.assertGreater(page.locator(".bgo-pick-row").count(), 0)
                    page.wait_for_timeout(200)
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()

    def test_without_its_script_the_page_says_so(self):
        """bingo.js blocked (a bad connection, a blocker): the notice outside the builder (.bgo-alert-load, Alpine
        alone) says the builder could not start, with its Reload button."""
        ctx = new_context(1280, 900)
        try:
            page = ctx.new_page()
            page.route(re.compile(r"/assets/js/bingo\.js(\?|$)"), lambda route: route.abort())
            answered(page.goto(url(bingo_path("en")), wait_until="load", timeout=60_000), bingo_path("en"))
            page.wait_for_selector(".bgo-alert-load", state="visible", timeout=10_000)
            self.assertIn(w("bingo.broken_title", "en"), page.inner_text(".bgo-alert-load"))
            self.assertTrue(page.locator(".bgo-alert-load button").is_visible())
        finally:
            ctx.close()


# ----------------------------------------------------------------------------------------------- grids
class Grids(unittest.TestCase):
    maxDiff = None

    def test_every_grid_has_its_squares_and_every_squares_words_fit(self):
        problems: list[str] = []
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            errors: list[str] = []
            try:
                page = open_bingo(ctx, lang, errors=errors)
                items = data(page)["items"]
                allowed = card_words(items, lang)
                for rows, cols in PRESETS + RECTANGLES:
                    with self.subTest(lang=lang, grid=f"{rows}×{cols}"):
                        grid(page, rows, cols)
                        c = card(page)
                        label = f"/{bingo_path(lang)} {rows}×{cols}"
                        self.assertEqual(c["lang"], lang, label)
                        self.assertEqual((c["n"], c["rows"], c["cols"]), (rows * cols, rows, cols), f"{label}: squares and their layout")
                        free = [i for i, t in enumerate(c["types"]) if t == "free"]
                        self.assertEqual(free, [(rows // 2) * cols + cols // 2] if rows % 2 and cols % 2 else [],
                                         f"{label}: the FREE square only on odd × odd grids, in the middle")
                        squares = [x for x, t in zip(c["words"], c["types"]) if t != "free"]
                        self.assertEqual(len(squares), len(set(squares)), f"{label}: a square twice on one card")
                        self.assertEqual([x for x in squares if x not in allowed], [], f"{label}: words that are no square's")
                        if max(rows, cols) >= 7:
                            self.assertEqual(c["dense"], "1", f"{label}: a big grid takes the short words")
                        if c["over"]:
                            problems.append(f"{label}: words stick out: {c['over']}")
                self.assertEqual(errors, [])
            finally:
                ctx.close()
        self.assertEqual(problems, [])


# ----------------------------------------------------------------------------------------------- printing
class Printing(unittest.TestCase):
    # (rows, cols, cards on a sheet, orientation) for each paper; WIDE: the grid beside the column (data-layout)
    RUNS = {"letter": [(5, 5, 1, "portrait"), (5, 5, 2, "portrait"), (4, 4, 4, "portrait"), (5, 5, 2, "landscape"),
                       (4, 4, 4, "landscape"), (3, 5, 2, "portrait")],
            "a4": [(5, 5, 1, "portrait"), (5, 5, 2, "portrait"), (4, 4, 4, "portrait"), (4, 4, 4, "landscape"),
                   (10, 10, 1, "landscape"), (3, 5, 2, "landscape")]}
    WIDE = {(4, 4, 4, "landscape"), (10, 10, 1, "landscape")}

    def test_ten_cards_on_letter_and_a4_one_two_and_four_on_a_sheet(self):
        for lang, paper in (("en", "letter"), ("es", "a4")):
            ctx = new_context(1280, 900, lang=lang)
            errors: list[str] = []
            try:
                page = open_bingo(ctx, lang, errors=errors)
                chip(page, "bgo-paper-l", ["letter", "a4"].index(paper))
                code = page.input_value("#bgo-code")
                foot = data(page)["card"][lang]["foot"]
                for rows, cols, per, o in self.RUNS[paper]:
                    with self.subTest(lang=lang, paper=paper, grid=f"{rows}×{cols}", per_sheet=per, orient=o):
                        grid(page, rows, cols)
                        per_sheet(page, per)
                        orient(page, o)
                        preview = page.get_attribute(".bgo-stage .bgo-card", "data-layout")
                        got = print_cards(page)
                        sheets = math.ceil(CARDS / per)
                        self.assertEqual(got["mode"], "bingo", "the cards alone go on paper")
                        self.assertIn("size: " + ("A4" if paper == "a4" else "letter") + " " + o, got["page"])
                        self.assertEqual(got["sheets"], sheets)
                        pages = got["pdf"]
                        self.assertEqual(len(pages), sheets, f"{CARDS} cards, {per} on a sheet: {sheets} pages")
                        want = PAPER_PT[paper] if o == "portrait" else PAPER_PT[paper][::-1]
                        self.assertEqual([p for p in pages if abs(p[0] - want[0]) > 1.5 or abs(p[1] - want[1]) > 1.5], [],
                                         f"every page {paper} {o} size {want}")
                        self.assertEqual(len(got["cards"]), CARDS)
                        self.assertEqual(len({frozenset(c) for c in got["cards"]}), CARDS, "every card different")
                        self.assertEqual([i + 1 for i, c in enumerate(got["cards"]) if len(c) != len(set(c))], [],
                                         "a square twice on a card")
                        self.assertEqual([len(c) for c in got["cards"]], [rows * cols] * CARDS)
                        self.assertEqual([m for i, m in enumerate(got["metas"]) if not m.startswith(fmt(foot, n=i + 1, total=CARDS, code=code))],
                                         [], "each card's footer: Card n of 10 · Game CODE")
                        self.assertEqual(got["over"], [], "words sticking out on paper")
                        self.assertEqual((got["small"], got["smallWords"]), ([], []), "text under 6 pt on paper")
                        self.assertEqual(got["stripBroken"], [], "a word of the meetings strip broken in two")
                        self.assertEqual(got["rangeBroken"], [], "a meeting's time (7 – 8 PM, 7 PM) on two lines")
                        self.assertEqual((got["sideOver"], got["stripLow"]), (0, 0),
                                         "a side column running over, a meetings strip reaching the small print")
                        self.assertEqual(got["layouts"], [preview], "every card of the run laid out as the preview")
                        if (rows, cols, per, o) in self.WIDE:
                            self.assertIn(preview, ("side", "top"), "a wide card: the grid beside the column")
                        self.assertIsNone(page.evaluate("document.documentElement.getAttribute('data-print')"), "afterprint: back to the page")
                orient(page, "portrait")
                # All cards the same: one card, ten times
                with self.subTest(lang=lang, same=True):
                    page.locator("[aria-label='" + w("bingo.f_same_label", lang) + "'] .chip").nth(1).click()
                    settle(page)
                    got = print_cards(page, pdf=False)
                    self.assertEqual(len(got["cards"]), CARDS)
                    self.assertEqual(len({tuple(c) for c in got["cards"]}), 1, "all cards the same")
                self.assertEqual(errors, [])
            finally:
                ctx.close()


# ----------------------------------------------------------------------------------------------- a typed head
class TypedHead(unittest.TestCase):
    """A long typed event or title on the smallest cards (4 on a Letter portrait sheet): the squares keep 6 pt."""

    # (about 28 and 60 characters: the builder takes 60 at most)
    EVENTS = {"en": ["Garland Grapevine Workshop", "Spring Assembly 2027, District 14, Garland Civic Center, TX"],
              "es": ["Taller de La Viña en Garland", "Asamblea de Primavera 2027, Área 65, Centro Cívico Garland"]}
    TITLES = {"en": "Northeast Texas Area 65 Grapevine and La Viña Bingo Night!",
              "es": "Gran Bingo de La Viña y Grapevine del Área 65 del Noreste TX"}

    def test_a_long_event_or_title_on_four_cards_a_sheet(self):
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            errors: list[str] = []
            try:
                heads = [("", e) for e in self.EVENTS[lang]] + [(self.TITLES[lang], "")]
                for rows, cols in ((4, 4), (4, 3)):
                    for title, event in heads:
                        with self.subTest(lang=lang, grid=f"{rows}×{cols}", title=len(title), event=len(event)):
                            typed = ("title=" + quote(title)) if title else ("event=" + quote(event))
                            page = open_bingo(ctx, lang, f"#grid={rows}x{cols}&per=4&cards=4&lang={lang}&{typed}", errors)
                            try:
                                got = print_cards(page, pdf=False)
                                self.assertEqual(len(got["cards"]), 4)
                                self.assertEqual((got["small"], got["smallWords"]), ([], []), "text under 6 pt on paper")
                                self.assertEqual(got["tight"], 0, "a square that gave up its write-in line")
                                self.assertEqual(got["labelBroken"], [], "a label broken inside a word")
                                self.assertEqual(got["over"], [], "words sticking out on paper")
                                self.assertEqual(got["rangeBroken"], [], "a meeting's time on two lines")
                                if event:
                                    self.assertEqual([x for x in got["subs"] if not x.startswith(event)], [], "the event whole")
                            finally:
                                page.close()
                self.assertEqual(errors, [])
            finally:
                ctx.close()

    # a meeting link pasted as the event (one piece of 37 characters with no space), and a made-up word of 45 letters
    LONG_PIECES = [("en", 4, 4, "Zoom: https://us02web.zoom.us/j/83412345678"),
                   ("es", 3, 4, "Zoom: https://us02web.zoom.us/j/83412345678"),
                   ("en", 4, 4, "Supercalifragilisticexpialidociousgrapevinega")]

    def test_a_long_piece_with_no_space_never_costs_the_squares_their_6_pt(self):
        """The cards where such an event made the squares print at 5 pt in round 34's last review (the column beside
        the grid made wider to keep the piece whole): 4×4 in English and 3×4 in Spanish, four on a Letter landscape
        sheet. The link breaks after its "/" and its dots (GVBingo.headPieces, bingo.js headIn), the made-up word
        anywhere; a wider column only when its squares lose little and no square its 6 pt (bingo.js chooseLayout,
        placeCard). Printed: every square's words at 6 pt or more, no square giving up its write-in line, nothing
        sticking out, and the event whole at the top (on two lines or more)."""
        for lang, rows, cols, event in self.LONG_PIECES:
            with self.subTest(lang=lang, grid=f"{rows}×{cols}", event=event[:12]):
                ctx = new_context(1280, 900, lang=lang)
                errors: list[str] = []
                try:
                    page = open_bingo(ctx, lang, f"#grid={rows}x{cols}&per=4&cards=4&orient=landscape&lang={lang}"
                                                 f"&event={quote(event, safe='')}", errors)
                    got = print_cards(page, pdf=False)
                    self.assertEqual(len(got["cards"]), 4)
                    self.assertEqual((got["small"], got["smallWords"]), ([], []), "text under 6 pt on paper")
                    self.assertEqual(got["tight"], 0, "a square that gave up its write-in line")
                    self.assertEqual(got["over"], [], "words sticking out on paper")
                    self.assertEqual((got["sideOver"], got["stripLow"]), (0, 0), "the side column running over")
                    self.assertEqual(got["stripBroken"], [], "a word of the meetings strip broken in two")
                    self.assertEqual(got["rangeBroken"], [], "a meeting's time (7 – 8 PM, 7 PM) on two lines")
                    self.assertEqual([x for x in got["subs"] if not x.startswith(event)], [], "the event whole")
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()

    # a hand-picked set of 17 short squares (Choose squares yourself), one of them a name square whose label fills it
    # when the squares are small ("Nombre y estado o país"), and a long title and event: round 34's last review
    PICKED = ["people-check-greet-door", "service-register-gvr", "people-sign-newcomer", "people-thank-organizer",
              "service-old-issues", "service-register-rlv", "service-volunteer-workshop", "service-gvr-kit",
              "service-rlv-kit", "write-letter-lv", "listen-lv-app", "listen-asl", "service-rlv-manual",
              "service-help-table", "people-sign-gvr", "people-sign-rlv", "people-online-far"]
    PICKED_HEAD = {"title": "Grapevine and La Viña Bingo at the Fall Assembly in Dallas T",
                   "event": "Northeast Texas Area 65 Fall Assembly and Workshop Day 2027"}

    def test_hand_picked_squares_from_a_link_keep_their_6_pt(self):
        """A Spanish 4×4 card, four on a Letter portrait sheet, no meetings & contact squares, only the PICKED squares,
        opened from its settings link in a fresh profile: in round 34's last review "Se conecta desde lejos" printed at
        5.5 pt. Tried with the long meeting lines first, at squares so small that its label took the whole square, it
        was taken for a square that fits — and kept as one for the bigger squares tried after (bingo.js floorMisses:
        a words' box with no height is a miss). Printed: every square's words at 6 pt or more, no square giving up its
        write-in line, nothing sticking out, the event whole. Skipped, saying so, when the committee's CSV no longer
        has one of these squares."""
        ctx = new_context(1280, 900, lang="es")
        errors: list[str] = []
        try:
            page = open_bingo(ctx, "es", "#grid=4x4&code=K7Q2&lang=es&date=2026-11-18", errors)
            items = data(page)["items"]
            ids = {it["id"] for it in items}
            gone = [i for i in self.PICKED if i not in ids]
            if gone:
                self.skipTest(f"content/bingo/bingo.csv no longer has {gone}: this case of round 34 does not apply")
            # the link as the builder writes it (GVBingo.encode, "Copy a link to these settings")
            link = page.evaluate("""([picked, ids, head]) => {
                const pick = {}; ids.forEach((id) => { pick[id] = picked.includes(id) ? 1 : 0; });
                return window.GVBingo.encode(Object.assign({}, window.GVBingo.DEFAULTS, head, { rows: 4, cols: 4,
                  code: "K7Q2", count: 4, perSheet: 4, paper: "letter", orient: "portrait", infoMax: 0, lang: "es",
                  date: "2026-11-18", pick })); }""", [self.PICKED, sorted(ids), self.PICKED_HEAD])
            ctx.close()
            ctx = new_context(1280, 900, lang="es")
            page = open_bingo(ctx, "es", link, errors)
            got = print_cards(page, pdf=False)
            self.assertEqual(len(got["cards"]), 4)
            mine = card_words([it for it in items if it["id"] in self.PICKED], "es")
            self.assertEqual([x for c in got["cards"] for x in c if x not in mine], [], "the picked squares, and no other")
            self.assertEqual((got["small"], got["smallWords"]), ([], []), "text under 6 pt on paper")
            self.assertEqual(got["tight"], 0, "a square that gave up its write-in line")
            self.assertEqual(got["over"], [], "words sticking out on paper")
            self.assertEqual([x for x in got["subs"] if not x.startswith(self.PICKED_HEAD["event"])], [], "the event whole")
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    # the preview's head, its meeting lines and the note under the Event box
    HEAD = """() => { const a = document.querySelector(".bgo-stage .bgo-card"), help = document.getElementById("bgo-head-help");
      return { sub: (a.querySelector(".bgo-sub") || {}).textContent || "", titleSize: a.querySelector(".bgo-title").style.fontSize,
               strip: a.querySelector(".bgo-info").textContent, help: !!help && help.offsetParent !== null,
               helpText: help ? help.innerText.trim() : "", described: document.getElementById("bgo-event").getAttribute("aria-describedby") }; }"""

    def test_the_head_gets_smaller_only_when_the_meeting_place_needs_it(self):
        """A 60-character title and event on English cards, 4 on an A4 portrait sheet: the "mid" meeting lines (with the
        place) keep every square at 6 pt with the head as typed, so the head stays whole — full size, the long date,
        the year not alone on its line — and the note under the Event box stays hidden (bingo.js placeCard: the head
        is made smaller only when even the "mid" lines need it). A Spanish 60-character title on a Letter sheet does
        need it: the note shows, says to print fewer cards on a sheet, and the Event box points to it."""
        title, event = self.TITLES["en"], self.EVENTS["en"][1]
        ctx = new_context(1280, 900, lang="en")
        errors: list[str] = []
        try:
            page = open_bingo(ctx, "en", f"#grid=4x4&per=4&cards=4&paper=a4&lang=en&date=2026-11-18&title={quote(title)}&event={quote(event)}", errors)
            got = page.evaluate(self.HEAD)
            self.assertEqual(got["sub"], f"{event} · Wednesday, November 18,\u00a02026", "the event and its long date")
            self.assertEqual(got["titleSize"], "", "the title at its own size")
            self.assertEqual(got["strip"].count(PLATFORM), 2, f"{PLATFORM} for both meetings: {got['strip']}")
            self.assertFalse(got["help"], "no note under the Event box")
            self.assertEqual(got["described"], "bgo-event-help")
            page.close()
            ctx.close()
            ctx = new_context(1280, 900, lang="es")
            page = open_bingo(ctx, "es", f"#grid=4x4&per=4&cards=4&lang=es&title={quote(self.TITLES['es'])}", errors)
            got = page.evaluate(self.HEAD)
            self.assertNotEqual(got["titleSize"], "", "the title smaller")
            self.assertTrue(got["help"], "the note under the Event box")
            self.assertEqual(got["helpText"], w("bingo.f_head_long", "es") + " " + w("bingo.f_head_fix_sheet", "es"))
            self.assertEqual(got["described"], "bgo-event-help bgo-head-help")
            self.assertEqual(errors, [])
        finally:
            ctx.close()


# ----------------------------------------------------------------------------------------------- the link
def all_cards(page) -> list[list[str]]:
    """Every card of the run, as printed: its head's event · date line, then the squares' words, row by row."""
    got = print_cards(page, pdf=False)
    return [[sub, *c] for sub, c in zip(got["subs"], got["cards"])]


class Link(unittest.TestCase):
    def test_the_same_link_makes_the_same_cards(self):
        errors: list[str] = []
        ctx = new_context(1280, 900)
        try:
            page = open_bingo(ctx, "en", errors=errors)
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=page.evaluate("() => location.origin"))
            grid(page, 4, 4)
            page.fill("#bgo-event", "Spring Assembly 2027")
            page.click(".bgo-chip-cat:has-text('" + w("bingo.cat.fun", "en") + "')")
            page.click(".chip[lang=es]")
            settle(page)
            page.click("button:has-text('" + w("bingo.copy_link", "en") + "')")
            page.wait_for_function("() => location.hash.length > 1", timeout=5_000)
            link = page.url
            self.assertEqual(page.evaluate("navigator.clipboard.readText()"), link, "the link copied is the page's address")
            hash = link[link.index("#"):]
            for key in ("grid=4x4", "code=" + page.input_value("#bgo-code"), "lang=es", "off=fun", "event="):
                self.assertIn(key, hash)
            cards = all_cards(page)
            self.assertEqual(len(cards), CARDS)
            self.assertEqual(len(cards[0]), 1 + 16)
            self.assertEqual([c[0] for c in cards if not c[0].startswith("Spring Assembly 2027 · ")], [], "the event on every card")
            # after a reload
            page.reload(wait_until="load")
            page.wait_for_selector(".bgo-stage .bgo-card", timeout=15_000)
            settle(page)
            self.assertEqual(all_cards(page), cards, "after a reload")
        finally:
            ctx.close()
        # a fresh profile (nothing remembered), on this page and on the other language's
        for lang in ("en", "es"):
            with self.subTest(fresh=lang):
                ctx = new_context(1280, 900, lang=lang)
                try:
                    page = open_bingo(ctx, lang, hash, errors=errors)
                    self.assertEqual(card(page)["lang"], "es")
                    self.assertEqual(page.input_value("#bgo-event"), "Spring Assembly 2027")
                    self.assertEqual(all_cards(page), cards, f"the link on /{bingo_path(lang)} in a fresh profile")
                finally:
                    ctx.close()
        # a broken link: ignored (the defaults)
        ctx = new_context(1280, 900)
        try:
            page = open_bingo(ctx, "en", "#grid=99x2&code=!!&cards=900&lang=xx", errors=errors)
            c = card(page)
            self.assertEqual((c["n"], c["lang"]), (25, "en"))
            self.assertEqual(page.input_value("#bgo-count"), str(CARDS))
            self.assertRegex(page.input_value("#bgo-code"), CODE)
        finally:
            ctx.close()
        self.assertEqual(errors, [])


# ----------------------------------------------------------------------------------------------- card language
class CardLanguage(unittest.TestCase):
    def check(self, page, lang: str, items: list, where: str) -> None:
        c = card(page)
        self.assertEqual(c["lang"], lang, where)
        self.assertEqual(c["title"], w("bingo.card.title", lang), where)
        self.assertEqual(c["rulesH"], w("bingo.card.rules_h", lang), where)
        self.assertEqual(c["infoH"], w("bingo.card.info_h", lang), where)
        self.assertTrue(c["meta"].startswith(fmt(w("bingo.card.foot", lang), n=1, total=CARDS, code=page.input_value("#bgo-code"))), c["meta"])
        free = [x for x, t in zip(c["words"], c["types"]) if t == "free"]
        self.assertEqual(free, [w("bingo.card.free", lang)], where)
        allowed = card_words(items, lang)
        self.assertEqual([x for x, t in zip(c["words"], c["types"]) if t != "free" and x not in allowed], [],
                         f"{where}: squares not in the card's language")

    def test_the_cards_language_apart_from_the_pages(self):
        for page_lang, other in (("en", "es"), ("es", "en")):
            with self.subTest(page=page_lang, card=other):
                ctx = new_context(1280, 900, lang=page_lang)
                errors: list[str] = []
                try:
                    page = open_bingo(ctx, page_lang, errors=errors)
                    items = data(page)["items"]
                    self.check(page, page_lang, items, f"/{bingo_path(page_lang)}: its own language first")
                    page.click(f".chip[lang={other}]")
                    settle(page)
                    self.assertEqual(page.get_attribute(f".chip[lang={other}]", "aria-pressed"), "true")
                    self.check(page, other, items, f"/{bingo_path(page_lang)}: the {other} card")
                    # the page's own words stay in its language
                    self.assertEqual(page.inner_text(".bgo-pager-n").strip(), fmt(w("bingo.ui.card_n", page_lang), n=1, total=CARDS))
                    page.click(f".chip[lang={page_lang}]")
                    settle(page)
                    self.check(page, page_lang, items, f"/{bingo_path(page_lang)}: back to its language")
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


# ----------------------------------------------------------------------------------------------- meetings strip
def strip_forms(lines: list[str], info: dict, cw: dict, lang: str) -> list[str]:
    """Which lines of each meeting (the Grapevine Meeting's, then the committee meeting's) a meetings strip's lines
    (CARD lines) are: "long", "mid" or "short" — as bingo.js fillStrip writes them: the long line after the meeting's
    whole name, the others after its short name — or "" (none of them)."""
    out = []
    for key, name, short in (("gvMeeting", "gv_meeting", "gv_meeting_short"), ("committeeMeeting", "committee_meeting", "committee_short")):
        found = [form for form, label, suf in (("long", name, ""), ("mid", short, "Mid"), ("short", short, "Short"))
                 if (info.get(key + suf) or {}).get(lang) and f"{cw[label]}: {info[key + suf][lang]}" in lines]
        out.append(found[0] if found else "")
    return out


class MeetingsStrip(unittest.TestCase):
    def test_the_strip_and_the_information_squares(self):
        self.assertTrue(EMAIL, "config/site.yml has the committee's e-mail")
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                errors: list[str] = []
                try:
                    page = open_bingo(ctx, lang, errors=errors)
                    d = data(page)
                    info, cw = d["info"], d["card"][lang]
                    self.assertEqual(info["email"], EMAIL)
                    for k in ("gvMeeting", "committeeMeeting", "gvMeetingMid", "committeeMeetingMid", "gvMeetingShort",
                              "committeeMeetingShort"):
                        self.assertTrue(info.get(k) and info[k].get(lang), f"#bingo-data info.{k}.{lang}")
                    # the whole card (one on a Letter sheet): the long lines — the day, the time and its zone, the place
                    c = card(page)
                    strip = c["info"]
                    self.assertEqual(strip_forms(c["lines"], info, cw, lang), ["long", "long"], c["lines"])
                    self.assertIn(cw["gv_meeting"] + ": " + info["gvMeeting"][lang], strip)
                    self.assertIn(cw["committee_meeting"] + ": " + info["committeeMeeting"][lang], strip)
                    self.assertIn(EMAIL, strip)
                    # (the e-mail may break after its "@" only: never "grapevine@neta65" / ".org" — bingo.js breakable)
                    raw = page.evaluate("() => document.querySelector('.bgo-stage .bgo-info').textContent")
                    self.assertIn(EMAIL.replace("@", "@\u200b"), raw, "the e-mail's one place to break")
                    self.assertIsNotNone(page.query_selector(".bgo-stage .bgo-info .bgo-qr use[href='#bgo-qr-" + lang + "']"),
                                         "the QR code of the card's language")
                    # the default card: the three "always" information squares — both meetings and the e-mail
                    infos = [x for x, t in zip(c["words"], c["types"]) if t == "info"]
                    short = c["dense"] == "1"
                    self.assertEqual(len(infos), 3, f"the default card's information squares: {infos}")
                    for k in ("gvMeeting", "committeeMeeting"):
                        line = info[k + ("Short" if short else "")][lang]
                        self.assertEqual(len([x for x in infos if line in x]), 1, f"a square with {line!r}: {infos}")
                    self.assertEqual(len([x for x in infos if EMAIL in x]), 1, f"a square with {EMAIL}: {infos}")
                    # a small card (4 on a Letter portrait sheet): the longest lines that fit (bingo.js measures: long,
                    # mid or short — which one depends on the room the squares leave), the same for both meetings —
                    # and with the meeting place in them (long or mid); the e-mail
                    grid(page, 4, 4)
                    per_sheet(page, 4)
                    small = card(page)
                    forms = strip_forms(small["lines"], info, cw, lang)
                    self.assertIn(forms[0], ("long", "mid"), f"a small card says where we meet: {small['lines']}")
                    self.assertEqual(forms[1], forms[0], f"both meetings in the same lines: {small['lines']}")
                    self.assertTrue(PLATFORM, "config/site.yml meeting.platform")
                    self.assertEqual(small["info"].count(PLATFORM), 2, f"{PLATFORM} for both meetings: {small['lines']}")
                    self.assertIn(EMAIL, small["info"])
                    # 0 meetings & contact squares: none on the card (the strip stays)
                    chip(page, "bgo-info-l", 0)
                    c = card(page)
                    self.assertEqual(c["types"].count("info"), 0)
                    self.assertIn(EMAIL, c["info"])
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


# ----------------------------------------------------------------------------------------------- phone
def rgb(css: str) -> tuple[int, int, int]:
    return tuple(int(float(v)) for v in re.findall(r"[\d.]+", css)[:3])


class Phone(unittest.TestCase):
    maxDiff = None

    def test_a_390_pixel_phone_in_light_and_dark(self):
        problems: list[str] = []
        for lang in ("en", "es"):
            for theme in ("light", "dark"):
                with self.subTest(lang=lang, theme=theme):
                    ctx = new_context(390, 844, lang=lang, theme=theme)
                    errors: list[str] = []
                    try:
                        page = open_bingo(ctx, lang, errors=errors)
                        self.assertEqual(page.evaluate("document.documentElement.getAttribute('data-theme')"), theme)
                        where = f"/{bingo_path(lang)} at 390px, {theme}"
                        open_kinds(page)
                        for step in ("the squares listed", "10×10"):
                            if step == "10×10":
                                grid(page, 10, 10)
                            r = page.evaluate(SIDEWAYS)
                            if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                                problems.append(f"{where}, {step}: scrolls {r['moved']} px sideways (page {r['scrollWidth']} px "
                                                f"wide in {r['width']}): {r['wide']}")
                            c = card(page)
                            if c["over"]:
                                problems.append(f"{where}, {step}: words stick out: {c['over']}")
                        # the card is paper: white, dark ink, in both themes
                        paper = page.evaluate("""() => { const a = document.querySelector(".bgo-stage .bgo-card"),
                            x = a.querySelector(".bgo-cell[data-type]:not([data-type=free]) .bgo-w");
                            return { bg: getComputedStyle(a).backgroundColor, ink: getComputedStyle(x).color }; }""")
                        self.assertEqual(rgb(paper["bg"]), (255, 255, 255), f"{where}: the card's paper")
                        self.assertGreaterEqual(contrast(rgb(paper["ink"]), (255, 255, 255)), 7, f"{where}: the card's ink {paper['ink']}")
                        self.assertEqual(errors, [])
                    finally:
                        ctx.close()
        self.assertEqual(problems, [])



# ----------------------------------------------------------------------------------------------- limits
# how the page is on paper while nothing has been prepared (the browser's own Print with too few squares): the
# settings' groups hidden, the note shown
ON_PAPER = """() => { const shown = (e) => !!e && e.getClientRects().length > 0;
  return { groups: [...document.querySelectorAll("fieldset.bgo-group")].filter(shown).length,
           note: shown(document.querySelector(".bgo-short")), mode: document.documentElement.getAttribute("data-print") }; }"""
# the squares' backgrounds on the preview card (of one type, or all)
BACKGROUNDS = """(type) => [...document.querySelectorAll(".bgo-stage .bgo-cell" + (type ? "[data-type=" + type + "]" : ""))]
  .map((c) => getComputedStyle(c).backgroundColor)"""


class Limits(unittest.TestCase):
    """The builder at its edges, on the English page (the steps one after the other, on one page)."""

    maxDiff = None

    def test_the_builder_at_its_edges(self):
        ctx = new_context(1280, 900)
        errors: list[str] = []
        try:
            page = open_bingo(ctx, "en", errors=errors)
            d = data(page)
            cw = d["card"]["en"]
            cats = page.locator(".bgo-chip-cat")
            others = [i for i, c in enumerate(d["cats"]) if c != "fun"]
            with self.subTest(step="a first visit's code kept"):
                first = page.input_value("#bgo-code")
                page.reload(wait_until="load")
                page.wait_for_selector(".bgo-stage .bgo-card", timeout=15_000)
                settle(page)
                self.assertEqual(page.input_value("#bgo-code"), first, "a reload gives the same cards")
            with self.subTest(step="too few squares"):
                # 10×10 with only "Just for fun": not enough squares — said (read aloud), the way out, Print waits
                grid(page, 10, 10)
                for i in others:
                    cats.nth(i).click()
                page.wait_for_selector(".bgo-pool.is-short", timeout=5_000)
                settle(page)
                line = re.escape(fmt(w("bingo.ui.pool_short", "en"), need=100)).replace(re.escape("{have}"), r"\d+")
                self.assertRegex(page.inner_text(".bgo-pool").strip(), "^" + line + "$")
                self.assertEqual(page.get_attribute(".bgo-pool", "aria-live"), "polite")
                self.assertTrue(page.locator(".bgo-short").is_visible())
                self.assertIn(w("bingo.ui.short_title", "en"), page.inner_text(".bgo-short"))
                self.assertTrue(page.locator(".bgo-print-btn").is_disabled(), "Print waits")
                self.assertTrue(page.locator(".bgo-stage").is_hidden())
                # the browser's own Print (Ctrl+P): one page, the note — not the form
                page.evaluate("() => window.dispatchEvent(new Event('beforeprint'))")
                page.emulate_media(media="print")
                try:
                    paper = page.evaluate(ON_PAPER)
                    pages = pdf_pages(page.pdf(prefer_css_page_size=True))
                finally:
                    page.emulate_media(media="screen")
                    page.evaluate("() => window.dispatchEvent(new Event('afterprint'))")
                    for i in others:                       # (the kinds back on, whatever the checks below say)
                        cats.nth(i).click()
                    page.wait_for_selector(".bgo-pool:not(.is-short)", timeout=5_000)
                self.assertEqual(paper, {"groups": 0, "note": True, "mode": None})
                self.assertEqual(len(pages), 1, "the note on one page")
                self.assertTrue(page.locator(".bgo-print-btn").is_enabled())
            with self.subTest(step="black and white"):
                grid(page, 5, 5)
                self.assertNotIn("rgb(255, 255, 255)", page.evaluate(BACKGROUNDS, "info"), "in colour: the information squares tinted")
                chip(page, "bgo-ink-l", 1)
                self.assertEqual(page.get_attribute(".bgo-stage .bgo-card", "data-ink"), "bw")
                self.assertEqual(set(page.evaluate(BACKGROUNDS, "")), {"rgb(255, 255, 255)"}, "black and white: every square white")
                chip(page, "bgo-ink-l", 0)
            with self.subTest(step="the help lines"):
                small = page.locator(".bgo-help", has_text=w("bingo.f_small_squares", "en"))
                self.assertTrue(small.is_hidden(), "5×5, one on a sheet: room to write")
                grid(page, 7, 7)
                self.assertTrue(small.is_visible(), "7×7: little room to write")
                # a "How to play" too long for small cards: they print the short one, and the builder says so
                grid(page, 4, 4)
                per_sheet(page, 4)
                typed = "Walk around, meet people and talk about the magazines. " * 4
                page.fill("#bgo-rules", typed)
                page.wait_for_selector("#bgo-rules-help", state="visible", timeout=5_000)
                page.wait_for_function("(t) => (document.querySelector('.bgo-stage .bgo-rules-txt') || {}).textContent === t",
                                       arg=fmt(cw["rules_square_short"], n=4), timeout=5_000)
                per_sheet(page, 1)
                page.wait_for_selector("#bgo-rules-help", state="hidden", timeout=5_000)
                page.wait_for_function("(t) => ((document.querySelector('.bgo-stage .bgo-rules-txt') || {}).textContent || '').trim() === t",
                                       arg=typed.strip(), timeout=5_000)
                page.fill("#bgo-rules", "")
            with self.subTest(step="remembered, then Start over"):
                grid(page, 7, 7)
                page.fill("#bgo-event", "Fall Workshop 2027")
                page.wait_for_timeout(500)                     # (the typed words are kept a moment after the last key)
                code = page.input_value("#bgo-code")
                page.reload(wait_until="load")
                page.wait_for_selector(".bgo-stage .bgo-card", timeout=15_000)
                settle(page)
                self.assertEqual((card(page)["n"], page.input_value("#bgo-event"), page.input_value("#bgo-code")),
                                 (49, "Fall Workshop 2027", code), "after a reload: the same settings")
                over = page.locator("[x-ref=overBtn]")
                over.click()
                page.wait_for_selector(".bgo-confirm", state="visible", timeout=5_000)
                self.assertIn(w("bingo.over_q", "en"), page.inner_text(".bgo-confirm"))
                self.assertEqual(page.evaluate("() => document.activeElement.textContent.trim()"), w("bingo.over_no", "en"),
                                 "the question asked: focus on Keep my settings")
                page.keyboard.press("Escape")
                page.wait_for_selector(".bgo-confirm", state="hidden", timeout=5_000)
                self.assertEqual((card(page)["n"], page.input_value("#bgo-event")), (49, "Fall Workshop 2027"), "Escape keeps them")
                over.click()
                page.locator(".bgo-confirm button", has_text=w("bingo.over_yes", "en")).click()
                page.wait_for_selector(".bgo-confirm", state="hidden", timeout=5_000)
                settle(page)
                fresh = page.input_value("#bgo-code")
                self.assertEqual((card(page)["n"], page.input_value("#bgo-event"), page.input_value("#bgo-count")), (25, "", str(CARDS)))
                self.assertRegex(fresh, CODE)
                self.assertNotEqual(fresh, code, "a new code")
                page.reload(wait_until="load")
                page.wait_for_selector(".bgo-stage .bgo-card", timeout=15_000)
                self.assertEqual(page.input_value("#bgo-code"), fresh, "a reload keeps the new start")
            with self.subTest(step="60 cards of 10×10"):
                grid(page, 10, 10)
                page.fill("#bgo-count", "60")
                page.press("#bgo-count", "Tab")
                page.wait_for_function("(t) => document.querySelector('.bgo-pager-n').textContent.trim() === t",
                                       arg=fmt(w("bingo.ui.card_n", "en"), n=1, total=60), timeout=5_000)
                got = print_cards(page, pdf=False)
                self.assertEqual((got["sheets"], len(got["cards"])), (60, 60))
                self.assertEqual(len({frozenset(c) for c in got["cards"]}), 60, "every card different")
                self.assertEqual(got["over"], [], "words sticking out on paper")
                self.assertLess(got["took"], 15, f"60 cards of 10×10 ready for the print window in {got['took']:.1f} s")
                self.assertTrue(page.locator(".bgo-busy").is_hidden(), "the busy line gone")
            self.assertEqual(errors, [])
        finally:
            ctx.close()


# ----------------------------------------------------------------------------------------------- reduced motion
class ReducedMotion(unittest.TestCase):
    """Motion reduced — the device's setting (prefers-reduced-motion) or the site's own "Aa" one (gvlv-prefs motion
    "reduce": html[data-motion="reduce"]) — must not change the cards: every square's words still fit, on screen and
    on paper.

    Round 34 found that main.css's two reduced-motion rules (@layer base: transition-duration 0.01ms !important on
    every element, transition-property still "all") held a square's new font size back for a frame, so bingo.js
    fitCards measured the OLD size and the words stuck out (19–20 pt: every square of a 3×3 card). The booth had the
    very same trouble (src/assets/css/areas/booth.css: "…and no transitions"); src/assets/css/areas/bingo.css now
    gives the card and everything in it — the preview and #bgo-print's sheets — transition-property: none under both
    rules, as booth.css does for the booth's screen. This class keeps it that way."""

    maxDiff = None

    def test_the_words_still_fit_with_motion_reduced(self):
        problems: list[str] = []
        errors: list[str] = []
        for how, motion, prefs in (("the device's setting", "reduce", None),
                                   ("the site's Aa setting", "no-preference", {"motion": "reduce"})):
            for lang in ("en", "es"):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_bingo(ctx, lang, errors=errors, motion=motion)
                    where = f"/{bingo_path(lang)}, motion reduced ({how})"
                    if prefs:
                        self.assertEqual(page.evaluate("document.documentElement.getAttribute('data-motion')"), "reduce")
                    for rows, cols in ((3, 3), (5, 5), (10, 10), (4, 6)):
                        grid(page, rows, cols)
                        c = card(page)
                        if c["over"]:
                            problems.append(f"{where}, {rows}×{cols}: {len(c['over'])} squares' words stick out, e.g. {c['over'][:2]}")
                    grid(page, 5, 5)
                    got = print_cards(page)
                    self.assertEqual(len(got["pdf"]), CARDS, where)
                    if got["over"]:
                        problems.append(f"{where}, printed 5×5: {len(got['over'])} squares' words stick out on paper")
                finally:
                    ctx.close()
        self.assertEqual(errors, [])
        self.assertEqual(problems, [], "with motion reduced the squares' words must fit too (areas/bingo.css: no "
                                       "transitions on the card)")


# ----------------------------------------------------------------------------------------------- no JavaScript
class NoScript(unittest.TestCase):
    def test_the_sample_card_without_javascript(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = S["browser"].new_context(viewport={"width": 1280, "height": 900}, java_script_enabled=False,
                                               reduced_motion="reduce", service_workers="block",
                                               timezone_id="America/Chicago", locale="es-US" if lang == "es" else "en-US")
                try:
                    page = ctx.new_page()
                    path = bingo_path(lang)
                    answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
                    self.assertTrue(page.locator(".bgo-sample .bgo-card").is_visible(), "the sample card shows")
                    self.assertTrue(page.locator(".bgo-app").is_hidden(), "the builder is hidden")
                    self.assertIn(w("bingo.nojs_title", lang), page.inner_text(".bgo-nojs-note"))
                    # the squares the build drew: its words, from the CSV, in the page's language
                    items = json.loads(page.text_content("#bingo-data"))["items"]
                    c = card(page, ".bgo-sample")
                    self.assertEqual(c["lang"], lang)
                    self.assertEqual((c["n"], c["rows"], c["cols"]), (25, 5, 5))
                    self.assertEqual([i for i, t in enumerate(c["types"]) if t == "free"], [12])
                    allowed = card_words(items, lang)
                    self.assertEqual([x for x, t in zip(c["words"], c["types"]) if t != "free" and x not in allowed], [])
                    self.assertEqual(c["over"], [], "the sample's words fit")
                    self.assertTrue(c["meta"].startswith(fmt(w("bingo.card.foot", lang), n=1, total=1, code="")), c["meta"])
                    # it prints as it is: that one card, on one page
                    self.assertEqual(len(pdf_pages(page.pdf(prefer_css_page_size=True))), 1)
                finally:
                    ctx.close()


# ----------------------------------------------------------------------------------------------- the /gvr/ teaser
class Teaser(unittest.TestCase):
    def test_the_gvr_pages_button_goes_to_the_bingo_page(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                errors: list[str] = []
                try:
                    gvr = ("es/" if lang == "es" else "") + "gvr/"
                    page = open_page(ctx, gvr, errors)
                    self.assertGreater(page.locator("a[href='#bingo']").count(), 0, "the page nav has Bingo")
                    btn = page.locator("#bingo a.btn-primary")
                    self.assertEqual(btn.count(), 1)
                    self.assertIn(w("read.gvr.bingo_btn", lang), btn.inner_text())
                    self.assertTrue(btn.get_attribute("href").endswith("/" + bingo_path(lang)), btn.get_attribute("href"))
                    btn.click()
                    page.wait_for_url(re.compile(re.escape(url(bingo_path(lang))) + r"$"), timeout=15_000)
                    page.wait_for_selector(".bgo-stage .bgo-card", timeout=15_000)
                    self.assertEqual(card(page)["lang"], lang)
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
