"""Draw the site's icons: the installable app's (the manifest's icons, the iPhone home-screen icon) and the
favicons (browser tabs, bookmarks, Google's search results, the OpenSearch and RSS pictures).

    python -m scripts.dev.make_app_icons              both sets
    python -m scripts.dev.make_app_icons favicons     the favicons only (the five app icons are left as they are)
    python -m scripts.dev.make_app_icons app          the app icons only

Writes into src/assets/img/ (commit the files; the build only copies them — and, as they sit under src/assets/,
a new drawing changes build.version, so the service worker's app shell takes it up too). To look at a new drawing,
build the whole site or start `npm start` again: an --incremental preview copies a changed icon to /assets/img/
only, never to its root copies (/favicon.ico, /favicon.svg, /apple-touch-icon*.png — eleventy.config.js):

  the app (APP_JOBS)
    app-icon-192.png, app-icon-512.png                  "any": a rounded square, transparent corners
    app-icon-maskable-192.png, app-icon-maskable-512.png "maskable": full bleed, the grapes inside the
                                                         80 % safe circle, so Android can cut any shape
    apple-touch-icon-180.png                            iPhone / iPad: full bleed, no transparency
                                                         (iOS rounds the corners itself); the build also
                                                         publishes it at /apple-touch-icon.png and
                                                         /apple-touch-icon-precomposed.png (eleventy.config.js)
  the favicons (FAVICON_JOBS, FAVICON_ICO, FAVICON_SVG) — the grape icon everywhere a site icon shows; the
  NETA 65 logo (logo-wide.png) is the header's wordmark only (the owner's rule, round 37)
    favicon.ico           16, 32 and 48 px in one file; the build publishes it at /favicon.ico
    favicon.svg           the same tile and grapes as vectors (Chrome, Edge, Firefox); published at /favicon.svg.
                          Google Search reads no SVG: the PNGs and the ICO are what it can pick from
    favicon-32.png        the OpenSearch picture (src/pages/opensearch.11ty.js: 32 x 32)
    favicon-48.png        <link rel="icon" sizes="48x48">: Google asks for a multiple of 48 px
    favicon-96.png        <link rel="icon" sizes="96x96"> and the RSS feeds' <image> (src/pages/feed.11ty.js)
  (src/_includes/partials/icon-links.njk names them in every page's <head>; the 192 px one is app-icon-192.png.)

The picture: the site hero's navy -> NETA-blue gradient (main.css .gv-hero) with a warm glow and
the site's grape-cluster mark (src/_includes/icons/grapes.svg) in the hero's "vine light" gold.
No text: at launcher size (48 px) words can't be read. Everything is drawn at 4x and scaled down,
so the edges stay crisp. At 16 px the eight small grapes would blur into one gold blot, so the
16 px picture of favicon.ico (and favicon.svg, which browsers draw at 16 and 32 px in a tab) uses
SMALL: a bolder mark of the same cluster — six bigger grapes in three rows, a bigger leaf, a thicker
stem. The navy tile is the background in every size, so the icon reads on a light tab bar and on a
dark one alike. Only Pillow + numpy (both already installed for the content sync).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "src" / "assets" / "img"
SS = 4  # supersampling factor

# .gv-hero background: linear-gradient(135deg, #0f172a 0%, #0b2f55 38%, #025a94 72%, #0170b9 100%)
STOPS = [(0.0, (0x0F, 0x17, 0x2A)), (0.38, (0x0B, 0x2F, 0x55)), (0.72, (0x02, 0x5A, 0x94)), (1.0, (0x01, 0x70, 0xB9))]
GOLD = (0xFF, 0xD7, 0x9A)        # .gv-hero-title em — "vine light" gold
GOLD_DEEP = (0xE8, 0xA8, 0x4E)
GOLD_HI = (0xFF, 0xF1, 0xD6)
GOLD_RIM = (0xB8, 0x76, 0x2A)    # SMALL's grape rim: darker, so the grapes stay apart at 16 px
LEAF = (0x8F, 0xD0, 0x8A)        # --c-vine (dark theme)
VEIN = (0x5E, 0xA8, 0x5A)
STEM = (0xD9, 0xB0, 0x72)
SHADOW = (4, 14, 34)             # under the grapes (alpha 150 / 255, blurred)
# the warm glow behind the grapes (the hero's string lights): a circle at (0.5, 0.47) of the side, radius 0.46,
# its strength (1 - distance) ** GLOW_FALL * GLOW_ALPHA
GLOW = (255, 196, 110)
GLOW_CX, GLOW_CY, GLOW_R = 0.5, 0.47, 0.46
GLOW_FALL, GLOW_ALPHA = 1.8, 0.30
CORNER = 0.22                    # the rounded tile's corner radius, a share of its side

# grapes.svg (viewBox 24): the eight grapes, back row first
GRAPES = [(9, 8.5), (13.5, 8.5), (7, 12.5), (11.2, 12.5), (15.5, 12.3), (9.2, 16.4), (13.5, 16.4), (11.3, 20.2)]
R = 2.2
CENTER = (11.4, 12.6)   # visual centre of stem + leaf + cluster in the 24-unit box


@dataclass(frozen=True)
class Mark:
    """A grape cluster in the 24-unit box of grapes.svg. `leaf`: two cubic Béziers (start, control, control, end),
    closed back to the stem; `stem`: (x, top y, bottom y, width), a round cap on top; each grape is a `rim` disc with
    a GOLD body of `body` x its radius (a little up and to the left), and a GOLD_HI highlight when `highlight`."""
    grapes: tuple
    r: float
    center: tuple
    leaf: tuple
    vein: tuple | None
    stem: tuple
    rim: tuple
    body: float
    body_shift: tuple
    highlight: bool
    shadow: bool


# The app icons' mark: grapes.svg as it is ("M12 4c1.5-1.8 4-2.2 6-1.2-.6 2.1-2.6 3.4-4.8 3.2" is its leaf).
FULL = Mark(grapes=tuple(GRAPES), r=R, center=CENTER,
            leaf=(((12, 4), (13.5, 2.2), (16, 1.8), (18, 2.8)), ((18, 2.8), (17.4, 4.9), (15.4, 6.2), (13.2, 6.0))),
            vein=((12.6, 4.6), (14.2, 3.6), (15.8, 3.3), (17.2, 3.2)), stem=(12, 2.1, 6.6, 1.5),
            rim=GOLD_DEEP, body=0.86, body_shift=(0.06, 0.08), highlight=True, shadow=True)
# The 16 px mark: six bigger grapes in rows of 3, 2 and 1 (the cluster's outline), a bigger leaf, a thicker stem.
SMALL = Mark(grapes=((7.4, 9.6), (11.6, 9.6), (15.8, 9.6), (9.5, 13.8), (13.7, 13.8), (11.6, 18.0)), r=2.35,
             center=(11.6, 11.6),
             leaf=(((12.2, 5.6), (13.2, 2.6), (16.4, 1.6), (19.4, 2.4)), ((19.4, 2.4), (18.8, 5.4), (16.0, 7.0), (12.6, 6.6))),
             vein=None, stem=(11.6, 3.0, 8.0, 1.9),
             rim=GOLD_RIM, body=0.80, body_shift=(0.05, 0.07), highlight=False, shadow=True)


def gradient(size: int) -> Image.Image:
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    t = (x + y) / (2 * (size - 1))
    out = np.zeros((size, size, 3))
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        m = (t >= t0) & (t <= t1)
        k = ((t - t0) / (t1 - t0))[m][:, None]
        out[m] = np.array(c0) * (1 - k) + np.array(c1) * k
    # a warm glow behind the grapes (the hero's string lights)
    cx, cy, rad = size * GLOW_CX, size * GLOW_CY, size * GLOW_R
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / rad
    a = np.clip(1 - d, 0, 1) ** GLOW_FALL * GLOW_ALPHA
    out = out * (1 - a[..., None]) + np.array(GLOW) * a[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def bezier(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def draw_mark(img: Image.Image, box: float, shape: Mark = FULL) -> None:
    """The grape cluster, `box` px for the 24-unit viewBox, centred on the image."""
    size = img.size[0]
    k = box / 24
    ox, oy = size / 2 - shape.center[0] * k, size / 2 - shape.center[1] * k
    P = lambda x, y: (ox + x * k, oy + y * k)  # noqa: E731
    R = shape.r  # noqa: N806

    if shape.shadow:
        # soft shadow under the cluster, so the gold reads on the lighter blue corner too
        shadow = Image.new("L", img.size, 0)
        sd = ImageDraw.Draw(shadow)
        for gx, gy in shape.grapes:
            cx, cy = P(gx + 0.25, gy + 0.45)
            sd.ellipse([cx - R * k, cy - R * k, cx + R * k, cy + R * k], fill=150)
        shadow = shadow.filter(ImageFilter.GaussianBlur(k * 0.9))
        img.paste(Image.new("RGB", img.size, SHADOW), (0, 0), shadow)

    d = ImageDraw.Draw(img)
    # leaf: closed back to the stem
    leaf = bezier(*shape.leaf[0]) + bezier(*shape.leaf[1])
    d.polygon([P(*p) for p in leaf], fill=LEAF)
    if shape.vein:
        vein = bezier(*shape.vein, 12)
        d.line([P(*p) for p in vein], fill=VEIN, width=max(1, round(k * 0.35)), joint="curve")
    # stem
    sx, top, bottom, sw = shape.stem
    w = k * sw
    x0, y0 = P(sx, top)
    x1, y1 = P(sx, bottom)
    d.line([(x0, y0), (x1, y1)], fill=STEM, width=round(w))
    d.ellipse([x0 - w / 2, y0 - w / 2, x0 + w / 2, y0 + w / 2], fill=STEM)
    # grapes: deep rim, gold body, a light highlight up and to the left
    bx, by = shape.body_shift
    for gx, gy in shape.grapes:
        cx, cy = P(gx, gy)
        r = R * k
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=shape.rim)
        r2 = r * shape.body
        d.ellipse([cx - r2 - r * bx, cy - r2 - r * by, cx + r2 - r * bx, cy + r2 - r * by], fill=GOLD)
        if shape.highlight:
            hr = r * 0.30
            hx, hy = cx - r * 0.38, cy - r * 0.40
            d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=GOLD_HI)


def render(size: int, *, mark: float, rounded: bool, alpha: bool, shape: Mark = FULL) -> Image.Image:
    big = size * SS
    img = gradient(big)
    draw_mark(img, mark * big, shape)
    if rounded:
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=round(big * CORNER), fill=255)
        rgba = img.convert("RGBA")
        rgba.putalpha(mask)
        img = rgba
    elif alpha:
        img = img.convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def _n(v: float) -> str:
    """A number for the SVG: at most 3 decimals, no trailing zeros ("0.5" → ".5")."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s.replace("0.", ".", 1) if s.startswith("0.") else s.replace("-0.", "-.", 1) or "0"


