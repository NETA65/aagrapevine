"""The booth display's logic (src/assets/js/booth-core.js, window.GVB) run in Node.js.

What a booth relies on, checked against values worked out by hand:
  * the settings       — DEFAULTS has every key of SPEC §3.6; normSettings never throws on garbage (wrong types,
                         a getter that throws), clamps every number, drops unknown keys and channels, keeps only the
                         switched-off items and hidden tags; withDefaults reads config/site.yml's names and settings
                         keys; diff gives only what differs; encode / decode round-trip (accents, emoji) within 2048
                         characters and refuse anything wrong (length, characters, stray bits, UTF-8, JSON, schema,
                         unknown keys, wrong kinds, out of range); clipEvery a whole number from 3 to 30 everywhere
                         (stored, typed, in a link, in a diff); the five presets (only "Quiz party" changes clipEvery)
  * the pool           — every reason of why() (off, channel, pub, collection, tag, date — Central days —, over,
                         lang, offline, muted, media) and their order; the auto items (welcome only with an event
                         name); a live list's past rows dropped from a copy (the show itself never changed)
  * languages          — the four modes with two-language, one-language and wordless items; "alternate" over a run
                         of slides; text() never null; fill(); qrOf() (a Spanish slide shows the item's qr_es)
  * the order          — 2000 slides with a fixed seed: the first items open the show, nothing repeats inside the
                         window, a video or a sound at most once in clipEvery slides, never the same type twice
                         (photo up to 2), at most 1 play slide in 3, a media slide at least every 4, a live list at
                         most once in 6, welcome every 12 (13 when a media slide was due), about every 30; with few
                         pictures (an offline booth, a small Drive folder): welcome / about still every 12 / 30 (a
                         media slide that cannot come yet never holds them back), the list cap still holds when the
                         media rule must give way (a rule gives way alone), and the pictures spread evenly over the
                         window instead of all at once and then none; the clips (3000 slides of a show whose only
                         media are videos and sounds, as the committed show is online): never closer than clipEvery
                         (3, 8, 12, 30), yet one as soon as it may — the media rule waits for it, never forces it —,
                         welcome / about never held back; with pictures too the media rule still holds (the pictures
                         fill it), and without clips nothing changed; "first" clips open the show anyway; "In order"
                         loops in the CSV / Drive order; boost; an empty pool; the same seed gives the same show and
                         next() never changes the state it is given
  * time               — pace, both languages, the clamps, an item's own seconds, the reveal, media caps (a web
                         video or sound: 90 s by default)
  * the rest           — scramble's properties, "Quiz me", poll votes and percentages, the offline list (every file
                         booth.json names, whatever the switches say), the day in Central time (also without Intl),
                         the module's shape and its plain-script syntax
The file runs in a vm context, as tests/test_presentations_core.py runs presentations-core.js. Skipped without
Node.js.

    python -m unittest tests.test_booth_core -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

CORE = "src/assets/js/booth-core.js"

# Instants (UTC). October 2, 2026 is a Friday; Central daylight time (UTC-5) until November 1, 2026.
NOW = "2026-10-02T15:00:00.000Z"
BASE = "/aagrapevine/"
SITE = {"url": "https://neta65.github.io/aagrapevine/", "url_es": "https://neta65.github.io/aagrapevine/es/",
        "base": BASE, "host": "neta65.github.io/aagrapevine",
        "committee_en": "NETA 65 Grapevine & La Viña Committee", "committee_es": "Comité de Grapevine y La Viña de NETA 65"}


def words(title="", text="", choices=None, answer="", explain="", credit="", rows=None):
    """One language of an ITEM (SPEC §2.4)."""
    return {"title": title, "text": text, "choices": choices or [], "answer": answer, "explain": explain,
            "credit": credit, "rows": rows or []}


def item(iid, typ, channel, en=None, es=None, **extra):
    """An ITEM as /about/booth.json has it: every key present, null when not used."""
    it = {"id": iid, "source": "csv", "type": typ, "channel": channel, "pub": "both",
          "langs": [lang for lang, t in (("en", en), ("es", es)) if t is not None], "en": en, "es": es,
          "correct": None, "seconds": None, "reveal": None, "weight": 1, "from": None, "until": None, "tags": [],
          "collection": "csv", "first": False, "order": None, "media": None, "online": False, "qr": None,
          "qr_es": None, "url": None, "until_ts": None}
    it.update(extra)
    return it


def media(kind, src="", **extra):
    m = {"kind": kind, "src": src, "id": None, "short": False, "local": False, "poster": None, "start": 0,
         "end": None, "muted": False, "fit": "cover", "w": None, "h": None, "bytes": None}
    m.update(extra)
    return m


def local(name, kind="image", **extra):
    """A Drive file the build downloaded (src under /about/booth/media/)."""
    return media(kind, BASE + "about/booth/media/" + name, local=True, **extra)


def drive(fid, typ, channel, title, langs, **extra):
    """A Drive booth file: its caption in the language(s) of its name (a wordless one: English words, langs [])."""
    en = words(title) if not langs or "en" in langs else None
    es = words(title) if "es" in langs else None
    base = {"source": "drive", "collection": "main", "langs": list(langs)}
    base.update(extra)
    return item("drive:" + fid, typ, channel, en, es, **base)


def ms(iso):
    from datetime import datetime
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def sample_show():
    """A realistic show: every render type, one- and two-language rows, Drive files, live items."""
    past, soon, later = ms("2026-10-01T23:00:00.000Z"), ms("2026-10-10T23:00:00.000Z"), ms("2026-11-14T23:00:00.000Z")
    yt = lambda vid, **kw: media("youtube", "https://www.youtube.com/watch?v=" + vid, id=vid, **kw)  # noqa: E731
    items = [
        # ---- the CSV (content/booth/booth.csv)
        item("quiz-first-issue", "quiz", "quiz",
             words(text="When did the first issue of the Grapevine come out?", choices=["1938", "June 1944", "1955", "1975"],
                   explain="The first issue was eight pages, sent to members who had gone to war.", credit="Source: aagrapevine.org"),
             words(text="¿Cuándo salió el primer número del Grapevine?", choices=["1938", "Junio de 1944", "1955", "1975"],
                   explain="El primer número tenía ocho páginas.", credit="Fuente: aagrapevine.org"),
             correct=1, tags=["history"]),
        item("quiz-la-vina-year", "quiz", "quiz",
             words(text="In what year did La Viña begin?", choices=["1985", "1990", "1996"], explain="La Viña began in 1996."),
             words(text="¿En qué año comenzó La Viña?", choices=["1985", "1990", "1996"], explain="La Viña comenzó en 1996."),
             correct=2, pub="lv", tags=["history"]),
        item("quiz-gvr", "quiz", "quiz",
             words(text="Who carries the Grapevine's message in a home group?", choices=["The GVR", "The treasurer"], explain="The Grapevine Representative."),
             words(text="¿Quién lleva el mensaje de La Viña en el grupo base?", choices=["El RLV", "El tesorero"], explain="El Representante de La Viña."),
             correct=0, tags=["service", "gvr"]),
        item("quiz-app", "quiz", "quiz",
             words(text="Where can you read the Grapevine on a phone?", choices=["Nowhere", "The Grapevine app"], explain="The app has the magazine."),
             correct=1, tags=["app"]),
        item("quiz-es-only", "quiz", "quiz", None,
             words(text="¿Cada cuánto sale La Viña?", choices=["Cada dos meses", "Cada semana"], explain="Seis números al año."),
             correct=0, pub="lv", tags=["rlv"]),
        item("quiz-podcast", "quiz", "quiz",
             words(text="What is the Grapevine's podcast called?", choices=["Bill's Story", "AA Grapevine's Podcast", "Meeting Talk", "Big Book"], explain="It has stories read aloud."),
             words(text="¿Cómo se llama el pódcast del Grapevine?", choices=["La historia de Bill", "AA Grapevine's Podcast", "Charla", "El Libro Grande"], explain="Tiene historias leídas en voz alta."),
             correct=1, reveal=20, tags=["podcast"]),
        item("tf-journal", "truefalse", "quiz",
             words(text="The Grapevine is the international journal of Alcoholics Anonymous.", explain="That is how it describes itself."),
             words(text="La Viña es la revista hispana de Alcohólicos Anónimos.", explain="Así se describe."), correct=True),
        item("tf-ads", "truefalse", "quiz",
             words(text="The Grapevine carries paid advertising.", explain="It carries no outside advertising."),
             words(text="La Viña publica anuncios pagados.", explain="No publica anuncios de fuera."), correct=False),
        item("tf-stories", "truefalse", "quiz",
             words(text="Most Grapevine stories are written by AA members.", explain="Members write in."),
             words(text="La mayoría de las historias de La Viña las escriben miembros de AA.", explain="Los miembros escriben."), correct=True),
        item("fill-meeting", "fill", "puzzles",
             words(text="The Grapevine is often called our ___.", answer="meeting in print", explain="A meeting you can take anywhere."),
             words(text="A La Viña se le llama nuestra ___.", answer="reunión impresa", explain="Una reunión que puedes llevar a todas partes.")),
        item("fill-carry", "fill", "puzzles",
             words(text="A gift subscription for someone else is called ___.", answer="Carry the Message", explain="It goes to someone who may need it."),
             words(text="Una suscripción de regalo para otra persona se llama ___.", answer="Lleva el Mensaje", explain="Va a alguien que la necesite.")),
        item("scramble-vine", "scramble", "puzzles", words(text="Unscramble the magazine's name", answer="GRAPEVINE"),
             words(text="Ordena el nombre de la revista", answer="LA VIÑA")),
        item("scramble-story", "scramble", "puzzles", words(text="Unscramble what members send", answer="STORY"),
             words(text="Ordena lo que mandan los miembros", answer="HISTORIA")),
        item("fact-1944", "fact", "facts", words(text="The Grapevine was first published in June 1944.", credit="Source: aagrapevine.org"),
             words(text="El Grapevine se publicó por primera vez en junio de 1944.", credit="Fuente: aagrapevine.org"), tags=["history"]),
        item("fact-languages", "fact", "facts", words(text="La Viña is written in Spanish for Spanish-speaking members."),
             words(text="La Viña se escribe en español para los miembros de habla hispana.")),
        item("fact-writers", "fact", "facts", words(text="Every story in the magazine comes from a member who chose to write it down.")),
        item("history-1944", "history", "facts", words(title="June 1944", text="Six members in New York put out the first issue."),
             words(title="Junio de 1944", text="Seis miembros en Nueva York sacaron el primer número."), tags=["history"]),
        item("history-1996", "history", "facts", words(title="1996", text="La Viña's first issue comes out."),
             words(title="1996", text="Sale el primer número de La Viña."), pub="lv", tags=["history"]),
        item("quote-preamble", "quote", "quotes",
             words(text="Alcoholics Anonymous is a fellowship of people who share their experience, strength and hope with each other.",
                   credit="Copyright © by AA Grapevine, Inc.; reprinted with permission."),
             words(text="Alcohólicos Anónimos es una comunidad de personas que comparten su mutua experiencia, fortaleza y esperanza.",
                   credit="Copyright © AA Grapevine, Inc.; reimpreso con permiso.")),
        item("quote-responsibility", "quote", "quotes",
             words(text="I am responsible. When anyone, anywhere, reaches out for help, I want the hand of A.A. always to be there.",
                   credit="The Responsibility Statement"),
             words(text="Yo soy responsable. Cuando cualquiera, dondequiera, extienda su mano pidiendo ayuda, quiero que la mano de A.A. siempre esté allí.",
                   credit="Declaración de la Responsabilidad")),
        item("poll-format", "poll", "polls", words(text="How do you like to read it?", choices=["Print", "App", "Audio"]),
             words(text="¿Cómo te gusta leerla?", choices=["Impresa", "App", "Audio"])),
        item("poll-story", "poll", "polls", words(text="Have you ever written a story?", choices=["Yes", "Not yet"]),
             words(text="¿Alguna vez has escrito una historia?", choices=["Sí", "Todavía no"])),
        item("prompt-first", "prompt", "prompts", words(text="What was the first story you read that stayed with you?"),
             words(text="¿Cuál fue la primera historia que leíste y que se quedó contigo?")),
        item("prompt-share", "prompt", "prompts", words(text="Who could you share a copy with this month?"),
             words(text="¿Con quién podrías compartir un ejemplar este mes?")),
        item("message-subs", "message", "messages", words(title="Ask us about subscriptions", text="Print, digital and the app — ask us at the table."),
             words(title="Pregúntanos por las suscripciones", text="Impresa, digital y la app — pregúntanos en la mesa."),
             qr="https://neta65.github.io/aagrapevine/shop/"),
        item("message-event", "message", "messages", words(title="Thank you", text="Thank you for visiting our table at {event}."),
             words(title="Gracias", text="Gracias por visitar nuestra mesa en {event}.")),
        item("qr-site", "qr", "qr", words(title="Take it home", text="Our committee's website"),
             words(title="Llévatelo", text="La página de nuestro comité"), qr=SITE["url"]),
        item("video-gv-yt", "video", "web-video", words(title="Why I write"), media=yt("dQw4w9WgXcQ", end=95), online=True, pub="gv"),
        item("video-lv-short", "video", "web-video", None, words(title="La Viña en un minuto"), media=yt("abcdEFGhij0", short=True),
             online=True, pub="lv"),
        item("audio-web", "audio", "web-audio", words(title="A story read aloud"),
             media=media("audio", "https://www.aagrapevine.org/sites/default/files/story.mp3"), online=True),
        item("image-web", "image", "web-image", words(title="Carry the Message", text="A gift subscription for someone who may need it."),
             words(title="Lleva el Mensaje", text="Una suscripción de regalo para alguien que la necesite."),
             media=media("image", "https://www.aagrapevine.org/sites/default/files/carry.jpg", fit="contain"), online=True),
        # ---- the Drive booth folder
        drive("p1", "poster", "posters", "Welcome to our table", ["en"], pub="gv", first=True, seconds=15,
              media=local("aa11-welcome.png", fit="contain", w=1920, h=1080)),
        drive("p2", "poster", "posters", "Our table at the Spring Assembly", [], weight=3, order=2,
              media=local("bb22-table.png", fit="contain")),
        drive("p3", "poster", "posters", "Grapevine and La Viña - ways to carry the message", [],
              media=local("cc33-ways.png", fit="contain")),
        drive("f1", "photo", "photos", "Our booth at CityWide Dallas", [], order=1, media=local("dd44-booth.jpg")),
        drive("f2", "photo", "photos", "", [], media=local("ee55-img.jpg")),
        drive("f3", "photo", "photos", "Taller de escritura en Tyler", ["es"], pub="lv", until="2026-10-26",
              media=local("ff66-taller.jpg")),
        drive("f4", "photo", "photos", "Book display", ["en"], pub="gv", collection="spring-assembly-2027",
              media=local("gg77-books.jpg")),
        drive("f5", "photo", "photos", "Esto ES La Viña", [], media=local("hh88-esto.jpg")),
        drive("f6", "photo", "photos", "Literature table", [], online=True,
              media=media("image", "https://lh3.googleusercontent.com/d/f6=s1920")),
        drive("v1", "video", "videos", "Testimonio - Mi primer número", ["es"], pub="lv",
              media=local("ii99-testimonio.mp4", kind="video", start=5, end=105, poster=BASE + "about/booth/media/ii99-poster.jpg")),
        drive("v2", "video", "videos", "Bienvenidos - Welcome", ["en", "es"], first=True,
              media=local("jj00-bienvenidos.mp4", kind="video")),
        drive("a1", "audio", "sounds", "Podcast teaser", ["en"], pub="gv", media=local("kk11-teaser.mp3", kind="audio", start=30)),
        drive("m1", "message", "notes", "Welcome message", ["en"], pub="gv"),
        # ---- live items (made by the build from the site's data)
        item("live:events:upcoming", "events", "live-events",
             words(title="Coming up", rows=[{"title": "CityWide booth", "when": "Oct 1", "place": "Dallas", "note": "", "ends_ts": past, "pub": "both", "thumb": None},
                                            {"title": "Writing workshop", "when": "Oct 10", "place": "Tyler", "note": "", "ends_ts": soon, "pub": "lv", "thumb": BASE + "assets/cache/flyers/taller.jpg"},
                                            {"title": "Fall Assembly", "when": "Nov 14", "place": "Waco", "note": "", "ends_ts": later, "pub": "both", "thumb": None}]),
             words(title="Próximamente", rows=[{"title": "Mesa en CityWide", "when": "1 oct", "place": "Dallas", "note": "", "ends_ts": past, "pub": "both", "thumb": None},
                                               {"title": "Taller de escritura", "when": "10 oct", "place": "Tyler", "note": "", "ends_ts": soon, "pub": "lv", "thumb": BASE + "assets/cache/flyers/taller.jpg"},
                                               {"title": "Asamblea de Otoño", "when": "14 nov", "place": "Waco", "note": "", "ends_ts": later, "pub": "both", "thumb": None}]),
             source="live", collection="live"),
        item("live:countdown:assembly", "countdown", "live-events", words(title="Fall Assembly", text="Waco"),
             words(title="Asamblea de Otoño", text="Waco"), source="live", collection="live", until_ts=later),
        item("live:quote:gv", "quote", "live-quote", words(title="Grapevine Daily Quote · Oct 2", text="A thought for the day, as the Home page shows it."),
             None, source="live", collection="live", pub="gv", qr="https://www.aagrapevine.org/"),
        item("live:quote:lv", "quote", "live-quote", None, words(title="Cita Diaria de La Viña · 2 de octubre", text="Un pensamiento para hoy."),
             source="live", collection="live", pub="lv", qr="https://www.aalavina.org/"),
        item("live:video:abc123", "video", "live-video", words(title="Grapevine short"), media=yt("abc123abc12", short=True),
             source="live", collection="live", pub="gv", online=True),
        item("live:video:def456", "video", "live-video", None, words(title="Video de La Viña"), media=yt("def456def45"),
             source="live", collection="live", pub="lv", online=True),
        item("live:podcast:ep1", "audio", "live-podcast", words(title="AA Grapevine's Podcast — Episode 1"),
             media=media("audio", "https://episodes.captivate.fm/episode/ep1.mp3", poster=BASE + "assets/cache/podcast/ep1.jpg"),
             source="live", collection="live", pub="gv", online=True),
        item("live:themes:next", "themes", "live-themes",
             words(title="Write for the magazines", rows=[{"title": "Humor", "when": "Due Nov 1", "place": "", "note": "", "ends_ts": later, "pub": "gv", "thumb": None}]),
             words(title="Escribe para las revistas", rows=[{"title": "Humor", "when": "Hasta el 1 de nov", "place": "", "note": "", "ends_ts": later, "pub": "lv", "thumb": None}]),
             source="live", collection="live", qr=SITE["url"] + "contribute/"),
        item("live:prices:subs", "prices", "live-prices",
             words(title="Subscriptions", text="As of October 2, 2026", rows=[{"title": "Grapevine print, 1 year", "when": "", "place": "", "note": "$36", "ends_ts": None, "pub": "gv", "thumb": None}]),
             words(title="Suscripciones", text="Al 2 de octubre de 2026", rows=[{"title": "La Viña impresa, 1 año", "when": "", "place": "", "note": "$12", "ends_ts": None, "pub": "lv", "thumb": None}]),
             source="live", collection="live", qr=SITE["url"] + "shop/"),
        item("live:book:gv", "book", "live-book", words(title="Book of the Month", text="A collection of stories from the magazine."),
             None, source="live", collection="live", pub="gv"),
        item("live:book:lv", "book", "live-book", None, words(title="Libro del Mes", text="Una colección de historias de la revista."),
             source="live", collection="live", pub="lv"),
        item("live:meetings:next", "meetings", "live-meetings",
             words(title="Our meetings", rows=[{"title": "Committee meeting", "when": "Oct 21, 7 PM", "place": "Zoom", "note": "", "ends_ts": soon + 11 * 86400000, "pub": "both", "thumb": None}]),
             words(title="Nuestras reuniones", rows=[{"title": "Reunión del comité", "when": "21 oct, 7 PM", "place": "Zoom", "note": "", "ends_ts": soon + 11 * 86400000, "pub": "both", "thumb": None}]),
             source="live", collection="live", qr=SITE["url"] + "meetings/"),
        item("live:bulletin:post1", "message", "live-bulletin", words(title="News", text="The committee meets on the third Wednesday."),
             words(title="Noticias", text="El comité se reúne el tercer miércoles."), source="live", collection="live"),
    ]
    return {"app": "gv-booth", "schema": 1, "version": "abc123def456", "built": NOW, "as_of": "2026-10-02", "site": SITE,
            "defaults": {}, "collections": [{"id": "main", "label": "Booth folder", "count": 13},
                                            {"id": "spring-assembly-2027", "label": "Spring Assembly 2027", "count": 1}],
            "channels": [], "events_pick": [], "items": items, "qr": {}, "problems": []}


TEXT_KINDS = [("fact", "facts"), ("quote", "quotes"), ("history", "facts"), ("prompt", "prompts"),
              ("message", "messages"), ("qr", "qr")]


def text_show(n_text, photos=0, lists=False):
    """An offline booth with a small Drive folder: n_text text slides of six kinds in turns, a few local photos (and
    the three live lists when asked) — far fewer pictures than the no-repeat window holds."""
    later = ms("2026-11-14T23:00:00.000Z")
    items = []
    for i in range(n_text):
        typ, channel = TEXT_KINDS[i % len(TEXT_KINDS)]
        items.append(item(f"{typ}-{i}", typ, channel, words(f"Slide {i}", "Text"), words(f"Diapositiva {i}", "Texto"),
                          qr=SITE["url"] if typ == "qr" else None))
    for i in range(photos):
        items.append(drive(f"m{i}", "photo", "photos", f"Our table {i}", [], media=local(f"m{i}.jpg")))
    if lists:
        row = {"title": "Fall Assembly", "when": "Nov 14", "place": "Waco", "note": "", "ends_ts": later, "pub": "both", "thumb": None}
        for typ, channel in (("events", "live-events"), ("meetings", "live-meetings"), ("themes", "live-themes")):
            items.append(item(f"live:{typ}:next", typ, channel, words(typ, rows=[row]), words(typ, rows=[row]),
                              source="live", collection="live"))
    show = sample_show()
    show["items"] = items
    return show


PLAY_KINDS = [("quiz", "quiz"), ("truefalse", "quiz"), ("fill", "puzzles"), ("scramble", "puzzles"), ("poll", "polls")]


def yt(vid, **extra):
    """A YouTube video's media (the player plays it by its id)."""
    return media("youtube", "https://www.youtube.com/watch?v=" + vid, id=vid, **extra)


