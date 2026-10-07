"""The settings in config/ and the code that reads them agree: no setting that does nothing, no read of a
setting that is not there.

  * Every setting is read — config/site.yml, every key at every depth, and the other settings files the build
    reads (config/expenses.yml, carry.yml, history.yml, orientation.yml): the key's name is read — `.name`,
    `["name"]`, `.get("name" …)` or "name" in a list of keys — by a code file (scripts/, eleventy/, the
    eleventy config, src/ templates, data files and scripts, the workflows) that also names the key's section
    (its parent key). Comments do not count. A "<name>_es" key counts as read when "<name>" is: the pages'
    `pick` / `langLink` and the sync's language helpers take the Spanish twin of a setting by that rule. Keys
    whose names are data (a map from months or region names) and keys read under a name the code builds are
    listed below, each with its reason.
  * Every setting the code reads is there, or the code gives a default — `site.…` in the templates
    (src/**/*.njk, also through `{% set L = site.links %}`), `site.…` / `data.site.…` and their aliases in the
    JS that builds the pages (eleventy/, src/_data/, src/pages/*.11ty.js, eleventy.config.js; and the files
    that load config/site.yml themselves), and in the Python sync every chain of `["key"]` / `.get("key")`
    from load_config() (followed through variables and loops). A default: `or …`, `| default(…)`, `||`, `??`,
    `?.`, `.get(key, default)`, or the read being the test of an `if` / `and` / `? :`. `site` is what
    src/_data/site.js makes: config `site:` itself, the sections it passes on (meeting, links, sources …) and
    the values it works out (built, url, repository, timezone).
  * Both checks are shown to fail on purpose: a made-up setting nothing reads, and misspelled reads in a
    template, the build's JS and the sync's Python (temporary inputs, nothing written).

    python -m unittest tests.test_settings_used -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import ast
import copy
import os
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# The settings files the build or the sync reads (config/presentations/*.yml are the slide decks' content,
# checked by tests/test_presentations_build.py).
SETTINGS_FILES = ["config/site.yml", "config/expenses.yml", "config/carry.yml", "config/history.yml",
                  "config/orientation.yml"]
# Where code that reads settings lives (tests/ do not count: a setting only a test reads does nothing).
CODE_DIRS = ["scripts", "eleventy", "src/_data", "src/pages", "src/_includes", "src/assets/js", ".github/workflows"]
CODE_FILES = ["eleventy.config.js"]

# Keys whose NAMES are data, not settings: their children are checked as children of the map itself.
MAP_LIKE = {
    "config/site.yml": {
        # an office's own region names (as its meeting list writes them) → the meeting types they add
        "meetings.feeds[].region_types": "the keys are the office's region names, matched against its meetings",
    },
    "config/carry.yml": {
        # one entry per month: carry.js picks this month's tips by its "YYYY-MM" key
        "tips": "the keys are months (YYYY-MM): src/_data/carry.js takes the current month's",
    },
}
# Keys read under a name the code builds (none today; an entry needs its reason).
DYNAMIC: dict[str, dict[str, str]] = {}

# --- the `site` the pages get (src/_data/site.js)
SITE_SECTIONS = {"meeting", "recurring_events", "drive", "sources", "links", "phone_access", "digest",
                 "lavina_weekly_open", "meetings", "spotlight"}
SITE_COMPUTED = {"built", "url", "repository", "timezone"}
# Settings site.js always fills in, so the pages have them even when config/site.yml leaves them out (as its notes
# allow): their path in `site` → what site.js gives.
SITE_DEFAULTED = {
    ("meeting", "platform"): 'config "meeting: platform" (leave out: Zoom) — site.js gives "Zoom" when it is missing',
}
# Not setting names: what JavaScript / Nunjucks ask of a value (a list's length, a text's methods …).
NOT_KEYS = {"length", "startsWith", "endsWith", "slice", "indexOf", "replace", "split", "map", "filter", "find",
            "some", "every", "includes", "join", "trim", "toString", "concat", "forEach", "keys", "values",
            "entries", "toLowerCase", "toUpperCase", "flatMap", "reduce"}
# A `site` that is not the pages' settings: (file, the name read, why).
OTHER_SITE = {
    ("eleventy/filters/booth.js", "url_es"):
        "boothShow's own `site` for the booth screen ({ url, url_es, base, host, committee_en, committee_es })",
}

NAME = r"[A-Za-z_][\w-]*"


# ============================================================================ reading the code
def strip_js(src: str, blank: bool = False) -> str:
    """JavaScript without its comments; strings and regular expressions are kept as they are — or, with
    `blank`, as spaces between their delimiters (an i18n key "site.tagline" is then no read of `site`, and a
    brace in a text or a pattern is no block)."""
    def keep(s: str) -> str:
        if not blank or len(s) < 2:
            return s
        if s[0] != "`":
            return s[0] + re.sub(r"[^\n]", " ", s[1:-1]) + s[-1]
        # a template literal: its ${…} parts are code
        out, k, depth = [s[0]], 1, 0
        while k < len(s) - 1:
            if depth == 0 and s.startswith("${", k):
                out.append("${")
                k, depth = k + 2, 1
                continue
            if depth:
                depth += {"{": 1, "}": -1}.get(s[k], 0)
                out.append(s[k])
            else:
                out.append("\n" if s[k] == "\n" else " ")
            k += 1
        return "".join(out) + s[-1]
    out, i, n, prev = [], 0, len(src), ""
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(keep(src[i:j + 1]))
            i, prev = j + 1, c
            continue
        if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^"):      # a regular expression
            j, in_class = i + 1, False
            while j < n and (src[j] != "/" or in_class) and src[j] != "\n":
                if src[j] == "\\":
                    j += 2
                    continue
                in_class = True if src[j] == "[" else False if src[j] == "]" else in_class
                j += 1
            out.append(keep(src[i:j + 1]))
            i, prev = j + 1, "/"
            continue
        out.append(c)
        prev = prev if c.isspace() else c
        i += 1
    return "".join(out)


def strip_njk(src: str) -> str:
    """A template without its {# comments #} and <!-- comments --> (each one blanked, its lines kept: the line
    numbers of what follows stay right)."""
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r"<!--.*?-->", blank, re.sub(r"\{#.*?#\}", blank, src, flags=re.S), flags=re.S)


def text_names(text: str) -> tuple[set[str], set[str]]:
    """(names read as `.name` or "name", every word) of a JS / template / workflow text."""
    read = set(re.findall(r"\.\s*(" + NAME + ")", text)) | set(re.findall(r"[\"'`](" + NAME + r")[\"'`]", text))
    return read, set(re.findall(NAME, text))


def py_names(src: str) -> tuple[set[str], set[str]]:
    """(names read as an attribute or a string "name", every word) of a Python file — comments left out."""
    read, words = set(), set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if re.fullmatch(NAME, node.value):
                read.add(node.value)
            words.update(re.findall(NAME, node.value))
        elif isinstance(node, ast.Attribute):
            read.add(node.attr)
            words.add(node.attr)
        elif isinstance(node, ast.Name):
            words.add(node.id)
        elif isinstance(node, ast.keyword) and node.arg:
            words.add(node.arg)
    return read, words


def code_files() -> list[Path]:
    out = [ROOT / f for f in CODE_FILES]
    for d in CODE_DIRS:
        out += sorted(p for p in (ROOT / d).rglob("*") if p.suffix in (".py", ".js", ".mjs", ".njk", ".yml", ".yaml"))
    return out


def code_index(files: list[Path] | None = None, extra: dict[str, str] | None = None) -> dict[str, tuple[set, set]]:
    """{file: (names it reads, its words)} for every code file (+ `extra`: {name: text} as given)."""
    out = {}
    items = [(p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8")) for p in (files or code_files())]
    for name, text in items + list((extra or {}).items()):
        if name.endswith(".py"):
            out[name] = py_names(text)
        elif name.endswith((".js", ".mjs")):
            out[name] = text_names(strip_js(text))
        elif name.endswith(".njk"):
            out[name] = text_names(strip_njk(text))
        else:
            out[name] = text_names(re.sub(r"(?m)^\s*#.*$", "", text))
    return out


# ============================================================================ every setting is read
def key_paths(obj, path: tuple = ()):
    """Every key of a settings tree as a path: ("meetings", "feeds", "[]", "id") — "[]" for a list's entries."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + (str(k),)
            yield p
            yield from key_paths(v, p)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                yield from key_paths(v, path + ("[]",))


