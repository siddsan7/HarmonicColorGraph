"""Prevent a release check from silently skipping Postgres coverage."""
import os

if not os.environ.get("TEST_DATABASE_URL"):
    raise SystemExit("TEST_DATABASE_URL is required for release integration checks; use a disposable test database.")
print("Postgres test configuration present (value hidden).")
