"""P4 Part C — company reports. Full reports (Gemini Flash) for shortlisted companies with deep analyses; light
reports (Flash-Lite, Tier-2 tags + metrics) for other relevant companies with >= 3 relevant videos.

Numbers + four tables are computed in code; Gemini writes only the cited narrative (pitchops.reports.company).
Stores company_reports (BigQuery, MERGE on company_id), Firestore company_reports_v1 and Markdown in the private
bucket (reports/<company_id>.md). Every report is labelled "internal draft".
Usage:
  uv run python -m jobs.company_reports --estimate
  uv run python -m jobs.company_reports [--type full|light|all] [--limit N] [--concurrency 2]
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from pitchops.bq import merge_rows
from pitchops.config import get_settings
from pitchops.gemini.budget import BudgetExhausted
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.reports import company as rep
from services.api import explore as ex

JOB = "p4_company_reports"
P4_CAP = 15.0
MIN_VIDEOS = 3
EST = {"full": (9000, 1300), "light": (5000, 1000)}


def targets(kind: str) -> list[dict[str, Any]]:
    cs = ex._companies()
    full = [c for c in cs if c["report_type"] == "full"]
    light = [c for c in cs if c["report_type"] == "light" and c["videos"] >= MIN_VIDEOS]
    return {"full": full, "light": light, "all": full + light}[kind]


def bundle(c: dict[str, Any]) -> dict[str, Any]:
    t = ex.t
    vids = ex.rows(f"""SELECT {ex.VIDEO_COLS} FROM `{t('v_videos_relevant')}` v {ex.video_joins()}
        WHERE c.company_id = @c ORDER BY deep DESC, tr.trending DESC LIMIT 10""", {"c": c["company_id"]})
    if c["report_type"] == "light":
        vids = ex.rows(f"""SELECT v.video_id, v.title, v.duration_sec, v.is_short, tr.views, ROUND(tr.trending, 2) trending,
                g.topic, g.sales_frameworks_guess, g.buyer_personas_guess, FALSE deep
            FROM `{t('v_videos_relevant')}` v JOIN `{t('channels')}` c USING (channel_id)
            LEFT JOIN `{t('video_trending')}` tr USING (video_id)
            LEFT JOIN `{t('video_tags_tier2')}` g ON g.video_id = v.video_id
            WHERE c.company_id = @c ORDER BY tr.trending DESC LIMIT 10""", {"c": c["company_id"]})
    for v in vids:
        if v.get("claims"):
            v["claims"] = [{k: x.get(k) for k in ("claim_type", "quote", "has_source", "is_risky")} for x in v["claims"][:4]]
    props = ex.rows(f"""SELECT m.project_name, COUNT(DISTINCT m.video_id) videos
        FROM `{t('property_mentions')}` m JOIN `{t('v_videos_relevant')}` v USING (video_id)
        JOIN `{t('channels')}` ch USING (channel_id)
        WHERE ch.company_id = @c AND m.project_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 8""",
                    {"c": c["company_id"]})
    pressures = [x["sales_pressure"] for x in ex._companies() if x["sales_pressure"] is not None]
    corpus = {"sales_pressure": round(sum(pressures) / len(pressures), 2) if pressures else None}
    return {"company": c, "mix": ex._mix(c["company_id"]), "top_videos": vids, "properties": props,
            "corpus": corpus, "rule_based_gaps": ex.gaps(c, corpus, [v for v in vids if v.get("deep")])}


def report_one(g: Any, c: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    b = bundle(c)
    allowed = {v["video_id"] for v in b["top_videos"]}
    model = s.gemini_model_flash if c["report_type"] == "full" else s.gemini_model_lite
    res = g.generate_json(model, [rep.prompt(b)], rep.schema(), prompt_version=rep.PROMPT_VERSION, temperature=0.3,
                          system=rep.SYSTEM, thinking="low" if c["report_type"] == "full" else None,
                          validator=lambda d: rep.validate(d, allowed))
    md = rep.markdown(c["name"], c["report_type"], b, res.data)
    uri = None
    try:
        from pitchops.gcs import upload_bytes

        uri = upload_bytes(f"reports/{c['company_id']}.md", md.encode(), "text/markdown")
    except Exception as e:  # noqa: BLE001 — the report itself is stored in BigQuery/Firestore regardless
        log("report_gcs_failed", severity="WARNING", company_id=c["company_id"], error=str(e)[:200])
    return {"company_id": c["company_id"], "report_type": c["report_type"], "company_name": c["name"],
            "report": {**res.data, "label": "internal draft"}, "markdown": md, "video_ids": rep.cited_ids(res.data),
            "gcs_uri": uri, "model_id": model, "prompt_version": rep.PROMPT_VERSION, "status": "succeeded"}


def save(rows: list[dict[str, Any]], run_id: str) -> None:
    if not rows:
        return
    from pitchops.fs import client as fs

    now = datetime.now(UTC).isoformat()
    merge_rows("company_reports", [{**r, "ingested_at": now, "run_id": run_id} for r in rows], ["company_id"])
    db = fs()
    for r in rows:
        db.collection("company_reports_v1").document(r["company_id"]).set(
            {k: r[k] for k in ("company_id", "report_type", "company_name", "markdown", "gcs_uri")}
            | {"headline": r["report"]["headline"], "label": "internal draft", "updated_at": now})


def main(argv: list[str] | None = None) -> int:
    p = base_parser("company_reports")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--type", default="all", choices=["full", "light", "all"])
    p.add_argument("--concurrency", type=int, default=2)
    a = p.parse_args(argv)
    s = get_settings()
    from pitchops.bq import query

    done = {r["company_id"] for r in query(f"""SELECT company_id FROM `{ex.t('company_reports')}`
        WHERE status = 'succeeded'""")}
    todo = [c for c in targets(a.type) if c["company_id"] not in done]
    todo = todo[: a.limit] if a.limit else todo
    if a.estimate or a.dry_run:
        est = 0.0
        for kind, model in (("full", s.gemini_model_flash), ("light", s.gemini_model_lite)):
            n = sum(c["report_type"] == kind for c in todo)
            pin, pout = s.price_for(model)
            est += n * (EST[kind][0] * pin + EST[kind][1] * pout) / 1e6
        kinds = [c["report_type"] for c in todo]
        print({"full": kinds.count("full"), "light": kinds.count("light"),
               "est_usd_with_15pct_repairs": round(est * 1.15, 2)})
        return 0
    from pitchops.gemini.client import GeminiClient

    run_id = a.run_id or new_run_id("reports")
    g = GeminiClient(JOB, run_id, phase_prefix="p4_", phase_cap=P4_CAP)
    out: list[dict[str, Any]] = []
    with job_run("company_reports", run_id) as c:
        failed = 0
        with ThreadPoolExecutor(a.concurrency) as pool:
            futs = {pool.submit(report_one, g, co): co["company_id"] for co in todo}
            for f in as_completed(futs):
                try:
                    out.append(f.result())
                    if len(out) % 10 == 0:
                        save(out[-10:], run_id)
                except BudgetExhausted as e:
                    c["_status"] = "BUDGET_EXHAUSTED"
                    log("BUDGET_EXHAUSTED", severity="WARNING", detail=str(e))
                    break
                except Exception as e:  # noqa: BLE001 — one failure must not stop the run
                    failed += 1
                    log("report_failed", severity="WARNING", company_id=futs[f], error=f"{type(e).__name__}: {e}"[:300])
        save(out[len(out) - len(out) % 10:], run_id)
        c.update(targets=len(todo), written=len(out), failed=failed, spend=g.budget.status())
    print({"run_id": run_id, **{k: v for k, v in c.items() if k != "spend"}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
