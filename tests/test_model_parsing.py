from __future__ import annotations

import unittest

from ulsa_schedule.domain.model import (
    Day,
    DayParseError,
    ScheduleError,
    TimeParseError,
    parse_day_token,
    parse_schedule_line,
    parse_time,
    parse_time_range,
)


class TestModelParsing(unittest.TestCase):
    def test_parse_day_token_valid(self) -> None:
        self.assertEqual(parse_day_token("Lu"), Day.MON)
        self.assertEqual(parse_day_token("ma"), Day.TUE)
        self.assertEqual(parse_day_token("Mi"), Day.WED)
        self.assertEqual(parse_day_token("Ju"), Day.THU)
        self.assertEqual(parse_day_token("Vi"), Day.FRI)
        self.assertEqual(parse_day_token("Sa"), Day.SAT)

    def test_parse_day_token_invalid(self) -> None:
        with self.assertRaises(DayParseError):
            parse_day_token("Xx")

    def test_parse_time_valid(self) -> None:
        time = parse_time("08:00 am")
        self.assertEqual(time.minutes, 8 * 60)
        self.assertEqual(parse_time("12:00 am").minutes, 0)
        self.assertEqual(parse_time("12:00 pm").minutes, 12 * 60)
        self.assertEqual(parse_time("01:15 pm").minutes, 13 * 60 + 15)

    def test_parse_time_invalid(self) -> None:
        with self.assertRaises(TimeParseError):
            parse_time("13:00 pm")
        with self.assertRaises(TimeParseError):
            parse_time("08:60 am")
        with self.assertRaises(TimeParseError):
            parse_time("8am")

    def test_parse_time_range_valid(self) -> None:
        start, end = parse_time_range("08:00 am - 09:40 am")
        self.assertEqual(start.minutes, 8 * 60)
        self.assertEqual(end.minutes, 9 * 60 + 40)

    def test_parse_time_range_invalid(self) -> None:
        with self.assertRaises(TimeParseError):
            parse_time_range("08:00 am - 07:40 am")
        with self.assertRaises(TimeParseError):
            parse_time_range("not a range")

    def test_parse_schedule_line_valid(self) -> None:
        day, start, end, location = parse_schedule_line("Lu 08:00 am - 09:40 am [ I102 ]")
        self.assertEqual(day, Day.MON)
        self.assertEqual(start.minutes, 8 * 60)
        self.assertEqual(end.minutes, 9 * 60 + 40)
        self.assertEqual(location, "I102")

    def test_parse_schedule_line_invalid(self) -> None:
        with self.assertRaises(ScheduleError):
            parse_schedule_line("Lu 08:00 - 09:40")
