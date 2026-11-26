"""Round 26b · the monthly posters in a real browser (tests/browser/__init__.py says how to run these; they share
test_site_in_browser.py's site server and browser). The owner: "every event of the month on the poster, with smaller
borders":

  * EveryDateFits — every month page the build has (poster_months: this month and the next 12), English and Spanish:
                    once the page has fitted its poster (src/assets/js/monthly.js: data-mp-fit), the poster holds every
                    date of the page's Dates list and, after them, the month's other happenings its message names (the
                    stores' offers, the price change: the same words), nothing overflows its column or the 1080 × 1350
                    sheet (the fit's own measure), each block is there once and in the reading order of its column, and
                    the type is 15px at least (7.5 pt on a Letter page).
  * PrintOnePage  — the busiest month's poster prints on one US Letter page, English and Spanish, every date on it.
  * MastheadClear — every month's masthead at its real size, fitted: the month's name, its year and the tagline never
                    touch (the y of July, the p of April, the g of August hang into the line below; the fit's measure
                    sees boxes, not letters — this compares what each one draws).
  * UnfittedClipped — the poster before its fit (or without JavaScript: the page's script blocked) has the build's
                    arrangement at the stylesheet's type: a busy month's column may lose its last lines, but no text
                    is drawn over another block's, and every date is whole inside its column (a Spanish poster starts
                    at a smaller type for it).
  * UseTheRoom    — round 27 (DESIGN-27 §B6: "use the empty space … the fitted type gets LARGER, never smaller"): every
                    month EN/ES, the fitted type is never smaller than the build's own arrangement reaches (the fit's
                    own search on the poster as built, the page's script blocked); a poster arranged otherwise keeps
                    every date's title 10 of its em wide at least (no title in four or five short lines); no column
                    spreads its blocks over its height; the month's name stays inside its column (the rule may move);
                    dates that flow on into the next column read on (at its head, no heading, the dates at the foot of
                    theirs).
  * NoDatesFits   — a poster whose dates block has only its "no dates" note (no list) still finishes its fit on every
                    layout whose dates may flow on into the next column.

Nothing here depends on today's date: the months are the build's, the dates are each page's own.
"""
from __future__ import annotations

import re
import unittest
from io import BytesIO

from .test_site_in_browser import S, new_context, open_page, poster_months, setUpModule, tearDownModule  # noqa: F401

FITTED_ATTR = "() => { const p = document.querySelector('[data-mp-poster]'); return !!p && p.hasAttribute('data-mp-fit'); }"

