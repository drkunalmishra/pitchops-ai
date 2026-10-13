# PitchOps AI

*From 33,000 registered brokers' public content to an evidence-rated persona playbook — and from that playbook to a
compliant sales pitch in minutes.* Built for the AI Builder Cup 2026 (Future of Work & Enterprise Productivity).

**Live:** https://pitchops-ai-2026.web.app (login required)

## Stack
Google Cloud free trial · Vertex AI Gemini (YouTube URLs analysed in place — no downloads) · BigQuery · Firestore ·
Cloud Run (FastAPI) · Firebase Hosting + Auth (Next.js static export) · YouTube Data API v3 · Cloud TTS.
See `CLAUDE.md` for the full build context and `docs/adr/` for decisions.

## Layout
`pitchops/` core library · `jobs/` job entrypoints · `services/api/` Cloud Run API · `web/` Next.js app ·
`infra/` idempotent gcloud scripts · `schemas/bq/` BigQuery schemas · `tests/` pytest.

## Run locally
```bash
uv sync
uv run pytest -q
bash infra/00_bootstrap.sh     # idempotent GCP setup + guardrail summary
bash infra/10_bigquery.sh      # create/extend tables (never drops)
uv run python -m jobs.load_registry --dry-run
bash infra/30_deploy.sh        # Cloud Run api
bash infra/40_web_deploy.sh    # Firebase Hosting
```

## Data & privacy
Raw DLD broker files stay in git-ignored `inputs/`. BigQuery stores only names, broker number, office, email
**domain** and `is_corporate_email` — no phone numbers or full emails. The repo contains only a synthetic
50-row sample (`data/sample/`). Personas are aggregated patterns, never profiles of individual brokers.
