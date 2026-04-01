from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass
from importlib import resources

from PIL import Image, ImageDraw, ImageFont

from ..domain.model import CellRender, Day, ScheduleView


@dataclass(frozen=True)
class PillowScheduleRenderer:
    width: int = 1920
    height: int = 1080
    supersample: int = 2

    BUNDLED_FONT = "assets/fonts/DejaVuSans.ttf"

    # Color palette per day (pastel colors)
    DAY_COLORS: dict[Day, str] = None

    def __post_init__(self):
        object.__setattr__(self, 'DAY_COLORS', {
            Day.MON: "#E8F4FD",  # light blue
            Day.TUE: "#FFF3E0",  # light orange
            Day.WED: "#E8F5E9",  # light green
            Day.THU: "#F3E5F5",  # light purple
            Day.FRI: "#FFF8E1",  # light yellow
            Day.SAT: "#FCE4EC",  # light pink
        })

    def render(self, schedule: ScheduleView) -> bytes:
        scale = max(1, self.supersample)
        canvas_width = self.width * scale
        canvas_height = self.height * scale
        image = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(image)

        if not schedule.grid or not schedule.days:
            if scale > 1:
                resampling = getattr(Image, "Resampling", Image)
                image = image.resize(
                    (self.width, self.height),
                    resample=resampling.LANCZOS,
                )
            return self._to_png_bytes(image)

        margin = 40 * scale
        header_height = 60 * scale
        time_col_width = 140 * scale
        rows = len(schedule.grid)
        cols = len(schedule.days)

        grid_left = margin + time_col_width
        grid_top = margin + header_height
        # NOTE: grid geometry must be computed in canvas coordinates
        grid_width = canvas_width - grid_left - margin
        grid_height = canvas_height - grid_top - margin
        cell_width = grid_width / max(cols, 1)
        cell_height = grid_height / max(rows, 1)

        font_header = self._load_font(28 * scale)
        font_body = self._load_font(18 * scale)
        font_time = self._load_font(16 * scale)

        for col_index, day in enumerate(schedule.days):
            x0 = grid_left + col_index * cell_width
            x1 = x0 + cell_width
            draw.rectangle([x0, margin, x1, margin + header_height], fill="#2C3E50", outline="#BDC3C7")
            label = day.value
            self._draw_centered_text(
                draw,
                label,
                x0,
                margin,
                x1,
                margin + header_height,
                font_header,
                fill="white",
            )

        for row_index, label in enumerate(schedule.time_labels):
            y0 = grid_top + row_index * cell_height
            y1 = y0 + cell_height
            draw.rectangle([margin, y0, grid_left, y1], fill="#34495E", outline="#BDC3C7")
            self._draw_centered_text(
                draw,
                label,
                margin,
                y0,
                grid_left,
                y1,
                font_time,
                fill="white",
            )

        for row_index in range(rows):
            y0 = grid_top + row_index * cell_height
            y1 = y0 + cell_height
            
            # Check if this is a lunch row
            is_lunch = row_index < len(schedule.is_lunch_row) and schedule.is_lunch_row[row_index]
            
            for col_index in range(cols):
                x0 = grid_left + col_index * cell_width
                x1 = x0 + cell_width
                draw.rectangle([x0, y0, x1, y1], outline="#BDC3C7")
                day = schedule.days[col_index]
                cell = schedule.grid[row_index][col_index]
                
                # Pass lunch info to renderer
                self._render_cell(draw, cell, day, is_lunch, x0, y0, x1, y1, font_body, scale)

        # Draw "ALMUERZO" text centered across the full lunch row
        for row_index in range(rows):
            is_lunch = row_index < len(schedule.is_lunch_row) and schedule.is_lunch_row[row_index]
            if is_lunch:
                y0 = grid_top + row_index * cell_height
                y1 = y0 + cell_height
                self._draw_centered_text(
                    draw,
                    "ALMUERZO",
                    grid_left,
                    y0,
                    grid_left + grid_width,
                    y1,
                    font_body,
                    fill="#7F8C8D",
                )
                break

        if scale > 1:
            resampling = getattr(Image, "Resampling", Image)
            image = image.resize(
                (self.width, self.height),
                resample=resampling.LANCZOS,
            )

        return self._to_png_bytes(image)

    def _render_cell(
        self,
        draw: ImageDraw.ImageDraw,
        cell: CellRender,
        day: Day,
        is_lunch: bool,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        font: ImageFont.ImageFont,
        scale: int,
    ) -> None:
        mid_y = y0 + (y1 - y0) / 2
        
        # Draw lunch row background if this is a lunch row
        if is_lunch:
            draw.rectangle([x0, y0, x1, y1], fill="#F5F5F5")
            return
        
        color = self.DAY_COLORS.get(day, "#DDEBFF")
        if self._events_equivalent(cell.top, cell.bottom):
            self._draw_block(draw, cell.top, color, x0, y0, x1, y1, font, scale)
            if cell.conflict_top or cell.conflict_bottom:
                self._draw_conflict(draw, x0, y0, x1, y1)
            return

        self._draw_half(draw, cell.top, color, x0, y0, x1, mid_y, font, scale)
        self._draw_half(draw, cell.bottom, color, x0, mid_y, x1, y1, font, scale)
        if cell.conflict_top:
            self._draw_conflict(draw, x0, y0, x1, mid_y)
        if cell.conflict_bottom:
            self._draw_conflict(draw, x0, mid_y, x1, y1)

    def _draw_half(
        self,
        draw: ImageDraw.ImageDraw,
        events: list,
        color: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        font: ImageFont.ImageFont,
        scale: int,
    ) -> None:
        if not events:
            return
        self._draw_block(draw, events, color, x0, y0, x1, y1, font, scale)

    def _draw_block(
        self,
        draw: ImageDraw.ImageDraw,
        events: list,
        color: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        font: ImageFont.ImageFont,
        scale: int,
    ) -> None:
        if not events:
            return
        padding = 8 * scale
        draw.rectangle([x0, y0, x1, y1], fill=color)
        max_width = max(1, x1 - x0 - padding * 2)
        max_height = max(1, y1 - y0 - padding * 2)
        lines = self._compose_event_lines(events, draw, font, max_width, max_height, scale)
        if not lines:
            return
        line_height = self._line_height(draw, font)
        spacing = 2 * scale
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
        start_y = y0 + padding + max(0, (max_height - total_height) / 2)
        for index, line in enumerate(lines):
            y = start_y + index * (line_height + spacing)
            draw.text((x0 + padding, y), line, fill="#2C3E50", font=font)

    def _draw_conflict(
        self,
        draw: ImageDraw.ImageDraw,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> None:
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        draw.line([x0, y0, x1, y1], fill="red", width=2)
        draw.line([x0, y1, x1, y0], fill="red", width=2)

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        bundled_font = self._load_bundled_font(size)
        if bundled_font is not None:
            return bundled_font
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except OSError:
                    continue
        return ImageFont.load_default()

    def _load_bundled_font(self, size: int) -> ImageFont.ImageFont | None:
        try:
            font_resource = resources.files("ulsa_schedule") / self.BUNDLED_FONT
            with resources.as_file(font_resource) as font_path:
                return ImageFont.truetype(str(font_path), size=size)
        except Exception as exc:
            warnings.warn(
                f"Unable to load bundled font '{self.BUNDLED_FONT}': {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        font: ImageFont.ImageFont,
        fill: str = "black",
    ) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = x0 + (x1 - x0 - text_width) / 2
        y = y0 + (y1 - y0 - text_height) / 2
        draw.text((x, y), text, fill=fill, font=font)

    def _events_equivalent(self, top: list, bottom: list) -> bool:
        if not top and not bottom:
            return True
        if not top or not bottom:
            return False
        return self._event_signatures(top) == self._event_signatures(bottom)

    def _event_signatures(self, events: list) -> set[tuple[str, str, str]]:
        signatures: set[tuple[str, str, str]] = set()
        for event in events:
            signatures.add((event.subject.strip(), event.code.strip(), event.location.strip()))
        return signatures

    def _compose_event_lines(
        self,
        events: list,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont,
        max_width: float,
        max_height: float,
        scale: int,
    ) -> list[str]:
        subjects = " / ".join(self._clean_subject(event.subject) for event in events)
        codes = " / ".join(event.code for event in events if event.code)
        locations = " / ".join(event.location for event in events if event.location)

        line_height = self._line_height(draw, font)
        spacing = 2 * scale
        max_lines_total = max(1, int((max_height + spacing) // (line_height + spacing)))
        max_lines_total = min(3, max_lines_total)

        lines: list[str] = []
        remaining = max_lines_total
        subject_lines = self._wrap_text(subjects, max_width, min(2, remaining), draw, font)
        lines.extend(subject_lines)
        remaining = max_lines_total - len(lines)

        if remaining > 0 and codes:
            lines.append(self._truncate_text(codes, max_width, draw, font))
            remaining -= 1

        if remaining > 0 and locations:
            lines.append(self._truncate_text(locations, max_width, draw, font))

        return lines

    def _clean_subject(self, subject: str) -> str:
        cleaned = re.sub(r"\[[^\]]*\]", "", subject)
        return " ".join(cleaned.split()).strip()

    def _line_height(self, draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> int:
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        return bbox[3] - bbox[1]

    def _wrap_text(
        self,
        text: str,
        max_width: float,
        max_lines: int,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont,
    ) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if self._text_width(draw, candidate, font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        if len(lines) < max_lines and current:
            lines.append(current)

        if len(lines) > max_lines:
            lines = lines[:max_lines]

        if len(lines) == max_lines and (len(words) > 0):
            if " ".join(lines) != text:
                lines[-1] = self._truncate_text(lines[-1], max_width, draw, font)
        return lines

    def _truncate_text(
        self,
        text: str,
        max_width: float,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont,
    ) -> str:
        if self._text_width(draw, text, font) <= max_width:
            return text
        ellipsis = "…"
        truncated = text
        while truncated and self._text_width(draw, f"{truncated}{ellipsis}", font) > max_width:
            truncated = truncated[:-1]
        return f"{truncated}{ellipsis}" if truncated else ellipsis

    def _text_width(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
    ) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def _to_png_bytes(self, image: Image.Image) -> bytes:
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