def clip_show(n_text, clips, photos=0, n_play=0):
    """An online booth whose media are videos and sounds, as the committed show is online (the CSV's and the
    official channels' YouTube videos and the podcast; no Drive pictures yet): n_text text slides of six kinds and
    n_play play slides of five kinds in turns, `clips` videos and sounds from every source in turns — a CSV YouTube
    video, an official channel's Short, a Drive video, a web sound, a podcast episode, a Drive sound file — and
    `photos` local photos (a Drive folder)."""
    show = text_show(n_text, photos=photos)
    items = show["items"]
    for i in range(n_play):
        typ, channel = PLAY_KINDS[i % len(PLAY_KINDS)]
        items.append(item(f"{typ}-p{i}", typ, channel, words(text=f"Question {i}", choices=["One", "Two"], answer="One"),
                          words(text=f"Pregunta {i}", choices=["Uno", "Dos"], answer="Uno"),
                          correct={"quiz": 0, "truefalse": True}.get(typ)))
    for i in range(clips):
        vid = f"clip{i:07d}"                      # 11 characters, like a YouTube id
        kind = i % 6
        if kind == 0:
            items.append(item(f"video-{i}", "video", "web-video", words(f"Video {i}"), media=yt(vid), online=True))
        elif kind == 1:
            items.append(item(f"live:video:{vid}", "video", "live-video", words(f"Short {i}"), media=yt(vid, short=True),
                              online=True, source="live", collection="live"))
        elif kind == 2:
            items.append(drive(f"v{i}", "video", "videos", f"Video {i}", [], media=local(f"v{i}.mp4", kind="video")))
        elif kind == 3:
            items.append(item(f"audio-{i}", "audio", "web-audio", words(f"Story {i}"),
                              media=media("audio", f"https://www.aagrapevine.org/files/story-{i}.mp3"), online=True))
        elif kind == 4:
            items.append(item(f"live:podcast:ep{i}", "audio", "live-podcast", words(f"Episode {i}"),
                              media=media("audio", f"https://episodes.captivate.fm/episode/ep{i}.mp3"), online=True,
                              source="live", collection="live"))
        else:
            items.append(drive(f"a{i}", "audio", "sounds", f"Sound {i}", [], media=local(f"a{i}.mp3", kind="audio")))
    return show


# Loads the core into a fresh vm context: G = window.GVB, J = the sample show, NOW = its instant, C = its ctx.
LOAD = r"""
import vm from "node:vm";
const vmctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/booth-core.js", "utf8"), vmctx, { filename: "booth-core.js" });
const G = vmctx.GVB;
const J = input.show;
const NOW = Date.parse(input.now);
const C = G.ctx({ now: NOW, online: true, page: "en" });
const plain = (v) => JSON.parse(JSON.stringify(v));
const S = (part) => G.normSettings(part || {});
const byId = (id) => J.items.find((it) => it.id === id);
// run the scheduler: n picks → [{ id, type, lang }] (+ the states when asked)
const run = (settings, n, seed, opts) => {
  const s = G.normSettings(settings || {});
  const p = (opts && opts.pool) || G.pool(J, s, C);
  let st = G.newState(seed === undefined ? 7 : seed);
  const out = [];
  for (let i = 0; i < n; i++) {
    const r = G.next(st, p, s, C);
    st = r.state;
    out.push({ id: r.item.id, type: r.item.type, lang: G.lang(r.item, s, st), langs: r.item.langs });
  }
  return { picks: out, pool: p.map((it) => it.id), state: st };
};
"""


def core(case: unittest.TestCase, js: str, data: dict | None = None, show: dict | None = None, **kw):
    """Run `js` (it calls out(value)) with the core loaded; returns the value."""
    return run_js(case, LOAD + js, data={"show": show or sample_show(), "now": NOW, **(data or {})}, needs_modules=False, **kw)


def js_round(x: float) -> float:
    """Math.round(x * 10) / 10, as the core rounds seconds."""
    return math.floor(x * 10 + 0.5) / 10


CHANNEL_IDS = ["quiz", "puzzles", "facts", "quotes", "polls", "prompts", "messages", "qr", "web-video", "web-audio",
               "web-image", "photos", "posters", "videos", "sounds", "notes", "live-events", "live-quote", "live-video",
               "live-podcast", "live-themes", "live-prices", "live-book", "live-meetings", "live-bulletin", "welcome",
               "about"]
DEFAULTS = {
    "event": {"en": "", "es": "", "sub": "", "show": True}, "lang": "both", "first": "en",
    "pubs": {"gv": True, "lv": True}, "channels": {c: True for c in CHANNEL_IDS}, "collections": {}, "items": {},
    "tags": {}, "boost": {}, "order": "shuffle", "pace": "normal", "reveal": 12, "photoSeconds": 8, "mediaMax": 180,
    "webMediaMax": 90, "clipEvery": 8, "sound": False, "volume": 0.8, "captions": True, "idleSeconds": 40, "visitor": True,
    "quizLength": 5, "theme": "dark", "textSize": "normal", "motion": "full", "clock": True, "qrCorner": True,
    "progress": True, "overscan": False, "pin": "", "wakeLock": True, "autoFullscreen": True, "refreshMinutes": 30,
    "autoSave": True,
}


