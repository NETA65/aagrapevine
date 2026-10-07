// /published/texas-archive.json and /es/published/texas-archive.json — the rest of Texas for the Texas
// writers archive on /published/ (#archive). The page renders the Area 65 stories itself (they show without
// JavaScript); the stories by writers from the rest of Texas come from this file, which
// /assets/js/published-archive.js fetches only when a visitor chooses All of Texas or Everyone — so the page
// stays light. Built by eleventy/filters/published.js → pwArchive (the same rows, order and words as the page).
// One row per story, in the page's order; short keys, empty ones left out:
//   o   the story's place in the whole list (the page's own rows carry it as data-o: the rows slot in by it)
//   u   the story's link — only https://www.aagrapevine.org/… or https://www.aalavina.org/…
//   p   magazine: gv | lv
//   t   title as shown; tl its language when it is not the page's
//   g   original title when t is a translation; gl its language; m 1 = t is a machine translation
//   b   the byline's items, ready to show: ["John W.", "Denton, Texas"], or one per writer of a letters
//       column ["Irene H-P. (San Antonio)", "Stacy C. (Horseshoe Bay)"] (w 1 = several writers)
//   c   county ("Denton County" / "Condado de Denton")
//   i   issue ("October 1991"), y year, d decade ("1990" | "undated")
//   h   theme; hl its language when it is not the page's
//   r   the magazine's own subtitle (or its translation); rl its language when it is not the page's;
//       rm 1 = r is a machine translation under a title without m (the subtitle carries the mark then)
//   a   1 = audio version · x 1 = online exclusive · k 1 = letter or short piece
//   s   search words (each once, normalized like the page's data-s: initials together and one by one)
// The page asks for it as texas-archive.json?v=<a fingerprint of this file> (pwArchive's version): a new address
// whenever the rows change, so they always slot into a page built from the same stories.
// Text only, no HTML: published-archive.js puts every value in with textContent.
export default class {
  data() {
    return {
      pagination: { data: "languages", size: 1, alias: "lang" },
      permalink: (data) => (data.lang === "en" ? "/published/texas-archive.json" : `/${data.lang}/published/texas-archive.json`),
      layout: false,
      eleventyExcludeFromCollections: true,
    };
  }

  render(data) {
    const A = this.pwArchive(data.db, data.lang);
    return JSON.stringify({ v: 1, lang: data.lang, count: A.json.length, items: A.json });
  }
}
