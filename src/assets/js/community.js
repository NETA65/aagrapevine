/* Community pages: What's New, Monthly Digest, Share Kit, Status, 404 (the /monthly/#report editor: report.js).
   Loaded (defer) before Alpine, so components register on "alpine:init".
   Everything here is a progressive enhancement: pages are fully readable
   without JavaScript. User-visible strings come from data-* attributes
   rendered by the templates (never hard-coded here). */
(function () {
  "use strict";
  var GV = window.GV || {};
  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";

  /* YYYY-MM-DD for a Date in Central time (matches the build-time grouping). */
  function ymd(d) {
    try {
      return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
    } catch (e) {
      return d.toISOString().slice(0, 10);
    }
  }
  function fill(tpl, n) { return String(tpl || "").replace("{n}", n); }
  // What's New: this device's record of its visits ("New since your last visit" — whats-new.njk)
  var SEEN_KEY = "gv-wn-seen";

  document.addEventListener("alpine:init", function () {
    var Alpine = window.Alpine;

    /* ---------------- What's New timeline ----------------
       Days: <li data-day="2026-09-23" data-counts='{"pdf":3}' data-total="5">
       Entries: <li data-kind="pdf" data-rank="0" data-rank-all="2">          */
    Alpine.data("whatsNew", function (opts) {
      opts = opts || {};
      var initialDays = opts.days || 10;
      return {
        filter: "",
        limit: initialDays,
        cap: opts.cap || 6,
        open: {},
        days: [],
        status: "",
        init: function () {
          var self = this;
          // counts/total = timeline ENTRIES (a magazine issue is one entry);
          // icounts/itotal = underlying ITEMS (what the chips and status report).
          var json = function (el, a) { try { return JSON.parse(el.getAttribute(a) || "{}"); } catch (e) { return {}; } };
          this.days = Array.prototype.map.call(this.$el.querySelectorAll("[data-day]"), function (el) {
            return {
              ymd: el.getAttribute("data-day"),
              counts: json(el, "data-counts"), total: Number(el.getAttribute("data-total")) || 0,
              icounts: json(el, "data-icounts"), itotal: Number(el.getAttribute("data-itotal")) || 0,
            };
          });
          // Shareable filtered view: /whats-new/?type=pdf
          var m = /[?&]type=([a-z]+)/.exec(location.search);
          if (m && this.days.some(function (d) { return d.counts[m[1]]; })) this.filter = m[1];
          this.updateStatus();
          this.watchBar();
          this.watchVisit();
        },
        /* "New since your last visit": the page's own script (whats-new.njk, right after the line) keeps this
           device's record of its visits — localStorage SEEN_KEY, { upto, last, base } — and shows the line and the
           "New for you" marks before the feed is drawn. Here: the visit goes on while the page stays open, so
           its time ("last") is also when the page is left or put in the background. Nothing is sent anywhere. */
        watchVisit: function () {
          var touch = function () {
            try {
              var r = JSON.parse(localStorage.getItem(SEEN_KEY));
              if (r && typeof r.last === "number") { r.last = Date.now(); localStorage.setItem(SEEN_KEY, JSON.stringify(r)); }
            } catch (e) { /* no storage: nothing is remembered */ }
          };
          window.addEventListener("pagehide", touch);
          document.addEventListener("visibilitychange", function () { if (document.hidden) touch(); });
        },
        /* The line's buttons. "Mark all as read" (forget false): this visit has seen them — the line and the marks
           go, and the next visit counts from this one. "Forget my last visit" (true): the record goes; the next
           visit is a first one again (nothing to compare with). Said to screen readers; the button that had focus
           is gone, so focus moves to the first day shown (never lost to <body>). */
        sinceDone: function (forget) {
          var box = document.getElementById("wn-since"), css = document.getElementById("wn-since-css");
          try {
            if (forget) localStorage.removeItem(SEEN_KEY);
            else {
              var r = JSON.parse(localStorage.getItem(SEEN_KEY));
              if (r && typeof r === "object") { r.base = null; localStorage.setItem(SEEN_KEY, JSON.stringify(r)); }
            }
          } catch (e) { /* no storage: the line goes all the same */ }
          if (css && css.parentNode) css.parentNode.removeChild(css);
          if (!box) return;
          box.hidden = true;
          this.status = box.getAttribute(forget ? "data-forgot" : "data-read") || "";
          var first = this.matchingDays()[0];
          var head = first && this.$root.querySelector('[data-day="' + first.ymd + '"] .cm-day-head');
          if (head) { head.setAttribute("tabindex", "-1"); head.focus(); }
        },
        /* The sticky filter bar's height while it covers the feed, as --wn-bar-h on <html>: html's
           scroll-padding-top adds it (community.css), so a link that gets keyboard focus — or a jump — never
           lands under the bar. Its chips may wrap onto a second row on a desktop, so it is measured, not
           guessed; 0 while it covers nothing: a window under 40rem tall (it scrolls away), the
           three-column layout (it is the left column), or larger text / relaxed spacing from 64rem
           (it stays in place: community.css). Measured again when its size changes, the window's, or
           a reading setting ("gvlv:prefs": the Aa panel, another tab) — that one may make it sticky
           or not at the same size. */
        watchBar: function () {
          var bar = this.$el.querySelector(".cm-chipbar"), feed = this.$el.querySelector(".cm-wn-feed");
          if (!bar || !feed) return;
          var html = document.documentElement;
          var size = function () {
            var b = bar.getBoundingClientRect(), f = feed.getBoundingClientRect();
            var covers = getComputedStyle(bar).position === "sticky" && b.height > 0 && b.left < f.right && b.right > f.left;
            html.style.setProperty("--wn-bar-h", covers ? Math.ceil(b.height) + "px" : "0px");
          };
          size();
          if (window.ResizeObserver) new ResizeObserver(size).observe(bar);
          window.addEventListener("resize", size);
          // (a frame later: the new data-text / data-spacing styles have applied)
          window.addEventListener("gvlv:prefs", function () { if (window.requestAnimationFrame) requestAnimationFrame(size); else size(); });
        },
        count: function (d) { return this.filter ? d.counts[this.filter] || 0 : d.total; },
        /* Day heading "7 updates": the day's ITEMS of the chosen type (a magazine issue
           counts its stories, like the chips and the status line), all items without a filter. */
        dayLabel: function (day) {
          var d = this.days.find(function (x) { return x.ymd === day; });
          var n = d ? (this.filter ? d.icounts[this.filter] || 0 : d.itotal) : 0;
          return fill(this.$root.getAttribute(n === 1 ? "data-day-one" : "data-day-many"), n);
        },
        matchingDays: function () { var self = this; return this.days.filter(function (d) { return self.count(d) > 0; }); },
        dayShown: function (day) {
          var list = this.matchingDays().slice(0, this.limit);
          for (var i = 0; i < list.length; i++) if (list[i].ymd === day) return true;
          return false;
        },
        entryShown: function (el) {
          var kind = el.getAttribute("data-kind");
          if (this.filter && kind !== this.filter) return false;
          var dayEl = el.closest("[data-day]");
          if (dayEl && this.open[dayEl.getAttribute("data-day")]) return true;
          return Number(el.getAttribute(this.filter ? "data-rank" : "data-rank-all")) < this.cap;
        },
        hiddenIn: function (day) {
          if (this.open[day]) return 0;
          var d = this.days.find(function (x) { return x.ymd === day; });
          return d ? Math.max(0, this.count(d) - this.cap) : 0;
        },
        moreLabel: function (day) { return fill(this.$root.getAttribute("data-more"), this.hiddenIn(day)); },
        /* The button hides itself once the day is open, so keyboard / screen-reader focus
           moves to the first entry it revealed (never lost to <body>). */
        openDay: function (day) {
          var self = this;
          var rankAttr = this.filter ? "data-rank" : "data-rank-all";
          this.open[day] = true;
          this.$nextTick(function () {
            var dayEl = self.$root.querySelector('[data-day="' + day + '"]');
            if (!dayEl) return;
            var first = Array.prototype.find.call(dayEl.querySelectorAll(".cm-entry"), function (el) {
              return (!self.filter || el.getAttribute("data-kind") === self.filter) && Number(el.getAttribute(rankAttr)) >= self.cap;
            });
            var target = first && first.querySelector(".cm-entry-link");
            if (!target && first) { target = first.querySelector("h3"); if (target) target.setAttribute("tabindex", "-1"); }
            if (!target) { target = dayEl.querySelector(".cm-day-head"); if (target) target.setAttribute("tabindex", "-1"); }
            if (target) target.focus();
          });
        },
        moreDays: function () { return this.matchingDays().length > this.limit; },
        showOlder: function () { this.limit += initialDays; },
        filteredTotal: function () {
          var f = this.filter;
          return this.days.reduce(function (a, d) { return a + (f ? d.icounts[f] || 0 : d.itotal); }, 0);
        },
        setFilter: function (k) {
          this.filter = k;
          this.limit = initialDays;
          this.updateStatus();
          try {
            var u = new URL(location.href);
            if (k) u.searchParams.set("type", k); else u.searchParams.delete("type");
            history.replaceState(null, "", u.toString());
          } catch (e) { /* old browser: filter still works */ }
        },
        updateStatus: function () { this.status = fill(this.$root.getAttribute("data-showing"), this.filteredTotal()); },
      };
    });

    /* ---------------- Monthly digest ----------------
       bi: one language or both in the texts — remembered as "gv-digest-bi", the same choice the monthly
       toolkit's "Send it as a message" uses (monthly.js mpMessage).
       stale: the page is last month's edition by now — its data-stale-after instant (midnight Central
       after the month it came out in) has passed: a copy built before the 1st (or a saved or offline one)
       says which edition it is and when the next one comes out. Checked now, every minute (a page left
       open over midnight), and when the page is shown again (a tab brought back to the front, or a page
       restored by the Back button). */
    Alpine.data("digestPage", function () {
      return {
        bi: false,
        more: false,   // phones: "More options" (e-mail, print, steps, previews) — always shown from 1024px
        stale: false,
        init: function () {
          var self = this;
          try { this.bi = localStorage.getItem("gv-digest-bi") === "1"; } catch (e) { /* ignore */ }
          this.$watch("bi", function (v) { try { localStorage.setItem("gv-digest-bi", v ? "1" : "0"); } catch (e) { /* ignore */ } });
          var after = Date.parse(this.$el.getAttribute("data-stale-after") || "");
          var check = function () { self.stale = !isNaN(after) && Date.now() >= after; };
          check();
          setInterval(check, 60000);
          document.addEventListener("visibilitychange", function () { if (!document.hidden) check(); });
          window.addEventListener("pageshow", function (e) { if (e.persisted) check(); });
        },
        src: function (kind) { return "#digest-" + kind + "-" + (this.bi ? "bi" : "one"); },
      };
    });

    /* ---------------- Share kit ---------------- */
    Alpine.data("sharePage", function (lang) {
      return {
        qrLang: lang || "en",
        posterLang: lang || "en",
        init: function () {
          window.addEventListener("afterprint", function () { document.documentElement.removeAttribute("data-print"); });
        },
        printVariant: function (which) {
          document.documentElement.setAttribute("data-print", which);
          // Let the attribute apply before the print dialog snapshots the page.
          setTimeout(function () { window.print(); }, 60);
        },
      };
    });
  });

  /* ---------------- enhancements (no Alpine needed) ---------------- */
  function enhance() {
    digestColumns();

    // "Today" / "Yesterday" badges on What's New day headings (computed in
    // the browser so a page built yesterday still reads correctly today).
    var wrap = document.querySelector("[data-today]");
    if (wrap) {
      var now = new Date();
      var today = ymd(now), p = today.split("-");
      // the calendar day before today, not "24 hours ago" (the days the clocks change have 23 or 25 hours)
      var yest = /^\d{4}-\d{2}-\d{2}$/.test(today) ? new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] - 1)).toISOString().slice(0, 10) : null;
      document.querySelectorAll("[data-rel-day]").forEach(function (el) {
        var d = el.getAttribute("data-rel-day");
        var label = d === today ? wrap.getAttribute("data-today") : d === yest ? wrap.getAttribute("data-yesterday") : "";
        if (label) el.textContent = label;
      });
    }

    // Copy the text of another element: <button data-copy-from="#id">
    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-copy-from]");
      if (!b) return;
      e.preventDefault();
      var src = document.querySelector(b.getAttribute("data-copy-from"));
      if (src && GV.copy) GV.copy("value" in src && src.tagName === "TEXTAREA" ? src.value : src.textContent, b);
    });

    // Download a QR <svg> as PNG: <button data-qr-png="#wrapper" data-filename="x.png">
    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-qr-png]");
      if (!b) return;
      e.preventDefault();
      var holder = document.querySelector(b.getAttribute("data-qr-png"));
      var svg = holder && holder.querySelector("svg");
      if (!svg) return;
      // Whole pixels per QR module, otherwise rows get hairline seams.
      var vb = (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) || 0;
      var size = vb ? vb * Math.max(1, Math.floor(1200 / vb)) : 1200;
      svgToPng(svg, size, b.getAttribute("data-filename") || "qr-code.png");
    });

    // 404: show the missing address and pre-fill the search box with words
    // from it ("/library/sponsorship-flyer.pdf" → "library sponsorship flyer").
    var nf = document.querySelector("[data-nf]");
    if (nf) {
      var base = (window.SITE && window.SITE.base) || "/";
      var path = location.pathname;
      try { path = decodeURIComponent(path); } catch (e) { /* malformed %-escape: use as-is */ }
      if (path.indexOf(base) === 0) path = path.slice(base.length);
      // A shared event's page (/events/<its card>/, src/pages/event-share.11ty.js) whose event has left the
      // events list since: on to the Events page — to that card, should it still be there.
      var ev = /^((?:es\/)?events\/)([a-z0-9][a-z0-9-]*)\/?$/.exec(path);
      if (ev) { location.replace(base + ev[1] + location.search + "#" + ev[2]); return; }
      var words = path.replace(/^es\//, "").replace(/\.[a-z0-9]{2,5}$/i, "")  // any file extension (.html, .php, .pdf …)
        .split(/[\/\-_.+]+/).filter(function (w) { return w && w.length > 2 && !/^(index|grapevine|es|en|www|\d+)$/i.test(w); });
      var q = words.slice(-4).join(" ");
      if (q) document.querySelectorAll("[data-nf-query]").forEach(function (i) { if (!i.value) i.value = q; });
      if (!/404\.html$/.test(location.pathname)) {
        document.querySelectorAll("[data-nf-path]").forEach(function (el) { el.textContent = location.pathname; });
      }
    }
  }

  /* Monthly digest, from 1280px: the newsletter's two newspaper columns (community.css .cm-dg-body) never
     end one with a heading whose first row is in the next. Chromium keeps a heading with what follows by
     itself (break-after: avoid). Safari ignores break-after / break-before: avoid inside CSS columns, and
     Firefox a forced column break too — but all three keep an unbreakable box whole (break-inside: avoid).
     So every section title and sub-heading gets an empty box just before it (.cm-dg-keep, aria-hidden), as
     tall as the run from the heading's top to the bottom of its first row (past an opening line and a
     sub-heading: "Writers…" · its line · "Area 65" · the first story) and pulled back up by as much (a
     negative margin; it carries the heading's own top margin): it takes no room, but a column can only hold
     it whole, so the heading goes on to the next column with its first row whenever they would not fit
     together — what Chromium does anyway, and as close as Chromium's two columns end. Likewise a list's last
     row and the line(s) under it ("+ 3 more — See all 8", "See all writers…", which Chromium keeps with the
     list by itself: break-before: avoid): a box before that row (an li, inside the list). The heights are
     measured on a copy of the sections laid out in one column of the columns' width (the same lines,
     nothing split) after each layout change (the fonts, the window's width, "Both languages", the text
     size), in the next frame, never inside the ResizeObserver's own callback. One column (phones, tablets,
     130 %+ text or relaxed spacing) and on paper: the boxes take no room (and print hides them). */
  function digestColumns() {
    var body = document.querySelector(".cm-dg-body");
    if (!body || !window.ResizeObserver || !window.requestAnimationFrame) return;
    var heads = [].slice.call(body.querySelectorAll(".cm-digest-group > h3, .cm-digest-group > h4"));
    if (!heads.length) return;
    function box(tag, parent, before) {
      var k = document.createElement(tag);
      k.className = "cm-dg-keep";
      k.setAttribute("aria-hidden", "true");
      parent.insertBefore(k, before);
      return k;
    }
    function firstRow(h) {
      for (var n = h.nextElementSibling; n; n = n.nextElementSibling) {
        if (n.classList.contains("cm-dg-keep")) continue;
        if (n.tagName === "UL" || n.tagName === "OL") return n.querySelector("li:not(.cm-dg-keep)");
        if (n.tagName !== "H3" && n.tagName !== "H4" && n.tagName !== "P") return n;
      }
      return null;
    }
    // a list's last row and the last of the lines right under the list
    function tail(p) {
      var rows = p.previousElementSibling.querySelectorAll(":scope > li:not(.cm-dg-keep)"), end = p;
      while (end.nextElementSibling && end.nextElementSibling.tagName === "P") end = end.nextElementSibling;
      return rows.length ? { row: rows[rows.length - 1], end: end } : null;
    }
    var TAILS = ".cm-digest-group > :is(ul, ol) + p";
    var keeps = heads.map(function (h) { return { k: box("div", h.parentNode, h), top: h }; });
    [].forEach.call(body.querySelectorAll(TAILS), function (p) {
      var t = tail(p);
      if (t) keeps.push({ k: box("li", t.row.parentNode, t.row), top: t.row });
    });
    function px(v) { return parseFloat(v) || 0; }
    function set(k, name, v) {
      if (k.style.getPropertyValue(name) === v) return;   // unchanged: no new layout, no new round
      if (v) k.style.setProperty(name, v); else k.style.removeProperty(name);
    }
    function fix() {
      var cs = getComputedStyle(body), n = parseInt(cs.columnCount, 10);
      var tall = keeps.map(function () { return 0; }), top = tall.slice();
      if (cs.display === "block" && n > 1) {
        // A copy of the sections in one column of the columns' width, out of sight beside the body (the body
        // itself is never switched to one column and back: Safari then put the intro and the pointer rows,
        // which span the card, in the wrong places). x-ignore: Alpine leaves the copy alone.
        var w = body.getBoundingClientRect().width - px(cs.borderLeftWidth) - px(cs.borderRightWidth) - px(cs.paddingLeft) - px(cs.paddingRight);
        var copy = document.createElement("div");
        copy.className = "cm-dg-body";
        copy.setAttribute("aria-hidden", "true");
        copy.setAttribute("x-ignore", "");
        copy.style.cssText = "position: absolute; left: 0; top: 0; visibility: hidden; pointer-events: none; display: block; columns: auto; " +
          "box-sizing: content-box; padding: 0; border: 0; width: " + (w - (n - 1) * px(cs.columnGap)) / n + "px";
        [].forEach.call(body.querySelectorAll(".cm-digest-group"), function (g) { copy.appendChild(g.cloneNode(true)); });
        [].forEach.call(copy.querySelectorAll("[id], img[onerror]"), function (e) { e.removeAttribute("id"); e.removeAttribute("onerror"); });
        body.parentNode.insertBefore(copy, body.nextSibling);
        // the copy's runs (each from its top to its end), in the same order as keeps
        var runs = [].map.call(copy.querySelectorAll(".cm-digest-group > h3, .cm-digest-group > h4"), function (t) { return [t, firstRow(t)]; });
        [].forEach.call(copy.querySelectorAll(TAILS), function (p) { var t = tail(p); if (t) runs.push([t.row, t.end]); });
        keeps.forEach(function (k, i) {
          var a = runs[i] && runs[i][0], b = runs[i] && runs[i][1];
          if (!b || !a.getClientRects().length || !b.getClientRects().length) return;   // hidden ("Both languages" off)
          // the run's end: its last element, or what sticks out of it — the padding that makes a link under a
          // list 24px tall (.tap-link): Safari will not end a column with a line whose link runs past the foot
          var end = b.getBoundingClientRect().bottom;
          [].forEach.call(b.querySelectorAll("a"), function (x) { end = Math.max(end, x.getBoundingClientRect().bottom); });
          // to 1/64px, rounded up (the browsers lay out in 1/64 or 1/60px): never short of the run, never a pixel more
          tall[i] = Math.ceil((end - a.getBoundingClientRect().top) * 64) / 64;
          top[i] = px(getComputedStyle(k.top).marginTop);
        });
        copy.remove();
      }
      keeps.forEach(function (k, i) {
        set(k.k, "--keep", tall[i] ? tall[i] + "px" : "");
        set(k.k, "--keep-mt", tall[i] ? top[i] + "px" : "");
      });
    }
    var queued = false;
    function queue() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () { queued = false; fix(); });
    }
    var ro = new ResizeObserver(queue);
    ro.observe(body);
    [].forEach.call(body.querySelectorAll(".cm-digest-group"), function (g) { ro.observe(g); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(queue);
  }

  function svgToPng(svg, size, filename) {
    var clone = svg.cloneNode(true);
    clone.setAttribute("width", size);
    clone.setAttribute("height", size);
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    var xml = new XMLSerializer().serializeToString(clone);
    var img = new Image();
    img.onload = function () {
      var c = document.createElement("canvas");
      c.width = c.height = size;
      var ctx = c.getContext("2d");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, size, size);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(img, 0, 0, size, size);
      c.toBlob(function (blob) {
        if (!blob) return;
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 800);
      }, "image/png");
    };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", enhance); else enhance();
})();