# The fitted poster against the page: its dates, its size and type, and the fit's own overflow measure (offsets: no
# scale, no tilt of the cork's cards) on every block, column and band.
CHECK = r"""() => {
  const p = document.querySelector("[data-mp-poster]");
  const BLOCKS = ".mp-b, .mp-foot, .mp-head, .mp-row, .mp-col, .mp-body, .mp-board, .mp-cover, .mp-strip, .mp-page, .mp-main, .mp-stub, .mp-side, .mp-content, .mp-top, .mp-feature, .mp-rail, .mp-band";
  const box = (el) => { let t = 0, l = 0, e = el; while (e && e !== p) { t += e.offsetTop; l += e.offsetLeft; e = e.offsetParent; } return { t, b: t + el.offsetHeight, r: l + el.offsetWidth }; };
  const over = [];
  p.querySelectorAll(BLOCKS).forEach((b) => {
    if (getComputedStyle(b).display === "none") return;
    const par = b.parentElement, bb = box(b);
    const pad = parseFloat(getComputedStyle(par).paddingBottom) || 0;
    const limit = par === p ? p.clientHeight - pad : box(par).t + par.clientTop + par.clientHeight - pad;
    if (bb.b > limit + 2) over.push(b.className + " +" + Math.round(bb.b - limit) + "px");
    if (bb.r > p.clientWidth + 2) over.push(b.className + " → +" + Math.round(bb.r - p.clientWidth) + "px");
  });
  // (a row's words without what only a screen reader hears: " (external)" after an outside link)
  const text = (el) => { const c = el.cloneNode(true); c.querySelectorAll(".sr-only, .mp-sr").forEach((s) => s.remove()); return c.textContent.replace(/\s+/g, " ").trim(); };
  const order = [];
  p.querySelectorAll("[data-mp-slot]").forEach((s) => {
    const o = [...s.children].filter((k) => k.hasAttribute("data-mp-order")).map((k) => Number(k.getAttribute("data-mp-order")));
    if (o.some((v, i) => i && v < o[i - 1])) order.push(s.getAttribute("data-mp-slot") + ": " + o.join(","));
  });
  // (the dates' rows that flow on into the next column, round 27, are the dates' own block continued)
  const kinds = [...p.querySelectorAll(".mp-b:not(.mp-dates--more)")].map((b) => [...b.classList].find((c) => c !== "mp-b" && c !== "mp-dates--cols"));
  return {
    size: p.offsetWidth + " x " + p.offsetHeight, font: parseFloat(getComputedStyle(p).fontSize),
    poster: [...p.querySelectorAll(".mp-dlist > li:not(.mp-date--offer, .mp-date--price) .mp-date-t")].map(text).sort(),
    page: [...document.querySelectorAll("#mp-dates li.mp-drow .mp-drow-t")].map(text).sort(),
    // the rows after the dates (macros/monthly.njk dates(), mpPosterExtras): "title | days" — and what the month's
    // message (WhatsApp, the page's language) names: 📦 / 🎁 an offer's heading and its days, 📢 the price change
    extras: [...p.querySelectorAll(".mp-dlist > li:is(.mp-date--offer, .mp-date--price)")].map((li) =>
      [li.querySelector(".mp-date-t"), li.querySelector(".mp-date-m")].filter(Boolean).map(text).join(" | ")),
    message: (() => {
      const msg = (document.getElementById("mp-msg-wa-one") || {}).textContent || "";
      return [...[...msg.matchAll(/^(?:📦|🎁) \*(.+)\*\n(.+): \S+$/gmu)].map((x) => x[1] + " | " + x[2]),
              ...[...msg.matchAll(/^📢 (.+): \S+$/gmu)].map((x) => x[1])];
    })(),
    more: !!p.querySelector(".mp-more"), over, order,
    twice: kinds.filter((k, i) => kinds.indexOf(k) !== i),
  };
}"""


class EveryDateFits(unittest.TestCase):
    def test_every_months_poster_holds_every_date(self):
        months = poster_months()
        self.assertGreaterEqual(len(months), 1, "month pages with their poster")
        problems: list[str] = []
        errors: list[str] = []
        ctx = new_context(1280, 900)
        try:
            for month in months:
                for lang in ("en", "es"):
                    path = ("es/" if lang == "es" else "") + f"monthly/{month}/"
                    page = open_page(ctx, path, errors)
                    page.wait_for_function(FITTED_ATTR, timeout=30_000)
                    r = page.evaluate(CHECK)
                    page.close()
                    where = f"/{path}"
                    if r["size"] != "1080 x 1350":
                        problems.append(f"{where}: the poster is {r['size']}")
                    if r["poster"] != r["page"]:
                        problems.append(f"{where}: the poster's dates {r['poster']} are not the page's {r['page']}")
                    if r["extras"] != r["message"]:
                        problems.append(f"{where}: the poster's offers and price change {r['extras']} are not the "
                                        f"message's {r['message']}")
                    if r["more"]:
                        problems.append(f"{where}: \"more on the website\"")
                    if r["over"]:
                        problems.append(f"{where}: overflows at {r['font']}px — {r['over'][:4]}")
                    if r["font"] < 15:
                        problems.append(f"{where}: type {r['font']}px")
                    if r["order"]:
                        problems.append(f"{where}: out of the reading order — {r['order']}")
                    if r["twice"]:
                        problems.append(f"{where}: twice on the poster — {r['twice']}")
        finally:
            ctx.close()
        self.assertEqual(errors, [])
        self.assertEqual(problems, [], "\n".join(problems))


