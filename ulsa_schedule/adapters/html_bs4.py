from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

from ..domain.model import Event, ScheduleError, parse_schedule_line


@dataclass(frozen=True)
class HtmlBs4ScheduleParser:
    def parse(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("#tableCurso")
        if table is None:
            raise ScheduleError("missing #tableCurso table")

        events: list[Event] = []
        rows = table.select("tbody tr.removeCS")
        if not rows:
            rows = table.select("tbody tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            code = cells[0].get_text(strip=True)
            subject = cells[1].get_text(" ", strip=True)
            group_cell = cells[3]
            teacher = cells[4].get_text(" ", strip=True)

            group_label = ""
            label = group_cell.select_one("span.label")
            if label is not None:
                group_label = label.get_text(" ", strip=True)

            lines = list(group_cell.stripped_strings)
            if group_label:
                lines = [line for line in lines if line != group_label]
            for line in lines:
                if line.startswith("Gpo"):
                    group_label = line
                    continue
                if "-" not in line or ":" not in line:
                    continue
                day, start, end, location = parse_schedule_line(line)
                events.append(
                    Event(
                        code=code,
                        subject=subject,
                        teacher=teacher,
                        group=group_label,
                        day=day,
                        start=start,
                        end=end,
                        location=location or "",
                    )
                )

        if not events:
            raise ScheduleError("no schedule events found in #tableCurso")
        return events
