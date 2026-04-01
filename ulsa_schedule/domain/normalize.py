from __future__ import annotations

from .model import AlignmentError, DurationNotSupportedError, Event, ScheduleView, CellRender, Day, ordered_days, Time


def _segment_bounds(event: Event) -> list[tuple[int, int]]:
    duration = event.duration_minutes
    if duration % 50 != 0:
        raise DurationNotSupportedError(
            f"duration must be a multiple of 50 minutes, got {duration}"
        )
    if duration < 50:
        raise DurationNotSupportedError(
            f"duration must be at least 50 minutes, got {duration}"
        )
    segments = []
    start = event.start.minutes
    for i in range(duration // 50):
        seg_start = start + i * 50
        seg_end = seg_start + 50
        segments.append((seg_start, seg_end))
    return segments


def _merge_consecutive_events(events: list[Event]) -> list[Event]:
    """Merge consecutive events with same properties into a single event."""
    if not events:
        return events

    # Group events by day
    events_by_day: dict[Day, list[Event]] = {}
    for event in events:
        events_by_day.setdefault(event.day, []).append(event)

    merged: list[Event] = []
    for day in Day:
        day_events = events_by_day.get(day, [])
        if not day_events:
            continue

        # Sort by start time
        day_events = sorted(day_events, key=lambda e: e.start.minutes)

        i = 0
        while i < len(day_events):
            current = day_events[i]
            merged_end = current.end

            # Look ahead for consecutive events with same properties
            j = i + 1
            while j < len(day_events):
                next_event = day_events[j]
                # Check if consecutive (end of current == start of next) and same properties
                if (
                    merged_end == next_event.start
                    and current.code == next_event.code
                    and current.subject == next_event.subject
                    and current.teacher == next_event.teacher
                    and current.group == next_event.group
                    and current.location == next_event.location
                ):
                    merged_end = next_event.end
                    j += 1
                else:
                    break

            # Create merged event
            if j > i + 1:
                # Events were merged
                merged.append(
                    Event(
                        code=current.code,
                        subject=current.subject,
                        teacher=current.teacher,
                        group=current.group,
                        day=current.day,
                        start=current.start,
                        end=Time(merged_end.minutes),
                        location=current.location,
                    )
                )
            else:
                merged.append(current)

            i = j

    return merged


def _has_lunch_gap(sorted_bounds: list[int]) -> bool:
    """Check if schedule has events spanning around lunch time (11:40 AM - 1:00 PM)."""
    lunch_start = 700  # 11:40 am
    lunch_end = 780  # 1:00 pm

    # Check if any event spans across the lunch period
    for start, end in zip(sorted_bounds, sorted_bounds[1:]):
        # If an event starts before lunch and ends after lunch
        if start < lunch_end and end > lunch_start:
            return True
    return False


def _insert_lunch_row(
    grid: list[list[CellRender]],
    time_labels: list[str],
    run_offsets: list[tuple[int, int]],
    runs: list[list[int]],
) -> tuple[list[list[CellRender]], list[str], list[tuple[int, int]]]:
    """Insert a lunch row between morning and afternoon blocks."""
    if not run_offsets:
        return grid, time_labels, run_offsets

    # Find the position to insert lunch row (around 11:40 - 1:00)
    lunch_label = "ALMUERZO"
    lunch_time = "11:40 am - 01:00 pm"

    # Find split point: after last morning block, before first afternoon block
    insert_idx = len(grid)  # Default to end

    for idx, (run_start, _) in enumerate(run_offsets):
        # If run starts at or after 1:00 pm (780 min), this is afternoon
        if run_start >= 780:
            # Insert lunch row before this run's blocks
            # Calculate total blocks before this run
            insert_idx = 0
            for i in range(idx):
                run = runs[i]
                slot_count = len(run) - 1
                insert_idx += (slot_count + 1) // 2
            break
    else:
        # No afternoon found, check if morning spans lunch
        if run_offsets and run_offsets[0][0] < 700:
            # Morning ends before lunch, insert at end
            insert_idx = len(grid)

    # Only insert if not already there (insert_idx == len(grid) is a valid append)
    if insert_idx > 0 and insert_idx <= len(grid):
        # Insert lunch row
        lunch_row = [CellRender() for _ in range(len(grid[0]))]
        grid.insert(insert_idx, lunch_row)
        time_labels.insert(insert_idx, lunch_time)

        # Adjust run_offsets to account for lunch row (offset +1 for all runs after lunch)
        new_run_offsets = []
        for run_start, block_offset in run_offsets:
            if run_start >= 780:
                new_run_offsets.append((run_start, block_offset + 1))
            else:
                new_run_offsets.append((run_start, block_offset))

        return grid, time_labels, new_run_offsets

    return grid, time_labels, run_offsets


def normalize_schedule(events: list[Event]) -> ScheduleView:
    if not events:
        return ScheduleView(grid=[], days=[], time_labels=[], has_conflicts=False, is_lunch_row=[])

    # Merge consecutive events with same properties
    events = _merge_consecutive_events(events)

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

    # Insert lunch row if schedule spans across lunch period
    is_lunch_row = [False] * len(time_labels)
    if _has_lunch_gap(sorted_bounds):
        grid, time_labels, _ = _insert_lunch_row(grid, time_labels, run_offsets, runs)
        is_lunch_row = [False] * len(time_labels)
        for i, lbl in enumerate(time_labels):
            if "ALMUERZO" in lbl:
                is_lunch_row[i] = True
                break

    return ScheduleView(
        grid=grid,
        days=days,
        time_labels=time_labels,
        has_conflicts=has_conflicts,
        is_lunch_row=is_lunch_row,
    )
