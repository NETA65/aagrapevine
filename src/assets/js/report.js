/* The district-meeting report editor on /monthly/#report (src/pages/monthly.njk).
   The report's sections come from the build (eleventy/filters/report.js → <script id="rp-data">, both
   languages); the editor's own words from <script id="rp-ui"> (page language). Each GVR / RLV can
   switch sections on and off, reorder them, edit any text, add their own sections and pick the
   counties near their district for the Grapevine meetings; the preview updates as they type.
   Output: plain text (copy / WhatsApp / e-mail / .txt), formatted text (copy → e-mail or Word), a
   Word file (.docx, written here: a small stored ZIP, no library) and print (print CSS in
   areas/report.css prints only the report).
   Drafts: localStorage, per month and report language ("gv-report:YYYY-MM:en"), plus the
   "Your details" fields ("gv-report:profile") and the report language ("gv-report:lang").
   Only the CHANGES are stored, so a section nobody edited always shows the latest data. A new month
   starts fresh, and offers last month's draft as its starting point (findPrev: the visitor's own
   sections, choices and words; the data sections are the new month's). Storage may fail (blocked site
   data, a full device): every access is wrapped, and the page works without it. (A private window saves
   until it is closed, and the page can't tell.)
   "For: Area" (mode "area"): the chair's report to an assembly or an Area committee meeting, for the dates the
   chair picks — the build's dated pieces (<script id="rp-area">, eleventy/filters/report.js areaModel) joined here
   for the dates (areaSections), one document: the English part, then the Spanish one. The language switch picks
   the part being edited; copy, share, print and the Word file give both. The working report
   ("gv-report:area:work"), the earlier ones ("gv-report:area:done") and the mode ("gv-report:mode"): the comment
   at the top of the Area report's code below.
   Without JavaScript the page shows the whole district report as text (.rp-nojs). */
