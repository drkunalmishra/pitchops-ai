"""P7 step 4 — video plans + FREE previews (no Veo / Imagen).

--create : 40 DRAFT plans in Firestore video_plans (20 x 16:9 + 20 x 9:16), each matched to the property's script in
           the right format, avatars rotated (~5 uses each), shot list + Veo cost estimate (conservative list prices).
--preview: render a low-res preview for every DRAFT plan: Cloud TTS narration (avatar voice) + Ken Burns over the
           selected official photos + captions + fact card + CTA card; Veo shots shown as labelled placeholders.
           Uploads media/plans/{plan_id}/preview.mp4 (private bucket) -> PREVIEW_READY. Cost: TTS characters only.
Usage: uv run python -m jobs.media_plans --create | --preview [--limit N] [--plan-id ID]
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from pitchops.bq import query
from pitchops.config import get_settings
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.media import plans as P
from pitchops.media import render as R
from pitchops.media.avatars import AVATARS
from pitchops.workflow.scripts import WPS, words


def fs() -> Any:
    from pitchops.fs import client

    return client()


def create(force: bool) -> dict[str, Any]:
    s = get_settings()
    db = fs()
    props = query(f"""SELECT property_id, canonical_name, media_candidate, area, emirate, rank
        FROM `{s.table('properties_ranked')}` WHERE media_candidate IS NOT NULL ORDER BY rank""")
    scripts = [d.to_dict() for d in db.collection("scripts").stream()]
    imgs = {d.id: d.to_dict().get("images", []) for d in db.collection("property_images").stream()}
    existing = {d.id for d in db.collection("video_plans").select(["state"]).stream()}
    rows = []
    for p in props:
        fmt_key = {"walkthrough": "walkthrough_16x9", "short": "short_9x16"}[p["media_candidate"]]
        cands = [x for x in scripts if x["property_id"] == p["property_id"] and x["format"] == fmt_key
                 and not x.get("demo_case")]
        if not cands:
            log("plan_no_script", severity="WARNING", property_id=p["property_id"])
            continue
        sc = sorted(cands, key=lambda x: (x.get("status") != "approved", -x.get("version", 1)))[0]
        rows.append((p, fmt_key, sc))
    avatars = rotate_avatars_for(rows)
    made = 0
    for (p, fmt_key, sc), av in zip(rows, avatars, strict=True):
        fmt = P.FORMAT_OF[fmt_key]
        plan_id = f"plan_{p['property_id'].removeprefix('prop_')}_{fmt}"
        if plan_id in existing and not force:
            continue
        narr_sec = len(words(" ".join(n["text"] for n in sc["current"]["narration"]))) / WPS
        shot_list = P.shots(sc, fmt, imgs.get(p["property_id"], []), narr_sec)
        plan = {"plan_id": plan_id, "property_id": p["property_id"], "property_name": p["canonical_name"],
                "area": ", ".join(x for x in (p["area"], p["emirate"]) if x), "format": fmt, "script_id": sc["script_id"],
                "script_version": sc.get("version", 1), "script_status": sc.get("status"), "avatar_id": av,
                "shots": shot_list, "est_cost_usd": P.cost(shot_list, s.veo_price_audio_per_sec, s.veo_price_silent_per_sec),
                "est_duration_sec": round(sum(x["sec"] for x in shot_list), 1), "max_sec": P.MAX_SEC[fmt],
                "images_selected": sum(1 for i in imgs.get(p["property_id"], []) if i.get("selected")),
                "state": "DRAFT", "created_at": datetime.now(UTC).isoformat()}
        plan["plan_hash"] = P.plan_hash(plan)
        db.collection("video_plans").document(plan_id).set(plan)
        made += 1
    return {"plans_created": made, "properties": len(props), "with_script": len(rows)}


def rotate_avatars_for(rows: list[tuple[dict[str, Any], str, dict[str, Any]]]) -> list[str]:
    per = -(-len(rows) // len(AVATARS))
    return P.rotate_avatars([sc.get("avatar_id", "avatar_na") for _, _, sc in rows], list(AVATARS), per)


def fetch_image(gcs: str, wd: Path) -> Path:
    from pitchops.gcs import bucket

    name = gcs.split("/", 3)[3]
    out = wd / Path(name).name
    if not out.exists():
        bucket().blob(name).download_to_filename(out)
        im = Image.open(out).convert("RGB")
        im.thumbnail((2400, 2400))
        out = out.with_suffix(".jpg")
        im.save(out, "JPEG", quality=88)
    return out.with_suffix(".jpg")


def fit_to_limit(plan: dict[str, Any], wd: Path) -> bool:
    """Measure real TTS lengths and drop trailing narration lines (keep >= 2) until the video fits its limit.
    Mutates plan["shots"]; returns True if anything was dropped."""
    av = AVATARS[plan["avatar_id"]]

    def length(sh: dict[str, Any]) -> float:
        if sh.get("veo") or sh["kind"] == "hero_clip":
            return float(sh["sec"])
        if sh.get("text"):
            return R.duration(R.tts(sh["text"], av["voice"], wd)) + (0.6 if sh["kind"] == "cta_card" else 0.35)
        return float(sh["sec"])

    dropped = False
    while sum(length(sh) for sh in plan["shots"]) > plan["max_sec"] - 0.5:
        narr = [i for i, sh in enumerate(plan["shots"]) if sh["kind"] == "narration"]
        if len(narr) <= 2:
            break
        plan["shots"].pop(narr[-1])
        dropped = True
    return dropped


def render_preview(plan: dict[str, Any], wd: Path, final: bool = False, clips: dict[int, Path] | None = None,
                   portrait: Path | None = None) -> tuple[Path, int]:
    """Compose the video. Preview: placeholders for Veo shots. Final: real Veo clips where present; a failed or non-Veo
    presenter shot becomes the approved portrait + TTS, a failed hero clip becomes photo motion (fallback ladder)."""
    clips = clips or {}
    size = R.SIZES[plan["format"]]["final" if final else "preview"]
    av = AVATARS[plan["avatar_id"]]
    parts: list[Path] = []
    chars = 0
    lower = f"{plan['property_name']} · {plan['area']}" if plan.get("area") else plan["property_name"]
    for i, sh in enumerate(plan["shots"]):
        seg = wd / f"seg_{i:02d}.mp4"
        if i in clips:
            R.clip_segment(seg, size, clips[i], keep_audio=sh["kind"] != "hero_clip", seconds=sh["sec"])
        elif sh["kind"] in ("avatar_intro", "avatar_outro") and final and portrait:
            audio = R.tts(sh["text"], av["voice"], wd)
            chars += len(sh["text"])
            ov = R.caption(wd / f"ov_{i}.png", size, sh["text"], lower_third=f"{av['name']} · {R.BRAND}")
            R.segment(seg, size, audio, portrait, ov, motion=i)
        elif sh["kind"] in ("avatar_intro", "avatar_outro"):
            audio = R.tts(sh["text"], av["voice"], wd)
            chars += len(sh["text"])
            slate = R.card(wd / f"slate_{i}.png", size, f"{av['name']} · {av['languages']}", [f"“{sh['text']}”"],
                           badge="Avatar clip (Veo) - preview placeholder")
            R.segment(seg, size, audio, slate, None, fixed=sh["sec"] if sh.get("veo") else None)
        elif sh["kind"] == "hero_clip":
            audio = R.silence(sh["sec"], wd / f"sil_{i}.mp3")
            still = fetch_image(sh["image_gcs"], wd)
            ov = None if final else R.caption(wd / f"ov_{i}.png", size, "", lower_third=f"Veo {sh['prompt_key']} - preview")
            R.segment(seg, size, audio, still, ov, pad=0, motion=i)
        elif sh["kind"] == "narration":
            audio = R.tts(sh["text"], av["voice"], wd)
            chars += len(sh["text"])
            ov = R.caption(wd / f"ov_{i}.png", size, sh["text"], lower_third=lower if i <= 2 else None,
                           fact=sh.get("fact"))
            still = fetch_image(sh["image_gcs"], wd) if sh.get("image_gcs") else \
                R.card(wd / f"bg_{i}.png", size, plan["property_name"], [plan.get("area", "")])
            R.segment(seg, size, audio, still, ov, motion=i)
        else:  # CTA card, narrated
            audio = R.tts(sh["text"], av["voice"], wd) if sh.get("text") else R.silence(sh["sec"], wd / f"sil_{i}.mp3")
            chars += len(sh.get("text") or "")
            cta = R.card(wd / "cta.png", size, R.BRAND,
                         ["Contact our advisors", f"Permit: {R.PERMIT}", "AI-generated presenter - demo content"])
            R.segment(seg, size, audio, cta, None, pad=0.6)
        parts.append(seg)
    out = R.concat(parts, wd / ("final.mp4" if final else "preview.mp4"))
    return out, chars


def preview(limit: int | None, only: str | None) -> dict[str, Any]:
    from pitchops.gcs import upload_bytes

    db = fs()
    q = db.collection("video_plans")
    docs = [d.to_dict() for d in q.stream() if (only and d.id == only) or (not only and d.to_dict()["state"] == "DRAFT")]
    docs = docs[:limit] if limit else docs
    done = failed = chars = 0
    for plan in docs:
        try:
            wd = R.workdir()
            if fit_to_limit(plan, wd):
                plan["plan_hash"] = P.plan_hash(plan)
                db.collection("video_plans").document(plan["plan_id"]).update(
                    {"shots": plan["shots"], "plan_hash": plan["plan_hash"],
                     "est_duration_sec": round(sum(x["sec"] for x in plan["shots"]), 1)})
            out, c = render_preview(plan, wd)
            errs = R.qc(out, plan["format"], plan["max_sec"])
            uri = upload_bytes(f"media/plans/{plan['plan_id']}/preview.mp4", out.read_bytes(), "video/mp4")
            db.collection("video_plans").document(plan["plan_id"]).update({
                "state": "PREVIEW_READY", "preview_gcs": uri, "preview_duration_sec": round(R.duration(out), 1),
                "preview_qc": errs, "tts_chars": c, "updated_at": datetime.now(UTC).isoformat()})
            done += 1
            chars += c
        except Exception as e:  # noqa: BLE001 — one plan must not stop the batch
            failed += 1
            log("preview_failed", severity="WARNING", plan_id=plan["plan_id"], error=f"{type(e).__name__}: {e}"[:400])
    return {"previews": done, "failed": failed, "tts_chars": chars}


def main(argv: list[str] | None = None) -> int:
    p = base_parser("media_plans")
    p.add_argument("--create", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--plan-id")
    a = p.parse_args(argv)
    run_id = a.run_id or new_run_id("plans")
    with job_run("media_plans", run_id, dry_run=a.dry_run) as c:
        if a.create:
            c.update(create(a.force))
        if a.preview:
            c.update(preview(a.limit, a.plan_id))
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
