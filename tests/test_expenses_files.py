"""The Tracker's files beyond CSV (src/assets/js/expenses-files.js, window.GVF) run in Node.js:

  * CRC-32       — the check values everyone uses, resumable, the same as Python's zlib
  * writing      — GVF.zip's archive is read back by Python's zipfile (STORED, UTF-8 names, the date)
  * reading      — archives Python writes (STORED and DEFLATED, a comment at the end) are read; a damaged
                   byte, a cut-off file, a password and a browser that can't unpack are each told apart
  * Excel        — the first worksheet of a workbook built here as Excel writes one: shared strings (rich
                   text, phonetic guides, entities, _x000D_), inline strings, numbers as Excel shows them,
                   TRUE / FALSE, dates by their cell's format (built-in and the workbook's own; the 1904
                   system), the first sheet found through its relationship, prefixed XML, the row limit
  * a big .json  — a backup with its photos inside read in slices (any slice size gives the same answer,
                   whatever quotes, backslashes and braces the names hold); a file not laid out as the
                   tracker writes it is left to be read whole; the v1 backup (tests/fixtures/expenses) reads
The file runs in a vm context, as tests/test_expenses_core.py runs the core. Skipped without Node.js.

    python -m unittest tests.test_expenses_files -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import sys
import unittest
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "expenses"

LOAD = r"""
import vm from "node:vm";
const ctx = vm.createContext({ console, TextDecoder, TextEncoder, Blob, atob,
  DecompressionStream: input && input.noInflate ? undefined : DecompressionStream });
