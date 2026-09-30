"""The Monthly toolkit (/monthly/): eleventy/filters/monthly.js builds it, src/_i18n/monthly.json words it,
src/pages/monthly.njk (the hub) and monthly-month.njk (one page per month) show it, src/assets/js/monthly.js
keeps it true between builds.

  * Strings   — every monthly.* text in English AND Spanish with the same {placeholders}; the site's
                wording rules; every key the templates, the poster and the model ask for exists.
  * Model     — one month's PLAN (monthModel) on a small October 2026 data set, "now" fixed: the dates in
                order with their "over" instant and link, the outside calendar's events, the La Viña issue
                and the Grapevine theme after the magazines' next issues are synced, deadlines and Book of
                the Month offers.
  * Now       — what is LIVE in the current month (monthNow): the next committee meeting, the next issue
                already online, the pointers (daily quote, What's New, the bulletin, Instagram, the
                subscription price, the Grapevine meetings count).
  * IssueLinks — the month's issues on the site: story counts and the /read/ links (monthIssueLinks).
  * Message   — the month as a WhatsApp / e-mail text (monthMessage), one language or both.
  * Templates / Browser — the pages' structure and the browser code's contract (read as text).
  * RealData  — every month of the window, both languages, from the repository's own data.

The Model, Now, IssueLinks, Message and RealData checks run the JavaScript with Node.js (tests/nodejs.py,
I18N_STRICT=1) and are skipped without Node.js or the site's npm packages.

    python -m unittest tests.test_monthly -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import glob
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

NOW_A = "2026-10-05T17:00:00Z"        # Monday, October 5, 2026, noon in Texas
NOW_B = "2026-10-22T06:00:00Z"        # 1 AM on October 22: the October committee meeting is over
PLACEHOLDER = re.compile(r"\{(\w+)\}")
SITE = {"url": "https://example.org/site", "title": "Grapevine / La Viña",
        "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Zoom"},
        "recurring_events": []}


def i18n_all() -> dict:
    out = {}
    for f in sorted(glob.glob(str(ROOT / "src" / "_i18n" / "*.json"))):
        out.update(json.loads(Path(f).read_text(encoding="utf-8")))
    return out


# ------------------------------------------------------------------ a small data set (October 2026)
def item(iid: str, kind: str, **kw) -> dict:
    it = {"id": iid, "kind": kind, "status": kw.pop("status", "ok"), "title": kw.pop("title", iid),
          "url": kw.pop("url", f"https://example.com/{iid}"), "date": kw.pop("date", None), "lang": kw.pop("lang", "en"),
          "category": kw.pop("category", None), "source": kw.pop("source", "committee"), "extra": kw.pop("extra", {}),
          "i18n": kw.pop("i18n", {}), "machine": []}
    it.update(kw)
    return it


def event(iid: str, start: str, end: str | None, title: str, **kw) -> dict:
    extra = {"start": start, "end": end, **kw.pop("extra", {})}
    return item(iid, "event", date=start, title=title, extra=extra,
                i18n={"title": {"en": title, "es": kw.pop("title_es", f"ES {title}")}}, **kw)


def story(iid: str, pub: str, key: str, free: bool = False, **ex) -> dict:
    labels = {"gv:2026-10": ("October 2026", "Octubre 2026"), "gv:2026-11": ("November 2026", "Noviembre 2026"),
              "lv:2026-09": ("September / October 2026", "Septiembre / Octubre 2026")}[f"{pub}:{key}"]
    themes = {"gv:2026-10": {"en": "Loneliness", "es": "Soledad"}, "gv:2026-11": {"en": "Classic Grapevine", "es": "Grapevine clásica"},
              "lv:2026-09": {"en": "Service in AA", "es": "Servicio en AA"}}[f"{pub}:{key}"]
    return item(iid, "article", source="grapevine" if pub == "gv" else "lavina", category=pub, date=f"{key}-01",
                extra={"publication": pub, "issue_key": key, "issue_label": labels[1] if pub == "lv" else labels[0],
                       "issue_theme": themes["es" if pub == "lv" else "en"], "free": free,
                       "issue_url": f"https://example.com/issue/{pub}-{key}", "pub_date": f"{key}-01", **ex},
                i18n={"title": {"en": iid, "es": iid}, "issue_label": {"en": labels[0], "es": labels[1]}, "issue_theme": themes})


def full_db() -> dict:
    return {
        "events": {"items": [
            event("ev:ws-oct3", "2026-10-03T19:00:00Z", "2026-10-03T22:00:00Z", "Grapevine Writing Workshop — Arlington",
                  url="https://neta65.org/event/arlington", extra={"city": "Arlington"}),
            # a timed event without an end: over one hour after it starts — every page's rule (committee.js
            # eventSpan): 11:30 AM CDT → 12:30 PM CDT, 17:30 UTC
            event("ev:talk", "2026-10-05T16:30:00Z", None, "Service talk", url="https://neta65.org/event/talk"),
            event("ev:rec:2026-10-10", "2026-10-10T22:00:00Z", "2026-10-11T01:00:00Z", "GV/LV booth at CityWide Dallas",
                  category="recurring", url="https://citywidedallasaa.org", extra={"recurring": True, "series": "citywide", "city": "Dallas"}),
            event("ev:gone", "2026-10-12T19:00:00Z", None, "Cancelled workshop", status="gone"),
            event("ev:ws-oct17", "2026-10-18T00:00:00Z", "2026-10-18T02:00:00Z", "La Viña Recording Workshop — Duncanville",
                  url="https://neta65.org/event/duncanville", extra={"city": "Duncanville"}),
            event("ev:committee:2026-10-21", "2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", "Committee meeting",
                  category="committee", url="/meetings/", extra={"recurring": True, "location": "Zoom"}),
            event("ev:feed", "2026-10-24T15:00:00Z", "2026-10-24T17:00:00Z", "NETA 65 Service Workshop", source="calendar",
                  category="neta65", url="https://neta65.org/event/service", extra={"city": "Plano"}),
            event("ev:assembly", "2026-10-30", "2026-11-01", "Fall Assembly", extra={"all_day": True, "tentative": True, "city": "Tyler"}),
            event("ev:rec:2026-11-14", "2026-11-14T23:00:00Z", "2026-11-15T02:00:00Z", "GV/LV booth at CityWide Dallas",
                  category="recurring", url="https://citywidedallasaa.org", extra={"recurring": True, "series": "citywide", "city": "Dallas"}),
        ]},
        "editorial": {"items": [
            item("ed:gv:2026-10", "topic", title="Dealing with Loneliness", source="grapevine",
                 extra={"publication": "gv", "issue_key": "2026-10", "deadline": "2026-03-01"}),
            item("ed:gv:2027-05", "topic", title="Fun in Sobriety", source="grapevine",
                 extra={"publication": "gv", "issue_key": "2027-05", "deadline": "2026-10-01"}),
            item("ed:gv:2027-06", "topic", title="Emotional Sobriety", source="grapevine",
                 extra={"publication": "gv", "issue_key": "2027-06", "deadline": "2026-10-15"},
                 i18n={"title": {"en": "Emotional Sobriety", "es": "Sobriedad emocional"}}),
            item("ed:gv:2027-07", "topic", title="Prison Issue", source="grapevine",
                 extra={"publication": "gv", "issue_key": "2027-07", "deadline": "2026-11-01"}),
        ] + [item(f"ed:lv:t{i}", "topic", title=f"Tema {i}", lang="es", source="lavina", extra={"publication": "lv", "evergreen": True},
                  i18n={"title": {"en": f"Topic {i}", "es": f"Tema {i}"}}) for i in range(4)]},
        # issues[] has already moved on to the NEXT issues (synced late in October): October keeps its
        # Grapevine theme and its La Viña issue from the stories
        "articles": {"issues": [
            {"id": "gv:2026-11", "publication": "gv", "key": "2026-11", "label": "November 2026", "theme": "Classic Grapevine",
             "url": "https://www.aagrapevine.org/magazine-issue/november-2026",
             "i18n": {"theme": {"en": "Classic Grapevine", "es": "Grapevine clásica"}, "label": {"en": "November 2026", "es": "Noviembre 2026"}}},
            {"id": "lv:2026-11", "publication": "lv", "key": "2026-11", "label": "Noviembre / Diciembre 2026", "theme": "Navidad sobria",
             "url": "https://www.aalavina.org/edicion/noviembre-diciembre-2026",
             "i18n": {"theme": {"en": "A sober Christmas", "es": "Navidad sobria"},
                      "label": {"en": "November / December 2026", "es": "Noviembre / Diciembre 2026"}}},
        ], "items": [
            story("gv:o1", "gv", "2026-10", free=True), story("gv:o2", "gv", "2026-10"), story("gv:o3", "gv", "2026-10"),
            story("gv:n1", "gv", "2026-11"),
            story("lv:s1", "lv", "2026-09"), story("lv:s2", "lv", "2026-09", free=True),
        ]},
        "weekly_open": {"items": [
            item("weekly_open", "meeting", title="Grapevine Weekly Open AA Meeting", source="grapevine",
                 i18n={"title": {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"},
                       "when": {"en": "Wednesdays at 11:00 AM Central", "es": "Los miércoles a las 11:00 a. m. (hora del Centro)"}}),
            item("weekly_open_lv", "meeting", title="Reunión Abierta de La Viña", source="lavina", lang="es", extra={"starts": "2026-11-05"},
                 i18n={"title": {"en": "La Viña Open Meeting", "es": "Reunión Abierta de La Viña"},
                       "when": {"en": "Thursdays at 11:00 AM Central", "es": "Los jueves a las 11:00 a. m. (hora del Centro)"}}),
        ]},
        "shop": {"botm": [
            {"id": "botm:gv", "pub": "gv", "title": "No Matter What", "discount_pct": 20, "starts": "2026-09-15", "ends": "2026-10-14", "lang": "en"},
            {"id": "botm:lv", "pub": "lv", "title": "Frente a Frente", "discount_pct": 20, "starts": "2026-09-15", "ends": "2026-10-14", "lang": "es"},
        ], "subscriptions": [{"pub": "gv", "region": "us", "plans": [{"type": "digital", "term_months": 1, "price": 2.99},
                                                                    {"type": "print", "term_months": 12, "price": 36.0}]}]},
        "quote": {"items": [{"id": "quote:gv", "pub": "gv", "text": "One day at a time.", "url": "https://www.aagrapevine.org/daily-quote",
                             "date": "2026-10-04"}]},
        "instagram": {"profiles": {"gv": {"username": "alcoholicsanonymous_gv"}, "lv": {"username": "@alcoholicosanonimos_lv"}}},
        "whatsnew": {"items": [
            {"id": "wn:sep", "status": "ok", "wn_date": "2026-09-30T12:00:00Z"},
            {"id": "wn:1", "status": "ok", "wn_date": "2026-10-01T12:00:00Z"},
            {"id": "wn:2", "status": "ok", "wn_date": "2026-10-04T12:00:00Z"},
            {"id": "wn:later", "status": "ok", "wn_date": "2026-10-07T12:00:00Z"},
            {"id": "wn:gone", "status": "gone", "wn_date": "2026-10-02T12:00:00Z"},
        ]},
        "announcements": {"items": [
            item("ann:pinned", "announcement", title="Pinned post", date="2026-10-02", extra={"pinned": True, "slug": "pinned-post"}),
            item("ann:new", "announcement", title="Newest post", date="2026-10-04", extra={"slug": "newest-post"}),
            item("ann:expired", "announcement", title="Expired post", date="2026-10-01", extra={"expires": "2026-10-03"}),
        ]},
        "meetings": {"items": [{"id": f"m{i}", "day": i % 7, "time": "19:00", "in_area": i < 3, "attendance": "in_person", "name": f"Group {i}",
                                "city": f"City {i}"} for i in range(5)]},
        "audio_project": {"gv": {"phone": "(559) 726-1216", "tel": "+15597261216"}, "lv": {"phone": "(559) 670-1601", "tel": "+15596701601"}},
    }


CARRY = {
    "ways": [{"id": "newcomer", "icon": "hand-heart", "title": {"en": "Give it to a newcomer", "es": "Dale un ejemplar a un recién llegado"},
              "text": {"en": "x", "es": "x"}},
             {"id": "group-topic", "icon": "messages-square", "title": {"en": "Bring it to your group", "es": "Llévala a tu grupo"},
              "text": {"en": "x", "es": "x"}}],
    "tips": {"2026-10": [{"way": "newcomer", "text": {"en": "So many newcomers feel isolated.", "es": "Muchos recién llegados se sienten aislados."}},
                         {"way": "group-topic", "text": {"en": "Members rarely raise this topic.", "es": "Los miembros rara vez sacan este tema."}}]},
}
CARRY["wayById"] = {w["id"]: w for w in CARRY["ways"]}

# Build the models, the live extras, the issue links and the messages with the site's own code.
JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const { db, site, carry } = input;
const res = {};
for (const [name, now, key] of input.runs) {
  const d = new Date(now);
  const mm = { en: M.monthModel(key, db, carry, site, "en", d), es: M.monthModel(key, db, carry, site, "es", d) };
  const nw = { en: M.monthNow(db, site, "en", d), es: M.monthNow(db, site, "es", d) };
  const iss = { en: M.monthIssueLinks(db, mm.en), es: M.monthIssueLinks(db, mm.es) };
  const msg = {};
  for (const langs of [["en"], ["es"], ["en", "es"], ["es", "en"]])
    for (const style of ["whatsapp", "email"]) msg[`${langs.join("+")}:${style}`] = M.monthMessage({ mm, nw, iss }, langs, style, site, t);
  res[name] = { mm, nw, iss, msg };
}
out(res);
"""


