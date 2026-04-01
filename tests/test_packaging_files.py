from __future__ import annotations

import unittest
from pathlib import Path


class TestPackagingFiles(unittest.TestCase):
    def test_packaging_artifacts_exist(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        self.assertTrue((repo_root / "pyproject.toml").exists())
        self.assertTrue((repo_root / "MANIFEST.in").exists())
        self.assertTrue(
            (repo_root / "ulsa_schedule" / "assets" / "fonts" / "DejaVuSans.ttf").exists()
        )
