/* The service expense tracker's logic (/expenses/, src/pages/expenses.njk + expenses.js).
   Pure functions, no DOM: this file only knows about entries, settings and text. The page's app
   (expenses.js) owns storage, IndexedDB receipts, the forms and the words on screen. Tested in Node
   by tests/test_expenses_core.py (the file runs in a vm context, as sw-core.js does).
   A plain script (no imports, ES2019): it defines window.GVX (globalThis.GVX in Node).

   DATA MODEL (schema 1) — localStorage["gv-expenses:v1"] = {v: 1, entries, settings, meta}
   * An entry is FLAT, so a CSV row maps to it one column to one field (CSV_COLUMNS below).
     type: expense · mileage · received · giveaway (items given out, no money) · stock (items received
     at no cost). Money is always INTEGER CENTS (amount_cents ≥ 0); the sign comes from the type
     (signed: received +, expense and mileage −, giveaway and stock 0) and is never stored.
   * Mileage: miles (1 decimal, already doubled for a round trip; odometer end − start when both are
     set — the odometer is the whole trip) × rate (a string, dollars per mile, up to 3 decimals, kept
     on the entry so changing a rate never changes old entries):
       amount_cents = round(miles × 1000 × round(rate × 1000) / 10000)
     done in whole numbers (milli-miles × mills), rounding half up — never a float in between.
   * funder = who pays for it in the end ("me" = self-supported; for received: who the money came
     from). claim_status: none · to_request · submitted · paid · denied. Paid by the funder directly
     (method "direct") is kept for the record and is never part of "my spending".
   * Derived, never stored: signed cents, sub_end (sub_start + sub_term months), renewals, balances.
   * Settings are the visitor's own copy of config/expenses.yml (mergeDefaults), plus everything
     they add. settings.builtins_seen remembers which built-in ids this browser has already been
     given, so a built-in the visitor deleted is not brought back, while a new one is added.

   MONEY OWED — one rule for the Area, a district, a group and a person you helped:
     claimed  = expenses + mileage charged to that funder with status to_request / submitted / paid
                (not "direct", not repaid "forgiven")
     settled  = the part marked paid (or, for a person, marked repaid)
     received = money recorded as received FROM that funder
     balance  = max(received, settled) − claimed      (< 0: they owe you; > 0: you hold their money)
   So marking a request "paid" settles it even when the check itself was not recorded, and a
   recorded check is never counted twice.

   CSV CONTRACT (toCSV / parseCSV / planImport) — the file is the visitor's own, so it has everything:
   * Written: UTF-8 with a BOM, CRLF, commas, RFC 4180 quotes. Header = the English ids in
     CSV_COLUMNS, whatever the page language, then "custom:<label>" per custom field. Amounts are
     plain "1234.50" (signed_amount is negative for spending), yes/no is "yes" / "", tags are joined
     with "; ". category_label and funder_name are in the page language, for people.
   * Formula guard: a TEXT cell that starts with = + - @ TAB or CR (after any ') gets one leading ';
     the reader takes exactly one ' off such a cell. Number and date cells are never touched.
   * Read: a BOM, CRLF / LF / CR, "," ";" or TAB (from the header, outside quotes; an Excel "sep=;"
     line too), quoted fields with line breaks, blank lines skipped, ragged rows padded.
     Money "$1,234.50", "1.234,50", "12,50", "(12.00)", "-12.00"; dates ISO, M/D/YYYY or D/M/YYYY
     (opts.dateOrder), YYYY/MM/DD, "27 Sep 2026", Excel serial numbers in date columns.
   * Our own file (a header with id, or type + date + amount): columns by name, any order. Anything
     else: needsMapping → the page asks which column is the date, description, amount … and calls
     planImport again with opts.mapping.
   * Rows with an id: update when newer, skip when the same or older. Without an id: a fingerprint
     (type | date | cents | description) already in the ledger is a duplicate (skipped unless asked).
   * Round-trip law (tested): planImport(parseCSV(toCSV(E))) into an empty ledger gives back E.
   * planImport never throws: problems come back as message keys ("expenses.err.*" stop a row or the
     file; "expenses.warn.*" are shown and the row is still imported).

   BACKUP: {format: "gv-expenses-backup", v, exported, entries, settings, meta, receipts: [{id, type,
   dataUrl}]}. readBackup also takes the stored state itself and an older plain list of entries. */
