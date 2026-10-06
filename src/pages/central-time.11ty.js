// /assets/js/central-time.js — the browser's copy of the site's Central-time helper, eleventy/central-time.js
// (the build imports that file itself): the same code as a plain script that defines window.GVTime, with the
// site's zone from window.SITE.tz (base.njk: config/site.yml site.timezone). base.njk loads it right before
// app.js (GV.nextMeeting, the calendar files, the meeting lines on /gvr/ and /about/) and committee.js (the
// countdown, the weekly open meetings); the service worker keeps it for offline use (sw.11ty.js shell).
// The module must end with ONE `export { name, … };` list (no `export` anywhere else, no "as"): the build
// stops otherwise, rather than ship a script that would not run. Whole-line comments are left out (the file
// comes with every page).
import fs from "node:fs";
import path from "node:path";

export const data = {
  permalink: "/assets/js/central-time.js",
  eleventyExcludeFromCollections: true,
  layout: false,
};

const SOURCE = path.join("eleventy", "central-time.js");

export function browserScript(file = SOURCE) {
  const src = fs.readFileSync(file, "utf8").replace(/\r\n?/g, "\n");
  const list = /^export\s*\{([^}]*)\};?[ \t]*$/m.exec(src);
  const rest = list ? src.slice(0, list.index) + src.slice(list.index + list[0].length) : src;
  if (!list || /^\s*export\b/m.test(rest) || /\bas\b/.test(list[1])) {
    throw new Error(`${file}: end it with one plain \`export { name, … };\` list — the browser copy is made from it`);
  }
  const names = list[1].split(",").map((s) => s.trim()).filter(Boolean);
  const body = rest
    .replace(/^[ \t]*\/\*[\s\S]*?\*\/[ \t]*\n/gm, "")   // block comments that start a line
    .replace(/^[ \t]*\/\/.*\n/gm, "")                    // whole-line // comments
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  return "/* NETA 65 Grapevine / La Viña — Central time (window.GVTime). Generated from eleventy/central-time.js by src/pages/central-time.11ty.js. */\n" +
    "(function (root) {\n\"use strict\";\n" + body + "\n\n" +
    "setZone(root.SITE && root.SITE.tz);\n" +
    "root.GVTime = { " + names.map((n) => `${n}: ${n}`).join(", ") + " };\n" +
    "})(typeof window !== \"undefined\" ? window : this);\n";
}

export function render() {
  return browserScript();
}
