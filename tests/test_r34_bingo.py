"""Round 34 · the GVR / RLV corner's bingo cards (/gvr/bingo/ and /es/gvr/bingo/, src/pages/gvr-bingo.njk; the /gvr/
teaser #bingo, src/pages/gvr.njk) — the offline checks: what a real build writes, the cards' logic run in Node.js, and
the words. The squares' file itself (content/bingo/bingo.csv, its checker eleventy/filters/bingo.js) has
tests/test_bingo_csv.py; what a browser draws, fits and prints is tests/browser/test_r34_bingo.py.

  * Built       — both pages as the build writes them: the page language, the title, the description, the canonical
                  address and the hreflang pair, the breadcrumb search engines read (Home › GVR / RLV corner ›
                  Grapevine & La Viña Bingo), the menu showing the GVR / RLV corner as the current page, the scripts
                  and the stylesheet; #bingo-data parses and holds exactly the build's squares and facts (the `bingo`
                  global: each meeting's long, mid and short lines, or none), the categories and occasions, the CARD
                  words in BOTH languages and the builder's words — no <, > or & in it (the pool's markup squares
                  written as escapes, their words given back exactly); no unfilled {placeholder} where a reader can
                  see it; no element or script of those squares on any of the four pages (their words escaped).
  * Sample      — the card the page shows and prints without JavaScript: 5×5 in the page's language, game code GV65,
                  FREE in the middle, no square twice, as many information squares as the cap gives (DEFAULTS.infoMax
                  is 3: the pinned ones first) — square for square the card bingo-core.js draws in Node from the
                  page's own squares, the markup squares as words; its head, name lines, meetings strip (the long
                  meeting lines, the e-mail, the QR code of its language), anonymity note and "Card 1 of 1 · Game
                  GV65".
  * Teaser      — /gvr/'s #bingo: after #ideas and before #pass-it-on, its chip in the page nav, its words and the
                  one button to the bingo page of each language, the decorative 3×3 card the core draws (the short
                  words: dense), word for word.
  * Found       — the page in both search indexes (page:gvr-bingo) and in the sitemap with its hreflang pair.
  * Settings, Pool, Draw, Link, Module — src/assets/js/bingo-core.js (window.GVBingo) in Node, in a vm context as
                  eleventy/filters/bingo-sample.js bingoCore() runs it, on squares of its own (FIXTURE: the committee
                  may edit the real file any day): normalize never throws on junk; the pool follows THE POOL's rules
                  (an independent copy of them here: language, date window, pick, pin, magazine, occasion,
                  category), and so does the pick list (pickRows: "always" only on a square in use); the same code
                  and settings give the same cards, another card or code others; never a square twice; rows × cols
                  squares; pins and the information cap; FREE only on odd × odd, in the middle; too few squares →
                  { error: "short", have, need }; the short words on big grids and small squares, and the page's own
                  measured choice (opts.dense) over the core's estimate; poolCells (every square a run may draw, as
                  card() draws it: what the page measures for its 6 pt floor); {event} filled in as typed ("$&" too); a
                  link gives the very same settings back, a bad or hostile one is ignored; the module's shape and its
                  plain-script syntax; an address breaks at the same places in the builder, the core and the no-JS
                  sample; a long typed piece of the head (a pasted link, an e-mail, a hashtag) may break after its "/",
                  ".", "@", "-" or "_" and between its words (headPieces), a short one never. Seeded loops of a few
                  hundred cases: the same cases on every run.
  * Strings     — every bingo.* key the page, the teaser and the builder's script use is there with English AND
                  Spanish words (tests/test_i18n_keys.py checks the files' shape and placeholders; the build's
                  I18N_STRICT cannot see the words the script reads through tGroup), each {placeholder} of the
                  script's words is one the script fills in, the core's own WORDS are the page's card words, and the
                  AA wording (no money asks, first names only, La Viña first in Spanish).
  * RealContent — the committee's file and settings as they are today (CONTENT_TESTS, scripts/ops/gate_tests.py), in
                  a build of their own: at least 200 squares on the page, the e-mail grapevine@neta65.org, both
                  meetings' lines on the page (the long ones with the time zone and the place), the three squares
                  pinned "Always on every card" on the default card in both languages, and that sample card square
                  for square the core's, its words at 6 pt or more on paper (at its print zoom).

The builds: Eleventy with the site's own config and data, the day fixed (MONTHLY_NOW = DAY: the sample card is the
same on any day the tests run). The one every class but RealContent reads: ONLY the GVR / RLV corner's pages (gvr.njk,
gvr-bingo.njk), the search indexes and the sitemap, its squares the fixture pool tests/fixtures/bingo_csv/pool.csv
(BINGO_CSV: 48 rows copied from the real file and three pinned squares whose words are markup) — so the tests the
publishing gate runs never judge the committee's file (docs/OPERATIONS.md). RealContent's: the bingo pages alone, from
content/bingo/bingo.csv. A few seconds each. Skipped without Node.js or the site's npm packages (npm ci); CI's tests
job has both.

    python -m unittest tests.test_r34_bingo -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import random
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

CORE = "src/assets/js/bingo-core.js"
APP = ROOT / "src" / "assets" / "js" / "bingo.js"
PAGE = ROOT / "src" / "pages" / "gvr-bingo.njk"
GVR = ROOT / "src" / "pages" / "gvr.njk"
LANGS = ("en", "es")
BINGO = {"en": "/gvr/bingo/", "es": "/es/gvr/bingo/"}
CORNER = {"en": "/gvr/", "es": "/es/gvr/"}
INDEX = {"en": "/search-index.json", "es": "/es/search-index.json"}
# the build's day (a Wednesday): the sample card's squares and date line
DAY = "2026-11-18"
SAMPLE_CODE = "GV65"
# the no-JS sample's smallest square size (src/pages/gvr-bingo.njk sampleCard): 6 pt on paper at its print zoom
SAMPLE_FLOOR = 6.5
# the squares the build reads (BINGO_CSV) for every class but RealContent: a good file of the CSV checker's fixtures
# (tests/test_bingo_csv.py Fixtures) — 48 rows copied from the real file and the three pinned squares below, whose
# words are markup: the pages must print them as words ({id: (text, label)}, the same in both languages)
POOL = ROOT / "tests" / "fixtures" / "bingo_csv" / "pool.csv"
MARKUP = {"fun-markup-script": ("</script><script>__h1=1</script>", ""),
          "fun-markup-at": ('a@b"><img src=x onerror=__h2=1>', "<b onclick=__h3=1>L</b>"),
          "fun-markup-entity": ("&lt;b&gt; & &amp; <i>it</i> 'q' $&", "")}

# the core's lists (bingo-core.js; eleventy/filters/bingo.js has the same)
CATS = ["people", "read", "write", "listen", "service", "meetings", "history", "fun"]
WHERES = ["group", "district", "assembly", "acm", "workshop", "booth", "committee", "online"]
MARKS = {"check": "tick", "name": "line", "phone": "line", "write": "line", "sign": "box", "info": "icon", "free": "free"}
# (the Spanish ones short enough for one line in the smallest squares, at 6 pt: round 34, r3 text-below-6pt)
LABEL_DEFAULT = {"en": {"name": "Name & group", "phone": "Name & phone", "write": "Answer", "sign": "Initials"},
                 "es": {"name": "Nombre/grupo", "phone": "Nombre y tel.", "write": "Respuesta", "sign": "Iniciales"}}
CELL_KEYS = ["id", "free", "type", "cat", "pub", "pin", "mark", "text", "label"]
VALID_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CODE = re.compile(r"^[A-HJ-NP-Z2-9]{4,6}$")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def i18n() -> dict:
    """Every string of src/_i18n, as the build merges them."""
    out: dict = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        out.update(json.loads(read(f)))
    return out


def group(strings: dict, prefix: str, lang: str) -> dict:
    """eleventy.config.js tGroup: every string under the prefix, the prefix taken off."""
    return {k[len(prefix):]: v[lang] for k, v in strings.items() if k.startswith(prefix) and len(k) > len(prefix)}


# ------------------------------------------------------------------------------------------------ the squares
def square(sid: str, typ: str, cat: str, *, pub: str = "both", where=(), pin: bool = False, weight: float = 1,
           frm: str | None = None, until: str | None = None, langs=LANGS, text: dict | None = None,
           label: dict | None = None) -> dict:
    """One item as bingo.items has it (eleventy/filters/bingo.js loadBingo): a language it is not offered in is ""."""
    words = text or {"en": f"Square {sid}: words long enough for a big square", "es": f"Casilla {sid}: palabras para una casilla grande"}
    short = {"en": f"Short {sid}", "es": f"Corta {sid}"}
    lab = label or {"en": "", "es": ""}
    return {"id": sid, "type": typ, "pub": pub, "cat": cat, "where": list(where), "pin": pin, "weight": weight,
            "from": frm, "until": until,
            "text": {L: words[L] if L in langs else "" for L in LANGS},
            "short": {L: short[L] if L in langs else "" for L in LANGS},
            "label": {L: lab[L] if L in langs else "" for L in LANGS}}


PINNED_INFO = ["meetings-gvm", "meetings-cm", "meetings-mail"]
OTHER_INFO = ["meetings-site", "meetings-gv-weekly", "meetings-lv-weekly", "meetings-find", "meetings-workshop"]


def make_fixture() -> list[dict]:
    """136 squares of every type, magazine, occasion and weight (enough for a 10×10 card in both languages): three
    information squares pinned (like the real file's meetings and e-mail) and five more, one plain square pinned,
    dated ones, one-language ones, one with {event} twice, one in a category the core does not list."""
    types = ["check", "name", "phone", "write", "sign"]
    items = []
    for i in range(120):
        cat = CATS[i % 8]
        typ = types[(i // 2) % 5]
        where = [[], [WHERES[i % 8]], [WHERES[i % 8], WHERES[(i + 3) % 8]], []][(i // 5) % 4]
        label = {"en": "Their tip", "es": "Su consejo"} if typ == "write" and i % 4 == 0 else None
        items.append(square(f"{cat}-sq-{i:03d}", typ, cat, pub=["both", "gv", "both", "lv"][(i // 3) % 4], where=where,
                            weight=[1, 1, 2, 0.5, 5, 1, 1.5][i % 7], label=label))
    items.append(square("people-always", "name", "people", pin=True))
    items += [square(i, "info", "meetings", pin=True) for i in PINNED_INFO]
    items += [square(i, "info", "meetings", pub=["both", "gv", "lv", "gv", "both"][n], where=[[], [], [], ["online"], ["workshop"]][n])
              for n, i in enumerate(OTHER_INFO)]
    items += [square("fun-december", "check", "fun", frm="2026-12-01", until="2026-12-31"),
              square("fun-from-2027", "check", "fun", frm="2027-01-01"),
              square("fun-until-nov", "check", "fun", until="2026-11-30"),
              square("read-en-only", "check", "read", langs=("en",)),
              square("read-es-only", "check", "read", langs=("es",)),
              square("fun-event", "check", "fun", text={"en": "Meet someone new at {event}, then again at {event}",
                                                        "es": "Conoce a alguien nuevo en {event}"}),
              square("games-new", "check", "games")]
    return items


FIXTURE = make_fixture()
FIXTURE_IDS = [it["id"] for it in FIXTURE]
# not squares (the core leaves them out: why → "bad"), and an id twice (the first one counts)
BAD_ITEMS = [None, {}, {"id": "Bad Id", "type": "check", "text": {"en": "x", "es": "x"}},
             {"id": "ok-free", "type": "free", "text": {"en": "x", "es": "x"}},
             {"id": "ok-nope", "type": "nope", "text": {"en": "x", "es": "x"}},
             {**square("people-sq-000", "check", "fun"), "text": {"en": "the same id again", "es": "otra vez"}}]


def expected_reason(it, s: dict) -> str | None:
    """THE POOL's rules (bingo-core.js's header), written again here: why a square may not be on the card (None: it
    may), on normalized settings."""
    if not isinstance(it, dict) or not isinstance(it.get("id"), str) or len(it["id"]) > 48 or not VALID_ID.match(it["id"]) \
            or it.get("type") not in MARKS or it.get("type") == "free":
        return "bad"
    text = it.get("text") if isinstance(it.get("text"), dict) else {}
    if not str(text.get(s["lang"]) or "").strip():
        return "lang"
    frm, until = it.get("from") or "", it.get("until") or ""
    if (frm or until) and (not s["date"] or (frm and s["date"] < frm) or (until and s["date"] > until)):
        return "date"
    if s["pick"].get(it["id"]) == 0:
        return "off"
    if s["pick"].get(it["id"]) == 1 or s["pin"].get(it["id"]) == 1:
        return None
    pub = it.get("pub") if it.get("pub") in ("both", "gv", "lv") else "both"
    if s["pub"] != "both" and pub not in ("both", s["pub"]):
        return "pub"
    where = [w for w in it.get("where") or [] if isinstance(w, str)]
    if s["where"] != "any" and where and s["where"] not in where:
        return "where"
    if s["cats"].get(str(it.get("cat") or "")) is False:
        return "cat"
    return None


def expected_pool(items: list, s: dict) -> dict:
    """The pool's lists and counts by the rules above (the first square of an id counts)."""
    seen, pool, pinned, info, rest = set(), [], [], [], []
    for it in items:
        if expected_reason(it, s) is not None or it["id"] in seen:
            continue
        seen.add(it["id"])
        pool.append(it["id"])
        is_pinned = s["pin"].get(it["id"]) == 1 or (it.get("pin") is True and s["pin"].get(it["id"]) != 0)
        if is_pinned:
            pinned.append(it["id"])
        if it["type"] == "info":
            info.append(it["id"])
        elif not is_pinned:
            rest.append(it["id"])
    free = s["free"] and s["rows"] % 2 == 1 and s["cols"] % 2 == 1
    need = s["rows"] * s["cols"] - (1 if free else 0)
    by_id = {it["id"]: it for it in items if isinstance(it, dict) and it.get("id") in seen}
    pinned_plain = [i for i in pinned if by_id[i]["type"] != "info"]
    take = min(len(info), s["infoMax"])
    have = len(pinned_plain) + take + len(rest)
    return {"pool": pool, "pinned": pinned, "pinnedPlain": pinned_plain, "info": info, "rest": rest, "need": need,
            "have": have, "infoTake": take, "free": free, "ok": have >= need}


