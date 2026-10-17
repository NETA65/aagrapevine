"""The shared hero aside ("something on the right side of the hero": ui.pageHero opts.side + the
ui.heroAside* helpers in src/_includes/macros/ui.njk) — static checks of the page contract that need no
browser. (The measured browser checks — the card inside the 480px hero at 1024–1920px, below it or hidden
on smaller screens and at 115–150 % text, light / dark / high contrast / Data saver — are QA scripts.)

  * Macros    — ui.njk defines pageHero's `side` slot and every helper named in its doc block.
  * Slot form — a page that fills the "side" slot uses {% call(slot) ui.pageHero(…) %} (a call block
                without (slot) hands its whole body to every slot) and sets opts.side.
  * Players   — a page with ui.heroAsideVideo loads lite-youtube (pageScripts + pageStyles), or the
                player has no size and no play button.

    python -m unittest tests.test_hero_aside -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "_includes" / "macros" / "ui.njk"
PAGES = sorted((ROOT / "src" / "pages").glob("*.njk"))
HELPERS = ("heroAside", "heroAsideStat", "heroAsideLinks", "heroAsideLink", "heroAsideMedia", "heroAsideVideo")


def front_matter(text: str) -> str:
    m = re.match(r"---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    return m.group(1) if m else ""


class Macros(unittest.TestCase):
    def test_helpers_exist_and_are_documented(self):
        src = UI.read_text(encoding="utf-8")
        for name in HELPERS:
            with self.subTest(name=name):
                self.assertRegex(src, r"\{%\s*macro\s+" + name + r"\(", f"ui.njk has no macro {name}")
                self.assertIn("ui." + name + "(", src, f"{name} is not in the ui.njk doc block")
        self.assertIn('caller("side")', src, "pageHero reads the 'side' slot")
        self.assertIn("HERO ASIDE", src)


class Pages(unittest.TestCase):
    def test_side_slot_uses_call_with_slot_and_opts_side(self):
        for page in PAGES:
            text = page.read_text(encoding="utf-8")
            if not re.search(r"""slot\s*==\s*["']side["']""", text):
                continue
            with self.subTest(page=page.name):
                self.assertRegex(text, r"\{%-?\s*call\(slot\)\s+ui\.pageHero\(", "use {% call(slot) ui.pageHero(…) %}")
                self.assertRegex(text, r"""\bside:\s*\S""", "pageHero opts need side: \"below\" (or \"hide\")")

    def test_video_aside_loads_lite_youtube(self):
        for page in PAGES:
            text = page.read_text(encoding="utf-8")
            if "ui.heroAsideVideo(" not in text:
                continue
            fm = front_matter(text)
            with self.subTest(page=page.name):
                self.assertIn("/assets/vendor/lite-yt-embed.js", fm, "pageScripts must list /assets/vendor/lite-yt-embed.js")
                self.assertIn("/assets/vendor/lite-yt-embed.css", fm, "pageStyles must list /assets/vendor/lite-yt-embed.css")


if __name__ == "__main__":
    unittest.main()
