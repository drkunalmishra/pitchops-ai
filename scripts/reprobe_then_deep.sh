#!/usr/bin/env bash
# Probe Vertex Gemini every INTERVAL seconds (max ATTEMPTS); on success resume deep analysis at concurrency 2.
set -uo pipefail
cd "$(dirname "$0")/.."
INTERVAL="${INTERVAL:-1800}"; ATTEMPTS="${ATTEMPTS:-16}"
for i in $(seq 1 "$ATTEMPTS"); do
  out="$(uv run python -m scripts.probe_gemini 2>/dev/null | tail -1)"; rc=$?
  echo "[$(TZ=Asia/Kolkata date +%H:%M) IST] probe $i/$ATTEMPTS: $out"
  if [[ "$out" == PROBE_OK* ]]; then
    echo "[$(TZ=Asia/Kolkata date +%H:%M) IST] generation allowed again -> resuming deep analysis (concurrency 2)"
    uv run python -m jobs.deep_analysis --retry-review --concurrency 2 2>&1 | grep -v '"llm_call"' | tail -3
    exit 0
  fi
  [ "$i" -lt "$ATTEMPTS" ] && sleep "$INTERVAL"
done
echo "still blocked after $ATTEMPTS probes"; exit 2
