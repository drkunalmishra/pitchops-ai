# PitchOps AI

*From 33,000 registered brokers' public content to an evidence-rated persona playbook — and from that playbook to a
compliant sales pitch in minutes.* Built for the AI Builder Cup 2026 (Future of Work & Enterprise Productivity).

**Live:** https://pitchops-ai-2026.web.app (login required) · **Demo video (3:26):** https://youtu.be/TVgMJCuMalM ([download MP4](https://github.com/drkunalmishra/pitchops-ai/releases/download/v1.0-submission/SellItR8_PitchOps_AI_Demo.mp4)) · **Team SellItR8:** Kunal Mishra, Manjeet Malwan

## What it does
1. **Persona Intelligence Engine.** It starts from the DLD broker register (33,565 brokers, 9,862 companies). It
   matched 1,141 YouTube channels and harvested 227,483 videos with the YouTube Data API. The analysis keeps only
   relevant UAE content from the last 24 months (65,898 videos):
   - Gemini Flash-Lite text-tagged 106k videos.
   - Gemini Flash watched 485 trending videos straight from the YouTube URL, with no download.
   - 16,271 comments were classified for buying intent.
   - The output is a Persona DB of 139 seller, buyer and format personas with 4,206 rated links, plus 386 company
     reports and 2,375 ranked properties.
2. **Pitch Workflow.** It runs property + persona → grounded script → UAE compliance check (Gemini explains flags
   and rewrites single lines) → human approval (frozen, audited) → video plan with a cost estimate and budget guard
   → owner approval. Then Veo 3.1 animates a fictional avatar and the property, Cloud TTS narrates and Lyria adds
   music. There are 111 scripts and 16 finished videos so far.

## Google Cloud / Firebase
| Service | Role |
|---|---|
| **Gemini on Vertex AI** | <ul><li>Video understanding from YouTube URLs (Flash).</li><li>Bulk tagging (Flash-Lite).</li><li>Persona naming, company reports, scripts and compliance explanations.</li><li>Avatar portraits (Gemini image model).</li><li>All output is JSON-schema validated.</li></ul> |
| **Veo 3.1 · Lyria · Cloud TTS** | Presenter and property clips, music beds and narration. |
| **Cloud Run** | <ul><li>FastAPI `api` service: scales to zero and verifies Firebase ID tokens.</li><li>Cloud Run Jobs + Cloud Scheduler: discover, harvest, score, comments, FinOps.</li></ul> |
| **Firestore** | Workflow state: scripts and versions, compliance, approvals, audit trail, avatars, image selections, video plans, media approvals. |
| **Firebase Hosting + Auth** | Next.js static export with `/api/**` routed to Cloud Run. Every page and call needs sign-in. |
| **BigQuery · Cloud Storage** | Analytical corpus (`pitchops_corpus`) and private media. |

**Cost guardrails** are in [ADR-002](docs/adr/ADR-002-free-trial-cost-guardrails.md):
- The whole build runs on the free trial.
- Every paid call is logged in `llm_calls`.
- The budget caps are $120 for media and $200 in total, enforced before every approval.
- The FinOps page shows spend by job and day.

Submission text and the demo-video script are in [docs/SUBMISSION.md](docs/SUBMISSION.md).

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
