"""The search-result descriptions: each page that takes its <meta name="description"> from src/_i18n (front matter
`descKey`, base.njk) says it in at most 160 characters in each language — what Google and Bing show before they
cut it off with "…" — and in at least 70 (a few words say too little). Measured as the page prints it: the
{platform} of the committee meeting filled in with "Zoom" (config/site.yml meeting.platform, and base.njk's
default); no other {placeholder} is left. Facts first, never promotion (AA's Tradition 11): the wording is the
writer's; this only keeps it whole in the results.

(Pages with their own `description` — the month pages, the stand-alone redirect and share pages — are not covered.)

    python -m unittest tests.test_seo_descriptions -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LONGEST, SHORTEST = 160, 70


def strings() -> dict:
    out: dict = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


def desc_keys() -> dict[str, str]:
    """{descKey: the page file that names it} for src/pages/*.njk."""
    keys: dict[str, str] = {}
    for p in sorted((ROOT / "src" / "pages").glob("*.njk")):
        m = re.match(r"---\n(.*?)\n---", p.read_text(encoding="utf-8").replace("\r\n", "\n"), re.S)
        data = yaml.safe_load(m.group(1)) if m else None
        if isinstance(data, dict) and data.get("descKey"):
            keys[str(data["descKey"])] = p.name
    return keys


class Descriptions(unittest.TestCase):
    def test_every_description_fits_the_results(self):
        s, keys = strings(), desc_keys()
        self.assertGreater(len(keys), 20)
        for key in ("community.digest.meta_desc", "expenses.meta_desc", "read.gvr.meta_desc", "orientation.meta_desc",
                    "published.meta_desc", "monthly.meta_desc"):
            self.assertIn(key, keys, "the six strings (eight pages) that were too long in October 2026 are checked")
        for key, page in sorted(keys.items()):
            for lang in ("en", "es"):
                with self.subTest(page=page, key=key, lang=lang):
                    text = s[key][lang].replace("{platform}", "Zoom")
                    self.assertNotRegex(text, r"\{\w+\}", "a placeholder base.njk does not fill")
                    self.assertLessEqual(len(text), LONGEST, f"{len(text)} characters: {text}")
                    self.assertGreaterEqual(len(text), SHORTEST, text)


if __name__ == "__main__":
    unittest.main()