def run(case: unittest.TestCase, runs: list[tuple[str, str, str]], db: dict | None = None) -> dict:
    return run_js(case, JS, data={"db": db or full_db(), "site": SITE, "carry": CARRY, "runs": runs})


class Strings(unittest.TestCase):
    def test_monthly_strings_in_both_languages(self):
        strings = json.loads((ROOT / "src" / "_i18n" / "monthly.json").read_text(encoding="utf-8"))
        for key, v in strings.items():
            with self.subTest(key=key):
                self.assertTrue(v.get("en", "").strip() and v.get("es", "").strip(), key)
                self.assertEqual(sorted(PLACEHOLDER.findall(v["en"])), sorted(PLACEHOLDER.findall(v["es"])), key)
                for lang in ("en", "es"):
                    # "documents", never "PDF"; the site never describes how it updates itself
                    self.assertNotRegex(v[lang], r"\bPDFs?\b|crawl|scrap|robot|\bbots?\b", key)

    def test_every_key_asked_for_exists(self):
        strings = i18n_all()
        used = set()
        files = ["src/pages/monthly.njk", "src/pages/monthly-month.njk", "src/_includes/macros/monthly.njk",
                 "eleventy/filters/monthly.js", "src/pages/digest.njk", "eleventy/filters/community.js"]
        key_re = re.compile(r"[\"']((?:monthly|report|read|community|committee|home|shop|nav|common|media)\.[a-z0-9_]+(?:\.[a-z0-9_]+)*)[\"']")
        for f in files:
            used |= set(key_re.findall((ROOT / f).read_text(encoding="utf-8")))
        used = {k for k in used if not k.endswith(("_", "."))}               # a key built from parts ("community.lang_name_" + l)
        missing = sorted(k for k in used if k not in strings)
        self.assertEqual(missing, [])
        for k in sorted(used):
            self.assertTrue(strings[k].get("en") and strings[k].get("es"), k)
        self.assertIn("monthly.msg_footer", used)                        # the message's words are among them


