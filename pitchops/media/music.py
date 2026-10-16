"""Background music beds from Lyria (lyria-002, ~30 s instrumental WAV), one per seller-persona mood, cached in the
private bucket media/music/{key}.wav and costed in llm_calls (job p7_lyria). Instrumental only — no vocals."""

from __future__ import annotations

import base64
import time
from datetime import UTC, datetime
from pathlib import Path

MODEL = "lyria-002"
PRICE = 0.06  # per 30 s track (estimate)
NEGATIVE = "vocals, singing, lyrics, speech, harsh drums, distortion, abrupt ending"
MOODS = {
    "lifestyle": "warm, breezy lounge house with soft piano and light percussion, sunny resort mood",
    "education_led": "calm, minimal corporate piano with gentle pads, thoughtful and clear",
    "status_luxury": "elegant cinematic strings and deep piano, luxurious, slow and confident",
    "developer_authority": "inspiring orchestral build, steady pulse, grand architecture mood",
    "financial": "modern minimal electronic with soft synth arpeggio, focused and analytical",
    "authority": "confident cinematic corporate with steady drums and piano, trustworthy",
    "fomo_scarcity": "energetic uplifting electronic with driving beat, anticipation, exciting launch",
    "payment_plan_ease": "light optimistic acoustic pop with ukulele and claps, friendly and easy",
    "risk_reduction": "calm reassuring ambient piano with warm pads, steady and safe",
    "social_proof": "upbeat feel-good corporate pop, celebratory, community vibe",
    "default": "soft modern corporate ambient with gentle piano, unobtrusive",
}


def track(key: str, cache: Path, run_id: str) -> Path:
    """Local WAV for a mood key; generated once (Lyria) and re-used from the bucket afterwards."""
    import google.auth
    import google.auth.transport.requests
    import httpx

    from pitchops.bq import insert_rows
    from pitchops.config import get_settings
    from pitchops.gcs import bucket, upload_bytes

    key = key if key in MOODS else "default"
    out = cache / f"music_{key}.wav"
    if out.exists():
        return out
    blob = bucket().blob(f"media/music/{key}.wav")
    if blob.exists():
        blob.download_to_filename(out)
        return out
    s = get_settings()
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    url = (f"https://{s.gcp_region}-aiplatform.googleapis.com/v1/projects/{s.gcp_project_id}/locations/"
           f"{s.gcp_region}/publishers/google/models/{MODEL}:predict")
    r = None
    for seed in (7, 23, 61):  # "recitation" blocks (output too close to existing music): try another seed
        t0 = time.monotonic()
        r = httpx.post(url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=180, json={
            "instances": [{"prompt": f"Original instrumental background music for a real-estate video: {MOODS[key]}.",
                           "negative_prompt": NEGATIVE, "seed": seed}], "parameters": {"sample_count": 1}})
        ok = r.status_code < 400
        now = datetime.now(UTC).isoformat()
        insert_rows("llm_calls", [{"ts": now, "job": "p7_lyria", "model_id": MODEL, "prompt_version": f"music_{key}",
                                   "tokens_in": 0, "tokens_out": 30, "cost_usd_est": PRICE if ok else 0.0,
                                   "latency_ms": int((time.monotonic() - t0) * 1000), "status": "OK" if ok else "ERROR",
                                   "run_id": run_id, "ingested_at": now}])
        if ok or "recitation" not in r.text.lower():
            break
    r.raise_for_status()
    data = base64.b64decode(r.json()["predictions"][0]["bytesBase64Encoded"])
    upload_bytes(f"media/music/{key}.wav", data, "audio/wav")
    out.write_bytes(data)
    return out
