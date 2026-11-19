// /orientation/presentations/<id>.json — one presentation (a workshop or the committee meeting) for the player on
// /orientation/ (src/assets/js/presentations*.js): the deck as written in config/presentations/<id>.yml, with
// today's facts filled in from the site's data — the next committee meetings, story deadlines, prices, events … —
// so a deck stays current with every build (the daily content sync rebuilds the site). One file per deck of
// `presentations.decks` (src/_data/presentations.js); no decks, no files. The shape (SPEC §2) and every field are
// made by eleventy/filters/presentations.js deckJson:
//   { app: "gv-presentation", schema: 1, id, lang, title, short, eyebrow, footer, minutes, built, as_of, version,
//     site: { url, host }, drive: { view, date } | null, presets, fillins, live: { <key>: text | { value, steps?:
//     [{ from, value }], until?, fallback? } }, slides: [{ id, layout, h, n_default, part, accent (the one it shows),
//     eyebrow, title, …its fields…, notes, minutes, version_minutes ({ <preset id>: minutes }), optional, starts_off,
//     facilitator, handout, print ("portrait" | "landscape" for a handout page, else null), version_notes,
//     version_fields ({ <preset id>: { <field>: value } }), show_from, show_until, when, lang ("en" | "es"),
//     data (a live slide's rows — every one known within about a year — and its `limit`; an event row's `series`,
//     a deadline's or an issue's `gloss_machine`) }] }
// A fact's steps say what it will be next, so a copy opened days later (saved for offline) still reads right.
// Not a page: it is left out of the collections — so of the sitemap, the service worker's page list and every
// list built from them; the search index and the feeds are built from the site's data, never from these files.
// The page fetches it on demand (the service worker keeps a copy: network first).
export default class PresentationsJson {
  data() {
    return {
      pagination: { data: "presentations.decks", size: 1, alias: "deck" },
      permalink: (data) => `/orientation/presentations/${data.deck.id}.json`,
      eleventyExcludeFromCollections: true,
      layout: null,
    };
  }

  render(data) {
    return this.presDeckJson(data.deck, data);
  }
}
