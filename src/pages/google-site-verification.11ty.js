// /googlef96fc15466439295.html — Google Search Console's ownership check of the site (a "URL prefix" property for
// https://neta65.github.io/aagrapevine/): Google fetches this address and expects exactly this one line. Keep it while
// the committee uses Search Console (Google drops the verification some time after the file disappears). Another
// Google account that verifies the site gets a file name of its own: add a second template like this one.
// A template, not a copied file: Eleventy would treat a plain .html file in src/ as a page and publish it at
// /googlef96fc15466439295/index.html, where Google does not look.
export const data = {
  permalink: "/googlef96fc15466439295.html",
  eleventyExcludeFromCollections: true,
  layout: false,
};

export function render() {
  return "google-site-verification: googlef96fc15466439295.html";
}
