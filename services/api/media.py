"""P7 Media API: property images (select / upload), avatars, video plans (preview playback, edit, approve with budget
guard, reject). Nothing here calls Veo or Imagen — generation is a separate job that runs only on APPROVED plans."""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from pitchops.config import get_settings
from pitchops.media import plans as P
from pitchops.media.avatars import AVATARS
from pitchops.media.images import TAGS

MAX_UPLOAD = 15 << 20



class Selection(BaseModel):
    selected: list[str]
    tags: dict[str, str] | None = None


class PlanEdit(BaseModel):
    avatar_id: str | None = None
    drop_hero: int | None = None  # index of a hero clip to remove (cost drops)


class AvatarPick(BaseModel):
    candidate_id: str


class Decision(BaseModel):
    note: str | None = None


def fs() -> Any:
    from pitchops.fs import client

    return client()


def blob_bytes(gcs: str) -> bytes:
    from pitchops.gcs import bucket

    return bucket().blob(gcs.split("/", 3)[3]).download_as_bytes()


def media_committed() -> float:
    """Estimated cost of every plan already approved / generating / done (actuals replace estimates when known)."""
    tot = 0.0
    for d in fs().collection("video_plans").where("state", "in",
                                                    ["APPROVED", "GENERATING", "COMPOSING", "REVIEW", "DONE"]).stream():
        x = d.to_dict()
        tot += float(x.get("actual_cost_usd") or x.get("est_cost_usd") or 0)
    for d in fs().collection("avatars").stream():
        tot += float(d.to_dict().get("imagen_cost_usd") or 0)
    return round(tot, 2)


def project_spent() -> float:
    return float((fs().collection("finops").document("current").get().to_dict() or {}).get("total_usd") or 0)


