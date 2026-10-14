# CLAUDE.md — PitchOps AI (BigSell) Master Build Context · v3 (Free-Trial stack, 5-day plan)

> **How to use this file.** Copy it to the root of the GitHub repo as `CLAUDE.md`. Claude Code reads it on every session. Run the phase prompts (`P1_…`, `P2_…`, …) in order. Do not start a phase until the previous phase's acceptance tests pass.

---

## 1. Mission

Build **PitchOps AI**, a Google Cloud–hosted sales-content intelligence workspace for Dubai real estate, for the AI Builder Cup 2026 (theme: *Future of Work & Enterprise Productivity*). **Submission deadline: Sunday 18 October 2026.**

The build has two halves:

1. **Persona Intelligence Engine (built first).**
   - Start from the Dubai Land Department (DLD) registered broker list.
   - Discover the YouTube channels of those brokers and their companies, and harvest every discoverable long-form video and Short.
   - Analyze the videos with Vertex AI Gemini and build a rated **Persona Database** with three linked layers:
     - **Seller personas:** *how* brokers sell (urgency pusher, information overloader, ROI analyst, trusted advisor …).
     - **Buyer personas:** *who* the videos target and *why they would buy* (FOMO investor, golden-visa settler, rental-yield seeker …).
     - **Presenter archetypes:** *how* the content is delivered (walkthrough tour, talking head, podcast, text-overlay reel …).
   - Every combination is rated on engagement, content quality, evidence volume and compliance risk.
2. **Pitch Workflow (built on top).** Brief → grounded script variants driven by the Persona DB → UAE compliance check → human approval → 9:16 video render. See `docs/02_PitchOps_AI_Build_Now_Hackathon_Playbook.md`.

**One-line pitch:** *From 33,000 registered brokers' public content to an evidence-rated persona playbook — and from that playbook to a compliant sales pitch in minutes.*

---

## 2. Non-negotiable rules

1. **Never download YouTube media.** No yt-dlp, pytube or any downloader, and no scraping of youtube.com HTML. Video understanding uses **Vertex AI Gemini with the public YouTube URL as `file_uri`**. Metadata, stats and comments come only from the **YouTube Data API v3**.
2. **Store derived intelligence, not media.** Store metadata, metric snapshots, Gemini analysis JSON, tags, embeddings and scores. Cloud Storage holds only rendered output and user-uploaded owned assets.
3. **Patterns, not people.** Personas are aggregated archetypes. Public example videos may be linked as evidence. Never profile, rank or clone an individual broker.
4. **PII minimization.**
   - `inputs/` is git-ignored and never committed.
   - BigQuery gets only: name EN/AR, broker number, office EN/AR, **email domain** and `is_corporate_email`. **No phone numbers and no full email addresses.**
   - The public repo has only a synthetic 50-row sample.
5. **Never call engagement "conversion".** Use *Observed Performance Index (OPI)* and *Content Effectiveness Score (CES)* only.
6. **Deterministic workflow, LLM steps.** Code owns state, quotas, retries, scoring and compliance severity. Gemini extracts, classifies, names and generates. Every Gemini output is JSON-schema validated before it is stored.
7. **COST GUARDRAILS (Free Trial — must never trigger extra charges).**
   - Use **only Vertex AI** for Gemini. **Never** use a Google AI Studio / Gemini Developer API key: trial credits do not cover it.
   - Do not create VMs, GKE, Cloud SQL, GPUs, Memorystore, load balancers, Marketplace items or partner models.
   - Cloud Run: `min-instances=0`, `max-instances=2` (api) and `1` (worker); Cloud Run Jobs: `parallelism=1`, `max-retries=1`.
   - `GeminiBudget`: before every Gemini call, check today's and the total `llm_calls.cost_usd_est`. Stop at `GEMINI_BUDGET_USD` (default **60**) total and `GEMINI_DAILY_USD` (default **25**).
   - Use low media resolution for video by default. Use Flash-class models only; Pro is optional for persona naming (≤ 30 calls).
   - Cloud Storage: lifecycle deletes `tmp/` after 3 days. Render only approved scripts.
   - Every Phase Report prints an estimated spend to date (Gemini estimate + a link to Billing Reports).
