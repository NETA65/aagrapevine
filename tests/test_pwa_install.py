"""Install the site as an app (/app/, src/pages/app.njk; src/assets/js/install-core.js; the install parts of
src/assets/js/pwa.js) — the checks that need no browser. (The browser checks — the notice on an Android
Chrome with the real prompt, the iPhone / Samsung / Firefox / in-app user agents, the installed app,
keyboard and focus, 320–1280 px at 150 % text / relaxed spacing / high contrast, axe — are QA scripts.)

  * Strings   — every pwa.app.* key in English AND Spanish, used by the page and none left over; the
                length budgets; the platforms' own words as their help pages print them today (EN and
                Latin-American ES — re-check them every September and after big Chrome releases); menus
                named in words, never ⋮ ≡ •••; no "PDF", no words about how the site is kept up to date;
                the {app} and {a} {b} {c} placeholders in both languages; each key in one i18n file only.
  * Page      — /app/ + /es/app/ (front matter, in the sitemap and the search), the seven guides in
                order, the data-attribute contract with pwa.js, Safari's step-1 versions, the official
                help links and the magazines' apps from config/site.yml, the Android shortcuts named as
                in the manifest, "Install as an app" the first of the site's own links in the footer's
                "Stay updated" (after the two magazine sites), the local safari-menu icon.
  * Manifest  — both manifests name each other as related_applications (getInstalledRelatedApps),
                prefer_related_applications stays false, id / scope / start_url / display unchanged
                (Node.js, as the build renders them).
  * Detect    — install-core.js detect() on real user agents (iPhone Safari 27 / 26 / 18, iPad, an
                iPhone asking for desktop sites, Chrome / Edge / Firefox on iPhone, Android Chrome /
                Samsung / Firefox / Edge / Opera / Brave, the in-app browsers of Facebook, Instagram,
                Messenger, WhatsApp, TikTok … and plain web views, computers) → guide, Safari variant,
                inApp + app name, canInstall; every guide it can name is on the page.
  * Offer     — offer() truth table (views, the one-tap prompt, time on the page, a first touch, quiet
                times, "Not now" twice, 4 showings, opened as the app, known installed, in-app, busy,
                pages, offline, computers), damaged records, the record helpers' arithmetic and RULES.
  * Wiring    — base.njk loads install-core.js right before pwa.js; the worker keeps it as optional;
                pwa.js keeps the browser's prompt for its own buttons, catches a refused prompt, uses
                localStorage "gvlv-app", leaves automated browsers alone, asks getInstalledRelatedApps,
                has the "install" toast with Not now / Show me how; pwa.css; the footer / phone-menu
                links hidden in the installed app; the offline page's link without JavaScript.

    python -m unittest tests.test_pwa_install -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DAY = 864e5
GUIDES = ["iphone", "iphone-other", "android", "samsung", "android-other", "in-app", "computer"]


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def pwa_strings() -> dict:
    return json.loads(read("src", "_i18n", "pwa.json"))


def app_keys() -> dict:
    return {k: v for k, v in pwa_strings().items() if k.startswith("pwa.app.")}


def strip_js_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\"'\\])//.*$", r"\1", src)


# Loads install-core.js into a fresh vm context: G = GVInstall.
LOAD = r"""
import vm from "node:vm";
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync("src/assets/js/install-core.js", "utf8"), ctx, { filename: "install-core.js" });
const G = ctx.GVInstall;
const plain = (v) => JSON.parse(JSON.stringify(v));
"""


def core(case: unittest.TestCase, js: str, data=None):
    return run_js(case, LOAD + js, data=data, needs_modules=False)


class Strings(unittest.TestCase):
    PINNED = {  # the platforms' own words, as Apple / Google / Mozilla print them today (EN, then es-MX / es-419)
        "pwa.app.ios_1_27": ("Page Menu", "Menú de página"),
        "pwa.app.ios_2": ("Add to Home Screen", "Agregar a Inicio"),
        "pwa.app.ios_3": ("Open as Web App", "Abrir como app web"),
        "pwa.app.android_2": ("Install and create shortcut", "Instalar y crear acceso directo"),
        "pwa.app.android_3": ("Create shortcut", "Crear acceso directo"),
        "pwa.app.other_firefox": ("Add app to Home screen", "Agregar app a la pantalla de inicio"),
    }

    def test_every_key_in_both_languages(self):
        keys = app_keys()
        self.assertEqual(len(keys), 79)
        for key, v in keys.items():
            with self.subTest(key=key):
                self.assertTrue((v.get("en") or "").strip())
                self.assertTrue((v.get("es") or "").strip())
                self.assertEqual(set(v), {"en", "es"})

    def test_the_page_uses_every_key_and_no_other(self):
        page = read("src", "pages", "app.njk")
        used = set(re.findall(r"""["'](pwa\.app\.[a-z0-9_]+)["']""", page))
        used |= set(re.findall(r"(?m)^(?:titleKey|descKey): (pwa\.app\.[a-z0-9_]+)$", page))
        keys = set(app_keys())
        self.assertEqual(used - keys, set(), "keys the page uses that pwa.json lacks")
        self.assertEqual(keys - used, set(), "pwa.app.* keys nothing uses")

    def test_length_budgets(self):
        s = pwa_strings()
        common = json.loads(read("src", "_i18n", "common.json"))
        budgets = {"pwa.app.sub": (110, 135), "pwa.app.eyebrow": (32, 38),
                   **{k: (24, 28) for k in ("pwa.app.cta_steps", "pwa.app.cta_install", "pwa.app.cta_send", "pwa.app.copy_link")}}
        for key, (en, es) in budgets.items():
            with self.subTest(key=key):
                self.assertLessEqual(len(s[key]["en"]), en)
                self.assertLessEqual(len(s[key]["es"]), es)
        self.assertLessEqual(len(common["nav.app"]["en"]), 24)
        self.assertLessEqual(len(common["nav.app"]["es"]), 28)

    def test_the_platforms_own_words(self):
        s = pwa_strings()
        for key, (en, es) in self.PINNED.items():
            with self.subTest(key=key):
                self.assertIn(en, s[key]["en"])
                self.assertIn(es, s[key]["es"])
        self.assertIn("View More", s["pwa.app.ios_2"]["en"])
        self.assertIn("Ver más", s["pwa.app.ios_2"]["es"])
        # Safari 26: More (three dots); Chrome on Android: More (three dots); Samsung: three lines
        self.assertIn("**More** button (three dots)", s["pwa.app.ios_1_26"]["en"])
        self.assertIn("**Más** (tres puntos)", s["pwa.app.ios_1_26"]["es"])
        # the generic step names both Safari buttons and the Share button
        for w in ("Page Menu", "More", "Share"):
            self.assertIn(w, s["pwa.app.ios_1"]["en"])
        for w in ("Menú de página", "Más", "Compartir"):
            self.assertIn(w, s["pwa.app.ios_1"]["es"])

    def test_menus_named_in_words_and_house_wording(self):
        glyphs = re.compile("[\u22ee\u22ef\u2261\u2022\u2630\ufe19]")         # ⋮ ⋯ ≡ • ☰ ︙
        banned = re.compile(r"\bPDF\b|crawl|automatic|automátic|\bbots?\b|\bjobs?\b|robot", re.I)
        for key, v in app_keys().items():
            for lang in ("en", "es"):
                with self.subTest(key=key, lang=lang):
                    self.assertIsNone(glyphs.search(v[lang]), v[lang])
                    self.assertIsNone(banned.search(v[lang]), v[lang])
                    self.assertEqual(v[lang].count("**") % 2, 0, "unbalanced **bold**")

    def test_spanish_rayas_closed(self):
        # a clause opened with a raya is closed with one ("… —una aclaración— …"), even before a period; the
        # " — " between a title's parts ("iPhone o iPad — Safari") is a separator, not a raya
        for key, v in app_keys().items():
            with self.subTest(key=key):
                self.assertEqual(v["es"].replace(" — ", " ").count("—") % 2, 0, v["es"])

    def test_whatsapp_tip_says_both_cases(self):
        # WhatsApp opens links in the phone's browser OR in its own window (WAiOS / WA4A): the tip says both,
        # and /app/ hides it inside WhatsApp's own window (Page.test_data_attribute_contract)
        tip = pwa_strings()["pwa.app.inapp_whatsapp"]
        self.assertIn("browser", tip["en"])
        self.assertIn("its own window", tip["en"])
        self.assertIn("navegador", tip["es"])
        self.assertIn("su propia ventana", tip["es"])

    def test_placeholders(self):
        s = pwa_strings()
        for lang in ("en", "es"):
            self.assertIn("{app}", s["pwa.app.inapp_now"][lang])
            for p in ("{a}", "{b}", "{c}"):
                self.assertIn(p, s["pwa.app.more_shortcuts"][lang])
        for key, v in app_keys().items():
            with self.subTest(key=key):
                self.assertEqual(sorted(re.findall(r"\{\w+\}", v["en"])), sorted(re.findall(r"\{\w+\}", v["es"])))

    def test_each_key_lives_in_one_file(self):
        # eleventy.config.js merges every src/_i18n/*.json: a key in two files would silently override
        mine = set(app_keys()) | {"nav.app", "nav.offline", "search.page_desc.app", "search.kw.app", "access.f_offline_cta"}
        seen = {}
        for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
            for k in json.loads(f.read_text(encoding="utf-8")):
                if k in mine:
                    seen.setdefault(k, []).append(f.name)
        for k in sorted(mine):
            with self.subTest(key=k):
                self.assertEqual(len(seen.get(k, [])), 1, seen.get(k))

    def test_labels_and_search_words(self):
        common = json.loads(read("src", "_i18n", "common.json"))
        access = json.loads(read("src", "_i18n", "access.json"))
        self.assertEqual(common["nav.app"], {"en": "Install as an app", "es": "Instalar como app"})
        self.assertEqual(common["nav.offline"], {"en": "Saved pages", "es": "Páginas guardadas"})
        self.assertEqual(access["access.f_offline_cta"], {"en": "Saved pages", "es": "Páginas guardadas"})
        for k in ("search.page_desc.app", "search.kw.app"):
            self.assertTrue(access[k]["en"] and access[k]["es"], k)
        self.assertIn("home screen", access["search.kw.app"]["en"])
        self.assertIn("pantalla de inicio", access["search.kw.app"]["es"])
        # installing has its own page now: /offline/'s search words are about saved pages only
        self.assertNotIn("install", access["search.kw.offline"]["en"])
        self.assertNotIn("instalar", access["search.kw.offline"]["es"])
        self.assertNotIn("app", access["search.page_desc.offline"]["en"])


class Page(unittest.TestCase):
    def setUp(self):
        self.page = read("src", "pages", "app.njk")

    def test_front_matter(self):
        fm = re.match(r"---\n(.*?)\n---\n", self.page, re.S).group(1)
        self.assertIn("pagination: { data: languages, size: 1, alias: lang }", fm)
        self.assertIn("""permalink: "{{ '/' if lang == 'en' else '/es/' }}app/index.html\"""", fm)
        self.assertRegex(fm, r"(?m)^layout: layouts/base\.njk$")
        self.assertRegex(fm, r"(?m)^pageKey: app$")
        self.assertRegex(fm, r"(?m)^titleKey: pwa\.app\.title$")
        self.assertRegex(fm, r"(?m)^descKey: pwa\.app\.meta_desc$")
        # a page to share and to find: in the sitemap, the collections and the search
        self.assertNotIn("sitemap: false", fm)
        self.assertNotIn("eleventyExcludeFromCollections", fm)
        self.assertNotIn('pageKey == "app"', read("src", "_includes", "layouts", "base.njk"))   # never noindex

    def test_seven_guides_in_order(self):
        block = self.page[self.page.index("{%- set guides = ["):self.page.index("{%- set why = [")]
        self.assertEqual(re.findall(r'\{ id: "([a-z-]+)"', block), GUIDES)
        self.assertIn('<details class="pwa-guide-os card" id="{{ g.id }}" data-pwa-guide="{{ g.id }}">', self.page)
        for g in GUIDES:
            self.assertIn(g, self.page.split("-#}", 1)[0], f"the header comment lists {g}")

    def test_data_attribute_contract(self):
        p = self.page
        self.assertRegex(p, r'<section id="steps" class="section container-page" aria-labelledby="app-steps-h" data-pwa-app>')
        self.assertRegex(p, r'<span class="pwa-guide-title min-w-0 flex-1">\{\{ g\.h \| t\(lang\) \}\} <span class="badge-vine pwa-guide-here" data-pwa-here hidden>')
        self.assertRegex(p, r'<a class="btn-light" href="#steps" data-pwa-steps-link>')
        self.assertRegex(p, r'<button type="button" class="btn-light" data-pwa-act="install" data-pwa-install-hero hidden>')
        self.assertRegex(p, r'data-pwa-inapp data-t="\{\{ \'pwa\.app\.inapp_now\' \| t\(lang\) \}\}" data-t-other="\{\{ \'pwa\.app\.inapp_other\' \| t\(lang\) \}\}" hidden>')
        self.assertIn("data-pwa-inapp-text", p)
        self.assertRegex(p, r'class="pwa-guide-note is-ok" data-pwa-using hidden>')
        self.assertRegex(p, r'class="pwa-guide-note is-ok" data-pwa-known hidden>')
        # Safari's step 1: "any" shown, 27 / 26 / share rendered hidden; 27 and 26 carry the Share tip
        self.assertIn('<div data-pwa-v="{{ x[0] }}"{% if x[0] != "any" %} hidden{% endif %}>', p)
        v = re.search(r"\{ v: \[(.*?)\] \}", p, re.S).group(1)
        self.assertEqual(re.findall(r'\["(any|27|26|share)"', v), ["any", "27", "26", "share"])
        self.assertIn('["27", "safari-menu", "pwa.app.ios_1_27", "pwa.app.ios_share_tip"]', v)
        self.assertIn('["26", "circle-ellipsis", "pwa.app.ios_1_26", "pwa.app.ios_share_tip"]', v)
        # the Copy / Send buttons carry this page's full address (JavaScript only; the address as text without it)
        self.assertIn("{%- set appUrl = page.url | siteUrl(site) -%}", p)
        self.assertRegex(p, r'data-js-only data-copy="\{\{ appUrl \}\}"')
        self.assertRegex(p, r'data-nojs-only>\{\{ appUrl \}\}<')
        self.assertRegex(p, r'class="btn-on-dark" data-js-only data-share="\{\{ appUrl \}\}"')
        # a tip hidden inside one app's own browser (the WhatsApp tip inside WhatsApp: the note says it already),
        # by the app's name as install-core.js gives it
        self.assertIn('tips: [{ k: "pwa.app.inapp_whatsapp", notIn: "WhatsApp" }]', p)
        self.assertIn('{% if tip.notIn %} data-pwa-not-in="{{ tip.notIn }}"{% endif %}', p)
        self.assertIn("{{ (tip.k or tip) | t(lang) | mdInline | safe }}", p)
        self.assertIn('["WhatsApp", ', read("src", "assets", "js", "install-core.js"))
        self.assertIn('querySelectorAll("[data-pwa-not-in]")', read("src", "assets", "js", "pwa.js"))
        # the step numbers are read once (the circle is aria-hidden, the number is screen-reader text)
        self.assertIn('<span class="step-num" aria-hidden="true">{{ n }}</span>', p)
        self.assertIn('<span class="sr-only">{{ n }}. </span>', p)
        self.assertIn('<span class="pwa-guide-key" aria-hidden="true">', p)

    def test_links_from_site_settings(self):
        p = self.page
        links = yaml.safe_load(read("config", "site.yml"))["links"]
        for k in ("app_help_iphone", "app_help_iphone_es", "app_help_android", "app_help_android_es"):
            with self.subTest(link=k):
                self.assertIn("ln." + k, p)
                self.assertRegex(links[k], r"^https://support\.(apple|google)\.com/")
        self.assertIn("/es-mx/", links["app_help_iphone_es"])
        self.assertIn("hl=es-419", links["app_help_android_es"])
        self.assertIn("[[ln.gv_apps, \"media.short_gv_app\", \"en\"], [ln.lv_apps, \"media.short_lv_app\", \"es\"]]", p)
        self.assertIn('magApps | reverse if lang == "es"', p)                      # La Viña first on /es/app/

    def test_shortcuts_named_as_in_the_manifest(self):
        manifest = read("src", "pages", "manifest.11ty.js")
        block = manifest[manifest.index("shortcuts: ["):manifest.index("].map(")]
        keys = re.findall(r't\("(nav\.[a-z_]+)"\)', block)
        m = re.search(r'"pwa\.app\.more_shortcuts" \| t\(lang, \{ a: "(nav\.\w+)" \| t\(lang\), b: "(nav\.\w+)" \| t\(lang\), c: "(nav\.\w+)" \| t\(lang\) \}\)', self.page)
        self.assertIsNotNone(m)
        self.assertEqual(list(m.groups()), keys)

    def test_footer_entry_and_icon(self):
        nav = read("src", "_data", "nav.js")
        self.assertIn('{ key: "nav.app", url: "/app/", page: "app", icon: "smartphone", group: "stay" }', nav)
        self.assertEqual(re.findall(r'key: "(nav\.\w+)"[^}]*group: "stay"', nav)[0], "nav.app")
        svg = read("src", "_includes", "icons", "safari-menu.svg")
        for d in ("M4 6h16", "M4 12h16", "M4 18h10"):
            self.assertIn(f'<path d="{d}"/>', svg)
        self.assertIn('viewBox="0 0 24 24"', svg)
        self.assertIn('stroke="currentColor"', svg)

    def test_accessibility_and_offline_pages_link_here(self):
        acc = read("src", "pages", "accessibility.njk")
        card = acc[acc.index("Saved pages and the app (feature 14)"):acc.index("</li>", acc.index("Saved pages and the app (feature 14)"))]
        self.assertIn("{{ '/offline/' | lurl(lang) }}", card)
        self.assertIn("{{ '/app/' | lurl(lang) }}", card)
        self.assertNotIn("after:absolute", card)                                  # two real links, no whole-card overlay
        off = read("src", "pages", "offline.njk")
        self.assertIn("data-pwa-install", off)
        self.assertIn("""<a class="link tap-link mt-auto" data-nojs-only href="{{ '/app/' | lurl(lang) }}">{{ 'nav.app' | t(lang) }}</a>""", off)


class Manifest(unittest.TestCase):
    SCRIPT = r"""
      const M = await imp("src/pages/manifest.11ty.js");
      const t = (k, l) => filters.t(k, l);
      out(["en", "es"].map((lang) => JSON.parse(M.render.call({ t }, { lang }))));
    """

    def test_related_applications(self):
        for prefix, base in (("/AAGrapevine/", "/AAGrapevine/"), ("/", "/")):
            with self.subTest(prefix=prefix):
                en, es = run_js(self, self.SCRIPT, env={"PATH_PREFIX": prefix})
                want = [{"platform": "webapp", "url": base + "manifest.webmanifest"},
                        {"platform": "webapp", "url": base + "es/manifest.webmanifest"}]
                for m in (en, es):
                    self.assertEqual(m["related_applications"], want)
                    self.assertIs(m["prefer_related_applications"], False)
                    self.assertEqual((m["id"], m["scope"], m["display"]), (base, base, "standalone"))
                self.assertEqual((en["start_url"], es["start_url"]), (base, base + "es/"))
                self.assertEqual([s["url"] for s in en["shortcuts"]], [base + p for p in ("meetings/", "monthly/", "orientation/")])
                self.assertNotIn("orientation", en)                            # no orientation lock
                self.assertEqual(en["short_name"], "GV/LV 65")


# name, user agent, env, guide, variant, app name ("" = none) or "cannot" (canInstall false)
UAS = [
    ["iOS27 Safari", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Mobile/15E148 Safari/604.1", {}, "iphone", "27", ""],
    ["iOS26.4 Safari", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Mobile/15E148 Safari/604.1", {}, "iphone", "26", ""],
    ["iOS18 Safari", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1", {}, "iphone", "share", ""],
    ["iPhone iOS 16 Safari", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_10 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1", {}, "iphone", "share", ""],
    ["iPadOS desktop UA", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Safari/605.1.15", {"touch": 5}, "iphone", "share", ""],
    ["iPad mini UA", "Mozilla/5.0 (iPad; CPU OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1", {}, "iphone", "share", ""],
    ["iPhone desktop-site mode", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Safari/605.1.15", {"touch": 5, "small": True}, "iphone", "27", ""],
    ["iPad Firefox desktop UA", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0", {"touch": 5}, "iphone-other", "", ""],
    ["iPad Chrome desktop UA", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {"touch": 5}, "iphone-other", "", ""],
    ["Mac Safari", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.0 Safari/605.1.15", {"touch": 0}, "computer", "", ""],
    ["CriOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/150.0.7390.0 Mobile/15E148 Safari/604.1", {}, "iphone-other", "", ""],
    ["CriOS old iOS 16.3", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/110.0.5481.114 Mobile/15E148 Safari/604.1", {}, "iphone-other", "", "cannot"],
    ["FxiOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/130.1  Mobile/15E148 Safari/605.1.15", {}, "iphone-other", "", ""],
    ["EdgiOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/128.0.2739.82 Version/18.0 Mobile/15E148 Safari/604.1", {}, "iphone-other", "", ""],
    ["GSA iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) GSA/334.0.674067880 Mobile/15E148 Safari/604.1", {}, "in-app", "", "Google"],
    ["Instagram iOS new", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/22F76 Instagram 393.1.0.36.70 (iPhone15,3; iOS 18_5; en_US; en; scale=3.00; 1290x2796; IABMV/1; 776538208) Safari/604.1)", {}, "in-app", "", "Instagram"],
    ["FB iOS MetaIAB", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/22G100 Safari/604.1 MetaIAB Facebook", {}, "in-app", "", "Facebook"],
    ["FB iOS FBAN", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/22B83 [FBAN/FBIOS;FBAV/488.0.0.68.101;FBBV/658219612;FBDV/iPhone12,8;FBMD/iPhone;FBSN/iOS;FBSV/18.1;FBSS/2;FBID/phone;FBLC/en_US;FBOP/5;FBRV/0;IABMV/1]", {}, "in-app", "", "Facebook"],
    ["Messenger iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Mobile/14D27 {useragents: [FBAN/MessengerForiOS;FBAV/117.0.0.36.70;FBBV/57539258]", {}, "in-app", "", "Messenger"],
    ["WhatsApp iOS IAB", "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Mobile/15E148 Safari/604.1 [WAiOS/2.25.31]", {}, "in-app", "", "WhatsApp"],
    ["TikTok iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/604.1 musical_ly_41.9.0", {}, "in-app", "", "TikTok"],
    ["Snapchat iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Snapchat/12.72.0.39 (like Safari/8617.2.4.10.8, panda)", {}, "in-app", "", "Snapchat"],
    ["LinkedIn iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 {useragents: [LinkedInApp]/9.30.1753", {}, "in-app", "", "LinkedIn"],
    ["X iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/602.3.12 (KHTML, like Gecko) Mobile/14D27 Twitter for iPhone", {}, "in-app", "", "X"],
    ["Pinterest iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [Pinterest/iOS]", {}, "in-app", "", "Pinterest"],
    ["LINE iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari Line/14.10.0", {}, "in-app", "", "LINE"],
    ["Generic iOS WKWebView", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", {}, "in-app", "", ""],
    ["Telegram iOS", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1", {"telegram": True}, "in-app", "", "Telegram"],
    ["Android Chrome", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36", {}, "android", "", ""],
    ["Android tablet Chrome", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {}, "android", "", ""],
    ["Android desktop-site Chrome", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {"touch": 5, "small": True}, "android", "", ""],
    # the bigger Android tablets ask for desktop sites by default: "X11; Linux x86_64" + a touch screen, any size
    ["Android tablet desktop-mode Chrome", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {"touch": 10, "small": False}, "android", "", ""],
    ["Android tablet desktop-mode Samsung", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/28.0 Chrome/130.0.0.0 Safari/537.36", {"touch": 10}, "samsung", "", ""],
    ["Android tablet desktop-mode Firefox", "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0", {"touch": 10}, "android-other", "", ""],
    ["Android Samsung", "Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-S921U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/28.0 Chrome/130.0.0.0 Mobile Safari/537.36", {}, "samsung", "", ""],
    ["Android Firefox", "Mozilla/5.0 (Android 14; Mobile; rv:143.0) Gecko/143.0 Firefox/143.0", {}, "android-other", "", ""],
    ["Android Edge", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 EdgA/140.0.0.0", {}, "android-other", "", ""],
    ["Android Opera", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36 OPR/90.0.0.0", {}, "android-other", "", ""],
    ["Android Brave", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36", {"brave": True}, "android-other", "", ""],
    ["Android FB wv", "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A.240905.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.83 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/488.0.0.62.79;IABMV/1;]", {}, "in-app", "", "Facebook"],
    ["Android Messenger wv", "Mozilla/5.0 (Linux; Android 6.0.1; D6653 Build/23.5.A.0.575; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/58.0.3029.83 Mobile Safari/537.36 {useragents: [FB_IAB/MESSENGER;FBAV/118.0.0.19.82;]", {}, "in-app", "", "Messenger"],
    # today's Messenger for Android (com.facebook.orca): FB_IAB/Orca-Android — not "Facebook"
    ["Android Messenger Orca", "Mozilla/5.0 (Linux; Android 13; SM-A536U Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36 [FB_IAB/Orca-Android;FBAV/439.0.0.29.119;]", {}, "in-app", "", "Messenger"],
    ["Android Instagram", "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A.240905.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 355.1.0.44.103 Android (34/14; 420dpi; 1080x2205; Google/google; Pixel 8; shiba; shiba; en_US; 658190016)", {}, "in-app", "", "Instagram"],
    ["Android Threads", "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A.240905.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.58 Mobile Safari/537.36 Barcelona 355.0.0.39.109 Android (34/14; 420dpi)", {}, "in-app", "", "Threads"],
    ["Android WhatsApp IAB", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.124 Mobile Safari/537.36 [WA4A/2.25.32.75;]", {}, "in-app", "", "WhatsApp"],
    ["Android TikTok", "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UQ1A.240105.004; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/121.0.6167.143 Mobile Safari/537.36 musical_ly_2023303040 JsSdk/1.0 NetType/WIFI BytedanceWebview/d8a21c6", {}, "in-app", "", "TikTok"],
    ["Android WeChat", "Mozilla/5.0 (Linux; Android 13; SM-A536U Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160065 MMWEBSDK/20231202 MicroMessenger/8.0.47.2560(0x28002F30) WeChat/arm64 Weixin NetType/WIFI Language/en ABI/arm64", {}, "in-app", "", "WeChat"],
    ["Android generic wv", "Mozilla/5.0 (Linux; Android 13; SM-A536U Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.0.0 Mobile Safari/537.36", {}, "in-app", "", ""],
    ["Android GSA", "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 GSA/15.30.0.28.arm64", {}, "in-app", "", "Google"],
    ["Android Reddit wv", "Mozilla/5.0 (Linux; Android 15; 23129RN51X Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/148.0.7778.215 Mobile Safari/537.36 Reddit/Version 2026.23.0/Build 2623040/Android 15", {}, "in-app", "", "Reddit"],
    ["Win Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {}, "computer", "", ""],
    ["Win Chrome, Telegram flag", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {"telegram": True}, "computer", "", ""],
    ["Win Edge", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0", {}, "computer", "", ""],
    ["Win Firefox", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0", {}, "computer", "", "cannot"],
    ["Linux laptop Chrome", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {}, "computer", "", ""],
    ["ChromeOS", "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", {"touch": 10, "small": True}, "computer", "", ""],
    ["Nothing at all", "", {}, "computer", "", "cannot"],
]


class Detect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def results(self):
        if Detect.r is None:
            Detect.r = core(self, "out(input.map(([n, ua, env]) => plain(G.detect(ua, env))));", data=UAS)
        return Detect.r

    def test_real_user_agents(self):
        self.assertGreaterEqual(len(UAS), 50)
        for (name, _ua, _env, guide, variant, extra), r in zip(UAS, self.results()):
            with self.subTest(name=name):
                self.assertEqual(r["guide"], guide, r)
                self.assertEqual(r["variant"], variant, r)
                self.assertEqual(set(r), {"os", "phone", "browser", "version", "inApp", "app", "guide", "variant", "canInstall"})
                if guide == "in-app":
                    self.assertTrue(r["inApp"])
                    self.assertFalse(r["canInstall"])
                    self.assertEqual(r["app"], extra)
                    self.assertTrue(r["phone"])
                else:
                    self.assertFalse(r["inApp"])
                    self.assertEqual(r["canInstall"], extra != "cannot", r)
                self.assertEqual(r["phone"], guide != "computer", r)

    def test_details(self):
        by = {u[0]: r for u, r in zip(UAS, self.results())}
        self.assertEqual((by["iOS27 Safari"]["browser"], by["iOS27 Safari"]["version"], by["iOS27 Safari"]["os"]), ("safari", 27, "ios"))
        self.assertEqual(by["iPadOS desktop UA"]["os"], "ipados")
        self.assertEqual(by["iPhone desktop-site mode"]["os"], "ios")
        self.assertEqual(by["CriOS"]["browser"], "chrome")
        self.assertEqual(by["FxiOS"]["browser"], "firefox")
        self.assertEqual(by["EdgiOS"]["browser"], "edge")
        self.assertEqual(by["iPad Chrome desktop UA"]["browser"], "chrome")
        self.assertEqual((by["Android Chrome"]["browser"], by["Android Chrome"]["version"]), ("chrome", 150))
        self.assertEqual(by["Android Samsung"]["browser"], "samsung")
        self.assertEqual(by["Android desktop-site Chrome"]["os"], "android")
        self.assertEqual((by["Android tablet desktop-mode Chrome"]["os"], by["Android tablet desktop-mode Chrome"]["browser"]), ("android", "chrome"))
        self.assertEqual(by["Android tablet desktop-mode Samsung"]["browser"], "samsung")
        self.assertEqual((by["Linux laptop Chrome"]["os"], by["Linux laptop Chrome"]["phone"]), ("linux", False))   # no touch: a computer
        self.assertEqual(by["Mac Safari"]["browser"], "safari")
        self.assertEqual(by["Win Edge"]["browser"], "edge")

    def test_every_guide_it_names_is_on_the_page(self):
        guides = {r["guide"] for r in self.results()}
        self.assertEqual(guides, set(GUIDES))
        self.assertLessEqual({r["variant"] for r in self.results()}, {"", "27", "26", "share"})

    def test_bad_input_never_throws(self):
        r = core(self, """out([null, undefined, 42, {}, [], "x"].map((ua) => plain(G.detect(ua, null))).concat([plain(G.detect("iPhone", "junk"))]));""")
        for d in r[:-1]:
            self.assertEqual((d["guide"], d["phone"], d["inApp"]), ("computer", False, False))
        self.assertEqual(r[-1]["guide"], "in-app")                           # an "iPhone" with no Safari/ is a web view


NOW = 1790640000000   # 2026-09-29 00:00 UTC
BASE = {"now": NOW, "phone": True, "canInstall": True, "inApp": False, "installed": False, "knownInstalled": False,
        "prompt": False, "online": True, "dwell": 25000, "touched": True, "busy": False, "page": ""}
# [record, ctx changes, expected, why]
OFFERS = [
    [{"views": 3}, {}, True, "3rd page view (the steps)"],
    [{"views": 2}, {}, False, "2nd page view (the steps)"],
    [{"views": 2}, {"prompt": True}, True, "2nd page view with the browser's one-tap prompt"],
    [{"views": 1}, {"prompt": True}, False, "1st page view, even with the prompt"],
    [{"views": 9}, {"dwell": 19999}, False, "under 20 s on the page"],
    [{"views": 9}, {"dwell": 20000}, True, "20 s on the page"],
    [{"views": 9}, {"touched": False}, False, "no tap, key or scroll yet"],
    [{"views": 9, "quiet": NOW + 1}, {}, False, "quiet time"],
    [{"views": 9, "quiet": NOW - 1}, {}, True, "quiet time over"],
    [{"views": 9, "no": 2}, {}, False, "said Not now twice"],
    [{"views": 9, "no": 1}, {}, True, "said Not now once, quiet over"],
    [{"views": 9, "shown": 4}, {}, False, "shown 4 times"],
    [{"views": 9, "shown": 3}, {}, True, "shown 3 times"],
    [{"views": 9, "app": NOW - 10 * DAY}, {}, False, "opened as the app 10 days ago"],
    [{"views": 9, "app": NOW - 100 * DAY}, {}, True, "opened as the app 100 days ago"],
    [{"views": 9}, {"knownInstalled": True}, False, "getInstalledRelatedApps says installed"],
    [{"views": 9}, {"inApp": True}, False, "inside another app"],
    [{"views": 9}, {"canInstall": False}, False, "a browser that can't install (iOS 16.3 Chrome)"],
    [{"views": 9}, {"busy": True}, False, "a banner, the player, a panel or a field is in use"],
    [{"views": 9}, {"page": "app"}, False, "on /app/"],
    [{"views": 9}, {"page": "offline"}, False, "on the offline page"],
    [{"views": 9}, {"page": "noindex"}, False, "on a noindex page"],
    [{"views": 9}, {"phone": False}, False, "a computer"],
    [{"views": 9}, {"online": False}, False, "offline"],
    [{"views": 9}, {"installed": True}, False, "running as the app"],
    [{"views": 9, "done": NOW - 1}, {}, False, "installed from this browser"],
    [{"views": 9, "done": 1}, {}, False, "installed, time unknown"],
    [{"views": 9, "quiet": NOW + 400 * DAY}, {}, True, "a damaged quiet time far ahead counts as unset"],
    [{"views": 9, "quiet": NOW + 30 * DAY}, {}, False, "a real 30-day quiet time"],
    [{"views": 9, "app": NOW + 400 * DAY}, {}, True, "a damaged app time far ahead counts as unset"],
    [None, {}, False, "no record"],
    ["garbage", {}, False, "not a record"],
    [{"views": "9"}, {}, True, "numbers stored as text"],
    [{"views": 9}, None, False, "no context"],
]


class Offer(unittest.TestCase):
    def test_truth_table(self):
        got = core(self, "out(input.cases.map(([rec, c]) => G.offer(rec, c === null ? undefined : Object.assign({}, input.base, c))));",
                   data={"cases": [[o[0], o[1]] for o in OFFERS], "base": BASE})
        self.assertEqual(len(got), len(OFFERS))
        for (rec, ctx, want, why), g in zip(OFFERS, got):
            with self.subTest(why=why):
                self.assertIs(g, want)

    def test_rules(self):
        r = core(self, "out(plain(G.RULES));")
        self.assertEqual(r, {"views": 3, "viewsWithPrompt": 2, "dwell": 20000, "quietAfterShow": 7 * DAY, "quietAfterNo": 30 * DAY,
                             "maxShows": 4, "maxNo": 2, "installedFor": 90 * DAY})

    def test_clean_never_throws(self):
        r = core(self, r"""
          const bad = [null, undefined, "x", 42, [], [1, 2], { views: -3, shown: "2", no: NaN, quiet: 1e20, app: Infinity, done: "yes" },
                       { get views() { throw new Error("boom"); } }, { views: Symbol("s") }, { views: { valueOf() { throw new Error("no"); } } },
                       { views: 2.9, shown: "1.5" }];
          out(bad.map((b) => plain(G.clean(b))));
        """)
        empty = {"v": 1, "views": 0, "shown": 0, "no": 0, "quiet": 0, "app": 0, "done": 0}
        for c in r[:6]:
            self.assertEqual(c, empty)
        self.assertEqual(r[6], {"v": 1, "views": 0, "shown": 2, "no": 0, "quiet": 1e20, "app": 0, "done": 0})
        self.assertEqual(r[7], empty)
        self.assertEqual(r[8]["views"], 0)
        self.assertEqual(r[9]["views"], 0)
        self.assertEqual((r[10]["views"], r[10]["shown"]), (2, 1))

    def test_helpers(self):
        r = core(self, r"""
          const now = input.now;
          let a = G.view(G.view(null));
          const viewed = plain(a);
          a = G.shown(a, now);
          const shown = plain(a);
          a = G.later(a, now + 1000);
          const later = plain(a);
          const later2 = plain(G.later(G.later(null, now), now));
          const guided = plain(G.guided({ quiet: now + 40 * 864e5 * 10 }, now));          // a damaged quiet time is replaced
          const keep = plain(G.guided({ quiet: now + 20 * 864e5 }, now));                  // a longer real one is kept
          const shorter = plain(G.shown({ quiet: now + 20 * 864e5 }, now));                // never shortened
          // the browser offers one-tap install (it was removed): installed / opened-as-the-app forgotten, the rest kept
          const gone = plain(G.notInstalled({ views: 7, shown: 2, no: 1, quiet: now + 864e5, app: now - 864e5, done: now - 2 * 864e5 }));
          out({ viewed, shown, later, later2, guided, keep, shorter, gone, goneJunk: plain(G.notInstalled("junk")),
                opened: plain(G.opened({ views: 2 }, now)), done: plain(G.done({}, now)), doneNoClock: plain(G.done({})),
                untouched: plain(G.view(input.orig)), orig: input.orig });
        """, data={"now": NOW, "orig": {"views": 1}})
        self.assertEqual(r["gone"], {"v": 1, "views": 7, "shown": 2, "no": 1, "quiet": NOW + DAY, "app": 0, "done": 0})
        self.assertEqual(r["goneJunk"], {"v": 1, "views": 0, "shown": 0, "no": 0, "quiet": 0, "app": 0, "done": 0})
        self.assertEqual(r["viewed"]["views"], 2)
        self.assertEqual((r["shown"]["shown"], r["shown"]["quiet"]), (1, NOW + 7 * DAY))
        self.assertEqual((r["later"]["no"], r["later"]["quiet"]), (1, NOW + 1000 + 30 * DAY))
        self.assertEqual(r["later2"]["no"], 2)
        self.assertEqual(r["guided"]["quiet"], NOW + 30 * DAY)
        self.assertEqual(r["keep"]["quiet"], NOW + 30 * DAY)
        self.assertEqual(r["shorter"]["quiet"], NOW + 20 * DAY)
        self.assertEqual(r["opened"]["app"], NOW)
        self.assertEqual(r["done"]["done"], NOW)
        self.assertEqual(r["doneNoClock"]["done"], 1)                          # still "installed"
        self.assertEqual(r["untouched"]["views"], 2)
        self.assertEqual(r["orig"], {"views": 1})                              # the helpers never change their input

    def test_offered_again_after_an_uninstall(self):
        # installed from this browser, then removed: the browser's one-tap offer clears it, and the notice may show
        r = core(self, r"""
          const t = input.now, c = Object.assign({}, input.base, { prompt: true });
          const installed = { views: 9, done: t - 200 * 864e5 }, ranAsApp = { views: 9, app: t - 10 * 864e5 };
          out([G.offer(installed, c), G.offer(G.notInstalled(installed), c), G.offer(ranAsApp, c), G.offer(G.notInstalled(ranAsApp), c),
               G.offer(G.notInstalled({ views: 9, no: 2 }), c)]);
        """, data={"now": NOW, "base": BASE})
        self.assertEqual(r, [False, True, False, True, False])                  # (two "Not now"s still mean never)

    def test_a_whole_season(self):
        # view, view, view → offered; Not now → quiet 30 days; after that offered again; Not now → never
        r = core(self, r"""
          const D = 864e5, c = (now, x) => Object.assign({ now, phone: true, canInstall: true, online: true, dwell: 30000, touched: true }, x || {});
          let rec = null; const t = input.now; const log = [];
          for (let i = 0; i < 3; i++) { rec = G.view(rec); log.push(G.offer(rec, c(t))); }
          rec = G.shown(rec, t); rec = G.later(rec, t);
          rec = G.view(rec); log.push(G.offer(rec, c(t + 29 * D)));
          rec = G.view(rec); log.push(G.offer(rec, c(t + 31 * D)));
          rec = G.shown(rec, t + 31 * D); rec = G.later(rec, t + 31 * D);
          rec = G.view(rec); log.push(G.offer(rec, c(t + 400 * D)));
          out({ log, rec: plain(rec) });
        """, data={"now": NOW})
        self.assertEqual(r["log"], [False, False, True, False, True, False])
        self.assertEqual((r["rec"]["no"], r["rec"]["shown"]), (2, 2))

    def test_plain_es2019_script_without_the_page(self):
        src = read("src", "assets", "js", "install-core.js")
        code = strip_js_comments(src)
        for bad in ("?.", "??", "import ", "export ", "document", "localStorage", "navigator", "location", "class "):
            self.assertNotIn(bad, code, bad)
        self.assertIn('typeof window !== "undefined" ? window : globalThis', code)
        r = run_js(self, r"""
          import vm from "node:vm";
          const w = {};
          vm.runInContext(fs.readFileSync("src/assets/js/install-core.js", "utf8"), vm.createContext({ window: w }));
          out(Object.keys(w.GVInstall).sort());
        """, needs_modules=False)
        self.assertEqual(r, sorted(["RULES", "detect", "clean", "offer", "view", "shown", "later", "guided", "opened", "done", "notInstalled"]))


class Wiring(unittest.TestCase):
    def setUp(self):
        self.pwa = read("src", "assets", "js", "pwa.js")

    def test_base_layout_loads_the_core_first(self):
        base = read("src", "_includes", "layouts", "base.njk")
        core_tag = '<script src="/assets/js/install-core.js?v={{ build.version }}" defer></script>'
        pwa_tag = '<script src="/assets/js/pwa.js?v={{ build.version }}" defer></script>'
        self.assertIn(core_tag, base)
        self.assertLess(base.index('/assets/js/app.js?v='), base.index(core_tag))
        self.assertLess(base.index(core_tag), base.index(pwa_tag))
        self.assertEqual(base[base.index(core_tag) + len(core_tag):base.index(pwa_tag)].strip(), "")   # right before pwa.js

    def test_worker_keeps_it_as_optional(self):
        sw = read("src", "pages", "sw.11ty.js")
        required = re.search(r"const required = \[(.*?)\];", sw, re.S).group(1)
        shell = re.search(r"const shell = \[(.*?)\];", sw, re.S).group(1)
        self.assertNotIn("install-core", required)
        self.assertIn("a(`assets/js/install-core.js?v=${v}`)", shell)

    def test_the_prompt(self):
        p = self.pwa
        handler = p[p.index('addEventListener("beforeinstallprompt"'):]
        handler = handler[:handler.index("});")]
        self.assertIn("e.preventDefault();", handler)                          # the site's own notice offers it
        self.assertIn("state.installEvt = e;", handler)
        self.assertIn("state.known = false;", handler)                         # the browser only offers it when not installed…
        self.assertIn("GI.notInstalled(", handler)                              # …so a remembered install is forgotten
        self.assertIn("!state.known && !state.installEvt", p[p.index("function relatedApps()"):])   # …and outweighs getInstalledRelatedApps
        self.assertIn("known.hidden = state.installed || !!state.installEvt || !state.known;", p)   # /app/: never "already on this device" beside Install
        inst = p[p.index("function install(from)"):p.index("function notNow()")]
        self.assertIn("Promise.resolve(e.prompt()).catch(", inst)              # a refused prompt is caught…
        self.assertIn("state.installEvt = null;", inst)
        self.assertIn("redraw();", inst)                                        # …and the controls are redrawn on every path
        self.assertIn("location.href = guideUrl", inst)                         # no event: this device's steps
        self.assertIn('addEventListener("appinstalled"', p)

    def test_the_record_and_the_guards(self):
        p = self.pwa
        self.assertIn('APP_KEY = "gvlv-app"', p)
        for m in re.finditer(r"localStorage\.(getItem|setItem)\(APP_KEY", p):
            self.assertIn("try", p[max(0, m.start() - 40):m.start()])
        self.assertIn("!navigator.webdriver", p)
        self.assertIn("navigator.getInstalledRelatedApps()", p)
        self.assertIn('root.classList.add("pwa-standalone")', p)
        self.assertIn('window.GVInstall || null', p)
        self.assertIn("setInterval(", p)
        self.assertIn("++checks > 36", p)

    def test_the_notice(self):
        p = self.pwa
        kind = p[p.index("function toastKind()"):p.index("function measure(")]
        order = [kind.index('return "update"'), kind.index('return "saver"'), kind.index('return "install"')]
        self.assertEqual(order, sorted(order))                                   # a new version > images off > install
        self.assertIn("state.offer && !state.installed && !state.known && !busy()", kind)
        for bit in ('data-pwa-act="install-later"', 'data-pwa-act="install-how"', 'data-from="toast"', "pwa-toast-icon pwa-toast-app",
                    'class="pwa-toast-actions"', '"Install this site as an app", "Instala este sitio como app"',
                    '"Not now", "Ahora no"', '"Show me how", "Ver cómo"',
                    "Okay. “Install as an app” is always in the menu and at the bottom of every page.",
                    "De acuerdo. «Instalar como app» siempre está en el menú y al pie de cada página."):
            self.assertIn(bit, p)
        self.assertIn('e.key === "Escape"', p)
        # redrawn under keyboard focus: the same control stays focused (Show me how <-> Install; Not now stays Not
        # now), and when another notice takes its place, focus goes back where the visitor was
        toast = p[p.index("function renderToast()"):p.index("function focusBack()")]
        self.assertIn('var same = { install: "install-how", "install-how": "install" };', toast)
        self.assertIn("if (had && hadKind === kind) {", toast)
        self.assertIn("} else if (had) focusBack();", toast)
        # the second sentence can go on a short screen (pwa.css)
        self.assertIn('<span class="pwa-toast-more">', p)
        # /app/: a link to a guide opens it (no hashchange when the address has it already); the Aa panel's link
        # moves focus to the opened guide's title after the jump
        start = p[p.index("function startAppPage()"):]
        self.assertIn("closest('a[href^=\"#\"]')", start)
        guided = p[p.index("function guided(a)"):p.index("/* The install row")]
        self.assertIn('d.querySelector("summary")', guided)
        self.assertIn("setTimeout(function () { s.focus({ preventScroll: true }); }, 0)", guided)
        for cls in ("has-lang-banner", "has-player", "tts-bar-on", "pwa-bar-on", "glightbox-open"):
            self.assertIn(cls, p[p.index("function busy()"):p.index("function busy()") + 1200])
        self.assertNotRegex(p, r"pwa-steps(?!-link)")                           # the old one-liners are gone
        self.assertNotIn("isMacSafari", p)

    def test_styles(self):
        css = read("src", "assets", "css", "areas", "pwa.css")
        for bit in (".pwa-toast-app {", ".pwa-guide {", ".pwa-guide-os > summary {", ".pwa-guide-key {", ".pwa-guide-note {",
                    ":root.pwa-standalone [data-pwa-app-link] { display: none !important; }",
                    "@media (display-mode: standalone) { [data-pwa-app-link] { display: none !important; } }",
                    ':root[data-motion="reduce"] .pwa-guide-chev { transition: none; }'):
            self.assertIn(bit, css)
        self.assertNotIn(".pwa-steps", css)
        # a short screen (a phone held sideways): the phone's text caps, the install notice's title and buttons only,
        # its buttons kept at the bottom of the box
        short = css[css.index("@media (height < 32rem) {"):]
        short = short[:short.index("\n}\n")]
        access = read("src", "assets", "css", "areas", "access.css")
        for pct in ("130", "150"):
            cap = re.search(r':root\[data-text="%s"\] \{ --bar-zoom: ([\d.]+); \}' % pct, access).group(1)
            self.assertIn(':root[data-text="%s"] .pwa-toast { --bar-zoom: %s; }' % (pct, cap), short)
        self.assertIn('.pwa-toast[data-kind="install"] :is(.pwa-toast-icon, .pwa-toast-more) { display: none; }', short)
        self.assertIn('.pwa-toast[data-kind="install"] .pwa-toast-actions { position: sticky; bottom: 0;', short)
        # printed: the in-app guide's address follows "Or copy the link…" (the Copy button is hidden on paper)
        self.assertIn(":root.js .pwa-guide-more [data-nojs-only] { display: inline !important; }", css[css.rindex("@media print"):])
        # a phone at 130 %+ or relaxed spacing: the notes' and tips' icon column goes (the site's rule for decorative icons)
        self.assertIn(':root:is([data-text="130"], [data-text="150"], [data-spacing="relaxed"]) :is(.pwa-guide-os > summary > :first-child, '
                      '.pwa-guide-note > .icon, .pwa-guide-tip > .icon) { display: none; }', css)
        self.assertIn("5. Install as an app", css[:css.index("*/")])            # listed in the file's header

    def test_links_hidden_in_the_installed_app(self):
        footer = read("src", "_includes", "partials", "footer.njk")
        header = read("src", "_includes", "partials", "header.njk")
        self.assertIn('<li class="flex"{% if f.page == "app" %} data-pwa-app-link{% endif %}>', footer)
        self.assertIn('{% if f.page == "app" %} data-pwa-app-link{% endif %}', header)
        self.assertNotIn("Saved pages & app", footer + header + read("src", "_data", "nav.js"))


if __name__ == "__main__":
    unittest.main()
