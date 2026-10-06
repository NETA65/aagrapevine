"""Instagram (scripts/sync/instagram.py): the saved pages it reads, and the removal re-check — a post Instagram
no longer shows (deleted, archived, made private) leaves the site, while a login wall or a block never removes
anything. No network: every request is answered from tests/fixtures/instagram/ (pages in the shape Instagram
served them in September 2026; the posts, captions and CDN addresses are made up).
Run:  python -m unittest tests.test_instagram -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import common  # noqa: E402
from scripts.sync import instagram as I  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "instagram"
USER = "alcoholicsanonymous_gv"
LISTED = ["DeKDjjTktaM", "DeHewrTktaL", "DeE59zTktaK", "Dd_wYDTktaI", "Dd9LlLTktaH", "Ddg21jTktaN"]
VANISHED = "DeCVK7TktaJ"            # 3 Oct: no longer listed, though older posts (1 and 2 Oct) still are
OLDER = ["Ddtuz7TktaP", "DdmAbTTktaO"]          # 25 and 22 Sep: dropped out of the listing the normal way


def fx(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- the saved pages
class SavedPages(unittest.TestCase):
    def test_profile_embed(self):
        ctx = I.parse_context_json(fx("profile-embed.html"))
        self.assertEqual((ctx["username"], ctx["posts_count"]), (USER, 3923))
        posts = [I.post_from_graphql(g["shortcode_media"], "gv", "profile_embed", USER) for g in ctx["graphql_media"]]
        self.assertEqual(sorted(p["shortcode"] for p in posts), sorted(LISTED))
        by = {p["shortcode"]: p for p in posts}
        self.assertEqual(by["DeKDjjTktaM"]["date"], "2026-10-06T15:00:00Z")
        self.assertEqual([by[s]["media_type"] for s in ("DeKDjjTktaM", "DeHewrTktaL", "DeE59zTktaK")],
                         ["image", "video", "carousel"])
        self.assertEqual(by["Dd9LlLTktaH"]["caption"], "", "a post without a caption: known to be empty")
        item = I.build_item(dict(by["DeKDjjTktaM"], thumb=None), {"gv": {"name": "AA Grapevine", "username": USER}}, None)
        self.assertEqual(item["title"], "Gratitude is an action word.")
        self.assertEqual(item["tags"], ["aagrapevine", "recovery"])
        self.assertEqual(item["url"], "https://www.instagram.com/p/DeKDjjTktaM/")

    def test_post_embed(self):
        data = I.parse_post_embed(fx("post-embed.html"))
        self.assertEqual((data["username"], data["media_type"], data["permalink"]),
                         (USER, "image", "https://www.instagram.com/p/DeCVK7TktaJ/"))
        self.assertEqual(data["caption"], "Three tools for a newcomer's first month.\n\nWhich helped you most?\n#aagrapevine")
        self.assertNotIn("comments", data["caption"])
        self.assertEqual(data["hover"], ["DeKDjjTktaM"], "the hover card's newest post, from its CDN cache key")
        self.assertEqual(I.date_from_media_id(data["media_id"]), "2026-10-03T15:00:00Z")

    def test_unusable_pages(self):
        self.assertIsNone(I.parse_post_embed(fx("post-embed-unavailable.html")))
        self.assertIsNone(I.parse_post_embed(fx("login-wall.html")))
        self.assertIsNone(I.parse_context_json(fx("login-wall.html")))

    def test_profile_page_keeps_only_the_accounts_own_posts(self):
        posts = I.parse_profile_html(fx("profile.html"), "gv", USER)
        self.assertEqual([p["shortcode"] for p in posts], ["DeKDjjTktaM", "DeHewrTktaL"])
        self.assertTrue(posts[1]["is_reel"])
        self.assertTrue(posts[0]["image_url"].endswith("_640.jpg"), "the smallest copy at least 480 px wide")


# --------------------------------------------------------------------------- the removal re-check
class Resp:
    def __init__(self, status: int, text: str = "", url: str = ""):
        self.status_code, self.text, self.url, self.headers = status, text, url, {}
        self.content = text.encode()


class FakeInstagram:
    """instagram.com as the module sees it. `gone`: posts whose embed is the generic page; `mode`: "ok", "wall"
    (every post embed is the login wall), "429" (post embeds rate-limited) or "404" (gone posts answer 404);
    `ok_first`: only that many post embeds of a run work, then the login wall (a block that begins mid-run)."""

    def __init__(self, gone=(), mode="ok", ok_first=None):
        self.gone, self.mode, self.ok_first = set(gone), mode, ok_first
        self.embeds: list[str] = []

    def get(self, url, headers=None, **kw):
        if url == f"https://www.instagram.com/{USER}/embed/":
            return Resp(200, fx("profile-embed.html"), url)
        m = re.search(r"instagram\.com/p/([A-Za-z0-9_-]+)/embed/captioned/", url)
        if m:
            self.embeds.append(m[1])
            if self.mode == "wall" or (self.ok_first is not None and len(self.embeds) > self.ok_first):
                return Resp(200, fx("login-wall.html"), url)
            if self.mode == "429":
                return Resp(429, "", url)
            if m[1] in self.gone:
                return Resp(404, "", url) if self.mode == "404" else Resp(200, fx("post-embed-unavailable.html"), url)
            return Resp(200, fx("post-embed.html"), url)
        return Resp(404, "", url)                       # the CDN (thumbnails, avatar) and anything else


class Removal(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-ig-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "raw").mkdir()
        self.thumbs = self.tmp / "ig"
        self.thumbs.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID", "IG_ANONYMOUS")}
        for p in (mock.patch.object(common, "RAW_DIR", self.tmp / "raw"), mock.patch.object(I, "THUMB_DIR", self.thumbs),
                  mock.patch.object(I.time, "sleep", lambda s: None), mock.patch.dict(os.environ, env, clear=True)):
            p.start()
            self.addCleanup(p.stop)
        # what the site knows: today's six listed posts and three older ones, each with its thumbnail
        items = []
        for sc in LISTED + [VANISHED] + OLDER:
            (self.thumbs / f"{sc}.webp").write_bytes(b"webp")
            rec = I.new_post(sc, "gv", "profile_embed", username=USER, caption=f"Post {sc}", media_type="image",
                             date=I.date_from_shortcode(sc), thumb=I.thumb_rel(sc))
            items.append(I.build_item(rec, {"gv": {"name": "AA Grapevine", "username": USER}}, None))
        common.save_raw("instagram", common.merge_items([], items)[0], extra={"profiles": {}})

    def run_once(self, web: FakeInstagram, *args: str) -> dict:
        web.embeds.clear()
        with mock.patch.object(I, "PoliteSession", lambda **kw: web):
            I.main(["--account", "gv", "--manual-file", str(self.tmp / "none.yml"), *args])
        return json.loads((self.tmp / "raw" / "instagram.json").read_text(encoding="utf-8"))

    @staticmethod
    def shortcodes(env: dict) -> set[str]:
        return {i["extra"]["shortcode"] for i in env["items"]}

    def age_marks(self, hours: float) -> None:
        """Pretend the "not there" marks were set `hours` ago."""
        p = self.tmp / "raw" / "instagram.json"
        env = json.loads(p.read_text(encoding="utf-8"))
        for v in env["removal"].values():
            if v.get("missing"):
                v["missing"] = iso(datetime.now(timezone.utc) - timedelta(hours=hours))
        p.write_text(json.dumps(env), encoding="utf-8")

    def test_a_vanished_post_leaves_after_two_answers_half_a_day_apart(self):
        web = FakeInstagram(gone={VANISHED})
        env = self.run_once(web)
        self.assertEqual(web.embeds[0], VANISHED, "the post that vanished from the listing is asked first")
        self.assertEqual(sorted(web.embeds), sorted([VANISHED] + OLDER), "only the posts that are not listed")
        self.assertIn(VANISHED, self.shortcodes(env), "one answer is not enough")
        self.assertEqual(env["stats"]["removal"]["missing"], [VANISHED])
        self.assertEqual(set(env["removal"]), {VANISHED, *OLDER})
        env = self.run_once(web)                           # a second answer an hour later: still not enough
        self.assertIn(VANISHED, self.shortcodes(env))
        self.age_marks(13)
        env = self.run_once(web)
        self.assertNotIn(VANISHED, self.shortcodes(env))
        self.assertEqual(env["stats"]["removal"]["removed"], [VANISHED])
        self.assertFalse((self.thumbs / f"{VANISHED}.webp").exists(), "its thumbnail is deleted too")
        self.assertTrue((self.thumbs / f"{OLDER[0]}.webp").exists())
        self.assertNotIn(VANISHED, env["removal"])
        self.assertEqual(self.shortcodes(env), set(LISTED + OLDER))

    def test_a_404_counts_as_not_there(self):
        web = FakeInstagram(gone={OLDER[1]}, mode="404")
        self.run_once(web)
        self.age_marks(20)
        env = self.run_once(web)
        self.assertNotIn(OLDER[1], self.shortcodes(env))

    def test_a_post_that_shows_again_loses_its_mark(self):
        self.run_once(FakeInstagram(gone={VANISHED}))
        self.age_marks(20)
        env = self.run_once(FakeInstagram())               # it was archived for a while, and is back
        self.assertIn(VANISHED, self.shortcodes(env))
        self.assertEqual(env["removal"][VANISHED].keys(), {"checked"})
        self.age_marks(20)
        env = self.run_once(FakeInstagram(gone={VANISHED}))
        self.assertIn(VANISHED, self.shortcodes(env), "a new first answer: it starts over")

    def test_a_post_back_in_the_listing_loses_its_mark(self):
        p = self.tmp / "raw" / "instagram.json"
        env = json.loads(p.read_text(encoding="utf-8"))
        old = iso(datetime.now(timezone.utc) - timedelta(days=3))
        env["removal"] = {LISTED[1]: {"checked": old, "missing": old}}
        p.write_text(json.dumps(env), encoding="utf-8")
        web = FakeInstagram()
        env = self.run_once(web)
        self.assertEqual(env["removal"][LISTED[1]].keys(), {"checked"})
        self.assertNotIn(LISTED[1], web.embeds, "a listed post is never asked")

    def test_a_login_wall_removes_nothing(self):
        """Every post embed is the login wall — the generic page a gone post gets looks no different, so the
        newest listed post (which surely exists) is asked too, and nothing is decided."""
        web = FakeInstagram(mode="wall")
        for _ in range(3):
            env = self.run_once(web)
            self.age_marks(48)
        self.assertEqual(self.shortcodes(env), set(LISTED + [VANISHED] + OLDER))
        self.assertIn("DeKDjjTktaM", web.embeds, "the control: the newest listed post")
        self.assertFalse(any(v.get("missing") for v in env["removal"].values()))
        self.assertTrue(any("nothing was decided" in w for w in env["stats"]["warnings"]), env["stats"].get("warnings"))

    def test_a_block_that_begins_during_the_run_removes_nothing(self):
        """The first post embed works, then Instagram serves its login wall: an answer that came after the last
        embed that worked proves nothing. The control request (the newest listed post) meets the wall too."""
        web = FakeInstagram(ok_first=1)
        env = self.run_once(web)
        self.assertEqual(web.embeds, [VANISHED, OLDER[1], OLDER[0], "DeKDjjTktaM"], "the last one: the control")
        for _ in range(2):
            self.age_marks(48)
            env = self.run_once(web)
        self.assertEqual(self.shortcodes(env), set(LISTED + [VANISHED] + OLDER))
        self.assertFalse(any(v.get("missing") for v in env["removal"].values()))
        self.assertTrue(any("nothing was decided" in w for w in env["stats"]["warnings"]), env["stats"].get("warnings"))

    def test_an_answer_before_a_working_embed_counts(self):
        """The gone post is asked first and the others work after it: no control request is needed."""
        web = FakeInstagram(gone={VANISHED})
        env = self.run_once(web)
        self.assertNotIn("DeKDjjTktaM", web.embeds)
        self.assertEqual(env["stats"]["removal"]["missing"], [VANISHED])
        web = FakeInstagram(gone={VANISHED, *OLDER})                # the last one asked is gone too: a control
        self.run_once(web)
        self.assertEqual((len(web.embeds), web.embeds[-1]), (4, "DeKDjjTktaM"))

    def test_a_rate_limit_stops_the_recheck(self):
        web = FakeInstagram(gone={VANISHED}, mode="429")
        env = self.run_once(web)
        self.assertEqual(web.embeds, [VANISHED], "one 429 and no further post embed is asked")
        self.assertEqual(env["removal"], {})
        self.assertTrue(any("HTTP 429" in w for w in env["stats"]["warnings"]))
        self.assertIn(VANISHED, self.shortcodes(env))

    def test_no_enrich_asks_no_post_embed(self):
        web = FakeInstagram(gone={VANISHED})
        env = self.run_once(web, "--no-enrich")
        self.assertEqual(web.embeds, [])
        self.assertNotIn("removal", env["stats"])

    def test_the_cap_and_oldest_check_first(self):
        web = FakeInstagram()
        self.run_once(web, "--recheck", "1")
        self.assertEqual(web.embeds, [VANISHED])
        self.run_once(web, "--recheck", "1")
        self.assertEqual(web.embeds, [OLDER[1]], "never checked: the oldest post first")
        self.run_once(web, "--recheck", "1")
        self.assertEqual(web.embeds, [OLDER[0]])
        self.run_once(web, "--recheck", "1")
        self.assertEqual(web.embeds, [VANISHED], "then the one checked longest ago")

    def test_another_accounts_embeds_prove_nothing(self):
        """Review of round 7: La Viña's posts answering the generic page while Grapevine's embeds work (La Viña turned
        embedding off, say) were marked "not there" — and removed, pictures and all, the next night. Only an embed of
        the same account that works after the answer proves it; with none of La Viña's posts listed today, nothing is
        decided for them."""
        lv = ["DcAAAATktaA", "DcBBBBTktaB", "DcCCCCTktaC"]
        p = self.tmp / "raw" / "instagram.json"
        env = json.loads(p.read_text(encoding="utf-8"))
        accounts = {"gv": {"name": "AA Grapevine", "username": USER}, "lv": {"name": "La Viña", "username": "lavina"}}
        for sc in lv:
            (self.thumbs / f"{sc}.webp").write_bytes(b"webp")
            rec = I.new_post(sc, "lv", "profile_embed", username="lavina", caption=f"Post {sc}", media_type="image",
                             date=I.date_from_shortcode(sc), thumb=I.thumb_rel(sc))
            env["items"].append(I.build_item(rec, accounts, None))
        p.write_text(json.dumps(env), encoding="utf-8")
        web = FakeInstagram(gone=set(lv))
        env = self.run_once(web, "--recheck", "10")
        self.assertTrue(set(lv) <= set(web.embeds), "La Viña's posts were asked …")
        self.assertTrue({VANISHED, *OLDER} <= set(web.embeds), "… and Grapevine's worked after them")
        self.assertFalse([sc for sc in lv if (env["removal"].get(sc) or {}).get("missing")], env["removal"])
        self.assertTrue(any("nothing was decided" in w for w in env["stats"]["warnings"]), env["stats"].get("warnings"))
        for _ in range(2):
            self.age_marks(48)
            env = self.run_once(web, "--recheck", "10")
        self.assertTrue(set(lv) <= self.shortcodes(env))
        self.assertTrue(all((self.thumbs / f"{sc}.webp").exists() for sc in lv))

    def sweep(self, web: FakeInstagram, prev: list[dict], listed: dict, records: dict) -> tuple[set, dict, dict]:
        state: dict = {}
        stats: dict = {}
        with mock.patch.object(I, "PoliteSession", lambda **kw: web):
            fx = I.Fetcher({}, deadline=I.time.monotonic() + 600)
            gone = I.removal_sweep(fx, prev, records, listed, state, 5, stats)
        return gone, state, stats

    def test_a_reel_is_proved_only_by_a_reel(self):
        """…and the same kind of post: a Reel's embed page may come in another shape than a photo's."""
        acct = {"gv": {"name": "AA Grapevine", "username": USER}}

        def known(sc: str, reel: bool = False) -> dict:
            rec = I.new_post(sc, "gv", "profile_embed", username=USER, caption=f"Post {sc}", media_type="video" if reel
                             else "image", date=I.date_from_shortcode(sc), is_reel=reel)
            return I.build_item(rec, acct, None)
        prev = [known(VANISHED, reel=True), known(OLDER[0])]
        day = I.date_from_shortcode(LISTED[0])
        records = {LISTED[0]: I.new_post(LISTED[0], "gv", "profile_embed", date=day)}
        gone, state, stats = self.sweep(FakeInstagram(gone={VANISHED}), prev, {"gv": {LISTED[0]: day}}, records)
        self.assertEqual(gone, set())
        self.assertNotIn("missing", state.get(VANISHED, {}), "a photo's embed that worked proves nothing about a Reel")
        self.assertTrue(any("nothing was decided" in w for w in stats["warnings"]))
        # a Reel listed today is asked as the control: now the answer counts
        reel_day = I.date_from_shortcode(LISTED[1])
        records[LISTED[1]] = I.new_post(LISTED[1], "gv", "profile_embed", date=reel_day, is_reel=True)
        web = FakeInstagram(gone={VANISHED})
        gone, state, stats = self.sweep(web, prev, {"gv": {LISTED[0]: day, LISTED[1]: reel_day}}, records)
        self.assertEqual(web.embeds[-1], LISTED[1], "the control: the newest listed Reel")
        self.assertIn("missing", state[VANISHED])
        self.assertNotIn("warnings", stats)

    def test_manual_posts_are_not_rechecked(self):
        p = self.tmp / "raw" / "instagram.json"
        env = json.loads(p.read_text(encoding="utf-8"))
        for it in env["items"]:
            if it["extra"]["shortcode"] == VANISHED:
                it["extra"]["manual"] = True
        p.write_text(json.dumps(env), encoding="utf-8")
        (self.tmp / "list.yml").write_text(f"posts:\n  - https://www.instagram.com/p/{VANISHED}/\n", encoding="utf-8")
        web = FakeInstagram(gone={VANISHED})
        with mock.patch.object(I, "PoliteSession", lambda **kw: web):
            I.main(["--account", "gv", "--manual-file", str(self.tmp / "list.yml")])
        self.assertEqual(sorted(web.embeds), sorted(OLDER), "the hand-listed post is the YAML's to decide")


class ManualListMistake(unittest.TestCase):
    """content/instagram.yml with a YAML mistake: the hand-listed posts of the last run stay, pictures and all,
    and the note names the file and the line — the list is never read as empty (that would drop them and
    delete their pictures). Once the file is right again, it decides as before."""

    def setUp(self):
        Removal.setUp(self)

    def run_with(self, yml: str, *args: str) -> dict:
        (self.tmp / "list.yml").write_text(yml, encoding="utf-8")
        with mock.patch.object(I, "PoliteSession", lambda **kw: FakeInstagram()):
            I.main(["--account", "gv", "--manual-file", str(self.tmp / "list.yml"), "--no-enrich", *args])
        return json.loads((self.tmp / "raw" / "instagram.json").read_text(encoding="utf-8"))

    def test_the_hand_listed_posts_stay_until_the_file_is_fixed(self):
        hand = [OLDER[0], LISTED[0]]                    # one only on the list, one also in today's listing
        env = self.run_with("posts:\n" + "".join(f"  - url: https://www.instagram.com/p/{sc}/\n" for sc in hand), "--keep", "2")
        manual = {i["extra"]["shortcode"] for i in env["items"] if i["extra"].get("manual")}
        self.assertEqual(manual, set(hand))
        self.assertTrue((self.thumbs / f"{OLDER[0]}.webp").exists())
        broken = ("posts:\n  - url: https://www.instagram.com/p/DdmAbTTktaO/\n"
                  '    caption: "a quote left open\n  - url: https://www.instagram.com/p/Dd9LlLTktaH/\n')
        env = self.run_with(broken, "--keep", "2")
        by = {i["extra"]["shortcode"]: i for i in env["items"]}
        self.assertEqual({sc for sc, i in by.items() if i["extra"].get("manual")}, set(hand), "still hand-listed")
        self.assertTrue((self.thumbs / f"{OLDER[0]}.webp").exists(), "its picture is not deleted")
        self.assertEqual(by[OLDER[0]]["image"], I.thumb_rel(OLDER[0]))
        self.assertTrue(env["ok"])
        self.assertEqual(env["stats"]["manual"], 2)
        note = [w for w in env["stats"]["warnings"] if "YAML error" in w]
        self.assertEqual(len(note), 1)
        self.assertRegex(note[0], r"^list\.yml line 5: YAML error — .+ — the 2 hand-listed post\(s\) of the last "
                                  r"update are kept, pictures and all, until the file is fixed$")
        env = self.run_with("posts: []\n", "--keep", "2")         # fixed: the list is empty now — they go
        self.assertFalse([i for i in env["items"] if i["extra"].get("manual")])
        self.assertFalse((self.thumbs / f"{OLDER[0]}.webp").exists())
        self.assertNotIn("warnings", env["stats"])

    def test_the_note_names_the_repository_file(self):
        self.assertEqual(I._file_name(I.MANUAL_FILE), "content/instagram.yml")
        bad = self.tmp / "instagram.yml"
        bad.write_text("posts:\n  - url: x\n   bad: [\n", encoding="utf-8")
        records, problems = I.load_manual([], bad)
        self.assertIsNone(records)
        self.assertRegex(problems[0], r"^instagram\.yml line \d+: YAML error — \S")


class ListingFloor(unittest.TestCase):
    def test_pinned_posts_do_not_lower_the_floor(self):
        self.assertEqual(I._listing_floor(["2026-10-06T15:00:00Z", "2026-10-02T15:00:00Z", "2026-08-01T15:00:00Z"]),
                         "2026-10-02T15:00:00Z")
        self.assertIsNone(I._listing_floor([]))


if __name__ == "__main__":
    unittest.main()
