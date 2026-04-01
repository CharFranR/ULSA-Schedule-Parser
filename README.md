# ULSA Schedule Parser

**Convert ugly ULSA enrollment HTML into beautiful schedule images.**

*PNG, SVG, and PDF output. Zero config. One command.*

[Installation](#installation) • [Usage](#usage) • [Output Formats](#output-formats) • [Architecture](#architecture) • [API](#programmatic-api) • [Contributing](#contributing)

---

> That enrollment HTML from ULSA? You know the one — a wall of `<table>` soup with inline styles from 2005. **ulsa-schedule** parses it and renders a clean, color-coded schedule you can actually read.

One command. PNG by default, SVG for crisp vector output, PDF for printing. Conflict detection included.

```
HTML Input (imprimir_inscripcion.html)
    ↓ parse
Domain Model (Events, Days, Time slots)
    ↓ normalize
ScheduleView (grid + metadata)
    ↓ render
PNG / SVG / PDF
```

## Quick Start

### Install

```bash
pip install ulsa-schedule-parser
```

For PDF support:

```bash
pip install ulsa-schedule-parser[pdf]
```

From source:

```bash
git clone https://github.com/CharFranR/ULSA-Schedule-Parser.git
cd ULSA-Schedule-Parser
pip install .
```

### Use

```bash
# PNG (default)
ulsa-schedule path/to/imprimir_inscripcion.html

# Custom output name
ulsa-schedule input.html -o my_schedule.png

# PDF
ulsa-schedule input.html -o schedule --pdf

# SVG (vector, scalable)
ulsa-schedule input.html -o schedule --svg

# All three at once
ulsa-schedule input.html -o schedule --pdf --svg
```

That's it. No config, no setup, no dependencies to wrestle with.

## Output Formats

| Format | Flag | Requires | Best for |
|--------|------|----------|----------|
| PNG | (default) | Pillow | Sharing, social media, quick view |
| SVG | `--svg` | (none) | Web, scalable prints, editing |
| PDF | `--pdf` | `ulsa-schedule-parser[pdf]` | Printing, formal documents |

## How It Works

```
1. HTML file → BeautifulSoup extracts the schedule table
2. Events parsed into domain model (Day, Time, Event)
3. Consecutive events with same properties merged automatically
4. Normalization: 50-minute slots, lunch row insertion, conflict detection
5. Renderers output clean, color-coded schedules
```

**Conflict detection**: overlapping classes are flagged and marked with X patterns in the output.

## Programmatic API

```python
from ulsa_schedule import (
    HtmlBs4ScheduleParser,
    PillowScheduleRenderer,
    SvgScheduleRenderer,
    RenderScheduleUseCase,
)

# Parse and render
parser = HtmlBs4ScheduleParser()
renderer = PillowScheduleRenderer()
use_case = RenderScheduleUseCase(parser, renderer)

html = open("imprimir_inscripcion.html").read()
png_bytes, view = use_case.execute(html)

# view.has_conflicts  → True if overlapping classes detected
# view.days           → [Day.MON, Day.TUE, ...]
# view.grid           → 2D list of CellRender objects
# view.time_labels    → ["08:00 am", "09:00 am", ...]

# SVG instead
from ulsa_schedule import SvgScheduleRenderer
svg_bytes = SvgScheduleRenderer().render(view)
```

## Architecture

```
ulsa_schedule/
├── domain/              # Pure business logic (no I/O)
│   ├── model.py         # Event, Day, Time, ScheduleView, CellRender
│   └── normalize.py     # Slot normalization, merge, lunch insertion
├── adapters/            # I/O adapters
│   ├── html_bs4.py      # HTML parser (BeautifulSoup)
│   ├── render_pillow.py # PNG renderer (Pillow, bundled DejaVu Sans)
│   ├── render_svg.py    # SVG renderer (zero dependencies)
│   └── render_reportlab.py  # PDF renderer (optional)
├── use_cases/
│   └── render_schedule.py   # Orchestration: parse → normalize → render
├── cli.py               # CLI entrypoint
└── assets/fonts/        # Bundled DejaVuSans.ttf
```

Clean Architecture: domain has zero dependencies on adapters. Swap renderers, add new formats, or replace the parser without touching business logic.

## CLI Reference

| Command | Description |
|---------|-------------|
| `ulsa-schedule <input>` | Render to PNG (default) |
| `ulsa-schedule <input> -o out.png` | Custom output path |
| `ulsa-schedule <input> --pdf` | Also generate PDF |
| `ulsa-schedule <input> --svg` | Also generate SVG |
| `python -m ulsa_schedule <input>` | Module execution (same behavior) |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Parse error (invalid HTML, missing table, file not found) |
| `3` | Render error (PDF dependency missing, write failure) |

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/CharFranR/ULSA-Schedule-Parser.git
cd ULSA-Schedule-Parser
pip install -e ".[pdf]"

# Run tests
python -m unittest discover -s tests -v

# Test without PDF (uninstall reportlab first)
pip uninstall reportlab
python -m unittest discover -s tests -v
```

## License

[MIT](LICENSE)

---

**Built with** Python, BeautifulSoup4, Pillow, and ReportLab.
