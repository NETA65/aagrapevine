"""The story recorder on Share your story (/contribute/ and /es/contribute/, #record › the card #recorder), read from its
sources — no build needed: src/pages/contribute.njk, src/_includes/partials/story-recorder.njk (the markup and the
#rec-config JSON), src/assets/js/recorder.js (the screen and the audio engine), src/assets/css/areas/community.css
(cm-rec-*), src/_i18n/community.json (community.recorder.*), eleventy.config.js / package.json (the MP3 encoder),
src/_includes/pwa/sw-core.js and src/assets/js/pwa.js. Its logic (recorder-core.js) has tests/test_recorder_core.py.

  * Page      — contribute.njk loads read.js, recorder-core.js, recorder.js (the core before the screen); the partial is
                included once, inside #record, before the story-line cards (.cm-rec-pair); each card's "Or record it
                yourself" box has a "Record it here" link (JS only) that scrolls to the recorder with its magazine chosen
  * Words     — every word the script writes or announces reaches it: each key recorder.js reads (s.KEY, t("KEY"),
                "e_" + every error, "m_" + every moment crossed() names) and each t('KEY') of the markup is in the
                partial's recSay list, nothing more; each is in src/_i18n/community.json in English and Spanish with the
                same {placeholders}; every state, level, zone, verdict, notice, error and help the script can show has
                its words in the markup — the storage box's (storeNote) and the "This device" line's (keptLine) too; the
                e-mail templates ask only for what
                recorder.js fills in; the numbers the words give are the core's (10 minutes, 80 MB, 20 minutes), and no
                word promises a deletion by age (takes are kept until the visitor deletes them); the storage words promise
                only what holds (a private tab: "at most until you close it"; "reload" only after a copy is kept)
  * Config    — #rec-config has every setting recorder.js reads; the partial reads only fields db.audio_project has;
                La Viña's address follows the cards' rule (links.lv_email_editorial first); the e-mail is in the
                magazine's language (Grapevine English, La Viña Spanish) whatever the page's
  * Component — recorder.js run in Node with a pretend page: it registers "storyRecorder", init() reads #rec-config,
                every method and data name the markup's Alpine attributes use is the component's; the cards' links
                scroll (never a change of address) and set the magazine — not while a take is being made; the message,
                subject and links it builds (the details' heading only over details; La Viña's sentence; the short
                message past the limit); "Safari" is Safari only (install-core.js's list of the other iPhone browsers)
  * Markup    — every element recorder.js looks up (by id, x-ref, data-*) is in the partial; every icon exists
                (lucide-static); every cm-rec-* class has its rules in community.css, and the recorder's own rules style
                nothing else on the page; no class of a page-area stylesheet (tests/test_page_weight.py AREAS)
  * Encoder   — wasm-media-encoders (MIT; LAME inside is LGPL): in package.json and package-lock.json; eleventy.config.js
                copies its two files to /assets/vendor/ (both exist in node_modules), the partial points at them; the
                service worker keeps the .wasm like a script (an MP3 can be made offline after one online use); the
                encoder, called the way recorder.js calls it, makes CBR 128 kbit/s mono MP3 at 44.1 kHz from 48, 44.1,
                24 and 16 kHz, about the size mp3Bytes() says
  * Promises  — nothing is uploaded (no XMLHttpRequest, sendBeacon, POST, WebSocket; fetch only for the encoder), the page's
                address never changes (no location, no history: iOS home-screen apps forget the microphone on a hash
                change — WebKit 215884), no MediaRecorder; pwa.js's busy() knows a take is being made (cm-rec-on), and its
                "Updated — Reload" waits while a take is made or not saved (cm-rec-on / cm-rec-hold); sound is stored as
                bytes, never as Blobs (Safari's private store refuses them); leaving by a link asks in the page
                (window.confirm: an iPhone shows no beforeunload question)
  * Rendered  — the page built in memory (Eleventy, Share your story only, both languages): each sentence of the "This
                device" box has a space before it (once "…when you're done.In a private tab…")
The tests that run JavaScript are skipped without Node.js; the encoder's, the icons' and Rendered without node_modules.

    python -m unittest tests.test_recorder_page -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
# the page-area stylesheets' class prefixes (one list), and the service worker in a pretend world (network, caches)
from test_page_weight import AREAS  # noqa: E402
from test_pwa_worker import HARNESS_JS  # noqa: E402

PAGE = ROOT / "src" / "pages" / "contribute.njk"
PARTIAL = ROOT / "src" / "_includes" / "partials" / "story-recorder.njk"
APP = ROOT / "src" / "assets" / "js" / "recorder.js"
CORE = ROOT / "src" / "assets" / "js" / "recorder-core.js"
CSS = ROOT / "src" / "assets" / "css" / "areas" / "community.css"
STRINGS = ROOT / "src" / "_i18n" / "community.json"
ELEVENTY = ROOT / "eleventy.config.js"
SW_CORE = ROOT / "src" / "_includes" / "pwa" / "sw-core.js"
PWA = ROOT / "src" / "assets" / "js" / "pwa.js"
BUILD_DATA = ROOT / "scripts" / "sync" / "build_data.py"
MODULES = ROOT / "node_modules"
ENCODER = MODULES / "wasm-media-encoders"
PLACEHOLDER = re.compile(r"\{\??(\w+)\}")
# the encoder's two files: node_modules → the site (eleventy.config.js addPassthroughCopy)
VENDOR = {"wasm-media-encoders/dist/umd/WasmMediaEncoder.min.js": "assets/vendor/wasm-media-encoder.min.js",
          "wasm-media-encoders/wasm/mp3.wasm": "assets/vendor/lame-mp3.wasm"}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")      # (a Windows checkout may have CRLF line ends)


def strings() -> dict:
    return json.loads(read(STRINGS))


def strip_js_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\"'\\])//.*$", r"\1", src)


def without_njk_comments(t: str) -> str:
    return re.sub(r"\{#.*?#\}", " ", t, flags=re.S)


def app_code() -> str:
    return strip_js_comments(read(APP))


def partial() -> str:
    return without_njk_comments(read(PARTIAL))


def function_body(src: str, name: str) -> str:
    """A function of the core by name: from `function name(` to the next one."""
    start = src.index(f"function {name}(")
    nxt = src.find("\n  function ", start + 1)
    return src[start:nxt if nxt > 0 else len(src)]


def rec_say() -> list[str]:
    """The words #rec-config carries for the script (the partial's recSay list)."""
    m = re.search(r"\{%-?\s*set recSay = \[(.*?)\]\s*-?%\}", read(PARTIAL), re.S)
    return re.findall(r'"(\w+)"', m.group(1))


def njk_list(src: str, prefix: str) -> list[str]:
    """The names a `{% for k in [...] %}` loop of the partial turns into ("community.recorder." + prefix + k)."""
    for m in re.finditer(r"\{%\s*for (\w+) in \[([^\]]*)\]\s*%\}(.*?)\{%\s*endfor\s*%\}", src, re.S):
        if f'("community.recorder.{prefix}" + {m.group(1)})' in m.group(3):
            return re.findall(r'"(\w+)"', m.group(2))
    raise AssertionError(f"no loop over community.recorder.{prefix}*")


def alpine_attrs(src: str) -> list[tuple[str, str]]:
    """The partial's Alpine attributes: (name, value) of every x-…, :… and @… attribute."""
    return re.findall(r'\s((?:x-|:|@)[\w.:-]+)="([^"]*)"', src)


def script_keys() -> set[str]:
    """The #rec-config words recorder.js reads by name: this.s.KEY, s["KEY"], t("KEY", …), t(a ? "K1" : "K2", …)."""
    code = app_code()
    keys = set(re.findall(r"\b(?:this|self|vm)\.s\.(\w+)", code)) | set(re.findall(r'\b(?:this|self|vm)\.s\[\s*"(\w+)"\s*\]', code))
    for arg in re.findall(r"\bt\(([^,)]*)", code):
        keys |= set(re.findall(r'(?:^|[?:])\s*"(\w+)"', arg.strip()))
    keys.discard("words")                     # init() makes it from the w_* words
    return keys


