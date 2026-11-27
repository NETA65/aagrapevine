"""/read/'s earlier issues hold their first stories only (since November 2026: their whole tables of contents were 440 KB
of the page's 670 KB, all inside folded rows) — eleventy/filters/read.js SSR_ROWS, src/pages/read.njk,
src/pages/read-archive.11ty.js `more`, src/assets/js/read.js:

  * Built   — Read and /read-archive.json built from data of the test's own (SITE_DATA: one Grapevine issue of 15
              stories, one La Viña issue of 4 and the current issues): an earlier issue on the page lists its first
              SSR_ROWS stories, with "Show all N stories" (a script button: data-read-more, the file's address) only when
              it has more; the file's `more` holds the rest of each, in order, with the credit line its Share sends
              (`ls`); an issue with SSR_ROWS stories or fewer has neither; the row template (no Alpine in it) is on the
              page; without JavaScript (where the button is not) the rest of each issue's stories are under the first
              ones all the same, in a <noscript> list (plain links: title, writer — every story of the issue is on the
              page once, in order, no Alpine, no script button); the issue's link to its own page on the magazine's
              site stays, and says "All 15 stories on aagrapevine.org".
  * Script  — read.js on a page of its own: "Show all" fetches the file once, adds each story as the page draws it
              (its title and original title with their languages, its writer, free / subscribers, its Share: the
              magazine's own title and "— Grapevine, June 2026"), every value as text; the button goes and focus moves
              to the first new story; when the file can't be read, the button says so and works again. A page and a
              file from different builds (a page kept offline): an issue no longer in `more` is found in the file's
              older issues, and only the stories after the ones on the page are added; in neither, the button says so
              and the next tap asks for the file again.

    python -m unittest tests.test_read_archive_rows -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BY = json.loads((ROOT / "src" / "_i18n" / "common.json").read_text(encoding="utf-8"))["common.by"]    # "By {name}"
SSR_ROWS = int(re.search(r"export const SSR_ROWS = (\d+);", (ROOT / "eleventy/filters/read.js").read_text(encoding="utf-8")).group(1))


def story(pub: str, key: str, n: int, **extra) -> dict:
    lv = pub == "lv"
    x = {"publication": pub, "issue_key": key, "issue_date": f"{key}-01", "pub_date": f"{key}-01", "author": f"Pat {n}.", "free": n % 2 == 0, **extra}
    return {"id": f"{pub}:{key}:s{n:02d}", "source": "lavina" if lv else "grapevine", "kind": "article",
            "url": f"https://www.{'aalavina' if lv else 'aagrapevine'}.org/{'revista' if lv else 'magazine'}/{key}/s{n:02d}",
            "title": f"Story {n:02d} of {key}", "lang": "es" if lv else "en", "date": f"{key}-01", "category": pub, "status": "ok", "extra": x}


DATA = {"articles": {"updated": "2026-10-06T06:00:00Z", "issues": [], "items": [
    *[story("gv", "2026-10", n) for n in range(1, 4)],      # the current issues
    *[story("lv", "2026-09", n) for n in range(1, 4)],
    *[story("gv", "2026-06", n, issue_url="https://www.aagrapevine.org/magazine-issue/june-2026") for n in range(1, 16)],  # earlier: 15
    *[story("lv", "2026-05", n) for n in range(1, 5)],      # earlier: 4 stories
]}}

PAGES_JS = r"""
const os = await import("node:os");
process.env.ONLY = "read.njk,read-archive";
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-read-rows-"));
try {
  const pages = await new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" }).toJSON();
  const want = ["/read/", "/es/read/", "/read-archive.json", "/es/read-archive.json"];
  out(Object.fromEntries(want.map((u) => [u, (pages.find((p) => p.url === u) || {}).content || ""])));
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""


class Built(unittest.TestCase):
    built: dict | None = None

    def pages(self) -> dict:
        if Built.built is None:
            with tempfile.TemporaryDirectory(prefix="gv-read-rows-data-") as folder:
                for name, body in DATA.items():
                    Path(folder, name + ".json").write_text(json.dumps(body), encoding="utf-8")
                Built.built = run_js(self, PAGES_JS, now="2026-10-06T15:00:00Z", timeout=300,
                                     env={"SITE_DATA": folder, "WRITERS_ARCHIVE": ""})
        return Built.built

    def issue(self, page: str, pub: str) -> str:
        i = page.index(f'<details class="read-past card @container group/past" data-pub="{pub}"')
        return page[i:page.index("</details>", i)]

    def test_the_first_stories_and_show_all(self):
        for url, file, pre in (("/read/", "/read-archive.json", ""), ("/es/read/", "/es/read-archive.json", "/es")):
            page = self.pages()[url]
            data = json.loads(self.pages()[file])
            with self.subTest(url=url):
                gv = self.issue(page, "gv")
                self.assertEqual(len(re.findall(r'<li class="read-article">', gv)), SSR_ROWS)
                ids = re.findall(r'data-read-more="([^"]+)"', gv)
                self.assertEqual(ids, ["gv-2026-06"])
                self.assertIn(f'data-json="{pre}/read-archive.json"', gv)
                self.assertIn("data-js-only", gv[gv.index("data-read-more") - 200:gv.index("data-read-more")])
                # without JavaScript (no button) the issue's own link says where all of them are
                link = re.search(r'<a class="link tap-link text-sm" href="(https://www\.aagrapevine\.org[^"]*)" target="_blank" rel="noopener">([^<]*)<', gv)
                self.assertEqual(link.group(1), "https://www.aagrapevine.org/magazine-issue/june-2026")
                self.assertEqual(link.group(2), "All 15 stories on aagrapevine.org" if pre == "" else "Las 15 historias en aagrapevine.org")
                # without JavaScript: the other 9 in a <noscript> list right under the first 6, plain links in order
                ns = re.findall(r"<noscript>(.*?)</noscript>", gv, re.S)
                self.assertEqual(len(ns), 1)
                self.assertLess(gv.index("data-read-rows"), gv.index("<noscript>"))
                self.assertLess(gv.index("<noscript>"), gv.index("data-read-more"))
                links = re.findall(r'<a class="link font-semibold" href="([^"]+)" target="_blank" rel="noopener" lang="en">([^<]+)</a>', ns[0])
                self.assertEqual([t for _, t in links], [f"Story {n:02d} of 2026-06" for n in range(SSR_ROWS + 1, 16)])
                self.assertEqual(links[0][0], "https://www.aagrapevine.org/magazine/2026-06/s07")
                self.assertIn(BY["en" if pre == "" else "es"].replace("{name}", "Pat 7."), ns[0])
                self.assertNotRegex(ns[0], r'\s(x-[a-z]+|@[a-z]+|:[a-z-]+)=')
                self.assertNotIn("data-js-only", ns[0])
                self.assertNotIn("data-read-more", ns[0])
                every = re.findall(r'href="(https://www\.aagrapevine\.org/magazine/2026-06/s\d+)"', gv)
                self.assertEqual(sorted(every), [f"https://www.aagrapevine.org/magazine/2026-06/s{n:02d}" for n in range(1, 16)])
                more = data["more"]["gv-2026-06"]
                self.assertEqual(more["pub"], "gv")
                self.assertEqual(more["count"], 15)
                self.assertEqual([i["t"] for i in more["items"]], [f"Story {n:02d} of 2026-06" for n in range(SSR_ROWS + 1, 16)])
                self.assertEqual(more["ls"], "June 2026" if pre == "" else "junio de 2026")
                # La Viña's issue (4 stories): all on the page, no button, nothing in the file
                lv = self.issue(page, "lv")
                self.assertEqual(len(re.findall(r'<li class="read-article">', lv)), 4)
                self.assertNotIn("data-read-more", lv)
                self.assertNotIn("<noscript>", lv)
                self.assertEqual(list(data["more"]), ["gv-2026-06"])
                # the template the script copies: no Alpine inside it
                tpl = page[page.index('<template id="read-row-tpl">'):]
                tpl = tpl[:tpl.index("</template>")]
                self.assertNotRegex(tpl, r'\s(x-[a-z]+|@[a-z]+|:[a-z-]+)=')
                for f in ("t", "orig", "mt", "o", "meta", "a", "free", "sub"):
                    self.assertIn(f'data-f="{f}"', tpl)


SCRIPT_JS = r"""
const rest = [
  { t: "Seven <b>", tl: "en", u: "https://www.aagrapevine.org/magazine/2026-06/s07", a: "Pat 7.", f: 1 },
  { t: "Ocho", tl: "es", o: "Eight", ol: "en", m: 1, u: "https://www.aagrapevine.org/magazine/2026-06/s08", f: 0 },
  { t: "Nine", u: "javascript:alert(1)" } ];
// input.moved: a file from a later build, where the issue is one of the older issues (all its stories);
// input.gone: a file without it
const json = input.moved ? { more: {}, issues: [{ id: "gv:2026-06", pub: "gv", ls: "June 2026", count: 4,
                                                  items: [{ t: "One", u: "https://www.aagrapevine.org/magazine/2026-06/s01" }, ...rest] }] }
  : input.gone ? { more: {}, issues: [] } : { more: { "gv:2026-06": { pub: "gv", count: 9, ls: "June 2026", items: rest } } };
let calls = 0, fail = input.fail;
const p = page({ html:
  '<details class="read-past" open><summary>June</summary><div x-ignore><ul data-read-rows><li class="read-article">One</li></ul>' +
  '<p data-js-only><button type="button" id="more" data-read-more="gv:2026-06" data-json="/read-archive.json" data-t-loading="Loading…" data-t-failed="try again">Show all 9 stories</button></p></div></details>' +
  '<template id="read-row-tpl"><li class="read-article"><a href="#" target="_blank" class="group x"><span class="flex"><span class="t" data-f="t"></span></span>' +
  '<span data-f="orig" title="Auto"><span data-f="mt">MT</span><span class="italic" data-f="o"></span></span>' +
  '<span data-f="meta"><span data-f="a" data-t="By {name}"></span><span data-f="free">Free</span><span data-f="sub">Subscribers</span></span></a>' +
  '<button type="button" class="read-share" data-t="Share" title="Share">S</button></li></template>',
  scripts: ["src/assets/js/read.js"],
  globals: { GV: { url: (u) => "/aagrapevine" + u },
             fetch: (u, o) => { calls++; return fail-- > 0 ? Promise.reject(new Error("offline")) : Promise.resolve({ ok: true, json: () => Promise.resolve(json), url: u }); } } });
await p.ready();
const res = {};
p.click(p.$("#more"));
await p.tick(10);
if (input.fail || input.gone) {
  res.failed = { text: p.$("#more").textContent, busy: p.$("#more").getAttribute("aria-busy"), rows: p.$$("[data-read-rows] > li").length };
  p.click(p.$("#more"));
  await p.tick(10);
}
const rows = p.$$("[data-read-rows] > li");
res.n = rows.length;
res.calls = calls;
res.button = !!p.$("#more");
res.focus = p.doc.activeElement && p.doc.activeElement.tagName + " " + p.doc.activeElement.getAttribute("href");
res.rows = rows.slice(1).map((li) => ({
  href: li.querySelector("a").getAttribute("href"), title: li.querySelector('[data-f="t"]').textContent,
  tl: li.querySelector('[data-f="t"]').getAttribute("lang"), hover: li.querySelector('[data-f="t"]').classList.contains("group-hover:text-gv"),
  orig: li.querySelector('[data-f="o"]') ? li.querySelector('[data-f="o"]').textContent : null,
  mt: !!li.querySelector('[data-f="mt"]'), by: li.querySelector('[data-f="a"]') ? li.querySelector('[data-f="a"]').textContent : null,
  free: !!li.querySelector('[data-f="free"]'), sub: !!li.querySelector('[data-f="sub"]'), meta: !!li.querySelector('[data-f="meta"]'),
  share: [li.querySelector(".read-share").getAttribute("data-share"), li.querySelector(".read-share").getAttribute("data-share-title"),
          li.querySelector(".read-share").getAttribute("data-share-text"), li.querySelector(".read-share").getAttribute("aria-label")],
  html: !!li.querySelector("b") }));
res.errors = p.errors.map(String);
out(res);
"""


class Script(unittest.TestCase):
    def test_show_all_adds_the_rest(self):
        r = run_js(self, PAGE_JS + SCRIPT_JS, data={"fail": 0}, needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["n"], r["calls"], r["button"]), (4, 1, False))
        self.assertEqual(r["focus"], "A https://www.aagrapevine.org/magazine/2026-06/s07", "on the first new story")
        seven, eight, nine = r["rows"]
        self.assertEqual(seven["title"], "Seven <b>")
        self.assertFalse(seven["html"], "a title goes in as text")
        self.assertTrue(seven["hover"])
        self.assertEqual((seven["orig"], seven["by"], seven["free"], seven["sub"]), (None, "By Pat 7.", True, False))
        self.assertEqual(seven["share"], ["https://www.aagrapevine.org/magazine/2026-06/s07", "Seven <b>", "— Grapevine, June 2026", "Share: Seven <b>"])
        self.assertEqual((eight["tl"], eight["orig"], eight["mt"], eight["free"], eight["sub"]), ("es", "Eight", True, False, True))
        self.assertEqual(eight["share"][1], "Eight", "the magazine's own title")
        self.assertEqual(nine["href"], "#", "only a web address")
        self.assertFalse(nine["meta"], "no writer, no free / subscribers: no line")

    def test_a_file_from_another_build(self):
        r = run_js(self, PAGE_JS + SCRIPT_JS, data={"fail": 0, "moved": 1}, needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["n"], r["calls"], r["button"]), (4, 1, False), "the stories after the one on the page")
        self.assertEqual([x["title"] for x in r["rows"]], ["Seven <b>", "Ocho", "Nine"])
        self.assertEqual(r["rows"][0]["share"][2], "— Grapevine, June 2026")
        r = run_js(self, PAGE_JS + SCRIPT_JS, data={"fail": 0, "gone": 1}, needs_modules=False)
        self.assertTrue(r["failed"]["text"].endswith("— try again"))
        self.assertEqual((r["n"], r["calls"], r["button"]), (1, 2, True), "the next tap asks for the file again")
        self.assertEqual(r["errors"], [])

    def test_when_the_file_cannot_be_read(self):
        r = run_js(self, PAGE_JS + SCRIPT_JS, data={"fail": 1}, needs_modules=False)
        self.assertEqual(r["failed"]["rows"], 1)
        self.assertIsNone(r["failed"]["busy"], "it works again")
        self.assertTrue(r["failed"]["text"].endswith("— try again"))
        self.assertEqual((r["n"], r["calls"], r["button"]), (4, 2, False), "the second tap fetches again and adds them")
        self.assertEqual(r["errors"], [])


if __name__ == "__main__":
    unittest.main()