# typed words a link must carry as typed: & = # % + in them, accents, emoji, other scripts, line breaks, too long
TEXTS = ["", "Spring Assembly 2027", "Asamblea de Primavera — Tyler", "A & B = C # 100% + more", "50%25 off?%", "a=b&c=d#e",
         "Año nuevo: ñ é ü ¿? ¡!", "grapes 🍇 and vines", "日本語のテキスト", "  spaces  inside  ", "line\none", "tab\there",
         "x" * 70, "🍇" * 40, "\u2028sep\u2029", "$& $1 $$ $'", "%E0%A4%A", "<b>bold</b>"]


def random_settings(r: random.Random) -> dict:
    """Settings a GVR could have made (and some no form makes: the core normalizes them)."""
    s: dict = {}

    def maybe(key, value, p=0.5):
        if r.random() < p:
            s[key] = value
    maybe("rows", r.randint(3, 10), 0.9)
    maybe("cols", r.randint(3, 10), 0.9)
    maybe("lang", r.choice(LANGS), 0.8)
    maybe("pub", r.choice(["both", "gv", "lv"]))
    maybe("where", r.choice(["any", *WHERES]))
    maybe("date", r.choice(["", "2026-11-30", "2026-12-01", "2026-12-15", "2026-12-31", "2027-01-01", "2030-05-05"]), 0.7)
    maybe("cats", {c: False for c in r.sample(CATS + ["games"], r.randint(0, 3))}, 0.4)
    maybe("infoMax", r.randint(0, 4))
    maybe("free", r.random() < 0.7)
    maybe("pick", {i: r.choice([0, 1]) for i in r.sample(FIXTURE_IDS, r.randint(0, 6))}, 0.4)
    maybe("pin", {i: r.choice([0, 1]) for i in r.sample(FIXTURE_IDS, r.randint(0, 4))}, 0.4)
    if r.random() < 0.15:                      # (no form does this, a link can: left out, and "always" too)
        both = r.choice(FIXTURE_IDS)
        s.setdefault("pick", {})[both] = 0
        s.setdefault("pin", {})[both] = 1
    maybe("code", r.choice(["K7Q2", "GV65", "ABCDEF", "zz99", "k7-q2", ""]), 0.9)
    maybe("count", r.randint(1, 60))
    maybe("same", r.random() < 0.2)
    maybe("perSheet", r.choice([1, 2, 4]))
    maybe("paper", r.choice(["letter", "a4"]))
    maybe("orient", r.choice(["portrait", "landscape"]))
    for k in ("color", "showName", "showRules", "showInfo"):
        maybe(k, r.random() < 0.5, 0.3)
    for k in ("title", "event", "freeText", "rules"):
        maybe(k, r.choice(TEXTS), 0.4)
    if r.random() < 0.2:
        s["rules"] = "Line one\r\nLine two\nLine three & four = 7 #1"
    return s


def seeded_settings(seed: int, n: int) -> list[dict]:
    r = random.Random(seed)
    return [random_settings(r) for _ in range(n)]


# Loads the core into a fresh vm context, as bingo-sample.js bingoCore() does: G = GVBingo, J = the squares
LOAD = r"""
import vm from "node:vm";
const vmctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/bingo-core.js", "utf8"), vmctx, { filename: "bingo-core.js" });
const G = vmctx.GVBingo;
const J = (input && input.items) || [];
const plain = (v) => JSON.parse(JSON.stringify(v));
const ids = (c) => c.cells.filter((x) => !x.free).map((x) => x.id);
const polluted = () => Object.keys(Object.prototype).length + Object.keys(Array.prototype).length +
  vm.runInContext("Object.keys(Object.prototype).length + Object.keys(Array.prototype).length", vmctx);
"""


def core(case: unittest.TestCase, js: str, data: dict | None = None, items: list | None = None):
    """Run `js` (it calls out(value)) with the core loaded on `items` (FIXTURE by default); returns the value."""
    return run_js(case, LOAD + js, data={"items": FIXTURE if items is None else items, **(data or {})}, needs_modules=False)


# ------------------------------------------------------------------------------------------------ the build
# Eleventy with the site's own config and data, ONLY these templates (input.only), the day fixed, the squares from
# BINGO_CSV; the `bingo` global and the site's address and title as the same build has them (src/_data/bingo.js,
# src/_data/site.js: SITE_URL wins there)
BUILD_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r34-bingo-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  const site = (await imp("src/_data/site.js")).default();
  const bingo = (await imp("src/_data/bingo.js")).default();
  const want = new Set(input.urls);
  out({ pages: Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])),
        site: { url: site.url, title: site.title, title_es: site.title_es || "" },
        bingo: { items: bingo.items, info: bingo.info, cats: bingo.cats, wheres: bingo.wheres } });
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
URLS = [*BINGO.values(), *CORNER.values(), *INDEX.values(), "/sitemap.xml"]
_BUILT: dict = {}
_REAL: dict = {}


def _build(case: unittest.TestCase, cache: dict, csv: str, only: str, urls: list[str]) -> dict:
    """A build (once for the module, kept in cache): {pages: {url: content}, site, bingo, soup: {url: BeautifulSoup},
    data: {lang: #bingo-data}}."""
    if not cache:
        r = run_js(case, BUILD_JS, data={"urls": urls, "only": only}, timeout=600,
                   env={"MONTHLY_NOW": DAY, "BINGO_CSV": csv, "BINGO_WEEKLY": "", "STRICT_BUILD": "", "ONLY": ""})
        from bs4 import BeautifulSoup                      # (requirements.txt; only these checks need it)
        missing = [u for u in urls if u not in r["pages"]]
        case.assertEqual(missing, [], "pages the build did not write")
        r["soup"] = {u: BeautifulSoup(r["pages"][u], "lxml") for u in urls if u in (*BINGO.values(), *CORNER.values())}
        r["data"] = {L: json.loads(r["soup"][BINGO[L]].select_one("script#bingo-data").string) for L in LANGS}
        cache.update(r)
    return cache


def built(case: unittest.TestCase) -> dict:
    """The build every class but RealContent reads: the squares of the fixture pool (POOL), never the committee's
    file — so the tests the publishing gate runs judge the code alone."""
    return _build(case, _BUILT, str(POOL), "gvr,search-index,sitemap", URLS)


def built_real(case: unittest.TestCase) -> dict:
    """RealContent's own build: the two bingo pages (only gvr-bingo.njk) from the committee's content/bingo/bingo.csv
    (BINGO_CSV empty: src/_data/bingo.js's own file)."""
    return _build(case, _REAL, "", "gvr-bingo", list(BINGO.values()))


SAMPLE_JS = LOAD + r"""
const res = {};
for (const L of ["en", "es"]) {
  const d = input.data[L], cw = d.card[L];
  const words = { title: cw.title, free: cw.free, thisEvent: cw.this_event,
                  label: { name: cw.label_name, phone: cw.label_phone, write: cw.label_write, sign: cw.label_sign } };
  // the page's no-JS sample (gvr-bingo.njk) and the /gvr/ teaser's mini card (gvr.njk), as they ask bingo-sample.js
  const s = G.normalize({ rows: 5, cols: 5, code: input.code, date: input.day, lang: L, count: 1, same: false, perSheet: 1 });
  const m = G.normalize({ rows: 3, cols: 3, code: input.code, date: input.day, lang: L, count: 1, same: false, perSheet: 1,
                          infoMax: 1, showName: false });
  const p = G.pool(d.items, s);
  // (the mini card with the short words — dense — as gvr.njk asks for them: it is no printed sheet)
  res[L] = { settings: s, card: plain(G.card(d.items, s, 0, words)),
             mini: plain(G.card(d.items, m, 0, { title: cw.title, free: cw.free, thisEvent: cw.this_event }, { dense: true })),
             infoTake: p.infoTake, pinnedInfo: p.info.filter((it) => G.isPinned(it, s)).map((it) => it.id),
             infoMax: G.DEFAULTS.infoMax };
}
out(res);
"""
_SAMPLE: dict = {}


def sample(case: unittest.TestCase, real: bool = False) -> dict:
    """The cards bingo-core.js draws in Node from each page's own squares and words: {lang: {card, mini, …}} — of the
    fixture pool's build, or (real) of RealContent's."""
    key = "real" if real else "pool"
    if key not in _SAMPLE:
        b = built_real(case) if real else built(case)
        _SAMPLE[key] = run_js(case, SAMPLE_JS, data={"data": b["data"], "day": DAY, "code": SAMPLE_CODE}, needs_modules=False)
    return _SAMPLE[key]


def script_json(text: str) -> str:
    """A text as eleventy/script-json.js scriptJson writes it inside its JSON (no quotes): <, > and & as their
    backslash-u escapes."""
    return json.dumps(text, ensure_ascii=False)[1:-1].translate({ord(c): chr(92) + "u%04x" % ord(c) for c in "<>&"})


def words_of(node) -> str:
    """A square's words as a reader sees them (the <wbr> after an address's "@" has none)."""
    return node.get_text("") if node is not None else ""


class Built(unittest.TestCase):
    """/gvr/bingo/ and /es/gvr/bingo/ as the build writes them."""

    def setUp(self):
        self.b = built(self)
        self.s = i18n()

    def test_the_head(self):
        site = self.b["site"]
        base = site["url"].rstrip("/")
        for L, url in BINGO.items():
            soup = self.b["soup"][url]
            with self.subTest(lang=L):
                self.assertEqual(soup.html.get("lang"), L)
                site_title = (site["title_es"] or site["title"]) if L == "es" else site["title"]
                self.assertEqual(soup.title.string, f"{self.s['bingo.title'][L]} · {site_title} — NETA 65")
                self.assertEqual(soup.select_one('meta[name="description"]')["content"], self.s["bingo.meta_desc"][L])
                self.assertEqual(soup.select_one('link[rel="canonical"]')["href"], base + url)
                self.assertEqual(soup.select_one('meta[property="og:url"]')["content"], base + url)
                alt = {a["hreflang"]: a["href"] for a in soup.select('link[rel="alternate"][hreflang]')}
                self.assertEqual(alt, {"en": base + BINGO["en"], "es": base + BINGO["es"], "x-default": base + BINGO["en"]})

    def test_the_breadcrumb_and_the_menu(self):
        base = self.b["site"]["url"].rstrip("/")
        for L, url in BINGO.items():
            soup = self.b["soup"][url]
            with self.subTest(lang=L):
                graph = json.loads(soup.select("script[type='application/ld+json']")[-1].string)["@graph"]
                crumbs = next(n for n in graph if n["@type"] == "BreadcrumbList")
                self.assertEqual(crumbs["@id"], base + url + "#breadcrumb")
                self.assertEqual([(i["position"], i["name"], i.get("item")) for i in crumbs["itemListElement"]],
                                 [(1, self.s["nav.home"][L], base + ("/es/" if L == "es" else "/")),
                                  (2, self.s["nav.gvr"][L], base + CORNER[L]),
                                  (3, self.s["bingo.title"][L], None)])
                # pageKey gvr: the menu shows the GVR / RLV corner as the page you are on (and nothing else)
                self.assertEqual({a["href"] for a in soup.select('a[aria-current="page"]')}, {CORNER[L]})

    def test_the_scripts_and_the_stylesheet(self):
        for L, url in BINGO.items():
            soup = self.b["soup"][url]
            with self.subTest(lang=L):
                names = [re.sub(r"\?.*$", "", s["src"]).rsplit("/", 1)[-1] for s in soup.select("script[src]")]
                self.assertLess(names.index("app.js"), names.index("bingo-core.js"))
                self.assertLess(names.index("bingo-core.js"), names.index("bingo.js"))
                for s in soup.select('script[src*="bingo"]'):
                    self.assertTrue(s.has_attr("defer"))
                self.assertTrue(soup.select('link[rel="stylesheet"][href*="/assets/css/bingo.css"]'))
                app = soup.select_one(".bgo-app")
                self.assertEqual(app.get("x-data"), f"bingoBuilder('{L}')")
                self.assertTrue(app.has_attr("data-js-only"))

    def test_the_data_block(self):
        b = self.b
        home = b["site"]["url"].rstrip("/")
        for L, url in BINGO.items():
            node = b["soup"][url].select_one("script#bingo-data")
            with self.subTest(lang=L):
                self.assertEqual(node.get("type"), "application/json")
                # the pool's markup squares: in the JSON as \u escapes (eleventy/script-json.js), so no word can close
                # the <script> or open a comment or an entity — and JSON.parse gives back the very words
                for raw in ("<", ">", "&"):
                    self.assertNotIn(raw, node.string, f"no raw {raw} in the JSON")
                self.assertIn(script_json(MARKUP["fun-markup-script"][0]), node.string)
                d = b["data"][L]
                squares = {it["id"]: it for it in d["items"]}
                for sid, (text, label) in MARKUP.items():
                    self.assertEqual((squares[sid]["text"], squares[sid]["label"]),
                                     ({"en": text, "es": text}, {"en": label, "es": label}), sid)
                self.assertEqual(sorted(d), ["card", "catNames", "cats", "info", "items", "ui", "wheres"])
                # every square of the build, as the build has it (not a count: the committee edits the file — RealContent
                # judges how many there are)
                self.assertTrue(d["items"])
                self.assertEqual(d["items"], b["bingo"]["items"])
                self.assertEqual(d["info"], b["bingo"]["info"])
                self.assertEqual(d["cats"], b["bingo"]["cats"])
                self.assertEqual(d["cats"][:8], CATS)
                self.assertEqual(d["wheres"], b["bingo"]["wheres"])
                self.assertEqual(d["wheres"], WHERES)
                # the card's words in BOTH languages (a card's language is chosen apart from the page's); the builder's
                # and the categories' names in the page's
                for C in LANGS:
                    self.assertEqual(d["card"][C], group(self.s, "bingo.card.", C), C)
                self.assertNotEqual(d["card"]["en"]["title"], d["card"]["es"]["title"])
                self.assertEqual(d["ui"], group(self.s, "bingo.ui.", L))
                self.assertEqual(d["catNames"], group(self.s, "bingo.cat.", L))
                info = d["info"]
                self.assertIn("@", info["email"])
                self.assertEqual(info["home"], {"en": home + "/", "es": home + "/es/"})
                self.assertEqual(info["gvr"], {"en": home + "/gvr/", "es": home + "/es/gvr/"})
                # each meeting's three lines (long, mid, short: what the card's strip chooses from) — or none of them
                for m in ("gvMeeting", "committeeMeeting"):
                    lines = [info[m + suf] for suf in ("", "Mid", "Short")]
                    self.assertTrue(all(v is None for v in lines) or all(v["en"].strip() and v["es"].strip() for v in lines), m)

    def test_markup_in_a_square_is_never_markup_on_the_pages(self):
        """No element and no script of the pool's markup squares anywhere on the four pages: their words are
        escaped wherever they are printed (the no-JS sample: escape | bingoBreaks | safe; the /gvr/ mini card:
        escape | replace("@", "@<wbr>") | safe — escaped first, then the line break after an "@"; their labels:
        autoescape)."""
        for url in (*BINGO.values(), *CORNER.values()):
            html = self.b["pages"][url]
            with self.subTest(url=url):
                for raw in ("<script>__h1", "<img src=x", "<b onclick", "<i>it</i>"):
                    self.assertNotIn(raw, html)
                # (the words as the templates write them: their entities written out, the "@" with its <wbr>)
                self.assertIn("&lt;/script&gt;&lt;script&gt;__h1=1&lt;/script&gt;", html)
                self.assertIn("a@<wbr>b&quot;&gt;&lt;img src=x onerror=__h2=1&gt;", html)
                self.assertIn("&amp;lt;b&amp;gt; &amp; &amp;amp; &lt;i&gt;it&lt;/i&gt; &#39;q&#39; $&amp;", html)
                if url in BINGO.values():
                    self.assertIn("&lt;b onclick=__h3=1&gt;L&lt;/b&gt;", html)

    def test_no_unfilled_placeholder(self):
        """Nothing a reader sees says {…} ({event} and the builder's {n} wait in #bingo-data, for the script)."""
        ph = re.compile(r"\{[a-zA-Z_]\w*\}")
        for url in BINGO.values():
            main = self.b["soup"][url].select_one("main")
            with self.subTest(url=url):
                words = " ".join(t for t in main.find_all(string=True) if t.parent.name not in ("script", "style", "template"))
                self.assertEqual(ph.findall(words), [])
                attrs = [f"{a}={v}" for el in main.find_all(True) for a, v in el.attrs.items()
                         if isinstance(v, str) and not a.startswith(("x-", ":", "@", "data-")) and ph.search(v)]
                self.assertEqual(attrs, [])
        for url in CORNER.values():
            self.assertEqual(ph.findall(self.b["soup"][url].select_one("section#bingo").get_text(" ")), [], url)


