# P4 — Persona Database, Property Ranking, Company Reports

**When:** Thu 15 Oct (start after P3; final run after the **corpus freeze at 22:00 IST**) · **Depends on:** P3 done · **Budget cap:** Gemini ≤ **$15**

**What this phase produces:**
- a rated Persona Database built by adding up per-video labels (D5)
- a ranking of the most-discussed properties, which feeds P6 and P7
- 50 full company reports and light reports for every other relevant company

---

## Prompt to paste into Claude Code

````text
You are building Phase P4 of PitchOps AI. Read CLAUDE.md (§2, §11 D1–D21). Only use v_videos_relevant / v_channels_relevant. FinOps (D14): estimate → my confirmation → run → ledger.

PART A — Persona Database (aggregation, no clustering; D5)
1. Unit of evidence: each relevant video with a deep analysis (weight 1.0); videos with only Tier-2 tags contribute with weight 0.3 and are counted separately ("text-only evidence").
2. Three persona layers, from taxonomy_v2:
   - seller persona = sales_framework (primary + secondary)
   - buyer persona = buyer_persona × buyer_motive (+ triggers, origin personas as attributes)
   - presenter/format = archetype × presenter_present/delivery_style × is_short_candidate
3. Combinations table persona_links: seller × buyer × format with video_count, channel_count, company_count.
4. Ratings per persona and per link (persona_ratings), with confidence and A–E band (CLAUDE.md §7), using:
   - median and P75 trending score; median OPI; median engagement rate
   - median sales_pressure_score, evidence_density, education_to_sales
   - comment buying intent: share of buyer-intent comments; top objections; top questions
   - compliance_risk_rate: share of videos with guarantee/ROI-without-source claims
   - Band shown only when confidence ≥ 0.4 (else "insufficient evidence").
5. Gemini Flash writes for each persona and each top-30 link: a name, a 2-sentence description, typical hooks, typical CTAs, "what works / what to avoid" — strictly from the aggregated stats + 5 example analyses (video_ids cited). Store in personas (persona_db_version = v1.0). Every statement must cite ≥ 1 video_id (validation rejects otherwise).
6. Publish to Firestore read-model: personas, persona_links (top 100), persona_ratings, evidence samples (≤ 12 video_ids each).

PART B — Property ranking ("most discussed properties")
1. Normalize property_mentions from Tier-2 and deep analyses: canonical project name + developer + area (fuzzy match ≥ 0.88 with rapidfuzz, alias table, manual-override CSV config/property_aliases.csv).
2. Score per property: mentions (distinct videos), distinct companies/channels discussing it, total views of those videos, recency (last 6 months weight 1.5), plus deep-analysis signals (avg sales pressure, top buyer personas targeting it, price text, payment plans, investment benefits).
3. Table properties_ranked with rank, stats, top buyer personas, top seller frameworks, common claims, example video_ids. Exclude non-UAE projects.
4. Print top 60 for my review. Mark the top 40 as candidates for media (P7): 20 for 16:9 walkthroughs and 20 different ones for Shorts (D18), alternating by rank so both sets get strong properties. I can override via config/media_property_selection.csv.
5. For each of the 40: official developer/project website URL (from developer domain knowledge + search of names in our corpus descriptions; Gemini may suggest URLs but every URL is verified with an HTTP fetch) → stored in property_sources (verified flag). Unverified ones listed for me to fill manually.

PART C — Company reports (D11, D21; owner spec §7.10)
1. Full reports for the 50 shortlisted companies: bundle (channel stats, archetype mix, framework mix, persona targeting, derived-metric averages, top 10 videos with compact analyses, audience summaries, properties they push). Gemini Flash with company_report_v1.md → CompanyReport JSON + Markdown in the four-table format + funnel architecture + persona statement + gaps & opportunities + Evidence list (every claim → video_ids; reject if any claim lacks evidence).
2. Light reports for all other relevant companies: same structure from Tier-2 tags + metrics only, marked report_type='light'; Flash-Lite; skip companies with < 3 relevant videos.
3. Store in company_reports (BigQuery) + Firestore read-model (summary + markdown); export Markdown to GCS private bucket. Label all reports "internal draft".

FinOps
- Print estimate for Part A naming, Part C full (50) and light (N) before running; confirm; ledger every call; P4 cap $15; finops_report at the end.

ACCEPTANCE (Phase Report)
- Persona DB v1.0: counts per layer, top 15 links with ratings and confidence; every persona statement cites video_ids.
- Top 60 properties printed; 40 media candidates selected (20 + 20, all different); property_sources verified count vs missing.
- Reports: 50 full + N light generated; 0 claims without evidence.
- FinOps: P4 actual vs cap; cumulative vs $200.
- Corpus freeze applied (CORPUS_FROZEN=true at 22:00 IST) and final re-run of Part A after freeze.
````

## Bring back after P4
- The top 60 properties and the 40 media candidates. Swap any you don't want.
- Any properties whose website couldn't be verified. You said you can download images manually, so these are the ones that would need it.
