"""Discovery job: website route + company search + keyword sweeps, then enrich + match.

Usage: uv run python -m jobs.discover [--routes website,company,keyword,match] [--searches N] [--kw-searches N]
"""

from __future__ import annotations

import os
import sys

from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.youtube.quota import QuotaExhausted


def main(argv: list[str] | None = None) -> int:
    p = base_parser("discover")
    p.add_argument("--routes", default="website,company,keyword,match")
    p.add_argument("--searches", type=int, default=40, help="company searches (100 units each)")
    p.add_argument("--kw-searches", type=int, default=20, help="keyword searches (100 units each)")
    a = p.parse_args(argv)
    if os.environ.get("CORPUS_FROZEN", "").lower() == "true":
        log("corpus_frozen", job="discover")
        return 0
    routes = a.routes.split(",")
    run_id = a.run_id or new_run_id("discover")
    from pitchops.discovery.common import yt_client

    yt = yt_client("discover", run_id)
    with job_run("discover", run_id, dry_run=a.dry_run) as c:
        try:
            from pitchops.discovery.review import apply_decisions

            if not a.dry_run:
                c.update(apply_decisions(yt, run_id))
            if "website" in routes:
                from pitchops.discovery import website_links

                c["website"] = website_links.run(yt, run_id, limit=a.limit, dry_run=a.dry_run)
            if "company" in routes:
                from pitchops.discovery import company_search

                c["company"] = company_search.run(yt, run_id, a.searches, a.dry_run)
            if "keyword" in routes:
                from pitchops.discovery import keyword_sweep

                c["keyword"] = keyword_sweep.run(yt, run_id, a.kw_searches, a.dry_run)
            if "match" in routes and not a.dry_run:
                from pitchops.discovery import resolve

                c["match"] = resolve.run(yt, run_id)
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
