// The build's warnings: what the log says when something in the code or the content is wrong, though the site
// still builds —
//   [icon] / [community] / [media] / [read] / [published]  an icon that does not exist (or is not in its page's sprite);
//   [sitemap]  a page the sitemap must list is missing (renamed, or left out by mistake);
//   [links]    a link value in data/site that had to be repaired or hidden (src/_data/db.js — mostly a link
//              written by hand in content/events or content/bulletin); a link that only lacked its "https://"
//              ("www.…", "zoom.us/j/…") works once repaired and is a plain "[links] note:" line, not a warning.
// buildWarning() prints each one, as before, and remembers it; at the end of the build eleventy.config.js
// ("eleventy.after") sums them up, each once (an icon missing from the page layout is printed for every page:
// "[icon] missing icon: x (×245)"):
//   STRICT_BUILD=1          the build fails, listing them — the Code check's test build (.github/workflows/check.yml);
//   BUILD_WARNINGS=<file>   they are written there, one per line (an empty file: none) — Website update's
//                           "Check the build" lists them in the run's summary; a warning never stops publishing;
//   on GitHub Actions       each one is also an annotation on the run (an error under STRICT_BUILD, else a warning).
// Notes that are expected are NOT build warnings and stay plain log lines: the booth display's "not downloaded in
// this build" (the Code check never downloads the booth's videos), the [css] sizes, a data file that is missing.
const seen = new Map(); // "[kind] text" → how many times

/** Print a build warning ("[kind] text") and remember it for the end of the build. */
export function buildWarning(kind, text) {
  const line = `[${kind}] ${text}`;
  console.warn(line);
  seen.set(line, (seen.get(line) || 0) + 1);
}

/** The warnings of this build so far, each once, in the order they first came (" (×n)": printed n times). */
export function buildWarnings() {
  return [...seen].map(([line, n]) => (n > 1 ? `${line} (×${n})` : line));
}

/** Start again (after a build has been summed up: `npm start` builds again on every change). */
export function clearBuildWarnings() {
  seen.clear();
}

// A GitHub Actions annotation's text: "%", CR and LF escaped as the runner expects.
const ghText = (s) => String(s).replace(/%/g, "%25").replace(/\r/g, "%0D").replace(/\n/g, "%0A");

/** STRICT_BUILD is on: any value but "", "0", "false", "no" or "off". */
export const isStrict = (env = process.env) => !/^\s*(?:0|false|no|off)?\s*$/i.test(String(env.STRICT_BUILD ?? ""));

/** The end of a build: write the list (BUILD_WARNINGS), annotate the run (GitHub Actions) and, under
    STRICT_BUILD, fail it. Then forget them. `env` = process.env (a test passes its own). */
export function finishBuild(env = process.env, write = null) {
  const list = buildWarnings();
  clearBuildWarnings();
  const strict = isStrict(env);
  if (env.BUILD_WARNINGS && write) write(env.BUILD_WARNINGS, list.length ? list.join("\n") + "\n" : "");
  if (env.GITHUB_ACTIONS === "true") {
    for (const w of list) console.log(`::${strict ? "error" : "warning"} title=Build warning::${ghText(w)}`);
  }
  if (strict && list.length) {
    throw new Error(`STRICT_BUILD: ${list.length} build warning(s) — fix them (or build without STRICT_BUILD):\n  ${list.join("\n  ")}`);
  }
  return list;
}