(function (root) {
  "use strict";

  var VERSION = "1.0.0";
  var SCHEMA = 1;
  var STORAGE_KEY = "gv-expenses:v1";
  var BACKUP_FORMAT = "gv-expenses-backup";
  var LIMITS = { bytes: 10 * 1024 * 1024, rows: 20000, cents: 99999999999, number: 1e9, text: 5000 };

  var TYPES = ["expense", "mileage", "received", "giveaway", "stock"];
  var TEMPLATES = ["general", "books", "subscription", "lodging", "meal", "printing", "travel", "mileage", "received", "giveaway", "stock"];
  var FUNDER_KINDS = ["self", "area", "district", "group", "committee", "person", "other"];
  var CLAIM = ["none", "to_request", "submitted", "paid", "denied"];
  var CLAIMED = ["to_request", "submitted", "paid"];
  var FORMATS = ["gv", "lv", "other"];
  var SUB_PRODUCTS = ["gv_print", "gv_online", "gv_complete", "lv_print", "lv_online", "lv_complete", "other"];
  var SUB_KINDS = ["gift", "helped", "group", "self"];
  var REPAID = ["owed", "repaid", "forgiven"];
  var RECEIPT = ["none", "paper", "photo", "file"];
  var CUSTOM_TYPES = ["text", "number", "date", "yesno", "choice"];
  var SELF = "me";          // the self-supported funder
  var DIRECT = "direct";    // payment method: paid by the funder directly, no money of mine
  // the template a new category gets when an import brings one we don't know
  var TYPE_TEMPLATE = { expense: "general", mileage: "mileage", received: "received", giveaway: "giveaway", stock: "stock" };

  /* The entry's fields and how each one is kept. str: one line of text · text: may have line
     breaks · date: "YYYY-MM-DD" or "" · cents: integer cents or "" · num: a number or "" ·
     int: a whole number or "" · bool · enum (list) · tags · custom. */
  var FIELDS = {
    id: "str", type: "enum", date: "date", end_date: "date", category: "str", description: "text",
    amount_cents: "cents", funder: "str", claim_status: "enum", claim_date: "date", claim_ref: "str",
    paid_date: "date", method: "str", vendor: "str", event: "str", place: "str", person: "str", item: "str",
    format: "enum", quantity: "num", unit_cost_cents: "cents", giveaway: "bool", miles: "num", rate: "rate",
    from: "str", to: "str", round_trip: "bool", odometer_start: "num", odometer_end: "num", nights: "int",
    attendees: "int", sub_product: "enum", sub_term: "int", sub_start: "date", sub_kind: "enum",
    repaid: "enum", receipt: "enum", receipt_ref: "str", tags: "tags", notes: "text", custom: "custom",
    created: "stamp", updated: "stamp", example: "bool",
  };
  var ENUMS = { type: TYPES, claim_status: CLAIM, format: FORMATS, sub_product: SUB_PRODUCTS, sub_kind: SUB_KINDS, repaid: REPAID, receipt: RECEIPT };

  // The CSV header, in order. Never rename a column: other devices' files are read by these names.
  var CSV_COLUMNS = ["id", "date", "end_date", "type", "category", "category_label", "description", "amount", "signed_amount",
    "funder", "funder_name", "claim_status", "claim_date", "claim_ref", "paid_date", "method", "vendor", "event", "place",
    "person", "item", "format", "quantity", "unit_cost", "giveaway", "miles", "rate", "from", "to", "round_trip",
    "odometer_start", "odometer_end", "nights", "attendees", "sub_product", "sub_term", "sub_start", "sub_end", "sub_kind",
    "repaid", "receipt", "receipt_ref", "tags", "notes", "created", "updated"];
  // columns that are numbers or dates (never guarded against formulas); everything else is text
  var CSV_NUMERIC = { amount: 1, signed_amount: 1, quantity: 1, unit_cost: 1, miles: 1, rate: 1, odometer_start: 1, odometer_end: 1,
    nights: 1, attendees: 1, sub_term: 1, date: 1, end_date: 1, claim_date: 1, paid_date: 1, sub_start: 1, sub_end: 1, created: 1, updated: 1 };

  /* Every message key the core can hand back (the page has each one in src/_i18n/expenses.json).
     err: the entry / row / file can't be used as it is; warn: shown, and the row is still kept. */
  var MESSAGE_KEYS = [
    "expenses.err.amount", "expenses.err.amount_too_large", "expenses.err.backup_foreign", "expenses.err.backup_invalid",
    "expenses.err.backup_newer", "expenses.err.category_required", "expenses.err.category_unknown", "expenses.err.custom_choice",
    "expenses.err.custom_date", "expenses.err.custom_number", "expenses.err.date", "expenses.err.date_required",
    "expenses.err.description_required", "expenses.err.empty", "expenses.err.end_before_start", "expenses.err.funder_required",
    "expenses.err.funder_unknown", "expenses.err.looks_like_backup", "expenses.err.mapping_required", "expenses.err.miles_required",
    "expenses.err.no_rows", "expenses.err.not_csv", "expenses.err.odometer", "expenses.err.paid_before_claim",
    "expenses.err.quantity_required", "expenses.err.too_big", "expenses.err.too_many_rows", "expenses.err.type", "expenses.err.unreadable",
    "expenses.warn.amount_negative", "expenses.warn.category_type", "expenses.warn.category_unknown", "expenses.warn.date_ignored",
    "expenses.warn.format_unknown", "expenses.warn.funder_unknown", "expenses.warn.id_invalid", "expenses.warn.miles_negative",
    "expenses.warn.no_rate", "expenses.warn.number_ignored", "expenses.warn.quantity_negative", "expenses.warn.rate",
    "expenses.warn.skip_duplicate", "expenses.warn.skip_duplicate_id", "expenses.warn.skip_error", "expenses.warn.skip_older",
    "expenses.warn.skip_same", "expenses.warn.status_unknown",
  ];
  /* The page's strings that claimLines / claimText read (from the `strings` they are given; the
     "expenses." prefix is optional). sub_kind.<id> and sub_product.<id> are used when present. */
  var STRING_KEYS = ["expenses.claim.title", "expenses.claim.from", "expenses.claim.period", "expenses.claim.none", "expenses.claim.miles_at",
    "expenses.claim.receipt", "expenses.claim.total_miles", "expenses.claim.by_category", "expenses.claim.total", "expenses.claim.receipts",
    "expenses.claim.term"];

  /* ------------------------------------------------------------------ small helpers */
  var hasOwn = Object.prototype.hasOwnProperty;
  function has(o, k) { return !!o && typeof o === "object" && hasOwn.call(o, k); }
  function isObj(v) { return !!v && typeof v === "object" && !Array.isArray(v); }
  function arr(v) { return Array.isArray(v) ? v : []; }
  function str(v) { return v === null || v === undefined ? "" : typeof v === "string" ? v : typeof v === "number" || typeof v === "boolean" ? String(v) : ""; }
  function oneLine(v) { return str(v).replace(/[\r\n\t]+/g, " ").replace(/\s+/g, " ").trim().slice(0, LIMITS.text); }
  function multiLine(v) { return str(v).replace(/\r\n?/g, "\n").replace(/^\s+|\s+$/g, "").slice(0, LIMITS.text * 4); }
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function clone(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
  function fmt(tpl, vars) {
    return String(tpl || "").replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m; });
  }
  // for matching and searching: lower case, no accents, single spaces
  function norm(s) {
    var t = str(s).toLowerCase();
    if (t.normalize) t = t.normalize("NFD").replace(/[̀-ͯ]/g, "");
    return t.replace(/\s+/g, " ").trim();
  }
  // item keys: case- and space-insensitive (accents are part of a title)
  function itemKey(s) { return str(s).toLowerCase().replace(/\s+/g, " ").trim(); }
  function slug(s) { return norm(s).replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 32); }
  function langOf(lang) { return lang === "es" ? "es" : "en"; }
  // a label that is {en, es} or a plain string (a visitor's own)
  function label(v, lang) {
    if (isObj(v)) return str(v[langOf(lang)] || v.en || v.es);
    return str(v);
  }
  function itemLabel(item, lang) { return item ? label(has(item, "label") ? item.label : item.name, lang) : ""; }
  function byOrder(a, b) { return (Number(a.order) || 0) - (Number(b.order) || 0); }
  function findById(list, id) { list = arr(list); for (var i = 0; i < list.length; i++) if (list[i] && list[i].id === id) return list[i]; return null; }

  var idSeq = 0;
  function newId() {
    idSeq = (idSeq + 1) % 1296;
    return "x" + Date.now().toString(36) + idSeq.toString(36).padStart(2, "0") + Math.floor(Math.random() * 1679616).toString(36).padStart(4, "0");
  }
  function validId(v) { return typeof v === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(v); }
  function nowISO() { return new Date().toISOString(); }
  function validStamp(v) { return typeof v === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?$/.test(v) && !isNaN(Date.parse(v)); }

  /* ------------------------------------------------------------------ dates */
  var MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "setiembre"];
  function daysInMonth(y, m) { return new Date(Date.UTC(y, m, 0)).getUTCDate(); }
  function ymd(y, m, d) {
    if (!(y >= 1900 && y <= 2200 && m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m))) return null;
    return y + "-" + pad2(m) + "-" + pad2(d);
  }
  function isISO(v) { return typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && ymd(+v.slice(0, 4), +v.slice(5, 7), +v.slice(8, 10)) === v; }
  function dayNum(iso) { return Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / 864e5; }
  function fromDayNum(n) { var d = new Date(n * 864e5); return d.getUTCFullYear() + "-" + pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()); }
  function daysBetween(a, b) { return isISO(a) && isISO(b) ? dayNum(b) - dayNum(a) : null; }
  function addDays(iso, n) { return isISO(iso) ? fromDayNum(dayNum(iso) + Math.round(Number(n) || 0)) : ""; }
  // "YYYY-MM-DD" + n months; the day is kept, or the month's last day (Jan 31 + 1 month = Feb 28/29)
  function addMonths(iso, n) {
    if (!isISO(iso)) return "";
    n = Math.round(Number(n) || 0);
    var t = (+iso.slice(0, 4)) * 12 + (+iso.slice(5, 7) - 1) + n;
    var y = Math.floor(t / 12), m = t - y * 12 + 1;
    return ymd(y, m, Math.min(+iso.slice(8, 10), daysInMonth(y, m))) || "";
  }
  // the visitor's own calendar day (not UTC: at 8 pm in Texas it is still today)
  function todayISO(d) { d = d || new Date(); return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate()); }
  function monthOf(word) {
    var w = word.replace(/\.$/, "");
    if (w.length < 3 || !/^[a-z]+$/.test(w)) return 0;
    for (var i = 0; i < MONTH_NAMES.length; i++) if (MONTH_NAMES[i].indexOf(w) === 0) return i === 24 ? 9 : (i % 12) + 1;
    return 0;
  }
  function excelSerial(n) {
    n = Math.floor(Number(n));
    return n >= 20000 && n <= 80000 ? fromDayNum(dayNum("1899-12-30") + n) : null;
  }
  /* A date as the visitor or a spreadsheet wrote it → "YYYY-MM-DD", or null.
     opts.dateOrder "mdy" (default) or "dmy" decides 3/4/2026; 13/4/2026 and 4/13/2026 decide
     themselves. opts.serial: the column is a date, so Excel's serial numbers (20000–80000) count. */
  function parseDate(v, opts) {
    opts = opts || {};
    if (typeof v === "number") return opts.serial ? excelSerial(v) : null;
    var s = str(v).trim().replace(/^'/, "");
    if (!s) return null;
    var m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T\s].*)?$/.exec(s);
    if (m) return ymd(+m[1], +m[2], +m[3]);
    m = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})(?:\s.*)?$/.exec(s);
    if (m) {
      var a = +m[1], b = +m[2], y = m[3].length === 2 ? (+m[3] < 70 ? 2000 : 1900) + +m[3] : +m[3];
      var dmy = opts.dateOrder === "dmy";
      if (a > 12 && b <= 12) dmy = true; else if (b > 12 && a <= 12) dmy = false;
      return dmy ? ymd(y, b, a) : ymd(y, a, b);
    }
    if (/^\d{5}(\.\d+)?$/.test(s)) return opts.serial ? excelSerial(s) : null;
    // "27 Sep 2026", "Sep 27, 2026", "27-sep-26", "27 de septiembre de 2026", "Sunday, September 27, 2026"
    var words = norm(s).replace(/[,/]|\bde\b|\bdel\b/g, " ").split(/[\s-]+/);
    var month = 0, nums = [];
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (!w) continue;
      if (/^\d{1,4}(st|nd|rd|th|o)?$/.test(w)) nums.push(w.replace(/\D+$/, ""));
      else if (!month && monthOf(w)) month = monthOf(w);
      else if (/\d/.test(w)) return null;
    }
    if (!month || nums.length !== 2) return null;
    var day = nums[0].length === 4 ? nums[1] : nums[0], yr = nums[0].length === 4 ? nums[0] : nums[1];
    if (day.length > 2 || (yr.length !== 2 && yr.length !== 4)) return null;
    return ymd(yr.length === 2 ? (+yr < 70 ? 2000 : 1900) + +yr : +yr, month, +day);
  }

  /* ------------------------------------------------------------------ money and numbers */
  /* A decimal number as people type it: "1,234.50", "1.234,50", "12,50", "1 234,5", "(12.00)", "-12",
     "$12", "12 US$" → {neg, int: "1234", frac: "50"} (digits as text, so nothing is rounded yet), or null.
     One kind of separator used once decides itself when 1–2 digits follow it ("12,50" = 12.50);
     with exactly 3 digits after it ("1,234" / "1.234") opts.decimal ("." by default) decides. */
  function decParts(v, opts) {
    opts = opts || {};
    var s;
    if (typeof v === "number") { if (!isFinite(v)) return null; s = String(v); if (/e/i.test(s)) return null; }
    else s = str(v);
    s = s.trim().replace(/^'/, "").replace(/[−‒–—﹣－]/g, "-");
    var neg = false;
    if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
    s = s.replace(/US\$|USD|\$|€|£/gi, "").replace(/[\s    '’]/g, "");
    if (/^[-+]/.test(s)) { if (s.charAt(0) === "-") neg = !neg; s = s.slice(1); }
    else if (/-$/.test(s)) { neg = !neg; s = s.slice(0, -1); }
    if (!/^[0-9.,]*[0-9][0-9.,]*$/.test(s)) return null;
    var dots = s.split(".").length - 1, commas = s.split(",").length - 1;
    var dflt = opts.decimal === "," ? "," : ".";
    var dec;
    if (!dots && !commas) dec = "";
    else if (dots && commas) dec = s.lastIndexOf(".") > s.lastIndexOf(",") ? "." : ",";
    else {
      var sep = dots ? "." : ",";
      if (dots + commas > 1) dec = "";
      else {
        var after = s.length - s.indexOf(sep) - 1;
        if (after <= 2) dec = sep;
        // "0,655" / ",655" are never thousands
        else if (after === 3) dec = sep === dflt || /^0?$/.test(s.slice(0, s.indexOf(sep))) ? sep : "";
        else if (sep === dflt || /^0?$/.test(s.slice(0, s.indexOf(sep)))) dec = sep;
        else return null;
      }
    }
    var intStr = s, frac = "";
    if (dec) { var at = s.lastIndexOf(dec); intStr = s.slice(0, at); frac = s.slice(at + 1); }
    if (!/^\d*$/.test(frac)) return null;
    if (/[.,]/.test(intStr)) {
      var thou = dec === "." ? "," : dec === "," ? "." : (dots ? "." : ",");
      var parts = intStr.split(thou);
      if (/[.,]/.test(parts.join("")) || !/^\d{1,3}$/.test(parts[0])) return null;
      for (var i = 1; i < parts.length; i++) if (!/^\d{3}$/.test(parts[i])) return null;
      intStr = parts.join("");
    }
    intStr = intStr.replace(/^0+(?=\d)/, "");
    if (intStr.length > 12) return null;
    return { neg: neg, int: intStr || "0", frac: frac };
  }
  // the parts as a whole number of 1/10^places, rounded half away from zero
  function scaled(p, places) {
    var f = (p.frac + "000000").slice(0, places);
    var n = Number(p.int) * Math.pow(10, places) + (places ? Number(f) : 0);
    if ((p.frac.charAt(places) || "0") >= "5") n += 1;
    return p.neg && n ? -n : n;
  }
  // "$1,234.50" → 123450 (integer cents; negative for "(12.00)" / "-12"), or null
  function parseMoney(v, opts) { var p = decParts(v, opts); return p ? scaled(p, 2) : null; }
  function parseNumber(v, opts) { var p = decParts(v, opts); return p ? (p.neg ? -1 : 1) * Number(p.int + "." + (p.frac || "0")) : null; }
  // integer cents → "1234.50" / "-12.00" (exact: no float is formatted)
  function centsText(c) {
    c = Math.round(Number(c) || 0);
    var a = Math.abs(c);
    return (c < 0 ? "-" : "") + Math.floor(a / 100) + "." + pad2(a % 100);
  }
  var moneyFmt = {};
  function fmtMoney(cents, lang) {
    var l = langOf(lang);
    if (!has(moneyFmt, l)) {
      try { moneyFmt[l] = new Intl.NumberFormat(l === "es" ? "es-US" : "en-US", { style: "currency", currency: "USD" }); }
      catch (e) { moneyFmt[l] = null; }
    }
    var c = Math.round(Number(cents) || 0);
    return moneyFmt[l] ? moneyFmt[l].format(c / 100) : (c < 0 ? "-$" : "$") + centsText(Math.abs(c));
  }
  var dateFmt = {};
  // "Sep 27, 2026" / "27 sept 2026", as on the rest of the site (es-US)
  function fmtDate(iso, lang) {
    if (!isISO(iso)) return str(iso);
    var l = langOf(lang);
    if (!has(dateFmt, l)) {
      try { dateFmt[l] = new Intl.DateTimeFormat(l === "es" ? "es-US" : "en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }); }
      catch (e) { dateFmt[l] = null; }
    }
    return dateFmt[l] ? dateFmt[l].format(new Date(dayNum(iso) * 864e5)) : iso;
  }

  /* Mileage. rate: dollars per mile, up to 3 decimals ("0.14", "0.655"; "0,14" is read too) → mills
     (thousandths of a dollar), or null. The canonical text keeps 2 or 3 places ("0.14", "0.655"). */
  function rateMills(rate) {
    var p = decParts(typeof rate === "number" ? rate : str(rate), { decimal: "." });
    if (!p || p.neg) return null;
    var m = scaled(p, 3);
    return m <= 99999 ? m : null;
  }
  function rateText(rate) {
    var m = rateMills(rate);
    if (m === null) return "";
    var t = Math.floor(m / 1000) + "." + ("00" + (m % 1000)).slice(-3);
    return t.slice(-1) === "0" ? t.slice(0, -1) : t;
  }
  /* amount_cents = round(miles × 1000 × round(rate × 1000) / 10000), in whole numbers:
     milli-miles × mills is exact (1/10000 of a cent); then half up to the cent. */
  function mileageCents(miles, rate) {
    var mi = typeof miles === "number" ? miles : parseNumber(miles, { decimal: "." });
    var mm = Math.round((mi || 0) * 1000);
    var r = rateMills(rate);
    if (!(mm > 0) || !r) return 0;
    var p = mm * r;
    if (p > 9007199254740991) return Math.round(p / 10000);
    var rem = p % 10000;
    return (p - rem) / 10000 + (rem >= 5000 ? 1 : 0);
  }
  /* The miles an entry keeps: the odometer (the whole trip) when both readings are there, else the
     miles typed, doubled for a round trip; 1 decimal. */
  function tripMiles(oneWay, roundTrip, odoStart, odoEnd) {
    var a = numOrBlank(odoStart), b = numOrBlank(odoEnd);
    if (a !== "" && b !== "" && b >= a) return Math.round((b - a) * 10) / 10;
    var m = numOrBlank(oneWay);
    if (!(m > 0)) return 0;
    return Math.round(m * (roundTrip ? 2 : 1) * 10) / 10;
  }
  // a number field: a finite number, or "" (blank / unreadable)
  function numOrBlank(v, opts) {
    if (typeof v === "number") return isFinite(v) ? v : "";
    if (str(v).trim() === "") return "";
    var n = parseNumber(v, opts || { decimal: "." });
    return n === null ? "" : n;
  }

  /* ------------------------------------------------------------------ settings */
  var LISTS = ["categories", "funders", "methods", "rates"];
  function dayCount(v, dflt) { var n = Number(v); return Number.isInteger(n) && n >= 1 && n <= 365 ? n : dflt; }

  /* The visitor's settings = their stored copy + the site's defaults (config/expenses.yml, handed over
     by the page as <script id="xp-config">).
     * Everything the visitor changed stays: renames (a label that is a plain string is theirs), hidden,
       order, colours, icons, rates, their own categories / funders / methods / rates.
     * A built-in label still in its {en, es} form follows the site (so a corrected wording arrives).
     * A built-in that is new since last time is added at the end; one the visitor deleted is not
       brought back (settings.builtins_seen), and a deleted custom one never comes back (only the
       stored copy knows it). */
  function mergeDefaults(configDefaults, storedSettings) {
    var cfg = isObj(configDefaults) ? configDefaults : {};
    var st = isObj(storedSettings) ? clone(storedSettings) : null;
    var out = st ? st : {};
    var seenBefore = st && isObj(st.builtins_seen) ? st.builtins_seen : null;
    var seen = {};
    LISTS.forEach(function (key) {
      var defs = arr(cfg[key]).filter(function (x) { return isObj(x) && validId(str(x.id)); });
      var mine = st && Array.isArray(st[key]) ? st[key].filter(function (x) { return isObj(x) && validId(str(x.id)); }) : null;
      var known = seenBefore && Array.isArray(seenBefore[key]) ? seenBefore[key].map(str) : (mine ? mine.map(function (x) { return str(x.id); }) : []);
      var list = [], ids = {};
      (mine || []).forEach(function (item) {
        if (ids[item.id]) return;
        ids[item.id] = 1;
        var def = findById(defs, item.id);
        var merged;
        if (def) {
          merged = Object.assign(clone(def), item, { builtin: true });
          ["label", "name", "note"].forEach(function (k) { if (isObj(item[k]) && isObj(def[k])) merged[k] = clone(def[k]); });
        } else merged = Object.assign({}, item, defs.length ? { builtin: false } : {}); // no site defaults given: flags as stored
        list.push(merged);
      });
      var top = list.reduce(function (m, x) { return Math.max(m, Number(x.order) || 0); }, -1);
      defs.forEach(function (def, i) {
        if (ids[def.id]) return;
        if (mine && known.indexOf(def.id) >= 0) return; // the visitor deleted it
        var add = clone(def);
        add.builtin = true;
        add.hidden = !!add.hidden;
        add.order = mine ? ++top : (has(def, "order") ? def.order : i);
        ids[def.id] = 1;
        list.push(add);
      });
      seen[key] = known.concat(defs.map(function (d) { return d.id; }).filter(function (id) { return known.indexOf(id) < 0; }));
      out[key] = list;
    });
    // the self-supported funder is part of the model: it is always there
    if (!findById(out.funders, SELF)) {
      var me = findById(cfg.funders, SELF);
      out.funders.unshift(me ? Object.assign(clone(me), { builtin: true, hidden: false, order: -1 }) : { id: SELF, kind: "self", name: { en: "Me (self-supported)", es: "Yo (autofinanciado)" }, builtin: true, hidden: false, order: -1 });
    }
    findById(out.funders, SELF).kind = "self";
    out.funders.forEach(function (f) { if (FUNDER_KINDS.indexOf(f.kind) < 0) f.kind = "other"; });
    out.builtins_seen = seen;

    var rateIds = out.rates.map(function (r) { return r.id; });
    out.default_rate = st && rateIds.indexOf(st.default_rate) >= 0 ? st.default_rate
      : rateIds.indexOf(cfg.default_rate) >= 0 ? cfg.default_rate : (rateIds[0] || "");
    var d = Object.assign({ funder: SELF, method: "", rate: "", round_trip: false, claim_status: "to_request" },
      isObj(cfg.defaults) ? cfg.defaults : {}, st && isObj(st.defaults) ? st.defaults : {});
    if (!findById(out.funders, d.funder)) d.funder = SELF;
    if (!findById(out.methods, d.method)) d.method = out.methods.length ? out.methods[0].id : "";
    if (rateIds.indexOf(d.rate) < 0) d.rate = out.default_rate;
    d.round_trip = !!d.round_trip;
    if (["none", "to_request"].indexOf(d.claim_status) < 0) d.claim_status = "to_request";
    out.defaults = d;
    out.renewal_days = dayCount(st && st.renewal_days, dayCount(cfg.renewal_days, 60));
    out.backup_reminder_days = dayCount(st && st.backup_reminder_days, dayCount(cfg.backup_reminder_days, 30));
    ["budgets", "custom_fields"].forEach(function (k) { out[k] = arr(st && st[k]).filter(isObj); });
    out.places = arr(st && st.places).map(oneLine).filter(Boolean);
    out.profile = Object.assign({ name: "", position: "", district: "", email: "" }, st && isObj(st.profile) ? st.profile : {});
    out.ui = st && isObj(st.ui) ? st.ui : {};
    out.panels = (Array.isArray(cfg.panels) ? cfg.panels : arr(st && st.panels)).filter(function (p) { return isObj(p) && isISO(p.from) && isISO(p.to); }).map(clone);
    return out;
  }

  function emptyState(defaultsFromConfig) {
    return { v: SCHEMA, entries: [], settings: mergeDefaults(defaultsFromConfig, null), meta: { lastBackup: null, lastExport: null, created: nowISO() } };
  }

  // lookups
  function catOf(S, id) { return isObj(S) ? findById(S.categories, id) : null; }
  function funderOf(S, id) { return isObj(S) ? findById(S.funders, id) : null; }
  function isSelf(S, id) { if (!id || id === SELF) return !!id; var f = funderOf(S, id); return !!f && f.kind === "self"; }
  function isPerson(S, id) { var f = funderOf(S, id); return !!f && f.kind === "person"; }
  function defaultCategory(S, type) {
    var list = arr(isObj(S) ? S.categories : null).filter(function (c) { return c && c.type === type; }).slice().sort(byOrder);
    var shown = list.filter(function (c) { return !c.hidden; });
    return (shown[0] || list[0] || { id: "" }).id;
  }
  function templateOf(S, entry) { var c = catOf(S, entry.category); return c && TEMPLATES.indexOf(c.template) >= 0 ? c.template : TYPE_TEMPLATE[entry.type] || "general"; }
  function categoryLabel(S, id, lang) { var c = catOf(S, id); return c ? label(c.label, lang) : str(id); }
  function funderName(S, id, lang) { var f = funderOf(S, id); return f ? label(f.name, lang) : str(id); }

  /* ------------------------------------------------------------------ one entry */
  function centsOrBlank(v) {
    if (typeof v === "number") return isFinite(v) ? Math.round(v) : "";
    var s = str(v).trim();
    return /^-?\d{1,15}$/.test(s) ? Number(s) : "";
  }
  function intOrBlank(v) { var n = numOrBlank(v); return n === "" ? "" : Math.round(n); }
  function yes(v) {
    if (typeof v === "boolean") return v;
    if (typeof v === "number") return v === 1;
    return ["yes", "y", "true", "1", "si", "x", "on"].indexOf(norm(v)) >= 0;
  }
  function enumOr(v, list, aliases) {
    var s = str(v).trim();
    if (list.indexOf(s) >= 0) return s;
    var n = norm(s).replace(/[\s-]+/g, "_");
    if (list.indexOf(n) >= 0) return n;
    return aliases && has(aliases, n) ? aliases[n] : null;
  }
  var FORMAT_ALIAS = { grapevine: "gv", aa_grapevine: "gv", la_vina: "lv", lavina: "lv", vina: "lv" };
  function cleanTags(v) {
    var list = Array.isArray(v) ? v : str(v).split(/[;\n]/);
    var out = [], seen = {};
    list.forEach(function (t) {
      t = oneLine(t).replace(/;/g, ",").slice(0, 60);
      if (t && !seen[norm(t)]) { seen[norm(t)] = 1; out.push(t); }
    });
    return out.slice(0, 30);
  }
  function customValue(v, field) {
    var type = field && CUSTOM_TYPES.indexOf(field.type) >= 0 ? field.type : "";
    if (type === "yesno") return typeof v === "boolean" ? v : str(v).trim() === "" ? "" : yes(v);
    if (type === "number") { var n = numOrBlank(v); return n === "" ? oneLine(v) : n; }
    if (type === "date") { var d = typeof v === "string" && isISO(v) ? v : parseDate(v, { serial: true }); return d || oneLine(v); }
    if (typeof v === "boolean" || (typeof v === "number" && isFinite(v))) return v;
    return type === "text" || !type ? multiLine(v) : oneLine(v);
  }

  /* raw (the form, an import row, an old backup) → {entry, problems}. Every field is coerced to its
     kind, defaults are filled in, and what follows from other fields is worked out (mileage amount,
     miles from the odometer, nights, the mileage description, books qty × price). Never throws;
     problems are message keys. Normalizing a normalized entry changes nothing. */
  function normalizeEntry(raw, settings) {
    var problems = [];
    try { return { entry: normalizeInner(isObj(raw) ? raw : {}, isObj(settings) ? settings : {}, problems), problems: problems }; }
    catch (err) {
      var e = normalizeInner({}, {}, []);
      return { entry: e, problems: ["expenses.err.unreadable"] };
    }
  }
  function normalizeInner(r, S, problems) {
    var e = {};
    var warn = function (k) { if (problems.indexOf(k) < 0) problems.push(k); };
    e.id = validId(r.id) ? r.id : newId();
    var type = enumOr(r.type, TYPES);
    if (!type) {
      if (str(r.type).trim()) warn("expenses.err.type");
      var c0 = catOf(S, str(r.category));
      type = c0 && TYPES.indexOf(c0.type) >= 0 ? c0.type : "expense";
    }
    e.type = type;
    var money = type === "expense" || type === "mileage";
    var date = isISO(r.date) ? r.date : parseDate(r.date);
    if (!date) warn(str(r.date).trim() ? "expenses.err.date" : "expenses.err.date_required");
    e.date = date || "";
    var end = isISO(r.end_date) ? r.end_date : parseDate(r.end_date);
    if (!end && str(r.end_date).trim()) warn("expenses.warn.date_ignored");
    e.end_date = end || "";

    var catId = oneLine(r.category);
    var cat = catOf(S, catId);
    if (cat && cat.type !== type) { warn("expenses.warn.category_type"); cat = null; catId = ""; }
    if (!cat && catId && isObj(S) && arr(S.categories).length) warn("expenses.warn.category_unknown");
    if (!catId) { catId = defaultCategory(S, type); cat = catOf(S, catId); }
    e.category = validId(catId) ? catId : "";
    var tpl = cat && TEMPLATES.indexOf(cat.template) >= 0 ? cat.template : TYPE_TEMPLATE[type];

    e.description = multiLine(r.description);
    var amt = centsOrBlank(r.amount_cents);
    if (amt === "" && str(r.amount).trim() !== "") { var pm = parseMoney(r.amount); if (pm === null) warn("expenses.err.amount"); else amt = pm; }
    if (amt === "" && str(r.amount_cents).trim() !== "") warn("expenses.err.amount");
    if (amt !== "" && amt < 0) { warn("expenses.warn.amount_negative"); amt = -amt; }
    if (amt !== "" && amt > LIMITS.cents) warn("expenses.err.amount_too_large");
    e.amount_cents = amt === "" ? 0 : amt;

    // who pays in the end, and whether anything is asked back
    var funder = oneLine(r.funder);
    if (!funder && money) funder = (cat && cat.default_funder) || (S.defaults && S.defaults.funder) || SELF;
    if (funder && isObj(S) && arr(S.funders).length && !funderOf(S, funder)) warn("expenses.warn.funder_unknown");
    e.funder = validId(funder) ? funder : (money ? SELF : "");
    e.method = oneLine(r.method);
    if (!has(r, "method") && type === "expense") e.method = (S.defaults && S.defaults.method) || "";
    var cs = enumOr(r.claim_status, CLAIM);
    if (!cs && str(r.claim_status).trim()) warn("expenses.warn.status_unknown");
    if (!money || isSelf(S, e.funder)) cs = "none";
    else if (!cs) cs = e.method === DIRECT ? "none" : (cat && cat.default_claim) || (S.defaults && S.defaults.claim_status) || "to_request";
    e.claim_status = cs;
    e.claim_date = money && isISO(r.claim_date) ? r.claim_date : money ? parseDate(r.claim_date) || "" : "";
    e.claim_ref = oneLine(r.claim_ref);
    e.paid_date = money && isISO(r.paid_date) ? r.paid_date : money ? parseDate(r.paid_date) || "" : "";

    ["vendor", "event", "place", "person", "item"].forEach(function (k) { e[k] = oneLine(r[k]); });
    var fm = enumOr(r.format, FORMATS, FORMAT_ALIAS);
    if (!fm && str(r.format).trim()) warn("expenses.warn.format_unknown");
    e.format = fm || "";
    var q = numOrBlank(r.quantity);
    if (q !== "" && q < 0) { warn("expenses.warn.quantity_negative"); q = -q; }
    e.quantity = q === "" ? "" : Math.round(Math.min(q, LIMITS.number) * 1000) / 1000;
    var uc = centsOrBlank(r.unit_cost_cents);
    if (uc === "" && str(r.unit_cost).trim() !== "") { var pu = parseMoney(r.unit_cost); if (pu !== null) uc = pu; }
    e.unit_cost_cents = uc === "" ? "" : Math.min(Math.abs(uc), LIMITS.cents);
    e.giveaway = type === "expense" ? (has(r, "giveaway") && r.giveaway !== "" && r.giveaway !== null && r.giveaway !== undefined ? yes(r.giveaway) : !!(cat && cat.giveaway_default)) : false;
    if (type === "giveaway" || type === "stock") e.amount_cents = 0;
    if (type === "expense" && !e.amount_cents && e.quantity !== "" && e.unit_cost_cents !== "" && (tpl === "books" || tpl === "printing" || e.giveaway)) {
      e.amount_cents = Math.round(e.quantity * e.unit_cost_cents);
    }

    // mileage
    var mil = type === "mileage";
    e.odometer_start = mil ? numOrBlank(r.odometer_start) : "";
    e.odometer_end = mil ? numOrBlank(r.odometer_end) : "";
    if (mil && e.odometer_start !== "" && e.odometer_end !== "" && e.odometer_end < e.odometer_start) warn("expenses.err.odometer");
    e.round_trip = mil ? yes(r.round_trip) : false;
    var miles = mil ? numOrBlank(r.miles) : "";
    if (mil && e.odometer_start !== "" && e.odometer_end !== "" && e.odometer_end >= e.odometer_start) miles = tripMiles(0, false, e.odometer_start, e.odometer_end);
    if (miles !== "") { if (miles < 0) { warn("expenses.warn.miles_negative"); miles = -miles; } miles = Math.round(Math.min(miles, 1e6) * 10) / 10; }
    e.miles = miles;
    e.rate = mil ? rateText(r.rate) : "";
    if (mil && str(r.rate).trim() && !e.rate) warn("expenses.warn.rate");
    if (mil && e.rate) e.amount_cents = mileageCents(e.miles || 0, e.rate);
    else if (mil && !e.amount_cents && e.miles) warn("expenses.warn.no_rate");
    e.from = oneLine(r.from);
    e.to = oneLine(r.to);
    if (mil && !e.description) e.description = [e.from, e.to].filter(Boolean).join(" → ") || e.event;

    var nights = intOrBlank(r.nights);
    if (tpl === "lodging" && e.date && e.end_date && e.end_date >= e.date) nights = daysBetween(e.date, e.end_date);
    e.nights = nights === "" ? "" : Math.max(0, nights);
    var att = intOrBlank(r.attendees);
    e.attendees = att === "" ? "" : Math.max(0, att);

    // subscriptions
    e.sub_product = enumOr(r.sub_product, SUB_PRODUCTS) || "";
    var term = intOrBlank(r.sub_term);
    e.sub_term = term === "" ? "" : Math.max(0, Math.min(term, 1200));
    e.sub_start = isISO(r.sub_start) ? r.sub_start : parseDate(r.sub_start) || "";
    e.sub_kind = enumOr(r.sub_kind, SUB_KINDS) || "";
    var rp = enumOr(r.repaid, REPAID) || "";
    if (!rp && money && (e.sub_kind === "helped" || isPerson(S, e.funder))) rp = "owed";
    e.repaid = rp;

    e.receipt = enumOr(r.receipt, RECEIPT) || "none";
    e.receipt_ref = oneLine(r.receipt_ref);
    e.tags = cleanTags(r.tags);
    e.notes = multiLine(r.notes);
    var custom = {};
    if (isObj(r.custom)) {
      Object.keys(r.custom).forEach(function (k) {
        if (!validId(k)) return;
        var v = r.custom[k];
        if (v === null || v === undefined || (typeof v === "string" && v.trim() === "")) return;
        var val = customValue(v, findById(S.custom_fields, k));
        if (val !== "") custom[k] = val;
      });
    }
    e.custom = custom;
    var now = nowISO();
    e.created = validStamp(r.created) ? r.created : now;
    e.updated = validStamp(r.updated) ? r.updated : e.created;
    e.example = r.example === true;
    // one key order for every entry (so two copies of an entry compare equal as JSON)
    var out = {};
    Object.keys(FIELDS).forEach(function (k) { out[k] = e[k]; });
    return out;
  }

  /* The form's check before saving → [{field, key}] (an empty list: fine to save). */
  function validateEntry(entry, settings) {
    var e = isObj(entry) ? entry : {}, S = isObj(settings) ? settings : {}, out = [];
    var add = function (field, key) { out.push({ field: field, key: key }); };
    if (TYPES.indexOf(e.type) < 0) add("type", "expenses.err.type");
    if (!e.date) add("date", "expenses.err.date_required");
    else if (!isISO(e.date)) add("date", "expenses.err.date");
    if (e.end_date && (!isISO(e.end_date) || (isISO(e.date) && e.end_date < e.date))) add("end_date", "expenses.err.end_before_start");
    if (!e.category) add("category", "expenses.err.category_required");
    else if (!catOf(S, e.category)) add("category", "expenses.err.category_unknown");
    if ((e.type === "expense" || e.type === "received") && !str(e.description).trim()) add("description", "expenses.err.description_required");
    var a = e.amount_cents;
    if (typeof a !== "number" || !Number.isInteger(a) || a < 0) add("amount_cents", "expenses.err.amount");
    else if (a > LIMITS.cents) add("amount_cents", "expenses.err.amount_too_large");
    if (e.type === "mileage") {
      if (e.odometer_start !== "" && e.odometer_end !== "" && e.odometer_end !== undefined && Number(e.odometer_end) < Number(e.odometer_start)) add("odometer_end", "expenses.err.odometer");
      else if (!(Number(e.miles) > 0)) add("miles", "expenses.err.miles_required");
    }
    if ((e.type === "giveaway" || e.type === "stock") && !(Number(e.quantity) > 0)) add("quantity", "expenses.err.quantity_required");
    if (e.type === "expense" || e.type === "mileage") {
      if (!e.funder) add("funder", "expenses.err.funder_required");
      else if (!funderOf(S, e.funder)) add("funder", "expenses.err.funder_unknown");
    } else if (e.funder && !funderOf(S, e.funder)) add("funder", "expenses.err.funder_unknown");
    if (e.claim_date && e.paid_date && isISO(e.claim_date) && isISO(e.paid_date) && e.paid_date < e.claim_date) add("paid_date", "expenses.err.paid_before_claim");
    arr(S.custom_fields).forEach(function (f) {
      if (!isObj(f) || !isObj(e.custom) || !has(e.custom, f.id)) return;
      var v = e.custom[f.id];
      if (f.type === "number" && typeof v !== "number") add("custom:" + f.id, "expenses.err.custom_number");
      if (f.type === "date" && !isISO(v)) add("custom:" + f.id, "expenses.err.custom_date");
      if (f.type === "choice" && arr(f.options).length && arr(f.options).indexOf(v) < 0) add("custom:" + f.id, "expenses.err.custom_choice");
    });
    return out;
  }

  /* ------------------------------------------------------------------ what follows from an entry */
  function isMoney(e) { return e.type === "expense" || e.type === "mileage"; }
  // received > 0; expense and mileage < 0; giveaway and stock 0
  function signedCents(e) { var a = Number(e && e.amount_cents) || 0; return e.type === "received" ? a : isMoney(e) ? -a : 0; }
  // money that left my pocket (paid by the funder directly is not)
  function isSpent(e) { return isMoney(e) && e.method !== DIRECT; }
  // …and nobody pays it back: self-supported, not asked, denied, or forgiven (a purchase made for a
  // person who pays it back is theirs, even when it was left on "me")
  function isSelfFunded(S, e) {
    if (e.repaid === "forgiven") return true;
    if (e.sub_kind === "helped" && e.person && isSelf(S, e.funder)) return false;
    return isSelf(S, e.funder) || e.claim_status === "none" || e.claim_status === "denied";
  }
  function isClaimed(e) { return isMoney(e) && e.method !== DIRECT && CLAIMED.indexOf(e.claim_status) >= 0 && e.repaid !== "forgiven"; }
  function subEnd(e) { return e && isISO(e.sub_start) && Number(e.sub_term) > 0 ? addMonths(e.sub_start, e.sub_term) : ""; }
  function inRange(e, o) {
    o = o || {};
    if (!o.from && !o.to) return true;
    if (!isISO(e.date)) return false;
    return (!o.from || e.date >= o.from) && (!o.to || e.date <= o.to);
  }
  function list(entries) { return arr(entries).filter(isObj); }
  function qty(e) { var q = Number(e.quantity); return isFinite(q) && q > 0 ? q : 0; }

  /* ------------------------------------------------------------------ the summary */
  /* Totals for a period (opts.from / opts.to, inclusive; either may be left out):
     spent = expenses + mileage I paid (not "direct") = self (nobody pays it back) + claimable (asked
     back: to_request / submitted / paid); owed = what funders still owe (funderBalances). */
  function summary(entries, settings, opts) {
    var S = isObj(settings) ? settings : {};
    opts = opts || {};
    var r = { count: 0, spent_cents: 0, self_cents: 0, claimable_cents: 0, direct_cents: 0, received_cents: 0, owed_cents: 0,
      miles: 0, mileage_cents: 0, items_given: 0, items_bought: 0, items_received: 0, items_on_hand: 0, by_category: [], by_month: [] };
    var cats = {}, months = {};
    var month = function (ym) { return months[ym] || (months[ym] = { ym: ym, spent: 0, received: 0 }); };
    list(entries).forEach(function (e) {
      if (!inRange(e, opts)) return;
      r.count += 1;
      var a = Number(e.amount_cents) || 0;
      var ym = isISO(e.date) ? e.date.slice(0, 7) : "";
      if (e.type === "mileage") { r.miles += Number(e.miles) || 0; r.mileage_cents += a; }
      if (isMoney(e) && e.method === DIRECT) r.direct_cents += a;
      if (isSpent(e)) {
        r.spent_cents += a;
        if (isSelfFunded(S, e)) r.self_cents += a; else r.claimable_cents += a;
        var c = cats[e.category] || (cats[e.category] = { id: e.category, cents: 0, count: 0 });
        c.cents += a; c.count += 1;
        if (ym) month(ym).spent += a;
      } else if (e.type === "received") {
        r.received_cents += a;
        if (ym) month(ym).received += a;
      } else if (e.type === "giveaway") r.items_given += qty(e);
      else if (e.type === "stock") r.items_received += qty(e);
      if (e.type === "expense" && e.giveaway) r.items_bought += qty(e);
    });
    r.miles = Math.round(r.miles * 10) / 10;
    funderBalances(entries, S, opts).forEach(function (b) { if (b.balance_cents < 0) r.owed_cents -= b.balance_cents; });
    peopleOwed(entries, S, opts).forEach(function (p) { if (!p.funder) r.owed_cents += p.owed_cents; }); // helped purchases left on "me"
    inventory(entries, { to: opts.to }).forEach(function (it) { if (it.on_hand > 0) r.items_on_hand += it.on_hand; });
    r.items_on_hand = Math.round(r.items_on_hand * 1000) / 1000;
    r.by_category = Object.keys(cats).map(function (k) { return cats[k]; }).sort(function (a, b) { return b.cents - a.cents || b.count - a.count || (a.id < b.id ? -1 : 1); });
    // every month from the first to the last one with money (gaps shown as 0), at most 20 years
    var keys = Object.keys(months).sort();
    if (keys.length) {
      var y = +keys[0].slice(0, 4), m = +keys[0].slice(5, 7), last = keys[keys.length - 1];
      for (var n = 0; n < 240; n++) {
        var k = y + "-" + pad2(m);
        r.by_month.push(month(k));
        if (k >= last) break;
        m += 1; if (m > 12) { m = 1; y += 1; }
      }
    }
    return r;
  }

  /* Per funder (not "me"), in the settings' order: what was asked of them, by status, what they sent,
     and the balance (see "MONEY OWED" at the top): < 0 they owe you, > 0 you hold their money. */
  function funderBalances(entries, settings, range) {
    var S = isObj(settings) ? settings : {};
    var rows = {};
    var row = function (id) {
      if (!rows[id]) {
        var f = funderOf(S, id);
        rows[id] = { funder: id, kind: f ? f.kind : "other", claimed_cents: 0, to_request_cents: 0, submitted_cents: 0, paid_cents: 0,
          denied_cents: 0, received_cents: 0, settled_cents: 0, balance_cents: 0, count: 0 };
      }
      return rows[id];
    };
    list(entries).forEach(function (e) {
      if (!e.funder || isSelf(S, e.funder) || !inRange(e, range)) return;
      var a = Number(e.amount_cents) || 0;
      if (e.type === "received") { var x = row(e.funder); x.received_cents += a; x.count += 1; return; }
      if (!isMoney(e) || e.method === DIRECT) return;
      var y = row(e.funder);
      y.count += 1;
      if (e.claim_status === "denied") y.denied_cents += a;
      if (!isClaimed(e)) return;
      y.claimed_cents += a;
      y[e.claim_status + "_cents"] += a;
      if (e.claim_status === "paid" || e.repaid === "repaid") y.settled_cents += a;
    });
    var order = arr(S.funders).slice().sort(byOrder).map(function (f) { return f.id; });
    return Object.keys(rows).sort(function (a, b) {
      var ia = order.indexOf(a), ib = order.indexOf(b);
      if (ia < 0) ia = 1e9; if (ib < 0) ib = 1e9;
      return ia - ib || (a < b ? -1 : a > b ? 1 : 0);
    }).map(function (id) {
      var r = rows[id];
      r.balance_cents = Math.max(r.received_cents, r.settled_cents) - r.claimed_cents;
      return r;
    });
  }

  /* People who owe you: helped purchases (a subscription bought for someone who pays you back) and
     anything charged to a funder of kind "person", minus what they paid back. The same rule as
     funderBalances. [{funder, owed_cents, claimed_cents, received_cents, settled_cents, entries}] —
     entries = the ones still open (not repaid / forgiven), oldest first. */
  function peopleOwed(entries, settings, range) {
    var S = isObj(settings) ? settings : {};
    var all = list(entries);
    var people = {};
    all.forEach(function (e) {
      if (!e.funder || isSelf(S, e.funder)) return;
      if (isPerson(S, e.funder) || (isMoney(e) && e.sub_kind === "helped")) people[e.funder] = 1;
    });
    // a helped purchase left on "me" with a person's name: grouped by the name
    var byName = {};
    all.forEach(function (e) {
      if (isMoney(e) && e.sub_kind === "helped" && isSelf(S, e.funder) && e.person && e.repaid !== "forgiven" && inRange(e, range)) {
        var k = norm(e.person), g = byName[k] || (byName[k] = { funder: "", person: e.person, claimed_cents: 0, received_cents: 0, settled_cents: 0, open: [] });
        g.claimed_cents += e.amount_cents;
        if (e.repaid === "repaid") g.settled_cents += e.amount_cents; else g.open.push(e);
      }
    });
    all.forEach(function (e) {
      if (e.type === "received" && (!e.funder || isSelf(S, e.funder)) && e.person && byName[norm(e.person)] && inRange(e, range)) byName[norm(e.person)].received_cents += e.amount_cents;
    });
    var out = [];
    funderBalances(all, S, range).forEach(function (b) {
      if (!people[b.funder] || b.balance_cents >= 0) return;
      var f = funderOf(S, b.funder);
      out.push({ funder: b.funder, person: f ? label(f.name) : b.funder, owed_cents: -b.balance_cents, claimed_cents: b.claimed_cents,
        received_cents: b.received_cents, settled_cents: b.settled_cents,
        entries: all.filter(function (e) { return e.funder === b.funder && isClaimed(e) && e.repaid !== "repaid" && e.claim_status !== "paid" && inRange(e, range); }).sort(byDate) });
    });
    Object.keys(byName).forEach(function (k) {
      var g = byName[k], owed = g.claimed_cents - Math.max(g.received_cents, g.settled_cents);
      if (owed > 0) out.push({ funder: "", person: g.person, owed_cents: owed, claimed_cents: g.claimed_cents, received_cents: g.received_cents, settled_cents: g.settled_cents, entries: g.open.sort(byDate) });
    });
    return out.sort(function (a, b) { return b.owed_cents - a.owed_cents; });
  }
  function byDate(a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : (a.created < b.created ? -1 : a.created > b.created ? 1 : 0); }

  /* Literature to carry the message: per item (title + format; case and spaces don't matter)
     bought (purchases marked "to give away"), received at no cost (stock), given away, on hand
     (can go below 0: flagged `negative`), what the purchases cost, and where it was given.
     opts.to: stock as of that day. */
  function inventory(entries, opts) {
    opts = opts || {};
    var items = {};
    list(entries).forEach(function (e) {
      var buy = e.type === "expense" && e.giveaway;
      if (!buy && e.type !== "stock" && e.type !== "giveaway") return;
      if (opts.to && isISO(e.date) && e.date > opts.to) return;
      if (opts.from && (!isISO(e.date) || e.date < opts.from)) return;
      var key = itemKey(e.item) + "|" + (e.format || "");
      var it = items[key] || (items[key] = { key: key, item: oneLine(e.item), format: e.format || "", bought_qty: 0, received_qty: 0, given_qty: 0,
        on_hand: 0, cost_cents: 0, avg_unit_cents: 0, events: [], negative: false, first_date: e.date, last_date: e.date, _ev: {} });
      var q = qty(e);
      if (buy) { it.bought_qty += q; it.cost_cents += Number(e.amount_cents) || 0; }
      else if (e.type === "stock") it.received_qty += q;
      else {
        it.given_qty += q;
        var ek = norm(e.event);
        var ev = it._ev[ek] || (it._ev[ek] = { event: oneLine(e.event), qty: 0 });
        ev.qty += q;
      }
      if (e.date && (!it.first_date || e.date < it.first_date)) it.first_date = e.date;
      if (e.date && e.date > it.last_date) it.last_date = e.date;
    });
    var coll = collator();
    return Object.keys(items).map(function (k) {
      var it = items[k];
      var r3 = function (n) { return Math.round(n * 1000) / 1000; };
      it.bought_qty = r3(it.bought_qty); it.received_qty = r3(it.received_qty); it.given_qty = r3(it.given_qty);
      it.on_hand = r3(it.bought_qty + it.received_qty - it.given_qty);
      it.negative = it.on_hand < 0;
      it.avg_unit_cents = it.bought_qty > 0 ? Math.round(it.cost_cents / it.bought_qty) : 0;
      it.events = Object.keys(it._ev).map(function (x) { return it._ev[x]; }).sort(function (a, b) { return b.qty - a.qty || coll(a.event, b.event); });
      delete it._ev;
      return it;
    }).sort(function (a, b) { return coll(a.item, b.item) || (a.format < b.format ? -1 : a.format > b.format ? 1 : 0); });
  }

  /* What was given at each event (the Giveaways view, the year summary), newest first:
     [{event, first_date, last_date, total_qty, count, items: [{item, format, qty}]}] */
  function eventGiveaways(entries, range) {
    var evs = {};
    list(entries).forEach(function (e) {
      if (e.type !== "giveaway" || !inRange(e, range)) return;
      var k = norm(e.event);
      var ev = evs[k] || (evs[k] = { event: oneLine(e.event), first_date: e.date, last_date: e.date, total_qty: 0, count: 0, items: [], _it: {} });
      var q = qty(e);
      ev.total_qty += q; ev.count += 1;
      if (e.date < ev.first_date) ev.first_date = e.date;
      if (e.date > ev.last_date) ev.last_date = e.date;
      var ik = itemKey(e.item) + "|" + (e.format || "");
      var it = ev._it[ik] || (ev._it[ik] = { item: oneLine(e.item), format: e.format || "", qty: 0 });
      it.qty += q;
    });
    return Object.keys(evs).map(function (k) {
      var ev = evs[k];
      ev.items = Object.keys(ev._it).map(function (x) { return ev._it[x]; }).sort(function (a, b) { return b.qty - a.qty; });
      delete ev._it;
      return ev;
    }).sort(function (a, b) { return a.last_date < b.last_date ? 1 : a.last_date > b.last_date ? -1 : 0; });
  }

  /* Subscriptions that end between 30 days ago and `days` from today, soonest first. A subscription
     renewed since (a later one for the same person and product) is not listed. [{entry, sub_end, days_left}] */
  function renewals(entries, today, days) {
    days = Number(days) >= 0 ? Number(days) : 60;
    var latest = {};
    var subs = list(entries).filter(function (e) { return isMoney(e) && subEnd(e); });
    subs.forEach(function (e) {
      var k = norm(e.person) + "|" + (e.sub_product || "") + "|" + (e.person ? "" : e.sub_kind);
      if (!latest[k] || e.sub_start > latest[k].sub_start) latest[k] = e;
    });
    var out = [];
    Object.keys(latest).forEach(function (k) {
      var e = latest[k], end = subEnd(e), left = daysBetween(today, end);
      if (left !== null && left >= -30 && left <= days) out.push({ entry: e, sub_end: end, days_left: left });
    });
    return out.sort(function (a, b) { return a.days_left - b.days_left; });
  }

  /* Budgets: [{budget, from, to, used_cents, left_cents, pct, over}]. A budget has a funder (none:
     all my spending; "me": what I fund myself; another: what is charged to them, paid directly
     included), a year or from / to (none: this year) and optionally a category. */
  function budgets(entries, settings, today) {
    var S = isObj(settings) ? settings : {};
    var year = isISO(today) ? today.slice(0, 4) : todayISO().slice(0, 4);
    return arr(S.budgets).filter(isObj).map(function (b) {
      var from = isISO(b.from) ? b.from : "", to = isISO(b.to) ? b.to : "";
      if (!from && !to) { var y = /^\d{4}$/.test(str(b.year)) ? str(b.year) : year; from = y + "-01-01"; to = y + "-12-31"; }
      var used = 0;
      list(entries).forEach(function (e) {
        if (!isMoney(e) || !inRange(e, { from: from, to: to })) return;
        if (b.category && e.category !== b.category) return;
        var hit;
        if (!b.funder) hit = isSpent(e);
        else if (isSelf(S, b.funder)) hit = isSpent(e) && isSelfFunded(S, e);
        else hit = e.funder === b.funder && e.claim_status !== "denied" && e.repaid !== "forgiven";
        if (hit) used += Number(e.amount_cents) || 0;
      });
      var amount = Math.max(0, Math.round(Number(b.amount_cents) || 0));
      return { budget: b, from: from, to: to, used_cents: used, left_cents: amount - used, pct: amount > 0 ? Math.round(used * 100 / amount) : null, over: used > amount };
    });
  }

  /* Requests sent more than `days` (30) days ago and still not paid, oldest first: [{entry, days}] */
  function staleClaims(entries, today, days) {
    days = Number(days) >= 0 ? Number(days) : 30;
    var out = [];
    list(entries).forEach(function (e) {
      if (!isMoney(e) || e.claim_status !== "submitted") return;
      var age = daysBetween(isISO(e.claim_date) ? e.claim_date : e.date, today);
      if (age !== null && age > days) out.push({ entry: e, days: age });
    });
    return out.sort(function (a, b) { return b.days - a.days; });
  }

  /* ------------------------------------------------------------------ the list */
  function collator() {
    try { var c = new Intl.Collator(undefined, { sensitivity: "base", numeric: true }); return function (a, b) { return c.compare(str(a), str(b)); }; }
    catch (e) { return function (a, b) { a = norm(a); b = norm(b); return a < b ? -1 : a > b ? 1 : 0; }; }
  }
  function haystack(e, S) {
    var parts = [e.description, e.vendor, e.event, e.place, e.person, e.item, e.notes, e.claim_ref, e.receipt_ref, e.from, e.to, arr(e.tags).join(" ")];
    var c = catOf(S, e.category);
    if (c) parts.push(label(c.label, "en"), label(c.label, "es"));
    var f = funderOf(S, e.funder);
    if (f) parts.push(label(f.name, "en"), label(f.name, "es"));
    if (isObj(e.custom)) Object.keys(e.custom).forEach(function (k) { parts.push(str(e.custom[k])); });
    return norm(parts.join(" \u0001 "));
  }
  /* f: {q, types, categories, funders, statuses, event, tag, from, to, hasReceipt, format, example, ids}
     (a missing or empty filter lets everything through; q: every word must appear, accents and case
     ignored). settings is optional (with it, q also finds category and funder names). */
  function filterEntries(entries, f, settings) {
    f = isObj(f) ? f : {};
    var S = isObj(settings) ? settings : {};
    var words = norm(f.q).split(" ").filter(Boolean);
    var inList = function (v, l) { return !Array.isArray(l) || !l.length || l.indexOf(v) >= 0; };
    var ev = norm(f.event), tag = norm(f.tag);
    return list(entries).filter(function (e) {
      if (!inList(e.type, f.types) || !inList(e.category, f.categories) || !inList(e.funder, f.funders) || !inList(e.claim_status, f.statuses)) return false;
      if (!inList(e.id, f.ids) || (f.format && e.format !== f.format)) return false;
      if (!inRange(e, f)) return false;
      if (ev && norm(e.event) !== ev) return false;
      if (tag && !arr(e.tags).some(function (t) { return norm(t) === tag; })) return false;
      if (f.hasReceipt === true && (!e.receipt || e.receipt === "none")) return false;
      if (f.hasReceipt === false && e.receipt && e.receipt !== "none") return false;
      if (typeof f.example === "boolean" && !!e.example !== f.example) return false;
      if (words.length) {
        var hay = haystack(e, S);
        for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) < 0) return false;
      }
      return true;
    });
  }
  /* A sorted copy. key: date (default) · amount · signed · description · category · funder · status ·
     type · miles · vendor · event · created · updated; dir: "desc" (default) or "asc". Ties: newest first. */
  function sortEntries(entries, key, dir, settings) {
    var S = isObj(settings) ? settings : {};
    var coll = collator(), sign = dir === "asc" ? 1 : -1;
    var val = {
      amount: function (e) { return Number(e.amount_cents) || 0; },
      signed: function (e) { return signedCents(e); },
      miles: function (e) { return Number(e.miles) || 0; },
      category: function (e) { return categoryLabel(S, e.category, "en"); },
      funder: function (e) { return funderName(S, e.funder, "en"); },
      status: function (e) { return CLAIM.indexOf(e.claim_status); },
    }[key] || function (e) { return e[key === "status" ? "claim_status" : ["description", "vendor", "event", "type", "created", "updated"].indexOf(key) >= 0 ? key : "date"]; };
    var tie = function (a, b) { return (a.date < b.date ? 1 : a.date > b.date ? -1 : 0) || (a.created < b.created ? 1 : a.created > b.created ? -1 : 0) || (a.id < b.id ? 1 : a.id > b.id ? -1 : 0); };
    return list(entries).slice().sort(function (a, b) {
      var x = val(a), y = val(b), c;
      if (typeof x === "number" && typeof y === "number") c = x - y;
      else if (key === "date" || key === "created" || key === "updated" || !key) c = str(x) < str(y) ? -1 : str(x) > str(y) ? 1 : 0;
      else c = coll(x, y);
      return c * sign || tie(a, b);
    });
  }

  /* ------------------------------------------------------------------ reimbursement requests */
  // the page's strings, with or without the "expenses." prefix (src/_data/expenses.js drops it)
  function word(strings, key, fallback) {
    if (isObj(strings)) {
      if (typeof strings["expenses." + key] === "string") return strings["expenses." + key];
      if (typeof strings[key] === "string") return strings[key];
    }
    return fallback;
  }
  /* The lines to ask one funder for. opts: {funder, from, to, statuses (default ["to_request"]),
     includeNames (default false), lang, strings (the page's, for the words of a line without a
     name), ids (only these entries)}. People's names stay out unless includeNames: a line that
     names someone is described by what it is ("Magazine subscriptions · Gift · 12 months").
     → {header, lines, mileage, totals, ids} */
  function claimLines(entries, settings, opts) {
    var S = isObj(settings) ? settings : {};
    opts = opts || {};
    var lang = langOf(opts.lang), strings = opts.strings;
    var statuses = Array.isArray(opts.statuses) && opts.statuses.length ? opts.statuses : ["to_request"];
    var only = Array.isArray(opts.ids) ? opts.ids : null;
    var sel = list(entries).filter(function (e) {
      return isMoney(e) && e.method !== DIRECT && e.funder === opts.funder && statuses.indexOf(e.claim_status) >= 0 &&
        e.repaid !== "forgiven" && inRange(e, opts) && (!only || only.indexOf(e.id) >= 0);
    }).sort(byDate);
    var cats = {}, totals = { cents: 0, miles: 0, mileage_cents: 0, count: 0, receipts: 0, by_category: [] };
    var lines = [], mileage = [];
    sel.forEach(function (e) {
      var catLabel = categoryLabel(S, e.category, lang);
      var desc = e.description || e.item || catLabel;
      if (!opts.includeNames && e.person) {
        var term = Number(e.sub_term) > 0 ? fmt(word(strings, "claim.term", "{n} months"), { n: e.sub_term }) : "";
        desc = [catLabel, e.sub_kind ? word(strings, "sub_kind." + e.sub_kind, "") : "", e.sub_product ? word(strings, "sub_product." + e.sub_product, "") : "",
          term, e.sub_product ? "" : e.item].filter(Boolean).join(" · ");
      }
      var a = Number(e.amount_cents) || 0;
      var mil = e.type === "mileage";
      lines.push({ id: e.id, date: e.date, description: desc, category: catLabel, category_id: e.category, miles: mil ? e.miles : "", rate: mil ? e.rate : "",
        amount_cents: a, receipt: !!e.receipt && e.receipt !== "none", receipt_kind: e.receipt || "none", vendor: e.vendor, event: e.event, status: e.claim_status });
      if (mil) {
        mileage.push({ id: e.id, date: e.date, from: e.from, to: e.to, round_trip: e.round_trip, purpose: e.event || desc, miles: e.miles, rate: e.rate, amount_cents: a });
        totals.miles += Number(e.miles) || 0;
        totals.mileage_cents += a;
      }
      totals.cents += a;
      totals.count += 1;
      if (e.receipt && e.receipt !== "none") totals.receipts += 1;
      var c = cats[e.category] || (cats[e.category] = { id: e.category, label: catLabel, cents: 0, count: 0 });
      c.cents += a; c.count += 1;
    });
    totals.miles = Math.round(totals.miles * 10) / 10;
    totals.by_category = Object.keys(cats).map(function (k) { return cats[k]; }).sort(function (a, b) { return b.cents - a.cents; });
    var p = isObj(S.profile) ? S.profile : {};
    return {
      header: { funder: opts.funder || "", funder_name: funderName(S, opts.funder, lang), from: opts.from || "", to: opts.to || "", statuses: statuses,
        name: oneLine(p.name), position: oneLine(p.position), district: oneLine(p.district), email: oneLine(p.email), lang: lang, includeNames: !!opts.includeNames },
      lines: lines, mileage: mileage, totals: totals, ids: sel.map(function (e) { return e.id; }),
    };
  }

  /* A request as plain text (WhatsApp, e-mail). strings: the page's (keys in the notes of
     the core's report: claim.*); an English wording is used for any that is missing. */
  function claimText(claim, strings, lang) {
    if (!isObj(claim) || !isObj(claim.header)) return "";
    lang = langOf(lang || claim.header.lang);
    var h = claim.header, t = claim.totals || {}, out = [];
    var money = function (c) { return fmtMoney(c, lang); };
    out.push(word(strings, "claim.title", "Reimbursement request") + (h.funder_name ? " — " + h.funder_name : ""));
    var who = [h.name, h.position, h.district].filter(Boolean).join(" · ");
    if (who) out.push(fmt(word(strings, "claim.from", "From: {name}"), { name: who }));
    if (h.from || h.to) out.push(fmt(word(strings, "claim.period", "Period: {from} – {to}"), { from: h.from ? fmtDate(h.from, lang) : "…", to: h.to ? fmtDate(h.to, lang) : "…" }));
    out.push("");
    if (!arr(claim.lines).length) out.push(word(strings, "claim.none", "Nothing to ask for in this period."));
    arr(claim.lines).forEach(function (l) {
      var bits = [fmtDate(l.date, lang), l.description];
      if (l.miles !== "" && l.miles !== undefined && l.rate) bits.push(fmt(word(strings, "claim.miles_at", "{miles} mi × ${rate}"), { miles: l.miles, rate: l.rate }));
      bits.push(money(l.amount_cents));
      if (l.receipt) bits.push(word(strings, "claim.receipt", "receipt ✓"));
      out.push("• " + bits.filter(Boolean).join(" · "));
    });
    if (arr(claim.lines).length) {
      out.push("");
      if (t.miles) out.push(fmt(word(strings, "claim.total_miles", "Mileage: {miles} miles · {amount}"), { miles: t.miles, amount: money(t.mileage_cents) }));
      if (arr(t.by_category).length > 1) {
        out.push(word(strings, "claim.by_category", "By category:"));
        arr(t.by_category).forEach(function (c) { out.push("  " + c.label + ": " + money(c.cents)); });
      }
      out.push(fmt(word(strings, "claim.total", "Total: {amount} ({count} items)"), { amount: money(t.cents), count: t.count }));
      if (t.receipts) out.push(fmt(word(strings, "claim.receipts", "Receipts kept: {n} of {count}"), { n: t.receipts, count: t.count }));
    }
    return out.join("\n");
  }

  /* ------------------------------------------------------------------ CSV: writing */
  // a text cell that a spreadsheet would run as a formula gets a leading ' (see the top of the file)
  function guard(v) { return /^'*[=+\-@\t\r]/.test(v) ? "'" + v : v; }
  function unguard(v) { return /^'+[=+\-@\t\r]/.test(v) ? v.slice(1) : v; }
  function cell(v) { return /[",;\r\n\t]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
  function numText(n) { return n === "" || n === null || n === undefined || !isFinite(Number(n)) ? "" : String(Number(n)); }
  // "custom:<label>" per custom field (a label used twice: the later ones by id)
  function customColumns(S, lang) {
    var used = {};
    return arr(isObj(S) ? S.custom_fields : null).filter(function (f) { return isObj(f) && validId(str(f.id)); }).map(function (f) {
      var name = oneLine(label(f.label, lang)) || f.id;
      if (used[norm(name)]) name = f.id;
      used[norm(name)] = 1;
      return { field: f, header: "custom:" + name };
    });
  }
  /* entries → the CSV text (see "CSV CONTRACT" at the top). opts.lang: the language of
     category_label and funder_name ("en" by default). */
  function toCSV(entries, settings, opts) {
    var S = isObj(settings) ? settings : {};
    var lang = langOf(opts && opts.lang);
    var customs = customColumns(S, lang);
    var head = CSV_COLUMNS.concat(customs.map(function (c) { return c.header; }));
    var lines = [head.map(function (h) { return cell(guard(h)); }).join(",")];
    var catName = {}, funName = {};
    list(entries).forEach(function (e) {
      if (!has(catName, e.category)) catName[e.category] = e.category ? categoryLabel(S, e.category, lang) : "";
      if (!has(funName, e.funder)) funName[e.funder] = e.funder ? funderName(S, e.funder, lang) : "";
      var v = {
        id: e.id, date: e.date, end_date: e.end_date, type: e.type, category: e.category, category_label: catName[e.category],
        description: e.description, amount: centsText(e.amount_cents), signed_amount: centsText(signedCents(e)),
        funder: e.funder, funder_name: funName[e.funder], claim_status: e.claim_status, claim_date: e.claim_date, claim_ref: e.claim_ref,
        paid_date: e.paid_date, method: e.method, vendor: e.vendor, event: e.event, place: e.place, person: e.person, item: e.item,
        format: e.format, quantity: numText(e.quantity), unit_cost: e.unit_cost_cents === "" || e.unit_cost_cents === undefined ? "" : centsText(e.unit_cost_cents),
        giveaway: e.giveaway ? "yes" : "", miles: numText(e.miles), rate: str(e.rate), from: e.from, to: e.to, round_trip: e.round_trip ? "yes" : "",
        odometer_start: numText(e.odometer_start), odometer_end: numText(e.odometer_end), nights: numText(e.nights), attendees: numText(e.attendees),
        sub_product: e.sub_product, sub_term: numText(e.sub_term), sub_start: e.sub_start, sub_end: subEnd(e), sub_kind: e.sub_kind,
        repaid: e.repaid, receipt: e.receipt, receipt_ref: e.receipt_ref, tags: arr(e.tags).join("; "), notes: e.notes, created: e.created, updated: e.updated,
      };
      var row = CSV_COLUMNS.map(function (k) {
        var s = str(v[k]);
        return cell(CSV_NUMERIC[k] ? s : guard(s));
      });
      customs.forEach(function (c) {
        var x = isObj(e.custom) && has(e.custom, c.field.id) ? e.custom[c.field.id] : "";
        if (typeof x === "boolean") row.push(x ? "yes" : "no");
        else if (typeof x === "number") row.push(cell(numText(x)));
        else row.push(cell(guard(str(x))));
      });
      lines.push(row.join(","));
    });
    return "﻿" + lines.join("\r\n") + "\r\n";
  }

  /* ------------------------------------------------------------------ CSV: reading */
  // A file's bytes → text: UTF-8, or Windows-1252 when it is not valid UTF-8 (Excel's "CSV" on Windows).
  function decodeText(bytes) {
    try { return new TextDecoder("utf-8", { fatal: true }).decode(bytes); } catch (e) { /* not UTF-8 */ }
    try { return new TextDecoder("windows-1252").decode(bytes); } catch (e2) { return ""; }
  }
  // the delimiter of the header line: the most used of , ; TAB outside quotes (a tie: the comma)
  function detectDelimiter(text) {
    var count = { ",": 0, ";": 0, "\t": 0 }, q = false;
    for (var i = 0; i < text.length && i < 65536; i++) {
      var c = text.charAt(i);
      if (c === '"') q = !q;
      else if (!q && (c === "\n" || c === "\r")) break;
      else if (!q && has(count, c)) count[c] += 1;
    }
    return count[";"] > count[","] && count[";"] >= count["\t"] ? ";" : count["\t"] > count[","] ? "\t" : ",";
  }
  /* text → rows (arrays of strings). The array also carries .delimiter, and .error (a message key:
     too big / too many rows) or .unterminated (a quote never closed: read to the end). */
  function parseCSV(text, opts) {
    opts = opts || {};
    var rows = [];
    if (typeof text !== "string") {
      if (text && (text instanceof ArrayBuffer || ArrayBuffer.isView(text))) text = decodeText(text);
      else { rows.error = "expenses.err.empty"; return rows; }
    }
    if (text.length > LIMITS.bytes) { rows.error = "expenses.err.too_big"; return rows; }
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
    var delim = opts.delimiter;
    var sep = /^"?sep=([,;\t|])"?[ \t]*(\r\n|\n|\r|$)/i.exec(text);
    if (sep) { delim = delim || sep[1]; text = text.slice(sep[0].length); }
    if ([",", ";", "\t", "|"].indexOf(delim) < 0) delim = detectDelimiter(text);
    rows.delimiter = delim;
    var D = delim.charCodeAt(0), n = text.length, i = 0, row = [], max = LIMITS.rows + 1;
    var end = function () {
      for (var k = 0; k < row.length; k++) if (row[k] !== "" && row[k].trim() !== "") { rows.push(row); break; }
      row = [];
    };
    while (i < n) {
      var val, k;
      if (text.charCodeAt(i) === 34) {
        var j = i + 1, buf = "";
        for (;;) {
          var q = text.indexOf('"', j);
          if (q < 0) { buf += text.slice(j); i = n; rows.unterminated = true; break; }
          buf += text.slice(j, q);
          if (text.charCodeAt(q + 1) === 34) { buf += '"'; j = q + 2; continue; }
          i = q + 1;
          break;
        }
        // anything between the closing quote and the delimiter is kept (lenient, as spreadsheets are)
        k = i;
        while (k < n) { var ck = text.charCodeAt(k); if (ck === D || ck === 10 || ck === 13) break; k++; }
        val = k > i ? buf + text.slice(i, k) : buf;
        i = k;
      } else {
        k = i;
        while (k < n) { var c2 = text.charCodeAt(k); if (c2 === D || c2 === 10 || c2 === 13) break; k++; }
        val = text.slice(i, k);
        i = k;
      }
      row.push(val);
      if (i >= n) break;
      var c = text.charCodeAt(i);
      if (c === D) { i++; if (i >= n) row.push(""); continue; }
      i += c === 13 && text.charCodeAt(i + 1) === 10 ? 2 : 1;
      end();
      if (rows.length > max) { rows.error = "expenses.err.too_many_rows"; return rows; }
    }
    if (row.length) end();
    if (rows.length > max) rows.error = "expenses.err.too_many_rows";
    return rows;
  }

  /* ------------------------------------------------------------------ CSV: the import plan */
  function fingerprint(e) { return [e.type, e.date, e.amount_cents, norm(e.description)].join("|"); }
  // an entry as comparable text: every field in one order (custom keys sorted); `example` left out
  function canon(e) {
    var o = [];
    Object.keys(FIELDS).forEach(function (k) {
      if (k === "example") return;
      var v = e[k];
      if (k === "custom" && isObj(v)) { var c = {}; Object.keys(v).sort().forEach(function (x) { c[x] = v[x]; }); v = c; }
      o.push(v === undefined ? null : v);
    });
    return JSON.stringify(o);
  }
  function uniqueId(base, taken) {
    base = base && validId(base) ? base.slice(0, 40) : "x";
    var id = base, n = 2;
    while (taken(id)) id = base + "_" + n++;
    return id;
  }
  function labelMatch(item, text) {
    var t = norm(text);
    if (!t) return false;
    var l = has(item, "label") ? item.label : item.name;
    if (isObj(l)) return norm(l.en) === t || norm(l.es) === t;
    return norm(l) === t || norm(item.id) === t;
  }
  function problem(plan, rowNo, field, key, fatal) {
    (fatal ? plan.errors : plan.warnings).push({ row: rowNo, field: field, message_key: key });
  }

  /* rows (parseCSV) + the ledger → what an import would do; nothing is changed yet.
     opts: {decimal: "." | ",", dateOrder: "mdy" | "dmy", mapping (the answer to needsMapping:
     {date, description, amount, category, miles, notes, type, funder, vendor, event, place, person,
     item, tags, end_date, quantity} → a column number or header), allowDuplicates}.
     → {add, update, skip: [{row, reason, message_key, entry}], errors / warnings: [{row, field,
       message_key}], newCategories, newFunders, newCustomFields, needsMapping, headers, sample,
       all (every good row: what "replace" keeps), duplicates, format ("ours" | "mapped"),
       delimiter, decimal, dateOrder, rows}. `row` is the spreadsheet's row number (the header is 1).
     It never throws: an unreadable file is an error with a message key. */
  function planImport(rows, existing, settings, opts) {
    var plan = { add: [], update: [], skip: [], errors: [], warnings: [], newCategories: [], newFunders: [], newCustomFields: [],
      needsMapping: false, headers: [], sample: [], all: [], duplicates: [], format: "", delimiter: "", decimal: "", dateOrder: "", rows: 0 };
    try { planInner(plan, rows, existing, settings, opts || {}); }
    catch (err) {
      plan.add = []; plan.update = []; plan.all = []; plan.duplicates = [];
      plan.errors.push({ row: 0, field: "", message_key: "expenses.err.unreadable" });
    }
    return plan;
  }
  function planInner(plan, rows, existing, settings, opts) {
    var fail = function (key) { plan.errors.push({ row: 0, field: "", message_key: key }); };
    if (typeof rows === "string" || (rows && !Array.isArray(rows) && (rows instanceof ArrayBuffer || ArrayBuffer.isView(rows)))) rows = parseCSV(rows);
    if (!Array.isArray(rows)) return fail("expenses.err.unreadable");
    if (rows.error) return fail(rows.error);
    plan.delimiter = rows.delimiter || ",";
    var data = rows.filter(Array.isArray).map(function (r) { return r.map(str); });
    if (!data.length) return fail("expenses.err.empty");
    var header = data[0].map(function (h, i) { return (i ? h : h.replace(/^﻿/, "")).trim(); });
    var first = header.join(",");
    // a backup, a web page, a spreadsheet file or random bytes read as text
    if (/^[{[<]/.test(first) || /PK\u0003\u0004|[\u0000-\u0008\u000e-\u001f�]/.test(data.slice(0, 5).map(function (r) { return r.join(","); }).join("\n"))) {
      return fail(/gv-expenses-backup/.test(first) ? "expenses.err.looks_like_backup" : "expenses.err.not_csv");
    }
    if (data.length === 1) return fail("expenses.err.no_rows");
    if (data.length - 1 > LIMITS.rows) return fail("expenses.err.too_many_rows");
    plan.rows = data.length - 1;
    plan.headers = header;
    plan.decimal = opts.decimal === "," || opts.decimal === "." ? opts.decimal : plan.delimiter === ";" ? "," : ".";
    plan.dateOrder = opts.dateOrder === "dmy" ? "dmy" : "mdy";
    var hk = header.map(function (h) { return norm(h); });
    var hasCol = function (h) { return hk.indexOf(h) >= 0; };
    var ours = hasCol("date") && (hasCol("id") || (hasCol("type") && hasCol("amount")));
    if (!ours && !isObj(opts.mapping)) { plan.needsMapping = true; plan.sample = data.slice(1, 6); return; }

    // a copy of the settings: the plan adds its new categories / funders / fields here only
    var S = clone(isObj(settings) ? settings : {});
    ["categories", "funders", "methods", "rates", "custom_fields"].forEach(function (k) { S[k] = arr(S[k]).filter(isObj); });
    var old = list(existing);
    var byId = {};
    old.forEach(function (e) { if (e.id) byId[e.id] = e; });
    var fps = null;
    var num = { decimal: plan.decimal };
    var dateOpts = { dateOrder: plan.dateOrder, serial: true };

    var memo = {};
    var resolveCategory = function (idCell, labelCell, type, rowNo) {
      var mk = "c\u0001" + type + "\u0001" + idCell + "\u0001" + labelCell;
      if (has(memo, mk) && memo[mk].ok) return memo[mk].id;
      var id = unguard(idCell || "").trim(), lab = unguard(labelCell || "").trim();
      var c = id ? catOf(S, id) : null;
      if (c && c.type === type) return id;
      var mine = arr(S.categories).filter(function (x) { return x.type === type; });
      var hit = null;
      for (var i = 0; i < mine.length && !hit; i++) if (labelMatch(mine[i], lab) || (!lab && labelMatch(mine[i], id))) hit = mine[i];
      if (hit) { memo[mk] = { ok: true, id: hit.id }; return hit.id; }
      if (c) { problem(plan, rowNo, "category", "expenses.warn.category_type"); memo[mk] = { ok: false }; return ""; }
      if (!id && !lab) return "";
      var base = defaultCategory(S, type), like = catOf(S, base) || {};
      var nc = { id: validId(id) && id !== lab && !catOf(S, id) ? id : uniqueId("c_" + slug(lab || id), function (x) { return !!catOf(S, x); }), type: type,
        template: TYPE_TEMPLATE[type], label: lab || id, color: like.color || "slate", icon: like.icon || "", hidden: false,
        order: arr(S.categories).length, builtin: false };
      S.categories.push(nc);
      plan.newCategories.push(nc);
      memo[mk] = { ok: true, id: nc.id };
      return nc.id;
    };
    var resolveFunder = function (idCell, nameCell, kind) {
      var mk = "f\u0001" + idCell + "\u0001" + nameCell;
      if (has(memo, mk)) return memo[mk];
      var id = unguard(idCell || "").trim(), name = unguard(nameCell || "").trim();
      if (id && funderOf(S, id)) return (memo[mk] = id);
      var hit = null;
      arr(S.funders).forEach(function (f) { if (!hit && (labelMatch(f, name) || (!name && labelMatch(f, id)))) hit = f; });
      if (hit) return (memo[mk] = hit.id);
      if (!id && !name) return (memo[mk] = "");
      var nf = { id: validId(id) && id !== name ? id : uniqueId("f_" + slug(name || id), function (x) { return !!funderOf(S, x); }), kind: kind,
        name: name || id, hidden: false, order: arr(S.funders).length, builtin: false };
      S.funders.push(nf);
      plan.newFunders.push(nf);
      return (memo[mk] = nf.id);
    };

    // the custom:<label> columns
    var customCols = [];
    header.forEach(function (h, i) {
      var m = /^custom:(.*)$/i.exec(h);
      if (!m) return;
      var name = m[1].trim(), f = null;
      arr(S.custom_fields).forEach(function (x) { if (!f && isObj(x) && x.id === name) f = x; });
      arr(S.custom_fields).forEach(function (x) { if (!f && isObj(x) && (norm(label(x.label, "en")) === norm(name) || norm(label(x.label, "es")) === norm(name))) f = x; });
      if (!f && name) {
        f = { id: uniqueId("cf_" + slug(name), function (x) { return !!findById(S.custom_fields, x); }), label: name, type: "text", options: [], types: [] };
        S.custom_fields.push(f);
        plan.newCustomFields.push(f);
      }
      if (f) customCols.push({ index: i, field: f });
    });

    var col = {};
    hk.forEach(function (h, i) { if (!has(col, h)) col[h] = i; });
    var mapping = null;
    if (!ours) {
      // the visitor's answer: which column is what (a number, or a header's text)
      mapping = {};
      Object.keys(opts.mapping).forEach(function (k) {
        var v = opts.mapping[k], idx = typeof v === "number" ? v : /^\d+$/.test(str(v)) ? Number(v) : hk.indexOf(norm(v));
        if (idx >= 0 && idx < header.length) mapping[k] = idx;
      });
      if (!has(mapping, "date") || (!has(mapping, "amount") && !has(mapping, "miles"))) return fail("expenses.err.mapping_required");
      col = mapping;
    }
    plan.format = ours ? "ours" : "mapped";
    var anyNegative = false;
    if (!ours && has(col, "amount") && !has(col, "type")) {
      for (var t = 1; t < data.length && !anyNegative; t++) { var pm = parseMoney(data[t][col.amount], num); if (pm !== null && pm < 0) anyNegative = true; }
    }
    var rateOf = function (id) { var r = findById(S.rates, id); return r ? str(r.rate) : ""; };
    var seenIds = {};

    for (var r = 1; r < data.length; r++) {
      var cells = data[r], rowNo = r + 1;
      if (!cells.some(function (x) { return x.trim() !== ""; })) continue;
      var get = function (name) { return has(col, name) && col[name] < cells.length ? cells[col[name]] : undefined; };
      var text = function (name) { var v = get(name); return v === undefined ? undefined : unguard(v); };
      var raw = {}, fatal = false;
      var bad = function (field, key) { problem(plan, rowNo, field, key, true); fatal = true; };
      var soft = function (field, key) { problem(plan, rowNo, field, key, false); };

      // money first: without a type column the sign decides
      var amtCell = get("amount"), amount = null, signedCell = get("signed_amount");
      if (amtCell !== undefined && amtCell.trim() !== "") { amount = parseMoney(amtCell, num); if (amount === null) bad("amount", "expenses.err.amount"); }
      var signed = signedCell !== undefined && signedCell.trim() !== "" ? parseMoney(signedCell, num) : null;
      if (amount === null && signed !== null) amount = signed;
      if (amount !== null && Math.abs(amount) > LIMITS.cents) bad("amount", "expenses.err.amount_too_large");
      var milesCell = get("miles"), miles = milesCell !== undefined ? parseNumber(milesCell, num) : null;
      if (milesCell !== undefined && milesCell.trim() !== "" && miles === null) soft("miles", "expenses.warn.number_ignored");
      // a row of somebody else's sheet needs an amount (or miles)
      if (!ours && amount === null && !fatal && !(miles > 0)) bad("amount", "expenses.err.amount");

      var typeCell = get("type"), type = "";
      if (typeCell !== undefined && typeCell.trim() !== "") {
        type = enumOr(unguard(typeCell), TYPES) || "";
        if (!type) bad("type", "expenses.err.type");
      }
      if (!type) {
        var sign = signed !== null ? signed : amount;
        if (miles > 0 && (amount === null || amount === 0 || !has(col, "amount"))) type = "mileage";
        else if (sign !== null && sign < 0) type = "expense";
        else if (sign !== null && sign > 0 && (ours ? signed !== null : anyNegative)) type = "received";
        else type = "expense";
      }
      raw.type = type;

      var dcell = get("date");
      var date = dcell === undefined ? null : parseDate(dcell, dateOpts);
      if (!date) bad("date", dcell === undefined || !dcell.trim() ? "expenses.err.date_required" : "expenses.err.date");
      raw.date = date || "";
      if (fatal) { plan.skip.push({ row: rowNo, reason: "error", message_key: "expenses.warn.skip_error", entry: null }); continue; }

      raw.amount_cents = amount === null ? 0 : Math.abs(amount);
      if (miles !== null) raw.miles = Math.abs(miles);
      ["end_date", "claim_date", "paid_date", "sub_start"].forEach(function (k) {
        var v = get(k);
        if (v === undefined || !v.trim()) return;
        var d = parseDate(v, dateOpts);
        if (d) raw[k] = d; else soft(k, "expenses.warn.date_ignored");
      });
      ["quantity", "odometer_start", "odometer_end", "nights", "attendees", "sub_term"].forEach(function (k) {
        var v = get(k);
        if (v === undefined || !v.trim()) return;
        var n = parseNumber(v, num);
        if (n === null) soft(k, "expenses.warn.number_ignored"); else raw[k] = n;
      });
      var uc = get("unit_cost");
      if (uc !== undefined && uc.trim()) { var ucc = parseMoney(uc, num); if (ucc === null) soft("unit_cost", "expenses.warn.number_ignored"); else raw.unit_cost_cents = Math.abs(ucc); }
      var rt = get("rate");
      if (rt !== undefined && rt.trim()) {
        var rp = decParts(rt, num), mills = rp && !rp.neg ? scaled(rp, 3) : null;
        if (mills === null || mills > 99999) soft("rate", "expenses.warn.rate"); else raw.rate = String(mills / 1000);
      } else if (type === "mileage" && !ours) raw.rate = rateOf(S.defaults && S.defaults.rate) || rateOf(S.default_rate);
      ["giveaway", "round_trip"].forEach(function (k) { var v = get(k); if (v !== undefined) raw[k] = yes(v); });
      ["description", "claim_ref", "method", "vendor", "event", "place", "person", "item", "from", "to", "receipt_ref", "notes",
        "claim_status", "format", "sub_product", "sub_kind", "repaid", "receipt"].forEach(function (k) { var v = text(k); if (v !== undefined) raw[k] = v; });
      var tags = text("tags");
      if (tags !== undefined) raw.tags = tags;
      ["created", "updated"].forEach(function (k) { var v = get(k); if (v !== undefined && validStamp(v.trim())) raw[k] = v.trim(); });

      var idCell = get("id");
      var hadId = false;
      if (idCell !== undefined && idCell.trim()) {
        var idv = unguard(idCell).trim();
        if (validId(idv)) { raw.id = idv; hadId = true; } else soft("id", "expenses.warn.id_invalid");
      }
      raw.category = resolveCategory(get("category"), ours ? get("category_label") : get("category"), type, rowNo);
      var sk = enumOr(raw.sub_kind, SUB_KINDS);
      var fid = resolveFunder(get("funder"), ours ? get("funder_name") : get("funder"), sk === "helped" ? "person" : "other");
      if (fid) raw.funder = fid;
      if (!ours) {
        // the columns nobody mapped go into the notes ("Column: value")
        var used = {};
        Object.keys(col).forEach(function (k) { used[col[k]] = 1; });
        var extra = [];
        header.forEach(function (h, i) { if (!used[i] && str(cells[i]).trim()) extra.push((h || "#" + (i + 1)) + ": " + unguard(cells[i]).trim()); });
        if (extra.length) raw.notes = [raw.notes || ""].concat(extra).filter(Boolean).join("\n");
      }
      if (customCols.length) {
        raw.custom = {};
        customCols.forEach(function (c) {
          var v = cells[c.index];
          if (v === undefined || v === "") return;
          raw.custom[c.field.id] = c.field.type === "text" || !c.field.type ? unguard(v) : c.field.type === "yesno" ? yes(v) : c.field.type === "number" ? (parseNumber(v, num) === null ? unguard(v) : parseNumber(v, num)) : unguard(v);
        });
      }

      var res = normalizeEntry(raw, S);
      var entry = res.entry;
      res.problems.forEach(function (k) { soft("", k); });
      if (seenIds[entry.id]) { plan.skip.push({ row: rowNo, reason: "duplicate_id", message_key: "expenses.warn.skip_duplicate_id", entry: entry }); continue; }
      seenIds[entry.id] = 1;
      plan.all.push(entry);
      var prev = hadId ? byId[entry.id] : null;
      if (prev) {
        var p = normalizeEntry(prev, S).entry;
        if (canon(p) === canon(entry)) plan.skip.push({ row: rowNo, reason: "same", message_key: "expenses.warn.skip_same", entry: entry });
        else if ((Date.parse(entry.updated) || 0) > (Date.parse(prev.updated) || 0)) plan.update.push(entry);
        else plan.skip.push({ row: rowNo, reason: "older", message_key: "expenses.warn.skip_older", entry: entry });
      } else if (!hadId) {
        if (!fps) { fps = {}; old.forEach(function (e) { fps[fingerprint(e)] = 1; }); }
        if (fps[fingerprint(entry)] && !opts.allowDuplicates) {
          plan.skip.push({ row: rowNo, reason: "duplicate", message_key: "expenses.warn.skip_duplicate", entry: entry });
          plan.duplicates.push(entry);
        } else plan.add.push(entry);
      } else plan.add.push(entry);
    }
  }

  /* The plan carried out → a new state (the old one is not changed). mode "merge" (default): new
     entries added, newer ones replaced, the rest kept; includeDuplicates also adds the rows that
     looked like duplicates. mode "replace": the ledger becomes the file's rows. New categories,
     funders and custom fields are added to the settings either way. */
  function applyImport(state, plan, opts) {
    opts = opts || {};
    var st = isObj(state) ? state : {};
    var p = isObj(plan) ? plan : {};
    var settings = clone(isObj(st.settings) ? st.settings : {});
    [["categories", "newCategories"], ["funders", "newFunders"], ["custom_fields", "newCustomFields"]].forEach(function (pair) {
      settings[pair[0]] = arr(settings[pair[0]]);
      arr(p[pair[1]]).forEach(function (x) { if (isObj(x) && !findById(settings[pair[0]], x.id)) settings[pair[0]].push(clone(x)); });
    });
    var entries;
    if (opts.mode === "replace") entries = arr(p.all).map(clone);
    else {
      var upd = {};
      arr(p.update).forEach(function (e) { upd[e.id] = e; });
      entries = list(st.entries).map(function (e) { return upd[e.id] ? clone(upd[e.id]) : e; });
      var ids = {};
      entries.forEach(function (e) { ids[e.id] = 1; });
      arr(p.add).concat(opts.includeDuplicates ? arr(p.duplicates) : []).forEach(function (e) {
        var c = clone(e);
        if (ids[c.id]) c.id = newId();
        ids[c.id] = 1;
        entries.push(c);
      });
    }
    return { v: SCHEMA, entries: entries, settings: settings, meta: Object.assign({ lastBackup: null, lastExport: null, created: nowISO() }, isObj(st.meta) ? st.meta : {}, { lastImport: nowISO() }) };
  }

  /* ------------------------------------------------------------------ full backup */
  function cleanReceipts(list) {
    return arr(list).filter(function (r) { return isObj(r) && validId(str(r.id)) && /^data:image\/(jpeg|png|webp|gif)[;,]/i.test(str(r.dataUrl)); }).map(function (r) {
      var o = { id: r.id, type: str(r.type) || str(r.dataUrl).slice(5).split(/[;,]/)[0], dataUrl: r.dataUrl };
      ["name", "added"].forEach(function (k) { if (typeof r[k] === "string") o[k] = r[k]; });
      ["w", "h"].forEach(function (k) { if (typeof r[k] === "number" && isFinite(r[k])) o[k] = r[k]; });
      return o;
    });
  }
  // state (+ receipt photos as data: URLs, which the page reads from IndexedDB) → the backup's JSON text
  function toBackup(state, receipts) {
    var st = isObj(state) ? state : {};
    return JSON.stringify({ format: BACKUP_FORMAT, v: SCHEMA, app: VERSION, exported: nowISO(), entries: list(st.entries),
      settings: isObj(st.settings) ? st.settings : {}, meta: isObj(st.meta) ? st.meta : {}, receipts: cleanReceipts(receipts) });
  }
  /* A backup file's text (or the parsed object) → {ok: true, state, receipts, problems} or
     {ok: false, error: message key}. Also takes the stored state itself ({v, entries, settings}) and
     a plain list of entries (the first test version kept only that). Anything else is refused.
     configDefaults (optional): the site's defaults, merged into the backup's settings. */
  function readBackup(json, configDefaults) {
    var o = json;
    if (typeof json === "string") {
      if (json.length > LIMITS.bytes * 8) return { ok: false, error: "expenses.err.too_big" };
      try { o = JSON.parse(json.replace(/^﻿/, "")); } catch (e) { return { ok: false, error: "expenses.err.backup_invalid" }; }
    }
    var looksLikeEntries = function (a) { return a.length > 0 && a.every(function (x) { return isObj(x) && has(x, "date") && (has(x, "type") || has(x, "amount_cents") || has(x, "amount")); }); };
    if (Array.isArray(o)) {
      if (!looksLikeEntries(o)) return { ok: false, error: "expenses.err.backup_foreign" };
      o = { v: 0, entries: o };
    }
    if (!isObj(o)) return { ok: false, error: "expenses.err.backup_foreign" };
    if (has(o, "format")) { if (o.format !== BACKUP_FORMAT) return { ok: false, error: "expenses.err.backup_foreign" }; }
    else if (!(Array.isArray(o.entries) && (isObj(o.settings) || (has(o, "v") && (o.entries.length === 0 || looksLikeEntries(o.entries)))))) return { ok: false, error: "expenses.err.backup_foreign" };
    var v = has(o, "v") ? Number(o.v) : 0;
    if (!(v >= 0)) return { ok: false, error: "expenses.err.backup_invalid" };
    if (v > SCHEMA) return { ok: false, error: "expenses.err.backup_newer" };
    if (!Array.isArray(o.entries)) return { ok: false, error: "expenses.err.backup_invalid" };
    var problems = [];
    var state = migrate(o, configDefaults, problems);
    return { ok: true, state: state, receipts: cleanReceipts(o.receipts), problems: problems.length, exported: validStamp(o.exported) ? o.exported : null };
  }
  /* Any stored or backed-up state (an older version, a partial one) → the current shape. Entries
     are normalized (older field names: kind → type, amount in dollars → amount_cents, cat → category),
     ids made unique. configDefaults (optional) are merged into the settings. */
  function migrate(state, configDefaults, problems) {
    var o = Array.isArray(state) ? { entries: state } : isObj(state) ? state : {};
    problems = Array.isArray(problems) ? problems : [];
    var settings = configDefaults || !isObj(o.settings) ? mergeDefaults(configDefaults, isObj(o.settings) ? o.settings : null) : mergeDefaults(null, o.settings);
    var ids = {};
    var entries = list(o.entries).map(function (raw, i) {
      var r = Object.assign({}, raw);
      if (!has(r, "type") && has(r, "kind")) r.type = r.kind;
      if (!has(r, "category") && has(r, "cat")) r.category = r.cat;
      var res = normalizeEntry(r, settings);
      res.problems.forEach(function (k) { problems.push({ index: i, message_key: k }); });
      if (ids[res.entry.id]) res.entry.id = newId();
      ids[res.entry.id] = 1;
      return res.entry;
    });
    var m = isObj(o.meta) ? o.meta : {};
    return { v: SCHEMA, entries: entries, settings: settings,
      meta: Object.assign({}, m, { lastBackup: validStamp(m.lastBackup) ? m.lastBackup : null, lastExport: validStamp(m.lastExport) ? m.lastExport : null, created: validStamp(m.created) ? m.created : nowISO() }) };
  }

  /* ------------------------------------------------------------------ example entries */
  /* "Try with example entries": a small, realistic season of a GVR's service, dated back from today
     (first names only). One of each kind of entry: literature bought for the district table and to
     give away, a gift subscription (due for renewal soon) and one bought for someone who will pay it
     back, a hotel for the Assembly (request sent over a month ago), a meal, printing, parking,
     registration, a Seventh Tradition contribution, miles (typed, round trip, and by odometer),
     a reimbursement received, an advance from the group, back issues received from the Area and
     issues given away at two events. All marked example: true (one click removes them). */
  var EX = {
    books: ["Grapevine books for the district literature table", "Libros de Grapevine para la mesa de literatura del distrito"],
    best: ["The Best of Grapevine", "The Best of Grapevine"],
    bulk_gv: ["Grapevine issues to carry the message", "Revistas Grapevine para llevar el mensaje"],
    bulk_lv: ["La Viña issues to carry the message", "Revistas La Viña para llevar el mensaje"],
    issue_gv: ["Grapevine (this month's issue)", "Grapevine (edición del mes)"],
    issue_lv: ["La Viña (this issue)", "La Viña (edición actual)"],
    back_gv: ["Grapevine (back issues)", "Grapevine (ediciones anteriores)"],
    back_desc: ["Back issues from the Area literature table", "Ediciones anteriores de la mesa de literatura del Área"],
    gift: ["Gift subscription", "Suscripción de regalo"],
    helped: ["Subscription bought for a sponsee (paying me back)", "Suscripción comprada para un ahijado (me la va a pagar)"],
    hotel: ["Hotel for the Fall Assembly", "Hotel para la Asamblea de otoño"],
    meal: ["Pizza for the Grapevine workshop volunteers", "Pizza para los voluntarios del taller de Grapevine"],
    printing: ["GVR report copies for the district meeting", "Copias del informe del GVR para la reunión del distrito"],
    report: ["GVR report", "Informe del GVR"],
    parking: ["Parking at the Assembly", "Estacionamiento en la Asamblea"],
    registration: ["Fall Assembly registration", "Inscripción a la Asamblea de otoño"],
    seventh: ["Seventh Tradition at the district meeting", "Séptima Tradición en la reunión del distrito"],
    reimb: ["Area reimbursement for the Grapevine issues", "Reembolso del Área por las revistas Grapevine"],
    advance: ["Group advance for the workshop", "Adelanto del grupo para el taller"],
    home: ["Home", "Casa"],
    assembly: ["Fall Assembly, Tyler", "Asamblea de otoño, Tyler"],
    ev_assembly: ["Fall Assembly", "Asamblea de otoño"],
    ev_district: ["District 22 business meeting", "Reunión de servicio del Distrito 22"],
    ev_workshop: ["Grapevine & La Viña workshop", "Taller de Grapevine y La Viña"],
    store: ["aagrapevine.org store", "tienda de aagrapevine.org"],
    shop: ["Print shop", "Imprenta"],
    pizza: ["Pizza place", "Pizzería"],
    email: ["Hotel e-mail", "Correo del hotel"],
  };
  function exampleEntries(today, settings, lang) {
    var S = isObj(settings) ? settings : {};
    var li = langOf(lang) === "es" ? 1 : 0;
    var t = function (k) { return EX[k][li]; };
    var day = isISO(today) ? today : todayISO();
    var d = function (n) { return addDays(day, -n); };
    var cat = function (id, type) { var c = catOf(S, id); return c && c.type === type ? id : defaultCategory(S, type); };
    var fund = function (id) { return funderOf(S, id) ? id : SELF; };
    var person = arr(S.funders).filter(function (f) { return f && f.kind === "person" && !f.hidden; })[0];
    var rate = (function () {
      var ids = [S.defaults && S.defaults.rate, S.default_rate].concat(arr(S.rates).map(function (r) { return r.id; }));
      for (var i = 0; i < ids.length; i++) { var r = findById(S.rates, ids[i]); if (r && rateText(r.rate)) return rateText(r.rate); }
      return "0.14";
    })();
    var rows = [
      { type: "expense", date: d(12), category: cat("books", "expense"), description: t("books"), item: t("best"), format: "gv", quantity: 2, unit_cost_cents: 1200,
        amount_cents: 2400, funder: fund("district"), claim_status: "to_request", method: "card", vendor: t("store"), receipt: "paper" },
      { type: "expense", date: d(48), category: cat("giveaways", "expense"), description: t("bulk_gv"), item: t("issue_gv"), format: "gv", quantity: 20, unit_cost_cents: 250,
        amount_cents: 5000, giveaway: true, funder: fund("area"), claim_status: "paid", claim_date: d(45), claim_ref: "A65-14", paid_date: d(20), method: "card", vendor: t("store"), receipt: "paper" },
      { type: "expense", date: d(40), category: cat("giveaways", "expense"), description: t("bulk_lv"), item: t("issue_lv"), format: "lv", quantity: 10, unit_cost_cents: 250,
        amount_cents: 2500, giveaway: true, funder: SELF, method: "card", vendor: t("store"), receipt: "none" },
      { type: "expense", date: d(330), category: cat("subscriptions", "expense"), description: t("gift"), person: "Maria G.", sub_product: "gv_print", sub_term: 12,
        sub_start: d(328), sub_kind: "gift", amount_cents: 3600, funder: SELF, method: "card", vendor: t("store"), receipt: "file", receipt_ref: "aagrapevine.org" },
      { type: "expense", date: d(18), category: cat("subscriptions", "expense"), description: t("helped"), person: "José R.", sub_product: "lv_online", sub_term: 12,
        sub_start: d(18), sub_kind: "helped", repaid: "owed", amount_cents: 1500, funder: person ? person.id : SELF, method: "card", vendor: t("store"), receipt: "none" },
      { type: "expense", date: d(75), end_date: d(73), category: cat("lodging", "expense"), description: t("hotel"), vendor: "Hampton Inn", place: "Tyler", event: t("ev_assembly"),
        amount_cents: 23800, funder: fund("district"), claim_status: "submitted", claim_date: d(70), claim_ref: "D22-07", method: "card", receipt: "file", receipt_ref: t("email"), tags: ["assembly"] },
      { type: "expense", date: d(33), category: cat("meals", "expense"), description: t("meal"), attendees: 6, event: t("ev_workshop"), amount_cents: 4200,
        funder: fund("group"), claim_status: "to_request", method: "cash", vendor: t("pizza"), receipt: "paper" },
      { type: "expense", date: d(9), category: cat("printing", "expense"), description: t("printing"), item: t("report"), quantity: 30, amount_cents: 450,
        funder: fund("district"), claim_status: "to_request", method: "cash", vendor: t("shop"), receipt: "paper", event: t("ev_district") },
      { type: "expense", date: d(74), category: cat("travel", "expense"), description: t("parking"), event: t("ev_assembly"), amount_cents: 800, funder: SELF, method: "cash", receipt: "none", tags: ["assembly"] },
      { type: "expense", date: d(90), category: cat("registration", "expense"), description: t("registration"), event: t("ev_assembly"), amount_cents: 1500,
        funder: fund("district"), claim_status: "paid", claim_date: d(70), claim_ref: "D22-07", paid_date: d(50), method: "card", receipt: "file", receipt_ref: t("email"), tags: ["assembly"] },
      { type: "expense", date: d(9), category: cat("contributions", "expense"), description: t("seventh"), event: t("ev_district"), amount_cents: 500, funder: SELF, claim_status: "none", method: "cash", receipt: "none" },
      { type: "mileage", date: d(75), category: cat("mileage", "mileage"), from: t("home"), to: t("assembly"), round_trip: true, miles: 184.6, rate: rate,
        event: t("ev_assembly"), funder: fund("district"), claim_status: "submitted", claim_date: d(70), claim_ref: "D22-07", receipt: "none", tags: ["assembly"] },
      { type: "mileage", date: d(9), category: cat("mileage", "mileage"), from: t("home"), to: t("ev_district"), odometer_start: 42150, odometer_end: 42188, rate: rate,
        event: t("ev_district"), funder: SELF, receipt: "none" },
      { type: "received", date: d(20), category: cat("reimbursement", "received"), description: t("reimb"), amount_cents: 5000, funder: fund("area"), method: "check", claim_ref: "Check 1042" },
      { type: "received", date: d(35), category: cat("advance", "received"), description: t("advance"), amount_cents: 5000, funder: fund("group"), method: "cash", event: t("ev_workshop") },
      { type: "stock", date: d(60), category: cat("stock_in", "stock"), description: t("back_desc"), item: t("back_gv"), format: "gv", quantity: 15, funder: fund("area") },
      { type: "giveaway", date: d(74), category: cat("given", "giveaway"), description: t("ev_assembly"), item: t("issue_gv"), format: "gv", quantity: 12, event: t("ev_assembly") },
      { type: "giveaway", date: d(33), category: cat("given", "giveaway"), description: t("ev_workshop"), item: t("issue_lv"), format: "lv", quantity: 6, event: t("ev_workshop") },
      { type: "giveaway", date: d(33), category: cat("given", "giveaway"), description: t("ev_workshop"), item: t("back_gv"), format: "gv", quantity: 10, event: t("ev_workshop") },
    ];
    return rows.map(function (raw, i) {
      raw.example = true;
      raw.created = raw.updated = raw.date + "T18:00:" + pad2(i) + ".000Z";
      return normalizeEntry(raw, S).entry;
    });
  }

  /* ------------------------------------------------------------------ the module */
  root.GVX = {
    VERSION: VERSION, SCHEMA: SCHEMA, STORAGE_KEY: STORAGE_KEY, BACKUP_FORMAT: BACKUP_FORMAT, LIMITS: LIMITS,
    TYPES: TYPES, TEMPLATES: TEMPLATES, FUNDER_KINDS: FUNDER_KINDS, CLAIM: CLAIM, FORMATS: FORMATS, SUB_PRODUCTS: SUB_PRODUCTS,
    SUB_KINDS: SUB_KINDS, REPAID: REPAID, RECEIPT: RECEIPT, CUSTOM_TYPES: CUSTOM_TYPES, FIELDS: FIELDS, CSV_COLUMNS: CSV_COLUMNS,
    MESSAGE_KEYS: MESSAGE_KEYS, STRING_KEYS: STRING_KEYS,
    // model
    newId: newId, emptyState: emptyState, normalizeEntry: normalizeEntry, validateEntry: validateEntry,
    // money, dates, mileage
    mileageCents: mileageCents, tripMiles: tripMiles, rateText: rateText, parseMoney: parseMoney, parseNumber: parseNumber,
    fmtMoney: fmtMoney, centsText: centsText, parseDate: parseDate, fmtDate: fmtDate, addMonths: addMonths, addDays: addDays,
    daysBetween: daysBetween, todayISO: todayISO, isISO: isISO,
    // derived values and lookups
    signedCents: signedCents, subEnd: subEnd, isSpent: isSpent, isSelf: isSelf, label: label, itemLabel: itemLabel,
    categoryLabel: categoryLabel, funderName: funderName, defaultCategory: defaultCategory, templateOf: templateOf, norm: norm, fmt: fmt,
    // computations
    summary: summary, funderBalances: funderBalances, peopleOwed: peopleOwed, inventory: inventory, eventGiveaways: eventGiveaways,
    renewals: renewals, budgets: budgets, staleClaims: staleClaims, filterEntries: filterEntries, sortEntries: sortEntries,
    claimLines: claimLines, claimText: claimText,
    // CSV
    toCSV: toCSV, parseCSV: parseCSV, planImport: planImport, applyImport: applyImport, decodeText: decodeText, fingerprint: fingerprint,
    // backup and settings
    toBackup: toBackup, readBackup: readBackup, migrate: migrate, mergeDefaults: mergeDefaults,
    // examples
    exampleEntries: exampleEntries,
  };
})(typeof window !== "undefined" ? window : globalThis);