def _hex(c: tuple) -> str:
    return "#%02x%02x%02x" % c


def svg(*, mark: float, shape: Mark) -> str:
    """favicon.svg: the rounded tile of render(…, rounded=True) — the hero gradient, the warm glow — and `shape` at
    `mark` of the side, from the same constants, in a 48-unit box. (The glow's fall-off is sampled into stops; the
    shadow under the grapes is the same discs, moved and blurred.)"""
    S = 48  # noqa: N806
    k = mark * S / 24
    tx, ty = S / 2 - shape.center[0] * k, S / 2 - shape.center[1] * k
    rx = _n(S * CORNER)
    stops = "".join(f'<stop offset="{_n(t)}" stop-color="{_hex(c)}"/>' for t, c in STOPS)
    glow = "".join(f'<stop offset="{_n(t)}" stop-color="{_hex(GLOW)}" stop-opacity="{_n((1 - t) ** GLOW_FALL * GLOW_ALPHA)}"/>'
                   for t in (0, 0.25, 0.5, 0.75, 1))
    (a0, a1, a2, a3), (_, b1, b2, b3) = shape.leaf
    pt = lambda p: f"{_n(p[0])} {_n(p[1])}"  # noqa: E731
    leaf = f'<path d="M{pt(a0)}C{pt(a1)} {pt(a2)} {pt(a3)}C{pt(b1)} {pt(b2)} {pt(b3)}Z" fill="{_hex(LEAF)}"/>'
    vein = ""
    if shape.vein:
        v0, v1, v2, v3 = shape.vein
        vein = f'<path d="M{pt(v0)}C{pt(v1)} {pt(v2)} {pt(v3)}" fill="none" stroke="{_hex(VEIN)}" stroke-width=".35" stroke-linecap="round"/>'
    sx, top, bottom, sw = shape.stem
    stem = (f'<path d="M{_n(sx)} {_n(bottom)}V{_n(top)}" stroke="{_hex(STEM)}" stroke-width="{_n(sw)}" '
            f'stroke-linecap="round"/>')
    blur, shadow = "", ""
    if shape.shadow:
        # render()'s blur is 0.9 units (GaussianBlur(k * 0.9)); the user-space units here are the mark's own
        blur = '<filter id="s" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation=".9"/></filter>\n'
        dots = "".join(f'<circle cx="{_n(x + 0.25)}" cy="{_n(y + 0.45)}" r="{_n(shape.r)}"/>' for x, y in shape.grapes)
        shadow = f'<g fill="{_hex(SHADOW)}" fill-opacity="{_n(150 / 255)}" filter="url(#s)">{dots}</g>\n'
    # the rim as a stroke round the gold body: together they fill the grape's radius
    rim = shape.r * (1 - shape.body)
    grapes = "".join(f'<circle cx="{_n(x)}" cy="{_n(y)}" r="{_n(shape.r - rim / 2)}"/>' for x, y in shape.grapes)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">\n<defs>\n'
        f'<linearGradient id="b" x1="0" y1="0" x2="1" y2="1">{stops}</linearGradient>\n'
        f'<radialGradient id="g" cx="{_n(GLOW_CX)}" cy="{_n(GLOW_CY)}" r="{_n(GLOW_R)}">{glow}</radialGradient>\n'
        f'{blur}</defs>\n'
        f'<rect width="{S}" height="{S}" rx="{rx}" fill="url(#b)"/><rect width="{S}" height="{S}" rx="{rx}" fill="url(#g)"/>\n'
        f'<g transform="translate({_n(tx)} {_n(ty)}) scale({_n(k)})">\n'
        f'{shadow}{leaf}{vein}\n{stem}\n'
        f'<g fill="{_hex(GOLD)}" stroke="{_hex(shape.rim)}" stroke-width="{_n(rim)}">{grapes}</g>\n'
        '</g>\n</svg>\n'
    )


