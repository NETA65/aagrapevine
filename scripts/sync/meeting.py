"""Monthly date rules: "the Nth <weekday> of every month, HH:MM–HH:MM" in the site's time zone.

One rule engine (upcoming_rule_dates) serves both
  * the committee meeting — config/site.yml `meeting:` (e.g. 3rd Wednesday 19:00–20:00 Central), and
  * every entry of `recurring_events:` (e.g. the GV/LV booth at CityWide Dallas, 2nd Saturday
    17:30–19:30, or our Grapevine Meeting, 1st Wednesday) — see build_data.recurring_events().

Dates are counted on the local calendar and each start/end is turned into a real instant with the
time zone's own rules, so a daylight-saving change (or a month / year boundary) never moves an
event by an hour: 17:00 Central is 22:00 UTC in October (CDT) and 23:00 UTC in November (CST).
An event that runs past midnight keeps its real end on the next day ("22:00"–"01:00" ends at 1 AM
the next morning) — MonthlyRule.span says when an earlier end counts as the next day. A rule with a
first date (`starts:` — the Grapevine Meeting's is 2026-12-02) has no date before it, not even among
the past days a caller asks for.

The committee meeting's guest speakers (`meeting: speakers:`) are read here too (meeting_speakers),
with the same checks as the web pages (eleventy/filters/committee.js meetingSpeakers).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .common import load_config, to_iso

WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
            "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2, "jueves": 3, "viernes": 4, "sabado": 5,
            "sábado": 5, "domingo": 6}
# "week_of_month" written as a word: second / 2nd / segundo / 2.º / last / último …
_ORDINAL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "last": -1,
                  "primer": 1, "primero": 1, "primera": 1, "segundo": 2, "segunda": 2, "tercer": 3, "tercero": 3,
                  "tercera": 3, "cuarto": 4, "cuarta": 4, "quinto": 5, "quinta": 5, "ultimo": -1, "último": -1,
                  "ultima": -1, "última": -1}


def parse_hhmm(v, default: tuple[int, int]) -> tuple[int, int]:
    """A time from config/site.yml → (hour, minute); `default` when it cannot be understood.

    The file is edited by hand, so accept every way a time can arrive:
      "19:00" / "7:00 PM" / "7pm" / 19 (hour only) — and an UNQUOTED 19:00, which the YAML reader
      turns into the number 1140 (minutes, base 60)."""
    if isinstance(v, bool) or v is None or v == "":
        return default
    if isinstance(v, float):
        v = f"{v:.2f}"                     # unquoted 19.30 → "19.30"
    if isinstance(v, int):
        if 0 <= v <= 23:                   # "start: 19" → 19:00
            return v, 0
        if v >= 24 * 60:                   # unquoted 19:00:00 → 68400 (seconds)
            h, m = v // 3600, v % 3600 // 60
        else:                              # unquoted 19:00 → 1140 (minutes)
            h, m = divmod(v, 60)
        return (h, m) if 0 <= h <= 23 and 0 <= m <= 59 else default
    m = re.fullmatch(r"\s*(\d{1,2})(?:[:.h](\d{2})(?::\d{2})?)?\s*(?:([ap])\.?\s*m\.?)?\s*", str(v), re.I)
    if not m:
        return default
    h, mi = int(m[1]), int(m[2] or 0)
    if m[3]:
        if not 1 <= h <= 12:
            return default
        h = h % 12 + (12 if m[3].lower() == "p" else 0)
    return (h, mi) if 0 <= h <= 23 and 0 <= mi <= 59 else default


def weekday_index(v: Any) -> int | None:
    """'saturday' / 'Saturday' / 'Saturdays' / 'sábado' / 'Sábados' → 5 (Monday = 0); None if not understood."""
    s = str(v or "").strip().lower().rstrip(".")
    if s in WEEKDAYS:
        return WEEKDAYS[s]
    if s.endswith("s") and s[:-1] in WEEKDAYS:        # plural: "saturdays", "sábados"
        return WEEKDAYS[s[:-1]]
    return None


def week_of_month_value(v: Any) -> int | None:
    """1–5, or -1 for "the last one" — from 2, "2", "2nd", "second", "segundo", "2.º", "last", "último".
    None when it cannot be understood."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v if v in (1, 2, 3, 4, 5, -1) else None
    s = str(v).strip().lower()
    if s in _ORDINAL_WORDS:
        return _ORDINAL_WORDS[s]
    m = re.fullmatch(r"(-?\d)\s*(?:st|nd|rd|th|\.?\s*[ºoª°]|\.?\s*er|\.?\s*ra)?", s)
    if m and int(m[1]) in (1, 2, 3, 4, 5, -1):
        return int(m[1])
    return None


