from __future__ import annotations

from typing import Protocol

from ..domain.model import Event, ScheduleView
from ..domain.normalize import normalize_schedule


class HtmlScheduleParser(Protocol):
    def parse(self, html: str) -> list[Event]:
        ...


class ScheduleRenderer(Protocol):
    def render(self, schedule: ScheduleView) -> bytes:
        ...


class RenderScheduleUseCase:
    def __init__(self, parser: HtmlScheduleParser, renderer: ScheduleRenderer) -> None:
        self._parser = parser
        self._renderer = renderer

    def execute(self, html: str) -> tuple[bytes, ScheduleView]:
        events = self._parser.parse(html)
        view = normalize_schedule(events)
        payload = self._renderer.render(view)
        return payload, view
