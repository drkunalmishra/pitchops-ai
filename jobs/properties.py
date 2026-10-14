"""P4 Part B — "most discussed properties" ranking + 40 media candidates (D18). Reads only v_videos_relevant. No LLM.

Overrides: config/property_aliases.csv (alias -> canonical_name), config/media_property_selection.csv
(property_id -> walkthrough | short | exclude). Usage: uv run python -m jobs.properties [--top 60]
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jobs.personas import load
from pitchops.bq import query
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.properties.normalize import build_canonicals, rank_properties, select_media

CONFIG = Path(__file__).resolve().parents[1] / "config"


def t(name: str) -> str:
    return get_settings().table(name)


def read_csv(name: str) -> list[dict[str, str]]:
    p = CONFIG / name
    if not p.exists():
        return []
    rows = [r for r in csv.DictReader(line for line in p.open() if not line.startswith("#"))]
    return [r for r in rows if any((v or "").strip() for v in r.values())]


def main(argv: list[str] | None = None) -> int:
    p = base_parser("properties")
    p.add_argument("--top", type=int, default=60)
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("properties")
    with job_run("properties", run_id, dry_run=a.dry_run) as c:
        mentions = query(f"""SELECT m.video_id, m.project_name, m.developer, m.area, m.emirate, m.property_type,
                                    m.price_text
                             FROM `{t('property_mentions')}` m JOIN `{t('v_videos_relevant')}` v USING (video_id)""")
        vrows = query(f"""
            SELECT v.video_id, v.channel_id, ch.company_id, v.published_at, tr.views,
                   a.video_id IS NOT NULL AS deep, d.sales_pressure_score AS sales_pressure,
                   IF(a.video_id IS NOT NULL, a.buyer_personas, g.buyer_personas_guess) AS personas,
                   IF(a.video_id IS NOT NULL, a.sales_frameworks, g.sales_frameworks_guess) AS frameworks
            FROM `{t('v_videos_relevant')}` v JOIN `{t('v_channels_relevant')}` ch USING (channel_id)
            LEFT JOIN `{t('video_trending')}` tr USING (video_id)
            LEFT JOIN `{t('video_analysis')}` a ON a.video_id = v.video_id AND a.status = 'succeeded'
            LEFT JOIN `{t('video_metrics_derived')}` d ON d.video_id = v.video_id
            LEFT JOIN `{t('video_tags_tier2')}` g ON g.video_id = v.video_id""")
        videos = {r["video_id"]: r for r in vrows}
        aliases = {r["alias"]: r["canonical_name"] for r in read_csv("property_aliases.csv")}
        media_over = {r["property_id"]: r["media_type"].strip() for r in read_csv("media_property_selection.csv")}
        canon, mapping = build_canonicals(mentions, aliases)
        rows = rank_properties(canon, mapping, mentions, videos, datetime.now(UTC))
        select_media(rows, 40, media_over)
        c.update(mentions=len(mentions), raw_names=len(mapping), canonical=len(canon), ranked=len(rows),
                 media=sum(1 for r in rows if r["media_candidate"]))
        if not a.dry_run:
            load("properties_ranked", rows, run_id)
            from pitchops.fs import client as fs

            db = fs()
            batch = db.batch()
            for r in rows[:a.top]:
                batch.set(db.collection("properties_v1").document(r["property_id"][:1400]), r)
            batch.commit()
        print_top(rows, a.top)
    print({"run_id": run_id, **c})
    return 0


def print_top(rows: list[dict[str, Any]], n: int) -> None:
    print(f"{'#':>3} {'media':<11} {'kind':<9} {'property':<34} {'developer':<20} {'videos':>6} {'cos':>4} "
          f"{'views':>11} {'recent':>6}")
    for r in rows[:n]:
        print(f"{r['rank']:>3} {r['media_candidate'] or '':<11} {r['kind']:<9} {r['canonical_name'][:34]:<34} "
              f"{(r['developer'] or '')[:20]:<20} {r['videos']:>6} {r['companies']:>4} {r['total_views']:>11,} "
              f"{r['recent_videos']:>6}")


if __name__ == "__main__":
    sys.exit(main())
