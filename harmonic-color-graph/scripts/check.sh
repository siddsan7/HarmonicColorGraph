#!/usr/bin/env bash
# Standard Check Gate (feature-specs/v2-implementation-plan.md §0.4).
# Usage: scripts/check.sh [static|test|build|all]   (default: all)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"

# Resolve a working Python interpreter. On Windows, a bare `python`/`python3`
# on PATH can silently be the non-functional Microsoft Store alias even when
# a real interpreter is installed, so probe candidates by running them
# instead of just checking PATH membership.
PYTHON_CMD=()
if [ -n "${PYTHON:-}" ]; then
  # shellcheck disable=SC2206
  PYTHON_CMD=($PYTHON)
else
  for candidate in "python3" "python"; do
    if "$candidate" --version >/dev/null 2>&1; then
      PYTHON_CMD=("$candidate")
      break
    fi
  done
  if [ "${#PYTHON_CMD[@]}" -eq 0 ] && command -v py >/dev/null 2>&1 && py -3.12 --version >/dev/null 2>&1; then
    PYTHON_CMD=(py -3.12)
  fi
fi
if [ "${#PYTHON_CMD[@]}" -eq 0 ]; then
  echo "No working Python interpreter found (tried python3, python, py -3.12)." >&2
  echo "Set \$PYTHON to an explicit interpreter and retry." >&2
  exit 1
fi

FAILED=0

step() { echo ""; echo "==> $1"; }

check_exit() {
  if [ "$1" -ne 0 ]; then
    echo "FAILED: $2 (exit $1)"
    FAILED=1
  fi
}

run_static() {
  (cd "$BACKEND" && step "ruff check backend" && "${PYTHON_CMD[@]}" -m ruff check .)
  check_exit $? "ruff check"

  (cd "$BACKEND" && step "ruff format --check backend" && "${PYTHON_CMD[@]}" -m ruff format --check .)
  check_exit $? "ruff format --check"

  (cd "$REPO_ROOT" && step "npm run lint" && npm run lint)
  check_exit $? "npm run lint"

  (cd "$REPO_ROOT" && step "npm run typecheck" && npm run typecheck)
  check_exit $? "npm run typecheck"
}

run_test() {
  (cd "$BACKEND" && step "pytest -q (unit)" && "${PYTHON_CMD[@]}" -m pytest -q)
  check_exit $? "pytest unit"

  step "pytest -q -m pg (Postgres integration)"
  (cd "$BACKEND" && "${PYTHON_CMD[@]}" -m pytest -q -m pg)
  pg_exit=$?
  if [ "$pg_exit" -ne 0 ] && [ "$pg_exit" -ne 5 ]; then
    echo "FAILED: pytest -m pg (exit $pg_exit)"
    FAILED=1
  elif [ "$pg_exit" -eq 5 ]; then
    echo "pytest -m pg: no tests collected yet (expected before F05)"
  fi

  (cd "$REPO_ROOT" && step "npm test" && npm test)
  check_exit $? "npm test"
}

run_build() {
  (cd "$REPO_ROOT" && step "npm run build" && npm run build)
  check_exit $? "npm run build"

  (cd "$BACKEND" && step 'python -c "import app.main"' && "${PYTHON_CMD[@]}" -c "import app.main")
  check_exit $? "import app.main"
}

CMD="${1:-all}"
case "$CMD" in
  static) run_static ;;
  test) run_test ;;
  build) run_build ;;
  all) run_static; run_test; run_build ;;
  *)
    echo "Usage: $0 {static|test|build|all}"
    exit 2
    ;;
esac

echo ""
if [ "$FAILED" -ne 0 ]; then
  echo "check $CMD: FAILED"
  exit 1
else
  echo "check $CMD: OK"
  exit 0
fi
