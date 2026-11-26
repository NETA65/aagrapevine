"""The four presentations added in November 2026 (config/presentations/): the welcome for Panel 77's new GVRs and RLVs
(welcome-panel-77), the booth or group visit built around QR codes (booth-visit), getting ready for the General Service
Conference (conference-prep) and the recording workshop (recording-workshop).

  * Files      — each deck passes the checker (tests/test_presentations.py), has the versions it was asked for, its
                 minutes add up EXACTLY in every version (the checker allows ±30 %), every slide shown in a version has
                 notes with a SAY or DO line for that version, its number of slides, its own card order, and an agenda
                 whose times are the ones the player works out (the full version's).
  * Facts      — the welcome's guest speakers pair {live:meeting_day} / {live:speaker_note} and {live:meeting_after} /
                 {live:speaker_after}, never {live:meeting_next} on the same slide; its GSR/DCM orientations are
                 content/events' three, and their slide leaves the show after the last one; the booth's codes are the
                 addresses config/site.yml `links:` gives (and three pages of the site); the Conference's agenda items
                 and dates are only the presenter's blanks; the recording workshop's story lines are the site's.
  * Build      — the build's loader reads the four with no problem, and their JSON has a code for every QR slide.

    python -m unittest tests.test_presentations_welcome_visit_prep_recording -v
"""
from __future__ import annotations

import json
import math
import re
import sys
import unittest
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_presentations import FOLDER, check_deck, slide_minutes  # noqa: E402

# deck → its versions (id: minutes) and how many slides its full version shows
DECKS = {
    "welcome-panel-77": ({"full": 30, "short": 15}, (20, 25)),
    "booth-visit": ({"full": 10, "short": 5}, (8, 12)),
    "conference-prep": ({"full": 45, "short": 30}, (15, 20)),
    "recording-workshop": ({"full": 60}, (20, 30)),
}
VERSION_MARK = re.compile(r"^\{(only|not):([^}]*)\}\s*")
LABEL = re.compile(r"^(?:\{lang:es\})?([A-Z][A-Z ()'’,.&/-]*?)(?:\s*\([^)\n]{1,90}\))?:\s")
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))


def deck(name: str) -> dict:
    return yaml.safe_load((FOLDER / f"{name}.yml").read_text(encoding="utf-8"))


def shown(d: dict, preset: dict) -> list[dict]:
    """The slides a version shows (dates aside), in the deck's order."""
    slides = d["slides"]
    if "only" in preset:
        return [s for s in slides if s["id"] in preset["only"]]
    hide = set(preset.get("hide") or [])
    return [s for s in slides if not s.get("facilitator") and not s.get("starts_off") and s["id"] not in hide]


def note_lines(notes: str, version: str) -> list[str]:
    """The notes' lines a version shows (presentations-core.js noteLines: {only:…} / {not:…} at a line's start)."""
    out = []
    for line in (notes or "").split("\n"):
        line = line.strip()
        m = VERSION_MARK.match(line)
        if m:
            ids = [x.strip() for x in m.group(2).split(",")]
            if (m.group(1) == "only") != (version in ids):
                continue
            line = line[m.end():]
        if line:
            out.append(line)
    return out


def clock(m: float) -> str:
    m = max(0, math.floor(m + 0.5))
    return f"{m // 60}:{m % 60:02d}"


def live_keys(node) -> set[str]:
    return set(re.findall(r"\{live:([a-z_]+)\}", json.dumps(node, ensure_ascii=False)))


