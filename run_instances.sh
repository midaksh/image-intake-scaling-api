#!/usr/bin/env bash
# Local demo: several processes on consecutive ports (no load balancer).
# Prefer docker compose: nginx on :8080 fronts api-1/api-2/api-3.
set -euo pipefail

INSTANCES="${INSTANCES:-3}"
BASE_PORT="${BASE_PORT:-8000}"
WORKERS="${WORKERS:-2}"
HOST="${HOST:-0.0.0.0}"

pids=()

cleanup() {
  if ((${#pids[@]})); then
    kill "${pids[@]}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

for ((i = 0; i < INSTANCES; i++)); do
  port=$((BASE_PORT + i))
  echo "Starting instance $((i + 1))/${INSTANCES} on ${HOST}:${port} (workers=${WORKERS})"
  uvicorn app:app --host "$HOST" --port "$port" --workers "$WORKERS" &
  pids+=("$!")
done

echo "PIDs: ${pids[*]}"
echo "Press Ctrl+C to stop all instances."
wait
