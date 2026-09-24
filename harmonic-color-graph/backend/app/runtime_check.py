"""Container health probes using the same settings as the application."""

import sys
from urllib.request import urlopen

from sqlalchemy import text

from app.core.redis import ping_redis
from app.db.session import create_database_engine


def check_dependencies() -> None:
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    finally:
        engine.dispose()
    ping_redis()


def check_api() -> None:
    for path in ("/health", "/health/db", "/health/redis"):
        with urlopen(f"http://127.0.0.1:8000{path}", timeout=3) as response:
            if response.status != 200:
                raise RuntimeError(f"{path} returned HTTP {response.status}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"api", "dependencies"}:
        raise SystemExit("usage: python -m app.runtime_check [api|dependencies]")
    if sys.argv[1] == "api":
        check_api()
    else:
        check_dependencies()


if __name__ == "__main__":
    main()
