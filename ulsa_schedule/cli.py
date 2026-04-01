from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .adapters.html_bs4 import HtmlBs4ScheduleParser
from .adapters.render_pillow import PillowScheduleRenderer
from .adapters.render_reportlab import ReportlabScheduleRenderer
from .domain.model import ScheduleError
from .use_cases.render_schedule import RenderScheduleUseCase


def _resolve_outputs(input_path: Path, output: str | None, pdf: bool) -> list[Path]:
    stem = input_path.stem
    if output:
        out_path = Path(output)
        suffix = out_path.suffix.lower()
        if suffix == ".png":
            return [out_path]
        if suffix == ".pdf":
            return [out_path]
        outputs = [out_path.with_suffix(".png")]
        if pdf:
            outputs.append(out_path.with_suffix(".pdf"))
        return outputs

    outputs = [Path(f"{stem}.png")]
    if pdf:
        outputs.append(Path(f"{stem}.pdf"))
    return outputs


def _write_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render ULSA schedule HTML to PNG")
    parser.add_argument("input", help="Path to ULSA enrollment HTML")
    parser.add_argument("-o", "--output", help="Output file path or base path")
    parser.add_argument("--pdf", action="store_true", help="Also generate PDF")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    try:
        html = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        return 2

    try:
        use_case = RenderScheduleUseCase(HtmlBs4ScheduleParser(), PillowScheduleRenderer())
        png_bytes, view = use_case.execute(html)
    except ScheduleError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 2

    outputs = _resolve_outputs(input_path, args.output, args.pdf)
    pdf_bytes: bytes | None = None
    if any(path.suffix.lower() == ".pdf" for path in outputs):
        try:
            pdf_bytes = ReportlabScheduleRenderer().render(view)
        except ImportError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        except Exception as exc:
            print(f"Render error: {exc}", file=sys.stderr)
            return 3

    try:
        for path in outputs:
            if path.suffix.lower() == ".png":
                _write_bytes(path, png_bytes)
            elif path.suffix.lower() == ".pdf":
                if pdf_bytes is None:
                    raise RuntimeError("PDF bytes missing")
                _write_bytes(path, pdf_bytes)
    except Exception as exc:
        print(f"Render error: {exc}", file=sys.stderr)
        return 3

    if view.has_conflicts:
        print("Warning: schedule conflicts detected", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
