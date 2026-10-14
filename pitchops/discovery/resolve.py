"""Enrich candidates (channels.list), run the matcher, MERGE channel_matches and accepted channels."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.discovery.common import now_iso
from pitchops.discovery.matcher import Registry, match_channel
from pitchops.logs import log
from pitchops.youtube.client import YouTubeClient

HUMAN = ("manual_accept", "manual_reject")


def load_registry() -> Registry:
    t = get_settings().table
    companies = query(f"SELECT company_id, office_names_en, primary_domain, corporate_domains, broker_count "
                      f"FROM `{t('companies')}`")
    brokers = query(f"SELECT broker_number, name_en, company_id FROM `{t('brokers')}`")
    return Registry.from_rows(companies, brokers)


def channel_row(ch: dict[str, Any], m: dict[str, Any], run_id: str) -> dict[str, Any]:
    sn, st = ch.get("snippet", {}), ch.get("statistics", {})
    uploads = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads") or "UU" + ch["id"][2:]
    return {"channel_id": ch["id"], "title": sn.get("title"), "handle": sn.get("customUrl"),
            "uploads_playlist_id": uploads, "subscriber_count": int(st.get("subscriberCount", 0) or 0),
            "video_count": int(st.get("videoCount", 0) or 0), "view_count": int(st.get("viewCount", 0) or 0),
            "country": sn.get("country"), "company_id": m["company_id"], "broker_number": m["broker_number"],
            "match_type": m["match_type"], "harvest_status": "new", "run_id": run_id, "ingested_at": now_iso()}


def upsert_channels(rows: list[dict[str, Any]]) -> int:
    """Insert new accepted channels; on re-match update identity/stats but never the harvest checkpoint."""
    return merge_rows("channels", rows, ["channel_id"], update_cols=[
        "title", "handle", "uploads_playlist_id", "subscriber_count", "video_count", "view_count", "country",
        "company_id", "broker_number", "match_type", "run_id", "ingested_at"])


def run(yt: YouTubeClient, run_id: str) -> dict[str, int]:
    t = get_settings().table
    cands = query(f"SELECT * FROM `{t('channel_candidates')}`")
    human = {r["channel_id"] for r in query(
        f"SELECT channel_id FROM `{t('channel_matches')}` WHERE decision IN UNNEST(@h)".replace(
            "UNNEST(@h)", "('manual_accept','manual_reject')"))}
    by_ch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cands:
        if c["channel_id"] not in human:
            by_ch[c["channel_id"]].append(c)
    log("resolve_start", channels=len(by_ch), human_locked=len(human))
    reg = load_registry()
    details = {ch["id"]: ch for ch in yt.channels_by_ids(list(by_ch))}
    matches, accepted = [], []
    for cid, rows in by_ch.items():
        ch = details.get(cid)
        if not ch:
            continue
        sn = ch.get("snippet", {})
        m = match_channel({"channel_id": cid, "title": sn.get("title"), "handle": sn.get("customUrl"),
                           "description": sn.get("description"), "country": sn.get("country")}, rows, reg)
        m["signals"]["thumbnail"] = (sn.get("thumbnails", {}).get("default") or {}).get("url")
        m["signals"]["title"] = sn.get("title")
        m["signals"]["handle"] = sn.get("customUrl")
        m["signals"]["subscribers"] = int(ch.get("statistics", {}).get("subscriberCount", 0) or 0)
        m["signals"]["videos"] = int(ch.get("statistics", {}).get("videoCount", 0) or 0)
        if m["broker_number"] and not m["company_id"]:
            m["company_id"] = reg.broker_company.get(m["broker_number"])
        matches.append({**m, "decided_by": "matcher_v1", "decided_at": now_iso(), "run_id": run_id,
                        "ingested_at": now_iso()})
        if m["decision"] == "auto_accept":
            accepted.append(channel_row(ch, m, run_id))
    merge_rows("channel_matches", matches, ["channel_id"])
    upsert_channels(accepted)
    withdrawn = withdraw_unaccepted()
    dec: dict[str, int] = defaultdict(int)
    for m in matches:
        dec[m["decision"]] += 1
    return {"channels_matched": len(matches), "accepted_new_or_updated": len(accepted), "withdrawn": withdrawn, **dec}


def withdraw_unaccepted() -> int:
    """Keep `channels` == accepted matches: drop channels whose latest decision is no longer an accept,
    together with any videos / metrics already harvested for them (derived data, re-harvestable)."""
    from pitchops.bq import client

    t = get_settings().table
    gone = f"(SELECT channel_id FROM `{t('channel_matches')}` WHERE decision NOT IN ('auto_accept', 'manual_accept'))"
    n = 0
    for sql in (
        f"DELETE FROM `{t('video_metrics_daily')}` WHERE video_id IN "
        f"(SELECT video_id FROM `{t('videos')}` WHERE channel_id IN {gone})",
        f"DELETE FROM `{t('videos')}` WHERE channel_id IN {gone}",
        f"DELETE FROM `{t('channels')}` WHERE channel_id IN {gone}",
    ):
        job = client().query(sql)
        job.result()
        n = job.num_dml_affected_rows or 0  # last statement = channels removed
    return int(n)
