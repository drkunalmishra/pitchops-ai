"""Tier-1 Observed Performance Index (pure). Playbook §10.1 / CLAUDE.md §7. Engagement, NOT conversion.

f1 = log(1 + V / max(A,1))          views per day of age
f2 = (L + 4C) / max(V,1)            engagement rate (missing if likes hidden)
f3 = log(1 + V / max(M,1))          vs creator median views (videos older than 7 days)
f4 = I / max(T,1)                   comment buying-intent rate (audience_summaries.intent_rate); null if unsampled
N(f) = clip((f - P10) / (P90 - P10), 0, 1) within cohort (is_short, duration bucket)
OPI = 100 * sum(w_i N_i) / sum(w_available);  confidence = available_weight * sample_quality
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime
from statistics import median
from typing import Any

WEIGHTS = {"f1": 0.35, "f2": 0.25, "f3": 0.25, "f4": 0.15}
MIN_COHORT = 30


def duration_bucket(sec: int | None) -> str:
    s = sec or 0
    return "le60" if s <= 60 else "61-180" if s <= 180 else "181-600" if s <= 600 else "gt600"


def cohort_of(is_short: bool, sec: int | None) -> str:
    return f"{'short' if is_short else 'long'}|{duration_bucket(sec)}"


def percentile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _age_days(published: Any, snap: date) -> float:
    if isinstance(published, str):
        published = datetime.fromisoformat(published.replace("Z", "+00:00"))
    return max((snap - published.date()).days, 0) if published else 0.0


def features(v: dict[str, Any], creator_median: float | None, snap: date) -> dict[str, float | None]:
    views = v.get("view_count")
    if views is None:
        return {"f1": None, "f2": None, "f3": None, "f4": None, "age": None}
    age = _age_days(v.get("published_at"), snap)
    likes, comments = v.get("like_count"), v.get("comment_count")
    return {
        "f1": math.log1p(views / max(age, 1)),
        "f2": None if likes is None else (likes + 4 * (comments or 0)) / max(views, 1),
        "f3": None if not creator_median else math.log1p(views / max(creator_median, 1)),
        "f4": v.get("intent_rate"),
        "age": age,
    }


def score_videos(videos: list[dict[str, Any]], snap: date) -> list[dict[str, Any]]:
    """videos: video_id, channel_id, is_short, duration_sec, published_at, view_count, like_count, comment_count."""
    by_ch: dict[str, list[float]] = defaultdict(list)
    for v in videos:
        if v.get("view_count") is not None and _age_days(v.get("published_at"), snap) > 7:
            by_ch[v["channel_id"]].append(float(v["view_count"]))
    med = {c: median(xs) for c, xs in by_ch.items() if xs}

    feats = {v["video_id"]: features(v, med.get(v["channel_id"]), snap) for v in videos}
    cohorts: dict[str, list[str]] = defaultdict(list)
    for v in videos:
        cohorts[cohort_of(bool(v.get("is_short")), v.get("duration_sec"))].append(v["video_id"])

    out: list[dict[str, Any]] = []
    for coh, ids in cohorts.items():
        bounds = {}
        for f in WEIGHTS:
            vals = [x for i in ids if (x := feats[i][f]) is not None]
            bounds[f] = (percentile(vals, 0.10), percentile(vals, 0.90)) if vals else None
        size_q = min(1.0, len(ids) / MIN_COHORT)
        for i in ids:
            fv = feats[i]
            num = wav = 0.0
            for f, w in WEIGHTS.items():
                x, b = fv[f], bounds[f]
                if x is None or b is None:
                    continue
                lo, hi = b
                n = 0.5 if hi <= lo else min(1.0, max(0.0, (x - lo) / (hi - lo)))
                num += w * n
                wav += w
            age = fv["age"]
            quality = size_q * (0.5 if age is not None and age < 3 else 1.0)
            out.append({"video_id": i, "opi": round(100 * num / wav, 3) if wav else None,
                        "opi_confidence": round(wav * quality, 3), "f1": fv["f1"], "f2": fv["f2"], "f3": fv["f3"],
                        "f4": fv["f4"], "cohort": coh})
    return out
