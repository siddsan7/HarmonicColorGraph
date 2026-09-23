# Standard Check Gate (feature-specs/v2-implementation-plan.md §0.4).
# Usage: scripts\check.ps1 [static|test|build|all]   (default: all)
param(
    [ValidateSet("static", "test", "build", "all")]
    [string]$Command = "all"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $RepoRoot "backend"
$script:Failed = $false

function Step($Name) {
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
}

function Check-Exit($Name) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        $script:Failed = $true
    }
}

function Run-Static {
    Push-Location $Backend
    try {
        Step "ruff check backend"
        py -3.12 -m ruff check .
        Check-Exit "ruff check"

        Step "ruff format --check backend"
        py -3.12 -m ruff format --check .
        Check-Exit "ruff format --check"
    } finally {
        Pop-Location
    }

    Push-Location $RepoRoot
    try {
        Step "npm run lint"
        npm run lint
        Check-Exit "npm run lint"

        Step "npm run typecheck"
        npm run typecheck
        Check-Exit "npm run typecheck"
    } finally {
        Pop-Location
    }
}

function Run-Test {
    Push-Location $Backend
    try {
        Step "pytest -q (unit)"
        py -3.12 -m pytest -q
        Check-Exit "pytest unit"

        Step "pytest -q -m pg (Postgres integration)"
        py -3.12 -m pytest -q -m pg
        $pgExit = $LASTEXITCODE
        if ($pgExit -ne 0 -and $pgExit -ne 5) {
            Write-Host "FAILED: pytest -m pg (exit $pgExit)" -ForegroundColor Red
            $script:Failed = $true
        } elseif ($pgExit -eq 5) {
            Write-Host "pytest -m pg: no tests collected yet (expected before F05)" -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }

    Push-Location $RepoRoot
    try {
        Step "npm test"
        npm test
        Check-Exit "npm test"
    } finally {
        Pop-Location
    }
}

function Run-Build {
    Push-Location $RepoRoot
    try {
        Step "npm run build"
        npm run build
        Check-Exit "npm run build"
    } finally {
        Pop-Location
    }

    Push-Location $Backend
    try {
        Step 'python -c "import app.main"'
        py -3.12 -c "import app.main"
        Check-Exit "import app.main"
    } finally {
        Pop-Location
    }
}

switch ($Command) {
    "static" { Run-Static }
    "test"   { Run-Test }
    "build"  { Run-Build }
    "all"    { Run-Static; Run-Test; Run-Build }
}

Write-Host ""
if ($script:Failed) {
    Write-Host "check ${Command}: FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "check ${Command}: OK" -ForegroundColor Green
    exit 0
}
