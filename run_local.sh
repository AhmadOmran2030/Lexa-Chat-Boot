#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p data parsed_laws
if [ ! -f .env ]; then cp .env.example .env; fi

docker compose up -d --build
printf '\nLexGO is running at http://localhost:8501\n'