class Model(unittest.TestCase):
    def setUp(self):
        self.r = run(self, [("a", NOW_A, "2026-10")])["a"]

    def test_the_dates_of_the_month(self):
        m = self.r["mm"]["en"]
        self.assertEqual([d["id"] for d in m["dates"]], ["ev:ws-oct3", "ev:talk", "ev:rec:2026-10-10", "ev:ws-oct17", "ev:committee:2026-10-21",
                                                        "ev:feed", "ev:assembly"])      # the outside calendar's event too; never a gone one
        by = {d["id"]: d for d in m["dates"]}
        self.assertEqual([d["id"] for d in m["dates"] if d["past"]], ["ev:ws-oct3"])  # over by an instant, not a day
        self.assertEqual((by["ev:committee:2026-10-21"]["href"], by["ev:committee:2026-10-21"]["external"]), ("/meetings/#committee-meeting", False))
        self.assertEqual(by["ev:committee:2026-10-21"]["overAt"], "2026-10-22T01:00:00.000Z")
        self.assertEqual((by["ev:rec:2026-10-10"]["href"], by["ev:rec:2026-10-10"]["external"]), ("https://citywidedallasaa.org", True))
        self.assertEqual((by["ev:feed"]["category"], by["ev:feed"]["kind"]), ("neta65", "event"))
        # the place once: the city after the title only when the title does not already name it (the page's
        # row, the poster and the message)
        self.assertEqual({k: (by[k]["city"], by[k]["place"]) for k in ("ev:ws-oct3", "ev:rec:2026-10-10", "ev:feed", "ev:assembly", "ev:talk")},
                         {"ev:ws-oct3": ("Arlington", ""), "ev:rec:2026-10-10": ("Dallas", ""), "ev:feed": ("Plano", "Plano"),
                          "ev:assembly": ("Tyler", "Tyler"), "ev:talk": ("", "")})
        self.assertEqual(self.r["mm"]["es"]["dates"][0]["place"], "", "the Spanish title names it too")
        # an all-day event: over at midnight Central after its last day (November 1: daylight saving ends)
        self.assertEqual(by["ev:assembly"]["overAt"], "2026-11-02T06:00:00.000Z")
        self.assertEqual(by["ev:assembly"]["range"], "Oct 30–Nov 1")
        # a timed event without an end is over one hour after it starts (the rule of /events/ and the home page
        # too): the talk began half an hour before NOW_A (noon CDT) and is not over yet; its time has no end
        self.assertEqual((by["ev:talk"]["overAt"], by["ev:talk"]["past"], by["ev:talk"]["time"]),
                         ("2026-10-05T17:30:00.000Z", False, "11:30 AM"))
        self.assertEqual(by["ev:ws-oct17"]["time"], "7–9 PM")                       # a no-break space: never split

    def test_deadlines_and_book_of_the_month(self):
        m = self.r["mm"]["en"]
        self.assertEqual([(d["id"], d["overAt"]) for d in m["deadlines"]],
                         [("ed:gv:2027-06", "2026-10-16T05:00:00.000Z"), ("ed:gv:2027-07", "2026-11-02T06:00:00.000Z")])
        self.assertEqual([(b["id"], b["overAt"], b["past"]) for b in m["botm"]],
                         [("botm:gv", "2026-10-15T05:00:00.000Z", False), ("botm:lv", "2026-10-15T05:00:00.000Z", False)])

    def test_the_issues_after_the_next_ones_are_synced(self):
        en, es = self.r["mm"]["en"], self.r["mm"]["es"]
        # the Grapevine theme: the one the issue's stories carry, not the editorial calendar's call for stories
        self.assertEqual((en["gv"]["theme"], es["gv"]["theme"]), ("Loneliness", "Soledad"))
        self.assertEqual(en["gv"]["url"], "https://example.com/issue/gv-2026-10")
        # La Viña's September / October issue, from its stories (issues[] only has November / December now)
        self.assertEqual(en["lv"], {"key": "2026-09", "theme": "Service in AA", "label": "September / October 2026",
                                    "url": "https://example.com/issue/lv-2026-09", "cover": ""})
        self.assertEqual(es["lv"]["theme"], "Servicio en AA")


