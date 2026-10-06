# content/archive: the magazines' archive files

The two files in this folder are exports of the Grapevine and La Viña online archives. Every update of the
website reads them and lists every story by a writer from Texas in **"Texas writers through the years"**, the
archive at the bottom of *Published writers* (`/published/#archive`, Spanish `/es/published/#archive`), Area 65
first. Only titles, the publishers' subtitles, themes, bylines as printed and links are shown — never a story's text.

## Name each file with the day it was exported

```text
aagrapevine_archive_2026-11-05.csv     Grapevine
aalavina_archive_2026-11-05.csv        La Viña
```

- The newest file of each magazine is used, by the **date in its name**. Write the day as `2026-11-05`
  (a date with the year last, such as `11-05-2026`, is read month first).
- An older copy left here is not used: the run summary names it ("may be deleted"). While a newer file waits to be
  fixed, the file used before stays in use, and the run summary says so ("it stays in use until … is fixed").
- Not used either: a name that does not start with the magazine (`Copy of …`), a name without `archive`, any file
  that is not a `.csv` — this README included. An export saved in another format under an archive name
  (`aagrapevine_archive_2026-11-05.xlsx`) is named in the run summary: save it again as **CSV UTF-8**.

## Replace a file

1. Put the new export here, named as above.
2. Delete the older file of the same magazine.
3. Commit and push (GitHub Desktop: **Commit to main**, then **Push origin**), or on github.com: **Add file →
   Upload files**, then delete the old file (**⋯ → Delete file**).

The push starts an update by itself: about 5 minutes later the archive is on the site (the run tests the code
before it publishes; later when the file brings many stories that are new to the site, as their titles are
translated first). The run summary
(*Actions → Website update →* the run) says `New archive file used: …`; a line **CSV file to fix** means the
file was not used (a missing column, or far fewer rows than the file before) and the older rows stay on the site.
A magazine you do not replace keeps its file. Keep the export as it was made (if you save it in Excel: **CSV UTF-8**).

Saving this README starts no *Website update* run (only the *Code check*).

The full guide — the columns, the checks, how Area 65 is decided, troubleshooting:
[how-to/writers-archive.md](../../how-to/writers-archive.md).
