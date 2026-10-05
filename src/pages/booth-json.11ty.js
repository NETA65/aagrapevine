// /about/booth.json — the booth display's show: the one file the player on the About page (src/assets/js/booth.js,
// "Booth display" — /about/#booth and /es/about/#booth) fetches, for both languages. Built with every deploy, so its
// live parts are as fresh as the site's data: the daily and morning syncs rebuild it (the next events, both daily
// quotes, the channel's newest short videos, podcast episodes, story themes, prices, the Books of the Month, the
// meetings anyone can join, the bulletin's newest posts), beside the committee's own rows (content/booth/booth.csv)
// and the Drive booth folder's photos, videos and notes (data/site/booth.json, with the copies the deploy saved under
// /about/booth/media/). The shape (SPEC §2.4) and every field are made by eleventy/filters/booth.js boothShow:
//   { app: "gv-booth", schema: 1, version (12 hex characters of the items and the defaults — a running player swaps
//     the show when it changes), built, as_of (the Central day), site: { url, url_es, base, host, committee_en,
//     committee_es }, defaults (config/site.yml booth.defaults as the player's settings), collections, channels
//     ([{ id, count }] — only those with items), events_pick, items (every key of an ITEM, null when not used), qr
//     ({ address: SVG }), problems ([{ where, en, es }] — Settings → Items shows them) }
// The `booth` global (src/_data/booth.js) holds the owner's files, read and checked; this page adds the day's live
// items from the template's data (db, site, meeting).
// Not a page: it is left out of the collections — so of the sitemap, the search index, the feeds and the service
// worker's page list; the player asks the worker to keep it for offline use (BOOTH_SAVE), and fetches it again every
// half hour while it runs online.
export default class BoothJson {
  data() {
    return {
      permalink: "/about/booth.json",
      eleventyExcludeFromCollections: true,
      layout: null,
    };
  }

  render(data) {
    return this.boothJson(data.booth, data);
  }
}
