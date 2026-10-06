// Shop filters (owned by the Shop page, /shop/; also used by the home page's Book of the Month teaser).
// Auto-loaded by eleventy.config.js. They read db.shop (data/site/shop.json, docs/DATA_SCHEMA.md → "shop.json")
// and never invent a price, percent or date: everything shown comes from the synced store data, so the
// Shop page stays the ONE canonical home for these numbers (other pages only show a compact teaser).
//
//   shopBotm(shop, lang)      → Book of the Month views, page-language publication first
//   shopSubs(shop, lang)      → subscription comparison: publications → regions → plan types → terms
//   shopBulk(shop, lang)      → bulk-book discount rows (tiers with a discount) + note + source
//   shopSpecialty(shop, lang) → specialty items: one card per kind (cards · planner · calendar · holiday), the
//                               page language's store first, the other store's item of that kind as `also`
//   shopFromMonthly(shop)     → lowest monthly price in the U.S. stores (for "Subscriptions from $2.99/month"), or null
//   shopMoney(n, lang)        → "$11.99" (USD, the stores' currency)
//   shopPriceChanges(shop, lang) → the price changes AA Grapevine announced (shop.json price_changes): the
//                               notices' views, each with the window it shows in (shopWindow)
// (and, for the other filter files: shopWindow, shopPriceChangeIn, shopPlanPrice, shopNextChange, botmPriceState,
//  dayLabel)
//
// Announced price changes (config/site.yml price_changes → build_data → shop.json): from the day a change was
// announced the pages say what changes; from the day it takes effect an affected 1-year plan shows its new price
// while the store data still has the old one (plans[].change.stale), and a Book of the Month price read before
// that day — or after it, but still the old one (botm[].price_stale) — is not shown. A page shows BOTH states
// around such a day, each with its window (shopWindow → data-gv-from / data-gv-expire: app.js GV.expire, applied
// before the first paint by base.njk), so a page built — or saved for offline use — the day before is right on
// the day; without JavaScript the state at build time shows. The build's clock is monthly.js nowDate (MONTHLY_NOW
// moves it for a preview build).

// (monthly.js imports this file too: the cycle is safe, both only call each other's functions.)
import { nowDate } from "./monthly.js";
// the site's time zone: config/site.yml site.timezone (America/Chicago)
import { TZ } from "../../eleventy.config.js";

const LOCALES = { en: "en-US", es: "es-US" };
const MAG = { gv: "Grapevine", lv: "La Viña" };
// The language each store writes its own texts in (plan-type descriptions, book titles).
const STORE_LANG = { gv: "en", lv: "es" };
const TYPE_ORDER = ["print", "digital", "complete", "other"];
const REGION_ORDER = ["us", "ca", "intl"];

const round2 = (n) => Math.round(n * 100) / 100;

function pubOrder(lang) {
  return lang === "es" ? ["lv", "gv"] : ["gv", "lv"];
}

export function todayYmd(now = new Date()) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

// Whole days from a to b (both YYYY-MM-DD, calendar dates).
function dayDiff(a, b) {
  const pa = String(a).slice(0, 10).split("-").map(Number);
  const pb = String(b).slice(0, 10).split("-").map(Number);
  if (pa.length < 3 || pb.length < 3 || pa.some(isNaN) || pb.some(isNaN)) return null;
  return Math.round((Date.UTC(pb[0], pb[1] - 1, pb[2]) - Date.UTC(pa[0], pa[1] - 1, pa[2])) / 864e5);
}

export function money(n, lang = "en", currency = "USD") {
  const v = Number(n);
  if (n === null || n === undefined || n === "" || !isFinite(v)) return "";
  try {
    return new Intl.NumberFormat(LOCALES[lang] || "en-US", { style: "currency", currency: currency || "USD" }).format(v);
  } catch (e) {
    return "$" + v.toFixed(2);
  }
}

// "October 14" / "14 de octubre" (a calendar date, so formatted in UTC: no time-zone shift).
function dayMonth(ymd, lang) {
  if (!ymd || dayDiff(ymd, ymd) === null) return "";
  const p = String(ymd).slice(0, 10).split("-").map(Number);
  try {
    return new Intl.DateTimeFormat(LOCALES[lang] || "en-US", { month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(p[0], p[1] - 1, p[2])));
  } catch (e) {
    return String(ymd);
  }
}

