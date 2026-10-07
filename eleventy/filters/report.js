// /monthly/#report — the district-meeting report a GVR / RLV tailors and shares.
// Owner: the #report section of src/pages/monthly.njk, the browser editor src/assets/js/report.js,
// the strings src/_i18n/report.json (report.*) and the styles src/assets/css/areas/report.css.
//
// reportModel() writes the report's 12 sections — each a title and a plain text — in English AND
// Spanish, for the current month (Central time), from data the site already has:
//   header     "District [##] Grapevine / La Viña report — <Month YYYY>" + "Prepared by: …" (blanks)
//   committee  site `meeting` (next date, the rule), a pointer to /meetings/ for the meeting's link (its platform:
//              config/site.yml meeting.platform, Zoom when not set)
//   issues     the month model (eleventy/filters/monthly.js): GV theme, LV issue, config/carry.yml tips
//   deadlines  db.editorial (next 3 Grapevine deadlines, next 2 La Viña deadlines — its yearly themes —, La
//              Viña's rotating topics), db.audio_project
//   shop       db.shop (Book of the Month offers, the lowest subscription prices, a price change AA Grapevine
//              announced: shopSection — with the section's text from its day, `after`), Carry the Message
//   events     db.events — the next 45 days (upcomingEvents: a monthly series once, with "every month")
//   writers    db.spotlight — Area 65 writers of the last 60 days (first name + initial + city)
//   meetings   db.meetings (committee.js gvMeetings) + `meetings.options` for the county picker
//   weekly     db.weekly_open (Grapevine on Wednesdays, La Viña on Thursdays)
//   resources  db.pdfs (official documents of the last 45 days), GVR / RLV sign-up links, contact
//   asks       a gentle example, in [brackets] where the GVR fills in
//   notes      empty (an empty section is left out of the report)
// The page embeds the model as JSON (rpJson); the editor lets each GVR / RLV switch sections on and
// off, reorder and edit them, add their own, and copy / share / print / download the result. Without
// JavaScript the page shows rpText(model, lang): the same sections joined by the same rules as the
// editor's plain text (composeText below — keep it in step with report.js's `compose`).
// Filters: rpModel(db, meeting, carry, site) · rpText(model, lang) · rpJson(value) · rpUi(lang)
// Dev/test: MONTHLY_NOW=2026-12-15 fixes "today" (as for the posters).
import { eventWhen, eventWhere, writersPick, spotlightOf, spotlightHomeDays, writerName, issueLabelOf, issueInSentence, itemIssueName } from "./community.js";
import { issueName } from "./read.js";
import { digestShop, weeklyOpenAll, gvMeetings, eventEndMs, chicagoDayEndMs } from "./committee.js";
import { monthModel, nowDate, chicagoYmd, shortDate, timeRange, monthLabel, midSentence } from "./monthly.js";
import { botmPriceState, shopPlanPrice, shopNextChange, shopPriceChangeIn, dayLabel } from "./shop.js";
import { scriptJson } from "../script-json.js";
import { langLink } from "../../eleventy.config.js";

const LOC = { en: "en-US", es: "es-US" };
const DAY = 864e5;
const EVENT_DAYS = 45;
const DOC_DAYS = 45;
export const SECTION_IDS = ["header", "committee", "issues", "deadlines", "shop", "events", "writers", "meetings", "weekly", "resources", "asks", "notes"];

// Helpers handed over by eleventy.config.js; the fallbacks keep the module usable from plain node.
let H = {
  translateKey: (k) => k,
  pickLang: (item, field, lang) => {
    const i = item && item.i18n && item.i18n[field];
    return (i && i[lang]) || (item && (item[field] ?? item.extra?.[field])) || "";
  },
};
const t = (key, lang, vars) => H.translateKey(key, lang, vars);
const clean = (s) => String(s ?? "").replace(/\s+/g, " ").trim();
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const lcFirst = (s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s);
const isYmd = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
/** "2026-10-15" → "2026-10-14" */
const dayBefore = (ymd) => new Date(Date.parse(ymd + "T12:00:00Z") - DAY).toISOString().slice(0, 10);
const list = (items, lang) => {
  const a = items.filter(Boolean);
  try { return new Intl.ListFormat(LOC[lang] || "en-US", { style: "long", type: "conjunction" }).format(a); } catch { return a.join(", "); }
};
const money = (v, lang) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  return new Intl.NumberFormat(LOC[lang] || "en-US", { style: "currency", currency: "USD" }).format(n);
};
/** "Wednesday, October 21" / "miércoles 21 de octubre" (a Central-time calendar day) */
function longDate(ymd, lang) {
  const d = new Date(ymd + "T12:00:00Z");
  if (lang === "es") {
    const f = (o) => new Intl.DateTimeFormat("es-US", { ...o, timeZone: "UTC" }).format(d);
    return `${f({ weekday: "long" })} ${d.getUTCDate()} de ${f({ month: "long" })}`;
  }
  return new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" }).format(d);
}
/** Is the item's own language not the report's? → " (in Spanish)" / " (en inglés)" */
const otherLangNote = (docLang, lang) => (docLang && docLang !== lang ? ` (${t(docLang === "es" ? "report.r_in_es" : "report.r_in_en", lang)})` : "");

