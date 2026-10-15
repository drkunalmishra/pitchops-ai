"""P3 Step 8 — FinOps ledger (D14) and report. Rebuilds finops_ledger from llm_calls, quota_ledger, job_runs and
BigQuery job metadata, prints spend by phase / stage / provider, and writes Firestore finops/current for the UI.

All figures are ESTIMATES (list prices, before free tiers / trial credits). Real spend: Billing -> Reports.
Usage: uv run python -m jobs.finops_report
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from google.cloud import bigquery

from pitchops.bq import client, query, schema_for
from pitchops.config import get_settings

CLOUD_RUN_USD_PER_SEC = 0.000024 + 0.0000025  # 1 vCPU + 1 GiB, list price
BQ_USD_PER_TIB = 6.25
JOB_PHASE = {"smoke": "P1", "load_registry": "P1", "discover": "P2", "harvest": "P2", "score": "P2",
             "match_preview": "P2", "relevance": "P3", "trending": "P3", "deep_analysis": "P3", "comments": "P3"}
LLM_PHASE = {"p3_": "P3", "p4_": "P4", "p5_": "P5", "p6_": "P6", "p7_": "P7", "smoke": "P1"}
# remaining-phase projections (USD) from the phase prompts / D15; updated as phases are quoted
PROJECTION = {"P4": 5.0, "P5": 1.0, "P6": 6.0, "P7": 120.0}


TRIAL_CREDIT_USD = 300.0
PHASE_CAPS = {"P1": 5.0, "P2": 5.0, "P4": 15.0, "P5": 5.0, "P6": 20.0, "P7": 120.0}


def unit_costs(by_phase: dict[str, float]) -> dict[str, Any]:
    """Cost per output unit (USD). Deep analyses done by hand in AI Studio cost $0 to the project and are excluded."""
    r = query(f"""SELECT
        (SELECT COUNT(*) FROM `{t('video_analysis')}` WHERE status = 'succeeded' AND tokens_in IS NOT NULL) vertex_deep,
        (SELECT COUNT(*) FROM `{t('video_analysis')}` WHERE status = 'succeeded' AND tokens_in IS NULL) manual_deep,
        (SELECT IFNULL(SUM(cost_usd_est), 0) FROM `{t('llm_calls')}` WHERE job LIKE 'p3_deep%') deep_usd,
        (SELECT COUNT(*) FROM `{t('video_tags_tier2')}`) tier2_videos,
        (SELECT IFNULL(SUM(cost_usd_est), 0) FROM `{t('llm_calls')}` WHERE job LIKE 'p3_tier2%') tier2_usd""")[0]
    per = lambda usd, n: round(float(usd) / n, 5) if n else None  # noqa: E731
    return {"per_deep_video_vertex": per(r["deep_usd"], r["vertex_deep"]), "vertex_deep_videos": r["vertex_deep"],
            "manual_deep_videos": r["manual_deep"], "per_tier2_video": per(r["tier2_usd"], r["tier2_videos"]),
            "per_report": None, "per_script": None, "per_rendered_second": None}


def t(name: str) -> str:
    return get_settings().table(name)


def llm_phase(job: str) -> str:
    return next((p for k, p in LLM_PHASE.items() if job.startswith(k)), "other")


BQ_SCOPE = {"value": "project"}


def bq_bytes_by_day(region: str) -> list[dict[str, Any]]:
    """Project-wide bytes billed needs bigquery.jobs.listAll. Without it (the jobs service account) fall back to this
    identity's own jobs, or to the BigQuery rows of the last full run (owner run), and say so in the summary."""
    from google.api_core.exceptions import Forbidden

    sql = """SELECT DATE(creation_time, 'Asia/Kolkata') d, SUM(total_bytes_billed) b
             FROM `region-{r}`.INFORMATION_SCHEMA.{v} GROUP BY 1"""
    try:
        return query(sql.format(r=region, v="JOBS_BY_PROJECT"))
    except Forbidden:
        pass
    try:
        rows = query(sql.format(r=region, v="JOBS_BY_USER"))
        BQ_SCOPE["value"] = "own_jobs_only"
        return rows
    except Forbidden:  # no job-history access at all: carry the last full run's BigQuery rows forward
        BQ_SCOPE["value"] = "last_full_run"
        return query(f"""SELECT date AS d, CAST(units * POW(2, 30) AS INT64) b FROM `{t('finops_ledger')}`
                         WHERE provider = 'bigquery'""")