class Now(unittest.TestCase):
    def setUp(self):
        self.r = run(self, [("a", NOW_A, "2026-10"), ("b", NOW_B, "2026-10")])

    def test_the_next_committee_meeting(self):
        nc = self.r["a"]["nw"]["en"]["nextCommittee"]
        self.assertEqual((nc["ymd"], nc["thisMonth"], nc["time"], nc["zone"], nc["platform"], nc["overAt"]),
                         ("2026-10-21", True, "7–8 PM", "Central", "Zoom", "2026-10-22T01:00:00.000Z"))
        # once October's is over: November's, worked out from the rule (events.json has no record of it)
        nb = self.r["b"]["nw"]["en"]["nextCommittee"]
        self.assertEqual((nb["ymd"], nb["thisMonth"], nb["dayLabel"]), ("2026-11-18", False, "Nov 18"))
        self.assertEqual(self.r["b"]["nw"]["es"]["nextCommittee"]["dayLabel"], "18 de noviembre")

    def test_the_pointers(self):
        en, es = self.r["a"]["nw"]["en"], self.r["a"]["nw"]["es"]
        self.assertTrue(en["quote"])                                           # the home page shows a quote of Oct 4
        self.assertEqual([p["username"] for p in en["instagram"]], ["alcoholicsanonymous_gv", "alcoholicosanonimos_lv"])
        self.assertEqual([p["username"] for p in es["instagram"]], ["alcoholicosanonimos_lv", "alcoholicsanonymous_gv"])
        self.assertEqual((en["news"]["n"], en["news"]["sinceLabel"], es["news"]["sinceLabel"]), (2, "Oct 1", "1 de octubre"))
        # "the newest:" is the newest post by its day (Oct 4) — not the pinned one /bulletin/ lists first (Oct 2)
        self.assertEqual((en["bulletin"]["n"], en["bulletin"]["top"]), (2, {"title": "Newest post", "href": "/bulletin/#newest-post"}))
        self.assertEqual((en["subsFrom"], en["gvm"]), (2.99, {"inArea": 3, "nearby": 2}))
        self.assertEqual(en["audio"]["lv"], {"phone": "(559) 670-1601", "tel": "+15596701601"})

    def test_the_newest_bulletin_post(self):
        # a post dated Oct 1 but scheduled for Oct 5 (publish:) appeared that morning: it is the newest; on the
        # same day, /bulletin/'s order decides (the pinned post first)
        db = full_db()
        db["announcements"]["items"].append(item("ann:sched", "announcement", title="Scheduled post", date="2026-10-01",
                                                 extra={"publish": "2026-10-05", "slug": "scheduled-post"}))
        top = run(self, [("a", NOW_A, "2026-10")], db)["a"]["nw"]["en"]["bulletin"]
        self.assertEqual((top["n"], top["top"]["title"]), (3, "Scheduled post"))
        db = full_db()
        db["announcements"]["items"][0]["date"] = "2026-10-04"            # the pinned post, the same day as the newest
        top = run(self, [("a", NOW_A, "2026-10")], db)["a"]["nw"]["en"]["bulletin"]["top"]
        self.assertEqual(top["title"], "Pinned post")

    def test_a_stale_quote_is_not_pointed_to(self):
        db = full_db()
        db["quote"]["items"][0]["date"] = "2026-10-01"                         # the magazine stopped: 4 days old
        self.assertFalse(run(self, [("a", NOW_A, "2026-10")], db)["a"]["nw"]["en"]["quote"])

    def test_the_next_issues_already_online(self):
        en, es = self.r["a"]["nw"]["en"]["outNext"], self.r["a"]["nw"]["es"]["outNext"]
        self.assertEqual(en, [
            {"pub": "gv", "theme": "Classic Grapevine", "issue": "November 2026", "monthKey": "2026-11",
             "monthLabel": "November 2026", "monthUrl": "/monthly/2026-11/"},
            {"pub": "lv", "theme": "A sober Christmas", "issue": "November / December 2026", "monthKey": "2026-11",
             "monthLabel": "November 2026", "monthUrl": "/monthly/2026-11/"}])
        self.assertEqual([o["pub"] for o in es], ["lv", "gv"])
        self.assertEqual(es[0]["issue"], "noviembre/diciembre de 2026")


