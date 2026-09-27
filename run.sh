#!/usr/bin/env bash
# Local single instance with multiple worker processes.
# Shipping path: docker compose up --build  (nginx on :8080, three API replicas)
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-4}"

exec uvicorn app:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
