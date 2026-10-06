// /sw.js — the service worker (offline use + the installable app). The logic lives in
// src/_includes/pwa/sw-core.js; this template puts this build's settings above it:
//   version   build.version (src/_data/build.js): a fingerprint of the site's code, so the worker —
//             and its app-shell cache — changes when the code does, not with each daily content sync
//   base      the site's base path ("/aagrapevine/" on GitHub Pages, "/" on a custom domain)
//   shell     what is saved on install: styles, scripts, the two main fonts, the logo and app icons,
//             and the two offline pages (/offline/, /es/offline/ — "Saved pages & app", also the
//             stand-in for a page not saved; the worker keeps them up to date with the daily content,
//             which doesn't change the version: sw-core.js refreshOffline); `required` is the part
//             without which the worker does not install (the browser tries again later) —
//             install-core.js (which phone, the "Install as an app" notice's rules) is optional:
//             without it pwa.js links to the steps (/offline/#steps) instead
//   save      the pages "Save key pages for offline" keeps, in the visitor's language: home, Meetings,
//             the Monthly toolkit hub (with the district report editor) and this month's page ({month},
//             worked out in the worker — skipped when it is missing), Contribute, Shop, Published writers
//             (with the Area 65 part of the Texas writers archive), and Accessibility / GVR 101 (the hub
//             and every lesson page) / the expense tracker when those pages exist
//   files     the data files "Save key pages for offline" keeps too, the same in both languages: the
//             workshop presentations on GVR 101 (/orientation/presentations/<id>.json, one per deck of
//             `presentations.decks`), so a presenter who saved the pages opens every presentation without
//             a connection, and the rest of the Texas writers archive (/published/texas-archive.json and
//             /es/…, src/pages/published-archive-json.11ty.js), so "All of Texas" works offline too (the
//             worker keeps them where it looks for JSON: sw-core.js saveFiles)
//   booth     the booth display's two addresses (the About page's #booth, src/assets/js/booth.js — it
//             plays unattended at the committee's table and keeps playing offline once opened online):
//             `media`, the folder of its photos, videos and sounds (/about/booth/media/<file>, copied
//             from the Drive booth folder by scripts/build/booth-media.mjs under names that never
//             change), answered from the booth's saved copy, byte ranges too, so a video plays and seeks
//             offline (sw-core.js boothMedia); `json`, the show itself (/about/booth.json), network first
//             with the saved copy as the fallback (boothJson). The copy is made when the booth asks
//             (BOOTH_SAVE), into its own cache, gvlv-booth-v1 — not by "Save key pages for offline".
// Registered by src/assets/js/pwa.js with scope = base. Served from the base path, so its scope
// can cover the whole site.
import fs from "node:fs";
import path from "node:path";

export const data = {
  permalink: "/sw.js",
  eleventyExcludeFromCollections: true,
  layout: false,
};

// Optional pages, picked up once they exist (first match wins).
const OPTIONAL = [
  ["accessibility/", "accesibilidad/"],
  ["gvr-101/", "gvr101/", "orientation/", "gvr/101/"],
  // the expense tracker: a GVR adds miles and receipts on the road, with no signal
  // (its entries live in the browser; the page and its two scripts are what is saved)
  ["tracker/"],
];

export function render(data) {
  const prefix = String(process.env.PATH_PREFIX || "/").replace(/^\/+|\/+$/g, "");
  const base = prefix ? `/${prefix}/` : "/";
  const v = data.build.version;

  const urls = new Set();
  for (const p of data.collections?.all || []) {
    if (p.url) urls.add(p.url);
    for (const h of p.data?.pagination?.hrefs || []) urls.add(h);
  }
  // The Monthly toolkit hub ("monthly/": the nav's "Monthly toolkit", the app shortcut and the district
  // report editor, #report) AND this month's page; then Contribute, the Shop, Published writers, the
  // optional pages and each GVR / RLV 101 lesson (what a GVR opens at a district meeting in a church basement).
  const save = ["", "meetings/", "monthly/", "monthly/{month}/", "contribute/", "shop/", "published/"];
  for (const group of OPTIONAL) {
    const hit = group.find((p) => urls.has("/" + p));
    if (hit) save.push(hit);
  }
  for (const l of data.orientation?.lessons || []) {
    const p = `orientation/${l.id}/`;
    if (l.id && urls.has("/" + p) && !save.includes(p)) save.push(p);
  }
  // …and, with the GVR 101 hub, its workshop presentations (their JSON: no page of their own, so not in
  // the collections — src/pages/presentations-json.11ty.js writes one per deck)
  const files = [];
  if (save.includes("orientation/")) {
    for (const d of data.presentations?.decks || []) {
      const p = String(d.url || "").replace(/^\/+/, "");
      if (/^orientation\/presentations\/[a-z0-9-]+\.json$/.test(p) && !files.includes(p)) files.push(p);
    }
  }
  // …and, with Published writers, the rest of Texas of its writers archive (both languages, like the decks)
  if (urls.has("/published/")) files.push("published/texas-archive.json", "es/published/texas-archive.json");

  const a = (p) => base + p;
  const offline = { en: a("offline/"), es: a("es/offline/") };
  const required = [a(`assets/css/main.css?v=${v}`), a(`assets/js/app.js?v=${v}`), a(`assets/js/pwa.js?v=${v}`), offline.en, offline.es];
  const shell = [
    ...required,
    // the time-zone math (window.GVTime): a saved page rolls the next meeting on with it — optional (without it the
    // pages keep the dates they were built with)
    a(`assets/js/central-time.js?v=${v}`),
    a(`assets/js/install-core.js?v=${v}`),
    a(`assets/js/hero-canvas.js?v=${v}`),
    a(`assets/vendor/alpine.min.js?v=${v}`),
    a("assets/fonts/inter-latin-wght-normal.woff2"),
    a("assets/fonts/fraunces-latin-opsz-normal.woff2"),
    a("assets/img/logo-wide.png"),
    a("assets/img/logo-32x32.png"),
    a("assets/img/app-icon-192.png"),
    a("favicon.ico"),
  ];

  // (relative to the base, like `save` and `files`; one show and one media folder for both languages)
  const booth = { media: "about/booth/media/", json: "about/booth.json" };

  const config = { version: v, base, shell, required, offline, save, files, booth };
  const core = fs.readFileSync(path.join("src", "_includes", "pwa", "sw-core.js"), "utf8");
  return `/* NETA 65 Grapevine / La Viña — service worker, version ${v}. Generated from src/pages/sw.11ty.js. */\n` +
    `const CONFIG = ${JSON.stringify(config, null, 2)};\n\n${core}`;
}