class IssueLinks(unittest.TestCase):
    def test_counts_and_links(self):
        r = run(self, [("oct", NOW_A, "2026-10"), ("nov", NOW_A, "2026-11")])
        oct_en, oct_es = r["oct"]["iss"]["en"], r["oct"]["iss"]["es"]
        self.assertEqual([(i["pub"], i["key"], i["count"], i["free"], i["readHref"]) for i in oct_en],
                         [("gv", "2026-10", 3, 1, "/read/#archive-title"), ("lv", "2026-09", 2, 1, "/read/#archive-title")])
        self.assertEqual([i["pub"] for i in oct_es], ["lv", "gv"])              # La Viña first in Spanish
        self.assertEqual(oct_en[1]["label"], "September / October 2026")
        # November: Grapevine's issue is the newest on /read/; La Viña's has no stories yet
        self.assertEqual([(i["pub"], i["count"], i["readHref"]) for i in r["nov"]["iss"]["en"]], [("gv", 1, "/read/#gv-current")])


class Message(unittest.TestCase):
    def setUp(self):
        self.r = run(self, [("a", NOW_A, "2026-10"), ("b", NOW_B, "2026-10"), ("nov", NOW_A, "2026-11")])
        # the texts keep the site's no-break spaces ("La Viña", "7:00 PM"): compared here as plain spaces
        self.plain = {name: {k: v.replace(" ", " ") for k, v in r["msg"].items()} for name, r in self.r.items()}

    def test_every_variant_is_clean(self):
        for name in ("a", "b", "nov"):
            for variant, text in self.r[name]["msg"].items():
                with self.subTest(month=name, variant=variant):
                    self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
                    self.assertNotRegex(text, r"\{|undefined|NaN|\bnull\b|\b(monthly|report|community|committee|read|shop)\.[a-z_]+")
                    self.assertNotIn("\n\n\n", text)
                    if variant.endswith(":email"):
                        self.assertNotIn("*", text)
                        self.assertNotRegex(text, "[\U0001F300-\U0001FAFF☀-➿]")      # no emoji in an e-mail

    def test_the_english_whatsapp_text(self):
        wa = self.plain["a"]["en:whatsapp"]
        self.assertTrue(wa.startswith("*Grapevine & La Viña · NETA 65 — October 2026*\n_Carry the message_\n\n📖 *In the magazines*\n"))
        heads = ["📖 *In the magazines*", "💡 *Put it to work*", "📅 *Dates in October*", "🔁 *Every week*", "✍️ *Share your story*",
                 "📚 *Book of the Month — 20% off through Oct 14*", "🖼️ The toolkit and poster for October: https://example.org/site/monthly/2026-10/"]
        self.assertEqual([wa.index(h) for h in heads], sorted(wa.index(h) for h in heads))
        for line in ("• Grapevine, October 2026: “Loneliness” — 3 stories · 1 free to read",
                     "• La Viña, September / October 2026 (in Spanish): “Service in AA” — 2 stories · 1 free to read",
                     "  All the stories: https://example.org/site/read/",
                     "• Give it to a newcomer: So many newcomers feel isolated.",
                     "• Sat, Oct 10 · 5–8 PM Central · every month — GV/LV booth at CityWide Dallas",
                     "• Sat, Oct 17 · 7–9 PM Central — La Viña Recording Workshop — Duncanville\n",   # the place once
                     "• Wed, Oct 21 · 7–8 PM Central — Committee meeting (Zoom) — all AA members welcome",
                     "• Sat, Oct 24 · 10 AM–12 PM Central — NETA 65 Service Workshop — Plano",
                     "• Oct 30–Nov 1 · details to be confirmed — Fall Assembly — Tyler",
                     "  How to join the committee meeting: https://example.org/site/meetings/#committee-meeting",
                     "• Grapevine Weekly Open AA Meeting — Wednesdays at 11:00 AM Central, on Zoom",
                     "• Grapevine meetings near you: 3 meetings every week in our Area, plus 2 in nearby areas",
                     "• Oct 15 — “Emotional Sobriety” (Grapevine, June 2027 issue)",
                     "• La Viña — no deadline, in Spanish: “Tema 2”",
                     "🎙️ Record it by phone: Grapevine (559) 726-1216 · La Viña (559) 670-1601",
                     "• “No Matter What” (Grapevine)", "📬 Subscriptions from $2.99 a month: https://example.org/site/shop/#subscriptions"):
            self.assertIn(line, wa)
        self.assertNotIn("Arlington", wa)                   # October 3: over
        self.assertNotIn("Next committee meeting", wa)      # this month's is still to come
        self.assertNotIn("Cancelled", wa)

    def test_late_in_the_month_and_a_later_month(self):
        wa = self.plain["b"]["en:whatsapp"]
        self.assertNotIn("Committee meeting (Zoom)", wa)                                   # October 21 is over
        self.assertIn("• Next committee meeting: Wed, Nov 18 · 7–8 PM Central — Zoom", wa)       # like the rows
        # in the middle of the line, after the colon, the Spanish weekday is lower-case (as the page writes it)
        self.assertIn("• Próxima reunión del comité: mié, 18 de noviembre · 7–8 p. m. (hora del Centro) — Zoom",
                      self.plain["b"]["es:whatsapp"])
        self.assertIn("• Mon, Oct 5 · 11:30 AM Central — Service talk", self.plain["a"]["en:whatsapp"])     # still on at noon
        self.assertNotIn("Service talk", self.plain["b"]["en:whatsapp"])                                 # over by October 22
        self.assertNotIn("Book of the Month", wa)                                           # the offer ended Oct 14
        self.assertIn("📬 Subscriptions from", wa)
        nov = self.plain["nov"]["en:whatsapp"]
        self.assertIn("• Sat, Nov 14 · 5–8 PM Central · every month — GV/LV booth at CityWide Dallas", nov)
        self.assertIn("• Wed, Nov 18 · 7–8 PM Central — Committee meeting (Zoom)", nov)
        self.assertIn("• La Viña Open Meeting — Thursdays at 11:00 AM Central, on Zoom — starting Nov 5", nov)
        for live in ("Grapevine meetings near you", "Subscriptions from", "Next committee meeting"):
            self.assertNotIn(live, nov)                                                     # the live parts: this month only

    def test_spanish_and_bilingual(self):
        es = self.plain["a"]["es:whatsapp"]
        self.assertTrue(es.startswith("*La Viña y Grapevine · NETA 65 — Octubre de 2026*\n_Lleva el mensaje_\n"))
        self.assertLess(es.index("• La Viña, septiembre/octubre de 2026: “Servicio en AA”"), es.index("• Grapevine, octubre de 2026 (en inglés): “Soledad”"))
        self.assertIn("📅 *Fechas de octubre*", es)
        self.assertIn("🎙️ Grábala por teléfono: La Viña (559) 670-1601 · Grapevine (559) 726-1216", es)
        self.assertIn("https://example.org/site/es/monthly/2026-10/", es)
        bi = self.plain["a"]["en+es:whatsapp"]
        self.assertIn("📖 *In the magazines / En las revistas*", bi)
        self.assertIn("  “Soledad”", bi)                                                     # the other language's theme
        self.assertIn("• Oct 15 — “Emotional Sobriety / Sobriedad emocional” (Grapevine, June 2027 issue)", bi)
        mail = self.plain["a"]["es+en:email"]
        self.assertIn("FECHAS DE OCTUBRE / DATES IN OCTOBER\n------------------------------------\n", mail)
        self.assertIn("- Grábala por teléfono:", mail)


