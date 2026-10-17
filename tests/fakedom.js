/* The pretend browser page of tests/fakedom.py (read by its PAGE_JS): a document, its elements, events,
   timers and a clock, run in the Node vm context the page's scripts run in. */
(function (G) {
  "use strict";
  /* ---------------- clock and timers ---------------- */
  const clock = (G.__clock = { now: Date.parse("2026-10-06T15:00:00Z"), start: 0 });
  clock.start = clock.now;
  const RealDate = Date;
  class FakeDate extends RealDate {
    constructor(...a) { if (a.length) super(...a); else super(clock.now); }
    static now() { return clock.now; }
  }
  G.Date = FakeDate;
  // the page's Math.random: the same numbers every run (mulberry32), so a test sees the same show every time
  let seed = 20261006;
  Math.random = () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  let seq = 0;
  const timers = (G.__timers = []);
  G.setTimeout = (fn, ms, ...a) => { seq += 1; timers.push({ id: seq, fn, a, at: clock.now + (Number(ms) || 0), every: 0 }); return seq; };
  G.setInterval = (fn, ms, ...a) => { seq += 1; const every = Math.max(1, Number(ms) || 0); timers.push({ id: seq, fn, a, at: clock.now + every, every }); return seq; };
  G.clearTimeout = G.clearInterval = (id) => { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); };
  G.requestAnimationFrame = (fn) => G.setTimeout(() => fn(clock.now - clock.start), 16);
  G.cancelAnimationFrame = (id) => G.clearTimeout(id);
  G.requestIdleCallback = (fn) => G.setTimeout(() => fn({ timeRemaining: () => 10, didTimeout: false }), 1);
  G.performance = { now: () => clock.now - clock.start, getEntriesByType: () => [] };
  const errors = (G.__errors = []);
  const guard = (fn, self, args) => { try { return fn.apply(self, args); } catch (e) { errors.push(e); return undefined; } };

  /* ---------------- events ---------------- */
  class Event {
    constructor(type, init) {
      init = init || {};
      this.type = type;
      this.bubbles = !!init.bubbles;
      this.cancelable = init.cancelable !== false;
      this.defaultPrevented = false;
      this.target = null;
      this.currentTarget = null;
      this._stop = false;
      this._stopNow = false;
      for (const k of Object.keys(init)) if (!(k in this)) this[k] = init[k];
    }
    preventDefault() { if (this.cancelable) this.defaultPrevented = true; }
    stopPropagation() { this._stop = true; }
    stopImmediatePropagation() { this._stop = true; this._stopNow = true; }
  }
  class CustomEvent extends Event { constructor(t, i) { super(t, i); this.detail = i && i.detail; } }
  G.Event = Event;
  G.CustomEvent = CustomEvent;
  G.KeyboardEvent = class extends Event {};
  G.MouseEvent = class extends Event {};
  G.FocusEvent = class extends Event {};
  G.PointerEvent = class extends Event {};
  function listen(target, t, fn, o) {
    if (!fn) return;
    const capture = o === true || !!(o && o.capture);
    const ls = (target._l[t] = target._l[t] || []);
    if (ls.some((l) => l.fn === fn && l.capture === capture)) return;
    ls.push({ fn, capture, once: !!(o && o.once) });
  }
  function unlisten(target, t, fn, o) {
    const capture = o === true || !!(o && o.capture);
    target._l[t] = (target._l[t] || []).filter((l) => !(l.fn === fn && l.capture === capture));
  }
  function invoke(node, ev, phase) {
    const ls = (node._l[ev.type] || []).slice();
    for (const l of ls) {
      if (phase === "capture" && !l.capture) continue;
      if (phase === "bubble" && l.capture) continue;
      if (l.once) unlisten(node, ev.type, l.fn, l.capture);
      ev.currentTarget = node;
      if (typeof l.fn === "function") guard(l.fn, node, [ev]); else if (l.fn && l.fn.handleEvent) guard(l.fn.handleEvent, l.fn, [ev]);
      if (ev._stopNow) break;
    }
    const on = node["on" + ev.type];
    if (phase !== "capture" && typeof on === "function" && !ev._stopNow) guard(on, node, [ev]);
  }
  function dispatch(target, ev) {
    ev.target = target;
    const path = [];
    for (let n = target.parentNode; n; n = n.parentNode) path.push(n);
    if (path.length && path[path.length - 1].nodeType === 9) path.push(G);
    for (let i = path.length - 1; i >= 0 && !ev._stop; i--) invoke(path[i], ev, "capture");
    if (!ev._stop) {
      invoke(target, Object.assign(ev, {}), "capture");
      if (!ev._stopNow) invoke(target, ev, "bubble");
    }
    if (ev.bubbles) for (let i = 0; i < path.length && !ev._stop; i++) invoke(path[i], ev, "bubble");
    ev.currentTarget = null;
    return !ev.defaultPrevented;
  }
  G._l = {};
  G.addEventListener = (t, fn, o) => listen(G, t, fn, o);
  G.removeEventListener = (t, fn, o) => unlisten(G, t, fn, o);
  G.dispatchEvent = (ev) => { ev.target = G; invoke(G, ev, "capture"); invoke(G, ev, "bubble"); return !ev.defaultPrevented; };

  /* ---------------- selectors ---------------- */
  const cache = new Map();
  function parseList(src) {
    if (cache.has(src)) return cache.get(src);
    const list = [];
    let i = 0;
    const s = String(src);
    const ws = () => { while (i < s.length && /\s/.test(s[i])) i++; };
    const ident = () => { const m = /^(?:\\.|[\w-])+/.exec(s.slice(i)); if (!m) throw new Error("selector? " + src); i += m[0].length; return m[0].replace(/\\(.)/g, "$1"); };
    function compound() {
      const c = { tag: null, id: null, classes: [], attrs: [], pseudos: [] };
      let any = false;
      for (;;) {
        const ch = s[i];
        if (ch === "*") { i++; any = true; continue; }
        if (ch && /[\w-]/.test(ch) && !any && c.tag === null && !c.id && !c.classes.length && !c.attrs.length) { c.tag = ident().toLowerCase(); any = true; continue; }
        if (ch === "#") { i++; c.id = ident(); any = true; continue; }
        if (ch === ".") { i++; c.classes.push(ident()); any = true; continue; }
        if (ch === "[") {
          i++; ws();
          const name = ident().toLowerCase(); ws();
          let op = "", value = null;
          const m = /^([~^$*|]?=)/.exec(s.slice(i));
          if (m) {
            op = m[1]; i += op.length; ws();
            if (s[i] === '"' || s[i] === "'") { const q = s[i]; const e = s.indexOf(q, i + 1); value = s.slice(i + 1, e); i = e + 1; }
            else value = ident();
            ws();
          }
          if (s[i] !== "]") throw new Error("selector? " + src);
          i++;
          c.attrs.push({ name, op, value });
          any = true;
          continue;
        }
        if (ch === ":") {
          i++;
          const name = ident().toLowerCase();
          let arg = null;
          if (s[i] === "(") {
            let depth = 1, j = i + 1;
            while (j < s.length && depth) { if (s[j] === "(") depth++; else if (s[j] === ")") depth--; j++; }
            arg = s.slice(i + 1, j - 1);
            i = j;
          }
          c.pseudos.push({ name, arg: name === "not" ? parseList(arg) : arg });
          any = true;
          continue;
        }
        break;
      }
      if (!any) throw new Error("selector? " + src);
      return c;
    }
    for (;;) {
      ws();
      const parts = [{ comb: null, c: compound() }];
      for (;;) {
        const before = i;
        ws();
        if (i >= s.length || s[i] === ",") break;
        let comb = " ";
        if (s[i] === ">" || s[i] === "+" || s[i] === "~") { comb = s[i]; i++; ws(); }
        else if (i === before) throw new Error("selector? " + src);
        parts.push({ comb, c: compound() });
      }
      list.push(parts);
      ws();
      if (s[i] === ",") { i++; continue; }
      break;
    }
    cache.set(src, list);
    return list;
  }
  function matchCompound(el, c) {
    if (!el || el.nodeType !== 1) return false;
    if (c.tag && el.localName !== c.tag) return false;
    if (c.id && el.getAttribute("id") !== c.id) return false;
    if (c.classes.length) { const cl = el.classList; for (const k of c.classes) if (!cl.contains(k)) return false; }
    for (const a of c.attrs) {
      const v = el.getAttribute(a.name);
      if (v === null) return false;
      const w = a.value;
      if (a.op === "=" && v !== w) return false;
      if (a.op === "~=" && !v.split(/\s+/).includes(w)) return false;
      if (a.op === "^=" && !v.startsWith(w)) return false;
      if (a.op === "$=" && !v.endsWith(w)) return false;
      if (a.op === "*=" && !v.includes(w)) return false;
      if (a.op === "|=" && !(v === w || v.startsWith(w + "-"))) return false;
    }
    for (const p of c.pseudos) {
      if (p.name === "not") { if (matchList(el, p.arg)) return false; }
      else if (p.name === "checked") { if (!el.checked) return false; }
      else if (p.name === "disabled") { if (!el.disabled) return false; }
      else if (p.name === "enabled") { if (el.disabled) return false; }
      else if (p.name === "first-child") { if (el.previousElementSibling) return false; }
      else if (p.name === "last-child") { if (el.nextElementSibling) return false; }
      else if (p.name === "empty") { if (el.childNodes.length) return false; }
      else if (p.name === "focus") { if (el.ownerDocument.activeElement !== el) return false; }
      else if (p.name === "scope") { /* the element itself */ }
      else throw new Error("selector :" + p.name + " is not known to the pretend page");
    }
    return true;
  }
  function matchParts(el, parts, k) {
    if (!matchCompound(el, parts[k].c)) return false;
    if (k === 0) return true;
    const comb = parts[k].comb;
    if (comb === ">") return matchParts(el.parentElement, parts, k - 1);
    if (comb === "+") return !!el.previousElementSibling && matchParts(el.previousElementSibling, parts, k - 1);
    if (comb === "~") { for (let n = el.previousElementSibling; n; n = n.previousElementSibling) if (matchParts(n, parts, k - 1)) return true; return false; }
    for (let n = el.parentElement; n; n = n.parentElement) if (matchParts(n, parts, k - 1)) return true;
    return false;
  }
  function matchList(el, list) { return list.some((parts) => matchParts(el, parts, parts.length - 1)); }

  /* ---------------- HTML ---------------- */
  const VOID = new Set("area base br col embed hr img input link meta source track wbr".split(" "));
  const RAW = new Set(["script", "style", "textarea", "title"]);
  const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0", hellip: "\u2026", mdash: "\u2014", ndash: "\u2013",
                middot: "\u00b7", copy: "\u00a9", rsquo: "\u2019", lsquo: "\u2018", rdquo: "\u201d", ldquo: "\u201c", times: "\u00d7" };
  const decode = (t) => String(t).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, k) =>
    k[0] === "#" ? String.fromCodePoint(k[1] === "x" || k[1] === "X" ? parseInt(k.slice(2), 16) : Number(k.slice(1))) : (ENT[k] !== undefined ? ENT[k] : m));
  const escText = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const escAttr = (t) => String(t).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  function parseInto(parent, html, doc) {
    const s = String(html);
    const stack = [{ name: "", into: parent }];
    const top = () => stack[stack.length - 1].into;
    let i = 0;
    while (i < s.length) {
      if (s.startsWith("<!--", i)) { const e = s.indexOf("-->", i + 4); top().appendChild(doc.createComment(s.slice(i + 4, e < 0 ? s.length : e))); i = e < 0 ? s.length : e + 3; continue; }
      if (s.startsWith("<!", i) || s.startsWith("<?", i)) { const e = s.indexOf(">", i); i = e < 0 ? s.length : e + 1; continue; }
      if (s[i] === "<" && s[i + 1] === "/") {
        const e = s.indexOf(">", i);
        const name = s.slice(i + 2, e).trim().toLowerCase();
        for (let k = stack.length - 1; k > 0; k--) if (stack[k].name === name) { stack.length = k; break; }
        i = e + 1;
        continue;
      }
      if (s[i] === "<" && /[a-zA-Z]/.test(s[i + 1] || "")) {
        let j = i + 1;
        while (j < s.length && /[^\s/>]/.test(s[j])) j++;
        const name = s.slice(i + 1, j).toLowerCase();
        const el = doc.createElement(name);
        let selfClose = false;
        for (;;) {
          while (j < s.length && /\s/.test(s[j])) j++;
          if (s[j] === ">") { j++; break; }
          if (s[j] === "/" && s[j + 1] === ">") { selfClose = true; j += 2; break; }
          if (j >= s.length) break;
          let k = j;
          while (k < s.length && /[^\s=/>]/.test(s[k])) k++;
          const an = s.slice(j, k).toLowerCase();
          j = k;
          while (j < s.length && /\s/.test(s[j])) j++;
          let av = "";
          if (s[j] === "=") {
            j++;
            while (j < s.length && /\s/.test(s[j])) j++;
            if (s[j] === '"' || s[j] === "'") { const q = s[j]; const e = s.indexOf(q, j + 1); av = s.slice(j + 1, e); j = e + 1; }
            else { let e = j; while (e < s.length && /[^\s>]/.test(s[e])) e++; av = s.slice(j, e); j = e; }
          } else if (k === j && s[j] === "/") { j++; }
          if (an) el.setAttribute(an, decode(av));
        }
        top().appendChild(el);
        i = j;
        if (RAW.has(name)) {
          const close = s.toLowerCase().indexOf("</" + name, i);
          const end = close < 0 ? s.length : close;
          const text = s.slice(i, end);
          if (text) el.appendChild(doc.createTextNode(name === "script" || name === "style" ? text : decode(text)));
          const gt = close < 0 ? s.length : s.indexOf(">", close);
          i = gt < 0 ? s.length : gt + 1;
          continue;
        }
        if (!VOID.has(name) && !selfClose) stack.push({ name, into: name === "template" ? el.content : el });
        continue;
      }
      let e = s.indexOf("<", i + 1);
      if (e < 0) e = s.length;
      const text = decode(s.slice(i, e));
      if (text) top().appendChild(doc.createTextNode(text));
      i = e;
    }
  }
  function serialize(n) {
    if (n.nodeType === 3) return n.parentNode && /^(script|style)$/.test(n.parentNode.localName) ? n.data : escText(n.data);
    if (n.nodeType === 8) return "<!--" + n.data + "-->";
    if (n.nodeType === 11) return n.childNodes.map(serialize).join("");
    const attrs = [...n._a].map(([k, v]) => " " + k + (v === "" ? "" : '="' + escAttr(v) + '"')).join("");
    if (VOID.has(n.localName)) return "<" + n.localName + attrs + ">";
    const inner = n.localName === "template" ? serialize(n.content) : n.childNodes.map(serialize).join("");
    return "<" + n.localName + attrs + ">" + inner + "</" + n.localName + ">";
  }

  /* ---------------- nodes ---------------- */
  const ZERO_RECT = Object.freeze({ x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 });
  class Node {
    constructor(type, doc) { this.nodeType = type; this.ownerDocument = doc; this.parentNode = null; this.childNodes = []; this._l = {}; }
    get parentElement() { return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null; }
    get firstChild() { return this.childNodes[0] || null; }
    get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
    get nextSibling() { const p = this.parentNode; if (!p) return null; return p.childNodes[p.childNodes.indexOf(this) + 1] || null; }
    get previousSibling() { const p = this.parentNode; if (!p) return null; return p.childNodes[p.childNodes.indexOf(this) - 1] || null; }
    get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
    get childElementCount() { return this.children.length; }
    get firstElementChild() { return this.children[0] || null; }
    get lastElementChild() { const c = this.children; return c[c.length - 1] || null; }
    get nextElementSibling() { for (let n = this.nextSibling; n; n = n.nextSibling) if (n.nodeType === 1) return n; return null; }
    get previousElementSibling() { for (let n = this.previousSibling; n; n = n.previousSibling) if (n.nodeType === 1) return n; return null; }
    get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n.nodeType === 9; }
    get nodeValue() { return this.nodeType === 3 || this.nodeType === 8 ? this.data : null; }
    set nodeValue(v) { if (this.nodeType === 3 || this.nodeType === 8) this.data = String(v); }
    get textContent() {
      if (this.nodeType === 3 || this.nodeType === 8) return this.data;
      return this.childNodes.map((c) => (c.nodeType === 8 ? "" : c.textContent)).join("");
    }
    set textContent(v) {
      if (this.nodeType === 3 || this.nodeType === 8) { this.data = String(v); return; }
      for (const c of this.childNodes) c.parentNode = null;
      this.childNodes = [];
      if (v !== "" && v !== null && v !== undefined) this.appendChild(this._doc().createTextNode(String(v)));
    }
    _doc() { return this.nodeType === 9 ? this : this.ownerDocument; }
    _adopt(c) {
      if (typeof c === "string") return this._doc().createTextNode(c);
      if (c.parentNode) c.parentNode.removeChild(c);
      return c;
    }
    appendChild(c) { return this.insertBefore(c, null); }
    insertBefore(c, ref) {
      if (c.nodeType === 11) { for (const k of c.childNodes.slice()) this.insertBefore(k, ref); return c; }
      c = this._adopt(c);
      const at = ref ? this.childNodes.indexOf(ref) : -1;
      if (at < 0) this.childNodes.push(c); else this.childNodes.splice(at, 0, c);
      c.parentNode = this;
      return c;
    }
    removeChild(c) {
      const at = this.childNodes.indexOf(c);
      if (at < 0) throw new Error("not a child");
      this.childNodes.splice(at, 1);
      c.parentNode = null;
      const d = this._doc();
      if (d && d._active && c.contains(d._active)) d._active = null;
      return c;
    }
    replaceChild(n, old) { this.insertBefore(n, old); this.removeChild(old); return old; }
    append(...ns) { for (const n of ns) this.appendChild(n); }
    prepend(...ns) { const first = this.firstChild; for (const n of ns) this.insertBefore(n, first); }
    replaceChildren(...ns) { for (const c of this.childNodes.slice()) this.removeChild(c); this.append(...ns); }
    remove() { if (this.parentNode) this.parentNode.removeChild(this); }
    contains(o) { for (let n = o; n; n = n.parentNode) if (n === this) return true; return false; }
    hasChildNodes() { return this.childNodes.length > 0; }
    addEventListener(t, fn, o) { listen(this, t, fn, o); }
    removeEventListener(t, fn, o) { unlisten(this, t, fn, o); }
    dispatchEvent(ev) { return dispatch(this, ev); }
    querySelectorAll(sel) {
      const list = parseList(sel), out = [];
      const walk = (n) => { for (const c of n.childNodes) { if (c.nodeType === 1) { if (matchList(c, list)) out.push(c); walk(c); } } };
      walk(this);
      return out;
    }
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
    getElementsByTagName(t) { return this.querySelectorAll(t); }
    getElementsByClassName(c) { return this.querySelectorAll("." + c.trim().split(/\s+/).join(".")); }
  }
  class Text extends Node { constructor(data, doc) { super(3, doc); this.data = String(data); } get nodeName() { return "#text"; } cloneNode() { return new Text(this.data, this.ownerDocument); } }
  class Comment extends Node { constructor(data, doc) { super(8, doc); this.data = String(data); } cloneNode() { return new Comment(this.data, this.ownerDocument); } }
  class Fragment extends Node {
    constructor(doc) { super(11, doc); }
    cloneNode(deep) { const f = new Fragment(this.ownerDocument); if (deep) for (const c of this.childNodes) f.appendChild(c.cloneNode(true)); return f; }
    getElementById(id) { return this.querySelector("#" + id); }
  }
  function classList(el) {
    const get = () => (el.getAttribute("class") || "").split(/\s+/).filter(Boolean);
    const set = (a) => el.setAttribute("class", a.join(" "));
    return {
      add: (...c) => { const a = get(); for (const k of c) if (!a.includes(k)) a.push(k); set(a); },
      remove: (...c) => { set(get().filter((k) => !c.includes(k))); },
      toggle: (c, force) => { const has = get().includes(c); const on = force === undefined ? !has : !!force; if (on && !has) set(get().concat(c)); else if (!on && has) set(get().filter((k) => k !== c)); return on; },
      contains: (c) => get().includes(c),
      replace: (a, b) => { const l = get(); const i = l.indexOf(a); if (i < 0) return false; l[i] = b; set(l); return true; },
      item: (i) => get()[i] || null,
      get length() { return get().length; },
      get value() { return el.getAttribute("class") || ""; },
      forEach: (fn) => get().forEach(fn),
    };
  }
  function styleOf() {
    const props = {};
    const api = {
      setProperty(k, v) { props[k] = String(v); },
      getPropertyValue(k) { return props[k] !== undefined ? props[k] : ""; },
      removeProperty(k) { const v = props[k]; delete props[k]; return v || ""; },
    };
    return new Proxy(api, {
      get(t, k) { if (k in t) return t[k]; if (k === "cssText") return Object.keys(props).map((p) => p + ": " + props[p]).join("; "); return typeof k === "string" && props[k] !== undefined ? props[k] : ""; },
      set(t, k, v) { if (k === "cssText") { for (const p of Object.keys(props)) delete props[p]; String(v).split(";").forEach((d) => { const i = d.indexOf(":"); if (i > 0) props[d.slice(0, i).trim()] = d.slice(i + 1).trim(); }); } else props[k] = String(v); return true; },
    });
  }
  const camel = (s) => s.replace(/-([a-z])/g, (m, c) => c.toUpperCase());
  const kebab = (s) => s.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
  function datasetOf(el) {
    return new Proxy({}, {
      get: (t, k) => (typeof k === "string" ? (el.getAttribute("data-" + kebab(k)) ?? undefined) : undefined),
      set: (t, k, v) => { el.setAttribute("data-" + kebab(k), v); return true; },
      deleteProperty: (t, k) => { el.removeAttribute("data-" + kebab(k)); return true; },
      has: (t, k) => el.hasAttribute("data-" + kebab(k)),
      ownKeys: () => [...el._a.keys()].filter((n) => n.startsWith("data-")).map((n) => camel(n.slice(5))),
      getOwnPropertyDescriptor: (t, k) => (el.hasAttribute("data-" + kebab(k)) ? { enumerable: true, configurable: true, value: el.getAttribute("data-" + kebab(k)) } : undefined),
    });
  }
  const reflect = (name) => ({ get() { return this.getAttribute(name) || ""; }, set(v) { this.setAttribute(name, v); } });
  const boolAttr = (name) => ({ get() { return this.hasAttribute(name); }, set(v) { if (v) this.setAttribute(name, ""); else this.removeAttribute(name); } });
  class Element extends Node {
    constructor(tag, doc) {
      super(1, doc);
      this.localName = String(tag).toLowerCase();
      this.tagName = this.localName.toUpperCase();
      this._a = new Map();
      this.style = styleOf();
      this.classList = classList(this);
      this.dataset = datasetOf(this);
      this.scrollTop = 0;
      this.scrollLeft = 0;
      if (this.localName === "template") this.content = new Fragment(doc);
      if (this.localName === "img") { this.complete = false; this.naturalWidth = 0; this.naturalHeight = 0; }
      if (this.localName === "video" || this.localName === "audio") {
        Object.assign(this, { currentTime: 0, duration: NaN, readyState: 0, paused: true, muted: false, volume: 1, ended: false, played: 0 });
      }
      if (this.localName === "dialog") this.open = false;
    }
    get nodeName() { return this.tagName; }
    getAttribute(n) { n = String(n).toLowerCase(); return this._a.has(n) ? this._a.get(n) : null; }
    setAttribute(n, v) { this._a.set(String(n).toLowerCase(), String(v)); }
    hasAttribute(n) { return this._a.has(String(n).toLowerCase()); }
    removeAttribute(n) { this._a.delete(String(n).toLowerCase()); }
    toggleAttribute(n, force) { const on = force === undefined ? !this.hasAttribute(n) : !!force; if (on) this.setAttribute(n, this.getAttribute(n) || ""); else this.removeAttribute(n); return on; }
    getAttributeNames() { return [...this._a.keys()]; }
    get attributes() { return [...this._a].map(([name, value]) => ({ name, value })); }
    get innerHTML() { return (this.localName === "template" ? this.content : this).childNodes.map(serialize).join(""); }
    set innerHTML(html) {
      const into = this.localName === "template" ? this.content : this;
      for (const c of into.childNodes.slice()) into.removeChild(c);
      parseInto(into, html, this.ownerDocument);
    }
    get outerHTML() { return serialize(this); }
    insertAdjacentHTML(pos, html) {
      const f = new Fragment(this.ownerDocument);
      parseInto(f, html, this.ownerDocument);
      this.insertAdjacentElement(pos, f);
    }
    insertAdjacentElement(pos, node) {
      pos = String(pos).toLowerCase();
      if (pos === "beforeend") this.appendChild(node);
      else if (pos === "afterbegin") this.insertBefore(node, this.firstChild);
      else if (pos === "beforebegin") this.parentNode.insertBefore(node, this);
      else if (pos === "afterend") this.parentNode.insertBefore(node, this.nextSibling);
      return node;
    }
    insertAdjacentText(pos, t) { this.insertAdjacentElement(pos, this.ownerDocument.createTextNode(t)); }
    matches(sel) { return matchList(this, parseList(sel)); }
    closest(sel) { const l = parseList(sel); for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (matchList(n, l)) return n; return null; }
    cloneNode(deep) {
      const c = this.ownerDocument.createElement(this.localName);
      for (const [k, v] of this._a) c._a.set(k, v);
      if (deep) {
        for (const k of this.childNodes) c.appendChild(k.cloneNode(true));
        if (this.content) for (const k of this.content.childNodes) c.content.appendChild(k.cloneNode(true));
      }
      return c;
    }
    get id() { return this.getAttribute("id") || ""; }
    set id(v) { this.setAttribute("id", v); }
    get className() { return this.getAttribute("class") || ""; }
    set className(v) { this.setAttribute("class", v); }
    get hidden() { return this.hasAttribute("hidden"); }
    set hidden(v) { if (v) this.setAttribute("hidden", ""); else this.removeAttribute("hidden"); }
    get inert() { return this.hasAttribute("inert"); }
    set inert(v) { if (v) this.setAttribute("inert", ""); else this.removeAttribute("inert"); }
    get disabled() { return this.hasAttribute("disabled"); }
    set disabled(v) { if (v) this.setAttribute("disabled", ""); else this.removeAttribute("disabled"); }
    get tabIndex() { const t = this.getAttribute("tabindex"); return t === null ? -1 : Number(t); }
    set tabIndex(v) { this.setAttribute("tabindex", v); }
    get value() { if (this._value !== undefined) return this._value; if (this.localName === "textarea") return this.textContent; if (this.localName === "select") { const o = this.querySelector("option[selected]") || this.querySelector("option"); return o ? o.value : ""; } return this.getAttribute("value") || ""; }
    set value(v) { this._value = String(v); }
    get checked() { return this._checked !== undefined ? this._checked : this.hasAttribute("checked"); }
    set checked(v) { this._checked = !!v; }
    get offsetParent() { return !this.isConnected || this.closest("[hidden]") ? null : this.parentElement; }
    get offsetWidth() { return 0; } get offsetHeight() { return 0; } get offsetTop() { return 0; } get offsetLeft() { return 0; }
    get clientWidth() { return 0; } get clientHeight() { return 0; } get scrollWidth() { return 0; } get scrollHeight() { return 0; }
    getBoundingClientRect() { return ZERO_RECT; }
    getClientRects() { return []; }
    scrollIntoView() {}
    scrollBy() {}
    scrollTo() {}
    focus() { this.ownerDocument._focus(this); }
    blur() { if (this.ownerDocument._active === this) this.ownerDocument._focus(null); }
    click() { if (!this.disabled) dispatch(this, new Event("click", { bubbles: true, button: 0 })); }
    // <dialog>
    showModal() { this.open = true; this.setAttribute("open", ""); }
    show() { this.showModal(); }
    close() { if (!this.open) return; this.open = false; this.removeAttribute("open"); dispatch(this, new Event("close")); }
    // <img>, <video>, <audio>
    decode() {
      if (this.complete && this.naturalWidth) return Promise.resolve();
      return new Promise((resolve, reject) => { (this._decode = this._decode || []).push([resolve, reject]); });
    }
    play() { this.paused = false; this._played = (this._played || 0) + 1; return Promise.resolve(); }
    pause() { this.paused = true; }
    load() { this._loads = (this._loads || 0) + 1; }
    canPlayType() { return "maybe"; }
  }
  for (const n of ["href", "src", "alt", "title", "type", "name", "rel", "target", "lang", "download", "poster", "preload", "role", "placeholder", "htmlFor"]) {
    Object.defineProperty(Element.prototype, n, reflect(n === "htmlFor" ? "for" : n));
  }
  for (const n of ["required", "readOnly", "multiple", "selected", "autoplay", "controls", "loop", "playsInline"]) Object.defineProperty(Element.prototype, n, boolAttr(n.toLowerCase()));
  Object.defineProperty(Element.prototype, "decoding", reflect("decoding"));
  Object.defineProperty(Element.prototype, "loading", reflect("loading"));

  class Document extends Node {
    constructor() {
      super(9, null);
      this.readyState = "loading";
      this.visibilityState = "visible";
      this.hidden = false;
      this.fullscreenElement = null;
      this.cookie = "";
      this._active = null;
      this.documentElement = this.createElement("html");
      this.appendChild(this.documentElement);
      this.head = this.createElement("head");
      this.body = this.createElement("body");
      this.documentElement.append(this.head, this.body);
    }
    get nodeName() { return "#document"; }
    createElement(t) { return new Element(t, this); }
    createElementNS(ns, t) { return new Element(t, this); }
    createTextNode(t) { return new Text(t, this); }
    createComment(t) { return new Comment(t, this); }
    createDocumentFragment() { return new Fragment(this); }
    getElementById(id) { return this.querySelector("#" + String(id).replace(/[^\w-]/g, "\\$&")); }
    get activeElement() { const a = this._active; return a && a.isConnected ? a : this.body; }
    hasFocus() { return true; }
    get title() { const t = this.querySelector("title"); return t ? t.textContent : ""; }
    set title(v) { let t = this.querySelector("title"); if (!t) { t = this.createElement("title"); this.head.appendChild(t); } t.textContent = v; }
    _focus(el) {
      if (el && (!el.isConnected || el.closest("[hidden], [inert]") || el.disabled)) return;
      const old = this._active && this._active.isConnected ? this._active : null;
      if (old === el) return;
      this._active = el;
      if (old) { dispatch(old, new Event("blur")); dispatch(old, new Event("focusout", { bubbles: true, relatedTarget: el })); }
      if (el) { dispatch(el, new Event("focus")); dispatch(el, new Event("focusin", { bubbles: true, relatedTarget: old })); }
    }
    exitFullscreen() { return Promise.resolve(); }
  }

  /* ---------------- the window ---------------- */
  function storage() {
    const m = new Map();
    return {
      getItem: (k) => (m.has(String(k)) ? m.get(String(k)) : null),
      setItem: (k, v) => { m.set(String(k), String(v)); },
      removeItem: (k) => { m.delete(String(k)); },
      clear: () => m.clear(),
      key: (i) => [...m.keys()][i] || null,
      get length() { return m.size; },
    };
  }
  class Observer { constructor(cb) { this.cb = cb; (G.__observers = G.__observers || []).push(this); this.targets = []; } observe(t) { this.targets.push(t); } unobserve() {} disconnect() { this.targets = []; } takeRecords() { return []; } }
  G.MutationObserver = class extends Observer {};
  G.ResizeObserver = class extends Observer {};
  G.IntersectionObserver = class extends Observer {};
  G.localStorage = storage();
  G.sessionStorage = storage();
  G.matchMedia = (q) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
  G.getComputedStyle = () => new Proxy({}, { get: (t, k) => (k === "getPropertyValue" ? () => "" : "") });
  G.getSelection = () => ({ toString: () => "", removeAllRanges() {} });
  G.customElements = { get: () => undefined, define() {}, whenDefined: () => new Promise(() => {}) };
  G.innerWidth = 1280;
  G.innerHeight = 800;
  G.scrollX = G.scrollY = G.pageYOffset = 0;
  G.scrollTo = G.scrollBy = () => {};
  G.devicePixelRatio = 1;
  G.isSecureContext = true;
  G.alert = () => {};
  G.confirm = () => true;
  G.open = () => null;
  G.screen = { width: 1280, height: 800 };
  G.navigator = { onLine: true, userAgent: "Mozilla/5.0 (pretend page)", language: "en-US", languages: ["en-US"], maxTouchPoints: 0, vendor: "" };

  G.__dom = {
    Element, Text, Document, Fragment, parseList, matchList,
    boot(o) {
      const doc = new Document();
      G.document = doc;
      const url = new G.URL(o.url || "https://example.test/aagrapevine/");
      const loc = {
        get href() { return url.href; }, set href(v) { G.__navigated = String(v); },
        get origin() { return url.origin; }, get protocol() { return url.protocol; }, get host() { return url.host; },
        get hostname() { return url.hostname; }, get pathname() { return url.pathname; }, get search() { return url.search; },
        get hash() { return url.hash; }, set hash(v) { url.hash = v; },
        reload() { G.__reloads = (G.__reloads || 0) + 1; }, assign(v) { G.__navigated = String(v); }, replace(v) { G.__navigated = String(v); },
        toString() { return url.href; },
      };
      G.location = loc;
      G.history = {
        state: null, length: 1,
        replaceState(s, t, u) { this.state = s; if (u !== undefined && u !== null) { const n = new G.URL(String(u), url.href); url.href = n.href; } },
        pushState(s, t, u) { this.replaceState(s, t, u); this.length += 1; },
        back() {},
      };
      let html = String(o.html || "");
      const m = /<body[^>]*>([\s\S]*)<\/body>/i.exec(html);
      const head = /<head[^>]*>([\s\S]*)<\/head>/i.exec(html);
      if (head) parseInto(doc.head, head[1], doc);
      parseInto(doc.body, m ? m[1] : html, doc);
      const lang = /<html[^>]*\blang="([^"]*)"/i.exec(html);
      if (lang) doc.documentElement.setAttribute("lang", lang[1]);
      doc.readyState = o.readyState || "loading";
      return doc;
    },
    // an <img> finishes loading (ok) or fails
    loadImage(img, ok, w = 640, h = 480) {
      img.complete = true;
      img.naturalWidth = ok ? w : 0;
      img.naturalHeight = ok ? h : 0;
      const waits = img._decode || [];
      img._decode = null;
      for (const [res, rej] of waits) { if (ok) res(); else rej(new Error("EncodingError")); }
      dispatch(img, new Event(ok ? "load" : "error"));
    },
  };
  G.Image = function Image(w, h) { const i = G.document.createElement("img"); if (w) i.setAttribute("width", w); if (h) i.setAttribute("height", h); return i; };
  G.Audio = function Audio(src) { const a = G.document.createElement("audio"); if (src) a.src = src; return a; };
  G.HTMLElement = Element;
  G.Element = Element;
  G.Node = Node;
})(globalThis);
