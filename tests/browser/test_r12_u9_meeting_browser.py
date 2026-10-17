"""Round 12 · the committee meeting's paperwork (Customize → Agenda & minutes) on the built site, in a real browser
(tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's site server and browser):

  * MeetingPaperwork — the tab is there for the committee meeting only; its three texts (the agenda e-mail, the
                       reminder with its paragraph in Spanish, the draft minutes) show the chair's details and never
                       the first name kept for the notes; "Copy" puts the text on the clipboard; "Start next month"
                       carries the ticked items into old business, clears tonight's blanks and the checklist, and its
                       Undo is still there after a reload and puts everything back. In Spanish on a 360-pixel phone at
                       150 % text: Spanish controls and dates, the English texts marked English, nothing wider than
                       the drawer, no sideways scroll, and no script error anywhere; the drawer's tabs (one row that
                       scrolls sideways) never push its panel off the screen or under the control bar, and each tab,
                       reached with the arrow keys, is whole on the screen and takes a tap — the workshops' too.
                       Once the next meeting has begun, the draft minutes no longer say to undo "Start next month"
                       and its Undo is gone (it would replace that meeting's details); minutes printed the morning
                       after are named with their meeting's date. A text too long for a mailto: link opens no e-mail
                       when the page cannot copy it (its "paste here" would paste whatever the clipboard held), and
                       the long message saying so stays as long as it takes to read it, with an OK the keyboard
                       reaches (its time stands still there). That message keeps off the drawer's text (over the
                       stage beside it; on a phone over the slide at the top), and on a Spanish phone at 150 % text
                       its "Entendido" goes under its words: the toast whole on the screen, nothing past its edge, at
                       most half the screen's height. On /es/ the moment "Start next month" was pressed reads as the
                       site writes a time ("8:30 p. m."), with one period at a sentence's end (release check
                       R12-DECK-ES-PM).

Nothing here depends on today's date: the texts are checked by their words, not their dates; the tests about a
meeting's day stop the browser's clock (Playwright's) at moments taken from the built deck's own meeting dates.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401 (its site server)

STATE_KEY = "gv-presentations-v1"
# What the chair typed (presentations-core.js state); the first name is notes_only: never in a text
SEED = {"v": 1, "shared": {"fill": {"first_name": "Pat"}}, "decks": {"committee-meeting": {
    "fill": {"old_1_item": "Booth schedule for 2027", "action_1_what": "Ask the Area for a table",
             "action_1_who": "the alternate chair", "action_1_when": "Nov 1", "district_order": "3, 22, 91",
             "chair_since": "Two group visits"},
    "checks": {"week-before": ["0"]}}}}
# Anything inside the drawer's panel wider than the panel, and the page's own sideways scroll
OVERFLOW = """(sel) => {
  const p = document.querySelector(sel), r = p.getBoundingClientRect(), wide = [];
  for (const el of p.querySelectorAll("*")) {
    const b = el.getBoundingClientRect();
    if (b.width && b.right > r.right + 1) wide.push(el.tagName.toLowerCase() + "." + String(el.className).split(" ")[0] + " +" + Math.round(b.right - r.right));
  }
  return { panel: p.scrollWidth - p.clientWidth, wide: wide.slice(0, 5),
           page: document.documentElement.scrollWidth - document.documentElement.clientWidth };
}"""


# The focused tab of the drawer (reached with the arrow keys) and the panel it shows: is the tab whole on the screen,
# inside its row and above the control bar, and is it what a tap at its middle lands on (WCAG 2.4.11 focus not
# obscured, 2.5.8 target)? The panel's box on the screen, and the control bar's top.
TAB_SEEN = """() => {
  const t = document.activeElement, row = t.closest("[data-gvp-tabs]");
  const b = t.getBoundingClientRect(), rb = row.getBoundingClientRect();
  const bar = document.querySelector(".gvp-bar").getBoundingClientRect();
  const p = document.querySelector("[data-gvp-panel]:not([hidden])").getBoundingClientRect();
  const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
  const low = Math.min(innerHeight, bar.top) + 0.5;
  return { tab: t.getAttribute("data-gvp-tab"), selected: t.getAttribute("aria-selected") === "true",
           whole: b.left >= Math.max(0, rb.left) - 0.5 && b.right <= Math.min(innerWidth, rb.right) + 0.5 && b.top >= 0 && b.bottom <= low,
           hit: !!hit && hit.closest("[data-gvp-tab]") === t,
           panel: [Math.round(p.top), Math.round(p.bottom)], low: Math.round(low),
           box: [Math.round(b.left), Math.round(b.right), Math.round(b.top), Math.round(b.bottom)] };
}"""
PANEL_ROOM = 200     # the least height (CSS px) a drawer's panel keeps on a phone, at any text size

# The toast with its button (OK, Undo) on the screen: the boxes of the toast, its words and its button; the control
# bar's top; the drawer and its open panel; whether the toast scrolls (sideways: something past its edge; down: words
# out of sight); whether the element with the focus is what a tap at its middle lands on (not under the toast), and
# whether a tap on the button lands on it.
TOAST_SEEN = """() => {
  const t = document.querySelector("[data-gvp-toast]"), b = t.querySelector(".gvp-toast-btn"), m = t.querySelector(".gvp-toast-text");
  const box = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height }; };
  const at = (e) => { const r = e.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                      return !!h && e.contains(h); };
  const f = document.activeElement;
  return { vw: innerWidth, vh: innerHeight, low: Math.min(innerHeight, document.querySelector(".gvp-bar").getBoundingClientRect().top),
           toast: box(t), msg: box(m), btn: box(b), sideways: t.scrollWidth - t.clientWidth, down: t.scrollHeight - t.clientHeight,
           drawer: box(document.querySelector("[data-gvp-drawer]")), panel: box(document.querySelector("[data-gvp-panel]:not([hidden])")),
           focus: f.getAttribute("data-gvp-key"), focus_seen: at(f), tap: at(b) };
}"""
TOAST_TALL = 0.5     # the most of the screen's height the long message takes on a phone (it was 0.78 before it wrapped)


def seeded(ctx, state: dict | None = None) -> None:
    """The chair's details in the browser before the first page (kept across reloads: set only when empty)."""
    ctx.add_init_script("(s => { try { if (!localStorage.getItem(%s)) localStorage.setItem(%s, s); } catch (e) {} })(%s);"
                        % (json.dumps(STATE_KEY), json.dumps(STATE_KEY), json.dumps(json.dumps(state or SEED))))