class Settings(unittest.TestCase):
    def test_defaults_channels_and_types(self):
        r = core(self, "out({ d: G.DEFAULTS, ch: G.CHANNELS, ty: G.TYPES });")
        self.assertEqual(r["d"], DEFAULTS)
        self.assertEqual(list(r["d"].keys()), list(DEFAULTS.keys()))
        self.assertEqual([c["id"] for c in r["ch"]], CHANNEL_IDS)
        self.assertEqual({c["id"] for c in r["ch"] if c.get("needsNet")},
                         {"web-video", "web-audio", "web-image", "live-video", "live-podcast"})
        types = r["ty"]
        render = {"quiz", "truefalse", "fact", "quote", "history", "fill", "scramble", "poll", "prompt", "message", "qr",
                  "video", "audio", "image", "photo", "poster", "events", "countdown", "themes", "prices", "book",
                  "meetings"}
        self.assertEqual(set(types), render | {"welcome", "about"})          # SPEC §3.1 + the player's own two
        by_group = lambda g: {t for t, v in types.items() if v["group"] == g}  # noqa: E731
        self.assertEqual(by_group("play"), {"quiz", "truefalse", "fill", "scramble", "poll"})
        self.assertEqual(by_group("media"), {"video", "audio", "image", "photo", "poster"})
        self.assertEqual({t for t, v in types.items() if v["interactive"]}, by_group("play"))
        for c in r["ch"]:
            self.assertIn(c["group"], {"play", "learn", "media", "live", "info"})
            for t in c["types"]:
                self.assertIn(t, types, c["id"])
        # a type's own channel exists and lists the type; every type is in at least one channel
        for t, v in types.items():
            owners = [c["id"] for c in r["ch"] if t in c["types"]]
            self.assertTrue(owners, t)
            if "channel" in v:
                self.assertIn(v["channel"], owners, t)

    def test_norm_settings_never_throws_and_clamps(self):
        r = core(self, r"""
          const evil = {};
          Object.defineProperty(evil, "lang", { enumerable: true, get() { throw new Error("boom"); } });
          const deep = { event: {} };
          Object.defineProperty(deep.event, "en", { enumerable: true, get() { throw new Error("boom"); } });
          out({
            garbage: [null, undefined, 42, "text", [], [1, 2], true].map((v) => G.normSettings(v)),
            evil: G.normSettings(evil), deep: G.normSettings(deep), badBase: G.normSettings({ lang: "es" }, evil),
            wrong: G.normSettings({ lang: "fr", first: "de", order: 3, pace: "fast", theme: "pink", textSize: {}, motion: null,
              reveal: "abc", photoSeconds: NaN, mediaMax: Infinity, volume: "loud", pin: "12345", sound: "yes", clock: "no",
              items: [1, 2], tags: "history", channels: "x", pubs: 5, collections: [true], boost: "x", clipEvery: "often",
              event: { en: 5, es: ["x"], sub: {}, show: "maybe" }, bogus: 1 }),
            clamped: G.normSettings({ reveal: 99, photoSeconds: 1, mediaMax: 5000, webMediaMax: 2, volume: 7, idleSeconds: -5,
              quizLength: 12.7, refreshMinutes: 0, clipEvery: 1, boost: { quiz: 99, puzzles: 0, bogus: 2, facts: "1.5" } }),
            strings: G.normSettings({ reveal: "30", volume: " 0.5 ", quizLength: "7", sound: "true", clock: 0, autoSave: "0", clipEvery: " 12 " }),
            // a video or a sound at most once in clipEvery slides: a whole number from 3 to 30
            clips: [2.4, 3, 7.4, 7.5, 8, 29.6, 30, 31, 500, -8, "9", "x", null, true, [10], { n: 10 }]
              .map((v) => G.normSettings({ clipEvery: v }).clipEvery),
            clipBase: [G.normSettings({}, { clipEvery: 12 }).clipEvery, G.normSettings({ clipEvery: "x" }, { clipEvery: 12 }).clipEvery,
                       G.normSettings({ clipEvery: 5 }, { clipEvery: 12 }).clipEvery, G.withDefaults({ clipEvery: 40 }).clipEvery],
            kept: G.normSettings({
              items: { "quiz-gvr": false, "drive:AbC_12-x": false, "live:events:upcoming": false, "on-item": true, "bad id!": false, "": false },
              tags: { History: false, humor: true, "two words": false }, channels: { quiz: false, bogus: false },
              collections: { main: false, "spring-assembly-2027": true, "bad slug!": false },
              event: { en: "NETA 65 Spring Assembly\n", es: "Asamblea de Primavera", sub: "March 14 · Waco", show: false }, pin: "0420" }),
            long: G.normSettings({ event: { en: "x".repeat(500), sub: "y".repeat(500) } }),
            proto: G.normSettings(JSON.parse('{"tags":{"__proto__":false,"_x":false,"ok":false},"items":{"__proto__":false},"collections":{"__proto__":false},"boost":{"__proto__":2}}')),
            polluted: vm.runInContext("Object.keys(Object.prototype).length + Object.keys(Array.prototype).length", vmctx),
          });""")
        for v in r["garbage"] + [r["evil"], r["deep"], r["wrong"]]:
            self.assertEqual(v, DEFAULTS)
        self.assertEqual(r["badBase"]["lang"], "es")            # a broken base: DEFAULTS stand in for it
        c = r["clamped"]
        self.assertEqual((c["reveal"], c["photoSeconds"], c["mediaMax"], c["webMediaMax"], c["volume"], c["idleSeconds"],
                          c["quizLength"], c["refreshMinutes"], c["clipEvery"]), (60, 3, 900, 10, 1, 10, 10, 5, 3))
        self.assertEqual(c["boost"], {"quiz": 5, "puzzles": 0.25, "facts": 1.5})
        s = r["strings"]
        self.assertEqual((s["reveal"], s["volume"], s["quizLength"], s["sound"], s["clock"], s["autoSave"], s["clipEvery"]),
                         (30, 0.5, 7, True, False, False, 12))
        # rounded to a whole number, then kept from 3 to 30; anything that is not a number → the default (8)
        self.assertEqual(r["clips"], [3, 3, 7, 8, 8, 30, 30, 30, 30, 3, 9, 8, 8, 8, 8, 8])
        # the site's starting value stands in for a missing or broken one; a site value out of range is clamped too
        self.assertEqual(r["clipBase"], [12, 12, 5, 30])
        k = r["kept"]
        self.assertEqual(k["items"], {"quiz-gvr": False, "drive:AbC_12-x": False, "live:events:upcoming": False})
        self.assertEqual(k["tags"], {"history": False})
        self.assertFalse(k["channels"]["quiz"])
        self.assertNotIn("bogus", k["channels"])
        self.assertEqual(k["collections"], {"main": False, "spring-assembly-2027": True})
        self.assertEqual(k["event"], {"en": "NETA 65 Spring Assembly ", "es": "Asamblea de Primavera", "sub": "March 14 · Waco", "show": False})
        self.assertEqual(k["pin"], "0420")
        self.assertEqual((len(r["long"]["event"]["en"]), len(r["long"]["event"]["sub"])), (80, 120))
        p = r["proto"]
        self.assertEqual((p["tags"], p["items"], p["collections"], p["boost"]), ({"ok": False}, {}, {}, {}))
        self.assertEqual(r["polluted"], 0)

    def test_with_defaults_reads_the_site_settings(self):
        r = core(self, """
          const yml = G.withDefaults({ event_name: "NETA 65 Spring Assembly", event_name_es: "Asamblea de Primavera de NETA 65",
                                       language: "Alternate", sound: true, max_file_mb: 95 });
          out({ yml, keys: G.withDefaults({ event: { en: "Fall Assembly" }, lang: "es", first: "es", reveal: 20 }),
                es: G.withDefaults({}, "es").first, esKeep: G.withDefaults({ first: "en" }, "es").first,
                none: [G.withDefaults(null), G.withDefaults("x"), G.withDefaults(undefined)],
                onBase: G.normSettings({ lang: "en" }, yml), missing: G.normSettings({}, yml) });""")
        y = r["yml"]
        self.assertEqual(y["event"], {"en": "NETA 65 Spring Assembly", "es": "Asamblea de Primavera de NETA 65", "sub": "", "show": True})
        self.assertEqual((y["lang"], y["sound"]), ("alternate", True))
        self.assertNotIn("max_file_mb", y)
        self.assertEqual((r["keys"]["event"]["en"], r["keys"]["lang"], r["keys"]["first"], r["keys"]["reveal"]), ("Fall Assembly", "es", "es", 20))
        self.assertEqual((r["es"], r["esKeep"]), ("es", "en"))
        for v in r["none"]:
            self.assertEqual(v, DEFAULTS)
        self.assertEqual((r["onBase"]["lang"], r["onBase"]["sound"], r["onBase"]["event"]["en"]), ("en", True, "NETA 65 Spring Assembly"))
        self.assertEqual(r["missing"], y)

    def test_diff_gives_only_what_differs(self):
        r = core(self, """
          const base = G.withDefaults({ event_name: "Spring Assembly", sound: true });
          const s = G.normSettings({ lang: "es", channels: { quiz: false, polls: false }, items: { "quiz-gvr": false }, sound: true,
                                     event: { en: "Spring Assembly", sub: "Waco" }, boost: { quiz: 2 }, collections: { main: false } }, base);
          const off = G.normSettings({ collections: { main: false }, items: { x: false } });
          const on = G.normSettings({ collections: { main: true }, items: {} }, off);
          out({ d: G.diff(s, base), back: G.normSettings(G.diff(s, base), base), s, same: G.diff(base, base),
                vsDefaults: G.diff(s), none: G.diff(G.DEFAULTS), d2: G.diff(on, off) });""")
        self.assertEqual(r["d"], {"event": {"sub": "Waco"}, "lang": "es", "channels": {"quiz": False, "polls": False},
                                  "collections": {"main": False}, "items": {"quiz-gvr": False}, "boost": {"quiz": 2}})
        self.assertEqual(r["back"], r["s"])
        self.assertEqual((r["same"], r["none"]), ({}, {}))
        self.assertEqual(r["vsDefaults"]["sound"], True)
        self.assertEqual(r["vsDefaults"]["event"], {"en": "Spring Assembly", "sub": "Waco"})
        # back on (a collection's default is on) and a whole items map back to none
        self.assertEqual(r["d2"], {"collections": {"main": True}, "items": {}})

    def test_share_links_round_trip(self):
        r = core(self, """
          const s = G.normSettings({ event: { en: "NETA 65 Spring Assembly — Waco", es: "Asamblea de Primavera — ¡Bienvenidos! 🍇",
            sub: "Sábado 14 de marzo · Waco" }, lang: "alternate", first: "es", channels: { "live-video": false },
            items: { "quiz-gvr": false, "drive:1AbC-xyz_09": false }, tags: { humor: false }, boost: { quiz: 2, puzzles: 2 },
            pace: "lively", pin: "2468", volume: 0.35, clipEvery: 12 });
          const d = G.diff(s), code = G.encode(d), back = G.decode(code);
          const many = {};
          for (let i = 0; i < 300; i++) many["drive:file-number-" + i] = false;
          out({ d, code, back, applied: G.normSettings(back), s, empty: G.decode(G.encode({})), big: G.encode({ items: many }),
                node: JSON.parse(Buffer.from(code, "base64url").toString("utf8")),
                dflt: G.diff(G.normSettings({ clipEvery: 8 })), clip: G.decode(G.encode({ clipEvery: 30 })),
                garbage: [G.encode(null), G.encode("x"), G.encode([]), G.encode({ bogus: 1 }), G.encode({ lang: "fr" }), G.encode({ reveal: 99 }),
                          G.encode({ clipEvery: 2 }), G.encode({ clipEvery: 7.5 }), G.encode({ clipEvery: "8" })] });""")
        self.assertRegex(r["code"], r"^[A-Za-z0-9_-]+$")
        self.assertLessEqual(len(r["code"]), 2048)
        self.assertEqual(r["back"], r["d"])
        self.assertEqual(r["d"]["clipEvery"], 12)
        self.assertEqual(r["applied"], r["s"])
        self.assertEqual(r["node"], {"v": 1, "s": r["d"]})          # plain base64url JSON: Node reads it too
        self.assertEqual(r["empty"], {})
        self.assertEqual((r["dflt"], r["clip"]), ({}, {"clipEvery": 30}))   # the default is no difference
        self.assertIsNone(r["big"])                                 # refused rather than cut
        self.assertEqual(r["garbage"], [None] * 9)

    def test_decode_is_strict(self):
        r = core(self, r"""
          const b64 = (s) => Buffer.from(s, "utf8").toString("base64url");
          const raw = (bytes) => Buffer.from(bytes).toString("base64url");
          const ABC = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
          const good = G.encode({ lang: "es" });
          const e = G.encode({});
          const stray = e.slice(0, -1) + ABC[ABC.indexOf(e.slice(-1)) | 1];   // the same bytes for a lenient reader
          out({
            good: G.decode(good), strayLen: e.length % 4, strayNode: Buffer.from(stray, "base64url").toString("utf8"),
            goodClip: [G.decode(b64('{"v":1,"s":{"clipEvery":3}}')), G.decode(b64('{"v":1,"s":{"clipEvery":30,"webMediaMax":90}}'))],
            bad: [
              G.decode(""), G.decode(null), G.decode(42), G.decode({}), G.decode("a".repeat(2049)), G.decode(good + "$"),
              G.decode(good + "="), G.decode("abcde"), G.decode(stray),
              G.decode(raw([0xff, 0xfe, 0x7b])), G.decode(raw([0xc0, 0xaf])), G.decode(raw([0xed, 0xa0, 0x80])),
              G.decode(raw([0x7b, 0xe2, 0x82])),
              G.decode(b64("hello")), G.decode(b64("[1,2]")), G.decode(b64("null")),
              G.decode(b64('{"v":2,"s":{}}')), G.decode(b64('{"v":1,"s":{},"x":1}')), G.decode(b64('{"v":1,"s":[]}')),
              G.decode(b64('{"v":1,"s":{"bogus":1}}')), G.decode(b64('{"v":1,"s":{"lang":"fr"}}')),
              G.decode(b64('{"v":1,"s":{"reveal":99}}')), G.decode(b64('{"v":1,"s":{"reveal":"12"}}')),
              G.decode(b64('{"v":1,"s":{"channels":{"bogus":false}}}')), G.decode(b64('{"v":1,"s":{"channels":{"quiz":"no"}}}')),
              G.decode(b64('{"v":1,"s":{"items":{"quiz-gvr":true}}}')), G.decode(b64('{"v":1,"s":{"tags":{"History":false}}}')),
              G.decode(b64('{"v":1,"s":{"event":{"en":"x","bogus":1}}}')), G.decode(b64('{"v":1,"s":{"pin":"12345"}}')),
              G.decode(b64('{"v":1,"s":{"boost":{"quiz":7}}}')), G.decode(b64('{"v":1,"s":{"channels":false}}')),
              G.decode(b64('{"v":1,"s":{"clipEvery":31}}')), G.decode(b64('{"v":1,"s":{"clipEvery":8.5}}')),
              G.decode(b64('{"v":1,"s":{"clipEvery":"8"}}')), G.decode(b64('{"v":1,"s":{"clipEvery":null}}')),
            ],
          });""")
        self.assertEqual(r["good"], {"lang": "es"})
        self.assertEqual(r["goodClip"], [{"clipEvery": 3}, {"clipEvery": 30, "webMediaMax": 90}])
        self.assertNotEqual(r["strayLen"], 0)                  # the test needs a last character with spare bits
        self.assertEqual(r["strayNode"], '{"v":1,"s":{}}')    # Node accepts the stray bits …
        self.assertEqual(r["bad"], [None] * len(r["bad"]))    # … the core does not, nor anything else wrong

    def test_presets(self):
        r = core(self, """
          const all = G.PRESETS.map((n) => G.preset(n));
          const a = G.preset("quizparty");
          a.boost.quiz = 9;
          const party = G.normSettings(Object.assign({}, S(), G.preset("quizparty")));
          // a preset is a part put on top: only "Quiz party" changes how often a video or a sound may come
          const clipOf = (n) => G.normSettings(Object.assign({}, S({ clipEvery: 5 }), G.preset(n))).clipEvery;
          out({ names: G.PRESETS, all, again: G.preset("quizparty"), unknown: [G.preset("x"), G.preset(null), G.preset()],
                party: { boost: party.boost, pace: party.pace, clipEvery: party.clipEvery }, clips: G.PRESETS.map(clipOf),
                encoded: G.PRESETS.map((n) => G.encode(G.preset(n)) !== null) });""")
        self.assertEqual(r["names"], ["assembly", "spanish", "english", "quiet", "quizparty"])
        self.assertEqual(r["all"], [{"lang": "both"}, {"lang": "es", "first": "es"}, {"lang": "en", "first": "en"},
                                    {"sound": False, "pace": "calm", "motion": "calm"},
                                    {"boost": {"quiz": 2, "puzzles": 2}, "pace": "lively", "clipEvery": 10}])
        self.assertEqual(r["again"]["boost"]["quiz"], 2)       # a fresh copy each time
        self.assertEqual(r["unknown"], [None, None, None])
        self.assertEqual(r["party"], {"boost": {"quiz": 2, "puzzles": 2}, "pace": "lively", "clipEvery": 10})
        self.assertEqual(r["clips"], [5, 5, 5, 5, 10])
        self.assertEqual(r["encoded"], [True] * 5)              # every preset is a setup a link can carry


