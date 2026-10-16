"""P4 A5 — Gemini Flash names every persona and the top-30 links from aggregated stats + up to 5 example analyses.

Writes persona_texts (entity_type persona|link, MERGE on entity_type+entity_id), so names survive persona rebuilds.
Usage:
  uv run python -m jobs.persona_naming --estimate
  uv run python -m jobs.persona_naming [--limit N] [--concurrency 2]
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.gemini.budget import BudgetExhausted
from pitchops.gemini.client import SchemaValidationFailed
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.personas import naming

JOB = "p4_persona_naming"
TOP_LINKS = 30
EST_IN, EST_OUT = 3500, 900
P4_CAP = 15.0


def t(name: str) -> str:
    return get_settings().table(name)


def entities(limit: int | None) -> list[dict[str, Any]]:
    pv = f"(SELECT MAX(persona_db_version) FROM `{t('personas')}`)"
    ps = query(f"""SELECT 'persona' kind, p.persona_id eid, p.layer, p.name label, p.member_count, p.deep_videos,
            p.company_count, p.attributes, r.rating_band, r.confidence, r.trending_median, r.opi_median,
            r.sales_pressure_median, r.evidence_density_median, r.compliance_risk_rate, r.top_objections,
            r.top_questions, p.example_video_ids
        FROM `{t('personas')}` p LEFT JOIN `{t('persona_ratings')}` r ON r.entity_type = 'persona'
          AND r.entity_id = p.persona_id AND r.persona_db_version = p.persona_db_version
        WHERE p.persona_db_version = {pv} ORDER BY p.weighted_evidence DESC""")
    links = query(f"""SELECT 'link' kind, l.link_id eid, 'link' layer, l.link_id label, l.video_count member_count,
            l.deep_videos, l.company_count, NULL attributes, r.rating_band, r.confidence, r.trending_median,
            r.opi_median, r.sales_pressure_median, r.evidence_density_median, r.compliance_risk_rate,
            r.top_objections, r.top_questions, l.example_video_ids
        FROM `{t('persona_links')}` l JOIN `{t('persona_ratings')}` r ON r.entity_type = 'link'
          AND r.entity_id = l.link_id AND r.persona_db_version = l.persona_db_version
        WHERE l.persona_db_version = {pv} AND r.confidence >= 0.4 AND r.score IS NOT NULL
        ORDER BY r.score DESC LIMIT {TOP_LINKS}""")
    rows = ps + links
    return rows[:limit] if limit else rows


def examples(e: dict[str, Any]) -> list[dict[str, Any]]:
    """Up to 5 deep-analysed example videos for this persona/link (by trending), else Tier-2 titles."""
    if e["kind"] == "persona":
        code = e["eid"].split(":", 1)[1]
        ids = [r["video_id"] for r in query(f"""SELECT g.video_id FROM `{t('video_persona_tags')}` g
            JOIN `{t('v_videos_relevant')}` v USING (video_id)
            JOIN `{t('video_analysis')}` a ON a.video_id = g.video_id AND a.status = 'succeeded'
            LEFT JOIN `{t('video_trending')}` tr ON tr.video_id = g.video_id
            WHERE g.layer = @l AND g.tag_code = @c ORDER BY tr.trending DESC LIMIT 5""",
                                               {"l": e["layer"], "c": code})]
    else:
        ids = []
    ids = ids or list(e["example_video_ids"] or [])[:5]
    return [{k: v for k, v in r.items() if v is not None} for r in query(f"""SELECT v.video_id, v.title,
            v.duration_sec, JSON_VALUE(a.overview, '$.summary') summary, JSON_VALUE(a.overview, '$.hook_text') hook,
            a.hook_type, a.cta_type, JSON_VALUE(a.overview, '$.cta_text') cta, a.sales_frameworks, a.buyer_personas,
            d.sales_pressure_score, d.verification_status, ROUND(tr.trending, 2) trending
        FROM `{t('videos')}` v
        LEFT JOIN `{t('video_analysis')}` a ON a.video_id = v.video_id AND a.status = 'succeeded'
        LEFT JOIN `{t('video_metrics_derived')}` d ON d.video_id = v.video_id
        LEFT JOIN `{t('video_trending')}` tr ON tr.video_id = v.video_id
        WHERE v.video_id IN UNNEST(@ids)""", {"ids": ids})]


def stats(e: dict[str, Any]) -> dict[str, Any]:
    keep = ("layer", "member_count", "deep_videos", "company_count", "attributes", "rating_band", "confidence",
            "trending_median", "opi_median", "sales_pressure_median", "evidence_density_median",
            "compliance_risk_rate", "top_objections", "top_questions")
    return {k: e[k] for k in keep if e.get(k) is not None}


def name_one(g: Any, e: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    ex = examples(e)
    allowed = {x["video_id"] for x in ex}
    kind = {"seller": "seller persona (sales tactic)", "buyer": "buyer persona (target buyer + motive)",
            "format": "content format", "link": "combination of seller tactic x buyer persona x format"}[e["layer"]]
    res = g.generate_json(s.gemini_model_flash, [naming.prompt(kind, e["label"], stats(e), ex)], naming.schema(),
                          prompt_version=naming.PROMPT_VERSION, temperature=0.3, system=naming.SYSTEM,
                          thinking="low", validator=lambda d: naming.validate(d, allowed))
    d = res.data
    texts = {k: d[k] for k in ("typical_hooks", "typical_ctas", "what_works", "what_to_avoid")}
    return {"entity_type": e["kind"], "entity_id": e["eid"], "name": d["name"], "description": d["description"],
            "texts": {**texts, "description_video_ids": d["description_video_ids"]},
            "video_ids": naming.cited_ids(d), "model_id": s.gemini_model_flash, "prompt_version": naming.PROMPT_VERSION}


def save(rows: list[dict[str, Any]], run_id: str) -> None:
    if rows:
        now = datetime.now(UTC).isoformat()
        merge_rows("persona_texts", [{**r, "ingested_at": now, "run_id": run_id} for r in rows],
                   ["entity_type", "entity_id"])


def main(argv: list[str] | None = None) -> int:
    p = base_parser("persona_naming")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--concurrency", type=int, default=2)
    a = p.parse_args(argv)
    s = get_settings()
    done = {(r["entity_type"], r["entity_id"]) for r in query(f"SELECT entity_type, entity_id FROM `{t('persona_texts')}`")}
    todo = [e for e in entities(None) if (e["kind"], e["eid"]) not in done]
    todo = todo[: a.limit] if a.limit else todo
    pin, pout = s.price_for(s.gemini_model_flash)
    est = round(len(todo) * (EST_IN * pin + EST_OUT * pout) / 1e6 * 1.15, 2)
    if a.estimate or a.dry_run:
        print({"entities": len(todo), "personas": sum(e["kind"] == "persona" for e in todo),
               "links": sum(e["kind"] == "link" for e in todo), "model": s.gemini_model_flash,
               "est_usd_with_15pct_repairs": est})
        return 0
    from pitchops.gemini.client import GeminiClient

    run_id = a.run_id or new_run_id("naming")
    g = GeminiClient(JOB, run_id, phase_prefix="p4_", phase_cap=P4_CAP)
    out: list[dict[str, Any]] = []
    with job_run("persona_naming", run_id) as c:
        ok = failed = 0
        with ThreadPoolExecutor(a.concurrency) as ex:
            futs = {ex.submit(name_one, g, e): e["eid"] for e in todo}
            for f in as_completed(futs):
                try:
                    out.append(f.result())
                    ok += 1
                    if len(out) % 10 == 0:
                        save(out[-10:], run_id)
                except BudgetExhausted as e:
                    c["_status"] = "BUDGET_EXHAUSTED"
                    log("BUDGET_EXHAUSTED", severity="WARNING", detail=str(e))
                    break
                except (SchemaValidationFailed, Exception) as e:  # noqa: BLE001 — one failure must not stop the run
                    failed += 1
                    log("naming_failed", severity="WARNING", entity=futs[f], error=f"{type(e).__name__}: {e}"[:300])
        save(out[len(out) - len(out) % 10:], run_id)
        c.update(entities=len(todo), named=ok, failed=failed, spend=g.budget.status())
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
