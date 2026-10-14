"""Manual review decisions: the API writes Firestore review_decisions/{channel_id}; jobs apply them to BigQuery."""

from __future__ import annotations

from typing import Any

from pitchops.bq import merge_rows
from pitchops.discovery.common import now_iso
from pitchops.discovery.resolve import channel_row, upsert_channels
from pitchops.logs import log
from pitchops.youtube.client import YouTubeClient

COLLECTION = "review_decisions"


def pending() -> list[dict[str, Any]]:
    from pitchops.fs import client

    return [{"channel_id": d.id, **(d.to_dict() or {})}
            for d in client().collection(COLLECTION).where("applied", "==", False).stream()]


def apply_decisions(yt: YouTubeClient, run_id: str) -> dict[str, int]:
    from pitchops.fs import client

    todo = pending()
    if not todo:
        return {"review_applied": 0}
    matches, accepted = [], []
    details = {c["id"]: c for c in yt.channels_by_ids([d["channel_id"] for d in todo if d["decision"] == "manual_accept"])}
    for d in todo:
        m = {"channel_id": d["channel_id"], "company_id": d.get("company_id"), "broker_number": d.get("broker_number"),
             "match_type": d.get("match_type") or "manual", "match_score": d.get("match_score"),
             "decision": d["decision"], "decided_by": d.get("decided_by"), "decided_at": d.get("decided_at"),
             "run_id": run_id, "ingested_at": now_iso()}
        matches.append(m)
        if d["decision"] == "manual_accept" and d["channel_id"] in details:
            accepted.append(channel_row(details[d["channel_id"]], m, run_id))
    merge_rows("channel_matches", matches, ["channel_id"], update_cols=[
        "company_id", "broker_number", "match_type", "decision", "decided_by", "decided_at", "run_id", "ingested_at"])
    upsert_channels(accepted)
    for d in todo:
        client().collection(COLLECTION).document(d["channel_id"]).update({"applied": True, "applied_run_id": run_id})
    log("review_applied", n=len(todo), accepted=len(accepted))
    return {"review_applied": len(todo), "review_accepted": len(accepted)}
