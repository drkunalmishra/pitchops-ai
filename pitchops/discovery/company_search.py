"""Route B — search.list type=channel per registry company (100 units each), largest companies first."""

from __future__ import annotations

from typing import Any

from pitchops.bq import query
from pitchops.config import get_settings
from pitchops.discovery.common import candidate_row, log_search, save_candidates, searched
from pitchops.discovery.names import search_name
from pitchops.logs import log
from pitchops.youtube.client import YouTubeClient

TIERS = ("T1", "T2", "T3")


def pending_companies(limit: int) -> list[dict[str, Any]]:
    t = get_settings().table
    rows = query(
        f"""SELECT c.company_id, c.office_names_en, c.broker_count, c.discovery_tier
        FROM `{t('companies')}` c
        LEFT JOIN (SELECT DISTINCT company_id FROM `{t('channels')}` WHERE company_id IS NOT NULL) a USING (company_id)
        WHERE a.company_id IS NULL AND REGEXP_CONTAINS(c.discovery_tier, r'^T[123]')
        ORDER BY c.discovery_tier, c.broker_count DESC LIMIT @n""", {"n": limit * 3 + 50})
    done = searched("company_search")
    return [r for r in rows if f"company:{r['company_id']}" not in done][:limit]


def search_query(office_names_en: str) -> str | None:
    first = (office_names_en or "").split("|")[0]
    name = search_name(first)
    return f"{name} Dubai real estate" if name else None


def run(yt: YouTubeClient, run_id: str, searches: int, dry_run: bool = False) -> dict[str, int]:
    c = {"searches": 0, "candidates": 0}
    for comp in pending_companies(searches):
        q = search_query(comp["office_names_en"])
        if not q:
            continue
        if dry_run:
            log("dry_search", q=q)
            c["searches"] += 1
            continue
        r = yt.search(q=q, type="channel", maxResults=10, regionCode="AE")
        items = r.get("items", [])
        rows = [candidate_row(i["snippet"]["channelId"], "company_search", q, run_id,
                              title=i["snippet"].get("channelTitle") or i["snippet"].get("title"),
                              description=i["snippet"].get("description"), company_id_guess=comp["company_id"])
                for i in items]
        c["candidates"] += save_candidates(rows)
        log_search(f"company:{comp['company_id']}", "company_search", q, run_id, company_id=comp["company_id"],
                   result_count=len(items))
        c["searches"] += 1
    return c
