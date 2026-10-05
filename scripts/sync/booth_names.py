"""The booth display's Drive files: what a file's NAME says about how the booth shows it.

The committee's Drive panel folder has a `booth/` folder (any of these names works, capitals and accents
ignored, as for every category in drive.CATEGORY_SYNONYMS: booth, mesa, kiosk / kiosko / kiosco, display /
pantalla, stand, exhibit / exhibición — singular or plural) for the booth display on the About page
(/about/#booth: a show that plays by itself at our table at assemblies and conventions). Its sub-folders are
COLLECTIONS — "booth/Spring Assembly 2027/" is the collection "spring-assembly-2027", which the player's
settings switch on or off (all on by default); a deeper sub-folder belongs to its top collection. drive.py
gives such a file `category: "booth"` and `extra.booth` = parse_booth_name(…) below; build_data puts it in
data/site/booth.json and in NO other site file (docs/DATA_SCHEMA.md → booth.json).

    [order] [magazine] [language] Title [(option) (option) …].ext       every part optional but the title

    GV EN Welcome to our table (first) (15s).png        poster · Grapevine · English · first · 15 seconds
    LV ES Testimonio - Mi primer número (0:05-1:45).mp4  video · La Viña · Spanish · plays 0:05 to 1:45
    02 GVLV Our booth at CityWide Dallas.jpg             photo · both magazines · any language · order 2
    [LV][ES] Cita (10s) (muted).mp4                      video · La Viña · Spanish · never its sound

  order     a leading number of 1–3 digits and a separator ("01 ", "02-", "3_"): the place in the player's
            "In order" mode, never shown. A 4-digit year or a date at the start is not an order ("2027 Spring
            Assembly", "10-26-2026 Taller"), nor a number that counts something ("12 Steps poster", "3 ways to
            carry the message", "1 Step at a time") — write it with a leading zero to make it one ("01 …").
  magazine  GV = Grapevine, LV = La Viña, GVLV / GV-LV / GV+LV / GV&LV / GV/LV / GV LV / AA = both (the
            default): the slide's colour (Grapevine blue, La Viña amber, both grape) and the player's
            "Grapevine / La Viña" filter. A leading word (any capitals), or in parentheses / brackets anywhere:
            "(LV)", "[GV]", "(AA)" — there "Grapevine" and "La Viña" work too. A leading AA only right before a
            language code ("AA EN Welcome"): otherwise it is the title's first word ("AA Preamble.png").
  language  EN (English, Inglés) / ES (Spanish, Español) / BI or EN-ES (bilingual: spoken or written in both).
            No language = shown in every language mode (photos, music, pictures without words); a file marked
            EN plays in the English, Both and Alternate modes, not in Spanish-only mode (and the other way
            round). As a leading word only in CAPITALS — "EN", "ES", "BI" — so the Spanish "En la mesa de
            Tyler" and "Es hora de servir" stay titles; the full words ("English", "Español") as a leading
            word only right after the magazine ("GV English Welcome"). In parentheses / brackets any capitals
            ("(es)", "[English]", "(en español)").
            Leading words count only BEFORE the title starts: "Esto ES La Viña.jpg" keeps "ES" in its title,
            "AA Preamble.png" its "AA".
  Title     the rest of the name, tidied like other Drive files (drive.tidy: underscores → spaces, "GV_LV" →
            "GV/LV"; "Copy of" / "Copia de" and a copy's " (1)" dropped): the caption (a message's heading).
            A camera name says nothing (drive.is_generic_media_name: IMG_1234, PXL_…, DSC…, WhatsApp Image …,
            Screenshot …, a bare number) → no caption.

  Options — in parentheses or brackets, in any order, English or Spanish, any capitals; several in one pair
  work too ("(first, 15s)", "(GV EN)"). Anything else in parentheses stays in the title ("(from the Chair)",
  "(parte 2)", "(until further notice)"):

    (poster) (cartel) (afiche)       the whole picture, never cropped, on a blurred copy of itself — the
                                     default for .png .gif .webp .svg .bmp, for documents (Drive's picture of
                                     page 1) and for videos
    (photo) (foto)                   fill the screen, with a slow zoom — the default for .jpg .jpeg .heic
                                     .heif .tif .tiff (on a video: fill the screen)
    (10s) (10 s) (10 sec) (10 seg)   seconds on screen of a photo, poster or message: 3–120 ((2 min) works
    (10 seconds) (10 segundos)       too); ignored for a video or sound file, which plays its own length
    (0:15-1:30) (15-90) (0:15-)      play only this part of a video / sound file: start-end in m:ss (or
    (0:15–1:30) (0:15 a 1:30)        h:mm:ss) or in seconds; no end = to its end. Plain seconds only on a
                                     video or sound file (on a picture "(15-90)" is part of the title)
    (muted) (mute) (silent)          never play this file's sound
    (sin sonido) (silencio)
    (x2) … (x5) (2x) (×3)            shown 2–5 times as often
    (rare) (sometimes) (poco)        shown half as often
    (a veces)
    (first) (primero) (primera)      shown FIRST when the show starts (and after the settings change)
    (from 2027-03-01) (desde …)      only from that day — any date common.date_from_text reads ("March 1,
                                     2027", "1 de marzo de 2027", "03/01/2027" …); a month alone ("(from
                                     March 2027)") is its first day
    (until 2027-03-15) (hasta …)     only until that day, inclusive (a month alone: its last day); after it
                                     build_data leaves the file out of data/site/booth.json
    (no caption) (no text)           the picture / video without its title; a message without its heading
    (sin texto) (sin título)
    (off) (apagado) (draft)          kept in the folder, never shown (not even listed as a problem)
    (borrador)
  A name starting with "_" or "~" is never shown either: notes for the committee ("_README naming.txt").

  File types — by the MIME type Drive gives, else by the extension:
    photo / poster  pictures: jpg jpeg png gif webp heic heif tif tiff bmp svg (HEIC & co are shown through
                    Google's converted copy); documents shown as Drive's picture of their first page: PDF,
                    PowerPoint (ppt pptx pps ppsx), Keynote, OpenDocument presentation, Google Slides, Google
                    Drawings
    video           mp4 (best: H.264 video + AAC sound), m4v, webm, mov (only H.264 plays everywhere)
    audio           mp3 m4a aac wav ogg oga opus — played only while the booth's sound is on
    message         txt md, Google Docs, docx: the title is the heading, the file's text the body (drive.py
                    fetches it like a bulletin post's; message_text below keeps it Markdown-light)
    unsupported     anything else — zip, a form, a shortcut Drive would not follow, a video or sound type
                    browsers do not play (avi, wmv, mkv, wma …): never shown, listed as a problem (with what to
                    do) in data/site/booth.json → the Actions run summary and the player's Items list

The rules for the folder itself (no faces or full names of AA members, no Grapevine / La Viña logos, covers,
artwork, cartoons or their audio / video files — official videos go into content/booth/booth.csv as YouTube
links — only material the committee made or may use; everything in it is public) are in content/booth/README.md
and the About page's "How to use it at a booth".

parse_booth_name(name, mime, path) → the `extra.booth` dict of a raw Drive item. Pure: no I/O, no clock (a
past "until" day is build_data's business). message_text(markdown) → a message's body as the player shows it.
tests/test_booth_names.py has every example of the design and many more.
"""
from __future__ import annotations