function i18nField(item, field, lang) {
  const tr = item && item.i18n && item.i18n[field];
  return (tr && tr[lang]) || "";
}

/* ---------------- Announced price changes: windows and dates ---------------- */
const INSTANT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?(?:Z|[+-]\d{2}:\d{2})$/;
const msOf = (now) => (now instanceof Date ? now.getTime() : Number(now));

/** When an element shows: from `from` until `until` (ISO instants, either may be empty) → the attributes it still
 *  needs at `now` — { from (only while it is still ahead), until, hidden (not started yet) } — or null once `until`
 *  has passed (the element is not written at all). The template writes them with ui.when (macros/ui.njk). */
export function shopWindow(from, until, now = nowDate()) {
  const t = msOf(now);
  const f = INSTANT.test(String(from || "")) ? String(from) : "";
  const u = INSTANT.test(String(until || "")) ? String(until) : "";
  if (u && Date.parse(u) <= t) return null;
  const ahead = !!f && Date.parse(f) > t;
  return { from: ahead ? f : "", until: u, hidden: ahead };
}

/** The changes by key (shop.json price_changes), with only well-formed moments. */
function changeMap(shop) {
  const m = new Map();
  for (const c of (shop && Array.isArray(shop.price_changes) ? shop.price_changes : [])) {
    if (c && c.key && c.at && INSTANT.test(String(c.at.effective || ""))) m.set(c.key, c);
  }
  return m;
}
const passed = (iso, now) => INSTANT.test(String(iso || "")) && Date.parse(iso) <= msOf(now);

/** A calendar day in words: "January 1, 2027" / "1 de enero de 2027" (short: "Jan 1, 2027" / "1 de enero de
 *  2027" — Spanish keeps the month's name). */
export function dayLabel(ymd, lang, short = false) {
  if (!ymd || dayDiff(ymd, ymd) === null) return "";
  const p = String(ymd).slice(0, 10).split("-").map(Number);
  const opts = { month: short && lang !== "es" ? "short" : "long", day: "numeric", year: "numeric", timeZone: "UTC" };
  try {
    return new Intl.DateTimeFormat(LOCALES[lang] || "en-US", opts).format(new Date(Date.UTC(p[0], p[1] - 1, p[2])));
  } catch (e) {
    return String(ymd);
  }
}

/** A Book of the Month offer and the announced book price changes (books_more): { stale: its prices were read
 *  before a change that is now in effect — or on or after its day but still at the regular price read before it
 *  (b.price_stale: build_data, the store's page not updated yet) — so they are not shown, soon: the next change,
 *  when one is still ahead (its prices go stale on that day) }. The store's prices of a read made on or after the
 *  day are shown once they are new (or the book is: a new one starts on the 15th). */
export function botmPriceState(b, shop, now = nowDate()) {
  const books = [...changeMap(shop).values()].filter((c) => Number(c.books_more) > 0)
    .sort((x, y) => String(x.effective).localeCompare(String(y.effective)));
  const done = books.filter((c) => passed(c.at.effective, now));
  const last = done[done.length - 1] || null;
  const read = /^\d{4}-\d{2}-\d{2}$/.test(String(b && b.read || "")) ? b.read : "";
  return {
    stale: !!last && (!read || read < last.effective || !!(b && b.price_stale)),
    last,
    soon: books.find((c) => !passed(c.at.effective, now)) || null,
  };
}