class PrintOnePage(unittest.TestCase):
    def test_the_busiest_months_poster_prints_on_one_letter_page(self):
        months = poster_months()
        self.assertTrue(months)
        rows = {m: (S["site"] / "monthly" / m / "index.html").read_text(encoding="utf-8").count('class="mp-date mp-date--')
                for m in months}
        busiest = max(months, key=lambda m: (rows[m], m))
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            try:
                page = open_page(ctx, ("es/" if lang == "es" else "") + f"monthly/{busiest}/")
                page.wait_for_function(FITTED_ATTR, timeout=30_000)
                shown = page.evaluate("document.querySelectorAll('[data-mp-poster] .mp-dlist > li').length")
                page.emulate_media(media="print")
                pdf = page.pdf(prefer_css_page_size=True, print_background=True)
            finally:
                ctx.close()
            with self.subTest(month=busiest, lang=lang):
                self.assertEqual(shown, rows[busiest])
                self.assertEqual(len(re.findall(rb"/Type\s*/Page(?!s)", pdf)), 1, "one Letter page")
                self.assertIn(b"/MediaBox [0 0 612 792]", pdf.replace(b"  ", b" "))


def _isolate(wait_for_fit: bool) -> str:
    """The share picture's script (scripts/ops/poster_share.py ISOLATE): the poster out of its scaled frame, at its real
    size at the top left — without waiting for the fit when there is none."""
    from scripts.ops.poster_share import ISOLATE
    return ISOLATE if wait_for_fit else ISOLATE.replace('!poster.hasAttribute("data-mp-fit") &&', "false &&")


# Shows one part of the masthead (the others keep their place, hidden; "none": all hidden) → the masthead's box.
SHOW = """(only) => {
  const h = document.querySelector("[data-mp-poster] .mp-head");
  for (const s of [".mp-mname", ".mp-year", ".mp-tag"]) { const e = h.querySelector(s); if (e) e.style.visibility = only === s ? "visible" : "hidden"; }
  const r = h.getBoundingClientRect();
  return { x: Math.max(0, r.left - 8), y: Math.max(0, r.top - 8), width: Math.min(1080, r.width + 16), height: r.height + 16 };
}"""


class MastheadClear(unittest.TestCase):
    def test_the_months_name_never_touches_the_line_under_it(self):
        from PIL import Image, ImageChops, ImageFilter

        def ink(shot, bare):          # what one part draws: where the masthead with it differs from the one without
            d = ImageChops.difference(shot.convert("RGB"), bare.convert("RGB")).convert("L")
            return d.point(lambda v: 255 if v > 40 else 0)

        def touching(a, b) -> int:    # pixels of b within a pixel of a
            return sum(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)), b).histogram()[1:])

        problems: list[str] = []
        ctx = new_context(1280, 1400)
        try:
            for month in poster_months():
                for lang in ("en", "es"):
                    path = ("es/" if lang == "es" else "") + f"monthly/{month}/"
                    page = open_page(ctx, path)
                    page.wait_for_function(FITTED_ATTR, timeout=30_000)
                    page.evaluate(_isolate(True))
                    clip = page.evaluate(SHOW, "none")
                    bare = Image.open(BytesIO(page.screenshot(clip=clip)))
                    parts = {}
                    for part in (".mp-mname", ".mp-year", ".mp-tag"):
                        page.evaluate(SHOW, part)
                        parts[part] = ink(Image.open(BytesIO(page.screenshot(clip=clip))), bare)
                    page.close()
                    for a, b in ((".mp-mname", ".mp-tag"), (".mp-mname", ".mp-year"), (".mp-year", ".mp-tag")):
                        n = touching(parts[a], parts[b])
                        if n:
                            problems.append(f"/{path}: {a} touches {b} ({n} px)")
        finally:
            ctx.close()
        self.assertEqual(problems, [], "\n".join(problems))


