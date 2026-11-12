"""Model-free corpus identity and local-server readiness checks."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx
import psycopg


def snapshot():
    uri = os.environ["HCG_PAIRED_EVAL_DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(uri, connect_timeout=15) as connection:
        connection.execute("set transaction read only")
        rows = connection.execute(
            "select version, loaded_at, manifest from hcg.corpus_versions where active"
        ).fetchall()
        if len(rows) != 1 or rows[0][0] != "cv-2026-10-b":
            raise ValueError("active_corpus_mismatch")
        version, loaded_at, manifest = rows[0]
        return {
            "version": version,
            "loaded_at": loaded_at.isoformat(),
            "manifest_sha256": hashlib.sha256(
                json.dumps(manifest, sort_keys=True, default=str).encode()
            ).hexdigest(),
            "scope": "active corpus version/load/manifest; not a full database row checksum",
        }


def wait_servers():
    for _ in range(30):
        try:
            for port in [8081, 8082]:
                response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2)
                response.raise_for_status()
            print("Both model-free local health endpoints are ready.")
            return
        except httpx.HTTPError:
            time.sleep(1)
    raise ValueError("servers_not_ready")


def check_models(output):
    from anthropic import Anthropic

    rows = []
    with Anthropic(max_retries=0, timeout=20) as client:
        for name in ("claude-haiku-4-5-20251001", "claude-sonnet-5"):
            model = client.models.retrieve(name)
            if model.id != name:
                raise ValueError("configured_model_is_alias_resolve_before_paid_run")
            rows.append({"requested_id": name, "resolved_id": model.id})
    output.write_text(json.dumps({"models": rows, "paid_requests": 0}, indent=2) + "\n")
    print("Both model IDs resolved through the model-free catalog endpoint.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--wait-servers", action="store_true")
    parser.add_argument("--check-models", action="store_true")
    args = parser.parse_args()
    try:
        if args.wait_servers:
            wait_servers()
        elif args.check_models:
            check_models(args.output)
        else:
            value = snapshot()
            if args.compare and value != json.loads(args.compare.read_text()):
                raise ValueError("corpus_identity_changed")
            args.output.write_text(json.dumps(value, indent=2) + "\n")
            print("Corpus identity verified; no model request made.")
    except Exception as exc:  # noqa: BLE001 - redact credentials and finish cleanup
        print(json.dumps({"preflight_failed": type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
