"""Smoke (e): channels.list by handle via QuotaLedger; then pick one Short + one long-form upload (1 unit each)."""

from __future__ import annotations

import json
import re
import sys

import httpx

from pitchops.config import get_settings
from pitchops.jobrun import new_run_id
from pitchops.youtube.client import YouTubeClient
from pitchops.youtube.quota import BigQueryQuotaStore, QuotaLedger


def iso_dur(d: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d)
    if not m:
        return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def main(handles: list[str]) -> int:
    s = get_settings()
    run_id = new_run_id("smoke")
    ledger = QuotaLedger(BigQueryQuotaStore(), "smoke", run_id, cap=s.yt_daily_unit_cap)
    yt = YouTubeClient(s.youtube_api_key.get_secret_value(), ledger)
    out: dict = {"run_id": run_id}
    try:
        for h in handles:
            r = yt.call("channels.list", part="snippet,contentDetails,statistics", forHandle=h)
            if not r.get("items"):
                print(f"{h}: not found")
                continue
            ch = r["items"][0]
            out["channel"] = {"handle": h, "channel_id": ch["id"], "title": ch["snippet"]["title"],
                              "videos": ch["statistics"].get("videoCount")}
            uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
            try:
                pl = yt.call("playlistItems.list", part="contentDetails", playlistId=uploads, maxResults=50)
            except httpx.HTTPStatusError as e:
                print(f"{h}: uploads playlist HTTP {e.response.status_code}")
                continue
            ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
            vs = yt.call("videos.list", part="contentDetails,snippet", id=",".join(ids))
            vids = [(v["id"], iso_dur(v["contentDetails"]["duration"]), v["snippet"]["title"]) for v in vs["items"]]
            short = next((v for v in vids if 0 < v[1] <= 60), None)
            longf = next((v for v in vids if 300 <= v[1] <= 1800), None)
            out["short"] = short and {"video_id": short[0], "duration_sec": short[1], "title": short[2]}
            out["long"] = longf and {"video_id": longf[0], "duration_sec": longf[1], "title": longf[2]}
            if short and longf:
                break
    finally:
        yt.close()
    out["quota_used_today"] = ledger.used_today()
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