def build_ledger() -> list[dict[str, Any]]:
    s = get_settings()
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    def add(day: Any, phase: str, stage: str, provider: str, units: float, unit_name: str, usd: float) -> None:
        k = (str(day), phase, stage, provider)
        r = rows.setdefault(k, {"ledger_id": ":".join(k), "date": str(day), "phase": phase, "stage": stage,
                                "provider": provider, "units": 0.0, "unit_name": unit_name, "est_cost_usd": 0.0})
        r["units"] += float(units or 0)
        r["est_cost_usd"] += float(usd or 0)

    for r in query(f"""SELECT DATE(ts, 'Asia/Kolkata') d, job, SUM(cost_usd_est) usd, SUM(tokens_in + tokens_out) tok
                       FROM `{t('llm_calls')}` GROUP BY 1, 2"""):
        add(r["d"], llm_phase(r["job"]), r["job"], "vertex_gemini", r["tok"], "tokens", r["usd"])
    for r in query(f"""SELECT DATE(ts, 'Asia/Kolkata') d, job, SUM(units) u FROM `{t('quota_ledger')}` GROUP BY 1, 2"""):
        add(r["d"], JOB_PHASE.get(r["job"], "P3" if r["job"].startswith("p3_") else "other"), r["job"],
            "youtube_api", r["u"], "quota_units", 0.0)
    for r in query(f"""SELECT DATE(started_at, 'Asia/Kolkata') d, job,
                       SUM(TIMESTAMP_DIFF(ended_at, started_at, SECOND)) sec FROM `{t('job_runs')}` GROUP BY 1, 2"""):
        add(r["d"], JOB_PHASE.get(r["job"], "other"), r["job"], "cloud_run", r["sec"], "job_seconds",
            r["sec"] * CLOUD_RUN_USD_PER_SEC)
    for r in bq_bytes_by_day(s.gcp_region):
        add(r["d"], "shared", "bigquery_queries", "bigquery", (r["b"] or 0) / 2**30, "GiB_billed",
            (r["b"] or 0) / 2**40 * BQ_USD_PER_TIB)
    return list(rows.values())


def main() -> int:
    s = get_settings()
    ledger = build_ledger()
    now = datetime.now(UTC).isoformat()
    cfg = bigquery.LoadJobConfig(schema=schema_for("finops_ledger"), write_disposition="WRITE_TRUNCATE",
                                 source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON)
    client().load_table_from_json([{**r, "ts": now, "run_id": "finops", "ingested_at": now} for r in ledger],
                                  t("finops_ledger"), job_config=cfg).result()

    today = datetime.now(UTC).astimezone().date().isoformat()
    by_phase: dict[str, float] = defaultdict(float)
    by_provider: dict[str, float] = defaultdict(float)
    by_stage: dict[str, float] = defaultdict(float)
    today_usd = 0.0
    for r in ledger:
        by_phase[r["phase"]] += r["est_cost_usd"]
        by_provider[r["provider"]] += r["est_cost_usd"]
        by_stage[f"{r['phase']}/{r['stage']}"] += r["est_cost_usd"]
        if r["date"] == today:
            today_usd += r["est_cost_usd"]
    by_day: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    quota_by_day: dict[str, float] = defaultdict(float)
    for r in ledger:
        by_day[r["date"]][r["provider"]] += r["est_cost_usd"]
    for r in query(f"SELECT CAST(day_pt AS STRING) d, SUM(units) u FROM `{t('quota_ledger')}` GROUP BY 1"):
        quota_by_day[r["d"]] += r["u"]  # Pacific-time quota day: the 9,000-unit cap resets at 12:30 IST
    total = sum(by_phase.values())
    p3_gemini = sum(r["est_cost_usd"] for r in ledger if r["phase"] == "P3" and r["provider"] == "vertex_gemini")
    projected = total + sum(PROJECTION.values())
    summary = {
        "as_of": now, "total_usd": round(total, 4), "today_usd": round(today_usd, 4),
        "by_phase": {k: round(v, 4) for k, v in sorted(by_phase.items())},
        "by_provider": {k: round(v, 4) for k, v in sorted(by_provider.items())},
        "top_stages": dict(sorted(((k, round(v, 4)) for k, v in by_stage.items()), key=lambda kv: -kv[1])[:10]),
        "p3_gemini_usd": round(p3_gemini, 4), "p3_cap_usd": s.gemini_phase_budget_usd_p3,
        "p3_cap_pct": round(100 * p3_gemini / s.gemini_phase_budget_usd_p3, 1),
        "project_cap_usd": s.total_project_cap_usd, "project_cap_pct": round(100 * total / s.total_project_cap_usd, 1),
        "projection_remaining": PROJECTION, "projected_total_usd": round(projected, 2),
        "note": "Estimates at list price before free tiers and trial credits. Real spend: Billing -> Reports.",
        "by_day": {d: {k: round(v, 4) for k, v in sorted(p.items())} for d, p in sorted(by_day.items())},
        "quota_by_day": {d: int(u) for d, u in sorted(quota_by_day.items())},
        "quota_cap": s.yt_daily_unit_cap, "trial_credit_usd": TRIAL_CREDIT_USD,
        "phase_caps": PHASE_CAPS | {"P3": s.gemini_phase_budget_usd_p3},
        "unit_costs": unit_costs(by_phase),
        "bigquery_scope": BQ_SCOPE["value"],
    }
    from pitchops.fs import client as fs

    fs().collection("finops").document("current").set(summary)
    print("=== FinOps report (estimates) ===")
    for k, v in summary.items():
        print(f"{k:22} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