def markup_keys() -> set[str]:
    """The words the markup asks the component for: t('KEY', …) and t(a ? 'K1' : 'K2') in Alpine attributes."""
    keys = set()
    for _name, value in alpine_attrs(partial()):
        for arg in re.findall(r"(?<![\w.$])t\(([^,)]*)", value):
            keys |= set(re.findall(r"(?:^|[?:])\s*'(\w+)'", arg.strip()))
    return keys


def error_kinds() -> set[str]:
    """Every value recorder.js can put in `error`: R.errorKind's, R.support()'s why, and its own."""
    core = read(CORE)
    kinds = set(re.findall(r'return "(\w+)"', function_body(core, "errorKind")))
    kinds |= set(re.findall(r'why: "(\w+)"', function_body(core, "support")))
    kinds |= set(re.findall(r'\.error = (?:[^;"]*\|\|\s*)?"(\w+)"', app_code()))
    return kinds


def crossed_kinds() -> list[str]:
    return re.findall(r'marks\.push\(\["(\w+)"', function_body(read(CORE), "crossed"))


def split_selectors(sel_list: str) -> list[str]:
    """"a, b:is(c, d)" → ["a", "b:is(c, d)"] (commas inside brackets stay)."""
    out, depth, cur = [], 0, ""
    for ch in sel_list:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return [s for s in out + [cur.strip()] if s]


def limits() -> dict:
    block = read(CORE)
    block = block[block.index("var LIMITS = {"):]
    block = block[:block.index("};")]
    out = {}
    for k, v in re.findall(r"(\w+): ([\d.]+(?: \* \d+)?)", block):
        a, _, b = v.partition(" * ")
        out[k] = float(a) * (float(b) if b else 1)
    return out


class Page(unittest.TestCase):
    def setUp(self):
        self.page = read(PAGE)

    def test_scripts_in_order(self):
        front = yaml.safe_load(self.page.split("---")[1])
        # the core before the screen (recorder.js reads window.GVRec as it loads); read.js stays the page's own
        self.assertEqual(front["pageScripts"], ["/assets/js/read.js", "/assets/js/recorder-core.js", "/assets/js/recorder.js"])

    def test_the_partial_heads_the_record_section(self):
        includes = re.findall(r'\{%-?\s*include\s+"partials/story-recorder\.njk"\s*-?%\}', self.page)
        self.assertEqual(len(includes), 1)
        sec = self.page[self.page.index('<section id="record"'):]
        sec = sec[:sec.index("</section>")]
        self.assertIn(includes[0], sec)                            # #record keeps its id: other pages link to it
        self.assertLess(sec.index(includes[0]), sec.index('<div class="cm-rec-pair">'))   # above the two cards, not inside them
        self.assertLess(sec.index("ui.sectionHead("), sec.index(includes[0]))
        self.assertRegex(sec, r"\{% for p in pubOrder %\}\{\{ recordCard\(p, ap\[p\], lang\) \}\}\{% endfor %\}")   # both cards

    def test_each_card_links_to_the_recorder(self):
        card = self.page[self.page.index("{% macro recordCard(pub, d, lang) %}"):]
        card = card[:card.index("{% endmacro %}")]
        box = card[card.index('"community.rec.diy_title"'):]
        box = box[:box.index("{% endif %}")]                       # the "Or record it yourself" box
        links = re.findall(r"<a\s[^>]*data-rec-go=[^>]*>", box)
        self.assertEqual(len(links), 1)
        a = links[0]
        self.assertIn('data-rec-go="{{ pub }}"', a)               # this card's magazine ("gv" / "lv")
        self.assertIn('href="#recorder"', a)
        self.assertRegex(a, r"\sdata-js-only[\s>]")               # without JavaScript there is no recorder to go to
        self.assertIn('"community.rec.diy_here" | t(lang)', box)
        part = read(PARTIAL)
        self.assertRegex(part, r'<article id="recorder"[^>]*\sdata-js-only[^>]*\sx-data="storyRecorder"')
        self.assertRegex(part, r'<h3 id="recorder-title"[^>]*tabindex="-1"')    # where the link puts the focus
        self.assertRegex(part, r'<p [^>]*data-nojs-only[^>]*>.*"community\.recorder\.nojs"')   # without JavaScript: the other ways


