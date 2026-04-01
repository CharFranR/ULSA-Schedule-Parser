# ULSA Schedule Parser

Render ULSA enrollment HTML into a readable schedule image (PNG) and optionally PDF.

## Installation

From a published package:

```bash
pip install ulsa_schedule
```

From this repository:

```bash
pip install .
```

### Optional PDF support

PDF rendering uses ReportLab and is provided as an extra.

```bash
pip install ulsa_schedule[pdf]
```

Or from the repo:

```bash
pip install '.[pdf]'
```

## Usage

CLI entry point:

```bash
ulsa-schedule path/to/imprimir_inscripcion.html -o schedule.png
```

To also generate a PDF:

```bash
ulsa-schedule path/to/imprimir_inscripcion.html -o schedule --pdf
```

Module execution (same behavior):

```bash
python -m ulsa_schedule path/to/imprimir_inscripcion.html -o schedule.png
```
