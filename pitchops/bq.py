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


def query(sql: str, params: dict[str, Any] | None = None, max_bytes: int | None = None) -> list[dict[str, Any]]:
    """max_bytes caps bytes billed (the query fails instead of scanning more) — used by the UI API."""
    cfg = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(k, "STRING", v) if isinstance(v, list)
            else bigquery.ScalarQueryParameter(k, _bq_type(k, v), v) for k, v in (params or {}).items()
        ]
    )
    if max_bytes:
        cfg.maximum_bytes_billed = max_bytes
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


def schema_for(table: str) -> list[bigquery.SchemaField]:
    import json
    from pathlib import Path

    spec = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "bq" / f"{table}.json").read_text())
    return [bigquery.SchemaField(f["name"], f["type"], mode=f["mode"]) for f in spec["fields"]]


def merge_rows(table: str, rows: list[dict[str, Any]], keys: list[str],
               update_cols: list[str] | None = None) -> int:
    """Idempotent upsert: load rows into a staging table, MERGE on keys, drop staging. Returns rows staged.

    update_cols limits which columns are overwritten on match (default: all non-key columns).
    """
    import json
    import uuid

    if not rows:
        return 0
    s = get_settings()
    schema = schema_for(table)
    names = [f.name for f in schema]
    # dedupe on keys inside the batch (last wins) so MERGE never sees duplicate source rows
    dedup: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        dedup[tuple(r.get(k) for k in keys)] = r
    payload = []
    for r in dedup.values():
        row = {k: r.get(k) for k in names if k in r}
        for f in schema:
            # load jobs serialize rows themselves: JSON columns must be objects, not pre-encoded strings
            val = row.get(f.name)
            if f.field_type == "JSON" and isinstance(val, str):
                row[f.name] = json.loads(val)
            elif f.field_type == "JSON" and row.get(f.name) is not None:
                row[f.name] = json.loads(json.dumps(row[f.name], default=str))
        payload.append(row)
    stg = f"{s.gcp_project_id}.{s.bq_dataset}._stg_{table}_{uuid.uuid4().hex[:8]}"
    stg_schema = [bigquery.SchemaField(f.name, f.field_type, mode="NULLABLE" if f.mode == "REQUIRED" else f.mode)
                  for f in schema]
    cfg = bigquery.LoadJobConfig(schema=stg_schema, write_disposition="WRITE_TRUNCATE",
                                 source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON)
    client().load_table_from_json(payload, stg, job_config=cfg).result()
    try:
        present = [n for n in names if any(n in p for p in payload)]
        upd = [c for c in (update_cols or present) if c not in keys and c in present]
        on = " AND ".join(f"T.{k} = S.{k}" for k in keys)
        set_clause = ", ".join(f"{c} = S.{c}" for c in upd) or f"{keys[0]} = S.{keys[0]}"
        cols = ", ".join(present)
        vals = ", ".join(f"S.{c}" for c in present)
        client().query(
            f"MERGE `{s.table(table)}` T USING `{stg}` S ON {on} "
            f"WHEN MATCHED THEN UPDATE SET {set_clause} "
            f"WHEN NOT MATCHED THEN INSERT ({cols}) VALUES ({vals})"
        ).result()
    finally:
        client().delete_table(stg, not_found_ok=True)
    return len(payload)
