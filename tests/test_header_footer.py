"""The site's chrome on every page — static checks that need no browser (the screenshots at 320–1920px, in
both themes, high contrast and larger text, are the QA scripts' job).

  * Menu      — the phone / tablet menu (partials/header.njk, the drawer used below 1280px) has ONE light /
                dark control: a labelled "Dark mode" switch (role="switch", aria-checked from the theme), its
                first row right under the top bar — not an unlabelled moon icon there — driving the same state
                as the header's own moon / sun button (app.js siteHeader theme / toggleTheme, localStorage
                "gvlv-theme", applied before the first paint in base.njk). Its words in English and Spanish;
                its picture (main.css .site-switch) shows the state by position as well as colour, also in
                Windows High Contrast.
  * Footer    — the bottom bar (partials/footer.njk): from 768px the disclaimer on the left and the site links
                + "Last updated" on the right, then the copyright / reprint-permission notice across BOTH
                columns (the whole width of the footer); on a phone the same order, one column.

    python -m unittest tests.test_header_footer -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class Menu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = read("src", "_includes", "partials", "header.njk")
        cls.drawer = cls.header[cls.header.index('<template x-teleport="body">'):cls.header.index("</template>")]

    def test_one_labelled_switch_in_the_drawer(self):
        d = self.drawer
        self.assertEqual(d.count('@click="toggleTheme()"'), 1, "one theme control in the menu (no icon-only duplicate)")
        sw = re.search(r'<button type="button" role="switch"([^>]*)>(.*?)</button>', d, re.S)
        self.assertIsNotNone(sw)
        attrs, inner = sw.group(1), sw.group(2)
        for bit in ('aria-checked="false"', ''':aria-checked="(theme === 'dark').toString()"''', '@click="toggleTheme()"', "min-h-11", "w-full"):
            self.assertIn(bit, attrs)
        self.assertIn('{{ "nav.theme_dark" | t(L) }}', inner)                  # a visible label, its name
        self.assertIn('<span class="site-switch" aria-hidden="true"></span>', inner)
        self.assertNotIn("aria-label", attrs)                                   # named by its words, not a hidden label
        # right under the top bar (Menu · Aa · Close), before the links
        self.assertLess(d.index('x-ref="drawerClose"'), d.index('role="switch"'))
        self.assertLess(d.index('role="switch"'), d.index("<nav "))

    def test_the_header_button_stays_from_640px(self):
        outside = self.header.replace(self.drawer, "")
        btn = re.search(r'<button type="button" @click="toggleTheme\(\)" class="([^"]*)"[^>]*aria-label="\{\{ \'nav\.theme_aria\' \| t\(L\) \}\}"', outside)
        self.assertIsNotNone(btn)
        self.assertIn("hidden", btn.group(1).split())
        self.assertIn("sm:grid", btn.group(1).split())

    def test_one_state_saved_and_applied_before_paint(self):
        app = read("src", "assets", "js", "app.js")
        fn = app[app.index("toggleTheme: function"):]
        fn = fn[:fn.index("},") + 2]
        self.assertIn('this.theme = this.theme === "dark" ? "light" : "dark";', fn)
        self.assertIn('document.documentElement.setAttribute("data-theme", this.theme);', fn)
        self.assertIn('localStorage.setItem("gvlv-theme", this.theme)', fn)
        self.assertIn('theme: document.documentElement.getAttribute("data-theme") || "light"', app)
        head = read("src", "_includes", "layouts", "base.njk").split("</head>")[0]
        self.assertIn('localStorage.getItem("gvlv-theme")', head)

    def test_its_words_and_its_picture(self):
        strings = json.loads(read("src", "_i18n", "common.json"))
        self.assertEqual(strings["nav.theme_dark"], {"en": "Dark mode", "es": "Modo oscuro"})
        # the Accessibility page sends phone visitors to the switch by the words it shows
        dev = json.loads(read("src", "_i18n", "access.json"))["access.dev_dark"]
        self.assertIn("<strong>Dark mode</strong> switch", dev["en"])
        self.assertIn("interruptor <strong>Modo oscuro</strong>", dev["es"])
        css = read("src", "assets", "css", "main.css")
        for bit in (".site-switch {", "border: 2px solid var(--c-faint);",
                    '[aria-checked="true"] > .site-switch { border-color: var(--c-gv); background: var(--c-gv); }',
                    '[aria-checked="true"] > .site-switch::after { transform: translateX(1.25rem);', "@media (forced-colors: active)"):
            self.assertIn(bit, css)
        # the narrowest phones at larger text: the row's moon steps aside so the label keeps whole words
        self.assertIn(".site-theme > svg { display: none; }", read("src", "assets", "css", "areas", "access.css"))


class Footer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f = read("src", "_includes", "partials", "footer.njk")
        cls.bar = f[f.index('<div class="border-t border-line">'):f.index("</footer>")]

    def test_the_notice_runs_across_the_bar(self):
        bar = self.bar
        grid = re.search(r'<div class="container-page grid ([^"]*)">', bar).group(1).split()
        self.assertIn("md:grid-cols-[minmax(0,1fr)_fit-content(50%)]", grid)
        notice = re.search(r'<p class="([^"]*)">\{\{ "footer\.reprints" \| t\(L\) \}\}</p>', bar)
        self.assertIsNotNone(notice, "the notice is a grid item of its own")
        self.assertIn("md:col-span-2", notice.group(1).split())
        self.assertFalse([c for c in notice.group(1).split() if c.startswith("max-w-")], "never capped to a column")
        disclaimer = re.search(r'<p class="([^"]*)">\{\{ "footer\.disclaimer" \| t\(L\) \}\}</p>', bar)
        self.assertIsNotNone(disclaimer)
        self.assertIn("md:col-start-1", disclaimer.group(1).split())
        self.assertIn("md:row-start-1", disclaimer.group(1).split())
        links = re.search(r'<div class="([^"]*)">\s*<ul class="grid grid-cols-2', bar).group(1).split()
        self.assertEqual({"md:col-start-2", "md:row-start-1"} <= set(links), True)

    def test_phone_order(self):
        # one column below 768px, in the source order: the site links and the time, the disclaimer, the notice
        bar = self.bar
        self.assertLess(bar.index('{%- for f in nav.footer %}'), bar.index('"footer.last_updated"'))
        self.assertLess(bar.index('"footer.last_updated"'), bar.index('"footer.disclaimer"'))
        self.assertLess(bar.index('"footer.disclaimer"'), bar.index('"footer.reprints"'))


if __name__ == "__main__":
    unittest.main()
