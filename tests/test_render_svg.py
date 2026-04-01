from __future__ import annotations

import unittest

from ulsa_schedule.adapters.render_svg import SvgScheduleRenderer
from ulsa_schedule.domain.model import CellRender, Day, Event, ScheduleView, Time


class TestRenderSvg(unittest.TestCase):
    def _event(self, day: Day, start: int, end: int, subject: str = "Test") -> Event:
        return Event(
            code="X",
            subject=subject,
            teacher="Teacher",
            group="A",
            day=day,
            start=Time(start),
            end=Time(end),
            location="Room",
        )

    def test_renders_empty_schedule(self) -> None:
        renderer = SvgScheduleRenderer()
        schedule = ScheduleView(grid=[], days=[], time_labels=[], has_conflicts=False)
        result = renderer.render(schedule)
        self.assertIn(b"<svg", result)
        self.assertIn(b"No schedule data", result)

    def test_renders_schedule_with_days(self) -> None:
        renderer = SvgScheduleRenderer()
        events = [self._event(Day.MON, 8 * 60, 8 * 60 + 50)]
        
        from ulsa_schedule.domain.normalize import normalize_schedule
        view = normalize_schedule(events)
        
        result = renderer.render(view)
        self.assertIn(b"<svg", result)
        self.assertIn(b"Lu", result)  # Monday abbreviation
        self.assertIn(b"08:00 am", result)

    def test_returns_bytes(self) -> None:
        renderer = SvgScheduleRenderer()
        schedule = ScheduleView(grid=[], days=[], time_labels=[], has_conflicts=False)
        result = renderer.render(schedule)
        self.assertIsInstance(result, bytes)

    def test_svg_has_viewbox(self) -> None:
        renderer = SvgScheduleRenderer()
        schedule = ScheduleView(grid=[], days=[], time_labels=[], has_conflicts=False)
        result = renderer.render(schedule)
        self.assertIn(b'viewBox="0 0 1920 1080"', result)

    def test_day_colors_applied(self) -> None:
        renderer = SvgScheduleRenderer()
        events = [self._event(Day.MON, 8 * 60, 8 * 60 + 50)]
        
        from ulsa_schedule.domain.normalize import normalize_schedule
        view = normalize_schedule(events)
        
        result = renderer.render(view)
        # Check for light blue color for Monday
        self.assertIn(b"#E8F4FD", result)


if __name__ == "__main__":
    unittest.main()