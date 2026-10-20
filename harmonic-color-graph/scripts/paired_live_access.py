"""Temporary, restricted database access for one reviewed paired Actions run.

Credentials stay in process memory and GitHub's secret store. This operational
helper never prints a DSN/password or changes production routing or app settings.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import psycopg
from dotenv import dotenv_values
from psycopg import sql

REPO = "siddsan7/HarmonicColorGraph"
SECRET = "HCG_PAIRED_EVAL_DATABASE_URL"
READ_TABLES = (
    "ngram_discount_stats",
    "color_norms",
    "color_profiles",
    "embeddings",
    "ngram_histories",
    "pattern_examples",
    "transition_examples",
    "edges",
    "chords",
    "roman_chords",
    "songs",
    "progressions",
    "progression_chords",
    "transitions",
    "genres",
    "sections",
    "theory_labels",
    "transition_theory_labels",
    "source_metadata",
    "corpus_versions",
    "contexts",
    "song_refs",
    "relationship_types",
    "patterns",
    "facts",
    "nodes",
    "edges_compact",
    "ai_query_logs",
    "rate_limits",
)
AUDIT_UPDATES = (
    "parsed_intent",
    "route",
    "tools",
    "final",
    "validation_errors",
    "error_category",
    "model",
    "model_usage",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "latency_ms",
)


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def github(*args, secret_input=None):
    environment = dict(os.environ)
    environment.pop("GH_DEBUG", None)
    result = subprocess.run(
        ["gh", *args, "--repo", REPO],
        input=secret_input,
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("github_operation_failed")
    return result.stdout


def admin_connection():
    values = dotenv_values(Path.home() / ".hcg/worker.env")
    uri = values["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(uri, connect_timeout=15), uri


def role_url(uri, role, password):
    parts = urlsplit(uri)
    if not parts.hostname or not parts.hostname.endswith(".pooler.supabase.com"):
        raise ValueError("expected_existing_session_pooler")
    if not (parts.username or "").endswith(".avnxcyulznofylsnydfg"):
        raise ValueError("unexpected_project")
    parameters = dict(parse_qsl(parts.query))
    parameters["sslmode"] = "require"
    authority = (
        quote(role + ".avnxcyulznofylsnydfg", safe="")
        + ":"
        + quote(password, safe="")
        + "@"
        + parts.hostname
        + (":" + str(parts.port) if parts.port else "")
    )
    return urlunsplit(("postgresql", authority, parts.path, urlencode(parameters), ""))


def validate_state(state):
    if not re.fullmatch(r"hcg_eval_pr78_[0-9a-f]{12}", state["role"]):
        raise ValueError("unexpected_role")
    if state["secret"] != SECRET or state["repo"] != REPO:
        raise ValueError("unexpected_secret_scope")
    for table, name in state["policies"]:
        if table not in (*READ_TABLES, "api_request_logs") or not name.startswith(
            state["role"] + "_"
        ):
            raise ValueError("unexpected_policy_scope")


def provision(path):
    if path.exists():
        raise ValueError("state_exists_cleanup_or_reconcile_first")
    existing = json.loads(github("secret", "list", "--json", "name"))
    if any(row["name"] == SECRET for row in existing):
        raise ValueError("refuse_to_overwrite_existing_secret")
    role = "hcg_eval_pr78_" + secrets.token_hex(6)
    nonce = secrets.token_hex(24)
    ip_hash = hmac.new(nonce.encode(), b"127.0.0.1", hashlib.sha256).hexdigest()
    state = {
        "repo": REPO,
        "secret": SECRET,
        "role": role,
        "ip_nonce": nonce,
        "ip_hash": ip_hash,
        "policies": [],
        "provisioned": False,
        "secret_created": False,
    }
    password = secrets.token_urlsafe(40)
    connection, admin_uri = admin_connection()
    dsn = role_url(admin_uri, role, password)
    with connection:
        now = connection.execute("select now()").fetchone()[0]
        state.update(
            cutoff=now.isoformat(), expires_at=(now + timedelta(hours=1)).isoformat()
        )
        save(path, state)
        if connection.execute("select hcg.v()").fetchone()[0] != "cv-2026-10-b":
            raise ValueError("corpus_mismatch")
        if connection.execute(
            "select has_schema_privilege('public','public','CREATE')"
        ).fetchone()[0]:
            raise ValueError("public_create_not_allowed")
        connection.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN PASSWORD {} VALID UNTIL {} CONNECTION LIMIT 4 "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
            ).format(
                sql.Identifier(role),
                sql.Literal(password),
                sql.Literal(state["expires_at"]),
            )
        )
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA hcg,extensions TO {}").format(
                sql.Identifier(role)
            )
        )

        def policy(table, suffix, command, expression):
            name = role + "_" + suffix
            tail = (
                sql.SQL("WITH CHECK ({})")
                if command == "INSERT"
                else sql.SQL("USING ({})")
            )
            clause = tail.format(expression)
            if command == "UPDATE":
                clause += sql.SQL(" WITH CHECK ({})").format(expression)
            connection.execute(
                sql.SQL("CREATE POLICY {} ON hcg.{} FOR {} TO {} ").format(
                    sql.Identifier(name),
                    sql.Identifier(table),
                    sql.SQL(command),
                    sql.Identifier(role),
                )
                + clause
            )
            state["policies"].append([table, name])

        for table in READ_TABLES:
            connection.execute(
                sql.SQL("GRANT SELECT ON hcg.{} TO {}").format(
                    sql.Identifier(table), sql.Identifier(role)
                )
            )
            expression = (
                sql.SQL("true")
                if table != "rate_limits"
                else sql.SQL("key={}").format(sql.Literal("ai:" + ip_hash))
            )
            policy(table, "r", "SELECT", expression)
        audit = sql.SQL("ip_hash={} AND created_at>={}").format(
            sql.Literal(ip_hash), sql.Literal(now)
        )
        rate = sql.SQL("key={}").format(sql.Literal("ai:" + ip_hash))
        for table, expression in (("ai_query_logs", audit), ("rate_limits", rate)):
            connection.execute(
                sql.SQL("GRANT INSERT ON hcg.{} TO {}").format(
                    sql.Identifier(table), sql.Identifier(role)
                )
            )
            columns = AUDIT_UPDATES if table == "ai_query_logs" else ("count",)
            connection.execute(
                sql.SQL("GRANT UPDATE ({}) ON hcg.{} TO {}").format(
                    sql.SQL(",").join(map(sql.Identifier, columns)),
                    sql.Identifier(table),
                    sql.Identifier(role),
                )
            )
            policy(table, "i", "INSERT", expression)
            policy(table, "u", "UPDATE", expression)
        connection.execute(
            sql.SQL("GRANT INSERT ON hcg.api_request_logs TO {}").format(
                sql.Identifier(role)
            )
        )
        connection.execute(
            sql.SQL("GRANT SELECT (id) ON hcg.api_request_logs TO {}").format(
                sql.Identifier(role)
            )
        )
        policy(
            "api_request_logs",
            "i",
            "INSERT",
            sql.SQL(
                "occurred_at>={} AND route IN ('/__paired_identity','/v2/ai/query')"
            ).format(sql.Literal(now)),
        )
        policy(
            "api_request_logs",
            "r",
            "SELECT",
            sql.SQL(
                "occurred_at>={} AND route IN ('/__paired_identity','/v2/ai/query')"
            ).format(sql.Literal(now)),
        )
        sequence = connection.execute(
            "select pg_get_serial_sequence('hcg.api_request_logs','id')"
        ).fetchone()[0]
        if sequence:
            schema, name = sequence.split(".", 1)
            if schema != "hcg" or name != "api_request_logs_id_seq":
                raise ValueError("unexpected_metrics_sequence")
            connection.execute(
                sql.SQL("GRANT USAGE ON SEQUENCE {}.{} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(name), sql.Identifier(role)
                )
            )
        # Persist the exact cleanup inventory before the database commit.
        save(path, state)
    connection.close()
    state["provisioned"] = True
    save(path, state)
    try:
        with psycopg.connect(dsn, connect_timeout=15) as restricted:
            assert restricted.execute("select hcg.v()").fetchone()[0] == "cv-2026-10-b"
            assert (
                restricted.execute(
                    "select count(*) from hcg.corpus_versions where active"
                ).fetchone()[0]
                == 1
            )
            assert not restricted.execute(
                "select has_schema_privilege(current_user,'hcg','CREATE')"
            ).fetchone()[0]
            assert not restricted.execute(
                "select has_table_privilege(current_user,'hcg.facts','UPDATE')"
            ).fetchone()[0]
            for table in READ_TABLES:
                if table not in {"ai_query_logs", "rate_limits"}:
                    assert not restricted.execute(
                        "select has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE')",
                        ("hcg." + table,),
                    ).fetchone()[0]
            assert not restricted.execute(
                "select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                "where n.nspname in ('hcg','public','extensions') and p.prosecdef "
                "and has_function_privilege(current_user,p.oid,'EXECUTE')"
            ).fetchone()[0]
            with restricted.transaction(force_rollback=True):
                changed = restricted.execute(
                    "update hcg.ai_query_logs set cost_usd=cost_usd "
                    "where query_id='3ab8e21e-973e-4060-9f99-f8669344d4aa' returning query_id"
                ).fetchall()
                assert changed == [], "other audit identities must be immutable"
                probe_id = uuid.uuid4()
                restricted.execute(
                    "insert into hcg.ai_query_logs(query_id,ip_hash,user_query) values(%s,%s,%s)",
                    (probe_id, ip_hash, "model-free access preflight"),
                )
                assert (
                    restricted.execute(
                        "update hcg.ai_query_logs set cost_usd=0 "
                        "where query_id=%s returning query_id",
                        (probe_id,),
                    ).fetchone()[0]
                    == probe_id
                )
                restricted.execute(
                    "insert into hcg.rate_limits(key,window_start,count) values(%s,now(),1) "
                    "on conflict(key,window_start) do update set count=hcg.rate_limits.count+1",
                    ("ai:" + ip_hash,),
                )
                restricted.execute(
                    "insert into hcg.api_request_logs"
                    "(trace_id,request_id,route,method,status,latency_ms) "
                    "values(%s,%s,'/__paired_identity','GET',200,0) returning id",
                    ("0" * 32, probe_id),
                ).fetchone()
            state["restricted_connection_verified"] = True
        state["secret_creation_intended"] = True
        save(path, state)
        github(
            "secret",
            "set",
            SECRET,
            secret_input=dsn.replace("postgresql://", "postgresql+psycopg://", 1),
        )
        state["secret_created"] = True
        save(path, state)
    except Exception:
        cleanup(path)
        raise
    print(json.dumps({key: value for key, value in state.items() if key != "ip_nonce"}))


def cleanup(path):
    state = json.loads(path.read_text(encoding="utf-8"))
    validate_state(state)
    failures = []
    role_absent = False
    secret_absent = False
    try:
        connection, _ = admin_connection()
        connection.autocommit = True
        role = state["role"]
        exists = connection.execute(
            "select 1 from pg_roles where rolname=%s", (role,)
        ).fetchone()
        if exists:
            connection.execute(
                sql.SQL("ALTER ROLE {} NOLOGIN").format(sql.Identifier(role))
            )
            connection.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where usename=%s and pid<>pg_backend_pid()",
                (role,),
            )
            owned = connection.execute(
                "select count(*) from pg_class "
                "where relowner=(select oid from pg_roles where rolname=%s)",
                (role,),
            ).fetchone()[0]
            if owned:
                raise ValueError("unexpected_owned_objects_manual_review_required")
            with connection.transaction():
                for table, policy in state["policies"]:
                    connection.execute(
                        sql.SQL("DROP POLICY IF EXISTS {} ON hcg.{}").format(
                            sql.Identifier(policy), sql.Identifier(table)
                        )
                    )
                connection.execute(
                    sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role))
                )
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
        role_absent = not connection.execute(
            "select 1 from pg_roles where rolname=%s", (role,)
        ).fetchone()
        connection.close()
    except Exception as exc:  # noqa: BLE001 - redact credentials and finish cleanup
        failures.append("database:" + type(exc).__name__)
    # Delete only this run's new secret; never replace an existing secret.
    try:
        existing = json.loads(github("secret", "list", "--json", "name"))
        if state.get("secret_creation_intended") and any(
            row["name"] == SECRET for row in existing
        ):
            github("secret", "delete", SECRET)
        existing = json.loads(github("secret", "list", "--json", "name"))
        secret_absent = not any(row["name"] == SECRET for row in existing)
    except Exception as exc:  # noqa: BLE001 - redact credentials and finish cleanup
        failures.append("github:" + type(exc).__name__)
    state["cleanup_complete"] = role_absent and secret_absent
    state["cleanup_failures"] = failures
    save(path, state)
    print(
        json.dumps(
            {
                "cleanup_complete": state["cleanup_complete"],
                "role": state["role"],
                "secret_absent": secret_absent,
            }
        )
    )
    if not state["cleanup_complete"]:
        raise RuntimeError("cleanup_incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "cleanup"))
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        (provision if args.action == "provision" else cleanup)(args.state)
    except Exception as exc:  # noqa: BLE001 - redact credentials and finish cleanup
        # Provider/driver errors can contain credentials. Report only the class.
        print(json.dumps({"operation_failed": type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
