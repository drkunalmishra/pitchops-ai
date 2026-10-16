"""PitchOps API (Cloud Run). /v1/* requires a Firebase ID token.

Routes are served both at /v1/... and /api/v1/... because Firebase Hosting forwards the full /api/** path.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import firebase_admin
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth as fb_auth
from pydantic import BaseModel

from pitchops.config import get_settings
from pitchops.youtube.quota import day_pt

settings = get_settings()
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={"projectId": settings.gcp_project_id})

app = FastAPI(title="PitchOps API", version="0.1.0")
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return dict(fb_auth.verify_id_token(authorization.split(" ", 1)[1]))
    except Exception as e:
        raise HTTPException(status_code=401, detail="invalid token") from e


@app.get("/healthz")
@app.get("/api/healthz")  # *.run.app reserves /healthz at the Google frontend; Hosting uses /api/*
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
@app.get("/api/readyz")
def readyz() -> dict[str, Any]:
    from pitchops.bq import query
    from pitchops.fs import client as fs

    checks: dict[str, str] = {}
    try:
        query("SELECT 1 AS x")
        checks["bigquery"] = "ok"
    except Exception as e:
        checks["bigquery"] = f"error: {type(e).__name__}"
    try:
        list(fs().collection("_health").limit(1).stream())
        checks["firestore"] = "ok"
    except Exception as e:
        checks["firestore"] = f"error: {type(e).__name__}"
    if any(v != "ok" for v in checks.values()):
        raise HTTPException(status_code=503, detail=checks)
    return {"status": "ready", **checks}


_cache: dict[str, Any] = {"at": 0.0, "data": None}
STATS_TTL_S = 60


def corpus_stats() -> dict[str, Any]:
    from pitchops.bq import query

    if _cache["data"] and time.monotonic() - _cache["at"] < STATS_TTL_S:
        return dict(_cache["data"])
    t = settings.table
    row = query(
        f"""SELECT
          (SELECT COUNT(*) FROM `{t('brokers')}`) AS brokers,
          (SELECT COUNT(*) FROM `{t('companies')}`) AS companies,
          (SELECT COUNT(*) FROM `{t('channels')}`) AS channels,
          (SELECT COUNT(*) FROM `{t('channel_candidates')}`) AS candidates,
          (SELECT COUNTIF(decision = 'review') FROM `{t('channel_matches')}`) AS review_queue,
          (SELECT COUNT(*) FROM `{t('videos')}`) AS videos,
          (SELECT COUNTIF(is_short) FROM `{t('videos')}`) AS shorts,
          (SELECT COUNTIF(NOT is_short) FROM `{t('videos')}`) AS long_form,
          (SELECT COALESCE(SUM(units),0) FROM `{t('quota_ledger')}` WHERE day_pt = @d) AS quota_units_today,
          (SELECT COALESCE(SUM(cost_usd_est),0) FROM `{t('llm_calls')}`) AS gemini_spend_usd_est,
          (SELECT COUNT(*) FROM `{t('llm_calls')}`) AS gemini_calls""",
        {"d": day_pt().isoformat()},
    )[0]
    row["channels_by_match_type"] = query(
        f"SELECT IFNULL(match_type,'?') AS k, COUNT(*) AS n FROM `{t('channels')}` GROUP BY 1 ORDER BY 2 DESC")
    row["channels_by_route"] = query(
        f"""SELECT r AS k, COUNT(DISTINCT c.channel_id) AS n FROM `{t('channels')}` c
            JOIN `{t('channel_candidates')}` cc USING (channel_id), UNNEST([cc.source_route]) r
            GROUP BY 1 ORDER BY 2 DESC""")
    data = {**row, "gemini_spend_usd_est": round(float(row["gemini_spend_usd_est"]), 4),
            "quota_cap": settings.yt_daily_unit_cap, "gemini_budget_usd": settings.gemini_budget_usd,
            "as_of": datetime.now(UTC).isoformat()}
    _cache.update(at=time.monotonic(), data=data)
    return data


v1 = APIRouter(dependencies=[Depends(require_user)])


@v1.get("/corpus/stats")
def get_corpus_stats() -> dict[str, Any]:
    return corpus_stats()




# ---- review queue -------------------------------------------------------------------------------
class ReviewDecision(BaseModel):
    decision: str
    company_id: str | None = None
    broker_number: str | None = None


@v1.get("/review/channels")
def review_channels(decision: str = Query("review"), limit: int = Query(200, le=500)) -> dict[str, Any]:
    import json

    from pitchops.bq import query
    from pitchops.fs import client as fs

    t = settings.table
    rows = query(
        f"""SELECT m.channel_id, m.company_id, m.broker_number, m.match_type, m.match_score,
                   TO_JSON_STRING(m.signals) AS signals, c.office_names_en AS company_name, b.name_en AS broker_name
            FROM `{t('channel_matches')}` m
            LEFT JOIN `{t('companies')}` c USING (company_id)
            LEFT JOIN `{t('brokers')}` b ON b.broker_number = m.broker_number
            WHERE m.decision = @decision ORDER BY m.match_score DESC LIMIT @lim""",
        {"decision": decision, "lim": limit})
    decided = {d.id for d in fs().collection("review_decisions").select([]).stream()}
    items = []
    for r in rows:
        if r["channel_id"] in decided:
            continue
        sig = json.loads(r.pop("signals") or "{}")
        r["title"], r["thumbnail"], r["handle"] = sig.get("title"), sig.get("thumbnail"), sig.get("handle")
        r["subscribers"], r["videos"] = sig.get("subscribers"), sig.get("videos")
        r["top_signals"] = {k: v for k, v in sig.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
                            and k in ("website_route", "domain_match", "brn_match", "name_similarity",
                                      "dubai_context", "real_estate_context", "broker_name_similarity") and v}
        r["routes"] = sig.get("routes", [])
        r["url"] = f"https://www.youtube.com/channel/{r['channel_id']}"
        items.append(r)
    return {"items": items, "count": len(items)}


@v1.post("/review/channels/{channel_id}")
def review_decide(channel_id: str, body: ReviewDecision, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    from pitchops.fs import client as fs

    decision = {"accept": "manual_accept", "manual_accept": "manual_accept",
                "reject": "manual_reject", "manual_reject": "manual_reject"}.get(body.decision)
    if not decision or not channel_id.startswith("UC"):
        raise HTTPException(status_code=400, detail="decision must be manual_accept|reject")
    doc = {"decision": decision, "company_id": body.company_id, "broker_number": body.broker_number,
           "decided_by": user.get("email") or user.get("uid"), "decided_at": datetime.now(UTC).isoformat(),
           "applied": False}
    fs().collection("review_decisions").document(channel_id).set(doc)
    return {"channel_id": channel_id, **doc}


from services.api.explore import admin_router  # noqa: E402
from services.api.explore import router as explore_router  # noqa: E402
from services.api.media import media_router  # noqa: E402
from services.api.studio import studio_router  # noqa: E402

v1.include_router(explore_router)
v1.include_router(admin_router(require_user))
v1.include_router(studio_router(require_user))
v1.include_router(media_router(require_user))
app.include_router(v1, prefix="/v1")
app.include_router(v1, prefix="/api/v1")
