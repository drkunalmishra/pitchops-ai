"""P3 Step 3 — in-window flags, rule pre-filter, Tier-2 Gemini tagging, channel relevance rule (D2, D3, D9).

Usage:
  uv run python -m jobs.relevance --estimate            # print cost estimate only (no paid calls)
  uv run python -m jobs.relevance --limit 250           # pilot
  uv run python -m jobs.relevance                       # full run (resumable; skips already-tagged videos)
  uv run python -m jobs.relevance --apply-only          # recompute flags + channel rule without Gemini
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from pitchops.analysis import tier2_text
from pitchops.analysis.relevance_rules import rule_irrelevant
from pitchops.bq import client, merge_rows, query
from pitchops.config import get_settings
from pitchops.gemini.budget import BudgetExhausted
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log

JOB = "p3_tier2"
CONCURRENCY = 8
FLUSH_CALLS = 40
CHANNEL_IRRELEVANT_SHARE = 0.60
CHANNEL_MIN_RELEVANT = 3
# fallback per-call token estimate until a pilot exists (measured values replace these)
DEFAULT_IN_PER_CALL, DEFAULT_OUT_PER_CALL = 6000, 5000


def t(name: str) -> str:
    return get_settings().table(name)


def dml(sql: str, params: dict[str, Any] | None = None) -> int:
    from google.cloud import bigquery

    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter(k, "STRING", v)
                                                    for k, v in (params or {}).items()])
    job = client().query(sql, job_config=cfg)
    job.result()
    return int(job.num_dml_affected_rows or 0)


def set_window() -> int:
    return dml(f"""UPDATE `{t('videos')}` SET
        in_window = published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 730 DAY)
                    AND published_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY),
        is_short_candidate = IFNULL(duration_sec, 0) BETWEEN 1 AND 180
        WHERE TRUE""")


def rule_pass(run_id: str) -> dict[str, int]:
    rows = query(f"""SELECT video_id, title, description, tags FROM `{t('videos')}`
                     WHERE in_window AND relevance_source IS NULL""")
    flagged = []
    for r in rows:
        reason = rule_irrelevant(r["title"], r["description"], r["tags"])
        if reason:
            flagged.append({"video_id": r["video_id"], "is_relevant": False, "relevance_reason": reason,
                            "relevance_source": "rule"})
    merge_rows("videos", flagged, ["video_id"], update_cols=["is_relevant", "relevance_reason", "relevance_source"])
    return {"rule_checked": len(rows), "rule_flagged": len(flagged)}


def pending(limit: int | None) -> list[dict[str, Any]]:
    rows = query(f"""SELECT v.video_id, v.title, v.description, v.tags, v.duration_sec, v.published_at
        FROM `{t('videos')}` v
        LEFT JOIN `{t('video_tags_tier2')}` g ON g.video_id = v.video_id AND g.prompt_version = @pv
        WHERE v.in_window AND IFNULL(v.relevance_source, '') NOT IN ('rule', 'manual') AND g.video_id IS NULL
        ORDER BY v.video_id""", {"pv": tier2_text.PROMPT_VERSION})
    return rows[:limit] if limit else rows


def measured_tokens_per_call() -> tuple[float, float, int]:
    r = query(f"""SELECT AVG(tokens_in) i, AVG(tokens_out) o, COUNT(*) n FROM `{t('llm_calls')}`
                  WHERE job = @j AND prompt_version = @pv AND status = 'OK'""",
              {"j": JOB, "pv": tier2_text.PROMPT_VERSION})[0]
    if r["n"]:
        return float(r["i"]), float(r["o"]), int(r["n"])
    return DEFAULT_IN_PER_CALL, DEFAULT_OUT_PER_CALL, 0


def estimate(n_videos: int) -> dict[str, Any]:
    s = get_settings()
    calls = -(-n_videos // tier2_text.BATCH)
    tin, tout, n = measured_tokens_per_call()
    pin, pout = s.price_for(s.gemini_model_lite)
    usd = calls * (tin * pin + tout * pout) / 1e6
    return {"videos": n_videos, "calls": calls, "tokens_in_per_call": round(tin), "tokens_out_per_call": round(tout),
            "measured_from_calls": n, "est_tokens_in_M": round(calls * tin / 1e6, 2),
            "est_tokens_out_M": round(calls * tout / 1e6, 2), "est_usd": round(usd, 2),
            "model": s.gemini_model_lite, "price_in_out_per_Mtok": [pin, pout]}


def tag_batch(g: Any, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    s = get_settings()
    ids = [v["video_id"] for v in batch]
    res = g.generate_json(s.gemini_model_lite, [tier2_text.build_input(batch)], tier2_text.schema(),
                          prompt_version=tier2_text.PROMPT_VERSION, temperature=0.1, system=tier2_text.SYSTEM,
                          thinking="minimal", validator=tier2_text.validator_for(ids))
    return [{**v, "_model": res.model_id} for v in res.data["videos"]]


def flush(results: list[dict[str, Any]], run_id: str) -> None:
    if not results:
        return
    now = datetime.now(UTC).isoformat()
    tags, mentions = [], []
    for r in results:
        tags.append({"video_id": r["video_id"], "prompt_version": tier2_text.PROMPT_VERSION, "model_id": r["_model"],
                     "is_relevant": r["is_relevant"], "relevance_reason": r["relevance_reason"][:300],
                     "language": r["language"], "archetype_guess": r["archetype_guess"],
                     "sales_frameworks_guess": r["sales_frameworks_guess"],
                     "buyer_personas_guess": r["buyer_personas_guess"], "buyer_motive_guess": r["buyer_motive_guess"],
                     "triggers_guess": r["triggers_guess"], "origin_personas_guess": r["origin_personas_guess"],
                     "property_mentions": r["property_mentions"], "confidence": r["confidence"],
                     "run_id": run_id, "ingested_at": now})
        for i, m in enumerate(r["property_mentions"]):
            if not any(m.get(k) for k in ("project_name", "developer", "area")):
                continue
            mentions.append({"mention_id": f"{r['video_id']}:t2:{i}", "video_id": r["video_id"], "source_tier": "tier2",
                             **{k: m.get(k) for k in ("project_name", "developer", "area", "emirate", "property_type",
                                                      "price_text")},
                             "project_key": project_key(m.get("project_name")), "run_id": run_id, "ingested_at": now})
    merge_rows("video_tags_tier2", tags, ["video_id"])
    merge_rows("property_mentions", mentions, ["mention_id"])


def project_key(name: str | None) -> str | None:
    import re

    if not name:
        return None
    k = re.sub(r"[^a-z0-9]+", " ", name.lower())
    k = re.sub(r"\b(by|the|tower|towers|residences?|project|dubai|uae)\b", " ", k)
    return " ".join(k.split()) or None


def apply_flags() -> dict[str, int]:
    videos = dml(f"""UPDATE `{t('videos')}` v SET is_relevant = g.is_relevant,
            relevance_reason = g.relevance_reason, relevance_source = 'tier2'
        FROM `{t('video_tags_tier2')}` g
        WHERE g.video_id = v.video_id AND g.prompt_version = @pv
          AND IFNULL(v.relevance_source, '') NOT IN ('rule', 'manual')""", {"pv": tier2_text.PROMPT_VERSION})
    channels = dml(f"""UPDATE `{t('channels')}` c SET
            relevant_video_count = s.rel, irrelevant_share = s.share,
            is_relevant = NOT (s.share > {CHANNEL_IRRELEVANT_SHARE} OR s.rel < {CHANNEL_MIN_RELEVANT}),
            relevance_reason = CASE
              WHEN s.share > {CHANNEL_IRRELEVANT_SHARE} THEN FORMAT('irrelevant_share %.2f > 0.60', s.share)
              WHEN s.rel < {CHANNEL_MIN_RELEVANT} THEN FORMAT('only %d relevant in-window videos', s.rel)
              ELSE 'ok' END
        FROM (SELECT channel_id, COUNTIF(is_relevant) rel,
                     SAFE_DIVIDE(COUNTIF(is_relevant = FALSE), COUNTIF(is_relevant IS NOT NULL)) share
              FROM `{t('videos')}` WHERE in_window GROUP BY channel_id) s
        WHERE s.channel_id = c.channel_id""")
    # channels with no in-window videos at all
    dml(f"""UPDATE `{t('channels')}` SET is_relevant = FALSE, relevant_video_count = 0,
            relevance_reason = 'no in-window videos'
            WHERE channel_id NOT IN (SELECT DISTINCT channel_id FROM `{t('videos')}` WHERE in_window)
              AND harvest_status IN ('done', 'unavailable')""")
    return {"videos_flag_updates": videos, "channel_updates": channels}


def main(argv: list[str] | None = None) -> int:
    p = base_parser("relevance")
    p.add_argument("--estimate", action="store_true", help="print the cost estimate and exit (no paid calls)")
    p.add_argument("--apply-only", action="store_true")
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("relevance")
    s = get_settings()
    if a.estimate:
        set_window()
        print({"rule": rule_pass(run_id)})
        print(estimate(len(pending(a.limit))))
        return 0
    with job_run("relevance", run_id, dry_run=a.dry_run) as c:
        c["window_rows"] = set_window()
        c.update(rule_pass(run_id))
        if not a.apply_only and not a.dry_run:
            from pitchops.gemini.client import GeminiClient

            todo = pending(a.limit)
            c["tier2_pending"] = len(todo)
            g = GeminiClient(JOB, run_id, phase_prefix="p3_", phase_cap=s.gemini_phase_budget_usd_p3)
            batches = [todo[i: i + tier2_text.BATCH] for i in range(0, len(todo), tier2_text.BATCH)]
            buf: list[dict[str, Any]] = []
            done = failed = 0
            with ThreadPoolExecutor(CONCURRENCY) as ex:
                futs = {ex.submit(tag_batch, g, b): b for b in batches}
                try:
                    for f in as_completed(futs):
                        try:
                            buf.extend(f.result())
                            done += 1
                        except BudgetExhausted:
                            raise
                        except Exception as e:  # leave the batch untagged; the next run retries it
                            failed += 1
                            log("tier2_batch_failed", severity="WARNING", error=f"{type(e).__name__}: {e}"[:300])
                        if done and done % FLUSH_CALLS == 0:
                            flush(buf, run_id)
                            buf = []
                            log("tier2_progress", calls_done=done, failed=failed, of=len(batches),
                                spend=g.budget.status())
                except BudgetExhausted as e:
                    log("BUDGET_EXHAUSTED", severity="WARNING", detail=str(e))
                    c["_status"] = "BUDGET_EXHAUSTED"
                    for fut in futs:
                        fut.cancel()
            flush(buf, run_id)
            c.update(tier2_calls_ok=done, tier2_calls_failed=failed)
        if not a.dry_run:
            c.update(apply_flags())
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
