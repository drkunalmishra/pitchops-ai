"""P4 Part A — Persona Database by aggregation (D5). Reads only v_videos_relevant / v_channels_relevant. No LLM.

Writes personas / persona_links / persona_ratings / video_persona_tags (version PERSONA_DB_VERSION, full rebuild)
and the Firestore read-model (personas_v1, persona_links_v1 top 100, persona_db/current).
Persona names are deterministic until Gemini naming (A5) runs — name_source='code'.
Usage: uv run python -m jobs.personas [--version v1.0-pre] [--dry-run]
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any

from google.cloud import bigquery

from pitchops.bq import client, query, schema_for
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.personas.aggregate import aggregate, humanize

DEFAULT_VERSION = "v1.0-pre"
TOP_LINKS_FS = 100


def t(name: str) -> str:
    return get_settings().table(name)


def load_videos() -> list[dict[str, Any]]:
    rows = query(f"""
        SELECT v.video_id, v.channel_id, ch.company_id, v.is_short_candidate,
               tr.trending, tr.eng_rate, sc.opi,
               a.status = 'succeeded' AS deep,
               a.sales_frameworks AS frameworks, a.buyer_personas AS personas, a.buyer_motive AS motive,
               a.buyer_triggers AS triggers, a.origin_personas AS origins, a.archetype AS archetype,
               SAFE_CAST(JSON_VALUE(a.overview, '$.presenter_on_camera') AS BOOL) AS presenter,
               g.sales_frameworks_guess AS g_frameworks, g.buyer_personas_guess AS g_personas,
               g.buyer_motive_guess AS g_motive, g.triggers_guess AS g_triggers,
               g.origin_personas_guess AS g_origins, g.archetype_guess AS g_archetype,
               d.sales_pressure_score AS sales_pressure, d.evidence_density, d.education_to_sales,
               (IFNULL(d.claims_risky, 0) > 0 OR EXISTS(
                  SELECT 1 FROM UNNEST(JSON_QUERY_ARRAY(a.claims)) c
                  WHERE JSON_VALUE(c, '$.claim_type') IN ('roi_yield', 'guarantee')
                    AND JSON_VALUE(c, '$.has_source') = 'false')) AS compliance_risk,
               s.intent_rate, TO_JSON_STRING(s.objection_topics) AS objections_json,
               TO_JSON_STRING(s.top_questions) AS questions_json
        FROM `{t('v_videos_relevant')}` v
        JOIN `{t('v_channels_relevant')}` ch USING (channel_id)
        LEFT JOIN `{t('video_trending')}` tr USING (video_id)
        LEFT JOIN `{t('video_scores')}` sc USING (video_id)
        LEFT JOIN `{t('video_analysis')}` a ON a.video_id = v.video_id AND a.status = 'succeeded'
        LEFT JOIN `{t('video_tags_tier2')}` g ON g.video_id = v.video_id
        LEFT JOIN `{t('video_metrics_derived')}` d ON d.video_id = v.video_id
        LEFT JOIN `{t('audience_summaries')}` s ON s.video_id = v.video_id""")
    for r in rows:
        r["deep"] = bool(r["deep"])
        r["objections"] = json.loads(r.pop("objections_json") or "null") or {}
        r["questions"] = json.loads(r.pop("questions_json") or "null") or []
    return rows


def load(table: str, rows: list[dict[str, Any]], run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    cfg = bigquery.LoadJobConfig(schema=schema_for(table), write_disposition="WRITE_TRUNCATE",
                                 source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON)
    names = {f.name for f in schema_for(table)}
    payload = [{k: v for k, v in {**r, "run_id": run_id, "ingested_at": now}.items() if k in names} for r in rows]
    client().load_table_from_json(payload, t(table), job_config=cfg).result()


def rating_row(version: str, etype: str, eid: str, r: dict[str, Any]) -> dict[str, Any]:
    return {"persona_db_version": version, "entity_type": etype, "entity_id": eid,
            "opi_median": r["opi_median"], "opi_p75": r["opi_p75"], "ces_median": None,
            "engagement_rate_median": r["engagement_rate_median"], "evidence_count": r["video_count"],
            "channel_count": r["channel_count"], "compliance_risk_rate": r["compliance_risk_rate"],
            "confidence": r["confidence"], "score": r["score"], "rating_band": r["rating_band"],
            "trending_median": r["trending_median"], "trending_p75": r["trending_p75"],
            "sales_pressure_median": r["sales_pressure_median"],
            "evidence_density_median": r["evidence_density_median"],
            "education_to_sales_median": r["education_to_sales_median"],
            "buyer_intent_share": r["buyer_intent_share"], "top_objections": r["top_objections"],
            "top_questions": r["top_questions"], "deep_n": r["deep_n"],
            "band_basis": "0.5*pct(OPI median) + 0.5*pct(trending median); CES not computed (ADR-006)"}


def fs_id(s: str) -> str:
    return s.replace("/", "_").replace("|", "__").replace(":", "--").replace("~", "___")[:1400]


def publish_firestore(version: str, personas: list[dict[str, Any]], links: list[dict[str, Any]],
                      summary: dict[str, Any]) -> None:
    from pitchops.fs import client as fs

    db = fs()
    batch, n = db.batch(), 0
    for p in personas:
        doc = {k: v for k, v in p.items() if k not in ("videos",)}
        batch.set(db.collection("personas_v1").document(fs_id(p["persona_id"])), {**doc, "persona_db_version": version})
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = db.batch()
    top = sorted(links, key=lambda r: (-(r["confidence"]), -(r["score"] or -1)))[:TOP_LINKS_FS]
    for i, link in enumerate(top):
        batch.set(db.collection("persona_links_v1").document(fs_id(link["link_id"])),
                  {**link, "rank": i + 1, "persona_db_version": version})
    batch.commit()
    db.collection("persona_db").document("current").set(summary)


def main(argv: list[str] | None = None) -> int:
    p = base_parser("personas")
    p.add_argument("--version", default=DEFAULT_VERSION)
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("personas")
    with job_run("personas", run_id, dry_run=a.dry_run) as c:
        vids = load_videos()
        out = aggregate(vids)
        c.update(videos=len(vids), deep=sum(v["deep"] for v in vids), personas=len(out["personas"]),
                 links=len(out["links"]), tags=len(out["tags"]))
        if a.dry_run:
            print(c)
            return 0
        personas = []
        for r in out["personas"]:
            r["name"] = humanize(r["persona_id"])
            r["name_source"] = "code"
            personas.append(r)
        load("personas", [{**r, "persona_db_version": a.version, "member_count": r["video_count"],
                           "motive": r["code"].split("|")[1] if r["layer"] == "buyer" else None,
                           "description": None} for r in personas], run_id)
        load("persona_links", [{**r, "persona_db_version": a.version, "evidence_count": r["video_count"]}
                               for r in out["links"]], run_id)
        load("persona_ratings", [rating_row(a.version, "persona", r["persona_id"], r) for r in personas]
             + [rating_row(a.version, "link", r["link_id"], r) for r in out["links"]], run_id)
        load("video_persona_tags", [{**tg, "evidence": None} for tg in out["tags"]], run_id)
        summary = {"persona_db_version": a.version, "built_at": datetime.now(UTC).isoformat(),
                   "videos": len(vids), "deep_videos": c["deep"], "personas": len(personas), "links": len(out["links"]),
                   "by_layer": {lay: sum(1 for r in personas if r["layer"] == lay) for lay in ("seller", "buyer", "format")},
                   "names": "code (Gemini naming pending)"}
        publish_firestore(a.version, personas, out["links"], summary)
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