def built_meetings() -> tuple[dict, dict]:
    """Two meetings of the built deck (its paperwork's dates, as the build saw them): the last one held when it was
    built, and the one after it."""
    deck = json.loads((S["site"] / "orientation" / "presentations" / "committee-meeting.json").read_text(encoding="utf-8"))
    rows = deck["paperwork"]["meetings"]
    i = next(n for n, r in enumerate(rows) if r["start"] > deck["built"])
    return rows[max(0, i - 1)], rows[max(1, i)]


def built_at() -> str:
    """When the built deck was built (its paperwork's "now"): a clock that never depends on today's date."""
    return json.loads((S["site"] / "orientation" / "presentations" / "committee-meeting.json").read_text(encoding="utf-8"))["built"]


def instant(iso: str, **delta) -> str:
    return (datetime.fromisoformat(iso.replace("Z", "+00:00")) + timedelta(**delta)).astimezone(timezone.utc).isoformat()


def stored(page) -> dict:
    return page.evaluate("(k) => JSON.parse(localStorage.getItem(k) || 'null')", STATE_KEY)


class MeetingPaperwork(unittest.TestCase):
    def open_paper(self, ctx, lang: str, errors: list, deck: str = "committee-meeting"):
        page = open_page(ctx, ("es/" if lang == "es" else "") + f"orientation/?present={deck}&mode=customize", errors)
        page.locator("[data-gvp-drawer]").wait_for(state="visible", timeout=30_000)
        page.locator('[data-gvp-panel="slides"] .gvp-rows, [data-gvp-panel="slides"] .gvp-pp').first.wait_for(timeout=30_000)
        return page

    def show_tab(self, page):
        page.locator('[data-gvp-tab="paper"]').click()
        page.locator('[data-gvp-panel="paper"] .gvp-out').first.wait_for(timeout=10_000)

    def assert_drawer_usable(self, page, deck: str):
        """Every tab, from the first to the last with the arrow keys: whole on the screen and above the control bar,
        what a tap there lands on, and its panel on the screen with room to use."""
        tabs = page.locator("[data-gvp-tab]:visible")
        n = tabs.count()
        page.locator('[data-gvp-tab][aria-selected="true"]').focus()
        page.keyboard.press("Home")
        seen = []
        for i in range(n):
            if i:
                page.keyboard.press("ArrowRight")
            r = page.evaluate(TAB_SEEN)
            seen.append(r["tab"])
            with self.subTest(deck=deck, tab=r["tab"]):
                self.assertTrue(r["selected"], r)
                self.assertTrue(r["whole"], f"the focused tab is cut off or under the control bar: {r}")
                self.assertTrue(r["hit"], f"a tap on the tab lands on something else: {r}")
                top, bottom = r["panel"]
                self.assertGreaterEqual(top, 0, r)
                self.assertLessEqual(bottom, r["low"], f"the panel runs under the control bar or off the screen: {r}")
                self.assertGreaterEqual(bottom - top, PANEL_ROOM, f"no room left for the panel: {r}")
        self.assertEqual(len(set(seen)), n, seen)
        return seen

    def test_texts_start_next_month_and_undo(self):
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="en")
        try:
            seeded(ctx)
            page = self.open_paper(ctx, "en", errors)
            origin = page.evaluate("() => location.origin")
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
            self.assertEqual(page.locator('[data-gvp-tab="paper"]').inner_text().strip(), "Agenda & minutes")
            self.show_tab(page)
            boxes = page.locator('[data-gvp-panel="paper"] .gvp-out')
            self.assertEqual(boxes.count(), 3)
            self.assertEqual([boxes.nth(i).get_attribute("aria-label") for i in range(3)],
                             ["Agenda e-mail: the text", "Reminder: the text", "Draft minutes: the text"])
            agenda, reminder, minutes = (boxes.nth(i).inner_text() for i in range(3))
            self.assertIn("Subject: Agenda: Grapevine and La Viña Committee meeting,", agenda)
            self.assertIn("Agenda (Central time)\n7:00  Welcome and opening", agenda)
            self.assertIn("Old business\n- Booth schedule for 2027", agenda)
            self.assertIn("District reports, in this order: 3, 22, 91.", agenda)
            self.assertTrue(reminder.split("Subject:", 1)[1].count("Recordatorio"), "the Spanish paragraph")
            self.assertEqual(boxes.nth(1).locator('p[lang="es"]').count(), 1)
            self.assertIn("Attended: about ___ members (by district: ___)", minutes)
            for text in (agenda, reminder, minutes):
                self.assertNotIn("Pat", text, "the first name kept for the notes is never in a text")
            # Copy: the agenda's text (without its subject) on the clipboard, and said
            page.locator('[data-gvp-key="paper:agenda:copy"]').click()
            page.wait_for_function("() => /Copied/.test((document.querySelector('[data-gvp-toast]') || {}).textContent || '')", timeout=5000)
            clip = page.evaluate("() => navigator.clipboard.readText()")
            self.assertTrue(clip.startswith("Hello, everyone,"), clip[:80])
            self.assertNotIn("Subject:", clip)
            # every mailto: link opens with no address (checked offline too: tests/test_r12_u9_meeting.py)
            self.assertEqual(page.locator('[data-gvp-panel="paper"] [data-gvp-key$=":mail"]').count(), 3)

            # Start next month: tonight's action item comes ticked, old business unticked (tick it: still open)
            action = page.locator('[data-gvp-key="carry:action_1"]')
            old = page.locator('[data-gvp-key="carry:old_1"]')
            self.assertTrue(action.is_checked())
            self.assertFalse(old.is_checked())
            old.check()
            page.once("dialog", lambda d: d.accept())
            page.locator('[data-gvp-key="paper:start"]').click()
            page.wait_for_function("(k) => { const s = JSON.parse(localStorage.getItem(k) || 'null'); return !!(s && s.decks['committee-meeting'].prev); }",
                                   arg=STATE_KEY, timeout=5000)
            deck = stored(page)["decks"]["committee-meeting"]
            self.assertEqual(deck["fill"].get("old_1_item"), "Booth schedule for 2027")
            self.assertEqual(deck["fill"].get("old_2_item"), "Ask the Area for a table (the alternate chair, by Nov 1)")
            self.assertNotIn("action_1_what", deck["fill"])
            self.assertNotIn("chair_since", deck["fill"])
            self.assertEqual(deck["fill"].get("district_order"), "3, 22, 91", "kept month to month")
            self.assertNotIn("week-before", deck.get("checks", {}), "the checklist starts over")
            self.assertEqual(stored(page)["shared"]["fill"], {"first_name": "Pat"})
            self.assertTrue(page.locator("[data-gvp-toast] .gvp-toast-btn").is_visible(), "an Undo right away")
            self.assertTrue(page.locator('[data-gvp-key="paper:start"]').is_disabled(), "once per meeting")

            # the lasting Undo, after a reload
            page.reload(wait_until="load")
            page.locator('[data-gvp-tab="paper"]').wait_for(state="visible", timeout=30_000)
            self.show_tab(page)
            page.once("dialog", lambda d: d.accept())
            page.locator('[data-gvp-key="paper:undo"]').click()
            page.wait_for_function("(k) => { const s = JSON.parse(localStorage.getItem(k) || 'null'); return !!(s && !s.decks['committee-meeting'].prev); }",
                                   arg=STATE_KEY, timeout=5000)
            deck = stored(page)["decks"]["committee-meeting"]
            self.assertEqual(deck["fill"], SEED["decks"]["committee-meeting"]["fill"])
            self.assertEqual(deck["checks"], {"week-before": ["0"]})
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_a_spanish_phone_at_150_percent(self):
        errors: list[str] = []
        ctx = new_context(360, 780, lang="es", prefs={"text": 150})
        try:
            seeded(ctx)
            page = self.open_paper(ctx, "es", errors)
            tab = page.locator('[data-gvp-tab="paper"]')
            self.assertEqual(tab.inner_text().strip(), "Agenda y acta")
            # eight tabs: none pushes the panel off the screen or under the control bar, each one whole and tappable
            self.assertEqual(self.assert_drawer_usable(page, "committee-meeting"),
                             ["version", "slides", "edit", "add", "details", "prepare", "paper", "save"])
            self.show_tab(page)        # (a click: Playwright's own check that the tab takes it)
            panel = '[data-gvp-panel="paper"]'
            r = page.evaluate(TAB_SEEN)
            self.assertEqual(r["tab"], "paper")
            self.assertGreaterEqual(r["panel"][1] - r["panel"][0], PANEL_ROOM, r)
            self.assertLessEqual(r["panel"][1], r["low"], r)
            # the meeting's date in Spanish among the Spanish controls; the English texts marked English
            first = page.locator(f"{panel} .gvp-sec").first.locator("p.gvp-pp").first.inner_text()
            self.assertRegex(first, r"^Para la reunión del [a-záéíóú]+, \d{1,2} de [a-z]+ de \d{4}\.")
            self.assertGreater(page.locator(f'{panel} .gvp-out p.gvp-out-p[lang="en"]').count(), 10)
            self.assertEqual(page.locator(f'{panel} .gvp-out p[lang="es"]').count(), 0, "the Spanish paragraph is the page's language")
            for key in ("paper:agenda:copy", "paper:start"):
                h = page.locator(f'[data-gvp-key="{key}"]').bounding_box()["height"]
                self.assertGreaterEqual(h, 36, key)
            page.wait_for_timeout(300)
            r = page.evaluate(OVERFLOW, panel)
            self.assertLessEqual(r["panel"], 1, r)
            self.assertEqual(r["wide"], [])
            self.assertLessEqual(r["page"], 0, "no sideways scroll")
            # another presentation has no such tab, and its seven are as usable
            other = self.open_paper(ctx, "es", errors, deck="writing-workshop")
            self.assertTrue(other.locator('[data-gvp-tab="paper"]').is_hidden())
            self.assertEqual(self.assert_drawer_usable(other, "writing-workshop"),
                             ["version", "slides", "edit", "add", "details", "prepare", "save"])
            other.locator('[data-gvp-tab="version"]').click()
            other.locator('[data-gvp-tab="save"]').click()
            self.assertEqual(other.locator('[data-gvp-tab="save"]').get_attribute("aria-selected"), "true")
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_the_undo_ends_when_the_next_meeting_begins(self):
        """The chair started next month after one meeting and typed the next month's details. The morning after,
        the draft minutes (that meeting's) say its details are gone and the Undo is offered; printed, they are named
        with that meeting's date. Once the next meeting has begun, the minutes are its own: no such word, no Undo
        (it would put the details from before over that meeting's)."""
        held, after = built_meetings()
        self.assertGreater(after["ymd"], held["ymd"])
        state = {"v": 1, "shared": {"fill": {}}, "decks": {"committee-meeting": {
            "fill": {"old_1_item": "Ask the Area for a table", "minutes_month": held["month"], "district_order": "3, 22, 91",
                     "chair_since": "Next month's visits"},
            "checks": {},
            "prev": {"at": instant(held["end"], minutes=30), "held": held["ymd"],
                     "fill": SEED["decks"]["committee-meeting"]["fill"], "checks": {"week-before": ["0"]}}}}}
        errors: list[str] = []
        for moment, current in ((instant(held["end"], hours=14), True), (instant(after["start"], minutes=30), False)):
            with self.subTest(at=moment):
                ctx = new_context(1280, 900, lang="en")
                try:
                    ctx.clock.set_fixed_time(moment)
                    seeded(ctx, state)
                    page = self.open_paper(ctx, "en", errors)
                    self.show_tab(page)
                    minutes = page.locator('[data-gvp-panel="paper"] .gvp-sec').nth(2)
                    word = minutes.locator("p.gvp-warn")
                    undo = page.locator('[data-gvp-key="paper:undo"]')
                    if current:
                        self.assertIn(f"the meeting of {held['label']}", minutes.inner_text())
                        self.assertEqual(word.count(), 1, "the minutes of the meeting it closed: their details are gone")
                        self.assertEqual(undo.count(), 1)
                        # printed (or saved as a document) the morning after: named with the meeting's date
                        page.evaluate("() => { window.print = () => { window.__printed = document.title; }; }")
                        page.locator('[data-gvp-key="paper:minutes:print"]').click()
                        page.wait_for_function("() => typeof window.__printed === 'string'", timeout=5000)
                        self.assertEqual(page.evaluate("() => window.__printed"),
                                         f"Monthly Committee Meeting – Draft minutes – {held['ymd']}")
                        page.evaluate("() => window.dispatchEvent(new Event('afterprint'))")
                    else:
                        self.assertIn(f"the meeting of {after['label']}", minutes.inner_text())
                        self.assertEqual(word.count(), 0, "the minutes are the meeting's own, from its own details")
                        self.assertEqual(undo.count(), 0, "an Undo would replace this meeting's details")
                        self.assertTrue(page.locator('[data-gvp-key="paper:start"]').is_enabled(), "next month can start again")
                        self.assertIn("Next month's visits", minutes.inner_text())
                finally:
                    ctx.close()
        self.assertEqual(errors, [])

    def test_the_spanish_time_it_was_started(self):
        """Release check R12-DECK-ES-PM: on /es/ the moment "Start next month" was pressed is written the way the whole
        site writes a time ("8:30 p. m.", its spaces no-break — Intl alone says "p.m."), and a sentence that ends with
        it has one period, never "p. m..": the word above the boxes, the line by the Undo, the minutes' word and the
        Undo's question. English keeps "8:30 PM." with its period."""
        held, _after = built_meetings()
        state = {"v": 1, "shared": {"fill": {}}, "decks": {"committee-meeting": {
            "fill": {"minutes_month": held["month"], "district_order": "3, 22, 91"}, "checks": {},
            "prev": {"at": instant(held["end"], minutes=30), "held": held["ymd"],
                     "fill": SEED["decks"]["committee-meeting"]["fill"], "checks": {"week-before": ["0"]}}}}}
        errors: list[str] = []
        seen = {}
        for lang in ("es", "en"):
            ctx = new_context(1280, 900, lang=lang)
            try:
                ctx.clock.set_fixed_time(instant(held["end"], minutes=45))
                seeded(ctx, state)
                page = self.open_paper(ctx, lang, errors)
                self.show_tab(page)
                panel = page.locator('[data-gvp-panel="paper"]')
                asked = []
                page.once("dialog", lambda d: (asked.append(d.message), d.dismiss()))
                page.locator('[data-gvp-key="paper:undo"]').click()      # (its question, then Cancel)
                seen[lang] = {"warn": panel.locator("p.gvp-warn").all_inner_texts(),
                              "started": panel.locator(".gvp-subfields p.gvp-pp").first.inner_text(), "asked": asked}
            finally:
                ctx.close()
        self.assertEqual(errors, [])
        time_es = r"\d{1,2} de [a-z]+(?:,| a las) \d{1,2}:\d{2} p\. m\."
        es = seen["es"]
        self.assertEqual(len(es["warn"]), 2, es)
        minutes_word, already = es["warn"]
        self.assertRegex(already, r"^Ya empezaste el mes siguiente después de esta reunión, el " + time_es + "$")
        self.assertRegex(es["started"], r"^Empezaste el mes siguiente el " + time_es + "$")
        self.assertRegex(minutes_word, r"^Empezaste el mes siguiente el " + time_es + ": este esquema")
        self.assertEqual(len(es["asked"]), 1, "the Undo asks first")
        self.assertRegex(es["asked"][0], r"\(" + time_es + r"\)\?")
        for text in es["warn"] + [es["started"]] + es["asked"]:
            self.assertNotIn("..", text)
            self.assertNotRegex(text, r"[ap]\.m\.", "the site's 'p. m.', not Intl's 'p.m.'")
        en = seen["en"]
        self.assertRegex(en["started"], r"^You started next month on [A-Z][a-z]+ \d{1,2}(?:,| at) \d{1,2}:\d{2}\s?PM\.$")
        self.assertRegex(en["warn"][1], r"^You already started next month after this meeting, on .*\d\s?PM\.$")

    def test_a_long_email_when_the_page_cannot_copy(self):
        """"Open in my e-mail" with a text too long for a mailto: link: copied, then the e-mail opens with "paste it
        here" — but when this browser does not let the page copy, no e-mail opens (the clipboard holds something
        else) and the chair is told to copy the text."""
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="en")
        try:
            seeded(ctx)
            page = self.open_paper(ctx, "en", errors)
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=page.evaluate("() => location.origin"))
            self.show_tab(page)
            # the e-mail links the page opens (none is followed)
            page.evaluate("""() => {
              window.__mail = [];
              const click = HTMLAnchorElement.prototype.click;
              HTMLAnchorElement.prototype.click = function () {
                if (/^mailto:/.test(this.getAttribute("href") || "")) { window.__mail.push(this.getAttribute("href")); return; }
                return click.call(this);
              };
            }""")
            agenda = page.locator('[data-gvp-panel="paper"] .gvp-out').first.inner_text()
            self.assertGreater(len(page.evaluate("(t) => encodeURIComponent(t)", agenda)), 1800, "too long for a mailto: link")
            toast = "(document.querySelector('[data-gvp-toast]') || {}).textContent || ''"
            # this browser does not let the page copy
            page.evaluate("""() => {
              window.__clip = navigator.clipboard.writeText;
              navigator.clipboard.writeText = () => Promise.reject(new Error("not allowed"));
              window.__exec = document.execCommand;
              document.execCommand = () => false;
            }""")
            page.locator('[data-gvp-key="paper:agenda:mail"]').click()
            page.wait_for_function(f"() => /too long to open in an e-mail/.test({toast})", timeout=5000)
            page.wait_for_timeout(300)
            self.assertEqual(page.evaluate("() => window.__mail"), [], "no e-mail that says the text is on the clipboard")
            self.assertIn("copy it yourself", page.evaluate(f"() => {toast}"))
            # it can copy: the e-mail opens, with a line saying to paste the text
            page.evaluate("() => { navigator.clipboard.writeText = window.__clip; document.execCommand = window.__exec; }")
            page.locator('[data-gvp-key="paper:agenda:mail"]').click()
            page.wait_for_function("() => window.__mail.length === 1", timeout=5000)
            href = page.evaluate("() => window.__mail[0]")
            self.assertTrue(href.startswith("mailto:?subject=Agenda"), href[:60])
            self.assertEqual(unquote(href.split("&body=", 1)[1]), "(Paste the text here: it's on your clipboard.)")
            self.assertIn("The text is long, so it was copied", page.evaluate(f"() => {toast}"))
            self.assertTrue(page.evaluate("() => navigator.clipboard.readText()").startswith("Hello, everyone,"))
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_the_long_message_stays_until_it_is_read(self):
        """(follow-up to u9-mail-long-copy-failed) The message after a failed copy (over 30 words) stays as long as it
        takes to read it — 1.5 s and 0.4 s a word, not the 5 s of a short one — and has an OK button: the keyboard
        reaches it with Tab, its time stands still while the focus is there, and OK (or Esc) puts it away, the focus
        going back to "Open in my e-mail". A short message still goes after its few seconds. Playwright's clock: the
        seconds are counted, not waited for."""
        idle = "() => document.querySelector('[data-gvp-toast]').classList.contains('is-idle')"
        for lang, ok in (("en", "OK"), ("es", "Entendido")):
            with self.subTest(lang=lang):
                errors: list[str] = []
                ctx = new_context(1280, 900, lang=lang)
                try:
                    seeded(ctx)
                    ctx.clock.install()
                    page = self.open_paper(ctx, lang, errors)
                    self.show_tab(page)
                    page.evaluate("""() => {
                      const click = HTMLAnchorElement.prototype.click;
                      HTMLAnchorElement.prototype.click = function () {
                        if (/^mailto:/.test(this.getAttribute("href") || "")) return;
                        return click.call(this);
                      };
                      navigator.clipboard.writeText = () => Promise.reject(new Error("not allowed"));
                      document.execCommand = () => false;
                    }""")
                    mail = page.locator('[data-gvp-key="paper:agenda:mail"]')
                    mail.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_function("() => document.querySelector('[data-gvp-toast] .gvp-toast-btn')", timeout=5000)
                    text = page.locator("[data-gvp-toast] .gvp-toast-text").inner_text()
                    words = len(text.split())
                    self.assertGreater(words, 30, text)
                    self.assertEqual(page.locator("[data-gvp-toast] .gvp-toast-btn").inner_text(), ok)
                    # over the stage, beside the drawer: not over the text it asks the chair to select
                    r = page.evaluate(TOAST_SEEN)
                    self.assertLessEqual(r["toast"]["r"], r["drawer"]["l"] + 0.5, r)
                    self.assertTrue(r["focus_seen"], f"the toast covers the button that has the focus: {r}")
                    page.clock.run_for(7000)
                    self.assertFalse(page.evaluate(idle), "still there after 7 s: not the 5 s of a short message")
                    if lang == "en":
                        # the keyboard reaches its OK (Tab, the dialog's own order); its time stands still there
                        for _ in range(150):
                            page.keyboard.press("Tab")
                            if page.evaluate("() => !!document.activeElement.closest('[data-gvp-toast]')"):
                                break
                        self.assertEqual(page.evaluate("() => document.activeElement.textContent"), ok)
                        page.clock.run_for(120_000)
                        self.assertFalse(page.evaluate(idle), "the focus on it holds it")
                        page.keyboard.press("Enter")
                        self.assertTrue(page.evaluate(idle))
                        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-gvp-key')"),
                                         "paper:agenda:mail", "the focus goes back where it was")
                        self.assertTrue(page.locator("[data-gvp-drawer]").is_visible(), "OK closed the message only")
                        # left alone, it goes once it has had its time: 1.5 s + 0.4 s a word
                        page.keyboard.press("Enter")
                        page.wait_for_function("() => document.querySelector('[data-gvp-toast] .gvp-toast-btn')", timeout=5000)
                        page.clock.run_for(1500 + 400 * words - 1000)
                        self.assertFalse(page.evaluate(idle), "a second before its time")
                        page.clock.run_for(2000)
                        self.assertTrue(page.evaluate(idle), "gone after its time")
                        # a short message: no button, gone after its 5 s
                        page.locator('[data-gvp-key="paper:agenda:copy"]').click()
                        page.wait_for_function("() => !document.querySelector('[data-gvp-toast]').classList.contains('is-idle')", timeout=5000)
                        self.assertEqual(page.locator("[data-gvp-toast] .gvp-toast-btn").count(), 0)
                        page.clock.run_for(9000)
                        self.assertTrue(page.evaluate(idle))
                    else:
                        # Esc on it puts it away too (and only it: the drawer stays open)
                        page.locator("[data-gvp-toast] .gvp-toast-btn").focus()
                        page.keyboard.press("Escape")
                        self.assertTrue(page.evaluate(idle))
                        self.assertTrue(page.locator("[data-gvp-drawer]").is_visible())
                        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-gvp-key')"),
                                         "paper:agenda:mail")
                finally:
                    ctx.close()
                self.assertEqual(errors, [])

    def test_the_long_message_on_a_spanish_phone_at_150_percent(self):
        """(follow-up) The same long message in Spanish on a 360-pixel phone at 150 % text: it used to keep its words and
        "Entendido" side by side — the button 17 px past the toast's edge, the words a narrow column, the toast 612 px
        tall over the drawer and the agenda it asks the chair to select. Now the button goes under the words: the toast
        and its button whole on the screen, nothing past its edge, no scrolling inside it, at most half the screen's
        height, over the slide at the top, so the drawer's panel (the text, "Abrir en mi correo" with the focus) stays
        in sight; a tap on "Entendido" puts it away. The clock: the deck's own build time, paused while measuring."""
        errors: list[str] = []
        ctx = new_context(360, 780, lang="es", prefs={"text": 150})
        try:
            seeded(ctx)
            ctx.clock.install(time=built_at())
            page = self.open_paper(ctx, "es", errors)
            self.show_tab(page)
            page.evaluate("""() => {
              const click = HTMLAnchorElement.prototype.click;
              HTMLAnchorElement.prototype.click = function () {
                if (/^mailto:/.test(this.getAttribute("href") || "")) return;
                return click.call(this);
              };
              navigator.clipboard.writeText = () => Promise.reject(new Error("not allowed"));
              document.execCommand = () => false;
            }""")
            page.locator('[data-gvp-key="paper:agenda:mail"]').click()
            page.wait_for_function("() => document.querySelector('[data-gvp-toast] .gvp-toast-btn')", timeout=5000)
            page.clock.pause_at(page.evaluate("() => (Date.now() + 500) / 1000"))   # (seconds: its 15 s never run out while measuring)
            text = page.locator("[data-gvp-toast] .gvp-toast-text").inner_text()
            self.assertGreater(len(text.split()), 30, text)
            self.assertEqual(page.locator("[data-gvp-toast] .gvp-toast-btn").inner_text(), "Entendido")
            r = page.evaluate(TOAST_SEEN)
            toast, msg, btn = r["toast"], r["msg"], r["btn"]
            # the toast whole on the screen, above the control bar
            self.assertGreaterEqual(toast["l"], 0, r)
            self.assertLessEqual(toast["r"], r["vw"], r)
            self.assertGreaterEqual(toast["t"], 0, r)
            self.assertLessEqual(toast["b"], r["low"] + 0.5, r)
            # its words and its button inside it: nothing past its edge, no scrolling inside it
            for name, b in (("the words", msg), ("Entendido", btn)):
                with self.subTest(inside=name):
                    self.assertGreaterEqual(b["l"], toast["l"] - 0.5, r)
                    self.assertLessEqual(b["r"], toast["r"] + 0.5, f"{name} past the toast's edge: {r}")
                    self.assertGreaterEqual(b["t"], toast["t"] - 0.5, r)
                    self.assertLessEqual(b["b"], toast["b"] + 0.5, r)
            self.assertLessEqual(r["sideways"], 0, r)
            self.assertLessEqual(r["down"], 0, "the whole message in sight, not scrolled")
            # the button under the words, the words across the toast (not a narrow column), the toast compact
            self.assertGreaterEqual(btn["t"], msg["b"] - 0.5, r)
            self.assertGreaterEqual(msg["w"], 0.75 * toast["w"], r)
            self.assertLessEqual(toast["h"], TOAST_TALL * r["vh"], f"the toast takes {toast['h']:.0f} of {r['vh']} px")
            self.assertGreaterEqual(btn["h"], 44, "a button a finger can tap")
            # over the slide, not the drawer's panel: the text to select and the button with the focus in sight
            self.assertLessEqual(toast["b"], r["panel"]["t"] + 0.5, f"the toast covers the drawer's panel: {r}")
            self.assertEqual(r["focus"], "paper:agenda:mail")
            self.assertTrue(r["focus_seen"], f"the toast covers the button that has the focus: {r}")
            self.assertTrue(r["tap"], f"a tap on Entendido lands on something else: {r}")
            page.clock.resume()
            page.locator("[data-gvp-toast] .gvp-toast-btn").click()
            self.assertTrue(page.evaluate("() => document.querySelector('[data-gvp-toast]').classList.contains('is-idle')"))
            self.assertTrue(page.locator("[data-gvp-drawer]").is_visible(), "Entendido closed the message only")
        finally:
            ctx.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
