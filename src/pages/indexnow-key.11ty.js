// /<key>.txt — the IndexNow key file (https://www.indexnow.org/documentation). After each publish, Website update
// (.github/workflows/update.yml, "Tell search engines which pages changed (IndexNow)") sends Bing, Yandex and the
// other IndexNow engines the pages whose content changed (eleventy/lastmod.js); an engine fetches this file to see
// that the list comes from the site: it holds exactly the key, nothing else. In the site's folder
// (/aagrapevine/<key>.txt), which covers every address under it — the request names it ("keyLocation").
// The key is config/site.yml site.search_engines.indexnow_key: public by design (it only proves that this site
// sent the list), so it is not a GitHub secret. Empty or missing: no file, and the workflow sends nothing. A key
// IndexNow would refuse (not 8–128 letters, digits or dashes): no file either — the workflow's step says so in
// the run's summary.
// A template, not a copied file, so the file follows the setting.
const KEY = /^[A-Za-z0-9-]{8,128}$/;

/** The site's IndexNow key, or "" (none, or not one IndexNow accepts). */
export function indexNowKey(site) {
  const key = String(site?.search_engines?.indexnow_key ?? "").trim();
  return KEY.test(key) ? key : "";
}

export const data = {
  permalink: (data) => {
    const key = indexNowKey(data.site);
    return key ? `/${key}.txt` : false;
  },
  eleventyExcludeFromCollections: true,
  layout: false,
};

export function render(data) {
  return indexNowKey(data.site);
}