def shown(path: tuple) -> str:
    return ".".join(path).replace(".[]", "[]")


def unread_settings(cfg: dict, index: dict, map_like: dict[str, str] | None = None,
                    dynamic: dict[str, str] | None = None) -> list[str]:
    """The keys of `cfg` no code file reads (see the module's docstring), in file order."""
    map_like, dynamic = map_like or {}, dynamic or {}

    def read_by_some_file(name: str, parent: str) -> bool:
        return any(name in read and (not parent or parent in words) for read, words in index.values())

    out = []
    for path in key_paths(cfg):
        here = shown(path)
        if here in dynamic or any(here == m for m in map_like):
            continue
        parent_map = next((m for m in map_like if here.startswith(m + ".")), None)
        if parent_map:
            rest = here[len(parent_map) + 1:]
            if "." not in rest and "[" not in rest:
                continue                                    # a map's own key: data
            segs = [parent_map.split(".")[-1].split("[")[0]] + [s for s in re.split(r"\.|\[\]", rest)[1:] if s]
        else:
            segs = [s for s in path if s != "[]"]
        name, parent = segs[-1], (segs[-2] if len(segs) > 1 else "")
        if read_by_some_file(name, parent):
            continue
        # "<name>_es": the Spanish twin of a setting that is read (pick / langLink / the sync's language helpers)
        twin = re.fullmatch(r"(.+)_es", name)
        if twin and read_by_some_file(twin.group(1), parent):
            continue
        if here not in out:
            out.append(here)
    return out