def media_router(require_user: Any) -> APIRouter:
    r = APIRouter()

    # ---- property images ----------------------------------------------------------------------------------------
    @r.get("/media/images")
    def list_images(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
        from pitchops.bq import query

        props = query(f"""SELECT property_id, canonical_name, media_candidate FROM
            `{get_settings().table('properties_ranked')}` WHERE media_candidate IS NOT NULL ORDER BY rank""",
                      max_bytes=1 << 30)
        docs = {d.id: d.to_dict() for d in fs().collection("property_images").stream()}
        out = []
        for p in props:
            imgs = docs.get(p["property_id"], {}).get("images", [])
            out.append({**p, "images": len(imgs), "selected": sum(1 for i in imgs if i.get("selected"))})
        return out

    @r.get("/media/images/{property_id}")
    def get_images(property_id: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        d = fs().collection("property_images").document(property_id).get()
        return d.to_dict() if d.exists else {"property_id": property_id, "images": []}

    @r.get("/media/image/{property_id}/{image_id}")
    def image_bytes(property_id: str, image_id: str, user: dict[str, Any] = Depends(require_user)) -> Response:
        d = fs().collection("property_images").document(property_id).get().to_dict() or {}
        img = next((i for i in d.get("images", []) if i["id"] == image_id), None)
        if not img:
            raise HTTPException(404, "image not found")
        from PIL import Image

        im = Image.open(io.BytesIO(blob_bytes(img["gcs"]))).convert("RGB")
        im.thumbnail((640, 640))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80)
        return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


    @r.post("/media/images/{property_id}/selection")
    def set_selection(property_id: str, body: Selection, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        ref = fs().collection("property_images").document(property_id)
        d = ref.get().to_dict() or {"images": []}
        for i in d["images"]:
            i["selected"] = i["id"] in body.selected
            if body.tags and body.tags.get(i["id"]) in TAGS:
                i["tag"] = body.tags[i["id"]]
        ref.set({**d, "updated_at": datetime.now(UTC).isoformat()})
        return {"selected": sum(1 for i in d["images"] if i["selected"])}

    @r.post("/media/images/{property_id}/upload")
    async def upload(property_id: str, file: UploadFile = File(...), tag: str = "exterior_facade",
                     user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        from PIL import Image

        from pitchops.gcs import upload_bytes

        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "image larger than 15 MB")
        try:
            im = Image.open(io.BytesIO(data))
            w, h = im.size
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, "not an image") from e
        iid = hashlib.sha1(data).hexdigest()[:16]
        ext = (im.format or "jpeg").lower().replace("jpeg", "jpg")
        gcs = upload_bytes(f"media/properties/{property_id}/raw/{iid}.{ext}", data, file.content_type or "image/jpeg")
        ref = fs().collection("property_images").document(property_id)
        d = ref.get().to_dict() or {"property_id": property_id, "images": []}
        d["images"] = [i for i in d.get("images", []) if i["id"] != iid] + [{
            "id": iid, "gcs": gcs, "source_url": None, "origin": "manual_upload", "width": w, "height": h,
            "tag": tag if tag in TAGS else "other", "quality": 0.8, "selected": True, "uploaded_by": user.get("uid")}]
        ref.set({**d, "updated_at": datetime.now(UTC).isoformat()})
        return {"id": iid, "width": w, "height": h, "low_res": w < 1280}

    # ---- avatars ------------------------------------------------------------------------------------------------
    @r.get("/media/avatars")
    def avatars(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
        docs = {d.id: d.to_dict() for d in fs().collection("avatars").stream()}
        return [{"avatar_id": k, **v, **{x: docs.get(k, {}).get(x) for x in ("candidates", "approved_candidate", "status")}}
                for k, v in AVATARS.items()]

    @r.get("/media/avatar/{avatar_id}/{candidate_id}")
    def avatar_image(avatar_id: str, candidate_id: str, user: dict[str, Any] = Depends(require_user)) -> Response:
        d = fs().collection("avatars").document(avatar_id).get().to_dict() or {}
        c = next((x for x in d.get("candidates") or [] if x["id"] == candidate_id), None)
        if not c:
            raise HTTPException(404, "candidate not found")
        from PIL import Image

        im = Image.open(io.BytesIO(blob_bytes(c["gcs"]))).convert("RGB")
        im.thumbnail((640, 640))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

    @r.post("/media/avatars/{avatar_id}/approve")
    def avatar_approve(avatar_id: str, body: AvatarPick, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        ref = fs().collection("avatars").document(avatar_id)
        d = ref.get().to_dict() or {}
        c = next((x for x in d.get("candidates") or [] if x["id"] == body.candidate_id), None)
        if not c:
            raise HTTPException(404, "candidate not found")
        now = datetime.now(UTC).isoformat()
        ref.update({"approved_candidate": c["id"], "portrait_gcs": c["gcs"], "status": "approved",
                    "approved_by": user.get("uid"), "approved_at": now})
        fs().collection("audit").add({"action": "avatar_approve", "avatar_id": avatar_id, "candidate": c["id"],
                                      "uid": user.get("uid"), "at": now})
        return {"avatar_id": avatar_id, "approved_candidate": c["id"]}

    # ---- plans --------------------------------------------------------------------------------------------------
    @r.get("/media/plans")
    def plans(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        s = get_settings()
        rows = [d.to_dict() for d in fs().collection("video_plans").stream()]
        for x in rows:
            x.pop("shots", None)
        return {"plans": sorted(rows, key=lambda x: (x["format"], x["property_name"])),
                "media_budget_usd": s.media_budget_usd, "committed_usd": media_committed(),
                "project_spent_usd": project_spent(), "project_cap_usd": s.total_project_cap_usd}

    @r.get("/media/plans/{plan_id}")
    def plan(plan_id: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        d = fs().collection("video_plans").document(plan_id).get()
        if not d.exists:
            raise HTTPException(404, "plan not found")
        return d.to_dict()

    @r.get("/media/plans/{plan_id}/video/{kind}")
    def video(plan_id: str, kind: str, user: dict[str, Any] = Depends(require_user)) -> Response:
        x = plan(plan_id, user)
        gcs = x.get("preview_gcs" if kind == "preview" else "final_gcs")
        if not gcs:
            raise HTTPException(404, f"no {kind} video yet")
        return Response(blob_bytes(gcs), media_type="video/mp4", headers={"Cache-Control": "private, max-age=600"})


    @r.post("/media/plans/{plan_id}/edit")
    def edit(plan_id: str, body: PlanEdit, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        s = get_settings()
        ref = fs().collection("video_plans").document(plan_id)
        x = ref.get().to_dict()
        if not x:
            raise HTTPException(404, "plan not found")
        if x["state"] not in ("DRAFT", "PREVIEW_READY", "AWAITING_APPROVAL"):
            raise HTTPException(409, f"plan is {x['state']}")
        if body.avatar_id:
            if body.avatar_id not in AVATARS:
                raise HTTPException(400, "unknown avatar")
            x["avatar_id"] = body.avatar_id
        if body.drop_hero is not None and 0 <= body.drop_hero < len(x["shots"]) and \
                x["shots"][body.drop_hero]["kind"] == "hero_clip":
            x["shots"].pop(body.drop_hero)
        x["est_cost_usd"] = P.cost(x["shots"], s.veo_price_audio_per_sec, s.veo_price_silent_per_sec)
        x["plan_hash"] = P.plan_hash(x)
        x["state"] = "DRAFT"  # preview must be re-rendered after a change
        ref.set(x)
        return x


    @r.post("/media/plans/{plan_id}/approve")
    def approve(plan_id: str, body: Decision, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        s = get_settings()
        ref = fs().collection("video_plans").document(plan_id)
        x = ref.get().to_dict()
        if not x:
            raise HTTPException(404, "plan not found")
        if x["state"] not in ("PREVIEW_READY", "AWAITING_APPROVAL"):
            raise HTTPException(409, "render and watch the free preview before approving")
        sc = fs().collection("scripts").document(x["script_id"]).get().to_dict() or {}
        if (sc.get("compliance_status") or "BLOCK") == "BLOCK":
            raise HTTPException(409, "the script has unresolved BLOCK compliance findings")
        why = P.budget_check(x["est_cost_usd"], media_committed(), s.media_budget_usd, project_spent(),
                             s.total_project_cap_usd)
        if why:
            raise HTTPException(409, f"budget guard: {why}")
        now = datetime.now(UTC).isoformat()
        rec = {"plan_id": plan_id, "plan_hash": P.plan_hash(x), "est_cost_usd": x["est_cost_usd"],
               "script_id": x["script_id"], "script_version": sc.get("version"), "avatar_id": x["avatar_id"],
               "approver_uid": user.get("uid"), "approved_at": now, "note": body.note}
        fs().collection("media_approvals").document(plan_id).set(rec)
        ref.update({"state": "APPROVED", "approval": rec, "updated_at": now})
        if sc.get("status") != "approved":  # approving the plan also approves its script (same reviewer, audited)
            fs().collection("scripts").document(x["script_id"]).update({"status": "approved", "approval": {
                "via": "media_plan", "plan_id": plan_id, "reviewer_uid": user.get("uid"), "approved_at": now,
                "script_hash": (sc.get("current") or {}).get("content_hash")}})
        fs().collection("audit").add({"action": "media_approve", "plan_id": plan_id, "uid": user.get("uid"),
                                      "at": now, "est_cost_usd": x["est_cost_usd"]})
        return rec

    @r.post("/media/plans/{plan_id}/reject")
    def reject(plan_id: str, body: Decision, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        ref = fs().collection("video_plans").document(plan_id)
        x = ref.get().to_dict()
        if not x:
            raise HTTPException(404, "plan not found")
        if x["state"] in ("GENERATING", "COMPOSING"):
            raise HTTPException(409, "generation in progress")
        now = datetime.now(UTC).isoformat()
        ref.update({"state": "REJECTED", "rejection": {"uid": user.get("uid"), "at": now, "note": body.note}})
        fs().collection("media_approvals").document(plan_id).delete()
        fs().collection("audit").add({"action": "media_reject", "plan_id": plan_id, "uid": user.get("uid"), "at": now})
        return {"plan_id": plan_id, "state": "REJECTED"}

    return r