class Words(unittest.TestCase):
    def setUp(self):
        self.s = strings()
        self.say = rec_say()
        self.code = app_code()

    def test_every_word_the_script_needs_is_in_rec_say(self):
        self.assertEqual(len(self.say), len(set(self.say)))
        used = script_keys() | markup_keys()
        # the names put together from a list: "e_" + an error, "m_" + a moment crossed() names
        self.assertIn('s["e_" + this.error]', self.code)
        self.assertIn('s["m_" + k]', self.code)
        used |= {"e_" + k for k in error_kinds()} | {"m_" + k for k in crossed_kinds()}
        # a file that could not be added ("e_" + its kind) and the test's level words ("lv_" + GVRec.level())
        self.assertIn('self.s["e_" + k]', self.code)
        self.assertIn('vm.s["lv_" + lv]', self.code)
        used |= {"e_import_big", "e_import_long", "e_import_bad"} | {"lv_" + k for k in ("silent", "quiet", "good", "loud")}
        self.assertGreater(len(used), 50)
        self.assertEqual(sorted(used - set(self.say)), [], "words the page asks for that #rec-config does not carry (they show empty)")
        self.assertEqual(sorted(set(self.say) - used), [], "words #rec-config carries that nothing reads")

    def test_every_word_exists_in_both_languages(self):
        keys = {"community.recorder." + k for k in self.say}
        part = partial()
        keys |= set(re.findall(r'"(community\.(?:recorder|rec)\.\w+)"\s*\|\s*t\(', part))
        for prefix in ("e_", "help_", "n_", "st_", "p_kept_"):
            keys |= {f"community.recorder.{prefix}{k}" for k in njk_list(part, prefix)}
        keys |= {"community.recorder.mag_gv", "community.recorder.mag_lv"} | {f"community.recorder.credit_{n}" for n in (1, 2, 3)}
        self.assertGreater(len(keys), 150)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertIn(key, self.s)
                v = self.s[key]
                for lang in ("en", "es"):
                    self.assertTrue(isinstance(v.get(lang), str) and v[lang].strip(), f"{key} [{lang}]")
                self.assertEqual(sorted(PLACEHOLDER.findall(v["en"])), sorted(PLACEHOLDER.findall(v["es"])), f"{key}: placeholders differ")

    def test_every_state_the_script_can_be_in_has_its_words(self):
        part = partial()
        core = read(CORE)
        states = set()
        for stmt in re.findall(r"\.state = ([^;]+);", self.code):
            states |= set(re.findall(r'"(\w+)"', stmt))
        self.assertEqual(states, {"idle", "asking", "testing", "countdown", "recording", "paused", "blocked", "saving"})
        for st in states:
            self.assertIn(f"state === '{st}'", part, st)
        for lv in set(re.findall(r'"(\w+)"', function_body(core, "level"))):
            self.assertIn(f"lvl === '{lv}'", part, lv)
        zones = set(re.findall(r'return "(\w+)"', function_body(core, "zone"))) | {"rest"}
        self.assertIn('this.rec() ? R.zone(this.sec, this.ruleOf(E.take ? E.take.pub : this.pub)) : "rest"', self.code)
        self.assertEqual(zones, {"over", "under", "near", "ok", "rest"})
        for z in zones:
            self.assertIn(f"zone() === '{z}'", part, z)
        for v in set(re.findall(r'return "(\w+)"', function_body(core, "verdict"))) - {"none"}:   # no rule known: nothing said
            self.assertIn(f"verdict(take) === '{v}'", part, v)

    def test_every_notice_error_and_help_has_its_words(self):
        part = partial()
        notices = set(re.findall(r'\.notice = "(\w+)"', self.code))
        # ("unsaved": a take Stop, Add a recording or Apply made isn't saved — said by the main button too, r10 A12)
        self.assertEqual(notices, {"silent", "interrupted", "limit", "recovered", "encoder", "low", "blocked", "unsaved"})
        shown = set(njk_list(part, "n_")) | set(re.findall(r"notice === '(\w+)'", part))
        self.assertEqual(sorted(notices - shown), [])
        # where the takes are (storeNote, a lasting box of its own — never the one-at-a-time notice): every state has its words
        note = self.code[self.code.index("storeNote: function () {"):]
        note = note[:note.index("\n        },")]
        states = set(re.findall(r'return (?:[^;]*\? )?"(\w+)"', note)) | set(re.findall(r'\? "(\w+)" : "(\w+)"', note)[0]) - {""}
        self.assertEqual(states, {"none", "reload", "full", "unsaved", "private"})
        self.assertEqual(set(njk_list(part, "st_")) & states, states)
        # how long the browser keeps them ("This device", keptLine): every line it can choose has its words
        kept = self.code[self.code.index("keptLine: function () {"):]
        kept = kept[:kept.index("\n        },")]
        lines = set(re.findall(r'"(\w+)"', kept)) - {"ios"}
        self.assertIn('return this.help === "safari" ? "mac" : "may";', kept)    # (Safari on a Mac: help "safari")
        self.assertEqual(lines, {"private", "yes", "safari", "browser", "mac", "may"})
        self.assertEqual(set(njk_list(part, "p_kept_")), lines)
        self.assertEqual(sorted(error_kinds() - set(njk_list(part, "e_"))), [], "an error the box would show without words")
        helps = set(re.findall(r'return "(\w+)"', function_body(read(CORE), "helpFor")))
        self.assertEqual(helps, {"ios", "android", "firefox", "edge", "chrome", "safari", "other"})
        self.assertEqual(set(njk_list(part, "help_")), helps)

    def test_the_mail_templates_ask_only_for_what_the_script_fills_in(self):
        m = re.search(r"values: function \(t\) \{(.*?)\n        \},", self.code, re.S)
        body = m.group(1).split("var o = {", 1)[1]
        given = set(re.findall(r"(\w+): ", body.split("};", 1)[0])) | set(re.findall(r"\bo\.(\w+) =", body))
        self.assertGreaterEqual(given, {"topic", "length", "file", "name", "phone", "email", "address", "place", "credit", "permission",
                                        "details"})       # (details: the {?details} heading — set when a detail is filled in)
        for pub in ("gv", "lv"):
            for part in ("subject", "subject_plain", "body", "short"):
                key = f"community.recorder.mail_{pub}_{part}"
                for lang in ("en", "es"):
                    with self.subTest(key=key, lang=lang):
                        asked = set(PLACEHOLDER.findall(self.s[key][lang]))
                        # ({?details}: the heading over the details — it shows only when the script says there are some)
                        self.assertEqual(sorted(asked - given), [], "placeholders recorder.js values() never fills in")

    def test_the_words_give_the_cores_numbers(self):
        L = limits()
        mins = {"en": "minutes", "es": "minutos"}
        for lang in ("en", "es"):
            t = {k[len("community.recorder."):]: v[lang] for k, v in self.s.items() if k.startswith("community.recorder.")}
            with self.subTest(lang=lang):
                # nothing is deleted for its age (D6): no "30 days", no "n_expired"
                self.assertNotIn("keepDays", L)
                self.assertNotIn("n_expired", t)
                self.assertNotRegex(t["p_text"], r"\b30\b")
                self.assertIn("{free}", t["n_low"])                                     # the free space, filled in by the script
                self.assertRegex(t["p_kept_safari"], r"\b7\b")                         # Safari's 7-day rule for a tab
                self.assertIn(f"{L['hardStop'] / 60:.0f} {mins[lang]}", t["z_free"])    # every take stops at 10 minutes
                self.assertIn(f"{L['hardStop'] / 60:.0f} {mins[lang]}", t["m_hard"])
                self.assertIn(f"{L['hardStop'] / 60:.0f} {mins[lang]}", t["m_hard_soon"])
                self.assertRegex(t["m_hard_soon"], r"\b30\b")                          # crossed()'s hard_soon: 30 s before
                self.assertIn(f"{L['importBytes'] / 1048576:.0f} MB", t["e_import_big"])
                self.assertIn(f"{L['importSec'] / 60:.0f} {mins[lang]}", t["e_import_long"])
                self.assertIn("{max}", t["n_limit"])                                   # LIMITS.maxTakes, filled in by the script
        self.assertIn('"hard_soon", r.hard - 30', read(CORE))

    def test_the_storage_words_promise_only_what_holds(self):
        """r10's second review (V2–V4, V7, V8): the "This device" box says a closed page loses nothing only where that holds;
        a private tab keeps the takes "at most" until it is closed (on an iPhone maybe not that long); Chrome's Incognito is
        named where the line says "kept until you delete them"; "saved" means on this device — a copy is "download or
        send"; nothing says "reload" without first keeping a copy of a take only in the page (an iPhone asks nothing)."""
        copy = {"en": r"[Dd]ownload\w* or sen[dt]", "es": r"[Dd]escarga\w* o env\w+"}
        for lang in ("en", "es"):
            t = {k[len("community.recorder."):]: v[lang] for k, v in self.s.items() if k.startswith("community.recorder.")}
            with self.subTest(lang=lang):
                # V2: the base sentence ("a closed page or a dropped call doesn't lose them") is its own, not p_text's
                self.assertNotRegex(t["p_text"], {"en": r"\bkept\b|\blose\b", "es": r"guardan|pierden"}[lang])
                self.assertRegex(t["p_kept_base"], {"en": r"doesn't lose them", "es": r"no se pierden"}[lang])
                # (shown without the base sentence before them: they name the takes themselves)
                for k in ("p_kept_private", "p_shared"):
                    self.assertIn({"en": "your takes", "es": "tus tomas"}[lang], t[k], k)
                # V3: a private tab or window — at most until it is closed; on an iPhone Safari may lose them sooner
                for k in ("st_private", "st_private_ios", "p_kept_private"):
                    self.assertIn({"en": "at most", "es": "como mucho"}[lang], t[k], k)
                self.assertIn({"en": "switch to another app", "es": "cambias a otra app"}[lang], t["st_private_ios"])
                # V4: "kept until you delete them" names the windows it does not hold for
                self.assertRegex(t["p_kept_may"], {"en": r"Incognito", "es": r"incógnito"}[lang])
                # V8: the keep switch's question asks for a copy, not to "save" what it removes from the device
                self.assertRegex(t["keep_q"], copy[lang])
                self.assertNotRegex(t["keep_q"], {"en": r"\bsave the one", "es": r"\bguarda la que"}[lang])
                # V7 (as A17 did for t_damaged): every word that says "reload" says to keep a copy first
                for k in ("e_delete", "st_reload", "a_reload_failed"):
                    self.assertRegex(t[k], {"en": r"\breload", "es": r"vuelve a cargar|volver a cargar"}[lang], k)
                    self.assertRegex(t[k], copy[lang], k)
                # V6: a Try again that fails again is not told to tap Try again
                self.assertNotIn(self.s["community.recorder.b_retry"][lang], t["a_damaged_again"])
        part = partial()
        self.assertIn("""x-show="keptLine() && keptLine() !== 'private'" x-cloak>{{ "community.recorder.p_kept_base" | t(lang) }}""", part)


