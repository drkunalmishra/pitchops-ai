"""Generates schemas/bq/*.json from the compact spec below (CLAUDE.md §5). Re-run after editing."""

import json
from pathlib import Path

S, I, F, B, T, D, J = "STRING", "INT64", "FLOAT64", "BOOL", "TIMESTAMP", "DATE", "JSON"
# REQUIRED only for each table's own key; everything else NULLABLE.
PK = {"brokers": {"broker_number"}, "companies": {"company_id"}, "channels": {"channel_id"}, "videos": {"video_id"},
      "video_metrics_daily": {"video_id", "snapshot_date"}, "channel_matches": {"channel_id"},
      "channel_candidates": {"candidate_id"}, "website_probes": {"domain"}, "discovery_searches": {"search_key"},
      "quota_ledger": {"ts"}, "llm_calls": {"ts"}, "job_runs": {"run_id"}, "video_trending": {"video_id"},
      "company_shortlist": {"company_id"}, "deep_selection": {"video_id"}, "video_analysis": {"video_id"},
      "video_metrics_derived": {"video_id"}, "comments": {"comment_id"}, "comment_classifications": {"comment_id"},
      "audience_summaries": {"video_id"}, "property_mentions": {"mention_id"}, "finops_ledger": {"ledger_id"},
      "properties_ranked": {"property_id"}, "property_sources": {"property_id"}}

