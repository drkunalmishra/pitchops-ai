"""Persona Database by aggregation of per-video labels (D5) — pure, no I/O, no LLM.

Evidence: deep-analysed video = weight 1.0; Tier-2-only video = weight 0.3 ("text-only evidence").
Layers:
  seller    = sales_framework (primary + secondary)
  buyer     = buyer_persona x buyer_motive (triggers / origin personas kept as attributes)
  format    = archetype x presenter (on_camera | off_camera | unknown) x short | long
Links = seller(primary) x buyer x format per video.
Ratings: medians / P75 per entity; confidence = min(1, log10(1+evidence)/2) * min(1, channels/5) (CLAUDE.md §7);
A-E band by percentile of 0.5*pct(OPI median) + 0.5*pct(trending median) among entities with confidence >= 0.4
(CES is not computed in this build; trending replaces it — ADR-006).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median
from typing import Any

DEEP_W, TEXT_W = 1.0, 0.3
MIN_CONFIDENCE = 0.4
BANDS = "ABCDE"


def video_labels(v: dict[str, Any]) -> dict[str, Any]:
    """Pick deep labels when a deep analysis exists, else Tier-2 guesses."""
    deep = bool(v.get("deep"))
    pre = "" if deep else "g_"
    fw = list(v.get(f"{pre}frameworks") or [])
    personas = list(v.get(f"{pre}personas") or [])
    motive = v.get(f"{pre}motive") or "unclear"
    archetype = v.get(f"{pre}archetype") or "other"
    presenter = ("on_camera" if v.get("presenter") else "off_camera") if deep and v.get("presenter") is not None \
        else "unknown"
    length = "short" if v.get("is_short_candidate") else "long"
    return {
        "weight": DEEP_W if deep else TEXT_W, "deep": deep,
        "seller": fw[:2],
        "buyer": [f"{p}|{motive}" for p in personas],
        "format": f"{archetype}|{presenter}|{length}",
        "triggers": list(v.get(f"{pre}triggers") or []),
        "origins": [o for o in (v.get(f"{pre}origins") or []) if o != "unspecified"],
    }


def pct(xs: list[Any], p: float) -> float | None:
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def confidence(evidence: float, channels: int) -> float:
    return round(min(1.0, math.log10(1 + evidence) / 2) * min(1.0, channels / 5), 4)


class Bucket:
    def __init__(self) -> None:
        self.videos: list[dict[str, Any]] = []
        self.weight = 0.0

    def add(self, v: dict[str, Any], w: float) -> None:
        self.videos.append(v)
        self.weight += w

    def stats(self) -> dict[str, Any]:
        vs = self.videos
        deep = [v for v in vs if v.get("deep")]
        chans = {v["channel_id"] for v in vs}
        comps = {v.get("company_id") for v in vs if v.get("company_id")}
        objections: Counter[str] = Counter()
        questions: list[str] = []
        for v in vs:
            objections.update(v.get("objections") or {})
            questions += list(v.get("questions") or [])
        with_comments = [v for v in vs if v.get("intent_rate") is not None]
        risky = [v for v in deep if v.get("compliance_risk")]
        return {
            "video_count": len(vs), "deep_videos": len(deep), "text_only_videos": len(vs) - len(deep),
            "weighted_evidence": round(self.weight, 2), "channel_count": len(chans), "company_count": len(comps),
            "opi_median": pct([v.get("opi") for v in vs], 0.5), "opi_p75": pct([v.get("opi") for v in vs], 0.75),
            "trending_median": pct([v.get("trending") for v in vs], 0.5),
            "trending_p75": pct([v.get("trending") for v in vs], 0.75),
            "engagement_rate_median": pct([v.get("eng_rate") for v in vs], 0.5),
            "sales_pressure_median": pct([v.get("sales_pressure") for v in deep], 0.5),
            "evidence_density_median": pct([v.get("evidence_density") for v in deep], 0.5),
            "education_to_sales_median": pct([v.get("education_to_sales") for v in deep], 0.5),
            "buyer_intent_share": round(sum(v["intent_rate"] for v in with_comments) / len(with_comments), 4)
            if with_comments else None,
            "compliance_risk_rate": round(len(risky) / len(deep), 4) if deep else None,
            "top_objections": dict(objections.most_common(5)),
            "top_questions": [q for q, _ in Counter(questions).most_common(5)],
            "confidence": confidence(self.weight, len(chans)),
            "deep_n": len(deep),
            "example_video_ids": examples(vs),
        }


def examples(vs: list[dict[str, Any]], n: int = 12) -> list[str]:
    """Deep-analysed first, then by trending; max 2 per channel for diversity."""
    per: Counter[str] = Counter()
    out = []
    for v in sorted(vs, key=lambda v: (not v.get("deep"), -(v.get("trending") or -99))):
        if per[v["channel_id"]] >= 2:
            continue
        per[v["channel_id"]] += 1
        out.append(v["video_id"])
        if len(out) >= n:
            break
    return out


def aggregate(videos: list[dict[str, Any]]) -> dict[str, Any]:
    personas: dict[str, Bucket] = defaultdict(Bucket)
    links: dict[tuple[str, str, str], Bucket] = defaultdict(Bucket)
    attrs: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: {"triggers": Counter(), "origins": Counter()})
    tags: list[dict[str, Any]] = []
    for v in videos:
        lab = video_labels(v)
        w = lab["weight"]
        src = "deep" if lab["deep"] else "tier2"
        ids = []
        for i, f in enumerate(lab["seller"]):
            pid = f"seller:{f}"
            personas[pid].add(v, w)
            ids.append(pid)
            tags.append({"video_id": v["video_id"], "layer": "seller", "tag_code": f,
                         "weight": w * (1.0 if i == 0 else 0.5), "source_tier": src})
        for b in lab["buyer"]:
            pid = f"buyer:{b}"
            personas[pid].add(v, w)
            attrs[pid]["triggers"].update(lab["triggers"])
            attrs[pid]["origins"].update(lab["origins"])
            tags.append({"video_id": v["video_id"], "layer": "buyer", "tag_code": b, "weight": w, "source_tier": src})
        fid = f"format:{lab['format']}"
        personas[fid].add(v, w)
        tags.append({"video_id": v["video_id"], "layer": "format", "tag_code": lab["format"], "weight": w,
                     "source_tier": src})
        if lab["seller"]:
            for b in lab["buyer"]:
                links[(f"seller:{lab['seller'][0]}", f"buyer:{b}", fid)].add(v, w)
        _ = ids
    p_rows = []
    for pid, b in personas.items():
        layer, code = pid.split(":", 1)
        st = b.stats()
        a = attrs.get(pid, {"triggers": Counter(), "origins": Counter()})
        p_rows.append({"persona_id": pid, "layer": layer, "code": code, **st,
                       "attributes": {"top_triggers": dict(a["triggers"].most_common(5)),
                                      "top_origins": dict(a["origins"].most_common(5))}})
    l_rows = [{"link_id": "~".join(k), "seller_persona_id": k[0], "buyer_persona_id": k[1],
               "presenter_persona_id": k[2], **b.stats()} for k, b in links.items()]
    band(p_rows, by="layer")
    band(l_rows, by=None)
    return {"personas": p_rows, "links": l_rows, "tags": tags}


def band(rows: list[dict[str, Any]], by: str | None) -> None:
    """Assign rating_band A-E (quintiles of the combined percentile score) within each group."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[r[by] if by else "_"].append(r)
    for rs in groups.values():
        ok = [r for r in rs if r["confidence"] >= MIN_CONFIDENCE and r["opi_median"] is not None
              and r["trending_median"] is not None]
        for r in rs:
            r["score"], r["rating_band"] = None, "insufficient_evidence"
        if not ok:
            continue
        o = sorted(r["opi_median"] for r in ok)
        t = sorted(r["trending_median"] for r in ok)
        for r in ok:
            po = _rank(o, r["opi_median"])
            pt = _rank(t, r["trending_median"])
            r["score"] = round(0.5 * po + 0.5 * pt, 4)
        for r in ok:
            better = sum(1 for x in ok if x["score"] > r["score"])
            r["rating_band"] = BANDS[min(4, int(5 * better / len(ok)))]


def _rank(sorted_vals: list[float], x: float) -> float:
    if len(sorted_vals) == 1:
        return 0.5
    lo = sum(1 for v in sorted_vals if v < x)
    eq = sum(1 for v in sorted_vals if v == x)
    return (lo + (eq - 1) / 2) / (len(sorted_vals) - 1)


def humanize(pid: str) -> str:
    """Deterministic display name until Gemini naming (A5) runs."""
    layer, code = pid.split(":", 1)
    parts = code.split("|")
    if layer == "seller":
        return parts[0].replace("_", " ").title() + " seller"
    if layer == "buyer":
        return f"{parts[0].replace('_', ' ').title()} ({parts[1]})"
    arche, pres, length = parts
    pres_txt = {"on_camera": "presenter on camera", "off_camera": "no presenter", "unknown": "presenter n/a"}[pres]
    return f"{arche.replace('_', ' ').title()} · {pres_txt} · {length}"


__all__ = ["aggregate", "confidence", "humanize", "median", "video_labels"]
