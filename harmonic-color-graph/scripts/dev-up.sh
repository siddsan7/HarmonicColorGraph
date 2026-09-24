#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env.docker ]; then
  echo "Create .env.docker from .env.docker.example before starting the stack." >&2
  exit 1
fi
docker compose up --build -d
docker compose ps
