#!/usr/bin/env bash
# Creates missing BigQuery tables and adds new NULLABLE columns from schemas/bq/*.json. Never drops.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python -m scripts.bq_sync
