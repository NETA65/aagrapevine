"""The booth display, build side: the `booth` global (src/_data/booth.js — the CSV checked, the Drive booth folder's
files with the copies the deploy saved, the starting settings) and /about/booth.json (src/pages/booth-json.11ty.js —
eleventy/filters/booth.js boothShow adds the day's live items), the one file the player on the About page fetches.

  * Show — boothShow on fixtures, at a fixed clock (2099, far from today): tests/fixtures/booth_csv/show.csv, the
    Drive folder's booth.json and the media manifest beside it, and made-up site data (db, site):
      - the file's top level (SPEC §2.4) and every key of every ITEM, text block, row and media block;
      - the CSV's items (a Short the channel's list knows is shown as one);
      - the Drive items with the manifest (local copies under <base>about/booth/media/, a picture's size) and without
        it (pictures from Google's copy, online; videos and sound files left out — "not downloaded in this build");
        collections with their counts; the sync's problems;
      - the live items: events (the next four, a monthly series once, each row until it is over) and the countdown to
        the next assembly; the daily quotes (as the Home page shows them: the last two days); the official channel's
        videos (no weekly open meeting or live recording, nothing over 8 minutes but the committee's own choice, the
        newest 30, none the CSV already plays, none whose title has sales words — left out and named); the podcast
        (AA Grapevine's own show, the newest six, from captivate.fm's addresses only — another site named —, never
        the show's logo as a picture); story themes (the next three of each magazine); prices (information, "as of",
        the announced change beside them — never an urgent word); the Books of the Month (never a cover; a book in
        the other language says so); the meetings (one in the other language says so, never twice); the bulletin's
        newest posts (the teaser: the first paragraph, never a heading run into it; one that says "PDF" left out and
        named); no refused word in any live or Drive item;
      - a Drive caption or note that says a refused word leaves its file out (DriveWords); a live QR code is a page,
        never a document file (LiveLinks);
      - the QR map, the channels, "pick the event", the problems, a stable version, the defaults;
  * Build — a real Eleventy build of /about/booth.json alone (ONLY=booth-json) from the same fixtures, as GitHub
    Pages builds it (PATH_PREFIX=/aagrapevine/, I18N_STRICT=1): the file, its base path, not in the sitemap; and a
    build without the CSV (a problem line, never a failed build).
Offline. Skipped without Node.js or without node_modules (npm ci), as in tests/nodejs.py.

    python -m unittest tests.test_booth_build -v
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = "tests/fixtures/booth_csv/"
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
REAL_BASE = (os.environ.get("SITE_URL") or SITE["site"]["url"]).rstrip("/") + "/"
URL = "https://neta65.github.io/aagrapevine"
BASE_URL = URL + "/"
NOW = "2099-10-15T17:00:00Z"
HEX12 = re.compile(r"^[0-9a-f]{12}$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

TOP = ["app", "schema", "version", "built", "as_of", "site", "defaults", "collections", "channels", "events_pick",
       "items", "qr", "problems"]
ITEM = ["id", "source", "type", "channel", "pub", "langs", "en", "es", "correct", "seconds", "reveal", "weight", "from",
        "until", "tags", "collection", "first", "order", "media", "online", "qr", "qr_es", "url", "until_ts"]
BLOCK = ["title", "text", "choices", "answer", "explain", "credit", "rows"]
ROW = ["title", "when", "place", "note", "ends_ts", "pub", "thumb", "starts_ts"]
MEDIA = ["kind", "src", "id", "short", "local", "poster", "start", "end", "muted", "fit", "w", "h", "bytes"]
CHANNELS = ["quiz", "puzzles", "facts", "quotes", "polls", "prompts", "messages", "qr", "web-video", "web-audio",
            "web-image", "photos", "posters", "videos", "sounds", "notes", "live-events", "live-quote", "live-video",
            "live-podcast", "live-themes", "live-prices", "live-book", "live-meetings", "live-bulletin"]


def node_ready(case: unittest.TestCase) -> None:
    if not node_path():
        case.skipTest("Node.js is not installed")
    if not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
        case.skipTest("the site's npm packages are not installed (npm ci)")


# ----------------------------------------------------------------------------------------------------------------
# Made-up site data (the shapes of data/site/*.json, docs/DATA_SCHEMA.md), around 2099-10-15
# ----------------------------------------------------------------------------------------------------------------
def event(eid, title, title_es, start, end, category="manual", **x):
    ext = {"start": start, "end": end, "all_day": len(start) == 10, "location": x.pop("location", None),
           "online_url": x.pop("online_url", None), "flyer_url": x.pop("flyer_url", None), "flyer_thumb": x.pop("flyer_thumb", None)}
    ext.update(x)
    i18n = {"title": {"en": title, "es": title_es}}
    if ext.get("location_tba"):
        i18n["location"] = {"en": ext["location"], "es": "Lugar por anunciarse"}
    slug = eid.split(":")[-1]
    if category == "manual":
        ext["slug"] = slug
    return {"id": eid, "source": "committee", "kind": "event", "url": f"/events/#{slug}" if category == "manual" else "/events/",
            "title": title, "lang": "en", "date": start, "first_seen": None, "image": None, "tags": [], "category": category,
            "status": "ok", "extra": ext, "i18n": i18n, "machine": []}


EVENTS = [
    event("ev:manual:2099-10-01-past", "A past workshop", "Un taller pasado", "2099-10-01T19:00:00Z", "2099-10-01T21:00:00Z",
          location="Grupo Uno, 1 Main St, Dallas, TX"),
    event("ev:manual:2099-10-20-writing", "Grapevine Writing Workshop — Plano", "Taller de Escritura de Grapevine — Plano",
          "2099-10-20T19:00:00Z", "2099-10-20T22:00:00Z", location="Group Two, 2 Elm St, Plano, TX",
          online_url="https://us02web.zoom.us/j/1234567890", platform="Zoom",
          flyer_url="https://drive.google.com/file/d/flyerPlano01/view",
          flyer_thumb="https://lh3.googleusercontent.com/d/flyerPlano01=w320"),
    event("ev:recurring:citywide-dallas:2099-10-24", "GV/LV booth at CityWide Dallas", "Mesa de GV/LV en CityWide Dallas",
          "2099-10-24T22:00:00Z", "2099-10-25T01:00:00Z", "recurring", location="Lover's Lane, 9200 Inwood Road, Dallas, TX",
          recurring=True, series="citywide-dallas", host="neta"),
    event("ev:recurring:lv-monthly-workshop:2099-10-29", "La Viña Monthly Virtual Workshop (in Spanish)",
          "Taller Mensual y Virtual de La Viña", "2099-10-29T19:00:00Z", "2099-10-29T20:00:00Z", "recurring",
          online_url="https://us06web.zoom.us/j/81595931777", platform="Zoom", recurring=True, series="lv-monthly-workshop",
          host="lv", meeting_id="815 9593 1777"),
    event("ev:recurring:citywide-dallas:2099-11-14", "GV/LV booth at CityWide Dallas", "Mesa de GV/LV en CityWide Dallas",
          "2099-11-14T23:00:00Z", "2099-11-15T02:00:00Z", "recurring", location="Lover's Lane, 9200 Inwood Road, Dallas, TX",
          recurring=True, series="citywide-dallas", host="neta"),
    event("ev:manual:2099-11-20-neta65-fall-assembly", "NETA 65 Fall Assembly 2099", "Asamblea de Otoño 2099 de NETA 65",
          "2099-11-20", "2099-11-22", location="Hotel Three, 3 Hotel Rd, Tyler, TX"),
    event("ev:manual:2099-11-25-online-workshop", "Grapevine Information Workshop (online)", "Taller informativo de Grapevine (en línea)",
          "2099-11-25T01:00:00Z", "2099-11-25T02:30:00Z", online_url="https://us02web.zoom.us/j/9990001111", platform="Zoom"),
    event("ev:manual:2100-03-19-neta65-spring-assembly", "NETA 65 Spring Assembly 2100", "Asamblea de Primavera 2100 de NETA 65",
          "2100-03-19", "2100-03-21", location="Venue to be announced", location_tba=True, tentative=True),
]


def video(vid, title, date, lang="en", cat="gv", sec=300, short=False, live=False, tags=(), playlists=()):
    return {"id": f"yt:{vid}", "source": "youtube", "kind": "video", "url": f"https://www.youtube.com/watch?v={vid}",
            "title": title, "lang": lang, "date": f"{date}T12:00:00Z", "category": cat, "status": "ok", "tags": list(tags),
            "extra": {"video_id": vid, "duration_sec": sec, "is_short": short, "is_live_recording": live,
                      "playlists": list(playlists)},
            "i18n": {"title": {lang: title}}}


VIDEOS = [
    video("aboutVidEN1", "ABOUT GRAPEVINE IN CAPITALS", "2099-01-01", sec=316),
    video("aboutVidLV2", "Sobre La Viña", "2099-01-02", lang="es", cat="lv", sec=489),
    video("weeklyOpen1", "Grapevine Weekly Open AA Meeting, October 14, 2099", "2099-10-14", sec=3000, live=True,
          tags=["weekly-open", "live"], playlists=["Grapevine Weekly Open AA Meeting"]),
    video("liveRec0001", "A live recording", "2099-10-13", sec=300, live=True, tags=["live"]),
    video("longVideo01", "A long video", "2099-10-12", sec=540),
    video("noDuration1", "A video of unknown length", "2099-10-11", sec=None),
    video("shortVid001", "A Short", "2099-10-10", sec=50, short=True, tags=["short"]),
    video("dupeVid0001", "El video de la fila", "2099-10-09", lang="es", cat="lv", sec=200),
    video("otherShort1", "Another Short", "2099-10-08", sec=40, short=True, tags=["short"]),
    # the official channel's own app Shorts (the real ones: 2cT_CxCheYw, -dLMxbAnV_o) — sales words, left out and named
    video("salesShort1", "Download Now! Then Subscribe!", "2099-10-14", sec=19, short=True, tags=["short"],
          playlists=["Grapevine and La Viña Apps"]),
    video("salesShort2", "¡Descárgala ahora! ¡Luego suscríbete!", "2099-10-14", lang="es", cat="lv", sec=19, short=True,
          tags=["short"], playlists=["Grapevine and La Viña Apps"]),
] + [video(f"regular{i:04d}", f"Regular video {i}", f"2099-08-{1 + i:02d}" if i < 31 else f"2099-09-{i - 30:02d}") for i in range(35)]


def episode(n, show="gv", host="episodes.captivate.fm", date="2099-09-01"):
    return {"id": f"pod:{show}:ep{n:02d}", "source": "podcast", "kind": "episode",
            "url": f"https://player.captivate.fm/episode/ep-{show}-{n:02d}", "title": f"Episode {n} [Season 12, Episode {n}]",
            "lang": "en", "date": f"{date}T04:15:00Z", "category": show, "status": "ok",
            "extra": {"audio_url": f"https://{host}/episode/ep-{show}-{n:02d}.mp3", "show": show,
                      "show_name": "AA Grapevine's Podcast" if show == "gv" else "Grapevine Weekly Open AA Meeting",
                      "thumb": f"/assets/cache/pod/{show}show.webp", "duration_sec": 1800}}


# (episode 6's sound file is on the host's file server, as the feed gives every episode of 2021 to mid-2025; episode 9,
# the newest, on another site: left out and named)
EPISODES = [episode(n, date=f"2099-09-{n:02d}", host="podcasts.captivate.fm" if n == 6 else "episodes.captivate.fm")
            for n in range(1, 9)] + [
    episode(1, "wo", date="2099-10-01"), episode(2, "wo", date="2099-10-08"),
    episode(9, host="cdn.example.com", date="2099-10-10"),
]


def theme(tid, pub, key, deadline, title, en, es, evergreen=False):
    lang = "es" if pub == "lv" else "en"
    return {"id": tid, "source": "lavina" if pub == "lv" else "grapevine", "kind": "topic", "title": title, "lang": lang,
            "status": "ok", "category": pub,
            "extra": {"publication": pub, "issue_key": key, "deadline": deadline, "theme": title, "evergreen": evergreen},
            "i18n": {"title": {"en": en, "es": es}}, "machine": ["es" if pub == "gv" else "en"]}


EDITORIAL = [
    theme("ed:gv:2100-04:theme-a", "gv", "2100-04", "2099-11-01", "Theme A", "Theme A", "Tema A"),
    theme("ed:gv:2100-05:theme-b", "gv", "2100-05", "2099-12-01", "Theme B", "Theme B", "Tema B"),
    theme("ed:gv:2100-06:theme-c", "gv", "2100-06", "2100-01-01", "Theme C", "Theme C", "Tema C"),
    theme("ed:gv:2100-07:theme-d", "gv", "2100-07", "2100-02-01", "Theme D", "Theme D", "Tema D"),
    theme("ed:gv:2100-03:closed", "gv", "2100-03", "2099-10-01", "Closed theme", "Closed theme", "Tema cerrado"),
    theme("ed:lv:2100-05:recaidas", "lv", "2100-05", "2099-10-20", "Recaídas", "Relapses", "Recaídas"),
    theme("ed:lv:any:mi-primer-paso", "lv", None, None, "Mi Primer Paso", "My First Step", "Mi Primer Paso", evergreen=True),
]

QUOTES = [
    {"id": "quote:gv:2099-10-14", "pub": "gv", "lang": "en", "date": "2099-10-14", "date_label": "October 14",
     "heading": "Grapevine Daily Quote October 14", "text": "A sample quote for the tests.",
     "attribution": "A member, Somewhere, May 1999", "source": "A sample book", "source_lang": "en",
     "url": "https://www.aagrapevine.org/#quote-of-the-day", "signup_url": "https://visitor.r20.constantcontact.com/x"},
    {"id": "quote:lv:2099-10-12", "pub": "lv", "lang": "es", "date": "2099-10-12", "date_label": "12 de octubre",
     "heading": "Cita Diaria", "text": "Una cita de prueba.", "attribution": "Un miembro", "source": "",
     "url": "https://www.aalavina.org/#quote-of-the-day", "signup_url": ""},
]
QUOTES_LATER = [dict(QUOTES[1], date="2099-10-13")]

LONG_BLURB = "Stories of members who stayed sober through hard times, " * 6
SHOP = {
    "updated": "2099-10-14T12:00:00Z",
    "botm": [
        {"id": "botm:gv", "pub": "gv", "lang": "en", "title": "A Grapevine Book", "url": "https://www.aagrapevine.org/store/a-grapevine-book",
         "page_url": "https://www.aagrapevine.org/BOTM", "image": "/assets/cache/shop/cover-gv.webp", "price": 14.99,
         "sale_price": 11.99, "discount_pct": 20, "currency": "USD", "sku": "GV99", "starts": "2099-10-01", "ends": "2099-10-31",
         "month_label": "October", "blurb": LONG_BLURB, "read": "2099-10-02", "price_stale": False,
         "i18n": {"title": {"en": "A Grapevine Book", "es": "Un libro de Grapevine"},
                  "blurb": {"en": LONG_BLURB, "es": "Historias de miembros que se mantuvieron sobrios en tiempos difíciles."},
                  "month_label": {"en": "October", "es": "Octubre"}}, "machine": ["es"]},
        {"id": "botm:lv", "pub": "lv", "lang": "es", "title": "Un libro de La Viña", "url": "https://www.aalavina.org/tienda/un-libro",
         "page_url": "https://www.aalavina.org/libro-del-mes", "image": "/assets/cache/shop/cover-lv.webp", "price": 14.99,
         "sale_price": 11.99, "discount_pct": 20, "currency": "USD", "sku": "LV99", "starts": "2099-10-01", "ends": "2099-10-31",
         "month_label": "Octubre", "blurb": "Historias breves.", "read": "2099-10-02", "price_stale": False,
         "i18n": {"title": {"en": "A La Viña Book", "es": "Un libro de La Viña"}, "blurb": {"en": "Short stories.", "es": "Historias breves."},
                  "month_label": {"en": "October", "es": "Octubre"}}, "machine": ["en"]},
    ],
    "subscriptions": [
        {"pub": "gv", "region": "us", "url": "https://www.aagrapevine.org/store/us-subscriptions", "plans": [
            {"type": "print", "term_months": 12, "price": 36.0, "currency": "USD", "url": "https://www.aagrapevine.org/store/print",
             "change": {"key": "2100-01", "new": 39.0, "stale": True}},
            {"type": "digital", "term_months": 12, "price": 29.99, "currency": "USD", "url": "https://www.aagrapevine.org/store/digital",
             "change": {"key": "2100-01", "new": 34.0, "stale": True}},
            {"type": "print", "term_months": 24, "price": 68.0, "currency": "USD", "url": "https://www.aagrapevine.org/store/print-2"}]},
        {"pub": "lv", "region": "us", "url": "https://www.aalavina.org/US-suscripciones", "plans": [
            {"type": "print", "term_months": 12, "price": 18.0, "currency": "USD", "url": "https://www.aalavina.org/tienda/impresa",
             "change": {"key": "2100-01", "new": 19.5, "stale": True}},
            {"type": "digital", "term_months": 12, "price": 14.99, "currency": "USD", "url": "https://www.aalavina.org/tienda/digital",
             "change": {"key": "2100-01", "new": 17.0, "stale": True}}]},
    ],
    "price_changes": [{"key": "2100-01", "announced": "2099-10-01", "effective": "2100-01-01", "notice_until": "2100-01-31",
                       "at": {"announced": "2099-10-01T05:00:00Z", "effective": "2100-01-01T06:00:00Z", "notice_end": "2100-02-01T06:00:00Z"},
                       "books_more": 2.0, "yearly": []}],
}


def post(pid, title, title_es, summary, summary_es, date, **x):
    return {"id": f"ann:{pid}", "source": "committee", "kind": "announcement", "url": f"/bulletin/#{pid}", "title": title,
            "summary": summary, "lang": "en", "date": date, "status": "ok", "category": "manual",
            "extra": {"slug": pid, "pinned": False, "expires": None, **x},
            "i18n": {"title": {"en": title, "es": title_es}, "summary": {"en": summary, "es": summary_es}}}


# A Drive post's summary is the sync's: its body run into one line (scripts/sync/announcements.py markdown_to_text) —
# headings and lists included; the slide's teaser is the body's first paragraph instead. p1 (with a translated body)
# would else say an unverified claim the booth refuses; p3 starts with a heading and has no Spanish body (its Spanish
# summary is used, never the English body).
P1_BODY = ("A pinned **post** about the [workshops](/events/).\n\n# Why it matters\n\n"
           "- **A meeting in print.** Grapevine and La Viña reach millions of people.")
P1_BODY_ES = ("Un aviso fijado sobre los [talleres](/events/).\n\n# Por qué importa\n\n"
              "- **Una reunión impresa.** Grapevine y La Viña llegan a millones de personas.")
P1 = post("p1", "Pinned post", "Aviso fijado",
          "A pinned post about the workshops. Why it matters A meeting in print. Grapevine and La Viña reach millions of people.",
          "Un aviso fijado sobre los talleres. Por qué importa Una reunión impresa. Grapevine y La Viña llegan a millones de personas.",
          "2099-10-01", pinned=True, expires="2099-12-31", body_md=P1_BODY)
P1["i18n"]["body_md"] = {"en": P1_BODY, "es": P1_BODY_ES}
ANNOUNCEMENTS = [
    P1,
    post("p2", "Newest post", "Aviso más nuevo", "Download the PDF flyer.", "Descarga el volante.", "2099-10-10"),
    post("p3", "Older post", "Aviso anterior", "Older news An older post, with a link. More text.", "Un aviso anterior.",
         "2099-10-05", body_md="# Older news\n\nAn *older* post, with [a link](/events/).\n\nMore text."),
    post("p4", "Expired post", "Aviso vencido", "Over.", "Terminado.", "2099-09-20", expires="2099-10-01"),
]

WEEKLY_OPEN = [
    {"id": "weekly_open", "source": "grapevine", "kind": "meeting", "url": "https://www.aagrapevine.org/grapevine-weekly-open",
     "title": "Grapevine Weekly Open AA Meeting", "lang": "en", "status": "ok",
     "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "day": "Wednesdays", "time": "Noon Eastern", "weekday": "wednesday",
               "start_local": "12:00", "timezone": "America/New_York", "time_central": "11 AM Central", "next_start": "2099-10-21T16:00:00Z"},
     "i18n": {"title": {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"},
              "when": {"en": "Wednesdays at 11:00 AM Central", "es": "Los miércoles a las 11:00 a. m. (hora del Centro)"}}},
    {"id": "weekly_open_lv", "source": "lavina", "kind": "meeting", "url": "", "title": "Reunión Abierta de La Viña", "lang": "es",
     "status": "ok",
     "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "day": "Jueves", "time": "12 p. m. (hora del Este)", "weekday": "thursday",
               "start_local": "12:00", "timezone": "America/New_York", "time_central": "11 AM Central", "next_start": "2099-11-05T17:00:00Z",
               "starts": "2099-11-05"},
     "i18n": {"title": {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"},
              "when": {"en": "Thursdays at 11:00 AM Central", "es": "Los jueves a las 11:00 a. m. (hora del Centro)"}}},
]

DB_X = {"events": {"items": EVENTS}, "videos": {"items": VIDEOS}, "episodes": {"items": EPISODES},
        "editorial": {"items": EDITORIAL}, "quote": {"items": QUOTES}, "shop": SHOP,
        "announcements": {"items": ANNOUNCEMENTS}, "weekly_open": {"items": WEEKLY_OPEN}}
SITE_X = {"url": URL, "committee": "NETA 65 Grapevine & La Viña Committee", "committee_es": "Comité de Grapevine y La Viña de NETA 65",
          "built": NOW, "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00",
                                    "platform": "Zoom", "meeting_id": "949 476 7497"},
          "about_videos": [{"id": "aboutVidEN1", "pub": "gv", "title": "About Grapevine"}, {"id": "aboutVidLV2", "pub": "lv"}],
          "recurring_events": []}
CONFIG_X = {"max_file_mb": 50, "defaults": {"event_name": "NETA 65 Fall Assembly", "event_name_es": "Asamblea de Otoño de NETA 65",
                                            "language": "ES", "sound": "yes"}}

SHOW_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const F = "tests/fixtures/booth_csv/";
const base = "/aagrapevine/";
const load = (o = {}) => B.loadBooth({ csv: F + "show.csv", drive: F + "drive-booth.json", manifest: F + "booth-manifest.json",
  config: input.config, site: input.site, base, ...o });
const ctx = (o = {}) => ({ db: input.db, site: input.site, now: new Date(input.now), base, ...o });
const booth = load();
const show = B.boothShow(booth, ctx());
const qrFull = show.qr;
const texts = (it) => ["en", "es"].flatMap((l) => (it[l] ? [it[l].title, it[l].text, it[l].explain, it[l].credit, ...it[l].choices,
  ...it[l].rows.flatMap((r) => [r.title, r.when, r.place, r.note])] : [])).filter(Boolean);
const noManifest = B.boothShow(load({ manifest: F + "no-such-manifest.json" }), ctx());
// no data at all: no CSV rows, no Drive folder, no site data and no settings beside the site's address
const empty = B.boothShow(load({ csvText: "id,type,text_en\n", driveData: null, manifestData: null }),
  { db: {}, site: { url: input.site.url }, now: new Date(input.now), base });
out({
  booth: { csvRows: booth.csv.rows, csvFound: booth.csv.found, driveFound: booth.drive.found, manifest: booth.manifest,
    config: booth.config, base: booth.base, items: booth.items.length },
  show: { ...show, qr: Object.fromEntries(Object.entries(qrFull).map(([k, v]) => [k, v.slice(0, 60)])) },
  qrSvgOk: Object.values(qrFull).every((v) => /^<svg [^>]*viewBox="0 0 \d+ \d+"[^>]*aria-hidden="true"/.test(v) && v.endsWith("</svg>")),
  noManifest: { items: noManifest.items.filter((i) => i.source === "drive"), problems: noManifest.problems, collections: noManifest.collections },
  versions: {
    first: show.version,
    again: B.boothShow(load(), ctx()).version,
    rebuilt: B.boothShow(load(), ctx({ site: { ...input.site, built: "2099-10-15T23:00:00Z" } })).version,
    otherCsv: B.boothShow(load({ csvText: "id,type,text_en\nprompt-x,prompt,Another question?\n" }), ctx()).version,
    otherDefaults: B.boothShow(load({ config: {} }), ctx()).version,
  },
  quotesLater: B.liveItems(ctx({ db: { quote: { items: input.quotesLater } } })).items.filter((i) => i.channel === "live-quote"),
  refused: show.items.filter((i) => i.source === "live" || i.source === "drive").flatMap(texts).flatMap((s) => B.refusedIn(s)),
  defaults: [B.boothDefaults(input.config), B.boothDefaults({ defaults: { event_name: ["a list"], event_name_es: "x".repeat(90),
    language: "french", sound: "loud" }, max_total_mb: "lots" }), B.boothDefaults(null)],
  empty: { items: empty.items, channels: empty.channels, qr: Object.keys(empty.qr), events_pick: empty.events_pick, problems: empty.problems },
  missingCsv: load({ csv: F + "no-such.csv" }).problems,
  badDrive: load({ driveData: undefined, drive: F + "show.csv" }).problems.filter((p) => p.where.endsWith("show.csv")),
});
"""


