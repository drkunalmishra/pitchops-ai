"""P3 Step 6b — load deep_v2 analyses produced by hand in AI Studio (while Vertex was policy-blocked) into the same
tables the Vertex path writes (video_analysis, video_metrics_derived, property_mentions).

Input: exports/ai_studio/returned/batch_*.json (git-ignored, phones already redacted). Each analysis goes through the
same checks as a Vertex result (JSON schema, normalize_mmss, validate) plus load-time re-checks for output we did not
generate ourselves (deep_video.recheck_claims: self-cited sources -> unsourced, missed yield claims added) and a few
mention fixes. Idempotent (MERGE on video_id / mention_id); videos that already have a succeeded Vertex analysis are
skipped. No Gemini calls, no cost.

Long videos (> 5 min, --long): returned/long_*.json analysed in AI Studio from the FIRST 5 MINUTES only (one clip
0-300 s instead of D8's 3 clips) -> coverage 'partial', clips [0-300], model_id marks the first-5-min provenance.

Usage:
  uv run python -m jobs.ingest_ai_studio --dry-run     # validate + print stats, write nothing
  uv run python -m jobs.ingest_ai_studio
  uv run python -m jobs.ingest_ai_studio --long [--dry-run]
"""

from __future__ import annotations

import copy
import csv
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema

from jobs.deep_analysis import apply_relevance_recheck, flush, t
from pitchops.analysis import deep_video
from pitchops.bq import query
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log

ROOT = Path(__file__).resolve().parents[1] / "exports" / "ai_studio"
MODEL_ID = "ai-studio:gemini-flash (manual)"
MODEL_ID_LONG = "ai-studio:gemini-flash (manual, first 5 min)"
LONG_CLIP = (0, 300)
PHONE = re.compile(r"\+?971[\s-]?\d[\d\s-]{7,11}\d|(?<!\d)05\d[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
# mention fixes the model got wrong or left empty (project canonical key -> fields to fill when missing)
MENTION_FILL = {
    "siniya island": {"emirate": "Umm Al Quwain"},
    "damac riverside": {"area": "Dubai Investment Park"},
}


def durations() -> dict[str, int]:
    with (ROOT / "videos_for_deep_analysis.csv").open() as f:
        return {r["video_id"]: int(r["duration_sec"]) for r in csv.DictReader(f)}


def load_files(pattern: str = "batch_*.json") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sorted(glob.glob(str(ROOT / "returned" / pattern))):
        for a in json.load(open(p))["analyses"]:
            out.append({**a, "_file": Path(p).name})
    return out


def fix_mentions(mentions: list[dict[str, Any]]) -> int:
    from pitchops.properties.normalize import canonical_key

    n = 0
    for m in mentions:
        for k, fill in MENTION_FILL.items():
            if canonical_key(m.get("project_name")) == k:
                for f, v in fill.items():
                    if not m.get(f):
                        m[f] = v
                        n += 1
    return n


def build(a: dict[str, Any], dur: int, schema: dict[str, Any], long: bool = False
          ) -> tuple[dict[str, Any], dict[str, int]]:
    d = {k: copy.deepcopy(a[k]) for k in ("overview", "segments", "claims", "property_mentions")}
    stats: Counter[str] = Counter()
    coverage, clips = ("partial", [LONG_CLIP]) if long else deep_video.clips_for(dur)
    base = {"video_id": a["video_id"], "prompt_version": deep_video.PROMPT_VERSION,
            "model_id": MODEL_ID_LONG if long else MODEL_ID,
            "coverage": coverage, "clips": [{"start": x, "end": y} for x, y in clips], "duration_sec": dur,
            "tokens_in": None, "tokens_out": None, "cost_usd_est": 0.0, "attempts": 1}
    try:
        jsonschema.validate(d, schema)
    except jsonschema.ValidationError as e:
        return {**base, "status": "needs_review", "error": f"schema: {e.message}"[:1000],
                "validation_errors": [e.message[:300]]}, {"schema_fail": 1}
    stats["mmss_fixed"] += deep_video.normalize_mmss(d, LONG_CLIP[1] if long else dur)
    errs = deep_video.validate(d, dur, coverage, clips)
    if errs:
        return {**base, "status": "needs_review", "error": "; ".join(errs)[:1000],
                "validation_errors": errs[:20]}, {"validate_fail": 1}
    stats.update(deep_video.recheck_claims(d))
    stats["mention_fixes"] += fix_mentions(d["property_mentions"])
    ov = d["overview"]
    if ov.get("cta_text"):
        ov["cta_text"], n = PHONE.subn("[phone]", ov["cta_text"])
        stats["phones"] += n
    return {**base, "status": "succeeded", "overview": ov, "segments": d["segments"], "claims": d["claims"],
            "property_mentions": d["property_mentions"], "archetype": ov["archetype"], "hook_type": ov["hook_type"],
            "sales_frameworks": ov["sales_frameworks"], "buyer_personas": ov["buyer_personas"],
            "buyer_motive": ov["buyer_motive"], "buyer_triggers": ov["buyer_triggers"],
            "origin_personas": ov["origin_personas"], "cta_type": ov["cta_type"], "language": ov["language"],
            "validation_errors": [], "_derived": deep_video.derived_metrics(d, sum(y - x for x, y in clips))}, stats


def main(argv: list[str] | None = None) -> int:
    p = base_parser("ingest_ai_studio")
    p.add_argument("--long", action="store_true", help="load long_*.json (videos > 5 min, first 5 min only)")
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("ai-studio")
    dur = durations()
    rows = load_files("long_*.json" if a.long else "batch_*.json")
    if a.limit:
        rows = rows[:a.limit]
    have = {r["video_id"] for r in query(f"""SELECT video_id FROM `{t('video_analysis')}`
        WHERE status = 'succeeded' AND model_id NOT IN (@m, @ml)""", {"m": MODEL_ID, "ml": MODEL_ID_LONG})}
    schema = deep_video.schema()
    out, stats = [], Counter()
    seen: set[str] = set()
    for r in rows:
        vid = r["video_id"]
        if vid in seen or vid in have:
            stats["skipped_duplicate_or_vertex"] += 1
            continue
        seen.add(vid)
        if vid not in dur:
            stats["unknown_video"] += 1
            log("ai_studio_unknown_video", severity="WARNING", video_id=vid, file=r["_file"])
            continue
        if a.long and dur[vid] <= deep_video.FULL_MAX_SEC:
            stats["not_long"] += 1
            continue
        row, st = build(r, dur[vid], schema, a.long)
        stats.update(st)
        stats[row["status"]] += 1
        stats["irrelevant"] += row.get("overview", {}).get("is_uae_real_estate") is False
        out.append(row)
    print({"run_id": run_id, "files_rows": len(rows), **dict(stats)})
    if a.dry_run:
        return 0
    with job_run("ingest_ai_studio", run_id) as c:
        for i in range(0, len(out), 100):
            flush(out[i:i + 100], run_id)
        c.update({k: int(v) for k, v in stats.items()})
        c["relevance_downgraded"] = apply_relevance_recheck()
    print({"run_id": run_id, "written": len(out), "relevance_downgraded": c["relevance_downgraded"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
