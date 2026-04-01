from __future__ import annotations

import io
import unittest
from unittest import mock

from PIL import Image

from ulsa_schedule.adapters.render_pillow import PillowScheduleRenderer
from ulsa_schedule.domain.model import CellRender, Day, ScheduleView


class TestRenderPng(unittest.TestCase):
    def _sample_view(self) -> ScheduleView:
        grid = [[CellRender()]]
        return ScheduleView(
            grid=grid,
            days=[Day.MON],
            time_labels=["08:00 am"],
            has_conflicts=False,
        )

    def test_png_signature_and_dimensions(self) -> None:
        payload = PillowScheduleRenderer().render(self._sample_view())
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        image = Image.open(io.BytesIO(payload))
        self.assertEqual(image.size, (1920, 1080))

    def test_png_uses_bundled_font_when_system_fonts_missing(self) -> None:
        with (
            mock.patch("os.path.exists", return_value=False),
            mock.patch(
                "ulsa_schedule.adapters.render_pillow.PillowScheduleRenderer._load_bundled_font"
            ) as load_bundled,
            mock.patch("PIL.ImageFont.load_default") as load_default,
        ):
            sentinel_font = object()
            load_bundled.return_value = sentinel_font
            font = PillowScheduleRenderer()._load_font(20)
        self.assertIs(font, sentinel_font)
        load_default.assert_not_called()
        load_bundled.assert_called_once()

    def test_png_missing_bundled_font_warns_and_falls_back(self) -> None:
        renderer = PillowScheduleRenderer()
        with (
            mock.patch("ulsa_schedule.adapters.render_pillow.resources.files", side_effect=FileNotFoundError("missing")),
            mock.patch("os.path.exists", return_value=False),
            mock.patch("PIL.ImageFont.load_default", return_value="default-font") as load_default,
            self.assertWarns(RuntimeWarning),
        ):
            font = renderer._load_font(20)
        self.assertEqual(font, "default-font")
        load_default.assert_called_once()