8. **YouTube quota discipline.** Every YouTube API call goes through `QuotaLedger`. Stop at **9,000 units/day** (the quota resets at 12:30 IST).
9. **Idempotency.** Jobs are keyed (e.g. `analysis:{video_id}:{prompt_version}`). Use `MERGE` in BigQuery. Re-runs never duplicate rows or repeat paid calls.
10. **No secrets in the repo.** Secrets live in Secret Manager. Services use service accounts. `.env.example` lists names only.
11. **Fresh project.** All code is written during the hackathon. Third-party libraries are listed in `NOTICE.md`.

---

## 3. Platform decisions (locked)

| Concern | Decision |
|---|---|
| Account | Google Cloud **Free Trial** ($300 credit, never upgraded). Region **us-central1** for everything. |
| Language and runtime | **Python 3.12** (FastAPI, `uv`) for API, jobs and analysis. **Next.js + TypeScript + Tailwind** for the web app. |
| Compute | **Cloud Run** service `api` (public, Firebase-token checked; also proxies in-app Gemini calls). **Cloud Run Jobs:** `discover`, `harvest`, `score`, `analyze`, `personas`, `render`. |
| Scheduling | **Cloud Scheduler** (Asia/Kolkata) triggers discover/harvest/score/analyze until the corpus freeze. |
| AI | **Vertex AI Gemini** via the `google-genai` SDK (`vertexai=True`, project + location, ADC/service account). Model IDs come from env vars (`GEMINI_MODEL_FLASH`, `GEMINI_MODEL_LITE`, `GEMINI_MODEL_PRO`, `EMBEDDING_MODEL_ID`). **Vertex AI text embeddings** are used for clustering. |
| Voice | **Cloud Text-to-Speech** (credit-covered) for the render voiceover. |
| Corpus and analytics | **BigQuery** dataset `pitchops_corpus` (us-central1). MERGE allowed. |
| App state | **Firestore** (Native, us-central1): campaigns, scripts, compliance, approvals, jobs, audit, review decisions. |
| Objects | **Cloud Storage** bucket `${PROJECT_ID}-pitchops` (private, uniform access, signed URLs). |
| Web and auth | **Firebase Hosting** (Next.js static export, `/api/**` rewrite → Cloud Run `api`) + **Firebase Auth** (email/password demo user + Google). |
| Secrets | **Secret Manager**: `YOUTUBE_API_KEY`. |
| Infrastructure and deploy | Idempotent `infra/*.sh` scripts using `gcloud`/`bq`. Build with Cloud Build. GitHub Actions CI for lint/tests only. |

---

## 4. Repository layout

```text
pitchops-ai/
├── CLAUDE.md  README.md  NOTICE.md  .env.example
├── .gitignore                    # inputs/, .env, *.xls, *.xlsx, data/private/, exports/
├── docs/                         # strategy docs + architecture.md + data-model.md + data-sources.md + adr/
├── inputs/                       # LOCAL ONLY — raw DLD broker files
├── data/sample/                  # synthetic 50-row sample
├── infra/                        # 00_bootstrap.sh 10_bigquery.sh 20_scheduler.sh 30_deploy.sh
├── schemas/bq/  schemas/llm/
├── prompts/                      # tier2_v1.md tier3_v1.md persona_naming_v1.md taxonomy_v1.json keywords_v1.json
├── pitchops/
│   ├── config.py  bq.py  fs.py  gcs.py
│   ├── youtube/                  # client.py quota.py models.py
│   ├── gemini/                   # client.py (Vertex) budget.py (GeminiBudget)
│   ├── discovery/                # website_links.py company_search.py keyword_sweep.py matcher.py
│   ├── harvest/                  # uploads.py stats.py comments.py shorts.py
│   ├── analysis/                 # tier2_text.py tier3_video.py validators.py
│   ├── scoring/                  # opi.py ces.py ratings.py
│   ├── personas/                 # embed.py cluster.py name.py rate.py
│   ├── workflow/                 # campaigns, scripts, compliance, approvals (P6)
│   └── render/                   # tts.py captions.py compose.py (P6)
├── services/api/                 # FastAPI → Cloud Run
├── jobs/                         # Cloud Run Job entrypoints
├── web/                          # Next.js → Firebase Hosting
├── evals/  tests/
└── .github/workflows/ci.yml
```