class Show(unittest.TestCase):
    """boothShow on the fixtures at a fixed clock."""

    r: dict | None = None

    def setUp(self):
        node_ready(self)
        if Show.r is None:
            Show.r = run_js(self, SHOW_JS, data={"db": DB_X, "site": SITE_X, "config": CONFIG_X, "now": NOW, "quotesLater": QUOTES_LATER})
        self.show = Show.r["show"]
        self.items = {it["id"]: it for it in self.show["items"]}

    def live(self, channel: str) -> list[dict]:
        return [it for it in self.show["items"] if it["channel"] == channel]

    # -- the file -----------------------------------------------------------------------------------------------
    def test_the_top_level(self):
        s = self.show
        self.assertEqual(list(s), TOP)
        self.assertEqual((s["app"], s["schema"]), ("gv-booth", 1))
        self.assertRegex(s["version"], HEX12)
        self.assertEqual((s["built"], s["as_of"]), ("2099-10-15T17:00:00.000Z", "2099-10-15"))
        self.assertEqual(s["site"], {"url": BASE_URL, "url_es": BASE_URL + "es/", "base": "/aagrapevine/",
                                     "host": "neta65.github.io/aagrapevine", "committee_en": SITE_X["committee"],
                                     "committee_es": SITE_X["committee_es"]})
        self.assertEqual(s["defaults"], {"event": {"en": "NETA 65 Fall Assembly", "es": "Asamblea de Otoño de NETA 65"},
                                         "lang": "es", "sound": True})
        b = self.r["booth"]
        self.assertEqual((b["csvRows"], b["csvFound"], b["driveFound"], b["base"]), (5, True, True, "/aagrapevine/"))
        self.assertEqual((b["manifest"]["found"], b["manifest"]["files"]), (True, 3))
        self.assertEqual((b["config"]["max_file_mb"], b["config"]["max_total_mb"]), (50, 400))

    def test_every_key_of_every_item(self):
        ids = [it["id"] for it in self.show["items"]]
        self.assertEqual(len(ids), len(set(ids)), "ids are unique")
        for it in self.show["items"]:
            with self.subTest(id=it["id"]):
                self.assertEqual(list(it), ITEM)
                self.assertIn(it["source"], ("csv", "drive", "live"))
                self.assertIn(it["channel"], CHANNELS)
                self.assertIn(it["pub"], ("gv", "lv", "both"))
                self.assertTrue(set(it["langs"]) <= {"en", "es"})
                self.assertEqual({"csv": it["id"].count(":") == 0, "drive": it["id"].startswith("drive:"),
                                  "live": it["id"].startswith("live:")}[it["source"]], True)
                for lang in ("en", "es"):
                    if it[lang] is None:
                        continue
                    self.assertEqual(list(it[lang]), BLOCK)
                    for row in it[lang]["rows"]:
                        self.assertEqual(list(row), ROW)
                        self.assertIn(row["pub"], ("gv", "lv", "both"))
                for lang in it["langs"]:
                    self.assertIsNotNone(it[lang], "a language the item is shown in has its words")
                if it["media"] is not None:
                    self.assertEqual(list(it["media"]), MEDIA)
                    self.assertIn(it["media"]["kind"], ("youtube", "video", "audio", "image"))
                    self.assertEqual(it["online"], not it["media"]["local"])
                else:
                    self.assertFalse(it["online"])
                if it["qr"]:
                    self.assertRegex(it["qr"], r"^https://(www\.)?(aagrapevine\.org|aalavina\.org|youtube\.com|neta65\.github\.io)/")
                # a Spanish code only beside an English one, and only when it is another address: a page under /es/
                if it["qr_es"] is not None:
                    self.assertTrue(it["qr"])
                    self.assertTrue(it["qr_es"].startswith(BASE_URL + "es/"), it["qr_es"])
                    if it["source"] == "live":
                        self.assertNotEqual(it["qr_es"], it["qr"])

    def test_the_csv_items(self):
        quiz = self.items["quiz-one"]
        self.assertEqual((quiz["type"], quiz["channel"], quiz["correct"], quiz["qr"]), ("quiz", "quiz", 1, BASE_URL + "contribute/"))
        self.assertEqual(quiz["qr_es"], BASE_URL + "es/contribute/", "{site}contribute/: the Spanish page on Spanish slides")
        self.assertEqual(quiz["es"]["choices"], ["1935", "1944", "1996"])
        # the channel's list knows shortVid001 as a Short: the CSV row plays it as one
        self.assertEqual((self.items["video-short"]["media"]["short"], self.items["video-dupe"]["media"]["short"]), (True, False))
        self.assertEqual(self.items["message-event"]["es"]["text"], "¡Bienvenidos a {event}!")
        self.assertEqual([it["id"] for it in self.show["items"] if it["source"] == "csv"],
                         ["quiz-one", "video-short", "video-dupe", "audio-dupe", "message-event"])

    # -- the Drive booth folder -----------------------------------------------------------------------------------
    def test_drive_items_with_the_saved_copies(self):
        d = {it["id"]: it for it in self.show["items"] if it["source"] == "drive"}
        self.assertEqual(list(d), ["drive:fileWelcome01", "drive:fileCamera001", "drive:fileTestimonio1",
                                   "drive:fileTeaser0001", "drive:fileMessage001"])
        welcome = d["drive:fileWelcome01"]
        self.assertEqual((welcome["type"], welcome["channel"], welcome["pub"], welcome["langs"], welcome["first"], welcome["seconds"]),
                         ("poster", "posters", "gv", ["en"], True, 15))
        self.assertEqual((welcome["en"]["title"], welcome["es"]), ("Welcome", None))
        self.assertEqual(welcome["media"], {"kind": "image", "src": "/aagrapevine/about/booth/media/filewe-welcome.png", "id": None,
                                            "short": False, "local": True, "poster": None, "start": 0, "end": None, "muted": False,
                                            "fit": "contain", "w": 1920, "h": 1080, "bytes": 123456})
        self.assertFalse(welcome["online"])
        camera = d["drive:fileCamera001"]
        self.assertEqual((camera["type"], camera["langs"], camera["en"], camera["es"], camera["order"], camera["weight"]),
                         ("photo", [], None, None, 2, 2))
        self.assertEqual((camera["media"]["src"], camera["media"]["local"], camera["online"], camera["media"]["fit"]),
                         ("https://lh3.googleusercontent.com/d/fileCamera001=s1920", False, True, "cover"))
        video = d["drive:fileTestimonio1"]
        self.assertEqual((video["channel"], video["collection"], video["langs"], video["es"]["title"], video["en"]),
                         ("videos", "spring-assembly-2099", ["es"], "Testimonio", None))
        self.assertEqual((video["media"]["src"], video["media"]["start"], video["media"]["end"], video["media"]["bytes"]),
                         ("/aagrapevine/about/booth/media/filete-testimonio.mp4", 5, 105, 9000000))
        teaser = d["drive:fileTeaser0001"]
        self.assertEqual((teaser["channel"], teaser["media"]["kind"], teaser["media"]["start"], teaser["media"]["end"]), ("sounds", "audio", 30, None))
        note = d["drive:fileMessage001"]
        self.assertEqual((note["type"], note["channel"], note["media"], note["en"]["text"]),
                         ("message", "notes", None, "Hello **friends**\n- the stories\n- the podcast"))
        self.assertEqual(self.show["collections"], [{"id": "main", "label": "Booth folder", "count": 4},
                                                    {"id": "spring-assembly-2099", "label": "Spring Assembly 2099", "count": 1}])
        lines = [f"{p['where']}: {p['en']}" for p in self.show["problems"] if p["where"].startswith("Drive")]
        self.assertEqual(lines, [
            "Drive: booth/Display.jpg: no picture to show: the sync gave no address for it",
            "Drive: booth/Big video.mp4: not downloaded in this build, so it is left out (videos and sound files play only from the copy saved with the site): too big",
            "Drive: booth/Budget.xlsx: not a type the booth can show",
            "Drive: booth/notes.zip: not a type the booth can show",
        ])
        es = [p["es"] for p in self.show["problems"] if p["where"].startswith("Drive")]
        self.assertTrue(es[1].endswith(": demasiado grande"))
        self.assertEqual(es[3], "no es un tipo de archivo que la pantalla pueda mostrar")

    def test_drive_items_without_the_saved_copies(self):
        nm = self.r["noManifest"]
        d = {it["id"]: it for it in nm["items"]}
        self.assertEqual(list(d), ["drive:fileWelcome01", "drive:fileCamera001", "drive:fileMessage001"])
        self.assertEqual((d["drive:fileWelcome01"]["media"]["src"], d["drive:fileWelcome01"]["online"], d["drive:fileWelcome01"]["media"]["w"]),
                         ("https://lh3.googleusercontent.com/d/fileWelcome01=s1920", True, None))
        left = [p["where"] for p in nm["problems"] if "not downloaded in this build" in p["en"]]
        self.assertEqual(left, ["Drive: booth/Spring Assembly 2099/LV ES Testimonio (0:05-1:45).mp4",
                                "Drive: booth/GV EN Podcast teaser (0:30-).mp3", "Drive: booth/Big video.mp4"])
        self.assertEqual(nm["collections"], [{"id": "main", "label": "Booth folder", "count": 3}])

    # -- the live items -------------------------------------------------------------------------------------------
    def test_events_and_the_countdown(self):
        ev = self.items["live:events:next"]
        self.assertEqual((ev["type"], ev["channel"], ev["langs"], ev["qr"]), ("events", "live-events", ["en", "es"], BASE_URL + "events/"))
        self.assertEqual(ev["qr_es"], BASE_URL + "es/events/")
        rows = ev["en"]["rows"]
        self.assertEqual([r["title"] for r in rows], ["Grapevine Writing Workshop — Plano", "GV/LV booth at CityWide Dallas",
                                                      "La Viña Monthly Virtual Workshop (in Spanish)", "NETA 65 Fall Assembly 2099"])
        self.assertEqual([r["title"] for r in ev["es"]["rows"]], ["Taller de Escritura de Grapevine — Plano", "Mesa de GV/LV en CityWide Dallas",
                                                                  "Taller Mensual y Virtual de La Viña", "Asamblea de Otoño 2099 de NETA 65"])
        plano, citywide, workshop, assembly = rows
        self.assertEqual((plano["place"], plano["note"], plano["thumb"]),
                         ("Group Two, 2 Elm St, Plano, TX", "Online on Zoom", "https://lh3.googleusercontent.com/d/flyerPlano01=w320"))
        self.assertEqual(ev["es"]["rows"][0]["note"], "En línea por Zoom")
        self.assertEqual((workshop["place"], workshop["pub"], citywide["pub"]), (None, "lv", "both"))
        self.assertIn("Nov 20", assembly["when"])
        self.assertIn("Nov 22, 2099", assembly["when"])
        for r in rows:
            self.assertGreater(r["ends_ts"], r["starts_ts"])
        self.assertEqual(plano["ends_ts"], 4096216800000)            # 2099-10-20T22:00:00Z
        self.assertEqual(ev["until_ts"], max(r["ends_ts"] for r in rows))
        cd = self.items["live:countdown:ev-manual-2099-11-20-neta65-fall-assembly"]
        self.assertEqual((cd["type"], cd["channel"], cd["en"]["title"], cd["es"]["title"], cd["en"]["text"], cd["es"]["text"]),
                         ("countdown", "live-events", "Next assembly", "Próxima asamblea", "NETA 65 Fall Assembly 2099",
                          "Asamblea de Otoño 2099 de NETA 65"))
        self.assertEqual(cd["until_ts"], cd["en"]["rows"][0]["starts_ts"], "a countdown is over when the assembly begins")
        self.assertEqual(cd["en"]["rows"][0]["place"], "Hotel Three, 3 Hotel Rd, Tyler, TX")
        self.assertEqual(cd["qr"], BASE_URL + "events/#2099-11-20-neta65-fall-assembly")
        self.assertEqual(cd["qr_es"], BASE_URL + "es/events/#2099-11-20-neta65-fall-assembly", "its card on the Spanish Events page")

    def test_the_daily_quotes(self):
        quotes = self.live("live-quote")
        self.assertEqual([q["id"] for q in quotes], ["live:quote:gv"], "La Viña's quote is three days old: the Home page drops it too")
        q = quotes[0]
        self.assertEqual((q["type"], q["pub"], q["langs"], q["es"]), ("quote", "gv", ["en"], None))
        self.assertEqual(q["en"]["title"], "Grapevine Daily Quote · Oct 14")
        self.assertEqual(q["en"]["text"], "A sample quote for the tests.")
        self.assertEqual(q["en"]["credit"], "A member, Somewhere, May 1999 · From A sample book")
        self.assertEqual((q["qr"], q["until_ts"]), ("https://www.aagrapevine.org/#quote-of-the-day", 4095896400000))   # 2099-10-17 00:00 CDT
        self.assertIsNone(q["qr_es"], "the official page has no other address for Spanish slides")
        later = self.r["quotesLater"]
        self.assertEqual([x["id"] for x in later], ["live:quote:lv"])
        self.assertEqual((later[0]["langs"], later[0]["en"], later[0]["es"]["title"], later[0]["es"]["credit"]),
                         (["es"], None, "Cita Diaria de La Viña · 13 de octubre", "Un miembro"))

    def test_the_official_videos(self):
        vids = self.live("live-video")
        ids = [v["id"].split(":")[-1] for v in vids]
        self.assertEqual(ids[:3], ["aboutVidEN1", "aboutVidLV2", "otherShort1"])
        self.assertEqual(ids[3:], [f"regular{i:04d}" for i in range(34, 5, -1)], "the newest 30 short videos and Shorts")
        for gone in ("weeklyOpen1", "liveRec0001", "longVideo01", "noDuration1", "shortVid001", "dupeVid0001",
                     "salesShort1", "salesShort2"):
            self.assertNotIn(gone, ids)
        # the app Shorts' sales words (SPEC §4): left out and named — and the list still has its 30 newest
        left = [p for p in self.show["problems"] if p["where"].startswith("YouTube")]
        self.assertEqual(left, [
            {"where": "YouTube: Download Now! Then Subscribe!", "en": "left out of the booth: it says “Download Now”",
             "es": "queda fuera de la pantalla: dice “Download Now”"},
            {"where": "YouTube: ¡Descárgala ahora! ¡Luego suscríbete!", "en": "left out of the booth: it says “Descárgala ahora”",
             "es": "queda fuera de la pantalla: dice “Descárgala ahora”"},
        ])
        about, lv, short = vids[:3]
        self.assertEqual((about["en"]["title"], about["pub"], about["langs"], about["en"]["credit"]),
                         ("About Grapevine", "gv", ["en"], "AA Grapevine & La Viña on YouTube"))
        self.assertEqual((lv["es"]["title"], lv["pub"], lv["langs"], lv["en"], lv["es"]["credit"]),
                         ("Sobre La Viña", "lv", ["es"], None, "AA Grapevine & La Viña en YouTube"))
        self.assertEqual(short["media"], {"kind": "youtube", "src": "https://www.youtube.com/shorts/otherShort1", "id": "otherShort1",
                                          "short": True, "local": False, "poster": "https://i.ytimg.com/vi/otherShort1/hqdefault.jpg",
                                          "start": 0, "end": None, "muted": False, "fit": "contain", "w": None, "h": None, "bytes": None})
        self.assertTrue(all(v["online"] and v["qr"] is None and v["url"].startswith("https://www.youtube.com/") for v in vids))

    def test_the_podcast(self):
        eps = self.live("live-podcast")
        self.assertEqual([e["id"] for e in eps], ["live:podcast:ep08", "live:podcast:ep06", "live:podcast:ep05", "live:podcast:ep04",
                                                  "live:podcast:ep03", "live:podcast:ep02"])
        e = eps[0]
        self.assertEqual((e["type"], e["pub"], e["langs"], e["en"]["title"], e["en"]["text"], e["tags"]),
                         ("audio", "gv", ["en"], "Episode 8 [Season 12, Episode 8]", "AA Grapevine's Podcast", ["podcast"]))
        # no picture: the show's artwork (the fixture's thumb) is the AA GRAPEVINE logo — never on a slide, never in
        # the offline copy
        self.assertEqual((e["media"]["kind"], e["media"]["src"], e["media"]["poster"], e["online"], e["url"]),
                         ("audio", "https://episodes.captivate.fm/episode/ep-gv-08.mp3", None,
                          True, "https://player.captivate.fm/episode/ep-gv-08"))
        self.assertTrue(all(x["media"]["poster"] is None for x in eps))
        self.assertNotIn("/assets/cache/pod/", json.dumps(eps))
        # an episode on the host's file server plays (podcasts.captivate.fm); the newest, on another site, is named
        self.assertEqual(eps[1]["media"]["src"], "https://podcasts.captivate.fm/episode/ep-gv-06.mp3")
        left = [p for p in self.show["problems"] if p["where"].startswith("Podcast")]
        self.assertEqual(left, [{
            "where": "Podcast: Episode 9 [Season 12, Episode 9]",
            "en": "left out of the booth: its sound file is on cdn.example.com, not on the podcast's host (captivate.fm)",
            "es": "queda fuera de la pantalla: su archivo de sonido está en cdn.example.com, no en el sitio del podcast (captivate.fm)",
        }])

    def test_story_themes(self):
        th = self.items["live:themes:next"]
        self.assertEqual((th["type"], th["qr"], th["tags"], th["en"]["title"], th["es"]["title"]),
                         ("themes", BASE_URL + "contribute/", ["writing"], "Upcoming themes & deadlines", "Próximos temas y fechas límite"))
        self.assertEqual(th["qr_es"], BASE_URL + "es/contribute/")
        en, es = th["en"]["rows"], th["es"]["rows"]
        self.assertEqual([r["title"] for r in en], ["Recaídas (Relapses)", "Theme A", "Theme B", "Theme C"])
        self.assertEqual([r["title"] for r in es], ["Recaídas", "Theme A (Tema A)", "Theme B (Tema B)", "Theme C (Tema C)"])
        self.assertEqual((en[0]["when"], es[0]["when"]), ("Due October 20, 2099", "Fecha límite: 20 de octubre de 2099"))
        self.assertEqual((en[0]["note"], es[0]["note"], en[1]["note"]), ("La Viña · May–June 2100", "La Viña · Mayo–Junio 2100", "Grapevine · April 2100"))
        self.assertEqual([r["pub"] for r in en], ["lv", "gv", "gv", "gv"])
        self.assertEqual(th["until_ts"], en[-1]["ends_ts"])

    def test_prices_as_information(self):
        p = self.items["live:prices:subscriptions"]
        self.assertEqual((p["type"], p["qr"], p["tags"]), ("prices", BASE_URL + "shop/#subscriptions", ["prices", "subscribe"]))
        self.assertEqual(p["qr_es"], BASE_URL + "es/shop/#subscriptions")
        self.assertEqual((p["en"]["title"], p["es"]["title"]), ("Subscriptions", "Suscripciones"))
        self.assertEqual(p["en"]["text"], "Prices as of October 14, 2099, from the official stores")
        self.assertEqual(p["es"]["text"], "Precios al 14 de octubre de 2099, según las tiendas oficiales")
        self.assertEqual([(r["title"], r["when"], r["note"]) for r in p["en"]["rows"]], [
            ("Grapevine · Print · 1 year", "$36.00", "From Jan 1, 2100: $39.00"),
            ("Grapevine · Digital · 1 year", "$29.99", "From Jan 1, 2100: $34.00"),
            ("La Viña · Print · 1 year", "$18.00", "From Jan 1, 2100: $19.50"),
            ("La Viña · Digital · 1 year", "$14.99", "From Jan 1, 2100: $17.00"),
        ])
        self.assertEqual(p["es"]["rows"][0]["title"], "Grapevine · Impresa · 1 año")
        self.assertEqual(p["until_ts"], 4102466400000, "until the new prices take effect (2100-01-01 00:00 CST)")

    def test_books_of_the_month_without_covers(self):
        books = self.live("live-book")
        self.assertEqual([b["id"] for b in books], ["live:book:gv", "live:book:lv"])
        gv, lv = books
        self.assertIsNone(gv["media"])
        self.assertNotIn("/assets/cache/shop/", json.dumps(books))
        self.assertEqual((gv["en"]["title"], gv["es"]["title"], gv["langs"]), ("A Grapevine Book", "A Grapevine Book", ["en", "es"]))
        self.assertLessEqual(len(gv["en"]["text"]), 200)
        self.assertTrue(gv["en"]["text"].endswith("…"))
        # a book in the other language says so first, as /shop/ does: its language and its title's translation (the
        # fixture's translations are automatic: "Auto-translated")
        self.assertEqual(gv["es"]["text"], "En inglés · Traducción automática: Un libro de Grapevine\n"
                                           "Historias de miembros que se mantuvieron sobrios en tiempos difíciles.")
        self.assertEqual(lv["en"]["text"], "In Spanish · Auto-translated: A La Viña Book\nShort stories.")
        self.assertEqual(lv["es"]["text"], "Historias breves.")
        self.assertEqual(gv["en"]["explain"], "$11.99 instead of $14.99, until October 31")
        self.assertEqual(gv["es"]["explain"], "$11.99 en vez de $14.99, hasta el 31 de octubre")
        self.assertEqual((gv["en"]["credit"], lv["es"]["credit"]), ("Grapevine · Book of the Month · October", "La Viña · Libro del mes · Octubre"))
        self.assertEqual((gv["qr"], lv["qr"]), ("https://www.aagrapevine.org/store/a-grapevine-book", "https://www.aalavina.org/tienda/un-libro"))
        self.assertEqual((gv["qr_es"], lv["qr_es"]), (None, None))
        self.assertEqual(gv["until_ts"], 4097192400000)   # the offer's last day (October 31) is over: 2099-11-01 00:00 CDT

    def test_the_meetings(self):
        m = self.items["live:meetings:next"]
        self.assertEqual((m["type"], m["qr"], m["en"]["title"], m["es"]["title"]),
                         ("meetings", BASE_URL + "meetings/", "Meetings you can join", "Reuniones a las que puedes unirte"))
        self.assertEqual(m["qr_es"], BASE_URL + "es/meetings/")
        rows = m["en"]["rows"]
        self.assertEqual([r["title"] for r in rows], ["NETA 65 Grapevine & La Viña Committee Meeting", "Grapevine Weekly Open AA Meeting",
                                                      "La Viña Open Meeting (in Spanish)", "La Viña Monthly Virtual Workshop (in Spanish)"])
        # (committee.js writes the clock with thin and narrow no-break spaces, as /meetings/ shows it)
        self.assertEqual(re.sub(r"[   ]", " ", rows[0]["when"]), "Every third Wednesday of the month · 7:00 – 8:00 PM Central time")
        self.assertEqual(rows[0]["note"], "Online on Zoom · Meeting ID 949 476 7497")
        self.assertEqual((rows[1]["when"], rows[1]["note"], rows[1]["pub"]), ("Wednesdays at 11:00 AM Central", "Zoom 871 2036 8287", "gv"))
        self.assertTrue(rows[2]["note"].startswith("Starts ") and "November 5, 2099" in rows[2]["note"])
        self.assertTrue(m["es"]["rows"][2]["note"].startswith("Comienza el "))
        self.assertEqual((rows[3]["pub"], rows[3]["note"]), ("lv", "Online on Zoom"))
        self.assertEqual(rows[3]["ends_ts"], 4096987200000)   # 2099-10-29T20:00:00Z
        self.assertEqual(m["es"]["rows"][0]["title"], "Reunión del Comité de Grapevine y La Viña de NETA 65")
        # a meeting in the other language says so, as /meetings/ does — never twice (La Viña's English titles say
        # "(in Spanish)" already, above)
        self.assertEqual([r["title"] for r in m["es"]["rows"][1:]], ["Grapevine Weekly Open AA Meeting (en inglés)",
                                                                     "Reunión Abierta de La Viña", "Taller Mensual y Virtual de La Viña"])

    def test_the_bulletin(self):
        posts = self.live("live-bulletin")
        self.assertEqual([p["id"] for p in posts], ["live:bulletin:p1", "live:bulletin:p3"])
        p1, p3 = posts
        # the teaser: the post's first paragraph — never its heading and list run into it ("… Why it matters A meeting
        # in print. Grapevine and La Viña reach millions …")
        self.assertEqual((p1["type"], p1["en"]["title"], p1["en"]["text"], p1["es"]["text"]),
                         ("message", "Pinned post", "A pinned post about the workshops.", "Un aviso fijado sobre los talleres."))
        # a heading at the top skipped, *italic* marks gone; no Spanish body: the Spanish summary, not the English body
        self.assertEqual((p3["en"]["text"], p3["es"]["text"]), ("An older post, with a link.", "Un aviso anterior."))
        self.assertEqual((p1["qr"], p1["until_ts"]), (BASE_URL + "bulletin/#p1", 4102466400000))   # 2099-12-31 is over
        self.assertEqual(p1["qr_es"], BASE_URL + "es/bulletin/#p1", "the same post on the Spanish bulletin")
        left = [p for p in self.show["problems"] if p["where"].startswith("Bulletin")]
        self.assertEqual(left, [{"where": "Bulletin: Newest post", "en": "left out of the booth: it says “PDF”",
                                 "es": "queda fuera de la pantalla: dice “PDF”"}])

    def test_no_refused_word_in_any_live_or_drive_item(self):
        self.assertEqual(self.r["refused"], [])

    # -- QR codes, channels, picking the event, problems, version, defaults --------------------------------------
    def test_the_qr_map(self):
        # every code a slide may show: each item's English one and Spanish one, then the site's two homes
        want = []
        for u in [u for it in self.show["items"] for u in (it["qr"], it["qr_es"])] + [BASE_URL, BASE_URL + "es/"]:
            if u and u not in want:
                want.append(u)
        self.assertEqual(list(self.show["qr"]), want)
        self.assertIn(BASE_URL + "es/contribute/", self.show["qr"], "the Spanish code of a {site} row")
        self.assertTrue(self.r["qrSvgOk"], "every code is an SVG (margin 2), hidden from screen readers: the player labels it")

    def test_the_channels(self):
        counts: dict[str, int] = {}
        for it in self.show["items"]:
            counts[it["channel"]] = counts.get(it["channel"], 0) + 1
        self.assertEqual(self.show["channels"], [{"id": c, "count": counts[c]} for c in CHANNELS if c in counts])
        self.assertEqual({c["id"] for c in self.show["channels"]} - set(CHANNELS), set())

    def test_picking_the_event(self):
        pick = self.show["events_pick"]
        self.assertEqual([p["id"] for p in pick], ["ev:manual:2099-10-20-writing", "ev:recurring:citywide-dallas:2099-10-24",
                                                   "ev:recurring:citywide-dallas:2099-11-14", "ev:manual:2099-11-20-neta65-fall-assembly",
                                                   "ev:manual:2100-03-19-neta65-spring-assembly"])
        self.assertEqual(list(pick[0]), ["id", "title_en", "title_es", "date_label_en", "date_label_es", "place"])
        self.assertEqual((pick[0]["title_es"], pick[0]["place"]), ("Taller de Escritura de Grapevine — Plano", "Group Two, 2 Elm St, Plano, TX"))
        self.assertEqual(pick[-1]["place"], "", "a venue to be announced is no place yet")
        self.assertIn("2099", pick[3]["date_label_en"])

    def test_problems_never_stop_it(self):
        where = [p["where"] for p in self.show["problems"]]
        self.assertFalse([w for w in where if w.startswith("show.csv")], "the fixture's CSV is good")
        for p in self.show["problems"]:
            self.assertEqual(list(p), ["where", "en", "es"])
            self.assertTrue(p["en"] and p["es"])
        self.assertFalse([p for p in self.show["problems"] if p["where"] == "Live items"], "no live part failed")
        self.assertEqual(self.r["missingCsv"][0], {"where": "no-such.csv", "en": "tests/fixtures/booth_csv/no-such.csv was not found: the show has no rows from it",
                                                   "es": "no se encontró tests/fixtures/booth_csv/no-such.csv: la pantalla no tiene filas de ese archivo"})
        self.assertEqual(len(self.r["badDrive"]), 1)
        self.assertIn("could not be read", self.r["badDrive"][0]["en"])
        e = self.r["empty"]
        self.assertEqual((e["items"], e["channels"], e["events_pick"], e["problems"]), ([], [], [], []))
        self.assertEqual(e["qr"], [BASE_URL, BASE_URL + "es/"], "even an empty show has the site's two QR codes")

    def test_a_stable_version(self):
        v = self.r["versions"]
        self.assertEqual(v["first"], v["again"])
        self.assertEqual(v["first"], v["rebuilt"], "a new build of the same show keeps its version")
        self.assertNotEqual(v["first"], v["otherCsv"])
        self.assertNotEqual(v["first"], v["otherDefaults"])

    def test_the_starting_settings(self):
        good, bad, none = self.r["defaults"]
        self.assertEqual((good["defaults"], good["max_file_mb"], good["max_total_mb"], good["problems"]),
                         ({"event": {"en": "NETA 65 Fall Assembly", "es": "Asamblea de Otoño de NETA 65"}, "lang": "es", "sound": True}, 50, 400, []))
        self.assertEqual((none["defaults"], none["max_file_mb"], none["max_total_mb"], none["problems"]),
                         ({"event": {"en": "", "es": ""}, "lang": "both", "sound": False}, 95, 400, []))
        self.assertEqual(bad["defaults"], {"event": {"en": "", "es": "x" * 80}, "lang": "both", "sound": False})
        self.assertEqual([f"{p['where']}: {p['en']}" for p in bad["problems"]], [
            "config/site.yml booth.defaults.event_name: the event's name must be a text in quotes",
            "config/site.yml booth.defaults.event_name_es: the event's name is 90 characters long: at most 80",
            'config/site.yml booth.defaults.language: "french" is not en, es, both or alternate: both is used',
            'config/site.yml booth.defaults.sound: "loud" is not true or false: false is used',
            'config/site.yml booth.max_total_mb: "lots" is not a number of megabytes: 400 is used',
        ])