class TheFiles(unittest.TestCase):
    def test_they_pass_the_checker(self):
        for name in DECKS:
            with self.subTest(deck=name):
                problems = check_deck(FOLDER / f"{name}.yml")
                self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_their_versions_and_minutes_add_up_exactly(self):
        for name, (versions, _) in DECKS.items():
            d = deck(name)
            with self.subTest(deck=name):
                self.assertEqual({p["id"]: p["minutes"] for p in d["presets"]}, versions)
                self.assertEqual(d["minutes"], d["presets"][0]["minutes"], "the deck's length is its full version's")
            for p in d["presets"]:
                with self.subTest(deck=name, version=p["id"]):
                    total = sum(slide_minutes(s, p["id"]) for s in shown(d, p))
                    self.assertAlmostEqual(total, p["minutes"], places=6)

    def test_notes_on_every_shown_slide(self):
        for name in DECKS:
            d = deck(name)
            for p in d["presets"]:
                for s in shown(d, p):
                    with self.subTest(deck=name, version=p["id"], slide=s["id"]):
                        lines = note_lines(s.get("notes", ""), p["id"])
                        self.assertGreaterEqual(len(" ".join(lines).split()), 25)
                        labels = {LABEL.match(x).group(1).strip() for x in lines if LABEL.match(x)}
                        self.assertTrue(labels & {"SAY", "DO"}, f"a SAY or DO line in this version: {sorted(labels)}")
            for s in d["slides"]:
                if s.get("facilitator"):
                    with self.subTest(deck=name, page=s["id"]):
                        self.assertTrue(s.get("notes", "").strip())

    def test_their_size_and_their_cards(self):
        orders = {}
        for f in sorted(FOLDER.glob("*.yml")):
            orders[f.stem] = yaml.safe_load(f.read_text(encoding="utf-8"))["order"]
        self.assertEqual(len(set(orders.values())), len(orders), f"each deck its own place on /orientation/: {orders}")
        for name, (_, (low, high)) in DECKS.items():
            d = deck(name)
            with self.subTest(deck=name):
                n = len(shown(d, d["presets"][0]))
                self.assertTrue(low <= n <= high, f"{n} slides in the full version")
                self.assertGreater(orders[name], 5, "after the five decks before them")
                self.assertNotIn("drive_title", d, "no PowerPoint copy (yet)")
                self.assertTrue(all(d["card"][k]["en"] and d["card"][k]["es"] for k in ("title", "summary", "audience")))

    def test_the_agendas_say_the_times_the_player_works_out(self):
        """An agenda row with `from` shows the start of its first slide in the version shown; the times written are
        the full version's (presentations-core.js agendaRows — tests/test_presentations_core.py checks the same on
        the day's build). No deck here has a slide shown by date before an agenda row, so the times never move."""
        for name in DECKS:
            d = deck(name)
            full = shown(d, d["presets"][0])
            ags = [s for s in full if s["layout"] == "agenda" and any("from" in i for i in s["items"])]
            for ag in ags:
                ids = [s["id"] for s in d["slides"]]
                start, t = {}, 0.0
                for s in full:
                    start[s["id"]] = t
                    t += slide_minutes(s, "full")
                rows = [i for i in ag["items"] if i.get("from")]
                for i, it in enumerate(rows):
                    end = ids.index(rows[i + 1]["from"]) if i + 1 < len(rows) else len(ids)
                    first = next(x for x in ids[ids.index(it["from"]):end] if x in start)
                    with self.subTest(deck=name, row=it["title"]):
                        self.assertEqual(it["time"], clock(start[first]))
                dated = [s["id"] for s in full if (s.get("show_from") or s.get("show_until") or s.get("when"))
                         and ids.index(s["id"]) < ids.index(rows[-1]["from"])]
                self.assertEqual(dated, [], f"{name}: a dated slide would move the agenda's times")


