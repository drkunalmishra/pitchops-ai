# P1 — GCP Foundation, Registry Load, Web Shell · v3 (Free Trial)

**When:** Tue 13 Oct, after completing `00_SETUP_AND_COST_GUARDRAILS.md` · **Time box:** about 3–4 hours of Claude Code

Paste everything inside the box into Claude Code (run from the repo root, which contains `CLAUDE.md`, `docs/`, `inputs/` and `.env`).

````text
You are building Phase P1 of PitchOps AI. Read CLAUDE.md (v3) fully first, especially §2 rule 7 (COST GUARDRAILS). We are on a Google Cloud FREE TRIAL: never use AI Studio keys, never create VMs/GPUs/Cloud SQL/GKE, keep Cloud Run at min-instances 0.

GOAL
Repo skeleton, idempotent GCP bootstrap, BigQuery schema, PII-minimized registry load, Vertex Gemini + YouTube smoke tests, deployed API + web shell with login. Keep it lean: time is short.

INPUTS
- .env: GCP_PROJECT_ID, GCP_REGION=us-central1, YOUTUBE_API_KEY, GEMINI_MODEL_FLASH, GEMINI_BUDGET_USD, FIREBASE_CONFIG_JSON, CONTACT_EMAIL
- Local auth: gcloud ADC already logged in.
- inputs/brokers_clean.csv (name_en, name_ar, broker_number, office_name_en, office_name_ar, email, phone, email_domain, is_corporate_email, company_key)
- inputs/companies_seed.csv (company_id, company_key, office_names_en, office_name_ar, broker_count, corporate_domains, primary_domain, discovery_tier)

TASKS
1. Skeleton per CLAUDE.md §4: .gitignore (inputs/, .env, *.xls, *.xlsx, data/private/, exports/), .env.example, README stub, NOTICE.md, pyproject.toml (uv, Python 3.12; google-cloud-bigquery, google-cloud-firestore, google-cloud-storage, google-cloud-secret-manager, google-genai, httpx, rapidfuzz, pydantic-settings, tenacity, fastapi, uvicorn, firebase-admin; dev: ruff, pytest, mypy), pitchops/config.py.

2. infra/00_bootstrap.sh (idempotent, set -euo pipefail):
   - Enable APIs: run, cloudbuild, artifactregistry, cloudscheduler, cloudtasks, bigquery, firestore, storage, secretmanager, aiplatform, texttospeech, youtube, iamcredentials, logging, monitoring.
   - Artifact Registry repo "pitchops" (docker, us-central1).
   - Service accounts + roles exactly as in docs: sa-jobs (bigquery.dataEditor, bigquery.jobUser, aiplatform.user, datastore.user, storage.objectAdmin on bucket, secretmanager.secretAccessor on YOUTUBE_API_KEY), sa-api (datastore.user, bigquery.dataViewer, bigquery.jobUser, aiplatform.user, storage.objectViewer, cloudtasks.enqueuer), sa-scheduler (run.invoker).
   - Bucket ${PROJECT_ID}-pitchops: us-central1, uniform access, public access prevention, lifecycle delete tmp/ after 3 days.
   - BigQuery dataset pitchops_corpus in us-central1. Firestore Native us-central1 if missing.
   - Secret YOUTUBE_API_KEY created from .env value (read without echoing).
   - Print a GUARDRAIL SUMMARY at the end: billing account type (gcloud billing projects describe), confirms no VMs/SQL instances exist, Cloud Run defaults.