---

## 5. Data model — BigQuery `pitchops_corpus`

All tables carry `ingested_at` and `run_id`.

| Table | Key columns |
|---|---|
| `brokers` | broker_number (PK), name_en, name_ar, office_name_en, office_name_ar, company_id, email_domain, is_corporate_email |
| `companies` | company_id (PK), company_key, office_names_en, office_name_ar, broker_count, primary_domain, corporate_domains, discovery_tier |
| `website_probes` | domain, url_fetched, http_status, robots_allowed, youtube_links[], social_links[], fetched_at, error |
| `channel_candidates` | candidate_id, channel_id, handle, title, description, country, source_route, source_query, company_id_guess, broker_number_guess |
| `channel_matches` | channel_id, company_id, broker_number, match_type, match_score, signals JSON, decision, decided_by, decided_at |
| `channels` | channel_id (PK), title, handle, uploads_playlist_id, subscriber_count, video_count, view_count, country, company_id, broker_number, match_type, harvest_status, next_page_token, last_harvested_at |
| `videos` | video_id (PK), channel_id, title, description, tags[], published_at, duration_sec, is_short, short_rule, default_language, has_captions |
| `video_metrics_daily` | video_id, snapshot_date, view_count, like_count, comment_count (partition snapshot_date) |
| `video_comments_sample` | video_id, comment_id, text, like_count, intent_label, intent_score (no author fields) |
| `video_scores` | video_id, opi, opi_confidence, f1–f4, cohort |
| `video_tags_tier2` | video_id, prompt_version, model_id, topic, property_type, seller_tactics[], buyer_persona_hints[], presenter_format_guess, language, confidence |
| `video_analysis_tier3` | video_id, prompt_version, model_id, analysis JSON, ces_total, ces_breakdown JSON, risk_claims_count, tokens_in, tokens_out, cost_usd_est, status, error |
| `video_persona_tags` | video_id, layer, tag_code, weight, evidence JSON, source_tier |
| `video_embeddings` | video_id, layer, embedding ARRAY<FLOAT64>, model_id |
| `personas` / `persona_links` / `persona_ratings` | persona_db_version + fields per §6–7 |
| `quota_ledger` | ts, day_pt, method, units, job, run_id |
| `llm_calls` | ts, job, model_id, prompt_version, tokens_in, tokens_out, cost_usd_est, latency_ms, status |
| `job_runs` | run_id, job, started_at, ended_at, status, counters JSON, error |

---

## 6. Persona taxonomy v1 (seed vocabulary — Gemini may propose `other:<label>`)

**Seller tactics:** `URGENCY_SCARCITY` · `FOMO_PRICE_RISE` · `INFO_OVERLOAD` · `ROI_NUMBERS` · `LIFESTYLE_DREAM` · `TRUSTED_ADVISOR_EDUCATOR` · `LUXURY_STATUS` · `MYTH_BUSTING` · `DEAL_FLIP_DISCOUNT` · `SOCIAL_PROOF_TESTIMONIAL` · `DEVELOPER_AUTHORITY` · `MARKET_NEWS_COMMENTARY` · `PAYMENT_PLAN_EASE` · `FEAR_OF_MISTAKES`

**Buyer personas:** `FOMO_INVESTOR` · `RENTAL_YIELD_SEEKER` · `CAPITAL_APPRECIATION_SPECULATOR` · `GOLDEN_VISA_RESIDENCY` · `RELOCATING_FAMILY_SETTLER` · `FIRST_TIME_END_USER` · `UPGRADER_FAMILY` · `HNI_LUXURY_COLLECTOR` · `INDIAN_NRI_INVESTOR` · `CIS_RUSSIAN_BUYER` · `EUROPEAN_UK_BUYER` · `GCC_LOCAL_BUYER` · `CHINESE_ASIAN_BUYER` · `TAX_SAFE_HAVEN_SEEKER` · `RETIREE_SECOND_HOME` — each with `motive ∈ {invest, settle, both, unclear}` and `trigger ∈ {fomo, safety, yield, lifestyle, visa, tax, family, status}`.