def ymd_text(v: Any) -> str | None:
    """A skip date from the settings → "YYYY-MM-DD" (YAML turns an unquoted 2027-01-09 into a date)."""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v or "").strip()
    try:
        return date.fromisoformat(s).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None
    except ValueError:                     # "2027-02-30"
        return None


# An end earlier than the start is the next morning when the event then lasts at most this long ("22:00" to
# "01:00": 3 hours). Further back it is a slip of the pen ("19:00" to "08:00" is not a 13-hour meeting).
OVERNIGHT_MAX_HOURS = 12


def overnight(start: tuple[int, int], end: tuple[int, int], max_hours: float = OVERNIGHT_MAX_HOURS) -> bool:
    """True when `end`, earlier on the clock than `start`, is the next morning: "22:00"–"01:00" → True,
    "19:00"–"08:00" (13 hours) → False, "19:00"–"20:00" → False (the same day)."""
    (sh, sm), (eh, em) = start, end
    if (eh, em) >= (sh, sm):
        return False
    return (24 * 60 - (sh * 60 + sm)) + (eh * 60 + em) <= max_hours * 60


@dataclass(frozen=True)
class MonthlyRule:
    """The Nth weekday of every month, from `start` to `end` (local wall-clock time)."""
    week_of_month: int                     # 1–5, or -1 = the last one of the month
    weekday: int                           # 0 = Monday … 6 = Sunday
    start: tuple[int, int]                 # (hour, minute)
    end: tuple[int, int]                   # (hour, minute); earlier than start → next day (see span)
    skip: frozenset[str] = frozenset()     # "YYYY-MM-DD" dates that do not happen
    starts: str | None = None              # "YYYY-MM-DD": the first date (none before it); None: no first date

    def span(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """(start, end) as used for every date. An end earlier than the start is the next morning when the
        event then lasts at most OVERNIGHT_MAX_HOURS ("22:00"–"01:00" ends at 1 AM the next day:
        ends_next_day). An end that is missing, equal to the start or further back ("19:00"–"08:00") makes
        it a one-hour event (a 23:30 start then ends at 23:59, the same day)."""
        (sh, sm), (eh, em) = self.start, self.end
        if (eh, em) <= (sh, sm) and not overnight(self.start, self.end):
            eh, em = min(sh + 1, 23), (sm if sh < 23 else 59)
        return (sh, sm), (eh, em)

    def ends_next_day(self) -> bool:
        """The end (span) is on the day after the start: the event runs past midnight."""
        start, end = self.span()
        return end < start


def nth_weekday(y: int, m: int, weekday: int, n: int) -> date | None:
    """The `n`th `weekday` (0 = Monday) of month `m` of year `y` (n = -1: the last one); None when the
    month has no such day (a 5th Saturday)."""
    if n == -1:
        last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
        return last - timedelta(days=(last.weekday() - weekday) % 7)
    first = date(y, m, 1)
    d = first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    return d if d.month == m else None


ORD_SHORT = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", -1: "last"}        # (settings messages)
DAY_NAMES_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def check_skip_dates(values: Any, weekday: int, week_of_month: int) -> tuple[set[str], list[str]]:
    """`skip_dates` from the settings (the committee meeting's or a recurring event's) → (the dates that
    really are one of the rule's days, notes for the chair). A value that is not a date, or not the rule's
    day of its month (the Sunday, the 1st Saturday, the wrong month …), would skip nothing: it is ignored
    and a note says which date to use instead."""
    ok: set[str] = set()
    notes: list[str] = []
    for s in values if isinstance(values, (list, tuple)) else [] if values in (None, "") else [values]:
        ymd = ymd_text(s)
        if not ymd:
            notes.append(f"skip date “{s}” is not a date like \"2027-01-09\" — ignored")
            continue
        d = date.fromisoformat(ymd)
        day = nth_weekday(d.year, d.month, weekday, week_of_month)
        if day != d:
            nth = f"{ORD_SHORT[week_of_month]} {DAY_NAMES_EN[weekday]}"
            notes.append(f"skip date “{ymd}” is not the {nth} of its month — ignored ("
                         + (f"that month's is {day.isoformat()})" if day else f"that month has no {nth})"))
            continue
        ok.add(ymd)
    return ok, notes


def check_starts(value: Any, weekday: int, week_of_month: int) -> tuple[str | None, list[str]]:
    """`starts` from the settings (the first date of a recurring event) → (the date, notes for the chair). No date
    of the rule comes before it. A value that is not a date is ignored (and noted); a date that is not one of the
    rule's days still counts — the rule's first day after it is the first date — and a note says which one."""
    if value in (None, ""):
        return None, []
    ymd = ymd_text(value)
    if not ymd:
        return None, [f"starts “{value}” is not a date like \"2026-12-02\" — ignored"]
    d = date.fromisoformat(ymd)
    y, m, day = d.year, d.month, None
    for _ in range(14):                    # the rule's first day on or after it (a "5th Saturday" may wait)
        day = nth_weekday(y, m, weekday, week_of_month)
        if day and day >= d:
            break
        y, m, day = (y, m + 1, None) if m < 12 else (y + 1, 1, None)
    if day == d:
        return ymd, []
    nth = f"{ORD_SHORT[week_of_month]} {DAY_NAMES_EN[weekday]}"
    return ymd, [f"starts “{ymd}” is not the {nth} of its month — the first date is "
                 + (f"{day.isoformat()} (the rule's next day)" if day else "none")]


def upcoming_rule_dates(rule: MonthlyRule, count: int, tz: ZoneInfo, now: datetime | None = None,
                        include_recent_days: int = 0, horizon_months: int | None = None) -> list[dict]:
    """The next `count` dates of a monthly rule that are not over yet (end ≥ now − include_recent_days),
    soonest first: [{"ymd": "2026-10-10", "start": "2026-10-10T22:00:00Z", "end": "2026-10-11T01:00:00Z"}].
    "ymd" is the day it starts; an overnight rule ends on the next day (MonthlyRule.span).

    Months are walked on the LOCAL calendar starting with the month before `now` (so an evening event on
    the last day of a month is still found while it is running, even though it is already the next month
    in UTC), for at most `horizon_months` months (default count + 15: a "5th Saturday" rule simply lists
    the months that have one). A date in `rule.skip`, or before `rule.starts`, is left out and does not count."""
    if count <= 0:
        return []
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=include_recent_days)
    (sh, sm), (eh, em) = rule.span()       # a missing end → one hour; an overnight one → the next day
    next_day = rule.ends_next_day()
    local = since.astimezone(tz)
    y, m = (local.year, local.month - 1) if local.month > 1 else (local.year - 1, 12)
    out: list[dict] = []
    for _ in range(horizon_months if horizon_months is not None else count + 15):
        d = nth_weekday(y, m, rule.weekday, rule.week_of_month)
        if d and d.isoformat() not in rule.skip and not (rule.starts and d.isoformat() < rule.starts):
            start = datetime(d.year, d.month, d.day, sh, sm, tzinfo=tz)
            e = d + timedelta(days=1) if next_day else d          # the wall clock of that day (DST-safe)
            end = datetime(e.year, e.month, e.day, eh, em, tzinfo=tz)
            if end.astimezone(timezone.utc) >= since:
                out.append({"ymd": d.isoformat(), "start": to_iso(start), "end": to_iso(end)})
                if len(out) >= count:
                    break
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def meeting_rule(cfg: dict | None) -> MonthlyRule:
    """config/site.yml `meeting:` → its rule. Tolerant on purpose (the committee meeting must always
    show): anything that cannot be understood falls back to the 3rd Wednesday, 19:00–20:00.
    (The weekday lookup is deliberately NOT weekday_index(): the web pages compute the same meetings
    themselves — eleventy/filters/committee.js meetingDates() — and a more forgiving reading here, e.g.
    of "Wednesdays", would make the two disagree about the day.)"""
    cfg = cfg or {}
    wd = WEEKDAYS.get(str(cfg.get("weekday", "wednesday")).strip().lower(), 2)
    try:
        n = int(cfg.get("week_of_month", 3))
    except (TypeError, ValueError):
        n = 3
    if n not in (1, 2, 3, 4, 5, -1):
        n = 3
    sh, sm = parse_hhmm(cfg.get("start"), (19, 0))
    # no end: one hour, never past midnight (a 23:30 start ends at 23:59, as the web pages show it)
    eh, em = parse_hhmm(cfg.get("end"), (sh + 1, sm) if sh < 23 else (23, 59))
    # Only real meeting days are skipped; anything else is ignored (meeting_skip_notes() tells the chair).
    skip, _notes = check_skip_dates(cfg.get("skip_dates"), wd, n)
    return MonthlyRule(week_of_month=n, weekday=wd, start=(sh, sm), end=(eh, em), skip=frozenset(skip),
                       starts=ymd_text(cfg.get("starts")))


