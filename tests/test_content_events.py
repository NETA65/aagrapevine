"""Every real event file in content/events/ — the content checker the Code check runs (.github/workflows/check.yml
runs on every change to content/**):

  * `start:` / `end:` are whole dates with their year (one without it would land in THIS year — maybe already past —
    and is left out of the site: scripts/sync/announcements.py as_when)
  * a time written with its UTC offset uses Central time's offset on that day (-05:00 from the second Sunday of
    March to the first Sunday of November, -06:00 the rest of the year)
  * the end comes after the start (on or after the start's day for a date-only event)

A file that fails shows its name and what to change. The daily update would leave such a file out (or show it at
another time) and list it on /status/; this check says so the moment the file is saved.
Run:  python -m unittest tests.test_content_events -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import announcements as A  # noqa: E402

CHI = ZoneInfo("America/Chicago")
FOLDER = ROOT / "content" / "events"
YEAR = re.compile(r"(?<!\d)20\d\d(?!\d)")


def central_day(v: str) -> str:
    """'2027-03-19' → itself; '2027-03-20T00:00:00Z' → its day in Central time ('2027-03-19')."""
    return v if len(v) == 10 else datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(CHI).date().isoformat()


def problems(path: Path) -> list[str]:
    """What is wrong with the dates of one event file (empty: nothing) — read exactly as the daily update reads it
    (announcements.parse_event), plus the checks it only reports."""
    try:
        meta, _body = A.read_front_matter(path)
        item = A.parse_event(path, CHI)          # no year, a time alone, an end before the start: ValueError
    except ValueError as e:
        return [str(e)]
    ex = item["extra"]
    out = list(ex.get("date_notes") or [])       # a UTC offset that is not Central time's; "05/10/2027"
    written = {k: meta.get(k) for k in ("start", "date", "end") if meta.get(k) not in (None, "")}
    for key, v in written.items():               # (as_when refuses these too; said here in so many words)
        clock_end = key == "end" and not isinstance(v, (date, datetime)) and A.parse_hhmm(v, (-1, -1)) != (-1, -1)
        if not isinstance(v, (date, datetime)) and not clock_end and not YEAR.search(str(v)):
            out.append(f"{key}: {v} — write the whole date with its year (2027-03-14 or 2027-03-14T19:00:00-05:00)")
        if isinstance(v, datetime) and v.tzinfo and v.utcoffset() != v.astimezone(CHI).utcoffset() \
                and not any(n.startswith(f"{key}: ") for n in out):
            out.append(f"{key}: {v.isoformat()} — use Central time's UTC offset on that day")
    start, end = ex.get("start"), ex.get("end")
    if start and end:
        shown = [v.isoformat() if isinstance(v, (date, datetime)) else str(v)
                 for v in (written.get("start", written.get("date", start)), written.get("end", end))]
        if len(start) > 10 and len(end) > 10 and not end > start:
            out.append(f"end: {shown[1]} is not after start: {shown[0]}")
        elif central_day(end) < central_day(start):
            out.append(f"end: {shown[1]} is before start: {shown[0]}")
    return out


class ContentEvents(unittest.TestCase):
    def test_every_event_file(self):
        files = A.content_files(FOLDER)
        self.assertTrue(files, "content/events/ holds no event files")
        found = {f"content/events/{p.name}": problems(p) for p in files}
        bad = {name: msgs for name, msgs in found.items() if msgs}
        self.assertEqual(bad, {}, "fix these content/events files (content/events/README.md shows how):\n" + "\n".join(
            f"  {name}: {msg}" for name, msgs in bad.items() for msg in msgs))


class TheCheckItself(unittest.TestCase):
    """The checker catches what it is for (files written to a temporary folder)."""

    def check(self, head: str) -> list[str]:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "event.md"
            p.write_text(f"---\ntitle: X\n{head}---\nAn event.\n", encoding="utf-8")
            return problems(p)

    def test_good_files(self):
        self.assertEqual(self.check("start: 2027-03-19\nend: 2027-03-21\n"), [])
        self.assertEqual(self.check("start: 2027-01-10T19:00:00-06:00\nend: 2027-01-10T21:00:00-06:00\n"), [])
        self.assertEqual(self.check('start: 2026-11-07T19:00:00-06:00\nend: "21:00"\n'), [])
        self.assertEqual(self.check("start: 2027-06-10T19:00:00-05:00\n"), [])

    def test_a_year_left_out(self):
        self.assertEqual(len(self.check("start: January 10\n")), 1)
        self.assertIn("has no year", self.check("start: January 10\n")[0])
        self.assertIn("has no year", self.check("start: 2027-01-10\nend: 12 de enero\n")[0])
        self.assertIn("is a time of day without its date", self.check("start: 19:00\n")[0])

    def test_a_day_left_out(self):
        # English and Spanish alike (review of round 7: "marzo de 2027" became March 1); a Spanish 1st is a day
        for head in ("start: March 2027\n", "start: marzo de 2027\nlang: es\n", "start: Enero de 2027\n",
                     "start: marzo del 2027 a las 7 pm\nlang: es\n"):
            with self.subTest(head=head):
                msgs = self.check(head)
                self.assertEqual(len(msgs), 1, msgs)
                self.assertIn("has no day", msgs[0])
        self.assertEqual(self.check("start: 1° de marzo de 2027\nlang: es\n"), [])
        self.assertEqual(self.check("start: primero de marzo de 2027\nlang: es\n"), [])

    def test_an_offset_that_is_not_centrals(self):
        msgs = self.check("start: 2027-01-10T19:00:00-05:00\nend: 2027-01-10T21:00:00-06:00\n")
        self.assertEqual(len(msgs), 1)
        self.assertTrue(msgs[0].startswith("start: 2027-01-10T19:00:00-05:00 — -05:00 is not Central time's UTC "
                                           "offset on 2027-01-10 (-06:00)"), msgs)

    def test_an_end_not_after_the_start(self):
        self.assertIn("is before the start", self.check("start: 2027-03-19\nend: 2027-03-12\n")[0])
        self.assertEqual(self.check("start: 2027-03-19T19:00:00-05:00\nend: 2027-03-19T19:00:00-05:00\n"),
                         ["end: 2027-03-19T19:00:00-05:00 is not after start: 2027-03-19T19:00:00-05:00"])
        self.assertEqual(self.check("start: 2027-03-19T19:00:00-05:00\nend: 2027-03-18\n"),
                         ["end: 2027-03-18 is before start: 2027-03-19T19:00:00-05:00"])


if __name__ == "__main__":
    unittest.main()
