from __future__ import annotations

import unittest

from ulsa_schedule.domain.model import Day, Event, Time
from ulsa_schedule.domain.normalize import normalize_schedule


class TestConflicts(unittest.TestCase):
    def _event(self, code: str) -> Event:
        return Event(
            code=code,
            subject="Test",
            teacher="",
            group="",
            day=Day.MON,
            start=Time(8 * 60),
            end=Time(9 * 60 + 40),
            location="",
        )

    def test_overlap_marks_conflict(self) -> None:
        view = normalize_schedule([self._event("A"), self._event("B")])
        self.assertTrue(view.has_conflicts)
        cell = view.grid[0][0]
        self.assertTrue(cell.conflict_top)
        self.assertTrue(cell.conflict_bottom)
        self.assertEqual({event.code for event in cell.top}, {"A", "B"})
        self.assertEqual({event.code for event in cell.bottom}, {"A", "B"})
