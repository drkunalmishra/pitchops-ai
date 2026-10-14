"""Tier-1 scoring job: latest metric snapshot per video -> OPI -> video_scores (full recompute, idempotent)."""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime

from google.cloud import bigquery

from pitchops.bq import client, query, schema_for
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.scoring.opi import score_videos


def main(argv: list[str] | None = None) -> int:
    a = base_parser("score").parse_args(argv)
    run_id = a.run_id or new_run_id("score")
    t = get_settings().table
    with job_run("score", run_id, dry_run=a.dry_run) as c:
        rows = query(f"""
            SELECT v.video_id, v.channel_id, v.is_short, v.duration_sec, v.published_at,
                   m.view_count, m.like_count, m.comment_count, m.snapshot_date, s.intent_rate
            FROM `{t('v_videos_relevant')}` v  -- D2/D3: in-window, relevant videos of relevant channels only
            LEFT JOIN `{t('audience_summaries')}` s USING (video_id)
            JOIN (SELECT * FROM `{t('video_metrics_daily')}`
                  QUALIFY ROW_NUMBER() OVER (PARTITION BY video_id ORDER BY snapshot_date DESC) = 1) m
            USING (video_id)""")
        if a.limit:
            rows = rows[: a.limit]
        snap = max((r["snapshot_date"] for r in rows), default=date.today())
        scores = score_videos(rows, snap)
        c.update(videos=len(rows), scored=sum(1 for s in scores if s["opi"] is not None))
        if not a.dry_run and scores:
            now = datetime.now(UTC).isoformat()
            payload = [{**s, "run_id": run_id, "ingested_at": now} for s in scores]
            cfg = bigquery.LoadJobConfig(schema=schema_for("video_scores"), write_disposition="WRITE_TRUNCATE",
                                         source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON)
            client().load_table_from_json(payload, t("video_scores"), job_config=cfg).result()
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