# ============================================================================ every read setting is there
def missing(cfg, segs: list[str]) -> str:
    """The first part of the path the settings lack ("" when it is there — or leads into a value or a list of
    plain values, past which nothing is a setting). "[]" = any entry of a list."""
    cur = [cfg]
    for i, s in enumerate(segs):
        if s in NOT_KEYS:
            return ""
        if s == "[]":
            cur = [x for c in cur if isinstance(c, list) for x in c]
            if not cur:
                return ""
            continue
        dicts = [c for c in cur if isinstance(c, dict)]
        if not dicts:
            return ""
        found = [c[s] for c in dicts if s in c]
        if not found:
            return ".".join(segs[:i + 1]).replace(".[]", "[]")
        cur = found
    return ""


def site_path(segs: list[str]) -> list[str] | None:
    """A path in `site` (the pages' settings) → its path in config/site.yml (None: worked out or filled in by
    site.js)."""
    if not segs or segs[0] in SITE_COMPUTED or any(tuple(segs[:len(d)]) == d for d in SITE_DEFAULTED):
        return None
    return segs if segs[0] in SITE_SECTIONS else ["site"] + segs


NJK_DEFAULT_AFTER = re.compile(r"\s*(?:or\b|\|\s*default\b|if\b)")
NJK_GUARD_BEFORE = re.compile(r"(?:\bif\s+(?:not\s+)?|\band\s+(?:not\s+)?|\bor\s+)\(*\s*$")


def njk_missing(text: str, cfg: dict) -> list[tuple[int, str, str]]:
    """[(line, what the template reads, the part config/site.yml lacks)] — reads without a default."""
    t = strip_njk(text)
    aliases = {m.group(1): [s for s in m.group(2).split(".") if s]
               for m in re.finditer(r"\{%-?\s*set\s+(\w+)\s*=\s*site((?:\.[A-Za-z_]\w*)*)\s*-?%\}", t)}
    pat = re.compile(r"(?<![\w.$'\"-])(" + "|".join(map(re.escape, ["site", *aliases])) + r")((?:\.[A-Za-z_]\w*)+)")
    out = []
    for m in pat.finditer(t):
        segs = ([] if m.group(1) == "site" else aliases[m.group(1)]) + [s for s in m.group(2).split(".") if s]
        cfg_segs = site_path(segs)
        gap = missing(cfg, cfg_segs) if cfg_segs else ""
        if not gap:
            continue
        if NJK_DEFAULT_AFTER.match(t, m.end()) or NJK_GUARD_BEFORE.search(t[max(0, m.start() - 16):m.start()]):
            continue
        out.append((t.count("\n", 0, m.start()) + 1, "site." + ".".join(segs), gap))
    return out


