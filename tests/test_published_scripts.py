"""The /published/ page's two scripts, run in a Node.js vm on a small stand-in for the page
(src/assets/js/published.js — the cards' filter card — and src/assets/js/published-archive.js — the Texas writers
archive), with the real view model (eleventy/filters/published.js pwView / pwArchive) giving the rows, their search
words and the scripts' settings:

  * Search    — the page scripts' norm() and the view model's pwNorm() give the same words for the same text (also
                where a browser has no lookbehind — Safari before 16.4: no page script uses one); a writer printed with
                initials is found by "M.B.", "MB", "M.B" and "M B" (cards and archive rows), "H.T.B." finds only
                H.T.B.; a year is a whole word ("1990" is not the decade "1990s").
  * Address   — published.js keeps the archive's ?dec= and the #hash (also when the page starts); after Back / Forward
                both scripts write their choices into the address again; Reset clears the decade (pw:reset).
  * Archive   — Area 65 lists only the Area 65 rows, All of Texas / Everyone also the rest of Texas once
                texas-archive.json?v=… is in (rows slotted in by their place in the whole list); a download that fails
                shows Try again, which keeps keyboard focus in the archive; the decade chips then count the rows that
                are here; Clear search keeps the reader in the archive; the empty state's help line follows the cause;
                "Show both magazines"; the note over the list shows only while a machine-translated row is shown.

    python -m unittest tests.test_published_scripts -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "fixtures" / "writers_archive" / "site_sample.json"
SCRIPTS = (ROOT / "src" / "assets" / "js" / "published.js", ROOT / "src" / "assets" / "js" / "published-archive.js")
TODAY = "2026-09-26"


def archive_data() -> dict:
    """The sample archive plus the rows these tests need: a writer printed as initials ("M.B.", Area 65), stories
    from 1990 and 1995, and a machine-translated subtitle under an untranslated title (rest of Texas)."""
    wa = json.loads(SAMPLE.read_text(encoding="utf-8"))
    base = next(it for it in wa["items"] if it["title"] == "Who We Are")
    rest = next(it for it in wa["items"] if it["title"] == "A New Year")

    def item(src: dict, slug: str, title: str, year: int, month: int, name: str, **extra) -> dict:
        it = copy.deepcopy(src)
        it.update({"id": "wa:t-" + slug, "key": "https://www.aagrapevine.org/magazine/t/" + slug,
                   "url": "https://www.aagrapevine.org/magazine/t/" + slug, "title": title, "year": year,
                   "decade": year // 10 * 10, "issue_key": f"{year}-{month:02d}", "issue_label": None, "summary": None})
        it.pop("i18n", None)
        it.pop("machine", None)
        it["writers"] = [dict(it["writers"][0], name=name)]
        it.update(extra)
        return it

    wa["items"] += [
        item(base, "serenity", "The Serenity Prayer: An Interpretation", 1977, 5, "M.B."),
        item(base, "ninety", "Ninety Meetings", 1990, 3, "Ray S."),
        item(base, "midway", "Halfway There", 1995, 7, "Kay N."),
        item(rest, "whammy", "The Triple Whammy of Spirituality", 1991, 7, "Lee R.", summary="Step Seven",
             i18n={"summary": {"en": "Step Seven", "es": "Paso Siete"}}, machine=["es"]),
    ]
    return wa


def spotlight_data() -> dict:
    """Recent stories for the cards (pwView): writers printed as initials ("L.C.", "J. D. O.") and full names."""
    def story(n: int, scope: str, author: str, city: str) -> dict:
        return {"id": f"s{n}", "kind": "article", "source": "grapevine", "category": "gv", "lang": "en",
                "url": f"https://www.aagrapevine.org/story/{n}", "title": f"Story number {n}", "date": "2026-09-01",
                "extra": {"pub_date": "2026-09-01", "author": author,
                          "geo": {"scope": scope, "city": city, "label_en": f"{city}, Texas"}}}
    items = [story(1, "neta65", "L.C.", "Tyler"), story(2, "neta65", "J. D. O.", "Longview"),
             story(3, "neta65", "Linda Carr", "Lufkin"), story(4, "texas", "Bob K.", "Austin")]
    return {"updated": TODAY + "T10:00:00Z", "list_days": [60, 90], "default_scope": "neta65", "items": items}


# The page stand-in: elements with attributes, children, text, `hidden` / `checked` / `disabled` / `value`, a few CSS
# selectors (tag, #id, .class, [attr], [attr=value], :checked, :disabled, descendants, lists), events that bubble,
# focus; a document; location + history.replaceState; fake timers (tick(ms)); fetch answered as the test says
# (net.mode "ok" | "fail" | "hang"; an AbortSignal stops a hanging one).
# page(opts) builds the cards and the archive from the view model and loads published.js, then published-archive.js.
DOM_JS = r"""
import vm from "node:vm";
const { pwNorm } = await imp("eleventy/filters/published.js");

