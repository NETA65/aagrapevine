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
      - the QR map, the channels, "pick the event", the problems, a stable version, the defaults (booth.defaults with
        photo_every → galleryEvery, booth.photos; a value it cannot read keeps its default, named);
  * Gallery — the Photos page's pictures (liveGallery) from a made-up drive.json: every album /photos/ shows but "To
    Organize" (no video, no file gone, no document), in five groups (the committee's own albums, Grapevine's covers,
    La Viña's, other countries' AA magazines, the Grapevine archive) with their channel, slide type, picture size and
    magazine; captions in both languages, never machine-made (the covers' own titles, "Grapevine · October 1951",
    "Partage · Bélgica · agosto de 1992", an album's name in Spanish only when a person wrote it); the publishers'
    line on every magazine slide (the /photos/ hero's, word for word), other countries' magazines their own; a name
    in booth.photos takes the folders inside its album too ("Historical Archive / 1960"; "To Organize / 1950s" never
    plays), never an album whose name only starts like it; a cover in an album booth.photos does not name keeps the
    publishers' line when its own name says so as a whole word ("1965-06-Gv-00-Cover.jpg", "1999-05-La-Vina-00.jpg")
    or holds, anywhere in it, an issue written the archive's way, with a day of 00 ("1965-10-00-I-Am-Responsible.jpg",
    "Scan of 1947-11-00.jpg"; never "Recovery Walk", a real day, nor the album's name alone — a phone or camera
    name, whose title is the album's name and a number, by its file name only); this file's copy of MAG_WORDS is the
    code's own; the build log names the day's live items' problems (logProblems: the boothJson filter), never the
    `booth` global's again; a world or archive name no album has is a problem line (never a leave_out name, nor with no
    album at all, nor for an album whose pictures are all in folders inside it); the same credit lines on the real
    data/site/drive.json (the code on the day's data); the day's data itself, no problem line and today's own photos
    ("2026 Displays") there with no credit line (test_todays_albums: the Code check runs it, the publish gate does not —
    scripts/ops/gate_tests.py DATA_TESTS); the group's place on /photos/ as the QR code; a refused word leaves its
    picture out, named, before the day's set is counted; a day's per_day of each group, a different block the next day,
    every picture in turn; none in a COMMITTEE_EMPTY preview;
  * Build — a real Eleventy build of /about/booth.json alone (ONLY=booth-json) from the same fixtures, as GitHub
    Pages builds it (PATH_PREFIX=/aagrapevine/, I18N_STRICT=1): the file, its base path, not in the sitemap; and a
    build without the CSV (a problem line, in the file and in the build log's block of the owner's files — never a
    failed build).
Offline. Skipped without Node.js or without node_modules (npm ci), as in tests/nodejs.py.

    python -m unittest tests.test_booth_build -v
"""
from __future__ import annotations

import datetime
import hashlib
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
GALLERY = ["gallery-ours", "gallery-gv", "gallery-lv", "gallery-world", "gallery-archive"]
CHANNELS = ["quiz", "puzzles", "facts", "quotes", "polls", "prompts", "messages", "qr", "web-video", "web-audio",
            "web-image", "photos", "posters", "videos", "sounds", "notes", "live-events", "live-quote", "live-video",
            "live-podcast", "live-themes", "live-prices", "live-book", "live-meetings", "live-bulletin"] + GALLERY


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
                                    "platform": "Zoom", "meeting_id": "123 456 7890"},
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
    language: "french", sound: "loud", photo_every: 3 }, max_total_mb: "lots",
    photos: { per_day: "many", leave_out: [["To Organize"]], world: "International-Equivalent", archive: 12 } }),
    B.boothDefaults(null), B.boothDefaults({ defaults: { photo_every: 30 }, photos: { per_day: 200, leave_out: [] } }),
    B.boothDefaults({ defaults: { photo_every: "8" }, photos: { per_day: 3 } }), B.boothDefaults({ defaults: { photo_every: 8.5 }, photos: "all" })],
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
                                         "lang": "es", "sound": True, "galleryEvery": 8})
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
        # the credit line ends with the publishers' permission credits, as the Home card shows them under the quotes:
        # each its own part, " · " between them, and "A.A." kept on the line of "World Services" (a no-break space)
        self.assertEqual(q["en"]["credit"], "A member, Somewhere, May 1999 · From A sample book · Reprinted with permission of "
                         "A.A.\u00a0World Services, Inc. · Copyright © The AA Grapevine, Inc. Reprinted with permission. All rights reserved.")
        self.assertEqual((q["qr"], q["until_ts"]), ("https://www.aagrapevine.org/#quote-of-the-day", 4095896400000))   # 2099-10-17 00:00 CDT
        self.assertIsNone(q["qr_es"], "the official page has no other address for Spanish slides")
        later = self.r["quotesLater"]
        self.assertEqual([x["id"] for x in later], ["live:quote:lv"])
        self.assertEqual((later[0]["langs"], later[0]["en"], later[0]["es"]["title"], later[0]["es"]["credit"]),
                         (["es"], None, "Cita Diaria de La Viña · 13 de octubre", "Un miembro · Reimpreso con permiso de A.A.\u00a0"
                          "World Services, Inc. · Copyright © The AA Grapevine, Inc. Reimpreso con permiso. Todos los derechos reservados."))

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
        self.assertEqual(rows[0]["note"], "Online on Zoom · Meeting ID 123 456 7890")
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
        good, bad, none, edges, text, odd = self.r["defaults"]
        usual = {"per_day": 20, "leave_out": ["To Organize"], "world": ["International-Equivalent"], "archive": ["Historical Archive"]}
        self.assertEqual((good["defaults"], good["max_file_mb"], good["max_total_mb"], good["photos"], good["problems"]),
                         ({"event": {"en": "NETA 65 Fall Assembly", "es": "Asamblea de Otoño de NETA 65"}, "lang": "es", "sound": True,
                           "galleryEvery": 8}, 50, 400, usual, []))
        self.assertEqual((none["defaults"], none["max_file_mb"], none["max_total_mb"], none["photos"], none["problems"]),
                         ({"event": {"en": "", "es": ""}, "lang": "both", "sound": False, "galleryEvery": 8}, 95, 400, usual, []))
        self.assertEqual(bad["defaults"], {"event": {"en": "", "es": "x" * 80}, "lang": "both", "sound": False, "galleryEvery": 8})
        # (one album name alone is a list of one)
        self.assertEqual(bad["photos"], {**usual, "world": ["International-Equivalent"]})
        self.assertEqual([f"{p['where']}: {p['en']}" for p in bad["problems"]], [
            "config/site.yml booth.defaults.event_name: the event's name must be a text in quotes",
            "config/site.yml booth.defaults.event_name_es: the event's name is 90 characters long: at most 80",
            'config/site.yml booth.defaults.language: "french" is not en, es, both or alternate: both is used',
            'config/site.yml booth.defaults.sound: "loud" is not true or false: false is used',
            'config/site.yml booth.defaults.photo_every: "3" is not a number from 4 to 30: 8 is used',
            'config/site.yml booth.max_total_mb: "lots" is not a number of megabytes: 400 is used',
            'config/site.yml booth.photos.per_day: "many" is not a number from 4 to 200: 20 is used',
            'config/site.yml booth.photos.leave_out: is not a list of album names: ["To Organize"] is used',
            'config/site.yml booth.photos.archive: is not a list of album names: ["Historical Archive"] is used',
        ])
        es = [p["es"] for p in bad["problems"]]
        self.assertEqual((es[4], es[6]), ('"3" no es un número del 4 al 30: se usa 8', '"many" no es un número del 4 al 200: se usa 20'))
        # the ends of the ranges, an empty list (every album plays), a number written as a text
        self.assertEqual((edges["defaults"]["galleryEvery"], edges["photos"]["per_day"], edges["photos"]["leave_out"], edges["problems"]),
                         (30, 200, [], []))
        self.assertEqual((text["defaults"]["galleryEvery"], text["photos"]["per_day"]), (8, 20))
        self.assertEqual([p["where"] for p in text["problems"]], ["config/site.yml booth.photos.per_day"])
        self.assertEqual((odd["defaults"]["galleryEvery"], odd["photos"]), (8, usual))
        self.assertEqual([f"{p['where']}: {p['en']}" for p in odd["problems"]], [
            'config/site.yml booth.defaults.photo_every: "8.5" is not a number from 4 to 30: 8 is used',
            "config/site.yml booth.photos: must hold its settings (per_day, leave_out, world, archive): the usual ones are used",
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


HTTP_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const F = "tests/fixtures/booth_csv/";
const show = (url) => {
  const site = { ...input.site, url };
  const booth = B.loadBooth({ csv: F + "show.csv", drive: F + "drive-booth.json", manifest: F + "booth-manifest.json",
    config: input.config, site, base: "/" });
  const s = B.boothShow(booth, { db: input.db, site, now: new Date(input.now), base: "/" });
  return { site: s.site, problems: s.problems.map((p) => p.where + ": " + p.en), qr: Object.keys(s.qr),
    items: s.items.map((i) => ({ id: i.id, qr: i.qr, qr_es: i.qr_es, url: i.url })) };
};
out({ http: show(input.http), https: show(input.https) });
"""


class HttpAddress(unittest.TestCase):
    """A custom domain is served on http:// until GitHub issues its certificate and the owner ticks "Enforce HTTPS",
    and the deploy builds for the address GitHub Pages reports — so for a while the site's own address is http://.
    The show is then the same as on https://: every CSV row with a {site} code, every live item's code, the same QR
    map, each page of this site with the site's own scheme (another host still needs https://: Rules in
    tests/test_booth_csv.py)."""

    def test_the_same_show_on_http(self):
        node_ready(self)
        http, https = "http://grapevine.example.org", "https://grapevine.example.org"
        r = run_js(self, HTTP_JS, data={"db": DB_X, "site": SITE_X, "config": CONFIG_X, "now": NOW,
                                        "http": http, "https": https})
        swap = lambda v: v.replace(https + "/", http + "/") if isinstance(v, str) else v  # noqa: E731
        h, s = r["http"], r["https"]
        self.assertEqual((h["site"]["url"], h["site"]["url_es"], h["site"]["host"]),
                         (http + "/", http + "/es/", "grapevine.example.org"))
        self.assertEqual(h["problems"], [swap(p) for p in s["problems"]])
        self.assertEqual(h["items"], [{k: swap(v) for k, v in it.items()} for it in s["items"]])
        self.assertEqual(h["qr"], [swap(u) for u in s["qr"]])
        own = [it for it in h["items"] if (it["qr"] or "").startswith(http + "/")]
        self.assertTrue(any(it["id"].startswith("live:") for it in own), "the live items' codes (events, meetings …)")
        self.assertTrue(any(not it["id"].startswith("live:") for it in own), "the CSV's {site} codes")
        self.assertFalse(any("{site" in p for p in h["problems"]), h["problems"])


# ----------------------------------------------------------------------------------------------------------------
# The gallery: the Photos page's pictures (data/site/drive.json's shape, docs/DATA_SCHEMA.md — category "photos")
# ----------------------------------------------------------------------------------------------------------------
def picture(fid, album, name, title=None, *, lang="en", machine=("es",), title_es=None, album_es=None, cover=None,
            kind="photo", status="ok", date="2026-05-01", generic=False):
    """generic: a phone or camera name ("IMG_1234.jpg") — drive.py's extra.generic_name, and then its title is the
    album's name and a number ("Grapevine History #1")."""
    title = title if title is not None else name.rsplit(".", 1)[0]
    ext = {"file_id": fid, "mime": "image/jpeg", "name": name, "panel": 77, "panel_label": "Panel 77",
           "path": ["photos", *album.split(" / ")], "album": album, "thumb_url": f"https://lh3.googleusercontent.com/d/{fid}=w600",
           # (the sync's image_url can be null — drive.py — the booth builds its own address from the file's id)
           "image_url": None, "is_image": kind == "photo", "is_video": kind == "video_file", "is_pdf": False}
    if cover:
        ext["cover"] = cover
    if generic:
        ext["generic_name"] = True
    return {"id": f"drive:{fid}", "source": "drive", "kind": kind, "url": f"https://drive.google.com/file/d/{fid}/view",
            "title": title, "lang": lang, "date": f"{date}T12:00:00Z", "first_seen": None,
            "image": f"https://lh3.googleusercontent.com/d/{fid}=w600", "tags": ["panel-77"], "category": "photos",
            "status": status, "extra": ext,
            "i18n": {"title": {"en": title, "es": title_es or title}, "album": {"en": album, "es": album_es or album}},
            "machine": list(machine), "is_new": False}


def gv_cover(year, month, name=None):
    key = f"{year}-{month:02d}"
    return picture(f"gvCover{year}{month:02d}", f"Grapevine covers {year}", name or f"GV_{key}.jpg", f"Grapevine — {key}",
                   machine=(), album_es=f"Portadas de Grapevine {year}", date=f"{key}-01",
                   cover={"pub": "gv", "year": year, "month": month, "issue": None, "months": [month], "key": key})


def lv_cover(year, issue):
    month = 2 * issue - 1
    key = f"{year}-{month:02d}"
    return picture(f"lvCover{year}{issue}", f"La Viña covers {year}", f"LaVina_{year}-{issue:02d}.jpg", f"La Viña — {key}",
                   lang="es", machine=(), album_es=f"Portadas de La Viña {year}", date=f"{key}-01",
                   cover={"pub": "lv", "year": year, "month": None, "issue": issue, "months": [month, month + 1], "key": key})


WORLD = "International-Equivalent"
ARCHIVE = "Historical Archive"
# 25 Grapevine covers (2024, 2025 and January 2026: more than a day's 20) and one whose file name says "PDF"
GV_COVERS = [gv_cover(y, m) for y in (2024, 2025) for m in range(1, 13)] + [gv_cover(2026, 1)]
DRIVE_PICTURES = [
    # the committee's own albums: one machine-translated (its Spanish name is never shown), one named in Spanish by hand
    *[picture(f"tableDisplay{i}", "Table Displays", f"Panel 75 Displays ({i}).jpeg", "Panel 75 Displays",
              title_es="Panel 75 pantallas", album_es="Pantallas de mesa", date="2026-06-01") for i in range(1, 4)],
    picture("tableDonate1", "Table Displays", "Donation jar.jpg", "Donation jar", album_es="Pantallas de mesa", date="2026-06-01"),
    picture("tableVideo01", "Table Displays", "Booth walk-through.mp4", kind="video_file", date="2026-06-01"),
    picture("tableGone001", "Table Displays", "Removed.jpg", status="gone", date="2026-06-01"),
    picture("tableSlide01", "Table Displays", "A document.jpg", kind="document", date="2026-06-01"),
    picture("boothPhoto01", "Booth Photos", "Mesa 1.jpg", "Mesa 1", lang="es", machine=("en",), album_es="Fotos de la mesa",
            date="2026-04-01"),
    # the staging folder: never at the booth
    *[picture(f"organize000{i}", "To Organize", f"1955-12-Gv-outside-0{i}.jpg", date="2026-07-01") for i in range(1, 3)],
    # other countries' AA magazines (their machine-made Spanish titles are never shown)
    *[picture(f"world{n:02d}abc", WORLD, name, title_es=f"Parte correspondiente {n}", album_es="International-Equivallent",
              date="2026-03-01")
      for n, name in enumerate(["Belgium_Partage_1992-08.jpg", "Uruguay_El-Triangulo_1997-01-02.jpg",
                                "Mexico_Plenitud-AA_20th-Anniversary.jpg", "Sweden_Bulletinen.jpg", "Russia_Az-Buki_1998_No2.jpg",
                                "Australia_Antenna_1991-Spring.jpg", "Atlantis_Box-12_1993-04.jpg", "Scan0001.jpg"])],
    # old Grapevine pages
    picture("archive0001", ARCHIVE, "1951-10-Gv-Report-00.png", date="2026-02-01"),
    picture("archive0002", ARCHIVE, "1948-04-Gv-V04-N11-Subscription.png", date="2026-02-01"),
    picture("archive0003", ARCHIVE, "Gv-Poster-Undated.png", date="2026-02-01"),
    *GV_COVERS,
    gv_cover(2023, 6, "GV_2023-06_June-PDF-scan.jpg"),
    lv_cover(2025, 6), lv_cover(2025, 5), lv_cover(2026, 1),
]
GALLERY_CASED = {"per_day": 20, "leave_out": ["to organize"], "world": ["INTERNATIONAL-EQUIVALENT"], "archive": ["historical archive"]}
GALLERY_DAYS = [f"2099-10-{d}T17:00:00Z" for d in range(15, 22)]
# albums only some of whose pictures were machine-translated (photoAlbums names the album after the first picture it
# meets, here a machine-made one): the magazines' album when booth.photos.world names it no more (as in
# data/site/drive.json: most of its pictures machine-made, a few not), and one the machine named in Spanish first
GALLERY_MIXED = [
    *[p for p in DRIVE_PICTURES if p["extra"]["album"] == WORLD],
    picture("world99abc", WORLD, "Spain_Boletin_1990-05.jpg", machine=(), date="2026-03-01"),
    picture("serviceDay01", "Service Day", "Service Day (1).jpg", album_es="Día de servizio", date="2026-05-01"),
    picture("serviceDay02", "Service Day", "Service Day (2).jpg", machine=(), date="2026-05-01"),
]
GALLERY_NO_GROUPS = {"per_day": 20, "leave_out": [], "world": [], "archive": []}
# pictures in albums booth.photos does not name (the committee's own): file id → (album, file name, the publishers'
# line?) — a name that says magazine material as a whole word keeps the line ("1965-06-Gv-00-Cover.jpg", "La-Vina",
# "La_Vina", "Covers", "Portadas"), and so does an archive page's issue with a day of 00, anywhere in the name
# ("1965-10-00-…", "Scan of 1947-11-00.jpg"); a word with one inside it ("Recovery", "Silver", "Covered",
# "Discover"), a real day ("2026-11-08 …") or the album's name alone ("Grapevine History") never. (In GALLERY_NESTED,
# beside the usual 4 and "Historical Archives": the committee's own pictures, 19 now, stay within a day's 20 —
# per_day — so all of them play; test_a_cover… checks it.)
GALLERY_OWN_NAMES = {
    "newAlbum01": ("Grapevine History", "1965-06-Gv-00-Cover.jpg", True),
    "newAlbum02": ("Grapevine History", "Founders dinner 1965.jpg", False),
    "oldIssues01": ("Old Issues", "1951-01-Gv-00.jpg", True),
    "oldIssues02": ("Old Issues", "1999-05-La-Vina-00.jpg", True),
    "oldIssues03": ("Old Issues", "La_Vina_1998-03.jpg", True),
    "oldIssues04": ("Old Issues", "Covers 1999 (2).jpg", True),
    "oldIssues05": ("Old Issues", "Portadas 1998.jpg", True),
    "oldIssues06": ("Old Issues", "1965-10-00-I-Am-Responsible.jpg", True),
    "oldIssues07": ("Old Issues", "Scan of 1947-11-00.jpg", True),
    "serviceDay11": ("Service Day", "Recovery Walk (1).jpg", False),
    "serviceDay12": ("Service Day", "Silver Anniversary.jpg", False),
    "serviceDay13": ("Service Day", "Covered dish supper.jpg", False),
    "serviceDay14": ("Service Day", "Discover AA Day.jpg", False),
    "serviceDay15": ("Service Day", "2026-11-08 Service Day.jpg", False),
}
# phone and camera names in albums named after a magazine's event (drive.py: extra.generic_name, the title the album's
# name and a number): file id → (album, file name, the sync's title, the publishers' line?) — only the file name
# counts, never the album's name in the title ("Cover (4).jpg" says it itself)
GALLERY_CAMERA = {
    "cameraGv0001": ("Grapevine History", "IMG_1234.jpg", "Grapevine History #1", False),
    "cameraGv0002": ("Grapevine History", "PXL_20260412_153012345.jpg", "Grapevine History #2", False),
    "cameraGv0003": ("Grapevine History", "WhatsApp Image 2026-04-12 at 6.33.16 PM.jpeg", "Grapevine History #3", False),
    "cameraGv0004": ("Grapevine History", "Cover (4).jpg", "Grapevine History #4", True),
    "cameraLv0001": ("Taller de La Viña Garland", "IMG_5678.jpg", "Taller de La Viña Garland #1", False),
}
# folders inside an album (drive.py names one "Historical Archive / 1960": the folders below photos/ joined with
# " / "), an album whose name only starts like one booth.photos names, and the pictures above
GALLERY_NESTED = [
    picture("organizeSub1", "To Organize / 1950s", "1955-09-Gv-Cover-1.jpg", date="2026-07-01"),
    picture("archiveSub01", f"{ARCHIVE} / 1960", "1960-11-Gv-00-Intl-Cover-Full-0.jpg", date="2026-02-01"),
    picture("worldSub01ab", f"{WORLD} / Europe", "Belgium_Partage_1992-08.jpg", title_es="Parte correspondiente",
            date="2026-03-01"),
    picture("archivesNot1", "Historical Archives", "Scan 1.jpg", date="2026-02-01"),
    *[picture(fid, album, name, date="2026-01-01") for fid, (album, name, _line) in GALLERY_OWN_NAMES.items()],
]
# the world and archive pictures only in folders inside their albums (the committee sorted them all)
GALLERY_SORTED = [*[p for p in DRIVE_PICTURES if p["extra"]["album"] not in (WORLD, ARCHIVE)], *GALLERY_NESTED]
# booth.photos with an archive name no album has (and a leave_out one: never named — an emptied "To Organize" is its
# normal end)
GALLERY_TYPO = {"per_day": 20, "leave_out": ["To Organize", "Por organizar"], "world": [WORLD], "archive": ["Historical Archiv"]}
# the camera names above, on a drive of their own (with the usual booth.photos)
GALLERY_CAMERA_PICTURES = [picture(fid, album, name, title, date="2026-04-12", generic=True)
                           for fid, (album, name, title, _line) in GALLERY_CAMERA.items()]

GALLERY_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const db = { drive: { items: input.pictures } };
const ctx = (now) => ({ db, site: input.site, now: new Date(now), base: "/aagrapevine/" });
const gallery = (r) => ({ items: r.items.filter((i) => i.id.startsWith("live:gallery:")),
  problems: r.problems.filter((p) => p.where.startsWith("Photos page")), failed: r.problems.filter((p) => p.where === "Live items"),
  config: r.problems.filter((p) => p.where.startsWith("config/site.yml booth.photos")) });
const nested = { ...ctx(input.days[0]), db: { drive: { items: [...input.pictures, ...input.nested] } } };
const four = { ...input.cased, per_day: 4 };
const booth = (photos) => B.loadBooth({ csvText: "id,type,text_en\n", driveData: null, manifestData: null,
  config: { defaults: { photo_every: photos }, photos: { per_day: 4 } }, site: input.site, base: "/aagrapevine/" });
const show = B.boothShow(booth(12), ctx(input.days[0]));
out({
  usual: gallery(B.liveItems(ctx(input.days[0]))),
  cased: gallery(B.liveItems(ctx(input.days[0]), {}, input.cased)).items.map((i) => i.id),
  days: input.days.map((d) => {
    const items = gallery(B.liveItems(ctx(d), {}, four)).items;
    return Object.fromEntries(["gallery-gv", "gallery-lv"].map((ch) => [ch, items.filter((i) => i.channel === ch).map((i) => i.id)]));
  }),
  again: gallery(B.liveItems(ctx(input.days[0]), {}, four)).items.filter((i) => i.channel === "gallery-gv").map((i) => i.id),
  show: { defaults: show.defaults, channels: show.channels.filter((c) => c.id.startsWith("gallery-")), qr: Object.keys(show.qr),
    problems: show.problems, version: show.version, again: B.boothShow(booth(12), ctx(input.days[0])).version },
  badEvery: B.boothShow(booth("often"), ctx(input.days[0])).defaults,
  mixed: gallery(B.liveItems({ ...ctx(input.days[0]), db: { drive: { items: input.mixed } } }, {}, input.noGroups)),
  nested: gallery(B.liveItems(nested)),
  nestedCased: gallery(B.liveItems(nested, {}, input.cased)).items.map((i) => i.id),
  sorted: gallery(B.liveItems({ ...ctx(input.days[0]), db: { drive: { items: input.sorted } } })).config,
  typo: gallery(B.liveItems(ctx(input.days[0]), {}, input.typo)).config,
  typoNoAlbums: gallery(B.liveItems({ ...ctx(input.days[0]), db: { drive: { items: [] } } }, {}, input.typo)).config,
  camera: gallery(B.liveItems({ ...ctx(input.days[0]), db: { drive: { items: input.camera } } })),
});
"""

# the real data: config/site.yml's booth.photos on data/site/drive.json, every picture of every group
REAL_GALLERY_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const drive = JSON.parse(fs.readFileSync("data/site/drive.json", "utf8"));
const photos = { ...B.boothDefaults(input.booth).photos, per_day: 200 };
const r = B.liveItems({ db: { drive }, site: input.site, now: new Date(input.now), base: "/aagrapevine/" }, {}, photos);
const pic = new Map(drive.items.map((it) => [`live:gallery:${it.extra && it.extra.file_id}`, it]));
out({
  items: r.items.filter((i) => i.id.startsWith("live:gallery:")).map((i) => ({ channel: i.channel, album: pic.get(i.id).extra.album,
    name: pic.get(i.id).extra.name, title: pic.get(i.id).title, generic: !!pic.get(i.id).extra.generic_name,
    credit: [i.en.credit, i.es.credit] })),
  config: r.problems.filter((p) => p.where.startsWith("config/site.yml booth.photos")),
  failed: r.problems.filter((p) => p.where === "Live items"),
});
"""
# a picture's own name that says it is magazine material, as a whole word, or an archive page's issue with a day of
# 00 — liveGallery's MAG_WORDS, word for word (Gallery.test_the_tests_copy_of_mag_words keeps the two the same)
MAG_WORDS = re.compile(r"(^|[^a-z])(gv|grapevine|lv|la[ _-]?vi[ñn]a|covers?|portadas?)([^a-z]|$)|(^|\D)(19|20)\d\d-(0[1-9]|1[0-2])-00(\D|$)", re.I)
# today's committee photos in data/site/drive.json's "2026 Displays"
TODAYS_DISPLAYS = re.compile(r"Panel 75 Displays \(\d+\)\.jpeg|2026 Dallas Gathering Of Eagles\.jpg")
WORLD_CREDIT = ("Cover of an AA magazine from another country. © its publisher.",
                "Portada de una revista de AA de otro país. © de su editor.")


def hero_credit() -> dict:
    """The /photos/ hero's line (committee.photos.hero_credit) as a magazine slide carries it, word for word ("A.A."
    kept on the line of "World Services": a no-break space)."""
    hero = json.loads((ROOT / "src" / "_i18n" / "committee.json").read_text(encoding="utf-8"))["committee.photos.hero_credit"]
    return {lang: hero[lang].replace("A.A. World", "A.A.\u00a0World") for lang in ("en", "es")}


# the build log (eleventy/filters/booth.js logProblems, console.warn caught): /about/booth.json written by the boothJson
# filter with a `booth` global that has a problem of its own (src/_data/booth.js logs it — never again here), on the
# drive above (two pictures left out) and on none; and more than 40 problems
LOG_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const warned = [];
console.warn = (...a) => { warned.push(a.join(" ")); };
const booth = B.loadBooth({ csvText: "id,type,text_en\nbad-row,nope,Hello\n", driveData: null, manifestData: null,
  config: {}, site: input.site, base: "/aagrapevine/" });
const own = warned.splice(0);
const ctx = (items) => ({ db: { drive: { items } }, site: input.site, now: new Date(input.now), base: "/aagrapevine/" });
const show = JSON.parse(filters.boothJson(booth, ctx(input.pictures)));
const live = warned.splice(0);
filters.boothJson(booth, ctx([]));
const none = warned.splice(0);
B.logProblems(Array.from({ length: 42 }, (_, i) => ({ where: `w${i + 1}`, en: "x", es: "x" })));
out({ global: booth.problems.map((p) => p.where), file: show.problems.map((p) => p.where), own, live, none, many: warned.splice(0) });
"""

GALLERY_INPUT = {"pictures": DRIVE_PICTURES, "site": SITE_X, "cased": GALLERY_CASED, "days": GALLERY_DAYS,
                 "mixed": GALLERY_MIXED, "noGroups": GALLERY_NO_GROUPS, "nested": GALLERY_NESTED, "typo": GALLERY_TYPO,
                 "sorted": GALLERY_SORTED, "camera": GALLERY_CAMERA_PICTURES}


class Gallery(unittest.TestCase):
    """The Photos page's pictures at the booth (liveGallery, config/site.yml booth.photos): the albums /photos/ shows
    (committee.js photoAlbums) but "To Organize", in five groups — the committee's own albums, Grapevine's covers, La
    Viña's, other countries' AA magazines, the Grapevine archive's pages — each its own channel, slide type and
    captions in both languages (rule-written, never machine-translated), the publishers' line on every magazine
    slide, the group's place on /photos/ as its QR code; online only (Google's copy); a day's share of each group
    (per_day), a different block every day, so every picture comes round; booth.defaults.photo_every → the player's
    galleryEvery. A name in booth.photos takes the folders inside its album too; a world or archive name no album
    has is a problem line. test_todays_albums judges the day's data/site/drive.json (scripts/ops/gate_tests.py
    DATA_TESTS: the Code check runs it, the publish gate does not); the other tests, the code."""

    r: dict | None = None
    real_r: dict | None = None

    def setUp(self):
        node_ready(self)
        if Gallery.r is None:
            Gallery.r = run_js(self, GALLERY_JS, data=GALLERY_INPUT)
        self.items = Gallery.r["usual"]["items"]
        self.by = {it["id"].split(":")[-1]: it for it in self.items}

    def group(self, channel: str) -> list[dict]:
        return [it for it in self.items if it["channel"] == channel]

    def test_the_groups_and_what_never_plays(self):
        self.assertEqual(self.r["usual"]["failed"], [], "the part never fails")
        # the groups in the settings' order, each picture once
        chans = [it["channel"] for it in self.items]
        self.assertEqual(sorted(set(chans), key=GALLERY.index), GALLERY)
        self.assertEqual(chans, sorted(chans, key=GALLERY.index), "the groups one after the other, in their order")
        self.assertEqual(len(self.by), len(self.items))
        for gone in ("organize0001", "organize0002", "tableVideo01", "tableGone001", "tableSlide01", "tableDonate1",
                     "gvCover202306"):
            self.assertNotIn(gone, self.by, "To Organize, a video, a file gone, a document, a refused word")
        self.assertEqual(sorted(it["id"] for it in self.group("gallery-ours")),
                         ["live:gallery:boothPhoto01", "live:gallery:tableDisplay1", "live:gallery:tableDisplay2",
                          "live:gallery:tableDisplay3"])
        self.assertEqual(len(self.group("gallery-world")), 8)
        self.assertEqual(len(self.group("gallery-archive")), 3)
        self.assertEqual(len(self.group("gallery-lv")), 3)
        self.assertEqual(len(self.group("gallery-gv")), 20, "a day's 20 of the 25 Grapevine covers")
        # the album names match the Drive folder's, capitals ignored
        self.assertEqual(self.r["cased"], [it["id"] for it in self.items])

    def test_every_item_and_its_picture(self):
        kinds = {"gallery-ours": ("photo", "cover", "=s1920", "both"), "gallery-gv": ("poster", "contain", "=s1600", "gv"),
                 "gallery-lv": ("poster", "contain", "=s1600", "lv"), "gallery-world": ("poster", "contain", "=s1600", "both"),
                 "gallery-archive": ("poster", "contain", "=s1600", "gv")}
        for it in self.items:
            with self.subTest(id=it["id"]):
                fid = it["id"].split(":")[-1]
                self.assertTrue(it["id"].startswith("live:gallery:"))
                self.assertEqual(list(it), ITEM)
                self.assertEqual(list(it["media"]), MEDIA)
                for lang in ("en", "es"):
                    self.assertEqual(list(it[lang]), BLOCK)
                    self.assertTrue(it[lang]["title"], "a caption in both languages: the credit line shows inside it")
                t, fit, size, pub = kinds[it["channel"]]
                self.assertEqual((it["source"], it["type"], it["pub"], it["langs"], it["tags"], it["first"], it["weight"],
                                  it["seconds"], it["collection"]), ("live", t, pub, [], [], False, 1, None, "live"))
                self.assertEqual((it["media"]["kind"], it["media"]["src"], it["media"]["fit"], it["media"]["local"], it["online"]),
                                 ("image", f"https://lh3.googleusercontent.com/d/{fid}{size}", fit, False, True))

    def test_the_captions(self):
        cap = lambda fid: (self.by[fid]["en"]["title"], self.by[fid]["es"]["title"])  # noqa: E731
        # the committee's albums: the album's name — its Spanish one only when a person wrote it
        self.assertEqual(cap("tableDisplay1"), ("Table Displays", "Table Displays"))
        self.assertEqual(cap("boothPhoto01"), ("Booth Photos", "Fotos de la mesa"))
        # the covers: their own rule-written titles (committee.js photoAlbums lbTitle)
        self.assertEqual(cap("gvCover202601"), ("Grapevine — January 2026", "Grapevine — Enero 2026"))
        self.assertEqual(cap("lvCover20256"), ("La Viña — November–December 2025", "La Viña — Noviembre–Diciembre 2025"))
        # old Grapevine pages: the issue their name starts with; without one, the Drive title in both
        self.assertEqual(cap("archive0001"), ("Grapevine · October 1951", "Grapevine · Octubre 1951"))
        self.assertEqual(cap("archive0002"), ("Grapevine · April 1948", "Grapevine · Abril 1948"))
        self.assertEqual(cap("archive0003"), ("Gv-Poster-Undated", "Gv-Poster-Undated"))
        # other countries' magazines: "Country_Magazine_Date" → magazine · country · date (the magazine never
        # translated, the country in Spanish when the table knows it)
        want = {
            "world00abc": ("Partage · Belgium · August 1992", "Partage · Bélgica · agosto de 1992"),
            "world01abc": ("El Triangulo · Uruguay · January–February 1997", "El Triangulo · Uruguay · enero–febrero de 1997"),
            "world02abc": ("Plenitud AA · Mexico · 20th Anniversary", "Plenitud AA · México · 20th Anniversary"),
            "world03abc": ("Bulletinen · Sweden", "Bulletinen · Suecia"),
            "world04abc": ("Az Buki · Russia · 1998, No. 2", "Az Buki · Rusia · 1998, n.º 2"),
            "world05abc": ("Antenna · Australia · Spring 1991", "Antenna · Australia · primavera de 1991"),
            "world06abc": ("Box 12 · Atlantis · April 1993", "Box 12 · Atlantis · abril de 1993"),
            "world07abc": ("Scan0001", "Scan0001"),
        }
        self.assertEqual({k: cap(k) for k in want}, want)
        words = json.dumps(self.items, ensure_ascii=False)
        for machine in ("Parte correspondiente", "Pantallas de mesa", "Panel 75 pantallas", "International-Equivallent"):
            self.assertNotIn(machine, words, "never a machine-made Spanish title")

    def test_an_album_partly_machine_translated(self):
        # (booth.photos.world names no album: the magazines' one is the committee's own then) one machine-translated
        # picture is enough for the Drive folder's name, whichever picture the album's name came from
        m = self.r["mixed"]
        self.assertEqual((m["failed"], m["problems"]), ([], []))
        got = {it["id"].split(":")[-1]: (it["channel"], it["en"]["title"], it["es"]["title"]) for it in m["items"]}
        want = {p["extra"]["file_id"]: ("gallery-ours", WORLD, WORLD) for p in GALLERY_MIXED if p["extra"]["album"] == WORLD}
        want.update({"serviceDay01": ("gallery-ours", "Service Day", "Service Day"),
                     "serviceDay02": ("gallery-ours", "Service Day", "Service Day")})
        self.assertEqual(got, want)
        words = json.dumps(m["items"], ensure_ascii=False)
        for machine in ("International-Equivallent", "Día de servizio", "Parte correspondiente"):
            self.assertNotIn(machine, words, "never a machine-made Spanish title")

    def test_the_credit_lines(self):
        nb = hero_credit()
        self.assertIn("A.A.\u00a0World", nb["en"])
        for it in self.items:
            with self.subTest(id=it["id"]):
                credit = (it["en"]["credit"], it["es"]["credit"])
                if it["channel"] == "gallery-ours":
                    self.assertEqual(credit, (None, None))
                elif it["channel"] == "gallery-world":
                    self.assertEqual(credit, WORLD_CREDIT)
                else:
                    self.assertEqual(credit, (nb["en"], nb["es"]))

    def test_the_folders_inside_an_album(self):
        # a name in booth.photos takes the folders inside that album too ("Historical Archive / 1960"): the staging
        # folder's never play, the archive's and the world album's play as theirs, with their captions and credit
        # lines; an album whose name only starts like one ("Historical Archives") is another album
        n = self.r["nested"]
        self.assertEqual((n["failed"], n["problems"], n["config"]), ([], self.r["usual"]["problems"], []))
        by = {it["id"].split(":")[-1]: it for it in n["items"]}
        self.assertNotIn("organizeSub1", by, "To Organize / 1950s: never at the booth")
        nb = hero_credit()
        got = {fid: (by[fid]["channel"], by[fid]["type"], by[fid]["media"]["fit"], by[fid]["en"]["title"], by[fid]["es"]["title"],
                     (by[fid]["en"]["credit"], by[fid]["es"]["credit"])) for fid in ("archiveSub01", "worldSub01ab", "archivesNot1")}
        self.assertEqual(got, {
            "archiveSub01": ("gallery-archive", "poster", "contain", "Grapevine · November 1960", "Grapevine · Noviembre 1960",
                             (nb["en"], nb["es"])),
            "worldSub01ab": ("gallery-world", "poster", "contain", "Partage · Belgium · August 1992",
                             "Partage · Bélgica · agosto de 1992", WORLD_CREDIT),
            "archivesNot1": ("gallery-ours", "photo", "cover", "Historical Archives", "Historical Archives", (None, None)),
        })
        # every other picture as without them; capitals ignored, as for an album's own name
        nested = {p["extra"]["file_id"] for p in GALLERY_NESTED}
        self.assertEqual([it for it in n["items"] if it["id"].split(":")[-1] not in nested], self.items)
        self.assertEqual(self.r["nestedCased"], [it["id"] for it in n["items"]])

    def test_a_cover_in_an_album_booth_photos_does_not_name(self):
        # an album booth.photos does not name is the committee's own (no credit line), but a picture whose own name
        # says it is magazine material as a whole word (GV, Grapevine, LV, La Viña — "La-Vina", "La_Vina" too —,
        # cover(s), portada(s)) or holds, anywhere in it, an issue written the archive's way, with a day of 00
        # ("1965-10-00-I-Am-Responsible.jpg", "Scan of 1947-11-00.jpg"), keeps the publishers' line: never for a word
        # with one inside it ("Recovery Walk", "Silver Anniversary", "Covered dish", "Discover AA Day"), a real day
        # ("2026-11-08 Service Day.jpg"), nor for the album's name alone ("Grapevine History")
        by = {it["id"].split(":")[-1]: it for it in self.r["nested"]["items"]}
        self.assertLessEqual(set(GALLERY_OWN_NAMES), set(by), "all of them in the day's set (a day's 20)")
        nb = hero_credit()
        got = {fid: (by[fid]["channel"], by[fid]["en"]["title"], by[fid]["es"]["title"], by[fid]["en"]["credit"],
                     by[fid]["es"]["credit"]) for fid in GALLERY_OWN_NAMES}
        want = {fid: ("gallery-ours", album, album, *((nb["en"], nb["es"]) if line else (None, None)))
                for fid, (album, _name, line) in GALLERY_OWN_NAMES.items()}
        self.assertEqual(got, want)
        # (the review's case: a Grapevine cover from "To Organize" filed in a new album, in both languages)
        self.assertEqual(got["newAlbum01"], ("gallery-ours", "Grapevine History", "Grapevine History", nb["en"], nb["es"]))

    def test_a_phone_photo_in_an_album_named_after_a_magazine(self):
        # a phone or camera name ("IMG_1234.jpg", "WhatsApp Image …": drive.py's extra.generic_name) has the album's
        # name and a number as its title ("Grapevine History #1"): only its file name counts, so the committee's own
        # photos of a Grapevine or La Viña event play without the publishers' line — and "Cover (4).jpg" keeps it
        c = self.r["camera"]
        self.assertEqual((c["failed"], c["problems"]), ([], []))
        by = {it["id"].split(":")[-1]: it for it in c["items"]}
        nb = hero_credit()
        got = {fid: (it["channel"], it["en"]["title"], it["en"]["credit"], it["es"]["credit"]) for fid, it in by.items()}
        want = {fid: ("gallery-ours", album, *((nb["en"], nb["es"]) if line else (None, None)))
                for fid, (album, _name, _title, line) in GALLERY_CAMERA.items()}
        self.assertEqual(got, want)

    def test_the_tests_copy_of_mag_words(self):
        # the real photos' check below judges the code by this file's MAG_WORDS: it is eleventy/filters/booth.js's own
        src = (ROOT / "eleventy" / "filters" / "booth.js").read_text(encoding="utf-8")
        found = re.findall(r"^const MAG_WORDS = /(.+)/([a-z]*);$", src, re.M)
        self.assertEqual(found, [(MAG_WORDS.pattern, "i")], "booth.js: const MAG_WORDS = /…/i; — the same pattern")
        self.assertTrue(MAG_WORDS.flags & re.I)

    def test_an_album_name_no_album_has(self):
        # booth.photos.archive "Historical Archiv" (a typo: only the start of "Historical Archive"): one problem line,
        # so the archive's pages never play as the committee's own unnoticed; never for a leave_out name (an emptied
        # "To Organize" is its normal end), nor for a drive with no album at all (a failed sync)
        self.assertEqual(self.r["typo"], [{
            "where": "config/site.yml booth.photos.archive",
            "en": 'no album of the Photos page is called "Historical Archiv": check the Drive folder\'s name',
            "es": 'ningún álbum de la página de fotos se llama "Historical Archiv": revisa el nombre de la carpeta de Drive'}])
        self.assertEqual(self.r["typoNoAlbums"], [])
        # the usual names: none (their albums, and the folders inside them — also when the world and archive pictures
        # are only in such folders)
        self.assertEqual((self.r["usual"]["config"], self.r["nested"]["config"], self.r["sorted"]), ([], [], []))

    def real(self) -> dict:
        """data/site/drive.json with config/site.yml's booth.photos, every picture (per_day 200) — run once."""
        if Gallery.real_r is None:
            Gallery.real_r = run_js(self, REAL_GALLERY_JS, data={"booth": SITE.get("booth"), "site": SITE_X, "now": NOW})
        return Gallery.real_r

    def test_the_credit_lines_of_the_real_photos(self):
        # the code on the day's data, whatever it holds: every magazine slide its line, and the committee's own
        # photos one only when their own name says magazine material (a phone or camera name: its file name alone —
        # its title is the album's name, which never counts)
        r = self.real()
        self.assertEqual(r["failed"], [])
        nb = hero_credit()
        for it in r["items"]:
            with self.subTest(album=it["album"], name=it["name"]):
                if it["channel"] == "gallery-world":
                    self.assertEqual(tuple(it["credit"]), WORLD_CREDIT)
                elif it["channel"] != "gallery-ours" or MAG_WORDS.search(it["name"] if it["generic"] else f"{it['name']} {it['title']}"):
                    self.assertEqual(it["credit"], [nb["en"], nb["es"]])
                else:
                    self.assertEqual(it["credit"], [None, None])

    def test_todays_albums(self):
        """The day's data (DATA_TESTS: the Code check runs it, the publish gate does not): a renamed Drive folder alone
        can change this answer; test_the_credit_lines_of_the_real_photos tests the code on it, and the tests above
        on data of their own."""
        # every world and archive name of config/site.yml has its album in data/site/drive.json, and today's
        # committee photos ("2026 Displays": "Panel 75 Displays (12).jpeg" …) are there with no credit line
        r = self.real()
        self.assertEqual(r["config"], [], "config/site.yml booth.photos: a name no album of data/site/drive.json has")
        displays = [it for it in r["items"] if it["channel"] == "gallery-ours" and it["album"] == "2026 Displays"
                    and TODAYS_DISPLAYS.fullmatch(it["name"])]
        self.assertTrue(displays, "today's committee photos")
        self.assertEqual({tuple(it["credit"]) for it in displays}, {(None, None)})

    def test_the_qr_codes(self):
        page = {"gallery-gv": "photos/#covers-gv", "gallery-lv": "photos/#covers-lv",
                "gallery-world": "photos/#album-international-equivalent", "gallery-archive": "photos/#album-historical-archive"}
        for it in self.items:
            with self.subTest(id=it["id"]):
                p = page.get(it["channel"]) or ("photos/#album-booth-photos" if it["id"].endswith("boothPhoto01")
                                                else "photos/#album-table-displays")
                self.assertEqual((it["qr"], it["qr_es"], it["url"]), (BASE_URL + p, BASE_URL + "es/" + p, BASE_URL + p))
        # few addresses, few codes in the file: one pair per group (and per own album)
        qr = self.r["show"]["qr"]
        self.assertEqual(len([u for u in qr if "/photos/#" in u]), 2 * 6)
        self.assertEqual(qr[-2:], [BASE_URL, BASE_URL + "es/"])

    def test_a_refused_word_is_left_out_and_named(self):
        self.assertEqual(self.r["usual"]["problems"], [
            {"where": "Photos page: Table Displays/Donation jar.jpg", "en": "left out of the booth: it says “Donation”",
             "es": "queda fuera de la pantalla: dice “Donation”"},
            {"where": "Photos page: Grapevine covers 2023/GV_2023-06_June-PDF-scan.jpg", "en": "left out of the booth: it says “PDF”",
             "es": "queda fuera de la pantalla: dice “PDF”"},
        ])

    def test_the_build_log_names_the_live_problems(self):
        # the day's live items' problems (a picture left out, a booth.photos name no album has …) reach the build log
        # as the owner's files' do, when /about/booth.json is written — not only the player's Settings → Slides; the
        # `booth` global's own are in the file too, but logged once, by src/_data/booth.js (loadBooth logs nothing)
        r = run_js(self, LOG_JS, data={"pictures": DRIVE_PICTURES, "site": SITE_X, "now": NOW})
        self.assertEqual(len(r["global"]), 1, r["global"])
        self.assertEqual(r["file"], [*r["global"], "Photos page: Table Displays/Donation jar.jpg",
                                     "Photos page: Grapevine covers 2023/GV_2023-06_June-PDF-scan.jpg"])
        self.assertEqual(r["own"], [])
        self.assertEqual(r["live"], [
            "[booth] 2 problem(s) of the day's live items — left out of the booth display:\n"
            "  Photos page: Table Displays/Donation jar.jpg: left out of the booth: it says “Donation”\n"
            "  Photos page: Grapevine covers 2023/GV_2023-06_June-PDF-scan.jpg: left out of the booth: it says “PDF”"])
        self.assertEqual(r["none"], [], "no live problem: no line")
        # the first 40, and where the rest are
        many = r["many"][0].split("\n")
        self.assertEqual((len(r["many"]), many[0], many[1], many[40], many[41:]),
                         (1, "[booth] 42 problem(s) — left out of the booth display:", "  w1: x", "  w40: x",
                          ["  … and 2 more (Settings → Slides in the player lists them all)"]))

    def test_a_days_share_and_every_picture_comes_round(self):
        days = [d["gallery-gv"] for d in self.r["days"]]
        ids = [f"live:gallery:{c['extra']['file_id']}" for c in GV_COVERS]
        ring = sorted(ids, key=lambda i: hashlib.sha1(f"gallery:{i}".encode()).hexdigest())
        for d, got in enumerate(days):
            n = (datetime.date(2099, 10, 15 + d) - datetime.date(1970, 1, 1)).days
            with self.subTest(day=d):
                # day n: the n-th block of 4 of the stable order (wrapping), shown in the /photos/ order (newest first)
                self.assertEqual(len(got), 4)
                self.assertEqual(set(got), {ring[(n * 4 + j) % len(ring)] for j in range(4)})
                self.assertEqual(got, [i for i in ids[::-1] if i in got])
                if d:
                    self.assertFalse(set(got) & set(days[d - 1]), "two days in a row: different pictures")
        self.assertEqual(set().union(*map(set, days)), set(ids), "seven days of 4: all 25 come round (the refused one never)")
        self.assertEqual(self.r["again"], days[0], "the same day gives the same set")
        # a group with no more than a day's share (La Viña's 3) shows them all, every day
        lv = [d["gallery-lv"] for d in self.r["days"]]
        self.assertEqual(lv, [["live:gallery:lvCover20261", "live:gallery:lvCover20256", "live:gallery:lvCover20255"]] * len(lv))

    def test_in_the_show(self):
        s = self.r["show"]
        self.assertEqual(s["defaults"], {"event": {"en": "", "es": ""}, "lang": "both", "sound": False, "galleryEvery": 12},
                         "booth.defaults.photo_every → the player's galleryEvery")
        self.assertEqual(self.r["badEvery"]["galleryEvery"], 8)
        self.assertEqual(s["channels"], [{"id": "gallery-ours", "count": 4}, {"id": "gallery-gv", "count": 4},
                                         {"id": "gallery-lv", "count": 3}, {"id": "gallery-world", "count": 4},
                                         {"id": "gallery-archive", "count": 3}], "booth.photos.per_day from the booth's config")
        self.assertIn("Photos page: Table Displays/Donation jar.jpg", [p["where"] for p in s["problems"]])
        self.assertEqual(s["version"], s["again"], "the same day, the same show")

    def test_no_gallery_in_an_empty_preview(self):
        # COMMITTEE_EMPTY=1 (the empty-page preview of the committee's pages: /photos/ has no album then)
        r = run_js(self, GALLERY_JS, data={**GALLERY_INPUT, "days": GALLERY_DAYS[:1]}, env={"COMMITTEE_EMPTY": "1"})
        self.assertEqual((r["usual"]["items"], r["usual"]["problems"], r["usual"]["failed"], r["usual"]["config"]), ([], [], [], []))
        self.assertEqual(r["typo"], [], "a preview: no album name is checked")


