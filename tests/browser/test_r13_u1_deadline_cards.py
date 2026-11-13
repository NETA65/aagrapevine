"""Round 13 · u1, in a real browser (tests/browser/__init__.py says how to run these; the site server, the browser and
the helpers are test_site_in_browser's): Share your story's two deadline cards (/contribute/#deadlines) side by side.

  * TheCardsEndTogether — from 1024 to 1920 pixels, English (Grapevine first) and Spanish (La Viña first), light and dark,
                          and at 150 % text: the two cards stand side by side, stretched to one height, and neither has a
                          large blank band — the shorter card's topic tiles take what is left without being stretched far
                          beyond their words (eleventy/filters/read.js deadlineLayout chooses how many deadline rows and
                          topics each card shows at each width; community.css cm-dl-hide-<width>). On a phone the cards
                          are one under the other and no tile is stretched. The page never scrolls sideways.
  * EachItemOnce        — at every width each deadline row and each topic is shown exactly once: in the card's list, or
                          under its "Show all" (never both, never neither), and "Show all" is there only when it holds
                          something.
  * NoRowAlone          — where a card's deadline rows run in two columns (a tablet, one card under the other; side by
                          side from about 1475px), its list shows an even number of them — or all it has —, so the last
                          row is never alone with half of it empty (the review of October 2026: 768px, 1920px Spanish).
  * AListOpened         — side by side (1024 to 1920 pixels, English and Spanish, and at 150 % text), each card's "Show
                          all" and "Recently closed" opened in turn: neither card's topic tiles are stretched (La Viña's
                          19 topics made Grapevine's eight tiles 3.6 to 4.7 times their words; Grapevine's 7 deadlines
                          La Viña's about twice — the review of October 2026) and neither card has a blank band (tiles
                          that merely stopped growing would leave one above "Recently closed"): each card ends at its
                          own content (community.css .cm-dl-pair:has(details.read-more[open])). Closed again, the two
                          are one height again.

What the cards hold depends on the day's data: without suggested topics in both cards the balance check is skipped (a
card without topics has nothing to grow), never failed.
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

# Per card: how many topic tiles it shows, the blank band under its content (rem: from the end of its content to
# "Recently closed" or the foot of its body), and how far its tallest tile is stretched beyond the tallest natural tile
# of its row (its words and paddings).
MEASURE = r"""
() => {
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  const vis = (e) => !!e && getComputedStyle(e).display !== 'none' && e.getClientRects().length > 0;
  const nat = (li) => { const s = li.querySelector(':scope > span.min-w-0'); const p = getComputedStyle(li);
    return s.getBoundingClientRect().height + parseFloat(p.paddingTop) + parseFloat(p.paddingBottom); };
  return [...document.querySelectorAll('#deadlines .cm-dl-pair > .card')].map((c) => {
    const body = c.querySelector(':scope > div.flex-1');
    const past = body.querySelector(':scope > details.group\\/past');
    const stop = vis(past) ? past.getBoundingClientRect().top - parseFloat(getComputedStyle(past).marginTop || 0)
      : body.getBoundingClientRect().bottom - parseFloat(getComputedStyle(body).paddingBottom);
    const kids = [...body.children].filter((k) => k !== past && vis(k));
    const end = Math.max(...kids.map((k) => k.getBoundingClientRect().bottom));
    let stretch = 1, tiles = 0;
    const evb = kids.find((k) => k.classList.contains('grow') && k.querySelector('ul.grid'));
    if (evb) {
      const ul = evb.querySelector('ul.grid');
      const lis = [...ul.children].filter(vis);
      tiles = lis.length;
      for (const li of lis) {
        const top = Math.round(li.getBoundingClientRect().top);
        const row = lis.filter((x) => Math.abs(Math.round(x.getBoundingClientRect().top) - top) < 2);
        stretch = Math.max(stretch, li.getBoundingClientRect().height / Math.max(...row.map(nat)));
      }
    }
    const r = c.getBoundingClientRect();
    return { name: c.querySelector('h3').textContent.trim(), top: r.top, bottom: r.bottom, tiles,
             band: (stop - end) / rem, stretch: Math.round(stretch * 100) / 100 };
  });
}
"""

# Per card: each deadline row's and topic's words, where it is shown — in the list or under "Show all" — and whether
# "Show all" itself is shown.
ONCE = r"""
() => {
  const shown = (e) => getComputedStyle(e).display !== 'none' && !e.closest('[style*="display: none"]');
  return [...document.querySelectorAll('#deadlines .cm-dl-pair > .card')].map((c) => {
    const body = c.querySelector(':scope > div.flex-1');
    const out = { name: c.querySelector('h3').textContent.trim(), rows: {}, topics: {} };
    const words = (e) => e.textContent.replace(/\s+/g, ' ').trim().slice(0, 60);
    const grid = [...body.children].find((k) => k.matches('div.grid') && k.querySelector('.read-deadline-row'));
    const dl = body.querySelector(':scope > details.group\\/dl');
    const evb = [...body.children].find((k) => k.classList.contains('grow') && k.querySelector('ul.grid'));
    const ev = evb && evb.querySelector(':scope > details');
    const add = (map, el, where) => { if (shown(el)) (map[words(el)] = map[words(el)] || []).push(where); };
    if (grid) for (const r of grid.children) add(out.rows, r, 'list');
    if (dl && shown(dl)) for (const r of dl.querySelectorAll('.read-deadline-row')) add(out.rows, r, 'more');
    if (evb) for (const li of evb.querySelector(':scope > ul').children) add(out.topics, li, 'list');
    if (ev && shown(ev)) for (const li of ev.querySelectorAll('li')) add(out.topics, li, 'more');
    out.allRows = [...new Set([...body.querySelectorAll('.read-deadline-row:not(.read-deadline-next):not(.is-past)')].map(words))];
    out.allTopics = evb ? [...new Set([...evb.querySelectorAll('li')].map(words))] : [];
    out.dlShown = !!(dl && shown(dl)); out.evShown = !!(ev && shown(ev));
    out.dlItems = dl ? [...dl.querySelectorAll('.read-deadline-row')].filter(shown).length : 0;
    out.evItems = ev ? [...ev.querySelectorAll('li')].filter(shown).length : 0;
    return out;
  });
}
"""


def visit(width: int, lang: str, theme: str | None = None, text: int | None = None):
    ctx = new_context(width, 900, lang=lang, theme=theme, prefs={"text": text} if text else None)
    page = open_page(ctx, ("es/" if lang == "es" else "") + "contribute/")
    return ctx, page


class TheCardsEndTogether(unittest.TestCase):
    CASES = [(w, lang, None, None) for w in (1024, 1280, 1440, 1920) for lang in ("en", "es")] + \
            [(1440, "en", "dark", None), (1440, "es", "dark", None), (1920, "en", None, 150), (1920, "es", None, 150)]

    def test_side_by_side(self):
        checked = 0
        for width, lang, theme, text in self.CASES:
            with self.subTest(width=width, lang=lang, theme=theme, text=text):
                ctx, page = visit(width, lang, theme, text)
                try:
                    cards = page.evaluate(MEASURE)
                    if len(cards) != 2:
                        self.skipTest("the deadline cards are not on the page in this build")
                    a, b = cards
                    self.assertLess(abs(a["top"] - b["top"]), 1, "side by side")
                    self.assertLess(abs(a["bottom"] - b["bottom"]), 1, "one height")
                    r = page.evaluate(SIDEWAYS)
                    self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                    if not (a["tiles"] and b["tiles"]):
                        continue                    # a card without topics: nothing to balance with (the day's data)
                    checked += 1
                    for c in cards:
                        # the shorter card: its tiles take what is left — never a blank band, never stretched far
                        self.assertLess(c["band"], 1.5, (c["name"], c))
                        self.assertLessEqual(c["stretch"], 1.45, (c["name"], c))
                finally:
                    ctx.close()
        if not checked:
            self.skipTest("no build day with suggested topics in both cards")

    def test_one_under_the_other_on_a_phone(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx, page = visit(390, lang)
                try:
                    cards = page.evaluate(MEASURE)
                    if len(cards) != 2:
                        self.skipTest("the deadline cards are not on the page in this build")
                    self.assertGreater(cards[1]["top"], cards[0]["bottom"] - 1, "one under the other")
                    for c in cards:
                        self.assertLessEqual(c["stretch"], 1.02, c)
                    r = page.evaluate(SIDEWAYS)
                    self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                finally:
                    ctx.close()


class EachItemOnce(unittest.TestCase):
    def test_in_the_list_or_under_show_all(self):
        for width in (390, 768, 1024, 1180, 1280, 1366, 1440, 1536, 1680, 1920):
            for lang in ("en", "es"):
                with self.subTest(width=width, lang=lang):
                    ctx, page = visit(width, lang)
                    try:
                        for card in page.evaluate(ONCE):
                            for kind, every in (("rows", "allRows"), ("topics", "allTopics")):
                                twice = {k: v for k, v in card[kind].items() if len(v) != 1}
                                self.assertEqual(twice, {}, (card["name"], kind))
                                self.assertEqual(sorted(card[kind]), sorted(card[every]), (card["name"], kind))   # none missing
                            # "Show all" only when it holds something
                            self.assertEqual(card["dlShown"], card["dlItems"] > 0, card["name"])
                            self.assertEqual(card["evShown"], card["evItems"] > 0, card["name"])
                    finally:
                        ctx.close()


# Per card: how many columns its deadline rows run in, how many its list shows, and how many it has after the next one.
ROWS = r"""
() => [...document.querySelectorAll('#deadlines .cm-dl-pair > .card')].map((c) => {
  const body = c.querySelector(':scope > div.flex-1');
  const grid = [...body.children].find((k) => k.matches('div.grid') && k.querySelector('.read-deadline-row'));
  const shown = grid ? [...grid.children].filter((r) => getComputedStyle(r).display !== 'none') : [];
  const all = new Set([...body.querySelectorAll('.read-deadline-row:not(.read-deadline-next):not(.is-past)')]
    .map((e) => e.textContent.replace(/\s+/g, ' ').trim().slice(0, 60)));
  return { name: c.querySelector('h3').textContent.trim(), shown: shown.length, all: all.size,
           cols: grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length : 0 };
})
"""


class NoRowAlone(unittest.TestCase):
    def test_an_even_number_in_two_columns(self):
        twos = 0
        for width in (768, 1024, 1366, 1536, 1680, 1920):
            for lang in ("en", "es"):
                with self.subTest(width=width, lang=lang):
                    ctx, page = visit(width, lang)
                    try:
                        for card in page.evaluate(ROWS):
                            if card["cols"] == 2:
                                twos += 1
                                self.assertTrue(card["shown"] % 2 == 0 or card["shown"] == card["all"], card)
                    finally:
                        ctx.close()
        self.assertGreater(twos, 0, "rows in two columns at some width (768px: a tablet)")


# Per card: where it is, how far its tallest topic tile is stretched beyond its row's tallest natural tile (as MEASURE),
# the room under the last thing it shows (rem: from the bottom of its last row, tile, "Show all" or open list item —
# never what a closed list holds — to the top of "Recently closed" or the foot of its body: the gap between them when
# nothing is left over), and the lists it can open there ("dl", "ev", "past": "Show all N deadlines", "Show all N
# topics", "Recently closed").
CARDS = r"""
() => {
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  const vis = (e) => !!e && getComputedStyle(e).display !== 'none' && e.getClientRects().length > 0;
  // inside a closed list (its own summary excepted)
  const hidden = (e) => {
    for (let d = e.parentElement && e.parentElement.closest('details'); d; d = d.parentElement && d.parentElement.closest('details'))
      if (!d.open && !(e.tagName === 'SUMMARY' && e.parentElement === d)) return true;
    return false;
  };
  const nat = (li) => { const s = li.querySelector(':scope > span.min-w-0'); const p = getComputedStyle(li);
    return s.getBoundingClientRect().height + parseFloat(p.paddingTop) + parseFloat(p.paddingBottom); };
  return [...document.querySelectorAll('#deadlines .cm-dl-pair > .card')].map((c) => {
    const body = c.querySelector(':scope > div.flex-1');
    const past = body.querySelector(':scope > details[class~="group/past"]');
    const stop = vis(past) ? past.getBoundingClientRect().top
      : body.getBoundingClientRect().bottom - parseFloat(getComputedStyle(body).paddingBottom);
    const shown = [...body.querySelectorAll('li, summary, p, .read-deadline-row')]
      .filter((e) => !(past && past.contains(e)) && vis(e) && !hidden(e));
    const end = Math.max(...shown.map((e) => e.getBoundingClientRect().bottom));
    let stretch = 1, tiles = 0;
    const evb = [...body.children].find((k) => k.classList.contains('grow') && k.querySelector('ul.grid'));
    if (evb) {
      const lis = [...evb.querySelector('ul.grid').children].filter(vis);
      tiles = lis.length;
      for (const li of lis) {
        const top = Math.round(li.getBoundingClientRect().top);
        const row = lis.filter((x) => Math.abs(Math.round(x.getBoundingClientRect().top) - top) < 2);
        stretch = Math.max(stretch, li.getBoundingClientRect().height / Math.max(...row.map(nat)));
      }
    }
    const r = c.getBoundingClientRect();
    return { name: c.querySelector('h3').textContent.trim(), top: r.top, bottom: r.bottom, tiles,
             stretch: Math.round(stretch * 100) / 100, room: Math.round((stop - end) / rem * 100) / 100,
             lists: [...body.querySelectorAll(':scope details.read-more')].filter(vis)
               .map((d) => [...d.classList].find((k) => k.startsWith('group/')).slice(6)) };
  });
}
"""

# Opens (or closes) one card's list, as its summary would.
TOGGLE = r"""
([i, group, open]) => {
  const d = document.querySelectorAll('#deadlines .cm-dl-pair > .card')[i].querySelector(`details[class~="group/${group}"]`);
  d.open = open;
}
"""


class AListOpened(unittest.TestCase):
    CASES = [(w, lang, None) for w in (1024, 1280, 1440, 1920) for lang in ("en", "es")] + \
            [(1920, "en", 150), (1920, "es", 150)]

    def test_each_card_ends_at_its_own_content(self):
        checked = 0
        for width, lang, text in self.CASES:
            ctx, page = visit(width, lang, text=text)
            try:
                cards = page.evaluate(CARDS)
                if len(cards) != 2:
                    self.skipTest("the deadline cards are not on the page in this build")
                if abs(cards[0]["top"] - cards[1]["top"]) >= 1 or not (cards[0]["tiles"] and cards[1]["tiles"]):
                    continue                        # one under the other, or a card without topics (the day's data)
                for i, card in enumerate(cards):
                    for group in card["lists"]:
                        with self.subTest(width=width, lang=lang, text=text, opened=f"{card['name']} {group}"):
                            page.evaluate(TOGGLE, [i, group, True])
                            try:
                                opened = page.evaluate(CARDS)
                            finally:
                                page.evaluate(TOGGLE, [i, group, False])
                            checked += 1
                            for c in opened:
                                # neither card's tiles stretched to fill the other's longer list, nor a blank band left
                                self.assertLessEqual(c["stretch"], 1.6, (c["name"], c))
                                self.assertLess(c["room"], 1.5, (c["name"], c))
                            again = page.evaluate(CARDS)    # closed again: one height again, as the page opened
                            self.assertLess(abs(again[0]["bottom"] - again[1]["bottom"]), 1, again)
            finally:
                ctx.close()
        if not checked:
            self.skipTest("no build day with suggested topics in both cards side by side")


if __name__ == "__main__":
    unittest.main()
