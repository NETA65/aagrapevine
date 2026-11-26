"""Timestamp-only data churn: a raw file whose content did not change is not written again, and every run's times
still reach data/site/status.json (scripts/sync/common.py save_raw, RUN_STAMPS, with_run_stamps; build_data's
Ctx.load_raw; run_all._attempted_on).

  * Stamps         — only_stamps_differ / without_stamps: an envelope's own `updated`, `attempted`, `generated` and the
                     `…seconds` of its `stats` are run times; a time inside the data (an item's `last_seen`, an
                     item's own `updated`) is content.
  * SaveRaw        — the same content again: the file is left byte for byte, this run's times go to RUN_STAMPS and
                     load_raw gives them; new content (also a last_seen moved, a failure) is written as before.
  * StatusKeepsIt  — build_data takes a source's times from this run (RUN_STAMPS) or the last status.json when they
                     are newer than its file's, so status.json shows the fresh `attempted` (the "not checked" warning,
                     the Morning check's `full_update`) — but never a last success for a file that never had one.
  * TheMorning     — run_all._attempted_on ("read today already?") also asks the last status.json.
  * WholeRun       — two builds over an unchanged source: the raw file unchanged, status.json's attempted and the
                     single-source site file's `updated` (the site's "Updated …" lines) are the second run's.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import run_all  # noqa: E402

T_ADD, T0, T1, T2 = "2026-11-25T06:00:00Z", "2026-11-25T12:00:00Z", "2026-11-25T18:00:00Z", "2026-11-26T02:46:00Z"


def item(i: int, last_seen: str = T0) -> dict:
    return {"id": f"yt:{i}", "source": "youtube", "kind": "video", "url": f"https://youtube.com/watch?v={i}",
            "title": f"Video {i}", "lang": "en", "date": "2026-11-20T12:00:00Z", "first_seen": "2026-11-20T12:00:00Z",
            "last_seen": last_seen, "category": "gv", "status": "ok", "extra": {}}


class Stamps(unittest.TestCase):
    def test_run_times_only(self):
        a = {"source": "x", "updated": T0, "attempted": T0, "ok": True, "stats": {"seconds": 3.7, "new": 0,
                                                                                    "backfill_seconds": 9}, "items": []}
        b = {**a, "updated": T1, "attempted": T1, "stats": {"seconds": 3.2, "new": 0, "backfill_seconds": 12}}
        self.assertTrue(common.only_stamps_differ(a, b))
        self.assertTrue(common.only_stamps_differ({"generated": T0, "x": 1}, {"generated": T1, "x": 1}))
        self.assertFalse(common.only_stamps_differ(a, a), "the same: nothing differs")
        for content in ({"stats": {**a["stats"], "new": 1}}, {"ok": False}, {"items": [item(1)]}):
            with self.subTest(content=content):
                self.assertFalse(common.only_stamps_differ(a, {**b, **content}))

    def test_a_time_inside_the_data_is_content(self):
        a = {"updated": T0, "items": [item(1, T0)]}
        self.assertFalse(common.only_stamps_differ(a, {"updated": T1, "items": [item(1, T1)]}), "last_seen")
        nested = {"updated": T0, "shows": {"gv": {"updated": T0}}}
        self.assertFalse(common.only_stamps_differ(nested, {"updated": T1, "shows": {"gv": {"updated": T1}}}))
        # what reading the file back gives: a date written as text is the same date
        self.assertTrue(common.only_stamps_differ({"d": date(2026, 11, 25), "updated": T0}, {"d": "2026-11-25", "updated": T1}))


class TempRaw(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-churn-"))
        self.raw = self.tmp / "data" / "raw"
        self.raw.mkdir(parents=True)
        for p in (mock.patch.object(common, "RAW_DIR", self.raw), mock.patch.object(B, "RAW_DIR", self.raw),
                  mock.patch.dict(common.RUN_STAMPS, clear=True)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def save(self, its: list[dict], at: str, **kw) -> None:
        with mock.patch.object(common, "now_iso", return_value=at):
            common.save_raw("youtube", its, **kw)

    def settled(self, its: list[dict], at: str = T0, **kw) -> None:
        """The source as after a run that found these items already there: one save that adds them (T_ADD), one
        that finds them again (`at`: its `changes` are zero — content — so it is written)."""
        self.save(its, T_ADD, **kw)
        self.save(its, at, **kw)

    def text(self) -> str:
        return (self.raw / "youtube.json").read_text(encoding="utf-8")


class SaveRaw(TempRaw):
    def test_the_same_content_is_not_written_again(self):
        self.settled([item(1), item(2)], T0, stats={"seconds": 3.7, "new": 0})
        before = self.text()
        self.save([item(1), item(2)], T1, stats={"seconds": 4.1, "new": 0})
        self.assertEqual(self.text(), before, "byte for byte")
        self.assertEqual(json.loads(before)["attempted"], T0)
        # this run's times: RUN_STAMPS, and every reader through load_raw
        stamp = common.RUN_STAMPS[str(self.raw / "youtube.json")]
        self.assertEqual((stamp["updated"], stamp["attempted"], stamp["stats"]["seconds"]), (T1, T1, 4.1))
        env = common.load_raw("youtube")
        self.assertEqual((env["updated"], env["attempted"], env["stats"]["seconds"]), (T1, T1, 4.1))
        # the next save that changes something writes the file, with its own times, and forgets the stamp
        self.save([item(1), item(2), item(3)], T2, stats={"seconds": 4.0, "new": 1})
        env = json.loads(self.text())
        self.assertEqual((env["attempted"], len(env["items"]), env["changes"]["added"]), (T2, 3, 1))
        self.assertNotIn(str(self.raw / "youtube.json"), common.RUN_STAMPS)

    def test_a_moved_last_seen_or_a_failure_is_written(self):
        self.settled([item(1)], T0)
        self.save([item(1, T1)], T1)
        self.assertEqual(json.loads(self.text())["items"][0]["last_seen"], T1)
        self.save([], T2, ok=False, error="no feed answered")
        env = json.loads(self.text())
        self.assertEqual((env["ok"], env["error"], env["updated"], env["attempted"]), (False, "no feed answered", T1, T2))
        # the same failure again: only `attempted` would move — kept in RUN_STAMPS; the last success stays
        before = self.text()
        self.save([], "2026-11-26T08:00:00Z", ok=False, error="no feed answered")
        self.assertEqual(self.text(), before)
        env = common.load_raw("youtube")
        self.assertEqual((env["ok"], env["updated"], env["attempted"]), (False, T1, "2026-11-26T08:00:00Z"))

    def test_a_run_after_one_that_added_items_is_written_once(self):
        # its `changes` ({"added": 1} → {"added": 0}) are this run's: content — after that, nothing moves
        self.save([item(1)], T_ADD)
        self.assertEqual(json.loads(self.text())["changes"]["added"], 1)
        self.save([item(1)], T0)
        self.assertEqual((json.loads(self.text())["changes"]["added"], json.loads(self.text())["attempted"]), (0, T0))
        self.save([item(1)], T1)
        self.assertEqual(json.loads(self.text())["attempted"], T0)

    def test_a_new_file_is_written(self):
        self.save([item(1)], T0)
        self.assertTrue((self.raw / "youtube.json").exists())
        self.assertEqual(common.RUN_STAMPS, {})


class StatusKeepsIt(TempRaw):
    def ctx(self, previous: dict | None = None) -> B.Ctx:
        ctx = B.Ctx(offline=True)
        ctx.load_raw(previous)
        return ctx

    def test_this_runs_times_and_the_last_status(self):
        self.settled([item(1)], T0)
        self.save([item(1)], T1)
        self.assertEqual(self.ctx().raw["youtube"]["attempted"], T1, "this run's (RUN_STAMPS)")
        # a later run that does not read the source (a quick refresh): the file is the T0 one; the last status.json
        # has T1 (it kept this run's times) — the newest wins, so the source is not "not checked"
        common.RUN_STAMPS.clear()
        prev = {"sources": [{"source": "youtube", "ok": True, "count": 1, "updated": T1, "attempted": T1}]}
        env = self.ctx(prev).raw["youtube"]
        self.assertEqual((env["updated"], env["attempted"]), (T1, T1))
        self.assertEqual(json.loads(self.text())["attempted"], T0, "the file itself is not touched")
        # an older status.json, or sample data, never moves a time back
        env = self.ctx({"sources": [{"source": "youtube", "updated": "2026-11-01T00:00:00Z",
                                     "attempted": "2026-11-01T00:00:00Z", "count": 1}]}).raw["youtube"]
        self.assertEqual(env["attempted"], T0)
        env = self.ctx({"fixture": True, "sources": [{"source": "youtube", "attempted": T2, "count": 1}]}).raw["youtube"]
        self.assertEqual(env["attempted"], T0)

    def test_never_a_last_success_for_a_file_that_never_had_one(self):
        self.save([], T0, ok=False, error="no feed answered")
        prev = {"sources": [{"source": "youtube", "ok": True, "count": 0, "updated": T1, "attempted": T1}]}
        env = self.ctx(prev).raw["youtube"]
        self.assertEqual((env["updated"], env["attempted"]), (None, T1))


class TheMorning(TempRaw):
    def test_read_today_also_asks_the_last_status(self):
        tz = timezone(timedelta(hours=-6))
        self.save([item(1)], "2026-11-24T12:00:00Z")
        day = date(2026, 11, 25)
        self.assertFalse(run_all._attempted_on("youtube", day, tz))
        site = self.raw.parent / "site"
        site.mkdir()
        (site / "status.json").write_text(json.dumps({"sources": [{"source": "youtube", "attempted": T1}]}),
                                          encoding="utf-8")
        self.assertTrue(run_all._attempted_on("youtube", day, tz), "an earlier run today (the file unchanged)")
        (site / "status.json").write_text(json.dumps({"fixture": True, "sources": [{"source": "youtube", "attempted": T1}]}),
                                          encoding="utf-8")
        self.assertFalse(run_all._attempted_on("youtube", day, tz), "sample data says nothing")
        # a test's raw folder that is not a data/raw: no status.json is looked for
        with mock.patch.object(common, "RAW_DIR", self.tmp):
            self.assertEqual(run_all._last_status_row("youtube"), {})


class WholeRun(TempRaw):
    def setUp(self):
        super().setUp()
        self.out = self.tmp / "data" / "site"
        self.cfg = {**common.load_config(), "recurring_events": [], "meeting": {}}
        self.cfg["sources"] = {**(self.cfg.get("sources") or {}), "ics_feeds": []}
        self.glossary, self.overrides = self.tmp / "glossary.yml", self.tmp / "overrides.yml"
        self.glossary.write_text("keep:\n  - AA Grapevine\n", encoding="utf-8")
        self.overrides.write_text("{}\n", encoding="utf-8")

    def build(self, at: str) -> dict:
        real = B.T.Translator
        with mock.patch.object(B, "load_config", lambda: self.cfg), mock.patch.object(B, "STATE_DIR", self.tmp / "state"), \
                mock.patch.object(B.T, "Translator", lambda **kw: real(cache_path=self.tmp / "cache.json", use_model=False,
                                                                       glossary_path=self.glossary,
                                                                       overrides_path=self.overrides,
                                                                       models_dir=self.tmp / "models", download=False)), \
                mock.patch.object(B.T, "_DEFAULT", None), mock.patch.object(B, "now_iso", return_value=at):
            self.assertEqual(B.main(["--out", str(self.out), "--offline"]), 0)
        return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in self.out.glob("*.json")}

    def test_status_json_keeps_the_times_the_raw_file_no_longer_takes(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        vids = [{**item(1), "date": recent, "first_seen": recent, "last_seen": recent}]
        self.settled(vids, T0)
        one = self.build(T0)
        self.save(vids, T1)                                   # the next run: the same videos
        raw_before = self.text()
        two = self.build(T1)
        self.assertEqual(self.text(), raw_before)
        self.assertEqual(json.loads(raw_before)["attempted"], T0, "the raw file keeps its old times")
        row = next(r for r in two["status"]["sources"] if r["source"] == "youtube")
        self.assertEqual((row["updated"], row["attempted"]), (T1, T1), "status.json has this run's")
        # the site's "Updated …" line reads the single-source file's `updated`: still the last read
        self.assertEqual((one["videos"]["updated"], two["videos"]["updated"]), (T0, T1))
        # a third run in another process (RUN_STAMPS empty), not reading YouTube: status.json still says T1
        common.RUN_STAMPS.clear()
        three = self.build(T2)
        row = next(r for r in three["status"]["sources"] if r["source"] == "youtube")
        self.assertEqual(row["attempted"], T1)


if __name__ == "__main__":
    unittest.main()