class TheFacts(unittest.TestCase):
    def test_the_welcomes_meetings_and_guest_speakers(self):
        slides = {s["id"]: s for s in deck("welcome-panel-77")["slides"]}
        sp = live_keys(slides["guest-speakers"])
        self.assertTrue({"meeting_day", "speaker_note", "meeting_after", "speaker_after"} <= sp)
        self.assertNotIn("meeting_next", sp, "a meeting's own day and the next meeting never on one slide")
        self.assertIn("meeting_next", live_keys(slides["committee-meeting"]))
        self.assertNotIn("meeting_day", live_keys(slides["committee-meeting"]))
        self.assertIn("grapevine_meeting_next", live_keys(slides["grapevine-meeting"]))
        self.assertTrue({"gv_open_meeting", "lv_open_meeting", "open_meeting_zoom"} <= live_keys(slides["open-meetings"]))
        self.assertTrue({"price_gv_print", "price_gv_digital", "price_lv_print", "price_lv_digital"}
                        <= live_keys(slides["prices"]["rows"]))
        self.assertNotRegex(json.dumps(slides["prices"]["rows"]), r"\$\d", "the prices of the day, never typed in")
        # the speakers start on January 20, 2027 (config/site.yml), and the Grapevine Meeting on January 6, 2027
        first = min(s["date"] for s in SITE["meeting"]["speakers"])
        self.assertEqual(first, "2027-01-20")
        self.assertIn("January 20, 2027", slides["guest-speakers"]["title"])
        gvm = next(e for e in SITE["recurring_events"] if e["key"] == "grapevine-meeting")
        self.assertEqual(gvm["starts"], "2027-01-06")
        self.assertIn("January 6, 2027", json.dumps(slides["grapevine-meeting"]["items"]))

    def test_the_welcomes_orientations_are_the_areas(self):
        slide = next(s for s in deck("welcome-panel-77")["slides"] if s["id"] == "orientations")
        files = sorted((ROOT / "content" / "events").glob("2027-01-*-neta65-gsr-dcm-orientation-*.md"))
        self.assertEqual(len(files), 3)
        days = []
        for f, row in zip(files, slide["rows"]):
            meta = yaml.safe_load(f.read_text(encoding="utf-8").split("---")[1])
            start = meta["start"] if isinstance(meta["start"], str) else meta["start"].isoformat()
            day = date.fromisoformat(start[:10])
            days.append(day.isoformat())
            with self.subTest(file=f.name):
                self.assertEqual(row[1], f"{day:%B} {day.day}, {day.year}")
                self.assertTrue(meta["location"].startswith(row[2].split(",")[0]), (row[2], meta["location"]))
                self.assertIn(row[0], meta["title"])
        self.assertEqual(slide["show_until"], max(days), "it leaves the show after the last orientation")
        self.assertTrue(slide.get("optional"))

    def test_the_booths_codes(self):
        d = deck("booth-visit")
        codes = {s["id"]: s["options"]["url"] for s in d["slides"] if s["layout"] == "live" and s["kind"] == "qr"}
        links = SITE["links"]
        self.assertEqual(codes, {"qr-grapevine": links["gv_subscribe"], "qr-la-vina": links["lv_subscribe"],
                                 "qr-carry": links["carry_the_message"], "qr-lleva": links["lleva_el_mensaje"],
                                 "qr-story": "/contribute/", "qr-calendar": "/events/"})
        closing = next(s for s in d["slides"] if s["layout"] == "closing")
        self.assertEqual(closing["qr"], "/")
        short = next(p for p in d["presets"] if p["id"] == "short")
        self.assertTrue({"qr-grapevine", "qr-la-vina", "qr-carry", "qr-story", "thank-you"} <= set(short["only"]))
        # describe, never sell: no prices on a slide (the notes may say today's, from the site)
        for s in d["slides"]:
            fields = {k: v for k, v in s.items() if k not in ("notes", "version_notes")}
            with self.subTest(slide=s["id"]):
                self.assertNotRegex(json.dumps(fields, ensure_ascii=False), r"\$\d|\{live:price_")

    def test_the_conferences_unknowns_are_blanks(self):
        d = deck("conference-prep")
        slides = {s["id"]: s for s in d["slides"]}
        self.assertEqual(slides["agenda-items"]["items"], ["{fill:item_1}", "{fill:item_2}", "{fill:item_3}"])
        keys = {f["key"] for f in d["fillins"]}
        self.assertTrue({"conference_dates", "item_1", "item_2", "item_3", "input_by", "delegate_visit"} <= keys)
        self.assertIn("{fill:conference_dates}", json.dumps(slides["what-is-the-conference"]["items"]))
        self.assertIn("{fill:conference_dates}", slides["dates"]["intro"])
        # the Conference's own dates are never typed in (April or May of 2027)
        text = (FOLDER / "conference-prep.yml").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)\b(?:april|may) \d{1,2}(?:\s*[–-]\s*\d{1,2})?, 2027")
        # the Fellowship survey: what the repository says of it (config/history.yml)
        history = (ROOT / "config" / "history.yml").read_text(encoding="utf-8")
        self.assertIn("survey the full Fellowship on relevance, usefulness, and viability", history)
        self.assertIn("75th Conference", json.dumps(slides["the-survey"]))
        # the delegate's address is the Area's service address
        self.assertIn("delegate@neta65.org", (ROOT / "content" / "events" / "2026-11-10-neta65-delegate-town-hall.md")
                      .read_text(encoding="utf-8"))

    def test_the_recording_workshops_facts(self):
        d = deck("recording-workshop")
        slides = {s["id"]: s for s in d["slides"]}
        for sid in ("two-programs", "by-phone"):
            with self.subTest(slide=sid):
                self.assertTrue({"gv_audio_phone", "lv_audio_phone"} <= live_keys(slides[sid]["rows"]))
                self.assertNotRegex(json.dumps(slides[sid]["rows"]), r"\(\d{3}\)", "the story lines from the site")
        self.assertEqual(SITE["links"]["lv_email_editorial"], "manuscritoslv@aagrapevine.org")
        self.assertIn(SITE["links"]["lv_email_editorial"], json.dumps(slides["send-it"]["rows"]))
        qr = slides["qr-recorder"]
        self.assertEqual((qr["kind"], qr["options"]["url"]), ("qr", "/contribute/#record"))
        self.assertEqual(slides["themes"]["kind"], "deadlines")
        # La Viña's permission statement is La Viña's words: never on a slide
        audio = json.loads((ROOT / "data" / "site" / "audio_project.json").read_text(encoding="utf-8"))
        permission = ((audio.get("lv") or {}).get("permission_text") or "")[:40]
        if permission:
            self.assertNotIn(permission, (FOLDER / "recording-workshop.yml").read_text(encoding="utf-8"))