/* ---------------- Book of the Month ---------------- */
function botmView(b, lang, today, shop, t, now) {
  const pub = b.pub === "lv" ? "lv" : "gv";
  const itemLang = b.lang || STORE_LANG[pub];
  const machine = Array.isArray(b.machine) ? b.machine : [];
  // The book is sold under its own title: that is the main title; the page-language title is a subtitle.
  const title = b.title || i18nField(b, "title", itemLang) || i18nField(b, "title", lang);
  const trTitle = lang !== itemLang ? i18nField(b, "title", lang) : "";
  const subtitle = trTitle && trTitle.trim().toLowerCase() !== String(title).trim().toLowerCase() ? trTitle : "";
  const trBlurb = i18nField(b, "blurb", lang);
  const blurb = trBlurb || b.blurb || "";
  const blurbLang = trBlurb ? lang : itemLang;
  const price = Number(b.price);
  const sale = Number(b.sale_price);
  const readPrices = isFinite(price) && price > 0 && isFinite(sale) && sale > 0 && sale < price;
  // An announced book price change (botmPriceState): prices read before it took effect are not shown — no
  // "you save" sums on an old price —, a note says the store has the current price; one still ahead gets its
  // line ("$2.00 more from …", from the day it was announced) and, from its day, the same note in place of
  // the prices (pcSwap).
  const pc = botmPriceState(b, shop, now);
  const hasPrices = readPrices && !pc.stale;
  const staleText = (c) => t("shop.pc_botm_after", lang, { date: dayLabel(c.effective, lang) });
  const days = b.ends ? dayDiff(today, b.ends) : null;
  return {
    id: b.id || "botm:" + pub,
    pub,
    isLv: pub === "lv",
    mag: MAG[pub],
    itemLang,
    title,
    subtitle,
    subtitleMachine: !!subtitle && machine.includes(lang),
    blurb,
    blurbLang,
    blurbMachine: blurbLang !== itemLang && machine.includes(lang),
    image: b.image || "",
    url: b.url || b.page_url || "",
    pageUrl: b.page_url || "",
    pct: Number(b.discount_pct) || (readPrices ? Math.round((1 - sale / price) * 100) : 0),
    hasPrices,
    price: hasPrices ? money(price, lang, b.currency) : "",
    sale: hasPrices ? money(sale, lang, b.currency) : "",
    save: hasPrices ? money(round2(price - sale), lang, b.currency) : "",
    saleNum: hasPrices ? sale : null,
    pcStale: readPrices && pc.stale ? staleText(pc.last) : "",
    pcBefore: pc.soon && shopWindow(pc.soon.at.announced, pc.soon.at.effective, now)
      ? { text: t("shop.pc_botm_before", lang, { date: dayLabel(pc.soon.effective, lang), amount: money(pc.soon.books_more, lang) }),
          win: shopWindow(pc.soon.at.announced, pc.soon.at.effective, now) }
      : null,
    pcSwap: hasPrices && pc.soon ? { at: pc.soon.at.effective, text: staleText(pc.soon) } : null,
    ends: b.ends || "",
    endsLabel: b.ends ? dayMonth(b.ends, lang) : "",
    starts: b.starts || "",
    startsLabel: b.starts ? dayMonth(b.starts, lang) : "",
    monthLabel: i18nField(b, "month_label", lang) || b.month_label || "",
    days,
    ended: days !== null && days < 0,
  };
}

export function shopBotm(shop, lang = "en", today = "", t = (k) => k, now = nowDate()) {
  const list = (shop && Array.isArray(shop.botm) ? shop.botm : []).filter((b) => b && (b.url || b.page_url));
  const order = pubOrder(lang);
  const day = today || todayYmd(now);
  return list
    .map((b) => botmView(b, lang, day, shop, t, now))
    .filter((v) => !v.ended)
    .sort((a, b) => order.indexOf(a.pub) - order.indexOf(b.pub));
}

/* ---------------- Subscriptions ---------------- */
function termKey(m) {
  if (m === 1) return { key: "shop.term_month" };
  if (m && m % 12 === 0) return m === 12 ? { key: "shop.term_year" } : { key: "shop.term_years", vars: { n: m / 12 } };
  if (m) return { key: "shop.term_months", vars: { n: m } };
  return null;
}

/* What a plan shows in one state of an announced change (plans[].change: build_data marks each 1-year plan a change
   affects, `stale` while the store data still has the old price):
     "now"    at build time — its store price; once the change's day has come and the store data is stale, the
              announced price instead;
     "after"  from the change's day on (the page switches to it in the browser, app.js GV.expire) — the announced
              price while the store data is stale.
   → { price, subst (the announced price stands in for the store's), note: { text, win, tone } | null — "From Jan 1,
   2027: $39.00" before the day (from the day it was announced), "New price since Jan 1, 2027" after it: for good
   while the announced price stands in, else until the notice ends }. */