def meeting_skip_notes(cfg: dict | None) -> list[str]:
    """Notes about config/site.yml `meeting: skip_dates` — the same check as a recurring event's skip dates
    (build_data puts them in status.json problems.meeting → the Actions run summary)."""
    rule = meeting_rule(cfg)
    return check_skip_dates((cfg or {}).get("skip_dates"), rule.weekday, rule.week_of_month)[1]


# --------------------------------------------------------------------------- guest speakers
# A speaker's name as the site may show it: a first name (one to three words: "Rick", "Mary Jo") and the last
# initial ("W.") — anonymity: never a full last name. The same pattern as committee.js SPEAKER_NAME.
_FIRST_NAME = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’-]*"
SPEAKER_NAME = re.compile(rf"{_FIRST_NAME}(?: {_FIRST_NAME}){{0,2}} [A-ZÀ-ÖØ-Þ]\.")
SPEAKER_CONFIRM_DAYS = 45      # a speaker this close who is not confirmed yet: a reminder for the chair (build_data)


def _line(v: Any) -> str:
    """A text setting as one line ("" for nothing, a list or a block)."""
    return "" if v is None or isinstance(v, (dict, list, bool)) else " ".join(str(v).split())


def meeting_speakers(cfg: dict | None) -> tuple[dict[str, dict], list[str]]:
    """config/site.yml `meeting: speakers:` → ({"2027-01-20": speaker, …} soonest first, notes for the chair).
    A speaker: {"name": "Rick W.", "position": {"en", "es"}, "topic": {"en", "es"}, "confirmed": bool} — a language
    left out has the other one's words; `confirmed` is for the chair (build_data's reminder), never shown.
    Every speaker of the list is shown, but one that would be wrong to show is left out, and a note says why: a date
    that is not a date, not a meeting day by the rule (the 3rd Wednesday) or one of the skip_dates, a name that is
    not a first name and a last initial ("Rick W." — anonymity), a second speaker for one date. One without a topic
    is shown without it (and noted). The web pages read the list the same way, with the same notes as build
    warnings (eleventy/filters/committee.js meetingSpeakers), so no meeting has a speaker on one and not the other."""
    cfg = cfg if isinstance(cfg, dict) else {}
    raw = cfg.get("speakers")
    if raw is None or raw == "" or raw == []:
        return {}, []
    if isinstance(raw, dict):              # a single speaker written without the leading "- "
        raw = [raw]
    if not isinstance(raw, list):
        return {}, ["speakers: not understood — it must be a list, each speaker starting with “- date:”"]
    rule = meeting_rule(cfg)
    nth = f"{ORD_SHORT[rule.week_of_month]} {DAY_NAMES_EN[rule.weekday]}"
    out: dict[str, dict] = {}
    notes: list[str] = []
    for n, e in enumerate(raw, 1):
        if not isinstance(e, dict):
            notes.append(f"speakers entry {n}: not understood (its settings must be indented under “- date:”) "
                         "— left out")
            continue
        name = _line(e.get("name"))
        who = f"speaker “{name}”" if name else f"speakers entry {n}"
        ymd = ymd_text(e.get("date"))
        if not ymd:
            notes.append(f"{who}: date “{_line(e.get('date'))}” is not a date like \"2027-01-20\" — left out")
            continue
        d = date.fromisoformat(ymd)
        day = nth_weekday(d.year, d.month, rule.weekday, rule.week_of_month)
        if day != d:
            notes.append(f"{who}: {ymd} is not the {nth} of its month — left out ("
                         + (f"that month's meeting is {day.isoformat()})" if day else f"that month has no {nth})"))
            continue
        if ymd in rule.skip:
            notes.append(f"{who}: {ymd} is one of the skip_dates (no meeting that day) — left out")
            continue
        if not SPEAKER_NAME.fullmatch(name):
            notes.append(f"{who} ({ymd}): the name must be a first name and a last initial, like \"Rick W.\" — left out")
            continue
        if ymd in out:
            notes.append(f"{who}: {ymd} has a speaker already (“{out[ymd]['name']}”) — left out")
            continue
        pos = (_line(e.get("position")), _line(e.get("position_es")))
        top = (_line(e.get("topic")), _line(e.get("topic_es")))
        if not any(top):
            notes.append(f"{who} ({ymd}): no topic — shown without one")
        out[ymd] = {"name": name, "position": {"en": pos[0] or pos[1], "es": pos[1] or pos[0]},
                    "topic": {"en": top[0] or top[1], "es": top[1] or top[0]}, "confirmed": e.get("confirmed") is True}
    return dict(sorted(out.items())), notes