class Config(unittest.TestCase):
    def setUp(self):
        self.part = partial()
        self.code = app_code()
        m = re.search(r"\{%-?\s*set recCfg = \{(.*?)\}\s*-?%\}\n", self.part, re.S)
        self.cfg = m.group(1)

    def test_rec_config_has_what_the_script_reads(self):
        self.assertIn('"s": {', read(PARTIAL))                    # the words, from recSay
        self.assertIn('"d": {', read(PARTIAL))                    # the device check's report words, from recCheck (round 12)
        read_by_script = set(re.findall(r"\bcfg\.(\w+)", self.code)) - {"s", "d"}
        for k in read_by_script:
            self.assertRegex(self.cfg, r"(?<![\w.])" + k + r": ", k)
        # (round 12: topics — "What will you talk about?"; diag — the device check's address and the page's version)
        self.assertEqual(read_by_script, {"enc", "pub", "pubs", "locale", "mail", "credit", "topics", "diag"})
        self.assertRegex(self.cfg, r"enc: \{ js: \"/assets/vendor/wasm-media-encoder\.min\.js\?v=\" ~ build\.version, "
                                   r"wasm: \"/assets/vendor/lame-mp3\.wasm\?v=\" ~ build\.version \}")
        for pub in ("gv", "lv"):
            with self.subTest(pub=pub):
                pubs = re.search(pub + r": \{ (min: [^}]*)\}", self.cfg).group(1)
                self.assertEqual(re.findall(r"(\w+): ", pubs), ["min", "max", "email", "upload", "page", "name"])
                mail = re.search(pub + r": \{ (subject: .*?permission: [^}]*)\}", self.cfg, re.S).group(1)
                self.assertEqual(re.findall(r"(\w+): ", mail), ["subject", "subject_plain", "body", "short", "permission"])
                credit = re.search(pub + r": \[(.*?)\]", self.cfg, re.S).group(1)
                self.assertEqual(re.findall(r'"community\.recorder\.(credit_\d)"', credit), ["credit_1", "credit_2", "credit_3"])
        # the form's "Show my name as" offers the same three (its value is the 1-based index values() reads)
        self.assertRegex(self.part, r'\{% for n in \[1, 2, 3\] %\}<option value="\{\{ n \}\}">\{\{ \("community\.recorder\.credit_" \+ n\) \| t\(lang\) \}\}')
        self.assertIn("(this.cfg.credit[v.pub] || [])[Number(v.credit) - 1]", self.code)

    def test_only_fields_the_audio_data_has(self):
        fields = {}
        for pub, body in re.findall(r'"(gv|lv)": \(([^)]*)\)', read(BUILD_DATA)[read(BUILD_DATA).index("AUDIO_FIELDS = {"):][:800]):
            fields[pub] = set(re.findall(r'"(\w+)"', body))
        self.assertIn("minutes_max", fields["gv"])
        self.assertIn("permission_text", fields["lv"])
        self.assertIn("{%- set dg = ap.gv or {} -%}", self.part)
        self.assertIn("{%- set dl = ap.lv or {} -%}", self.part)
        used = set(re.findall(r"\b(?:dg|dl|d)\.(\w+)", self.part))
        self.assertGreaterEqual(used, {"minutes_min", "minutes_max", "email", "permission_text"})
        # (La Viña gives no minimum: the partial asks for one the same way and gets nothing — 0)
        self.assertEqual(sorted(used - fields["gv"] - fields["lv"]), [])
        self.assertEqual(sorted(set(re.findall(r"\bdg\.(\w+)", self.part)) - fields["gv"]), [])

    def test_la_vinas_address_follows_the_cards_rule(self):
        # the cards: La Viña's recordings go to links.lv_email_editorial (the owner's choice, 2026-10-02) when it is set,
        # else to the address La Viña's page gives; Grapevine's to the Audio Project's own
        page = read(PAGE)
        self.assertIn("{%- set recEmail = (L.lv_email_editorial if (isLv and L.lv_email_editorial) else d.email) -%}", page)
        self.assertIn('{%- set recEmails = { gv: dg.email or "", lv: L.lv_email_editorial or dl.email or "" } -%}', self.part)
        self.assertRegex(self.cfg, r"gv: \{ min: dg\.minutes_min or 0, max: dg\.minutes_max or 0, email: recEmails\.gv,")
        self.assertRegex(self.cfg, r"lv: \{ min: dl\.minutes_min or 0, max: dl\.minutes_max or 0, email: recEmails\.lv,")
        self.assertIn('mailTo: function () { return this.mag().email || ""; }', self.code)
        self.assertIn("mag: function () { return this.cfg.pubs[this.send.pub] || {}; }", self.code)

    def test_the_mail_is_in_the_magazines_language(self):
        # Grapevine reads English, La Viña Spanish: the message goes in the magazine's language from either page
        for k in ("subject", "subject_plain", "body", "short"):
            self.assertIn(f'"community.recorder.mail_gv_{k}" | t("en")', self.cfg)
            self.assertIn(f'"community.recorder.mail_lv_{k}" | t("es")', self.cfg)
        for n in (1, 2, 3):
            self.assertIn(f'"community.recorder.credit_{n}" | t("en")', self.cfg)
            self.assertIn(f'"community.recorder.credit_{n}" | t("es")', self.cfg)
        self.assertRegex(self.cfg, r'(?s)lv: \{ subject: .*permission: dl\.permission_text or "" \}')
        self.assertRegex(self.cfg, r'(?s)gv: \{ subject: [^}]*permission: "" \}')
        # and the page marks it so (a screen reader reads it in that language)
        self.assertIn(""":lang="send.pub === 'lv' ? 'es' : 'en'" x-text="body(take)\"""", self.part)
        self.assertIn(""":lang="send.pub === 'lv' ? 'es' : 'en'" x-text="subject(take)\"""", self.part)
        # the recorder starts on the page language's magazine (pubOrder: La Viña first on the Spanish page)
        self.assertIn("pub: pubOrder[0]", self.cfg)


# recorder.js run in a pretend page: window = the vm's global; the core first, then the script; "alpine:init" registers the
# component. init() reads #rec-config (input.cfg); no microphone, no IndexedDB, no Web Share.
COMPONENT_JS = r"""
import vm from "node:vm";
const reg = {}, on = {}, calls = { focus: [], scroll: [] };
const listen = (where) => (type, fn) => { (on[where + ":" + type] = on[where + ":" + type] || []).push(fn); };
const ctx = vm.createContext({
  console, setTimeout, clearTimeout, setInterval, clearInterval,
  document: {
    addEventListener: listen("doc"), visibilityState: "visible",
    getElementById: (id) => id === "rec-config" ? { textContent: JSON.stringify(input.cfg) }
      : id === "recorder-title" ? { focus: (o) => calls.focus.push(o) } : null,
    documentElement: { classList: { add() {}, remove() {} } },
  },
  navigator: { userAgent: "", maxTouchPoints: 0 }, screen: { width: 1280, height: 800 },
  localStorage: { getItem: () => null, setItem() {} }, matchMedia: () => ({ matches: false }),
  addEventListener: listen("win"), isSecureContext: true,
});
vm.runInContext("var window = globalThis; window.GV = {}; window.Alpine = { data: function (n, f) { window.__reg[n] = f; } };", Object.assign(ctx, { __reg: reg }));
vm.runInContext(fs.readFileSync("src/assets/js/recorder-core.js", "utf8"), ctx, { filename: "recorder-core.js" });
vm.runInContext(fs.readFileSync("src/assets/js/recorder.js", "utf8"), ctx, { filename: "recorder.js" });
(on["doc:alpine:init"] || []).forEach((f) => f());
const C = reg.storyRecorder ? reg.storyRecorder() : null;
const fresh = C ? Object.keys(C) : [];
if (C) { C.$root = { scrollIntoView: (o) => calls.scroll.push(o || null) }; C.$nextTick = (f) => f(); C.init(); }
const R = ctx.GVRec;
const take = (pub, n, extra) => Object.assign({ id: "t" + pub + n, pub, n, name: "", created: Date.parse("2026-10-13T17:00:00Z"), rate: 48000,
  samples: 48000 * 402, peak: 0.5, bins: [], src: "mic", noise: false, starred: false, gaps: false, from: 0, mp3Size: 1, saved: true }, extra || {});
"""


