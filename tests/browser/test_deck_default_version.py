"""The version the committee meeting's presentation opens on, in a real browser on the built site (tests/browser/
__init__.py says how to run these; they share test_site_in_browser.py's site server and browser):

  * DefaultVersion — on a device where no version was ever chosen, a week before a meeting the site lists no guest
                     speaker for (December 16, 2026: config/site.yml `meeting.speakers`), the deck opens on "No
                     guest speaker": no guest speaker's slide in the overview (never "Welcome to our guest speaker
                     · none tonight"), Customize → Version has it picked and says it was chosen for you, in
                     English and in Spanish — and nothing is stored for it. A version picked there (the first one)
                     is kept: after a reload the deck opens on it, without that line. A week before a meeting with
                     a guest speaker listed (January 20, 2027), the first version, with the speaker's slide.
The offline side (the core, the real deck at fixed clocks): tests/test_presentations_default_version.py.

Nothing here depends on today's date: the browser's clock (Playwright's) is stopped a week before meetings taken
from the built deck's own paperwork rows (the build's settings); a test is skipped when the deck lists no such
meeting ahead.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401 (its site server)

STATE_KEY = "gv-presentations-v1"
DECK = "committee-meeting"
SPEAKER_TITLE = "Welcome to our guest speaker"


def built_deck() -> dict:
    return json.loads((S["site"] / "orientation" / "presentations" / f"{DECK}.json").read_text(encoding="utf-8"))


def week_before(iso: str) -> str:
    return (datetime.fromisoformat(iso.replace("Z", "+00:00")) - timedelta(days=7)).astimezone(timezone.utc).isoformat()


def stored(page) -> dict | None:
    return page.evaluate("(k) => JSON.parse(localStorage.getItem(k) || 'null')", STATE_KEY)


class DefaultVersion(unittest.TestCase):
    def meeting(self, no_speaker: bool) -> dict:
        deck = built_deck()
        row = next((r for r in deck["paperwork"]["meetings"] if r["start"] > deck["built"]
                    and (r.get("no_speaker") if no_speaker else (r.get("speaker") or {}).get("name"))), None)
        if not row:
            self.skipTest("the built deck lists no meeting ahead " + ("without a guest speaker" if no_speaker else "with one"))
        return row

    def overview_titles(self, ctx, lang: str, errors: list) -> list[str]:
        page = open_page(ctx, ("es/" if lang == "es" else "") + f"orientation/?present={DECK}&mode=overview", errors)
        page.locator("[data-gvp-ov-grid] .gvp-thumb").first.wait_for(timeout=30_000)
        titles = page.locator("[data-gvp-ov-grid] .gvp-thumb .gvp-slide").all_inner_texts()
        page.close()
        return titles

    def version_panel(self, ctx, lang: str, errors: list):
        page = open_page(ctx, ("es/" if lang == "es" else "") + f"orientation/?present={DECK}&mode=customize", errors)
        page.locator("[data-gvp-drawer]").wait_for(state="visible", timeout=30_000)
        page.locator('[data-gvp-tab="version"]').click()
        page.locator('[data-gvp-panel="version"] .gvp-radios').wait_for(timeout=10_000)
        return page

    def checked(self, page) -> str:
        return page.locator('[data-gvp-panel="version"] input[name="gvp-preset"]:checked').get_attribute("value")

    def test_a_meeting_without_a_guest_speaker(self):
        row = self.meeting(no_speaker=True)
        errors: list[str] = []
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            try:
                ctx.clock.set_fixed_time(week_before(row["start"]))
                titles = self.overview_titles(ctx, lang, errors)
                self.assertTrue(titles, lang)
                self.assertFalse([t for t in titles if SPEAKER_TITLE in t or "none tonight" in t], (lang, titles))
                page = self.version_panel(ctx, lang, errors)
                self.assertEqual(self.checked(page), "no-speaker", lang)
                note = page.locator("[data-gvp-version-auto]")
                self.assertEqual(note.count(), 1, lang)
                text = note.inner_text()
                if lang == "en":
                    self.assertIn("Chosen for you: the Meetings page lists no guest speaker for " + row["label"], text)
                    self.assertIn("“No guest speaker (about 60 minutes)”", text)
                else:
                    self.assertIn("Elegida para ti", text)
                    self.assertIn(row["label_es"], text)
                    self.assertIn("«Sin orador(a) invitado(a) (unos 60 minutos)»", text)
                self.assertNotIn("pres.", text)
                self.assertFalse(((stored(page) or {}).get("decks") or {}).get(DECK, {}).get("preset"),
                                 "the default is not stored as a choice")
                # the first version picked is the presenter's: kept after a reload, without "Chosen for you"
                if lang == "en":
                    page.locator('[data-gvp-panel="version"] input[value="full"]').check()
                    self.assertEqual(stored(page)["decks"][DECK]["preset"], "full")
                    page.close()
                    page = self.version_panel(ctx, lang, errors)
                    self.assertEqual(self.checked(page), "full")
                    self.assertEqual(page.locator("[data-gvp-version-auto]").count(), 0)
                    page.close()
                    titles = self.overview_titles(ctx, lang, errors)
                    self.assertTrue([t for t in titles if SPEAKER_TITLE in t], titles)
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_a_meeting_with_a_guest_speaker(self):
        row = self.meeting(no_speaker=False)
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="en")
        try:
            ctx.clock.set_fixed_time(week_before(row["start"]))
            titles = self.overview_titles(ctx, "en", errors)
            self.assertTrue([t for t in titles if SPEAKER_TITLE in t], titles)
            page = self.version_panel(ctx, "en", errors)
            self.assertEqual(self.checked(page), "full")
            self.assertEqual(page.locator("[data-gvp-version-auto]").count(), 0)
        finally:
            ctx.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