class Sample(unittest.TestCase):
    """The card /gvr/bingo/ shows (and prints) without JavaScript."""

    def setUp(self):
        self.b = built(self)
        self.x = sample(self)
        self.s = i18n()

    def card_of(self, L: str):
        nojs = self.b["soup"][BINGO[L]].select_one(".bgo-nojs")
        self.assertTrue(nojs.has_attr("data-nojs-only"))
        return nojs.select_one(".bgo-sample article.bgo-card")

    def test_without_javascript_the_page_says_so_and_shows_a_card(self):
        for L in LANGS:
            nojs = self.b["soup"][BINGO[L]].select_one(".bgo-nojs")
            with self.subTest(lang=L):
                note = nojs.select_one(".bgo-nojs-note").get_text(" ", strip=True)
                self.assertIn(self.s["bingo.nojs_title"][L], note)
                self.assertIn(self.s["bingo.nojs_text"][L], note)
                self.assertNotIn("error", self.x[L]["card"], "the build's squares fill a 5×5 card")
                self.assertIsNotNone(self.card_of(L))

    def test_it_is_the_card_the_core_draws(self):
        """5×5, the page's language, game code GV65, the build's day: square for square bingo-core.js's card 0 of
        the page's own squares (eleventy/filters/bingo-sample.js runs the very same core)."""
        for L in LANGS:
            card, want = self.card_of(L), self.x[L]["card"]
            cells = card.select(".bgo-cell")
            with self.subTest(lang=L):
                self.assertEqual(card.get("lang"), L)
                self.assertEqual((want["rows"], want["cols"], want["code"], want["lang"]), (5, 5, SAMPLE_CODE, L))
                self.assertIn("--rows:5;--cols:5", card["style"])
                self.assertEqual(card.get("data-dense"), "1" if want["dense"] else "0")
                self.assertEqual(len(cells), 25)
                self.assertEqual(
                    [(c["data-type"], c["data-mark"], c["data-pub"], words_of(c.select_one(".bgo-txt")),
                      words_of(c.select_one(".bgo-lab"))) for c in cells],
                    [(w["type"], w["mark"], w["pub"], w["text"], w["label"]) for w in want["cells"]])
                # the pool's markup squares (pinned: on every card) are on it as words — their words and their label;
                # nothing in a square is an element but an address's <wbr> (and a time range's span.bgo-nb)
                on = {w["id"]: (w["text"], w["label"]) for w in want["cells"]}
                self.assertEqual({k: on.get(k) for k in MARKUP}, MARKUP)
                self.assertEqual({t.name for c in cells for t in c.select(".bgo-txt *, .bgo-lab *")}, {"span", "wbr"})
                for c in cells:
                    pt = float(re.search(r"font-size:([\d.]+)pt", c.select_one(".bgo-w")["style"]).group(1))
                    self.assertTrue(SAMPLE_FLOOR <= pt <= 36, pt)

    def test_free_in_the_middle_and_no_square_twice(self):
        for L in LANGS:
            cells = self.card_of(L).select(".bgo-cell")
            with self.subTest(lang=L):
                free = [i for i, c in enumerate(cells) if c["data-type"] == "free"]
                self.assertEqual(free, [12])
                self.assertEqual(words_of(cells[12].select_one(".bgo-txt")), self.s["bingo.card.free"][L])
                self.assertIsNotNone(cells[12].select_one(".bgo-free-mark svg"))
                texts = [words_of(c.select_one(".bgo-txt")) for c in cells if c["data-type"] != "free"]
                self.assertEqual(len(set(texts)), 24)
                ids = [w["id"] for w in self.x[L]["card"]["cells"] if not w["free"]]
                self.assertEqual(len(set(ids)), 24)

    def test_the_information_squares_the_cap_gives(self):
        """DEFAULTS.infoMax is 3 (the three squares the CSV pins "Always on every card" — both meetings and the
        e-mail — on every default card); the card has that many information squares, the pinned ones first."""
        for L in LANGS:
            x = self.x[L]
            cells = self.card_of(L).select(".bgo-cell")
            with self.subTest(lang=L):
                self.assertEqual(x["infoMax"], 3)
                self.assertEqual(x["settings"]["infoMax"], 3)
                infos = [w["id"] for w in x["card"]["cells"] if w["type"] == "info"]
                pool = expected_pool(self.b["data"][L]["items"], x["settings"])
                self.assertEqual(x["infoTake"], min(3, len(pool["info"])))
                self.assertEqual(len(infos), x["infoTake"])
                self.assertEqual(len([c for c in cells if c["data-type"] == "info"]), x["infoTake"])
                pinned = x["pinnedInfo"]
                self.assertEqual(sorted(pinned), sorted(i for i in pool["pinned"] if i in pool["info"]))
                if len(pinned) >= len(infos):
                    self.assertTrue(set(infos) <= set(pinned), "the pinned ones first")
                else:
                    self.assertTrue(set(pinned) <= set(infos))
                for c in cells:
                    if c["data-type"] == "info":
                        self.assertIsNotNone(c.select_one(".bgo-ic svg"))

    def test_the_head_the_strip_and_the_small_print(self):
        b = self.b
        for L in LANGS:
            card, info, cw = self.card_of(L), b["data"][L]["info"], b["data"][L]["card"][L]
            with self.subTest(lang=L):
                self.assertEqual(card.select_one(".bgo-title").get_text(strip=True), cw["title"])
                sub = card.select_one(".bgo-sub").get_text(strip=True)
                self.assertIn("2026", sub)
                self.assertIn("November 18" if L == "en" else "18 de noviembre", sub)
                self.assertEqual([p.get_text(strip=True) for p in card.select(".bgo-names .bgo-field")],
                                 [cw["name_line"], cw["group_line"]])
                self.assertEqual(card.select_one(".bgo-rules .bgo-h").get_text(strip=True), cw["rules_h"])
                self.assertEqual(card.select_one(".bgo-rules-txt").get_text(strip=True), cw["rules_square"].replace("{n}", "5"))
                lines = [p.get_text("") for p in card.select(".bgo-info .bgo-li")]
                want = []
                if info["gvMeeting"]:
                    want.append(f"{cw['gv_meeting']}: {info['gvMeeting'][L]}")
                if info["committeeMeeting"]:
                    want.append(f"{cw['committee_meeting']}: {info['committeeMeeting'][L]}")
                want.append(f"{cw['write_us']}: {info['email']}" + (f" · {info['site']}" if info["site"] else ""))
                self.assertEqual(lines, want)
                use = card.select_one("figure.bgo-qr use")
                self.assertEqual(use["href"], f"#bgo-qr-{L}")
                for q in LANGS:                                # (the builder's cards of either language use them too)
                    self.assertEqual(b["soup"][BINGO[L]].select_one(f"#bgo-qr-{q}").name, "symbol")
                self.assertEqual(card.select_one(".bgo-anon").get_text(strip=True), cw["anon"])
                foot = cw["foot"].replace("{n}", "1").replace("{total}", "1").replace("{code}", SAMPLE_CODE)
                self.assertEqual(card.select_one(".bgo-meta").get_text(strip=True), foot + (f" · {info['site']}" if info["site"] else ""))


class Teaser(unittest.TestCase):
    """/gvr/'s #bingo: the way to the bingo cards."""

    def setUp(self):
        self.b = built(self)
        self.s = i18n()

    def test_its_place_and_its_chip(self):
        for L, url in CORNER.items():
            soup = self.b["soup"][url]
            with self.subTest(lang=L):
                ids = [s.get("id") for s in soup.select("main section[id]")]
                self.assertEqual(ids.index("bingo"), ids.index("ideas") + 1)
                self.assertEqual(ids.index("pass-it-on"), ids.index("bingo") + 1)
                chips = soup.select("nav.page-nav a.chip")
                hrefs = [a["href"] for a in chips]
                self.assertEqual(hrefs.index("#bingo"), hrefs.index("#ideas") + 1)
                self.assertEqual(hrefs.index("#pass-it-on"), hrefs.index("#bingo") + 1)
                chip = chips[hrefs.index("#bingo")]
                self.assertEqual(chip.get_text(" ", strip=True), self.s["read.gvr.nav_bingo"][L])
                self.assertIsNotNone(chip.select_one('use[href="#i-grid-3x3"]'))

    def test_its_words_and_the_button(self):
        for L, url in CORNER.items():
            sec = self.b["soup"][url].select_one("section#bingo")
            with self.subTest(lang=L):
                self.assertEqual(sec.get("aria-labelledby"), "bingo-title")
                self.assertEqual(sec.select_one("#bingo-title").get_text(" ", strip=True), self.s["read.gvr.bingo_title"][L])
                text = sec.get_text(" ", strip=True)
                for k in ("bingo_eyebrow", "bingo_text", "bingo_p1", "bingo_p2", "bingo_p3"):
                    self.assertIn(self.s["read.gvr." + k][L], text, k)
                links = sec.select("a[href]")
                self.assertEqual([a["href"] for a in links], [BINGO[L]], "one way out: the bingo page of the page's language")
                self.assertIn("btn-primary", links[0]["class"])
                self.assertEqual(links[0].get_text(" ", strip=True), self.s["read.gvr.bingo_btn"][L])

    def test_the_mini_card_is_the_cores(self):
        """Decoration (aria-hidden): the 3×3 card the core draws with one information square at most, each square's
        short words, FREE in the middle."""
        x = sample(self)
        for L, url in CORNER.items():
            sec = self.b["soup"][url].select_one("section#bingo")
            mini = next((d for d in sec.select('div[aria-hidden="true"]') if d.select("div.aspect-square")), None)
            want = x[L]["mini"]
            with self.subTest(lang=L):
                if "error" in want:                             # (too few squares: no card, the words and the button stay)
                    self.assertIsNone(mini)
                    continue
                self.assertEqual(mini.select_one("[lang]")["lang"], L)
                cells = mini.select("div.aspect-square")
                self.assertEqual(len(cells), 9)
                items = {it["id"]: it for it in self.b["data"][L]["items"]}
                this_event = self.b["data"][L]["card"][L]["this_event"]
                self.assertTrue(want["dense"])
                for c in want["cells"]:
                    if not c["free"]:
                        self.assertEqual(c["text"], (items[c["id"]]["short"][L] or items[c["id"]]["text"][L]).replace("{event}", this_event))
                # square for square, word for word (the pool's three markup squares pinned on it: as words)
                self.assertEqual([c.get_text("", strip=True) for c in cells], [c["text"] for c in want["cells"]])
                self.assertTrue({t for t, _ in MARKUP.values()} <= {c["text"] for c in want["cells"]})
                self.assertEqual(mini.select("img, script, b, i"), [])
                self.assertEqual(want["cells"][4]["text"], self.s["bingo.card.free"][L])
                self.assertLessEqual(len([w for w in want["cells"] if w["type"] == "info"]), 1)
                foot = self.s["bingo.card.foot"][L].replace("{n}", "1").replace("{total}", "1").replace("{code}", SAMPLE_CODE)
                self.assertEqual(mini.select("p")[-1].get_text(strip=True), foot)


