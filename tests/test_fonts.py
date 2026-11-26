"""The web fonts (src/assets/css/main.css "Fonts", eleventy.config.js, src/pages/sw.11ty.js,
src/_includes/layouts/base.njk): Inter and Fraunces, Latin and Latin Extended, and Fraunces' italic — the brand's
display italic (the hero's "meeting in print", the daily quotes, the magazines' names), whose letters are its own.
Since November 2026 no Inter italic file (52 KB): Inter's italic is the upright face slanted by the browser
(font-synthesis-style: auto), very nearly what its own italic is. A browser downloads a face only for text that uses it,
and no italic is preloaded: a page without Fraunces italic pays nothing for it.

  * CSS     — every Inter @font-face is font-style: normal and names an upright file; Fraunces has its two upright
              faces and one italic one (the Latin file, with the Latin unicode-range); the fallback faces have an
              italic for Fraunces only (Georgia Italic, measured like the upright ones), none for Inter; synthesis is on.
  * Files   — the build copies exactly the files the CSS names; the offline worker keeps the Latin ones (the app's
              start page, Home, shows Fraunces italic) and never an Inter italic.
  * Preload — the head preloads Inter's Latin file on every page and Fraunces' upright one on the home page only —
              never an italic or an extended file.

    python -m unittest tests.test_fonts -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPRIGHT = {"inter-latin-wght-normal", "inter-latin-ext-wght-normal", "fraunces-latin-opsz-normal", "fraunces-latin-ext-opsz-normal"}
FILES = UPRIGHT | {"fraunces-latin-opsz-italic"}


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def faces(css: str) -> list[str]:
    return re.findall(r"@font-face \{([^}]*)\}", css)


class Fonts(unittest.TestCase):
    def test_the_css_faces(self):
        css = read("src", "assets", "css", "main.css")
        all_faces = faces(css)
        self.assertGreaterEqual(len(all_faces), 11)
        files = set()
        italic = []
        for f in all_faces:
            family = re.search(r'font-family: "([^"]+)"', f).group(1)
            named = re.findall(r'url\("\.\./fonts/([a-z0-9-]+)\.woff2"\)', f)
            files.update(named)
            if "font-style: italic" in f:
                italic.append((family, named))
            with self.subTest(face=f[:70]):
                if family.startswith("Inter"):
                    self.assertNotIn("italic", f, "no Inter italic: the upright face slanted")
        self.assertEqual(files, FILES)
        self.assertEqual(italic, [("Fraunces Variable", ["fraunces-latin-opsz-italic"]), ("Fraunces Fallback", []), ("Fraunces Fallback", [])])
        face = next(f for f in all_faces if "fraunces-latin-opsz-italic" in f)
        upright = next(f for f in all_faces if "fraunces-latin-opsz-normal" in f)
        self.assertEqual(re.search(r"unicode-range: ([^;]+);", face).group(1), re.search(r"unicode-range: ([^;]+);", upright).group(1))
        self.assertIn('src: local("Georgia Italic")', css)
        self.assertIn("font-synthesis-style: auto;", css)

    def test_the_files_copied_and_kept_offline(self):
        conf = read("eleventy.config.js")
        copied = set(re.findall(r'"((?:inter|fraunces)-[a-z0-9-]+)"', conf[conf.index("const nm = (p)"):conf.index("/* ---------- i18n filters")]))
        self.assertEqual(copied, FILES)
        sw = read("src", "pages", "sw.11ty.js")
        kept = set(re.findall(r'a\("assets/fonts/([a-z0-9-]+)\.woff2"\)', sw))
        self.assertEqual(kept, {"inter-latin-wght-normal", "fraunces-latin-opsz-normal", "fraunces-latin-opsz-italic"})
        self.assertNotIn("inter-latin-wght-italic", sw)
        self.assertNotIn("required", sw[sw.index('a("assets/fonts/fraunces-latin-opsz-italic.woff2")') - 400:sw.index('a("assets/fonts/fraunces-latin-opsz-italic.woff2")')],
                         "an optional part of the app shell")

    def test_the_head_preloads_upright_faces(self):
        base = read("src", "_includes", "layouts", "base.njk")
        pre = re.findall(r"'/assets/fonts/([a-z0-9-]+)\.woff2'", base)
        self.assertEqual(pre, ["inter-latin-wght-normal", "fraunces-latin-opsz-normal"])
        self.assertIn('{% if pageKey == "home" %}, "{{ \'/assets/fonts/fraunces-latin-opsz-normal.woff2\' | url }}"{% endif %}', base)
        self.assertNotIn("italic.woff2", base)


if __name__ == "__main__":
    unittest.main()
