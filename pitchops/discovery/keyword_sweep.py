"""Route C — keyword sweeps: search.list type=channel,video (100 units each); nextPageToken persisted per keyword."""

from __future__ import annotations

import json
from pathlib import Path

from pitchops.discovery.common import candidate_row, log_search, save_candidates, searched
from pitchops.youtube.client import YouTubeClient

KEYWORDS = Path(__file__).resolve().parents[2] / "prompts" / "keywords_v1.json"
MAX_PAGES = 3


def run(yt: YouTubeClient, run_id: str, searches: int, dry_run: bool = False) -> dict[str, int]:
    kws = json.loads(KEYWORDS.read_text())["keywords"]
    done = searched("keyword_sweep")
    c = {"searches": 0, "candidates": 0}
    # page 1 for every keyword first, then page 2, ...
    for page in range(1, MAX_PAGES + 1):
        for kw in kws:
            if c["searches"] >= searches:
                return c
            key, prev = f"kw:{kw}:p{page}", f"kw:{kw}:p{page - 1}"
            if key in done:
                continue
            token = None
            if page > 1:
                if prev not in done or not done[prev].get("next_page_token"):
                    continue
                token = done[prev]["next_page_token"]
            c["searches"] += 1
            if dry_run:
                continue
            params = {"q": kw, "type": "channel,video", "maxResults": 50, "regionCode": "AE"}
            if token:
                params["pageToken"] = token
            r = yt.search(**params)
            items = r.get("items", [])
            rows = [candidate_row(i["snippet"]["channelId"], "keyword_sweep", kw, run_id,
                                  title=i["snippet"].get("channelTitle"),
                                  description=i["snippet"].get("description")
                                  if i["id"].get("kind") == "youtube#channel" else None)
                    for i in items]
            c["candidates"] += save_candidates(rows)
            log_search(key, "keyword_sweep", kw, run_id, page=page, next_page_token=r.get("nextPageToken"),
                       result_count=len(items))
    return c
