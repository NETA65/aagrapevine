"""Install the site as an app (the steps on Saved pages & app, /offline/#steps, src/pages/offline.njk;
src/assets/js/install-core.js; the install parts of src/assets/js/pwa.js) — the checks that need no
browser. (The browser checks — the notice on an Android Chrome with the real prompt, the iPhone / Samsung /
Firefox / in-app user agents, the installed app, the offline stand-in, keyboard and focus, 320–1280 px at
150 % text / relaxed spacing / high contrast, axe — are QA scripts.)

  * Strings   — every pwa.app.* key in English AND Spanish, used by the pages and none left over; the
                length budgets; the platforms' own words as their help pages print them today (EN and
                Latin-American ES — re-check them every September and after big Chrome releases); menus
                named in words, never ⋮ ≡ •••; no "PDF", no words about how the site is kept up to date;
                the {app} and {a} {b} {c} placeholders in both languages; each key in one i18n file only;
                the page's name "Saved pages & app" and its search words (saved pages AND installing);
                the hero's install link and button name the app; a meeting ID wraps between its groups.
  * Page      — /offline/ + /es/offline/, the one page with the steps (front matter, in the sitemap, the
                search and search engines), its sections in order with nothing said twice, the seven
                guides in order, the data-attribute contract with pwa.js, Safari's step-1 versions, the
                official help links and the magazines' apps from config/site.yml, the Android shortcuts
                named as in the manifest, one footer entry (the bottom bar's "Saved pages & app", no
                "Install as an app" in "Stay updated"), the Accessibility page's one link, the local
                safari-menu icon.
  * Stand-in  — the script after the hero's buttons (inside the hero), run in Node against a pretend
                page: standing in for a page that isn't saved it says "You're offline" (hero and tab
                title), leaves "Try again" alone and takes the address's #fragment off (/gvr/#steps: the
                page has a #steps of its own), kept for pwa.js to put back before reloading; opened on
                purpose (index.html included) it changes nothing — reloaded or Back, the #fragment is off
                the address while the page loads (Chrome would jump to it before putting the visitor back
                where they were); pwa.js tells standing in the same way.
  * Redirect  — the old install page's address (src/pages/app-redirect.njk) forwards to /offline/ with
                the ?query and the #guide, #steps without one; noindex, canonical, out of the sitemap.
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
                has the "install" toast with Not now / Show me how (and "Not now" names the page the steps
                are on); every install link goes to /offline/, the hero's buttons give way to "Try again"
                on the stand-in, a #guide asked for stays on screen as the saved list fills in (on arrival,
                not after a reload or Back), forwarding pages are not listed, the steps count as read (the
                notice's 30 days of quiet) only once reached, the installed app opens no guide; pwa.css;
                nothing left of the old page (no /app/ anywhere but its forwarding stub).

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
PAGE = ("src", "pages", "offline.njk")            # Saved pages & app: the install steps are its #steps
STUB = ("src", "pages", "app-redirect.njk")       # the old install page's address


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
        self.assertEqual(len(keys), 74)
        for key, v in keys.items():
            with self.subTest(key=key):
                self.assertTrue((v.get("en") or "").strip())
                self.assertTrue((v.get("es") or "").strip())
                self.assertEqual(set(v), {"en", "es"})

    def test_the_pages_use_every_key_and_no_other(self):
        # the steps on /offline/, and the old address's "moved" line
        pages = read(*PAGE) + read(*STUB)
        used = set(re.findall(r"""["'](pwa\.app\.[a-z0-9_]+)["']""", pages))
        keys = set(app_keys())
        self.assertEqual(used - keys, set(), "keys the pages use that pwa.json lacks")
        self.assertEqual(keys - used, set(), "pwa.app.* keys nothing uses")
        self.assertIn('"pwa.app.moved_text"', read(*STUB))

    def test_length_budgets(self):
        # (the hero's subtitle and eyebrow are the offline page's: tests/test_pwa.py)
        s = pwa_strings()
        common = json.loads(read("src", "_i18n", "common.json"))
        budgets = {k: (24, 28) for k in ("pwa.app.cta_steps", "pwa.app.cta_install", "pwa.app.cta_send", "pwa.app.copy_link")}
        for key, (en, es) in budgets.items():
            with self.subTest(key=key):
                self.assertLessEqual(len(s[key]["en"]), en)
                self.assertLessEqual(len(s[key]["es"]), es)
        # the page's name: the footer's bottom bar and the phone menu
        self.assertLessEqual(len(common["nav.offline"]["en"]), 24)
        self.assertLessEqual(len(common["nav.offline"]["es"]), 28)

    def test_the_hero_buttons_name_the_app(self):
        # the hero's title is the whole page's ("Saved pages & app"): its install link and one-tap button say what
        # they do on their own (a screen reader's list of links and buttons, WCAG 2.4.4 / 2.4.6)
        s = pwa_strings()
        self.assertEqual(s["pwa.app.cta_steps"], {"en": "How to install the app", "es": "Cómo instalar la app"})
        self.assertEqual(s["pwa.app.cta_install"], {"en": "Install the app", "es": "Instalar la app"})

    def test_a_meeting_id_breaks_between_its_groups(self):
        # the hero's "Join by phone" card: the ID keeps a line of its own where it fits (an inline-block) and a narrow
        # phone at 150 % text wraps it only between its digit groups ("871 2036" / "8287"), never inside one — and
        # "ID" stays with the number (a no-break space)
        s = pwa_strings()
        self.assertEqual(s["pwa.offline.phone_call"], {"en": "Call now ({city})", "es": "Llamar ahora ({city})"})
        self.assertEqual(s["pwa.offline.phone_id"], {"en": "ID\u00a0{id}", "es": "ID\u00a0{id}"})
        page = read(*PAGE)
        self.assertIn('''{%- set callText = (("pwa.offline.phone_call" | t(lang, { city: mt.callCity })) | escape) ~ " · " ~ '''
                      '''\'<span class="inline-block">\' ~ (("pwa.offline.phone_id" | t(lang, { id: mt.id })) | escape) ~ "</span>" %}''', page)
        self.assertIn("text: callText | safe,", page)
        self.assertNotIn("mt.id | replace(", page)                                    # (the whole ID one word: broken anywhere)

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
        # and the steps hide it inside WhatsApp's own window (Page.test_data_attribute_contract)
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
        mine = set(app_keys()) | {"nav.offline", "search.page_desc.offline", "search.kw.offline"}
        # …and the old install page's own keys are gone (its title is the page's, its words /offline/'s)
        gone = {"nav.app", "search.page_desc.app", "search.kw.app", "access.f_offline_cta", "pwa.offline.page_title",
                "pwa.offline.title_online", "pwa.app.meta_desc", "pwa.app.eyebrow", "pwa.app.sub", "pwa.app.steps_h"}
        seen = {}
        for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
            for k in json.loads(f.read_text(encoding="utf-8")):
                if k in mine or k in gone:
                    seen.setdefault(k, []).append(f.name)
        for k in sorted(mine):
            with self.subTest(key=k):
                self.assertEqual(len(seen.get(k, [])), 1, seen.get(k))
        self.assertEqual({k: v for k, v in seen.items() if k in gone}, {})

    def test_labels_and_search_words(self):
        common = json.loads(read("src", "_i18n", "common.json"))
        access = json.loads(read("src", "_i18n", "access.json"))
        # the page's name, as it was before the install steps had a page of their own
        self.assertEqual(common["nav.offline"], {"en": "Saved pages & app", "es": "Páginas guardadas y app"})
        # one page for both: the site's search finds it by saved pages AND by installing
        kw, desc = access["search.kw.offline"], access["search.page_desc.offline"]
        for word in ("saved pages", "offline", "data saver", "install", "home screen", "iphone", "android", "pwa"):
            self.assertIn(word, kw["en"], word)
        for word in ("páginas guardadas", "sin conexión", "ahorro de datos", "instalar", "pantalla de inicio", "iphone", "android", "celular"):
            self.assertIn(word, kw["es"], word)
        self.assertIn("as an app", desc["en"])
        self.assertIn("como app", desc["es"])


class Page(unittest.TestCase):
    def setUp(self):
        self.page = read(*PAGE)

    def test_front_matter(self):
        fm = re.match(r"---\n(.*?)\n---\n", self.page, re.S).group(1)
        self.assertIn("pagination: { data: languages, size: 1, alias: lang }", fm)
        self.assertIn("""permalink: "{{ '/' if lang == 'en' else '/es/' }}offline/index.html\"""", fm)
        self.assertRegex(fm, r"(?m)^layout: layouts/base\.njk$")
        self.assertRegex(fm, r"(?m)^pageKey: offline$")
        self.assertRegex(fm, r"(?m)^titleKey: nav\.offline$")                   # "Saved pages & app": nav, <title>, hero
        self.assertRegex(fm, r"(?m)^descKey: pwa\.offline\.meta_desc$")
        # a page to share and to find: in the sitemap, the collections and the search — and never noindex
        self.assertNotIn("sitemap: false", fm)
        self.assertNotIn("eleventyExcludeFromCollections", fm)
        base = read("src", "_includes", "layouts", "base.njk")
        self.assertNotIn('pageKey == "offline"', base)
        self.assertIn('{%- if pageKey == "404" %}', base)
        self.assertIn("so it is indexed with its canonical and hreflang links", base)   # (and the comment says why)
        # the page it replaces is gone: its address is a forwarding stub (Redirect)
        self.assertFalse(ROOT.joinpath("src", "pages", "app.njk").exists())

    def test_the_sitemap_requires_it(self):
        # src/pages/sitemap.11ty.js REQUIRED: a build that lost /offline/ or /es/offline/ (renamed, excluded by
        # mistake) says so in its log; with both, the sitemap lists them and says nothing
        r = run_js(self, r"""
          const m = await imp("src/pages/sitemap.11ty.js");
          const warned = [];
          console.warn = (s) => warned.push(String(s));
          const page = (u) => ({ url: u, data: {} });
          const all = ["/", "/whats-new/", "/published/", "/read/", "/monthly/", "/digest/"].flatMap((u) => [page(u), page("/es" + u)]);
          m.render({ site: { url: "https://x.test" }, collections: { all } });
          const xml = m.render({ site: { url: "https://x.test" }, collections: { all: [...all, page("/offline/"), page("/es/offline/")] } });
          out({ warned, listed: xml.includes("<loc>https://x.test/offline/</loc>") && xml.includes("<loc>https://x.test/es/offline/</loc>") });""",
                   needs_modules=False, env={"ONLY": ""})
        self.assertEqual(r["warned"], ["[sitemap] missing page(s): /offline/, /es/offline/"])
        self.assertTrue(r["listed"])
        self.assertNotIn('"/app/"', read("src", "pages", "sitemap.11ty.js"))

    def test_the_site_search_finds_it(self):
        # the site's own search: one entry for the page (library.js walks nav.footer), by its name, found by the
        # words for saved pages AND for installing — and none for the old install page
        r = run_js(self, r"""
          const nav = (await imp("src/_data/nav.js")).default;
          out(["en", "es"].map((lang) => JSON.parse(filters.searchIndexJson({}, nav, lang, {})).items.filter((e) => /^page:(offline|app)$/.test(e.id))));
        """, env={"LIB_EMPTY": "1"})
        en, es = r
        self.assertEqual([e["id"] for e in en + es], ["page:offline", "page:offline"])
        self.assertEqual((en[0]["t"], en[0]["u"], es[0]["t"], es[0]["u"]), ("Saved pages & app", "/offline/", "Páginas guardadas y app", "/es/offline/"))
        for e in (en[0], es[0]):
            for word in ("saved pages", "install", "home screen", "páginas guardadas", "instalar", "pantalla de inicio"):
                self.assertIn(word, e["x"], word)
        self.assertIn("as an app", en[0]["s"])
        self.assertIn("como app", es[0]["s"])

    def test_sections_in_order_and_nothing_said_twice(self):
        # hero → the pages saved on this device → how it works offline → the install steps → why → good to know
        p = self.page
        order = [p.index("ui.pageHero(lang, \"nav.offline\" | t(lang)"), p.index('aria-labelledby="pwa-saved-h"'),
                 p.index('aria-labelledby="pwa-how-h"'), p.index('<section id="steps"'), p.index('aria-labelledby="app-why-h"'),
                 p.index('aria-labelledby="app-more-h"')]
        self.assertEqual(order, sorted(order))
        # one install card, not two: the hero's buttons and the steps (the "how" cards: kept pages, Save key
        # pages, Data saver); "works with a weak signal" is the "how" section, not a "why" card too
        how = p[p.index("{%- set how = ["):p.index("] -%}", p.index("{%- set how = ["))]
        self.assertEqual(re.findall(r'h: "(pwa\.offline\.how\d_h)"', how), ["pwa.offline.how1_h", "pwa.offline.how2_h", "pwa.offline.how3_h"])
        self.assertEqual(how.count("save: true"), 1)
        self.assertNotIn("install", how)
        why = p[p.index("{%- set why = ["):p.index("] -%}", p.index("{%- set why = ["))]
        self.assertEqual(re.findall(r'h: "(pwa\.app\.why\d_h)"', why), ["pwa.app.why1_h", "pwa.app.why2_h", "pwa.app.why3_h"])
        self.assertNotIn("wifi-off", why)
        self.assertIsNone(re.search(r"data-pwa-install(?![-\w])", p))           # no install slot on the page
        self.assertNotIn("'/offline/' | lurl", p)                                # never a link to itself
        s = pwa_strings()
        self.assertEqual(s["pwa.offline.how3_h"]["en"], "Use less data")
        self.assertEqual(s["pwa.app.why2_h"]["en"], "In your language")
        for k in ("pwa.offline.how4_h", "pwa.offline.how4_t", "pwa.app.why4_h", "pwa.app.why4_t"):
            self.assertNotIn(k, s)
        # the steps' own heading: the old page's title
        self.assertIn('ui.sectionHead("pwa.app.title" | t(lang), "pwa.app.steps_sub" | t(lang)', p)

    def test_seven_guides_in_order(self):
        block = self.page[self.page.index("{%- set guides = ["):self.page.index("{%- set why = [")]
        self.assertEqual(re.findall(r'\{ id: "([a-z-]+)"', block), GUIDES)
        self.assertIn('<details class="pwa-guide-os card" id="{{ g.id }}" data-pwa-guide="{{ g.id }}">', self.page)
        for g in GUIDES:
            self.assertIn(g, self.page.split("-#}", 1)[0], f"the header comment lists {g}")

    def test_data_attribute_contract(self):
        p = self.page
        self.assertRegex(p, r'<section id="steps" class="section container-page pt-0" aria-labelledby="app-steps-h" data-pwa-app>')
        self.assertRegex(p, r'<span class="pwa-guide-title min-w-0 flex-1">\{\{ g\.h \| t\(lang\) \}\} <span class="badge-vine pwa-guide-here" data-pwa-here hidden>')
        # the hero: "Try again" (hidden: the stand-in shows it), "How to install the app", the one-tap "Install the app",
        # "Send this page"
        hero = p[p.index("<div class=\"hero-actions\" data-pwa-offline-copy"):p.index("</div>", p.index("<div class=\"hero-actions\" data-pwa-offline-copy"))]
        for attr in ("data-title-standin=\"{{ 'pwa.offline.title' | t(lang) }}\"", "data-sub-standin=\"{{ 'pwa.offline.sub' | t(lang) }}\"",
                     "data-sub-online=\"{{ 'pwa.offline.sub_online' | t(lang) }}\"", "data-sub-offline=\"{{ 'pwa.offline.sub_direct' | t(lang) }}\""):
            self.assertIn(attr, hero)
        self.assertRegex(hero, r'<a class="btn-light" href="[^"]*" data-pwa-retry hidden>')
        self.assertRegex(hero, r'<a class="btn-light" href="#steps" data-pwa-steps-link>')
        self.assertRegex(hero, r'<button type="button" class="btn-light" data-pwa-act="install" data-pwa-install-hero hidden>')
        self.assertRegex(hero, r'<button type="button" class="btn-on-dark" data-js-only data-share="\{\{ appUrl \}\}" data-share-title="\{\{ \'pwa\.app\.title\' \| t\(lang\) \}\}"')
        self.assertIn('"pwa.offline.sub_online" | t(lang)', p[p.index("ui.pageHero("):p.index("ui.pageHero(") + 200])   # the static subtitle
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
        # the Copy / Send buttons carry the steps' full address (JavaScript only; the address as text without it)
        self.assertIn('{%- set appUrl = (page.url | siteUrl(site)) + "#steps" -%}', p)
        self.assertRegex(p, r'data-js-only data-copy="\{\{ appUrl \}\}"')
        self.assertRegex(p, r'data-nojs-only>\{\{ appUrl \}\}<')
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
        # the saved pages come first after the hero (pwa.js offlineList) and "Save key pages" has its slot
        self.assertIn('<section class="container-page page-overlap" aria-labelledby="pwa-saved-h">', p)
        self.assertIn("data-pwa-saved", p)
        self.assertIn('<div class="pwa-card-slot mt-auto empty:hidden" data-pwa-save></div>', p)

    def test_links_from_site_settings(self):
        p = self.page
        for k in ("app_help_iphone", "app_help_iphone_es", "app_help_android", "app_help_android_es"):
            with self.subTest(link=k):
                self.assertIn("ln." + k, p)
        self.assertIn("[[ln.gv_apps, \"media.short_gv_app\", \"en\"], [ln.lv_apps, \"media.short_lv_app\", \"es\"]]", p)
        self.assertIn('magApps | reverse if lang == "es"', p)                      # La Viña first on /es/offline/

    def test_the_help_links_in_the_settings(self):
        # config/site.yml as the committee keeps it — left to the Code check (scripts/ops/gate_tests.py CONTENT_TESTS)
        links = yaml.safe_load(read("config", "site.yml"))["links"]
        for k in ("app_help_iphone", "app_help_iphone_es", "app_help_android", "app_help_android_es"):
            with self.subTest(link=k):
                self.assertRegex(links[k], r"^https://support\.(apple|google)\.com/")
        self.assertIn("/es-mx/", links["app_help_iphone_es"])
        self.assertIn("hl=es-419", links["app_help_android_es"])

    def test_shortcuts_named_as_in_the_manifest(self):
        manifest = read("src", "pages", "manifest.11ty.js")
        block = manifest[manifest.index("shortcuts: ["):manifest.index("].map(")]
        keys = re.findall(r't\("(nav\.[a-z_]+)"\)', block)
        m = re.search(r'"pwa\.app\.more_shortcuts" \| t\(lang, \{ a: "(nav\.\w+)" \| t\(lang\), b: "(nav\.\w+)" \| t\(lang\), c: "(nav\.\w+)" \| t\(lang\) \}\)', self.page)
        self.assertIsNotNone(m)
        self.assertEqual(list(m.groups()), keys)

    def test_one_footer_entry_and_the_icon(self):
        # the footer stays uniform: "Stay updated" holds Instagram and QR Post only; the page is the bottom
        # bar's "Saved pages & app" (group "site"), which the phone menu's "More" lists too
        nav = read("src", "_data", "nav.js")
        self.assertIn('{ key: "nav.offline", url: "/offline/", page: "offline", icon: "hard-drive-download", group: "site" }', nav)
        self.assertEqual(re.findall(r'key: "(nav\.\w+)"[^}]*group: "stay"', nav), ["nav.instagram", "nav.share"])
        self.assertEqual(len(re.findall(r'url: "/offline/"', nav)), 1)
        self.assertNotIn("nav.app", nav)
        footer = read("src", "_includes", "partials", "footer.njk")
        header = read("src", "_includes", "partials", "header.njk")
        for part in (footer, header):
            self.assertNotIn("data-pwa-app-link", part)
            self.assertNotIn('f.page == "app"', part)
        svg = read("src", "_includes", "icons", "safari-menu.svg")
        for d in ("M4 6h16", "M4 12h16", "M4 18h10"):
            self.assertIn(f'<path d="{d}"/>', svg)
        self.assertIn('viewBox="0 0 24 24"', svg)
        self.assertIn('stroke="currentColor"', svg)

    def test_the_accessibility_page_links_here_once(self):
        acc = read("src", "pages", "accessibility.njk")
        at = acc.index("Saved pages and the app (feature 14)")
        card = acc[at:acc.index("</li>", at)]
        self.assertEqual(re.findall(r'href="([^"]+)"', card), ["{{ '/offline/' | lurl(lang) }}"])   # one real link…
        self.assertIn('{{ "nav.offline" | t(lang) }}', card)                                      # …by the page's name
        self.assertNotIn("after:absolute", card)


# Runs the script the offline page puts after its hero's buttons (it is the page's own, so the test takes it
# from the template) against a pretend page: input = [{ path, search, hash, nav, own, title }] → what each run changed
# (beforeLoad: the addresses it set as the page was read; replaced: those and the ones set at load).
STAND_IN = r"""
import vm from "node:vm";
const src = fs.readFileSync("src/pages/offline.njk", "utf8");
const m = /<script>(\(function \(box\) \{[\s\S]*?\}\)\(document\.querySelector\("\[data-pwa-offline-copy\]"\)\);)<\/script>/.exec(src);
if (!m) throw new Error("the stand-in script is not there");
out(input.map((c) => {
  const el = (attrs, extra) => Object.assign({ hidden: "hidden" in attrs, attrs: Object.assign({}, attrs),
    hasAttribute(n) { return n in this.attrs; }, getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; },
    setAttribute(n, v) { this.attrs[n] = String(v); }, removeAttribute(n) { delete this.attrs[n]; } }, extra || {});
  const retry = el({ href: "/aagrapevine/", "data-pwa-retry": "", hidden: "" });
  const kids = [retry, el({ href: "#steps", "data-pwa-steps-link": "" }), el({ "data-pwa-install-hero": "", hidden: "" }), el({ "data-share": "x" })];
  const h1 = { textContent: "Saved pages & app" }, sub = { textContent: "The pages saved on this device open…" };
  const hero = { querySelector: (q) => (q === ".gv-hero-title > span:last-child" ? h1 : q === ".gv-hero-sub" ? sub : null) };
  const box = el({ "data-title-standin": "You're offline", "data-sub-standin": "This page isn't saved…" }, {
    children: kids, closest: (q) => (q === "[data-gv-hero]" ? hero : null),
    querySelector: (q) => (q === "[data-pwa-retry]" ? retry : null) });
  const document = { title: c.title, querySelector: (q) => (q === "[data-pwa-offline-copy]" ? box : null) };
  const replaced = [], history = { state: null, replaceState: (st, t, u) => { replaced.push(u); } };
  const loads = [], performance = { getEntriesByType: (t) => (t === "navigation" && c.nav ? [{ type: c.nav }] : []) };
  const code = m[1].replace(/\{\{ \(page\.url \| url\) \| dump \| safe \}\}/, JSON.stringify(c.own));
  vm.runInContext(code, vm.createContext({ document, history, performance, addEventListener: (t, fn) => { if (t === "load") loads.push(fn); },
                                           location: { pathname: c.path, search: c.search || "", hash: c.hash || "" } }));
  const beforeLoad = replaced.slice(), heldBeforeLoad = box.getAttribute("data-hash-load");
  loads.forEach((fn) => fn());
  return { h1: h1.textContent, sub: sub.textContent, title: document.title, hidden: kids.map((k) => k.hidden), retry: retry.attrs.href,
           hash: box.getAttribute("data-hash"), beforeLoad, replaced, heldBeforeLoad, heldAfterLoad: box.getAttribute("data-hash-load") };
}));
"""


class StandIn(unittest.TestCase):
    def test_standing_in_and_opened_on_purpose(self):
        own = "/aagrapevine/es/offline/"
        title = "Páginas guardadas y app · Grapevine / La Viña — NETA 65"
        r = run_js(self, STAND_IN, needs_modules=False, data=[
            {"path": "/aagrapevine/es/meetings/", "search": "?x=1", "own": own, "title": title},   # the worker's stand-in
            {"path": own, "own": own, "title": title},                                             # opened on purpose
            {"path": own + "index.html", "own": own, "title": title},                               # …as index.html
            {"path": "/aagrapevine/es/", "own": own, "title": "Grapevine"},                          # a title without " · "
        ])
        stand, direct, index, bare = r
        self.assertEqual((stand["h1"], stand["sub"]), ("You're offline", "This page isn't saved…"))
        self.assertEqual(stand["title"], "You're offline · Grapevine / La Viña — NETA 65")
        self.assertEqual(bare["title"], "You're offline")
        self.assertEqual(stand["hidden"], [False, True, True, True])                # "Try again" alone
        self.assertEqual(stand["retry"], "/aagrapevine/es/meetings/?x=1")            # …for the address asked for
        for d in (direct, index):
            self.assertEqual((d["h1"], d["title"]), ("Saved pages & app", title))
            self.assertEqual(d["hidden"], [True, False, True, False])               # the page's own buttons
            self.assertEqual(d["retry"], "/aagrapevine/")
        for d in r:
            self.assertEqual((d["hash"], d["replaced"]), (None, []))                # no #fragment: the address as it is

    def test_the_other_pages_fragment_comes_off(self):
        # Offline, a saved GVR / RLV 101 lesson's "Your first steps (checklist)" → /gvr/#steps, not saved: the
        # stand-in answers at that address, and it has a #steps of its own (the install steps, far below the saved
        # pages). The #fragment comes off the address before the browser can jump there — kept in data-hash, which
        # pwa.js puts back before reloading — so "You're offline" and the saved pages come first. Opened on
        # purpose, a #guide is the visitor's to keep.
        own = "/aagrapevine/offline/"
        title = "Saved pages & app · Grapevine / La Viña — NETA 65"
        r = run_js(self, STAND_IN, needs_modules=False, data=[
            {"path": "/aagrapevine/gvr/", "hash": "#steps", "own": own, "title": title},
            {"path": "/aagrapevine/es/gvr/", "search": "?a=1", "hash": "#steps", "own": "/aagrapevine/es/offline/", "title": title},
            {"path": own, "hash": "#android", "own": own, "title": title},
        ])
        gvr, es, direct = r
        self.assertEqual((gvr["hash"], gvr["replaced"], gvr["h1"]), ("#steps", ["/aagrapevine/gvr/"], "You're offline"))
        self.assertEqual(gvr["retry"], "/aagrapevine/gvr/")                          # "Try again": pwa.js reloads, #steps back on
        self.assertEqual((es["hash"], es["replaced"]), ("#steps", ["/aagrapevine/es/gvr/?a=1"]))
        self.assertEqual((direct["hash"], direct["replaced"], direct["h1"]), (None, [], "Saved pages & app"))
        # pwa.js: the #fragment back on before either reload ("Try again", the connection back), and no scrolling
        # to a #fragment while standing in (a browser that jumped anyway — it read the address first — goes back to
        # the top once the list is drawn, or at load)
        pwa = read("src", "assets", "js", "pwa.js")
        again = pwa[pwa.index("function reloadAsked()"):pwa.index("function offlinePageCopy()")]
        self.assertIn('box.getAttribute("data-hash")', again)
        self.assertIn("history.replaceState(history.state, \"\", location.pathname + location.search + h)", again)
        self.assertEqual(pwa.count("reloadAsked();"), 2)
        self.assertEqual(pwa.count("location.reload();"), 3)                         # reloadAsked's, the new version's, and one applied in another tab
        self.assertIn("if (wantReload) { wantReload = false; location.reload(); }", pwa)
        lst = pwa[pwa.index("function offlineList()"):pwa.index('box.addEventListener("click"', pwa.index("function offlineList()"))]
        self.assertIn("var dropped = isFallback && !!(copyBox && copyBox.getAttribute(\"data-hash\"));", lst)
        self.assertIn("if (isFallback) { if (dropped && window.scrollY) window.scrollTo(0, 0); return; }", lst)
        self.assertIn('if (dropped) window.addEventListener("load", keepFragment, { once: true });', lst)

    def test_opened_again_the_browser_keeps_its_place(self):
        # /offline/#android reloaded, or back to it: the browser puts the visitor back where they were — but Chrome
        # first jumps to the #guide when it can't at once (the saved pages, listed a moment later, make the page
        # taller than its first layout). The #fragment is off the address while the page loads, back on at load; a
        # first arrival keeps it (the browser's own jump, then pwa.js keeps the guide on screen)
        own = "/aagrapevine/offline/"
        title = "Saved pages & app · Grapevine / La Viña — NETA 65"
        r = run_js(self, STAND_IN, needs_modules=False, data=[
            {"path": own, "hash": "#android", "nav": "reload", "own": own, "title": title},
            {"path": own, "search": "?x=1", "hash": "#steps", "nav": "back_forward", "own": own, "title": title},
            {"path": own, "hash": "#android", "nav": "navigate", "own": own, "title": title},
            {"path": own, "nav": "reload", "own": own, "title": title},
        ])
        reload, back, first, bare = r
        self.assertEqual((reload["beforeLoad"], reload["replaced"]), (["/aagrapevine/offline/"], ["/aagrapevine/offline/", "/aagrapevine/offline/#android"]))
        self.assertEqual((back["beforeLoad"], back["replaced"]), (["/aagrapevine/offline/?x=1"], ["/aagrapevine/offline/?x=1", "/aagrapevine/offline/?x=1#steps"]))
        for d in (first, bare):
            self.assertEqual(d["replaced"], [])
        for d in r:
            self.assertEqual((d["h1"], d["hash"], d["hidden"]), ("Saved pages & app", None, [True, False, True, False]))   # the page's own
        # While the #guide is off the address, data-hash-load keeps it for pwa.js (the guide still opens — also one
        # that is not this device's, e.g. a shared /offline/#iphone reloaded on an Android phone); gone at load.
        self.assertEqual((reload["heldBeforeLoad"], reload["heldAfterLoad"]), ("#android", None))
        self.assertEqual((back["heldBeforeLoad"], back["heldAfterLoad"]), ("#steps", None))
        for d in (first, bare):
            self.assertEqual((d["heldBeforeLoad"], d["heldAfterLoad"]), (None, None))
        pwa = read("src", "assets", "js", "pwa.js")
        guide = pwa[pwa.index("var hashGuide = function () {"):pwa.index('window.addEventListener("hashchange", hashGuide);')]
        self.assertIn('location.hash || (held && held.getAttribute("data-hash-load")) || ""', guide)
        self.assertIn("openGuide(decodeURIComponent(h.slice(1)))", guide)

    def test_it_sits_in_the_hero(self):
        # right after the buttons it changes, inside the hero's call: nothing may come between the hero and the
        # saved pages' card (main.css: .gv-hero-shell.side-below + .page-overlap spaces the card under "Join by phone")
        page = read(*PAGE)
        at = page.index("<script>(function (box) {")
        self.assertLess(page.index('<div class="hero-actions" data-pwa-offline-copy'), at)
        self.assertLess(at, page.index("{% endcall %}\n\n{#- ============ The pages saved on this device"))
        self.assertIn(".gv-hero-shell.side-below + .page-overlap", read("src", "assets", "css", "main.css"))

    def test_pwa_js_tells_the_same_way(self):
        page = read(*PAGE)
        self.assertIn('if (location.pathname.replace(/index\\.html$/, "") === {{ (page.url | url) | dump | safe }}) {', page)
        pwa = read("src", "assets", "js", "pwa.js")
        self.assertIn('var isFallback = isOfflinePage && location.pathname.replace(/index\\.html$/, "") !== new URL(OFFLINE_URL, location.href).pathname;', pwa)


# Runs the old address's forwarding line against pretend addresses: input = [{ search, hash }] → where it goes.
REDIRECT = r"""
import vm from "node:vm";
const src = fs.readFileSync("src/pages/app-redirect.njk", "utf8");
const m = /<script>(location\.replace\([\s\S]*?\);)<\/script>/.exec(src);
if (!m) throw new Error("the forwarding script is not there");
const code = m[1].replace(/\{\{ \(target \| url\) \| dump \| safe \}\}/, JSON.stringify("/aagrapevine/offline/"));
out(input.map((loc) => { let to = null; vm.runInContext(code, vm.createContext({ location: Object.assign({ replace: (u) => { to = u; } }, loc) })); return to; }));
"""


class Redirect(unittest.TestCase):
    def setUp(self):
        self.stub = read(*STUB)

    def test_a_tiny_stand_alone_page(self):
        fm = re.match(r"---\n(.*?)\n---\n", self.stub, re.S).group(1)
        self.assertIn("pagination: { data: languages, size: 1, alias: lang }", fm)
        self.assertIn("""permalink: "{{ '/' if lang == 'en' else '/es/' }}app/index.html\"""", fm)
        for bit in ("layout: false", "sitemap: false", "eleventyExcludeFromCollections: true"):
            self.assertRegex(fm, r"(?m)^" + re.escape(bit) + "$")
        b = self.stub[len(fm):]
        self.assertIn('{%- set target = "/offline/" | lurl(lang) -%}', b)
        self.assertIn('<meta http-equiv="refresh" content="0; url={{ target }}#steps">', b)   # without JavaScript: the steps
        self.assertIn('<meta name="robots" content="noindex">', b)
        self.assertIn('<link rel="canonical" href="{{ target | siteUrl(site) }}">', b)
        self.assertIn('{{ "read.subs.moved_title" | t(lang) }}', b)
        self.assertIn('{{ "pwa.app.moved_text" | t(lang) }}', b)
        self.assertIn('<a id="go" href="{{ target }}#steps">{{ "nav.offline" | t(lang) }} →</a>', b)
        self.assertNotIn("Saved pages", pwa_strings()["pwa.app.moved_text"]["en"])             # the link names the page

    def test_the_guide_and_the_query_go_along(self):
        r = run_js(self, REDIRECT, needs_modules=False, data=[
            {"search": "", "hash": "#android"}, {"search": "?utm=wa", "hash": "#in-app"}, {"search": "", "hash": ""},
            {"search": "?x=1", "hash": ""}])
        self.assertEqual(r, ["/aagrapevine/offline/#android", "/aagrapevine/offline/?utm=wa#in-app",
                             "/aagrapevine/offline/#steps", "/aagrapevine/offline/?x=1#steps"])


class Manifest(unittest.TestCase):
    SCRIPT = r"""
      const M = await imp("src/pages/manifest.11ty.js");
      const t = (k, l) => filters.t(k, l);
      out(["en", "es"].map((lang) => JSON.parse(M.render.call({ t }, { lang }))));
    """

    def test_related_applications(self):
        for prefix, base in (("/aagrapevine/", "/aagrapevine/"), ("/", "/")):
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
    [{"views": 9}, {"page": "offline"}, False, "on the offline page (the steps are there)"],
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
        self.assertIn("known.hidden = state.installed || !!state.installEvt || !state.known;", p)   # the steps: never "already on this device" beside Install
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
        self.assertIn("state.installed = standalone();", p)
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
                    '"Not now", "Ahora no"', '"Show me how", "Ver cómo"'):
            self.assertIn(bit, p)
        # "Not now" says where the steps always are: the page's name as the footer's bottom bar and the phone menu
        # print it (nav.offline — so the two can't drift apart)
        common = json.loads(read("src", "_i18n", "common.json"))
        later = p[p.index("function notNow()"):p.index("function guided(a)")]
        en, es = re.search(r'announce\(T\("([^"]+)", "([^"]+)"\)\);', later).groups()
        self.assertEqual(en, "Okay. The steps are always in “%s”, in the menu and at the bottom of every page." % common["nav.offline"]["en"])
        self.assertEqual(es, "De acuerdo. Los pasos siempre están en «%s», en el menú y al pie de cada página." % common["nav.offline"]["es"])
        self.assertIn('e.key === "Escape"', p)
        # redrawn under keyboard focus: the same control stays focused (Show me how <-> Install; Not now stays Not
        # now), and when another notice takes its place, focus goes back where the visitor was
        toast = p[p.index("function renderToast()"):p.index("function focusBack()")]
        self.assertIn('var same = { install: "install-how", "install-how": "install" };', toast)
        self.assertIn("if (had && hadKind === kind) {", toast)
        self.assertIn("} else if (had) focusBack();", toast)
        # the second sentence can go on a short screen (pwa.css)
        self.assertIn('<span class="pwa-toast-more">', p)
        # the steps: a link to a guide opens it (no hashchange when the address has it already); the Aa panel's
        # link moves focus to the opened guide's title after the jump
        start = p[p.index("function startAppSteps()"):]
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
                    ':root[data-motion="reduce"] .pwa-guide-chev { transition: none; }'):
            self.assertIn(bit, css)
        self.assertNotIn(".pwa-steps", css)
        self.assertNotIn("data-pwa-app-link", css)                             # no link to hide in the installed app
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

    def test_every_install_link_goes_to_the_steps(self):
        p = self.pwa
        # "Show me how", the Aa panel's row and "How to open it in your browser": this device's guide on
        # /offline/ (without install-core.js: the steps themselves)
        self.assertIn('var guideUrl = OFFLINE_URL + "#" + (dev ? dev.guide : "steps");', p)
        self.assertIn('esc(OFFLINE_URL + "#in-app")', p)
        self.assertIn('var appSteps = document.querySelector("[data-pwa-app]");', p)
        # the Aa panel's install row is the only one (the offline page's install card went with its slot)
        self.assertNotIn("APP_URL", p)
        self.assertIsNone(re.search(r"data-pwa-install(?![-\w])", p))
        self.assertIn("function installHtml() {", p)
        # on the stand-in the hero's own buttons give way to "Try again" (the page's script hides them first)
        self.assertIn("if (btn) btn.hidden = state.installed || isFallback || !state.installEvt;", p)
        self.assertIn("steps.hidden = state.installed || isFallback || !!state.installEvt;", p)
        # opened on purpose, the hero's subtitle follows the connection
        copy = p[p.index("function offlinePageCopy()"):p.index("function readCache(")]
        self.assertIn("if (!box || isFallback) return;", copy)
        self.assertIn('box.getAttribute(state.online ? "data-sub-online" : "data-sub-offline")', copy)
        # the notice never shows on the page with the steps (nor on a noindex page)
        self.assertIn('page: isOfflinePage ? "offline" : isNoindex ? "noindex" : "",', p)
        self.assertIn("if (!canOffer() || isOfflinePage || isNoindex) return;", p)

    def test_a_guide_asked_for_stays_on_screen(self):
        # /offline/#android (Show me how, a link someone sent): the saved list fills in above the steps after the
        # browser has scrolled there, so it scrolls back to the guide once drawn — whatever the list turned out to
        # be — unless the visitor has scrolled, tapped or pressed a key since; and on arrival only: after a reload
        # or Back the browser puts the visitor back where they were (the navigation's type says which)
        p = self.pwa
        lst = p[p.index("function offlineList()"):p.index('box.addEventListener("click"', p.index("function offlineList()"))]
        self.assertIn('["wheel", "touchstart", "pointerdown", "keydown"]', lst)
        keep = lst[lst.index("var keepFragment = function () {"):lst.index("};", lst.index("var keepFragment = function () {"))]
        self.assertIn('nav = performance.getEntriesByType("navigation")[0];', keep)
        self.assertIn('if (moved || (nav && (nav.type === "reload" || nav.type === "back_forward"))) return;', keep)
        self.assertLess(keep.index("nav.type"), keep.index("if (isFallback)"))
        self.assertLess(keep.index("if (isFallback)"), keep.index("if (!location.hash) return;"))   # (never the other page's #fragment)
        self.assertIn("box.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING", keep)   # only a target below the list
        self.assertIn('t.scrollIntoView({ block: "start", behavior: "instant" })', keep)
        # the list is drawn by drawSaved, which runs keepFragment once it is drawn: empty, listed, or the caches failed
        self.assertIn("drawSaved(keepFragment);", lst)
        draw = p[p.index("function drawSaved(done)"):p.index("\n  }\n", p.index("function drawSaved(done)"))]
        self.assertEqual(draw.count("done();"), 3)
        # …and again once a save made on the page is done (finish), so the list never contradicts "Saved 16 pages"
        fin = p[p.index("function finish(d)"):p.index("navigator.serviceWorker.ready.then", p.index("function finish(d)"))]
        self.assertIn("drawSaved();", fin)

    def test_forwarding_pages_are_not_listed(self):
        # the old addresses' forwarding pages (/meeting/, the old install page …) are kept by the worker, so an old
        # link still works offline, but the list leaves them out: the worker marks them (tests/test_pwa_worker.py)
        p = self.pwa
        self.assertIn('moved: !!(res && res.headers.get("x-gvlv-moved"))', p)
        lst = p[p.index("function drawSaved(done)"):p.index("\n  }\n", p.index("function drawSaved(done)"))]
        self.assertIn("r = r.map(function (a) { return a.filter(function (e) { return !e.moved; }); });", lst)
        self.assertLess(lst.index("return !e.moved;"), lst.index("var savedUrls = {};"))

    def test_the_steps_read_only_once_reached(self):
        # a visit for the saved pages is not reading the steps (they are below them): the page view counts, and the
        # 30 days of quiet (GI.guided) start once the steps are reached — the address asks for them, a link to them
        # or a guide's title is used, or they come on screen; never while standing in or in the installed app
        p = self.pwa
        rec = p[p.index("  if (GI) {\n    rec = loadRec();"):p.index('window.addEventListener("beforeinstallprompt"')]
        self.assertNotIn("GI.guided", rec)
        self.assertIn("else if (!isFallback && !isNoindex) rec = saveRec(GI.view(rec));", rec)
        read_ = p[p.index("function readSteps()"):p.index("function inSteps(id)")]
        self.assertIn("if (stepsRead || !GI || state.installed || isFallback) return;", read_)
        self.assertIn("rec = saveRec(GI.guided(loadRec(), Date.now()));", read_)
        self.assertIn("return !!(el && appSteps && appSteps.contains(el));", p[p.index("function inSteps(id)"):])
        self.assertEqual(p.count("GI.guided("), 2)                               # readSteps, and "Show me how" / the Aa row
        start = p[p.index("function startAppSteps()"):p.index("/* ================================================================= Save for offline")]
        self.assertIn("if (inSteps(location.hash.slice(1))) readSteps();", start)    # the address (and a hashchange)
        self.assertIn("if (inSteps(id)) readSteps();", start)                          # a link into the steps
        self.assertIn('if (e.target.closest("[data-pwa-guide] > summary")) readSteps();', start)   # a guide's title
        self.assertIn('{ rootMargin: "0px 0px -20% 0px" }', start)                    # on screen
        self.assertIn("seen.observe(appSteps);", start)
        core = read("src", "assets", "js", "install-core.js")
        self.assertIn("steps on /offline/ reached — not a look at the saved pages above them", core)

    def test_the_installed_app_opens_no_guide(self):
        # inside the app the steps say "You're using the app": no phone's guide opened or marked "Your device" (a
        # #guide in the address or a link to one still opens)
        p = self.pwa
        self.assertIn("if (dev && !state.installed) openGuide(dev.guide);", p)
        self.assertIn('badge.hidden = !(dev && !state.installed && dev.guide === d.getAttribute("data-pwa-guide"));', p)
        self.assertEqual(p.count("openGuide(dev.guide)"), 1)

    @staticmethod
    def links_to_the_old_page(*tops: str) -> list[str]:
        hits = []
        for top in tops:
            for f in ROOT.joinpath(top).rglob("*"):
                if not f.is_file() or f.suffix not in {".njk", ".js", ".mjs", ".json", ".yml", ".yaml", ".md", ".py", ".css", ".txt", ".html"}:
                    continue
                rel = f.relative_to(ROOT).as_posix()
                if rel in ("src/pages/app-redirect.njk", "tests/test_pwa_install.py"):
                    continue
                if re.search(r"/(es/)?app/", f.read_text(encoding="utf-8", errors="replace")):
                    hits.append(rel)
        return hits

    def test_nothing_left_of_the_old_page(self):
        # no link to /app/ anywhere in the code: only its forwarding stub (and this file) name that address
        self.assertEqual(self.links_to_the_old_page("src", "eleventy", "scripts", "tests", ".github"), [])
        for part in ("footer.njk", "header.njk"):
            self.assertNotIn("nav.app", read("src", "_includes", "partials", part))

    def test_nothing_left_of_the_old_page_in_the_docs_settings_and_content(self):
        # … nor in the documentation, the settings or the content (the committee's files and the docs — left to the
        # Code check: scripts/ops/gate_tests.py CONTENT_TESTS)
        hits = self.links_to_the_old_page("config", "docs", "content")
        if re.search(r"/(es/)?app/", read("README.md")):
            hits.append("README.md")
        self.assertEqual(hits, [])
        self.assertNotIn("pwa-standalone", self.pwa + read("src", "assets", "css", "areas", "pwa.css"))   # it only hid the old links


if __name__ == "__main__":
    unittest.main()
