/* The Tracker's files beyond CSV (/tracker/, src/pages/tracker.njk + expenses.js): ZIP archives and Excel
   workbooks, with no library. Bytes, Blobs and text only — no DOM. Loaded before expenses.js; tested in
   Node by tests/test_expenses_files.py (the file runs in a vm context, as expenses-core.js does).
   A plain script (ES2019): it defines window.GVF (globalThis.GVF in Node).
     crc32(bytes, crc)    CRC-32 (the one ZIP uses), resumable: crc32(b, crc32(a)) is the CRC of a + b.
     zip(files, when)     → Promise<Blob>: a ZIP archive, every file STORED as it is — the receipt photos are
                          JPEGs already, nothing is gained by compressing them, and any unzip program (or this
                          file) reads it back. files: [{name, data: Blob | Uint8Array | string}]. Each Blob is
                          read once, on its own, for its CRC, and goes into the archive as itself: a backup of
                          500 photos is never in memory all at once.
     readZip(blob)        → Promise<archive>: the central directory, read from the end of the file; an entry's
                          bytes are sliced from the file only when asked for — STORED, or DEFLATED (Excel's own
                          files) through the browser's DecompressionStream("deflate-raw") — and their CRC checked.
                          archive: {entries, has(name), bytes(name, limit), text(name, limit), blob(name, type)}.
     xlsxRows(archive)    → Promise<rows>: the first worksheet of an Excel workbook (.xlsx) as rows of text —
                          the shape GVX.parseCSV gives, so GVX.planImport reads it as it reads a CSV. Shared and
                          inline strings, numbers as Excel shows them (15 digits), TRUE / FALSE, and the cells
                          a date format shows as dates: "YYYY-MM-DD" (with " HH:MM" when there is a time).
     jsonBackup(blob)     → Promise<{head, receipts} | null>: a big .json backup (the photos inside it, as every
                          full backup was before 1.2.0) read in slices: head = the backup without its photos
                          (GVX.readBackup takes it), receipts = [{id, type, load()}] — load() reads that one
                          photo from the file when it is restored. null: the file is not laid out as
                          GVX.toBackup writes it (the page then reads it whole).
     dataUrlBytes(url)    a data: URL's bytes (base64 or not), or null.
   A failure is an Error whose .key is a message key of src/_i18n/expenses.json ("expenses.err.zip_damaged" …). */
