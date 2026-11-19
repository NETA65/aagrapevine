// /llms.txt (English) and /es/llms.txt (Spanish) — since round 35: a short plain-text guide to the site for AI tools,
// in the llms.txt layout (llmstxt.org): "# <the site's name>", a "> " summary of who runs the site, the committee's
// monthly meetings as rules, then "## " lists of the main pages (src/_data/nav.js), each with that page's own meta
// description, and last the other language's file.
//
// Honest about what it is worth: Google says Google Search does not use llms.txt — it "will neither harm nor help"
// (Search Central, June 2026) — and no major AI platform (OpenAI, Anthropic, Perplexity, Google, Meta) has said it
// reads one; coding and agent tools do. It is made at every build from the same settings and strings as the pages,
// so it never goes stale, and it costs nothing: kept out of the collections, so out of the sitemap, IndexNow, the
// search index and the offline worker's list; never an [seo] problem (eleventy/seo-check.js reads .html pages only).
// GitHub Pages sends a .txt file as text/plain, UTF-8 here.
//
// The site's rules hold here as in the structured data (base.njk): no person's name (never a guest speaker), and how
// to join an online meeting — its link, its meeting ID or code, a passcode — stays on the pages for people, never in
// this machine-readable copy: the meetings are rules and times only ("online"), and the Meetings page is linked like
// every other page. Plain facts, attraction rather than promotion. Every link is absolute, on the site's address
// (site.url): only pages that are built (a page missing from this build is left out); outside addresses only in the
// summary (the Area's, the magazines' own sites — config/site.yml). tests/test_r35_head.py checks all of it.
// (Not named "sitemap…": ONLY=sitemap test builds pick src/pages files by the start of their names.)
import { monthlyRule, TZ } from "../../eleventy.config.js";
import { recurrenceText } from "../../eleventy/filters/committee.js";
import { ymdOf } from "../../eleventy/central-time.js";

export const data = {
  pagination: { data: "languages", size: 1, alias: "lang" },
  permalink: (data) => (data.lang === "en" ? "/llms.txt" : `/${data.lang}/llms.txt`),
  eleventyExcludeFromCollections: true,
  layout: false,
};

// The few words only this file says (the rest are the site's strings: src/_i18n).
const WORDS = {
  summary: {
    en: "The website of the {committee} of Alcoholics Anonymous (AA), a service committee of {area} ({area_link}). It shares the stories, podcasts and videos of AA Grapevine and La Viña, AA's magazines — \"our meeting in print\" — and service tools for AA groups, districts and their Grapevine and La Viña representatives (GVRs and RLVs), in English and Spanish. It is not the official site of AA Grapevine, Inc. or of Alcoholics Anonymous World Services, Inc. (A.A.W.S.): the magazines' own sites are {gv_link} and {lv_link}.",
    es: "El sitio web del {committee} de Alcohólicos Anónimos (AA), un comité de servicio del {area} ({area_link}). Comparte las historias, los podcasts y los videos de La Viña y AA Grapevine, las revistas de AA — «nuestra reunión impresa» — y recursos de servicio para los grupos y distritos de AA y sus representantes de La Viña y de Grapevine (RLV y GVR), en español y en inglés. No es el sitio oficial de AA Grapevine, Inc. ni de Alcoholics Anonymous World Services, Inc. (A.A.W.S.): los sitios propios de las revistas son {lv_link} y {gv_link}.",
  },
  meetings: {
    en: "The committee's monthly meetings are online and open to all AA members; how to join is on the Meetings page (below):",
    es: "Las reuniones mensuales del comité son en línea y abiertas a todos los miembros de AA; cómo unirse está en la página de Reuniones (abajo):",
  },
  contact: { en: "Contact: {email}.", es: "Contacto: {email}." },
  online: { en: "online", es: "en línea" },
  from: { en: "first meeting {date}", es: "primera reunión el {date}" },
  main: { en: "Main pages", es: "Páginas principales" },
  optional: { en: "Optional", es: "Opcional" },
  sitemap: { en: "Sitemap", es: "Mapa del sitio" },
  sitemap_desc: {
    en: "every page of the site, in English and Spanish, with the date each one last changed.",
    es: "todas las páginas del sitio, en español y en inglés, con la fecha en que cambió cada una.",
  },
  other: { en: "En español", es: "In English" },
  other_desc: {
    en: "this guide for the site's pages in Spanish (/es/).",
    es: "esta guía para las páginas del sitio en inglés.",
  },
};
const word = (k, lang, vars = {}) => String(WORDS[k][lang] ?? WORDS[k].en).replace(/\{(\w+)\}/g, (m, v) => (v in vars ? vars[v] : m));

// Where an online meeting is held, by its link's host — the platform's name only, never the link itself.
const PLATFORMS = [[/(^|\.)meet\.google\.com$/i, "Google Meet"], [/(^|\.)zoom\.us$/i, "Zoom"], [/(^|\.)teams\.microsoft\.com$/i, "Microsoft Teams"]];
function platformOf(url) {
  try {
    const host = new URL(String(url)).hostname;
    return (PLATFORMS.find(([re]) => re.test(host)) || [null, ""])[1];
  } catch {
    return "";
  }
}

// One line of text: no markup, no line breaks, no Markdown that would start a link.
const oneLine = (s) => String(s ?? "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").replace(/[[\]]/g, "").trim();

