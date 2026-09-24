"""MemoryGuard: the hard memory ceiling every pipeline stage runs under
(see pipeline/memory_guard.py). Runs the guard in real subprocesses,
since it calls `os._exit` on trip -- exercising that in-process would
kill the test runner.
"""

import subprocess
import sys

import pytest

pytest.importorskip("psutil")

TRIP_SCRIPT = """
import sys
sys.path.insert(0, {backend_dir!r})
from pipeline.memory_guard import MemoryGuard

# A cap far below what allocating a large list will need, so the guard's
# 0.05s poll interval catches it almost immediately.
with MemoryGuard(label="test-stage", max_rss_mb=20, check_interval_s=0.05):
    hog = []
    while True:
        hog.append(bytearray(10 * 1024 * 1024))  # 10 MB per chunk
"""

NO_TRIP_SCRIPT = """
import sys
sys.path.insert(0, {backend_dir!r})
from pipeline.memory_guard import MemoryGuard

with MemoryGuard(label="test-stage", max_rss_mb=4096, check_interval_s=0.05):
    total = sum(range(1_000_000))
print("done", total)
"""


def _run_script(script: str, backend_dir: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", script.format(backend_dir=backend_dir)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_guard_kills_the_process_when_rss_exceeds_the_cap(tmp_path):
    from pathlib import Path

    backend_dir = str(Path(__file__).resolve().parents[2])
    result = _run_script(TRIP_SCRIPT, backend_dir)

    assert result.returncode == 1
    assert "ABORTING" in result.stderr
    assert "test-stage" in result.stderr
    assert "cap 20 MB" in result.stderr


def test_guard_does_not_interfere_with_normal_completion():
    from pathlib import Path

    backend_dir = str(Path(__file__).resolve().parents[2])
    result = _run_script(NO_TRIP_SCRIPT, backend_dir)

    assert result.returncode == 0
    assert "done" in result.stdout