# table: (fields, partition_field or None, cluster fields)
TABLES = {
    "brokers": ([("broker_number", S), ("name_en", S), ("name_ar", S), ("office_name_en", S),
                 ("office_name_ar", S), ("company_id", S), ("email_domain", S), ("is_corporate_email", B)],
                None, ["company_id"]),
    "companies": ([("company_id", S), ("company_key", S), ("office_names_en", S), ("office_name_ar", S),
                   ("broker_count", I), ("primary_domain", S), ("corporate_domains", S, "REPEATED"),
                   ("discovery_tier", S)], None, ["discovery_tier"]),
    "website_probes": ([("domain", S), ("url_fetched", S), ("http_status", I), ("robots_allowed", B),
                        ("youtube_links", S, "REPEATED"), ("social_links", S, "REPEATED"),
                        ("fetched_at", T), ("error", S)], None, ["domain"]),
    "channel_candidates": ([("candidate_id", S), ("channel_id", S), ("handle", S), ("title", S),
                            ("description", S), ("country", S), ("source_route", S), ("source_query", S),
                            ("company_id_guess", S), ("broker_number_guess", S)], None, ["channel_id"]),
    "channel_matches": ([("channel_id", S), ("company_id", S), ("broker_number", S), ("match_type", S),
                         ("match_score", F), ("signals", J), ("decision", S), ("decided_by", S),
                         ("decided_at", T)], None, ["channel_id"]),
    "channels": ([("channel_id", S), ("title", S), ("handle", S), ("uploads_playlist_id", S),
                  ("subscriber_count", I), ("video_count", I), ("view_count", I), ("country", S),
                  ("company_id", S), ("broker_number", S), ("match_type", S), ("harvest_status", S),
                  ("next_page_token", S), ("last_harvested_at", T), ("is_relevant", B), ("irrelevant_share", F),
                  ("relevant_video_count", I), ("relevance_reason", S)], None, ["channel_id"]),
    "videos": ([("video_id", S), ("channel_id", S), ("title", S), ("description", S),
                ("tags", S, "REPEATED"), ("published_at", T), ("duration_sec", I), ("is_short", B),
                ("short_rule", S), ("default_language", S), ("has_captions", B),
                ("is_relevant", B), ("relevance_reason", S), ("relevance_source", S), ("in_window", B),
                ("is_short_candidate", B)], None,
               ["channel_id", "video_id"]),
    "video_metrics_daily": ([("video_id", S), ("snapshot_date", D), ("view_count", I), ("like_count", I),
                             ("comment_count", I)], "snapshot_date", ["video_id"]),
    "video_comments_sample": ([("video_id", S), ("comment_id", S), ("text", S), ("like_count", I),
                               ("intent_label", S), ("intent_score", F)], None, ["video_id"]),
    "video_scores": ([("video_id", S), ("opi", F), ("opi_confidence", F), ("f1", F), ("f2", F), ("f3", F),
                      ("f4", F), ("cohort", S)], None, ["video_id"]),
    "video_tags_tier2": ([("video_id", S), ("prompt_version", S), ("model_id", S), ("topic", S),
                          ("property_type", S), ("seller_tactics", S, "REPEATED"),
                          ("buyer_persona_hints", S, "REPEATED"), ("presenter_format_guess", S),
                          ("language", S), ("confidence", F), ("is_relevant", B), ("relevance_reason", S),
                          ("archetype_guess", S), ("sales_frameworks_guess", S, "REPEATED"),
                          ("buyer_personas_guess", S, "REPEATED"), ("buyer_motive_guess", S),
                          ("triggers_guess", S, "REPEATED"), ("origin_personas_guess", S, "REPEATED"),
                          ("property_mentions", J)], None, ["video_id"]),
    "video_analysis_tier3": ([("video_id", S), ("prompt_version", S), ("model_id", S), ("analysis", J),
                              ("ces_total", F), ("ces_breakdown", J), ("risk_claims_count", I),
                              ("tokens_in", I), ("tokens_out", I), ("cost_usd_est", F), ("status", S),
                              ("error", S)], None, ["video_id"]),
    "video_persona_tags": ([("video_id", S), ("layer", S), ("tag_code", S), ("weight", F), ("evidence", J),
                            ("source_tier", S)], None, ["layer", "tag_code"]),
    "video_embeddings": ([("video_id", S), ("layer", S), ("embedding", F, "REPEATED"), ("model_id", S)],
                         None, ["layer"]),
    "personas": ([("persona_db_version", S), ("persona_id", S), ("layer", S), ("code", S), ("name", S),
                  ("description", S), ("motive", S), ("trigger", S), ("member_count", I),
                  ("example_video_ids", S, "REPEATED"), ("attributes", J), ("weighted_evidence", F), ("deep_videos", I),
                  ("text_only_videos", I), ("channel_count", I), ("company_count", I), ("name_source", S)], None,
                 ["persona_db_version", "layer"]),
    "persona_links": ([("persona_db_version", S), ("link_id", S), ("seller_persona_id", S),
                       ("buyer_persona_id", S), ("presenter_persona_id", S), ("evidence_count", I),
                       ("example_video_ids", S, "REPEATED"), ("video_count", I), ("deep_videos", I), ("channel_count", I),
                       ("company_count", I), ("weighted_evidence", F)], None, ["persona_db_version"]),
    "persona_ratings": ([("persona_db_version", S), ("entity_type", S), ("entity_id", S), ("opi_median", F),
                         ("opi_p75", F), ("ces_median", F), ("engagement_rate_median", F),
                         ("evidence_count", I), ("channel_count", I), ("compliance_risk_rate", F),
                         ("confidence", F), ("score", F), ("rating_band", S), ("trending_median", F),
                         ("trending_p75", F), ("sales_pressure_median", F), ("evidence_density_median", F),
                         ("education_to_sales_median", F), ("buyer_intent_share", F), ("top_objections", J),
                         ("top_questions", J), ("deep_n", I), ("band_basis", S)], None,
                        ["persona_db_version", "entity_type"]),
    "quota_ledger": ([("ts", T), ("day_pt", D), ("method", S), ("units", I), ("job", S)], "ts", ["day_pt"]),
    "llm_calls": ([("ts", T), ("job", S), ("model_id", S), ("prompt_version", S), ("tokens_in", I),
                   ("tokens_out", I), ("cost_usd_est", F), ("latency_ms", I), ("status", S)], "ts", ["model_id"]),
    "video_trending": ([("video_id", S), ("channel_id", S), ("views", I), ("baseline", F), ("baseline_n", I),
                        ("baseline_kind", S), ("outlier", F), ("eng_rate", F), ("z_eng", F), ("trending", F),
                        ("computed_at", T)], None, ["channel_id"]),
    "company_shortlist": ([("company_id", S), ("rank", I), ("company_name", S), ("total_views", I),
                           ("relevant_videos", I), ("channels", I), ("selected_videos", I)], None, ["company_id"]),
    "deep_selection": ([("video_id", S), ("company_id", S), ("channel_id", S), ("rank_in_company", I),
                        ("trending", F), ("outlier", F), ("reason", S)], None, ["company_id"]),
    "video_analysis": ([("video_id", S), ("prompt_version", S), ("model_id", S), ("status", S), ("coverage", S),
                        ("clips", J), ("duration_sec", I), ("overview", J), ("segments", J), ("claims", J),
                        ("property_mentions", J), ("archetype", S), ("hook_type", S),
                        ("sales_frameworks", S, "REPEATED"), ("buyer_personas", S, "REPEATED"), ("buyer_motive", S),
                        ("buyer_triggers", S, "REPEATED"), ("origin_personas", S, "REPEATED"), ("cta_type", S),
                        ("language", S), ("validation_errors", S, "REPEATED"), ("tokens_in", I), ("tokens_out", I),
                        ("cost_usd_est", F), ("attempts", I), ("error", S)], None, ["video_id"]),
    "video_metrics_derived": ([("video_id", S), ("prompt_version", S), ("evidence_density", F),
                               ("sourced_claim_share", F), ("education_to_sales", F), ("pitch_share", F),
                               ("sales_pressure_score", F), ("verification_status", S), ("claims_total", I),
                               ("claims_risky", I)], None, ["video_id"]),
    "comments": ([("comment_id", S), ("video_id", S), ("parent_id", S), ("is_reply", B), ("author_hash", S),
                  ("author_is_owner", B), ("text_redacted", S), ("redaction_count", I), ("like_count", I),
                  ("reply_count", I), ("published_at", T)], None, ["video_id"]),
    "comment_classifications": ([("comment_id", S), ("video_id", S), ("prompt_version", S), ("model_id", S),
                                 ("sentiment", S), ("intent", S), ("buying_intent_score", F), ("persona_hint", S),
                                 ("topic", S), ("question", S), ("objection_topic", S), ("language", S)], None,
                                ["video_id"]),
    "audience_summaries": ([("video_id", S), ("data_status", S), ("comments_collected", I),
                            ("comments_available", I), ("sentiment_mix", J), ("intent_mix", J), ("persona_mix", J),
                            ("buyer_intent_count", I), ("intent_rate", F), ("top_questions", J),
                            ("objection_topics", J), ("owner_reply_rate", F)], None, ["video_id"]),
    "property_mentions": ([("mention_id", S), ("video_id", S), ("source_tier", S), ("project_name", S),
                           ("project_key", S), ("developer", S), ("area", S), ("emirate", S), ("property_type", S),
                           ("price_text", S), ("ts_sec", F)], None, ["project_key"]),
    "finops_ledger": ([("ledger_id", S), ("date", D), ("phase", S), ("stage", S), ("provider", S), ("units", F),
                       ("unit_name", S), ("est_cost_usd", F), ("ts", T)], None, ["phase", "provider"]),
    "properties_ranked": ([("property_id", S), ("rank", I), ("canonical_name", S), ("kind", S), ("developer", S),
                           ("area", S), ("emirate", S), ("aliases", S, "REPEATED"), ("property_types", S, "REPEATED"),
                           ("videos", I), ("weighted_videos", F), ("recent_videos", I), ("companies", I),
                           ("channels", I), ("total_views", I), ("score", F), ("avg_sales_pressure", F),
                           ("top_buyer_personas", S, "REPEATED"), ("top_frameworks", S, "REPEATED"),
                           ("price_texts", S, "REPEATED"), ("example_video_ids", S, "REPEATED"),
                           ("media_candidate", S)], None, ["rank"]),
    "property_sources": ([("property_id", S), ("canonical_name", S), ("media_candidate", S), ("url", S),
                          ("url_kind", S), ("final_url", S), ("http_status", I), ("robots_allowed", B), ("verified", B),
                          ("checked_at", T)], None, ["property_id"]),
    "discovery_searches": ([("search_key", S), ("route", S), ("query", S), ("company_id", S), ("page", I),
                            ("next_page_token", S), ("result_count", I), ("searched_at", T)], None, ["route"]),
    "job_runs": ([("job", S), ("started_at", T), ("ended_at", T), ("status", S), ("counters", J),
                  ("error", S)], None, ["job"]),
}

COMMON = [("ingested_at", T), ("run_id", S)]


def field(spec: tuple, table: str) -> dict:
    name, typ, *mode = spec
    m = mode[0] if mode else ("REQUIRED" if name in PK.get(table, set()) else "NULLABLE")
    return {"name": name, "type": typ, "mode": m}


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "schemas" / "bq"
    out.mkdir(parents=True, exist_ok=True)
    for name, (fields, part, cluster) in TABLES.items():
        names = {f[0] for f in fields}
        allf = fields + [c for c in COMMON if c[0] not in names]
        doc = {"table": name, "fields": [field(f, name) for f in allf], "clustering": cluster}
        if part:
            doc["time_partitioning"] = {"field": part, "type": "DAY"}
        (out / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {len(TABLES)} schemas to {out}")


if __name__ == "__main__":
    main()