function planState(p, changes, state, lang, t, now) {
  const price = Number(p.price);
  const ch = p.change && changes.get(p.change.key);
  const newPrice = ch ? Number(p.change.new) : NaN;
  if (!ch || !(newPrice > 0)) return { price, subst: false, note: null };
  const isPassed = passed(ch.at.effective, now);
  const subst = !!p.change.stale && (state === "after" || isPassed);
  let note = null;
  if (state === "now" && !isPassed) {
    const win = shopWindow(ch.at.announced, ch.at.effective, now);
    if (win && round2(newPrice) !== round2(price)) {
      note = { text: t("shop.pc_from", lang, { date: dayLabel(ch.effective, lang, true), price: money(newPrice, lang, p.currency) }), win, tone: "soon" };
    }
  } else {
    const win = subst ? { from: "", until: "", hidden: false } : shopWindow("", ch.at.notice_end, now);
    if (win) note = { text: t("shop.pc_new_since", lang, { date: dayLabel(ch.effective, lang, true) }), win, tone: "new" };
  }
  return { price: subst ? newPrice : price, subst, note, change: ch };
}

/** The price a plan shows in a state of its announced change ("now", or "after" — from the next change's day on):
 *  for the pages that quote one price (the GV/LV report). */
export function shopPlanPrice(p, shop, state = "now", now = nowDate()) {
  return planState(p, changeMap(shop), state, "en", (k) => k, now).price;
}

/** The next announced change whose day is still ahead at `now` (shop.json price_changes), or null. */
export function shopNextChange(shop, now = nowDate()) {
  return [...changeMap(shop).values()].filter((c) => !passed(c.at.effective, now))
    .sort((a, b) => String(a.at.effective).localeCompare(String(b.at.effective)))[0] || null;
}

/* One plan type's terms, volume table and lowest monthly rate in one state (planState). A saving set against an
   announced price that stands in for the store's would compare it with prices the store may change the same day,
   and that plan's volume prices are the ones read with its old price: both are left out (a note under the table
   sends readers to the store for them — and claims nothing: an announcement names no volume prices). */
function typeState(plans, lang, t, changes, now, state) {
  const cur = plans[0].currency || "USD";
  const sorted = plans.slice().sort((a, b) => (a.term_months || 999) - (b.term_months || 999));
  const st = new Map(sorted.map((p) => [p, planState(p, changes, state, lang, t, now)]));
  const priceOf = (p) => st.get(p).price;
  const withMonths = sorted.filter((p) => p.term_months && priceOf(p) > 0);
  // Baseline for "save": the shortest term's price per month (monthly plans, or the 1-year plan for print).
  const base = withMonths[0] || null;
  const baseRate = base ? priceOf(base) / base.term_months : null;
  let best = null;
  if (withMonths.length > 1) {
    for (const p of withMonths) if (!best || priceOf(p) / p.term_months < priceOf(best) / best.term_months - 1e-9) best = p;
  }
  const terms = sorted.map((p) => {
    const s = st.get(p);
    const m = p.term_months || null;
    const price = s.price;
    const tk = termKey(m);
    const perMonth = m && m > 1 && price > 0 ? price / m : null;
    let save = null;
    if (base && m && p !== base && baseRate && !s.subst && !st.get(base).subst) {
      const v = round2(baseRate * m - price);
      const key = base.term_months === 1 ? "shop.save_vs_monthly" : base.term_months === 12 ? "shop.save_vs_yearly" : "shop.save_plain";
      if (v >= 0.5) save = t(key, lang, { amount: money(v, lang, cur) });
    }
    return {
      months: m,
      label: tk ? t(tk.key, lang, tk.vars) : p.title || "",
      price: money(price, lang, cur),
      monthly: m === 1,
      perMonth: perMonth ? money(round2(perMonth), lang, cur) : "",
      save,
      best: !!best && p === best,
      note: s.note,
      url: p.url || "",
      sku: p.sku || "",
      title: p.title || "",
    };
  });
  // Group / volume pricing (print): rows = quantity tiers, columns = terms.
  let volume = null;
  const hasVol = (p) => Array.isArray(p.volume) && p.volume.length;
  const volPlans = sorted.filter((p) => hasVol(p) && !st.get(p).subst);
  const stoodIn = sorted.find((p) => hasVol(p) && st.get(p).subst);
  if (volPlans.length || stoodIn) {
    const rowsByKey = new Map();
    volPlans.forEach((p, col) => {
      for (const v of p.volume) {
        const k = `${v.min}-${v.max}`;
        if (!rowsByKey.has(k)) rowsByKey.set(k, { min: v.min, max: v.max, prices: new Array(volPlans.length).fill("") });
        rowsByKey.get(k).prices[col] = money(v.price, lang, cur);
      }
    });
    const rows = [...rowsByKey.values()].sort((a, b) => a.min - b.min).map((r) => ({
      label: r.max ? t("shop.copies_range", lang, { a: r.min, b: r.max }) : t("shop.copies_plus", lang, { a: r.min }),
      prices: r.prices,
    }));
    volume = {
      cols: volPlans.map((p) => { const tk = termKey(p.term_months); return tk ? t(tk.key, lang, tk.vars) : p.title; }),
      rows,
      note: stoodIn ? t("shop.pc_volume", lang, { term: t("shop.term_year", lang) }) : "",
    };
  }
  // the change whose announced price stands in for a store price here (shopSubs: the note under the prices)
  const stood = sorted.map((p) => st.get(p)).find((x) => x.subst);
  return {
    terms,
    volume,
    fromPerMonth: withMonths.length ? money(round2(Math.min(...withMonths.map((p) => priceOf(p) / p.term_months))), lang, cur) : "",
    stoodIn: stood ? stood.change : null,
  };
}

