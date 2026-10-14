"""Harvest job: uploads of accepted channels (new/partial first) + today's metrics for all videos.

Usage: uv run python -m jobs.harvest [--limit N] [--run-id ID] [--dry-run]
"""

from __future__ import annotations

import os
import sys

from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.youtube.quota import QuotaExhausted


def main(argv: list[str] | None = None) -> int:
    a = base_parser("harvest").parse_args(argv)
    if os.environ.get("CORPUS_FROZEN", "").lower() == "true":
        log("corpus_frozen", job="harvest")
        return 0
    run_id = a.run_id or new_run_id("harvest")
    from pitchops.discovery.common import yt_client
    from pitchops.harvest import uploads

    if a.dry_run:
        print({"channels_to_harvest": len(uploads.channels_to_harvest(a.limit))})
        return 0
    yt = yt_client("harvest", run_id)
    with job_run("harvest", run_id) as c:
        try:
            from pitchops.discovery.review import apply_decisions

            c.update(apply_decisions(yt, run_id))
            c.update(uploads.harvest_uploads(yt, run_id, a.limit))
            c.update(uploads.refresh_metrics(yt, run_id))
        except QuotaExhausted as e:
            log("QUOTA_EXHAUSTED", severity="WARNING", detail=str(e))
            c["_status"] = "QUOTA_EXHAUSTED"
        finally:
            yt.close()
            c["quota_used_today"] = yt.ledger.used_today()
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
