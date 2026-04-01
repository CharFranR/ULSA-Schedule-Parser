from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Iterable, Optional


class ScheduleError(ValueError):
    """Base error for schedule domain parsing/validation."""


class DayParseError(ScheduleError):
    pass


class TimeParseError(ScheduleError):
    pass


class DurationNotSupportedError(ScheduleError):
    pass


class AlignmentError(ScheduleError):
    pass


class Day(Enum):
    MON = "Lu"
    TUE = "Ma"
    WED = "Mi"
    THU = "Ju"
    FRI = "Vi"
    SAT = "Sa"

    @classmethod
    def from_token(cls, token: str) -> "Day":
        normalized = token.strip().title()[:2]
        for day in cls:
            if day.value == normalized:
                return day
        raise DayParseError(f"invalid day token: {token!r}")


@dataclass(frozen=True)
class Time:
    minutes: int

    def __post_init__(self) -> None:
        if self.minutes < 0 or self.minutes >= 24 * 60:
            raise TimeParseError(f"invalid time minutes: {self.minutes}")

    def format_ampm(self) -> str:
        hour = self.minutes // 60
        minute = self.minutes % 60
        suffix = "am" if hour < 12 else "pm"
        hour12 = hour % 12
        if hour12 == 0:
            hour12 = 12
        return f"{hour12:02d}:{minute:02d} {suffix}"


@dataclass(frozen=True)
class Event:
    code: str
    subject: str
    teacher: str
    group: str
    day: Day
    start: Time
    end: Time
    location: str

    @property
    def duration_minutes(self) -> int:
        return self.end.minutes - self.start.minutes

    def __post_init__(self) -> None:
        if self.end.minutes <= self.start.minutes:
            raise TimeParseError(
                f"event end must be after start: {self.start.minutes} -> {self.end.minutes}"
            )


@dataclass
class CellRender:
    top: list[Event] = field(default_factory=list)
    bottom: list[Event] = field(default_factory=list)
    conflict_top: bool = False
    conflict_bottom: bool = False


@dataclass(frozen=True)
class ScheduleView:
    grid: list[list[CellRender]]
    days: list[Day]
    time_labels: list[str]
    has_conflicts: bool
    is_lunch_row: list[bool] = field(default_factory=list)


_TIME_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>am|pm)$", re.IGNORECASE)
_TIME_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}\s*(?:am|pm))\s*-\s*(?P<end>\d{1,2}:\d{2}\s*(?:am|pm))",
    re.IGNORECASE,
)
_LINE_RE = re.compile(
    r"^\s*(?P<day>[A-Za-z]{2})\s+(?P<range>\d{1,2}:\d{2}\s*(?:am|pm)\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm))\s*(?:\[\s*(?P<loc>[^\]]+)\s*\])?\s*$",
    re.IGNORECASE,
)


def parse_time(value: str) -> Time:
    match = _TIME_RE.match(value.strip())
    if not match:
        raise TimeParseError(f"invalid time format: {value!r}")
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    ampm = match.group("ampm").lower()
    if hour < 1 or hour > 12 or minute < 0 or minute > 59:
        raise TimeParseError(f"invalid time value: {value!r}")
    if ampm == "am":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12
    return Time(hour * 60 + minute)


def parse_time_range(value: str) -> tuple[Time, Time]:
    match = _TIME_RANGE_RE.search(value.strip())
    if not match:
        raise TimeParseError(f"invalid time range: {value!r}")
    start = parse_time(match.group("start"))
    end = parse_time(match.group("end"))
    if end.minutes <= start.minutes:
        raise TimeParseError(f"time range end must be after start: {value!r}")
    return start, end


def parse_day_token(value: str) -> Day:
    return Day.from_token(value)


def parse_schedule_line(value: str) -> tuple[Day, Time, Time, Optional[str]]:
    """Parse a schedule line like 'Lu 08:00 am - 09:40 am [ I102 ]'."""
    match = _LINE_RE.match(value)
    if not match:
        raise ScheduleError(f"invalid schedule line: {value!r}")
    day = parse_day_token(match.group("day"))
    start, end = parse_time_range(match.group("range"))
    location = match.group("loc")
    if location is not None:
        location = location.strip()
    return day, start, end, location


def ordered_days(events: Iterable[Event]) -> list[Day]:
    days = {event.day for event in events}
    ordered = [Day.MON, Day.TUE, Day.WED, Day.THU, Day.FRI]
    result = [day for day in ordered if day in days]
    if Day.SAT in days:
        result.append(Day.SAT)
    return result
