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


def t(name: str) -> str:
    return get_settings().table(name)


def llm_phase(job: str) -> str:
    return next((p for k, p in LLM_PHASE.items() if job.startswith(k)), "other")


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
    for r in query(f"""SELECT DATE(creation_time, 'Asia/Kolkata') d, SUM(total_bytes_billed) b
                       FROM `region-{s.gcp_region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT GROUP BY 1"""):
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
    }
    from pitchops.fs import client as fs

    fs().collection("finops").document("current").set(summary)
    print("=== FinOps report (estimates) ===")
    for k, v in summary.items():
        print(f"{k:22} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