**Presenter archetypes:** `WALKTHROUGH_TOUR` · `TALKING_HEAD_EXPLAINER` · `PODCAST_INTERVIEW` · `TEXT_OVERLAY_REEL` · `CINEMATIC_DRONE` · `STREET_VOXPOP` · `SCREEN_DATA_EXPLAINER` · `DEVELOPER_LAUNCH_EVENT` · `SKIT_STORY` · `NEWS_STYLE_UPDATE`

---

## 7. Scoring

- **OPI:** the playbook §10.1 formula. Robust P10/P90 normalization within cohort `(is_short, duration bucket ≤60/61–180/181–600/>600)`. Missing features have their weight redistributed and confidence reduced.
- **CES:** the 9-dimension rubric from playbook §10.2, produced by Gemini with timestamp evidence. Code validates the ranges.
- **Persona and link rating:**
  - Compute OPI median/P75, CES median, engagement-rate median, evidence_count, channel_count and compliance_risk_rate.
  - `confidence = min(1, log10(1+evidence)/2) × min(1, channels/5)`.
  - `rating_band` A–E by percentile of `0.5·OPI_median + 0.5·CES_median`, shown only when confidence ≥ 0.4.

---

## 8. Analysis funnel

| Tier | Scope | Engine |
|---|---|---|
| T1 | All videos | Code (OPI) |
| T2 | All videos | Vertex Gemini Flash-Lite, 25 videos per call (title, description, tags, duration) |
| T3 | Stratified sample, **target 1,500–2,500** | Vertex Gemini Flash, YouTube URL, low media resolution; Shorts whole; long-form ≤ 15 min using `video_metadata` start/end offsets (first 120 s + 60 s from the middle). If the P1 smoke test shows offsets are not supported for YouTube URLs, analyze only long-form ≤ 5 min in full |

**T3 sample per channel:** top 8 by OPI + 2 median + 2 bottom (contrast set), then fill so each T2 seller and buyer tag has ≥ 25 videos. Concurrency 4. Stops on GeminiBudget.

---

## 9. Compressed day plan (today = Tue 13 Oct)