ITEM_KEYS = set(item("x", "fact", "facts", words("t")).keys())
AUDIO = {"drive:a1", "audio-web", "live:podcast:ep1"}


class Pool(unittest.TestCase):
    def test_every_reason_in_its_order(self):
        r = core(self, r"""
          const W = (id, part, c) => G.why(typeof id === "string" ? byId(id) : id, S(part), c || C);
          const at = (iso, online) => G.ctx({ now: Date.parse(iso), online: online !== false });
          const offline = at(input.now, false);
          const later = byId("live:countdown:assembly").until_ts;
          const ahead = Object.assign({}, byId("fact-1944"), { from: "2026-10-03" });
          const photo = (media) => Object.assign({}, byId("drive:f1"), { media });
          out({
            ok: [W("quiz-gvr"), W("drive:f1"), W("live:events:upcoming"), W("drive:v2")],
            off: W("quiz-gvr", { items: { "quiz-gvr": false } }),
            channel: [W("quiz-gvr", { channels: { quiz: false } }), W("tf-ads", { channels: { quiz: false } }),
                      W("quote-preamble", { channels: { quotes: false } }), W("live:quote:gv", { channels: { quotes: false } }),
                      W("live:quote:gv", { channels: { "live-quote": false } }), W("drive:v1", { channels: { "web-video": false } })],
            pub: [W("drive:p1", { pubs: { gv: false } }), W("quiz-gvr", { pubs: { gv: false } }), W("quiz-gvr", { pubs: { gv: false, lv: false } }),
                  W("quiz-la-vina-year", { pubs: { lv: false } })],
            collection: [W("drive:f4", { collections: { "spring-assembly-2027": false } }), W("drive:f1", { collections: { "spring-assembly-2027": false } }),
                         W("drive:f1", { collections: { main: false } })],
            tag: [W("fact-1944", { tags: { history: false } }), W("fact-languages", { tags: { history: false } }), W("quiz-gvr", { tags: { GVR: false } })],
            date: [W("drive:f3", {}, at("2026-10-27T04:59:00Z")), W("drive:f3", {}, at("2026-10-27T05:00:00Z")),
                   W(ahead), W(ahead, {}, at("2026-10-03T04:59:00Z")), W(ahead, {}, at("2026-10-03T05:00:00Z"))],
            over: [W("live:countdown:assembly", {}, G.ctx({ now: later })), W("live:countdown:assembly", {}, G.ctx({ now: later + 1 })),
                   W("live:events:upcoming", {}, G.ctx({ now: later + 1 })), W("live:meetings:next", {}, at("2026-11-01T00:00:00Z")),
                   W(Object.assign({}, byId("live:themes:next"), { en: null, es: null, langs: [] })), W("live:prices:subs", {}, at("2027-06-01T00:00:00Z"))],
            lang: [W("quiz-app", { lang: "es" }), W("quiz-app", { lang: "en" }), W("quiz-es-only", { lang: "en" }), W("drive:f1", { lang: "es" }),
                   W("drive:p1", { lang: "es" }), W("drive:f3", { lang: "en" }), W("drive:f3", { lang: "both" }), W("quiz-app", { lang: "alternate" })],
            offline: [W("video-gv-yt", {}, offline), W("drive:f6", {}, offline), W("drive:f1", {}, offline), W("live:quote:gv", {}, offline)],
            muted: [W("drive:a1"), W("drive:a1", { sound: true }), W("audio-web"), W("live:podcast:ep1", {}, offline), W("drive:v1")],
            media: [W(photo(null)), W(photo({ kind: "image", src: "" })), W(photo({ kind: "gif", src: "/x.gif" })),
                    W("video-gv-yt", {}, G.ctx({ now: NOW, youtube: false })), W("drive:v1", {}, G.ctx({ now: NOW, youtube: false })),
                    W("drive:f1", {}, G.ctx({ now: NOW, failed: { "drive:f1": true } })),
                    W(Object.assign({}, byId("video-gv-yt"), { media: { kind: "youtube", src: "x", id: "" } })),
                    W({ id: "x", type: "hologram" }), W({ type: "fact" }), G.why(null, S(), C), G.why("x", S(), C)],
            order: [W("quiz-gvr", { items: { "quiz-gvr": false }, channels: { quiz: false } }), W("drive:p1", { channels: { posters: false }, pubs: { gv: false } }),
                    W("quiz-app", { lang: "es" }, offline), W("drive:f3", { lang: "en" }, at("2026-11-01T12:00:00Z")),
                    W("video-gv-yt", { lang: "es" }, offline)],
            garbageSettings: G.why(byId("quiz-gvr"), "nonsense", null),
            // a ctx written by hand: online unless it says false
            handCtx: [W("video-gv-yt", {}, { now: NOW, today: "2026-10-02" }), W("video-gv-yt", {}, { now: NOW, today: "2026-10-02", online: false })],
          });""")
        self.assertEqual(r["ok"], [None, None, None, None])
        self.assertEqual(r["off"], "off")
        self.assertEqual(r["channel"], ["channel", "channel", "channel", None, "channel", None])
        self.assertEqual(r["pub"], ["pub", None, "pub", "pub"])
        self.assertEqual(r["collection"], ["collection", None, "collection"])
        self.assertEqual(r["tag"], ["tag", None, "tag"])
        # a Central day: October 26 lasts until 05:00Z on the 27th (daylight time)
        self.assertEqual(r["date"], [None, "date", "date", "date", None])
        self.assertEqual(r["over"], [None, "over", "over", "over", "over", None])
        self.assertEqual(r["lang"], ["lang", None, "lang", None, "lang", "lang", None, None])
        self.assertEqual(r["offline"], ["offline", "offline", None, None])
        self.assertEqual(r["muted"], ["muted", None, "muted", "offline", None])
        # (a local video plays while YouTube is unavailable)
        self.assertEqual(r["media"], ["media"] * 4 + [None] + ["media"] * 6)
        self.assertEqual(r["order"], ["off", "channel", "lang", "date", "lang"])
        self.assertIsNone(r["garbageSettings"])
        self.assertEqual(r["handCtx"], [None, "offline"])

    def test_auto_items(self):
        r = core(self, r"""
          const autos = (part, json) => G.pool(json === undefined ? J : json, S(part), C).filter((it) => it.source === "auto").map((it) => it.id);
          out({
            none: G.autoItems(J, S()).map((it) => it.id),
            withEvent: G.autoItems(J, S({ event: { en: "NETA 65 Spring Assembly" } })),
            esOnly: G.autoItems(J, S({ event: { es: "Asamblea de Primavera" } }))[0],
            both: G.autoItems(J, S({ event: { en: "Fall Assembly", es: "Asamblea de Otoño" } }))[0],
            hidden: G.autoItems(J, S({ event: { en: "X", show: false } })).map((it) => it.id),
            spaces: G.autoItems(J, S({ event: { en: "   " } })).map((it) => it.id),
            noJson: G.autoItems(null, S())[0], rawSettings: G.autoItems(J, { event: { en: "Raw" } }).map((it) => it.id),
            inPool: autos({ event: { en: "X" } }), welcomeOff: autos({ event: { en: "X" }, channels: { welcome: false } }),
            aboutOff: autos({ items: { "auto:about": false } }), emptyShow: autos({}, { items: [] }),
          });""")
        self.assertEqual(r["none"], ["auto:about"])
        w, a = r["withEvent"]
        self.assertEqual((w["id"], w["type"], w["channel"], w["source"], w["langs"], w["collection"]),
                         ("auto:welcome", "welcome", "welcome", "auto", ["en", "es"], "auto"))
        self.assertEqual(set(w.keys()), ITEM_KEYS)
        self.assertEqual(set(a.keys()), ITEM_KEYS)
        # (no sentence joins the event's name: "¡Bienvenidos a Asamblea …!" would lack its "la")
        self.assertEqual((w["en"]["title"], w["en"]["text"]), ("Welcome! · NETA 65 Spring Assembly", "Grapevine and La Viña — ask us anything"))
        # the Spanish name left blank → the English one; La Viña first on a Spanish text that names both (SPEC §4)
        self.assertEqual((w["es"]["title"], w["es"]["text"]), ("¡Bienvenidos! · NETA 65 Spring Assembly", "La Viña y Grapevine — pregúntanos lo que quieras"))
        self.assertEqual((a["id"], a["type"], a["qr"], a["url"]), ("auto:about", "about", SITE["url"], SITE["url"]))
        self.assertEqual((a["qr_es"], w["qr"], w["qr_es"]), (SITE["url_es"], None, None), "the about slide's Spanish code: the Spanish home")
        self.assertEqual(a["en"]["title"], "Shared by the NETA 65 Grapevine & La Viña Committee")
        self.assertEqual(a["en"]["text"], "Not an official AA Grapevine, Inc. or A.A.W.S. display")
        self.assertEqual(a["es"]["title"], "Compartido por el Comité de Grapevine y La Viña de NETA 65")
        self.assertEqual(a["es"]["text"], "Esta no es una pantalla oficial de AA Grapevine, Inc. ni de A.A.W.S.")
        self.assertEqual((a["en"]["credit"], a["es"]["credit"]), (SITE["host"], SITE["host"]))
        self.assertEqual(r["esOnly"]["en"]["title"], "Welcome! · Asamblea de Primavera")
        self.assertEqual((r["both"]["en"]["title"], r["both"]["es"]["title"]), ("Welcome! · Fall Assembly", "¡Bienvenidos! · Asamblea de Otoño"))
        self.assertEqual((r["hidden"], r["spaces"]), (["auto:about"], ["auto:about"]))
        self.assertEqual((r["noJson"]["qr"], r["noJson"]["qr_es"], r["noJson"]["en"]["credit"]), (None, None, ""))
        self.assertEqual(r["noJson"]["en"]["title"], "Shared by the NETA 65 Grapevine & La Viña Committee")
        self.assertEqual(r["rawSettings"], ["auto:welcome", "auto:about"])
        self.assertEqual(r["inPool"], ["auto:welcome", "auto:about"])
        self.assertEqual(r["welcomeOff"], ["auto:about"])
        self.assertEqual(r["aboutOff"], [])
        self.assertEqual(r["emptyShow"], ["auto:about"])

    def test_pool_contents_and_live_rows(self):
        show = sample_show()
        r = core(self, r"""
          const s = S();
          const p = G.pool(J, s, C);
          const ev = p.find((it) => it.id === "live:events:upcoming");
          out({
            ids: p.map((it) => it.id), evRows: ev.en.rows.map((x) => x.title), evRowsEs: ev.es.rows.map((x) => x.title),
            untouched: byId("live:events:upcoming").en.rows.length, evTitle: ev.en.title,
            sameObject: p.find((it) => it.id === "quiz-gvr") === byId("quiz-gvr"),
            later: G.pool(J, s, G.ctx({ now: Date.parse("2026-11-15T00:00:00Z") })).map((it) => it.id),
            offline: G.pool(J, s, G.ctx({ now: NOW, online: false })).map((it) => it.id),
            sound: G.pool(J, S({ sound: true }), C).map((it) => it.id),
            es: G.pool(J, S({ lang: "es" }), C).map((it) => it.id),
            dup: G.pool({ items: [byId("quiz-gvr"), byId("quiz-gvr"), null, 5, { id: 3 }] }, s, C).map((it) => it.id),
            empty: [G.pool(null, s, C), G.pool({}, s, C), G.pool({ items: "x" }, s, C)].map((q) => q.map((it) => it.id)),
            rawCtx: G.pool(J, s, { now: NOW, online: false }).length,
          });""", show=show)
        all_ids = [it["id"] for it in show["items"]]
        self.assertEqual(r["ids"], [i for i in all_ids if i not in AUDIO] + ["auto:about"])
        self.assertEqual(r["evRows"], ["Writing workshop", "Fall Assembly"])      # the CityWide row of Oct 1 is over
        self.assertEqual(r["evRowsEs"], ["Taller de escritura", "Asamblea de Otoño"])
        self.assertEqual((r["untouched"], r["evTitle"]), (3, "Coming up"))        # a copy: the show is not changed
        self.assertTrue(r["sameObject"])
        gone = {"live:events:upcoming", "live:countdown:assembly", "live:meetings:next", "live:themes:next", "drive:f3"}
        self.assertEqual(r["later"], [i for i in r["ids"] if i not in gone])
        online = {it["id"] for it in show["items"] if it["online"]}
        self.assertEqual(r["offline"], [i for i in r["ids"] if i not in online])
        self.assertEqual(r["rawCtx"], len(r["offline"]))
        self.assertEqual(r["sound"], all_ids + ["auto:about"])
        es_ok = [it["id"] for it in show["items"] if (not it["langs"] or "es" in it["langs"]) and it["id"] not in AUDIO]
        self.assertEqual(r["es"], es_ok + ["auto:about"])
        self.assertEqual(r["dup"], ["quiz-gvr", "auto:about"])
        self.assertEqual(r["empty"], [["auto:about"]] * 3)


