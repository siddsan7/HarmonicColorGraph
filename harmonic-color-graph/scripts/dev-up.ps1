$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath ".env.docker")) {
    throw "Create .env.docker from .env.docker.example before starting the stack."
}
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose ps
exit $LASTEXITCODE
