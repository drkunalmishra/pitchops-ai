"""P7 stage C — generate + compose APPROVED video plans (D16). Nothing runs for a plan that is not APPROVED, whose
content changed after approval (plan hash), whose avatar portrait is not approved, or that would breach the media /
project budget (checked again before every Veo clip). Every clip is costed in llm_calls (job p7_veo).

Per plan: Veo image-to-video clips (presenter intro/outro with dialogue audio from the approved portrait; silent hero
clips from official photos; <= 2 concurrent, 1 retry, then fallback to photo motion) -> FFmpeg final (1080p, -14 LUFS)
-> QC -> media/plans/{plan_id}/final.mp4 + thumbnail -> DONE (or REVIEW with QC reasons / FAILED).
Usage: uv run python -m jobs.media_generate [--plan-id ID] [--limit N] [--dry-run]
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pitchops.bq import insert_rows
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.media import plans as P
from pitchops.media import render as R
from pitchops.media import veo as V
from pitchops.media.avatars import AVATARS

CONCURRENCY = 2


class NotApproved(Exception):
    pass


def fs() -> Any:
    from pitchops.fs import client

    return client()


def gcs_bytes(uri: str) -> bytes:
    from pitchops.gcs import bucket

    return bucket().blob(uri.split("/", 3)[3]).download_as_bytes()


def gcs_download(uri: str, out: Path) -> Path:
    from pitchops.gcs import bucket

    bucket().blob(uri.split("/", 3)[3]).download_to_filename(out)
    return out


def as_jpeg(data: bytes, aspect: str = "16:9") -> bytes:
    """Veo accepts only JPEG / PNG first frames (official images can be WebP/AVIF), and pads a first frame whose
    aspect differs from the video's — so centre-crop to the target aspect first (9:16 Shorts would be letterboxed)."""
    import io

    from PIL import Image

    im = Image.open(io.BytesIO(data)).convert("RGB")
    tw, th = (16, 9) if aspect == "16:9" else (9, 16)
    w, h = im.size
    if w * th > h * tw:  # too wide -> crop width
        nw = h * tw // th
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:  # too tall -> crop height (keep a little more of the top: faces / rooftops)
        nh = w * th // tw
        top = max(0, int((h - nh) * 0.35))
        im = im.crop((0, top, w, top + nh))
    im.thumbnail((1920, 1920))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def check_runnable(plan: dict[str, Any], retry_failed: bool = False) -> None:
    """Raise NotApproved unless this exact plan was approved (pure — tested). retry_failed also allows a REVIEW plan
    (same approval, same hash) so only its failed Veo shots are generated again."""
    ok_states = ("APPROVED", "REVIEW") if retry_failed else ("APPROVED",)
    if plan.get("state") not in ok_states:
        raise NotApproved(f"{plan.get('plan_id')} is {plan.get('state')}, not APPROVED")
    appr = plan.get("approval") or {}
    if appr.get("plan_hash") != P.plan_hash(plan):
        raise NotApproved(f"{plan.get('plan_id')} changed after approval (plan hash mismatch)")


def ledger(run_id: str, plan_id: str, sec: float, audio: bool, ok: bool, ms: int) -> float:
    s = get_settings()
    cost = round(sec * (s.veo_price_audio_per_sec if audio else s.veo_price_silent_per_sec), 4) if ok else 0.0
    now = datetime.now(UTC).isoformat()
    insert_rows("llm_calls", [{"ts": now, "job": "p7_veo", "model_id": s.veo_model_id, "prompt_version": V.PROMPT_VERSION,
                               "tokens_in": 0, "tokens_out": int(sec), "cost_usd_est": cost, "latency_ms": ms,
                               "status": "OK" if ok else "ERROR", "run_id": f"{run_id}:{plan_id}", "ingested_at": now}])
    return cost