class Languages(unittest.TestCase):
    def test_four_modes_and_words(self):
        r = core(self, r"""
          const two = byId("quiz-gvr"), en1 = byId("quiz-app"), es1 = byId("quiz-es-only"), neutral = byId("drive:f1"), photoEn = byId("drive:p1");
          const table = {};
          ["en", "es", "both", "alternate"].forEach((m) => { table[m] = [two, en1, es1, neutral, photoEn].map((it) => G.lang(it, S({ lang: m }), G.newState(1))); });
          const alt = (first, turn) => G.lang(two, S({ lang: "alternate", first }), { langTurn: turn });
          out({
            table, alt: [alt("en", 0), alt("en", 1), alt("en", 2), alt("en", 3), alt("es", 1), alt("es", 2), alt("en", -4), alt("en", "x")],
            noState: G.lang(two, S({ lang: "alternate" })), firstEs: G.lang(two, S({ lang: "alternate", first: "es" })),
            text: { en: G.text(two, "en"), es: G.text(two, "es"), both: G.text(two, "both"), borrow: G.text(neutral, "es"),
                    bothNeutral: G.text(neutral, "both"), nul: G.text(null, "en"), nulBoth: G.text(undefined, "both"),
                    odd: G.text({ en: { title: 5, choices: "x", rows: [1, { a: 1 }], text: null } }, "en"), weird: G.text(two, "fr") },
            fill: [G.fill("Thank you for visiting our table at {event}.", { event: "the Spring Assembly" }), G.fill("Welcome to {event}!", {}),
                   G.fill("Visit {site} or {site_es} · {committee}", { site: "neta65.github.io/aagrapevine", site_es: "neta65.github.io/aagrapevine/es/",
                          committee: "NETA 65 Grapevine & La Viña Committee" }),
                   G.fill("{unknown} stays", { unknown: "x" }), G.fill(null, {}), G.fill("{event}", null)],
            fmt: [G.fmt("{n} of {total}", { n: 4, total: 5 }), G.fmt("{n} of {total}", { n: 4 }), G.fmt("{a}", null)],
          });""")
        self.assertEqual(r["table"], {"en": ["en", "en", "es", "en", "en"], "es": ["es", "en", "es", "es", "en"],
                                      "both": ["both", "en", "es", "both", "en"], "alternate": ["en", "en", "es", "en", "en"]})
        self.assertEqual(r["alt"], ["en", "en", "es", "en", "es", "en", "en", "en"])
        self.assertEqual((r["noState"], r["firstEs"]), ("en", "es"))
        t = r["text"]
        empty = words()
        self.assertEqual(t["en"], words(text="Who carries the Grapevine's message in a home group?", choices=["The GVR", "The treasurer"],
                                        explain="The Grapevine Representative."))
        self.assertEqual(t["es"]["choices"], ["El RLV", "El tesorero"])
        self.assertEqual(t["both"], {"en": t["en"], "es": t["es"]})
        self.assertEqual(t["borrow"]["title"], "Our booth at CityWide Dallas")      # a caption in one language
        self.assertEqual(t["bothNeutral"], {"en": words("Our booth at CityWide Dallas"), "es": empty})
        self.assertEqual((t["nul"], t["nulBoth"]), (empty, {"en": empty, "es": empty}))
        self.assertEqual(t["odd"], words(title="5", rows=[{"a": 1}]))
        self.assertEqual(t["weird"], t["en"])
        self.assertEqual(r["fill"], ["Thank you for visiting our table at the Spring Assembly.", "Welcome to!",
                                     "Visit neta65.github.io/aagrapevine or neta65.github.io/aagrapevine/es/ · NETA 65 Grapevine & La Viña Committee",
                                     "{unknown} stays", "", ""])
        self.assertEqual(r["fmt"], ["4 of 5", "4 of {total}", "{a}"])

    def test_alternate_over_a_show(self):
        r = core(self, r"""
          out({ a: run({ lang: "alternate" }, 300, 11).picks, b: run({ lang: "alternate", first: "es" }, 300, 11).picks,
                both: run({ lang: "both" }, 120, 11).picks, es: run({ lang: "es" }, 120, 11).picks });""")
        for key in ("a", "b"):
            picks = r[key]
            for i, p in enumerate(picks):
                if len(p["langs"]) == 1:
                    self.assertEqual(p["lang"], p["langs"][0], (key, i, p))   # one language: always that one
                elif i:
                    self.assertNotEqual(p["lang"], picks[i - 1]["lang"], (key, i, p))  # the turn goes to the other language
            counts = {lang: sum(1 for p in picks if p["lang"] == lang) for lang in ("en", "es")}
            self.assertGreater(min(counts.values()), 100, (key, counts))
        self.assertEqual(r["a"][0]["lang"], "en")                    # the first item is English-only (drive:p1)
        self.assertEqual((r["a"][1]["lang"], r["b"][1]["lang"]), ("es", "es"))
        for p in r["both"]:
            self.assertEqual(p["lang"], "both" if len(p["langs"]) != 1 else p["langs"][0])
        for p in r["es"]:
            self.assertEqual(p["lang"], "es")                       # Spanish only: no English-only item is in the pool


PLAY = {"quiz", "truefalse", "fill", "scramble", "poll"}
MEDIA = {"video", "audio", "image", "photo", "poster"}
CLIPS = {"video", "audio"}                 # a video or a sound: at most once in clipEvery slides
PICTURES = MEDIA - CLIPS
LISTS = {"events", "meetings", "themes"}


def gaps(positions):
    return [b - a for a, b in zip(positions, positions[1:])]


class QrCodes(unittest.TestCase):
    """The code a slide shows (SPEC update 1): a CSV qr_url written {site}… — and a live list's page — has an English
    address (qr) and a Spanish one (qr_es); a Spanish slide shows the Spanish one, "both" the first language's."""

    def test_qr_of(self):
        en, es = SITE["url"] + "contribute/", SITE["url"] + "es/contribute/"
        r = core(self, r"""
          const site = { qr: input.en, qr_es: input.es }, one = { qr: input.en, qr_es: null }, none = { qr: null, qr_es: null };
          out({
            site: ["en", "es"].map((l) => G.qrOf(site, l)),
            both: [G.qrOf(site, "both", S()), G.qrOf(site, "both", S({ first: "es" })), G.qrOf(site, "both")],
            one: ["en", "es", "both"].map((l) => G.qrOf(one, l, S({ first: "es" }))),
            none: [G.qrOf(none, "es"), G.qrOf(null, "en"), G.qrOf({ qr: 5, qr_es: ["x"] }, "es")],
            about: ["en", "es"].map((l) => G.qrOf(G.autoItems(J, S())[0], l)),
            lone: G.qrOf({ qr: null, qr_es: input.es }, "es"),
          });""", data={"en": en, "es": es})
        self.assertEqual(r["site"], [en, es])
        self.assertEqual(r["both"], [en, es, en], "both: the first language's code (English unless Spanish leads)")
        self.assertEqual(r["one"], [en, en, en], "no Spanish address: the same code on every slide")
        self.assertEqual(r["none"], ["", "", ""])
        self.assertEqual(r["about"], [SITE["url"], SITE["url_es"]], "the about slide: the site's home in the slide's language")
        self.assertEqual(r["lone"], SITE["url"] + "es/contribute/")