for (const f of ["src/assets/js/expenses-core.js", "src/assets/js/expenses-files.js"]) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
const F = ctx.GVF, G = ctx.GVX;
const bytes = (b64) => new Uint8Array(Buffer.from(b64, "base64"));
const blobOf = (b64) => new Blob([bytes(b64)]);
const b64 = async (blob) => Buffer.from(await blob.arrayBuffer()).toString("base64");
const err = async (p) => { try { await p; return "ok"; } catch (e) { return e.key || String(e); } };
"""


def files(case: unittest.TestCase, js: str, data: dict | None = None):
    return run_js(case, LOAD + js, data=data or {}, needs_modules=False)


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def a_zip(entries: list[tuple[str, bytes, int]], comment: bytes = b"") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data, method in entries:
            z.writestr(zipfile.ZipInfo(name, (2026, 9, 27, 10, 30, 0)), data, compress_type=method)
        z.comment = comment
    return buf.getvalue()


# A workbook as Excel writes one (deflated parts). The first sheet in the workbook's order is "Gastos",
# whose part is sheet2.xml (found through its relationship); sheet1.xml is the second tab.
NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
WORKBOOK = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook {NS}><workbookPr{{d1904}}/><sheets>'
            '<sheet name="Gastos" sheetId="2" r:id="rId2"/><sheet name="Otra" sheetId="1" r:id="rId1"/></sheets></workbook>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Target="/xl/worksheets/sheet2.xml" Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
SHARED = (f'<sst {NS} count="8" uniqueCount="8">'
          '<si><t>Date</t></si><si><t>Description</t></si><si><t>Amount</t></si><si><t>Paid</t></si>'
          '<si><r><rPr><b/></rPr><t>Hotel </t></r><r><t xml:space="preserve">&amp; parking</t></r><rPh sb="0" eb="1"><t>ホテル</t></rPh></si>'
          '<si><t>Line one_x000D__x000A_line two &lt;3 &#233;&#x00F1;</t></si>'
          '<si><t/></si>'
          '<si><t>Literal _x005F_x0041_</t></si></sst>')
STYLES = (f'<styleSheet {NS}><numFmts count="3"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/>'
          '<numFmt numFmtId="165" formatCode="0.00 &quot;days&quot;"/><numFmt numFmtId="166" formatCode="[h]:mm"/></numFmts>'
          '<cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs>'
          '<cellXfs count="6"><xf numFmtId="0" xfId="0"/><xf numFmtId="14" xfId="0" applyNumberFormat="1"/>'
          '<xf numFmtId="164" xfId="0" applyNumberFormat="1"><alignment horizontal="left"/></xf><xf numFmtId="165" xfId="0"/>'
          '<xf numFmtId="166" xfId="0"/><xf numFmtId="22" xfId="0"/></cellXfs></styleSheet>')
SHEET2 = (f'<worksheet {NS}><dimension ref="A2:E9"/><sheetData>'
          # row 1 is empty: the header is the first row with something in it
          '<row r="2"><c r="A2" t="s"><v>0</v></c><c r="B2" t="s"><v>1</v></c><c r="C2" t="s"><v>2</v></c><c r="D2" t="s"><v>3</v></c></row>'
          '<row r="3"><c r="A3" s="1"><v>46292</v></c><c r="B3" t="s"><v>4</v></c><c r="C3"><v>12.339999999999998</v></c><c r="D3" t="b"><v>1</v></c></row>'
          '<row r="4"><c r="A4" s="2"><v>46293.75</v></c><c r="B4" t="inlineStr"><is><t>Café &amp; donuts</t></is></c><c r="C4"><v>1.5E-3</v></c>'
          '<c r="D4" t="b"><v>0</v></c><c r="E4" s="3"><v>2</v></c></row>'
          '<row r="5"><c r="A5" s="5"><v>46294.5</v></c><c r="B5" t="s"><v>5</v></c><c r="C5" t="str"><f>C3*2</f><v>24.68</v></c><c r="D5" t="e"><v>#N/A</v></c></row>'
          # row 6 is empty inside the sheet (it stays: row numbers are the sheet's own); 7 has a gap (B) and a time
          '<row r="7"><c r="A7" s="4"><v>0.5</v></c><c r="C7"><v>-45</v></c></row>'
          '<row r="8" spans="1:4"><c r="A8" t="s"><v>6</v></c><c r="B8" t="s"><v>7</v></c><c r="C8" s="1"/></row>'
          '</sheetData></worksheet>')
SHEET1 = f'<worksheet {NS}><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>The other tab</t></is></c></row></sheetData></worksheet>'


def workbook(d1904: bool = False, sheet2: str = SHEET2, prefixed: bool = False) -> bytes:
    parts = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "xl/workbook.xml": WORKBOOK.replace("{d1904}", ' date1904="1"' if d1904 else ""),
        "xl/_rels/workbook.xml.rels": RELS, "xl/sharedStrings.xml": SHARED, "xl/styles.xml": STYLES,
        "xl/worksheets/sheet1.xml": SHEET1, "xl/worksheets/sheet2.xml": sheet2,
    }
    if prefixed:      # (the OpenXML SDK's way: every element with a prefix)
        parts = {k: v.replace("<", "<x:").replace("<x:/", "</x:").replace("<x:?", "<?").replace(' xmlns="', ' xmlns:x="')
                 if k.startswith("xl/w") or k.startswith("xl/s") else v for k, v in parts.items()}
    return a_zip([(k, v.encode("utf-8"), zipfile.ZIP_DEFLATED) for k, v in parts.items()])


def serial(n: float) -> dt.datetime:
    return dt.datetime(1899, 12, 30) + dt.timedelta(days=n)


class Crc(unittest.TestCase):
    def test_check_values(self):
        blob = bytes(range(256)) * 9 + "año".encode("utf-8")
        r = files(self, r"""
          const t = new TextEncoder();
          const all = bytes(input.blob), half = all.length >> 1;
          out([F.crc32(t.encode("123456789")), F.crc32(new Uint8Array(0)), F.crc32(all), F.crc32(all.subarray(half), F.crc32(all.subarray(0, half)))]);""",
                  {"blob": b64(blob)})
        self.assertEqual(r[0], 0xCBF43926)                                    # the CRC-32 check value
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], zlib.crc32(blob))
        self.assertEqual(r[3], r[2])                                          # resumable


class WriteZip(unittest.TestCase):
    def test_python_reads_it(self):
        r = files(self, r"""
          const jpeg = new Blob([new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3])], { type: "image/jpeg" });
          const z = await F.zip([{ name: "backup.json", data: '{"format":"gv-expenses-backup","año":1}' }, { name: "2026-09-27-recibo-año-x1.jpg", data: jpeg },
                                 { name: "raw.bin", data: new Uint8Array([0, 0, 0]) }], new Date(2026, 8, 27, 18, 45, 31));
          const twice = await err(F.zip([{ name: "a", data: "1" }, { name: "a", data: "2" }]));
          out({ zip: await b64(z), type: z.type, twice });""")
        z = zipfile.ZipFile(io.BytesIO(base64.b64decode(r["zip"])))
        self.assertIsNone(z.testzip())
        self.assertEqual(z.namelist(), ["backup.json", "2026-09-27-recibo-año-x1.jpg", "raw.bin"])
        self.assertEqual(z.read("backup.json").decode("utf-8"), '{"format":"gv-expenses-backup","año":1}')
        self.assertEqual(z.read("2026-09-27-recibo-año-x1.jpg"), bytes([0xFF, 0xD8, 0xFF, 0xE0, 1, 2, 3]))
        for i in z.infolist():
            self.assertEqual((i.compress_type, i.flag_bits & 0x800, i.date_time), (zipfile.ZIP_STORED, 0x800, (2026, 9, 27, 18, 45, 30)))
        self.assertEqual(r["type"], "application/zip")
        self.assertNotEqual(r["twice"], "ok")                                   # a name used twice is refused


class ReadZip(unittest.TestCase):
    def test_stored_deflated_and_a_comment(self):
        text = ("Receipt line, " * 400).encode("utf-8")
        zz = a_zip([("backup.json", b'{"v":1}', zipfile.ZIP_STORED), ("big.txt", text, zipfile.ZIP_DEFLATED),
                    ("receipts/p 1.jpg", bytes([255, 216, 0, 9]), zipfile.ZIP_STORED)], comment=b"x" * 300)
        r = files(self, r"""
          const z = await F.readZip(blobOf(input.zip));
          out({ names: z.entries.map((e) => [e.name, e.method, e.size]), has: [z.has("backup.json"), z.has("nope")],
                json: await z.text("backup.json"), big: (await z.text("big.txt")).length, photo: Array.from(await z.bytes("receipts/p 1.jpg")),
                blob: await (async () => { const b = await z.blob("receipts/p 1.jpg", "image/jpeg"); return [b.type, b.size]; })() });""",
                  {"zip": b64(zz)})
        self.assertEqual(r["names"], [["backup.json", 0, 7], ["big.txt", 8, len(text)], ["receipts/p 1.jpg", 0, 4]])
        self.assertEqual(r["has"], [True, False])
        self.assertEqual((r["json"], r["big"], r["photo"], r["blob"]), ('{"v":1}', len(text), [255, 216, 0, 9], ["image/jpeg", 4]))

    def test_what_goes_wrong_is_told_apart(self):
        good = a_zip([("a.txt", b"hello hello hello", zipfile.ZIP_STORED), ("b.txt", b"deflated " * 50, zipfile.ZIP_DEFLATED)])
        bad = bytearray(good)
        bad[good.index(b"hello") + 2] ^= 0x20                                  # one byte of a.txt changed: its CRC fails
        locked = bytearray(good)
        cd = good.rindex(b"PK\x01\x02", 0, good.index(b"PK\x05\x06"))         # b.txt's central record: "encrypted"
        locked[cd + 8] |= 1
        r = files(self, r"""
          out({ crc: await err((await F.readZip(blobOf(input.bad))).text("a.txt")),
                cut: await err(F.readZip(blobOf(input.cut))), notzip: await err(F.readZip(new Blob(["date,amount\n1,2\n"]))),
                tiny: await err(F.readZip(new Blob(["PK"]))),
                locked: await err((await F.readZip(blobOf(input.locked))).text("b.txt")), missing: await err((await F.readZip(blobOf(input.good))).text("c.txt")) });""",
                  {"good": b64(good), "bad": b64(bytes(bad)), "cut": b64(good[:-30]), "locked": b64(bytes(locked))})
        self.assertEqual(r, {"crc": "expenses.err.zip_damaged", "cut": "expenses.err.zip_damaged", "notzip": "expenses.err.zip_damaged",
                             "tiny": "expenses.err.zip_damaged", "locked": "expenses.err.zip_locked", "missing": "expenses.err.zip_damaged"})
        # a browser without DecompressionStream("deflate-raw"): a STORED file still reads, a deflated one says so
        r2 = files(self, r"""
          const z = await F.readZip(blobOf(input.good));
          out([await z.text("a.txt"), await err(z.text("b.txt"))]);""", {"good": b64(good), "noInflate": True})
        self.assertEqual(r2, ["hello hello hello", "expenses.err.zip_browser"])


class Excel(unittest.TestCase):
    def rows(self, wb: bytes, **extra):
        return files(self, r"""
          const z = await F.readZip(blobOf(input.wb));
          const rows = await F.xlsxRows(z, input.maxRows ? { maxRows: input.maxRows } : undefined);
          out({ rows: rows.map((r) => r.slice()), error: rows.error || "" });""", {"wb": b64(wb), **extra})

    def test_the_first_sheet_as_rows(self):
        r = self.rows(workbook())
        d = lambda n, t="": serial(n).strftime("%Y-%m-%d") + (" " + t if t else "")  # noqa: E731
        self.assertEqual(r["error"], "")
        self.assertEqual(r["rows"], [
            ["Date", "Description", "Amount", "Paid"],
            [d(46292), "Hotel & parking", "12.34", "TRUE"],                  # rich text (no phonetic guide); 15 digits
            [d(46293, "18:00"), "Café & donuts", "0.0015", "FALSE", "2"],    # a date format of the workbook's own; no exponent; "0.00 days" is a number
            [d(46294, "12:00"), "Line one\r\nline two <3 éñ", "24.68", "#N/A"],   # built-in 22 (date and time); _x000D_; a formula's value; an error
            [],                                                              # the sheet's own empty row 6
            ["12:00", "", "-45"],                                            # a time of day ([h]:mm); a gap
            ["", "Literal _x0041_"],                                         # an empty string; Excel's escaped underscore
        ])
        self.assertEqual(d(46292), "2026-09-27")

    def test_1904_prefixes_and_the_row_limit(self):
        self.assertEqual(self.rows(workbook(d1904=True))["rows"][1][0], "2030-09-28")   # the same serial, four years and a day later
        self.assertEqual(self.rows(workbook(prefixed=True))["rows"], self.rows(workbook())["rows"])
        r = self.rows(workbook(), maxRows=3)
        self.assertEqual(r["error"], "expenses.err.too_many_rows")
        # no relationship to follow: the first worksheet by name
        z = zipfile.ZipFile(io.BytesIO(workbook()))
        bare = a_zip([(n, z.read(n), zipfile.ZIP_DEFLATED) for n in z.namelist() if n != "xl/_rels/workbook.xml.rels"])
        self.assertEqual(self.rows(bare)["rows"], [["The other tab"]])

    def test_a_browser_that_cannot_unpack(self):
        r = files(self, r"""out(await err((async () => F.xlsxRows(await F.readZip(blobOf(input.wb))))()));""", {"wb": b64(workbook()), "noInflate": True})
        self.assertEqual(r, "expenses.err.xlsx_browser")


class BigJson(unittest.TestCase):
    JS = r"""
      const S = G.emptyState(null).settings;
      const E = [G.normalizeEntry({ id: "e1", type: "expense", date: "2026-09-01", category: "books", amount_cents: 1250, receipt: "photo",
                                     description: 'He said "receipts":[ {braces} \\ and \\" quotes' }, S).entry,
                 G.normalizeEntry({ id: "e2", type: "expense", date: "2026-09-02", category: "books", amount_cents: 99, receipt: "photo", description: "B" }, S).entry];
      const photo = (s) => "data:image/jpeg;base64," + Buffer.from(s).toString("base64");
      const R = [{ id: "e1", type: "image/jpeg", dataUrl: photo("first photo"), name: 'a "quoted" name\\', added: "2026-09-01T00:00:00Z" },
                 { id: "e2", type: "image/png", dataUrl: "data:image/png;base64," + Buffer.from("x".repeat(3000)).toString("base64"), name: "}{][\\\\" }];
      const text = G.toBackup({ entries: E, settings: S, meta: { lastBackup: null } }, R);
      const whole = JSON.parse(text); delete whole.receipts;
      const read = async (blob, chunk) => {
        const jb = await F.jsonBackup(blob, { chunk });
        if (!jb) return null;
        const got = [];
        for (const r of jb.receipts) { const b = await r.load(); got.push([r.id, r.type, b.type, b.size, (await b.text()).slice(0, 11)]); }
        return { same: JSON.stringify(jb.head) === JSON.stringify(whole), got };
      };
    """

    def test_any_slice_size_reads_the_same(self):
        r = files(self, self.JS + r"""
          const res = [];
          for (const chunk of [65, 66, 67, 70, 97, 128, 255, 256, 1024, 8 << 20]) res.push(await read(new Blob([text]), chunk));
          out(res);""")
        want = {"same": True, "got": [["e1", "image/jpeg", "image/jpeg", 11, "first photo"], ["e2", "image/png", "image/png", 3000, "xxxxxxxxxxx"]]}
        for x in r:
            self.assertEqual(x, want)

    def test_other_layouts_are_left_to_be_read_whole(self):
        r = files(self, self.JS + r"""
          const first = JSON.stringify({ receipts: R, ...JSON.parse(text) });            // the photos first
          out([await read(new Blob([first]), 100) === null || (await read(new Blob([first]), 100)).got.length, await read(new Blob(["not json at all"]), 100),
               await read(new Blob([JSON.stringify({ v: 1, entries: E, settings: S })]), 100),                 // the stored state: no photos
               await read(new Blob([text.slice(0, -40)]), 100)]);                                               // cut off before the end""")
        self.assertEqual(r[1:], [None, None, None])
        self.assertIn(r[0], (True, 0))         # (its "receipts" key is first: either not found as ours, or no photo found after it)

    def test_the_v1_backup(self):
        text = (FIXTURES / "v1-backup.json").read_bytes()
        r = files(self, r"""
          const jb = await F.jsonBackup(blobOf(input.file), { chunk: 4096 });
          const back = G.readBackup(jb.head, null);
          const p = await jb.receipts[0].load();
          out({ ok: back.ok, n: back.state.entries.length, receipts: jb.receipts.map((r) => [r.id, r.type]), photo: [p.type, p.size] });""",
                  {"file": b64(text)})
        want = json.loads(text.decode("utf-8"))
        self.assertEqual((r["ok"], r["n"]), (True, len(want["entries"])))
        self.assertEqual(r["receipts"], [[x["id"], x["type"]] for x in want["receipts"]])
        self.assertEqual(r["photo"][0], want["receipts"][0]["type"])

    def test_data_urls(self):
        r = files(self, r"""
          const f = (u) => { const x = F.dataUrlBytes(u); return x ? [x.type, Array.from(x.bytes)] : null; };
          out([f("data:image/jpeg;base64,AQID"), f("data:image/png;charset=x;base64,AQ%3D%3D".replace("%3D%3D", "==")), f("data:,a%20b"), f("nope"), f("data:image/jpeg;base64,***")]);""")
        self.assertEqual(r, [["image/jpeg", [1, 2, 3]], ["image/png", [1]], ["image/jpeg", [97, 32, 98]], None, None])


class Keys(unittest.TestCase):
    def test_every_message_exists_in_both_languages(self):
        src = (ROOT / "src" / "assets" / "js" / "expenses-files.js").read_text(encoding="utf-8")
        strings = json.loads((ROOT / "src" / "_i18n" / "expenses.json").read_text(encoding="utf-8"))
        import re
        used = set(re.findall(r'"(expenses\.err\.[a-z0-9_]+)"', src))
        listed = set(files(self, "out(F.KEYS);"))
        self.assertEqual(used, listed)
        for k in used | {"expenses.err.xls_old"}:
            self.assertIn(k, strings)
            self.assertTrue(strings[k]["en"].strip() and strings[k]["es"].strip(), k)

    def test_es2019(self):
        src = (ROOT / "src" / "assets" / "js" / "expenses-files.js").read_text(encoding="utf-8")
        code = "\n".join(line.split("//")[0] for line in src.splitlines())
        import re
        self.assertNotRegex(code, r"(?m)\?\.[A-Za-z_(\[]|\?\?|^\s*(import|export)\s|\(\?<[=!]")    # no ?. ?? modules or lookbehind


if __name__ == "__main__":
    unittest.main()
