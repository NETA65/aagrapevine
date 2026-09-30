/* "Install as an app" — which phone and browser this is, which guide on /offline/ (the steps of
   "Saved pages & app", src/pages/offline.njk) fits it, and whether the install notice may be offered
   now (src/assets/js/pwa.js).
   Pure functions, no DOM, no storage: pwa.js owns localStorage, the notice, the Aa panel's install
   row and the steps on /offline/; this file only knows about user-agent strings, a small record and
   clocks.
   Tested in Node by tests/test_pwa_install.py (the file runs in a vm context, as expenses-core.js
   and sw-core.js do). A plain script (no imports, ES2019): it defines window.GVInstall
   (globalThis.GVInstall in Node). Loaded by layouts/base.njk right before pwa.js; the service worker
   keeps it in its shell as an optional file — without it (a first offline visit) pwa.js makes every
   install control a plain link to the steps (/offline/#steps).

   DETECT — detect(ua, env) → { os, phone, browser, version, inApp, app, guide, variant, canInstall }
   env (all optional): touch = navigator.maxTouchPoints · small = the screen's short side < 600px ·
   telegram = Telegram's in-app browser globals are there · brave = navigator.brave exists.
   * iOS: iPhone / iPod / iPad in the user agent, or "Macintosh" with a touch screen (an iPad asks for
     desktop sites; on a small screen it is an iPhone in desktop-site mode). Android: "Android" —
     or Linux (not ChromeOS) with a touch screen, whatever its size: a phone or a tablet asking for
     desktop sites ("X11; Linux x86_64" — Chrome and Samsung Internet do that by default on the
     bigger Android tablets). A Linux laptop with a touch screen is taken for Android too: rare
     here, and its Chrome still offers one-tap install. phone = iOS or Android (tablets included);
     everything else is a computer (guide "computer", phone false).
   * Inside another app (phones only): the first app whose token the user agent carries — Messenger
     (FBAN/Messenger… on iPhone, FB_IAB/Orca-Android or FB_IAB/MESSENGER on Android) before
     Facebook, Threads before Instagram (their user agents carry both) — or Telegram, or a web
     view with no browser around it (Android "; wv)", a real iPhone / iPad user agent without
     "Safari/"): inApp true, app = its name ("" when unknown), guide "in-app", canInstall false.
     Those browsers can't install anything; /offline/#in-app explains how to open the page in the
     phone's browser. (Chrome Custom Tabs and Safari views opened from Gmail look exactly like Chrome
     and Safari: the iPhone and Android guides carry an "opened from Gmail?" tip instead.)
   * iPhone / iPad, other browsers (Chrome, Edge, Firefox, Opera, Yandex, DuckDuckGo): guide
     "iphone-other"; they can add to the home screen from iOS 16.4 (an unknown version counts as new).
   * iPhone / iPad, Safari: guide "iphone"; variant = which button leads to Share, from Safari's own
     Version/NN (Safari 26 froze the OS number at 18_x): "27" the Page Menu button, "26" the More
     button, "share" the Share button itself (Safari 18 and older, and every iPad), "" unknown (the
     page keeps the step that names them all).
   * Android: Samsung Internet → "samsung"; Firefox, Edge, Opera, Brave, Yandex, UC, Mi, Huawei,
     DuckDuckGo, Vivaldi and anything unknown → "android-other"; Chrome → "android". All can install.
   The platform words the guides use live in src/_i18n/pwa.json (pwa.app.*): re-check them every
   September (a new iOS) and after big Chrome releases, together with the tokens here.

   THE OFFER — offer(rec, ctx) → true when the install notice may show now. ctx: now (ms), phone,
   canInstall, inApp, installed (running as the app), knownInstalled (the app is on this device),
   prompt (the browser offers one-tap install), online, busy (another bar, panel or field is in use),
   page (non-empty on the offline page — the steps are there — and on a noindex page), dwell (ms
   visible on this page), touched (a tap, a key or a scroll on this page). Never on a computer,
   inside another app, in the app itself, offline, while something else is up, on those pages, or
   once it is known to be installed. Otherwise only after RULES.views page views
   (RULES.viewsWithPrompt when the browser offers one-tap install), RULES.dwell on the page and a
   first touch; then at most RULES.maxShows showings in all and RULES.maxNo "Not now"s, each followed
   by a quiet time.

   THE RECORD — localStorage "gvlv-app" = {v: 1, views, shown, no, quiet, app, done} (pwa.js reads
   and writes it; blocked storage means the notice is never offered, as a "Not now" could not be
   remembered). Numbers only: page views, times shown, "Not now"s; quiet = no notice before this
   time (ms); app = last time the site ran as the installed app (iOS home-screen apps have storage
   of their own, so this is only ever seen on Android and computers); done = installed from this
   browser (never offered again). A time further ahead than any rule sets (a clock set back, a
   damaged record) counts as unset. clean() never throws; the helpers return a new cleaned record:
     view(r)            one more page view
     shown(r, now)      the notice was shown: +1, quiet for RULES.quietAfterShow
     later(r, now)      "Not now" (or Escape): +1 no, quiet for RULES.quietAfterNo
     guided(r, now)     the steps were read ("Show me how", the Aa panel's "Install as an app", the
                        steps on /offline/ reached — not a look at the saved pages above them):
                        quiet for RULES.quietAfterNo
     opened(r, now)     the site runs as the installed app now
     done(r, now)       installed from this browser (appinstalled, or the prompt was accepted)
     notInstalled(r)    the browser offers one-tap install (beforeinstallprompt), which it only does
                        while the app is NOT installed — so it was removed: "installed" and "opened as
                        the app" are forgotten (the notice's counts and quiet times stay) */
