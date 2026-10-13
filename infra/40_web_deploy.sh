#!/usr/bin/env bash
# Build the static Next.js export and deploy to Firebase Hosting (/api/** -> Cloud Run "api").
set -euo pipefail
source "$(dirname "$0")/lib.sh"
cd "$REPO_ROOT"
# Firebase web config is a public client config, but it lives only in .env -> git-ignored web/.env.production.local
uv run python -c "import json; from pitchops.config import get_settings as g; \
print('NEXT_PUBLIC_FIREBASE_CONFIG=' + json.dumps(g().firebase_config()))" > web/.env.production.local
(cd web && npm ci --no-audit --no-fund && npm run build)
firebase deploy --only hosting --project "$PROJECT_ID" --non-interactive
