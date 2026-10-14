"""P3 Steps 4-5 — trending scores, 50-company shortlist (D21) and the deep-analysis selection (D7, D12).

Reads only v_videos_relevant. Usage: uv run python -m jobs.trending [--top 50] [--min-videos 10] [--per-company 10]
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from google.cloud import bigquery

from pitchops.bq import client, query, schema_for
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.scoring.trending import trending_scores

MAX_PER_COMPANY = 12
OUTLIER_EXTRA = 3.0


def t(name: str) -> str:
    return get_settings().table(name)


def truncate_load(table: str, rows: list[dict], run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    cfg = bigquery.LoadJobConfig(schema=schema_for(table), write_disposition="WRITE_TRUNCATE",
                                 source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON)
    client().load_table_from_json([{**r, "run_id": run_id, "ingested_at": now} for r in rows], t(table),
                                  job_config=cfg).result()


def main(argv: list[str] | None = None) -> int:
    p = base_parser("trending")
    p.add_argument("--top", type=int, default=50)
    p.add_argument("--min-videos", type=int, default=10)
    p.add_argument("--per-company", type=int, default=10)
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("trending")
    with job_run("trending", run_id, dry_run=a.dry_run) as c:
        vids = query(f"""
            SELECT v.video_id, v.channel_id, v.published_at, m.view_count, m.like_count, m.comment_count
            FROM `{t('v_videos_relevant')}` v
            JOIN (SELECT * FROM `{t('video_metrics_daily')}`
                  QUALIFY ROW_NUMBER() OVER (PARTITION BY video_id ORDER BY snapshot_date DESC) = 1) m USING (video_id)""")
        scores = trending_scores(vids)
        now = datetime.now(UTC).isoformat()
        c.update(relevant_videos=len(vids), scored=len(scores))
        if a.dry_run:
            return 0
        truncate_load("video_trending", [{**s, "computed_at": now} for s in scores], run_id)

        short = query(f"""
            SELECT ch.company_id, ANY_VALUE(co.office_names_en) AS company_name, SUM(m.view_count) AS total_views,
                   COUNT(DISTINCT v.video_id) AS relevant_videos, COUNT(DISTINCT v.channel_id) AS channels
            FROM `{t('v_videos_relevant')}` v
            JOIN `{t('v_channels_relevant')}` ch USING (channel_id)
            JOIN `{t('companies')}` co ON co.company_id = ch.company_id
            JOIN `{t('video_trending')}` m USING (video_id)
            WHERE ch.company_id IS NOT NULL
              AND (ch.broker_number IS NULL OR ch.harvest_status IN ('done', 'partial'))  -- D12
            GROUP BY ch.company_id HAVING relevant_videos >= {a.min_videos}
            ORDER BY total_views DESC LIMIT {a.top}""".replace("SUM(m.view_count)", "SUM(m.views)"))
        ids = [r["company_id"] for r in short]
        cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", ids)])
        sel = [dict(r) for r in client().query(f"""
            WITH ranked AS (
              SELECT ch.company_id, v.video_id, v.channel_id, tr.trending, tr.outlier,
                     ROW_NUMBER() OVER (PARTITION BY ch.company_id ORDER BY tr.trending DESC) AS rk
              FROM `{t('v_videos_relevant')}` v
              JOIN `{t('v_channels_relevant')}` ch USING (channel_id)
              JOIN `{t('video_trending')}` tr USING (video_id)
              WHERE ch.company_id IN UNNEST(@ids)
                AND (ch.broker_number IS NULL OR ch.harvest_status IN ('done', 'partial')))
            SELECT company_id, video_id, channel_id, trending, outlier, rk FROM ranked
            WHERE rk <= {a.per_company} OR (outlier >= {OUTLIER_EXTRA} AND rk <= {MAX_PER_COMPANY})""",
            job_config=cfg).result()]
        per = {i: 0 for i in ids}
        rows = []
        for r in sorted(sel, key=lambda r: (r["company_id"], r["rk"])):
            reason = "top_trending" if r["rk"] <= a.per_company else "outlier_ge_3"
            rows.append({"video_id": r["video_id"], "company_id": r["company_id"], "channel_id": r["channel_id"],
                         "rank_in_company": r["rk"], "trending": r["trending"], "outlier": r["outlier"],
                         "reason": reason})
            per[r["company_id"]] += 1
        truncate_load("company_shortlist", [{**s, "rank": i + 1, "selected_videos": per[s["company_id"]]}
                                            for i, s in enumerate(short)], run_id)
        truncate_load("deep_selection", rows, run_id)
        c.update(shortlist=len(short), deep_selected=len(rows))
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