(function (root) {
  "use strict";

  var DAY = 864e5;
  var RULES = {
    views: 3,               // page views before the notice (steps to follow: the third)
    viewsWithPrompt: 2,     // …when the browser offers one-tap install (the second)
    dwell: 20000,           // ms the page has been on screen
    quietAfterShow: 7 * DAY,
    quietAfterNo: 30 * DAY, // after "Not now" or "Show me how"
    maxShows: 4,
    maxNo: 2,
    installedFor: 90 * DAY, // opened as the app this recently: it is installed
  };

  // Another app's own browser (it can't install): the app's name when its user agent says so.
  // Order matters: Messenger before Facebook, Threads before Instagram.
  var APPS = [
    // (Orca = Messenger for Android, com.facebook.orca; MessengerLite = the old Lite app)
    ["Messenger", /FBAN\/Messenger|MessengerForiOS|MessengerLite|FB_IAB\/(MESSENGER|Orca-Android)|\bMessenger\b/],
    ["Threads", /\bBarcelona\b/],
    ["Instagram", /\bInstagram\b/],
    ["Facebook", /\bFBAN\/|\bFBAV\/|\bFB_IAB\/|\bFBIOS\b|\bFB4A\b|\bMetaIAB\b/],
    ["WhatsApp", /\b(WAiOS|WA4A)\//],
    ["TikTok", /musical_ly|Bytedance|\bTikTok\b/i],
    ["Snapchat", /\bSnapchat\b/],
    ["LinkedIn", /\bLinkedInApp\b/],
    ["X", /\bTwitter\b/],
    ["Pinterest", /\bPinterest\b/],
    ["Reddit", /\bReddit\//],
    ["LINE", /\bLine\//],
    ["WeChat", /\bMicroMessenger\//],
    ["Google", /\bGSA\//],
  ];
  // iPhone / iPad browsers other than Safari (Safari's user agent never names another browser;
  // "Chrome/" and "Edg/": Chrome and Edge on an iPad asking for desktop sites)
  var IOS_OTHER = /\b(CriOS|FxiOS|EdgiOS|OPiOS|OPT|YaBrowser|DuckDuckGo|Firefox|Chrome|Edg)\//;
  var IOS_NAMES = { CriOS: "chrome", Chrome: "chrome", FxiOS: "firefox", Firefox: "firefox", EdgiOS: "edge", Edg: "edge" };

  function num(m) { return m ? parseInt(m[1], 10) : 0; }

  function detect(ua, env) {
    ua = String(ua || "");
    env = env && typeof env === "object" ? env : {};
    var touch = Number(env.touch) || 0;
    var macTouch = /\bMacintosh\b/.test(ua) && touch > 1;
    // an iPhone asking for desktop sites says "Macintosh" too: its small screen tells them apart
    var ipad = /\biPad\b/.test(ua) || (macTouch && !env.small);
    var ios = ipad || macTouch || /\b(iPhone|iPod)\b/.test(ua);
    // …and an Android phone or tablet asking for desktop sites says "X11; Linux x86_64" (any screen size:
    // the bigger tablets do it by default)
    var android = !ios && (/\bAndroid\b/.test(ua) || (/\bLinux\b/.test(ua) && !/\bCrOS\b/.test(ua) && touch > 0));
    var r = {
      os: ios ? (ipad ? "ipados" : "ios") : android ? "android" : /\bMacintosh\b/.test(ua) ? "mac" : /\bWindows\b/.test(ua) ? "windows" : /\bCrOS\b/.test(ua) ? "chromeos" : /\bLinux\b/.test(ua) ? "linux" : "other",
      phone: ios || android, browser: "other", version: 0, inApp: false, app: "", guide: "computer", variant: "", canInstall: false,
    };
    var app = "";
    for (var i = 0; i < APPS.length; i++) if (APPS[i][1].test(ua)) { app = APPS[i][0]; break; }
    if (env.telegram) app = "Telegram";
    // a web view with no browser around it: Android "; wv)", or an iPhone user agent without "Safari/"
    // (only a real iPhone / iPad user agent: an iPad asking for desktop sites may be Firefox, with no "Safari/")
    var webview = android ? /;\s*wv\)/.test(ua) : /\b(iPhone|iPod|iPad)\b/.test(ua) && !/\bSafari\//.test(ua);
    if (r.phone && (app || webview)) { r.inApp = true; r.app = app; r.guide = "in-app"; r.browser = "in-app"; return r; }
    if (ios) {
      var other = IOS_OTHER.exec(ua);
      var osv = /\bOS (\d+)_(\d+)/.exec(ua), os = osv ? parseInt(osv[1], 10) + parseInt(osv[2], 10) / 100 : 0;
      if (other) {
        r.browser = IOS_NAMES[other[1]] || "other";
        r.guide = "iphone-other"; r.canInstall = !os || os >= 16.04; return r;
      }
      // Safari: from Safari 26 the user agent keeps the OS at 18_x, so Safari's own Version/NN decides
      r.browser = "safari"; r.version = num(/\bVersion\/(\d+)/.exec(ua)); r.guide = "iphone"; r.canInstall = true;
      r.variant = ipad ? "share" : r.version >= 27 ? "27" : r.version === 26 ? "26" : r.version ? "share" : "";
      return r;
    }
    if (android) {
      r.canInstall = true;
      if (/\bSamsungBrowser\//.test(ua)) { r.browser = "samsung"; r.version = num(/\bSamsungBrowser\/(\d+)/.exec(ua)); r.guide = "samsung"; }
      else if (/\bFirefox\//.test(ua)) { r.browser = "firefox"; r.guide = "android-other"; }
      else if (/\bEdgA\//.test(ua)) { r.browser = "edge"; r.guide = "android-other"; }
      else if (/\bOPR\//.test(ua)) { r.browser = "opera"; r.guide = "android-other"; }
      else if (env.brave) { r.browser = "brave"; r.guide = "android-other"; }
      else if (/\b(YaBrowser|UCBrowser|MiuiBrowser|HuaweiBrowser|DuckDuckGo|Vivaldi)\b/.test(ua)) { r.guide = "android-other"; }
      else if (/\bChrome\//.test(ua)) { r.browser = "chrome"; r.version = num(/\bChrome\/(\d+)/.exec(ua)); r.guide = "android"; }
      else r.guide = "android-other";
      return r;
    }
    if (/\bEdg\//.test(ua)) { r.browser = "edge"; r.canInstall = true; }
    else if (/\bFirefox\//.test(ua)) { r.browser = "firefox"; }
    else if (/\b(Chrome|Chromium)\//.test(ua)) { r.browser = "chrome"; r.canInstall = true; }
    else if (/\bSafari\//.test(ua) && r.os === "mac") { r.browser = "safari"; r.version = num(/\bVersion\/(\d+)/.exec(ua)); r.canInstall = r.version >= 17; }
    return r;
  }

  // Whole milliseconds / counts ≥ 0; anything else (text, NaN, negative, an object) is 0.
  function n(v) {
    try { v = Number(v); } catch (e) { return 0; }
    return isFinite(v) && v > 0 ? Math.floor(v) : 0;
  }
  function clean(rec) {
    var r = { v: 1, views: 0, shown: 0, no: 0, quiet: 0, app: 0, done: 0 };
    try {
      if (!rec || typeof rec !== "object" || Array.isArray(rec)) return r;
      r.views = n(rec.views); r.shown = n(rec.shown); r.no = n(rec.no);
      r.quiet = n(rec.quiet); r.app = n(rec.app); r.done = n(rec.done);
    } catch (e) { return { v: 1, views: 0, shown: 0, no: 0, quiet: 0, app: 0, done: 0 }; }
    return r;
  }

  function offer(rec, ctx) {
    var c = ctx && typeof ctx === "object" ? ctx : {};
    rec = clean(rec);
    var now = n(c.now);
    if (!c.phone || !c.canInstall || c.inApp || c.installed || !c.online || c.busy || c.page) return false;
    if (c.knownInstalled || rec.done) return false;
    // (a time further ahead than any rule sets — a clock set back, a damaged record — counts as unset)
    if (rec.app && rec.app <= now + DAY && now - rec.app < RULES.installedFor) return false;
    if (rec.no >= RULES.maxNo || rec.shown >= RULES.maxShows) return false;
    if (now < rec.quiet && rec.quiet - now <= RULES.quietAfterNo) return false;
    if (rec.views < (c.prompt ? RULES.viewsWithPrompt : RULES.views)) return false;
    return n(c.dwell) >= RULES.dwell && !!c.touched;
  }

  // A quiet time from now: never shortened, except one further ahead than any rule sets (damaged).
  function quiet(r, now, ms) {
    now = n(now);
    r.quiet = r.quiet - now > RULES.quietAfterNo ? now + ms : Math.max(r.quiet, now + ms);
    return r;
  }

  root.GVInstall = {
    RULES: RULES,
    detect: detect,
    clean: clean,
    offer: offer,
    view: function (r) { r = clean(r); r.views += 1; return r; },
    shown: function (r, now) { r = clean(r); r.shown += 1; return quiet(r, now, RULES.quietAfterShow); },
    later: function (r, now) { r = clean(r); r.no += 1; return quiet(r, now, RULES.quietAfterNo); },
    guided: function (r, now) { return quiet(clean(r), now, RULES.quietAfterNo); },
    opened: function (r, now) { r = clean(r); r.app = n(now); return r; },
    done: function (r, now) { r = clean(r); r.done = n(now) || 1; return r; },   // (no clock: still done)
    notInstalled: function (r) { r = clean(r); r.app = 0; r.done = 0; return r; },
  };
})(typeof window !== "undefined" ? window : globalThis);
