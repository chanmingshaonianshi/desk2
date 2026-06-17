#!/usr/bin/env bash
set -euo pipefail

DEVICE_COUNT="${DEVICE_COUNT:-20}"
DURATION="${DURATION:-60}"
INTERVAL="${INTERVAL:-1}"
API_BASE="${API_BASE:-https://www.myhjmycjh.tech}"
INGEST_URL="${INGEST_URL:-http://api:8000/api/v2/ingest}"
DATA_DATE="${DATA_DATE:-$(date +%F)}"
CHECK_DEVICE_ID="${CHECK_DEVICE_ID:-device_001}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"

echo "== Miniapp frontend demo data =="
echo "Device count: $DEVICE_COUNT"
echo "Duration:     ${DURATION}s"
echo "Data date:    $DATA_DATE"
echo

cd "$DEPLOY_DIR"

echo "== 1) Stop long-running simulator if it exists =="
docker compose stop simulator >/dev/null 2>&1 || true

echo "== 2) Start backend services =="
docker compose up -d nginx api worker mongodb mysql redis

echo "== 3) Send ${DEVICE_COUNT} simulated devices =="
docker compose exec api python3 /app/simulator_client.py \
  --device-count "$DEVICE_COUNT" \
  --duration "$DURATION" \
  --interval "$INTERVAL" \
  --api-url "$INGEST_URL" \
  --no-mq \
  --insecure \
  --encrypt \
  --no-local-store

echo "== 4) Generate stats and leaderboard =="
docker compose exec api python3 scripts/daily_aggregation.py --run-now --date "$DATA_DATE"

echo
echo "== Done =="
echo "Ask the miniapp frontend to read:"
echo "Realtime:    GET $API_BASE/api/miniapp/device/$CHECK_DEVICE_ID/realtime"
echo "Stats:       GET $API_BASE/api/miniapp/user/<user_id>/stats?days=7"
echo "Leaderboard: GET $API_BASE/api/miniapp/leaderboard?date=$DATA_DATE&limit=20"
echo
echo "Required headers:"
echo "X-API-Key: myh"
echo "Authorization: Bearer <login_token>"