import calendar
import re
import unicodedata

from .common import MONTHS, slugify
# drive.py's own name helpers, so a booth file's title is tidied exactly like every other Drive file's. (drive.py
# imports this module inside the functions that need it, not at its top, so the two never import each other
# half-way.)
from .drive import _COPY_PREFIX, _COPY_SUFFIX, is_generic_media_name, name_date, tidy

BOOTH_CATEGORY = "booth"         # drive.CATEGORY_SYNONYMS key of the booth folder
MAIN = "main"                    # the collection of the files directly in the booth folder
MAIN_LABEL = "Booth folder"      # its label (the player names it in the page language itself)
TEXT_MAX = 1200                  # characters of a message's text kept (the player shows about the first 600)
SECONDS_MIN, SECONDS_MAX = 3, 120
WEIGHT_MAX = 5

# Why a file cannot be shown — (English, Spanish), by code. extra.booth.problem holds the English words;
# data/site/booth.json `problems` gives both languages and the code (PROBLEM_CODES finds it from the words).
PROBLEMS: dict[str, tuple[str, str]] = {
    "unsupported": ("not a type the booth can show",
                    "no es un tipo de archivo que la pantalla de la mesa pueda mostrar"),
    "video-type": ("a video type browsers do not play — save it as .mp4 (H.264 video, AAC sound)",
                   "un tipo de video que los navegadores no reproducen: guárdalo como .mp4 (video H.264, sonido AAC)"),
    "audio-type": ("a sound type browsers do not play — save it as .mp3 or .m4a",
                   "un tipo de sonido que los navegadores no reproducen: guárdalo como .mp3 o .m4a"),
    "no-text": ("no text to show — the file is empty, or its text could not be read yet",
                "no hay texto que mostrar: el archivo está vacío o todavía no se pudo leer su texto"),
    "dates": ("its days never meet — the (from …) day is after the (until …) day",
              "sus fechas nunca coinciden: el día de (desde …) es posterior al de (hasta …)"),
}
PROBLEM_CODES = {en: code for code, (en, _es) in PROBLEMS.items()}