/* ------------------------------------------------------------------ */
/*  Upcoming events                                                    */
/* ------------------------------------------------------------------ */
/**
 * Events that start within `days` days and are not over yet (an assembly over several days stays
 * until its last day), soonest first; the committee meeting has its own section. A monthly series
 * (config/site.yml recurring_events, category "recurring") shows only its next date. "Over" is the rule
 * of every page that lists events (committee.js eventEndMs: a timed event at its end — one hour after it
 * starts without one —, an all-day one at midnight Central after its last day).
 */
export function upcomingEvents(db, now, days = EVENT_DAYS) {
  const nowMs = now instanceof Date ? now.getTime() : Number(now);
  const isYmd = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
  const startOf = (e) => (e.extra && e.extra.start) || e.date || null;
  const msOf = (v) => (isYmd(v) ? Date.parse(v + "T12:00:00Z") : Date.parse(v));
  const seen = new Set();
  return ((db.events && db.events.items) || [])
    .filter((e) => e && e.kind === "event" && e.status !== "gone" && e.category !== "committee" && startOf(e))
    .filter((e) => { const t = msOf(startOf(e)); return Number.isFinite(t) && t <= nowMs + days * DAY && eventEndMs(e) >= nowMs; })
    .sort((a, b) => msOf(startOf(a)) - msOf(startOf(b)))
    .filter((e) => {
      if (e.category !== "recurring") return true;
      const k = String((e.extra && e.extra.series) || e.id);
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .map((e) => ({ ...e, _recurring: e.category === "recurring", _tentative: !!(e.extra && e.extra.tentative === true) }));
}

/* ------------------------------------------------------------------ */
/*  Section 5: Book of the Month, subscriptions, price changes         */
/* ------------------------------------------------------------------ */
/**
 * The shop section's text as it stands at the moment `at` (the build's "now", or a later moment it changes at —
 * shopSteps): in the "now" state, or "after" from the day the next announced price change (`next`, shop.js
 * shopNextChange) takes effect. Book of the Month offers only while they run (dated data: from their `starts` day
 * through their `ends` day, Central time — an offer that has ended by `at` is never quoted). Prices only while they
 * are current (eleventy/filters/shop.js): a Book of the Month price read before a book price change in effect — or
 * before `next`, in the "after" state — is left out (its percent stays), and a 1-year plan shows its announced price
 * while the store data still has the old one (shopPlanPrice). An announced change is passed on to the district in AA
 * Grapevine's own list — the 1-year prices it names and the books — under "New prices from …" before its day and
 * "New prices since …" from it through its notice_until (never "the prices above are the new ones": the lowest
 * price above may be a plan the announcement does not name, like a monthly one).
 */
function shopSection(L, T, ctx, at, next = null) {
  const { db, site, abs } = ctx;
  const now = at;
  const state = next && now.getTime() >= Date.parse(next.at.effective) ? "after" : "now";
  const out = [];
  const shop = db.shop || {};
  const day = chicagoYmd(now);
  const bm = digestShop(shop, L, new Date(now));
  bm.offers = bm.offers.filter((o) => !isYmd(o.raw && o.raw.starts) || o.raw.starts <= day);
  if (bm.offers.length) {
    const same = bm.offers.every((o) => o.pct === bm.offers[0].pct && o.endsLabel === bm.offers[0].endsLabel);
    out.push(same && bm.offers[0].pct && bm.offers[0].endsLabel ? T("b_title", { pct: bm.offers[0].pct, date: bm.offers[0].endsLabel }) : T("b_title_plain"));
    for (const o of bm.offers) {
      const title = `“${o.title}”${o.gloss ? ` (${o.gloss})` : ""}`;
      const pc = botmPriceState(o.raw, shop, now);
      const current = !pc.stale && !(state === "after" && pc.soon);
      let price = current ? (o.price ? T("b_price", { sale: o.sale, price: o.price }) : o.sale) : "";
      if (!same && o.pct && o.endsLabel) price += `${price ? " · " : ""}${T("b_until", { pct: o.pct, date: o.endsLabel })}`;
      out.push(`• ${price ? T("b_line", { pub: o.pubName, title, price }) : T("b_line_plain", { pub: o.pubName, title })}`);
    }
  }
  const subs = [];
  const order = L === "es" ? ["lv", "gv"] : ["gv", "lv"];
  for (const pub of order) {
    const reg = (shop.subscriptions || []).find((s) => s && s.pub === pub && s.region === "us");
    const plans = ((reg && reg.plans) || []).filter((p) => p && Number.isFinite(Number(p.price)) && Number(p.price) > 0)
      .map((p) => ({ p, price: shopPlanPrice(p, shop, state, now) }));
    if (!plans.length) continue;
    const printYear = plans.find((x) => x.p.type === "print" && Number(x.p.term_months) === 12);
    const low = [...plans].sort((a, b) => a.price - b.price)[0];
    const term = (n) => (Number(n) === 1 ? T("term_1") : Number(n) === 12 ? T("term_12") : T("term_n", { n }));
    const bits = [];
    if (printYear) bits.push(T("s_print", { price: money(printYear.price, L) }));
    if (low && low !== printYear) bits.push(T("s_low", { type: ["print", "digital", "complete"].includes(low.p.type) ? T(`t_${low.p.type}`) : low.p.type, price: money(low.price, L), term: term(low.p.term_months) }));
    if (bits.length) subs.push(`• ${pub === "lv" ? "La Viña" : "Grapevine"}: ${bits.join(" · ")}`);
  }
  if (subs.length) out.push(T("s_title"), ...subs);
  // the announced change to pass on (shopPriceChangeIn on the day of `at`: "before" from its announcement, "after"
  // from its day through its notice_until)
  const hit = shopPriceChangeIn(shop, day);
  if (hit) {
    out.push(T(hit.kind === "before" ? "pc_before" : "pc_after", { date: dayLabel(hit.c.effective, L) }));
    for (const pub of order) {
      const rows = (hit.c.yearly || []).filter((r) => r && r.pub === pub && Number(r.new) > 0);
      if (rows.length) out.push(`• ${T("pc_pub", { pub: pub === "lv" ? "La Viña" : "Grapevine", list: rows.map((r) => `${T(`t_${r.type}`)} ${money(r.new, L)}`).join(", ") })}`);
    }
    if (Number(hit.c.books_more) > 0) out.push(`• ${T("pc_books", { amount: money(hit.c.books_more, L) })}`);
  }
  out.push(T("s_group"));
  // Carry the Message: La Viña's own page ("Lleva el Mensaje", in Spanish) on a Spanish report, as on /es/shop/
  // (the site's one rule for a link's Spanish twin: eleventy.config.js langLink)
  const ctm = langLink(site.links, "carry_the_message", L);
  if (ctm) out.push(T("s_ctm", { url: ctm }));
  out.push(T("s_more", { url: abs("/shop/") }));
  return out.join("\n");
}

/** The moments after `now` the shop section's text changes at, as [{ at: ISO instant, text }] in time order (the
 *  browser editor shows the last one passed — report.js swapTexts): a Book of the Month offer starts (midnight
 *  Central at its first day) or ends (midnight after its last day), a price change is announced, takes effect or its
 *  notice ends (shop.json price_changes at.announced / at.effective / at.notice_end). Only moments that change the
 *  text; at most 8. */
function shopSteps(L, T, ctx, first) {
  const shop = ctx.db.shop || {};
  const nowMs = ctx.now.getTime();
  const next = shopNextChange(shop, ctx.now);
  const marks = new Set();
  for (const b of Array.isArray(shop.botm) ? shop.botm : []) {
    if (b && isYmd(b.ends)) marks.add(chicagoDayEndMs(b.ends));
    if (b && isYmd(b.starts)) marks.add(chicagoDayEndMs(dayBefore(b.starts)));
  }
  for (const c of Array.isArray(shop.price_changes) ? shop.price_changes : []) {
    for (const k of ["announced", "effective", "notice_end"]) if (c && c.at && c.at[k]) marks.add(Date.parse(c.at[k]));
  }
  const steps = [];
  let last = first;
  for (const ms of [...marks].filter((x) => Number.isFinite(x) && x > nowMs).sort((a, b) => a - b)) {
    const text = shopSection(L, T, ctx, new Date(ms), next);
    if (text !== last) steps.push({ at: new Date(ms).toISOString(), text });
    last = text;
    if (steps.length >= 8) break;
  }
  return steps;
}

/* ------------------------------------------------------------------ */
/*  One language's sections                                            */
/* ------------------------------------------------------------------ */
function sectionsFor(L, ctx) {
  const { db, meeting, carry, site, now, key, abs, meet } = ctx;
  const T = (k, v) => t(`report.${k}`, L, v);
  const today = chicagoYmd(now);
  const year = key.slice(0, 4);
  const m = monthModel(key, db, carry, site, L, now);
  const S = {};
  const A = {};      // a section's texts from later moments on: [{ at, text }] (shopSteps)

  /* 1. Header — the blanks are filled by the editor's "Your details" fields */
  S.header = [
    T("h_title", { district: T("tok_district"), month: monthLabel(key, L) }),
    T("h_by", { name: T("tok_name"), role: T("tok_role"), group: T("tok_group") }),
  ].join("\n");

  /* 2. Committee meeting */
  {
    const out = [];
    const nx = meeting && meeting.next;
    // where it meets (config/site.yml meeting.platform), as /meetings/ and the home page say it
    const platform = clean((site && site.meeting && site.meeting.platform) || "") || "Zoom";
    if (nx && nx.start) {
      const time = T("c_time", { time: timeRange(nx.start, nx.end, L) });
      out.push(T("c_next", { date: longDate(nx.ymd || chicagoYmd(nx.start), L), time, platform }));
      const r = (meeting && meeting.rule) || {};
      const wd = Number.isInteger(r.weekday) ? new Intl.DateTimeFormat(LOC[L], { weekday: "long", timeZone: "UTC" }).format(new Date(Date.UTC(2023, 0, 1 + r.weekday))) : "";
      const ord = r.n === -1 ? "last" : String(r.n || "");
      if (wd && ord) out.push(T("c_rule", { rule: lcFirst(t("committee.rule", L, { ord: t(`committee.ord.${ord}`, L), weekday: L === "es" ? wd : cap(wd) })) }));
    } else out.push(T("c_none"));
    out.push(T("c_join", { url: abs("/meetings/"), platform }));
    out.push(T("c_covers"));
    S.committee = out.join("\n");
  }

  /* 3. This month's issues + "put it to work" tips + the month's poster page. A theme that is a machine translation
        (a Grapevine theme in Spanish, a La Viña one in English) has the magazine's own words after it in brackets,
        as the deadlines below, and the section says some titles were translated automatically (mt_note). */
  {
    const out = [];
    let mt = false;
    const orig = (x) => (x && x.machine && x.orig && x.orig !== x.theme ? ` (“${x.orig}”)` : "");
    const gvLine = m.gv ? T("i_gv", { issue: m.gv.label, theme: m.gv.theme }) + orig(m.gv) : "";
    // La Viña's issue by the site's one name for it ("September–October 2026" / "septiembre–octubre de 2026":
    // read.js issueName), as the toolkit, /contribute/, Home and the digest write it
    const lvLine = m.lv && m.lv.theme ? T("i_lv", { issue: issueName(m.lv.key, "lv", L, true) || m.lv.label, theme: m.lv.theme }) + orig(m.lv) : "";
    if ((gvLine && m.gv.machine) || (lvLine && m.lv.machine)) mt = true;
    // On a Spanish report La Viña comes first (the site's rule wherever both magazines appear).
    for (const l of L === "es" ? [lvLine, gvLine] : [gvLine, lvLine]) if (l) out.push(l);
    // A newer issue is already on the web (the October Grapevine appears in late September).
    const issues = (db.articles && db.articles.issues) || [];
    const newer = (pub, after) => issues.filter((i) => i && i.publication === pub && i.key && i.key > after).sort((a, b) => a.key.localeCompare(b.key))[0];
    // its theme in the report's language; a machine translation with the magazine's own words in brackets (the
    // string's “ ” sit around {theme}: “Soledad” (“Loneliness”))
    const newTheme = (i) => {
      const here = clean(H.pickLang(i, "theme", L) || i.theme);
      const own = clean(i.theme);
      const machine = !!here && here !== own && (i.machine || []).includes(L);
      if (machine) mt = true;
      return machine && own ? `${here}” (“${own}` : here;
    };
    const outLines = [];
    const gvNew = newer("gv", key);
    if (gvNew) {
      const theme = newTheme(gvNew);
      if (theme) outLines.push(T("i_out_gv", { issue: issueInSentence(clean((gvNew.i18n && gvNew.i18n.label && gvNew.i18n.label[L]) || monthLabel(gvNew.key, L)), L), theme }));
    }
    const lvNew = m.lv ? newer("lv", m.lv.key) : null;
    if (lvNew) {
      const theme = newTheme(lvNew);
      const label = clean((lvNew.i18n && lvNew.i18n.label && lvNew.i18n.label[L]) || lvNew.label || lvNew.key);
      if (theme) outLines.push(T("i_out_lv", { issue: issueName(lvNew.key, "lv", L, true) || issueInSentence(label, L), theme }));
    }
    if (L === "es") outLines.reverse();
    out.push(...outLines);
    if (!out.length) out.push(T("i_none", { url: abs("/read/") }));
    if (mt) out.push(T("mt_note"));
    if (m.tips.length) {
      out.push(T("i_tips"));
      for (const tp of m.tips.slice(0, 3)) out.push(`• ${tp.title}: ${tp.text}`);
    }
    out.push(T("i_poster", { url: abs(`/monthly/${key}/`) }));
    S.issues = out.join("\n");
  }

  /* 4. Story deadlines: the next 3 Grapevine themes, the next 2 La Viña themes, La Viña's topics, record by phone.
        A machine-translated title (the data's `machine` languages): the section says some titles were translated
        automatically (mt_note), under the lists. */
  {
    const out = [];
    let mt = false;
    const isMt = (d) => (d.machine || []).includes(L);
    const open = (pub) => ((db.editorial && db.editorial.items) || [])
      .filter((e) => e && e.status !== "gone" && e.extra && e.extra.publication === pub && e.extra.deadline && e.extra.deadline >= today
        && (pub === "gv" || e.extra.issue_key))
      .sort((a, b) => a.extra.deadline.localeCompare(b.extra.deadline) || clean(a.title).localeCompare(clean(b.title)));
    const gv = open("gv").slice(0, 3);
    const gvBlock = [];
    if (gv.length) {
      gvBlock.push(T("d_gv"));
      for (const d of gv) {
        const own = clean(d.title);
        const here = clean(H.pickLang(d, "title", L)) || own;
        const theme = `“${here}”${own && here !== own ? ` (“${own}”)` : ""}`; // “Diversión en sobriedad” (“Fun in Sobriety”)
        if (here !== own && isMt(d)) mt = true;
        const issue = d.extra.issue_key ? monthLabel(d.extra.issue_key, L) : issueInSentence(issueLabelOf(d, L), L);
        gvBlock.push(`• ${T("d_line", { theme, issue, date: shortDate(d.extra.deadline, L, year) })}`);
      }
    } else gvBlock.push(T("d_none"));
    const lvBlock = [];
    // an English gloss after a Spanish title: in brackets, or after a dash when it has brackets of its own
    const gloss = (s) => (/[()]/.test(s) ? ` — ${s}` : ` (${s})`);
    // La Viña's dated themes (its yearly themes document): its own Spanish words, the English ones as a gloss
    const lv = open("lv").slice(0, 2);
    if (lv.length) {
      lvBlock.push(T("d_lv_dl"));
      for (const d of lv) {
        const own = clean(H.pickLang(d, "title", "es")) || clean(d.title);
        const here = L === "es" ? own : clean(H.pickLang(d, "title", L)) || own;
        const theme = `“${own}”${here !== own ? gloss(here) : ""}`;          // “Recaídas” (Relapses)
        if (here !== own && isMt(d)) mt = true;
        lvBlock.push(`• ${T("d_line", { theme, issue: itemIssueName(d, L, true), date: shortDate(d.extra.deadline, L, year) })}`);
      }
    }
    if (m.lvTopics.length) {
      lvBlock.push(T("d_lv"));
      for (const tp of m.lvTopics) lvBlock.push(`• “${tp.es}”${L !== "es" && tp.text && tp.text !== tp.es ? gloss(tp.text) : ""}`);
      if (m.lvTopics.some((tp) => tp.machine)) mt = true;
    }
    out.push(...(L === "es" ? [...lvBlock, ...gvBlock] : [...gvBlock, ...lvBlock]));
    if (mt) out.push(T("mt_note"));
    const ap = db.audio_project || {};
    const phones = [];
    if (ap.gv && ap.gv.phone) {
      phones.push(`• ${ap.gv.minutes_min && ap.gv.minutes_max
        ? T("d_phone_gv", { phone: ap.gv.phone, min: ap.gv.minutes_min, max: ap.gv.minutes_max })
        : T("d_phone_gv_max", { phone: ap.gv.phone, max: ap.gv.minutes_max || 8 })}`);
    }
    if (ap.lv && ap.lv.phone) phones.push(`• ${T("d_phone_lv", { phone: ap.lv.phone, max: ap.lv.minutes_max || 7 })}`);
    if (L === "es") phones.reverse();
    if (phones.length) out.push(T("d_phone"), ...phones);
    out.push(T("d_how", { url: abs("/contribute/") }));
    S.deadlines = out.join("\n");
  }

  /* 5. Book of the Month + the lowest subscription prices + home group + Carry the Message (+ a price change AA
        Grapevine announced: shopSection). The section also gets the texts it has from each later moment its
        words change at — an offer ends or starts, a price change is announced, takes effect or its notice ends
        (`steps`, shopSteps: the browser editor switches at that moment, midnight Central — report.js swapTexts). */
  {
    S.shop = shopSection(L, T, ctx, now, shopNextChange(db.shop || {}, now));
    const steps = shopSteps(L, T, ctx, S.shop);
    if (steps.length) A.shop = steps;
  }
  /* 6. Upcoming events (the next 45 days; a monthly series once, with "every month") */
  {
    const out = [];
    const evs = ctx.events;
    if (evs.length) {
      out.push(T("e_intro", { n: EVENT_DAYS }));
      for (const ev of evs.slice(0, 10)) {
        const where = eventWhere(ev, L, t);
        // Spanish: "(hora del Centro)" in place of the CDT / CST abbreviation, as the committee line
        // above (committee.js whenText) and the monthly toolkit say it
        const when = eventWhen(ev, L, now.getTime());
        const bits = [L === "es" ? when.replace(/\s*\b(?:CDT|CST|CT)\b/g, " (hora del Centro)") : when];
        if (ev._recurring) bits.push(T("e_monthly"));
        if (ev._tentative) bits.push(T("e_tbc"));
        out.push(`• ${bits.join(" · ")} — ${clean(H.pickLang(ev, "title", L)) || clean(ev.title)}${where ? ` (${where})` : ""}`);
      }
    } else out.push(T("e_none", { n: EVENT_DAYS }));
    out.push(T("e_all", { url: abs("/events/") }));
    S.events = out.join("\n");
  }

  /* 7. Published writers from our Area (first name + initial + city, as /published/ shows them) */
  {
    const out = [];
    const W = ctx.writers;
    const city = (it) => clean(it.extra && it.extra.geo && it.extra.geo.city) || clean(it.extra && it.extra.author_location);
    const pub = (it) => (it.extra && it.extra.publication === "lv" ? "La Viña" : "Grapevine");
    if (W.neta65.length) {
      out.push(T("w_intro", { n: W.days }));
      for (const it of W.neta65.slice(0, 8)) {
        const c = city(it);
        const title = clean(H.pickLang(it, "title", L)) || clean(it.title);
        out.push(`• ${writerName(it, L, t)}${c ? `, ${c}` : ""} — “${title}” (${pub(it)}, ${itemIssueName(it, L, true)})`);
      }
      if (W.neta65.length > 8) out.push(`• ${T("w_more", { n: W.neta65.length - 8 })}`);
    } else out.push(T("w_none", { n: W.days }));
    if (W.texas.length) {
      const names = W.texas.slice(0, 4).map((it) => { const c = city(it); return `${writerName(it, L, t)}${c ? ` (${c})` : ""}`; });
      const rest = W.texas.length - names.length;
      out.push(T("w_texas", { names: rest > 0 ? `${names.join(", ")} ${T("w_rest", { n: rest })}` : list(names, L) }));
    }
    out.push(T("w_all", { url: abs("/published/") }));
    S.writers = out.join("\n");
  }

  /* 8. Grapevine meetings — the default (no county picked): the count + one group per office region */
  S.meetings = meetingsDefault(L, meet, abs);

  /* 9. Weekly open meetings */
  {
    const out = [];
    const wos = weeklyOpenAll((db.weekly_open && db.weekly_open.items) || [], L, new Date(now));
    if (wos.length) {
      out.push(T("o_intro"));
      for (const w of wos) {
        const starts = w.starts ? ` — ${T("o_starts", { date: w.starts.date })}` : "";
        // "— los jueves a las 11:00 a. m.": the data's "Los jueves …" goes on in lower case after the dash
        out.push(`• ${T("o_line", { title: clean(w.title), when: midSentence(clean(w.when), L) })}${starts}`);
      }
      out.push(T("o_more", { url: abs("/meetings/") + "#weekly-open" }));
    }
    S.weekly = out.join("\n");
  }

  /* 10. Service resources: new official documents, sign-up links, the GVR corner, contact */
  {
    const out = [];
    const docs = ctx.docs;
    if (docs.length) {
      out.push(T("r_docs"));
      const seen = new Set();
      const shown = [];
      for (const d of docs) {
        const title = clean(H.pickLang(d, "title", L)) || clean(d.title);
        if (!title || seen.has(title.toLowerCase())) continue;
        seen.add(title.toLowerCase());
        shown.push({ d, title });
      }
      for (const { d, title } of shown.slice(0, 5)) out.push(`• ${title}${otherLangNote(d.extra && d.extra.doc_lang || d.lang, L)} — ${d.url}`);
      if (shown.length > 5) out.push(T("r_docs_more", { n: shown.length - 5, url: abs("/library/") }));
      else out.push(T("r_library", { url: abs("/library/") }));
    } else out.push(T("r_library", { url: abs("/library/") }));
    const links = site.links || {};
    const signup = [links.gvr_register ? T("r_gvr", { url: links.gvr_register }) : "", links.rlv_register ? T("r_rlv", { url: links.rlv_register }) : ""].filter(Boolean);
    out.push(...(L === "es" ? signup.reverse() : signup));
    out.push(T("r_corner", { url: abs("/gvr/") }));
    if (site.contact_email) out.push(T("r_contact", { email: site.contact_email }));
    S.resources = out.join("\n");
  }

  /* 11. Action items / asks of the Area (a gentle example) · 12. My notes (empty) */
  S.asks = T("a_default");
  S.notes = "";

  return SECTION_IDS.map((id) => ({ id, title: T(`s.${id}`), text: S[id] || "", ...(A[id] ? { steps: A[id] } : {}) }));
}

/* ------------------------------------------------------------------ */
/*  Grapevine meetings: the county picker's options (both languages)   */
/* ------------------------------------------------------------------ */
function placeLine(p, L) {
  const sched = (p.rows || []).map((r) => `${r.label} ${r.slots.map((s) => s.time).join(", ")}`).join("; ");
  const notes = [];
  if (p.spanish) notes.push(t("report.m_es", L));
  if (p.attendance === "hybrid") notes.push(t("report.m_hybrid", L));
  else if (p.attendance === "online") notes.push(t("report.m_online", L));
  const where = p.city ? [p.city, p.state].filter(Boolean).join(", ") : p.placeLine;
  return `• ${p.name}${where ? `, ${where}` : ""}${sched ? ` — ${sched}` : ""}${notes.length ? ` (${notes.join(", ")})` : ""}`;
}

/** The picker: our Area's counties (A–Z), then the regions next to it — with the lines of each. */
function meetingOptions(db, site) {
  const byLang = {};
  for (const L of ["en", "es"]) byLang[L] = gvMeetings(db.meetings || {}, L, site);
  const en = byLang.en;
  const options = [];
  const counties = new Map();
  for (const p of en.areaGroup.places) {
    const c = p.county || "";
    if (!counties.has(c)) counties.set(c, []);
    counties.get(c).push(p.anchor);
  }
  const lineOf = (L, anchor, group) => {
    const all = group === "area" ? byLang[L].areaGroup.places : byLang[L].nearbyGroups.flatMap((g) => g.places);
    const p = all.find((x) => x.anchor === anchor);
    return p ? placeLine(p, L) : "";
  };
  const countyNames = [...counties.keys()].filter(Boolean).sort((a, b) => a.localeCompare(b));
  for (const c of countyNames) {
    const anchors = counties.get(c);
    const count = en.areaGroup.places.filter((p) => anchors.includes(p.anchor)).reduce((n, p) => n + p.count, 0);
    options.push({
      id: "c-" + c.toLowerCase().replace(/[^a-z0-9]+/g, "-"), group: "area", count,
      label: { en: t("report.m_county_label", "en", { name: c }), es: t("report.m_county_label", "es", { name: c }) },
      name: { en: t("report.m_county", "en", { name: c }), es: t("report.m_county", "es", { name: c }) },
      lines: { en: anchors.map((a) => lineOf("en", a, "area")), es: anchors.map((a) => lineOf("es", a, "area")) },
    });
  }
  if (counties.has("")) {
    const anchors = counties.get("");
    options.push({
      id: "c-other", group: "area", count: en.areaGroup.places.filter((p) => anchors.includes(p.anchor)).reduce((n, p) => n + p.count, 0),
      label: { en: t("committee.gvm.area_other", "en"), es: t("committee.gvm.area_other", "es") },
      name: { en: t("committee.gvm.area_other", "en"), es: t("committee.gvm.area_other", "es") },
      lines: { en: anchors.map((a) => lineOf("en", a, "area")), es: anchors.map((a) => lineOf("es", a, "area")) },
    });
  }
  en.nearbyGroups.forEach((g, i) => {
    const es = byLang.es.nearbyGroups[i] || g;
    options.push({
      id: "n-" + g.id, group: "near", count: g.count,
      label: { en: g.label, es: es.label }, name: { en: g.label, es: es.label },
      lines: { en: g.places.map((p) => placeLine(p, "en")), es: es.places.map((p) => placeLine(p, "es")) },
    });
  });
  return { options, byLang };
}

function meetingsDefault(L, meet, abs) {
  const T = (k, v) => t(`report.${k}`, L, v);
  const url = abs("/meetings/") + "#grapevine-meetings";
  const g = meet.byLang[L].areaGroup;
  if (!g || !g.places.length) return T("m_empty", { url });
  const out = [];
  const counties = [...new Set(g.places.map((p) => p.county).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const where = counties.length === 1 ? T("m_county", { name: counties[0] }) : T("m_counties", { list: list(counties, L) });
  out.push(T("m_intro", { n: g.count, g: g.placeCount, counties: where }));
  // A few: from each office region, the group that meets most often (then by city) — the spread of the Area.
  const few = (g.regions || []).map((r) => [...r.places].sort((a, b) => b.count - a.count)[0]).filter(Boolean).slice(0, 5);
  for (const p of few) out.push(placeLine(p, L));
  out.push(T("m_find", { url }));
  return out.join("\n");
}

/* ------------------------------------------------------------------ */
/*  The model (both languages) and its plain text                      */
/* ------------------------------------------------------------------ */
export function reportModel(db = {}, meeting = {}, carry = {}, site = {}, now = nowDate()) {
  const key = chicagoYmd(now).slice(0, 7);
  const base = String(site.url || "").replace(/\/+$/, "");
  const nowMs = now.getTime();
  const spot = spotlightOf(db);
  const today = chicagoYmd(now);
  const since = chicagoYmd(new Date(nowMs - DOC_DAYS * DAY));
  const docs = ((db.pdfs && db.pdfs.items) || [])
    .filter((d) => d && d.status !== "gone" && d.url && typeof d.date === "string" && d.date.slice(0, 10) >= since && d.date.slice(0, 10) <= today)
    .sort((a, b) => b.date.localeCompare(a.date) || clean(a.title).localeCompare(clean(b.title)));
  const meet = meetingOptions(db, site);
  const ctx = { db, meeting, carry, site, now, key, meet, events: upcomingEvents(db, now), writers: writersPick(spot, spotlightHomeDays(spot), nowMs), docs };
  const model = { v: 1, month: key, langs: {}, meetings: { options: meet.options } };
  for (const L of ["en", "es"]) {
    const abs = (p) => `${base}${L === "es" ? "/es" : ""}${p}`;
    model.langs[L] = {
      month: monthLabel(key, L),
      sections: sectionsFor(L, { ...ctx, abs }),
      tokens: { district: t("report.tok_district", L), name: t("report.tok_name", L), role: t("report.tok_role", L), group: t("report.tok_group", L) },
      roles: Object.fromEntries(["gvr", "rlv", "both", "chair", "dcm"].map((r) => [r, t(`report.role_${r}`, L)])),
      custom: t("report.s.custom", L),
      paste: t("report.mail_paste", L),
      meet: { pick: t("report.m_pick", L), none: t("report.m_none", L), more: t("report.m_more", L, { url: abs("/meetings/") + "#grapevine-meetings" }) },
    };
  }
  return model;
}

/** The sections joined as the report: the header as it is, then "1. Title" + text; empty ones left out. */
export function composeText(sections) {
  const out = [];
  let n = 0;
  for (const s of sections) {
    const body = String(s.text || "").replace(/\r\n?/g, "\n").replace(/\s+$/, "").replace(/^\n+/, "");
    if (!body.trim()) continue;
    if (s.id === "header") out.push(body);
    else out.push(`${++n}. ${clean(s.title)}\n${body}`);
  }
  return out.join("\n\n") + "\n";
}
export const reportText = (model, lang) => composeText(((model && model.langs && model.langs[lang]) || { sections: [] }).sections);

// The editor's own strings, in the page language (report.js reads them from the JSON).
const UI_KEYS = ["saved_idle", "saved", "not_saved", "move_up", "move_down", "moved", "include", "included", "excluded", "reset_done", "removed", "added",
  "reset_all_confirm", "reset_all_done", "lang_done", "blanks", "blanks_one", "blanks_none", "read_time", "read_time_one",
  "copied_text", "copied_html", "copied_plain", "copy_failed", "downloaded", "mail_long", "opening", "wa_copied", "text_hint", "header_hint", "n_placeholder",
  "prev_title", "prev_title_month", "prev_text", "prev_btn", "prev_done"];
export function uiStrings(lang) {
  const o = Object.fromEntries(UI_KEYS.map((k) => [k, t(`report.${k}`, lang)]));
  o.lang_en = t("community.lang_name_en", lang);
  o.lang_es = t("community.lang_name_es", lang);
  return o;
}

/** JSON that is safe inside <script type="application/json"> (no "</script>", no "<!--"). */
export const safeJson = scriptJson; // the shared serializer (eleventy/script-json.js)

export default function (eleventyConfig, helpers) {
  if (helpers) H = { ...H, ...helpers };
  // Built once per build (both languages' pages share it).
  let cache = null;
  eleventyConfig.on("eleventy.before", () => { cache = null; });
  eleventyConfig.addFilter("rpModel", (db, meeting, carry, site) => (cache ||= reportModel(db || {}, meeting || {}, carry || {}, site || {})));
  eleventyConfig.addFilter("rpText", (model, lang) => reportText(model, lang));
  eleventyConfig.addFilter("rpJson", (v) => safeJson(v));
  eleventyConfig.addFilter("rpUi", (lang) => uiStrings(lang));
}
