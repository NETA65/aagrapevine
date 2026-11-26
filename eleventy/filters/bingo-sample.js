// GVR / RLV Bingo — the cards the BUILD draws: the /gvr/bingo/ page's sample card (what the page shows and prints
// without JavaScript: 5×5, the page's language, a fixed game code) and the /gvr/ teaser's decorative mini card (3×3 or
// 4×4). Auto-loaded by eleventy.config.js like every eleventy/filters/*.js: its default export below registers the
// filter. The squares are the `bingo` global (src/_data/bingo.js → eleventy/filters/bingo.js loadBingo: the CSV
// content/bingo/bingo.csv checked and filled in); the draw and the layout are src/assets/js/bingo-core.js itself
// (window.GVBingo, the browser builder's pure functions), run once here in a vm context as booth.js boothCore() runs
// booth-core.js — so the sample is the card the builder draws with the same settings and code, never a copy of its
// rules. The pages: src/pages/gvr-bingo.njk (the sample) and src/pages/gvr.njk (#bingo, the teaser).
//
//   bingoCore()                         → GVBingo (bingo-core.js's module), read once per build
//   bingoSample(bingo, lang, opts)      → { ok, settings, words, card, plan, pool } — card 0 of a fixed code:
//       bingo  the `bingo` global ({ items, … }; anything else = no squares)
//       lang   the card's language: "es" | anything else = "en" (the page's language: a sample's card is in it)
//       opts   { rows, cols (default 5 × 5), code (default SAMPLE.code), pub, where, infoMax, free, event, date
//                ("YYYY-MM-DD"; default the build's day in Central time — monthly.js nowDate, so MONTHLY_NOW moves it
//                for a preview as for the other dated pages), showName, showRules, showInfo, words (the page's card
//                words in that language — src/_i18n/bingo.json's; what is missing comes from GVBingo.WORDS), dense
//                (true / false: the squares' short words or not, whatever the core estimates for the settings — the
//                teaser's mini card is no printed sheet) } — any other settings key of GVBingo.DEFAULTS too;
//                GVBingo.normalize makes every value safe
//     → ok: false when the pool is too small for the grid (card null; error "short", have, need: the template
//       says the builder needs more squares and shows no card); else card = GVBingo.card(…, 0) with each cell's
//       starting font size `pt` (GVBingo.fontGuess for the plan's cell: the server cannot measure), plan =
//       GVBingo.layout(settings) ({ sheet, card }: the page, the slot, the parts and the cell in inches), pool =
//       { size, need, have } (the "N squares to draw from" line). settings: the normalized ones (their code and
//       date, so a test can draw the same card again).
//
//   bingoBreaks(html)                   → the sample's words with the places to break the builder gives them (bingo.js
//       breakable / textIn): HTML that was ESCAPED first ({{ c.text | escape | bingoBreaks | safe }}), with <wbr>
//       after an e-mail's "@" and after a "/" and before a "." in the site's address, and each time range ("7 – 8
//       PM", "7–8 p. m.") in <span class="bgo-nb"> (kept on one line: areas/bingo.css)
//
// Pure apart from the build's clock: the same CSV, settings and day give the same card in every build, on both
// pages and in the browser (tests/test_bingo_cards.py checks the sample against the core run in Node). Nothing here
// makes HTML but bingoBreaks, which only adds those tags to words already escaped: the templates put every word in
// with autoescape on, or escape first.

import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { nowDate, chicagoYmd } from "./monthly.js";

const ROOT = process.cwd();
const CORE = "src/assets/js/bingo-core.js";

/** The sample's fixed settings (a code of the core's ALPHABET: no I, O, 0 or 1). */
export const SAMPLE = Object.freeze({ rows: 5, cols: 5, code: "GV65" });

let coreModule = null;
/** src/assets/js/bingo-core.js's GVBingo (the builder's pure functions), run once for the build. */
export function bingoCore() {
  if (!coreModule) {
    const ctx = vm.createContext({ console });
    vm.runInContext(fs.readFileSync(path.resolve(ROOT, CORE), "utf8"), ctx, { filename: "bingo-core.js" });
    coreModule = ctx.GVBingo;
  }
  return coreModule;
}

const isMap = (v) => !!v && typeof v === "object" && !Array.isArray(v);
// a value from the vm context as a plain object of this realm (the templates and the tests compare them)
const plain = (v) => JSON.parse(JSON.stringify(v));

/** Card 0 of a fixed code for the page's no-JS sample and the /gvr/ teaser (the header says what comes back). */
export function bingoSample(bingo, lang = "en", opts = {}) {
  const G = bingoCore();
  const L = lang === "es" ? "es" : "en";
  const o = isMap(opts) ? opts : {};
  const items = isMap(bingo) && Array.isArray(bingo.items) ? bingo.items : [];
  const raw = { ...o, lang: L, count: 1, same: false, perSheet: 1 };
  delete raw.words;
  delete raw.dense;
  if (raw.rows === undefined) raw.rows = SAMPLE.rows;
  if (raw.cols === undefined) raw.cols = SAMPLE.cols;
  if (!G.cleanCode(raw.code)) raw.code = SAMPLE.code;
  if (!raw.date) raw.date = chicagoYmd(nowDate());
  const settings = plain(G.normalize(raw));
  const words = plain(G.wordsFor(L, o.words));
  const p = G.pool(items, settings);
  const pool = { size: p.pool.length, need: p.need, have: p.have };
  const plan = plain(G.layout(settings));
  if (!p.ok) return { ok: false, error: "short", have: p.have, need: p.need, settings, words, card: null, plan, pool };
  const card = plain(G.card(items, settings, 0, words, typeof o.dense === "boolean" ? { dense: o.dense } : undefined));
  for (const c of card.cells) c.pt = G.fontGuess(c.text, plan.card.cell, c.mark);
  return { ok: true, settings, words, card, plan, pool };
}

// an address and its places to break (bingo.js ADDRESS / breakable, bingo-core.js addressPieces: the same); a time
// range (bingo.js RANGE / textIn). Neither can match inside an entity of the escaped words (&amp; &lt; &#39; …: no
// "@", "/", "." or "–" in them)
const ADDRESS = /\S*@\S+|\S+\.(?:org|com|net|io|edu|gov|us)(?:\/\S*)?/gi;
const RANGE = /\d\s?\u2013\s?\d/g;

/** Escaped words → the same HTML with the builder's places to break and its time ranges kept whole (the header). */
export function bingoBreaks(html) {
  return String(html ?? "")
    .replace(ADDRESS, (a) => (a.includes("@") ? a.replace(/@(?=\S)/g, "@<wbr>")
      : a.replace(/\/(?=\S)/g, "/<wbr>").replace(/(\S)\.(?=\S)/g, "$1<wbr>.")))
    .replace(RANGE, (r) => `<span class="bgo-nb">${r}</span>`);
}

export default function (eleventyConfig) {
  // {% set sample = bingo | bingoSample(lang, { rows: 4, cols: 4, words: … }) %} — src/pages/gvr-bingo.njk (the
  // no-JS sample card) and src/pages/gvr.njk (the teaser's mini card)
  eleventyConfig.addFilter("bingoSample", (bingo, lang, opts) => bingoSample(bingo, lang, opts));
  // {{ c.text | escape | bingoBreaks | safe }} — the no-JS sample's squares and meetings strip (gvr-bingo.njk)
  eleventyConfig.addFilter("bingoBreaks", (html) => bingoBreaks(html));
}
