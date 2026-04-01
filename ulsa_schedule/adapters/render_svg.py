from __future__ import annotations

import re
from dataclasses import dataclass

from ..domain.model import CellRender, Day, ScheduleView


@dataclass(frozen=True)
class SvgScheduleRenderer:
    width: int = 1920
    height: int = 1080

    # Color palette per day
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
        if not schedule.grid or not schedule.days:
            return self._render_empty()

        margin = 40
        header_height = 60
        time_col_width = 140
        rows = len(schedule.grid)
        cols = len(schedule.days)

        grid_left = margin + time_col_width
        grid_top = margin + header_height
        grid_width = self.width - grid_left - margin
        grid_height = self.height - grid_top - margin
        cell_width = grid_width / max(cols, 1)
        cell_height = grid_height / max(rows, 1)

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">',
            f'<style>'
            f'.header {{ fill: #2C3E50; }} '
            f'.time-col {{ fill: #34495E; }} '
            f'.time-text {{ fill: white; font-family: Arial, sans-serif; }} '
            f'.day-text {{ fill: white; font-family: Arial, sans-serif; font-weight: bold; }} '
            f'.cell-text {{ fill: #2C3E50; font-family: Arial, sans-serif; }} '
            f'.grid-line {{ stroke: #BDC3C7; stroke-width: 1; }} '
            f'.lunch {{ fill: #F5F5F5; }} '
            f'.lunch-text {{ fill: #7F8C8D; font-family: Arial, sans-serif; font-weight: bold; }} '
            f'.conflict {{ stroke: #E74C3C; stroke-width: 2; }} '
            f'</style>',
            f'<rect width="{self.width}" height="{self.height}" fill="white"/>',
        ]

        # Header row with days
        for col_index, day in enumerate(schedule.days):
            x0 = grid_left + col_index * cell_width
            x1 = x0 + cell_width
            svg_parts.append(
                f'<rect x="{x0}" y="{margin}" width="{cell_width}" height="{header_height}" class="header"/>'
            )
            svg_parts.append(
                f'<text x="{x0 + cell_width/2}" y="{margin + header_height/2 + 6}" '
                f'text-anchor="middle" class="day-text" font-size="24">{day.value}</text>'
            )

        # Time column
        for row_index, label in enumerate(schedule.time_labels):
            y0 = grid_top + row_index * cell_height
            y1 = y0 + cell_height
            svg_parts.append(
                f'<rect x="{margin}" y="{y0}" width="{time_col_width}" height="{cell_height}" class="time-col"/>'
            )
            svg_parts.append(
                f'<text x="{margin + time_col_width/2}" y="{y0 + cell_height/2 + 5}" '
                f'text-anchor="middle" class="time-text" font-size="14">{label}</text>'
            )

        # Grid cells
        for row_index in range(rows):
            y0 = grid_top + row_index * cell_height
            y1 = y0 + cell_height
            
            # Check if this is a lunch row
            is_lunch = row_index < len(schedule.is_lunch_row) and schedule.is_lunch_row[row_index]
            
            for col_index in range(cols):
                x0 = grid_left + col_index * cell_width
                x1 = x0 + cell_width

                day = schedule.days[col_index]
                
                if is_lunch:
                    # Lunch row has special background
                    svg_parts.append(
                        f'<rect x="{x0}" y="{y0}" width="{cell_width}" height="{cell_height}" class="lunch"/>'
                    )
                    if col_index == len(schedule.days) - 1:
                        # Draw "ALMUERZO" centered across the full lunch row
                        full_x = grid_left + cell_width * len(schedule.days) / 2
                        svg_parts.append(
                            f'<text x="{full_x}" y="{y0 + cell_height/2 + 5}" '
                            f'text-anchor="middle" class="lunch-text" font-size="18">ALMUERZO</text>'
                        )
                else:
                    color = self.DAY_COLORS.get(day, "#DDEBFF")
                    svg_parts.append(
                        f'<rect x="{x0}" y="{y0}" width="{cell_width}" height="{cell_height}" '
                        f'fill="{color}" class="grid-line"/>'
                    )

                cell = schedule.grid[row_index][col_index]
                self._render_cell_svg(svg_parts, cell, is_lunch, x0, y0, x1, y1, cell_width, cell_height)

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts).encode('utf-8')

    def _render_empty(self) -> bytes:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">
  <rect width="{self.width}" height="{self.height}" fill="white"/>
  <text x="{self.width/2}" y="{self.height/2}" text-anchor="middle" fill="#7F8C8D" font-family="Arial, sans-serif" font-size="24">No schedule data</text>