function typeView(pub, type, plans, shop, lang, t, changes = new Map(), now = nowDate()) {
  // Description: the store's own words when they are in the page's language (not a machine translation),
  // else our short i18n text.
  const official = shop.types && shop.types[pub] && shop.types[pub][type];
  // The card lists every term, so a description written for one term ("Un año de acceso…",
  // "One year of online access…") loses that lead-in. The print text is always ours: the store's
  // ("seis (6) ejemplares…") counts one year's copies and would read as the total on a 1–3 year card.
  const officialText = official && lang === STORE_LANG[pub] && type !== "print"
    ? String(official[lang] || "").replace(/^(un|1)\s+años?\s+de\s+|^(one|1)\s+years?\s+of\s+/i, "").replace(/^./, (c) => c.toUpperCase())
    : "";
  const fallbackKey = type === "print" ? "shop.desc_print_" + pub : type === "other" ? "" : "shop.desc_" + type;
  // The next announced change of one of these plans that is still ahead: the card holds both lists, and the
  // browser switches to the second at that moment (`swap`).
  const ahead = plans.map((p) => p.change && p.change.stale && changes.get(p.change.key))
    .filter((c) => c && !passed(c.at.effective, now))
    .sort((a, b) => String(a.at.effective).localeCompare(String(b.at.effective)))[0];
  return {
    type,
    name: type === "other" ? (plans[0].title || "") : t("shop.type_" + type, lang),
    desc: officialText || (fallbackKey ? t(fallbackKey, lang) : ""),
    descLang: officialText ? lang : "",
    ...typeState(plans, lang, t, changes, now, "now"),
    swap: ahead ? { at: ahead.at.effective, ...typeState(plans, lang, t, changes, now, "after") } : null,
  };
}

