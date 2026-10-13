# ADR-002 — Free-trial cost guardrails

**Status:** Accepted · **Date:** 13 Oct 2026

## Context
The project runs on the Google Cloud **Free Trial** ($300 credit). The account must never be upgraded, and nothing may
create charges outside the credit (AI Studio / Gemini Developer API is *not* covered by trial credit).

## Decisions
1. **Gemini only through Vertex AI** (`genai.Client(vertexai=True)`, ADC/service accounts). No API keys for Gemini.
   CI (`scripts/guard_forbidden.sh`) fails on `generativelanguage.googleapis.com`, `GEMINI_API_KEY`, `AISTUDIO`
   and on any YouTube downloader (`yt_dlp`, `pytube`, `youtube-dl`).
2. **GeminiBudget** (`pitchops/gemini/budget.py`) runs before every call: stops at `GEMINI_BUDGET_USD` (60) total and
   `GEMINI_DAILY_USD` (25) per IST day, using `llm_calls.cost_usd_est`. Every call (including failures) is logged to
   `llm_calls`. Prices in `pitchops/config.py` are deliberately conservative and overridable via `PRICE_PER_MTOK_JSON`.
3. **Flash-class models, low media resolution** by default; Pro only for persona naming (≤ 30 calls).
4. **YouTube quota:** every call goes through `QuotaLedger`, capped at 9,000 units per Pacific day (12:30 IST reset).
5. **No VMs, GKE, Cloud SQL, GPUs, Memorystore, load balancers, Marketplace or partner models.** `infra/guardrails.sh`
   prints a read-only summary (billing link, VM / SQL / GKE counts, Cloud Run min/max) at the end of every bootstrap.
6. **Cloud Run:** `api` min 0 / max 2 / 512 Mi / concurrency 40; workers max 1; jobs parallelism 1, max-retries 1.
7. **Cloud Storage:** private bucket, uniform access, public-access prevention; lifecycle deletes `tmp/` after 3 days.
8. **Billing is never changed by scripts.** `gcloud billing projects describe` is read-only. Free-trial status is only
   visible in Console → Billing → Overview and must be checked by a human.

## Spend to date (end of P1)
Gemini estimate ≈ **$0.03** (8 logged calls). Billing Reports:
https://console.cloud.google.com/billing/linkedaccount?project=pitchops-ai-2026
