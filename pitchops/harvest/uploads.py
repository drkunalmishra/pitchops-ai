"""Harvest uploads of accepted channels + daily metric snapshots. Checkpoints next_page_token per channel."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.harvest.shorts import classify, iso_duration_sec
from pitchops.logs import log
from pitchops.youtube.client import YouTubeClient
from pitchops.youtube.quota import QuotaExhausted

MAX_VIDEOS_PER_CHANNEL = 1000
FLUSH_VIDEOS = 2500
IST = ZoneInfo("Asia/Kolkata")


def snapshot_date() -> str:
    return datetime.now(UTC).astimezone(IST).date().isoformat()


def _int(v: Any) -> int | None:
    return int(v) if v not in (None, "") else None


def video_rows(items: list[dict[str, Any]], run_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now, snap = datetime.now(UTC).isoformat(), snapshot_date()
    vids, mets = [], []
    for v in items:
        sn, cd, st = v.get("snippet", {}), v.get("contentDetails", {}), v.get("statistics", {})
        dur = iso_duration_sec(cd.get("duration"))
        tags = sn.get("tags") or []
        is_short, rule = classify(dur, sn.get("title"), sn.get("description"), tags)
        vids.append({"video_id": v["id"], "channel_id": sn.get("channelId"), "title": sn.get("title"),
                     "description": (sn.get("description") or "")[:5000], "tags": tags[:50],
                     "published_at": sn.get("publishedAt"), "duration_sec": dur, "is_short": is_short,
                     "short_rule": rule, "default_language": sn.get("defaultLanguage") or sn.get("defaultAudioLanguage"),
                     "has_captions": cd.get("caption") == "true", "run_id": run_id, "ingested_at": now})
        mets.append({"video_id": v["id"], "snapshot_date": snap, "view_count": _int(st.get("viewCount")),
                     "like_count": _int(st.get("likeCount")), "comment_count": _int(st.get("commentCount")),
                     "run_id": run_id, "ingested_at": now})
    return vids, mets


class Sink:
    """Buffers video + metric rows and channel checkpoints; flushes with idempotent MERGEs."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.videos: list[dict[str, Any]] = []
        self.metrics: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.totals = {"videos": 0, "metrics": 0, "channels": 0}

    def add(self, items: list[dict[str, Any]]) -> None:
        v, m = video_rows(items, self.run_id)
        self.videos += v
        self.metrics += m

    def flush(self, force: bool = False) -> None:
        if not force and len(self.videos) < FLUSH_VIDEOS:
            return
        if self.videos:
            self.totals["videos"] += merge_rows("videos", self.videos, ["video_id"])
            self.totals["metrics"] += merge_rows("video_metrics_daily", self.metrics, ["video_id", "snapshot_date"])
        if self.checkpoints:
            self.totals["channels"] += merge_rows("channels", self.checkpoints, ["channel_id"], update_cols=[
                "harvest_status", "next_page_token", "last_harvested_at"])
        log("harvest_flush", **self.totals)
        self.videos, self.metrics, self.checkpoints = [], [], []


def channels_to_harvest(limit: int | None) -> list[dict[str, Any]]:
    t = get_settings().table
    rows = query(f"""SELECT channel_id, uploads_playlist_id, harvest_status, next_page_token,
                       (SELECT COUNT(*) FROM `{t('videos')}` v WHERE v.channel_id = c.channel_id) AS have
                     FROM `{t('channels')}` c WHERE harvest_status IN ('new', 'partial')
                     ORDER BY harvest_status = 'partial' DESC, subscriber_count DESC""")
    return rows[:limit] if limit else rows


def harvest_uploads(yt: YouTubeClient, run_id: str, limit: int | None = None) -> dict[str, int]:
    sink = Sink(run_id)
    chans = channels_to_harvest(limit)
    log("harvest_start", channels=len(chans))
    try:
        for ch in chans:
            token, got = ch.get("next_page_token"), int(ch.get("have") or 0)
            status = "partial"
            while True:
                page = yt.playlist_items(ch["uploads_playlist_id"], token)
                ids = [i["contentDetails"]["videoId"] for i in page.get("items", [])]
                if ids:
                    sink.add(yt.videos_by_ids(ids))
                got += len(ids)
                token = page.get("nextPageToken")
                if not token or got >= MAX_VIDEOS_PER_CHANNEL:
                    status = "done"
                    break
            sink.checkpoints.append({"channel_id": ch["channel_id"], "harvest_status": status,
                                     "next_page_token": token if status == "partial" else None,
                                     "last_harvested_at": datetime.now(UTC).isoformat()})
            sink.flush()
    except QuotaExhausted:
        # persist the in-flight channel as partial so the next run resumes from its token
        if "ch" in locals():
            sink.checkpoints.append({"channel_id": ch["channel_id"], "harvest_status": "partial",
                                     "next_page_token": token, "last_harvested_at": datetime.now(UTC).isoformat()})
        sink.flush(force=True)
        raise
    except Exception as e:
        if getattr(e, "response", None) is not None and e.response.status_code == 404:  # type: ignore[attr-defined]
            log("uploads_404", severity="WARNING", channel_id=ch["channel_id"])
        sink.flush(force=True)
        raise
    sink.flush(force=True)
    return sink.totals


def refresh_metrics(yt: YouTubeClient, run_id: str, limit: int | None = None) -> dict[str, int]:
    """Today's snapshot for every harvested video that does not have one yet (1 unit per 50 videos)."""
    t = get_settings().table
    ids = [r["video_id"] for r in query(
        f"""SELECT v.video_id FROM `{t('videos')}` v LEFT JOIN `{t('video_metrics_daily')}` m
            ON m.video_id = v.video_id AND m.snapshot_date = @snapshot_date
            WHERE m.video_id IS NULL""", {"snapshot_date": snapshot_date()})]
    ids = ids[:limit] if limit else ids
    sink = Sink(run_id)
    try:
        for i in range(0, len(ids), 50):
            sink.add(yt.videos_by_ids(ids[i : i + 50]))
            sink.flush()
    finally:
        sink.flush(force=True)
    return {"refresh_candidates": len(ids), **{f"refresh_{k}": v for k, v in sink.totals.items()}}