DRIVE_WORDS_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const r = B.driveItems(input.drive, input.manifest, "/aagrapevine/");
out({ items: r.items.map((i) => i.id), problems: r.problems, shown: r.items });
"""


class DriveWords(unittest.TestCase):
    """driveItems with what the sync and the download step write today (docs/DATA_SCHEMA.md booth.json, SPEC §2.3):
    the sync's problems carry their own Spanish words (problem_es); the manifest's skipped files a `code` — worded in
    Spanish here — and one past its last day since the sync ("expired") is left out without a note."""

    def test_the_sync_and_the_download_step_words(self):
        node_ready(self)

        def item(fid, kind, name):
            return {"id": f"drive:{fid}", "file_id": fid, "name": name, "kind": kind, "pub": "both", "langs": [],
                    "title": name.rsplit(".", 1)[0], "caption": True, "collection": "main", "image_url": None}

        drive = {"items": [item("fileVideoBig1", "video", "Big.mp4"), item("fileVideoOld1", "video", "Old (until 2099-01-01).mp4"),
                           item("fileSoundLate", "audio", "Late.mp3")],
                 "problems": [{"file": "booth/clip.avi", "problem": "a video type browsers do not play",
                               "problem_es": "un tipo de video que los navegadores no reproducen", "code": "video-type"}]}
        manifest = {"built": "2099-10-15T11:30:00Z", "items": {}, "skipped": [
            {"file_id": "fileVideoBig1", "name": "Big.mp4", "code": "too_big",
             "reason": "too big to save for offline (120 MB; one video or sound file may have 95 MB — config/site.yml booth.max_file_mb)"},
            {"file_id": "fileVideoOld1", "name": "Old (until 2099-01-01).mp4", "code": "expired",
             "reason": "past its last day (2099-01-01), so it is not saved"},
            {"file_id": "fileSoundLate", "name": "Late.mp3", "code": "out_of_time",
             "reason": "not downloaded: this run's time for downloads ran out (the next run tries again)"}]}
        r = run_js(self, DRIVE_WORDS_JS, data={"drive": drive, "manifest": manifest})
        self.assertEqual(r["items"], [])
        by = {p["where"]: p for p in r["problems"]}
        self.assertEqual(sorted(by), ["Drive: booth/Big.mp4", "Drive: booth/Late.mp3", "Drive: booth/clip.avi"], "no note for the expired file")
        self.assertIn("(120 MB;", by["Drive: booth/Big.mp4"]["en"])
        self.assertTrue(by["Drive: booth/Big.mp4"]["es"].endswith(": es demasiado grande para guardarlo para usar sin conexión (config/site.yml booth.max_file_mb)"))
        self.assertIn("se acabó el tiempo para descargas", by["Drive: booth/Late.mp3"]["es"])
        self.assertEqual((by["Drive: booth/clip.avi"]["en"], by["Drive: booth/clip.avi"]["es"]),
                         ("a video type browsers do not play", "un tipo de video que los navegadores no reproducen"))

    def test_a_refused_word_leaves_a_file_out(self):
        # the CSV's rule for the folder the committee fills by hand: a caption, or a note's heading or text, that says
        # a word the booth never shows leaves the file out, named; "(no caption)" shows the picture without its title
        node_ready(self)

        def item(fid, kind, name, title, caption=True, text=None):
            return {"id": f"drive:{fid}", "file_id": fid, "name": name, "kind": kind, "pub": "gv", "langs": ["en"],
                    "title": title, "caption": caption, "collection": "main", "text": text,
                    "image_url": f"https://lh3.googleusercontent.com/d/{fid}=s1920"}

        drive = {"items": [
            item("filePosterPdf", "poster", "GV EN Order form (PDF).png", "Order form (PDF)"),
            item("fileNoteGift1", "message", "GV EN Ask us.txt", "Ask us",
                 text="Ask us how your group can donate to Grapevine. Hurry, limited time!"),
            item("filePosterOk1", "poster", "GV EN Order form (PDF) (no caption).png", "Order form (PDF)", caption=False),
            item("fileNoteFine1", "message", "GV EN Welcome.txt", "Welcome", text="Ask us about the Carry the Message gift."),
        ]}
        r = run_js(self, DRIVE_WORDS_JS, data={"drive": drive, "manifest": None})
        self.assertEqual(r["items"], ["drive:filePosterOk1", "drive:fileNoteFine1"])
        self.assertEqual(r["problems"], [
            {"where": "Drive: booth/GV EN Order form (PDF).png", "en": "left out of the booth: it says “PDF”",
             "es": "queda fuera de la pantalla: dice “PDF”"},
            {"where": "Drive: booth/GV EN Ask us.txt", "en": "left out of the booth: it says “donate”",
             "es": "queda fuera de la pantalla: dice “donate”"},
        ])
        self.assertIsNone(r["shown"][0]["en"], "(no caption): the picture alone, without the title it has in its name")


LIVE_LINKS_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const r = B.liveItems({ db: input.db, site: input.site, now: new Date(input.now), base: "/aagrapevine/" });
out(r.items.filter((i) => i.channel === "live-events" || i.channel === "live-book")
  .map((i) => ({ id: i.id, qr: i.qr, qr_es: i.qr_es, url: i.url })));
"""


