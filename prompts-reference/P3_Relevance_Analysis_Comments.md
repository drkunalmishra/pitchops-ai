# P3 — Relevance Flags, Trending Selection, Text Tagging, Deep Video Analysis, Comment Intelligence

**When:** start Wed 14 Oct evening, finish Thu 15 Oct · **Depends on:** P2 done · **Budget cap for this phase:** Gemini ≤ **$30**

**What this phase produces:**
- every in-window video flagged relevant or irrelevant
- text tags for all relevant videos, including the property, project and developer they mention
- a per-channel trending score
- a 50-company shortlist
- deep "four-table" analysis for top-10 trending videos of each shortlisted company
- classified comments for those videos

---

## Prompt to paste into Claude Code

````text
You are building Phase P3 of PitchOps AI. Read CLAUDE.md fully, especially §2 (rules), §11 Decisions D1–D21. Gemini runs on Vertex AI (GEMINI_LOCATION=global for Gemini 3.x; see docs/adr/ADR-001). FinOps (D14) is mandatory: every paid stage prints an estimate and asks for my "yes" before running at scale.

STEP 0 — Housekeeping
- Pause the Cloud Scheduler job "discover" (D1). Keep harvest + score running until the corpus freeze (Thu 15 Oct 22:00 IST).
- Harvest: finish the remaining accepted channels; afterwards restrict daily metric refresh to videos published in the last 24 months.
- Add to config: GEMINI_PHASE_BUDGET_USD_P3=30, GEMINI_DAILY_USD=25, TOTAL_PROJECT_CAP_USD=200.
- Create Secret Manager secret PII_HASH_PEPPER with 32 random bytes (generated locally, never printed).

STEP 1 — Schema changes (BigQuery, additive only; never drop)
- videos: is_relevant BOOL, relevance_reason STRING, relevance_source STRING (tier2|rule|manual), in_window BOOL (published within 730 days and older than 3 days), is_short_candidate BOOL (duration ≤ 180 s).
- channels: is_relevant BOOL, irrelevant_share FLOAT64, relevant_video_count INT64, relevance_reason STRING.
- New views: v_videos_relevant (in_window AND is_relevant AND channel.is_relevant) — EVERY downstream query in P3–P7 reads from this view or joins to it. v_channels_relevant likewise.
- New tables: video_trending, video_tags_tier2 (v2 schema below), company_shortlist, video_analysis (four-table schema), video_metrics_derived, comments, comment_classifications, audience_summaries, property_mentions, finops_ledger.

STEP 2 — Taxonomy (prompts/taxonomy_v2.json, versioned). The owner's spec lists are the MINIMUM; keep every value and add the expansions:
- archetype: market_intelligence, project_showcase, property_tour, lifestyle, developer_briefing, event_open_house, social_proof_deal, team_employer_brand, educational_explainer, testimonial, agent_personal_brand, entertainment_trend, other (+ market_news_update, myth_busting, comparison, q_and_a)
- hook_type: data_shock, question, bold_claim, visual_reveal, price_reveal, story, trend_audio, controversy, other (+ mistake_warning, urgency_countdown)
- sales_framework: authority, challenger, education_led, fomo_scarcity, social_proof, developer_authority, experiential, lifestyle, financial, risk_reduction (+ payment_plan_ease, info_overload, deal_discount, myth_busting, status_luxury)
- buyer_persona: hnw_uhnw_investor, yield_investor, capital_growth_investor, offplan_investor, end_user_family, international_expat, first_time_buyer, golden_visa_seeker, agent_industry (+ relocating_professional, retiree_second_home, tax_safe_haven_seeker, upgrader_family)
- buyer_motive: invest | settle | both | unclear
- buyer_trigger (multi): fomo, visa, yield, capital_growth, family, lifestyle, safety, tax, status, payment_plan
- origin_persona (multi): indian_nri, cis_russian, gcc_local, european_uk, chinese_east_asian, african, south_asian_other, north_american, latin_american, unspecified
- segment_type, claim_type, CTA type: exactly as in the owner's spec §8.1.

STEP 3 — Relevance + Tier-2 text tagging (all in-window videos)
- Rule pre-filter (free): mark is_relevant=false with relevance_source='rule' when title+description clearly signal non-UAE property only, or team culture/motivation/office party/birthday/award night/hiring/vlog with no property content (keyword lists in config, conservative). Everything else goes to Gemini.
- Gemini Flash-Lite, 25 videos per call, input = video_id, title, description (first 600 chars), tags, duration, published_at. Wrap all third-party text in <untrusted_metadata>. Output per video (schema-validated):
  is_relevant (true only if about UAE real estate: properties, projects, areas, market, buying/renting/investing, visas linked to property), relevance_reason, language, archetype_guess, sales_frameworks_guess[], buyer_personas_guess[], buyer_motive_guess, triggers_guess[], origin_personas_guess[],
  property_mentions[]: {project_name, developer, area, emirate, property_type, price_text} exactly as stated (null if absent),
  confidence 0–1.
