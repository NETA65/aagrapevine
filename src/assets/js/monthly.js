/* /monthly/ — the Monthly toolkit's pages (src/pages/monthly.njk, the hub; monthly-month.njk, a month):
   1. The poster: the scale-to-fit fallback and the "fill the canvas" fit (month pages).
   2. "Over" marks (both pages; the build marks what was over when it ran, this keeps it true while the
      page stays open or is read later): an element whose data-mp-over instant has passed — a hub chip
      ([data-mp-chip]) hides, and its list ([data-mp-chips]) when no chip is left; a month page's date or
      Book of the Month row gets .is-past and shows its "Over" badge ([data-mp-over-badge]). The new-month
      notice ([data-mp-newmonth="YYYY-MM"]) shows once the visitor's month (Central time) is that month or
      later — the site has not been rebuilt for it yet; a copy two or more months old (saved for offline
      use) names and links the visitor's month ([data-mp-newmonth-label], data-mp-newmonth-text). On load,
      every minute (a page left open) and each time the page is shown again; a chip that holds keyboard
      focus goes once focus leaves it.
   3. "Send it as a message" (month pages): the Alpine component mpMessage — this language or both,
      remembered as "gv-digest-bi" (the Monthly digest's key: one choice for both tools), and the Copy
      buttons (GV.copy copies the prebuilt text and says so).
   4. "Download image (PNG)" and "Share" (month pages). Progressive enhancement: the Download and Share
      buttons are `hidden` in the HTML and shown here; Print works on its own (onclick="window.print()";
      the print stylesheet prints only the poster).
      The PNG is made from the unscaled poster node (1080 × 1350) with html-to-image, self-hosted at
      assets/vendor/html-to-image.js and loaded on first use. It waits for document.fonts.ready and
      html-to-image embeds the site's self-hosted fonts, so the image looks like the page.
      Share: Web Share API level 2 with the PNG file where the browser can share files (phones →
      WhatsApp …); anywhere else it copies the page link.
   Every storage access is in try/catch: the page works the same without storage (one language). */