class Templates(unittest.TestCase):
    """The pages' structure (read as text): the order of the toolkit's cards, the message tool, the chips."""

    def setUp(self):
        self.month = (ROOT / "src" / "pages" / "monthly-month.njk").read_text(encoding="utf-8")
        self.hub = (ROOT / "src" / "pages" / "monthly.njk").read_text(encoding="utf-8")

    def test_a_place_is_said_once(self):
        # the Dates card's rows and the poster print dateRow.place (the city unless the title names it):
        # "Grapevine Writing Workshop — Arlington", never "… — Arlington · Arlington"; on the poster a row
        # with a city still never says "Online"
        poster = (ROOT / "src" / "_includes" / "macros" / "monthly.njk").read_text(encoding="utf-8")
        self.assertIn('{% if d.kind == "committee" %} · {{ d.platform }}{% elif d.place %} · {{ d.place }}{% endif %}', self.month)
        self.assertIn("{% elif d.city %}{% if d.place %} · {{ d.place }}{% endif %}{% elif d.online %}", poster)
        for name, t in (("monthly-month.njk", self.month), ("macros/monthly.njk", poster)):
            self.assertNotIn("· {{ d.city }}", t, name)

    def test_the_month_page(self):
        t = self.month
        ids = ["mp-poster", "mp-message", "mp-issues", "mp-tips", "mp-dates", "mp-weekly", "mp-stories", "mp-botm", "mp-keep"]
        at = [t.index(f'id="{i}"') for i in ids]
        self.assertEqual(at, sorted(at))
        self.assertIn("ui.pageNav(", t)
        for i in ids[:1] + ids[1:3] + ["mp-dates", "mp-weekly", "mp-stories", "mp-botm", "mp-keep"]:
            self.assertIn(f'"#{i}', t)
        keep = t.index('id="mp-keep"')
        opened = t.rindex("{% if nx %}", 0, keep)
        self.assertNotIn("{% endif %}", t[opened:keep])                     # #mp-keep only on the current month
        self.assertRegex(t, r'<fieldset[^>]*data-js-only')
        self.assertRegex(t, r'<div class="[^"]*" data-js-only>\s*<button[^>]*@click="copy\(\'wa\', \$el\)"')
        for kind in ("wa", "email"):
            self.assertRegex(t, rf'<pre id="mp-msg-{kind}-one" class="cm-pre" x-show="!bi" role="region" tabindex="0"')
            self.assertRegex(t, rf'<pre id="mp-msg-{kind}-bi" class="cm-pre" x-show="bi" x-cloak role="region" tabindex="0"')
        self.assertIn('x-data="mpMessage"', t)
        self.assertIn("data-mp-over=", t)
        self.assertIn("data-mp-over-badge", t)
        # the "Over" badge only on this month's rows: nothing on a later month's page could ever show it
        badge = t.index("data-mp-over-badge")
        self.assertIn("{% if m.isCurrent %}<span", t[t.rindex("\n", 0, badge):badge])
        # … and it is a word of its own: a real space after it on both rows (the page's text, copy and paste
        # and screen readers read "Over Wednesday, October 21", never "OverWednesday")
        self.assertEqual(t.count('{{ "monthly.over" | t(lang) }}</span> {% endif %}'), 2)
        self.assertIn('data-mp-newmonth="{{ m.next }}"', t)
        self.assertIn("/contribute/' | lurl(lang) }}#record", t)
        # the Bulletin row of "Keep up all month": two links, so no link covers the row; both are tap-links and
        # the number of posts is said in words (never a bare number)
        row = t[t.index("{% if nx.bulletin.n %}"):]
        row = row[:row.index("{% endif %}\n")]
        self.assertNotIn("after:inset-0", row)
        self.assertEqual(row.count("tap-link"), 2)
        self.assertIn('"monthly.bulletin_n_one" if nx.bulletin.n == 1 else "monthly.bulletin_n"', row)
        self.assertNotIn('<span class="badge-muted">{{ nx.bulletin.n }}</span>', row)
        # the new-month notice's link is a tap-link (44px on phones), on the hub too
        for page in (t, self.hub):
            notice = page[page.index("data-mp-newmonth="):]
            self.assertRegex(notice[:notice.index("</a>")], r'<a class="tap-link ')

    def test_the_hub(self):
        h = self.hub
        self.assertIn("{% set nx = db | mpNow(site, lang) -%}", h.replace("{%- set nx", "{% set nx"))
        self.assertRegex(h, r'<ul [^>]*data-mp-chips>')
        self.assertIn('<li class="{{ c.cls }}" data-mp-chip data-mp-over="{{ c.over }}">', h)
        self.assertIn('href="{{ monthUrl }}#mp-message"', h)
        self.assertIn("data-mp-newmonth=", h)
        self.assertIn('"monthly.digest_last"', h)


