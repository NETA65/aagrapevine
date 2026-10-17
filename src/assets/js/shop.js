/* Shop page (/shop/) + the home page's Book of the Month teaser.
   Loaded with `defer` after app.js and BEFORE Alpine, so the Alpine component below is registered
   in time (alpine:init). No dependencies besides Alpine (the countdown is plain JS).

   1. Offer countdown — any element with data-shop-offer data-ends="YYYY-MM-DD" (the last day of the
      offer, in the site's time zone). Inside it:
        [data-shop-days]   text redrawn from its templates: data-t-many="{n} days left",
                           data-t-tomorrow="Ends tomorrow", data-t-last="Last day!" — counting to its own
                           data-shop-ends="YYYY-MM-DD YYYY-MM-DD" when it has them (the first one not over yet:
                           the home teaser shows both books, whose offers can end on different days)
        [data-shop-live]   shown while the offer runs
        [data-shop-ended]  shown (hidden attribute removed) once the offer is over
      The build renders the same text for the build day, so without JavaScript the page still reads right
      (the site is rebuilt daily, and the sync drops an offer once it has ended).
   2. shopSubs — the subscription price switch (publication × region radio groups). Without JavaScript
      the switch stays hidden (x-cloak) and every publication's U.S. prices show. ?pub=lv preselects.
   3. shopCost — "What it would cost" (#group-cost, in "Subscribe your home group"): the magazine, format, term
      and number of copies → the total at the store's volume price, a month (and a year), and while AA
      Grapevine's notice of a price change is up, the price from its day. The page holds the plans as numbers
      (#shop-cost-data: eleventy/filters/shop.js shopCost); GV.shopQuote does the sums here, by the clock, so a
      page built — or saved for offline use — the day before a price change is right on the day. "Print an
      information sheet" prints #shop-sheet alone (html[data-shop-print]: shop.css) in English, Spanish or both.
      Nothing is kept or sent: the choices live in the page. Without JavaScript the card links the stores. */
