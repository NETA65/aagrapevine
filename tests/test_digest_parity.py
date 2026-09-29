"""The monthly digest is written twice — by the website (/digest/, eleventy/filters/community.js →
buildMonthlyDigest) and by the e-mail (scripts/notify/send_digest.py, standard library only so the
e-mail job needs no Node.js). Their rules are copies of each other ("keep them equal"); this test
builds the same editions with BOTH and compares what each one picked, so a rule changed on one side
only fails here instead of drifting quietly:

  the edition (the month covered, the month it comes out in), the month's news by group (the photo albums
  and their photo counts, the podcast/YouTube twins, the Instagram posts, the counts), the Instagram
  accounts (each one's count and newest posts), the magazine issues whose stories came out in the month
  (stories of the month, all of the issue's, free ones, "current", highlights, label, theme), the Area 65 /
  Texas writers and the events that took place (the committee meeting included).

Two data sets: a small one made for the edge cases (a bulletin post that expired the day before, seen
in the small hours of the 1st; a post scheduled with `publish:`; posts saved after the month their date
names; a video and an Instagram post at 11:30 PM
on the last day; stories published on the last day and on the 1st, stories without a pub_date; a removed
story of a newer issue; committee files added after the month their name dates them to; an album with a
photo of the next month; a dated flyer; a skipped committee meeting …) and the repository's own data for
several editions. TextSmoke renders the WhatsApp / e-mail text of the page and DaySpelling compares how
the page and the e-mail write an event's days (the other rendered words are not compared with the
e-mail's — tests/test_send_digest.py checks those). Skipped without Node.js and the site's npm packages
(tests/nodejs.py).

    python -m unittest tests.test_digest_parity -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
import test_send_digest as SD  # noqa: E402  (its fixture: a realistic September 2026 edition)

from scripts.notify import send_digest as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# What buildMonthlyDigest picked, in the same shape as summary() below.
PICK_JS = r"""
const C = await imp("eleventy/filters/community.js");
const summary = (md) => ({
  edition: { key: md.edition.key, out: md.edition.out },
  news: Object.fromEntries(Object.entries(md.news).map(([k, v]) => [k, v.map((i) => i.id)])),
  albums: md.news.drive.filter((i) => i._album).map((i) => [i.id, i._count]),
  twins: md.news.episode.filter((i) => i._twin).map((i) => [i.id, i._twin.id]),
  instagram: md.instagram.map((a) => [a.key, a.username, a.count, a.newest.map((p) => p.id)]),
  counts: md.counts,
  issues: md.issues.map((i) => ({ pub: i.pub, key: i.key, count: i.count, total: i.total, free: i.free, current: i.current,
                                  highlights: i.highlights.map((a) => a.id), label_en: i.label.en, theme: i.theme })),
  writers: { neta65: md.writers.neta65.map((i) => i.id || i.url), texas: md.writers.texas.map((i) => i.id || i.url) },
  events: md.events.map((e) => e.id),
});
let db, site;
if (input.dir) {
  const fs = await import("node:fs");
  db = {};
  for (const f of fs.readdirSync(input.dir)) if (f.endsWith(".json")) db[f.slice(0, -5)] = JSON.parse(fs.readFileSync(input.dir + "/" + f, "utf8"));
  if (!db.spotlight) db.spotlight = { items: [] };
  site = input.site;
} else {
  db = (await imp("src/_data/db.js")).default();
  site = (await imp("src/_data/site.js")).default();
}
const res = {};
for (const [month, now] of input.cases) {
  res[`${month}@${now}`] = summary(C.buildMonthlyDigest(db, { site, now: new Date(now), month: month || undefined }));
}
out(res);
"""


def summary(data: dict) -> dict:
    """What send_digest.collect picked, in the shape PICK_JS writes."""
    return {
        "edition": {"key": data["edition"]["key"], "out": data["edition"]["out"]},
        "news": {g: [i["id"] for i in v] for g, v in data["groups"].items()},
        "albums": [[i["id"], i["_count"]] for i in data["groups"]["drive"] if i.get("_album")],
        "twins": [[i["id"], i["_twin"]["id"]] for i in data["groups"]["episode"] if i.get("_twin")],
        "instagram": [[a["key"], a["username"], a["count"], [p["id"] for p in a["newest"]]] for a in data["instagram"]],
        "counts": D.counts(data),
        "issues": [{"pub": i["pub"], "key": i["key"], "count": i["count"], "total": i["total"], "free": i["free"],
                    "current": i["current"], "highlights": [a["id"] for a in i["highlights"]], "label_en": i["label"]["en"],
                    "theme": i["theme"]} for i in data["issues"]],
        "writers": {k: [i.get("id") or i.get("url") for i in v] for k, v in data["writers"].items()},
        "events": [e["id"] for e in data["events"]],
    }


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Parity:
    maxDiff = None

    """Compare JS and Python for each (month, now)."""

    def compare(self, js: dict, cases: list[tuple[str, datetime]], highlights: int, max_per: int) -> None:
        for month, now in cases:
            key = f"{month}@{iso(now)}"
            py = summary(D.collect(now, month or None, max_per, highlights))
            with self.subTest(edition=key):
                self.assertIn(key, js)
                for field in py:
                    with self.subTest(field=field):
                        self.assertEqual(js[key][field], py[field], f"{key}: community.js and send_digest.py differ on {field}")


# the edge-case fixture's settings: August's committee meeting (the 19th) was skipped
EDGE_CONFIG = SD.CONFIG.replace("skip_dates: []", 'skip_dates: ["2026-08-19"]')


class FixtureParity(SD.DigestCase, Parity):
    config = EDGE_CONFIG

    def test_the_edge_cases(self):
        self.full_month()
        # bulletin posts: one that expired on the last day of the month (gone on the 1st in the small hours
        # too, Central time), one that lasts through the 1st, one written in August and scheduled for
        # September 2 (`publish:`), one scheduled for October 2; and — each counts on the day it was added
        # to the site — one written in August but saved on September 10, one dated September 28 but saved
        # on October 3, after the September e-mail
        self.write("announcements", {"items": [
            SD.item("ann:1", "announcement", "committee", "2026-09-05", "New GVR orientation", url="/bulletin/#new",
                    extra={"body_md": "Join us **Saturday**.", "pinned": True}),
            SD.item("ann:sep30", "announcement", "committee", "2026-09-06", "Until the 30th", extra={"expires": "2026-09-30"}),
            SD.item("ann:oct1", "announcement", "committee", "2026-09-07", "Until the 1st", extra={"expires": "2026-10-01"}),
            SD.item("ann:sched", "announcement", "committee", "2026-08-28", "Scheduled for September", extra={"publish": "2026-09-02"}),
            SD.item("ann:later", "announcement", "committee", "2026-09-20", "Scheduled for October", extra={"publish": "2026-10-02"}),
            SD.item("ann:aug-saved", "announcement", "committee", "2026-08-20", "Saved in September", first_seen="2026-09-10T14:00:00Z"),
            SD.item("ann:saved-oct", "announcement", "committee", "2026-09-28", "Saved on October 3", first_seen="2026-10-03T14:00:00Z"),
        ]})
        # August: a booth and a committee meeting that was skipped (settings) — the August digest has the booth only
        events = json.loads((self.site_dir / "events.json").read_text(encoding="utf-8"))["items"]
        self.write("events", {"items": events + [
            SD.event("ev:aug-ws", "2026-08-22T15:00:00Z", "2026-08-22T18:00:00Z", "August workshop")]})
        # the magazines: a story whose pub_date could not be worked out counts on its issue's earliest one
        # (the October Grapevine's: September 23); one of an issue without any pub_date is in no edition (never
        # by first_seen); a removed story of a newer issue does not make the October issue old — /read/ does
        # not list it (read.js live()), and neither does the e-mail
        articles = json.loads((self.site_dir / "articles.json").read_text(encoding="utf-8"))
        articles["items"] += [
            dict(SD.article("gv:nopd", "gv", "2026-10", None, "No pub_date"), first_seen="2026-10-03T12:00:00Z"),
            dict(SD.article("gv:nodates", "gv", "2026-07", None, "An issue without dates"), first_seen="2026-09-24T12:00:00Z"),
            dict(SD.article("gv:gone-nov", "gv", "2026-11", "2026-09-28", "Removed"), status="gone"),
        ]
        self.write("articles", articles)
        # Instagram: a removed post, and a post of another account (after the magazines')
        ig = json.loads((self.site_dir / "instagram.json").read_text(encoding="utf-8"))
        ig["items"] += [dict(SD.post("ig:gone", "lv", "2026-09-11T15:00:00Z"), status="gone"),
                        SD.post("ig:other", "xx", "2026-09-15T15:00:00Z")]
        self.write("instagram", ig)
        cfg = yaml.safe_load(EDGE_CONFIG)
        site = {**cfg["site"], "meeting": cfg.get("meeting") or {}, "digest": cfg.get("digest") or {}, "links": {},
                "recurring_events": []}
        cases = [("", SD.OCT1),                                                   # the September digest goes out
                 ("", datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)),         # 1:30 AM CDT on October 1
                 ("", datetime(2026, 10, 20, 15, 5, tzinfo=timezone.utc)),        # later in October
                 ("2026-10", SD.OCT1),                                            # a preview of October on the 1st
                 ("", datetime(2026, 11, 1, 15, 5, tzinfo=timezone.utc)),         # the October digest (late uploads)
                 ("2026-08", datetime(2026, 9, 1, 15, 5, tzinfo=timezone.utc))]   # August's (its meeting skipped)
        js = run_js(self, PICK_JS, data={"dir": str(self.site_dir), "site": site, "cases": [[m, iso(n)] for m, n in cases]})
        highlights = int((cfg.get("digest") or {}).get("highlights") or 3)
        max_per = int((cfg.get("digest") or {}).get("per_section") or 5)
        self.compare(js, cases, highlights, max_per)
        # and the rules themselves
        early = summary(D.collect(datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc), None, max_per, highlights))
        self.assertEqual(early["news"]["announcement"], ["ann:1", "ann:aug-saved", "ann:oct1", "ann:sched"])  # pinned, then newest
        self.assertIn("yt:late", early["news"]["video"])                                        # 11:30 PM CDT on the 30th
        self.assertIn("lv:a2", early["news"]["article"])                                        # published on the 30th
        self.assertNotIn("gv:a5", early["news"]["article"])                                     # … on October 2
        self.assertEqual(early["albums"], [["album:f:Booth", 3]])                               # the October photos are not in it
        self.assertNotIn("flyer", json.dumps(early["news"]))
        self.assertEqual(early["news"]["drive"], ["doc:aug", "album:f:Booth", "doc1"])           # added in September
        self.assertIn("gv:nopd", early["news"]["article"])                                       # its issue's day
        self.assertNotIn("gv:nodates", json.dumps(early))                                         # no day: never
        self.assertEqual([i["current"] for i in early["issues"] if i["key"] == "2026-10"], [True])  # the removed story
        self.assertEqual(early["instagram"], [["gv", "alcoholicsanonymous_gv", 4, ["ig:g4", "ig:g3", "ig:g2"]],
                                              ["lv", "alcoholicosanonimos_lv", 1, ["ig:l1"]], ["xx", "xx", 1, ["ig:other"]]])
        later = summary(D.collect(datetime(2026, 11, 1, 15, 5, tzinfo=timezone.utc), None, max_per, highlights))
        self.assertEqual(later["news"]["announcement"], ["ann:saved-oct", "ann:later"])            # saved / scheduled in October
        self.assertEqual(later["news"]["drive"], ["doc:min", "album:f:Booth"])                    # October's uploads
        self.assertEqual(later["albums"], [["album:f:Booth", 2]])                                # ph4 and the late ph5
        self.assertEqual(js[f"2026-08@{iso(cases[5][1])}"]["events"], ["ev:rec:2026-08-08", "ev:aug-ws"])   # no meeting: skipped
        self.assertEqual(js[f"2026-10@{iso(SD.OCT1)}"]["events"], ["ev:early"])                # only what has started


class RealDataParity(unittest.TestCase, Parity):
    def test_the_repositorys_data(self):
        cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        digest = cfg.get("digest") or {}
        highlights = D._positive(digest.get("highlights"), 3)
        max_per = D._positive(digest.get("per_section"), 5)
        today = datetime.now(timezone.utc).replace(microsecond=0)
        last = D.edition_of(today)["key"]                        # the digest on /digest/ today

        def sent(month: str) -> datetime:                        # the 1st of the month after it, 15:05 UTC
            y, m = (int(x) for x in D.month_add(month, 1).split("-"))
            return datetime(y, m, 1, 15, 5, tzinfo=timezone.utc)
        cases = [("", today), (last, sent(last)), (D.month_add(last, -1), sent(D.month_add(last, -1))), (D.month_add(last, 1), today)]
        js = run_js(self, PICK_JS, data={"cases": [[m, iso(n)] for m, n in cases]})
        self.compare(js, cases, highlights, max_per)
        self.assertTrue(json.dumps(js))


class TextSmoke(unittest.TestCase):
    """The page's WhatsApp / e-mail texts of the September digest (MONTHLY_NOW = October 1): the new order,
    the one pointer to October's toolkit, nothing of what is current."""

    SCRIPT = r"""
const conf = await imp("eleventy.config.js");
const C = await imp("eleventy/filters/community.js");
const db = (await imp("src/_data/db.js")).default();
const site = (await imp("src/_data/site.js")).default();
const md = filters.cmMonthlyDigest(db, site);
const t = (k, l, v) => conf.translateKey(k, l, v);
const media = { title: filters.mediaTitle, cleanTitle: filters.mediaCleanTitle, videoKind: filters.mediaVideoKind };
out({
  key: md.edition.key,
  wa: C.monthlyDigestText(md, ["en"], "whatsapp", site, t, media),
  waBi: C.monthlyDigestText(md, ["en", "es"], "whatsapp", site, t, media),
  mailBi: C.monthlyDigestText(md, ["es", "en"], "email", site, t, media),
  viaFilter: filters.cmDigestText(md, ["en"], "whatsapp", site).length > 0,
});
"""

    def test_the_september_texts(self):
        r = run_js(self, self.SCRIPT, env={"MONTHLY_NOW": "2026-10-01T15:05:00Z"})
        self.assertEqual(r["key"], "2026-09")
        wa = r["wa"]
        self.assertTrue(wa.startswith("*NETA 65 Grapevine / La Viña — September 2026 digest*\n_Everything new on the site in September_\n"))
        for needle in ("📅 *Events in September*", "📖 *New in the magazines*", "🗓️ *Coming up in October*"):
            self.assertIn(needle, wa)
        self.assertEqual(wa.count("/monthly/2026-10/"), 1)
        heads = [wa.index(h) for h in ("📅 *Events in September*", "📖 *New in the magazines*", "🗓️ *Coming up in October*") if h in wa]
        self.assertEqual(heads, sorted(heads))
        # none of the old "coming up" sections (their headings and markers; a file may be called "Share your story")
        for gone in ("*Next committee meeting*", "*Put it to work*", "Every week:", "Grapevine meetings near you:", "✍️", "📚",
                     "*Book of the Month", "📬", "Subscriptions from", "💬", "daily quote", "zoom.us",
                     "tel:", "every month", "{", "undefined", "NaN"):
            self.assertNotIn(gone, wa)
        self.assertIn("*NETA 65 Grapevine / La Viña — September 2026 digest / Resumen de septiembre de 2026*", r["waBi"])
        self.assertIn("🗓️ *Coming up in October / Lo que viene en octubre*", r["waBi"])
        self.assertIn("NETA 65 Grapevine / La Viña — Resumen de septiembre de 2026 / September 2026 digest", r["mailBi"])
        self.assertIn("LO QUE VIENE EN OCTUBRE / COMING UP IN OCTOBER", r["mailBi"])
        self.assertIn("/es/monthly/2026-10/", r["mailBi"])
        self.assertNotIn("*", r["mailBi"].split("\n", 1)[1].replace("•", ""))       # the e-mail style: no *bold*
        self.assertTrue(r["viaFilter"])
        # Instagram (while instagram.json still has September's posts): each account's count and ONE link to
        # the site's Instagram page — never the posts one by one in a message
        if "📸" in wa:
            ig = wa[wa.index("📸"):]
            ig = ig[:ig.index("\n\n")]
            self.assertRegex(ig, r"^📸 \*Instagram \(\d+\)\*\n(• (Grapevine|La.Viña) @\w+: \d+ posts?\n)+  https://\S+/instagram/$")
            self.assertNotIn("instagram.com/p/", wa)
            self.assertLess(wa.index("🎬") if "🎬" in wa else 0, wa.index("📸"))


