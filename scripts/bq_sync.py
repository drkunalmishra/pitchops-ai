"""Create missing BigQuery tables and add new NULLABLE columns. Never drops or alters existing columns."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from pitchops.bq import client
from pitchops.config import get_settings


def to_field(f: dict) -> bigquery.SchemaField:
    return bigquery.SchemaField(f["name"], f["type"], mode=f.get("mode", "NULLABLE"))


def main() -> int:
    s = get_settings()
    bq = client()
    created = altered = unchanged = 0
    for path in sorted((Path(__file__).resolve().parents[1] / "schemas" / "bq").glob("*.json")):
        spec = json.loads(path.read_text())
        ref = s.table(spec["table"])
        want = [to_field(f) for f in spec["fields"]]
        try:
            tbl = bq.get_table(ref)
        except NotFound:
            tbl = bigquery.Table(ref, schema=want)
            if tp := spec.get("time_partitioning"):
                tbl.time_partitioning = bigquery.TimePartitioning(field=tp["field"], type_=tp["type"])
            tbl.clustering_fields = spec.get("clustering") or None
            bq.create_table(tbl)
            print(f"CREATED  {spec['table']}")
            created += 1
            continue
        want_mode = {f.name: f.mode for f in want}
        relaxed = [f.name for f in tbl.schema if f.mode == "REQUIRED" and want_mode.get(f.name) == "NULLABLE"]
        if relaxed:  # REQUIRED -> NULLABLE is a non-destructive schema change
            tbl.schema = [bigquery.SchemaField(f.name, f.field_type, mode="NULLABLE", fields=f.fields)
                          if f.name in relaxed else f for f in tbl.schema]
            tbl = bq.update_table(tbl, ["schema"])
            print(f"RELAXED  {spec['table']} {relaxed}")
            altered += 1
        have = {f.name for f in tbl.schema}
        new = [bigquery.SchemaField(f.name, f.field_type, mode="NULLABLE" if f.mode == "REQUIRED" else f.mode)
               for f in want if f.name not in have]
        if new:
            tbl.schema = list(tbl.schema) + new
            bq.update_table(tbl, ["schema"])
            print(f"ALTERED  {spec['table']} +{[f.name for f in new]}")
            altered += 1
        elif not relaxed:
            unchanged += 1
    print(f"tables: created={created} altered={altered} unchanged={unchanged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