def speaker_until(cfg: dict | None) -> tuple[tuple[int, int] | None, list[str]]:
    """config/site.yml `meeting: speaker_until` ("19:30": the guest speaker's part ends by then; coming events,
    workshop requests, special offers, magazine topics and GVR and RLV sharing follow until the meeting's end) →
    ((19, 30), notes). None when it is left out — or noted when it cannot be read or is not between the meeting's
    start and end (committee.js meetingSpeakerUntil reads it the same way)."""
    cfg = cfg if isinstance(cfg, dict) else {}
    v = cfg.get("speaker_until")
    if v is None or v == "":
        return None, []
    (sh, sm), (eh, em) = meeting_rule(cfg).span()
    t = parse_hhmm(v, (-1, -1))
    if t == (-1, -1) or not (sh, sm) < t < ((eh, em) if (eh, em) > (sh, sm) else (24, 0)):
        return None, [f"speaker_until “{v}” is not a time between the meeting's start and end — not shown"]
    return t, []


def upcoming_meetings(count: int = 12, include_recent_days: int = 0, now: datetime | None = None,
                      cfg: dict | None = None) -> list[dict]:
    """The next `count` committee meetings (config/site.yml `meeting:`) as of `now` (default: the clock).
    build_data passes its own clock and settings (Ctx.now / Ctx.cfg), so a build — or a test — with a fixed
    clock gets the meetings of ITS day, not the real day's."""
    cfg = cfg if cfg is not None else load_config()
    tz = ZoneInfo((cfg.get("site", {}) or {}).get("timezone", "America/Chicago"))
    return upcoming_rule_dates(meeting_rule(cfg.get("meeting", {})), count, tz, now=now,
                               include_recent_days=include_recent_days)