(function () {
  "use strict";
  var GV = window.GV || {};
  var announce = function (msg) { if (GV.announce) GV.announce(msg); };
  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";

  /* ---------- 1. The poster ---------- */

  /* Scale-to-fit fallback: the CSS uses tan(atan2(100cqw, 1080px)); older browsers get --mp-s here. */
  var cssScale = window.CSS && CSS.supports && CSS.supports("width", "calc(tan(atan2(1px, 2px)) * 1px)");
  if (!cssScale && "ResizeObserver" in window) {
    var ro = new ResizeObserver(function (entries) {
      entries.forEach(function (e) {
        var p = e.target.querySelector(".mp-poster");
        if (p) p.style.setProperty("--mp-s", String(e.contentRect.width / 1080));
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll(".mp-fit"), function (f) { ro.observe(f); });
  }

  /* Fill the canvas: the poster's type (all in em) is sized to the largest step at which every
     block still fits its column — busy months (many events, long Spanish titles) step down,
     quiet months step up, so no poster is left with a half-empty page. Every date of the month is on
     the poster (round 26b), so a busy month's blocks also take the room another column leaves (round 27:
     the type gets as large as the room allows — a column's blocks sit together at its top, so what is left
     is one band at its foot, and the fit gives that room to the column that needs it):
       · a block that may sit in another column (data-mp-move="b a", the build's place first; the columns are
         [data-mp-slot]) is tried in each, in its place in the reading order (data-mp-order);
       · the dates may flow on from a column into the next (data-mp-move "a+b": the rows that fit at the foot
         of a — one at least, under the heading —, the others at the head of b, in a block of their own,
         .mp-dates--more, where nothing comes before them in b and nothing after the dates in a);
       · the rule between the columns may move a step or two toward the column that needs the room (the
         layout's data-mp-widths: values of its --mp-split, the build's first; data-mp-sizes: the column a
         larger value widens, then the one it narrows — areas/monthly.css);
       · the dates may stand in one more column (.mp-dates--cols: two in a column, four in a band across).
     The arrangement whose type is largest wins — the build's own (its columns, its rule, one column of
     dates) unless another is larger; another counts only where every date's title keeps a line of
     MIN_ROW_EM at least (narrower, a title breaks into four or five short lines), and the dates in more
     columns only where they beat one column by MORE_COLS steps. The search, on a hidden copy, in quarter
     pixels: every arrangement of the blocks once, with the build's rule and one column of dates — one that
     cannot beat the best so far is dropped after one layout, one that can is raised step by step (1, 2,
     4 … then halving); then, for the best and the NEAR arrangements that fell short by least, what may free
     the one of the two columns that runs out of room: the rule a step toward it, the dates in one more
     column where they are what is too tall (as long as each step helps). As many layouts a task as fit in
     BUDGET_MS (the page never freezes, the visible poster changes once): about as long as round 26b's fit
     took, a third longer in the busiest month. Only for the full-size poster of a month page (the hub shows the
     months in miniature — macros/monthly.njk posterMini, never fitted). The PNG and the print use this DOM;
     once it is done the poster carries data-mp-fit (the share pictures wait for it:
     scripts/ops/poster_share.py) and fitDone resolves (the PNG waits for it). */
  var BLOCKS = ".mp-b, .mp-foot, .mp-head, .mp-row, .mp-col, .mp-body, .mp-board, .mp-cover, .mp-strip, .mp-page, .mp-main, .mp-stub, .mp-side, .mp-content, .mp-top, .mp-feature, .mp-rail, .mp-band";
  var MIN_PX = 15, MAX_PX = 28;            // the type's range (poster px; 15px prints at 7.5 pt on Letter)
  var MAX_PLACES = 48;                     // arrangements of the movable blocks tried at most
  var BUDGET_MS = 12;                      // the fit's layouts in one task (then the page gets its turn)
  var MIN_ROW_EM = 10;                     // a date's title: room for 10 of its own em beside its chip, at least
  var MORE_COLS = 2;                       // the dates in more columns: only for this many quarter pixels more, at least
  var NEAR = 6;                            // the arrangements held back by least whose column rule and dates are tried
  var toArray = function (list) { return Array.prototype.slice.call(list); };
  var now = function () { return window.performance && performance.now ? performance.now() : Date.now(); };
  // Layout boxes in poster px (offset* ignore the scale and the tilted cork cards' rotation).
  function box(el, p) {
    var t = 0, l = 0, e = el;
    while (e && e !== p) { t += e.offsetTop; l += e.offsetLeft; e = e.offsetParent; }
    return { t: t, b: t + el.offsetHeight, r: l + el.offsetWidth };
  }
  // A date's row too narrow for its title (less than MIN_ROW_EM of the title's type beside the chip).
  function narrow(p) {
    var rows = p.querySelectorAll(".mp-dlist > li");
    for (var i = 0; i < rows.length; i++) {
      var li = rows[i], ls = getComputedStyle(li), chip = li.querySelector(".mp-chip"), t = li.querySelector(".mp-date-t");
      if (!t) continue;
      var room = li.clientWidth - (parseFloat(ls.paddingLeft) || 0) - (parseFloat(ls.paddingRight) || 0) - (chip ? chip.offsetWidth : 0) - (parseFloat(ls.columnGap) || 0);
      if (room < MIN_ROW_EM * (parseFloat(getComputedStyle(t).fontSize) || 16)) return true;
    }
    return false;
  }
  // The lowest a block in this column may reach (box() px): the foot of its content box, or of a box around it that
  // ends higher (a grid's row grows with its tallest column — the area around it does not); as overflowing() reads it.
  function footOf(slot, p) {
    var lim = Infinity;
    for (var e = slot; e; e = e.parentElement) {
      var pad = parseFloat(getComputedStyle(e).paddingBottom) || 0;
      lim = Math.min(lim, e === p ? p.clientHeight - pad : box(e, p).t + e.clientTop + e.clientHeight - pad);
      if (e === p) break;
    }
    return lim;
  }
  // How far the block that overflows most runs past its parent's content box (or the poster's right edge), in px beyond
  // the 2px allowed; 0 when every block fits.
  function overflowing(p) {
    var blocks = p.querySelectorAll(BLOCKS), most = 0;
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i], par = b.parentElement, bb = box(b, p);
      // the parent's content box (inside its padding)
      var pad = parseFloat(getComputedStyle(par).paddingBottom) || 0;
      var limit = par === p ? p.clientHeight - pad : box(par, p).t + par.clientTop + par.clientHeight - pad;
      most = Math.max(most, bb.b - limit - 2, bb.r - p.clientWidth - 2);
    }
    return most;
  }
  // A block into a column, before the first block that comes after it in the reading order (data-mp-order).
  function place(slot, el) {
    var ord = Number(el.getAttribute("data-mp-order")) || 0, before = null;
    for (var k = 0; k < slot.children.length; k++) {
      var ch = slot.children[k];
      if (ch !== el && (Number(ch.getAttribute("data-mp-order")) || 0) > ord) { before = ch; break; }
    }
    if (el.parentNode !== slot || el.nextElementSibling !== before) slot.insertBefore(el, before);
  }
  // Every arrangement of the movable blocks (each in one of its places: a column, or "a+b"), the build's own first; at
  // most MAX_PLACES.
  function arrangements(movers) {
    var all = [[]];
    movers.forEach(function (m) {
      var opts = (m.getAttribute("data-mp-move") || "").split(/\s+/).filter(Boolean), next = [];
      all.forEach(function (a) { opts.forEach(function (o) { if (next.length < MAX_PLACES) next.push(a.concat([o])); }); });
      all = next;
    });
    return all;
  }
  // The layout's column rule: the element whose --mp-split it sets (data-mp-widths: its values, the build's first), the
  // values from the narrowest to the widest for the column they size, and the two columns (data-mp-sizes="a b": the one a
  // larger value widens, the one it narrows).
  function splitOf(root) {
    var el = root.querySelector("[data-mp-widths]");
    if (!el) return null;
    var vals = el.getAttribute("data-mp-widths").split(/\s+/).filter(Boolean), cols = (el.getAttribute("data-mp-sizes") || "").split(/\s+/);
    var sorted = vals.slice().sort(function (x, y) { return parseFloat(x) - parseFloat(y); });
    return { el: el, vals: sorted, build: sorted.indexOf(vals[0]), wide: cols[0], narrow: cols[1] };
  }
  // The dates' rows back in their own block (none flowing on).
  function unflow(root) {
    var more = root.querySelector(".mp-dates--more");
    if (!more) return;
    var list = root.querySelector(".mp-dates:not(.mp-dates--more) .mp-dlist"), rest = more.querySelector(".mp-dlist");
    while (rest && rest.firstChild) list.appendChild(rest.firstChild);
    more.parentNode.removeChild(more);
  }
  // A combo ({ slots, wi, cols }) in place: each movable block in its column, the column rule (sp.vals[wi]), the dates in
  // one or more columns. → the dates' flow ({ dates, from, to, more } when they may flow on from one column into the
  // next), null when they do not, false when this combo cannot be (a flow with a block after the dates in their column,
  // or before them in the next — the rows that flow on would not read on from where they left off).
  function arrange(root, movers, combo, sp) {
    unflow(root);
    var flow = null;
    movers.forEach(function (m, i) {
      var to = combo.slots[i].split("+"), slot = root.querySelector('[data-mp-slot="' + to[0] + '"]');
      if (slot) place(slot, m);
      if (to[1] && slot) flow = { dates: m, from: slot, to: root.querySelector('[data-mp-slot="' + to[1] + '"]') };
    });
    if (sp) { if (combo.wi === sp.build) sp.el.style.removeProperty("--mp-split"); else sp.el.style.setProperty("--mp-split", sp.vals[combo.wi]); }
    Array.prototype.forEach.call(root.querySelectorAll(".mp-dates"), function (d) { d.classList.toggle("mp-dates--cols", !!combo.cols); });
    if (!flow) return null;
    var ord = Number(flow.dates.getAttribute("data-mp-order")) || 0;
    var after = toArray(flow.from.children).some(function (k) { return k !== flow.dates && (Number(k.getAttribute("data-mp-order")) || 0) > ord; });
    var before = !flow.to || toArray(flow.to.children).some(function (k) { var o = Number(k.getAttribute("data-mp-order")); return o >= 10 && o <= ord; });
    if (after || before) return false;
    // the block the rows flow on into: the dates' own (classes, colours, its place in the reading order next), no heading
    var more = flow.dates.cloneNode(false);
    more.classList.add("mp-dates--more");
    more.removeAttribute("data-mp-move");
    more.setAttribute("data-mp-order", String(ord + 1));
    more.appendChild(flow.dates.querySelector(".mp-dlist").cloneNode(false));
    flow.more = more;
    return flow;
  }
  // The dates flowing on at this type: every row in their column first; from the first row that runs past the column's
  // foot, the rows go to the head of the next column. → false when no row would stay under the heading.
  function flowOn(root, flow) {
    unflow(root);
    var list = flow.dates.querySelector(".mp-dlist"), rows = list.children;
    var cs = getComputedStyle(flow.dates);
    var foot = footOf(flow.from, root) - (parseFloat(cs.paddingBottom) || 0) - (parseFloat(cs.borderBottomWidth) || 0);
    var i = 0;
    while (i < rows.length && box(rows[i], root).b <= foot + 2) i++;
    if (i === rows.length) return true;               // all of them fit: nothing flows on
    if (i < 1) return false;
    place(flow.to, flow.more);
    var rest = flow.more.querySelector(".mp-dlist");
    while (rows.length > i) rest.appendChild(rows[i]);
    return true;
  }
  // The height a column's blocks need, packed at its top (its padding included; a footer's auto margin left out). The
  // two columns of a layout's rule start level and end level, so the one that needs more is the one out of room.
  function need(slot) {
    var cs = getComputedStyle(slot), h = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0), n = 0;
    toArray(slot.children).forEach(function (k) { if (k.offsetHeight) { h += k.offsetHeight; n++; } });
    return h + Math.max(0, n - 1) * (parseFloat(cs.rowGap) || 0);
  }
  function fit(p, done) {
    // the copy: same classes and content, unscaled, positioned (so offsetParent stops at it), out of sight
    var holder = document.createElement("div");
    holder.className = "mp-measure";
    holder.setAttribute("aria-hidden", "true");
    holder.style.cssText = "position:absolute;left:-12000px;top:0;width:1080px;visibility:hidden;pointer-events:none;";
    var c = p.cloneNode(true);
    c.removeAttribute("data-mp-poster");
    c.removeAttribute("aria-labelledby");
    Array.prototype.forEach.call(c.querySelectorAll("[id]"), function (el) { el.removeAttribute("id"); });
    c.style.position = "relative";
    c.style.fontSize = "";
    holder.appendChild(c);
    document.body.appendChild(holder);
    // the type in quarter pixels (k / 4 px): the largest k at which nothing overflows, for each arrangement
    var base = Math.floor((parseFloat(getComputedStyle(c).fontSize) || 23) * 4);
    var minK = MIN_PX * 4, topK = Math.floor(Math.min(base / 4 * 1.25, MAX_PX) * 4);
    var cm = toArray(c.querySelectorAll("[data-mp-move]")), pm = toArray(p.querySelectorAll("[data-mp-move]"));
    var sp = splitOf(c), psp = splitOf(p), hasDates = !!c.querySelector(".mp-dates .mp-dlist");
    // what is left to try: every arrangement of the blocks with the build's rule and one column of dates, the build's
    // own first; one held back a step up puts the steps that may free it (explore) at the front
    var todo = arrangements(cm).map(function (s, i) { return { slots: s, wi: sp ? sp.build : 0, cols: false, build: i === 0 }; });
    // the best type with one column of dates and with more (the dates in more columns win only by MORE_COLS steps or
    // more: a tie, or a quarter pixel, keeps the plainer poster)
    var seen = {}, cur = null, best = [-1, -1], bestCombo = [todo[0], null], lo = 0, hi = 0, searching = false, flow = null;
    var aim = function (cb) { return cb.cols ? Math.max(best[1] + 1, best[0] + MORE_COLS) : best[0] + 1; };
    // the arrangements held back in the first round ({ short: by how many px, next: the steps that may free them }); the
    // NEAR closest get those steps tried in the second (every arrangement once, then the rule and the dates' columns for
    // the best and the nearest — trying them for every arrangement took three times as long)
    var held = [], round = 1, short = 0, gal = 0, lastK = -1, lastOk = false;
    // (the build's own arrangement is measured as it is: no month's type can end up smaller than it)
    var fits = function (k) {
      lastK = k;
      lastOk = false;
      c.style.fontSize = k / 4 + "px";
      if (flow && !flowOn(c, flow)) { short = Infinity; return false; }
      short = overflowing(c);
      if (short > 0) return false;
      if (!cur.build && narrow(c)) { short = Infinity; return false; }
      return (lastOk = true);
    };
    // The copy as it stands, held back: → what to try next, the rule a step toward whichever of its two columns runs out
    // of room, and the dates in one more column where they are what is too tall (in that column, or across under it).
    function explore(cb) {
      var next = [], tight = null;
      if (sp) {
        var a = c.querySelector('[data-mp-slot="' + sp.wide + '"]'), b = c.querySelector('[data-mp-slot="' + sp.narrow + '"]');
        if (a && b) tight = need(a) >= need(b) ? sp.wide : sp.narrow;
        var wi = cb.wi + (tight === sp.wide ? 1 : -1);
        if (tight && wi >= 0 && wi < sp.vals.length) next.push({ slots: cb.slots, wi: wi, cols: cb.cols });
      }
      if (!cb.cols && hasDates) {
        var d = c.querySelector(".mp-dates"), ds = d && d.parentElement.closest("[data-mp-slot]");
        var where = ds ? ds.getAttribute("data-mp-slot") : "";
        if (!tight || where === tight || (where !== sp.wide && where !== sp.narrow)) next.push({ slots: cb.slots, wi: cb.wi, cols: true });
      }
      return next;
    }
    // held back at the step it had to reach: its next steps now (the best so far, the second round), or kept for later
    function heldBack(cb) {
      if (round === 1 && !cb.build) held.push({ short: short, next: explore(cb) });
      else todo.unshift.apply(todo, explore(cb));
    }
    // one layout (or two, the dates flowing on) of the search; → true once it is over
    function step() {
      if (searching) {
        if (hi - lo > 1) {
          // up from the step it holds by a step, two, four … (most beat the best by a step or two), then halving
          var mid = gal ? Math.min(lo + gal, hi - 1) : (lo + hi) >> 1;
          if (fits(mid)) { lo = mid; gal *= 2; } else { hi = mid; gal = 0; }
          return false;
        }
        searching = false;
        // (lo below minK: nothing fits even at the smallest type — another arrangement may still)
        var w = cur.cols ? 1 : 0;
        if (lo > best[w]) { best[w] = lo; bestCombo[w] = cur; }
        // what holds it back a step up (the copy stands so when that was the last size tried)
        var a = aim(cur);
        if (a <= topK && ((lastK === a && !lastOk) || !fits(a))) todo.unshift.apply(todo, explore(cur));
        return false;
      }
      cur = todo.shift();
      if (!cur && round === 1) {
        round = 2;
        held.sort(function (x, y) { return x.short - y.short; }).slice(0, NEAR).forEach(function (h) { todo.push.apply(todo, h.next); });
        cur = todo.shift();
      }
      if (!cur) return true;
      var key = cur.slots.join(" ") + "|" + cur.wi + "|" + (cur.cols ? 1 : 0);
      if (seen[key]) return false;
      seen[key] = true;
      flow = arrange(c, cm, cur, sp);
      if (flow === false) return false;
      if (cur.build) {
        // the build's arrangement: from the type the stylesheet gives it (the month's density)
        lo = minK - 1; hi = topK + 1; gal = 0; searching = true;
        if (Math.min(base, topK) >= minK) { if (fits(Math.min(base, topK))) lo = Math.min(base, topK); else hi = Math.min(base, topK); }
      } else if (aim(cur) <= topK) {
        // another: only when it holds the step it must beat (else, after this one layout, only what may free it is tried)
        if (fits(aim(cur))) { lo = aim(cur); hi = topK + 1; gal = 1; searching = true; } else heldBack(cur);
      }
      return false;
    }
    (function run() {
      for (var until = now() + BUDGET_MS; now() < until;) {
        if (!step()) continue;
        // the winner, on the copy at its type (where its rows flow on), then on the poster itself
        var w = best[1] >= best[0] + MORE_COLS ? 1 : 0, win = bestCombo[w];
        flow = arrange(c, cm, win, sp);
        var k = Math.max(best[w], minK), stay = -1;
        c.style.fontSize = k / 4 + "px";
        if (flow && flowOn(c, flow) && c.querySelector(".mp-dates--more")) stay = flow.dates.querySelector(".mp-dlist").children.length;
        holder.remove();
        var pf = arrange(p, pm, win, psp);
        p.style.fontSize = k / 4 + "px";
        if (pf && stay > 0) {
          var rows = pf.dates.querySelector(".mp-dlist").children, rest = pf.more.querySelector(".mp-dlist");
          place(pf.to, pf.more);
          while (rows.length > stay) rest.appendChild(rows[stay]);
        }
        p.setAttribute("data-mp-fit", "");
        if (done) done();
        return;
      }
      setTimeout(run, 0);
    })();
  }
  // Resolves once every poster of the page is fitted (the PNG is made from the fitted poster).
  var fitDone = new Promise(function (resolve) {
    var fitAll = function () {
      var posters = document.querySelectorAll(".mp-stage:not(.mp-stage--thumb) [data-mp-poster]"), left = posters.length;
      if (!left) { resolve(); return; }
      Array.prototype.forEach.call(posters, function (p) { fit(p, function () { if (--left === 0) resolve(); }); });
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitAll); else fitAll();
  });

  /* ---------- 2. "Over" marks and the new-month notice ---------- */
  var each = function (sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); };
  // The visitor's month in Central time ("2026-10"), like the build's month (home.js does the same for days;
  // like it, only a real YYYY-MM-DD is taken: the notice's link and words are made from it).
  function centralMonth() {
    try {
      var s = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.slice(0, 7);
    } catch (e) { /* fall through */ }
    return new Date().toISOString().slice(0, 7);
  }
  // A hub chip that holds keyboard focus is never hidden under the reader: it goes once focus leaves it
  // (app.js GV.expire's rule).
  var afterFocus = function (el) {
    if (el.__mpOverWait) return;
    el.__mpOverWait = true;
    el.addEventListener("focusout", function () { el.__mpOverWait = false; setTimeout(markOver, 0); }, { once: true });
  };
  function markOver() {
    var now = Date.now(), active = document.activeElement;
    each("[data-mp-over]", function (el) {
      var t = Date.parse(el.getAttribute("data-mp-over") || "");
      if (isNaN(t) || t > now) return;
      if (el.hasAttribute("data-mp-chip")) {
        if (!el.hidden && active && active !== document.body && el.contains(active)) { afterFocus(el); return; }
        el.hidden = true;
        return;
      }
      el.classList.add("is-past");
      var badge = el.querySelector("[data-mp-over-badge]");
      if (badge) badge.hidden = false;
    });
    each("[data-mp-chips]", function (list) {
      list.hidden = !Array.prototype.some.call(list.querySelectorAll("[data-mp-chip]"), function (c) { return !c.hidden; });
    });
    // The new-month notice, once the visitor's month is its month or later. A copy two or more months old (a page
    // saved for offline use, or no rebuild for a while) names and links the VISITOR's month, not the one after the
    // build's: data-mp-newmonth-text holds the words with {month} unfilled, and the link's own address is kept in
    // data-mp-href (a month can turn while the page is open: every minute starts from it).
    var month = centralMonth();
    each("[data-mp-newmonth]", function (el) {
      var key = el.getAttribute("data-mp-newmonth") || "9999-99";
      el.hidden = !(month >= key);
      if (el.hidden) return;
      var a = el.querySelector("a"), label = el.querySelector("[data-mp-newmonth-label]"), text = el.getAttribute("data-mp-newmonth-text");
      if (a && a.getAttribute("href")) {
        if (!a.hasAttribute("data-mp-href")) a.setAttribute("data-mp-href", a.getAttribute("href"));
        var href = a.getAttribute("data-mp-href").replace("/" + key + "/", "/" + month + "/");
        if (a.getAttribute("href") !== href) a.setAttribute("href", href);
      }
      if (label && text) {
        try {
          var words = text.replace("{month}", new Intl.DateTimeFormat(document.documentElement.lang === "es" ? "es-US" : "en-US",
            { month: "long", timeZone: "UTC" }).format(new Date(month + "-15T12:00:00Z")));
          if (label.textContent !== words) label.textContent = words;    // (a live region: only a real change is read out)
        } catch (e) { /* the build's words stay */ }
      }
    });
  }
  // Now, every minute (a month page left open — shown at a district meeting — marks a meeting "Over" as it
  // ends, as the home page, /events/ and /bulletin/ hide theirs), and when the page is shown again (a tab
  // brought back to the front, or a page restored by the Back button).
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", markOver); else markOver();
  setInterval(markOver, 60000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) markOver(); });
  window.addEventListener("pageshow", function (e) { if (e.persisted) markOver(); });

  /* ---------- 3. "Send it as a message" (Alpine starts after this file: see base.njk) ---------- */
  document.addEventListener("alpine:init", function () {
    window.Alpine.data("mpMessage", function () {
      return {
        bi: false,
        init: function () {
          try { this.bi = localStorage.getItem("gv-digest-bi") === "1"; } catch (e) { /* no storage: this language */ }
        },
        setBi: function (v) {
          this.bi = !!v;
          try { localStorage.setItem("gv-digest-bi", v ? "1" : "0"); } catch (e) { /* not remembered */ }
        },
        // kind: "wa" | "email" → the prebuilt text of the chosen language(s): #mp-msg-<kind>-<one|bi>
        copy: function (kind, btn) {
          var el = document.getElementById("mp-msg-" + kind + "-" + (this.bi ? "bi" : "one"));
          if (el && GV.copy) GV.copy(el.textContent, btn);
        },
      };
    });
  });

  /* ---------- 4. Download image (PNG) and Share ---------- */
  var poster = document.querySelector(".mp-print-root [data-mp-poster]");
  var dl = document.querySelector("[data-mp-download]");
  var sh = document.querySelector("[data-mp-share]");
  if (!poster || !dl) return;

  var base = ((window.SITE && window.SITE.base) || "/").replace(/\/?$/, "/");
  var libPromise = null;
  function loadLib() {
    if (window.htmlToImage) return Promise.resolve(window.htmlToImage);
    if (!libPromise) {
      libPromise = new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = base + "assets/vendor/html-to-image.js";
        s.onload = function () { window.htmlToImage ? resolve(window.htmlToImage) : reject(new Error("html-to-image")); };
        s.onerror = function () { libPromise = null; reject(new Error("html-to-image failed to load")); };
        document.head.appendChild(s);
      });
    }
    return libPromise;
  }

  // The poster's icons point at the page's icon sprite (<use href="#i-…">, eleventy/icons.js), which the picture
  // doesn't hold (html-to-image copies the poster alone): each gets its drawing inline first, as on screen.
  function inlineIcons(root) {
    Array.prototype.forEach.call(root.querySelectorAll("svg > use[href^='#i-']"), function (u) {
      var sym = document.getElementById(u.getAttribute("href").slice(1));
      if (!sym) return;
      Array.prototype.forEach.call(sym.childNodes, function (n) { u.parentNode.insertBefore(n.cloneNode(true), u); });
      u.parentNode.removeChild(u);
    });
  }

  var blobPromise = null;
  function render() {
    if (blobPromise) return blobPromise;
    var fontsReady = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    // (the poster fitted first: its type and the places of its blocks)
    blobPromise = Promise.all([loadLib(), fontsReady, fitDone]).then(function (r) {
      var h2i = r[0];
      inlineIcons(poster);
      var opts = {
        width: 1080, height: 1350, canvasWidth: 1080, canvasHeight: 1350, pixelRatio: 1, cacheBust: false,
        backgroundColor: getComputedStyle(poster).backgroundColor || "#ffffff",
        // The on-screen poster is scaled down with a transform: the image is taken unscaled.
        style: { transform: "none", position: "relative", top: "0", left: "0", margin: "0" },
      };
      // First pass warms the image/font caches (Safari drops fonts on the very first draw).
      return h2i.toBlob(poster, opts).then(function () { return h2i.toBlob(poster, opts); });
    }).then(function (blob) {
      if (!blob) throw new Error("empty image");
      return blob;
    }, function (err) { blobPromise = null; throw err; });
    return blobPromise;
  }

  // Busy state without `disabled`: a disabled button loses keyboard focus (it drops to <body>),
  // so the button keeps focus and ignores clicks while the image is being made (WCAG 2.4.3).
  function busy(btn, on) {
    btn._busy = on;
    if (on) {
      btn.setAttribute("aria-busy", "true");
      btn.setAttribute("aria-disabled", "true");
      announce(dl.getAttribute("data-working"));
    } else {
      btn.removeAttribute("aria-busy");
      btn.removeAttribute("aria-disabled");
    }
  }

  function save(blob, name) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
  }

  dl.hidden = false;
  dl.addEventListener("click", function () {
    if (dl._busy) return;
    busy(dl, true);
    render().then(function (blob) {
      save(blob, dl.getAttribute("data-file"));
      announce(dl.getAttribute("data-done"));
    }).catch(function () {
      announce(dl.getAttribute("data-failed"));
      window.alert(dl.getAttribute("data-failed"));
    }).then(function () { busy(dl, false); });
  });

  if (!sh) return;
  sh.hidden = false;
  var url = sh.getAttribute("data-url") || location.href;
  var copyLink = function () {
    if (GV.copy) GV.copy(url, sh);
    announce(sh.getAttribute("data-copied"));
  };
  var canShareFiles = function (file) {
    try { return !!(navigator.canShare && navigator.share && navigator.canShare({ files: [file] })); } catch (e) { return false; }
  };
  // Phones: make the image while the finger is still on the button, so share() runs within the
  // click's user activation.
  if (navigator.canShare) {
    ["pointerdown", "focus"].forEach(function (ev) { sh.addEventListener(ev, function () { render().catch(function () {}); }, { once: true }); });
  }
  sh.addEventListener("click", function () {
    if (sh._busy) return;
    if (!navigator.canShare || !navigator.share) { copyLink(); return; }
    busy(sh, true);
    render().then(function (blob) {
      var file = new File([blob], sh.getAttribute("data-file"), { type: "image/png" });
      if (!canShareFiles(file)) { copyLink(); return; }
      return navigator.share({ files: [file], title: sh.getAttribute("data-title") || document.title, text: sh.getAttribute("data-text") || url })
        .catch(function (err) { if (!err || err.name !== "AbortError") copyLink(); });
    }).catch(copyLink).then(function () { busy(sh, false); });
  });
})();