# Every line of text the poster draws (and its QR, chips and logo), cut to what its ancestors' overflow lets show
# (overflow-clip-margin included); two of them from different blocks drawn on the same spot = an overlap.
DRAWN = r"""() => {
  const p = document.querySelector("[data-mp-poster]");
  const P = p.getBoundingClientRect();
  const R = (r) => ({ l: r.left, t: r.top, r: r.right, b: r.bottom });
  const cut = (a, b) => ({ l: Math.max(a.l, b.l), t: Math.max(a.t, b.t), r: Math.min(a.r, b.r), b: Math.min(a.b, b.b) });
  const area = (a) => Math.max(0, a.r - a.l) * Math.max(0, a.b - a.t);
  const clipOf = (el) => {
    let c = R(P);
    for (let e = el.parentElement; e && e !== p.parentElement; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.overflowX === "visible" && cs.overflowY === "visible") continue;
      const r = e.getBoundingClientRect(), m = cs.overflowX === "clip" || cs.overflowY === "clip" ? parseFloat(cs.overflowClipMargin) || 0 : 0;
      c = cut(c, { l: r.left + (parseFloat(cs.borderLeftWidth) || 0) - m, t: r.top + (parseFloat(cs.borderTopWidth) || 0) - m,
                   r: r.right - (parseFloat(cs.borderRightWidth) || 0) + m, b: r.bottom - (parseFloat(cs.borderBottomWidth) || 0) + m });
    }
    return c;
  };
  const blocks = [...p.querySelectorAll(".mp-b, .mp-foot, .mp-head")], drawn = [];
  blocks.forEach((b, bi) => {
    const w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (!n.textContent.trim() || n.parentElement.closest(".mp-sr, .sr-only")) continue;
      const g = document.createRange(); g.selectNodeContents(n);
      const c = clipOf(n.parentElement);
      for (const r of g.getClientRects()) { const v = cut(R(r), c); if (area(v) >= 1) drawn.push({ bi, v, s: n.textContent.trim().slice(0, 30) }); }
    }
    b.querySelectorAll(".mp-qr, .mp-chip, .mp-logo").forEach((q) => { const v = cut(R(q.getBoundingClientRect()), clipOf(q)); if (area(v) >= 1) drawn.push({ bi, v, s: q.className }); });
  });
  const over = [];
  for (let i = 0; i < drawn.length; i++) for (let j = i + 1; j < drawn.length; j++) {
    const a = drawn[i], b = drawn[j];
    if (a.bi === b.bi || blocks[a.bi].contains(blocks[b.bi]) || blocks[b.bi].contains(blocks[a.bi])) continue;
    if (area(cut(a.v, b.v)) > 6) over.push(a.s + " / " + b.s);
  }
  // a date (or an offer, the price change) cut by its column: its row not whole inside what its ancestors show
  const hidden = [...p.querySelectorAll(".mp-dlist > li")].filter((li) => {
    const r = R(li.getBoundingClientRect()), c = clipOf(li);
    return r.t < c.t - 1 || r.b > c.b + 1 || r.l < c.l - 1 || r.r > c.r + 1;
  }).map((li) => (li.querySelector(".mp-date-t") || li).textContent.trim().slice(0, 40));
  return { fitted: p.hasAttribute("data-mp-fit"), over, hidden };
}"""


class UnfittedClipped(unittest.TestCase):
    def test_no_text_over_another_block_before_the_fit(self):
        problems: list[str] = []
        ctx = new_context(1280, 1400)
        ctx.route(re.compile(r".*/assets/js/monthly\.js(\?.*)?$"), lambda route: route.abort())
        try:
            for month in poster_months():
                for lang in ("en", "es"):
                    path = ("es/" if lang == "es" else "") + f"monthly/{month}/"
                    page = open_page(ctx, path)
                    page.evaluate(_isolate(False))
                    r = page.evaluate(DRAWN)
                    page.close()
                    self.assertFalse(r["fitted"], "the page's script was blocked: no fit")
                    if r["over"]:
                        problems.append(f"/{path}: {r['over'][:4]}")
                    if r["hidden"]:
                        problems.append(f"/{path}: dates cut by their column — {r['hidden']}")
        finally:
            ctx.close()
        self.assertEqual(problems, [], "\n".join(problems))