(function () {
  "use strict";
  var GV = window.GV || {};
  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";
  var PREFIX = "gv-report:";
  var WA_MAX = 6000;     // longest wa.me link we open (longer: copy + paste instead)
  var MAIL_MAX = 1800;   // longest mailto: link (Windows / Outlook stop near 2,000)
  var WPM = 130;         // reading aloud
  var BOM = String.fromCharCode(0xfeff);
  var NBSP = String.fromCharCode(0xa0);
  var WJ = String.fromCharCode(0x2060);   // word joiner: no line break there
  var OWN_TEXT = ["asks", "notes"];       // the sections that are the visitor's own words (last month's draft keeps them)
  var OWN_TEXT_AREA = ["invite", "notes"]; // … and the Area report's ("Start from your … report?" keeps them)

  /* ---------------- small helpers ---------------- */
  function load(k) { try { var s = localStorage.getItem(k); return s ? JSON.parse(s) : null; } catch (e) { return null; } }
  function store(k, v) {
    try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; }
  }
  // "k in o" (not hasOwnProperty): Alpine's reactive proxies track `in`, so a section's first edit
  // updates the preview. Keys are section ids, never inherited names.
  function has(o, k) { return !!o && k in o && o[k] !== undefined; }
  function str(v, max) { return typeof v === "string" ? v.slice(0, max || 20000) : ""; }
  function fmt(tpl, vars) {
    return String(tpl || "").replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] != null ? String(vars[k]) : m; });
  }
  function clean(s) { return String(s == null ? "" : s).replace(/\s+/g, " ").trim(); }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function slug(s) { return clean(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 24); }
  // Only the characters XML 1.0 allows reach the Word file (Word refuses to open a file with any other): tab, line
  // breaks, U+0020–U+D7FF, U+E000–U+FFFD and the pairs of surrogates that make a character above U+FFFF. Dropped:
  // the other control characters, U+FFFE / U+FFFF (they come along when text is pasted from some documents) and a
  // lone surrogate.
  function xmlText(s) {
    var out = "";
    s = String(s);
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c >= 0xd800 && c <= 0xdbff) {
        var n = s.charCodeAt(i + 1);
        if (n >= 0xdc00 && n <= 0xdfff) { out += s.charAt(i) + s.charAt(i + 1); i++; }
        continue;
      }
      if (c === 9 || c === 10 || c === 13 || (c >= 0x20 && c <= 0xd7ff) || (c >= 0xe000 && c <= 0xfffd)) out += s.charAt(i);
    }
    return out.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ---------------- the report: text and blocks ---------------- */
  /* The sections joined as the report — the same rules as composeText in eleventy/filters/report.js:
     the header as it is, then "1. Title" + text; an empty section is left out. */
  function compose(sections) {
    var out = [], n = 0;
    sections.forEach(function (s) {
      var body = String(s.text || "").replace(/\r\n?/g, "\n").replace(/\s+$/, "").replace(/^\n+/, "");
      if (!body.trim()) return;
      if (s.id === "header") out.push(body);
      else out.push((++n) + ". " + clean(s.title) + "\n" + body);
    });
    return out.join("\n\n") + "\n";
  }

  /* The same report as blocks for the preview, the formatted copy and the Word file: the header's
     first line is the title, its other lines the byline; a line starting with • - * or · is a list
     item (an indented line after it continues it); every other line is a paragraph.
     (The Area report's part not being edited: `tag` before each section id — its sections are never the one
     highlighted —, and every block carries its part's `lang`.) */
  function blocks(sections, tag, lang) {
    var out = [], n = 0;
    tag = tag || "";
    sections.forEach(function (s) {
      var body = String(s.text || "").replace(/\r\n?/g, "\n");
      if (!body.trim()) return;
      var sec = tag + s.id;
      if (s.id === "header") {
        var lines = body.split("\n").map(clean).filter(Boolean);
        out.push({ t: "title", text: lines[0], sec: sec, lang: lang });
        lines.slice(1).forEach(function (l) { out.push({ t: "meta", text: l, sec: sec, lang: lang }); });
        return;
      }
      n++;
      out.push({ t: "h", text: n + ". " + clean(s.title), sec: sec, lang: lang });
      var list = null;
      body.split("\n").forEach(function (line) {
        if (!line.trim()) { list = null; return; }
        var m = /^\s*[•·*-]\s+(.*)$/.exec(line);
        if (m) {
          if (!list) { list = { t: "ul", items: [], sec: sec, lang: lang }; out.push(list); }
          list.items.push(m[1].trim());
          return;
        }
        if (list && /^\s{2,}\S/.test(line)) { list.items[list.items.length - 1] += "\n" + line.trim(); return; }
        list = null;
        out.push({ t: "p", text: line.trim(), sec: sec, lang: lang });
      });
    });
    return out;
  }

  // Links and e-mail addresses inside a line (a trailing period or bracket is not part of a link).
  var LINK = /(https?:\/\/[^\s<>"]*[^\s<>".,;:!?)\]’”])|([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/g;
  function splitLinks(text) {
    var parts = [], last = 0, m;
    LINK.lastIndex = 0;
    while ((m = LINK.exec(text))) {
      if (m.index > last) parts.push({ text: text.slice(last, m.index) });
      parts.push({ text: m[0], href: m[1] ? m[1] : "mailto:" + m[2] });
      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push({ text: text.slice(last) });
    return parts;
  }
  // HTML of one line: links; in the preview, [blanks] are marked.
  function inline(text, o) {
    return splitLinks(text).map(function (p) {
      if (p.href) {
        var ext = /^https?:/.test(p.href) && o.newTab;
        return '<a href="' + esc(p.href) + '"' + (o.link ? ' style="' + o.link + '"' : "") + (ext ? ' target="_blank" rel="noopener"' : "") + ">" + esc(p.text) + "</a>";
      }
      // never "La / Viña" or "7– / 8 PM" at a line end
      var h = esc(p.text).replace(/La Viña/g, "La" + NBSP + "Viña").replace(/(\d)–(\d)/g, "$1–" + WJ + "$2");
      return o.marks ? h.replace(/\[([^\]\n]{1,80})\]/g, '<mark class="rp-blank">[$1]</mark>') : h;
    }).join("").replace(/\n/g, "<br>");
  }

  /* The on-screen preview: one wrapper per section (data-sec) so the section being edited can be
     shown and highlighted. Headings are h4 (the page: h2 section → h3 "Your report"). */
  function previewHtml(bl, active) {
    var h = "", cur = null;
    var o = { marks: true, newTab: true };
    bl.forEach(function (b) {
      // the Area report: the line between its English and its Spanish part (print: the Spanish part on a new page)
      if (b.t === "split") {
        if (cur !== null) h += "</div>";
        cur = null;
        h += '<hr class="rp-doc-split">';
        return;
      }
      if (b.sec !== cur) {
        if (cur !== null) h += "</div>";
        cur = b.sec;
        h += '<div class="rp-doc-sec' + (b.sec === active ? " is-active" : "") + '" data-sec="' + esc(b.sec) + '"' + (b.lang ? ' lang="' + esc(b.lang) + '"' : "") + ">";
      }
      if (b.t === "title") h += '<p class="rp-doc-title">' + inline(b.text, o) + "</p>";
      else if (b.t === "meta") h += '<p class="rp-doc-meta">' + inline(b.text, o) + "</p>";
      else if (b.t === "h") h += '<h4 class="rp-doc-h">' + inline(b.text, o) + "</h4>";
      else if (b.t === "p") h += "<p>" + inline(b.text, o) + "</p>";
      else if (b.t === "ul") h += "<ul>" + b.items.map(function (i) { return "<li>" + inline(i, o) + "</li>"; }).join("") + "</ul>";
    });
    if (cur !== null) h += "</div>";
    return h;
  }

  /* Formatted copy for e-mail and word processors: inline styles only (mail apps drop <style>). */
  function emailHtml(bl, lang) {
    var o = { link: "color:#0b57a4" };
    var h = '<div lang="' + lang + '" style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;color:#1a1a1a">';
    bl.forEach(function (b) {
      // a block of the other language's part (the Area report) says its language
      var l = b.lang && b.lang !== lang ? ' lang="' + b.lang + '"' : "";
      if (b.t === "split") h += '<hr style="margin:28px 0;border:0;border-top:1px solid #bbbbbb">';
      else if (b.t === "title") h += "<h1" + l + ' style="font-size:20px;line-height:1.3;margin:0 0 4px">' + inline(b.text, o) + "</h1>";
      else if (b.t === "meta") h += "<p" + l + ' style="margin:0 0 2px;color:#555555">' + inline(b.text, o) + "</p>";
      else if (b.t === "h") h += "<h2" + l + ' style="font-size:16px;line-height:1.3;margin:18px 0 6px">' + inline(b.text, o) + "</h2>";
      else if (b.t === "p") h += "<p" + l + ' style="margin:0 0 6px">' + inline(b.text, o) + "</p>";
      else if (b.t === "ul") h += "<ul" + l + ' style="margin:0 0 8px;padding-left:22px">' + b.items.map(function (i) { return '<li style="margin:0 0 4px">' + inline(i, o) + "</li>"; }).join("") + "</ul>";
    });
    return h + "</div>";
  }

  /* ---------------- Word (.docx): WordprocessingML in a stored ZIP ---------------- */
  var CRC = null;
  function crc32(u8) {
    if (!CRC) {
      CRC = new Uint32Array(256);
      for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[n] = c >>> 0; }
    }
    var crc = 0xffffffff;
    for (var i = 0; i < u8.length; i++) crc = CRC[(crc ^ u8[i]) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }
  function zipBlob(files, type) {
    var enc = new TextEncoder(), parts = [], central = [], offset = 0, now = new Date();
    var time = ((now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)) & 0xffff;
    var date = (((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()) & 0xffff;
    files.forEach(function (f) {
      var name = enc.encode(f.name), data = enc.encode(f.text), crc = crc32(data);
      var lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
      lh.setUint16(10, time, true); lh.setUint16(12, date, true); lh.setUint32(14, crc, true);
      lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
      parts.push(new Uint8Array(lh.buffer), name, data);
      var ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true);
      ch.setUint16(12, time, true); ch.setUint16(14, date, true); ch.setUint32(16, crc, true);
      ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, name.length, true);
      ch.setUint16(30, 0, true); ch.setUint16(32, 0, true); ch.setUint16(34, 0, true); ch.setUint16(36, 0, true); ch.setUint32(38, 0, true); ch.setUint32(42, offset, true);
      central.push(new Uint8Array(ch.buffer), name);
      offset += 30 + name.length + data.length;
    });
    var size = 0;
    central.forEach(function (p) { size += p.length; });
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, size, true); end.setUint32(16, offset, true);
    return new Blob(parts.concat(central, [new Uint8Array(end.buffer)]), { type: type });
  }

  var W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
  var RELS = "http://schemas.openxmlformats.org/package/2006/relationships";
  var OREL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
  var XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';

  function docx(bl, lang, title) {
    var rels = [];
    var WLANG = { en: "en-US", es: "es-419" };
    // (a block of the other language's part — the Area report — marks its words with their language, so Word checks
    // their spelling as Spanish)
    function runs(text, bLang) {
      var lp = bLang && bLang !== lang && WLANG[bLang] ? '<w:lang w:val="' + WLANG[bLang] + '"/>' : "";
      return splitLinks(text).map(function (p) {
        var t = p.text.split("\n").map(function (seg) { return '<w:t xml:space="preserve">' + xmlText(seg) + "</w:t>"; }).join("<w:br/>");
        if (!p.href) return "<w:r>" + (lp ? "<w:rPr>" + lp + "</w:rPr>" : "") + t + "</w:r>";
        var id = "rId" + (rels.length + 10);
        rels.push('<Relationship Id="' + id + '" Type="' + OREL + '/hyperlink" Target="' + xmlText(p.href) + '" TargetMode="External"/>');
        return '<w:hyperlink r:id="' + id + '" w:history="1"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/>' + lp + "</w:rPr>" + t + "</w:r></w:hyperlink>";
      }).join("");
    }
    function para(style, inner) { return "<w:p><w:pPr><w:pStyle w:val=\"" + style + "\"/></w:pPr>" + inner + "</w:p>"; }
    var body = bl.map(function (b) {
      if (b.t === "split") return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>';   // the Spanish part starts a page
      if (b.t === "title") return para("Title", runs(b.text, b.lang));
      if (b.t === "meta") return para("Subtitle", runs(b.text, b.lang));
      if (b.t === "h") return para("Heading1", runs(b.text, b.lang));
      if (b.t === "p") return para("Normal", runs(b.text, b.lang));
      return b.items.map(function (i) { return para("ListBullet", '<w:r><w:t xml:space="preserve">•</w:t></w:r><w:r><w:tab/></w:r>' + runs(i, b.lang)); }).join("");
    }).join("");
    var wlang = WLANG[lang] || "en-US";
    var document = XML + '<w:document xmlns:w="' + W + '" xmlns:r="' + OREL + '"><w:body>' + body +
      '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>';
    var styles = XML + '<w:styles xmlns:w="' + W + '">' +
      '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="' + wlang + '"/></w:rPr></w:rPrDefault>' +
      '<w:pPrDefault><w:pPr><w:spacing w:after="80" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>' +
      '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="60"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="1F3864"/><w:sz w:val="34"/><w:szCs w:val="34"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="40"/></w:pPr><w:rPr><w:color w:val="555555"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="280" w:after="80"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="1F3864"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40"/><w:ind w:left="360" w:hanging="360"/></w:pPr></w:style>' +
      '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>' +
      "</w:styles>";
    var docRels = XML + '<Relationships xmlns="' + RELS + '"><Relationship Id="rId1" Type="' + OREL + '/styles" Target="styles.xml"/>' + rels.join("") + "</Relationships>";
    var core = XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
      "<dc:title>" + xmlText(title) + "</dc:title><dc:language>" + wlang + '</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">' + new Date().toISOString().replace(/\.\d+Z$/, "Z") + "</dcterms:created></cp:coreProperties>";
    var types = XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
      '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>';
    var rootRels = XML + '<Relationships xmlns="' + RELS + '"><Relationship Id="rId1" Type="' + OREL + '/officeDocument" Target="word/document.xml"/>' +
      '<Relationship Id="rId2" Type="' + RELS + '/metadata/core-properties" Target="docProps/core.xml"/></Relationships>';
    return zipBlob([
      { name: "[Content_Types].xml", text: types },
      { name: "_rels/.rels", text: rootRels },
      { name: "docProps/core.xml", text: core },
      { name: "word/document.xml", text: document },
      { name: "word/styles.xml", text: styles },
      { name: "word/_rels/document.xml.rels", text: docRels },
    ], "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
  }

  /* ---------------- clipboard, files, links ---------------- */
  // The copy event lets us put plain text AND html on the clipboard where the async API is missing.
  function legacyCopy(text, html) {
    var ok = false;
    function onCopy(e) {
      try { e.clipboardData.setData("text/plain", text); if (html) e.clipboardData.setData("text/html", html); e.preventDefault(); ok = true; } catch (x) { /* no clipboardData */ }
    }
    document.addEventListener("copy", onCopy);
    try { document.execCommand("copy"); } catch (e) { /* not allowed */ }
    document.removeEventListener("copy", onCopy);
    if (ok || html) return ok;
    // Last resort: select the text in a hidden textarea (focus goes back afterwards).
    var back = document.activeElement, ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0"; ta.style.top = "0";
    document.body.appendChild(ta); ta.select();
    try { ok = document.execCommand("copy") !== false; } catch (e) { ok = false; }
    document.body.removeChild(ta);
    if (back && back.focus) back.focus({ preventScroll: true });
    return ok;
  }
  function writeText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text) ? true : Promise.reject(new Error("copy")); });
    }
    return legacyCopy(text) ? Promise.resolve(true) : Promise.reject(new Error("copy"));
  }
  function saveBlob(blob, name) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }
  // Opens a link the way a click on it would (a new tab for web links; mailto: in place).
  function openLink(href, newTab) {
    var a = document.createElement("a");
    a.href = href;
    if (newTab) { a.target = "_blank"; a.rel = "noopener"; }
    a.setAttribute("data-rp-open", "");
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { a.remove(); }, 0);
  }

  /* ---------------- the report to the Area ("For: Area") ---------------- */
  /* On this device — one design, kept small:
     * ONE working report, "gv-report:area:work" = { from, to, toFollowsToday, parts: { en, es } } (each part a draft:
       the changes only, as a month's). From and To are just two fields: changing them changes nothing else (a To
       picked by hand: toFollowsToday false; while it is true, To is today on each load). A section not edited
       shows the site's text for the dates; an edited one keeps the chair's words.
     * "Next report" (once a To picked by hand is before today; confirmed) files the working report in the ARCHIVE,
       "gv-report:area:done" (newest first, 12 at most, never edited: its dates, parts, the site's text then, the
       name and meeting), and starts a fresh one — From the day after its To, To today (following), no edits —
       with the offer "Start from your <dates> report?" (the newest one's own parts: startFromPrev).
     * "Earlier reports": the archive, read-only — Word and print from what was filed; Delete (confirmed).
     * "Start over": this part's edits are cleared; the dates and the other part stay as they are.
     * Storage that fails (a full device, blocked site data) never throws nor takes the words on screen: the page says
       so. A private window saves until it is closed (the page can't tell: the README says to download first).
     * Kept as long as the browser keeps the site's data: once something is saved or filed, the browser is asked to
       keep it (askPersist), and a Safari tab says that Safari may remove it after 7 days (sevenKind). */
  var WORK = PREFIX + "area:work", DONE = PREFIX + "area:done", DONE_MAX = 12;
  /* The build's pieces (eleventy/filters/report.js areaModel: dated rows, each written in English and Spanish) and the
     period the chair picks → each language's sections, in the shape of a month's model (langs.en / .es: sections,
     tokens …), so the editor works on them as on the district report. Recent: our events of the period (a monthly
     series once, with its dates) and the committee meetings held. Next: our events and the Area assemblies after the
     period, until the next assembly (when it is within ASSEMBLY_DAYS; else NEXT_DAYS), a monthly series once, and
     the committee meetings until then. Writers: the issues whose first day is in the period (two reports never list
     the same one). Next committee meeting: the first one after the period. */
  var AREA_IDS = ["header", "recent", "next", "writers", "invite", "meeting", "notes"];
  var AREA_SPLIT = "* * *";               // between the English and the Spanish part, in the plain text
  var NEXT_DAYS = 120, ASSEMBLY_DAYS = 200;
  function isYmd(v) { return typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && !isNaN(Date.parse(v + "T12:00:00Z")); }
  function ymdAdd(ymd, n) { return new Date(Date.parse(ymd + "T12:00:00Z") + n * 864e5).toISOString().slice(0, 10); }
  // the same day `n` months before (the 31st → that month's last day)
  function monthsBack(ymd, n) {
    var first = new Date(Date.UTC(Number(ymd.slice(0, 4)), Number(ymd.slice(5, 7)) - 1 - n, 1));
    var last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
    var d = Math.min(Number(ymd.slice(8, 10)), last);
    return first.toISOString().slice(0, 8) + (d < 10 ? "0" : "") + d;
  }
  // today in Central time (the site's zone), as the build counts days
  function todayYmd(fallback) {
    try { return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()); } catch (e) { return fallback; }
  }
  // "November 14, 2026" / "14 de noviembre de 2026"
  function longDay(ymd, lang) {
    try { return new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(ymd + "T12:00:00Z")); } catch (e) { return ymd; }
  }
  // "Aug 12 – Nov 14, 2026" / "12 de agosto – 14 de noviembre de 2026" (both years when they differ)
  function rangeLabel(a, b, lang) {
    var es = lang === "es";
    function f(ymd, year) {
      var o = es ? { day: "numeric", month: "long", timeZone: "UTC" } : { month: "short", day: "numeric", timeZone: "UTC" };
      if (year) o.year = "numeric";
      try { return new Intl.DateTimeFormat(es ? "es-US" : "en-US", o).format(new Date(ymd + "T12:00:00Z")); } catch (e) { return ymd; }
    }
    return f(a, a.slice(0, 4) !== b.slice(0, 4)) + " – " + f(b, true);
  }
  function joinList(items, lang) {
    try { return new Intl.ListFormat(lang === "es" ? "es-US" : "en-US", { style: "long", type: "conjunction" }).format(items); } catch (e) { return items.join(", "); }
  }
  // today (Central), within the days the pieces cover (A.min … A.max)
  function areaToday(A) { var t = todayYmd(A.today); return t < A.min ? A.min : t > A.max ? A.max : t; }
  /* The dates offered first: up to today (following it), from the day after the last Area assembly that ended
     before it (within ASSEMBLY_DAYS), else from the same day three months back — within A.min … A.max. */
  function areaRange(A) {
    var to = areaToday(A), from = "";
    (A.ev || []).forEach(function (r) {
      var end = r.z || r.y;
      if (r.a && end < to && end >= ymdAdd(to, -ASSEMBLY_DAYS)) from = ymdAdd(end, 1);
    });
    if (!from) from = monthsBack(to, 3);
    return { from: from < A.min ? A.min : from, to: to, toFollowsToday: true };
  }
  // What keeps two dates from being a period: "reach" (one is not a day the pieces cover, A.min … A.max), "order"
  // (the start after the end); "" — they are one.
  function rangeProblem(A, r) {
    var day = function (v) { return isYmd(v) && v >= A.min && v <= A.max; };
    if (!r || !day(r.from) || !day(r.to)) return "reach";
    return r.from > r.to ? "order" : "";
  }
  /* Safari's 7-day rule (WebKit's tracking prevention): a Safari tab — and every browser on an iPhone or iPad, all
     WebKit — may remove what a site keeps on the device after 7 days of using the browser without a tap or click
     on the site. A Home Screen app (and a Mac's "Add to Dock" app) counts its own days of use: no line. The story
     recorder's checks and wording (recorder.js keptLine, recorder-core.js helpFor): "safari" (Safari on an iPhone
     or iPad — an iPad asking for desktop sites sends a Mac's user agent, with touch points: "tapping"), "browser"
     (another browser or an app's browser there: "this browser"), "mac" (Safari on a Mac: "clicking"), ""
     (elsewhere). The line shows whether or not persist() was granted: WebKit does not say a granted one lifts the
     rule. */
  function sevenKind(ua, touch, standalone) {
    ua = String(ua || "");
    if (standalone) return "";
    var mac = /\bMacintosh\b/.test(ua), ios = /\b(iPhone|iPad|iPod)\b/.test(ua) || (mac && Number(touch) > 1);
    var other = /\b(CriOS|FxiOS|EdgiOS|OPiOS|OPT|YaBrowser|DuckDuckGo|Firefox|Chrome|Chromium|HeadlessChrome|Edg|OPR)\//.test(ua);
    var safari = !other && /\bSafari\//.test(ua);
    if (ios) return safari ? "safari" : "browser";
    return mac && safari ? "mac" : "";
  }
  function areaSections(A, L, from, to) {
    var M = A.langs[L], S = M.s, out = {}, lines = [];
    out.header = [S.h_title, fmt(S.h_period, { from: longDay(from, L), to: longDay(to, L) }), S.h_by].join("\n");

    /* Recent: ours of the period; a monthly series on one line with its dates */
    var groups = {}, order = [];
    (A.ev || []).forEach(function (r) {
      if (!r.o || r.y > to || (r.z || r.y) < from) return;
      var g = r.s ? "s:" + r.s : r.id;
      if (!groups[g]) { groups[g] = []; order.push(g); }
      groups[g].push(r);
    });
    order.forEach(function (g) {
      var rs = groups[g], r = rs[0], t = r.t[L];
      var tail = r.k === "w" ? S.attended + ", " + S.written : r.k === "r" ? S.attended + ", " + S.recorded : r.k === "b" ? S.visitors : S.attended;
      var head = rs.length > 1 ? t[1] + " — " + joinList(rs.map(function (x) { return x.t[L][0]; }), L) : t[0] + " — " + t[1];
      lines.push("• " + head + ": " + tail);
    });
    if (!lines.length) lines.push(S.recent_none);
    var held = (A.mt || []).filter(function (m) { return m.y >= from && m.y <= to; });
    if (held.length) lines.push("• " + fmt(S.met, { dates: joinList(held.map(function (m) { return m.t[L][0]; }), L) }));
    out.recent = lines.join("\n");

    /* Next: until the next assembly; a monthly series once ("every month") */
    var asm = null, seen = {};
    (A.ev || []).forEach(function (r) { if (!asm && r.a && r.y > to) asm = r; });
    var until = asm && asm.y <= ymdAdd(to, ASSEMBLY_DAYS) ? asm.z || asm.y : ymdAdd(to, NEXT_DAYS);
    lines = [];
    (A.ev || []).forEach(function (r) {
      if (!(r.o || r.a) || r.y <= to || r.y > until) return;
      if (r.s) { if (seen[r.s]) return; seen[r.s] = true; }
      var bits = [r.t[L][0]];
      if (r.s) bits.push(S.monthly);
      if (r.tb) bits.push(S.tbc);
      lines.push("• " + bits.join(" · ") + " — " + r.t[L][1]);
    });
    if (!lines.length) lines.push(S.next_none);
    var coming = (A.mt || []).filter(function (m) { return m.y > to && m.y <= until; });
    if (coming.length) lines.push("• " + fmt(S.meets, { dates: joinList(coming.map(function (m) { return m.t[L][0]; }), L) }));
    out.next = lines.join("\n");

    /* Writers of the period's issues */
    var ws = (A.wr || []).filter(function (w) { return w.y >= from && w.y <= to; });
    lines = ws.length ? [S.w_intro].concat(ws.map(function (w) { return "• " + w.t[L]; })) : [S.w_none];
    lines.push(S.w_all);
    out.writers = lines.join("\n");

    out.invite = S.invite;
    var nm = null;
    (A.mt || []).forEach(function (m) { if (!nm && m.y > to) nm = m; });
    out.meeting = [nm ? nm.t[L][1] : S.meet_none, S.meet_more].filter(Boolean).join("\n");
    out.notes = "";
    return AREA_IDS.map(function (id) { return { id: id, title: M.titles[id], text: out[id] }; });
  }
  // The model the editor works on for the dates r ({ from, to }).
  function areaModelFor(A, r) {
    var langs = {};
    ["en", "es"].forEach(function (L) {
      var M = A.langs[L];
      langs[L] = { month: rangeLabel(r.from, r.to, L), sections: areaSections(A, L, r.from, r.to), tokens: M.tokens, roles: {}, kinds: M.kinds,
        custom: M.custom, paste: M.paste, meet: { pick: "", none: "", more: "" } };
    });
    return { v: 1, area: true, month: "area", from: r.from, to: r.to, langs: langs, meetings: { options: [] } };
  }
  // An earlier report's model: its dates', with the site's text as it was when it was filed (r.site)
  function doneModel(A, r) {
    var M = areaModelFor(A, r);
    ["en", "es"].forEach(function (L) {
      var t = (r.site && r.site[L]) || {};
      M.langs[L].sections.forEach(function (s) { if (typeof t[s.id] === "string") s.text = t[s.id]; });
    });
    return M;
  }
  // One language's part as it goes out: the draft's order, the sections left out, the edited texts and titles over
  // the model's (what the editor's textOf / titleOf do).
  function partSections(model, lang, d) {
    var M = model.langs[lang], by = {};
    M.sections.forEach(function (s) { by[s.id] = s; });
    return d.order.filter(function (id) { return !d.off[id]; }).map(function (id) {
      var c = null;
      d.custom.forEach(function (x) { if (x.id === id) c = x; });
      if (c) return { id: id, title: clean(c.title) || M.custom, text: c.text };
      var s = by[id] || { title: id, text: "" };
      return { id: id, title: has(d.titles, id) && clean(d.titles[id]) ? d.titles[id] : s.title, text: has(d.text, id) ? d.text[id] : s.text };
    });
  }

  /* ---------------- the Alpine component ---------------- */
  document.addEventListener("alpine:init", function () {
    window.Alpine.data("rpEditor", function (pageLang) {
      return {
        L: pageLang || "en",
        rl: pageLang || "en",       // the report's language (its own EN / ES switch; the Area report: the part edited)
        D: null,                    // the model (both languages) — the district report's (D0) or the Area report's
        D0: null,                   // the district report's model
        A: null,                    // the Area report's pieces (<script id="rp-area">; null: no "For" switch)
        mode: "district",           // For: "district" (a district meeting) · "area" (an assembly or Area committee meeting)
        range: { from: "", to: "", toFollowsToday: false }, // the Area report's dates (the working report's)
        work: { en: null, es: null }, // … its parts (d / d2 are these while For: Area)
        done: [],                   // … the earlier reports (the archive), newest first
        shown: "",                  // the preview while an earlier report is printed
        rangeIn: { from: "", to: "" }, // the dates in its fields: the period's, or the ones typed that aren't one yet
        rangeErr: "",               // why those can't be a period: "order" (start after end) · "reach" (rangeProblem)
        ui: {},
        prof: { district: "", name: "", role: "", group: "", ameet: "" },
        d: null,                    // this month + language's changes
        d2: null,                   // the Area report: the changes to the part not being edited (its output)
        open: {},                   // sections whose editor is open
        active: "",                 // the section being edited (highlighted in the preview)
        saveState: "idle",          // idle · saved · failed
        savedAt: "",
        msg: "",
        waLong: false,
        full: false,                // phones: the preview unfolded
        prev: null,                 // "Start from last month's draft": { month: "YYYY-MM", label } (findPrev; Area: { r, label })
        canShare: !!navigator.share,
        sevenDays: "",              // the Area report's line on Safari's 7-day rule: sevenKind
        _saveT: 0, _msgT: 0, _pending: false, _persistAsked: false,

        init: function () {
          try {
            this.D = JSON.parse(document.getElementById("rp-data").textContent);
            this.ui = JSON.parse(document.getElementById("rp-ui").textContent) || {};
          } catch (e) { return; }
          this.D0 = this.D;
          var standalone = false;
          try { standalone = navigator.standalone === true || !!(window.matchMedia && window.matchMedia("(display-mode: standalone)").matches); } catch (e) { /* old */ }
          this.sevenDays = sevenKind(navigator.userAgent, navigator.maxTouchPoints, standalone);
          try {
            var ar = document.getElementById("rp-area");
            this.A = ar ? JSON.parse(ar.textContent) : null;
            if (!this.A || !this.A.langs || !this.A.langs.en || !this.A.langs.es) this.A = null;
          } catch (e) { this.A = null; }
          this.swapTexts();
          var p = load(PREFIX + "profile");
          if (p && typeof p === "object") {
            for (var k in this.prof) if (has(p, k)) this.prof[k] = str(p[k], 60);
            if (typeof this.D.langs.en.roles[this.prof.role] !== "string") this.prof.role = "";
            if (this.prof.ameet !== "assembly" && this.prof.ameet !== "acm") this.prof.ameet = "";
          }
          var lg = load(PREFIX + "lang");
          if (lg === "en" || lg === "es") this.rl = lg;
          this.prune();
          if (this.A) {
            this.loadWork();
            this.done = this.loadDone();
            if (load(PREFIX + "mode") === "area") { this.mode = "area"; this.D = areaModelFor(this.A, this.range); }
          }
          this.reload();
          var self = this;
          // Leaving the page within the save delay still keeps the last keystrokes.
          var flush = function () { if (self._pending) self.saveNow(); };
          window.addEventListener("pagehide", flush);
          document.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") flush(); });
          // An edit in another tab (same device) shows up here too.
          window.addEventListener("storage", function (e) {
            if (self.A && e.key === WORK) {
              self.loadWork();
              if (self.D.area) { self.D = areaModelFor(self.A, self.range); self.reload(); }
            } else if (self.A && e.key === DONE) { self.done = self.loadDone(); self.prev = self.findPrev(self.rl); }
            else if (!self.D.area && e.key === self.key(self.rl)) { self.d = self.loadDraft(self.rl); self.prev = self.findPrev(self.rl); }
          });
        },

        /* ---- For: district meeting | Area ---- */
        other: function () { return this.rl === "en" ? "es" : "en"; },
        // A new model, mode or part: its drafts (the Area report: the working report's parts, in memory), its offer,
        // nothing open.
        reload: function () {
          if (this.D.area) { this.d = this.work[this.rl]; this.d2 = this.work[this.other()]; }
          else { this.d = this.loadDraft(this.rl); this.d2 = null; }
          this.prev = this.findPrev(this.rl);
          this.open = {};
          this.active = "";
          this.waLong = false;
          this.rangeIn = { from: this.range.from, to: this.range.to };
          this.rangeErr = "";
        },
        setMode: function (m) {
          if (m === this.mode || (m === "area" && !this.A)) return;
          if (this._pending) this.saveNow();
          this.mode = m === "area" ? "area" : "district";
          store(PREFIX + "mode", this.mode);
          this.D = this.mode === "area" ? areaModelFor(this.A, this.range) : this.D0;
          this.reload();
          GV.announce && GV.announce(fmt(this.ui.ar_mode_done, { mode: this.ui[this.mode === "area" ? "ar_for_area" : "ar_for_district"] }));
        },
        /* The working report on this device (the top of the Area report's code): its dates — To today while it follows
           today; none kept, or dates the page can't use: the dates offered first — and its parts, whatever the dates. */
        loadWork: function () {
          var A = this.A, x = load(WORK), today = areaToday(A);
          x = x && typeof x === "object" ? x : {};
          var r = rangeProblem(A, x) ? areaRange(A) : { from: x.from, to: x.to, toFollowsToday: x.toFollowsToday === true };
          if (r.toFollowsToday && today >= r.from) r.to = today;
          var M = areaModelFor(A, r), P = x.parts && typeof x.parts === "object" ? x.parts : {};
          this.range = r;
          this.work = { en: this.parseDraft("en", P.en, M), es: this.parseDraft("es", P.es, M) };
        },
        // The earlier reports (the archive), newest first
        loadDone: function () {
          var x = load(DONE);
          return (Array.isArray(x) ? x : []).filter(function (r) { return r && typeof r === "object" && isYmd(r.from) && isYmd(r.to); }).slice(0, DONE_MAX);
        },
        saveWork: function () {
          var r = this.range;
          return store(WORK, { from: r.from, to: r.to, toFollowsToday: !!r.toFollowsToday, parts: this.work });
        },
        /* A date typed in its field ("from" | "to"). Two dates that can't be a period stay in the fields as typed, with
           the reason under them — the other date may come next. Once they are one, only the dates change (a To picked
           by hand stops following today); the parts stay as they are. */
        setRange: function (which, v) {
          var r = { from: this.rangeIn.from, to: this.rangeIn.to }, old = this.range;
          r[which] = v;
          this.rangeIn = r;
          this.rangeErr = rangeProblem(this.A, r);
          if (this.rangeErr) { GV.announce && GV.announce(this.rangeErrText()); return; }
          this.range = { from: r.from, to: r.to, toFollowsToday: which === "from" && !!old.toFollowsToday && r.to === old.to };
          this.D = areaModelFor(this.A, this.range);
          this.saveNow();
        },
        rangeErrText: function () {
          if (this.rangeErr === "reach") return fmt(this.ui.ar_range_out, { from: longDay(this.A.min, this.L), to: longDay(this.A.max, this.L) });
          return this.rangeErr ? this.ui.ar_range_bad : "";
        },
        // To follows today (the line under the dates)
        follows: function () { return this.mode === "area" && !!this.range.toFollowsToday; },
        // "Next report: from {date} to today" — once a To picked by hand is before today
        newPeriodText: function () {
          var r = this.range, today = this.mode === "area" ? areaToday(this.A) : "";
          return today && !r.toFollowsToday && r.to < today ? fmt(this.ui.ar_new_period, { date: longDay(ymdAdd(r.to, 1), this.L) }) : "";
        },
        // "Next report", confirmed: the working report into the archive (as it is, with the site's text for its
        // dates, the name and the meeting), then a fresh one from the day after it, to today. Nothing is filed or
        // cleared when the archive can't be saved.
        newPeriod: function () {
          var r = this.range, ui = this.ui, L = this.L, self = this, last = this.done[DONE_MAX - 1];
          if (!this.newPeriodText()) return;
          var q = fmt(ui.ar_next_confirm, { dates: rangeLabel(r.from, r.to, L), date: longDay(ymdAdd(r.to, 1), L) });
          if (last) q += " " + fmt(ui.ar_next_full, { dates: rangeLabel(last.from, last.to, L) });
          if (!window.confirm(q)) return;
          if (this._pending) this.saveNow();
          var site = {};
          ["en", "es"].forEach(function (P) { site[P] = {}; self.D.langs[P].sections.forEach(function (s) { site[P][s.id] = s.text; }); });
          var entry = JSON.parse(JSON.stringify({ from: r.from, to: r.to, parts: this.work, site: site, prof: { name: this.prof.name, ameet: this.prof.ameet } }));
          var done = [entry].concat(this.done).slice(0, DONE_MAX);
          if (!store(DONE, done)) { this.saveState = "failed"; this.flash(ui.ar_next_failed); return; }
          this.askPersist();
          this.done = done;
          this.range = { from: ymdAdd(r.to, 1), to: areaToday(this.A), toFollowsToday: true };
          this.D = areaModelFor(this.A, this.range);
          this.work = { en: this.parseDraft("en", null), es: this.parseDraft("es", null) };
          this.reload();
          this.saveNow();
          if (this.saveState === "failed") store(WORK, null);   // (never the filed report twice)
          this.flash(fmt(ui.ar_next_done, { dates: rangeLabel(r.from, r.to, L) }));
          // (the button is gone: the keyboard goes on to the new report's first date)
          this.$nextTick(function () { var f = document.getElementById("rp-from"); if (f) f.focus(); });
        },
        // "Earlier reports (3)"; one by its dates
        doneTitle: function () { return fmt(this.ui.ar_done_title, { n: this.done.length }); },
        doneLabel: function (r) { return rangeLabel(r.from, r.to, this.L); },
        doneDownload: function (i) {
          var r = this.done[i], name = r && this.fileBase(r) + ".docx";
          if (!r) return;
          saveBlob(docx(this.docBlocks(r), "en", this.titleLine(r)), name);
          this.flash(fmt(this.ui.downloaded, { file: name }));
        },
        donePrint: function (i) {
          var r = this.done[i];
          if (!r) return;
          this.shown = previewHtml(this.docBlocks(r), "");
          this.print(this.fileBase(r));
        },
        doneDelete: function (i) {
          var r = this.done[i], label = r && this.doneLabel(r);
          if (!r || !window.confirm(fmt(this.ui.ar_done_del_confirm, { dates: label }))) return;
          var done = this.done.filter(function (x, j) { return j !== i; });
          if (!store(DONE, done)) { this.saveState = "failed"; this.flash(this.ui.not_saved); return; }
          this.done = done;
          this.prev = this.findPrev(this.rl);
          this.flash(fmt(this.ui.ar_done_deleted, { dates: label }));
          // (its buttons are gone: the keyboard goes back to the list's title — or, the list gone, the first date)
          // (by the count, not the title's visibility: on this tick the list's x-show has not hidden it yet)
          var left = done.length;
          this.$nextTick(function () { var f = left ? document.querySelector(".rp-done-sum") : null; if (!f) f = document.getElementById("rp-from"); if (f) f.focus(); });
        },
        // Before the first day the site keeps all our past events from (areaModel `hz`): say so.
        olderText: function () {
          return this.mode === "area" && this.A && this.A.hz && this.range.from && this.range.from < this.A.hz ? fmt(this.ui.ar_older, { date: longDay(this.A.hz, this.L) }) : "";
        },
        fileHint: function () { return this.mode === "area" ? fmt(this.ui.ar_file_hint, { file: this.fileBase() + ".docx" }) : ""; },

        /* A section whose text changes at set moments (eleventy/filters/report.js: the shop section when a Book of
           the Month offer ends or starts and from the day an announced price change takes effect — section.steps =
           [{ at: ISO instant, text }, …] in time order; an older page's single section.after = { at, text } counts
           as one step): by this device's clock, the text of the last moment passed — a page built, or saved for
           offline use, days before is right on the day, and never quotes an offer that has ended. A section the
           visitor edited keeps their own words (only changes are stored). */
        swapTexts: function () {
          var now = Date.now(), D = this.D;
          Object.keys(D.langs || {}).forEach(function (l) {
            (D.langs[l].sections || []).forEach(function (s) {
              var steps = Array.isArray(s.steps) ? s.steps : s.after ? [s.after] : [];
              steps.forEach(function (a) {
                if (a && typeof a.text === "string" && /^\d{4}-\d{2}-\d{2}T/.test(String(a.at || "")) && Date.parse(a.at) <= now) s.text = a.text;
              });
            });
          });
        },

        /* ---- storage ---- */
        key: function (lang) { return PREFIX + this.D.month + ":" + lang; },
        ids: function () { return this.D.langs[this.rl].sections.map(function (s) { return s.id; }); },
        blank: function () { return { order: this.ids(), off: {}, text: {}, titles: {}, custom: [], meet: [] }; },
        loadDraft: function (lang) { return this.parseDraft(lang, load(this.key(lang))); },
        // A stored draft (x) checked against this month's sections (or model M's); nothing usable → a blank draft.
        parseDraft: function (lang, x, M) {
          M = M || this.D;
          var b = { order: M.langs[lang].sections.map(function (s) { return s.id; }), off: {}, text: {}, titles: {}, custom: [], meet: [] };
          if (!x || typeof x !== "object") return b;
          var defaults = b.order.slice();
          (Array.isArray(x.custom) ? x.custom : []).forEach(function (c) {
            if (c && /^custom-\d{1,4}$/.test(c.id) && !b.custom.some(function (o) { return o.id === c.id; })) b.custom.push({ id: c.id, title: str(c.title, 120), text: str(c.text) });
          });
          var valid = defaults.concat(b.custom.map(function (c) { return c.id; }));
          var order = (Array.isArray(x.order) ? x.order : []).filter(function (id, i, a) { return valid.indexOf(id) !== -1 && a.indexOf(id) === i; });
          valid.forEach(function (id) { if (order.indexOf(id) === -1) order.push(id); });  // a section new since the draft
          order.splice(order.indexOf("header"), 1);
          b.order = ["header"].concat(order);
          ["off", "text", "titles"].forEach(function (f) {
            var src = x[f] && typeof x[f] === "object" ? x[f] : {};
            Object.keys(src).forEach(function (id) {
              // a section switched off stays off — one of the visitor's own too, or it would be back in
              // the report copied, sent and printed after a reload; edited texts and titles are the
              // built-in sections' (a custom section keeps its own in `custom`)
              if (f === "off") { if (src[id] === true && valid.indexOf(id) !== -1) b.off[id] = true; return; }
              if (defaults.indexOf(id) !== -1 && typeof src[id] === "string") b[f][id] = str(src[id], f === "titles" ? 120 : 20000);
            });
          });
          var opts = M.meetings.options.map(function (o) { return o.id; });
          b.meet = (Array.isArray(x.meet) ? x.meet : []).filter(function (id) { return opts.indexOf(id) !== -1; });
          return b;
        },
        /* "Start from last month's draft": a new month starts from the latest data; when this month has no draft
           yet (in the report language) and an earlier month has one on this device (the newest of the last three:
           older ones are pruned), the editor offers it as the starting point. What carries over is the visitor's
           own: their sections (custom), the order, the sections left out, the titles they changed, the counties
           picked, and the texts of the sections that are their own words ("asks", "notes"); every section made
           from the site's data starts from this month's. The offer goes once this month's draft exists. */
        findPrev: function (lang) {
          if (this.D.area) return this.areaPrev(lang);
          if (this.hasOwnWork(load(this.key(lang)), lang)) return null;
          var months = [], m, best = "";
          try {
            for (var i = 0; i < localStorage.length; i++) {
              var k = localStorage.key(i);
              m = k && /^gv-report:(\d{4}-\d{2}):(en|es)$/.exec(k);
              if (m && m[2] === lang && m[1] < this.D.month) months.push(m[1]);
            }
          } catch (e) { return null; }
          // the newest month whose draft has something to carry over
          months.sort().reverse();
          for (var j = 0; j < months.length && !best; j++) if (this.hasOwnWork(load(PREFIX + months[j] + ":" + lang), lang, true)) best = months[j];
          if (!best) return null;
          var label = best;
          try { label = new Intl.DateTimeFormat(this.L === "es" ? "es-US" : "en-US", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(best + "-15T12:00:00Z")); } catch (e) { /* the key */ }
          return { month: best, label: label };
        },
        // The Area report: the newest earlier report, while this part of the working report has nothing of the chair's
        // own and that report has something to carry over (either part). { r, label }
        areaPrev: function (lang) {
          var r = this.done[0], self = this;
          if (!r || this.hasOwnWork(this.work[lang], lang)) return null;
          return ["en", "es"].some(function (L) { return self.hasOwnWork((r.parts || {})[L], L, true); }) ? { r: r, label: rangeLabel(r.from, r.to, this.L) } : null;
        },
        // Anything of the visitor's own in a stored draft: a section of their own, a county picked, a section left out,
        // a title or text changed, or the sections in another order (a draft saved with none of it — "Your details"
        // typed in, a change undone — is not a draft to offer, nor one that hides the offer). carried: only what
        // "Start from last month's draft" carries over counts (of the texts, the visitor's own sections' only).
        hasOwnWork: function (x, lang, carried) {
          if (!x || typeof x !== "object") return false;
          var b = this.parseDraft(lang, x), ids = this.D.langs[lang].sections.map(function (s) { return s.id; });
          var own = this.D.area ? OWN_TEXT_AREA : OWN_TEXT;
          var texts = Object.keys(b.text).filter(function (id) { return !carried || own.indexOf(id) !== -1; });
          return b.custom.length > 0 || b.meet.length > 0 || Object.keys(b.off).length > 0 || Object.keys(b.titles).length > 0 ||
            texts.length > 0 || b.order.join() !== ids.join();
        },
        // "Start from last month's draft?" — or, when the newest draft is older (two or three months back), its month:
        // "Start from your August 2026 draft?"
        prevTitle: function () {
          if (!this.prev) return "";
          if (this.D.area) return fmt(this.ui.ar_prev_title, { month: this.prev.label });
          var y = Number(this.D.month.slice(0, 4)), mo = Number(this.D.month.slice(5, 7)) - 1;
          var before = mo ? y + "-" + (mo < 10 ? "0" : "") + mo : (y - 1) + "-12";
          return this.prev.month === before || !this.ui.prev_title_month ? (this.ui.prev_title || "") : fmt(this.ui.prev_title_month, { month: this.prev.label });
        },
        prevText: function () { return this.prev ? fmt(this.ui[this.D.area ? "ar_prev_text" : "prev_text"], { month: this.prev.label }) : ""; },
        prevBtn: function () { return this.prev ? fmt(this.ui[this.D.area ? "ar_prev_btn" : "prev_btn"], { month: this.prev.label }) : ""; },
        // (the Area report: both parts start from the earlier report's — the other part only while it has nothing of
        // its own)
        startFromPrev: function () {
          var p = this.prev, self = this, area = !!this.D.area, started = false;
          this.prev = null;
          if (!p) return;
          (area ? ["en", "es"] : [this.rl]).forEach(function (L) {
            var x = area ? (p.r.parts || {})[L] : load(PREFIX + p.month + ":" + L);
            if (!x || typeof x !== "object" || (L !== self.rl && self.hasOwnWork(area ? self.work[L] : load(self.key(L)), L))) return;
            var own = {};
            (area ? OWN_TEXT_AREA : OWN_TEXT).forEach(function (id) { if (x.text && typeof x.text[id] === "string") own[id] = x.text[id]; });
            var nd = self.parseDraft(L, { order: x.order, off: x.off, titles: x.titles, custom: x.custom, meet: x.meet, text: own });
            if (area) self.work[L] = nd;
            if (L === self.rl) { self.d = nd; started = true; } else self.d2 = nd;
          });
          if (!started) return;
          this.open = {};
          this.active = "";
          this.saveNow();
          this.flash(fmt(this.ui[area ? "ar_prev_done" : "prev_done"], { month: p.label }));
          // the keyboard goes on to the sections (the offer is gone)
          var self = this;
          this.$nextTick(function () { var b = self.$root.querySelector("[data-rp-edit]"); if (b) b.focus(); });
        },
        // Drafts older than three months are removed (the district report's; the Area report keeps its own: newPeriod).
        prune: function () {
          try {
            var cut = this.D0.month.split("-").map(Number);
            var min = cut[0] * 12 + cut[1] - 3;
            for (var i = localStorage.length - 1; i >= 0; i--) {
              var k = localStorage.key(i), m = k && /^gv-report:(\d{4})-(\d{2}):/.exec(k);
              if (m && Number(m[1]) * 12 + Number(m[2]) < min) localStorage.removeItem(k);
            }
          } catch (e) { /* no storage */ }
        },
        touch: function () {
          var self = this;
          this.prev = null;           // this month's own draft from now on
          this._pending = true;
          clearTimeout(this._saveT);
          this._saveT = setTimeout(function () { self.saveNow(); }, 350);
        },
        saveNow: function () {
          clearTimeout(this._saveT);
          this._pending = false;
          var ok = this.D.area ? this.saveWork() : store(this.key(this.rl), this.d);   // (the Area report: all of it)
          this.saveState = ok ? "saved" : "failed";
          if (ok && this.D.area) this.askPersist();
          if (ok) {
            try { this.savedAt = new Intl.DateTimeFormat(this.L === "es" ? "es-US" : "en-US", { hour: "numeric", minute: "2-digit" }).format(new Date()); } catch (e) { this.savedAt = ""; }
            if (GV.esMeridiem) this.savedAt = GV.esMeridiem(this.savedAt);
          }
        },
        // "Keep this site's data until I delete it": asked once a page, once the Area report is saved or filed (as the
        // Tracker and the story recorder ask). The browser decides — Firefox asks the visitor; Chrome and Edge answer by
        // how the site is used —, and the page works the same either way.
        askPersist: function () {
          if (this._persistAsked) return;
          this._persistAsked = true;
          try { navigator.storage.persist().then(function () {}, function () {}); } catch (e) { /* no Storage API */ }
        },
        setProf: function (k, v) {
          this.prof[k] = str(v, 60);
          this.saveState = store(PREFIX + "profile", this.prof) ? "saved" : "failed";
          if (this.saveState === "saved") this.saveNow();
        },
        say: function (k, title) { return fmt(this.ui[k], { title: title }); },
        savedText: function () { return this.saveState === "failed" ? this.ui.not_saved : this.saveState === "saved" ? this.ui.saved : this.ui.saved_idle; },

        /* ---- the sections ---- */
        lm: function () { return this.D.langs[this.rl]; },
        def: function (id) { var s = this.lm().sections; for (var i = 0; i < s.length; i++) if (s[i].id === id) return s[i]; return null; },
        cust: function (id) { for (var i = 0; i < this.d.custom.length; i++) if (this.d.custom[i].id === id) return this.d.custom[i]; return null; },
        isCustom: function (id) { return /^custom-/.test(id); },
        defaultText: function (id) {
          if (id === "meetings" && this.d.meet.length) return this.meetText();
          var s = this.def(id);
          return s ? s.text : "";
        },
        textOf: function (id) {
          if (this.isCustom(id)) { var c = this.cust(id); return c ? c.text : ""; }
          return has(this.d.text, id) ? this.d.text[id] : this.defaultText(id);
        },
        titleOf: function (id) {
          if (this.isCustom(id)) { var c = this.cust(id); return (c && clean(c.title)) || this.lm().custom; }
          if (has(this.d.titles, id) && clean(this.d.titles[id])) return this.d.titles[id];
          var s = this.def(id);
          return s ? s.title : id;
        },
        titleValue: function (id) {
          if (this.isCustom(id)) { var c = this.cust(id); return c ? c.title : ""; }
          return has(this.d.titles, id) ? this.d.titles[id] : this.titleOf(id);
        },
        setText: function (id, v) {
          v = str(v);
          if (this.isCustom(id)) { var c = this.cust(id); if (c) c.text = v; }
          else if (v === this.defaultText(id)) delete this.d.text[id];
          else this.d.text[id] = v;
          this.touch();
        },
        setTitle: function (id, v) {
          v = str(v, 120);
          if (this.isCustom(id)) { var c = this.cust(id); if (c) c.title = v; }
          else if (v === (this.def(id) || {}).title) delete this.d.titles[id];
          else this.d.titles[id] = v;
          this.touch();
        },
        isOn: function (id) { return !this.d.off[id]; },
        edited: function (id) { return !this.isCustom(id) && (has(this.d.text, id) || has(this.d.titles, id)); },
        // The list the editor shows: the report's order, each with its number in the report.
        list: function () {
          var self = this, n = 0, total = this.d.order.length;
          return this.d.order.map(function (id, i) {
            var on = self.isOn(id), empty = !String(self.textOf(id)).trim();
            var num = on && !empty && id !== "header" ? ++n : 0;
            return { id: id, i: i, title: self.titleOf(id), on: on, empty: empty, num: num, header: id === "header", custom: self.isCustom(id), edited: self.edited(id), first: i <= 1, last: i === total - 1 };
          });
        },
        toggle: function (id) {
          if (this.d.off[id]) delete this.d.off[id]; else this.d.off[id] = true;
          this.touch();
        },
        canMove: function (id, dir) {
          var i = this.d.order.indexOf(id), j = i + dir;
          return i > 0 && j > 0 && j < this.d.order.length;
        },
        move: function (id, dir) {
          if (!this.canMove(id, dir)) return;
          var o = this.d.order, i = o.indexOf(id);
          o.splice(i, 1);
          o.splice(i + dir, 0, id);
          this.touch();
          GV.announce && GV.announce(fmt(this.ui.moved, { title: this.titleOf(id), n: i + dir, total: o.length - 1 }));
          // Keep the keyboard on the moved section: the same arrow, or the other one at an end.
          var self = this;
          this.$nextTick(function () {
            var want = dir < 0 ? "up" : "down", other = dir < 0 ? "down" : "up";
            var b = self.$root.querySelector('[data-rp-move="' + (self.canMove(id, dir) ? want : other) + '"][data-rp-id="' + id + '"]');
            if (b) b.focus();
          });
        },
        toggleOpen: function (id) {
          var self = this;
          this.open[id] = !this.open[id];
          if (this.open[id]) this.focusSec(id);
          this.$nextTick(function () { self.growAll(); });
        },
        closeEditor: function (id) {
          this.open[id] = false;
          var b = this.$root.querySelector('[data-rp-edit="' + id + '"]');
          if (b) b.focus();
        },
        addCustom: function () {
          var max = 0;
          this.d.custom.forEach(function (c) { max = Math.max(max, Number(c.id.split("-")[1]) || 0); });
          var id = "custom-" + (max + 1);
          this.d.custom.push({ id: id, title: "", text: "" });
          this.d.order.push(id);
          this.open[id] = true;
          this.touch();
          GV.announce && GV.announce(this.ui.added);
          var self = this;
          this.$nextTick(function () {
            var f = document.getElementById("rp-title-" + id);
            if (f) f.focus();
            self.focusSec(id);
          });
        },
        removeCustom: function (id) {
          this.d.custom = this.d.custom.filter(function (c) { return c.id !== id; });
          this.d.order = this.d.order.filter(function (x) { return x !== id; });
          delete this.d.off[id];   // a section added later may get the same id: it starts switched on
          delete this.open[id];
          this.touch();
          GV.announce && GV.announce(this.ui.removed);
          var b = this.$refs.add;
          this.$nextTick(function () { if (b) b.focus(); });
        },
        resetSection: function (id) {
          delete this.d.text[id];
          delete this.d.titles[id];
          this.touch();
          GV.announce && GV.announce(fmt(this.ui.reset_done, { title: this.titleOf(id) }));
          this.$nextTick(function () { var t = document.getElementById("rp-text-" + id); if (t) t.focus(); });
        },
        // (the Area report: this part only — the dates and the other part stay as they are)
        resetAll: function () {
          var area = !!this.D.area, ui = this.ui, parts = area && { part: ui["ar_part_" + this.rl], other: ui["ar_part_" + this.other()] };
          if (!window.confirm(area ? fmt(ui.ar_reset_confirm, parts) : ui.reset_all_confirm)) return;
          clearTimeout(this._saveT);
          this._pending = false;
          this.d = this.blank();
          this.open = {};
          this.active = "";
          if (area) { this.work[this.rl] = this.d; this.saveNow(); } else store(this.key(this.rl), null);
          this.prev = this.findPrev(this.rl);
          if (!area) this.saveState = "idle";
          this.flash(area ? fmt(ui.ar_reset_done, parts) : ui.reset_all_done);
        },
        setLang: function (l) {
          if (l === this.rl || !this.D.langs[l]) return;
          if (this._pending) this.saveNow();   // the old language's last changes
          this.rl = l;
          store(PREFIX + "lang", l);
          this.reload();
          // (the Area report: the switch picks the part being edited — the report holds both)
          GV.announce && GV.announce(fmt(this.ui[this.D.area ? "ar_part_done" : "lang_done"], { lang: this.ui["lang_" + l] }));
        },

        /* ---- Grapevine meetings: the county picker ---- */
        meetOpts: function (group) { return this.D.meetings.options.filter(function (o) { return o.group === group; }); },
        picked: function (id) { return this.d.meet.indexOf(id) !== -1; },
        togglePick: function (id) {
          var i = this.d.meet.indexOf(id);
          if (i === -1) this.d.meet.push(id); else this.d.meet.splice(i, 1);
          delete this.d.text.meetings;  // picking writes the section again
          this.touch();
        },
        clearPicks: function () { this.d.meet = []; delete this.d.text.meetings; this.touch(); },
        meetText: function () {
          var rl = this.rl, M = this.lm().meet, picks = this.d.meet;
          var chosen = this.D.meetings.options.filter(function (o) { return picks.indexOf(o.id) !== -1; });
          var lines = [];
          chosen.forEach(function (o) { lines = lines.concat(o.lines[rl] || []); });
          var out = [fmt(M.pick, { where: chosen.map(function (o) { return o.name[rl]; }).join(", ") })];
          out = out.concat(lines.length ? lines : [M.none]);
          out.push(M.more);
          return out.join("\n");
        },

        /* ---- the output ---- */
        // The blanks the details fill in, in a language's words (the Area report: the name and the Area meeting).
        // (M, p: another model and details — an earlier Area report's)
        filled: function (text, lang, M, p) {
          M = M || this.D;
          p = p || this.prof;
          var lm = M.langs[lang || this.rl], tk = lm.tokens;
          var pairs = M.area
            ? [[tk.name, clean(p.name)], [tk.meeting, lm.kinds && typeof lm.kinds[p.ameet] === "string" ? lm.kinds[p.ameet] : ""]]
            : [[tk.district, clean(p.district)], [tk.name, clean(p.name)], [tk.group, clean(p.group)], [tk.role, typeof lm.roles[p.role] === "string" ? lm.roles[p.role] : ""]];
          pairs.forEach(function (m) { if (m[0] && m[1]) text = text.split(m[0]).join(m[1]); });
          return text;
        },
        outSections: function () {
          var self = this;
          return this.d.order.filter(function (id) { return self.isOn(id); })
            .map(function (id) { return { id: id, title: self.filled(self.titleOf(id)), text: self.filled(self.textOf(id)) }; });
        },
        // The Area report's two parts as they go out, English first: [{ lang, secs }] — the working report's, or (r) an
        // earlier one's (its dates, the site's text then, its parts, its name and meeting).
        parts: function (r) {
          var self = this, M = r ? doneModel(this.A, r) : this.D, p = r ? r.prof || {} : this.prof;
          return ["en", "es"].map(function (L) {
            var d = r ? self.parseDraft(L, (r.parts || {})[L], M) : self.work[L];
            return { lang: L, secs: partSections(M, L, d).map(function (s) { return { id: s.id, title: self.filled(s.title, L, M, p), text: self.filled(s.text, L, M, p) }; }) };
          });
        },
        plain: function () {
          if (!this.D.area) return compose(this.outSections());
          var p = this.parts();
          return compose(p[0].secs) + "\n" + AREA_SPLIT + "\n\n" + compose(p[1].secs);
        },
        // The report as blocks (the preview, the formatted copy, the Word file); the Area report: both parts, the line
        // between them, the part not being edited with its own section ids ("es:recent") — or (r) an earlier report.
        docBlocks: function (r) {
          if (!r && !this.D.area) return blocks(this.outSections());
          var self = this, out = [];
          this.parts(r).forEach(function (p, i) {
            if (i) out.push({ t: "split" });
            out = out.concat(blocks(p.secs, !r && p.lang === self.rl ? "" : p.lang + ":", p.lang));
          });
          return out;
        },
        docLang: function () { return this.D.area ? "en" : this.rl; },
        titleLine: function (r) {
          if (r || this.D.area) {   // the English part's title (r: an earlier report's)
            var M = r ? doneModel(this.A, r) : this.D, hd = this.parts(r)[0].secs.filter(function (s) { return s.id === "header"; })[0];
            var t = hd ? clean(String(hd.text).split("\n")[0]) : "";
            return t || clean(this.filled(M.langs.en.sections[0].text.split("\n")[0], "en", M, r ? r.prof || {} : null));
          }
          var h = this.isOn("header") ? clean(this.filled(this.textOf("header")).split("\n")[0]) : "";
          return h || clean(this.filled(this.def("header").text.split("\n")[0]));
        },
        preview: function () { return this.shown || (this.d ? previewHtml(this.docBlocks(), this.active) : ""); },
        blanks: function () { var m = this.plain().match(/\[[^\]\n]{1,80}\]/g); return m ? m.length : 0; },
        blanksText: function () { var n = this.blanks(); return n === 0 ? this.ui.blanks_none : n === 1 ? this.ui.blanks_one : fmt(this.ui.blanks, { n: n }); },
        // (the Area report: one part is read aloud — the one being edited)
        readText: function () {
          var words = (this.D.area ? compose(this.outSections()) : this.plain()).replace(/https?:\/\/\S+/g, "").split(/\s+/).filter(Boolean).length;
          var n = Math.max(1, Math.round(words / WPM));
          return n === 1 ? this.ui.read_time_one : fmt(this.ui.read_time, { n: n });
        },
        // The Area report: a dated name, as the committee's reports are named on its Drive ("2026-11-14 Grapevine La
        // Vina Area Assembly Report") — the meeting's day (the period's end) first, so the folder lists them in order.
        // (r: an earlier report's)
        fileBase: function (r) {
          if (r || this.D.area) return (r || this.D).to + " Grapevine La Vina " + ({ assembly: "Area Assembly", acm: "Area Committee Meeting" }[(r ? r.prof || {} : this.prof).ameet] || "Area") + " Report";
          var d = slug(this.prof.district);
          return "grapevine-la-vina-report-" + (d ? "district-" + d + "-" : "") + this.D.month + "-" + this.rl;
        },
        flash: function (m, btn) {
          var self = this;
          this.msg = m;
          if (GV.announce) GV.announce(m);
          clearTimeout(this._msgT);
          this._msgT = setTimeout(function () { self.msg = ""; }, 6000);
          if (btn) { btn.classList.add("is-done"); setTimeout(function () { btn.classList.remove("is-done"); }, 1600); }
        },
        copyText: function (btn) {
          var self = this;
          writeText(this.plain()).then(function () { self.flash(self.ui.copied_text, btn); }, function () { self.flash(self.ui.copy_failed); });
        },
        copyHtml: function (btn) {
          var self = this, text = this.plain(), html = emailHtml(this.docBlocks(), this.docLang());
          var fallback = function () {
            if (legacyCopy(text, html)) return self.flash(self.ui.copied_html, btn);
            writeText(text).then(function () { self.flash(self.ui.copied_plain, btn); }, function () { self.flash(self.ui.copy_failed); });
          };
          if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write && window.isSecureContext) {
            try {
              var item = new window.ClipboardItem({ "text/html": new Blob([html], { type: "text/html" }), "text/plain": new Blob([text], { type: "text/plain" }) });
              navigator.clipboard.write([item]).then(function () { self.flash(self.ui.copied_html, btn); }, fallback);
              return;
            } catch (e) { /* older ClipboardItem */ }
          }
          fallback();
        },
        download: function (kind) {
          var name = this.fileBase() + (kind === "txt" ? ".txt" : ".docx");
          var blob = kind === "txt"
            ? new Blob([BOM + this.plain().replace(/\n/g, "\r\n")], { type: "text/plain;charset=utf-8" })
            : docx(this.docBlocks(), this.docLang(), this.titleLine());
          saveBlob(blob, name);
          this.flash(fmt(this.ui.downloaded, { file: name }));
        },
        // (name: an earlier Area report's — donePrint shows it in the preview until it is printed)
        print: function (name) {
          var was = document.title, self = this;
          // the name "Save as PDF" suggests (the Area report: its dated file name, for the committee's Drive)
          document.title = typeof name === "string" ? name : this.D.area ? this.fileBase() : this.titleLine();
          var restore = function () { document.title = was; self.shown = ""; window.removeEventListener("afterprint", restore); };
          window.addEventListener("afterprint", restore);
          this.$nextTick(function () { window.print(); if (!("onafterprint" in window)) restore(); });
        },
        // One tap, whatever the report's length. Short enough for a wa.me link: WhatsApp opens with it
        // written in. Longer (the usual full report): a phone's share sheet takes the whole text
        // (WhatsApp is in it); elsewhere the text is copied and WhatsApp opens, to paste it into a chat.
        // Only when neither can work (the share sheet fails, copying is blocked) the help box shows.
        whatsapp: function () {
          var self = this, text = this.plain();
          var url = "https://wa.me/?text=" + encodeURIComponent(text);
          this.waLong = false;
          if (url.length <= WA_MAX) {
            openLink(url, true);
            this.flash(fmt(this.ui.opening, { app: "WhatsApp" }));
            return;
          }
          var touch = !!(window.matchMedia && window.matchMedia("(pointer: coarse)").matches);
          if (touch && navigator.share) {
            navigator.share({ text: text }).catch(function (e) { if (!e || e.name !== "AbortError") self.waHelp(); });
            return;
          }
          // copied synchronously, while the tap still counts and before WhatsApp takes the focus
          if (legacyCopy(text)) {
            openLink("https://wa.me/", true);
            this.flash(this.ui.wa_copied);
            return;
          }
          this.waHelp();
        },
        waHelp: function () {
          this.waLong = true;
          this.$nextTick(function () { var h = document.getElementById("rp-wa-title"); if (h) h.focus(); });
        },
        closeWa: function () {
          this.waLong = false;
          this.$nextTick(function () { var b = document.querySelector("[data-rp-wa]"); if (b) b.focus(); });
        },
        waOpen: function () { openLink("https://wa.me/", true); },
        shareNative: function () {
          if (!navigator.share) return;
          navigator.share({ title: this.titleLine(), text: this.plain() }).catch(function () { /* cancelled */ });
        },
        email: function () {
          var self = this, subject = this.titleLine(), text = this.plain();
          var url = "mailto:?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(text);
          if (url.length <= MAIL_MAX) { openLink(url, false); return; }
          var short = "mailto:?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(this.lm().paste);
          writeText(text).then(function () { self.flash(self.ui.mail_long); }, function () { self.flash(self.ui.copy_failed); })
            .then(function () { openLink(short, false); });
        },

        /* ---- editing comfort ---- */
        // The preview follows the section being edited (only when the preview scrolls by itself).
        focusSec: function (id) {
          this.active = id;
          var box = this.$refs.doc;
          this.$nextTick(function () {
            if (!box) return;
            var el = box.querySelector('[data-sec="' + id + '"]');
            var oy = getComputedStyle(box).overflowY;
            if (!el || (oy !== "auto" && oy !== "scroll") || box.scrollHeight <= box.clientHeight + 4) return;
            // the site's own "Less motion" choice counts too (an explicit behavior overrides the CSS rule)
            var reduce = window.GV && GV.reducedMotion ? GV.reducedMotion() : (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
            box.scrollTo({ top: Math.max(0, el.offsetTop - 16), behavior: reduce ? "auto" : "smooth" });
          });
        },
        grow: function (el) {
          if (!el || (window.CSS && CSS.supports && CSS.supports("field-sizing", "content"))) return;
          el.style.height = "auto";
          el.style.height = el.scrollHeight + 2 + "px";
        },
        growAll: function () {
          var self = this;
          this.$root.querySelectorAll("textarea.rp-text").forEach(function (t) { if (t.offsetParent) self.grow(t); });
        },
      };
    });
  });
})();
