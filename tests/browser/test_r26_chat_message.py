"""Round 26 · the Grapevine Meeting's message for the Google Meet chat, on the built site, in a real browser
(tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's site server and browser):

  * ChatMessageCopy — Customize → Prepare gives the Grapevine Meeting's page "Chat message for Google Meet" (a
                      `text` page for the chair) a Copy button — the only one in its Prepare, beside View and Print —
                      and pressing it puts the message on the clipboard as plain text, line by line: every web address
                      written out in full (a link would keep its words only), the day's facts filled in (no
                      "{live:" left, no "[blank]", no ** or link marks, no word joiner), and says "Copied". On the
                      Spanish page the button is "Copiar" and the message stays the deck's English, the same lines.

Nothing here depends on today's date: the dates in the message are checked by their shape, the site's own address by
the built deck's facts.
"""
from __future__ import annotations

import json
import re
import unittest

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401 (its site server)

DECK = "grapevine-meeting"
# A date as the deck's facts write it, or the fallback when the build knew no date ("see the Events page")
DATE = r"(?:(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day, [A-Z][a-z]+ \d{1,2}, \d{4}|see the (?:Events|Meetings) page)"


def built_site_url() -> str:
    """The committee website's full address, as the built deck gives it ({live:site_url})."""
    deck = json.loads((S["site"] / "orientation" / "presentations" / f"{DECK}.json").read_text(encoding="utf-8"))
    v = deck["live"]["site_url"]
    return v if isinstance(v, str) else v["value"]


class ChatMessageCopy(unittest.TestCase):
    def copied(self, lang: str) -> tuple[str, str, int]:
        """The Prepare tab of the Grapevine Meeting, its chat message's Copy pressed → (the clipboard, the button's
        words, how many Copy buttons the tab has)."""
        errors: list[str] = []
        ctx = new_context(1280, 900, lang=lang)
        try:
            page = open_page(ctx, ("es/" if lang == "es" else "") + f"orientation/?present={DECK}&mode=customize", errors)
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=page.evaluate("() => location.origin"))
            page.locator("[data-gvp-drawer]").wait_for(state="visible", timeout=30_000)
            page.locator('[data-gvp-tab="prepare"]').click()
            panel = page.locator('[data-gvp-panel="prepare"]')
            button = panel.locator('[data-gvp-key="copy:chat-message"]')
            button.wait_for(state="visible", timeout=10_000)
            count = panel.locator('[data-gvp-key^="copy:"]').count()
            words = button.inner_text().strip()
            # beside the page's own View and Print, in its card
            card = panel.locator("section.gvp-prep", has=page.locator('[data-gvp-key="copy:chat-message"]'))
            self.assertEqual(card.locator(".gvp-prep-h").inner_text().strip(), "Chat message for Google Meet")
            self.assertEqual(card.locator(".gvp-prep-acts button").count(), 3)
            button.click()
            page.wait_for_function("() => /Copied|Copiado/.test((document.querySelector('[data-gvp-toast]') || {}).textContent || '')",
                                   timeout=5000)
            # (Windows' clipboard hands the line breaks back as \r\n)
            clip = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
        finally:
            ctx.close()
        self.assertEqual(errors, [])
        return clip, words, count

    def test_the_message_as_plain_text(self):
        clip, words, count = self.copied("en")
        self.assertEqual(words, "Copy")
        self.assertEqual(count, 1, "only the deck's one page of text for the chair has a Copy button")
        lines = clip.split("\n")
        self.assertEqual(len(lines), 7, clip)
        self.assertEqual(lines[0], "🍇 Grapevine Meeting · links and dates 🍇")
        self.assertTrue(all(line.startswith("• ") for line in lines[1:]), lines)
        # the addresses written out in full, as Google Meet's chat makes links of them
        self.assertEqual(lines[1], "• Carry the Message: https://www.aagrapevine.org/carry-the-message · La Viña: "
                                   "https://www.aalavina.org/lleva-el-mensaje · or cash at our table at the next event")
        self.assertEqual(lines[2], "• Our table at CityWide Dallas: every 2nd Saturday, 5:30–7:30 PM, Lovers Lane United Methodist Church")
        self.assertRegex(lines[3], rf"^• Grapevine Meeting: every 1st Wednesday, .+, on this Google Meet \(next: {DATE}\)$")
        self.assertRegex(lines[4], rf"^• Committee meeting: every 3rd Wednesday, .+, the same link \(next: {DATE}\)$")
        self.assertEqual(lines[5], "• Write for Grapevine: https://www.aagrapevine.org/submit-your-story")
        site = built_site_url()
        self.assertTrue(site.startswith("https://"), site)
        self.assertEqual(lines[6], f"• Dates and flyers: {site} · NETA 65: https://neta65.org")
        # plain text: every fact filled in, no blank, no formatting marks, no link's words without its address
        for mark in ("{live:", "{fill:", "{lang:", "[", "]", "**", "](", "⁠", "", ""):
            self.assertNotIn(mark, clip, mark)
        self.assertEqual(re.findall(r"https://\S+", clip), ["https://www.aagrapevine.org/carry-the-message",
                                                             "https://www.aalavina.org/lleva-el-mensaje",
                                                             "https://www.aagrapevine.org/submit-your-story",
                                                             site, "https://neta65.org"])

    def test_the_spanish_page(self):
        clip_es, words, count = self.copied("es")
        self.assertEqual(words, "Copiar")
        self.assertEqual(count, 1)
        clip_en, _, _ = self.copied("en")
        self.assertEqual(clip_es, clip_en, "the deck's own English, whatever the page's language")


if __name__ == "__main__":
    unittest.main()
