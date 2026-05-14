#!/usr/bin/env bash
set -euo pipefail

cd /app

export SKIP_DATABASE_INIT="${SKIP_DATABASE_INIT:-1}"
export REQUIRE_DATABASE="${REQUIRE_DATABASE:-0}"
export FRAUD_API_BASE="${FRAUD_API_BASE:-http://127.0.0.1:8000}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

ST_PORT="${STREAMLIT_SERVER_PORT:-8501}"

uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 &
UV_PID=$!

cleanup() {
  kill "${UV_PID}" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if python - <<'PY'
import urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
PY
  then
    break
  fi
  sleep 1
done

exec streamlit run dashboard/streamlit_app.py \
  --server.port="${ST_PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