JS_DEFAULT_AFTER = re.compile(r"\s*(?:\|\||\?\?|\?(?!\.)|&&|=(?!=))")
JS_GUARD_BEFORE = re.compile(r"(?:\bif\s*\(\s*!*|&&\s*!*|\|\|\s*|!\s*|\?\?\s*)$")
JS_ALIAS = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*\(?\s*(?:(?:data\.)?site\s*&&\s*)?(?:data\.)?site((?:\??\.[A-Za-z_]\w*)*)"
                      r"\s*\)?\s*(?:(?:\|\||\?\?)\s*\{\s*\}\s*)?[;,\n]")
JS_ROOT = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*\(?\s*yaml\.load\(\s*fs\.readFileSync\(\s*\"config/site\.yml\"")


def block_end(t: str, pos: int) -> int:
    """Where the block (function body …) around `pos` closes: a name declared there is known up to it."""
    depth = 0
    for i in range(pos, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            if depth == 0:
                return i
            depth -= 1
    return len(t)


def js_missing(text: str, cfg: dict) -> list[tuple[int, str, str]]:
    """[(line, what the code reads, the part config/site.yml lacks)] — reads without a default."""
    code = strip_js(text)
    t = strip_js(text, blank=True)                                           # the same length, texts blanked
    # names that hold the settings: config/site.yml loaded here (its root), or `site` (or a part of it), each
    # from its declaration to the end of its block: [(name, path, start, end, is_root)]
    known = [(m.group(1), [], m.start(), block_end(t, m.end()), True) for m in JS_ROOT.finditer(code)]
    known += [(m.group(1), [s for s in re.split(r"\??\.", m.group(2)) if s], m.start(), block_end(t, m.end()), False)
              for m in JS_ALIAS.finditer(t) if m.group(1) != "site"]
    names = ["data\\.site", "site", *sorted({re.escape(k[0]) for k in known})]
    pat = re.compile(r"(?<![\w$.'\"`-])(" + "|".join(names) + r")((?:\??\.[A-Za-z_]\w*)+)")
    out = []
    for m in pat.finditer(t):
        who, chain = m.group(1), m.group(2)
        segs = [s for s in re.split(r"\??\.", chain) if s]
        if who in ("site", "data.site"):
            cfg_segs = site_path(segs)
        else:
            here = [k for k in known if k[0] == who and k[2] <= m.start() < k[3]]
            if not here:
                continue                                                     # another variable of that name
            _, base, _, _, is_root = max(here, key=lambda k: k[2])
            cfg_segs = base + segs if is_root else site_path(base + segs)
        gap = missing(cfg, cfg_segs) if cfg_segs else ""
        if not gap:
            continue
        if "?." in chain or JS_DEFAULT_AFTER.match(t, m.end()) or JS_GUARD_BEFORE.search(t[max(0, m.start() - 16):m.start()]):
            continue
        out.append((t.count("\n", 0, m.start()) + 1, f"{who}{chain}", gap))
    return out


class PyReads(ast.NodeVisitor):
    """The config reads of one Python file: every chain of ["key"] / .get("key"[, default]) that starts at
    load_config(), followed through assignments (also `self.cfg = load_config()`), `x if … else load_config()`,
    `(… or {})` and `for entry in <a list>` ("[]")."""

    def __init__(self):
        self.scopes: list[dict[str, tuple]] = [{}]
        self.attrs: dict[str, tuple] = {}
        self.defaulted: set[int] = set()            # nodes followed by `or …`
        self.reads: list[tuple[tuple, bool, int]] = []

    def path(self, node) -> tuple[tuple, bool] | None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "load_config":
            return (), False
        if isinstance(node, ast.Name):
            for scope in reversed(self.scopes):
                if node.id in scope:
                    return scope[node.id], False
            return None
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and node.attr in self.attrs:
            return self.attrs[node.attr], False
        if isinstance(node, ast.IfExp):
            return self.path(node.body) or self.path(node.orelse)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            p = self.path(node.values[0])
            return (p[0], True) if p else None
        if isinstance(node, ast.Subscript):
            base, key = self.path(node.value), node.slice
            if base and isinstance(key, ast.Constant):
                if isinstance(key.value, str):
                    return base[0] + (key.value,), False
                if isinstance(key.value, int):
                    return base[0] + ("[]",), False
            return None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
            base, key = self.path(node.func.value), node.args[0]
            if base and isinstance(key, ast.Constant) and isinstance(key.value, str):
                return base[0] + (key.value,), len(node.args) > 1 or bool(node.keywords)
        return None

    def note(self, node):
        p = self.path(node)
        if p and p[0]:
            self.reads.append((p[0], p[1] or id(node) in self.defaulted, node.lineno))

    def visit_FunctionDef(self, node):
        self.scopes.append({})
        self.generic_visit(node)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.Or):
            self.defaulted.update(id(v) for v in node.values[:-1])
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.generic_visit(node)
        p = self.path(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                if p:
                    self.scopes[-1][target.id] = p[0]
                else:
                    self.scopes[-1].pop(target.id, None)
            elif isinstance(target, ast.Attribute) and p:
                self.attrs[target.attr] = p[0]

    def visit_For(self, node):
        p = self.path(node.iter)
        if p and isinstance(node.target, ast.Name):
            self.scopes[-1][node.target.id] = p[0] + ("[]",)
        self.generic_visit(node)

    def visit_Subscript(self, node):
        self.note(node)
        self.generic_visit(node)

    def visit_Call(self, node):
        self.note(node)
        self.generic_visit(node)


def py_reads(src: str) -> list[tuple[tuple, bool, int]]:
    v = PyReads()
    v.visit(ast.parse(src))
    return v.reads


def py_missing(src: str, cfg: dict) -> list[tuple[int, str, str]]:
    """[(line, what the code reads, the part config/site.yml lacks)] — reads without a default."""
    out = []
    for path, has_default, line in py_reads(src):
        gap = "" if has_default else missing(cfg, list(path))
        if gap:
            out.append((line, shown(path), gap))
    return out


def load(rel: str):
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


SITE_JS_FILES = (["eleventy.config.js"] + sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "eleventy").rglob("*.js"))
                 + sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "src/_data").glob("*.js"))
                 + sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "src/pages").glob("*.11ty.js")))


