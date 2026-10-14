"""Shared discovery helpers: YouTube client factory, candidate + search-log persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.youtube.client import YouTubeClient
from pitchops.youtube.quota import BigQueryQuotaStore, QuotaLedger


def yt_client(job: str, run_id: str) -> YouTubeClient:
    s = get_settings()
    return YouTubeClient(s.youtube_api_key.get_secret_value(),
                         QuotaLedger(BigQueryQuotaStore(), job, run_id, cap=s.yt_daily_unit_cap))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def candidate_row(channel_id: str, route: str, query_text: str, run_id: str, *, title: str | None = None,
                  description: str | None = None, handle: str | None = None, country: str | None = None,
                  company_id_guess: str | None = None, broker_number_guess: str | None = None) -> dict[str, Any]:
    return {"candidate_id": f"{route}:{channel_id}:{company_id_guess or query_text}"[:300], "channel_id": channel_id,
            "handle": handle, "title": title, "description": (description or "")[:5000] or None, "country": country,
            "source_route": route, "source_query": query_text, "company_id_guess": company_id_guess,
            "broker_number_guess": broker_number_guess, "run_id": run_id, "ingested_at": now_iso()}


def save_candidates(rows: list[dict[str, Any]]) -> int:
    return merge_rows("channel_candidates", rows, ["candidate_id"],
                      update_cols=["title", "description", "handle", "country", "run_id", "ingested_at"])


def log_search(key: str, route: str, q: str, run_id: str, *, company_id: str | None = None, page: int = 1,
               next_page_token: str | None = None, result_count: int = 0) -> None:
    merge_rows("discovery_searches", [{
        "search_key": key, "route": route, "query": q, "company_id": company_id, "page": page,
        "next_page_token": next_page_token, "result_count": result_count, "searched_at": now_iso(),
        "run_id": run_id, "ingested_at": now_iso()}], ["search_key"])


def searched(route: str) -> dict[str, dict[str, Any]]:
    rows = query(f"SELECT * FROM `{get_settings().table('discovery_searches')}` WHERE route = @r", {"r": route})
    return {r["search_key"]: r for r in rows}