LOAD_JS = r"""
const P = await imp("eleventy/filters/presentations.js");
const { decks, problems } = P.loadDecks("config/presentations", { now: new Date(input.now), shop: {} });
const out1 = {};
for (const d of decks.filter((x) => input.ids.includes(x.id))) {
  const j = P.deckJson(d, { site: { url: "https://neta65.github.io/aagrapevine/" }, db: {}, now: new Date(input.now) });
  out1[d.id] = { count: d.count, order: d.order, url: d.url, kinds: d.kinds,
    qr: j.slides.filter((s) => (s.layout === "live" && s.kind === "qr") || (s.layout === "closing" && s.qr))
      .map((s) => [s.id, s.data && s.data.url, !!(s.data && s.data.svg)]) };
}
out({ problems, ids: decks.map((d) => d.id), decks: out1 });
"""


class TheBuild(unittest.TestCase):
    def test_the_loader_and_the_json(self):
        r = run_js(self, LOAD_JS, data={"now": "2027-01-10T18:00:00Z", "ids": list(DECKS)}, now="2027-01-10T18:00:00Z")
        self.assertEqual(r["problems"], [])
        self.assertTrue(set(DECKS) <= set(r["ids"]))
        base = "https://neta65.github.io/aagrapevine/"
        for name in DECKS:
            got = r["decks"][name]
            with self.subTest(deck=name):
                self.assertEqual(got["url"], f"/orientation/presentations/{name}.json")
                self.assertGreater(got["count"], 5)
                for sid, url, svg in got["qr"]:
                    self.assertTrue(svg, f"{sid}: a code drawn by the build")
                    self.assertTrue(url.startswith(("https://www.aagrapevine.org/", "https://www.aalavina.org/", base)), url)
        self.assertEqual(len(r["decks"]["booth-visit"]["qr"]), 7)
        self.assertIn("meeting", r["decks"]["welcome-panel-77"]["kinds"])
        self.assertIn("prices", r["decks"]["welcome-panel-77"]["kinds"])
        self.assertIn("deadlines", r["decks"]["recording-workshop"]["kinds"])


if __name__ == "__main__":
    unittest.main()
