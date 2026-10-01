"""The local launcher must fail closed without exposing private configuration."""

import subprocess
import sys
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[3] / "scripts" / "local_worker.py"


def run_check(tmp_path, content):
    env_file = tmp_path / "worker.env"
    env_file.write_text(content, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(LAUNCHER), "--env-file", str(env_file), "--check"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_missing_redis_does_not_fall_back_to_inherited_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("REDIS_URL", "rediss://must-not-use-inherited:password@localhost:1")
    result = run_check(tmp_path, "DATABASE_URL='postgresql+psycopg://secret@localhost/db'\n")
    assert result.returncode == 2
    assert "REDIS_URL" in result.stdout
    assert "secret" not in result.stdout + result.stderr


def test_refuses_sqlite_before_connecting(tmp_path):
    result = run_check(tmp_path, "DATABASE_URL='sqlite:///wrong.db'\nREDIS_URL='rediss://x'\n")
    assert result.returncode == 2
    assert "postgresql+psycopg" in result.stdout


def test_connection_failure_redacts_credentials(tmp_path):
    secret = "launcher-secret-must-not-appear"
    result = run_check(
        tmp_path,
        f"DATABASE_URL='postgresql+psycopg://user:{secret}@127.0.0.1:1/db?connect_timeout=2'\n"
        "REDIS_URL='rediss://localhost:1'\n",
    )
    assert result.returncode == 1
    assert "Worker startup failed" in result.stdout
    assert secret not in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