class Browser(unittest.TestCase):
    """src/assets/js/monthly.js and the digest's page script (read as text)."""

    def test_monthly_js(self):
        js = (ROOT / "src" / "assets" / "js" / "monthly.js").read_text(encoding="utf-8")
        early_return = js.index("if (!poster || !dl) return;")
        for needle in ('Alpine.data("mpMessage"', "[data-mp-over]", "[data-mp-chips]", "[data-mp-newmonth]", '"alpine:init"',
                       "visibilitychange", "data-mp-over-badge"):
            self.assertLess(js.index(needle), early_return, needle)          # runs on the hub too (no poster there)
        # the digest's choice of language: one for both tools
        self.assertIn('localStorage.getItem("gv-digest-bi")', js)
        self.assertIn('localStorage.setItem("gv-digest-bi"', js)
        for m in re.finditer(r"localStorage\.", js):
            line = js[js.rindex("\n", 0, m.start()):js.index("\n", m.start())]
            self.assertIn("try {", line)                                     # every storage access in try/catch

    def test_the_digest_page_knows_when_it_is_stale(self):
        js = (ROOT / "src" / "assets" / "js" / "community.js").read_text(encoding="utf-8")
        self.assertIn('getAttribute("data-stale-after")', js)
        self.assertIn("stale: false", js)
        page = (ROOT / "src" / "pages" / "digest.njk").read_text(encoding="utf-8")
        self.assertIn('data-stale-after="{{ md.staleAfter }}"', page)
        self.assertIn('x-show="stale" x-cloak role="status"', page)


