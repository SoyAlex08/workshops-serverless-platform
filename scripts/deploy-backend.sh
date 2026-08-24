#!/usr/bin/env bash
# Build + deploy the SAM backend to a given environment (dev|prod).
set -euo pipefail

ENV="${1:-dev}"
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
  echo "Usage: $0 <dev|prod>" >&2
  exit 1
fi

cd "$(dirname "$0")/../backend"

sam build
sam deploy --config-env "$ENV"