def generate_plan(plan: dict[str, Any], run_id: str, retry_failed: bool = False) -> dict[str, Any]:
    import time

    from google import genai

    from services.api.media import media_committed, project_spent

    s = get_settings()
    check_runnable(plan, retry_failed)
    av = fs().collection("avatars").document(plan["avatar_id"]).get().to_dict() or {}
    veo_shots = [(i, sh) for i, sh in enumerate(plan["shots"]) if sh.get("veo")]
    if any(sh["kind"].startswith("avatar") for _, sh in veo_shots) and not av.get("portrait_gcs"):
        raise NotApproved(f"avatar {plan['avatar_id']} has no approved portrait yet")
    ref = fs().collection("video_plans").document(plan["plan_id"])
    ref.update({"state": "GENERATING", "updated_at": datetime.now(UTC).isoformat()})
    client = genai.Client(vertexai=True, project=s.gcp_project_id, location=s.gcp_region)
    portrait = gcs_bytes(av["portrait_gcs"]) if av.get("portrait_gcs") else None
    aspect = "16:9" if plan["format"] == "16x9" else "9:16"
    voice = AVATARS[plan["avatar_id"]]["veo_voice"]
    base = f"gs://{s.bucket}/media/plans/{plan['plan_id']}/veo/{run_id[-6:]}"
    spent = 0.0
    done_clips: dict[str, str] = dict(plan.get("veo_clips") or {})

    def one(i: int, sh: dict[str, Any]) -> tuple[int, str | None, float]:
        nonlocal spent
        if str(i) in done_clips:  # already generated (and paid) in an earlier run: reuse
            return i, done_clips[str(i)], 0.0
        audio = bool(sh.get("audio"))
        est = sh["sec"] * (s.veo_price_audio_per_sec if audio else s.veo_price_silent_per_sec)
        # the plan's own estimate is already committed; guard against anything beyond it
        why = P.budget_check(max(0.0, spent + est - plan["est_cost_usd"]), media_committed(), s.media_budget_usd,
                             project_spent(), s.total_project_cap_usd)
        if why:
            log("veo_budget_stop", severity="WARNING", plan_id=plan["plan_id"], why=why)
            return i, None, 0.0
        if sh["kind"].startswith("avatar"):
            img, mime, prompt = as_jpeg(portrait, aspect), "image/jpeg", V.presenter_prompt(sh["text"], voice)
        else:
            img, mime, prompt = as_jpeg(gcs_bytes(sh["image_gcs"]), aspect), "image/jpeg", V.PROMPTS[sh["prompt_key"]]
        for attempt in (1, 2):
            t0 = time.monotonic()
            try:
                uri = V.generate_clip(client, s.veo_model_id, prompt, img, mime, aspect, int(sh["sec"]), audio,
                                      f"{base}/shot{i:02d}_a{attempt}/")
                cost = ledger(run_id, plan["plan_id"], sh["sec"], audio, True, int((time.monotonic() - t0) * 1000))
                spent += cost
                return i, uri, cost
            except Exception as e:  # noqa: BLE001 — one retry, then the composer falls back to photo motion
                ledger(run_id, plan["plan_id"], sh["sec"], audio, False, int((time.monotonic() - t0) * 1000))
                log("veo_clip_failed", severity="WARNING", plan_id=plan["plan_id"], shot=i, attempt=attempt,
                    error=f"{type(e).__name__}: {e}"[:300])
                if "PERMISSION_DENIED" in str(e) or "policies" in str(e).lower():
                    raise  # never hammer a policy refusal
                if "filtered" in str(e).lower() or "usage guidelines" in str(e).lower():
                    break  # safety-filtered: don't retry the same input; the composer uses the free fallback
        return i, None, 0.0

    with ThreadPoolExecutor(CONCURRENCY) as pool:
        results = list(pool.map(lambda x: one(*x), veo_shots))
    actual = round(float(plan.get("actual_cost_usd") or 0) + sum(c for _, _, c in results), 2)
    ref.update({"state": "COMPOSING", "actual_cost_usd": actual,
                "veo_clips": {str(i): u for i, u, _ in results if u}, "updated_at": datetime.now(UTC).isoformat()})
    from jobs.media_plans import render_preview

    wd = R.workdir()
    clips = {i: gcs_download(u if u.endswith(".mp4") else u, wd / f"veo_{i}.mp4") for i, u, _ in results if u}
    port = None
    if av.get("portrait_gcs"):
        port = gcs_download(av["portrait_gcs"], wd / "portrait.png")
    out, chars = render_preview(plan, wd, final=True, clips=clips, portrait=port)
    errs = R.qc(out, plan["format"], plan["max_sec"])
    thumb = wd / "thumb.jpg"
    R.run(["ffmpeg", "-y", "-ss", "2", "-i", str(out), "-frames:v", "1", "-q:v", "3", str(thumb)])
    from pitchops.gcs import upload_bytes

    final_uri = upload_bytes(f"media/plans/{plan['plan_id']}/final.mp4", out.read_bytes(), "video/mp4")
    thumb_uri = upload_bytes(f"media/plans/{plan['plan_id']}/thumb.jpg", thumb.read_bytes(), "image/jpeg")
    failed = [i for i, u, _ in results if not u]
    state = "DONE" if not errs and not failed else "REVIEW"
    ref.update({"state": state, "final_gcs": final_uri, "thumb_gcs": thumb_uri, "final_qc": errs,
                "final_duration_sec": round(R.duration(out), 1), "failed_veo_shots": failed, "tts_chars_final": chars,
                "updated_at": datetime.now(UTC).isoformat()})
    return {"plan_id": plan["plan_id"], "state": state, "actual_cost_usd": actual, "clips": len(clips),
            "failed_shots": failed, "qc": errs}


def main(argv: list[str] | None = None) -> int:
    p = base_parser("media_generate")
    p.add_argument("--plan-id")
    p.add_argument("--retry-failed", action="store_true", help="re-run only failed Veo shots of REVIEW plans")
    a = p.parse_args(argv)
    q = [d.to_dict() for d in fs().collection("video_plans").stream()]
    todo = [x for x in q if (x["plan_id"] == a.plan_id if a.plan_id else x["state"] == "APPROVED")]
    todo = todo[: a.limit] if a.limit else todo
    if a.dry_run:
        print([{"plan_id": x["plan_id"], "state": x["state"], "est": x["est_cost_usd"]} for x in todo])
        return 0
    run_id = a.run_id or new_run_id("media")
    out = []
    with job_run("media_generate", run_id) as c:
        for x in todo:
            try:
                out.append(generate_plan(x, run_id, a.retry_failed))
            except NotApproved as e:
                out.append({"plan_id": x["plan_id"], "refused": str(e)})
            except Exception as e:  # noqa: BLE001
                fs().collection("video_plans").document(x["plan_id"]).update(
                    {"state": "FAILED", "error": f"{type(e).__name__}: {e}"[:500]})
                out.append({"plan_id": x["plan_id"], "failed": f"{type(e).__name__}: {e}"[:300]})
                if "PERMISSION_DENIED" in str(e):
                    break  # policy refusal: stop the whole run
        c.update(plans=len(out), done=sum(1 for o in out if o.get("state") == "DONE"),
                 refused=sum(1 for o in out if "refused" in o), failed=sum(1 for o in out if "failed" in o),
                 cost_usd=round(sum(o.get("actual_cost_usd", 0) for o in out), 2))
    for o in out:
        print(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