# "any": the mark fills ~64 % of the square; maskable: ~56 %, well inside the safe circle
# (radius 40 %) — the leaf tip, the farthest point, sits ~28 % from the centre.
APP_JOBS = {
    "app-icon-192.png": dict(size=192, mark=0.64, rounded=True, alpha=True),
    "app-icon-512.png": dict(size=512, mark=0.64, rounded=True, alpha=True),
    "app-icon-maskable-192.png": dict(size=192, mark=0.56, rounded=False, alpha=False),
    "app-icon-maskable-512.png": dict(size=512, mark=0.56, rounded=False, alpha=False),
    "apple-touch-icon-180.png": dict(size=180, mark=0.60, rounded=False, alpha=False),
}
# Favicons: the smaller the picture, the more of the tile the mark fills (a tab shows 16 px).
FAVICON_JOBS = {
    "favicon-32.png": dict(size=32, mark=0.80, rounded=True, alpha=True),
    "favicon-48.png": dict(size=48, mark=0.72, rounded=True, alpha=True),
    "favicon-96.png": dict(size=96, mark=0.68, rounded=True, alpha=True),
}
# favicon.ico: (size, mark, shape) for each picture in it; the largest is the base image Pillow saves the others with
FAVICON_ICO = ((16, 0.90, SMALL), (32, 0.80, FULL), (48, 0.72, FULL))
# favicon.svg: drawn at 16 and 32 px in a tab, so the bold 16 px mark
FAVICON_SVG = dict(mark=0.90, shape=SMALL)