(function (root) {
  "use strict";

  var PART = 64 * 1024 * 1024;     // the most one file of an archive may unpack to (an Excel sheet's XML)
  var CHUNK = 8 * 1024 * 1024;     // a big .json backup is read this much at a time
  var KEYS = ["expenses.err.zip_damaged", "expenses.err.zip_locked", "expenses.err.zip_browser", "expenses.err.xlsx_browser",
    "expenses.err.backup_too_big", "expenses.err.part_too_big", "expenses.err.too_many_rows"];

  function fail(key) { var e = new Error(key); e.key = key; return e; }
  function noop() {}
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  // (a Blob or a Uint8Array from another window or vm context is not `instanceof` this one's)
  function isBlob(v) { return !!v && typeof v === "object" && typeof v.size === "number" && typeof v.slice === "function" && !ArrayBuffer.isView(v); }
  function u8(v) { return ArrayBuffer.isView(v) ? new Uint8Array(v.buffer, v.byteOffset, v.byteLength) : new Uint8Array(v || 0); }
  function utf8(s) { return new TextEncoder().encode(String(s)); }
  function text(bytes) { return new TextDecoder("utf-8").decode(bytes); }
  // a Blob's bytes (a FileReader where the Blob has no arrayBuffer(): Safari before 14)
  function bytesOf(blob) {
    if (typeof blob.arrayBuffer === "function") return blob.arrayBuffer().then(u8);
    return new Promise(function (res, rej) {
      var r = new FileReader();
      r.onload = function () { res(u8(r.result)); };
      r.onerror = function () { rej(r.error); };
      r.readAsArrayBuffer(blob);
    });
  }
  function slice(blob, a, b) { return bytesOf(blob.slice(a, b)); }
  function join(chunks, n) {
    var out = new Uint8Array(n), at = 0;
    chunks.forEach(function (c) { out.set(c, at); at += c.length; });
    return out;
  }
  function view(b) { return new DataView(b.buffer, b.byteOffset, b.byteLength); }

  /* ------------------------------------------------------------------ CRC-32 */
  var TABLE = null;
  function crc32(bytes, crc) {
    if (!TABLE) {
      TABLE = new Int32Array(256);
      for (var n = 0; n < 256; n++) {
        var c = n;
        for (var k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        TABLE[n] = c;
      }
    }
    var x = (crc >>> 0) ^ -1;
    for (var i = 0; i < bytes.length; i++) x = TABLE[(x ^ bytes[i]) & 0xff] ^ (x >>> 8);
    return (x ^ -1) >>> 0;
  }

  /* ------------------------------------------------------------------ writing a .zip */
  /* The archive, as the ZIP format (APPNOTE 6.3) lays it out: each file's local header and its data, then
     the central directory (one record per file) and its end record. Names in UTF-8 (flag bit 11); the
     date and time are when the backup is made (the visitor's clock). No ZIP64: 4 GB or 65,535 files at
     most — far more than any ledger's photos. */
  function zip(files, when) {
    var d = when && typeof when.getTime === "function" && !isNaN(when.getTime()) ? when : new Date();
    var time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
    var date = ((Math.min(Math.max(d.getFullYear(), 1980), 2107) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    var list = Array.isArray(files) ? files : [], parts = [], central = [], offset = 0, seen = {};
    var add = function (i) {
      if (i >= list.length) return Promise.resolve();
      var f = list[i], data = f && f.data;
      var name = utf8(f && f.name);
      if (!name.length || name.length > 0xffff || has(seen, f.name)) return Promise.reject(new Error("zip: a name is empty or used twice"));
      seen[f.name] = 1;
      var read = isBlob(data) ? bytesOf(data) : Promise.resolve(typeof data === "string" ? utf8(data) : u8(data));
      return read.then(function (bytes) {
        var crc = crc32(bytes), size = bytes.length;
        if (offset + 30 + name.length + size > 0xffffffff) throw fail("expenses.err.backup_too_big");
        var local = new Uint8Array(30 + name.length), l = view(local);
        l.setUint32(0, 0x04034b50, true); l.setUint16(4, 20, true); l.setUint16(6, 0x0800, true); l.setUint16(8, 0, true);
        l.setUint16(10, time, true); l.setUint16(12, date, true); l.setUint32(14, crc, true); l.setUint32(18, size, true);
        l.setUint32(22, size, true); l.setUint16(26, name.length, true); l.setUint16(28, 0, true);
        local.set(name, 30);
        var cd = new Uint8Array(46 + name.length), c = view(cd);
        c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
        c.setUint16(10, 0, true); c.setUint16(12, time, true); c.setUint16(14, date, true); c.setUint32(16, crc, true);
        c.setUint32(20, size, true); c.setUint32(24, size, true); c.setUint16(28, name.length, true);
        c.setUint32(42, offset, true);
        cd.set(name, 46);
        // the Blob itself goes in (the browser copies it when the archive is saved), not the bytes just read
        parts.push(local, isBlob(data) ? data : bytes);
        central.push(cd);
        offset += local.length + size;
        return add(i + 1);
      });
    };
    return add(0).then(function () {
      if (central.length > 0xffff) throw fail("expenses.err.backup_too_big");
      var size = central.reduce(function (n, x) { return n + x.length; }, 0);
      var end = new Uint8Array(22), e = view(end);
      e.setUint32(0, 0x06054b50, true); e.setUint16(8, central.length, true); e.setUint16(10, central.length, true);
      e.setUint32(12, size, true); e.setUint32(16, offset, true);
      return new Blob(parts.concat(central, [end]), { type: "application/zip" });
    });
  }

  /* ------------------------------------------------------------------ reading a .zip */
  function readZip(blob) {
    if (!isBlob(blob)) blob = new Blob([u8(blob)]);
    var size = blob.size;
    if (size < 22) return Promise.reject(fail("expenses.err.zip_damaged"));
    // the end record: in the last 22 bytes, or before a comment of up to 65,535
    var tail = Math.min(size, 22 + 0xffff);
    return slice(blob, size - tail, size).then(function (t) {
      var at = -1;
      for (var i = t.length - 22; i >= 0; i--) if (t[i] === 0x50 && t[i + 1] === 0x4b && t[i + 2] === 5 && t[i + 3] === 6) { at = i; break; }
      if (at < 0) throw fail("expenses.err.zip_damaged");
      var v = view(t), count = v.getUint16(at + 10, true), cdSize = v.getUint32(at + 12, true), cdOff = v.getUint32(at + 16, true);
      // (ZIP64 — 0xFFFF / 0xFFFFFFFF here — is never one of ours, nor an Excel workbook)
      if (count === 0xffff || cdOff === 0xffffffff || cdOff + cdSize > size) throw fail("expenses.err.zip_damaged");
      return slice(blob, cdOff, cdOff + cdSize).then(function (cd) {
        var c = view(cd), p = 0, entries = [], byName = {};
        for (var k = 0; k < count; k++) {
          if (p + 46 > cd.length || c.getUint32(p, true) !== 0x02014b50) throw fail("expenses.err.zip_damaged");
          var nlen = c.getUint16(p + 28, true), xlen = c.getUint16(p + 30, true), mlen = c.getUint16(p + 32, true);
          var e = { name: text(cd.subarray(p + 46, p + 46 + nlen)), flags: c.getUint16(p + 8, true), method: c.getUint16(p + 10, true),
            crc: c.getUint32(p + 16, true), csize: c.getUint32(p + 20, true), size: c.getUint32(p + 24, true), offset: c.getUint32(p + 42, true) };
          entries.push(e);
          if (!has(byName, e.name)) byName[e.name] = e;
          p += 46 + nlen + xlen + mlen;
        }
        return archive(blob, entries, byName);
      });
    });
  }
  function archive(blob, entries, byName) {
    var find = function (name) { return typeof name === "string" ? (has(byName, name) ? byName[name] : null) : name || null; };
    var bytes = function (name, limit) {
      var e = find(name);
      if (!e) return Promise.reject(fail("expenses.err.zip_damaged"));
      if (e.flags & 1) return Promise.reject(fail("expenses.err.zip_locked"));           // a password
      if (e.size > (limit || PART)) return Promise.reject(fail("expenses.err.part_too_big"));
      // the data starts after the file's own (local) header, whose name and extra field may differ in length
      return slice(blob, e.offset, e.offset + 30).then(function (h) {
        if (h.length < 30 || view(h).getUint32(0, true) !== 0x04034b50) throw fail("expenses.err.zip_damaged");
        var start = e.offset + 30 + view(h).getUint16(26, true) + view(h).getUint16(28, true);
        if (start + e.csize > blob.size) throw fail("expenses.err.zip_damaged");
        return slice(blob, start, start + e.csize);
      }).then(function (raw) {
        if (e.method === 0) return raw;
        if (e.method === 8) return inflate(raw, e.size);
        throw fail("expenses.err.zip_damaged");                                          // (a method nobody uses)
      }).then(function (out) {
        if (out.length !== e.size || crc32(out) !== e.crc) throw fail("expenses.err.zip_damaged");
        return out;
      });
    };
    return {
      entries: entries,
      has: function (name) { return !!find(name); },
      bytes: bytes,
      text: function (name, limit) { return bytes(name, limit).then(text); },
      blob: function (name, type) { return bytes(name).then(function (b) { return new Blob([b], { type: type || "" }); }); },
    };
  }
  // DEFLATE (RFC 1951) through the browser: Chrome 103, Firefox 113, Safari 16.4 and later
  function inflate(raw, size) {
    var ds;
    try { ds = new DecompressionStream("deflate-raw"); } catch (e) { return Promise.reject(fail("expenses.err.zip_browser")); }
    var w = ds.writable.getWriter();
    w.write(raw).catch(noop);
    w.close().catch(noop);
    var r = ds.readable.getReader(), chunks = [], n = 0;
    var pump = function () {
      return r.read().then(function (x) {
        if (x.done) return join(chunks, n);
        n += x.value.length;
        if (n > size) { r.cancel().catch(noop); throw fail("expenses.err.zip_damaged"); }
        chunks.push(u8(x.value));
        return pump();
      });
    };
    return pump().catch(function (e) { throw e && e.key ? e : fail("expenses.err.zip_damaged"); });
  }

  /* ------------------------------------------------------------------ Excel (.xlsx) */
  // XML text: the five entities, character references, and Excel's own _xHHHH_ (a control character in a cell)
  function unxml(s) {
    return String(s).replace(/&(?:#(\d+)|#x([0-9a-f]+)|(amp|lt|gt|quot|apos));/gi, function (m, d, h, n) {
      if (n) return { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" }[n.toLowerCase()];
      var cp = d ? Number(d) : parseInt(h, 16);
      return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "";
    }).replace(/_x([0-9A-Fa-f]{4})_/g, function (m, h) { return String.fromCharCode(parseInt(h, 16)); });
  }
  // an element's attributes by name, and by their name without a prefix (r:id is also "id"; an attribute
  // with no prefix wins)
  function attrs(s) {
    var o = {}, re = /([\w:.-]+)\s*=\s*"([^"]*)"/g, m;
    while ((m = re.exec(s))) {
      var local = m[1].replace(/^[\w.-]+:/, "");
      o[m[1]] = m[2];
      if (local === m[1] || !has(o, local)) o[local] = m[2];
    }
    return o;
  }
  // the text from `from` up to the closing tag `close` matches (a global regex) → [text, the index after
  // the closing tag], or null when it never closes
  function upTo(xml, from, close) {
    close.lastIndex = from;
    var m = close.exec(xml);
    return m ? [xml.slice(from, m.index), close.lastIndex] : null;
  }
  // the text of a string item: its <t>, or each run's <t> — never a phonetic guide (<rPh>)
  function runText(x) {
    var s = "", re = /<(?:\w+:)?t(\s[^>]*?)?(\/?)>/g, close = /<\/(?:\w+:)?t>/g, m, got;
    x = String(x).replace(/<(?:\w+:)?rPh\b[\s\S]*?<\/(?:\w+:)?rPh>/g, "");
    while ((m = re.exec(x))) {
      if (m[2]) continue;                                     // <t/>: empty
      if (!(got = upTo(x, re.lastIndex, close))) break;
      s += got[0];
      re.lastIndex = got[1];
    }
    return unxml(s);
  }
  function sharedStrings(xml) {
    var out = [], re = /<(?:\w+:)?si\b[^>]*?(\/?)>/g, close = /<\/(?:\w+:)?si>/g, m, got;
    while ((m = re.exec(xml))) {
      if (m[1]) { out.push(""); continue; }
      if (!(got = upTo(xml, re.lastIndex, close))) break;
      out.push(runText(got[0]));
      re.lastIndex = got[1];
    }
    return out;
  }
  // Excel's built-in date formats (14–17 and 22; 27–36 and 50–58 are the East Asian ones)
  var DATE_FMT = {};
  [14, 15, 16, 17, 22, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 50, 51, 52, 53, 54, 55, 56, 57, 58].forEach(function (n) { DATE_FMT[n] = 1; });
  // a number format of the workbook's own that shows a date: a d or a y, or an m with no hour or second
  // ("mmm-yy"; "h:mm" is a time) — once quoted text, [colours] and escaped characters are out
  function isDateCode(code) {
    var c = String(code).replace(/"[^"]*"/g, "").replace(/\\./g, "").replace(/\[[^\]]*\]/g, "").replace(/[_*]./g, "");
    return /[dy]/i.test(c) || (/m/i.test(c) && !/[hs]/i.test(c));
  }
  // → for each cell style (the s="…" of a cell, cellXfs in order): does it show a date?
  function dateStyles(xml) {
    var codes = {}, out = [], m, re = /<(?:\w+:)?numFmt\b([^>]*)>/g;
    while ((m = re.exec(xml))) { var a = attrs(m[1]); if (a.numFmtId) codes[a.numFmtId] = unxml(a.formatCode || ""); }
    var xfs = /<(?:\w+:)?cellXfs\b[^>]*>([\s\S]*?)<\/(?:\w+:)?cellXfs>/.exec(xml);
    if (!xfs) return out;
    var re2 = /<(?:\w+:)?xf\b([^>]*)>/g;
    while ((m = re2.exec(xfs[1]))) {
      var id = attrs(m[1]).numFmtId || "0";
      out.push(!!DATE_FMT[Number(id)] || (has(codes, id) && isDateCode(codes[id])));
    }
    return out;
  }
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  // an Excel date: days since 1899-12-30 (since 1904-01-01 in a workbook made with the 1904 system), a time
  // of day as the fraction
  function serialDate(n, d1904) {
    var days = Math.floor(n), mins = Math.round((n - days) * 1440);
    if (mins >= 1440) { days += 1; mins -= 1440; }
    var d = new Date(Date.UTC(1899, 11, 30) + (days + (d1904 ? 1462 : 0)) * 864e5);
    var time = mins ? pad2(Math.floor(mins / 60)) + ":" + pad2(mins % 60) : "";
    if (!days && !d1904) return time;                         // a time of day alone
    return d.getUTCFullYear() + "-" + pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()) + (time ? " " + time : "");
  }
  // a number as Excel shows it: 15 significant digits (12.339999999999998 is 12.34), never an exponent
  function numText(v, isDate, d1904) {
    var n = Number(v);
    if (v === "" || !isFinite(n)) return v;
    if (isDate && n >= 0 && n < 2958466) return serialDate(n, d1904);
    var s = String(Number(n.toPrecision(15)));
    if (/e/i.test(s) && Math.abs(n) < 1) s = Number(n.toPrecision(15)).toFixed(20).replace(/0+$/, "").replace(/\.$/, "");
    return s;
  }
  function colIndex(letters) {
    var n = 0;
    for (var i = 0; i < letters.length; i++) n = n * 26 + (letters.toUpperCase().charCodeAt(i) - 64);
    return n - 1;
  }
  /* A worksheet's XML → rows of text, from its first row with something in it (the header); an empty row
     inside the sheet stays (so a row number in a message is the sheet's own, counted from the header). */
  function sheetRows(xml, shared, dates, d1904, maxRows) {
    var rows = [], re = /<(\/?)(?:\w+:)?(row|c)\b([^>]*?)(\/?)>/g, close = /<\/(?:\w+:)?c>/g, m, got, row = -1, col = 0, top = -1;
    while ((m = re.exec(xml))) {
      if (m[1]) continue;
      var a = attrs(m[3]);
      if (m[2] === "row") { var rn = Number(a.r); row = rn >= 1 ? rn - 1 : row + 1; col = 0; continue; }
      var ref = /^([A-Za-z]{1,3})(\d+)$/.exec(a.r || ""), ci = ref ? colIndex(ref[1]) : col, ri = ref ? Number(ref[2]) - 1 : Math.max(row, 0);
      col = ci + 1;
      var body = "";
      if (!m[4]) {
        if (!(got = upTo(xml, re.lastIndex, close))) break;
        body = got[0];
        re.lastIndex = got[1];
      }
      var t = a.t || "n", v = /<(?:\w+:)?v\b[^>]*>([\s\S]*?)<\/(?:\w+:)?v>/.exec(body), val = v ? unxml(v[1]) : "", out;
      if (t === "s") out = v && has(shared, Number(val)) ? shared[Number(val)] : "";
      else if (t === "inlineStr") out = runText(body);
      else if (t === "b") out = val === "1" ? "TRUE" : val === "0" ? "FALSE" : val;
      else if (t === "str" || t === "e" || t === "d") out = val;
      else out = numText(val, !!dates[Number(a.s) || 0], d1904);
      if (out === "" || ri < 0 || ci < 0 || ci > 16383) continue;
      if (ri >= maxRows + Math.max(top, 0)) { rows.error = "expenses.err.too_many_rows"; break; }
      if (top < 0 || ri < top) top = ri;
      (rows[ri] = rows[ri] || [])[ci] = out;
    }
    var outRows = [];
    if (top >= 0) {
      for (var r = top; r < rows.length; r++) {
        var cells = rows[r] || [], line = [];
        for (var k = 0; k < cells.length; k++) line.push(cells[k] === undefined ? "" : cells[k]);
        outRows.push(line);
      }
    }
    if (rows.error) outRows.error = rows.error;
    return outRows;
  }
  // the first worksheet: the workbook's first <sheet>, found through its relationship — else sheet1.xml
  function firstSheet(wb, rels, ar) {
    var s = /<(?:\w+:)?sheet\b([^>]*)>/.exec(wb), id = s ? attrs(s[1]).id : "";
    var re = /<(?:\w+:)?Relationship\b([^>]*)>/g, m;
    while (id && (m = re.exec(rels))) {
      var a = attrs(m[1]);
      if (a.Id !== id || !a.Target) continue;
      var p = a.Target.charAt(0) === "/" ? a.Target.slice(1) : "xl/" + a.Target.replace(/^\.\//, "");
      if (ar.has(p)) return p;
    }
    var all = ar.entries.map(function (e) { return e.name; }).filter(function (n) { return /^xl\/worksheets\/[^/]+\.xml$/.test(n); }).sort();
    return ar.has("xl/worksheets/sheet1.xml") ? "xl/worksheets/sheet1.xml" : all[0] || "";
  }
  function xlsxRows(ar, opts) {
    var maxRows = opts && opts.maxRows > 0 ? opts.maxRows : 20001;
    var get = function (name) { return ar.has(name) ? ar.text(name) : Promise.resolve(""); };
    return Promise.all([get("xl/workbook.xml"), get("xl/_rels/workbook.xml.rels")]).then(function (wb) {
      var sheet = firstSheet(wb[0], wb[1], ar);
      if (!sheet) return [];
      var d1904 = /<(?:\w+:)?workbookPr\b[^>]*\bdate1904="(1|true)"/i.test(wb[0]);
      return Promise.all([ar.text(sheet), get("xl/sharedStrings.xml"), get("xl/styles.xml")]).then(function (p) {
        return sheetRows(p[0], sharedStrings(p[1]), dateStyles(p[2]), d1904, maxRows);
      });
    }).catch(function (e) {
      // (an Excel workbook is always compressed: a browser that can't unpack it can't read one)
      throw e && e.key === "expenses.err.zip_browser" ? fail("expenses.err.xlsx_browser") : e;
    });
  }

  /* ------------------------------------------------------------------ a big .json backup, in slices */
  /* GVX.toBackup writes {"format":…,"entries":[…],"settings":{…},"meta":{…},"receipts":[{"id":…,"type":…,
     "dataUrl":"data:image/jpeg;base64,…"},…]} — the photos last, and nearly all of the file. The part before
     ,"receipts":[ is the backup without them (a quote inside a JSON string is always \", so those bytes are
     the key itself); each photo is then found by its braces, strings skipped whole, and only its id and type
     are read now. A file not laid out so (or not a backup at all) → null. */
  var RECEIPTS = utf8(',"receipts":[');
  function findBytes(blob, pat, chunk) {
    var size = blob.size;
    var step = function (off) {
      if (off >= size) return Promise.resolve(-1);
      return slice(blob, off, Math.min(size, off + chunk + pat.length - 1)).then(function (c) {
        for (var i = c.indexOf(pat[0]); i >= 0 && i + pat.length <= c.length; i = c.indexOf(pat[0], i + 1)) {
          var k = 1;
          while (k < pat.length && c[i + k] === pat[k]) k++;
          if (k === pat.length) return off + i;
        }
        return step(off + chunk);
      });
    };
    return step(0);
  }
  // the photos' byte ranges [start, end) in the receipts array, each with the id and type its first bytes give
  function scanReceipts(blob, from, chunk) {
    var size = blob.size, found = [], depth = 0, inStr = false, bs = 0, start = -1, done = false;
    var step = function (off) {
      if (done) return Promise.resolve(found);
      if (off >= size) return Promise.resolve(null);                       // never closed: not a whole file
      return slice(blob, off, Math.min(size, off + chunk)).then(function (c) {
        var i = 0, n = c.length;
        while (i < n && !done) {
          if (inStr) {
            var q = c.indexOf(34, i);
            if (q < 0) {
              // the string goes on into the next slice: how many backslashes it ends with here
              var t = n - 1, run = 0;
              while (t >= i && c[t] === 92) { run++; t--; }
              bs = t < 0 ? bs + run : run;
              i = n;
              break;
            }
            var k = q - 1, back = 0;
            while (k >= i && c[k] === 92) { back++; k--; }
            if (k < 0) back += bs;                                          // (they began in the last slice)
            bs = 0;
            i = q + 1;
            if (back % 2 === 0) inStr = false;                               // an odd number escapes it
            continue;
          }
          var b = c[i];
          if (b === 34) { inStr = true; bs = 0; }
          else if (b === 123) {
            if (depth === 0) {
              start = off + i;
              var head = text(c.subarray(i, Math.min(n, i + 256)));
              var id = /^\{\s*"id"\s*:\s*"([A-Za-z0-9_-]{1,64})"/.exec(head), ty = /"type"\s*:\s*"(image\/(?:jpeg|png|webp|gif))"/i.exec(head);
              found.push({ start: start, end: -1, id: id ? id[1] : "", type: ty ? ty[1] : "" });
            }
            depth++;
          } else if (b === 125) {
            depth--;
            if (depth === 0 && found.length) found[found.length - 1].end = off + i + 1;
            else if (depth < 0) done = true;
          } else if (b === 93 && depth === 0) done = true;
          i++;
        }
        return step(off + n);
      });
    };
    return step(from);
  }
  function jsonBackup(blob, opts) {
    var chunk = opts && opts.chunk > 64 ? opts.chunk : CHUNK;
    return findBytes(blob, RECEIPTS, chunk).then(function (at) {
      if (at < 0) return null;
      return slice(blob, 0, at).then(function (bytes) {
        var head = null;
        try { head = JSON.parse(text(bytes) + "}"); } catch (e) { return null; }
        if (!head || typeof head !== "object" || Array.isArray(head)) return null;
        return scanReceipts(blob, at + RECEIPTS.length, chunk).then(function (found) {
          if (!found) return null;
          var read = function (r) {
            return slice(blob, r.start, r.end).then(function (b) { var o = JSON.parse(text(b)); return o && typeof o === "object" ? o : {}; });
          };
          // a photo whose id is not at its start (a file written some other way): read it whole, now
          var ids = found.filter(function (r) { return r.end > r.start; }).reduce(function (p, r) {
            return r.id ? p : p.then(function () { return read(r).then(function (o) { r.id = String(o.id || ""); r.type = String(o.type || ""); }, noop); });
          }, Promise.resolve());
          return ids.then(function () {
            return {
              head: head,
              receipts: found.filter(function (r) { return r.end > r.start && /^[A-Za-z0-9_-]{1,64}$/.test(r.id); }).map(function (r) {
                return { id: r.id, type: r.type || "image/jpeg", load: function () {
                  return read(r).then(function (o) {
                    var b = dataUrlBytes(o.dataUrl);
                    if (!b || !/^data:image\/(jpeg|png|webp|gif)[;,]/i.test(String(o.dataUrl))) throw fail("expenses.err.zip_damaged");
                    return new Blob([b.bytes], { type: b.type });
                  });
                } };
              }),
            };
          });
        });
      });
    });
  }
  // "data:image/jpeg;base64,/9j/…" → {type, bytes}
  function dataUrlBytes(url) {
    var m = /^data:([^;,]+)?((?:;[^;,]*)*?)(;base64)?,([\s\S]*)$/.exec(String(url || ""));
    if (!m) return null;
    try {
      var bin = m[3] ? atob(m[4].replace(/\s+/g, "")) : decodeURIComponent(m[4]), out = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return { type: m[1] || "image/jpeg", bytes: out };
    } catch (e) { return null; }
  }

  root.GVF = { KEYS: KEYS, crc32: crc32, zip: zip, readZip: readZip, xlsxRows: xlsxRows, jsonBackup: jsonBackup, dataUrlBytes: dataUrlBytes };
})(typeof window !== "undefined" ? window : globalThis);
