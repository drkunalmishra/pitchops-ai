"""PitchOps API (Cloud Run). /v1/* requires a Firebase ID token.

Routes are served both at /v1/... and /api/v1/... because Firebase Hosting forwards the full /api/** path.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import firebase_admin
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth as fb_auth

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
          (SELECT COUNT(*) FROM `{t('videos')}`) AS videos,
          (SELECT COUNTIF(is_short) FROM `{t('videos')}`) AS shorts,
          (SELECT COALESCE(SUM(units),0) FROM `{t('quota_ledger')}` WHERE day_pt = @d) AS quota_units_today,
          (SELECT COALESCE(SUM(cost_usd_est),0) FROM `{t('llm_calls')}`) AS gemini_spend_usd_est,
          (SELECT COUNT(*) FROM `{t('llm_calls')}`) AS gemini_calls""",
        {"d": day_pt().isoformat()},
    )[0]
    data = {**row, "gemini_spend_usd_est": round(float(row["gemini_spend_usd_est"]), 4),
            "quota_cap": settings.yt_daily_unit_cap, "gemini_budget_usd": settings.gemini_budget_usd,
            "as_of": datetime.now(UTC).isoformat()}
    _cache.update(at=time.monotonic(), data=data)
    return data


v1 = APIRouter(dependencies=[Depends(require_user)])


@v1.get("/corpus/stats")
def get_corpus_stats() -> dict[str, Any]:
    return corpus_stats()


app.include_router(v1, prefix="/v1")
app.include_router(v1, prefix="/api/v1")
