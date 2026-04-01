from __future__ import annotations

import unittest

from ulsa_schedule.domain.model import CellRender, Day, ScheduleView


try:
    import reportlab  # noqa: F401
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


@unittest.skipUnless(HAS_REPORTLAB, "reportlab not installed")
class TestRenderPdf(unittest.TestCase):
    def _sample_view(self) -> ScheduleView:
        grid = [[CellRender()]]
        return ScheduleView(
            grid=grid,
            days=[Day.MON],
            time_labels=["08:00 am"],
            has_conflicts=False,
        )

    def test_pdf_bytes_signature(self) -> None:
        from ulsa_schedule.adapters.render_reportlab import ReportlabScheduleRenderer

        payload = ReportlabScheduleRenderer().render(self._sample_view())
        self.assertTrue(payload.startswith(b"%PDF"))

    def test_cli_writes_pdf(self) -> None:
        from pathlib import Path
        import subprocess
        import sys
        import tempfile

        fixtures = Path(__file__).resolve().parent / "fixtures" / "imprimir_inscripcion.html"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = Path(__file__).resolve().parents[1]
            output = temp_path / "imprimir_inscripcion.pdf"
            with subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "ulsa_schedule",
                    str(fixtures),
                    "--pdf",
                    "-o",
                    str(output),
                ],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as proc:
                stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                raise AssertionError(
                    f"CLI failed: code={proc.returncode}\nstdout={stdout!r}\nstderr={stderr!r}"
                )
            self.assertTrue(output.exists())
            payload = output.read_bytes()
            self.assertTrue(payload.startswith(b"%PDF"))


@unittest.skipIf(HAS_REPORTLAB, "reportlab installed")
class TestRenderPdfMissingDependency(unittest.TestCase):
    def test_missing_reportlab_message_mentions_pdf_extra(self) -> None:
        from ulsa_schedule.adapters.render_reportlab import ReportlabScheduleRenderer

        with self.assertRaises(ImportError) as raised:
            ReportlabScheduleRenderer().render(ScheduleView(grid=[], days=[], time_labels=[], has_conflicts=False))

        message = str(raised.exception)
        self.assertIn("ulsa_schedule[pdf]", message)
        self.assertIn(".[pdf]", message)
