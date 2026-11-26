"""The web fonts every page loads (src/assets/css/main.css "Fonts", eleventy.config.js, src/pages/sw.11ty.js,
src/_includes/layouts/base.njk): since November 2026 the upright faces only — Inter and Fraunces, Latin and Latin
Extended — and no italic files (the two were 134 of the ~250 KB of fonts every page loaded). Italic text is the
upright face slanted by the browser (font-synthesis-style: auto).

  * CSS     — every @font-face of a web font is font-style: normal and names an upright file; no fallback face is
              italic either (what a slow page shows first slants the same way); synthesis is on.
  * Files   — the build copies only the upright files; the offline worker keeps only those.
  * Preload — the head preloads Inter's Latin file on every page and Fraunces' on the home page only — never an italic
              or an extended file.

    python -m unittest tests.test_fonts -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPRIGHT = {"inter-latin-wght-normal", "inter-latin-ext-wght-normal", "fraunces-latin-opsz-normal", "fraunces-latin-ext-opsz-normal"}


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class Fonts(unittest.TestCase):
    def test_the_css_has_upright_faces_only(self):
        css = read("src", "assets", "css", "main.css")
        faces = re.findall(r"@font-face \{([^}]*)\}", css)
        self.assertGreaterEqual(len(faces), 8)
        files = set()
        for f in faces:
            with self.subTest(face=f[:60]):
                self.assertNotIn("italic", f)
                files.update(re.findall(r'url\("\.\./fonts/([a-z0-9-]+)\.woff2"\)', f))
        self.assertEqual(files, UPRIGHT)
        self.assertIn("font-synthesis-style: auto;", css)

    def test_only_those_files_are_copied_and_kept_offline(self):
        conf = read("eleventy.config.js")
        copied = set(re.findall(r'"((?:inter|fraunces)-[a-z0-9-]+)"', conf[conf.index("const nm = (p)"):conf.index("/* ---------- i18n filters")]))
        self.assertEqual(copied, UPRIGHT)
        sw = read("src", "pages", "sw.11ty.js")
        kept = set(re.findall(r'a\("assets/fonts/([a-z0-9-]+)\.woff2"\)', sw))
        self.assertTrue(kept <= UPRIGHT and kept)
        self.assertNotIn("italic.woff2", sw)

    def test_the_head_preloads_upright_faces(self):
        base = read("src", "_includes", "layouts", "base.njk")
        pre = re.findall(r"'/assets/fonts/([a-z0-9-]+)\.woff2'", base)
        self.assertEqual(pre, ["inter-latin-wght-normal", "fraunces-latin-opsz-normal"])
        self.assertIn('{% if pageKey == "home" %}, "{{ \'/assets/fonts/fraunces-latin-opsz-normal.woff2\' | url }}"{% endif %}', base)


if __name__ == "__main__":
    unittest.main()