- Channel rule (D9): channel.is_relevant=false if irrelevant_share > 0.60 OR relevant_video_count < 3 (in-window videos only).
- FinOps: before running, print N videos, calls, est. tokens and $; ask me to confirm. Run with concurrency 8, checkpointed, resumable, idempotent (skip video_ids already tagged with the same prompt_version).

STEP 4 — Trending score (owner spec §7.4, code only, relevant in-window videos)
- metric = views; baseline = median views of the same channel's videos within ±90 days of posting (min 5 videos, else channel median); outlier = views / max(baseline,1);
- eng_rate = (likes + comments) / max(views,1); z_eng = robust z (median/MAD) within channel;
- trending = 0.65·log2(max(outlier,0.01)) + 0.35·clamp(z_eng,−3,3). Store in video_trending with all components. Keep OPI as well.
- Unit tests against a hand-computed fixture.

STEP 5 — Company shortlist (D21)
- Rank companies by total views of v_videos_relevant; take top 50 that have ≥ 10 relevant videos. Store in company_shortlist with rank and stats. Print the list for me before Step 6.
- Selection for deep analysis: per shortlisted company, top 10 by trending score (across all its accepted channels), plus any video with outlier ≥ 3 (cap 12 per company). Include company-matched broker channels only if already harvested (D12). Expected ≈ 500–600 videos.

STEP 6 — Deep video analysis (four tables, owner spec §8.1 + taxonomy_v2)
- Vertex Gemini Flash, YouTube URL as file_data, media_resolution LOW, temperature 0.2, response_schema = VideoAnalysis (extend owner schema with buyer_motive, buyer_triggers[], origin_personas[], and property_mentions[] with timestamps).
- Clip rule (D8): duration ≤ 300 s → full video. > 300 s → three clips via video_metadata offsets: 0–120 s, middle 60 s, last 120 s; one call with three file_data parts (or three calls merged if needed); coverage='partial'; timestamps are absolute.
- Validation (owner §7.7 step 5): timestamps within duration, segments ordered (coverage ≥ 80% only when coverage='full'), enums valid, claims have quotes, sub-scores in range. One repair retry, then status='needs_review'.
- Derived metrics in code (owner §8.2): evidence_density, sourced_claim_share, education_to_sales, pitch_share, sales_pressure_score 0–10, verification_status → video_metrics_derived. The LLM never computes final scores.
- FinOps: estimate before run (seconds of video × measured tokens/sec × price), confirm, concurrency 4, stop at phase budget.

STEP 7 — Comment intelligence (D10; owner spec §7.9; YouTube only)
- commentThreads.list order=relevance, up to 200 comments per deep-analysed video (≈ 2 units per video), via QuotaLedger.
- PII: author_hash = HMAC-SHA256(PII_HASH_PEPPER from Secret Manager, "youtube:"+channelId); never store names/handles/profile URLs; author_is_owner when commenter channel == video channel; redact phones (UAE + international), emails, Emirates ID pattern 784-\d{4}-\d{7}-\d, URLs with personal identifiers.
- Classify in batches of 50 with Flash-Lite (owner §8.4 schema; never infer nationality/religion/health).
- audience_summaries per video: data_status complete|partial|unavailable, sentiment/intent/persona mix, buyer_intent_count (score ≥ 0.6), top questions, objection topics (group by normalized topic), owner_reply_rate. Feed f4 (intent rate) back into OPI.

STEP 8 — FinOps ledger and report
- finops_ledger table: date, phase, stage, provider (vertex_gemini|youtube_api|cloud_run|bigquery|tts|veo|imagen), units, est_cost_usd, run_id. Populate from llm_calls, quota_ledger and job durations.
- jobs/finops_report.py prints: spend by phase/stage today and cumulative, % of P3 cap, % of TOTAL_PROJECT_CAP_USD, projection for remaining phases; writes summary doc to Firestore finops/current for the dashboard.

ACCEPTANCE (Phase Report)
- All in-window videos have is_relevant set; counts of relevant/irrelevant videos and channels with reasons breakdown; 20 random irrelevant + 20 random relevant samples printed for my spot check.
- v_videos_relevant used by every new job (grep check).
- Trending unit tests green; shortlist of 50 printed with views and relevant-video counts.
- Deep analyses: ≥ 95% status=succeeded, rest needs_review; distribution of archetypes, frameworks, personas, sales_pressure printed.
- Comments: count collected, % videos with data_status complete/partial/unavailable; zero raw author identifiers stored (assert).
- property_mentions: top 40 projects by mentions × views printed.
- FinOps report: actual P3 spend vs $30 cap, cumulative vs $200.
````

## Bring back after P3
- The Phase Report.
- The relevance spot-check samples, with any wrong ones marked.
- Changes to the 50-company shortlist, if you want any.
- The top-40 property list. P4 uses it to pick properties for the scripts and videos.
