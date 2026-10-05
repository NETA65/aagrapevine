"""The booth display's Drive file names (scripts/sync/booth_names.py) — what a file's NAME says about how the booth
shows it: every example of the design (each one exactly as written there) and many more — the Spanish options,
brackets, several options in one pair, odd spacing and underscores, dates in names and in options (every form
common.date_from_text reads, a month alone, a date without its year), camera names, order numbers against years,
dates and counted things ("12 Steps"), words that only look like codes ("Esto ES La Viña", "En la mesa de Tyler"),
copies ("Copy of …", " (1)"), the collections, the file types by MIME type and by extension, the problems, and a
message's Markdown-light text. Pure functions: no network, no files.

    python -m unittest tests.test_booth_names -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import booth_names as BN  # noqa: E402
from scripts.sync.drive_listing import guess_mime  # noqa: E402

KEYS = ("kind", "pub", "langs", "title", "caption", "order", "seconds", "start", "end", "muted", "weight", "first",
        "from", "until", "off", "fit", "collection", "collection_label", "text", "problem")


def parse(name: str, mime: str | None = None, path=("booth",)) -> dict:
    """A booth file as drive.py reads it: the MIME type Drive gives (here: the one the HTML listing guesses from
    the name, as drive_listing does when the folder view shows no better one)."""
    return BN.parse_booth_name(name, guess_mime(name) or "" if mime is None else mime, list(path))


class Case(unittest.TestCase):
    def check(self, name: str, mime: str | None = None, path=("booth",), **want) -> dict:
        got = parse(name, mime, path)
        for key, value in want.items():
            self.assertEqual(got[key], value, f"{name!r} → {key}")
        return got


# --------------------------------------------------------------------------- the design's examples
class DesignExamples(Case):
    """The table of examples in the design (kind, magazine, languages, title, options), one test each."""

    def test_a_poster_shown_first_for_15_seconds(self):
        got = self.check("GV EN Welcome to our table (first) (15s).png", kind="poster", pub="gv", langs=["en"],
                         title="Welcome to our table", first=True, seconds=15, fit="contain", caption=True)
        self.assertEqual(tuple(got), KEYS, "every key, in the documented order")
        self.assertEqual((got["order"], got["off"], got["problem"], got["text"]), (None, False, None, None))

    def test_a_video_part(self):
        self.check("LV ES Testimonio - Mi primer número (0:05-1:45).mp4", kind="video", pub="lv", langs=["es"],
                   title="Testimonio - Mi primer número", start=5, end=105, fit="contain", muted=False)

    def test_a_photo_for_both_magazines(self):
        self.check("GVLV Our booth at CityWide Dallas.jpg", kind="photo", pub="both", langs=[],
                   title="Our booth at CityWide Dallas", fit="cover", caption=True)

    def test_a_camera_name_has_no_caption(self):
        self.check("IMG_2045.JPG", kind="photo", pub="both", langs=[], caption=False, title="")

    def test_an_order_number_and_a_weight(self):
        # (the committee's own picture of its table: Grapevine cartoons, logos, covers and artwork are never
        # reproduced — not in the folder, not in an example)
        self.check("02 GV Our book table (x3).png", kind="poster", pub="gv", langs=[], title="Our book table",
                   order=2, weight=3)

    def test_until_a_day(self):
        self.check("LV ES Taller de escritura en Tyler (hasta 2026-10-26).jpg", kind="photo", pub="lv",
                   langs=["es"], until="2026-10-26", title="Taller de escritura en Tyler")

    def test_never_shown(self):
        self.check("_draft poster.png", off=True)
        self.check("Draft poster (off).png", off=True, title="Draft poster")

    def test_a_collection(self):
        self.check("GV EN Book display.jpg", path=("booth", "Spring Assembly 2027"), kind="photo", pub="gv",
                   langs=["en"], title="Book display", collection="spring-assembly-2027",
                   collection_label="Spring Assembly 2027")

    def test_a_bilingual_video(self):
        self.check("GVLV BI Bienvenidos - Welcome.mp4", kind="video", pub="both", langs=["en", "es"],
                   title="Bienvenidos - Welcome")

    def test_a_message(self):
        # the heading; the body is fetched by drive.fill_booth_texts (tests/test_booth_sync.py)
        self.check("GV EN Welcome message.txt", kind="message", pub="gv", langs=["en"], title="Welcome message",
                   text=None, fit=None)

    def test_a_document_is_a_poster_of_its_first_page(self):
        self.check("Grapevine and La Viña - ways to carry the message.pdf", kind="poster", pub="both", langs=[],
                   title="Grapevine and La Viña - ways to carry the message", fit="contain")

    def test_es_inside_the_title_stays(self):
        self.check("Esto ES La Viña.jpg", kind="photo", pub="both", langs=[], title="Esto ES La Viña")

    def test_brackets_and_seconds_ignored_for_a_video(self):
        self.check("[LV][ES] Cita (10s) (muted).mp4", kind="video", pub="lv", langs=["es"], title="Cita",
                   muted=True, seconds=None)

    def test_a_sound_file_from_30_seconds(self):
        self.check("GV EN Podcast teaser (0:30-).mp3", kind="audio", pub="gv", langs=["en"], title="Podcast teaser",
                   start=30, end=None, fit=None)


# --------------------------------------------------------------------------- options
class SpanishOptions(Case):
    def test_every_option_in_spanish(self):
        self.check("LV ES Bienvenidos (primero) (20 segundos).png", first=True, seconds=20, title="Bienvenidos")
        self.check("LV ES Bienvenidas (primera) (20 seg).png", first=True, seconds=20)
        self.check("GV EN Book display (foto).png", kind="photo", fit="cover")           # a .png filling the screen
        self.check("LV Folleto (cartel).jpg", kind="poster", fit="contain")              # a .jpg shown whole
        self.check("LV Folleto (afiche).jpg", kind="poster")
        self.check("LV ES Cita (sin sonido) (0:10-0:40).mp4", muted=True, start=10, end=40)
        self.check("GV Clip (silencio).webm", muted=True)
        self.check("LV ES Taller (desde 2027-03-01) (hasta 2027-03-15).jpg", **{"from": "2027-03-01"},
                   until="2027-03-15")
        self.check("LV ES Recuerdo (a veces).jpg", weight=0.5)
        self.check("LV ES Recuerdo (poco).jpg", weight=0.5)
        self.check("LV ES Mesa (sin título).jpg", caption=False, title="Mesa")
        self.check("LV ES Mesa (sin texto).jpg", caption=False)
        self.check("LV Cartel nuevo (borrador).png", off=True)
        self.check("LV Cartel nuevo (apagado).png", off=True)

    def test_capitals_and_accents_do_not_matter(self):
        self.check("LV ES Mesa (SIN TEXTO) (Primera) (X2).jpg", caption=False, first=True, weight=2)
        self.check("LV ES Taller (Desde 1 de marzo de 2027).jpg", **{"from": "2027-03-01"}, title="Taller")
        self.check("LV ES Taller (sin titulo).jpg", caption=False)          # without its accent

    def test_english_words_for_the_same(self):
        self.check("GV EN Clip (mute).mp4", muted=True)
        self.check("GV EN Clip (silent).mp4", muted=True)
        self.check("GV EN Table (rare).jpg", weight=0.5)
        self.check("GV EN Table (sometimes).jpg", weight=0.5)
        self.check("GV EN Table (no text).jpg", caption=False)
        self.check("GV EN Table (no caption).jpg", caption=False, title="Table")
        self.check("GV EN Table (draft).jpg", off=True)


class DateOptions(Case):
    def test_every_date_form(self):
        self.check("GV Booth (from March 1, 2027).jpg", **{"from": "2027-03-01"}, title="Booth")
        self.check("GV Booth (until 03/15/2027).jpg", until="2027-03-15")
        self.check("GV Booth (until 15 March 2027).jpg", until="2027-03-15")
        self.check("GV Booth (hasta el 15 de marzo de 2027).jpg", until="2027-03-15")
        self.check("GV Booth (until 2027.03.15).jpg", until="2027-03-15")
        self.check("GV Booth (from: 2027-03-01).jpg", **{"from": "2027-03-01"})

    def test_a_month_alone(self):
        self.check("GV Booth (from March 2027).jpg", **{"from": "2027-03-01"})
        self.check("GV Booth (until March 2027).jpg", until="2027-03-31")        # through the whole month
        self.check("LV Mesa (hasta febrero de 2028).jpg", until="2028-02-29")    # a leap year

    def test_no_full_date_stays_in_the_title(self):
        self.check("GV EN Message (from the Chair).txt", title="Message (from the Chair)", **{"from": None})
        self.check("GV EN Notice (until further notice).txt", title="Notice (until further notice)", until=None)
        self.check("LV ES Aviso (hasta el 1 de febrero).txt", title="Aviso (hasta el 1 de febrero)", until=None)

    def test_dates_that_never_meet_are_a_problem(self):
        got = self.check("GV Booth (from 2027-03-15) (until 2027-03-01).jpg", kind="photo")
        self.assertEqual(got["problem"], BN.PROBLEMS["dates"][0])

    def test_a_date_in_the_name_stays_in_the_title(self):
        # not an option, not an order: the caption keeps it
        self.check("2027-03-14 Spring Assembly.jpg", title="2027-03-14 Spring Assembly", order=None,
                   **{"from": None, "until": None})
        self.check("GV EN Spring Assembly March 14, 2027.jpg", title="Spring Assembly March 14, 2027")


class Groups(Case):
    def test_brackets_like_parentheses(self):
        self.check("[GV] [EN] Welcome [first] [x2].png", pub="gv", langs=["en"], first=True, weight=2,
                   title="Welcome")
        self.check("Welcome [LV] [poster].jpg", pub="lv", kind="poster", title="Welcome")

    def test_several_options_in_one_pair(self):
        self.check("Welcome (first, 15s).png", first=True, seconds=15, title="Welcome")
        self.check("Welcome (GV EN).png", pub="gv", langs=["en"], title="Welcome")
        self.check("Welcome (first x2).png", first=True, weight=2)
        self.check("Welcome (GV; ES; muted).mp4", pub="gv", langs=["es"], muted=True)

    def test_a_pair_with_anything_else_stays_whole(self):
        self.check("Welcome (first, see notes).png", first=False, title="Welcome (first, see notes)")
        self.check("Taller (parte 2).jpg", title="Taller (parte 2)")
        self.check("Taller (English version).jpg", title="Taller (English version)", langs=[])
        self.check("Welcome (Off Broadway).png", off=False, title="Welcome (Off Broadway)")

    def test_magazines_and_languages_in_parentheses(self):
        self.check("Taller (La Viña).jpg", pub="lv", title="Taller")
        self.check("Story (Grapevine).jpg", pub="gv")
        self.check("Story (AA Grapevine).jpg", pub="gv")
        self.check("Story (Grapevine y La Viña).jpg", pub="both")
        self.check("Cita (en español).mp4", langs=["es"], title="Cita")
        self.check("Quote (in English).mp4", langs=["en"])
        self.check("Quote (English).mp4", langs=["en"])
        self.check("Cita (Español).mp4", langs=["es"])
        self.check("Cita [es].mp4", langs=["es"])
        self.check("Saludo (Bilingüe).mp4", langs=["en", "es"])
        self.check("Saludo (EN-ES).mp4", langs=["en", "es"])
        self.check("Saludo (en inglés y español).mp4", langs=["en", "es"])
        self.check("Saludo (EN ES).mp4", langs=["en", "es"])


class Timing(Case):
    def test_seconds_are_kept_within_3_to_120(self):
        self.check("GV Poster (1s).png", seconds=3)
        self.check("GV Poster (500s).png", seconds=120)
        self.check("GV Poster (2 min).png", seconds=120)
        self.check("GV Poster (10 sec).png", seconds=10)
        self.check("GV Poster (10 seconds).png", seconds=10)
        self.check("GV EN Note (45s).txt", seconds=45)                     # a message
        self.check("GV Song (30s).mp3", seconds=None, title="Song")        # sound: its own length

    def test_weights(self):
        self.check("GV Poster (x9).png", weight=5)
        self.check("GV Poster (x1).png", weight=1)
        self.check("GV Poster (3x).png", weight=3)
        self.check("GV Poster (×2).png", weight=2)
        self.check("GV Poster.png", weight=1)

    def test_the_part_of_a_video_to_play(self):
        self.check("GV Clip (15-90).mp4", start=15, end=90)
        self.check("GV Clip (0:15–1:30).mp4", start=15, end=90)             # an en dash
        self.check("GV Clip (0:15 a 1:30).mp4", start=15, end=90)
        self.check("GV Clip (0:15 to 1:30).mp4", start=15, end=90)
        self.check("GV Clip (1:02:03-1:05:00).mp4", start=3723, end=3900)
        self.check("GV Clip (1:30-0:15).mp4", start=90, end=None)           # an end before the start: dropped
        self.check("GV Clip (0:00-0:45).m4v", start=0, end=45)

    def test_a_range_on_a_picture(self):
        self.check("Big Book pages (15-90).jpg", title="Big Book pages (15-90)", start=None)   # plain numbers: title
        self.check("GV Poster (0:15-1:30).png", title="Poster", start=None, end=None)          # clock times: ignored


# --------------------------------------------------------------------------- the words before the title
class Leading(Case):
    def test_order_separators(self):
        for name in ("01 Welcome.png", "01-Welcome.png", "01_Welcome.png", "01. Welcome.png", "01) Welcome.png",
                     "1 - Welcome.png", "001 Welcome.png"):
            self.check(name, order=1, title="Welcome")
        self.check("3_GV_EN_Welcome.png", order=3, pub="gv", langs=["en"], title="Welcome")
        self.check("02-GV EN Welcome.png", order=2, pub="gv", langs=["en"])
        self.check("(first) 02 GV EN Welcome.png", order=2, first=True, pub="gv", title="Welcome")

    def test_years_and_dates_are_not_orders(self):
        self.check("2027 Spring Assembly.jpg", order=None, title="2027 Spring Assembly")
        self.check("10-26-2026 Taller en Tyler.jpg", order=None, title="10-26-2026 Taller en Tyler")
        self.check("5 de octubre Taller en Tyler.jpg", order=None, title="5 de octubre Taller en Tyler")
        self.check("1 May 2027 Workshop.jpg", order=None)
        self.check("0042 Booth.jpg", order=None, title="0042 Booth")        # 4 digits

    def test_counted_things_are_not_orders(self):
        self.check("12 Steps poster.png", order=None, title="12 Steps poster")
        self.check("12 Tradiciones.png", order=None, title="12 Tradiciones")
        self.check("3 ways to carry the message.png", order=None, title="3 ways to carry the message")
        self.check("1 Step at a time.png", order=None)
        self.check("10 años de La Viña.png", order=None, title="10 años de La Viña")
        self.check("01 Steps poster.png", order=1, title="Steps poster")    # a leading zero: an order after all

    def test_magazine_codes(self):
        for code in ("GVLV", "GV-LV", "GV+LV", "GV&LV", "GV/LV", "GV LV", "GV_LV", "LV-GV", "AA"):
            self.check(f"{code} EN Welcome.png", pub="both", langs=["en"], title="Welcome")
        self.check("gv Welcome.png", pub="gv", title="Welcome")             # magazine codes: any capitals
        self.check("Lv ES Taller.png", pub="lv", langs=["es"])
        self.check("EN GV Welcome.png", pub="gv", langs=["en"], title="Welcome")   # either order
        self.check("AA EN Preamble poster.png", pub="both", title="Preamble poster")

    def test_aa_starting_a_title(self):
        # A leading AA is the both-magazines code only right before a language code in capitals; anywhere else it
        # is the title's first word (both magazines is the default anyway, so the code would add nothing)
        self.check("AA Preamble (poster).png", pub="both", langs=[], title="AA Preamble", fit="contain", caption=True)
        self.check("AA and Grapevine.png", pub="both", title="AA and Grapevine")
        self.check("Aa ver la mesa.png", title="Aa ver la mesa")
        self.check("AA in Prison.jpg", langs=[], title="AA in Prison")
        self.check("AA en Tyler.jpg", langs=[], title="AA en Tyler")
        self.check("AA en español.png", langs=[], title="AA en español")
        self.check("AA Grapevine Story.jpg", pub="both", title="AA Grapevine Story")
        self.check("AA GV Welcome.png", pub="both", title="AA GV Welcome")
        self.check("AA ENGLISH TABLE.png", langs=[], title="AA ENGLISH TABLE")        # a word, not the code EN
        self.check("AA.png", pub="both", title="AA", caption=True)
        self.check("EN AA Welcome.png", langs=["en"], title="AA Welcome")
        self.check("GV AA Welcome.png", pub="gv", title="AA Welcome")
        self.check("01 AA Preamble.png", order=1, title="AA Preamble")
        # still the code: right before a language code, or in parentheses / brackets anywhere
        self.check("02 AA ES Taller.png", order=2, pub="both", langs=["es"], title="Taller")
        self.check("AA_EN_Welcome.png", pub="both", langs=["en"], title="Welcome")
        self.check("AA-ES Taller.png", pub="both", langs=["es"], title="Taller")
        self.check("AA BI Saludo.mp4", pub="both", langs=["en", "es"], title="Saludo")
        self.check("AA EN-ES Saludo.mp4", pub="both", langs=["en", "es"], title="Saludo")
        self.check("[AA][EN] Preamble.png", pub="both", langs=["en"], title="Preamble")
        self.check("Preamble (AA).png", pub="both", title="Preamble")

    def test_language_codes(self):
        self.check("GV EN-ES Welcome.mp4", langs=["en", "es"], title="Welcome")
        self.check("GV BI Welcome.mp4", langs=["en", "es"])
        self.check("GV English Welcome.png", langs=["en"], title="Welcome")       # the word, after the magazine
        self.check("LV Español Bienvenidos.png", langs=["es"], title="Bienvenidos")
        self.check("ES Bienvenidos.png", langs=["es"], pub="both", title="Bienvenidos")

    def test_words_that_only_look_like_codes(self):
        self.check("Esto ES La Viña.jpg", langs=[], title="Esto ES La Viña")
        self.check("En la mesa de Tyler.jpg", langs=[], title="En la mesa de Tyler")
        self.check("Es hora de servir.jpg", langs=[], title="Es hora de servir")
        self.check("LV es hora de servir.jpg", pub="lv", langs=[], title="es hora de servir")
        self.check("LV En la mesa.jpg", pub="lv", langs=[], title="En la mesa")
        self.check("English literature table.jpg", langs=[], title="English literature table")
        self.check("Spanish Assembly booth.jpg", langs=[], title="Spanish Assembly booth")
        self.check("Bienvenidos a la mesa EN Tyler.jpg", langs=[], title="Bienvenidos a la mesa EN Tyler")
        self.check("Grapevine table.jpg", pub="both", title="Grapevine table")    # the magazine's name is a title
        self.check("GVR training.jpg", pub="both", title="GVR training")          # GVR is not GV
        self.check("Lvl 2 display.jpg", pub="both", title="Lvl 2 display")


# --------------------------------------------------------------------------- titles
class Titles(Case):
    def test_camera_names_have_no_caption(self):
        for name in ("PXL_20261017_183316123.jpg", "WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg",
                     "Screenshot 2026-10-01 at 10.15.32 AM.png", "DSC_0042.JPG", "20261017_183316.jpg",
                     "0042.jpg", "IMG_2045 (1).JPG", "VID_20261017_183316.mp4", "Captura de pantalla 2026-10-01.png",
                     "01.png", "IMG-20261017-WA0003.jpg"):
            self.check(name, caption=False, title="")
        self.check("GV EN IMG_1234.jpg", pub="gv", langs=["en"], caption=False, title="")
        self.check("GV EN Book display IMG_1234.jpg", caption=True, title="Book display IMG 1234")

    def test_copies(self):
        self.check("Copy of GV EN Welcome.png", pub="gv", langs=["en"], title="Welcome")
        self.check("Copia de LV ES Taller.jpg", pub="lv", langs=["es"], title="Taller")
        self.check("GV EN Welcome (1).png", title="Welcome")
        self.check("GV EN Welcome (first) (2).png", title="Welcome", first=True)
        self.check("GV EN Welcome (2) (first).png", title="Welcome", first=True)
        self.check("Welcome - Copy.png", title="Welcome")
        self.check("Step (2) poster.png", title="Step (2) poster")         # a number inside the title stays

    def test_odd_spacing_and_underscores(self):
        self.check("  GV   EN   Welcome   to  our   table   ( first )  (15 s) .png", pub="gv", langs=["en"],
                   title="Welcome to our table", first=True, seconds=15)
        self.check("GV_EN_Welcome_to_our_table_(first).png", pub="gv", langs=["en"], title="Welcome to our table",
                   first=True)
        self.check("02__GV__EN__Welcome.png", order=2, pub="gv", langs=["en"], title="Welcome")
        self.check("Our GV_LV table.jpg", title="Our GV/LV table", pub="both")
        self.check("Welcome%20to%20our%20table.png", title="Welcome to our table")

    def test_hidden_names(self):
        self.check("_README naming.txt", off=True, kind="message")
        self.check("~notes for the chair.txt", off=True)
        self.check("GV EN Welcome (off) (first).png", off=True, first=True)


# --------------------------------------------------------------------------- collections
class Collections(Case):
    def test_the_top_folder_and_its_sub_folders(self):
        self.check("Welcome.png", path=("booth",), collection="main", collection_label="Booth folder")
        self.check("Welcome.png", path=("Booth photos",), collection="main")
        # a deeper sub-folder belongs to its top collection
        self.check("Welcome.png", path=("booth", "Spring Assembly 2027", "extra"), collection="spring-assembly-2027",
                   collection_label="Spring Assembly 2027")
        self.check("Bienvenidos.png", path=("Mesa", "Asamblea de Primavera"), collection="asamblea-de-primavera",
                   collection_label="Asamblea de Primavera")
        self.check("Welcome.png", path=("booth", "Spring_Assembly_2027"), collection="spring-assembly-2027",
                   collection_label="Spring Assembly 2027")
        self.check("Welcome.png", path=("booth", "Exhibición Área 65"), collection="exhibicion-area-65")

    def test_a_sub_folder_named_main_keeps_its_own_id(self):
        self.check("Welcome.png", path=("booth", "Main"), collection="main-folder", collection_label="Main")
        self.assertEqual(BN.collection_id("Spring Assembly 2027"), "spring-assembly-2027")


# --------------------------------------------------------------------------- file types
class FileTypes(Case):
    def test_by_mime_type(self):
        cases = {
            "application/vnd.google-apps.presentation": "poster", "application/vnd.google-apps.drawing": "poster",
            "application/vnd.google-apps.document": "message", "application/pdf": "poster",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "poster",
            "application/vnd.openxmlformats-officedocument.presentationml.slideshow": "poster",
            "application/vnd.apple.keynote": "poster", "image/heic": "photo", "image/heif": "photo",
            "image/tiff": "photo", "image/jpeg": "photo", "image/png": "poster", "image/gif": "poster",
            "image/webp": "poster", "image/svg+xml": "poster", "image/bmp": "poster", "video/mp4": "video",
            "video/webm": "video", "video/quicktime": "video", "video/x-m4v": "video", "audio/mpeg": "audio",
            "audio/mp4": "audio", "audio/x-m4a": "audio", "audio/aac": "audio", "audio/wav": "audio",
            "audio/ogg": "audio", "audio/opus": "audio", "text/plain": "message", "text/markdown": "message",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "message",
        }
        for mime, kind in cases.items():
            self.check("GV Something", mime=mime, kind=kind)          # a native Google file has no extension

    def test_by_extension_when_drive_gives_no_type(self):
        for ext, kind in {"jpg": "photo", "jpeg": "photo", "heic": "photo", "tif": "photo", "png": "poster",
                          "svg": "poster", "pdf": "poster", "pptx": "poster", "ppsx": "poster", "key": "poster",
                          "mp4": "video", "m4v": "video", "webm": "video", "mov": "video", "mp3": "audio",
                          "m4a": "audio", "aac": "audio", "wav": "audio", "ogg": "audio", "oga": "audio",
                          "opus": "audio", "txt": "message", "md": "message", "markdown": "message",
                          "docx": "message"}.items():
            for mime in ("", "application/octet-stream"):
                self.check(f"GV Something.{ext.upper()}", mime=mime, kind=kind, title="Something")

    def test_what_the_booth_cannot_show(self):
        unsupported = BN.PROBLEMS["unsupported"][0]
        for name, mime, problem in (
                ("notes.zip", "application/zip", unsupported),
                ("Sign-up", "application/vnd.google-apps.form", unsupported),
                ("Flyer.pdf", "application/vnd.google-apps.shortcut", unsupported),     # a shortcut Drive would not follow
                ("Old notes.doc", "application/msword", unsupported),
                ("Icon.ico", "image/x-icon", unsupported),
                ("Page.html", "text/html", unsupported),
                ("Old clip.avi", "video/x-msvideo", BN.PROBLEMS["video-type"][0]),
                ("Old clip.mkv", "", BN.PROBLEMS["video-type"][0]),
                ("Clip", "video/x-flv", BN.PROBLEMS["video-type"][0]),
                ("Song.wma", "audio/x-ms-wma", BN.PROBLEMS["audio-type"][0]),
                ("Song", "audio/x-something", BN.PROBLEMS["audio-type"][0])):
            got = self.check(name, mime=mime, kind="unsupported", fit=None)
            self.assertEqual(got["problem"], problem, name)
        self.assertIn("mp4", BN.PROBLEMS["video-type"][0])                 # says what to do
        self.assertIn("mp3", BN.PROBLEMS["audio-type"][1])

    def test_fit_by_kind(self):
        self.check("GV Clip.mp4", fit="contain")
        self.check("GV Clip (photo).mp4", fit="cover")                     # a video asked to fill the screen
        self.check("GV Slides (photo).pdf", kind="photo", fit="cover")
        self.check("GV Song.mp3", fit=None)
        self.check("GV EN Note.txt", fit=None)

    def test_options_that_do_not_apply_are_ignored(self):
        self.check("GV EN Note (muted) (0:15-1:30).txt", muted=False, start=None, end=None, title="Note")
        self.check("GV Poster (muted).png", muted=False, title="Poster")


class Problems(unittest.TestCase):
    def test_every_problem_in_both_languages(self):
        for code, (en, es) in BN.PROBLEMS.items():
            self.assertTrue(en and es and en != es, code)
            self.assertEqual(BN.PROBLEM_CODES[en], code)
            for words in (en, es):
                self.assertNotRegex(words, r"(?i)\bpdf\b", "visitors never read the word")
        self.assertEqual(BN.PROBLEMS["unsupported"][0], "not a type the booth can show")    # the design's words

    def test_problem_of(self):
        self.assertIsNone(BN.problem_of(parse("GV Poster.png")))
        self.assertEqual(BN.problem_of(parse("notes.zip")), BN.PROBLEMS["unsupported"][0])
        self.assertIsNone(BN.problem_of(parse("notes (off).zip")), "switched off: simply not shown")
        self.assertEqual(BN.problem_of(parse("GV EN Note.txt")), BN.PROBLEMS["no-text"][0])     # no text (yet)
        self.assertIsNone(BN.problem_of({**parse("GV EN Note.txt"), "text": "Hello"}))
        self.assertEqual(BN.problem_of(parse("X (from 2027-03-15) (until 2027-03-01).png")), BN.PROBLEMS["dates"][0])


# --------------------------------------------------------------------------- a message's text
class MessageText(unittest.TestCase):
    def test_markdown_light(self):
        md = ("# Welcome to our table\n\nCome **visit** us and read [the magazine](https://www.aagrapevine.org).\n\n"
              "* one\n+ two\n• three\n- four\n1. first\n\n> A quote line\n\n__Bold too__, _italics_, *more*, "
              "`code`, ~~old~~.\n\n![a picture](https://x.test/p.png)\n\n| a | b |\n|---|---|\n\n---\n\n"
              "<b>tags</b> and <https://neta65.github.io/aagrapevine/>\n\n— Bill W.")
        self.assertEqual(BN.message_text(md), (
            "**Welcome to our table**\n\nCome **visit** us and read the magazine.\n\n- one\n- two\n- three\n- four\n"
            "1. first\n\nA quote line\n\n**Bold too**, italics, more, code, old.\n\n"
            "tags and https://neta65.github.io/aagrapevine/\n\n— Bill W."))

    def test_code_blocks_and_spacing(self):
        self.assertEqual(BN.message_text("Line one  \nLine   two\n\n\n\n```\nprint(1)\n```\n\nEnd"),
                         "Line one\nLine two\n\nEnd")
        self.assertEqual(BN.message_text(""), "")
        self.assertEqual(BN.message_text("2*3*4 stays"), "2*3*4 stays")

    def test_at_most_1200_characters(self):
        long = ("Grapevine and La Viña carry the message. " * 60).strip()
        out = BN.message_text(long)
        self.assertLessEqual(len(out), BN.TEXT_MAX)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn(" …", out)
        self.assertTrue(long.startswith(out[:-1]), "cut at a word end")
        bold = "a " * 590 + "**a bold phrase that runs past the end of the text kept**"
        out = BN.message_text(bold)
        self.assertEqual(out.count("**") % 2, 0, "no bold pair cut in two")
        self.assertLessEqual(len(out), BN.TEXT_MAX)
        # a cut that falls on a word end keeps that word: 12 × "word" + "…" = exactly 60 characters
        self.assertEqual(BN.message_text("word " * 100, limit=60), " ".join(["word"] * 12) + "…")
        self.assertEqual(BN.message_text("word " * 100, limit=62), " ".join(["word"] * 12) + "…")


if __name__ == "__main__":
    unittest.main()
