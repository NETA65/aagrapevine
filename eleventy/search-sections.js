// Round 37 · the SECTIONS of the site's long pages that the site search finds on their own (eleventy/filters/library.js
// searchIndex, kind "section"): a search for "booth display", "exhibidor", "FAQ", "New to AA?" or "ASL" lands on the
// section itself (/about/#booth-title …), not on the top of a long page where the visitor still has to look for it.
// One line per section — the page, the heading's id on it, the i18n key of the heading's own words (so a result says
// what the visitor will see), optionally the key of the line under it (the result's snippet) and a few more words it is
// found by (search.sec.<id>.x, in src/_i18n/library.json: both languages are searched, as for the site's pages).
// A plain list (no Eleventy registration: this file is not in eleventy/filters/, whose files are loaded as plugins and
// whose filters must all be used — test_unused_code). Keys are written out in full: test_unused_code counts a key as
// read when the code names it.
//
//   id      the entry's id in the index ("section:<id>") — unique
//   page    the page's path in English ("/about/": the Spanish index adds /es itself)
//   anchor  the id of the heading (or of the section) on that page: the [search] check (eleventy/seo-check.js
//           searchProblems) says so when a page no longer has it — a heading renamed or removed
//   title   the heading's i18n key (the page's own words) — titleVars(ctx): its {placeholders}, as the page fills them
//   sub     the line under it (the result's snippet), or "" — subVars(ctx) likewise
//   x       the i18n key of the other words it is found by ("" none)
//   icon    the result's icon (it must be in search.njk's ss-icons, as every icon an entry names)
//   shown   optional, shown(ctx): false when the page leaves the section out (its heading shows only with data: the
//           history's with config/history.yml's milestones) — then it has no entry either, and nothing to check
// ctx (library.js): { orientation, history } — src/_data/orientation.js's lessons (their minutes), src/_data/history.js
// (config/history.yml: its items; null when it cannot be read — the section then counts as shown).
//
// Add a section: a line here, its search.sec.<id>.x key in both languages, and — if its icon is new — the icon in
// src/pages/search.njk's ss-icons. tests/test_site_search.py checks every line against the built pages: the anchor
// exists and the entry's title is that heading's words, in both languages (a line whose shown(ctx) says the page
// leaves it out: not looked for).

