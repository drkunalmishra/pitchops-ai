"""Trending score (pure; P3 Step 4). Computed on relevant in-window videos only (v_videos_relevant).

baseline  = median views of the same channel's OTHER videos posted within ±90 days (needs >= 5), else channel median
outlier   = views / max(baseline, 1)
eng_rate  = (likes + comments) / max(views, 1)
z_eng     = robust z of eng_rate within the channel: (x - median) / (1.4826 * MAD); 0 when MAD = 0
trending  = 0.65 * log2(max(outlier, 0.01)) + 0.35 * clamp(z_eng, -3, 3)
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from typing import Any

WINDOW = timedelta(days=90)
MIN_WINDOW_N = 5


def _ts(v: Any) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00")) if isinstance(v, str) else v


def robust_z(xs: list[float]) -> list[float]:
    if not xs:
        return []
    med = median(xs)
    mad = median(abs(x - med) for x in xs)
    if mad == 0:
        return [0.0] * len(xs)
    return [(x - med) / (1.4826 * mad) for x in xs]


def trending_scores(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """videos: video_id, channel_id, published_at, view_count, like_count, comment_count."""
    by_ch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for v in videos:
        if v.get("view_count") is not None:
            by_ch[v["channel_id"]].append(v)
    out = []
    for ch, vs in by_ch.items():
        vs = sorted(vs, key=lambda v: _ts(v["published_at"]))
        views = [float(v["view_count"]) for v in vs]
        ch_median = median(views)
        eng = [((v.get("like_count") or 0) + (v.get("comment_count") or 0)) / max(float(v["view_count"]), 1.0)
               for v in vs]
        zs = robust_z(eng)
        times = [_ts(v["published_at"]) for v in vs]
        for i, v in enumerate(vs):
            near = [views[j] for j in range(len(vs)) if j != i and abs(times[j] - times[i]) <= WINDOW]
            if len(near) >= MIN_WINDOW_N:
                base, kind, n = median(near), "window_90d", len(near)
            else:
                base, kind, n = ch_median, "channel_median", len(vs)
            outlier = views[i] / max(base, 1.0)
            z = max(-3.0, min(3.0, zs[i]))
            out.append({"video_id": v["video_id"], "channel_id": ch, "views": int(views[i]), "baseline": base,
                        "baseline_n": n, "baseline_kind": kind, "outlier": outlier, "eng_rate": eng[i],
                        "z_eng": zs[i], "trending": 0.65 * math.log2(max(outlier, 0.01)) + 0.35 * z})
    return out