class LiveLinks(unittest.TestCase):
    """A live item's QR code is a page, never a document file (an event's flyer, an offer's leaflet): the player prints
    the address under the code, and a visitor never reads "PDF" — the CSV's qr_url has the same rule."""

    def test_a_document_link_is_never_a_code(self):
        node_ready(self)
        # (a content/events file whose link is the flyer itself)
        asm = event("ev:manual:2099-11-20-fall-assembly", "NETA 65 Fall Assembly 2099", "Asamblea de Otoño 2099 de NETA 65",
                    "2099-11-20", "2099-11-22", location="Hotel Three, 3 Hotel Rd, Tyler, TX")
        asm["url"] = "https://www.neta65.org/wp-content/uploads/2099/09/Fall-Assembly-Flyer.pdf"
        book = dict(SHOP["botm"][0], url="https://www.aagrapevine.org/files/BOTM-October.PDF")
        db = {"events": {"items": [asm]}, "shop": {**SHOP, "botm": [book]}}
        got = {i["id"].split(":")[1]: i for i in run_js(self, LIVE_LINKS_JS, data={"db": db, "site": SITE_X, "now": NOW})}
        self.assertEqual(sorted(got), ["book", "countdown", "events"])
        cd = got["countdown"]
        self.assertEqual((cd["qr"], cd["qr_es"], cd["url"]), (BASE_URL + "events/", BASE_URL + "es/events/", BASE_URL + "events/"),
                         "the flyer's document: the Events page instead")
        self.assertEqual((got["book"]["qr"], got["book"]["url"]), ("https://www.aagrapevine.org/BOTM",) * 2,
                         "the offer's leaflet: the store's Book of the Month page instead")
        self.assertNotIn("pdf", json.dumps(got).lower())