# --------------------------------------------------------------------------- file types
# What a file is, from its MIME type (Drive's), else its extension: a picture's default kind ("photo" fills the
# screen, "poster" shows it whole), "page" (a document shown as the picture of its first page → poster),
# "video", "audio", "text" (→ message), or a problem code (PROBLEMS).
_PICTURE_MIME = {
    "image/jpeg": "photo", "image/pjpeg": "photo", "image/heic": "photo", "image/heif": "photo",
    "image/heic-sequence": "photo", "image/heif-sequence": "photo", "image/tiff": "photo",
    "image/png": "poster", "image/gif": "poster", "image/webp": "poster", "image/svg+xml": "poster",
    "image/bmp": "poster", "image/x-ms-bmp": "poster",
}
_VIDEO_MIME = {"video/mp4", "video/x-m4v", "video/webm", "video/quicktime"}
_AUDIO_MIME = {"audio/mpeg", "audio/mp3", "audio/mpeg3", "audio/x-mpeg-3", "audio/mp4", "audio/m4a", "audio/x-m4a",
               "audio/aac", "audio/x-aac", "audio/aacp", "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave",
               "audio/ogg", "audio/opus", "audio/x-opus+ogg"}
_PAGE_MIME = {
    "application/pdf", "application/vnd.google-apps.presentation", "application/vnd.google-apps.drawing",
    "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.slideshow", "application/vnd.apple.keynote",
    "application/x-iwork-keynote-sffkey", "application/vnd.oasis.opendocument.presentation",
}
_TEXT_MIME = {"application/vnd.google-apps.document", "text/plain", "text/markdown", "text/x-markdown",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
_EXT = {
    "jpg": "photo", "jpeg": "photo", "jfif": "photo", "heic": "photo", "heif": "photo", "tif": "photo",
    "tiff": "photo", "png": "poster", "gif": "poster", "webp": "poster", "svg": "poster", "bmp": "poster",
    "pdf": "page", "ppt": "page", "pptx": "page", "pps": "page", "ppsx": "page", "key": "page", "odp": "page",
    "mp4": "video", "m4v": "video", "webm": "video", "mov": "video",
    "mp3": "audio", "m4a": "audio", "aac": "audio", "wav": "audio", "ogg": "audio", "oga": "audio", "opus": "audio",
    "txt": "text", "md": "text", "markdown": "text", "docx": "text",
    # known, but no browser plays them: say what to do
    "avi": "video-type", "wmv": "video-type", "mkv": "video-type", "3gp": "video-type", "flv": "video-type",
    "mpg": "video-type", "mpeg": "video-type", "mts": "video-type",
    "wma": "audio-type", "aif": "audio-type", "aiff": "audio-type", "amr": "audio-type", "mid": "audio-type",
    "midi": "audio-type", "flac": "audio-type",
    # known types the booth cannot show (only taken off the title)
    "doc": "unsupported", "rtf": "unsupported", "odt": "unsupported", "pages": "unsupported",
    "zip": "unsupported", "epub": "unsupported", "html": "unsupported", "htm": "unsupported",
}
_EXT_RE = re.compile(r"(?i)\.(" + "|".join(sorted(_EXT, key=len, reverse=True)) + r")$")


def extension(name: str) -> str:
    """'Welcome.JPG' → 'jpg' ('' when the name has no extension the booth knows)."""
    m = _EXT_RE.search(name or "")
    return m.group(1).lower() if m else ""


def media_type(mime: str | None, name: str) -> str:
    """What a file is for the booth: photo · poster · page · video · audio · text, or a problem code
    (unsupported · video-type · audio-type). A MIME type the booth knows decides; else the extension (Drive
    gives none, or only "application/octet-stream"); else an unknown video / sound type says what to do."""
    m = (mime or "").lower().split(";")[0].strip()
    if m in _PICTURE_MIME:
        return _PICTURE_MIME[m]
    if m in _VIDEO_MIME:
        return "video"
    if m in _AUDIO_MIME:
        return "audio"
    if m in _PAGE_MIME:
        return "page"
    if m in _TEXT_MIME:
        return "text"
    if "google-apps" in m:            # a form, a site, a folder shortcut, a shortcut Drive would not follow …
        return "unsupported"
    by_ext = _EXT.get(extension(name))
    if by_ext:
        return by_ext
    if m.startswith("video/"):
        return "video-type"
    if m.startswith("audio/"):
        return "audio-type"
    return "unsupported"


# --------------------------------------------------------------------------- options
def _fold(s: str) -> str:
    """Lower case, accents off, spaces evened: '(Sin  Título)' → 'sin titulo'. Punctuation stays ("0:15-1:30")."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


# Word options (folded) → the settings they give. Each value is copied before use (_option), never changed.
_WORD_OPTIONS: dict[str, dict] = {
    **dict.fromkeys(("poster", "cartel", "afiche"), {"fit": "contain"}),
    **dict.fromkeys(("photo", "foto"), {"fit": "cover"}),
    **dict.fromkeys(("muted", "mute", "silent", "sin sonido", "silencio"), {"muted": True}),
    **dict.fromkeys(("rare", "sometimes", "poco", "a veces"), {"weight": 0.5}),
    **dict.fromkeys(("first", "primero", "primera"), {"first": True}),
    **dict.fromkeys(("no caption", "no text", "no title", "sin texto", "sin titulo"), {"caption": False}),
    **dict.fromkeys(("off", "apagado", "draft", "borrador"), {"off": True}),
}
_LANG_WORDS = {"en": "en", "eng": "en", "english": "en", "ingles": "en",
               "es": "es", "esp": "es", "spanish": "es", "espanol": "es", "castellano": "es",
               "bi": "both", "bilingual": "both", "bilingue": "both"}
_SECONDS = re.compile(r"(\d{1,3})\s*(?:s|secs?|seconds?|segs?|segundos?)\.?")
_MINUTES = re.compile(r"(\d{1,2})\s*(?:mins?|minutes?|minutos?)\.?")
_WEIGHT = re.compile(r"[x×]\s*(\d{1,2})|(\d{1,2})\s*[x×]")
_CLOCK = r"(?:\d{1,2}:)?\d{1,2}:[0-5]\d"                       # m:ss or h:mm:ss
_RANGE = re.compile(rf"({_CLOCK}|\d{{1,5}})\s*(?:[-–—]|\b(?:to|a|hasta)\b)\s*({_CLOCK}|\d{{1,5}})?")
_FROM = re.compile(r"(?:from|starting|desde|a partir del?)\s*:?\s+(.+)")
_UNTIL = re.compile(r"(?:until|till|through|thru|expires?|hasta|vence)\s*:?\s+(.+)")
_GROUP = re.compile(r"\(([^()\[\]]*)\)|\[([^()\[\]]*)\]")


def _magazines(t: str) -> set[str] | None:
    """'gv' · 'grapevine' · 'la vina' · 'gv-lv' · 'aa' (folded) → {"gv"} · {"lv"} · {"gv", "lv"}; None when it is
    not (only) magazines."""
    t = t.replace("aa grapevine", "grapevine").replace("la vina", "lavina")
    words = [w for w in re.split(r"[\s\-+&/]+", t) if w and w not in ("and", "y")]
    pubs: set[str] = set()
    for w in words:
        if w in ("gv", "grapevine"):
            pubs.add("gv")
        elif w in ("lv", "lavina"):
            pubs.add("lv")
        elif w in ("gvlv", "lvgv", "aa"):
            pubs |= {"gv", "lv"}
        else:
            return None
    return pubs or None


def _languages(t: str) -> set[str] | None:
    """'en' · 'español' · 'en-es' · 'bilingüe' · 'en español' · 'in English' (folded) → {"en"} · {"es"} ·
    {"en", "es"}; None when it is not (only) languages. ("en" before a language's name is the Spanish "in".)"""
    t = re.sub(r"^(?:en|in)\s+(?=(?:english|ingles|spanish|espanol|castellano|bilingual|bilingue)\b)", "", t)
    words = [w for w in re.split(r"[\s\-+&/]+", t) if w and w not in ("and", "y")]
    langs: set[str] = set()
    for w in words:
        v = _LANG_WORDS.get(w)
        if v is None:
            return None
        langs |= {"en", "es"} if v == "both" else {v}
    return langs or None


def _secs(v: str) -> int:
    """'0:05' → 5 · '1:45' → 105 · '1:02:03' → 3723 · '90' → 90."""
    total = 0
    for part in v.split(":"):
        total = total * 60 + int(part)
    return total


def _day(text: str, last: bool) -> str | None:
    """A date as common.date_from_text reads it → 'YYYY-MM-DD'. A month alone ("March 2027") is its first day,
    or its last one when `last` (an "until" day). None when the text holds no full date ("March 15" — no year
    —, "the Chair", "further notice")."""
    iso, _rest, explicit = name_date(text)
    if not iso:
        return None
    if last and not explicit:
        y, m = int(iso[:4]), int(iso[5:7])
        return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
    return iso


def _option(part: str, media: bool) -> dict | None:
    """One option (folded text) → the settings it gives ({"fit": …}, {"pubs": {…}}, {"range": (a, b)} …), or
    None when it is not an option. `media`: the file is a video or sound file (plain-seconds ranges count)."""
    if part in _WORD_OPTIONS:
        return dict(_WORD_OPTIONS[part])
    pubs = _magazines(part)
    if pubs:
        return {"pubs": pubs}
    langs = _languages(part)
    if langs:
        return {"langs": langs}
    m = _SECONDS.fullmatch(part)
    if m:
        return {"seconds": int(m[1])}
    m = _MINUTES.fullmatch(part)
    if m:
        return {"seconds": int(m[1]) * 60}
    m = _WEIGHT.fullmatch(part)
    if m:
        return {"weight": int(m[1] or m[2])}
    m = _RANGE.fullmatch(part)
    if m and (media or (":" in m[1] and (m[2] is None or ":" in m[2]))):
        return {"range": (_secs(m[1]), _secs(m[2]) if m[2] else None)}
    m = _FROM.fullmatch(part)
    day = _day(m[1], last=False) if m else None
    if day:
        return {"from": day}
    m = _UNTIL.fullmatch(part)
    day = _day(m[1], last=True) if m else None
    if day:
        return {"until": day}
    return None


def _merge(into: dict, more: dict) -> None:
    """Add one option's settings: magazines and languages add up; anything else — the later one wins."""
    for k, v in more.items():
        into[k] = (into.get(k) or set()) | v if k in ("pubs", "langs") else v


def _read_group(inner: str, media: bool) -> dict | None:
    """The settings of one (…) / […] group, or None when it holds anything that is not an option — then the
    whole group stays in the title and none of it counts. Several options may share a group, separated by
    commas ("(first, 15s)"; "(from March 1, 2027)" is ONE option) or by spaces ("(GV EN)", "(first x2)")."""
    t = _fold(inner)
    if not t:
        return None
    whole = _option(t, media)
    if whole is not None:
        return whole
    got: dict = {}
    for part in (p.strip() for p in re.split(r"[,;]", t)):
        if not part:
            continue
        one = _option(part, media)
        if one is None:
            words = part.split(" ")
            singles = [_option(w, media) for w in words] if len(words) > 1 else [None]
            if any(s is None for s in singles):
                return None
            for s in singles:
                _merge(got, s)
        else:
            _merge(got, one)
    return got or None


# --------------------------------------------------------------------------- the words before the title
_SEP = r"[\s.,;:_|·\-–—)]"
_ORDER = re.compile(rf"(\d{{1,3}})(?={_SEP}|$){_SEP}*")
_MAG_LEAD = re.compile(rf"(?i)(gv\s*[-+&/]?\s*lv|lv\s*[-+&/]?\s*gv|gv|lv|aa)(?={_SEP}|$){_SEP}*")
_LANG_LEAD = re.compile(rf"(EN\s*[-+&/]\s*ES|ES\s*[-+&/]\s*EN|BI|EN|ES)(?={_SEP}|$){_SEP}*")      # CAPITALS only
_LANG_WORD_LEAD = re.compile(rf"(?i)(english|ingl[eé]s|spanish|espa[nñ]ol|bilingual|biling[uü]e)(?={_SEP}|$){_SEP}*")
_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
# A date at the very start ("10-26-2026 Taller", "5 de octubre …", "1 May 2027 …"): its day is not an order.
_DATE_LEAD = re.compile(rf"(?i)\d{{1,2}}[-/.]\d{{1,2}}[-/.](?:\d{{4}}|\d{{2}})(?!\d)"
                        rf"|\d{{1,2}}(?:st|nd|rd|th)?[\s.,_-]+(?:de\s+)?(?:{_MONTH_ALT})\b")
# "12 Steps", "3 ways to carry the message", "1 Step at a time": a number that counts something is part of the
# title (folded words; written "01 …" it is an order after all).
_COUNTED = {
    "step", "steps", "tradition", "traditions", "concept", "concepts", "promise", "promises", "legacy", "legacies",
    "way", "ways", "year", "years", "day", "days", "hour", "hours", "minute", "minutes", "question", "questions",
    "tip", "tips", "reason", "reasons", "thing", "things", "paso", "pasos", "tradicion", "tradiciones", "concepto",
    "conceptos", "promesa", "promesas", "legado", "legados", "manera", "maneras", "forma", "formas", "ano", "anos",
    "dia", "dias", "hora", "horas", "minuto", "minutos", "pregunta", "preguntas", "consejo", "consejos", "razon",
    "razones", "cosa", "cosas",
}


def _leading(text: str) -> tuple[int | None, set[str], set[str], str]:
    """(order, magazines, languages, the rest) — what is written BEFORE the title starts: an order number
    first, then a magazine code and a language code in either order, each once. The first word that is none of
    these starts the title, so "Esto ES La Viña" keeps its "ES". A leading "AA" is the both-magazines code only
    right before a language code in capitals ("AA EN Welcome", "02 AA ES Taller"); anywhere else it is the
    title's first word — "AA Preamble", "AA en español" keep it (both magazines is the default anyway)."""
    rest = text.lstrip(" .,;:_|·-–—")
    order = None
    m = _ORDER.match(rest)
    if m and not _DATE_LEAD.match(rest):
        counted = re.match(r"[a-z]*", _fold(rest[m.end():]))[0] in _COUNTED
        if m[1].startswith("0") or not counted:
            order, rest = int(m[1]), rest[m.end():]
    pubs: set[str] = set()
    langs: set[str] = set()
    after_mag = False
    while rest:
        m = None if pubs else _MAG_LEAD.match(rest)
        if m and _fold(m[1]) == "aa" and not _LANG_LEAD.match(rest[m.end():]):
            m = None                          # "AA Preamble": AA starts the title
        if m:
            pubs = _magazines(_fold(m[1])) or {"gv", "lv"}
            rest, after_mag = rest[m.end():], True
            continue
        if not langs:
            m = _LANG_LEAD.match(rest) or (_LANG_WORD_LEAD.match(rest) if after_mag else None)
        if m:
            langs = _languages(_fold(m[1])) or set()
            rest, after_mag = rest[m.end():], False
            continue
        break
    return order, pubs, langs, rest


# --------------------------------------------------------------------------- the whole name
def collection_id(label: str) -> str:
    """'Spring Assembly 2027' → 'spring-assembly-2027': the id the player's settings remember a collection by. A
    sub-folder whose name would give the top folder's own id ("Main") gets one of its own."""
    cid = slugify(label, 60)
    return "main-folder" if cid == MAIN else cid


def parse_booth_name(name: str, mime: str | None = "", path: list[str] | tuple[str, ...] | None = None) -> dict:
    """A booth folder file → its `extra.booth` (docs/DATA_SCHEMA.md):

        {"kind": "photo|poster|video|audio|message|unsupported", "pub": "gv|lv|both", "langs": ["en"],
         "title": "Welcome to our table", "caption": true, "order": 2, "seconds": 15, "start": 5, "end": 105,
         "muted": false, "weight": 1, "first": false, "from": "2027-03-01", "until": null, "off": false,
         "fit": "contain|cover|null", "collection": "main|<slug>", "collection_label": "Booth folder|<folder>",
         "text": null, "problem": null}

    `name` is the file name, `mime` Drive's MIME type, `path` the folder names below the panel folder (["booth"],
    ["booth", "Spring Assembly 2027", "extra"]: the second one is the collection). `seconds` only for a photo,
    poster or message (3–120); `start` / `end` (seconds) and `muted` only for a video or sound file; `weight` 0.5
    or 1–5; `fit` "cover" (photo, or a video asked to fill the screen), "contain" (poster, video) or null (sound,
    message); `text` stays null here — drive.fill_booth_texts puts a message's text in; `problem` (English words,
    PROBLEMS) when the file can never be shown. Pure: no I/O, no clock."""
    raw = unicodedata.normalize("NFC", str(name or "")).strip()
    mtype = media_type(mime, raw)
    media = mtype in ("video", "audio")
    folders = [tidy(str(p)) or str(p).strip() for p in (path or [])]
    label = folders[1] if len(folders) > 1 else ""

    # the name as drive.py tidies any file's: no extension, no "Copy of", "GV_LV" → "GV/LV", underscores → spaces
    text = _COPY_PREFIX.sub("", _EXT_RE.sub("", raw).strip())
    text = re.sub(r"(?i)\bGV[\s_-]+LV\b", "GV/LV", text.replace("%20", " "))
    text = re.sub(r"_+", " ", text)
    got: dict = {}

    def take(m: re.Match) -> str:
        found = _read_group(m[1] if m[1] is not None else m[2], media)
        if found is None:
            return m[0]                       # not an option: part of the title
        _merge(got, found)
        return " "

    text = _GROUP.sub(take, text)
    for _ in range(3):                        # a copy's " (1)" / " - Copy", now that the options are out
        shorter = _COPY_SUFFIX.sub("", text.rstrip())
        if shorter == text.rstrip():
            break
        text = shorter
    order, pubs, langs, rest = _leading(text)
    pubs |= got.get("pubs") or set()
    langs |= got.get("langs") or set()
    title = tidy(rest)
    if is_generic_media_name(title):          # IMG_1234, WhatsApp Image …, a bare number: no caption
        title = ""

    fit_opt, problem = got.get("fit"), None
    if mtype in ("photo", "poster", "page"):
        kind = "photo" if fit_opt == "cover" or (fit_opt is None and mtype == "photo") else "poster"
        fit = "cover" if kind == "photo" else "contain"
    elif mtype == "video":
        kind, fit = "video", fit_opt or "contain"
    elif mtype == "audio":
        kind, fit = "audio", None
    elif mtype == "text":
        kind, fit = "message", None
    else:
        kind, fit, problem = "unsupported", None, PROBLEMS.get(mtype, PROBLEMS["unsupported"])[0]

    seconds = got.get("seconds") if kind in ("photo", "poster", "message") else None
    if seconds is not None:
        seconds = min(max(seconds, SECONDS_MIN), SECONDS_MAX)
    start = end = None
    if media and "range" in got:
        start, end = got["range"]
        if end is not None and end <= start:   # "(1:30-0:15)": the end is a slip — from 1:30 to the file's end
            end = None
    weight = got.get("weight", 1)
    if weight != 0.5:
        weight = min(max(int(weight), 1), WEIGHT_MAX)
    day_from, day_until = got.get("from"), got.get("until")
    if problem is None and day_from and day_until and day_from > day_until:
        problem = PROBLEMS["dates"][0]
    return {
        "kind": kind,
        "pub": next(iter(pubs)) if len(pubs) == 1 else "both",
        "langs": [lang for lang in ("en", "es") if lang in langs],
        "title": title,
        "caption": bool(title) and got.get("caption", True) is not False,
        "order": order,
        "seconds": seconds,
        "start": start,
        "end": end,
        "muted": bool(got.get("muted")) and media,
        "weight": weight,
        "first": bool(got.get("first")),
        "from": day_from,
        "until": day_until,
        "off": bool(got.get("off")) or raw[:1] in ("_", "~"),
        "fit": fit,
        "collection": collection_id(label) if label else MAIN,
        "collection_label": label or MAIN_LABEL,
        "text": None,
        "problem": problem,
    }


def problem_of(booth: dict) -> str | None:
    """Why a booth file can never be shown (English words, PROBLEMS), or None: the problem its name or type gave
    it, or — for a message — no text (an empty file, or one whose text could not be read yet). A file switched
    off has none: it is simply not shown. (build_data lists these in data/site/booth.json `problems`; drive.py
    names the files in one note of the run's stats — the Actions run summary.)"""
    if booth.get("off"):
        return None
    if booth.get("problem"):
        return booth["problem"]
    if booth.get("kind") == "message" and not booth.get("text"):
        return PROBLEMS["no-text"][0]
    return None


# --------------------------------------------------------------------------- a message's text
def message_text(md: str, limit: int = TEXT_MAX) -> str:
    """A booth message's body — a .txt / .md / Google Doc / .docx file's text as drive.normalize_body tidied it
    (the bulletin's Markdown) — → the Markdown-light text the player shows: paragraphs and line breaks,
    **bold** and "- " bullets ("* " / "+ " / "•" lists become "- "). Every other mark comes out: links → their
    words, a heading → a bold line, pictures, tables, code blocks and HTML dropped, _italics_, `code` and
    ~~strike~~ → plain words. At most `limit` characters, cut at a line or word end with "…" (never in the
    middle of a **bold** pair)."""
    t = (md or "").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"(?s)```.*?```", "\n", t)                       # code blocks
    t = re.sub(r"(?m)^[ \t]*\|.*$", "", t)                      # tables (a message is prose)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)                  # pictures
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)              # links → their words
    t = re.sub(r"<(https?://[^>\s]+)>", r"\1", t)               # <https://…> → the address
    t = re.sub(r"<[^>\n]+>", "", t)                             # HTML tags
    lines = []
    for ln in t.split("\n"):
        s = ln.strip()
        if re.fullmatch(r"(?:[-*_]\s*){3,}", s):                # --- / *** rules
            lines.append("")
            continue
        heading = re.fullmatch(r"#{1,6}\s+(.*?)\s*#*", s)
        if heading:
            words = heading[1].strip("*_ ")
            s = f"**{words}**" if words else ""
        else:
            s = re.sub(r"^(?:>\s?)+", "", s)                    # quotes
            s = re.sub(r"^[*+•·‣◦▪-]\s+", "- ", s)              # bullets → "- " ("— Bill W." stays a line)
        lines.append(s)
    t = "\n".join(lines)
    t = re.sub(r"__(?=\S)(.+?)(?<=\S)__", r"**\1**", t)         # __bold__ → **bold**
    t = re.sub(r"(?<![*\w])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![*\w])", r"\1", t)   # *italics*
    t = re.sub(r"(?<![\w_])_(?=\S)([^_\n]+?)(?<=\S)_(?![\w_])", r"\1", t)              # _italics_
    t = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"\1", t)
    t = re.sub(r"`([^`\n]+)`", r"\1", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) > limit:
        cut = t[: limit - 1]
        if not t[limit - 1].isspace():                         # the cut falls inside a word: back to its start
            k = max(cut.rfind("\n"), cut.rfind(" "))
            if k > limit * 0.6:
                cut = cut[:k]
        cut = cut.rstrip(" \n,;:.-–—")
        if cut.count("**") % 2:                                # a bold pair cut in two: drop its opening mark
            i = cut.rfind("**")
            cut = cut[:i] + cut[i + 2:]
        t = cut.rstrip() + "…"
    return t