def config_like_the_partial(lang: str = "en") -> dict:
    """What #rec-config holds on the page in `lang` (the partial's recCfg + recSay), with made-up addresses."""
    s = strings()

    def t(k: str, lng: str) -> str:
        return s["community.recorder." + k][lng]
    mail = {pub: {k: t(f"mail_{pub}_{k}", "en" if pub == "gv" else "es") for k in ("subject", "subject_plain", "body", "short")}
            for pub in ("gv", "lv")}
    mail["gv"]["permission"] = ""
    mail["lv"]["permission"] = "Yo, cedo a La Viña los derechos de autor de esta grabación."
    return {
        "lang": lang, "locale": "es-US" if lang == "es" else "en-US", "pub": "lv" if lang == "es" else "gv",
        "enc": {"js": "/assets/vendor/wasm-media-encoder.min.js?v=t1", "wasm": "/assets/vendor/lame-mp3.wasm?v=t1"},
        "pubs": {"gv": {"min": 6, "max": 8, "email": "gv@example.org", "upload": "https://example.org/gv/share", "page": "https://example.org/gv",
                        "name": "Grapevine"},
                 "lv": {"min": 0, "max": 7, "email": "lv@example.org", "upload": "https://example.org/lv/comparte", "page": "https://example.org/lv",
                        "name": "La Viña"}},
        "mail": mail,
        "credit": {"gv": [t(f"credit_{n}", "en") for n in (1, 2, 3)], "lv": [t(f"credit_{n}", "es") for n in (1, 2, 3)]},
        "s": {k: t(k, lang) for k in rec_say()},
    }


JS_WORDS = {"true", "false", "null", "undefined", "const", "let", "var", "if", "else", "return", "typeof", "new", "in", "of", "function",
            "this", "document", "Math", "Number", "String", "Date", "window"}
MAGIC = {"$refs", "$nextTick", "$event", "$root", "$el", "$dispatch", "$watch", "$store"}


class Component(unittest.TestCase):
    def component(self, js: str, lang: str = "en"):
        return run_js(self, COMPONENT_JS + js, data={"cfg": config_like_the_partial(lang)}, needs_modules=False)

    def test_init_and_what_the_markup_uses(self):
        r = self.component(r"""out({ registered: !!C, fresh, keys: Object.keys(C).filter((k) => !k.startsWith("$")),
          methods: Object.keys(C).filter((k) => typeof C[k] === "function"), s: C.s.take, words: C.s.words, pub: C.pub, loaded: C.loaded, kept: C.kept,
          can: C.can, help: C.help, listens: Object.keys(on).sort() });""")
        self.assertTrue(r["registered"])                           # Alpine.data("storyRecorder", …) on alpine:init
        self.assertEqual(r["s"], "Take {n}")                       # init() read #rec-config
        self.assertEqual(r["words"], {"min1": "{n} minute", "min": "{n} minutes", "sec1": "{n} second", "sec": "{n} seconds"})
        self.assertEqual((r["pub"], r["loaded"], r["kept"]), ("gv", True, False))   # no IndexedDB here: the takes live in the page
        self.assertEqual((r["can"]["record"], r["can"]["why"]), ("", "no_media"))
        self.assertEqual(r["help"], "other")
        # nothing on load asks for the microphone or anything else: listeners only
        # (pageshow: Back to this page from the back-forward cache — the list again; focus: a write tried again)
        self.assertEqual(r["listens"], ["doc:alpine:init", "doc:click", "doc:visibilitychange", "win:focus", "win:online", "win:pagehide",
                                        "win:pageshow"])
        names = set(r["fresh"])
        loops = set()
        for name, value in alpine_attrs(partial()):
            m = re.fullmatch(r"\s*\(?(\w+)(?:,\s*(\w+))?\)?\s+in\s+(\w+)\s*", value) if name == "x-for" else None
            if m:
                loops |= {m.group(1), m.group(2)} - {None}
        used_calls, used_names = set(), set()
        for name, value in alpine_attrs(partial()):
            if name in ("x-for", "x-ref", "x-data", "x-cloak"):
                continue
            v = re.sub(r"\{\{.*?\}\}", "0", value)
            v = re.sub(r"'[^']*'", "''", v)
            local = set(re.findall(r"\bconst (\w+)", v))
            used_calls |= set(re.findall(r"(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(", v))
            for tok in re.finditer(r"(?<![\w.$])([A-Za-z_$][\w$]*)(?![\w$])(?!\s*\()(?!\s*:(?!\s*'))", v):
                used_names.add(tok.group(1))
            used_names -= local
        used_names -= JS_WORDS | MAGIC | loops
        used_calls -= JS_WORDS | MAGIC
        self.assertGreater(len(used_calls), 40)
        self.assertEqual(sorted(used_calls - set(r["methods"])), [], "methods the markup calls that the component does not have")
        self.assertEqual(sorted(used_names - names), [], "names the markup reads that the component does not have")
        self.assertEqual(loops, {"take", "m"})

    def test_safari_is_safari_only(self):
        # r10 V1: Safari (its 7-day line, its private-tab check) is not Chrome, Firefox or Edge on an iPad — they send a
        # Mac's address line — nor DuckDuckGo, Opera or Yandex on an iPhone: the same list as install-core.js's IOS_OTHER
        # (its own copy in recorder.js: GVInstall may not have loaded). The cases: tests/test_recorder_store.py Telling.
        other = re.search(r"var IOS_OTHER = (/[^\n]*?/);", read(ROOT / "src" / "assets" / "js" / "install-core.js")).group(1)
        self.assertIn("!" + other + ".test(ua)", self.code_of_init())

    def code_of_init(self) -> str:
        code = app_code()
        start = code.index("init: function () {")
        return code[start:code.index("\n        },", start)]

    def test_the_cards_links_scroll_and_choose_the_magazine(self):
        r = self.component(r"""
          const click = (pub) => { let stopped = false;
            (on["doc:click"] || []).forEach((f) => f({ target: { closest: (sel) => sel === "[data-rec-go]" ? { getAttribute: (a) => a === "data-rec-go" ? pub : null } : null },
                                                      preventDefault: () => { stopped = true; } }));
            return stopped; };
          const other = (() => { let stopped = false; (on["doc:click"] || []).forEach((f) => f({ target: { closest: () => null }, preventDefault: () => { stopped = true; } })); return stopped; })();
          const lv = click("lv"), pubLv = C.pub;
          C.state = "recording"; const busy = click("gv"), pubBusy = C.pub; C.state = "idle";
          const gv = click("gv"), pubGv = C.pub;
          await new Promise((res) => setTimeout(res, 120));
          out({ lv, pubLv, busy, pubBusy, gv, pubGv, other, scroll: calls.scroll, focus: calls.focus });""")
        self.assertTrue(r["lv"])                                   # the link's own jump (a hash change) never happens
        self.assertEqual(r["pubLv"], "lv")
        self.assertEqual(r["pubBusy"], "lv")                       # not while a take is being made
        self.assertEqual(r["pubGv"], "gv")
        self.assertFalse(r["other"])                               # any other click is left alone
        self.assertEqual(len(r["scroll"]), 3)
        self.assertEqual(r["scroll"][0]["block"], "start")
        self.assertTrue(r["focus"])
        self.assertEqual(r["focus"][0], {"preventScroll": True})  # the heading takes the focus without a second jump

    def test_the_message_it_builds(self):
        r = self.component(r"""
          const t = take("gv", 2), l = take("lv", 3);
          const send = (o) => Object.assign(C.send, { pub: "gv", fmt: "mp3", topic: "", name: "", phone: "", email: "", address: "", place: "", credit: "" }, o);
          send({});
          const bare = { body: C.body(t), subject: C.subject(t), to: C.mailTo(), file: C.values(t).file };
          send({ topic: "Gratitude ", name: " Jane Doe", phone: "555-0100", credit: "2" });
          const full = { body: C.body(t), subject: C.subject(t), link: C.mailLink(t, "mailto"), gmail: C.mailLink(t, "gmail").href.slice(0, 80) };
          send({ pub: "lv", topic: "Gratitud", name: "Ana" });
          const lv = { body: C.body(l), subject: C.subject(l), to: C.mailTo(), file: C.values(l).file };
          send({ pub: "gv", fmt: "wav", topic: "x".repeat(900), name: "y".repeat(900) });
          const long = C.mailLink(t, "mailto");
          out({ bare, full, lv, long, short: C.short(t), names: [C.name(t), C.name(take("gv", 4, { name: "Mi toma" }))],
                verdicts: [C.verdict(t), C.verdict(take("gv", 5, { samples: 48000 * 200 })), C.verdict(take("lv", 6, { samples: 48000 * 500 }))],
                marks: [C.markPct("min"), C.markPct("max")], dur: [C.dur(t), C.durSpoken(t)] });""")
        bare, full, lv = r["bare"], r["full"], r["lv"]
        self.assertEqual(bare["to"], "gv@example.org")
        self.assertEqual(bare["subject"], "Audio Project story")
        self.assertEqual(bare["file"], "grapevine-story-2026-10-13-take-2.mp3")
        self.assertIn("Length: 6:42\nFile: grapevine-story-2026-10-13-take-2.mp3", bare["body"])
        self.assertNotIn("in case my story is chosen", bare["body"])        # no details: no heading over them
        self.assertNotIn("{", bare["body"])
        self.assertEqual(full["subject"], "Audio Project story: Gratitude")
        self.assertIn("Topic: Gratitude\n", full["body"])
        self.assertIn("Name: Jane Doe\nPhone: 555-0100\n", full["body"])
        self.assertIn("Please show my name as: " + strings()["community.recorder.credit_2"]["en"], full["body"])
        # the details come under their heading (the template's {?details} line)
        self.assertIn("My contact details, in case my story is chosen:\nName: Jane Doe", full["body"])
        self.assertFalse(full["link"]["cut"])
        self.assertTrue(full["link"]["href"].startswith("mailto:gv@example.org?subject=Audio%20Project%20story%3A%20Gratitude&body=Hello%2C%0D%0A"))
        self.assertTrue(full["gmail"].startswith("https://mail.google.com/mail/?view=cm&fs=1&to=gv%40example.org"))
        # La Viña: its address, in Spanish, its sentence quoted, its file name
        self.assertEqual(lv["to"], "lv@example.org")
        self.assertEqual(lv["subject"], "Graba tu historia: Gratitud")
        self.assertEqual(lv["file"], "la-vina-historia-2026-10-13-toma-3.mp3")
        self.assertIn("«Yo, cedo a La Viña los derechos de autor de esta grabación.»", lv["body"])
        self.assertIn("Nombre completo: Ana", lv["body"])
        self.assertIn("Mis datos, por si mi historia es seleccionada:\nNombre completo: Ana", lv["body"])
        # a message too long for a mailto: link: the short one (the page copies the whole message)
        self.assertTrue(r["long"]["cut"])
        self.assertLessEqual(len(r["long"]["href"]), 1800)
        self.assertIn("grapevine-story-2026-10-13-take-2.wav", r["short"])
        self.assertEqual(r["names"], ["Take 2", "Mi toma"])
        self.assertEqual(r["verdicts"], ["ok", "short", "long"])
        self.assertEqual(r["marks"], [60, 80])                    # Grapevine's 6 and 8 minutes on a bar to 10:00
        self.assertEqual(r["dur"], ["6:42", "6 minutes 42 seconds"])

    def test_the_spanish_page(self):
        r = self.component(r"""out({ pub: C.pub, send: C.send.pub, take: C.t("take", { n: 2 }), spoken: C.durSpoken(take("lv", 1, { samples: 48000 * 61 })),
          marks: [C.markPct("min"), C.markPct("max")] });""", lang="es")
        self.assertEqual((r["pub"], r["send"]), ("lv", "lv"))      # La Viña first on the Spanish page
        self.assertEqual(r["take"], "Toma 2")
        self.assertEqual(r["spoken"], "1 minuto 1 segundo")
        self.assertEqual(r["marks"], [-1, 77.8])                  # La Viña: no minimum, its 7 minutes on a bar to 9:00