function parseCompound(s) {
  const m = /^([a-zA-Z][\w-]*)?((?:#[\w-]+|\.[\w-]+|\[[^\]]+\]|:[\w-]+)*)$/.exec(s);
  if (!m) throw new Error("selector not supported: " + s);
  const c = { tag: m[1] ? m[1].toUpperCase() : null, ids: [], classes: [], attrs: [], pseudo: [] };
  const re = /#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:=("[^"]*"|'[^']*'|[^\]]*))?\]|:([\w-]+)/g;
  let p;
  while ((p = re.exec(m[2]))) {
    if (p[1]) c.ids.push(p[1]);
    else if (p[2]) c.classes.push(p[2]);
    else if (p[3]) c.attrs.push([p[3], p[4] === undefined ? null : p[4].replace(/^["']|["']$/g, "")]);
    else c.pseudo.push(p[5]);
  }
  return c;
}
function matchCompound(el, c) {
  if (!el || el.nodeType !== 1) return false;
  if (c.tag && el.tagName !== c.tag) return false;
  if (c.ids.some((i) => el.getAttribute("id") !== i)) return false;
  if (c.classes.some((k) => !el.classList.contains(k))) return false;
  if (c.attrs.some(([n, v]) => !el.hasAttribute(n) || (v !== null && el.getAttribute(n) !== v))) return false;
  for (const ps of c.pseudo) {
    if (ps === "checked" && !el.checked) return false;
    if (ps === "disabled" && !el.disabled) return false;
    if (ps !== "checked" && ps !== "disabled") throw new Error("pseudo-class not supported: " + ps);
  }
  return true;
}
function matches(el, sel) {
  return String(sel).split(",").some((alt) => {
    const parts = alt.trim().split(/\s+/).map(parseCompound);
    if (!matchCompound(el, parts[parts.length - 1])) return false;
    let node = el.parentNode;
    for (let i = parts.length - 2; i >= 0; i--) {
      while (node && !matchCompound(node, parts[i])) node = node.parentNode;
      if (!node) return false;
      node = node.parentNode;
    }
    return true;
  });
}

class Text {
  constructor(t) { this.nodeType = 3; this.data = String(t); this.parentNode = null; }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
}
class El {
  constructor(doc, tag, attrs) {
    this.ownerDocument = doc; this.nodeType = 1; this.tagName = String(tag).toUpperCase();
    this.attributes = {}; this.childNodes = []; this.parentNode = null; this.listeners = {}; this.props = {};
    for (const k in attrs || {}) if (attrs[k] !== false && attrs[k] !== null && attrs[k] !== undefined) this.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
  }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  getAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attributes, n) ? this.attributes[n] : null; }
  setAttribute(n, v) { this.attributes[n] = String(v); }
  hasAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attributes, n); }
  removeAttribute(n) { delete this.attributes[n]; }
  get id() { return this.getAttribute("id") || ""; }
  get className() { return this.getAttribute("class") || ""; }
  set className(v) { this.setAttribute("class", v); }
  get classList() {
    const self = this, list = () => self.className.split(/\s+/).filter(Boolean);
    return {
      contains: (c) => list().includes(c),
      add: (c) => { if (!list().includes(c)) self.className = [...list(), c].join(" "); },
      remove: (c) => { self.className = list().filter((x) => x !== c).join(" "); },
      toggle(c, on) { if (on === undefined ? !list().includes(c) : on) this.add(c); else this.remove(c); },
    };
  }
  get hidden() { return this.hasAttribute("hidden"); }
  set hidden(v) { if (v) this.setAttribute("hidden", ""); else this.removeAttribute("hidden"); }
  get disabled() { return this.hasAttribute("disabled"); }
  set disabled(v) { if (v) this.setAttribute("disabled", ""); else this.removeAttribute("disabled"); }
  get checked() { return "checked" in this.props ? this.props.checked : this.hasAttribute("checked"); }
  set checked(v) {
    if (v && this.getAttribute("type") === "radio") {
      for (const o of this.ownerDocument.querySelectorAll('input[name="' + this.getAttribute("name") + '"]')) if (o !== this) o.props.checked = false;
    }
    this.props.checked = !!v;
  }
  get value() { return "value" in this.props ? this.props.value : this.getAttribute("value") || ""; }
  set value(v) { this.props.value = String(v); }
  get name() { return this.getAttribute("name") || ""; }
  get type() { return this.getAttribute("type") || ""; }
  get href() { return this.getAttribute("href") || ""; }
  set href(v) { this.setAttribute("href", v); }
  set target(v) { this.setAttribute("target", v); }
  set rel(v) { this.setAttribute("rel", v); }
  get lang() { return this.getAttribute("lang") || ""; }
  set lang(v) { this.setAttribute("lang", v); }
  set title(v) { this.setAttribute("title", v); }
  get textContent() { return this.childNodes.map((n) => n.textContent).join(""); }
  set textContent(v) { for (const n of this.childNodes) n.parentNode = null; this.childNodes = []; if (String(v) !== "") this.appendChild(new Text(v)); }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.childNodes.push(c); return c; }
  insertBefore(c, ref) {
    if (!ref) return this.appendChild(c);
    if (c.parentNode) c.parentNode.removeChild(c);
    c.parentNode = this; this.childNodes.splice(this.childNodes.indexOf(ref), 0, c); return c;
  }
  removeChild(c) { const i = this.childNodes.indexOf(c); if (i >= 0) this.childNodes.splice(i, 1); c.parentNode = null; return c; }
  *all() { for (const c of this.children) { yield c; yield* c.all(); } }
  querySelectorAll(sel) { return [...this.all()].filter((e) => matches(e, sel)); }
  querySelector(sel) { for (const e of this.all()) if (matches(e, sel)) return e; return null; }
  closest(sel) { for (let e = this; e && e.nodeType === 1; e = e.parentNode) if (matches(e, sel)) return e; return null; }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  dispatchEvent(ev) {
    if (!ev.target) ev.target = this;
    const path = [];
    for (let n = this; n; n = n.parentNode) path.push(n);
    if (ev.bubbles) path.push(this.ownerDocument);
    for (const n of ev.bubbles ? path : [this]) {
      for (const fn of (n.listeners && n.listeners[ev.type]) || []) { ev.currentTarget = n; fn.call(n, ev); }
    }
    return !ev.defaultPrevented;
  }
  click() { return this.dispatchEvent(new this.ownerDocument.win.Event("click", { bubbles: true, cancelable: true })); }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  scrollIntoView() { this.ownerDocument.scrolledTo.push(this.id || this.tagName); }
  getBoundingClientRect() { return { top: 2000, bottom: 2100, left: 0, right: 100, width: 100, height: 100 }; }
}
class Doc {
  constructor() {
    this.listeners = {}; this.scrolledTo = [];
    this.documentElement = new El(this, "html"); this.body = new El(this, "body");
    this.documentElement.appendChild(this.body); this.activeElement = this.body;
  }
  getElementById(id) { return this.documentElement.querySelector("#" + id); }
  querySelector(s) { return this.documentElement.querySelector(s); }
  querySelectorAll(s) { return this.documentElement.querySelectorAll(s); }
  createElement(t) { return new El(this, t); }
  createElementNS(ns, t) { return new El(this, t); }
  createTextNode(t) { return new Text(t); }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  dispatchEvent(ev) { if (!ev.target) ev.target = this; for (const fn of this.listeners[ev.type] || []) fn(ev); return true; }
}

const page = (opts) => {
  const o = Object.assign({ search: "", hash: "", fetch: "ok", lang: "en" }, opts || {});
  const doc = new Doc();
  const h = (tag, attrs, ...kids) => {
    const e = new El(doc, tag, attrs);
    for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) e.appendChild(typeof k === "object" ? k : new Text(k));
    return e;
  };
  const S = filters.pwStrings(o.lang), AS = filters.pwArcStrings(o.lang);
  const V = filters.pwView({ spotlight: input.spotlight }, o.lang);
  const A = filters.pwArchive({ writers_archive: input.wa }, o.lang);
  const chip = (name, value, checked) => h("label", { class: "pw-chip" },
    h("input", { type: "radio", class: "sr-only", name, value, checked, disabled: true, "data-pw-ctl": true }), h("span", {}, value), h("span", { class: "pw-n", "data-n": true }, "0"));

  // the filter card + the cards (published.njk: pwChip, pwCard, the groups, the empty state, the nudge)
  const form = h("form", { id: "pw-form" },
    ["neta65", "texas", "all"].map((v) => chip("scope", v, v === V.defScope)),
    V.listDays.map((d) => chip("days", String(d), d === V.defDays)),
    ["all", "gv", "lv"].map((v) => chip("pub", v, v === "all")),
    h("input", { id: "pw-q", name: "q", type: "search", disabled: true, "data-pw-ctl": true }),
    h("button", { type: "button", id: "pw-q-clear", hidden: true }),
    h("p", { id: "pw-status" }), h("button", { type: "button", id: "pw-reset", hidden: true }, "Reset"));
  const results = h("div", { id: "pw-results" },
    V.groups.map((g) => h("section", { "data-group": g.key },
      h("span", { "data-group-n": true }),
      h("div", { class: "pw-grid" }, g.items.map((it) => h("article", { class: "pw-card", "data-scope": it.scope, "data-pub": it.pub, "data-date": it.date, "data-s": it.search },
        h("p", { class: "pw-writer" }, it.author), h("a", { class: "pw-link", href: it.url }, it.title)))),
      h("div", { class: "pw-showall", hidden: true }, h("button", { type: "button", "data-pw-showall": g.key }, h("span", { "data-label": true })), h("p", { "data-note": true })))),
    h("div", { id: "pw-empty", hidden: true }, h("h2", { id: "pw-empty-title" }), h("button", { type: "button", "data-pw-clear": true, hidden: true })),
    h("div", { id: "pw-nudge", hidden: true }, h("p", { id: "pw-nudge-text" }), h("button", { type: "button", "data-pw-nudge": true }, h("span", { "data-label": true }))));
  const cfg = h("script", { id: "pw-config", type: "application/json" }, JSON.stringify({ lang: o.lang, tz: "America/Chicago", today: V.today,
    listDays: V.listDays, defDays: V.defDays, defScope: V.defScope, limit: V.limit, pubs: { gv: "Grapevine", lv: "La Viña" }, s: S }));

  // the archive (published.njk: the panel, the note, the decade groups with the Area 65 rows, the empty state, "Show more")
  const arcRow = (r) => h("li", { class: "pw-arc-row", "data-scope": r.scope, "data-pub": r.pub, "data-dec": r.dec, "data-y": r.year || "", "data-o": r.o,
    "data-s": r.search, "data-mt": r.machine || r.briefMachine, "data-pw-over": r.over }, h("a", { class: "pw-arc-link", href: r.url }, r.title));
  const arcChip = (value, checked) => h("label", { class: "pw-chip" },
    h("input", { type: "radio", class: "sr-only", name: "pw-dec", value, checked, disabled: true, "data-arc-ctl": true }), h("span", { class: "pw-n", "data-n": true }, "0"));
  const archive = h("section", { id: "archive" }, h("h2", { id: "pw-arc-title" }),
    h("div", { id: "pw-arc", "data-scope": "neta65" },
      h("div", { class: "pw-arc-panel" },
        h("div", { class: "pw-arc-places" }, A.top.map((p) => h("button", { type: "button", class: "pw-chip pw-arc-place", "data-arc-place": p.label, disabled: true, "data-arc-ctl": true },
          h("span", {}, p.label), h("span", { class: "pw-n", "data-n": true }, String(p.n))))),
        h("fieldset", {}, arcChip("all", true), A.decades.map((d) => arcChip(d.key, false))),
        h("p", { id: "pw-arc-status" }), h("button", { type: "button", class: "pw-reset", "data-arc-retry": true, hidden: true }, "Try again"),
        h("p", { id: "pw-arc-note", hidden: true })),
      h("p", { id: "pw-arc-mt", hidden: !A.mt }),
      h("div", { id: "pw-arc-list" }, A.decades.map((d) => h("div", { class: "pw-arc-dec", "data-dec": d.key, hidden: !d.n },
        h("h3", { id: "pw-arc-d-" + d.key }, h("span", { "data-arc-n": true })), h("ol", {}, d.rows.map(arcRow))))),
      h("div", { id: "pw-arc-empty", hidden: true }, h("p", { "data-arc-empty-text": true, hidden: true }),
        ["clear", "alldec", "allpub", "texas"].map((k) => h("button", { type: "button", ["data-arc-" + k]: true, hidden: true }, k))),
      h("div", { id: "pw-arc-more", hidden: true }, h("button", { type: "button", "data-arc-more": "page" }, h("span", { "data-label": true })),
        h("button", { type: "button", "data-arc-more": "all" }, h("span", { "data-label": true })), h("p", { id: "pw-arc-shown" }))));
  const arcCfg = h("script", { id: "pw-arc-config", type: "application/json" }, JSON.stringify({ lang: o.lang,
    json: (o.lang === "es" ? "/es" : "") + "/published/texas-archive.json?v=" + A.version, rest: A.restRows.length, page: A.page,
    since: A.since, counts: A.counts, pubs: { gv: "Grapevine", lv: "La Viña" }, s: AS }));
  doc.body.appendChild(cfg); doc.body.appendChild(form); doc.body.appendChild(results); doc.body.appendChild(archive); doc.body.appendChild(arcCfg);

  // the window: address + history, timers, fetch
  const loc = { pathname: "/aagrapevine/published/", search: o.search, hash: o.hash };
  const urls = [];
  const history = { state: null, replaceState(st, t, url) { const u = new URL(url, "https://example.test"); loc.pathname = u.pathname; loc.search = u.search; loc.hash = u.hash; urls.push(url); } };
  let now = 0, nextId = 1;
  const timers = [];
  const tick = (ms) => { now += ms; for (;;) { timers.sort((a, b) => a.at - b.at); const t = timers[0]; if (!t || t.at > now) break; timers.shift(); t.fn(); } };
  const net = { mode: o.fetch, calls: [], json: { v: 1, lang: o.lang, count: A.json.length, items: A.json } };
  const winListeners = {};
  class Event { constructor(type, init) { this.type = type; this.bubbles = !!(init && init.bubbles); this.cancelable = !!(init && init.cancelable); this.defaultPrevented = false; this.target = null; } preventDefault() { this.defaultPrevented = true; } }
  class CustomEvent extends Event { constructor(type, init) { super(type, init); this.detail = init && init.detail; } }
  // the device's clock: the build day (published.js counts the 60 / 90 days from the later of the two)
  const NOW = Date.parse(input.today + "T17:00:00Z");
  class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(NOW); } static now() { return NOW; } }
  const ctx = {
    console, JSON, Math, Object, Array, String, Number, RegExp, Intl, Promise, Date: FakeDate, Error, URLSearchParams, URL, isNaN, Infinity,
    document: doc, location: loc, history, Event, CustomEvent, AbortController, innerHeight: 900,
    GV: { url: (p) => "/aagrapevine" + p, reducedMotion: () => true },
    matchMedia: () => ({ matches: false }),
    setTimeout: (fn, ms) => { const id = nextId++; timers.push({ id, fn, at: now + (ms || 0) }); return id; },
    clearTimeout: (id) => { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); },
    addEventListener: (t, fn) => { (winListeners[t] ||= []).push(fn); },
    fetch: (url, init) => {
      net.calls.push({ url, cache: init && init.cache });
      if (net.mode === "fail") return Promise.reject(new Error("offline"));
      if (net.mode === "hang") return new Promise((res, rej) => { if (init && init.signal) init.signal.addEventListener("abort", () => rej(new Error("aborted"))); });
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(net.json) });
    },
  };
  ctx.window = ctx;
  doc.win = ctx;
  vm.createContext(ctx);
  for (const f of ["src/assets/js/published.js", "src/assets/js/published-archive.js"]) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });

  const $ = (id) => doc.getElementById(id);
  const visible = () => doc.querySelectorAll("#pw-arc-list li.pw-arc-row").filter((li) => !li.hidden && !li.parentNode.parentNode.hidden);
  // a row's title: the first thing in its link (a row from the JSON has its "(opens on …)" and byline after it)
  const rows = () => visible().map((li) => ({ t: li.querySelector("a").childNodes[0].textContent, scope: li.getAttribute("data-scope"),
                                              y: li.getAttribute("data-y"), dec: li.getAttribute("data-dec") }));
  const cards = () => doc.querySelectorAll(".pw-card").filter((c) => !c.hidden).map((c) => c.querySelector(".pw-writer").textContent);
  const search = (q) => { const qi = $("pw-q"); qi.value = q; qi.dispatchEvent(new Event("input", { bubbles: true })); $("pw-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); };
  const choose = (name, value) => { const r = doc.querySelector('input[name="' + name + '"][value="' + value + '"]'); r.checked = true; r.dispatchEvent(new Event("change", { bubbles: true })); };
  const popstate = () => { for (const fn of winListeners.popstate || []) fn({ type: "popstate" }); };
  const flush = async () => { for (let i = 0; i < 6; i++) await new Promise((r) => setImmediate(r)); };
  const active = () => { const a = doc.activeElement; return a === doc.body ? "BODY" : (a.getAttribute("name") || a.getAttribute("id") || a.tagName) + (a.getAttribute("value") ? "=" + a.getAttribute("value") : ""); };
  const chips = () => Object.fromEntries(doc.querySelectorAll('input[name="pw-dec"]').map((r) => [r.getAttribute("value"), Number(r.closest(".pw-chip").querySelector("[data-n]").textContent.replace(/\D/g, ""))]));
  return { doc, ctx, loc, urls, net, tick, $, rows, cards, search, choose, popstate, flush, active, chips, A, V, AS, S };
};
"""


def js(case: unittest.TestCase, script: str):
    return run_js(case, DOM_JS + script, data={"wa": archive_data(), "spotlight": spotlight_data(), "today": TODAY},
                  env={"PW_TODAY": TODAY}, timeout=120)


class Search(unittest.TestCase):
    def test_no_page_script_uses_a_lookbehind(self):
        # Safari before 16.4 cannot compile one: the page's own RegExp would throw (and the search split initials)
        for f in SCRIPTS:
            with self.subTest(script=f.name):
                self.assertNotIn("(?<", f.read_text(encoding="utf-8"))

    def test_the_scripts_and_the_view_model_normalize_alike(self):
        inputs = ["H. T. B.", "H.T.B.", "h.t.b", "H.T.B", "M.B", "M B", "M.B.", "MB", "J. D. O", "J. D. O.", "L.C",
                  "Beginner's Meeting", "Beginner’s Meeting", "C.D.A.", "1985", "1990s", "Peñasco, Tejas", "Ñandú",
                  "(A.B.)(C.D.)", "A.B.,C.D.", "A.B..C.D.", "U.S.A.-born", "Ms.A.B.", "1A.B.", "xA.B.", "Irene H-P. (San Antonio)",
                  "Dear Grapevine", "  spaced   out  ", "Condado de Smith, Texas", "O’Brien", "", None, 1985]
        for it in archive_data()["items"]:
            inputs += [it["title"], it.get("summary")] + [w.get("name") for w in it["writers"]] + [w.get("place") for w in it["writers"]]
        r = run_js(self, r"""
          import vm from "node:vm";
          const { pwNorm } = await imp("eleventy/filters/published.js");
          // a browser without lookbehind (Safari before 16.4): new RegExp("(?<…") throws
          class OldRegExp extends RegExp { constructor(p, f) { if (String(p).includes("(?<")) throw new SyntaxError("invalid group specifier name"); super(p, f); } }
          const normOf = (file, Re) => {
            const src = fs.readFileSync(file, "utf8");
            const start = src.indexOf("  var NON_WORD"), end = src.indexOf("\n  }\n", src.indexOf("  function norm(s)")) + 4;
            const ctx = vm.createContext({ RegExp: Re, String });
            vm.runInContext(src.slice(start, end) + "\nthis.norm = norm;", ctx);
            return ctx.norm;
          };
          const res = {};
          for (const f of ["src/assets/js/published.js", "src/assets/js/published-archive.js"]) {
            for (const [label, Re] of [["now", RegExp], ["old", OldRegExp]]) {
              const norm = normOf(f, Re);
              res[f + " " + label] = input.map((s) => norm(s));
            }
          }
          res.server = input.map((s) => pwNorm(s));
          out(res);""", data=inputs, needs_modules=True)
        server = r.pop("server")
        self.assertEqual(server[0], "htb")
        self.assertEqual(server[inputs.index("Beginner’s Meeting")], "beginners meeting")
        for label, got in r.items():
            with self.subTest(script=label):
                self.assertEqual(got, server)

    def test_initials_years_and_words_on_the_archive(self):
        r = js(self, r"""
          const p = page({ search: "?scope=texas" });
          await p.flush();
          p.doc.querySelector('[data-arc-more="all"]').click();
          const res = {};
          for (const q of ["M.B", "M B", "M.B.", "MB", "H.T.B.", "H T B", "h.t.b", "1990", "1990s", "1995", "199", "2020", "beginners", "Beginner's"]) {
            p.search(q);
            p.doc.querySelector('[data-arc-more="all"]').click();
            res[q] = p.rows().map((r) => r.t + " | " + r.y);
          }
          out(res);""")
        serenity = "The Serenity Prayer: An Interpretation | 1977"
        for q in ("M.B", "M B", "M.B.", "MB"):
            with self.subTest(q=q):
                self.assertIn(serenity, r[q])
        self.assertEqual(r["M.B."], [serenity])                                     # the full form stays precise
        self.assertEqual(r["MB"], [serenity])
        for q in ("H.T.B.", "h.t.b"):
            self.assertEqual(r[q], ["Spring Cleaning | 1985"], q)                   # only H.T.B.'s story
        self.assertIn("Spring Cleaning | 1985", r["H T B"])
        # a year is a whole word: "1990" is not the decade "1990s"; the decade word and a part of a year still widen
        self.assertEqual(r["1990"], ["Ninety Meetings | 1990"])
        self.assertEqual(r["1995"], ["Halfway There | 1995"])
        nineties = {"Ninety Meetings | 1990", "Halfway There | 1995", "Who We Are | 1991", "A New Year | 1999",
                    "The Triple Whammy of Spirituality | 1991"}
        self.assertEqual(set(r["1990s"]), nineties)
        self.assertEqual(set(r["199"]), nineties)
        self.assertNotIn("Ninety Meetings | 1990", r["2020"])
        self.assertEqual(r["beginners"], r["Beginner's"])
        self.assertIn("Beginner’s Meeting | ", r["beginners"])

    def test_initials_on_the_cards(self):
        r = js(self, r"""
          const p = page({ search: "?scope=all" });
          const res = {};
          for (const q of ["L.C", "L C", "LC", "L.C.", "J. D. O", "J.D.O.", "jdo", "Linda"]) { p.search(q); res[q] = p.cards(); }
          out(res);""")
        for q in ("L.C", "L C"):
            self.assertIn("L.C.", r[q], q)
        for q in ("LC", "L.C."):
            self.assertEqual(r[q], ["L.C."], q)
        for q in ("J. D. O", "J.D.O.", "jdo"):
            self.assertEqual(r[q], ["J. D. O."], q)
        self.assertEqual(r["Linda"], ["Linda Carr"])


class Address(unittest.TestCase):
    def test_the_decade_and_the_hash_survive_the_start(self):
        r = js(self, r"""
          const p = page({ search: "?scope=texas&dec=1990s&utm=x", hash: "#archive" });
          await p.flush();
          out({ loc: p.loc.search + p.loc.hash, gvpw: p.ctx.GVPW && p.ctx.GVPW.state, checked: p.doc.querySelector('input[name="pw-dec"]:checked').getAttribute("value"),
                scrolled: p.doc.scrolledTo, json: p.net.calls.map((c) => c.url) });""")
        q = dict(re.findall(r"[?&]([^=&#]+)=([^&#]*)", r["loc"]))
        self.assertEqual(q, {"scope": "texas", "dec": "1990s", "utm": "x"})            # a key neither script owns stays too
        self.assertTrue(r["loc"].endswith("#archive"))
        self.assertEqual(r["gvpw"], {"scope": "texas", "days": 60, "pub": "all", "q": ""})
        self.assertEqual(r["checked"], "1990")
        self.assertIn("archive", r["scrolled"])
        # the rest of Texas, asked for by its fingerprint (a new address whenever its rows change)
        self.assertEqual(len(r["json"]), 1)
        self.assertRegex(r["json"][0], r"^/aagrapevine/published/texas-archive\.json\?v=[0-9a-f]{10}$")

    def test_card_changes_keep_the_decade_and_reset_clears_it(self):
        r = js(self, r"""
          const p = page({ search: "?dec=1990s" });
          p.choose("pub", "gv");
          const afterPub = p.loc.search;
          p.search("tyler");
          const afterSearch = p.loc.search;
          p.$("pw-reset").click();
          out({ afterPub, afterSearch, afterReset: p.loc.search, checked: p.doc.querySelector('input[name="pw-dec"]:checked').getAttribute("value") });""")
        self.assertIn("dec=1990s", r["afterPub"])
        self.assertIn("pub=gv", r["afterPub"])
        self.assertIn("dec=1990s", r["afterSearch"])
        self.assertEqual(r["afterReset"], "")
        self.assertEqual(r["checked"], "all")

    def test_back_over_an_in_page_link_writes_the_choices_again(self):
        # #archive added a history entry; the choices made after it replaced only that entry's address — Back shows
        # the older address while the page keeps the choices: both scripts put theirs back
        r = js(self, r"""
          const p = page({ search: "?scope=texas" });
          await p.flush();
          p.loc.hash = "#archive";                                   // the hero's link to #archive
          p.choose("pub", "gv");
          p.choose("pw-dec", "1990");
          const before = p.loc.search + p.loc.hash;
          p.loc.search = "?scope=texas"; p.loc.hash = "";             // Back: the older entry's address
          p.popstate();
          out({ before, after: p.loc.search + p.loc.hash });""")
        query = lambda s: dict(re.findall(r"[?&]([^=&#]+)=([^&#]*)", s))  # noqa: E731
        self.assertEqual(query(r["before"]), {"scope": "texas", "pub": "gv", "dec": "1990s"})
        self.assertTrue(r["before"].endswith("#archive"))
        self.assertEqual(query(r["after"]), {"scope": "texas", "pub": "gv", "dec": "1990s"})
        self.assertNotIn("#", r["after"])


class Archive(unittest.TestCase):
    def test_scope_rule_and_the_rows_slotted_in_by_their_place(self):
        r = js(self, r"""
          const p = page();
          p.doc.querySelector('[data-arc-more="all"]').click();
          const area = p.rows().map((r) => r.scope);
          const before = p.net.calls.length;
          p.choose("scope", "texas");
          await p.flush();
          p.doc.querySelector('[data-arc-more="all"]').click();
          const texas = p.rows().map((r) => r.scope);
          const order = p.doc.querySelectorAll(".pw-arc-dec").map((g) => g.querySelectorAll("li.pw-arc-row").map((li) => Number(li.getAttribute("data-o"))));
          p.choose("scope", "all");
          const all = p.rows().length;
          p.choose("scope", "neta65");
          p.doc.querySelector('[data-arc-more="all"]').click();
          out({ area, before, calls: p.net.calls.length, texas, order, all, back: p.rows().map((r) => r.scope),
                total: p.A.total, areaN: p.A.area, status: p.$("pw-arc-status").textContent });""")
        self.assertEqual((r["before"], r["calls"]), (0, 1))                           # fetched once, when the scope asked for it
        self.assertEqual(set(r["area"]), {"neta65"})
        self.assertEqual(len(r["area"]), r["areaN"])
        self.assertEqual(len(r["texas"]), r["total"])
        self.assertEqual(set(r["texas"]), {"neta65", "texas"})
        self.assertEqual(r["all"], r["total"])                                        # Everyone: still Texas only
        self.assertEqual(set(r["back"]), {"neta65"})                                  # back to Area 65: the rest hides again
        for o in r["order"]:
            self.assertEqual(o, sorted(o))                                            # each decade in the whole list's order
        self.assertTrue(r["status"].startswith(f"{r['areaN']} stories by Area 65 writers"))

    def test_a_download_that_fails_and_try_again(self):
        r = js(self, r"""
          const p = page({ search: "?scope=texas", fetch: "fail" });
          await p.flush();
          const retry = p.doc.querySelector("[data-arc-retry]");
          const failed = { retry: !retry.hidden, status: p.$("pw-arc-status").textContent, chips: p.chips() };
          // the decade chips count the rows that are here, like the headings (not the build's count of all of Texas)
          const heads = Object.fromEntries(p.doc.querySelectorAll(".pw-arc-dec").map((g) => [g.getAttribute("data-dec"), g.querySelector("[data-arc-n]").textContent]));
          retry.focus();
          p.net.mode = "hang";
          retry.click();
          const loading = { retry: !retry.hidden, active: p.active(), status: p.$("pw-arc-status").textContent, busy: p.$("pw-arc-list").getAttribute("aria-busy") };
          p.tick(20000);                                             // no answer in 20 s: the download is stopped
          await p.flush();
          out({ failed, heads, loading, timedOut: { retry: !retry.hidden, status: p.$("pw-arc-status").textContent }, counts: p.A.counts, area: p.A.area });""")
        f = r["failed"]
        self.assertTrue(f["retry"])
        self.assertEqual(f["status"], "The stories from the rest of Texas didn’t load. Check your connection and try again.")
        self.assertEqual(f["chips"]["all"], r["area"])                                 # not counts.texas.all.all
        self.assertNotEqual(f["chips"]["all"], r["counts"]["texas"]["all"]["all"])
        self.assertEqual(r["heads"]["2020"], f"{f['chips']['2020']} stories")
        lo = r["loading"]
        self.assertFalse(lo["retry"])
        self.assertEqual(lo["active"], "pw-dec=all")                                   # focus stays in the archive, not on <body>
        self.assertEqual(lo["busy"], "true")
        self.assertTrue(lo["status"].startswith("Loading"))
        self.assertTrue(r["timedOut"]["retry"])
        self.assertIn("didn’t load", r["timedOut"]["status"])

    def test_clear_search_keeps_the_reader_in_the_archive(self):
        r = js(self, r"""
          const p = page({ search: "?q=zzqqxx" });
          await p.flush();
          const empty = !p.$("pw-arc-empty").hidden;
          const clear = p.doc.querySelector("[data-arc-clear]");
          const shown = !clear.hidden;
          clear.focus();
          clear.click();
          out({ empty, shown, active: p.active(), q: p.$("pw-q").value, emptyAfter: !p.$("pw-arc-empty").hidden, rows: p.rows().length });""")
        self.assertTrue(r["empty"] and r["shown"])
        self.assertEqual(r["active"], "pw-dec=all")                                     # not the search box at the top of the page
        self.assertEqual(r["q"], "")
        self.assertFalse(r["emptyAfter"])
        self.assertGreater(r["rows"], 0)

    def test_the_empty_states_help_line_follows_the_cause(self):
        r = js(self, r"""
          const p = page({ search: "?scope=texas&dec=1950s&pub=lv" });
          await p.flush();
          const text = () => { const t = p.doc.querySelector("[data-arc-empty-text]"); return t.hidden ? null : t.textContent; };
          const shown = () => p.doc.querySelectorAll("#pw-arc-empty button").filter((b) => !b.hidden).map((b) => b.textContent);
          const chosen = { empty: !p.$("pw-arc-empty").hidden, text: text(), buttons: shown() };
          p.search("zzqqxx");
          const searched = { text: text(), buttons: shown() };
          p.search("");
          p.doc.querySelector("[data-arc-allpub]").click();
          out({ chosen, searched, after: { loc: p.loc.search, empty: !p.$("pw-arc-empty").hidden, active: p.active() }, strings: p.AS });""")
        s = r["strings"]
        self.assertTrue(r["chosen"]["empty"])
        self.assertEqual(r["chosen"]["text"], s["archive.empty_filters"])                # no search: the decade and magazine
        self.assertEqual(r["chosen"]["buttons"], ["alldec", "allpub"])
        self.assertEqual(r["searched"]["text"], s["archive.empty_text"])                 # a search: another spelling
        self.assertEqual(r["searched"]["buttons"], ["clear", "alldec", "allpub"])
        self.assertNotIn("pub=", r["after"]["loc"])                                      # "Show both magazines" set the page's magazine
        self.assertFalse(r["after"]["empty"])
        self.assertEqual(r["after"]["active"], "pw-dec=1950")

    def test_the_machine_translation_note_follows_the_rows_shown(self):
        r = js(self, r"""
          const note = (p) => !p.$("pw-arc-mt").hidden;
          const es = page({ lang: "es", search: "?scope=texas" });
          await es.flush();
          const res = { esStart: note(es), esMt: es.doc.querySelectorAll("li.pw-arc-row[data-mt]").length };
          es.search("Spring Cleaning");
          res.esNoMt = note(es);
          es.search("Whammy");
          res.esBrief = { note: note(es), rows: es.rows().map((r) => r.t) };
          const brief = es.doc.querySelectorAll("li.pw-arc-row").find((li) => li.textContent.includes("Whammy"));
          const en = page({ search: "?pub=gv" });
          res.enGv = note(en);
          en.choose("pub", "all");
          res.enAll = note(en);
          out(res);""")
        self.assertTrue(r["esStart"])
        self.assertGreater(r["esMt"], 0)
        self.assertFalse(r["esNoMt"])                                                     # no machine translation shown: no note
        self.assertEqual(r["esBrief"]["rows"], ["The Triple Whammy of Spirituality"])
        self.assertTrue(r["esBrief"]["note"])                                             # a translated subtitle counts too
        self.assertFalse(r["enGv"])                                                       # English page: only La Viña rows are translated
        self.assertTrue(r["enAll"])

    def test_rows_of_the_json_carry_the_marks(self):
        # buildRow(): the translated title says so in its link, the original keeps "Original title:", a translated
        # subtitle under an untranslated title has its own mark — text only
        r = js(self, r"""
          const p = page({ lang: "es", search: "?scope=texas" });
          await p.flush();
          const li = (t) => p.doc.querySelectorAll("li.pw-arc-row").find((x) => x.querySelector("a").textContent.startsWith(t));
          const desc = (el) => el ? { text: el.textContent, srOnly: el.querySelectorAll(".sr-only").map((s) => s.textContent),
                                      icons: el.querySelectorAll("svg").length, titled: el.querySelectorAll("[title]").length } : null;
          const whammy = li("The Triple Whammy");
          out({ whammy: { mt: whammy.hasAttribute("data-mt"), link: desc(whammy.querySelector(".pw-arc-link")), brief: desc(whammy.querySelector(".pw-arc-brief")) },
                json: p.net.json.items.filter((x) => x.rm || x.m).map((x) => ({ t: x.t, m: x.m || 0, rm: x.rm || 0 })), strings: p.AS });""")
        auto = r["strings"]["common.auto_translated"]
        w = r["whammy"]
        self.assertTrue(w["mt"])
        self.assertNotIn(f"({auto})", w["link"]["text"])                                  # the title itself is not translated
        self.assertEqual(w["brief"]["srOnly"], [f"{auto}: "])
        self.assertEqual(w["brief"]["icons"], 1)
        self.assertEqual(w["brief"]["text"], f"{auto}: Paso Siete")
        self.assertIn({"t": "The Triple Whammy of Spirituality", "m": 0, "rm": 1}, r["json"])
        self.assertTrue(all(not (x["m"] and x["rm"]) for x in r["json"]))                # one mark per row


if __name__ == "__main__":
    unittest.main()