# The months of committee meetings the web pages list: this month (the site's time zone) and the MEETING_MONTHS_AHEAD
# after it — eleventy/filters/committee.js MEETING_MONTHS_AHEAD, the window of normalizeEvents (/events/, /events.ics,
# the event share pages; the month pages are the same months). The sync writes a record for every date of those months
# (build_data.committee_meetings: its flyer, its guest speaker), so no date the pages list goes without the flyer the
# Drive has for it. One number on both sides: a unit test keeps the two in step (tests/test_r24_meeting_window.py).
MEETING_MONTHS_AHEAD = 12


def window_meetings(now: datetime | None = None, cfg: dict | None = None,
                    months_ahead: int = MEETING_MONTHS_AHEAD) -> list[dict]:
    """The committee meetings (config/site.yml `meeting:`) the web pages list as of `now` (default: the clock) that are
    not over yet, soonest first: every date of the rule from `now`'s month in the site's time zone through
    `months_ahead` months after it — the months of committee.js meetingDates(meeting, 0, MEETING_MONTHS_AHEAD). Not a
    count of dates: before this month's meeting the pages list 13 (on Nov 11, 2026: Nov 18, 2026 … Nov 17, 2027),
    after it 12 — a count of 12 left the 13th without its record, and so without its flyer. A meeting of the month
    before that is still running (an overnight one on a month's last day) is in it too, as in upcoming_meetings."""
    cfg = cfg if cfg is not None else load_config()
    tz = ZoneInfo((cfg.get("site", {}) or {}).get("timezone", "America/Chicago"))
    # (upcoming_rule_dates walks from the month before now's: that one, now's and the `months_ahead` after it — at
    # most one date each, so the count never cuts the window short)
    months = max(0, int(months_ahead)) + 2
    return upcoming_rule_dates(meeting_rule(cfg.get("meeting", {})), months, tz, now=now, horizon_months=months)


if __name__ == "__main__":
    for x in upcoming_meetings(4):
        print(x)
