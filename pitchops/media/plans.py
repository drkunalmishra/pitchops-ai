"""P7 video plans (pure): shot lists, cost estimates, avatar rotation, budget guard, plan hash. No API calls here."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

FORMAT_OF = {"walkthrough_16x9": "16x9", "short_9x16": "9x16"}
MAX_SEC = {"16x9": 120.0, "9x16": 55.0}
VEO_SEC = 8
CTA_SEC = 3
STATES = ["DRAFT", "PREVIEW_READY", "AWAITING_APPROVAL", "APPROVED", "GENERATING", "COMPOSING", "REVIEW", "DONE",
          "REJECTED", "FAILED"]
HERO_TAGS = {"16x9": [("aerial_orbit", ("aerial", "skyline_view", "exterior_facade")),
                      ("interior_glide", ("interior_living", "pool_amenity", "lobby", "exterior_facade"))],
             "9x16": [("aerial_approach", ("aerial", "exterior_facade", "skyline_view"))]}


def rotate_avatars(preferred: list[str], avatars: list[str], per: int) -> list[str]:
    """Keep each item's preferred avatar unless it is already used `per` times; then take the least-used one."""
    used: Counter[str] = Counter()
    out = []
    for p in preferred:
        a = p if p in avatars and used[p] < per else min(avatars, key=lambda x: (used[x], avatars.index(x)))
        used[a] += 1
        out.append(a)
    return out


def pick_image(images: list[dict[str, Any]], tags: tuple[str, ...], used: set[str]) -> dict[str, Any] | None:
    sel = [i for i in images if i.get("selected")]
    for tg in tags:
        for i in sorted(sel, key=lambda x: -x.get("quality", 0)):
            if i["tag"] == tg and i["id"] not in used:
                return i
    rest = [i for i in sel if i["id"] not in used]
    return rest[0] if rest else None


def shots(script: dict[str, Any], fmt: str, images: list[dict[str, Any]],
          est_narration_sec: float) -> list[dict[str, Any]]:
    """intro (Veo+audio) -> hero clip(s) (Veo, silent, photo as first frame) -> narration photo-motion -> outro -> CTA."""
    cur = script["current"]
    used: set[str] = set()
    out: list[dict[str, Any]] = [{"kind": "avatar_intro", "veo": True, "audio": True, "sec": VEO_SEC,
                                  "text": cur["avatar_intro_line"]}]
    heroes = HERO_TAGS[fmt]
    first = heroes[0]
    img = pick_image(images, first[1], used)
    if img:
        used.add(img["id"])
        out.append({"kind": "hero_clip", "veo": True, "audio": False, "sec": VEO_SEC, "prompt_key": first[0],
                    "image_id": img["id"], "image_gcs": img["gcs"]})
    # time budget: keep whole narration lines while the full video stays inside the format limit
    wps = 2.2
    outro_sec = VEO_SEC if fmt == "16x9" else len(cur["avatar_outro_line"].split()) / wps + 0.4
    cta_sec = max(CTA_SEC, len(cur["cta"].split()) / wps + 0.6)
    fixed = VEO_SEC * (1 + len(heroes)) + outro_sec + cta_sec + 1.0
    budget = MAX_SEC[fmt] - fixed
    narr, used_sec = [], 0.0
    for n in cur["narration"]:
        sec = len(n["text"].split()) / wps + 0.4
        if used_sec + sec > budget:
            break
        narr.append(n["text"])
        used_sec += sec
    for i, line in enumerate(narr):
        im = pick_image(images, ("exterior_facade", "interior_living", "pool_amenity", "skyline_view", "aerial",
                                 "kitchen", "interior_bedroom", "lobby", "community", "gym_amenity"), used)
        if im:
            used.add(im["id"])
        out.append({"kind": "narration", "veo": False, "audio": True,
                    "sec": round(est_narration_sec / max(len(narr), 1), 1),
                    "text": line, "image_id": im["id"] if im else None, "image_gcs": im["gcs"] if im else None,
                    "fact": next((f["text"] for f in cur.get("on_screen_facts") or []), None) if i == 1 else None})
        if fmt == "16x9" and len(heroes) > 1 and i == len(narr) // 2:
            im2 = pick_image(images, heroes[1][1], used)
            if im2:
                used.add(im2["id"])
                out.append({"kind": "hero_clip", "veo": True, "audio": False, "sec": VEO_SEC,
                            "prompt_key": heroes[1][0], "image_id": im2["id"], "image_gcs": im2["gcs"]})
    # Shorts: Veo intro only; the outro is TTS over the avatar's approved portrait (P7 cost model: ~$2 per Short)
    out.append({"kind": "avatar_outro", "veo": fmt == "16x9", "audio": True,
                "sec": VEO_SEC if fmt == "16x9" else round(outro_sec, 1), "text": cur["avatar_outro_line"]})
    out.append({"kind": "cta_card", "veo": False, "audio": True, "sec": round(cta_sec, 1), "text": cur["cta"]})
    return out


def voice_over_heroes(shot_list: list[dict[str, Any]], max_words: int = 24) -> list[dict[str, Any]]:
    """No dead air over silent Veo property clips: move the next short narration line onto each hero clip as a
    voice-over (it is spoken over the 3D view with a caption instead of over a photo)."""
    out = [dict(x) for x in shot_list]
    for i, sh in enumerate(out):
        if sh["kind"] != "hero_clip" or sh.get("vo_text"):
            continue
        j = next((k for k in range(i + 1, len(out)) if out[k]["kind"] == "narration"
                  and len(out[k]["text"].split()) <= max_words), None)
        if j is not None:
            sh["vo_text"] = out[j]["text"]
            out.pop(j)
    return out


def cost(shot_list: list[dict[str, Any]], price_audio: float, price_silent: float) -> float:
    return round(sum(s["sec"] * (price_audio if s["audio"] else price_silent) for s in shot_list if s["veo"]), 2)


def plan_hash(plan: dict[str, Any]) -> str:
    keys = ("property_id", "format", "script_id", "script_version", "avatar_id", "shots")
    return hashlib.sha256(json.dumps({k: plan.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()[:16]


def budget_check(est: float, committed: float, media_cap: float, project_spent: float, project_cap: float) -> str | None:
    """None if the approval fits; else the reason it is refused (media cap or total project cap)."""
    if committed + est > media_cap + 1e-9:
        return f"would exceed the media budget: ${committed:.2f} committed + ${est:.2f} > ${media_cap:.2f}"
    if project_spent + committed + est > project_cap + 1e-9:
        return f"would exceed the project cap: ${project_spent + committed + est:.2f} > ${project_cap:.2f}"
    return None