class Scheduler(unittest.TestCase):
    def test_the_rules_over_2000_slides(self):
        show = sample_show()
        r = core(self, r"""
          const s = { event: { en: "NETA 65 Spring Assembly" } };
          const res = run(s, 2000, 7);
          out({ picks: res.picks.map((x) => [x.id, x.type]), pool: G.pool(J, S(s), C).map((it) => it.id) });""", show=show)
        ids = [p[0] for p in r["picks"]]
        types = [p[1] for p in r["picks"]]
        # the first items open the show, the welcome slide before them
        self.assertEqual(ids[:3], ["auto:welcome", "drive:p1", "drive:v2"])
        rest = [i for i in r["pool"] if not i.startswith("auto:")]
        window = min(max(4, math.ceil(0.4 * len(rest))), len(rest) - 1)
        self.assertEqual(window, 22)
        for i in range(len(ids)):
            if not ids[i].startswith("auto:"):
                self.assertNotIn(ids[i], ids[max(0, i - window):i], f"slide {i}: {ids[i]} again inside the window")
            if i >= 3 and types[i] == types[i - 1]:
                self.assertEqual(types[i], "photo", f"slide {i}: {types[i]} twice")
                self.assertNotEqual(types[i - 2], "photo", f"slide {i}: a third photo")
            self.assertLessEqual(sum(t in PLAY for t in types[i:i + 3]), 1, f"slides {i}-{i + 2}: more than 1 play slide")
            self.assertLessEqual(sum(t in LISTS for t in types[i:i + 6]), 1, f"slides {i}-{i + 5}: more than 1 list")
            if i + 4 <= len(types):
                self.assertTrue(any(t in MEDIA for t in types[i:i + 4]), f"slides {i}-{i + 3}: no media slide")
        # a video or a sound at most once in 8 slides (clipEvery's default), counted from drive:v2: a video marked
        # first, which opens the show whatever the rules say
        clips = [i for i, t in enumerate(types) if t in CLIPS]
        self.assertEqual(clips[0], 2)
        self.assertGreaterEqual(min(gaps(clips)), 8, gaps(clips))
        self.assertGreater(len(clips), 2000 / 8 * 0.6, len(clips))   # (and they still come: the media rule brings them)
        welcome = [i for i, x in enumerate(ids) if x == "auto:welcome"]
        about = [i for i, x in enumerate(ids) if x == "auto:about"]
        self.assertEqual(welcome[0], 0)
        self.assertTrue(set(gaps(welcome)) <= {12, 13}, gaps(welcome))   # 13: a media slide was due first
        self.assertIn(12, gaps(welcome))
        self.assertTrue(29 <= about[0] <= 31, about[0])
        self.assertTrue(set(gaps(about)) <= {30, 31, 32}, gaps(about))
        # every item of the pool comes up; play slides are a good share (the cap of 1 in 3 is a most, not a target:
        # once allowed, they come by their weight); weight 3 shows more than weight 1
        self.assertEqual(set(ids), set(r["pool"]))
        self.assertTrue(2000 * 0.12 < sum(t in PLAY for t in types) <= 2000 / 3 + 1, sum(t in PLAY for t in types))
        self.assertGreater(ids.count("drive:p2"), ids.count("drive:p3") * 1.3)

    # a run of the scheduler as [id, type] pairs, and the pool without the auto items
    RUN = r"""
      const res = run(input.settings, input.n, input.seed);
      out({ picks: res.picks.map((x) => [x.id, x.type]), pool: res.pool.filter((id) => !id.startsWith("auto:")) });"""

    def show_run(self, show, settings, n, seed):
        r = core(self, self.RUN, data={"settings": settings, "n": n, "seed": seed}, show=show)
        rest = r["pool"]
        return [p[0] for p in r["picks"]], [p[1] for p in r["picks"]], rest, min(max(4, math.ceil(0.4 * len(rest))), len(rest) - 1)

    def assert_rules(self, ids, types, window, label, clip_every=8, firsts=0):
        """Rules 1, 2, 3, 4 and 6 on every slide: no repeat inside the window, a clip at most once in clip_every
        slides, types vary (photo up to 2) — both but on the `firsts` slides that open the show (the items marked
        first come whatever the rules say) —, at most 1 play slide in 3, at most 1 live list in 6."""
        for i in range(len(ids)):
            if not ids[i].startswith("auto:"):
                self.assertNotIn(ids[i], ids[max(0, i - window):i], f"{label}, slide {i}: {ids[i]} again inside the window")
            if i >= firsts and types[i] in CLIPS:
                near = [j for j in range(max(0, i - clip_every + 1), i) if types[j] in CLIPS]
                self.assertFalse(near, f"{label}, slide {i}: a clip {i - near[-1] if near else 0} slides after another")
            if i >= max(1, firsts) and types[i] == types[i - 1]:
                self.assertEqual(types[i], "photo", f"{label}, slide {i}: {types[i]} twice")
                self.assertFalse(i >= 2 and types[i - 2] == "photo", f"{label}, slide {i}: a third photo")
            self.assertLessEqual(sum(t in PLAY for t in types[i:i + 3]), 1, f"{label}, slides {i}-{i + 2}: more than 1 play slide")
            self.assertLessEqual(sum(t in LISTS for t in types[i:i + 6]), 1, f"{label}, slides {i}-{i + 5}: more than 1 list")

    def test_welcome_and_about_never_wait_for_a_media_slide_that_cannot_come(self):
        # 100 text slides and 2 photos (window 41): most of the time both photos are inside the window. The welcome
        # and about slides wait only for a media slide that can come now — before, they waited until a photo left the
        # window (gaps up to 46 and 42 instead of 12 and 30; the about slide is the one that says the display is not
        # an official one)
        for lists in (False, True):
            ids, types, rest, window = self.show_run(text_show(100, photos=2, lists=lists), {"event": {"en": "X"}}, 1200, 7)
            self.assertEqual(len(rest), 105 if lists else 102)
            welcome = [i for i, x in enumerate(ids) if x == "auto:welcome"]
            about = [i for i, x in enumerate(ids) if x == "auto:about"]
            self.assertEqual(welcome[0], 0)
            self.assertTrue(set(gaps(welcome)) <= {12, 13}, (lists, gaps(welcome)))
            self.assertTrue(29 <= about[0] <= 31, (lists, about[0]))
            self.assertTrue(set(gaps(about)) <= {30, 31, 32}, (lists, gaps(about)))
            self.assert_rules(ids, types, window, f"lists {lists}")
            if lists:
                self.assertGreaterEqual(min(gaps([i for i, t in enumerate(types) if t in LISTS])), 6)

    def test_a_rule_that_cannot_be_kept_gives_way_alone(self):
        # a state as storage may hold it (normState keeps its counters as they are): the last slide a poster, a media
        # slide due, the events list two slides back. The one media item outside the window is a poster too, so the
        # media rule cannot be kept along with "types vary" (more important): it gives way alone, and the list cap
        # after it still holds — the meetings list never comes now. (The old fallback dropped every rule after the
        # one that could not be kept: the meetings list in about 1 draw of 4.)
        r = core(self, r"""
          const p = ["drive:p2", "live:events:upcoming", "live:meetings:next", "fact-1944", "fact-languages", "quote-preamble",
                     "prompt-first", "message-subs", "history-1944"].map(byId);
          const picks = [];
          for (let seed = 1; seed <= 300; seed++) {
            const st = { seed, n: 40, recent: ["drive:p2", "history-1944", "live:events:upcoming", "fact-1944", "message-subs"], firstQueue: [],
                         lastType: "poster", sinceWelcome: 5, sinceAbout: 5, sinceMedia: 9, sincePlay: 9, sinceList: 2, langTurn: 0 };
            picks.push(G.next(st, p, S(), C).item.id);
          }
          out(picks);""")
        # (the window: the last 4 slides; drive:p2 is outside it, but a poster right after a poster breaks rule 2)
        self.assertEqual(set(r), {"fact-languages", "quote-preamble", "prompt-first"})

    def test_one_picture_left_keeps_every_other_rule(self):
        # the sample show with one picture left (drive:f1): a media slide cannot come every 4 slides. The live-list cap
        # still holds (two lists came back to back when the media rule gave way and took it along) and the welcome /
        # about slides keep their 12 / 30 (they waited for that picture to leave the window)
        off = {c: False for c in ("web-video", "web-audio", "web-image", "posters", "videos", "sounds", "live-video", "live-podcast")}
        settings = {"event": {"en": "NETA 65 Spring Assembly"}, "channels": off,
                    "items": {f"drive:f{k}": False for k in range(2, 7)}}
        show = sample_show()
        type_of = {it["id"]: it["type"] for it in show["items"]}
        for seed in (7, 1):
            ids, types, rest, window = self.show_run(show, settings, 2000, seed)
            self.assertEqual([i for i in rest if type_of[i] in MEDIA], ["drive:f1"])
            self.assertTrue(any(not any(t in MEDIA for t in types[i:i + 4]) for i in range(len(types) - 3)))  # the show this needs
            self.assert_rules(ids, types, window, f"seed {seed}")
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:welcome"])) <= {12, 13})
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:about"])) <= {30, 31, 32})

    def test_few_pictures_spread_over_the_window(self):
        # an offline booth: 234 text slides and 11 photos (pool 245, window 98). A media slide every 4 would use the
        # 11 up in ~44 slides, then show none for ~55 (half an hour) until the first left the window, again and again.
        # With so few, one comes every (98 + 1) / 11 = 9 slides — and only then — so they spread evenly. With 22 the
        # spacing rounds to 4, and they still come only on their turn: 22 in 88 slides, then the 11 left over until
        # the first may come back (a picture drawn between turns made that hole 27 slides long)
        for photos in (11, 22):
            ids, types, rest, window = self.show_run(text_show(245 - photos, photos=photos), {"event": {"en": "X"}}, 1500, 3)
            self.assertEqual((len(rest), window), (245, 98))
            every = max(4, (window + 1) // photos)                    # 9, 4
            left = window + 1 - every * photos                         # 0, 11: the slides a cycle leaves over
            media = [i for i, t in enumerate(types) if t in MEDIA]
            self.assertEqual(media[0], every - 1, (photos, media[:3]))
            self.assertLessEqual(max(gaps(media)), every + left, (photos, gaps(media)))
            for i in range(0, 1500 - 49):
                self.assertTrue(any(t in MEDIA for t in types[i:i + 50]), f"{photos} photos, slides {i}-{i + 49}: no picture")
            # every picture still once per window (as many media slides as a burst gave), only spread out
            self.assertGreaterEqual(len(media), 1500 * photos // (window + 1) - photos, photos)
            self.assert_rules(ids, types, window, f"{photos} photos")
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:welcome"])) <= {12, 13}, photos)
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:about"])) <= {30, 31, 32}, photos)

    def test_clips_never_closer_than_clip_every(self):
        # The committed show online: its only media are videos and sounds (the CSV's and the official channels'
        # YouTube videos, the podcast — no Drive pictures yet). The media rule wanted a media slide every 4 and only a
        # clip could fill it: about 30 % of the slides were videos, and most of the screen time. Now a clip comes at
        # most once in clipEvery slides — and as soon as it may: a due media slide waits for the clip's turn (it never
        # forces one sooner) and then brings it, every max(4, clipEvery) slides. The welcome / about slides are never
        # held back by a clip that may not come yet
        show = clip_show(150, 60, n_play=80)
        for every, n in ((8, 3000), (3, 1200), (12, 1200), (30, 1500)):
            settings = {"sound": True, "event": {"en": "NETA 65 Spring Assembly"}}
            if every != 8:
                settings["clipEvery"] = every                  # (8 is the default)
            ids, types, rest, window = self.show_run(show, settings, n, 5)
            self.assertEqual((len(rest), window), (290, 116))
            clips = [i for i, t in enumerate(types) if t in CLIPS]
            self.assertGreaterEqual(min(gaps(clips)), every, (every, gaps(clips)[:30]))
            if every >= 4:
                # only clips as media and plenty of them: the media turn comes every clipEvery slides, a clip on it
                self.assertEqual(set(gaps(clips)), {every}, (every, sorted(set(gaps(clips)))))
                self.assertEqual(clips[0], every - 1)
            else:
                # clipEvery 3: a clip may come between the media turns (every 4) too
                self.assertTrue(set(gaps(clips)) <= {3, 4}, sorted(set(gaps(clips))))
            self.assertGreaterEqual(len(clips), n // max(4, every) - 1, every)
            # every kind of clip takes its turns: YouTube, a Drive video, a web sound, a podcast, a Drive sound
            self.assertEqual({ids[i].split(":")[0].split("-")[0] for i in clips}, {"video", "live", "drive", "audio"}, every)
            self.assertEqual({types[i] for i in clips}, CLIPS)
            self.assert_rules(ids, types, window, f"clipEvery {every}", clip_every=every)
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:welcome"])) <= {12, 13}, every)
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:about"])) <= {30, 31, 32}, every)

    def test_pictures_keep_the_media_pace(self):
        # A Drive folder's pictures online, with the clips: the media rule still brings a media slide at least every
        # 4 — the pictures fill the turns a clip may not take (after a clip, the next media slide is a picture) —
        # and the clips stay at most one in 8. Without a clip the pictures come every 4 exactly as before
        for clips in (60, 0):
            show = clip_show(150, clips, photos=60, n_play=80)
            ids, types, rest, window = self.show_run(show, {"sound": True, "event": {"en": "X"}}, 2000, 9)
            media = [i for i, t in enumerate(types) if t in MEDIA]
            pictures = [i for i, t in enumerate(types) if t in PICTURES]
            at = [i for i, t in enumerate(types) if t in CLIPS]
            self.assertLessEqual(media[0], 3, clips)
            self.assertLessEqual(max(gaps(media)), 4, (clips, sorted(set(gaps(media)))))
            self.assertLessEqual(max(gaps(pictures)), 8 if clips else 4, (clips, sorted(set(gaps(pictures)))))
            if clips:
                self.assertGreaterEqual(min(gaps(at)), 8)
                self.assertGreater(len(pictures), len(at), "the pictures take the turns a clip may not")
                self.assertGreater(len(at), 2000 / 8 * 0.5, "and the clips still come")
            else:
                self.assertEqual(at, [])
            self.assert_rules(ids, types, window, f"{clips} clips")
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:welcome"])) <= {12, 13}, clips)
            self.assertTrue(set(gaps([i for i, x in enumerate(ids) if x == "auto:about"])) <= {30, 31, 32}, clips)

    def test_first_clips_open_the_show_anyway(self):
        # the items marked first open the show whatever the rules say: two videos marked first play one after the
        # other (a Drive video with order 1, a YouTube video with order 2, then a fact marked first without one) —
        # and the clip rule counts from the last of them. After the settings change (firstQueue null) they open it
        # again, even right after a clip
        show = clip_show(150, 60, n_play=80)
        marks = {"drive:v2": {"first": True, "order": 1}, "video-0": {"first": True, "order": 2}, "fact-0": {"first": True}}
        for it in show["items"]:
            it.update(marks.get(it["id"], {}))
        r = core(self, r"""
          const s = { sound: true, event: { en: "NETA 65 Spring Assembly" } };
          const res = run(s, 600, 4);
          // the show again from a state whose last slide was a clip: firstQueue null (the settings changed)
          const p = G.pool(J, S(s), C);
          let st = res.state, k = 0;
          while (!["video", "audio"].includes(st.lastType) && k < 50) { st = G.next(st, p, S(s), C).state; k++; }
          let again = Object.assign({}, st, { firstQueue: null });
          const reopened = [];
          for (let i = 0; i < 40; i++) { const x = G.next(again, p, S(s), C); again = x.state; reopened.push([x.item.id, x.item.type]); }
          out({ picks: res.picks.map((x) => [x.id, x.type]), pool: res.pool.filter((id) => !id.startsWith("auto:")), lastType: st.lastType, reopened });""",
                 show=show)
        ids, types = [p[0] for p in r["picks"]], [p[1] for p in r["picks"]]
        self.assertEqual(ids[:4], ["auto:welcome", "drive:v2", "video-0", "fact-0"])
        clips = [i for i, t in enumerate(types) if t in CLIPS]
        self.assertEqual(clips[:3], [1, 2, 10])       # back to back, then 8 slides after the last one marked first
        self.assertGreaterEqual(min(gaps(clips[1:])), 8)
        window = min(max(4, math.ceil(0.4 * len(r["pool"]))), len(r["pool"]) - 1)
        self.assert_rules(ids, types, window, "first clips", firsts=4)
        self.assertIn(r["lastType"], CLIPS)
        again_ids, again_types = [p[0] for p in r["reopened"]], [p[1] for p in r["reopened"]]
        self.assertEqual(again_ids[:4], ["auto:welcome", "drive:v2", "video-0", "fact-0"])
        reclips = [i for i, t in enumerate(again_types) if t in CLIPS]
        self.assertEqual(reclips[:3], [1, 2, 10])

    def test_a_due_media_slide_waits_for_the_clips_turn(self):
        # One pick from a state as storage may hold it: a media slide due (sinceMedia 20) and only clips outside the
        # no-repeat window (the window: the last 4 slides). While a clip may not come yet the media rule waits — a
        # text comes, or the welcome slide when its turn has come (never held back) —; once the clip's turn has come
        # it brings one (and the welcome slide waits a slide for it). A picture fills the turn a clip may not take.
        # "In order" plays the committee's order, clips back to back if that is the order
        r = core(self, r"""
          const texts = ["fact-1944", "fact-languages", "quote-preamble", "prompt-first", "message-subs", "history-1944"].map(byId);
          const clips = ["video-gv-yt", "live:video:abc123", "drive:v1"].map(byId);
          const ev = S({ event: { en: "X" } });
          const welcome = G.autoItems(J, ev)[0];
          const picks = (pool, part, state) => {
            const seen = new Set();
            for (let seed = 1; seed <= 200; seed++) {
              const st = Object.assign({ seed, n: 60, recent: ["fact-1944", "quote-preamble", "prompt-first", "message-subs"], firstQueue: [],
                lastType: "message", sinceWelcome: 5, sinceAbout: 5, sinceMedia: 20, sinceClip: 3, sincePlay: 9, sinceList: 9, langTurn: 0 }, state);
              seen.add(G.next(st, pool, S(Object.assign({ event: { en: "X" } }, part)), C).item.id);
            }
            return [...seen].sort();
          };
          const all = texts.concat(clips);
          const inOrder = (() => {
            const p = [clips[0], clips[1], texts[0]];
            let st = Object.assign(G.newState(1), { firstQueue: [], recent: [clips[0].id], lastType: "video", n: 1, sinceClip: 0 });
            const o = [];
            for (let i = 0; i < 6; i++) { const x = G.next(st, p, S({ order: "inorder" }), C); st = x.state; o.push(x.item.id); }
            return o;
          })();
          out({
            notYet: picks(all, {}, {}), turn: picks(all, {}, { sinceClip: 7 }), fresh: picks(all, {}, { sinceClip: 60 }),
            welcomeNotYet: picks(all.concat([welcome]), {}, { sinceWelcome: 11 }), welcomeTurn: picks(all.concat([welcome]), {}, { sinceWelcome: 11, sinceClip: 7 }),
            every12: [picks(all, { clipEvery: 12 }, { sinceClip: 7 }), picks(all, { clipEvery: 12 }, { sinceClip: 11 })],
            every3: picks(all, { clipEvery: 3 }, { sinceClip: 2 }),
            picture: picks(all.concat([byId("drive:f1")]), {}, {}), pictureTurn: picks(all.concat([byId("drive:f1")]), {}, { sinceClip: 7 }),
            // only clips left to show: the rule gives way (never a blank screen, never the same slide again and again)
            onlyClips: picks(clips.concat([byId("fact-1944")]), {}, { recent: ["fact-1944"] }),
            inOrder,
          });""")
        clip_ids = ["drive:v1", "live:video:abc123", "video-gv-yt"]
        self.assertEqual(r["notYet"], ["fact-languages", "history-1944"])
        self.assertEqual(r["turn"], clip_ids)
        self.assertEqual(r["fresh"], clip_ids)
        self.assertEqual(r["welcomeNotYet"], ["auto:welcome"])
        self.assertEqual(r["welcomeTurn"], clip_ids)
        self.assertEqual(r["every12"], [["fact-languages", "history-1944"], clip_ids])
        self.assertEqual(r["every3"], clip_ids)
        self.assertEqual(r["picture"], ["drive:f1"])
        self.assertEqual(sorted(set(r["pictureTurn"]) - {"drive:f1"}), clip_ids)    # a picture or a clip: drawn by weight
        self.assertEqual(r["onlyClips"], clip_ids)
        self.assertEqual(r["inOrder"], ["live:video:abc123", "fact-1944", "video-gv-yt", "live:video:abc123", "fact-1944", "video-gv-yt"])

    def test_same_seed_same_show_and_next_is_pure(self):
        r = core(self, r"""
          const s = S(), p = G.pool(J, s, C);
          const ids = (seed) => run({}, 200, seed).picks.map((x) => x.id).join(" ");
          const st = G.newState(5), frozen = JSON.stringify(st);
          const r1 = G.next(st, p, s, C), r2 = G.next(st, p, s, C);
          const frozen2 = JSON.stringify(r1.state);
          G.next(r1.state, p, s, C);
          let later = r1.state;
          for (let i = 0; i < 10; i++) later = G.next(later, p, s, C).state;
          const restart = Object.assign({}, later, { firstQueue: null });
          out({ same: ids(42) === ids(42), differ: ids(42) !== ids(43), untouched: JSON.stringify(st) === frozen,
                untouched2: JSON.stringify(r1.state) === frozen2, repeat: r1.item.id === r2.item.id, first: r1.item.id, state: r1.state,
                fresh: G.newState(5), word: [G.newState("booth").seed === G.newState("booth").seed, G.newState("booth").seed !== G.newState("table").seed],
                noSeed: typeof G.newState().seed, garbage: G.next("x", p, s, C).item.id, stored: G.next(JSON.parse(frozen2), p, s, C).item.id === G.next(r1.state, p, s, C).item.id,
                restart: G.next(restart, p, s, C).item.id, normState: G.normState({ seed: 3, n: -2, recent: [1, "a", null], firstQueue: "x", lastType: "bogus", sincePlay: "9" }) });""")
        self.assertTrue(r["same"])
        self.assertTrue(r["differ"])
        self.assertTrue(r["untouched"])
        self.assertTrue(r["untouched2"])
        self.assertTrue(r["repeat"])                     # the same state → the same pick
        self.assertEqual(r["first"], "drive:p1")
        self.assertEqual(r["fresh"], {"seed": 5, "n": 0, "recent": [], "firstQueue": None, "lastType": None, "sinceWelcome": 0,
                                      "sinceAbout": 0, "sinceMedia": 0, "sinceClip": 0, "sincePlay": 0, "sinceList": 0, "langTurn": 0})
        st = r["state"]
        self.assertEqual((st["n"], st["recent"], st["firstQueue"], st["lastType"], st["sinceMedia"], st["sinceClip"], st["sincePlay"]),
                         (1, ["drive:p1"], ["drive:v2"], "poster", 0, 1, 1))     # a poster is a picture, not a clip
        self.assertEqual(r["word"], [True, True])
        self.assertEqual(r["noSeed"], "number")
        self.assertEqual(r["garbage"], "drive:p1")        # a broken stored state: a new show
        self.assertTrue(r["stored"])                      # a state that went through storage (JSON) picks the same
        self.assertEqual(r["restart"], "drive:p1")        # firstQueue null: the first items open the show again
        self.assertEqual(r["normState"], {"seed": 3, "n": 0, "recent": ["a"], "firstQueue": None, "lastType": None, "sinceWelcome": 0,
                                          "sinceAbout": 0, "sinceMedia": 0, "sinceClip": 0, "sincePlay": 0, "sinceList": 0, "langTurn": 0})

    def test_in_order_loops_in_the_csv_and_drive_order(self):
        show = sample_show()
        r = core(self, r"""
          const res = run({ order: "inorder" }, 150, 3);
          out({ picks: res.picks.map((x) => x.id), pool: res.pool });""", show=show)
        rest = [i for i in r["pool"] if not i.startswith("auto:")]
        order_of = {it["id"]: it["order"] for it in show["items"]}
        seq = sorted(rest, key=lambda i: (0, order_of[i], rest.index(i)) if order_of[i] is not None else (1, 0, rest.index(i)))
        self.assertEqual(seq[:2], ["drive:f1", "drive:p2"])            # the order numbers first (1, 2), then the show's order
        picks = r["picks"]
        self.assertEqual(picks[:2], ["drive:p1", "drive:v2"])          # the first items still open it
        body = [i for i in picks[2:] if not i.startswith("auto:")]
        k = seq.index("drive:v2")
        self.assertEqual(body, [seq[(k + 1 + j) % len(seq)] for j in range(len(body))])   # … then the order, looping
        self.assertGreater(len(body), len(seq))
        about = [i for i, x in enumerate(picks) if x == "auto:about"]
        self.assertEqual(about, [29, 59, 89, 119, 149])

    def test_boost(self):
        r = core(self, r"""
          const chan = (picks, c) => picks.filter((x) => byId(x.id) && byId(x.id).channel === c).length;
          const plainRun = run({}, 2000, 9).picks, boosted = run({ boost: { quiz: 3 } }, 2000, 9).picks;
          const party = run(G.preset("quizparty"), 2000, 9).picks;
          out({ plain: chan(plainRun, "quiz"), boosted: chan(boosted, "quiz"), plainPuzzles: chan(plainRun, "puzzles"),
                boostedPuzzles: chan(boosted, "puzzles"), partyPolls: chan(party, "polls"), plainPolls: chan(plainRun, "polls") });""")
        self.assertGreater(r["boosted"], r["plain"] * 1.15, r)
        self.assertLess(r["boostedPuzzles"], r["plainPuzzles"], r)     # the play slots go to the boosted channel
        self.assertLess(r["partyPolls"], r["plainPolls"], r)          # quiz party: quizzes and puzzles before polls

    def test_small_and_empty_pools(self):
        r = core(self, r"""
          const go = (p, n, part) => { let st = G.newState(2); const o = []; for (let i = 0; i < n; i++) { const x = G.next(st, p, S(part), C); st = x.state; o.push(x.item.id); } return o; };
          const allOff = {};
          G.CHANNELS.forEach((c) => { allOff[c.id] = false; });
          const offPool = G.pool(J, S({ channels: allOff }), C);
          out({
            three: go(["quiz-gvr", "quiz-app", "quiz-podcast"].map(byId), 30), one: go([byId("fact-1944")], 5),
            onlyAbout: go([G.autoItems(J, S())[0]], 3), welcomeAbout: go(G.autoItems(J, S({ event: { en: "X" } })), 6, { event: { en: "X" } }),
            firsts: go([byId("fact-1944"), Object.assign({}, byId("quiz-gvr"), { first: true, order: 5 }),
                        Object.assign({}, byId("fact-languages"), { first: true, order: 2 }), Object.assign({}, byId("prompt-first"), { first: true })], 3),
            empty: go([], 4), emptyEvent: go([], 6, { event: { en: "Fall Assembly" } }), fallback: G.next(G.newState(1), [], S(), C).item,
            garbagePool: go("x", 1), junk: go([null, 5, { id: "x", type: "bogus" }, { type: "fact" }], 2),
            offPool: offPool.length, offPick: go(offPool, 2),
          });""")
        three = r["three"]
        for i in range(2, len(three)):
            self.assertNotIn(three[i], three[i - 2:i], i)        # three quizzes: every one before any comes back
        self.assertEqual(r["one"], ["fact-1944"] * 5)
        self.assertEqual(r["onlyAbout"], ["auto:about"] * 3)
        self.assertEqual(r["welcomeAbout"], ["auto:welcome", "auto:about"] * 3)
        self.assertEqual(r["firsts"], ["fact-languages", "quiz-gvr", "prompt-first"])   # by order number, then the pool's order
        # never a blank screen: the about slide (and the welcome slide in turns when an event is set)
        self.assertEqual(r["empty"], ["auto:about"] * 4)
        self.assertEqual(r["emptyEvent"], ["auto:welcome", "auto:about"] * 3)
        f = r["fallback"]
        self.assertEqual((f["type"], f["qr"], f["en"]["text"]), ("about", None, "Not an official AA Grapevine, Inc. or A.A.W.S. display"))
        self.assertEqual(set(f.keys()), ITEM_KEYS)
        self.assertEqual((r["garbagePool"], r["junk"]), (["auto:about"], ["auto:about"] * 2))
        self.assertEqual((r["offPool"], r["offPick"]), (0, ["auto:about"] * 2))


def chars(it, lang, fields=("title", "text", "credit")):
    t = it[lang] or it["en" if lang == "es" else "es"]
    return sum(len(t[f]) for f in fields)


def read_time(n, both=False):
    return min(30, max(8, (6 + n / 12) * (1.7 if both else 1)))


class Timing(unittest.TestCase):
    def test_durations(self):
        show = sample_show()
        r = core(self, r"""
          const D = (id, part, l) => G.duration(typeof id === "string" ? byId(id) : id, S(part), l || "en");
          const fact = (text, extra) => Object.assign({}, byId("fact-languages"), { en: Object.assign({}, byId("fact-languages").en, { text }) }, extra || {});
          const long = fact("x".repeat(400)), short = fact("Hi");
          const own = (seconds) => Object.assign({}, byId("fact-1944"), { seconds });
          const [welcome, about] = G.autoItems(J, S({ event: { en: "X" } }));
          out({
            fact: [D("fact-1944"), D("fact-1944", { pace: "calm" }), D("fact-1944", { pace: "lively" }), D("fact-1944", {}, "both"), D("fact-1944", {}, "es")],
            long: [D(long), D(long, { pace: "calm" }), D(long, {}, "both")], short: [D(short), D(short, { pace: "lively" })],
            own: [D(own(20)), D(own(20), { pace: "calm" }), D(own(500)), D(own(1)), D(own("x"))],
            quiz: [D("quiz-gvr"), D("quiz-gvr", {}, "both"), D("quiz-podcast"), D("quiz-gvr", { reveal: 20 }), D("quiz-gvr", { pace: "calm" }),
                   D(Object.assign({}, byId("quiz-gvr"), { seconds: 10 })), D(Object.assign({}, byId("quiz-gvr"), { seconds: 40 }))],
            reveal: [G.revealAt(byId("quiz-gvr"), S(), "en"), G.revealAt(byId("quiz-podcast"), S(), "en"), G.revealAt(byId("quiz-gvr"), S({ pace: "calm" }), "en"),
                     G.revealAt(byId("quiz-gvr"), S({ reveal: 30, pace: "lively" }), "en"), G.revealAt(byId("tf-ads"), S(), "es"),
                     G.revealAt(byId("scramble-vine"), S(), "both"), G.revealAt(byId("fill-meeting"), S(), "en"),
                     G.revealAt(Object.assign({}, byId("quiz-gvr"), { reveal: 99 }), S(), "en"),
                     G.revealAt(byId("poll-format"), S(), "en"), G.revealAt(byId("fact-1944"), S(), "en"), G.revealAt(null, S(), "en")],
            fixed: [D("poll-format"), D("prompt-first"), D("qr-site"), D("drive:f1"), D("drive:f1", { photoSeconds: 5 }), D("drive:p2"), D("drive:p1"),
                    D("live:events:upcoming"), D("live:countdown:assembly"), D("live:prices:subs"), D("live:themes:next"), D("live:meetings:next"),
                    D(welcome), D(about), D("poll-format", { pace: "calm" })],
            media: [D("drive:v1"), D("drive:v2"), D("drive:v2", { mediaMax: 60 }), D("video-gv-yt"), D("video-lv-short"), D("video-lv-short", { webMediaMax: 45 }),
                    D("drive:a1"), D("live:podcast:ep1"), D("drive:v1", { pace: "calm" }), D(Object.assign({}, byId("drive:v2"), { seconds: 10 })),
                    D(Object.assign({}, byId("drive:v1"), { media: Object.assign({}, byId("drive:v1").media, { start: 50, end: 52 }) })),
                    D("video-gv-yt", { webMediaMax: 120 })],
            low: D("drive:f1", { photoSeconds: 3, pace: "lively" }), nul: G.duration(null, S(), "en"),
            image: [D("image-web"), D("image-web", {}, "both"), D(Object.assign({}, byId("image-web"), { en: Object.assign({}, byId("image-web").en, { text: "" }) }))],
          });""", show=show)
        it = {x["id"]: x for x in show["items"]}
        f = it["fact-1944"]
        n_en, n_es = chars(f, "en"), chars(f, "es")
        base = read_time(n_en)
        self.assertEqual(r["fact"], [js_round(base), js_round(base * 1.35), js_round(base * 0.75),
                                     js_round(read_time(max(n_en, n_es), True)), js_round(read_time(n_es))])
        self.assertGreater(r["fact"][3], r["fact"][0] * 1.5)          # both languages: × 1.7 (unless clamped)
        self.assertEqual(r["long"], [30, 40.5, 30])                   # 8–30 s, then × pace
        self.assertEqual(r["short"], [8, 6])
        self.assertEqual(r["own"], [20, 27, 180, js_round(max(5, 3)), js_round(base)])
        q = it["quiz-gvr"]
        ans_en = len(q["en"]["answer"]) + len(q["en"]["explain"])
        ans_es = len(q["es"]["answer"]) + len(q["es"]["explain"])
        self.assertEqual(r["quiz"][0], js_round(12 + 7 + ans_en / 12))
        self.assertEqual(r["quiz"][1], js_round(12 + 7 + max(ans_en, ans_es) / 12 * 1.7))
        qp = it["quiz-podcast"]
        self.assertEqual(r["quiz"][2], js_round(20 + 7 + (len(qp["en"]["answer"]) + len(qp["en"]["explain"])) / 12))
        self.assertEqual(r["quiz"][3], js_round(20 + 7 + ans_en / 12))
        self.assertEqual(r["quiz"][4], js_round(12 * 1.35 + (7 + ans_en / 12) * 1.35))
        self.assertEqual(r["quiz"][5:], [16, 40])                     # its own seconds — never before the reveal + 4 s
        self.assertEqual(r["reveal"], [12, 20, 16.2, 22.5, 12, 12, 12, 60, None, None, None])
        self.assertEqual(r["fixed"], [14, 14, 14, 8, 5, 12, 15, 15, 10, 15, 15, 15, 10, 12, 18.9])
        # media: the part between start and end, at most mediaMax (a file of the booth: 180 s) / webMediaMax (the web:
        # 90 s — video-gv-yt's 0:00–1:35 is cut there, all of it with 120); never × pace, never the item's seconds
        self.assertEqual(r["media"], [100, 180, 60, 90, 90, 45, 180, 90, 100, 180, 5, 95])
        self.assertEqual((r["low"], r["nul"]), (5, 8))
        img = it["image-web"]
        self.assertEqual(r["image"], [js_round(max(8, read_time(chars(img, "en")))),
                                      js_round(max(8, read_time(max(chars(img, "en"), chars(img, "es")), True))), 8])


class Puzzles(unittest.TestCase):
    def test_scramble(self):
        r = core(self, r"""
          const list = ["GRAPEVINE", "LA VIÑA", "STORY", "HISTORIA", "Carry the Message", "abc", "aab", "Viña", "AA", "ab"];
          out({
            res: list.map((w) => { const o = []; for (let s = 0; s < 200; s++) o.push(G.scramble(w, s)); return { w, o, again: G.scramble(w, 5) === G.scramble(w, 5), word: G.scramble(w) === G.scramble(w) }; }),
            same: [G.scramble("aaa", 1), G.scramble("a", 1), G.scramble("", 1), G.scramble(null, 1), G.scramble("a a", 3), G.scramble("AAA", 2)],
            nfd: G.scramble("viña", 4), words: G.scramble("GRAPEVINE", "booth") === G.scramble("GRAPEVINE", "booth"),
          });""")
        for x in r["res"]:
            w, outs = x["w"], x["o"]
            letters = sorted(c for c in w if not c.isspace())
            for o in outs:
                self.assertEqual(len(o), len(w))
                self.assertEqual([i for i, c in enumerate(o) if c == " "], [i for i, c in enumerate(w) if c == " "], (w, o))
                self.assertEqual(sorted(c for c in o if not c.isspace()), letters, (w, o))
                if len(letters) >= 3:
                    self.assertNotEqual(o.lower(), w.lower(), (w, o))   # never the word itself
            if len(set(letters)) > 1 and len(letters) >= 5:
                self.assertGreater(len(set(outs)), 20, w)              # a real shuffle, not one fixed answer
            self.assertTrue(x["again"] and x["word"], w)                # the same seed (or none: the word) → the same tiles
        self.assertEqual(r["res"][-2]["o"], ["AA"] * 200)                # two letters alike: nothing to shuffle
        self.assertEqual(set(r["res"][-1]["o"]), {"ba"})                 # two letters: swapped
        self.assertEqual(r["same"], ["aaa", "a", "", "", "a a", "AAA"])
        self.assertEqual(sorted(r["nfd"]), sorted("viña"))                # a combining tilde joins its letter first
        self.assertTrue(r["words"])

    def test_quiz_round(self):
        show = sample_show()
        r = core(self, r"""
          const p = G.pool(J, S({ sound: true }), C);
          const q = (l, n, rnd) => G.quizRound(p, l, n, rnd).map((it) => it.id);
          const broken = [Object.assign({}, byId("quiz-gvr"), { correct: 7 }), Object.assign({}, byId("tf-ads"), { correct: "false" }),
                          Object.assign({}, byId("fill-meeting"), { en: Object.assign({}, byId("fill-meeting").en, { answer: "" }) }),
                          Object.assign({}, byId("quiz-app"), { en: Object.assign({}, byId("quiz-app").en, { text: "" }) })];
          out({ en: q("en", 5, G.rng(1)), es: q("es", 50, G.rng(1)), both: q("both", 99, G.rng(2)), again: q("en", 5, G.rng(1)), seed: q("en", 5, 1),
                other: q("en", 5, G.rng(77)), dflt: G.quizRound(p, "en").length, dup: G.quizRound([byId("quiz-gvr"), byId("quiz-gvr")], "en", 5, G.rng(1)).map((it) => it.id),
                broken: G.quizRound(broken, "en", 5, G.rng(1)).length, none: [G.quizRound(null, "en", 5).length, G.quizRound("x", "es", 5).length] });""", show=show)
        langs = {it["id"]: it["langs"] for it in show["items"] if it["type"] in ("quiz", "truefalse", "fill")}
        en_ok = {i for i, ls in langs.items() if "en" in ls}
        es_ok = {i for i, ls in langs.items() if "es" in ls}
        self.assertEqual(len(r["en"]), 5)
        self.assertEqual(len(set(r["en"])), 5)
        self.assertTrue(set(r["en"]) <= en_ok)
        self.assertEqual(set(r["es"]), es_ok)                 # all of them when n is larger (no scramble, no poll)
        self.assertEqual(set(r["both"]), en_ok | es_ok)
        self.assertEqual(r["again"], r["en"])
        self.assertEqual(r["seed"], r["en"])                  # a seed works like GVB.rng(seed)
        self.assertNotEqual(r["other"], r["en"])
        self.assertEqual(r["dflt"], 5)
        self.assertEqual(r["dup"], ["quiz-gvr"])
        self.assertEqual(r["broken"], 0)                      # no right choice, no answer, no question: not playable
        self.assertEqual(r["none"], [0, 0])

    def test_polls(self):
        r = core(self, r"""
          const p0 = { "poll-format": [1, 0, 2] };
          const p1 = G.tally(p0, "poll-format", 1), p2 = G.tally(p1, "poll-story", 0);
          const six = { id: "poll-six", type: "poll", en: { choices: ["a", "b", "c", "d", "e", "f"] }, es: null };
          const vectors = [[1, 1, 1, 1, 1, 1], [1, 2, 4, 0, 0, 0], [7, 0, 0, 0, 0, 0], [5, 3, 1, 1, 1, 0], [999, 1, 1, 0, 0, 0], [2, 2, 2, 1, 0, 0]];
          out({
            p0, p1, p2, fresh: G.tally("garbage", "poll-story", 1),
            bad: [G.tally(p0, "poll-format", 6), G.tally(p0, "poll-format", -1), G.tally(p0, "poll-format", 1.5), G.tally(p0, "bad id!", 0), G.tally(p0, null, 0), G.tally(p0, "poll-format", "x")],
            norm: G.normPolls({ "poll-format": [1, -3, "x", 2.7, 9e9, 1, 1, 1], "bad id!": [1], "poll-story": "x" }),
            res: [G.pollResults({ "poll-format": [1, 1, 1] }, byId("poll-format")), G.pollResults({ "poll-format": [2, 1] }, byId("poll-format")),
                  G.pollResults({}, byId("poll-format")), G.pollResults({ "poll-story": [3, 0] }, byId("poll-story")), G.pollResults(p0, null),
                  G.pollResults({ "poll-format": [1, 2, 3, 4, 5, 6] }, byId("poll-format")), G.pollResults("garbage", byId("poll-story"))],
            sums: vectors.map((v) => G.pollResults({ "poll-six": v }, six)), vectors,
          });""")
        self.assertEqual(r["p0"], {"poll-format": [1, 0, 2]})            # the votes passed in are not changed
        self.assertEqual(r["p1"], {"poll-format": [1, 1, 2]})
        self.assertEqual(r["p2"], {"poll-format": [1, 1, 2], "poll-story": [1]})
        self.assertEqual(r["fresh"], {"poll-story": [0, 1]})
        self.assertEqual(r["bad"], [{"poll-format": [1, 0, 2]}] * 6)
        self.assertEqual(r["norm"], {"poll-format": [1, 0, 0, 2, 1000000, 1]})
        cp = lambda counts, pcts: [{"count": c, "pct": p} for c, p in zip(counts, pcts)]  # noqa: E731
        self.assertEqual(r["res"], [cp([1, 1, 1], [34, 33, 33]), cp([2, 1, 0], [67, 33, 0]), cp([0, 0, 0], [0, 0, 0]),
                                    cp([3, 0], [100, 0]), [], cp([1, 2, 3], [17, 33, 50]), cp([0, 0], [0, 0])])
        for v, res in zip(r["vectors"], r["sums"]):
            self.assertEqual([x["count"] for x in res], v)
            self.assertEqual(sum(x["pct"] for x in res), 100, res)
            total = sum(v)
            for c, x in zip(v, res):
                self.assertLess(abs(x["pct"] - c * 100 / total), 1, res)
                if not c:
                    self.assertEqual(x["pct"], 0)


class Offline(unittest.TestCase):
    def test_save_list(self):
        show = sample_show()
        r = core(self, r"""
          const s = S();
          const abs = { site: J.site, items: [Object.assign({}, byId("drive:f1"), { media: Object.assign({}, byId("drive:f1").media,
                         { src: "https://neta65.github.io/aagrapevine/about/booth/media/x.jpg", poster: "https://other.example/x.jpg" }) }),
                       Object.assign({}, byId("drive:f2"), { media: Object.assign({}, byId("drive:f2").media, { src: "//evil.example/x.jpg" }) })] };
          out({ dflt: G.saveList(J, s, "/aagrapevine/"), noBase: G.saveList(J, s), es: G.saveList(J, S({ lang: "es" }), "/aagrapevine/"),
                quick: G.saveList(J, S({ lang: "en", sound: false }), "/aagrapevine/"),
                off: G.saveList(J, S({ channels: { posters: false }, items: { "drive:f1": false }, pubs: { lv: false } }), "/aagrapevine/"),
                switches: [S({ channels: { videos: false, sounds: false, "live-podcast": false, "live-events": false } }), S({ pubs: { gv: false } }),
                           S({ collections: { main: false, "spring-assembly-2027": false } }), S({ tags: { history: false } }),
                           S({ items: { "drive:v1": false, "drive:p3": false, "live:events:upcoming": false } }),
                           S({ pubs: { gv: false, lv: false } })].map((x) => G.saveList(J, x, "/aagrapevine/")),
                // an item that cannot show at all (an unknown type, a photo without its picture) is still left out
                broken: G.saveList({ site: J.site, items: [Object.assign({}, byId("drive:f1"), { type: "hologram" }), byId("drive:f2"),
                                                           Object.assign({}, byId("drive:f3"), { media: null })] }, s),
                abs: G.saveList(abs, s), empty: G.saveList(null, s, "aagrapevine"), root: G.saveList({ items: [] }, s) });""", show=show)

        def expected(skip=lambda it: False):
            out = [BASE + "about/", BASE + "es/about/", BASE + "about/booth.json"]
            for it in show["items"]:
                if skip(it):
                    continue
                urls = []
                if it["media"]:
                    urls += [it["media"]["src"], it["media"]["poster"]]
                for lang in ("en", "es"):
                    if it[lang]:
                        urls += [row.get("thumb") for row in it[lang]["rows"]]
                for u in urls:
                    if u and u.startswith("/") and u not in out:
                        out.append(u)
            return out
        everything = expected()
        self.assertEqual(r["dflt"], everything)
        self.assertIn(BASE + "about/booth/media/ii99-poster.jpg", everything)        # a video's poster
        self.assertIn(BASE + "assets/cache/flyers/taller.jpg", everything)            # a list's thumb, once
        self.assertIn(BASE + "assets/cache/podcast/ep1.jpg", everything)              # a muted, online item's poster
        self.assertIn(BASE + "about/booth/media/ff66-taller.jpg", everything)         # an item outside its dates
        self.assertFalse([u for u in everything if "youtube" in u or u.startswith("https:")])
        self.assertEqual(r["noBase"], everything)                 # the base from booth.json's site
        self.assertEqual(r["es"], everything)                     # a language switch at the table never misses a file
        self.assertEqual(r["quick"], everything)
        # nor a switched-off channel, item, magazine, collection or tag: their files stay in the copy (a save — Start,
        # new content, the connection back — prunes what the list leaves out), so turning one back on at an offline
        # venue still finds its posters and videos
        self.assertEqual(r["off"], everything)
        self.assertEqual(r["switches"], [everything] * 6)
        self.assertEqual(r["broken"], [BASE + "about/", BASE + "es/about/", BASE + "about/booth.json", BASE + "about/booth/media/ee55-img.jpg"])
        self.assertEqual(r["abs"], [BASE + "about/", BASE + "es/about/", BASE + "about/booth.json", BASE + "about/booth/media/x.jpg"])
        self.assertEqual(r["empty"], ["/aagrapevine/about/", "/aagrapevine/es/about/", "/aagrapevine/about/booth.json"])
        self.assertEqual(r["root"], ["/about/", "/es/about/", "/about/booth.json"])


class Clock(unittest.TestCase):
    DAYS = [("2026-01-15T05:59:00Z", "2026-01-14"), ("2026-01-15T06:00:00Z", "2026-01-15"),
            ("2026-03-08T05:30:00Z", "2026-03-07"), ("2026-03-09T05:30:00Z", "2026-03-09"),   # daylight time from Mar 8
            ("2026-07-04T04:59:00Z", "2026-07-03"), ("2026-07-04T05:00:00Z", "2026-07-04"),
            ("2026-10-03T04:30:00Z", "2026-10-02"), ("2026-11-01T05:30:00Z", "2026-11-01"),
            ("2026-11-02T05:30:00Z", "2026-11-01"), ("2026-11-02T06:00:00Z", "2026-11-02"),   # standard time from Nov 1
            ("2027-01-01T05:59:00Z", "2026-12-31"), ("2027-01-01T06:00:00Z", "2027-01-01"),
            ("2027-03-14T05:30:00Z", "2027-03-13"), ("2027-03-15T05:30:00Z", "2027-03-15")]

    def test_the_day_is_the_sites_zone(self):
        # config/site.yml site.timezone → window.SITE.tz (base.njk): the booth's "today" is the day there; without a
        # page (Node) or a zone, Central time
        r = core(self, r"""
          const at = Date.parse("2026-10-31T12:00:00Z");                    // Oct 31 in Central time, Nov 1 on Kiritimati
          const res = {};
          for (const tz of ["Pacific/Kiritimati", "America/Chicago", ""]) {
            const c = vm.createContext({ console, SITE: tz ? { tz } : {} });
            vm.runInContext(fs.readFileSync("src/assets/js/booth-core.js", "utf8"), c);
            res[tz || "none"] = [c.GVB.TZ, c.GVB.dayCentral(at)];
          }
          out(res);""")
        self.assertEqual(r, {"Pacific/Kiritimati": ["Pacific/Kiritimati", "2026-11-01"], "America/Chicago": ["America/Chicago", "2026-10-31"],
                             "none": ["America/Chicago", "2026-10-31"]})
        # booth.js and presentations.js write their dates in the site's zone too (never a fixed "America/Chicago")
        for f in ("booth.js", "presentations.js"):
            src = (ROOT / "src" / "assets" / "js" / f).read_text(encoding="utf-8")
            self.assertNotIn('timeZone: "America/Chicago"', src, f)
            self.assertNotRegex(src, r'"UTC" : "America/Chicago"', f)

    def test_central_day_with_and_without_intl(self):
        r = core(self, r"""
          const t = input.days.map((d) => Date.parse(d[0]));
          const bare = vm.createContext({ console });
          vm.runInContext("delete globalThis.Intl;", bare);
          vm.runInContext(fs.readFileSync("src/assets/js/booth-core.js", "utf8"), bare);
          const c = G.ctx();
          out({ intl: t.map((x) => G.dayCentral(x)), noIntl: t.map((x) => bare.GVB.dayCentral(x)), gone: vm.runInContext("typeof Intl", bare),
                ctx: G.ctx({ now: Date.parse("2026-10-03T04:30:00Z"), online: false, page: "es" }), dflt: [typeof c.now, c.online, c.page, /^\d{4}-\d{2}-\d{2}$/.test(c.today)],
                date: G.ctx({ now: new Date(Date.parse("2026-10-02T15:00:00Z")) }).today, odd: G.ctx({ online: "no", page: "fr", youtube: false, failed: { a: true } }),
                today: /^\d{4}-\d{2}-\d{2}$/.test(G.dayCentral()) });""", data={"days": self.DAYS})
        days = [d[1] for d in self.DAYS]
        self.assertEqual(r["intl"], days)
        self.assertEqual(r["gone"], "undefined")
        self.assertEqual(r["noIntl"], days)                       # the U.S. daylight-time rule by hand
        self.assertEqual(r["ctx"], {"now": ms("2026-10-03T04:30:00.000Z"), "today": "2026-10-02", "online": False, "page": "es"})
        self.assertEqual(r["dflt"], ["number", True, "en", True])
        self.assertEqual(r["date"], "2026-10-02")
        self.assertEqual((r["odd"]["online"], r["odd"]["page"], r["odd"]["youtube"], r["odd"]["failed"]), (True, "en", False, {"a": True}))
        self.assertTrue(r["today"])

    def test_rng_is_mulberry32(self):
        r = core(self, r"""
          const a = G.rng(1), b = G.rng(1), c = G.rng(2), w = G.rng("booth");
          const xs = []; for (let i = 0; i < 1000; i++) xs.push(a());
          const ys = []; for (let i = 0; i < 1000; i++) ys.push(b());
          out({ same: xs.join() === ys.join(), first: G.rng(1)(), other: c() !== G.rng(1)(), range: xs.every((x) => x >= 0 && x < 1),
                mean: xs.reduce((p, x) => p + x, 0) / xs.length, word: w() === G.rng("booth")(), odd: [G.rng(null)(), G.rng(-1)() === G.rng(1)()] });""")
        self.assertTrue(r["same"] and r["other"] and r["range"] and r["word"])
        self.assertAlmostEqual(r["first"], 0.6270739405881613)      # mulberry32(1)'s first number
        self.assertTrue(0.45 < r["mean"] < 0.55)
        self.assertTrue(0 <= r["odd"][0] < 1)
        self.assertTrue(r["odd"][1])


class Module(unittest.TestCase):
    API = ["DEFAULTS", "CHANNELS", "TYPES", "withDefaults", "normSettings", "diff", "encode", "decode", "preset", "rng",
           "dayCentral", "ctx", "autoItems", "why", "pool", "newState", "next", "lang", "text", "fill", "qrOf", "duration",
           "revealAt", "scramble", "quizRound", "tally", "pollResults", "saveList", "fmt"]

    def test_module_shape_and_plain_script(self):
        r = core(self, r"""
          const w = {};
          vm.runInContext(fs.readFileSync("src/assets/js/booth-core.js", "utf8"), vm.createContext({ window: w }));
          const d = G.DEFAULTS; d.channels.quiz = false; d.lang = "es";
          out({ keys: Object.keys(G), browser: Object.keys(w.GVB).length === Object.keys(G).length,
                untouched: [G.normSettings({}).channels.quiz, G.normSettings({}).lang, G.DEFAULTS === d],
                words: G.WORDS, reasons: G.REASONS, keysNames: [G.STORAGE_KEY, G.POLLS_KEY, G.STATE_KEY] });""")
        for name in self.API:
            self.assertIn(name, r["keys"])
        self.assertTrue(r["browser"])                            # window.GVB in a browser
        self.assertEqual(r["untouched"], [True, "both", True])   # changing GVB.DEFAULTS cannot change the core's own
        self.assertEqual(r["reasons"], ["off", "channel", "pub", "collection", "tag", "date", "over", "lang", "offline", "muted", "media"])
        self.assertEqual(r["keysNames"], ["gv-booth-v1", "gv-booth-polls-v1", "gv-booth-state-v1"])
        shown = " ".join(v for lang in r["words"].values() for v in lang.values())
        self.assertNotIn("PDF", shown.upper())                    # what a visitor reads: never "PDF"
        src = (ROOT / CORE).read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = "\n".join(line.split("//")[0] if not re.search(r"https?:\\?/", line) else line for line in code.splitlines())
        # old Safari: no optional chaining, no ??, no modules, no arrow functions or let / const in this file
        self.assertNotRegex(code, r"\?\.[A-Za-z_(\[]|\?\?|^\s*(import|export)\s")
        for bad in ("=>", "let ", "const ", "class ", "async ", "document", "localStorage", "sessionStorage", "fetch(",
                    "navigator", "XMLHttpRequest", "indexedDB", "location"):
            self.assertNotIn(bad, code, bad)
        self.assertIn('typeof window !== "undefined" ? window : globalThis', code)
