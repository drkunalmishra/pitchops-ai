"""P5 read API for the Intelligence Explorer. Read-only, relevant data only (v_videos_relevant / v_channels_relevant),
every BigQuery query capped at 1 GB billed, results cached in memory (the corpus is frozen; jobs refresh it rarely).

Admin/QA endpoints require an admin: Firebase custom claim `admin` or an email listed in ADMIN_EMAILS.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from pitchops.config import get_settings

MAX_BYTES = 1 << 30
TTL_S = 600
_cache: dict[str, tuple[float, Any]] = {}

router = APIRouter()


def t(name: str) -> str:
    return get_settings().table(name)


def q(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    from pitchops.bq import query

    return query(sql, params, max_bytes=MAX_BYTES)


def cached(key: str, fn: Any) -> Any:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL_S:
        return hit[1]
    val = fn()
    _cache[key] = (time.monotonic(), val)
    return val


def jsonable(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    return v


def rows(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [jsonable(r) for r in q(sql, params)]


def finops_doc() -> dict[str, Any]:
    from pitchops.fs import client as fs

    return jsonable(fs().collection("finops").document("current").get().to_dict() or {})


PV = "(SELECT MAX(persona_db_version) FROM `{personas}`)"


def pv() -> str:
    return PV.format(personas=t("personas"))


# ---- overview ------------------------------------------------------------------------------------------------------
def _overview() -> dict[str, Any]:
    f = rows(f"""SELECT
        (SELECT COUNT(*) FROM `{t('brokers')}`) brokers,
        (SELECT COUNT(*) FROM `{t('companies')}`) companies,
        (SELECT COUNT(*) FROM `{t('channels')}`) channels,
        (SELECT COUNT(*) FROM `{t('v_channels_relevant')}`) relevant_channels,
        (SELECT COUNT(*) FROM `{t('videos')}`) videos,
        (SELECT COUNT(*) FROM `{t('v_videos_relevant')}`) relevant_videos,
        (SELECT COUNT(*) FROM `{t('video_analysis')}` a JOIN `{t('v_videos_relevant')}` USING (video_id)
           WHERE a.status = 'succeeded') deep_analysed,
        (SELECT COUNT(*) FROM `{t('deep_selection')}`) deep_selected,
        (SELECT COUNT(*) FROM `{t('comments')}`) comments,
        (SELECT ROUND(AVG(d.sales_pressure_score), 2) FROM `{t('video_metrics_derived')}` d
           JOIN `{t('v_videos_relevant')}` USING (video_id)) avg_sales_pressure,
        (SELECT MAX(ingested_at) FROM `{t('video_metrics_daily')}`) last_refresh""")[0]
    top = rows(f"""SELECT p.layer, p.persona_id, p.name, p.weighted_evidence, r.rating_band
        FROM `{t('personas')}` p LEFT JOIN `{t('persona_ratings')}` r
          ON r.entity_type = 'persona' AND r.entity_id = p.persona_id AND r.persona_db_version = p.persona_db_version
        WHERE p.persona_db_version = {pv()} AND p.layer IN ('seller', 'buyer')
          AND NOT STARTS_WITH(p.persona_id, 'buyer:agent_industry')
        QUALIFY ROW_NUMBER() OVER (PARTITION BY p.layer ORDER BY p.weighted_evidence DESC) = 1""")
    prop = rows(f"""SELECT property_id, canonical_name, developer, videos FROM `{t('properties_ranked')}`
        WHERE kind = 'project' ORDER BY rank LIMIT 1""")
    fin = finops_doc()
    return {"funnel": f, "top_personas": {r["layer"]: r for r in top}, "top_property": prop[0] if prop else None,
            "finops": {k: fin.get(k) for k in ("total_usd", "project_cap_usd", "project_cap_pct",
                                                "projected_total_usd", "as_of")},
            "as_of": datetime.now(UTC).isoformat()}


@router.get("/explore/overview")
def overview() -> dict[str, Any]:
    return cached("overview", _overview)


# ---- personas ------------------------------------------------------------------------------------------------------
def _personas() -> list[dict[str, Any]]:
    ps = rows(f"""SELECT p.persona_id, p.layer, p.code, p.name, p.description, p.motive, p.member_count,
            p.example_video_ids, p.attributes, p.weighted_evidence, p.deep_videos, p.text_only_videos,
            p.channel_count, p.company_count, p.name_source,
            r.rating_band, r.confidence, r.score, r.opi_median, r.trending_median, r.sales_pressure_median,
            r.evidence_density_median, r.compliance_risk_rate, r.buyer_intent_share, r.top_objections,
            r.top_questions, r.deep_n
        FROM `{t('personas')}` p LEFT JOIN `{t('persona_ratings')}` r
          ON r.entity_type = 'persona' AND r.entity_id = p.persona_id AND r.persona_db_version = p.persona_db_version
        WHERE p.persona_db_version = {pv()} ORDER BY p.weighted_evidence DESC""")
    links = rows(f"""SELECT l.seller_persona_id s, l.buyer_persona_id b, l.presenter_persona_id f, l.video_count n,
            r.score, r.confidence
        FROM `{t('persona_links')}` l JOIN `{t('persona_ratings')}` r
          ON r.entity_type = 'link' AND r.entity_id = l.link_id AND r.persona_db_version = l.persona_db_version
        WHERE l.persona_db_version = {pv()} AND r.confidence >= 0.4 AND r.score IS NOT NULL""")
    names = {p["persona_id"]: p["name"] for p in ps}
    trend = sorted(p["trending_median"] for p in ps if p["trending_median"] is not None)
    risk = sorted(p["compliance_risk_rate"] for p in ps if p["compliance_risk_rate"] is not None)
    med_t = trend[len(trend) // 2] if trend else None
    p75_risk = risk[int(len(risk) * 0.75)] if risk else None
    for p in ps:
        key = {"seller": "s", "buyer": "b", "format": "f"}[p["layer"]]
        mine = sorted((x for x in links if x[key] == p["persona_id"]), key=lambda x: -(x["score"] or 0))[:3]
        others = [k for k in ("s", "b", "f") if k != key]
        p["works_with"] = [" × ".join(names.get(x[o], x[o]) for o in others) for x in mine]
        avoid = []
        if p_risk := p["compliance_risk_rate"]:
            if p75_risk is not None and p_risk >= p75_risk and p_risk > 0:
                avoid.append(f"Risky claims in {round(100 * p_risk)}% of deep-analysed videos")
        if (p["sales_pressure_median"] or 0) >= 6:
            avoid.append(f"High sales pressure (median {p['sales_pressure_median']}/10)")
        if med_t is not None and p["trending_median"] is not None and p["trending_median"] < med_t:
            avoid.append("Trends below the median persona")
        p["avoid"] = avoid
    return ps


@router.get("/explore/personas")
def personas() -> list[dict[str, Any]]:
    return cached("personas", _personas)


def _base(buyer_id: str) -> str:
    return buyer_id.split(":", 1)[-1].split("|", 1)[0]


def _matrix() -> dict[str, Any]:
    cells = rows(f"""SELECT l.seller_persona_id seller, SPLIT(SPLIT(l.buyer_persona_id, ':')[OFFSET(1)], '|')[OFFSET(0)]
            buyer, SUM(l.video_count) videos, SUM(l.deep_videos) deep_videos,
            SAFE_DIVIDE(SUM(r.trending_median * l.video_count), SUM(IF(r.trending_median IS NULL, 0, l.video_count)))
              trending, SAFE_DIVIDE(SUM(r.sales_pressure_median * l.deep_videos),
              SUM(IF(r.sales_pressure_median IS NULL, 0, l.deep_videos))) sales_pressure
        FROM `{t('persona_links')}` l LEFT JOIN `{t('persona_ratings')}` r
          ON r.entity_type = 'link' AND r.entity_id = l.link_id AND r.persona_db_version = l.persona_db_version
        WHERE l.persona_db_version = {pv()} AND NOT STARTS_WITH(l.buyer_persona_id, 'buyer:agent_industry')
        GROUP BY 1, 2""")
    sellers = Counter[str]()
    buyers = Counter[str]()
    for c in cells:
        sellers[c["seller"]] += c["videos"]
        buyers[c["buyer"]] += c["videos"]
        for k in ("trending", "sales_pressure"):
            c[k] = round(c[k], 3) if c[k] is not None else None
    return {"sellers": [s for s, _ in sellers.most_common()], "buyers": [b for b, _ in buyers.most_common(14)],
            "cells": cells}


@router.get("/explore/matrix")
def matrix() -> dict[str, Any]:
    return cached("matrix", _matrix)


VIDEO_COLS = """v.video_id, v.title, v.duration_sec, v.is_short, v.published_at, c.title AS channel, c.company_id,
    tr.views, tr.trending, a.video_id IS NOT NULL AS deep, a.claims, a.hook_type, a.cta_type, a.archetype,
    JSON_VALUE(a.overview, '$.hook_text') AS hook_text, JSON_VALUE(a.overview, '$.cta_text') AS cta_text,
    JSON_VALUE(a.overview, '$.summary') AS summary, d.sales_pressure_score, d.verification_status,
    s.top_questions, s.objection_topics"""


def video_joins() -> str:
    return f"""JOIN `{t('channels')}` c USING (channel_id)
        LEFT JOIN `{t('video_trending')}` tr USING (video_id)
        LEFT JOIN `{t('video_analysis')}` a ON a.video_id = v.video_id AND a.status = 'succeeded'
        LEFT JOIN `{t('video_metrics_derived')}` d ON d.video_id = v.video_id
        LEFT JOIN `{t('audience_summaries')}` s ON s.video_id = v.video_id"""


def _tally(vids: list[dict[str, Any]], key: str, n: int = 5) -> list[str]:
    cnt: Counter[str] = Counter()
    for v in vids:
        val = v.get(key)
        for x in (val if isinstance(val, list) else [val] if val else []):
            cnt[str(x.get("topic") or x.get("question") or x) if isinstance(x, dict) else str(x)] += 1
    return [k for k, _ in cnt.most_common(n)]


@router.get("/explore/matrix/cell")
def matrix_cell(seller: str = Query(...), buyer: str = Query(...)) -> dict[str, Any]:
    s_code = seller.split(":", 1)[-1]

    def run() -> dict[str, Any]:
        vids = rows(f"""WITH st AS (SELECT DISTINCT video_id FROM `{t('video_persona_tags')}`
                               WHERE layer = 'seller' AND tag_code = @s),
                 bt AS (SELECT DISTINCT video_id FROM `{t('video_persona_tags')}`
                       WHERE layer = 'buyer' AND SPLIT(tag_code, '|')[OFFSET(0)] = @b)
            SELECT {VIDEO_COLS}
            FROM st JOIN bt USING (video_id) JOIN `{t('v_videos_relevant')}` v USING (video_id) {video_joins()}
            ORDER BY deep DESC, tr.trending DESC LIMIT 12""", {"s": s_code, "b": buyer})
        return {"seller": seller, "buyer": buyer, "videos": vids,
                "hooks": _tally(vids, "hook_type"), "ctas": _tally(vids, "cta_type"),
                "questions": _tally(vids, "top_questions"), "objections": _tally(vids, "objection_topics")}

    return cached(f"cell:{s_code}:{buyer}", run)


# ---- properties ----------------------------------------------------------------------------------------------------
@router.get("/explore/properties")
def properties(limit: int = Query(60, le=200)) -> list[dict[str, Any]]:
    return cached(f"props:{limit}", lambda: rows(f"""SELECT * EXCEPT (ingested_at, run_id)
        FROM `{t('properties_ranked')}` ORDER BY rank LIMIT @n""", {"n": limit}))


@router.get("/explore/properties/{property_id}")
def property_detail(property_id: str) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        r = rows(f"SELECT * EXCEPT (ingested_at, run_id) FROM `{t('properties_ranked')}` WHERE property_id = @p",
                 {"p": property_id})
        if not r:
            raise HTTPException(404, "property not found")
        p = r[0]
        vids = rows(f"""SELECT {VIDEO_COLS} FROM `{t('v_videos_relevant')}` v {video_joins()}
            WHERE v.video_id IN UNNEST(@ids) ORDER BY deep DESC, tr.views DESC""", {"ids": p["example_video_ids"] or []})
        return {"property": p, "videos": vids}

    return cached(f"prop:{property_id}", run)


# ---- companies -----------------------------------------------------------------------------------------------------
def _companies() -> list[dict[str, Any]]:
    base = rows(f"""WITH vids AS (
            SELECT ch.company_id, v.video_id, v.is_short FROM `{t('v_videos_relevant')}` v
            JOIN `{t('v_channels_relevant')}` ch USING (channel_id) WHERE ch.company_id IS NOT NULL)
        SELECT vids.company_id, ANY_VALUE(c.office_names_en) name, ANY_VALUE(c.broker_count) brokers,
            COUNT(*) videos, COUNTIF(vids.is_short) shorts, SUM(tr.views) views,
            COUNTIF(a.video_id IS NOT NULL) deep, ROUND(AVG(d.sales_pressure_score), 2) sales_pressure,
            ANY_VALUE(sl.rank) shortlist_rank
        FROM vids JOIN `{t('companies')}` c USING (company_id)
        LEFT JOIN `{t('video_trending')}` tr USING (video_id)
        LEFT JOIN `{t('video_analysis')}` a ON a.video_id = vids.video_id AND a.status = 'succeeded'
        LEFT JOIN `{t('video_metrics_derived')}` d ON d.video_id = vids.video_id
        LEFT JOIN `{t('company_shortlist')}` sl ON sl.company_id = vids.company_id
        GROUP BY 1 ORDER BY views DESC""")
    tops = rows(f"""SELECT ch.company_id, g.tag_code, SUM(g.weight) w
        FROM `{t('video_persona_tags')}` g JOIN `{t('v_videos_relevant')}` v USING (video_id)
        JOIN `{t('v_channels_relevant')}` ch USING (channel_id)
        WHERE g.layer = 'buyer' AND ch.company_id IS NOT NULL AND NOT STARTS_WITH(g.tag_code, 'agent_industry')
        GROUP BY 1, 2 QUALIFY ROW_NUMBER() OVER (PARTITION BY ch.company_id ORDER BY w DESC) = 1""")
    top = {r["company_id"]: r["tag_code"].split("|")[0] for r in tops}
    for c in base:
        c["top_buyer"] = top.get(c["company_id"])
        c["report_type"] = "full" if c["shortlist_rank"] and c["deep"] else "light"
    return base


@router.get("/explore/companies")
def companies() -> list[dict[str, Any]]:
    return cached("companies", _companies)


def _mix(company_id: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows(f"""SELECT g.layer, SPLIT(g.tag_code, '|')[OFFSET(0)] code, ROUND(SUM(g.weight), 1) w,
            COUNT(DISTINCT g.video_id) n
        FROM `{t('video_persona_tags')}` g JOIN `{t('v_videos_relevant')}` v USING (video_id)
        JOIN `{t('v_channels_relevant')}` ch USING (channel_id)
        WHERE ch.company_id = @c GROUP BY 1, 2
        QUALIFY ROW_NUMBER() OVER (PARTITION BY g.layer ORDER BY w DESC) <= 6
        ORDER BY layer, w DESC""", {"c": company_id}):
        out.setdefault(r["layer"], []).append(r)
    return out


def gaps(company: dict[str, Any], corpus: dict[str, Any], deep: list[dict[str, Any]]) -> list[str]:
    """Rule-based gaps vs the corpus (pure, deterministic)."""
    g: list[str] = []
    if not company["deep"]:
        g.append("No deep-analysed videos yet — insights are from text tags only (light report).")
    sp, csp = company["sales_pressure"], corpus["sales_pressure"]
    if sp and csp and sp > 1.25 * csp:
        g.append(f"Sales pressure {company['sales_pressure']}/10 vs corpus {corpus['sales_pressure']}/10 — "
                 "more education-led content would balance it.")
    if deep:
        sourced = sum(1 for v in deep if v.get("verification_status") == "sourced")
        risky = sum(1 for v in deep if v.get("verification_status") == "unverified_claims")
        if sourced / len(deep) < 0.1:
            g.append("Almost no claims cite a visible source (DLD, RERA, developer documents).")
        if risky:
            g.append(f"{risky} deep-analysed video(s) carry risky, unsourced claims (e.g. guaranteed returns).")
    if company["videos"] and not company["shorts"]:
        g.append("No Shorts — Shorts drive most reach in this corpus.")
    elif company["videos"] and company["shorts"] / company["videos"] > 0.9:
        g.append("Almost only Shorts — few long-form explainers or tours that build trust.")
    return g


@router.get("/explore/companies/{company_id}")
def company_detail(company_id: str) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        c = next((x for x in companies() if x["company_id"] == company_id), None)
        if not c:
            raise HTTPException(404, "company not found or not relevant")
        chans = rows(f"""SELECT channel_id, title, handle, subscriber_count, relevant_video_count
            FROM `{t('v_channels_relevant')}` WHERE company_id = @c ORDER BY subscriber_count DESC""", {"c": company_id})
        vids = rows(f"""SELECT {VIDEO_COLS} FROM `{t('v_videos_relevant')}` v {video_joins()}
            WHERE c.company_id = @c ORDER BY deep DESC, tr.trending DESC LIMIT 15""", {"c": company_id})
        all_c = companies()
        pressures = [x["sales_pressure"] for x in all_c if x["sales_pressure"] is not None]
        corpus = {"sales_pressure": round(sum(pressures) / len(pressures), 2) if pressures else None}
        deep = [v for v in vids if v["deep"]]
        return {"company": c, "channels": chans, "videos": vids, "mix": _mix(company_id),
                "gaps": gaps(c, corpus, deep), "corpus": corpus}

    return cached(f"company:{company_id}", run)


# ---- video ---------------------------------------------------------------------------------------------------------
@router.get("/explore/videos/{video_id}")
def video_detail(video_id: str) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        r = rows(f"""SELECT v.video_id, v.title, v.duration_sec, v.is_short, v.published_at, v.is_relevant,
                v.relevance_reason, v.relevance_source, c.title channel, c.channel_id, c.company_id,
                co.office_names_en company, tr.views, tr.trending, tr.eng_rate, sc.opi,
                a.status, a.model_id, a.coverage, a.clips, a.overview, a.segments, a.claims, a.property_mentions,
                d.* EXCEPT (video_id, prompt_version, ingested_at, run_id),
                s.data_status audience_status, s.comments_collected, s.sentiment_mix, s.intent_mix, s.intent_rate,
                s.top_questions, s.objection_topics
            FROM `{t('videos')}` v JOIN `{t('channels')}` c USING (channel_id)
            LEFT JOIN `{t('companies')}` co ON co.company_id = c.company_id
            LEFT JOIN `{t('video_trending')}` tr ON tr.video_id = v.video_id
            LEFT JOIN `{t('video_scores')}` sc ON sc.video_id = v.video_id
            LEFT JOIN `{t('video_analysis')}` a ON a.video_id = v.video_id AND a.status = 'succeeded'
            LEFT JOIN `{t('video_metrics_derived')}` d ON d.video_id = v.video_id
            LEFT JOIN `{t('audience_summaries')}` s ON s.video_id = v.video_id
            WHERE v.video_id = @v LIMIT 1""", {"v": video_id})
        if not r:
            raise HTTPException(404, "video not found")
        return r[0]

    return cached(f"video:{video_id}", run)


# ---- finops --------------------------------------------------------------------------------------------------------
@router.get("/finops")
def finops() -> dict[str, Any]:
    return cached("finops", finops_doc)


# ---- admin / QA ----------------------------------------------------------------------------------------------------
def is_admin(user: dict[str, Any]) -> bool:
    allowed = {e.strip().lower() for e in re.split(r"[,;]", get_settings().admin_emails) if e.strip()}
    return bool(user.get("admin")) or (user.get("email") or "").lower() in allowed


def require_admin(user: dict[str, Any]) -> None:
    if not is_admin(user):
        raise HTTPException(403, "admin only")


def admin_router(require_user: Any) -> APIRouter:
    r = APIRouter()

    @r.get("/me")
    def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return {"admin": is_admin(user)}

    @r.get("/admin/qa")
    def qa(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        require_admin(user)
        return {
            "videos": rows(f"""SELECT * FROM `{t('v_videos_irrelevant_qa')}`
                ORDER BY relevance_source, video_id LIMIT 300"""),
            "channels": rows(f"""SELECT channel_id, title, irrelevant_share, relevant_video_count, relevance_reason
                FROM `{t('channels')}` WHERE is_relevant = FALSE ORDER BY irrelevant_share DESC LIMIT 200"""),
            "needs_review": rows(f"""SELECT video_id, model_id, error, ingested_at FROM `{t('video_analysis')}`
                WHERE status = 'needs_review' ORDER BY ingested_at DESC LIMIT 200"""),
        }

    class Relevance(BaseModel):
        is_relevant: bool

    @r.post("/admin/relevance/{video_id}")
    def set_relevance(video_id: str, body: Relevance, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        require_admin(user)
        from google.cloud import bigquery

        from pitchops.bq import client
        from pitchops.fs import client as fs

        job = client().query(
            f"""UPDATE `{t('videos')}` SET is_relevant = @r, relevance_source = 'manual',
                relevance_reason = @why WHERE video_id = @v""",
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("r", "BOOL", body.is_relevant),
                bigquery.ScalarQueryParameter("why", "STRING", "manual override (admin QA)"),
                bigquery.ScalarQueryParameter("v", "STRING", video_id)]))
        job.result()
        if not job.num_dml_affected_rows:
            raise HTTPException(404, "video not found")
        now = datetime.now(UTC).isoformat()
        fs().collection("audit").add({"action": "relevance_override", "video_id": video_id,
                                      "is_relevant": body.is_relevant, "uid": user.get("uid"), "at": now})
        _cache.clear()
        return {"video_id": video_id, "is_relevant": body.is_relevant, "relevance_source": "manual"}

    return r
