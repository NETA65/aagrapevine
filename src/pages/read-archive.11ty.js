// /read-archive.json and /es/read-archive.json — older magazine issues for the
// Read page. The page server-renders the newest issues; everything older is
// fetched from this file only when a visitor taps "Load older issues", so the
// page stays light even after years of daily syncing.
// Short keys keep the file small:
//   issue: id, pub, key, label, ls=label inside a sentence (a story's Share: "— La Viña, septiembre–octubre de 2026";
//          none when undated), topic, tl=topic lang, c=cover (site-relative), u=issue url, h=its host, count, items
//   story: t=title, tl=title lang, o=original title, ol=original lang, u=url, s=section,
//          a=author, f=1 free / 0 subscribers, m=machine-translated, n=new
// The issues the page shows itself are left out: the same number read.njk uses (eleventy/filters/read.js).
// Of those, the page holds each one's first SSR_ROWS stories: the rest of each are here, in `more` — by the issue's
// id, { pub, ls, count, items } (the same short keys), for its "Show all N stories" button (read.js).
import { SSR_ARCHIVE, SSR_ROWS } from "../../eleventy/filters/read.js";

const HUBS = { gv: "https://www.aagrapevine.org/magazine", lv: "https://www.aalavina.org/la-revista" };

const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };

export default class {
  data() {
    return {
      pagination: { data: "languages", size: 1, alias: "lang" },
      permalink: (data) => (data.lang === "en" ? "/read-archive.json" : `/${data.lang}/read-archive.json`),
      layout: false,
      eleventyExcludeFromCollections: true,
    };
  }

  render(data) {
    const lang = data.lang;
    const src = data.site && data.site.sources ? data.site.sources : {};
    const hubs = {
      gv: src.grapevine ? src.grapevine.base + src.grapevine.magazine_hub : HUBS.gv,
      lv: src.lavina ? src.lavina.base + src.lavina.magazine_hub : HUBS.lv,
    };
    const archive = this.readArchive(data.db.articles) || [];
    const older = archive.slice(SSR_ARCHIVE);
    const story = (a) => {
      const o = { t: a.title, tl: a.titleLang, u: a.url };
      if (a.original) { o.o = a.original; o.ol = a.origLang; }
      if (a.section) o.s = a.section;
      if (a.author) o.a = a.author;
      if (a.free === true) o.f = 1;
      else if (a.free === false) o.f = 0;
      if (a.machine) o.m = 1;
      if (a.isNew) o.n = 1;
      return o;
    };
    // the issues the page shows: the stories after its first SSR_ROWS
    const more = {};
    for (const is of archive.slice(0, SSR_ARCHIVE)) {
      const v = this.readIssueView(is, lang);
      if (v.articles.length <= SSR_ROWS) continue;
      const m = { pub: v.pub, count: v.count, items: v.articles.slice(SSR_ROWS).map(story) };
      if (v.label) m.ls = this.readInSentence(v.label, lang, v.pub);
      more[v.id] = m;
    }
    const issues = older.map((is) => {
      const v = this.readIssueView(is, lang);
      const u = v.url || hubs[v.pub] || hubs.gv;
      const out = {
        id: v.id,
        pub: v.pub,
        key: v.key,
        label: v.label || this.t("read.undated", lang),
        topic: v.topic || "",
        tl: v.topicLang || "",
        u,
        h: host(u),
        count: v.count,
        items: v.articles.map(story),
      };
      if (v.label) out.ls = this.readInSentence(v.label, lang, v.pub);
      if (v.cover) out.c = v.cover;
      return out;
    });
    return JSON.stringify({ lang, generated: data.site.built, count: issues.length, issues, more });
  }
}
