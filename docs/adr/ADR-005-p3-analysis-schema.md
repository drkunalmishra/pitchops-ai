# ADR-005 — P3 relevance, deep-analysis schema and derived metrics (drafted)

**Status:** Accepted (owner asked P3 to draft these because the owner spec §7–8 was not available) · **Date:** 14 Oct 2026

## Relevance (D2, D3, D9)
- `videos.in_window` = published within 730 days and older than 3 days. `is_short_candidate` = duration ≤ 180 s.
- Free rule pre-filter (`pitchops/analysis/relevance_rules.py`): a non-UAE market in the title with no UAE term
  anywhere, or team-culture / hiring / motivation titles with no property term anywhere → `is_relevant=false`,
  `relevance_source='rule'`. Everything else → Gemini Flash-Lite Tier 2 (`relevance_source='tier2'`).
- Channel: `is_relevant=false` if > 60 % of in-window videos are irrelevant or < 3 relevant in-window videos.
- Nothing is deleted. Every downstream job reads `v_videos_relevant` / `v_channels_relevant`;
  `v_videos_irrelevant_qa` is the admin view.

## Deep analysis — four tables (`pitchops/analysis/deep_video.py`, prompt `deep_v1`)
1. **overview** — summary, language, archetype, hook_type / hook_text / hook_end_sec, sales_frameworks,
   buyer_personas, buyer_motive, buyer_triggers, origin_personas, cta_type / cta_text, presenter_on_camera,
   sub_scores 0–10 (hook_strength, clarity, evidence_quality, cta_clarity, production_quality).
2. **segments** — ordered, non-overlapping; segment_type, mode (education | pitch | neutral), summary, on-screen text.
3. **claims** — exact quote, ts, claim_type, has_source, source_text, is_risky, risk_note.
4. **property_mentions** — ts, project, developer, area, emirate, property_type, price_text (as stated).

Enums: `prompts/taxonomy_v2.json` (segment_type, claim_type and cta_type drafted here).
Clips (D8): ≤ 300 s full; else 0–120 s + middle 60 s + last 120 s, `coverage='partial'`, absolute timestamps.
Validation: timestamps ≤ duration (+3 s), segments ordered / non-overlapping, ≥ 80 % coverage when full, segments
inside clips when partial, claims need quotes; one repair retry, then `status='needs_review'`.

## Derived metrics (code only — `derived_metrics()`)
| Metric | Formula |
|---|---|
| evidence_density | sourced claims per analysed minute |
| sourced_claim_share | sourced / total claims (null if none) |
| education_to_sales | education seconds / max(pitch seconds, 1) |
| pitch_share | pitch seconds / segmented seconds |
| sales_pressure_score (0–10) | 10 × (0.35·pitch_share + 0.25·[fomo_scarcity or deal_discount] + 0.20·risky-claim share + 0.10·[urgent hook] + 0.10·[direct CTA]) |
| verification_status | no_claims · unverified_claims (any risky) · sourced (≥ 50 % sourced) · partially_sourced |

## Trending (owner §7.4 as given in the P3 prompt)
`trending = 0.65·log2(max(outlier, 0.01)) + 0.35·clamp(z_eng, −3, 3)`; baseline = median views of the channel's
other videos within ±90 days (≥ 5) else channel median; z_eng = robust (median / MAD) z within the channel.

## Comments (D10)
≤ 200 threads per deep-analysed video (order=relevance). `author_hash = HMAC-SHA256(PII_HASH_PEPPER, "youtube:"+id)`;
no names, handles, avatars or profile URLs; phones, emails, Emirates IDs, URLs and @mentions redacted before storage.
Flash-Lite classification never infers nationality, religion, health or other sensitive traits.
`audience_summaries.intent_rate` feeds OPI f4.