export function shopSubs(shop, lang = "en", t = (k) => k, now = nowDate()) {
  const subs = shop && Array.isArray(shop.subscriptions) ? shop.subscriptions : [];
  const changes = changeMap(shop);
  const pubs = [];
  for (const pub of pubOrder(lang)) {
    const regions = [];
    for (const region of REGION_ORDER) {
      const entry = subs.find((s) => s && s.pub === pub && s.region === region);
      const plans = entry && Array.isArray(entry.plans) ? entry.plans.filter((p) => p && Number(p.price) > 0 && p.url) : [];
      if (!plans.length) continue;
      const types = [];
      for (const type of TYPE_ORDER) {
        const tp = plans.filter((p) => (TYPE_ORDER.includes(p.type) ? p.type : "other") === type);
        if (tp.length) types.push(typeView(pub, type, tp, shop, lang, t, changes, now));
      }
      regions.push({ region, url: entry.url || "", types });
    }
    if (regions.length) pubs.push({ pub, isLv: pub === "lv", mag: MAG[pub], regions });
  }
  // Every region that any publication offers, in the fixed order (a region missing for the selected
  // publication is hidden by the page's switch).
  const regionList = REGION_ORDER.filter((r) => pubs.some((p) => p.regions.some((x) => x.region === r)));
  // Client-side switch config: which regions each publication offers, and the default (U.S. when offered).
  const avail = {};
  for (const p of pubs) avail[p.pub] = p.regions.map((r) => r.region);
  for (const p of pubs) p.defaultRegion = avail[p.pub].includes("us") ? "us" : avail[p.pub][0];
  // The prices come from the stores — except an announced price standing in for a store's old one: the note
  // under the prices says so (now, or from the moment the page switches to the new prices: `win`).
  const types = pubs.flatMap((p) => p.regions.flatMap((r) => r.types));
  const now0 = types.find((tp) => tp.stoodIn);
  const later = types.find((tp) => tp.swap && tp.swap.stoodIn);
  // (the date as the plans' own mark writes it: "New price since Jan 1, 2027")
  const pcNote = now0 ? { date: dayLabel(now0.stoodIn.effective, lang, true), win: null }
    : later ? { date: dayLabel(later.swap.stoodIn.effective, lang, true), win: { from: later.swap.at, until: "", hidden: true } } : null;
  return { pubs, regions: regionList, first: pubs.length ? pubs[0].pub : "", avail, pcNote };
}

// "Subscriptions from $2.99/month" (home page, monthly toolkit, orientation): the U.S. store's prices only — the
// Canadian and international listings are other prices for other readers (no U.S. listing: null, no line).
export function shopFromMonthly(shop) {
  const subs = (shop && Array.isArray(shop.subscriptions) ? shop.subscriptions : []).filter((s) => s && s.region === "us");
  const plans = subs.flatMap((s) => (Array.isArray(s.plans) ? s.plans : [])).filter((p) => p && Number(p.price) > 0);
  const monthly = plans.filter((p) => p.term_months === 1).map((p) => Number(p.price));
  if (monthly.length) return Math.min(...monthly);
  const rates = plans.filter((p) => p.term_months).map((p) => Number(p.price) / p.term_months);
  return rates.length ? round2(Math.min(...rates)) : null;
}

/* ---------------- Announced price changes: the notices ---------------- */
/**
 * The notices of the announced price changes that still have something to say at `now`, soonest first → [{
 *   key, effective, at, date ("January 1, 2027"), dateShort ("Jan 1, 2027"),
 *   before: { win, rows, books } | null   "Prices change on …": from the day it was announced to the day before
 *                                          (books: "$2.00" more each, or "")
 *   after:  { win, rows, books } | null    "New prices since …": from the day through notice_until (books: true when
 *                                          book prices changed — the amount is said only before the day)
 *   source, sourceLang, docMatch (finds AA Grapevine's notice among the Drive files: committee.js driveMatch)
 * }]. Rows (shop.json price_changes[].yearly, the page language's magazine first): { pub, isLv, mag, type, typeName,
 * term, now (the store's price today, "" when the stores list none), new, same (the store already shows it),
 * after (what the plan shows from the day) }.
 */
export function shopPriceChanges(shop, lang = "en", t = (k) => k, now = nowDate()) {
  const order = pubOrder(lang);
  const out = [];
  for (const c of changeMap(shop).values()) {
    const before = shopWindow(c.at.announced, c.at.effective, now);
    const after = shopWindow(c.at.effective, c.at.notice_end, now);
    if (!before && !after) continue;
    const rows = (Array.isArray(c.yearly) ? c.yearly : [])
      .filter((r) => r && MAG[r.pub] && Number(r.new) > 0)
      .map((r, i) => ({ r, i }))
      .sort((a, b) => order.indexOf(a.r.pub) - order.indexOf(b.r.pub) || a.i - b.i)
      .map(({ r }) => ({
        pub: r.pub, isLv: r.pub === "lv", mag: MAG[r.pub], type: r.type,
        typeName: t("shop.type_" + r.type, lang), term: t("shop.term_year", lang),
        now: Number(r.now) > 0 ? money(r.now, lang) : "",
        new: money(r.new, lang),
        same: Number(r.now) > 0 && round2(Number(r.now)) === round2(Number(r.new)),
        after: money(Number(r.after) > 0 ? r.after : r.new, lang),
      }));
    const books = Number(c.books_more) > 0 ? money(c.books_more, lang) : "";
    out.push({
      key: c.key, effective: c.effective, at: c.at,
      date: dayLabel(c.effective, lang), dateShort: dayLabel(c.effective, lang, true),
      before: before ? { win: before, rows, books } : null,
      after: after ? { win: after, rows, books: !!books } : null,
      source: (c.source && c.source[lang]) || "",
      sourceLang: (c.source_lang && c.source_lang[lang]) || lang,
      docMatch: c.doc_match || "",
    });
  }
  return out.sort((a, b) => String(a.effective).localeCompare(String(b.effective)));
}

