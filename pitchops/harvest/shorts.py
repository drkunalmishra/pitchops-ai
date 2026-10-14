"""Shorts classification (pure). The YouTube Data API has no Shorts flag, so we use a documented rule:
is_short = duration <= 180 s AND (duration <= 60 s OR '#shorts' in title / description / tags)."""

from __future__ import annotations

import re

_DUR = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def iso_duration_sec(d: str | None) -> int | None:
    if not d:
        return None
    m = _DUR.fullmatch(d)
    if not m:
        return None
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def classify(duration_sec: int | None, title: str | None, description: str | None,
             tags: list[str] | None) -> tuple[bool, str]:
    if duration_sec is None or duration_sec <= 0:
        return False, "unknown_duration"
    if duration_sec <= 60:
        return True, "le60"
    if duration_sec <= 180:
        text = " ".join([title or "", description or "", " ".join(f"#{t}" for t in (tags or []))]).lower()
        if "#shorts" in text or "#short " in text + " ":
            return True, "le180_hashtag"
        return False, "le180_no_hashtag"
    return False, "gt180"
