// The site's icons: the {% icon %} shortcode (eleventy.config.js) and the filters that draw icons in their own
// markup (eleventy/filters/committee.js). Lucide (lucide-static), or our own art in src/_includes/icons/<name>.svg
// (brands, custom art), which wins.
// Each icon is drawn ONCE per page, from an SVG sprite: an icon is a small <svg> that points at its drawing —
//   <svg class="icon size-5" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none"
//        stroke="currentColor" …><use href="#i-calendar"/></svg>
// — and iconSprite() (run on each finished page: the iconSprite transform, eleventy.config.js) puts the drawings, one
// <symbol id="i-<name>"> each, in one hidden <svg> at the start of <body>: only the icons that page points at, in
// its markup, its <template>s and its inline JSON alike, so the copies the scripts make of the page's icons (Alpine
// templates, the Tracker's and the booth's icon lists) draw too, offline as well.
// The file's own attributes stay on the small <svg>, so CSS on .icon still reaches the drawing (colour,
// stroke-width, fill: the posters' motifs). A label makes the icon a picture with that name (role="img",
// aria-label: text, escaped here); without one it is decoration (aria-hidden).
// A <use> draws only in the page that holds the sprite: markup copied out of the page as it is (a poster turned
// into a picture, src/assets/js/monthly.js) needs the drawings put back inline first.
// (The same idea as the older sprites of single pages — Listen, Watch and Instagram's {% micon %}, Read's {% ricon %},
// Published writers' pwIcon, What's New's cmUse —, which keep their own symbols.)
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const LUCIDE_DIR = path.join(path.dirname(require.resolve("lucide-static/package.json")), "icons");
const NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
// href="#i-…" in markup, in a JSON string (\"), in an escaped attribute value (&quot;)
const REF = /href=(?:"|'|\\"|&quot;|&#34;)#i-([a-z0-9]+(?:-[a-z0-9]+)*)/g;
const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const escAttr = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);
const cache = new Map();

/** name → { attrs: the file's <svg> attributes (no class, no xmlns, no 24 × 24 size), viewBox, body: the drawing }
    | null (not a name, or no such icon). */
export function iconParts(name) {
  if (cache.has(name)) return cache.get(name);
  let parts = null;
  const local = path.join("src/_includes/icons", `${name}.svg`);
  const file = !NAME.test(name) ? "" : fs.existsSync(local) ? local : path.join(LUCIDE_DIR, `${name}.svg`);
  const m = file && fs.existsSync(file) ? /<svg\b([^>]*)>([\s\S]*)<\/svg>/i.exec(fs.readFileSync(file, "utf8").replace(/<!--.*?-->/gs, "")) : null;
  if (m) {
    const attrs = m[1].replace(/\s(?:class|xmlns(?::\w+)?)="[^"]*"/g, "").replace(/\s(?:width|height)="24"/g, "").replace(/\s+/g, " ").trimEnd();
    parts = { attrs, viewBox: (/\sviewBox="[^"]*"/.exec(attrs) || [""])[0], body: m[2].replace(/>\s+</g, "><").trim() };
  }
  cache.set(name, parts);
  return parts;
}

/** One icon: the small <svg> pointing at the page's sprite — "" for an unknown name. cls: its classes after
    "icon"; label: its name for a screen reader (else it is decoration). */
export function iconSvg(name, cls = "size-5", label = "") {
  const n = String(name ?? "");
  const icon = iconParts(n);
  if (!icon) return "";
  const a11y = label ? `role="img" aria-label="${escAttr(label)}"` : `aria-hidden="true" focusable="false"`;
  return `<svg class="icon ${escAttr(cls ?? "")}" ${a11y}${icon.attrs}><use href="#i-${n}"/></svg>`;
}

/** A page with its sprite: the <symbol>s of every icon it points at, in one hidden <svg> right after <body> (before
    every icon, so each draws as soon as it arrives on a weak signal). A page that points at none is returned as it
    is, and so is one that has its sprite already (its <svg data-icon-sprite>: the words alone, in a script or a
    how-to, don't count). <body>'s end is found past quoted attribute values (an x-data="… a > b …" holds a ">"). */
const SPRITE = /<svg data-icon-sprite[\s>]/;
const BODY = /<body\b(?:[^>"']|"[^"]*"|'[^']*')*>/i;
export function iconSprite(html) {
  if (SPRITE.test(html)) return html;
  const symbols = [...new Set(Array.from(html.matchAll(REF), (m) => m[1]))].sort()
    .map((n) => { const p = iconParts(n); return p ? `<symbol id="i-${n}"${p.viewBox}>${p.body}</symbol>` : ""; }).join("");
  if (!symbols) return html;
  const sprite = `<svg data-icon-sprite xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true" focusable="false">${symbols}</svg>`;
  const body = BODY.exec(html);
  return body ? html.slice(0, body.index + body[0].length) + sprite + html.slice(body.index + body[0].length) : html + sprite;
}