class Found(unittest.TestCase):
    """The page is not in the menu: the site's search finds it, and so do search engines (the sitemap)."""

    def setUp(self):
        self.b = built(self)
        self.s = i18n()

    def test_the_search_entry_in_both_indexes(self):
        for L, url in INDEX.items():
            entries = [e for e in json.loads(self.b["pages"][url])["items"] if e.get("id") == "page:gvr-bingo"]
            other = "es" if L == "en" else "en"
            with self.subTest(lang=L):
                self.assertEqual(len(entries), 1)
                e = entries[0]
                self.assertEqual((e["k"], e["u"], e["src"], e["ic"]), ("page", BINGO[L], "site", "grid-3x3"))
                self.assertEqual((e["t"], e["o"], e["ol"]), (self.s["bingo.title"][L], self.s["bingo.title"][other], other))
                self.assertEqual(e["s"], self.s["bingo.meta_desc"][L])
                for word in ("bingo", "juego"):
                    self.assertIn(word, e["x"])
        # the search page can draw its icon
        icons = re.search(r'<template id="ss-icons">\s*\{%-? for name in \[(.*?)\]', read(ROOT / "src" / "pages" / "search.njk"), re.S)
        self.assertIn('"grid-3x3"', icons.group(1))

    def test_the_sitemap(self):
        base = self.b["site"]["url"].rstrip("/")
        xml = self.b["pages"]["/sitemap.xml"]
        for L, url in BINGO.items():
            with self.subTest(lang=L):
                block = re.search(r"<url>\s*<loc>" + re.escape(base + url) + r"</loc>(.*?)</url>", xml, re.S)
                self.assertIsNotNone(block)
                alt = dict(re.findall(r'<xhtml:link rel="alternate" hreflang="([\w-]+)" href="([^"]+)"/>', block.group(1)))
                self.assertEqual(alt, {"en": base + BINGO["en"], "es": base + BINGO["es"], "x-default": base + BINGO["en"]})


# ------------------------------------------------------------------------------------------------ the core
DEFAULTS = {"title": "", "event": "", "date": "", "lang": "en", "pub": "both", "rows": 5, "cols": 5, "free": True,
            "freeText": "", "where": "any", "cats": {}, "infoMax": 3, "pick": {}, "pin": {}, "count": 10, "same": False,
            "code": "", "perSheet": 1, "paper": "letter", "orient": "portrait", "color": True, "showName": True,
            "showRules": True, "rules": "", "showInfo": True}
TEXT_MAX = {"title": 60, "event": 60, "freeText": 16, "rules": 320}


