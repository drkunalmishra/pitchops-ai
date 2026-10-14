"""P3 Step 6 — deep four-table analysis of the selected trending videos (deep_selection ∩ v_videos_relevant).

Usage:
  uv run python -m jobs.deep_analysis --estimate     # cost estimate only
  uv run python -m jobs.deep_analysis --limit 6      # pilot
  uv run python -m jobs.deep_analysis                # full run (resumable; skips analysed videos)
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from pitchops.analysis import deep_video
from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.gemini.budget import BudgetExhausted
from pitchops.gemini.client import SchemaValidationFailed
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log

JOB = "p3_deep"
CONCURRENCY = 4
# defaults until a pilot is measured: P1 smoke showed ~92 input tokens per second of LOW-res video
DEFAULT_TOK_PER_SEC, DEFAULT_OVERHEAD_IN, DEFAULT_OUT = 95.0, 3000.0, 4000.0


def t(name: str) -> str:
    return get_settings().table(name)


def pending(limit: int | None, retry_review: bool = False) -> list[dict[str, Any]]:
    done = "('succeeded')" if retry_review else "('succeeded', 'needs_review')"
    rows = query(f"""
        SELECT d.video_id, d.company_id, v.title, v.duration_sec
        FROM `{t('deep_selection')}` d
        JOIN `{t('v_videos_relevant')}` v USING (video_id)
        LEFT JOIN `{t('video_analysis')}` a ON a.video_id = d.video_id AND a.prompt_version = @pv
             AND a.status IN {done}
        WHERE a.video_id IS NULL AND IFNULL(v.duration_sec, 0) > 0
        ORDER BY d.company_id, d.rank_in_company""", {"pv": deep_video.PROMPT_VERSION})
    return rows[:limit] if limit else rows


def analysed_seconds(duration: int) -> int:
    cov, clips = deep_video.clips_for(duration)
    return sum(b - a for a, b in clips)


def measured() -> tuple[float, float, float, int]:
    """(input tokens per analysed second, fixed input overhead, output tokens per call, n calls measured)."""
    r = query(f"""SELECT AVG(tokens_out) o, COUNT(*) n, SUM(tokens_in) tin,
                         SUM(IF(coverage = 'full', duration_sec, 300)) secs
                  FROM `{t('video_analysis')}` WHERE prompt_version = @pv AND attempts = 1""",
              {"pv": deep_video.PROMPT_VERSION})[0]
    if r["n"] and r["secs"]:
        per_sec = (float(r["tin"]) - DEFAULT_OVERHEAD_IN * r["n"]) / float(r["secs"])
        return max(per_sec, 50.0), DEFAULT_OVERHEAD_IN, float(r["o"]), int(r["n"])
    return DEFAULT_TOK_PER_SEC, DEFAULT_OVERHEAD_IN, DEFAULT_OUT, 0


def estimate(todo: list[dict[str, Any]]) -> dict[str, Any]:
    s = get_settings()
    per_sec, overhead, out, n = measured()
    secs = sum(analysed_seconds(int(v["duration_sec"])) for v in todo)
    tin = secs * per_sec + overhead * len(todo)
    tout = out * len(todo)
    pin, pout = s.price_for(s.gemini_model_flash)
    full = sum(1 for v in todo if int(v["duration_sec"]) <= deep_video.FULL_MAX_SEC)
    return {"videos": len(todo), "full_coverage": full, "partial_3_clips": len(todo) - full,
            "analysed_minutes": round(secs / 60, 1), "tokens_per_sec": round(per_sec, 1),
            "out_tokens_per_call": round(out), "measured_from": n, "est_tokens_in_M": round(tin / 1e6, 2),
            "est_tokens_out_M": round(tout / 1e6, 2), "est_usd": round((tin * pin + tout * pout) / 1e6, 2),
            "est_usd_with_10pct_repairs": round(1.1 * (tin * pin + tout * pout) / 1e6, 2), "model": s.gemini_model_flash}


def analyse(g: Any, v: dict[str, Any]) -> dict[str, Any]:
    from pitchops.gemini.client import youtube_part

    s = get_settings()
    dur = int(v["duration_sec"])
    coverage, clips = deep_video.clips_for(dur)
    url = f"https://www.youtube.com/watch?v={v['video_id']}"
    parts: list[Any] = [youtube_part(url) if coverage == "full" else youtube_part(url, a, b) for a, b in clips]
    parts.append(deep_video.clip_note(coverage, clips, dur)
                 + f"\n<untrusted_metadata>title: {(v.get('title') or '')[:200]}</untrusted_metadata>")
    base = {"video_id": v["video_id"], "prompt_version": deep_video.PROMPT_VERSION, "model_id": s.gemini_model_flash,
            "coverage": coverage, "clips": [{"start": a, "end": b} for a, b in clips], "duration_sec": dur}
    try:
        res = g.generate_json(s.gemini_model_flash, parts, deep_video.schema(), media_resolution="low",
                              prompt_version=deep_video.PROMPT_VERSION, temperature=0.2, system=deep_video.SYSTEM,
                              thinking="low",
                              validator=lambda d: (deep_video.normalize_mmss(d, dur) and False)
                              or deep_video.validate(d, dur, coverage, clips))
    except SchemaValidationFailed as e:
        return {**base, "status": "needs_review", "error": str(e)[:1000], "validation_errors": [str(e)[:300]],
                "attempts": 2}
    d = res.data
    ov = d["overview"]
    return {**base, "status": "succeeded", "overview": ov, "segments": d["segments"], "claims": d["claims"],
            "property_mentions": d["property_mentions"], "archetype": ov["archetype"], "hook_type": ov["hook_type"],
            "sales_frameworks": ov["sales_frameworks"], "buyer_personas": ov["buyer_personas"],
            "buyer_motive": ov["buyer_motive"], "buyer_triggers": ov["buyer_triggers"],
            "origin_personas": ov["origin_personas"], "cta_type": ov["cta_type"], "language": ov["language"],
            "validation_errors": [], "tokens_in": res.tokens_in, "tokens_out": res.tokens_out,
            "cost_usd_est": res.cost_usd_est, "attempts": res.attempts,
            "_derived": deep_video.derived_metrics(d, sum(b - a for a, b in clips))}


def flush(rows: list[dict[str, Any]], run_id: str) -> None:
    from jobs.relevance import project_key

    if not rows:
        return
    now = datetime.now(UTC).isoformat()
    analyses, derived, mentions = [], [], []
    for r in rows:
        dm = r.pop("_derived", None)
        analyses.append({**r, "run_id": run_id, "ingested_at": now})
        if dm:
            derived.append({"video_id": r["video_id"], "prompt_version": r["prompt_version"], **dm,
                            "run_id": run_id, "ingested_at": now})
        for i, m in enumerate(r.get("property_mentions") or []):
            if any(m.get(k) for k in ("project_name", "developer", "area")):
                mentions.append({"mention_id": f"{r['video_id']}:deep:{i}", "video_id": r["video_id"],
                                 "source_tier": "deep", "ts_sec": m.get("ts_sec"),
                                 **{k: m.get(k) for k in ("project_name", "developer", "area", "emirate",
                                                          "property_type", "price_text")},
                                 "project_key": project_key(m.get("project_name")), "run_id": run_id,
                                 "ingested_at": now})
    merge_rows("video_analysis", analyses, ["video_id"])
    merge_rows("video_metrics_derived", derived, ["video_id"])
    merge_rows("property_mentions", mentions, ["mention_id"])


def apply_relevance_recheck() -> int:
    """Watching the video beats reading its title: a deep analysis that finds no UAE real-estate content
    flags the video irrelevant (relevance_source='deep'); it then drops out of v_videos_relevant (D3)."""
    from jobs.relevance import dml

    return dml(f"""UPDATE `{t('videos')}` v SET is_relevant = FALSE, relevance_source = 'deep',
            relevance_reason = CONCAT('deep: ', JSON_VALUE(a.overview, '$.relevance_note'))
        FROM `{t('video_analysis')}` a
        WHERE a.video_id = v.video_id AND a.status = 'succeeded'
          AND JSON_VALUE(a.overview, '$.is_uae_real_estate') = 'false'
          AND IFNULL(v.relevance_source, '') != 'manual'""")


def main(argv: list[str] | None = None) -> int:
    p = base_parser("deep_analysis")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--retry-review", action="store_true", help="also re-run videos currently in needs_review")
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("deep")
    s = get_settings()
    todo = pending(a.limit, a.retry_review)
    if a.estimate or a.dry_run:
        print(estimate(todo))
        return 0
    from pitchops.gemini.client import GeminiClient

    g = GeminiClient(JOB, run_id, phase_prefix="p3_", phase_cap=s.gemini_phase_budget_usd_p3)
    with job_run("deep_analysis", run_id) as c:
        buf: list[dict[str, Any]] = []
        ok = review = failed = 0
        with ThreadPoolExecutor(CONCURRENCY) as ex:
            futs = [ex.submit(analyse, g, v) for v in todo]
            try:
                for f in as_completed(futs):
                    try:
                        r = f.result()
                    except BudgetExhausted:
                        raise
                    except Exception as e:  # API errors: left pending, retried next run
                        failed += 1
                        log("deep_failed", severity="WARNING", error=f"{type(e).__name__}: {e}"[:300])
                        continue
                    ok += r["status"] == "succeeded"
                    review += r["status"] == "needs_review"
                    buf.append(r)
                    if len(buf) >= 5:
                        flush(buf, run_id)
                        buf = []
                        log("deep_progress", succeeded=ok, needs_review=review, failed=failed, of=len(todo),
                            spend=g.budget.status())
            except BudgetExhausted as e:
                log("BUDGET_EXHAUSTED", severity="WARNING", detail=str(e))
                c["_status"] = "BUDGET_EXHAUSTED"
                for fut in futs:
                    fut.cancel()
        flush(buf, run_id)
        c.update(selected=len(todo), succeeded=ok, needs_review=review, api_failed=failed)
        c["relevance_downgraded"] = apply_relevance_recheck()
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
