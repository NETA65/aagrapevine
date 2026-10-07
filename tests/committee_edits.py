"""Edits the committee makes to its own files — the kind content/**/README.md, the notes in config/ and the how-to
guides describe, and the slips a hand edit on github.com makes — applied to a COPY of the repository
(tests/test_automation.py, GateLists).

Website update's tests before publishing (scripts/ops/gate_tests.py) test the code. What the committee edits —
content/, config/, data/translations/glossary.yml and overrides.yml — and the documentation (README.md, docs/,
how-to/, the READMEs in content/ and config/) are left out of the tests' fingerprint, so an edit there never makes
them run again: a test of the gate that judged those files would fail only later, on somebody else's change of the
code, and stop every run from publishing until then. So with every edit below made, every test the gate runs must
still pass; the tests that judge the committee's files are left to the Code check (CONTENT_TESTS).

    copy_repository(ROOT, dest)          the files git knows (and new ones it does not ignore), node_modules linked
    apply_committee_edits(dest)          → what was done, one line each (an edit that finds nothing to change —
                                           the files changed since — is simply not listed)
    remove_copy(dest)

Standard library only.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


# ----------------------------------------------------------------------------------------------- the copy
def copy_repository(root: Path, dest: Path) -> None:
    """The working tree's files git knows, and the new ones it does not ignore, copied to `dest` (no .git: a test
    that needs a git checkout skips there); node_modules linked, not copied."""
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root,
                         capture_output=True, check=True, timeout=120).stdout
    for rel in filter(None, out.decode("utf-8").split("\0")):
        src = root / rel
        if src.is_file() and not src.is_symlink():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest / rel)
    modules = root / "node_modules"
    if modules.is_dir():
        if os.name == "nt":                        # a junction: no administrator's right needed, unlike a symlink
            import _winapi
            _winapi.CreateJunction(str(modules.resolve()), str(dest / "node_modules"))
        else:
            os.symlink(modules.resolve(), dest / "node_modules", target_is_directory=True)


def remove_copy(dest: Path) -> None:
    """Delete the copy — the node_modules link first, by itself (never what it points to)."""
    link = dest / "node_modules"
    if os.path.islink(link):
        os.unlink(link)
    elif link.exists():
        os.rmdir(link)                              # a junction: removes the link only
    shutil.rmtree(dest, ignore_errors=True)


# ----------------------------------------------------------------------------------------------- the edits
def _edit(path: Path, change) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    new = change(text)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8", newline="\n")
    return True


def _sub(pattern: str, repl, count: int = 0, flags: int = re.M):
    return lambda text: re.sub(pattern, repl, text, count=count, flags=flags)


def _dated(folder: Path) -> list[Path]:
    """The events / posts of a content folder: its dated .md files (not README.md, not "_example.md")."""
    return sorted(p for p in folder.glob("*.md") if re.match(r"\d{4}-\d{2}-\d{2}-", p.name)) if folder.is_dir() else []


def _later(m: re.Match) -> str:
    return m.group(1) + f"{(int(m.group(2)) + 1) % 24:02d}"


def apply_committee_edits(root: Path) -> list[str]:
    """Make the edits in the repository copy at `root` → what was done, one line each."""
    done: list[str] = []

    def did(ok: bool, what: str) -> None:
        if ok:
            done.append(what)

    # ------------------------------------------------------------------ content/events (content/events/README.md)
    events = root / "content" / "events"
    files = _dated(events)
    if files:                                                   # an event that is over: its file deleted
        files[0].unlink()
        did(True, f"content/events: {files[0].name} deleted")
    for p in _dated(events):
        name = f"content/events/{p.name}"
        did(_edit(p, _sub(r"^confirmed:.*\n", "")), f"{name}: the confirmed: line deleted (the event is over)")
        did(_edit(p, _sub(r"^# .*\n", "")), f"{name}: the notes (# lines) deleted")
        if _edit(p, _sub(r"^tentative:\s*true.*\n", "")):        # "when the details are final"
            _edit(p, _sub(r"^location_es:.*\n", ""))
            _edit(p, _sub(r"^location:.*$", 'location: "Tyler Civic Center, 1530 South Southwest Loop 323, Tyler, TX 75701"'))
            did(True, f"{name}: the venue announced")
        did(_edit(p, _sub(r'^(title(?:_es)?:\s*"?)(.+?)("?\s*)$', r"\1\2 (updated)\3")), f"{name}: the title changed")
        did(_edit(p, _sub(r"^(start:\s*\d{4}-\d{2}-\d{2}T)(\d{2})", _later)), f"{name}: it starts an hour later")
        did(_edit(p, _sub(r"^(end:\s*\d{4}-\d{2}-\d{2}T)(\d{2})", _later)), f"{name}: it ends an hour later")
    if events.is_dir():
        (events / "2027-02-13-gvr-workshop-tyler.md").write_text(
            '---\ntitle: "GVR Workshop — Tyler"\nstart: 2027-02-13T10:00:00-06:00\nend: 2027-02-13T12:00:00-06:00\n'
            'location: "Tyler, TX"\nurl: www.neta65.org/events\nonline_url: zoom.us/j/123456789\ntags: [workshop]\n'
            "lang: en\n---\nA new workshop.\n", encoding="utf-8", newline="\n")
        did(True, "content/events: a new event, its links written without https://")
        (events / "2026-11-14-open-house.md").write_text(
            '---\ntitle: "Open House"\nstart: "November 14 7:00 PM"\nlocation: "Tyler, TX"\n---\nx\n',
            encoding="utf-8", newline="\n")
        did(True, "content/events: a new event whose date has no year (a slip)")

    # ------------------------------------------------------------------ content/bulletin (content/bulletin/README.md)
    bulletin = root / "content" / "bulletin"
    for p in _dated(bulletin) + [bulletin / "_example.md"]:
        name = f"content/bulletin/{p.name}"
        did(_edit(p, _sub(r'^(title(?:_es)?:\s*"?)(.+?)("?\s*(?:#.*)?)$', r"\1Update: \2\3")), f"{name}: the title changed")
        did(_edit(p, _sub(r"^(date:\s*\d{4}-\d{2}-)(\d{2})", lambda m: m.group(1) + f"{max(1, int(m.group(2)) - 1):02d}")),
            f"{name}: the date changed")
        did(_edit(p, _sub(r"^(pinned:\s*)true", r"\1false")), f"{name}: no longer pinned")
    if bulletin.is_dir():
        (bulletin / "2026-12-01-holiday-meetings.md").write_text(
            '---\ntitle: "Holiday meetings"\ndate: 2026-12-01\nurl: www.neta65.org/events\nimage: www.neta65.org/x.jpg\n'
            "pinned: true\n---\nMeetings over the holidays.\n", encoding="utf-8", newline="\n")
        did(True, "content/bulletin: a new post, its links written without https://")

    # ------------------------------------------------------------------ content/booth, content/archive, instagram.yml
    booth = root / "content" / "booth" / "booth.csv"
    if booth.is_file():
        with booth.open("a", encoding="utf-8", newline="") as f:
            f.write("quiz-new-tag-row,yes,quiz,gv,brand-new-tag,,,,,,,A new question?,Yes|No,1,,Yes.,,,"
                    "¿Una pregunta nueva?,Sí|No,,Sí.,,,,,,,\n")
            f.write("bad row without its columns,maybe\n")
        did(True, "content/booth/booth.csv: a new row with a new tag, and a row with a mistake")
    archive = root / "content" / "archive"
    for old in sorted(archive.glob("*_archive_*.csv")) if archive.is_dir() else []:
        lines = old.read_text(encoding="utf-8-sig").splitlines()
        new = archive / re.sub(r"\d{4}-\d{2}-\d{2}", "2099-01-01", old.name)
        new.write_text("\n".join(ln.rsplit(",", 1)[0] for ln in lines[:3]) + "\n", encoding="utf-8")
        did(True, f"content/archive: {new.name}, a newer export with a column missing")
    did(_edit(root / "content" / "instagram.yml",
              _sub(r"^posts: \[\]", "posts:\n  - url: https://www.instagram.com/p/ABCdef12345/\n    account: gv")),
        "content/instagram.yml: a post added")

    # ------------------------------------------------------------------ config/site.yml (its own notes)
    site = root / "config" / "site.yml"
    for pattern, repl, count, what in (
            (r'^(  platform:\s*)"[^"]*"', r'\1"Microsoft Teams"', 1, "meeting.platform: another platform"),
            (r'^(  note:\s*)"[^"]*"', r'\1"Everyone is welcome."', 1, "meeting.note"),
            (r'^(  note_es:\s*)"[^"]*"', r'\1"Todos son bienvenidos."', 1, "meeting.note_es"),
            (r'^(  start:\s*)"19:00"', r'\1"18:30"', 1, "meeting.start"),
            (r'^(  morning_goal:\s*)"[^"]*"', r'\1"06:00"', 1, "site.morning_goal"),
            (r"^  (?:listen|watch):\n(?:    .*\n)+", "", 0, "the /listen/ and /watch/ videos deleted (to hide them)"),
            (r'^(    title_es:\s*)"Taller Mensual y Virtual de La Viña"', r'\1"Taller Mensual de La Viña"', 1,
             "La Viña's workshop renamed"),
            (r'^(    record_story:\s*)"[^"]*"', r'\1"/graba-tu-historia-nueva"', 1, "sources.lavina.record_story"),
            (r'^(    themes_page:\s*)"[^"]*"', r'\1"/recursos-nuevos"', 1, "sources.lavina.themes_page"),
            (r"^(    minutes_per_run:\s*)\d+", r"\g<1>25", 1, "sources.crawler.minutes_per_run"),
            (r"^(    keep_per_account:\s*)\d+", r"\g<1>100", 1, "sources.instagram.keep_per_account"),
            (r'^(  area_label: \{ en: )"[^"]*"', r'\1"Our Area"', 1, "meetings.area_label"),
            (r"^(    - )Wichita$", r"\1Wichta", 1, "a county misspelled in spotlight.neta65_counties"),
            (r"^(  highlights:\s*)\d+", r"\g<1>4", 1, "digest.highlights"),
            (r"^(  numbers:\n)", '\\1    - number: "+52 55 8659 9002"\n      city: "Mexico City"\n', 1,
             "phone_access: a number abroad"),
            (r"^(links:\n)", '\\1  committee_flyers: "https://example.org/flyers"\n  gv_store_es: "https://example.org/tienda"\n',
             1, "links: a new link nobody reads yet, and a Spanish twin no page shows yet"),
            (r"^  lv_apps:.*\n", "", 1, "links.lv_apps deleted, a link a page reads (a slip)"),
            (r"^(price_changes:\n)", '\\1  - key: "2028-01"\n    effective: "someday"\n', 1, "a price change with a mistake")):
        did(_edit(site, _sub(pattern, repl, count=count)), f"config/site.yml: {what}")

    # ------------------------------------------------------------------ the other settings files
    for p in sorted((root / "config").rglob("*.yml")):
        if p.name != "site.yml":                    # some English and Spanish texts reworded
            did(_edit(p, _sub(r'^(\s+(?:en|es):\s+)"([^"\n]+)"', r'\1"\2 (updated)"', count=3)),
                f"{p.relative_to(root).as_posix()}: texts reworded")
    did(_edit(root / "config" / "history.yml", lambda t: t.rstrip("\n") + (
        '\n\n  - year: "2026"\n    type: both\n    title:\n      en: "A new milestone"\n      es: "Un nuevo hito"\n'
        '    desc:\n      en: "Something that happened."\n      es: "Algo que pasó."\n')),
        "config/history.yml: a milestone added")
    did(_edit(root / "config" / "expenses.yml", _sub(
        r"^(  - id: other\n    type: expense\n(?:    .*\n)+)",
        r"\1  - id: banners\n    type: expense\n    template: general\n    icon: shapes\n    color: slate\n"
        r'    label: { en: "Banners", es: "Pancartas" }' "\n", count=1)),
        "config/expenses.yml: a category added")

    # ------------------------------------------------------------------ the translations the committee writes
    tr = root / "data" / "translations"
    did(_edit(tr / "glossary.yml", lambda t: t + '\nkeep:\n  - { en: "sponsee", es: "ahijado"\n'),
        "data/translations/glossary.yml: a line with a mistake (the file cannot be read)")
    did(_edit(tr / "overrides.yml", lambda t: t + '\n"The Joy of Living": { es: "La alegría de vivir"\n'),
        "data/translations/overrides.yml: a line with a mistake (the file cannot be read)")

    # ------------------------------------------------------------------ the documentation
    for doc in sorted([*root.glob("*.md"), *(root / "content").rglob("README.md"), *(root / "config").rglob("README.md")]):
        doc.unlink()
        did(True, f"{doc.relative_to(root).as_posix()} deleted")
    for folder in ("docs", "how-to"):
        if (root / folder).is_dir():
            shutil.rmtree(root / folder)
            did(True, f"{folder}/ deleted")
    return done