export const SEARCH_SECTIONS = Object.freeze([
  // About
  { id: "about-magazines", page: "/about/", anchor: "mags-title", title: "read.about.mags_title", sub: "read.about.mags_sub", x: "search.sec.about-magazines.x", icon: "book-open" },
  { id: "about-booth", page: "/about/", anchor: "booth-title", title: "booth.title", sub: "booth.sub", x: "search.sec.about-booth.x", icon: "monitor-play" },
  // (about.njk shows the history only with milestones: `{% if H.items.length %}`)
  { id: "about-history", page: "/about/", anchor: "history-title", title: "read.about.hist_title", sub: "search.sec.about-history.s", x: "search.sec.about-history.x", icon: "history",
    shown: (ctx) => !ctx?.history || !!(Array.isArray(ctx.history.items) && ctx.history.items.length) },
  { id: "about-committee", page: "/about/", anchor: "committee-title", title: "read.about.com_title", sub: "read.about.com_p1", x: "search.sec.about-committee.x", icon: "users" },
  { id: "about-privacy", page: "/about/", anchor: "privacy-title", title: "read.about.privacy_title", sub: "read.about.privacy1", x: "search.sec.about-privacy.x", icon: "shield-check" },
  // Read
  { id: "read-print", page: "/read/", anchor: "print-title", title: "read.print_title", sub: "read.print_text", x: "search.sec.read-print.x", icon: "heart-handshake" },
  // GVR / RLV corner
  { id: "gvr-position", page: "/gvr/", anchor: "position-title", title: "read.gvr.job_title", sub: "read.gvr.job_text", x: "search.sec.gvr-position.x", icon: "hand-heart" },
  { id: "gvr-steps", page: "/gvr/", anchor: "steps-title", title: "read.gvr.steps_title", sub: "read.gvr.steps_sub", x: "search.sec.gvr-steps.x", icon: "list-checks" },
  { id: "gvr-kits", page: "/gvr/", anchor: "kits-title", title: "read.gvr.kits_title", sub: "read.gvr.kits_sub", x: "search.sec.gvr-kits.x", icon: "folder-open" },
  { id: "gvr-ideas", page: "/gvr/", anchor: "ideas-title", title: "read.gvr.ideas_title", sub: "read.gvr.ideas_sub", x: "search.sec.gvr-ideas.x", icon: "lightbulb" },
  { id: "gvr-pass", page: "/gvr/", anchor: "pass-title", title: "read.gvr.pass_title", sub: "read.gvr.pass_sub", x: "search.sec.gvr-pass.x", icon: "handshake" },
  // Share your story
  { id: "contribute-submit", page: "/contribute/", anchor: "submit-title", title: "read.contrib.how_title", sub: "read.contrib.how_sub", x: "search.sec.contribute-submit.x", icon: "send" },
  { id: "contribute-record", page: "/contribute/", anchor: "record-title", title: "community.rec.title", sub: "community.rec.sub", x: "search.sec.contribute-record.x", icon: "mic" },
  { id: "contribute-deadlines", page: "/contribute/", anchor: "deadlines-title", title: "read.contrib.deadlines_title", sub: "read.contrib.deadlines_sub", x: "search.sec.contribute-deadlines.x", icon: "calendar-clock" },
  { id: "contribute-tips", page: "/contribute/", anchor: "tips-title", title: "read.contrib.tips_title", sub: "read.contrib.tips_sub", x: "search.sec.contribute-tips.x", icon: "lightbulb" },
  { id: "contribute-anonymity", page: "/contribute/", anchor: "anon-title", title: "read.contrib.anon_title", sub: "read.contrib.anon_text", x: "search.sec.contribute-anonymity.x", icon: "shield-check" },
  { id: "contribute-workshop", page: "/contribute/", anchor: "workshop-title", title: "read.contrib.ws_title", sub: "read.contrib.ws_text", x: "search.sec.contribute-workshop.x", icon: "users" },
  { id: "contribute-faq", page: "/contribute/", anchor: "faq-title", title: "read.contrib.faq_title", sub: "read.contrib.faq_sub", x: "search.sec.faq.x", icon: "circle-help" },
  // …and its six questions (the page's FAQ, read.contrib.faq1_q … faq6_a — its FAQPage markup too, base.njk ldFaq):
  // each found by its own words, all six landing on the FAQ (#faq: they open there)
  { id: "faq1", page: "/contribute/", anchor: "faq", title: "read.contrib.faq1_q", sub: "read.contrib.faq1_a", x: "search.sec.faq.x", icon: "circle-help" },
  { id: "faq2", page: "/contribute/", anchor: "faq", title: "read.contrib.faq2_q", sub: "read.contrib.faq2_a", x: "search.sec.faq.x", icon: "circle-help" },
  { id: "faq3", page: "/contribute/", anchor: "faq", title: "read.contrib.faq3_q", sub: "read.contrib.faq3_a", x: "search.sec.faq.x", icon: "circle-help" },
  { id: "faq4", page: "/contribute/", anchor: "faq", title: "read.contrib.faq4_q", sub: "read.contrib.faq4_a", x: "search.sec.faq.x", icon: "circle-help" },
  { id: "faq5", page: "/contribute/", anchor: "faq", title: "read.contrib.faq5_q", sub: "read.contrib.faq5_a", x: "search.sec.faq.x", icon: "circle-help" },
  { id: "faq6", page: "/contribute/", anchor: "faq", title: "read.contrib.faq6_q", sub: "read.contrib.faq6_a", x: "search.sec.faq.x", icon: "circle-help" },
  // Meetings
  { id: "meetings-new-to-aa", page: "/meetings/", anchor: "new-to-aa-h", title: "newcomer.title", sub: "newcomer.text", x: "search.sec.meetings-new-to-aa.x", icon: "hand-heart" },
  // Accessibility
  { id: "accessibility-asl", page: "/accessibility/", anchor: "asl-title", title: "access.asl_title", sub: "access.asl_sub", x: "search.sec.accessibility-asl.x", icon: "hand" },
  { id: "accessibility-captions", page: "/accessibility/", anchor: "captions-title", title: "access.cap_title", sub: "access.cap_sub", x: "search.sec.accessibility-captions.x", icon: "captions" },
  { id: "accessibility-phone", page: "/accessibility/", anchor: "phone-title", title: "access.ph_title", sub: "access.ph_sub", x: "search.sec.accessibility-phone.x", icon: "phone" },
  { id: "accessibility-print", page: "/accessibility/", anchor: "print-title", title: "access.pr_title", sub: "access.pr_sub", x: "search.sec.accessibility-print.x", icon: "printer" },
  { id: "accessibility-audio", page: "/accessibility/", anchor: "audio-title", title: "access.aud_title", sub: "access.aud_sub", x: "search.sec.accessibility-audio.x", icon: "headphones" },
  { id: "accessibility-feedback", page: "/accessibility/", anchor: "feedback-title", title: "access.fb_title", sub: "access.fb_sub", x: "search.sec.accessibility-feedback.x", icon: "accessibility" },
  // GVR / RLV 101 (its six sessions have entries of their own: library.js, orientation; the presentations too)
  { id: "orientation-presenting", page: "/orientation/", anchor: "presenting-title", title: "orientation.pres_how_title", sub: "orientation.pres_how_sub", x: "search.sec.orientation-presenting.x", icon: "lightbulb" },
  // (the minutes as orientation.njk adds them up: its welcomeMin + the sessions' minutes + its closeMin, 3 + … + 3)
  { id: "orientation-facilitators", page: "/orientation/", anchor: "facilitators-title", title: "orientation.trainers_title",
    titleVars: (ctx) => ({ n: 3 + (Number(ctx?.orientation?.totalMinutes) || 0) + 3 }), sub: "orientation.trainers_sub",
    x: "search.sec.orientation-facilitators.x", icon: "users" },
  // Shop
  { id: "shop-subscriptions", page: "/shop/", anchor: "subs-title", title: "shop.subs_title", sub: "shop.subs_sub", x: "search.sec.shop-subscriptions.x", icon: "badge-dollar-sign" },
  { id: "shop-carry", page: "/shop/", anchor: "ctm-title", title: "read.subs.ctm_title", sub: "read.subs.ctm_text", x: "search.sec.shop-carry.x", icon: "gift" },
  { id: "shop-group", page: "/shop/", anchor: "group-title", title: "read.subs.group_title", sub: "read.subs.group_sub", x: "search.sec.shop-group.x", icon: "users" },
  { id: "shop-catalogs", page: "/shop/", anchor: "cat-title", title: "read.subs.cat_title", sub: "read.subs.cat_sub", x: "search.sec.shop-catalogs.x", icon: "book-open" },
  { id: "shop-help", page: "/shop/", anchor: "help-title", title: "read.subs.help_title", sub: "read.subs.help_text", x: "search.sec.shop-help.x", icon: "phone" },
]);
