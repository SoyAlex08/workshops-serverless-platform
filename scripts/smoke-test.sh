#!/usr/bin/env bash
# Post-deploy smoke test: hits /healthz and a public GET /workshops.
set -euo pipefail

ENV="${1:-dev}"
STACK_NAME="workshops-${ENV}"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

echo "Testing ${API_URL}healthz"
curl -sf "${API_URL}healthz" | grep -q '"status":"ok"' && echo "OK: healthz"

echo "Testing ${API_URL}workshops"
curl -sf "${API_URL}workshops" | grep -q '"items"' && echo "OK: GET /workshops"

echo "Smoke test passed for ${ENV}"
