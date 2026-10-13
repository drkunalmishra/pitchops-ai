"""Common job scaffolding: --dry-run / --limit / --run-id flags and a job_runs record."""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from pitchops.logs import log


def base_parser(job: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=job)
    p.add_argument("--dry-run", action="store_true", help="read and validate only; write nothing")
    p.add_argument("--limit", type=int, default=None, help="process at most N items")
    p.add_argument("--run-id", default=None, help="explicit run id (default: generated)")
    return p


def new_run_id(job: str) -> str:
    return f"{job}-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


@contextmanager
def job_run(job: str, run_id: str, dry_run: bool = False) -> Iterator[dict[str, Any]]:
    """Yields a counters dict; records the run in job_runs (skipped on dry runs)."""
    counters: dict[str, Any] = {}
    started = datetime.now(UTC)
    status, error = "SUCCESS", None
    log("job_start", job=job, run_id=run_id, dry_run=dry_run)
    try:
        yield counters
        status = counters.pop("_status", "SUCCESS")
    except Exception as e:  # recorded, then re-raised
        status, error = "FAILED", f"{type(e).__name__}: {e}"[:2000]
        raise
    finally:
        log("job_end", job=job, run_id=run_id, status=status, counters=counters, error=error)
        if not dry_run:
            from pitchops.bq import insert_rows

            now = datetime.now(UTC).isoformat()
            insert_rows("job_runs", [{
                "run_id": run_id, "job": job, "started_at": started.isoformat(), "ended_at": now,
                "status": status, "counters": json.dumps(counters, default=str), "error": error,
                "ingested_at": now,
            }])
