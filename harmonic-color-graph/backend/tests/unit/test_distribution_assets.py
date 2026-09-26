"""The deployed wheel must include files read by path at runtime."""

import json
import subprocess
import sys
from pathlib import Path
from shutil import copy2, copytree, ignore_patterns
from zipfile import ZipFile


def test_runtime_json_files_are_in_wheel(tmp_path: Path) -> None:
    backend = Path(__file__).resolve().parents[2]
    source = tmp_path / "source"
    source.mkdir()
    copy2(backend / "pyproject.toml", source / "pyproject.toml")
    copytree(backend / "app", source / "app", ignore=ignore_patterns("__pycache__", "*.pyc"))
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheels),
            ".",
        ],
        cwd=source,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    wheel = next(wheels.glob("*.whl"))
    with ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert {
        "app/color/perceptual_params.json",
        "app/color/rules/color_rules.json",
        "app/recommend/weights/plausibility_v1.json",
        "app/theory/keys_params.json",
    } <= names


def test_vercel_function_explicitly_bundles_runtime_json() -> None:
    backend = Path(__file__).resolve().parents[2]
    config = json.loads((backend / "vercel.json").read_text(encoding="utf-8"))
    include = config["functions"]["app/main.py"]["includeFiles"]
    for asset in (
        "app/color/perceptual_params.json",
        "app/color/rules/color_rules.json",
        "app/recommend/weights/plausibility_v1.json",
        "app/theory/keys_params.json",
    ):
        assert asset in include