# ============================================================================ the checks
class SettingsAreRead(unittest.TestCase):
    index: dict | None = None

    @classmethod
    def setUpClass(cls):
        cls.index = code_index()

    def test_every_setting_in_site_yml_is_read(self):
        unread = unread_settings(load("config/site.yml"), self.index, MAP_LIKE.get("config/site.yml"), DYNAMIC.get("config/site.yml"))
        self.assertEqual(unread, [], "settings in config/site.yml that no code reads: wire them up or delete them "
                                     "(a key read under a built name goes in DYNAMIC, with the reason)")

    def test_every_setting_in_the_other_settings_files_is_read(self):
        for rel in SETTINGS_FILES[1:]:
            with self.subTest(rel):
                self.assertEqual(unread_settings(load(rel), self.index, MAP_LIKE.get(rel), DYNAMIC.get(rel)), [],
                                 f"settings in {rel} that no code reads")

    def test_the_lists_of_exceptions_are_current(self):
        for rel, entries in list(MAP_LIKE.items()) + list(DYNAMIC.items()):
            paths = {shown(p) for p in key_paths(load(rel))}
            for entry, why in entries.items():
                with self.subTest(f"{rel}: {entry}"):
                    self.assertIn(entry, paths, "an exception for a key that is gone: remove it")
                    self.assertTrue(why.strip(), "every exception says why")

    def test_a_made_up_setting_is_caught(self):
        # (on top of what the committee's own file has unread today: that is the first test's, left to the Code check)
        base = set(unread_settings(load("config/site.yml"), self.index, MAP_LIKE["config/site.yml"]))
        cfg = copy.deepcopy(load("config/site.yml"))
        cfg["site"]["made_up_setting"] = "x"
        cfg["links"]["sobriety_calculator"] = "https://example.org/calc"
        cfg["meeting"]["breakout_rooms"] = True
        # (an entry of its own: the list may be empty the day the committee has no recurring event)
        cfg["recurring_events"] = list(cfg.get("recurring_events") or []) + [{"key": "x", "title": "x", "parking_note": "Lot B"}]
        cfg["links"]["gv_home_es"] = "https://example.org/es"          # the Spanish twin of a link that is read
        unread = [u for u in unread_settings(cfg, self.index, MAP_LIKE["config/site.yml"]) if u not in base]
        self.assertEqual(sorted(unread), sorted(["site.made_up_setting", "meeting.breakout_rooms", "recurring_events[].parking_note",
                                                 "links.sobriety_calculator"]))
        # … and a reader makes it go away; a comment that names it does not
        index = code_index(extra={"src/pages/x.njk": "{# site.made_up_setting #}<p>{{ site.made_up_setting }}</p>",
                                  "scripts/x.py": "# links sobriety_calculator\nx = 1\n"})
        self.assertEqual(sorted(u for u in unread_settings(cfg, index, MAP_LIKE["config/site.yml"]) if u not in base),
                         sorted(["meeting.breakout_rooms", "recurring_events[].parking_note", "links.sobriety_calculator"]))
        # a map whose keys are data: its keys are never "unread", its entries' own keys are checked
        carry = copy.deepcopy(load("config/carry.yml"))
        carry_base = set(unread_settings(carry, self.index, MAP_LIKE["config/carry.yml"]))
        carry["tips"] = {**(carry.get("tips") or {}), "2099-01": [{"colour": "red"}]}
        self.assertEqual([u for u in unread_settings(carry, self.index, MAP_LIKE["config/carry.yml"]) if u not in carry_base],
                         ["tips.2099-01[].colour"])


