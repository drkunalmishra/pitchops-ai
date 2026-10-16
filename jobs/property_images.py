"""P7 step 1 — property image library for the 40 media properties (D18).

For each property with a verified official site: fetch <= 5 pages (robots.txt respected), collect image URLs, download
images >= 1280 px wide (<= 40 per property) into the PRIVATE bucket media/properties/{property_id}/raw/, tag each with
Gemini Flash-Lite vision (low res thumbnail), and pre-select 8-15 covering aerial/exterior + interiors + amenities.
State lives in Firestore property_images/{property_id}; the admin "Property Images" page edits the selection and
accepts manual uploads for properties without (good) images. Re-runs skip properties that already have images.
Usage:
  uv run python -m jobs.property_images --estimate
  uv run python -m jobs.property_images [--limit N] [--property-id ID] [--force]
"""

from __future__ import annotations

import hashlib
import io
import sys
from datetime import UTC, datetime
from typing import Any

import httpx
from google.genai import types
from PIL import Image

from jobs.property_facts import fetch_pages
from pitchops.bq import query
from pitchops.config import get_settings
from pitchops.discovery.website_links import user_agent
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.media import images as M

JOB = "p7_image_tagging"
MEDIA_PHASE_CAP = 120.0
MAX_BYTES = 15 << 20


def t(name: str) -> str:
    return get_settings().table(name)


def targets(only: str | None) -> list[dict[str, Any]]:
    rows = query(f"""SELECT r.property_id, r.canonical_name, r.media_candidate, r.developer,
            ANY_VALUE(COALESCE(s.final_url, s.url)) url, LOGICAL_OR(IFNULL(s.verified, FALSE)) verified
        FROM `{t('properties_ranked')}` r LEFT JOIN `{t('property_sources')}` s USING (property_id)
        WHERE r.media_candidate IS NOT NULL GROUP BY 1, 2, 3, 4 ORDER BY ANY_VALUE(r.rank)""")
    return [r for r in rows if not only or r["property_id"] == only]


def thumb(img: Image.Image, width: int = 512) -> bytes:
    im = img.convert("RGB")
    im.thumbnail((width, width * 2))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def collect(p: dict[str, Any]) -> list[dict[str, Any]]:
    from pitchops.gcs import upload_bytes

    pages = fetch_pages(p["url"], p["canonical_name"])
    first = p["canonical_name"].split()[0].lower()
    project = [pg for pg in pages if first in pg[1].lower()] or pages
    urls: list[str] = []
    for u, _, html in project:
        urls += [x for x in M.candidates(html, u) if x not in urls]
    out: list[dict[str, Any]] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": user_agent()}) as c:
        for u in urls[: M.MAX_IMAGES * 2]:
            if len(out) >= M.MAX_IMAGES:
                break
            try:
                r = c.get(u)
                if r.status_code >= 400 or not r.headers.get("content-type", "").startswith("image/") \
                        or len(r.content) > MAX_BYTES:
                    continue
                img = Image.open(io.BytesIO(r.content))
                w, h = img.size
            except Exception:  # noqa: BLE001 — skip unreadable images
                continue
            if w < M.MIN_WIDTH:
                continue
            iid = hashlib.sha1(r.content).hexdigest()[:16]
            ext = (img.format or "jpeg").lower().replace("jpeg", "jpg")
            gcs = upload_bytes(f"media/properties/{p['property_id']}/raw/{iid}.{ext}", r.content,
                               r.headers.get("content-type", "image/jpeg"))
            out.append({"id": iid, "gcs": gcs, "source_url": u, "width": w, "height": h, "_thumb": thumb(img),
                        "origin": "official_site"})
    return out


def tag(g: Any, img: dict[str, Any], name: str) -> dict[str, Any]:
    s = get_settings()
    res = g.generate_json(s.gemini_model_lite, [
        types.Part.from_bytes(data=img["_thumb"], mime_type="image/jpeg"),
        f"Real-estate marketing image for the project '{name}'. Classify what it shows, rate its quality for a "
        "premium property video (0-1: sharp, well lit, no heavy text overlays, not a floor plan or brochure page), "
        "and say whether it contains overlaid text/logos and whether people are visible."],
        M.tag_schema(), prompt_version="image_tag_v1", temperature=0.0)
    d = res.data
    q = float(d["quality"]) * (0.6 if d["has_text_or_logo"] else 1.0) * (0.7 if d["shows_people"] else 1.0)
    return {**{k: v for k, v in img.items() if k != "_thumb"}, "tag": d["tag"], "quality": round(q, 2),
            "has_text_or_logo": d["has_text_or_logo"], "shows_people": d["shows_people"], "caption": d.get("caption")}


def main(argv: list[str] | None = None) -> int:
    p = base_parser("property_images")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--property-id")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    s = get_settings()
    from pitchops.fs import client as fs

    db = fs()
    props = targets(a.property_id)
    have = {d.id for d in db.collection("property_images").select(["updated_at"]).stream()}
    todo = [x for x in props if x["verified"] and x["url"] and (a.force or x["property_id"] not in have)]
    todo = todo[: a.limit] if a.limit else todo
    if a.estimate or a.dry_run:
        pin, pout = s.price_for(s.gemini_model_lite)
        print({"media_properties": len(props), "with_verified_site": sum(1 for x in props if x["verified"]),
               "to_fetch": len(todo), "need_manual_images": [x["canonical_name"] for x in props if not x["verified"]],
               "est_usd": round(len(todo) * M.MAX_IMAGES * (700 * pin + 80 * pout) / 1e6, 3)})
        return 0
    from pitchops.gemini.client import GeminiClient

    run_id = a.run_id or new_run_id("images")
    g = GeminiClient(JOB, run_id, phase_prefix="p7_", phase_cap=MEDIA_PHASE_CAP)
    with job_run("property_images", run_id) as c:
        stats = {"properties": 0, "images": 0, "selected": 0, "empty": []}
        for x in todo:
            try:
                imgs = collect(x)
                tagged = []
                for im in imgs:
                    try:
                        tagged.append(tag(g, im, x["canonical_name"]))
                    except Exception as e:  # noqa: BLE001
                        log("image_tag_failed", severity="WARNING", image=im["id"], error=str(e)[:160])
                sel = set(M.select(tagged))
                for im in tagged:
                    im["selected"] = im["id"] in sel
                db.collection("property_images").document(x["property_id"]).set({
                    "property_id": x["property_id"], "canonical_name": x["canonical_name"],
                    "media_candidate": x["media_candidate"], "images": tagged,
                    "updated_at": datetime.now(UTC).isoformat()})
                stats["properties"] += 1
                stats["images"] += len(tagged)
                stats["selected"] += len(sel)
                if len(sel) < M.PER_PROPERTY[0]:
                    stats["empty"].append(x["canonical_name"])
            except Exception as e:  # noqa: BLE001 — one site must not stop the run
                log("images_failed", severity="WARNING", property_id=x["property_id"], error=str(e)[:200])
        c.update({k: v if not isinstance(v, list) else len(v) for k, v in stats.items()})
    print({"run_id": run_id, **stats, "need_manual_images": [x["canonical_name"] for x in props if not x["verified"]]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
