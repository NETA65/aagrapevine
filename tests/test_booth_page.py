"""The booth display on the About page (/about/, /es/about/ #booth): src/_includes/macros/booth.njk (the section, the
player's dialog shell and its #gvb-config), src/pages/about.njk (the section after #committee, the "On this page"
entry, the scripts), src/assets/js/booth.js (the screen; its logic, booth-core.js, has tests/test_booth_core.py),
src/assets/css/areas/booth.css and src/_i18n/booth.json.

  * Strings — every booth.* text in English AND Spanish (tests/test_i18n_keys.py checks the placeholders for every
              file); every key booth.js asks for exists and reaches it (the macro's pageKeys / screenKeys lists that
              #gvb-config is made of), every key of those lists and of the templates exists; every topic (tag) the CSV
              and the live items use has its two words (Settings → Show lists them in the page's language); the
              wording rules (never "PDF"; La Viña first in a Spanish text that names both magazines).
  * Wiring  — about.njk imports the macro, puts the section between #committee and #privacy, lists it in "On this
              page" and loads booth-core.js before booth.js; main.css imports booth.css right after presentations.css;
              booth.js keeps its promises (storage in try/catch, the worker's messages — to the worker that knows
              them, the new one taking over from an old one —, a slide's QR code through GVB.qrOf, the settings kept
              as a diff, no PIN in a share link, a probe's answer never left unread) and its accessibility ones (the
              visitors' bar a group, no pressed state on a Pause that changes its words, the video's Sound a toggle
              with one name, "Leave the show" in Settings for a touch screen).
  * Built   — after a build (skipped without a fresh one, like the other page tests): both About pages have the
              section, its nav entry, the dialog shell with Settings' eight tabs, the config JSON (the page's language,
              the base path, the show's address, the page-language strings, the on-screen words in BOTH languages) and
              the scripts in order; /about/booth.json parses once the show's page (src/pages/booth-json.11ty.js) is
              part of the build.

    python -m unittest tests.test_booth_page -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRINGS = ROOT / "src" / "_i18n" / "booth.json"
MACRO = ROOT / "src" / "_includes" / "macros" / "booth.njk"
PAGE = ROOT / "src" / "pages" / "about.njk"
APP = ROOT / "src" / "assets" / "js" / "booth.js"
CORE = ROOT / "src" / "assets" / "js" / "booth-core.js"
CSS = ROOT / "src" / "assets" / "css" / "areas" / "booth.css"
CSV = ROOT / "content" / "booth" / "booth.csv"
FILTERS = ROOT / "eleventy" / "filters" / "booth.js"
MAIN_CSS = ROOT / "src" / "assets" / "css" / "main.css"
SITE = ROOT / "_site"
BUILT = {"en": SITE / "about" / "index.html", "es": SITE / "es" / "about" / "index.html"}
SHOW_PAGE = ROOT / "src" / "pages" / "booth-json.11ty.js"
TABS = ["event", "show", "items", "timing", "screen", "kiosk", "offline", "share"]
# a key the script puts together from a name: booth.ch.<channel>, booth.why.<reason> …
KEY = re.compile(r'"(booth\.[a-z0-9_.]+)"')


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def strings() -> dict:
    return json.loads(read(STRINGS))


def macro_list(name: str) -> list[str]:
    m = re.search(r"\{%-\s*set " + name + r" = \[(.*?)\]\s*-%\}", read(MACRO), re.S)
    assert m, f"booth.njk has no {name} list"
    return re.findall(r'"([^"]+)"', m.group(1))


def script_keys() -> tuple[set[str], set[str]]:
    """The keys booth.js names (TN / SN add the _one form), and the prefixes it builds keys from."""
    js = read(APP)
    keys = set(KEY.findall(js))
    for k in re.findall(r'\bTN\("(booth\.[a-z0-9_.]+)"', js) + re.findall(r'\bSN\([^,]+, "(booth\.[a-z0-9_.]+)"', js):
        keys.add(k + "_one")
    prefixes = {k for k in keys if k.endswith(".")}
    return keys - prefixes, prefixes


class Strings(unittest.TestCase):
    def setUp(self):
        self.s = strings()

    def test_both_languages(self):
        self.assertGreater(len(self.s), 300)
        for key, v in self.s.items():
            with self.subTest(key=key):
                self.assertTrue(key.startswith("booth."), "booth.json holds booth.* keys only")
                self.assertTrue(v.get("en", "").strip() and v.get("es", "").strip(), "both languages")

    def test_every_key_the_script_uses_exists_and_reaches_it(self):
        keys, prefixes = script_keys()
        self.assertGreater(len(keys), 150)
        page = {"booth." + k for k in macro_list("pageKeys")}
        screen = {"booth.screen." + k for k in macro_list("screenKeys")}
        for k in sorted(keys):
            with self.subTest(key=k):
                self.assertIn(k, self.s)
                self.assertIn(k, screen if k.startswith("booth.screen.") else page, "#gvb-config gives the script only the listed keys")
        # a key built from a name (booth.ch.<channel> …): the family is in the lists, and every one of it exists
        for p in sorted(prefixes - {"booth.screen."}):
            with self.subTest(prefix=p):
                family = [k for k in self.s if k.startswith(p)]
                self.assertTrue(family, p)
                for k in family:
                    self.assertIn(k, page)

    def test_the_families_the_script_builds(self):
        """The channels of booth-core.js (dashes as underscores), the reasons why() gives, the presets (the core's
        lists: booth.js takes them from GVB), the render types and the language modes each have their words."""
        js, core = read(APP), read(CORE)
        channels = re.search(r"var CHANNELS = \[(.*?)\];", core, re.S).group(1)
        ids = re.findall(r'\{ id: "([a-z-]+)"', channels)
        self.assertGreaterEqual(len(ids), 27)
        for ch in ids:
            with self.subTest(channel=ch):
                self.assertIn("booth.ch." + ch.replace("-", "_"), self.s)
        for why in ["off", "channel", "pub", "collection", "tag", "date", "ended", "lang", "offline", "muted", "media", "youtube", "unknown"]:
            self.assertIn("booth.why." + why, self.s)
        self.assertIn("var PRESETS = G.PRESETS.slice();", js)
        for name in re.findall(r'"([a-z]+)"', re.search(r"var PRESETS = \[(.*?)\];", core).group(1)):
            with self.subTest(preset=name):
                self.assertIn("booth.preset." + name, self.s)
                self.assertIn("booth.preset." + name + "_d", self.s)
        renders = set(re.findall(r"\bRENDER\.(\w+) = ", js))
        self.assertGreaterEqual(renders, {"quiz", "truefalse", "fact", "quote", "history", "fill", "scramble", "poll", "prompt", "message",
                                          "qr", "video", "audio", "image", "photo", "poster", "events", "countdown", "themes", "prices",
                                          "book", "meetings", "welcome", "about", "score"})
        for t in renders - {"score"}:
            with self.subTest(type=t):
                self.assertIn("booth.type." + t, self.s)
        for m in ["en", "es", "both", "alternate"]:
            self.assertIn("booth.lang." + m, self.s)
            self.assertIn("booth.lang_d." + m, self.s)

    def test_every_listed_and_template_key_exists(self):
        for k in ["booth." + x for x in macro_list("pageKeys")] + ["booth.screen." + x for x in macro_list("screenKeys")]:
            with self.subTest(key=k):
                self.assertIn(k, self.s)
        for src in (MACRO, PAGE):
            for k in re.findall(r"""["'](booth\.[a-z0-9_.]+)["']\s*\|\s*t\b""", read(src)):
                with self.subTest(file=src.name, key=k):
                    self.assertIn(k, self.s)
        for tab in TABS:
            self.assertIn("booth.tab." + tab, self.s)
        for n in range(1, 8):
            self.assertIn(f"booth.how_{n}", self.s)

    def test_wording(self):
        for key, v in self.s.items():
            for lang in ("en", "es"):
                with self.subTest(key=key, lang=lang):
                    self.assertNotRegex(v[lang], r"\bPDF\b", "a visitor never reads “PDF” (say document / save a copy)")
                    self.assertNotRegex(v[lang], r"(?i)\b(donat|buy now|hurry|limited time|conference-approved)")
            es = v["es"]
            if "Grapevine" in es and "La Viña" in es:
                with self.subTest(key=key, rule="La Viña first"):
                    self.assertLess(es.index("La Viña"), es.index("Grapevine"), "La Viña first in Spanish")

    def test_the_screen_words_match_the_core_where_they_overlap(self):
        """The welcome line names La Viña first in Spanish, as booth-core.js's own welcome slide does; the welcome
        slide's title joins no sentence to the event's name ("¡Bienvenidos a Asamblea…!" would lack its "la")."""
        self.assertEqual(self.s["booth.screen.welcome_line"]["es"], "La Viña y Grapevine — pregúntanos lo que quieras")
        self.assertEqual(self.s["booth.screen.welcome"]["en"], "Welcome! · {event}")
        self.assertEqual(self.s["booth.screen.welcome"]["es"], "¡Bienvenidos! · {event}")
        core = read(CORE)
        self.assertIn('welcome: "Welcome! · {event}"', core)
        self.assertIn('welcome: "¡Bienvenidos! · {event}"', core)

    def test_every_topic_has_its_words(self):
        """Settings → Show lists the topics (the CSV's tags, and the live items' own) in the page's language:
        booth.tag.<tag> (dashes as underscores) in both languages, listed for #gvb-config. A new tag in the CSV
        needs its two words in src/_i18n/booth.json."""
        import csv
        used = set()
        with CSV.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("id") or "").strip().startswith("#"):
                    continue
                used.update(t for t in re.split(r"[;,\s]+", (row.get("tags") or "").strip().lower()) if t)
        for lit in re.findall(r"tags: \[([^\]]*)\]", read(FILTERS)):
            used.update(re.findall(r'"([a-z0-9-]+)"', lit))
        self.assertGreater(len(used), 20)
        page = set(macro_list("pageKeys"))
        for tag in sorted(used):
            key = "booth.tag." + tag.replace("-", "_")
            with self.subTest(tag=tag):
                self.assertIn(key, self.s, "a topic without its words in src/_i18n/booth.json")
                self.assertIn(key[len("booth."):], page)
        labels = {}
        for tag in used:
            v = self.s.get("booth.tag." + tag.replace("-", "_"), {})
            for lang in ("en", "es"):
                labels.setdefault((lang, v.get(lang)), []).append(tag)
        twice = {k: v for k, v in labels.items() if len(v) > 1}
        self.assertEqual(twice, {}, "two topics with the same words would show as two identical boxes")


