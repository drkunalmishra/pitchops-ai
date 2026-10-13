"""Load the DLD broker registry into BigQuery with PII minimization.

Drops phone and full email; keeps email_domain + is_corporate_email only (CLAUDE.md §2 rule 4).
Usage: uv run python -m jobs.load_registry [--dry-run] [--limit N] [--run-id ID] [--write-sample]
"""

from __future__ import annotations

import csv
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id

ROOT = Path(__file__).resolve().parents[1]
BROKERS_CSV = ROOT / "inputs" / "brokers_clean.csv"
COMPANIES_CSV = ROOT / "inputs" / "companies_seed.csv"
SAMPLE_CSV = ROOT / "data" / "sample" / "brokers_sample.csv"

BROKER_COLS = ["broker_number", "name_en", "name_ar", "office_name_en", "office_name_ar", "company_id",
               "email_domain", "is_corporate_email"]
FORBIDDEN = {"phone", "email", "mobile", "email_address"}


def _bool(v: str) -> bool:
    return v.strip().lower() in {"true", "1", "yes", "y"}


def _clean(v: str | None) -> str | None:
    v = (v or "").strip()
    return v or None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def build_companies(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        domains = [d.strip().lower() for d in (r.get("corporate_domains") or "").split("|") if d.strip()]
        out.append({
            "company_id": r["company_id"].strip(),
            "company_key": _clean(r.get("company_key")),
            "office_names_en": _clean(r.get("office_names_en")),
            "office_name_ar": _clean(r.get("office_name_ar")),
            "broker_count": int(r["broker_count"]) if (r.get("broker_count") or "").strip() else None,
            "primary_domain": _clean((r.get("primary_domain") or "").lower()),
            "corporate_domains": domains,
            "discovery_tier": _clean(r.get("discovery_tier")),
        })
    return out


def build_brokers(rows: list[dict[str, str]], key_to_id: dict[str, str]) -> list[dict[str, Any]]:
    """Projects only the allowed columns — phone and full email never leave this function."""
    out = []
    for r in rows:
        out.append({
            "broker_number": r["broker_number"].strip(),
            "name_en": _clean(r.get("name_en")),
            "name_ar": _clean(r.get("name_ar")),
            "office_name_en": _clean(r.get("office_name_en")),
            "office_name_ar": _clean(r.get("office_name_ar")),
            "company_id": key_to_id.get((r.get("company_key") or "").strip()),
            "email_domain": _clean((r.get("email_domain") or "").lower()),
            "is_corporate_email": _bool(r.get("is_corporate_email") or ""),
        })
    return out


def validate(brokers: list[dict[str, Any]], companies: list[dict[str, Any]]) -> dict[str, int]:
    nums = [b["broker_number"] for b in brokers]
    if len(nums) != len(set(nums)):
        raise ValueError(f"broker_number not unique: {len(nums) - len(set(nums))} duplicates")
    if any(not n for n in nums):
        raise ValueError("blank broker_number")
    ids = [c["company_id"] for c in companies]
    if len(ids) != len(set(ids)):
        raise ValueError("company_id not unique")
    for b in brokers[:1]:
        leaked = FORBIDDEN & set(b)
        if leaked:
            raise ValueError(f"PII columns present: {leaked}")
    return {"brokers_without_company": sum(1 for b in brokers if not b["company_id"])}


def load(table: str, rows: list[dict[str, Any]], run_id: str) -> int:
    s = get_settings()
    from pitchops.bq import client

    spec = json.loads((ROOT / "schemas" / "bq" / f"{table}.json").read_text())
    schema = [bigquery.SchemaField(f["name"], f["type"], mode=f["mode"]) for f in spec["fields"]]
    now = datetime.now(UTC).isoformat()
    payload = [{**r, "run_id": run_id, "ingested_at": now} for r in rows]
    cfg = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE",
                                 source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON)
    client().load_table_from_json(payload, s.table(table), job_config=cfg).result()
    return int(client().get_table(s.table(table)).num_rows or 0)


def assert_no_pii_columns() -> list[str]:
    from pitchops.bq import query

    s = get_settings()
    rows = query(
        f"SELECT table_name, column_name FROM `{s.gcp_project_id}.{s.bq_dataset}.INFORMATION_SCHEMA.COLUMNS` "
        "WHERE LOWER(column_name) LIKE '%phone%' OR LOWER(column_name) IN ('email','email_address','mobile')"
    )
    bad = [f"{r['table_name']}.{r['column_name']}" for r in rows]
    if bad:
        raise AssertionError(f"PII columns found in BigQuery: {bad}")
    return bad


def write_synthetic_sample(n: int = 50, seed: int = 7) -> None:
    """Synthetic rows only — no real names, numbers or domains. Uses reserved *.test domains."""
    rnd = random.Random(seed)
    first = ["Aisha", "Omar", "Priya", "Daniel", "Fatima", "Ivan", "Mei", "Rahul", "Sara", "Yusuf"]
    last = ["Example", "Sample", "Demo", "Placeholder", "Testcase"]
    offices = [("Palm Example Realty", "عقارات النخلة التجريبية"), ("Marina Demo Homes", "منازل المرسى التجريبية"),
               ("Downtown Sample Brokers", "وسطاء وسط المدينة"), ("Creek Test Properties", "عقارات الخور")]
    SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SAMPLE_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name_en", "name_ar", "broker_number", "office_name_en", "office_name_ar",
                    "email_domain", "is_corporate_email", "company_key"])
        for i in range(n):
            off_en, off_ar = offices[i % len(offices)]
            corp = rnd.random() < 0.4
            dom = off_en.split()[0].lower() + "-realty.test" if corp else "freemail.test"
            w.writerow([f"{rnd.choice(first)} {rnd.choice(last)}", "وسيط تجريبي", f"T{900000 + i}",
                        off_en, off_ar, dom, corp, off_en.lower().replace(" ", "_")])


def main(argv: list[str] | None = None) -> int:
    p = base_parser("load_registry")
    p.add_argument("--write-sample", action="store_true", help="also (re)write data/sample/brokers_sample.csv")
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("load_registry")
    with job_run("load_registry", run_id, dry_run=a.dry_run) as c:
        companies = build_companies(read_csv(COMPANIES_CSV))
        key_to_id = {(r.get("company_key") or "").strip(): r["company_id"].strip()
                     for r in read_csv(COMPANIES_CSV)}
        brokers = build_brokers(read_csv(BROKERS_CSV), key_to_id)
        if a.limit:
            brokers = brokers[: a.limit]
        c.update(validate(brokers, companies))
        c["brokers_read"], c["companies_read"] = len(brokers), len(companies)
        if a.write_sample:
            write_synthetic_sample()
            c["sample_rows"] = 50
        if a.dry_run:
            return 0
        c["brokers_loaded"] = load("brokers", brokers, run_id)
        c["companies_loaded"] = load("companies", companies, run_id)
        assert_no_pii_columns()
        c["pii_columns"] = 0
    print(json.dumps({"run_id": run_id, **c}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
