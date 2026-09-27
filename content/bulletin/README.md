# The Bulletin

The committee's bulletin board: the **Bulletin** page under *Committee* on the site
(`/bulletin/`, in English and Spanish). Two ways to post (both are translated
EN ⇄ ES automatically):

1. **Google Drive (easiest):** put a Google Doc (or a `.txt`, `.md` or `.docx`
   file) in the `bulletin` folder inside the current Panel folder (`boletín`
   works too, and so does an older `announcements` / `anuncios` folder). The
   file name is the headline. Start the name with a date to control the date
   shown, e.g. `2027-01-10 Welcome new GVRs`. The document text is the body.
2. **GitHub:** add a Markdown file (ending in `.md`) to this folder, e.g.
   `2027-01-10-welcome-gvrs.md`. **[`_example.md`](_example.md) shows every
   option** — copy it, rename the copy (without the `_`) and edit it.

## The smallest post

A file needs nothing but text:

```markdown
# Welcome, new GVRs and RLVs!

Come to our committee meeting on the third Wednesday of the month.
```

- **Title:** the `title:` line of the header; without one, the first line when
  it is a heading (`# Welcome`), else the first `# ` heading, else the file
  name (`welcome-new-GVRs.md` → "Welcome new GVRs").
- **Date:** the `date:` line; without one, the date the file name starts with
  (`2027-01-10-…`), else the day the post first appears on the site.

## A header for more options

```markdown
---
title: Welcome, new GVRs and RLVs!
date: 2027-01-10
expires: 2027-03-31     # optional — hidden after this date
pinned: true            # optional — keep at the top
image: flyer.jpg        # optional — a picture for the post in lists
url: https://www.neta65.org   # optional — a "More information" button
title_es: "¡Bienvenidos, nuevos GVR y RLV!"   # optional — your own Spanish
summary_es: "Texto completo del aviso en español."
---
Write in English **or** Spanish. Links like [aagrapevine.org](https://www.aagrapevine.org) work.
```

If a value contains `: ` (like `title: Reminder: Assembly`), put it in quotes:
`title: "Reminder: Assembly"`.

**Your own translation (optional).** Add `title_es` and `summary_es` to a file
written in English (or `title_en` and `summary_en` to one written in Spanish)
and the other-language page shows your words instead of an automatic
translation, without the "auto-translated" note. `summary_es` replaces the whole
text below the header on the Spanish page, so write the complete text there.
Whatever you leave out is still translated automatically.

## What the text can hold

Headings (`#` to `####` — they come out under the post's title, in order),
lists (also inside lists), **bold**, *italic*, ~~crossed out~~, emoji, links
(web addresses, or our own pages like `/meetings/` — the Spanish page then links
to the Spanish version), `code`, quotations (`>`), tables (they scroll sideways
on a phone) and lines of `---`. A long web address wraps on a phone.

**HTML** pasted from an e-mail or a web page is turned into the same Markdown
(`<b>`, `<i>`, `<a href>`, `<br>`, `<img>`, headings, lists); other tags are
taken out and their text stays, and scripts, styles and embedded frames are
removed completely. Nothing in a post can run on the site. A picture that only
lived inside the e-mail (a signature logo, for one) shows as its description,
and the update's report names it; a link that is not a web, e-mail or phone
address keeps only its words.

## Pictures and documents

Save a picture (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`) or a document
(`.pdf`) **in this folder, next to the post**, and link to it by its name:

```markdown
![The Spring Assembly flyer](flyer.jpg)
[The sign-up form](<Sign-up form.pdf>)
```

(A name with spaces goes between `< >`.) The site publishes these files at
`/bulletin/files/` and points the links there; `image:` and `url:` in the
header can name them too. A link to a file that is not in the folder shows as
plain words, and the update's report (`status.json`) names the file. Keep files
small (a flyer photo under 1 MB), and never save anything private here —
everything in this folder is public. A picture already on Google Drive or the
web can be linked by its address instead.

Files whose name starts with `_` or `README` are ignored; any other file that is
not a post, a picture or a document is left out and reported.

This folder was called `content/announcements/` until September 2026. A post
saved there by habit still shows on the Bulletin, and the update's report asks
for it to be moved here.