class Markup(unittest.TestCase):
    def setUp(self):
        self.part = partial()
        self.code = app_code()

    def test_what_the_script_looks_for_is_there(self):
        for m in re.finditer(r'getElementById\(\s*"([\w-]+)"(\s*\+)?', self.code):
            ident, dynamic = m.group(1), bool(m.group(2))
            with self.subTest(id=ident):
                if dynamic:
                    self.assertRegex(self.part, r""":id="'""" + re.escape(ident) + r"""' \+ take\.id\"""")
                else:
                    self.assertRegex(self.part, r'\sid="' + re.escape(ident) + '"')
        for attr in re.findall(r'querySelectorAll\("\[([\w-]+)\]"\)', self.code):
            self.assertRegex(self.part, r"\s" + attr + r"[\s>]")
        self.assertIn('closest("[data-rec-go]")', self.code)
        for ref in set(re.findall(r"\$refs\.(\w+)", self.part)):
            self.assertIn(f'x-ref="{ref}"', self.part, ref)
        self.assertIn('<script type="application/json" id="rec-config" data-lastmod="skip:diag">', read(PARTIAL))

    def test_every_icon_exists(self):
        lucide = MODULES / "lucide-static" / "icons"
        local = ROOT / "src" / "_includes" / "icons"
        if not lucide.is_dir():
            self.skipTest("node_modules (lucide-static) is not installed")
        names = set(re.findall(r'\{%-?\s*icon\s+"([a-z0-9-]+)"', self.part))
        names |= set(re.findall(r'recCheck\([^)]*?,\s*"([a-z0-9-]+)"\)', self.part))
        names |= set(re.findall(r'macro recCheck\(text, icon="([a-z0-9-]+)"\)', self.part))
        page = read(PAGE)
        link = page[page.index("data-rec-go="):]
        names |= set(re.findall(r'\{%\s*icon\s+"([a-z0-9-]+)"', link[:link.index("</a>")]))
        self.assertGreater(len(names), 30)
        for name in sorted(names):
            with self.subTest(icon=name):
                self.assertTrue((lucide / f"{name}.svg").exists() or (local / f"{name}.svg").exists(), name)

    def test_the_classes_have_their_rules(self):
        css = read(CSS)
        used = set(re.findall(r"(?<![\w-])(cm-rec[a-z0-9-]*)", self.part))
        self.assertGreater(len(used), 25)
        for c in sorted(used):
            with self.subTest(cls=c):
                self.assertRegex(css, r"\." + re.escape(c) + r"(?![\w-])", "a class with no rule in community.css")

    def test_the_recorders_rules_style_nothing_else(self):
        """The story-line cards right below the recorder have cm-rec-* classes of their own (cm-rec-pair, cm-rec-body,
        cm-rec-foot …): a rule of the recorder's part of community.css whose class is also used elsewhere must reach
        only inside the recorder (.cm-recorder …)."""
        css = read(CSS)
        block = re.sub(r"/\*.*?\*/", "", css[css.index("The story recorder ("):], flags=re.S)
        own = set(re.findall(r"\.(cm-rec[a-z0-9-]*)", block))
        self.assertIn("cm-recorder", own)
        elsewhere = {}
        for p in list((ROOT / "src").rglob("*.njk")) + list((ROOT / "src" / "assets" / "js").glob("*.js")) + list((ROOT / "eleventy").rglob("*.js")):
            if p in (PARTIAL, APP):
                continue
            text = without_njk_comments(read(p))
            for c in own:
                if re.search(r"(?<![\w-])" + re.escape(c) + r"(?![\w-])", text):
                    elsewhere.setdefault(c, []).append(p.relative_to(ROOT).as_posix())
        loose = {}
        for sel_list in re.findall(r"([^{};]+)\{", block):
            if sel_list.strip().startswith("@"):
                continue
            for sel in split_selectors(sel_list):
                for c in elsewhere:
                    if re.search(r"\." + re.escape(c) + r"(?![\w-])", sel) and not re.match(r"\.cm-recorder[\s>]", sel):
                        loose.setdefault(c, {"used in": elsewhere[c], "rules": []})["rules"].append(sel)
        self.assertEqual(loose, {}, "the recorder's rules (community.css) would also style these")

    def test_no_page_area_classes(self):
        area = re.compile(r"(?<![\w-])(" + "|".join(re.escape(p) for p in AREAS.values()) + r")[a-z0-9]")
        for p in (APP, CORE, PARTIAL):
            with self.subTest(file=p.name):
                self.assertEqual(area.findall(read(p)), [], "a page-area stylesheet's prefix (mp-, rp-, xp-, …): main.css has no rules for it")