| Date | Work | Exit gate |
|---|---|---|
| **Tue 13** | Setup + guardrails, then **P1**; start **P2** discovery tonight (today's YouTube quota is still unused) | Foundation live; registry loaded; first channels found |
| **Wed 14** | **P2** complete: discovery + harvest + T1; scheduler armed | ≥ 100 accepted channels; videos + metrics; OPI |
| **Thu 15** | **P3** T2 (all) + T3 (sample) · **P4** persona synthesis by night · **corpus freeze 22:00 IST** | Persona DB v1.0 in BigQuery + Firestore |
| **Fri 16** | **P5** persona explorer + **P6** brief → scripts → compliance → approval → render | End-to-end flow works on deployed app |
| **Sat 17** | Fix, evals, security check, demo video, deck, README | Assets ready |
| **Sun 18** | Final checks and submit (morning) | Submitted with buffer |

---

## 10. Working conventions for Claude Code

- Restate the phase goal and acceptance tests, plan, then implement.
- End each phase with a **Phase Report**: what was built, test results, BigQuery counts, quota used, Gemini spend estimate, gaps and the next step.
- Scoring, matching, quota and budget logic are pure functions with pytest tests.
- Every job supports `--dry-run`, `--limit N` and `--run-id`, and writes `job_runs`.
- Use structured JSON logs. Never log keys or full emails.
- When a quota or budget limit is hit, persist progress, exit 0 with `QUOTA_EXHAUSTED` / `BUDGET_EXHAUSTED`, and resume on the next run.
- Time is short: prefer the simplest working version, and leave polish for later phases.

---

## 11. Decisions log (binding — added 14 Oct 2026, after P2)

- **D1 · No new channel discovery.** The channel set is closed at the P2 result (1,108 accepted). Do not run discover / search.list again. YouTube quota is reserved for (a) harvesting the remaining un-harvested accepted channels, (b) metric refresh, (c) comment sampling for analysed videos.
- **D2 · Analysis window = last 24 months only.** Every analysis stage (Tier 2, Tier 3, comments, personas, ratings, reports) considers only videos with `published_at >= CURRENT_DATE - 730 days` (and older than 3 days, so metrics are mature). Older videos stay stored for channel baselines only.
- **D3 · Irrelevant content is FLAGGED, never deleted.** Add `is_relevant BOOL`, `relevance_reason STRING`, `relevance_source STRING` (tier2 | rule | manual) at video level and `is_relevant BOOL`, `irrelevant_share FLOAT64`, `relevance_reason STRING` at channel level. Videos not about Dubai/UAE real estate → `is_relevant=false`. Channels whose in-window videos are mostly irrelevant → channel `is_relevant=false` (threshold to be confirmed). **Every downstream query, view, score, persona, rating, report and UI must exclude `is_relevant = false` rows by default** (expose them only in an admin/QA view). Nothing is removed from BigQuery.
- Pending: more scope input from the owner (spec "Dubai Real Estate Social Video Intelligence Platform", YouTube-only subset). Do not start P3 until the P3 prompt is issued.
- **D4 · Full hackathon playbook stays in scope**, with a new final phase: property selection → scripts → compliance → approval → media generation (walkthroughs + digital-avatar presenter). Details in the phase prompts.
- **D5 · Persona DB = aggregation of per-video labels** (sales framework × buyer persona × format, + motive/trigger/origin), rated on views/OPI, trending, Sales Pressure and comment buying-intent. No embedding clustering required.
- **D6 · Taxonomy = owner's spec lists as the MINIMUM** (13 archetypes, hook types, 10 sales frameworks, 9 buyer personas, segment/claim types), expanded with: buyer motive (invest/settle/both), trigger (fomo, visa, yield, capital_growth, family, lifestyle, safety, tax, status), origin persona (Indian/NRI, CIS/Russian, GCC, European/UK, Chinese/Asian, African, other).
- **D7 · Deep analysis scope = top 10 trending videos (last 24 months, relevant only) for a shortlist of ~50 companies.** Text tagging (Tier 2) still covers all relevant last-24-month videos.
- **D8 · Long videos (> 5 min)** are analysed from 3 clips: first 2 min + 1 min from the middle + last 2 min; coverage marked `partial`. Videos ≤ 5 min are analysed in full.
- **D9 · Relevance rule:** relevant = UAE real estate only (no non-UAE projects, no team-culture/motivation/generic content). Channel `is_relevant=false` if > 60% of its last-24-month videos are irrelevant OR it has < 3 relevant videos.
- **D10 · Comments** collected for every deep-analysed video (YouTube API, PII hashed/redacted).
- **D11 · Company reports for as many companies as possible** (full reports where deep analysis exists).
- **D12 · Individual broker channels:** include only if their videos are already harvested; otherwise defer.
- **D13 · Personal project.** No employer, practice or internal-governance references anywhere in code, docs, prompts, UI or deck.
- **D14 · FinOps is mandatory in every phase:** cost estimate printed before any paid run, per-stage budget caps, spend logged per call, daily cost report, and a cumulative FinOps dashboard.
- **D15 · Media budget ≈ $120, total project cap $200** ($100 buffer kept so the trial never runs out during judging). Media is the LAST phase.
- **D16 · Every media video needs owner approval in the web app** (plan → cost estimate → Approve → render). No render without an approval record.
- **D17 · 8 fictional bilingual avatars** (Imagen portrait + Veo animation; speak intro/outro in English; TTS narration in between): Indian, Middle Eastern, North American, East Asian, African, Russian, European, South American. Fictional only — must not resemble real people.
- **D18 · 40 demo videos = 40 different properties:** 20 × 16:9 walkthroughs (≤ 2 min) + 20 × 9:16 Shorts (≤ 1 min). Images from developer/project websites (robots.txt respected; owner may add images manually). Images and rendered media stay private (never in the public repo).
- **D19 · Branding:** fictional "PitchOps Demo Realty", placeholder permit "DEMO-PERMIT", no real Madmoun QR. No extra on-video disclaimer required (demo use only).
- **D20 · Scripts English only.** ~100 scripts: top ~25 most-discussed properties × 3–4 buyer-persona angles, plus one script for each of the 40 video properties.
- **D21 · Deep-analysis shortlist** = top ~50 companies by total views of relevant last-24-month videos. Full reports for those 50; light reports (text-tag + metrics based) for all other relevant companies.
