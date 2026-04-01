from __future__ import annotations

from .model import AlignmentError, Duration, DurationNotSupportedError, Event, ScheduleView, CellRender, Day, ordered_days


def _segment_bounds(event: Event) -> list[tuple[int, int]]:
    duration = event.duration_minutes
    try:
        Duration(duration)
    except DurationNotSupportedError as exc:
        raise DurationNotSupportedError(str(exc))
    if duration == 100:
        return [
            (event.start.minutes, event.start.minutes + 50),
            (event.start.minutes + 50, event.end.minutes),
        ]
    return [(event.start.minutes, event.end.minutes)]


def normalize_schedule(events: list[Event]) -> ScheduleView:
    if not events:
        return ScheduleView(grid=[], days=[], time_labels=[], has_conflicts=False)

    days = ordered_days(events)
    all_bounds: set[int] = set()
    for event in events:
        for start, end in _segment_bounds(event):
            if (end - start) % 50 != 0:
                raise AlignmentError(
                    "event boundaries must align to 50-minute slots"
                )
            all_bounds.add(start)
            all_bounds.add(end)
    sorted_bounds = sorted(all_bounds)
    if len(sorted_bounds) < 2:
        raise AlignmentError("not enough boundaries to build slots")

    runs: list[list[int]] = []
    current: list[int] = [sorted_bounds[0]]
    for prev, nxt in zip(sorted_bounds, sorted_bounds[1:]):
        if nxt - prev == 50:
            current.append(nxt)
        else:
            if len(current) > 1:
                runs.append(current)
            current = [nxt]
    if len(current) > 1:
        runs.append(current)

    if not runs:
        raise AlignmentError("no contiguous 50-minute runs available")

    for run in runs:
        minute = run[0] % 60
        if minute in (10, 30, 50):
            run.insert(0, run[0] - 50)

    run_offsets: list[tuple[int, int]] = []
    block_base = 0
    slot_lookup: dict[int, tuple[int, int]] = {}
    for run in runs:
        slot_count = len(run) - 1
        block_count = (slot_count + 1) // 2
        run_offsets.append((run[0], block_base))
        for index, boundary in enumerate(run[:-1]):
            slot_lookup[boundary] = (index, block_base)
        block_base += block_count

    total_blocks = block_base
    grid: list[list[CellRender]] = [
        [CellRender() for _ in range(len(days))] for _ in range(total_blocks)
    ]

    occupancy: dict[tuple[Day, int, str], list[Event]] = {}
    has_conflicts = False

    def add_to_half(day: Day, block_index: int, half: str, event: Event) -> None:
        nonlocal has_conflicts
        key = (day, block_index, half)
        items = occupancy.setdefault(key, [])
        items.append(event)
        cell = grid[block_index][days.index(day)]
        if half == "top":
            cell.top = items
            if len(items) > 1:
                cell.conflict_top = True
                has_conflicts = True
        else:
            cell.bottom = items
            if len(items) > 1:
                cell.conflict_bottom = True
                has_conflicts = True

    def resolve_run_index(start: int) -> tuple[int, int]:
        if start not in slot_lookup:
            raise AlignmentError(f"start time {start} not aligned to 50-minute slots")
        return slot_lookup[start]

    for event in events:
        if event.duration_minutes == 100:
            start = event.start.minutes
            slot_index, block_offset = resolve_run_index(start)
            half = "top" if slot_index % 2 == 0 else "bottom"
            if half != "top":
                raise AlignmentError(
                    "100-minute event must start on top half of a block"
                )
            block_index = block_offset + (slot_index // 2)
            add_to_half(event.day, block_index, "top", event)
            add_to_half(event.day, block_index, "bottom", event)
            continue
        for start, _ in _segment_bounds(event):
            slot_index, block_offset = resolve_run_index(start)
            half = "top" if slot_index % 2 == 0 else "bottom"
            block_index = block_offset + (slot_index // 2)
            add_to_half(event.day, block_index, half, event)

    time_labels: list[str] = []
    for run_start, block_offset in run_offsets:
        run = next(r for r in runs if r[0] == run_start)
        slot_count = len(run) - 1
        block_count = (slot_count + 1) // 2
        for idx in range(block_count):
            minutes = run[0] + idx * 100
            hour = minutes // 60
            minute = minutes % 60
            suffix = "am" if hour < 12 else "pm"
            hour12 = hour % 12
            if hour12 == 0:
                hour12 = 12
            time_labels.append(f"{hour12:02d}:{minute:02d} {suffix}")

    return ScheduleView(
        grid=grid,
        days=days,
        time_labels=time_labels,
        has_conflicts=has_conflicts,
    )
