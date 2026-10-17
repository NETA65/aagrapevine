"""Browser checks: a BUILT website, served the way GitHub Pages serves it, in a real browser — what the offline tests
(tests/*.py, the site's scripts in Node) cannot see: what the browser draws and how the offline worker behaves.

The Code check runs them on its test build (.github/workflows/check.yml, the runner's Google Chrome). On a computer:

    PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy --output=_site          (a build as GitHub Pages gets it)
    GV_BROWSER_SITE=_site python -m unittest discover -s tests/browser -t tests -v

They need Playwright (pip install -r scripts/ops/requirements-browser.txt), Node.js (the site server,
scripts/ops/serve_site.mjs) and Google Chrome or Microsoft Edge (GV_BROWSER_CHANNEL picks one). Without
GV_BROWSER_SITE, Playwright or a browser they are skipped — so the normal test run (python -m unittest discover -s
tests) is unchanged; GV_BROWSER_REQUIRED=1 (the Code check) makes a missing browser a failure instead, and
GV_BROWSER_VERBOSE=1 prints the focus rings' measured contrasts. The browser never reaches another site
(scripts/ops/site_browser.py).
"""
