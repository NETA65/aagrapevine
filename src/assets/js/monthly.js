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
     the poster (round 26b), so a busy month's blocks also take the room another column leaves: a block
     that may sit in another column (data-mp-move="b a", the build's place first; the columns are
     [data-mp-slot]) is tried in each, in its place in the reading order (data-mp-order), and the
     arrangement whose type is largest wins (the build's own unless another is larger). A very busy
     month whose type would still be under 18px also tries each arrangement with its dates in one more
     column (.mp-dates--cols: two in a column, four in a band across the poster). Binary search,
     ~8 layouts an arrangement (one that cannot beat the best so far is dropped after one), done on a
     hidden copy one step per task (the page never freezes, the visible poster changes once) and only
     for the full-size poster of a month page (the hub shows the months in miniature — macros/monthly.njk
     posterMini, never fitted). The PNG and the print use this DOM; once it is done the poster carries
     data-mp-fit (the share pictures wait for it: scripts/ops/poster_share.py) and fitDone resolves (the
     PNG waits for it). */
  var BLOCKS = ".mp-b, .mp-foot, .mp-head, .mp-row, .mp-col, .mp-body, .mp-board, .mp-cover, .mp-strip, .mp-page, .mp-main, .mp-stub, .mp-side, .mp-content, .mp-top, .mp-feature, .mp-rail, .mp-band";
  var MIN_PX = 15, MAX_PX = 28;            // the type's range (poster px; 15px prints at 7.5 pt on Letter)
  var COLS_BELOW_PX = 18;                  // the dates in two columns only when one column leaves the type under this
  var toArray = function (list) { return Array.prototype.slice.call(list); };
  // Layout boxes in poster px (offset* ignore the scale and the tilted cork cards' rotation).
  function box(el, p) {
    var t = 0, l = 0, e = el;
    while (e && e !== p) { t += e.offsetTop; l += e.offsetLeft; e = e.offsetParent; }
    return { t: t, b: t + el.offsetHeight, r: l + el.offsetWidth };
  }
  function overflowing(p) {
    var blocks = p.querySelectorAll(BLOCKS);
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i], par = b.parentElement, bb = box(b, p);
      // the parent's content box (inside its padding)
      var pad = parseFloat(getComputedStyle(par).paddingBottom) || 0;
      var limit = par === p ? p.clientHeight - pad : box(par, p).t + par.clientTop + par.clientHeight - pad;
      if (bb.b > limit + 2 || bb.r > p.clientWidth + 2) return true;
    }
    return false;
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
  // Every arrangement of the movable blocks (each in one of its columns), the build's own first; at most 24 —
  // then the same with the dates in one more column ({ slots, cols }).
  function arrangements(root, movers) {
    var all = [[]];
    movers.forEach(function (m) {
      var opts = (m.getAttribute("data-mp-move") || "").split(/\s+/).filter(Boolean), next = [];
      all.forEach(function (a) { opts.forEach(function (o) { if (next.length < 24) next.push(a.concat([o])); }); });
      all = next;
    });
    var one = all.map(function (s) { return { slots: s, cols: false }; });
    return one.concat(root.querySelector(".mp-dates .mp-dlist") ? all.map(function (s) { return { slots: s, cols: true }; }) : []);
  }
  function arrange(root, movers, combo) {
    movers.forEach(function (m, i) {
      var slot = root.querySelector('[data-mp-slot="' + combo.slots[i] + '"]');
      if (slot) place(slot, m);
    });
    var d = root.querySelector(".mp-dates");
    if (d) d.classList.toggle("mp-dates--cols", !!combo.cols);
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
    var combos = arrangements(c, cm), ci = -1, best = -1, bestCombo = combos[0], lo = 0, hi = 0, searching = false;
    var fits = function (k) { c.style.fontSize = k / 4 + "px"; return !overflowing(c); };
    (function step() {
      if (searching) {
        if (hi - lo > 1) {
          var mid = (lo + hi) >> 1;
          if (fits(mid)) lo = mid; else hi = mid;
        } else {
          searching = false;
          // (lo below minK: nothing fits even at the smallest type — another arrangement may still)
          if (lo > best) { best = lo; bestCombo = combos[ci]; }
        }
      } else if (++ci < combos.length) {
        // (the dates in two columns: only for a month that needs them — no layout spent otherwise)
        if (combos[ci].cols && best >= COLS_BELOW_PX * 4) { setTimeout(step, 0); return; }
        arrange(c, cm, combos[ci]);
        if (best < 0) {
          // the build's arrangement: from the type the stylesheet gives it (the month's density)
          lo = minK - 1; hi = topK + 1; searching = true;
          if (Math.min(base, topK) >= minK) { if (fits(Math.min(base, topK))) lo = Math.min(base, topK); else hi = Math.min(base, topK); }
        } else if (best < topK && fits(best + 1)) {
          // another: only when it holds the next step up (else it is dropped after this one layout)
          lo = best + 1; hi = topK + 1; searching = true;
        }
      } else {
        holder.remove();
        arrange(p, pm, bestCombo);
        p.style.fontSize = Math.max(best, minK) / 4 + "px";
        p.setAttribute("data-mp-fit", "");
        if (done) done();
        return;
      }
      setTimeout(step, 0); // one layout per task
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
