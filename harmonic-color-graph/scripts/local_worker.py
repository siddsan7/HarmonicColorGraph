"""Run the temporary worker with an explicit private environment file.

No secrets are accepted on the command line or printed on failure.
Stop gracefully by creating the file supplied through --stop-file.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument(
        "--check", action="store_true", help="Read-only dependency check"
    )
    parser.add_argument("--stop-file", type=Path)
    args = parser.parse_args()
    env_file = args.env_file.resolve()
    stop_file = args.stop_file.resolve() if args.stop_file else None
    if not env_file.is_file():
        print("Private environment file is missing.", flush=True)
        return 2

    from dotenv import dotenv_values

    values = dotenv_values(env_file)
    missing = [name for name in ("DATABASE_URL", "REDIS_URL") if not values.get(name)]
    if missing:
        print("Set these names in the private environment file: " + ", ".join(missing))
        return 2
    if not values["DATABASE_URL"].startswith("postgresql+psycopg://"):
        print("DATABASE_URL must use postgresql+psycopg://.")
        return 2
    if not values["REDIS_URL"].startswith("rediss://"):
        print("Use the Upstash native TLS URL beginning rediss://.")
        return 2
    for name, value in values.items():
        if value is not None:
            os.environ[name] = value
    os.environ.setdefault("PGCONNECT_TIMEOUT", "10")

    backend = Path(__file__).resolve().parents[1] / "backend"
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    from app.db.session import create_database_engine
    from app.runtime_check import check_dependencies
    from sqlalchemy import text

    check_dependencies()
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT status, count(*) FROM hcg.jobs GROUP BY status")
            ).all()
        print("Postgres, jobs table, and Redis reachable.", flush=True)
        print("Job counts: " + str(dict(rows)), flush=True)
    finally:
        engine.dispose()
    if args.check:
        return 0
    if stop_file is None:
        print(
            "Supply --stop-file for a background worker, or use python -m app.worker."
        )
        return 2
    if stop_file.exists():
        print("Stop file exists; remove it before intentionally restarting.")
        return 2

    # Retain this socket for the process lifetime to prevent duplicate local launchers.
    with socket.socket() as singleton:
        try:
            singleton.bind(("127.0.0.1", 18769))
        except OSError:
            print("Another local worker launcher may already be running (port 18769).")
            return 2
        from app.worker import main as run_worker
        from app.worker import stop_event

        def watch_stop() -> None:
            while not stop_event.wait(1):
                if stop_file.exists():
                    stop_event.set()
                    return

        threading.Thread(target=watch_stop, daemon=True).start()
        print(f"Temporary worker starting (PID {os.getpid()}).", flush=True)
        run_worker()
        print("Temporary worker stopped gracefully.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:  # noqa: BLE001 -- redact credential-bearing startup exceptions
        # Connection exceptions can contain credential-bearing URLs.
        print(
            f"Worker startup failed ({type(exc).__name__}); check private configuration."
        )
        raise SystemExit(1) from None