class DaySpelling(unittest.TestCase):
    """An event's days read the same on the page (and its texts: community.js eventWhen with time: false,
    cmEventDays) and in the e-mail (send_digest.event_row): "Sat, Sep 12" / "sáb, 12 de sept", over several
    days "Fri, Jun 25 – Sun, Jun 27", with the year when it is another year. The page capitalizes a day that
    starts a line; the e-mail writes it inside a line."""

    # (each with the last day of the month it is listed in: the edition's)
    EVENTS = [
        (SD.event("ev:one", "2026-09-12T22:00:00Z", "2026-09-13T01:00:00Z", "Booth"), "2026-09-30"),
        (SD.event("ev:late", "2026-10-01T04:30:00Z", "2026-10-01T06:00:00Z", "Late on the 30th"), "2026-09-30"),
        (SD.event("ev:days", "2027-06-25", "2027-06-27", "Summer Assembly", all_day=True), "2027-06-30"),
        (SD.event("ev:year", "2026-12-31", "2027-01-02", "New Year", all_day=True), "2026-12-31"),
        (SD.event("ev:mar", "2027-03-19T14:00:00Z", "2027-03-21T20:00:00Z", "Spring Assembly"), "2027-03-31"),
    ]
    SCRIPT = r"""
const C = await imp("eleventy/filters/community.js");
const res = {};
for (const [ev, last] of input.events) for (const l of ["en", "es"]) res[`${ev.id}|${l}`] = C.eventWhen(ev, l, Date.parse(`${last}T12:00:00Z`), { time: false });
out(res);
"""

    def test_the_page_and_the_email_write_the_same_days(self):
        js = run_js(self, self.SCRIPT, data={"events": self.EVENTS})
        links = D.Links("https://example.org")
        for ev, last in self.EVENTS:
            for lang in ("en", "es"):
                with self.subTest(event=ev["id"], lang=lang):
                    page = js[f"{ev['id']}|{lang}"]
                    mail = D.event_row(ev, lang, links, date.fromisoformat(last))["when"]
                    self.assertEqual(page[:1].lower() + page[1:], mail[:1].lower() + mail[1:])
        self.assertEqual(js["ev:one|es"], "Sáb, 12 de sept")
        self.assertEqual(js["ev:late|en"], "Wed, Sep 30")                       # 11:30 PM CDT: one day
        self.assertEqual(js["ev:days|es"], "Vie, 25 de jun – dom, 27 de jun")
        self.assertEqual(js["ev:year|en"], "Thu, Dec 31, 2026 – Sat, Jan 2, 2027")