def write_pngs(jobs: dict) -> None:
    for name, kw in jobs.items():
        kw = dict(kw)
        size = kw.pop("size")
        im = render(size, **kw)
        im.save(OUT / name, optimize=True)
        print(f"{name}: {im.size[0]}x{im.size[1]} {im.mode} {(OUT / name).stat().st_size // 1024} KB")


def write_favicons() -> None:
    write_pngs(FAVICON_JOBS)
    frames = {n: render(n, mark=m, rounded=True, alpha=True, shape=s) for n, m, s in FAVICON_ICO}
    sizes = sorted(frames)
    ico = OUT / "favicon.ico"
    # every size is given as its own picture (append_images): Pillow then never shrinks the base image for it
    frames[sizes[-1]].save(ico, sizes=[(n, n) for n in sizes], append_images=[frames[n] for n in sizes[:-1]])
    print(f"favicon.ico: {' + '.join(f'{n}x{n}' for n in sizes)} {ico.stat().st_size // 1024} KB")
    out = OUT / "favicon.svg"
    out.write_text(svg(**FAVICON_SVG), encoding="utf-8", newline="\n")
    print(f"favicon.svg: {out.stat().st_size} bytes")


def main(argv: list[str] | None = None) -> None:
    which = set((sys.argv[1:] if argv is None else argv) or ["app", "favicons"])
    if which - {"app", "favicons"}:
        raise SystemExit("usage: python -m scripts.dev.make_app_icons [app] [favicons]   (nothing: both)")
    OUT.mkdir(parents=True, exist_ok=True)
    if "app" in which:
        write_pngs(APP_JOBS)
    if "favicons" in which:
        write_favicons()


if __name__ == "__main__":
    main()