class Encoder(unittest.TestCase):
    def test_the_package(self):
        pkg = json.loads(read(ROOT / "package.json"))
        self.assertIn("wasm-media-encoders", pkg["devDependencies"])
        lock = json.loads(read(ROOT / "package-lock.json"))
        entry = lock["packages"]["node_modules/wasm-media-encoders"]
        self.assertEqual((entry["version"], entry["license"]), ("0.7.0", "MIT"))      # LAME 3.100 inside is LGPL (credited)
        self.assertIn("wasm-media-encoders", lock["packages"][""]["devDependencies"])

    def test_copied_to_the_site_and_pointed_at(self):
        conf = read(ELEVENTY)
        for src, dest in VENDOR.items():
            with self.subTest(file=dest):
                self.assertIn(f'[nm("{src}")]: "{dest}",', conf)
                self.assertIn(f'"/{dest}?v=" ~ build.version', read(PARTIAL))
                if MODULES.is_dir():
                    self.assertTrue((MODULES / src).is_file(), f"node_modules/{src} (npm ci)")
        # fetched through GV.url (the site's base path: the JSON in #rec-config is not rewritten by the build)
        self.assertIn("var at = function (p) { return GV.url ? GV.url(p) : p; };", app_code())

    def test_the_worker_keeps_it(self):
        sw = read(SW_CORE)
        static = [line for line in sw.splitlines() if 'staleWhileRevalidate(event, url, "static")' in line]
        self.assertEqual(len(static), 1)
        self.assertIn("wasm", static[0])
        r = run_js(self, HARNESS_JS + r"""
          const w = world();
          const WASM = B + "assets/vendor/lame-mp3.wasm?v=t1", LIB = B + "assets/vendor/wasm-media-encoder.min.js?v=t1";
          w.page(WASM, { body: "WASM", ct: "application/wasm" });
          w.page(LIB, { body: "/* lib */", ct: "text/javascript" });
          const first = [await w.request(WASM), await w.request(LIB)].map((x) => x && x.body);
          w.net.delete(ORIGIN + WASM); w.net.delete(ORIGIN + LIB);         // offline
          const offline = [await w.request(WASM), await w.request(LIB)].map((x) => x && x.body);
          const kept = [];
          for (const n of w.store.keys()) for (const u of (await w.keys(n)) || []) if (/lame-mp3/.test(u)) kept.push(n + " " + u.slice(ORIGIN.length));
          out({ first, offline, kept });
        """, needs_modules=False, env={"PATH_PREFIX": "/aagrapevine/"}, timeout=120)
        self.assertEqual(r["first"], ["WASM", "/* lib */"])
        self.assertEqual(r["offline"], ["WASM", "/* lib */"])     # the second time, with no network: from the static cache
        self.assertEqual(len(r["kept"]), 1)
        self.assertRegex(r["kept"][0], r"^gvlv-static-\S+ /aagrapevine/assets/vendor/lame-mp3\.wasm\?v=t1$")

    def test_it_makes_the_mp3_recorder_js_asks_for(self):
        for src in VENDOR:
            if not (MODULES / src).is_file():
                self.skipTest("node_modules (wasm-media-encoders) is not installed")
        code = app_code()
        # how recorder.js calls it: the module compiled once (its callback), then an encoder from it for each take
        self.assertIn('window.WasmMediaEncoder.createEncoder("audio/mpeg", buf, function (m) { encMod = m; })', code)
        self.assertIn('window.WasmMediaEncoder.createEncoder("audio/mpeg", encMod)', code)
        self.assertIn("enc.configure({ sampleRate: rate, channels: 1, bitrate: L.mp3Kbps, outputSampleRate: L.mp3Rate });", code)
        r = run_js(self, r"""
          import vm from "node:vm";
          const ctx = vm.createContext({ console });
          vm.runInContext(fs.readFileSync("src/assets/js/recorder-core.js", "utf8"), ctx);
          vm.runInContext(fs.readFileSync("node_modules/wasm-media-encoders/dist/umd/WasmMediaEncoder.min.js", "utf8"), ctx);
          const W = ctx.WasmMediaEncoder, R = ctx.GVRec, L = R.LIMITS;
          const bytes = fs.readFileSync("node_modules/wasm-media-encoders/wasm/mp3.wasm");
          let mod = null;
          await W.createEncoder("audio/mpeg", bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), (m) => { mod = m; });
          const F = vm.runInContext("Float32Array", ctx), I = vm.runInContext("Int16Array", ctx);
          const res = {};
          for (const rate of [48000, 44100, 24000, 16000]) {
            const enc = await W.createEncoder("audio/mpeg", mod);
            enc.configure({ sampleRate: rate, channels: 1, bitrate: L.mp3Kbps, outputSampleRate: L.mp3Rate });
            // 10 s of a voice-like tone, as 16-bit PCM encoded a second at a time (encodePcm)
            const pcm = new I(rate * 10);
            for (let i = 0; i < pcm.length; i++) pcm[i] = Math.round(12000 * Math.sin(2 * Math.PI * 220 * i / rate) * (0.6 + 0.4 * Math.sin(i / rate)));
            const parts = [];
            for (let p = 0; p < pcm.length; p += rate) parts.push(new Uint8Array(enc.encode([R.toFloat32(pcm.subarray(p, Math.min(pcm.length, p + rate)))])));
            parts.push(new Uint8Array(enc.finalize()));
            const all = Buffer.concat(parts);
            res[rate] = { size: all.length, head: [...all.slice(0, 4)] };
          }
          out({ res, expect: R.mp3Bytes(10) });""", needs_modules=False, timeout=120)
        for rate, got in r["res"].items():
            with self.subTest(rate=rate):
                b = got["head"]
                self.assertEqual((b[0], b[1] & 0xFE), (0xFF, 0xFA))      # an MPEG-1 Layer III frame
                self.assertEqual(b[2] >> 4, 9)                          # 128 kbit/s (bit-rate index 9)
                self.assertEqual((b[2] >> 2) & 3, 0)                    # 44.1 kHz, whatever the microphone's rate
                self.assertEqual(b[3] >> 6, 3)                          # mono
                self.assertAlmostEqual(got["size"] / r["expect"], 1, delta=0.02)   # the size mp3Bytes() promises


