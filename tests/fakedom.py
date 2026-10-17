"""A small pretend browser page for running the site's browser scripts (src/assets/js/*.js) in Node.js — the page
itself is tests/fakedom.js; PAGE_JS below loads it.

    from fakedom import PAGE_JS          # JavaScript to put before a test script for tests/nodejs.py run_js
    out = run_js(self, PAGE_JS + "const p = page({ html: '<button id=b>Go</button>', scripts: [...] }); …",
                 needs_modules=False)

page({ html, url, scripts, globals, readyState }) builds a document from `html` (a tiny HTML parser: elements,
attributes, text, comments, <template> content, void elements, script / style text), runs each script file in a
Node vm context that holds it, and returns
    win          the page's window (the vm context: GV, window.MiniSearch … — whatever the scripts put there)
    doc          its document
    $(sel), $$(sel)   document.querySelector / querySelectorAll
    tick(ms)     async: the clock (Date.now, performance.now) moves on and every timer due by then runs, in order
                 (setTimeout, setInterval, requestAnimationFrame); promises settle between them
    ready()      async: DOMContentLoaded (readyState "interactive"), then load ("complete")
    click(el), key(el, key, init), fire(el, type, init)   events, bubbling (capture listeners first)
    errors       exceptions thrown by timers and listeners (a test can check none happened)
The elements have what the scripts use: attributes, classList, dataset, style (setProperty …), hidden, disabled,
inert, children and siblings, innerHTML / textContent / insertAdjacentHTML, querySelector(All), closest, matches
(tag, #id, .class, [attr], [attr=v|^=|$=|*=|~=], :not(), :checked, :disabled, :first-child, :last-child; the
descendant and child combinators; lists with ","), focus / blur (document.activeElement, focus / focusin / blur /
focusout events), <template>.content, <dialog> showModal / close, <img> (complete, naturalWidth, decode() — an
image loads when the test says: loadImage(img, ok)), <video> / <audio> (play, pause, load), new Image(), new
Audio(). No layout: every size is 0 and getBoundingClientRect() is all 0. Math.random gives the same numbers every
run. localStorage / sessionStorage work; fetch, navigator and the rest come from `globals`.
"""
from __future__ import annotations

# Before a run_js script: page({ html, url, scripts, globals, readyState }) → { win, doc, $, $$, tick, ready, click, key,
# fire, errors, loadImage } (see the module's docstring).
PAGE_JS = r"""
import vm from "node:vm";
const FAKEDOM = fs.readFileSync("tests/fakedom.js", "utf8");
const flush = () => new Promise((r) => setImmediate(r));
function page({ html = "", url = "https://example.test/aagrapevine/", scripts = [], globals = {}, readyState = "loading" } = {}) {
  const ctx = vm.createContext({ console, URL, URLSearchParams, TextEncoder, TextDecoder, AbortController, Blob, structuredClone });
  ctx.window = ctx;
  ctx.self = ctx;
  vm.runInContext(FAKEDOM, ctx, { filename: "fakedom.js" });
  const doc = ctx.__dom.boot({ html, url, readyState });
  for (const [k, v] of Object.entries(globals)) {
    if (k === "navigator") Object.assign(ctx.navigator, v); else ctx[k] = v;
  }
  for (const f of scripts) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
  const T = ctx.__timers, C = ctx.__clock;
  const ev = (type, init) => new ctx.Event(type, Object.assign({ bubbles: true }, init || {}));
  const p = {
    win: ctx, doc, errors: ctx.__errors,
    $: (s) => doc.querySelector(s), $$: (s) => doc.querySelectorAll(s),
    async tick(ms = 0) {
      const end = C.now + ms;
      for (;;) {
        await flush();
        T.sort((x, y) => x.at - y.at || x.id - y.id);
        const t = T[0];
        if (!t || t.at > end) break;
        C.now = Math.max(C.now, t.at);
        if (t.every) t.at += t.every; else T.shift();
        try { t.fn(...t.a); } catch (e) { ctx.__errors.push(e); }
      }
      C.now = end;
      await flush();
    },
    async ready() {
      doc.readyState = "interactive";
      doc.dispatchEvent(new ctx.Event("DOMContentLoaded", { bubbles: true }));
      await p.tick(0);
      doc.readyState = "complete";
      ctx.dispatchEvent(new ctx.Event("load"));
      await p.tick(0);
    },
    fire(el, type, init) { return el.dispatchEvent(ev(type, init)); },
    click(el, init) { return el.dispatchEvent(ev("click", Object.assign({ button: 0 }, init || {}))); },
    key(el, key, init) { return el.dispatchEvent(ev("keydown", Object.assign({ key }, init || {}))); },
    loadImage: (img, ok, w, h) => ctx.__dom.loadImage(img, ok, w, h),
  };
  return p;
}
"""