export function render(data) {
  const { site, lang, nav, collections } = data;
  const t = (key, vars) => this.t(key, lang, vars);
  const abs = (u) => this.siteUrl(u, site);
  const local = (u) => this.lurl(u, lang);
  // the built pages by address, each language's: their data says their description, as base.njk prints it. (A page
  // made for both languages is in the collections once, as its first — English — page: its pagination.hrefs name
  // both addresses, and its descKey is the same in both; the sitemap reads them the same way.)
  const built = new Map();
  for (const p of collections?.all || []) {
    for (const u of p.data?.pagination?.hrefs || [p.url]) if (u && !built.has(u)) built.set(u, p);
  }
  const descOf = (p) => {
    const d = p.data || {};
    if (d.descKey) return oneLine(t(d.descKey, { platform: site.meeting?.platform || "Zoom" }));
    return oneLine(d.description || t("site.description"));
  };
  const item = (label, url) => {
    const p = built.get(url);
    if (!p || p.data?.noindex || p.data?.sitemap === false) return null;
    return `- [${oneLine(label)}](${abs(url)}): ${descOf(p)}`;
  };
  const md = (label, href) => `[${label}](${href})`;
  const out = [];

  // the site's name (base.njk's WebSite name) and who runs it
  out.push(`# ${site.title} — NETA 65`, "");
  const host = (u) => String(u || "").replace(/^https?:\/\/(?:www\.)?/, "").replace(/\/+$/, "");
  out.push("> " + word("summary", lang, {
    committee: lang === "es" ? site.committee_es || site.committee : site.committee,
    area: lang === "es" ? site.area_es || site.area : site.area,
    area_link: site.area_website ? md(host(site.area_website), site.area_website) : "NETA 65",
    gv_link: md(host(site.links?.gv_home || "https://www.aagrapevine.org"), site.links?.gv_home || "https://www.aagrapevine.org"),
    lv_link: md(host(site.links?.lv_home || "https://www.aalavina.org"), site.links?.lv_home || "https://www.aalavina.org"),
  }) + (site.contact_email ? " " + word("contact", lang, { email: site.contact_email }) : ""), "");

  // the committee's own monthly meetings online, as rules (config/site.yml meeting: and the recurring_events that
  // are ours and online) — times and days only, read the way the pages read them (monthlyRule: "7:00 PM" or
  // "sábado" count; presentations.js and bingo.js do the same)
  const meetings = [];
  const ruleLine = (name, rule, platform, extra = "") => {
    let when = recurrenceText(rule, lang);
    if (!when) return;
    when = when.charAt(0).toLowerCase() + when.slice(1);          // after a colon: "every third Wednesday …"
    const where = word("online", lang) + (platform ? ` (${platform})` : "");
    meetings.push(`- ${oneLine(name)}: ${when}, ${where}${extra ? `, ${extra}` : ""}.`);
  };
  const m = site.meeting || {};
  if (Object.keys(m).length) ruleLine(t("nav.meeting"), monthlyRule(m), m.platform || platformOf(m.online_url));
  // a series still to start says its first date until that day comes — the build's day in Central time (site.built,
  // as the pages read it), never the UTC date, which turns at 6 or 7 PM the evening before
  const today = ymdOf(Date.parse(site.built || "") || Date.now(), TZ);
  for (const r of site.recurring_events || []) {
    if (!r || typeof r !== "object" || r.enabled === false || (r.host && r.host !== "neta") || !r.online_url || r.location) continue;
    const starts = /^\d{4}-\d{2}-\d{2}$/.test(String(r.starts || "")) ? String(r.starts) : "";
    const first = starts > today
      ? word("from", lang, { date: new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", { dateStyle: "long", timeZone: "UTC" }).format(new Date(`${starts}T12:00:00Z`)) })
      : "";
    const name = (lang === "es" && r.title_es) || r.title;
    if (name) ruleLine(name, monthlyRule(r, true), platformOf(r.online_url), first);
  }
  if (meetings.length) out.push(word("meetings", lang), "", ...meetings, "");

  // the pages, as the menus group them: the top-level ones, then each menu, then the footer's
  const main = [item(t("nav.home"), local("/"))];
  const groups = [];
  for (const it of nav.primary || []) {
    if (it.url) main.push(item(t(it.key), local(it.url)));
    else if (it.children) groups.push([t(it.key), it.children.map((c) => item(t(c.key), local(c.url)))]);
  }
  groups.unshift([word("main", lang), main]);
  groups.push([t("nav.more"), (nav.footer || []).map((f) => item(t(f.key), local(f.url)))]);
  for (const [title, lines] of groups) {
    const kept = lines.filter(Boolean);
    if (kept.length) out.push(`## ${oneLine(title)}`, "", ...kept, "");
  }

  // last: the sitemap and the other language's guide
  const other = lang === "es" ? "en" : "es";
  out.push(`## ${word("optional", lang)}`, "");
  out.push(`- [${word("sitemap", lang)}](${abs("/sitemap.xml")}): ${word("sitemap_desc", lang)}`);
  out.push(`- [${word("other", lang)}](${abs(other === "en" ? "/llms.txt" : `/${other}/llms.txt`)}): ${word("other_desc", lang)}`);
  return out.join("\n") + "\n";
}
