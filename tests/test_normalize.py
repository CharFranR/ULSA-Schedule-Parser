from __future__ import annotations

import unittest

from ulsa_schedule.domain.model import AlignmentError, Day, Event, ScheduleView, Time, ordered_days
from ulsa_schedule.domain.normalize import normalize_schedule, _merge_consecutive_events


class TestNormalize(unittest.TestCase):
    def _event(self, day: Day, start: int, end: int) -> Event:
        return Event(
            code="X",
            subject="Test",
            teacher="",
            group="",
            day=day,
            start=Time(start),
            end=Time(end),
            location="",
        )

    def test_half_selection_top(self) -> None:
        view = normalize_schedule([self._event(Day.MON, 8 * 60, 8 * 60 + 50)])
        self.assertEqual(view.days, [Day.MON])
        self.assertEqual(len(view.grid), 1)
        cell = view.grid[0][0]
        self.assertEqual(len(cell.top), 1)
        self.assertEqual(len(cell.bottom), 0)

    def test_half_selection_bottom(self) -> None:
        view = normalize_schedule([self._event(Day.MON, 8 * 60 + 50, 9 * 60 + 40)])
        self.assertEqual(len(view.grid), 1)
        cell = view.grid[0][0]
        self.assertEqual(len(cell.top), 0)
        self.assertEqual(len(cell.bottom), 1)

    def test_block100_pairing(self) -> None:
        view = normalize_schedule([self._event(Day.MON, 8 * 60, 9 * 60 + 40)])
        self.assertEqual(len(view.grid), 1)
        cell = view.grid[0][0]
        self.assertEqual(len(cell.top), 1)
        self.assertEqual(len(cell.bottom), 1)

    def test_block100_bottom_start(self) -> None:
        """100-min event starting at bottom half spans two blocks."""
        view = normalize_schedule([self._event(Day.MON, 8 * 60 + 50, 10 * 60 + 30)])
        self.assertEqual(len(view.grid), 2)
        # First block: bottom half has the event
        self.assertEqual(len(view.grid[0][0].bottom), 1)
        self.assertEqual(len(view.grid[0][0].top), 0)
        # Second block: top half has the event
        self.assertEqual(len(view.grid[1][0].top), 1)
        self.assertEqual(len(view.grid[1][0].bottom), 0)

    def test_odd_slot_blank_half(self) -> None:
        events = [
            self._event(Day.MON, 8 * 60, 8 * 60 + 50),
            self._event(Day.MON, 8 * 60 + 100, 8 * 60 + 150),
        ]
        view = normalize_schedule(events)
        self.assertEqual(len(view.grid), 2)
        second_cell = view.grid[1][0]
        self.assertEqual(len(second_cell.top), 1)
        self.assertEqual(len(second_cell.bottom), 0)
        self.assertIsInstance(view, ScheduleView)

    def test_saturday_only_days(self) -> None:
        view = normalize_schedule([self._event(Day.SAT, 9 * 60, 9 * 60 + 50)])
        self.assertEqual(view.days, [Day.SAT])


class TestMergeConsecutiveEvents(unittest.TestCase):
    def _ev(self, day: Day, start: int, end: int, code: str = "X", subject: str = "Test",
            teacher: str = "", group: str = "", location: str = "") -> Event:
        return Event(
            code=code, subject=subject, teacher=teacher, group=group,
            day=day, start=Time(start), end=Time(end), location=location,
        )

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_merge_consecutive_events([]), [])

    def test_consecutive_same_props_merged(self) -> None:
        events = [
            self._ev(Day.MON, 480, 530),
            self._ev(Day.MON, 530, 580),
        ]
        merged = _merge_consecutive_events(events)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].start.minutes, 480)
        self.assertEqual(merged[0].end.minutes, 580)

    def test_non_consecutive_stay_separate(self) -> None:
        events = [
            self._ev(Day.MON, 480, 530),
            self._ev(Day.MON, 600, 650),
        ]
        merged = _merge_consecutive_events(events)
        self.assertEqual(len(merged), 2)

    def test_consecutive_different_props_stay_separate(self) -> None:
        events = [
            self._ev(Day.MON, 480, 530, code="A"),
            self._ev(Day.MON, 530, 580, code="B"),
        ]
        merged = _merge_consecutive_events(events)
        self.assertEqual(len(merged), 2)

    def test_different_days_no_cross_merge(self) -> None:
        events = [
            self._ev(Day.MON, 480, 530),
            self._ev(Day.TUE, 480, 530),
        ]
        merged = _merge_consecutive_events(events)
        self.assertEqual(len(merged), 2)


class TestOrderedDays(unittest.TestCase):
    def test_weekday_plus_saturday_includes_sat(self) -> None:
        events = [
            Event(code="X", subject="T", teacher="", group="",
                  day=Day.MON, start=Time(480), end=Time(530), location=""),
            Event(code="X", subject="T", teacher="", group="",
                  day=Day.SAT, start=Time(480), end=Time(530), location=""),
        ]
        days = ordered_days(events)
        self.assertIn(Day.SAT, days)
        self.assertEqual(days[-1], Day.SAT)
        self.assertEqual(days, [Day.MON, Day.SAT])