(function () {
  "use strict";
  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";
  var GV = window.GV || (window.GV = {});

  function todayYmd() {
    try {
      return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
    } catch (e) {
      return new Date().toISOString().slice(0, 10);
    }
  }
  function dayDiff(a, b) {
    var pa = a.split("-").map(Number), pb = b.split("-").map(Number);
    return Math.round((Date.UTC(pb[0], pb[1] - 1, pb[2]) - Date.UTC(pa[0], pa[1] - 1, pa[2])) / 864e5);
  }

  function updateOffers() {
    var today = todayYmd();
    var offers = document.querySelectorAll("[data-shop-offer][data-ends]");
    for (var i = 0; i < offers.length; i++) {
      var el = offers[i];
      var ends = el.getAttribute("data-ends");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(ends)) continue;
      var n = dayDiff(today, ends);
      var ended = n < 0;
      el.classList.toggle("is-ended", ended);
      var live = el.querySelectorAll("[data-shop-live]");
      for (var j = 0; j < live.length; j++) live[j].hidden = ended;
      var gone = el.querySelectorAll("[data-shop-ended]");
      for (var k = 0; k < gone.length; k++) gone[k].hidden = !ended;
      if (ended) continue;
      var days = el.querySelectorAll("[data-shop-days]");
      for (var d = 0; d < days.length; d++) {
        var s = days[d];
        var m = n;
        var each = (s.getAttribute("data-shop-ends") || "").split(" ");
        for (var e = 0; e < each.length; e++) {
          if (!/^\d{4}-\d{2}-\d{2}$/.test(each[e])) continue;
          var left = dayDiff(today, each[e]);
          if (left >= 0 && left < m) m = left;
        }
        var txt = m === 0 ? s.getAttribute("data-t-last") : m === 1 ? s.getAttribute("data-t-tomorrow") : (s.getAttribute("data-t-many") || "").replace("{n}", m);
        if (txt && s.textContent !== txt) s.textContent = txt;
        s.classList.toggle("is-urgent", m <= 3);
      }
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", updateOffers);
  else updateOffers();
  // A page left open past midnight (or brought back from the background) catches up.
  setInterval(updateOffers, 60 * 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) updateOffers(); });

  /* ---------------- 3. What it would cost ---------------- */
  var MAX_COPIES = 999;
  function round2(n) { return Math.round(n * 100) / 100; }
  function at(iso) { var t = Date.parse(iso || ""); return isNaN(t) ? null : t; }
  // A plan's state at `now` (ms): from an announced change's day on (`after`), else the one the page was built with.
  function stateAt(plan, now) {
    var t = plan.after ? at(plan.after.at) : null;
    return t !== null && now >= t ? plan.after : plan.now;
  }
  // The store's volume tier for n copies ({ min, max — null: "or more" —, price }), or null.
  function tierFor(vol, n) {
    for (var i = 0; vol && i < vol.length; i++) {
      if (n >= vol[i].min && (!vol[i].max || n <= vol[i].max)) return vol[i];
    }
    return null;
  }
  // Does a window { from, until } (ISO instants, either may be empty) hold `now`?
  function inWindow(w, now) {
    if (!w) return false;
    var f = at(w.from), u = at(w.until);
    return (f === null || now >= f) && (u === null || now < u);
  }
  // What of the plans the clock decides at `now` — each one's state (stateAt) and its two windows (next, none): the
  // only things of a quote that move with the clock. Two instants with the same key give the same quotes.
  function clockKey(plans, now) {
    var k = "";
    for (var i = 0; i < plans.length; i++) {
      var p = plans[i];
      k += (stateAt(p, now) === p.after ? "a" : "n") + (inWindow(p.next, now) ? "x" : "-") + (inWindow(p.none, now) ? "o" : "-");
    }
    return k;
  }

  /** What `copies` copies of one plan (shopCost's plans[]) cost at `now` (ms) → { copies (1–999), months, unit (the
   *  price of one copy: the volume price when the store lists one for that many), tier, note ("vol": a volume price ·
   *  "novol": none listed for this plan or this many · "later": the price AA Grapevine announced stands in for the
   *  store's, whose volume prices are the store's to say · ""), total, perMonth, perYear, since (the change's dates
   *  while its announced price stands in), next ({ price, total, vol, date } — the announced price, while the notice
   *  is up and its day still ahead), none (the notice's dates: it names no price for this plan) }. */
  function quote(plan, copies, now) {
    var n = Math.floor(Number(copies));
    n = n >= 1 ? Math.min(n, MAX_COPIES) : 1;
    var st = stateAt(plan, now);
    var tier = n > 1 ? tierFor(st.vol, n) : null;
    var unit = tier ? tier.price : st.price;
    var total = round2(unit * n);
    var nx = inWindow(plan.next, now) ? plan.next : null;
    return {
      copies: n,
      months: plan.months,
      unit: unit,
      tier: tier,
      note: tier ? "vol" : n < 2 ? "" : plan.hasVol && !st.vol ? "later" : "novol",
      total: total,
      perMonth: round2(total / plan.months),
      perYear: round2(total * 12 / plan.months),
      since: st.subst ? st.date : null,
      next: nx ? { price: nx.price, total: round2(nx.price * n), vol: plan.hasVol && n > 1, date: nx.date } : null,
      none: inWindow(plan.none, now) ? plan.none.date : null,
    };
  }
  GV.shopQuote = quote;

  function money(v, locale) {
    try {
      return new Intl.NumberFormat(locale || "en-US", { style: "currency", currency: "USD" }).format(v);
    } catch (e) {
      return "$" + Number(v).toFixed(2);
    }
  }
  function fill(tpl, vars) {
    return String(tpl || "").replace(/\{(\w+)\}/g, function (m, k) { return vars[k] !== undefined && vars[k] !== null ? vars[k] : m; });
  }

  /** A quote in words, in one language L ("en" | "es"; s: shopCost's s[L]) — the calculator's result and each
   *  language's part of the information sheet. */
  function words(q, plan, s, L) {
    var m = function (v) { return money(v, s.locale); };
    var term = s.term[plan.months] || "";
    var copies = q.copies === 1 ? s.copies_one : fill(s.copies_n, { n: q.copies });
    var range = q.tier ? fill(q.tier.max ? s.range : s.range_plus, { a: q.tier.min, b: q.tier.max }) : "";
    var note = q.note === "vol" ? fill(s.note_vol, { range: range }) : q.note ? s["note_" + q.note] : "";
    var next = "";
    if (q.next) {
      next = q.copies === 1 ? fill(s.next_one, { date: q.next.date[L], price: m(q.next.price) })
        : fill(s.next_many, { date: q.next.date[L], price: m(q.next.price), total: m(q.next.total), copies: copies });
      if (q.next.vol) next += " " + s.next_vol;
    }
    return {
      mag: s.mag[plan.pub],
      plan: s.type[plan.type] + " · " + term,
      desc: s.desc[plan.pub + "." + plan.type] || "",
      count: String(q.copies),
      copies: copies,
      total: m(q.total),
      totalFor: plan.months === 1 ? s.each_month : fill(s.for_term, { term: term }),
      perMonth: plan.months > 1 ? fill(s.per_month, { amount: m(q.perMonth) }) : "",
      perYear: plan.months !== 12 ? fill(s.per_year, { amount: m(q.perYear) }) : "",
      unit: q.copies > 1 ? fill(s.unit, { price: m(q.unit) }) + (note ? " (" + note + ")" : "") : "",
      unitAmt: m(q.unit) + (note ? " (" + note + ")" : ""),
      since: q.since ? fill(s.since, { date: q.since[L] }) : "",
      next: next,
      none: q.none ? fill(s.next_none, { date: q.none[L] }) : "",
      store: fill(s.store, { store: plan.pub === "lv" ? "aalavina.org" : "aagrapevine.org" }),
      order: fill(s.order, { store: String(plan.url || "").replace(/^https?:\/\/(www\.)?/, "") }),
    };
  }
  GV.shopQuoteWords = words;

  document.addEventListener("alpine:init", function () {
    /* x-data="shopSubs({ first: 'gv', avail: { gv: ['us','ca','intl'], lv: [...] } })" */
    window.Alpine.data("shopSubs", function (cfg) {
      cfg = cfg || {};
      var avail = cfg.avail || {};
      return {
        pub: cfg.first || "gv",
        region: "us",
        init: function () {
          try {
            var want = new URLSearchParams(window.location.search).get("pub");
            if (want && avail[want]) this.pub = want;
          } catch (e) {}
          this.fixRegion();
          var self = this;
          this.$watch("pub", function () { self.fixRegion(); });
        },
        has: function (r) { return (avail[this.pub] || []).indexOf(r) !== -1; },
        fixRegion: function () {
          var list = avail[this.pub] || [];
          if (list.length && list.indexOf(this.region) === -1) this.region = list.indexOf("us") !== -1 ? "us" : list[0];
        },
        show: function (p, r) { return this.pub === p && this.region === r; },
      };
    });

    /* x-data="shopCost('en')" — the calculator and its information sheet (#group-cost; the plans: #shop-cost-data).
       pub / type / months / copies: the choice (the page language's magazine, print, 1 year, 1 copy to start;
       ?pub=lv preselects, as for the price switch); sheet: the sheet's language ("en" | "es" | "both"). */
    window.Alpine.data("shopCost", function (lang) {
      var cfg = {};
      try { cfg = JSON.parse((document.getElementById("shop-cost-data") || {}).textContent || "{}") || {}; } catch (e) { cfg = {}; }
      var plans = cfg.plans || [], S = cfg.s || {};
      var L0 = lang === "es" ? "es" : "en";
      var find = function (pub, type, months) {
        for (var i = 0; i < plans.length; i++) {
          var p = plans[i];
          if (p.pub === pub && (type === undefined || p.type === type) && (months === undefined || p.months === months)) return p;
        }
        return null;
      };
      return {
        lang: L0,
        pub: (cfg.pubs || [])[0] || "gv",
        type: "print",
        months: 12,
        copies: 1,
        sheet: L0,
        now: Date.now(),
        init: function () {
          var self = this;
          try {
            var want = new URLSearchParams(window.location.search).get("pub");
            if (want && find(want)) this.pub = want;
          } catch (e) {}
          this.fix();
          this.$watch("pub", function () { self.fix(); });
          this.$watch("type", function () { self.fix(); });
          // a page left open past midnight (the day of a price change) catches up — `now` moves only when that
          // changes a quote (clockKey): every change of it redraws the sum, and the sum is a live region
          // (aria-live), so a screen reader would say the same total again every minute
          var tick = function () {
            var t = Date.now();
            if (clockKey(plans, t) !== clockKey(plans, self.now)) self.now = t;
          };
          setInterval(tick, 60 * 1000);
          document.addEventListener("visibilitychange", function () { if (!document.hidden) tick(); });
        },
        hasType: function (t) { return !!find(this.pub, t); },
        hasTerm: function (m) { return !!find(this.pub, this.type, m); },
        // a format or a term this magazine does not sell (La Viña's print has no monthly plan): the nearest one it does
        fix: function () {
          var i;
          if (!find(this.pub, this.type)) {
            for (i = 0; i < (cfg.types || []).length; i++) if (find(this.pub, cfg.types[i])) { this.type = cfg.types[i]; break; }
          }
          var m = Number(this.months);
          if (!find(this.pub, this.type, m)) {
            var p = find(this.pub, this.type, 12) || find(this.pub, this.type);
            if (p) this.months = p.months;
          } else if (m !== this.months) this.months = m;
        },
        // the number field once it is left: a whole number of copies, 1 to 999 (the sums already read it so)
        tidy: function () {
          var n = Math.floor(Number(this.copies));
          this.copies = n >= 1 ? Math.min(n, MAX_COPIES) : 1;
        },
        plan: function () { return find(this.pub, this.type, Number(this.months)); },
        w: function (L) {
          var p = this.plan(), s = S[L];
          return p && s ? words(quote(p, this.copies, this.now), p, s, L) : {};
        },
        // "Volume prices from 2 copies" under the number, for a plan the store lists them for
        volHint: function () {
          var p = this.plan(), s = S[this.lang], st = p && stateAt(p, this.now);
          return st && st.vol && st.vol.length && s ? fill(s.vol_hint, { n: st.vol[0].min }) : "";
        },
        // the information sheet alone, on paper or as a PDF (html[data-shop-print]: shop.css; afterwards the page
        // is as it was — Chrome and Firefox say "afterprint", Safari's print() returns once it is done)
        print: function () {
          var root = document.documentElement, was = document.title, p = this.plan(), s = S[this.sheet === "es" ? "es" : "en"];
          root.setAttribute("data-shop-print", this.sheet);
          if (p && s) document.title = s.sheet_title + " — " + s.mag[p.pub];   // the file name "Save as PDF" suggests
          var done = function () { root.removeAttribute("data-shop-print"); document.title = was; window.removeEventListener("afterprint", done); };
          window.addEventListener("afterprint", done);
          this.$nextTick(function () { setTimeout(function () { window.print(); if (!("onafterprint" in window)) done(); }, 60); });
        },
      };
    });
  });
})();
