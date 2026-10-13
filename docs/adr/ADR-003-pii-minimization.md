# ADR-003 — PII minimization for the DLD broker registry

**Status:** Accepted · **Date:** 13 Oct 2026

## Context
The DLD broker list contains names, broker numbers, offices, phone numbers and email addresses. We need it only to
discover company/broker YouTube channels and to aggregate content patterns — never to profile individuals.

## Decisions
1. Raw files live only in `inputs/` (git-ignored, excluded from Cloud Build uploads via `.gcloudignore`, excluded from
   Docker builds via `.dockerignore`). `scripts/guard_forbidden.sh` fails CI if `.env`, `inputs/` or `*.xls(x)` are tracked.
2. `jobs/load_registry.py` projects an explicit allow-list of columns. **Phone and full email are dropped in code**
   before anything reaches BigQuery. Kept: `name_en`, `name_ar`, `broker_number`, `office_name_en/ar`, `company_id`,
   `email_domain`, `is_corporate_email`.
3. After each load the job asserts via `INFORMATION_SCHEMA.COLUMNS` that no `phone`/`email`/`mobile` column exists in
   the dataset (result for P1: **0**).
4. The repository ships only `data/sample/brokers_sample.csv`: 50 **synthetic** rows with reserved `*.test` domains.
5. Personas are aggregated archetypes (patterns, not people). Public videos may be cited as evidence; individual brokers
   are never ranked, profiled or cloned. Comment samples store no author fields.
6. Logs never contain keys or full emails. The YouTube API key is sent in the `X-Goog-Api-Key` header, never in URLs.

## P1 load result
33,565 brokers (unique broker numbers, 0 without a company) and 9,862 companies loaded with `WRITE_TRUNCATE`.
