"""Operational access helpers reject unrelated targets and fail cleanup safely."""

import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[3] / "scripts/paired_live_access.py"
SPEC = importlib.util.spec_from_file_location("paired_access", SOURCE)
access = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(access)


def state():
    return {
        "role": "hcg_eval_pr78_0123456789ab",
        "secret": access.SECRET,
        "repo": access.REPO,
        "policies": [["facts", "hcg_eval_pr78_0123456789ab_r"]],
        "secret_creation_intended": True,
    }


def test_pooler_scope_and_secret_encoding():
    source = "postgresql://postgres.avnxcyulznofylsnydfg:old@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
    uri = access.role_url(source, state()["role"], "special:/@password")
    assert "sslmode=require" in uri
    assert "special%3A%2F%40password" in uri
    assert "old@" not in uri
    with pytest.raises(ValueError):
        access.role_url(
            source.replace(".avnxcyulznofylsnydfg", ".otherproject"), state()["role"], "unused"
        )


@pytest.mark.parametrize(
    "key,value", [("role", "postgres"), ("secret", "ANTHROPIC_API_KEY"), ("repo", "other/repo")]
)
def test_cleanup_rejects_unrelated_scope(key, value):
    value_state = state()
    value_state[key] = value
    with pytest.raises(ValueError):
        access.validate_state(value_state)


def test_failed_database_cleanup_still_revokes_secret_and_preserves_failure(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state()))
    commands = []

    class Connection:
        autocommit = False

        def execute(self, statement, parameters=None):
            commands.append((str(statement), self.autocommit))
            return self

        def fetchone(self):
            # Role exists, then ownership check finds unexpected objects.
            return (1,)

    monkeypatch.setattr(access, "admin_connection", lambda: (Connection(), "not-used"))
    secret_exists = [True]

    def github(*args, **kwargs):
        if args[:2] == ("secret", "delete"):
            secret_exists[0] = False
            return ""
        return json.dumps([{"name": access.SECRET}] if secret_exists[0] else [])

    monkeypatch.setattr(access, "github", github)
    with pytest.raises(RuntimeError, match="cleanup_incomplete"):
        access.cleanup(path)
    assert not secret_exists[0]
    assert any("NOLOGIN" in command and autocommit for command, autocommit in commands)
    saved = json.loads(path.read_text())
    assert saved["cleanup_complete"] is False
    assert saved["cleanup_failures"] == ["database:ValueError"]