class RealData(unittest.TestCase):
    """Every month of the window, both languages, from the repository's own data."""

    SCRIPT = r"""
const M = await imp("eleventy/filters/monthly.js");
const db = (await imp("src/_data/db.js")).default();
const site = (await imp("src/_data/site.js")).default();
const carry = (await imp("src/_data/carry.js")).default();
const res = [];
for (const key of M.windowKeys()) {
  for (const lang of ["en", "es"]) {
    const m = filters.mpMonth(key, db, carry, site, lang);
    const iss = filters.mpIssues(key, db, carry, site, lang);
    const now = filters.mpNow(db, site, lang);
    const msgs = [];
    for (const langs of [[lang], [lang, lang === "es" ? "en" : "es"]])
      for (const style of ["whatsapp", "email"]) msgs.push(filters.mpMessage(key, db, carry, site, langs, style));
    res.push({ key, lang, dates: m.dates.length, overAt: m.dates.every((d) => /^\d{4}-\d{2}-\d{2}T/.test(d.overAt)),
               issues: iss.length, now: !!now.key, msgs });
  }
}
out(res);
"""

    def test_every_month_builds(self):
        res = run_js(self, self.SCRIPT)
        self.assertEqual(len(res), 26)
        for r in res:
            with self.subTest(month=r["key"], lang=r["lang"]):
                self.assertTrue(r["overAt"] and r["now"])
                for text in r["msgs"]:
                    self.assertGreaterEqual(len(text), 300)
                    self.assertNotRegex(text, r"\{|undefined|NaN|\b(monthly|report|community|committee)\.[a-z_]+")


if __name__ == "__main__":
    unittest.main()