3. schemas/bq/*.json for every table in CLAUDE.md §5 (partition video_metrics_daily by snapshot_date; llm_calls/quota_ledger by DATE(ts); cluster by key). infra/10_bigquery.sh creates missing tables, adds new NULLABLE columns, never drops.

4. jobs/load_registry.py: read CSVs, DROP phone and full email, keep email_domain + is_corporate_email, join company_id via company_key, validate unique broker_number, load brokers + companies (WRITE_TRUNCATE). Write data/sample/brokers_sample.csv (50 synthetic rows, *.test domains). Assert via INFORMATION_SCHEMA that no phone/email column exists.

5. pitchops/youtube/quota.py — QuotaLedger: COST {search.list:100, channels.list:1, playlistItems.list:1, videos.list:1, commentThreads.list:1}; day key = date in America/Los_Angeles; can_spend() reads today's sum (cache, refresh every 50 calls); cap YT_DAILY_UNIT_CAP=9000; spend() buffers and flushes to quota_ledger. Unit tests with a fake store.

6. pitchops/gemini/ — Vertex client + GeminiBudget:
   - client.py: google-genai Client(vertexai=True, project, location=us-central1). generate_json(model, contents, schema, media_resolution='low') with retries on 429/5xx, schema validation, and one repair retry.
   - Cost estimate per call from usage_metadata (token counts) × price table in config (PRICE_PER_MTOK_IN/OUT per model, editable; document that it is an estimate). Log every call to llm_calls.
   - budget.py: GeminiBudget.check() — reads total and today's cost_usd_est; raises BudgetExhausted at GEMINI_BUDGET_USD (60) / GEMINI_DAILY_USD (25). Unit tests.

7. Smoke tests (scripts/smoke/) → results in docs/adr/ADR-001-vertex-youtube.md:
   a. Vertex Gemini Flash with a public Dubai real-estate YouTube Short URL as file_data(file_uri, mime 'video/*'): 3-sentence summary + on-screen text list. Record tokens, est. cost, latency.
   b. Same with a long-form video using video_metadata start_offset/end_offset (0–120s): does Vertex accept offsets for YouTube URLs? Record yes/no.
   c. Structured JSON output with GEMINI_MODEL_LITE.
   d. Vertex text embeddings (EMBEDDING_MODEL_ID): record dimension.
   e. YouTube Data API channels.list for one handle (1 unit, logged).
   f. Cloud TTS: synthesize 1 sentence (en-US Neural2 or Studio voice), save to gs://…/tmp/.
   g. Firestore write/read/delete test doc.

8. services/api (FastAPI): /healthz, /readyz (BQ + Firestore), GET /v1/corpus/stats (counts from brokers, companies, channels, videos; quota used today; Gemini spend estimate). Verify Firebase ID tokens on /v1/*. Dockerfile. infra/30_deploy.sh: Cloud Build → Cloud Run service "api" (sa-api, min 0, max 2, 512Mi, concurrency 40).

9. web/ — Next.js + TS + Tailwind, output:'export'. Firebase Auth login (email/password + Google). Dashboard page calling /api/v1/corpus/stats with tiles (brokers, companies, channels, videos, shorts, quota today, Gemini spend). Clean professional look (deep navy + teal, Inter). firebase.json: Hosting serves web/out, rewrite /api/** → Cloud Run service "api" in us-central1. Deploy with firebase deploy --only hosting.

10. .github/workflows/ci.yml: ruff + mypy + pytest + guard that fails on: yt_dlp|pytube|youtube-dl|generativelanguage.googleapis.com|GEMINI_API_KEY|AISTUDIO (AI Studio usage forbidden on trial).

11. ADRs: ADR-001 Vertex + YouTube (smoke results), ADR-002 free-trial cost guardrails, ADR-003 PII minimization.

ACCEPTANCE TESTS (print Phase Report)
- Re-running infra/00 and infra/10 is a no-op; guardrail summary printed (no VMs/SQL; Cloud Run min 0).
- All §5 tables exist; brokers ≈ 33.5k, companies ≈ 9.8k; no phone/email columns.
- Smoke tests a–g recorded; ADR-001 states clearly whether YouTube URLs and offsets work on Vertex.
- https://<project>.web.app: login works; dashboard shows counts; /api/v1/corpus/stats without token → 401.
- pytest + CI green; inputs/ and .env ignored; no secrets in git.
- Report Gemini spend estimate so far (should be < $0.50).
- Do NOT start P2 work.
````

## Bring back after P1
- The Phase Report.
- The smoke-test answers: YouTube URL works on Vertex (yes/no); offsets work (yes/no).
- If it's still before about 23:00 IST, run P2 straight away. Today's YouTube quota hasn't been used yet.