/**
 * The announced change to mention for the days `first`–`last` (YYYY-MM-DD, Central) — a month of the toolkit, the
 * month a digest goes out in, or one day → { kind, c } or null: "before" when those days meet the days from its
 * announcement to the day before it takes effect, else "after" when they meet the days from it through
 * notice_until (the soonest such change). The monthly toolkit's message (monthly.js priceMention), the GV/LV
 * report (report.js shopSection) and the monthly digest (community.js digestPrice; its e-mail twin:
 * scripts/notify/send_digest.py price_change) say it in one line: shop.pc_line_before / shop.pc_line_after.
 */
export function shopPriceChangeIn(shop, first, last = first) {
  const ymd = /^\d{4}-\d{2}-\d{2}$/;
  if (!ymd.test(String(first)) || !ymd.test(String(last))) return null;
  const list = [...changeMap(shop).values()]
    .filter((c) => ymd.test(String(c.effective)) && ymd.test(String(c.announced)))
    .sort((a, b) => String(a.effective).localeCompare(String(b.effective)));
  for (const c of list) {
    const until = ymd.test(String(c.notice_until)) ? c.notice_until : c.effective;
    if (first < c.effective && last >= c.announced) return { kind: "before", c };
    if (first <= until && last >= c.effective) return { kind: "after", c };
  }
  return null;
}


/* ---------------- Specialty items (greeting cards, pocket planner, wall calendar, holiday cards) ---------------- */
// The page order. The holiday cards come last: the stores sell them in season only (from about September), so
// out of season the other three keep their places (build_data leaves a seasonal item off two weeks after its store
// stopped showing it: SHOP_SEASONAL_GRACE_DAYS).
const SPECIAL_ORDER = ["cards", "planner", "calendar", "holiday"];
const SEASONAL = ["holiday"];
// The same product sold by both stores: "MS08LV" (La Viña) is "MS08" (Grapevine).
const skuRoot = (sku) => String(sku || "").trim().toUpperCase().replace(/-?LV$/, "");
// The pack size at the end of a store's product name: "Holiday Greeting Cards - 12 pack", "¡Tarjetas de ocasión
// para las fiestas! Paquete de 12", "… (Pack of 12)". Shown as the badge right above the title instead.
const PACK_TAIL = /\s*(?:[-–—:,]\s*)?\(?\s*(?:\d{1,3}[\s-]*pack|(?:pack|box)\s+of\s+\d{1,3}|(?:paquete|caja)\s+de\s+\d{1,3})\s*\)?\s*$/i;

// The name a card shows: the store's own, without a pack size the badge already gives ("12 pack" → "Pack of 12")
function cardTitle(p) {
  const title = String(p.title || "");
  return (Number(p.pack) > 1 && title.replace(PACK_TAIL, "").trim()) || title;
}

