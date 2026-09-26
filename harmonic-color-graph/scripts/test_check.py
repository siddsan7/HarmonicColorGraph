"""Dependency-free regression tests for the verification wrapper."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from check import run_checks


class CheckTests(unittest.TestCase):
    def execute(self, entries):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "checks.json"
            manifest.write_text(json.dumps({"scopes": {"test": entries}}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                return run_checks(manifest, "test", root / "logs")

    def test_success(self):
        self.assertEqual(self.execute([{"name": "ok", "argv": ["{python}", "-c", "pass"]}]), 0)

    def test_defect_is_nonzero(self):
        self.assertEqual(self.execute([{"name": "defect", "argv": ["{python}", "-c", "raise SystemExit(7)"]}]), 7)

    def test_timeout(self):
        self.assertEqual(self.execute([{"name": "slow", "argv": ["{python}", "-c", "import time; time.sleep(10)"], "timeout_seconds": 0.1}]), 124)

    def test_escape_rejected(self):
        with self.assertRaises(ValueError):
            self.execute([{"name": "escape", "cwd": "..", "argv": ["{python}", "-c", "pass"]}])


if __name__ == "__main__":
    unittest.main()
