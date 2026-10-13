"""Pick one public Dubai property Short and one long-form video for smoke tests (2 x search.list = 200 units)."""

from __future__ import annotations

import json
import sys

from pitchops.config import get_settings
from pitchops.jobrun import new_run_id
from pitchops.youtube.client import YouTubeClient
from pitchops.youtube.quota import BigQueryQuotaStore, QuotaLedger
from scripts.smoke.yt_lookup import iso_dur


def main() -> int:
    s = get_settings()
    run_id = new_run_id("smoke")
    ledger = QuotaLedger(BigQueryQuotaStore(), "smoke", run_id, cap=s.yt_daily_unit_cap)
    yt = YouTubeClient(s.youtube_api_key.get_secret_value(), ledger)
    out: dict = {}
    try:
        for kind, dur in (("short", "short"), ("long", "medium")):
            r = yt.call("search.list", part="snippet", q="Dubai apartment property tour", type="video",
                        videoDuration=dur, regionCode="AE", relevanceLanguage="en", maxResults=10,
                        videoEmbeddable="true")
            ids = [i["id"]["videoId"] for i in r.get("items", [])]
            vs = yt.call("videos.list", part="contentDetails,snippet,status", id=",".join(ids))
            for v in vs["items"]:
                d = iso_dur(v["contentDetails"]["duration"])
                ok = (d <= 60) if kind == "short" else (300 <= d <= 1200)
                if ok and v["status"].get("privacyStatus") == "public":
                    out[kind] = {"video_id": v["id"], "duration_sec": d, "title": v["snippet"]["title"],
                                 "channel_id": v["snippet"]["channelId"],
                                 "channel_title": v["snippet"]["channelTitle"]}
                    break
        # smoke (e): channels.list for the Short's channel (1 unit)
        if "short" in out:
            c = yt.call("channels.list", part="snippet,statistics", id=out["short"]["channel_id"])
            ch = c["items"][0]
            out["channels_list"] = {"channel_id": ch["id"], "handle": ch["snippet"].get("customUrl"),
                                    "subscribers": ch["statistics"].get("subscriberCount"), "units": 1}
    finally:
        yt.close()
    out["quota_used_today"] = ledger.used_today()
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