class Build(unittest.TestCase):
    """A real build of /about/booth.json alone, as GitHub Pages builds the site."""

    @classmethod
    def build(cls, out: Path, **env_extra) -> subprocess.CompletedProcess:
        env = {**os.environ, "PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1", "ONLY": "booth-json,sitemap",
               "NODE_NO_WARNINGS": "1", "BOOTH_CSV": FIX + "show.csv", "BOOTH_DRIVE": FIX + "drive-booth.json",
               "BOOTH_MANIFEST": FIX + "booth-manifest.json", **env_extra}
        env.pop("MONTHLY_NOW", None)
        return subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet", "--output", str(out)],
                              cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)

    @classmethod
    def setUpClass(cls):
        cls.tmp = None
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="booth-build-"))
        cls.run1 = cls.build(cls.tmp / "site")
        cls.run2 = cls.build(cls.tmp / "site-nocsv", BOOTH_CSV=FIX + "no-such.csv", BOOTH_MANIFEST=FIX + "no-such.json")
        f = cls.tmp / "site" / "about" / "booth.json"
        cls.json = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None
        f2 = cls.tmp / "site-nocsv" / "about" / "booth.json"
        cls.json2 = json.loads(f2.read_text(encoding="utf-8")) if f2.is_file() else None

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, True)

    def setUp(self):
        node_ready(self)
        self.assertEqual(self.run1.returncode, 0, self.run1.stderr[-3000:])
        self.assertEqual(self.run2.returncode, 0, self.run2.stderr[-3000:])

    def test_the_file(self):
        j = self.json
        self.assertIsNotNone(j)
        self.assertEqual(list(j), TOP)
        self.assertEqual((j["app"], j["schema"], j["site"]["url"], j["site"]["base"]), ("gv-booth", 1, REAL_BASE, "/aagrapevine/"))
        self.assertRegex(j["version"], HEX12)
        self.assertRegex(j["built"], ISO)
        self.assertRegex(j["as_of"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual([it["id"] for it in j["items"] if it["source"] == "csv"],
                         ["quiz-one", "video-short", "video-dupe", "audio-dupe", "message-event"])
        welcome = next(it for it in j["items"] if it["id"] == "drive:fileWelcome01")
        self.assertEqual(welcome["media"]["src"], "/aagrapevine/about/booth/media/filewe-welcome.png")
        self.assertEqual(j["defaults"], {"event": {"en": "", "es": ""}, "lang": "both", "sound": False},
                         "config/site.yml booth.defaults: no event name, both languages, sound off")
        for it in j["items"]:
            self.assertEqual(list(it), ITEM)

    def test_not_a_page(self):
        sitemap = (self.tmp / "site" / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("booth.json", sitemap)
        src = (ROOT / "src" / "pages" / "booth-json.11ty.js").read_text(encoding="utf-8")
        self.assertIn("eleventyExcludeFromCollections: true", src)
        self.assertIn('permalink: "/about/booth.json"', src)

    def test_without_the_csv_and_the_copies(self):
        j = self.json2
        self.assertIsNotNone(j)
        self.assertFalse([it for it in j["items"] if it["source"] == "csv"])
        self.assertIn(FIX + "no-such.csv was not found: the show has no rows from it", [p["en"] for p in j["problems"]])
        self.assertTrue([p for p in j["problems"] if "not downloaded in this build" in p["en"]])
        self.assertIn("[booth]", self.run2.stderr + self.run2.stdout, "the build log names the problems")


if __name__ == "__main__":
    unittest.main()