class Wiring(unittest.TestCase):
    def test_about_page(self):
        page = read(PAGE)
        front = page.split("---", 2)[1]
        scripts = re.search(r"pageScripts:\s*\[(.*?)\]", front).group(1)
        order = re.findall(r'"([^"]+)"', scripts)
        self.assertIn("/assets/js/booth-core.js", order)
        self.assertIn("/assets/js/booth.js", order)
        self.assertLess(order.index("/assets/js/booth-core.js"), order.index("/assets/js/booth.js"), "the core first")
        self.assertIn('{% import "macros/booth.njk" as boothUi with context %}', page)
        body = page.split("-#}", 1)[1]
        self.assertLess(body.index('id="committee"'), body.index("{{ boothUi.section(lang) }}"))
        self.assertLess(body.index("{{ boothUi.section(lang) }}"), body.index('id="privacy"'))
        self.assertIn("{{ boothUi.player(lang) }}", body)
        nav = re.search(r"ui\.pageNav\(\[(.*?)\], lang\)", body, re.S).group(1)
        hrefs = re.findall(r'href: "([^"]+)"', nav)
        self.assertLess(hrefs.index("#committee"), hrefs.index("#booth"))
        self.assertLess(hrefs.index("#booth"), hrefs.index("#privacy"))
        self.assertIn('label: "booth.nav" | t(lang)', nav)

    def test_stylesheet_imported_after_presentations(self):
        imports = re.findall(r'@import "\./areas/([a-z-]+)\.css";', read(MAIN_CSS))
        self.assertIn("booth", imports)
        self.assertEqual(imports.index("booth"), imports.index("presentations") + 1)
        css = read(CSS)
        self.assertIn("container: gvb / size", css, "sizes in container units: the same slide fills a TV and the card")
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn('[data-contrast="high"]', css)
        self.assertRegex(css, r"@media print \{[^}]*\.gvb\b")

    def test_the_script_keeps_its_promises(self):
        js = read(APP)
        # storage only inside try/catch: the two helpers, nothing else touches localStorage
        uses = [m.start() for m in re.finditer(r"localStorage\.", js)]
        self.assertTrue(uses)
        for at in uses:
            block = js[max(0, at - 400):at]
            self.assertIn("try {", block, "every localStorage access in try/catch")
        for key in ("gv-booth-v1", "gv-booth-polls-v1", "gv-booth-state-v1"):
            self.assertIn(f'"{key}"', js)
        for msg in ("BOOTH_SAVE", "BOOTH_STATUS", "BOOTH_CLEAR", "BOOTH_PROGRESS", "BOOTH_DONE", "BOOTH_CLEARED"):
            self.assertIn(f'"{msg}"', js)
        self.assertIn("youtube-nocookie.com", js)
        self.assertIn("MessageChannel", js)
        self.assertIn("wakeLock", js)
        self.assertNotIn("innerHTML", js, "text and elements only: nothing from the show is read as HTML")
        self.assertNotRegex(js, r"\bPDF\b")
        # a slide's QR code in the slide's language: the core's qrOf (an item's qr_es on a Spanish slide), so no
        # renderer reads item.qr by itself
        self.assertIn('call("qrOf", [item, l, SETTINGS]', js)
        self.assertNotRegex(js, r"R\.item\.qr\b")
        # the settings are kept as a diff against the site's (GVB.diff); the share link never carries the PIN
        self.assertIn('call("diff", [SETTINGS, BASE_SETTINGS || baseSettings()], null)', js)
        self.assertRegex(js, r'function startLink\(\) \{\s*var s = clone\(SETTINGS\) \|\| \{\};\s*s\.pin = "";')
        # the booth's messages go to the worker that knows them: on a device that had the site before, the new worker
        # waits behind the old one — the operator's saves let it take over (SKIP_WAITING), never only the old one
        self.assertIn('postMessage({ type: "SKIP_WAITING" })', js)
        self.assertIn("function boothWorker(reg, takeOver)", js)
        self.assertNotIn("var w = reg.active || navigator.serviceWorker.controller;", js)
        self.assertRegex(js, r'type: "BOOTH_SAVE"[^\n]*\n(?:.*\n){0,12}?.*45000, true, 15000\)')
        # a probe's answer is cancelled (an unread body keeps its loader alive all day)
        self.assertRegex(js, r"setOnline\(!!r\.ok\); dropBody\(r\);")

    def test_the_screen_keeps_its_accessibility_promises(self):
        js, njk = read(APP), read(MACRO)
        # the visitors' bar: a group of buttons (a toolbar would promise ← → between them; those are the slides' keys)
        self.assertIn('attrs(el("div", "gvb-bar"), { role: "group" })', js)
        self.assertNotIn('role: "toolbar"', js)
        # Pause (the bar's and the preview's) says what a tap does: no pressed state as well
        self.assertNotRegex(js, r'vb\.pause\.setAttribute\("aria-pressed"')
        inline = re.search(r"function inlinePauseLabel\(\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertNotIn("aria-pressed", inline)
        # the video's Sound: one name, pressed while it plays with its sound
        self.assertIn('S(R.lead, "booth.screen.sound")', js)
        self.assertIn('snd.setAttribute("aria-pressed"', js)
        self.assertNotIn("booth.screen.unmute", js)
        # a touch screen's way out: "Leave the show" at the foot of Settings
        self.assertIn('data-gvb-act="leave"', njk)
        self.assertIn('name === "leave"', js)
        # answered choices and voted rows keep the focus (aria-disabled, not disabled)
        self.assertIn('b.setAttribute("aria-disabled", "true")', js)
        self.assertIn('r.b.setAttribute("aria-disabled", "true")', js)

    def test_the_section_and_its_hooks(self):
        njk = read(MACRO)
        for hook in ("data-gvb-start", "data-gvb-settings", "data-gvb-preview", "data-gvb-pv-frame", 'data-gvb-q="event"', 'data-gvb-q="event_es"',
                     'data-gvb-q="lang"', 'data-gvb-q="preset"', 'data-gvb-chip="items"', 'data-gvb-chip="content"', 'data-gvb-chip="offline"',
                     "<noscript>", "how-to/booth.md", 'id="gvb-tpl"', 'id="gvb-icons"', 'id="gvb-config"'):
            with self.subTest(hook=hook):
                self.assertIn(hook, njk)
    def test_every_icon_the_script_draws_is_printed(self):
        """The script draws its icons from #gvb-icons (the site's {% icon %} prints them at build time): every icon
        name on a line of booth.js that draws one (icon(…), { icon: … }, eyebrow, listSlide, setBtn) is there."""
        lucide = ROOT / "node_modules" / "lucide-static" / "icons"
        local = ROOT / "src" / "_includes" / "icons"
        if not lucide.is_dir():
            self.skipTest("node_modules (lucide-static) is not installed")
        njk = read(MACRO)
        tpl = re.search(r'<template id="gvb-icons">(.*?)</template>', njk, re.S).group(1)
        printed = set(re.findall(r'"([a-z0-9-]+)"', re.search(r"\{%-?\s*for n in \[(.*?)\]\s*%\}", tpl, re.S).group(1)))
        for name in printed:
            with self.subTest(printed=name):
                self.assertTrue((lucide / f"{name}.svg").exists() or (local / f"{name}.svg").exists(), name)
        used = set()
        for line in read(APP).splitlines():
            if re.search(r"\bicon\(|icon: |eyebrow\(|listSlide\(|setBtn\(", line):
                for name in re.findall(r'"([a-z0-9]+(?:-[a-z0-9]+)*)"', line):
                    if (lucide / f"{name}.svg").exists() or (local / f"{name}.svg").exists():
                        used.add(name)
        self.assertGreater(len(used), 25)
        for name in sorted(used):
            with self.subTest(icon=name):
                self.assertIn(name, printed)


def fresh_build() -> bool:
    """Both About pages built after their sources changed (an older build would show an older page). The tests job
    in CI does not build the site: these checks run after a local build."""
    if not all(p.exists() for p in BUILT.values()):
        return False
    built = min(p.stat().st_mtime for p in BUILT.values())
    return all(built >= s.stat().st_mtime for s in (PAGE, MACRO, STRINGS))


@unittest.skipUnless(fresh_build(), "no fresh build (npx @11ty/eleventy) to check")
class Built(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bs4 import BeautifulSoup                      # (requirements.txt; only these checks need it)
        cls.soup = {lang: BeautifulSoup(read(p), "lxml") for lang, p in BUILT.items()}
        cls.s = strings()

    def test_the_section_and_its_nav_entry(self):
        for lang, soup in self.soup.items():
            with self.subTest(lang=lang):
                sec = soup.select_one("section#booth")
                self.assertIsNotNone(sec)
                self.assertEqual(sec.get("aria-labelledby"), "booth-title")
                self.assertEqual(soup.select_one("#booth-title").get_text(strip=True), self.s["booth.title"][lang])
                ids = [s.get("id") for s in soup.select("main section[id]")]
                self.assertLess(ids.index("committee"), ids.index("booth"))
                self.assertLess(ids.index("booth"), ids.index("privacy"))
                chips = {a["href"]: a.get_text(" ", strip=True) for a in soup.select("nav.page-nav a.chip")}
                self.assertIn("#booth", chips)
                self.assertEqual(chips["#booth"], self.s["booth.nav"][lang])
                self.assertIsNotNone(sec.select_one("[data-gvb-start]"))
                self.assertIsNotNone(sec.select_one("[data-gvb-pv-frame] [data-gvb-still]"), "a still slide without JavaScript")
                self.assertIn(self.s["booth.noscript"][lang], sec.select_one("noscript").get_text())
                link = sec.select_one('a[href$="/blob/main/how-to/booth.md"]')
                self.assertIsNotNone(link)
                self.assertEqual(len(sec.select(".gvb-how-steps > li")), 7)

    def test_the_dialog_shell(self):
        for lang, soup in self.soup.items():
            with self.subTest(lang=lang):
                tpl = soup.select_one("template#gvb-tpl")
                self.assertIsNotNone(tpl)
                html = tpl.decode_contents()
                for tab in TABS:
                    self.assertIn(f'data-gvb-tab="{tab}"', html)
                    self.assertIn(f'data-gvb-panel="{tab}"', html)
                self.assertIn('role="dialog"', html)
                self.assertIn('aria-modal="true"', html)
                self.assertIn(f'lang="{lang}"', html)
                self.assertIn("data-gvb-pin", html)
                self.assertIn("data-gvb-leave", html)
                self.assertIn('data-gvb-act="leave"', html)

    def test_the_config(self):
        keys, _ = script_keys()
        for lang, soup in self.soup.items():
            with self.subTest(lang=lang):
                node = soup.select_one("script#gvb-config")
                self.assertEqual(node.get("type"), "application/json")
                self.assertNotIn("<", node.string, "no raw < in the JSON")
                cfg = json.loads(node.string)
                self.assertEqual(cfg["lang"], lang)
                self.assertTrue(cfg["base"].startswith("/") and cfg["base"].endswith("/"))
                self.assertEqual(cfg["json"], cfg["base"] + "about/booth.json")
                self.assertEqual(cfg["pages"], [cfg["base"] + "about/", cfg["base"] + "es/about/"])
                self.assertTrue(cfg["site"]["url"].startswith("https://"))
                self.assertTrue(cfg["site"]["url_es"].endswith("/es/"))
                self.assertTrue(cfg["site"]["committee_en"] and cfg["site"]["committee_es"])
                for k in keys:
                    if k.startswith("booth.screen."):
                        self.assertEqual(cfg["screen"]["en"][k], self.s[k]["en"])
                        self.assertEqual(cfg["screen"]["es"][k], self.s[k]["es"])
                    else:
                        self.assertEqual(cfg["t"][k], self.s[k][lang], k)
                self.assertEqual(cfg["screen"]["en"]["booth.screen.true"], "True")
                self.assertEqual(cfg["screen"]["es"]["booth.screen.true"], "Verdadero")

    def test_the_scripts_in_order(self):
        for lang, soup in self.soup.items():
            with self.subTest(lang=lang):
                srcs = [re.sub(r"\?.*$", "", s["src"]) for s in soup.select("script[src]")]
                names = [s.rsplit("/", 1)[-1] for s in srcs]
                self.assertLess(names.index("app.js"), names.index("booth-core.js"))
                self.assertLess(names.index("booth-core.js"), names.index("booth.js"))
                for s in soup.select('script[src*="booth"]'):
                    self.assertTrue(s.has_attr("defer"))

    @unittest.skipUnless(SHOW_PAGE.exists(), "the show's page (src/pages/booth-json.11ty.js) is not part of this build yet")
    def test_the_show_file(self):
        f = SITE / "about" / "booth.json"
        self.assertTrue(f.exists())
        doc = json.loads(read(f))
        self.assertEqual(doc.get("app"), "gv-booth")
        self.assertIsInstance(doc.get("items"), list)
        self.assertIsInstance(doc.get("qr"), dict)


if __name__ == "__main__":
    unittest.main()