class SortOrder(unittest.TestCase):
    def test_ties_are_broken_like_localeCompare(self):
        """Items with the same date are listed by id, titles by title — the website sorts them with
        JavaScript's localeCompare; send_digest.js_order must give the same order."""
        words = ["drive:1fC3vvsu0CG-XdUagGDb_fgiw", "drive:1Fs9t4jxeMXemu_FQP", "drive:1fc3", "drive:1FC3", "pod:abc",
                 "pdf:9372f4b13305", "yt:_abc", "yt:-abc", "yt:Abc", "yt:abc", "Área 65", "Arlington", "arlington", "Écrire",
                 "ecrire", "écrire", "Ecrire", "Zeta", "alpha beta", "alpha-beta", "alpha_beta", "alpha1", "Alpha", "ñandú",
                 "nube", "oso", "A Halloween to Remember", "At Wit's End", "At Wit’s End", "“Quoted”", "(Paren)", "10 ways",
                 "9 ways", "—dash", "¡Hola!", "¿Qué?", "…more", "’s", "‘x", "”q", "«gui»", "Mi GPS", "Mi GPS", "Mi-GPS"]
        js = run_js(self, "out(input.slice().sort((a, b) => a.localeCompare(b, 'en-US')))", data=words, needs_modules=False)
        self.assertEqual(sorted(words, key=D.js_order), js)


if __name__ == "__main__":
    unittest.main()