# The build's own arrangement (the page's script blocked: the poster as built), searched as the fit searches it first
# (assets/js/monthly.js: from the density's type, then halving; the same overflow measure) → the type it reaches.
BUILD_BEST = r"""() => {
  const p = document.querySelector("[data-mp-poster]");
  const BLOCKS = ".mp-b, .mp-foot, .mp-head, .mp-row, .mp-col, .mp-body, .mp-board, .mp-cover, .mp-strip, .mp-page, .mp-main, .mp-stub, .mp-side, .mp-content, .mp-top, .mp-feature, .mp-rail, .mp-band";
  const holder = document.createElement("div");
  holder.className = "mp-measure";
  holder.style.cssText = "position:absolute;left:-12000px;top:0;width:1080px;visibility:hidden;pointer-events:none;";
  const c = p.cloneNode(true);
  c.removeAttribute("data-mp-poster");
  c.style.position = "relative";
  holder.appendChild(c);
  document.body.appendChild(holder);
  const box = (el) => { let t = 0, l = 0, e = el; while (e && e !== c) { t += e.offsetTop; l += e.offsetLeft; e = e.offsetParent; } return { t, b: t + el.offsetHeight, r: l + el.offsetWidth }; };
  const fits = (k) => {
    c.style.fontSize = k / 4 + "px";
    for (const b of c.querySelectorAll(BLOCKS)) {
      const par = b.parentElement, bb = box(b), pad = parseFloat(getComputedStyle(par).paddingBottom) || 0;
      const limit = par === c ? c.clientHeight - pad : box(par).t + par.clientTop + par.clientHeight - pad;
      if (bb.b > limit + 2 || bb.r > c.clientWidth + 2) return false;
    }
    return true;
  };
  const base = Math.floor((parseFloat(getComputedStyle(c).fontSize) || 23) * 4), minK = 60, topK = Math.floor(Math.min(base / 4 * 1.25, 28) * 4);
  let lo = minK - 1, hi = topK + 1;
  const b0 = Math.min(base, topK);
  if (b0 >= minK) { if (fits(b0)) lo = b0; else hi = b0; }
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (fits(mid)) lo = mid; else hi = mid; }
  holder.remove();
  return Math.max(lo, minK) / 4;
}"""

# The fitted poster (taken out of its scaled frame: _isolate): its type, whether it is arranged as built, the narrowest
# room beside a date's chip (in its title's em), the columns that spread their blocks, how far the month's name runs
# past its column, and what is wrong with dates that flow on.
FITTED = r"""() => {
  const p = document.querySelector("[data-mp-poster]");
  const sp = p.querySelector("[data-mp-widths]");
  const built = [...p.querySelectorAll("[data-mp-move]")].every((m) => m.parentElement.closest("[data-mp-slot]").getAttribute("data-mp-slot") === m.getAttribute("data-mp-move").split(/\s+/)[0])
    && !(sp && sp.style.getPropertyValue("--mp-split")) && !p.querySelector(".mp-dates--cols, .mp-dates--more");
  const rooms = [...p.querySelectorAll(".mp-dlist > li")].map((li) => {
    const ls = getComputedStyle(li), chip = li.querySelector(".mp-chip"), t = li.querySelector(".mp-date-t");
    const room = li.clientWidth - parseFloat(ls.paddingLeft) - parseFloat(ls.paddingRight) - (chip ? chip.offsetWidth : 0) - (parseFloat(ls.columnGap) || 0);
    return Math.round(room / parseFloat(getComputedStyle(t).fontSize) * 10) / 10;
  });
  const spread = [...p.querySelectorAll("[data-mp-slot], .mp-page")].filter((s) => /space-/.test(getComputedStyle(s).justifyContent)).map((s) => s.className);
  const head = p.querySelector(".mp-head"), col = head.parentElement, cs = getComputedStyle(col);
  const name = document.createRange();
  name.selectNodeContents(head.querySelector(".mp-month"));
  const right = col.getBoundingClientRect().right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
  const more = p.querySelector(".mp-dates--more"), flow = [];
  if (more) {
    const d = p.querySelector(".mp-dates:not(.mp-dates--more)"), ord = (k) => Number(k.getAttribute("data-mp-order"));
    if ([...more.parentElement.children].find((k) => k.hasAttribute("data-mp-order") && ord(k) >= 10) !== more) flow.push("not at the head of its column");
    if ([...d.parentElement.children].filter((k) => k.hasAttribute("data-mp-order")).pop() !== d) flow.push("the dates not at the foot of theirs");
    if (more.querySelector(".mp-h")) flow.push("a heading");
    if (d.querySelectorAll(".mp-dlist > li").length < 2 || more.querySelectorAll(".mp-dlist > li").length < 2) flow.push("fewer than two dates in a part");
  }
  return { font: parseFloat(getComputedStyle(p).fontSize), built, minRoom: Math.min(...rooms), spread,
           nameOut: Math.round(name.getBoundingClientRect().right - right), flow };
}"""


