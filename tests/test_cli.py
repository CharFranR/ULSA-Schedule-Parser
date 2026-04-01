from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ulsa_schedule import cli


class TestCli(unittest.TestCase):
    def test_cli_happy_path_writes_png(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        fixture = Path(__file__).resolve().parent / "fixtures" / "imprimir_inscripcion.html"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out.png"
            with subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "ulsa_schedule",
                    str(fixture),
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

    def test_cli_missing_table_exits_2(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        html = "<html><body><table id='other'></table></body></html>"
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.html"
            input_path.write_text(html, encoding="utf-8")
            with subprocess.Popen(
                [sys.executable, "-m", "ulsa_schedule", str(input_path)],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as proc:
                stdout, stderr = proc.communicate()
            self.assertEqual(proc.returncode, 2, msg=stderr.decode("utf-8"))

    def test_cli_conflict_warning_exits_0(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        html = """
        <html>
          <body>
            <table id="tableCurso">
              <tbody>
                <tr>
                  <td>CODE1</td>
                  <td>Subject 1</td>
                  <td>4</td>
                  <td>
                    <span class="label label-success"><b>Gpo 1</b></span><br>
                    Lu 08:00 am - 09:40 am [ A1 ]<br>
                  </td>
                  <td>Teacher 1</td>
                </tr>
                <tr>
                  <td>CODE2</td>
                  <td>Subject 2</td>
                  <td>4</td>
                  <td>
                    <span class="label label-success"><b>Gpo 1</b></span><br>
                    Lu 08:00 am - 09:40 am [ B1 ]<br>
                  </td>
                  <td>Teacher 2</td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.html"
            input_path.write_text(html, encoding="utf-8")
            output = Path(temp_dir) / "conflict.png"
            with subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "ulsa_schedule",
                    str(input_path),
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
            self.assertIn("Warning: schedule conflicts detected", stderr.decode("utf-8"))
            self.assertTrue(output.exists())

    def test_cli_main_programmatic_invocation(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "imprimir_inscripcion.html"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out.png"
            exit_code = cli.main([str(fixture), "-o", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
