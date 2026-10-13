"""Thin BigQuery helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from google.cloud import bigquery

from pitchops.config import get_settings


@lru_cache
def client() -> bigquery.Client:
    s = get_settings()
    return bigquery.Client(project=s.gcp_project_id, location=s.gcp_region)


def query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(k, _bq_type(k, v), v) for k, v in (params or {}).items()
        ]
    )
    return [dict(r) for r in client().query(sql, job_config=cfg).result()]


def insert_rows(table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    errors = client().insert_rows_json(get_settings().table(table), rows)
    if errors:
        raise RuntimeError(f"BigQuery insert into {table} failed: {errors[:3]}")


def _bq_type(name: str, v: Any) -> str:
    if isinstance(v, bool):
        return "BOOL"
    if isinstance(v, int):
        return "INT64"
    if isinstance(v, float):
        return "FLOAT64"
    if name in ("d", "day") or name.endswith("_date"):
        return "DATE"
    return "STRING"
