// Serve a built website folder the way GitHub Pages does — for the browser checks (tests/browser) and the monthly
// posters' share pictures (scripts/ops/poster_share.py), on this computer only (127.0.0.1):
//
//   node scripts/ops/serve_site.mjs <built site folder> [--port N] [--prefix /aagrapevine/] [--overrides file.json]
//
// It prints ONE line once it listens — "serving <folder> at http://127.0.0.1:<port>/aagrapevine/" — and serves until
// it is stopped. --port 0 (the default) takes any free port (the line says which). --prefix is the site's folder on
// GitHub Pages (PATH_PREFIX of the build: "/aagrapevine/", or "/" for a custom domain); anything outside it is a
// plain 404, as on github.io. A folder's address gives its index.html (one without the final "/" is sent on to
// it); an unknown address gives the site's 404.html with status 404; nothing is cached (no-store); byte ranges are
// answered (the booth display's videos), like GitHub Pages.
//
// --overrides: a JSON file read again for every request (missing or unreadable = none), so a check can change what
// the "site" answers while the browser runs — a new version of a file, a slow page:
//   { "files": { "/aagrapevine/sw.js": "<file served instead>" }, "delay_ms": { "/aagrapevine/about/": 20000 } }
// (addresses as the browser asks for them, without the ?query). (Node, not Python: Python's http.server can stall
// on large files on Windows.)
import fs from "node:fs";
import http from "node:http";
import path from "node:path";

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback;
};
const ROOT = path.resolve(args.find((a, i) => !a.startsWith("--") && (i === 0 || !args[i - 1].startsWith("--"))) || "_site");
const PORT = Number(opt("--port", "0")) || 0;
// "/aagrapevine/" → "/aagrapevine"; "/" → "" (the site at the server's root)
const PREFIX = ("/" + String(opt("--prefix", "/aagrapevine/")).replace(/^\/+|\/+$/g, "")).replace(/^\/$/, "");
const OVERRIDES = opt("--overrides", "");

const TYPES = {
  ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8", ".xml": "application/xml; charset=utf-8",
  ".ics": "text/calendar; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
  ".avif": "image/avif", ".ico": "image/x-icon", ".woff2": "font/woff2", ".woff": "font/woff", ".mp3": "audio/mpeg",
  ".pdf": "application/pdf", ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
  ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".oga": "audio/ogg", ".wav": "audio/wav", ".opus": "audio/ogg",
};

function overrides() {
  if (!OVERRIDES) return {};
  try {
    const o = JSON.parse(fs.readFileSync(OVERRIDES, "utf8"));
    return o && typeof o === "object" ? o : {};
  } catch {
    return {};
  }
}

function send(req, res, status, file) {
  const size = fs.statSync(file).size;
  const type = TYPES[path.extname(file).toLowerCase()] || "application/octet-stream";
  const base = { "Content-Type": type, "Cache-Control": "no-store", "Accept-Ranges": "bytes" };
  const range = status === 200 ? req.headers.range : null;
  if (range) {
    const m = /^bytes=(\d*)-(\d*)$/.exec(String(range).trim());
    let start, end;
    if (m && (m[1] !== "" || m[2] !== "")) {
      if (m[1] === "") { start = Math.max(0, size - Number(m[2])); end = size - 1; }
      else { start = Number(m[1]); end = m[2] === "" ? size - 1 : Math.min(Number(m[2]), size - 1); }
    }
    if (start === undefined || start > end || start >= size) {
      res.writeHead(416, { ...base, "Content-Range": `bytes */${size}` }).end();
      return;
    }
    res.writeHead(206, { ...base, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": end - start + 1 });
    if (req.method === "HEAD") { res.end(); return; }
    fs.createReadStream(file, { start, end }).pipe(res);
    return;
  }
  res.writeHead(status, { ...base, "Content-Length": size });
  if (req.method === "HEAD") { res.end(); return; }
  fs.createReadStream(file).pipe(res);
}

function answer(req, res, p, o) {
  if (PREFIX && p === PREFIX) { res.writeHead(301, { Location: PREFIX + "/" }).end(); return; }
  if (!p.startsWith(PREFIX + "/")) { res.writeHead(404).end("not under " + PREFIX + "/"); return; }
  const swap = o.files && typeof o.files === "object" ? o.files[p] : null;
  if (typeof swap === "string" && fs.existsSync(swap) && fs.statSync(swap).isFile()) return send(req, res, 200, swap);
  let f = path.resolve(ROOT, "." + p.slice(PREFIX.length));
  if (f !== ROOT && !f.startsWith(ROOT + path.sep)) { res.writeHead(403).end(); return; }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) {
    if (!p.endsWith("/")) { res.writeHead(301, { Location: p + "/" }).end(); return; }
    f = path.join(f, "index.html");
  }
  if (fs.existsSync(f) && fs.statSync(f).isFile()) return send(req, res, 200, f);
  const nf = path.join(ROOT, "404.html");
  if (fs.existsSync(nf)) return send(req, res, 404, nf);
  res.writeHead(404).end();
}

const server = http.createServer((req, res) => {
  let p;
  try { p = decodeURIComponent(new URL(req.url, "http://x").pathname); } catch { res.writeHead(400).end(); return; }
  const o = overrides();
  const wait = Number((o.delay_ms && typeof o.delay_ms === "object" ? o.delay_ms[p] : 0) || 0);
  if (wait > 0) {
    const timer = setTimeout(() => { if (!res.destroyed) answer(req, res, p, o); }, wait);
    res.on("close", () => clearTimeout(timer));
    return;
  }
  answer(req, res, p, o);
});
// a stopped browser leaves half-open connections behind: never let them keep this process alive or crash it
server.on("clientError", (_e, socket) => socket.destroy());
server.listen(PORT, "127.0.0.1", () => {
  console.log(`serving ${ROOT} at http://127.0.0.1:${server.address().port}${PREFIX}/`);
});
