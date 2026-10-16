"""P7 stage B — Imagen portrait candidates for the 8 fictional presenters (D17). Approval-gated by the owner in chat
(test with one avatar first), budget-checked against the media cap, every image costed in llm_calls (job p7_imagen).
Candidates go to the PRIVATE bucket media/avatars/{avatar_id}/; the owner picks one per avatar in the web app.
Usage: uv run python -m jobs.avatars --avatar avatar_in [--n 4] | --all
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from typing import Any

from google import genai
from google.genai import types

from pitchops.bq import insert_rows
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.media.avatars import AVATARS, PORTRAIT_PROMPT
from pitchops.media.plans import budget_check

PAUSE_S = 20
NEGATIVE = "text, logo, watermark, celebrity likeness, cartoon, distorted hands, extra fingers, sunglasses"


def generate(avatar_id: str, n: int, run_id: str) -> dict[str, Any]:
    from pitchops.fs import client as fs
    from pitchops.gcs import upload_bytes
    from services.api.media import media_committed, project_spent

    s = get_settings()
    est = n * s.imagen_price
    why = budget_check(est, media_committed(), s.media_budget_usd, project_spent(), s.total_project_cap_usd)
    if why:
        raise RuntimeError(f"budget guard: {why}")
    a = AVATARS[avatar_id]
    prompt = PORTRAIT_PROMPT.format(heritage=a["heritage"], presentation=a["presentation"])
    client = genai.Client(vertexai=True, project=s.gcp_project_id, location=s.gemini_location)
    t0 = time.monotonic()
    status, cands, err = "OK", [], None
    try:
        cfg = types.GenerateContentConfig(response_modalities=["IMAGE"],
                                          image_config=types.ImageConfig(aspect_ratio="16:9"))
        for i in range(n):  # one image per call; the prompt asks for a fictional person, never a real one
            if i:
                time.sleep(PAUSE_S)  # stay under the per-minute image quota
            for attempt in (1, 2):
                try:
                    res = client.models.generate_content(model=s.imagen_model_id, contents=[
                        f"{prompt} Avoid: {NEGATIVE}. Variation {i + 1}."], config=cfg)
                    break
                except Exception as e:  # noqa: BLE001
                    if "RESOURCE_EXHAUSTED" in str(e) and attempt == 1:
                        time.sleep(60)
                        continue
                    raise
            parts = [p for c in (res.candidates or []) for p in (c.content.parts if c.content else [])]
            data = next((p.inline_data.data for p in parts if p.inline_data and p.inline_data.data), None)
            if data:
                gcs = upload_bytes(f"media/avatars/{avatar_id}/cand_{run_id[-6:]}_{i}.png", data, "image/png")
                cands.append({"id": f"{run_id[-6:]}_{i}", "gcs": gcs})
            else:
                err = str((res.candidates or [None])[0] and res.candidates[0].finish_reason) or "no image returned"
    except Exception as e:  # noqa: BLE001 — record the refusal; nothing else is retried
        status, err = "ERROR", f"{type(e).__name__}: {e}"[:400]
    ms = int((time.monotonic() - t0) * 1000)
    cost = round(len(cands) * s.imagen_price, 4)  # billed per generated image
    now = datetime.now(UTC).isoformat()
    insert_rows("llm_calls", [{"ts": now, "job": "p7_imagen", "model_id": s.imagen_model_id, "prompt_version": "portrait_v1",
                               "tokens_in": 0, "tokens_out": len(cands), "cost_usd_est": cost, "latency_ms": ms,
                               "status": status, "run_id": run_id, "ingested_at": now}])
    ref = fs().collection("avatars").document(avatar_id)
    doc = ref.get().to_dict() or {}
    ref.set({**doc, "avatar_id": avatar_id, "candidates": (doc.get("candidates") or []) + cands,
             "imagen_cost_usd": round(float(doc.get("imagen_cost_usd") or 0) + cost, 4),
             "status": "candidates_ready" if cands else f"generation failed: {err}", "prompt": prompt, "updated_at": now})
    return {"avatar_id": avatar_id, "candidates": len(cands), "cost_usd": cost, "status": status, "error": err}


def main(argv: list[str] | None = None) -> int:
    p = base_parser("avatars")
    p.add_argument("--avatar", choices=list(AVATARS))
    p.add_argument("--all", action="store_true")
    p.add_argument("--n", type=int, default=4)
    a = p.parse_args(argv)
    ids = list(AVATARS) if a.all else [a.avatar] if a.avatar else []
    if not ids:
        p.error("--avatar or --all")
    run_id = a.run_id or new_run_id("avatars")
    with job_run("avatars", run_id) as c:
        out = [generate(i, a.n, run_id) for i in ids]
        c.update(avatars=len(out), candidates=sum(o["candidates"] for o in out), cost_usd=sum(o["cost_usd"] for o in out))
    for o in out:
        print(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