class Promises(unittest.TestCase):
    def setUp(self):
        self.code = app_code()

    def test_nothing_is_uploaded(self):
        self.assertNotRegex(self.code, r"XMLHttpRequest|sendBeacon|WebSocket|EventSource|\bmethod\s*:|[\"']POST[\"']|new Image\b")
        # fetch() only for the encoder's .wasm, a <script> only for its library — both the site's own files
        self.assertEqual(re.findall(r"\bfetch\((.*?\))\)", self.code), ["at(cfg.enc.wasm)"])
        self.assertEqual(self.code.count("fetch("), 1)
        self.assertEqual(self.code.count("loadScript("), 2)       # its definition and one call
        self.assertIn("loadScript(at(cfg.enc.js))", self.code)
        # (s.src = src: that script; E.src is the microphone's node in the audio graph; a.src = url: an <audio> that
        # reads the length of the visitor's own file, through a blob: address of that file — nothing leaves the device)
        self.assertEqual(re.findall(r"(\w+)\.src\s*=", self.code).count("s"), 1)
        self.assertEqual(set(re.findall(r"(\w+)\.src\s*=", self.code)), {"s", "E", "a"})
        self.assertIn("url = URL.createObjectURL(file)", self.code)
        self.assertIn("a.src = url;", self.code)
        # what the visitor types (name, phone, address…) goes into the message only: never stored, never sent by the page
        self.assertNotRegex(self.code, r"(lsSet|setItem)\([^)]*send\b")

    def test_the_address_never_changes(self):
        # iOS home-screen apps forget the microphone permission on a hash change (WebKit 215884): the recorder scrolls
        self.assertNotRegex(self.code, r"\blocation\b|\bhistory\.|\.hash\b|pushState|replaceState")
        self.assertIn("scrollIntoView", self.code)
        for name, value in alpine_attrs(partial()):
            self.assertNotRegex(value, r"\blocation\b|\bhistory\.|\.hash\b", name)

    def test_no_media_recorder(self):
        # MediaRecorder gives WebM (Chrome, Firefox) or MP4 (Safari): the magazines take WAV and MP3
        self.assertNotIn("MediaRecorder", self.code)
        self.assertIn("audioWorklet.addModule", self.code)
        self.assertIn("createScriptProcessor(4096, 1, 1)", self.code)

    def test_the_page_knows_a_take_is_being_made(self):
        pwa = read(PWA)
        busy = pwa[pwa.index("function busy()"):]
        busy = busy[:busy.index("\n  }\n")]
        self.assertIn('c.contains("cm-rec-on")', busy)            # no install prompt over a take
        # and no "Updated — Reload" while a take is made or not saved on the device: held, shown once the recorder lets go,
        # its Reload never run meanwhile (an iPhone never asks before a reload — NS-5)
        self.assertIn('function recHeld() { return root.classList.contains("cm-rec-on") || root.classList.contains("cm-rec-hold"); }', pwa)
        kind = pwa[pwa.index("function toastKind()"):pwa.index("function measure(")]
        self.assertIn('if (state.waiting && !recHeld()) return "update";', kind)
        self.assertIn('if (state.waiting) return "";', kind)
        self.assertIn('else if (act === "update" && state.waiting && !recHeld()) {', pwa)
        self.assertIn("if (wantReload && recHeld()) { wantReload = false; renderToast(); return; }", pwa)
        self.assertIn("if (state.waiting) renderToast();", pwa)
        guard = self.code[self.code.index("guard: function () {"):]
        guard = guard[:guard.index("\n        },")]
        self.assertIn('root.classList[need ? "add" : "remove"]("cm-rec-hold")', guard)
        self.assertIn("need = this.atRisk()", guard)
        self.assertIn('document.documentElement.classList.add("cm-rec-on");', self.code)
        self.assertIn('document.documentElement.classList.remove("cm-rec-on");', self.code)
        begin = self.code[self.code.index("begin: function () {"):]
        self.assertIn('classList.add("cm-rec-on")', begin[:begin.index("\n        },")])
        close = self.code[self.code.index("close: function () {"):]
        self.assertIn('classList.remove("cm-rec-on")', close[:close.index("\n        },")])
        # and a page left mid-take asks first: beforeunload (a computer, Android) and, for a link, in the page (an iPhone
        # shows no beforeunload question) — a capture listener, a confirm, R.leaves deciding which links leave
        self.assertIn('window.addEventListener("beforeunload", E.leave);', self.code)
        self.assertIn('document.addEventListener("click", function (e) { self.askLeave(e); }, true);', self.code)
        ask = self.code[self.code.index("askLeave: function (e) {"):]
        ask = ask[:ask.index("\n        },")]
        self.assertIn("R.leaves(", ask)
        self.assertIn("window.confirm(", ask)
        self.assertIn("e.preventDefault()", ask)

    def test_the_sound_is_stored_as_bytes(self):
        # Safari's private store (and sometimes a normal tab) refuses every Blob value in IndexedDB (WebKit 156347,
        # 188438): what goes to the device is ArrayBuffers — rows {k, id, kind, seq, buf} — and records
        code = self.code
        idb = code[code.index("function idb() {"):code.index("function readSound(c, both) {")]
        self.assertIn('d.createObjectStore("sound", { keyPath: "k" })', idb)
        self.assertNotRegex(idb, r'createObjectStore\("(pcm|mp3|parts)"')       # a v2 database has only takes and sound
        # opened at R.SCHEMA — or at the version a mend raised it to (a store was missing: one version up, r10 A10)
        self.assertIn("indexedDB.open(R.DB_NAME, ver)", idb)
        self.assertIn("open(E.dbv || R.SCHEMA, 0);", idb)
        self.assertIn("buf: a === 0 && b === buf.byteLength ? buf : buf.slice(a, b)", idb)
        for put in re.findall(r"\.put\(([^)]*)\)", code):
            with self.subTest(put=put):
                self.assertNotRegex(put, r"\bblob\b|new Blob")
        self.assertNotRegex(code, r"\bblob: (?!.*bufferOf)")                     # no record carries a Blob
        # and nothing goes by itself: no deletion by age, no db.clear() (Delete all and the switch drop takes by id)
        self.assertNotRegex(code, r"expired|keepDays|\.clear\(\)\.then|db\.clear")


class Rendered(unittest.TestCase):
    def test_the_this_device_box_reads_as_sentences(self):
        """r10 V2: Share your story built in memory (Eleventy, only that page, both languages): in the "This device" box each
        sentence the script may show is an element of its own with a space before it — a whitespace-trimming tag around
        them once glued "…when you're done.In a private tab…" (ES "…al terminar.En una pestaña…")."""
        s = strings()
        r = run_js(self, r"""
          const os = await import("node:os");
          process.env.ONLY = "contribute";
          const { Eleventy } = await import("@11ty/eleventy");
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-rec-render-"));
          try {
            const pages = await new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" }).toJSON();
            const res = {};
            for (const [lang, url] of [["en", "/contribute/"], ["es", "/es/contribute/"]]) {
              const c = (pages.find((p) => p.url === url) || {}).content || "";
              const i = c.indexOf(input.title[lang] + "</p>");
              res[lang] = { found: i >= 0, box: i < 0 ? "" : c.slice(i, c.indexOf("</p>", i + input.title[lang].length + 4) + 4),
                glued: ["done.<span", "terminar.<span"].filter((g) => c.includes(g)) };
            }
            out(res);
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }""",
                   data={"title": {lang: s["community.recorder.p_title"][lang] for lang in ("en", "es")}}, timeout=240)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                v = r[lang]
                self.assertTrue(v["found"], "no \"This device\" box on the page")
                self.assertEqual(v["glued"], [])
                box = v["box"]
                body = box[box.index("<p "):]
                spans = re.findall(r"<span\b", body)
                self.assertGreaterEqual(len(spans), 10)                  # base, six kept lines, shared computer, two iPhone lines
                self.assertEqual(re.findall(r"\S<span\b", body), [], "a sentence glued to the one before it")
                text = re.sub(r"<[^>]+>", "", body)
                self.assertIn(s["community.recorder.p_text"][lang], text)
                self.assertIn(s["community.recorder.p_kept_base"][lang].replace("'", "&#39;"), text)


if __name__ == "__main__":
    unittest.main()