function specialView(p, lang, twin, t) {
  const pub = p.pub === "lv" ? "lv" : "gv";
  const itemLang = p.lang || STORE_LANG[pub];
  const cur = p.currency || "USD";
  // The store's own words only in the page's language (never a machine translation); else our own line.
  const own = p.text && itemLang === lang ? p.text : "";
  const vol = (Array.isArray(p.volume) ? p.volume : []).filter((v) => v && Number(v.price) > 0 && v.min > 1)[0];
  return {
    id: p.id || "",
    type: p.type,
    anchor: "special-" + p.type,
    pub,
    isLv: pub === "lv",
    mag: MAG[pub],
    store: pub === "lv" ? "aalavina.org" : "aagrapevine.org",
    title: cardTitle(p),
    titleLang: itemLang,
    // what the kind is called in the page language: shown under a title in the other language (a store that
    // does not sell this kind right now: the other store's item fills in)
    typeName: t("shop.special_type_" + p.type, lang),
    url: p.url || "",
    // the same product's picture from the other store when this one has none yet
    image: p.image || (twin && twin.image) || "",
    price: money(p.price, lang, cur),
    volume: vol ? t(vol.max ? "shop.special_vol_range" : "shop.special_vol", lang, { a: vol.min, b: vol.max, price: money(vol.price, lang, cur) }) : "",
    // the stores sell the greeting cards by the box ("box of 24"), the holiday cards by the pack ("12 pack",
    // "Paquete de 12")
    pack: Number(p.pack) > 1 ? t(p.type === "holiday" ? "shop.special_pack_of" : "shop.special_pack", lang, { n: p.pack }) : "",
    trilingual: !!(p.trilingual || (twin && twin.trilingual)),
    seasonal: SEASONAL.includes(p.type),
    text: own || t("shop.special_desc_" + p.type, lang),
    textLang: own ? itemLang : lang,
  };
}

// One card per kind (cards · planner · calendar · holiday): the page language's store first (/es/: La Viña),
// the other store's item of the same kind as `also` (a link). Kinds the stores do not list are left out.
export function shopSpecialty(shop, lang = "en", t = (k) => k) {
  const all = (shop && Array.isArray(shop.specialty) ? shop.specialty : [])
    .filter((p) => p && p.url && p.title && Number(p.price) > 0 && SPECIAL_ORDER.includes(p.type));
  const order = pubOrder(lang);
  const out = [];
  for (const type of SPECIAL_ORDER) {
    const of = (pub) => all.filter((p) => p.type === type && (p.pub === "lv" ? "lv" : "gv") === pub);
    const first = of(order[0])[0] || of(order[1])[0];
    if (!first) continue;
    const otherPub = (first.pub === "lv" ? "lv" : "gv") === "lv" ? "gv" : "lv";
    const other = of(otherPub)[0] || null;
    const twin = other && skuRoot(other.sku) && skuRoot(other.sku) === skuRoot(first.sku) ? other : null;
    const v = specialView(first, lang, twin, t);
    v.also = other ? { url: other.url, title: cardTitle(other), titleLang: other.lang || STORE_LANG[other.pub === "lv" ? "lv" : "gv"],
      mag: MAG[otherPub], store: otherPub === "lv" ? "aalavina.org" : "aagrapevine.org", isLv: otherPub === "lv", same: !!twin } : null;
    out.push(v);
  }
  return out;
}

/* ---------------- Bulk-book discounts ---------------- */
export function shopBulk(shop, lang = "en", t = (k) => k) {
  const bd = shop && shop.bulk_discounts;
  const tiers = bd && Array.isArray(bd.tiers) ? bd.tiers : [];
  const rows = tiers
    .filter((x) => x && Number(x.off) > 0)
    .sort((a, b) => a.min - b.min)
    .map((x) => ({
      label: x.max ? t("shop.books_range", lang, { a: x.min, b: x.max }) : t("shop.books_plus", lang, { a: x.min }),
      off: money(x.off, lang),
    }));
  const note = bd && bd.note ? bd.note[lang] || "" : "";
  return { rows, note, source: (bd && bd.source_url) || "" };
}

export default function (eleventyConfig, helpers) {
  const t = helpers.translateKey;
  eleventyConfig.addFilter("shopBotm", (shop, lang) => shopBotm(shop, lang, "", t));
  eleventyConfig.addFilter("shopSubs", (shop, lang) => shopSubs(shop, lang, t));
  eleventyConfig.addFilter("shopPriceChanges", (shop, lang) => shopPriceChanges(shop, lang, t));
  eleventyConfig.addFilter("shopBulk", (shop, lang) => shopBulk(shop, lang, t));
  eleventyConfig.addFilter("shopSpecialty", (shop, lang) => shopSpecialty(shop, lang, t));
  eleventyConfig.addFilter("shopFromMonthly", (shop) => shopFromMonthly(shop));
  eleventyConfig.addFilter("shopMoney", (n, lang) => money(n, lang));
}
