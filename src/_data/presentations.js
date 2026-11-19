// The presentations of /orientation/ ("Presentations": three workshops and the committee meeting) —
// config/presentations/<id>.yml, one file per deck (the owner's how-to:
// config/presentations/README.md) — exposed as `presentations` in every template:
//   presentations.decks     [{ id, order, title, short, card: { title, summary, audience } ({en, es} each), minutes,
//                              icon, tone, drive_title, count (slides in the default version, today), parts: [{ n,
//                              title, id }], kinds (what stays current by itself: "meeting", "deadlines", "prices" …),
//                              presets, fillins, url ("/orientation/presentations/<id>.json"),
//                              and, for that file: lang, eyebrow, footer, version, slides }]   by `order`
//   presentations.problems  ["writing-workshop.yml: slide 12 (story-tips): …", …]
// Pages: src/pages/orientation.njk (#presentations: a card per deck) and src/pages/presentations-json.11ty.js (the
// JSON the player opens). Reading, checking and shaping: eleventy/filters/presentations.js loadDecks.
// PRESENTATIONS_DIR=tests/fixtures/presentations reads another folder instead (the sample decks: tests, previews).
// Checks: the rules of tests/test_presentations.py (what the people writing a deck run; SPEC UPDATE 3 included:
// version_fields, {only:…} / {not:…} notes lines, {lang:es}…{/lang}, {ui:…}, text styles, print) — logged, and with
// I18N_STRICT=1 (CI) they fail the build instead (the same rule as config/orientation.yml and config/carry.yml).
// No folder or no deck files: { decks: [], problems: [] } — the site builds as it did without them.
// (Only the default export here: with a named one, Eleventy would hand the pages the module object instead.)
import { loadDecks } from "../../eleventy/filters/presentations.js";

export default function () {
  const dir = process.env.PRESENTATIONS_DIR || "config/presentations";
  const { decks, problems } = loadDecks(dir);
  if (problems.length) {
    const msg = `[presentations] ${dir}: ${problems.length} problem(s):\n  ${problems.join("\n  ")}`;
    if (process.env.I18N_STRICT) throw new Error(msg);
    console.warn(msg);
  }
  return { decks, problems };
}
