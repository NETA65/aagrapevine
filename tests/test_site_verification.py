"""Google Search Console's ownership file (src/pages/google-site-verification.11ty.js): published at the site root under
its exact name, holding exactly Google's one line, and left out of every collection (sitemap, site search)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402


class SiteVerification(unittest.TestCase):
    def test_the_file_google_fetches(self):
        got = run_js(self, 'const m = await imp("src/pages/google-site-verification.11ty.js");'
                           'out({data: m.data, body: m.render()});', needs_modules=False)
        self.assertEqual(got["data"]["permalink"], "/googlef96fc15466439295.html",
                         "Google looks for the file at the site root (/aagrapevine/…), not in a folder")
        self.assertIs(got["data"]["layout"], False, "no page around it")
        self.assertIs(got["data"]["eleventyExcludeFromCollections"], True, "not in the sitemap or the site search")
        self.assertEqual(got["body"], "google-site-verification: googlef96fc15466439295.html")


if __name__ == "__main__":
    unittest.main()
