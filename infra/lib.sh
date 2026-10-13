#!/usr/bin/env bash
# Shared helpers for infra scripts. Reads single keys from .env WITHOUT echoing them.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

env_get() {  # env_get KEY [default]
  local v=""
  if [[ -n "${!1:-}" ]]; then v="${!1}"
  elif [[ -f "$REPO_ROOT/.env" ]]; then v="$(grep -E "^$1=" "$REPO_ROOT/.env" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"; fi
  printf '%s' "${v:-${2:-}}"
}

PROJECT_ID="$(env_get GCP_PROJECT_ID)"
REGION="$(env_get GCP_REGION us-central1)"
DATASET="$(env_get BQ_DATASET pitchops_corpus)"
FS_DB="$(env_get FIRESTORE_DATABASE pitchops)"
BUCKET="${PROJECT_ID}-pitchops"
[[ -n "$PROJECT_ID" ]] || { echo "GCP_PROJECT_ID missing" >&2; exit 1; }
gcloud config set project "$PROJECT_ID" --quiet >/dev/null 2>&1

step() { printf '\n== %s\n' "$*"; }
