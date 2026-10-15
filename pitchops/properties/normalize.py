"""Property-mention canonicalisation and ranking (pure; P4 Part B).

- canonical key: lowercase, drop "by <developer>", leading "the", trailing "dubai/uae", unify residence(s), & -> and
- developer key: developer name minus corporate words ("DAMAC Properties" -> "damac")
- fuzzy merge (rapidfuzz token_sort_ratio >= 88) only when developer keys are compatible AND numeric tokens match
  (so "DAMAC Islands" never merges with "DAMAC Islands 2"); config/property_aliases.csv overrides everything
- kind: 'community' for master communities / landmarks (not a sellable project), else 'project'
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from rapidfuzz import fuzz, process

MERGE_MIN = 88
UAE_EMIRATES = {"dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "umm al quwain", "fujairah", "uae",
                "دبي", "أبوظبي", "الشارقة", "عجمان", "رأس الخيمة"}
DEV_DROP = {"properties", "property", "developments", "development", "developers", "developer", "realty",
            "real", "estate", "group", "llc", "holding", "holdings", "pjsc", "company", "co", "the", "by", "uae", "dubai"}
COMMUNITIES = {
    "palm jumeirah", "dubai marina", "downtown dubai", "downtown", "business bay", "jvc", "jumeirah village circle",
    "jvt", "jumeirah village triangle", "jlt", "jumeirah lake towers", "dubai hills estate", "dubai hills",
    "creek harbour", "dubai creek harbour", "expo city", "expo city dubai", "springs", "meadows", "lakes",
    "town square", "arabian ranches", "arabian ranches 2", "arabian ranches 3", "dubai islands", "dubai south",
    "mbr city", "mohammed bin rashid city", "jumeirah golf estates", "damac hills", "damac hills 2", "emaar beachfront",
    "bluewaters", "bluewaters island", "la mer", "city walk", "al barsha", "dubailand", "dubai land", "sports city",
    "dubai sports city", "motor city", "international city", "burj khalifa", "yas island", "saadiyat island",
    "al reem island", "reem island", "al marjan island", "deira islands", "jumeirah", "meydan", "dubai harbour",
    "jumeirah beach residence", "jbr", "al furjan", "dubai investment park", "dip", "arjan", "majan", "al jaddaf",
    "sobha hartland", "mudon", "tilal al ghaf", "the valley", "valley", "dubai creek", "palm jebel ali",
    "dubai maritime city", "al habtoor city", "silicon oasis", "dubai silicon oasis", "jumeirah park", "emirates hills",
    "wynn al marjan island", "wynn al marjan", "louvre abu dhabi", "emerald hills", "aljada", "al barari",
}


def _clean(s: str) -> str:
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def canonical_key(name: str | None) -> str | None:
    if not name:
        return None
    s = _clean(name)
    s = re.sub(r"\s+by\s+.*$", "", s)
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\s+(in\s+)?(dubai|uae|abu dhabi)$", "", s)
    s = re.sub(r"\bresidence\b", "residences", s)
    s = " ".join(s.split())
    if not s or s in {"dubai", "uae", "villa", "villas", "apartment", "apartments", "off plan", "project", "tower"}:
        return None
    return s


def developer_key(dev: str | None) -> str | None:
    if not dev:
        return None
    toks = [t for t in _clean(dev).split() if t not in DEV_DROP]
    return " ".join(toks[:2]) or None


def is_uae(emirate: str | None) -> bool:
    return emirate is None or _clean(emirate) in UAE_EMIRATES or emirate.strip() in UAE_EMIRATES


def _digits(s: str) -> frozenset[str]:
    return frozenset(re.findall(r"\d+", s))


@dataclass
class Canonical:
    key: str
    display: Counter[str] = field(default_factory=Counter)
    devs: Counter[str] = field(default_factory=Counter)
    dev_display: Counter[str] = field(default_factory=Counter)
    areas: Counter[str] = field(default_factory=Counter)
    emirates: Counter[str] = field(default_factory=Counter)
    aliases: set[str] = field(default_factory=set)


def build_canonicals(mentions: list[dict[str, Any]], overrides: dict[str, str] | None = None
                     ) -> tuple[dict[str, Canonical], dict[str, str]]:
    """Returns (canonicals by key, raw_key -> canonical key). mentions: project_name, developer, area, emirate."""
    overrides = {canonical_key(k) or k: canonical_key(v) or v for k, v in (overrides or {}).items()}
    freq: Counter[str] = Counter()
    dev_of: dict[str, Counter[str]] = defaultdict(Counter)
    for m in mentions:
        k = canonical_key(m.get("project_name"))
        if k and is_uae(m.get("emirate")):
            freq[k] += 1
            d = developer_key(m.get("developer"))
            if d:
                dev_of[k][d] += 1
    canon: dict[str, Canonical] = {}
    canon_dev: dict[str, str | None] = {}
    mapping: dict[str, str] = {}
    keys: list[str] = []
    for k, _ in freq.most_common():
        target = overrides.get(k)
        if not target:
            dev = dev_of[k].most_common(1)[0][0] if dev_of[k] else None
            hit = process.extractOne(k, keys, scorer=fuzz.token_sort_ratio, score_cutoff=MERGE_MIN) if keys else None
            if hit:
                cand = hit[0]
                cdev = canon_dev.get(cand)
                if _digits(cand) == _digits(k) and (dev is None or cdev is None or dev == cdev):
                    target = cand
        target = target or k
        if target not in canon:
            canon[target] = Canonical(target)
            canon_dev[target] = dev_of[k].most_common(1)[0][0] if dev_of[k] else None
            keys.append(target)
        mapping[k] = target
    for m in mentions:
        k = canonical_key(m.get("project_name"))
        if not k or k not in mapping:
            continue
        c = canon[mapping[k]]
        c.display[m["project_name"].strip()] += 1
        c.aliases.add(k)
        if m.get("developer"):
            c.dev_display[m["developer"].strip()] += 1
            dk = developer_key(m["developer"])
            if dk:
                c.devs[dk] += 1
        if m.get("area"):
            c.areas[m["area"].strip()] += 1
        if m.get("emirate"):
            c.emirates[m["emirate"].strip()] += 1
    return canon, mapping


def kind_of(c: Canonical) -> str:
    area = canonical_key(c.areas.most_common(1)[0][0]) if c.areas else None
    return "community" if c.key in COMMUNITIES or (area is not None and area == c.key) else "project"


def rank_properties(canon: dict[str, Canonical], mapping: dict[str, str], mentions: list[dict[str, Any]],
                    videos: dict[str, dict[str, Any]], now: datetime, min_videos: int = 3) -> list[dict[str, Any]]:
    """videos: video_id -> {channel_id, company_id, views, published_at, deep, sales_pressure, personas[], frameworks[]}."""
    by: dict[str, dict[str, Any]] = defaultdict(lambda: {"videos": set(), "prices": Counter(), "types": Counter()})
    for m in mentions:
        k = canonical_key(m.get("project_name"))
        if not k or k not in mapping or m["video_id"] not in videos:
            continue
        b = by[mapping[k]]
        b["videos"].add(m["video_id"])
        if m.get("price_text"):
            b["prices"][m["price_text"].strip()] += 1
        if m.get("property_type"):
            b["types"][m["property_type"]] += 1
    recent_cut = now - timedelta(days=183)
    rows: list[dict[str, Any]] = []
    for key, b in by.items():
        vids = [videos[v] | {"video_id": v} for v in b["videos"]]
        if len(vids) < min_videos:
            continue
        recent = [v for v in vids if v["published_at"] and v["published_at"] >= recent_cut]
        deep = [v for v in vids if v.get("deep") and v.get("sales_pressure") is not None]
        personas: Counter[str] = Counter()
        frameworks: Counter[str] = Counter()
        for v in vids:
            personas.update(v.get("personas") or [])
            frameworks.update(v.get("frameworks") or [])
        c = canon[key]
        rows.append({
            "property_id": "prop_" + re.sub(r"\W+", "_", key),
            "canonical_name": c.display.most_common(1)[0][0], "kind": kind_of(c),
            "developer": c.dev_display.most_common(1)[0][0] if c.dev_display else None,
            "area": c.areas.most_common(1)[0][0] if c.areas else None,
            "emirate": c.emirates.most_common(1)[0][0] if c.emirates else None,
            "aliases": sorted(c.aliases)[:20], "property_types": [t for t, _ in b["types"].most_common(3)],
            "videos": len(vids), "weighted_videos": round(len(vids) + 0.5 * len(recent), 2),
            "recent_videos": len(recent), "companies": len({v["company_id"] for v in vids if v.get("company_id")}),
            "channels": len({v["channel_id"] for v in vids}), "total_views": int(sum(v.get("views") or 0 for v in vids)),
            "avg_sales_pressure": round(sum(v["sales_pressure"] for v in deep) / len(deep), 2) if deep else None,
            "top_buyer_personas": [p for p, _ in personas.most_common(3)],
            "top_frameworks": [f for f, _ in frameworks.most_common(3)],
            "price_texts": [p for p, _ in b["prices"].most_common(5)],
            "example_video_ids": [v["video_id"] for v in sorted(vids, key=lambda v: -(v.get("views") or 0))[:8]],
        })
    _score(rows)
    rows.sort(key=lambda r: -float(r["score"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def _pct(vals: list[float]) -> dict[float, float]:
    s = sorted(vals)
    n = len(s)
    return {v: (sum(1 for x in s if x < v) + (sum(1 for x in s if x == v) - 1) / 2) / max(n - 1, 1) for v in set(s)}


def _score(rows: list[dict[str, Any]]) -> None:
    """score = 0.4·pct(weighted_videos) + 0.3·pct(companies) + 0.3·pct(log10 views)."""
    if not rows:
        return
    pw = _pct([r["weighted_videos"] for r in rows])
    pc = _pct([float(r["companies"]) for r in rows])
    pv = _pct([math.log10(1 + r["total_views"]) for r in rows])
    for r in rows:
        r["score"] = round(0.4 * pw[r["weighted_videos"]] + 0.3 * pc[float(r["companies"])]
                           + 0.3 * pv[math.log10(1 + r["total_views"])], 4)


def select_media(rows: list[dict[str, Any]], n: int = 40, overrides: dict[str, str] | None = None) -> None:
    """Top-n distinct *projects* (>= 2 companies), alternating 16:9 walkthrough / 9:16 short by rank (D18).
    overrides: property_id -> 'walkthrough' | 'short' | 'exclude'."""
    overrides = overrides or {}
    for r in rows:
        r["media_candidate"] = None
    picked = 0
    for r in rows:
        o = overrides.get(r["property_id"])
        if o == "exclude":
            continue
        if o in ("walkthrough", "short"):
            r["media_candidate"] = o
            continue
        if picked >= n - sum(1 for v in overrides.values() if v in ("walkthrough", "short")):
            continue
        if r["kind"] == "project" and r["companies"] >= 2:
            r["media_candidate"] = "walkthrough" if picked % 2 == 0 else "short"
            picked += 1
