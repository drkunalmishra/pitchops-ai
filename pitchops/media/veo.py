"""P7 Veo prompt library (veo_v1) and the image-to-video call. Every shot starts from a real first frame: an approved
fictional-presenter portrait (intro/outro, with dialogue audio) or a selected official property photo (silent)."""

from __future__ import annotations

import time
from typing import Any

PROMPT_VERSION = "veo_v1"
NEGATIVE = ("distorted architecture, extra floors, new buildings, warped or invented text, logos, watermarks, "
            "people in property shots, celebrity likeness")
PROMPTS = {
    "aerial_orbit": "Cinematic drone shot slowly orbiting the building shown, smooth 30-degree arc, golden-hour light, "
                    "clear sky, gentle parallax on surrounding towers and roads, realistic architecture preserved exactly, "
                    "no new buildings, no text.",
    "aerial_approach": "Slow forward drone approach toward the building shown from mid-altitude, slight descent, Dubai "
                       "skyline in the distance, stable horizon, realistic, architecture preserved exactly, no text.",
    "facade_rise": "Low-angle camera rising smoothly up the facade shown, reflections on glass, steady motion, realistic, "
                   "no text.",
    "interior_glide": "Smooth gimbal glide through the space shown toward the window view, natural daylight, subtle "
                      "parallax, furniture and layout preserved exactly, no people, no text.",
    "amenity_reveal": "Slow lateral dolly along the amenity shown, soft shimmering water, calm atmosphere, realistic, "
                      "no people, no text.",
    "skyline_sunset": "Gentle push-in toward the skyline view at sunset, warm light, realistic, no text.",
}


def presenter_prompt(line: str, voice: str) -> str:
    return (f"The presenter shown looks into the camera and says in clear, friendly English, in a {voice}: \"{line}\" "
            "Natural lip movement and a subtle hand gesture, modern office with the Dubai skyline behind, steady medium "
            "shot, no on-screen text, no captions, no music.")


def generate_clip(client: Any, model: str, prompt: str, image: bytes, mime: str, aspect: str, seconds: int,
                  audio: bool, out_gcs: str, poll_s: float = 10.0, timeout_s: float = 600.0) -> str:
    """Submit one image-to-video job and wait for it. Returns the output gs:// URI (raises on failure / refusal)."""
    from google.genai import types

    op = client.models.generate_videos(
        model=model, prompt=prompt, image=types.Image(image_bytes=image, mime_type=mime),
        config=types.GenerateVideosConfig(aspect_ratio=aspect, duration_seconds=seconds, generate_audio=audio,
                                          number_of_videos=1, person_generation="allow_adult", resolution="1080p",
                                          negative_prompt=NEGATIVE, output_gcs_uri=out_gcs))
    t0 = time.monotonic()
    while not op.done:
        if time.monotonic() - t0 > timeout_s:
            raise TimeoutError("Veo operation timed out")
        time.sleep(poll_s)
        op = client.operations.get(op)
    if op.error:
        raise RuntimeError(f"Veo error: {op.error}")
    res = op.response or op.result
    vids = getattr(res, "generated_videos", None) or []
    if not vids or not vids[0].video or not vids[0].video.uri:
        reasons = getattr(res, "rai_media_filtered_reasons", None)
        raise RuntimeError(f"Veo returned no video (filtered: {reasons})")
    return vids[0].video.uri
