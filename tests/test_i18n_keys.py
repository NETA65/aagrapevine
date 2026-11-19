"""The site's strings (src/_i18n/*.json) as the build reads them: eleventy.config.js loadI18n() merges EVERY
file there, in alphabetical order, into one table — so a key written in two files is silently taken from the
later one. Across all the files:

  * no key is in two files (each string has one home);
  * every key has an English AND a Spanish text (a key whose two texts are both empty, like `lang.und`, is
    deliberate);
  * the {placeholders} are the same in both languages (a {date} missing in Spanish would print nothing, one
    only in Spanish would print "{date}").

    python -m unittest tests.test_i18n_keys -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "src" / "_i18n"
PLACEHOLDER = re.compile(r"\{(\w+)\}")          # the build's interpolate() in eleventy.config.js


def load() -> dict[str, dict[str, dict]]:
    """{file name: {key: value}} for every src/_i18n/*.json, in the loader's order."""
    return {f.name: json.loads(f.read_text(encoding="utf-8")) for f in sorted(I18N.glob("*.json"))}


class Strings(unittest.TestCase):
    def setUp(self):
        self.files = load()

    def test_there_are_files(self):
        self.assertGreater(len(self.files), 5)
        self.assertIn("freshness.json", self.files)

    def test_no_key_in_two_files(self):
        where: dict[str, list[str]] = defaultdict(list)
        for name, data in self.files.items():
            self.assertIsInstance(data, dict, name)
            for key in data:
                where[key].append(name)
        twice = {k: v for k, v in where.items() if len(v) > 1}
        self.assertEqual(twice, {}, "a key in two files: the later file wins silently — keep one")

    def test_english_and_spanish(self):
        for name, data in self.files.items():
            for key, v in data.items():
                with self.subTest(file=name, key=key):
                    self.assertIsInstance(v, dict)
                    self.assertTrue({"en", "es"} <= set(v), "both languages")
                    en, es = v["en"], v["es"]
                    self.assertIsInstance(en, str)
                    self.assertIsInstance(es, str)
                    if en.strip() or es.strip():
                        self.assertTrue(en.strip() and es.strip(), "one language is empty")

    def test_the_same_placeholders(self):
        for name, data in self.files.items():
            for key, v in data.items():
                if not isinstance(v, dict):
                    continue
                with self.subTest(file=name, key=key):
                    self.assertEqual(sorted(set(PLACEHOLDER.findall(str(v.get("en", ""))))),
                                     sorted(set(PLACEHOLDER.findall(str(v.get("es", ""))))))


if __name__ == "__main__":
    unittest.main()