def defaults_as_read(d) -> dict:
    """config/site.yml booth.defaults → the player's settings, by boothDefaults' rules (its own test,
    Show.test_the_starting_settings, takes them one by one): an event's name is a one-line text of at most 80
    characters (a list or a yes/no: none); the language one of en, es, both, alternate (else both); the sound on for
    a yes; photo_every a whole number from 4 to 30, or a text of one (else 8)."""
    d = d if isinstance(d, dict) else {}
    blank = lambda v: v is None or v == ""  # noqa: E731
    line = lambda v: " ".join(str(v).split())  # noqa: E731

    def name(k):
        v = d.get(k)
        return "" if blank(v) or isinstance(v, (dict, list, bool)) else line(v)[:80].strip()

    lang = "both" if blank(d.get("language")) else line(d["language"]).lower()
    sound = not blank(d.get("sound")) and line(d["sound"]).lower() in ("true", "yes", "y", "on", "1", "si", "sí")
    pe = d.get("photo_every")
    n = (int(pe) if isinstance(pe, (int, float)) and not isinstance(pe, bool) and float(pe).is_integer()
         else int(pe) if isinstance(pe, str) and re.fullmatch(r"\s*[0-9]+\s*", pe) else None)
    return {"event": {"en": name("event_name"), "es": name("event_name_es")},
            "lang": lang if lang in ("en", "es", "both", "alternate") else "both", "sound": sound,
            "galleryEvery": n if n is not None and 4 <= n <= 30 else 8}


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
        # config/site.yml booth.defaults as the player's settings (whatever the committee set there: the gate runs this
        # test, and an event's name or another photo_every is the committee's to choose — read the way boothDefaults
        # reads them, so an edit the build takes, "10" or a value it replaces with its default, never fails it)
        self.assertEqual(j["defaults"], defaults_as_read(SITE["booth"].get("defaults")))
        self.assertEqual(list(j["defaults"]), ["event", "lang", "sound", "galleryEvery"])
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
        # the build log names the owner's files' problems: src/_data/booth.js's block ("[booth] N problem(s) — left
        # out…", never the boothJson filter's " of the day's live items" one, which the day's data may fill too) holds
        # the CSV's line
        self.assertRegex(self.run2.stderr + self.run2.stdout,
                         r"\[booth\] \d+ problem\(s\) — left out of the booth display:\n(?:  .*\n)*?  [^\n]*"
                         + re.escape(FIX + "no-such.csv was not found: the show has no rows from it"),
                         "the build log names the owner's files' problems")


if __name__ == "__main__":
    unittest.main()