class UseTheRoom(unittest.TestCase):
    def test_the_type_is_as_large_as_the_room_allows(self):
        problems: list[str] = []
        blocked = new_context(1280, 1400)
        blocked.route(re.compile(r".*/assets/js/monthly\.js(\?.*)?$"), lambda route: route.abort())
        ctx = new_context(1280, 1400)
        try:
            for month in poster_months():
                for lang in ("en", "es"):
                    path = ("es/" if lang == "es" else "") + f"monthly/{month}/"
                    page = open_page(blocked, path)
                    built = page.evaluate(BUILD_BEST)
                    page.close()
                    page = open_page(ctx, path)
                    page.wait_for_function(FITTED_ATTR, timeout=30_000)
                    page.evaluate(_isolate(True))
                    r = page.evaluate(FITTED)
                    page.close()
                    where = f"/{path}"
                    if r["font"] < built:
                        problems.append(f"{where}: {r['font']}px, smaller than the build's own arrangement's {built}px")
                    if not r["built"] and r["minRoom"] < 10:
                        problems.append(f"{where}: a date's title has {r['minRoom']} em beside its chip (10 at least)")
                    if r["spread"]:
                        problems.append(f"{where}: blocks spread over their column — {r['spread']}")
                    if r["nameOut"] > 1:
                        problems.append(f"{where}: the month's name runs {r['nameOut']}px past its column")
                    if r["flow"]:
                        problems.append(f"{where}: the dates that flow on — {r['flow']}")
        finally:
            ctx.close()
            blocked.close()
        self.assertEqual(problems, [], "\n".join(problems))


# The poster's own dates block (not the page's #mp-dates list): its list → the macro's "no dates" note.
_POSTER_DATES = re.compile(r'(<section class="mp-b mp-dates"[^>]*>.*?)<ul class="mp-dlist">.*?</ul>(.*?</section>)', re.S)
NO_DATES = r"""() => {
  const p = document.querySelector("[data-mp-poster]"), d = p.querySelector(".mp-dates");
  return { lists: p.querySelectorAll(".mp-dlist").length, note: !!(d && d.querySelector(".mp-note")),
           measuring: document.querySelectorAll(".mp-measure").length };
}"""


class NoDatesFits(unittest.TestCase):
    """A month with no dates and no offers (skip_dates, nothing else that month): the poster's dates block holds only
    its "no dates" note. On a layout whose dates may flow on into the next column ("a+b", "main+stub"), the fit
    still finishes (data-mp-fit, its measuring copy gone, no script error): that arrangement cannot be, so it is
    skipped (src/assets/js/monthly.js arrange()). One month of each such layout, the build's own months."""

    def test_the_fit_finishes_without_a_list_of_dates(self):
        found: dict[str, str] = {}
        for month in poster_months():
            html = (S["site"] / "monthly" / month / "index.html").read_text(encoding="utf-8")
            layout = re.search(r'class="mp-poster mp-l-([\w-]+)', html)
            if layout and re.search(r'data-mp-move="[^"]*\+', html):
                found.setdefault(layout.group(1), month)
        self.assertTrue(found, "a month whose poster's dates may flow on into the next column")

        def without_list(route):
            resp = route.fetch()
            body, n = _POSTER_DATES.subn(r'\1<p class="mp-note">No dates announced yet.</p>\2', resp.text(), count=1)
            if not n:
                raise AssertionError(f"{route.request.url}: no poster dates list to replace")
            route.fulfill(response=resp, body=body, headers={**resp.headers, "content-type": "text/html; charset=utf-8"})

        problems: list[str] = []
        errors: list[str] = []
        ctx = new_context(1280, 1400)
        ctx.route(re.compile(r".*/monthly/\d{4}-\d{2}/$"), without_list)
        try:
            for layout, month in sorted(found.items()):
                path = f"monthly/{month}/"
                page = open_page(ctx, path, errors)
                try:
                    page.wait_for_function(FITTED_ATTR, timeout=20_000)
                except Exception:
                    problems.append(f"/{path} ({layout}): the poster never fitted")
                r = page.evaluate(NO_DATES)
                page.close()
                if r["lists"] or not r["note"]:
                    problems.append(f"/{path} ({layout}): the dates list was not replaced by the note — {r}")
                if r["measuring"]:
                    problems.append(f"/{path} ({layout}): the fit's measuring copy is still in the page")
        finally:
            ctx.close()
        self.assertEqual(errors, [])
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
