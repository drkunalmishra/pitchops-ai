#!/usr/bin/env bash
# Fails if code references YouTube downloaders or Google AI Studio / Gemini Developer API (forbidden on the trial).
set -euo pipefail
cd "$(dirname "$0")/.."
PATTERN='yt_dlp|yt-dlp|pytube|youtube-dl|generativelanguage\.googleapis\.com|GEMINI_API_KEY|AISTUDIO'
HITS="$(git ls-files -- '*.py' '*.ts' '*.tsx' '*.js' '*.mjs' '*.sh' '*.toml' '*.json' '*.yml' '*.yaml' 'Dockerfile' '**/Dockerfile' \
  | grep -vE '^(scripts/guard_forbidden\.sh|\.github/workflows/ci\.yml)$' \
  | xargs grep -nIiE "$PATTERN" || true)"
if [[ -n "$HITS" ]]; then echo "FORBIDDEN references found:"; echo "$HITS"; exit 1; fi
if git ls-files | grep -qE '(^|/)\.env$|^inputs/|\.xlsx?$'; then echo "secret/private file tracked by git"; exit 1; fi
echo "guard: clean"
