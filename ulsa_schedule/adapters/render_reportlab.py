from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

from ..domain.model import CellRender, ScheduleView


def _load_reportlab():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise ImportError(
            "ReportLab is required for PDF output. Install with: "
            "pip install ulsa_schedule[pdf] (or pip install '.[pdf]' from the repo)."
        ) from exc
    return colors, A4, canvas


@dataclass(frozen=True)
class ReportlabScheduleRenderer:
    page_size: tuple[float, float] | None = None

    def render(self, schedule: ScheduleView) -> bytes:
        colors, default_size, canvas_mod = _load_reportlab()
        page_size = self.page_size or default_size
        width, height = page_size

        buffer = BytesIO()
        pdf = canvas_mod.Canvas(buffer, pagesize=page_size)

        if not schedule.grid or not schedule.days:
            pdf.showPage()
            pdf.save()
            return buffer.getvalue()

        margin = 40
        header_height = 60
        time_col_width = 140
        rows = len(schedule.grid)
        cols = len(schedule.days)

        grid_left = margin + time_col_width
        grid_top = margin + header_height
        grid_width = width - grid_left - margin
        grid_height = height - grid_top - margin
        cell_width = grid_width / max(cols, 1)
        cell_height = grid_height / max(rows, 1)

        def rect(
            x0: float,
            y0: float,
            x1: float,
            y1: float,
            stroke_color,
            fill_color=None,
            stroke_width: float = 1.0,
        ) -> None:
            pdf.setStrokeColor(stroke_color)
            pdf.setLineWidth(stroke_width)
            if fill_color is None:
                pdf.setFillColor(stroke_color)
                pdf.rect(x0, height - y1, x1 - x0, y1 - y0, stroke=1, fill=0)
                return
            pdf.setFillColor(fill_color)
            pdf.rect(x0, height - y1, x1 - x0, y1 - y0, stroke=1, fill=1)

        def line(x0: float, y0: float, x1: float, y1: float, color, width: float = 1.0) -> None:
            pdf.setStrokeColor(color)
            pdf.setLineWidth(width)
            pdf.line(x0, height - y0, x1, height - y1)

        def text(x: float, y: float, value: str, font: str, size: int) -> None:
            pdf.setFont(font, size)
            pdf.setFillColor(colors.black)
            pdf.drawString(x, height - y - size, value)

        for col_index, day in enumerate(schedule.days):
            x0 = grid_left + col_index * cell_width
            x1 = x0 + cell_width
            rect(x0, margin, x1, margin + header_height, colors.black)
            text(x0 + 8, margin + 20, day.value, "Helvetica-Bold", 12)

        for row_index, label in enumerate(schedule.time_labels):
            y0 = grid_top + row_index * cell_height
            y1 = y0 + cell_height
            rect(margin, y0, grid_left, y1, colors.black)
            text(margin + 8, y0 + cell_height / 2 - 4, label, "Helvetica", 9)

        for row_index in range(rows):
            y0 = grid_top + row_index * cell_height
            y1 = y0 + cell_height
            for col_index in range(cols):
                x0 = grid_left + col_index * cell_width
                x1 = x0 + cell_width
                rect(x0, y0, x1, y1, colors.HexColor("#666666"))
                cell = schedule.grid[row_index][col_index]
                self._render_cell(pdf, colors, cell, x0, y0, x1, y1, height)

        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    def _render_cell(self, pdf, colors, cell: CellRender, x0: float, y0: float, x1: float, y1: float, page_height: float) -> None:
        mid_y = y0 + (y1 - y0) / 2
        self._draw_half(pdf, colors, cell.top, x0, y0, x1, mid_y, page_height)
        self._draw_half(pdf, colors, cell.bottom, x0, mid_y, x1, y1, page_height)
        if cell.conflict_top:
            self._draw_conflict(pdf, colors, x0, y0, x1, mid_y, page_height)
        if cell.conflict_bottom:
            self._draw_conflict(pdf, colors, x0, mid_y, x1, y1, page_height)

    def _draw_half(
        self,
        pdf,
        colors,
        events: Iterable,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        page_height: float,
    ) -> None:
        events = list(events)
        if not events:
            return
        pdf.setStrokeColor(colors.HexColor("#666666"))
        pdf.setFillColor(colors.HexColor("#DDEBFF"))
        pdf.rect(x0, page_height - y1, x1 - x0, y1 - y0, stroke=0, fill=1)
        padding = 4
        lines = [" / ".join(event.subject for event in events)]
        lines.append(" / ".join(event.code for event in events))
        location = " / ".join(event.location for event in events if event.location)
        if location:
            lines.append(location)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 8)
        cursor_y = y0 + padding + 8
        for line in lines:
            pdf.drawString(x0 + padding, page_height - cursor_y, line)
            cursor_y += 10

    def _draw_conflict(self, pdf, colors, x0: float, y0: float, x1: float, y1: float, page_height: float) -> None:
        pdf.setStrokeColor(colors.red)
        pdf.setLineWidth(2)
        pdf.rect(x0, page_height - y1, x1 - x0, y1 - y0, stroke=1, fill=0)
        pdf.line(x0, page_height - y0, x1, page_height - y1)
        pdf.line(x0, page_height - y1, x1, page_height - y0)