class ReadsExist(unittest.TestCase):
    # The checks of the committee's config/site.yml as it is are left to the Code check (scripts/ops/gate_tests.py
    # CONTENT_TESTS: a setting the committee deleted must never keep the site from updating); the proof that the
    # check catches a misspelled read, on settings of its own, is a test of the code.
    cfg: dict | None = None

    @classmethod
    def setUpClass(cls):
        cls.cfg = load("config/site.yml")

    def test_every_setting_the_templates_read_is_there(self):
        problems = []
        for p in sorted((ROOT / "src").rglob("*.njk")):
            for line, what, gap in njk_missing(p.read_text(encoding="utf-8"), self.cfg):
                problems.append(f"{p.relative_to(ROOT).as_posix()}:{line}: {what} (config/site.yml has no {gap})")
        self.assertEqual(problems, [], "add the setting, or give the read a default (`or …`, `| default(…)`)")

    def test_every_setting_the_build_reads_is_there(self):
        problems = []
        for rel in SITE_JS_FILES:
            for line, what, gap in js_missing((ROOT / rel).read_text(encoding="utf-8"), self.cfg):
                if (rel, what.rsplit(".", 1)[-1]) in OTHER_SITE:
                    continue
                problems.append(f"{rel}:{line}: {what} (config/site.yml has no {gap})")
        self.assertEqual(problems, [], "add the setting, or give the read a default (`||`, `??`, `?.`)")

    def test_every_setting_the_sync_reads_is_there(self):
        problems, reads = [], 0
        for p in sorted((ROOT / "scripts").rglob("*.py")):
            src = p.read_text(encoding="utf-8")
            reads += len(py_reads(src))
            for line, what, gap in py_missing(src, self.cfg):
                problems.append(f"{p.relative_to(ROOT).as_posix()}:{line}: {what} (config/site.yml has no {gap})")
        self.assertEqual(problems, [], "add the setting, or read it with a default (.get(key, default) / `or …`)")
        self.assertGreater(reads, 100, "the sync's config reads are followed (load_config() chains)")

    def test_the_exceptions_are_still_needed(self):
        for (rel, name), why in OTHER_SITE.items():
            with self.subTest(rel):
                self.assertTrue(why.strip())
                self.assertIn(name, [w.rsplit(".", 1)[-1] for _, w, _ in js_missing((ROOT / rel).read_text(encoding="utf-8"), self.cfg)],
                              "an exception nothing needs any more: remove it")

    def test_a_misspelled_read_is_caught(self):
        # settings of their own (the proof does not change when config/site.yml does)
        cfg = {"site": {"title": "x", "timezone": "America/Chicago"}, "meeting": {"platform": "Zoom"},
               "links": {"gv_home": "https://example.org/"}, "spotlight": {"home_days": 60},
               "meetings": {"feeds": [{"id": "a", "name": "A"}]}}
        # templates: a link the settings do not have (the old /contribute/ bug: links.lv_record_story)
        tpl = ('{%- set L = site.links -%}\n<a href="{{ site.links.lv_record_story }}">x</a>\n'
               '<p>{{ site.meeting.platfrom }}</p>\n<a href="{{ L.gv_hom }}">y</a>\n'
               '<p>{{ site.meeting.platform }} {{ site.links.gv_home }} {{ site.built }} {{ "site.tagline" | t(L) }}</p>\n'
               '<p>{{ site.links.lv_record_story or "#" }} {% if site.links.extra %}z{% endif %}</p>\n'
               '{# {{ site.links.in_a_comment }} #}')
        self.assertEqual(njk_missing(tpl, cfg), [(2, "site.links.lv_record_story", "links.lv_record_story"),
                                                (3, "site.meeting.platfrom", "meeting.platfrom"),
                                                (4, "site.links.gv_hom", "links.gv_hom")])
        # a setting the committee may leave out because site.js fills it in (meeting.platform: Zoom) is no gap — in a
        # template, through an alias, or in the build's JavaScript; a misspelled read still is; a comment of several
        # lines keeps the line numbers of what follows
        no_platform = {**cfg, "meeting": {"weekday": "wednesday"}}
        tpl2 = ('{# a note\n   of two lines #}\n{% set m = site.meeting %}\n<p>{{ site.meeting.platform }}</p>\n'
                '<p>{{ t("x", { platform: m.platform }) }} {{ m.platfrom }}</p>\n')
        self.assertEqual(njk_missing(tpl2, no_platform), [(5, "site.meeting.platfrom", "meeting.platfrom")])
        self.assertEqual(njk_missing(tpl2, cfg), [(5, "site.meeting.platfrom", "meeting.platfrom")])
        self.assertEqual(js_missing("export const f = (site) => [site.meeting.platform, site.meeting.platfrom];\n", no_platform),
                         [(1, "site.meeting.platfrom", "meeting.platfrom")])
        # the build's JavaScript
        js = ('export function f(site) {\n  const L = site.links || {};\n  return [site.meeting.platfrom, L.gv_hom,\n'
              '    site.meeting.platform, site.spotlight.home_dayz || 60, site.links?.nope, "site.tagline"];\n}\n'
              '// site.links.in_a_comment\n')
        self.assertEqual(js_missing(js, cfg), [(3, "site.meeting.platfrom", "meeting.platfrom"), (3, "L.gv_hom", "links.gv_hom")])
        # the sync's Python
        py = ('from scripts.sync.common import load_config\n'
              'def f():\n    cfg = load_config()\n    tz = cfg["site"]["timezon"]\n'
              '    for feed in cfg["meetings"]["feeds"]:\n        print(feed["nmae"], feed["id"], feed.get("colour", "red"))\n'
              '    m = cfg.get("meeting") or {}\n    return m["platfrom"], m.get("platform"), (m.get("notes") or ""), tz\n')
        self.assertEqual(py_missing(py, cfg), [(4, "site.timezon", "site.timezon"), (6, "meetings.feeds[].nmae", "meetings.feeds[].nmae"),
                                               (8, "meeting.platfrom", "meeting.platfrom")])


if __name__ == "__main__":
    unittest.main()
