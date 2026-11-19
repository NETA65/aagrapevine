// /opensearch.xml (English) and /es/opensearch.xml (Spanish) — OpenSearch descriptions: they let a browser offer the
// site's own search as a search engine of its own ("Add search engine" in Firefox, a keyword in Chrome's address bar
// once the site was searched). base.njk names the page language's file on every page (<link rel="search">), so a
// Spanish page offers the Spanish search: /es/search/?q=… (src/assets/js/search.js reads ?q=). Each language has its
// own name (site.search_engine_name, 16 characters at most — OpenSearch's ShortName), so a bilingual visitor can
// keep both. Absolute addresses (site.url): the browser keeps this file and uses it away from the site; the HTML
// base plugin never rewrites an XML file. (Not named "sitemap…": ONLY=sitemap test builds pick src/pages files by
// the start of their names.)
import { escapeXml as x } from "../../eleventy/filters/community.js";

export const data = {
  pagination: { data: "languages", size: 1, alias: "lang" },
  permalink: (data) => (data.lang === "en" ? "/opensearch.xml" : `/${data.lang}/opensearch.xml`),
  eleventyExcludeFromCollections: true,
  layout: false,
};

export function render(data) {
  const { site, lang } = data;
  const t = (key) => this.t(key, lang);
  const abs = (u) => this.siteUrl(u, site);
  const home = lang === "en" ? "/" : `/${lang}/`;
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">',
    `  <ShortName>${x(t("site.search_engine_name"))}</ShortName>`,
    `  <Description>${x(t("search.meta_desc"))}</Description>`,
    `  <Url type="text/html" method="get" template="${x(abs(`${home}search/`))}?q={searchTerms}"/>`,
    `  <Url type="application/opensearchdescription+xml" rel="self" template="${x(abs(`${home}opensearch.xml`))}"/>`,
    `  <Image width="32" height="32" type="image/png">${x(abs("/assets/img/logo-32x32.png"))}</Image>`,
    `  <Language>${lang === "es" ? "es-US" : "en-US"}</Language>`,
    "  <InputEncoding>UTF-8</InputEncoding>",
    "</OpenSearchDescription>",
  ].join("\n") + "\n";
}