</svg>'''
        return svg.encode('utf-8')

    def _render_cell_svg(
        self,
        svg_parts: list[str],
        cell: CellRender,
        is_lunch: bool,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        cell_width: float,
        cell_height: float,
    ) -> None:
        # Skip rendering events for lunch rows
        if is_lunch:
            return
        
        mid_y = y0 + cell_height / 2

        if self._events_equivalent(cell.top, cell.bottom):
            self._draw_block_svg(svg_parts, cell.top, x0, y0, x1, y1, cell_width, cell_height)
            if cell.conflict_top or cell.conflict_bottom:
                self._draw_conflict_svg(svg_parts, x0, y0, x1, y1)
            return

        self._draw_half_svg(svg_parts, cell.top, x0, y0, x1, mid_y, cell_width, cell_height / 2)
        self._draw_half_svg(svg_parts, cell.bottom, x0, mid_y, x1, y1, cell_width, cell_height / 2)
        if cell.conflict_top:
            self._draw_conflict_svg(svg_parts, x0, y0, x1, mid_y)
        if cell.conflict_bottom:
            self._draw_conflict_svg(svg_parts, x0, mid_y, x1, y1)

    def _draw_half_svg(
        self,
        svg_parts: list[str],
        events: list,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        cell_width: float,
        cell_height: float,
    ) -> None:
        if not events:
            return
        self._draw_block_svg(svg_parts, events, x0, y0, x1, y1, cell_width, cell_height)

    def _draw_block_svg(
        self,
        svg_parts: list[str],
        events: list,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        cell_width: float,
        cell_height: float,
    ) -> None:
        if not events:
            return
        padding = 8
        text_x = x0 + padding
        text_y = y0 + padding
        max_width = max(1, cell_width - padding * 2)
        max_height = max(1, cell_height - padding * 2)

        lines = self._compose_event_lines(events, max_width, max_height)
        if not lines:
            return

        line_height = 18
        spacing = 2
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
        start_y = y0 + padding + max(0, (max_height - total_height) / 2)

        for index, line in enumerate(lines):
            y = start_y + index * (line_height + spacing)
            escaped_line = self._escape_xml(line)
            svg_parts.append(
                f'<text x="{text_x}" y="{y + 14}" class="cell-text" font-size="14">{escaped_line}</text>'
            )

    def _draw_conflict_svg(
        self,
        svg_parts: list[str],
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> None:
        svg_parts.append(
            f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" class="conflict"/>'
        )
        svg_parts.append(
            f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y0}" class="conflict"/>'
        )

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
        max_width: float,
        max_height: float,
    ) -> list[str]:
        subjects = " / ".join(self._clean_subject(event.subject) for event in events)
        codes = " / ".join(event.code for event in events if event.code)
        locations = " / ".join(event.location for event in events if event.location)

        max_lines_total = max(1, int(max_height // 20))
        max_lines_total = min(3, max_lines_total)

        lines: list[str] = []
        remaining = max_lines_total
        subject_lines = self._wrap_text(subjects, max_width, min(2, remaining))
        lines.extend(subject_lines)
        remaining = max_lines_total - len(lines)

        if remaining > 0 and codes:
            lines.append(self._truncate_text(codes, max_width))
            remaining -= 1

        if remaining > 0 and locations:
            lines.append(self._truncate_text(locations, max_width))

        return lines

    def _clean_subject(self, subject: str) -> str:
        cleaned = re.sub(r"\[[^\]]*\]", "", subject)
        return " ".join(cleaned.split()).strip()

    def _wrap_text(self, text: str, max_width: float, max_lines: int) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if self._text_width(candidate) <= max_width:
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
                lines[-1] = self._truncate_text(lines[-1], max_width)
        return lines

    def _truncate_text(self, text: str, max_width: float) -> str:
        if self._text_width(text) <= max_width:
            return text
        ellipsis = "…"
        truncated = text
        while truncated and self._text_width(f"{truncated}{ellipsis}") > max_width:
            truncated = truncated[:-1]
        return f"{truncated}{ellipsis}" if truncated else ellipsis

    def _text_width(self, text: str) -> int:
        # Approximate width: 8px per character (average)
        return len(text) * 8

    def _escape_xml(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")