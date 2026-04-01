from __future__ import annotations

import unittest

from ulsa_schedule.domain.model import AlignmentError, Day, Event, ScheduleView, Time
from ulsa_schedule.domain.normalize import normalize_schedule


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

    def test_block100_bottom_start_error(self) -> None:
        with self.assertRaises(AlignmentError):
            normalize_schedule([self._event(Day.MON, 8 * 60 + 50, 10 * 60 + 30)])

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
