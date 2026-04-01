from __future__ import annotations

import unittest
from pathlib import Path

from ulsa_schedule.adapters.html_bs4 import HtmlBs4ScheduleParser
from ulsa_schedule.domain.model import Day


class TestHtmlParser(unittest.TestCase):
    def test_parse_fixture_events(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "imprimir_inscripcion.html"
        html = fixture.read_text(encoding="utf-8")
        events = HtmlBs4ScheduleParser().parse(html)
        self.assertTrue(events)
        days = {event.day for event in events}
        self.assertTrue({Day.MON, Day.TUE, Day.WED, Day.THU}.issubset(days))