def settings_problems(n: dict) -> list[str]:
    """What is wrong with settings normalize gave back ([]: they are safe to use)."""
    bad = []
    if list(n) != list(DEFAULTS):
        bad.append(f"keys {list(n)}")
        return bad
    for k, lo, hi in (("rows", 3, 10), ("cols", 3, 10), ("count", 1, 60), ("infoMax", 0, 4)):
        if not (isinstance(n[k], int) and not isinstance(n[k], bool) and lo <= n[k] <= hi):
            bad.append(f"{k} {n[k]!r}")
    for k, allowed in (("lang", LANGS), ("pub", ("both", "gv", "lv")), ("where", ("any", *WHERES)), ("paper", ("letter", "a4")),
                       ("orient", ("portrait", "landscape")), ("perSheet", (1, 2, 4))):
        if n[k] not in allowed:
            bad.append(f"{k} {n[k]!r}")
    for k in ("free", "same", "color", "showName", "showRules", "showInfo"):
        if not isinstance(n[k], bool):
            bad.append(f"{k} {n[k]!r}")
    for k, most in TEXT_MAX.items():
        ctl = r"[\x00-\x09\x0b-\x1f\x7f]" if k == "rules" else r"[\x00-\x1f\x7f]"
        if not isinstance(n[k], str) or len(n[k].encode("utf-16-le")) // 2 > most or re.search(ctl, n[k]) \
                or re.search(r"[\ud800-\udfff]", n[k]):
            bad.append(f"{k} {n[k]!r}")
    if n["code"] and not CODE.match(n["code"]):
        bad.append(f"code {n['code']!r}")
    if n["date"] and not re.fullmatch(r"20\d\d-\d\d-\d\d", n["date"]):
        bad.append(f"date {n['date']!r}")
    if not all(v is False and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", c) for c, v in n["cats"].items()):
        bad.append(f"cats {n['cats']!r}")
    for k in ("pick", "pin"):
        if len(n[k]) > 1000 or not all(v in (0, 1) and not isinstance(v, bool) and len(i) <= 48 and VALID_ID.match(i)
                                       for i, v in n[k].items()):
            bad.append(f"{k} {str(n[k])[:200]}")
    return bad


class Settings(unittest.TestCase):
    """GVBingo.DEFAULTS and normalize: anything from storage or an address is made safe, and nothing throws."""

    def test_the_defaults(self):
        r = core(self, r"""
          const d = G.DEFAULTS; d.infoMax = 0; d.rows = 9;           // (a copy: changing it changes nothing)
          out({ defaults: plain(vmctx.GVBingo.normalize({})), after: [G.normalize({}).infoMax, G.normalize({}).rows],
                es: G.normalize({}, { lang: "es" }).lang, words: plain(G.WORDS) });""")
        self.assertEqual(r["defaults"], DEFAULTS)
        self.assertEqual(r["after"], [3, 5])
        self.assertEqual(r["es"], "es")
        self.assertEqual(r["words"]["en"]["label"], LABEL_DEFAULT["en"])
        self.assertEqual(r["words"]["es"]["label"], LABEL_DEFAULT["es"])

    def test_values_are_read_and_clamped(self):
        r = core(self, r"""
          const N = (raw, base) => plain(G.normalize(raw, base));
          out({
            rows: [1e308, -1e308, "7", " 4 ", "7.6", Infinity, NaN, true, [7], "1e3", -0].map((v) => N({ rows: v }).rows),
            count: [0, 61, "12", 5.5].map((v) => N({ count: v }).count),
            infoMax: [-1, 9, "2", 0].map((v) => N({ infoMax: v }).infoMax),
            perSheet: [3, "2", 4, "4.0"].map((v) => N({ perSheet: v }).perSheet),
            lang: [N({ lang: "fr" }).lang, N({ lang: "fr" }, { lang: "es" }).lang, N({}, "es").lang, N({ lang: "es" }, { lang: "en" }).lang],
            base: N({}, { rows: 99, pub: "nope", count: "3" }),
            text: [N({ title: "x".repeat(100) }).title.length, N({ title: "a\nb\tc" }).title, N({ rules: "a\r\nb\u0001c" }).rules,
                   N({ title: 12345 }).title, N({ title: {} }).title, N({ freeText: "🍇".repeat(20) }).freeText,
                   N({ event: "\ud800 half" }).event],
            code: ["k7q2", "K7 Q-2", "IO01", "ABC", "ABCDEFG", 1234].map((v) => N({ code: v }).code),
            date: ["2026-02-30", "2026-02-28", "2099-12-31", "2100-01-01", "1999-12-31", " 2027-01-05 ", "2027-1-5"]
              .map((v) => N({ date: v }).date),
            cats: [N({ cats: ["fun", "Bad Cat", 7] }).cats, N({ cats: { fun: "false", read: true, Bad: false } }).cats, N({ cats: "fun" }).cats],
            pick: N({ pick: { "ok-id": "1", "bad id": 1, x: "maybe", y: 0, "Up-Case": 1 } }).pick,
            many: Object.keys(N({ pick: Object.fromEntries(Array.from({ length: 2000 }, (_, i) => ["sq-" + i, 1])) }).pick).length,
          });""")
        self.assertEqual(r["rows"], [10, 3, 7, 4, 8, 5, 5, 5, 5, 5, 3])
        self.assertEqual(r["count"], [1, 60, 12, 6])
        self.assertEqual(r["infoMax"], [0, 4, 2, 0])
        self.assertEqual(r["perSheet"], [1, 2, 4, 4])
        self.assertEqual(r["lang"], ["en", "es", "en", "es"])
        self.assertEqual((r["base"]["rows"], r["base"]["pub"], r["base"]["count"]), (10, "both", 3))
        self.assertEqual(r["text"][:5], [60, "a b c", "a\nb c", "12345", ""])
        self.assertEqual(r["text"][5], "🍇" * 8)                   # (16 UTF-16 units: no half emoji)
        self.assertEqual(r["text"][6], " half")
        self.assertEqual(r["code"], ["K7Q2", "K7Q2", "", "", "", ""])
        self.assertEqual(r["date"], ["", "2026-02-28", "2099-12-31", "", "", "2027-01-05", ""])
        self.assertEqual(r["cats"], [{"fun": False}, {"fun": False}, {}])
        self.assertEqual(r["pick"], {"ok-id": 1, "y": 0})
        self.assertEqual(r["many"], 1000)

    def test_junk_never_throws(self):
        """Junk of every kind, also a few hundred seeded random mixes of it under every key (own __proto__ and
        constructor keys too, as JSON.parse makes them): normalize never throws, the settings are safe to use, and no
        prototype is touched."""
        r = core(self, r"""
          const junk = [undefined, null, 0, -0, 1, 7, 1e308, -1e308, Infinity, -Infinity, NaN, "", "  ", "7", "7.5", "-3", "abc",
            "x".repeat(5000), "\u0000\u0001\n\r\t", "🍇".repeat(50), "\ud800", true, false, [], [1, 2], ["fun"], {}, { a: 1 },
            { "ok-id": 1 }, () => 1, Symbol("x"), 10n, new Date(0), Object.create(null), JSON.parse('{"__proto__": {"x": 1}}'),
            "2026-12-01", "K7Q2", "es", "gv", "a4", "landscape", 2, 4];
          const keys = [...Object.keys(G.DEFAULTS), "__proto__", "constructor", "prototype", "unknown"];
          const own = (o, k, v) => Object.defineProperty(o, k, { value: v, enumerable: true, configurable: true, writable: true });
          const R = G.rng("junk");
          const pickOf = () => junk[Math.floor(R() * junk.length)];
          const results = [], errors = [];
          const tries = [...junk.map((j) => [j, undefined]), ...junk.map((j) => [{}, j]),
                         [JSON.parse('{"__proto__": {"rows": 9}, "constructor": 1, "pick": {"__proto__": 1, "constructor": 1}}'), undefined]];
          for (let i = 0; i < 300; i++) {
            const raw = {}, base = {};
            for (const k of keys) { if (R() < 0.6) own(raw, k, pickOf()); if (R() < 0.2) own(base, k, pickOf()); }
            tries.push([raw, R() < 0.5 ? base : pickOf()]);
          }
          for (const [raw, base] of tries) {
            try { results.push(plain(G.normalize(raw, base))); } catch (e) { errors.push(String(e)); }
          }
          out({ results, errors, polluted: polluted(), protoCase: plain(G.normalize(tries[2 * junk.length][0])) });""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["polluted"], 0)
        self.assertGreater(len(r["results"]), 380)
        for n in r["results"]:
            self.assertEqual(settings_problems(n), [], n)
        self.assertEqual(r["protoCase"]["rows"], 5)
        self.assertEqual(r["protoCase"]["pick"], {"constructor": 1})

    def test_codes(self):
        r = core(self, r"""
          const a = G.newCode(G.rng(5)), b = G.newCode(G.rng(5)), six = G.newCode(G.rng(5), 6);
          const R = G.rng("codes"), many = []; for (let i = 0; i < 500; i++) many.push(G.newCode(R, 4 + (i % 3)));
          out({ a, b, six, long: G.newCode(G.rng(1), 99).length, short: G.newCode(G.rng(1), 1).length, odd: G.newCode(() => NaN),
                many, clean: many.every((c) => G.cleanCode(c) === c), random: G.newCode().length, alphabet: G.ALPHABET });""")
        self.assertEqual(r["a"], r["b"])
        self.assertEqual(len(r["a"]), 4)
        self.assertEqual(len(r["six"]), 6)
        self.assertEqual((r["long"], r["short"], r["random"]), (6, 4, 4))
        self.assertEqual(r["alphabet"], "ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        self.assertTrue(CODE.match(r["odd"]))
        self.assertTrue(r["clean"])
        self.assertTrue(all(CODE.match(c) for c in r["many"]))
        self.assertGreater(len(set(r["many"])), 450)

    def test_free_square_and_sheets(self):
        r = core(self, r"""
          const out1 = [];
          for (let rows = 3; rows <= 10; rows++) for (let cols = 3; cols <= 10; cols++) {
            const s = { rows, cols };
            out1.push([rows, cols, G.freeOn(s), G.freeOn({ ...s, free: false }), G.needOf(s), G.perSheetChoices(s),
                       G.perSheetOf({ ...s, perSheet: 4 })]);
          }
          const sheets = [[1, 1], [10, 1], [10, 2], [9, 2], [10, 4], [9, 4], [60, 4], [1, 4]].map(([count, perSheet]) => {
            const p = G.sheetPlan({ rows: 3, cols: 3, count, perSheet });
            return [p.sheets, p.slots.length, p.perSheet];
          });
          out({ grid: out1, sheets, a4: G.sheetPlan({ paper: "a4", orient: "landscape" }).size, letter: G.sheetPlan({}).size });""")
        for rows, cols, free, free_off, need, choices, four in r["grid"]:
            with self.subTest(grid=f"{rows}x{cols}"):
                odd = rows % 2 == 1 and cols % 2 == 1
                self.assertEqual(free, odd)
                self.assertFalse(free_off)
                self.assertEqual(need, rows * cols - (1 if odd else 0))
                big = max(rows, cols)
                self.assertEqual(choices, [1, 2, 4] if big <= 4 else [1, 2] if big <= 5 else [1])
                self.assertEqual(four, choices[-1])
        self.assertEqual(r["sheets"], [[1, 1, 1], [10, 1, 1], [5, 2, 2], [5, 2, 2], [3, 4, 4], [3, 4, 4], [15, 4, 4], [1, 4, 4]])
        self.assertEqual((r["letter"], r["a4"]), ("letter portrait", "A4 landscape"))


class Pool(unittest.TestCase):
    """THE POOL: the squares a card may have, by the rules written again in expected_reason."""

    def test_every_square_by_the_rules(self):
        """300 seeded settings (magazine, occasion, categories, date windows, language, by-hand picks and pins) ×
        every square, not-squares and an id twice: why() gives the rule's reason, pool() its lists and counts."""
        cases = seeded_settings(34, 300)
        items = FIXTURE + BAD_ITEMS
        r = core(self, r"""
          out(input.cases.map((raw) => {
            const s = plain(G.normalize(raw)), p = G.pool(J, raw);
            return { s, why: J.map((it) => G.why(it, raw)), offered: J.map((it) => G.offered(it, raw)),
                     pool: p.pool.map((it) => it.id), pinned: p.pinned.map((it) => it.id), info: p.info.map((it) => it.id),
                     rest: p.rest.map((it) => it.id), need: p.need, have: p.have, infoTake: p.infoTake, free: p.free, ok: p.ok };
          }));""", data={"cases": cases}, items=items)
        reasons = set()
        for case in r:
            s = case["s"]
            want = [expected_reason(it, s) for it in items]
            reasons |= set(want)
            self.assertEqual(case["why"], want, s)
            self.assertEqual(case["offered"], [w not in ("bad", "lang", "date") for w in want])
            p = expected_pool(items, s)
            for k in ("pool", "pinned", "info", "rest", "need", "have", "infoTake", "free", "ok"):
                self.assertEqual(case[k], p[k], (k, s))
        self.assertEqual(reasons, {None, "bad", "lang", "date", "off", "pub", "where", "cat"}, "every rule was met")
        self.assertTrue(any(c["ok"] for c in r) and not all(c["ok"] for c in r))

    def test_the_magazine_occasion_date_and_language(self):
        r = core(self, r"""
          const P = (s) => G.pool(J, s).pool;
          out({ gv: P({ pub: "gv" }).map((it) => it.pub), lv: P({ pub: "lv" }).map((it) => it.pub),
                online: P({ where: "online" }).map((it) => it.where), noFun: P({ cats: { fun: false } }).map((it) => it.cat),
                es: P({ lang: "es" }).map((it) => it.id), en: P({ lang: "en" }).map((it) => it.id),
                days: ["", "2026-11-30", "2026-12-01", "2026-12-31", "2027-01-01"]
                  .map((date) => P({ date }).filter((it) => it.from || it.until).map((it) => it.id)) });""")
        self.assertEqual(set(r["gv"]), {"gv", "both"})
        self.assertEqual(set(r["lv"]), {"lv", "both"})
        self.assertTrue(all(w == [] or "online" in w for w in r["online"]))
        self.assertNotIn("fun", r["noFun"])
        self.assertIn("read-es-only", r["es"])
        self.assertNotIn("read-en-only", r["es"])
        self.assertIn("read-en-only", r["en"])
        self.assertNotIn("read-es-only", r["en"])
        # (both days included; no date: every dated square out)
        self.assertEqual(r["days"], [[], ["fun-until-nov"], ["fun-december"], ["fun-december"], ["fun-from-2027"]])

    def test_the_pick_list(self):
        """pickRows — the rows of the builder's "Choose squares yourself", 300 seeded settings: every square offered
        (not a bad one, nor one of another language or outside its dates; an id twice listed twice), in the squares'
        order; on = it may be on the card (why() is null); "always" ticked only on a square that is on and pinned —
        one left out by hand shows it off, whatever pins it."""
        cases = seeded_settings(461, 300)
        items = FIXTURE + BAD_ITEMS
        r = core(self, r"""
          out(input.cases.map((raw) => ({ s: plain(G.normalize(raw)),
                                          rows: G.pickRows(J, raw).map((x) => [J.indexOf(x.item), x.on, x.pin]) })));""",
                 data={"cases": cases}, items=items)
        seen = set()
        for case in r:
            s = case["s"]
            want = []
            for n, it in enumerate(items):
                why = expected_reason(it, s)
                if why in ("bad", "lang", "date"):
                    continue
                pinned = s["pin"].get(it["id"]) == 1 or (it.get("pin") is True and s["pin"].get(it["id"]) != 0)
                want.append([n, why is None, why is None and pinned])
            seen |= {(on, pin) for _, on, pin in want}
            self.assertEqual(case["rows"], want, s)
        self.assertEqual(seen, {(True, True), (True, False), (False, False)}, "every kind of row was met")

    def test_by_hand(self):
        """Choose squares yourself: taking one in overrides the magazine, the occasion and the category — never the
        language or the date; leaving one out beats its pin; the maps keep only what the filters would not do."""
        r = core(self, r"""
          const byId = (id) => J.find((it) => it.id === id);
          const gv = byId("listen-sq-003"), plainSq = byId("read-sq-001"), enOnly = byId("read-en-only"), dec = byId("fun-december");
          const pinned = byId("people-always");
          const lv = G.normalize({ pub: "lv", date: "2026-11-18", lang: "es" });
          const s1 = G.setPick(lv, gv, true), s2 = G.setPick(s1, gv, false);
          const s3 = G.setPick(lv, plainSq, false), s4 = G.setPin(s3, plainSq, true);
          const s5 = G.setPick(lv, enOnly, true), s6 = G.setPick(lv, dec, true), s7 = G.setPin(lv, enOnly, true);
          const s8 = G.setPin(lv, pinned, false), s9 = G.setPin(s8, pinned, true), s10 = G.setPick(lv, pinned, false);
          out({ before: G.why(gv, lv), s1: [s1.pick, G.why(gv, s1)], s2: [s2.pick, G.why(gv, s2)],
                s3: [s3.pick, G.why(plainSq, s3)], s4: [s4.pick, s4.pin, G.why(plainSq, s4), G.isPinned(plainSq, s4)],
                s5: G.why(enOnly, s5), s6: G.why(dec, s6), s7: G.why(enOnly, s7),
                s8: [s8.pin, G.isPinned(pinned, s8)], s9: [s9.pin, G.isPinned(pinned, s9)],
                s10: [s10.pick, G.why(pinned, s10), G.pool(J, s10).pool.some((it) => it.id === pinned.id)],
                // (a link can say both: #out=x&pin=x — left out wins)
                both: [G.why(plainSq, { pick: { "read-sq-001": 0 }, pin: { "read-sq-001": 1 } }),
                       G.pool(J, G.fromHash("#out=read-sq-001&pin=read-sq-001")).pool.some((it) => it.id === "read-sq-001")],
                bad: [G.setPick(lv, null, true), G.setPin(lv, { id: "Bad Id" }, true)].map((s) => [s.pick, s.pin]) });""")
        self.assertEqual(r["before"], "pub")
        self.assertEqual(r["s1"], [{"listen-sq-003": 1}, None])
        self.assertEqual(r["s2"], [{}, "pub"])
        self.assertEqual(r["s3"], [{"read-sq-001": 0}, "off"])
        self.assertEqual(r["s4"], [{}, {"read-sq-001": 1}, None, True])
        self.assertEqual((r["s5"], r["s6"], r["s7"]), ("lang", "date", "lang"))
        self.assertEqual(r["s8"], [{"people-always": 0}, False])
        self.assertEqual(r["s9"], [{}, True])
        self.assertEqual(r["s10"], [{"people-always": 0}, "off", False])
        self.assertEqual(r["both"], ["off", False])
        self.assertEqual(r["bad"], [[{}, {}], [{}, {}]])


class Draw(unittest.TestCase):
    """THE CARD: the seeded draw."""

    def check_card(self, card: dict, s: dict, items: list = FIXTURE) -> None:
        """What every card must be (s: its normalized settings)."""
        rows, cols = s["rows"], s["cols"]
        p = expected_pool(items, s)
        cells = card["cells"]
        self.assertEqual((card["rows"], card["cols"], card["lang"], card["code"]), (rows, cols, s["lang"], s["code"]))
        self.assertEqual(len(cells), rows * cols)
        self.assertTrue(all(list(c) == CELL_KEYS for c in cells))
        free = [i for i, c in enumerate(cells) if c["free"]]
        self.assertEqual(free, [rows // 2 * cols + cols // 2] if p["free"] else [], "FREE only on odd × odd, in the middle")
        self.assertEqual(card["free"], p["free"])
        drawn = [c["id"] for c in cells if not c["free"]]
        self.assertEqual(len(drawn), len(set(drawn)), "never a square twice")
        self.assertTrue(set(drawn) <= set(p["pool"]), "only squares of the pool")
        for c in cells:
            self.assertEqual(c["mark"], MARKS[c["type"]])
        # the pinned squares (not info) first, then the information squares up to the cap, then the rest
        need, plain = p["need"], p["pinnedPlain"]
        info = [c["id"] for c in cells if c["type"] == "info"]
        if len(plain) <= need:
            self.assertTrue(set(plain) <= set(drawn), "every pinned square")
        else:
            self.assertTrue(set(drawn) <= set(plain), "more pinned squares than places: drawn among them")
        self.assertEqual(len(info), min(p["infoTake"], need - min(len(plain), need)))
        pinned_info = [i for i in p["pinned"] if i in p["info"]]
        if len(info) <= len(pinned_info):
            self.assertTrue(set(info) <= set(pinned_info), "the pinned information squares first")
        else:
            self.assertTrue(set(pinned_info) <= set(info))

    def test_every_grid_in_both_languages(self):
        r = core(self, r"""
          const res = [];
          for (const lang of ["en", "es"]) for (let rows = 3; rows <= 10; rows++) for (let cols = 3; cols <= 10; cols++) {
            const s = G.normalize({ rows, cols, lang, code: "K7Q2", date: "2026-12-15" });
            res.push({ s: plain(s), card: plain(G.card(J, s, rows + cols)) });
          }
          out(res);""")
        self.assertEqual(len(r), 128)
        for case in r:
            with self.subTest(grid=f"{case['s']['rows']}x{case['s']['cols']}", lang=case["s"]["lang"]):
                self.check_card(case["card"], case["s"])

    def test_random_settings(self):
        """300 seeded settings, a card of each at a seeded index: a whole card by the rules, or — too few squares —
        { error: "short", have, need }, the pool's own counts (cards() says the same)."""
        cases = seeded_settings(65, 300)
        r = core(self, r"""
          const R = G.rng("draws");
          out(input.cases.map((raw) => {
            const s = G.normalize(raw), i = Math.floor(R() * s.count);
            const c = G.card(J, raw, i), all = G.cards(J, raw);
            return { s: plain(s), i, card: plain(c), cards: c.error ? plain(all) : all.length,
                     same: c.error ? null : JSON.stringify(plain(all[i])) === JSON.stringify(plain(c)) };
          }));""", data={"cases": cases})
        short = 0
        for case in r:
            s, card = case["s"], case["card"]
            with self.subTest(s=s):
                if "error" in card:
                    short += 1
                    p = expected_pool(FIXTURE, s)
                    self.assertFalse(p["ok"])
                    self.assertEqual(card, {"error": "short", "have": p["have"], "need": p["need"]})
                    self.assertEqual(case["cards"], card)
                else:
                    self.check_card(card, s)
                    self.assertEqual(card["index"], case["i"])
                    self.assertEqual(case["cards"], s["count"])
                    self.assertTrue(case["same"], "card(i) is cards()[i]")
        self.assertTrue(0 < short < 150, short)

    def test_the_same_code_and_settings_give_the_same_cards(self):
        r = core(self, r"""
          const s = { code: "K7Q2", count: 10, date: "2026-12-15" };
          const a = plain(G.cards(J, s)), b = plain(G.cards(J, s));
          const other = vm.createContext({ console });
          vm.runInContext(fs.readFileSync("src/assets/js/bingo-core.js", "utf8"), other);
          const c = plain(other.GVBingo.cards(JSON.parse(JSON.stringify(J)), s));
          const same = plain(G.cards(J, { ...s, same: true }));
          out({ a, b, c, one: a.map((x, i) => JSON.stringify(plain(G.card(J, s, i))) === JSON.stringify(x)),
                code: ids(G.card(J, { ...s, code: "GV65" }, 0)),
                lower: JSON.stringify(plain(G.card(J, { ...s, code: "k7q2" }, 0))) === JSON.stringify(a[0]),
                same: same.map((x) => [x.index, JSON.stringify(x.cells)]) });""")
        self.assertEqual(r["a"], r["b"])
        self.assertEqual(r["a"], r["c"], "on any device: another context, the squares copied")
        self.assertTrue(all(r["one"]))
        self.assertEqual([c["index"] for c in r["a"]], list(range(10)))
        sets = [frozenset(c["id"] for c in card["cells"]) for card in r["a"]]
        self.assertEqual(len(set(sets)), 10, "every card different")
        self.assertNotEqual([c["id"] for c in r["a"][0]["cells"]], [c["id"] for c in r["a"][1]["cells"]])
        self.assertNotEqual(set(r["code"]), sets[0], "another code, another card")
        self.assertTrue(r["lower"], "the code is read in capitals")
        self.assertEqual([i for i, _ in r["same"]], list(range(10)))
        self.assertEqual(len({c for _, c in r["same"]}), 1, "All cards the same")
        self.assertEqual(r["same"][0][1], json.dumps(r["a"][0]["cells"], ensure_ascii=False, separators=(",", ":")))

    def test_pins(self):
        r = core(self, r"""
          const base = { code: "PIN5", date: "2026-12-15", count: 30, infoMax: 0 };
          const many = Object.fromEntries(J.filter((it) => it.type === "check").slice(0, 12).map((it) => [it.id, 1]));
          out({ row: G.cards(J, base).map(ids), map: G.cards(J, { ...base, pin: { "read-sq-001": 1 } }).map(ids),
                unpinned: G.cards(J, { ...base, pin: { "people-always": 0 } }).map(ids),
                many: plain(G.cards(J, { ...base, rows: 3, cols: 3, pin: many })), manyIds: Object.keys(many),
                gv: G.cards(J, { ...base, pub: "lv", pin: { "listen-sq-003": 1 } }).map(ids) });""")
        self.assertTrue(all("people-always" in c for c in r["row"]), "the row's own pin: on every card")
        self.assertTrue(all("people-always" in c and "read-sq-001" in c for c in r["map"]))
        self.assertLess(sum("people-always" in c for c in r["unpinned"]), 30, "unpinned: drawn like the others")
        self.assertTrue(all("listen-sq-003" in c for c in r["gv"]), "a pin takes a Grapevine square onto La Viña cards")
        pinned = set(r["manyIds"]) | {"people-always"}
        for card in r["many"]:
            drawn = [c["id"] for c in card["cells"] if not c["free"]]
            self.assertEqual(len(drawn), 8)
            self.assertEqual(len(set(drawn)), 8)
            self.assertTrue(set(drawn) <= pinned, "more pins than places: the card is drawn among them")
        self.assertGreater(len({frozenset(c["id"] for c in card["cells"]) for card in r["many"]}), 5)

    def test_the_information_cap(self):
        """infoMax: that many information squares on each card (0 = none, whatever is pinned), the pinned ones first;
        fewer when the pool has fewer."""
        r = core(self, r"""
          const info = (cards) => cards.map((c) => c.cells.filter((x) => x.type === "info").map((x) => x.id));
          const base = { code: "INFO", date: "2026-12-15", count: 12 };
          const unpin = { "meetings-gvm": 0, "meetings-cm": 0, "meetings-mail": 0 };
          const out6 = { "meetings-site": 0, "meetings-gv-weekly": 0, "meetings-lv-weekly": 0, "meetings-find": 0,
                         "meetings-gvm": 0, "meetings-cm": 0 };
          out({ caps: [0, 1, 2, 3, 4].map((infoMax) => info(G.cards(J, { ...base, infoMax }))), dflt: info(G.cards(J, base)),
                unpinned: info(G.cards(J, { ...base, pin: unpin })), fewer: info(G.cards(J, { ...base, infoMax: 4, pick: out6 })),
                small: info(G.cards(J, { ...base, rows: 3, cols: 3, infoMax: 4 })) });""")
        for n, cards in enumerate(r["caps"]):
            with self.subTest(infoMax=n):
                for c in cards:
                    self.assertEqual(len(c), n)
                    if n <= 3:
                        self.assertTrue(set(c) <= set(PINNED_INFO))
                    else:
                        self.assertTrue(set(PINNED_INFO) <= set(c))
        self.assertEqual({frozenset(c) for c in r["caps"][3]}, {frozenset(PINNED_INFO)})
        self.assertGreater(len({frozenset(c) for c in r["caps"][2]}), 1, "two of the three pinned, drawn")
        self.assertEqual(r["dflt"], r["caps"][3], "the default cap is 3: both meetings and the e-mail on every card")
        self.assertTrue(all(len(c) == 3 for c in r["unpinned"]))
        self.assertTrue(set().union(*map(set, r["unpinned"])) - set(PINNED_INFO), "unpinned: drawn among all eight")
        self.assertTrue(all(sorted(c) == ["meetings-mail", "meetings-workshop"] for c in r["fewer"]))
        self.assertTrue(all(len(c) == 4 for c in r["small"]))

    def test_too_few_squares(self):
        plain12 = [square(f"fun-only-{i}", "check", "fun") for i in range(12)]
        some_info = [square(f"fun-only-{i}", "check", "fun") for i in range(7)] + [square(i, "info", "meetings", pin=True) for i in PINNED_INFO]
        r = core(self, r"""
          const run = (items, s) => [plain(G.card(items, s, 0)), plain(G.cards(items, s))];
          out({ ok: run(input.a, { rows: 3, cols: 3 })[0].cells.length, four: run(input.a, { rows: 4, cols: 4 }),
                ten: run(input.a, { rows: 10, cols: 10 }), info3: run(input.b, { rows: 3, cols: 4 }),
                info1: plain(G.card(input.b, { rows: 3, cols: 3, infoMax: 1 }, 0)).cells.filter((c) => c.type === "info").length,
                none: run([], {}), junk: run("not a list", {}) });""", data={"a": plain12, "b": some_info})
        self.assertEqual(r["ok"], 9)
        self.assertEqual(r["four"], [{"error": "short", "have": 12, "need": 16}] * 2)
        self.assertEqual(r["ten"], [{"error": "short", "have": 12, "need": 100}] * 2)
        self.assertEqual(r["info3"], [{"error": "short", "have": 10, "need": 12}] * 2)
        self.assertEqual(r["info1"], 1)
        self.assertEqual(r["none"], [{"error": "short", "have": 0, "need": 24}] * 2)
        self.assertEqual(r["junk"], [{"error": "short", "have": 0, "need": 24}] * 2)

    def test_short_words_on_big_grids_and_small_squares(self):
        """dense: 7 squares or more on a side, or squares smaller than SMALL_CELL inches on their sheet (two or four
        on a sheet …): every square takes its short words."""
        r = core(self, r"""
          const res = [];
          for (const [rows, cols] of [[3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [3, 10], [10, 3], [8, 5], [10, 10]])
            for (const perSheet of [1, 2, 4]) for (const paper of ["letter", "a4"]) for (const orient of ["portrait", "landscape"]) {
              const s = G.normalize({ rows, cols, perSheet, paper, orient, code: "DNS7", date: "2026-12-15" });
              const c = G.card(J, s, 0);
              res.push({ s: plain(s), dense: G.denseOf(s), cell: G.cardPlan(s).cell, card: plain(c) });
            }
          out({ res, small: G.SMALL_CELL, big: G.DENSE });""")
        self.assertEqual((r["big"], r["small"]), (7, 1.2))
        texts = {it["id"]: it for it in FIXTURE}
        fixed = {(5, 5, 1, "letter", "portrait"): False, (3, 3, 1, "letter", "portrait"): False, (7, 7, 1, "letter", "portrait"): True,
                 (3, 10, 1, "letter", "portrait"): True, (10, 3, 1, "a4", "landscape"): True, (5, 5, 2, "letter", "portrait"): True,
                 (4, 4, 4, "a4", "portrait"): True}
        for case in r["res"]:
            s = case["s"]
            key = (s["rows"], s["cols"], s["perSheet"], s["paper"], s["orient"])
            with self.subTest(case=key):
                want = s["rows"] >= 7 or s["cols"] >= 7 or case["cell"] < 1.2
                self.assertEqual(case["dense"], want)
                if key in fixed:
                    self.assertEqual(case["dense"], fixed[key])
                self.assertEqual(case["card"]["dense"], case["dense"])
                for c in case["card"]["cells"]:
                    if not c["free"]:
                        it = texts[c["id"]]
                        self.assertEqual(c["text"], (it["short"] if case["dense"] else it["text"])[s["lang"]].replace("{event}", "this event"))

    def test_the_page_says_which_words(self):
        """opts.dense — what the page measured on the squares it drew (bingo.js placeCard) — wins over the core's own
        estimate both ways, in card() and in cards(); anything but true or false leaves the estimate. The squares
        drawn and their places stay the same: only their words change."""
        r = core(self, r"""
          const s = { code: "DNS8", date: "2026-12-15", count: 3 }, big = { ...s, rows: 10, cols: 10 };
          const one = (st, opts) => plain(G.card(J, st, 1, null, opts));
          out({ est: [G.denseOf(s), G.denseOf(big)],
                five: [one(s, { dense: true }), one(s, { dense: false }), one(s), one(s, { dense: "yes" }), one(s, null)],
                ten: [one(big, { dense: false }), one(big)],
                all: plain(G.cards(J, s, null, { dense: true })).map((c) => c.dense) });""")
        self.assertEqual(r["est"], [False, True])
        texts = {it["id"]: it for it in FIXTURE}

        def words_ok(c: dict, dense: bool) -> bool:
            return c["dense"] == dense and all(x["text"] == (texts[x["id"]]["short"] if dense else texts[x["id"]]["text"])["en"]
                                               .replace("{event}", "this event") for x in c["cells"] if not x["free"])
        five, ten = r["five"], r["ten"]
        self.assertTrue(words_ok(five[0], True), "measured small: the short words on a 5×5")
        for c in five[1:]:
            self.assertTrue(words_ok(c, False), "measured roomy, or the estimate: the whole words")
        self.assertTrue(words_ok(ten[0], False), "measured roomy: the whole words on a 10×10")
        self.assertTrue(words_ok(ten[1], True))
        self.assertEqual(r["all"], [True] * 3)
        for a, b in ((five[0], five[1]), (ten[0], ten[1])):
            self.assertEqual([x["id"] for x in a["cells"]], [x["id"] for x in b["cells"]], "the same squares, the same places")

    def test_every_square_the_pool_may_draw(self):
        """poolCells — what the page measures to keep every card of a run at 6 pt (bingo.js placeCard, THE FLOOR):
        every square the pool may put on a card, once each in the items' order, exactly as card() draws it (the short
        words when dense); every square of every card is one of them; [] when the pool is too small. Not the squares
        no card can get: the information squares that are not pinned while the pinned ones fill the cap (3 of 3),
        every information square at a cap of 0; only the pinned squares when they fill the card."""
        many = [it["id"] for it in FIXTURE if it["type"] != "info" and not it["pin"] and it["cat"] in CATS][:12]
        r = core(self, r"""
          const s = { code: "POOL", date: "2026-12-15", count: 20, rows: 5, cols: 5 };
          const off = Object.fromEntries(G.CATS.map((c) => [c, false]));
          const idsIn = (cells) => plain(cells).map((c) => c.id);
          const pin = Object.fromEntries(input.many.map((id) => [id, 1]));
          out({ full: plain(G.poolCells(J, s, null, { dense: false })), dense: plain(G.poolCells(J, s, null, { dense: true })),
                est: plain(G.poolCells(J, s)).length, pool: plain(G.pool(J, s)).pool.map((it) => it.id),
                cards: plain(G.cards(J, s, null, { dense: false })).map((c) => c.cells.filter((x) => !x.free)),
                none: plain(G.poolCells(J, { ...s, cats: off })),
                zero: idsIn(G.poolCells(J, { ...s, infoMax: 0 })), four: idsIn(G.poolCells(J, { ...s, infoMax: 4 })),
                four_pool: plain(G.pool(J, { ...s, infoMax: 4 })).pool.map((it) => it.id),
                pinned: idsIn(G.poolCells(J, { ...s, rows: 3, cols: 3, pin })),
                pinnedCards: plain(G.cards(J, { ...s, rows: 3, cols: 3, pin })).map((c) => c.cells.filter((x) => !x.free).map((x) => x.id)) });""",
                 data={"many": many})
        info = set(PINNED_INFO) | set(OTHER_INFO)
        self.assertEqual([c["id"] for c in r["full"]], [i for i in r["pool"] if i not in OTHER_INFO])
        self.assertEqual([c["id"] for c in r["dense"]], [c["id"] for c in r["full"]])
        self.assertEqual(r["est"], len(r["full"]))
        self.assertEqual(r["none"], [])
        self.assertEqual(r["zero"], [i for i in r["pool"] if i not in info], "a cap of 0: no information square")
        self.assertEqual(r["four"], r["four_pool"], "a cap of 4 over 3 pinned: every information square may print")
        want = [i for i in FIXTURE_IDS if i in set(many) | {"people-always"}]
        self.assertEqual(r["pinned"], want, "the pinned squares fill a 3×3: only they")
        self.assertEqual([x for c in r["pinnedCards"] for x in c if x not in want], [])
        by_id = {c["id"]: c for c in r["full"]}
        drawn = [x for c in r["cards"] for x in c]
        self.assertGreater(len(drawn), 0)
        self.assertEqual([x for x in drawn if by_id.get(x["id"]) != x], [], "a card's square as poolCells has it")
        texts = {it["id"]: it for it in FIXTURE}
        for c in r["dense"]:
            want = ((texts[c["id"]].get("short") or {}).get("en") or texts[c["id"]]["text"]["en"]).replace("{event}", "this event")
            self.assertEqual(c["text"], want, c["id"])

    def test_the_event_words(self):
        """{event} becomes the event's name as typed — "$&" and "$1" too (a function, not a replace pattern) —, or
        "this event" / "este evento" (the page's words when it gives them)."""
        r = core(self, r"""
          const cell = (s, words) => G.card(J, { code: "EVNT", pin: { "fun-event": 1 }, ...s }, 0, words).cells
            .find((c) => c.id === "fun-event").text;
          const tricky = "$& and $1, $$ $' $` {event}";
          out({ tricky: cell({ event: tricky }), es: cell({ event: tricky, lang: "es" }), none: cell({}), noneEs: cell({ lang: "es" }),
                words: cell({}, { thisEvent: "the assembly" }), spaces: cell({ event: "  Spring \n  Assembly  " }),
                direct: [G.fillEvent("At {event}!", "$&", {}), G.fillEvent("{event}", "", { thisEvent: "x" }), G.fillEvent("{event}", "", null),
                         G.fillEvent(null, "a", {}), G.fillEvent("no place", "a", {})] });""")
        tricky = "$& and $1, $$ $' $` {event}"
        self.assertEqual(r["tricky"], f"Meet someone new at {tricky}, then again at {tricky}")
        self.assertEqual(r["es"], f"Conoce a alguien nuevo en {tricky}")
        self.assertEqual(r["none"], "Meet someone new at this event, then again at this event")
        self.assertEqual(r["noneEs"], "Conoce a alguien nuevo en este evento")
        self.assertEqual(r["words"], "Meet someone new at the assembly, then again at the assembly")
        self.assertEqual(r["spaces"], "Meet someone new at Spring Assembly, then again at Spring Assembly")
        self.assertEqual(r["direct"], ["At $&!", "x", "this event", "", "no place"])

    def test_labels_and_free_words(self):
        r = core(self, r"""
          const cards = (s, words) => G.cards(J, { code: "LABL", count: 20, date: "2026-12-15", ...s }, words).flatMap((c) => c.cells);
          out({ en: cards({}), es: cards({ lang: "es" }), words: cards({}, { label: { name: "First name", write: "" }, free: "BINGO" }),
                freeText: cards({ freeText: "  Gratis  " }).filter((c) => c.free).map((c) => c.text),
                titles: [G.wordsFor("en").title, G.wordsFor("es").title, G.wordsFor("fr").title,
                         G.wordsFor("es", { title: "Mi bingo" }).title] });""")
        own = {it["id"]: it["label"] for it in FIXTURE}
        for lang in LANGS:
            for c in r[lang]:
                with self.subTest(lang=lang, id=c["id"]):
                    if c["free"]:
                        self.assertEqual(c["text"], "FREE" if lang == "en" else "LIBRE")
                    elif c["type"] in LABEL_DEFAULT[lang]:
                        self.assertEqual(c["label"], own[c["id"]][lang] or LABEL_DEFAULT[lang][c["type"]])
                    else:
                        self.assertEqual(c["label"], "")
        self.assertTrue(any(c["label"] == "Su consejo" for c in r["es"]))
        names = [c for c in r["words"] if c["type"] == "name"]
        self.assertTrue(names and all(c["label"] == "First name" for c in names))
        self.assertTrue(all(c["label"] in ("Answer", "Their tip") for c in r["words"] if c["type"] == "write"))
        self.assertEqual({c["text"] for c in r["words"] if c["free"]}, {"BINGO"})
        self.assertEqual(set(r["freeText"]), {"Gratis"})
        self.assertEqual(r["titles"], ["Grapevine & La Viña Bingo", "Bingo de La Viña y Grapevine", "Grapevine & La Viña Bingo", "Mi bingo"])

    def test_weights(self):
        """Over 400 cards of 3×3 from 30 squares: one of weight 5 far more often than one of weight 0.5."""
        items = [square(f"fun-w-{i:02d}", "check", "fun", weight={0: 5, 1: 0.5}.get(i, 1)) for i in range(30)]
        r = core(self, r"""
          const n = {};
          for (let i = 0; i < 400; i++) for (const id of ids(G.card(J, { rows: 3, cols: 3, free: false, code: "WGHT" }, i))) n[id] = (n[id] || 0) + 1;
          out(n);""", items=items)
        heavy, light = r.get("fun-w-00", 0), r.get("fun-w-01", 0)
        others = [v for k, v in r.items() if k not in ("fun-w-00", "fun-w-01")]
        self.assertGreater(heavy, 2 * max(others))
        self.assertLess(light, min(others))
        self.assertEqual(sum(r.values()), 400 * 9)


class Link(unittest.TestCase):
    """THE LINK: "Copy a link to these settings" and a page opened with one."""

    def test_a_link_gives_the_same_settings_and_cards_back(self):
        """300 seeded settings — typed words with & = # % + in them, accents, emoji, other scripts, line breaks, too
        long —: fromHash(encode(s)) is normalize(s), on the defaults (a link made on /es/ opened on the English page
        still makes its own language's cards), and the same cards."""
        cases = seeded_settings(2027, 300)
        r = core(self, r"""
          out(input.cases.map((raw, k) => {
            const n = plain(G.normalize(raw)), h = G.encode(raw), other = n.lang === "es" ? "en" : "es";
            const back = G.fromHash(h), onOther = G.fromHash(h, { lang: other });
            const res = { n, h, back: plain(back), decoded: plain(G.normalize(G.decode(h))), other: onOther.lang };
            if (k < 60) res.cards = JSON.stringify(plain(G.cards(J, back))) === JSON.stringify(plain(G.cards(J, raw)));
            return res;
          }));""", data={"cases": cases})
        texts = 0
        for case in r:
            n, h = case["n"], case["h"]
            with self.subTest(h=h[:200]):
                self.assertEqual(case["back"], n)
                self.assertEqual(case["decoded"], n)
                self.assertEqual(case["other"], n["lang"])
                self.assertRegex(h, r"^#grid=\d{1,2}x\d{1,2}(&|$)")
                self.assertIn(f"&lang={n['lang']}", h)
                self.assertRegex(h, r"^#[A-Za-z0-9%._~!*'()\-=&]*$", "every typed character percent-encoded")
                self.assertEqual(f"&code={n['code']}" in h, bool(n["code"]))
                if case.get("cards") is not None:
                    self.assertTrue(case["cards"], "the same link, the same cards")
                texts += any(n[k] and re.search(r"[&=#%+\n]|[^\x00-\x7f]", n[k]) for k in ("title", "event", "freeText", "rules"))
        self.assertGreater(texts, 50, "the hard characters were tried")

    def test_only_what_differs(self):
        r = core(self, r"""
          out([{}, { code: "k7q2" }, { infoMax: 3 }, { infoMax: 2, color: false, cats: { history: false, fun: false } },
               { pick: { "b-sq": 1, "a-sq": 1, "c-sq": 0 }, pin: { "x-sq": 0 }, lang: "es", rows: 4, cols: 6, perSheet: 2 },
               { title: "A & B = C", event: "50% #1", date: "2027-03-14", same: true, count: 1 }].map((s) => G.encode(s)));""")
        self.assertEqual(r, ["#grid=5x5&lang=en",
                             "#grid=5x5&code=K7Q2&lang=en",
                             "#grid=5x5&lang=en",
                             "#grid=5x5&lang=en&off=fun.history&info=2&bw=1",
                             "#grid=4x6&lang=es&in=a-sq.b-sq&out=c-sq&unpin=x-sq&per=2",
                             "#grid=5x5&cards=1&same=1&lang=en&title=A%20%26%20B%20%3D%20C&event=50%25%20%231&date=2027-03-14"])

    def test_a_bad_or_hostile_link_is_ignored(self):
        """A garbled, unknown or out-of-range value is skipped (never clamped), a link without a bingo setting is no
        link (null), nothing throws and no prototype is touched — also for 300 seeded random strings."""
        r = core(self, r"""
          const hand = ["", "#", "#main", "#=", "#&&&", "#grid", "#grid=", "#grid=99x2&code=!!&cards=900", "#grid=2x5", "#grid=5x5x5",
            "#grid=4x6&cards=900&info=9&per=3&paper=a5&date=2026-02-30&code=IO01&lang=fr&mag=all&where=moon&bw=2&same=yes",
            "#title=%E0%A4%A&grid=3x3", "#__proto__=1&constructor=2&toString=3&grid=3x3", "#in=__proto__.constructor.ok-id&grid=3x3",
            "#off=__proto__.Bad.fun&grid=3x3", "#grid=5x5&title=" + "a".repeat(61), "#rules=line1%0Aline2&title=a%0Ab&grid=5x5",
            "#grid=5x5&cards=07&info=+1", "#grid=5x5&event=%00null", "#grid=5x5&" + "title=a&".repeat(5000), "%", "#%%%&&==",
            "#grid=10x10&grid=3x3", "#cards=60&cards=61", null, undefined, 42, {}, [], "#code=k7q2&code=K7Q2X9Z"];
          const R = G.rng("hostile"), alphabet = "#&=%+.x_-09azAZéñ🍇\n ";
          const keys = ["grid", "code", "cards", "same", "lang", "mag", "where", "title", "event", "date", "free", "freetext", "off",
                        "info", "in", "out", "pin", "unpin", "per", "paper", "orient", "bw", "names", "howto", "rules", "strip", "__proto__"];
          const random = [];
          for (let i = 0; i < 300; i++) {
            let h = R() < 0.5 ? "#" : "";
            const parts = Math.floor(R() * 6);
            for (let p = 0; p < parts; p++) {
              if (p) h += "&";
              if (R() < 0.7) h += keys[Math.floor(R() * keys.length)] + "=";
              const n = Math.floor(R() * 12);
              for (let c = 0; c < n; c++) h += Array.from(alphabet)[Math.floor(R() * Array.from(alphabet).length)];
            }
            random.push(h);
          }
          const res = [], errors = [];
          for (const h of [...hand, ...random]) {
            try {
              const back = G.fromHash(h), dec = G.decode(h);
              res.push({ h: typeof h === "string" ? h.slice(0, 120) : String(h), back: back === null ? null : plain(back),
                         dec: plain(dec), again: back === null ? null : plain(G.normalize(dec)) });
            } catch (e) { errors.push([String(h).slice(0, 80), String(e)]); }
          }
          out({ res, errors, polluted: polluted(), hand: hand.length });""")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["polluted"], 0)
        res = r["res"]
        self.assertEqual(len(res), r["hand"] + 300)
        for case in res:
            with self.subTest(h=case["h"]):
                self.assertTrue(set(case["dec"]) <= set(DEFAULTS), case["dec"])
                if case["back"] is None:
                    self.assertEqual(case["dec"], {})
                else:
                    self.assertEqual(settings_problems(case["back"]), [])
                    self.assertEqual(case["back"], case["again"])
        by = {c["h"]: c for c in res}

        def only(h: str, **want) -> None:
            self.assertEqual(by[h[:120]]["back"], {**DEFAULTS, **want}, h)
        for h in ("", "#", "#main", "#=", "#&&&", "#grid", "#grid=", "#grid=99x2&code=!!&cards=900", "#grid=2x5", "#grid=5x5x5", "%",
                  "#%%%&&=="):
            self.assertIsNone(by[h]["back"], h)
        only("#grid=4x6&cards=900&info=9&per=3&paper=a5&date=2026-02-30&code=IO01&lang=fr&mag=all&where=moon&bw=2&same=yes", rows=4, cols=6)
        only("#title=%E0%A4%A&grid=3x3", rows=3, cols=3)
        only("#__proto__=1&constructor=2&toString=3&grid=3x3", rows=3, cols=3)
        only("#in=__proto__.constructor.ok-id&grid=3x3", rows=3, cols=3, pick={"constructor": 1, "ok-id": 1})
        only("#off=__proto__.Bad.fun&grid=3x3", rows=3, cols=3, cats={"fun": False})
        only("#grid=5x5&title=" + "a" * 61)
        only("#rules=line1%0Aline2&title=a%0Ab&grid=5x5", rules="line1\nline2")
        only("#grid=5x5&cards=07&info=+1", count=7)
        only("#grid=5x5&event=%00null")
        only("#grid=10x10&grid=3x3", rows=3, cols=3)
        only("#cards=60&cards=61", count=60)
        only("#code=k7q2&code=K7Q2X9Z", code="K7Q2")
        self.assertIsNone(by[("#grid=5x5&" + "title=a&" * 5000)[:120]]["back"], "a link that long is no link")
        for h in ("null", "undefined", "42", "[object Object]", ""):
            self.assertIsNone(by[h]["back"])


class Module(unittest.TestCase):
    API = ["VERSION", "LANGS", "PUBS", "WHERES", "CATS", "MARKS", "LABELLED", "PAPERS", "ORIENTS", "PER_SHEET", "LIMITS", "TEXT_MAX",
           "DENSE", "SMALL_CELL", "ALPHABET", "MARGIN", "GAP", "SIDE", "MIN_PT", "MAX_PT", "WORDS", "DEFAULTS", "normalize",
           "cleanCode", "newCode", "freeOn", "needOf", "perSheetOf", "perSheetChoices", "rng", "seedOf", "why", "offered",
           "isPinned", "pool", "catCounts", "setPick", "setPin", "pickRows", "wordsFor", "fillEvent", "denseOf", "card", "cards",
           "poolCells", "encode", "decode", "fromHash", "sheetPlan", "cardPlan", "layout", "fontGuess", "headPieces"]

    def test_the_module_and_its_plain_script(self):
        r = core(self, r"""
          const w = {};
          vm.runInContext(fs.readFileSync("src/assets/js/bingo-core.js", "utf8"), vm.createContext({ window: w }));
          out({ keys: Object.keys(G), browser: Object.keys(w.GVBingo), lists: [G.LANGS, G.PUBS, G.WHERES, G.CATS, G.MARKS, G.LIMITS],
                first: G.rng(1)(), word: G.rng("bingo")() === G.rng("bingo")(), seed: [G.seedOf(""), G.seedOf(null), G.seedOf(-7)] });""")
        self.assertEqual(r["keys"], self.API)
        self.assertEqual(r["browser"], self.API, "window.GVBingo in a browser")
        self.assertEqual(r["lists"], [list(LANGS), ["both", "gv", "lv"], ["any", *WHERES], CATS, MARKS,
                                      {"rows": [3, 10], "cols": [3, 10], "count": [1, 60], "infoMax": [0, 4]}])
        self.assertAlmostEqual(r["first"], 0.6270739405881613)      # mulberry32(1)'s first number
        self.assertTrue(r["word"])
        self.assertEqual(r["seed"], [0, 0, 7])
        src = (ROOT / CORE).read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = "\n".join(line.split("//")[0] for line in code.splitlines())
        # an older phone runs it: no optional chaining, no ??, no modules, no arrow functions or let / const; pure: no
        # page, no storage, no network, no clock
        self.assertNotRegex(code, r"\?\.[A-Za-z_(\[]|\?\?|^\s*(import|export)\s")
        for bad in ("=>", "let ", "const ", "class ", "async ", "document", "window.", "localStorage", "sessionStorage", "fetch(",
                    "navigator", "XMLHttpRequest", "indexedDB", "location", "Date.now", "new Date()", "innerHTML", "eval("):
            self.assertNotIn(bad, code, bad)
        self.assertIn('typeof window !== "undefined" ? window : globalThis', code)
        # the build runs this very file (eleventy/filters/bingo-sample.js bingoCore()), never a copy of it
        sample_js = (ROOT / "eleventy" / "filters" / "bingo-sample.js").read_text(encoding="utf-8")
        self.assertIn(f'const CORE = "{CORE}";', sample_js)
        self.assertIn("vm.runInContext(fs.readFileSync(path.resolve(ROOT, CORE)", sample_js)
        self.assertIn(f'code: "{SAMPLE_CODE}"', sample_js)

    def test_addresses_and_times_break_alike(self):
        """An address breaks at the same places in the builder's squares and strip (bingo.js breakable), in the core's
        size guess (bingo-core.js addressPieces) and on the no-JS sample (eleventy/filters/bingo-sample.js
        bingoBreaks, on words escaped first): one ADDRESS in all three; an e-mail only after its "@", the site's
        address after a "/" and before a "."; a time range kept on one line (bgo-nb, as bingo.js textIn) — and
        nothing inside an escaped word's entities."""
        rx = re.compile(r"(?:var|const) ADDRESS = (/.+?/gi);")
        found = {f: rx.findall(read(ROOT / f)) for f in ("src/assets/js/bingo.js", CORE, "eleventy/filters/bingo-sample.js")}
        self.assertEqual({f: len(v) for f, v in found.items()}, {f: 1 for f in found}, "one ADDRESS each")
        self.assertEqual(len({v[0] for v in found.values()}), 1, found)
        cases = {"Write to us: grapevine@neta65.org": "Write to us: grapevine@<wbr>neta65.org",
                 "Listen on neta65.github.io/aagrapevine: podcasts": "Listen on neta65<wbr>.github<wbr>.io/<wbr>aagrapevine: podcasts",
                 "Share at aalavina.org/comparte.": "Share at aalavina<wbr>.org/<wbr>comparte.",
                 "1st Wednesday of the month, 7\u2009\u2013\u20098\u202fPM Central":
                     "1st Wednesday of the month, <span class=\"bgo-nb\">7\u2009\u2013\u20098</span>\u202fPM Central",
                 "cada primer miércoles del mes, 7\u20138 p.\u00a0m.": "cada primer miércoles del mes, <span class=\"bgo-nb\">7\u20138</span> p.\u00a0m.",
                 "a@b&quot;&gt;&lt;img src=x onerror=__h2=1&gt;": "a@<wbr>b&quot;&gt;&lt;img src=x onerror=__h2=1&gt;",
                 "&lt;/script&gt;&lt;script&gt;__h1=1&lt;/script&gt; &#39;q&#39; 1999&#8211;2026": None}
        r = run_js(self, r"""
          const { bingoBreaks } = await imp("eleventy/filters/bingo-sample.js");
          out(input.map((t) => bingoBreaks(t)));""", data=list(cases))
        self.assertEqual(r, [want if want is not None else got for got, want in cases.items()])


    def test_a_long_typed_piece_of_the_head_breaks_where_it_can(self):
        """headPieces — where the builder lets a typed title or event go on two lines (bingo.js headIn puts a <wbr>
        there), so a long piece with no space breaks where it reads well rather than widen the head's column and make
        the squares smaller (bingo.js chooseLayout, THE FLOOR): a pasted meeting link after its "/" runs and its dots,
        an e-mail after its "@" and its dot, a hashtag between its words; a piece under 12 characters never ("A.A.",
        "iPhone"), a long word with no place to break neither (it breaks anywhere: bingo.css overflow-wrap). The
        pieces always join back into the words as typed."""
        cases = {
            "Zoom: https://us02web.zoom.us/j/83412345678": ["Zoom: https://", "us02web.", "zoom.", "us/", "j/", "83412345678"],
            "Bingo at grapevine.neta65.org/gvr/bingo": ["Bingo at grapevine.", "neta65.", "org/", "gvr/", "bingo"],
            "Write us: grapevine@neta65.org": ["Write us: grapevine@", "neta65.", "org"],
            "#NETA65GrapevineLaVinaFallAssembly2027": ["#NETA65Grapevine", "La", "Vina", "Fall", "Assembly2027"],
            "Grapevine-Gemeinschaftsversammlungsbingo": ["Grapevine-", "Gemeinschaftsversammlungsbingo"],
            "Taller_de_La_Viña_en_Garland": ["Taller_", "de_", "La_", "Viña_", "en_", "Garland"],
            "MacDonaldLaViñaÑandú": ["Mac", "Donald", "La", "Viña", "Ñandú"],
            "Supercalifragilisticexpialidociousgrapevinega": ["Supercalifragilisticexpialidociousgrapevinega"],
            "A.A. Grapevine Bingo at the iPhone table": ["A.A. Grapevine Bingo at the iPhone table"],
            "Reunión de Compañerismo, 1.er miércoles": ["Reunión de Compañerismo, 1.er miércoles"],
            "...dots... and trailing/ slashes/": ["...dots... and trailing/ slashes/"],
            "": [""],
        }
        r = core(self, "out(input.cases.map((t) => G.headPieces(t)).concat([G.headPieces(null), G.headPieces(42)]));",
                 data={"cases": list(cases)})
        self.assertEqual(r[:-2], list(cases.values()))
        self.assertEqual(r[-2:], [[""], ["42"]], "anything that is not words: the words it has")
        self.assertEqual([("".join(p), t) for p, t in zip(r, cases) if "".join(p) != t], [], "the pieces join back")


# ------------------------------------------------------------------------------------------------ the words
def ui_calls(js: str) -> list[tuple[list[str], set[str] | None]]:
    """Each ui(…) call of the script: (the keys it may ask for — a condition may choose between two —, the
    placeholders it fills in, or None when it fills in none)."""
    out = []
    for m in re.finditer(r"\bui\(([^\n]*)", js):
        args = m.group(1)
        head = args.split("{", 1)[0]
        keys = re.findall(r"""(?<![=!]== )(?<!== )["']([a-z0-9_]+)["']""", head)
        if not keys:
            continue
        filled = re.match(r"[^{]*\{([^}]*)\}", args)
        out.append((keys, set(re.findall(r"(\w+)\s*:", filled.group(1))) if filled else None))
    return out


class Strings(unittest.TestCase):
    """The words the page, the teaser and the builder use (src/_i18n/bingo.json, read.json's read.gvr.bingo_*)."""

    def setUp(self):
        self.s = i18n()
        self.js = read(APP)
        self.page = read(PAGE)
        self.gvr = read(GVR)

    def has(self, key: str, where: str) -> None:
        with self.subTest(key=key, used=where):
            self.assertIn(key, self.s)
            for L in LANGS:
                self.assertTrue(self.s[key][L].strip(), f"{key}: no {L} words")

    def test_every_key_the_templates_name(self):
        for name, src in (("gvr-bingo.njk", self.page), ("gvr.njk", self.gvr)):
            keys = re.findall(r"""["']((?:bingo|read\.gvr|search\.kw)\.[a-z0-9_.]+)["']\s*\|\s*t\b""", src)
            if name == "gvr.njk":
                keys = [k for k in keys if k.startswith(("bingo.", "read.gvr.bingo", "read.gvr.nav_bingo"))]
            self.assertGreater(len(keys), 5 if name == "gvr.njk" else 40, name)
            for k in keys:
                self.has(k, name)
            # the card's words the templates put together: (C + "title"), (cw + "name_line") …
            for k in re.findall(r"""\((?:C|cw) \+ ["']([a-z0-9_]+)["']\)\s*\|\s*t\b""", src):
                self.has("bingo.card." + k, name)
        for k in ("read.gvr.nav_bingo", *(f"read.gvr.bingo_p{n}" for n in (1, 2, 3)), "search.kw.bingo"):
            self.has(k, "gvr.njk / library.js")
        # the families the page builds a key from
        tips = re.search(r"\{%- for tip in \[(.*?)\] %\}", self.page).group(1).count('["')
        self.assertEqual(tips, 4)
        for n in range(1, tips + 1):
            self.has(f"bingo.tip{n}", "the tips")
            self.has(f"bingo.tip{n}_t", "the tips")
        for k in ("paper_letter", "paper_a4", "orient_portrait", "orient_landscape", "pub_both"):
            self.has("bingo." + k, "the builder")
        for w in ("any", *WHERES):
            self.has("bingo.where." + w, "Where are you taking it?")
        for c in CATS:
            self.has("bingo.cat." + c, "the categories")

    def test_every_word_the_script_asks_for(self):
        """bingo.js reads the builder's words (ui) and the card's (cw) from #bingo-data, where the page hands them over
        by prefix (tGroup): the build's I18N_STRICT never sees a missing one — this does; and every {placeholder} in
        them is one the script fills in."""
        calls = ui_calls(self.js + self.page)
        asked = {k for keys, _ in calls for k in keys}
        self.assertGreater(len(asked), 12)
        for k in sorted(asked):
            self.has("bingo.ui." + k, "bingo.js ui()")
        for keys, filled in calls:
            for k in keys:
                for L in LANGS:
                    with self.subTest(key=k, lang=L):
                        self.assertLessEqual(set(re.findall(r"\{(\w+)\}", self.s["bingo.ui." + k][L])), filled or set())
        card = set(re.findall(r"\bcw(?:\(\))?\.([a-z][a-z0-9_]*)", self.js + self.page))
        self.assertGreater(len(card), 15)
        for k in sorted(card):
            self.has("bingo.card." + k, "bingo.js cw")
        for m in re.finditer(r"\bfmt\(([^{]*)\{([^}]*)\}\)", self.js):
            filled = set(re.findall(r"(\w+)\s*:", m.group(2)))
            for k in re.findall(r"\bcw\.([a-z_]+)", m.group(1)):
                for L in LANGS:
                    with self.subTest(key=k, lang=L):
                        self.assertLessEqual(set(re.findall(r"\{(\w+)\}", self.s["bingo.card." + k][L])), filled)
        # every builder word the page hands over is one the script uses (no word for nothing)
        self.assertEqual({k for k in group(self.s, "bingo.ui.", "en")}, asked)

    def test_the_cores_own_words_are_the_pages(self):
        """bingo-core.js WORDS (for Node, the tests and anything the page leaves out) are the page's card words."""
        r = core(self, "out(plain(G.WORDS));")
        for L in LANGS:
            cw = group(self.s, "bingo.card.", L)
            with self.subTest(lang=L):
                self.assertEqual(r[L], {"title": cw["title"], "free": cw["free"], "thisEvent": cw["this_event"],
                                        "label": {t: cw["label_" + t] for t in ("name", "phone", "write", "sign")}})
                self.assertEqual(cw["title"], self.s["bingo.title"][L], "the card's title is the page's name")

    def test_aa_wording(self):
        """No money asks, first names only (never a last name; the card's own note says so), "service", never "job";
        a Spanish text that names both magazines names La Viña first. (The squares' words: the CSV checker's.)"""
        words = {k: v for k, v in self.s.items() if k.startswith(("bingo.", "read.gvr.bingo", "read.gvr.nav_bingo", "search.kw.bingo"))}
        self.assertGreater(len(words), 150)
        for k, v in words.items():
            for L in LANGS:
                with self.subTest(key=k, lang=L):
                    self.assertNotRegex(v[L], r"(?i)\bjobs?\b|donat|donaci|contribution|selfie|full name|last name|surname|apellido|"
                                              r"nombre completo|conference-approved|buy now|hurry|limited time")
            es = v["es"]
            if "Grapevine" in es and "La Viña" in es:
                with self.subTest(key=k, rule="La Viña first"):
                    self.assertLess(es.index("La Viña"), es.index("Grapevine"))
        self.assertRegex(self.s["bingo.card.anon"]["en"], r"(?i)first names")
        self.assertRegex(self.s["bingo.card.anon"]["es"], r"(?i)nombres de pila")


# ------------------------------------------------------------------------------------------------ the real file
class RealContent(unittest.TestCase):
    """content/bingo/bingo.csv and config/site.yml as they are today, through a build of their own (built_real: the
    two bingo pages from the committee's file) — the committee edits them: CONTENT_TESTS in scripts/ops/gate_tests.py,
    the Code check judges them, the gate before publishing does not."""

    def setUp(self):
        self.b = built_real(self)

    def test_a_large_pool_on_both_pages(self):
        for L in LANGS:
            items = self.b["data"][L]["items"]
            with self.subTest(lang=L):
                self.assertGreaterEqual(len(items), 200)
                self.assertGreaterEqual(len([it for it in items if it["text"][L]]), 200)

    def test_our_meetings_and_our_e_mail(self):
        """The e-mail, and both meetings' three lines on the page (#bingo-data info, what the card's strip chooses
        from): the long one with the time zone as the site writes it ("Central", "(hora del Centro)") and the place,
        the mid one the same place, the short one neither (the words themselves: tests/test_bingo_csv.py)."""
        info = self.b["data"]["en"]["info"]
        self.assertEqual(info["email"], "grapevine@neta65.org")
        for m in ("gvMeeting", "committeeMeeting"):
            for suf in ("", "Mid", "Short"):
                self.assertIsNotNone(info[m + suf], m + suf)
                self.assertTrue(info[m + suf]["en"].strip() and info[m + suf]["es"].strip(), m + suf)
            long, mid, short = info[m], info[m + "Mid"], info[m + "Short"]
            with self.subTest(meeting=m):
                self.assertIn(" Central", long["en"])
                self.assertIn("(hora del Centro)", long["es"])
                for L in LANGS:
                    place = mid[L].rsplit(" · ", 1)[-1]
                    self.assertTrue(len(mid[L].split(" · ")) == 3 and long[L].endswith(place), (L, long[L], mid[L]))
                    self.assertNotRegex(mid[L] + short[L], r"Central|hora del Centro")
                    self.assertNotIn(place, short[L])

    def test_both_meetings_and_the_e_mail_on_the_default_card(self):
        """The three squares pinned "Always on every card" — our Grapevine Meeting, the committee meeting, how to write
        to us — and the cap of 3: on the sample card in both languages, and in its strip (the long lines)."""
        x = sample(self, real=True)
        for L in LANGS:
            info = self.b["data"][L]["info"]
            card = self.b["soup"][BINGO[L]].select_one(".bgo-nojs .bgo-sample article.bgo-card")
            squares = [words_of(c.select_one(".bgo-txt")) for c in card.select('.bgo-cell[data-type="info"]')]
            with self.subTest(lang=L):
                self.assertEqual(len(squares), 3)
                self.assertEqual(len(x[L]["pinnedInfo"]), 3)
                for want in (info["gvMeeting"][L], info["committeeMeeting"][L], info["email"]):
                    self.assertEqual(len([s for s in squares if want in s]), 1, want)
                strip = card.select_one(".bgo-info").get_text("")
                for want in (info["gvMeeting"][L], info["committeeMeeting"][L], info["email"]):
                    self.assertIn(want, strip)

    def test_the_sample_card_is_the_cores(self):
        """The committee's squares on the no-JS sample: square for square card 0 the core draws from them (what
        Sample checks on the fixture pool), each square's words at 6 pt or more ON PAPER (the floor for every printed
        card): the sample prints at areas/bingo.css's zoom for it (0.94: it fits A4 too), so its sizes times that."""
        css = (ROOT / "src" / "assets" / "css" / "areas" / "bingo.css").read_text(encoding="utf-8")
        zoom = float(re.search(r":root:not\(\.js\) \.bgo-sample-stage > \.bgo-card \{ zoom: ([\d.]+);", css).group(1))
        self.assertGreaterEqual(SAMPLE_FLOOR * zoom, 6, "the template's floor (gvr-bingo.njk sampleCard) prints at 6 pt or more")
        x = sample(self, real=True)
        for L in LANGS:
            card = self.b["soup"][BINGO[L]].select_one(".bgo-nojs .bgo-sample article.bgo-card")
            want = x[L]["card"]
            with self.subTest(lang=L):
                self.assertNotIn("error", want, "the committee's squares fill a 5×5 card")
                cells = card.select(".bgo-cell")
                self.assertEqual([words_of(c.select_one(".bgo-txt")) for c in cells], [w["text"] for w in want["cells"]])
                sizes = [float(re.search(r"font-size:([\d.]+)pt", c.select_one(".bgo-w")["style"]).group(1)) for c in cells]
                self.assertGreaterEqual(min(sizes) * zoom, 6, sizes)

if __name__ == "__main__":
    unittest.main()
